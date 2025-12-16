"""Document Processor - Hybrid Strategy

Extracts text from various file formats using a format-based router:
- MarkItDown: Excel, PowerPoint (fast, precise numerical data)
- Docling: PDF, Word, Images (advanced layout analysis, OCR)
- Simple: TXT, MD (direct extraction)
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
import re
import time
from io import BytesIO

from src.utils.text_cleaner import TextCleaner
from src.utils.document_validator import DocumentValidator, ValidationReport
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractOcrOptions

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process documents using hybrid extraction strategy
    
    Format-Based Router:
    - MarkItDown: .xlsx, .xls, .pptx, .ppt (optimized for Office files)
    - Docling: .pdf, .docx, .doc, images (advanced layout + OCR)
    - Simple: .txt, .md (plain text)
    
    Usage:
        processor = DocumentProcessor(config)
        pages = processor.extract_text(file_path="report.xlsx")  # Auto-routes to MarkItDown
        pages = processor.extract_text(file_path="doc.pdf")      # Auto-routes to Docling
        chunks = processor.chunk_text(pages, chunk_size=1000, overlap=200)
    """
    
    def __init__(self, config=None):
        self.config = config
        self.chunk_size = getattr(config, "chunk_size", 1000) if config else 1000
        self.chunk_overlap = getattr(config, "chunk_overlap", 200) if config else 200
        
        # Initialize Docling converter with lazy loading
        self._converter = None
        self._docling_config = None
        
        # Initialize MarkItDown converter with lazy loading
        self._markitdown = None
        
        # Initialize utilities
        self.text_cleaner = TextCleaner()
        self.validator = DocumentValidator()
    
    def _get_converter(self):
        """Lazy initialization of Docling converter with advanced settings (Fixed for Thai OCR)"""
        if self._converter is None:
            try:
                import os
                # 1. ระบุ Path ของ Tesseract (Homebrew M1/M2/M3) สำคัญมาก!
                os.environ["TESSDATA_PREFIX"] = "/opt/homebrew/share/tessdata"

                # Import ที่จำเป็น
                from docling.datamodel.base_models import InputFormat
                from docling.document_converter import DocumentConverter, PdfFormatOption
                from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode, TesseractOcrOptions
                
                # Default settings
                enable_ocr = True
                table_mode = "accurate"
                enable_vlm = False
                img_scale = 2.0
                
                # พยายามอ่านจาก Config (ถ้ามี) แต่จะเน้น Default ที่เราตั้งข้างล่างเพื่อความชัวร์
                if self.config and hasattr(self.config, 'docling'):
                    enable_ocr = getattr(self.config.docling, 'enable_ocr', True)
                    # เราจะข้าม ocr_engine จาก config ไปก่อน เพื่อบังคับใช้ Tesseract แก้ปัญหา
                    table_mode = getattr(self.config.docling, 'table_mode', 'accurate')
                    enable_vlm = getattr(self.config.docling, 'enable_vlm', False)
                    img_scale = getattr(self.config.docling, 'image_resolution_scale', 2.0)

                # Configure PDF pipeline options
                pipeline_options = PdfPipelineOptions()
                pipeline_options.images_scale = img_scale
                pipeline_options.do_ocr = enable_ocr
                
                # Set table extraction mode
                pipeline_options.do_table_structure = True
                if table_mode == "accurate":
                    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
                    pipeline_options.table_structure_options.do_cell_matching = True # ช่วยจับคู่ Text ลงตารางให้แม่นขึ้น
                else:
                    pipeline_options.table_structure_options.mode = TableFormerMode.FAST
                
                # 2. Configure OCR engine (บังคับใช้ Tesseract สำหรับภาษาไทย)
                if enable_ocr:
                    try:
                        # กำหนดภาษา: ไทย + อังกฤษ
                        lang_list = ["tha", "eng"]
                        
                        pipeline_options.ocr_options = TesseractOcrOptions(
                            lang=lang_list
                        )
                        logger.info(f"Configured Tesseract OCR with languages: {lang_list}")
                    except Exception as e:
                        logger.warning(f"Failed to configure Tesseract OCR: {e}")

                # Enable VLM for picture descriptions if configured
                if enable_vlm:
                    pipeline_options.generate_picture_images = True
                    logger.info("VLM enabled for picture descriptions")
                
                # 3. Initialize converter (แก้ไข Syntax ตรงนี้ให้ถูกต้อง)
                self._converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                    }
                )
                
                logger.info("Initialized Docling converter (Engine=Tesseract, TableMode=%s)", table_mode)
                
            except ImportError as e:
                logger.error("Docling not installed: %s", e)
                raise ImportError("Please install docling: pip install docling>=2.0.0")
            except Exception as e:
                logger.warning("Failed to configure advanced Docling options: %s. Using defaults.", e)
                # Fallback to basic converter
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
                logger.info("Initialized Docling converter with default settings")
        
        return self._converter
    
    def _get_markitdown(self):
        """Lazy initialization of MarkItDown converter
        
        MarkItDown (by Microsoft) is optimized for Office files:
        - Faster processing for Excel/PowerPoint
        - Better handling of numerical data and formulas
        - Preserves table structure accurately
        
        Returns:
            MarkItDown instance
        """
        if self._markitdown is None:
            try:
                from markitdown import MarkItDown
                self._markitdown = MarkItDown()
                logger.info("Initialized MarkItDown converter for Office files")
            except ImportError as e:
                logger.error("MarkItDown not installed: %s", e)
                raise ImportError("Please install markitdown: pip install markitdown")
        
        return self._markitdown
    
    def _fix_thai_encoding(self, text: str) -> str:
        """
        Fix Thai character encoding issues
        
        Common issues:
        - ด�า → ดำ 
        - ส�า → สำ
        - ท�า → ทำ
        
        Args:
            text: Text with potential encoding issues
            
        Returns:
            Fixed text
        """
        if not text:
            return text
        
        try:
            # Method 1: Try to fix by re-encoding.
            # Sometimes the text is UTF-8 decoded as Latin-1 or vice versa
            try:
                # If text contains replacement character, try to fix
                if '�' in text:
                    # Try encoding as latin-1 and decoding as utf-8
                    try:
                        fixed = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
                        if '�' not in fixed or fixed.count('�') < text.count('�'):
                            text = fixed
                    except:
                        pass
                    
                    # Try other encoding combinations
                    try:
                        fixed = text.encode('cp1252', errors='ignore').decode('utf-8', errors='ignore')
                        if '�' not in fixed or fixed.count('�') < text.count('�'):
                            text = fixed
                    except:
                        pass
            except:
                pass
            
            # Method 2: Use Unicode normalization
            import unicodedata
            
            # Normalize to composed form (NFC) - combines base + combining characters
            text = unicodedata.normalize('NFC', text)
            
            # Method 3: Fix common Thai character issues
            # Thai vowel combining characters that might appear as �
            thai_fixes = {
                'ำ': '\u0e33',  
                'ั': '\u0e31',  
                'ิ': '\u0e34',  
                'ี': '\u0e35',  
                'ึ': '\u0e36',  
                'ื': '\u0e37',  
                'ุ': '\u0e38',  
                'ู': '\u0e39',  
                '็': '\u0e47',  
                '่': '\u0e48',  
                '้': '\u0e49',  
                '๊': '\u0e4a',  
                '๋': '\u0e4b',  
                'ะ': '\u0e30',  
            }
            
            # If we still have replacement characters, log warning
            if '�' in text:
                logger.warning("Text still contains replacement characters after encoding fix")
            
            return text
            
        except Exception as e:
            logger.error(f"Error fixing Thai encoding: {e}")
            return text
    
    def _clean_markdown(self, text: str) -> str:
        """
        Clean Markdown text from common PDF parsing artifacts
        
        This method removes:
        - GLYPH tags (e.g., GLYPH<29>, GLYPH&lt;19&gt;)
        - Excessive newlines (3+ consecutive newlines)
        - Lines with only dots (Table of Contents artifacts)
        - Redundant whitespace
        
        Args:
            text: Raw Markdown text from Docling
            
        Returns:
            Cleaned Markdown text
        """
        if not text:
            return text
        
        # Remove GLYPH tags and variants
        # Patterns: GLYPH<29>, GLYPH&lt;19&gt;, GLYPH<c=29,font=...>
        text = re.sub(r'GLYPH<[^>]+>', '', text)
        text = re.sub(r'GLYPH&lt;[^&]+&gt;', '', text)
        text = re.sub(r'GLYPH\([^)]+\)', '', text)
        
        # Remove lines that are just dots (common in TOC)
        # Example: "Chapter 1 ................... 5"
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip lines with excessive dots (more than 10 consecutive dots)
            if re.match(r'^[.\s]{10,}$', line):
                continue
            # Skip lines that are mostly dots with minimal other content
            if len(re.findall(r'\.', line)) > len(line) * 0.7:
                continue
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Collapse excessive newlines (3+ → 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing/leading whitespace on each line
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove spaces before punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        
        # Normalize multiple spaces to single space
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def extract_text(
        self, 
        file_path: str, 
        file_content: Optional[bytes] = None,
        clean_text: bool = True,
        validate: bool = False
    ) -> List[str]:
        """Extract text from file using hybrid strategy (MarkItDown + Docling)
        
        Format-Based Router:
        - Group A (MarkItDown): Excel, PowerPoint → Fast, precise numerical data
        - Group B (Docling): PDF, Word, Images → Advanced layout analysis, OCR
        - Group C (Simple): TXT, MD → Direct text extraction
        
        Args:
            file_path: Path to file (used for extension detection)
            file_content: Optional raw bytes (if provided, will use instead of reading file)
            clean_text: ทำความสะอาดข้อความหลังแปลง (แนะนำ: True)
            validate: สร้าง validation report (ใช้เวลาเพิ่มเล็กน้อย)
            
        Returns:
            List of extracted text sections in Markdown format
        """
        ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).name
        start_time = time.time()
        
        logger.info(f"📄 Extracting text from: {file_name} ({ext})")
        
        try:
            # Group C: Plain text files - direct extraction
            if ext in [".txt", ".md"]:
                logger.info(f"📝 Using simple text extraction for {ext}")
                pages = self._extract_text_simple(file_path, file_content)
            
            # Group A: Office files (Excel, PowerPoint) - use MarkItDown
            elif ext in [".xlsx", ".xls", ".pptx", ".ppt"]:
                logger.info(f"📊 Using MarkItDown for Office file: {ext}")
                try:
                    pages = self._extract_with_markitdown(file_path, file_content)
                    
                    # Fallback to Docling if MarkItDown fails
                    if not pages:
                        logger.warning(f"⚠️  MarkItDown extraction empty, falling back to Docling")
                        pages = self._extract_with_docling(file_path, file_content)
                        
                except Exception as e:
                    logger.warning(f"⚠️  MarkItDown failed ({ext}), falling back to Docling: {str(e)}")
                    pages = self._extract_with_docling(file_path, file_content)
            
            # Group B: PDFs, Word docs, Images - use Docling
            elif ext in [".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"]:
                logger.info(f"📑 Using Docling for document: {ext}")
                pages = self._extract_with_docling(file_path, file_content)
            
            # Fallback: Unknown format - try Docling
            else:
                logger.info(f"❓ Unknown format {ext}, attempting Docling extraction")
                pages = self._extract_with_docling(file_path, file_content)
            
            # Log extraction stats
            extraction_time = time.time() - start_time
            total_chars = sum(len(p) for p in pages) if pages else 0
            logger.info(f"✅ Extracted {len(pages)} sections ({total_chars:,} chars) in {extraction_time:.2f}s")
            
            # Clean text if requested
            if clean_text and pages:
                logger.info(f"🧹 Cleaning extracted text...")
                pages = self.text_cleaner.clean_pages(pages)
            
            # Validate if requested
            if validate and pages:
                processing_time = time.time() - start_time
                report = self.validator.validate(file_path, pages, processing_time)
                logger.info(f"✅ Validation: Quality={report.quality_score:.2f}, "
                          f"Recommendation={report.recommendation}")
                
                # Log issues if any
                if report.issues:
                    for issue in report.issues:
                        if issue.severity in ['HIGH', 'CRITICAL']:
                            logger.warning(f"⚠️  {issue.type}: {issue.message}")
            
            return pages
            
        except Exception as e:
            logger.error(f"❌ Failed to extract text from {file_name}: {str(e)}", exc_info=True)
            return []
    
    def extract_and_validate(
        self,
        file_path: str,
        file_content: Optional[bytes] = None,
        clean_text: bool = True
    ) -> Tuple[List[str], ValidationReport]:
        """
        แปลงเอกสารและ return พร้อม validation report
        
        Args:
            file_path: Path to file
            file_content: Optional file bytes
            clean_text: ทำความสะอาดข้อความ
            
        Returns:
            (pages, validation_report)
        """
        start_time = time.time()
        ext = Path(file_path).suffix.lower()
        
        try:
            # Extract
            if ext in [".txt", ".md"]:
                pages = self._extract_text_simple(file_path, file_content)
            else:
                pages = self._extract_with_docling(file_path, file_content)
            
            # Clean
            if clean_text and pages:
                pages = self.text_cleaner.clean_pages(pages)
            
            # Validate
            processing_time = time.time() - start_time
            report = self.validator.validate(file_path, pages, processing_time)
            
            return pages, report
            
        except Exception as e:
            logger.error("Failed to extract and validate %s: %s", file_path, e)
            # Return empty pages and error report
            processing_time = time.time() - start_time
            from src.utils.document_validator import ValidationReport, ValidationIssue
            error_report = ValidationReport(
                file_path=file_path,
                file_size_mb=0.0,
                total_pages=0,
                total_chars=0,
                quality_score=0.0,
                recommendation='FAILED',
                processing_time=processing_time
            )
            error_report.issues.append(ValidationIssue(
                type='EXTRACTION_ERROR',
                severity='CRITICAL',
                message=str(e),
                suggestion='Check file format and integrity'
            ))
            return [], error_report
    
    def _extract_with_docling(self, file_path: str, file_content: Optional[bytes]) -> List[str]:
        """Extract text using Docling DocumentConverter with structure preservation
        
        This method extracts text while preserving document structure:
        - Processes document items hierarchically (headers, paragraphs, tables, lists)
        - Maintains semantic boundaries for better RAG performance
        - Cleans artifacts while preserving structure
        
        Args:
            file_path: Path to document
            file_content: Optional file bytes
            
        Returns:
            List of text sections (one per major document section OR per page)
        """
        file_name = Path(file_path).name
        start_time = time.time()
        
        logger.debug(f"🔄 Docling: Processing {file_name}...")
        
        try:
            converter = self._get_converter()
            
            # Docling requires either file path or BytesIO stream
            if file_content:
                # Create a temporary BytesIO object with proper name
                stream = BytesIO(file_content)
                stream.name = Path(file_path).name  # Docling uses this for format detection
                result = converter.convert(stream)
            else:
                result = converter.convert(file_path)
            
            # Try page-based extraction first (better for verification)
            logger.debug(f"🔄 Extracting by pages...")
            sections = self._extract_by_pages(result.document)
            
            # If structured extraction fails, fall back to full markdown
            if not sections or (len(sections) == 1 and len(sections[0]) < 100):
                logger.debug(f"🔄 Using full document markdown export as fallback")
                full_markdown = result.document.export_to_markdown()
                
                if not full_markdown or len(full_markdown.strip()) < 10:
                    logger.warning(f"⚠️  Docling returned empty content for {file_name}")
                    return []
                
                # Split large markdown into manageable sections
                sections = [full_markdown]
            
            # Fix Thai encoding issues if configured
            fix_thai = True
            if self.config and hasattr(self.config, 'docling'):
                fix_thai = getattr(self.config.docling, 'fix_thai_encoding', True)
            
            if fix_thai:
                sections = [self._fix_thai_encoding(s) for s in sections]
            
            # Clean artifacts if configured
            clean_artifacts = True
            if self.config and hasattr(self.config, 'docling'):
                clean_artifacts = getattr(self.config.docling, 'clean_artifacts', True)
            
            if clean_artifacts:
                original_total = sum(len(s) for s in sections)
                sections = [self._clean_markdown(s) for s in sections]
                cleaned_total = sum(len(s) for s in sections)
                
                if original_total != cleaned_total:
                    logger.info("Cleaned sections: %d → %d chars (removed %d chars of artifacts)",
                               original_total, cleaned_total, original_total - cleaned_total)
            
            # Filter out empty sections
            sections = [s for s in sections if s.strip()]
            
            logger.info("Extracted %d sections (%d total chars) from %s", 
                       len(sections), sum(len(s) for s in sections), Path(file_path).name)
            
            return sections
            
        except Exception as e:
            logger.error("Docling extraction failed for %s: %s", file_path, e)
            return []
    
    def _extract_with_markitdown(self, file_path: str, file_content: Optional[bytes]) -> List[str]:
        """Extract text using MarkItDown for Office files (Excel, PowerPoint)
        
        MarkItDown is optimized for structured Office documents:
        - Excel: Preserves formulas, formatting, and numerical precision
        - PowerPoint: Extracts slide content with proper hierarchy
        - Fast processing without heavy ML models
        
        Args:
            file_path: Path to document (used for extension detection)
            file_content: Optional file bytes
            
        Returns:
            List containing extracted markdown text
        """
        import tempfile
        import os
        
        file_name = Path(file_path).name
        start_time = time.time()
        temp_file_path = None
        
        logger.debug(f"🔄 MarkItDown: Processing {file_name}...")
        
        try:
            markitdown = self._get_markitdown()
            
            # MarkItDown requires a file path, so write bytes to temp file if needed
            if file_content:
                # Create temporary file with correct extension
                ext = Path(file_path).suffix
                with tempfile.NamedTemporaryFile(mode='wb', suffix=ext, delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name
                
                logger.debug(f"📝 Created temp file for MarkItDown: {temp_file_path}")
                result = markitdown.convert(temp_file_path)
            else:
                result = markitdown.convert(file_path)
            
            # MarkItDown returns a result object with text_content attribute
            markdown_text = result.text_content if hasattr(result, 'text_content') else str(result)
            
            if not markdown_text or len(markdown_text.strip()) < 10:
                logger.warning(f"⚠️  MarkItDown returned empty content for {file_name}")
                return []
            
            extraction_time = time.time() - start_time
            logger.debug(f"✅ MarkItDown extracted {len(markdown_text):,} chars in {extraction_time:.2f}s")
            
            # Clean artifacts if configured
            clean_artifacts = True
            if self.config and hasattr(self.config, 'docling'):
                clean_artifacts = getattr(self.config.docling, 'clean_artifacts', True)
            
            if clean_artifacts:
                markdown_text = self._clean_markdown(markdown_text)
            
            logger.info("MarkItDown extracted %d chars from %s", 
                       len(markdown_text), Path(file_path).name)
            
            return [markdown_text]
            
        except Exception as e:
            logger.error("MarkItDown extraction failed for %s: %s", file_path, e)
            return []
        
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning("Failed to delete temp file %s: %s", temp_file_path, e)
    
    def _extract_by_pages(self, document) -> List[str]:
        """Extract document content by pages (for easier verification)
        
        This method groups content by page number, making it easier to:
        - Verify extraction quality page by page
        - Debug specific pages with issues
        - Compare with original document
        
        Args:
            document: Docling Document object
            
        Returns:
            List of page texts (Markdown format), one string per page
        """
        try:
            from docling_core.types.doc import DocItemLabel
            
            # Dictionary to store content by page
            pages_dict = {}
            
            # Iterate through document items
            for item, level in document.iterate_items():
                # Get page number
                page_no = getattr(item.prov[0], 'page_no', 0) if hasattr(item, 'prov') and item.prov else 0
                
                # Initialize page if not exists
                if page_no not in pages_dict:
                    pages_dict[page_no] = []
                
                # Get text from item
                item_text = None
                try:
                    if hasattr(item, 'export_to_markdown'):
                        try:
                            item_text = item.export_to_markdown(doc=document).strip()
                        except TypeError:
                            item_text = item.export_to_markdown().strip()
                    elif hasattr(item, 'text'):
                        item_text = str(item.text).strip()
                        # Add markdown formatting based on label
                        item_label = getattr(item, 'label', None)
                        if item_label in [DocItemLabel.TITLE, DocItemLabel.SECTION_HEADER]:
                            header_level = min(level + 1, 6)
                            item_text = f"{'#' * header_level} {item_text}"
                except Exception as e:
                    logger.debug(f"Error exporting item: {e}")
                    continue
                
                if item_text:
                    pages_dict[page_no].append(item_text)
            
            # Convert dictionary to sorted list of pages
            if not pages_dict:
                logger.warning("No pages extracted, falling back to full document")
                return [document.export_to_markdown()]
            
            # Sort by page number and join content
            pages = []
            for page_no in sorted(pages_dict.keys()):
                page_content = '\n\n'.join(pages_dict[page_no])
                if page_content.strip():
                    # Add page header for easy identification
                    page_text = f"## Page {page_no}\n\n{page_content}"
                    pages.append(page_text)
            
            logger.info(f"✅ Extracted {len(pages)} pages")
            return pages
            
        except ImportError:
            logger.warning("Docling core types not available, falling back to full document")
            return [document.export_to_markdown()]
        except Exception as e:
            logger.warning(f"Page extraction failed, falling back to full document: {e}")
            return [document.export_to_markdown()]
    
    def _extract_structured_sections(self, document) -> List[str]:
        """Extract document content as structured sections (by headers)
        
        This method processes the Docling document model to create semantic sections:
        - Groups content by headers (creates natural boundaries)
        - Preserves tables, lists, and formatting
        - Splits large sections for better chunking
        
        Args:
            document: Docling Document object
            
        Returns:
            List of section texts (Markdown format)
        """
        try:
            from docling_core.types.doc import DocItemLabel
            
            sections = []
            current_section = []
            current_level = 0
            max_section_size = 10000  # Split sections larger than 10K chars
            
            # Iterate through document items
            for item, level in document.iterate_items():
                # Get text from item (handle different item types)
                item_text = None
                
                try:
                    if hasattr(item, 'export_to_markdown'):
                        # Try to call with doc argument first (for items like PictureItem)
                        try:
                            item_text = item.export_to_markdown(doc=document).strip()
                        except TypeError:
                            # Fallback: call without doc argument
                            item_text = item.export_to_markdown().strip()
                    elif hasattr(item, 'text'):
                        # Fallback for items without export_to_markdown
                        item_text = str(item.text).strip()
                        # Add markdown formatting based on label
                        if hasattr(item, 'label') and item.label in [DocItemLabel.TITLE, DocItemLabel.SECTION_HEADER]:
                            # Format as header based on level
                            header_level = min(level + 1, 6)  # Max 6 levels in Markdown
                            item_text = f"{'#' * header_level} {item_text}"
                except Exception as e:
                    logger.debug(f"Error exporting item: {e}")
                    continue
                
                if not item_text:
                    continue
                
                if not item_text:
                    continue
                
                # Check if this is a header (safely check for label)
                item_label = getattr(item, 'label', None)
                
                if item_label in [DocItemLabel.TITLE, DocItemLabel.SECTION_HEADER]:
                    # Save previous section if it exists
                    if current_section:
                        section_text = '\n\n'.join(current_section)
                        
                        # Split large sections
                        if len(section_text) > max_section_size:
                            sections.extend(self._split_large_section(section_text, max_section_size))
                        else:
                            sections.append(section_text)
                        
                        current_section = []
                    
                    # Start new section with header
                    current_section.append(item_text)
                    current_level = level
                
                elif item_label == DocItemLabel.PARAGRAPH:
                    current_section.append(item_text)
                
                elif item_label == DocItemLabel.TABLE:
                    # Tables are important - keep them intact
                    current_section.append(item_text)
                
                elif item_label in [DocItemLabel.LIST_ITEM, DocItemLabel.CODE]:
                    current_section.append(item_text)
                
                else:
                    # Other content (captions, footnotes, pictures, etc.)
                    current_section.append(item_text)
            
            # Add final section
            if current_section:
                section_text = '\n\n'.join(current_section)
                
                if len(section_text) > max_section_size:
                    sections.extend(self._split_large_section(section_text, max_section_size))
                else:
                    sections.append(section_text)
            
            # Fallback: if no sections created, use full document export
            if not sections:
                logger.warning("No sections extracted, falling back to full document export")
                sections = [document.export_to_markdown()]
            
            return sections
            
        except ImportError:
            logger.warning("Docling core types not available, falling back to simple export")
            return [document.export_to_markdown()]
        except Exception as e:
            logger.error("Failed to extract structured sections: %s", e)
            # Fallback to simple export
            return [document.export_to_markdown()]
    
    def _split_large_section(self, text: str, max_size: int) -> List[str]:
        """Split a large section into smaller subsections
        
        Args:
            text: Section text to split
            max_size: Maximum size per subsection
            
        Returns:
            List of subsection texts
        """
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        
        subsections = []
        current_subsection = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            # If adding this paragraph exceeds max_size, start new subsection
            if current_size + para_size > max_size and current_subsection:
                subsections.append('\n\n'.join(current_subsection))
                current_subsection = [para]
                current_size = para_size
            else:
                current_subsection.append(para)
                current_size += para_size
        
        # Add remaining subsection
        if current_subsection:
            subsections.append('\n\n'.join(current_subsection))
        
        return subsections
    
    def _extract_text_simple(self, file_path: str, file_content: Optional[bytes]) -> List[str]:
        """Extract text from plain text files (TXT/MD)
        
        Args:
            file_path: Path to text file
            file_content: Optional file bytes
            
        Returns:
            List containing single text string
        """
        try:
            if file_content:
                text = file_content.decode('utf-8', errors='ignore')
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            return [text] if text.strip() else []
            
        except Exception as e:
            logger.error("Text extraction failed: %s", e)
            return []
    
    def chunk_text(
        self,
        pages: List[str],
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Chunk text with Markdown-aware splitting
        
        This method attempts to respect Markdown structure (headers, paragraphs, lists)
        when chunking to maintain semantic coherence.
        
        Args:
            pages: List of page texts (usually single Markdown document from Docling)
            chunk_size: Characters per chunk (uses config default if None)
            chunk_overlap: Overlap between chunks (uses config default if None)
            
        Returns:
            List of chunks with metadata: [{"text": "...", "page": 1, "chunk_index": 0}, ...]
        """
        start_time = time.time()
        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap
        
        logger.debug(f"🔄 Chunking {len(pages)} pages (size={chunk_size}, overlap={chunk_overlap})...")
        
        chunks = []
        chunk_index = 0
        
        for page_num, page_text in enumerate(pages, start=1):
            # Try Markdown-aware chunking first
            page_chunks = self._chunk_markdown_text(page_text, chunk_size, chunk_overlap)
            
            # Add metadata to each chunk
            for chunk_text in page_chunks:
                if chunk_text.strip():
                    chunks.append({
                        "text": chunk_text,
                        "page": page_num,
                        "chunk_index": chunk_index,
                    })
                    chunk_index += 1
        
        chunking_time = time.time() - start_time
        avg_chunk_size = sum(len(c["text"]) for c in chunks) / len(chunks) if chunks else 0
        logger.info(f"✂️  Created {len(chunks)} chunks (avg size: {avg_chunk_size:.0f} chars) in {chunking_time:.2f}s")
        return chunks
    
    def _chunk_markdown_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text intelligently with semantic-aware chunking
        
        Enhanced strategy for better RAG performance:
        1. Preserve semantic boundaries (sentences, paragraphs)
        2. Keep headers with their content
        3. Respect table and list structures
        4. Add overlap at natural boundaries
        
        Args:
            text: Markdown text to split (already a semantic section from Docling)
            chunk_size: Target size for chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # If section is already small enough, return as-is
        if len(text) <= chunk_size:
            return [text]
        
        # Try to split by sub-headers first (###, ####)
        subheader_pattern = r'^(#{2,6}\s+.+)$'
        sections = re.split(f'({subheader_pattern})', text, flags=re.MULTILINE)
        
        chunks = []
        current_chunk = ""
        current_header = ""
        
        for section in sections:
            if not section.strip():
                continue
            
            # Check if this is a sub-header
            if re.match(subheader_pattern, section):
                current_header = section
                continue
            
            # Try to add section to current chunk
            if current_header:
                potential_chunk = f"{current_chunk}\n\n{current_header}\n\n{section}" if current_chunk else f"{current_header}\n\n{section}"
            else:
                potential_chunk = f"{current_chunk}\n\n{section}" if current_chunk else section
            
            if len(potential_chunk) <= chunk_size:
                current_chunk = potential_chunk
                current_header = ""  # Reset header after use
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Handle large section
                section_with_header = f"{current_header}\n\n{section}" if current_header else section
                
                if len(section_with_header) > chunk_size:
                    # Split by semantic units (sentences and paragraphs)
                    para_chunks = self._split_by_semantic_units(
                        section_with_header,
                        chunk_size,
                        chunk_overlap
                    )
                    chunks.extend(para_chunks)
                    current_chunk = ""
                else:
                    current_chunk = section_with_header.strip()
                
                current_header = ""
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If no chunks created, fall back to semantic splitting
        if not chunks:
            chunks = self._split_by_semantic_units(text, chunk_size, chunk_overlap)
        
        return chunks
    
    def _split_by_semantic_units(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text by semantic units (sentences/paragraphs) for better RAG
        
        This method tries to create chunks at natural boundaries:
        - Prefer splitting at paragraph breaks
        - Fall back to sentence boundaries
        - Add overlap at semantic boundaries
        
        Args:
            text: Text to split
            chunk_size: Target chunk size
            chunk_overlap: Overlap size
            
        Returns:
            List of chunks
        """
        # Split by paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Try to add paragraph to current chunk
            potential_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            
            if len(potential_chunk) <= chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If paragraph is too large, split by sentences
                if len(para) > chunk_size:
                    sentence_chunks = self._split_by_sentences(para, chunk_size, chunk_overlap)
                    chunks.extend(sentence_chunks)
                    current_chunk = ""
                else:
                    # Add overlap from previous chunk if available
                    if chunks and chunk_overlap > 0:
                        overlap_text = self._get_overlap_text(chunks[-1], chunk_overlap)
                        current_chunk = f"{overlap_text}\n\n{para}" if overlap_text else para
                    else:
                        current_chunk = para
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _split_by_sentences(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text by sentences with overlap
        
        Args:
            text: Text to split
            chunk_size: Target chunk size
            chunk_overlap: Overlap size
            
        Returns:
            List of chunks
        """
        # Split by sentence boundaries (Thai and English)
        # Thai: ใช้ ., !, ?, จบประโยค
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Zก-ฮ])|(?<=[。！？])'
        sentences = re.split(sentence_pattern, text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            potential_chunk = f"{current_chunk} {sentence}" if current_chunk else sentence
            
            if len(potential_chunk) <= chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If sentence is too large, use character splitting
                if len(sentence) > chunk_size:
                    char_chunks = self._split_by_characters(sentence, chunk_size, chunk_overlap)
                    chunks.extend(char_chunks)
                    current_chunk = ""
                else:
                    # Add overlap if available
                    if chunks and chunk_overlap > 0:
                        overlap_text = self._get_overlap_text(chunks[-1], chunk_overlap)
                        current_chunk = f"{overlap_text} {sentence}" if overlap_text else sentence
                    else:
                        current_chunk = sentence
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get last N characters from text for overlap
        
        Args:
            text: Source text
            overlap_size: Number of characters to take
            
        Returns:
            Overlap text (tries to break at word boundary)
        """
        if len(text) <= overlap_size:
            return text
        
        # Take last overlap_size chars
        overlap = text[-overlap_size:]
        
        # Try to start at word boundary
        space_idx = overlap.find(' ')
        if space_idx > 0:
            overlap = overlap[space_idx+1:]
        
        return overlap.strip()
    
    def _split_by_paragraphs(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text by paragraphs with semantic awareness (DEPRECATED - use _split_by_semantic_units)
        
        This method is kept for backward compatibility but delegates to the new semantic splitter.
        
        Args:
            text: Text to split
            chunk_size: Target chunk size
            chunk_overlap: Overlap size
            
        Returns:
            List of chunks
        """
        return self._split_by_semantic_units(text, chunk_size, chunk_overlap)
    
    def _split_by_characters(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Fall back to character-based splitting with overlap
        
        Args:
            text: Text to split
            chunk_size: Chunk size
            chunk_overlap: Overlap size
            
        Returns:
            List of chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk)
            
            start += chunk_size - chunk_overlap
            
            if end >= len(text):
                break
        
        return chunks
