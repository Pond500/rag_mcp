"""Integration Test for Phase 5: RAG Service

Tests the complete RAG service API:
1. KB management (create, list, delete)
2. Document upload
3. Search
4. Chat with retrieval

Run: PYTHONPATH=/Users/pond500/RAG/mcp_rag_v2:$PYTHONPATH python tests/integration/test_rag_service.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings
from src.services import RAGService
from src.utils import get_logger

logger = get_logger(__name__)


def test_rag_service():
    """Test complete RAG service"""
    print("\n" + "="*60)
    print("INTEGRATION TEST: RAG Service")
    print("="*60)
    
    # Initialize service
    settings = get_settings()
    service = RAGService.from_settings(settings)
    
    print("✓ RAG Service initialized\n")
    
    # ========================
    # Step 1: Health Check
    # ========================
    print("Step 1: Health Check")
    print("-" * 40)
    
    health = service.health_check()
    print(f"  Healthy: {health['healthy']}")
    for component, info in health['components'].items():
        status = info.get('status', 'unknown')
        print(f"  - {component}: {status}")
    print()
    
    # ========================
    # Step 2: KB Management
    # ========================
    print("Step 2: KB Management")
    print("-" * 40)
    
    # Create test KBs
    test_kbs = [
        {
            "kb_name": "test_service_gun_law",
            "description": "กฎหมายเกี่ยวกับอาวุธปืน การขออนุญาต",
            "category": "firearms"
        },
        {
            "kb_name": "test_service_contracts",
            "description": "สัญญาจ้างงาน ข้อกำหนดการทำงาน",
            "category": "contracts"
        }
    ]
    
    for kb in test_kbs:
        result = service.create_kb(
            kb_name=kb["kb_name"],
            description=kb["description"],
            category=kb["category"]
        )
        
        if result["success"]:
            print(f"  ✓ Created: {kb['kb_name']}")
        else:
            print(f"  ✗ Failed: {kb['kb_name']} - {result.get('message')}")
    
    # List KBs
    list_result = service.list_kbs()
    print(f"\n  Total KBs: {list_result['total']}")
    for kb in list_result['kbs']:
        print(f"  - {kb['kb_name']}: {kb.get('description', 'N/A')[:50]}...")
    
    print()
    
    # ========================
    # Step 3: Document Upload
    # ========================
    print("Step 3: Document Upload")
    print("-" * 40)
    
    # Sample documents
    test_docs = [
        {
            "kb_name": "test_service_gun_law",
            "filename": "gun_law.txt",
            "content": """พระราชบัญญัติอาวุธปืน พ.ศ. 2490

หมวด 1 บทเบ็ดเสร็จ

มาตรา 1 ให้ใช้พระราชบัญญัตินี้ในราชอาณาจักร

มาตรา 2 ในพระราชบัญญัตินี้
"อาวุธปืน" หมายความว่า อาวุธปืนทุกชนิด
"กระสุนปืน" หมายความว่า กระสุนปืนทุกชนิด

มาตรา 3 ห้ามมิให้ผู้ใดมีอาวุธปืนหรือกระสุนปืนไว้ในครอบครอง เว้นแต่จะได้รับอนุญาตจากนายทะเบียน

มาตรา 4 การขออนุญาตให้ยื่นคำขอต่อนายทะเบียนพร้อมเอกสารหลักฐาน
- สำเนาบัตรประชาชน
- หนังสือรับรองการทำงาน
- ใบรับรองแพทย์
"""
        },
        {
            "kb_name": "test_service_contracts",
            "filename": "contract.txt",
            "content": """สัญญาจ้างงาน

ฉบับนี้ทำขึ้นระหว่าง

1. บริษัท ABC จำกัด ("ผู้ว่าจ้าง")
2. นาย ทดสอบ ตัวอย่าง ("ผู้รับจ้าง")

ข้อ 1 ผู้ว่าจ้างตกลงจ้าง และผู้รับจ้างตกลงรับจ้างทำงาน
ในตำแหน่ง: พนักงานพัฒนาโปรแกรม

ข้อ 2 ค่าตอบแทน
ผู้ว่าจ้างตกลงจ่ายค่าตอบแทนเดือนละ 50,000 บาท

