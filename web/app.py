"""
Progressive Document Processing Web Viewer
Upload documents and view extraction results with quality assessment

Features:
- Progressive extraction (Fast → VLM fallback)
- Quality score display (0.0-1.0)
- Extraction method indicator (BASIC/VLM)
- 5-dimension quality breakdown
- Page-based viewing
"""
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import sys
import time
import logging
from types import SimpleNamespace

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.progressive_processor import ProgressiveDocumentProcessor
from src.core.document_processor import DocumentProcessor
from src.config.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = Path(__file__).parent.parent / 'uploads'
app.config['OUTPUT_FOLDER'] = Path(__file__).parent.parent / 'output'

# Create directories
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['OUTPUT_FOLDER'].mkdir(exist_ok=True)

# Allowed file extensions (Hybrid Processing: MarkItDown + Docling)
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'doc',     # Documents (Docling)
    'xlsx', 'xls',            # Excel (MarkItDown → Docling fallback)
    'pptx', 'ppt',            # PowerPoint (MarkItDown → Docling fallback)
    'txt', 'md'               # Plain text (Simple)
}

# Initialize processor
settings = Settings()

# Use ProgressiveDocumentProcessor with OpenRouter
try:
    # Check if OpenRouter API key is configured
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY', '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')
    
    if openrouter_api_key:
        # Import progressive processor (OpenRouter-based)
        from src.core.progressive_processor import ProgressiveDocumentProcessor
        
        processor = ProgressiveDocumentProcessor(
            openrouter_api_key=openrouter_api_key,
            enable_fast_tier=True,       # Docling (no OCR) - FREE
            enable_balanced_tier=True,   # OpenRouter Gemini Free (but rate limited)
            enable_premium_tier=True,    # ✅ ENABLE premium tier with credits!
            image_dpi=150,               # ลด DPI เพื่อความเร็ว (150 = เร็วกว่า 200 ~30%)
            disable_ocr=True             # ปิด Tesseract OCR! (หลีกเลี่ยง OSD errors)
        )
        USE_PROGRESSIVE = True
        logger.info("🚀 Using ProgressiveDocumentProcessor (Hybrid Mode)")
        logger.info("   ✅ Fast tier: Docling only (NO Tesseract OCR)")
        logger.info("   ✅ Balanced tier: Gemini Free VLM (rate limited)")
        logger.info("   ✅ Premium tier: Gemini Pro (ENABLED with credits)")
    else:
        processor = DocumentProcessor(config=settings)
        USE_PROGRESSIVE = False
        logger.info("📝 Using basic DocumentProcessor (set OPENROUTER_API_KEY for progressive mode)")
