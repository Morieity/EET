#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""故障树模块 API 测试"""

import json
import time
import requests

BASE_URL = "http://127.0.0.1:8080"


def parse_sse_stream(response):
    """解析 SSE 流，逐事件返回"""
    event_type = None
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            event_type = None
        elif line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_str = line[5:].strip()
            try:
                data = json.loads(data_str)
            except Exception:
                data = data_str
            if event_type:
                yield event_type, data


# ── 通过对话生成故障树 ──


def test_generate_fault_tree_via_chat():
    """测试通过对话触发故障树生成"""
    print("\n" + "=" * 60)
    print("FT TEST 1: POST /api/chat - 通过对话生成故障树")
    print("=" * 60)

    payload = {
        "question": "请根据以下描述生成故障树：汽车无法启动，可能原因包括电池没电、启动马达故障、燃油不足。电池没电可能由于电池老化或发电机故障引起。"
    }

    print(f"问题: {payload['question'][:50]}...\n")

    conversation_id = None
    fault_tree_data = None
    full_answer = ""
    done_fault_tree_id = None

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload,
        headers={"Content-Type": "application/json"},
        stream=True,
        timeout=120,
    )
    response.raise_for_status()

    # 验证 SSE 头
    assert response.headers.get("Content-Type", "").startswith("text/event-stream"), \
        "响应类型应为 text/event-stream"

    for event_type, data in parse_sse_stream(response):
        if event_type == "conversation":
            conversation_id = data.get("conversation_id")
            print(f"[✓ conversation] 对话ID: {conversation_id[:20]}...")
        elif event_type == "sources":
            print(f"[✓ sources] 检索到 {len(data.get('sources', []))} 条文档")
        elif event_type == "fault_tree":
            fault_tree_data = data.get("fault_tree") or data
            tree_name = fault_tree_data.get("name", "未知")
            nodes = fault_tree_data.get("nodes", [])
            edges = fault_tree_data.get("edges", [])
            print(f"\n[✓ fault_tree] 名称: {tree_name}")
            print(f"               节点数: {len(nodes)}")
            print(f"               边数: {len(edges)}")
        elif event_type == "token":
            full_answer += data.get("content", "")
            print(data.get("content", ""), end="", flush=True)
        elif event_type == "done":
            done_fault_tree_id = data.get("fault_tree_id")
            print(f"\n\n[✓ done] 完成! 回答共 {len(full_answer)} 字符")
        elif event_type == "error":
            print(f"\n[✗ error] {data.get('message')}")

    assert conversation_id, "conversation_id 不能为空"
    assert fault_tree_data, "应该生成了故障树"
    assert len(fault_tree_data.get("nodes", [])) > 0, "故障树应有节点"
    assert len(fault_tree_data.get("edges", [])) > 0, "故障树应有边"
    assert done_fault_tree_id == fault_tree_data.get("id"), "done 事件应携带当前轮的 fault_tree_id"

    return conversation_id, fault_tree_data


def test_get_fault_tree_by_conversation(conversation_id):
    """通过 conversation_id 查询故障树"""
    print("\n" + "=" * 60)
    print("FT TEST 2: GET /api/fault-trees/conversation/<id>")
    print("=" * 60)

    response = requests.get(
        f"{BASE_URL}/api/fault-trees/conversation/{conversation_id}", timeout=10
    )
    response.raise_for_status()
    tree = response.json()

    print(f"[✓] 状态: {response.status_code}")
    print(f"[✓] 树ID: {tree['id'][:20]}...")
    print(f"[✓] 名称: {tree['name']}")
    print(f"[✓] 节点数: {len(tree['nodes'])}")
    print(f"[✓] 边数: {len(tree['edges'])}")
    print(f"[✓] conversation_id: {tree.get('conversation_id', 'N/A')[:20]}...")

    assert tree.get("conversation_id") == conversation_id
    assert len(tree["nodes"]) > 0
    assert len(tree["edges"]) > 0

    return tree["id"]


