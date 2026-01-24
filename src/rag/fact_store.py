"""
Fact Store for Mudrex Bot
Manages strict key-value pairs that override RAG retrieval.
Persists data to a JSON file.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any

from ..config import config

logger = logging.getLogger(__name__)

class FactStore:
    """
    Manages strict facts (Key-Value pairs).
    Example: "LATENCY" -> "200ms"
    These facts take precedence over RAG retrieval.
    """
    
    def __init__(self):
        """Initialize FactStore"""
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.file_path = self.data_dir / "facts.json"
        self.facts: Dict[str, str] = {}
        self._load()
    
    def _load(self):
        """Load facts from JSON file"""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r') as f:
                    self.facts = json.load(f)
                logger.info(f"Loaded {len(self.facts)} facts from store")
            except Exception as e:
                logger.error(f"Error loading facts: {e}")
                self.facts = {}
        else:
            self.facts = {}
    
    def _save(self):
        """Save facts to JSON file"""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.facts, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving facts: {e}")
    
    def set(self, key: str, value: str) -> None:
        """Set a fact"""
        self.facts[key.upper()] = value
        self._save()
        logger.info(f"Set fact: {key} = {value}")
    
    def get(self, key: str) -> Optional[str]:
        """Get a fact by key (case-insensitive)"""
        return self.facts.get(key.upper())
    
    def delete(self, key: str) -> bool:
        """Delete a fact"""
        if key.upper() in self.facts:
            del self.facts[key.upper()]
            self._save()
            logger.info(f"Deleted fact: {key}")
            return True
        return False
    
    def get_all(self) -> Dict[str, str]:
        """Get all facts"""
        return self.facts.copy()
    
    def search(self, query: str) -> Optional[str]:
        """
        Simple keyword search in facts.
        If query contains a strict key, return its value.
        """
        query_upper = query.upper()
        for key, value in self.facts.items():
            if key in query_upper:
                return f"**{key}**: {value}"
        return None
