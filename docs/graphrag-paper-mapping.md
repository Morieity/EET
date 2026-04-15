# 轻量级 GraphRAG 论文落地映射说明

本文档说明项目中如何将四篇参考论文（LightRAG、PathRAG、HippoRAG、Query-Driven GraphRAG）的核心思想落地到代码实现。

---

## 一、论文与代码映射总览

| 论文 | 核心思想 | 项目中的实现 | 关键代码位置 |
|------|----------|-------------|-------------|
| **LightRAG** | 双层结构：低层实体 + 高层关系/主题，联合向量检索 | ChromaDB 三层 Collection 分层设计 | `ChromaVectorStoreRepository.py` |
| **PathRAG** | 图谱关系路径剪枝，去冗余边，降低遍历消耗 | NetworkX 图 `MAX_EDGES_PER_NODE=20` 剪枝 + 实体 upsert 去重 | `NetworkXGraphRepository.py` |
| **HippoRAG** | 模拟海马体：向量召回种子节点 → PPR 算法激活子图 | 向量寻点 + BFS 图发散的两阶段检索 | `ChatUseCase.py` |
| **Query-Driven GraphRAG** | 查询时在线局部建图，规避离线全局图构建 | 文件导入时异步建图，降级策略保证在线服务不受阻 | `ImportFileUseCase.py` |

---

## 二、LightRAG — 三层 Collection 分层设计

### 论文思想

LightRAG (Guo et al., 2024) 提出双层索引结构：低层存储实体节点及其向量，高层存储关系/主题描述及向量。查询时对两层分别做语义检索，再联合推理。

### 项目落地

在 `ChromaVectorStoreRepository` 中，通过三个独立的 ChromaDB Collection 实现分层：

```
ChromaDB
├── rag_docs          ← 低层：原始文档切片 + 向量（原有）
├── graph_entities    ← 实体层：实体名 + 类型 + 向量
└── graph_relations   ← 关系层：三元组描述 + 向量
```

**对应代码** — `Backend/Infrastructure/vectorstore/ChromaVectorStoreRepository.py`：

- **`_get_entity_store()`**（第25行）：获取 `graph_entities` collection，存储实体名称及其类型元数据
- **`_get_relation_store()`**（第31行）：获取 `graph_relations` collection，存储 `"{head} {relation} {tail}"` 文本
- **`add_entity()`**（第73行）：按实体名 MD5 生成 ID，支持 upsert 去重
- **`add_relation()`**（第110行）：按 `head|relation|tail` 生成唯一 ID，支持 upsert
- **`search_entities()`**（第90行）：查询时对实体名做语义检索，返回 Top-K 种子

查询阶段在 `ChatUseCase` 中联合使用：先 `search_entities()` 获取种子实体，再 `search()` 获取原文片段，两路结果合并送入 LLM。这正是 LightRAG "联合向量检索"的简化实现。

---

## 三、PathRAG — 图谱剪枝与去冗余

### 论文思想

PathRAG (Feb 2025) 指出大规模图谱中存在大量冗余路径，提出对关系路径做剪枝：合并同义关系、限制节点出边数上限、丢弃低频边，以降低遍历消耗并提升路径质量。

### 项目落地

**1）节点出边上限剪枝** — `Backend/Infrastructure/graphstore/NetworkXGraphRepository.py`：

```python
MAX_EDGES_PER_NODE = 20  # 第12行

def prune(self):          # 第120行
    for node in list(self._G.nodes):
        out_edges = list(self._G.out_edges(node, data=True))
        if len(out_edges) > MAX_EDGES_PER_NODE:
            sorted_edges = sorted(out_edges, key=lambda e: e[2].get("weight", 1), reverse=True)
            for _, v, _ in sorted_edges[MAX_EDGES_PER_NODE:]:
                self._G.remove_edge(node, v)
```

对每个节点，当出边数超过 20 条时，按权重排序保留前 20 条，丢弃低权重冗余边。

**2）实体 Upsert 去重** — `ChromaVectorStoreRepository.add_entity()`（第73行）：

同一实体名来自不同文件时，通过 MD5(name) 生成固定 ID，写入时自动覆盖旧记录，避免同义实体在 Collection 中重复膨胀。

**3）BFS 扩展时路径截断** — `NetworkXGraphRepository.expand_subgraph()`（第95行）：

通过 `hops=2` 参数严格限制扩展深度，且 `_build_enhanced_context()` 中最多取前 20 条路径（`graph_paths[:20]`），防止过长路径稀释上下文质量。

---

## 四、HippoRAG — 两阶段检索（向量寻点 + 图发散）

### 论文思想

HippoRAG (2024) 模拟人类海马体的记忆检索机制：第一阶段用向量检索召回"种子节点"（类似记忆线索），第二阶段在图上从种子节点出发用 Personalized PageRank (PPR) 算法激活关联子图，实现从局部到全局的知识发散。

### 项目落地

在 `ChatUseCase.execute()` 中实现了两阶段检索链路，用 BFS 替代 PPR 作为轻量化方案：

**阶段一：向量寻点** — `ChatUseCase.py` 第87-92行：

