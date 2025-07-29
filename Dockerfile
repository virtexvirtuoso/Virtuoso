# Multi-stage build for Virtuoso Trading System
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1001 -s /bin/bash virtuoso

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/virtuoso/.local

# Copy application code
COPY --chown=virtuoso:virtuoso . .

# Create necessary directories
RUN mkdir -p logs reports data && \
    chown -R virtuoso:virtuoso /app

# Switch to non-root user
USER virtuoso

# Add local bin to PATH
ENV PATH=/home/virtuoso/.local/bin:$PATH
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Expose API port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Set Python environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Run the application
CMD ["python", "-u", "src/main.py"]