# ---------------------------------------------------------------------------
# TechLabz Scraper API — production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# Faster, quieter, unbuffered Python.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source.
COPY . .

EXPOSE 8000

# Container-level healthcheck hits the DB-connectivity probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

# The in-process APScheduler runs inside the web dyno, so a single worker keeps
# one scheduler. Scale reads with more workers only if you move scheduling out.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
