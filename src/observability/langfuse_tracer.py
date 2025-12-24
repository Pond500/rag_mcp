"""
Langfuse Tracer Implementation

ส่ง traces ไปยัง Langfuse Dashboard อัตโนมัติ
Compatible with Langfuse v3.x
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime
import time
import uuid

from .tracer import ObservabilityTracer, TraceContext, SpanType, TraceData, SpanData
from .mcp_tracer import MCPToolTracer, ToolTraceContext
from .langfuse_config import get_langfuse_config

logger = logging.getLogger(__name__)

# Lazy import Langfuse
_langfuse_client = None
_langfuse_available = False


def _get_langfuse():
    """Lazy load Langfuse client"""
    global _langfuse_client, _langfuse_available
    
    if _langfuse_client is not None:
        return _langfuse_client
    
    try:
        from langfuse import Langfuse
        
        config = get_langfuse_config()
        valid, message = config.validate()
        
        if not valid:
            logger.warning(f"Langfuse config invalid: {message}")
            _langfuse_available = False
            return None
        
        if not config.enabled:
            logger.info("Langfuse disabled by config")
            _langfuse_available = False
            return None
        
        # Remove trailing slash from host
        host = config.host.rstrip('/')
        
        _langfuse_client = Langfuse(
            host=host,
            public_key=config.public_key,
            secret_key=config.secret_key,
        )
        
        # Test connection
        _langfuse_client.auth_check()
        
        _langfuse_available = True
        logger.info(f"✅ Connected to Langfuse at {host}")
        return _langfuse_client
        
    except ImportError:
        logger.warning("langfuse package not installed. Run: pip install langfuse")
        _langfuse_available = False
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse: {e}")
        _langfuse_available = False
        return None


class LangfuseTracer(ObservabilityTracer):
    """
    Langfuse implementation of ObservabilityTracer (v3 API)
    
    ส่ง traces ไปยัง Langfuse Dashboard อัตโนมัติ
    """
    
    def __init__(self):
        self._trace_data: Dict[str, Dict[str, Any]] = {}
    
    @property
    def langfuse(self):
        return _get_langfuse()
    
    @property
    def is_available(self) -> bool:
        return self.langfuse is not None
    
    # ========================================
    # Required Abstract Methods Implementation
    # ========================================
    
    def on_trace_start(self, trace: TraceData) -> None:
        """Called when a new trace starts - store data for later"""
        self._trace_data[trace.trace_id] = {
            "trace": trace,
            "spans": {},
        }
        logger.debug(f"Started trace: {trace.trace_id} ({trace.name})")
    
    def on_trace_end(self, trace: TraceData) -> None:
        """Called when a trace ends - send to Langfuse"""
        if not self.is_available:
            self._trace_data.pop(trace.trace_id, None)
            return
        
        try:
            config = get_langfuse_config()
            
            # Create event for trace
            self.langfuse.create_event(
                name=trace.name,
                input=trace.metadata,
                output={
                    "status": trace.status,
                    "total_tokens": trace.total_tokens,
                    "total_cost": trace.total_cost,
                },
                metadata={
                    "trace_id": trace.trace_id,
                    "user_id": trace.user_id,
                    "session_id": trace.session_id,
                    "environment": config.environment,
                    "duration_ms": trace.duration_ms,
                    "error": trace.error,
                },
                level="ERROR" if trace.error else "DEFAULT",
            )
            self.langfuse.flush()
            logger.debug(f"Sent trace to Langfuse: {trace.trace_id}")
        except Exception as e:
            logger.error(f"Failed to send trace: {e}")
        finally:
            self._trace_data.pop(trace.trace_id, None)
    
    def on_span_end(self, span: SpanData, trace: TraceData) -> None:
        """Called when a span ends - send to Langfuse"""
        if not self.is_available:
            return
        
        try:
            config = get_langfuse_config()
            
            # Create event for span
            self.langfuse.create_event(
                name=span.name,
                input=span.input_data,
                output=span.output_data,
                metadata={
                    "trace_id": trace.trace_id,
                    "span_id": span.span_id,
                    "span_type": span.span_type.value,
                    "environment": config.environment,
                    "duration_ms": span.duration_ms,
                    "metrics": span.metrics,
                    "error": span.error,
                },
                level="ERROR" if span.error else "DEFAULT",
            )
            logger.debug(f"Sent span to Langfuse: {span.span_id}")
        except Exception as e:
            logger.error(f"Failed to send span: {e}")
    
    # ========================================
    # Optional Methods Override
    # ========================================
    
    def on_event(self, trace: TraceData, name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log custom event"""
        if not self.is_available:
            return
        
        try:
            self.langfuse.create_event(
                name=name,
                metadata={
                    "trace_id": trace.trace_id,
                    **(data or {}),
                },
            )
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
    
    def flush(self) -> None:
        """Flush all pending traces to Langfuse"""
        if self.is_available:
            try:
                self.langfuse.flush()
                logger.debug("Flushed traces to Langfuse")
            except Exception as e:
                logger.error(f"Failed to flush: {e}")


