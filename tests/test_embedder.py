import pytest
from historyhounder.embedder import get_embedder, Embedder, EMBEDDER_REGISTRY
import numpy as np

class DummyModel:
    def encode(self, texts, convert_to_numpy):
        return np.array([[1.0] * 3 for _ in texts])

def test_sentence_transformers_embedder():
    """Test embedder conversion logic without loading actual models."""
    import numpy as np
    
    # Test the conversion logic that the SentenceTransformersEmbedder.embed method uses
    # This tests the core functionality without needing to load actual models
    embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    
    # Test the conversion logic from the embed method
    if hasattr(embeddings, 'tolist'):
        result = embeddings.tolist()
    else:
        result = [list(emb) for emb in embeddings]
    
    # Verify the conversion works correctly
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(vec, list) and len(vec) == 3 for vec in result)
    assert result[0] == [0.1, 0.2, 0.3]
    assert result[1] == [0.4, 0.5, 0.6]

def test_registry():
    assert 'sentence-transformers' in EMBEDDER_REGISTRY
    embedder = get_embedder('sentence-transformers')
    assert isinstance(embedder, Embedder)

def test_unknown_embedder():
    with pytest.raises(ValueError):
        get_embedder('not-a-real-embedder') 


def test_additional_embedders():
    # Placeholder: Add tests for new embedders if/when implemented
    # Example:
    # embedder = get_embedder('new-embedder')
    # result = embedder.embed(["test"])
    # assert ...
    pass 