#!/usr/bin/env python3
"""
Post Mock Evaluation Scores to Langfuse
สคริปต์สำหรับ POST คะแนน mockup ไปยัง Langfuse เพื่อทดสอบระบบ evaluation
โดยไม่ต้องรัน evaluation จริง
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langfuse import Langfuse
from src.observability.langfuse_config import get_langfuse_config, print_connection_info
import random
from datetime import datetime
from typing import Dict, List


def create_mock_trace(langfuse: Langfuse, trace_name: str) -> str:
    """สร้าง mock trace พร้อม generation และส่งกลับ trace_id"""
    
    # สร้าง generation (observation) - Langfuse จะสร้าง trace_id อัตโนมัติ
    generation = langfuse.start_observation(
        as_type="generation",
        name=trace_name,
        input={
            "query": "What is the capital of Thailand?",
            "context": ["Bangkok is the capital and most populous city of Thailand."]
        },
        metadata={
            "test": True,
            "trace_type": "mock",
            "created_at": datetime.now().isoformat()
        }
    )
    
    # ดึง trace_id จาก generation
    trace_id = generation.trace_id
    
    print(f"📝 Created mock trace: {trace_name}")
    print(f"   Trace ID: {trace_id}")
    
    # Update generation ด้วย output ก่อนจะ end
    generation.update(
        output={
            "answer": "Bangkok is the capital of Thailand.",
            "confidence": round(random.uniform(0.8, 1.0), 3)
        },
        metadata={
            "model": "mock-model",
            "tokens_used": random.randint(50, 200)
        }
    )
    
    # End generation
    generation.end()
    
    return trace_id


def post_mock_rag_scores(langfuse: Langfuse, trace_id: str, trace_name: str):
    """POST คะแนน RAG evaluation แบบ mockup
    
    คะแนนที่ POST:
    - faithfulness (0-1): ความถูกต้องตาม context
    - answer_relevancy (0-1): ความเกี่ยวข้องของคำตอบ
    - context_precision (0-1): ความแม่นยำของ context ที่ retrieve
    - context_recall (0-1): ความครบถ้วนของ context
    """
    
    scores = {
        "faithfulness": round(random.uniform(0.7, 1.0), 3),
        "answer_relevancy": round(random.uniform(0.6, 0.95), 3),
        "context_precision": round(random.uniform(0.65, 0.9), 3),
        "context_recall": round(random.uniform(0.7, 0.95), 3),
        "correctness": round(random.uniform(0.7, 0.95), 3),
        "helpfulness": round(random.uniform(0.7, 0.95), 3),
        "harmfulness": round(random.uniform(0.7, 0.95), 3),
        "semantic_similarity": round(random.uniform(0.7, 0.95), 3)
        
    }
    
    print(f"\n📊 Posting mock scores for trace: {trace_name}")
    print(f"   Trace ID: {trace_id}")
    
    for metric_name, score_value in scores.items():
        langfuse.create_score(
            trace_id=trace_id,
            name=metric_name,
            value=score_value,
            comment=f"Mock score generated for testing (not real evaluation)"
        )
        print(f"   ✅ {metric_name}: {score_value:.3f}")


def post_mock_llm_scores(langfuse: Langfuse, trace_id: str, trace_name: str):
    """POST คะแนน LLM quality แบบ mockup
    
    คะแนนที่ POST:
    - hallucination_score (0-1): ระดับการ hallucinate (ต่ำ = ดี)
    - toxicity_score (0-1): ระดับความเป็นพิษ (ต่ำ = ดี)
    - coherence (0-1): ความสอดคล้องของคำตอบ (สูง = ดี)
    - fluency (0-1): ความลื่นไหลของภาษา (สูง = ดี)
    """
    
    scores = {
        "hallucination_score": round(random.uniform(0.0, 0.3), 3),  # ต่ำ = ดี
        "toxicity_score": round(random.uniform(0.0, 0.2), 3),       # ต่ำ = ดี
        "coherence": round(random.uniform(0.75, 1.0), 3),           # สูง = ดี
        "fluency": round(random.uniform(0.8, 1.0), 3),              # สูง = ดี
    }
    
    print(f"\n📊 Posting mock LLM quality scores for trace: {trace_name}")
    print(f"   Trace ID: {trace_id}")
    
    for metric_name, score_value in scores.items():
        langfuse.create_score(
            trace_id=trace_id,
            name=metric_name,
            value=score_value,
            comment=f"Mock score generated for testing (not real evaluation)"
        )
        print(f"   ✅ {metric_name}: {score_value:.3f}")


def post_mock_user_feedback(langfuse: Langfuse, trace_id: str, trace_name: str):
    """POST คะแนน user feedback แบบ mockup
    
    คะแนนที่ POST:
    - user_rating (1-5): คะแนนจากผู้ใช้
    - thumbs_up (0/1): ถูกใจหรือไม่
    """
    
    user_rating = random.randint(3, 5)
    thumbs_up = 1 if user_rating >= 4 else 0
    
    print(f"\n👤 Posting mock user feedback for trace: {trace_name}")
    print(f"   Trace ID: {trace_id}")
    
    langfuse.create_score(
        trace_id=trace_id,
        name="user_rating",
        value=user_rating,
        comment=f"Mock user rating for testing"
    )
    print(f"   ⭐ user_rating: {user_rating}/5")
    
    langfuse.create_score(
        trace_id=trace_id,
        name="thumbs_up",
        value=thumbs_up,
        comment=f"Mock thumbs up for testing"
    )
    print(f"   👍 thumbs_up: {'Yes' if thumbs_up else 'No'}")


def post_mock_custom_scores(langfuse: Langfuse, trace_id: str, trace_name: str, 
                            custom_metrics: Dict[str, float]):
    """POST คะแนน custom metrics แบบ mockup
    
    Args:
        custom_metrics: Dict ของ metric_name: score_value
    """
    
    print(f"\n🔧 Posting mock custom scores for trace: {trace_name}")
    print(f"   Trace ID: {trace_id}")
    
    for metric_name, score_value in custom_metrics.items():
        langfuse.create_score(
            trace_id=trace_id,
            name=metric_name,
            value=score_value,
            comment=f"Mock custom score for testing"
        )
        print(f"   ✅ {metric_name}: {score_value}")


def main():
    """Main function"""
    print("=" * 70)
    print("📝 POST MOCK EVALUATION SCORES TO LANGFUSE")
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
    
    # Create mock traces and post scores
    print("\n" + "=" * 70)
    print("🚀 เริ่มสร้าง mock traces และ POST คะแนน (10 รอบ)")
    print("=" * 70)
    
    # สุ่มสร้าง mock traces 10 รอบ (ทุก trace ได้คะแนนครบทุก metric)
    for i in range(1, 11):
        print(f"\n{'='*70}")
        print(f"🔄 รอบที่ {i}/10")
        print(f"{'='*70}")
        
        # ทุก trace ใช้ชื่อเดียวกัน: "evaluation:ragas"
        trace_name = "evaluation:ragas"
        
        # สร้าง trace
        trace_id = create_mock_trace(langfuse, trace_name)
        
        # POST คะแนนครบทุก metric
        # 1. RAG Metrics
        post_mock_rag_scores(langfuse, trace_id, trace_name)
        
        # 2. LLM Quality Metrics
        post_mock_llm_scores(langfuse, trace_id, trace_name)
        
        # 3. User Feedback
        post_mock_user_feedback(langfuse, trace_id, trace_name)
        
        # 4. Custom Performance Metrics
        post_mock_custom_scores(
            langfuse, 
            trace_id, 
            trace_name,
            {
                "response_time_ms": round(random.uniform(200, 800), 2),
                "retrieval_count": random.randint(3, 10),
                "chunk_relevance_avg": round(random.uniform(0.6, 0.95), 3),
                "reranker_score": round(random.uniform(0.7, 0.98), 3)
            }
        )
    
    # Flush to ensure all data is sent
    print("\n📤 กำลังส่งข้อมูลไปยัง Langfuse...")
    langfuse.flush()
    
    print("\n" + "=" * 70)
    print("✅ POST MOCK SCORES เสร็จสิ้น")
    print("=" * 70)
    print(f"\n🌐 ดูผลลัพธ์ได้ที่: {config.host}")
    print("📊 ไปที่ Dashboard → Traces เพื่อดู mock traces ที่สร้าง")
    print("📈 ไปที่ Scores/Evaluations เพื่อดูคะแนนที่ POST")
    print("\n💡 TIP: คุณสามารถ customize metrics ได้ด้วยการแก้ไข")
    print("   ฟังก์ชัน post_mock_custom_scores() ในสคริปต์นี้")


if __name__ == "__main__":
    main()
