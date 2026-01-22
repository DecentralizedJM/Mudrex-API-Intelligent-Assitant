"""
RAG Pipeline - Orchestrates the retrieval and generation process

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License - See LICENSE file for details.
"""
import logging
from typing import List, Dict, Any, Optional

from .vector_store import VectorStore
from .gemini_client import GeminiClient
from .document_loader import DocumentLoader

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Coordinates the RAG workflow"""
    
    def __init__(self):
        """Initialize RAG components"""
        self.vector_store = VectorStore()
        self.gemini_client = GeminiClient()
        self.document_loader = DocumentLoader()
        logger.info("RAG Pipeline initialized")
    
    def ingest_documents(self, docs_directory: str) -> int:
        """
        Ingest documents from a directory into the vector store
        
        Args:
            docs_directory: Path to documentation directory
            
        Returns:
            Number of chunks added
        """
        logger.info(f"Starting document ingestion from: {docs_directory}")
        
        # Load documents
        documents = self.document_loader.load_from_directory(docs_directory)
        
        if not documents:
            logger.warning("No documents found to ingest")
            return 0
        
        # Process and chunk documents
        texts, metadatas, ids = self.document_loader.process_documents(documents)
        
        # Add to vector store
        self.vector_store.add_documents(texts, metadatas, ids)
        
        logger.info(f"Successfully ingested {len(texts)} chunks from {len(documents)} documents")
        return len(texts)
    
    def query(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = None
    ) -> Dict[str, Any]:
        """
        Process a query through the RAG pipeline
        
        Args:
            question: User question
            chat_history: Optional conversation history
            top_k: Number of documents to retrieve
            
        Returns:
            Dict with 'answer', 'sources', and 'is_relevant'
        """
        # Check if query is API-related
        is_api_related = self.gemini_client.is_api_related_query(question)
        
        if not is_api_related:
            return {
                'answer': "I'm here to help with Mudrex API questions only. Please ask about API endpoints, authentication, integration, or technical documentation.",
                'sources': [],
                'is_relevant': False
            }
        
        # Retrieve relevant documents
        logger.info(f"Processing query: {question[:50]}...")
        retrieved_docs = self.vector_store.search(question, top_k=top_k)
        
        if not retrieved_docs:
            return {
                'answer': "I couldn't find relevant information in the documentation. Could you rephrase your question or check the official Mudrex API documentation?",
                'sources': [],
                'is_relevant': True
            }
        
        # Generate response
        answer = self.gemini_client.generate_response(
            question,
            retrieved_docs,
            chat_history
        )
        
        # Extract sources
        sources = [
            {
                'filename': doc['metadata'].get('filename', 'Unknown'),
                'similarity': doc['similarity']
            }
            for doc in retrieved_docs[:3]  # Top 3 sources
        ]
        
        return {
            'answer': answer,
            'sources': sources,
            'is_relevant': True
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return {
            'total_documents': self.vector_store.get_count(),
            'model': self.gemini_client.model_name
        }
