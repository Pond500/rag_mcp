# 🚀 Quick Start: OpenRouter-based Document Extraction

## ✨ What Changed?

### Before (Gemini API):
- ❌ Free tier quota limits
- ❌ 429 errors frequently
- ❌ Single model only
- ❌ Complex API versioning

### After (OpenRouter):
- ✅ Multiple models (Gemini, GPT-4V, Claude)
- ✅ Pay-as-you-go (no quotas)
- ✅ FREE tier available! (`gemini-2.0-flash-exp:free`)
- ✅ Automatic fallback
- ✅ Single unified API

---

## 🔑 Step 1: Get OpenRouter API Key

1. Go to: https://openrouter.ai/
2. Sign up (free)
3. Get API key: https://openrouter.ai/keys
4. Copy key (starts with `sk-or-v1-...`)

---

## 📦 Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🎯 Step 3: Use the System

### Option A: Use FREE Tier (No Cost!)

```python
from src.core.progressive_processor import ProgressiveDocumentProcessor

# Initialize with OpenRouter
processor = ProgressiveDocumentProcessor(
    openrouter_api_key="sk-or-v1-your-key-here",
    enable_fast_tier=True,      # Docling (free)
    enable_balanced_tier=True,   # Gemini Flash (cheap)
    enable_premium_tier=True     # Gemini Pro (best)
)

# Extract with automatic tier selection
result = processor.extract_with_smart_routing(
    pdf_path="document.pdf",
    target_quality=0.85,
    start_tier='fast'  # Try free tier first!
)

# Use the result
if result.success:
    print(f"✅ Extracted {len(result.pages)} pages")
    print(f"Quality: {result.quality_score:.3f}")
    print(f"Tier used: {result.tier_used}")
    print(f"Cost: ${result.cost:.4f}")
    
    # Get the text
    for i, page in enumerate(result.pages, 1):
        print(f"\nPage {i}:\n{page[:500]}...")
```

### Option B: Direct OpenRouter Extraction

```python
from src.core.openrouter_extractor import OpenRouterExtractor

# Use FREE model
extractor = OpenRouterExtractor(
    api_key="sk-or-v1-your-key-here",
    model='free'  # google/gemini-2.0-flash-exp:free
)

pages = extractor.extract_from_pdf("document.pdf")
print(f"Extracted {len(pages)} pages - FREE!")
```

---

## 💰 Pricing

| Tier | Model | Cost/Page | Quality | Speed |
|------|-------|-----------|---------|-------|
| **Free** | Gemini 2.0 Flash (Free) | $0.00 | Good | Fast |
| **Balanced** | Gemini Flash 1.5 8B | ~$0.0001 | Very Good | Fast |
| **Premium** | Gemini Pro 1.5 | ~$0.0005 | Excellent | Medium |
| **GPT-4V** | OpenAI GPT-4 Vision | ~$0.01 | Excellent | Slow |
| **Claude** | Anthropic Claude 3.5 | ~$0.003 | Best | Medium |

### Example Costs:
```
10-page document:
- Free tier: $0.00 ✅
- Balanced: $0.001 ($0.10 per 1000 pages)
- Premium: $0.005 ($5.00 per 1000 pages)

100-page document:
- Free tier: $0.00 ✅
- Balanced: $0.01
- Premium: $0.05
```

---

## 🎯 How It Works

### Automatic Tier Escalation:

```
1. Try Fast Tier (FREE)
   ↓ Quality < 0.85?
2. Try Balanced Tier ($0.0001/page)
   ↓ Quality < 0.85?
3. Try Premium Tier ($0.0005/page)
   ↓
4. Return Best Result
```

### Quality Targets:
- **Excellent** (0.85-1.00): Production ready
- **Good** (0.70-0.85): Acceptable
- **Fair** (0.50-0.70): Review needed
- **Poor** (< 0.50): Re-extract

---

## 🔧 Advanced Usage

### Custom Model Selection:

```python
from src.core.openrouter_extractor import OpenRouterExtractor

# Use specific model
extractor = OpenRouterExtractor(
    api_key="sk-or-v1-...",
    model='gpt4v'  # Or 'claude', 'premium', 'balanced', 'free'
)

pages = extractor.extract_from_pdf("document.pdf", dpi=300)
```

### With Fallback:

```python
extractor = OpenRouterExtractor(
    api_key="sk-or-v1-...",
    model='premium',
    fallback_models=['balanced', 'free']  # Auto-fallback on error
)

pages, model_used, cost = extractor.extract_with_fallback(
    pdf_path="document.pdf"
)

print(f"Used: {model_used}, Cost: ${cost:.4f}")
```

### Batch Processing:

