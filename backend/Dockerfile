FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for opencv/mediapipe + wget + pngquant
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    wget \
    pngquant \
 && rm -rf /var/lib/apt/lists/*

# Python deps first (better layer caching)
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir -r requirements.txt

# App code
COPY backend/ /app/

# Non-root
RUN useradd -m app && chown -R app:app /app
USER app

EXPOSE 8000

# Healthcheck: use FastAPI's OpenAPI (always present)
HEALTHCHECK --interval=10s --timeout=3s --retries=6 CMD wget -q --spider http://127.0.0.1:8000/openapi.json || exit 1

# Keep workers=1 to reduce memory/startup flakiness while we validate
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000","--workers","1"]