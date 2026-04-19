"""FaultTreeSkill sources 字段 — 单元测试与集成测试

覆盖范围:
  - _parse_tree_data 解析含 sources 的 arguments
  - _parse_tree_data 解析不含 sources 的 arguments（默认空数组）
  - FAULT_TREE_TOOLS schema 校验（generate + update 均含 sources 定义）
  - sources 不在 nodes required 列表中
  - generate 和 update 端到端含 sources 流程
  - 系统提示词包含引用来源约束
"""

import pytest

from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Application.Interfaces.IFaultTreeRepository import IFaultTreeRepository
from Backend.Application.Skills.FaultTreeSkill import FaultTreeSkill, FAULT_TREE_TOOLS
from Backend.Domain.Entities.fault_tree import FaultTree, FaultTreeNode
from Backend.Domain.Common.Enums.FaultTreeEnums import NodeType


# ── 内存仓储 ──


class _InMemoryFaultTreeRepo(IFaultTreeRepository):
    def __init__(self):
        self._trees: dict[str, FaultTree] = {}

    def save(self, fault_tree: FaultTree) -> None:
        self._trees[fault_tree.id] = fault_tree

    def get_by_id(self, tree_id: str) -> FaultTree | None:
        return self._trees.get(tree_id)

    def get_by_conversation_id(self, conversation_id: str) -> FaultTree | None:
        for tree in reversed(list(self._trees.values())):
            if tree.conversation_id == conversation_id:
                return tree
        return None

    def get_all(self) -> list[FaultTree]:
        return list(self._trees.values())

    def update(self, fault_tree: FaultTree) -> None:
        self._trees[fault_tree.id] = fault_tree

    def delete(self, tree_id: str) -> None:
        self._trees.pop(tree_id, None)


class _InMemoryConversationRepo(IConversationRepository):
    def __init__(self):
        self._conversations = {}

    def save(self, conversation) -> None:
        self._conversations[conversation.id] = conversation

    def get_by_id(self, conversation_id: str):
        return self._conversations.get(conversation_id)

    def get_all(self) -> list:
        return list(self._conversations.values())

    def delete(self, conversation_id: str) -> None:
        self._conversations.pop(conversation_id, None)

    def add_round(self, conversation_id: str, chat_round) -> None:
        self._conversations[conversation_id].add_round(chat_round)

    def link_latest_round_fault_tree(self, conversation_id: str, fault_tree_id: str) -> bool:
        return False


@pytest.fixture()
def skill():
    repo = _InMemoryFaultTreeRepo()
    return FaultTreeSkill(repo)


@pytest.fixture()
def skill_with_repos():
    ft_repo = _InMemoryFaultTreeRepo()
    conv_repo = _InMemoryConversationRepo()
    return FaultTreeSkill(ft_repo, conversation_repository=conv_repo), ft_repo


# ── Tool Schema 测试 ──


class TestFaultTreeToolSchema:
    """验证 FAULT_TREE_TOOLS schema 中 sources 属性定义"""

    def _get_tool_by_name(self, name: str) -> dict:
        for tool in FAULT_TREE_TOOLS:
            if tool["function"]["name"] == name:
                return tool
        raise ValueError(f"Tool {name} not found")

    def test_generate_tool_has_sources_in_nodes_items(self):
        tool = self._get_tool_by_name("generate_fault_tree")
        node_props = tool["function"]["parameters"]["properties"]["nodes"]["items"]["properties"]
        assert "sources" in node_props
        assert node_props["sources"]["type"] == "array"

    def test_update_tool_has_sources_in_nodes_items(self):
        tool = self._get_tool_by_name("update_fault_tree")
        node_props = tool["function"]["parameters"]["properties"]["nodes"]["items"]["properties"]
        assert "sources" in node_props
        assert node_props["sources"]["type"] == "array"

    def test_sources_items_has_required_fields(self):
        tool = self._get_tool_by_name("generate_fault_tree")
        sources_schema = tool["function"]["parameters"]["properties"]["nodes"]["items"]["properties"]["sources"]
        item_required = sources_schema["items"]["required"]
        assert "file_name" in item_required
        assert "page_content" in item_required

    def test_sources_not_in_nodes_required(self):
        """sources 应为可选字段，不在 nodes item required 列表中"""
        for tool in FAULT_TREE_TOOLS:
            node_required = tool["function"]["parameters"]["properties"]["nodes"]["items"]["required"]
            assert "sources" not in node_required, (
                f"sources should not be required in {tool['function']['name']}"
            )

    def test_generate_and_update_sources_schema_consistent(self):
        """两个工具的 sources schema 应一致"""
        gen = self._get_tool_by_name("generate_fault_tree")
        upd = self._get_tool_by_name("update_fault_tree")
        gen_sources = gen["function"]["parameters"]["properties"]["nodes"]["items"]["properties"]["sources"]
        upd_sources = upd["function"]["parameters"]["properties"]["nodes"]["items"]["properties"]["sources"]
        assert gen_sources == upd_sources

    def test_generate_description_contains_source_guidance(self):
        """generate_fault_tree 的 description 应包含引用来源约束"""
        tool = self._get_tool_by_name("generate_fault_tree")
        desc = tool["function"]["description"]
        assert "sources" in desc
        assert "检索上下文" in desc or "检索结果" in desc
        assert "逻辑门" in desc


# ── _parse_tree_data 测试 ──


