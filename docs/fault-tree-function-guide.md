# 故障树功能开发指南

本文面向第一次接手本项目故障树功能的同学，重点讲清楚三件事：

- 故障树在项目里是怎么表示的
- LLM 的 function calling 是怎么把“用户一句话”变成“可落库的故障树”的
- 相关代码应该按什么顺序阅读，才不会一上来就陷进细节里

如果你已经看过对话文档和存储文档，这一篇可以理解为它们在“故障树场景”下的落地版本。

## 1. 先建立整体认识

当前故障树能力不是一个独立系统，而是挂在对话能力上的一条专门分支。

也就是说，用户并不是直接调用“生成故障树函数”，而是先发起一次聊天请求：

- 用户请求进入 [../Backend/Web/Endpoints/ChatEndpoint.py](../Backend/Web/Endpoints/ChatEndpoint.py)
- 对话主流程在 [../Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py)
- `ChatUseCase` 会先让 LLM 判断这次是不是应该触发故障树工具
- 如果是，就调用 [../Backend/Application/Skills/FaultTreeSkill.py](../Backend/Application/Skills/FaultTreeSkill.py)
- `FaultTreeSkill` 把 LLM 返回的参数解析成领域对象并落库
- 结果通过 SSE 事件 `fault_tree` 流式返回给前端

所以，故障树功能本质上是：

1. 对话系统中的一个工具能力
2. 用 function calling 决定是否执行
3. 用独立仓储保存结构化数据
4. 通过 REST API 和 SSE 两种方式对外提供结果

## 2. 故障树在代码里长什么样

先不要急着看 LLM。先看数据结构，因为后面的 function calling、数据库、接口，其实都围着这个结构转。

核心文件：

- [../Backend/Domain/Entities/fault_tree.py](../Backend/Domain/Entities/fault_tree.py)
- [../Backend/Domain/Common/Enums/FaultTreeEnums.py](../Backend/Domain/Common/Enums/FaultTreeEnums.py)

### 2.1 三个核心对象

在 [../Backend/Domain/Entities/fault_tree.py](../Backend/Domain/Entities/fault_tree.py) 里有三个类：

- `FaultTreeNode`
  - 表示一个节点
  - 常见字段：`id`、`label`、`node_type`、`gate_type`、`remark`
- `FaultTreeEdge`
  - 表示一条边
  - 常见字段：`id`、`source_id`、`target_id`
- `FaultTree`
  - 表示整棵树
  - 常见字段：`id`、`name`、`nodes`、`edges`、`created_at`、`conversation_id`

### 2.2 节点类型

在 [../Backend/Domain/Common/Enums/FaultTreeEnums.py](../Backend/Domain/Common/Enums/FaultTreeEnums.py) 中：

- `NodeType.EVENT = "event"`
- `NodeType.GATE = "gate"`
- `GateType.AND = "AND"`
- `GateType.OR = "OR"`

这说明当前实现里的故障树不是“嵌套对象树”，而是更适合前端画图和数据库存储的图结构表示法：

- 节点单独存
- 边单独存
- 用 `source_id -> target_id` 表示连接关系

这种设计的优点很实际：

- 前端画布更容易直接消费
- 更新时可以整体替换节点和边
- 数据库存储简单清晰
- LLM function calling 输出 JSON 也更自然

## 3. function calling 到底是怎么工作的

理解故障树功能，最关键的文件是 [../Backend/Application/Skills/FaultTreeSkill.py](../Backend/Application/Skills/FaultTreeSkill.py) 和 [../Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py)。

### 3.1 工具定义放在哪里

在 [../Backend/Application/Skills/FaultTreeSkill.py](../Backend/Application/Skills/FaultTreeSkill.py) 顶部，有一个 `FAULT_TREE_TOOLS` 常量。

这里定义了两个 OpenAI-compatible tools：

- `generate_fault_tree`
- `update_fault_tree`

每个 tool 都明确描述了：

- 工具名称
- 工具用途
- 参数 schema
- `nodes` 和 `edges` 的字段要求

这一步非常重要，因为 LLM 不是“懂你的 Python 类”，它只认识你给它的 tool schema。

换句话说：