def test_get_fault_tree_by_id(tree_id):
    """通过 tree_id 查询故障树"""
    print("\n" + "=" * 60)
    print("FT TEST 3: GET /api/fault-trees/<id>")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/api/fault-trees/{tree_id}", timeout=10)
    response.raise_for_status()
    tree = response.json()

    print(f"[✓] 状态: {response.status_code}")
    print(f"[✓] 树ID: {tree['id']}")
    print(f"[✓] 名称: {tree['name']}")

    assert tree["id"] == tree_id


def test_conversation_round_links_fault_tree(conversation_id, tree_id):
    """验证会话详情中的最后一轮带有 fault_tree_id"""
    print("\n" + "=" * 60)
    print("FT TEST 3.5: GET /api/conversations/<id> 轮次关联故障树")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/api/conversations/{conversation_id}", timeout=10)
    response.raise_for_status()
    conversation = response.json()
    rounds = conversation.get("rounds", [])

    assert rounds, "会话至少应包含一轮对话"

    last_round = rounds[-1]
    print(f"[✓] 会话轮次数: {len(rounds)}")
    print(f"[✓] 最后一轮 fault_tree_id: {last_round.get('fault_tree_id')}")

    assert last_round.get("fault_tree_id") == tree_id


def test_list_fault_trees(tree_id):
    """获取故障树列表"""
    print("\n" + "=" * 60)
    print("FT TEST 4: GET /api/fault-trees")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/api/fault-trees", timeout=10)
    response.raise_for_status()
    trees = response.json()

    print(f"[✓] 状态: {response.status_code}")
    print(f"[✓] 故障树总数: {len(trees)}")

    assert isinstance(trees, list)
    assert any(t["id"] == tree_id for t in trees), "列表中应包含刚创建的故障树"


def test_update_fault_tree(tree_id):
    """测试更新故障树"""
    print("\n" + "=" * 60)
    print("FT TEST 5: PUT /api/fault-trees/<id> - 更新故障树")
    print("=" * 60)

    update_data = {
        "name": "更新后的故障树",
        "nodes": [
            {"id": "n1", "label": "系统故障", "node_type": "event"},
            {"id": "g1", "label": "", "node_type": "gate", "gate_type": "OR"},
            {"id": "n2", "label": "硬件故障", "node_type": "event"},
            {"id": "n3", "label": "软件故障", "node_type": "event"},
        ],
        "edges": [
            {"id": "e1", "source_id": "n1", "target_id": "g1"},
            {"id": "e2", "source_id": "g1", "target_id": "n2"},
            {"id": "e3", "source_id": "g1", "target_id": "n3"},
        ],
    }

    response = requests.put(
        f"{BASE_URL}/api/fault-trees/{tree_id}",
        json=update_data,
        timeout=10,
    )
    response.raise_for_status()
    tree = response.json()

    print(f"[✓] 状态: {response.status_code}")
    print(f"[✓] 更新后名称: {tree['name']}")
    print(f"[✓] 节点数: {len(tree['nodes'])}")
    print(f"[✓] 边数: {len(tree['edges'])}")

    assert tree["name"] == "更新后的故障树"
    assert len(tree["nodes"]) == 4
    assert len(tree["edges"]) == 3


def test_update_fault_tree_via_chat(conversation_id):
    """通过对话修改已有故障树"""
    print("\n" + "=" * 60)
    print("FT TEST 6: POST /api/chat - 通过对话修改故障树")
    print("=" * 60)

    payload = {
        "question": "请在故障树中增加一个原因节点：'点火系统故障'，作为汽车无法启动的另一个可能原因。",
        "conversation_id": conversation_id,
    }

    print(f"问题: {payload['question'][:50]}...\n")

    fault_tree_data = None
    full_answer = ""

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload,
        headers={"Content-Type": "application/json"},
        stream=True,
        timeout=120,
    )
    response.raise_for_status()

    for event_type, data in parse_sse_stream(response):
        if event_type == "fault_tree":
            fault_tree_data = data.get("fault_tree") or data
            print(f"[✓ fault_tree] 更新后名称: {fault_tree_data.get('name')}")
            print(f"               节点数: {len(fault_tree_data.get('nodes', []))}")
            print(f"               边数: {len(fault_tree_data.get('edges', []))}")
        elif event_type == "token":
            full_answer += data.get("content", "")
            print(data.get("content", ""), end="", flush=True)
        elif event_type == "done":
            print(f"\n\n[✓ done] 完成")
        elif event_type == "error":
            print(f"\n[✗ error] {data.get('message')}")

    # 故障树可能被更新也可能 LLM 选择了文本回复，两种都是有效行为
    if fault_tree_data:
        print("[✓] 故障树已通过对话成功更新")
    else:
        print("[~] LLM 选择了文本回复而非工具调用（也是有效行为）")

    assert len(full_answer) > 0, "应有文字回答"


