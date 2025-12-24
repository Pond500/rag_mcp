"""RAG Service - High-level orchestrator

Combines all components to provide complete RAG functionality:
- KB management (create, delete, list)
- Document upload and processing
- Chat with retrieval
- Search
- Routing
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

from qdrant_client import QdrantClient
from src.config import Settings
from src.models import EmbeddingManager, Reranker, LLMClient
from src.core import (
    CollectionManager,
    DocumentProcessor,
    MetadataExtractor,
    VectorStore,
    Retriever,
    Router,
    ChatEngine
)
from src.core.progressive_processor import ProgressiveDocumentProcessor

logger = logging.getLogger(__name__)


class RAGService:
    """High-level RAG service orchestrator
    
    Usage:
        service = RAGService.from_settings(settings)
        
        # Create KB
        service.create_kb("gun_law", "กฎหมายอาวุธปืน")
        
        # Upload document
        service.upload_document("gun_law", "doc.pdf", file_content)
        
        # Chat
        response = service.chat("อาวุธปืนต้องขออนุญาตไหม", kb_name="gun_law")
    """
    
    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_manager: EmbeddingManager,
        reranker: Reranker,
        llm_client: LLMClient,
        config: Settings
    ):
        self.config = config
        
        # Core modules
        self.collection_mgr = CollectionManager(qdrant_client, config)
        
        # Use ProgressiveDocumentProcessor if OpenRouter is configured, otherwise fallback to basic DocumentProcessor
        if config.openrouter.use_progressive and config.openrouter.api_key:
            logger.info("Using ProgressiveDocumentProcessor with OpenRouter VLM")
            self.doc_processor = ProgressiveDocumentProcessor(
                openrouter_api_key=config.openrouter.api_key,
                enable_fast_tier=True,
                enable_balanced_tier=False,  # Skip Gemini Free, go straight to Premium
                enable_premium_tier=True,
                disable_ocr=True  # Use VLM instead of Tesseract
            )
            self.target_quality = config.openrouter.target_quality
        else:
            # Get OCR setting from config.docling (default: True)
            enable_ocr = getattr(config, 'docling', None) and getattr(config.docling, 'enable_ocr', True)
            logger.info(f"Using basic DocumentProcessor (OCR: {'ON' if enable_ocr else 'OFF'})")
            self.doc_processor = DocumentProcessor(config.document, enable_ocr=enable_ocr)
        
        self.metadata_extractor = MetadataExtractor(llm_client, config.chat.system_prompt)
        self.vector_store = VectorStore(qdrant_client, embedding_manager)
        
        # Advanced modules
        self.retriever = Retriever(
            self.vector_store,
            embedding_manager,
            reranker,
            config.search
        )
        self.router = Router(
            self.vector_store,
            embedding_manager,
            master_collection="master_index"
        )
        self.chat_engine = ChatEngine(llm_client, config.chat)
        
        # State
        self._embedding_manager = embedding_manager
        self._qdrant_client = qdrant_client
        
        logger.info("RAG Service initialized")
    
    @classmethod
    def from_settings(cls, settings: Settings) -> "RAGService":
        """Create RAG service from settings"""
        # Initialize clients
        qdrant_client = QdrantClient(
            host=settings.qdrant.host,
            port=settings.qdrant.port,
            timeout=settings.qdrant.timeout
        )
        
        embedding_manager = EmbeddingManager(settings)
        reranker = Reranker(settings.reranker)
        llm_client = LLMClient(
            api_key=settings.llm.api_key,
            model_name=settings.llm.model_name,
            base_url=settings.llm.base_url
        )
        
        return cls(
            qdrant_client=qdrant_client,
            embedding_manager=embedding_manager,
            reranker=reranker,
            llm_client=llm_client,
            config=settings
        )
    
    # ========================
    # KB Management
    # ========================
    
    def create_kb(
        self,
        kb_name: str,
        description: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """Create a new knowledge base
        
        Args:
            kb_name: Name of KB (alphanumeric, underscore, hyphen)
            description: Description for semantic routing
            category: Category (e.g., "firearms", "contracts")
            
        Returns:
            {"success": bool, "kb_name": "...", "message": "..."}
        """
        try:
            # Get actual embedding dimension
            test_embed = self._embedding_manager.embed_dense(["test"])[0]
            dense_size = len(test_embed)
            
            # Create collection
            result = self.collection_mgr.create_collection(
                kb_name=kb_name,
                description=description,
                dense_size=dense_size
            )
            
            if not result["success"]:
                return result
            
            # Add to master index (for routing)
            self.router.add_kb_to_master(
                kb_name=kb_name,
                description=description,
                category=category
            )
            
            logger.info("Created KB: %s (%s)", kb_name, category)
            
            return {
                "success": True,
                "kb_name": kb_name,
                "message": f"Knowledge base '{kb_name}' created successfully"
            }
            
        except Exception as e:
            logger.error("Failed to create KB: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    def delete_kb(self, kb_name: str) -> Dict[str, Any]:
        """Delete a knowledge base
        
        Args:
            kb_name: Name of KB to delete
            
        Returns:
            {"success": bool, "message": "..."}
        """
        try:
            # Delete collection
            result = self.collection_mgr.delete_collection(kb_name)
            
            if result["success"]:
                # Remove from master index
                self.router.remove_kb_from_master(kb_name)
                
                logger.info("Deleted KB: %s", kb_name)
                return {
                    "success": True,
                    "message": f"Knowledge base '{kb_name}' deleted successfully"
                }
            else:
                return result
                
        except Exception as e:
            logger.error("Failed to delete KB: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    def list_kbs(self) -> Dict[str, Any]:
        """List all knowledge bases
        
        Returns:
            {"success": bool, "kbs": [...], "total": N}
        """
        try:
            # Get from collection manager
            collections_result = self.collection_mgr.list_collections()
            
            if not collections_result["success"]:
                return collections_result
            
            # Enrich with master index info
            master_kbs = {kb["kb_name"]: kb for kb in self.router.list_kbs()}
            
            kbs = []
            for col in collections_result["collections"]:
                kb_name = col["kb_name"]
                master_info = master_kbs.get(kb_name, {})
                
                kbs.append({
                    "kb_name": kb_name,
                    "description": col.get("description", master_info.get("description", "")),
                    "category": master_info.get("category", "general"),
                    "document_count": col.get("document_count", 0),
                    "points_count": col.get("points_count", 0)
                })
            
            return {
                "success": True,
                "kbs": kbs,
                "total": len(kbs)
            }
            
        except Exception as e:
            logger.error("Failed to list KBs: %s", e)
            return {
                "success": False,
                "message": str(e),
                "kbs": [],
                "total": 0
            }
    
    def get_kb_info(self, kb_name: str) -> Dict[str, Any]:
        """Get detailed info about a KB
        
        Args:
            kb_name: Name of KB
            
        Returns:
            {"success": bool, "kb_name": "...", "points_count": N, ...}
        """
        try:
            return self.collection_mgr.get_collection_info(kb_name)
        except Exception as e:
            logger.error("Failed to get KB info: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    # ========================
    # Document Management
    # ========================
    
    def upload_document(
        self,
        kb_name: str,
        filename: str,
        file_content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload and process a document
        
        Args:
            kb_name: Target KB
            filename: Original filename (for extension detection)
            file_content: Raw file bytes
            metadata: Optional additional metadata
            
        Returns:
            {"success": bool, "chunks_count": N, "point_ids": [...]}
        """
        try:
            # Check KB exists
            if not self.collection_mgr.collection_exists(kb_name):
                return {
                    "success": False,
                    "message": f"Knowledge base '{kb_name}' not found"
                }
            
            # Extract text (handle both Progressive and basic processors)
            extraction_metadata = {}
            file_ext = Path(filename).suffix.lower()
            
            # Progressive processor only works with PDFs
            # For other file types (txt, md, docx, xlsx), use basic processor
            use_progressive = (
                isinstance(self.doc_processor, ProgressiveDocumentProcessor) and 
                file_ext == '.pdf'
            )
            
            if use_progressive:
                # Use progressive extraction with VLM (PDF only)
                target_quality = getattr(self, 'target_quality', 0.70)
                logger.info(f"🚀 Using Progressive extraction for {filename} (target_quality={target_quality})")
                result = self.doc_processor.extract_with_smart_routing(
                    pdf_bytes=file_content,
                    target_quality=target_quality
                )
                if not result.success:
                    return {
                        "success": False,
                        "message": f"Failed to extract text: {result.error}"
                    }
                pages = result.pages
                extraction_metadata = {
                    "tier_used": result.tier_used,
                    "tier_attempted": result.tier_attempted,
                    "quality_score": result.quality_score,
                    "extraction_cost": result.cost,
                    "extraction_time": result.extraction_time
                }
                logger.info("Progressive extraction: %d pages, tier=%s, quality=%.2f, cost=$%.4f",
                          len(pages), result.tier_used, result.quality_score, result.cost)
            else:
                # Use basic extraction (for non-PDF files or when progressive is disabled)
                # If using ProgressiveDocumentProcessor, use its internal fast_processor for non-PDFs
                if isinstance(self.doc_processor, ProgressiveDocumentProcessor):
                    basic_processor = self.doc_processor.fast_processor
                    logger.info(f"🔄 Using basic extraction (non-PDF): {filename}")
                else:
                    basic_processor = self.doc_processor
                    logger.info(f"🔄 Starting basic extraction: {filename} ({len(file_content)} bytes), OCR={basic_processor.enable_ocr}")
                
                pages = basic_processor.extract_text(filename, file_content)
                logger.info("Basic extraction: %d pages from %s", len(pages), filename)
                
                # Debug: log first page preview if available
                if pages:
                    logger.info(f"📄 First page preview (100 chars): {pages[0][:100]}")
                else:
                    logger.error(f"❌ Extraction returned empty pages! File: {filename}")
            
            if not pages:
                logger.error(f"❌ No pages extracted from {filename}. Enable OCR if this is an image-based PDF.")
                return {
                    "success": False,
                    "message": "Failed to extract text from document"
                }
            
            # Chunk text
            chunks = self.doc_processor.chunk_text(pages)
            
            if not chunks:
                return {
                    "success": False,
                    "message": "Failed to chunk document"
                }
            
            logger.info("Created %d chunks from %s", len(chunks), filename)
            
            # Extract metadata from first chunk
            auto_metadata = self.metadata_extractor.extract(chunks[0]["text"])
            
            # Merge with provided metadata
            doc_metadata = {
                **auto_metadata,
                "kb_name": kb_name,
                "filename": filename,
                "upload_date": datetime.now().isoformat(),
                **extraction_metadata,  # Include progressive extraction metadata
                **(metadata or {})
            }
            
            # Prepare documents for upsert
            documents = []
            for chunk in chunks:
                documents.append({
                    "text": chunk["text"],
                    "metadata": {
                        **doc_metadata,
                        "page": chunk["page"],
                        "chunk_index": chunk["chunk_index"]
                    }
                })
            
            # Upsert to vector store
            collection_name = self.collection_mgr._get_collection_name(kb_name)
            result = self.vector_store.upsert_documents(
                collection_name=collection_name,
                documents=documents
            )
            
            if result["success"]:
                logger.info("Uploaded %s: %d chunks to %s",
                           filename, result["upserted_count"], kb_name)
                
                return {
                    "success": True,
                    "chunks_count": result["upserted_count"],
                    "chunks_created": result["upserted_count"],  # For Langfuse tracking
                    "point_ids": result["point_ids"],
                    "metadata": doc_metadata,
                    "message": f"Document uploaded successfully: {result['upserted_count']} chunks",
                    # VLM cost tracking for Langfuse
                    "document_name": filename,
                    "pages_processed": len(pages),
                    "vlm_cost": extraction_metadata.get("extraction_cost", 0.0)
                }
            else:
                return result
                
        except Exception as e:
            logger.error("Failed to upload document: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    def list_documents(
        self,
        kb_name: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List all documents in a KB
        
        Args:
            kb_name: Knowledge base name
            limit: Max number of documents to return
            offset: Pagination offset
            
        Returns:
            {"success": bool, "documents": [...], "total": int}
        """
        try:
            if not self.collection_mgr.collection_exists(kb_name):
                return {
                    "success": False,
                    "message": f"Knowledge base '{kb_name}' not found",
                    "documents": [],
                    "total": 0
                }
            
            collection_name = self.collection_mgr._get_collection_name(kb_name)
            
            # Use scroll to get all documents
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Get unique filenames
            all_points, _ = self._qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="_type",
                            match=MatchValue(value="document")
                        )
                    ]
                ),
                limit=10000,  # Get all for counting
                with_payload=True,
                with_vectors=False
            )
            
            # Group by filename
            docs_by_file = {}
            for point in all_points:
                filename = point.payload.get("filename", "unknown")
                if filename not in docs_by_file:
                    docs_by_file[filename] = {
                        "filename": filename,
                        "chunks_count": 0,
                        "upload_date": point.payload.get("upload_date", ""),
                        "point_ids": [],
                        "tier_used": point.payload.get("tier_used", "basic"),
                        "quality_score": point.payload.get("quality_score"),
                    }
                docs_by_file[filename]["chunks_count"] += 1
                docs_by_file[filename]["point_ids"].append(point.id)
            
            # Convert to list and apply pagination
            documents = list(docs_by_file.values())
            total = len(documents)
            
            # Sort by upload_date descending
            documents.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
            
            # Apply pagination
            paginated = documents[offset:offset + limit]
            
            logger.info("Listed %d documents in %s (total: %d)", len(paginated), kb_name, total)
            
            return {
                "success": True,
                "kb_name": kb_name,
                "documents": paginated,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error("Failed to list documents: %s", e)
            return {
                "success": False,
                "message": str(e),
                "documents": [],
                "total": 0
            }
    
    def get_document(
        self,
        kb_name: str,
        filename: str,
        include_chunks: bool = False
    ) -> Dict[str, Any]:
        """Get document info and optionally its chunks
        
        Args:
            kb_name: Knowledge base name
            filename: Document filename
            include_chunks: Whether to include chunk contents
            
        Returns:
            {"success": bool, "document": {...}, "chunks": [...]}
        """
        try:
            if not self.collection_mgr.collection_exists(kb_name):
                return {
                    "success": False,
                    "message": f"Knowledge base '{kb_name}' not found"
                }
            
            collection_name = self.collection_mgr._get_collection_name(kb_name)
            
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Get all points for this filename
            points, _ = self._qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="filename",
                            match=MatchValue(value=filename)
                        )
                    ]
                ),
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            
            if not points:
                return {
                    "success": False,
                    "message": f"Document '{filename}' not found in KB '{kb_name}'"
                }
            
            # Build document info from first chunk metadata
            first_point = points[0]
            document = {
                "filename": filename,
                "kb_name": kb_name,
                "chunks_count": len(points),
                "upload_date": first_point.payload.get("upload_date", ""),
                "tier_used": first_point.payload.get("tier_used", "basic"),
                "quality_score": first_point.payload.get("quality_score"),
                "extraction_cost": first_point.payload.get("extraction_cost"),
                "point_ids": [p.id for p in points]
            }
            
            result = {
                "success": True,
                "document": document
            }
            
            # Optionally include chunk contents
            if include_chunks:
                chunks = []
                for point in sorted(points, key=lambda x: x.payload.get("chunk_index", 0)):
                    chunks.append({
                        "chunk_index": point.payload.get("chunk_index", 0),
                        "page": point.payload.get("page", 1),
                        "text": point.payload.get("text", ""),
                        "point_id": point.id
                    })
                result["chunks"] = chunks
            
            logger.info("Got document info: %s in %s (%d chunks)", filename, kb_name, len(points))
            
            return result
            
        except Exception as e:
            logger.error("Failed to get document: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    def delete_document(
        self,
        kb_name: str,
        filename: str
    ) -> Dict[str, Any]:
        """Delete a document from KB
        
        Args:
            kb_name: Knowledge base name
            filename: Document filename to delete
            
        Returns:
            {"success": bool, "deleted_chunks": int}
        """
        try:
            if not self.collection_mgr.collection_exists(kb_name):
                return {
                    "success": False,
                    "message": f"Knowledge base '{kb_name}' not found"
                }
            
            collection_name = self.collection_mgr._get_collection_name(kb_name)
            
            # First, count how many chunks exist for this file
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            points, _ = self._qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="filename",
                            match=MatchValue(value=filename)
                        )
                    ]
                ),
                limit=1,
                with_payload=False,
                with_vectors=False
            )
            
            if not points:
                return {
                    "success": False,
                    "message": f"Document '{filename}' not found in KB '{kb_name}'"
                }
            
            # Delete by filter
            result = self.vector_store.delete_by_filter(
                collection_name=collection_name,
                filter_dict={"filename": filename}
            )
            
            if result["success"]:
                logger.info("Deleted document: %s from %s", filename, kb_name)
                return {
                    "success": True,
                    "message": f"Document '{filename}' deleted successfully",
                    "kb_name": kb_name,
                    "filename": filename
                }
            else:
                return result
            
        except Exception as e:
            logger.error("Failed to delete document: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    def update_document(
        self,
        kb_name: str,
        filename: str,
        file_content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update (replace) a document in KB
        
        Deletes old document and uploads new content.
        
        Args:
            kb_name: Knowledge base name
            filename: Document filename
            file_content: New file content
            metadata: Optional metadata updates
            
        Returns:
            {"success": bool, "chunks_count": int, ...}
        """
        try:
            # Delete existing document
            delete_result = self.delete_document(kb_name, filename)
            
            if not delete_result["success"] and "not found" not in delete_result.get("message", "").lower():
                return delete_result
            
            # Upload new document
            upload_result = self.upload_document(
                kb_name=kb_name,
                filename=filename,
                file_content=file_content,
                metadata=metadata
            )
            
            if upload_result["success"]:
                upload_result["message"] = f"Document '{filename}' updated successfully"
                
            return upload_result
            
        except Exception as e:
            logger.error("Failed to update document: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    # ========================
    # Search & Retrieval
    # ========================
    
    def search(
        self,
        query: str,
        kb_name: str,
        top_k: int = 5,
        use_reranking: bool = True,
        include_metadata: bool = True,
        deduplicate: bool = True
    ) -> Dict[str, Any]:
        """Search for documents and return context for agent
        
        Optimized for agent consumption:
        - No semantic routing (kb_name required)
        - Returns formatted context ready for LLM
        - Deduplication to avoid redundant information
        - Rich metadata for source attribution
        
        Args:
            query: Search query
            kb_name: Target KB name (REQUIRED)
            top_k: Number of results (1-20)
            use_reranking: Whether to use reranking for better relevance
            include_metadata: Include source metadata (file, page, etc.)
            deduplicate: Remove duplicate/similar content
            
        Returns:
            {
                "success": bool,
                "kb_name": str,
                "query": str,
                "total_results": int,
                "results": [
                    {
                        "content": str,
                        "score": float,
                        "rank": int,
                        "metadata": {...}  # if include_metadata=True
                    }
                ],
                "formatted_context": str,  # Ready-to-use context for agent
                "metadata_summary": [...]   # Source files summary
            }
        """
        try:
            # Check KB exists
            if not self.collection_mgr.collection_exists(kb_name):
                return {
                    "success": False,
                    "message": f"Knowledge base '{kb_name}' not found",
                    "results": []
                }
            
            # Retrieve
            collection_name = self.collection_mgr._get_collection_name(kb_name)
            results = self.retriever.retrieve(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                use_reranking=use_reranking
            )
            
            logger.info("Search in %s: %d results (rerank=%s, dedup=%s)", 
                       kb_name, len(results), use_reranking, deduplicate)
            
            # Deduplicate if requested
            if deduplicate and results:
                results = self._deduplicate_results(results)
                logger.info("After deduplication: %d results", len(results))
            
            # Format results for agent
            formatted_results = []
            sources = []
            
            for idx, result in enumerate(results, 1):
                payload = result.get("payload", {})
                content = payload.get("text", "")
                score = result.get("score", 0.0)
                
                # Extract metadata
                metadata = {}
                if include_metadata:
                    metadata = {
                        "source_file": payload.get("source_file", "Unknown"),
                        "page": payload.get("page"),
                        "section": payload.get("section"),
                        "chunk_id": payload.get("chunk_id"),
                        "doc_id": payload.get("doc_id")
                    }
                    # Remove None values
                    metadata = {k: v for k, v in metadata.items() if v is not None}
                    
                    # Track unique sources
                    source_file = metadata.get("source_file", "Unknown")
                    if source_file not in sources:
                        sources.append(source_file)
                
                formatted_results.append({
                    "content": content,
                    "score": round(score, 4),
                    "rank": idx,
                    "metadata": metadata if include_metadata else {}
                })
            
            # Create formatted context for agent
            formatted_context = self._format_context_for_agent(formatted_results, include_metadata)
            
            # Create metadata summary
            metadata_summary = []
            if include_metadata and sources:
                for source in sources:
                    chunks_from_source = sum(
                        1 for r in formatted_results 
                        if r.get("metadata", {}).get("source_file") == source
                    )
                    metadata_summary.append({
                        "source_file": source,
                        "chunk_count": chunks_from_source
                    })
            
            return {
                "success": True,
                "kb_name": kb_name,
                "query": query,
                "total_results": len(formatted_results),
                "results": formatted_results,
                "formatted_context": formatted_context,
                "metadata_summary": metadata_summary
            }
            
        except Exception as e:
            logger.error("Search failed: %s", e, exc_info=True)
            return {
                "success": False,
                "message": str(e),
                "results": []
            }
    
    # ========================
    # Chat
    # ========================
    
    def chat(
        self,
        query: str,
        kb_name: Optional[str] = None,
        session_id: Optional[str] = None,
        top_k: int = 5,
        use_routing: bool = True,
        use_reranking: bool = True
    ) -> Dict[str, Any]:
        """Chat with retrieval-augmented generation
        
        Args:
            query: User query
            kb_name: Target KB (if None, uses routing)
            session_id: Session ID for conversation history
            top_k: Number of context documents
            use_routing: Whether to use semantic routing
            use_reranking: Whether to use reranking
            
        Returns:
            {
                "success": bool,
                "answer": "...",
                "kb_name": "...",
                "sources": [...],
                "session_id": "..."
            }
        """
        try:
            # Search for context (kb_name is required when calling search)
            if not kb_name:
                return {
                    "success": False,
                    "message": "kb_name is required for chat",
                    "answer": "",
                    "kb_name": None,
                    "sources": []
                }
            
            search_result = self.search(
                query=query,
                kb_name=kb_name,
                top_k=top_k,
                use_reranking=use_reranking
            )
            
            if not search_result["success"]:
                # No context, but still answer
                context = []
                kb_name = kb_name or "unknown"
            else:
                # search() returns results with "content" field
                context = [r.get("content", "") for r in search_result["results"]]
                kb_name = search_result.get("kb_name", kb_name)
            
            # Get conversation history
            history = None
            if session_id:
                history = self.chat_engine.get_history(session_id)
            
            # Generate answer
            response = self.chat_engine.chat(
                query=query,
                context=context,
                history=history,
                session_id=session_id
            )
            
            # Format sources from search results
            sources = []
            if search_result.get("success"):
                for r in search_result["results"]:
                    sources.append({
                        "text": r.get("content", "")[:200] + "...",
                        "score": r.get("score", 0),
                        "filename": r.get("metadata", {}).get("source_file", "N/A"),
                        "page": r.get("metadata", {}).get("page", 0)
                    })
            
            return {
                "success": True,
                "answer": response["answer"],
                "kb_name": kb_name,
                "sources": sources,
                "session_id": session_id,
                "model": response.get("model", "unknown"),
                "timestamp": response.get("timestamp"),
                "tokens": response.get("tokens", {})
            }
            
        except Exception as e:
            logger.error("Chat failed: %s", e)
    
    # Helper methods for search optimization
    # ========================
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate or highly similar content
        
        Uses simple text similarity to avoid redundant information.
        Keeps higher-scored results when duplicates found.
        
        Args:
            results: List of search results with scores
            
        Returns:
            Deduplicated list of results
        """
        if not results:
            return results
        
        deduplicated = []
        seen_contents = []
        
        for result in results:
            content = result.get("payload", {}).get("text", "")
            if not content:
                continue
            
            # Normalize content for comparison
            normalized = content.lower().strip()
            
            # Check if similar to any seen content
            is_duplicate = False
            for seen in seen_contents:
                # Simple character overlap check (>90% similarity = duplicate)
                if len(normalized) > 0 and len(seen) > 0:
                    overlap = len(set(normalized) & set(seen))
                    similarity = overlap / max(len(set(normalized)), len(set(seen)))
                    if similarity > 0.9:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                deduplicated.append(result)
                seen_contents.append(normalized)
        
        return deduplicated
    
    def _format_context_for_agent(
        self,
        results: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> str:
        """Format search results into context string for agent
        
        Creates a well-structured context that agents can easily parse and use.
        
        Args:
            results: Formatted search results
            include_metadata: Whether to include source attribution
            
        Returns:
            Formatted context string ready for agent/LLM consumption
        """
        if not results:
            return "No relevant information found."
        
        context_parts = []
        
        for idx, result in enumerate(results, 1):
            content = result.get("content", "")
            score = result.get("score", 0.0)
            metadata = result.get("metadata", {})
            
            # Build context entry
            if include_metadata and metadata:
                source_info = metadata.get("source_file", "Unknown")
                page_info = f", Page {metadata['page']}" if metadata.get("page") else ""
                section_info = f", Section: {metadata['section']}" if metadata.get("section") else ""
                
                header = f"[{idx}] (Source: {source_info}{page_info}{section_info}, Relevance: {score:.2f})"
            else:
                header = f"[{idx}] (Relevance: {score:.2f})"
            
            context_parts.append(f"{header}\n{content}\n")
        
        formatted = "\n".join(context_parts)
        
        # Add header
        final_context = (
            f"📚 Retrieved Context ({len(results)} relevant passages):\n\n"
            f"{formatted}"
        )
        
        return final_context
    
    def clear_chat_history(self, session_id: str) -> Dict[str, Any]:
        """Clear conversation history
        
        Args:
            session_id: Session ID
            
        Returns:
            {"success": bool}
        """
        try:
            success = self.chat_engine.clear_history(session_id)
            return {
                "success": success,
                "message": f"History cleared for session: {session_id}" if success else "Session not found"
            }
        except Exception as e:
            logger.error("Failed to clear history: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    # ========================
    # Admin / Utility
    # ========================
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health
        
        Returns:
            {"healthy": bool, "components": {...}}
        """
        components = {}
        
        # Check Qdrant
        try:
            collections = self._qdrant_client.get_collections()
            components["qdrant"] = {"status": "ok", "collections": len(collections.collections)}
        except Exception as e:
            components["qdrant"] = {"status": "error", "error": str(e)}
        
        # Check embeddings
        try:
            test = self._embedding_manager.embed_dense(["test"])[0]
            components["embeddings"] = {"status": "ok", "dimension": len(test)}
        except Exception as e:
            components["embeddings"] = {"status": "error", "error": str(e)}
        
        healthy = all(c.get("status") == "ok" for c in components.values())
        
        return {
            "healthy": healthy,
            "components": components,
            "timestamp": datetime.now().isoformat()
        }
