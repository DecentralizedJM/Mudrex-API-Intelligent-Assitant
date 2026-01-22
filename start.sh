#!/bin/bash
# Startup script for Mudrex Bot
# Auto-ingests documentation if vector store doesn't exist

set -e

echo "🚀 Starting Mudrex API Bot..."

# Check if docs directory exists
if [ ! -d "docs" ]; then
    echo "⚠️  WARNING: docs/ directory not found!"
    echo "📚 Creating docs directory and scraping documentation..."
    python3 scripts/scrape_docs.py || {
        echo "❌ Failed to scrape docs. Continuing without RAG knowledge base..."
    }
fi

# Check if vector store exists
if [ ! -f "data/chroma/vectors.pkl" ]; then
    echo "📚 Vector store not found. Ingesting documentation..."
    
    # Check if docs exist
    if [ ! -d "docs" ] || [ -z "$(ls -A docs/*.md 2>/dev/null)" ]; then
        echo "⚠️  WARNING: No documentation files found in docs/ directory!"
        echo "📚 Attempting to scrape documentation..."
        python3 scripts/scrape_docs.py || {
            echo "❌ Failed to scrape docs. Bot will run without RAG knowledge base."
            echo "🤖 Starting Telegram bot (without RAG)..."
            exec python3 main.py
        }
    fi
    
    # Ingest documentation
    echo "📖 Ingesting documentation files..."
    python3 scripts/ingest_docs.py || {
        echo "❌ Failed to ingest docs. Bot will run without RAG knowledge base."
        echo "🤖 Starting Telegram bot (without RAG)..."
        exec python3 main.py
    }
    
    # Verify ingestion
    if [ -f "data/chroma/vectors.pkl" ]; then
        echo "✅ Documentation ingested successfully!"
    else
        echo "⚠️  WARNING: Vector store file not created. Bot will run without RAG."
    fi
else
    echo "✅ Vector store found. Skipping ingestion."
fi

# Start the bot
echo "🤖 Starting Telegram bot..."
exec python3 main.py
