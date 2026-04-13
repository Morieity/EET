import re
import logging
import threading
from collections.abc import Generator
from Backend.Domain.Entities.conversation import Conversation, ChatRound
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.ILLMService import ILLMService
from Backend.Application.Skills.FaultTreeSkill import FaultTreeSkill

logger = logging.getLogger(__name__)

# 用于判断用户是否想要操作故障树的关键词模式
_FAULT_TREE_GENERATE_PATTERN = re.compile(
    r"(生成|创建|构建|画|建立|分析).{0,10}(故障树|故障分析|FTA)",
    re.IGNORECASE,
)
_FAULT_TREE_UPDATE_PATTERN = re.compile(
    r"(修改|更新|调整|删除|添加|增加|移除|重命名|改).{0,10}(故障树|节点|逻辑门|连接)",
    re.IGNORECASE,
)

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

        # 4. 判断是否为故障树请求，若是则异步生成，同时流式输出普通对话
        generate_match = _FAULT_TREE_GENERATE_PATTERN.search(question)
        update_match = _FAULT_TREE_UPDATE_PATTERN.search(question)
        is_fault_tree_request = bool(generate_match or update_match)

        full_answer = ""
        fault_tree_id: str | None = None

        if is_fault_tree_request:
            # 构建带工具指令的 messages，供后台 function calling 使用
            tool_instruction = (
                "当前用户明确要求生成故障树。请调用 generate_fault_tree 工具，"
                "并返回完整的 name、nodes、edges 结构。"
                if generate_match
                else
                "当前用户明确要求修改已有故障树。请调用 update_fault_tree 工具，"
                "并返回修改后的完整 name、nodes、edges 结构。"
            )
            tool_messages = messages.copy()
            tool_messages[0] = {
                "role": "system",
                "content": f"{system_content}\n\n{tool_instruction}",
            }

            # 后台异步执行 function calling + 故障树生成
            fault_tree_container: list = [None]
            async_done = threading.Event()

            def _generate_fault_tree_async() -> None:
                try:
                    tool_result = self._llm.chat_with_tools(
                        tool_messages,
                        self._fault_tree_skill.tools,
                    )
                    if tool_result["type"] == "tool_call":
                        ft = self._fault_tree_skill.execute(
                            function_name=tool_result["name"],
                            arguments=tool_result["arguments"],
                            conversation_id=conversation.id,
                        )
                        fault_tree_container[0] = ft
                        logger.info("Async fault tree generated: %s (id=%s)", ft.name, ft.id)
                    else:
                        logger.warning(
                            "Fault tree intent detected but model did not call a tool: %s",
                            question,
                        )
                except Exception:
                    logger.exception("Async fault tree generation failed")
                finally:
                    async_done.set()

            thread = threading.Thread(target=_generate_fault_tree_async, daemon=True)
            thread.start()

            # 前台同步流式普通对话（让 LLM 先做自然语言分析）
            stream_system = (
                f"{system_content}\n\n"
                "用户请求生成故障树，请先用自然语言简要分析故障场景和原因，"
                "不要在回复中输出任何JSON代码、代码块或故障树数据结构，"
                "不必在文字中描述节点结构，故障树图将在本次回复结束后自动附加展示。"
            )
            stream_messages = messages.copy()
            stream_messages[0] = {"role": "system", "content": stream_system}

            try:
                for token in self._llm.stream_chat(stream_messages):
                    full_answer += token
                    yield {"type": "token", "content": token}
            except Exception:
                logger.exception("LLM stream failed during fault tree request")
                async_done.wait()
                yield {"type": "error", "message": "LLM service error"}
                return

            # 等待故障树后台线程完成（最多 120 秒），并在结尾推送结果
            async_done.wait(timeout=120)
            if fault_tree_container[0] is not None:
                fault_tree_id = fault_tree_container[0].id
                yield {"type": "fault_tree", "fault_tree": fault_tree_container[0].to_dict()}
            else:
                logger.warning("Async fault tree generation produced no result for: %s", question)

        else:
            # 普通对话：直接流式调用 LLM（无 tool calling）
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
            fault_tree_id=fault_tree_id,
        )
        self._conversation_repo.add_round(conversation.id, chat_round)
        logger.info("Chat round saved for conversation: %s", conversation.id)

        done_event = {
            "type": "done",
            "conversation_id": conversation.id,
            "answer": full_answer,
        }
        if fault_tree_id:
            done_event["fault_tree_id"] = fault_tree_id

        yield done_event


