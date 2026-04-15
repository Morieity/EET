from Backend.Application.ContextManagement.ContextManager import DefaultContextManager
from Backend.Application.ContextManagement.ContextManagerTypes import ContextManagerConfig
from Backend.Domain.Entities.conversation import ChatRound


def _round(question: str, answer: str) -> ChatRound:
    return ChatRound(question=question, answer=answer)


def test_prepare_context_filters_dedups_and_builds_user_content() -> None:
    manager = DefaultContextManager()

    rounds = [
        _round("上一次问题", "上一次回答"),
        _round("第二次问题", "第二次回答"),
    ]
    sources = [
        {"file_name": "A.md", "page_content": "轴承磨损导致温升异常", "score": 0.91},
        {"file_name": "A.md", "page_content": "轴承磨损导致温升异常", "score": 0.88},
        {"file_name": "B.md", "page_content": "润滑不足会加速磨损", "score": 0.72},
    ]
    graph_paths = [
        {"from": "轴承", "relation": "导致", "to": "温升", "confidence": 0.92},
        {"from": "轴承", "relation": "关联", "to": "振动", "confidence": 0.20},
    ]

    result = manager.prepare_context(
        question="当前故障的根因是什么？",
        conversation_rounds=rounds,
        seed_names=["轴承"],
        graph_paths=graph_paths,
        sources=sources,
        config=ContextManagerConfig(max_context_tokens=32000, mmr_top_k=5),
    )

    assert len(result.sources) == 2
    assert len(result.graph_paths) == 1
    assert result.sources[0]["score"] >= result.sources[1]["score"]
    assert "Context:" in result.user_content
    assert result.user_content.startswith("当前故障的根因是什么？")


def test_prepare_context_triggers_budget_actions_and_tiered_history() -> None:
    manager = DefaultContextManager()

    rounds = [
        _round(
            "请帮我分析设备反复告警的原因，包含硬件与软件两方面",
            "可能与传感器漂移、风扇异常和阈值配置不当相关，建议先看日志与监控。",
        )
        for _ in range(12)
    ]
    sources = [
        {
            "file_name": "C.md",
            "page_content": "系统发生连续告警，排查步骤包括查看日志、校验阈值、检查传感器和执行器状态。" * 4,
            "score": 0.95,
        },
        {
            "file_name": "D.md",
            "page_content": "故障树分析可用于定位根本原因，建议按模块逐层拆解并验证连接关系。" * 4,
            "score": 0.89,
        },
    ]

    result = manager.prepare_context(
        question="请给出当前告警的排查优先级与根因路径",
        conversation_rounds=rounds,
        seed_names=["告警系统", "传感器"],
        graph_paths=[{"from": "告警系统", "relation": "关联", "to": "传感器", "confidence": 0.8}],
        sources=sources,
        config=ContextManagerConfig(
            max_context_tokens=200,
            max_history_rounds=10,
            mmr_top_k=5,
            max_graph_paths=20,
            history_hot_size=3,
            history_warm_size=7,
        ),
    )

    assert "compress_history_tier2" in result.budget_actions
    assert "compress_vector_docs_keep_50pct" in result.budget_actions
    assert result.history_messages
    assert "[Conversation Memory]" in result.history_messages[0]["content"]
