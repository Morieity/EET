"""生成项目环境安装与运行教程 Word 文档"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def set_font(run, name="等线", size=11, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if color:
        run.font.color.rgb = RGBColor(*color)


def add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    if level == 1:
        set_font(run, size=16, bold=True, color=(31, 73, 125))
    elif level == 2:
        set_font(run, size=13, bold=True, color=(47, 84, 150))
    else:
        set_font(run, size=11, bold=True)
    return p


def add_body(doc, text, indent=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    if indent:
        p.paragraph_format.left_indent = Inches(0.3)
    run = p.add_run(text)
    set_font(run, size=11)
    return p


def add_code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.font.name = "Courier New"
    run.font.size = Pt(10)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Courier New")
    run.font.color.rgb = RGBColor(0, 100, 0)
    # 灰色背景
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F2F2F2")
    p._p.pPr.append(shd)
    return p


def add_note(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    set_font(run, size=10, color=(128, 128, 128))
    return p


def add_divider(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run("─" * 50)
    set_font(run, size=9, color=(180, 180, 180))
    return p


doc = Document()

# 页面边距
for section in doc.sections:
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1.2)
    section.right_margin = Inches(1.2)

# 标题
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(10)
p.paragraph_format.space_after = Pt(6)
run = p.add_run("RAG 系统环境安装与运行指南")
set_font(run, size=22, bold=True, color=(31, 73, 125))

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
p2.paragraph_format.space_after = Pt(12)
run2 = p2.add_run("适用平台：Windows / macOS / Linux")
set_font(run2, size=11, color=(128, 128, 128))

add_divider(doc)

# ──────────────── 一、环境概览 ────────────────
add_heading(doc, "一、环境概览", 1)
add_body(doc, "本项目分为后端（Python）和前端（Node.js）两部分，运行前请确认以下软件已安装：")
add_body(doc, "  后端      Python 3.11    uv 包管理工具", indent=False)
add_body(doc, "  前端      Node.js 18+    npm 9+", indent=False)
add_body(doc, "  向量化    首次运行时自动下载 BGE 嵌入模型（需联网，约 130 MB）", indent=False)

add_divider(doc)

# ──────────────── 二、后端环境安装 ────────────────
add_heading(doc, "二、后端环境安装", 1)

add_heading(doc, "2.1  安装 Python 3.11", 2)
add_body(doc, "前往官网 https://python.org/downloads 下载并安装 Python 3.11。")
add_body(doc, "安装时勾选「Add Python to PATH」，安装完成后验证：")
add_code(doc, "python --version")
add_note(doc, "# 预期输出：Python 3.11.x")

add_heading(doc, "2.2  安装 uv", 2)
add_body(doc, "uv 是高性能的 Python 包管理工具，用于替代 pip + venv。")
add_body(doc, "Windows（PowerShell）：")
add_code(doc, "powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
add_body(doc, "macOS / Linux：")
add_code(doc, "curl -LsSf https://astral.sh/uv/install.sh | sh")
add_body(doc, "安装完成后验证：")
add_code(doc, "uv --version")

add_heading(doc, "2.3  创建虚拟环境", 2)
add_body(doc, "在项目根目录（rag/）执行：")
add_code(doc, "cd rag")
add_code(doc, "uv venv --python 3.11")
add_note(doc, "# 将在当前目录下创建 .venv 文件夹")

add_heading(doc, "2.4  激活虚拟环境", 2)
add_body(doc, "Windows：")
add_code(doc, ".venv\\Scripts\\activate")
add_body(doc, "macOS / Linux：")
add_code(doc, "source .venv/bin/activate")
add_note(doc, "# 激活后命令行前缀会显示 (.venv)")

add_heading(doc, "2.5  安装 Python 依赖", 2)
add_body(doc, "虚拟环境激活后，执行以下命令安装所有依赖：")
add_code(doc, "uv pip install -r requirements.txt")
add_note(doc, "# 依赖较多，首次安装约需 3～10 分钟，请耐心等待")

add_heading(doc, "2.6  配置环境变量", 2)
add_body(doc, "在项目根目录创建 .env 文件，写入 API Key：")
add_code(doc, "DEEPSEEK_API_KEY=your_api_key_here")
add_note(doc, "# 将 your_api_key_here 替换为真实的 DeepSeek API Key")

add_divider(doc)

# ──────────────── 三、向量化模型说明 ────────────────
add_heading(doc, "三、向量化嵌入模型", 1)

add_body(doc, "本项目使用 FastEmbedEmbeddings 进行文档向量化，底层模型为：")
add_body(doc, "  模型名称：BAAI/bge-small-en-v1.5（ONNX 量化版）")
add_body(doc, "  模型大小：约 130 MB")
add_body(doc, "  缓存目录：rag/llm_model/（自动创建）")
add_body(doc, "  向量数据库：ChromaDB，数据持久化在 rag/db/ 目录")
add_body(doc, "首次启动后端时，程序会自动从 HuggingFace 下载模型并缓存到本地。")
add_body(doc, "后续启动直接读取本地缓存，无需重复下载。")
add_note(doc, "# 若网络无法访问 HuggingFace，可手动下载后放置到 llm_model/ 目录")

add_divider(doc)

# ──────────────── 四、前端环境安装 ────────────────
add_heading(doc, "四、前端环境安装", 1)

add_heading(doc, "4.1  安装 Node.js", 2)
add_body(doc, "前往 https://nodejs.org 下载并安装 LTS 版本（18 或以上）。")
add_body(doc, "安装完成后验证：")
add_code(doc, "node --version")
add_code(doc, "npm --version")
add_note(doc, "# 预期：node v18.x.x 或更高，npm 9.x.x 或更高")

add_heading(doc, "4.2  安装前端依赖", 2)
add_body(doc, "进入前端目录并安装依赖：")
add_code(doc, "cd rag/frontend")
add_code(doc, "npm install")
add_note(doc, "# 首次安装约需 2～5 分钟")

add_divider(doc)

# ──────────────── 五、运行项目 ────────────────
add_heading(doc, "五、运行项目", 1)

add_heading(doc, "5.1  启动后端", 2)
add_body(doc, "在项目根目录（rag/），确保虚拟环境已激活，执行：")
add_code(doc, "python main.py")
add_body(doc, "启动成功后终端显示：")
add_code(doc, " * Running on http://0.0.0.0:8080")
add_note(doc, "# 后端监听端口 8080，debug 模式，支持多线程并发")

add_heading(doc, "5.2  启动前端", 2)
add_body(doc, "新开一个终端窗口，进入前端目录：")
add_code(doc, "cd rag/frontend")
add_code(doc, "npm start")
add_body(doc, "启动成功后浏览器将自动打开：")
add_code(doc, "http://localhost:3000")
add_note(doc, "# 前端开发服务器支持热重载")

add_heading(doc, "5.3  目录结构速查", 2)
add_body(doc, "rag/")
add_body(doc, "  backend/        后端源代码（Clean Architecture）", indent=True)
add_body(doc, "  frontend/       前端源代码（React 19 + Ant Design）", indent=True)
add_body(doc, "  docs/           项目文档", indent=True)
add_body(doc, "  db/             SQLite 数据库 + ChromaDB 向量库（自动创建）", indent=True)
add_body(doc, "  llm_model/      向量化模型缓存（自动创建）", indent=True)
add_body(doc, "  uploads/        用户上传文件（自动创建）", indent=True)
add_body(doc, "  requirements.txt    Python 依赖清单", indent=True)
add_body(doc, "  main.py             后端启动入口", indent=True)
add_body(doc, "  .env                环境变量配置（需手动创建）", indent=True)

add_divider(doc)

# ──────────────── 六、常见问题 ────────────────
add_heading(doc, "六、常见问题", 1)

add_heading(doc, "Q1  uv 命令找不到", 3)
add_body(doc, "安装 uv 后重新打开终端，或手动将 uv 安装路径加入 PATH 环境变量。")

add_heading(doc, "Q2  模型下载失败", 3)
add_body(doc, "检查网络是否能访问 huggingface.co，或配置镜像：")
add_code(doc, "set HF_ENDPOINT=https://hf-mirror.com")
add_note(doc, "# Windows 临时设置，再次运行 python main.py")

add_heading(doc, "Q3  端口被占用", 3)
add_body(doc, "后端默认 8080，前端默认 3000。如端口冲突，分别修改：")
add_body(doc, "  后端：main.py 第 8 行的 port=8080", indent=True)
add_body(doc, "  前端：在 frontend/ 目录下新建 .env 文件，写入 PORT=3001", indent=True)

add_heading(doc, "Q4  依赖安装报错", 3)
add_body(doc, "确认已激活虚拟环境（命令行前缀显示 .venv），再重新执行安装命令。")

add_divider(doc)

# 页脚注
p_end = doc.add_paragraph()
p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
run_end = p_end.add_run("文档生成日期：2026-04-19")
set_font(run_end, size=9, color=(160, 160, 160))

# 保存
out_path = r"C:\Users\tangx\desktop\rag\docs\项目环境安装与运行指南.docx"
doc.save(out_path)
print(f"文档已生成：{out_path}")
