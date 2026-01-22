#!/bin/bash
# Startup script for Mudrex Bot
# Auto-ingests documentation if vector store doesn't exist

set -e

echo "🚀 Starting Mudrex API Bot..."

# Check if vector store exists
if [ ! -f "data/chroma/vectors.pkl" ]; then
    echo "📚 Vector store not found. Ingesting documentation..."
    python3 scripts/ingest_docs.py
    echo "✅ Documentation ingested successfully!"
else
    echo "✅ Vector store found. Skipping ingestion."
fi

# Start the bot
echo "🤖 Starting Telegram bot..."
exec python3 main.py
