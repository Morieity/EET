import React from 'react';
import DocLayout, {
  DocSection, DocSubSection, DocParagraph, DocTable, DocCode,
  DocList, DocCallout, DocFlowChart
} from './DocLayout';

const SECTIONS = [
  { id: 'overview', title: '一、概述', level: 2 },
  { id: 'algorithms', title: '二、算法模块与论文对照', level: 2 },
  { id: 'mmr', title: '2.1 MMR 去重', level: 3 },
  { id: 'reorder', title: '2.2 检索重排', level: 3 },
  { id: 'path-pruning', title: '2.3 路径剪枝', level: 3 },
  { id: 'token-budget', title: '2.4 Token 预算', level: 3 },
  { id: 'history-tiering', title: '2.5 历史分层', level: 3 },
  { id: 'query-compression', title: '2.6 查询感知压缩', level: 3 },
  { id: 'query-placement', title: '2.7 查询位置', level: 3 },
  { id: 'pipeline', title: '三、整体编排流程', level: 2 },
  { id: 'prompt-gen', title: '四、用户 Prompt 的生成过程', level: 2 },
  { id: 'history-gen', title: '4.1 历史消息的生成', level: 3 },
  { id: 'user-content', title: '4.2 User Content 的生成', level: 3 },
  { id: 'output-example', title: '4.3 一次典型调用的输出', level: 3 },
  { id: 'tradeoffs', title: '五、设计取舍', level: 2 },
  { id: 'config', title: '六、配置默认值速查', level: 2 },
];

