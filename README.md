# RAG 智能问答系统

基于 Clean Architecture 的检索增强生成（RAG）系统，集成文档向量化、知识图谱构建与大模型问答能力。后端采用 Python（Flask + ChromaDB + DeepSeek），前端采用 React 19 + Ant Design。

---

## 一、环境概览

本项目分为**后端（Python）**和**前端（Node.js）**两部分，运行前请确认以下软件已安装：

| 模块 | 依赖 | 版本要求 |
| --- | --- | --- |
| 后端 | Python | 3.11 |
| 后端 | uv | 最新版（包管理工具） |
| 前端 | Node.js | 18+ |
| 前端 | npm | 9+ |
| 向量化 | BGE 嵌入模型 | 首次运行自动下载（需联网，约 130 MB） |

---

## 二、后端环境安装

### 1. 安装 Python 3.11

前往官网 <https://python.org/downloads> 下载并安装 Python 3.11。

> 安装时务必勾选 **「Add Python to PATH」**。

安装完成后验证：

```bash
python --version
# 预期输出：Python 3.11.x
```

### 2. 安装 uv

`uv` 是高性能的 Python 包管理工具，用于替代 `pip + venv`。

**Windows（PowerShell）：**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux / macOS：**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装完成后验证：

```bash
uv --version
```

### 3. 创建虚拟环境

在项目根目录（`rag/`）执行：

```bash
cd rag
uv venv --python 3.11
# 将在当前目录下创建 .venv 文件夹
```

### 4. 激活虚拟环境

**Windows：**

```powershell
.venv\Scripts\activate
```

**Linux / macOS：**

```bash
source .venv/bin/activate
```

> 激活成功后，命令行前缀会显示 `(.venv)`。

### 5. 安装 Python 依赖

虚拟环境激活后，执行：

```bash
uv pip install -r requirements.txt
```

> 依赖较多，首次安装约需 **3 ~ 10 分钟**，请耐心等待。

### 6. 配置环境变量

在项目根目录 `.env` 文件中，写入 API Key：

```env
DEEPSEEK_API_KEY=your_api_key_here
```

> 将 `your_api_key_here` 替换为真实的 DeepSeek API Key。

---

## 三、向量化嵌入模型

本项目使用 `FastEmbedEmbeddings` 进行文档向量化，底层模型为：

- **模型名称**：`BAAI/bge-small-en-v1.5`（ONNX 量化版）
- **模型大小**：约 130 MB
- **缓存目录**：`rag/llm_model/`（自动创建）
- **向量数据库**：ChromaDB，数据持久化在 `rag/db/` 目录

首次启动后端时，程序会自动从 HuggingFace 下载模型并缓存到本地。后续启动直接读取本地缓存，无需重复下载。

---

## 四、前端环境安装

### 1. 安装 Node.js

前往 <https://nodejs.org> 下载并安装 LTS 版本（18 或以上）。

安装完成后验证：

```bash
node --version
npm --version
# 预期：node v18.x.x 或更高，npm 9.x.x 或更高
```

### 2. 安装前端依赖

进入前端目录并安装依赖：

```bash
cd rag/frontend
npm install
# 首次安装约需 2 ~ 5 分钟
```

---

## 五、运行项目

### 1. 启动后端

在项目根目录（`rag/`），确保虚拟环境已激活，执行：

```bash
python main.py
```

启动成功后终端显示：

```
 * Running on http://0.0.0.0:8080
```

> 后端监听端口 **8080**，debug 模式，支持多线程并发。

### 2. 启动前端

新开一个终端窗口，进入前端目录：

```bash
cd rag/frontend
npm start
```

启动成功后浏览器将自动打开：

```
http://localhost:3000
```

> 前端开发服务器支持热重载。

---

## 六、目录结构速查

```
rag/
├── Backend/            后端源代码（Clean Architecture）
│   ├── Application/    应用层（用例、技能、上下文管理）
│   ├── Domain/         领域层（实体与公共模型）
│   ├── Infrastructure/ 基础设施层
│   └── Web/            Web 接口层
├── frontend/           前端源代码（React 19 + Ant Design）
├── docs/               项目文档
├── db/                 SQLite 数据库 + ChromaDB 向量库（自动创建）
├── llm_model/          向量化模型缓存（自动创建）
├── uploads/            用户上传文件（自动创建）
├── tests/              测试用例
├── requirements.txt    Python 依赖清单
├── main.py             后端启动入口
└── .env                环境变量配置（需手动创建）当前给了一个示例
```

---

## 七、常见问题（FAQ）

### Q1：`uv` 命令找不到？

安装 `uv` 后重新打开终端，或手动将 `uv` 安装路径加入 `PATH` 环境变量。

### Q2：模型下载失败？

检查网络是否能访问 `huggingface.co`，或配置国内镜像：

```powershell
# Windows 临时设置
set HF_ENDPOINT=https://hf-mirror.com
# 然后再次运行
python main.py
```

### Q3：端口被占用？

后端默认 **8080**，前端默认 **3000**。如端口冲突，分别修改：

- **后端**：`main.py` 第 8 行的 `port=8080`
- **前端**：
  1. 在 `frontend/` 目录下新建 `.env` 文件，写入 `PORT=3001`
  2. 同步修改 `frontend/src/setupProxy.js` 第 14 行 `url` 中的 `8080` 为新端口

### Q4：依赖安装报错？

确认已激活虚拟环境（命令行前缀显示 `(.venv)`），再重新执行安装命令。

### Q5：文件检索结果为空？

文件导入后，后端会执行：文档切片 → 提取信息三元组 → 构建知识图谱。该过程需要一定时间，请等待构建完成后再进行检索。

---

## 八、技术栈

- **后端**：Python 3.11、Flask、ChromaDB、FastEmbed、DeepSeek LLM
- **前端**：React 19、Ant Design、TailwindCSS
- **架构**：Clean Architecture（领域驱动设计）
- **数据存储**：SQLite + ChromaDB 向量库 + JSON 知识图谱
