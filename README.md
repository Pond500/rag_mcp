# Multi-KB RAG System v2.1 with Progressive VLM Extraction

**Production-ready Multi-Knowledge Base RAG system** with 2-Tier Progressive Document Extraction (Docling → Gemini Pro VLM), Hybrid Search (Dense + Sparse BM25), RRF fusion, Reranking, and Semantic Routing via Model Context Protocol (MCP). Fully observable with Langfuse integration.

![Version](https://img.shields.io/badge/version-2.1.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Langfuse](https://img.shields.io/badge/observability-Langfuse-purple)

---

## 🌟 Features

### Core Capabilities
- 🎯 **Multi-KB Management** - Manage multiple independent knowledge bases
- 📄 **Progressive Document Extraction** - 2-tier strategy (Docling → Gemini Pro)
  - Tier 1: Docling (FREE, ~10s/doc) for text PDFs
  - Tier 3: Gemini Pro VLM ($0.0013/page) for complex/scanned PDFs
  - Quality-based escalation (5-dimension scoring)
  - Auto VLM cost tracking (actual OpenRouter API costs)
- � **Hybrid Search** - Dense vector (BAAI/bge-m3) + Sparse BM25 (Qdrant/bm25)
- 🔀 **RRF Fusion** - Reciprocal Rank Fusion for optimal result merging
- 🎓 **Reranking** - CrossEncoder (BAAI/bge-reranker-v2-m3) for precision
- 🧭 **Semantic Routing** - Automatic KB selection based on query semantics
- 💬 **Conversation History** - Session-based chat with context retention
- � **Full Observability** - Langfuse integration for traces, costs, and evaluation metrics
- 🤖 **LLM Integration** - OpenRouter API gateway (Gemini, GPT-4, Claude, local LLMs)

### Architecture Highlights
- ✨ **Clean Architecture** - Separation of concerns (config, models, core, services, mcp, observability)
- 🔌 **Lazy Loading** - Models load on-demand with fallback mechanisms
- ⚙️ **Type-Safe Config** - Pydantic Settings with environment variable support
- 📊 **Production Logging** - Colored console + rotating file logs with request tracking
- 📈 **Observability** - Langfuse traces with cost/latency tracking, evaluation scores
- 🧪 **Comprehensive Tests** - Unit and integration tests for all layers
- 🚀 **MCP Protocol** - FastAPI server with 13 MCP tools + REST API endpoints
- 💰 **Cost Optimized** - 90% documents use FREE tier (Docling), 80% cost savings

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Architecture](#-architecture)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker (for Qdrant)
- OpenRouter API key (for VLM extraction - optional)
- Langfuse instance (for observability - optional)

### 1. Clone & Install
```bash
git clone https://github.com/Pond500/rag-mcp-server.git
cd mcp_rag_v2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install base dependencies
pip install -r requirements.txt

# Install VLM dependencies (for progressive extraction)
pip install -r requirements_progressive.txt
```

### 2. Start Qdrant
```bash
docker-compose up -d
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings:
# - OPENROUTER_API_KEY (for VLM extraction)
# - LANGFUSE credentials (for observability)
# - LLM settings (OpenRouter models)
```

### 4. Run Server
```bash
# Standard mode
python scripts/run_server.py

# With Ngrok tunnel (for external access)
bash scripts/start_with_ngrok.sh

# Or using uvicorn directly
uvicorn mcp.server:app --reload --port 8000
```

### 5. Access API
- **API**: http://localhost:8000
- **OpenAPI Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/tools/health
- **Langfuse Dashboard**: http://your-langfuse-host:3000 (if configured)

---

## 📦 Installation

### Option 1: Standard Installation (Basic RAG)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start Qdrant
docker-compose up -d

# Verify installation
python test_config.py
```

### Option 2: Full Installation (with VLM + Observability)
```bash
# Install base + VLM dependencies
pip install -r requirements.txt
pip install -r requirements_progressive.txt

# Start Qdrant
docker-compose up -d

# Configure Langfuse (optional)
# Set LANGFUSE_* variables in .env

# Run tests
python -m pytest tests/
```

---

## ⚙️ Configuration

### Environment Variables
Create a `.env` file (use `.env.example` as template):

```env
# Qdrant Settings
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_TIMEOUT=30

# LLM Settings (OpenRouter)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# VLM Extraction Settings
ENABLE_PROGRESSIVE_EXTRACTION=true
OPENROUTER_VLM_MODEL_FREE=google/gemini-2.0-flash-exp:free
OPENROUTER_VLM_MODEL_PREMIUM=google/gemini-2.5-pro
IMAGE_DPI=200
TARGET_QUALITY=0.70

# Langfuse Observability (optional)
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PROJECT=mcp-rag-v2
LANGFUSE_ENVIRONMENT=development

# Embedding Settings
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIMENSION=1024
SPARSE_EMBEDDING_MODEL=Qdrant/bm25

# Search Settings
SEARCH_TOP_K=5
SEARCH_RRF_K=60
RERANK_THRESHOLD=0.0

# Document Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Configuration Files
- `src/config/settings.py` - Pydantic Settings classes
- `src/config/prompts.yaml` - System prompts and templates
- `.env` - Environment-specific settings

---

## 🎯 Usage

### Python SDK

```python
from src.config import get_settings
from src.services import RAGService

# Initialize service
settings = get_settings()
service = RAGService.from_settings(settings)

# 1. Create Knowledge Base
result = service.create_kb(
    kb_name="company_docs",
    description="Company documentation and policies",
    category="internal"
)

# 2. Upload Document (with Progressive VLM Extraction)
with open("policy.pdf", "rb") as f:
    result = service.upload_document(
        kb_name="company_docs",
        filename="policy.pdf",
        file_content=f.read()
    )

# Check extraction results
print(f"VLM Cost: ${result['vlm_cost']:.4f}")
print(f"Pages: {result['pages_processed']}")
print(f"Chunks: {result['chunks_created']}")
print(f"Extraction Quality: {result.get('extraction_quality', 'N/A')}")

# 3. Search
result = service.search(
    query="What is the vacation policy?",
    kb_name="company_docs",
    top_k=5
)

# 4. Chat with RAG
result = service.chat(
    query="How many vacation days do I get?",
    kb_name="company_docs",
    session_id="user_123"
)

print(result["answer"])
```

### REST API

```bash
# Create KB
curl -X POST http://localhost:8000/tools/create_kb \
  -H "Content-Type: application/json" \
  -d '{
    "kb_name": "my_kb",
    "description": "My knowledge base",
    "category": "general"
  }'

# Upload Document
curl -X POST http://localhost:8000/tools/upload_document \
  -F "kb_name=my_kb" \
  -F "file=@document.pdf"

# Search
curl -X POST http://localhost:8000/tools/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Your question here",
    "kb_name": "my_kb",
    "top_k": 5
  }'

# Chat
curl -X POST http://localhost:8000/tools/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Your question here",
    "kb_name": "my_kb",
    "session_id": "session_123"
  }'
```

---

## 📚 API Documentation

### MCP Tools (Endpoints)

#### 1. `POST /tools/create_kb`
Create a new knowledge base
```json
{
  "kb_name": "string",
  "description": "string",
  "category": "general" | "dopa" | "fidf" | "contracts" | etc.,
  "enable_routing": true
}
```

#### 2. `POST /tools/delete_kb`
Delete a knowledge base
```json
{
  "kb_name": "string"
}
```

#### 3. `GET /tools/list_kbs`
List all knowledge bases

**Response:**
```json
{
  "success": true,
  "kbs": [
    {
      "name": "string",
      "description": "string",
      "category": "string",
      "document_count": 0,
      "vector_count": 0,
      "created_at": "2026-01-06T..."
    }
  ]
}
```

#### 4. `POST /tools/upload_document`
Upload document with progressive VLM extraction (multipart/form-data)
- `kb_name`: string (required)
- `file`: file (PDF, DOCX, TXT, XLSX, PPTX)
- `description`: string (optional)

**Response:**
```json
{
  "success": true,
  "vlm_cost": 0.0078,
  "pages_processed": 6,
  "chunks_created": 45,
  "document_name": "policy.pdf",
  "extraction_tier": "premium",
  "extraction_quality": 0.97,
  "processing_time_seconds": 368.5
}
```

#### 5. `POST /tools/search`
Search with Hybrid Search (Dense + Sparse + Reranking)
```json
{
  "query": "string",
  "kb_name": "string" | null,
  "top_k": 5,
  "use_routing": true,
  "use_reranking": true,
  "include_metadata": true,
  "deduplicate": true
}
```

**Response:**
```json
{
  "success": true,
  "query": "string",
  "kb_name": "string",
  "total_results": 5,
  "results": [
    {
      "text": "string",
      "score": 0.95,
      "metadata": {...}
    }
  ],
  "metadata_summary": [...]
}
```

#### 6. `POST /tools/chat`
Chat with RAG (with conversation history)
```json
{
  "query": "string",
  "kb_name": "string" | null,
  "session_id": "string" | null,
  "top_k": 5,
  "use_routing": true,
  "use_reranking": true
}
```

**Response:**
```json
{
  "success": true,
  "query": "string",
  "answer": "string",
  "kb_name": "string",
  "session_id": "string",
  "sources": [...],
  "documents_used": 3,
  "tokens": {
    "input": 150,
    "output": 200,
    "total": 350
  },
  "cost": 0.0005
}
```

#### 7. `POST /tools/clear_history`
Clear conversation history
```json
{
  "session_id": "string"
}
```

#### 8. `GET /tools/health`
Health check

**Response:**
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "qdrant": "connected",
  "embedding_model": "BAAI/bge-m3",
  "langfuse": "enabled",
  "progressive_extraction": "enabled"
}
```

#### Additional Tools:
- **9-13**: Document management (list, get, update, delete, list documents)

See `/docs` endpoint for complete API documentation.

---

## 🏗️ Architecture

```
mcp_rag_v2/
├── src/
│   ├── config/              # Configuration (Pydantic Settings + YAML prompts)
│   │   ├── settings.py
│   │   └── prompts.yaml
│   ├── utils/               # Utilities (logging, helpers)
│   │   └── logger.py
│   ├── models/              # Model wrappers (embeddings, reranker, llm)
│   │   ├── embeddings.py
│   │   ├── reranker.py
│   │   └── llm.py
│   ├── core/                # Core business logic
│   │   ├── collection_manager.py        # KB CRUD
│   │   ├── document_processor.py        # Docling extraction (Tier 1)
│   │   ├── progressive_processor.py     # VLM orchestrator (Tier 2-3)
│   │   ├── openrouter_extractor.py      # OpenRouter VLM API
│   │   ├── quality_checker.py           # 5-dimension quality scoring
│   │   ├── metadata_extractor.py        # AI metadata extraction
│   │   ├── vector_store.py              # Qdrant operations
│   │   ├── retriever.py                 # Hybrid Search + RRF + Reranking
│   │   ├── router.py                    # Semantic routing
│   │   └── chat_engine.py               # LLM chat with history
│   ├── services/            # Service layer (RAG orchestrator)
│   │   └── rag_service.py
│   └── observability/       # Langfuse integration
│       ├── __init__.py
│       ├── tracer.py                    # Base tracer interface
│       ├── mcp_tracer.py                # MCP tool tracer
│       ├── langfuse_tracer.py           # Langfuse implementation
│       └── langfuse_config.py           # Langfuse configuration
├── mcp/                     # MCP Server (FastAPI)
│   └── server.py
├── scripts/                 # Utility scripts
│   ├── run_server.py
│   ├── start_with_ngrok.sh
│   ├── post_mock_scores.py              # Mock evaluation scores
│   └── test_chat_10queries.sh           # Batch testing
├── tests/                   # Tests
│   ├── unit/
│   └── integration/
├── docs/                    # Documentation
│   ├── PROGRESSIVE_EXTRACTION.md
│   ├── OPENROUTER_QUICKSTART.md
│   ├── LANGFUSE_MOCK_SCORES.md
│   └── archive/
├── docker-compose.yml       # Qdrant setup
├── requirements.txt         # Base dependencies
├── requirements_progressive.txt  # VLM dependencies
├── .env.example             # Environment template
└── README.md
```

### Key Design Patterns
- **Clean Architecture**: Separation of layers (observability, models, core, services, api)
- **2-Tier Progressive Strategy**: Cost-optimized document extraction (Docling → Gemini Pro)
- **Dependency Injection**: Services receive dependencies via constructor
- **Lazy Loading**: Models load on first use with fallback mechanisms
- **Singleton Pattern**: Service and settings use singleton pattern
- **Repository Pattern**: VectorStore abstracts Qdrant operations
- **Observer Pattern**: Langfuse tracing throughout the stack

---

## 🔍 How Progressive Extraction & Hybrid Search Works

### Progressive Document Extraction (2-Tier Strategy)
```
User Upload PDF
    ↓
