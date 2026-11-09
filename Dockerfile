FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# audio/ (pre-rendered clips) must exist before building: run scripts/prerender.py first.
# api-key.txt is git-ignored and must NOT be baked in; set GNANI_API_KEY as a host secret instead.
COPY backend ./backend
COPY data ./data
COPY scenarios ./scenarios
COPY frontend ./frontend
COPY audio ./audio

ENV PORT=7860
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT}"]
