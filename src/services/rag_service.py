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
        self.doc_processor = DocumentProcessor(config.document)
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
            
            # Extract text
            pages = self.doc_processor.extract_text(filename, file_content)
            
            if not pages:
                return {
                    "success": False,
                    "message": "Failed to extract text from document"
                }
            
            logger.info("Extracted %d pages from %s", len(pages), filename)
            
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
                    "point_ids": result["point_ids"],
                    "metadata": doc_metadata,
                    "message": f"Document uploaded successfully: {result['upserted_count']} chunks"
                }
            else:
                return result
                
        except Exception as e:
            logger.error("Failed to upload document: %s", e)
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
            # Search for context
            search_result = self.search(
                query=query,
                kb_name=kb_name,
                top_k=top_k,
                use_routing=use_routing,
                use_reranking=use_reranking
            )
            
            if not search_result["success"]:
                # No context, but still answer
                context = []
                kb_name = kb_name or "unknown"
            else:
                context = [r["payload"].get("text", "") for r in search_result["results"]]
                kb_name = search_result["kb_name"]
            
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
            
            # Format sources
            sources = []
            if search_result.get("success"):
                for r in search_result["results"]:
                    sources.append({
                        "text": r["payload"].get("text", "")[:200] + "...",
                        "score": r["score"],
                        "filename": r["payload"].get("filename", "N/A"),
                        "page": r["payload"].get("page", 0)
                    })
            
            return {
                "success": True,
                "answer": response["answer"],
                "kb_name": kb_name,
                "sources": sources,
                "session_id": session_id,
                "model": response.get("model", "unknown"),
                "timestamp": response.get("timestamp")
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
