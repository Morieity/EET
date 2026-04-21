# RAG 上下文管理 · 前沿论文与 Prompt 架构设计

---

## 一、前沿论文索引

### 📌 你提到的论文

| 论文 | 类别 | 核心贡献 |
|------|------|----------|
| Adaptive Context Compression Techniques for LLMs in Long-Running Interactions | Context Compression | 自适应滑动窗口压缩，动态调整上下文保留策略 |
| MemAgent: Reshaping Long-Context LLM with Multi-Conv RL-based Memory Agent | RL Memory | 多轮强化学习训练记忆 Agent，自适应摘要与选择性保留 |
| Retrieval Head Mechanistically Explains Long-Context Factuality | Mechanistic | 从注意力机制层面解释长上下文事实性，证明末尾 token 注意力最高 |
| NoLiMa: Non-Literal Matching Benchmark for Long-Context | Benchmark | 非字面语义匹配的长上下文评测基准 |

---

### 📚 RAG 与长上下文管理

| 论文 | 会议/来源 | 核心发现 |
|------|-----------|----------|
| Long Context vs. RAG for LLMs: An Evaluation and Revisits | arXiv 2501.01880 · 2024.12 | LC 在 Wikipedia QA 上总体优于 RAG；摘要式检索接近 LC 效果；RAG 在对话场景有优势 |
| Long-Context LLMs Meet RAG: Overcoming Challenges for Long Inputs in RAG | ICLR 2025 | **硬负样本**是 RAG 性能下降主因；Retrieval Reordering 是强力 training-free 优化 |
| Chain of Agents: LLMs Collaborating on Long-Context Tasks | NeurIPS 2024 | 多 Agent 协作框架（CoA），超越 RAG 和单纯长上下文 LLM |
| U-NIAH: Unified RAG and LLM Evaluation for Long Context | 2025 | 统一的 Needle-In-A-Haystack 评测框架，涵盖 RAG 与 LC 场景 |
| Retrieval Augmented Generation or Long-Context LLMs? A Comprehensive Study | EMNLP 2024 Industry | 资源充足时 LC 更强，成本敏感场景 RAG 有优势 |
| LaRA: Benchmarking RAG and Long-Context LLMs — No Silver Bullet | 2025 | 无万能方案，最优策略依赖模型大小、任务类型、上下文长度 |

---

### 🗜️ Prompt 压缩与上下文压缩

| 论文 | 会议/来源 | 方法类型 | 核心指标 |
|------|-----------|----------|----------|
| LLMLingua / LongLLMLingua | EMNLP 2023 · ACL 2024 · Microsoft | Hard · Token Pruning | 最高 20× 压缩，RAG 性能提升 21.4%，token 减少 75% |
| LLMLingua-2 | ACL 2024 Findings | Hard · Data Distillation | 3x-6x 速度提升，任务无关压缩 |
| ICAE: In-context Autoencoder for Context Compression | 2023/2024 | Soft · Memory Slots | 4× 压缩率，仅增加 1% 参数，Llama 上验证 |
| AutoCompressor | 2023 | Soft · Continuous Embeddings | 自适应上下文压缩为 summary vectors |
| Prompt Compression for LLMs: A Survey | NAACL 2025 Oral | Survey | 全面梳理 Hard/Soft 两类方法体系 |
| ProCut: Prompt Compression via Attribution Estimation | EMNLP Industry 2025 | Hard · SHAP Attribution | 段落级归因分析，Shapley 值驱动段落剪枝 |
| Pretraining Context Compressor (PCC) | Microsoft 2025 | Soft · Universal | 通用压缩器，支持 16× 压缩率 |
| AdaComp: Extractive Context Compression with Adaptive Predictor | 2024 | Hard · Extractive | 自适应预测器，RAG 专用压缩 |

---

### 🕸️ 知识图谱增强 RAG（GraphRAG）