Tier 1: FAST (Docling - NO OCR)
├─ Cost: $0.00 (FREE)
├─ Time: ~5-10 seconds
├─ Quality Target: ≥ 0.70
└─ Works on: PDFs with text layer
    ↓ (if quality < 0.70 or empty)
Tier 3: PREMIUM (Gemini Pro VLM)
├─ Cost: $0.0013/page
├─ Time: ~60 seconds/page
├─ Quality Target: ≥ 0.95
└─ Works on: Scanned PDFs, complex documents, Thai language
    ↓
Quality Check (5 dimensions)
├─ text_quality (0.25 weight)
├─ word_quality (0.20 weight)
├─ consistency (0.15 weight)
├─ structure_quality (0.20 weight)
└─ content_density (0.20 weight)
    ↓
Auto Cost Tracking → Langfuse
```

**Note**: Tier 2 (Gemini Flash Free) is disabled due to rate limiting issues.

### Hybrid Search Pipeline
```
User Query
    ↓
1. Embedding (Dense + Sparse)
    ├─ Dense: BAAI/bge-m3 (1024-dim vector)
    └─ Sparse: BM25 (keyword matching)
    ↓
2. Parallel Search
    ├── Dense Search (Cosine Similarity)
    └── Sparse Search (BM25 Score)
    ↓
