在根目录运行：

uv venv

.venv\Scripts\activate

uv pip install -r requirements.txt

python app.py



项目结构：

Backend/
├── Application/       # 应用层 - 业务用例
│   └── UseCases/
│       ├── ask_pdf_use_case.py    # 查询PDF文档
│       ├── chat_use_case.py       # 聊天功能
│       └── upload_pdf_use_case.py # 上传PDF
├── Domain/           # 领域层 - 核心业务实体
│   ├── Entities/
│   │   └── Equipment.py
│   └── Common/
│       └── Enums/
├── Infrastructure/   # 基础设施层 - 技术实现
│   ├── document/     # PDF处理
│   ├── llm/          # DeepSeek LLM集成
│   └── vectorstore/  # Chroma向量数据库
└── Web/             # Web层 - API端点
    ├── app_factory.py    # 应用工厂/依赖注入
    └── Endpoints/