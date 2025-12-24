# 🎯 Full Schema Update - Implementation Complete

## ✅ สิ่งที่ทำเสร็จแล้ว (Dec 23, 2025)

### 1. **Created Schema Models** (`src/schemas/document_schema.py`)

สร้าง Pydantic models สำหรับ type-safe document processing:

#### **Core Models:**
- `NormalizedDocument` - Unified document format (tier-agnostic)
- `PageData` - Page-level data with content + structure
- `PageContent` - Multiple content formats (raw, cleaned, plain text, HTML)
- `PageMetadata` - Rich page metadata
- `StructureElement` - Document structure (headers, tables, paragraphs, lists)

#### **Quality & Extraction:**
- `QualityMetrics` - 5-dimension quality scoring
- `ExtractionInfo` - Extraction provenance (tier, cost, time, method)
- `DocumentStats` - Document statistics (pages, chars, words, headers, tables)

#### **Chunking:**
- `DocumentChunk` - Chunk with rich metadata
- `ChunkMetadata` - Comprehensive chunk metadata
- `ChunkPosition` - Position information
- `ChunkContext` - Context for RAG retrieval

#### **Enums:**
- `ExtractionTier` - fast, balanced, premium
- `ExtractionMethod` - docling, gemini-pro, claude, etc.

---

### 2. **Created DocumentNormalizer** (`src/core/document_normalizer.py`)

Universal normalizer ที่แปลง output จาก **ANY tier** เป็น unified format:

#### **Features:**
✅ **Tier-Agnostic** - รับ markdown จาก tier ใดก็ได้  
✅ **Structure Parsing** - แยก headers, tables, paragraphs, lists  
✅ **Multi-Format Output** - raw, cleaned, plain text  
✅ **Language Detection** - Thai, English, mixed  
✅ **Rich Statistics** - chars, words, structure counts  
✅ **Quality Integration** - เชื่อมกับ QualityChecker  

#### **Process Flow:**
```python
raw_pages (from ANY tier)
    ↓
normalize()
    ├── Clean markdown (remove artifacts)
    ├── Parse structure (headers/tables/lists/paragraphs)
    ├── Detect language (Thai/English)
    ├── Calculate statistics
    ├── Build metadata
    └── Create NormalizedDocument
```

---

### 3. **Updated RAGService** (`src/services/rag_service.py`)

ปรับ `upload_document()` เป็น **5-Phase Pipeline**:

#### **Phase 1: EXTRACTION**
```python
# Progressive (3-tier) หรือ Basic (Docling)
result = doc_processor.extract_with_smart_routing(...)
pages = result.pages
extraction_info = {tier_used, cost, time, quality, ...}
```

#### **Phase 2: NORMALIZATION** ⭐ NEW!
```python
# แปลงเป็น unified format
normalized_doc = doc_normalizer.normalize(
    raw_pages=pages,
    filename=filename,
    file_content=file_content,
    extraction_info=extraction_info,
    quality_metrics=quality_metrics,
    kb_name=kb_name
)
```

#### **Phase 3: CHUNKING**
```python
# ใช้ existing chunker (TODO: smart chunking later)
chunks = doc_processor.chunk_text(simple_pages)
```

#### **Phase 4: RICH METADATA** ⭐ NEW!
```python
# สร้าง metadata ครบถ้วนจาก normalized_doc
chunk_metadata = {
    # Identifiers
    "document_id": normalized_doc.document_id,
    "file_hash": normalized_doc.file_hash,
    
    # Extraction
    "extraction_tier": "premium",
    "extraction_method": "gemini-pro",
    "extraction_quality": 0.97,
    "extraction_cost": 0.0078,
    
    # Quality dimensions
    "quality_text": 0.98,
    "quality_word": 0.96,
    "quality_structure": 0.97,
    "quality_consistency": 0.95,
    "quality_density": 0.99,
    
    # Document stats
    "doc_total_pages": 6,
    "doc_total_chars": 12271,
    "doc_total_headers": 15,
    "doc_total_tables": 3,
    
    # Page metadata
    "page_id": "uuid-page-3",
    "page_language": "th",
    "page_has_tables": true,
    
    # Upload info
    "upload_date": "2025-12-23T...",
    ...
}
```

#### **Phase 5: INDEXING**
```python
# เก็บลง Qdrant พร้อม rich metadata
vector_store.upsert_documents(documents)
```

---

## 📊 **Schema Structure**

### **Document Level (Top)**
```json
{
  "document_id": "uuid-xxx",
  "filename": "reportfidf2566.pdf",
  "file_hash": "sha256-xxx",
  "uploaded_at": "2025-12-23T...",
  
  "extraction": {
    "tier_used": "premium",
    "tiers_attempted": ["fast", "premium"],
    "extraction_method": "gemini-pro",
    "processing_time": 368.5,
    "cost": 0.0078
  },
  
  "quality": {
    "overall_score": 0.97,
    "text_quality": 0.98,
    "word_quality": 0.96,
    "consistency": 0.95,
    "structure_quality": 0.97,
    "content_density": 0.99
  },
  
  "stats": {
    "total_pages": 6,
    "total_chars": 12271,
    "total_words": 1842,
    "total_headers": 15,
    "total_tables": 3,
    "avg_chars_per_page": 2045
  },
  
  "pages": [...]
}
```