3. RRF Fusion (Reciprocal Rank Fusion)
    Formula: score(d) = Σ 1/(k + rank_i(d))
    ↓
4. Reranking (CrossEncoder)
    Model: BAAI/bge-reranker-v2-m3
    ↓
5. Deduplication (optional)
    ↓
6. Top-k Results → LLM Context
    ↓
7. Answer Generation (OpenRouter)
    ↓
8. Full Trace → Langfuse Dashboard
```

---

## 🛠️ Development

### Project Structure
```
src/
  config/     - Configuration management
  utils/      - Shared utilities
  models/     - ML model wrappers
  core/       - Business logic
  services/   - High-level orchestration
mcp/          - API layer
tests/        - Test suites
```

### Adding New Features

#### 1. Add a new model wrapper
```python
# src/models/your_model.py
class YourModel:
    def __init__(self, config):
        self.config = config
        self._model = None
    
    def _load(self):
        # Lazy loading logic
        pass
```

#### 2. Add a new core module
```python
# src/core/your_module.py
class YourModule:
    def __init__(self, dependencies):
        self.deps = dependencies
    
    def process(self, data):
        # Business logic
        pass
```

#### 3. Add a new API endpoint
```python
# mcp/server.py
@app.post("/tools/your_tool")
async def your_tool(request: YourRequest):
    service = get_service()
    result = service.your_method(...)
    return JSONResponse(content=result)
