"""Thin Gemini client wrapper."""

from __future__ import annotations

import os
from dataclasses import dataclass

from google import genai
from google.genai import types


# Gemini 3.1 Pro (API model id). Override with GEMINI_MODEL if needed.
DEFAULT_MODEL = "gemini-3.1-pro-preview"

# Parsing must stay deterministic; prediction uses minimal sampling to reduce truncation stalls.
PARSE_TEMPERATURE = 0.0
PREDICTION_TEMPERATURE = 0.05


@dataclass
class GeminiConfig:
    api_key: str | None = None
    model: str = DEFAULT_MODEL
    parse_temperature: float = PARSE_TEMPERATURE
    prediction_temperature: float = PREDICTION_TEMPERATURE
    parse_max_output_tokens: int = 4096
    max_output_tokens: int = 16384


class GeminiClient:
    def __init__(self, config: GeminiConfig | None = None) -> None:
        self.config = config or GeminiConfig()
        api_key = self.config.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing API key. Set GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment "
                "or a .env file. See .env.example."
            )
        self.config.api_key = api_key
        self.config.model = os.getenv("GEMINI_MODEL", self.config.model)
        self._client = genai.Client(api_key=api_key)

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
