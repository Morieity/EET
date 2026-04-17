"""T028: 测试 WorkOrderUseCase 新增方法。"""
import os
import sys
import uuid
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Backend.Domain.Entities.conversation import Conversation
from Backend.Domain.Entities.work_order import WorkOrder
from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus
from Backend.Application.UseCases.WorkOrderUseCase import WorkOrderUseCase


def _make_work_order(**kwargs):
    defaults = {
        "order_no": "WO-001",
        "device_name": "设备A",
        "fault_phenomenon": "温度过高",
    }
    defaults.update(kwargs)
    return WorkOrder(**defaults)


def _make_use_case():
    wo_repo = MagicMock()
    vs = MagicMock()
    conv_repo = MagicMock()
    ft_repo = MagicMock()
    uc = WorkOrderUseCase(
        work_order_repository=wo_repo,
        vector_store_repository=vs,
        conversation_repository=conv_repo,
        fault_tree_repository=ft_repo,
    )
    return uc, wo_repo, conv_repo, ft_repo


class TestGetConversations:
    def test_returns_conversations(self):
        uc, wo_repo, conv_repo, ft_repo = _make_use_case()
        wid = str(uuid.uuid4())
        conv_repo.get_by_work_order_id.return_value = [
            Conversation(name="对话1", work_order_id=wid),
        ]
        result = uc.get_conversations(wid)
        assert len(result) == 1
        conv_repo.get_by_work_order_id.assert_called_once_with(wid)

    def test_no_conv_repo_returns_empty(self):
        wo_repo = MagicMock()
        vs = MagicMock()
        uc = WorkOrderUseCase(work_order_repository=wo_repo, vector_store_repository=vs)
        assert uc.get_conversations("any") == []


class TestGetFaultTrees:
    def test_returns_trees_via_conversations(self):
        uc, wo_repo, conv_repo, ft_repo = _make_use_case()
        conv = Conversation(name="对话1")
        conv_repo.get_by_work_order_id.return_value = [conv]
        mock_tree = MagicMock()
        ft_repo.get_by_conversation_id.return_value = mock_tree
        result = uc.get_fault_trees("wid")
        assert len(result) == 1
        assert result[0] == mock_tree

    def test_no_trees_returns_empty(self):
        uc, wo_repo, conv_repo, ft_repo = _make_use_case()
        conv_repo.get_by_work_order_id.return_value = [Conversation(name="c")]
        ft_repo.get_by_conversation_id.return_value = None
        result = uc.get_fault_trees("wid")
        assert result == []


class TestLinkFaultTree:
    def test_link_success(self):
        uc, wo_repo, conv_repo, ft_repo = _make_use_case()
        wo = _make_work_order()
        wo_repo.get_by_id.return_value = wo
        wo_repo.link_fault_tree.return_value = True
        tid = str(uuid.uuid4())
        result = uc.link_fault_tree(wo.id, tid)
        assert result.fault_tree_id == tid
        wo_repo.link_fault_tree.assert_called_once_with(wo.id, tid)

    def test_link_not_found(self):
        uc, wo_repo, conv_repo, ft_repo = _make_use_case()
        wo_repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            uc.link_fault_tree("bad-id", "tid")


class TestUnlinkFaultTree:
    def test_unlink_success(self):
        uc, wo_repo, conv_repo, ft_repo = _make_use_case()
        wo = _make_work_order(fault_tree_id="old-tid")
        wo_repo.get_by_id.return_value = wo
        wo_repo.unlink_fault_tree.return_value = True
        result = uc.unlink_fault_tree(wo.id)
        assert result.fault_tree_id is None
        wo_repo.unlink_fault_tree.assert_called_once_with(wo.id)

    def test_unlink_not_found(self):
        uc, wo_repo, conv_repo, ft_repo = _make_use_case()
        wo_repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            uc.unlink_fault_tree("bad-id")
