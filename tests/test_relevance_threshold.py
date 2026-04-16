"""
相关度阈值探索测试
─────────────────
直接调用 ChromaVectorStoreRepository 的 search_entities / search_relations，
用多种典型问题查看不同阈值下返回的结果数量和分数分布，帮助确定最优阈值。

用法：
  1. 确保 db/ 目录存在且已有向量数据
  2. python -m pytest tests/test_relevance_threshold.py -v -s
"""

import json
import pytest
from Backend.Infrastructure.vectorstore.ChromaVectorStoreRepository import (
    ChromaVectorStoreRepository,
)

# ── 典型查询（覆盖故障码、症状、解决方案等场景）────
QUERIES = [
    "电源故障",
    "9003",
    "过电压",
    "编码器信号故障",
    "通讯故障",
    "电机过载怎么处理",
    "F50518",
    "检查电源和保险丝",
    "硬件故障",
    "温度过高",
]


@pytest.fixture(scope="module")
def repo():
    return ChromaVectorStoreRepository(persist_directory="db")


class TestEntityRelevanceExploration:
    """探索 entity 搜索在不同阈值下的表现"""

    THRESHOLDS = [0.2, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6]

    def test_entity_score_distribution(self, repo: ChromaVectorStoreRepository):
        """打印每个查询的 entity 分数分布"""
        print("\n" + "=" * 80)
        print("ENTITY 搜索分数分布")
        print("=" * 80)
        for q in QUERIES:
            # 用较低阈值取尽可能多的结果
            results = repo.search_entities(query=q, top_k=20, score_threshold=0.1)
            print(f"\n查询: '{q}'  命中: {len(results)} 条")
            for r in results:
                print(f"  name={r.get('name','?'):30s}  type={r.get('type','?'):15s}  score={r.get('_score', '?')}")

    def test_entity_threshold_summary(self, repo: ChromaVectorStoreRepository):
        """统计各阈值下每个查询的命中数"""
        print("\n" + "=" * 80)
        print("ENTITY 各阈值命中数量汇总")
        print("=" * 80)
        header = f"{'查询':20s}" + "".join(f"  ≥{t:<5}" for t in self.THRESHOLDS)
        print(header)
        print("-" * len(header))
        for q in QUERIES:
            raw = repo.search_entities(query=q, top_k=20, score_threshold=0.1)
            counts = []
            for t in self.THRESHOLDS:
                cnt = sum(1 for r in raw if r.get("_score", 0) >= t)
                counts.append(cnt)
            row = f"{q:20s}" + "".join(f"  {c:<6}" for c in counts)
            print(row)


class TestRelationRelevanceExploration:
    """探索 relation 搜索在不同阈值下的表现"""

    THRESHOLDS = [0.2, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6]

    def test_relation_score_distribution(self, repo: ChromaVectorStoreRepository):
        """打印每个查询的 relation 分数分布"""
        print("\n" + "=" * 80)
        print("RELATION 搜索分数分布")
        print("=" * 80)
        for q in QUERIES:
            results = repo.search_relations(query=q, top_k=20, score_threshold=0.1)
            print(f"\n查询: '{q}'  命中: {len(results)} 条")
            for r in results:
                label = f"{r.get('head','?')} --{r.get('relation','?')}--> {r.get('tail','?')}"
                print(f"  {label:60s}  score={r.get('_score', '?')}")

    def test_relation_threshold_summary(self, repo: ChromaVectorStoreRepository):
        """统计各阈值下每个查询的命中数"""
        print("\n" + "=" * 80)
        print("RELATION 各阈值命中数量汇总")
        print("=" * 80)
        header = f"{'查询':20s}" + "".join(f"  ≥{t:<5}" for t in self.THRESHOLDS)
        print(header)
        print("-" * len(header))
        for q in QUERIES:
            raw = repo.search_relations(query=q, top_k=20, score_threshold=0.1)
            counts = []
            for t in self.THRESHOLDS:
                cnt = sum(1 for r in raw if r.get("_score", 0) >= t)
                counts.append(cnt)
            row = f"{q:20s}" + "".join(f"  {c:<6}" for c in counts)
            print(row)
