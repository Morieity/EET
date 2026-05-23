# RAG 智能问答系统面试问答准备

本文档模拟面试官围绕当前项目可能提出的 20 个问题，并给出可用于面试回答的参考答案。回答时建议先讲业务目标，再讲架构设计，最后补充技术取舍和风险处理。

## 1. 请你整体介绍一下这个项目，它解决了什么问题？

**面试官想考察：** 你是否能从业务价值和技术方案两个层面概括项目。

**参考回答：**

这是一个面向工业故障分析场景的 RAG 智能问答系统。它支持用户上传 PDF、Word、TXT、Markdown 等资料，将文档切分、向量化并写入 ChromaDB；问答时先检索相关文档片段，再结合历史对话、知识图谱路径和故障树上下文组织提示词，调用 DeepSeek 兼容的大模型进行回答。

项目不仅做了普通文档问答，还扩展了工业领域能力，包括知识图谱三元组抽取、GraphRAG 检索、故障树生成与更新、工单导入和工单驱动分析。整体目标是让用户在复杂设备资料和维修经验中更快定位故障原因，并形成可复用的结构化知识。

## 2. 项目为什么采用 Clean Architecture？各层职责如何划分？

**面试官想考察：** 你是否理解架构分层，而不是只会堆功能。

**参考回答：**

项目采用 Clean Architecture 是为了降低业务逻辑和技术实现之间的耦合。核心业务不直接依赖 Flask、SQLite、ChromaDB 或 LangChain，而是依赖接口，这样后续替换向量库、模型服务或存储实现时，改动范围更可控。

当前后端主要分为四层：

- `Domain`：领域实体和枚举，例如文件、会话、故障树、工单、三元组。
- `Application`：用例、接口、聊天编排、上下文管理、技能模块，例如 `ChatUseCase`、`ImportFileUseCase`、`FaultTreeSkill`。
- `Infrastructure`：具体技术实现，例如 SQLite 仓储、Chroma 向量库、LangChain LLM 服务、文档解析器。
- `Web`：Flask 蓝图和依赖注入入口，负责 HTTP 接口和对象组装。

这样的分层让应用层可以通过 `ILLMService`、`IVectorStoreRepository`、`IConversationRepository` 等接口调用能力，而不直接绑定具体框架。

## 3. 这个项目的 RAG 流程是怎样的？

**面试官想考察：** 你是否能讲清楚从上传文档到回答问题的完整链路。

**参考回答：**

RAG 链路分为离线入库和在线问答两部分。

离线入库时，用户上传文件后，系统先把文件保存到 `uploads`，在 SQLite 中记录文件元数据，然后后台线程加载文档、按结构切分成 chunk，为每个 chunk 加上 `file_name` 和 `chunk_index` 等元数据，再通过 FastEmbed 生成向量并写入 ChromaDB 的 `rag_docs` collection。随后系统会调用 LLM 抽取三元组，把实体和关系写入知识图谱以及 Chroma 的实体/关系 collection。

在线问答时，系统先用用户问题检索实体和关系，尝试扩展知识图谱子图，再基于图谱来源定位原文 chunk；如果图谱检索结果不足，会回退到普通向量检索。最后把检索片段、图谱路径、历史对话和系统提示词组合成 prompt，流式调用 LLM 返回答案。

## 4. 项目中 LangChain 主要用到了哪些能力？

**面试官想考察：** 你是否知道项目中到底用了 LangChain 的哪些组件。

**参考回答：**

项目没有使用 `LLMChain`、`RetrievalQA`、`ConversationalRetrievalChain` 或 LCEL Runnable 链，而是把 LangChain 当作底层适配层使用。

主要用到以下能力：

- `ChatOpenAI`：封装 DeepSeek 兼容接口，实现聊天模型调用。
- `SystemMessage`、`HumanMessage`、`AIMessage`、`ToolMessage`：把项目内部 message dict 转成 LangChain 消息对象。
- `stream()`：实现 SSE 场景下的流式 token 输出。
- `bind_tools()` 和 `invoke()`：实现故障树生成/更新的 tool calling。
- `Chroma`：作为 LangChain 的 Chroma 向量库封装。
- `FastEmbedEmbeddings`：使用本地缓存的 BGE embedding 模型。
- `PDFPlumberLoader`、`Docx2txtLoader`、`TextLoader`：加载不同类型文档。
- `RecursiveCharacterTextSplitter`：对文档进行 chunk 切分。
- `Document`：统一表达文档内容和 metadata。

RAG 编排、提示词组织、JSON 解析、GraphRAG 逻辑和业务用例都是项目自己实现的。

## 5. 为什么没有直接使用 LangChain 的 RetrievalQA 或 ConversationalRetrievalChain？

**面试官想考察：** 你是否能解释技术取舍。

**参考回答：**

