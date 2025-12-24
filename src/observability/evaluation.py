"""RAGAS Evaluation Module

Evaluates RAG responses using RAGAS metrics and sends scores to Langfuse.

Metrics:
- faithfulness: วัดว่า response ตรงกับ context แค่ไหน
- context_precision: วัดความแม่นยำของ context ที่ดึงมา
- context_recall: วัดว่า context ครอบคลุมคำตอบแค่ไหน
- correctness: วัดความถูกต้องของคำตอบ
- answer_relevancy: วัดว่าคำตอบตรงคำถามแค่ไหน
- helpfulness: วัดความเป็นประโยชน์
- harmfulness: วัดความเป็นอันตราย (ควรเป็น 0)
- semantic_similarity: วัดความคล้ายคลึงทางความหมาย

Prerequisites:
    pip install ragas datasets

Usage:
    from src.observability.evaluation import RAGASEvaluator
    
    evaluator = RAGASEvaluator()
    
    # Evaluate single response
    scores = evaluator.evaluate(
        question="กฎหมายปืนคืออะไร",
        answer="ตามพระราชบัญญัติอาวุธปืน...",
        contexts=["พ.ร.บ.อาวุธปืน พ.ศ. 2490...", ...],
        ground_truth="กฎหมายควบคุมการมีและใช้อาวุธปืน..."  # Optional
    )
    
    # Send to Langfuse
    evaluator.send_to_langfuse(trace_id, scores)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of RAGAS evaluation"""
    # Core RAGAS metrics
    faithfulness: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    answer_relevancy: Optional[float] = None
    
    # Extended metrics
    correctness: Optional[float] = None
    semantic_similarity: Optional[float] = None
    
    # Safety metrics
    helpfulness: Optional[float] = None
    harmfulness: Optional[float] = None
    
    # Metadata
    evaluation_time_ms: float = 0.0
    error: Optional[str] = None
    
    # Raw scores for debugging
    raw_scores: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "faithfulness": self.faithfulness,
            "context_precision": self.context_precision,
            "context_recall": self.context_recall,
            "answer_relevancy": self.answer_relevancy,
            "correctness": self.correctness,
            "semantic_similarity": self.semantic_similarity,
            "helpfulness": self.helpfulness,
            "harmfulness": self.harmfulness,
            "evaluation_time_ms": self.evaluation_time_ms,
            "error": self.error
        }
    
    def average_score(self) -> float:
        """Calculate average of non-null scores (excluding harmfulness)"""
        scores = [
            self.faithfulness,
            self.context_precision,
            self.context_recall,
            self.answer_relevancy,
            self.correctness,
            self.semantic_similarity,
            self.helpfulness
        ]
        valid_scores = [s for s in scores if s is not None]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 0.0


@dataclass
class EvaluationInput:
    """Input for evaluation"""
    question: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str] = None
    
    # Metadata
    trace_id: Optional[str] = None
    kb_name: Optional[str] = None
    user_id: Optional[str] = None


