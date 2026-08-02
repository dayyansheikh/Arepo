# Astrolabe backend — FastAPI + uvicorn
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps kept minimal; slim base already has what httpx/websockets need.
# Install Python deps first for layer caching.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application package and metadata.
COPY pyproject.toml ./
COPY astrolabe ./astrolabe
COPY scripts ./scripts

# Non-root runtime user.
RUN useradd --create-home --uid 10001 astro && chown -R astro:astro /app
USER astro

EXPOSE 8000

# Container healthcheck hits the liveness endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "astrolabe.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
