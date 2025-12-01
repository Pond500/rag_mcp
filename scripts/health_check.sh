#!/bin/bash
# ===========================================
# MCP RAG Server v2.0 - Health Check
# ===========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

HOST="${1:-localhost}"
PORT="${2:-8000}"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════╗"
echo "║           MCP RAG Server - Health Check        ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check Qdrant
echo -e "${YELLOW}1. Checking Qdrant...${NC}"
if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
    collections=$(curl -s http://localhost:6333/collections | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('result', {}).get('collections', [])))" 2>/dev/null || echo "?")
    echo -e "   ${GREEN}✅ Qdrant: OK (${collections} collections)${NC}"
else
    echo -e "   ${RED}❌ Qdrant: NOT RUNNING${NC}"
fi

# Check MCP Server
echo -e "${YELLOW}2. Checking MCP Server...${NC}"
response=$(curl -s "http://${HOST}:${PORT}/tools/health" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$response" ]; then
    healthy=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('healthy', False))" 2>/dev/null)
    if [ "$healthy" = "True" ]; then
        echo -e "   ${GREEN}✅ MCP Server: HEALTHY${NC}"
    else
        echo -e "   ${YELLOW}⚠️  MCP Server: UNHEALTHY${NC}"
    fi
    echo -e "   ${BLUE}   Response: ${response}${NC}"
else
    echo -e "   ${RED}❌ MCP Server: NOT RUNNING${NC}"
fi

# Check endpoints
echo -e "${YELLOW}3. Testing API Endpoints...${NC}"
endpoints=("/" "/docs" "/tools/health" "/tools/list_kbs")
for endpoint in "${endpoints[@]}"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://${HOST}:${PORT}${endpoint}" 2>/dev/null)
    if [ "$status" = "200" ]; then
        echo -e "   ${GREEN}✅ GET ${endpoint} -> ${status}${NC}"
    else
        echo -e "   ${RED}❌ GET ${endpoint} -> ${status}${NC}"
    fi
done

echo ""
echo -e "${BLUE}📚 API Docs: http://${HOST}:${PORT}/docs${NC}"
