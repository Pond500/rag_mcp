"""Quality Checker - Lightweight version"""
from typing import List
from dataclasses import dataclass


@dataclass
class QualityReport:
    overall_score: float
    text_quality: float
    word_quality: float
    consistency: float
    structure_quality: float
    content_density: float
    issues: List[str]
    recommendations: List[str]
    details: dict


class UnsupervisedQualityChecker:
    """Simple quality checker"""
    
    def check_quality(self, pages: List[str]) -> QualityReport:
        if not pages:
            return QualityReport(0, 0, 0, 0, 0, 0, ["No content"], ["Re-extract"], {})
        
        # Simple heuristics
        all_text = '\n'.join(pages)
        words = all_text.split()
        
        # Text quality (encoding, special chars)
        printable_ratio = sum(1 for c in all_text if c.isprintable() or c in '\n\t') / max(len(all_text), 1)
        text_quality = printable_ratio
        
        # Word quality (average length, vocabulary)
        avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
        word_quality = min(1.0, avg_word_len / 6.0) if 4 <= avg_word_len <= 10 else 0.6
        
        # Consistency (page length variance)
        page_lens = [len(p) for p in pages]
        avg_len = sum(page_lens) / len(pages)
        if avg_len > 0:
            variance = sum((l - avg_len) ** 2 for l in page_lens) / len(pages)
            cv = (variance ** 0.5) / avg_len
            consistency = max(0, 1.0 - cv)
        else:
            consistency = 0.5
        
        # Structure (headers, lists)
        lines = all_text.split('\n')
        headers = sum(1 for l in lines if l.startswith('#'))
        structure_quality = min(1.0, headers / max(len(pages) * 2, 1))
        
        # Density (chars per page)
        avg_chars = sum(len(p) for p in pages) / len(pages)
        if avg_chars >= 800:
            content_density = 1.0
        elif avg_chars >= 400:
            content_density = 0.8
        elif avg_chars >= 200:
            content_density = 0.6
        else:
            content_density = 0.4
        
        # Overall weighted score
        overall = (
            text_quality * 0.25 +
            word_quality * 0.20 +
            consistency * 0.15 +
            structure_quality * 0.20 +
            content_density * 0.20
        )
        
        # Issues and recommendations
        issues = []
        recommendations = []
        
        if overall >= 0.85:
            recommendations.append("✅ Excellent quality")
        elif overall >= 0.70:
            recommendations.append("✅ Good quality")
        else:
            issues.append("Low quality score")
            recommendations.append("⚠️ Consider re-extraction")
        
        return QualityReport(
            overall_score=overall,
            text_quality=text_quality,
            word_quality=word_quality,
            consistency=consistency,
            structure_quality=structure_quality,
            content_density=content_density,
            issues=issues,
            recommendations=recommendations,
            details={'pages': len(pages), 'chars': len(all_text), 'words': len(words)}
        )
