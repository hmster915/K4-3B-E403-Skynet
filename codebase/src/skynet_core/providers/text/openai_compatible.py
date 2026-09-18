"""
__init__()  --> configure OpenAI-compatible text generator
generate()  --> system_prompt + user_prompt -> LLM completion text
"""

from typing import Any
import httpx


class OpenAICompatibleTextGenerator:
    """Production TextGenerator adapter for OpenAI-compatible chat completion APIs."""

    # Preflight: Role=Configure text generator | Input=api_key, base_url, model, timeout | Output=OpenAICompatibleTextGenerator | Decision boundary=Store credentials and connection configuration | Failure/Test=Missing configuration validation
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        cleaned_key = api_key.strip()
        cleaned_url = base_url.strip().rstrip("/")
        cleaned_model = model.strip()

        if not cleaned_key:
            raise ValueError("api_key is required")
        if not cleaned_url:
            raise ValueError("base_url is required")
        if not cleaned_model:
            raise ValueError("model is required")

        self._api_key = cleaned_key
        self._base_url = cleaned_url
        self._model = cleaned_model
        self._timeout = timeout

    # Preflight: Role=Generate text from LLM | Input=system_prompt, user_prompt | Output=raw response text | Decision boundary=HTTP POST to OpenAI chat completions | Failure/Test=RuntimeError on HTTP/parsing failure
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, headers=headers, json=payload)
        except Exception as err:
            raise RuntimeError(f"HTTP request to LLM provider failed: {err}") from err

        if response.is_error:
            raise RuntimeError(
                f"LLM provider returned HTTP error {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except Exception as err:
            raise RuntimeError(f"Malformed JSON response from LLM provider: {err}") from err

        if not isinstance(data, dict):
            raise RuntimeError("Malformed LLM provider response: expected JSON object")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError(f"LLM provider response missing 'choices': {data}")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise RuntimeError(f"LLM provider choice is not an object: {first_choice}")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise RuntimeError(f"LLM provider choice missing 'message': {first_choice}")

        content = message.get("content")
        if content is None:
            raise RuntimeError(f"LLM provider choice missing 'content': {message}")

        return content
