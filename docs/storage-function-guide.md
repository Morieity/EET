# 存储功能开发指南

本文面向新开发者，专门介绍本项目的「存储功能」：包括文件落盘、元数据入库、向量库存储、对话存储与并发策略。

## 1. 存储能力范围

项目当前存储体系由四部分组成：

- 本地文件存储：`uploads/`
- 元数据与业务数据：SQLite（`db/files.sqlite3`）
- 向量存储：Chroma（`db/` 持久化目录）
- 文档切分与载入：LangChain loaders + text splitter

## 2. 使用的技术

- SQLite（内置数据库）
- SQLite WAL（并发读写优化）
- Chroma 向量数据库
- FastEmbedEmbeddings 向量化模型
- PDFPlumber / Docx2txt / TextLoader
- Flask SSE（文件嵌入状态通知）
- Clean Architecture（接口抽象 + 基础设施实现）

## 3. 存储模型与数据位置

### 3.1 SQLite 表

在 [Backend/Infrastructure/persistence/database.py](../Backend/Infrastructure/persistence/database.py) 中初始化：

- `files`
  - `id`, `file_name`, `file_type`, `created_at`, `status`
- `conversations`
  - `id`, `name`, `created_at`
- `chat_rounds`
  - `id`, `conversation_id`, `question`, `prompt`, `answer`, `sources`, `created_at`

### 3.2 目录

- 业务数据库：`db/files.sqlite3`
- Chroma 持久化：`db/`
- 上传文件：`uploads/`

## 4. 存储调用链路（文件导入）

一次文件上传到可检索的流程：

1. [Backend/Web/Endpoints/FileEndpoint.py](../Backend/Web/Endpoints/FileEndpoint.py) 接收上传
2. [Backend/Application/UseCases/ImportFileUseCase.py](../Backend/Application/UseCases/ImportFileUseCase.py) `receive_file()`
   - 文件保存到 `uploads/`
   - `files` 表创建 `pending` 记录
3. Endpoint 后台线程调用 `embed_file()`
4. [Backend/Infrastructure/document/DocumentProcessor.py](../Backend/Infrastructure/document/DocumentProcessor.py)
   - 加载文档并切 chunk
5. [Backend/Infrastructure/vectorstore/ChromaVectorStoreRepository.py](../Backend/Infrastructure/vectorstore/ChromaVectorStoreRepository.py)
   - 写入向量库并补充 `file_name` 元数据
6. `files.status` 更新为 `embedded` 或 `failed`
7. SSE 接口 `/api/files/<name>/status` 将状态推送给前端

## 5. 存储调用链路（对话持久化）

一次对话请求的存储行为：

1. [Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py) 检索 `sources`
2. LLM 输出后，构造 `ChatRound`
3. [Backend/Infrastructure/persistence/ConversationRepository.py](../Backend/Infrastructure/persistence/ConversationRepository.py)
   - 插入 `chat_rounds`
4. 查询详情时，仓储把 `conversations + chat_rounds` 组装回领域对象

## 6. 存储相关逐文件说明（每个文件做什么）

### 6.1 Domain

- [Backend/Domain/Entities/file.py](../Backend/Domain/Entities/file.py)
  - 文件领域实体，描述文件元数据和状态
- [Backend/Domain/Common/Enums/FileType.py](../Backend/Domain/Common/Enums/FileType.py)
  - 文件类型枚举，含扩展名映射逻辑
- [Backend/Domain/Common/Enums/FileStatus.py](../Backend/Domain/Common/Enums/FileStatus.py)
  - `pending/embedded/failed`
- [Backend/Domain/Entities/conversation.py](../Backend/Domain/Entities/conversation.py)
  - 对话与轮次实体（属于对话存储对象）

### 6.2 Application Interfaces

- [Backend/Application/Interfaces/IFileStorage.py](../Backend/Application/Interfaces/IFileStorage.py)
  - 抽象文件系统操作
- [Backend/Application/Interfaces/IFileRepository.py](../Backend/Application/Interfaces/IFileRepository.py)
  - 抽象 `files` 表操作
- [Backend/Application/Interfaces/IConversationRepository.py](../Backend/Application/Interfaces/IConversationRepository.py)
  - 抽象会话存储操作
- [Backend/Application/Interfaces/IVectorStoreRepository.py](../Backend/Application/Interfaces/IVectorStoreRepository.py)
  - 抽象向量库操作（add/delete/search）
- [Backend/Application/Interfaces/IDocumentProcessor.py](../Backend/Application/Interfaces/IDocumentProcessor.py)
  - 抽象文档加载与切分

### 6.3 Application UseCases

- [Backend/Application/UseCases/ImportFileUseCase.py](../Backend/Application/UseCases/ImportFileUseCase.py)
  - 上传后两阶段流程（同步入库 + 异步向量化）
- [Backend/Application/UseCases/DeleteFileUseCase.py](../Backend/Application/UseCases/DeleteFileUseCase.py)
  - 删除顺序：向量 -> 本地文件 -> DB 记录
- [Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py)
  - 使用检索结果 + 保存对话轮次