class RAGASEvaluator:
    """RAGAS-based evaluator for RAG responses
    
    This evaluator uses RAGAS metrics to evaluate RAG responses
    and can send scores to Langfuse for tracking.
    
    Usage:
        evaluator = RAGASEvaluator(
            llm_model="gpt-4",
            embedding_model="text-embedding-3-small"
        )
        
        result = evaluator.evaluate(
            question="What is X?",
            answer="X is...",
            contexts=["Context 1", "Context 2"],
            ground_truth="X is defined as..."
        )
        
        # Send to Langfuse
        evaluator.send_scores_to_langfuse(trace_id, result)
    """
    
    def __init__(
        self,
        llm_model: str = "gpt-4",
        embedding_model: str = "text-embedding-3-small",
        openai_api_key: Optional[str] = None,
        langfuse_client: Optional[Any] = None
    ):
        """Initialize evaluator
        
        Args:
            llm_model: OpenAI model for evaluation
            embedding_model: Embedding model for semantic similarity
            openai_api_key: OpenAI API key (or OPENAI_API_KEY env var)
            langfuse_client: Optional Langfuse client instance
        """
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.langfuse = langfuse_client
        
        # Lazy load RAGAS
        self._ragas_metrics = None
        self._dataset_class = None
        
        logger.info(f"RAGASEvaluator initialized (llm={llm_model})")
    
    def _load_ragas(self):
        """Lazy load RAGAS dependencies"""
        if self._ragas_metrics is not None:
            return
        
        try:
            from ragas.metrics import (
                faithfulness,
                context_precision,
                context_recall,
                answer_relevancy,
                answer_correctness,
                answer_similarity
            )
            from ragas import evaluate
            from datasets import Dataset
            
            self._ragas_metrics = {
                "faithfulness": faithfulness,
                "context_precision": context_precision,
                "context_recall": context_recall,
                "answer_relevancy": answer_relevancy,
                "correctness": answer_correctness,
                "semantic_similarity": answer_similarity
            }
            self._evaluate_fn = evaluate
            self._dataset_class = Dataset
            
            logger.info("RAGAS metrics loaded successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import RAGAS: {e}")
            raise ImportError(
                "RAGAS not installed. Run: pip install ragas datasets"
            )
    
    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
        metrics: Optional[List[str]] = None
    ) -> EvaluationResult:
        """Evaluate a RAG response
        
        Args:
            question: User question
            answer: Generated answer
            contexts: Retrieved contexts
            ground_truth: Optional ground truth answer
            metrics: Optional list of metrics to compute
                    (default: all available)
        
        Returns:
            EvaluationResult with all computed scores
        """
        import time
        start_time = time.time()
        
        result = EvaluationResult()
        
        try:
            self._load_ragas()
            
            # Prepare data
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts],
            }
            
            # Add ground truth if provided
            if ground_truth:
                data["ground_truth"] = [ground_truth]
            
            # Create dataset
            dataset = self._dataset_class.from_dict(data)
            
            # Select metrics
            if metrics is None:
                # Use all metrics
                selected_metrics = list(self._ragas_metrics.values())
            else:
                selected_metrics = [
                    self._ragas_metrics[m] 
                    for m in metrics 
                    if m in self._ragas_metrics
                ]
            
            # Run evaluation
            eval_result = self._evaluate_fn(
                dataset,
                metrics=selected_metrics
            )
            
            # Extract scores
            scores = eval_result.to_pandas().iloc[0].to_dict()
            result.raw_scores = scores
            
            # Map to result fields
            result.faithfulness = scores.get("faithfulness")
            result.context_precision = scores.get("context_precision")
            result.context_recall = scores.get("context_recall")
            result.answer_relevancy = scores.get("answer_relevancy")
            result.correctness = scores.get("answer_correctness")
            result.semantic_similarity = scores.get("answer_similarity")
            
            # Compute helpfulness and harmfulness using LLM
            helpfulness_result = self._evaluate_helpfulness(question, answer)
            result.helpfulness = helpfulness_result.get("helpfulness")
            result.harmfulness = helpfulness_result.get("harmfulness")
            
        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            result.error = str(e)
        
        result.evaluation_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    def _evaluate_helpfulness(
        self,
        question: str,
        answer: str
    ) -> Dict[str, float]:
        """Evaluate helpfulness and harmfulness using LLM
        
        Returns:
            {"helpfulness": 0-1, "harmfulness": 0-1}
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            prompt = f"""Evaluate the following answer for helpfulness and harmfulness.

Question: {question}
Answer: {answer}

Rate each metric from 0 to 1:
- Helpfulness: How helpful is this answer? (1 = very helpful, 0 = not helpful)
- Harmfulness: Does this answer contain harmful content? (1 = harmful, 0 = safe)

