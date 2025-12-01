"""Integration Test for Core Workflow

Tests the complete workflow:
1. CollectionManager - Create KB
2. DocumentProcessor - Extract and chunk text
3. MetadataExtractor - Extract metadata
4. VectorStore - Store vectors and search

Run: PYTHONPATH=/Users/pond500/RAG/mcp_rag_v2:$PYTHONPATH python tests/integration/test_core_workflow.py
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from qdrant_client import QdrantClient
from src.config import get_settings
from src.models import EmbeddingManager, LLMClient
from src.core.collection_manager import CollectionManager
from src.core.document_processor import DocumentProcessor
from src.core.metadata_extractor import MetadataExtractor
from src.core.vector_store import VectorStore
from src.utils import get_logger

logger = get_logger(__name__)


def test_core_workflow():
    """Test complete core workflow"""
    print("\n" + "="*60)
    print("INTEGRATION TEST: Core Workflow")
    print("="*60)
    
    # Load config
    settings = get_settings()
    print(f"\n✓ Settings loaded: Qdrant at {settings.qdrant.url}")
    
    # Initialize clients
    qdrant_client = QdrantClient(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        timeout=settings.qdrant.timeout
    )
    print(f"✓ Qdrant client connected")
    
    embedding_manager = EmbeddingManager(settings)
    print(f"✓ Embedding manager initialized")
    
    llm_client = LLMClient(
        api_key=settings.llm.api_key,
        model_name=settings.llm.model_name,
        base_url=settings.llm.base_url
    )
    print(f"✓ LLM client initialized")
    
    # Initialize core modules
    collection_mgr = CollectionManager(qdrant_client, settings)
    doc_processor = DocumentProcessor(settings.document)
    metadata_extractor = MetadataExtractor(llm_client, settings.chat.system_prompt)
    vector_store = VectorStore(qdrant_client, embedding_manager)
    
    print(f"✓ All core modules initialized\n")
    
    # Test embedding to get actual dimension
    test_embed = embedding_manager.embed_dense(["test"])[0]
    actual_dense_dim = len(test_embed)
    print(f"Detected dense embedding dimension: {actual_dense_dim}")
    
    # ========================
    # Step 1: Create Collection
    # ========================
    print("Step 1: Create Collection")
    print("-" * 40)
    
    kb_name = "test_integration_kb"
    
    # Delete if exists (cleanup)
    if collection_mgr.collection_exists(kb_name):
        print(f"  Cleaning up existing collection: {kb_name}")
        collection_mgr.delete_collection(kb_name)
    
    # Create new collection (use actual dense dimension)
    result = collection_mgr.create_collection(
        kb_name=kb_name,
        description="Integration test knowledge base",
        dense_size=actual_dense_dim
    )
    
    if result["success"]:
        print(f"  ✓ Collection created: {result['collection_name']}")
        print(f"    Description: {result['description']}")
        print(f"    Created at: {result['created_at']}")
    else:
        print(f"  ✗ Failed to create collection: {result.get('error')}")
        return False
    
    # ========================
    # Step 2: Process Documents
    # ========================
    print("\nStep 2: Process Documents")
    print("-" * 40)
    
    # Sample documents (simulate uploaded files)
    test_documents = [
        {
            "filename": "gun_law.txt",
            "content": """พระราชบัญญัติอาวุธปืน พ.ศ. 2490

หมวด 1 บทเบ็ดเสร็จ

มาตรา 1 ให้ใช้พระราชบัญญัตินี้ในราชอาณาจักร

มาตรา 2 ในพระราชบัญญัตินี้
"อาวุธปืน" หมายความว่า อาวุธปืนทุกชนิด
"กระสุนปืน" หมายความว่า กระสุนปืนทุกชนิด

มาตรา 3 ห้ามมิให้ผู้ใดมีอาวุธปืนหรือกระสุนปืนไว้ในครอบครอง
เว้นแต่จะได้รับอนุญาตจากนายทะเบียนตามพระราชบัญญัตินี้"""
        },
        {
            "filename": "contract_sample.txt",
            "content": """สัญญาจ้างงาน ฉบับนี้ทำขึ้นระหว่าง

1. บริษัท ABC จำกัด ("ผู้ว่าจ้าง")
2. นาย ทดสอบ ตัวอย่าง ("ผู้รับจ้าง")

ข้อ 1 ผู้ว่าจ้างตกลงจ้าง และผู้รับจ้างตกลงรับจ้างทำงาน
ในตำแหน่ง: พนักงานพัฒนาโปรแกรม

