"""生成项目介绍 PPT (.pptx)。

风格约束：
- 纯黑白灰 + 单一深蓝主色，不使用五颜六色
- 无花哨动画、无渐变背景
- 字体：中文宋体，英文/数字 Times New Roman，代码 Consolas
"""

from __future__ import annotations

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml
from lxml import etree
import copy

# ---------------------------------------------------------------------------
# 颜色常量
# ---------------------------------------------------------------------------
C_BLACK   = RGBColor(0x1A, 0x1A, 0x1A)
C_DARK    = RGBColor(0x1F, 0x38, 0x64)   # 深蓝（主色）
C_MID     = RGBColor(0x44, 0x44, 0x44)   # 深灰
C_LIGHT   = RGBColor(0x88, 0x88, 0x88)   # 浅灰
C_RULE    = RGBColor(0xCC, 0xCC, 0xCC)   # 分隔线灰
C_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
C_BG_HEAD = RGBColor(0x1F, 0x38, 0x64)   # 表头深蓝
C_BG_ALT  = RGBColor(0xF2, 0xF2, 0xF2)   # 表格交替行浅灰

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

CJK  = "宋体"
LATIN = "Times New Roman"
MONO  = "Consolas"


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _set_font(run, size: float, bold=False, italic=False,
              color: RGBColor = C_BLACK, mono=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = MONO if mono else LATIN
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("a:latin"))
    if rFonts is None:
        rFonts = etree.SubElement(rPr, qn("a:latin"))
    rFonts.set("typeface", MONO if mono else LATIN)
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = etree.SubElement(rPr, qn("a:ea"))
    ea.set("typeface", MONO if mono else CJK)


def _para_align(para, align):
    para.alignment = align


def add_textbox(slide, left, top, width, height, text, size=18,
                bold=False, italic=False, color=C_BLACK,
                align=PP_ALIGN.LEFT, mono=False, word_wrap=True):
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = word_wrap
    para = tf.paragraphs[0]
    para.alignment = align
    run = para.add_run()
    run.text = text
    _set_font(run, size, bold=bold, italic=italic, color=color, mono=mono)
    return txBox


def add_line(slide, left, top, width, color=C_RULE, thickness=Pt(1)):
    """水平分隔线"""
    line = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.LINE — 用矩形模拟
        Inches(left), Inches(top), Inches(width), Emu(0)
    )
    line.width = Inches(width)
    line.height = Emu(1)
    line.line.color.rgb = color
    line.line.width = thickness
    line.fill.background()
    return line


