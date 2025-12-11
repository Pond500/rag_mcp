"""
Document Quality Validator
ตรวจสอบคุณภาพของเอกสารที่แปลงแล้ว และให้คำแนะนำ
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field

from src.utils.text_cleaner import TextStatistics

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """ปัญหาที่พบจากการตรวจสอบ"""
    type: str
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    message: str
    count: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """รายงานผลการตรวจสอบคุณภาพ"""
    file_path: str
    file_size_mb: float
    total_pages: int
    total_chars: int
    quality_score: float  # 0.0 - 1.0
    recommendation: str   # 'EXCELLENT', 'GOOD', 'FAIR', 'POOR', 'NEEDS_OCR'
    issues: List[ValidationIssue] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    
    def to_dict(self) -> dict:
        """แปลงเป็น dictionary"""
        return {
            'file_path': self.file_path,
            'file_size_mb': self.file_size_mb,
            'total_pages': self.total_pages,
            'total_chars': self.total_chars,
            'quality_score': self.quality_score,
            'recommendation': self.recommendation,
            'issues': [
                {
                    'type': issue.type,
                    'severity': issue.severity,
                    'message': issue.message,
                    'count': issue.count,
                    'suggestion': issue.suggestion
                }
                for issue in self.issues
            ],
            'statistics': self.statistics,
            'processing_time': self.processing_time
        }
    
    def get_severity_counts(self) -> Dict[str, int]:
        """นับจำนวนปัญหาตาม severity"""
        counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts


class DocumentValidator:
    """ตรวจสอบคุณภาพของเอกสารที่แปลงแล้ว"""
    
    # Thresholds
    MIN_CHARS_PER_PAGE = 100
    MAX_GLYPH_RATIO = 0.05  # 5% ของข้อความ
    MIN_QUALITY_SCORE = 0.7
    
    def __init__(self):
        self.text_stats = TextStatistics()
    
    def validate(
        self,
        file_path: str,
        extracted_pages: List[str],
        processing_time: float = 0.0
    ) -> ValidationReport:
        """
        ตรวจสอบคุณภาพเอกสารที่แปลงแล้ว
        
        Args:
            file_path: ที่อยู่ไฟล์
            extracted_pages: ข้อความที่แปลงแล้ว (list of pages)
            processing_time: เวลาที่ใช้ในการประมวลผล (seconds)
            
        Returns:
            ValidationReport
        """
        # Basic info
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        total_pages = len(extracted_pages)
        full_text = '\n\n'.join(extracted_pages)
        total_chars = len(full_text)
        
        # Get statistics
        stats = self.text_stats.get_statistics(full_text)
        
        # Initialize report
        report = ValidationReport(
            file_path=file_path,
            file_size_mb=file_size_mb,
            total_pages=total_pages,
            total_chars=total_chars,
            quality_score=1.0,
            recommendation='EXCELLENT',
            statistics=stats,
            processing_time=processing_time
        )
        
        # Run validation checks
        self._check_glyph_characters(report, full_text, stats)
        self._check_content_density(report, extracted_pages)
        self._check_text_distribution(report, stats)
        self._check_structure(report, full_text, stats)
        
        # Calculate final quality score
        report.quality_score = self._calculate_quality_score(report)
        report.recommendation = self._get_recommendation(report)
        
        return report
    
    def _check_glyph_characters(
        self,
        report: ValidationReport,
        full_text: str,
        stats: dict
    ):
        """ตรวจสอบ GLYPH characters"""
        glyph_count = stats['glyph_count']
        
        if glyph_count == 0:
            return
        
        glyph_ratio = glyph_count / max(1, stats['total_chars'])
        
        if glyph_ratio > self.MAX_GLYPH_RATIO:
            severity = 'CRITICAL' if glyph_ratio > 0.1 else 'HIGH'
            report.issues.append(ValidationIssue(
                type='GLYPH_CHARACTERS',
                severity=severity,
                message=f'Found {glyph_count} GLYPH characters ({glyph_ratio*100:.1f}% of text)',
                count=glyph_count,
                suggestion='Consider using OCR or different extraction method'
            ))
        elif glyph_count > 10:
            report.issues.append(ValidationIssue(
                type='GLYPH_CHARACTERS',
                severity='MEDIUM',
                message=f'Found {glyph_count} GLYPH characters',
                count=glyph_count,
                suggestion='Text may have font encoding issues'
            ))
    
    def _check_content_density(
        self,
        report: ValidationReport,
        pages: List[str]
    ):
        """ตรวจสอบความหนาแน่นของเนื้อหา"""
        if not pages:
            report.issues.append(ValidationIssue(
                type='EMPTY_DOCUMENT',
                severity='CRITICAL',
                message='No content extracted from document',
                suggestion='File may be corrupted or unsupported format'
            ))
            return
        
        # Check average characters per page
        avg_chars = sum(len(p) for p in pages) / len(pages)
        
        if avg_chars < self.MIN_CHARS_PER_PAGE:
            report.issues.append(ValidationIssue(
                type='LOW_CONTENT_DENSITY',
                severity='HIGH',
                message=f'Average {avg_chars:.0f} chars/page (< {self.MIN_CHARS_PER_PAGE})',
                suggestion='Document may be image-based or have extraction issues'
            ))
        
        # Check for empty pages
        empty_pages = sum(1 for p in pages if len(p.strip()) < 10)
        if empty_pages > 0:
            severity = 'HIGH' if empty_pages > len(pages) / 2 else 'MEDIUM'
            report.issues.append(ValidationIssue(
                type='EMPTY_PAGES',
                severity=severity,
                message=f'{empty_pages} out of {len(pages)} pages are nearly empty',
                count=empty_pages,
                suggestion='Check if document has image-only pages'
            ))
    
    def _check_text_distribution(
        self,
        report: ValidationReport,
        stats: dict
    ):
        """ตรวจสอบการกระจายตัวของข้อความ"""
        thai_ratio = stats['thai_ratio']
        
        # Check language distribution
        if thai_ratio < 0.1 and stats['thai_chars'] > 0:
            report.issues.append(ValidationIssue(
                type='LOW_THAI_CONTENT',
                severity='LOW',
                message=f'Thai content is only {thai_ratio*100:.1f}% of document',
                suggestion='Document may be primarily in another language'
            ))
    
    def _check_structure(
        self,
        report: ValidationReport,
        full_text: str,
        stats: dict
    ):
        """ตรวจสอบโครงสร้างเอกสาร"""
        # Check if has any structure (headers, tables, etc.)
        has_structure = (
            stats['header_count'] > 0 or
            stats['has_tables']
        )
        
        if not has_structure and stats['total_chars'] > 1000:
            report.issues.append(ValidationIssue(
                type='NO_STRUCTURE',
                severity='LOW',
                message='Document has no Markdown structure (headers/tables)',
                suggestion='Content may be plain text or poorly formatted'
            ))
        
        # Check table extraction quality
        if stats['has_tables']:
            # Count broken table markers
            broken_tables = full_text.count('||') + full_text.count('| |')
            if broken_tables > 5:
                report.issues.append(ValidationIssue(
                    type='BROKEN_TABLES',
                    severity='MEDIUM',
                    message='Tables may have formatting issues',
                    count=broken_tables,
                    suggestion='Consider using accurate table extraction mode'
                ))
    
    def _calculate_quality_score(self, report: ValidationReport) -> float:
        """
        คำนวณคะแนนคุณภาพ (0.0 - 1.0)
        
        เริ่มจาก 1.0 แล้วลดตาม severity ของปัญหา
        """
        score = 1.0
        
        severity_weights = {
            'LOW': 0.05,
            'MEDIUM': 0.1,
            'HIGH': 0.2,
            'CRITICAL': 0.4
        }
        
        for issue in report.issues:
            weight = severity_weights.get(issue.severity, 0.1)
            score -= weight
        
        return max(0.0, min(1.0, score))
    
    def _get_recommendation(self, report: ValidationReport) -> str:
        """
        ให้คำแนะนำตามคะแนนคุณภาพ
        """
        score = report.quality_score
        
        # Check for critical issues
        has_critical = any(i.severity == 'CRITICAL' for i in report.issues)
        if has_critical:
            return 'NEEDS_OCR'
        
        # Check for high GLYPH ratio
        glyph_issues = [i for i in report.issues if i.type == 'GLYPH_CHARACTERS']
        if glyph_issues and any(i.severity in ['HIGH', 'CRITICAL'] for i in glyph_issues):
            return 'NEEDS_OCR'
        
        # Based on score
        if score >= 0.9:
            return 'EXCELLENT'
        elif score >= 0.7:
            return 'GOOD'
        elif score >= 0.5:
            return 'FAIR'
        else:
            return 'POOR'
    
    def validate_batch(
        self,
        results: List[tuple]
    ) -> List[ValidationReport]:
        """
        ตรวจสอบหลายไฟล์พร้อมกัน
        
        Args:
            results: List of (file_path, extracted_pages, processing_time)
            
        Returns:
            List of ValidationReport
        """
        reports = []
        for file_path, pages, proc_time in results:
            try:
                report = self.validate(file_path, pages, proc_time)
                reports.append(report)
            except Exception as e:
                logger.error(f"Validation failed for {file_path}: {e}")
        
        return reports
    
    def print_report(self, report: ValidationReport):
        """แสดงรายงานแบบสวยงาม"""
        print("\n" + "="*60)
        print(f"📄 {Path(report.file_path).name}")
        print("="*60)
        print(f"Quality Score: {'🟢' if report.quality_score >= 0.7 else '🟡' if report.quality_score >= 0.5 else '🔴'} {report.quality_score:.2f}")
        print(f"Recommendation: {report.recommendation}")
        print(f"\nFile Size: {report.file_size_mb:.2f} MB")
        print(f"Pages: {report.total_pages}")
        print(f"Characters: {report.total_chars:,}")
        print(f"Processing Time: {report.processing_time:.2f}s")
        
        if report.statistics:
            print(f"\n📊 Statistics:")
            print(f"  - Thai ratio: {report.statistics.get('thai_ratio', 0)*100:.1f}%")
            print(f"  - Headers: {report.statistics.get('header_count', 0)}")
            print(f"  - Has tables: {'Yes' if report.statistics.get('has_tables') else 'No'}")
        
        if report.issues:
            print(f"\n⚠️  Issues Found ({len(report.issues)}):")
            severity_counts = report.get_severity_counts()
            print(f"  CRITICAL: {severity_counts['CRITICAL']}, HIGH: {severity_counts['HIGH']}, "
                  f"MEDIUM: {severity_counts['MEDIUM']}, LOW: {severity_counts['LOW']}")
            
            for i, issue in enumerate(report.issues, 1):
                icon = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(issue.severity, '⚪')
                print(f"\n  {i}. {icon} [{issue.severity}] {issue.type}")
                print(f"     {issue.message}")
                if issue.suggestion:
                    print(f"     💡 {issue.suggestion}")
        else:
            print("\n✅ No issues found!")
        
        print("="*60)
