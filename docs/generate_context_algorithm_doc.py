"""生成《上下文管理算法介绍文档》Word 版 (.docx)。

样式约束：
- 仅使用普通字体与加粗/斜体/字号/段落对齐等基础样式。
- 所有数学公式使用 Word 原生 OMML (Office Math) 渲染，而非纯文本。
- 不使用彩色、不使用花哨主题。
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import nsmap, qn
from docx.shared import Cm, Pt, RGBColor

# ---------------------------------------------------------------------------
# OMML (Office Math) helpers — 让 LaTeX 公式在 Word 中作为真实公式渲染。
# ---------------------------------------------------------------------------

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _m(tag: str) -> str:
    return f"{{{M_NS}}}{tag}"


def _m_t(text: str) -> OxmlElement:
    node = OxmlElement("m:t")
    node.text = text
    return node


def _m_r(text: str, italic: bool = False) -> OxmlElement:
    r = OxmlElement("m:r")
    if italic:
        rpr = OxmlElement("m:rPr")
        sty = OxmlElement("m:sty")
        sty.set(qn("m:val"), "i")
        rpr.append(sty)
        r.append(rpr)
    r.append(_m_t(text))
    return r


def _m_frac(num_nodes, den_nodes) -> OxmlElement:
    frac = OxmlElement("m:f")
    num = OxmlElement("m:num")
    for n in num_nodes:
        num.append(n)
    den = OxmlElement("m:den")
    for n in den_nodes:
        den.append(n)
    frac.append(num)
    frac.append(den)
    return frac


def _m_sub(base_nodes, sub_nodes) -> OxmlElement:
    sub = OxmlElement("m:sSub")
    e = OxmlElement("m:e")
    for n in base_nodes:
        e.append(n)
    s = OxmlElement("m:sub")
    for n in sub_nodes:
        s.append(n)
    sub.append(e)
    sub.append(s)
    return sub


def add_oxml(paragraph, element):
    paragraph._p.append(element)


def build_math_paragraph(doc, math_element, align_center: bool = True):
    """把一个 m:oMathPara 段落加入文档。"""
    p = doc.add_paragraph()
    if align_center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    math_para = OxmlElement("m:oMathPara")
    math = OxmlElement("m:oMath")
    for node in math_element:
        math.append(node)
    math_para.append(math)
    p._p.append(math_para)
    return p


# ---------------------------------------------------------------------------
# 正文样式辅助
# ---------------------------------------------------------------------------

CJK_FONT = "宋体"
LATIN_FONT = "Times New Roman"
CODE_FONT = "Consolas"


def _apply_font(run, size: Pt | None = None, bold: bool = False, italic: bool = False, mono: bool = False):
    run.bold = bold
    run.italic = italic
    if size is not None:
        run.font.size = size
    run.font.name = CODE_FONT if mono else LATIN_FONT
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), CODE_FONT if mono else LATIN_FONT)
    rFonts.set(qn("w:hAnsi"), CODE_FONT if mono else LATIN_FONT)
    rFonts.set(qn("w:eastAsia"), CODE_FONT if mono else CJK_FONT)
    rFonts.set(qn("w:cs"), CODE_FONT if mono else LATIN_FONT)


def add_title(doc, text, size=22, align=WD_ALIGN_PARAGRAPH.CENTER):
    p = doc.add_paragraph()
    p.alignment = align
    r = p.add_run(text)
    _apply_font(r, size=Pt(size), bold=True)
    return p


def add_heading(doc, text, level=1):
    size_map = {1: 16, 2: 14, 3: 12}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    _apply_font(r, size=Pt(size_map.get(level, 12)), bold=True)
    return p


def add_para(doc, runs, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent_first=True):
    """runs 是一个列表，每个元素为 (text, {bold,italic,mono,size})."""
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(4)
    if indent_first:
        p.paragraph_format.first_line_indent = Cm(0.74)  # 2 个汉字
    for item in runs:
        if isinstance(item, str):
            text, opts = item, {}
        else:
            text, opts = item
        r = p.add_run(text)
        _apply_font(
            r,
            size=Pt(opts.get("size", 11)),
            bold=opts.get("bold", False),
            italic=opts.get("italic", False),
            mono=opts.get("mono", False),
        )
    return p


def add_bullet(doc, runs, level=0):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(0.74 * (level + 1))
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_after = Pt(2)
    for item in runs:
        if isinstance(item, str):
            text, opts = item, {}
        else:
            text, opts = item
        r = p.add_run(text)
        _apply_font(
            r,
            size=Pt(opts.get("size", 11)),
            bold=opts.get("bold", False),
            italic=opts.get("italic", False),
            mono=opts.get("mono", False),
        )
    return p


def add_code_block(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    _apply_font(r, size=Pt(9.5), mono=True)
    # 浅灰底
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F2F2F2")
    pPr.append(shd)


def add_hr(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "808080")
    pBdr.append(bottom)
    pPr.append(pBdr)


# ---------------------------------------------------------------------------
# 公式构造：逐个手写为 OMML
# ---------------------------------------------------------------------------


def formula_mmr():
    """MMR(d) = λ·rel(d,q) - (1-λ)·max sim(d,d')"""
    nodes = [
        _m_r("MMR"),
        _m_r("("),
        _m_r("d", italic=True),
        _m_r(") = "),
        _m_r("λ", italic=True),
        _m_r(" · rel("),
        _m_r("d", italic=True),
        _m_r(", "),
        _m_r("q", italic=True),
        _m_r(") − (1 − "),
        _m_r("λ", italic=True),
        _m_r(") · "),
        _m_r("max", italic=False),
        _m_sub([_m_r("")], [_m_r("d′ ∈ S", italic=True)]),
        _m_r(" sim("),
        _m_r("d", italic=True),
        _m_r(", "),
        _m_r("d′", italic=True),
        _m_r(")"),
    ]
    return nodes


def formula_jaccard():
    """J(A,B) = |A∩B| / |A∪B|"""
    num = [_m_r("|"), _m_r("A", italic=True), _m_r(" ∩ "), _m_r("B", italic=True), _m_r("|")]
    den = [_m_r("|"), _m_r("A", italic=True), _m_r(" ∪ "), _m_r("B", italic=True), _m_r("|")]
    nodes = [
        _m_r("J"),
        _m_r("("),
        _m_r("A", italic=True),
        _m_r(", "),
        _m_r("B", italic=True),
        _m_r(") = "),
        _m_frac(num, den),
    ]
    return nodes


def formula_utilization():
    """ρ = total_prompt_tokens / max_context_tokens"""
    num = [_m_r("total_prompt_tokens", italic=True)]
    den = [_m_r("max_context_tokens", italic=True)]
    nodes = [
        _m_r("ρ", italic=True),
        _m_r(" = "),
        _m_frac(num, den),
    ]
    return nodes


def formula_prompt_sum():
    """Prompt = System + History + UserContent"""
    nodes = [
        _m_r("Prompt = SystemInstructions + HistoryMessages + UserContent"),
    ]
    return nodes


def formula_score():
    """score(c_i) = |terms(c_i)∩Q| / |Q| + 0.5·|terms(c_i)∩Q∩D|"""
    num = [
        _m_r("|"),
        _m_r("terms", italic=True),
        _m_r("("),
        _m_sub([_m_r("c", italic=True)], [_m_r("i", italic=True)]),
        _m_r(") ∩ "),
        _m_r("Q", italic=True),
        _m_r("|"),
    ]
    den = [_m_r("|"), _m_r("Q", italic=True), _m_r("|")]
    nodes = [
        _m_r("score("),
        _m_sub([_m_r("c", italic=True)], [_m_r("i", italic=True)]),
        _m_r(") = "),
        _m_frac(num, den),
        _m_r(" + 0.5 · |"),
        _m_r("terms", italic=True),
        _m_r("("),
        _m_sub([_m_r("c", italic=True)], [_m_r("i", italic=True)]),
        _m_r(") ∩ "),
        _m_r("Q", italic=True),
        _m_r(" ∩ "),
        _m_r("D", italic=True),
        _m_r("|"),
    ]
    return nodes


def formula_ratios():
    """ratios = {...}"""
    nodes = [
        _m_r("ratios = { system : 0.05,  kg : 0.20,  vector : 0.35,  "
              "history : 0.25,  query : 0.05,  reserve : 0.10 }"),
    ]
    return nodes


# ---------------------------------------------------------------------------
# 正文构建
# ---------------------------------------------------------------------------


def build_document() -> Document:
    doc = Document()

    # 默认样式：Normal
    normal = doc.styles["Normal"]
    normal.font.name = LATIN_FONT
    normal.font.size = Pt(11)
    rPr = normal.element.rPr
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), LATIN_FONT)
    rFonts.set(qn("w:hAnsi"), LATIN_FONT)
    rFonts.set(qn("w:eastAsia"), CJK_FONT)

    # 页边距
    section = doc.sections[0]
    section.top_margin = Cm(2.3)
    section.bottom_margin = Cm(2.3)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # ------------------------------------------------------------------
    # 标题
    # ------------------------------------------------------------------
    add_title(doc, "上下文管理算法介绍文档", size=22)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("RAG 问答流水线中的检索后编排模块")
    _apply_font(r, size=Pt(11), italic=True)

    add_hr(doc)

    # ------------------------------------------------------------------
    # 一、概述
    # ------------------------------------------------------------------
    add_heading(doc, "一、概述", level=1)

    add_para(doc, [
        "本项目的上下文管理模块位于 ",
        ("Backend/Application/ContextManagement", {"mono": True}),
        "，是 RAG 问答流水线中处于 ",
        ("“检索之后、生成之前”", {"bold": True}),
        " 的关键环节。它的职责是把来自不同数据源的原材料（知识图谱路径、向量检索片段、"
        "历史对话、当前用户问题）编排成一条 ",
        ("结构合理、冗余可控、长度可算、注意力友好", {"bold": True}),
        " 的最终提示词。",
    ])

    add_para(doc, [
        "整体实现采用 ",
        ("算法模块 + 规则式编排器", {"italic": True}),
        " 的组合架构：",
    ])
    add_bullet(doc, [
        ("算法模块（", {}),
        ("Algorithms/", {"mono": True}),
        ("）：每个算法封装一篇论文的核心思想，只负责单一职责。", {}),
    ])
    add_bullet(doc, [
        ("编排器（", {}),
        ("ContextManager.py", {"mono": True}),
        ("）：以确定性顺序调用各算法，并依据 token 预算触发分级动作。", {}),
    ])
    add_bullet(doc, [
        ("注册表（", {}),
        ("AlgorithmRegistry.py", {"mono": True}),
        ("）：统一装配算法实例，便于替换与测试。", {}),
    ])
    add_para(doc, [
        "配置参数集中在 ",
        ("ContextManagerTypes.py", {"mono": True}),
        " 的 ",
        ("ContextManagerConfig", {"mono": True}),
        " 中，可在运行时覆盖。",
    ])

    # ------------------------------------------------------------------
    # 二、算法与论文
    # ------------------------------------------------------------------
    add_heading(doc, "二、算法模块与论文对照", level=1)

    rows = [
        ("MMR 去重", "Long-Context LLMs Meet RAG (ICLR 2025, arXiv:2410.05983)",
         "对检索片段做“相关性 vs 新颖性”的平衡选择"),
        ("检索重排", "Long-Context LLMs Meet RAG；Retrieval Head (arXiv:2404.15574)",
         "把高相关证据放到提示词首尾，利用注意力边界效应"),
        ("路径剪枝", "GraphRAG (arXiv:2404.16130)；PathRAG (arXiv:2502.14902)",
         "过滤低置信度三元组并保持关系类型多样性"),
        ("Token 预算", "Long Context vs. RAG (arXiv:2501.01880)；LongLLMLingua (arXiv:2310.06839)；Retrieval Head",
         "为提示词各分区分配预算并触发分级压缩"),
        ("历史分层", "MemAgent (arXiv:2507.02259)；Long Context vs. RAG",
         "把历史对话切成冷 / 温 / 热三层，只保热层原文"),
        ("查询感知压缩", "LongLLMLingua；LLMLingua-2 (arXiv:2403.12968)",
         "保留查询相关句子的抽取式压缩"),
        ("查询位置", "Retrieval Head",
         "强制当前查询位于消息列表末尾"),
    ]
    table = doc.add_table(rows=1 + len(rows), cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, name in enumerate(("算法模块", "论文来源", "在本项目中的作用")):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name)
        _apply_font(r, size=Pt(10.5), bold=True)
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = table.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(val)
            _apply_font(r, size=Pt(10), bold=(j == 0))

    # 2.1 MMR
    add_heading(doc, "2.1 MMR 去重（MMRDeduplicationAlgorithm）", level=2)
    add_para(doc, [
        ("Maximal Marginal Relevance", {"italic": True}),
        " 的经典目标是：在已选集合 ",
        ("S", {"italic": True}),
        " 的基础上挑选下一条片段时，最大化下列目标函数：",
    ])
    build_math_paragraph(doc, formula_mmr())
    add_para(doc, [
        "其中 rel 取检索分数，sim 采用内容词的 ",
        ("Jaccard", {"bold": True}),
        " 相似度：",
    ])
    build_math_paragraph(doc, formula_jaccard())
    add_para(doc, [
        "相关性权重 ",
        ("λ", {"italic": True}),
        " 对应配置项 ",
        ("mmr_relevance_weight", {"mono": True}),
        "（默认 0.7），输出长度由 ",
        ("mmr_top_k", {"mono": True}),
        "（默认 15）限制。在检索片段常存在近重复的场景下，",
        ("MMR 是本流水线第一道“信息密度闸门”。", {"bold": True}),
    ])

    # 2.2 Reorder
    add_heading(doc, "2.2 检索重排（RetrievalReorderingAlgorithm）", level=2)
    add_para(doc, [
        ("Retrieval Head", {"italic": True}),
        " 指出长上下文模型的事实性能力高度依赖少量“检索头”，而这些注意力头对 ",
        ("序列头尾的信息更敏感", {"bold": True}),
        "。因此算法把 MMR 输出先按分数降序排序，再做“首位—末位—首位—末位…”的交替放置：",
    ])
    add_code_block(doc, "[ d1, d3, d5, ..., d6, d4, d2 ]")
    add_para(doc, [
        "最高相关的证据放在首位，次高放在末位，依此类推。无论模型偏爱前景还是后景，都能优先看到关键证据。",
    ])

    # 2.3 Path Pruning
    add_heading(doc, "2.3 路径剪枝（PathPruningAlgorithm）", level=2)
    add_para(doc, [
        "针对知识图谱三元组 (s, r, t)，算法依次执行：",
    ])
    add_bullet(doc, [("过滤字段不全或置信度低于阈值的三元组，阈值对应 ", {}),
                     ("min_path_confidence", {"mono": True}), ("。", {})])
    add_bullet(doc, [("按 (s, r, t) 做精确去重。", {})])
    add_bullet(doc, [("若 ", {}), ("relation_diversity=True", {"mono": True}),
                     ("，先对每一类关系类型各保留一条最佳路径，再按全局置信度补齐到 ", {}),
                     ("max_graph_paths", {"mono": True}), ("。", {})])
    add_para(doc, [
        "这种 ",
        ("多样性优先", {"italic": True}),
        " 的策略来源于 GraphRAG 与 PathRAG 的实证结论：在有限预算下，关系类型的覆盖度"
        "比单一类型的深度更能提升下游问答质量。",
    ])

    # 2.4 Token Budgeting
    add_heading(doc, "2.4 Token 预算（TokenBudgetingAlgorithm）", level=2)
    add_para(doc, ["算法为六个分区分配固定比例："])
    build_math_paragraph(doc, formula_ratios())
    add_para(doc, [
        "残差 token 并入 ",
        ("vector", {"mono": True}),
        " 分区以提升检索侧灵活度。运行时计算利用率：",
    ])
    build_math_paragraph(doc, formula_utilization())
    add_para(doc, ["依 ρ 触发 ", ("分级压缩动作", {"bold": True}), "："])
    add_bullet(doc, [("ρ > 0.6：触发 ", {}), ("compress_history_tier2", {"mono": True}),
                     ("（历史分层）。", {})])
    add_bullet(doc, [("ρ > 0.8：追加 ", {}),
                     ("compress_history_tier3", {"mono": True}),
                     (" 与 ", {}),
                     ("compress_vector_docs_keep_50pct", {"mono": True}),
                     ("（查询感知压缩）。", {})])
    add_bullet(doc, [("ρ > 0.9：再追加 ", {}),
                     ("kg_one_hop_only", {"mono": True}),
                     ("、", {}),
                     ("remove_kg_community_summary", {"mono": True}),
                     ("、", {}),
                     ("vector_top_k_hard_cap", {"mono": True}),
                     ("。", {})])
    add_para(doc, [
        ("system", {"mono": True}),
        " 与 ",
        ("query", {"mono": True}),
        " 分区被标记为 ",
        ("不可压缩", {"bold": True}),
        " —— 这是 ",
        ("Retrieval Head", {"italic": True}),
        " 工作结论的直接工程化。",
    ])

    # 2.5 History Tiering
    add_heading(doc, "2.5 历史分层（HistoryTieringAlgorithm）", level=2)
    add_para(doc, [
        "参照 ",
        ("MemAgent", {"italic": True}),
        "，算法把按时间顺序排列的对话轮次切成三层：",
    ])
    add_bullet(doc, [("Hot（热层）", {"bold": True}),
                     ("：最近 hot_size 轮，原样保留。", {})])
    add_bullet(doc, [("Warm（温层）", {"bold": True}),
                     ("：紧邻热层前的 warm_size 轮，摘要为要点。", {})])
    add_bullet(doc, [("Cold（冷层）", {"bold": True}),
                     ("：其余早期轮次，进一步粗粒度摘要。", {})])
    add_para(doc, [
        "温层摘要时按工业故障诊断关键词（“故障”“现象”“原因”“解决”等）打分排序，",
        ("优先保留领域相关度高的轮次", {"bold": True}),
        "，最多 5 个要点；冷层则只抽取含关键词的问题作为“历史聚焦摘要”。输出以 ",
        ("[Hot Turns] / [Warm Memory Summary] / [Cold Memory Summary]", {"mono": True}),
        " 三段文本组织。",
    ])

    # 2.6 Query-Aware Compression
    add_heading(doc, "2.6 查询感知压缩（QueryAwareCompressionAlgorithm）", level=2)
    add_para(doc, [
        "参照 LongLLMLingua 与 LLMLingua-2 的查询感知思想，算法按分数保留前 ",
        ("keep_rate", {"mono": True}),
        " 比例的文档（默认 0.5），然后对每篇文档做抽取式压缩：",
    ])
    add_bullet(doc, [("用 jieba 中文分词（加载了工业故障领域词典）提取查询词集合 Q。", {})])
    add_bullet(doc, [("按分隔符将文档切成句子。", {})])
    add_bullet(doc, [("计算与查询的重叠得分：", {})])
    build_math_paragraph(doc, formula_score())
    add_para(doc, [
        "其中 D 是 ",
        ("INDUSTRIAL_DOMAIN_TERMS", {"mono": True}),
        " 领域词典（故障、诊断、传感器、日志等），领域词重叠会获得额外加成。",
    ])
    add_bullet(doc, [("按得分降序累积句子，直到达到 ", {}),
                     ("compression_min_chars", {"mono": True}),
                     ("（默认 160）。", {})])

    # 2.7 Query Placement
    add_heading(doc, "2.7 查询位置（QueryPlacementAlgorithm）", level=2)
    add_para(doc, [
        ("原则", {"bold": True}),
        "：当前用户问题必须出现在消息序列的最后一条。算法提供两个接口：",
        ("append_query", {"mono": True}),
        " 把问题与上下文合并为一条 user 消息并追加，",
        ("ensure_query_last", {"mono": True}),
        " 在必要时将末位 user 消息移到尾部。其理论依据仍是 ",
        ("Retrieval Head", {"italic": True}),
        " —— 尾部位置在长上下文下的事实召回率更稳定。",
    ])

    # ------------------------------------------------------------------
    # 三、整体编排
    # ------------------------------------------------------------------
    add_heading(doc, "三、整体编排流程", level=1)
    add_para(doc, [
        "编排器 ",
        ("DefaultContextManager.prepare_context", {"mono": True}),
        " 以 ",
        ("确定性顺序", {"bold": True}),
        " 调用上述算法。下图给出数据流与决策分支：",
    ])
    add_code_block(doc,
        "输入: question, rounds, seed_names, graph_paths, sources, cfg\n"
        "  │\n"
        "  ▼\n"
        "① PathPruning        ──►  按置信度 + 去重 + 关系多样性裁剪 graph_paths\n"
        "  │\n"
        "  ▼\n"
        "② MMRDeduplication   ──►  在检索片段上做 MMR 选择，输出 top_k 条\n"
        "  │\n"
        "  ▼\n"
        "③ RetrievalReorder   ──►  首尾交替放置，形成边界感知顺序\n"
        "  │\n"
        "  ▼\n"
        "④ 基线历史 + 上下文文本 + user_content  (QueryPlacement 拼装)\n"
        "  │\n"
        "  ▼\n"
        "⑤ TokenBudgeting     ──►  计算 ρ，产出 budget_actions 列表\n"
        "  │   ├── ρ > 0.6 ──► HistoryTiering   (重建冷/温/热历史消息)\n"
        "  │   ├── ρ > 0.8 ──► QueryAwareCompression (压缩保留片段)\n"
        "  │   └── ρ > 0.9 ──► vector hard cap / KG one-hop 限制\n"
        "  ▼\n"
        "⑥ 重新组装 context_text 与 user_content → ContextPreparationResult"
    )
    add_para(doc, [("关键点：", {"bold": True})])
    add_bullet(doc, [("确定性", {"bold": True}),
                     ("：在相同输入与配置下，输出严格可复现，便于测试与 A/B 分析。", {})])
    add_bullet(doc, [("单向流水线", {"bold": True}),
                     ("：除了第 ⑤ 步的条件分支外，各算法只读上游结果、不回溯。", {})])
    add_bullet(doc, [("不可压缩的 system / query", {"bold": True}),
                     ("：整个流程中两者的文本不会被裁剪。", {})])
    add_bullet(doc, [("可观测性", {"bold": True}),
                     ("：", {}),
                     ("ContextPreparationResult.budget_actions", {"mono": True}),
                     (" 与 ", {}),
                     ("budget_plan", {"mono": True}),
                     (" 会随响应一起返回，可在日志与前端调试面板中直接查看。", {})])

    # ------------------------------------------------------------------
    # 四、Prompt 生成
    # ------------------------------------------------------------------
    add_heading(doc, "四、用户 Prompt 的生成过程", level=1)
    add_para(doc, [
        "最终送入 LLM 的提示词由 ",
        ("三部分", {"bold": True}),
        " 构成：",
    ])
    build_math_paragraph(doc, formula_prompt_sum())
    add_para(doc, [
        "上下文管理模块负责生成 ",
        ("History Messages", {"bold": True}),
        " 与 ",
        ("User Content", {"bold": True}),
        " 两部分。",
    ])

    add_heading(doc, "4.1 历史消息的生成", level=2)
    add_bullet(doc, [("默认情况下调用 ", {}),
                     ("_build_recent_history_messages", {"mono": True}),
                     ("，取末尾 max_history_rounds 轮（默认 10）原样转成 user / assistant 的消息对。", {})])
    add_bullet(doc, [("当触发 ", {}),
                     ("compress_history_tier2", {"mono": True}),
                     (" 时，改由 ", {}),
                     ("_build_tiered_history_messages", {"mono": True}),
                     (" 生成，输出为 ", {}),
                     ("单条 assistant 消息", {"bold": True}),
                     ("，内容形如：", {})])
    add_code_block(doc,
        "[Conversation Memory]\n"
        "[Cold Memory Summary]\n"
        "- Historical focus: ...\n\n"
        "[Warm Memory Summary]\n"
        "- Q: ... | A: ...\n"
        "- Q: ... | A: ...\n\n"
        "[Hot Turns]\n"
        "User: ...\n"
        "Assistant: ..."
    )

    add_heading(doc, "4.2 User Content 的生成", level=2)
    add_para(doc, [
        "User Content 由 ",
        ("_build_context_text", {"mono": True}),
        " 与 ",
        ("_compose_user_content", {"mono": True}),
        " 共同完成。",
    ])
    add_para(doc, [
        ("第一步", {"bold": True}),
        "：拼装上下文文本 ",
        ("context_text", {"mono": True}),
        "，遵循固定的三段式结构：",
    ])
    add_code_block(doc,
        "【关联实体】\n"
        "实体A, 实体B, 实体C\n\n"
        "【知识图谱路径】\n"
        "  - 实体A --[关系r1]--> 实体B\n"
        "  - 实体B --[关系r2]--> 实体C\n\n"
        "【相关原文片段】\n"
        "[file_name_1.pdf]\n"
        "片段内容 ...\n\n"
        "[file_name_2.pdf]\n"
        "片段内容 ..."
    )
    add_para(doc, [
        ("第二步", {"bold": True}),
        "：交由 ",
        ("QueryPlacementAlgorithm", {"mono": True}),
        " 把问题与上下文合并，并保证查询居末。最终 User Content 形态为：",
    ])
    add_code_block(doc,
        "<用户问题>\n\n"
        "Context:\n"
        "<上面的三段式上下文>"
    )

    add_heading(doc, "4.3 一次典型调用的输出", level=2)
    add_para(doc, [
        ("ContextPreparationResult", {"mono": True}),
        " 返回字段示例（简化）：",
    ])
    add_code_block(doc,
        "{\n"
        '    "context": "【关联实体】...\\n\\n【知识图谱路径】...\\n\\n【相关原文片段】...",\n'
        '    "user_content": "故障现象是什么？\\n\\nContext:\\n...",\n'
        '    "history_messages": [{"role": "user", ...}, {"role": "assistant", ...}],\n'
        '    "sources": [... 经 MMR + 重排 (+ 压缩) 后的片段 ...],\n'
        '    "graph_paths": [... 经路径剪枝 (+ one-hop 限制) 后的三元组 ...],\n'
        '    "seed_names": ["实体A", "实体B"],\n'
        '    "budget_actions": ["compress_history_tier2", "compress_vector_docs_keep_50pct"],\n'
        '    "prompt_token_estimate": 18432,\n'
        '    "budget_plan": {"system": 1600, "kg": 6400, "vector": 11200, ...}\n'
        "}"
    )
    add_para(doc, [
        "该结果被 ",
        ("ChatUseCase", {"mono": True}),
        " 直接消费：",
        ("history_messages", {"mono": True}),
        " 作为模型对话历史，",
        ("user_content", {"mono": True}),
        " 作为最终一条 user 消息，",
        ("budget_actions", {"mono": True}),
        " 与 ",
        ("budget_plan", {"mono": True}),
        " 供日志与前端展示。",
    ])

    # ------------------------------------------------------------------
    # 五、设计取舍
    # ------------------------------------------------------------------
    add_heading(doc, "五、设计取舍", level=1)
    add_bullet(doc, [("规则式 over 端到端学习", {"bold": True}),
                     ("：所有决策都来自可解释的阈值与比例，便于复盘与回滚。", {})])
    add_bullet(doc, [("单一职责的算法模块", {"bold": True}),
                     ("：每个算法只对应一篇论文的核心贡献，避免耦合。", {})])
    add_bullet(doc, [("分级触发 over 一刀切压缩", {"bold": True}),
                     ("：通过利用率阈值逐级加码，低负载时不牺牲信息保真度。", {})])
    add_bullet(doc, [("领域词典的中文增强", {"bold": True}),
                     ("：jieba + 工业故障词典使压缩与摘要在中文场景下更稳健。", {})])
    add_bullet(doc, [("注意力边界友好的布局", {"bold": True}),
                     ("：检索重排与查询末置共同实现 Retrieval Head 的工程化。", {})])

    # ------------------------------------------------------------------
    # 六、配置默认值
    # ------------------------------------------------------------------
    add_heading(doc, "六、配置默认值速查", level=1)
    config_rows = [
        ("max_context_tokens", "32000", "模型上下文窗口总量"),
        ("max_history_rounds", "10", "未分层时保留的最近对话轮数"),
        ("mmr_top_k", "15", "MMR 输出上限"),
        ("mmr_relevance_weight", "0.7", "MMR 中相关性权重 λ"),
        ("min_path_confidence", "0.4", "路径剪枝的置信度阈值"),
        ("max_graph_paths", "20", "输出路径上限"),
        ("history_hot_size", "3", "热层轮数"),
        ("history_warm_size", "7", "温层轮数"),
        ("compression_keep_rate", "0.5", "查询感知压缩保留比例"),
        ("compression_min_chars", "160", "单文档压缩后最小字符数"),
    ]
    ctbl = doc.add_table(rows=1 + len(config_rows), cols=3)
    ctbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    ctbl.style = "Light Grid Accent 1"
    for i, name in enumerate(("配置项", "默认值", "说明")):
        cell = ctbl.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name)
        _apply_font(r, size=Pt(10.5), bold=True)
    for i, row in enumerate(config_rows, start=1):
        for j, val in enumerate(row):
            cell = ctbl.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(val)
            _apply_font(r, size=Pt(10), mono=(j < 2))

    # 页脚
    add_hr(doc)
    foot = doc.add_paragraph()
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = foot.add_run("文档版本：v1.0  |  对应代码路径：Backend/Application/ContextManagement/")
    _apply_font(r, size=Pt(9), italic=True)

    return doc


if __name__ == "__main__":
    out_path = Path(__file__).parent / "上下文管理算法介绍文档.docx"
    document = build_document()
    document.save(str(out_path))
    print(f"Saved: {out_path}")
