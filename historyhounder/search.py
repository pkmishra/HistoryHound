from langchain_chroma import Chroma as LCChroma
from langchain_huggingface import HuggingFaceEmbeddings
from historyhounder.embedder import get_embedder
from historyhounder.vector_store import ChromaVectorStore
from historyhounder.llm.ollama_qa import answer_question_ollama

def semantic_search(query, top_k=5, embedder_backend='sentence-transformers', persist_directory='chroma_db'):
    embedder = get_embedder(embedder_backend)
    store = ChromaVectorStore(persist_directory=persist_directory)
    query_emb = embedder.embed([query])[0]
    results = store.query(query_emb, top_k=top_k)
    output = []
    for i in range(len(results['documents'][0])):
        doc = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        dist = results['distances'][0][i]
        output.append({**meta, 'document': doc, 'distance': dist})
    return output

def llm_qa_search(query, top_k=5, llm='ollama', llm_model='llama3.2:latest', embedder_backend='sentence-transformers', persist_directory='chroma_db'):
    # Use the same approach as semantic_search to ensure consistency
    embedder = get_embedder(embedder_backend)
    store = ChromaVectorStore(persist_directory=persist_directory)
    query_emb = embedder.embed([query])[0]
    results = store.query(query_emb, top_k=top_k)
    
    # Convert results to format expected by answer_question_ollama
    documents = results['documents'][0] if results['documents'] else []
    metadatas = results['metadatas'][0] if results['metadatas'] else []
    
    # Create a simple retriever-like object
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.documents import Document
    
    class SimpleRetriever(BaseRetriever):
        def __init__(self, docs, metas):
            super().__init__()
            self._docs = docs
            self._metas = metas
        
        def get_relevant_documents(self, query):
            return [Document(page_content=doc, metadata=meta) for doc, meta in zip(self._docs, self._metas)]
        
        async def aget_relevant_documents(self, query):
            return self.get_relevant_documents(query)
    
    retriever = SimpleRetriever(documents, metadatas)
    result = answer_question_ollama(query, retriever, model=llm_model)
    
    # Create detailed source information with URLs and titles
    sources = []
    for doc, meta in zip(documents, metadatas):
        source_info = {
            'content': doc,
            'url': meta.get('url', ''),
            'title': meta.get('title', ''),
            'visit_time': meta.get('visit_time', ''),
            'domain': meta.get('domain', '')
        }
        sources.append(source_info)
    
    return {
        'answer': result['answer'],
        'sources': sources
    } 