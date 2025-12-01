#!/usr/bin/env python3
"""Test new configuration system"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config import get_settings
from src.utils import get_logger

def test_config():
    """Test configuration loading"""
    print("🧪 Testing Configuration System...\n")
    
    # Load settings
    settings = get_settings()
    
    print("✅ Settings loaded successfully!")
    print(f"   Environment: {settings.env}")
    print(f"   Debug: {settings.debug}")
    print(f"   Log Level: {settings.log_level}")
    
    print(f"\n📊 Qdrant Configuration:")
    print(f"   URL: {settings.qdrant.url}")
    print(f"   Timeout: {settings.qdrant.timeout}s")
    
    print(f"\n🤖 Model Configuration:")
    print(f"   Embedding: {settings.embedding.model_name} ({settings.embedding.dimension}d)")
    print(f"   Sparse: {settings.sparse_embedding.model_name}")
    print(f"   Reranker: {settings.reranker.model_name}")
    print(f"   LLM: {settings.llm.model_name}")
    
    print(f"\n🔍 Search Configuration:")
    print(f"   top_k: {settings.search.top_k}")
    print(f"   search_limit: {settings.search.search_limit}")
    print(f"   rrf_k: {settings.search.rrf_k}")
    
    print(f"\n📄 Document Configuration:")
    print(f"   chunk_size: {settings.document.chunk_size}")
    print(f"   chunk_overlap: {settings.document.chunk_overlap}")
    
    # Test logger
    print(f"\n📝 Testing Logger...")
    logger = get_logger(__name__)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    print(f"\n✅ All tests passed!")

if __name__ == "__main__":
    test_config()