因为项目的问答流程并不是单纯的“向量检索 + LLM 回答”。它还包含图谱扩展、故障树上下文注入、多轮对话历史压缩、来源过滤、工单上下文、故障树 tool calling，以及 SSE 事件流等业务逻辑。

如果直接使用 `RetrievalQA` 或 `ConversationalRetrievalChain`，短期开发会简单一些，但对图谱检索、事件流、故障树生成、多源上下文预算等定制能力不够灵活。因此项目选择只复用 LangChain 的模型、loader、splitter、vectorstore 等底层组件，上层编排自己实现。

## 6. 文档是如何加载和切分的？为什么要做结构化切分？

**面试官想考察：** 你是否理解 chunk 策略对 RAG 效果的影响。

**参考回答：**

项目中当前实际使用的是 `DocumentProcessorPro`。它先根据文件类型选择 loader：PDF 使用 `PDFPlumberLoader`，Word 使用 `Docx2txtLoader`，TXT 和 Markdown 使用 `TextLoader`。

加载后不是直接粗暴按固定长度切分，而是先合并页面文本，做 Unicode 正规化，再根据中文标题、章节、条款、Markdown 标题、数字编号等规则识别结构标题。系统先按标题结构形成较大的语义块，如果块超过 `chunk_size`，再用 `RecursiveCharacterTextSplitter` 做细切分。

这样做的好处是 chunk 更容易保留章节语义和上下文路径，减少把一个完整故障描述或处理步骤切断的情况。切分后还会做清洗、过滤短噪音块和精确去重。

## 7. 向量库为什么选择 ChromaDB？当前如何组织 collection？

**面试官想考察：** 你是否理解向量存储设计。

**参考回答：**

ChromaDB 适合本地开发和中小规模知识库场景，部署简单，支持持久化，和 LangChain 集成方便。当前项目把数据持久化在 `db/` 目录。

主要 collection 包括：

- `rag_docs`：通用文档 chunk，用于普通 RAG 检索。
- `graph_entities`：知识图谱实体向量，用于根据问题召回相关实体。
- `graph_relations`：知识图谱关系向量，用于召回相关三元组关系。
- `work_orders`：工单专属 collection，避免工单数据和普通文档混在一起影响检索。

这种设计让不同类型的数据可以使用不同检索策略和过滤阈值，也便于后续独立优化。

## 8. `ChromaVectorStoreRepository` 里有哪些关键方法？

**面试官想考察：** 你是否熟悉当前编辑文件的核心逻辑。

**参考回答：**

`ChromaVectorStoreRepository` 是向量存储的基础设施实现，核心职责是封装 Chroma 和 embedding。

关键方法包括：

- `add_documents()`：给文档 chunk 添加 `file_name` metadata，然后写入当前 collection。
- `delete_by_file_name()`：根据 `file_name` 删除某个文件关联的向量。
- `search()`：调用 `similarity_search_with_relevance_scores()` 做普通相似度检索，并按分数过滤。
- `search_by_sources()`：根据图谱给出的 `source_file + chunk_index` 精准过滤，再用 query embedding 排序。
- `add_entity()` / `add_relation()`：把知识图谱实体和关系写入专门 collection。
- `search_entities()` / `search_relations()`：根据用户问题检索相关实体和关系。
- `delete_entities_by_file()` / `delete_relations_by_file()`：删除某个来源文件关联的图谱向量。

它还使用稳定 hash 生成实体和关系 id，避免同一实体或关系重复写入。

## 9. 为什么对普通文档和对话历史使用不同的相似度阈值？

**面试官想考察：** 你是否理解检索质量控制。

**参考回答：**

普通文档一般是用户主动上传的知识资料，应该尽量参与回答；而对话历史是系统运行过程中不断积累的内容，如果相似度较低也被检索出来，容易让模型被旧对话带偏。

所以项目对普通检索使用一个较低的默认阈值，比如 `score_threshold=0.1`，但对 `conversation_history` 类型或 `conversation_` 开头的来源设置更高阈值 `CONVERSATION_SCORE_THRESHOLD=0.7`。这样可以让真正相关的历史经验被复用，同时减少无关历史对当前回答的干扰。

## 10. GraphRAG 在这个项目里是怎么工作的？

**面试官想考察：** 你是否能讲清楚图谱和向量检索如何结合。

**参考回答：**

项目的 GraphRAG 不是替代向量检索，而是在向量检索前增加一层结构化召回。

流程是：系统先用问题去 `graph_entities` 和 `graph_relations` collection 中检索相关实体和关系，得到 seed names；然后通过 NetworkX 图仓储对这些种子实体做子图扩展，找出相关路径。路径中带有 `source_file` 和 `source_chunk_id`，系统再用这些信息回到 Chroma 的 `rag_docs` 中精准查找对应文档 chunk。

