"""
Hybrid Document Processing Web Viewer
Upload documents and view extraction results in real-time

Supports:
- PDF, Word (.pdf, .docx, .doc) → Docling
- Excel, PowerPoint (.xlsx, .xls, .pptx, .ppt) → MarkItDown → Docling fallback
- Plain text (.txt, .md) → Simple extraction
"""
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import sys
import time
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
processor = DocumentProcessor(config=settings)


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
        
        # Extract with Docling
        start_time = time.time()
        sections = processor.extract_text(str(filepath), clean_text=True, validate=False)
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
        
        # Prepare response
        result = {
            'success': True,
            'filename': filename,
            'stats': {
                'sections': len(sections),
                'total_chars': total_chars,
                'avg_section_size': total_chars // len(sections) if sections else 0,
                'headers': total_headers,
                'tables': total_tables,
                'paragraphs': total_paragraphs,
                'glyph_artifacts': glyph_count,
                'processing_time': round(processing_time, 2)
            },
            'sections': [
                {
                    'id': i,
                    'content': section,
                    'length': len(section),
                    'preview': section[:200] + ('...' if len(section) > 200 else '')
                }
                for i, section in enumerate(sections, 1)
            ],
            'quality': {
                'score': calculate_quality_score(sections, glyph_count),
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


def calculate_quality_score(sections, glyph_count):
    """Calculate quality score for extraction"""
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
    print("🚀 Docling Web Viewer")
    print("="*80)
    print(f"\n📂 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"📁 Output folder: {app.config['OUTPUT_FOLDER']}")
    print(f"📄 Allowed files: {', '.join(ALLOWED_EXTENSIONS)}")
    print(f"\n🌐 Open browser: http://localhost:5001")
    print("\n⚡ Press Ctrl+C to stop\n")
    print("="*80)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
