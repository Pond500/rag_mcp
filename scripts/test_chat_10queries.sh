#!/bin/bash

# Test script: ส่ง 10 queries ไปที่ chat endpoint
# สำหรับทดสอบ Langfuse tracing และ latency tracking

set -e

BASE_URL="http://localhost:8000"
KB_NAME="dopa_kb"
SESSION_ID="test_batch_$(date +%s)"

echo "🚀 Testing Chat Endpoint with 10 Queries"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Base URL:    $BASE_URL"
echo "KB Name:     $KB_NAME"
echo "Session ID:  $SESSION_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Array of test queries
queries=(
    "DOPA คืออะไร"
    "การจัดซื้อจัดจ้างภาครัฐมีขั้นตอนอย่างไร"
    "วิธีการสมัครใช้งาน DOPA"
    "ระบบ e-GP คืออะไร"
    "สรุปกระบวนการประกวดราคา"
    "ข้อกำหนดการยื่นเอกสารทางอิเล็กทรอนิกส์"
    "แนวทางการจัดทำ TOR"
    "ระยะเวลาการประกาศจัดซื้อจัดจ้าง"
    "หน่วยงานที่รับผิดชอบระบบ e-GP"
    "ช่องทางติดต่อสอบถามข้อมูล DOPA"
)

# Loop through queries
for i in "${!queries[@]}"; do
    query_num=$((i + 1))
    query="${queries[$i]}"
    
    echo "[$query_num/10] 🔍 Query: \"$query\""
    
    # Send request
    response=$(curl -s -X POST "$BASE_URL/tools/chat" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"$query\",
            \"kb_name\": \"$KB_NAME\",
            \"session_id\": \"${SESSION_ID}_q${query_num}\",
            \"top_k\": 5
        }")
    
    # Check success
    success=$(echo "$response" | jq -r '.success')
    
    if [ "$success" = "true" ]; then
        answer=$(echo "$response" | jq -r '.answer' | head -c 100)
        kb=$(echo "$response" | jq -r '.kb_name')
        docs=$(echo "$response" | jq -r '.documents_used')
        
        echo "   ✅ Success: KB=$kb, Docs=$docs"
        echo "   📝 Answer: ${answer}..."
        echo ""
    else
        message=$(echo "$response" | jq -r '.message')
        echo "   ❌ Failed: $message"
        echo ""
    fi
    
    # Small delay between requests
    sleep 0.5
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Completed 10 queries!"
echo "📊 Check Langfuse Dashboard at: http://103.245.166.219:3000/"
echo "🔍 Filter by session IDs: ${SESSION_ID}_q1 to ${SESSION_ID}_q10"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
