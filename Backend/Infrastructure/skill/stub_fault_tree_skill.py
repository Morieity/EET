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
    """示例 Skill：基于会话消息构造一棵可用的最小故障树。"""

    # 实现一个具体案例
    def __init__(self, min_user_messages: int = 2) -> None:
        self.min_user_messages = min_user_messages

    # def generate(self, session: DiagnosisSession) -> FaultTree | None:
    #     user_messages = [m for m in session.messages if m.role == MessageRole.USER]
    #     if len(user_messages) < self.min_user_messages:
    #         return None

    #     top_event_label = self._build_top_event_label(user_messages[-1].content)
    #     basic_events = self._build_basic_event_labels(user_messages)

    #     nodes = [
    #         FaultTreeNode(id="n_top", type=NODE_TYPE_EVENT, label=top_event_label),
    #         FaultTreeNode(id="n_gate_1", type=NODE_TYPE_GATE, gate_type=GateType.OR),
    #     ]
    #     edges = [
    #         FaultTreeEdge(id="e_top_gate", source="n_top", target="n_gate_1"),
    #     ]

    #     for index, label in enumerate(basic_events, start=1):
    #         node_id = f"n_basic_{index}"
    #         edge_id = f"e_gate_basic_{index}"
    #         nodes.append(FaultTreeNode(id=node_id, type=NODE_TYPE_EVENT, label=label))
    #         edges.append(FaultTreeEdge(id=edge_id, source="n_gate_1", target=node_id))

    #     tree = FaultTree.create(
    #         name="示例故障树",
    #         description="由 StubFaultTreeSkill 基于对话自动生成",
    #         session_id=session.id,
    #         nodes=nodes,
    #         edges=edges,
    #     )

    #     return tree if not tree.validate_structure() else None

    # def get_missing_info(self, session: DiagnosisSession) -> list[str]:
    #     user_messages = [m for m in session.messages if m.role == MessageRole.USER]
    #     if len(user_messages) >= self.min_user_messages:
    #         return []

    #     return [
    #         "请补充故障现象的具体表现（例如报错、噪音、停机方式）",
    #         "请补充触发条件（例如温度、负载、操作步骤、出现频率）",
    #         "请补充已尝试的排查动作及结果",
    #     ]

    # @staticmethod
    # def _build_top_event_label(last_message: str) -> str:
    #     normalized = " ".join(last_message.split())
    #     if not normalized:
    #         return "系统故障"
    #     snippet = normalized[:24]
    #     return f"故障：{snippet}"

    # @staticmethod
    # def _build_basic_event_labels(user_messages: list[ChatMessage]) -> list[str]:
    #     labels: list[str] = []
    #     for msg in user_messages[-3:]:
    #         content = " ".join(msg.content.split())
    #         if content:
    #             labels.append(f"可能原因：{content[:18]}")

    #     if not labels:
    #         labels = ["可能原因：传感器异常", "可能原因：电源波动"]

    #     return labels