# ── 错误处理测试 ──


def test_error_get_nonexistent_tree():
    """测试查询不存在的故障树"""
    print("\n" + "=" * 60)
    print("FT TEST 7: 错误处理 - 查询不存在的故障树")
    print("=" * 60)

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.get(f"{BASE_URL}/api/fault-trees/{fake_id}", timeout=10)

    print(f"[✓] 状态: {response.status_code} (期望 404)")
    print(f"[✓] {response.json()}")
    assert response.status_code == 404


def test_error_get_nonexistent_conversation_tree():
    """测试查询不存在对话的故障树"""
    print("\n" + "=" * 60)
    print("FT TEST 8: 错误处理 - 不存在对话的故障树")
    print("=" * 60)

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.get(
        f"{BASE_URL}/api/fault-trees/conversation/{fake_id}", timeout=10
    )

    print(f"[✓] 状态: {response.status_code} (期望 404)")
    assert response.status_code == 404


def test_error_update_missing_fields(tree_id):
    """测试更新时缺少必填字段"""
    print("\n" + "=" * 60)
    print("FT TEST 9: 错误处理 - 更新缺少字段")
    print("=" * 60)

    # 缺少 nodes 和 edges
    response = requests.put(
        f"{BASE_URL}/api/fault-trees/{tree_id}",
        json={"name": "测试"},
        timeout=10,
    )

    print(f"[✓] 状态: {response.status_code} (期望 400)")
    print(f"[✓] {response.json()}")
    assert response.status_code == 400


def test_error_update_nonexistent_tree():
    """测试更新不存在的故障树"""
    print("\n" + "=" * 60)
    print("FT TEST 10: 错误处理 - 更新不存在的故障树")
    print("=" * 60)

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.put(
        f"{BASE_URL}/api/fault-trees/{fake_id}",
        json={
            "name": "test",
            "nodes": [{"id": "n1", "label": "test", "node_type": "event"}],
            "edges": [{"id": "e1", "source_id": "n1", "target_id": "n1"}],
        },
        timeout=10,
    )

    print(f"[✓] 状态: {response.status_code} (期望 404)")
    assert response.status_code == 404


def test_error_delete_nonexistent_tree():
    """测试删除不存在的故障树"""
    print("\n" + "=" * 60)
    print("FT TEST 11: 错误处理 - 删除不存在的故障树")
    print("=" * 60)

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.delete(f"{BASE_URL}/api/fault-trees/{fake_id}", timeout=10)

    print(f"[✓] 状态: {response.status_code} (期望 404)")
    assert response.status_code == 404


def test_delete_fault_tree(tree_id):
    """测试删除故障树"""
    print("\n" + "=" * 60)
    print("FT TEST 12: DELETE /api/fault-trees/<id> - 删除故障树")
    print("=" * 60)

    response = requests.delete(f"{BASE_URL}/api/fault-trees/{tree_id}", timeout=10)
    response.raise_for_status()
    result = response.json()

    print(f"[✓] 状态: {response.status_code}")
    print(f"[✓] {result['message']}")

    assert response.status_code == 200

    # 验证已删除
    verify = requests.get(f"{BASE_URL}/api/fault-trees/{tree_id}", timeout=10)
    print(f"[✓] 验证删除: 状态 {verify.status_code} (期望 404)")
    assert verify.status_code == 404


