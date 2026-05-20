import re

from Backend.Application.Chat.ChatModels import FaultTreeIntent

_FAULT_TREE_GENERATE_PATTERN = re.compile(
    r"(生成|创建|构建|画|建立).{0,10}(故障树|故障分析|FTA)",
    re.IGNORECASE,
)
_FAULT_TREE_UPDATE_PATTERN = re.compile(
    r"(修改|更新|调整|删除|添加|增加|移除|重命名|改).{0,10}(故障树|节点|逻辑门|连接)",
    re.IGNORECASE,
)
_FAULT_TREE_MENTION_PATTERN = re.compile(
    r"(故障树|FTA|故障分析)",
    re.IGNORECASE,
)


class FaultTreeIntentDetector:
    def detect(self, question: str) -> FaultTreeIntent:
        generate_match = _FAULT_TREE_GENERATE_PATTERN.search(question)
        update_match = _FAULT_TREE_UPDATE_PATTERN.search(question)
        mention_match = _FAULT_TREE_MENTION_PATTERN.search(question)
        is_direct = bool(generate_match or update_match)
        return FaultTreeIntent(
            is_generate=bool(generate_match),
            is_update=bool(update_match),
            is_direct=is_direct,
            is_request=is_direct or bool(mention_match),
        )