```python
# ① 向量寻点：从 entity collection 找种子实体
entity_results = self._vector_store.search_entities(query=question, top_k=5)
seed_names = [m.get("name", "") for m in entity_results if m.get("name")]
```

用户的自然语言问题直接作为查询文本，在 `graph_entities` collection 中做语义检索，返回语义最相近的 5 个实体名作为"种子"。

**阶段二：图发散** — `ChatUseCase.py` 第94-99行 → `NetworkXGraphRepository.expand_subgraph()`：

```python
# ② 图谱发散：从种子实体扩展子图
graph_paths = self._graph_repo.expand_subgraph(seed_names, hops=2)
```

从种子实体出发，在 NetworkX 内存图中做 2 跳 BFS 扩展：同时遍历出边（successors）和入边（predecessors），收集路径上的所有 `{from, relation, to}` 三元组。

**降级策略**：如果实体检索或图扩展任一环节失败（Collection 为空、图文件不存在等），自动降级为纯向量检索（原有 `rag_docs` search），保证服务可用性。

> **与原论文的差异**：HippoRAG 使用 PPR 算法根据图结构计算节点重要度，本项目用 BFS 替代以降低实现复杂度。后续可通过 `networkx.pagerank_scipy()` 升级为 PPR。

---

## 五、Query-Driven GraphRAG — 异步增量建图

### 论文思想

Query-Driven GraphRAG (2025) 的核心贡献是：**不预先构建全局知识图谱**，而是在查询时对召回的文档片段进行实时的小规模三元组抽取，仅构建与当前查询相关的局部子图。这样可以避免离线全局图构建的巨大算力开销。

### 项目落地

项目采用了该思想的**变体实现**——在文件导入时异步建图，而非查询时实时建图，兼顾了响应速度和资源消耗：

**异步建图** — `ImportFileUseCase.embed_file()`（第48行起）：

```
文件上传 → [同步] 保存磁盘 + DB
         → [异步线程] 文档分割 → 向量嵌入 → 三元组抽取 → 建图
```

关键设计：
1. **向量嵌入优先**（第56-60行）：先完成 `add_documents()` 并标记 `EMBEDDED`，保证基础检索能力立即可用
2. **建图后置串行**（第65-69行）：嵌入成功后才执行 `_build_graph()`，逐 chunk 调用 LLM 抽取三元组
3. **降级策略**（第67行）：`_build_graph()` 外层 try-except，建图失败不回滚已完成的向量嵌入，文件状态仍为 EMBEDDED

**Schema 定向抽取** — `GraphExtractionSkill`（`Backend/Application/Skills/GraphExtractionSkill.py`）：

```python
VALID_ENTITY_TYPES = {"COMPONENT", "SYMPTOM", "ERROR_CODE", "SOLUTION"}
VALID_RELATION_TYPES = {"CAUSES", "BELONGS_TO", "RESOLVES", "DIAGNOSES"}
```

通过 Prompt 硬性约束 4+4 种类型，杜绝开放式信息抽取的算力浪费。抽取结果经过严格的字段完整性校验和类型白名单过滤（第62-76行），确保入图数据质量。

> **与原论文的差异**：Query-Driven GraphRAG 在查询时实时建图（延迟大但无冗余），本项目在文件导入时离线建图（一次性成本、查询零延迟）。两者的共同点是"局部建图"——只对实际被处理的文档构建子图，而非尝试构建全局图谱。

---

## 六、端到端数据流

```
                      ┌─── LightRAG 思想 ───┐
文件上传               │                     │
  │                    │  rag_docs (chunks)   │
  ▼                    │  graph_entities      │
DocumentProcessorPro   │  graph_relations     │
  │                    └─────────────────────┘
  ├─→ ChromaDB  ───────────┤
  │                        │
  └─→ LLM 三元组抽取 ──→ NetworkX 图  ─── PathRAG 剪枝
       (Query-Driven                       MAX_EDGES=20
        Schema 定向)

用户查询
  │
  ├─① search_entities()  ─── HippoRAG 向量寻点
  │      ↓ seeds
  ├─② expand_subgraph()  ─── HippoRAG 图发散 (BFS 2跳)
  │      ↓ paths
  ├─③ search()           ─── 原文片段召回
  │      ↓ chunks
  └─④ _build_enhanced_context() → LLM 生成回答
```

---

## 七、关键文件索引

| 文件 | 对应论文思想 |
|------|-------------|
| `Backend/Infrastructure/vectorstore/ChromaVectorStoreRepository.py` | LightRAG 三层 Collection |
| `Backend/Infrastructure/graphstore/NetworkXGraphRepository.py` | PathRAG 剪枝 + HippoRAG 图发散 |
| `Backend/Application/UseCases/ChatUseCase.py` | HippoRAG 两阶段检索 |
| `Backend/Application/Skills/GraphExtractionSkill.py` | Query-Driven Schema 定向抽取 |
| `Backend/Application/UseCases/ImportFileUseCase.py` | Query-Driven 异步增量建图 |
| `Backend/Domain/Common/Enums/GraphEnums.py` | Schema 约束的实体/关系类型定义 |
