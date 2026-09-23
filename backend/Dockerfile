FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Mount your Firebase service account key at runtime, e.g.:
#   docker run -v /path/to/serviceAccountKey.json:/app/serviceAccountKey.json:ro ...
# and set FIREBASE_SERVICE_ACCOUNT_PATH=/app/serviceAccountKey.json
# On Cloud Run, skip the key: with no key file present the app uses the service's own identity.
#
# Listens on $PORT if set (required by platforms like Cloud Run / Render), else 8000.
# Set CORS_ORIGINS to the frontend's public URL when it's hosted on a different domain.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
