FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/pricetracker

# Install system deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgbm1 libasound2 libpangocairo-1.0-0 libgtk-3-0 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    libxshmfence1 fonts-liberation xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy only worker files
COPY worker worker

# Install worker dependencies directly
RUN --mount=type=cache,sharing=locked,target=/root/.cache/pip \
    pip install \
        beautifulsoup4 \
        playwright \
        ollama \
        openai \
        requests

# Install Playwright browsers
RUN playwright install chromium

CMD ["python", "-m", "worker.app"]
