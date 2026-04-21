"""生成《知识图谱模块介绍文档》Word 版 (.docx)。

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
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

# ---------------------------------------------------------------------------
# OMML (Office Math) helpers
# ---------------------------------------------------------------------------

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


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


def _m_sup(base_nodes, sup_nodes) -> OxmlElement:
    sup_elem = OxmlElement("m:sSup")
    e = OxmlElement("m:e")
    for n in base_nodes:
        e.append(n)
    s = OxmlElement("m:sup")
    for n in sup_nodes:
        s.append(n)
    sup_elem.append(e)
    sup_elem.append(s)
    return sup_elem


def build_math_paragraph(doc, math_element, align_center: bool = True):
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


def _apply_font(run, size=None, bold: bool = False, italic: bool = False, mono: bool = False):
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
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(4)
    if indent_first:
        p.paragraph_format.first_line_indent = Cm(0.74)
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
# 公式构造
# ---------------------------------------------------------------------------


def formula_triple():
    """τ = (h, r, t)，h,t ∈ E，r ∈ R"""
    return [
        _m_r("τ", italic=True),
        _m_r(" = ("),
        _m_r("h", italic=True),
        _m_r(", "),
        _m_r("r", italic=True),
        _m_r(", "),
        _m_r("t", italic=True),
        _m_r("),   "),
        _m_r("h", italic=True),
        _m_r(", "),
        _m_r("t", italic=True),
        _m_r(" ∈ "),
        _m_r("E", italic=True),
        _m_r(",   "),
        _m_r("r", italic=True),
        _m_r(" ∈ "),
        _m_r("R", italic=True),
    ]


def formula_kg():
    """G = (V, E, R)"""
    return [
        _m_r("G", italic=True),
        _m_r(" = ("),
        _m_r("V", italic=True),
        _m_r(", "),
        _m_r("E", italic=True),
        _m_r(", "),
        _m_r("R", italic=True),
        _m_r(")"),
    ]


def formula_entity_score():
    """sim(q, e) = 1 / (1 + ||emb(q) - emb(e)||^2)"""
    num = [_m_r("1")]
    den = [
        _m_r("1 + ‖emb("),
        _m_r("q", italic=True),
        _m_r(") − emb("),
        _m_r("e", italic=True),
        _m_r(")‖"),
        _m_sup([_m_r("")], [_m_r("2")]),
    ]
    return [
        _m_r("sim("),
        _m_r("q", italic=True),
        _m_r(", "),
        _m_r("e", italic=True),
        _m_r(") = "),
        _m_frac(num, den),
    ]


def formula_bfs():
    """G_sub(S, h) = {(u, r, v) ∈ E : ∃s ∈ S, d_G(s, u) ≤ h}"""
    return [
        _m_sub([_m_r("G", italic=True)], [_m_r("sub")]),
        _m_r("("),
        _m_r("S", italic=True),
        _m_r(", "),
        _m_r("h", italic=True),
        _m_r(") = { ("),
        _m_r("u", italic=True),
        _m_r(", "),
        _m_r("r", italic=True),
        _m_r(", "),
        _m_r("v", italic=True),
        _m_r(") ∈ "),
        _m_r("E", italic=True),
        _m_r(" : ∃"),
        _m_r("s", italic=True),
        _m_r(" ∈ "),
        _m_r("S", italic=True),
        _m_r(", "),
        _m_sub([_m_r("d", italic=True)], [_m_r("G", italic=True)]),
        _m_r("("),
        _m_r("s", italic=True),
        _m_r(", "),
        _m_r("u", italic=True),
        _m_r(") ≤ "),
        _m_r("h", italic=True),
        _m_r(" }"),
    ]


def formula_chunk_merge():
    """C'_k = C_{2k-1} ∪ C_{2k}"""
    return [
        _m_sub([_m_r("C", italic=True)], [_m_r("k", italic=True)]),
        _m_r("' = "),
        _m_sub([_m_r("C", italic=True)], [_m_r("2k-1", italic=True)]),
        _m_r(" ∪ "),
        _m_sub([_m_r("C", italic=True)], [_m_r("2k", italic=True)]),
        _m_r(",   k = 1, 2, …"),
    ]


