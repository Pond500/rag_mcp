#!/bin/bash
# ===========================================
# MCP RAG Server v2.0 - Stop Script
# ===========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Stopping MCP Server...${NC}"

# Kill uvicorn processes
if pgrep -f "uvicorn mcp.server:app" > /dev/null; then
    pkill -f "uvicorn mcp.server:app"
    echo -e "${GREEN}✅ MCP Server stopped${NC}"
else
    echo -e "${YELLOW}⚠️  MCP Server was not running${NC}"
fi

# Optional: Stop Qdrant
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
