from flask import Flask
from flask_cors import CORS
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

from Backend.Application.UseCases.ask_pdf_use_case import AskPdfUseCase
from Backend.Application.UseCases.chat_use_case import ChatUseCase
from Backend.Application.UseCases.upload_pdf_use_case import UploadPdfUseCase
from Backend.Infrastructure.document.pdf_loader import load_pdf
from Backend.Infrastructure.document.text_splitter import build_text_splitter
from Backend.Infrastructure.llm.deepseek_client import DeepSeekChatProvider
from Backend.Infrastructure.vectorstore.chroma_repository import ChromaVectorStoreRepository
from Backend.Web.Endpoints.llmchat import create_blueprint


def create_app(db_path: str = "db", pdf_dir: str = "pdf") -> Flask:
    """组装应用依赖并返回已配置的 Flask 应用实例。"""
    chat_provider = DeepSeekChatProvider()
    embedding = FastEmbedEmbeddings()
    text_splitter = build_text_splitter()

    vector_store_repository = ChromaVectorStoreRepository(
        persist_directory=db_path,
        embedding=embedding,
    )

    raw_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a technical assistant good at searching documents. If you do not have an answer from the provided information say so.",
            ),
            ("human", "{input}\n\nContext:\n{context}"),
        ]
    )

    chat_use_case = ChatUseCase(chat_provider)
    ask_pdf_use_case = AskPdfUseCase(
        retriever_factory=vector_store_repository,
        prompt=raw_prompt,
        llm=chat_provider.client,
    )
    upload_pdf_use_case = UploadPdfUseCase(
        pdf_dir=pdf_dir,
        loader=load_pdf,
        splitter=text_splitter,
        vector_store_repository=vector_store_repository,
    )

    app = Flask(__name__)
    CORS(app)  # 允许跨域请求
    app.register_blueprint(
        create_blueprint(
            chat_use_case=chat_use_case,
            ask_pdf_use_case=ask_pdf_use_case,
            upload_pdf_use_case=upload_pdf_use_case,
        )
    )
    return app
