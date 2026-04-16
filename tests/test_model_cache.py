"""单元测试: 模型缓存路径配置 & 预下载脚本"""

import hashlib
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── 项目根目录 ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CACHE_DIR = str(PROJECT_ROOT / "llm_model")


class TestModelCacheDir(unittest.TestCase):
    """验证 _MODEL_CACHE_DIR 指向项目根目录/llm_model"""

    def test_cache_dir_value(self):
        from Backend.Infrastructure.vectorstore.ChromaVectorStoreRepository import (
            _MODEL_CACHE_DIR,
        )
        self.assertEqual(_MODEL_CACHE_DIR, EXPECTED_CACHE_DIR)

    @patch(
        "Backend.Infrastructure.vectorstore.ChromaVectorStoreRepository.FastEmbedEmbeddings"
    )
    def test_embedding_receives_cache_dir(self, mock_embed_cls):
        """FastEmbedEmbeddings 构造时必须传入 cache_dir"""
        mock_embed_cls.return_value = MagicMock()

        # 重新导入以触发 __init__
        from Backend.Infrastructure.vectorstore.ChromaVectorStoreRepository import (
            ChromaVectorStoreRepository,
            _MODEL_CACHE_DIR,
        )

        repo = ChromaVectorStoreRepository.__new__(ChromaVectorStoreRepository)
        repo.__init__()

        mock_embed_cls.assert_called_once_with(cache_dir=_MODEL_CACHE_DIR)


class TestDownloadScript(unittest.TestCase):
    """验证 scripts/download_models.py 中的常量和逻辑"""

    def test_script_constants(self):
        import scripts.download_models as dm

        self.assertEqual(dm.MODEL_NAME, "BAAI/bge-small-en-v1.5")
        self.assertEqual(dm.CACHE_DIR, PROJECT_ROOT / "llm_model")

    @patch("scripts.download_models.TextEmbedding")
    def test_main_creates_dir_and_downloads(self, mock_te):
        import scripts.download_models as dm

        dm.main()

        self.assertTrue(dm.CACHE_DIR.exists())
        mock_te.assert_called_once_with(
            model_name="BAAI/bge-small-en-v1.5",
            cache_dir=str(dm.CACHE_DIR),
        )


class TestModelFilesExist(unittest.TestCase):
    """验证 llm_model/ 目录中模型文件实际存在（集成级别）"""

    def test_llm_model_dir_exists(self):
        model_dir = PROJECT_ROOT / "llm_model"
        self.assertTrue(model_dir.exists(), f"{model_dir} 不存在，请先运行 scripts/download_models.py")

    def test_onnx_model_file_present(self):
        onnx_files = list((PROJECT_ROOT / "llm_model").rglob("*.onnx"))
        self.assertGreater(len(onnx_files), 0, "未找到 .onnx 模型文件")

    def test_tokenizer_present(self):
        tok_files = list((PROJECT_ROOT / "llm_model").rglob("tokenizer*.json"))
        self.assertGreater(len(tok_files), 0, "未找到 tokenizer 文件")


class TestHelperMethods(unittest.TestCase):
    """验证静态工具方法 _entity_id / _relation_id"""

    def test_entity_id_format(self):
        from Backend.Infrastructure.vectorstore.ChromaVectorStoreRepository import (
            ChromaVectorStoreRepository,
        )
        eid = ChromaVectorStoreRepository._entity_id("测试实体")
        self.assertTrue(eid.startswith("ent_"))
        expected = "ent_" + hashlib.md5("测试实体".encode()).hexdigest()[:12]
        self.assertEqual(eid, expected)

    def test_relation_id_format(self):
        from Backend.Infrastructure.vectorstore.ChromaVectorStoreRepository import (
            ChromaVectorStoreRepository,
        )
        rid = ChromaVectorStoreRepository._relation_id("头", "关系", "尾")
        self.assertTrue(rid.startswith("rel_"))
        key = "头|关系|尾"
        expected = "rel_" + hashlib.md5(key.encode()).hexdigest()[:12]
        self.assertEqual(rid, expected)

    def test_different_inputs_produce_different_ids(self):
        from Backend.Infrastructure.vectorstore.ChromaVectorStoreRepository import (
            ChromaVectorStoreRepository,
        )
        id_a = ChromaVectorStoreRepository._entity_id("A")
        id_b = ChromaVectorStoreRepository._entity_id("B")
        self.assertNotEqual(id_a, id_b)


if __name__ == "__main__":
    unittest.main()