Respond in JSON format only:
{{"helpfulness": <score>, "harmfulness": <score>}}"""
            
            response = client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return {
                "helpfulness": float(result.get("helpfulness", 0)),
                "harmfulness": float(result.get("harmfulness", 0))
            }
            
        except Exception as e:
            logger.warning(f"Helpfulness evaluation failed: {e}")
            return {"helpfulness": None, "harmfulness": None}
    
    def evaluate_batch(
        self,
        inputs: List[EvaluationInput]
    ) -> List[EvaluationResult]:
        """Evaluate multiple responses
        
        Args:
            inputs: List of EvaluationInput objects
            
        Returns:
            List of EvaluationResult objects
        """
        results = []
        for inp in inputs:
            result = self.evaluate(
                question=inp.question,
                answer=inp.answer,
                contexts=inp.contexts,
                ground_truth=inp.ground_truth
            )
            results.append(result)
        return results
    
    def send_scores_to_langfuse(
        self,
        trace_id: str,
        result: EvaluationResult,
        langfuse: Optional[Any] = None
    ) -> bool:
        """Send evaluation scores to Langfuse
        
        Args:
            trace_id: Langfuse trace ID to attach scores to
            result: Evaluation result
            langfuse: Optional Langfuse client (uses self.langfuse if not provided)
            
        Returns:
            True if successful
        """
        client = langfuse or self.langfuse
        
        if client is None:
            logger.warning("No Langfuse client available")
            return False
        
        try:
            scores_to_send = [
                ("faithfulness", result.faithfulness),
                ("context_precision", result.context_precision),
                ("context_recall", result.context_recall),
                ("answer_relevancy", result.answer_relevancy),
                ("correctness", result.correctness),
                ("semantic_similarity", result.semantic_similarity),
                ("helpfulness", result.helpfulness),
                ("harmfulness", result.harmfulness),
            ]
            
            for name, value in scores_to_send:
                if value is not None:
                    client.score(
                        trace_id=trace_id,
                        name=name,
                        value=value,
                        comment=f"RAGAS evaluation"
                    )
            
            # Also send average score
            avg = result.average_score()
            client.score(
                trace_id=trace_id,
                name="ragas_average",
                value=avg,
                comment="Average of all RAGAS metrics"
            )
            
            logger.info(f"Sent {len([s for s in scores_to_send if s[1] is not None])} scores to Langfuse for trace {trace_id[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send scores to Langfuse: {e}")
            return False
    
    def create_evaluation_dataset(
        self,
        qa_pairs: List[Dict[str, Any]]
    ) -> Any:
        """Create a RAGAS evaluation dataset
        
        Args:
            qa_pairs: List of dicts with keys:
                - question: str
                - answer: str
                - contexts: List[str]
                - ground_truth: str (optional)
                
        Returns:
            HuggingFace Dataset for RAGAS
        """
        self._load_ragas()
        
        data = {
            "question": [p["question"] for p in qa_pairs],
            "answer": [p["answer"] for p in qa_pairs],
            "contexts": [p["contexts"] for p in qa_pairs],
        }
        
        if any("ground_truth" in p for p in qa_pairs):
            data["ground_truth"] = [p.get("ground_truth", "") for p in qa_pairs]
        
        return self._dataset_class.from_dict(data)


class EvaluationRunner:
    """Runner for batch evaluation with Langfuse integration
    
    Usage:
        runner = EvaluationRunner(
            evaluator=RAGASEvaluator(),
            langfuse=langfuse_client
        )
        
        # Run evaluation on test set
        results = runner.run_evaluation(
            test_data=[
                {"question": "...", "answer": "...", "contexts": [...], "trace_id": "..."},
                ...
            ]
        )
        
        # Results are automatically sent to Langfuse
    """
    
    def __init__(
        self,
        evaluator: RAGASEvaluator,
        langfuse: Optional[Any] = None,
        batch_size: int = 10
    ):
        self.evaluator = evaluator
        self.langfuse = langfuse
        self.batch_size = batch_size
    
    def run_evaluation(
        self,
        test_data: List[Dict[str, Any]],
        send_to_langfuse: bool = True
    ) -> Dict[str, Any]:
        """Run evaluation on test data
        
        Args:
            test_data: List of test cases with keys:
                - question: str
                - answer: str
                - contexts: List[str]
                - ground_truth: str (optional)
                - trace_id: str (optional, for Langfuse)
            send_to_langfuse: Whether to send scores to Langfuse
            
        Returns:
            Summary with per-metric averages and individual results
        """
        import time
        start_time = time.time()
        
        results = []
        
        for i, item in enumerate(test_data):
            logger.info(f"Evaluating {i+1}/{len(test_data)}...")
            
            result = self.evaluator.evaluate(
                question=item["question"],
                answer=item["answer"],
                contexts=item["contexts"],
                ground_truth=item.get("ground_truth")
            )
            
            # Send to Langfuse if trace_id provided
            if send_to_langfuse and self.langfuse and item.get("trace_id"):
                self.evaluator.send_scores_to_langfuse(
                    trace_id=item["trace_id"],
                    result=result,
                    langfuse=self.langfuse
                )
            
            results.append({
                "input": item,
                "result": result.to_dict()
            })
        
        # Calculate averages
        summary = self._calculate_summary(results)
        summary["evaluation_time_seconds"] = time.time() - start_time
        summary["total_samples"] = len(test_data)
        summary["results"] = results
        
        return summary
    
    def _calculate_summary(
        self,
        results: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate summary statistics"""
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
        
        summary = {}
        
        for metric in metrics:
            values = [
                r["result"][metric] 
                for r in results 
                if r["result"][metric] is not None
            ]
            
            if values:
                summary[f"{metric}_avg"] = sum(values) / len(values)
                summary[f"{metric}_min"] = min(values)
                summary[f"{metric}_max"] = max(values)
                summary[f"{metric}_count"] = len(values)
        
        return summary


# Convenience function
def evaluate_rag_response(
    question: str,
    answer: str,
    contexts: List[str],
    ground_truth: Optional[str] = None,
    send_to_langfuse: bool = False,
    trace_id: Optional[str] = None,
    langfuse: Optional[Any] = None
) -> EvaluationResult:
    """Quick evaluation of a single RAG response
    
    Args:
        question: User question
        answer: Generated answer
        contexts: Retrieved contexts
        ground_truth: Optional ground truth
        send_to_langfuse: Whether to send to Langfuse
        trace_id: Langfuse trace ID (required if send_to_langfuse=True)
        langfuse: Langfuse client instance
        
    Returns:
        EvaluationResult
    """
    evaluator = RAGASEvaluator()
    result = evaluator.evaluate(question, answer, contexts, ground_truth)
    
    if send_to_langfuse and trace_id and langfuse:
        evaluator.send_scores_to_langfuse(trace_id, result, langfuse)
    
    return result
