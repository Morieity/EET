import logging
import threading
from typing import Any
from langchain_core.documents import Document
from Backend.Application.Interfaces.ILLMService import ILLMService
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.IGraphRepository import IGraphRepository
from Backend.Application.Interfaces.ITripleExtractor import ITripleExtractor
from Backend.Application.Interfaces.IFaultTreeRepository import IFaultTreeRepository
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository

logger = logging.getLogger(__name__)

EXPERT_DIAGNOSIS_SYSTEM = (
    "你是一位工业设备故障诊断专家。"
    "你的任务是从专家对故障树的修改中提炼可学习的诊断知识。"
    "只输出报告正文，不要输出 JSON 或额外说明。"
)

EXPERT_DIAGNOSIS_USER = """以下是一次专家对故障树的人工修改，请生成“专家修改学习报告”，并重点解释“改了什么、为何而改、在什么条件下改”。

输出要求：
1. 修改场景与故障背景
2. 关键修改点（新增/删除/重命名节点、逻辑门变化、连接变化）
3. 修改意图与适用条件（什么故障现象、什么上下文下进行此修改）
4. 对诊断路径和排查优先级的影响
5. 可复用的经验规则（给后续类似问题直接参考）

故障树名称：{name}

修改前故障树：
{before_tree}

修改后故障树：
{after_tree}

变更摘要：
{change_summary}

{conversation_context}
"""