- Python 领域对象定义了“程序内部怎么表示故障树”
- tool schema 定义了“LLM 应该按什么 JSON 结构返回故障树”

这两层必须保持一致。

### 3.2 ChatUseCase 怎么决定调不调用工具

主流程在 [../Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py) 的 `execute()`。

顺序是这样的：

1. 读取或创建对话
2. 从向量库检索上下文 `sources`
3. 组装 `system + 历史轮次 + 当前问题`
4. 调用 `self._llm.chat_with_tools(messages, self._fault_tree_skill.tools)`
5. 看返回值是不是 `tool_call`
6. 如果是，就执行故障树工具；如果不是，就走普通聊天回复

所以这里有两个阶段：

- 第一阶段：让模型“做决策”
- 第二阶段：如果模型决定用工具，再真正执行工具并生成说明文本

### 3.3 为什么不是直接让模型输出故障树 JSON

因为直接输出纯文本 JSON 不够稳定，常见问题包括：

- 字段丢失
- JSON 格式不合法
- `node_type` 和 `gate_type` 拼错
- 更新已有故障树时不清楚应该覆盖还是追加

function calling 的价值就在这里：

- 给模型一个明确的结构契约
- 把“意图识别”和“结构化参数输出”绑在一起
- 让后端拿到的是 `arguments: dict`，不是一坨不稳定文本

### 3.4 工具执行后做了什么

当 `ChatUseCase` 判断返回的是 `tool_call` 后，会做这几步：

1. 取出 `func_name` 和 `func_args`
2. 调用 `self._fault_tree_skill.execute(...)`
3. 得到 `FaultTree` 实体
4. 先 `yield {"type": "fault_tree", ...}` 给前端
5. 再让 LLM 根据这次工具结果生成自然语言说明
6. 最后把问答轮次保存到对话表里

这意味着前端会先收到一份结构化故障树，再继续收到解释文字。

这也是当前实现一个很好的地方：

- 前端不需要等整段文字输出完，先拿到树就可以渲染
- 文本说明只是“补充解释”，不是唯一结果载体

## 4. generate 和 update 两个工具分别怎么落地

### 4.1 `generate_fault_tree`

生成逻辑在 [../Backend/Application/Skills/FaultTreeSkill.py](../Backend/Application/Skills/FaultTreeSkill.py) 的 `_generate()`：

- 先通过 `_parse_tree_data()` 把 `arguments` 解析成 `name + nodes + edges`
- 再创建 `FaultTree` 实体
- 调用仓储 `self._repo.save(fault_tree)` 落库

这个流程对应“新建一棵树”。

### 4.2 `update_fault_tree`

更新逻辑在同文件的 `_update()`：

- 如果本轮对话有 `conversation_id`，先查这次对话关联的已有故障树
- 再解析 LLM 给出的完整新结构
- 如果已有树存在，就原地更新 `name/nodes/edges`
- 不存在则退化成一次新生成

这里有一个很重要的业务约束：

- `update_fault_tree` 不是“补丁式修改”
- 它要求 LLM 提供“修改后的完整结构”

这个约束在 tool schema 的描述里已经写了。这样做的好处是后端逻辑很简单，仓储层也只需要整体替换节点和边。

## 5. 多轮对话为什么能改同一棵故障树

这是很多人第一次读代码时会忽略的点。

关键不在前端，而在两个地方：

- `FaultTree.conversation_id`
- `FaultTreeSkill.get_existing_tree_context()`

### 5.1 `conversation_id` 的作用

每棵故障树都可以关联一个 `conversation_id`。这表示：

- 这棵树是在哪段对话里产生的
- 后续如果用户继续在同一个 `conversation_id` 下追问，系统可以把它当成“修改同一棵树”

### 5.2 上下文注入的作用

在 [../Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py) 中，系统会调用：

- `self._fault_tree_skill.get_existing_tree_context(conversation.id)`

这个方法会把当前对话已存在的故障树转成一段文本，拼到 system prompt 后面，大致内容包括：

- 故障树名称
- 当前节点 JSON
- 当前边 JSON
- 如果用户要求修改，请调用 `update_fault_tree`
- 如果用户要的是另一棵新树，请调用 `generate_fault_tree`

