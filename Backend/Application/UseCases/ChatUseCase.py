import re
import logging
import threading
from collections.abc import Generator
from typing import TYPE_CHECKING
from Backend.Domain.Entities.conversation import Conversation, ChatRound
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.ILLMService import ILLMService
from Backend.Application.Interfaces.IGraphRepository import IGraphRepository
from Backend.Application.Interfaces.IContextManager import IContextManager
from Backend.Application.ContextManagement.ContextManagerTypes import ContextManagerConfig
from Backend.Application.Skills.FaultTreeSkill import FaultTreeSkill

if TYPE_CHECKING:
    from Backend.Application.UseCases.ExpertLearningUseCase import ExpertLearningUseCase

logger = logging.getLogger(__name__)

# 精确意图：用户明确要求生成/修改故障树 → 跳过分析，直接调用 function calling
_FAULT_TREE_GENERATE_PATTERN = re.compile(
    r"(生成|创建|构建|画|建立).{0,10}(故障树|故障分析|FTA)",
    re.IGNORECASE,
)
_FAULT_TREE_UPDATE_PATTERN = re.compile(
    r"(修改|更新|调整|删除|添加|增加|移除|重命名|改).{0,10}(故障树|节点|逻辑门|连接)",
    re.IGNORECASE,
)
# 宽泛匹配：只要提到故障树/FTA → 让 LLM 分析 + 后台生成
_FAULT_TREE_MENTION_PATTERN = re.compile(
    r"(故障树|FTA|故障分析)",
    re.IGNORECASE,
)

SYSTEM_PROMPT = (
    "你是一位专业的故障分析与文档问答助手，名字叫做EET Fault Tree，具备故障树分析(FTA)领域知识。\n"
    "你的职责是基于用户提供的文档和上下文，准确回答问题并构建规范的故障树。\n"
    "如果上下文信息不足以回答问题，请如实说明，不要编造。\n\n"
    "如果用户没有明确的目的和问题，请先询问用户的具体需求和目标，确保理解清楚后再进行回答或分析，不能基于匹配的上下文进行回答。\n\n"
    "## 故障树分析能力\n\n"
    "你可以调用以下工具：\n"
    "- generate_fault_tree：生成新故障树（用户要求生成、分析故障原因、构建 FTA 模型时）\n"
    "- update_fault_tree：修改已有故障树（用户要求增删改节点、调整连接关系时）\n\n"
    "## 故障树构建规范\n\n"
    "1. **结构原则**：采用自顶向下的分解方式，顶层事件(Top Event)为根故障，"
    "逐层分解为中间事件和底层基本事件。\n"
    "2. **逻辑门使用**：\n"
    "   - OR 门：任一子事件发生即可导致父事件，用于表示多种独立原因。\n"
    "   - AND 门：所有子事件同时发生才导致父事件，用于表示需要多因素耦合的故障。\n"
    "3. **节点命名**：事件节点使用简洁明确的故障描述（如“轴承磨损”而非“问题1”），"
    "门节点 label 留空或标注逻辑关系。\n"
    "4. **层级深度**：一般 3-5 层为宜，确保底层事件是可直接检测或排查的基本事件。\n"
    "5. **完整性**：每个逻辑门至少有 2 个子节点，避免出现悬空节点或孤立子树。\n\n"
    "## 信息不足时的处理\n\n"
    "若用户描述不够详细，请先基于已有信息和文档上下文尽力生成合理的故障树，"
    "然后在回复末尾提出针对性问题，引导用户补充关键信息（如具体故障现象、系统组成、运行环境等）。\n"
)

MAX_HISTORY_ROUNDS = 20
DEFAULT_CONTEXT_CONFIG = ContextManagerConfig(max_history_rounds=MAX_HISTORY_ROUNDS)


