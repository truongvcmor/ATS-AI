from functools import lru_cache

from app.core.runtime_config import get_ai_config
from app.services.llm.factory import get_llm_service, has_configured_llm_keys
from app.services.ocr.base import OCRService
from app.services.ocr.tesseract_service import TesseractOCRService


@lru_cache
def get_ocr_service() -> OCRService:
    tesseract = TesseractOCRService()
    ocr_provider = get_ai_config().ocr_provider

    if ocr_provider == "tesseract":
        return tesseract

    if ocr_provider == "llm_vision":
        if not has_configured_llm_keys():
            return tesseract  # no key configured — fall back to the free path rather than error
        from app.services.ocr.llm_vision_service import LLMVisionOCRService

        return LLMVisionOCRService(get_llm_service())

    # "auto": Tesseract first, LLM vision as a fallback if a real key is configured.
    from app.services.ocr.hybrid_service import HybridOCRService

    llm_fallback = None
    if has_configured_llm_keys():
        from app.services.ocr.llm_vision_service import LLMVisionOCRService

        llm_fallback = LLMVisionOCRService(get_llm_service())
    return HybridOCRService(tesseract, llm_fallback)
