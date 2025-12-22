"""
Text Cleaner Utilities
ทำความสะอาดข้อความที่ได้จาก Docling และ OCR
"""
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class TextCleaner:
    """ทำความสะอาดและ normalize ข้อความ"""
    
    @staticmethod
    def remove_glyph_characters(text: str) -> str:
        """
        ลบ GLYPH characters ที่เกิดจากปัญหาการแปลงฟอนต์
        
        Examples:
            GLYPH<29> → (removed)
            GLYPH&lt;19&gt; → (removed)
            GLYPH<c=29,font=/AAAAAH+DBHelvethaicaX> → (removed)
        
        Args:
            text: ข้อความที่ต้องการทำความสะอาด
            
        Returns:
            ข้อความที่ไม่มี GLYPH characters
        """
        # ลบ GLYPH patterns ทั้งหมด
        patterns = [
            r'GLYPH<[^>]+>',           # GLYPH<29>
            r'GLYPH&lt;[^&]+&gt;',     # GLYPH&lt;19&gt;
            r'GLYPH\([^)]+\)',         # GLYPH(xxx)
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text)
        
        # ลบช่องว่างซ้ำซ้อนที่เกิดจากการลบ GLYPH
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    @staticmethod
    def normalize_thai_text(text: str) -> str:
        """
        Normalize ข้อความภาษาไทย
        - แก้ไขช่องว่างที่ไม่เหมาะสม
        - Normalize tone marks
        - แก้ไขการเรียงตัวอักษร
        
        Args:
            text: ข้อความภาษาไทย
            
        Returns:
            ข้อความที่ normalized แล้ว
        """
        # ลบช่องว่างระหว่างพยัญชนะและสระ/วรรณยุกต์
        # เช่น "ก ิ" → "กิ"
        text = re.sub(r'([ก-ฮ])\s+([ะ-ฺ])', r'\1\2', text)
        
        # ลบช่องว่างซ้ำซ้อน
        text = re.sub(r'\s+', ' ', text)
        
        # ลบช่องว่างก่อนเครื่องหมายวรรคตอน
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        
        # ใช้ PyThaiNLP ถ้ามี (optional)
        try:
            from pythainlp import normalize
            text = normalize(text)
        except ImportError:
            logger.debug("PyThaiNLP not available, using basic normalization")
        
        return text.strip()
    
    @staticmethod
    def clean_markdown_artifacts(text: str) -> str:
        """
        ทำความสะอาด artifacts จากการแปลง Markdown
        
        Args:
            text: ข้อความ Markdown
            
        Returns:
            ข้อความที่สะอาดขึ้น
        """
        # ลบ HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        
        # แก้ไข broken tables
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip ONLY truly empty table rows (no content)
            if stripped in ['|', '| |', '||', '|||']:
                continue
            
            # Skip lines with ONLY pipes and spaces (broken table structure)
            if stripped and all(c in '| ' for c in stripped) and len(stripped) < 5:
                continue
                
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # ลบบรรทัดว่างซ้ำซ้อน (เกิน 2 บรรทัด)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    @staticmethod
    def fix_broken_words(text: str) -> str:
        """
        แก้ไขคำที่ถูกตัดแบบผิดๆ จากการแปลง
        เช่น "ก าร" → "การ", "เป็ น" → "เป็น"
        
        Args:
            text: ข้อความที่มีคำผิด
            
        Returns:
            ข้อความที่แก้ไขแล้ว
        """
        # แก้ไขคำไทยที่มีช่องว่างระหว่างตัวอักษร
        # ใช้ regex เพื่อจับคำที่มีรูปแบบ: พยัญชนะ + ช่องว่าง + สระ/วรรณยุกต์
        patterns = [
            (r'([ก-ฮ])\s+([ิีึืุูัๅๆ็่้๊๋์])', r'\1\2'),  # กิ, ที่, etc.
            (r'([เแโใไ])\s+([ก-ฮ])', r'\1\2'),           # เป็น, แก้, etc.
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    @staticmethod
    def remove_ocr_noise(text: str) -> str:
        """
        ลบ noise ที่เกิดจาก OCR
        - ตัวอักษรแปลกๆ ที่ไม่ควรอยู่
        - Special characters ที่ไม่จำเป็น
        
        Args:
            text: ข้อความจาก OCR
            
        Returns:
            ข้อความที่สะอาดขึ้น
        """
        # ลบ control characters (ยกเว้น newline, tab)
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # ลบ special Unicode characters ที่เป็น noise
        text = re.sub(r'[\ufeff\u200b-\u200f\u202a-\u202e]', '', text)
        
        return text
    
    @classmethod
    def clean_text(
        cls,
        text: str,
        remove_glyphs: bool = True,
        normalize_thai: bool = True,
        clean_markdown: bool = True,
        fix_words: bool = True,
        remove_noise: bool = True
    ) -> str:
        """
        ทำความสะอาดข้อความแบบครบวงจร
        
        Args:
            text: ข้อความที่ต้องการทำความสะอาด
            remove_glyphs: ลบ GLYPH characters
            normalize_thai: Normalize ข้อความภาษาไทย
            clean_markdown: ทำความสะอาด Markdown artifacts
            fix_words: แก้ไขคำที่ถูกตัดผิด
            remove_noise: ลบ OCR noise
            
        Returns:
            ข้อความที่สะอาดแล้ว
        """
        if not text or not text.strip():
            return ""
        
        # Apply cleaning steps
        if remove_glyphs:
            text = cls.remove_glyph_characters(text)
        
        if remove_noise:
            text = cls.remove_ocr_noise(text)
        
        if fix_words:
            text = cls.fix_broken_words(text)
        
        if normalize_thai:
            text = cls.normalize_thai_text(text)
        
        if clean_markdown:
            text = cls.clean_markdown_artifacts(text)
        
        return text.strip()
    
    @classmethod
    def clean_pages(
        cls,
        pages: List[str],
        min_chars: int = 3,  # Keep pages with at least 3 chars (very permissive)
        **kwargs
    ) -> List[str]:
        """
        ทำความสะอาดหลายๆ pages พร้อมกัน
        
        Args:
            pages: List ของข้อความแต่ละหน้า
            min_chars: จำนวนตัวอักษรขั้นต่ำเพื่อเก็บ page (default: 3)
            **kwargs: Arguments สำหรับ clean_text()
            
        Returns:
            List ของข้อความที่สะอาดแล้ว
        """
        cleaned = []
        for i, page in enumerate(pages):
            cleaned_page = cls.clean_text(page, **kwargs)
            # เก็บ page ที่มีเนื้อหาอย่างน้อย min_chars ตัวอักษร
            if cleaned_page and len(cleaned_page.strip()) >= min_chars:
                cleaned.append(cleaned_page)
            else:
                # Log ว่าทำไมถึง skip
                if not cleaned_page:
                    logger.warning(f"⚠️  Page {i+1}: Empty after cleaning (original: {len(page)} chars)")
                else:
                    logger.warning(f"⚠️  Page {i+1}: Too short after cleaning ({len(cleaned_page)} chars < {min_chars})")
        
        return cleaned


class TextStatistics:
    """คำนวณสถิติของข้อความ"""
    
    @staticmethod
    def count_glyph_chars(text: str) -> int:
        """นับจำนวน GLYPH characters"""
        return len(re.findall(r'GLYPH', text))
    
    @staticmethod
    def count_thai_chars(text: str) -> int:
        """นับจำนวนตัวอักษรไทย"""
        return len(re.findall(r'[ก-๙]', text))
    
    @staticmethod
    def count_english_chars(text: str) -> int:
        """นับจำนวนตัวอักษรอังกฤษ"""
        return len(re.findall(r'[a-zA-Z]', text))
    
    @staticmethod
    def calculate_thai_ratio(text: str) -> float:
        """คำนวณอัตราส่วนภาษาไทย"""
        if not text:
            return 0.0
        thai_count = TextStatistics.count_thai_chars(text)
        total_chars = len(text)
        return thai_count / max(1, total_chars)
    
    @staticmethod
    def has_tables(text: str) -> bool:
        """ตรวจสอบว่ามีตารางหรือไม่"""
        # ตรวจหา Markdown table pattern
        lines = text.split('\n')
        table_lines = [line for line in lines if '|' in line]
        return len(table_lines) >= 2  # อย่างน้อย 2 บรรทัด
    
    @staticmethod
    def count_headers(text: str) -> int:
        """นับจำนวน Markdown headers"""
        return len(re.findall(r'^#{1,6}\s+.+$', text, re.MULTILINE))
    
    @classmethod
    def get_statistics(cls, text: str) -> dict:
        """รวมสถิติทั้งหมด"""
        return {
            'total_chars': len(text),
            'total_lines': text.count('\n') + 1,
            'glyph_count': cls.count_glyph_chars(text),
            'thai_chars': cls.count_thai_chars(text),
            'english_chars': cls.count_english_chars(text),
            'thai_ratio': cls.calculate_thai_ratio(text),
            'has_tables': cls.has_tables(text),
            'header_count': cls.count_headers(text),
        }
