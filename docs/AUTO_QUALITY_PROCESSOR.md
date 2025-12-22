# 🤖 Auto-Quality Document Processor

Fully automated document extraction system optimized for **HIGHEST QUALITY**.  
Perfect for document ingestion pipelines before RAG indexing.

## 🎯 Key Features

### ✅ Zero Configuration Needed
```python
from src.core.auto_quality_processor import process_document_auto

result = process_document_auto("document.pdf", gemini_api_key="...")
if result.success:
    pages = result.pages  # Ready for indexing!
```

### 🚀 Intelligent Automation
1. **Visual Pre-Assessment** - Quick quality check (2-3 pages)
2. **Smart Tier Selection** - Choose optimal extraction method
3. **Auto-Retry Logic** - Escalate to better tier if quality insufficient
4. **Quality Guarantee** - Target ≥ 0.85, acceptable ≥ 0.70

### 💎 Quality-First Strategy
- **Target Quality**: 0.85 (excellent)
- **Minimum Acceptable**: 0.70 (good)
- **Auto-escalation**: Tries higher tiers until target met
- **Cost-aware**: Uses cheapest tier that meets quality goal

---

## 📖 Usage Examples

### 1. Single Document (Simple API)

```python
from src.core.auto_quality_processor import process_document_auto

result = process_document_auto(
    file_path="document.pdf",
    gemini_api_key="your_api_key_here",
    target_quality=0.85
)

if result.success:
    print(f"Quality: {result.quality_score:.3f}")
    print(f"Pages: {len(result.pages)}")
    print(f"Tier: {result.tier_used}")
    print(f"Cost: ${result.cost:.4f}")
    
    # Use the extracted text
    for i, page in enumerate(result.pages, 1):
        print(f"Page {i}: {page[:200]}...")
```

### 2. Batch Processing

```python
from src.core.auto_quality_processor import AutoQualityProcessor, AutoQualityConfig

# Configure
config = AutoQualityConfig(
    gemini_api_key="your_api_key_here",
    target_quality=0.85,
    enable_visual_precheck=True
)

# Create processor
processor = AutoQualityProcessor(config)

# Process multiple documents
documents = [
    "doc1.pdf",
    "doc2.pdf",
    "doc3.pdf"
]

results = processor.process_batch(documents, show_progress=True)

# Analyze
successful = [r for r in results if r.success]
print(f"Success rate: {len(successful)}/{len(results)}")
```

### 3. RAG Pipeline Integration

```python
from src.core.auto_quality_processor import AutoQualityProcessor, AutoQualityConfig

# Step 1: Configure processor
config = AutoQualityConfig(
    gemini_api_key="your_api_key_here",
    target_quality=0.85,
    enable_visual_precheck=True
)
processor = AutoQualityProcessor(config)

# Step 2: Extract from documents
documents = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
results = processor.process_batch(documents)

# Step 3: Prepare for indexing
chunks = []
for result in [r for r in results if r.success]:
    chunks.append({
        'text': "\n\n".join(result.pages),
        'metadata': {
            'source': result.file_path,
            'quality': result.quality_score,
            'tier': result.tier_used,
            'pages': len(result.pages)
        }
    })

# Step 4: Index to your vector store
from your_rag_system import VectorStore

vector_store = VectorStore()
for chunk in chunks:
    vector_store.add_document(
        text=chunk['text'],
        metadata=chunk['metadata']
    )

# Step 5: Get statistics
stats = processor.get_statistics()
print(f"Total cost: ${stats['total_cost']:.4f}")
print(f"Avg quality: {stats['average_quality']:.3f}")
```

---

## 🎯 How It Works

### Extraction Strategy

```
Document → Visual Assessment → Tier Selection → Extract → Validate → Return
                 (fast)           (smart)       (auto)    (retry)   (best)
```

### Tier Selection Logic

| Visual Quality | Starting Tier | Fallback Chain |
|---------------|---------------|----------------|
| ≥ 0.8 | Fast (Docling) | → Balanced → Premium |
| 0.5-0.8 | Balanced (Gemini Flash) | → Premium |
| < 0.5 | Premium (Gemini Pro) | (no fallback) |

### Quality Validation

```python
Extract → Check Quality → Compare to Target
                            ├─ >= 0.85 → Return (excellent!)
                            ├─ >= 0.70 → Return (acceptable)
                            └─ < 0.70  → Retry with next tier
```

---

## 💰 Cost Optimization

### Tier Pricing
- **Fast** (Docling): $0/page - Free!
- **Balanced** (Gemini Flash): ~$0.0001/page
- **Premium** (Gemini Pro): ~$0.0005/page

### Smart Cost Management
1. **Try Fast First** - For high-quality PDFs
2. **Escalate Only If Needed** - When quality insufficient
3. **Track Everything** - Full cost visibility
4. **Optimize Over Time** - Learn from historical data

