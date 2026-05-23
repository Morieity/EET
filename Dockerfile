# ── 后端 Dockerfile ──────────────────────────────────────────────
# 使用 slim 镜像减小体积；Python 3.11 与项目要求一致
FROM python:3.11-slim

# chromadb / onnxruntime 需要 libgomp1；pdfplumber 等需要 gcc
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── 依赖安装（分两步，利用 Docker 层缓存）──────────────────────
COPY requirements2.txt .

# torch 默认包含 CUDA（约 2 GB），生产环境只需 CPU 版（约 200 MB）。
# 先安装与 requirements2.txt 一致的 CPU 版 torch，再安装其余依赖，避免 pip 回退到 CUDA 包。
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
        torch==2.10.0 \
        --index-url https://download.pytorch.org/whl/cpu

RUN grep -v '^torch==' requirements2.txt > requirements-docker.txt \
    && pip install --no-cache-dir --timeout 120 --retries 5 -r requirements-docker.txt \
    && rm requirements-docker.txt

# ── 复制源代码 ────────────────────────────────────────────────────
COPY . .

# 创建运行时目录（实际数据由 volume 挂载，这里只是确保路径存在）
RUN mkdir -p db uploads llm_model

EXPOSE 8080

# 生产环境关闭 debug，使用 threaded 模式保持多请求并发
CMD ["python", "-c", \
     "from Backend.Web.app_factory import create_app; \
      app = create_app(); \
      app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)"]