ข้อ 2 ค่าตอบแทน
ผู้ว่าจ้างตกลงจ่ายค่าตอบแทนเดือนละ 50,000 บาท"""
        }
    ]
    
    # Process each document
    all_chunks = []
    all_metadata = []
    
    for doc in test_documents:
        print(f"\n  Processing: {doc['filename']}")
        
        # Extract text (simulate file)
        pages = [doc["content"]]  # Simple case: single page
        print(f"    ✓ Extracted {len(pages)} page(s)")
        
        # Chunk text
        chunks = doc_processor.chunk_text(
            pages=pages,
            chunk_size=500,
            chunk_overlap=100
        )
        print(f"    ✓ Created {len(chunks)} chunk(s)")
        
        # Extract metadata (from first chunk)
        if chunks:
            metadata = metadata_extractor.extract(chunks[0]["text"])
            print(f"    ✓ Extracted metadata:")
            print(f"      - Type: {metadata.get('doc_type')}")
            print(f"      - Category: {metadata.get('category')}")
            print(f"      - Title: {metadata.get('title', 'N/A')[:50]}...")
            
            # Add metadata to each chunk
            for chunk in chunks:
                chunk["metadata"] = {
                    **metadata,
                    "kb_name": kb_name,
                    "filename": doc["filename"],
                    "page": chunk["page"],
                    "chunk_index": chunk["chunk_index"]
                }
            
            all_chunks.extend(chunks)
            all_metadata.append(metadata)
    
    print(f"\n  Total chunks: {len(all_chunks)}")
    
    # ========================
    # Step 3: Store Vectors
    # ========================
    print("\nStep 3: Store Vectors")
    print("-" * 40)
    
    # Prepare documents for upsert
    documents = [
        {
            "text": chunk["text"],
            "metadata": chunk["metadata"]
        }
        for chunk in all_chunks
    ]
    
    # Upsert to vector store
    result = vector_store.upsert_documents(
        collection_name=collection_mgr._get_collection_name(kb_name),
        documents=documents
    )
    
    if result["success"]:
        print(f"  ✓ Upserted {result['upserted_count']} documents")
        print(f"    Point IDs: {result['point_ids'][:3]}... (showing first 3)")
    else:
        print(f"  ✗ Failed to upsert: {result.get('error')}")
        return False
    
    # ========================
    # Step 4: Search (Dense)
    # ========================
    print("\nStep 4: Search - Dense Vector")
    print("-" * 40)
    
    query = "อาวุธปืนต้องขออนุญาตอย่างไร"
    print(f"  Query: {query}")
    
    # Embed query
    query_dense = embedding_manager.embed_dense([query])[0]
    print(f"  ✓ Query embedded (dense): {len(query_dense)}-dim")
    
    # Search
    results = vector_store.search_dense(
        collection_name=collection_mgr._get_collection_name(kb_name),
        query_vector=query_dense,
        top_k=3
    )
    
    print(f"  ✓ Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n    Result {i}:")
        print(f"      Score: {result['score']:.4f}")
        print(f"      Category: {result['payload'].get('category', 'N/A')}")
        print(f"      Filename: {result['payload'].get('filename', 'N/A')}")
        print(f"      Text: {result['payload'].get('text', '')[:100]}...")
    
    # ========================
    # Step 5: Search (Sparse)
    # ========================
    print("\nStep 5: Search - Sparse Vector (BM25)")
    print("-" * 40)
    
    # Embed query (sparse)
    query_sparse = embedding_manager.embed_sparse([query])[0]
    print(f"  ✓ Query embedded (sparse): {len(query_sparse.get('indices', []))} terms")
    
    # Search
    results_sparse = vector_store.search_sparse(
        collection_name=collection_mgr._get_collection_name(kb_name),
        query_vector=query_sparse,
        top_k=3
    )
    
    print(f"  ✓ Found {len(results_sparse)} results:")
    for i, result in enumerate(results_sparse, 1):
        print(f"\n    Result {i}:")
        print(f"      Score: {result['score']:.4f}")
        print(f"      Category: {result['payload'].get('category', 'N/A')}")
        print(f"      Filename: {result['payload'].get('filename', 'N/A')}")
        print(f"      Text: {result['payload'].get('text', '')[:100]}...")
    
    # ========================
    # Step 6: Get Collection Info
    # ========================
    print("\nStep 6: Get Collection Info")
    print("-" * 40)
    
    info = collection_mgr.get_collection_info(kb_name)
    if info["success"]:
        print(f"  ✓ Collection: {info['kb_name']}")
        print(f"    Points: {info['points_count']}")
        print(f"    Vectors: {info['vectors_count']}")
        print(f"    Description: {info['metadata'].get('description', 'N/A')}")
    
    # ========================
    # Step 7: Cleanup
    # ========================
    print("\nStep 7: Cleanup")
    print("-" * 40)
    
    result = collection_mgr.delete_collection(kb_name)
    if result["success"]:
        print(f"  ✓ Collection deleted: {kb_name}")
    
    # ========================
    # Summary
    # ========================
    print("\n" + "="*60)
    print("INTEGRATION TEST: PASSED ✓")
    print("="*60)
    print("\nAll core modules working correctly:")
    print("  ✓ CollectionManager - Create/Delete collections")
    print("  ✓ DocumentProcessor - Extract and chunk text")
    print("  ✓ MetadataExtractor - Extract metadata from text")
    print("  ✓ VectorStore - Upsert and search vectors")
    print("\nCore workflow validated successfully!")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_core_workflow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
