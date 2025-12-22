# Progressive Document Extraction

**2-Level extraction pipeline with automatic quality-based fallback**

## 🎯 Overview

Progressive Document Extraction automatically chooses the best extraction method based on quality assessment:

- **Level 1 (Fast)**: Docling/MarkItDown extraction
  - ✅ Pass threshold: `quality_score >= 0.85`
  - ⚡ Fast processing
  - 💰 No API costs
  - Works for most documents

- **Level 2 (VLM)**: Gemini 2.0 Flash extraction
  - ✅ Pass threshold: `quality_score >= 0.70`
  - 🤖 Advanced OCR + context understanding
  - 🎯 Better for scanned/complex documents
  - 💸 API costs apply (automatic fallback only when needed)

## 📦 Installation

### 1. Install Python dependencies

```bash
# Install base requirements first
pip install -r requirements.txt

# Install progressive extraction dependencies
pip install -r requirements_progressive.txt
```

### 2. Install system dependencies

**pdf2image requires poppler-utils:**

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
# Add to PATH
```

### 3. Configure API key

```python
from types import SimpleNamespace

config = SimpleNamespace()
config.gemini_api_key = "your-api-key-here"
```

## 🚀 Quick Start

### Basic Usage

```python
from src.core.progressive_processor import ProgressiveDocumentProcessor
from types import SimpleNamespace

# Configure
config = SimpleNamespace()
config.level1_threshold = 0.85  # Level 1 pass threshold
config.level2_threshold = 0.70  # Level 2 pass threshold
config.gemini_api_key = "your-api-key"

# Initialize processor
processor = ProgressiveDocumentProcessor(config)

# Extract text (automatic fallback)
pages, method, report = processor.extract_text("document.pdf")

print(f"Method: {method}")  # "BASIC" or "VLM"
print(f"Quality: {report.overall_score:.3f}")
print(f"Pages: {len(pages)}")
```

### Force VLM Extraction

```python
# Skip Level 1 and use VLM directly (for known scanned docs)
pages, method, report = processor.extract_text(
    "scanned_document.pdf",
    force_vlm=True
)
```

### Quality Assessment Only

```python
from src.core.quality_checker import UnsupervisedQualityChecker

checker = UnsupervisedQualityChecker()
report = checker.check_quality(pages)

print(f"Quality: {report.overall_score:.3f}")
print(f"Recommendation: {report.get_recommendation()}")

# Check dimension scores
for name, dim in report.dimensions.items():
    print(f"{name}: {dim.score:.3f}")
```

## 📊 Quality Assessment

### 5 Quality Dimensions

The `UnsupervisedQualityChecker` evaluates extraction quality across 5 dimensions:

1. **Text Quality (25%)**
   - Replacement characters (�)
   - Non-printable characters
   - Whitespace ratio
   - Alphanumeric ratio

2. **Word Quality (20%)**
   - Average word length (should be 4-8)
   - Very long words ratio (<20 chars)
   - Unique word ratio
   - Thai language presence

3. **Page Consistency (15%)**
   - Page length variance (CV)
   - Empty pages ratio

4. **Structure (20%)**
   - Markdown headers
   - Lists and tables
   - Excessive newlines
   - Average line length

5. **Content Density (20%)**
   - Chars per page (>500)
   - Words per page (>80)
   - Content line ratio
   - Repetition score

### Quality Thresholds

```python
# Overall quality score (0.0 - 1.0)
score >= 0.85  # EXCELLENT - Level 1 passes
score >= 0.70  # GOOD - Level 2 passes
score >= 0.50  # FAIR - Consider manual review
score < 0.50   # POOR - Needs attention
```

## 🔧 Configuration Options

```python
config = SimpleNamespace()

# Quality thresholds
config.level1_threshold = 0.85  # Default: 0.85
config.level2_threshold = 0.70  # Default: 0.70

# Gemini settings
config.gemini_api_key = "your-key"           # Required for Level 2
config.gemini_model = "gemini-2.0-flash-exp" # Default model
config.image_dpi = 300                       # PDF to image DPI

# Text processing
config.chunk_size = 1000       # Chunk size for RAG
config.chunk_overlap = 200     # Chunk overlap
```

## 📝 Usage Examples

### Example 1: RAG Pipeline Integration

```python
from src.core.progressive_processor import ProgressiveDocumentProcessor

processor = ProgressiveDocumentProcessor(config)

# Extract with quality check
pages, method, report = processor.extract_text("kb_document.pdf")

# Only index if quality is acceptable
if report.overall_score >= 0.50:
    chunks = processor.chunk_text(pages)
    # vector_store.add_documents(chunks)
    print(f"✅ Indexed {len(chunks)} chunks")
else:
    print(f"❌ Quality too low: {report.overall_score:.3f}")
```

### Example 2: Batch Processing

```python
results = {'level1': 0, 'level2': 0, 'failed': 0}

for file_path in files:
    pages, method, report = processor.extract_text(file_path)
    
    if method == "BASIC":
        results['level1'] += 1
    elif method == "VLM":
        results['level2'] += 1
    else:
        results['failed'] += 1

print(f"Level 1: {results['level1']}")
print(f"Level 2: {results['level2']} (VLM)")
print(f"Failed: {results['failed']}")
```

### Example 3: Custom Quality Checker

```python
from src.core.quality_checker import UnsupervisedQualityChecker

checker = UnsupervisedQualityChecker()

