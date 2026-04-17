"""T038: 测试工单驱动的 API 端点。"""
import os
import sys
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask
from Backend.Domain.Entities.conversation import Conversation
from Backend.Domain.Entities.work_order import WorkOrder
from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus
from Backend.Web.Endpoints.WorkOrderEndpoint import create_work_order_blueprint
from Backend.Web.Endpoints.ChatEndpoint import create_chat_blueprint


def _make_work_order(**kwargs):
    defaults = {
        "order_no": "WO-001",
        "device_name": "设备A",
        "fault_phenomenon": "温度过高",
    }
    defaults.update(kwargs)
    return WorkOrder(**defaults)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    import_uc = MagicMock()
    wo_uc = MagicMock()
    chat_uc = MagicMock()

    wo = _make_work_order()
    wo_uc.get_by_id.return_value = wo
    wo_uc.get_all.return_value = [wo]
    wo_uc.get_conversations.return_value = [
        Conversation(name="对话1", work_order_id=wo.id),
    ]
    wo_uc.get_fault_trees.return_value = []
    wo_uc.get_aggregated_counts.return_value = {
        wo.id: {"conversation_count": 1, "fault_tree_count": 0},
    }

    bp = create_work_order_blueprint(import_uc, wo_uc, chat_use_case=chat_uc)
    app.register_blueprint(bp)

    # 存储 mock 引用供测试使用
    app.wo_uc = wo_uc
    app.chat_uc = chat_uc
    app.wo = wo
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestGetWorkOrderConversations:
    def test_returns_conversations(self, client, app):
        resp = client.get(f"/api/work-orders/{app.wo.id}/conversations")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["work_order_id"] == app.wo.id
        assert len(data["conversations"]) == 1

    def test_not_found(self, client, app):
        app.wo_uc.get_by_id.return_value = None
        resp = client.get("/api/work-orders/bad-id/conversations")
        assert resp.status_code == 404


class TestGetWorkOrderFaultTrees:
    def test_returns_trees(self, client, app):
        resp = client.get(f"/api/work-orders/{app.wo.id}/fault-trees")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["work_order_id"] == app.wo.id
        assert data["fault_trees"] == []

    def test_not_found(self, client, app):
        app.wo_uc.get_by_id.return_value = None
        resp = client.get("/api/work-orders/bad-id/fault-trees")
        assert resp.status_code == 404


class TestAnalyzeWorkOrder:
    def test_sse_stream(self, client, app):
        app.chat_uc.execute.return_value = iter([
            {"type": "conversation", "conversation_id": "cid", "name": "test"},
            {"type": "work_order_context", "work_order_id": app.wo.id, "device_name": "设备A", "fault_phenomenon": "温度过高"},
            {"type": "done", "conversation_id": "cid", "answer": "分析完成"},
        ])
        resp = client.post(
            f"/api/work-orders/{app.wo.id}/analyze",
            json={},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type
        data = resp.get_data(as_text=True)
        assert "work_order_context" in data

    def test_not_found(self, client, app):
        app.wo_uc.get_by_id.return_value = None
        resp = client.post("/api/work-orders/bad-id/analyze", json={})
        assert resp.status_code == 404


class TestLinkUnlinkFaultTree:
    def test_link_success(self, client, app):
        tid = str(uuid.uuid4())
        linked_wo = _make_work_order(fault_tree_id=tid)
        app.wo_uc.link_fault_tree.return_value = linked_wo
        resp = client.put(
            f"/api/work-orders/{app.wo.id}/fault-tree",
            json={"fault_tree_id": tid},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["fault_tree_id"] == tid

    def test_link_missing_id(self, client, app):
        resp = client.put(
            f"/api/work-orders/{app.wo.id}/fault-tree",
            json={},
        )
        assert resp.status_code == 400

    def test_unlink_success(self, client, app):
        unlinked_wo = _make_work_order()
        app.wo_uc.unlink_fault_tree.return_value = unlinked_wo
        resp = client.delete(f"/api/work-orders/{app.wo.id}/fault-tree")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["fault_tree_id"] is None


class TestListWorkOrdersAggregated:
    def test_includes_aggregated_fields(self, client, app):
        resp = client.get("/api/work-orders")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert "conversation_count" in data[0]
        assert "fault_tree_count" in data[0]
        assert "fault_tree_id" in data[0]