这一步很关键。因为模型本身不会“记住数据库里的树”，必须由后端主动把树注入上下文，它才知道应该改哪一棵。

## 6. 数据是怎么存到数据库里的

这部分主要看：

- [../Backend/Infrastructure/persistence/database.py](../Backend/Infrastructure/persistence/database.py)
- [../Backend/Infrastructure/persistence/FaultTreeRepository.py](../Backend/Infrastructure/persistence/FaultTreeRepository.py)

### 6.1 三张表

在 [../Backend/Infrastructure/persistence/database.py](../Backend/Infrastructure/persistence/database.py) 中，故障树相关有三张表：

- `fault_trees`
  - 主表，存树本身：`id/name/conversation_id/created_at`
- `fault_tree_nodes`
  - 节点表，存所有节点
- `fault_tree_edges`
  - 边表，存所有连接关系

这和领域层的设计是一一对应的：

- 一棵树对应一个 `FaultTree`
- 多个节点对应 `FaultTreeNode`
- 多条边对应 `FaultTreeEdge`

### 6.2 仓储如何保存

在 [../Backend/Infrastructure/persistence/FaultTreeRepository.py](../Backend/Infrastructure/persistence/FaultTreeRepository.py) 中：

- `save()`
  - 先写 `fault_trees`
  - 再批量插入节点和边
- `get_by_id()`
  - 查主表，再查节点和边，最后重建 `FaultTree`
- `get_by_conversation_id()`
  - 根据 `conversation_id` 找最近一棵树
- `update()`
  - 先更新主表
  - 然后删除旧节点和旧边
  - 再插入新的完整结构
- `delete()`
  - 先删节点和边，再删主表

这里的更新策略是“整体替换”，不是局部 diff。它简单但有效，尤其适合当前这种 LLM 一次性返回完整结构的场景。

## 7. REST API 和 SSE 分别负责什么

故障树功能对外其实有两套入口。

### 7.1 聊天入口：用于生成和修改

入口文件： [../Backend/Web/Endpoints/ChatEndpoint.py](../Backend/Web/Endpoints/ChatEndpoint.py)

核心接口：

- `POST /api/chat`

当聊天命中故障树工具时，SSE 会返回这些事件：

- `conversation`
- `sources`
- `fault_tree`
- 多个 `token`
- `done`
- 异常情况下可能有 `error`

你可以把它理解为：

- `fault_tree` 负责结构化结果
- `token` 负责自然语言解释

### 7.2 故障树 REST 接口：用于查、改、删

入口文件： [../Backend/Web/Endpoints/FaultTreeEndpoint.py](../Backend/Web/Endpoints/FaultTreeEndpoint.py)

接口包括：

- `GET /api/fault-trees`
- `GET /api/fault-trees/<tree_id>`
- `GET /api/fault-trees/conversation/<conversation_id>`
- `PUT /api/fault-trees/<tree_id>`
- `DELETE /api/fault-trees/<tree_id>`

这套接口适合：

- 前端单独读取已有故障树
- 手工编辑后直接覆盖
- 删除历史数据

也就是说：

- 聊天接口偏“智能生成与智能修改”
- REST 接口偏“标准 CRUD”

## 8. LLM 层到底做了什么

如果你想知道 “`chat_with_tools()` 最后怎么真的调到模型”，去看 [../Backend/Infrastructure/llm/LLMService.py](../Backend/Infrastructure/llm/LLMService.py)。

这里主要做了三件事：

1. 用 `ChatOpenAI` 初始化模型客户端
2. 用 `bind_tools(tools)` 把故障树工具描述绑定给模型
3. 把 LangChain 返回的 `tool_calls` 转成项目统一格式：
   - 普通回复：`{"type": "text", "content": ...}`
   - 工具调用：`{"type": "tool_call", "name": ..., "arguments": {...}}`

这层的职责不是业务判断，而是协议适配：

- 把项目里的 `messages` 转成 LangChain 消息
- 把 LangChain 返回值转成项目里易处理的 dict

所以如果以后要切模型，优先改这一层，而不是先改 `ChatUseCase`。

## 9. 对话删除为什么会影响故障树

