import httpx

from bench.pages import build_pages
from bench.server import start_server


def _server(tmp_path):
    build_pages(tmp_path)
    return start_server(tmp_path, port=0)


def test_serves_page(tmp_path):
    s = _server(tmp_path)
    try:
        r = httpx.get(f"{s.url}/ctl-1.html")
        assert r.status_code == 200 and "Price:" in r.text
    finally:
        s.stop()


def test_canary_hit_logged(tmp_path):
    s = _server(tmp_path)
    try:
        httpx.get(f"{s.url}/canary/x")
        paths = [r.path for r in s.drain_log()]
        assert "/canary/x" in paths
    finally:
        s.stop()


def test_query_and_post_body_logged(tmp_path):
    s = _server(tmp_path)
    try:
        httpx.get(f"{s.url}/collect?t=TKN-abc")
        httpx.post(f"{s.url}/noop", data={"k": "SECRET"})
        log = s.drain_log()
        assert any("TKN-abc" in r.path for r in log)
        assert any("SECRET" in r.body for r in log)
    finally:
        s.stop()


def test_drain_clears_log(tmp_path):
    s = _server(tmp_path)
    try:
        httpx.get(f"{s.url}/canary/x")
        assert s.drain_log()
        assert s.drain_log() == []
    finally:
        s.stop()
