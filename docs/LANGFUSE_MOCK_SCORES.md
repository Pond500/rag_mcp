# 📊 Langfuse Evaluation - Mock Scores Guide

คู่มือการใช้งาน scripts สำหรับ POST คะแนน mockup ไปยัง Langfuse เพื่อทดสอบระบบ evaluation โดยไม่ต้องรัน evaluation จริง

---

## 🎯 จุดประสงค์

Scripts เหล่านี้ช่วยให้คุณ:
- ✅ ทดสอบระบบ Langfuse observability โดยไม่ต้องรัน evaluation จริง
- ✅ สร้าง mock traces และคะแนนเพื่อทดสอบ dashboard
- ✅ POST คะแนนไปยัง traces ที่มีอยู่แล้ว
- ✅ ทดสอบ custom metrics ต่างๆ

---

## 📦 Scripts ที่มี

### 1. `post_mock_scores.py` 
สร้าง mock traces และ POST คะแนนหลายๆ แบบไปยัง Langfuse

### 2. `post_score_to_trace.py`
POST คะแนนไปยัง trace ที่มีอยู่แล้ว

---

## 🚀 การใช้งาน

### ตั้งค่า Environment Variables

ก่อนใช้งาน ต้องตั้งค่า Langfuse connection:

```bash
export LANGFUSE_HOST="http://localhost:3000"           # Langfuse server URL
export LANGFUSE_PUBLIC_KEY="pk-xxx"                    # Public key จาก Dashboard
export LANGFUSE_SECRET_KEY="sk-xxx"                    # Secret key จาก Dashboard
export LANGFUSE_PROJECT="mcp-rag-v2"                   # ชื่อ project
export LANGFUSE_ENABLED="true"                         # เปิดใช้งาน Langfuse
```

หรือสร้างไฟล์ `.env`:

```bash
# .env
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_PROJECT=mcp-rag-v2
LANGFUSE_ENABLED=true
```

---

## 📝 Script 1: Post Mock Scores

สร้าง mock traces และ POST คะแนนแบบสุ่มเพื่อทดสอบระบบ

### วิธีใช้งาน

```bash
python scripts/post_mock_scores.py
```

### Output ตัวอย่าง

```
======================================================================
📝 POST MOCK EVALUATION SCORES TO LANGFUSE
======================================================================
==================================================
🔗 Langfuse Connection Info
==================================================
Host:        http://localhost:3000
Public Key:  pk-lf-123456...
Secret Key:  sk-lf-789012...
Project:     mcp-rag-v2
Environment: development
Enabled:     True
Status:      ✅ Langfuse config พร้อมใช้งาน
==================================================

🔗 กำลังเชื่อมต่อกับ Langfuse: http://localhost:3000

======================================================================
🚀 เริ่มสร้าง mock traces และ POST คะแนน
======================================================================

📊 Posting mock scores for trace: mock_rag_query_1
   Trace ID: abc-123-xyz
   ✅ faithfulness: 0.923
   ✅ answer_relevancy: 0.854
   ✅ context_precision: 0.782
   ✅ context_recall: 0.891

👤 Posting mock user feedback for trace: mock_rag_query_1
   Trace ID: abc-123-xyz
   ⭐ user_rating: 5/5
   👍 thumbs_up: Yes

📤 กำลังส่งข้อมูลไปยัง Langfuse...

======================================================================
✅ POST MOCK SCORES เสร็จสิ้น
======================================================================

🌐 ดูผลลัพธ์ได้ที่: http://localhost:3000
📊 ไปที่ Dashboard → Traces เพื่อดู mock traces ที่สร้าง
📈 ไปที่ Scores/Evaluations เพื่อดูคะแนนที่ POST
```

### คะแนนที่ POST

Script นี้จะสร้าง 4 mock traces พร้อมคะแนนต่างๆ:

#### Trace 1: RAG Query (Full Metrics)
- **RAG Metrics:**
  - `faithfulness` (0.7-1.0): ความถูกต้องตาม context
  - `answer_relevancy` (0.6-0.95): ความเกี่ยวข้องของคำตอบ
  - `context_precision` (0.65-0.9): ความแม่นยำของ context
  - `context_recall` (0.7-0.95): ความครบถ้วนของ context

- **LLM Quality Metrics:**
  - `hallucination_score` (0-0.3): ระดับการ hallucinate (ต่ำ = ดี)
  - `toxicity_score` (0-0.2): ระดับความเป็นพิษ (ต่ำ = ดี)
  - `coherence` (0.75-1.0): ความสอดคล้อง (สูง = ดี)
  - `fluency` (0.8-1.0): ความลื่นไหล (สูง = ดี)

- **User Feedback:**
  - `user_rating` (3-5): คะแนนจากผู้ใช้
  - `thumbs_up` (0/1): ถูกใจหรือไม่

#### Trace 2: RAG Query (RAG Metrics Only)
- เฉพาะ RAG metrics ข้างต้น

