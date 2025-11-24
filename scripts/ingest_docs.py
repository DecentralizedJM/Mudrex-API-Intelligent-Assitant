"""
Script to ingest API documentation into the vector database
"""
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import RAGPipeline
from src.config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Ingest documentation files"""
    logger.info("Starting document ingestion...")
    
    # Initialize pipeline
    pipeline = RAGPipeline()
    
    # Ingest documents from docs/ directory
    docs_dir = Path(__file__).parent.parent / "docs"
    
    if not docs_dir.exists():
        logger.error(f"Documentation directory not found: {docs_dir}")
        logger.info("Please create a 'docs/' folder and add your API documentation")
        sys.exit(1)
    
    # Ingest
    num_chunks = pipeline.ingest_documents(str(docs_dir))
    
    if num_chunks > 0:
        logger.info(f"✓ Successfully ingested {num_chunks} chunks")
        logger.info(f"✓ Vector database: {config.CHROMA_PERSIST_DIR}")
    else:
        logger.warning("No documents were ingested")
        logger.info("Add .md, .txt, or .rst files to the docs/ directory")


if __name__ == "__main__":
    main()
