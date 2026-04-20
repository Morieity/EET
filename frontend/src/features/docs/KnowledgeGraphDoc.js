import React from 'react';
import DocLayout, {
  DocSection, DocSubSection, DocParagraph, DocTable, DocCode,
  DocList, DocCallout, DocFlowChart
} from './DocLayout';

const SECTIONS = [
  { id: 'design-goals', title: '一、设计目标与背景', level: 2 },
  { id: 'why-kg', title: '1.1 为什么引入知识图谱', level: 3 },
  { id: 'lightweight', title: '1.2 轻量化设计目标', level: 3 },
  { id: 'papers', title: '1.3 参考论文', level: 3 },
  { id: 'comparison', title: '1.4 与全量 GraphRAG 的对比', level: 3 },
  { id: 'architecture', title: '二、系统架构', level: 2 },
  { id: 'data-model', title: '三、数据模型', level: 2 },
  { id: 'triple', title: '3.1 三元组（Triple）', level: 3 },
  { id: 'entity-types', title: '3.2 实体类型', level: 3 },
  { id: 'relation-types', title: '3.3 关系类型', level: 3 },
  { id: 'graph-structure', title: '3.4 知识图谱整体结构', level: 3 },
  { id: 'extraction', title: '四、三元组提取流程', level: 2 },
  { id: 'preprocessing', title: '4.1 文本块预处理', level: 3 },
  { id: 'llm-schema', title: '4.2 LLM 调用与 Schema 约束', level: 3 },
  { id: 'concurrent', title: '4.3 并发提取与去重', level: 3 },
  { id: 'storage', title: '五、图存储与持久化', level: 2 },
  { id: 'networkx', title: '5.1 NetworkX 内存图', level: 3 },
  { id: 'vector-storage', title: '5.2 向量存储中的图数据', level: 3 },
  { id: 'query', title: '六、图查询与检索', level: 2 },
  { id: 'two-stage', title: '6.1 两阶段检索策略', level: 3 },
  { id: 'bfs', title: '6.2 BFS 子图展开', level: 3 },
  { id: 'full-query', title: '6.3 完整查询流程', level: 3 },
  { id: 'lifecycle', title: '七、图的生命周期管理', level: 2 },
  { id: 'build', title: '7.1 图的构建', level: 3 },
  { id: 'cleanup', title: '7.2 图的清理', level: 3 },
  { id: 'integration', title: '八、与上下文管理模块的集成', level: 2 },
  { id: 'params', title: '九、关键参数速查', level: 2 },
];

