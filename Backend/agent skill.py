import os
import glob
from dotenv import load_dotenv

from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver


# =========================
# Config
# =========================
CHROMA_PERSIST_DIR = "./chroma_db"
CHROMA_COLLECTION_NAME = "pdf_documents"
PDF_DIR = "./pdf"

DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# =========================
# Environment checks
# =========================
def check_env():
    required_vars = [
        "DEEPSEEK_API_KEY",
    ]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        raise EnvironmentError(
            f"缺少必要环境变量: {missing}\n"
            f"请先设置后再运行。"
        )


# =========================
# ChromaDB setup / PDF loading
# =========================
def load_or_build_vectorstore() -> Chroma:
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    # 如果已有持久化的 ChromaDB，直接加载
    if os.path.exists(CHROMA_PERSIST_DIR) and os.listdir(CHROMA_PERSIST_DIR):
        print("[INFO] 检测到已有 ChromaDB，直接加载...")
        vectorstore = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
        )
        return vectorstore

    # 否则从 PDF 目录加载文档并进行 embedding
    pdf_files = list(set(
        glob.glob(os.path.join(PDF_DIR, "**/*.pdf"), recursive=True) +
        glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    ))

    if not pdf_files:
        raise FileNotFoundError(
            f"在 '{PDF_DIR}' 目录下未找到任何 PDF 文件，"
            f"请确认路径正确且文件存在。"
        )

    print(f"[INFO] 找到 {len(pdf_files)} 个 PDF 文件，开始加载...")
    all_docs = []
    for pdf_path in pdf_files:
        print(f"  - 加载: {os.path.basename(pdf_path)}")
        loader = PyPDFLoader(pdf_path)
        all_docs.extend(loader.load())

    print(f"[INFO] 共加载 {len(all_docs)} 页，开始切分文本...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(all_docs)
    print(f"[INFO] 切分完成，共 {len(chunks)} 个文本块，正在 embedding 并写入 ChromaDB...")

    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    print("[INFO] ChromaDB 构建完成并已持久化")
    return vectorstore


# =========================
# Build agent with history (create_react_agent)
# =========================
def _make_deepseek_llm(temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=DEEPSEEK_API_BASE,
        temperature=temperature,
    )


def build_agent(vectorstore: Chroma):
    chat_llm = _make_deepseek_llm()
    retrieval_llm = _make_deepseek_llm()

    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    qa_prompt = ChatPromptTemplate.from_template(
        "故障树任务要求：1. 三级结构构建：必须清晰划分“顶事件（Top Event）- 中间事件（Intermediate Event）- 底事件（Basic Event）”的传导路径。\n\n"
        "2. 逻辑门推断：根据文档描述判断事件间的逻辑关系（或门/与门）。\n\n"
        "3. 证据溯源：每一层级的推论必须在 `evidence` 字段中引用文档原文或具体参数。\n\n"
        "请根据以下文档内容回答问题，回答要详细准确。\n\n"
        "文档内容：\n{context}\n\n"
        "问题：{question}"
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    pdf_qa_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | qa_prompt
        | retrieval_llm
        | StrOutputParser()
    )

    tools = [
        Tool(
            name="Knowledge_Base",
            func=pdf_qa_chain.invoke,
            description=(
                "用于查询本地 PDF 文档知识库中的内容。"
                "适用于文档中已有记录的专业知识、详细信息或具体内容。"
                "输入应为一个完整的问题句子。"
            ),
        ),
    ]

    system_prompt = (
        "你是一位深耕工业运维领域的“故障树分析（FTA）智能体”。你的任务是严格基于提供的【知识库信息】，针对用户提出的【问题】构建标准化、逻辑严密的故障树结构。\n"
        "请优先使用 Knowledge_Base 工具查询文档内容后再作答。"
    )

    memory = MemorySaver()

    agent = create_react_agent(
        model=chat_llm,
        tools=tools,
        prompt=system_prompt,
        checkpointer=memory,
    )

    return agent






# =========================
# Main
# =========================
def main():
    load_dotenv()  # 自动读取项目根目录的 .env 文件
    check_env()

    # 构建或加载 ChromaDB 向量数据库
    vectorstore = load_or_build_vectorstore()

    # 构建带历史记忆的 Agent
    agent = build_agent(vectorstore)

    # 每个会话用同一个 thread_id，Agent 自动保留对话历史
    config = {"configurable": {"thread_id": "session_1"}}

    def ask(question: str) -> str:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config=config,
        )
        return result["messages"][-1].content

    print("\n================ PDF 知识库 Agent 测试 ================\n")

    result1 = ask("请针对‘SI CU: STOP A被触发’（F01600）生成故障树。")
    print("\n[RESULT 1]", result1)

    result2 = ask("如果控制单元（CU）出现‘内部软件错误’相关的故障现象（如F01015, F01023等），请构建其故障树。")
    print("\n[RESULT 2]", result2)

    result3 = ask("分析‘拓扑：DRIVE-CLIQ组件属性变化’（F01014）的故障树。")
    print("\n[RESULT 3]", result3)


if __name__ == "__main__":
    main()