"""Anthropic Claude client (Sonnet / Opus / Mythos)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from anthropic import Anthropic

from .llm import (
    CLAUDE_MODEL_ALIASES,
    DEFAULT_CLAUDE_MODEL,
    LLMClientConfig,
    PARSE_TEMPERATURE,
    PREDICTION_TEMPERATURE,
    claude_sampling_kwargs,
    resolve_claude_model,
)


# Sonnet 5 / Opus 5 use adaptive thinking by default; thinking counts against max_tokens.
# 4096 is often exhausted by thinking alone on chart parse prompts (empty text → error).
DEFAULT_CLAUDE_PARSE_MAX_TOKENS = 16384
DEFAULT_CLAUDE_PREDICTION_MAX_TOKENS = 32768


@dataclass
class ClaudeConfig:
    api_key: str | None = None
    model: str = DEFAULT_CLAUDE_MODEL
    parse_temperature: float = PARSE_TEMPERATURE
    prediction_temperature: float = PREDICTION_TEMPERATURE
    parse_max_output_tokens: int = DEFAULT_CLAUDE_PARSE_MAX_TOKENS
    max_output_tokens: int = DEFAULT_CLAUDE_PREDICTION_MAX_TOKENS
    # Lower effort on parse to leave budget for checklist text; medium for predictions.
    parse_effort: str = "low"
    prediction_effort: str = "medium"

    @property
    def provider(self) -> str:
        return "claude"


class ClaudeClient:
    def __init__(self, config: ClaudeConfig | None = None) -> None:
        self._claude = config or ClaudeConfig()
        api_key = (
            self._claude.api_key
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("CLAUDE_API_KEY")
        )
        if not api_key:
            raise RuntimeError(
                "Missing Claude API key. Set ANTHROPIC_API_KEY (or CLAUDE_API_KEY) "
                "in the environment or a .env file. See .env.example."
            )
        self._claude.api_key = api_key
        # Allow CLAUDE_MODEL env only when caller did not already pin a model.
        if self._claude.model == DEFAULT_CLAUDE_MODEL and os.getenv("CLAUDE_MODEL"):
            self._claude.model = resolve_claude_model(os.getenv("CLAUDE_MODEL"))
        else:
            self._claude.model = resolve_claude_model(self._claude.model)
        self._client = Anthropic(api_key=api_key)
        self.config = LLMClientConfig(
            provider="claude",
            model=self._claude.model,
            parse_temperature=self._claude.parse_temperature,
            prediction_temperature=self._claude.prediction_temperature,
            parse_max_output_tokens=self._claude.parse_max_output_tokens,
            max_output_tokens=self._claude.max_output_tokens,
        )

    def generate(
        self,
        *,
        system: str,
        user: str,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        effort: str | None = None,
    ) -> str:
        temp = self.config.prediction_temperature if temperature is None else temperature
        # Sonnet 5 / Opus / Mythos: omit temperature (API returns 400 if sent).
        sampling = claude_sampling_kwargs(self.config.model, temp)
        create_kwargs: dict = {
            "model": self.config.model,
            "max_tokens": max_output_tokens or self.config.max_output_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            **sampling,
        }
        if effort:
            create_kwargs["output_config"] = {"effort": effort}
        # Anthropic SDK requires streaming when expected runtime > 10 minutes
        # (triggered by high max_tokens, e.g. our 32k prediction budget).
        with self._client.messages.stream(**create_kwargs) as stream:
            response = stream.get_final_message()
        parts: list[str] = []
        block_types: list[str] = []
        for block in response.content:
            block_types.append(str(getattr(block, "type", type(block).__name__)))
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        text = "\n".join(parts).strip()
        if not text:
            stop = getattr(response, "stop_reason", None)
            usage = getattr(response, "usage", None)
            out_tok = getattr(usage, "output_tokens", None) if usage else None
            raise RuntimeError(
                f"Empty response from model {self.config.model} "
                f"(stop_reason={stop}, output_tokens={out_tok}, blocks={block_types}). "
                "On Claude Sonnet 5 / Opus 5, adaptive thinking counts against max_tokens; "
                "raise parse/prediction max_tokens or lower effort if stop_reason is max_tokens."
            )
        return text

    def generate_parse(self, *, system: str, user: str) -> str:
        return self.generate(
            system=system,
            user=user,
            temperature=self.config.parse_temperature,
            max_output_tokens=self.config.parse_max_output_tokens,
            effort=self._claude.parse_effort,
        )

    def generate_prediction(self, *, system: str, user: str) -> str:
        return self.generate(
            system=system,
            user=user,
            temperature=self.config.prediction_temperature,
            max_output_tokens=self.config.max_output_tokens,
            effort=self._claude.prediction_effort,
        )


def available_claude_aliases() -> list[str]:
    return list(CLAUDE_MODEL_ALIASES)
