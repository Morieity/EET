# 对话功能开发指南

本文面向第一次接触本项目的开发同学，专注讲清楚「对话功能」的技术选型、调用链路、文件职责和阅读路径。

## 1. 功能范围

当前对话模块提供：

- 创建新对话并流式返回回答（SSE）
- 在已有对话中继续追问（多轮）
- 获取对话列表
- 获取单个对话详情（含所有轮次）
- 删除对话
- 返回检索文档片段（sources）给前端展示

## 2. 使用的技术

- Web 框架：Flask + Blueprint
- 流式协议：SSE（`text/event-stream`）
- LLM 接入：`langchain-openai` 的 `ChatOpenAI`
- OpenAI 兼容模型：DeepSeek、Qwen（通过 `base_url + api_key + model` 切换）
- 检索层：Chroma + FastEmbedEmbeddings
- 元数据存储：SQLite（`db/files.sqlite3`）
- 架构风格：整洁架构（Domain / Application / Infrastructure / Web）

## 3. API 一览

- `POST /api/chat`
  - 请求体：`{"question": "...", "conversation_id": "..."(可选)}`
  - 返回：SSE 事件流
  - 事件顺序：`conversation` -> `sources` -> 多个 `token` -> `done`
- `GET /api/conversations`
- `GET /api/conversations/<conversation_id>`
- `DELETE /api/conversations/<conversation_id>`

## 4. 调用链路（从请求到落库）

一次 `POST /api/chat` 的主流程：

1. [Backend/Web/Endpoints/ChatEndpoint.py](../Backend/Web/Endpoints/ChatEndpoint.py) 收到请求并校验 `question`
2. endpoint 调用 [Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py) 的 `execute()`
3. UseCase 读取或创建对话（仓储接口 [Backend/Application/Interfaces/IConversationRepository.py](../Backend/Application/Interfaces/IConversationRepository.py)）
4. UseCase 调用向量检索接口 [Backend/Application/Interfaces/IVectorStoreRepository.py](../Backend/Application/Interfaces/IVectorStoreRepository.py) 获取 `sources`
5. UseCase 拼接 `system + history + context + question`
6. UseCase 调用 LLM 接口 [Backend/Application/Interfaces/ILLMService.py](../Backend/Application/Interfaces/ILLMService.py) 进行流式生成
7. endpoint 将每个事件实时写回 SSE
8. UseCase 结束时把本轮问答写入 SQLite（`chat_rounds`）

## 5. 对话功能逐文件说明（每个文件做什么）

### 5.1 Domain（业务实体）

- [Backend/Domain/Entities/conversation.py](../Backend/Domain/Entities/conversation.py)
  - `Conversation`：对话聚合根（id、name、created_at、rounds）
  - `ChatRound`：单轮数据（question、prompt、answer、sources、created_at）
  - `to_dict()`：返回接口层可直接序列化的数据

### 5.2 Application Interfaces（依赖倒置）

- [Backend/Application/Interfaces/IConversationRepository.py](../Backend/Application/Interfaces/IConversationRepository.py)
  - 抽象了对话读写行为：`save/get_by_id/get_all/delete/add_round`
- [Backend/Application/Interfaces/ILLMService.py](../Backend/Application/Interfaces/ILLMService.py)
  - 抽象了 LLM 流式输出：`stream_chat(messages)`
- [Backend/Application/Interfaces/IVectorStoreRepository.py](../Backend/Application/Interfaces/IVectorStoreRepository.py)
  - 对话检索使用 `search()`；文档导入使用 `add_documents()` / `delete_by_file_name()`

### 5.3 Application UseCases（核心业务编排）

- [Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py)
  - 对话主编排器
  - 负责新建/读取会话、检索上下文、组装 prompt、流式生成、保存轮次
  - 对外输出统一事件：`conversation/sources/token/done/error`
- [Backend/Application/UseCases/DeleteConversationUseCase.py](../Backend/Application/UseCases/DeleteConversationUseCase.py)
  - 删除对话前先检查是否存在