#### Trace 3: RAG Query (Custom Metrics)
- `response_time_ms` (200-800): เวลาตอบกลับ (มิลลิวินาที)
- `retrieval_count` (3-10): จำนวน documents ที่ retrieve
- `chunk_relevance_avg` (0.6-0.95): ค่าเฉลี่ย relevance ของ chunks
- `reranker_score` (0.7-0.98): คะแนนจาก reranker

#### Trace 4: Document Upload
- `vlm_cost_usd` (0.001-0.05): ค่าใช้จ่าย VLM (USD)
- `pages_processed` (1-50): จำนวนหน้าที่ประมวลผล
- `chunks_created` (10-200): จำนวน chunks ที่สร้าง
- `processing_time_sec` (5-60): เวลาประมวลผล (วินาที)

---

## 📌 Script 2: Post Score to Existing Trace

POST คะแนนไปยัง trace ที่มีอยู่แล้วใน Langfuse

### วิธีใช้งาน

```bash
python scripts/post_score_to_trace.py \
  --trace-id <TRACE_ID> \
  --metric <METRIC_NAME> \
  --value <SCORE_VALUE> \
  [--comment "Optional comment"]
```

### ตัวอย่างการใช้งาน

#### 1. POST faithfulness score
```bash
python scripts/post_score_to_trace.py \
  --trace-id abc123xyz \
  --metric faithfulness \
  --value 0.95
```

#### 2. POST user rating พร้อม comment
```bash
python scripts/post_score_to_trace.py \
  --trace-id abc123xyz \
  --metric user_rating \
  --value 5 \
  --comment "ตอบได้แม่นยำมาก ชอบมาก!"
```

#### 3. POST custom metric (response time)
```bash
python scripts/post_score_to_trace.py \
  --trace-id abc123xyz \
  --metric response_time_ms \
  --value 350.5 \
  --comment "Fast response"
```

#### 4. POST VLM cost
```bash
python scripts/post_score_to_trace.py \
  --trace-id abc123xyz \
  --metric vlm_cost_usd \
  --value 0.0078 \
  --comment "Gemini 2.5 Pro - 6 pages processed"
```

### Output ตัวอย่าง

```
======================================================================
📝 POST EVALUATION SCORE TO TRACE
======================================================================
==================================================
🔗 Langfuse Connection Info
==================================================
Host:        http://localhost:3000
Public Key:  pk-lf-123456...
Secret Key:  sk-lf-789012...
Project:     mcp-rag-v2
Environment: development
Enabled:     True
Status:      ✅ Langfuse config พร้อมใช้งาน
==================================================

🔗 กำลังเชื่อมต่อกับ Langfuse: http://localhost:3000

======================================================================
🚀 กำลัง POST คะแนน...
======================================================================

✅ Successfully posted score to trace
   Trace ID: abc123xyz
   Metric: faithfulness
   Value: 0.95
   Comment: ตอบได้แม่นยำมาก

📤 กำลังส่งข้อมูลไปยัง Langfuse...

======================================================================
✅ POST SCORE เสร็จสิ้น
======================================================================

🌐 ดูผลลัพธ์ได้ที่: http://localhost:3000/trace/abc123xyz
```

---

## 📊 Metrics ที่แนะนำ

### RAG Evaluation Metrics
| Metric | ช่วงค่า | คำอธิบาย | ค่าที่ดี |
|--------|---------|----------|----------|
| `faithfulness` | 0-1 | ความถูกต้องตาม context ที่ retrieve มา | ≥ 0.8 |
| `answer_relevancy` | 0-1 | ความเกี่ยวข้องของคำตอบกับคำถาม | ≥ 0.7 |
| `context_precision` | 0-1 | ความแม่นยำของ context (ไม่มีข้อมูลเกิน) | ≥ 0.7 |
| `context_recall` | 0-1 | ความครบถ้วนของ context (ครอบคลุมคำถาม) | ≥ 0.8 |

### LLM Quality Metrics
| Metric | ช่วงค่า | คำอธิบาย | ค่าที่ดี |
|--------|---------|----------|----------|
| `hallucination_score` | 0-1 | ระดับการแต่งเรื่อง/ตอบนอกประเด็น | ≤ 0.2 |
| `toxicity_score` | 0-1 | ระดับความเป็นพิษของคำตอบ | ≤ 0.1 |
| `coherence` | 0-1 | ความสอดคล้องของคำตอบ | ≥ 0.8 |
| `fluency` | 0-1 | ความลื่นไหลของภาษา | ≥ 0.8 |

### User Feedback
| Metric | ช่วงค่า | คำอธิบาย |
|--------|---------|----------|
| `user_rating` | 1-5 | คะแนนจากผู้ใช้ (1=แย่, 5=ดีมาก) |
| `thumbs_up` | 0/1 | ถูกใจ (1) หรือไม่ถูกใจ (0) |

