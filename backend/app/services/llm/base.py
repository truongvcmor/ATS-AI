from abc import ABC, abstractmethod


class LLMService(ABC):
    """Provider-agnostic chat/completion abstraction.

    Every caller sends a system + user prompt and expects raw text back
    (expected to be JSON per the prompt's instructions). Callers are
    responsible for validating/parsing the response with Pydantic.
    """

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    def complete_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str) -> str:
        """Optional: send an image alongside the prompt to a vision-capable
        model. Used by the OCR fallback path (app/services/ocr/). Providers
        that can't do this (the mock) simply don't implement it."""
        raise NotImplementedError(f"{type(self).__name__} does not support vision input")
