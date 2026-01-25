"""
Vector database handler using simple file-based storage with sklearn
Updated to use NEW google-genai SDK for embeddings

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License
"""
import logging
from typing import List, Optional, Dict, Any
import pickle
import os
from pathlib import Path
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from google import genai

from ..config import config

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages document storage and retrieval using simple file-based vector storage"""
    
    def __init__(self):
        """Initialize vector store"""
        self.persist_dir = Path(config.CHROMA_PERSIST_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_file = self.persist_dir / "vectors.pkl"
        
        # Set API key in environment
        if config.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = config.GEMINI_API_KEY
        
        # Initialize new Gemini client for embeddings
        self.client = genai.Client()
        
        # Load existing database or create new
        if self.db_file.exists():
            self._load_db()
        else:
            self.documents = []
            self.embeddings = []
            self.metadatas = []
            self.ids = []
        
        logger.info(f"Initialized vector store with {len(self.documents)} documents")
    
    def _load_db(self):
        """Load database from disk"""
        with open(self.db_file, 'rb') as f:
            data = pickle.load(f)
            self.documents = data.get('documents', [])
            self.embeddings = data.get('embeddings', [])
            self.metadatas = data.get('metadatas', [])
            self.ids = data.get('ids', [])
    
    def _save_db(self):
        """Save database to disk"""
        with open(self.db_file, 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'embeddings': self.embeddings,
                'metadatas': self.metadatas,
                'ids': self.ids
            }, f)
    
    def _get_embedding(self, text: str, retries: int = 1) -> List[float]:
        """Get embedding for text using NEW Gemini SDK with retry logic"""
        import time
        for attempt in range(retries + 1):
            try:
                # Use the new SDK format for embeddings
                result = self.client.models.embed_content(
                    model=config.EMBEDDING_MODEL,
                    contents=text,
                )
                return result.embeddings[0].values
            except Exception as e:
                if attempt < retries:
                    logger.warning(f"Embedding retry {attempt + 1}/{retries}: {e}")
                    time.sleep(0.5)  # Brief pause before retry
                    continue
                logger.error(f"Embedding failed after {retries + 1} attempts: {e}")
                raise  # Let caller handle gracefully instead of returning broken zero vector
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Add documents to the vector store
        
        Args:
            documents: List of text documents to add
            metadatas: Optional metadata for each document
            ids: Optional unique IDs for documents (auto-generated if not provided)
        """
        if not documents:
            logger.warning("No documents provided to add")
            return
        
        # Generate IDs if not provided
        if ids is None:
            import hashlib
            ids = [hashlib.md5(doc.encode()).hexdigest() for doc in documents]
        
        # Generate metadatas if not provided
        if metadatas is None:
            metadatas = [{}] * len(documents)
        
        # Get embeddings for all documents
        logger.info(f"Generating embeddings for {len(documents)} documents...")
        for doc, metadata, doc_id in zip(documents, metadatas, ids):
            embedding = self._get_embedding(doc)
            
            self.documents.append(doc)
            self.embeddings.append(embedding)
            self.metadatas.append(metadata)
            self.ids.append(doc_id)
        
        # Save to disk
        self._save_db()
        
        logger.info(f"Added {len(documents)} documents to vector store")
    
    def search(
        self,
        query: str,
        top_k: int = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query: Search query text
            top_k: Number of results to return (default from config)
            filter_metadata: Optional metadata filters
            
        Returns:
            List of dicts containing document, metadata, and similarity
        """
        if top_k is None:
            top_k = config.TOP_K_RESULTS
        
        if not self.documents:
            logger.warning("No documents in vector store")
            return []
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        query_vector = np.array(query_embedding).reshape(1, -1)
        
        # Calculate similarities
        doc_vectors = np.array(self.embeddings)
        similarities = cosine_similarity(query_vector, doc_vectors)[0]
        
        # Get top k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Format results
        formatted_results = []
        for idx in top_indices:
            similarity = float(similarities[idx])
            
            # Filter by similarity threshold
            if similarity >= config.SIMILARITY_THRESHOLD:
                # Apply metadata filter if provided
                if filter_metadata:
                    match = all(
                        self.metadatas[idx].get(k) == v 
                        for k, v in filter_metadata.items()
                    )
                    if not match:
                        continue
                
                formatted_results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadatas[idx],
                    'similarity': similarity,
                    'distance': 1 - similarity
                })
        
        logger.info(f"Found {len(formatted_results)} relevant documents for query")
        return formatted_results
    
    def clear(self) -> None:
        """Clear all documents from the collection"""
        self.documents = []
        self.embeddings = []
        self.metadatas = []
        self.ids = []
        self._save_db()
        logger.info("Cleared vector store")
    
    def get_count(self) -> int:
        """Get the number of documents in the store"""
        return len(self.documents)
