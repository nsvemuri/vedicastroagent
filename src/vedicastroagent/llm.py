"""Shared LLM provider protocol, model aliases, and client factory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# Shared sampling defaults for all providers.
PARSE_TEMPERATURE = 0.0
PREDICTION_TEMPERATURE = 0.05

PROVIDERS = ("gemini", "claude")

# Gemini
DEFAULT_GEMINI_MODEL = "gemini-3.1-pro-preview"
# Backward-compatible alias used across the package.
DEFAULT_MODEL = DEFAULT_GEMINI_MODEL

# Claude aliases the user can pick; mapped to current API model ids.
CLAUDE_MODEL_ALIASES: dict[str, str] = {
    "sonnet": "claude-sonnet-5",
    "opus": "claude-opus-5",
    "mythos": "claude-mythos-5",
}
DEFAULT_CLAUDE_ALIAS = "sonnet"
DEFAULT_CLAUDE_MODEL = CLAUDE_MODEL_ALIASES[DEFAULT_CLAUDE_ALIAS]

# Prediction output budget. Claude adaptive thinking counts against this ceiling.
# Spiritual (D-9 / D-20 / Karakamsa + 6 yogas) needs more room than other topics.
# Longevity also carries the full JH dump + 45-year gochara table.
DEFAULT_PREDICTION_MAX_OUTPUT_TOKENS = 20480
DENSE_TOPIC_PREDICTION_MAX_OUTPUT_TOKENS = 24576
LONGEVITY_PREDICTION_MAX_OUTPUT_TOKENS = 32768
DENSE_PREDICTION_TOPICS = frozenset({"spiritual", "longevity"})
_TOPIC_PREDICTION_TOKEN_FLOOR = {
    "spiritual": DENSE_TOPIC_PREDICTION_MAX_OUTPUT_TOKENS,
    "longevity": LONGEVITY_PREDICTION_MAX_OUTPUT_TOKENS,
}


def prediction_max_output_tokens(topic_key: str, default: int) -> int:
    """Raise the per-call ceiling for dense topics without shrinking a user override."""
    return max(default, _TOPIC_PREDICTION_TOKEN_FLOOR.get(topic_key, default))


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface used by VedicAstroAgent (parse + prediction)."""

    @property
    def config(self) -> LLMClientConfig: ...

    def generate_parse(self, *, system: str, user: str) -> str: ...

    def generate_prediction(
        self, *, system: str, user: str, max_output_tokens: int | None = None
    ) -> str: ...


@dataclass
class LLMClientConfig:
    provider: str
    model: str
    parse_temperature: float = PARSE_TEMPERATURE
    prediction_temperature: float = PREDICTION_TEMPERATURE
    parse_max_output_tokens: int = 4096
    max_output_tokens: int = 20480


def resolve_provider(provider: str | None = None) -> str:
    """Pick gemini or claude from CLI/env/available keys. Default remains gemini."""
    if provider:
        return _normalize_provider(provider)

    env = os.getenv("LLM_PROVIDER") or os.getenv("VEDIC_PROVIDER")
    if env:
        return _normalize_provider(env)

    has_gemini = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    has_claude = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY"))
    if has_claude and not has_gemini:
        return "claude"
    return "gemini"


def resolve_claude_model(model: str | None = None) -> str:
    """Resolve sonnet/opus/mythos aliases or a full Claude model id."""
    raw = (model or os.getenv("CLAUDE_MODEL") or DEFAULT_CLAUDE_ALIAS).strip()
    key = raw.lower()
    if key in CLAUDE_MODEL_ALIASES:
        return CLAUDE_MODEL_ALIASES[key]
    if raw.startswith("claude-"):
        return raw
    raise ValueError(
        f"Unknown Claude model {model!r}. "
        f"Choose one of: {', '.join(CLAUDE_MODEL_ALIASES)} "
        f"(or a full id like claude-sonnet-5)."
    )


def claude_supports_temperature(model: str) -> bool:
    """Return False when the Messages API rejects the temperature parameter.

    Claude Sonnet 5, Opus 4.7+, and Mythos return HTTP 400 if temperature is sent.
    We omit it for all Claude model ids — safe for older Sonnet/Opus too (API default).
    """
    _ = model
    return False


def claude_sampling_kwargs(model: str, temperature: float) -> dict[str, float]:
    """Sampling kwargs safe for the given Claude model (may be empty)."""
    _ = temperature
    if claude_supports_temperature(model):
        return {"temperature": temperature}
    return {}


def create_llm_client(
    provider: str | None = None,
    model: str | None = None,
) -> LLMClient:
    """Create a Gemini or Claude client. Only the chosen provider's API key is required."""
    chosen = resolve_provider(provider)
    if chosen == "gemini":
        from .gemini_client import GeminiClient, GeminiConfig

        cfg = GeminiConfig()
        if model:
            cfg.model = model
        return GeminiClient(cfg)

    if chosen == "claude":
        from .claude_client import ClaudeClient, ClaudeConfig

        cfg = ClaudeConfig(model=resolve_claude_model(model))
        return ClaudeClient(cfg)

    raise ValueError(f"Unsupported provider {chosen!r}. Choose: {', '.join(PROVIDERS)}")


def _normalize_provider(value: str) -> str:
    key = value.strip().lower()
    aliases = {
        "gemini": "gemini",
        "google": "gemini",
        "claude": "claude",
        "anthropic": "claude",
    }
    if key not in aliases:
        raise ValueError(
            f"Unknown provider {value!r}. Choose one of: {', '.join(PROVIDERS)}"
        )
    return aliases[key]
