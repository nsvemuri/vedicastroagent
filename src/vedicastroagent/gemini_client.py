"""Thin Gemini client wrapper."""

from __future__ import annotations

import os
from dataclasses import dataclass

from google import genai
from google.genai import types


DEFAULT_MODEL = "gemini-2.5-pro"


@dataclass
class GeminiConfig:
    api_key: str | None = None
    model: str = DEFAULT_MODEL
    temperature: float = 0.35
    max_output_tokens: int = 8192


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

    def generate(self, *, system: str, user: str) -> str:
        response = self._client.models.generate_content(
            model=self.config.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError(f"Empty response from model {self.config.model}")
        return text
