import time
import logging
from concurrent.futures import ThreadPoolExecutor
from Backend.Domain.Entities.triple import Triple
from Backend.Application.Interfaces.ITripleExtractor import ITripleExtractor
from Backend.Application.Skills.GraphExtractionSkill import GraphExtractionSkill
from Backend.Application.Interfaces.ILLMService import ILLMService

logger = logging.getLogger(__name__)

CHUNK_GROUP_SIZE = 2
ASYNC_TRIPLE_EXTRACT_MAX_WORKERS = 50


class TripleExtractor(ITripleExtractor):
    def __init__(self, llm_service: ILLMService, request_interval: float = 0.1):
        self._skill = GraphExtractionSkill(llm_service)
        self._request_interval = request_interval

    def extract(
        self, chunk_text: str, source_file: str = "", source_chunk_id: str = ""
    ) -> list[Triple]:
        return self._skill.extract(chunk_text, source_file, source_chunk_id)

    def _merge_chunks(self, chunks: list[str], group_size: int = CHUNK_GROUP_SIZE) -> list[tuple[str, list[int]]]:
        """将相邻的 chunks 合并，每组 2 个。返回 (合并后文本, 原始索引列表)"""
        merged = []
        for i in range(0, len(chunks), group_size):
            group = chunks[i:i+group_size]
            merged_text = "\n---\n".join(group)  # 用分隔线连接
            original_indices = list(range(i, min(i+group_size, len(chunks))))
            merged.append((merged_text, original_indices))
        logger.info(f"将 {len(chunks)} 个 chunks 合并为 {len(merged)} 组（每组最多 {group_size} 个）")
        return merged

    def batch_extract(self, chunks: list[str], source_file: str = "") -> list[Triple]:
        """同步版本：合并 chunks + 异步并发提取"""
        # 合并相邻 chunks
        merged_groups = self._merge_chunks(chunks, group_size=CHUNK_GROUP_SIZE)
        
        # 使用线程池并发调用 LLM
        all_triples: list[Triple] = []
        total = len(merged_groups)
        
        with ThreadPoolExecutor(max_workers=ASYNC_TRIPLE_EXTRACT_MAX_WORKERS) as executor:
            futures = []
            for merged_text, indices in merged_groups:
                future = executor.submit(
                    self._extract_from_merged,
                    merged_text,
                    indices,
                    source_file
                )
                futures.append((future, indices))
            
            # 收集结果
            for idx, (future, indices) in enumerate(futures):
                try:
                    triples = future.result()
                    all_triples.extend(triples)
                    logger.info(
                        "[%d/%d] 从合并组抽取 %d 条三元组（含 %d 个原始 chunks），累计 %d 条",
                        idx + 1, total, len(triples), len(indices), len(all_triples)
                    )
                except Exception as e:
                    logger.exception(f"[{idx + 1}/{total}] 抽取失败: {e}")
        
        logger.info("批量抽取完成: 共 %d 个原始 chunk → %d 个合并组 → %d 条三元组", 
                    len(chunks), total, len(all_triples))
        return all_triples

    def _extract_from_merged(
        self, merged_text: str, original_indices: list[int], source_file: str
    ) -> list[Triple]:
        """从合并的文本中提取三元组，保留原始 chunk 索引"""
        triples = self.extract(merged_text, source_file=source_file, source_chunk_id=str(original_indices[0]))
        
        # 为所有三元组添加第一个原始索引作为来源
        for triple in triples:
            triple.source_chunk_id = str(original_indices[0])
        
        time.sleep(self._request_interval)
        return triples
