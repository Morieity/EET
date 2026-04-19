"""
生成项目人工智能技术介绍文档（Word格式）
样式：简洁纯文本 + LaTeX公式注释，无表格无花哨格式
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

doc = Document()

# ── 页面边距 ──────────────────────────────────────────
section = doc.sections[0]
section.page_width  = Cm(21)
section.page_height = Cm(29.7)
section.left_margin   = Cm(3.17)
section.right_margin  = Cm(3.17)
section.top_margin    = Cm(2.54)
section.bottom_margin = Cm(2.54)

# ── 字体常量 ──────────────────────────────────────────
FONT_BODY   = "Times New Roman"
FONT_BODY_CN = "宋体"
FONT_HEAD   = "Times New Roman"
FONT_HEAD_CN = "黑体"
SIZE_TITLE  = Pt(18)
SIZE_H1     = Pt(14)
SIZE_H2     = Pt(12)
SIZE_BODY   = Pt(11)
SIZE_SMALL  = Pt(10)

def set_font(run, en_font, cn_font, size, bold=False, color=None):
    run.font.name = en_font
    run.font.size = size
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    r = run._r
    rPr = r.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:eastAsia"), cn_font)
    rPr.insert(0, rFonts)

def add_title(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(18)
    run = p.add_run(text)
    set_font(run, FONT_HEAD, FONT_HEAD_CN, SIZE_TITLE, bold=True)

def add_h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run(text)
    set_font(run, FONT_HEAD, FONT_HEAD_CN, SIZE_H1, bold=True)

def add_h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after  = Pt(2)
    run = p.add_run(text)
    set_font(run, FONT_HEAD, FONT_HEAD_CN, SIZE_H2, bold=True)

def add_body(text, indent=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(4)
    if indent:
        p.paragraph_format.first_line_indent = Pt(22)
    p.paragraph_format.line_spacing = Pt(18)
    run = p.add_run(text)
    set_font(run, FONT_BODY, FONT_BODY_CN, SIZE_BODY)

def add_formula(label, formula_text):
    """一行居中公式，旁注编号"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run(f"{formula_text}    {label}")
    set_font(run, FONT_BODY, FONT_BODY_CN, SIZE_BODY)