如果图谱召回的来源不足，系统会再执行普通向量检索做补充。这样既能利用向量检索的语义泛化能力，又能利用知识图谱的结构化路径解释能力。

## 11. 三元组是如何抽取和入库的？

**面试官想考察：** 你是否理解 LLM 在知识图谱构建中的角色。

**参考回答：**

文档完成向量化后，`ImportFileUseCase` 会把每个 chunk 的文本交给 `TripleExtractor`。`TripleExtractor` 会把相邻 chunk 合并成组，然后用线程池并发调用 `GraphExtractionSkill`。

`GraphExtractionSkill` 通过 `ILLMService.stream_chat()` 调 LLM，要求模型只返回 JSON 数组，数组中每项包含 `head`、`head_type`、`relation`、`tail`、`tail_type`。代码会对返回结果做 JSON 解析、字段校验、实体类型和关系类型校验，过滤不合法内容后生成 `Triple` 实体。

最终三元组会写入两个地方：一是 NetworkX 知识图谱文件，二是 Chroma 的实体/关系 collection，用于后续 GraphRAG 召回。

## 12. LLM 服务是如何封装的？为什么要定义 `ILLMService`？

**面试官想考察：** 你是否理解接口抽象和可替换性。

**参考回答：**

项目在应用层定义了 `ILLMService`，只暴露两个能力：`stream_chat()` 和 `chat_with_tools()`。基础设施层的 `LLMService` 用 LangChain 的 `ChatOpenAI` 实现这个接口。

`stream_chat()` 负责把项目内部的 message dict 转成 LangChain 的 `SystemMessage`、`HumanMessage`、`AIMessage` 等对象，然后调用 `ChatOpenAI.stream()`，逐 token yield 给上层。`chat_with_tools()` 则先绑定 tools，再调用 `invoke()`，把模型返回的 tool call 转成项目统一格式。

这样做的好处是应用层不用知道底层是 DeepSeek、OpenAI、Ollama 还是其他模型。只要新实现满足 `ILLMService`，就可以替换模型服务。

## 13. 聊天接口为什么使用 SSE 流式返回？

**面试官想考察：** 你是否理解用户体验和后端实现之间的关系。

**参考回答：**

LLM 生成回答通常耗时较长，如果等完整回答生成完再返回，用户会觉得系统卡住。SSE 适合服务端持续推送文本 token，浏览器端实现也比 WebSocket 简单，符合“一问一答”的聊天场景。

项目的聊天接口会按事件流返回多种事件，例如 `conversation`、`sources`、`generating_tree`、`token`、`fault_tree`、`done`、`error`。这样前端不仅能实时展示模型输出，还能提前拿到引用来源，在故障树生成时展示状态，并在结束时拿到完整答案和故障树 id。

## 14. 故障树生成为什么使用 tool calling，而不是让模型直接输出 JSON？

**面试官想考察：** 你是否理解结构化输出的可靠性。

**参考回答：**

故障树是结构化数据，包含节点、边、节点类型、逻辑门、来源引用等字段。如果只靠 prompt 让模型直接输出 JSON，容易出现格式错误、字段缺失、额外解释文本等问题。

项目使用 tool calling，把 `generate_fault_tree` 和 `update_fault_tree` 定义成工具，并通过 LangChain 的 `bind_tools(tools, tool_choice="required")` 强制模型调用工具。这样模型返回的是结构化 arguments，后端再由 `FaultTreeSkill` 解析成领域实体并保存到数据库。

同时，项目把故障树生成和自然语言说明分开：后台线程负责 tool calling 生成故障树，主流程继续流式输出分析说明，最后再把故障树事件推给前端。

## 15. 故障树更新如何保证不会丢失已有上下文？

**面试官想考察：** 你是否关注多轮编辑和状态一致性。

**参考回答：**

项目会根据 `conversation_id` 查询当前对话已有的故障树，并把已有树的上下文注入系统提示词。用户要求修改时，意图检测器会判断这是更新请求，然后 tool instruction 会要求模型调用 `update_fault_tree`，并在已有结构基础上返回修改后的完整故障树。

后端 `FaultTreeSkill` 执行更新时，会优先根据当前会话找到已有树。如果没有找到旧树，会退化为生成新树。更新后还会把故障树和最新对话轮次关联，保证前端恢复历史时能定位到对应版本。

## 16. 工单模块是怎么接入 RAG 和图谱的？

**面试官想考察：** 你是否理解扩展业务模块如何复用基础能力。

**参考回答：**

工单模块支持 CSV、Excel 和自由文本导入。结构化文件会通过字段别名映射解析成 `WorkOrder` 实体；自由文本则调用 LLM，把非结构化内容抽取成工单字段。

