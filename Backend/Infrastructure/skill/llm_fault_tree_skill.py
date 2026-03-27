"""LlmFaultTreeSkill — 基于 LLM 的故障树生成 Skill。

通过 LLM 分析对话历史，提取故障现象、原因、条件等关键信息，
识别因果关系和层次结构，构建多层故障树。
"""
from __future__ import annotations

import json
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from Backend.Application.Interfaces.fault_tree_skill import FaultTreeGenerationSkill
from Backend.Domain.Common.Enums.gate_type import GateType
from Backend.Domain.Common.Enums.message_role import MessageRole
from Backend.Domain.Entities.diagnosis_session import DiagnosisSession
from Backend.Domain.Entities.fault_tree import (
    FaultTree,
    FaultTreeEdge,
    FaultTreeNode,
    NODE_TYPE_EVENT,
    NODE_TYPE_GATE,
)

logger = logging.getLogger(__name__)

# ---- JSON 输出格式示例（嵌入到 Prompt 中） ----

_OUTPUT_EXAMPLE = """\
{
  "top_event": "发动机无法启动",
  "sub_trees": [
    {
      "gate_type": "OR",
      "intermediate_event": "燃油系统故障",
      "remark": "依据: 维修手册第3章-燃油供给系统常见故障",
      "children": [
        {"type": "basic", "label": "燃油泵损坏", "remark": "依据: 用户描述供油压力不足; 手册P45故障码F-012"},
        {"type": "basic", "label": "燃油滤清器堵塞", "remark": "依据: 运行超5000小时未更换滤芯"}
      ]
    },
    {
      "gate_type": "AND",
      "intermediate_event": "电气系统故障",
      "remark": "依据: 对话中提到蓄电池老化且点火异常，两者需同时存在",
      "children": [
        {"type": "basic", "label": "蓄电池电量不足", "remark": "依据: 用户测量电压低于10V"},
        {
          "type": "intermediate",
          "gate_type": "OR",
          "intermediate_event": "点火系统异常",
          "remark": "依据: 手册第5章-点火系统故障排查树",
          "children": [
            {"type": "basic", "label": "火花塞积碳", "remark": "依据: 用户反馈冷启动困难"},
            {"type": "basic", "label": "点火线圈故障", "remark": "依据: 高压测试无火花"}
          ]
        }
      ]
    }
  ]
}"""


