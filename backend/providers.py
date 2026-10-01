"""Provider-agnostic chat completion client for benchmark runs.

All model IDs are configured through environment variables. Never commit API keys.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class ModelConfig:
    key: str
    provider: str
    model: str
    base_url: str


MODEL_CONFIGS: dict[str, ModelConfig] = {
    "groq_primary": ModelConfig(
        key="groq_primary",
        provider="groq",
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        base_url="https://api.groq.com/openai/v1",
    ),
    "openrouter_model_1": ModelConfig(
        key="openrouter_model_1",
        provider="openrouter",
        model=os.getenv("OPENROUTER_MODEL_1", "openai/gpt-4o-mini"),
        base_url="https://openrouter.ai/api/v1",
    ),
    "openrouter_model_2": ModelConfig(
        key="openrouter_model_2",
        provider="openrouter",
        model=os.getenv("OPENROUTER_MODEL_2", "google/gemini-2.0-flash-001"),
        base_url="https://openrouter.ai/api/v1",
    ),
    "openrouter_judge": ModelConfig(
        key="openrouter_judge",
        provider="openrouter",
        model=os.getenv("OPENROUTER_JUDGE_MODEL", "anthropic/claude-3.5-haiku"),
        base_url="https://openrouter.ai/api/v1",
    ),
}


class ModelCallError(RuntimeError):
    """Raised when a provider call fails or returns no usable content."""


def _api_key(provider: str) -> str:
    env_name = "GROQ_API_KEY" if provider == "groq" else "OPENROUTER_API_KEY"
    value = os.getenv(env_name)
    if not value:
        raise ModelCallError(f"Missing {env_name}. Add it to your local environment.")
    return value


def call_model(
    model_key: str,
    prompt: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Call a configured model and return content plus measurable call metadata."""
    if model_key not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model key: {model_key}")

    config = MODEL_CONFIGS[model_key]
    client = OpenAI(
        api_key=_api_key(config.provider),
        base_url=config.base_url,
        timeout=timeout,
        max_retries=0,
    )

    started = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        content = response.choices[0].message.content or ""
        if not content.strip():
            raise ModelCallError(f"{model_key} returned an empty response")
        usage = getattr(response, "usage", None)
        return {
            "model_key": model_key,
            "provider": config.provider,
            "model": config.model,
            "content": content,
            "latency_ms": elapsed_ms,
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
            "status": "success",
            "error": None,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        raise ModelCallError(
            f"{config.provider}/{config.model} failed after {elapsed_ms} ms: {exc}"
        ) from exc


def available_model_keys() -> list[str]:
    return list(MODEL_CONFIGS)
