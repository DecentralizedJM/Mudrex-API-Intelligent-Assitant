# Dockerfile for Mudrex API Bot
# Production-grade with health checks and metrics
FROM python:3.11-slim

WORKDIR /app

# Cache buster - change value to force full rebuild
ARG CACHEBUST=1
RUN echo "Build: $CACHEBUST"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for vector store (legacy fallback)
RUN mkdir -p data/chroma

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose health check port
EXPOSE 8080

# Environment variables
ENV HEALTH_PORT=8080
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health/live || exit 1

# Run the bot (startup script will auto-ingest docs if needed)
CMD ["/app/start.sh"]
