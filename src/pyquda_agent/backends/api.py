"""OpenAI-compatible API backend."""

from __future__ import annotations

import json
from urllib import request
from urllib.error import HTTPError
from urllib.error import URLError

from .base import LLMBackend


class OpenAICompatibleBackend(LLMBackend):
    """Small OpenAI-compatible chat backend using the standard library."""

    def __init__(self, *, provider: str, model_name: str, api_key: str, base_url: str | None = None) -> None:
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    @property
    def name(self) -> str:
        return f"api:{self.provider}/{self.model_name}"

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:  # pragma: no cover - network dependent
            raise RuntimeError(f"API request failed with status {exc.code}") from exc
        except URLError as exc:  # pragma: no cover - network dependent
            raise RuntimeError(f"API request failed: {exc.reason}") from exc
        try:
            return response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:  # pragma: no cover - defensive
            raise RuntimeError("API response did not contain choices[0].message.content") from exc
