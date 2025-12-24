"""Observability Module

Provides tracing hooks and evaluation for RAG pipeline monitoring.
Ready for Langfuse integration by the observability team.

Components:
- Tracer: Track request lifecycle (traces, spans)
- Hooks: Pre-built hooks for RAG operations
- Evaluation: RAGAS-based evaluation metrics
"""
from .tracer import (
    ObservabilityTracer,
    TraceContext,
    SpanType,
    get_tracer,
    set_tracer,
    init_tracer,
    LoggingTracer,
    NoOpTracer
)
from .hooks import ObservabilityHooks
from .evaluation import (
    RAGASEvaluator,
    EvaluationResult,
    EvaluationInput,
    EvaluationRunner,
    evaluate_rag_response
)
from .mcp_tracer import (
    MCPToolTracer,
    ToolTraceContext,
    get_mcp_tool_tracer,
    set_mcp_tool_tracer,
    trace_mcp_tool
)

__all__ = [
    # Tracer
    "ObservabilityTracer",
    "TraceContext", 
    "SpanType",
    "get_tracer",
    "set_tracer",
    "init_tracer",
    "LoggingTracer",
    "NoOpTracer",
    # Hooks
    "ObservabilityHooks",
    # Evaluation
    "RAGASEvaluator",
    "EvaluationResult",
    "EvaluationInput",
    "EvaluationRunner",
    "evaluate_rag_response",
    # MCP Tool Tracing
    "MCPToolTracer",
    "ToolTraceContext",
    "get_mcp_tool_tracer",
    "set_mcp_tool_tracer",
    "trace_mcp_tool"
]
