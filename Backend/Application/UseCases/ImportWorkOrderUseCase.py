import logging
import threading

from langchain_core.documents import Document

from Backend.Application.Interfaces.IGraphRepository import IGraphRepository
from Backend.Application.Interfaces.ITripleExtractor import ITripleExtractor
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.IWorkOrderRepository import IWorkOrderRepository
from Backend.Application.UseCases.WorkOrderUseCase import WorkOrderUseCase
from Backend.Domain.Common.Enums.GraphEnums import EntityType, RelationType
from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus
from Backend.Domain.Entities.triple import Triple
from Backend.Domain.Entities.work_order import WorkOrder
from Backend.Infrastructure.document.WorkOrderParser import WorkOrderParser

logger = logging.getLogger(__name__)


class ImportWorkOrderUseCase:
    """工单导入与异步处理用例。

    处理链路拆成两段：
    1. 导入阶段：解析输入并落库。
    2. 后台阶段：向量化、三元组抽取、图谱写入。
    """

    def __init__(
        self,
        work_order_repository: IWorkOrderRepository,
        parser: WorkOrderParser,
        vector_store_repository: IVectorStoreRepository,
        triple_extractor: ITripleExtractor | None = None,
        graph_repository: IGraphRepository | None = None,
    ):
        self._repo = work_order_repository
        self._parser = parser
        self._vector_store = vector_store_repository
        self._triple_extractor = triple_extractor
        self._graph_repo = graph_repository

    def import_from_upload(self, uploaded_file, filename: str) -> dict:
        """处理文件上传导入，并异步启动后续处理。"""
        work_orders, parse_errors = self._parser.parse_upload(uploaded_file, filename)
        imported_ids, save_errors = self._save_work_orders(work_orders)
        self.process_async(imported_ids)
        return {
            "message": f"Imported {len(imported_ids)} work orders",
            "imported_count": len(imported_ids),
            "skipped_count": len(parse_errors) + len(save_errors),
            "ids": imported_ids,
            "errors": parse_errors + save_errors,
        }

    def import_from_text(self, text: str, source_file: str = "manual_text.txt") -> dict:
        """处理自由文本导入，并异步启动后续处理。"""
        work_order = self._parser.parse_text(text, source_file=source_file)
        imported_ids, save_errors = self._save_work_orders([work_order])
        self.process_async(imported_ids)
        return {
            "message": f"Imported {len(imported_ids)} work orders",
            "imported_count": len(imported_ids),
            "skipped_count": len(save_errors),
            "ids": imported_ids,
            "errors": save_errors,
        }

    def process_async(self, work_order_ids: list[str]) -> None:
        """以后台线程处理工单，保证 HTTP 请求快速返回。"""
        if not work_order_ids:
            return

        thread = threading.Thread(
            target=self._process_batch,
            args=(work_order_ids,),
            daemon=True,
        )
        thread.start()

    def _save_work_orders(self, work_orders: list[WorkOrder]) -> tuple[list[str], list[dict]]:
        """逐条保存工单，并收集重复编号等业务错误。"""
        imported_ids: list[str] = []
        errors: list[dict] = []
        for work_order in work_orders:
            try:
                self._repo.save(work_order)
                imported_ids.append(work_order.id)
            except ValueError as exc:
                errors.append({
                    "order_no": work_order.order_no,
                    "error": str(exc),
                })
        return imported_ids, errors

    def _process_batch(self, work_order_ids: list[str]) -> None:
        """串行处理一批工单，便于控制图谱写入顺序。"""
        for work_order_id in work_order_ids:
            self._process_work_order(work_order_id)

    def _process_work_order(self, work_order_id: str) -> None:
        """处理单条工单的向量化与图谱写入。"""
        work_order = self._repo.get_by_id(work_order_id)
        if work_order is None:
            logger.warning("Work order disappeared before processing: %s", work_order_id)
            return

        try:
            # 第一阶段：把工单字段转为统一文档并写入工单专属 collection。
            document = Document(
                page_content=work_order.to_embedding_text(),
                metadata={
                    "work_order_id": work_order.id,
                    "order_no": work_order.order_no,
                    "device_name": work_order.device_name,
                    "source_file": work_order.source_file,
                    "status": work_order.status.value,
                },
            )
            self._vector_store.delete_by_file_name(work_order.id)
            self._vector_store.add_documents(work_order.id, [document])
            self._repo.update_status(work_order.id, WorkOrderStatus.PARSED)
        except Exception as exc:
            logger.exception("Failed to vectorize work order: %s", work_order.id)
            self._repo.update_status(work_order.id, WorkOrderStatus.PENDING, str(exc))
            return

        # 没有图谱仓储时，阶段一至少保证工单已可检索。
        if self._graph_repo is None:
            return

        graph_source = WorkOrderUseCase.graph_source(work_order.id)
        try:
            # 第二阶段前先清理旧的图谱关联，避免更新工单后产生重复边。
            self._vector_store.delete_entities_by_file(graph_source)
            self._vector_store.delete_relations_by_file(graph_source)
            self._graph_repo.remove_by_file(graph_source)

            triples = self._build_structured_triples(work_order)
            if self._triple_extractor is not None:
                # 在规则三元组基础上，再叠加 LLM 抽取到的补充关系。
                extracted = self._triple_extractor.extract(
                    work_order.to_embedding_text(),
                    source_file=graph_source,
                    source_chunk_id=work_order.id,
                )
                triples = self._deduplicate_triples(triples + extracted)

            if triples:
                # 先写入实体/关系向量，再持久化图谱，保证 GraphRAG 两侧都能命中。
                seen_entities = set()
                for triple in triples:
                    if triple.head not in seen_entities:
                        self._vector_store.add_entity(triple.head, triple.head_type, source_file=graph_source)
                        seen_entities.add(triple.head)
                    if triple.tail not in seen_entities:
                        self._vector_store.add_entity(triple.tail, triple.tail_type, source_file=graph_source)
                        seen_entities.add(triple.tail)
                    self._vector_store.add_relation(
                        triple.head,
                        triple.relation,
                        triple.tail,
                        source_file=graph_source,
                    )

                self._graph_repo.add_triples(triples)
                self._graph_repo.save()

            self._repo.update_status(work_order.id, WorkOrderStatus.LINKED)
        except Exception as exc:
            logger.exception("Failed to build graph for work order: %s", work_order.id)
            self._repo.update_status(work_order.id, WorkOrderStatus.PARSED, str(exc))

    def _build_structured_triples(self, work_order: WorkOrder) -> list[Triple]:
        """从结构化工单字段直接构造核心三元组。"""
        graph_source = WorkOrderUseCase.graph_source(work_order.id)
        work_order_node = f"工单:{work_order.order_no}"
        fault_node = (work_order.fault_phenomenon or "").strip()
        triples: list[Triple] = []

        # 设备 -> 故障模式
        if work_order.device_name and fault_node:
            triples.append(Triple(
                head=work_order.device_name,
                head_type=EntityType.DEVICE.value,
                relation=RelationType.HAS_FAULT.value,
                tail=fault_node,
                tail_type=EntityType.FAULT_MODE.value,
                source_file=graph_source,
                source_chunk_id=work_order.id,
            ))

        # 根因 -> 故障模式
        if work_order.fault_cause and fault_node:
            triples.append(Triple(
                head=work_order.fault_cause,
                head_type=EntityType.CAUSE.value,
                relation=RelationType.ROOT_CAUSE_OF.value,
                tail=fault_node,
                tail_type=EntityType.FAULT_MODE.value,
                source_file=graph_source,
                source_chunk_id=work_order.id,
            ))

        # 故障模式 -> 处置措施
        if fault_node and work_order.solution:
            triples.append(Triple(
                head=fault_node,
                head_type=EntityType.FAULT_MODE.value,
                relation=RelationType.TREATED_BY.value,
                tail=work_order.solution,
                tail_type=EntityType.SOLUTION.value,
                source_file=graph_source,
                source_chunk_id=work_order.id,
            ))

        # 故障模式 -> 工单来源
        if fault_node:
            triples.append(Triple(
                head=fault_node,
                head_type=EntityType.FAULT_MODE.value,
                relation=RelationType.RECORDED_IN.value,
                tail=work_order_node,
                tail_type=EntityType.WORK_ORDER.value,
                source_file=graph_source,
                source_chunk_id=work_order.id,
            ))

        return self._deduplicate_triples(triples)

    @staticmethod
    def _deduplicate_triples(triples: list[Triple]) -> list[Triple]:
        """按主谓宾和来源去重，避免重复写入图谱。"""
        deduplicated: list[Triple] = []
        seen = set()
        for triple in triples:
            key = (
                triple.head,
                triple.head_type,
                triple.relation,
                triple.tail,
                triple.tail_type,
                triple.source_file,
            )
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(triple)
        return deduplicated