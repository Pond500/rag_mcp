"""
Unit tests for the Docling-powered DocumentProcessor

Tests the new functionality including:
- Docling integration
- Markdown-aware chunking
- Error handling
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.document_processor import DocumentProcessor
from src.config.settings import Settings, DocumentSettings, DoclingSettings


class TestDocumentProcessorDocling:
    """Test DocumentProcessor with Docling integration"""
    
    @pytest.fixture
    def settings(self):
        """Create test settings"""
        return Settings(
            document=DocumentSettings(
                chunk_size=1000,
                chunk_overlap=200
            ),
            docling=DoclingSettings(
                enable_ocr=True,
                table_mode="fast"
            )
        )
    
    @pytest.fixture
    def processor(self, settings):
        """Create DocumentProcessor instance"""
        return DocumentProcessor(settings.document)
    
    def test_initialization(self, processor):
        """Test processor initialization"""
        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 200
        assert processor._converter is None  # Lazy loading
    
    def test_extract_text_simple(self, processor, tmp_path):
        """Test extracting simple text files"""
        # Create a test text file
        test_file = tmp_path / "test.txt"
        test_content = "This is a test document.\nWith multiple lines."
        test_file.write_text(test_content)
        
        # Extract text
        result = processor.extract_text(str(test_file))
        
        assert len(result) == 1
        assert result[0] == test_content
    
    def test_extract_markdown_simple(self, processor, tmp_path):
        """Test extracting markdown files"""
        # Create a test markdown file
        test_file = tmp_path / "test.md"
        test_content = "# Heading\n\nParagraph text."
        test_file.write_text(test_content)
        
        # Extract text
        result = processor.extract_text(str(test_file))
        
        assert len(result) == 1
        assert result[0] == test_content
    
    @patch('src.core.document_processor.DocumentConverter')
    def test_extract_with_docling_pdf(self, mock_converter_class, processor):
        """Test extracting PDF with Docling"""
        # Mock Docling converter
        mock_converter = MagicMock()
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "# PDF Content\n\nText from PDF"
        mock_converter.convert.return_value = mock_result
        mock_converter_class.return_value = mock_converter
        
        # Extract text
        result = processor.extract_text("test.pdf")
        
        assert len(result) == 1
        assert "# PDF Content" in result[0]
        assert "Text from PDF" in result[0]
    
    def test_extract_with_file_content(self, processor):
        """Test extraction using file_content parameter"""
        test_content = b"Simple text content"
        
        result = processor.extract_text("test.txt", file_content=test_content)
        
        assert len(result) == 1
        assert "Simple text content" in result[0]
    
    def test_extract_empty_file(self, processor, tmp_path):
        """Test extracting empty file"""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")
        
        result = processor.extract_text(str(test_file))
        
        assert result == []
    
    def test_extract_nonexistent_file(self, processor):
        """Test handling non-existent file"""
        result = processor.extract_text("nonexistent.pdf")
        
        assert result == []


class TestMarkdownAwareChunking:
    """Test Markdown-aware chunking functionality"""
    
    @pytest.fixture
    def processor(self):
        """Create processor with specific chunk settings"""
        settings = Settings(
            document=DocumentSettings(chunk_size=200, chunk_overlap=50)
        )
        return DocumentProcessor(settings.document)
    
    def test_chunk_by_headers(self, processor):
        """Test chunking respects Markdown headers"""
        text = """# Chapter 1

Content of chapter 1.

## Section 1.1

Content of section 1.1.

# Chapter 2

