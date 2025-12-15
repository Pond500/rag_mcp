#!/bin/bash
# Start Hybrid Document Processing Web Interface

echo "=================================================="
echo "  🚀 Hybrid Document Processor - Web Interface"
echo "=================================================="
echo ""
echo "Supports:"
echo "  📊 Excel (.xlsx, .xls) → MarkItDown (fast!)"
echo "  📽️  PowerPoint (.pptx, .ppt) → MarkItDown"
echo "  📄 PDF (.pdf) → Docling (OCR + layout)"
echo "  📝 Word (.docx, .doc) → Docling"
echo "  📋 Text (.txt, .md) → Simple"
echo ""
echo "Starting server on http://localhost:5001 ..."
echo ""

cd "$(dirname "$0")/.."
python web/app.py
