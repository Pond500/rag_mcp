#!/usr/bin/env python3
"""Run MCP Server

Usage: python scripts/run_server.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
from src.utils import get_logger

logger = get_logger(__name__)


def main():
    """Run the MCP server"""
    print("="*60)
    print("Starting Multi-KB RAG MCP Server v2.0.0")
    print("="*60)
    print("\nDocs: http://localhost:8000/docs")
    print("API:  http://localhost:8000")
    print("\nPress Ctrl+C to stop\n")
    print("="*60 + "\n")
    
    try:
        uvicorn.run(
            "mcp.server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        sys.exit(0)


if __name__ == "__main__":
    main()