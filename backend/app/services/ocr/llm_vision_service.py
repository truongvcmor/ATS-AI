import logging

from app.prompts.ocr import build_ocr_prompt
from app.services.llm.base import LLMService
from app.services.ocr.base import OCRService

logger = logging.getLogger(__name__)


class LLMVisionOCRService(OCRService):
    """OCR "by other means": sends the page image to a vision-capable model
    (OpenAI/Gemini, via the same rotating key pool used for screening) and
    asks it to transcribe the text verbatim. Higher accuracy than Tesseract
    on messy scans/handwriting, but requires a real API key."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    def extract_text(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        system_prompt, user_prompt = build_ocr_prompt()
        try:
            return self._llm.complete_vision(system_prompt, user_prompt, image_bytes, mime_type)
        except Exception:
            logger.error("LLM vision OCR failed", exc_info=True)
            return ""
