# MCP RAG v2.0 - Project Structure

## 📁 Directory Overview (After Cleanup)

```
mcp_rag_v2/
├── 📄 .env                    # Environment configuration
├── 📄 .gitignore              # Git ignore patterns
├── 📄 docker-compose.yml      # Qdrant container setup
├── 📄 Makefile                # Build/run commands
├── 📄 requirements.txt        # Python dependencies
├── 📄 requirements_progressive.txt  # VLM dependencies
│
├── 📁 mcp/                    # MCP Server (Main Entry Point)
│   ├── __init__.py
│   └── server.py              # FastAPI server with MCP tools
│
├── 📁 src/                    # Source Code
│   ├── __init__.py
│   ├── config/                # Configuration
│   │   ├── __init__.py
│   │   ├── settings.py        # Pydantic settings (main config)
│   │   └── prompts.yaml       # Prompt templates
│   │
│   ├── core/                  # Core Business Logic
│   │   ├── __init__.py
│   │   ├── document_processor.py      # Docling + OCR extraction
│   │   ├── progressive_processor.py   # VLM-based extraction (Gemini)
│   │   ├── openrouter_extractor.py    # OpenRouter VLM API
│   │   ├── quality_checker.py         # Extraction quality scoring
│   │   ├── collection_manager.py      # KB management
│   │   ├── vector_store.py            # Qdrant operations
│   │   ├── retriever.py               # Hybrid search + reranking
│   │   ├── chat_engine.py             # RAG chat with history
│   │   ├── metadata_extractor.py      # Auto metadata extraction
│   │   └── router.py                  # Query routing
│   │
│   ├── models/                # ML Models
│   │   ├── __init__.py
│   │   ├── embeddings.py      # BGE-M3 embeddings
│   │   ├── reranker.py        # BGE Reranker
│   │   └── llm.py             # LLM client
│   │
│   ├── services/              # Business Services
│   │   ├── __init__.py
│   │   └── rag_service.py     # Main RAG orchestration
│   │
│   └── utils/                 # Utilities
│       ├── __init__.py
│       ├── logger.py          # Logging configuration
│       ├── text_cleaner.py    # Text cleaning utilities
│       └── document_validator.py  # Document validation
│
├── 📁 web/                    # Web Interface (Optional)
│   ├── app.py                 # Streamlit/Flask web app
│   └── templates/
│
├── 📁 scripts/                # Utility Scripts
│   ├── start_server.sh        # Start MCP server
│   ├── start_with_ngrok.sh    # Start with ngrok tunnel
│   ├── stop_server.sh         # Stop server
│   ├── health_check.sh        # Health check
│   └── setup.sh               # Initial setup
│
├── 📁 tests/                  # Test Suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── full_system_test.py    # E2E tests
│
├── 📁 docs/                   # Documentation
│   ├── PROGRESSIVE_EXTRACTION.md
│   ├── OPENROUTER_QUICKSTART.md
│   └── ...
│
├── 📁 examples/               # Usage Examples
│   ├── docling_usage_example.py
│   ├── pipeline_usage.py
│   └── progressive_extraction_demo.py
│
├── 📁 logs/                   # Log files (git ignored)
├── 📁 uploads/                # Temp uploads (git ignored)
├── 📁 data/                   # Test data (git ignored)
└── 📁 qdrant_storage/         # Qdrant data (git ignored)
```

## 🔧 Key Files

| File | Purpose |
|------|---------|
| `mcp/server.py` | Main entry point - FastAPI MCP server |
| `src/services/rag_service.py` | Core RAG orchestration |
| `src/core/document_processor.py` | Docling + OCR extraction |
| `src/core/progressive_processor.py` | VLM extraction (Gemini) |
| `src/config/settings.py` | All configuration settings |

## 🚀 Quick Start

```bash
# Start server
make run
# or
bash scripts/start_server.sh

# Start with ngrok
bash scripts/start_with_ngrok.sh

# Health check
curl http://localhost:8000/tools/health
```

## 📦 Removed (Cleanup Dec 2024)

The following were removed as duplicates or unused:
- `config/` → Use `src/config/` instead
- `utils/` → Use `src/utils/` instead  
- `src/schemas/` → Not used in current implementation
- `output/` → Empty folder
- `test_config.py`, `test_hybrid_mode.py` → Root level test files

## 🔄 Document Processing Flow

```
PDF Upload → DocumentProcessor (Docling/OCR)
         ↓
   [If quality < threshold]
         ↓
ProgressiveProcessor (VLM - Gemini Pro)
         ↓
Chunking (Markdown-aware, semantic)
         ↓
Embedding (BGE-M3 + BM25)
         ↓
Qdrant Storage (Hybrid vectors)
```
