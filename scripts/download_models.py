"""在环境安装阶段预下载 FastEmbed 所需的嵌入模型到 llm_model/ 目录。

用法:
    python scripts/download_models.py
"""

from pathlib import Path
from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
CACHE_DIR = Path(__file__).resolve().parents[1] / "llm_model"


def main() -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    print(f"下载模型 {MODEL_NAME} → {CACHE_DIR}")
    # TextEmbedding 构造时会自动下载缺失的模型文件
    TextEmbedding(model_name=MODEL_NAME, cache_dir=str(CACHE_DIR))
    print("模型下载完成。")


if __name__ == "__main__":
    main()