| 论文 | 会议/来源 | 核心贡献 |
|------|-----------|----------|
| From Local to Global: A Graph RAG Approach to Query-Focused Summarization | Microsoft 2024 | 社区检测 + 分层摘要，解决全局信息缺失问题，开源 |
| LightRAG: Simple and Fast Retrieval-Augmented Generation | 2024.10 | 双层检索（实体级+关系级），10× token 减少，65-80% 成本节省 |
| Graph Retrieval-Augmented Generation: A Survey | ACM TOIS 2024 | 首个 GraphRAG 综述，G-Indexing · G-Retrieval · G-Generation 三阶段框架 |
| KAG: Boosting LLMs in Professional Domains via Knowledge Augmented Generation | arXiv 2024 | KG + 向量混合检索，专业领域增强 |
| PathRAG: Pruning Graph-based RAG with Relational Paths | arXiv 2025 | 关系路径剪枝，减少图噪声注入 |
| RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval | ICLR 2024 | 递归抽象树形索引，层次化语义检索 |
| OG-RAG: Ontology-Grounded RAG for LLMs | arXiv 2024 | 本体论驱动的结构化检索 |
| Graphusion: A RAG Framework for Scientific KG Construction | WWW 2025 | 全局视角科学知识图谱构建 |
| GraphReader: Building Graph-based Agent for Long-Context | EMNLP 2024 Findings | 图结构 Agent 增强长上下文能力 |
| HybridRAG: KG + Vector Dual Retrieval | 2025 | 符号检索与语义检索融合，多跳推理 |

---

### 🧠 记忆与对话历史管理

| 论文 | 来源 | 核心机制 |
|------|------|----------|
| From Isolated Conversations to Hierarchical Schemas: Dynamic Tree Memory | 2024.10 | 树形层次记忆，叶节点为原始轮次，父节点为摘要 |
| Crafting Personalized Agents via RAG on Editable Memory Graphs | 2024.09 | 可编辑记忆图，支持增删改 |
| Human-inspired Episodic Memory for Infinite Context LLMs | 2024.07 | 仿人类情节记忆，支持无限上下文 |
| From RAG to Memory: Non-Parametric Continual Learning for LLMs | arXiv 2025.02 | 持续学习范式，RAG 作为外部记忆模块 |
| MemoryBank: Enhancing LLMs with Long-term Memory | 2024 | 用户历史与偏好存储，个性化增强 |
| Memolet: Reifying the Reuse of User-AI Conversational Memories | 2024.10 | 对话记忆复用机制 |
| AriGraph: Learning KG World Models with Episodic Memory | 2024.07 | 知识图谱世界模型 + 情节记忆 |

---

## 二、Prompt 五层架构设计

### 架构总览

```
┌─────────────────────────────────────────────────────────┐
│  ① SYSTEM PROMPT           [固定 · 永不压缩]            │
├─────────────────────────────────────────────────────────┤
│  ② KNOWLEDGE GRAPH CONTEXT  [结构化 · 实体关系]          │
├─────────────────────────────────────────────────────────┤
│  ③ VECTOR RAG DOCUMENTS     [语义检索 · 动态]            │
├─────────────────────────────────────────────────────────┤
│  ④ CONVERSATION HISTORY     [分层压缩 · 分级保留]        │
├─────────────────────────────────────────────────────────┤
│  ⑤ USER QUERY               [实时 · 末尾放置]            │
└─────────────────────────────────────────────────────────┘
                    ↓ LLM 生成
```

---

### ① 系统基础 Prompt（System Prompt）

**定位**：定义角色、能力边界、输出格式约束  
**研究依据**：ProCut（EMNLP 2025）用 Shapley 值证明系统指令是贡献度最高的段落  
**策略**：永不压缩，永不裁剪

**技术要素**：

