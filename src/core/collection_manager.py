"""Collection Manager

Handles CRUD operations for Qdrant collections (knowledge bases).
Each collection stores vectors for one KB.
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CollectionManager:
    """Manage Qdrant collections (create, list, delete, exists)
    
    Usage:
        mgr = CollectionManager(qdrant_client, config)
        mgr.create_collection("my_kb", description="My knowledge base")
        exists = mgr.collection_exists("my_kb")
        info = mgr.get_collection_info("my_kb")
        mgr.delete_collection("my_kb")
    """
    
    def __init__(self, qdrant_client, config=None):
        self.client = qdrant_client
        self.config = config
        
    def _get_collection_name(self, kb_name: str) -> str:
        """Convert KB name to collection name (prefix with 'kb_')"""
        return f"kb_{kb_name}"
    
    def collection_exists(self, kb_name: str) -> bool:
        """Check if collection exists"""
        collection_name = self._get_collection_name(kb_name)
        try:
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception as e:
            logger.error("Failed to check collection existence: %s", e)
            return False
    
    def create_collection(
        self,
        kb_name: str,
        description: str = "",
        dense_size: int = 1024,
        dense_distance: str = "Cosine"
    ) -> Dict[str, Any]:
        """Create a new collection with named vectors (dense + sparse)
        
        Args:
            kb_name: Knowledge base name
            description: Description of the KB
            dense_size: Dimension of dense vectors (default 1024 for bge-m3)
            dense_distance: Distance metric (Cosine, Dot, Euclid)
            
        Returns:
            Dict with success status and collection info
        """
        from qdrant_client.models import VectorParams, Distance, SparseVectorParams, Modifier
        
        collection_name = self._get_collection_name(kb_name)
        
        if self.collection_exists(kb_name):
            return {
                "success": False,
                "message": f"Collection '{kb_name}' already exists",
                "collection_name": collection_name
            }
        
        try:
            # Map distance string to enum
            distance_map = {
                "Cosine": Distance.COSINE,
                "Dot": Distance.DOT,
                "Euclid": Distance.EUCLID
            }
            distance_enum = distance_map.get(dense_distance, Distance.COSINE)
            
            # Create collection with named vectors
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": VectorParams(size=dense_size, distance=distance_enum)
                },
                sparse_vectors_config={
                    "bm25": SparseVectorParams(modifier=Modifier.IDF)
                }
            )
            
            # Store metadata point (description, created_at, etc.)
            metadata_point = {
                "_type": "collection_metadata",
                "kb_name": kb_name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "document_count": 0
            }
            
            from qdrant_client.models import PointStruct
            import uuid
            
            # Create dummy vectors for metadata point
            dummy_dense = [0.0] * dense_size
            dummy_sparse = {"indices": [], "values": []}
            
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector={"dense": dummy_dense, "bm25": dummy_sparse},
                        payload=metadata_point
                    )
                ]
            )
            
            logger.info("✅ Created Hybrid Search collection: %s (Dense + BM25)", collection_name)
            
            return {
                "success": True,
                "kb_name": kb_name,
                "collection_name": collection_name,
                "description": description,
                "created_at": metadata_point["created_at"]
            }
            
        except Exception as e:
            logger.error("Failed to create collection: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    def get_collection_info(self, kb_name: str) -> Dict[str, Any]:
        """Get collection info (points count, metadata)"""
        collection_name = self._get_collection_name(kb_name)
        
        if not self.collection_exists(kb_name):
            return {
                "success": False,
                "message": f"Collection '{kb_name}' not found"
            }
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # Try to get metadata point
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            metadata_results = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="_type",
                            match=MatchValue(value="collection_metadata")
                        )
                    ]
                ),
                limit=1
            )
            
            metadata = {}
            if metadata_results[0]:
                metadata = metadata_results[0][0].payload
            
            return {
                "success": True,
                "kb_name": kb_name,
                "collection_name": collection_name,
                "points_count": collection.points_count,
                "vectors_count": collection.indexed_vectors_count,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error("Failed to get collection info: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    def delete_collection(self, kb_name: str) -> Dict[str, Any]:
        """Delete a collection"""
        collection_name = self._get_collection_name(kb_name)
        
        if not self.collection_exists(kb_name):
            return {
                "success": False,
                "message": f"Collection '{kb_name}' not found"
            }
        
        try:
            self.client.delete_collection(collection_name)
            logger.info("✅ Deleted collection: %s", collection_name)
            
            return {
                "success": True,
                "message": f"Collection '{kb_name}' deleted successfully"
            }
            
        except Exception as e:
            logger.error("Failed to delete collection: %s", e)
            return {
                "success": False,
                "message": str(e)
            }
    
    def list_collections(self) -> Dict[str, Any]:
        """List all collections"""
        try:
            collections = self.client.get_collections().collections
            
            kb_collections = []
            for c in collections:
                if c.name.startswith("kb_"):
                    kb_name = c.name[3:]  # Remove 'kb_' prefix
                    info = self.get_collection_info(kb_name)
                    kb_collections.append(info)
            
            return {
                "success": True,
                "collections": kb_collections,
                "total": len(kb_collections)
            }
            
        except Exception as e:
            logger.error("Failed to list collections: %s", e)
            return {
                "success": False,
                "message": str(e),
                "collections": []
            }
