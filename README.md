# RAG 项目开发入口

本仓库是一个基于 Flask + 整洁架构（Clean Architecture）的 RAG 项目，包含两条核心能力：

- 文档导入与检索（文件上传、切分、向量化、检索）
- 对话模块（SSE 流式输出、多轮会话、会话持久化）

## 1. 快速启动

在项目根目录执行：

```powershell
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
python main.py
```

服务默认地址：`http://127.0.0.1:8080`

## 2. 面向新开发者的功能文档

- [docs/chat-function-guide.md](docs/chat-function-guide.md)（对话功能开发指南）
- [docs/storage-function-guide.md](docs/storage-function-guide.md)（存储功能开发指南）

## 3. 推荐阅读顺序

1. [Backend/Web/app_factory.py](Backend/Web/app_factory.py)（看依赖如何装配）
2. [Backend/Web/Endpoints/FileEndpoint.py](Backend/Web/Endpoints/FileEndpoint.py) 和 [Backend/Web/Endpoints/ChatEndpoint.py](Backend/Web/Endpoints/ChatEndpoint.py)（看输入输出）
3. `Backend/Application/UseCases`（看业务编排）
4. `Backend/Application/Interfaces`（看抽象边界）
5. `Backend/Infrastructure`（看具体技术实现）
6. `Backend/Domain`（看核心实体与枚举）

## 4. 测试

- 文档功能测试：`python tests/test_file_api.py`
- 对话功能测试：`python tests/test_chat_api.py`
- 并发测试：`python tests/test_concurrent.py`
- 一键运行：`python tests/run_all.py`