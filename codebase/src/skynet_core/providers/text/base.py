"""Text-generation provider contract."""

from typing import Protocol


class TextGenerator(Protocol):
    """Minimal LLM interface to keep application logic provider independent."""

    # Preflight: Role=Generate text from LLM | Input=system_prompt str, user_prompt str | Output=raw response text str | Decision boundary=Text generation provider interface | Failure/Test=Provider-specific exception
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str: ...
