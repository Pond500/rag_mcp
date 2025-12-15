#!/bin/bash
# ===========================================
# MCP RAG Server v2.0 - Setup Script
# First-time setup: venv + dependencies
# ===========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════╗"
echo "║       MCP RAG Server v2.0 - Setup              ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

cd "$PROJECT_ROOT"

# 1. Check Python version
echo -e "${YELLOW}1. Checking Python...${NC}"
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    echo -e "   ${GREEN}✅ Found Python 3.10${NC}"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    version=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "   ${YELLOW}⚠️  Using Python ${version} (recommend 3.10+)${NC}"
else
    echo -e "   ${RED}❌ Python not found!${NC}"
    exit 1
fi

# 2. Create venv
echo -e "${YELLOW}2. Creating virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "   ${YELLOW}⚠️  venv already exists. Recreate? (y/N)${NC}"
    read -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        $PYTHON_CMD -m venv venv
        echo -e "   ${GREEN}✅ venv recreated${NC}"
    else
        echo -e "   ${BLUE}   Using existing venv${NC}"
    fi
else
    $PYTHON_CMD -m venv venv
    echo -e "   ${GREEN}✅ venv created${NC}"
fi

# 3. Activate and install
echo -e "${YELLOW}3. Installing dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "   ${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "   ${RED}❌ requirements.txt not found!${NC}"
    exit 1
fi

# 4. Check .env
echo -e "${YELLOW}4. Checking configuration...${NC}"
if [ -f ".env" ]; then
    echo -e "   ${GREEN}✅ .env found${NC}"
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "   ${YELLOW}⚠️  Created .env from .env.example${NC}"
        echo -e "   ${YELLOW}   Please edit .env with your settings${NC}"
    else
        echo -e "   ${RED}❌ .env not found! Please create one.${NC}"
    fi
fi

# 5. Start Qdrant
echo -e "${YELLOW}5. Starting Qdrant...${NC}"
if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Qdrant already running${NC}"
else
    if [ -f "docker-compose.yml" ]; then
        docker-compose up -d
        sleep 3
        if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
            echo -e "   ${GREEN}✅ Qdrant started${NC}"
        else
            echo -e "   ${RED}❌ Failed to start Qdrant${NC}"
        fi
    else
        echo -e "   ${YELLOW}⚠️  docker-compose.yml not found${NC}"
        echo -e "   ${YELLOW}   Please start Qdrant manually${NC}"
    fi
fi

# 6. Verify setup
echo -e "${YELLOW}6. Verifying setup...${NC}"
python -c "
from src.config import get_settings
settings = get_settings()
print(f'   ✅ Config loaded')
print(f'   📦 Qdrant: {settings.qdrant.host}:{settings.qdrant.port}')
print(f'   🤖 LLM: {settings.llm.model_name}')
print(f'   🔍 Embedding: {settings.embedding.model_name}')
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✅ Setup complete!${NC}"
else
    echo -e "   ${RED}❌ Setup verification failed${NC}"
    echo -e "   ${YELLOW}   Try running: source venv/bin/activate && python -c 'from src.config import get_settings; print(get_settings())'${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Activate venv:  ${YELLOW}source venv/bin/activate${NC}"
echo -e "  2. Start server:   ${YELLOW}./scripts/start_server.sh${NC}"
echo -e "  3. Or dev mode:    ${YELLOW}./scripts/dev.sh${NC}"
echo -e "  4. Health check:   ${YELLOW}./scripts/health_check.sh${NC}"
echo ""