```

---

## 🧪 Testing

### Run All Tests
```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python tests/integration/test_core_workflow.py
python tests/integration/test_phase4.py
python tests/integration/test_rag_service.py

# MCP Server tests (requires running server)
python tests/integration/test_mcp_server.py
```

### Test Coverage
- ✅ Model wrappers (embeddings, reranker, llm)
- ✅ Core modules (collection, document, progressive extraction, metadata, vector store)
- ✅ Advanced modules (retriever, router, chat engine)
- ✅ Service layer (RAG orchestrator with VLM cost tracking)
- ✅ MCP Server (13 API endpoints)
- ✅ Observability (Langfuse tracing, cost tracking)
- ✅ Quality scoring (5-dimension extraction quality)

### Test Scripts
```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python tests/integration/test_core_workflow.py
python tests/integration/test_phase4.py
python tests/integration/test_rag_service.py
python tests/integration/test_mcp_server.py

# Full system test
python tests/full_system_test.py

# Batch chat testing (10 queries)
bash scripts/test_chat_10queries.sh

# Mock evaluation scores (Langfuse)
python scripts/post_mock_scores.py
```

---

## 🚀 Deployment

### Docker Deployment
```bash
# Build image
docker build -t mcp-rag-v2 .

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Environment-specific Settings
```bash
# Development
export ENV=development

# Production
export ENV=production
export OPENAI_API_KEY=your-prod-key
export QDRANT_HOST=qdrant.production.internal
```

