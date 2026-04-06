FROM python:3.12-slim

WORKDIR /app

# System deps for Playwright Chromium + asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libx11-6 libx11-xcb1 \
    libxcb1 libxext6 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (scraper + backend, so we can import app.*)
COPY scraper/pyproject.toml /app/scraper/pyproject.toml
COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN pip install --no-cache-dir -e /app/scraper && \
    pip install --no-cache-dir -e /app/backend

# Install Playwright Chromium
RUN playwright install chromium

# Copy source
COPY scraper/ /app/scraper/
COPY backend/ /app/backend/

ENV PYTHONPATH="/app:/app/scraper:/app/backend"
WORKDIR /app
