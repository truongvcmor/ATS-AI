import re
import unicodedata

_WS_RE = re.compile(r"\s+")
_PHONE_RE = re.compile(r"[^\d+]")


def normalize_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def normalize_name(name: str) -> str:
    """Lowercase, strip accents/punctuation so 'Nguyễn Văn A' == 'nguyen van a'."""
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    stripped = re.sub(r"[^a-zA-Z0-9\s]", "", stripped)
    return _WS_RE.sub(" ", stripped).strip().lower()


def normalize_phone(phone: str) -> str:
    digits = _PHONE_RE.sub("", phone)
    # Normalize Vietnamese numbers: +84 / 84 / 0 leading prefixes -> local 0-prefixed form
    if digits.startswith("+84"):
        digits = "0" + digits[3:]
    elif digits.startswith("84") and len(digits) > 9:
        digits = "0" + digits[2:]
    return digits


def normalize_email(email: str) -> str:
    return email.strip().lower()
