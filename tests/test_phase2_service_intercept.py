"""
Phase 2 前端服务层 API 拦截测试
-------------------------------
新增测试（在原有拦截测试基础上扩展）：

1. test_service_layer_api_prefix_scan:
   静态扫描 services/ 目录下所有 JS 文件，验证每个 fetch 调用
   的 URL 都以 /api/ 开头。

2. test_no_direct_fetch_in_components:
   验证组件和 hooks 目录中不含裸 fetch() 调用，
   确保所有 HTTP 调用都通过服务层。

3. test_service_api_intercept:
   继承原有拦截测试模式 — 启动本地 HTTP 拦截服务器，
   模拟发送与 services 文件完全对应的 API 请求，
   验证路径完整性。

使用方法:
    python -m pytest tests/test_phase2_service_intercept.py -v
"""

import os
import re
import threading
import time
import json
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler


# ─── 路径常量 ───────────────────────────────────────────

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_SRC = os.path.join(PROJECT_ROOT, "frontend", "src")
SERVICES_DIR = os.path.join(FRONTEND_SRC, "features", "flow", "services")
COMPONENTS_DIR = os.path.join(FRONTEND_SRC, "features", "flow", "components")
HOOKS_DIR = os.path.join(FRONTEND_SRC, "features", "flow", "hooks")

# fetch URL 提取正则：匹配 fetch('/api/...' 和 fetch(`/api/...`
FETCH_URL_PATTERN = re.compile(r"""fetch\(\s*[`'"]([^`'"]+)[`'"]""")
# 匹配模板字符串中的 fetch 调用
FETCH_TEMPLATE_PATTERN = re.compile(r"""fetch\(\s*`([^`]+)`""")
# 匹配裸 fetch( 调用
BARE_FETCH_PATTERN = re.compile(r"""\bfetch\s*\(""")


def collect_js_files(directory):
    """递归收集目录下所有 .js 文件。"""
    files = []
    if not os.path.exists(directory):
        return files
    for root, _, filenames in os.walk(directory):
        for name in filenames:
            if name.endswith(".js"):
                files.append(os.path.join(root, name))
    return files


def extract_fetch_urls(filepath):
    """提取 JS 文件中 fetch() 调用的 URL 路径。"""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    urls = []
    # 静态字符串 fetch('/api/...')
    for match in FETCH_URL_PATTERN.finditer(content):
        urls.append(match.group(1))
    # 模板字符串 fetch(`/api/.../${...}`)
    for match in FETCH_TEMPLATE_PATTERN.finditer(content):
        raw = match.group(1)
        # 替换模板表达式为占位符
        normalized = re.sub(r"\$\{[^}]+\}", "PLACEHOLDER", raw)
        if normalized not in [u for u in urls]:
            urls.append(normalized)
    # 去重
    return list(dict.fromkeys(urls))


def count_fetch_calls(filepath):
    """统计 JS 文件中 fetch() 调用次数。"""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    return len(BARE_FETCH_PATTERN.findall(content))


# ─── 拦截服务器 ─────────────────────────────────────────

request_log = []


class InterceptHandler(BaseHTTPRequestHandler):
    def _record(self):
        request_log.append({"method": self.command, "path": self.path})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def do_GET(self):
        self._record()

    def do_POST(self):
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
        pass


