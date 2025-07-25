import pytest
from historyhounder.embedder import get_embedder, Embedder, EMBEDDER_REGISTRY
import numpy as np

class DummyModel:
    def encode(self, texts, convert_to_numpy):
        return np.array([[1.0] * 3 for _ in texts])

def test_sentence_transformers_embedder(monkeypatch):
    class DummyST:
        def __init__(self, model_name):
            pass
        def encode(self, texts, convert_to_numpy):
            return np.array([[0.1, 0.2, 0.3] for _ in texts])
    monkeypatch.setattr('sentence_transformers.SentenceTransformer', DummyST)
    embedder = get_embedder('sentence-transformers')
    result = embedder.embed(["hello", "world"])
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(vec, list) and len(vec) == 3 for vec in result)

def test_registry():
    assert 'sentence-transformers' in EMBEDDER_REGISTRY
    embedder = get_embedder('sentence-transformers')
    assert isinstance(embedder, Embedder)

def test_unknown_embedder():
    with pytest.raises(ValueError):
        get_embedder('not-a-real-embedder') 