### Production Checklist
- [ ] Set strong `OPENROUTER_API_KEY`
- [ ] Configure Langfuse for observability
- [ ] Configure Qdrant persistence volume
- [ ] Set up logging aggregation
- [ ] Enable HTTPS/TLS
- [ ] Configure rate limiting
- [ ] Set up monitoring (health checks + Langfuse)
- [ ] Configure backup strategy
- [ ] Review security settings
- [ ] Set VLM extraction tier strategy (cost vs quality)
- [ ] Configure ngrok for external access (optional)

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Qdrant Connection Error
```
Error: [Errno 61] Connection refused
```
**Solution**: Start Qdrant with `docker-compose up -d`

#### 2. VLM Extraction Failed
```
Error: OpenRouter API rate limit exceeded
```
**Solutions**:
- System automatically escalates from Tier 1 (Docling) to Tier 3 (Premium)
- Tier 2 (Gemini Flash Free) is currently disabled due to rate limiting
- Add credits to OpenRouter account for premium tier
- Lower target quality to use Tier 1 (Docling) more often

#### 3. Embedding Model Not Found
```
Model BAAI/bge-m3 is not supported
```
**Solution**: The system uses fallback embeddings. For production, install compatible fastembed version or use different model.

#### 4. Import Errors
```
ImportError: cannot import name 'RAGService'
```
**Solution**: Ensure PYTHONPATH includes project root:
```bash
export PYTHONPATH=/path/to/mcp_rag_v2:$PYTHONPATH
```

#### 5. Langfuse Connection Failed
```
Error: Failed to connect to Langfuse
```
**Solutions**:
- Check LANGFUSE_HOST is correct
- Verify LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
- Ensure Langfuse server is running
- Set LANGFUSE_ENABLED=false to disable if not needed

#### 6. VLM Cost Shows $0.00
```
Warning: VLM cost tracking returned None
```
**Solution**: Ensure OpenRouter API response includes `usage.total_cost` field. System now extracts actual costs from API.

#### 7. Latency Shows 0 Seconds
```
Warning: Trace latency is 0s
```
**Solution**: Ensure Langfuse generation lifecycle is correct (start_generation → tool execution → end). Fixed in v2.1.

---

## 📝 Configuration Reference

### VLM Extraction Settings
- `ENABLE_PROGRESSIVE_EXTRACTION` (default: true) - Enable 2-tier extraction
- `TARGET_QUALITY` (default: 0.70) - Minimum acceptable quality score
- `IMAGE_DPI` (default: 200) - DPI for PDF to image conversion
- `OPENROUTER_VLM_MODEL_PREMIUM` (default: google/gemini-2.5-pro)

**Note**: Tier 2 (Balanced/Free) is disabled. Only Tier 1 (Docling) and Tier 3 (Premium) are active.

