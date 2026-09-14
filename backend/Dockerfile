# --- builder: compiles wheels that need build-essential/libpq-dev -----------
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- runtime: slim image, no compilers, non-root user ------------------------
FROM python:3.11-slim

WORKDIR /app

# Runtime-only system deps: libpq5 (not -dev), tesseract+poppler for OCR/scanned
# CVs, curl for the container healthcheck. No build-essential here — smaller
# image, smaller attack surface.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-vie poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

COPY --from=builder /root/.local /home/app/.local
COPY . .

RUN mkdir -p /app/uploads && chown -R app:app /app /home/app/.local

USER app
ENV PATH="/home/app/.local/bin:${PATH}" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
