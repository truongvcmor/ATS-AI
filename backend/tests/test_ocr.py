import io

from PIL import Image, ImageDraw, ImageFont

from app.services.cv_parser.extractors import extract_text
from app.services.ocr.tesseract_service import TesseractOCRService


def _render_text_image(text: str) -> bytes:
    image = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 60), text, fill="black", font=font)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_tesseract_extracts_text_from_a_rendered_image():
    image_bytes = _render_text_image("NGUYEN VAN A")
    text = TesseractOCRService().extract_text(image_bytes, "image/png")
    assert "NGUYEN" in text.upper()


def test_extract_text_routes_image_extension_through_ocr():
    image_bytes = _render_text_image("PYTHON DEVELOPER")
    text, method = extract_text(image_bytes, ".png")
    assert method == "ocr"
    assert "PYTHON" in text.upper()


def test_extract_text_unsupported_extension_raises():
    import pytest

    with pytest.raises(ValueError):
        extract_text(b"not a real file", ".exe")
