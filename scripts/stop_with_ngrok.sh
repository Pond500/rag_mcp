#!/bin/bash
# ===========================================
# MCP RAG Server v2.0 - Stop Server + ngrok
# Usage: ./scripts/stop_with_ngrok.sh
# ===========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════╗"
echo "║    Stopping MCP RAG Server + ngrok             ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

# Kill MCP Server
echo -e "${YELLOW}🛑 Stopping MCP Server...${NC}"
if pkill -9 -f "uvicorn mcp.server:app" 2>/dev/null; then
    echo -e "${GREEN}   ✅ MCP Server stopped${NC}"
else
    echo -e "${YELLOW}   ⚠️  MCP Server was not running${NC}"
fi

# Kill ngrok
echo -e "${YELLOW}🌐 Stopping ngrok...${NC}"
if pkill -9 ngrok 2>/dev/null; then
    echo -e "${GREEN}   ✅ ngrok stopped${NC}"
else
    echo -e "${YELLOW}   ⚠️  ngrok was not running${NC}"
fi

# Kill by port (backup)
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ All processes stopped!${NC}"
echo ""

# Ask about Qdrant
read -p "Stop Qdrant as well? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    cd "$PROJECT_ROOT"
    docker-compose down
    echo -e "${GREEN}✅ Qdrant stopped${NC}"
fi

echo -e "${GREEN}👋 Done!${NC}"