# Override dimension weights
checker.dimension_weights = {
    'text_quality': 0.30,      # Increase text quality importance
    'word_quality': 0.15,
    'page_consistency': 0.10,
    'structure': 0.25,
    'content_density': 0.20
}

report = checker.check_quality(pages)
```

## 🔍 Quality Report Structure

```python
report = checker.check_quality(pages)

# Overall assessment
report.overall_score      # 0.0 - 1.0
report.get_recommendation()  # "EXCELLENT", "GOOD", "FAIR", "POOR"

# Dimension breakdown
for name, dim in report.dimensions.items():
    dim.name     # Dimension name
    dim.score    # 0.0 - 1.0
    dim.weight   # Weight in overall score
    dim.signals  # Raw metrics
    dim.issues   # List of issues found

# Issues
for severity, message in report.issues:
    print(f"[{severity}] {message}")
```

## 📈 Performance

### Extraction Speed

- **Level 1**: ~1-5 seconds per page (CPU-based)
- **Level 2**: ~2-10 seconds per page (API calls)

### Quality Comparison

| Document Type | Level 1 Quality | Level 2 Quality | Recommendation |
|--------------|-----------------|-----------------|----------------|
| Digital PDF | 0.90+ | 0.92+ | Use Level 1 |
| Scanned PDF | 0.60-0.75 | 0.85+ | Level 2 triggered |
| Complex Layout | 0.70-0.80 | 0.88+ | Level 2 triggered |
| Mixed Content | 0.75-0.85 | 0.90+ | Level 1 often passes |

### Cost Optimization

```python
# Monitor extraction methods to optimize costs
batch_results = {
    'level1_passed': 0,  # No API costs
    'level2_needed': 0,  # API costs incurred
}

# If Level 2 needed > 30%, consider:
# 1. Lowering level1_threshold (more tolerant)
# 2. Pre-processing documents (deskew, denoise)
# 3. Using dedicated OCR preprocessing
```

## 🔬 Advanced Features

### Thai Language Support

The quality checker includes Thai-specific checks:

```python
# Thai language metrics in quality report
signals = dimension.signals

signals['thai_ratio']           # Ratio of Thai characters
signals['common_thai_found']    # Count of common Thai words
signals['thai_tone_marks']      # Tone mark balance check
```

### Custom Extraction Prompt

```python
from src.core.gemini_extractor import GeminiVLMExtractor

# Override extraction prompt
extractor = GeminiVLMExtractor(api_key="your-key")

extractor.EXTRACTION_PROMPT = """
Your custom prompt here:
- Extract all text
- Preserve structure
- Special instructions...
"""

pages = extractor.extract_from_pdf("doc.pdf")
```

### Error Handling

```python
try:
    pages, method, report = processor.extract_text(file_path)
except ImportError as e:
    print(f"Missing dependency: {e}")
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Extraction failed: {e}")
```

## 🧪 Testing

```bash
# Run quality checker tests
python examples/progressive_extraction_demo.py

# Test with your documents
python -c "
from src.core.progressive_processor import ProgressiveDocumentProcessor
from types import SimpleNamespace

config = SimpleNamespace()
config.gemini_api_key = 'your-key'

processor = ProgressiveDocumentProcessor(config)
pages, method, report = processor.extract_text('test.pdf')

print(f'Method: {method}')
print(f'Quality: {report.overall_score:.3f}')
"
```

## 📚 Architecture

```
Progressive Document Extraction
│
├── Level 1: Fast Extraction
│   ├── DocumentProcessor (existing)
│   │   ├── MarkItDown (Office files)
│   │   ├── Docling (PDFs)
│   │   └── Simple (TXT/MD)
│   │
│   └── UnsupervisedQualityChecker
│       └── 5 dimension assessment
│           └── quality_score >= 0.85? ✅ Done
│                                    ❌ → Level 2
│
└── Level 2: VLM Extraction
    ├── GeminiVLMExtractor
    │   ├── PDF → Images (pdf2image)
    │   └── Gemini 2.0 Flash API
    │
    └── UnsupervisedQualityChecker
        └── quality_score >= 0.70? ✅ Done
                                   ❌ → Return best result
```

## 🐛 Troubleshooting

### Import Error: google-generativeai

```bash
pip install google-generativeai
```

### Import Error: pdf2image

```bash
pip install pdf2image
# Also install poppler (see Installation section)
```

### Low Quality Scores

1. **Check extraction output**: Print first page to see what was extracted
2. **Inspect dimension scores**: Identify which dimension is failing
3. **Adjust thresholds**: Lower thresholds if consistently failing
4. **Pre-process documents**: Deskew, denoise, increase DPI

### VLM API Errors

```python
# Check API key
config.gemini_api_key = "your-valid-key"

# Check API quota
# Visit: https://aistudio.google.com/app/apikey

# Handle rate limits
from time import sleep
for file in files:
    pages, method, report = processor.extract_text(file)
    sleep(1)  # Rate limiting
```

## 📄 License

Same as main project license.

## 🤝 Contributing

Contributions welcome! Areas for improvement:

1. Additional quality dimensions
2. Language-specific checks (Chinese, Japanese, etc.)
3. Custom extraction models
4. Quality threshold optimization
5. Performance benchmarks

## 📞 Support

For issues or questions:
1. Check examples in `examples/progressive_extraction_demo.py`
2. Review quality reports for insights
3. Open an issue with quality report output
