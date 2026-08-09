"""Thin Gemini client wrapper."""

from __future__ import annotations

import os
from dataclasses import dataclass

from google import genai
from google.genai import types

from .llm import (
    DEFAULT_GEMINI_MODEL,
    LLMClientConfig,
    PARSE_TEMPERATURE,
    PREDICTION_TEMPERATURE,
)

# Backward-compatible exports.
DEFAULT_MODEL = DEFAULT_GEMINI_MODEL


@dataclass
class GeminiConfig:
    api_key: str | None = None
    model: str = DEFAULT_GEMINI_MODEL
    parse_temperature: float = PARSE_TEMPERATURE
    prediction_temperature: float = PREDICTION_TEMPERATURE
    parse_max_output_tokens: int = 4096
    max_output_tokens: int = 16384

    @property
    def provider(self) -> str:
        return "gemini"


class GeminiClient:
    def __init__(self, config: GeminiConfig | None = None) -> None:
        self._gemini = config or GeminiConfig()
        api_key = (
            self._gemini.api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        if not api_key:
            raise RuntimeError(
                "Missing API key. Set GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment "
                "or a .env file. See .env.example."
            )
        self._gemini.api_key = api_key
        if self._gemini.model == DEFAULT_GEMINI_MODEL:
            self._gemini.model = os.getenv("GEMINI_MODEL", self._gemini.model)
        self._client = genai.Client(api_key=api_key)
        self.config = LLMClientConfig(
            provider="gemini",
            model=self._gemini.model,
            parse_temperature=self._gemini.parse_temperature,
            prediction_temperature=self._gemini.prediction_temperature,
            parse_max_output_tokens=self._gemini.parse_max_output_tokens,
            max_output_tokens=self._gemini.max_output_tokens,
        )

    def generate(
        self,
        *,
        system: str,
        user: str,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        response = self._client.models.generate_content(
            model=self.config.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=(
                    self.config.prediction_temperature if temperature is None else temperature
                ),
                max_output_tokens=max_output_tokens or self.config.max_output_tokens,
            ),
        )
        text = (response.text or "").strip()
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
