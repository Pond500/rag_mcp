"""
MCP Server - FastAPI Application

Provides Model Context Protocol (MCP) tools for Multi-KB RAG system.

Tools:
1. create_kb - Create a new knowledge base
2. delete_kb - Delete a knowledge base
3. list_kbs - List all knowledge bases
4. upload_document - Upload document to KB
5. search - Search in KB
6. chat - Chat with retrieval
7. clear_history - Clear chat history
8. health - Health check

Run: uvicorn mcp.server:app --reload
"""
# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import time
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import get_settings
from src.services import RAGService
from src.utils.logger import get_logger, LoggerContext, set_request_id, clear_request_id

# Import MCP Tool Tracer for observability
from src.observability import MCPToolTracer, get_mcp_tool_tracer

# Try to setup Langfuse tracing
try:
    from src.observability.langfuse_tracer import setup_langfuse_tracing
    LANGFUSE_AVAILABLE = setup_langfuse_tracing()
except Exception as e:
    LANGFUSE_AVAILABLE = False
    print(f"⚠️ Langfuse setup failed: {e}")
 
# Initialize logger with comprehensive settings
logger = get_logger(__name__, log_file="mcp_server.log", enable_json=True)

# Initialize FastAPI app
app = FastAPI(
    title="Multi-KB RAG MCP Server",
    description="Model Context Protocol server for Multi-KB RAG system with Hybrid Search",
    version="2.0.0"
)

# Add CORS middleware for Dify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing and request ID"""
    request_id = str(uuid.uuid4())
    set_request_id(request_id)
    
    start_time = time.time()
    
    # Log request start
    logger.info(f"📨 REQUEST {request.method} {request.url.path} | Client: {request.client.host if request.client else 'unknown'}")
    
    try:
        response = await call_next(request)
        elapsed = time.time() - start_time
        
        # Log response
        logger.info(f"📤 RESPONSE {response.status_code} | took {elapsed:.2f}s")
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"💥 REQUEST FAILED | took {elapsed:.2f}s | {str(e)}")
        raise
        
    finally:
        clear_request_id()

# Global service instance
_service: Optional[RAGService] = None


def get_service() -> RAGService:
    """Get or create RAG service singleton"""
    global _service
    if _service is None:
        settings = get_settings()
        _service = RAGService.from_settings(settings)
        logger.info("RAG Service initialized")
    return _service


# ========================
# Pydantic Models
# ========================

class CreateKBRequest(BaseModel):
    kb_name: str = Field(..., description="Name of knowledge base")
    description: str = Field(..., description="Description for semantic routing")
    category: str = Field(default="general", description="Category (e.g., firearms, contracts)")


class DeleteKBRequest(BaseModel):
    kb_name: str = Field(..., description="Name of knowledge base to delete")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    kb_name: str = Field(..., description="Target KB name (REQUIRED)")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results (1-20)")
    use_reranking: bool = Field(default=True, description="Use reranking for better relevance")
    include_metadata: bool = Field(default=True, description="Include source metadata (file, page, etc.)")
    deduplicate: bool = Field(default=True, description="Remove duplicate content")


class ChatRequest(BaseModel):
    query: str = Field(..., description="User query")
    kb_name: Optional[str] = Field(None, description="Target KB (if None, uses routing)")
    session_id: Optional[str] = Field(None, description="Session ID for conversation")
    top_k: int = Field(default=5, description="Number of context documents")
    use_routing: bool = Field(default=True, description="Use semantic routing")
    use_reranking: bool = Field(default=True, description="Use reranking")


class ClearHistoryRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to clear")


# Document Management Models
class ListDocumentsRequest(BaseModel):
    kb_name: str = Field(..., description="Knowledge base name")
    limit: int = Field(default=100, ge=1, le=1000, description="Max documents to return")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class GetDocumentRequest(BaseModel):
    kb_name: str = Field(..., description="Knowledge base name")
    filename: str = Field(..., description="Document filename")
    include_chunks: bool = Field(default=False, description="Include chunk contents")


class DeleteDocumentRequest(BaseModel):
    kb_name: str = Field(..., description="Knowledge base name")
    filename: str = Field(..., description="Document filename to delete")


# ========================
# MCP Protocol Endpoint (for Dify)
# ========================

