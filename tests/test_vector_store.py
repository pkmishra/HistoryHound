import pytest
from historyhounder.vector_store import ChromaVectorStore

class DummyCollection:
    def __init__(self):
        self.added = []
    def add(self, documents, embeddings, metadatas, ids):
        if not documents or not embeddings:
            raise ValueError("Expected Embeddings to be non-empty list or numpy array, got [] in add.")
        self.added.append((documents, embeddings, metadatas, ids))
    def query(self, query_embeddings, n_results, include):
        return {'documents': [['doc1']], 'metadatas': [[{'url': 'u'}]], 'distances': [[0.1]]}

class DummyClient:
    def __init__(self, *a, **kw):
        self.collection = DummyCollection()
    def get_or_create_collection(self, name):
        return self.collection


def test_add_and_query(monkeypatch):
    monkeypatch.setattr('chromadb.PersistentClient', DummyClient)
    store = ChromaVectorStore(persist_directory=':memory:')
    docs = ['doc1', 'doc2']
    embs = [[0.1, 0.2], [0.3, 0.4]]
    metas = [{'url': 'a'}, {'url': 'b'}]
    store.add(docs, embs, metas)
    assert store.collection.added
    result = store.query([0.1, 0.2], top_k=1)
    assert 'documents' in result
    assert 'metadatas' in result
    assert 'distances' in result 


def test_query_no_results(monkeypatch):
    class EmptyCollection:
        def add(self, documents, embeddings, metadatas, ids):
            pass
        def query(self, query_embeddings, n_results, include):
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
    class DummyClient:
        def __init__(self, *a, **kw):
            self.collection = EmptyCollection()
        def get_or_create_collection(self, name):
            return self.collection
    monkeypatch.setattr('chromadb.PersistentClient', DummyClient)
    store = ChromaVectorStore(persist_directory=':memory:')
    result = store.query([0.1, 0.2], top_k=1)
    assert result['documents'] == [[]]
    assert result['metadatas'] == [[]]
    assert result['distances'] == [[]]


def test_add_empty(monkeypatch):
    monkeypatch.setattr('chromadb.PersistentClient', DummyClient)
    store = ChromaVectorStore(persist_directory=':memory:')
    with pytest.raises(ValueError):
        store.add([], [], []) 