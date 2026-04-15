#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试中文文档压缩和工业领域词汇优化的效果
"""

from Backend.Application.ContextManagement.Algorithms import (
    QueryAwareCompressionAlgorithm,
    HistoryTieringAlgorithm,
)


def test_compression_chinese():
    """测试中文文档压缩"""
    print("=" * 80)
    print("【测试1】中文文档压缩（工业领域）")
    print("=" * 80)

    algo = QueryAwareCompressionAlgorithm()

    query = "故障现象排查解决方案"
    
    document = {
        "page_content": """
        系统故障现象通常表现为页面无响应和数据加载缓慢。
        下面介绍故障排查步骤。
        第一步检查系统资源占用，查看CPU和内存使用率是否超过阈值。
        第二步查看错误日志文件，寻找异常堆栈信息。
        第三步执行诊断工具进行深层分析。
        如果问题依然存在，联系技术支持获取帮助。
        解决方案包括清理缓存、重启服务、更新驱动程序等。
        故障树分析显示根本原因可能在于内存泄漏或磁盘空间不足。
        本文档还包含许多技术细节但不相关的内容，如网络协议、DNS配置等。
        这些技术细节对解决问题帮助不大。
        """,
        "score": 0.95,
    }

    # 测试压缩效果
    compressed = algo.compress_documents([document], query, keep_rate=1.0, min_chars=200)
    
    print(f"\n【输入查询】: {query}")
    print(f"\n【原始文档长度】: {len(document['page_content'])} 字符")
    print(f"\n【原始文档内容】:\n{document['page_content']}")
    
    if compressed:
        compressed_text = compressed[0]["page_content"]
        print(f"\n【压缩后长度】: {len(compressed_text)} 字符")
        print(f"\n【压缩后内容】:\n{compressed_text}")
        print(f"\n✅ 压缩率: {100 * len(compressed_text) / len(document['page_content']):.1f}%")
    else:
        print("\n❌ 压缩失败")


def test_history_tiering():
    """测试历史分层和工业词汇优化"""
    print("\n" + "=" * 80)
    print("【测试2】对话历史分层（工业领域关键词优先）")
    print("=" * 80)

    algo = HistoryTieringAlgorithm()

    # 模拟对话轮次
    rounds = [
        {"question": "今天天气怎么样？", "answer": "天气不错", "prompt": "", "created_at": "2025-01-01"},
        {"question": "推荐一个餐厅", "answer": "可以试试意大利餐厅", "prompt": "", "created_at": "2025-01-02"},
        {"question": "系统报错怎么办？", "answer": "查看日志文件", "prompt": "", "created_at": "2025-01-03"},
        {"question": "故障现象是什么？", "answer": "页面无响应，内存占用过高", "prompt": "", "created_at": "2025-01-04"},
        {"question": "如何排查根本原因？", "answer": "使用故障树分析和性能指标检查", "prompt": "", "created_at": "2025-01-05"},
        {"question": "解决方案有哪些？", "answer": "清理缓存、重启服务、升级驱动", "prompt": "", "created_at": "2025-01-06"},
        {"question": "下载什么软件？", "answer": "推荐用Chrome或Firefox", "prompt": "", "created_at": "2025-01-07"},
        {"question": "故障诊断工具怎么用？", "answer": "运行工具后查看生成的报告", "prompt": "", "created_at": "2025-01-08"},
        {"question": "还有其他问题吗？", "answer": "可以", "prompt": "", "created_at": "2025-01-09"},
        {"question": "显示屏黑屏怎么办？", "answer": "尝试重启或检查电源连接", "prompt": "", "created_at": "2025-01-10"},
    ]

    result = algo.split(rounds, hot_size=3, warm_size=5)
    
    print(f"\n【对话总数】: {len(rounds)} 轮")
    print(f"【热层轮次】: {len(result.hot_rounds)} 轮（最近3轮，保留原文）")
    print(f"【温层摘要】: 中期5轮摘要（优先保留工业关键词）")
    print(f"【冷层摘要】: 早期轮次摘要（优先保留关键话题）")
    
    print("\n------- 热层内容（原文保留）-------")
    for i, turn in enumerate(result.hot_rounds, 1):
        print(f"轮{i}: Q: {turn.get('question')}")
        print(f"     A: {turn.get('answer')}")
    
    print("\n------- 温层摘要（工业词汇优先）-------")
    print(result.warm_summary)
    
    print("\n------- 冷层摘要（关键话题提取）-------")
    print(result.cold_summary)
    
    print("\n📊 说明:")
    print("   - 热层: 最近的对话保持完整，便于上下文连贯")
    print("   - 温层: 优先保留包含'故障'、'原因'、'解决'等关键词的对话")
    print("   - 冷层: 只保留关键问题标题，极度压缩")


if __name__ == "__main__":
    test_compression_chinese()
    test_history_tiering()
    
    print("\n" + "=" * 80)
    print("✅ 所有测试完成！")
    print("=" * 80)
