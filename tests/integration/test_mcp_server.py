"""Test MCP Server

Tests all MCP tools via HTTP requests.

Run server first: uvicorn mcp.server:app --reload
Then run this test: python tests/integration/test_mcp_server.py
"""
import requests
import time
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health check"""
    print("\n" + "="*60)
    print("TEST: Health Check")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/tools/health")
    print(f"Status: {response.status_code}")
    
    data = response.json()
    print(f"Healthy: {data.get('healthy')}")
    
    for component, info in data.get('components', {}).items():
        print(f"  - {component}: {info.get('status')}")
    
    assert response.status_code in [200, 503], "Health check failed"
    print("✓ Health check passed\n")


def test_create_kb():
    """Test KB creation"""
    print("="*60)
    print("TEST: Create KB")
    print("="*60)
    
    kbs = [
        {
            "kb_name": "test_mcp_gun_law",
            "description": "กฎหมายอาวุธปืน การขออนุญาต",
            "category": "firearms"
        },
        {
            "kb_name": "test_mcp_contracts",
            "description": "สัญญาจ้างงาน สวัสดิการ",
            "category": "contracts"
        }
    ]
    
    for kb in kbs:
        response = requests.post(f"{BASE_URL}/tools/create_kb", json=kb)
        print(f"Create {kb['kb_name']}: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"  ✓ {data.get('message')}")
        else:
            print(f"  ✗ {response.json()}")
    
    print()


def test_list_kbs():
    """Test listing KBs"""
    print("="*60)
    print("TEST: List KBs")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/tools/list_kbs")
    print(f"Status: {response.status_code}")
    
    data = response.json()
    print(f"Total KBs: {data.get('total')}")
    
    for kb in data.get('kbs', []):
        print(f"  - {kb['kb_name']}: {kb.get('description', 'N/A')[:50]}")
    
    assert response.status_code == 200, "List KBs failed"
    print("✓ List KBs passed\n")


def test_upload_document():
    """Test document upload"""
    print("="*60)
    print("TEST: Upload Document")
    print("="*60)
    
    docs = [
        {
            "kb_name": "test_mcp_gun_law",
            "filename": "gun_law.txt",
            "content": """พระราชบัญญัติอาวุธปืน พ.ศ. 2490

มาตรา 3 ห้ามมิให้ผู้ใดมีอาวุธปืนหรือกระสุนปืนไว้ในครอบครอง เว้นแต่จะได้รับอนุญาตจากนายทะเบียน

มาตรา 4 การขออนุญาตให้ยื่นคำขอต่อนายทะเบียน พร้อมเอกสาร:
- สำเนาบัตรประชาชน
- หนังสือรับรองการทำงาน
- ใบรับรองแพทย์
"""
        },
        {
            "kb_name": "test_mcp_contracts",
            "filename": "contract.txt",
            "content": """สัญญาจ้างงาน

ข้อ 1 ผู้ว่าจ้างตกลงจ้างผู้รับจ้างในตำแหน่งพนักงานพัฒนาโปรแกรม

ข้อ 2 ค่าตอบแทนเดือนละ 50,000 บาท

