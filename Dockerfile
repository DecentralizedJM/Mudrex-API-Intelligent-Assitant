# Dockerfile for Mudrex API Bot
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for vector store
RUN mkdir -p data/chroma

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Run the bot (startup script will auto-ingest docs if needed)
CMD ["/app/start.sh"]
