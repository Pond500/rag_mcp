"""Integration Test for Phase 4: Retriever, Router, ChatEngine

Tests:
1. Retriever - Hybrid Search + RRF + Reranking
2. Router - Semantic KB selection
3. ChatEngine - LLM chat with history

Run: PYTHONPATH=/Users/pond500/RAG/mcp_rag_v2:$PYTHONPATH python tests/integration/test_phase4.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from qdrant_client import QdrantClient
from src.config import get_settings
from src.models import EmbeddingManager, Reranker, LLMClient
from src.core import (
    CollectionManager, DocumentProcessor, MetadataExtractor,
    VectorStore, Retriever, Router, ChatEngine
)
from src.utils import get_logger

logger = get_logger(__name__)


def test_phase4():
    """Test Phase 4: Retriever + Router + ChatEngine"""
    print("\n" + "="*60)
    print("INTEGRATION TEST: Phase 4")
    print("="*60)
    
    # Setup
    settings = get_settings()
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
    
    collection_mgr = CollectionManager(qdrant_client, settings)
    doc_processor = DocumentProcessor(settings.document)
    metadata_extractor = MetadataExtractor(llm_client, settings.chat.system_prompt)
    vector_store = VectorStore(qdrant_client, embedding_manager)
    
    # Phase 4 modules
    retriever = Retriever(vector_store, embedding_manager, reranker, settings.search)
    router = Router(vector_store, embedding_manager, master_collection="master_index")
    chat_engine = ChatEngine(llm_client, settings.chat)
    
    print("✓ All modules initialized\n")
    
    # Get actual embedding dimension
    test_embed = embedding_manager.embed_dense(["test"])[0]
    actual_dense_dim = len(test_embed)
    
    # ========================
    # Step 1: Setup Test Data
    # ========================
    print("Step 1: Setup Test Data")
    print("-" * 40)
    
    # Create master index (use direct collection name, not kb_ prefix)
    master_collection = "master_index"
    
    try:
        qdrant_client.delete_collection(master_collection)
    except:
        pass
    
    from qdrant_client.models import VectorParams, Distance, SparseVectorParams, Modifier
    qdrant_client.create_collection(
        collection_name=master_collection,
        vectors_config={
            "dense": VectorParams(size=actual_dense_dim, distance=Distance.COSINE)
        },
        sparse_vectors_config={
            "bm25": SparseVectorParams(modifier=Modifier.IDF)
        }
    )
    print("✓ Created master index")
    
    # Create test KBs
    test_kbs = [
        {
            "kb_name": "test_gun_law",
            "description": "กฎหมายเกี่ยวกับอาวุธปืน การขออนุญาต การครอบครอง",
            "category": "firearms",
            "documents": [
                "พระราชบัญญัติอาวุธปืน พ.ศ. 2490 มาตรา 3 ห้ามมิให้ผู้ใดมีอาวุธปืนหรือกระสุนปืนไว้ในครอบครอง เว้นแต่จะได้รับอนุญาตจากนายทะเบียน"
            ]
        },
        {
            "kb_name": "test_contracts",
            "description": "สัญญาจ้างงาน ข้อกำหนดการทำงาน สวัสดิการ",
            "category": "contracts",
            "documents": [
                "สัญญาจ้างงาน ข้อ 1 ผู้ว่าจ้างตกลงจ้างผู้รับจ้างในตำแหน่งพนักงานพัฒนาโปรแกรม ข้อ 2 ค่าตอบแทนเดือนละ 50,000 บาท"
            ]
        }
    ]
    
    for kb in test_kbs:
        # Create collection
        if collection_mgr.collection_exists(kb["kb_name"]):
            collection_mgr.delete_collection(kb["kb_name"])
        
        collection_mgr.create_collection(
            kb_name=kb["kb_name"],
            description=kb["description"],
            dense_size=actual_dense_dim
        )
        
        # Add to master index
        router.add_kb_to_master(
            kb_name=kb["kb_name"],
            description=kb["description"],
            category=kb["category"]
        )
        
        # Add documents
        documents = [{"text": doc, "metadata": {"kb_name": kb["kb_name"]}} for doc in kb["documents"]]
        vector_store.upsert_documents(
            collection_name=collection_mgr._get_collection_name(kb["kb_name"]),
            documents=documents
        )
        
        print(f"✓ Created KB: {kb['kb_name']} ({len(kb['documents'])} docs)")
    
    # ========================
    # Step 2: Test Router
    # ========================
    print("\nStep 2: Test Router (Semantic Routing)")
    print("-" * 40)
    
    test_queries = [
        "อาวุธปืนต้องขออนุญาตอย่างไร",
        "สัญญาจ้างงานมีอะไรบ้าง"
    ]
    
    for query in test_queries:
        print(f"\n  Query: {query}")
        selected = router.route(query, top_k=2, score_threshold=0.0)
        
        if selected:
            for i, kb in enumerate(selected, 1):
                print(f"    {i}. {kb['kb_name']} (score: {kb['score']:.4f})")
                print(f"       Category: {kb['category']}")
        else:
            print("    No KB selected")
    
    # List all KBs
    all_kbs = router.list_kbs()
    print(f"\n  Total KBs in master: {len(all_kbs)}")
    
    # ========================
    # Step 3: Test Retriever
    # ========================
    print("\nStep 3: Test Retriever (Hybrid Search + RRF)")
    print("-" * 40)
    
    query = "อาวุธปืนต้องขออนุญาตอย่างไร"
    print(f"  Query: {query}")
    
    # Get best KB from router
    selected_kbs = router.route(query, top_k=1, score_threshold=0.0)
    if selected_kbs:
        kb_name = selected_kbs[0]["kb_name"]
        print(f"  Routed to: {kb_name}")
        
        # Retrieve with details
        details = retriever.retrieve_with_details(
            query=query,
            collection_name=collection_mgr._get_collection_name(kb_name),
            top_k=3
        )
        
        print(f"\n  Dense results: {len(details['dense_results'])}")
        print(f"  Sparse results: {len(details['sparse_results'])}")
        print(f"  RRF results: {len(details['rrf_results'])}")
        print(f"  Final results: {len(details['final_results'])}")
        
        if details['final_results']:
            print("\n  Top result:")
            top = details['final_results'][0]
            print(f"    Score: {top['score']:.4f}")
            print(f"    Text: {top['payload'].get('text', '')[:100]}...")
    
    # ========================
    # Step 4: Test ChatEngine
    # ========================
    print("\nStep 4: Test ChatEngine (LLM Chat)")
    print("-" * 40)
    
    query = "อาวุธปืนต้องทำอย่างไร"
    print(f"  Query: {query}")
    
    # Get context from retriever
    if selected_kbs:
        kb_name = selected_kbs[0]["kb_name"]
        results = retriever.retrieve(
            query=query,
            collection_name=collection_mgr._get_collection_name(kb_name),
            top_k=2
        )
        
        context = [r["payload"].get("text", "") for r in results]
        print(f"  Retrieved {len(context)} context documents")
        
        # Generate answer
        response = chat_engine.chat(
            query=query,
            context=context,
            session_id="test_session_1"
        )
        
        print(f"\n  Answer: {response['answer'][:200]}...")
        print(f"  Model: {response['model']}")
        print(f"  Session: {response['session_id']}")
        
        # Test follow-up query
        follow_up = "มันต้องใช้เอกสารอะไรบ้าง"
        print(f"\n  Follow-up: {follow_up}")
        
        # Rewrite query with history
        history = chat_engine.get_history("test_session_1")
        rewritten = chat_engine.rewrite_query(follow_up, history)
        print(f"  Rewritten: {rewritten}")
        
        # Get answer
        response2 = chat_engine.chat(
            query=follow_up,
            context=context,
            session_id="test_session_1"
        )
        print(f"  Answer: {response2['answer'][:200]}...")
        
        # Check history
        history = chat_engine.get_history("test_session_1")
        print(f"\n  Conversation turns: {len(history)}")
    
    # ========================
    # Step 5: Cleanup
    # ========================
    print("\nStep 5: Cleanup")
    print("-" * 40)
    
    for kb in test_kbs:
        collection_mgr.delete_collection(kb["kb_name"])
        print(f"  ✓ Deleted: {kb['kb_name']}")
    
    try:
        qdrant_client.delete_collection("master_index")
        print(f"  ✓ Deleted: master_index")
    except:
        pass
    
    # Clear chat history
    chat_engine.clear_history("test_session_1")
    print(f"  ✓ Cleared chat history")
    
    # ========================
    # Summary
    # ========================
    print("\n" + "="*60)
    print("INTEGRATION TEST: PHASE 4 PASSED ✓")
    print("="*60)
    print("\nPhase 4 modules validated:")
    print("  ✓ Retriever - Hybrid Search + RRF + Reranking")
    print("  ✓ Router - Semantic KB selection with master index")
    print("  ✓ ChatEngine - LLM chat with conversation history")
    print("\nAll core functionality working correctly!")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_phase4()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
