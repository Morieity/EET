"""T012: 测试 Conversation 实体的 work_order_id 字段及仓储读写。"""
import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Backend.Infrastructure.persistence.database import init_db, DB_PATH, get_connection
from Backend.Infrastructure.persistence.ConversationRepository import SQLiteConversationRepository
from Backend.Domain.Entities.conversation import Conversation


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.sqlite3")
    monkeypatch.setattr("Backend.Infrastructure.persistence.database.DB_PATH", db_path)
    monkeypatch.setattr("Backend.Infrastructure.persistence.ConversationRepository.get_connection",
                        lambda: __import__("Backend.Infrastructure.persistence.database", fromlist=["get_connection"]).get_connection())
    init_db()


@pytest.fixture
def repo():
    return SQLiteConversationRepository()


class TestConversationEntity:
    def test_work_order_id_default_none(self):
        conv = Conversation(name="test")
        assert conv.work_order_id is None

    def test_work_order_id_set(self):
        wid = str(uuid.uuid4())
        conv = Conversation(name="test", work_order_id=wid)
        assert conv.work_order_id == wid

    def test_to_dict_includes_work_order_id(self):
        wid = str(uuid.uuid4())
        conv = Conversation(name="test", work_order_id=wid)
        d = conv.to_dict()
        assert d["work_order_id"] == wid

    def test_to_dict_work_order_id_null(self):
        conv = Conversation(name="test")
        d = conv.to_dict()
        assert d["work_order_id"] is None


class TestConversationRepositoryWorkOrder:
    def test_save_and_get_with_work_order_id(self, repo):
        wid = str(uuid.uuid4())
        conv = Conversation(name="工单对话", work_order_id=wid)
        repo.save(conv)
        loaded = repo.get_by_id(conv.id)
        assert loaded is not None
        assert loaded.work_order_id == wid

    def test_save_without_work_order_id(self, repo):
        conv = Conversation(name="普通对话")
        repo.save(conv)
        loaded = repo.get_by_id(conv.id)
        assert loaded is not None
        assert loaded.work_order_id is None

    def test_get_all_includes_work_order_id(self, repo):
        wid = str(uuid.uuid4())
        repo.save(Conversation(name="工单对话", work_order_id=wid))
        repo.save(Conversation(name="普通对话"))
        all_convs = repo.get_all()
        assert len(all_convs) == 2
        wo_conv = next(c for c in all_convs if c.work_order_id == wid)
        plain_conv = next(c for c in all_convs if c.work_order_id is None)
        assert wo_conv is not None
        assert plain_conv is not None

    def test_get_by_work_order_id(self, repo):
        wid = str(uuid.uuid4())
        repo.save(Conversation(name="对话1", work_order_id=wid))
        repo.save(Conversation(name="对话2", work_order_id=wid))
        repo.save(Conversation(name="其他对话"))
        result = repo.get_by_work_order_id(wid)
        assert len(result) == 2
        assert all(c.work_order_id == wid for c in result)

    def test_get_by_work_order_id_empty(self, repo):
        result = repo.get_by_work_order_id(str(uuid.uuid4()))
        assert result == []

    def test_get_by_work_order_id_no_rounds_loaded(self, repo):
        wid = str(uuid.uuid4())
        repo.save(Conversation(name="对话", work_order_id=wid))
        result = repo.get_by_work_order_id(wid)
        assert len(result) == 1
        assert result[0].rounds == []
        assert hasattr(result[0], "round_count")
