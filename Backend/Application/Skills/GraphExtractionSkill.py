import json
import logging
from Backend.Domain.Entities.triple import Triple
from Backend.Application.Interfaces.ILLMService import ILLMService

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM = "你是一个工业故障知识图谱抽取助手，只返回 JSON，不附加任何解释。"

EXTRACT_USER = """请从以下文本中，仅抽取符合 Schema 的三元组。

Schema 约束（严格遵守，不得自行扩展类型）：
- 实体类型：COMPONENT（组件）| SYMPTOM（故障现象）| ERROR_CODE（错误码）| SOLUTION（解决方案）
- 关系类型：CAUSES（引发）| BELONGS_TO（属于）| RESOLVES（解决）| DIAGNOSES（排查）

输出格式（仅返回 JSON 数组，无任何额外文字）：
[
  {{"head": "实体名", "head_type": "类型", "relation": "关系", "tail": "实体名", "tail_type": "类型"}},
  ...
]
若文本中无符合条件的三元组，返回空数组 []。

文本：
{chunk_text}
"""

REQUIRED_FIELDS = ("head", "head_type", "relation", "tail", "tail_type")
VALID_ENTITY_TYPES = {"COMPONENT", "SYMPTOM", "ERROR_CODE", "SOLUTION"}
VALID_RELATION_TYPES = {"CAUSES", "BELONGS_TO", "RESOLVES", "DIAGNOSES"}


class GraphExtractionSkill:
    """调用 LLM 从文本块中抽取 Schema 定向三元组。"""

    def __init__(self, llm_service: ILLMService):
        self._llm = llm_service

    def extract(
        self, chunk_text: str, source_file: str = "", source_chunk_id: str = ""
    ) -> list[Triple]:
        user_prompt = EXTRACT_USER.format(chunk_text=chunk_text)
        messages = [
            {"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        # 收集流式输出的完整文本
        raw = ""
        try:
            for token in self._llm.stream_chat(messages):
                raw += token
        except Exception:
            logger.exception("LLM 调用失败，跳过本块抽取")
            return []

        parsed = self._parse_json(raw)
        if not isinstance(parsed, list):
            return []

        triples = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            if not all(k in item for k in REQUIRED_FIELDS):
                continue
            if item["head_type"] not in VALID_ENTITY_TYPES:
                continue
            if item["tail_type"] not in VALID_ENTITY_TYPES:
                continue
            if item["relation"] not in VALID_RELATION_TYPES:
                continue
            triples.append(Triple(
                head=item["head"].strip(),
                head_type=item["head_type"],
                relation=item["relation"],
                tail=item["tail"].strip(),
                tail_type=item["tail_type"],
                source_file=source_file,
                source_chunk_id=source_chunk_id,
            ))
        return triples

    @staticmethod
    def _parse_json(raw: str):
        text = raw.strip()
        # 去除 markdown 代码块
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip().rstrip("```").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("JSON 解析失败: %s | 原始内容: %s", e, raw[:200])
            return None
