"""
Configuration Management for RAG System
Using Pydantic Settings for type-safe configuration
"""
from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class QdrantSettings(BaseSettings):
    """Qdrant Vector Database Configuration"""
    host: str = Field(default="localhost", description="Qdrant host")
    port: int = Field(default=6333, description="Qdrant port")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class EmbeddingSettings(BaseSettings):
    """Dense Embedding Model Configuration"""
    model_name: str = Field(default="intfloat/multilingual-e5-large", description="HuggingFace model name")
    dimension: int = Field(default=1024, description="Embedding dimension")
    device: Literal["cpu", "cuda", "mps"] = Field(default="cpu", description="Device to use")
    batch_size: int = Field(default=32, description="Batch size for embedding")


class SparseEmbeddingSettings(BaseSettings):
    """Sparse (BM25) Embedding Configuration"""
    model_name: str = Field(default="Qdrant/bm25", description="Sparse embedding model")


class RerankerSettings(BaseSettings):
    """Reranker Model Configuration"""
    model_name: str = Field(default="BAAI/bge-reranker-v2-m3", description="CrossEncoder model")
    device: Literal["cpu", "cuda", "mps"] = Field(default="cpu", description="Device to use")
    batch_size: int = Field(default=32, description="Batch size for reranking")


class LLMSettings(BaseSettings):
    """Large Language Model Configuration"""
    model_name: str = Field(default=None, description="OpenAI model name")
    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    base_url: Optional[str] = Field(default=None, description="Custom API base URL")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=1500, description="Maximum tokens to generate")
    
    model_config = SettingsConfigDict(env_prefix="LLM_")


class SearchSettings(BaseSettings):
    """Search & Retrieval Configuration"""
    top_k: int = Field(default=5, description="Number of final documents to return")
    search_limit_multiplier: int = Field(default=2, description="Multiplier for initial search (top_k * multiplier)")
    rrf_k: int = Field(default=60, description="RRF constant for score fusion")
    rerank_threshold: float = Field(default=0.0, description="Minimum rerank score threshold")
    
    @property
    def search_limit(self) -> int:
        """Calculate search limit for initial retrieval"""
        return self.top_k * self.search_limit_multiplier


class DocumentSettings(BaseSettings):
    """Document Processing Configuration"""
    chunk_size: int = Field(default=1000, description="Characters per chunk")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks")
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")


class DoclingSettings(BaseSettings):
    """Docling Document Conversion Configuration"""
    enable_ocr: bool = Field(default=True, description="Enable OCR for scanned documents")
    ocr_engine: str = Field(default="auto", description="OCR engine: 'auto', 'tesseract', 'easyocr', 'ocrmac'")
    ocr_lang: str = Field(default="tha+eng", description="OCR languages (e.g., 'tha+eng' for Thai+English)")
    table_mode: str = Field(default="accurate", description="Table extraction mode: 'fast' or 'accurate'")
    parse_tables: bool = Field(default=True, description="Extract and parse tables")
    parse_images: bool = Field(default=True, description="Extract image descriptions")
    generate_page_images: bool = Field(default=False, description="Generate page images")
    force_ocr_on_text: bool = Field(default=False, description="Force OCR even if text layer exists")
    image_resolution_scale: int = Field(default=2, description="Image resolution multiplier for OCR")
    enable_vlm: bool = Field(default=False, description="Enable Vision Language Model for picture descriptions/captions")
    clean_artifacts: bool = Field(default=True, description="Clean GLYPH tags and other PDF parsing artifacts")
    fix_thai_encoding: bool = Field(default=True, description="Fix Thai character encoding issues")


class ChatSettings(BaseSettings):
    """Chat Engine Configuration"""
    memory_token_limit: int = Field(default=3000, description="Token limit for chat memory")
    system_prompt: Optional[str] = Field(default=None, description="Custom system prompt")


class OCRSettings(BaseSettings):
    """OCR Service Configuration (Optional)"""
    api_endpoint: Optional[str] = Field(default=None, description="OCR API endpoint")
    api_model: str = Field(default="typhoon-ocr-preview", description="OCR model name")
    
    model_config = SettingsConfigDict(env_prefix="OCR_")


class OpenRouterSettings(BaseSettings):
    """OpenRouter API Configuration for Progressive Document Processing"""
    api_key: Optional[str] = Field(default=None, description="OpenRouter API key")
    use_progressive: bool = Field(default=True, description="Use progressive document processor")
    target_quality: float = Field(default=0.70, description="Target quality threshold (0.0-1.0)")
    fast_threshold: float = Field(default=0.70, description="Fast tier quality threshold")
    balanced_threshold: float = Field(default=0.80, description="Balanced tier quality threshold")
    premium_threshold: float = Field(default=0.85, description="Premium tier quality threshold")
    
    model_config = SettingsConfigDict(env_prefix="OPENROUTER_")


class Settings(BaseSettings):
    """Main Application Settings"""
    # Environment
    env: Literal["development", "production", "testing"] = Field(default="development")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    
    # Component Settings
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    sparse_embedding: SparseEmbeddingSettings = Field(default_factory=SparseEmbeddingSettings)
    reranker: RerankerSettings = Field(default_factory=RerankerSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    document: DocumentSettings = Field(default_factory=DocumentSettings)
    docling: DoclingSettings = Field(default_factory=DoclingSettings)
    chat: ChatSettings = Field(default_factory=ChatSettings)
    ocr: OCRSettings = Field(default_factory=OCRSettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-load LLM API key from environment if not set
        if not self.llm.api_key:
            self.llm.api_key = os.getenv("OPENAI_API_KEY")
        # Auto-load OpenRouter API key from environment if not set
        if not self.openrouter.api_key:
            self.openrouter.api_key = os.getenv("OPENROUTER_API_KEY")


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings():
    """Reload settings (useful for testing)"""
    global _settings
    _settings = None
    return get_settings()
