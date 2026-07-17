"""OpenAI-compatible API backend."""

from __future__ import annotations

import json
import socket
from urllib import request
from urllib.error import HTTPError
from urllib.error import URLError

from pyquda_agent.config import resolve_base_url

from .base import BackendInvocationError
from .base import LLMBackend


class OpenAICompatibleBackend(LLMBackend):
    """Small OpenAI-compatible chat backend using the standard library."""

    def __init__(
        self,
        *,
        provider: str,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        resolved_base_url = resolve_base_url(provider, base_url)
        if not resolved_base_url:
            raise ValueError(
                f"No base URL is configured for provider {provider!r}; pass --base-url explicitly or configure the provider."
            )
        self.base_url = resolved_base_url.rstrip("/")

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
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:  # pragma: no cover - network dependent
            category = "upstream_service_error"
            detail_category = None
            if exc.code in {401, 403}:
                category = "authentication_error"
                detail_category = "http_authentication_failed"
            elif exc.code == 404:
                category = "endpoint_not_found"
                detail_category = "chat_completions_endpoint_not_found"
            elif exc.code == 408:
                category = "timeout"
                detail_category = "http_timeout"
            elif exc.code == 429:
                category = "rate_limited"
                detail_category = "http_rate_limited"
            elif 400 <= exc.code < 500:
                category = "request_error"
                detail_category = "http_client_request_rejected"
            elif 500 <= exc.code < 600:
                detail_category = "http_server_error"
            raise BackendInvocationError(
                f"API request failed with status {exc.code}",
                category=category,
                detail_category=detail_category,
            ) from exc
        except socket.timeout as exc:  # pragma: no cover - network dependent
            raise BackendInvocationError(
                "API request timed out.",
                category="timeout",
                detail_category="socket_timeout",
            ) from exc
        except URLError as exc:  # pragma: no cover - network dependent
            if isinstance(exc.reason, socket.timeout):
                raise BackendInvocationError(
                    "API request timed out.",
                    category="timeout",
                    detail_category="socket_timeout",
                ) from exc
            reason_text = str(exc.reason).lower()
            detail_category = "network_transport_error"
            if any(token in reason_text for token in ("name resolution", "dns", "lookup")):
                detail_category = "dns_resolution_failure"
            elif "connection refused" in reason_text:
                detail_category = "connection_refused"
            raise BackendInvocationError(
                f"API request failed: {exc.reason}",
                category="network_error",
                detail_category=detail_category,
            ) from exc
        try:
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:  # pragma: no cover - defensive
            raise BackendInvocationError(
                "API response did not contain choices[0].message.content",
                category="response_parse_error",
                detail_category="chat_completions_schema_mismatch",
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise BackendInvocationError(
                "API backend returned an empty response.",
                category="empty_response",
                detail_category="empty_message_content",
            )
        return content.strip()
