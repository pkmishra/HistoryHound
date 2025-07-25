from abc import ABC, abstractmethod
from typing import List

class Embedder(ABC):
    """
    Abstract base class for embedders. Implement embed(texts) to return list of vectors.
    """
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        pass

# Registry for embedders
EMBEDDER_REGISTRY = {}

def register_embedder(name):
    def decorator(cls):
        EMBEDDER_REGISTRY[name] = cls
        return cls
    return decorator

# Default: SentenceTransformersEmbedder
@register_embedder('sentence-transformers')
class SentenceTransformersEmbedder(Embedder):
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()

def get_embedder(name='sentence-transformers', **kwargs):
    if name not in EMBEDDER_REGISTRY:
        raise ValueError(f"Unknown embedder: {name}")
    return EMBEDDER_REGISTRY[name](**kwargs) 