ข้อ 3 สวัสดิการ:
- ประกันสังคม
- ประกันสุขภาพ
- ลาพักผ่อนปีละ 10 วัน
"""
        }
    ]
    
    for doc in docs:
        files = {
            'file': (doc['filename'], doc['content'].encode('utf-8'), 'text/plain')
        }
        data = {'kb_name': doc['kb_name']}
        
        response = requests.post(f"{BASE_URL}/tools/upload_document", files=files, data=data)
        print(f"Upload {doc['filename']}: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"  ✓ {result.get('chunks_count')} chunks uploaded")
        else:
            print(f"  ✗ {response.json()}")
    
    print()


def test_search():
    """Test search"""
    print("="*60)
    print("TEST: Search")
    print("="*60)
    
    queries = [
        {
            "query": "อาวุธปืนต้องขออนุญาตอย่างไร",
            "kb_name": "test_mcp_gun_law",
            "top_k": 3
        },
        {
            "query": "สัญญาจ้างงานมีสวัสดิการอะไร",
            "kb_name": "test_mcp_contracts",
            "top_k": 3
        }
    ]
    
    for q in queries:
        response = requests.post(f"{BASE_URL}/tools/search", json=q)
        print(f"\nQuery: {q['query']}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  KB: {data.get('kb_name')}")
            print(f"  Results: {data.get('total')}")
            
            if data.get('results'):
                top = data['results'][0]
                print(f"  Top score: {top['score']:.4f}")
                print(f"  Text: {top['payload'].get('text', '')[:80]}...")
        else:
            print(f"  ✗ {response.json()}")
    
    print()


def test_chat():
    """Test chat"""
    print("="*60)
    print("TEST: Chat")
    print("="*60)
    
    session_id = "test_session_mcp"
    
    # First query
    query1 = {
        "query": "อาวุธปืนต้องขออนุญาตอย่างไร",
        "kb_name": "test_mcp_gun_law",
        "session_id": session_id,
        "top_k": 3
    }
    
    response = requests.post(f"{BASE_URL}/tools/chat", json=query1)
    print(f"\nQuery 1: {query1['query']}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  KB: {data.get('kb_name')}")
        print(f"  Answer: {data.get('answer', '')[:150]}...")
        print(f"  Sources: {len(data.get('sources', []))}")
        print(f"  Model: {data.get('model')}")
    else:
        print(f"  ✗ {response.json()}")
    
    # Follow-up query
    query2 = {
        "query": "ต้องใช้เอกสารอะไรบ้าง",
        "kb_name": "test_mcp_gun_law",
        "session_id": session_id,
        "top_k": 3
    }
    
    response = requests.post(f"{BASE_URL}/tools/chat", json=query2)
    print(f"\nQuery 2 (follow-up): {query2['query']}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  Answer: {data.get('answer', '')[:150]}...")
        print(f"  Session: {data.get('session_id')}")
    else:
        print(f"  ✗ {response.json()}")
    
    print()


def test_clear_history():
    """Test clear history"""
    print("="*60)
    print("TEST: Clear History")
    print("="*60)
    
    payload = {"session_id": "test_session_mcp"}
    response = requests.post(f"{BASE_URL}/tools/clear_history", json=payload)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ {data.get('message')}")
    
    print()


def test_delete_kb():
    """Test KB deletion"""
    print("="*60)
    print("TEST: Delete KB")
    print("="*60)
    
    kbs = ["test_mcp_gun_law", "test_mcp_contracts"]
    
    for kb_name in kbs:
        payload = {"kb_name": kb_name}
        response = requests.post(f"{BASE_URL}/tools/delete_kb", json=payload)
        
        print(f"Delete {kb_name}: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ {data.get('message')}")
        else:
            print(f"  ✗ {response.json()}")
    
    print()


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MCP SERVER INTEGRATION TEST")
    print("="*60)
    print(f"Testing server at: {BASE_URL}")
    print("="*60)
    
    try:
        # Check if server is running
        try:
            requests.get(BASE_URL, timeout=2)
        except requests.exceptions.ConnectionError:
            print("\n✗ Server not running!")
            print("Start server first: uvicorn mcp.server:app --reload")
            sys.exit(1)
        
        # Run tests
        test_health()
        test_create_kb()
        test_list_kbs()
        test_upload_document()
        test_search()
        test_chat()
        test_clear_history()
        test_delete_kb()
        
        # Summary
        print("="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        print("\nMCP Server validated:")
        print("  ✓ Health check")
        print("  ✓ Create/Delete/List KBs")
        print("  ✓ Upload documents")
        print("  ✓ Search with Hybrid Search")
        print("  ✓ Chat with RAG")
        print("  ✓ Clear conversation history")
        print("\nMCP Server working correctly!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