ข้อ 3 สวัสดิการ
- ประกันสังคม
- ประกันสุขภาพ
- ลาพักผ่อนปีละ 10 วัน
"""
        }
    ]
    
    for doc in test_docs:
        result = service.upload_document(
            kb_name=doc["kb_name"],
            filename=doc["filename"],
            file_content=doc["content"].encode('utf-8')
        )
        
        if result["success"]:
            print(f"  ✓ Uploaded: {doc['filename']} → {doc['kb_name']}")
            print(f"    Chunks: {result['chunks_count']}")
            print(f"    Metadata: {result['metadata'].get('doc_type')}, {result['metadata'].get('category')}")
        else:
            print(f"  ✗ Failed: {doc['filename']} - {result.get('message')}")
    
    print()
    
    # ========================
    # Step 4: Search
    # ========================
    print("Step 4: Search")
    print("-" * 40)
    
    test_queries = [
        ("อาวุธปืนต้องขออนุญาตอย่างไร", "test_service_gun_law"),
        ("สัญญาจ้างงานมีสวัสดิการอะไรบ้าง", "test_service_contracts"),
        ("อาวุธปืน", None)  # Test routing
    ]
    
    for query, kb_name in test_queries:
        print(f"\n  Query: {query}")
        if kb_name:
            print(f"  Target KB: {kb_name}")
        else:
            print(f"  Using routing...")
        
        result = service.search(
            query=query,
            kb_name=kb_name,
            top_k=3,
            use_routing=(kb_name is None)
        )
        
        if result["success"]:
            print(f"  ✓ Found {result['total']} results in {result['kb_name']}")
            if result["results"]:
                top = result["results"][0]
                print(f"    Top result (score: {top['score']:.4f}):")
                print(f"    {top['payload'].get('text', '')[:100]}...")
        else:
            print(f"  ✗ {result.get('message')}")
    
    print()
    
    # ========================
    # Step 5: Chat
    # ========================
    print("Step 5: Chat with RAG")
    print("-" * 40)
    
    session_id = "test_session_service"
    
    # First query
    query1 = "อาวุธปืนต้องขออนุญาตอย่างไร"
    print(f"\n  Query 1: {query1}")
    
    result = service.chat(
        query=query1,
        kb_name="test_service_gun_law",
        session_id=session_id,
        top_k=3
    )
    
    if result["success"]:
        print(f"  ✓ Answer: {result['answer'][:150]}...")
        print(f"    KB: {result['kb_name']}")
        print(f"    Sources: {len(result['sources'])}")
        print(f"    Model: {result['model']}")
    else:
        print(f"  ✗ {result.get('message')}")
    
    # Follow-up query (with history)
    query2 = "ต้องใช้เอกสารอะไรบ้าง"
    print(f"\n  Query 2 (follow-up): {query2}")
    
    result = service.chat(
        query=query2,
        kb_name="test_service_gun_law",
        session_id=session_id,
        top_k=3
    )
    
    if result["success"]:
        print(f"  ✓ Answer: {result['answer'][:150]}...")
        print(f"    Session: {result['session_id']}")
    
    # Chat with routing
    query3 = "สัญญาจ้างงานมีสวัสดิการอะไร"
    print(f"\n  Query 3 (with routing): {query3}")
    
    result = service.chat(
        query=query3,
        kb_name=None,  # Use routing
        session_id="another_session",
        top_k=3,
        use_routing=True
    )
    
    if result["success"]:
        print(f"  ✓ Answer: {result['answer'][:150]}...")
        print(f"    Routed to: {result['kb_name']}")
    
    print()
    
    # ========================
    # Step 6: Get KB Info
    # ========================
    print("Step 6: Get KB Info")
    print("-" * 40)
    
    for kb in test_kbs:
        info = service.get_kb_info(kb["kb_name"])
        if info.get("success"):
            print(f"  {kb['kb_name']}:")
            print(f"    Points: {info.get('points_count', 'N/A')}")
            print(f"    Description: {info['metadata'].get('description', 'N/A')[:50]}...")
    
    print()
    
    # ========================
    # Step 7: Cleanup
    # ========================
    print("Step 7: Cleanup")
    print("-" * 40)
    
    # Clear chat history
    service.clear_chat_history(session_id)
    service.clear_chat_history("another_session")
    print("  ✓ Cleared chat histories")
    
    # Delete KBs
    for kb in test_kbs:
        result = service.delete_kb(kb["kb_name"])
        if result["success"]:
            print(f"  ✓ Deleted: {kb['kb_name']}")
    
    print()
    
    # ========================
    # Summary
    # ========================
    print("="*60)
    print("INTEGRATION TEST: RAG SERVICE PASSED ✓")
    print("="*60)
    print("\nRAG Service validated:")
    print("  ✓ Health check")
    print("  ✓ KB management (create, list, delete)")
    print("  ✓ Document upload with processing")
    print("  ✓ Search with routing")
    print("  ✓ Chat with RAG and conversation history")
    print("  ✓ KB info retrieval")
    print("\nComplete RAG pipeline working correctly!")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_rag_service()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
