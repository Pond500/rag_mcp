"""MCP Tool Tracing

Automatic tracing for all MCP tool calls.
Captures: tool name, arguments, result, duration, errors, and costs.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Callable
from functools import wraps
from datetime import datetime
import time
import logging
import json
import uuid

from .tracer import get_tracer, SpanType

logger = logging.getLogger(__name__)


class MCPToolTracer:
    """Tracer for MCP tool calls
    
    Automatically traces all MCP tool executions with:
    - Tool name and arguments
    - Execution duration
    - Success/failure status
    - Result summary
    - VLM costs (for upload with progressive processor)
    
    Usage:
        tracer = MCPToolTracer()
        
        # Wrap tool execution
        with tracer.trace_tool("search", {"query": "...", "kb_name": "..."}) as ctx:
            result = execute_search(...)
            ctx.set_result(result)
        
        # Or use decorator
        @tracer.traced_tool
        async def execute_mcp_tool(tool_name: str, arguments: dict):
            ...
    """
    
    def __init__(self):
        self.tool_stats: Dict[str, Dict[str, Any]] = {}
        self._active_traces: Dict[str, 'ToolTraceContext'] = {}
    
    def start_tool_trace(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> 'ToolTraceContext':
        """Start a tool trace and return context for later completion
        
        This method is compatible with LangfuseMCPToolTracer interface.
        """
        context = ToolTraceContext(
            tracer=self,
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id,
            session_id=session_id,
            start_time=time.time()
        )
        self._active_traces[context.request_id] = context
        logger.debug(f"Started trace for {tool_name}: {context.request_id}")
        return context
    
    def end_tool_trace(
        self,
        context: 'ToolTraceContext',
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        **kwargs
    ) -> None:
        """End a tool trace and record statistics
        
        This method is compatible with LangfuseMCPToolTracer interface.
        """
        if context is None:
            return
            
        duration_ms = (time.time() - context._start_time) * 1000
        success = error is None and (result.get("success", False) if result else False)
        
        # Extract cost if present
        cost = 0.0
        if result:
            cost = result.get("vlm_cost", 0.0) or 0.0
        
        # Record statistics
        self.record_tool_call(
            tool_name=context.tool_name,
            duration_ms=duration_ms,
            success=success,
            cost=cost
        )
        
        # Remove from active traces
        self._active_traces.pop(context.request_id, None)
        
        # Log summary
        status = "✓" if success else "✗"
        logger.info(f"📊 MCP Trace: {context.tool_name} {status} | {duration_ms:.0f}ms")
    
    def trace_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> 'ToolTraceContext':
        """Create a trace context for a tool call"""
        return ToolTraceContext(
            tracer=self,
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id,
            session_id=session_id
        )
    
    def record_tool_call(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        cost: float = 0.0
    ):
        """Record tool call statistics"""
        if tool_name not in self.tool_stats:
            self.tool_stats[tool_name] = {
                "total_calls": 0,
                "success_count": 0,
                "error_count": 0,
                "total_duration_ms": 0,
                "total_cost": 0.0
            }
        
        stats = self.tool_stats[tool_name]
        stats["total_calls"] += 1
        stats["total_duration_ms"] += duration_ms
        stats["total_cost"] += cost
        
        if success:
            stats["success_count"] += 1
        else:
            stats["error_count"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tool call statistics"""
        return {
            "tools": self.tool_stats,
            "summary": {
                "total_calls": sum(s["total_calls"] for s in self.tool_stats.values()),
                "total_cost": sum(s["total_cost"] for s in self.tool_stats.values()),
                "avg_duration_ms": (
                    sum(s["total_duration_ms"] for s in self.tool_stats.values()) /
                    max(1, sum(s["total_calls"] for s in self.tool_stats.values()))
                )
            }
        }


