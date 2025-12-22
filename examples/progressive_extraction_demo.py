"""
Progressive Document Extraction - Usage Examples

This script demonstrates how to use the progressive extraction system:
1. Basic usage with automatic fallback
2. Force VLM extraction
3. Quality assessment and reporting
4. Integration with existing RAG pipeline
"""
import logging
from pathlib import Path
from types import SimpleNamespace

from src.core.progressive_processor import ProgressiveDocumentProcessor
from src.core.quality_checker import UnsupervisedQualityChecker
from src.utils.document_validator import DocumentValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_1_basic_usage():
    """Example 1: Basic progressive extraction"""
    print("\n" + "="*80)
    print("📝 Example 1: Basic Progressive Extraction")
    print("="*80)
    
    # Configure
    config = SimpleNamespace()
    config.level1_threshold = 0.85
    config.level2_threshold = 0.70
    config.gemini_api_key = "AIzaSyCSnvUZwRF5PgZtU7GAO9fL_5PVeqR3XN4"
    config.gemini_model = "gemini-2.0-flash-exp"
    config.image_dpi = 300
    
    # Initialize processor
    processor = ProgressiveDocumentProcessor(config)
    
    # Extract text
    file_path = "test_document.pdf"  # Replace with actual file
    
    try:
        pages, method, report = processor.extract_text(file_path)
        
        print(f"\n✅ Extraction Complete!")
        print(f"   Method: {method}")
        print(f"   Pages: {len(pages)}")
        print(f"   Quality: {report.overall_score:.3f}")
        print(f"   Recommendation: {report.get_recommendation()}")
        
        # Show dimension scores
        print(f"\n📊 Quality Dimensions:")
        for name, dim in report.dimensions.items():
            print(f"   {name:20s}: {dim.score:.3f} (weight: {dim.weight:.0%})")
        
        # Show issues
        if report.issues:
            print(f"\n⚠️  Issues ({len(report.issues)}):")
            for severity, message in report.issues[:5]:
                print(f"   [{severity}] {message}")
        
    except FileNotFoundError:
        print(f"⚠️  File not found: {file_path}")
        print("   Replace with actual file path to test")


def example_2_force_vlm():
    """Example 2: Force VLM extraction (skip Level 1)"""
    print("\n" + "="*80)
    print("🤖 Example 2: Force VLM Extraction")
    print("="*80)
    
    config = SimpleNamespace()
    config.gemini_api_key = "AIzaSyCSnvUZwRF5PgZtU7GAO9fL_5PVeqR3XN4"
    config.gemini_model = "gemini-2.0-flash-exp"
    config.image_dpi = 300
    
    processor = ProgressiveDocumentProcessor(config)
    
    file_path = "scanned_document.pdf"
    
    try:
        # Force VLM extraction (useful for scanned docs)
        pages, method, report = processor.extract_text(
            file_path, 
            force_vlm=True
        )
        
        print(f"✅ VLM Extraction: {len(pages)} pages")
        print(f"   Quality: {report.overall_score:.3f}")
        
    except FileNotFoundError:
        print(f"⚠️  File not found: {file_path}")


def example_3_quality_only():
    """Example 3: Quality assessment only (no extraction)"""
    print("\n" + "="*80)
    print("🔍 Example 3: Quality Assessment Only")
    print("="*80)
    
    # Simulate extracted pages
    pages = [
        "# Page 1\n\nThis is sample content with proper structure.",
        "# Page 2\n\nMore content here with good formatting.",
        "# Page 3\n\nFinal page with tables:\n\n| Col1 | Col2 |\n|------|------|\n| A | B |"
    ]
    
    checker = UnsupervisedQualityChecker()
    report = checker.check_quality(pages)
    
    print(f"\n📊 Quality Assessment:")
    print(f"   Overall Score: {report.overall_score:.3f}")
    print(f"   Recommendation: {report.get_recommendation()}")
    
    print(f"\n📈 Dimension Breakdown:")
    for name, dim in report.dimensions.items():
        print(f"   {name:20s}: {dim.score:.3f}")
        if dim.issues:
            for issue in dim.issues:
                print(f"      ⚠️  {issue}")


