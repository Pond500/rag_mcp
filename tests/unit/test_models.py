#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from src.models import EmbeddingManager, Reranker, LLMClient


def test_embeddings():
    mgr = EmbeddingManager()
    dense = mgr.embed_dense(["hello", "world!"])
    sparse = mgr.embed_sparse(["hello world", "foo bar baz"])
    print('dense:', dense)
    print('sparse:', sparse)


def test_reranker():
    r = Reranker()
    scores = r.score("query", ["doc1", "longer document text"])
    print('rerank scores:', scores)


def test_llm():
    c = LLMClient()
    resp = c.generate("Say hi")
    print('llm resp:', resp)


if __name__ == '__main__':
    test_embeddings()
    test_reranker()
    test_llm()
