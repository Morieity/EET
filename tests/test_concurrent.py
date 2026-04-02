#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""并发对话测试 - 模拟多个终端同时进行对话"""

import json
import time
import threading
import requests

BASE_URL = "http://127.0.0.1:8080"

results = {}
lock = threading.Lock()


def parse_sse_stream(response):
    """解析 SSE 流"""
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


def chat_worker(worker_id: int, question: str, conversation_id: str | None = None):
    """单个对话 worker，模拟一个终端"""
    start_time = time.time()
    payload = {"question": question}
    if conversation_id:
        payload["conversation_id"] = conversation_id

    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=120
        )
        response.raise_for_status()

        conv_id = None
        full_answer = ""
        token_count = 0

        for event_type, data in parse_sse_stream(response):
            if event_type == "conversation":
                conv_id = data.get("conversation_id")
            elif event_type == "token":
                full_answer += data.get("content", "")
                token_count += 1
            elif event_type == "error":
                with lock:
                    results[worker_id] = {
                        "status": "error",
                        "message": data.get("message"),
                        "duration": time.time() - start_time,
                    }
                return

        duration = time.time() - start_time
        with lock:
            results[worker_id] = {
                "status": "success",
                "conversation_id": conv_id,
                "answer_length": len(full_answer),
                "token_count": token_count,
                "duration": round(duration, 2),
                "answer_preview": full_answer[:50],
            }

    except Exception as e:
        with lock:
            results[worker_id] = {
                "status": "error",
                "message": str(e),
                "duration": round(time.time() - start_time, 2),
            }


def test_concurrent_new_conversations(n: int = 5):
    """测试 N 个终端同时创建新对话"""
    print("\n" + "="*60)
    print(f"CONCURRENT TEST 1: {n} 个终端同时创建新对话")
    print("="*60)

    results.clear()
    threads = []

    questions = [
        "什么是机器学习？",
        "请解释什么是 Python？",
        "什么是 RESTful API？",
        "请介绍 Flask 框架",
        "什么是向量数据库？",
        "什么是自然语言处理？",
        "请解释什么是 Docker？",
        "什么是微服务架构？",
        "什么是 CI/CD？",
        "请介绍 Git 版本控制",
    ]

    start_time = time.time()

    for i in range(n):
        t = threading.Thread(
            target=chat_worker,
            args=(i, questions[i % len(questions)])
        )
        threads.append(t)

    # 同时启动所有线程
    for t in threads:
        t.start()

    # 等待所有线程完成
    for t in threads:
        t.join(timeout=120)

    total_duration = round(time.time() - start_time, 2)

    # 统计结果
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    error_count = sum(1 for r in results.values() if r["status"] == "error")

    print(f"\n总耗时: {total_duration}s")
    print(f"成功: {success_count}/{n}, 失败: {error_count}/{n}")

    for wid in sorted(results.keys()):
        r = results[wid]
        if r["status"] == "success":
            print(f"  Worker {wid}: {r['duration']}s, {r['answer_length']}字, "
                  f"答: {r['answer_preview']}...")
        else:
            print(f"  Worker {wid}: [FAIL] {r['message']}")

    # 清理创建的对话
    conv_ids = [r["conversation_id"] for r in results.values()
                if r["status"] == "success" and r.get("conversation_id")]
    for cid in conv_ids:
        requests.delete(f"{BASE_URL}/api/conversations/{cid}", timeout=10)

    print(f"  已清理 {len(conv_ids)} 个测试对话")

    return success_count, error_count


