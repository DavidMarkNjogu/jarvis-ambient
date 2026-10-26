"""Chat providers that speak the OpenAI-compatible API: Gemini, Groq and Ollama."""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from .config import ProviderConfig


class ProviderError(Exception):
    def __init__(self, provider: str, reason: str):
        super().__init__(f"{provider}: {reason}")
        self.provider = provider
        self.reason = reason


class Provider:
    def __init__(self, config: ProviderConfig, client: httpx.Client | None = None):
        self.name = config.name
        self.model = config.model
        headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}
        self._client = client or httpx.Client(
            base_url=config.base_url,
            headers=headers,
            timeout=httpx.Timeout(60.0, connect=5.0),
        )

    def stream(self, messages: list[dict]) -> Iterator[str]:
        """Yield the reply text piece by piece as it arrives."""
        payload = {"model": self.model, "messages": messages, "stream": True}
        try:
            with self._client.stream("POST", "chat/completions", json=payload) as response:
                if response.status_code != 200:
                    response.read()
                    raise ProviderError(self.name, _describe_status(response, self.model))
                for line in response.iter_lines():
                    text = self._parse_sse_line(line)
                    if text:
                        yield text
        except httpx.TimeoutException as exc:
            raise ProviderError(self.name, "took too long to answer") from exc
        except httpx.TransportError as exc:
            hint = " (is Ollama running?)" if self.name == "ollama" else " (check your internet)"
            raise ProviderError(self.name, "could not connect" + hint) from exc

    def list_models(self) -> list[str]:
        try:
            response = self._client.get("models")
        except httpx.TransportError as exc:
            raise ProviderError(self.name, "could not connect") from exc
        if response.status_code != 200:
            raise ProviderError(self.name, _describe_status(response, self.model))
        ids = [m.get("id", "") for m in response.json().get("data", [])]
        return sorted(i.removeprefix("models/") for i in ids if i)

    def _parse_sse_line(self, line: str) -> str:
        if not line.startswith("data:"):
            return ""
        data = line[len("data:"):].strip()
        if not data or data == "[DONE]":
            return ""
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            return ""
        if "error" in event:
            raise ProviderError(self.name, _error_message(event) or "failed mid-reply")
        choices = event.get("choices") or [{}]
        return (choices[0].get("delta") or {}).get("content") or ""


def _describe_status(response: httpx.Response, model: str) -> str:
    status = response.status_code
    if status in (401, 403):
        return "the API key was rejected; check it in .env"
    if status == 404:
        return f"model '{model}' was not found; type /models to see available ones"
    if status == 429:
        return "free-tier rate limit reached; try again in a minute"
    if status >= 500:
        return f"the service is having problems (HTTP {status})"
    try:
        detail = _error_message(response.json())
    except ValueError:
        detail = ""
    if "api key" in detail.lower():  # Gemini reports bad keys as HTTP 400
        return "the API key was rejected; check it in .env"
    return f"HTTP {status}" + (f": {detail[:160]}" if detail else "")


def _error_message(body: object) -> str:
    if isinstance(body, list) and body:
        body = body[0]
    if not isinstance(body, dict):
        return ""
    error = body.get("error")
    if isinstance(error, dict):
        return str(error.get("message", ""))
    return str(error or "")
