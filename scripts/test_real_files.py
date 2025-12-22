#!/usr/bin/env python3
"""
ทดสอบ Hybrid Document Processing กับไฟล์จริง
"""
import sys
from pathlib import Path
import time

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.document_processor import DocumentProcessor
from src.config.settings import Settings


def test_file(file_path: str, file_type: str):
    """ทดสอบการแปลงไฟล์"""
    
    print('=' * 70)
    print(f'🧪 ทดสอบ: {file_type}')
    print('=' * 70)
    print()
    print(f'📄 ไฟล์: {file_path}')
    
    if not Path(file_path).exists():
        print(f'❌ ไม่พบไฟล์: {file_path}')
        return False
    
    # เช็คขนาดไฟล์
    size = Path(file_path).stat().st_size
    print(f'📦 ขนาด: {size:,} bytes ({size/1024:.1f} KB)')
    print()
    
    # สร้าง processor
    settings = Settings()
    processor = DocumentProcessor(config=settings)
    
    # แปลงไฟล์
    print('🔄 กำลังแปลง...')
    start = time.time()
    
    try:
        pages = processor.extract_text(file_path, clean_text=True)
        elapsed = time.time() - start
        
        print()
        print(f'✅ สำเร็จ!')
        print(f'⏱️  เวลา: {elapsed:.2f} วินาที')
        print(f'📊 จำนวนส่วน: {len(pages)}')
        
        if pages:
            total_chars = sum(len(p) for p in pages)
            print(f'📝 ตัวอักษรทั้งหมด: {total_chars:,} ตัว')
            
            # นับตัวอักษรไทย
            all_text = ' '.join(pages)
            thai_count = sum(1 for c in all_text if '\u0e00' <= c <= '\u0e7f')
            has_replacement = '�' in all_text
            
            print(f'🇹🇭 ตัวอักษรไทย: {thai_count:,} ตัว ({thai_count/total_chars*100:.1f}%)')
            print(f'❌ มี � (replacement): {"มี ⚠️" if has_replacement else "ไม่มี ✅"}')
            print()
            
            # แสดงตัวอย่าง
            print('📋 ตัวอย่าง 500 ตัวอักษรแรก:')
            print('-' * 70)
            sample = pages[0][:500]
            print(sample)
            print()
            
            # ถ้ามีหลายส่วน แสดงภาพรวม
            if len(pages) > 1:
                print('📑 ภาพรวมทุกส่วน:')
                print('-' * 70)
                for i, page in enumerate(pages[:3], 1):
                    print(f'ส่วนที่ {i}: {len(page):,} ตัวอักษร')
                    print(f'   ตัวอย่าง: {page[:100]}...')
                    print()
                
                if len(pages) > 3:
                    print(f'... และอีก {len(pages) - 3} ส่วน')
            
            return True
        else:
            print('⚠️  ไม่มีข้อมูล (empty result)')
            return False
            
    except Exception as e:
        elapsed = time.time() - start
        print()
        print(f'❌ ล้มเหลว! (ใช้เวลา {elapsed:.2f} วินาที)')
        print(f'Error: {e}')
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    print()
    print('🚀 ทดสอบ Hybrid Document Processing')
    print()
    
    # ทดสอบ PDF
    pdf_result = test_file(
        '/Users/pond500/RAG/data/62-2.pdf',
        'PDF Document (ใช้ Docling)'
    )
    
    print()
    print()
    
    # ทดสอบ DOCX
    docx_result = test_file(
        '/Users/pond500/RAG/data/บทที่ 2.docx',
        'DOCX Document (ใช้ Docling)'
    )
    
    print()
    print('=' * 70)
    print('📊 สรุปผลการทดสอบ')
    print('=' * 70)
    print()
    print(f'PDF (62-2.pdf):        {"✅ ผ่าน" if pdf_result else "❌ ไม่ผ่าน"}')
    print(f'DOCX (บทที่ 2.docx):   {"✅ ผ่าน" if docx_result else "❌ ไม่ผ่าน"}')
    print()
    
    if pdf_result and docx_result:
        print('🎉 ทุกไฟล์ทำงานได้สมบูรณ์!')
    else:
        print('⚠️  บางไฟล์มีปัญหา กรุณาตรวจสอบ error ด้านบน')
    
    print()


if __name__ == '__main__':
    main()
