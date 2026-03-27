from flask import Flask
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

from Backend.Application.UseCases.ask_pdf_use_case import AskPdfUseCase
from Backend.Application.UseCases.create_session_use_case import CreateSessionUseCase
from Backend.Application.UseCases.diagnose_use_case import DiagnoseUseCase
from Backend.Application.UseCases.get_session_use_case import GetSessionUseCase
from Backend.Application.UseCases.upload_document_use_case import UploadDocumentUseCase
from Backend.Application.UseCases.upload_pdf_use_case import UploadPdfUseCase
from Backend.Infrastructure.document.deduplicator import ThreeTierDeduplicator
from Backend.Infrastructure.document.pdf_loader import load_pdf
from Backend.Infrastructure.document.text_splitter import build_text_splitter
from Backend.Infrastructure.llm.deepseek_client import DeepSeekChatProvider
from Backend.Infrastructure.llm.diagnosis_llm_adapter import DiagnosisLlmAdapter
from Backend.Infrastructure.persistence.database import init_db
from Backend.Infrastructure.persistence.session_repository import SessionRepositoryImpl
from Backend.Infrastructure.vectorstore.chroma_repository import ChromaVectorStoreRepository
from Backend.Web.Endpoints.diagnosis import create_blueprint as create_diagnosis_blueprint
from Backend.Web.Endpoints.documents import create_blueprint as create_document_blueprint
from Backend.Web.Endpoints.llmchat import create_blueprint as create_chat_blueprint
from Backend.Web.Endpoints.pdfpost import create_blueprint as create_pdf_blueprint


def create_app(db_path: str = "db", pdf_dir: str = "pdf") -> Flask:
    """组装应用依赖并返回已配置的 Flask 应用实例。"""
    # 初始化数据库表
    init_db()

    # 初始化 LLM 提供者、向量嵌入模型和文本分割器
    chat_provider = DeepSeekChatProvider()
    embedding = FastEmbedEmbeddings()
    text_splitter = build_text_splitter()

    # 创建向量存储仓库实例
    vector_store_repository = ChromaVectorStoreRepository(
        persist_directory=db_path,
        embedding=embedding,
    )

    # ---- 原有用例 ----
    ask_pdf_use_case = AskPdfUseCase(
        retriever_factory=vector_store_repository,
        llm=chat_provider.client,
    )
    upload_pdf_use_case = UploadPdfUseCase(
        pdf_dir=pdf_dir,
        loader=load_pdf,
        splitter=text_splitter,
        vector_store_repository=vector_store_repository,
    )

    # ---- US1: 知识库文档上传与向量化 ----
    deduplicator = ThreeTierDeduplicator(
        retriever_factory=vector_store_repository,
        similarity_threshold=0.95,
    )
    upload_document_use_case = UploadDocumentUseCase(
        pdf_dir=pdf_dir,
        loader=load_pdf,
        splitter=text_splitter,
        vector_store_repository=vector_store_repository,
        deduplicator=deduplicator,
    )

    # ---- US2: 多轮对话式故障诊断 ----
    session_repository = SessionRepositoryImpl()
    diagnosis_llm = DiagnosisLlmAdapter(llm=chat_provider.client)

    create_session_use_case = CreateSessionUseCase(
        session_repository=session_repository,
        diagnosis_llm=diagnosis_llm,
        retriever_factory=vector_store_repository,
    )
    diagnose_use_case = DiagnoseUseCase(
        session_repository=session_repository,
        diagnosis_llm=diagnosis_llm,
        retriever_factory=vector_store_repository,
    )
    get_session_use_case = GetSessionUseCase(
        session_repository=session_repository,
    )

    # 创建 Flask 应用并注册蓝图
    app = Flask(__name__)

    # 注册聊天蓝图（基于 RAG）
    app.register_blueprint(create_chat_blueprint(ask_pdf_use_case=ask_pdf_use_case))

    # 注册 PDF 蓝图（上传和向量化 — 原有接口）
    app.register_blueprint(create_pdf_blueprint(upload_pdf_use_case=upload_pdf_use_case))

    # 注册文档蓝图（US1: 带去重的文档上传）
    app.register_blueprint(create_document_blueprint(
        upload_document_use_case=upload_document_use_case,
    ))

    # 注册诊断蓝图（US2: 多轮对话式故障诊断）
    app.register_blueprint(create_diagnosis_blueprint(
        create_session_use_case=create_session_use_case,
        diagnose_use_case=diagnose_use_case,
        get_session_use_case=get_session_use_case,
    ))

    return app