def example_4_validator_integration():
    """Example 4: Integration with existing DocumentValidator"""
    print("\n" + "="*80)
    print("📋 Example 4: DocumentValidator Integration")
    print("="*80)
    
    # Simulate extraction
    pages = [
        "# Document Title\n\nSome content here.",
        "## Section 1\n\nMore detailed content.",
    ]
    
    # Use DocumentValidator with new UnsupervisedQualityChecker
    validator = DocumentValidator()
    
    validation_report = validator.validate(
        file_path="sample.pdf",
        extracted_pages=pages,
        processing_time=1.5,
        use_unsupervised_checker=True  # Use new checker
    )
    
    print(f"\n📄 Validation Report:")
    print(f"   Quality Score: {validation_report.quality_score:.3f}")
    print(f"   Recommendation: {validation_report.recommendation}")
    print(f"   Total Chars: {validation_report.total_chars:,}")
    
    # Check UQC dimensions if available
    if 'uqc_dimensions' in validation_report.statistics:
        print(f"\n🔍 UQC Dimensions:")
        for name, data in validation_report.statistics['uqc_dimensions'].items():
            print(f"   {name:20s}: {data['score']:.3f}")


def example_5_rag_pipeline():
    """Example 5: Integration with RAG pipeline"""
    print("\n" + "="*80)
    print("🔗 Example 5: RAG Pipeline Integration")
    print("="*80)
    
    # Configure
    config = SimpleNamespace()
    config.level1_threshold = 0.85
    config.level2_threshold = 0.70
    config.gemini_api_key = "AIzaSyCSnvUZwRF5PgZtU7GAO9fL_5PVeqR3XN4"
    config.chunk_size = 1000
    config.chunk_overlap = 200
    
    processor = ProgressiveDocumentProcessor(config)
    
    file_path = "knowledge_base.pdf"
    
    try:
        # Extract with progressive fallback
        pages, method, quality_report = processor.extract_text(file_path)
        
        # Only proceed if quality is acceptable
        if quality_report.overall_score < 0.50:
            print(f"❌ Extraction quality too low: {quality_report.overall_score:.3f}")
            print(f"   Skipping document for RAG indexing")
            return
        
        # Chunk for RAG
        chunks = processor.chunk_text(pages)
        
        print(f"\n✅ Ready for RAG:")
        print(f"   Extraction method: {method}")
        print(f"   Quality: {quality_report.overall_score:.3f}")
        print(f"   Pages: {len(pages)}")
        print(f"   Chunks: {len(chunks)}")
        print(f"   Avg chunk size: {sum(len(c['text']) for c in chunks) / len(chunks):.0f} chars")
        
        # Here you would index chunks into vector store
        # vector_store.add_documents(chunks)
        
    except FileNotFoundError:
        print(f"⚠️  File not found: {file_path}")


def example_6_batch_processing():
    """Example 6: Batch processing with quality tracking"""
    print("\n" + "="*80)
    print("📦 Example 6: Batch Processing")
    print("="*80)
    
    config = SimpleNamespace()
    config.level1_threshold = 0.85
    config.level2_threshold = 0.70
    config.gemini_api_key = "AIzaSyCSnvUZwRF5PgZtU7GAO9fL_5PVeqR3XN4"
    
    processor = ProgressiveDocumentProcessor(config)
    
    # Simulated file list
    files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    
    results = {
        'level1_passed': 0,
        'level2_passed': 0,
        'failed': 0,
        'total_pages': 0
    }
    
    for file_path in files:
        try:
            print(f"\n🔄 Processing: {file_path}")
            pages, method, report = processor.extract_text(file_path)
            
            results['total_pages'] += len(pages)
            
            if method == "BASIC":
                results['level1_passed'] += 1
            elif method == "VLM":
                results['level2_passed'] += 1
            else:
                results['failed'] += 1
            
            print(f"   ✅ {method}: {len(pages)} pages, quality={report.overall_score:.3f}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results['failed'] += 1
    
    print(f"\n📊 Batch Results:")
    print(f"   Level 1 passed: {results['level1_passed']}")
    print(f"   Level 2 needed: {results['level2_passed']}")
    print(f"   Failed: {results['failed']}")
    print(f"   Total pages: {results['total_pages']}")


if __name__ == "__main__":
    print("\n🚀 Progressive Document Extraction - Examples\n")
    
    # Run examples
    # example_1_basic_usage()
    # example_2_force_vlm()
    example_3_quality_only()
    example_4_validator_integration()
    # example_5_rag_pipeline()
    # example_6_batch_processing()
    
    print("\n✅ Examples complete!")
    print("\n💡 Tips:")
    print("   - Use Level 1 for most documents (fast, good quality)")
    print("   - Use Level 2 (VLM) for scanned/complex documents")
    print("   - Set thresholds based on your quality requirements")
    print("   - Monitor extraction methods to optimize costs")
