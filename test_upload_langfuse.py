#!/usr/bin/env python3
"""Test upload document and verify VLM cost is sent to Langfuse"""

import requests
import base64
import json
import sys

def upload_document():
    # Read PDF file
    pdf_path = '/Users/pond500/RAG/mcp_rag_v2/data/reportfidf2566.pdf'
    print(f'📂 Reading: {pdf_path}')
    
    try:
        with open(pdf_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        print(f'❌ File not found: {pdf_path}')
        return False
    
    # Prepare request
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {
            'name': 'upload_document',
            'arguments': {
                'kb_name': 'dopa_kb',
                'file_content': content,
                'filename': 'reportfidf2566.pdf',
                'description': 'ทดสอบ upload เพื่อดู VLM cost ใน Langfuse'
            }
        }
    }
    
    # Send request
    print('📤 Uploading document to MCP server...')
    try:
        response = requests.post(
            'http://localhost:8000/mcp',
            json=payload,
            timeout=500
        )
        result = response.json()
    except requests.exceptions.Timeout:
        print('❌ Request timeout (>500s)')
        return False
    except Exception as e:
        print(f'❌ Request failed: {e}')
        return False
    
    # Parse result
    if 'result' in result:
        content_text = result['result']['content'][0]['text']
        data = json.loads(content_text)
        
        print('\n✅ Upload successful!')
        print(f'📄 Document: {data.get("document_name")}')
        print(f'📊 Pages: {data.get("pages_processed")}')
        print(f'📝 Chunks: {data.get("chunks_created")}')
        print(f'💰 VLM Cost: ${data.get("vlm_cost", 0):.4f}')
        print(f'⏱️  Processing time: {data.get("processing_time_seconds", 0):.1f}s')
        
        vlm_cost = data.get('vlm_cost', 0)
        if vlm_cost > 0:
            print(f'\n✅ VLM cost detected: ${vlm_cost:.4f}')
            print('📊 Check Langfuse dashboard for trace with:')
            print(f'   - tool_name: upload_document')
            print(f'   - vlm_cost_usd: {vlm_cost}')
            print(f'   - vlm_pages: {data.get("pages_processed")}')
            print(f'   - chunks_created: {data.get("chunks_created")}')
        else:
            print('\n⚠️  VLM cost is 0 - might be cached or error')
        
        return True
    else:
        error = result.get('error', {})
        print(f'\n❌ Error: {error.get("message")}')
        return False

if __name__ == '__main__':
    success = upload_document()
    sys.exit(0 if success else 1)