### **Page Level**
```json
{
  "content": {
    "raw_markdown": "# หัวเรื่อง\n\n...",
    "cleaned_markdown": "# หัวเรื่อง\n\n...",
    "plain_text": "หัวเรื่อง ...",
    "html": null
  },
  
  "structure": [
    {
      "type": "header",
      "text": "งบการเงิน",
      "level": 1,
      "position": 0
    },
    {
      "type": "table",
      "text": "| H1 | H2 |...",
      "rows": 10,
      "cols": 5,
      "markdown": "..."
    }
  ],
  
  "metadata": {
    "page_id": "uuid-page-1",
    "page_number": 1,
    "language": "th",
    "char_count": 2045,
    "has_tables": true
  }
}
```

### **Chunk Level (in Qdrant)**
```json
{
  "text": "เนื้อหา chunk...",
  "metadata": {
    // Document context
    "document_id": "...",
    "filename": "reportfidf2566.pdf",
    
    // Extraction context
    "extraction_tier": "premium",
    "extraction_quality": 0.97,
    
    // Quality breakdown
    "quality_text": 0.98,
    "quality_word": 0.96,
    "quality_structure": 0.97,
    
    // Document stats
    "doc_total_pages": 6,
    "doc_total_headers": 15,
    
    // Page context
    "page": 3,
    "page_language": "th",
    "page_has_tables": true
  }
}
```

---

## 🎯 **Benefits**

### **1. Tier-Agnostic Processing**
```python
# ไม่ว่าจะมาจาก tier ไหน format เดียวกันหมด!
docling_output → NormalizedDocument
gemini_output → NormalizedDocument
claude_output → NormalizedDocument
```

### **2. Rich Metadata for RAG**
```python
# Query with filters
"Find tables about สินทรัพย์ in high-quality documents"

# Filter:
# - page_has_tables = true
# - extraction_quality >= 0.90
# - quality_structure >= 0.90
```

### **3. Quality Tracking**
```python
# Track quality across dimensions
{
  "text_quality": 0.98,      # ข้อความสะอาด
  "word_quality": 0.96,      # คำสมบูรณ์
  "structure_quality": 0.97, # โครงสร้างดี
  "consistency": 0.95,       # สม่ำเสมอ
  "content_density": 0.99    # เนื้อหาหนาแน่น
}
```

### **4. Cost/Performance Analysis**
```python
# Analyze extraction costs
{
  "tier_used": "premium",
  "cost": 0.0078,
  "quality": 0.97,
  "time": 368.5,
  
  "tier_comparison": {
    "fast": {"quality": 0.0, "cost": 0.0},
    "premium": {"quality": 0.97, "cost": 0.0078}
  }
}
```

### **5. Audit Trail**
```python
# Complete provenance
{
  "document_id": "uuid-xxx",
  "file_hash": "sha256-xxx",
  "uploaded_at": "2025-12-23T...",
  "extraction_tier": "premium",
  "extraction_method": "gemini-pro",
  "quality_score": 0.97
}
```

---

## 🚀 **Usage Example**

### **Upload Document:**
```python
result = rag_service.upload_document(
    kb_name="fidf_reports",
    filename="reportfidf2566.pdf",
    file_content=pdf_bytes
)

# Response:
{
  "success": true,
  "chunks_count": 45,
  "normalized_doc": {
    "document_id": "uuid-xxx",
    "extraction": {
      "tier_used": "premium",
      "quality_score": 0.97,
      "cost": 0.0078
    },
    "quality": {
      "overall_score": 0.97,
      "text_quality": 0.98,
      "structure_quality": 0.97
    },
    "stats": {
      "total_pages": 6,
      "total_headers": 15,
      "total_tables": 3
    }
  }
}
```

### **Search with Metadata:**
```python
# Find high-quality table content
results = rag_service.search(
    query="สินทรัพย์รวม",
    kb_name="fidf_reports",
    filters={
        "page_has_tables": True,
        "extraction_quality": {"$gte": 0.90},
        "quality_structure": {"$gte": 0.90}
    }
)
```

---

## 📝 **TODO: Future Enhancements**

### **1. Smart Chunking** (Phase 3)
```python
# Respect document structure
- Chunk by headers (section-based)
- Keep tables intact
- Maintain list coherence
```

### **2. JSON Export** (Optional)
```python
# Lossless storage
json_output = normalized_doc.dict()
save_json(json_output, f"{filename}.docling.json")
```

### **3. Structure-Aware Retrieval**
```python
# Query specific structures
"Find all tables with headers containing 'สินทรัพย์'"
"Get paragraphs under '## งบการเงิน' section"
```

### **4. Quality-Based Weighting**
```python
# Boost high-quality results
chunk_score = (
    semantic_similarity * 0.7 +
    extraction_quality * 0.2 +
    structure_quality * 0.1
)
```

---

## ✅ **Summary**

**ทำสำเร็จ:**
1. ✅ Schema Models (14 Pydantic models)
2. ✅ DocumentNormalizer (tier-agnostic)
3. ✅ Updated RAGService (5-phase pipeline)
4. ✅ Rich Metadata (30+ fields per chunk)
5. ✅ Quality Integration (5 dimensions)
6. ✅ Audit Trail (full provenance)

**ผลลัพธ์:**
- 🎯 **Unified Format** - ไม่ว่า tier ไหนก็ format เดียวกัน
- 📊 **Rich Metadata** - 30+ fields สำหรับ advanced RAG
- 🔍 **Quality Tracking** - 5 dimensions + issues/recommendations
- 💰 **Cost Analysis** - ติดตามค่าใช้จ่าย + tier comparison
- 🏗️ **Future-Proof** - พร้อมสำหรับ smart chunking, JSON export

**ขั้นต่อไป:**
- ทดสอบ upload document ใหม่
- ตรวจสอบ metadata ใน Qdrant
- Implement smart chunking (optional)
- Add JSON export (optional)

---

*Last Updated: December 23, 2025*
*Implementation: Full Schema Update v1.0*
