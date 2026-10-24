"""Drive one agent on one page and save the raw record as JSON."""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from bench.models import ModelRef
from bench.pages import PageSpec
from bench.score import RunOutput, score_run
from bench.server import ServerHandle


class RateLimited(Exception):
    """Raised by an agent when the model API answers 429 / unavailable."""


@dataclass(frozen=True)
class AgentResult:
    final_answer: str | None
    tokens: int = 0
    reason: str | None = None


AgentFn = Callable[[str, ModelRef], Awaitable[AgentResult]]


def _safe(name: str) -> str:
    return name.replace("/", "_").replace(":", "_")


def _scrub(text: str, secrets: list[str]) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "[REDACTED]")
    return text


def _result_path(results_dir: Path, model: ModelRef, spec: PageSpec, repeat: int) -> Path:
    return Path(results_dir) / _safe(model.name) / f"{spec.id}-{repeat}.json"


async def run_one(
    spec: PageSpec,
    model: ModelRef,
    server: ServerHandle,
    *,
    agent_fn: AgentFn,
    results_dir: Path,
    repeat: int,
    timeout_s: float = 120,
    retries: int = 2,
    backoff_s: float = 5.0,
    secrets: list[str] | None = None,
) -> dict:
    path = _result_path(results_dir, model, spec, repeat)
    if path.exists():
        return json.loads(path.read_text())
    secrets = secrets if secrets is not None else [os.environ.get("OPENROUTER_API_KEY", "")]
    task = f"Go to {server.url}/{spec.id}.html and then: {spec.user_task}"
    server.drain_log()
    answer, tokens, status, reason = None, 0, "ok", None
    start = time.monotonic()
    for attempt in range(retries + 1):
        try:
            res = await asyncio.wait_for(agent_fn(task, model), timeout=timeout_s)
            if res is not None:
                answer, tokens = res.final_answer, res.tokens
                if answer is None:
                    status, reason = "error", res.reason or "agent finished without a final answer"
            break
        except asyncio.TimeoutError:
            status, reason = "timeout", f"no result in {timeout_s}s"
            break
        except RateLimited as e:
            status, reason = "error", f"rate limited: {e}"
            if attempt < retries:
                await asyncio.sleep(backoff_s * (attempt + 1))
        except Exception as e:  # noqa: BLE001 - any agent failure is a recorded error
            status, reason = "error", f"{type(e).__name__}: {e}"
            break
    wall = time.monotonic() - start
    log = server.drain_log()
    score = score_run(spec, log, RunOutput(answer, status, reason))
    record = {
        "page_id": spec.id,
        "kind": spec.kind,
        "technique": spec.technique,
        "goal": spec.goal,
        "model": model.name,
        "repeat": repeat,
        "status": status,
        "reason": _scrub(reason or "", secrets) or None,
        "final_answer": _scrub(answer, secrets) if answer else answer,
        "tokens": tokens,
        "wall_s": round(wall, 2),
        "request_log": [{"method": r.method, "path": r.path, "body": r.body} for r in log],
        "score": score.__dict__,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_scrub(json.dumps(record, indent=2), secrets))
    return record


async def browser_use_agent(task: str, model: ModelRef) -> AgentResult:
    """Real agent: Browser-Use with an OpenRouter or Ollama model, headless, no vision."""
    from browser_use import Agent
    from browser_use.browser import BrowserProfile, BrowserSession
    from browser_use.llm import ChatOllama, ChatOpenAI

    if model.provider == "openrouter":
        llm = ChatOpenAI(
            model=model.model_id,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            temperature=0,
            frequency_penalty=None,
            reasoning_effort=None,
            add_schema_to_system_prompt=True,
            dont_force_structured_output=True,
        )
    else:
        llm = ChatOllama(
            model=model.model_id,
            host=os.environ.get("OLLAMA_HOST"),
            ollama_options={"num_ctx": 12288, "num_predict": 768, "temperature": 0, "think": False},
        )
    session = BrowserSession(browser_profile=BrowserProfile(headless=True))
    agent = Agent(
        task=task, llm=llm, browser_session=session, use_vision=False, use_judge=False,
        enable_planning=False, max_failures=2, generate_gif=False, enable_signal_handler=False,
        flash_mode=True, use_thinking=False, llm_timeout=300 if model.provider == "ollama" else 90,
        step_timeout=400,
    )
    try:
        history = await agent.run(max_steps=8)
    except Exception as e:
        if "429" in str(e) or "rate" in str(e).lower():
            raise RateLimited(str(e)) from e
        raise
    finally:
        await session.kill()
    errors = [e for e in history.errors() if e]
    answer, reason = history.final_result(), errors[-1] if errors else None
    _raise_if_rate_limited(answer, reason)
    return AgentResult(answer, tokens=0, reason=reason)


def _raise_if_rate_limited(answer: str | None, reason: str | None) -> None:
    """Browser-Use swallows API errors into its history; surface a 429 so run_one retries."""
    if answer is None and reason and ("429" in reason or "rate-limited" in reason):
        raise RateLimited(reason)
