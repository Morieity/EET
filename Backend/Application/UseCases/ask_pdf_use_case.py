from typing import Protocol, Tuple, List, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document


class Retriever(Protocol):
    def invoke(self, query: str) -> List[Document]:
        """返回与用户问题相关的文档列表。"""
        ...


class RetrieverFactory(Protocol):
    def get_retriever(self):
        """返回带有仓储默认配置的检索器实例。"""
        ...


class AskPdfUseCase:
    def __init__(self, retriever_factory: RetrieverFactory, prompt: ChatPromptTemplate, llm: ChatOpenAI):
        """初始化 PDF 检索增强问答所需依赖。"""
        self.retriever_factory = retriever_factory
        self.prompt = prompt
        self.llm = llm

    def execute(self, query: str) -> Tuple[str, List[Dict[str, str]]]:
        """基于检索到的文档上下文生成答案并返回来源信息。"""
        if not query:
            raise ValueError("Query is required")

        retriever = self.retriever_factory.get_retriever()
        retrieved_docs = retriever.invoke(query)

        context = "\n\n".join(
            [f"Document: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}" for doc in retrieved_docs]
        )

        chain = self.prompt | self.llm
        result = chain.invoke({"input": query, "context": context})

        sources = []
        for doc in retrieved_docs:
            sources.append(
                {"source": doc.metadata.get("source", "Unknown"), "page_content": doc.page_content}
            )

        return result.content, sources
