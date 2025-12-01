"""Metadata Extractor

Uses LLM to extract structured metadata from document text.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract structured metadata from document text using LLM
    
    Usage:
        extractor = MetadataExtractor(llm_client, prompt_template)
        metadata = extractor.extract(text)
        # Returns: {"doc_type": "...", "category": "...", "status": "...", "title": "..."}
    """
    
    def __init__(self, llm_client=None, prompt_template: str = ""):
        self.llm_client = llm_client
        self.prompt_template = prompt_template or self._default_prompt()
    
    def _default_prompt(self) -> str:
        """Default metadata extraction prompt"""
        return """คุณคือผู้ช่วยในการวิเคราะห์เอกสาร กรุณาอ่านเนื้อหาต่อไปนี้และสกัดข้อมูล metadata ออกมาในรูปแบบ JSON:

เนื้อหาเอกสาร:
{text}

กรุณาส่งคืนเฉพาะ JSON object ที่มีฟิลด์เหล่านี้:
- doc_type: ประเภทของเอกสาร (เช่น "law", "regulation", "guideline", "policy", "report", "other")
- category: หมวดหมู่เอกสาร (เช่น "firearms", "contracts", "hr", "finance", "general")
- status: สถานะเอกสาร (เช่น "active", "draft", "archived", "unknown")
- title: ชื่อเอกสาร (สกัดจากเนื้อหา หรือใช้ "Untitled" ถ้าไม่พบ)

ตัวอย่างผลลัพธ์:
{{"doc_type": "law", "category": "firearms", "status": "active", "title": "พระราชบัญญัติอาวุธปืน"}}

JSON:"""
    
    def extract(self, text: str, max_chars: int = 3000) -> Dict[str, Any]:
        """Extract metadata from document text
        
        Args:
            text: Document text to analyze
            max_chars: Maximum characters to send to LLM (will truncate)
            
        Returns:
            Dict with keys: doc_type, category, status, title
        """
        # Truncate text if too long
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        # Format prompt
        prompt = self.prompt_template.format(text=text)
        
        # Call LLM
        try:
            if not self.llm_client:
                logger.warning("No LLM client provided, using fallback metadata")
                return self._fallback_metadata(text)
            
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3  # Lower temp for structured output
            )
            
            # Parse JSON from response
            response_text = response.get("text", "").strip()
            metadata = self._parse_json(response_text)
            
            if metadata:
                logger.info("Extracted metadata: %s", metadata)
                return metadata
            else:
                logger.warning("Failed to parse LLM response, using fallback")
                return self._fallback_metadata(text)
                
        except Exception as e:
            logger.error("Metadata extraction failed: %s", e)
            return self._fallback_metadata(text)
    
    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response (handles markdown code blocks)"""
        try:
            # Try direct JSON parse
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                json_str = text[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            # Try to extract JSON object
            if "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                json_str = text[start:end]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            return None
    
    def _fallback_metadata(self, text: str) -> Dict[str, Any]:
        """Generate fallback metadata based on simple heuristics"""
        # Extract first line as potential title
        lines = text.split("\n")
        first_line = lines[0].strip() if lines else "Untitled"
        title = first_line[:100] if first_line else "Untitled"
        
        # Simple keyword-based category detection
        text_lower = text.lower()
        
        category = "general"
        if any(word in text_lower for word in ["ปืน", "อาวุธ", "firearm", "gun"]):
            category = "firearms"
        elif any(word in text_lower for word in ["สัญญา", "contract"]):
            category = "contracts"
        elif any(word in text_lower for word in ["พนักงาน", "hr", "human resource"]):
            category = "hr"
        elif any(word in text_lower for word in ["การเงิน", "finance", "budget"]):
            category = "finance"
        
        doc_type = "other"
        if any(word in text_lower for word in ["พระราชบัญญัติ", "พรบ", "law", "act"]):
            doc_type = "law"
        elif any(word in text_lower for word in ["ระเบียบ", "regulation"]):
            doc_type = "regulation"
        elif any(word in text_lower for word in ["แนวทาง", "guideline"]):
            doc_type = "guideline"
        elif any(word in text_lower for word in ["นโยบาย", "policy"]):
            doc_type = "policy"
        
        return {
            "doc_type": doc_type,
            "category": category,
            "status": "unknown",
            "title": title
        }