### Search Settings
- `SEARCH_TOP_K` (default: 5) - Number of final results
- `SEARCH_LIMIT_MULTIPLIER` (default: 2) - Search multiplier for RRF input
- `SEARCH_RRF_K` (default: 60) - RRF constant
- `RERANK_THRESHOLD` (default: 0.0) - Minimum reranking score

### Document Settings
- `CHUNK_SIZE` (default: 1000) - Characters per chunk
- `CHUNK_OVERLAP` (default: 200) - Overlap between chunks
- `MAX_FILE_SIZE_MB` (default: 50) - Maximum upload size

### Chat Settings
- `MEMORY_TOKEN_LIMIT` (default: 3000) - Max conversation history tokens
- `SYSTEM_PROMPT` - Default system prompt for LLM

### Langfuse Settings
- `LANGFUSE_ENABLED` (default: false) - Enable observability
- `LANGFUSE_HOST` - Langfuse server URL
- `LANGFUSE_PUBLIC_KEY` - Public API key
- `LANGFUSE_SECRET_KEY` - Secret API key
- `LANGFUSE_PROJECT` - Project name
- `LANGFUSE_ENVIRONMENT` - Environment (development/production)

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- **Qdrant** - Vector database with hybrid search support
- **OpenRouter** - Universal LLM API gateway
- **Langfuse** - Open-source LLM observability platform
- **Docling** - Document layout analysis and extraction
- **FastEmbed** - Fast embedding models
- **Sentence Transformers** - Reranking models
- **FastAPI** - Modern async web framework
- **Google Gemini** - Vision language models

---

## 📧 Contact

- GitHub: [@Pond500](https://github.com/Pond500)
- Repository: [rag-mcp-server](https://github.com/Pond500/rag-mcp-server)

---

## 🗺️ Roadmap

### v2.1 (Current) ✅
- [x] Progressive VLM extraction (2-tier strategy: Docling → Gemini Pro)
- [x] Langfuse observability integration
- [x] Actual VLM cost tracking from OpenRouter API
- [x] 5-dimension quality scoring
- [x] Latency tracking for all operations
- [x] Mock evaluation score generation
- [x] Batch testing scripts
- [x] 13 MCP tools + REST endpoints
- [x] Tier 2 (Free VLM) disabled due to rate limiting

### v2.2 (Planned)
- [ ] Schema-based document normalization
- [ ] Smart chunking (structure-aware)
- [ ] Multi-modal support (images, tables extraction)
- [ ] Advanced caching strategies
- [ ] Streaming responses
- [ ] Batch processing API
- [ ] Multi-language support (Thai optimization)
- [ ] Real-time evaluation with RAGAS
- [ ] Cost optimization dashboard

### v3.0 (Future)
- [ ] GraphRAG integration
- [ ] Advanced query rewriting
- [ ] Agentic RAG workflows
- [ ] Custom evaluation metrics UI
- [ ] A/B testing framework
- [ ] Multi-tenant support

---

## 📊 Performance Metrics

### Extraction Performance (v2.1)
| Tier | PDF Type | Pages | Time | Cost | Quality |
|------|----------|-------|------|------|---------|
| Fast | Text PDF | 6 | ~9s | $0.00 | 0.75-0.85 |
| Premium | Scanned/Complex | 6 | ~360s | $0.0078 | 0.90-0.97 |

**Note**: Tier 2 (Balanced/Gemini Flash Free) has been disabled due to rate limiting.

### Search Performance
- **Hybrid Search**: ~100-200ms per query (5 results)
- **With Reranking**: ~200-300ms per query
- **Chat (RAG)**: ~1-2s per response (including LLM)

### Cost Optimization
- **90% of documents**: Processed with FREE tier (Docling)
- **10% of documents**: Use premium tier for scanned/complex PDFs
- **Average cost**: $0.0003/page (80% savings vs direct VLM)
- **Tier 2 disabled**: Gemini Flash Free VLM disabled due to rate limiting

---

**Built with ❤️ for production RAG systems**

**Version 2.1.0** | Last Updated: January 6, 2026