- [Backend/Application/UseCases/DeleteConversationUseCase.py](../Backend/Application/UseCases/DeleteConversationUseCase.py)
  - 删除对话数据

### 6.4 Infrastructure

- [Backend/Infrastructure/persistence/database.py](../Backend/Infrastructure/persistence/database.py)
  - SQLite 连接、建表、并发配置（WAL + busy_timeout）
- [Backend/Infrastructure/persistence/FileRepository.py](../Backend/Infrastructure/persistence/FileRepository.py)
  - `files` 表的 CRUD + 实体映射
- [Backend/Infrastructure/persistence/ConversationRepository.py](../Backend/Infrastructure/persistence/ConversationRepository.py)
  - 对话与轮次落库、查询组装
- [Backend/Infrastructure/persistence/LocalFileStorage.py](../Backend/Infrastructure/persistence/LocalFileStorage.py)
  - `uploads/` 文件保存、删除、路径获取
- [Backend/Infrastructure/vectorstore/ChromaVectorStoreRepository.py](../Backend/Infrastructure/vectorstore/ChromaVectorStoreRepository.py)
  - Chroma 写入、删除、检索（含相关度阈值过滤）
- [Backend/Infrastructure/document/DocumentProcessor.py](../Backend/Infrastructure/document/DocumentProcessor.py)
  - 依据文件类型选择 loader 并切分文档

### 6.5 Web 与装配

- [Backend/Web/Endpoints/FileEndpoint.py](../Backend/Web/Endpoints/FileEndpoint.py)
  - 文件相关 API + 状态 SSE
- [Backend/Web/Endpoints/ChatEndpoint.py](../Backend/Web/Endpoints/ChatEndpoint.py)
  - 对话 API（含 sources 回传）
- [Backend/Web/app_factory.py](../Backend/Web/app_factory.py)
  - 把所有仓储、服务、用例装配起来
- [main.py](../main.py)
  - 启动 Flask（`threaded=True`）

### 6.6 测试

- [tests/test_file_api.py](../tests/test_file_api.py)
  - 文件上传、状态流、删除、错误场景
- [tests/test_chat_api.py](../tests/test_chat_api.py)
  - 对话完整流程（间接覆盖会话存储）
- [tests/test_concurrent.py](../tests/test_concurrent.py)
  - 并发读写与并发对话
- [tests/run_all.py](../tests/run_all.py)
  - 一键串行执行所有测试

## 7. 并发与一致性策略（当前实现）

- SQLite 使用 WAL：读写互不完全阻塞，适合轻量并发
- `busy_timeout=5000`：写锁冲突时短暂等待
- Flask `threaded=True`：可同时处理多个终端请求
- 文件向量化在后台线程执行，避免上传接口长阻塞

说明：当前方案适合个人/小团队并发。若要高并发生产场景，可考虑迁移到 PostgreSQL + 专门任务队列。

## 8. 如何阅读这个项目（存储视角）

建议按这个顺序看代码：

1. 看存储接口定义（先理解抽象）
   - [Backend/Application/Interfaces/IFileStorage.py](../Backend/Application/Interfaces/IFileStorage.py)
   - [Backend/Application/Interfaces/IFileRepository.py](../Backend/Application/Interfaces/IFileRepository.py)
   - [Backend/Application/Interfaces/IVectorStoreRepository.py](../Backend/Application/Interfaces/IVectorStoreRepository.py)
2. 看存储实现（再看技术细节）
   - [Backend/Infrastructure/persistence/database.py](../Backend/Infrastructure/persistence/database.py)
   - [Backend/Infrastructure/persistence/FileRepository.py](../Backend/Infrastructure/persistence/FileRepository.py)
   - [Backend/Infrastructure/persistence/LocalFileStorage.py](../Backend/Infrastructure/persistence/LocalFileStorage.py)
   - [Backend/Infrastructure/vectorstore/ChromaVectorStoreRepository.py](../Backend/Infrastructure/vectorstore/ChromaVectorStoreRepository.py)
3. 看业务编排（存储如何被使用）
   - [Backend/Application/UseCases/ImportFileUseCase.py](../Backend/Application/UseCases/ImportFileUseCase.py)
   - [Backend/Application/UseCases/DeleteFileUseCase.py](../Backend/Application/UseCases/DeleteFileUseCase.py)
   - [Backend/Application/UseCases/ChatUseCase.py](../Backend/Application/UseCases/ChatUseCase.py)
4. 看接口层和装配
   - [Backend/Web/Endpoints/FileEndpoint.py](../Backend/Web/Endpoints/FileEndpoint.py)
   - [Backend/Web/app_factory.py](../Backend/Web/app_factory.py)
5. 最后用测试验证
   - [tests/test_file_api.py](../tests/test_file_api.py)
   - [tests/test_concurrent.py](../tests/test_concurrent.py)

## 9. 日常开发检查清单

每次修改存储逻辑后，建议最少执行：

- `python tests/test_file_api.py`
- `python tests/test_chat_api.py`
- `python tests/test_concurrent.py`

如果你只改了数据库连接或并发策略，至少跑并发测试和文件测试。
