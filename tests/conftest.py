import pytest
import os
import tempfile
import shutil
from historyhounder.embedder import clear_embedder_cache

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up test environment with offline mode for HuggingFace models when possible.
    This runs once per test session to minimize model downloads.
    """
    # Try to use offline mode for HuggingFace to avoid rate limiting
    original_offline = os.environ.get('HF_HUB_OFFLINE')
    
    # Check if sentence-transformers model exists locally
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    model_path = os.path.join(cache_dir, "models--sentence-transformers--all-MiniLM-L6-v2")
    
    if os.path.exists(model_path):
        # Model exists locally, enable offline mode for tests
        os.environ['HF_HUB_OFFLINE'] = '1'
        print(f"\n✅ Using offline mode for HuggingFace models (found in {model_path})")
    else:
        print(f"\n⚠️ HuggingFace model not found locally, may download during tests")
    
    yield
    
    # Restore original offline setting
    if original_offline is not None:
        os.environ['HF_HUB_OFFLINE'] = original_offline
    elif 'HF_HUB_OFFLINE' in os.environ:
        del os.environ['HF_HUB_OFFLINE']

@pytest.fixture(scope="function")
def clean_embedder_cache():
    """
    Fixture to clean embedder cache before each test function that specifically needs it.
    Most tests should NOT use this to benefit from caching.
    """
    clear_embedder_cache()
    yield
    # Cache is preserved after test to benefit subsequent tests

@pytest.fixture(scope="session")
def persistent_embedder_cache():
    """
    Fixture that preserves embedder cache across the entire test session.
    This ensures the model is downloaded only once per session.
    """
    # Don't clear cache - let it persist across tests
    yield
    # Clean up at the end of the session
    clear_embedder_cache()

@pytest.fixture(scope="function", autouse=True)
def temp_vector_store_dir():
    """
    Create a temporary directory for vector store tests.
    Each test gets its own directory to avoid interference.
    """
    temp_dir = tempfile.mkdtemp(prefix='test_vector_store_')
    yield temp_dir
    
    # Clean up
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass  # Ignore cleanup errors

# Mark tests that can run with cached embedders (most tests)
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may download models)"
    )
    config.addinivalue_line(
        "markers", "embedding: marks tests that use embedding models"
    )

def pytest_collection_modifyitems(config, items):
    """Automatically mark tests that use embeddings."""
    for item in items:
        # Check if test uses embedder
        if any(marker in item.nodeid.lower() for marker in ['embedding', 'embedder', 'qa', 'search']):
            item.add_marker(pytest.mark.embedding) 