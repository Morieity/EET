import json
import logging
from Backend.Domain.Entities.fault_tree import FaultTree, FaultTreeNode, FaultTreeEdge
from Backend.Domain.Common.Enums.FaultTreeEnums import NodeType, GateType
from Backend.Application.Interfaces.IFaultTreeRepository import IFaultTreeRepository

logger = logging.getLogger(__name__)

# OpenAI-compatible function/tool definitions
FAULT_TREE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_fault_tree",
            "description": (
                "根据用户描述和文档上下文生成或更新一棵故障树。"
                "当用户要求生成故障树、分析故障原因、构建故障分析模型时调用此工具。"
                "故障树由事件节点(event)和逻辑门节点(gate)以及连接边组成。"
                "顶层事件是根节点，通过逻辑门(AND/OR)连接到下层事件。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "故障树名称，通常为顶层故障事件名称，如'发动机故障'",
                    },
                    "nodes": {
                        "type": "array",
                        "description": "故障树节点列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "节点唯一标识，如 n1, n2, g1 等",
                                },
                                "label": {
                                    "type": "string",
                                    "description": "节点显示名称，事件节点填写故障事件名称，门节点可为空",
                                },
                                "node_type": {
                                    "type": "string",
                                    "enum": ["event", "gate"],
                                    "description": "节点类型：event(故障事件) 或 gate(逻辑门)",
                                },
                                "gate_type": {
                                    "type": "string",
                                    "enum": ["AND", "OR"],
                                    "description": "逻辑门类型，仅当 node_type 为 gate 时需要",
                                },
                                "remark": {
                                    "type": "string",
                                    "description": "节点备注信息，可选",
                                },
                            },
                            "required": ["id", "label", "node_type"],
                        },
                    },
                    "edges": {
                        "type": "array",
                        "description": "故障树连接边列表，表示父子关系（从上层指向下层）",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "边唯一标识",
                                },
                                "source_id": {
                                    "type": "string",
                                    "description": "源节点ID（上层节点）",
                                },
                                "target_id": {
                                    "type": "string",
                                    "description": "目标节点ID（下层节点）",
                                },
                            },
                            "required": ["id", "source_id", "target_id"],
                        },
                    },
                },
                "required": ["name", "nodes", "edges"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_fault_tree",
            "description": (
                "修改当前对话中已有的故障树。当用户要求对已有故障树进行增删改节点、"
                "修改连接关系、重命名等操作时调用此工具。需提供完整的修改后的故障树结构。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "故障树名称（可修改）",
                    },
                    "nodes": {
                        "type": "array",
                        "description": "修改后的完整节点列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "节点唯一标识"},
                                "label": {"type": "string", "description": "节点显示名称"},
                                "node_type": {
                                    "type": "string",
                                    "enum": ["event", "gate"],
                                    "description": "节点类型",
                                },
                                "gate_type": {
                                    "type": "string",
                                    "enum": ["AND", "OR"],
                                    "description": "逻辑门类型，仅 gate 节点需要",
                                },
                                "remark": {"type": "string", "description": "备注信息"},
                            },
                            "required": ["id", "label", "node_type"],
                        },
                    },
                    "edges": {
                        "type": "array",
                        "description": "修改后的完整边列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "边唯一标识"},
                                "source_id": {"type": "string", "description": "源节点ID"},
                                "target_id": {"type": "string", "description": "目标节点ID"},
                            },
                            "required": ["id", "source_id", "target_id"],
                        },
                    },
                },
                "required": ["name", "nodes", "edges"],
            },
        },
    },
]


class FaultTreeSkill:
    def __init__(self, fault_tree_repository: IFaultTreeRepository):
        self._repo = fault_tree_repository

    @property
    def tools(self) -> list[dict]:
        return FAULT_TREE_TOOLS

    def execute(
        self,
        function_name: str,
        arguments: dict,
        conversation_id: str | None = None,
    ) -> FaultTree:
        """执行 function call，返回生成或更新后的 FaultTree 实体。"""
        if function_name == "generate_fault_tree":
            return self._generate(arguments, conversation_id)
        elif function_name == "update_fault_tree":
            return self._update(arguments, conversation_id)
        else:
            raise ValueError(f"Unknown function: {function_name}")

    def _parse_tree_data(self, arguments: dict) -> tuple[str, list[FaultTreeNode], list[FaultTreeEdge]]:
        """从 function call 参数解析故障树结构。"""
        name = arguments.get("name") or "未命名故障树"
        nodes = []
        for n in arguments.get("nodes", []):
            gate_type = GateType(n["gate_type"]) if n.get("gate_type") else None
            node = FaultTreeNode(
                node_id=n["id"],
                label=n.get("label", ""),
                node_type=NodeType(n.get("node_type", "event")),
                gate_type=gate_type,
                remark=n.get("remark", ""),
            )
            nodes.append(node)

        edges = []
        for e in arguments.get("edges", []):
            edge = FaultTreeEdge(
                edge_id=e["id"],
                source_id=e["source_id"],
                target_id=e["target_id"],
            )
            edges.append(edge)

        return name, nodes, edges

    def _generate(self, arguments: dict, conversation_id: str | None) -> FaultTree:
        """生成新的故障树。"""
        name, nodes, edges = self._parse_tree_data(arguments)
        fault_tree = FaultTree(
            name=name,
            nodes=nodes,
            edges=edges,
            conversation_id=conversation_id,
        )
        self._repo.save(fault_tree)
        logger.info("Fault tree generated: %s (id=%s)", name, fault_tree.id)
        return fault_tree

    def _update(self, arguments: dict, conversation_id: str | None) -> FaultTree:
        """更新当前对话关联的故障树。"""
        existing = None
        if conversation_id:
            existing = self._repo.get_by_conversation_id(conversation_id)

        name, nodes, edges = self._parse_tree_data(arguments)

        if existing:
            existing.name = name
            existing.nodes = nodes
            existing.edges = edges
            self._repo.update(existing)
            logger.info("Fault tree updated: %s (id=%s)", name, existing.id)
            return existing
        else:
            # 没有已有树，创建新的
            return self._generate(arguments, conversation_id)

    def get_existing_tree_context(self, conversation_id: str | None) -> str:
        """获取当前对话中已有的故障树描述，用于注入到 LLM 上下文中。"""
        if not conversation_id:
            return ""
        tree = self._repo.get_by_conversation_id(conversation_id)
        if not tree:
            return ""
        return (
            f"\n\n[当前对话已有故障树]\n"
            f"名称: {tree.name}\n"
            f"节点: {json.dumps([n.to_dict() for n in tree.nodes], ensure_ascii=False)}\n"
            f"边: {json.dumps([e.to_dict() for e in tree.edges], ensure_ascii=False)}\n"
            f"如果用户要求修改此故障树，请使用 update_fault_tree 工具并提供修改后的完整结构。\n"
            f"如果用户要求生成一棵新的故障树（与当前主题无关），请使用 generate_fault_tree 工具。\n"
        )
