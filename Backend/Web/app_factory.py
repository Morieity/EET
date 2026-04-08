from flask import Flask
from Backend.Infrastructure.persistence.database import init_db
from Backend.Infrastructure.persistence.FileRepository import SQLiteFileRepository
from Backend.Infrastructure.persistence.LocalFileStorage import LocalFileStorage
from Backend.Infrastructure.persistence.ConversationRepository import SQLiteConversationRepository
from Backend.Infrastructure.persistence.FaultTreeRepository import SQLiteFaultTreeRepository
from Backend.Infrastructure.document.DocumentProcessorPro import DocumentProcessorPro
from Backend.Infrastructure.vectorstore.ChromaVectorStoreRepository import ChromaVectorStoreRepository
from Backend.Infrastructure.llm.LLMService import LLMService
from Backend.Application.UseCases.ImportFileUseCase import ImportFileUseCase
from Backend.Application.UseCases.DeleteFileUseCase import DeleteFileUseCase
from Backend.Application.UseCases.ChatUseCase import ChatUseCase
from Backend.Application.UseCases.DeleteConversationUseCase import DeleteConversationUseCase
from Backend.Application.UseCases.FaultTreeUseCase import FaultTreeUseCase
from Backend.Application.Skills.FaultTreeSkill import FaultTreeSkill
from Backend.Web.Endpoints.FileEndpoint import create_file_blueprint
from Backend.Web.Endpoints.ChatEndpoint import create_chat_blueprint
from Backend.Web.Endpoints.FaultTreeEndpoint import create_fault_tree_blueprint


def create_app() -> Flask:
    app = Flask(__name__)

    # 初始化数据库
    init_db()

    # Infrastructure 实例化
    file_repository = SQLiteFileRepository()
    file_storage = LocalFileStorage(upload_folder="uploads")
    document_processor = DocumentProcessorPro(chunk_size=1024, chunk_overlap=200)
    vector_store_repository = ChromaVectorStoreRepository(persist_directory="db")
    conversation_repository = SQLiteConversationRepository()
    fault_tree_repository = SQLiteFaultTreeRepository()
    llm_service = LLMService()

    # Skills 组装
    fault_tree_skill = FaultTreeSkill(fault_tree_repository=fault_tree_repository)

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
    chat_use_case = ChatUseCase(
        conversation_repository=conversation_repository,
        vector_store_repository=vector_store_repository,
        llm_service=llm_service,
        fault_tree_skill=fault_tree_skill,
    )
    delete_conversation_use_case = DeleteConversationUseCase(
        conversation_repository=conversation_repository,
        fault_tree_repository=fault_tree_repository,
    )
    fault_tree_use_case = FaultTreeUseCase(
        fault_tree_repository=fault_tree_repository,
    )

    # 注册 Blueprint
    file_bp = create_file_blueprint(import_use_case, delete_use_case, file_repository)
    app.register_blueprint(file_bp)

    chat_bp = create_chat_blueprint(chat_use_case, delete_conversation_use_case, conversation_repository)
    app.register_blueprint(chat_bp)

    fault_tree_bp = create_fault_tree_blueprint(fault_tree_use_case)
    app.register_blueprint(fault_tree_bp)

    return app
