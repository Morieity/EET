from __future__ import annotations

from Backend.Application.Interfaces.fault_tree_skill import FaultTreeGenerationSkill
from Backend.Domain.Common.Enums.gate_type import GateType
from Backend.Domain.Common.Enums.message_role import MessageRole
from Backend.Domain.Entities.diagnosis_session import ChatMessage, DiagnosisSession
from Backend.Domain.Entities.fault_tree import (
    FaultTree,
    FaultTreeEdge,
    FaultTreeNode,
    NODE_TYPE_EVENT,
    NODE_TYPE_GATE,
)


class StubFaultTreeSkill(FaultTreeGenerationSkill):
    """示例 Skill：基于会话消息构造一棵多层故障树。

    生成结构示例（3 层）：
        顶事件 → OR门 → 中间事件1 → AND门 → 基本事件A, 基本事件B
                      → 中间事件2 → OR门  → 基本事件C, 基本事件D
    """

    def __init__(self, min_user_messages: int = 2) -> None:
        self.min_user_messages = min_user_messages

    def generate(self, session: DiagnosisSession) -> FaultTree | None:
        user_messages = [m for m in session.messages if m.role == MessageRole.USER]
        if len(user_messages) < self.min_user_messages:
            return None

        nodes: list[FaultTreeNode] = []
        edges: list[FaultTreeEdge] = []
        counter = _IdCounter()

        # 1. 顶事件
        top_label = self._build_top_event_label(user_messages[-1].content)
        top_id = counter.next_event()
        nodes.append(FaultTreeNode(id=top_id, type=NODE_TYPE_EVENT, label=top_label))

        # 2. 将用户消息按层分组，递归构建子树
        groups = self._group_messages(user_messages)
        self._build_subtree(
            parent_event_id=top_id,
            groups=groups,
            nodes=nodes,
            edges=edges,
            counter=counter,
        )

        tree = FaultTree.create(
            name="示例故障树",
            description="由 StubFaultTreeSkill 基于对话自动生成（多层结构）",
            session_id=session.id,
            nodes=nodes,
            edges=edges,
        )

        errors = tree.validate_structure()
        return tree if not errors else None

    def get_missing_info(self, session: DiagnosisSession) -> list[str]:
        user_messages = [m for m in session.messages if m.role == MessageRole.USER]
        if len(user_messages) >= self.min_user_messages:
            return []

        return [
            "请补充故障现象的具体表现（例如报错、噪音、停机方式）",
            "请补充触发条件（例如温度、负载、操作步骤、出现频率）",
            "请补充已尝试的排查动作及结果",
        ]

    # ---- 递归建树核心 ----

    def _build_subtree(
        self,
        parent_event_id: str,
        groups: list[list[ChatMessage]],
        nodes: list[FaultTreeNode],
        edges: list[FaultTreeEdge],
        counter: _IdCounter,
    ) -> None:
        """为一个父事件节点构建子树。

        groups 的长度决定本层分支数；当某分支仍可再分时递归产生中间层。
        """
        gate_type = GateType.OR if len(groups) > 1 else GateType.AND
        gate_id = counter.next_gate()
        nodes.append(FaultTreeNode(id=gate_id, type=NODE_TYPE_GATE, gate_type=gate_type))
        edges.append(FaultTreeEdge(
            id=counter.next_edge(),
            source=parent_event_id,
            target=gate_id,
        ))

        for group in groups:
            if len(group) == 1:
                # 叶子：直接作为基本事件
                basic_id = counter.next_event()
                label = self._snippet(group[0].content, prefix="可能原因：", max_len=18)
                nodes.append(FaultTreeNode(id=basic_id, type=NODE_TYPE_EVENT, label=label))
                edges.append(FaultTreeEdge(
                    id=counter.next_edge(),
                    source=gate_id,
                    target=basic_id,
                ))
            else:
                # 中间事件 → 递归
                inter_id = counter.next_event()
                label = self._snippet(group[0].content, prefix="中间事件：", max_len=20)
                nodes.append(FaultTreeNode(id=inter_id, type=NODE_TYPE_EVENT, label=label))
                edges.append(FaultTreeEdge(
                    id=counter.next_edge(),
                    source=gate_id,
                    target=inter_id,
                ))
                sub_groups = self._split_group(group)
                self._build_subtree(inter_id, sub_groups, nodes, edges, counter)

    # ---- 消息分组 ----

    @staticmethod
    def _group_messages(user_messages: list[ChatMessage]) -> list[list[ChatMessage]]:
        """将用户消息分组。每 2 条一组，至少产生 2 组以保证树的宽度。"""
        msgs = user_messages[-6:]  # 最多取最近 6 条
        if len(msgs) <= 1:
            return [msgs]
        groups: list[list[ChatMessage]] = []
        for i in range(0, len(msgs), 2):
            groups.append(msgs[i : i + 2])
        return groups

    @staticmethod
    def _split_group(group: list[ChatMessage]) -> list[list[ChatMessage]]:
        """将一个中间分组继续拆分为更小的子组（递归终止条件：每组 1 条）。"""
        return [[m] for m in group]

    # ---- 文本工具 ----

    @staticmethod
    def _build_top_event_label(last_message: str) -> str:
        normalized = " ".join(last_message.split())
        if not normalized:
            return "系统故障"
        return f"故障：{normalized[:24]}"

    @staticmethod
    def _snippet(text: str, prefix: str = "", max_len: int = 20) -> str:
        normalized = " ".join(text.split())
        body = normalized[:max_len] if normalized else "未知"
        return f"{prefix}{body}"


class _IdCounter:
    """为节点和边生成唯一且可读的自增 ID。"""

    def __init__(self) -> None:
        self._event = 0
        self._gate = 0
        self._edge = 0

    def next_event(self) -> str:
        self._event += 1
        return f"n_evt_{self._event}"

    def next_gate(self) -> str:
        self._gate += 1
        return f"n_gate_{self._gate}"

    def next_edge(self) -> str:
        self._edge += 1
        return f"e_{self._edge}"