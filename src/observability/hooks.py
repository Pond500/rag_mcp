"""Observability Hooks - Pre-integrated hooks for RAG pipeline

This module provides ready-to-use hooks that are already integrated
into the RAG pipeline. The observe team just needs to set the tracer.

These hooks automatically capture:
- Search operations (retrieval, reranking)
- Chat operations (full RAG pipeline)
- Document processing (upload, chunking)
- LLM calls (generation, token usage, cost)
"""
from __future__ import annotations
from typing import Any, Dict, Optional, List, Callable
from functools import wraps
import time
import logging

from .tracer import (
    get_tracer,
    SpanType,
    TraceContext,
    SpanContext
)

logger = logging.getLogger(__name__)


class ObservabilityHooks:
    """Pre-built hooks for RAG pipeline observability
    
    These hooks are designed to be called from RAG service methods.
    They automatically create traces and spans with relevant data.
    
    Usage in RAG service:
        ```python
        from src.observability import ObservabilityHooks
        
        hooks = ObservabilityHooks()
        
        def search(self, query: str, kb_name: str, ...):
            with hooks.trace_search(query, kb_name) as trace:
                # Retrieval
                with trace.span_retrieval(kb_name) as span:
                    results = self.retriever.retrieve(...)
                    span.record_results(results)
                
                # Reranking  
                with trace.span_reranking() as span:
                    reranked = self.reranker.rerank(...)
                    span.record_results(reranked)
                
                trace.set_output({"results": reranked})
            
            return results
        ```
    """
    
    def trace_search(
        self,
        query: str,
        kb_name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        top_k: int = 5,
        use_reranking: bool = True,
        **kwargs
    ) -> 'SearchTraceContext':
        """Create a trace for search operation"""
        tracer = get_tracer()
        trace_ctx = tracer.trace(
            name="search",
            user_id=user_id,
            session_id=session_id,
            metadata={
                "query": query,
                "kb_name": kb_name,
                "top_k": top_k,
                "use_reranking": use_reranking,
                **kwargs
            },
            tags=["search", f"kb:{kb_name}"]
        )
        return SearchTraceContext(trace_ctx)
    
    def trace_chat(
        self,
        query: str,
        kb_name: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        use_routing: bool = False,
        **kwargs
    ) -> 'ChatTraceContext':
        """Create a trace for chat operation"""
        tracer = get_tracer()
        trace_ctx = tracer.trace(
            name="chat",
            user_id=user_id,
            session_id=session_id,
            metadata={
                "query": query,
                "kb_name": kb_name,
                "use_routing": use_routing,
                **kwargs
            },
            tags=["chat"] + ([f"kb:{kb_name}"] if kb_name else ["auto_routing"])
        )
        return ChatTraceContext(trace_ctx)
    
    def trace_upload(
        self,
        kb_name: str,
        filename: str,
        file_size: int,
        user_id: Optional[str] = None,
        **kwargs
    ) -> 'UploadTraceContext':
        """Create a trace for document upload operation"""
        tracer = get_tracer()
        trace_ctx = tracer.trace(
            name="upload_document",
            user_id=user_id,
            metadata={
                "kb_name": kb_name,
                "filename": filename,
                "file_size": file_size,
                **kwargs
            },
            tags=["upload", f"kb:{kb_name}"]
        )
        return UploadTraceContext(trace_ctx)
    
    def trace_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: Optional[str] = None,
        **kwargs
    ) -> TraceContext:
        """Create a trace for MCP tool execution"""
        tracer = get_tracer()
        return tracer.trace(
            name=f"tool:{tool_name}",
            user_id=user_id,
            metadata={
                "tool_name": tool_name,
                "arguments": arguments,
                **kwargs
            },
            tags=["mcp_tool", tool_name]
        )


