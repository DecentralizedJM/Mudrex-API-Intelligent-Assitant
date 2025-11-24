"""
Document ingestion pipeline for loading API documentation
"""
import logging
import os
from pathlib import Path
from typing import List, Dict, Any
import hashlib

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loads and preprocesses documentation files"""
    
    @staticmethod
    def load_from_directory(directory: str, extensions: List[str] = None) -> List[Dict[str, Any]]:
        """
        Load all documents from a directory
        
        Args:
            directory: Path to documentation directory
            extensions: List of file extensions to load (default: .md, .txt)
            
        Returns:
            List of dicts with 'content', 'metadata', and 'id'
        """
        if extensions is None:
            extensions = ['.md', '.txt', '.rst']
        
        docs_path = Path(directory)
        if not docs_path.exists():
            logger.warning(f"Directory not found: {directory}")
            return []
        
        documents = []
        
        for file_path in docs_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Create metadata
                    metadata = {
                        'filename': file_path.name,
                        'filepath': str(file_path),
                        'type': file_path.suffix.lstrip('.'),
                        'size': len(content)
                    }
                    
                    # Generate unique ID
                    doc_id = hashlib.md5(str(file_path).encode()).hexdigest()
                    
                    documents.append({
                        'content': content,
                        'metadata': metadata,
                        'id': doc_id
                    })
                    
                    logger.info(f"Loaded: {file_path.name}")
                    
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
        
        logger.info(f"Loaded {len(documents)} documents from {directory}")
        return documents
    
    @staticmethod
    def chunk_document(content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split document into overlapping chunks
        
        Args:
            content: Document content
            chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to break at sentence end
            if end < len(content):
                # Look for sentence ending
                sentence_end = content.rfind('.', start, end)
                if sentence_end != -1 and sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
            
            chunks.append(content[start:end].strip())
            start = end - overlap
        
        return chunks
    
    @staticmethod
    def process_documents(
        documents: List[Dict[str, Any]],
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        Process documents into chunks with metadata
        
        Args:
            documents: List of document dicts
            chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks
            
        Returns:
            Tuple of (texts, metadatas, ids)
        """
        texts = []
        metadatas = []
        ids = []
        
        for doc in documents:
            chunks = DocumentLoader.chunk_document(
                doc['content'],
                chunk_size=chunk_size,
                overlap=overlap
            )
            
            for i, chunk in enumerate(chunks):
                texts.append(chunk)
                
                # Add chunk info to metadata
                chunk_metadata = doc['metadata'].copy()
                chunk_metadata['chunk_index'] = i
                chunk_metadata['total_chunks'] = len(chunks)
                metadatas.append(chunk_metadata)
                
                # Create unique ID for chunk
                chunk_id = f"{doc['id']}_chunk_{i}"
                ids.append(chunk_id)
        
        logger.info(f"Created {len(texts)} chunks from {len(documents)} documents")
        return texts, metadatas, ids
