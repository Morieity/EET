import os
import json
from dotenv import load_dotenv
from flask import Flask, request
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.document_loaders import PDFPlumberLoader

load_dotenv()

app = Flask(__name__)

folder_path = "db"

# 使用 DeepSeek 兼容的 OpenAI 接口
cached_llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.7
)

embedding = FastEmbedEmbeddings()

## 文本分割
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1024, chunk_overlap=80, length_function=len, is_separator_regex=False
)

## 提示词模板
raw_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a technical assistant good at searching documents. If you do not have an answer from the provided information say so."),
    ("human", "{input}\n\nContext:\n{context}")
])

## 对AI提问并回答
@app.route("/ai", methods=["POST"])
def aiPost():
    print("Post /ai called")
    json_content = request.json
    query = json_content.get("query")

    print(f"query: {query}")

    response = cached_llm.invoke(query)

    print(response.content)

    response_answer = {"answer": response.content}
    return response_answer


@app.route("/ask_pdf", methods=["POST"])
def askPDFPost():
    ## 获取向量数据库中的临近信息用于LLM提示词编写
    print("Post /ask_pdf called")
    json_content = request.json
    query = json_content.get("query")

    print(f"query: {query}")

    try:
        print("Loading vector store")
        vector_store = Chroma(persist_directory=folder_path, embedding_function=embedding)

        print("Creating retriever")
        retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 20,
                "score_threshold": 0.1,
            },
        )
        
        # 使用新的 Runnable API 构建链
        print("Building RAG chain")
        
        # 检索相关文档
        retrieved_docs = retriever.invoke(query)
        
        # 格式化文档为上下文
        context = "\n\n".join([f"Document: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}" for doc in retrieved_docs])
        
        # 构建提示词并调用 LLM
        chain = raw_prompt | cached_llm
        result = chain.invoke({"input": query, "context": context})
        
        print(f"Answer: {result.content}")
        
        sources = []
        for doc in retrieved_docs:
            sources.append(
                {"source": doc.metadata.get("source", "Unknown"), "page_content": doc.page_content}
            )

        response_answer = {"answer": result.content, "sources": sources}
        return response_answer
    except Exception as e:
        print(f"Error in askPDFPost: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "Error",
            "message": f"Failed to process PDF query: {str(e)}"
        }, 500

# 实现PDF文件上传接口
# 我为这个代码添加了错误处理
@app.route("/pdf", methods=["POST"])
def pdfPost():
    try:
        # 1. 验证文件是否存在
        if "file" not in request.files:
            return {
                "status": "Error",
                "message": "No file provided in request"
            }, 400
        
        file = request.files["file"]
        
        # 2. 验证文件名
        if not file.filename:
            return {
                "status": "Error",
                "message": "File name is empty"
            }, 400
        
        if not file.filename.lower().endswith(".pdf"):
            return {
                "status": "Error",
                "message": "File must be a PDF"
            }, 400
        
        file_name = file.filename
        save_file = "pdf/" + file_name
        
        # 3. 存储上传的PDF文件
        try:
            file.save(save_file)
            print(f"filename: {file_name}")
        except Exception as e:
            return {
                "status": "Error",
                "message": f"Failed to save file: {str(e)}"
            }, 500
        
        # 4. 加载PDF文件
        try:
            loader = PDFPlumberLoader(save_file)
            docs = loader.load()
            print(f"docs len={len(docs)}")
            
            if not docs:
                return {
                    "status": "Error",
                    "message": "PDF file is empty or unreadable"
                }, 400
        except Exception as e:
            return {
                "status": "Error",
                "message": f"Failed to load PDF: {str(e)}"
            }, 500
        
        # 5. 文本分割
        try:
            chunks = text_splitter.split_documents(docs)
            print(f"chunks len={len(chunks)}")
            
            if not chunks:
                return {
                    "status": "Error",
                    "message": "No chunks generated from PDF content"
                }, 400
        except Exception as e:
            return {
                "status": "Error",
                "message": f"Failed to split documents: {str(e)}"
            }, 500
        
        # 6. 向量化和保存到数据库
        try:
            vector_store = Chroma.from_documents(
                documents=chunks, embedding=embedding, persist_directory=folder_path
            )
            vector_store.persist()
            print("Vector store persisted successfully")
        except Exception as e:
            return {
                "status": "Error",
                "message": f"Failed to create vector store: {str(e)}"
            }, 500
        
        # 7. 成功响应
        response = {
            "status": "Successfully Uploaded",
            "filename": file_name,
            "doc_len": len(docs),
            "chunks": len(chunks),
        }
        return response, 200
    
    except Exception as e:
        # 捕获所有未预期的异常
        print(f"Unexpected error in pdfPost: {str(e)}")
        return {
            "status": "Error",
            "message": f"Unexpected error: {str(e)}"
        }, 500


def start_app():
    app.run(host="0.0.0.0", port=8080, debug=True)


if __name__ == "__main__":
    start_app()
