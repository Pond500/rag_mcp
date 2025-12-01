# Multi-KB RAG System v2.0 with Hybrid Search

**Production-ready Multi-Knowledge Base RAG system** with Hybrid Search (Dense + Sparse BM25), RRF fusion, Reranking, and Semantic Routing via Model Context Protocol (MCP).

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 🌟 Features

### Core Capabilities
- 🎯 **Multi-KB Management** - Manage multiple independent knowledge bases
- 🔍 **Hybrid Search** - Dense vector (BAAI/bge-m3) + Sparse BM25 (Qdrant/bm25)
- 🔀 **RRF Fusion** - Reciprocal Rank Fusion for optimal result merging
- 🎓 **Reranking** - CrossEncoder (BAAI/bge-reranker-v2-m3) for precision
- 🧭 **Semantic Routing** - Automatic KB selection based on query semantics
- 💬 **Conversation History** - Session-based chat with context retention
- 📄 **Multi-format Support** - PDF, DOCX, TXT document processing
- 🤖 **LLM Integration** - OpenAI-compatible API for answer generation

### Architecture Highlights
- ✨ **Clean Architecture** - Separation of concerns (config, models, core, services, mcp)
- 🔌 **Lazy Loading** - Models load on-demand with fallback mechanisms
- ⚙️ **Type-Safe Config** - Pydantic Settings with environment variable support
- 📊 **Production Logging** - Colored console + rotating file logs
- 🧪 **Comprehensive Tests** - Unit and integration tests for all layers
- 🚀 **MCP Protocol** - FastAPI server with 8 MCP tools

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
- OpenAI-compatible LLM API (optional)

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/mcp_rag_v2.git
cd mcp_rag_v2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Qdrant
```bash
docker-compose up -d
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings (LLM API key, etc.)
```

### 4. Run Server
```bash
python scripts/run_server.py
# Or: uvicorn mcp.server:app --reload
```

### 5. Access API
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/tools/health

---

## 📦 Installation

### Option 1: Standard Installation
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start Qdrant
docker-compose up -d

# Verify installation
python test_config.py
```

### Option 2: Development Installation
```bash
# Install with dev dependencies
pip install -r requirements.txt

# Install pre-commit hooks (if available)
# pre-commit install

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

# LLM Settings
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

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

# 2. Upload Document
with open("policy.pdf", "rb") as f:
    result = service.upload_document(
        kb_name="company_docs",
        filename="policy.pdf",
        file_content=f.read()
    )

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
  "category": "general" | "firearms" | "contracts" | etc.
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

#### 4. `POST /tools/upload_document`
Upload document (multipart/form-data)
- `kb_name`: string
- `file`: file (PDF, DOCX, TXT)

#### 5. `POST /tools/search`
Search with Hybrid Search
```json
{
  "query": "string",
  "kb_name": "string" | null,
  "top_k": 5,
  "use_routing": true,
  "use_reranking": true
}
```

#### 6. `POST /tools/chat`
Chat with RAG
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

#### 7. `POST /tools/clear_history`
Clear conversation history
```json
{
  "session_id": "string"
}
```

#### 8. `GET /tools/health`
Health check

---

## 🏗️ Architecture

```
mcp_rag_v2/
├── src/
│   ├── config/          # Configuration (Pydantic Settings + YAML prompts)
│   │   ├── settings.py
│   │   └── prompts.yaml
│   ├── utils/           # Utilities (logging, helpers)
│   │   └── logger.py
│   ├── models/          # Model wrappers (embeddings, reranker, llm)
│   │   ├── embeddings.py
│   │   ├── reranker.py
│   │   └── llm.py
│   ├── core/            # Core business logic
│   │   ├── collection_manager.py   # KB CRUD
│   │   ├── document_processor.py   # Text extraction & chunking
│   │   ├── metadata_extractor.py   # AI metadata extraction
│   │   ├── vector_store.py         # Qdrant operations
│   │   ├── retriever.py            # Hybrid Search + RRF + Reranking
│   │   ├── router.py               # Semantic routing
│   │   └── chat_engine.py          # LLM chat with history
│   └── services/        # Service layer (RAG orchestrator)
│       └── rag_service.py
├── mcp/                 # MCP Server (FastAPI)
│   └── server.py
├── tests/               # Tests
│   ├── unit/
│   └── integration/
├── scripts/             # Utility scripts
│   └── run_server.py
├── docker-compose.yml   # Qdrant setup
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
└── README.md
```

### Design Patterns
- **Clean Architecture**: Separation of layers (models, core, services, api)
- **Dependency Injection**: Services receive dependencies via constructor
- **Lazy Loading**: Models load on first use with fallback mechanisms
- **Singleton Pattern**: Service and settings use singleton pattern
- **Repository Pattern**: VectorStore abstracts Qdrant operations

---

## 🔍 How Hybrid Search Works

```
User Query
    ↓
1. Embedding (Dense + Sparse)
    ↓
2. Parallel Search
    ├── Dense Search (Cosine Similarity)
    └── Sparse Search (BM25)
    ↓
3. RRF Fusion (Reciprocal Rank Fusion)
    Formula: score(d) = Σ 1/(k + rank_i(d))
    ↓
4. Reranking (CrossEncoder)
    ↓
5. Top-k Results → LLM Context
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
- ✅ Core modules (collection, document, metadata, vector store)
- ✅ Advanced modules (retriever, router, chat engine)
- ✅ Service layer (RAG orchestrator)
- ✅ MCP Server (API endpoints)

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
- [ ] Set strong `OPENAI_API_KEY`
- [ ] Configure Qdrant persistence volume
- [ ] Set up logging aggregation
- [ ] Enable HTTPS/TLS
- [ ] Configure rate limiting
- [ ] Set up monitoring (health checks)
- [ ] Configure backup strategy
- [ ] Review security settings

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Qdrant Connection Error
```
Error: [Errno 61] Connection refused
```
**Solution**: Start Qdrant with `docker-compose up -d`

#### 2. Embedding Model Not Found
```
Model BAAI/bge-m3 is not supported
```
**Solution**: The system uses fallback embeddings. For production, install compatible fastembed version or use different model.

#### 3. Import Errors
```
ImportError: cannot import name 'RAGService'
```
**Solution**: Ensure PYTHONPATH includes project root:
```bash
export PYTHONPATH=/path/to/mcp_rag_v2:$PYTHONPATH
```

#### 4. Master Index Not Found
```
Collection 'master_index' doesn't exist
```
**Solution**: Master index is created automatically when first KB is created with routing enabled.

---

## 📝 Configuration Reference

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

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- **Qdrant** - Vector database with sparse vector support
- **FastEmbed** - Fast embedding models
- **Sentence Transformers** - Reranking models
- **FastAPI** - Modern web framework
- **OpenAI** - LLM API

---

## 📧 Contact

- GitHub: [@Pond500](https://github.com/Pond500)
- Repository: [rag-mcp-server](https://github.com/Pond500/rag-mcp-server)

---

## 🗺️ Roadmap

- [ ] Multi-modal support (images, tables)
- [ ] Advanced caching strategies
- [ ] Streaming responses
- [ ] Batch processing API
- [ ] Metrics and monitoring dashboard
- [ ] Multi-language support
- [ ] GraphRAG integration
- [ ] Advanced query rewriting

---

**Built with ❤️ for production RAG systems**
