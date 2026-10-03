# Hugging Face Spaces (Docker SDK) — Flask + SQLite dashboard
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so the layer caches across deploys
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + SQLite database (data/loans.db is required at runtime)
COPY . .

# HF Spaces routes to the port declared in the Space's README (app_port: 7860)
EXPOSE 7860
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "2", "--timeout", "60", "app:app"]
