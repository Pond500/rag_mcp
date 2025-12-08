"""Document Processor

Extracts text from various file formats (PDF, DOCX, TXT) and chunks them using Docling.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import re
from io import BytesIO

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process documents: extract text and chunk using Docling
    
    Usage:
        processor = DocumentProcessor(config)
        pages = processor.extract_text(file_path="doc.pdf")
        chunks = processor.chunk_text(pages, chunk_size=1000, overlap=200)
    """
    
    def __init__(self, config=None):
        self.config = config
        self.chunk_size = getattr(config, "chunk_size", 1000) if config else 1000
        self.chunk_overlap = getattr(config, "chunk_overlap", 200) if config else 200
        
        # Initialize Docling converter with lazy loading
        self._converter = None
        self._docling_config = None
    
    def _get_converter(self):
        """Lazy initialization of Docling converter"""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                
                # Get Docling settings from config
                enable_ocr = True
                table_mode = "fast"
                
                if self.config and hasattr(self.config, 'docling'):
                    enable_ocr = getattr(self.config.docling, 'enable_ocr', True)
                    table_mode = getattr(self.config.docling, 'table_mode', 'fast')
                
                # Initialize converter with configuration
                self._converter = DocumentConverter()
                logger.info("Initialized Docling converter (OCR=%s, table_mode=%s)", enable_ocr, table_mode)
                
            except ImportError as e:
                logger.error("Docling not installed: %s", e)
                raise ImportError("Please install docling: pip install docling>=2.0.0")
        
        return self._converter
    
    def extract_text(self, file_path: str, file_content: Optional[bytes] = None) -> List[str]:
        """Extract text from file using Docling (supports PDF, DOCX, TXT, etc.)
        
        Docling converts documents to high-quality Markdown format, preserving:
        - Tables (with proper structure)
        - Headers and formatting
        - Lists and layout
        
        Args:
            file_path: Path to file (used for extension detection)
            file_content: Optional raw bytes (if provided, will use instead of reading file)
            
        Returns:
            List with single Markdown string (Docling returns unified document)
        """
        ext = Path(file_path).suffix.lower()
        
        try:
            # Handle plain text files directly (no need for Docling)
            if ext in [".txt", ".md"]:
                return self._extract_text_simple(file_path, file_content)
            
            # Use Docling for structured documents (PDF, DOCX, etc.)
            return self._extract_with_docling(file_path, file_content)
            
        except Exception as e:
            logger.error("Failed to extract text from %s: %s", file_path, e)
            return []
    
    def _extract_with_docling(self, file_path: str, file_content: Optional[bytes]) -> List[str]:
        """Extract text using Docling DocumentConverter
        
        Args:
            file_path: Path to document
            file_content: Optional file bytes
            
        Returns:
            List containing single Markdown string
        """
        try:
            converter = self._get_converter()
            
            # Docling requires either file path or BytesIO stream
            if file_content:
                # Create a temporary BytesIO object with proper name
                stream = BytesIO(file_content)
                stream.name = Path(file_path).name  # Docling uses this for format detection
                result = converter.convert(stream)
            else:
                result = converter.convert(file_path)
            
            # Export to Markdown format
            markdown_text = result.document.export_to_markdown()
            
            if not markdown_text.strip():
                logger.warning("Docling returned empty content for %s", file_path)
                return []
            
            logger.info("Extracted document as Markdown (%d chars) from %s", 
                       len(markdown_text), Path(file_path).name)
            
            # Return as single-item list for consistency
            return [markdown_text]
            
        except Exception as e:
            logger.error("Docling extraction failed for %s: %s", file_path, e)
            return []
    
    def _extract_text_simple(self, file_path: str, file_content: Optional[bytes]) -> List[str]:
        """Extract text from plain text files (TXT/MD)
        
        Args:
            file_path: Path to text file
            file_content: Optional file bytes
            
        Returns:
            List containing single text string
        """
        try:
            if file_content:
                text = file_content.decode('utf-8', errors='ignore')
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            return [text] if text.strip() else []
            
        except Exception as e:
            logger.error("Text extraction failed: %s", e)
            return []
    
    def chunk_text(
        self,
        pages: List[str],
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Chunk text with Markdown-aware splitting
        
        This method attempts to respect Markdown structure (headers, paragraphs, lists)
        when chunking to maintain semantic coherence.
        
        Args:
            pages: List of page texts (usually single Markdown document from Docling)
            chunk_size: Characters per chunk (uses config default if None)
            chunk_overlap: Overlap between chunks (uses config default if None)
            
        Returns:
            List of chunks with metadata: [{"text": "...", "page": 1, "chunk_index": 0}, ...]
        """
        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap
        
        chunks = []
        chunk_index = 0
        
        for page_num, page_text in enumerate(pages, start=1):
            # Try Markdown-aware chunking first
            page_chunks = self._chunk_markdown_text(page_text, chunk_size, chunk_overlap)
            
            # Add metadata to each chunk
            for chunk_text in page_chunks:
                if chunk_text.strip():
                    chunks.append({
                        "text": chunk_text,
                        "page": page_num,
                        "chunk_index": chunk_index,
                    })
                    chunk_index += 1
        
        logger.info("Created %d chunks from %d pages", len(chunks), len(pages))
        return chunks
    
    def _chunk_markdown_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text intelligently, respecting Markdown structure
        
        Strategy:
        1. Split by Markdown headers (##, ###, etc.)
        2. If sections are too large, split by paragraphs
        3. If still too large, fall back to character-based splitting
        
        Args:
            text: Markdown text to split
            chunk_size: Target size for chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # First, try to split by headers
        header_pattern = r'^(#{1,6}\s+.+)$'
        sections = re.split(f'({header_pattern})', text, flags=re.MULTILINE)
        
        chunks = []
        current_chunk = ""
        current_header = ""
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            # Check if this is a header
            if re.match(header_pattern, section):
                current_header = section
                continue
            
            # Try to add section to current chunk
            potential_chunk = current_chunk + current_header + "\n\n" + section if current_chunk else current_header + "\n\n" + section if current_header else section
            
            if len(potential_chunk) <= chunk_size:
                current_chunk = potential_chunk
                current_header = ""  # Reset header after use
            else:
                # Current chunk is complete, save it
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Check if section itself is too large
                if len(section) > chunk_size:
                    # Split by paragraphs
                    para_chunks = self._split_by_paragraphs(
                        current_header + "\n\n" + section if current_header else section,
                        chunk_size,
                        chunk_overlap
                    )
                    chunks.extend(para_chunks)
                    current_chunk = ""
                    current_header = ""
                else:
                    current_chunk = (current_header + "\n\n" + section if current_header else section).strip()
                    current_header = ""
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If no chunks were created (no headers found), fall back to paragraph splitting
        if not chunks:
            chunks = self._split_by_paragraphs(text, chunk_size, chunk_overlap)
        
        return chunks
    
    def _split_by_paragraphs(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text by paragraphs, respecting chunk size
        
        Args:
            text: Text to split
            chunk_size: Target chunk size
            chunk_overlap: Overlap size
            
        Returns:
            List of chunks
        """
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Try to add paragraph to current chunk
            potential_chunk = current_chunk + "\n\n" + para if current_chunk else para
            
            if len(potential_chunk) <= chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If paragraph is too large, split by characters
                if len(para) > chunk_size:
                    char_chunks = self._split_by_characters(para, chunk_size, chunk_overlap)
                    chunks.extend(char_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _split_by_characters(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Fall back to character-based splitting with overlap
        
        Args:
            text: Text to split
            chunk_size: Chunk size
            chunk_overlap: Overlap size
            
        Returns:
            List of chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk)
            
            start += chunk_size - chunk_overlap
            
            if end >= len(text):
                break
        
        return chunks
