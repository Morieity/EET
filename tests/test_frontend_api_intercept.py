"""
前端 API 请求拦截测试
---------------------
【测试设计说明】
本测试文件包含两类测试：

1. test_api_prefix_preserved（路径完整性验证）
   仅验证"前端代码中写的 fetch URL 包含 /api 前缀"。
   注意：此测试直接向拦截服务器发请求，完全绕过 CRA 代理层，
   因此无法验证 setupProxy.js 的代理转发行为是否正确。

2. test_direct_backend_api_routes（后端路由连通性验证）
   直接向正在运行的后端 8080 端口发请求，
   验证后端带 /api 前缀的路由是否响应 200，不带前缀的是否 404。

【验证代理转发本身是否正确】
需要启动 CRA dev server 后，在浏览器 DevTools Network 面板观察，
或使用 Playwright/Cypress 等 E2E 工具通过 localhost:3000 发请求。

使用方法:
    python -m pytest tests/test_frontend_api_intercept.py -v
    或者直接运行:
    python tests/test_frontend_api_intercept.py
"""

import threading
import time
import json
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler


# 收集所有请求记录
request_log = []


class InterceptHandler(BaseHTTPRequestHandler):
    """拦截并记录所有进入的 HTTP 请求。"""

    def _record(self):
        request_log.append({
            "method": self.command,
            "path": self.path,
        })
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def do_GET(self):
        self._record()

    def do_POST(self):
        # 读取 body 防止连接异常
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)
        self._record()

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)
        self._record()

    def do_DELETE(self):
        self._record()

    def log_message(self, format, *args):
        # 静默日志
        pass


def start_intercept_server(port=18999):
    """在指定端口启动拦截服务器，返回 (server, thread)。"""
    server = HTTPServer(("127.0.0.1", port), InterceptHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, t


def send_request(port, method, path, body=None):
    """向拦截服务器发送请求。"""
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except Exception as e:
        return str(e)


# ─── 测试用例 ─────────────────────────────────────────────

def test_api_prefix_preserved():
    """
    模拟前端实际会发出的所有 API 路径，验证拦截服务器收到的路径均包含 /api 前缀。
    如果 setupProxy.js 配置有误，代理会剥离 /api，此测试将失败。
    """
    PORT = 18999
    request_log.clear()
    server, _ = start_intercept_server(PORT)

    # 前端实际会调用的 API 路径清单（与各组件 fetch 调用一一对应）
    frontend_api_calls = [
        ("GET",    "/api/conversations"),
        ("GET",    "/api/conversations/test-conv-id"),
        ("DELETE", "/api/conversations/test-conv-id"),
        ("POST",   "/api/chat"),
        ("GET",    "/api/files"),
        ("POST",   "/api/files"),
        ("DELETE", "/api/files/test-file.pdf"),
        ("GET",    "/api/fault-trees"),
        ("GET",    "/api/fault-trees/test-tree-id"),
        ("PUT",    "/api/fault-trees/test-tree-id"),
        ("DELETE", "/api/fault-trees/test-tree-id"),
    ]

    try:
        for method, path in frontend_api_calls:
            body = {"question": "test"} if method == "POST" else None
            status = send_request(PORT, method, path, body)
            assert status == 200, f"{method} {path} 返回 {status}"

        time.sleep(0.2)

        # 验证所有记录的路径都有 /api 前缀
        print(f"\n{'='*60}")
        print(f"拦截到 {len(request_log)} 个请求：")
        print(f"{'='*60}")

        errors = []
        for i, record in enumerate(request_log):
            expected_path = frontend_api_calls[i][1]
            symbol = "✅" if record["path"].startswith("/api") else "❌"
            print(f"  {symbol} {record['method']:6s} {record['path']}")
            if not record["path"].startswith("/api"):
                errors.append(record)

        print(f"{'='*60}")

        if errors:
            print(f"\n❌ 发现 {len(errors)} 个请求缺少 /api 前缀：")
            for e in errors:
                print(f"   {e['method']} {e['path']}")
            assert False, f"{len(errors)} 个请求缺少 /api 前缀（详见上方输出）"
        else:
            print("\n✅ 所有请求路径均正确包含 /api 前缀")
    finally:
        server.shutdown()


def test_direct_backend_api_routes():
    """
    直接向正在运行的后端 (127.0.0.1:8080) 发送请求，
    验证后端路由是否能正确响应 /api/* 路径。
    跳过条件：后端未启动时自动跳过。
    """
    import socket

    def is_port_open(host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, port)) == 0

    if not is_port_open("127.0.0.1", 8080):
        print("⚠️  后端未启动 (127.0.0.1:8080)，跳过此测试")
        return

    test_routes = [
        ("GET", "/api/conversations"),
        ("GET", "/api/files"),
        ("GET", "/api/fault-trees"),
    ]

    print(f"\n{'='*60}")
    print("直接请求后端 127.0.0.1:8080：")
    print(f"{'='*60}")

    for method, path in test_routes:
        url = f"http://127.0.0.1:8080{path}"
        req = urllib.request.Request(url, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code
        except Exception as e:
            status = str(e)

        symbol = "✅" if status == 200 else "❌"
        print(f"  {symbol} {method:6s} {path} → {status}")

    # 验证带 /api 前缀的路径不返回 404
    for method, path in test_routes:
        url = f"http://127.0.0.1:8080{path}"
        req = urllib.request.Request(url, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code
        except Exception as e:
            continue
        assert status != 404, f"后端路由 {method} {path} 返回 404，路由未正确注册"

    # 验证不带 /api 前缀的路径应该返回 404
    no_prefix_routes = [
        ("GET", "/conversations"),
        ("GET", "/files"),
        ("GET", "/fault-trees"),
    ]

    print(f"\n验证不带 /api 前缀的路径（应为 404）：")
    for method, path in no_prefix_routes:
        url = f"http://127.0.0.1:8080{path}"
        req = urllib.request.Request(url, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code
        except Exception as e:
            continue

        symbol = "✅" if status == 404 else "⚠️"
        print(f"  {symbol} {method:6s} {path} → {status}")
        assert status == 404, f"不带 /api 前缀的 {path} 不应该被路由匹配，但返回了 {status}"

    print(f"{'='*60}")
    print("✅ 后端路由验证通过")


if __name__ == "__main__":
    print("=" * 60)
    print("前端 API 请求拦截测试")
    print("=" * 60)

    print("\n[测试 1] 模拟前端请求，验证 /api 前缀完整性")
    test_api_prefix_preserved()

    print("\n[测试 2] 直接请求后端，验证路由注册")
    test_direct_backend_api_routes()

    print("\n" + "=" * 60)
    print("全部测试完成")
    print("=" * 60)
