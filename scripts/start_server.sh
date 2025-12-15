#!/bin/bash
# ===========================================
# MCP RAG Server v2.0 - Start Script
# ===========================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════╗"
echo "║       MCP RAG Server v2.0 - Starting...        ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

# Change to project root
cd "$PROJECT_ROOT"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found!${NC}"
    echo "   Please copy .env.example to .env and configure it."
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3.10 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if Qdrant is running
echo -e "${YELLOW}🔍 Checking Qdrant connection...${NC}"
if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Qdrant is running${NC}"
else
    echo -e "${RED}❌ Qdrant is not running!${NC}"
    echo -e "${YELLOW}   Starting Qdrant with docker-compose...${NC}"
    docker-compose up -d
    sleep 3
    
    if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Qdrant started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Qdrant. Please check docker-compose.${NC}"
        exit 1
    fi
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-false}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --reload)
            RELOAD="true"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --host HOST    Host to bind (default: 0.0.0.0)"
            echo "  --port PORT    Port to bind (default: 8000)"
            echo "  --reload       Enable auto-reload for development"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Start server
echo ""
echo -e "${GREEN}🚀 Starting MCP Server...${NC}"
echo -e "${BLUE}   Host: ${HOST}${NC}"
echo -e "${BLUE}   Port: ${PORT}${NC}"
echo -e "${BLUE}   Reload: ${RELOAD}${NC}"
echo ""
echo -e "${GREEN}📚 API Documentation: http://${HOST}:${PORT}/docs${NC}"
echo -e "${GREEN}🔧 Health Check: http://${HOST}:${PORT}/tools/health${NC}"
echo ""

if [ "$RELOAD" = "true" ]; then
    python -m uvicorn mcp.server:app --host "$HOST" --port "$PORT" --reload
else
    python -m uvicorn mcp.server:app --host "$HOST" --port "$PORT"
fi