class LangfuseMCPToolTracer(MCPToolTracer):
    """
    Langfuse implementation for MCP Tool tracing
    
    ส่ง MCP tool traces ไปยัง Langfuse พร้อม VLM cost tracking
    """
    
    def __init__(self):
        super().__init__()
        self._current_traces: Dict[str, Any] = {}
    
    @property
    def langfuse(self):
        return _get_langfuse()
    
    @property
    def is_available(self) -> bool:
        return self.langfuse is not None
    
    def start_tool_trace(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> ToolTraceContext:
        """เริ่ม trace สำหรับ MCP tool call"""
        request_id = str(uuid.uuid4())
        
        # Store trace data
        self._current_traces[request_id] = {
            "tool_name": tool_name,
            "arguments": self._filter_sensitive_args(arguments),
        }
        
        return ToolTraceContext(
            request_id=request_id,
            tool_name=tool_name,
            arguments=arguments,
            start_time=time.time()
        )
    
    def _filter_sensitive_args(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out large/sensitive data like file_content"""
        safe_args = {}
        for key, value in arguments.items():
            if key == "file_content":
                # Don't send base64 file content
                safe_args[key] = f"<base64 data, {len(str(value))} chars>"
            elif isinstance(value, str) and len(value) > 1000:
                safe_args[key] = value[:1000] + "..."
            else:
                safe_args[key] = value
        return safe_args
    
    def _extract_vlm_cost(self, result: Optional[Dict]) -> tuple:
        """Extract VLM cost, pages, and chunks from result
        
        Returns: (vlm_cost, vlm_pages, chunks_created)
        """
        if not result:
            return None, None, None
            
        vlm_cost = result.get("vlm_cost")
        vlm_pages = result.get("pages_processed")
        chunks_created = result.get("chunks_created")
        
        return vlm_cost, vlm_pages, chunks_created
    
    def end_tool_trace(
        self,
        context: ToolTraceContext,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> None:
        """จบ trace สำหรับ MCP tool call - ส่งไป Langfuse ทันที"""
        if not self.is_available:
            return
        
        try:
            import uuid
            import psutil
            
            trace_data = self._current_traces.pop(context.request_id, {})
            arguments = trace_data.get("arguments", {})
            
            # Calculate duration
            if duration is None:
                duration = time.time() - context.start_time
            
            duration_ms = duration * 1000
            
            # Extract VLM cost if applicable
            vlm_cost = None
            vlm_pages = None
            chunks_created = None
            
            if result and context.tool_name in ["upload_document", "update_document"]:
                vlm_cost, vlm_pages, chunks_created = self._extract_vlm_cost(result)
            
            # Extract detailed info from result
            model_name = None
            input_tokens = 0
            output_tokens = 0
            kb_name = None
            query = arguments.get("query", "")
            answer = ""
            sources = []
            
            if result:
                model_name = result.get("model")
                kb_name = result.get("kb_name") or arguments.get("kb_name")
                answer = result.get("answer", "")
                sources = result.get("sources", [])
                
                # Extract tokens
                if "tokens" in result and isinstance(result["tokens"], dict):
                    tokens_data = result["tokens"]
                    input_tokens = tokens_data.get("input", 0)
                    output_tokens = tokens_data.get("output", 0)
                
                # Legacy format
                if "usage" in result and isinstance(result["usage"], dict):
                    input_tokens = result["usage"].get("prompt_tokens", 0)
                    output_tokens = result["usage"].get("completion_tokens", 0)
            
            # Get system metrics
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # Calculate text metrics
            query_length = len(query)
            query_words = len(query.split()) if query else 0
            answer_length = len(answer)
            answer_words = len(answer.split()) if answer else 0
            
            # Context metrics
            context_texts = [s.get("text", "") for s in sources] if sources else []
            context_length = sum(len(t) for t in context_texts)
            context_words = sum(len(t.split()) for t in context_texts)
            
            # Calculate derived metrics
            total_tokens = input_tokens + output_tokens
            tokens_per_second = total_tokens / duration if duration > 0 else 0
            output_input_ratio = output_tokens / input_tokens if input_tokens > 0 else 0
            avg_source_length = context_length / len(sources) if sources else 0
            
            # Generate unique ID for this generation
            generation_id = str(uuid.uuid4())
            
            # Build comprehensive metadata
            config = get_langfuse_config()
            metadata = {
                # Basic info
                "kb_name": kb_name,
                "model": model_name,
                "tool_name": context.tool_name,
                
                # Status
                "status": "error" if error else "success",
                "is_success": error is None,
                "is_error": error is not None,
                "error_message": error,
                
                # Query metrics
                "query_length": query_length,
                "query_words": query_words,
                
                # Answer metrics
                "answer_length": answer_length,
                "answer_words": answer_words,
                
                # Context/Sources metrics
                "context_length": context_length,
                "context_words": context_words,
                "sources_count": len(sources),
                "avg_source_length": round(avg_source_length, 2),
                
                # System metrics
                "memory_rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "memory_vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "memory_percent": round(process.memory_percent(), 2),
                "cpu_percent": process.cpu_percent(),
                
                # Performance metrics
                "processing_time_seconds": round(duration, 3),
                "processing_time_ms": round(duration_ms, 1),
                "tokens_per_second": round(tokens_per_second, 1),
                "output_input_ratio": round(output_input_ratio, 2),
                
                # Tracking
                "generation_id": generation_id,
                "environment": config.environment,
                "type": "mcp_tool_call",
            }
            
            # Add VLM-specific metrics
            if vlm_cost is not None:
                metadata["vlm_cost_usd"] = vlm_cost
            if vlm_pages is not None:
                metadata["vlm_pages"] = vlm_pages
            if chunks_created is not None:
                metadata["chunks_created"] = chunks_created
            
            # Build output summary
            output = {
                "success": result.get("success") if result else False,
                "message": result.get("message") if result else error,
            }
            if result:
                if "results" in result:
                    output["result_count"] = len(result.get("results", []))
                if "kbs" in result:
                    output["kb_count"] = len(result.get("kbs", []))
                if "documents" in result:
                    output["document_count"] = len(result.get("documents", []))
                if answer:
                    output["answer"] = answer[:500]  # Truncate for display
            
            # Use generation for LLM-related tools, create_event for others
            llm_tools = ["chat", "auto_routing_chat"]
            vlm_tools = ["upload_document", "update_document"]
            
            if context.tool_name in llm_tools:
                # Use generation observation with proper usage tracking
                try:
                    # Build usage_details for LLM tokens
                    usage_details = {}
                    if input_tokens > 0:
                        usage_details["input"] = input_tokens
                    if output_tokens > 0:
                        usage_details["output"] = output_tokens
                    if input_tokens > 0 or output_tokens > 0:
                        usage_details["total"] = input_tokens + output_tokens
                    
                    # Create generation observation
                    with self.langfuse.start_as_current_observation(
                        as_type="generation",
                        name=f"mcp_tool:{context.tool_name}",
                        model=model_name,
                        input=trace_data.get("arguments"),
                        output=output,
                        metadata=metadata,
                        usage_details=usage_details if usage_details else None,
                        level="ERROR" if error else "DEFAULT",
                    ) as generation:
                        # Generation is auto-ended by context manager
                        pass
                        
                except Exception as gen_error:
                    logger.warning(f"Generation tracking failed: {gen_error}, falling back to event")
                    # Fallback to event
                    self.langfuse.create_event(
                        name=f"mcp_tool:{context.tool_name}",
                        input=trace_data.get("arguments"),
                        output=output,
                        metadata={
                            **metadata,
                            "model": model_name,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        },
                        level="ERROR" if error else "DEFAULT",
                    )
            elif context.tool_name in vlm_tools:
                # Use generation for VLM with cost tracking
                try:
                    cost_details = {}
                    vlm_total_cost = vlm_cost or 0.0
                    if vlm_total_cost > 0:
                        cost_details["total"] = vlm_total_cost
                    
                    with self.langfuse.start_as_current_observation(
                        as_type="generation",
                        name=f"mcp_tool:{context.tool_name}",
                        model=model_name or "gemini-2.0-flash",
                        input=trace_data.get("arguments"),
                        output=output,
                        metadata=metadata,
                        cost_details=cost_details if cost_details else None,
                        level="ERROR" if error else "DEFAULT",
                    ) as generation:
                        pass
                        
                except Exception as gen_error:
                    logger.warning(f"VLM generation tracking failed: {gen_error}")
                    self.langfuse.create_event(
                        name=f"mcp_tool:{context.tool_name}",
                        input=trace_data.get("arguments"),
                        output=output,
                        metadata={**metadata, "vlm_cost_usd": vlm_cost or 0.0},
                        level="ERROR" if error else "DEFAULT",
                    )
            else:
                # Create event for non-LLM tools
                self.langfuse.create_event(
                    name=f"mcp_tool:{context.tool_name}",
                    input=trace_data.get("arguments"),
                    output=output,
                    metadata=metadata,
                    level="ERROR" if error else "DEFAULT",
                )
            
            # Flush to send immediately
            self.langfuse.flush()
            
            # Log summary
            cost_str = f" | VLM cost: ${vlm_cost:.4f}" if vlm_cost else ""
            logger.info(f"📊 MCP Trace: {context.tool_name} | {duration_ms:.0f}ms{cost_str}")
            
        except Exception as e:
            logger.error(f"Failed to end MCP tool trace: {e}")


# ===========================================
# 🚀 Easy Setup Function
# ===========================================

def setup_langfuse_tracing() -> bool:
    """
    ตั้งค่า Langfuse tracing ทั้งหมดในครั้งเดียว
    
    เรียกใช้ตอน server startup:
    
        from src.observability.langfuse_tracer import setup_langfuse_tracing
        setup_langfuse_tracing()
    
    Returns:
        True if Langfuse is available, False otherwise
    """
    from . import set_tracer
    from .mcp_tracer import set_mcp_tool_tracer
    from .langfuse_config import print_connection_info
    
    # Show connection info
    print_connection_info()
    
    # Setup tracers
    tracer = LangfuseTracer()
    mcp_tracer = LangfuseMCPToolTracer()
    
    if tracer.is_available:
        set_tracer(tracer)
        set_mcp_tool_tracer(mcp_tracer)
        logger.info("✅ Langfuse tracing enabled for all MCP tools")
        print("\n🎉 Langfuse tracing is ACTIVE!")
        print("   All MCP tool calls will be tracked.\n")
        return True
    else:
        logger.warning("⚠️ Langfuse not available, using NoOp tracer")
        print("\n⚠️ Langfuse tracing is DISABLED")
        print("   Check your configuration.\n")
        return False


def test_langfuse_connection() -> bool:
    """
    ทดสอบการเชื่อมต่อ Langfuse
    
    Returns:
        True if connection successful
    """
    from .langfuse_config import print_connection_info
    
    print("\n🔍 Testing Langfuse connection...\n")
    print_connection_info()
    
    langfuse = _get_langfuse()
    if langfuse:
        try:
            # Test auth
            langfuse.auth_check()
            
            # Send a test event using v3 API
            event = langfuse.create_event(
                name="connection_test",
                input={"test": True, "timestamp": datetime.now().isoformat()},
                output={"status": "success"},
                metadata={"source": "mcp-rag-v2", "type": "connection_test"},
            )
            langfuse.flush()
            
            print("\n✅ Connection test PASSED!")
            print("   Check your Langfuse dashboard for 'connection_test' event.\n")
            return True
        except Exception as e:
            print(f"\n❌ Connection test FAILED: {e}\n")
            return False
    else:
        print("\n❌ Could not connect to Langfuse\n")
        return False
