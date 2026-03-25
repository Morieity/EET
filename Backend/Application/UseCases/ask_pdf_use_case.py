from typing import Tuple, List, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from Backend.Application.Interfaces.retriever_repository import RetrieverFactory


class AskPdfUseCase:
    def __init__(self, retriever_factory: RetrieverFactory, llm: ChatOpenAI):
        """初始化 PDF 检索增强问答所需依赖。"""
        self.retriever_factory = retriever_factory
        self.prompt = self._build_prompt_template()
        self.llm = llm

    def _build_prompt_template(self) -> ChatPromptTemplate:
        """构建 RAG 问答提示词模板。"""
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a technical assistant good at searching documents. If you do not have an answer from the provided information say so.",
                ),
                ("human", "{input}\n\nContext:\n{context}"),
            ]
        )

    def execute(
        self,
        query: str,
        k: int = 20,
        score_threshold: float = 0.1,
    ) -> Tuple[str, List[Dict[str, str]]]:
        """基于检索到的文档上下文生成答案并返回来源信息。"""
        # 验证输入存在
        if not query:
            raise ValueError("Query is required")
        if k <= 0:
            raise ValueError("k must be greater than 0")
        if score_threshold < 0 or score_threshold > 1:
            raise ValueError("score_threshold must be between 0 and 1")

        # 搜索临近文字向量并获取相关文档
        retriever = self.retriever_factory.get_retriever(k=k, score_threshold=score_threshold)
        retrieved_docs = retriever.invoke(query)

        # 将检索到的文档内容与来源信息拼接成上下文字符串，供 LLM 生成答案使用
        context = "\n\n".join(
            [f"Document: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}" for doc in retrieved_docs]
        )

        # 将用户查询和检索到的上下文输入到 LLM 中生成答案
        chain = self.prompt | self.llm
        result = chain.invoke({"input": query, "context": context})
        # 为什么这里要调用一次invoke？因为 prompt 是一个 ChatPromptTemplate，它需要被调用来生成最终的提示文本，然后这个文本会被传递给 llm 来生成答案。

        # 从检索到的文档中提取来源信息，准备返回给前端展示
        sources = []
        for doc in retrieved_docs:
            sources.append(
                {"source": doc.metadata.get("source", "Unknown"), "page_content": doc.page_content}
            )

        return result.content, sources