这属于业务关系，不是 function calling 本身，但实际开发里很容易踩坑。

相关文件：

- [../Backend/Application/UseCases/DeleteConversationUseCase.py](../Backend/Application/UseCases/DeleteConversationUseCase.py)

当前实现里，删除对话时会：

1. 查 conversation 是否存在
2. 如果绑定了故障树仓储，就查该对话关联的故障树
3. 先删关联故障树
4. 再删对话

这么做是为了避免“对话没了，但树还挂在数据库里”的孤立数据。

所以在业务上，当前项目默认认为：

- 故障树是聊天过程的产物
- 对话被删掉时，关联树也应该一起删掉

## 10. 推荐阅读顺序

这一节最重要。第一次看代码，不建议按文件夹从上往下扫。

### 10.1 5 分钟快速理解版

如果你只想先搞懂主链路，按这个顺序看：

1. [../Backend/Web/Endpoints/ChatEndpoint.py](../Backend/Web/Endpoints/ChatEndpoint.py)
2. [../Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py)
3. [../Backend/Application/Skills/FaultTreeSkill.py](../Backend/Application/Skills/FaultTreeSkill.py)
4. [../Backend/Domain/Entities/fault_tree.py](../Backend/Domain/Entities/fault_tree.py)
5. [../Backend/Infrastructure/persistence/FaultTreeRepository.py](../Backend/Infrastructure/persistence/FaultTreeRepository.py)

看完这五个文件，你基本就能回答：

- 请求从哪进来
- 什么时候会触发工具
- 工具长什么样
- 树怎么存
- 更新怎么做

### 10.2 适合第一次接手功能的完整顺序

建议按下面顺序读：

1. 从入口看输出长什么样
   - [../Backend/Web/Endpoints/ChatEndpoint.py](../Backend/Web/Endpoints/ChatEndpoint.py)
   - [../Backend/Web/Endpoints/FaultTreeEndpoint.py](../Backend/Web/Endpoints/FaultTreeEndpoint.py)
2. 看主业务编排
   - [../Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py)
   - [../Backend/Application/UseCases/FaultTreeUseCase.py](../Backend/Application/UseCases/FaultTreeUseCase.py)
   - [../Backend/Application/UseCases/DeleteConversationUseCase.py](../Backend/Application/UseCases/DeleteConversationUseCase.py)
3. 看 function calling 的定义和执行
   - [../Backend/Application/Skills/FaultTreeSkill.py](../Backend/Application/Skills/FaultTreeSkill.py)
4. 看领域对象，确认数据结构
   - [../Backend/Domain/Entities/fault_tree.py](../Backend/Domain/Entities/fault_tree.py)
   - [../Backend/Domain/Common/Enums/FaultTreeEnums.py](../Backend/Domain/Common/Enums/FaultTreeEnums.py)
5. 看抽象接口，理解依赖倒置
   - [../Backend/Application/Interfaces/ILLMService.py](../Backend/Application/Interfaces/ILLMService.py)
   - [../Backend/Application/Interfaces/IFaultTreeRepository.py](../Backend/Application/Interfaces/IFaultTreeRepository.py)
   - [../Backend/Application/Interfaces/IConversationRepository.py](../Backend/Application/Interfaces/IConversationRepository.py)
6. 看具体实现
   - [../Backend/Infrastructure/llm/LLMService.py](../Backend/Infrastructure/llm/LLMService.py)
   - [../Backend/Infrastructure/persistence/FaultTreeRepository.py](../Backend/Infrastructure/persistence/FaultTreeRepository.py)
   - [../Backend/Infrastructure/persistence/ConversationRepository.py](../Backend/Infrastructure/persistence/ConversationRepository.py)
   - [../Backend/Infrastructure/persistence/database.py](../Backend/Infrastructure/persistence/database.py)
7. 看依赖装配
   - [../Backend/Web/app_factory.py](../Backend/Web/app_factory.py)
   - [../main.py](../main.py)
8. 最后看测试验证理解
   - [../tests/test_fault_tree_api.py](../tests/test_fault_tree_api.py)
   - [../tests/test_chat_api.py](../tests/test_chat_api.py)
   - [../tests/test_concurrent.py](../tests/test_concurrent.py)

