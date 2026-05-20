import pytest

from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.UseCases.ImportWorkOrderUseCase import ImportWorkOrderUseCase
from Backend.Application.UseCases.WorkOrderUseCase import WorkOrderUseCase
from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus
from Backend.Domain.Entities.triple import Triple
from Backend.Domain.Entities.work_order import WorkOrder


class _InMemoryWorkOrderRepository:
    def __init__(self) -> None:
        self._items: dict[str, WorkOrder] = {}

    def save(self, work_order: WorkOrder) -> None:
        if any(item.order_no == work_order.order_no for item in self._items.values()):
            raise ValueError(f"Work order already exists: {work_order.order_no}")
        self._items[work_order.id] = work_order

    def save_many(self, work_orders: list[WorkOrder]) -> None:
        for work_order in work_orders:
            self.save(work_order)

    def get_by_id(self, work_order_id: str) -> WorkOrder | None:
        return self._items.get(work_order_id)

    def get_by_order_no(self, order_no: str) -> WorkOrder | None:
        for item in self._items.values():
            if item.order_no == order_no:
                return item
        return None

    def get_all(self, device_name=None, fault_category=None, status=None) -> list[WorkOrder]:
        items = list(self._items.values())
        if device_name:
            items = [item for item in items if item.device_name == device_name]
        if fault_category:
            items = [item for item in items if item.fault_category == fault_category]
        if status:
            items = [item for item in items if item.status == status]
        return items

    def update(self, work_order: WorkOrder) -> None:
        if work_order.id not in self._items:
            raise ValueError(f"Work order not found: {work_order.id}")
        for existing in self._items.values():
            if existing.id != work_order.id and existing.order_no == work_order.order_no:
                raise ValueError(f"Work order already exists: {work_order.order_no}")
        self._items[work_order.id] = work_order

    def update_status(self, work_order_id: str, status: WorkOrderStatus, processing_error: str = "") -> None:
        item = self._items[work_order_id]
        item.status = status
        item.processing_error = processing_error

    def delete(self, work_order_id: str) -> None:
        self._items.pop(work_order_id, None)

    def get_device_stats(self, device_name: str) -> dict:
        items = [item for item in self._items.values() if item.device_name == device_name]
        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for item in items:
            by_status[item.status.value] = by_status.get(item.status.value, 0) + 1
            if item.fault_category:
                by_category[item.fault_category] = by_category.get(item.fault_category, 0) + 1
            if item.severity:
                by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
        return {
            "device_name": device_name,
            "total": len(items),
            "by_status": by_status,
            "by_category": by_category,
            "by_severity": by_severity,
        }


class _FakeVectorStore(IVectorStoreRepository):
    def __init__(self) -> None:
        self.documents: list[tuple[str, list]] = []
        self.deleted_document_ids: list[str] = []
        self.entities: list[tuple[str, str, str]] = []
        self.relations: list[tuple[str, str, str, str]] = []
        self.deleted_entity_sources: list[str] = []
        self.deleted_relation_sources: list[str] = []

    def add_documents(self, file_name: str, documents: list) -> None:
        self.documents.append((file_name, documents))

    def delete_by_file_name(self, file_name: str) -> None:
        self.deleted_document_ids.append(file_name)

    def search(self, query: str, k: int = 5, score_threshold: float = 0.1) -> list[dict]:
        return []

    def add_entity(self, name: str, entity_type: str, source_file: str = "") -> None:
        self.entities.append((name, entity_type, source_file))

    def search_entities(self, query: str, top_k: int = 20, score_threshold: float = 0.85) -> list[dict]:
        return []

    def delete_entities_by_file(self, file_name: str) -> None:
        self.deleted_entity_sources.append(file_name)

    def add_relation(self, head: str, relation: str, tail: str, source_file: str = "") -> None:
        self.relations.append((head, relation, tail, source_file))

    def search_relations(self, query: str, top_k: int = 20, score_threshold: float = 0.5) -> list[dict]:
        return []

    def search_by_sources(self, source_keys: list[dict], query: str, k: int = 15) -> list[dict]:
        return []

    def delete_relations_by_file(self, file_name: str) -> None:
        self.deleted_relation_sources.append(file_name)