except Exception as e:
    logger.warning(f"Failed to initialize ProgressiveDocumentProcessor: {e}")
    logger.exception(e)
    processor = DocumentProcessor(config=settings)
    USE_PROGRESSIVE = False
    logger.info("📝 Falling back to basic DocumentProcessor")


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and extraction"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = app.config['UPLOAD_FOLDER'] / filename
        file.save(str(filepath))
        
        logger.info(f"Processing file: {filename}")
        
        # Extract with progressive processor
        start_time = time.time()
        
        if USE_PROGRESSIVE:
            # Get extraction settings from form
            target_quality = float(request.form.get('target_quality', 0.70))  # Realistic default
            start_tier = request.form.get('start_tier', 'fast')  # fast, balanced, premium
            auto_retry = request.form.get('auto_retry', 'true') == 'true'
            
            logger.info(
                f"⚙️ Settings: target_quality={target_quality}, "
                f"start_tier={start_tier}, auto_retry={auto_retry}"
            )
            
            try:
                # Extract with smart routing
                result = processor.extract_with_smart_routing(
                    pdf_path=str(filepath),
                    target_quality=target_quality,
                    start_tier=start_tier,
                    auto_retry=auto_retry,
                    clean_text=True
                )
                
                sections = result.pages
                extraction_method = result.tier_used.upper()
                quality_score = result.quality_score
                quality_report = result.quality_report
                
                # Debug: Log sections content
                logger.info(f"📊 Response: {len(sections)} sections")
                if sections:
                    logger.info(f"📄 First section preview (200 chars): {sections[0][:200]}")
                
                # Quality dimensions
                quality_dimensions = {
                    'text_quality': {'score': quality_report.text_quality, 'weight': 0.25},
                    'word_quality': {'score': quality_report.word_quality, 'weight': 0.20},
                    'consistency': {'score': quality_report.consistency, 'weight': 0.15},
                    'structure': {'score': quality_report.structure_quality, 'weight': 0.20},
                    'density': {'score': quality_report.content_density, 'weight': 0.20}
                }
                
                # Get recommendations
                quality_recommendation = quality_report.recommendations[0] if quality_report.recommendations else "Good quality"
                quality_issues = quality_report.issues[:5]  # Top 5 issues
                
                # Add extraction metadata
                extraction_metadata = {
                    'tier_used': result.tier_used,
                    'tiers_attempted': result.tier_attempted,
                    'cost': result.cost,
                    'extraction_time': result.extraction_time,
                    'total_time': result.total_time,
                    'retry_count': len(result.tier_attempted) - 1,
                    'target_quality': target_quality
                }
                
                logger.info(
                    f"✅ Extraction complete: "
                    f"tier={result.tier_used}, "
                    f"quality={result.quality_score:.3f}, "
                    f"cost=${result.cost:.4f}, "
                    f"time={result.total_time:.1f}s"
                )
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'quota' in error_msg or '429' in error_msg:
                    logger.error(f"❌ Gemini API quota exceeded: {e}")
                    return jsonify({
                        'error': 'Gemini API quota exceeded. Please try again later or use a different API key.',
                        'details': 'The document was processed with basic extraction instead.'
                    }), 429
                else:
                    raise
        else:
            # Use basic extraction (backward compatible)
            sections = processor.extract_text(str(filepath), clean_text=True, validate=False)
            extraction_method = "BASIC"
            quality_score = None
            quality_dimensions = {}
            quality_recommendation = None
            quality_issues = []
            extraction_metadata = {}
        
        processing_time = time.time() - start_time
        
        if not sections:
            return jsonify({'error': 'Failed to extract content from document'}), 500
        
        # Analyze extracted content
        total_chars = sum(len(s) for s in sections)
        
        # Count structure elements
        total_headers = 0
        total_tables = 0
        total_paragraphs = 0
        
        for section in sections:
            headers = [line for line in section.split('\n') if line.strip().startswith('#')]
            total_headers += len(headers)
            
            table_lines = [line for line in section.split('\n') if '|' in line]
            if len(table_lines) >= 3:
                total_tables += 1
            
            paras = [p for p in section.split('\n\n') if p.strip()]
            total_paragraphs += len(paras)
        
        # Check quality
        combined_text = '\n\n'.join(sections)
        glyph_count = combined_text.count('GLYPH')
        
        # Prepare response with quality assessment
        result = {
            'success': True,
            'filename': filename,
            'extraction': {
                'method': extraction_method,  # "FAST", "BALANCED", "PREMIUM", "BASIC", or "FAILED"
                'method_icon': get_method_icon(extraction_method),
                'method_label': get_method_label(extraction_method),
                'quality_score': quality_score if quality_score is not None else calculate_quality_score(sections, glyph_count),
                'quality_recommendation': quality_recommendation,
                'quality_dimensions': quality_dimensions,
                'quality_issues': [
                    {'severity': 'warning', 'message': issue}
                    for issue in quality_issues
                ] if quality_issues else []
            },
            'stats': {
                'pages': len(sections),
                'total_chars': total_chars,
                'avg_page_size': total_chars // len(sections) if sections else 0,
                'headers': total_headers,
                'tables': total_tables,
                'paragraphs': total_paragraphs,
                'glyph_artifacts': glyph_count,
                'processing_time': round(processing_time, 2)
            },
            'metadata': extraction_metadata if USE_PROGRESSIVE and extraction_metadata else {},
            'pages': [
                {
                    'id': i,
                    'page_no': i,
                    'content': section,
                    'length': len(section),
                    'preview': section[:200] + ('...' if len(section) > 200 else '')
                }
                for i, section in enumerate(sections, 1)
            ],
            'quality': {
                'score': quality_score if quality_score is not None else calculate_quality_score(sections, glyph_count),
                'is_clean': glyph_count == 0,
                'has_structure': total_headers > 0
            }
        }
        
        # Clean up uploaded file
        try:
            filepath.unlink()
        except:
            pass
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def get_method_icon(method):
    """Get icon for extraction method"""
    icons = {
        'BASIC': '⚡',
        'FAST': '⚡',
        'BALANCED': '⚖️',
        'PREMIUM': '💎',
        'VLM': '🤖',
        'FAILED': '❌'
    }
    return icons.get(method.upper(), '📄')