| 要素 | 说明 |
|------|------|
| 角色定义 | 明确 LLM 的身份与专业领域 |
| 输出格式约束 | Markdown / JSON / 结构化等 |
| 安全边界声明 | 仅使用提供的上下文信息 |
| 语言 / 风格指定 | 语言、口吻、详细程度 |
| 任务类型声明 | QA / 摘要 / 推理 / 生成等 |

```
你是一个专业的知识库问答助手。请基于提供的知识上下文、历史对话和用户问题给出精准回答。
规则：
- 仅使用提供的上下文信息作答；
- 对不确定信息标注来源；
- 输出使用 Markdown 格式，结构清晰。
```

---

### ② 知识图谱上下文（KG Context）

**定位**：提供实体关系、多跳推理路径、全局语义骨架  
**研究依据**：GraphRAG（2024）解决传统 RAG 的"lost in the middle"和全局信息缺失；LightRAG 双层检索实现 10× token 减少

**检索策略**：

```
Local 检索：query → 实体识别 → 一跳邻域子图 → 路径文本化
Global 检索：query → 相关社区识别 → 社区摘要注入
融合策略：Local 优先（具体事实）+ Global 补充（背景语义）
PathRAG 剪枝：删除置信度低于阈值的关系路径
```

**注入格式**：

```
[实体关系]
- (实体A, 关系, 实体B)
- (Claude, 开发者, Anthropic) · (Anthropic, 成立于, 2021年)

[多跳推理路径]
Claude → 基于 → Transformer → 使用 → 注意力机制 → 解决 → 长序列理解

[社区主题摘要]
本知识库主要涵盖：LLM 技术演进（2020-2025）、RAG 架构设计、上下文管理策略。
```

**工具选型**：

| 场景 | 推荐工具 |
|------|----------|
| 全局查询 / 主题分析 | Microsoft GraphRAG |
| 高频更新 / 成本敏感 | LightRAG |
| 多跳推理 / 路径分析 | PathRAG |
| 专业领域 | KAG |
| 层次语义索引 | RAPTOR |

---

### ③ 向量数据库检索知识（Vector RAG）

**定位**：注入与当前 query 语义最相关的文档块  
**研究依据**：ICLR 2025 核心发现——硬负样本是 RAG 性能下降主因；Retrieval Reordering 可显著缓解 lost-in-middle

**关键处理步骤**：

```
1. 检索：强检索器（e5 / BGE）+ 小 K 值（3-5），优于弱检索器大 K 值
2. Reordering：最相关文档放首位和末位，次相关置中间
3. 压缩：LongLLMLingua query-aware 压缩，减少 75% token，性能提升 21.4%
4. 去冗余：MMR（最大边际相关性）剔除重复语义块
```

**注入格式**：

```
[Doc-1 · 相关度 0.94 · 来源: 文档名] 文档内容摘要或压缩后文本...
[Doc-2 · 相关度 0.91 · 来源: 文档名] 文档内容摘要或压缩后文本...
[Doc-3 · 相关度 0.87 · 来源: 文档名] 文档内容摘要或压缩后文本...
```

**Chunking 策略对比**：

| 策略 | 优点 | 适用场景 |
|------|------|----------|
| Fixed-size Chunking | 简单高效，实测效果不差 | 通用场景 |
| Proposition Chunking | 原子命题粒度，EM 提升 5.9-7.8% | 精确 QA |
| Semantic Chunking | 语义自适应分割 | 长文档 |
| RAPTOR 树形 | 层次化，支持全局查询 | 多文档摘要 |

---

### ④ 对话历史（Conversation History）

**定位**：提供多轮对话上下文，保持对话连贯性  
**研究依据**：MemAgent（2025）RL 驱动自适应摘要；Dynamic Tree Memory（2024）层次树形管理

**三级压缩策略**：

