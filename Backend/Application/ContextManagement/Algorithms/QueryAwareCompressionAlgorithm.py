import math
import re
from collections.abc import Sequence
from typing import Any

from Backend.Application.ContextManagement.ContextTypes import ScoredDocument

try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False


class QueryAwareCompressionAlgorithm:
    """简要算法说明。

        论文来源:
        - LongLLMLingua (arXiv:2310.06839)
        - LLMLingua-2 (arXiv:2403.12968)

        核心原理:
        - 按分数保留文档前部子集（`keep_rate`）。
        - 对保留文档执行确定性的抽取式压缩，优先选择与查询词重叠更高的文本片段。

        参数含义:
        - documents: 输入检索片段，需包含 score/page_content 等字段。
        - query: 用于查询感知打分的当前查询。
        - keep_rate: 保留高分文档的比例（0.1 到 1.0）。
        - min_chars: 每个保留文档压缩后的最小文本长度。

        结果说明:
        - 返回上下文规模更小的压缩文档列表。
        - 增加 `compression_note` 标记，便于下游可观测性。

        证据键:
        - longllmlingua_2023_2024
        - llmlingua2_2024
        """

    # 工业/故障文中常见的核心领域词汇
    INDUSTRIAL_DOMAIN_TERMS = {
        # 故障诊断相关
        "故障", "现象", "症状", "诊断", "排查", "分析", "原因", "根本原因",
        "故障树", "故障分析", "故障模式", "FMEA", "FTA",
        # 设备/组件相关
        "设备", "组件", "硬件", "软件", "系统", "模块", "传感器", "执行器",
        "电池", "电路", "芯片", "内存", "磁盘", "处理器", "风扇",
        # 故障类型
        "错误", "异常", "宕机", "崩溃", "卡顿", "断连", "超时", "溢出",
        "泄漏", "短路", "过载", "过热", "欠压", "过压",
        # 解决方案相关
        "解决", "方案", "处理", "修复", "维修", "更换", "升级", "回滚",
        "重启", "重置", "清理", "优化", "参数", "配置", "调整",
        # 检测工具/方法
        "日志", "监控", "告警", "阈值", "指标", "性能", "CPU", "内存", "磁盘",
        "网络", "API", "数据库", "缓存", "队列", "消息",
    }

    def __init__(self):
        """初始化工业领域词汇和权重。"""
        if HAS_JIEBA:
            self._init_jieba_dict()

    def _init_jieba_dict(self):
        """加载工业领域词汇到 jieba，并设定权重。"""
        # ① 添加工业领域术语到词典
        for term in self.INDUSTRIAL_DOMAIN_TERMS:
            jieba.add_word(term, freq=500)  # freq 越高，越可能被作为一个词单独分割

        # ② 优化特定的多字词组
        # 这些词组容易被错误分割，需要明确指定
        multi_char_phrases = [
            ("故障树", 1000),
            ("故障分析", 1000),
            ("根本原因", 900),
            ("故障现象", 900),
            ("故障模式", 900),
            ("解决方案", 900),
            ("排查步骤", 800),
            ("错误代码", 800),
            ("系统故障", 800),
            ("性能指标", 800),
            ("故障排查", 800),
            ("FMEA分析", 700),
            ("故障诊断", 700),
        ]
        for phrase, freq in multi_char_phrases:
            jieba.add_word(phrase, freq=freq)

        # ③ 设定词分割权重（增强分割准确度）
        jieba.suggest_freq(("故障", "分析"), tune=True)
        jieba.suggest_freq(("根本", "原因"), tune=True)
        jieba.suggest_freq(("解决", "方案"), tune=True)
        jieba.suggest_freq(("排查", "步骤"), tune=True)

    def compress_documents(
        self,
        documents: Sequence[ScoredDocument],
        query: str,
        keep_rate: float = 0.5,
        min_chars: int = 160,
    ) -> list[ScoredDocument]:
        """以查询感知方式压缩选中的检索文档。

        参数:
            documents: 检索片段，后续会按内部打分逻辑排序。
            query: 当前用户查询。
            keep_rate: 保留高分文档的比例。
            min_chars: 每个保留文档抽取文本的最小长度。

        返回:
            带有 `compression_note` 元数据的压缩文档子集。
        """
        if not documents:
            return []

        keep_rate = max(0.1, min(1.0, keep_rate))
        min_chars = max(80, min_chars)

        ranked = sorted((dict(d) for d in documents), key=self._score, reverse=True)
        keep_count = max(1, math.ceil(len(ranked) * keep_rate))
        kept = ranked[:keep_count]

        query_terms = self._extract_terms(query)
        compressed: list[ScoredDocument] = []

        for doc in kept:
            text = str(doc.get("page_content", ""))
            doc["page_content"] = self._compress_text(text, query_terms=query_terms, min_chars=min_chars)
            doc["compression_note"] = "extractive_query_aware_placeholder"
            compressed.append(doc)

        return compressed

    def _compress_text(self, text: str, query_terms: set[str], min_chars: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= min_chars:
            return normalized

        chunks = [c.strip() for c in re.split(r"[\n\.!?;]", normalized) if c.strip()]
        if not chunks:
            return normalized[:min_chars]

        # 优先保留与查询词重叠更多的文本片段。
        scored_chunks = sorted(
            chunks,
            key=lambda chunk: self._overlap_score(chunk, query_terms),
            reverse=True,
        )

        selected: list[str] = []
        size = 0
        for chunk in scored_chunks:
            selected.append(chunk)
            size += len(chunk)
            if size >= min_chars:
                break

        if not selected:
            return normalized[:min_chars]

        return ". ".join(selected)

    @staticmethod
    def _extract_terms(text: str) -> set[str]:
        """提取文本中的关键词，支持中文。
        包错误则降级为英文。
        优先使用 jieba 中文分词（更精确），
        降级到正则提取（更快）。
        """
        if HAS_JIEBA:
            # ① 使用 jieba 中文分词
            words = jieba.cut(text, cut_all=False)
            # ② 过滤停用词和空字符串
            filtered = [w.lower() for w in words if len(w.strip()) > 0]
            # ③ 移除纯标点符号和数字
            terms = {w for w in filtered if re.search(r"[\u4e00-\u9fff\w]", w)}
            return terms
        else:
            # 降级：仅做英文正则提取
            return set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))

    def _overlap_score(self, chunk: str, query_terms: set[str]) -> float:
        """计算句子与查询的关联度，支持领域术语权重。
        
        返回值范围：0.0 ~ 2.0+
        - 普通词重叠：1.0x
        - 领域术语重叠：2.0x（权重提升）
        """
        if not query_terms:
            return 0.0
        chunk_terms = self._extract_terms(chunk)
        if not chunk_terms:
            return 0.0
        
        # ① 计算简单重叠
        overlap = len(chunk_terms & query_terms)
        base_score = overlap / len(query_terms)
        
        # ② 增强：如果重叠的词是领域术语，权重加倍
        domain_overlap = len((chunk_terms & query_terms) & self.INDUSTRIAL_DOMAIN_TERMS)
        domain_bonus = domain_overlap * 0.5  # 每个领域词 +0.5 加成
        
        total_score = base_score + domain_bonus
        return total_score

    @staticmethod
    def _score(document: dict[str, Any]) -> float:
        try:
            return float(document.get("score", 0.0))
        except (TypeError, ValueError):
            return 0.0
