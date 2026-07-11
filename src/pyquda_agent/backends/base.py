"""Abstract base class for text generation backends."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class LLMBackend(ABC):
    """Minimal text-generation interface used by the MVP."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name."""

    @abstractmethod
    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return generated text for the given prompts."""
