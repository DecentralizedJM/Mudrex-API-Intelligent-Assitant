# Mudrex API Documentation Bot - Workspace Instructions

## Project Overview
Telegram bot for answering Mudrex API documentation questions using RAG with Gemini 2.0 Flash.

## Tech Stack
- Python 3.10+
- python-telegram-bot for Telegram integration
- ChromaDB for vector storage
- Google Gemini 2.0 Flash API for LLM
- FastAPI for optional webhook server

## Code Style
- Follow PEP 8
- Use type hints
- Async/await for bot handlers
- Modular architecture with separate concerns

## Project Structure
- `src/bot/` - Telegram bot logic
- `src/rag/` - RAG pipeline and embeddings
- `src/config/` - Configuration management
- `docs/` - API documentation to ingest
- `tests/` - Unit and integration tests