工单保存后，后台会把工单转成 embedding text，并写入独立的 `work_orders` collection。随后系统会先根据工单字段构造规则三元组，例如“设备存在故障”“根因对应故障”“故障由措施处理”；如果配置了三元组抽取器，还会再调用 LLM 补充抽取关系。最终这些三元组会写入知识图谱和图谱向量 collection。

这样工单既能被语义检索，也能成为 GraphRAG 的结构化知识来源。

## 17. 上下文管理模块解决了什么问题？

**面试官想考察：** 你是否理解长上下文和 token 预算问题。

**参考回答：**

随着文档片段、历史对话、图谱路径和系统提示词越来越多，直接全部塞进 prompt 会导致 token 超限、成本变高，也可能让模型注意力分散。

项目通过 `DefaultContextManager` 在生成最终 prompt 前做上下文编排，包括路径裁剪、MMR 去重、检索重排、token 预算评估，以及必要时对历史或向量上下文进行压缩。`ChatContextBuilder` 会优先使用上下文管理器的结果，如果模块异常，会回退到旧的上下文拼接逻辑，保证主流程可用。

这种设计把上下文优化做成可插拔能力，不影响聊天主链路的稳定性。

## 18. 项目如何处理异步任务和失败降级？

**面试官想考察：** 你是否关注工程可靠性。

**参考回答：**

项目里很多耗时任务都放到了后台线程，避免阻塞 HTTP 请求。例如文件向量化、工单后处理、故障树 tool calling、专家学习和对话轮次索引。

失败处理上也有分层降级：

- 文件入库分成同步保存和异步嵌入，嵌入失败会更新文件状态为 `FAILED`。
- 知识图谱构建失败不会影响已经完成的向量检索。
- GraphRAG 检索失败会回退到普通向量检索。
- 上下文管理失败会回退到 legacy prompt 拼接。
- 故障树生成失败时，聊天说明仍可输出，并给用户提示重试。

这样的设计能保证核心问答能力尽量不中断。

## 19. 这个项目目前有哪些潜在问题或可以优化的地方？

**面试官想考察：** 你是否能客观分析项目不足。

**参考回答：**

可以从几个方向优化：

- 并发控制：三元组抽取线程池最大 worker 较高，实际生产中需要结合模型 QPS、限流和重试策略调整。
- 结构化输出：图谱抽取和工单解析目前是 prompt + JSON 解析，可以升级为更严格的 tool calling 或 schema 校验。
- 向量评分：不同 Chroma API 返回的 relevance score 和 distance 转换方式不完全一致，可以统一封装评分归一化逻辑。
- 可观测性：可以增加每次检索、上下文裁剪、LLM 调用耗时和 token 估算日志，便于排查效果问题。
- 数据一致性：向量库、SQLite、知识图谱文件之间目前是多存储写入，可以进一步设计事务补偿或重建机制。
- 安全性：上传文件需要更严格的大小、类型、内容扫描限制，避免异常文件拖垮解析流程。

回答时可以强调：这些不是项目不可用，而是从原型走向生产时需要加强的工程点。

## 20. 如果让你继续迭代这个项目，你会优先做什么？

**面试官想考察：** 你是否能制定合理迭代路线。

**参考回答：**

我会优先做三类迭代。

第一是效果评估体系。建立一批工业故障问答、故障树生成、工单解析的测试集，记录召回率、答案准确性、引用命中率和结构化输出合法率。没有评估集，很难判断 RAG 优化是否真的有效。

第二是检索和上下文优化。可以引入 reranker，对向量检索和 GraphRAG 结果做二次排序；同时完善上下文压缩策略，让长文档和多轮会话下的回答更稳定。

第三是生产可靠性。包括 LLM 调用限流、任务队列替代裸线程、向量库和图谱重建脚本、统一日志链路、上传文件安全校验，以及更完整的自动化测试。

这样迭代顺序兼顾效果、成本和稳定性，比较适合把当前系统从课程/原型项目推进到可演示、可维护的工程系统。

## 面试回答小抄

- 项目定位：工业故障分析场景下的 RAG + GraphRAG + 故障树生成系统。
- 后端架构：Clean Architecture，应用层依赖接口，基础设施层实现 Flask/SQLite/Chroma/LangChain。
- LangChain 用法：主要用 `ChatOpenAI.stream`、`bind_tools + invoke`、loader、splitter、Document、Chroma、FastEmbedEmbeddings。
- RAG 亮点：文档结构化切分、Chroma 向量检索、图谱实体/关系召回、图谱路径定位 chunk、上下文管理。
- 故障树亮点：tool calling 生成结构化树，支持多轮更新和对话轮次关联。
- 工单亮点：结构化导入 + LLM 自由文本解析 + 工单专属向量库 + 规则三元组和 LLM 抽取融合。
- 工程亮点：SSE 流式响应、异步后台处理、失败降级、依赖注入、接口抽象。
- 可优化点：评估集、rerank、任务队列、限流、观测日志、schema 校验、数据一致性。