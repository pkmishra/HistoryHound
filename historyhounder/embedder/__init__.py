from abc import ABC, abstractmethod
from typing import List
import os

class Embedder(ABC):
    """
    Abstract base class for embedders. Implement embed(texts) to return list of vectors.
    """
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        pass

# Registry for embedders
EMBEDDER_REGISTRY = {}

# Cache for embedder instances to avoid multiple model downloads
_EMBEDDER_CACHE = {}

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
        
        # Cache the model to avoid repeated downloads
        if not hasattr(self.__class__, '_model_cache'):
            self.__class__._model_cache = {}
        
        if model_name not in self.__class__._model_cache:
            # Set offline mode if model exists locally (for both test and production)
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            is_testing = os.environ.get('PYTEST_CURRENT_TEST') is not None
            model_path = os.path.join(cache_dir, f"models--sentence-transformers--{model_name.replace('/', '--')}")
            
            # Try offline mode first if model exists locally (for both test and production)
            if os.path.exists(model_path):
                # Model exists locally, try offline mode first
                original_offline = os.environ.get('HF_HUB_OFFLINE')
                os.environ['HF_HUB_OFFLINE'] = '1'
                try:
                    self.__class__._model_cache[model_name] = SentenceTransformer(model_name)
                    # Success with offline mode - model loaded from cache
                except Exception:
                    # Offline loading failed, fallback to online mode
                    if 'HF_HUB_OFFLINE' in os.environ:
                        del os.environ['HF_HUB_OFFLINE']
                    self.__class__._model_cache[model_name] = SentenceTransformer(model_name)
                finally:
                    # Restore original offline setting
                    if original_offline is not None:
                        os.environ['HF_HUB_OFFLINE'] = original_offline
                    elif 'HF_HUB_OFFLINE' in os.environ:
                        del os.environ['HF_HUB_OFFLINE']
            else:
                # Model not cached locally, download normally
                self.__class__._model_cache[model_name] = SentenceTransformer(model_name)
        
        self.model = self.__class__._model_cache[model_name]
        self.model_name = model_name
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()

def get_embedder(name='sentence-transformers', **kwargs):
    """
    Get an embedder instance with caching to avoid multiple model downloads.
    """
    if name not in EMBEDDER_REGISTRY:
        raise ValueError(f"Unknown embedder: {name}")
    
    # Create a cache key based on embedder name and kwargs
    cache_key = f"{name}_{hash(frozenset(kwargs.items()) if kwargs else frozenset())}"
    
    # Return cached instance if available
    if cache_key in _EMBEDDER_CACHE:
        return _EMBEDDER_CACHE[cache_key]
    
    # Create new instance and cache it
    embedder_instance = EMBEDDER_REGISTRY[name](**kwargs)
    _EMBEDDER_CACHE[cache_key] = embedder_instance
    
    return embedder_instance

def clear_embedder_cache():
    """
    Clear the embedder cache. Useful for testing or memory management.
    """
    global _EMBEDDER_CACHE
    _EMBEDDER_CACHE.clear()
    
    # Also clear model cache in SentenceTransformersEmbedder
    if hasattr(SentenceTransformersEmbedder, '_model_cache'):
        SentenceTransformersEmbedder._model_cache.clear() 