# Define MCP tools schema
MCP_TOOLS = [
    {
        "name": "create_kb",
        "description": "สร้าง Knowledge Base ใหม่สำหรับเก็บเอกสาร",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {"type": "string", "description": "ชื่อ Knowledge Base (ภาษาอังกฤษ ไม่มีเว้นวรรค)"},
                "description": {"type": "string", "description": "คำอธิบาย KB (ใช้สำหรับ semantic routing)"},
                "category": {"type": "string", "description": "หมวดหมู่ เช่น legal, finance, hr", "default": "general"}
            },
            "required": ["kb_name", "description"]
        }
    },
    {
        "name": "delete_kb",
        "description": "ลบ Knowledge Base",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {"type": "string", "description": "ชื่อ KB ที่ต้องการลบ"}
            },
            "required": ["kb_name"]
        }
    },
    {
        "name": "list_kbs",
        "description": "แสดงรายการ Knowledge Base ทั้งหมด",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "upload_document",
        "description": "อัปโหลดเอกสารเข้า Knowledge Base (รองรับ PDF, DOCX, TXT)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {"type": "string", "description": "ชื่อ KB ปลายทาง"},
                "file_content": {"type": "string", "description": "เนื้อหาไฟล์ในรูปแบบ Base64"},
                "filename": {"type": "string", "description": "ชื่อไฟล์ เช่น document.pdf"},
                "content_type": {"type": "string", "description": "MIME type เช่น application/pdf"}
            },
            "required": ["kb_name", "file_content", "filename"]
        }
    },
    {
        "name": "search",
        "description": "ค้นหาเอกสารและส่ง context ให้ agent - ใช้ Hybrid Search (Dense + Sparse BM25 + RRF + Reranking) พร้อม deduplication และ metadata ครบถ้วน สำหรับให้ agent ตอบคำถามจากข้อมูลที่ได้",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string", 
                    "description": "คำค้นหาหรือคำถามที่ต้องการหาข้อมูล"
                },
                "kb_name": {
                    "type": "string", 
                    "description": "ชื่อ Knowledge Base ที่ต้องการค้นหา (REQUIRED - ไม่รองรับ routing อีกต่อไป)"
                },
                "top_k": {
                    "type": "integer", 
                    "description": "จำนวนผลลัพธ์ที่ต้องการ (1-20)", 
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "use_reranking": {
                    "type": "boolean",
                    "description": "ใช้ reranking เพื่อเพิ่มความแม่นยำ (แนะนำ: True)",
                    "default": True
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "รวม metadata (ชื่อไฟล์, หน้า, section) สำหรับอ้างอิงแหล่งที่มา",
                    "default": True
                },
                "deduplicate": {
                    "type": "boolean",
                    "description": "ลบข้อความซ้ำซ้อน (แนะนำ: True)",
                    "default": True
                }
            },
            "required": ["query", "kb_name"]
        }
    },
    {
        "name": "chat",
        "description": "สนทนากับ Knowledge Base (RAG + ประวัติการสนทนา)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "คำถามหรือข้อความ"},
                "kb_name": {"type": "string", "description": "ชื่อ KB (ถ้าไม่ระบุจะใช้ routing อัตโนมัติ)"},
                "session_id": {"type": "string", "description": "Session ID สำหรับเก็บประวัติ"},
                "top_k": {"type": "integer", "description": "จำนวนเอกสารอ้างอิง", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "clear_history",
        "description": "ล้างประวัติการสนทนา",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID ที่ต้องการล้าง"}
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "auto_routing_chat",
        "description": "สนทนาแบบ Auto-Routing - ระบบจะเลือก Knowledge Base ที่เหมาะสมที่สุดโดยอัตโนมัติจาก description ของแต่ละ KB",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "คำถามหรือข้อความของผู้ใช้"},
                "session_id": {"type": "string", "description": "Session ID สำหรับเก็บประวัติการสนทนา (ถ้าไม่ระบุจะสร้างใหม่)"},
                "top_k": {"type": "integer", "description": "จำนวนเอกสารอ้างอิง", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "health",
        "description": "ตรวจสอบสถานะระบบ",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    # Document Management Tools
    {
        "name": "list_documents",
        "description": "แสดงรายการเอกสารทั้งหมดใน Knowledge Base",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {"type": "string", "description": "ชื่อ Knowledge Base"},
                "limit": {"type": "integer", "description": "จำนวนเอกสารสูงสุดที่แสดง", "default": 100},
                "offset": {"type": "integer", "description": "ตำแหน่งเริ่มต้น (pagination)", "default": 0}
            },
            "required": ["kb_name"]
        }
    },
    {
        "name": "get_document",
        "description": "ดูรายละเอียดเอกสาร รวมถึง chunks ที่แบ่งไว้",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {"type": "string", "description": "ชื่อ Knowledge Base"},
                "filename": {"type": "string", "description": "ชื่อไฟล์เอกสาร"},
                "include_chunks": {"type": "boolean", "description": "รวมเนื้อหา chunks ทั้งหมด", "default": False}
            },
            "required": ["kb_name", "filename"]
        }
    },
    {
        "name": "delete_document",
        "description": "ลบเอกสารออกจาก Knowledge Base",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {"type": "string", "description": "ชื่อ Knowledge Base"},
                "filename": {"type": "string", "description": "ชื่อไฟล์ที่ต้องการลบ"}
            },
            "required": ["kb_name", "filename"]
        }
    },
    {
        "name": "update_document",
        "description": "อัปเดตเอกสาร (ลบของเก่าและอัปโหลดใหม่)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {"type": "string", "description": "ชื่อ Knowledge Base"},
                "filename": {"type": "string", "description": "ชื่อไฟล์เอกสาร"},
                "file_content": {"type": "string", "description": "เนื้อหาไฟล์ใหม่ในรูปแบบ Base64"}
            },
            "required": ["kb_name", "filename", "file_content"]
        }
    }
]