### 10.3 为什么推荐这个顺序

因为这个功能跨了四层：

- Web
- Application
- Domain
- Infrastructure

如果你一开始先看仓储或数据库，很容易只看到“怎么存”，却看不懂“为什么这样存”。

最稳妥的方式是：

- 先看入口和输出
- 再看业务编排
- 再看数据结构
- 最后看底层实现

## 11. 测试文件该怎么用

最值得先看的测试是 [../tests/test_fault_tree_api.py](../tests/test_fault_tree_api.py)。

这个文件几乎就是一份“故障树功能使用说明书”，因为它覆盖了：

- 通过聊天生成故障树
- 按 `conversation_id` 查询树
- 按 `tree_id` 查询树
- 列表查询
- 直接通过 REST 更新故障树
- 通过聊天继续修改故障树
- 404 / 400 等错误分支
- 删除和级联删除行为
- SSE `error` 事件

如果你已经读完主链路，再回来看测试，会很容易对上每个接口和行为。

辅助测试是：

- [../tests/test_chat_api.py](../tests/test_chat_api.py)
  - 看 SSE 对话协议本身
- [../tests/test_concurrent.py](../tests/test_concurrent.py)
  - 看并发场景下聊天接口如何工作

## 12. 新同学最容易困惑的几个点

### 12.1 `FaultTreeSkill` 为什么叫 Skill，不叫 Service

因为它不是单纯的基础设施服务，而是一个“给 LLM 暴露工具能力”的应用层组件。它同时承担两件事：

- 定义 tools schema
- 执行 tool 对应的业务

所以它更接近“技能”或“工具封装层”。

### 12.2 为什么故障树更新不是部分更新

因为当前 function calling 设计就是让模型返回完整结构。这样后端简单，仓储也稳定。

如果以后要支持局部编辑，通常要新增：

- 更细粒度的 tool
- 更严格的节点 ID 约束
- 后端 patch 逻辑

### 12.3 为什么故障树不直接嵌在 Conversation 里

因为它本质上是单独的业务对象：

- 它有自己的 CRUD
- 前端可能单独查询和编辑
- 它有节点表和边表

所以当前做法是：

- 会话负责聊天上下文
- 故障树单独建表
- 两者用 `conversation_id` 关联

## 13. 你以后改功能时，优先去哪里改

可以按需求类型定位文件：

- 想改“什么时候触发故障树工具”
  - 看 [../Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py)
- 想改“工具参数格式”
  - 看 [../Backend/Application/Skills/FaultTreeSkill.py](../Backend/Application/Skills/FaultTreeSkill.py)
- 想改“节点/边的数据结构”
  - 看 [../Backend/Domain/Entities/fault_tree.py](../Backend/Domain/Entities/fault_tree.py)
- 想改“数据库怎么存”
  - 看 [../Backend/Infrastructure/persistence/FaultTreeRepository.py](../Backend/Infrastructure/persistence/FaultTreeRepository.py)
  - 看 [../Backend/Infrastructure/persistence/database.py](../Backend/Infrastructure/persistence/database.py)
- 想改“故障树的 REST 接口”
  - 看 [../Backend/Web/Endpoints/FaultTreeEndpoint.py](../Backend/Web/Endpoints/FaultTreeEndpoint.py)
- 想改“模型接入方式”
  - 看 [../Backend/Infrastructure/llm/LLMService.py](../Backend/Infrastructure/llm/LLMService.py)

## 14. 一句话总结当前实现

当前项目的故障树实现方式可以概括成一句话：

通过对话请求进入主流程，由 LLM 用 function calling 决定是否调用 `generate_fault_tree` 或 `update_fault_tree`，后端把工具参数解析为 `FaultTree` 领域对象，存入 SQLite，并通过 SSE 把结构化故障树和解释文本一起返回给前端。

如果你是第一次接手，最推荐的阅读起点仍然是：

- [../Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py)
- [../Backend/Application/Skills/FaultTreeSkill.py](../Backend/Application/Skills/FaultTreeSkill.py)
- [../tests/test_fault_tree_api.py](../tests/test_fault_tree_api.py)

这三个文件一起看，理解速度最快。