"""Observability Tracer - Base Interface

This module provides the base tracer interface for RAG pipeline observability.
The observability team can extend this to integrate with Langfuse or other platforms.

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                      RAG Pipeline                                │
    │  Query → Retrieval → Reranking → LLM Generation → Response      │
    └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                  ObservabilityTracer                             │
    │  - start_trace()     - Track entire request lifecycle           │
    │  - start_span()      - Track individual operations              │
    │  - log_event()       - Log important events                     │
    │  - record_metrics()  - Record custom metrics                    │
    └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │              LangfuseTracer (implement by observe team)          │
    │  - Connects to Langfuse cloud/self-hosted                       │
    │  - Sends traces, spans, metrics                                 │
    │  - Manages prompt versioning                                    │
    └─────────────────────────────────────────────────────────────────┘

Usage for RAG team (already integrated):
    ```python
    from src.observability import get_tracer
    
    tracer = get_tracer()
    
    with tracer.trace("chat_request", user_id="user123") as trace:
        with trace.span("retrieval", span_type=SpanType.RETRIEVAL) as span:
            results = retriever.search(query)
            span.set_output({"results_count": len(results)})
        
        with trace.span("llm_generation", span_type=SpanType.LLM) as span:
            span.set_input({"prompt": prompt, "model": "gpt-4"})
            response = llm.generate(prompt)
            span.set_output({"response": response, "tokens": 500})
    ```

Usage for Observe team (to implement):
    ```python
    from src.observability import ObservabilityTracer, set_tracer
    from langfuse import Langfuse
    
    class LangfuseTracer(ObservabilityTracer):
        def __init__(self):
            self.langfuse = Langfuse()
        
        def start_trace(self, name, **kwargs):
            return LangfuseTraceContext(self.langfuse.trace(name=name, **kwargs))
        
        # ... implement other methods
    
    # Register the tracer
    set_tracer(LangfuseTracer())
    ```
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import uuid
import time
import logging

logger = logging.getLogger(__name__)


class SpanType(Enum):
    """Types of spans in RAG pipeline"""
    RETRIEVAL = "retrieval"          # Vector search, hybrid search
    RERANKING = "reranking"          # Reranking results
    LLM = "llm"                      # LLM generation
    EMBEDDING = "embedding"          # Embedding generation
    ROUTING = "routing"              # KB routing
    DOCUMENT_PROCESSING = "document_processing"  # Doc extraction, chunking
    TOOL_CALL = "tool_call"          # MCP tool execution
    CUSTOM = "custom"                # Custom spans


@dataclass
class SpanData:
    """Data collected for a span"""
    span_id: str
    name: str
    span_type: SpanType
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    # Input/Output
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    
    # Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: str = "running"  # running, success, error
    error: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Parent span
    parent_span_id: Optional[str] = None


@dataclass  
class TraceData:
    """Data collected for a trace (entire request lifecycle)"""
    trace_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    # User info
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Request info
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    
    # Spans
    spans: List[SpanData] = field(default_factory=list)
    
    # Aggregated metrics
    total_tokens: int = 0
    total_cost: float = 0.0
    
    # Status
    status: str = "running"
    error: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


class SpanContext:
    """Context manager for a span
    
    Provides methods to record span data during execution.
    """
    
    def __init__(self, tracer: 'ObservabilityTracer', span_data: SpanData, trace_context: 'TraceContext'):
        self.tracer = tracer
        self.data = span_data
        self.trace_context = trace_context
        self._start_time = time.time()
    
    def set_input(self, input_data: Dict[str, Any]) -> 'SpanContext':
        """Set span input data"""
        self.data.input_data = input_data
        return self
    
    def set_output(self, output_data: Dict[str, Any]) -> 'SpanContext':
        """Set span output data"""
        self.data.output_data = output_data
        return self
    
    def set_metadata(self, key: str, value: Any) -> 'SpanContext':
        """Set metadata"""
        self.data.metadata[key] = value
        return self
    
    def record_metric(self, name: str, value: Union[int, float]) -> 'SpanContext':
        """Record a metric"""
        self.data.metrics[name] = value
        return self
    
    def record_tokens(self, input_tokens: int = 0, output_tokens: int = 0, total_tokens: int = 0) -> 'SpanContext':
        """Record token usage (for LLM spans)"""
        self.data.metrics["input_tokens"] = input_tokens
        self.data.metrics["output_tokens"] = output_tokens
        self.data.metrics["total_tokens"] = total_tokens or (input_tokens + output_tokens)
        self.trace_context.data.total_tokens += self.data.metrics["total_tokens"]
        return self
    
    def record_cost(self, cost: float) -> 'SpanContext':
        """Record cost (for LLM spans)"""
        self.data.metrics["cost"] = cost
        self.trace_context.data.total_cost += cost
        return self
    
    def set_error(self, error: str) -> 'SpanContext':
        """Mark span as error"""
        self.data.status = "error"
        self.data.error = error
        return self
    
    def __enter__(self) -> 'SpanContext':
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.data.end_time = datetime.now()
        self.data.duration_ms = (time.time() - self._start_time) * 1000
        
        if exc_type:
            self.data.status = "error"
            self.data.error = str(exc_val)
        elif self.data.status == "running":
            self.data.status = "success"
        
        # Callback to tracer
        self.tracer.on_span_end(self.data, self.trace_context.data)
        
        return False  # Don't suppress exceptions


class TraceContext:
    """Context manager for a trace (entire request)
    
    Usage:
        with tracer.trace("chat", user_id="user123") as trace:
            trace.set_input({"query": "..."})
            
            with trace.span("retrieval", SpanType.RETRIEVAL) as span:
                results = search(...)
                span.set_output({"count": len(results)})
            
            trace.set_output({"response": "..."})
    """
    
    def __init__(self, tracer: 'ObservabilityTracer', trace_data: TraceData):
        self.tracer = tracer
        self.data = trace_data
        self._start_time = time.time()
        self._current_span: Optional[SpanContext] = None
    
    def set_input(self, input_data: Dict[str, Any]) -> 'TraceContext':
        """Set trace input"""
        self.data.input_data = input_data
        return self
    
    def set_output(self, output_data: Dict[str, Any]) -> 'TraceContext':
        """Set trace output"""
        self.data.output_data = output_data
        return self
    
    def set_user(self, user_id: str, session_id: Optional[str] = None) -> 'TraceContext':
        """Set user info"""
        self.data.user_id = user_id
        if session_id:
            self.data.session_id = session_id
        return self
    
    def add_tag(self, tag: str) -> 'TraceContext':
        """Add a tag"""
        self.data.tags.append(tag)
        return self
    
    def set_metadata(self, key: str, value: Any) -> 'TraceContext':
        """Set metadata"""
        self.data.metadata[key] = value
        return self
    
    def span(self, name: str, span_type: SpanType = SpanType.CUSTOM) -> SpanContext:
        """Create a new span within this trace"""
        span_data = SpanData(
            span_id=str(uuid.uuid4()),
            name=name,
            span_type=span_type,
            start_time=datetime.now(),
            parent_span_id=self._current_span.data.span_id if self._current_span else None
        )
        self.data.spans.append(span_data)
        
        span_context = SpanContext(self.tracer, span_data, self)
        return span_context
    
    def set_error(self, error: str) -> 'TraceContext':
        """Mark trace as error"""
        self.data.status = "error"
        self.data.error = error
        return self
    
    def __enter__(self) -> 'TraceContext':
        self.tracer.on_trace_start(self.data)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.data.end_time = datetime.now()
        self.data.duration_ms = (time.time() - self._start_time) * 1000
        
        if exc_type:
            self.data.status = "error"
            self.data.error = str(exc_val)
        elif self.data.status == "running":
            self.data.status = "success"
        
        # Callback to tracer
        self.tracer.on_trace_end(self.data)
        
        return False


class ObservabilityTracer(ABC):
    """Abstract base class for observability tracers
    
    The observe team should extend this class to integrate with Langfuse.
    
    Required methods to implement:
    - on_trace_start: Called when a trace starts
    - on_trace_end: Called when a trace ends  
    - on_span_end: Called when a span ends
    
    Optional methods to override:
    - on_event: Log custom events
    - on_feedback: Record user feedback
    - flush: Flush any buffered data
    """
    
    @abstractmethod
    def on_trace_start(self, trace: TraceData) -> None:
        """Called when a new trace starts
        
        Args:
            trace: The trace data with initial info
        """
        pass
    
    @abstractmethod
    def on_trace_end(self, trace: TraceData) -> None:
        """Called when a trace ends
        
        Args:
            trace: The complete trace data with all spans
        """
        pass
    
    @abstractmethod
    def on_span_end(self, span: SpanData, trace: TraceData) -> None:
        """Called when a span ends
        
        Args:
            span: The completed span data
            trace: The parent trace data
        """
        pass
    
    def on_event(self, name: str, data: Dict[str, Any], trace_id: Optional[str] = None) -> None:
        """Log a custom event
        
        Args:
            name: Event name
            data: Event data
            trace_id: Optional trace ID to associate with
        """
        pass
    
    def on_feedback(
        self, 
        trace_id: str, 
        score: float, 
        comment: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Record user feedback for a trace
        
        Args:
            trace_id: The trace to attach feedback to
            score: Feedback score (0-1)
            comment: Optional feedback comment
            user_id: Optional user ID
        """
        pass
    
    def flush(self) -> None:
        """Flush any buffered data
        
        Call this before shutdown to ensure all data is sent.
        """
        pass
    
    def trace(
        self,
        name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> TraceContext:
        """Start a new trace
        
        Args:
            name: Trace name (e.g., "chat", "search", "upload_document")
            user_id: Optional user identifier
            session_id: Optional session identifier
            metadata: Optional metadata dict
            tags: Optional tags list
            
        Returns:
            TraceContext for use in with statement
        """
        trace_data = TraceData(
            trace_id=str(uuid.uuid4()),
            name=name,
            start_time=datetime.now(),
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or []
        )
        return TraceContext(self, trace_data)


class NoOpTracer(ObservabilityTracer):
    """No-operation tracer - does nothing but satisfies interface
    
    This is the default tracer when no observability platform is configured.
    All data is discarded.
    """
    
    def on_trace_start(self, trace: TraceData) -> None:
        pass
    
    def on_trace_end(self, trace: TraceData) -> None:
        pass
    
    def on_span_end(self, span: SpanData, trace: TraceData) -> None:
        pass


class LoggingTracer(ObservabilityTracer):
    """Simple logging tracer - logs all traces to Python logger
    
    Useful for development and debugging.
    """
    
    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level
        self.logger = logging.getLogger("observability.tracer")
    
    def on_trace_start(self, trace: TraceData) -> None:
        self.logger.log(
            self.log_level,
            f"🔵 TRACE START: {trace.name} | id={trace.trace_id[:8]} | user={trace.user_id}"
        )
    
    def on_trace_end(self, trace: TraceData) -> None:
        status_emoji = "✅" if trace.status == "success" else "❌"
        self.logger.log(
            self.log_level,
            f"{status_emoji} TRACE END: {trace.name} | id={trace.trace_id[:8]} | "
            f"duration={trace.duration_ms:.0f}ms | spans={len(trace.spans)} | "
            f"tokens={trace.total_tokens} | cost=${trace.total_cost:.4f}"
        )
    
    def on_span_end(self, span: SpanData, trace: TraceData) -> None:
        status_emoji = "✅" if span.status == "success" else "❌"
        self.logger.log(
            self.log_level,
            f"  {status_emoji} SPAN: {span.name} ({span.span_type.value}) | "
            f"duration={span.duration_ms:.0f}ms | metrics={span.metrics}"
        )
    
    def on_event(self, name: str, data: Dict[str, Any], trace_id: Optional[str] = None) -> None:
        self.logger.log(self.log_level, f"📌 EVENT: {name} | data={data}")
    
    def on_feedback(
        self,
        trace_id: str,
        score: float,
        comment: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        self.logger.log(
            self.log_level,
            f"👍 FEEDBACK: trace={trace_id[:8]} | score={score} | comment={comment}"
        )


# Global tracer instance
_tracer: Optional[ObservabilityTracer] = None


def get_tracer() -> ObservabilityTracer:
    """Get the global tracer instance
    
    Returns NoOpTracer if no tracer has been set.
    """
    global _tracer
    if _tracer is None:
        _tracer = NoOpTracer()
    return _tracer


def set_tracer(tracer: ObservabilityTracer) -> None:
    """Set the global tracer instance
    
    Call this at application startup to configure observability.
    
    Example:
        # For development (logs to console)
        set_tracer(LoggingTracer())
        
        # For production (Langfuse - implement by observe team)
        set_tracer(LangfuseTracer(api_key="..."))
    """
    global _tracer
    _tracer = tracer
    logger.info(f"Observability tracer set: {type(tracer).__name__}")


def init_tracer(mode: str = "noop", **kwargs) -> ObservabilityTracer:
    """Initialize tracer based on mode
    
    Args:
        mode: "noop", "logging", or "langfuse"
        **kwargs: Additional arguments for tracer
        
    Returns:
        Configured tracer instance
    """
    if mode == "noop":
        tracer = NoOpTracer()
    elif mode == "logging":
        tracer = LoggingTracer(**kwargs)
    elif mode == "langfuse":
        # Placeholder - observe team will implement LangfuseTracer
        raise NotImplementedError(
            "LangfuseTracer not implemented yet. "
            "Please see src/observability/langfuse_tracer.py.example"
        )
    else:
        raise ValueError(f"Unknown tracer mode: {mode}")
    
    set_tracer(tracer)
    return tracer
