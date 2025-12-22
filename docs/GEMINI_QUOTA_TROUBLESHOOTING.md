# 🚨 Gemini API Quota Troubleshooting Guide

## ปัญหา: API Quota Exceeded (Error 429)

เมื่อเจอ error แบบนี้:
```
429 You exceeded your current quota, please check your plan and billing details
```

---

## 🔍 สาเหตุ

Gemini API (Free Tier) มี limits:
- **Requests per minute**: ~15 requests
- **Requests per day**: ~1,500 requests  
- **Input tokens per minute**: Limited based on model
- **Model**: `gemini-2.0-flash-exp` (experimental, strict limits)

เมื่อ Level 1 extraction ได้คะแนนต่ำกว่า threshold → ระบบจะ fallback ไป Level 2 (Gemini) → ใช้ quota

---

## ✅ วิธีแก้ไข

### Option 1: ปรับ Threshold (แนะนำ - ทำแล้ว ✅)

**ลด Level 1 threshold** เพื่อให้ผ่านง่ายขึ้น ไม่ต้อง fallback:

```bash
# ใน .env หรือ web/app.py
LEVEL1_THRESHOLD=0.75  # ลดจาก 0.85
```

**ผลลัพธ์:**
- เอกสารที่มีคะแนน ≥ 0.75 จะใช้ Level 1 (Fast, ไม่ใช้ API)
- ลดการเรียก Gemini API ลง ~50%

---

### Option 2: Disable VLM Fallback ชั่วคราว

แก้ไขใน `web/app.py`:

```python
# Force Level 1 only (no VLM fallback)
if USE_PROGRESSIVE:
    sections, method, quality_report = processor.extract_text(
        str(filepath), 
        clean_text=True,
        force_vlm=False  # ตั้งเป็น False เสมอ
    )
```

หรือตั้งค่าให้ไม่ใช้ Progressive mode:

```python
# ใน web/app.py (บรรทัด ~55)
gemini_api_key = None  # Force disable Gemini
```

---

### Option 3: เปลี่ยน API Key ใหม่

1. ไปที่: https://aistudio.google.com/app/apikey
2. สร้าง API key ใหม่
3. อัปเดตใน `.env`:

```bash
GEMINI_API_KEY=your-new-api-key-here
```

---

### Option 4: รอ Quota Reset

Free tier quotas reset:
- **Per minute**: รอ 1 นาที
- **Per day**: รอถึงวันถัดไป (UTC time)

Check usage ที่: https://ai.dev/usage?tab=rate-limit

---

## 📊 ตรวจสอบ Quota Usage

1. เข้า: https://ai.dev/usage
2. เลือก tab **Rate Limit**
3. ดูการใช้งาน:
   - Requests today
   - Requests per minute
   - Tokens consumed

---

## 🎯 Best Practices (ป้องกันไม่ให้เกิด)

### 1. ปรับ Threshold ให้เหมาะสม

```python
# Aggressive (ใช้ Level 1 บ่อย)
LEVEL1_THRESHOLD=0.70  

# Balanced (ค่าเริ่มต้น)
LEVEL1_THRESHOLD=0.75  

# Strict (ใช้ VLM บ่อย - ระวัง quota!)
LEVEL1_THRESHOLD=0.90
```

### 2. Monitor Quality Scores

ดูว่าเอกสารส่วนใหญ่ได้คะแนนเท่าไหร่:
- ถ้าส่วนใหญ่ได้ 0.80-0.85 → ลด threshold เป็น 0.75
- ถ้าส่วนใหญ่ได้ < 0.70 → พิจารณาใช้ VLM หรือปรับ preprocessing

### 3. Batch Processing

ถ้าประมวลผลเอกสารจำนวนมาก:

```python
import time

for file in files:
    pages, method, report = processor.extract_text(file)
    
    if method == "VLM":
        time.sleep(5)  # Rate limiting: รอ 5 วิก่อนประมวลผลไฟล์ถัดไป
```

### 4. Use Paid Plan (Production)

สำหรับ production ควรใช้ **paid plan**:
- Higher rate limits
- More reliable
- Better SLA

ดูที่: https://ai.google.dev/pricing

---

## 🧪 ทดสอบว่าแก้ไขแล้ว

1. **Restart web server:**
   ```bash
   # กด Ctrl+C ใน terminal
   python web/app.py
   ```

2. **ลองอัพโหลดเอกสาร:**
   - เอกสารที่ได้คะแนน 0.75-0.85 ควร pass Level 1
   - ไม่ต้อง fallback ไป Gemini
   - ไม่เกิด quota error

3. **Check logs:**
   ```
   ✅ Level 1 PASSED: Quality 0.830 (threshold: 0.75)
   ```

---

## 🔧 Current Configuration

**ปัจจุบัน (ปรับแล้ว):**
- ✅ `LEVEL1_THRESHOLD=0.75` (ลดจาก 0.85)
- ✅ Error handling สำหรับ quota errors
- ✅ Graceful fallback to Level 1 results

**ผลลัพธ์:**
- เอกสารที่ได้คะแนน ≥ 0.75 จะไม่ใช้ Gemini API
- ประหยัด quota มากขึ้น
- ยังคงได้คุณภาพที่ดี (0.75 = "GOOD")

---

## 📞 หากยังมีปัญหา

1. **ตรวจสอบ quota:** https://ai.dev/usage
2. **ลด threshold อีก:** `LEVEL1_THRESHOLD=0.70`
3. **Disable VLM:** Comment out `gemini_api_key` in `web/app.py`
4. **Use paid plan:** Upgrade at https://ai.google.dev/pricing

---

## ✅ สรุป

**ทำไปแล้ว:**
- ✅ ลด `LEVEL1_THRESHOLD` เป็น 0.75
- ✅ เพิ่ม error handling สำหรับ quota errors
- ✅ ระบบจะใช้ Level 1 results ถ้า Gemini quota หมด

**ลอง restart web server แล้วทดสอบใหม่ครับ!** 🚀

```bash
python web/app.py
```