### Example Costs
```
10-page PDF:
- Fast tier: $0.00
- Balanced tier: $0.001
- Premium tier: $0.005

100-page document:
- Fast tier: $0.00
- Balanced tier: $0.01
- Premium tier: $0.05
```

---

## 🔧 Configuration Options

```python
AutoQualityConfig(
    gemini_api_key: str,              # Required
    target_quality: float = 0.85,      # Target score (0-1)
    min_acceptable_quality: float = 0.70,  # Minimum acceptable
    enable_visual_precheck: bool = True,   # Pre-assess quality
    max_retries: int = 3,              # Max tier escalations
    cost_tracking: bool = True,        # Track costs
    batch_size: int = 10               # Batch processing size
)
```

---

## 📊 Result Structure

```python
ProcessingResult(
    file_path: str,           # Source file path
    success: bool,            # Processing success
    pages: List[str],         # Extracted pages
    quality_score: float,     # Overall quality (0-1)
    tier_used: str,           # Tier used (fast/balanced/premium)
    cost: float,              # Processing cost ($USD)
    processing_time: float,   # Time taken (seconds)
    error: Optional[str],     # Error message if failed
    metadata: Dict[str, Any]  # Additional metadata
)
```

---

## 🌐 Web UI Usage

### Auto Mode (Default) - Recommended for Quality
1. Select **"อัตโนมัติ (แนะนำ)"** mode
2. Upload document
3. System automatically:
   - Assesses visual quality
   - Selects best tier
   - Retries if quality insufficient
   - Returns highest quality result

### Manual Mode - For Custom Settings
1. Select **"กำหนดเอง"** mode
2. Configure:
   - Visual pre-check (on/off)
   - Document importance (low/medium/high)
   - Budget mode (free/balanced/premium)
   - Force specific tier (optional)
3. Upload document

---

## 📈 Quality Metrics

### 5-Dimension Assessment
1. **Text Quality** (25%) - Character issues, encoding
2. **Word Quality** (20%) - Word patterns, vocabulary
3. **Page Consistency** (15%) - Page variance
4. **Structure** (20%) - Headers, lists, formatting
5. **Content Density** (20%) - Text richness

### Quality Scores
- 🟢 **0.85-1.00**: Excellent - Production ready
- 🟡 **0.70-0.85**: Good - Acceptable for most uses
- 🟠 **0.50-0.70**: Fair - May need review
- 🔴 **< 0.50**: Poor - Manual intervention needed

---

## 🚀 Quick Start

### 1. Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Set API key in .env
echo "GEMINI_API_KEY=your_key_here" >> .env
```

### 2. Run Example
```bash
python examples/pipeline_usage.py
```

### 3. Start Web UI
```bash
python web/app.py
# Open http://localhost:5001
```

---

## 📝 Best Practices

### ✅ DO
- Use **Auto Mode** for pipelines
- Set `target_quality=0.85` for production
- Enable `visual_precheck` for efficiency
- Track costs with `cost_tracking=True`
- Batch process for better throughput

### ❌ DON'T
- Force specific tiers (let system decide)
- Skip visual pre-check (saves time/money)
- Set target too low (<0.70)
- Process one-by-one (use batching)
- Ignore quality scores in metadata

---

## 🔍 Troubleshooting

### Low Quality Scores
**Problem**: Getting scores < 0.70  
**Solutions**:
- Check source document quality
- Try rescanning at higher DPI
- Use image enhancement tools
- Consider manual review

### High Costs
**Problem**: Excessive API usage  
**Solutions**:
- Enable visual pre-check
- Let system choose tier automatically
- Batch process documents
- Review quality targets

### Slow Processing
**Problem**: Taking too long  
**Solutions**:
- Use batch processing
- Disable visual pre-check for known-good documents
- Process in parallel (multiple processors)
- Consider async implementation

---

## 📚 Additional Resources

- [Visual Quality Assessor](../src/core/visual_quality_assessor.py) - Pre-assessment details
- [Cost Optimizer](../src/core/cost_optimizer.py) - Cost tracking & optimization
- [Enhanced Processor](../src/core/enhanced_progressive_processor.py) - 3-tier extraction
- [Pipeline Examples](../examples/pipeline_usage.py) - Complete examples

---

## 🎯 Summary

**For Pipeline Use:**
```python
from src.core.auto_quality_processor import process_document_auto

result = process_document_auto("document.pdf", api_key="...")
if result.success:
    # Use result.pages for indexing
    index_to_vector_store(result.pages, result.metadata)
```

**That's it!** The system handles everything automatically:
- ✅ Visual quality assessment
- ✅ Optimal tier selection  
- ✅ Auto-retry if needed
- ✅ Cost optimization
- ✅ Quality guarantee

Perfect for production pipelines! 🚀
