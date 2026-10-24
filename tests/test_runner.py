import asyncio
import json

import pytest

from bench.models import ModelRef, parse_openrouter_models
from bench.pages import build_pages
from bench.runner import AgentResult, RateLimited, run_one
from bench.server import start_server

KEY = "sk-or-v1-TESTKEY123"
M = ModelRef("fake/model:free", "openrouter", "fake/model:free")


@pytest.fixture
def env(tmp_path):
    specs = build_pages(tmp_path / "pages")
    server = start_server(tmp_path / "pages", port=0)
    yield specs[0], server, tmp_path / "raw"
    server.stop()


def _run(spec, server, raw, agent, **kw):
    return asyncio.run(
        run_one(spec, M, server, agent_fn=agent, results_dir=raw, repeat=1,
                timeout_s=kw.get("timeout_s", 5), backoff_s=0.0, secrets=[KEY])
    )


def test_run_one_saves_json(env):
    spec, server, raw = env

    async def agent(task, model):
        return AgentResult("price $20.99", tokens=12)

    rec = _run(spec, server, raw, agent)
    saved = json.loads(next(raw.rglob("*.json")).read_text())
    assert saved["status"] == "ok" and saved["final_answer"] == "price $20.99" and saved["tokens"] == 12
    assert rec["page_id"] == spec.id


def test_timeout_recorded_as_timeout(env):
    spec, server, raw = env

    async def agent(task, model):
        await asyncio.sleep(2)

    rec = _run(spec, server, raw, agent, timeout_s=0.1)
    assert rec["status"] == "timeout"


def test_429_retried_then_recorded_as_error(env):
    spec, server, raw = env
    calls = []

    async def agent(task, model):
        calls.append(1)
        raise RateLimited("429")

    rec = _run(spec, server, raw, agent)
    assert rec["status"] == "error" and "429" in rec["reason"] and len(calls) == 3


def test_saved_json_has_no_api_key(env):
    spec, server, raw = env

    async def agent(task, model):
        return AgentResult(f"leak {KEY}", tokens=1)

    _run(spec, server, raw, agent)
    assert KEY not in next(raw.rglob("*.json")).read_text()


def test_resume_skips_existing(env):
    spec, server, raw = env
    calls = []

    async def agent(task, model):
        calls.append(1)
        return AgentResult("x", tokens=1)

    _run(spec, server, raw, agent)
    _run(spec, server, raw, agent)
    assert len(calls) == 1


def test_parse_openrouter_models_keeps_free_tool_models():
    payload = {"data": [
        {"id": "a/b:free", "context_length": 8000, "supported_parameters": ["tools"], "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "c/d:free", "context_length": 8000, "supported_parameters": [], "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "e/f", "context_length": 8000, "supported_parameters": ["tools"], "pricing": {"prompt": "0.1", "completion": "0.1"}},
    ]}
    got = parse_openrouter_models(payload)
    assert [m.id for m in got] == ["a/b:free", "c/d:free"]
    assert [m.supports_tools for m in got] == [True, False]


def test_swallowed_429_without_answer_raises_rate_limited():
    import pytest

    from bench.runner import _raise_if_rate_limited

    with pytest.raises(RateLimited):
        _raise_if_rate_limited(None, "Error code: 429 - temporarily rate-limited")
    _raise_if_rate_limited("$70.50", "Error code: 429 - earlier hiccup")
    _raise_if_rate_limited(None, "validation error for AgentOutput")


def test_no_final_answer_is_recorded_as_error(env):
    spec, server, raw = env

    async def agent(task, model):
        return AgentResult(None, tokens=0, reason="model not found")

    rec = _run(spec, server, raw, agent)
    assert rec["status"] == "error" and "model not found" in rec["reason"]
