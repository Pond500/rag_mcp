"""Retriever - Hybrid Search with RRF and Reranking

Orchestrates:
1. Dense vector search (cosine similarity)
2. Sparse BM25 search
3. RRF (Reciprocal Rank Fusion) to merge results
4. Reranking with CrossEncoder
5. Return top-k results

Based on legacy implementation but refactored for clean architecture.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Retriever:
    """Hybrid Search retriever with RRF and reranking
    
    Usage:
        retriever = Retriever(
            vector_store=vector_store,
            embedding_manager=embedding_manager,
            reranker=reranker,
            config=settings.search
        )
        
        results = retriever.retrieve(
            query="อาวุธปืนต้องขออนุญาตอย่างไร",
            collection_name="kb_gun_law",
            top_k=5
        )
    """
    
    def __init__(
        self,
        vector_store,
        embedding_manager,
        reranker,
        config=None
    ):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.reranker = reranker
        
        # Config with defaults
        self.top_k = getattr(config, "top_k", 5) if config else 5
        self.search_limit_multiplier = getattr(config, "search_limit_multiplier", 2) if config else 2
        self.rrf_k = getattr(config, "rrf_k", 60) if config else 60
        self.rerank_threshold = getattr(config, "rerank_threshold", 0.0) if config else 0.0
    
    def retrieve(
        self,
        query: str,
        collection_name: str,
        top_k: Optional[int] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        use_reranking: bool = True
    ) -> List[Dict[str, Any]]:
        """Retrieve documents using Hybrid Search + RRF + Reranking
        
        Args:
            query: Search query
            collection_name: Name of Qdrant collection
            top_k: Number of final results (uses config default if None)
            filter_dict: Optional metadata filter (e.g. {"category": "firearms"})
            use_reranking: Whether to apply reranking (default: True)
            
        Returns:
            List of results with scores: [{"id": "...", "score": 0.9, "payload": {...}}, ...]
        """
        top_k = top_k or self.top_k
        search_limit = top_k * self.search_limit_multiplier
        
        logger.info("Hybrid Search: query='%s', collection='%s', top_k=%d", 
                   query[:50], collection_name, top_k)
        
        try:
            # Step 1: Embed query (dense + sparse)
            query_dense = self.embedding_manager.embed_dense([query])[0]
            query_sparse = self.embedding_manager.embed_sparse([query])[0]
            
            logger.debug("Embedded query: dense=%d-dim, sparse=%d terms", 
                        len(query_dense), len(query_sparse.get("indices", [])))
            
            # Step 2: Dense search
            dense_results = self.vector_store.search_dense(
                collection_name=collection_name,
                query_vector=query_dense,
                top_k=search_limit,
                filter_dict=filter_dict
            )
            logger.debug("Dense search: %d results", len(dense_results))
            
            # Step 3: Sparse search
            sparse_results = self.vector_store.search_sparse(
                collection_name=collection_name,
                query_vector=query_sparse,
                top_k=search_limit,
                filter_dict=filter_dict
            )
            logger.debug("Sparse search: %d results", len(sparse_results))
            
            # Step 4: RRF fusion
            fused_results = self._rrf_fusion(dense_results, sparse_results, k=self.rrf_k)
            logger.debug("RRF fusion: %d unique results", len(fused_results))
            
            # Step 5: Reranking (optional)
            if use_reranking and self.reranker:
                reranked_results = self._rerank(query, fused_results)
                logger.debug("Reranked: %d results", len(reranked_results))
                
                # Filter by threshold
                if self.rerank_threshold > 0:
                    reranked_results = [
                        r for r in reranked_results 
                        if r["score"] >= self.rerank_threshold
                    ]
                    logger.debug("After threshold filter: %d results", len(reranked_results))
                
                final_results = reranked_results[:top_k]
            else:
                final_results = fused_results[:top_k]
            
            logger.info("Retrieval complete: returning %d results", len(final_results))
            return final_results
            
        except Exception as e:
            logger.error("Retrieval failed: %s", e)
            return []
    
    def _rrf_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion (RRF)
        
        Formula: RRF_score(d) = sum(1 / (k + rank_i(d)))
        where rank_i(d) is the rank of document d in search result i
        
        Args:
            dense_results: Results from dense search
            sparse_results: Results from sparse search
            k: RRF constant (default: 60)
            
        Returns:
            Fused results sorted by RRF score
        """
        # Build rank maps
        dense_ranks = {r["id"]: rank for rank, r in enumerate(dense_results, start=1)}
        sparse_ranks = {r["id"]: rank for rank, r in enumerate(sparse_results, start=1)}
        
        # Get all unique document IDs
        all_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())
        
        # Calculate RRF scores
        rrf_scores = {}
        for doc_id in all_ids:
            score = 0.0
            if doc_id in dense_ranks:
                score += 1.0 / (k + dense_ranks[doc_id])
            if doc_id in sparse_ranks:
                score += 1.0 / (k + sparse_ranks[doc_id])
            rrf_scores[doc_id] = score
        
        # Build result list with payloads
        id_to_payload = {}
        for r in dense_results:
            id_to_payload[r["id"]] = r["payload"]
        for r in sparse_results:
            if r["id"] not in id_to_payload:
                id_to_payload[r["id"]] = r["payload"]
        
        fused = [
            {
                "id": doc_id,
                "score": rrf_scores[doc_id],
                "payload": id_to_payload[doc_id]
            }
            for doc_id in all_ids
        ]
        
        # Sort by RRF score (descending)
        fused.sort(key=lambda x: x["score"], reverse=True)
        
        logger.debug("RRF fusion: %d dense + %d sparse → %d unique (k=%d)",
                    len(dense_results), len(sparse_results), len(fused), k)
        
        return fused
    
    def _rerank(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rerank results using CrossEncoder
        
        Args:
            query: Original query
            results: Results to rerank
            
        Returns:
            Reranked results with updated scores
        """
        if not results:
            return []
        
        # Extract texts
        texts = [r["payload"].get("text", "") for r in results]
        
        # Score with reranker
        scores = self.reranker.score(query, texts)
        
        # Update scores and re-sort
        reranked = []
        for result, score in zip(results, scores):
            reranked.append({
                "id": result["id"],
                "score": float(score),  # Convert from numpy float
                "payload": result["payload"]
            })
        
        reranked.sort(key=lambda x: x["score"], reverse=True)
        
        return reranked
    
    def retrieve_with_details(
        self,
        query: str,
        collection_name: str,
        top_k: Optional[int] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        use_reranking: bool = True
    ) -> Dict[str, Any]:
        """Retrieve with detailed intermediate results (for debugging)
        
        Returns:
            {
                "query": "...",
                "dense_results": [...],
                "sparse_results": [...],
                "rrf_results": [...],
                "final_results": [...]
            }
        """
        top_k = top_k or self.top_k
        search_limit = top_k * self.search_limit_multiplier
        
        # Embed query
        query_dense = self.embedding_manager.embed_dense([query])[0]
        query_sparse = self.embedding_manager.embed_sparse([query])[0]
        
        # Dense search
        dense_results = self.vector_store.search_dense(
            collection_name=collection_name,
            query_vector=query_dense,
            top_k=search_limit,
            filter_dict=filter_dict
        )
        
        # Sparse search
        sparse_results = self.vector_store.search_sparse(
            collection_name=collection_name,
            query_vector=query_sparse,
            top_k=search_limit,
            filter_dict=filter_dict
        )
        
        # RRF fusion
        rrf_results = self._rrf_fusion(dense_results, sparse_results, k=self.rrf_k)
        
        # Reranking
        if use_reranking and self.reranker:
            reranked_results = self._rerank(query, rrf_results)
            final_results = reranked_results[:top_k]
        else:
            final_results = rrf_results[:top_k]
        
        return {
            "query": query,
            "dense_results": dense_results,
            "sparse_results": sparse_results,
            "rrf_results": rrf_results,
            "final_results": final_results,
            "config": {
                "top_k": top_k,
                "search_limit": search_limit,
                "rrf_k": self.rrf_k,
                "rerank_threshold": self.rerank_threshold,
                "use_reranking": use_reranking
            }
        }
