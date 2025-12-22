"""Progressive Processor with OpenRouter - Simplified"""
from typing import List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import logging
import time

from src.core.document_processor import DocumentProcessor
from src.core.openrouter_extractor import OpenRouterExtractor
from src.core.quality_checker import UnsupervisedQualityChecker, QualityReport

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    pages: List[str]
    tier_used: str
    tier_attempted: List[str]
    quality_score: float
    quality_report: QualityReport
    cost: float
    extraction_time: float
    total_time: float
    success: bool
    error: Optional[str] = None
    metadata: dict = None


class ProgressiveDocumentProcessor:
    """3-tier progressive extraction: Docling (fast) → VLM (balanced) → VLM Premium"""
    
    # Tier thresholds and costs
    TIER_THRESHOLDS = {'fast': 0.70, 'balanced': 0.80, 'premium': 0.85}
    TIER_COSTS = {
        'fast': 0.0,        # Docling (no OCR) - FREE
        'balanced': 0.0,    # Gemini 2.0 Flash Free
        'premium': 0.0013   # Gemini 2.5 Pro (paid)
    }
    
    def __init__(self, openrouter_api_key: Optional[str] = None, 
                 enable_fast_tier: bool = True,
                 enable_balanced_tier: bool = True,
                 enable_premium_tier: bool = True,
                 image_dpi: int = 200,
                 disable_ocr: bool = True):  # Disable Tesseract OCR by default
        self.openrouter_api_key = openrouter_api_key
        self.disable_ocr = disable_ocr  # No Tesseract OCR!
        
        # Fast tier always enabled (Docling)
        self.enable_fast_tier = enable_fast_tier
        
        # VLM tiers require API key
        self.enable_balanced_tier = enable_balanced_tier and bool(openrouter_api_key)
        self.enable_premium_tier = enable_premium_tier and bool(openrouter_api_key)
        
        self.image_dpi = image_dpi
        
        # Initialize Docling processor (without Tesseract OCR by default)
        self.fast_processor = DocumentProcessor(enable_ocr=not disable_ocr) if enable_fast_tier else None
        self.quality_checker = UnsupervisedQualityChecker()
        
        # Lazy-loaded VLM extractors
        self._balanced_extractor = None
        self._premium_extractor = None
        
        logger.info(f"🚀 ProgressiveDocumentProcessor ready")
        logger.info(f"   • Fast tier: Docling (OCR: {'OFF' if disable_ocr else 'ON'})")
        logger.info(f"   • Balanced tier: {'Gemini Free VLM' if self.enable_balanced_tier else 'Disabled'}")
        logger.info(f"   • Premium tier: {'Gemini Pro VLM' if self.enable_premium_tier else 'Disabled'}")
    
    def extract_with_smart_routing(
        self, pdf_path: Optional[str] = None, pdf_bytes: Optional[bytes] = None,
        target_quality: float = 0.70, start_tier: str = 'fast',
        auto_retry: bool = True, clean_text: bool = True
    ) -> ExtractionResult:
        """Extract with automatic tier escalation"""
        start_time = time.time()
        file_name = Path(pdf_path).name if pdf_path else "document.pdf"
        
        logger.info(f"📄 Processing: {file_name} (target: {target_quality:.2f})")
        
        # Tier sequence
        tiers = []
        if self.enable_fast_tier and start_tier == 'fast':
            tiers.append('fast')
        if self.enable_balanced_tier:
            tiers.append('balanced')
        if self.enable_premium_tier:
            tiers.append('premium')
        
        best_result = None
        best_quality = 0.0
        tiers_attempted = []
        total_cost = 0.0
        
        for tier in tiers:
            tiers_attempted.append(tier)
            logger.info(f"🔄 Trying {tier} tier...")
            
            try:
                extract_start = time.time()
                pages, quality_report = self._extract_tier(tier, pdf_path, pdf_bytes, clean_text)
                extraction_time = time.time() - extract_start
                
                cost = len(pages) * self.TIER_COSTS[tier]
                total_cost += cost
                
                logger.info(
                    f"✅ {tier}: {len(pages)} pages, "
                    f"quality={quality_report.overall_score:.3f}, "
                    f"cost=${cost:.4f}"
                )
                
                if quality_report.overall_score > best_quality:
                    best_result = (pages, quality_report, tier, extraction_time, cost)
                    best_quality = quality_report.overall_score
                
                if quality_report.overall_score >= target_quality:
                    logger.info(f"🎉 Target met!")
                    break
                elif auto_retry and tier != tiers[-1]:
                    logger.info(f"🔄 Escalating...")
                else:
                    break
                    
            except Exception as e:
                logger.error(f"❌ {tier} failed: {e}")
                
                # Fallback to fast if quota error
                if ("429" in str(e) or "quota" in str(e).lower()) and tier != 'fast' and self.enable_fast_tier:
                    logger.info("🆓 Emergency fallback to fast tier")
                    try:
                        pages, quality_report = self._extract_tier('fast', pdf_path, pdf_bytes, clean_text)
                        best_result = (pages, quality_report, 'fast', 0, 0)
                        best_quality = quality_report.overall_score
                        break
                    except:
                        pass
                
                if not auto_retry:
                    break
        
        total_time = time.time() - start_time
        
        if best_result:
            pages, quality_report, tier_used, extraction_time, cost = best_result
            return ExtractionResult(
                pages=pages,
                tier_used=tier_used,
                tier_attempted=tiers_attempted,
                quality_score=quality_report.overall_score,
                quality_report=quality_report,
                cost=total_cost,
                extraction_time=extraction_time,
                total_time=total_time,
                success=True,
                metadata={'file_name': file_name}
            )
        else:
            return ExtractionResult(
                pages=[],
                tier_used=start_tier,
                tier_attempted=tiers_attempted,
                quality_score=0.0,
                quality_report=self.quality_checker.check_quality([]),
                cost=total_cost,
                extraction_time=0,
                total_time=total_time,
                success=False,
                error="All tiers failed"
            )
    
    def _extract_tier(self, tier: str, pdf_path, pdf_bytes, clean_text) -> Tuple[List[str], QualityReport]:
        """Extract with specific tier"""
        if tier == 'fast':
            # Level 1: Use Docling (no Tesseract OCR)
            if pdf_path:
                pages = self.fast_processor.extract_text(file_path=pdf_path)
            else:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = tmp.name
                pages = self.fast_processor.extract_text(file_path=tmp_path)
                Path(tmp_path).unlink()
            
            if clean_text and hasattr(self.fast_processor, 'text_cleaner'):
                pages = self.fast_processor.text_cleaner.clean_pages(pages)
        
        elif tier == 'balanced':
            # Level 2: Use VLM if quality < 0.70 from fast tier
            if not self._balanced_extractor:
                self._balanced_extractor = OpenRouterExtractor(
                    api_key=self.openrouter_api_key,
                    model='free'  # Use free Gemini model
                )
            pages = self._balanced_extractor.extract_from_pdf(pdf_path=pdf_path, pdf_bytes=pdf_bytes, dpi=self.image_dpi)
        
        elif tier == 'premium':
            # Level 3: Use Premium VLM if quality < 0.80 from balanced tier
            if not self._premium_extractor:
                self._premium_extractor = OpenRouterExtractor(
                    api_key=self.openrouter_api_key,
                    model='premium'
                )
            pages = self._premium_extractor.extract_from_pdf(pdf_path=pdf_path, pdf_bytes=pdf_bytes, dpi=self.image_dpi)
        
        quality_report = self.quality_checker.check_quality(pages)
        return pages, quality_report
