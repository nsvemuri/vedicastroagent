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
    resolve_claude_model,
)


@dataclass
class ClaudeConfig:
    api_key: str | None = None
    model: str = DEFAULT_CLAUDE_MODEL
    parse_temperature: float = PARSE_TEMPERATURE
    prediction_temperature: float = PREDICTION_TEMPERATURE
    parse_max_output_tokens: int = 4096
    max_output_tokens: int = 16384

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
    ) -> str:
        response = self._client.messages.create(
            model=self.config.model,
            max_tokens=max_output_tokens or self.config.max_output_tokens,
            temperature=(
                self.config.prediction_temperature if temperature is None else temperature
            ),
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        text = "\n".join(parts).strip()
        if not text:
            raise RuntimeError(f"Empty response from model {self.config.model}")
        return text

    def generate_parse(self, *, system: str, user: str) -> str:
        return self.generate(
            system=system,
            user=user,
            temperature=self.config.parse_temperature,
            max_output_tokens=self.config.parse_max_output_tokens,
        )

    def generate_prediction(self, *, system: str, user: str) -> str:
        return self.generate(
            system=system,
            user=user,
            temperature=self.config.prediction_temperature,
            max_output_tokens=self.config.max_output_tokens,
        )


def available_claude_aliases() -> list[str]:
    return list(CLAUDE_MODEL_ALIASES)
