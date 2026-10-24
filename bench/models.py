"""Model references and discovery (OpenRouter free models, local Ollama models)."""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class ModelRef:
    name: str  # label used in results paths
    provider: str  # "openrouter" | "ollama"
    model_id: str


@dataclass(frozen=True)
class ModelInfo:
    id: str
    supports_tools: bool
    context_length: int


def parse_openrouter_models(payload: dict) -> list[ModelInfo]:
    out = []
    for m in payload.get("data", []):
        p = m.get("pricing") or {}
        free = m["id"].endswith(":free") or (p.get("prompt") == "0" and p.get("completion") == "0")
        if free:
            out.append(
                ModelInfo(m["id"], "tools" in (m.get("supported_parameters") or []), m.get("context_length") or 0)
            )
    return out


def list_cloud_free_models(api_key: str) -> list[ModelInfo]:
    r = httpx.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    r.raise_for_status()
    return parse_openrouter_models(r.json())


def list_local_models() -> list[str]:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    r = httpx.get(f"{host}/api/tags", timeout=10)
    r.raise_for_status()
    return [m["name"] for m in r.json().get("models", [])]
