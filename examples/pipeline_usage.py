"""Example: Using Auto-Quality Processor in Pipeline

This example shows how to use AutoQualityProcessor for batch processing
before indexing documents into a RAG system.

Perfect for:
- Document ingestion pipelines
- Pre-processing before vector indexing
- Batch document conversion
- Quality-critical applications
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.auto_quality_processor import AutoQualityProcessor, AutoQualityConfig
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_single_document():
    """Example: Process single document"""
    print("\n" + "="*80)
    print("Example 1: Single Document Processing")
    print("="*80)
    
    # Configuration
    config = AutoQualityConfig(
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        target_quality=0.85,  # Aim for excellent quality
        min_acceptable_quality=0.70,  # Accept if above this
        enable_visual_precheck=True,
        max_retries=3
    )
    
    # Create processor
    processor = AutoQualityProcessor(config)
    
    # Process document
    result = processor.process("test_document.pdf")
    
    # Check result
    if result.success:
        print(f"\n✅ Success!")
        print(f"   Quality Score: {result.quality_score:.3f}")
        print(f"   Tier Used: {result.tier_used}")
        print(f"   Pages Extracted: {len(result.pages)}")
        print(f"   Cost: ${result.cost:.4f}")
        print(f"   Processing Time: {result.processing_time:.1f}s")
        
        # Access extracted text
        for i, page in enumerate(result.pages, 1):
            print(f"\n   Page {i} preview: {page[:100]}...")
    else:
        print(f"\n❌ Failed: {result.error}")


def process_batch_pipeline():
    """Example: Batch processing pipeline"""
    print("\n" + "="*80)
    print("Example 2: Batch Processing Pipeline")
    print("="*80)
    
    # Configuration
    config = AutoQualityConfig(
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        target_quality=0.85,
        enable_visual_precheck=True,
        cost_tracking=True
    )
    
    # Create processor
    processor = AutoQualityProcessor(config)
    
    # List of documents to process
    documents = [
        "document1.pdf",
        "document2.pdf",
        "document3.pdf"
    ]
    
    # Process batch
    results = processor.process_batch(documents, show_progress=True)
    
    # Analyze results
    print("\n" + "-"*80)
    print("Batch Results:")
    print("-"*80)
    
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        avg_quality = sum(r.quality_score for r in successful) / len(successful)
        total_cost = sum(r.cost for r in results)
        total_pages = sum(len(r.pages) for r in successful)
        
        print(f"\n📊 Statistics:")
        print(f"   Average Quality: {avg_quality:.3f}")
        print(f"   Total Pages: {total_pages}")
        print(f"   Total Cost: ${total_cost:.4f}")
        print(f"   Cost per Page: ${total_cost/total_pages:.6f}")
        
        # Tier distribution
        tier_counts = {}
        for r in successful:
            tier_counts[r.tier_used] = tier_counts.get(r.tier_used, 0) + 1
        
        print(f"\n🎯 Tier Distribution:")
        for tier, count in sorted(tier_counts.items()):
            print(f"   {tier}: {count} documents")
    
    # Return for pipeline use
    return successful


def rag_pipeline_integration():
    """Example: Integration with RAG pipeline"""
    print("\n" + "="*80)
    print("Example 3: RAG Pipeline Integration")
    print("="*80)
    
    # Step 1: Configure processor
    config = AutoQualityConfig(
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        target_quality=0.85,
        enable_visual_precheck=True
    )
    
    processor = AutoQualityProcessor(config)
    
    # Step 2: Process documents
    print("\n📄 Step 1: Extracting text from documents...")
    documents = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    results = processor.process_batch(documents, show_progress=True)
    
    # Step 3: Filter successful results
    print("\n✅ Step 2: Filtering successful extractions...")
    successful_docs = [r for r in results if r.success]
    print(f"   {len(successful_docs)}/{len(results)} documents ready for indexing")
    
    # Step 4: Prepare for indexing
    print("\n🔍 Step 3: Preparing for vector indexing...")
    chunks = []
    for result in successful_docs:
        # Combine pages
        full_text = "\n\n".join(result.pages)
        
        # Create metadata
        metadata = {
            'source': result.file_path,
            'quality_score': result.quality_score,
            'extraction_tier': result.tier_used,
            'page_count': len(result.pages),
            'extraction_cost': result.cost
        }
        
        chunks.append({
            'text': full_text,
            'metadata': metadata
        })
    
    print(f"   Prepared {len(chunks)} documents for indexing")
    
    # Step 5: (Simulated) Index to vector store
    print("\n💾 Step 4: Indexing to vector store...")
    print("   [This is where you'd call your RAG indexing code]")
    print("   Example:")
    print("   ```python")
    print("   from your_rag_system import VectorStore")
    print("   ")
    print("   vector_store = VectorStore()")
    print("   for chunk in chunks:")
    print("       vector_store.add_document(")
    print("           text=chunk['text'],")
    print("           metadata=chunk['metadata']")
    print("       )")
    print("   ```")
    
    # Step 6: Get statistics
    print("\n📊 Step 5: Processing Statistics...")
    stats = processor.get_statistics()
    print(f"   Total Documents: {stats['total_documents']}")
    print(f"   Total Pages: {stats['total_pages']}")
    print(f"   Total Cost: ${stats['total_cost']:.4f}")
    print(f"   Avg Cost/Doc: ${stats['average_cost_per_doc']:.4f}")
    
    return chunks


def simple_api_usage():
    """Example: Simple API usage"""
    print("\n" + "="*80)
    print("Example 4: Simple API Usage")
    print("="*80)
    
    from src.core.auto_quality_processor import process_document_auto
    
    # One-liner processing
    result = process_document_auto(
        file_path="document.pdf",
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        target_quality=0.85
    )
    
    if result.success:
        print(f"\n✅ Document processed successfully!")
        print(f"   Quality: {result.quality_score:.3f}")
        print(f"   Pages: {len(result.pages)}")
        print(f"   Tier: {result.tier_used}")
        print(f"   Cost: ${result.cost:.4f}")
    else:
        print(f"\n❌ Processing failed: {result.error}")


if __name__ == "__main__":
    # Check API key
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ Error: GEMINI_API_KEY not set")
        print("Please set it in .env file or environment variable")
        sys.exit(1)
    
    print("\n🚀 Auto-Quality Processor Examples")
    print("="*80)
    
    # Run examples
    try:
        # Example 1: Single document
        # process_single_document()
        
        # Example 2: Batch processing
        # process_batch_pipeline()
        
        # Example 3: RAG pipeline integration
        rag_pipeline_integration()
        
        # Example 4: Simple API
        # simple_api_usage()
        
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        sys.exit(1)
    
    print("\n" + "="*80)
    print("✅ Examples completed!")
    print("="*80)