class SearchTraceContext:
    """Specialized trace context for search operations"""
    
    def __init__(self, trace_ctx: TraceContext):
        self._trace = trace_ctx
    
    def __enter__(self) -> 'SearchTraceContext':
        self._trace.__enter__()
        return self
    
    def __exit__(self, *args):
        return self._trace.__exit__(*args)
    
    def set_input(self, query: str, **kwargs) -> 'SearchTraceContext':
        self._trace.set_input({"query": query, **kwargs})
        return self
    
    def set_output(self, results: List[Dict], **kwargs) -> 'SearchTraceContext':
        self._trace.set_output({
            "results_count": len(results),
            "results": results[:3],  # Only first 3 for brevity
            **kwargs
        })
        return self
    
    def span_retrieval(self, kb_name: str, search_type: str = "hybrid") -> 'RetrievalSpanContext':
        """Create retrieval span"""
        span = self._trace.span("retrieval", SpanType.RETRIEVAL)
        span.set_metadata("kb_name", kb_name)
        span.set_metadata("search_type", search_type)
        return RetrievalSpanContext(span)
    
    def span_reranking(self, model: str = "bge-reranker") -> 'RerankingSpanContext':
        """Create reranking span"""
        span = self._trace.span("reranking", SpanType.RERANKING)
        span.set_metadata("model", model)
        return RerankingSpanContext(span)
    
    def span_embedding(self, model: str = "bge-m3") -> SpanContext:
        """Create embedding span"""
        span = self._trace.span("embedding", SpanType.EMBEDDING)
        span.set_metadata("model", model)
        return span


class ChatTraceContext:
    """Specialized trace context for chat operations"""
    
    def __init__(self, trace_ctx: TraceContext):
        self._trace = trace_ctx
    
    def __enter__(self) -> 'ChatTraceContext':
        self._trace.__enter__()
        return self
    
    def __exit__(self, *args):
        return self._trace.__exit__(*args)
    
    def set_input(self, query: str, history: Optional[List] = None, **kwargs) -> 'ChatTraceContext':
        self._trace.set_input({
            "query": query,
            "history_length": len(history) if history else 0,
            **kwargs
        })
        return self
    
    def set_output(self, response: str, sources: Optional[List] = None, **kwargs) -> 'ChatTraceContext':
        self._trace.set_output({
            "response": response[:500],  # Truncate for storage
            "response_length": len(response),
            "sources_count": len(sources) if sources else 0,
            **kwargs
        })
        return self
    
    def span_routing(self) -> 'RoutingSpanContext':
        """Create routing span (for auto-routing)"""
        span = self._trace.span("routing", SpanType.ROUTING)
        return RoutingSpanContext(span)
    
    def span_retrieval(self, kb_name: str) -> 'RetrievalSpanContext':
        """Create retrieval span"""
        span = self._trace.span("retrieval", SpanType.RETRIEVAL)
        span.set_metadata("kb_name", kb_name)
        return RetrievalSpanContext(span)
    
    def span_reranking(self) -> 'RerankingSpanContext':
        """Create reranking span"""
        return RerankingSpanContext(self._trace.span("reranking", SpanType.RERANKING))
    
    def span_llm(self, model: str) -> 'LLMSpanContext':
        """Create LLM generation span"""
        span = self._trace.span("llm_generation", SpanType.LLM)
        span.set_metadata("model", model)
        return LLMSpanContext(span, self._trace)


class UploadTraceContext:
    """Specialized trace context for upload operations"""
    
    def __init__(self, trace_ctx: TraceContext):
        self._trace = trace_ctx
    
    def __enter__(self) -> 'UploadTraceContext':
        self._trace.__enter__()
        return self
    
    def __exit__(self, *args):
        return self._trace.__exit__(*args)
    
    def set_input(self, filename: str, file_size: int, **kwargs) -> 'UploadTraceContext':
        self._trace.set_input({
            "filename": filename,
            "file_size": file_size,
            **kwargs
        })
        return self
    
    def set_output(self, chunks_count: int, **kwargs) -> 'UploadTraceContext':
        self._trace.set_output({
            "chunks_count": chunks_count,
            **kwargs
        })
        return self
    
    def span_extraction(self, method: str = "docling") -> SpanContext:
        """Create text extraction span"""
        span = self._trace.span("text_extraction", SpanType.DOCUMENT_PROCESSING)
        span.set_metadata("method", method)
        return span
    
    def span_chunking(self, chunk_size: int = 1000) -> SpanContext:
        """Create chunking span"""
        span = self._trace.span("chunking", SpanType.DOCUMENT_PROCESSING)
        span.set_metadata("chunk_size", chunk_size)
        return span
    
    def span_embedding(self, model: str = "bge-m3") -> SpanContext:
        """Create embedding span"""
        span = self._trace.span("embedding", SpanType.EMBEDDING)
        span.set_metadata("model", model)
        return span
    
    def span_vlm(self, model: str, tier: str) -> 'LLMSpanContext':
        """Create VLM extraction span (for progressive processor)"""
        span = self._trace.span("vlm_extraction", SpanType.LLM)
        span.set_metadata("model", model)
        span.set_metadata("tier", tier)
        return LLMSpanContext(span, self._trace)


