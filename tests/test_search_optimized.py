#!/usr/bin/env python3
"""
Test script for optimized /tools/search endpoint

Tests the new agent-optimized search functionality:
- Required kb_name
- Deduplication
- Formatted context
- Metadata summary
"""
import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8001"


def test_search_basic(kb_name: str = "gun_law", query: str = "อาวุธปืนต้องขออนุญาตอย่างไร"):
    """Test basic search with required kb_name"""
    print(f"\n{'='*60}")
    print(f"TEST 1: Basic Search")
    print(f"{'='*60}")
    
    payload = {
        "query": query,
        "kb_name": kb_name,
        "top_k": 5,
        "use_reranking": True,
        "deduplicate": True,
        "include_metadata": True
    }
    
    print(f"\n📤 Request:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    response = requests.post(f"{BASE_URL}/tools/search", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Success!")
        print(f"   KB: {result.get('kb_name')}")
        print(f"   Total Results: {result.get('total_results')}")
        print(f"   Sources: {len(result.get('metadata_summary', []))}")
        
        # Show first result
        if result.get('results'):
            first = result['results'][0]
            print(f"\n📄 First Result:")
            print(f"   Rank: {first['rank']}")
            print(f"   Score: {first['score']}")
            print(f"   Content: {first['content'][:100]}...")
            if first.get('metadata'):
                print(f"   Source: {first['metadata'].get('source_file', 'N/A')}")
                print(f"   Page: {first['metadata'].get('page', 'N/A')}")
        
        # Show formatted context preview
        if result.get('formatted_context'):
            context = result['formatted_context']
            print(f"\n📚 Formatted Context (preview):")
            print(context[:300] + "...")
        
        # Show metadata summary
        if result.get('metadata_summary'):
            print(f"\n📊 Metadata Summary:")
            for meta in result['metadata_summary']:
                print(f"   - {meta['source_file']}: {meta['chunk_count']} chunks")
        
        return result
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        return None


def test_search_without_deduplication(kb_name: str = "gun_law", query: str = "อาวุธปืน"):
    """Compare results with/without deduplication"""
    print(f"\n{'='*60}")
    print(f"TEST 2: Deduplication Comparison")
    print(f"{'='*60}")
    
    # Without deduplication
    payload_no_dedup = {
        "query": query,
        "kb_name": kb_name,
        "top_k": 10,
        "deduplicate": False
    }
    
    print(f"\n📤 Request (deduplicate=False):")
    response1 = requests.post(f"{BASE_URL}/tools/search", json=payload_no_dedup)
    
    # With deduplication
    payload_with_dedup = {
        "query": query,
        "kb_name": kb_name,
        "top_k": 10,
        "deduplicate": True
    }
    
    print(f"📤 Request (deduplicate=True):")
    response2 = requests.post(f"{BASE_URL}/tools/search", json=payload_with_dedup)
    
    if response1.status_code == 200 and response2.status_code == 200:
        result1 = response1.json()
        result2 = response2.json()
        
        count_without = result1.get('total_results', 0)
        count_with = result2.get('total_results', 0)
        
        print(f"\n📊 Comparison:")
        print(f"   Without deduplication: {count_without} results")
        print(f"   With deduplication: {count_with} results")
        print(f"   Removed: {count_without - count_with} duplicates")
        
        if count_without > count_with:
            print(f"   ✅ Deduplication working! Removed {count_without - count_with} duplicates")
        else:
            print(f"   ℹ️  No duplicates found in this query")
    else:
        print(f"❌ Error in one or both requests")


