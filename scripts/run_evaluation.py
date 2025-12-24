#!/usr/bin/env python3
"""RAGAS Evaluation Script

Run RAGAS evaluation on RAG responses and send scores to Langfuse.

Usage:
    # Evaluate from JSON file
    python scripts/run_evaluation.py --input test_data.json --output results.json
    
    # Evaluate with Langfuse
    python scripts/run_evaluation.py --input test_data.json --langfuse
    
    # Single evaluation
    python scripts/run_evaluation.py --question "What is X?" --answer "X is..." --contexts "ctx1" "ctx2"

Input JSON format:
    [
        {
            "question": "User question",
            "answer": "Generated answer",
            "contexts": ["context 1", "context 2"],
            "ground_truth": "Expected answer (optional)",
            "trace_id": "langfuse-trace-id (optional)"
        },
        ...
    ]
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.observability.evaluation import (
    RAGASEvaluator,
    EvaluationRunner,
    EvaluationResult
)


def main():
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation")
    
    # Input options
    parser.add_argument("--input", "-i", help="Input JSON file with test data")
    parser.add_argument("--question", "-q", help="Single question to evaluate")
    parser.add_argument("--answer", "-a", help="Answer to evaluate")
    parser.add_argument("--contexts", "-c", nargs="+", help="Contexts (space-separated)")
    parser.add_argument("--ground-truth", "-g", help="Ground truth answer")
    
    # Output options
    parser.add_argument("--output", "-o", help="Output JSON file for results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # Langfuse options
    parser.add_argument("--langfuse", action="store_true", help="Send scores to Langfuse")
    parser.add_argument("--trace-id", help="Langfuse trace ID (for single evaluation)")
    
    # Model options
    parser.add_argument("--llm-model", default="gpt-4", help="LLM model for evaluation")
    parser.add_argument("--embedding-model", default="text-embedding-3-small", help="Embedding model")
    
    args = parser.parse_args()
    
    # Initialize evaluator
    evaluator = RAGASEvaluator(
        llm_model=args.llm_model,
        embedding_model=args.embedding_model
    )
    
    # Initialize Langfuse if requested
    langfuse = None
    if args.langfuse:
        try:
            from langfuse import Langfuse
            langfuse = Langfuse()
            print("✅ Langfuse connected")
        except ImportError:
            print("❌ Langfuse not installed. Run: pip install langfuse")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Langfuse connection failed: {e}")
            sys.exit(1)
    
    # Single evaluation mode
    if args.question and args.answer and args.contexts:
        print(f"\n📊 Evaluating single response...")
        print(f"Question: {args.question[:100]}...")
        print(f"Answer: {args.answer[:100]}...")
        print(f"Contexts: {len(args.contexts)} provided")
        
        result = evaluator.evaluate(
            question=args.question,
            answer=args.answer,
            contexts=args.contexts,
            ground_truth=args.ground_truth
        )
        
        print_result(result)
        
        # Send to Langfuse
        if langfuse and args.trace_id:
            evaluator.send_scores_to_langfuse(args.trace_id, result, langfuse)
            print(f"\n✅ Scores sent to Langfuse (trace: {args.trace_id[:8]}...)")
        
        # Save output
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"\n💾 Results saved to {args.output}")
        
        return
    
    # Batch evaluation mode
    if args.input:
        print(f"\n📂 Loading test data from {args.input}...")
        
        with open(args.input) as f:
            test_data = json.load(f)
        
        print(f"📊 Evaluating {len(test_data)} samples...")
        
        runner = EvaluationRunner(
            evaluator=evaluator,
            langfuse=langfuse
        )
        
        summary = runner.run_evaluation(
            test_data=test_data,
            send_to_langfuse=args.langfuse
        )
        
        print_summary(summary)
        
        # Save output
        if args.output:
            # Remove results for smaller file
            output_summary = {k: v for k, v in summary.items() if k != "results"}
            if args.verbose:
                output_summary["results"] = summary["results"]
            
            with open(args.output, "w") as f:
                json.dump(output_summary, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Results saved to {args.output}")
        
        return
    
    # No valid input
    parser.print_help()
    sys.exit(1)


def print_result(result: EvaluationResult):
    """Print single evaluation result"""
    print("\n" + "=" * 50)
    print("📊 RAGAS Evaluation Results")
    print("=" * 50)
    
    metrics = [
        ("Faithfulness", result.faithfulness),
        ("Context Precision", result.context_precision),
        ("Context Recall", result.context_recall),
        ("Answer Relevancy", result.answer_relevancy),
        ("Correctness", result.correctness),
        ("Semantic Similarity", result.semantic_similarity),
        ("Helpfulness", result.helpfulness),
        ("Harmfulness", result.harmfulness),
    ]
    
    for name, value in metrics:
        if value is not None:
            bar = "█" * int(value * 20) + "░" * (20 - int(value * 20))
            emoji = "✅" if value >= 0.7 else "⚠️" if value >= 0.4 else "❌"
            print(f"  {emoji} {name:20s} {bar} {value:.3f}")
        else:
            print(f"  ⬜ {name:20s} {'░' * 20} N/A")
    
    print("-" * 50)
    print(f"  📈 Average Score: {result.average_score():.3f}")
    print(f"  ⏱️  Evaluation Time: {result.evaluation_time_ms:.0f}ms")
    
    if result.error:
        print(f"  ❌ Error: {result.error}")


def print_summary(summary: dict):
    """Print batch evaluation summary"""
    print("\n" + "=" * 60)
    print("📊 RAGAS Batch Evaluation Summary")
    print("=" * 60)
    
    print(f"\n📈 Total Samples: {summary['total_samples']}")
    print(f"⏱️  Total Time: {summary['evaluation_time_seconds']:.1f}s")
    
    print("\n📊 Metric Averages:")
    print("-" * 60)
    
    metrics = [
        "faithfulness",
        "context_precision",
        "context_recall", 
        "answer_relevancy",
        "correctness",
        "semantic_similarity",
        "helpfulness",
        "harmfulness"
    ]
    
    for metric in metrics:
        avg_key = f"{metric}_avg"
        if avg_key in summary:
            avg = summary[avg_key]
            min_val = summary.get(f"{metric}_min", 0)
            max_val = summary.get(f"{metric}_max", 0)
            count = summary.get(f"{metric}_count", 0)
            
            bar = "█" * int(avg * 20) + "░" * (20 - int(avg * 20))
            emoji = "✅" if avg >= 0.7 else "⚠️" if avg >= 0.4 else "❌"
            
            print(f"  {emoji} {metric:20s} {bar} {avg:.3f} (min={min_val:.2f}, max={max_val:.2f}, n={count})")


if __name__ == "__main__":
    main()
