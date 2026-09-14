from abc import ABC, abstractmethod


class OCRService(ABC):
    """Turns a single page image into plain text, for scanned/photographed
    CVs (image files, or PDFs with no extractable text layer)."""

    @abstractmethod
    def extract_text(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        raise NotImplementedError