def test_search_different_top_k(kb_name: str = "gun_law", query: str = "ใบอนุญาต"):
    """Test different top_k values"""
    print(f"\n{'='*60}")
    print(f"TEST 3: Different top_k Values")
    print(f"{'='*60}")
    
    for top_k in [3, 5, 10]:
        payload = {
            "query": query,
            "kb_name": kb_name,
            "top_k": top_k,
            "use_reranking": True
        }
        
        response = requests.post(f"{BASE_URL}/tools/search", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n   top_k={top_k}: {result.get('total_results')} results")
            
            # Show average score
            if result.get('results'):
                avg_score = sum(r['score'] for r in result['results']) / len(result['results'])
                print(f"              Average score: {avg_score:.4f}")


def test_search_agent_integration(kb_name: str = "gun_law", query: str = "การขออนุญาตอาวุธปืน"):
    """Demonstrate agent integration pattern"""
    print(f"\n{'='*60}")
    print(f"TEST 4: Agent Integration Pattern")
    print(f"{'='*60}")
    
    # Step 1: Search
    payload = {
        "query": query,
        "kb_name": kb_name,
        "top_k": 5,
        "use_reranking": True,
        "deduplicate": True,
        "include_metadata": True
    }
    
    print(f"\n🔍 Searching: '{query}' in KB: '{kb_name}'")
    response = requests.post(f"{BASE_URL}/tools/search", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        
        # Step 2: Agent receives formatted context
        formatted_context = result.get('formatted_context', '')
        
        print(f"\n📚 Agent receives formatted context:")
        print("="*60)
        print(formatted_context[:500] + "...")
        print("="*60)
        
        # Step 3: Agent constructs prompt
        user_question = query
        prompt = f"""Based on the following retrieved context, answer the user's question comprehensively:

{formatted_context}

Question: {user_question}

Instructions:
1. Answer based ONLY on the provided context
2. Cite sources using the [N] reference numbers
3. If the context doesn't contain enough information, say so

Answer:"""
        
        print(f"\n🤖 Agent constructs prompt:")
        print("="*60)
        print(prompt[:600] + "...")
        print("="*60)
        
        print(f"\n✅ Ready to send to LLM!")
        print(f"   Context length: {len(formatted_context)} chars")
        print(f"   Number of sources: {len(result.get('metadata_summary', []))}")
        print(f"   Prompt length: {len(prompt)} chars")
        
        return prompt
    else:
        print(f"❌ Search failed: {response.status_code}")
        return None


def test_list_kbs():
    """Helper: List available KBs"""
    print(f"\n{'='*60}")
    print(f"Available Knowledge Bases")
    print(f"{'='*60}")
    
    response = requests.post(f"{BASE_URL}/tools/list_kbs", json={})
    
    if response.status_code == 200:
        result = response.json()
        kbs = result.get('kbs', [])
        
        print(f"\nTotal: {len(kbs)} KBs")
        for kb in kbs:
            print(f"   - {kb['name']}: {kb.get('description', 'No description')}")
            print(f"     Documents: {kb.get('document_count', 0)}, Chunks: {kb.get('chunk_count', 0)}")
        
        return kbs
    else:
        print(f"❌ Error: {response.status_code}")
        return []


if __name__ == "__main__":
    print("\n🚀 Testing Optimized /tools/search Endpoint")
    print("="*60)
    
    # First, check what KBs are available
    kbs = test_list_kbs()
    
    if not kbs:
        print("\n⚠️  No KBs found. Please create one first.")
        print("\nExample:")
        print('  curl -X POST "http://localhost:8001/tools/create_kb" \\')
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'{"kb_name": "test_kb", "description": "Test KB"}\'')
        exit(1)
    
    # Use first available KB for testing
    test_kb = kbs[0]['name']
    print(f"\n✅ Using KB: '{test_kb}' for tests")
    
    # Run tests
    test_search_basic(kb_name=test_kb, query="test query")
    test_search_without_deduplication(kb_name=test_kb, query="test")
    test_search_different_top_k(kb_name=test_kb, query="test")
    test_search_agent_integration(kb_name=test_kb, query="test question")
    
    print(f"\n{'='*60}")
    print("✅ All tests completed!")
    print(f"{'='*60}\n")
