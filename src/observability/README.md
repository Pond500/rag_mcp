# 🔍 Observability Module

โมดูลสำหรับ tracing และ monitoring RAG pipeline - พร้อมให้ทีม Observe เชื่อมต่อ Langfuse

## 📁 โครงสร้างไฟล์

```
src/observability/
├── __init__.py              # Public exports
├── tracer.py                # Base tracer interface + implementations
├── hooks.py                 # Pre-built hooks for RAG pipeline
├── langfuse_tracer.py.example  # Template สำหรับ Langfuse integration
└── README.md                # เอกสารนี้
```

## 🎯 สถาปัตยกรรม

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG Pipeline                              │
│  Query → Routing → Retrieval → Reranking → LLM → Response   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  ObservabilityHooks                          │
│  Pre-integrated hooks ที่เรียกใช้อัตโนมัติใน RAG service      │
│  - trace_search()  - trace_chat()  - trace_upload()         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  ObservabilityTracer (Interface)             │
│  - on_trace_start()    - on_trace_end()                     │
│  - on_span_end()       - on_feedback()                      │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
      ┌──────────┐   ┌───────────┐   ┌─────────────┐
      │ NoOpTracer│   │LoggingTracer│   │LangfuseTracer│
      │ (default) │   │ (dev/debug)│   │ (production) │
      └──────────┘   └───────────┘   └─────────────┘
```

## 🚀 Quick Start สำหรับทีม Observe

### 1. ติดตั้ง Langfuse
```bash
pip install langfuse
```

### 2. สร้าง LangfuseTracer
```bash
cp src/observability/langfuse_tracer.py.example src/observability/langfuse_tracer.py
```

### 3. Implement methods ใน langfuse_tracer.py
```python
from langfuse import Langfuse
from src.observability.tracer import ObservabilityTracer, TraceData, SpanData

class LangfuseTracer(ObservabilityTracer):
    def __init__(self):
        self.langfuse = Langfuse()
        self._traces = {}
    
    def on_trace_start(self, trace: TraceData) -> None:
        self._traces[trace.trace_id] = self.langfuse.trace(
            id=trace.trace_id,
            name=trace.name,
            user_id=trace.user_id,
            session_id=trace.session_id,
            input=trace.input_data
        )
    
    def on_trace_end(self, trace: TraceData) -> None:
        if trace.trace_id in self._traces:
            self._traces[trace.trace_id].update(
                output=trace.output_data,
                metadata={"tokens": trace.total_tokens, "cost": trace.total_cost}
            )
    
    def on_span_end(self, span: SpanData, trace: TraceData) -> None:
        lf_trace = self._traces.get(trace.trace_id)
        if lf_trace:
            if span.span_type.value == "llm":
                lf_trace.generation(name=span.name, input=span.input_data, output=span.output_data)
            else:
                lf_trace.span(name=span.name, input=span.input_data, output=span.output_data)
```

### 4. เปิดใช้งาน
```python
# ใน mcp/server.py หรือ main.py
from src.observability import set_tracer
from src.observability.langfuse_tracer import LangfuseTracer

# Set environment variables
# LANGFUSE_PUBLIC_KEY=pk-...
# LANGFUSE_SECRET_KEY=sk-...

set_tracer(LangfuseTracer())
```

## 📊 Data ที่ถูก Capture อัตโนมัติ

### Search Operations
| Field | Description |
|-------|-------------|
| `query` | Search query |
| `kb_name` | Target Knowledge Base |
| `results_count` | Number of results |
| `retrieval_time` | Retrieval duration (ms) |
| `reranking_time` | Reranking duration (ms) |

### Chat Operations
| Field | Description |
|-------|-------------|
| `query` | User question |
| `kb_name` | Selected KB (or auto-routed) |
| `response` | LLM response |
| `input_tokens` | Input token count |
| `output_tokens` | Output token count |
| `cost` | LLM cost ($) |
| `sources` | Retrieved sources |

### Upload Operations
| Field | Description |
|-------|-------------|
| `filename` | Document filename |
| `file_size` | File size in bytes |
| `chunks_count` | Number of chunks created |
| `extraction_method` | docling, vlm, markitdown |
| `embedding_time` | Embedding duration (ms) |

## 🔧 การใช้งานใน Code ที่มีอยู่แล้ว

RAG Service ถูก integrate ไว้แล้ว (ทีม observe ไม่ต้องแก้):

```python
# src/services/rag_service.py
from src.observability import ObservabilityHooks

class RAGService:
    def __init__(self):
        self.obs = ObservabilityHooks()
    
    def search(self, query: str, kb_name: str, ...):
        # Tracing ถูกเรียกอัตโนมัติ
        with self.obs.trace_search(query, kb_name) as trace:
            with trace.span_retrieval(kb_name) as span:
                results = self.retriever.retrieve(query)
                span.record_results(results)
            
            with trace.span_reranking() as span:
                reranked = self.reranker.rerank(results)
                span.record_results(reranked)
            
            trace.set_output({"results": reranked})
        
        return reranked
```

## 🧪 ทดสอบ

### Development Mode (Logging)
```python
from src.observability import init_tracer

# เปิด logging tracer
init_tracer("logging")

# ทดสอบ search
service.search("กฎหมายปืน", "gun_law")

# ดู logs
# 🔵 TRACE START: search | id=abc12345
#   ✅ SPAN: retrieval (retrieval) | duration=45ms
#   ✅ SPAN: reranking (reranking) | duration=23ms
# ✅ TRACE END: search | duration=68ms | tokens=0 | cost=$0.00
```

### Production Mode (Langfuse)
```python
from src.observability import set_tracer
from src.observability.langfuse_tracer import LangfuseTracer

set_tracer(LangfuseTracer())

# Traces จะถูกส่งไป Langfuse Dashboard อัตโนมัติ
```

## 📈 Metrics ที่ควร Monitor

1. **Latency**
   - `retrieval_time_ms`
   - `reranking_time_ms`
   - `llm_generation_time_ms`
   - `total_request_time_ms`

2. **Quality**
   - `retrieval_top_score`
   - `reranking_top_score`
   - `user_feedback_score`

3. **Cost**
   - `llm_input_tokens`
   - `llm_output_tokens`
   - `llm_cost_usd`
   - `vlm_cost_usd` (for progressive processor)

4. **Usage**
   - `requests_per_kb`
   - `documents_uploaded`
   - `chunks_created`

## 🔗 Links

- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse Python SDK](https://langfuse.com/docs/sdk/python)
- [Langfuse Self-Hosting](https://langfuse.com/docs/deployment/self-host)

## 📝 Notes for Observe Team

1. **TraceData และ SpanData** มี fields ครบถ้วนที่ต้องการ - ดูใน `tracer.py`

2. **SpanType** บอกประเภทของ span:
   - `RETRIEVAL` - Vector/hybrid search
   - `RERANKING` - Reranking results
   - `LLM` - LLM generation (ใช้ `generation()` ใน Langfuse)
   - `EMBEDDING` - Embedding generation
   - `ROUTING` - KB routing
   - `DOCUMENT_PROCESSING` - Doc extraction/chunking

3. **Token & Cost** tracking อยู่ใน `TraceData.total_tokens` และ `TraceData.total_cost`

4. **User Feedback** สามารถเรียก `tracer.on_feedback(trace_id, score, comment)`

5. **Flush** ควรเรียก `tracer.flush()` ก่อน shutdown
