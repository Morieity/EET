import json
import logging
from collections.abc import Generator
from Backend.Domain.Entities.conversation import Conversation, ChatRound
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.ILLMService import ILLMService
from Backend.Application.Skills.FaultTreeSkill import FaultTreeSkill

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是一个基于文档的智能助手，擅长根据提供的文档内容回答问题和生成故障树。\n"
    "如果提供的上下文不包含足够的信息来回答问题，请如实说明。\n\n"
    "你具备故障树生成能力：\n"
    "- 当用户要求生成故障树、分析故障原因、构建故障分析模型时，使用 generate_fault_tree 工具。\n"
    "- 当用户要求修改、更新、调整已有的故障树时，使用 update_fault_tree 工具。\n"
    "- 故障树由事件节点(event)和逻辑门节点(gate, AND/OR)以及连接边组成。\n"
    "- 顶层事件是根故障，通过逻辑门连接到下层原因事件。\n"
    "- 如果用户提供的信息没有描述故障且混乱，无法生成完整的故障树，"
    "请先尽力根据已有信息生成，然后在回复末尾提出补充问题以获取更多细节。\n"
)

MAX_HISTORY_ROUNDS = 10


class ChatUseCase:
    def __init__(
        self,
        conversation_repository: IConversationRepository,
        vector_store_repository: IVectorStoreRepository,
        llm_service: ILLMService,
        fault_tree_skill: FaultTreeSkill,
    ):
        self._conversation_repo = conversation_repository
        self._vector_store = vector_store_repository
        self._llm = llm_service
        self._fault_tree_skill = fault_tree_skill

    def execute(
        self, question: str, conversation_id: str | None = None
    ) -> Generator[dict, None, None]:
        """执行一轮对话，以 Generator 方式逐步 yield 事件给调用方。

        事件类型:
          - {"type": "conversation", "conversation_id": ..., "name": ...}
          - {"type": "sources", "sources": [...]}
          - {"type": "token", "content": ...}
          - {"type": "fault_tree", "fault_tree": {...}}
          - {"type": "done", "answer": ..., "conversation_id": ...}
          - {"type": "error", "message": ...}
        """
        # 1. 获取或创建对话
        if conversation_id:
            conversation = self._conversation_repo.get_by_id(conversation_id)
            if conversation is None:
                yield {"type": "error", "message": f"Conversation not found: {conversation_id}"}
                return
        else:
            name = question[:30] if len(question) > 30 else question
            conversation = Conversation(name=name)
            self._conversation_repo.save(conversation)
            logger.info("New conversation created: %s", conversation.id)

        yield {
            "type": "conversation",
            "conversation_id": conversation.id,
            "name": conversation.name,
        }

        # 2. 从向量库检索相关文档
        try:
            sources = self._vector_store.search(query=question, k=5, score_threshold=0.1)
        except Exception:
            logger.exception("Vector store search failed")
            sources = []

        yield {"type": "sources", "sources": sources}

        # 3. 构建 messages（system + context + 历史 + 当前问题）
        context = "\n\n".join(
            [f"[{s.get('file_name', 'Unknown')}]\n{s['page_content']}" for s in sources]
        )

        # 注入已有故障树上下文（支持多轮修改同一棵树）
        existing_tree_context = self._fault_tree_skill.get_existing_tree_context(
            conversation.id
        )

        system_content = SYSTEM_PROMPT + existing_tree_context

        messages: list[dict] = [{"role": "system", "content": system_content}]

        # 加入最近 N 轮历史对话
        recent_rounds = conversation.rounds[-MAX_HISTORY_ROUNDS:]
        for r in recent_rounds:
            messages.append({"role": "user", "content": r.question})
            messages.append({"role": "assistant", "content": r.answer})

        # 当前问题拼接检索上下文
        if context:
            user_content = f"{question}\n\nContext:\n{context}"
        else:
            user_content = question

        messages.append({"role": "user", "content": user_content})

        # 4. 先用 tool calling 判断是否需要生成/修改故障树
        try:
            tool_result = self._llm.chat_with_tools(
                messages, self._fault_tree_skill.tools
            )
        except Exception:
            logger.exception("LLM chat_with_tools failed, falling back to stream_chat")
            tool_result = {"type": "text"}

        if tool_result["type"] == "tool_call":
            # LLM 决定调用故障树工具
            func_name = tool_result["name"]
            func_args = tool_result["arguments"]
            logger.info("Function call triggered: %s", func_name)

            try:
                fault_tree = self._fault_tree_skill.execute(
                    function_name=func_name,
                    arguments=func_args,
                    conversation_id=conversation.id,
                )
                yield {"type": "fault_tree", "fault_tree": fault_tree.to_dict()}

                # 生成一段文字描述作为 answer，并流式输出
                tree_summary = self._build_tree_summary(fault_tree, func_name)
                full_answer = ""
                # 再让 LLM 生成一段自然语言说明
                summary_messages = messages.copy()
                summary_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": func_name,
                            "arguments": json.dumps(func_args, ensure_ascii=False),
                        },
                    }],
                })
                summary_messages.append({
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "content": json.dumps(fault_tree.to_dict(), ensure_ascii=False),
                })

                try:
                    for token in self._llm.stream_chat(summary_messages):
                        full_answer += token
                        yield {"type": "token", "content": token}
                except Exception:
                    # 如果摘要生成失败，使用预构建的摘要
                    logger.exception("Summary stream failed, using built-in summary")
                    full_answer = tree_summary
                    yield {"type": "token", "content": full_answer}

            except Exception:
                logger.exception("Fault tree function execution failed")
                yield {"type": "error", "message": "故障树生成失败"}
                return
        else:
            # 普通对话：流式调用 LLM
            full_answer = ""
            try:
                for token in self._llm.stream_chat(messages):
                    full_answer += token
                    yield {"type": "token", "content": token}
            except Exception:
                logger.exception("LLM stream failed")
                yield {"type": "error", "message": "LLM service error"}
                return

        # 5. 保存这一轮对话到数据库
        chat_round = ChatRound(
            question=question,
            prompt=user_content,
            answer=full_answer,
            sources=sources,
        )
        self._conversation_repo.add_round(conversation.id, chat_round)
        logger.info("Chat round saved for conversation: %s", conversation.id)

        yield {
            "type": "done",
            "conversation_id": conversation.id,
            "answer": full_answer,
        }

    @staticmethod
    def _build_tree_summary(fault_tree, func_name: str) -> str:
        """构建故障树操作的简要描述。"""
        action = "生成" if func_name == "generate_fault_tree" else "更新"
        event_nodes = [n for n in fault_tree.nodes if n.node_type.value == "event"]
        gate_nodes = [n for n in fault_tree.nodes if n.node_type.value == "gate"]
        return (
            f"已{action}故障树「{fault_tree.name}」，"
            f"包含 {len(event_nodes)} 个事件节点和 {len(gate_nodes)} 个逻辑门节点，"
            f"共 {len(fault_tree.edges)} 条连接边。"
        )
