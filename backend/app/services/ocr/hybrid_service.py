import logging

from app.core.config import settings
from app.services.ocr.base import OCRService

logger = logging.getLogger(__name__)


class HybridOCRService(OCRService):
    """Tries Tesseract first (free, offline). If the result looks too short
    to be a real page of text, falls back to the LLM-vision OCR service —
    "OCR, or another method" when the cheap path isn't good enough."""

    def __init__(self, primary: OCRService, fallback: OCRService | None) -> None:
        self._primary = primary
        self._fallback = fallback

    def extract_text(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        text = self._primary.extract_text(image_bytes, mime_type)
        if len(text.strip()) >= settings.OCR_MIN_TEXT_LENGTH or self._fallback is None:
            return text
        logger.info("Tesseract OCR produced too little text (%d chars), falling back to LLM vision", len(text.strip()))
        fallback_text = self._fallback.extract_text(image_bytes, mime_type)
        return fallback_text if len(fallback_text.strip()) > len(text.strip()) else text
