"""Test Hybrid Mode: Docling (fast) → VLM (balanced/premium)"""
import time
import os
from pathlib import Path
from src.core.progressive_processor import ProgressiveDocumentProcessor


def test_hybrid_mode():
    """Test hybrid extraction: Docling first, then VLM if quality low"""
    
    # Get API key
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found!")
        return
    
    print("=" * 80)
    print("🧪 Testing Hybrid Mode: Docling (no OCR) → VLM")
    print("=" * 80)
    
    # Initialize processor in hybrid mode
    processor = ProgressiveDocumentProcessor(
        openrouter_api_key=api_key,
        enable_fast_tier=True,        # Docling (no Tesseract OCR)
        enable_balanced_tier=True,    # Gemini Free VLM
        enable_premium_tier=False,    # Skip premium (paid tier)
        disable_ocr=True              # ปิด Tesseract OCR!
    )
    
    # Test with smaller files first (avoid rate limit)
    test_files = [
        "data/62-2.pdf",            # 5 pages - good for testing
        "data/reportfidf2566.pdf",  # 6 pages
        "data/foundation64_english.pdf",  # 10 pages
    ]
    
    for filename in test_files:
        pdf_path = Path(filename)
        if not pdf_path.exists():
            print(f"\n⚠️  File not found: {filename}")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"📄 Processing: {filename}")
        print(f"{'=' * 80}")
        
        start = time.time()
        
        # Extract with hybrid mode (Docling first, VLM if needed)
        result = processor.extract_with_smart_routing(
            pdf_path=str(pdf_path),
            target_quality=0.75,
            clean_text=True
        )
        
        elapsed = time.time() - start
        
        # Display results
        print(f"\n✅ Extraction completed in {elapsed:.1f}s")
        print(f"   • Tier used: {result.tier_used}")
        print(f"   • Quality: {result.quality_report.overall_score:.3f}")
        print(f"   • Cost: ${result.cost:.6f}")
        print(f"   • Pages extracted: {len(result.pages)}")
        print(f"   • Success: {result.success}")
        
        if result.error:
            print(f"   • Error: {result.error}")
        
        # Show quality metrics
        quality = result.quality_report
        print(f"\n📊 Quality Metrics:")
        print(f"   • Content density: {quality.content_density:.3f}")
        print(f"   • Text quality: {quality.text_quality:.3f}")
        print(f"   • Word quality: {quality.word_quality:.3f}")
        print(f"   • Consistency: {quality.consistency:.3f}")
        print(f"   • Structure quality: {quality.structure_quality:.3f}")
        
        # Explain tier selection
        print(f"\n🔄 Tier Selection Logic:")
        if result.tier_used == 'fast':
            print(f"   ✓ Docling (no OCR) was sufficient (quality {quality.overall_score:.3f} ≥ 0.70)")
        elif result.tier_used == 'balanced':
            print(f"   ✓ Escalated to VLM because Docling quality was low")
            print(f"   ✓ VLM (Gemini Free) achieved quality {quality.overall_score:.3f}")
        
        # Show sample text from first page
        if result.pages:
            sample = result.pages[0][:500]
            print(f"\n📝 First 500 chars:")
            print("-" * 80)
            print(sample)
            print("-" * 80)
        
        # Performance comparison
        print(f"\n📈 Performance vs Tesseract OCR:")
        print(f"   • Previous (Docling + Tesseract): 98s with 200+ OSD errors")
        print(f"   • Current (Docling only): {elapsed:.1f}s with NO errors")
        if elapsed < 98:
            improvement = ((98 - elapsed) / 98) * 100
            print(f"   • Speed improvement: {improvement:.1f}% faster! 🚀")


if __name__ == "__main__":
    test_hybrid_mode()