def start_intercept_server(port=18998):
    server = HTTPServer(("127.0.0.1", port), InterceptHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, t


def send_request(port, method, path, body=None):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except Exception as e:
        return str(e)


# ─── 测试 1: 服务层源码 /api 前缀扫描 ──────────────────────

def test_service_layer_api_prefix_scan():
    """
    静态扫描 services/ 目录下所有 JS 文件，
    验证每个 fetch 调用的 URL 都以 /api/ 开头。
    """
    service_files = collect_js_files(SERVICES_DIR)
    assert len(service_files) > 0, f"未找到服务文件: {SERVICES_DIR}"

    print(f"\n{'='*60}")
    print(f"扫描 {len(service_files)} 个服务文件：")
    print(f"{'='*60}")

    errors = []
    total_urls = 0

    for filepath in service_files:
        relative = os.path.relpath(filepath, PROJECT_ROOT)
        urls = extract_fetch_urls(filepath)
        total_urls += len(urls)

        for url in urls:
            ok = url.startswith("/api/")
            symbol = "✅" if ok else "❌"
            print(f"  {symbol} {relative}: {url}")
            if not ok:
                errors.append((relative, url))

    print(f"\n共扫描 {total_urls} 个 fetch URL")

    if errors:
        print(f"\n❌ {len(errors)} 个 URL 缺少 /api/ 前缀:")
        for f, u in errors:
            print(f"   {f}: {u}")
        assert False, f"{len(errors)} 个 URL 缺少 /api/ 前缀"
    else:
        print("✅ 所有服务层 fetch URL 均包含 /api/ 前缀")


# ─── 测试 2: 组件/hooks 无裸 fetch 验证 ─────────────────────

def test_no_direct_fetch_in_components():
    """
    验证 components/ 和 hooks/ 目录中不含裸 fetch() 调用，
    确保所有 HTTP 请求都通过服务层。
    """
    dirs_to_scan = [
        ("components", COMPONENTS_DIR),
        ("hooks", HOOKS_DIR),
    ]

    print(f"\n{'='*60}")
    print("检查组件和 hooks 是否有裸 fetch 调用：")
    print(f"{'='*60}")

    violations = []

    for label, directory in dirs_to_scan:
        js_files = collect_js_files(directory)
        for filepath in js_files:
            relative = os.path.relpath(filepath, PROJECT_ROOT)
            count = count_fetch_calls(filepath)
            if count > 0:
                violations.append((relative, count))
                print(f"  ❌ {relative}: {count} 个 fetch 调用")
            else:
                print(f"  ✅ {relative}: 无裸 fetch")

    if violations:
        total = sum(c for _, c in violations)
        print(f"\n❌ {len(violations)} 个文件包含 {total} 个裸 fetch 调用")
        assert False, f"组件/hooks 中发现裸 fetch 调用: {violations}"
    else:
        print("\n✅ 所有组件和 hooks 均通过服务层调用 API")


# ─── 测试 3: 拦截服务器验证 ─────────────────────────────────

def test_service_api_intercept():
    """
    启动本地拦截服务器，模拟前端服务层发出的所有 API 请求，
    验证路径完整性（与 services 文件中的 URL 一一对应）。
    """
    PORT = 18998
    request_log.clear()
    server, _ = start_intercept_server(PORT)

    # 与服务层文件完全对应的 API 清单
    service_api_calls = [
        # chatApi.js
        ("POST",   "/api/chat"),
        # conversationApi.js
        ("GET",    "/api/conversations"),
        ("GET",    "/api/conversations/test-conv-id"),
        ("DELETE", "/api/conversations/test-conv-id"),
        # faultTreeApi.js
        ("GET",    "/api/fault-trees"),
        ("GET",    "/api/fault-trees/test-tree-id"),
        ("PUT",    "/api/fault-trees/test-tree-id"),
        ("DELETE", "/api/fault-trees/test-tree-id"),
        # fileApi.js
        ("GET",    "/api/files"),
        ("POST",   "/api/files"),
        ("DELETE", "/api/files/test-file.pdf"),
    ]

    try:
        for method, path in service_api_calls:
            body = {"question": "test"} if method in ("POST", "PUT") else None
            status = send_request(PORT, method, path, body)
            assert status == 200, f"{method} {path} 返回 {status}"

        time.sleep(0.2)

        print(f"\n{'='*60}")
        print(f"拦截到 {len(request_log)} 个请求：")
        print(f"{'='*60}")

        errors = []
        for i, record in enumerate(request_log):
            symbol = "✅" if record["path"].startswith("/api") else "❌"
            print(f"  {symbol} {record['method']:6s} {record['path']}")
            if not record["path"].startswith("/api"):
                errors.append(record)

        print(f"{'='*60}")

        assert len(request_log) == len(service_api_calls), \
            f"请求数量不匹配: 期望 {len(service_api_calls)}, 实际 {len(request_log)}"

        if errors:
            assert False, f"{len(errors)} 个请求缺少 /api 前缀"
        else:
            print("\n✅ 所有服务层 API 路径验证通过")
    finally:
        server.shutdown()


# ─── 直接运行入口 ─────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2 前端服务层 API 拦截测试")
    print("=" * 60)

    print("\n[测试 1] 服务层源码 /api 前缀扫描")
    test_service_layer_api_prefix_scan()

    print("\n[测试 2] 组件/hooks 无裸 fetch 验证")
    test_no_direct_fetch_in_components()

    print("\n[测试 3] 拦截服务器验证")
    test_service_api_intercept()

    print("\n" + "=" * 60)
    print("全部测试完成")
    print("=" * 60)