class ChatUseCase:
    def __init__(
        self,
        conversation_repository: IConversationRepository,
        vector_store_repository: IVectorStoreRepository,
        llm_service: ILLMService,
        fault_tree_skill: FaultTreeSkill,
        graph_repository: IGraphRepository | None = None,
        context_manager: IContextManager | None = None,
        context_config: ContextManagerConfig | None = None,
        fault_tree_wait_timeout_seconds: float = 120,
        expert_learning: "ExpertLearningUseCase | None" = None,
    ):
        self._conversation_repo = conversation_repository
        self._vector_store = vector_store_repository
        self._llm = llm_service
        self._fault_tree_skill = fault_tree_skill
        self._graph_repo = graph_repository
        self._context_manager = context_manager
        self._context_config = context_config or DEFAULT_CONTEXT_CONFIG
        self._fault_tree_wait_timeout_seconds = fault_tree_wait_timeout_seconds
        self._expert_learning = expert_learning

    def execute(
        self, question: str, conversation_id: str | None = None
    ) -> Generator[dict, None, None]:
        """执行一轮对话，以 Generator 方式逐步 yield 事件给调用方。

        事件类型:
          - {"type": "conversation", "conversation_id": ..., "name": ...}
          - {"type": "sources", "sources": [...]}
                    - {"type": "generating_tree"}
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

        # 2. 五步 GraphRAG 检索（图谱引导模式）
        # ① 向量寻点（增强版）：同时搜索 entity + relation 集合
        graph_paths: list[dict] = []
        seed_names: list[str] = []
        try:
            entity_results = self._vector_store.search_entities(query=question)
            seed_names = [m.get("name", "") for m in entity_results if m.get("name")]
        except Exception:
            logger.debug("Entity search skipped or failed")

        try:
            relation_results = self._vector_store.search_relations(query=question)
            for rel in relation_results:
                head = rel.get("head", "")
                tail = rel.get("tail", "")
                if head and head not in seed_names:
                    seed_names.append(head)
                if tail and tail not in seed_names:
                    seed_names.append(tail)
        except Exception:
            logger.debug("Relation search skipped or failed")

        # ② 图谱扩展：BFS 从种子扩展 2 跳子图
        if seed_names and self._graph_repo:
            try:
                graph_paths = self._graph_repo.expand_subgraph(seed_names, hops=2)
            except Exception:
                logger.debug("Subgraph expansion failed, falling back to vector-only")

        # ③ 图谱引导的切片检索：用图谱路径中的来源信息精准定位切片
        sources: list[dict] = []
        if graph_paths:
            source_keys: list[dict] = []
            seen_keys: set[tuple] = set()
            for path in graph_paths:
                sf = path.get("source_file", "")
                sc = path.get("source_chunk_id", "")
                if sf:
                    key = (sf, sc)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        source_keys.append({"file_name": sf, "chunk_index": sc})
            if source_keys:
                try:
                    sources = self._vector_store.search_by_sources(
                        source_keys=source_keys, query=question, k=15
                    )
                except Exception:
                    logger.debug("Graph-guided chunk retrieval failed")

        # ④ 向量补充检索（兜底）：图谱引导结果不足时补充
        GRAPH_MIN_SOURCES = 5
        if len(sources) < GRAPH_MIN_SOURCES:
            try:
                fallback_k = 15 - len(sources)
                fallback_sources = self._vector_store.search(
                    query=question, k=fallback_k, score_threshold=0.1
                )
                # 去重合并
                existing_contents = {
                    (s["file_name"], s["page_content"]) for s in sources
                }
                for fs in fallback_sources:
                    if (fs["file_name"], fs["page_content"]) not in existing_contents:
                        sources.append(fs)
                        existing_contents.add((fs["file_name"], fs["page_content"]))
            except Exception:
                logger.exception("Vector store fallback search failed")

        # 注入已有故障树上下文（支持多轮修改同一棵树）
        existing_tree_context = self._fault_tree_skill.get_existing_tree_context(
            conversation.id
        )

        system_content = SYSTEM_PROMPT + existing_tree_context

        context_result = None
        if self._context_manager:
            try:
                # 将 system prompt（含故障树 skill prompt）token 数传入，
                # 确保 budget 评估时为不可压缩的故障树 prompt 预留空间。
                system_prompt_tokens = max(1, len(system_content) // 2)
                context_result = self._context_manager.prepare_context(
                    question=question,
                    conversation_rounds=conversation.rounds,
                    seed_names=seed_names,
                    graph_paths=graph_paths,
                    sources=sources,
                    config=self._context_config,
                    system_prompt_tokens=system_prompt_tokens,
                )
                seed_names = context_result.seed_names
                graph_paths = context_result.graph_paths
                sources = context_result.sources
                context = context_result.context
                logger.debug(
                    "Context prepared: actions=%s, tokens=%s, sources=%d, paths=%d",
                    ",".join(context_result.budget_actions) or "none",
                    context_result.prompt_token_estimate,
                    len(sources),
                    len(graph_paths),
                )
            except Exception:
                logger.exception("Context manager preparation failed, fallback to legacy flow")

        if context_result is None:
            # 回退：保留现有上下文组装逻辑
            context = self._build_enhanced_context(seed_names, graph_paths, sources)

        yield {"type": "sources", "sources": sources}

        messages: list[dict] = [{"role": "system", "content": system_content}]

        if context_result is not None:
            # 新流程：历史装配由 Context Manager 统一编排
            messages.extend(context_result.history_messages)
            user_content = context_result.user_content or question
        else:
            # 回退：沿用现有最近 N 轮历史拼装
            recent_rounds = conversation.rounds[-MAX_HISTORY_ROUNDS:]
            for r in recent_rounds:
                messages.append({"role": "user", "content": r.question})
                messages.append({"role": "assistant", "content": r.answer})

            if context:
                user_content = f"{question}\n\nContext:\n{context}"
            else:
                user_content = question

        messages.append({"role": "user", "content": user_content})

        # 4. 判断故障树意图
        #    精确匹配（生成/修改等动词）→ 直接 function calling，跳过 LLM 分析
        #    宽泛匹配（提到故障树）    → LLM 分析 + 后台 function calling 并行
        generate_match = _FAULT_TREE_GENERATE_PATTERN.search(question)
        update_match = _FAULT_TREE_UPDATE_PATTERN.search(question)
        mention_match = _FAULT_TREE_MENTION_PATTERN.search(question)
        is_direct_fault_tree = bool(generate_match or update_match)
        is_fault_tree_request = is_direct_fault_tree or bool(mention_match)

        full_answer = ""
        fault_tree_id: str | None = None

        def _persist_round() -> None:
            chat_round = ChatRound(
                question=question,
                prompt=user_content,
                answer=full_answer,
                sources=sources,
                fault_tree_id=fault_tree_id,
            )
            self._conversation_repo.add_round(conversation.id, chat_round)
            logger.info("Chat round saved for conversation: %s", conversation.id)

        if is_fault_tree_request:
            # 前端依赖该事件展示“故障树加载中”状态卡片。
            yield {"type": "generating_tree"}

            # 构建带工具指令的 messages，供 function calling 使用
            tool_instruction = (
                "用户要求修改已有故障树。请调用 update_fault_tree 工具。要求：\n"
                "1. 在已有故障树基础上进行修改，返回修改后的完整结构。\n"
                "2. 保留未被用户要求修改的部分，仅变更用户指定的内容。\n"
                "3. 确保修改后的结构仍然完整合理，无悬空节点或断裂的连接关系。"
                if update_match
                else
                "用户要求生成故障树。请调用 generate_fault_tree 工具。要求：\n"
                "1. name 使用顶层故障事件作为名称。\n"
                "2. 节点 id 按层级编号（如顶层 n1，门 g1/g2，子事件 n2/n3/n4）。\n"
                "3. 事件节点 label 用简洁的故障描述，门节点 label 留空。\n"
                "4. 确保每个逻辑门至少连接 2 个子节点，结构完整无悬空节点。\n"
                "5. 结合上下文中的文档信息构建故障原因链，优先使用文档中提到的故障模式。"
            )
            tool_messages = messages.copy()
            tool_messages[0] = {
                "role": "system",
                "content": f"{system_content}\n\n{tool_instruction}",
            }

            # function calling 生成故障树
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
                        logger.info("Fault tree generated: %s (id=%s)", ft.name, ft.id)
                    else:
                        logger.warning(
                            "Fault tree intent detected but model did not call a tool: %s",
                            question,
                        )
                except Exception:
                    logger.exception("Fault tree generation failed")
                finally:
                    async_done.set()

            # ── 统一流程：LLM 自然语言分析 + 后台 function calling 并行 ──
            # 不论精确匹配还是宽泛匹配，都保证回复同时包含「文字说明 + 故障树」。
            thread = threading.Thread(target=_generate_fault_tree_async, daemon=True)
            thread.start()

            if update_match:
                stream_task_desc = (
                    "用户要求修改已有故障树，故障树将自动更新并附加在回复末尾。\n"
                    "你的任务是用自然语言说明本次修改的思路，请遵循以下要求：\n"
                    "1. 简要说明本次修改的目标与改动点（哪些节点/连接被增删改）。\n"
                    "2. 如果上下文文档中有相关信息，引用关键内容辅助说明。\n"
                    "3. 严禁输出 JSON、代码块或任何故障树数据结构。\n"
                    "4. 不必逐一罗列节点和连接，故障树图会自动展示。\n"
                    "5. 如果信息不够充分，在末尾提出补充问题引导用户。"
                )
            elif is_direct_fault_tree:
                stream_task_desc = (
                    "用户要求生成故障树，故障树将自动生成并附加在回复末尾。\n"
                    "你的任务是用自然语言进行故障分析说明，请遵循以下要求：\n"
                    "1. 简要分析故障场景、可能的故障原因及其逻辑关系。\n"
                    "2. 如果上下文文档中有相关信息，引用关键内容辅助分析。\n"
                    "3. 严禁输出 JSON、代码块或任何故障树数据结构。\n"
                    "4. 不必描述节点和连接的具体结构，故障树图会自动展示。\n"
                    "5. 如果信息不够充分，在末尾提出补充问题引导用户。"
                )
            else:
                stream_task_desc = (
                    "用户提到了故障树相关内容，故障树将自动生成并附加在回复末尾。\n"
                    "你的任务是用自然语言进行分析说明，请遵循以下要求：\n"
                    "1. 简要分析故障场景、可能的故障原因及其逻辑关系。\n"
                    "2. 如果上下文文档中有相关信息，引用关键内容辅助分析。\n"
                    "3. 严禁输出 JSON、代码块或任何故障树数据结构。\n"
                    "4. 不必描述节点和连接的具体结构，故障树图会自动展示。\n"
                    "5. 如果信息不够充分，在末尾提出补充问题引导用户。"
                )

            stream_system = f"{system_content}\n\n{stream_task_desc}"
            stream_messages = messages.copy()
            stream_messages[0] = {"role": "system", "content": stream_system}

            try:
                for token in self._llm.stream_chat(stream_messages):
                    full_answer += token
                    yield {"type": "token", "content": token}
            except Exception:
                logger.exception("LLM stream failed during fault tree request")
                async_done.wait(timeout=self._fault_tree_wait_timeout_seconds)
                if fault_tree_container[0] is not None:
                    fault_tree_id = fault_tree_container[0].id
                    yield {"type": "fault_tree", "fault_tree": fault_tree_container[0].to_dict()}
                _persist_round()
                yield {"type": "error", "message": "LLM service error"}
                return

            # 等待故障树后台线程完成
            async_done.wait(timeout=self._fault_tree_wait_timeout_seconds)

            if fault_tree_container[0] is not None:
                fault_tree_id = fault_tree_container[0].id
                yield {"type": "fault_tree", "fault_tree": fault_tree_container[0].to_dict()}
            else:
                err_msg = "\n\n（故障树生成失败，请重试。）"
                full_answer += err_msg
                yield {"type": "token", "content": err_msg}
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
        _persist_round()

        if self._expert_learning:
            self._expert_learning.index_conversation_round(
                conversation_id=conversation.id,
                question=question,
                answer=full_answer,
            )

        done_event = {
            "type": "done",
            "conversation_id": conversation.id,
            "answer": full_answer,
        }
        if fault_tree_id:
            done_event["fault_tree_id"] = fault_tree_id

        yield done_event

    def _build_enhanced_context(
        self,
        seed_names: list[str],
        graph_paths: list[dict],
        sources: list[dict],
    ) -> str:
        parts = []

        # 图谱上下文（若有）
        if seed_names or graph_paths:
            if seed_names:
                parts.append(f"【关联实体】\n{', '.join(seed_names)}")
            if graph_paths:
                path_lines = "\n".join(
                    f"  - {p['from']} --[{p['relation']}]--> {p['to']}"
                    for p in graph_paths[:20]
                )
                parts.append(f"【知识图谱路径】\n{path_lines}")

        # 原文片段
        if sources:
            chunk_text = "\n\n".join(
                f"[{s.get('file_name', 'Unknown')}]\n{s['page_content']}" for s in sources
            )
            parts.append(f"【相关原文片段】\n{chunk_text}")

        return "\n\n".join(parts)


