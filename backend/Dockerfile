# backend/Dockerfile — Spetser AI API (Phase 12, Lesson 12.1)
# Multi-stage: install deps as root, run as non-root.

FROM python:3.11-slim AS builder

WORKDIR /build

# Build tools for any wheels that need compiling (bcrypt, cryptography, asyncpg)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Package metadata + sources required for `pip install .` (setuptools find)
COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Runtime libs for asyncpg / Pillow / cryptography
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/false --create-home app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

# Liveness only — readiness needs DB and is checked by compose/k8s separately.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/v1/health/live || exit 1

# Single worker by default; scale with uvicorn --workers or a process manager.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
