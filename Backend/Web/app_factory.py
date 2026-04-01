from flask import Flask
from Backend.Infrastructure.persistence.database import init_db
from Backend.Infrastructure.persistence.FileRepository import SQLiteFileRepository
from Backend.Infrastructure.persistence.LocalFileStorage import LocalFileStorage
from Backend.Infrastructure.document.DocumentProcessor import DocumentProcessor
from Backend.Infrastructure.vectorstore.ChromaVectorStoreRepository import ChromaVectorStoreRepository
from Backend.Application.UseCases.ImportFileUseCase import ImportFileUseCase
from Backend.Application.UseCases.DeleteFileUseCase import DeleteFileUseCase
from Backend.Web.Endpoints.FileEndpoint import create_file_blueprint


def create_app() -> Flask:
    app = Flask(__name__)

    # 初始化数据库
    init_db()

    # Infrastructure 实例化
    file_repository = SQLiteFileRepository()
    file_storage = LocalFileStorage(upload_folder="uploads")
    document_processor = DocumentProcessor(chunk_size=1024, chunk_overlap=80)
    vector_store_repository = ChromaVectorStoreRepository(persist_directory="db")

    # Use Cases 组装（依赖注入）
    import_use_case = ImportFileUseCase(
        file_repository=file_repository,
        document_processor=document_processor,
        vector_store_repository=vector_store_repository,
        file_storage=file_storage,
    )
    delete_use_case = DeleteFileUseCase(
        file_repository=file_repository,
        vector_store_repository=vector_store_repository,
        file_storage=file_storage,
    )

    # 注册 Blueprint
    file_bp = create_file_blueprint(import_use_case, delete_use_case, file_repository)
    app.register_blueprint(file_bp)

    return app