class ToolTraceContext:
    """Context manager for tool tracing"""
    
    def __init__(
        self,
        tracer: 'MCPToolTracer' = None,
        tool_name: str = "",
        arguments: Dict[str, Any] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        # Additional fields for Langfuse tracer
        request_id: Optional[str] = None,
        start_time: Optional[float] = None,
    ):
        self.mcp_tracer = tracer
        self.tool_name = tool_name
        self.arguments = arguments or {}
        self.user_id = user_id
        self.session_id = session_id
        self.request_id = request_id or str(uuid.uuid4())
        
        self._start_time: float = start_time or 0
        self._trace_ctx = None
        self._span_ctx = None
        self._result: Optional[Dict] = None
        self._error: Optional[str] = None
        self._cost: float = 0.0
        self._vlm_cost: float = 0.0
        self._tokens: Dict[str, int] = {}
    
    @property
    def start_time(self) -> float:
        """Get start time"""
        return self._start_time
    
    def set_result(self, result: Any) -> 'ToolTraceContext':
        """Set the tool result"""
        if isinstance(result, str):
            try:
                self._result = json.loads(result)
            except:
                self._result = {"raw": result[:500]}
        elif isinstance(result, dict):
            self._result = result
        else:
            self._result = {"raw": str(result)[:500]}
        
        # Extract cost info from result if available
        if isinstance(self._result, dict):
            # VLM extraction cost
            if "extraction_cost" in self._result:
                self._vlm_cost = self._result.get("extraction_cost", 0) or 0
            if "metadata" in self._result and isinstance(self._result["metadata"], dict):
                self._vlm_cost = self._result["metadata"].get("extraction_cost", 0) or 0
            
            # Token info
            if "total_tokens" in self._result:
                self._tokens["total"] = self._result["total_tokens"]
        
        return self
    
    def set_error(self, error: str) -> 'ToolTraceContext':
        """Set error message"""
        self._error = error
        return self
    
    def set_cost(self, cost: float) -> 'ToolTraceContext':
        """Set additional cost"""
        self._cost = cost
        return self
    
    def set_vlm_cost(self, cost: float) -> 'ToolTraceContext':
        """Set VLM extraction cost"""
        self._vlm_cost = cost
        return self
    
    def set_tokens(self, input_tokens: int = 0, output_tokens: int = 0) -> 'ToolTraceContext':
        """Set token usage"""
        self._tokens = {
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens
        }
        return self
    
    def __enter__(self) -> 'ToolTraceContext':
        self._start_time = time.time()
        
        # Get observability tracer
        obs_tracer = get_tracer()
        
        # Start trace
        self._trace_ctx = obs_tracer.trace(
            name=f"mcp_tool:{self.tool_name}",
            user_id=self.user_id,
            session_id=self.session_id,
            metadata={
                "tool_name": self.tool_name,
                "arguments_keys": list(self.arguments.keys())
            },
            tags=["mcp_tool", self.tool_name, self._get_tool_category()]
        )
        self._trace_ctx.__enter__()
        
        # Set input (sanitize sensitive data)
        sanitized_args = self._sanitize_arguments(self.arguments)
        self._trace_ctx.set_input(sanitized_args)
        
        # Start tool execution span
        self._span_ctx = self._trace_ctx.span(
            f"execute_{self.tool_name}",
            SpanType.TOOL_CALL
        )
        self._span_ctx.__enter__()
        self._span_ctx.set_input(sanitized_args)
        
        logger.info(f"🔧 MCP Tool Start: {self.tool_name}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self._start_time) * 1000
        success = exc_type is None and self._error is None
        total_cost = self._cost + self._vlm_cost
        
        # Handle exception
        if exc_type:
            self._error = str(exc_val)
            self._span_ctx.set_error(self._error)
            self._trace_ctx.set_error(self._error)
        
        # Set output
        output_data = {
            "success": success,
            "duration_ms": duration_ms,
            "cost": total_cost
        }
        
        if self._result:
            # Include summary of result
            if isinstance(self._result, dict):
                output_data["result_keys"] = list(self._result.keys())
                if "success" in self._result:
                    output_data["result_success"] = self._result["success"]
                if "chunks_count" in self._result:
                    output_data["chunks_count"] = self._result["chunks_count"]
                if "total_results" in self._result:
                    output_data["results_count"] = self._result["total_results"]
        
        if self._error:
            output_data["error"] = self._error
        
        if self._vlm_cost > 0:
            output_data["vlm_cost"] = self._vlm_cost
        
        if self._tokens:
            output_data["tokens"] = self._tokens
        
        # End span
        self._span_ctx.set_output(output_data)
        self._span_ctx.record_metric("duration_ms", duration_ms)
        if total_cost > 0:
            self._span_ctx.record_cost(total_cost)
        if self._tokens.get("total"):
            self._span_ctx.record_tokens(
                self._tokens.get("input", 0),
                self._tokens.get("output", 0),
                self._tokens.get("total", 0)
            )
        self._span_ctx.__exit__(exc_type, exc_val, exc_tb)
        
        # End trace
        self._trace_ctx.set_output(output_data)
        self._trace_ctx.__exit__(exc_type, exc_val, exc_tb)
        
        # Record stats
        self.mcp_tracer.record_tool_call(
            self.tool_name,
            duration_ms,
            success,
            total_cost
        )
        
        # Log
        status_emoji = "✅" if success else "❌"
        cost_str = f" | cost=${total_cost:.4f}" if total_cost > 0 else ""
        logger.info(
            f"{status_emoji} MCP Tool End: {self.tool_name} | "
            f"duration={duration_ms:.0f}ms{cost_str}"
        )
        
        return False  # Don't suppress exceptions
    
    def _get_tool_category(self) -> str:
        """Get tool category for tagging"""
        kb_tools = ["create_kb", "delete_kb", "list_kbs"]
        doc_tools = ["upload_document", "list_documents", "get_document", "delete_document", "update_document"]
        search_tools = ["search", "chat", "auto_routing_chat"]
        
        if self.tool_name in kb_tools:
            return "kb_management"
        elif self.tool_name in doc_tools:
            return "document_management"
        elif self.tool_name in search_tools:
            return "search_chat"
        else:
            return "admin"
    
    def _sanitize_arguments(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize arguments for logging (remove large/sensitive data)"""
        sanitized = {}
        
        for key, value in args.items():
            if key in ["file_content", "content"]:
                # Don't log file content, just size
                if isinstance(value, (str, bytes)):
                    sanitized[key] = f"<{len(value)} bytes>"
                else:
                    sanitized[key] = "<content>"
            elif key in ["api_key", "password", "secret"]:
                sanitized[key] = "<redacted>"
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "..."
            else:
                sanitized[key] = value
        
        return sanitized


# Global MCP tool tracer instance
_mcp_tool_tracer: Optional[MCPToolTracer] = None


def get_mcp_tool_tracer() -> MCPToolTracer:
    """Get the global MCP tool tracer"""
    global _mcp_tool_tracer
    if _mcp_tool_tracer is None:
        _mcp_tool_tracer = MCPToolTracer()
    return _mcp_tool_tracer


def set_mcp_tool_tracer(tracer: MCPToolTracer) -> None:
    """Set the global MCP tool tracer
    
    Used to replace default tracer with Langfuse tracer.
    
    Usage:
        from src.observability.langfuse_tracer import LangfuseMCPToolTracer
        set_mcp_tool_tracer(LangfuseMCPToolTracer())
    """
    global _mcp_tool_tracer
    _mcp_tool_tracer = tracer
    logger.info(f"MCP Tool Tracer set to: {type(tracer).__name__}")


def trace_mcp_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> ToolTraceContext:
    """Convenience function to trace an MCP tool call
    
    Usage:
        with trace_mcp_tool("search", {"query": "...", "kb_name": "..."}) as ctx:
            result = service.search(...)
            ctx.set_result(result)
    """
    return get_mcp_tool_tracer().trace_tool(
        tool_name=tool_name,
        arguments=arguments,
        user_id=user_id,
        session_id=session_id
    )
