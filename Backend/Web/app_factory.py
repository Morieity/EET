import logging
import os

from flask import Flask
from Backend.Infrastructure.persistence.database import init_db
from Backend.Infrastructure.persistence.FileRepository import SQLiteFileRepository
from Backend.Infrastructure.persistence.LocalFileStorage import LocalFileStorage
from Backend.Infrastructure.persistence.ConversationRepository import SQLiteConversationRepository
from Backend.Infrastructure.persistence.FaultTreeRepository import SQLiteFaultTreeRepository
from Backend.Infrastructure.persistence.WorkOrderRepository import SQLiteWorkOrderRepository
from Backend.Infrastructure.document.DocumentProcessorPro import DocumentProcessorPro
from Backend.Infrastructure.document.WorkOrderParser import WorkOrderParser
from Backend.Infrastructure.vectorstore.ChromaVectorStoreRepository import ChromaVectorStoreRepository
from Backend.Infrastructure.llm.LLMService import LLMService
from Backend.Infrastructure.llm.TripleExtractor import TripleExtractor
from Backend.Infrastructure.graphstore.NetworkXGraphRepository import NetworkXGraphRepository
from Backend.Infrastructure.logging.ContextModuleLogger import NullLogger, PythonLoggerAdapter
from Backend.Application.ContextManagement.ContextManager import DefaultContextManager
from Backend.Application.UseCases.ImportFileUseCase import ImportFileUseCase
from Backend.Application.UseCases.DeleteFileUseCase import DeleteFileUseCase
from Backend.Application.UseCases.ChatUseCase import ChatUseCase
from Backend.Application.UseCases.DeleteConversationUseCase import DeleteConversationUseCase
from Backend.Application.UseCases.FaultTreeUseCase import FaultTreeUseCase
from Backend.Application.UseCases.ExpertLearningUseCase import ExpertLearningUseCase
from Backend.Application.UseCases.ImportWorkOrderUseCase import ImportWorkOrderUseCase
from Backend.Application.UseCases.WorkOrderUseCase import WorkOrderUseCase
from Backend.Application.Skills.FaultTreeSkill import FaultTreeSkill
from Backend.Web.Endpoints.FileEndpoint import create_file_blueprint
from Backend.Web.Endpoints.ChatEndpoint import create_chat_blueprint
from Backend.Web.Endpoints.FaultTreeEndpoint import create_fault_tree_blueprint
from Backend.Web.Endpoints.WorkOrderEndpoint import create_work_order_blueprint


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def create_app() -> Flask:
    app = Flask(__name__)

    # 初始化数据库
    init_db()

    # Infrastructure 实例化
    file_repository = SQLiteFileRepository()
    file_storage = LocalFileStorage(upload_folder="uploads")
    document_processor = DocumentProcessorPro(chunk_size=1024, chunk_overlap=200)
    vector_store_repository = ChromaVectorStoreRepository(persist_directory="db")
    # 工单使用独立 collection，避免与通用文档检索的 rag_docs 混用。
    work_order_vector_store = ChromaVectorStoreRepository(
        persist_directory="db",
        collection_name="work_orders",
    )
    conversation_repository = SQLiteConversationRepository()
    fault_tree_repository = SQLiteFaultTreeRepository()
    work_order_repository = SQLiteWorkOrderRepository()
    llm_service = LLMService()

    # GraphRAG 组件
    graph_repository = NetworkXGraphRepository(graph_path="db/knowledge_graph.json")
    triple_extractor = TripleExtractor(llm_service=llm_service)
    # 工单解析器负责 CSV/Excel/文本三类输入统一转实体。
    work_order_parser = WorkOrderParser(llm_service=llm_service)

    # Skills 组装
    fault_tree_skill = FaultTreeSkill(
        fault_tree_repository=fault_tree_repository,
        conversation_repository=conversation_repository,
    )

    # 上下文模块日志开关由 DI 统一控制。
    context_log_enabled = _to_bool(os.getenv("CONTEXT_MODULE_LOG_ENABLED"), default=False)
    context_logger = (
        PythonLoggerAdapter(logging.getLogger("Backend.ContextManagement"))
        if context_log_enabled
        else NullLogger()
    )
    context_manager = DefaultContextManager(context_logger=context_logger)

    # Use Cases 组装（依赖注入）
    import_use_case = ImportFileUseCase(
        file_repository=file_repository,
        document_processor=document_processor,
        vector_store_repository=vector_store_repository,
        file_storage=file_storage,
        triple_extractor=triple_extractor,
        graph_repository=graph_repository,
    )
    delete_use_case = DeleteFileUseCase(
        file_repository=file_repository,
        vector_store_repository=vector_store_repository,
        file_storage=file_storage,
        graph_repository=graph_repository,
    )
    expert_learning_use_case = ExpertLearningUseCase(
        llm_service=llm_service,
        vector_store_repository=vector_store_repository,
        graph_repository=graph_repository,
        triple_extractor=triple_extractor,
        fault_tree_repository=fault_tree_repository,
        conversation_repository=conversation_repository,
    )
    chat_use_case = ChatUseCase(
        conversation_repository=conversation_repository,
        vector_store_repository=vector_store_repository,
        llm_service=llm_service,
        fault_tree_skill=fault_tree_skill,
        graph_repository=graph_repository,
        context_manager=context_manager,
        expert_learning=expert_learning_use_case,
    )
    delete_conversation_use_case = DeleteConversationUseCase(
        conversation_repository=conversation_repository,
        fault_tree_repository=fault_tree_repository,
    )
    fault_tree_use_case = FaultTreeUseCase(
        fault_tree_repository=fault_tree_repository,
    )
    # 工单链路拆分为“导入处理”和“同步 CRUD”两个用例，职责更清晰。
    import_work_order_use_case = ImportWorkOrderUseCase(
        work_order_repository=work_order_repository,
        parser=work_order_parser,
        vector_store_repository=work_order_vector_store,
        triple_extractor=triple_extractor,
        graph_repository=graph_repository,
    )
    work_order_use_case = WorkOrderUseCase(
        work_order_repository=work_order_repository,
        vector_store_repository=work_order_vector_store,
        graph_repository=graph_repository,
    )

    # 注册 Blueprint
    file_bp = create_file_blueprint(import_use_case, delete_use_case, file_repository)
    app.register_blueprint(file_bp)

    chat_bp = create_chat_blueprint(chat_use_case, delete_conversation_use_case, conversation_repository)
    app.register_blueprint(chat_bp)

    fault_tree_bp = create_fault_tree_blueprint(
        fault_tree_use_case,
        expert_learning_use_case,
    )
    app.register_blueprint(fault_tree_bp)

    work_order_bp = create_work_order_blueprint(
        import_work_order_use_case,
        work_order_use_case,
    )
    # 工单模块作为独立入口注册，不影响现有对话与文件能力。
    app.register_blueprint(work_order_bp)

    return app
