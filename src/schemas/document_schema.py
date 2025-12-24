"""
Document Schema - Unified format for all extraction outputs

Provides standardized schema for documents regardless of extraction tier:
- Document-level metadata
- Page-level structure
- Quality metrics
- Extraction provenance
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ExtractionTier(str, Enum):
    """Extraction tier used"""
    FAST = "fast"
    BALANCED = "balanced"
    PREMIUM = "premium"


class ExtractionMethod(str, Enum):
    """Specific extraction method/model"""
    DOCLING = "docling"
    MARKITDOWN = "markitdown"
    GEMINI_FLASH = "gemini-flash"
    GEMINI_PRO = "gemini-pro"
    CLAUDE = "claude"
    GPT4O = "gpt4o"


class QualityMetrics(BaseModel):
    """Quality scoring across 5 dimensions"""
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality (weighted average)")
    text_quality: float = Field(..., ge=0.0, le=1.0, description="Text cleanliness (no GLYPH, artifacts)")
    word_quality: float = Field(..., ge=0.0, le=1.0, description="Word completeness (no broken words)")
    consistency: float = Field(..., ge=0.0, le=1.0, description="Page-to-page consistency")
    structure_quality: float = Field(..., ge=0.0, le=1.0, description="Document structure (headers, lists, tables)")
    content_density: float = Field(..., ge=0.0, le=1.0, description="Content richness")
    issues: List[str] = Field(default_factory=list, description="Quality issues detected")
    recommendations: List[str] = Field(default_factory=list, description="Improvement suggestions")


class ExtractionInfo(BaseModel):
    """Extraction process information"""
    tier_used: ExtractionTier = Field(..., description="Final tier used for extraction")
    tiers_attempted: List[ExtractionTier] = Field(..., description="All tiers attempted")
    extraction_method: ExtractionMethod = Field(..., description="Specific extraction method")
    timestamp: datetime = Field(default_factory=datetime.now, description="Extraction timestamp")
    processing_time: float = Field(..., description="Total processing time (seconds)")
    cost: float = Field(default=0.0, description="Extraction cost (USD)")
    
    # Tier comparison (if multiple tiers were tried)
    tier_comparison: Optional[Dict[str, Any]] = Field(None, description="Quality comparison across tiers")


class DocumentStats(BaseModel):
    """Document statistics"""
    total_pages: int = Field(..., description="Number of pages")
    total_chars: int = Field(..., description="Total characters")
    total_words: int = Field(..., description="Total words")
    total_headers: int = Field(0, description="Number of headers")
    total_tables: int = Field(0, description="Number of tables")
    total_paragraphs: int = Field(0, description="Number of paragraphs")
    total_lists: int = Field(0, description="Number of lists")
    avg_chars_per_page: float = Field(0.0, description="Average characters per page")
    avg_words_per_page: float = Field(0.0, description="Average words per page")


class StructureElement(BaseModel):
    """Document structure element (header, table, paragraph, list)"""
    type: str = Field(..., description="Element type: header, table, paragraph, list")
    text: str = Field(..., description="Element text content")
    position: int = Field(..., description="Character position in page")
    length: int = Field(..., description="Character length")
    level: Optional[int] = Field(None, description="Level for headers (1-6)")
    
    # Table-specific
    rows: Optional[int] = Field(None, description="Number of rows (tables only)")
    cols: Optional[int] = Field(None, description="Number of columns (tables only)")
    markdown: Optional[str] = Field(None, description="Markdown representation (tables only)")


class PageContent(BaseModel):
    """Page-level content in multiple formats"""
    raw_markdown: str = Field(..., description="Original markdown from extraction")
    cleaned_markdown: str = Field(..., description="Cleaned markdown (artifacts removed)")
    plain_text: str = Field(..., description="Plain text (no formatting)")
    html: Optional[str] = Field(None, description="HTML representation (optional)")


class PageMetadata(BaseModel):
    """Page-level metadata"""
    page_id: str = Field(..., description="Unique page identifier")
    page_number: int = Field(..., description="Page number (1-based)")
    document_id: str = Field(..., description="Parent document ID")
    
    language: str = Field(default="th", description="Primary language")
    char_count: int = Field(..., description="Character count")
    word_count: int = Field(..., description="Word count")
    has_images: bool = Field(default=False, description="Contains images")
    has_tables: bool = Field(default=False, description="Contains tables")
    has_lists: bool = Field(default=False, description="Contains lists")
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")


class PageData(BaseModel):
    """Complete page data"""
    content: PageContent
    structure: List[StructureElement] = Field(default_factory=list, description="Structured elements")
    metadata: PageMetadata


class NormalizedDocument(BaseModel):
    """Unified document format (tier-agnostic)"""
    # Core identifiers
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="SHA-256 hash of file content")
    uploaded_at: datetime = Field(default_factory=datetime.now, description="Upload timestamp")
    
    # Extraction metadata
    extraction: ExtractionInfo = Field(..., description="Extraction process info")
    quality: QualityMetrics = Field(..., description="Quality metrics")
    stats: DocumentStats = Field(..., description="Document statistics")
    
    # Content
    pages: List[PageData] = Field(..., description="Page-level data")
    
    # Optional fields
    kb_name: Optional[str] = Field(None, description="Target knowledge base")
    user_metadata: Dict[str, Any] = Field(default_factory=dict, description="User-provided metadata")


class ChunkPosition(BaseModel):
    """Chunk position information"""
    page_number: int = Field(..., description="Page number (1-based)")
    chunk_index: int = Field(..., description="Chunk index within page")
    char_start: int = Field(..., description="Start character position")
    char_end: int = Field(..., description="End character position")


class ChunkContext(BaseModel):
    """Chunk context (for RAG retrieval)"""
    prev_chunk_id: Optional[str] = Field(None, description="Previous chunk ID")
    next_chunk_id: Optional[str] = Field(None, description="Next chunk ID")
    parent_headers: List[str] = Field(default_factory=list, description="Parent header hierarchy")
    section_path: List[str] = Field(default_factory=list, description="Section path (breadcrumb)")


class ChunkMetadata(BaseModel):
    """Rich metadata for chunk"""
    # Core IDs
    chunk_id: str = Field(..., description="Unique chunk identifier")
    page_id: str = Field(..., description="Parent page ID")
    document_id: str = Field(..., description="Parent document ID")
    
    # Document context
    filename: str = Field(..., description="Original filename")
    kb_name: str = Field(..., description="Knowledge base name")
    
    # Extraction context
    extraction_tier: ExtractionTier = Field(..., description="Tier used for extraction")
    extraction_quality: float = Field(..., ge=0.0, le=1.0, description="Extraction quality score")
    extraction_method: ExtractionMethod = Field(..., description="Extraction method")
    
    # Position context
    position: ChunkPosition = Field(..., description="Position information")
    context: ChunkContext = Field(..., description="Context information")
    
    # Content metadata
    language: str = Field(default="th", description="Language")
    chunk_type: str = Field(default="paragraph", description="Chunk type: paragraph, table, header, list")
    contains_table: bool = Field(default=False, description="Contains table")
    contains_numbers: bool = Field(default=False, description="Contains numbers")
    entity_types: List[str] = Field(default_factory=list, description="Entity types detected")
    
    # Upload metadata
    upload_date: str = Field(..., description="Upload date (ISO format)")


class DocumentChunk(BaseModel):
    """Chunk ready for RAG indexing"""
    text: str = Field(..., description="Chunk text content")
    metadata: ChunkMetadata = Field(..., description="Rich metadata")


class TierComparison(BaseModel):
    """Comparison between extraction tiers"""
    tier: ExtractionTier
    quality_score: float
    cost: float
    time: float
    success: bool
    error: Optional[str] = None