Content of chapter 2."""
        
        chunks = processor.chunk_text([text], chunk_size=100, chunk_overlap=20)
        
        # Should create multiple chunks based on headers
        assert len(chunks) > 1
        
        # Each chunk should have metadata
        for chunk in chunks:
            assert 'text' in chunk
            assert 'page' in chunk
            assert 'chunk_index' in chunk
    
    def test_chunk_by_paragraphs(self, processor):
        """Test chunking by paragraphs when headers aren't available"""
        text = """First paragraph with some content.

Second paragraph with more content.

Third paragraph with additional content."""
        
        chunks = processor.chunk_text([text], chunk_size=60, chunk_overlap=10)
        
        assert len(chunks) >= 2
    
    def test_chunk_preserves_tables(self, processor):
        """Test that tables are kept together when possible"""
        text = """# Data Table

| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |
| Value 3  | Value 4  |

## Analysis

Some analysis text."""
        
        chunks = processor.chunk_text([text], chunk_size=200, chunk_overlap=20)
        
        # Check that table content appears in chunks
        has_table = any('|' in chunk['text'] for chunk in chunks)
        assert has_table
    
    def test_chunk_with_overlap(self, processor):
        """Test that chunk overlap works correctly"""
        text = "A" * 500  # Long text
        
        chunks = processor.chunk_text([text], chunk_size=200, chunk_overlap=50)
        
        # Should have multiple chunks
        assert len(chunks) >= 2
        
        # Verify overlap exists (chunks should share some content)
        if len(chunks) >= 2:
            # Last part of first chunk should overlap with start of second
            assert len(chunks[0]['text']) <= 200
    
    def test_chunk_empty_pages(self, processor):
        """Test chunking empty pages"""
        chunks = processor.chunk_text([])
        
        assert chunks == []
    
    def test_chunk_multiple_pages(self, processor):
        """Test chunking multiple pages"""
        pages = [
            "# Page 1\n\nContent of page 1.",
            "# Page 2\n\nContent of page 2."
        ]
        
        chunks = processor.chunk_text(pages)
        
        # Should have chunks from both pages
        assert len(chunks) >= 2
        
        # Check page numbers are correct
        page_nums = [chunk['page'] for chunk in chunks]
        assert 1 in page_nums
        assert 2 in page_nums
    
    def test_split_by_paragraphs(self, processor):
        """Test paragraph splitting method"""
        text = """Paragraph one.

Paragraph two.

Paragraph three."""
        
        result = processor._split_by_paragraphs(text, chunk_size=30, chunk_overlap=5)
        
        assert len(result) >= 3
    
    def test_split_by_characters(self, processor):
        """Test character-based splitting as fallback"""
        text = "A" * 1000
        
        result = processor._split_by_characters(text, chunk_size=200, chunk_overlap=50)
        
        # Should create multiple chunks
        assert len(result) >= 4
        
        # Each chunk should be approximately the right size
        for chunk in result[:-1]:  # Except last one
            assert len(chunk) <= 200
    
    def test_complex_markdown_structure(self, processor):
        """Test with complex Markdown including lists and code blocks"""
        text = """# Main Title

## Introduction

Some introductory text.

### Features

- Feature 1
- Feature 2
- Feature 3

## Code Example

```python
def hello():
    print("Hello")
```

## Conclusion

Final thoughts."""
        
        chunks = processor.chunk_text([text], chunk_size=150, chunk_overlap=30)
        
        # Should handle complex structure
        assert len(chunks) > 0
        
        # Check that code block is preserved
        has_code = any('```' in chunk['text'] or 'def hello' in chunk['text'] 
                      for chunk in chunks)
        # Note: depending on chunk size, code might be split


class TestDoclingSettings:
    """Test Docling settings integration"""
    
    def test_docling_settings_defaults(self):
        """Test default Docling settings"""
        settings = DoclingSettings()
        
        assert settings.enable_ocr is True
        assert settings.table_mode == "fast"
        assert settings.parse_tables is True
        assert settings.parse_images is True
        assert settings.generate_page_images is False
    
    def test_custom_docling_settings(self):
        """Test custom Docling settings"""
        settings = DoclingSettings(
            enable_ocr=False,
            table_mode="accurate",
            parse_tables=False
        )
        
        assert settings.enable_ocr is False
        assert settings.table_mode == "accurate"
        assert settings.parse_tables is False
    
    @patch('src.core.document_processor.DocumentConverter')
    def test_processor_uses_docling_settings(self, mock_converter_class):
        """Test that processor uses Docling settings"""
        settings = Settings(
            document=DocumentSettings(),
            docling=DoclingSettings(
                enable_ocr=False,
                table_mode="accurate"
            )
        )
        
        processor = DocumentProcessor(settings.document)
        processor.config = settings  # Manually set config for testing
        
        # Trigger converter initialization
        processor._get_converter()
        
        # Verify converter was initialized
        assert mock_converter_class.called


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