| 层级 | 轮次范围 | 处理方式 | 压缩率 |
|------|----------|----------|--------|
| Tier 1（热区） | 最近 3 轮 | 原文保留 | 1× |
| Tier 2（温区） | 第 4-10 轮 | LLM 提炼关键事实，每轮 2-3 句 | ~5× |
| Tier 3（冷区） | 10 轮以上 | ICAE 编码为 Memory Slots | ~4× |

**注入格式**：

```
[历史摘要 T-10 到 T-4]
用户咨询了 RAG 的基本原理和向量数据库选型，
系统介绍了 Chroma、Qdrant 和 Milvus 的差异。

[近期对话 T-2]
User: GraphRAG 和普通 RAG 最大的区别是什么？
Assistant: GraphRAG 最大的优势是能处理需要多跳推理的复杂问题，
           通过社区检测实现全局信息感知。

[近期对话 T-1]
User: 那 LightRAG 呢？
Assistant: LightRAG 在 GraphRAG 基础上引入了双层检索机制，
           实体级和关系级并行检索，token 消耗减少 10 倍。
```

---

### ⑤ 用户当前输入（User Query）

**定位**：驱动整个检索和生成流程的核心  
**研究依据**：Retrieval Head 论文从机制层面证明 LLM 对末尾 token 注意力权重最高，query 必须置于末尾

**Query 增强策略**：

| 策略 | 说明 | 论文依据 |
|------|------|----------|
| 末尾放置 | query 永远在 Prompt 最末 | Retrieval Head（2024） |
| HyDE | 生成假设文档扩展 query | HyDE（2022） |
| Query 分解 | 复杂问题拆分为子问题 | Chain-of-Agents（NeurIPS 2024） |
| 实体抽取 | 反向驱动 KG 和向量库检索 | GraphRAG（2024） |

```
如何在实际项目中同时使用向量数据库和知识图谱？有什么最佳实践吗？
```

---

## 三、完整 Prompt 模板

```
# ── ① SYSTEM PROMPT ──────────────────────────────────────
你是一个专业的知识库问答助手。请基于提供的知识上下文、历史对话和用户问题给出精准回答。
规则：仅使用提供的上下文信息；对不确定信息标注来源；输出使用 Markdown 格式。

# ── ② KNOWLEDGE GRAPH CONTEXT ────────────────────────────
[实体关系]
- (Claude, 开发者, Anthropic) · (Anthropic, 成立于, 2021年)
- (大语言模型, 核心技术, Transformer架构)

[多跳推理路径]
Claude → 基于 → Transformer → 使用 → 注意力机制 → 解决 → 长序列理解

[社区主题摘要]
本知识库主要涵盖：LLM 技术演进（2020-2025）、RAG 架构设计、上下文管理策略。

# ── ③ RETRIEVED DOCUMENTS (Top-K, reordered) ─────────────
[Doc-1 · 相关度 0.94] RAG 系统通过检索外部知识源来增强生成质量...
[Doc-2 · 相关度 0.91] LLMLingua 研究表明，对检索块进行 query-aware 压缩...
[Doc-3 · 相关度 0.87] GraphRAG 通过构建实体关系图解决了传统 RAG 的全局...

# ── ④ CONVERSATION HISTORY (compressed) ──────────────────
[历史摘要 T-5 到 T-2]
用户咨询了 RAG 的基本原理和向量数据库选型，
系统介绍了 Chroma、Qdrant 和 Milvus 的差异。

[原文 T-1] User: GraphRAG 和普通 RAG 最大的区别是什么？
[原文 T-1] Assistant: GraphRAG 最大的优势是能处理需要多跳推理的复杂问题...

[原文 T-0] User: 那 LightRAG 呢？
[原文 T-0] Assistant: LightRAG 在 GraphRAG 基础上引入了双层检索机制...

# ── ⑤ USER QUERY ─────────────────────────────────────────
如何在实际项目中同时使用向量数据库和知识图谱？有什么最佳实践吗？
```

---

## 四、上下文管理算法

### Token 预算分配

