from collections.abc import Sequence

from Backend.Application.ContextManagement.ContextTypes import MessageRecord


class QueryPlacementAlgorithm:
    """简要算法说明。

        论文来源:
        - Retrieval Head Mechanistically Explains Long-Context Factuality
            (arXiv:2404.15574)

        核心原理:
        - 将当前用户查询保持在提示词消息序列的尾部。
        - 尾部放置可在检索问答场景中提升实际注意力利用效果。

        参数含义:
        - messages: 现有提示词消息序列。
        - user_query: 最新用户问题。
        - context_block: 与查询一并拼接的可选检索上下文。

        结果说明:
        - 返回保证用户查询处于最后一条的新消息列表。
        - 不对现有消息内容做语义改写。

        证据键:
        - retrieval_head_2024
        """

    def append_query(
        self,
        messages: Sequence[MessageRecord],
        user_query: str,
        context_block: str = "",
    ) -> list[MessageRecord]:
        """追加一条包含查询与可选上下文的用户消息。

        参数:
            messages: 现有消息序列。
            user_query: 查询文本。
            context_block: 与查询拼接的可选上下文片段。

        返回:
            追加了一条用户消息的新消息列表。
        """
        copied = [dict(m) for m in messages]
        query = user_query.strip()
        context = context_block.strip()

        if context:
            content = f"{query}\n\nContext:\n{context}"
        else:
            content = query

        copied.append({"role": "user", "content": content})
        return copied

    def ensure_query_last(self, messages: Sequence[MessageRecord]) -> list[MessageRecord]:
        """在需要时将最后一条用户消息移动到尾部。"""
        copied = [dict(m) for m in messages]
        if not copied:
            return []

        last_user_index = None
        for idx in range(len(copied) - 1, -1, -1):
            if copied[idx].get("role") == "user":
                last_user_index = idx
                break

        if last_user_index is None or last_user_index == len(copied) - 1:
            return copied

        user_message = copied.pop(last_user_index)
        copied.append(user_message)
        return copied
