"""Router - Semantic KB Selection

Uses master index to route queries to the most relevant knowledge base.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Router:
    """Semantic router for KB selection
    
    Usage:
        router = Router(
            vector_store=vector_store,
            embedding_manager=embedding_manager,
            master_collection="master_index"
        )
        
        selected_kb = router.route(
            query="อาวุธปืนต้องขออนุญาตอย่างไร",
            kb_list=["gun_law", "contracts", "hr_policy"]
        )
    """
    
    def __init__(
        self,
        vector_store,
        embedding_manager,
        master_collection: str = "master_index"
    ):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.master_collection = master_collection
    
    def route(
        self,
        query: str,
        kb_list: Optional[List[str]] = None,
        top_k: int = 1,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Route query to best matching KB(s)
        
        Args:
            query: User query
            kb_list: Optional list of KB names to filter (if None, search all)
            top_k: Number of KBs to return
            score_threshold: Minimum similarity score
            
        Returns:
            List of selected KBs: [{"kb_name": "gun_law", "score": 0.9, "description": "..."}, ...]
        """
        try:
            # Embed query
            query_dense = self.embedding_manager.embed_dense([query])[0]
            
            # Build filter if kb_list provided
            filter_dict = None
            if kb_list:
                # Note: Qdrant doesn't support "IN" filter directly
                # For simplicity, we'll search all and filter in Python
                pass
            
            # Search master index
            results = self.vector_store.search_dense(
                collection_name=self.master_collection,
                query_vector=query_dense,
                top_k=top_k * 2,  # Get more to filter
                score_threshold=score_threshold
            )
            
            # Filter by kb_list if provided
            if kb_list:
                results = [
                    r for r in results
                    if r["payload"].get("kb_name") in kb_list
                ]
            
            # Format results
            selected = []
            for r in results[:top_k]:
                selected.append({
                    "kb_name": r["payload"].get("kb_name"),
                    "score": r["score"],
                    "description": r["payload"].get("description", ""),
                    "category": r["payload"].get("category", "general")
                })
            
            if selected:
                logger.info("Routed query to: %s (score: %.3f)",
                           selected[0]["kb_name"], selected[0]["score"])
            else:
                logger.warning("No KB matched query (threshold: %.2f)", score_threshold)
            
            return selected
            
        except Exception as e:
            logger.error("Routing failed: %s", e)
            return []
    
    def add_kb_to_master(
        self,
        kb_name: str,
        description: str,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add KB entry to master index
        
        Args:
            kb_name: Name of knowledge base
            description: Description for semantic search
            category: Category (e.g., "firearms", "contracts")
            metadata: Additional metadata
            
        Returns:
            {"success": bool, "point_id": "..."}
        """
        try:
            # Embed description
            dense_embedding = self.embedding_manager.embed_dense([description])[0]
            sparse_embedding = self.embedding_manager.embed_sparse([description])[0]
            
            # Build payload
            payload = {
                "_type": "kb_index",
                "kb_name": kb_name,
                "description": description,
                "category": category,
                **(metadata or {})
            }
            
            # Upsert to master index
            result = self.vector_store.upsert_documents(
                collection_name=self.master_collection,
                documents=[{"text": description, "metadata": payload}],
                dense_embeddings=[dense_embedding],
                sparse_embeddings=[sparse_embedding]
            )
            
            if result["success"]:
                logger.info("Added KB '%s' to master index", kb_name)
                return {
                    "success": True,
                    "point_id": result["point_ids"][0]
                }
            else:
                return {"success": False, "error": result.get("error")}
                
        except Exception as e:
            logger.error("Failed to add KB to master: %s", e)
            return {"success": False, "error": str(e)}
    
    def remove_kb_from_master(self, kb_name: str) -> Dict[str, Any]:
        """Remove KB entry from master index
        
        Args:
            kb_name: Name of knowledge base
            
        Returns:
            {"success": bool}
        """
        try:
            result = self.vector_store.delete_by_filter(
                collection_name=self.master_collection,
                filter_dict={"kb_name": kb_name}
            )
            
            logger.info("Removed KB '%s' from master index", kb_name)
            return {"success": result["success"]}
            
        except Exception as e:
            logger.error("Failed to remove KB from master: %s", e)
            return {"success": False, "error": str(e)}
    
    def list_kbs(self) -> List[Dict[str, Any]]:
        """List all KBs in master index
        
        Returns:
            List of KB entries: [{"kb_name": "...", "description": "...", "category": "..."}, ...]
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Scroll through all KB entries
            results, _ = self.vector_store.client.scroll(
                collection_name=self.master_collection,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="_type",
                            match=MatchValue(value="kb_index")
                        )
                    ]
                ),
                limit=100
            )
            
            kbs = []
            for point in results:
                kbs.append({
                    "kb_name": point.payload.get("kb_name"),
                    "description": point.payload.get("description", ""),
                    "category": point.payload.get("category", "general")
                })
            
            logger.debug("Listed %d KBs from master index", len(kbs))
            return kbs
            
        except Exception as e:
            logger.error("Failed to list KBs: %s", e)
            return []
