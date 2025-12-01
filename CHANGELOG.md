# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2025-11-28

### 🎉 Major Release - Complete Refactoring

This release represents a complete architectural refactoring from the monolithic v1 codebase to a clean, modular, production-ready system.

### Added

#### Architecture
- ✨ **Clean Architecture** - Separated concerns: config, utils, models, core, services, mcp
- 🔌 **Lazy Loading** - Models load on-demand with automatic fallback mechanisms
- ⚙️ **Type-Safe Configuration** - Pydantic Settings with environment variable support
- 📊 **Production Logging** - Colored console output with daily rotating file logs

#### Core Features
- 🎯 **Multi-KB Management** - Complete CRUD operations for knowledge bases
- 🔍 **Hybrid Search** - Dense (BAAI/bge-m3) + Sparse BM25 (Qdrant/bm25) fusion
- 🔀 **RRF Fusion** - Reciprocal Rank Fusion for optimal result merging
- 🎓 **Reranking** - CrossEncoder (BAAI/bge-reranker-v2-m3) for precision
- 🧭 **Semantic Routing** - Automatic KB selection via master index
- 💬 **Conversation History** - Session-based chat with context retention
- 📄 **Document Processing** - PDF, DOCX, TXT extraction and chunking
- 🤖 **Metadata Extraction** - AI-powered metadata generation

#### Models Layer
- `EmbeddingManager` - Unified interface for dense and sparse embeddings
- `Reranker` - CrossEncoder wrapper with fallback scoring
- `LLMClient` - OpenAI-compatible API wrapper

#### Core Layer
- `CollectionManager` - Qdrant collection CRUD operations
- `DocumentProcessor` - Multi-format text extraction and chunking
- `MetadataExtractor` - LLM-based metadata extraction
- `VectorStore` - Qdrant operations abstraction
- `Retriever` - Hybrid Search orchestration with RRF and reranking
- `Router` - Semantic KB selection with master index
- `ChatEngine` - LLM chat with conversation memory

#### Service Layer
- `RAGService` - High-level orchestrator combining all components
- Complete API: create_kb, delete_kb, list_kbs, upload_document, search, chat, clear_history, health_check

#### MCP Server
- 🚀 **FastAPI Application** - 8 MCP tools via REST API
- 📚 **OpenAPI Docs** - Auto-generated API documentation at `/docs`
- 🛡️ **Error Handling** - Proper HTTP status codes and error messages
- 🔄 **Lifecycle Hooks** - Startup/shutdown event handlers

#### Testing
- ✅ Unit tests for model wrappers
- ✅ Integration tests for core workflow
- ✅ Integration tests for Phase 4 modules
- ✅ Integration tests for RAG Service
- ✅ HTTP tests for MCP Server

#### Documentation
- 📖 Comprehensive README.md with usage examples
- 📋 API documentation for all endpoints
- 🏗️ Architecture diagrams and explanations
- 🔧 Troubleshooting guide
- 🚀 Deployment instructions

### Changed

#### From v1.x (Legacy)
- **Refactored**: Monolithic 800+ line file → Modular architecture
- **Improved**: Better error handling and logging
- **Enhanced**: Type safety with Pydantic throughout
- **Optimized**: Lazy loading reduces startup time
- **Simplified**: Configuration management with Settings classes

#### Breaking Changes
- API endpoints changed to `/tools/*` format
- Configuration moved from hardcoded values to environment variables
- Service initialization requires `RAGService.from_settings()`
- Session-based chat replaces stateless conversations

### Fixed
- ✅ Sparse vector format compatibility with Qdrant
- ✅ Named vector handling for Hybrid Search
- ✅ Collection existence checking
- ✅ Metadata point handling in collections
- ✅ RRF fusion algorithm (correct k=60 pattern)

### Removed
- ❌ Monolithic code structure
- ❌ Hardcoded configuration values
- ❌ Global state management
- ❌ Direct model imports in API layer

### Security
- 🔒 Environment-based secrets management
- 🔒 No hardcoded API keys
- 🔒 Proper request validation with Pydantic

### Performance
- ⚡ Lazy loading reduces initial memory footprint
- ⚡ Batch upsert for document processing
- ⚡ Connection pooling for Qdrant
- ⚡ Efficient RRF implementation

### Technical Debt Resolved
- 🧹 Removed code duplication
- 🧹 Improved testability with dependency injection
- 🧹 Consistent error handling patterns
- 🧹 Proper separation of concerns

---

## [1.x] - 2025-11-27 and earlier

### Legacy Version (Preserved)

The v1.x codebase has been preserved in `/legacy/` for reference. Key features:
- Multi-KB RAG with Hybrid Search (working implementation)
- MCP server with 8 tools
- Gun law test data (16 files, 28 points)
- Original monolithic architecture

See `legacy/README_LEGACY.md` for details.

---

## Migration Guide: v1.x → v2.0

### Code Changes

**Before (v1.x):**
```python
from app.multi_kb_rag import MultiKBRAG

rag = MultiKBRAG()
result = rag.create_kb("my_kb", "Description")
```

**After (v2.0):**
```python
from src.config import get_settings
from src.services import RAGService

settings = get_settings()
service = RAGService.from_settings(settings)
result = service.create_kb("my_kb", "Description", "general")
```

### Configuration Changes

**Before**: Hardcoded in code
**After**: Environment variables in `.env`

### API Changes

**Before**: `/create_kb`, `/chat`, etc.
**After**: `/tools/create_kb`, `/tools/chat`, etc.

---

## Future Roadmap

### v2.1.0 (Planned)
- [ ] Streaming response support
- [ ] Batch processing API
- [ ] Advanced caching layer
- [ ] Metrics and monitoring

### v2.2.0 (Planned)
- [ ] Multi-modal support (images, tables)
- [ ] GraphRAG integration
- [ ] Multi-language support
- [ ] Query rewriting improvements

### v3.0.0 (Future)
- [ ] Distributed architecture
- [ ] Kubernetes deployment
- [ ] Advanced observability
- [ ] Plugin system

---

## Contributors

- **Pond500** - Initial work and v2.0 refactoring

---

## Acknowledgments

Special thanks to:
- Original v1.x implementation for proving the concept
- Qdrant team for sparse vector support
- FastAPI and Pydantic communities
- Open source ML model creators

---

**Legend:**
- 🎉 Major feature
- ✨ New feature
- 🔀 Changed
- 🐛 Bug fix
- 🔒 Security
- ⚡ Performance
- 📖 Documentation
- 🧪 Testing
