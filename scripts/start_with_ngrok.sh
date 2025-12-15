#!/bin/bash
# ===========================================
# MCP RAG Server v2.0 - Start with ngrok
# Usage: ./scripts/start_with_ngrok.sh
# ===========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════╗"
echo "║    MCP RAG Server v2.0 + ngrok                 ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================
# 1. Cleanup old processes
# ============================================
echo -e "${YELLOW}🧹 Cleaning up old processes...${NC}"

# Kill uvicorn
pkill -9 -f "uvicorn mcp.server:app" 2>/dev/null || true

# Kill ngrok
pkill -9 ngrok 2>/dev/null || true

# Kill by port 8000 (backup)
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

echo -e "${GREEN}   ✅ Cleanup done${NC}"
sleep 2

# ============================================
# 2. Check prerequisites
# ============================================
echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"

# Check .env
if [ ! -f ".env" ]; then
    echo -e "${RED}   ❌ .env not found!${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ .env found${NC}"

# Check venv
if [ ! -d "venv" ]; then
    echo -e "${RED}   ❌ venv not found! Run: make setup${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ venv found${NC}"

# Check ngrok
if ! command -v ngrok &> /dev/null; then
    echo -e "${RED}   ❌ ngrok not found! Install: brew install ngrok${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ ngrok found${NC}"

# Check Qdrant
if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Qdrant running${NC}"
else
    echo -e "${YELLOW}   ⚠️  Qdrant not running, starting...${NC}"
    docker-compose up -d
    sleep 3
    if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ Qdrant started${NC}"
    else
        echo -e "${RED}   ❌ Failed to start Qdrant${NC}"
        exit 1
    fi
fi

# ============================================
# 3. Start MCP Server
# ============================================
echo -e "${YELLOW}🚀 Starting MCP Server on port 8000...${NC}"

source venv/bin/activate
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

nohup python -B -m uvicorn mcp.server:app --host 0.0.0.0 --port 8000 > logs/mcp_server.log 2>&1 &
SERVER_PID=$!
echo -e "${GREEN}   ✅ Server PID: $SERVER_PID${NC}"

echo -e "${YELLOW}   ⏳ Waiting for server to start...${NC}"
sleep 5

# Verify server is running
if curl -s http://localhost:8000/tools/health > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Server is healthy${NC}"
else
    echo -e "${RED}   ❌ Server failed to start!${NC}"
    echo -e "${YELLOW}   Check logs: tail -f logs/mcp_server.log${NC}"
    exit 1
fi

# ============================================
# 4. Start ngrok
# ============================================
echo -e "${YELLOW}🌐 Starting ngrok tunnel...${NC}"

nohup ngrok http 8000 > /dev/null 2>&1 &
NGROK_PID=$!
echo -e "${GREEN}   ✅ ngrok PID: $NGROK_PID${NC}"

echo -e "${YELLOW}   ⏳ Waiting for ngrok...${NC}"
sleep 5

# ============================================
# 5. Get ngrok URL
# ============================================
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tunnels = data.get('tunnels', [])
    if tunnels:
        # Prefer https
        for t in tunnels:
            if t.get('proto') == 'https':
                print(t['public_url'])
                sys.exit(0)
        print(tunnels[0]['public_url'])
    else:
        print('')
except Exception as e:
    print('')
")

# Check if URL is valid
if [ -z "$NGROK_URL" ]; then
    NGROK_URL="ERROR"
fi

# ============================================
# 6. Display Results
# ============================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ MCP RAG Server v2.0 is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$NGROK_URL" = "ERROR" ]; then
    echo -e "${RED}❌ Failed to get ngrok URL${NC}"
    echo -e "${YELLOW}   Run: curl -s http://localhost:4040/api/tunnels | python3 -m json.tool${NC}"
else
    echo -e "${CYAN}📍 Dify MCP URL:${NC}"
    echo -e "${GREEN}   ${NGROK_URL}/mcp${NC}"
    echo ""
    echo -e "${BLUE}📋 Dify Configuration:${NC}"
    echo -e "   Server Name:    ${YELLOW}mcp-rag-v2${NC}"
    echo -e "   Server Version: ${YELLOW}2.0.0${NC}"
    echo -e "   URL:            ${YELLOW}${NGROK_URL}/mcp${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📊 MCP Tools Available (8 tools):${NC}"
echo -e "   ✅ create_kb          - สร้าง Knowledge Base"
echo -e "   ✅ delete_kb          - ลบ Knowledge Base"
echo -e "   ✅ list_kbs           - แสดงรายการ KB ทั้งหมด"
echo -e "   ✅ upload_document    - อัปโหลดเอกสาร"
echo -e "   ✅ search             - ค้นหา (Hybrid Search + Reranking)"
echo -e "   ✅ chat               - สนทนา (RAG + History)"
echo -e "   ✅ clear_history      - ล้างประวัติสนทนา"
echo -e "   ✅ health             - ตรวจสอบสถานะระบบ"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📊 URLs:${NC}"
echo -e "   Local:    ${YELLOW}http://localhost:8000${NC}"
echo -e "   API Docs: ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "   Health:   ${YELLOW}http://localhost:8000/tools/health${NC}"
echo -e "   ngrok:    ${YELLOW}${NGROK_URL}${NC}"
echo ""
echo -e "${BLUE}📋 Commands:${NC}"
echo -e "   View logs:  ${YELLOW}tail -f logs/mcp_server.log${NC}"
echo -e "   Stop:       ${YELLOW}./scripts/stop_with_ngrok.sh${NC}"
echo -e "   Or:         ${YELLOW}make stop-ngrok${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"