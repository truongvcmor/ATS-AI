OCR_SYSTEM_PROMPT = """TASK: OCR_EXTRACTION
You are an OCR engine. Transcribe ALL visible text from the image exactly as
it appears, preserving line breaks and reading order (top to bottom, left to
right). Do not translate, summarize, correct spelling, or add commentary —
output only the raw transcribed text, nothing else.
"""

OCR_USER_PROMPT = "Transcribe every piece of text visible in this CV/resume image."


def build_ocr_prompt() -> tuple[str, str]:
    return OCR_SYSTEM_PROMPT, OCR_USER_PROMPT
