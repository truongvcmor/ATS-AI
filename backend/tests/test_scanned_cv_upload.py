import io
import time

from PIL import Image, ImageDraw, ImageFont

from tests.test_candidates import _upload_and_wait


def _render_cv_image() -> bytes:
    image = Image.new("RGB", (1000, 600), color="white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    lines = [
        "TRAN THI SCANNED",
        "scanned.candidate@example.com",
        "0955555555",
        "Ho Chi Minh City",
        "",
        "SUMMARY",
        "Backend Engineer with 5 years of experience.",
        "",
        "SKILLS",
        "Python, FastAPI, Docker",
    ]
    y = 20
    for line in lines:
        draw.text((20, y), line, fill="black", font=font)
        y += 45
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_scanned_image_cv_is_ocred_and_parsed(client, auth_headers):
    image_bytes = _render_cv_image()
    job = _upload_and_wait(client, auth_headers, image_bytes, filename="scanned_cv.png", timeout=20)
    assert job["status"] == "COMPLETED", job.get("error_message")
    assert job["candidate_id"]

    detail = client.get(f"/api/candidates/{job['candidate_id']}", headers=auth_headers).json()
    assert "SCANNED" in detail["full_name"].upper()
    assert len(detail["cvs"]) == 1
    assert detail["cvs"][0]["extraction_method"] == "ocr"