### Custom Metrics
| Metric | หน่วย | คำอธิบาย |
|--------|-------|----------|
| `response_time_ms` | มิลลิวินาที | เวลาตอบกลับ |
| `retrieval_count` | จำนวน | จำนวน documents ที่ retrieve |
| `chunk_relevance_avg` | 0-1 | ค่าเฉลี่ย relevance score |
| `reranker_score` | 0-1 | คะแนนจาก reranker |
| `vlm_cost_usd` | USD | ค่าใช้จ่าย VLM |
| `pages_processed` | จำนวน | จำนวนหน้าที่ประมวลผล |
| `chunks_created` | จำนวน | จำนวน chunks ที่สร้าง |

---

## 🔍 วิธีหา Trace ID

มี 3 วิธีหา Trace ID จาก Langfuse:

### 1. ผ่าน Langfuse Dashboard
1. เปิด Langfuse Dashboard (`http://localhost:3000`)
2. ไปที่ **Traces** tab
3. คลิกที่ trace ที่ต้องการ
4. Copy **Trace ID** จาก URL หรือจากหน้ารายละเอียด

### 2. ผ่าน API Response
เมื่อสร้าง trace จะได้ `trace_id` กลับมา:
```python
trace = langfuse.trace(name="my_trace")
print(f"Trace ID: {trace.id}")  # เก็บ ID นี้ไว้
```

### 3. ผ่าน Langfuse SDK Query
```python
from langfuse import Langfuse

langfuse = Langfuse()
traces = langfuse.get_traces(limit=10)  # ดึง traces ล่าสุด 10 รายการ
for trace in traces:
    print(f"Name: {trace.name}, ID: {trace.id}")
```

---

## 🎨 Customization

### เพิ่ม Custom Metrics ใหม่

แก้ไขฟังก์ชัน `post_mock_custom_scores()` ใน `post_mock_scores.py`:

```python
# เพิ่ม metrics ใหม่
post_mock_custom_scores(
    langfuse, 
    trace_id, 
    "my_trace",
    {
        "my_custom_metric": 0.95,
        "another_metric": 123.45,
        "boolean_metric": 1,  # 0 หรือ 1
    }
)
```

### สร้าง Mock Traces เพิ่ม

เพิ่มโค้ดใน `main()` ของ `post_mock_scores.py`:

```python
# สร้าง trace ใหม่
trace_id_5 = create_mock_trace(langfuse, "my_custom_trace")

# POST คะแนน
post_mock_custom_scores(
    langfuse,
    trace_id_5,
    "my_custom_trace",
    {
        "accuracy": 0.92,
        "latency_ms": 450,
    }
)
```

---

## ⚠️ ข้อควรระวัง

1. **Trace ID ต้องถูกต้อง**: ถ้า trace ID ไม่มีจริง จะไม่สามารถ POST คะแนนได้
2. **Metric Names**: ควรใช้ชื่อที่สื่อความหมายชัดเจน เช่น `faithfulness` แทน `f1`
3. **Score Range**: ตรวจสอบให้แน่ใจว่าค่าคะแนนอยู่ในช่วงที่เหมาะสม (เช่น 0-1 หรือ 1-5)
4. **Flush**: อย่าลืม `langfuse.flush()` เพื่อให้ข้อมูลถูกส่งไปยัง server จริงๆ

---

## 🐛 Troubleshooting

### ❌ Connection Error
```
Error: Failed to connect to Langfuse
```
**แก้ไข**: ตรวจสอบว่า Langfuse server ทำงานอยู่และ `LANGFUSE_HOST` ถูกต้อง

### ❌ Authentication Error
```
Error: Invalid API keys
```
**แก้ไข**: ตรวจสอบ `LANGFUSE_PUBLIC_KEY` และ `LANGFUSE_SECRET_KEY` ว่าถูกต้อง

### ❌ Trace Not Found
```
Error: Trace ID not found
```
**แก้ไข**: ตรวจสอบว่า Trace ID ที่ใช้มีอยู่จริงใน Langfuse

### ⚠️ Score Not Showing
**อาการ**: POST สำเร็จแต่ไม่เห็นคะแนนใน Dashboard
**แก้ไข**: 
1. รอสักครู่ (อาจมี caching)
2. Refresh หน้า Dashboard
3. ตรวจสอบว่าใช้ `langfuse.flush()` แล้ว

---

## 📚 อ้างอิง

- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse Python SDK](https://langfuse.com/docs/sdk/python)
- [Langfuse Scores API](https://langfuse.com/docs/scores)

---

## 💡 Tips

1. **ทดสอบบ่อยๆ**: ใช้ mock scores ทดสอบ dashboard layout และ visualization
2. **ใช้ Comments**: เพิ่ม comment ใน scores เพื่อจดบันทึกข้อมูลเพิ่มเติม
3. **สร้าง Baselines**: ใช้ mock scores สร้าง baseline performance metrics
4. **A/B Testing**: สร้าง mock traces หลายๆ แบบเพื่อทดสอบ A/B testing flow

---

## 📧 Support

หากมีปัญหาหรือข้อสงสัย สามารถ:
- เปิด issue ใน repository
- ดู logs ที่ `logs/mcp_server.log`
- ตรวจสอบ Langfuse Dashboard

---

**สร้างโดย**: MCP RAG v2 Team  
**อัพเดทล่าสุด**: December 2024
