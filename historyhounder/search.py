from langchain_chroma import Chroma as LCChroma
from langchain_huggingface import HuggingFaceEmbeddings
from historyhounder.embedder import get_embedder
from historyhounder.vector_store import ChromaVectorStore
from historyhounder.llm.ollama_qa import answer_question_ollama, enhance_context_for_qa, format_context_for_prompt, parse_temporal_reference

def semantic_search(query, top_k=5, embedder_backend='sentence-transformers', persist_directory='chroma_db'):
    embedder = get_embedder(embedder_backend)
    store = ChromaVectorStore(persist_directory=persist_directory)
    query_emb = embedder.embed([query])[0]
    
    # Get more results initially for re-ranking
    initial_k = min(top_k * 3, 50)  # Get 3x more results for relevance scoring
    results = store.query(query_emb, top_k=initial_k)
    
    # Extract and clean query keywords for relevance scoring
    import re
    query_lower = query.lower()
    # Remove punctuation and split into words
    clean_query = re.sub(r'[^\w\s]', '', query_lower)
    query_keywords = set(word for word in clean_query.split() if len(word) > 1)
    
    # Score and rank documents by relevance
    scored_results = []
    for i in range(len(results['documents'][0])):
        doc = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        
        # Calculate relevance score
        relevance_score = calculate_relevance_score(doc, meta, query_lower, query_keywords)
        
        scored_results.append({
            'document': doc,
            'metadata': meta,
            'relevance_score': relevance_score,
            'semantic_score': results['distances'][0][i] if 'distances' in results else 1.0
        })
    
    # Sort by relevance score (higher is better)
    scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    # Return top_k results
    output = []
    for result in scored_results[:top_k]:
        output.append({
            'document': result['document'],
            'metadata': result['metadata']
        })
    
    store.close()
    return output


def calculate_relevance_score(document, metadata, query_lower, query_keywords):
    """
    Calculate relevance score for a document based on keyword matching, 
    domain relevance, and visit frequency.
    """
    score = 0.0
    
    # 1. Keyword matching in content (weight: 3.0)
    doc_lower = document.lower()
    keyword_matches = sum(1 for keyword in query_keywords if keyword in doc_lower)
    score += keyword_matches * 3.0
    
    # 2. Keyword matching in title (weight: 5.0) 
    title = metadata.get('title', '').lower()
    title_matches = sum(1 for keyword in query_keywords if keyword in title)
    score += title_matches * 5.0
    
    # 3. Domain/URL relevance (weight: 20.0) - Increased weight for better domain prioritization
    url = metadata.get('url', '').lower()
    domain = metadata.get('domain', '').lower()
    
    # Enhanced domain matching - look for specific domain names in query
    domain_boost = 0
    for keyword in query_keywords:
        # Direct domain name matches (github, linkedin, etc.)
        if keyword in ['github', 'linkedin', 'stackoverflow', 'google', 'youtube', 'facebook', 'twitter']:
            if keyword in url or keyword in domain:
                domain_boost = 20.0
                break
        # General keyword in URL/domain
        elif keyword in url or keyword in domain:
            domain_boost = max(domain_boost, 10.0)
    
    score += domain_boost
    
    # 4. Visit count boost (logarithmic scaling, weight: 2.0) - Slightly increased
    visit_count = metadata.get('visit_count', 1)
    try:
        import math
        # Log scale to prevent high visit counts from dominating
        visit_boost = math.log(max(visit_count, 1)) * 2.0
        score += visit_boost
    except (ValueError, TypeError):
        # If visit_count is not a valid number, skip this boost
        pass
    
    # 5. Exact phrase matching bonus (weight: 15.0)
    if len(query_keywords) > 1:
        # Remove common words for phrase matching
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'how', 'many', 'what', 'did', 'i', 'my'}
        important_keywords = [kw for kw in query_keywords if kw not in common_words and len(kw) > 2]
        
        if len(important_keywords) >= 2:
            # Check if multiple important keywords appear close together
            for i, kw1 in enumerate(important_keywords):
                for kw2 in important_keywords[i+1:]:
                    if kw1 in doc_lower and kw2 in doc_lower:
                        # Find positions and check proximity
                        pos1 = doc_lower.find(kw1)
                        pos2 = doc_lower.find(kw2)
                        if abs(pos1 - pos2) < 100:  # Within 100 characters
                            score += 15.0
                            break
    
    return score


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
    
    # Create a proper retriever for the QA chain
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.documents import Document
    from typing import List
    
    class SimpleRetriever(BaseRetriever):
        documents: List[str]
        metadatas: List[dict]
        
        def __init__(self, documents: List[str], metadatas: List[dict]):
            super().__init__(documents=documents, metadatas=metadatas)
        
        def _get_relevant_documents(self, query: str) -> List[Document]:
            docs = []
            for doc, meta in zip(self.documents, self.metadatas):
                # Create a document with metadata
                doc_obj = Document(
                    page_content=doc,
                    metadata=meta
                )
                docs.append(doc_obj)
            return docs
        
        async def _aget_relevant_documents(self, query: str) -> List[Document]:
            # Async version - just call the sync version
            return self._get_relevant_documents(query)
    
    retriever = SimpleRetriever(documents, metadatas)
    
    # Get answer using enhanced QA
    result = answer_question_ollama(query, retriever)
    
    # Add enhanced context to the result
    result['enhanced_context'] = enhanced_context
    
    store.close()
    return result 