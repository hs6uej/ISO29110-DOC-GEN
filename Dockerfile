FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_BASE_DIR=/app \
    DATA_DIR=/app/data \
    STORAGE_DIR=/app/storage \
    SECRETS_DIR=/app/secrets \
    PORT=8290

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p data storage secrets

# actual port = PORT from .env (docker-compose env_file), default 8290
EXPOSE 8290
CMD ["python", "-m", "app"]