export default function ContextManagementDoc() {
  return (
    <DocLayout
      title="上下文管理算法介绍文档"
      subtitle="RAG 问答流水线中的检索后编排模块"
      sections={SECTIONS}
    >
      {/* 一、概述 */}
      <DocSection id="overview" title="一、概述">
        <DocParagraph>
          本项目的上下文管理模块位于 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">Backend/Application/ContextManagement</code>，是 RAG 问答流水线中处于"检索之后、生成之前"的关键环节。它的职责是把来自不同数据源的原材料（知识图谱路径、向量检索片段、历史对话、当前用户问题）编排成一条<strong>结构合理、冗余可控、长度可算、注意力友好</strong>的最终提示词。
        </DocParagraph>
        <DocParagraph>
          整体实现采用<strong>算法模块 + 规则式编排器</strong>的组合架构：
        </DocParagraph>
        <DocList items={[
          <><strong>算法模块</strong>（Algorithms/）：每个算法封装一篇论文的核心思想，只负责单一职责。</>,
          <><strong>编排器</strong>（ContextManager.py）：以确定性顺序调用各算法，并依据 token 预算触发分级动作。</>,
          <><strong>注册表</strong>（AlgorithmRegistry.py）：统一装配算法实例，便于替换与测试。</>,
        ]} />
        <DocCallout>
          配置参数集中在 <code className="px-1 py-0.5 bg-[#4C9755]/10 rounded text-sm font-mono">ContextManagerConfig</code> 中，可在运行时覆盖。
        </DocCallout>
      </DocSection>

      {/* 二、算法模块与论文对照 */}
      <DocSection id="algorithms" title="二、算法模块与论文对照">
        <DocTable
          headers={['算法模块', '论文来源', '在本项目中的作用']}
          rows={[
            ['MMR 去重', 'Long-Context LLMs Meet RAG (ICLR 2025)', '对检索片段做"相关性 vs 新颖性"的平衡选择'],
            ['检索重排', 'Long-Context LLMs Meet RAG；Retrieval Head', '把高相关证据放到提示词首尾，利用注意力边界效应'],
            ['路径剪枝', 'GraphRAG；PathRAG', '过滤低置信度三元组并保持关系类型多样性'],
            ['Token 预算', 'Long Context vs. RAG；LongLLMLingua；Retrieval Head', '为提示词各分区分配预算并触发分级压缩'],
            ['历史分层', 'MemAgent；Long Context vs. RAG', '把历史对话切成冷/温/热三层，只保热层原文'],
            ['查询感知压缩', 'LongLLMLingua；LLMLingua-2', '保留查询相关句子的抽取式压缩'],
            ['查询位置', 'Retrieval Head', '强制当前查询位于消息列表末尾'],
          ]}
        />

        <DocSubSection id="mmr" title="2.1 MMR 去重（MMRDeduplicationAlgorithm）">
          <DocParagraph>
            Maximal Marginal Relevance 的经典目标是：在已选集合 S 的基础上挑选下一条片段时，最大化以下目标函数：
          </DocParagraph>
          <DocCode title="MMR 公式">{`MMR(d) = λ · rel(d, q) - (1 - λ) · max_{d' ∈ S} sim(d, d')

其中 rel 取检索分数，sim 采用内容词的 Jaccard 相似度：
J(A, B) = |A ∩ B| / |A ∪ B|`}</DocCode>
          <DocParagraph>
            相关性权重 λ 对应配置项 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">mmr_relevance_weight</code>（默认 0.7），输出长度由 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">mmr_top_k</code>（默认 15）限制。在检索片段常存在近重复的场景下，MMR 是本流水线第一道"信息密度闸门"。
          </DocParagraph>
        </DocSubSection>

        <DocSubSection id="reorder" title="2.2 检索重排（RetrievalReorderingAlgorithm）">
          <DocParagraph>
            Retrieval Head 指出长上下文模型的事实性能力高度依赖少量"检索头"，而这些注意力头对<strong>序列头尾的信息更敏感</strong>。因此算法把 MMR 输出先按分数降序排序，再做"首位—末位—首位—末位..."的交替放置：
          </DocParagraph>
          <DocCode>{`[ d1, d3, d5, ..., d6, d4, d2 ]

最高相关的证据放在首位，次高放在末位，依此类推。`}</DocCode>
          <DocCallout type="tip">
            无论模型偏爱前景还是后景，都能优先看到关键证据。
          </DocCallout>
        </DocSubSection>

        <DocSubSection id="path-pruning" title="2.3 路径剪枝（PathPruningAlgorithm）">
          <DocParagraph>
            针对知识图谱三元组 (s, r, t)，算法依次执行：
          </DocParagraph>
          <DocList ordered items={[
            '过滤字段不全或置信度低于阈值的三元组，阈值对应 min_path_confidence。',
            '按 (s, r, t) 做精确去重。',
            '若 relation_diversity=True，先对每一类关系类型各保留一条最佳路径，再按全局置信度补齐到 max_graph_paths。',
          ]} />
          <DocCallout>
            这种<strong>多样性优先</strong>的策略来源于 GraphRAG 与 PathRAG 的实证结论：在有限预算下，关系类型的覆盖度比单一类型的深度更能提升下游问答质量。
          </DocCallout>
        </DocSubSection>

        <DocSubSection id="token-budget" title="2.4 Token 预算（TokenBudgetingAlgorithm）">
          <DocParagraph>
            算法为六个分区分配固定比例：
          </DocParagraph>
          <DocCode title="Token 预算分配">{`ratios = {
  system:  0.05,   // 系统提示
  kg:      0.20,   // 知识图谱
  vector:  0.35,   // 向量检索
  history: 0.25,   // 历史对话
  query:   0.05,   // 用户查询
  reserve: 0.10    // 预留空间
}`}</DocCode>
          <DocParagraph>
            残差 token 并入 vector 分区以提升检索侧灵活度。运行时计算利用率 ρ = total_prompt_tokens / max_context_tokens，依 ρ 触发<strong>分级压缩动作</strong>：
          </DocParagraph>
          <DocTable
            headers={['利用率阈值', '触发动作']}
            rows={[
              ['ρ > 0.6', '触发 compress_history_tier2（历史分层）'],
              ['ρ > 0.8', '追加 compress_history_tier3 与 compress_vector_docs_keep_50pct（查询感知压缩）'],
              ['ρ > 0.9', '再追加 kg_one_hop_only、remove_kg_community_summary、vector_top_k_hard_cap'],
            ]}
          />
          <DocCallout>
            system 与 query 分区被标记为<strong>不可压缩</strong>——这是 Retrieval Head 工作结论的直接工程化。
          </DocCallout>
        </DocSubSection>

        <DocSubSection id="history-tiering" title="2.5 历史分层（HistoryTieringAlgorithm）">
          <DocParagraph>
            参照 MemAgent，算法把按时间顺序排列的对话轮次切成三层：
          </DocParagraph>
          <DocTable
            headers={['层级', '说明', '处理方式']}
            rows={[
              ['Hot（热层）', '最近 hot_size 轮', '原样保留'],
              ['Warm（温层）', '紧邻热层前的 warm_size 轮', '摘要为要点（最多 5 个要点）'],
              ['Cold（冷层）', '其余早期轮次', '进一步粗粒度摘要'],
            ]}
          />
          <DocParagraph>
            温层摘要时按工业故障诊断关键词（"故障""现象""原因""解决"等）打分排序，优先保留领域相关度高的轮次；冷层则只抽取含关键词的问题作为"历史聚焦摘要"。输出以 [Hot Turns] / [Warm Memory Summary] / [Cold Memory Summary] 三段文本组织。
          </DocParagraph>
        </DocSubSection>

        <DocSubSection id="query-compression" title="2.6 查询感知压缩（QueryAwareCompressionAlgorithm）">
          <DocParagraph>
            参照 LongLLMLingua 与 LLMLingua-2 的查询感知思想，算法按分数保留前 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">keep_rate</code> 比例的文档（默认 0.5），然后对每篇文档做抽取式压缩：
          </DocParagraph>
          <DocList ordered items={[
            '用 jieba 中文分词（加载了工业故障领域词典）提取查询词集合 Q。',
            '按分隔符将文档切成句子。',
            <>{'计算与查询的重叠得分：score(cᵢ) = |terms(cᵢ) ∩ Q| / |Q| + 0.5 · |terms(cᵢ) ∩ Q ∩ D|，其中 D 是领域词典（故障、诊断、传感器等），领域词重叠获得额外加成。'}</>,
            '按得分降序累积句子，直到达到 compression_min_chars（默认 160）。',
          ]} />
        </DocSubSection>

        <DocSubSection id="query-placement" title="2.7 查询位置（QueryPlacementAlgorithm）">
          <DocParagraph>
            原则：当前用户问题必须出现在消息序列的最后一条。算法提供两个接口：<code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">append_query</code> 把问题与上下文合并为一条 user 消息并追加，<code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">ensure_query_last</code> 在必要时将末位 user 消息移到尾部。其理论依据仍是 Retrieval Head——尾部位置在长上下文下的事实召回率更稳定。
          </DocParagraph>
        </DocSubSection>
      </DocSection>

      {/* 三、整体编排流程 */}
      <DocSection id="pipeline" title="三、整体编排流程">
        <DocParagraph>
          编排器 <code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">DefaultContextManager.prepare_context</code> 以确定性顺序调用上述算法：
        </DocParagraph>
        <DocFlowChart>{`输入: question, rounds, seed_names, graph_paths, sources, cfg
  │
  ▼
① PathPruning        ──►  按置信度 + 去重 + 关系多样性裁剪 graph_paths
  │
  ▼
② MMRDeduplication   ──►  在检索片段上做 MMR 选择，输出 top_k 条
  │
  ▼
③ RetrievalReorder   ──►  首尾交替放置，形成边界感知顺序
  │
  ▼
④ 基线历史 + 上下文文本 + user_content  (QueryPlacement 拼装)
  │
  ▼
⑤ TokenBudgeting     ──►  计算 ρ，产出 budget_actions 列表
  │   ├── ρ > 0.6 ──► HistoryTiering   (重建冷/温/热历史消息)
  │   ├── ρ > 0.8 ──► QueryAwareCompression (压缩保留片段)
  │   └── ρ > 0.9 ──► vector hard cap / KG one-hop 限制
  ▼
⑥ 重新组装 context_text 与 user_content → ContextPreparationResult`}</DocFlowChart>
        <DocParagraph>
          关键设计特点：
        </DocParagraph>
        <DocList items={[
          <><strong>确定性</strong>：在相同输入与配置下，输出严格可复现，便于测试与 A/B 分析。</>,
          <><strong>单向流水线</strong>：除了第 ⑤ 步的条件分支外，各算法只读上游结果、不回溯。</>,
          <><strong>不可压缩的 system / query</strong>：整个流程中两者的文本不会被裁剪。</>,
          <><strong>可观测性</strong>：ContextPreparationResult.budget_actions 与 budget_plan 会随响应一起返回，可在日志与前端调试面板中直接查看。</>,
        ]} />
      </DocSection>

      {/* 四、用户 Prompt 的生成过程 */}
      <DocSection id="prompt-gen" title="四、用户 Prompt 的生成过程">
        <DocParagraph>
          最终送入 LLM 的提示词由三部分构成：<code className="px-1.5 py-0.5 bg-gray-100 rounded text-sm font-mono">Prompt = SystemInstructions + HistoryMessages + UserContent</code>
        </DocParagraph>

        <DocSubSection id="history-gen" title="4.1 历史消息的生成">
          <DocParagraph>
            默认情况下调用 _build_recent_history_messages，取末尾 max_history_rounds 轮（默认 10）原样转成 user / assistant 的消息对。当触发 compress_history_tier2 时，改由 _build_tiered_history_messages 生成，输出为单条 assistant 消息：
          </DocParagraph>
          <DocCode title="分层历史消息格式">{`[Conversation Memory]
[Cold Memory Summary]
- Historical focus: ...

[Warm Memory Summary]
- Q: ... | A: ...
- Q: ... | A: ...

[Hot Turns]
User: ...
Assistant: ...`}</DocCode>
        </DocSubSection>

        <DocSubSection id="user-content" title="4.2 User Content 的生成">
          <DocParagraph>
            User Content 由 _build_context_text 与 _compose_user_content 共同完成，遵循固定的三段式结构：
          </DocParagraph>
          <DocCode title="上下文文本结构">{`【关联实体】
实体A, 实体B, 实体C

【知识图谱路径】
  - 实体A --[关系r1]--> 实体B
  - 实体B --[关系r2]--> 实体C

【相关原文片段】
[file_name_1.pdf]
片段内容 ...

[file_name_2.pdf]
片段内容 ...`}</DocCode>
          <DocParagraph>
            交由 QueryPlacementAlgorithm 把问题与上下文合并，并保证查询居末。最终形态：
          </DocParagraph>
          <DocCode>{`<用户问题>

Context:
<上面的三段式上下文>`}</DocCode>
        </DocSubSection>

        <DocSubSection id="output-example" title="4.3 一次典型调用的输出">
          <DocCode title="ContextPreparationResult 示例">{`{
  "context": "【关联实体】...\\n\\n【知识图谱路径】...\\n\\n【相关原文片段】...",
  "user_content": "故障现象是什么？\\n\\nContext:\\n...",
  "history_messages": [{"role": "user", ...}, {"role": "assistant", ...}],
  "sources": [... 经 MMR + 重排 (+ 压缩) 后的片段 ...],
  "graph_paths": [... 经路径剪枝 (+ one-hop 限制) 后的三元组 ...],
  "seed_names": ["实体A", "实体B"],
  "budget_actions": ["compress_history_tier2", "compress_vector_docs_keep_50pct"],
  "prompt_token_estimate": 18432,
  "budget_plan": {"system": 1600, "kg": 6400, "vector": 11200, ...}
}`}</DocCode>
          <DocParagraph>
            该结果被 ChatUseCase 直接消费：history_messages 作为模型对话历史，user_content 作为最终一条 user 消息，budget_actions 与 budget_plan 供日志与前端展示。
          </DocParagraph>
        </DocSubSection>
      </DocSection>

      {/* 五、设计取舍 */}
      <DocSection id="tradeoffs" title="五、设计取舍">
        <DocList items={[
          <><strong>规则式 over 端到端学习</strong>：所有决策都来自可解释的阈值与比例，便于复盘与回滚。</>,
          <><strong>单一职责的算法模块</strong>：每个算法只对应一篇论文的核心贡献，避免耦合。</>,
          <><strong>分级触发 over 一刀切压缩</strong>：通过利用率阈值逐级加码，低负载时不牺牲信息保真度。</>,
          <><strong>领域词典的中文增强</strong>：jieba + 工业故障词典使压缩与摘要在中文场景下更稳健。</>,
          <><strong>注意力边界友好的布局</strong>：检索重排与查询末置共同实现 Retrieval Head 的工程化。</>,
        ]} />
      </DocSection>

      {/* 六、配置默认值速查 */}
      <DocSection id="config" title="六、配置默认值速查">
        <DocTable
          headers={['配置项', '默认值', '说明']}
          rows={[
            ['max_context_tokens', '32000', '模型上下文窗口总量'],
            ['max_history_rounds', '10', '未分层时保留的最近对话轮数'],
            ['mmr_top_k', '15', 'MMR 输出上限'],
            ['mmr_relevance_weight', '0.7', 'MMR 中相关性权重 λ'],
            ['min_path_confidence', '0.4', '路径剪枝的置信度阈值'],
            ['max_graph_paths', '20', '输出路径上限'],
            ['history_hot_size', '3', '热层轮数'],
            ['history_warm_size', '7', '温层轮数'],
            ['compression_keep_rate', '0.5', '查询感知压缩保留比例'],
            ['compression_min_chars', '160', '单文档压缩后最小字符数'],
          ]}
        />
        <DocParagraph>
          <span className="text-sm text-gray-500">文档版本：v1.0 | 对应代码路径：Backend/Application/ContextManagement/</span>
        </DocParagraph>
      </DocSection>
    </DocLayout>
  );
}