def formula_dedup():
    """T_unique = {τ ∈ T : (h,r,t) 唯一}"""
    return [
        _m_sub([_m_r("T", italic=True)], [_m_r("unique")]),
        _m_r(" = { "),
        _m_r("τ", italic=True),
        _m_r(" ∈ "),
        _m_r("T", italic=True),
        _m_r(" : ("),
        _m_r("h", italic=True),
        _m_r(", "),
        _m_r("r", italic=True),
        _m_r(", "),
        _m_r("t", italic=True),
        _m_r(") 唯一 }"),
    ]


# ---------------------------------------------------------------------------
# 正文构建
# ---------------------------------------------------------------------------


def build_document() -> Document:
    doc = Document()

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

    section = doc.sections[0]
    section.top_margin = Cm(2.3)
    section.bottom_margin = Cm(2.3)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # ======================================================================
    # 标题
    # ======================================================================
    add_title(doc, "知识图谱模块介绍文档", size=22)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("工业故障 RAG 系统中的轻量化知识图谱构建与检索")
    _apply_font(r, size=Pt(11), italic=True)
    add_hr(doc)

    # ======================================================================
    # 一、设计目标与背景
    # ======================================================================
    add_heading(doc, "一、设计目标与背景", level=1)

    add_heading(doc, "1.1 为什么引入知识图谱", level=2)
    add_para(doc, [
        "传统 RAG 系统依赖向量相似度检索，能够快速找到语义相关的文本片段，"
        "但在以下场景中存在明显局限：",
    ])
    add_bullet(doc, [
        ("多跳推理", {"bold": True}),
        ("：用户问题涉及跨文档的因果链（如 A 组件故障引发 B 现象、根因为 C），"
         "向量检索无法利用文档间的显式关联。", {}),
    ])
    add_bullet(doc, [
        ("关系敏感问题", {"bold": True}),
        ("：用户询问哪些组件会引发该故障时，向量相似度无法区分属于与引发等不同关系语义。", {}),
    ])
    add_bullet(doc, [
        ("知识复用", {"bold": True}),
        ("：相同的实体关系散布在多个文档中，向量检索每次只返回孤立片段，"
         "图结构则可将分散知识聚合为连通的推理链。", {}),
    ])
    add_para(doc, [
        "为此，本系统在向量检索的基础上叠加了一层 ",
        ("知识图谱", {"bold": True}),
        "，以三元组形式显式编码实体与关系，并通过图拓扑结构支持多跳关联检索。"
        "两种机制互补：向量检索覆盖语义相似性，知识图谱覆盖结构关系推理。",
    ])

    add_heading(doc, "1.2 轻量化设计目标", level=2)
    add_para(doc, [
        "工业场景中的部署资源往往受限，全量离线 GraphRAG（如 Microsoft GraphRAG）"
        "需要为整个语料库预构建社区摘要，成本极高。本系统的核心目标是在 ",
        ("资源受限环境", {"bold": True}),
        " 下运行可用的知识图谱，为此确立了四条设计原则：",
    ])

    principle_rows = [
        (
            "拒绝重型外部图数据库",
            "不引入 Neo4j 等外部图数据库，完全使用 NetworkX 内存图 + JSON 文件持久化，"
            "启动时毫秒级加载，零运维依赖。",
        ),
        (
            "Schema 定向抽取",
            "硬性限定实体类型（8 种）与关系类型（8 种），杜绝开放式信息抽取的算力浪费，"
            "同时保证三元组质量与类型一致性。",
        ),
        (
            "向量与图算法融合",
            "ChromaDB 负责语义模糊寻点，NetworkX 负责拓扑精确扩展，两者分工明确、"
            "各司其职，查询延迟可控。",
        ),
        (
            "异步建图、不阻塞查询",
            "图的构建在文件导入时异步执行，以降级策略处理——图构建失败不影响向量检索可用性，"
            "在线查询路径不依赖建图完成。",
        ),
    ]

    ptbl = doc.add_table(rows=1 + len(principle_rows), cols=2)
    ptbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    ptbl.style = "Light Grid Accent 1"
    for i, name in enumerate(("设计原则", "工程含义")):
        cell = ptbl.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name)
        _apply_font(r, size=Pt(10.5), bold=True)
    for i, (principle, desc) in enumerate(principle_rows, start=1):
        cell0 = ptbl.rows[i].cells[0]
        cell0.text = ""
        p0 = cell0.paragraphs[0]
        r0 = p0.add_run(principle)
        _apply_font(r0, size=Pt(10), bold=True)

        cell1 = ptbl.rows[i].cells[1]
        cell1.text = ""
        p1 = cell1.paragraphs[0]
        r1 = p1.add_run(desc)
        _apply_font(r1, size=Pt(10))

    add_heading(doc, "1.3 参考论文", level=2)
    add_para(doc, [
        "本系统的设计参照了 2024—2025 年间若干轻量化图增强 RAG 的研究方向：",
    ])

    paper_rows = [
        (
            "LightRAG",
            "Guo et al., 2024",
            "双层结构（低层实体 + 高层关系/主题），联合向量检索",
            "三个独立 ChromaDB Collection 的分层存储设计",
        ),
        (
            "HippoRAG",
            "2024",
            "模拟海马体记忆：向量寻点 → PPR 算法激活子图",
            "向量寻点 + BFS 图发散的两阶段检索结构",
        ),
        (
            "PathRAG",
            "arXiv:2502.14902, 2025",
            "对图谱关系路径剪枝，去冗余边，降低遍历消耗",
            "MAX_EDGES_PER_NODE 限制 + PathPruningAlgorithm 置信度过滤",
        ),
        (
            "Query-Driven GraphRAG",
            "2025",
            "查询时在线局部建图，规避离线全局图构建的高成本",
            "仅对被召回文档的 chunks 做小规模三元组抽取，而非全量预建",
        ),
        (
            "GraphRAG (Microsoft)",
            "arXiv:2404.16130",
            "社区摘要 + 全局图构建，用于大规模离线场景",
            "路径多样性优先策略（PathPruningAlgorithm 中的关系类型多样性）",
        ),
    ]

    rtbl = doc.add_table(rows=1 + len(paper_rows), cols=4)
    rtbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    rtbl.style = "Light Grid Accent 1"
    for i, name in enumerate(("论文", "来源", "核心贡献", "在本系统中的体现")):
        cell = rtbl.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name)
        _apply_font(r, size=Pt(10.5), bold=True)
    for i, row in enumerate(paper_rows, start=1):
        for j, val in enumerate(row):
            cell = rtbl.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(val)
            _apply_font(r, size=Pt(10), bold=(j == 0), italic=(j == 1))

    add_heading(doc, "1.4 与全量 GraphRAG 的对比", level=2)
    add_para(doc, [
        "下表对比了本系统与典型全量 GraphRAG 方案在关键维度上的差异：",
    ])

    compare_rows = [
        ("图构建时机", "文件导入时异步增量构建", "语料库离线预处理（数小时~数天）"),
        ("图数据库", "NetworkX 内存图 + JSON 文件", "Neo4j / ArangoDB 等外部图数据库"),
        ("抽取粒度", "Schema 定向（8 类实体 × 8 类关系）", "开放式实体关系抽取"),
        ("社区摘要", "不构建", "层级社区摘要（高成本 LLM 调用）"),
        ("查询方式", "向量寻点 + BFS 2 跳展开", "全局搜索 + 社区摘要融合"),
        ("硬件要求", "CPU 可运行，无 GPU 强依赖", "通常需要 GPU 加速和大内存"),
        ("删除支持", "按文件名增量删除边与孤立节点", "通常需全量重建"),
    ]

    ctbl = doc.add_table(rows=1 + len(compare_rows), cols=3)
    ctbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    ctbl.style = "Light Grid Accent 1"
    for i, name in enumerate(("对比维度", "本系统（轻量化）", "全量 GraphRAG")):
        cell = ctbl.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name)
        _apply_font(r, size=Pt(10.5), bold=True)
    for i, row in enumerate(compare_rows, start=1):
        for j, val in enumerate(row):
            cell = ctbl.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(val)
            _apply_font(r, size=Pt(10), bold=(j == 0))

    # ======================================================================
    # 二、系统架构
    # ======================================================================
    add_heading(doc, "二、系统架构", level=1)

    add_para(doc, [
        "知识图谱模块纵贯 Domain、Infrastructure、Application 三个架构层，"
        "整体数据流分为 ",
        ("离线建图", {"bold": True}),
        " 与 ",
        ("在线查询", {"bold": True}),
        " 两条路径：",
    ])
    add_code_block(doc,
        "原始文档\n"
        "  │\n"
        "  ▼  [异步，文件导入时触发]\n"
        "Schema 定向抽取（LLM + 限定 Prompt）\n"
        "  │\n"
        "  ├──> ChromaDB: graph_entities   （实体名 + 向量 + 类型元数据）\n"
        "  ├──> ChromaDB: graph_relations  （关系描述文本 + 向量）\n"
        "  └──> db/knowledge_graph.json    （节点 + 边，供 NetworkX 加载）\n"
        "\n"
        "用户提问\n"
        "  │\n"
        "  ▼  [在线，毫秒级]\n"
        "① 向量寻点    graph_entities  →  Top-K 种子实体\n"
        "② 图谱发散    NetworkX BFS    →  2 跳关联路径\n"
        "③ 原文检索    rag_docs        →  语义相关片段\n"
        "④ 上下文编排  ContextManager  →  结构化 Prompt\n"
        "⑤ LLM 推理                   →  最终回答"
    )

    add_para(doc, [
        "建图与查询完全解耦：建图失败时查询自动降级为纯向量 RAG，"
        "不影响服务可用性。NetworkX 图在服务启动时一次性加载到内存，"
        "后续查询直接在内存中执行 BFS，延迟通常在 ",
        ("10 ms", {"bold": True}),
        " 以内。",
    ])

    # ======================================================================
    # 三、数据模型
    # ======================================================================
    add_heading(doc, "三、数据模型", level=1)

    add_heading(doc, "3.1 三元组（Triple）", level=2)
    add_para(doc, [
        "知识图谱的最小语义单元是三元组，记作：",
    ])
    build_math_paragraph(doc, formula_triple())
    add_para(doc, [
        "其中 ",
        ("h", {"italic": True}),
        " 为头实体，",
        ("r", {"italic": True}),
        " 为关系类型，",
        ("t", {"italic": True}),
        " 为尾实体，",
        ("E", {"italic": True}),
        " 为实体集合，",
        ("R", {"italic": True}),
        " 为关系类型集合。代码中由 ",
        ("Triple", {"mono": True}),
        " 数据类表示：",
    ])
    add_code_block(doc,
        "@dataclass\n"
        "class Triple:\n"
        "    head:            str   # 头实体名称\n"
        "    head_type:       str   # 头实体类型（EntityType 枚举值）\n"
        "    relation:        str   # 关系类型（RelationType 枚举值）\n"
        "    tail:            str   # 尾实体名称\n"
        "    tail_type:       str   # 尾实体类型\n"
        "    source_file:     str   # 来源文件名\n"
        "    source_chunk_id: str   # 来源文本块 ID"
    )

    add_heading(doc, "3.2 实体类型（EntityType）", level=2)
    add_para(doc, [
        "Schema 定向抽取的核心约束之一是 ",
        ("封闭的实体类型集合", {"bold": True}),
        "。面向工业故障诊断场景，定义了 8 种实体类型，"
        "覆盖从设备组件到根因分析的完整故障链路：",
    ])

    entity_rows = [
        ("COMPONENT",  "组件",     "具体的硬件或软件组件，如传感器、驱动板"),
        ("SYMPTOM",    "故障现象", "可观测到的异常表现，如电流突变、过载报警"),
        ("ERROR_CODE", "错误码",   "系统输出的错误编号，如 E-04"),
        ("SOLUTION",   "解决方案", "针对故障的处理措施，如更换驱动板"),
        ("DEVICE",     "设备",     "包含组件的上层设备单元"),
        ("FAULT_MODE", "失效模式", "故障的发生模式与类别"),
        ("WORK_ORDER", "工单",     "记录维修过程的工单实体"),
        ("CAUSE",      "根因",     "故障的根本原因"),
    ]
    etbl = doc.add_table(rows=1 + len(entity_rows), cols=3)
    etbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    etbl.style = "Light Grid Accent 1"
    for i, name in enumerate(("枚举值", "中文含义", "说明")):
        cell = etbl.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name)
        _apply_font(r, size=Pt(10.5), bold=True)
    for i, row in enumerate(entity_rows, start=1):
        for j, val in enumerate(row):
            cell = etbl.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(val)
            _apply_font(r, size=Pt(10), mono=(j == 0))

    add_heading(doc, "3.3 关系类型（RelationType）", level=2)
    add_para(doc, [
        "同样封闭的 8 种关系类型，覆盖故障链路的因果、归属、诊断与记录四类语义：",
    ])

    relation_rows = [
        ("CAUSES",        "引发",         "组件故障或根因引发故障现象"),
        ("BELONGS_TO",    "属于",         "组件属于某设备"),
        ("RESOLVES",      "解决",         "解决方案解决某故障现象"),
        ("DIAGNOSES",     "排查",         "错误码用于排查某组件或故障"),
        ("HAS_FAULT",     "设备存在故障", "设备存在某种失效模式"),
        ("ROOT_CAUSE_OF", "根因对应故障", "某根因导致某失效模式"),
        ("TREATED_BY",    "由措施处理",   "故障由某解决方案处理"),
        ("RECORDED_IN",   "记录于工单",   "故障或操作记录于某工单"),
    ]
    rtbl = doc.add_table(rows=1 + len(relation_rows), cols=3)
    rtbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    rtbl.style = "Light Grid Accent 1"
    for i, name in enumerate(("枚举值", "中文含义", "语义描述")):
        cell = rtbl.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name)
        _apply_font(r, size=Pt(10.5), bold=True)
    for i, row in enumerate(relation_rows, start=1):
        for j, val in enumerate(row):
            cell = rtbl.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(val)
            _apply_font(r, size=Pt(10), mono=(j == 0))

    add_heading(doc, "3.4 知识图谱整体结构", level=2)
    add_para(doc, [
        "所有三元组共同构成一个有向知识图谱：",
    ])
    build_math_paragraph(doc, formula_kg())
    add_para(doc, [
        "其中 ",
        ("V", {"italic": True}),
        " 为实体节点集合，",
        ("E", {"italic": True}),
        " 为有向边集合，",
        ("R", {"italic": True}),
        " 为关系类型集合。图以 NetworkX 有向图（",
        ("DiGraph", {"mono": True}),
        "）在内存中维护，并序列化为 ",
        ("db/knowledge_graph.json", {"mono": True}),
        " 持久化。",
    ])

    # ======================================================================
    # 四、三元组提取流程
    # ======================================================================
    add_heading(doc, "四、三元组提取流程", level=1)

    add_heading(doc, "4.1 文本块预处理", level=2)
    add_para(doc, [
        "文档切分后的原始 chunks 在送入 LLM 前，先将相邻两个 chunk 合并为一组，"
        "以为 LLM 提供更完整的上下文（配置项 ",
        ("CHUNK_GROUP_SIZE = 2", {"mono": True}),
        "）：",
    ])
    build_math_paragraph(doc, formula_chunk_merge())
    add_para(doc, [
        "合并后的块数约为原始数量的一半，保留了段落间的语义延续性，"
        "有助于提取跨段落的实体关系。",
    ])

    add_heading(doc, "4.2 LLM 调用与 Schema 约束", level=2)
    add_para(doc, [
        "三元组提取由 ",
        ("GraphExtractionSkill", {"mono": True}),
        " 调用大语言模型完成。提示词严格约束输出格式，这是轻量化设计的核心手段——"
        "封闭的 Schema 既降低了 LLM 的自由发挥空间（减少幻觉），"
        "又保证了所有三元组类型的一致性，无需后处理归一化：",
    ])
    add_bullet(doc, [("系统提示词", {"bold": True}),
                     ("：", {}),
                     ('"你是一个工业故障知识图谱抽取助手，只返回 JSON，不附加任何解释。"', {"mono": True})])
    add_bullet(doc, [("实体类型约束", {"bold": True}),
                     ("：必须为 EntityType 枚举中的值，不得自行扩展。", {})])
    add_bullet(doc, [("关系类型约束", {"bold": True}),
                     ("：必须为 RelationType 枚举中的值，不得自行扩展。", {})])
    add_bullet(doc, [("必填字段", {"bold": True}),
                     ("：每条三元组必须包含 head、head_type、relation、tail、tail_type 五个字段。", {})])
    add_bullet(doc, [("无符合条件时", {"bold": True}),
                     ("：返回空数组 []，不得捏造三元组。", {})])
    add_para(doc, [
        "LLM 返回原始文本后，解析逻辑会自动去除 Markdown 代码块包裹（",
        ("```json...```", {"mono": True}),
        "），并对每条记录做字段完整性和类型白名单校验，过滤不合规条目。",
    ])

    add_heading(doc, "4.3 并发提取与去重", level=2)
    add_para(doc, [
        "为提升吞吐量，",
        ("TripleExtractor.batch_extract", {"mono": True}),
        " 使用线程池并发调用 LLM，最大并发数为 ",
        ("ASYNC_TRIPLE_EXTRACT_MAX_WORKERS = 30", {"mono": True}),
        "，相邻请求最小间隔为 1 秒以避免触发 API 速率限制。"
        "并发完成后对全量三元组做精确去重：",
    ])
    build_math_paragraph(doc, formula_dedup())
    add_para(doc, [
        "去重键为 (head, relation, tail) 三元组，与来源文件无关，"
        "保证同一知识关系在图中只有一条边（幂等性）。",
    ])

    # ======================================================================
    # 五、图存储与持久化
    # ======================================================================
    add_heading(doc, "五、图存储与持久化", level=1)

    add_heading(doc, "5.1 NetworkX 内存图", level=2)
    add_para(doc, [
        ("NetworkXGraphRepository", {"mono": True}),
        " 以 NetworkX ",
        ("DiGraph", {"mono": True}),
        " 在进程内存中维护图结构，通过 ",
        ("threading.Lock", {"mono": True}),
        " 保证并发写入安全。选择 NetworkX 而非外部图数据库，"
        "是轻量化原则的直接体现：无需安装和运维额外服务，"
        "启动时从 JSON 文件加载，10 万节点规模加载时间不超过 2 秒。",
    ])
    add_code_block(doc,
        "# 节点格式\n"
        "{ \"id\": \"<实体名>\", \"attrs\": { \"entity_type\": \"<EntityType>\" } }\n\n"
        "# 边格式\n"
        "{ \"src\": \"<头实体>\", \"dst\": \"<尾实体>\","
        " \"relation\": \"<RelationType>\", \"source_file\": \"<文件名>\" }"
    )
    add_para(doc, [
        "为控制图规模（PathRAG 的剪枝思想），每个节点的出边数量硬性上限为 ",
        ("MAX_EDGES_PER_NODE = 20", {"mono": True}),
        "，超出时由 ",
        ("prune()", {"mono": True}),
        " 裁剪，避免高频实体占用过多内存与查询时间。",
    ])

    add_heading(doc, "5.2 向量存储中的图数据", level=2)
    add_para(doc, [
        "实体与关系被分别嵌入到 ChromaDB 的两个独立集合，支持基于自然语言查询的模糊寻点。"
        "这是 LightRAG 双层结构思想在本系统中的工程化体现：",
    ])

    chroma_rows = [
        ("graph_entities",  "实体语义搜索", "ent_ + MD5(name)[0:12]",    "name, type, source_file",          "0.85"),
        ("graph_relations", "关系语义搜索", "rel_ + MD5(h|r|t)[0:12]",   "head, relation, tail, source_file", "0.50"),
    ]
    ctbl = doc.add_table(rows=1 + len(chroma_rows), cols=5)
    ctbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    ctbl.style = "Light Grid Accent 1"
    for i, name in enumerate(("集合名", "用途", "ID 格式", "元数据字段", "相似度阈值")):
        cell = ctbl.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name)
        _apply_font(r, size=Pt(10.5), bold=True)
    for i, row in enumerate(chroma_rows, start=1):
        for j, val in enumerate(row):
            cell = ctbl.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(val)
            _apply_font(r, size=Pt(10), mono=(j in (0, 2, 3, 4)))

    add_para(doc, [
        "实体的嵌入文本为实体名称本身；关系的嵌入文本格式为 ",
        ('"<head> <relation> <tail>"', {"mono": True}),
        "。相似度由 L2 距离转换而来：",
    ])
    build_math_paragraph(doc, formula_entity_score())
    add_para(doc, [
        "实体集合的阈值（0.85）高于关系集合（0.50）：实体名空间密集，"
        "需要更严格的过滤；关系描述文本较长，语义距离更分散，阈值可适当放宽。",
    ])

    # ======================================================================
    # 六、图查询与检索
    # ======================================================================
    add_heading(doc, "六、图查询与检索", level=1)

    add_heading(doc, "6.1 两阶段检索策略", level=2)
    add_para(doc, [
        "在线查询采用 ",
        ("向量寻点 + 图拓扑扩展", {"bold": True}),
        " 的两阶段策略，参照 HippoRAG 的海马体模型："
        "向量检索模拟感知层（快速定位相关节点），图拓扑扩展模拟联想层（激活关联记忆）。",
    ])
    add_bullet(doc, [
        ("阶段一 — 向量寻点", {"bold": True}),
        ("：以用户问题为查询，在 graph_entities 集合中检索相似度最高的实体，"
         "得到种子实体集合 S（top_k = 20，阈值 0.85）。", {}),
    ])
    add_bullet(doc, [
        ("阶段二 — BFS 扩展", {"bold": True}),
        ("：以 S 中每个节点为起点，在 NetworkX 图上执行广度优先搜索，"
         "展开 h = 2 跳范围内的所有可达三元组。", {}),
    ])

    add_heading(doc, "6.2 BFS 子图展开", level=2)
    add_para(doc, [
        "子图展开的形式化定义：",
    ])
    build_math_paragraph(doc, formula_bfs())
    add_para(doc, [
        "其中 ",
        ("d_G(s, u)", {"italic": True}),
        " 为图中 ",
        ("s", {"italic": True}),
        " 到 ",
        ("u", {"italic": True}),
        " 的最短跳数。2 跳展开在覆盖直接关联与间接关联的同时，"
        "将路径数量控制在可管理范围内（受 MAX_EDGES_PER_NODE 与 max_graph_paths 双重约束）。",
    ])
    add_para(doc, [
        "展开结果以路径列表形式返回，每条路径包含完整的溯源信息：",
    ])
    add_code_block(doc,
        "# GraphPath 条目示例\n"
        "{\n"
        "    \"from\":        \"传感器A\",\n"
        "    \"relation\":    \"CAUSES\",\n"
        "    \"to\":          \"温度过高\",\n"
        "    \"score\":       0.92,\n"
        "    \"confidence\":  0.85,\n"
        "    \"source_file\": \"设备手册.pdf\"\n"
        "}"
    )

    add_heading(doc, "6.3 完整查询流程", level=2)
    add_code_block(doc,
        "① 向量寻点\n"
        "   vector_store.search_entities(query, top_k=20, threshold=0.85)\n"
        "   → seed_names: list[str]\n\n"
        "② BFS 子图展开\n"
        "   graph_repo.expand_subgraph(seed_names, hops=2)\n"
        "   → graph_paths: list[GraphPath]\n\n"
        "③ 原文片段检索\n"
        "   vector_store.search(query)\n"
        "   → sources: list[dict]\n\n"
        "④ 上下文管理编排\n"
        "   ContextManager（PathPruning + MMR + Reorder）\n"
        "   → 结构化 Prompt 中的三段式上下文"
    )

    # ======================================================================
    # 七、图的生命周期管理
    # ======================================================================
    add_heading(doc, "七、图的生命周期管理", level=1)

    add_heading(doc, "7.1 图的构建（文件导入）", level=2)
    add_para(doc, [
        ("ImportFileUseCase.embed_file", {"mono": True}),
        " 在完成向量化后异步触发图构建。以降级策略执行——"
        "图构建失败不影响向量检索可用性，在线查询不等待建图完成：",
    ])
    add_code_block(doc,
        "文件上传\n"
        "  ↓\n"
        "文档加载 → 分割 chunks → 向量化 → 存入 rag_docs（同步）\n"
        "  ↓（异步，失败降级）\n"
        "batch_extract(chunks)\n"
        "  ├─ 合并相邻 chunks（每 2 个一组）\n"
        "  └─ ThreadPoolExecutor（30 线程）并发调用 LLM\n"
        "  ↓\n"
        "去重 → add_entity()   → graph_entities（ChromaDB）\n"
        "     → add_relation() → graph_relations（ChromaDB）\n"
        "     → add_triples()  → NetworkX DiGraph\n"
        "     → save()         → db/knowledge_graph.json"
    )

    add_heading(doc, "7.2 图的清理（文件删除）", level=2)
    add_para(doc, [
        "删除文件时，",
        ("DeleteFileUseCase", {"mono": True}),
        " 按文件名同步清理图数据，三个存储层保持一致：",
    ])
    add_bullet(doc, [("vector_store.delete_entities_by_file()", {"mono": True}),
                     ("  →  删除 graph_entities 中该文件的实体", {})])
    add_bullet(doc, [("vector_store.delete_relations_by_file()", {"mono": True}),
                     ("  →  删除 graph_relations 中该文件的关系", {})])
    add_bullet(doc, [("graph_repo.remove_by_file()", {"mono": True}),
                     ("  →  删除 NetworkX 图中所有 source_file 匹配的边，并清除孤立节点", {})])
    add_para(doc, [
        "按文件增量删除的能力，是轻量化方案中刻意保留的运维友好性设计——"
        "全量 GraphRAG 通常需要整图重建才能完成删除操作。",
    ])

    # ======================================================================
    # 八、与上下文管理模块的集成
    # ======================================================================
    add_heading(doc, "八、与上下文管理模块的集成", level=1)

    add_para(doc, [
        "BFS 展开得到的图路径经 ",
        ("PathPruningAlgorithm", {"mono": True}),
        " 过滤（按置信度阈值 + 关系类型多样性）后，"
        "与向量检索结果一同组装为三段式 Prompt 上下文，"
        "注入 LLM 的 user 消息（详见《上下文管理算法介绍文档》第 2.3 节）：",
    ])
    add_code_block(doc,
        "【关联实体】\n"
        "传感器A, 温度过高, 冷却系统\n\n"
        "【知识图谱路径】\n"
        "  - 传感器A --[CAUSES]--> 温度过高\n"
        "  - 温度过高 --[ROOT_CAUSE_OF]--> 冷却系统失效\n"
        "  - 冷却系统失效 --[TREATED_BY]--> 更换冷却液\n\n"
        "【相关原文片段】\n"
        "[设备手册.pdf]\n"
        "传感器A负责监测冷却系统出口温度……"
    )
    add_para(doc, [
        "结构化图路径与原文片段并列呈现：LLM 可利用图中的显式因果链做多跳推理，"
        "同时从原文中获取细节依据，两者互补，提升故障诊断问答的准确性与可解释性。",
    ])

    # ======================================================================
    # 九、关键参数速查
    # ======================================================================
    add_heading(doc, "九、关键参数速查", level=1)

    param_rows = [
        ("CHUNK_GROUP_SIZE",               "2",    "TripleExtractor",             "批量提取时相邻 chunk 的合并数量"),
        ("ASYNC_TRIPLE_EXTRACT_MAX_WORKERS","30",   "TripleExtractor",             "并发提取线程池大小"),
        ("request_interval",               "1.0 s","TripleExtractor",             "LLM 请求的最小时间间隔"),
        ("MAX_EDGES_PER_NODE",             "20",   "NetworkXGraphRepository",     "每个节点的出边上限（PathRAG 剪枝）"),
        ("expand_subgraph hops",           "2",    "NetworkXGraphRepository",     "BFS 展开的最大跳数"),
        ("entity score threshold",         "0.85", "ChromaVectorStoreRepository", "实体向量搜索相似度阈值"),
        ("relation score threshold",       "0.50", "ChromaVectorStoreRepository", "关系向量搜索相似度阈值"),
        ("entity search top_k",            "20",   "ChromaVectorStoreRepository", "实体向量搜索返回数量上限"),
    ]
    ptbl = doc.add_table(rows=1 + len(param_rows), cols=4)
    ptbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    ptbl.style = "Light Grid Accent 1"
    for i, name in enumerate(("参数", "默认值", "所在模块", "说明")):
        cell = ptbl.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name)
        _apply_font(r, size=Pt(10.5), bold=True)
    for i, row in enumerate(param_rows, start=1):
        for j, val in enumerate(row):
            cell = ptbl.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(val)
            _apply_font(r, size=Pt(10), mono=(j in (0, 1, 2)))

    # 页脚
    add_hr(doc)
    foot = doc.add_paragraph()
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = foot.add_run(
        "文档版本：v2.0  |  对应代码路径："
        "Backend/Domain/  ·  Backend/Infrastructure/  ·  Backend/Application/UseCases/"
    )
    _apply_font(r, size=Pt(9), italic=True)

    return doc


if __name__ == "__main__":
    out_path = Path(__file__).parent / "知识图谱模块介绍文档.docx"
    document = build_document()
    document.save(str(out_path))
    print(f"Saved: {out_path}")