class _FakeGraphRepository:
    def __init__(self) -> None:
        self._triples: list[Triple] = []
        self.removed_sources: list[str] = []
        self.saved_count = 0

    def load(self) -> None:
        return None

    def save(self) -> None:
        self.saved_count += 1

    def add_triples(self, triples: list[Triple]) -> None:
        self._triples.extend(triples)

    def remove_by_file(self, file_name: str) -> None:
        self.removed_sources.append(file_name)
        self._triples = [triple for triple in self._triples if triple.source_file != file_name]

    def expand_subgraph(self, seed_entities: list[str], hops: int = 2) -> list[dict]:
        return []

    def node_count(self) -> int:
        names = {triple.head for triple in self._triples} | {triple.tail for triple in self._triples}
        return len(names)

    def edge_count(self) -> int:
        return len(self._triples)


class _FakeParser:
    def __init__(self, work_orders=None, text_work_order=None) -> None:
        self._work_orders = work_orders or []
        self._text_work_order = text_work_order

    def parse_upload(self, uploaded_file, filename: str):
        return self._work_orders, []

    def parse_text(self, text: str, source_file: str = "manual_text.txt") -> WorkOrder:
        if self._text_work_order is not None:
            self._text_work_order.source_file = source_file
            self._text_work_order.raw_text = text
            return self._text_work_order
        return WorkOrder(
            order_no="WO-TEXT-001",
            device_name="泵站A",
            source_file=source_file,
            raw_text=text,
        )


class _FakeTripleExtractor:
    def extract(self, chunk_text: str, source_file: str = "", source_chunk_id: str = "") -> list[Triple]:
        return [
            Triple(
                head="高温报警",
                head_type="ERROR_CODE",
                relation="DIAGNOSES",
                tail="温度过高",
                tail_type="FAULT_MODE",
                source_file=source_file,
                source_chunk_id=source_chunk_id,
            )
        ]


def test_work_order_use_case_supports_crud_and_stats():
    repo = _InMemoryWorkOrderRepository()
    vector_store = _FakeVectorStore()
    graph_repo = _FakeGraphRepository()
    use_case = WorkOrderUseCase(repo, vector_store, graph_repo)

    created = use_case.create(
        {
            "order_no": "WO-001",
            "device_name": "主泵A",
            "fault_phenomenon": "泵体泄漏",
            "fault_category": "机械",
            "severity": "一般",
        }
    )

    assert created.status == WorkOrderStatus.PENDING
    assert use_case.get_by_id(created.id).order_no == "WO-001"
    assert len(use_case.get_all(device_name="主泵A")) == 1

    updated = use_case.update(
        created.id,
        {
            "fault_phenomenon": "泵体严重泄漏",
            "solution": "更换密封圈",
            "severity": "严重",
        },
    )
    assert updated.fault_phenomenon == "泵体严重泄漏"
    assert updated.solution == "更换密封圈"
    assert updated.status == WorkOrderStatus.PENDING

    stats = use_case.get_device_stats("主泵A")
    assert stats["total"] == 1
    assert stats["by_category"]["机械"] == 1

    use_case.delete(created.id)
    assert repo.get_by_id(created.id) is None
    assert vector_store.deleted_document_ids == [created.id]
    assert graph_repo.removed_sources == [WorkOrderUseCase.graph_source(created.id)]


def test_import_work_order_use_case_processes_vectors_and_graph():
    repo = _InMemoryWorkOrderRepository()
    vector_store = _FakeVectorStore()
    graph_repo = _FakeGraphRepository()
    parser = _FakeParser(
        text_work_order=WorkOrder(
            order_no="WO-100",
            device_name="压缩机B",
            fault_phenomenon="温度过高",
            fault_cause="冷却不足",
            solution="清理散热器",
            severity="严重",
        )
    )
    use_case = ImportWorkOrderUseCase(
        work_order_repository=repo,
        parser=parser,
        vector_store_repository=vector_store,
        triple_extractor=_FakeTripleExtractor(),
        graph_repository=graph_repo,
    )
    use_case.process_async = use_case._process_batch

    result = use_case.import_from_text("压缩机B发生高温报警，现场清理散热器后恢复。", source_file="manual.txt")

    assert result["imported_count"] == 1
    work_order = repo.get_by_id(result["ids"][0])
    assert work_order is not None
    assert work_order.status == WorkOrderStatus.LINKED
    assert vector_store.documents[0][0] == work_order.id
    assert any(relation[1] == "HAS_FAULT" for relation in vector_store.relations)
    assert any(relation[1] == "RECORDED_IN" for relation in vector_store.relations)
    assert graph_repo.saved_count == 1
    assert graph_repo.edge_count() >= 4