```python
from src.core.progressive_processor import ProgressiveDocumentProcessor

processor = ProgressiveDocumentProcessor(
    openrouter_api_key="sk-or-v1-..."
)

documents = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
results = []

for doc in documents:
    result = processor.extract_with_smart_routing(
        pdf_path=doc,
        target_quality=0.85
    )
    results.append(result)

# Analyze
total_cost = sum(r.cost for r in results)
avg_quality = sum(r.quality_score for r in results) / len(results)

print(f"Processed {len(results)} documents")
print(f"Total cost: ${total_cost:.4f}")
print(f"Average quality: {avg_quality:.3f}")
```

---

## 🌐 Web UI

Update your `.env`:

```bash
# OpenRouter API (replaces Gemini)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Start web server:

```bash
python web/app.py
```

Open: http://localhost:5001

---

## 🆘 Troubleshooting

### Error: "OpenRouter API key required"
**Solution:** Get key from https://openrouter.ai/keys

### Error: "Insufficient credits"
**Solution:** 
1. Use FREE tier: `model='free'`
2. Or add credits: https://openrouter.ai/credits

### Slow extraction
**Solutions:**
- Use `'free'` or `'balanced'` models (faster)
- Lower DPI: `dpi=150` instead of `300`
- Process in batches

### Low quality scores
**Solutions:**
- Try premium model: `model='premium'`
- Increase DPI: `dpi=300`
- Enable auto-retry: `auto_retry=True`

---

## 📚 Available Models

Check all models:

```python
from src.core.openrouter_extractor import OpenRouterExtractor

models = OpenRouterExtractor.get_available_models()
for tier, config in models.items():
    print(f"{tier}: {config['name']} - ${config['cost_per_page']}/page")
```

Output:
```
free: Gemini 2.0 Flash (Free) - $0.0/page
balanced: Gemini Flash 1.5 8B - $0.0001/page
premium: Gemini Pro 1.5 - $0.0005/page
gpt4v: GPT-4 Vision - $0.01/page
claude: Claude 3.5 Sonnet - $0.003/page
```

---

## 🎓 Examples

### 1. Single Document (Free):
```python
from src.core.progressive_processor import ProgressiveDocumentProcessor

processor = ProgressiveDocumentProcessor(openrouter_api_key="sk-or-v1-...")
result = processor.extract_with_smart_routing("doc.pdf", start_tier='fast')
# Cost: $0.00 (uses Docling first)
```

### 2. High-Quality Extraction:
```python
result = processor.extract_with_smart_routing(
    pdf_path="important-doc.pdf",
    target_quality=0.90,  # High target
    start_tier='premium'  # Start with best
)
# Cost: ~$0.0005/page
```

### 3. Cost-Optimized Pipeline:
```python
# Use free tier only
processor = ProgressiveDocumentProcessor(
    enable_fast_tier=True,
    enable_balanced_tier=False,  # Disable paid tiers
    enable_premium_tier=False
)

result = processor.extract_with_smart_routing("doc.pdf")
# Cost: $0.00 guaranteed!
```

---

## ✅ Migration from Gemini

### Old Code:
```python
from src.core.gemini_extractor import GeminiVLMExtractor

extractor = GeminiVLMExtractor(
    api_key="gemini-key",
    model_name="gemini-2.0-flash-exp"
)
pages = extractor.extract_from_pdf("doc.pdf")
```

### New Code:
```python
from src.core.openrouter_extractor import OpenRouterExtractor

extractor = OpenRouterExtractor(
    api_key="sk-or-v1-...",  # OpenRouter key
    model='free'  # Same model, via OpenRouter
)
pages = extractor.extract_from_pdf("doc.pdf")
```

---

## 🎉 Benefits Summary

1. **No Quota Issues**: Pay-as-you-go, no daily limits
2. **FREE Tier**: Use `gemini-2.0-flash-exp:free` at no cost
3. **Multi-Model**: Switch between Gemini, GPT-4V, Claude easily
4. **Auto-Fallback**: Graceful degradation on errors
5. **Unified API**: One interface for all models
6. **Cost Tracking**: Know exactly what you're spending

---

## 📞 Support

- OpenRouter Docs: https://openrouter.ai/docs
- Get API Key: https://openrouter.ai/keys
- Check Usage: https://openrouter.ai/activity
- Pricing: https://openrouter.ai/models

---

**Ready to extract?** 🚀

```python
from src.core.progressive_processor import ProgressiveDocumentProcessor

processor = ProgressiveDocumentProcessor(openrouter_api_key="sk-or-v1-...")
result = processor.extract_with_smart_routing("your-document.pdf")

if result.success:
    print("🎉 Done! Quality:", result.quality_score)
    print("💰 Cost: $", result.cost)
```
