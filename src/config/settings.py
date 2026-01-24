"""
Configuration management for the Mudrex API Bot
Supports MCP integration and latest Gemini models

Copyright (c) 2025 DecentralizedJM
Licensed under MIT License
"""
import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration"""
    
    # Required - Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Required - Gemini AI
    GEMINI_API_KEY: str = ""
    
    # Mudrex API Credentials (for Public Data Access)
    MUDREX_API_SECRET: Optional[str] = None  # Your personal API secret
    
    # Optional - Access Control
    ALLOWED_CHAT_IDS: Optional[List[int]] = None  # None = all chats allowed
    ADMIN_USER_IDS: Optional[List[int]] = None  # Admin users for escalation
    
    # Gemini AI Settings (NEW SDK)
    GEMINI_MODEL: str = "gemini-3-flash-preview"  # Latest model
    GEMINI_TEMPERATURE: float = 0.4  # Slightly creative but focused
    GEMINI_MAX_TOKENS: int = 2048
    
    # Vector Store
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "mudrex_api_docs"
    
    # RAG Settings
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    TOP_K_RESULTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.55  # Slightly lower for better recall
    
    # Bot Behavior
    MAX_RESPONSE_LENGTH: int = 4000  # Telegram limit is 4096
    ONLY_RESPOND_TO_QUESTIONS: bool = True
    AUTO_DETECT_QUERIES: bool = True
    
    # MCP Settings
    MCP_ENABLED: bool = True
    MCP_BASE_URL: str = "https://mudrex.com/mcp"
    MCP_TIMEOUT: int = 15  # seconds
    
    # Rate Limiting
    RATE_LIMIT_MESSAGES: int = 30  # Max messages per user
    RATE_LIMIT_WINDOW: int = 60  # Per minute
    
    # Google Search Grounding (for out-of-context API questions)
    GEMINI_GROUNDING_MODEL: str = "gemini-2.5-flash"
    
    # Changelog watcher (daily scrape + broadcast to ALLOWED_CHAT_IDS)
    ENABLE_CHANGELOG_WATCHER: bool = True
    CHANGELOG_CRON_HOUR: int = 2  # 2 AM UTC
    CHANGELOG_CRON_MINUTE: int = 0
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        
        # Parse allowed chat IDs
        allowed_chats = os.getenv("ALLOWED_CHAT_IDS")
        chat_ids = None
        if allowed_chats:
            chat_ids = [int(cid.strip()) for cid in allowed_chats.split(",") if cid.strip()]
        
        # Parse admin user IDs
        admin_users = os.getenv("ADMIN_USER_IDS")
        admin_ids = None
        if admin_users:
            admin_ids = [int(uid.strip()) for uid in admin_users.split(",") if uid.strip()]
        
        return cls(
            # Required
            TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", ""),
            
            # Mudrex API Secret (Your Personal Key)
            MUDREX_API_SECRET=os.getenv("MUDREX_API_SECRET") or os.getenv("MUDREX_BOT_KEY"),
            
            # Access Control
            ALLOWED_CHAT_IDS=chat_ids,
            ADMIN_USER_IDS=admin_ids,
            
            # Gemini
            GEMINI_MODEL=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
            GEMINI_TEMPERATURE=float(os.getenv("GEMINI_TEMPERATURE", "0.4")),
            GEMINI_MAX_TOKENS=int(os.getenv("GEMINI_MAX_TOKENS", "2048")),
            
            # Vector Store
            CHROMA_PERSIST_DIR=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"),
            CHROMA_COLLECTION_NAME=os.getenv("CHROMA_COLLECTION_NAME", "mudrex_api_docs"),
            
            # RAG
            EMBEDDING_MODEL=os.getenv("EMBEDDING_MODEL", "models/text-embedding-004"),
            TOP_K_RESULTS=int(os.getenv("TOP_K_RESULTS", "5")),
            SIMILARITY_THRESHOLD=float(os.getenv("SIMILARITY_THRESHOLD", "0.45")),
            
            # Bot
            MAX_RESPONSE_LENGTH=int(os.getenv("MAX_RESPONSE_LENGTH", "4000")),
            ONLY_RESPOND_TO_QUESTIONS=os.getenv("ONLY_RESPOND_TO_QUESTIONS", "true").lower() == "true",
            AUTO_DETECT_QUERIES=os.getenv("AUTO_DETECT_QUERIES", "true").lower() == "true",
            
            # MCP
            MCP_ENABLED=os.getenv("MCP_ENABLED", "true").lower() == "true",
            MCP_BASE_URL=os.getenv("MCP_BASE_URL", "https://mudrex.com/mcp"),
            MCP_TIMEOUT=int(os.getenv("MCP_TIMEOUT", "15")),
            
            # Rate Limiting
            RATE_LIMIT_MESSAGES=int(os.getenv("RATE_LIMIT_MESSAGES", "30")),
            RATE_LIMIT_WINDOW=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
            
            # Grounding and changelog watcher
            GEMINI_GROUNDING_MODEL=os.getenv("GEMINI_GROUNDING_MODEL", "gemini-2.5-flash"),
            ENABLE_CHANGELOG_WATCHER=os.getenv("ENABLE_CHANGELOG_WATCHER", "true").lower() == "true",
            CHANGELOG_CRON_HOUR=int(os.getenv("CHANGELOG_CRON_HOUR", "2")),
            CHANGELOG_CRON_MINUTE=int(os.getenv("CHANGELOG_CRON_MINUTE", "0")),
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not self.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        if not self.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is required")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        return len(self.validate()) == 0


# Global config instance
config = Config.from_env()
