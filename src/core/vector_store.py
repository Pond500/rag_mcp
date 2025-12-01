"""Vector Store

Wrapper for Qdrant operations: upsert vectors and search.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    NamedVector,
    NamedSparseVector
)
import logging
import uuid

logger = logging.getLogger(__name__)


class VectorStore:
    """Wrapper for Qdrant vector operations
    
    Usage:
        store = VectorStore(qdrant_client, embedding_manager)
        
        # Upsert documents
        store.upsert_documents(
            collection_name="kb_gun_law",
            documents=[{"text": "...", "metadata": {...}}],
            embeddings={"dense": [...], "sparse": [...]}
        )
        
        # Search
        results = store.search_dense(collection_name, query_vector, top_k=10)
        results = store.search_sparse(collection_name, query_vector, top_k=10)
    """
    
    def __init__(self, qdrant_client, embedding_manager=None):
        self.client = qdrant_client
        self.embedding_manager = embedding_manager
    
    def upsert_documents(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        dense_embeddings: Optional[List[List[float]]] = None,
        sparse_embeddings: Optional[List[Dict]] = None,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Upsert documents with vectors to collection
        
        Args:
            collection_name: Name of Qdrant collection
            documents: List of dicts with "text" and "metadata" keys
            dense_embeddings: Pre-computed dense embeddings (if None, will compute)
            sparse_embeddings: Pre-computed sparse embeddings (if None, will compute)
            batch_size: Number of points per batch
            
        Returns:
            {"success": bool, "upserted_count": int, "point_ids": [...]}
        """
        try:
            # Compute embeddings if not provided
            if dense_embeddings is None and self.embedding_manager:
                texts = [doc["text"] for doc in documents]
                dense_embeddings = self.embedding_manager.embed_dense(texts)
                logger.info("Computed dense embeddings for %d documents", len(texts))
            
            if sparse_embeddings is None and self.embedding_manager:
                texts = [doc["text"] for doc in documents]
                sparse_embeddings = self.embedding_manager.embed_sparse(texts)
                logger.info("Computed sparse embeddings for %d documents", len(texts))
            
            # Create points
            points = []
            point_ids = []
            
            for idx, doc in enumerate(documents):
                point_id = str(uuid.uuid4())
                point_ids.append(point_id)
                
                # Build vectors dict
                vectors = {}
                if dense_embeddings and idx < len(dense_embeddings):
                    vectors["dense"] = dense_embeddings[idx]
                if sparse_embeddings and idx < len(sparse_embeddings):
                    vectors["bm25"] = sparse_embeddings[idx]
                
                # Build payload
                payload = {
                    "_type": "document",
                    "text": doc["text"],
                    **doc.get("metadata", {})
                }
                
                point = PointStruct(
                    id=point_id,
                    vector=vectors,
                    payload=payload
                )
                points.append(point)
            
            # Upsert in batches
            total_upserted = 0
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=collection_name,
                    points=batch
                )
                total_upserted += len(batch)
                logger.debug("Upserted batch %d-%d to %s", i, i + len(batch), collection_name)
            
            logger.info("Successfully upserted %d documents to %s", total_upserted, collection_name)
            
            return {
                "success": True,
                "upserted_count": total_upserted,
                "point_ids": point_ids
            }
            
        except Exception as e:
            logger.error("Failed to upsert documents: %s", e)
            return {
                "success": False,
                "error": str(e),
                "upserted_count": 0,
                "point_ids": []
            }
    
    def search_dense(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Search using dense vector
        
        Args:
            collection_name: Name of collection
            query_vector: Dense query vector
            top_k: Number of results to return
            filter_dict: Optional metadata filter (e.g. {"kb_name": "gun_law"})
            score_threshold: Optional minimum score
            
        Returns:
            List of results: [{"id": "...", "score": 0.9, "payload": {...}}, ...]
        """
        try:
            # Build filter
            query_filter = None
            if filter_dict:
                query_filter = self._build_filter(filter_dict)
            
            # Search using query_points (Qdrant 1.16+ API)
            result = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                using="dense",
                limit=top_k,
                query_filter=query_filter,
                score_threshold=score_threshold
            )
            
            # Format results
            formatted = []
            for point in result.points:
                formatted.append({
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                })
            
            logger.debug("Dense search found %d results in %s", len(formatted), collection_name)
            return formatted
            
        except Exception as e:
            logger.error("Dense search failed: %s", e)
            return []
    
    def search_sparse(
        self,
        collection_name: str,
        query_vector: Dict[str, List],
        top_k: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Search using sparse vector (BM25)
        
        Args:
            collection_name: Name of collection
            query_vector: Sparse query vector {"indices": [...], "values": [...]}
            top_k: Number of results to return
            filter_dict: Optional metadata filter
            score_threshold: Optional minimum score
            
        Returns:
            List of results: [{"id": "...", "score": 0.9, "payload": {...}}, ...]
        """
        try:
            # Build filter
            query_filter = None
            if filter_dict:
                query_filter = self._build_filter(filter_dict)
            
            # Create SparseVector for search
            from qdrant_client.models import SparseVector
            sparse_vec = SparseVector(
                indices=query_vector.get("indices", []),
                values=query_vector.get("values", [])
            )
            
            # Search with sparse vector using query_points (Qdrant 1.16+ API)
            result = self.client.query_points(
                collection_name=collection_name,
                query=sparse_vec,
                using="bm25",
                limit=top_k,
                query_filter=query_filter,
                score_threshold=score_threshold
            )
            
            # Format results
            formatted = []
            for point in result.points:
                formatted.append({
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                })
            
            logger.debug("Sparse search found %d results in %s", len(formatted), collection_name)
            return formatted
            
        except Exception as e:
            logger.error("Sparse search failed: %s", e)
            return []
    
    def _build_filter(self, filter_dict: Dict[str, Any]) -> Filter:
        """Build Qdrant filter from dict"""
        must_conditions = []
        
        for key, value in filter_dict.items():
            must_conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
            )
        
        return Filter(must=must_conditions)
    
    def delete_by_filter(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delete points matching filter
        
        Args:
            collection_name: Name of collection
            filter_dict: Filter dict (e.g. {"kb_name": "gun_law"})
            
        Returns:
            {"success": bool, "deleted_count": int or "unknown"}
        """
        try:
            query_filter = self._build_filter(filter_dict)
            
            result = self.client.delete(
                collection_name=collection_name,
                points_selector=query_filter
            )
            
            logger.info("Deleted points from %s with filter %s", collection_name, filter_dict)
            
            return {
                "success": True,
                "deleted_count": "unknown"  # Qdrant doesn't return count
            }
            
        except Exception as e:
            logger.error("Delete by filter failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "deleted_count": 0
            }