```
总预算分配建议（以 32K context 为例）：
┌──────────────────┬──────────┬────────────┐
│ 层级             │ 占比     │ Token 数   │
├──────────────────┼──────────┼────────────┤
│ System Prompt    │ 5%       │ ~1,600     │
│ KG Context       │ 20%      │ ~6,400     │
│ Vector RAG       │ 35%      │ ~11,200    │
│ History          │ 25%      │ ~8,000     │
│ User Query       │ 5%       │ ~1,600     │
│ 预留生成空间     │ 10%      │ ~3,200     │
└──────────────────┴──────────┴────────────┘
```

### 动态压缩触发规则

```
IF total_tokens > max_budget × 0.6:
    → 压缩 History Tier 2：LLM 提炼关键事实（~5× 压缩）

IF total_tokens > max_budget × 0.8:
    → 压缩 History Tier 3：ICAE Memory Slots（~4× 压缩）
    → 向量块 LLMLingua 剪枝（保留率 50%）

IF total_tokens > max_budget × 0.9:
    → KG 子图仅保留一跳关系，去除社区摘要

NEVER compress:
    → System Prompt（贡献度最高，ProCut 依据）
    → User Query（末尾注意力最高，Retrieval Head 依据）
```

### 检索驱动流程

```
用户 Query
    │
    ▼
实体抽取 + HyDE 扩展
    │
    ├──────────────────────────────┐
    ▼                              ▼
KG 子图检索                  向量 Top-K 检索
(Local: 一跳邻域)            (Dense + BM25 Hybrid)
(Global: 社区摘要)
    │                              │
    └──────────────┬───────────────┘
                   ▼
           结果融合 & MMR 去冗余
                   │
                   ▼
         Retrieval Reordering
         (最相关放首尾，减少 lost-in-middle)
                   │
                   ▼
        LongLLMLingua Query-Aware 压缩
                   │
                   ▼
             注入 Prompt ③ 层
```

---

## 五、工程落地建议

### 向量数据库选型

| 数据库 | 适用场景 | 优势 |
|--------|----------|------|
| **Milvus** | 大规模生产 | 高吞吐，分布式 |
| **Qdrant** | 中等规模 | 过滤丰富，Rust 实现 |
| **Chroma** | 本地开发 / 原型 | 轻量，易上手 |
| **Neo4j** | 图 + 向量混合 | 原生图数据库，GraphRAG 首选 |

### 压缩工具选型

| 工具 | 压缩率 | 场景 |
|------|--------|------|
| LLMLingua-2 | 3-20× | RAG 块压缩，任务无关 |
| LongLLMLingua | 4× | 长上下文 query-aware 压缩 |
| ICAE | 4× | 对话历史 Tier 3 压缩 |
| AutoCompressor | 可变 | 连续向量摘要 |

### 关键注意事项

> ⚠️ **硬负样本陷阱**（ICLR 2025）：增加 Top-K 不等于性能提升。强检索器（e5/BGE）+ K=3 通常优于弱检索器 + K=10。

> ⚠️ **Lost-in-Middle 问题**：长上下文中间位置的信息往往被忽视。Retrieval Reordering 是目前最简单有效的 training-free 解决方案。

> ⚠️ **GraphRAG Token 成本**：GraphRAG 实体抽取阶段 token 消耗是原文的数倍到数十倍。生产环境建议使用 LightRAG 代替，或仅对核心文档做图构建。

> ✅ **Query 末尾原则**：基于 Retrieval Head 论文，用户 query 始终置于 Prompt 末尾，这是成本最低、收益最高的优化。

---

*基于论文：GraphRAG (2024) · LightRAG (2024) · LongLLMLingua (ACL 2024) · ICAE (2024) · MemAgent (2025) · ProCut (EMNLP 2025) · Long-Context LLMs Meet RAG (ICLR 2025) · Retrieval Head (2024) · Dynamic Tree Memory (2024) · PathRAG (2025)*