class ExpertLearningUseCase:
    def __init__(
        self,
        llm_service: ILLMService,
        vector_store_repository: IVectorStoreRepository,
        graph_repository: IGraphRepository,
        triple_extractor: ITripleExtractor,
        fault_tree_repository: IFaultTreeRepository,
        conversation_repository: IConversationRepository,
    ):
        self._llm = llm_service
        self._vector_store = vector_store_repository
        self._graph = graph_repository
        self._triple_extractor = triple_extractor
        self._fault_tree_repo = fault_tree_repository
        self._conversation_repo = conversation_repository

    def learn_from_fault_tree_async(
        self,
        tree_id: str,
        before_tree: dict[str, Any] | None = None,
        after_tree: dict[str, Any] | None = None,
        update_payload: dict[str, Any] | None = None,
    ) -> None:
        """PUT 接口调用后触发，后台异步执行，不阻塞响应。"""
        t = threading.Thread(
            target=self._learn_from_fault_tree,
            args=(tree_id, before_tree, after_tree, update_payload),
            daemon=True,
        )
        t.start()

    def _learn_from_fault_tree(
        self,
        tree_id: str,
        before_tree: dict[str, Any] | None = None,
        after_tree: dict[str, Any] | None = None,
        update_payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            latest_tree = self._fault_tree_repo.get_by_id(tree_id)
            if latest_tree is None and after_tree is None:
                logger.warning("ExpertLearning: 找不到故障树 %s", tree_id)
                return

            after_snapshot = after_tree or (latest_tree.to_dict() if latest_tree else {})
            before_snapshot = before_tree or {}

            tree_name = str(after_snapshot.get("name") or "未命名故障树")
            before_tree_text = self._render_tree_snapshot(before_snapshot)
            after_tree_text = self._render_tree_snapshot(after_snapshot)
            change_summary = self._summarize_changes(
                before_tree=before_snapshot,
                after_tree=after_snapshot,
                update_payload=update_payload,
            )
            conversation_context = self._build_conversation_context(after_snapshot.get("conversation_id"))

            prompt = EXPERT_DIAGNOSIS_USER.format(
                name=tree_name,
                before_tree=before_tree_text,
                after_tree=after_tree_text,
                change_summary=change_summary,
                conversation_context=conversation_context,
            )
            messages = [
                {"role": "system", "content": EXPERT_DIAGNOSIS_SYSTEM},
                {"role": "user", "content": prompt},
            ]

            expert_text = ""
            for token in self._llm.stream_chat(messages):
                expert_text += token

            expert_text = expert_text.strip()
            if not expert_text:
                logger.warning("ExpertLearning: LLM 返回空内容，跳过 tree_id=%s", tree_id)
                return

            source_name = f"expert_modification_{tree_id}"
            learning_text = self._build_learning_text(
                tree_name=tree_name,
                before_tree_text=before_tree_text,
                after_tree_text=after_tree_text,
                change_summary=change_summary,
                expert_text=expert_text,
            )

            doc = Document(
                page_content=learning_text,
                metadata={
                    "file_name": source_name,
                    "type": "expert_modification_learning",
                    "tree_id": tree_id,
                },
            )
            self._vector_store.add_documents(source_name, [doc])
            logger.info("ExpertLearning: 修改学习文本已写入向量库，source=%s", source_name)

            # 显式触发一次知识图谱构建，抽取源文本改为“修改摘要 + 专家解释”。
            triples = self._triple_extractor.extract(learning_text, source_file=source_name)
            if triples:
                self._graph.add_triples(triples)
                self._graph.save()
                self._upsert_graph_vectors(triples, source_name)
                logger.info("ExpertLearning: 写入 %d 条三元组到图谱", len(triples))

        except Exception:
            logger.exception("ExpertLearning: learn_from_fault_tree 失败，tree_id=%s", tree_id)

    def index_conversation_round(
        self, conversation_id: str, question: str, answer: str
    ) -> None:
        """每轮对话结束后调用，后台异步写入向量库。"""
        t = threading.Thread(
            target=self._index_round,
            args=(conversation_id, question, answer),
            daemon=True,
        )
        t.start()

    def _index_round(self, conversation_id: str, question: str, answer: str) -> None:
        try:
            source_name = f"conversation_{conversation_id}"
            content = f"问题：{question}\n\n回答：{answer}"
            doc = Document(
                page_content=content,
                metadata={
                    "file_name": source_name,
                    "type": "conversation_history",
                    "conversation_id": conversation_id,
                },
            )
            self._vector_store.add_documents(source_name, [doc])
            logger.info("ExpertLearning: 对话轮次已写入向量库，conversation_id=%s", conversation_id)
        except Exception:
            logger.exception(
                "ExpertLearning: index_conversation_round 失败，conversation_id=%s",
                conversation_id,
            )

    @staticmethod
    def _render_tree_snapshot(tree_snapshot: dict[str, Any]) -> str:
        if not tree_snapshot:
            return "- (无快照)"

        nodes = tree_snapshot.get("nodes") or []
        edges = tree_snapshot.get("edges") or []

        node_lines = []
        for node in nodes:
            node_id = node.get("id", "")
            node_type = node.get("node_type", "")
            label = node.get("label", "")
            gate_type = node.get("gate_type", "")
            remark = node.get("remark", "")

            line = f"- {node_id} [{node_type}] {label}"
            if gate_type:
                line += f"（逻辑门: {gate_type}）"
            if remark:
                line += f" 备注: {remark}"
            node_lines.append(line)

        edge_lines = [
            f"- {edge.get('source_id', '')} -> {edge.get('target_id', '')}"
            for edge in edges
        ]

        node_text = "\n".join(node_lines) if node_lines else "- (无节点)"
        edge_text = "\n".join(edge_lines) if edge_lines else "- (无连接)"
        return f"节点：\n{node_text}\n\n连接：\n{edge_text}"

    def _summarize_changes(
        self,
        before_tree: dict[str, Any],
        after_tree: dict[str, Any],
        update_payload: dict[str, Any] | None = None,
    ) -> str:
        before_nodes = {n.get("id", ""): n for n in before_tree.get("nodes") or []}
        after_nodes = {n.get("id", ""): n for n in after_tree.get("nodes") or []}

        before_edges = {
            (e.get("source_id", ""), e.get("target_id", ""))
            for e in (before_tree.get("edges") or [])
        }
        after_edges = {
            (e.get("source_id", ""), e.get("target_id", ""))
            for e in (after_tree.get("edges") or [])
        }

        added_nodes = [nid for nid in after_nodes if nid and nid not in before_nodes]
        removed_nodes = [nid for nid in before_nodes if nid and nid not in after_nodes]

        modified_nodes = []
        for nid in (set(before_nodes) & set(after_nodes)):
            b = before_nodes[nid]
            a = after_nodes[nid]
            changed_fields = []
            for field in ("label", "node_type", "gate_type", "remark"):
                if (b.get(field) or "") != (a.get(field) or ""):
                    changed_fields.append(field)
            if changed_fields:
                modified_nodes.append((nid, changed_fields))

        added_edges = after_edges - before_edges
        removed_edges = before_edges - after_edges

        lines = [
            f"- 节点新增: {len(added_nodes)} 个",
            f"- 节点删除: {len(removed_nodes)} 个",
            f"- 节点修改: {len(modified_nodes)} 个",
            f"- 连接新增: {len(added_edges)} 条",
            f"- 连接删除: {len(removed_edges)} 条",
        ]

        if added_nodes:
            lines.append("- 新增节点ID: " + ", ".join(sorted(added_nodes)))
        if removed_nodes:
            lines.append("- 删除节点ID: " + ", ".join(sorted(removed_nodes)))
        if modified_nodes:
            changed_detail = "; ".join(
                f"{nid}({','.join(fields)})" for nid, fields in sorted(modified_nodes)
            )
            lines.append("- 变更字段: " + changed_detail)

        if added_edges:
            edge_text = ", ".join(sorted(f"{s}->{t}" for s, t in added_edges))
            lines.append("- 新增连接: " + edge_text)
        if removed_edges:
            edge_text = ", ".join(sorted(f"{s}->{t}" for s, t in removed_edges))
            lines.append("- 删除连接: " + edge_text)

        if update_payload:
            payload_keys = [k for k in update_payload.keys() if k not in {"nodes", "edges"}]
            if payload_keys:
                lines.append("- 用户补充字段: " + ", ".join(sorted(payload_keys)))

        return "\n".join(lines)

    @staticmethod
    def _build_learning_text(
        tree_name: str,
        before_tree_text: str,
        after_tree_text: str,
        change_summary: str,
        expert_text: str,
    ) -> str:
        return (
            "【专家修改学习记录】\n"
            f"故障树：{tree_name}\n\n"
            "【修改摘要】\n"
            f"{change_summary}\n\n"
            "【修改前故障树】\n"
            f"{before_tree_text}\n\n"
            "【修改后故障树】\n"
            f"{after_tree_text}\n\n"
            "【专家解释】\n"
            f"{expert_text}"
        )

    def _upsert_graph_vectors(self, triples: list, source_file: str) -> None:
        add_entity = getattr(self._vector_store, "add_entity", None)
        add_relation = getattr(self._vector_store, "add_relation", None)
        if not callable(add_entity) or not callable(add_relation):
            return

        try:
            seen_entities = set()
            for triple in triples:
                if triple.head and triple.head not in seen_entities:
                    add_entity(triple.head, triple.head_type, source_file=source_file)
                    seen_entities.add(triple.head)
                if triple.tail and triple.tail not in seen_entities:
                    add_entity(triple.tail, triple.tail_type, source_file=source_file)
                    seen_entities.add(triple.tail)

                if triple.head and triple.relation and triple.tail:
                    add_relation(
                        triple.head,
                        triple.relation,
                        triple.tail,
                        source_file=source_file,
                    )
        except Exception:
            # 这里采用降级策略，避免图谱向量索引失败影响主流程。
            logger.exception("ExpertLearning: graph_entities/relations 写入失败，source=%s", source_file)

    def _build_conversation_context(self, conversation_id: str | None) -> str:
        if not conversation_id:
            return ""

        conversation = self._conversation_repo.get_by_id(conversation_id)
        if not conversation or not conversation.rounds:
            return ""

        recent_rounds = conversation.rounds[-3:]
        qa_text = "\n".join(f"Q: {r.question}\nA: {r.answer}" for r in recent_rounds)
        return f"参考对话上下文：\n{qa_text}"