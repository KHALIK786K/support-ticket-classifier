# syntax=docker/dockerfile:1.7

# ============================================================================
# Multi-stage build for the ticket-classifier API.
# Stage 1 installs dependencies and trains the initial model.
# Stage 2 produces a slim runtime image.
# ============================================================================

ARG PYTHON_VERSION=3.10

# ---- builder ---------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt ./
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---- runtime ---------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Create a non-root user
RUN groupadd --system app && useradd --system --gid app --create-home --home-dir /home/app app

WORKDIR /app

# Install wheels built in stage 1
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# App code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY models/ ./models/

# Pre-download NLTK assets so cold start is fast
RUN python -c "import nltk; \
    [nltk.download(p, quiet=True) for p in ['punkt','punkt_tab','stopwords','wordnet','omw-1.4']]"

RUN chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request, sys; \
        sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status==200 else sys.exit(1)"

# Gunicorn with uvicorn workers — the canonical FastAPI prod combo.
CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--access-logfile", "-"]
