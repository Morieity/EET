#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件夹管理模块 API 测试 —— 覆盖文件夹增删改查及文件归类操作"""

import os
import time
import requests

BASE_URL = "http://127.0.0.1:8080"
TEST_DIR = os.path.dirname(os.path.abspath(__file__))


# ────────────────── 辅助函数 ──────────────────

def _create_test_file(filename: str, content: str) -> str:
    filepath = os.path.join(TEST_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def _cleanup_test_file(filename: str):
    filepath = os.path.join(TEST_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)


def _upload_file(filename: str, content: str) -> dict:
    """上传一个测试文件并等待向量化完成，返回文件实体 dict。"""
    filepath = _create_test_file(filename, content)
    try:
        with open(filepath, "rb") as f:
            resp = requests.post(
                f"{BASE_URL}/api/files",
                files={"file": (filename, f, "text/plain")},
                timeout=10,
            )
        assert resp.status_code == 202, f"上传失败: {resp.status_code} {resp.text}"
        file_entity = resp.json()

        # 等待向量化完成（最多 60 秒）
        for _ in range(60):
            updated = requests.get(f"{BASE_URL}/api/files", timeout=5).json()
            match = [fe for fe in updated if fe["id"] == file_entity["id"]]
            if match and match[0]["status"] in ("embedded", "failed"):
                return match[0]
            time.sleep(1)
        return file_entity
    finally:
        _cleanup_test_file(filename)


def _delete_file(file_name: str):
    requests.delete(f"{BASE_URL}/api/files/{file_name}", timeout=10)


# ────────────────── 文件夹 CRUD 测试 ──────────────────

def test_create_folder():
    """测试 1: 创建文件夹"""
    print("\n" + "=" * 60)
    print("TEST 1: POST /api/folders — 创建文件夹")
    print("=" * 60)

    resp = requests.post(f"{BASE_URL}/api/folders", json={"name": "安全分析"}, timeout=10)
    result = resp.json()

    print(f"[✓] 状态码: {resp.status_code}")
    print(f"[✓] 文件夹: id={result.get('id')}, name={result.get('name')}")

    assert resp.status_code == 201
    assert result["name"] == "安全分析"
    return result["id"]


def test_create_folder_duplicate():
    """测试 2: 创建重名文件夹应返回 409"""
    print("\n" + "=" * 60)
    print("TEST 2: POST /api/folders — 重名文件夹")
    print("=" * 60)

    resp = requests.post(f"{BASE_URL}/api/folders", json={"name": "安全分析"}, timeout=10)
    print(f"[✓] 状态码: {resp.status_code}")
    print(f"[✓] 错误: {resp.json().get('error')}")
    assert resp.status_code == 409


def test_create_folder_empty():
    """测试 3: 空名称应返回 400"""
    print("\n" + "=" * 60)
    print("TEST 3: POST /api/folders — 空名称")
    print("=" * 60)

    resp = requests.post(f"{BASE_URL}/api/folders", json={"name": ""}, timeout=10)
    print(f"[✓] 状态码: {resp.status_code}")
    print(f"[✓] 错误: {resp.json().get('error')}")
    assert resp.status_code == 400


def test_list_folders():
    """测试 4: 获取文件夹列表"""
    print("\n" + "=" * 60)
    print("TEST 4: GET /api/folders — 文件夹列表")
    print("=" * 60)

    resp = requests.get(f"{BASE_URL}/api/folders", timeout=10)
    folders = resp.json()

    print(f"[✓] 状态码: {resp.status_code}")
    print(f"[✓] 文件夹数: {len(folders)}")
    for f in folders:
        print(f"    - {f['name']} (文件数: {len(f.get('files', []))})")

    assert resp.status_code == 200
    assert isinstance(folders, list)
    assert len(folders) >= 1


def test_rename_folder(folder_id: str):
    """测试 5: 重命名文件夹"""
    print("\n" + "=" * 60)
    print("TEST 5: PATCH /api/folders/<id> — 重命名")
    print("=" * 60)

    resp = requests.patch(
        f"{BASE_URL}/api/folders/{folder_id}",
        json={"name": "故障分析"},
        timeout=10,
    )
    result = resp.json()

    print(f"[✓] 状态码: {resp.status_code}")
    print(f"[✓] 新名称: {result.get('name')}")

    assert resp.status_code == 200
    assert result["name"] == "故障分析"


def test_rename_nonexistent():
    """测试 6: 重命名不存在的文件夹"""
    print("\n" + "=" * 60)
    print("TEST 6: PATCH /api/folders/<不存在> — 404")
    print("=" * 60)

    resp = requests.patch(
        f"{BASE_URL}/api/folders/no-such-id",
        json={"name": "x"},
        timeout=10,
    )
    print(f"[✓] 状态码: {resp.status_code}")
    assert resp.status_code == 404


# ────────────────── 文件归类测试 ──────────────────

def test_move_file_to_folder(folder_id: str, file_id: str):
    """测试 7: 将文件移入文件夹"""
    print("\n" + "=" * 60)
    print("TEST 7: POST /api/folders/<id>/files — 移入文件")
    print("=" * 60)

    resp = requests.post(
        f"{BASE_URL}/api/folders/{folder_id}/files",
        json={"file_id": file_id},
        timeout=10,
    )
    print(f"[✓] 状态码: {resp.status_code}")
    print(f"[✓] {resp.json()}")
    assert resp.status_code == 200


def test_verify_file_in_folder(folder_id: str, file_id: str):
    """测试 8: 验证文件已出现在文件夹列表中"""
    print("\n" + "=" * 60)
    print("TEST 8: GET /api/folders — 验证文件归类")
    print("=" * 60)

    resp = requests.get(f"{BASE_URL}/api/folders", timeout=10)
    folders = resp.json()
    target = [f for f in folders if f["id"] == folder_id]

    assert len(target) == 1, "目标文件夹未找到"
    file_ids = [fi["id"] for fi in target[0].get("files", [])]
    print(f"[✓] 文件夹 '{target[0]['name']}' 中的文件: {file_ids}")
    assert file_id in file_ids, "文件未出现在文件夹中"
    print(f"[✓] 文件 {file_id} 已确认在文件夹内")


def test_file_list_has_folder_id(file_id: str, folder_id: str):
    """测试 9: 文件列表中 folder_id 字段正确"""
    print("\n" + "=" * 60)
    print("TEST 9: GET /api/files — 文件的 folder_id 字段")
    print("=" * 60)

    resp = requests.get(f"{BASE_URL}/api/files", timeout=10)
    files = resp.json()
    target = [f for f in files if f["id"] == file_id]

    assert len(target) == 1
    print(f"[✓] 文件 folder_id = {target[0].get('folder_id')}")
    assert target[0].get("folder_id") == folder_id


def test_remove_file_from_folder(file_id: str):
    """测试 10: 将文件移出文件夹"""
    print("\n" + "=" * 60)
    print("TEST 10: POST /api/folders/unfile — 移出文件")
    print("=" * 60)

    resp = requests.post(
        f"{BASE_URL}/api/folders/unfile",
        json={"file_id": file_id},
        timeout=10,
    )
    print(f"[✓] 状态码: {resp.status_code}")
    assert resp.status_code == 200

    # 确认 folder_id 已清空
    files = requests.get(f"{BASE_URL}/api/files", timeout=10).json()
    target = [f for f in files if f["id"] == file_id]
    assert target[0].get("folder_id") is None
    print(f"[✓] 文件 folder_id 已清空")


# ────────────────── 删除文件夹测试 ──────────────────

def test_delete_folder(folder_id: str):
    """测试 11: 删除文件夹"""
    print("\n" + "=" * 60)
    print("TEST 11: DELETE /api/folders/<id> — 删除文件夹")
    print("=" * 60)

    resp = requests.delete(f"{BASE_URL}/api/folders/{folder_id}", timeout=10)
    print(f"[✓] 状态码: {resp.status_code}")
    assert resp.status_code == 200

    # 确认已删除
    folders = requests.get(f"{BASE_URL}/api/folders", timeout=10).json()
    assert all(f["id"] != folder_id for f in folders)
    print(f"[✓] 文件夹已从列表中移除")


def test_delete_nonexistent():
    """测试 12: 删除不存在的文件夹"""
    print("\n" + "=" * 60)
    print("TEST 12: DELETE /api/folders/<不存在> — 404")
    print("=" * 60)

    resp = requests.delete(f"{BASE_URL}/api/folders/no-such-id", timeout=10)
    print(f"[✓] 状态码: {resp.status_code}")
    assert resp.status_code == 404


# ────────────────── 主流程 ──────────────────

def main():
    print("\n╔" + "=" * 58 + "╗")
    print("║" + "  文件夹管理 + 文件归类 — API 综合测试".center(50) + "║")
    print("╚" + "=" * 58 + "╝")

    passed = 0
    failed = 0
    folder_id = None
    file_entity = None

    def _run(name, fn, *args):
        nonlocal passed, failed
        try:
            result = fn(*args)
            passed += 1
            return result
        except Exception as e:
            print(f"[✗ FAIL] {name}: {e}")
            failed += 1
            return None

    # ── 上传一个测试文件 ──
    print("\n>>> 准备：上传测试文件 <<<")
    file_entity = _run("上传测试文件", _upload_file, "folder_test.txt", "文件夹功能测试文本。\n" * 20)
    file_id = file_entity["id"] if file_entity else None
    file_name = file_entity["file_name"] if file_entity else None
    if file_entity:
        print(f"[✓] 测试文件就绪: id={file_id}, status={file_entity['status']}")

    # ── 文件夹 CRUD ──
    print("\n>>> 文件夹 CRUD 测试 <<<")
    folder_id = _run("创建文件夹", test_create_folder)
    _run("重名文件夹", test_create_folder_duplicate)
    _run("空名称", test_create_folder_empty)
    _run("文件夹列表", test_list_folders)
    if folder_id:
        _run("重命名", test_rename_folder, folder_id)
    _run("重命名不存在", test_rename_nonexistent)

    # ── 文件归类 ──
    if folder_id and file_id:
        print("\n>>> 文件归类测试 <<<")
        _run("移入文件", test_move_file_to_folder, folder_id, file_id)
        _run("验证归类", test_verify_file_in_folder, folder_id, file_id)
        _run("文件 folder_id", test_file_list_has_folder_id, file_id, folder_id)
        _run("移出文件", test_remove_file_from_folder, file_id)
    else:
        print("\n[⚠ SKIP] 缺少文件夹或文件，跳过归类测试")

    # ── 删除 ──
    print("\n>>> 删除测试 <<<")
    if folder_id:
        _run("删除文件夹", test_delete_folder, folder_id)
    _run("删除不存在", test_delete_nonexistent)

    # ── 清理测试文件 ──
    if file_name:
        _delete_file(file_name)
        print(f"\n[清理] 已删除测试文件: {file_name}")

    # ── 汇总 ──
    print("\n" + "=" * 60)
    print(f"结果: {passed} 通过, {failed} 失败")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
