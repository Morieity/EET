import io

import pytest
from flask import Flask

from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus
from Backend.Domain.Entities.work_order import WorkOrder
from Backend.Web.Endpoints.WorkOrderEndpoint import create_work_order_blueprint


class _StubImportWorkOrderUseCase:
    def __init__(self) -> None:
        self.file_imports: list[str] = []
        self.text_imports: list[tuple[str, str]] = []
        self.process_calls: list[list[str]] = []

    def import_from_upload(self, uploaded_file, filename: str) -> dict:
        self.file_imports.append(filename)
        return {
            "message": "Imported 1 work orders",
            "imported_count": 1,
            "skipped_count": 0,
            "ids": ["wo-imported-1"],
            "errors": [],
        }

    def import_from_text(self, text: str, source_file: str = "manual_text.txt") -> dict:
        self.text_imports.append((text, source_file))
        return {
            "message": "Imported 1 work orders",
            "imported_count": 1,
            "skipped_count": 0,
            "ids": ["wo-text-1"],
            "errors": [],
        }

    def process_async(self, work_order_ids: list[str]) -> None:
        self.process_calls.append(work_order_ids)


class _StubWorkOrderUseCase:
    def __init__(self) -> None:
        self.items = {
            "wo-1": WorkOrder(
                work_order_id="wo-1",
                order_no="WO-001",
                device_name="主泵A",
                fault_phenomenon="泵体泄漏",
                status=WorkOrderStatus.PENDING,
            )
        }

    def create(self, data: dict) -> WorkOrder:
        work_order = WorkOrder.from_dict({
            "id": "wo-2",
            **data,
            "status": WorkOrderStatus.PENDING.value,
        })
        self.items[work_order.id] = work_order
        return work_order

    def get_all(self, device_name=None, fault_category=None, status=None):
        items = list(self.items.values())
        if device_name:
            items = [item for item in items if item.device_name == device_name]
        return items

    def get_device_stats(self, device_name: str) -> dict:
        matched = [item for item in self.items.values() if item.device_name == device_name]
        return {
            "device_name": device_name,
            "total": len(matched),
            "by_status": {WorkOrderStatus.PENDING.value: len(matched)},
            "by_category": {},
            "by_severity": {},
        }

    def get_by_id(self, work_order_id: str):
        return self.items.get(work_order_id)

    def update(self, work_order_id: str, data: dict) -> WorkOrder:
        existing = self.items.get(work_order_id)
        if existing is None:
            raise ValueError(f"Work order not found: {work_order_id}")
        merged = {**existing.to_dict(), **data, "id": work_order_id}
        updated = WorkOrder.from_dict(merged)
        self.items[work_order_id] = updated
        return updated

    def delete(self, work_order_id: str) -> None:
        if work_order_id not in self.items:
            raise ValueError(f"Work order not found: {work_order_id}")
        del self.items[work_order_id]


@pytest.fixture()
def _app_and_stubs():
    import_uc = _StubImportWorkOrderUseCase()
    work_order_uc = _StubWorkOrderUseCase()

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(create_work_order_blueprint(import_uc, work_order_uc))
    return app, import_uc, work_order_uc


@pytest.fixture()
def client(_app_and_stubs):
    app, _, _ = _app_and_stubs
    return app.test_client()


@pytest.fixture()
def import_uc(_app_and_stubs):
    _, import_uc, _ = _app_and_stubs
    return import_uc


@pytest.fixture()
def work_order_uc(_app_and_stubs):
    _, _, work_order_uc = _app_and_stubs
    return work_order_uc


def test_import_work_orders_accepts_json_text(client, import_uc):
    response = client.post(
        "/api/work-orders/import",
        json={"text": "主泵A出现泄漏，需要更换密封圈。", "source_file": "manual.txt"},
    )

    assert response.status_code == 202
    assert response.get_json()["imported_count"] == 1
    assert import_uc.text_imports == [("主泵A出现泄漏，需要更换密封圈。", "manual.txt")]


def test_import_work_orders_accepts_csv_upload(client, import_uc):
    response = client.post(
        "/api/work-orders/import",
        data={"file": (io.BytesIO("order_no,device_name\nWO-002,主泵B\n".encode("utf-8")), "orders.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 202
    assert import_uc.file_imports == ["orders.csv"]


def test_create_update_delete_and_query_work_orders(client, import_uc, work_order_uc):
    create_response = client.post(
        "/api/work-orders",
        json={
            "order_no": "WO-010",
            "device_name": "压缩机C",
            "fault_phenomenon": "异常振动",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.get_json()["id"]
    assert import_uc.process_calls[-1] == [created_id]

    list_response = client.get("/api/work-orders", query_string={"device_name": "压缩机C"})
    assert list_response.status_code == 200
    assert len(list_response.get_json()) == 1

    detail_response = client.get(f"/api/work-orders/{created_id}")
    assert detail_response.status_code == 200
    assert detail_response.get_json()["order_no"] == "WO-010"

    update_response = client.put(
        f"/api/work-orders/{created_id}",
        json={"solution": "校正联轴器"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["solution"] == "校正联轴器"

    stats_response = client.get("/api/work-orders/device/压缩机C/stats")
    assert stats_response.status_code == 200
    assert stats_response.get_json()["total"] == 1

    delete_response = client.delete(f"/api/work-orders/{created_id}")
    assert delete_response.status_code == 200
    assert created_id not in work_order_uc.items


def test_import_work_orders_rejects_unsupported_extension(client):
    response = client.post(
        "/api/work-orders/import",
        data={"file": (io.BytesIO(b"invalid"), "orders.exe")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.get_json()["error"]
