#!/bin/bash
# ===========================================
# MCP RAG Server v2.0 - Development Mode
# ===========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Start with auto-reload enabled
exec "$SCRIPT_DIR/start_server.sh" --reload "$@"