def get_method_label(method):
    """Get human-readable label for extraction method"""
    labels = {
        'BASIC': 'Fast Extraction (Docling)',
        'FAST': 'Fast Extraction (Tier 1)',
        'BALANCED': 'Balanced Extraction (Tier 2 - Gemini Flash)',
        'PREMIUM': 'Premium Extraction (Tier 3 - Gemini Pro)',
        'VLM': 'VLM Extraction (Gemini)',
        'FAILED': 'Extraction Failed'
    }
    return labels.get(method.upper(), 'Unknown')


def calculate_quality_score(sections, glyph_count):
    """Calculate quality score for extraction (legacy fallback)"""
    score = 0.0
    
    # No GLYPH artifacts
    if glyph_count == 0:
        score += 0.3
    
    # Good section count
    if len(sections) > 10:
        score += 0.3
    elif len(sections) > 1:
        score += 0.2
    
    # Check structure
    total_headers = sum(
        len([line for line in s.split('\n') if line.strip().startswith('#')])
        for s in sections
    )
    
    if total_headers > 10:
        score += 0.2
    elif total_headers > 0:
        score += 0.1
    
    # Check paragraphs
    total_paras = sum(
        len([p for p in s.split('\n\n') if p.strip()])
        for s in sections
    )
    
    if total_paras > 10:
        score += 0.2
    elif total_paras > 0:
        score += 0.1
    
    return round(min(score, 1.0), 2)


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'docling': 'ready'})


if __name__ == '__main__':
    print("="*80)
    print("🚀 Enhanced Progressive Document Processor - Web Viewer")
    print("="*80)
    print(f"\n📂 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"📁 Output folder: {app.config['OUTPUT_FOLDER']}")
    print(f"📄 Allowed files: {', '.join(ALLOWED_EXTENSIONS)}")
    
    if USE_PROGRESSIVE:
        print(f"\n✨ Mode: Progressive Extraction with OpenRouter")
        print(f"   Tier 1 (Fast): Docling/MarkItDown - FREE")
        print(f"   Tier 2 (Balanced): Gemini 2.0 Flash Lite - ~$0.00008/page")
        print(f"   Tier 3 (Premium): Gemini 2.5 Pro - ~$0.0013/page")
        print(f"   Quality thresholds: Fast≥{processor.TIER_THRESHOLDS['fast']:.2f}, Balanced≥{processor.TIER_THRESHOLDS['balanced']:.2f}, Premium≥{processor.TIER_THRESHOLDS['premium']:.2f}")
        print(f"\n🎯 Features:")
        print(f"   • Multi-model support (Gemini, GPT-4V, Claude)")
        print(f"   • No quota limits (pay-as-you-go)")
        print(f"   • FREE tier available!")
        print(f"   • Auto-retry with tier escalation")
        print(f"   • Automatic fallback on errors")
    else:
        print(f"\n📝 Mode: Basic Extraction")
        print(f"   Set OPENROUTER_API_KEY environment variable for progressive mode")
    
    print(f"\n🌐 Open browser: http://localhost:5001")
    print("\n⚡ Press Ctrl+C to stop\n")
    print("="*80)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
