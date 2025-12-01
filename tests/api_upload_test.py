"""
API Upload Script - Upload gun law documents via MCP Server API
"""

import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Configuration
SERVER_URL = "http://localhost:8000"
KB_NAME = "gun_law_api_test"
DATA_FOLDER = Path("/Users/pond500/Downloads/1. งานอาวุธปืน")


def upload_file_via_api(file_path: Path, kb_name: str) -> Dict[str, Any]:
    """Upload a single file via multipart/form-data"""
    url = f"{SERVER_URL}/tools/upload_document"
    
    with open(file_path, 'rb') as f:
        files = {
            'file': (file_path.name, f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        }
        data = {
            'kb_name': kb_name
        }
        
        response = requests.post(url, files=files, data=data)
        
    return response.json()


def main():
    print("="*80)
    print("🚀 API UPLOAD TEST - Gun Law Documents")
    print("="*80)
    print(f"Server: {SERVER_URL}")
    print(f"KB: {KB_NAME}")
    print(f"Folder: {DATA_FOLDER}")
    print()
    
    # Get all DOCX files
    docx_files = sorted(DATA_FOLDER.glob("*.docx"))
    print(f"📁 Found {len(docx_files)} documents")
    print()
    
    success_count = 0
    fail_count = 0
    results = []
    
    for idx, file_path in enumerate(docx_files, 1):
        print(f"[{idx}/{len(docx_files)}] Uploading: {file_path.name}")
        
        start_time = time.time()
        try:
            result = upload_file_via_api(file_path, KB_NAME)
            elapsed = time.time() - start_time
            
            if result.get("success"):
                print(f"   ✅ Success in {elapsed:.2f}s")
                print(f"   📄 Chunks: {result.get('chunks_created', 0)}")
                print(f"   🏷️  Type: {result.get('metadata', {}).get('doc_type', 'N/A')}")
                success_count += 1
            else:
                print(f"   ❌ Failed: {result.get('message')}")
                fail_count += 1
            
            results.append({
                "filename": file_path.name,
                "success": result.get("success"),
                "elapsed": round(elapsed, 2),
                "chunks": result.get("chunks_created", 0)
            })
            
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            fail_count += 1
            results.append({
                "filename": file_path.name,
                "success": False,
                "error": str(e)
            })
        
        print()
    
    # Summary
    print("="*80)
    print("📊 UPLOAD SUMMARY")
    print("="*80)
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    
    if success_count > 0:
        total_chunks = sum(r.get("chunks", 0) for r in results if r.get("success"))
        avg_time = sum(r.get("elapsed", 0) for r in results if r.get("success")) / success_count
        print(f"📄 Total Chunks: {total_chunks}")
        print(f"⏱️  Avg Time: {avg_time:.2f}s per file")
    
    print("="*80)
    
    # Now test search
    print("\n" + "="*80)
    print("🔍 TESTING SEARCH")
    print("="*80)
    
    test_queries = [
        "ขออนุญาตมีอาวุธปืนต้องทำอย่างไร",
        "เอกสารที่ต้องใช้ในการยื่นขออนุญาต",
        "การโอนใบอนุญาตอาวุธปืน"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        response = requests.post(
            f"{SERVER_URL}/tools/search",
            json={
                "query": query,
                "kb_name": KB_NAME,
                "top_k": 3,
                "use_routing": False,
                "use_reranking": True
            }
        )
        
        result = response.json()
        
        if result.get("success"):
            results = result.get("results", [])
            print(f"   ✅ Found {len(results)} results")
            
            if results:
                top = results[0]
                print(f"   🏆 Top Result:")
                print(f"      Score: {top.get('score', 0):.4f}")
                print(f"      Text: {top.get('text', '')[:100]}...")
        else:
            print(f"   ❌ Search failed: {result.get('message')}")
    
    # Test chat
    print("\n" + "="*80)
    print("💬 TESTING CHAT")
    print("="*80)
    
    session_id = f"test_session_{int(time.time())}"
    
    chat_queries = [
        "ถ้าอยากมีปืนต้องทำอย่างไร",
        "ต้องใช้เอกสารอะไรบ้าง"
    ]
    
    for idx, query in enumerate(chat_queries, 1):
        print(f"\n[Turn {idx}] User: '{query}'")
        
        response = requests.post(
            f"{SERVER_URL}/tools/chat",
            json={
                "query": query,
                "kb_name": KB_NAME,
                "session_id": session_id,
                "top_k": 3,
                "use_routing": False,
                "use_reranking": True
            }
        )
        
        result = response.json()
        
        if result.get("success"):
            answer = result.get("answer", "")
            sources = result.get("sources", [])
            print(f"   ✅ Bot: {answer[:150]}...")
            print(f"   📚 Sources: {len(sources)} documents")
        else:
            print(f"   ❌ Chat failed: {result.get('message')}")
    
    print("\n" + "="*80)
    print("🎉 API TEST COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()