def add_bullet(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1.0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(3)
    run = p.add_run("• " + text)
    set_font(run, FONT_BODY, FONT_BODY_CN, SIZE_BODY)

def add_small(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Cm(1.0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(2)
    run = p.add_run(text)
    set_font(run, FONT_BODY, FONT_BODY_CN, SIZE_SMALL, color=(100, 100, 100))

def add_sep():
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(2)

# ═══════════════════════════════════════════════════════
#  正文内容
# ═══════════════════════════════════════════════════════

add_title("基于大语言模型的知识增强智能问答系统\n——人工智能技术说明文档")

add_body("本文档系统介绍项目所采用的人工智能核心技术，重点阐述两项主要创新：面向长上下文的多级动态上下文处理算法，以及适用于资源受限环境的轻量化知识图谱构建方案。", indent=True)

# ─── 一、系统概述 ─────────────────────────────────────
add_h1("一、系统概述")

add_body(
    "本项目构建了一套面向工业故障诊断领域的智能问答系统，核心架构为检索增强生成（Retrieval-Augmented Generation，RAG）范式。系统以大语言模型（LLM）为推理核心，结合向量语义检索与知识图谱结构化推理，实现对复杂技术问题的精准回答。", indent=True
)

add_body(
    "系统主要由以下四个技术层次构成：文档预处理与向量化入库、知识图谱异步构建与更新、多路检索与上下文动态装配、以及基于流式 SSE 协议的 LLM 推理生成。",
    indent=True
)

add_sep()

# ─── 二、向量语义检索 ─────────────────────────────────
add_h1("二、向量语义检索")

add_body(
    "系统采用 ChromaDB 作为向量存储后端，通过文本嵌入模型将文档切片（Chunk）转化为高维稠密向量，支持基于余弦相似度的近似最近邻检索。",
    indent=True
)

add_h2("2.1  文档分块策略")
add_body(
    "原始文档经过语义感知分块处理后存入向量数据库。每个切片保留其原始文本内容与元数据（来源文件、所属页面、切片序号），以支持后续的来源溯源与上下文扩展。"
)

add_h2("2.2  相似度检索")
add_body(
    "给定用户查询 q，系统计算查询向量与所有切片向量的余弦相似度，取 Top-K 结果作为候选证据集："
)
add_formula("(1)", "sim(q, d) = ( q · d ) / ( ‖q‖ · ‖d‖ )")
add_body(
    "其中 q 与 d 分别为查询和文档切片的嵌入向量。检索结果携带相似度得分，供后续上下文处理算法使用。"
)

add_sep()

# ─── 三、轻量化知识图谱构建（创新点一） ────────────────
add_h1("三、轻量化知识图谱构建（创新点）")

add_body(
    "传统 GraphRAG 方案（如 Microsoft GraphRAG）依赖 Neo4j 等重型图数据库，全局离线建图，难以在资源受限的工业部署环境中落地。本项目提出一套轻量化知识图谱构建与检索方案，综合借鉴 LightRAG、PathRAG、HippoRAG、Query-Driven GraphRAG 四篇前沿论文的核心思想，在本地内存图上实现结构化语义推理。",
    indent=True
)

add_h2("3.1  设计原则")
add_bullet("拒绝全局重型图谱：使用 NetworkX 内存图代替外部图数据库，零运维开销。")
add_bullet("Schema 定向抽取：限定实体类型（COMPONENT、SYMPTOM、ERROR_CODE、SOLUTION）与关系类型（CAUSES、RESOLVES、BELONGS_TO、DIAGNOSES），避免开放式信息抽取的算力浪费。")
add_bullet("向量与图算法融合：ChromaDB 负责语义召回种子实体，NetworkX 负责拓扑邻域扩展。")
add_bullet("异步建图、在线查询解耦：文件导入时触发异步图构建，不阻塞在线服务响应。")

add_h2("3.2  三层向量集合设计（源自 LightRAG）")
add_body(
    "受 LightRAG 双层索引架构启发，系统在 ChromaDB 中维护三个独立 Collection："
)
add_bullet("rag_docs：原始文档切片及其向量，用于语义片段召回。")
add_bullet("graph_entities：实体名称、类型及其向量，用于种子实体语义寻点。")
add_bullet("graph_relations：三元组描述文本（head relation tail）及其向量，用于关系语义检索。")
add_body(
    "查询阶段联合使用三个 Collection：先对 graph_entities 做语义检索获取种子实体，再通过图邻域扩展获取关联路径，最后结合 rag_docs 的原始片段共同送入 LLM。"
)

add_h2("3.3  两阶段图检索（源自 HippoRAG）")
add_body(
    "HippoRAG 通过模拟海马体的工作机制，将检索分为【向量寻点】与【图激活】两个阶段。本项目的实现方式如下："
)
add_body("第一阶段（向量寻点）：对用户查询做实体向量检索，获取 Top-K 种子实体节点 S。")
add_body("第二阶段（图发散）：以 S 为起点，在 NetworkX 内存图上执行广度优先搜索（BFS），获取 1~2 跳内的关联子图，提取实体-关系路径集合 P：")
add_formula("(2)", "P = { (s, r₁, v₁, r₂, v₂, …) | s ∈ S, depth ≤ 2 }")

add_h2("3.4  图路径剪枝（源自 PathRAG）")
add_body(
    "PathRAG 指出大规模图谱中存在大量冗余路径。本项目在建图时与查询时分别施加剪枝："
)
add_body("建图剪枝：每个节点最多保留 MAX_EDGES_PER_NODE = 20 条出边，合并同义关系，基于词频赋予边权重，低频边在 prune() 时被移除。")
add_body("查询剪枝（PathPruningAlgorithm）：对检索到的路径集合，按置信度阈值 τ 过滤，并在关系类型维度做多样性保留——同类关系只保留置信度最高的 k 条路径：")
add_formula("(3)", "P' = { p ∈ P | conf(p) ≥ τ },  |{ p ∈ P' | type(p) = t }| ≤ k  ∀t")

add_h2("3.5  在线局部建图（源自 Query-Driven GraphRAG）")
add_body(
    "Query-Driven GraphRAG 提出查询时在线对召回文档做局部建图，规避离线全局图构建的高开销。本项目在文件导入阶段异步执行 LLM 三元组抽取，同时提供降级策略——若建图服务异常，系统自动回退到纯向量检索模式，确保在线服务不中断。"
)

add_sep()

# ─── 四、上下文处理算法（创新点二） ──────────────────
add_h1("四、上下文处理算法（创新点）")

add_body(
    "RAG 系统的性能上限不仅由检索质量决定，更受制于送入 LLM 的上下文质量。本项目设计了一套多级动态上下文处理流水线（ContextManagement），综合应用 7 个算法模块，在有限 Token 预算内最大化上下文的信息密度与检索有效性。",
    indent=True
)

add_h2("4.1  MMR 去重（MMRDeduplicationAlgorithm）")
add_body(
    "最大边际相关度（Maximal Marginal Relevance，MMR）算法在保证相关性的同时减少候选文档之间的冗余。每次选择新文档 d* 时，最大化如下目标函数："
)
add_formula("(4)", "d* = argmax_{d ∈ R\\S} [ λ·rel(d, q)  −  (1−λ)·max_{s ∈ S} sim(d, s) ]")
add_body(
    "其中 R 为候选集，S 为已选集，rel 为与查询的相关度，sim 为文档间相似度，λ 为权衡系数（默认 0.7）。在存在大量重复切片的工程场景中，MMR 能有效提升上下文信息密度。"
)

add_h2("4.2  检索重排序（RetrievalReorderingAlgorithm）")
add_body(
    '论文《Retrieval Head Mechanistically Explains Long-Context Factuality》（ICLR 2025）通过对注意力机制的深度分析，发现 Transformer 中存在【检索头】（Retrieval Head），这些注意力头对序列首尾位置的 Token 关注度显著高于中间位置。'
)
add_body(
    "基于此发现，算法将相关度最高的文档片段交替排列在上下文的首部与尾部——得分最高的放首位，次高的放末位，依此交替——而非按相关度简单降序排列："
)
add_formula("(5)", "order = [ d₁, d₃, d₅, …, d₆, d₄, d₂ ]")
add_body(
    "此排列确保关键证据处于模型注意力最强的位置，在长上下文场景下显著提升答案准确率。"
)

add_h2("4.3  Token 预算管理（TokenBudgetingAlgorithm）")
add_body(
    "当上下文总长度接近模型窗口上限时，系统进行分级压缩。定义填充率 ρ = 当前 Token 数 / 窗口上限，根据阈值触发不同动作："
)
add_bullet("ρ > 0.6：触发历史对话分层压缩（compress_history_tier2）。")
add_bullet("ρ > 0.8：追加查询感知压缩（compress_history_tier3）并对向量文档保留 50%。")
add_bullet("ρ > 0.9：进一步限制知识图谱为单跳、移除社区摘要、硬性截断向量 Top-K。")
add_body(
    "系统提示（system prompt）与用户查询始终视为不可压缩内容，保证推理基线不受损。"
)

add_h2("4.4  历史分层（HistoryTieringAlgorithm）")
add_body(
    "受 MemAgent 论文启发，算法将对话历史按时序划分为三层："
)
add_bullet("热层（Hot）：最近 hot_size 轮，完整保留原始消息。")
add_bullet("温层（Warm）：前 warm_size 轮，压缩为关键要点摘要。")
add_bullet("冷层（Cold）：更早轮次，提炼为单段高度概括的历史摘要。")
add_body(
    "温层摘要时，优先保留包含业务关键词（故障、原因、解决、操作等）及信息密度高的轮次，最多提取 5 条要点，组织为结构化的 [Hot Turns] / [Warm Memory Summary] / [Cold Memory Summary] 三段式 prompt 块。"
)

add_h2("4.5  查询感知压缩（QueryAwareCompressionAlgorithm）")
add_body(
    "借鉴 LongLLMLingua 与 LLMLingua-2 的查询感知压缩思路，算法对每篇候选文档按目标保留率 keep_rate（默认 0.5）进行抽取式压缩。核心步骤为："
)
add_body("1. 用 jieba 分词提取查询关键词集合 Q（过滤停用词与通用词）。")
add_body("2. 将文档切分为句子，计算每句与 Q 的查询相关得分：")
add_formula("(6)", "score(sent) = |tokens(sent) ∩ Q| / |tokens(sent)|  +  α·domain_bonus(sent)")
add_body("3. 按得分降序保留前 keep_rate 比例的句子，直至达到 compression_min_chars 字符下限。")
add_body(
    "其中 domain_bonus 对包含工业术语字典词汇的句子给予额外加权，确保关键技术信息不被误删。"
)

add_h2("4.6  查询末位保障（QueryPlacementAlgorithm）")
add_body(
    "根据检索头机制的研究结论，用户查询应始终位于上下文末尾以获得最强注意力激活。算法保证多路上下文合并后，当前用户查询追加至最后一条 user 消息末尾，并在必要时将末尾 user 消息移位至序列终点。"
)

add_sep()

# ─── 五、LLM 推理与接口设计 ─────────────────────────
add_h1("五、大语言模型推理与接口设计")

add_body(
    "系统将 LLM 调用抽象为统一接口，兼容 DeepSeek、OpenAI 及所有兼容 OpenAI API 格式的推理服务，仅需切换 base_url 与 api_key 即可无缝迁移。",
    indent=True
)
add_body(
    "推理采用流式 SSE（Server-Sent Events）协议，前端可实时接收生成内容。响应事件类型包括：conversation（文本分片）、sources（来源证据）、token（Token 统计）、done（完成标记）、error（异常通知）。"
)
add_body(
    "知识图谱三元组抽取同样通过 LLM 完成，Prompt 严格限定输出格式为 JSON 数组，包含 head、relation、tail、confidence 四个字段，系统对输出做结构化解析与置信度过滤后写入图存储。"
)

add_sep()

# ─── 六、参考文献 ───────────────────────────────────
add_h1("六、主要参考文献")

refs = [
    "[1]  Guo H, et al. LightRAG: Simple and Fast Retrieval-Augmented Generation. arXiv, 2024.",
    "[2]  Chen B, et al. PathRAG: Pruning Graph-based RAG with Relational Paths. arXiv:2502.14902, 2025.",
    "[3]  Gutierrez B J, et al. HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models. arXiv, 2024.",
    "[4]  Edge D, et al. From Local to Global: A Graph RAG Approach to Query-Focused Summarization. arXiv:2404.16130, 2024.",
    "[5]  Wu H, et al. Long-Context LLMs Meet RAG: Overcoming Challenges for Long Inputs in RAG. ICLR, 2025.",
    "[6]  Fei Z, et al. Retrieval Head Mechanistically Explains Long-Context Factuality. arXiv:2404.15574, 2024.",
    "[7]  Jiang H, et al. LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios. ACL, 2024.",
    "[8]  Pan X, et al. LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression. ACL Findings, 2024.",
    "[9]  Ning W, et al. MemAgent: Reshaping Long-Context LLM with Multi-Conv RL-based Memory Agent. arXiv:2507.02259, 2025.",
]
for r in refs:
    add_small(r)

# ── 保存 ─────────────────────────────────────────────
output_path = r"C:\Users\tangx\desktop\rag\docs\人工智能技术介绍文档.docx"
doc.save(output_path)
print(f"已生成：{output_path}")