export default function KnowledgeGraphDoc() {
  return (
    <DocLayout
      title="知识图谱模块介绍文档"
      subtitle="工业故障 RAG 系统中的轻量化知识图谱构建与检索"
      sections={SECTIONS}
    >
      {/* 一、设计目标与背景 */}
      <DocSection id="design-goals" title="一、设计目标与背景">
        <DocSubSection id="why-kg" title="1.1 为什么引入知识图谱">
          <DocParagraph>
            传统 RAG 系统依赖向量相似度检索，能够快速找到语义相关的文本片段，但在以下场景中存在明显局限：
          </DocParagraph>
          <DocList items={[
            <><strong>多跳推理</strong>：用户问题涉及跨文档的因果链（如 A 组件故障引发 B 现象、根因为 C），向量检索无法利用文档间的显式关联。</>,
            <><strong>关系敏感问题</strong>：用户询问"哪些组件会引发该故障"时，向量相似度无法区分"属于"与"引发"等不同关系语义。</>,
            <><strong>知识复用</strong>：相同的实体关系散布在多个文档中，向量检索每次只返回孤立片段，图结构则可将分散知识聚合为连通的推理链。</>,
          ]} />
          <DocCallout>
            本系统在向量检索的基础上叠加了一层<strong>知识图谱</strong>，以三元组形式显式编码实体与关系，并通过图拓扑结构支持多跳关联检索。两种机制互补：向量检索覆盖语义相似性，知识图谱覆盖结构关系推理。
          </DocCallout>
        </DocSubSection>

        <DocSubSection id="lightweight" title="1.2 轻量化设计目标">
          <DocParagraph>
            工业场景中的部署资源往往受限，全量离线 GraphRAG（如 Microsoft GraphRAG）需要为整个语料库预构建社区摘要，成本极高。本系统的核心目标是在<strong>资源受限环境</strong>下运行可用的知识图谱，为此确立了四条设计原则：
          </DocParagraph>
          <DocTable
            headers={['设计原则', '工程含义']}
            rows={[
              ['拒绝重型外部图数据库', '不引入 Neo4j 等外部图数据库，完全使用 NetworkX 内存图 + JSON 文件持久化，启动时毫秒级加载，零运维依赖。'],
              ['Schema 定向抽取', '硬性限定实体类型（8 种）与关系类型（8 种），杜绝开放式信息抽取的算力浪费，同时保证三元组质量与类型一致性。'],
              ['向量与图算法融合', 'ChromaDB 负责语义模糊寻点，NetworkX 负责拓扑精确扩展，两者分工明确、各司其职，查询延迟可控。'],
              ['异步建图、不阻塞查询', '图的构建在文件导入时异步执行，以降级策略处理——图构建失败不影响向量检索可用性，在线查询路径不依赖建图完成。'],
            ]}
          />
        </DocSubSection>

        <DocSubSection id="papers" title="1.3 参考论文">
          <DocTable
            headers={['论文', '来源', '核心贡献', '在本系统中的体现']}
            rows={[
              ['LightRAG', 'Guo et al., 2024', '双层结构（低层实体 + 高层关系/主题），联合向量检索', '三个独立 ChromaDB Collection 的分层存储设计'],
              ['HippoRAG', '2024', '模拟海马体记忆：向量寻点 → PPR 算法激活子图', '向量寻点 + BFS 图发散的两阶段检索结构'],
              ['PathRAG', 'arXiv:2502.14902, 2025', '对图谱关系路径剪枝，去冗余边，降低遍历消耗', 'MAX_EDGES_PER_NODE 限制 + PathPruningAlgorithm 置信度过滤'],
              ['Query-Driven GraphRAG', '2025', '查询时在线局部建图，规避离线全局图构建的高成本', '仅对被召回文档的 chunks 做小规模三元组抽取'],
              ['GraphRAG (Microsoft)', 'arXiv:2404.16130', '社区摘要 + 全局图构建，用于大规模离线场景', '路径多样性优先策略'],
            ]}
          />
        </DocSubSection>

        <DocSubSection id="comparison" title="1.4 与全量 GraphRAG 的对比">
          <DocTable
            headers={['对比维度', '本系统（轻量化）', '全量 GraphRAG']}
            rows={[
              ['图构建时机', '文件导入时异步增量构建', '语料库离线预处理（数小时~数天）'],
              ['图数据库', 'NetworkX 内存图 + JSON 文件', 'Neo4j / ArangoDB 等外部图数据库'],
              ['抽取粒度', 'Schema 定向（8 类实体 × 8 类关系）', '开放式实体关系抽取'],
              ['社区摘要', '不构建', '层级社区摘要（高成本 LLM 调用）'],
              ['查询方式', '向量寻点 + BFS 2 跳展开', '全局搜索 + 社区摘要融合'],
              ['硬件要求', 'CPU 可运行，无 GPU 强依赖', '通常需要 GPU 加速和大内存'],
              ['删除支持', '按文件名增量删除边与孤立节点', '通常需全量重建'],
            ]}
          />
        </DocSubSection>
      </DocSection>

      {/* 二、系统架构 */}
      <DocSection id="architecture" title="二、系统架构">
        <DocParagraph>
          知识图谱模块纵贯 Domain、Infrastructure、Application 三个架构层，整体数据流分为<strong>离线建图</strong>与<strong>在线查询</strong>两条路径：
        </DocParagraph>
        <DocFlowChart>{`原始文档
  │
  ▼  [异步，文件导入时触发]
Schema 定向抽取（LLM + 限定 Prompt）
  │
  ├──> ChromaDB: graph_entities   （实体名 + 向量 + 类型元数据）
  ├──> ChromaDB: graph_relations  （关系描述文本 + 向量）
  └──> db/knowledge_graph.json    （节点 + 边，供 NetworkX 加载）

用户提问
  │
  ▼  [在线，毫秒级]
① 向量寻点    graph_entities  →  Top-K 种子实体
② 图谱发散    NetworkX BFS    →  2 跳关联路径
③ 原文检索    rag_docs        →  语义相关片段
④ 上下文编排  ContextManager  →  结构化 Prompt
⑤ LLM 推理                   →  最终回答`}</DocFlowChart>
        <DocCallout>
          建图与查询完全解耦：建图失败时查询自动降级为纯向量 RAG，不影响服务可用性。NetworkX 图在服务启动时一次性加载到内存，后续查询直接在内存中执行 BFS，延迟通常在 10 ms 以内。
        </DocCallout>
      </DocSection>

      {/* 三、数据模型 */}
      <DocSection id="data-model" title="三、数据模型">
        <DocSubSection id="triple" title="3.1 三元组（Triple）">
          <DocParagraph>
            知识图谱的最小语义单元是三元组，记作 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">τ = (h, r, t)</code>，其中 h 为头实体，r 为关系类型，t 为尾实体。代码中由 Triple 数据类表示：
          </DocParagraph>
          <DocCode title="Triple 数据类">{`@dataclass
class Triple:
    head:            str   # 头实体名称
    head_type:       str   # 头实体类型（EntityType 枚举值）
    relation:        str   # 关系类型（RelationType 枚举值）
    tail:            str   # 尾实体名称
    tail_type:       str   # 尾实体类型
    source_file:     str   # 来源文件名
    source_chunk_id: str   # 来源文本块 ID`}</DocCode>
        </DocSubSection>

        <DocSubSection id="entity-types" title="3.2 实体类型（EntityType）">
          <DocParagraph>
            Schema 定向抽取的核心约束之一是<strong>封闭的实体类型集合</strong>。面向工业故障诊断场景，定义了 8 种实体类型：
          </DocParagraph>
          <DocTable
            headers={['枚举值', '中文含义', '说明']}
            rows={[
              ['COMPONENT', '组件', '具体的硬件或软件组件，如传感器、驱动板'],
              ['SYMPTOM', '故障现象', '可观测到的异常表现，如电流突变、过载报警'],
              ['ERROR_CODE', '错误码', '系统输出的错误编号，如 E-04'],
              ['SOLUTION', '解决方案', '针对故障的处理措施，如更换驱动板'],
              ['DEVICE', '设备', '包含组件的上层设备单元'],
              ['FAULT_MODE', '失效模式', '故障的发生模式与类别'],
              ['WORK_ORDER', '工单', '记录维修过程的工单实体'],
              ['CAUSE', '根因', '故障的根本原因'],
            ]}
          />
        </DocSubSection>

        <DocSubSection id="relation-types" title="3.3 关系类型（RelationType）">
          <DocParagraph>
            封闭的 8 种关系类型，覆盖故障链路的因果、归属、诊断与记录四类语义：
          </DocParagraph>
          <DocTable
            headers={['枚举值', '中文含义', '语义描述']}
            rows={[
              ['CAUSES', '引发', '组件故障或根因引发故障现象'],
              ['BELONGS_TO', '属于', '组件属于某设备'],
              ['RESOLVES', '解决', '解决方案解决某故障现象'],
              ['DIAGNOSES', '排查', '错误码用于排查某组件或故障'],
              ['HAS_FAULT', '设备存在故障', '设备存在某种失效模式'],
              ['ROOT_CAUSE_OF', '根因对应故障', '某根因导致某失效模式'],
              ['TREATED_BY', '由措施处理', '故障由某解决方案处理'],
              ['RECORDED_IN', '记录于工单', '故障或操作记录于某工单'],
            ]}
          />
        </DocSubSection>

        <DocSubSection id="graph-structure" title="3.4 知识图谱整体结构">
          <DocParagraph>
            所有三元组共同构成一个有向知识图谱 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">G = (V, E, R)</code>，其中 V 为实体节点集合，E 为有向边集合，R 为关系类型集合。图以 NetworkX 有向图（DiGraph）在内存中维护，并序列化为 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">db/knowledge_graph.json</code> 持久化。
          </DocParagraph>
        </DocSubSection>
      </DocSection>

      {/* 四、三元组提取流程 */}
      <DocSection id="extraction" title="四、三元组提取流程">
        <DocSubSection id="preprocessing" title="4.1 文本块预处理">
          <DocParagraph>
            文档切分后的原始 chunks 在送入 LLM 前，先将相邻两个 chunk 合并为一组（配置项 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">CHUNK_GROUP_SIZE = 2</code>）。合并后的块数约为原始数量的一半，保留了段落间的语义延续性，有助于提取跨段落的实体关系。
          </DocParagraph>
        </DocSubSection>

        <DocSubSection id="llm-schema" title="4.2 LLM 调用与 Schema 约束">
          <DocParagraph>
            三元组提取由 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">GraphExtractionSkill</code> 调用大语言模型完成。提示词严格约束输出格式——封闭的 Schema 既降低了 LLM 的自由发挥空间（减少幻觉），又保证了所有三元组类型的一致性：
          </DocParagraph>
          <DocList items={[
            '系统提示词："你是一个工业故障知识图谱抽取助手，只返回 JSON，不附加任何解释。"',
            '实体类型约束：必须为 EntityType 枚举中的值，不得自行扩展。',
            '关系类型约束：必须为 RelationType 枚举中的值，不得自行扩展。',
            '必填字段：每条三元组必须包含 head、head_type、relation、tail、tail_type 五个字段。',
            '无符合条件时：返回空数组 []，不得捏造三元组。',
          ]} />
        </DocSubSection>

        <DocSubSection id="concurrent" title="4.3 并发提取与去重">
          <DocParagraph>
            为提升吞吐量，<code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">TripleExtractor.batch_extract</code> 使用线程池并发调用 LLM，最大并发数为 30，相邻请求最小间隔为 1 秒以避免触发 API 速率限制。并发完成后对全量三元组做精确去重，去重键为 (head, relation, tail) 三元组，保证同一知识关系在图中只有一条边（幂等性）。
          </DocParagraph>
        </DocSubSection>
      </DocSection>

      {/* 五、图存储与持久化 */}
      <DocSection id="storage" title="五、图存储与持久化">
        <DocSubSection id="networkx" title="5.1 NetworkX 内存图">
          <DocParagraph>
            <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">NetworkXGraphRepository</code> 以 NetworkX DiGraph 在进程内存中维护图结构，通过 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">threading.Lock</code> 保证并发写入安全。10 万节点规模加载时间不超过 2 秒。
          </DocParagraph>
          <DocCode title="节点与边格式">{`# 节点格式
{ "id": "<实体名>", "attrs": { "entity_type": "<EntityType>" } }

# 边格式
{ "src": "<头实体>", "dst": "<尾实体>",
  "relation": "<RelationType>", "source_file": "<文件名>" }`}</DocCode>
          <DocParagraph>
            为控制图规模（PathRAG 的剪枝思想），每个节点的出边数量硬性上限为 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">MAX_EDGES_PER_NODE = 20</code>，超出时由 prune() 裁剪。
          </DocParagraph>
        </DocSubSection>

        <DocSubSection id="vector-storage" title="5.2 向量存储中的图数据">
          <DocParagraph>
            实体与关系被分别嵌入到 ChromaDB 的两个独立集合，支持基于自然语言查询的模糊寻点：
          </DocParagraph>
          <DocTable
            headers={['集合名', '用途', 'ID 格式', '相似度阈值']}
            rows={[
              ['graph_entities', '实体语义搜索', 'ent_ + MD5(name)[0:12]', '0.85'],
              ['graph_relations', '关系语义搜索', 'rel_ + MD5(h|r|t)[0:12]', '0.50'],
            ]}
          />
          <DocCallout>
            实体集合的阈值（0.85）高于关系集合（0.50）：实体名空间密集，需要更严格的过滤；关系描述文本较长，语义距离更分散，阈值可适当放宽。
          </DocCallout>
        </DocSubSection>
      </DocSection>

      {/* 六、图查询与检索 */}
      <DocSection id="query" title="六、图查询与检索">
        <DocSubSection id="two-stage" title="6.1 两阶段检索策略">
          <DocParagraph>
            在线查询采用<strong>向量寻点 + 图拓扑扩展</strong>的两阶段策略，参照 HippoRAG 的海马体模型：
          </DocParagraph>
          <DocList ordered items={[
            <><strong>阶段一 — 向量寻点</strong>：以用户问题为查询，在 graph_entities 集合中检索相似度最高的实体，得到种子实体集合 S（top_k = 20，阈值 0.85）。</>,
            <><strong>阶段二 — BFS 扩展</strong>：以 S 中每个节点为起点，在 NetworkX 图上执行广度优先搜索，展开 h = 2 跳范围内的所有可达三元组。</>,
          ]} />
        </DocSubSection>

        <DocSubSection id="bfs" title="6.2 BFS 子图展开">
          <DocParagraph>
            2 跳展开在覆盖直接关联与间接关联的同时，将路径数量控制在可管理范围内（受 MAX_EDGES_PER_NODE 与 max_graph_paths 双重约束）。展开结果以路径列表形式返回：
          </DocParagraph>
          <DocCode title="GraphPath 条目示例">{`{
    "from":        "传感器A",
    "relation":    "CAUSES",
    "to":          "温度过高",
    "score":       0.92,
    "confidence":  0.85,
    "source_file": "设备手册.pdf"
}`}</DocCode>
        </DocSubSection>

        <DocSubSection id="full-query" title="6.3 完整查询流程">
          <DocCode title="查询流程">{`① 向量寻点
   vector_store.search_entities(query, top_k=20, threshold=0.85)
   → seed_names: list[str]

② BFS 子图展开
   graph_repo.expand_subgraph(seed_names, hops=2)
   → graph_paths: list[GraphPath]

③ 原文片段检索
   vector_store.search(query)
   → sources: list[dict]

④ 上下文管理编排
   ContextManager（PathPruning + MMR + Reorder）
   → 结构化 Prompt 中的三段式上下文`}</DocCode>
        </DocSubSection>
      </DocSection>

      {/* 七、图的生命周期管理 */}
      <DocSection id="lifecycle" title="七、图的生命周期管理">
        <DocSubSection id="build" title="7.1 图的构建（文件导入）">
          <DocParagraph>
            <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">ImportFileUseCase.embed_file</code> 在完成向量化后异步触发图构建。以降级策略执行——图构建失败不影响向量检索可用性：
          </DocParagraph>
          <DocFlowChart>{`文件上传
  ↓
文档加载 → 分割 chunks → 向量化 → 存入 rag_docs（同步）
  ↓（异步，失败降级）
batch_extract(chunks)
  ├─ 合并相邻 chunks（每 2 个一组）
  └─ ThreadPoolExecutor（30 线程）并发调用 LLM
  ↓
去重 → add_entity()   → graph_entities（ChromaDB）
     → add_relation() → graph_relations（ChromaDB）
     → add_triples()  → NetworkX DiGraph
     → save()         → db/knowledge_graph.json`}</DocFlowChart>
        </DocSubSection>

        <DocSubSection id="cleanup" title="7.2 图的清理（文件删除）">
          <DocParagraph>
            删除文件时，<code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">DeleteFileUseCase</code> 按文件名同步清理图数据，三个存储层保持一致：
          </DocParagraph>
          <DocCode>{`vector_store.delete_entities_by_file()   →  删除 graph_entities 中该文件的实体
vector_store.delete_relations_by_file()  →  删除 graph_relations 中该文件的关系
graph_repo.remove_by_file()              →  删除 NetworkX 图中所有匹配的边，并清除孤立节点`}</DocCode>
          <DocCallout>
            按文件增量删除的能力，是轻量化方案中刻意保留的运维友好性设计——全量 GraphRAG 通常需要整图重建才能完成删除操作。
          </DocCallout>
        </DocSubSection>
      </DocSection>

      {/* 八、与上下文管理模块的集成 */}
      <DocSection id="integration" title="八、与上下文管理模块的集成">
        <DocParagraph>
          BFS 展开得到的图路径经 PathPruningAlgorithm 过滤后，与向量检索结果一同组装为三段式 Prompt 上下文：
        </DocParagraph>
        <DocCode title="结构化 Prompt 上下文示例">{`【关联实体】
传感器A, 温度过高, 冷却系统

【知识图谱路径】
  - 传感器A --[CAUSES]--> 温度过高
  - 温度过高 --[ROOT_CAUSE_OF]--> 冷却系统失效
  - 冷却系统失效 --[TREATED_BY]--> 更换冷却液

【相关原文片段】
[设备手册.pdf]
传感器A负责监测冷却系统出口温度……`}</DocCode>
        <DocCallout>
          结构化图路径与原文片段并列呈现：LLM 可利用图中的显式因果链做多跳推理，同时从原文中获取细节依据，两者互补，提升故障诊断问答的准确性与可解释性。
        </DocCallout>
      </DocSection>

      {/* 九、关键参数速查 */}
      <DocSection id="params" title="九、关键参数速查">
        <DocTable
          headers={['参数', '默认值', '所在模块', '说明']}
          rows={[
            ['CHUNK_GROUP_SIZE', '2', 'TripleExtractor', '批量提取时相邻 chunk 的合并数量'],
            ['ASYNC_TRIPLE_EXTRACT_MAX_WORKERS', '30', 'TripleExtractor', '并发提取线程池大小'],
            ['request_interval', '1.0 s', 'TripleExtractor', 'LLM 请求的最小时间间隔'],
            ['MAX_EDGES_PER_NODE', '20', 'NetworkXGraphRepository', '每个节点的出边上限（PathRAG 剪枝）'],
            ['expand_subgraph hops', '2', 'NetworkXGraphRepository', 'BFS 展开的最大跳数'],
            ['entity score threshold', '0.85', 'ChromaVectorStoreRepository', '实体向量搜索相似度阈值'],
            ['relation score threshold', '0.50', 'ChromaVectorStoreRepository', '关系向量搜索相似度阈值'],
            ['entity search top_k', '20', 'ChromaVectorStoreRepository', '实体向量搜索返回数量上限'],
          ]}
        />
        <DocParagraph>
          <span className="text-sm text-gray-500">文档版本：v2.0 | 对应代码路径：Backend/Domain/ · Backend/Infrastructure/ · Backend/Application/UseCases/</span>
        </DocParagraph>
      </DocSection>
    </DocLayout>
  );
}
