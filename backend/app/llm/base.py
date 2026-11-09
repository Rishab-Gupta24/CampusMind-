"""Every LLM call goes through LLMProvider (Rules.md §1.19). Ollama ↔ Gemini is a config change only."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import TypedDict

from app.config import get_settings


class Message(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMError(Exception):
    """The language model failed. The message is safe to show users."""


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self, messages: list[Message], temperature: float = 0.1, max_tokens: int = 512, json_mode: bool = False
    ) -> str:
        """Return the whole reply. `json_mode` asks the model for a single JSON object."""

    @abstractmethod
    def stream(self, messages: list[Message], temperature: float = 0.1, max_tokens: int = 512) -> AsyncIterator[str]:
        """Yield the reply as text pieces."""


@lru_cache
def get_provider() -> LLMProvider:
    provider = get_settings().llm_provider
    if provider == "ollama":
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider()
    raise LLMError(f"LLM provider '{provider}' is not available yet.")
