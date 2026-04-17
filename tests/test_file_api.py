#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文档模块 API 测试（集成测试，需要后端服务运行）"""

import os
import json
import time
import requests
import pytest


def _server_is_running():
    try:
        requests.get("http://127.0.0.1:8080/api/conversations", timeout=2)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _server_is_running(),
    reason="集成测试需要后端服务运行在 127.0.0.1:8080",
)

BASE_URL = "http://127.0.0.1:8080"
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TEST_DIR)


def _create_test_file(filename: str, content: str) -> str:
    """在 tests/ 目录下创建临时测试文件"""
    filepath = os.path.join(TEST_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def _cleanup_test_file(filename: str):
    filepath = os.path.join(TEST_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)


def test_upload_txt_file():
    """测试上传 .txt 文件"""
    print("\n" + "="*60)
    print("FILE TEST 1: POST /api/files - 上传 .txt 文件")
    print("="*60)

    test_filename = "test_doc.txt"
    test_content = "这是一个测试文档。\n用于验证 RAG 系统的文档上传和向量化功能。\n" * 10
    filepath = _create_test_file(test_filename, test_content)

    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/files",
                files={"file": (test_filename, f, "text/plain")},
                timeout=10
            )

        print(f"[✓] 响应状态: {response.status_code}")
        result = response.json()
        print(f"[✓] 文件ID: {result.get('id', 'N/A')}")
        print(f"[✓] 文件名: {result.get('file_name')}")
        print(f"[✓] 状态: {result.get('status')}")

        assert response.status_code == 202, f"期望 202，实际 {response.status_code}"
        assert result["file_name"] == test_filename
        assert result["status"] == "pending"

        return test_filename
    finally:
        _cleanup_test_file(test_filename)


def test_upload_md_file():
    """测试上传 .md 文件"""
    print("\n" + "="*60)
    print("FILE TEST 2: POST /api/files - 上传 .md 文件")
    print("="*60)

    test_filename = "test_readme.md"
    test_content = "# Test Document\n\n## Section 1\nThis is a test markdown file.\n" * 5
    filepath = _create_test_file(test_filename, test_content)

    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/files",
                files={"file": (test_filename, f, "text/markdown")},
                timeout=10
            )

        print(f"[✓] 响应状态: {response.status_code}")
        result = response.json()
        print(f"[✓] 文件名: {result.get('file_name')}")
        print(f"[✓] 文件类型: {result.get('file_type')}")

        assert response.status_code == 202
        return test_filename
    finally:
        _cleanup_test_file(test_filename)


def test_upload_unsupported_file():
    """测试上传不支持的文件类型"""
    print("\n" + "="*60)
    print("FILE TEST 3: POST /api/files - 上传不支持的文件类型")
    print("="*60)

    test_filename = "test.exe"
    filepath = _create_test_file(test_filename, "invalid")

    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/files",
                files={"file": (test_filename, f, "application/octet-stream")},
                timeout=10
            )

        print(f"[✓] 响应状态: {response.status_code}")
        result = response.json()
        print(f"[✓] 错误信息: {result.get('error')}")

        assert response.status_code == 400
        assert "Unsupported" in result.get("error", "")
    finally:
        _cleanup_test_file(test_filename)


def test_upload_no_file():
    """测试不提供文件"""
    print("\n" + "="*60)
    print("FILE TEST 4: POST /api/files - 不提供文件")
    print("="*60)

    response = requests.post(f"{BASE_URL}/api/files", timeout=10)

    print(f"[✓] 响应状态: {response.status_code}")
    result = response.json()
    print(f"[✓] 错误信息: {result.get('error')}")

    assert response.status_code == 400


def test_list_files():
    """测试获取文件列表"""
    print("\n" + "="*60)
    print("FILE TEST 5: GET /api/files - 获取文件列表")
    print("="*60)

    response = requests.get(f"{BASE_URL}/api/files", timeout=10)
    files = response.json()

    print(f"[✓] 响应状态: {response.status_code}")
    print(f"[✓] 文件数量: {len(files)}")

    for i, f in enumerate(files[:5], 1):
        print(f"    {i}. {f['file_name']} ({f['status']})")

    assert response.status_code == 200
    assert isinstance(files, list)

    return files


def test_wait_for_embedding(file_name: str):
    """等待文件向量化完成"""
    print("\n" + "="*60)
    print(f"FILE TEST 6: GET /api/files/{file_name}/status - 等待向量化")
    print("="*60)

    response = requests.get(
        f"{BASE_URL}/api/files/{file_name}/status",
        stream=True,
        timeout=130
    )

    print(f"[✓] SSE 连接建立: {response.status_code}")
    final_status = None

    for line in response.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            data = json.loads(line[5:].strip())
            status = data.get("status")
            print(f"[✓] 状态更新: {status}")
            final_status = status
            if status in ("embedded", "failed", "timeout"):
                break

    print(f"[✓] 最终状态: {final_status}")
    return final_status


def test_delete_file(file_name: str):
    """测试删除文件"""
    print("\n" + "="*60)
    print(f"FILE TEST 7: DELETE /api/files/{file_name} - 删除文件")
    print("="*60)

    response = requests.delete(f"{BASE_URL}/api/files/{file_name}", timeout=10)

    print(f"[✓] 响应状态: {response.status_code}")
    result = response.json()
    print(f"[✓] {result}")

    assert response.status_code == 200


def test_delete_nonexistent_file():
    """测试删除不存在的文件"""
    print("\n" + "="*60)
    print("FILE TEST 8: DELETE /api/files/<不存在> - 错误处理")
    print("="*60)

    response = requests.delete(f"{BASE_URL}/api/files/nonexistent.pdf", timeout=10)

    print(f"[✓] 响应状态: {response.status_code}")
    result = response.json()
    print(f"[✓] {result}")

    assert response.status_code == 404


def main():
    print("\n╔" + "="*58 + "╗")
    print("║" + "  文档模块 - API 综合测试".center(58) + "║")
    print("╚" + "="*58 + "╝")

    passed = 0
    failed = 0

    tests = [
        ("上传 .txt 文件", test_upload_txt_file),
        ("上传 .md 文件", test_upload_md_file),
        ("上传不支持类型", test_upload_unsupported_file),
        ("不提供文件", test_upload_no_file),
        ("获取文件列表", test_list_files),
        ("删除不存在文件", test_delete_nonexistent_file),
    ]

    txt_name = None
    md_name = None

    for name, test_fn in tests:
        try:
            result = test_fn()
            if name == "上传 .txt 文件":
                txt_name = result
            elif name == "上传 .md 文件":
                md_name = result
            passed += 1
        except Exception as e:
            print(f"[✗ FAIL] {name}: {e}")
            failed += 1

    # 等待向量化并删除
    if txt_name:
        try:
            print("\n--- 等待 txt 文件向量化 ---")
            test_wait_for_embedding(txt_name)
            passed += 1
        except Exception as e:
            print(f"[✗ FAIL] 等待向量化: {e}")
            failed += 1

        try:
            test_delete_file(txt_name)
            passed += 1
        except Exception as e:
            print(f"[✗ FAIL] 删除 txt 文件: {e}")
            failed += 1

    if md_name:
        try:
            print("\n--- 等待 md 文件向量化 ---")
            test_wait_for_embedding(md_name)
            passed += 1
        except Exception as e:
            print(f"[✗ FAIL] 等待向量化: {e}")
            failed += 1

        try:
            test_delete_file(md_name)
            passed += 1
        except Exception as e:
            print(f"[✗ FAIL] 删除 md 文件: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"文档测试结果: {passed} 通过, {failed} 失败")
    print("="*60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
