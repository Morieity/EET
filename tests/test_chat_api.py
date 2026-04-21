#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对话模块 API 测试"""

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
            except:
                data = data_str
            if event_type:
                yield event_type, data


def test_create_conversation():
    """测试创建新对话"""
    print("\n" + "="*60)
    print("CHAT TEST 1: POST /api/chat - 创建新对话")
    print("="*60)

    payload = {"question": "你好，请简要介绍一下自己"}

    print(f"请求: POST {BASE_URL}/api/chat")
    print(f"数据: {json.dumps(payload, ensure_ascii=False)}")
    print("\n流式响应:\n")

    conversation_id = None
    full_answer = ""

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload,
        headers={"Content-Type": "application/json"},
        stream=True,
        timeout=60
    )
    response.raise_for_status()

    for event_type, data in parse_sse_stream(response):
        if event_type == "conversation":
            conversation_id = data.get("conversation_id")
            print(f"[✓ conversation] 对话ID: {conversation_id[:20]}...")
            print(f"                 对话名: {data.get('name')}")
        elif event_type == "sources":
            sources_data = data.get("sources", [])
            print(f"\n[✓ sources] 检索到 {len(sources_data)} 条文档\n")
        elif event_type == "token":
            token = data.get("content", "")
            full_answer += token
            print(token, end="", flush=True)
        elif event_type == "done":
            print(f"\n\n[✓ done] 完成! 回答共 {len(full_answer)} 字符")
        elif event_type == "error":
            print(f"\n[✗ error] {data.get('message')}")

    assert conversation_id, "conversation_id 不能为空"
    assert len(full_answer) > 0, "回答不能为空"

    return conversation_id


def test_list_conversations(conversation_id):
    """测试获取对话列表"""
    print("\n" + "="*60)
    print("CHAT TEST 2: GET /api/conversations - 获取对话列表")
    print("="*60)

    response = requests.get(f"{BASE_URL}/api/conversations", timeout=10)
    response.raise_for_status()
    conversations = response.json()

    print(f"[✓] 响应状态: {response.status_code}")
    print(f"[✓] 对话总数: {len(conversations)}")

    for i, conv in enumerate(conversations[:3], 1):
        marker = ">>>" if conv['id'] == conversation_id else "   "
        print(f"\n{marker} 对话 #{i}")
        print(f"    ID: {conv['id'][:20]}...")
        print(f"    名: {conv['name'][:40]}")

    assert response.status_code == 200
    assert isinstance(conversations, list)
    assert any(c['id'] == conversation_id for c in conversations)


def test_get_conversation_detail(conversation_id):
    """测试获取对话详情"""
    print("\n" + "="*60)
    print("CHAT TEST 3: GET /api/conversations/<id> - 获取对话详情")
    print("="*60)

    response = requests.get(f"{BASE_URL}/api/conversations/{conversation_id}", timeout=10)
    response.raise_for_status()
    conversation = response.json()

    print(f"[✓] 对话ID: {conversation['id']}")
    print(f"[✓] 对话名: {conversation['name']}")
    print(f"[✓] 创建于: {conversation['created_at']}")
    print(f"[✓] 轮次数: {len(conversation.get('rounds', []))}")

    for i, r in enumerate(conversation.get('rounds', []), 1):
        print(f"\n    第 {i} 轮: {r['question'][:40]}...")

    assert conversation['id'] == conversation_id
    assert len(conversation.get('rounds', [])) >= 1


def test_add_round(conversation_id):
    """测试在对话中添加新轮次"""
    print("\n" + "="*60)
    print("CHAT TEST 4: POST /api/chat - 添加新轮次")
    print("="*60)

    payload = {
        "question": "我再问一个问题",
        "conversation_id": conversation_id
    }

    print(f"问题: {payload['question']}\n")

    full_answer = ""

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload,
        headers={"Content-Type": "application/json"},
        stream=True,
        timeout=60
    )
    response.raise_for_status()

    for event_type, data in parse_sse_stream(response):
        if event_type == "conversation":
            print(f"[✓ conversation] 使用已有对话")
        elif event_type == "sources":
            print(f"[✓ sources] 检索 {len(data.get('sources', []))} 条文档\n")
        elif event_type == "token":
            full_answer += data.get("content", "")
            print(data.get("content", ""), end="", flush=True)
        elif event_type == "done":
            print(f"\n\n[✓ done] 完成")

    assert len(full_answer) > 0


def test_verify_rounds(conversation_id):
    """验证多轮对话"""
    print("\n" + "="*60)
    print("CHAT TEST 4.5: 验证 - 多轮对话")
    print("="*60)

    response = requests.get(f"{BASE_URL}/api/conversations/{conversation_id}", timeout=10)
    conversation = response.json()
    rounds = conversation.get("rounds", [])

    print(f"[✓] 轮次数: {len(rounds)}")
    for i, r in enumerate(rounds, 1):
        print(f"    第 {i} 轮: {r['question'][:40]}...")

    assert len(rounds) == 2, f"期望 2 轮，实际 {len(rounds)}"


def test_delete_conversation(conversation_id):
    """测试删除对话"""
    print("\n" + "="*60)
    print("CHAT TEST 5: DELETE /api/conversations/<id> - 删除对话")
    print("="*60)

    response = requests.delete(f"{BASE_URL}/api/conversations/{conversation_id}", timeout=10)
    response.raise_for_status()
    result = response.json()

    print(f"[✓] 响应状态: {response.status_code}")
    print(f"[✓] {result['message']}")

    assert response.status_code == 200