class TestParseTreeData:
    """_parse_tree_data 解析 sources 字段"""

    def test_parse_with_sources(self, skill):
        arguments = {
            "name": "测试树",
            "nodes": [
                {
                    "id": "n1",
                    "label": "电机过热",
                    "node_type": "event",
                    "remark": "备注",
                    "sources": [
                        {"file_name": "手册.pdf", "page_content": "原文片段"},
                        {"file_name": "案例.docx", "page_content": "案例内容"},
                    ],
                },
                {
                    "id": "g1",
                    "label": "",
                    "node_type": "gate",
                    "gate_type": "OR",
                },
            ],
            "edges": [],
        }
        name, nodes, edges = skill._parse_tree_data(arguments)
        assert name == "测试树"
        assert len(nodes) == 2
        assert nodes[0].sources == arguments["nodes"][0]["sources"]
        assert nodes[1].sources == []

    def test_parse_without_sources_defaults_empty(self, skill):
        arguments = {
            "name": "无来源树",
            "nodes": [
                {"id": "n1", "label": "事件", "node_type": "event"},
            ],
            "edges": [],
        }
        name, nodes, edges = skill._parse_tree_data(arguments)
        assert nodes[0].sources == []

    def test_parse_sources_empty_array(self, skill):
        arguments = {
            "name": "空来源",
            "nodes": [
                {"id": "n1", "label": "事件", "node_type": "event", "sources": []},
            ],
            "edges": [],
        }
        _, nodes, _ = skill._parse_tree_data(arguments)
        assert nodes[0].sources == []

    def test_parse_multiple_nodes_mixed_sources(self, skill):
        arguments = {
            "name": "混合",
            "nodes": [
                {
                    "id": "n1", "label": "A", "node_type": "event",
                    "sources": [{"file_name": "a.pdf", "page_content": "内容A"}],
                },
                {"id": "g1", "label": "", "node_type": "gate", "gate_type": "AND"},
                {"id": "n2", "label": "B", "node_type": "event"},
            ],
            "edges": [
                {"id": "e1", "source_id": "n1", "target_id": "g1"},
                {"id": "e2", "source_id": "g1", "target_id": "n2"},
            ],
        }
        _, nodes, edges = skill._parse_tree_data(arguments)
        assert len(nodes) == 3
        assert nodes[0].sources == [{"file_name": "a.pdf", "page_content": "内容A"}]
        assert nodes[1].sources == []  # gate
        assert nodes[2].sources == []  # missing sources key
        assert len(edges) == 2


# ── execute (generate/update) 集成测试 ──


class TestSkillExecuteWithSources:
    """FaultTreeSkill.execute 端到端含 sources"""

    def test_generate_with_sources(self, skill_with_repos):
        skill, repo = skill_with_repos
        args = {
            "name": "电机故障分析",
            "nodes": [
                {
                    "id": "n1", "label": "电机过热", "node_type": "event",
                    "sources": [{"file_name": "手册.pdf", "page_content": "原因分析"}],
                },
                {"id": "g1", "label": "", "node_type": "gate", "gate_type": "OR"},
                {"id": "n2", "label": "子事件", "node_type": "event"},
            ],
            "edges": [
                {"id": "e1", "source_id": "n1", "target_id": "g1"},
                {"id": "e2", "source_id": "g1", "target_id": "n2"},
            ],
        }
        tree = skill.execute("generate_fault_tree", args)
        assert tree.name == "电机故障分析"
        assert tree.nodes[0].sources == [{"file_name": "手册.pdf", "page_content": "原因分析"}]
        assert tree.nodes[1].sources == []
        assert tree.nodes[2].sources == []

        # 验证持久化
        saved = repo.get_by_id(tree.id)
        assert saved is not None
        assert saved.nodes[0].sources == tree.nodes[0].sources

    def test_update_preserves_sources(self, skill_with_repos):
        skill, repo = skill_with_repos
        conv_id = "test-conv-1"

        # 先生成
        gen_args = {
            "name": "初始树",
            "nodes": [
                {"id": "n1", "label": "A", "node_type": "event",
                 "sources": [{"file_name": "old.pdf", "page_content": "旧内容"}]},
            ],
            "edges": [],
        }
        original = skill.execute("generate_fault_tree", gen_args, conversation_id=conv_id)

        # 再更新
        upd_args = {
            "name": "更新后的树",
            "nodes": [
                {"id": "n1", "label": "A更新", "node_type": "event",
                 "sources": [{"file_name": "new.pdf", "page_content": "新内容"}]},
                {"id": "n2", "label": "B", "node_type": "event"},
            ],
            "edges": [],
        }
        updated = skill.execute("update_fault_tree", upd_args, conversation_id=conv_id)

        assert updated.id == original.id
        assert updated.name == "更新后的树"
        assert updated.nodes[0].sources == [{"file_name": "new.pdf", "page_content": "新内容"}]
        assert updated.nodes[1].sources == []

    def test_generate_without_sources_backward_compat(self, skill_with_repos):
        """不含 sources 的旧格式 arguments 也能正常生成"""
        skill, repo = skill_with_repos
        args = {
            "name": "旧格式树",
            "nodes": [
                {"id": "n1", "label": "事件", "node_type": "event"},
            ],
            "edges": [],
        }
        tree = skill.execute("generate_fault_tree", args)
        assert tree.nodes[0].sources == []

    def test_to_dict_output_contains_sources(self, skill_with_repos):
        """验证生成的树 to_dict 输出包含 sources（API 返回格式）"""
        skill, _ = skill_with_repos
        args = {
            "name": "API输出测试",
            "nodes": [
                {"id": "n1", "label": "A", "node_type": "event",
                 "sources": [{"file_name": "doc.pdf", "page_content": "片段"}]},
            ],
            "edges": [],
        }
        tree = skill.execute("generate_fault_tree", args)
        d = tree.to_dict()
        assert "sources" in d["nodes"][0]
        assert d["nodes"][0]["sources"] == [{"file_name": "doc.pdf", "page_content": "片段"}]
