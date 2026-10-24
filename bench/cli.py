"""Run the benchmark: python -m bench.cli --repeats 3 [--models a,b] [--pages ctl-1,...]"""
from __future__ import annotations

import argparse
import asyncio
import tomllib
from pathlib import Path

from dotenv import load_dotenv

from bench.models import ModelRef
from bench.pages import build_pages
from bench.runner import browser_use_agent, run_one
from bench.server import start_server

ROOT = Path(__file__).resolve().parent.parent


def load_models(path: Path = ROOT / "models.toml") -> list[ModelRef]:
    data = tomllib.loads(path.read_text())
    return [ModelRef(m["name"], m["provider"], m["model_id"]) for m in data["model"]]


async def _run_model(model: ModelRef, specs, pages_dir: Path, repeats: int, results_dir: Path) -> None:
    server = start_server(pages_dir, port=0)
    try:
        for n in range(1, repeats + 1):
            for spec in specs:
                rec = await run_one(
                    spec, model, server, agent_fn=browser_use_agent,
                    results_dir=results_dir, repeat=n,
                    timeout_s=900 if model.provider == "ollama" else 240,
                    retries=0 if model.provider == "ollama" else 5,
                    backoff_s=30,
                )
                s = rec["score"]
                print(f"{model.name} {spec.id} #{n} {rec['status']} obeyed={s['obeyed']} ok={s['task_ok']}", flush=True)
    finally:
        server.stop()


async def main_async(args) -> None:
    pages_dir = ROOT / "build" / "pages"
    specs = build_pages(pages_dir)
    if args.pages:
        wanted = set(args.pages.split(","))
        specs = [s for s in specs if s.id in wanted]
    models = load_models()
    if args.models:
        wanted = set(args.models.split(","))
        models = [m for m in models if m.name in wanted]
    results_dir = ROOT / "results" / "raw"
    cloud = [m for m in models if m.provider == "openrouter"]
    local = [m for m in models if m.provider == "ollama"]
    await asyncio.gather(*[_run_model(m, specs, pages_dir, args.repeats, results_dir) for m in cloud])
    for m in local:
        await _run_model(m, specs, pages_dir, args.repeats, results_dir)


def main() -> None:
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser()
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--models", default="")
    p.add_argument("--pages", default="")
    asyncio.run(main_async(p.parse_args()))


if __name__ == "__main__":
    main()