@app.post("/mcp", tags=["MCP Protocol"])
async def mcp_endpoint(request: Request):
    """MCP Protocol endpoint for Dify integration
    
    Handles JSON-RPC 2.0 requests from Dify:
    - initialize: Initialize MCP connection
    - tools/list: List available tools
    - tools/call: Call a tool
    - notifications/*: Handle notifications (return 202)
    """
    try:
        body = await request.json()
        method = body.get("method")
        message_id = body.get("id")
        params = body.get("params", {})
        
        logger.info("MCP request: method=%s, id=%s", method, message_id)
        
        # Handle initialize
        if method == "initialize":
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True}
                    },
                    "serverInfo": {
                        "name": "mcp-rag-v2",
                        "version": "2.0.0"
                    }
                }
            })
        
        # Handle notifications (CRITICAL: return 202 with no body!)
        elif method and method.startswith("notifications/"):
            logger.info("MCP notification: %s", method)
            return Response(status_code=202, headers={"Content-Length": "0"})
        
        # Handle tools/list
        elif method == "tools/list":
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "tools": MCP_TOOLS
                }
            })
        
        # Handle tools/call
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.info("MCP tools/call: %s with %s", tool_name, arguments)
            
            try:
                result = await execute_mcp_tool(tool_name, arguments)
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": str(result)}
                        ]
                    }
                })
            except Exception as e:
                logger.error("Tool execution error: %s", e)
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                })
        
        # Unknown method
        else:
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            })
    
    except Exception as e:
        logger.error("MCP endpoint error: %s", e)
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        })