### 5.4 Infrastructure（具体实现）

- [Backend/Infrastructure/llm/LLMService.py](../Backend/Infrastructure/llm/LLMService.py)
  - `load_dotenv()` 读取 `.env`
  - 用 `ChatOpenAI` 实现 OpenAI 兼容调用
  - 环境变量：`LLM_MODEL`、`LLM_BASE_URL`、`LLM_API_KEY`、`DEEPSEEK_API_KEY`
- [Backend/Infrastructure/persistence/ConversationRepository.py](../Backend/Infrastructure/persistence/ConversationRepository.py)
  - `SQLiteConversationRepository`
  - `conversations` 与 `chat_rounds` 两表读写
  - `sources` 以 JSON 字符串存储

### 5.5 Web（接口层）

- [Backend/Web/Endpoints/ChatEndpoint.py](../Backend/Web/Endpoints/ChatEndpoint.py)
  - Flask 路由定义与参数校验
  - 将 UseCase 事件转换为 SSE 输出
  - 对列表/详情/删除接口直接调用仓储或删除用例
- [Backend/Web/app_factory.py](../Backend/Web/app_factory.py)
  - 依赖注入装配点
  - 实例化：`LLMService`、`SQLiteConversationRepository`、`ChatUseCase`
- [main.py](../main.py)
  - 启动入口（`threaded=True`，允许多请求并发）

### 5.6 测试文件

- [tests/test_chat_api.py](../tests/test_chat_api.py)
  - 覆盖对话模块主流程与错误分支
- [tests/test_concurrent.py](../tests/test_concurrent.py)
  - 覆盖并发对话与并发读写场景

## 6. SSE 事件契约（前端对接重点）

- `event: conversation`
  - data: `{"conversation_id": "...", "name": "..."}`
- `event: sources`
  - data: `{"sources": [{"file_name": "...", "page_content": "...", "score": 0.0}]}`
- `event: token`
  - data: `{"content": "..."}`
- `event: done`
  - data: `{"conversation_id": "...", "answer": "..."}`
- `event: error`
  - data: `{"message": "..."}`

## 7. 如何阅读这个项目（对话视角）

建议按下面顺序读：

1. 先看路由输入输出：
   - [Backend/Web/Endpoints/ChatEndpoint.py](../Backend/Web/Endpoints/ChatEndpoint.py)
2. 再看业务编排：
   - [Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py)
3. 看数据结构：
   - [Backend/Domain/Entities/conversation.py](../Backend/Domain/Entities/conversation.py)
4. 看依赖抽象：
   - [Backend/Application/Interfaces/IConversationRepository.py](../Backend/Application/Interfaces/IConversationRepository.py)
   - [Backend/Application/Interfaces/ILLMService.py](../Backend/Application/Interfaces/ILLMService.py)
5. 看基础设施实现：
   - [Backend/Infrastructure/llm/LLMService.py](../Backend/Infrastructure/llm/LLMService.py)
   - [Backend/Infrastructure/persistence/ConversationRepository.py](../Backend/Infrastructure/persistence/ConversationRepository.py)
6. 最后看装配和启动：
   - [Backend/Web/app_factory.py](../Backend/Web/app_factory.py)
   - [main.py](../main.py)
7. 用测试验证认知：
   - [tests/test_chat_api.py](../tests/test_chat_api.py)
   - [tests/test_concurrent.py](../tests/test_concurrent.py)

## 8. 常见扩展点

- 修改对话命名规则：`ChatUseCase.execute()` 中创建对话名称逻辑
- 调整历史轮次：`MAX_HISTORY_ROUNDS`
- 增加 prompt 策略：`SYSTEM_PROMPT` 与 `user_content` 拼接规则
- 切换模型：`.env` 或环境变量中的 `LLM_MODEL/LLM_BASE_URL/LLM_API_KEY`
- 给 `sources` 增加字段：修改 `IVectorStoreRepository.search()` 与 Chroma 实现
