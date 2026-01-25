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
from .fact_store import FactStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Coordinates the RAG workflow"""
    
    def __init__(self):
        """Initialize RAG components"""
        self.vector_store = VectorStore()
        self.gemini_client = GeminiClient()
        self.document_loader = DocumentLoader()
        self.fact_store = FactStore()
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
        top_k: int = None,
        mcp_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a query through the RAG pipeline.
        When mcp_context is provided (live MCP data), it is passed to the model as co-pilot context.
        
        Args:
            question: User question
            chat_history: Optional conversation history
            top_k: Number of documents to retrieve
            mcp_context: Optional live data from MCP (list_futures, get_future, etc.)
            
        Returns:
            Dict with 'answer', 'sources', and 'is_relevant'
        """
        # 1. Check Fact Store (Strict Rules) - PRIORITY OVER EVERYTHING
        fact_match = self.fact_store.search(question)
        if fact_match:
            logger.info(f"Fact Match found for query: {question}")
            return {
                'answer': fact_match,
                'sources': [{'filename': 'FactStore (Strict User Rule)', 'similarity': 1.0}],
                'is_relevant': True
            }

        # NOTE: is_api_related check is now done in telegram_bot.py (handle_message)
        # Pipeline should always process what gets to it after that gatekeeper check
        
        # 2. Retrieve relevant documents
        logger.info(f"Processing query: {question[:50]}...")
        retrieved_docs = self.vector_store.search(question, top_k=top_k)
        
        # DEBUG: Log retrieval scores
        if retrieved_docs:
            logger.info("Top retrieved docs:")
            for doc in retrieved_docs:
                logger.info(f"- {doc['metadata'].get('filename')}: {doc['similarity']:.4f}")
        else:
            logger.info("No docs retrieved above threshold")
            
        if not retrieved_docs:
            # API-related but RAG empty: use Google Search grounding
            logger.info("No RAG docs; using Google Search grounding for API-related query")
            answer = self.gemini_client.generate_response_with_grounding(
                question, [], chat_history, mcp_context
            )
            return {
                'answer': answer,
                'sources': [{'filename': 'Google Search (grounding)', 'similarity': 0.0}],
                'is_relevant': True
            }
        
        # Generate response (with optional MCP live data for co-pilot)
        answer = self.gemini_client.generate_response(
            question,
            retrieved_docs,
            chat_history,
            mcp_context,
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

    def learn_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Learn new unstructured text (Admin only). Chunks long text. Optional metadata (e.g. source, filename)."""
        base = metadata or {}
        if len(text) > 1500:
            chunks = self.document_loader.chunk_document(text, chunk_size=1000, overlap=200)
            metadatas = [dict(base, chunk_index=i, total_chunks=len(chunks)) for i in range(len(chunks))]
            self.vector_store.add_documents(chunks, metadatas, None)
            logger.info(f"Learned {len(chunks)} chunks ({len(text)} chars)")
        else:
            self.vector_store.add_documents([text], [base], None)
            logger.info(f"Learned new text: {text[:50]}...")

    def set_fact(self, key: str, value: str) -> None:
        """Set a strict fact (Admin only)"""
        self.fact_store.set(key, value)

    def delete_fact(self, key: str) -> bool:
        """Delete a strict fact (Admin only)"""
        return self.fact_store.delete(key)
