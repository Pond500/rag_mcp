"""
Example: Using the upgraded DocumentProcessor with Docling

This example demonstrates how to use the new Docling-powered document processor.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.document_processor import DocumentProcessor
from src.config.settings import get_settings, Settings, DoclingSettings


def example_basic_usage():
    """Basic usage example"""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Get default settings
    settings = get_settings()
    processor = DocumentProcessor(settings.document)
    
    # Extract text from a PDF (example)
    # pages = processor.extract_text("sample.pdf")
    # print(f"Extracted {len(pages)} pages")
    # print(f"First 500 chars:\n{pages[0][:500]}")
    
    # Chunk the text
    # chunks = processor.chunk_text(pages)
    # print(f"\nCreated {len(chunks)} chunks")
    # print(f"First chunk:\n{chunks[0]['text'][:300]}")


def example_custom_settings():
    """Example with custom Docling settings"""
    print("\n" + "=" * 60)
    print("Example 2: Custom Docling Settings")
    print("=" * 60)
    
    # Create custom settings
    settings = Settings(
        docling=DoclingSettings(
            enable_ocr=True,
            table_mode="accurate",  # Use accurate mode for better table extraction
            parse_tables=True,
            parse_images=True
        )
    )
    
    processor = DocumentProcessor(settings.document)
    print("Processor initialized with custom settings:")
    print(f"  - OCR: {settings.docling.enable_ocr}")
    print(f"  - Table Mode: {settings.docling.table_mode}")
    print(f"  - Parse Tables: {settings.docling.parse_tables}")


def example_with_file_content():
    """Example using file content instead of file path"""
    print("\n" + "=" * 60)
    print("Example 3: Processing from BytesIO")
    print("=" * 60)
    
    settings = get_settings()
    processor = DocumentProcessor(settings.document)
    
    # Read file into memory
    # with open("sample.pdf", "rb") as f:
    #     file_content = f.read()
    
    # Process from bytes
    # pages = processor.extract_text(
    #     file_path="sample.pdf",  # Used for format detection
    #     file_content=file_content
    # )
    # print(f"Processed document from memory: {len(pages)} pages")


def example_custom_chunking():
    """Example with custom chunk settings"""
    print("\n" + "=" * 60)
    print("Example 4: Custom Chunking")
    print("=" * 60)
    
    settings = get_settings()
    processor = DocumentProcessor(settings.document)
    
    # Simulate extracted text (Markdown format)
    sample_text = """# Introduction

This is a sample document with markdown formatting.

## Section 1: Overview

Here is some text in section 1.

### Subsection 1.1

More detailed information here.

## Section 2: Data

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |

## Conclusion

Final thoughts and summary.
"""
    
    # Chunk with custom settings
    chunks = processor.chunk_text(
        pages=[sample_text],
        chunk_size=200,  # Smaller chunks
        chunk_overlap=50  # Larger overlap
    )
    
    print(f"Created {len(chunks)} chunks with custom settings")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n--- Chunk {i} ---")
        print(chunk['text'][:150] + "..." if len(chunk['text']) > 150 else chunk['text'])


def example_markdown_aware_chunking():
    """Example showing Markdown-aware chunking"""
    print("\n" + "=" * 60)
    print("Example 5: Markdown-Aware Chunking")
    print("=" * 60)
    
    settings = get_settings()
    processor = DocumentProcessor(settings.document)
    
    # Document with clear structure
    structured_text = """# Chapter 1: Getting Started

This is the introduction to the chapter. It explains the basics.

## Installation

To install the software, follow these steps:

1. Download the installer
2. Run the installer
3. Follow the on-screen instructions

## Configuration

After installation, you need to configure the application:

- Set your username
- Choose your preferences
- Configure your workspace

# Chapter 2: Advanced Topics

This chapter covers advanced features.

## Performance Optimization

Here are some tips for better performance:

### Memory Management

Proper memory management is crucial for performance.

### Caching Strategies

Implement caching to speed up your application.
"""
    
    chunks = processor.chunk_text([structured_text], chunk_size=400, chunk_overlap=50)
    
    print(f"Created {len(chunks)} chunks (respecting Markdown structure)")
    print("\nChunks preserve semantic boundaries:")
    for i, chunk in enumerate(chunks, 1):
        # Show first line of each chunk to see structure
        first_line = chunk['text'].split('\n')[0]
        print(f"  Chunk {i}: {first_line}")


def example_error_handling():
    """Example showing error handling"""
    print("\n" + "=" * 60)
    print("Example 6: Error Handling")
    print("=" * 60)
    
    settings = get_settings()
    processor = DocumentProcessor(settings.document)
    
    # Try to process non-existent file
    result = processor.extract_text("nonexistent.pdf")
    if not result:
        print("✓ Gracefully handled missing file")
    
    # Try to chunk empty pages
    chunks = processor.chunk_text([])
    print(f"✓ Handled empty input: {len(chunks)} chunks")


if __name__ == "__main__":
    print("\n🚀 Docling Document Processor Examples\n")
    
    example_basic_usage()
    example_custom_settings()
    example_with_file_content()
    example_custom_chunking()
    example_markdown_aware_chunking()
    example_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)
    print("\nNote: Some examples are commented out because they require actual files.")
    print("Uncomment and provide real files to see full functionality.\n")
