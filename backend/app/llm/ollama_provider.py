import json
from collections.abc import AsyncIterator

import httpx

from app.config import get_settings
from app.llm.base import LLMError, LLMProvider, Message

UNREACHABLE = "The answer model is not reachable. Check that Ollama is running."


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.ollama_url
        self.model = settings.llm_model

    def _payload(self, messages: list[Message], temperature: float, max_tokens: int, stream: bool) -> dict[str, object]:
        return {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "think": False,  # gemma4 thinks by default; answers must start fast
            "keep_alive": "30m",
            "options": {"temperature": temperature, "num_predict": max_tokens, "num_ctx": 8192},
        }

    async def generate(
        self, messages: list[Message], temperature: float = 0.1, max_tokens: int = 512, json_mode: bool = False
    ) -> str:
        payload = self._payload(messages, temperature, max_tokens, False)
        if json_mode:
            payload["format"] = "json"
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=300) as client:
                res = await client.post("/api/chat", json=payload)
                res.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(UNREACHABLE) from exc
        return res.json()["message"]["content"]

    async def stream(
        self, messages: list[Message], temperature: float = 0.1, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        try:
            async with (
                httpx.AsyncClient(base_url=self.base_url, timeout=300) as client,
                client.stream("POST", "/api/chat", json=self._payload(messages, temperature, max_tokens, True)) as res,
            ):
                res.raise_for_status()
                async for line in res.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("error"):
                        raise LLMError(UNREACHABLE)
                    piece = data.get("message", {}).get("content", "")
                    if piece:
                        yield piece
                    if data.get("done"):
                        break
        except httpx.HTTPError as exc:
            raise LLMError(UNREACHABLE) from exc

    async def warm_up(self) -> None:
        """Load the model into memory so the first real answer starts fast."""
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=300) as client:
                # Same options as real requests: a different num_ctx would force a full reload later.
                payload = self._payload([{"role": "user", "content": "ok"}], 0.0, 1, False)
                await client.post("/api/chat", json=payload)
        except httpx.HTTPError:
            pass
