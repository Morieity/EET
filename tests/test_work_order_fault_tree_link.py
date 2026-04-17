"""T013: 测试 WorkOrder 实体的 fault_tree_id 字段及仓储方法。"""
import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Backend.Infrastructure.persistence.database import init_db
from Backend.Infrastructure.persistence.WorkOrderRepository import SQLiteWorkOrderRepository
from Backend.Domain.Entities.work_order import WorkOrder
from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.sqlite3")
    monkeypatch.setattr("Backend.Infrastructure.persistence.database.DB_PATH", db_path)
    monkeypatch.setattr("Backend.Infrastructure.persistence.WorkOrderRepository.get_connection",
                        lambda: __import__("Backend.Infrastructure.persistence.database", fromlist=["get_connection"]).get_connection())
    init_db()


@pytest.fixture
def repo():
    return SQLiteWorkOrderRepository()


def _make_work_order(**kwargs) -> WorkOrder:
    defaults = {
        "order_no": f"WO-{uuid.uuid4().hex[:8]}",
        "device_name": "设备A",
        "fault_phenomenon": "温度过高",
    }
    defaults.update(kwargs)
    return WorkOrder(**defaults)


class TestWorkOrderEntityFaultTree:
    def test_fault_tree_id_default_none(self):
        wo = _make_work_order()
        assert wo.fault_tree_id is None

    def test_fault_tree_id_set(self):
        tid = str(uuid.uuid4())
        wo = _make_work_order(fault_tree_id=tid)
        assert wo.fault_tree_id == tid

    def test_link_fault_tree(self):
        wo = _make_work_order()
        tid = str(uuid.uuid4())
        wo.link_fault_tree(tid)
        assert wo.fault_tree_id == tid

    def test_unlink_fault_tree(self):
        wo = _make_work_order(fault_tree_id=str(uuid.uuid4()))
        wo.unlink_fault_tree()
        assert wo.fault_tree_id is None

    def test_to_dict_includes_fault_tree_id(self):
        tid = str(uuid.uuid4())
        wo = _make_work_order(fault_tree_id=tid)
        d = wo.to_dict()
        assert d["fault_tree_id"] == tid

    def test_from_dict_reads_fault_tree_id(self):
        tid = str(uuid.uuid4())
        wo = _make_work_order(fault_tree_id=tid)
        d = wo.to_dict()
        restored = WorkOrder.from_dict(d)
        assert restored.fault_tree_id == tid

    def test_from_dict_fault_tree_id_null(self):
        wo = _make_work_order()
        d = wo.to_dict()
        restored = WorkOrder.from_dict(d)
        assert restored.fault_tree_id is None


class TestWorkOrderRepoFaultTree:
    def test_save_and_get_with_fault_tree_id(self, repo):
        tid = str(uuid.uuid4())
        wo = _make_work_order(fault_tree_id=tid)
        repo.save(wo)
        loaded = repo.get_by_id(wo.id)
        assert loaded is not None
        assert loaded.fault_tree_id == tid

    def test_save_without_fault_tree_id(self, repo):
        wo = _make_work_order()
        repo.save(wo)
        loaded = repo.get_by_id(wo.id)
        assert loaded is not None
        assert loaded.fault_tree_id is None

    def test_link_fault_tree(self, repo):
        wo = _make_work_order()
        repo.save(wo)
        tid = str(uuid.uuid4())
        result = repo.link_fault_tree(wo.id, tid)
        assert result is True
        loaded = repo.get_by_id(wo.id)
        assert loaded.fault_tree_id == tid

    def test_unlink_fault_tree(self, repo):
        tid = str(uuid.uuid4())
        wo = _make_work_order(fault_tree_id=tid)
        repo.save(wo)
        result = repo.unlink_fault_tree(wo.id)
        assert result is True
        loaded = repo.get_by_id(wo.id)
        assert loaded.fault_tree_id is None

    def test_link_fault_tree_not_found(self, repo):
        result = repo.link_fault_tree(str(uuid.uuid4()), str(uuid.uuid4()))
        assert result is False

    def test_get_by_device_name(self, repo):
        repo.save(_make_work_order(device_name="设备B"))
        repo.save(_make_work_order(device_name="设备B"))
        repo.save(_make_work_order(device_name="设备C"))
        result = repo.get_by_device_name("设备B")
        assert len(result) == 2
        assert all(wo.device_name == "设备B" for wo in result)

    def test_get_by_device_name_empty(self, repo):
        result = repo.get_by_device_name("不存在的设备")
        assert result == []

    def test_existing_work_order_fault_tree_id_null(self, repo):
        wo = _make_work_order()
        repo.save(wo)
        loaded = repo.get_by_id(wo.id)
        assert loaded.fault_tree_id is None
