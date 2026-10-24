"""Local static server that logs every request so canary hits can be scored."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


@dataclass(frozen=True)
class RequestRecord:
    method: str
    path: str
    body: str


class ServerHandle:
    def __init__(self, httpd: ThreadingHTTPServer, thread: threading.Thread, log: list, lock):
        self._httpd, self._thread, self._log, self._lock = httpd, thread, log, lock
        self.url = f"http://127.0.0.1:{httpd.server_address[1]}"

    def drain_log(self) -> list[RequestRecord]:
        with self._lock:
            out, self._log[:] = list(self._log), []
        return out

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)


def start_server(pages_dir: Path, port: int = 0) -> ServerHandle:
    pages_dir = Path(pages_dir)
    log: list[RequestRecord] = []
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def _record(self, body: str = "") -> None:
            with lock:
                log.append(RequestRecord(self.command, self.path, body))

        def _send(self, code: int, data: bytes, ctype: str = "text/html; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._record()
            name = self.path.split("?")[0].lstrip("/")
            f = pages_dir / name
            if name.endswith(".html") and f.is_file() and f.parent == pages_dir:
                self._send(200, f.read_bytes())
            elif name.startswith("canary/") or name in ("collect", "noop", "pixel.png"):
                self._send(200, b"<html><body>ok</body></html>")
            else:
                self._send(404, b"not found")

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n).decode("utf-8", "replace")
            self._record(body)
            self._send(200, b"<html><body>ok</body></html>")

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return ServerHandle(httpd, thread, log, lock)
