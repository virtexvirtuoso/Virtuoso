# Virtuoso CCXT Trading System - Docker Image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better cache utilization
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data cache config

# Environment variables with defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_PORT=8003 \
    MONITORING_PORT=8001 \
    API_PORT=8002 \
    MEMCACHED_HOST=memcached \
    REDIS_HOST=redis \
    ENABLE_MULTI_TIER_CACHE=true \
    ENABLE_UNIFIED_ENDPOINTS=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Expose ports
EXPOSE 8001 8002 8003

# Start script that launches both services
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["all"]