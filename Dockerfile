FROM python:3.11-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + the vetted knowledge base.
COPY app ./app

# SQLite lives on a persistent disk in production (see render.yaml).
ENV DB_PATH=/data/ayuda.db
ENV BOT_MODEL=claude-haiku-4-5

EXPOSE 8000

# Render/Railway/Fly inject $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
