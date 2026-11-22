# -*- coding: utf-8 -*-
"""P2 提供的本地匹配服务：P3 直接 fetch 就能拿到和命令行一模一样的 JSON。

启动：
    cd Y:\hks\p2
    python scripts/api_server.py --port 8787

调用：
    GET http://127.0.0.1:8787/match?q=汉德%2035%20吨桥，前面那副
    GET http://127.0.0.1:8787/health

设计取舍：只用标准库（不用装 FastAPI/uvicorn），赛前少一个依赖；单进程内复用
skus/axles/BM25 索引，实测单次 3–6 ms。
"""
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p2"))

from engine.match import match_query  # noqa: E402
from engine.store import load_axles, load_skus  # noqa: E402

SKUS = load_skus()
AXLES = load_axles()


class Handler(BaseHTTPRequestHandler):
    server_version = "GYMatch/1.1"

    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # 本地联调用，放开跨域，免得 P3 前端被 CORS 卡住
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path: Path) -> None:
        """把 app/ 下的静态文件发出去，让 P3 的页面与接口同源，省掉 file:// 的麻烦。"""
        try:
            path = path.resolve()
            path.relative_to((ROOT / "app").resolve())
        except (ValueError, OSError):
            return self._json(403, {"error": "越界"})
        if not path.is_file():
            return self._json(404, {"error": "文件不存在: %s" % path.name})
        ctype = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".png": "image/png", ".jpg": "image/jpeg",
                 ".svg": "image/svg+xml", ".json": "application/json; charset=utf-8"}.get(path.suffix.lower(), "application/octet-stream")
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        if u.path == "/health":
            return self._json(200, {"ok": True, "skus": len(SKUS), "axles": len(AXLES)})
        if u.path in ("/", "/index.html"):
            page = ROOT / "p2" / "web" / "select.html"
            if not page.exists():
                page = ROOT / "p2" / "web" / "index.html"
            if not page.exists():
                return self._json(404, {"error": "演示页 p2/web/index.html 不存在"})
            body = page.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path.startswith("/app/"):
            return self._static(ROOT / "app" / u.path[len("/app/"):].lstrip("/"))
        if u.path != "/match":
            return self._json(404, {"error": "use /  (演示页)  or /app/match.html  or /match?q=...  or /health"})
        q = (parse_qs(u.query).get("q") or [""])[0]
        q = unquote(q).strip()
        if not q:
            return self._json(400, {"error": "缺少 q 参数，例如 /match?q=147×100×14.5"})
        try:
            top = int((parse_qs(u.query).get("top") or ["3"])[0])
        except Exception:
            top = 3
        r = match_query(q, SKUS, AXLES, top=max(1, min(top, 5)))
        return self._json(200, r)

    do_OPTIONS = lambda self: self._json(204, {})  # noqa: E731

    def log_message(self, fmt, *args):  # 安静点，别把终端刷满
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("匹配服务已起： http://%s:%d/match?q=<查询>   （Ctrl+C 结束）" % (args.host, args.port))
    print("健康检查：     http://%s:%d/health" % (args.host, args.port))
    print("已载入 SKU %d 条 / 车桥 %d 个" % (len(SKUS), len(AXLES)))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
