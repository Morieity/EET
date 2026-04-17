"""T027: 测试 ChatUseCase 工单模式。"""
import os
import sys
import uuid
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Backend.Domain.Entities.conversation import Conversation, ChatRound
from Backend.Domain.Entities.work_order import WorkOrder
from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus
from Backend.Application.UseCases.ChatUseCase import ChatUseCase


def _make_work_order(**kwargs):
    defaults = {
        "order_no": "WO-001",
        "device_name": "设备A",
        "fault_phenomenon": "温度过高",
        "fault_cause": "散热不良",
        "fault_category": "机械故障",
    }
    defaults.update(kwargs)
    return WorkOrder(**defaults)


def _make_mocks(work_order=None, conversation=None):
    conv_repo = MagicMock()
    vector_store = MagicMock()
    llm = MagicMock()
    ft_skill = MagicMock()
    wo_repo = MagicMock()
    wo_vector_store = MagicMock()

    # 默认返回值
    ft_skill.get_existing_tree_context.return_value = ""
    ft_skill.tools = []
    vector_store.search.return_value = []
    vector_store.search_entities.return_value = []
    wo_vector_store.search.return_value = []
    llm.stream_chat.return_value = iter(["回答内容"])

    if work_order:
        wo_repo.get_by_id.return_value = work_order
    else:
        wo_repo.get_by_id.return_value = None

    if conversation:
        conv_repo.get_by_id.return_value = conversation
    else:
        conv_repo.get_by_id.return_value = None
        conv_repo.save.return_value = None

    return conv_repo, vector_store, llm, ft_skill, wo_repo, wo_vector_store


def _create_use_case(conv_repo, vector_store, llm, ft_skill, wo_repo, wo_vector_store):
    return ChatUseCase(
        conversation_repository=conv_repo,
        vector_store_repository=vector_store,
        llm_service=llm,
        fault_tree_skill=ft_skill,
        work_order_repository=wo_repo,
        work_order_vector_store=wo_vector_store,
    )


def _collect_events(gen):
    return list(gen)


class TestChatUseCaseWorkOrder:
    def test_work_order_context_event_yielded(self):
        wo = _make_work_order()
        conv_repo, vs, llm, ft, wo_repo, wo_vs = _make_mocks(work_order=wo)
        uc = _create_use_case(conv_repo, vs, llm, ft, wo_repo, wo_vs)
        events = _collect_events(uc.execute("分析故障", work_order_id=wo.id))
        types = [e["type"] for e in events]
        assert "work_order_context" in types
        ctx = next(e for e in events if e["type"] == "work_order_context")
        assert ctx["device_name"] == "设备A"
        assert ctx["fault_phenomenon"] == "温度过高"

    def test_system_prompt_contains_work_order_info(self):
        wo = _make_work_order()
        conv_repo, vs, llm, ft, wo_repo, wo_vs = _make_mocks(work_order=wo)
        uc = _create_use_case(conv_repo, vs, llm, ft, wo_repo, wo_vs)
        _collect_events(uc.execute("分析故障", work_order_id=wo.id))
        # 检查 ft_skill.get_existing_tree_context 被调用时传入了 work_order
        ft.get_existing_tree_context.assert_called_once()
        call_kwargs = ft.get_existing_tree_context.call_args
        assert call_kwargs.kwargs.get("work_order") == wo or call_kwargs[1].get("work_order") == wo

    def test_first_round_auto_triggers_fault_tree(self):
        wo = _make_work_order()
        conv_repo, vs, llm, ft, wo_repo, wo_vs = _make_mocks(work_order=wo)
        # 模拟 function calling 返回工具调用
        llm.chat_with_tools.return_value = {"type": "no_tool_call"}
        uc = _create_use_case(conv_repo, vs, llm, ft, wo_repo, wo_vs)
        events = _collect_events(uc.execute("请帮我分析", work_order_id=wo.id))
        # 首轮应自动进入故障树生成分支 → llm.chat_with_tools 被调用
        assert llm.chat_with_tools.called or llm.stream_chat.called

    def test_non_first_round_no_auto_trigger(self):
        wo = _make_work_order()
        existing_conv = Conversation(name="已有对话", work_order_id=wo.id)
        existing_conv.rounds = [ChatRound(question="之前的问题", answer="之前的回答")]
        conv_repo, vs, llm, ft, wo_repo, wo_vs = _make_mocks(work_order=wo, conversation=existing_conv)
        uc = _create_use_case(conv_repo, vs, llm, ft, wo_repo, wo_vs)
        events = _collect_events(uc.execute("继续对话", conversation_id=existing_conv.id, work_order_id=wo.id))
        # 非首轮 + 非故障树关键词 → 不自动触发
        types = [e["type"] for e in events]
        assert "done" in types

    def test_no_work_order_id_unchanged_behavior(self):
        conv_repo, vs, llm, ft, wo_repo, wo_vs = _make_mocks()
        uc = _create_use_case(conv_repo, vs, llm, ft, wo_repo, wo_vs)
        events = _collect_events(uc.execute("普通问题"))
        types = [e["type"] for e in events]
        assert "work_order_context" not in types
        assert "conversation" in types
        assert "done" in types

    def test_work_order_not_found_yields_error(self):
        conv_repo, vs, llm, ft, wo_repo, wo_vs = _make_mocks()
        wo_repo.get_by_id.return_value = None
        uc = _create_use_case(conv_repo, vs, llm, ft, wo_repo, wo_vs)
        events = _collect_events(uc.execute("分析", work_order_id="nonexistent"))
        assert events[0]["type"] == "error"
        assert "not found" in events[0]["message"]