def add_rect(slide, left, top, width, height, fill: RGBColor, line_color=None):
    rect = slide.shapes.add_shape(
        1, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    rect.fill.solid()
    rect.fill.fore_color.rgb = fill
    if line_color:
        rect.line.color.rgb = line_color
        rect.line.width = Pt(0.5)
    else:
        rect.line.fill.background()
    return rect


def add_rect_text(slide, left, top, width, height, text,
                  fill: RGBColor, text_color: RGBColor = C_WHITE,
                  size=11, bold=False, align=PP_ALIGN.CENTER):
    rect = add_rect(slide, left, top, width, height, fill)
    tf = rect.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    para.alignment = align
    # 垂直居中
    from pptx.enum.text import MSO_ANCHOR
    tf.auto_size = None
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    run = para.add_run()
    run.text = text
    _set_font(run, size, bold=bold, color=text_color)
    return rect


def slide_header(slide, title: str, subtitle: str = ""):
    """每页统一页眉：左侧深蓝标题条"""
    add_rect(slide, 0, 0, 13.33, 1.0, C_DARK)
    add_textbox(slide, 0.4, 0.12, 10, 0.75, title,
                size=26, bold=True, color=C_WHITE)
    if subtitle:
        add_textbox(slide, 0.4, 0.62, 10, 0.4, subtitle,
                    size=13, italic=True, color=RGBColor(0xCC, 0xD6, 0xEA))
    # 页码（右上）
    add_textbox(slide, 12.2, 0.18, 1.0, 0.6, "",
                size=11, color=C_WHITE, align=PP_ALIGN.RIGHT)


def bullet_block(slide, left, top, width, items: list[tuple[str, int]],
                 base_size=13, line_gap=0.38):
    """
    items: [(text, level), ...]  level=0 一级，1 二级
    返回实际高度（英寸）
    """
    y = top
    for text, level in items:
        indent = left + level * 0.35
        prefix = "•  " if level == 0 else "–  "
        color = C_MID if level == 0 else C_LIGHT
        sz = base_size if level == 0 else base_size - 1
        add_textbox(slide, indent, y, width - level * 0.35, line_gap + 0.05,
                    prefix + text, size=sz, color=color)
        y += line_gap
    return y - top


def add_table(slide, left, top, width, col_widths: list[float],
              rows_data: list[list[str]], header_row: list[str] | None = None,
              font_size=11):
    """手动用矩形拼表格，精确控制样式"""
    row_h = 0.42
    y = top

    def _row(cells, bg, fg, bold_first=False, size=font_size):
        x = left
        for i, (cell, cw) in enumerate(zip(cells, col_widths)):
            add_rect(slide, x, y, cw, row_h, bg,
                     line_color=RGBColor(0xBB, 0xBB, 0xBB))
            bold = bold_first and i == 0
            add_textbox(slide, x + 0.08, y + 0.05, cw - 0.1, row_h - 0.05,
                        cell, size=size, bold=bold, color=fg)
            x += cw

    if header_row:
        _row(header_row, C_BG_HEAD, C_WHITE, size=font_size, bold_first=False)
        y += row_h

    for ri, row in enumerate(rows_data):
        bg = C_BG_ALT if ri % 2 == 0 else C_WHITE
        _row(row, bg, C_MID, bold_first=True)
        y += row_h

    return y - top  # 实际高度


# ---------------------------------------------------------------------------
# 幻灯片内容
# ---------------------------------------------------------------------------

def slide_cover(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    # 深蓝背景上半部分
    add_rect(slide, 0, 0, 13.33, 4.5, C_DARK)
    # 项目名
    add_textbox(slide, 1.0, 1.0, 11.0, 1.2,
                "工业故障诊断 RAG 系统",
                size=40, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_textbox(slide, 1.0, 2.3, 11.0, 0.7,
                "基于轻量化知识图谱与上下文智能编排的问答平台",
                size=18, italic=True,
                color=RGBColor(0xCC, 0xD6, 0xEA), align=PP_ALIGN.CENTER)
    # 下半部分关键词
    add_textbox(slide, 0, 4.7, 13.33, 0.5,
                "整洁架构  ·  GraphRAG  ·  上下文管理  ·  故障树生成  ·  SSE 流式输出",
                size=13, color=C_LIGHT, align=PP_ALIGN.CENTER)
    # 横线
    add_rect(slide, 0, 4.5, 13.33, 0.04, C_RULE)


def slide_overview(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide_header(slide, "项目概览", "解决什么问题，怎么解决")

    add_textbox(slide, 0.5, 1.2, 12.5, 0.45,
                "背景与痛点", size=15, bold=True, color=C_DARK)
    bullet_block(slide, 0.5, 1.65, 12.0, [
        ("工业设备故障排查依赖专家经验，知识分散在大量文档、工单与历史记录中，检索效率低", 0),
        ("传统向量 RAG 无法利用实体关系进行多跳推理，复杂故障链路难以覆盖", 0),
        ("长上下文场景下 Prompt 拼装无序，导致 LLM 注意力稀释、回答质量下降", 0),
    ], base_size=13)

    add_textbox(slide, 0.5, 3.3, 12.5, 0.45,
                "解决方案", size=15, bold=True, color=C_DARK)
    bullet_block(slide, 0.5, 3.75, 12.0, [
        ("向量检索 + 知识图谱双引擎：语义相似性与结构关系推理互补", 0),
        ("轻量化 GraphRAG：NetworkX 内存图 + ChromaDB，无外部图数据库依赖", 0),
        ("上下文智能编排：7 个算法模块（MMR、重排、路径剪枝、Token 预算、历史分层等）", 0),
        ("故障树自动生成：Function Calling 驱动，多轮修改，图结构持久化", 0),
    ], base_size=13)


def slide_architecture(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide_header(slide, "系统整体架构", "整洁架构 · 四层分离 · 依赖倒置")

    # 四层架构框
    layers = [
        ("Web 层",            "Flask Blueprint · REST API · SSE 流式输出 · CORS",       C_DARK),
        ("Application 层",    "UseCase 编排 · Interface 契约 · 上下文管理 · DI 装配",    RGBColor(0x2E, 0x55, 0x9E)),
        ("Domain 层",         "Triple · EntityType · RelationType · 业务实体 · 枚举",    RGBColor(0x4A, 0x86, 0xC8)),
        ("Infrastructure 层", "SQLite · ChromaDB · NetworkX · LLM 客户端 · 文件系统",   RGBColor(0x6B, 0xA3, 0xD9)),
    ]
    y = 1.15
    for label, desc, color in layers:
        add_rect(slide, 0.5, y, 2.2, 0.72, color)
        add_textbox(slide, 0.55, y + 0.15, 2.1, 0.45,
                    label, size=13, bold=True, color=C_WHITE)
        add_rect(slide, 2.72, y, 10.1, 0.72,
                 RGBColor(0xF5, 0xF7, 0xFA),
                 line_color=RGBColor(0xCC, 0xCC, 0xCC))
        add_textbox(slide, 2.85, y + 0.15, 9.8, 0.45,
                    desc, size=12, color=C_MID)
        y += 0.85

    # 右侧标注
    add_rect(slide, 0.5, y + 0.1, 12.32, 0.04, C_RULE)
    add_textbox(slide, 0.5, y + 0.25, 12.5, 0.4,
                "依赖方向：Web → Application → Domain   ←   Infrastructure（依赖倒置，Infrastructure 依赖 Domain 接口）",
                size=11, italic=True, color=C_LIGHT)

    # 数据流说明
    add_textbox(slide, 0.5, 5.5, 12.5, 0.4,
                "查询流：用户请求 → Endpoint → UseCase → Repository（Interface）→ Infrastructure 实现 → LLM / DB",
                size=11, color=C_MID)
    add_textbox(slide, 0.5, 5.9, 12.5, 0.4,
                "建图流：文件上传 → ImportFileUseCase → TripleExtractor（异步）→ NetworkX + ChromaDB",
                size=11, color=C_MID)


def slide_kg(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide_header(slide, "轻量化知识图谱", "Schema 定向抽取 · 向量 + 图双引擎 · 无外部图数据库")

    # 左列：设计原则
    add_textbox(slide, 0.5, 1.15, 5.8, 0.4,
                "四大设计原则", size=14, bold=True, color=C_DARK)
    principles = [
        ("拒绝重型图数据库", "NetworkX 内存图 + JSON 持久化，零运维"),
        ("Schema 定向抽取",  "8 类实体 × 8 类关系，封闭类型空间"),
        ("向量 + 图融合",    "ChromaDB 语义寻点 + BFS 拓扑扩展"),
        ("异步建图",         "建图失败不影响向量检索可用性"),
    ]
    y = 1.6
    for title, desc in principles:
        add_rect(slide, 0.5, y, 0.08, 0.28, C_DARK)
        add_textbox(slide, 0.7, y, 2.5, 0.28, title, size=12, bold=True, color=C_MID)
        add_textbox(slide, 0.7, y + 0.28, 5.5, 0.28, desc, size=11, color=C_LIGHT)
        y += 0.65

    # 右列：查询两阶段
    add_textbox(slide, 7.0, 1.15, 6.0, 0.4,
                "在线查询：两阶段检索", size=14, bold=True, color=C_DARK)
    stages = [
        ("① 向量寻点",  "graph_entities 集合 → Top-20 种子实体\n（相似度阈值 0.85，emb L2 距离转换）"),
        ("② BFS 扩展",  "以种子实体为起点，广度优先 2 跳展开\nG_sub(S,h) = {(u,r,v)∈E : d_G(s,u)≤h}"),
        ("③ 路径剪枝",  "按置信度过滤 + 关系类型多样性优先\n输出上限 max_graph_paths = 20"),
    ]
    y = 1.6
    for label, desc in stages:
        add_rect(slide, 7.0, y, 5.8, 0.9,
                 RGBColor(0xF0, 0xF4, 0xFA),
                 line_color=RGBColor(0xBB, 0xCC, 0xDD))
        add_textbox(slide, 7.15, y + 0.05, 2.0, 0.35,
                    label, size=12, bold=True, color=C_DARK)
        add_textbox(slide, 7.15, y + 0.38, 5.5, 0.5,
                    desc, size=10, color=C_MID)
        y += 1.02

    # 底部论文来源
    add_rect(slide, 0.5, 5.6, 12.33, 0.04, C_RULE)
    add_textbox(slide, 0.5, 5.7, 12.5, 0.4,
                "参考论文：LightRAG (2024) · HippoRAG (2024) · PathRAG (arXiv:2502.14902) · "
                "Query-Driven GraphRAG (2025) · GraphRAG-Microsoft (arXiv:2404.16130)",
                size=10, italic=True, color=C_LIGHT)


def slide_entity_relation(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide_header(slide, "知识图谱数据模型", "三元组 · 实体类型 · 关系类型")

    add_textbox(slide, 0.5, 1.15, 12.5, 0.35,
                "三元组定义：τ = (h, r, t)，其中 h, t ∈ E（实体集合），r ∈ R（关系集合）",
                size=13, color=C_MID)

    # 实体类型表
    add_textbox(slide, 0.5, 1.65, 6.0, 0.35,
                "实体类型（EntityType）", size=13, bold=True, color=C_DARK)
    add_table(slide, 0.5, 2.05, 6.0,
              [2.2, 1.4, 2.4],
              [
                  ["COMPONENT",  "组件",     "传感器、驱动板等硬件组件"],
                  ["SYMPTOM",    "故障现象", "电流突变、过载报警等"],
                  ["ERROR_CODE", "错误码",   "系统输出的错误编号"],
                  ["SOLUTION",   "解决方案", "针对故障的处理措施"],
                  ["DEVICE",     "设备",     "组件所属的上层设备"],
                  ["FAULT_MODE", "失效模式", "故障的发生模式与类别"],
                  ["WORK_ORDER", "工单",     "维修过程记录实体"],
                  ["CAUSE",      "根因",     "故障的根本原因"],
              ],
              header_row=["枚举值", "含义", "示例"],
              font_size=10)

    # 关系类型表
    add_textbox(slide, 7.0, 1.65, 6.0, 0.35,
                "关系类型（RelationType）", size=13, bold=True, color=C_DARK)
    add_table(slide, 7.0, 2.05, 6.2,
              [2.4, 1.4, 2.4],
              [
                  ["CAUSES",        "引发",         "组件/根因引发故障现象"],
                  ["BELONGS_TO",    "属于",         "组件属于某设备"],
                  ["RESOLVES",      "解决",         "方案解决某故障"],
                  ["DIAGNOSES",     "排查",         "错误码排查某组件"],
                  ["HAS_FAULT",     "设备存在故障", "设备存在失效模式"],
                  ["ROOT_CAUSE_OF", "根因对应故障", "根因导致失效模式"],
                  ["TREATED_BY",    "由措施处理",   "故障由方案处理"],
                  ["RECORDED_IN",   "记录于工单",   "记录于维修工单"],
              ],
              header_row=["枚举值", "含义", "说明"],
              font_size=10)


def slide_context_mgmt(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide_header(slide, "上下文管理与 Prompt 编排", "7 算法模块 · 确定性流水线 · Token 预算控制")

    add_textbox(slide, 0.5, 1.15, 12.5, 0.35,
                "编排公式：Prompt = System + History + UserContent（关联实体 + KG路径 + 原文片段 + 问题）",
                size=13, color=C_MID)

    # 编排流程（纵向流）
    steps = [
        ("① PathPruning",       "置信度过滤 + 精确去重 + 关系类型多样性裁剪",   "min_confidence=0.4  max_paths=20"),
        ("② MMRDeduplication",  "Maximal Marginal Relevance 选择检索片段",      "λ=0.7  top_k=15"),
        ("③ RetrievalReorder",  "首尾交替放置，利用注意力边界效应",              "高相关→首位，次高→末位"),
        ("④ TokenBudgeting",    "计算利用率 ρ，产出分级压缩动作列表",            "ρ>0.6 / 0.8 / 0.9 三级触发"),
        ("⑤ HistoryTiering",   "对话历史分冷/温/热三层，热层原样保留",          "hot=3轮  warm=7轮"),
        ("⑥ QueryAwareCompress","查询感知抽取式压缩，保留领域相关句子",          "keep_rate=0.5  min_chars=160"),
    ]
    y = 1.6
    for i, (label, desc, param) in enumerate(steps):
        bg = RGBColor(0xF0, 0xF4, 0xFA) if i % 2 == 0 else C_WHITE
        add_rect(slide, 0.5, y, 12.33, 0.58, bg,
                 line_color=RGBColor(0xCC, 0xCC, 0xCC))
        add_textbox(slide, 0.65, y + 0.08, 2.8, 0.4,
                    label, size=12, bold=True, color=C_DARK)
        add_textbox(slide, 3.55, y + 0.08, 5.8, 0.4,
                    desc, size=11, color=C_MID)
        add_textbox(slide, 9.4, y + 0.08, 3.3, 0.4,
                    param, size=10, italic=True, color=C_LIGHT, mono=True)
        y += 0.6

    add_rect(slide, 0.5, y + 0.05, 12.33, 0.04, C_RULE)
    add_textbox(slide, 0.5, y + 0.15, 12.5, 0.35,
                "参考论文：Long-Context LLMs Meet RAG (ICLR 2025) · MemAgent (2025) · "
                "LongLLMLingua · LLMLingua-2 · Retrieval Head (arXiv:2404.15574)",
                size=10, italic=True, color=C_LIGHT)


def slide_chat_fault(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide_header(slide, "对话系统与故障树", "多轮问答 · SSE 流式 · Function Calling 生成故障树")

    # 左：对话系统
    add_textbox(slide, 0.5, 1.15, 6.0, 0.38,
                "多轮对话系统", size=14, bold=True, color=C_DARK)
    bullet_block(slide, 0.5, 1.6, 6.0, [
        ("SSE 流式协议：token 逐字推送，sources/done/error 事件", 0),
        ("五类 SSE 事件：conversation · sources · token · done · error", 1),
        ("完整检索链路：向量寻点 → BFS 发散 → 上下文编排 → LLM", 0),
        ("历史对话持久化：SQLite + 分层摘要，支持长期记忆", 0),
        ("专家学习：对话轮次异步索引到向量库与知识图谱", 0),
    ], base_size=12)

    add_line(slide, 6.8, 1.15, 0.04, color=C_RULE, thickness=Pt(1))

    # 右：故障树
    add_textbox(slide, 7.1, 1.15, 6.0, 0.38,
                "故障树自动生成", size=14, bold=True, color=C_DARK)
    bullet_block(slide, 7.1, 1.6, 6.0, [
        ("Function Calling 驱动：LLM 调用预定义工具生成/修改树", 0),
        ("工具集：create_fault_tree · add_node · add_edge · delete_node", 1),
        ("图结构存储：三表设计（fault_trees / nodes / edges）", 0),
        ("多轮修改：同一会话内持续修改同一棵树", 0),
        ("两套接口：聊天流式接口 + REST CRUD 接口", 0),
    ], base_size=12)

    # 底部流程图
    add_rect(slide, 0.5, 5.3, 12.33, 0.04, C_RULE)
    add_textbox(slide, 0.5, 5.45, 12.5, 0.35,
                "对话流：用户输入 → ChatUseCase → 检索编排 → LLM 推理 → SSE 流式输出 → 前端渲染",
                size=11, color=C_MID)
    add_textbox(slide, 0.5, 5.85, 12.5, 0.35,
                "故障树流：用户描述故障 → FaultTreeUseCase → Function Calling → 图结构写入 → 前端可视化",
                size=11, color=C_MID)


def slide_storage(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide_header(slide, "存储架构", "SQLite · ChromaDB · NetworkX · 本地文件系统")

    add_table(slide, 0.5, 1.2, 12.33,
              [2.2, 2.2, 4.0, 3.93],
              [
                  ["SQLite",      "关系型元数据",  "files · conversations · chat_rounds · fault_trees / nodes / edges",
                   "WAL 模式并发优化，threading.local 连接隔离"],
                  ["ChromaDB",    "向量存储",      "rag_docs · graph_entities · graph_relations",
                   "L2 距离转相似度分数，支持元数据过滤"],
                  ["NetworkX",    "知识图谱",      "DiGraph 内存图，JSON 持久化至 db/knowledge_graph.json",
                   "BFS 2 跳扩展，MAX_EDGES_PER_NODE=20 剪枝"],
                  ["本地文件系统", "原始文档",      "uploads/ 目录，格式：PDF/TXT/DOCX/MD 等",
                   "文档三阶段加载：读取 → 切分 → 向量化"],
              ],
              header_row=["存储组件", "类型", "存储内容", "关键策略"],
              font_size=10)

    # 一致性策略
    add_textbox(slide, 0.5, 4.95, 12.5, 0.38,
                "一致性策略", size=13, bold=True, color=C_DARK)
    bullet_block(slide, 0.5, 5.38, 12.0, [
        ("文件删除时同步清理：rag_docs + graph_entities + graph_relations + NetworkX 边 + 孤立节点 + 磁盘文件 + 元数据记录", 0),
        ("向量化异步执行：文件状态机（PENDING → EMBEDDED），建图失败自动降级，不阻塞在线查询", 0),
    ], base_size=12)


def slide_stack(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide_header(slide, "技术栈与工程亮点", "核心依赖 · 关键工程决策")

    # 左：技术栈
    add_textbox(slide, 0.5, 1.15, 5.8, 0.38,
                "核心技术栈", size=14, bold=True, color=C_DARK)
    add_table(slide, 0.5, 1.6, 6.0,
              [2.2, 3.8],
              [
                  ["后端框架",  "Python · Flask · Blueprint"],
                  ["向量数据库", "ChromaDB（嵌入式持久化）"],
                  ["图计算",    "NetworkX（内存 DiGraph）"],
                  ["关系数据库", "SQLite（WAL 并发）"],
                  ["LLM 接入",  "OpenAI 兼容接口（DeepSeek/Qwen 等）"],
                  ["嵌入模型",  "BAAI/bge-small-zh-v1.5（约 130 MB）"],
                  ["文档处理",  "LangChain Document Loaders"],
                  ["前端",      "React · SSE · 组件化"],
              ],
              font_size=11)

    # 右：工程亮点
    add_textbox(slide, 7.0, 1.15, 6.0, 0.38,
                "工程亮点", size=14, bold=True, color=C_DARK)
    bullet_block(slide, 7.0, 1.6, 6.2, [
        ("整洁架构：四层严格分离，依赖倒置，可独立替换任意技术组件", 0),
        ("确定性编排：相同输入输出严格可复现，便于 A/B 测试", 0),
        ("降级保护：图构建失败自动降级为纯向量 RAG", 0),
        ("无外部重型依赖：不需要 Neo4j / Elasticsearch / Redis", 0),
        ("CPU 友好：嵌入模型约 130 MB，全链路无 GPU 强依赖", 0),
        ("可观测性：budget_actions + budget_plan 随响应返回", 0),
        ("增量更新：按文件增量添加/删除知识，无需全量重建", 0),
    ], base_size=12, line_gap=0.42)


def slide_papers(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide_header(slide, "论文支撑", "17 篇前沿研究 · 每个算法有文献来源")

    add_table(slide, 0.5, 1.2, 12.33,
              [3.2, 2.8, 6.33],
              [
                  ["Long-Context LLMs Meet RAG",   "ICLR 2025 · arXiv:2410.05983",  "MMR 去重 · 检索重排 · Token 预算分区"],
                  ["Retrieval Head",                "arXiv:2404.15574",               "注意力头首尾敏感性 → 重排 + 查询末置"],
                  ["GraphRAG (Microsoft)",          "arXiv:2404.16130",               "路径多样性策略（PathPruningAlgorithm）"],
                  ["PathRAG",                       "arXiv:2502.14902",               "关系路径剪枝，MAX_EDGES_PER_NODE"],
                  ["LightRAG",                      "Guo et al., 2024",               "三层 Collection 分层存储设计"],
                  ["HippoRAG",                      "2024",                           "向量寻点 + 图拓扑扩展两阶段检索"],
                  ["MemAgent",                      "arXiv:2507.02259",               "历史分层（冷/温/热三层）"],
                  ["LongLLMLingua / LLMLingua-2",  "arXiv:2310.06839 / 2403.12968",  "查询感知抽取式压缩"],
                  ["Long Context vs. RAG",          "arXiv:2501.01880",               "Token 预算分配与历史压缩"],
                  ["Query-Driven GraphRAG",         "2025",                           "异步增量建图，无全局离线图构建"],
              ],
              header_row=["论文", "来源", "在本系统中的体现"],
              font_size=10)


def slide_summary(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide_header(slide, "总结", "核心价值与后续方向")

    add_textbox(slide, 0.5, 1.15, 12.5, 0.38,
                "核心价值", size=14, bold=True, color=C_DARK)
    bullet_block(slide, 0.5, 1.6, 12.0, [
        ("向量 RAG + 知识图谱双引擎，覆盖语义检索与多跳关系推理两类需求", 0),
        ("轻量化设计：无重型外部依赖，CPU 即可运行，适合资源受限的工业部署环境", 0),
        ("上下文智能编排：7 个算法模块确保 Prompt 质量，支持动态 Token 压缩", 0),
        ("故障树自动生成：Function Calling 驱动，知识从文档到结构化图谱的完整闭环", 0),
        ("工程可维护性：整洁架构 + 确定性流水线，算法可独立替换与测试", 0),
    ], base_size=13)

    add_textbox(slide, 0.5, 4.3, 12.5, 0.38,
                "后续扩展方向", size=14, bold=True, color=C_DARK)
    bullet_block(slide, 0.5, 4.75, 12.0, [
        ("引入 PPR（个性化 PageRank）替代 BFS 扩展，提升图路径质量（HippoRAG 核心）", 0),
        ("支持多模态输入：图片 + 文本联合建图与检索", 0),
        ("图谱版本管理：支持增量 diff 与历史回溯", 0),
        ("专家学习自动化：对话轮次与故障树修改实时沉淀为结构化知识", 0),
    ], base_size=13)

    add_rect(slide, 0.5, 6.7, 12.33, 0.04, C_RULE)
    add_textbox(slide, 0.5, 6.77, 12.5, 0.35,
                "代码路径：Backend/Application/  ·  Backend/Infrastructure/  ·  Backend/Domain/",
                size=10, italic=True, color=C_LIGHT)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def build_ppt() -> Presentation:
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_cover(prs)
    slide_overview(prs)
    slide_architecture(prs)
    slide_kg(prs)
    slide_entity_relation(prs)
    slide_context_mgmt(prs)
    slide_chat_fault(prs)
    slide_storage(prs)
    slide_stack(prs)
    slide_papers(prs)
    slide_summary(prs)

    return prs


if __name__ == "__main__":
    from pathlib import Path
    out = Path(__file__).parent / "项目介绍.pptx"
    prs = build_ppt()
    prs.save(str(out))
    print(f"Saved: {out}")