class RetrievalSpanContext:
    """Specialized span for retrieval operations"""
    
    def __init__(self, span: SpanContext):
        self._span = span
    
    def __enter__(self) -> 'RetrievalSpanContext':
        self._span.__enter__()
        return self
    
    def __exit__(self, *args):
        return self._span.__exit__(*args)
    
    def set_query(self, query: str) -> 'RetrievalSpanContext':
        self._span.set_input({"query": query})
        return self
    
    def record_results(
        self,
        results: List[Dict],
        dense_count: Optional[int] = None,
        sparse_count: Optional[int] = None
    ) -> 'RetrievalSpanContext':
        self._span.set_output({
            "results_count": len(results),
            "top_score": results[0].get("score", 0) if results else 0
        })
        self._span.record_metric("results_count", len(results))
        if dense_count is not None:
            self._span.record_metric("dense_results", dense_count)
        if sparse_count is not None:
            self._span.record_metric("sparse_results", sparse_count)
        return self


class RerankingSpanContext:
    """Specialized span for reranking operations"""
    
    def __init__(self, span: SpanContext):
        self._span = span
    
    def __enter__(self) -> 'RerankingSpanContext':
        self._span.__enter__()
        return self
    
    def __exit__(self, *args):
        return self._span.__exit__(*args)
    
    def set_input(self, query: str, candidates_count: int) -> 'RerankingSpanContext':
        self._span.set_input({
            "query": query,
            "candidates_count": candidates_count
        })
        return self
    
    def record_results(self, results: List[Dict]) -> 'RerankingSpanContext':
        self._span.set_output({
            "results_count": len(results),
            "top_score": results[0].get("score", 0) if results else 0
        })
        self._span.record_metric("reranked_count", len(results))
        return self


class RoutingSpanContext:
    """Specialized span for KB routing operations"""
    
    def __init__(self, span: SpanContext):
        self._span = span
    
    def __enter__(self) -> 'RoutingSpanContext':
        self._span.__enter__()
        return self
    
    def __exit__(self, *args):
        return self._span.__exit__(*args)
    
    def set_query(self, query: str) -> 'RoutingSpanContext':
        self._span.set_input({"query": query})
        return self
    
    def record_result(
        self,
        selected_kb: str,
        confidence: float,
        candidates: Optional[List[Dict]] = None
    ) -> 'RoutingSpanContext':
        self._span.set_output({
            "selected_kb": selected_kb,
            "confidence": confidence,
            "candidates_count": len(candidates) if candidates else 0
        })
        self._span.record_metric("routing_confidence", confidence)
        return self


class LLMSpanContext:
    """Specialized span for LLM operations"""
    
    def __init__(self, span: SpanContext, trace: TraceContext):
        self._span = span
        self._trace = trace
    
    def __enter__(self) -> 'LLMSpanContext':
        self._span.__enter__()
        return self
    
    def __exit__(self, *args):
        return self._span.__exit__(*args)
    
    def set_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> 'LLMSpanContext':
        self._span.set_input({
            "prompt": prompt[:1000],  # Truncate
            "prompt_length": len(prompt),
            "system_prompt_length": len(system_prompt) if system_prompt else 0
        })
        return self
    
    def set_response(self, response: str) -> 'LLMSpanContext':
        self._span.set_output({
            "response": response[:500],  # Truncate
            "response_length": len(response)
        })
        return self
    
    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        total_tokens: Optional[int] = None,
        cost: Optional[float] = None
    ) -> 'LLMSpanContext':
        self._span.record_tokens(input_tokens, output_tokens, total_tokens)
        if cost is not None:
            self._span.record_cost(cost)
        return self
    
    def record_model_info(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> 'LLMSpanContext':
        self._span.set_metadata("model", model)
        self._span.set_metadata("temperature", temperature)
        if max_tokens:
            self._span.set_metadata("max_tokens", max_tokens)
        return self


# Decorator for easy tracing
def trace_function(
    name: Optional[str] = None,
    span_type: SpanType = SpanType.CUSTOM
):
    """Decorator to automatically trace a function
    
    Usage:
        @trace_function("my_operation", SpanType.CUSTOM)
        def my_function(arg1, arg2):
            return result
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            trace_name = name or func.__name__
            
            with tracer.trace(trace_name) as trace:
                with trace.span(trace_name, span_type) as span:
                    span.set_input({"args": str(args)[:200], "kwargs": str(kwargs)[:200]})
                    
                    try:
                        result = func(*args, **kwargs)
                        span.set_output({"result": str(result)[:200]})
                        return result
                    except Exception as e:
                        span.set_error(str(e))
                        raise
        
        return wrapper
    return decorator
