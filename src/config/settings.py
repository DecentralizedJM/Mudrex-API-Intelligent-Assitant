"""
Configuration management for the Mudrex API Bot
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration"""
    
    # Required fields (no defaults)
    TELEGRAM_BOT_TOKEN: str
    GEMINI_API_KEY: str
    
    # Optional fields (with defaults)
    ALLOWED_CHAT_IDS: Optional[list[int]] = None  # None = all chats allowed
    
    # Gemini AI
    GEMINI_MODEL: str = "gemini-3-pro-preview"
    GEMINI_TEMPERATURE: float = 0.3
    GEMINI_MAX_TOKENS: int = 1024
    
    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "mudrex_api_docs"
    
    # RAG Settings
    EMBEDDING_MODEL: str = "models/text-embedding-004"  # Gemini embedding
    TOP_K_RESULTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.6
    
    # Bot Behavior
    MAX_RESPONSE_LENGTH: int = 4000  # Telegram message limit is 4096
    ONLY_RESPOND_TO_QUESTIONS: bool = True
    AUTO_DETECT_QUERIES: bool = True
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        
        # Parse allowed chat IDs if provided
        allowed_chats = os.getenv("ALLOWED_CHAT_IDS")
        chat_ids = None
        if allowed_chats:
            chat_ids = [int(chat_id.strip()) for chat_id in allowed_chats.split(",")]
        
        return cls(
            TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            ALLOWED_CHAT_IDS=chat_ids,
            GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", ""),
            GEMINI_MODEL=os.getenv("GEMINI_MODEL", "gemini-3-pro-preview"),
            GEMINI_TEMPERATURE=float(os.getenv("GEMINI_TEMPERATURE", "0.3")),
            GEMINI_MAX_TOKENS=int(os.getenv("GEMINI_MAX_TOKENS", "1024")),
            CHROMA_PERSIST_DIR=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"),
            CHROMA_COLLECTION_NAME=os.getenv("CHROMA_COLLECTION_NAME", "mudrex_api_docs"),
            EMBEDDING_MODEL=os.getenv("EMBEDDING_MODEL", "models/text-embedding-004"),
            TOP_K_RESULTS=int(os.getenv("TOP_K_RESULTS", "5")),
            SIMILARITY_THRESHOLD=float(os.getenv("SIMILARITY_THRESHOLD", "0.6")),
            MAX_RESPONSE_LENGTH=int(os.getenv("MAX_RESPONSE_LENGTH", "4000")),
            ONLY_RESPOND_TO_QUESTIONS=os.getenv("ONLY_RESPOND_TO_QUESTIONS", "true").lower() == "true",
            AUTO_DETECT_QUERIES=os.getenv("AUTO_DETECT_QUERIES", "true").lower() == "true",
        )


# Global config instance
config = Config.from_env()
