FROM python:3.12-slim

# Force rebuild: 2025-03-05-07-20
ARG BUILD_DATE=2025-03-05

WORKDIR /app

# System deps for faster-whisper (ctranslate2)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
