"""Text-generation provider contract."""

from typing import Protocol


class TextGenerator(Protocol):
    """Minimal LLM interface to keep application logic provider independent."""

    def generate(self, prompt: str) -> str: ...