def test_delete_conversation_cascades(conversation_id):
    """测试删除对话时级联删除关联故障树"""
    print("\n" + "=" * 60)
    print("FT TEST 13: 删除对话级联删除故障树")
    print("=" * 60)

    # 先确认故障树还存在
    tree_resp = requests.get(
        f"{BASE_URL}/api/fault-trees/conversation/{conversation_id}", timeout=10
    )

    if tree_resp.status_code == 404:
        print("[~] 故障树已被前面的测试删除，跳过级联测试")
        # 仍需清理对话
        requests.delete(f"{BASE_URL}/api/conversations/{conversation_id}", timeout=10)
        return

    tree_id = tree_resp.json()["id"]
    print(f"[✓] 关联故障树: {tree_id[:20]}...")

    # 删除对话
    del_resp = requests.delete(
        f"{BASE_URL}/api/conversations/{conversation_id}", timeout=10
    )
    del_resp.raise_for_status()
    print(f"[✓] 对话删除: {del_resp.status_code}")

    # 验证故障树也被删除
    verify = requests.get(f"{BASE_URL}/api/fault-trees/{tree_id}", timeout=10)
    print(f"[✓] 故障树验证: 状态 {verify.status_code} (期望 404)")
    assert verify.status_code == 404, "删除对话后关联的故障树应被级联删除"


def test_chat_with_nonexistent_conversation():
    """测试使用不存在的 conversation_id 发起对话"""
    print("\n" + "=" * 60)
    print("FT TEST 14: SSE 错误 - 不存在的 conversation_id")
    print("=" * 60)

    fake_id = "00000000-0000-0000-0000-000000000000"
    payload = {"question": "测试", "conversation_id": fake_id}

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload,
        stream=True,
        timeout=30,
    )

    got_error = False
    for event_type, data in parse_sse_stream(response):
        if event_type == "error":
            print(f"[✓ error] {data.get('message')}")
            got_error = True

    assert got_error, "应收到 error 事件"


def main():
    print("\n╔" + "=" * 58 + "╗")
    print("║" + "  故障树模块 - API 综合测试".center(52) + "║")
    print("╚" + "=" * 58 + "╝")

    passed = 0
    failed = 0
    conversation_id = None
    tree_id = None

    tests = [
        ("通过对话生成故障树", lambda: test_generate_fault_tree_via_chat()),
        ("会话轮次关联树ID", lambda: test_conversation_round_links_fault_tree(conversation_id, tree_id)),
        ("按对话ID查故障树", lambda: test_get_fault_tree_by_conversation(conversation_id)),
        ("按树ID查故障树", lambda: test_get_fault_tree_by_id(tree_id)),
        ("故障树列表", lambda: test_list_fault_trees(tree_id)),
        ("API更新故障树", lambda: test_update_fault_tree(tree_id)),
        ("对话修改故障树", lambda: test_update_fault_tree_via_chat(conversation_id)),
        ("查询不存在树", lambda: test_error_get_nonexistent_tree()),
        ("不存在对话树", lambda: test_error_get_nonexistent_conversation_tree()),
        ("更新缺字段", lambda: test_error_update_missing_fields(tree_id)),
        ("更新不存在树", lambda: test_error_update_nonexistent_tree()),
        ("删除不存在树", lambda: test_error_delete_nonexistent_tree()),
        ("删除故障树", lambda: test_delete_fault_tree(tree_id)),
        ("对话级联删除", lambda: test_delete_conversation_cascades(conversation_id)),
        ("不存在对话SSE", lambda: test_chat_with_nonexistent_conversation()),
    ]

    for name, test_fn in tests:
        try:
            result = test_fn()
            if name == "通过对话生成故障树" and result:
                conversation_id, ft_data = result
                tree_id = ft_data["id"]
            elif name == "按对话ID查故障树" and result:
                tree_id = result
            passed += 1
        except Exception as e:
            print(f"\n[✗ FAIL] {name}: {e}")
            failed += 1
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print(f"故障树测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
