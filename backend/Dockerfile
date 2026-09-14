# --- builder: compiles wheels that need build-essential/libpq-dev -----------
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# A venv at a fixed path (rather than `pip install --user`) so the installed
# packages are found the same way regardless of which user runs a command —
# `pip install --user` resolves against $HOME, which differs between the
# app user the entrypoint drops to and root (e.g. `docker exec` defaults to
# root, whose $HOME is /root, not the app user's /home/app).
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- runtime: slim image, no compilers, drops to a non-root user -----------
FROM python:3.11-slim

WORKDIR /app

# Runtime-only system deps: libpq5 (not -dev), tesseract+poppler for OCR/scanned
# CVs, curl for the container healthcheck, gosu to drop root -> app in the
# entrypoint after fixing volume ownership (see docker-entrypoint.sh). No
# build-essential here — smaller image, smaller attack surface.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl gosu \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-vie poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

COPY --from=builder /opt/venv /opt/venv
COPY . .
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN mkdir -p /app/uploads \
    && chown -R app:app /app \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Starts as root (see entrypoint) purely to fix /app/uploads ownership on an
# existing volume, then re-execs everything below as the unprivileged "app"
# user — the app process itself never runs as root.
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