async def execute_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Execute MCP tool and return result with tracing"""
    import base64
    import json
    
    service = get_service()
    mcp_tracer = get_mcp_tool_tracer()
    
    # Start tracing
    start_time = time.time()
    trace_context = mcp_tracer.start_tool_trace(tool_name, arguments)
    result_data = None
    error_info = None
    
    try:
        if tool_name == "create_kb":
            result_data = service.create_kb(
                kb_name=arguments["kb_name"],
                description=arguments["description"],
                category=arguments.get("category", "general")
            )
        
        elif tool_name == "delete_kb":
            result_data = service.delete_kb(arguments["kb_name"])
        
        elif tool_name == "list_kbs":
            result_data = service.list_kbs()
        
        elif tool_name == "upload_document":
            # Decode base64 content
            file_content = base64.b64decode(arguments["file_content"])
            result_data = service.upload_document(
                kb_name=arguments["kb_name"],
                filename=arguments["filename"],
                file_content=file_content
            )
        
        elif tool_name == "search":
            # v2.1: kb_name is required, no routing support
            kb_name = arguments.get("kb_name")
            if not kb_name:
                result_data = {
                    "success": False,
                    "message": "kb_name is required for search (v2.1+). Use auto_routing_chat for automatic KB selection."
                }
            else:
                result_data = service.search(
                    query=arguments["query"],
                    kb_name=kb_name,
                    top_k=arguments.get("top_k", 5),
                    use_reranking=arguments.get("use_reranking", True),
                    include_metadata=arguments.get("include_metadata", True),
                    deduplicate=arguments.get("deduplicate", True)
                )
        
        elif tool_name == "chat":
            result_data = service.chat(
                query=arguments["query"],
                kb_name=arguments.get("kb_name"),
                session_id=arguments.get("session_id"),
                top_k=arguments.get("top_k", 5),
                use_routing=arguments.get("kb_name") is None,
                use_reranking=True
            )
        
        elif tool_name == "auto_routing_chat":
            # Auto-routing chat - always use semantic routing to select best KB
            import uuid as uuid_lib
            session_id = arguments.get("session_id") or str(uuid_lib.uuid4())
            result_data = service.chat(
                query=arguments["query"],
                kb_name=None,  # Force auto-routing
                session_id=session_id,
                top_k=arguments.get("top_k", 5),
                use_routing=True,  # Always use routing
                use_reranking=True
            )
            # Add extra info about routing
            result_data["auto_routed"] = True
            result_data["session_id"] = session_id
        
        elif tool_name == "clear_history":
            result_data = service.clear_chat_history(arguments["session_id"])
        
        elif tool_name == "health":
            result_data = service.health_check()
        
        # Document Management Tools
        elif tool_name == "list_documents":
            result_data = service.list_documents(
                kb_name=arguments["kb_name"],
                limit=arguments.get("limit", 100),
                offset=arguments.get("offset", 0)
            )
        
        elif tool_name == "get_document":
            result_data = service.get_document(
                kb_name=arguments["kb_name"],
                filename=arguments["filename"],
                include_chunks=arguments.get("include_chunks", False)
            )
        
        elif tool_name == "delete_document":
            result_data = service.delete_document(
                kb_name=arguments["kb_name"],
                filename=arguments["filename"]
            )
        
        elif tool_name == "update_document":
            file_content = base64.b64decode(arguments["file_content"])
            result_data = service.update_document(
                kb_name=arguments["kb_name"],
                filename=arguments["filename"],
                file_content=file_content
            )
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return json.dumps(result_data, ensure_ascii=False)
    
    except Exception as e:
        error_info = str(e)
        logger.error(f"MCP Tool Error [{tool_name}]: {error_info}")
        raise
    
    finally:
        # End tracing - always record the trace
        duration = time.time() - start_time
        mcp_tracer.end_tool_trace(
            context=trace_context,
            result=result_data,
            error=error_info,
            duration=duration
        )


# ========================
# MCP Tools (Endpoints)
# ========================

@app.post("/tools/create_kb", tags=["KB Management"])
async def create_kb(request: CreateKBRequest):
    """Create a new knowledge base
    
    Creates a Qdrant collection with Hybrid Search (Dense + Sparse BM25) support
    and adds it to the master index for semantic routing.
    """
    with LoggerContext(logger, "CREATE_KB", kb_name=request.kb_name, category=request.category):
        try:
            service = get_service()
            result = service.create_kb(
                kb_name=request.kb_name,
                description=request.description,
                category=request.category
            )
            
            if result["success"]:
                logger.info(f"✅ KB created successfully: {request.kb_name} | category: {request.category}")
                return JSONResponse(content=result, status_code=201)
            else:
                logger.warning(f"⚠️  KB creation failed: {result.get('message')}")
                raise HTTPException(status_code=400, detail=result.get("message"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ create_kb error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/delete_kb", tags=["KB Management"])
async def delete_kb(request: DeleteKBRequest):
    """Delete a knowledge base
    
    Deletes the Qdrant collection and removes it from the master index.
    """
    with LoggerContext(logger, "DELETE_KB", kb_name=request.kb_name):
        try:
            service = get_service()
            result = service.delete_kb(request.kb_name)
            
            if result["success"]:
                logger.info(f"🗑️  KB deleted successfully: {request.kb_name}")
                return JSONResponse(content=result)
            else:
                logger.warning(f"⚠️  KB deletion failed: {result.get('message')}")
                raise HTTPException(status_code=400, detail=result.get("message"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ delete_kb error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/list_kbs", tags=["KB Management"])
async def list_kbs():
    """List all knowledge bases
    
    Returns information about all KBs including document counts and descriptions.
    """
    with LoggerContext(logger, "LIST_KBS"):
        try:
            service = get_service()
            result = service.list_kbs()
            
            kb_count = result.get("total", 0)
            logger.info(f"📋 Listed {kb_count} knowledge base(s)")
            return JSONResponse(content=result)
            
        except Exception as e:
            logger.error(f"❌ list_kbs error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/upload_document", tags=["Document Management"])
async def upload_document(
    kb_name: str = Form(..., description="Target knowledge base"),
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT)")
):
    """Upload and process a document
    
    Extracts text, chunks it, generates embeddings, and stores in the specified KB.
    Supports PDF, DOCX, and TXT formats.
    """
    with LoggerContext(logger, "UPLOAD_DOCUMENT", kb_name=kb_name, filename=file.filename):
        try:
            service = get_service()
            
            # Read file content
            file_size = 0
            file_content = await file.read()
            file_size = len(file_content)
            
            logger.info(f"📄 Uploading: {file.filename} ({file_size:,} bytes) to KB: {kb_name}")
            
            # Upload
            result = service.upload_document(
                kb_name=kb_name,
                filename=file.filename or "untitled",
                file_content=file_content
            )
            
            if result["success"]:
                chunks_count = result.get("chunks_count", 0)
                logger.info(f"✅ Document uploaded successfully: {file.filename} | {chunks_count} chunks created")
                return JSONResponse(content=result, status_code=201)
            else:
                logger.warning(f"⚠️  Document upload failed: {result.get('message')}")
                raise HTTPException(status_code=400, detail=result.get("message"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ upload_document error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


# ========================
# Document Management Endpoints
# ========================

@app.post("/tools/list_documents", tags=["Document Management"])
async def list_documents(request: ListDocumentsRequest):
    """List all documents in a Knowledge Base
    
    Returns document filenames, chunk counts, and upload dates.
    Supports pagination with limit/offset.
    """
    with LoggerContext(logger, "LIST_DOCUMENTS", kb_name=request.kb_name):
        try:
            service = get_service()
            result = service.list_documents(
                kb_name=request.kb_name,
                limit=request.limit,
                offset=request.offset
            )
            
            if result["success"]:
                doc_count = len(result.get("documents", []))
                total = result.get("total", 0)
                logger.info(f"📋 Listed {doc_count}/{total} documents in KB: {request.kb_name}")
                return JSONResponse(content=result)
            else:
                logger.warning(f"⚠️  List documents failed: {result.get('message')}")
                raise HTTPException(status_code=400, detail=result.get("message"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ list_documents error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/get_document", tags=["Document Management"])
async def get_document(request: GetDocumentRequest):
    """Get detailed info about a document
    
    Returns document metadata and optionally all chunks with their content.
    Useful for inspecting document processing results.
    """
    with LoggerContext(logger, "GET_DOCUMENT", kb_name=request.kb_name, filename=request.filename):
        try:
            service = get_service()
            result = service.get_document(
                kb_name=request.kb_name,
                filename=request.filename,
                include_chunks=request.include_chunks
            )
            
            if result["success"]:
                chunks_count = result.get("document", {}).get("chunks_count", 0)
                logger.info(f"📄 Got document: {request.filename} ({chunks_count} chunks)")
                return JSONResponse(content=result)
            else:
                logger.warning(f"⚠️  Get document failed: {result.get('message')}")
                raise HTTPException(status_code=404, detail=result.get("message"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ get_document error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/delete_document", tags=["Document Management"])
async def delete_document(request: DeleteDocumentRequest):
    """Delete a document from Knowledge Base
    
    Removes all chunks associated with the document.
    This action cannot be undone.
    """
    with LoggerContext(logger, "DELETE_DOCUMENT", kb_name=request.kb_name, filename=request.filename):
        try:
            service = get_service()
            result = service.delete_document(
                kb_name=request.kb_name,
                filename=request.filename
            )
            
            if result["success"]:
                logger.info(f"🗑️  Document deleted: {request.filename} from {request.kb_name}")
                return JSONResponse(content=result)
            else:
                logger.warning(f"⚠️  Delete document failed: {result.get('message')}")
                raise HTTPException(status_code=400, detail=result.get("message"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ delete_document error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/update_document", tags=["Document Management"])
async def update_document(
    kb_name: str = Form(..., description="Target knowledge base"),
    file: UploadFile = File(..., description="Updated document file")
):
    """Update (replace) a document in Knowledge Base
    
    Deletes the old document and uploads the new version.
    Filename must match existing document.
    """
    with LoggerContext(logger, "UPDATE_DOCUMENT", kb_name=kb_name, filename=file.filename):
        try:
            service = get_service()
            
            file_content = await file.read()
            file_size = len(file_content)
            
            logger.info(f"🔄 Updating: {file.filename} ({file_size:,} bytes) in KB: {kb_name}")
            
            result = service.update_document(
                kb_name=kb_name,
                filename=file.filename or "untitled",
                file_content=file_content
            )
            
            if result["success"]:
                chunks_count = result.get("chunks_count", 0)
                logger.info(f"✅ Document updated: {file.filename} | {chunks_count} chunks")
                return JSONResponse(content=result)
            else:
                logger.warning(f"⚠️  Update document failed: {result.get('message')}")
                raise HTTPException(status_code=400, detail=result.get("message"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ update_document error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/search", tags=["Search"])
async def search(request: SearchRequest):
    """Search for documents and return context for agent
    
    Optimized for agent/LLM consumption:
    - Hybrid Search (Dense + Sparse BM25 with RRF fusion)
    - Optional reranking for better relevance
    - Deduplication to avoid redundant information
    - Formatted context ready for agent to use
    - Rich metadata for source attribution
    
    Returns formatted context that agent can directly use to answer questions.
    """
    with LoggerContext(logger, "SEARCH", 
                      query=request.query[:50], 
                      kb_name=request.kb_name, 
                      top_k=request.top_k,
                      rerank=request.use_reranking,
                      dedup=request.deduplicate):
        try:
            service = get_service()
            result = service.search(
                query=request.query,
                kb_name=request.kb_name,
                top_k=request.top_k,
                use_reranking=request.use_reranking,
                include_metadata=request.include_metadata,
                deduplicate=request.deduplicate
            )
            
            if result["success"]:
                results_count = result.get("total_results", 0)
                sources_count = len(result.get("metadata_summary", []))
                logger.info(f"🔍 Search successful: {results_count} results from {sources_count} sources in KB: {request.kb_name}")
                return JSONResponse(content=result)
            else:
                logger.warning(f"⚠️  Search failed: {result.get('message')}")
                raise HTTPException(status_code=400, detail=result.get("message"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ search error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/chat", tags=["Chat"])
async def chat(request: ChatRequest):
    """Chat with retrieval-augmented generation (RAG)
    
    Retrieves relevant context using Hybrid Search and generates an answer using LLM.
    Supports conversation history via session_id.
    """
    with LoggerContext(logger, "CHAT", query=request.query[:50], kb_name=request.kb_name, session_id=request.session_id):
        try:
            service = get_service()
            result = service.chat(
                query=request.query,
                kb_name=request.kb_name,
                session_id=request.session_id,
                top_k=request.top_k,
                use_routing=request.use_routing,
                use_reranking=request.use_reranking
            )
            
            if result["success"]:
                kb_name = result.get("kb_name", "N/A")
                answer_length = len(result.get("answer", ""))
                logger.info(f"💬 Chat successful: {answer_length} chars from KB: {kb_name}")
                return JSONResponse(content=result)
            else:
                logger.warning(f"⚠️  Chat failed: {result.get('message')}")
                raise HTTPException(status_code=400, detail=result.get("message"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ chat error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


class AutoRoutingChatRequest(BaseModel):
    """Request for auto-routing chat"""
    query: str = Field(..., description="User question or message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation history")
    top_k: int = Field(default=5, description="Number of context documents")


@app.post("/tools/auto_routing_chat", tags=["Chat"])
async def auto_routing_chat(request: AutoRoutingChatRequest):
    """Semantic Router Auto-Routing Chat
    
    Automatically selects the best Knowledge Base based on semantic matching
    between the user's query and KB descriptions stored in master index.
    
    This is useful when:
    - You have multiple KBs and don't know which one to query
    - You want the system to intelligently route questions to the right KB
    - You're building a multi-domain chatbot
    
    How it works:
    1. User query is embedded and compared against KB descriptions
    2. The most relevant KB is selected based on semantic similarity
    3. Search is performed on the selected KB
    4. LLM generates answer using retrieved context
    """
    import uuid as uuid_lib
    
    with LoggerContext(logger, "AUTO_ROUTING_CHAT", query=request.query[:50], session_id=request.session_id):
        try:
            service = get_service()
            session_id = request.session_id or str(uuid_lib.uuid4())
            
            logger.info(f"🎯 Auto-routing query to best KB (session: {session_id[:8]}...)")
            
            result = service.chat(
                query=request.query,
                kb_name=None,  # Force auto-routing
                session_id=session_id,
                top_k=request.top_k,
                use_routing=True,  # Always use semantic routing
                use_reranking=True
            )
            
            if result["success"]:
                result["auto_routed"] = True
                result["session_id"] = session_id
                kb_name = result.get("kb_name", "N/A")
                answer_length = len(result.get("answer", ""))
                logger.info(f"✅ Auto-routed to KB: {kb_name} | {answer_length} chars generated")
                return JSONResponse(content=result)
            else:
                logger.warning(f"⚠️  Auto-routing chat failed: {result.get('message')}")
                raise HTTPException(status_code=400, detail=result.get("message"))
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ auto_routing_chat error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/clear_history", tags=["Chat"])
async def clear_history(request: ClearHistoryRequest):
    """Clear conversation history for a session
    
    Removes all conversation turns for the specified session_id.
    """
    with LoggerContext(logger, "CLEAR_HISTORY", session_id=request.session_id):
        try:
            service = get_service()
            result = service.clear_chat_history(request.session_id)
            
            logger.info(f"🗑️  Chat history cleared: {request.session_id[:8]}...")
            return JSONResponse(content=result)
            
        except Exception as e:
            logger.error(f"❌ clear_history error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/health", tags=["Admin"])
async def health():
    """Health check
    
    Returns service health status and component status (Qdrant, embeddings).
    """
    with LoggerContext(logger, "HEALTH_CHECK"):
        try:
            service = get_service()
            result = service.health_check()
            
            status_code = 200 if result["healthy"] else 503
            status_emoji = "✅" if result["healthy"] else "⚠️ "
            status_text = "healthy" if result["healthy"] else "unhealthy"
            logger.info(f"{status_emoji} Health check: {status_text}")
            return JSONResponse(content=result, status_code=status_code)
            
        except Exception as e:
            logger.error(f"❌ health check error: {str(e)}", exc_info=True)
            return JSONResponse(
                content={
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                status_code=503
            )


# =======================
# Root & Docs
# =======================

@app.get("/", tags=["Root"])
async def root():
    """API root - returns basic info"""
    logger.debug("🏠 Root endpoint accessed")
    return {
        "name": "Multi-KB RAG MCP Server",
        "version": "2.1.0",
        "description": "Model Context Protocol server for Multi-KB RAG with Hybrid Search",
        "docs_url": "/docs",
        "tools": {
            "kb_management": [
                "/tools/create_kb",
                "/tools/delete_kb",
                "/tools/list_kbs"
            ],
            "document_management": [
                "/tools/upload_document",
                "/tools/list_documents",
                "/tools/get_document",
                "/tools/delete_document",
                "/tools/update_document"
            ],
            "search_chat": [
                "/tools/search",
                "/tools/chat",
                "/tools/auto_routing_chat",
                "/tools/clear_history"
            ],
            "admin": [
                "/tools/health"
            ]
        }
    }


# ========================
# Lifecycle Events
# ========================

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("=" * 80)
    logger.info("🚀 Starting Multi-KB RAG MCP Server v2.0.0")
    logger.info("=" * 80)
    
    # Warm up service (loads models)
    try:
        service = get_service()
        health = service.health_check()
        
        if health["healthy"]:
            logger.info("✅ Service ready - all components healthy")
            for component, status in health.get("components", {}).items():
                status_emoji = "✅" if status else "❌"
                logger.info(f"  {status_emoji} {component}: {'OK' if status else 'FAILED'}")
        else:
            logger.warning(f"⚠️  Service started but some components unhealthy: {health['components']}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize service: {str(e)}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("=" * 80)
    logger.info("🛑 Shutting down Multi-KB RAG MCP Server")
    logger.info("=" * 80)


# ========================
# Error Handlers
# ========================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "mcp.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
