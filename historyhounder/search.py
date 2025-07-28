from langchain_chroma import Chroma as LCChroma
from langchain_huggingface import HuggingFaceEmbeddings
from historyhounder.embedder import get_embedder
from historyhounder.vector_store import ChromaVectorStore
from historyhounder.llm.ollama_qa import answer_question_ollama, enhance_context_for_qa, format_context_for_prompt, parse_temporal_reference

def semantic_search(query, top_k=5, embedder_backend='sentence-transformers', persist_directory='chroma_db'):
    embedder = get_embedder(embedder_backend)
    store = ChromaVectorStore(persist_directory=persist_directory)
    query_emb = embedder.embed([query])[0]
    results = store.query(query_emb, top_k=top_k)
    output = []
    for i in range(len(results['documents'][0])):
        doc = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        output.append({
            'document': doc,
            'metadata': meta
        })
    store.close()
    return output


def llm_qa_search(query, top_k=5, embedder_backend='sentence-transformers', persist_directory='chroma_db'):
    """
    Enhanced Q&A search with temporal filtering support.
    """
    embedder = get_embedder(embedder_backend)
    store = ChromaVectorStore(persist_directory=persist_directory)
    
    # Parse temporal references from the query
    filtered_query, start_date, end_date = parse_temporal_reference(query)
    temporal_filter = (start_date, end_date) if start_date and end_date else None
    
    # Get all documents for enhanced context processing
    # Use a simple query to get all documents
    try:
        # Try to get all documents using a generic query
        query_emb = embedder.embed(["browsing history"])[0]
        all_results = store.query(query_emb, top_k=1000)  # Get all documents
    except Exception:
        # If that fails, try with a different approach
        try:
            query_emb = embedder.embed(["website"])[0]
            all_results = store.query(query_emb, top_k=1000)
        except Exception:
            # If all else fails, return empty result
            store.close()
            return {
                'answer': 'No browsing data found.',
                'sources': [],
                'enhanced_context': enhance_context_for_qa([], [], temporal_filter)
            }
    
    if not all_results['documents'][0]:
        store.close()
        return {
            'answer': 'No browsing data found.',
            'sources': [],
            'enhanced_context': enhance_context_for_qa([], [], temporal_filter)
        }
    
    documents = all_results['documents'][0]
    metadatas = all_results['metadatas'][0]
    
    # Create enhanced context with temporal filtering
    enhanced_context = enhance_context_for_qa(documents, metadatas, temporal_filter)
    
    # For semantic search, use the filtered query
    if filtered_query.strip():
        try:
            query_emb = embedder.embed([filtered_query])[0]
            results = store.query(query_emb, top_k=top_k)
            
            # Update documents and metadatas with filtered results
            if results['documents'][0]:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                # Re-create enhanced context with filtered results
                enhanced_context = enhance_context_for_qa(documents, metadatas, temporal_filter)
        except Exception:
            # If semantic search fails, continue with all documents
            pass
    
    # Create a simple retriever for the QA chain
    class SimpleRetriever:
        def __init__(self, documents, metadatas):
            self.documents = documents
            self.metadatas = metadatas
        
        def get_relevant_documents(self, query):
            from langchain_core.documents import Document
            docs = []
            for doc, meta in zip(self.documents, self.metadatas):
                # Create a document with metadata
                doc_obj = Document(
                    page_content=doc,
                    metadata=meta
                )
                docs.append(doc_obj)
            return docs
    
    retriever = SimpleRetriever(documents, metadatas)
    
    # Get answer using enhanced QA
    result = answer_question_ollama(query, retriever)
    
    # Add enhanced context to the result
    result['enhanced_context'] = enhanced_context
    
    store.close()
    return result 