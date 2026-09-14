import io
import logging

import pytesseract
from PIL import Image

from app.services.ocr.base import OCRService

logger = logging.getLogger(__name__)


class TesseractOCRService(OCRService):
    """Free, offline OCR via the Tesseract binary (apt package `tesseract-ocr`).
    Default OCR backend — works with zero API keys, same "core system works
    without AI" principle as the rest of the AI layer."""

    def extract_text(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Tesseract does best on high-contrast, upright, grayscale input.
            image = image.convert("L")
            return pytesseract.image_to_string(image, lang="eng+vie")
        except Exception:
            logger.error("Tesseract OCR failed", exc_info=True)
            return ""