class LlmFaultTreeSkill(FaultTreeGenerationSkill):
    """基于 LLM 的故障树生成 Skill。

    分析完整对话历史，提取故障信息并构建多层故障树。
    """

    _GENERATE_SYSTEM = (
        "你是一名遵循 IEC 61025 标准的故障树分析(FTA)高级工程师。\n"
        "你的任务是根据诊断对话历史和其中引用的知识库信息，"
        "提取故障事件、事件关联关系和逻辑门规则，构建一棵结构完整的多层故障树。\n\n"
        "## 核心原则\n"
        "1. 知识驱动: 优先从对话中助手引用的知识库文档、设备手册、维修记录中提取故障关联关系，"
        "而非凭空推测。每个事件节点的 remark 字段必须注明信息来源(溯源依据)。\n"
        "2. 严格遵循 FTA 规范: 故障树必须呈现清晰的 顶事件(故障现象) -> 中间事件(过渡原因) -> 底事件(根本原因) 逻辑传导路径。\n\n"
        "## 故障树结构规则\n"
        "1. 顶事件(Top Event): 对话中描述的主要故障现象，用简洁专业术语概括(如 电机异常振动、液压系统失压)\n"
        "2. 中间事件(Intermediate Event): 按子系统或故障类别分类的过渡原因(如 机械子系统故障、电气子系统故障、润滑系统异常)，"
        "应体现设备结构层次\n"
        "3. 底事件/基本事件(Basic Event): 不可再分解的根本原因(如 轴承磨损、密封圈老化、电源电压波动)，"
        "必须是可直接检测或更换的具体部件/参数异常\n"
        "4. 逻辑门选择:\n"
        "   - OR门: 子事件中任意一个发生即可导致父事件(多个独立的可能原因)\n"
        "   - AND门: 所有子事件必须同时发生才导致父事件(多因素耦合故障)\n"
        "   选择依据: 根据对话中描述的故障触发条件判断——"
        "若用户说'A或B都可能导致'用OR; 若说'只有A和B同时出现才会'用AND\n"
        "5. 结构深度: 至少 3 层(顶事件->中间事件->底事件)，复杂故障应构建 4 层及以上\n"
        "6. 结构宽度: 每个逻辑门下至少 2 个子事件，同层分支数建议 2-5 个\n"
        "7. 完整性: 对话中提及的所有故障现象、原因、条件都应体现在树中，不得遗漏\n\n"
        "## 溯源依据要求(remark 字段)\n"
        "每个事件节点的 remark 必须标注信息来源，格式示例:\n"
        "- 来自用户描述: '依据: 用户反馈负载超80%%时振动加剧'\n"
        "- 来自知识库: '依据: 知识库-XX设备维修手册第3章'\n"
        "- 来自助手诊断: '依据: 助手分析指出轴承温度85度超出正常范围'\n"
        "- 来自专业推断: '依据: FTA经验-轴承润滑不足通常伴随温升异常'\n"
        "remark 不得为空字符串。\n\n"
        "## 逻辑校验(生成前自检)\n"
        "生成故障树前请自行校验:\n"
        "- 无循环关联: 不存在 A->B->...->A 的环路\n"
        "- 无逻辑冲突: 同一事件不能同时作为原因和结果出现在不同位置\n"
        "- 事件不重复: 同一故障原因只出现一次\n"
        "- 门类型合理: AND/OR 选择有对话依据支撑\n\n"
        "## 输出格式\n"
        "只返回一个合法 JSON 对象，不要包含任何其他文字或 markdown 标记。\n"
        "格式如下:\n"
        "{output_example}\n\n"
        "### 字段说明\n"
        "- top_event: 顶事件标签(简洁专业术语)\n"
        "- sub_trees: 数组，每项代表顶事件下的一个子树分支\n"
        "  - gate_type: OR 或 AND\n"
        "  - intermediate_event: 中间事件标签\n"
        "  - remark: 溯源依据(该中间事件的信息来源)\n"
        "  - children: 数组，每项为基本事件或嵌套的中间事件\n"
        "    - type: basic 或 intermediate\n"
        "    - label: 事件标签(专业术语)\n"
        "    - remark: 溯源依据(不得为空)\n"
        "    - 如果 type 为 intermediate，还需包含 gate_type, intermediate_event, remark, children\n"
    )

    _GENERATE_PROMPT = ChatPromptTemplate.from_messages([
        ("system", _GENERATE_SYSTEM),
        ("human",
         "以下是诊断对话历史:\n\n{conversation}\n\n"
         "请根据以上对话，生成故障树 JSON。"),
    ])

    _MISSING_SYSTEM = (
        "你是一名故障诊断助手，正在辅助构建故障树(FTA)。\n"
        "请根据以下诊断对话历史，判断信息是否足以构建一棵结构准确的故障树。\n\n"
        "构建故障树至少需要以下信息:\n"
        "1. 故障现象: 主要故障表现(作为顶事件)\n"
        "2. 故障原因: 至少 2 种可能的故障原因或子系统异常(作为中间/底事件)\n"
        "3. 触发条件: 故障发生的工况、操作步骤或环境条件\n"
        "4. 因果关系: 原因之间的逻辑关系(独立OR？耦合AND？)\n\n"
        "如有缺失，请列出最关键的缺失项(最多 3 条)，引导用户补充。\n\n"
        '只返回一个 JSON 对象，格式: {{"missing": ["缺失信息1", "缺失信息2"]}}\n'
        '如果信息已足够，返回: {{"missing": []}}\n'
        "不要输出其他任何内容。"
    )

    _MISSING_INFO_PROMPT = ChatPromptTemplate.from_messages([
        ("system", _MISSING_SYSTEM),
        ("human", "对话历史:\n{conversation}"),
    ])

    def __init__(self, llm: ChatOpenAI, min_user_messages: int = 2) -> None:
        self._llm = llm
        self.min_user_messages = min_user_messages

    def generate(self, session: DiagnosisSession) -> FaultTree | None:
        user_messages = [m for m in session.messages if m.role == MessageRole.USER]
        if len(user_messages) < self.min_user_messages:
            return None

        # 构建对话文本
        conversation = self._format_conversation(session)

        # 调用 LLM 生成故障树 JSON
        chain = self._GENERATE_PROMPT | self._llm
        result = chain.invoke({
            "output_example": _OUTPUT_EXAMPLE,
            "conversation": conversation,
        })

        # 解析 LLM 输出
        tree_json = self._parse_llm_json(result.content)
        if tree_json is None:
            logger.warning("LLM 返回的故障树 JSON 解析失败: %s", result.content[:200])
            return None

        # 从 JSON 构建 FaultTree 领域对象
        tree = self._build_tree_from_json(tree_json, session.id)
        if tree is None:
            return None

        errors = tree.validate_structure()
        if errors:
            logger.warning("生成的故障树校验失败: %s", errors)
            return None

        return tree

    def get_missing_info(self, session: DiagnosisSession) -> list[str]:
        user_messages = [m for m in session.messages if m.role == MessageRole.USER]
        if len(user_messages) < self.min_user_messages:
            return [
                "请补充故障现象的具体表现（例如报错、噪音、停机方式）",
                "请补充触发条件（例如温度、负载、操作步骤、出现频率）",
                "请补充已尝试的排查动作及结果",
            ]

        conversation = self._format_conversation(session)
        chain = self._MISSING_INFO_PROMPT | self._llm
        result = chain.invoke({"conversation": conversation})

        try:
            parsed = self._parse_llm_json(result.content)
            if parsed and isinstance(parsed.get("missing"), list):
                return [str(item) for item in parsed["missing"] if item]
        except Exception:
            pass

        return []

    # ---- 内部方法 ----

    @staticmethod
    def _format_conversation(session: DiagnosisSession) -> str:
        """将会话消息格式化为文本。"""
        lines = []
        for m in session.messages:
            role_label = "用户" if m.role == MessageRole.USER else "助手"
            lines.append(f"[{role_label}]: {m.content}")
        return "\n".join(lines)

    @staticmethod
    def _parse_llm_json(text: str) -> dict | None:
        """从 LLM 输出中提取 JSON，容忍 markdown 代码块包裹。"""
        content = text.strip()
        # 去掉 markdown 代码块
        if content.startswith("```"):
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _build_tree_from_json(data: dict, session_id: str) -> FaultTree | None:
        """将 LLM 返回的 JSON 转换为 FaultTree 领域对象。"""
        try:
            nodes: list[FaultTreeNode] = []
            edges: list[FaultTreeEdge] = []
            counter = _Counter()

            # 顶事件
            top_label = data.get("top_event", "系统故障")
            top_id = counter.next_event()
            nodes.append(FaultTreeNode(id=top_id, type=NODE_TYPE_EVENT, label=top_label))

            sub_trees = data.get("sub_trees", [])
            if not sub_trees:
                return None

            # 顶事件下的逻辑门（汇总所有子树分支）
            top_gate_type = GateType.OR if len(sub_trees) > 1 else GateType.AND
            top_gate_id = counter.next_gate()
            nodes.append(FaultTreeNode(
                id=top_gate_id, type=NODE_TYPE_GATE, gate_type=top_gate_type,
            ))
            edges.append(FaultTreeEdge(
                id=counter.next_edge(), source=top_id, target=top_gate_id,
            ))

            # 递归构建每个子树
            for branch in sub_trees:
                _build_branch(branch, top_gate_id, nodes, edges, counter)

            return FaultTree.create(
                name="故障树",
                description="由 LLM 基于诊断对话自动生成",
                session_id=session_id,
                nodes=nodes,
                edges=edges,
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("构建故障树失败: %s", exc)
            return None


def _build_branch(
    branch: dict,
    parent_gate_id: str,
    nodes: list[FaultTreeNode],
    edges: list[FaultTreeEdge],
    counter: _Counter,
) -> None:
    """递归构建子树分支。"""
    node_type = branch.get("type", "intermediate")

    if node_type == "basic":
        # 基本事件（叶子）
        evt_id = counter.next_event()
        nodes.append(FaultTreeNode(
            id=evt_id,
            type=NODE_TYPE_EVENT,
            label=branch.get("label", "未知事件"),
            remark=branch.get("remark", ""),
        ))
        edges.append(FaultTreeEdge(
            id=counter.next_edge(), source=parent_gate_id, target=evt_id,
        ))
    else:
        # 中间事件 → 逻辑门 → 子节点
        inter_id = counter.next_event()
        inter_label = branch.get("intermediate_event", branch.get("label", "中间事件"))
        inter_remark = branch.get("remark", "")
        nodes.append(FaultTreeNode(
            id=inter_id, type=NODE_TYPE_EVENT, label=inter_label,
            remark=inter_remark,
        ))
        edges.append(FaultTreeEdge(
            id=counter.next_edge(), source=parent_gate_id, target=inter_id,
        ))

        # 该中间事件下的逻辑门
        gate_str = branch.get("gate_type", "OR").upper()
        gate_type = GateType(gate_str) if gate_str in GateType.__members__ else GateType.OR
        gate_id = counter.next_gate()
        nodes.append(FaultTreeNode(
            id=gate_id, type=NODE_TYPE_GATE, gate_type=gate_type,
        ))
        edges.append(FaultTreeEdge(
            id=counter.next_edge(), source=inter_id, target=gate_id,
        ))

        # 递归处理 children
        for child in branch.get("children", []):
            _build_branch(child, gate_id, nodes, edges, counter)


class _Counter:
    """自增 ID 生成器。"""

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
