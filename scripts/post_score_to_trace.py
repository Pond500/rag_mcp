#!/usr/bin/env python3
"""
Post Evaluation Score to Existing Trace
สคริปต์สำหรับ POST คะแนนไปยัง trace ที่มีอยู่แล้วใน Langfuse
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langfuse import Langfuse
from src.observability.langfuse_config import get_langfuse_config, print_connection_info
import argparse


def post_score_to_trace(
    langfuse: Langfuse,
    trace_id: str,
    metric_name: str,
    score_value: float,
    comment: str = None
):
    """POST คะแนนไปยัง trace ที่ระบุ
    
    Args:
        langfuse: Langfuse client
        trace_id: ID ของ trace ที่ต้องการ POST คะแนน
        metric_name: ชื่อ metric (เช่น faithfulness, answer_relevancy)
        score_value: ค่าคะแนน (0-1 หรือ 1-5 ตาม metric)
        comment: คำอธิบายเพิ่มเติม (optional)
    """
    
    try:
        langfuse.create_score(
            trace_id=trace_id,
            name=metric_name,
            value=score_value,
            comment=comment or f"Manual score posted via script"
        )
        print(f"✅ Successfully posted score to trace")
        print(f"   Trace ID: {trace_id}")
        print(f"   Metric: {metric_name}")
        print(f"   Value: {score_value}")
        if comment:
            print(f"   Comment: {comment}")
        return True
    except Exception as e:
        print(f"❌ Failed to post score: {e}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="POST evaluation score to existing Langfuse trace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # POST faithfulness score
  python scripts/post_score_to_trace.py --trace-id abc123 --metric faithfulness --value 0.95
  
  # POST user rating with comment
  python scripts/post_score_to_trace.py --trace-id abc123 --metric user_rating --value 5 --comment "Excellent answer"
  
  # POST custom metric
  python scripts/post_score_to_trace.py --trace-id abc123 --metric response_time_ms --value 350.5
  
Common RAG Metrics:
  - faithfulness (0-1): ความถูกต้องตาม context
  - answer_relevancy (0-1): ความเกี่ยวข้องของคำตอบ
  - context_precision (0-1): ความแม่นยำของ context
  - context_recall (0-1): ความครบถ้วนของ context
  - user_rating (1-5): คะแนนจากผู้ใช้
  - thumbs_up (0/1): ถูกใจหรือไม่
        """
    )
    
    parser.add_argument(
        "--trace-id",
        required=True,
        help="Trace ID ที่ต้องการ POST คะแนน (หาได้จาก Langfuse Dashboard)"
    )
    
    parser.add_argument(
        "--metric",
        required=True,
        help="ชื่อ metric (เช่น faithfulness, answer_relevancy, user_rating)"
    )
    
    parser.add_argument(
        "--value",
        type=float,
        required=True,
        help="ค่าคะแนน (0-1 สำหรับ RAG metrics, 1-5 สำหรับ user_rating)"
    )
    
    parser.add_argument(
        "--comment",
        help="คำอธิบายเพิ่มเติม (optional)"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("📝 POST EVALUATION SCORE TO TRACE")
    print("=" * 70)
    
    # Load config
    print_connection_info()
    config = get_langfuse_config()
    
    # Validate config
    valid, message = config.validate()
    if not valid:
        print(f"\n{message}")
        print("❌ กรุณาตั้งค่า Langfuse environment variables ก่อน")
        sys.exit(1)
    
    if not config.enabled:
        print("\n⚠️  Langfuse ถูก disable (LANGFUSE_ENABLED=false)")
        print("💡 ตั้งค่า LANGFUSE_ENABLED=true เพื่อใช้งาน")
        sys.exit(1)
    
    # Initialize Langfuse
    print(f"\n🔗 กำลังเชื่อมต่อกับ Langfuse: {config.host}")
    langfuse = Langfuse(
        public_key=config.public_key,
        secret_key=config.secret_key,
        host=config.host,
        debug=config.debug
    )
    
    # Post score
    print("\n" + "=" * 70)
    print("🚀 กำลัง POST คะแนน...")
    print("=" * 70 + "\n")
    
    success = post_score_to_trace(
        langfuse=langfuse,
        trace_id=args.trace_id,
        metric_name=args.metric,
        score_value=args.value,
        comment=args.comment
    )
    
    # Flush to ensure data is sent
    print("\n📤 กำลังส่งข้อมูลไปยัง Langfuse...")
    langfuse.flush()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ POST SCORE เสร็จสิ้น")
        print("=" * 70)
        print(f"\n🌐 ดูผลลัพธ์ได้ที่: {config.host}/trace/{args.trace_id}")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("❌ POST SCORE ล้มเหลว")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