def test_concurrent_same_conversation(n: int = 3):
    """测试 N 个终端在同一个对话中交替发言"""
    print("\n" + "="*60)
    print(f"CONCURRENT TEST 2: {n} 个终端在同一对话中发言")
    print("="*60)

    # 先创建一个对话
    payload = {"question": "初始化对话"}
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60
    )
    content = response.content.decode("utf-8")
    conv_id = None
    for line in content.split("\n"):
        if line.startswith("data:"):
            try:
                data = json.loads(line[5:].strip())
                if "conversation_id" in data:
                    conv_id = data["conversation_id"]
            except:
                pass

    if not conv_id:
        print("[✗] 无法创建初始对话")
        return 0, 1

    print(f"  初始对话创建成功: {conv_id[:20]}...")
    time.sleep(1)

    results.clear()
    threads = []

    questions = [
        f"第 {i+1} 个终端的问题：你好" for i in range(n)
    ]

    start_time = time.time()
    for i in range(n):
        t = threading.Thread(
            target=chat_worker,
            args=(i, questions[i], conv_id)
        )
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=120)

    total_duration = round(time.time() - start_time, 2)

    success_count = sum(1 for r in results.values() if r["status"] == "success")
    error_count = sum(1 for r in results.values() if r["status"] == "error")

    print(f"\n总耗时: {total_duration}s")
    print(f"成功: {success_count}/{n}, 失败: {error_count}/{n}")

    for wid in sorted(results.keys()):
        r = results[wid]
        if r["status"] == "success":
            print(f"  Worker {wid}: {r['duration']}s, {r['answer_length']}字")
        else:
            print(f"  Worker {wid}: [FAIL] {r['message']}")

    # 验证对话轮次数
    try:
        resp = requests.get(f"{BASE_URL}/api/conversations/{conv_id}", timeout=10)
        conv = resp.json()
        total_rounds = len(conv.get("rounds", []))
        print(f"  对话总轮次: {total_rounds} (预期 {1 + success_count})")
    except:
        pass

    # 清理
    requests.delete(f"{BASE_URL}/api/conversations/{conv_id}", timeout=10)
    print(f"  已清理测试对话")

    return success_count, error_count


def test_concurrent_crud():
    """测试并发读写 - 一个线程写，多个线程读"""
    print("\n" + "="*60)
    print("CONCURRENT TEST 3: 并发读写操作")
    print("="*60)

    # 先创建几个对话
    conv_ids = []
    for i in range(3):
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"question": f"预创建对话 {i}"},
            timeout=60
        )
        content = response.content.decode("utf-8")
        for line in content.split("\n"):
            if line.startswith("data:"):
                try:
                    data = json.loads(line[5:].strip())
                    if "conversation_id" in data:
                        conv_ids.append(data["conversation_id"])
                except:
                    pass
        time.sleep(0.5)

    print(f"  预创建了 {len(conv_ids)} 个对话")

    read_results = []
    read_errors = []

    def reader_worker(idx):
        try:
            resp = requests.get(f"{BASE_URL}/api/conversations", timeout=10)
            resp.raise_for_status()
            with lock:
                read_results.append(len(resp.json()))
        except Exception as e:
            with lock:
                read_errors.append(str(e))

    def detail_reader(conv_id, idx):
        try:
            resp = requests.get(f"{BASE_URL}/api/conversations/{conv_id}", timeout=10)
            resp.raise_for_status()
            with lock:
                read_results.append(1)
        except Exception as e:
            with lock:
                read_errors.append(str(e))

    # 同时发起多个读请求
    threads = []
    for i in range(5):
        threads.append(threading.Thread(target=reader_worker, args=(i,)))

    for cid in conv_ids:
        threads.append(threading.Thread(target=detail_reader, args=(cid, 0)))

    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    duration = round(time.time() - start, 2)

    print(f"  并发读: {len(read_results)} 成功, {len(read_errors)} 失败, 耗时 {duration}s")

    # 清理
    for cid in conv_ids:
        requests.delete(f"{BASE_URL}/api/conversations/{cid}", timeout=10)
    print(f"  已清理 {len(conv_ids)} 个测试对话")

    return len(read_results), len(read_errors)


def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + "  并发对话测试套件".center(58) + "║")
    print("╚" + "="*58 + "╝")

    total_success = 0
    total_fail = 0

    # Test 1: 5 个终端同时创建
    s, f = test_concurrent_new_conversations(5)
    total_success += s
    total_fail += f
    time.sleep(2)

    # Test 2: 3 个终端在同一对话
    s, f = test_concurrent_same_conversation(3)
    total_success += s
    total_fail += f
    time.sleep(2)

    # Test 3: 并发读写
    s, f = test_concurrent_crud()
    total_success += s
    total_fail += f

    print("\n" + "="*60)
    print(f"并发测试总结: {total_success} 操作成功, {total_fail} 操作失败")
    if total_fail == 0:
        print("✓ 系统可以支持多终端并发对话!")
    else:
        print("⚠ 部分并发操作失败，需要进一步优化")
    print("="*60 + "\n")

    return total_fail == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