def test_verify_deletion(conversation_id):
    """验证删除"""
    print("\n" + "="*60)
    print("CHAT TEST 5.5: 验证 - 已删除")
    print("="*60)

    response = requests.get(f"{BASE_URL}/api/conversations/{conversation_id}", timeout=10)

    print(f"[✓] 状态: {response.status_code} (期望 404)")
    assert response.status_code == 404


def test_error_empty_question():
    """测试空问题"""
    print("\n" + "="*60)
    print("CHAT TEST 6: 错误处理 - 空问题")
    print("="*60)

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={"question": ""},
        timeout=10
    )

    print(f"[✓] 响应状态: {response.status_code}")
    print(f"[✓] {response.json()}")
    assert response.status_code == 400


def test_error_whitespace_question():
    """测试纯空白问题"""
    print("\n" + "="*60)
    print("CHAT TEST 6b: 错误处理 - 纯空白问题")
    print("="*60)

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={"question": "   "},
        timeout=10
    )

    print(f"[✓] 响应状态: {response.status_code}")
    print(f"[✓] {response.json()}")
    assert response.status_code == 400


def test_error_missing_question():
    """测试缺少 question 字段"""
    print("\n" + "="*60)
    print("CHAT TEST 6c: 错误处理 - 缺少 question 字段")
    print("="*60)

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={},
        timeout=10
    )

    print(f"[✓] 响应状态: {response.status_code}")
    print(f"[✓] {response.json()}")
    assert response.status_code == 400


def test_error_invalid_json():
    """测试无效 JSON 请求"""
    print("\n" + "="*60)
    print("CHAT TEST 6d: 错误处理 - 无效 JSON")
    print("="*60)

    response = requests.post(
        f"{BASE_URL}/api/chat",
        data="not json",
        headers={"Content-Type": "application/json"},
        timeout=10
    )

    print(f"[✓] 响应状态: {response.status_code}")
    # Flask 的 get_json(silent=True) 返回 None，所以 question 为空
    assert response.status_code == 400


def test_error_chat_nonexistent_conversation_sse():
    """测试使用不存在的 conversation_id 聊天（SSE 错误事件）"""
    print("\n" + "="*60)
    print("CHAT TEST 6e: 错误处理 - SSE 不存在的 conversation_id")
    print("="*60)

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={"question": "测试", "conversation_id": fake_id},
        stream=True,
        timeout=30
    )

    got_error = False
    for event_type, data in parse_sse_stream(response):
        if event_type == "error":
            print(f"[✓ error] {data.get('message')}")
            got_error = True

    assert got_error, "应在 SSE 流中收到 error 事件"


def test_sse_response_headers():
    """测试 SSE 响应头"""
    print("\n" + "="*60)
    print("CHAT TEST 6f: SSE 响应头验证")
    print("="*60)

    payload = {"question": "你好"}
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload,
        stream=True,
        timeout=60
    )

    content_type = response.headers.get("Content-Type", "")
    cache_control = response.headers.get("Cache-Control", "")

    print(f"[✓] Content-Type: {content_type}")
    print(f"[✓] Cache-Control: {cache_control}")

    assert "text/event-stream" in content_type, "Content-Type 应为 text/event-stream"
    assert "no-cache" in cache_control, "Cache-Control 应包含 no-cache"

    # 消费流以完成请求
    for _ in parse_sse_stream(response):
        pass


def test_error_nonexistent_conversation():
    """测试不存在的对话"""
    print("\n" + "="*60)
    print("CHAT TEST 7: 错误处理 - 不存在的对话")
    print("="*60)

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.get(f"{BASE_URL}/api/conversations/{fake_id}", timeout=10)

    print(f"[✓] 响应状态: {response.status_code}")
    print(f"[✓] {response.json()}")
    assert response.status_code == 404


def test_error_delete_nonexistent():
    """测试删除不存在的对话"""
    print("\n" + "="*60)
    print("CHAT TEST 8: 错误处理 - 删除不存在的对话")
    print("="*60)

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.delete(f"{BASE_URL}/api/conversations/{fake_id}", timeout=10)

    print(f"[✓] 响应状态: {response.status_code}")
    print(f"[✓] {response.json()}")
    assert response.status_code == 404


def main():
    print("\n╔" + "="*58 + "╗")
    print("║" + "  对话模块 - API 综合测试".center(58) + "║")
    print("╚" + "="*58 + "╝")

    passed = 0
    failed = 0
    conv_id = None

    tests = [
        ("创建新对话", lambda: test_create_conversation()),
        ("获取对话列表", lambda: test_list_conversations(conv_id)),
        ("获取对话详情", lambda: test_get_conversation_detail(conv_id)),
        ("添加新轮次", lambda: test_add_round(conv_id)),
        ("验证多轮", lambda: test_verify_rounds(conv_id)),
        ("删除对话", lambda: test_delete_conversation(conv_id)),
        ("验证删除", lambda: test_verify_deletion(conv_id)),
        ("空问题", lambda: test_error_empty_question()),
        ("纯空白问题", lambda: test_error_whitespace_question()),
        ("缺少question", lambda: test_error_missing_question()),
        ("无效JSON", lambda: test_error_invalid_json()),
        ("SSE不存在对话", lambda: test_error_chat_nonexistent_conversation_sse()),
        ("SSE响应头", lambda: test_sse_response_headers()),
        ("不存在对话", lambda: test_error_nonexistent_conversation()),
        ("删不存在对话", lambda: test_error_delete_nonexistent()),
    ]

    for name, test_fn in tests:
        try:
            result = test_fn()
            if name == "创建新对话":
                conv_id = result
            passed += 1
        except Exception as e:
            print(f"[✗ FAIL] {name}: {e}")
            failed += 1
        time.sleep(0.5)

    print("\n" + "="*60)
    print(f"对话测试结果: {passed} 通过, {failed} 失败")
    print("="*60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
