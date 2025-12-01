# ===========================================
# MCP RAG Server v2.0 - Makefile
# ===========================================

.PHONY: help setup install dev start stop restart health test clean logs ngrok stop-ngrok

# Default target
help:
	@echo "╔════════════════════════════════════════════════╗"
	@echo "║       MCP RAG Server v2.0 - Commands           ║"
	@echo "╚════════════════════════════════════════════════╝"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Setup:"
	@echo "  setup      - First-time setup (venv + deps + qdrant)"
	@echo "  install    - Install/update dependencies"
	@echo ""
	@echo "Server:"
	@echo "  dev        - Start server in development mode (auto-reload)"
	@echo "  start      - Start server in production mode"
	@echo "  stop       - Stop server"
	@echo "  restart    - Restart server"
	@echo "  health     - Check server health"
	@echo ""
	@echo "Server + ngrok (for Dify):"
	@echo "  ngrok      - Start server + ngrok tunnel"
	@echo "  stop-ngrok - Stop server + ngrok"
	@echo ""
	@echo "Database:"
	@echo "  qdrant-up  - Start Qdrant"
	@echo "  qdrant-down- Stop Qdrant"
	@echo "  qdrant-logs- View Qdrant logs"
	@echo ""
	@echo "Testing:"
	@echo "  test       - Run all tests"
	@echo "  test-unit  - Run unit tests"
	@echo "  test-int   - Run integration tests"
	@echo ""
	@echo "Utilities:"
	@echo "  clean      - Remove cache files"
	@echo "  logs       - View server logs"
	@echo "  shell      - Activate venv shell"

# Setup
setup:
	@./scripts/setup.sh

install:
	@source venv/bin/activate && pip install -r requirements.txt

# Server commands
dev:
	@./scripts/dev.sh

start:
	@./scripts/start_server.sh

stop:
	@./scripts/stop_server.sh

restart: stop start

health:
	@./scripts/health_check.sh

# Server + ngrok
ngrok:
	@./scripts/start_with_ngrok.sh

stop-ngrok:
	@./scripts/stop_with_ngrok.sh

# Qdrant
qdrant-up:
	@docker-compose up -d
	@echo "✅ Qdrant started"

qdrant-down:
	@docker-compose down
	@echo "✅ Qdrant stopped"

qdrant-logs:
	@docker-compose logs -f qdrant

# Testing
test:
	@source venv/bin/activate && PYTHONPATH=. pytest tests/ -v

test-unit:
	@source venv/bin/activate && PYTHONPATH=. pytest tests/unit/ -v

test-int:
	@source venv/bin/activate && PYTHONPATH=. pytest tests/integration/ -v

test-full:
	@source venv/bin/activate && PYTHONPATH=. python tests/full_system_test.py

# Utilities
clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cache cleaned"

logs:
	@tail -f logs/*.log 2>/dev/null || echo "No logs found"

shell:
	@echo "Activating venv... Run: source venv/bin/activate"
	@bash --rcfile <(echo "source venv/bin/activate")
