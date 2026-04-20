import json
import logging
from Backend.Domain.Entities.fault_tree import FaultTree, FaultTreeNode, FaultTreeEdge
from Backend.Domain.Common.Enums.FaultTreeEnums import NodeType, GateType
from Backend.Application.Interfaces.IFaultTreeRepository import IFaultTreeRepository
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository

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
                "一定要在每个节点后有原文的引用来源(sources)，"
                "故障树由事件节点(event)和逻辑门节点(gate)以及连接边组成。"
                "顶层事件是根节点，通过逻辑门(AND/OR/XOR/INHIBIT/PRIORITY_AND)连接到下层事件。"
                "生成故障树时，请为每个事件节点的 sources 字段标注内容依据："
                "仅引用本次检索上下文中实际提供的文档片段，"
                "选取相关度最高的1~3个片段作为来源，"
                "必须为所有子节点添加来源，且来源必须真实存在于检索结果中。"
                "file_name 必须与检索结果中的文件名完全一致，"
                "page_content 截取相关的句子，"
                "逻辑门节点无需填写 sources。"
                "需要填写remark字段时，请简要说明该节点的特殊含义或与用户描述的关系。"
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
                                    "enum": ["AND", "OR", "XOR", "INHIBIT", "PRIORITY_AND"],
                                    "description": "逻辑门类型，仅当 node_type 为 gate 时需要",
                                },
                                "remark": {
                                    "type": "string",
                                    "description": "节点备注信息，可选",
                                },
                                "sources": {
                                    "type": "array",
                                    "description": "支撑该节点内容的文档来源，仅引用检索上下文中实际存在的文档",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "file_name": {
                                                "type": "string",
                                                "description": "文档文件名",
                                            },
                                            "page_content": {
                                                "type": "string",
                                                "description": "相关原文片段",
                                            },
                                        },
                                        "required": ["file_name", "page_content"],
                                    },
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
                                    "enum": ["AND", "OR", "XOR", "INHIBIT", "PRIORITY_AND"],
                                    "description": "逻辑门类型，仅 gate 节点需要",
                                },
                                "remark": {"type": "string", "description": "备注信息"},
                                "sources": {
                                    "type": "array",
                                    "description": "支撑该节点内容的文档来源，仅引用检索上下文中实际存在的文档",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "file_name": {
                                                "type": "string",
                                                "description": "文档文件名",
                                            },
                                            "page_content": {
                                                "type": "string",
                                                "description": "相关原文片段（不超过200字）",
                                            },
                                        },
                                        "required": ["file_name", "page_content"],
                                    },
                                },
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
    def __init__(
        self,
        fault_tree_repository: IFaultTreeRepository,
        conversation_repository: IConversationRepository | None = None,
    ):
        self._repo = fault_tree_repository
        self._conversation_repo = conversation_repository

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
                sources=n.get("sources", []),
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
        self._link_latest_round_if_needed(fault_tree)
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
            self._link_latest_round_if_needed(existing)
            logger.info("Fault tree updated: %s (id=%s)", name, existing.id)
            return existing
        else:
            # 没有已有树，创建新的
            return self._generate(arguments, conversation_id)

    def _link_latest_round_if_needed(self, tree: FaultTree) -> None:
        """兜底：故障树成功落库后，尝试回填到最近一轮未绑定故障树的对话记录。"""
        if self._conversation_repo is None:
            return
        if not tree.conversation_id:
            return

        try:
            linked = self._conversation_repo.link_latest_round_fault_tree(
                tree.conversation_id,
                tree.id,
            )
            if linked:
                logger.info(
                    "Fault tree linked to latest round: tree_id=%s, conversation_id=%s",
                    tree.id,
                    tree.conversation_id,
                )
        except Exception:
            logger.exception(
                "Failed to link fault tree to latest round: tree_id=%s, conversation_id=%s",
                tree.id,
                tree.conversation_id,
            )

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
