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
    Enhanced Q&A search with temporal filtering support and context optimization.
    """
    embedder = get_embedder(embedder_backend)
    store = ChromaVectorStore(persist_directory=persist_directory)
    
    # Parse temporal references from the query
    filtered_query, start_date, end_date = parse_temporal_reference(query)
    temporal_filter = (start_date, end_date) if start_date and end_date else None
    
    # Determine question type for adaptive context sizing
    question_type = classify_question_type(query)
    adaptive_top_k = get_adaptive_context_size(question_type, top_k)
    
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
    
    # For semantic search, use the filtered query with improved relevance
    if filtered_query.strip():
        try:
            # Use our improved semantic search for better document selection
            relevant_results = semantic_search(filtered_query, top_k=adaptive_top_k, 
                                             embedder_backend=embedder_backend, 
                                             persist_directory=persist_directory)
            
            if relevant_results:
                # Extract documents and metadatas from semantic search results
                documents = [result['document'] for result in relevant_results]
                metadatas = [result['metadata'] for result in relevant_results]
                
                # Apply context optimization
                documents, metadatas = optimize_context_window(documents, metadatas, question_type)
                
                # Re-create enhanced context with optimized results
                enhanced_context = enhance_context_for_qa(documents, metadatas, temporal_filter)
        except Exception:
            # If semantic search fails, continue with all documents but optimize them
            documents, metadatas = optimize_context_window(documents, metadatas, question_type)
            enhanced_context = enhance_context_for_qa(documents, metadatas, temporal_filter)
    
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
    
    # IMPORTANT: Filter sources to ensure they match question relevance
    # The LangChain retriever might return all documents, but we want only relevant ones
    filtered_sources = filter_sources_by_relevance(result.get('sources', []), query)
    result['sources'] = filtered_sources
    
    # Add enhanced context to the result
    result['enhanced_context'] = enhanced_context
    
    store.close()
    return result


def classify_question_type(query):
    """
    Classify question type for adaptive context optimization.
    """
    query_lower = query.lower()
    
    # Statistical questions need less content but more metadata
    if any(phrase in query_lower for phrase in ['how many', 'how much', 'count', 'total', 'most visited', 'top ', 'number of']):
        return 'statistical'
    
    # Comparative questions need data from multiple sources  
    elif any(phrase in query_lower for phrase in ['compare', ' vs ', 'versus', 'more than', 'better than', 'or ', ' vs. ', 'difference between']):
        return 'comparative'
    
    # Semantic questions need full content for understanding
    elif any(phrase in query_lower for phrase in ['what is', 'what are', 'explain', 'about', 'describe', 'topics', 'research', 'learn']):
        return 'semantic'
    
    # Temporal questions need chronological context
    elif any(phrase in query_lower for phrase in ['yesterday', 'last week', 'recently', 'when', 'time', 'today', 'this week', 'last month']):
        return 'temporal'
    
    # Default to factual
    return 'factual'


def get_adaptive_context_size(question_type, base_top_k):
    """
    Determine optimal context size based on question type.
    """
    if question_type == 'statistical':
        return base_top_k  # Standard size for counting/stats
    elif question_type == 'temporal':
        return base_top_k + 2  # Slightly more for time-based queries
    elif question_type == 'semantic':
        return min(base_top_k + 5, 10)  # More content for understanding
    elif question_type == 'comparative':
        return base_top_k + 3  # More sources for comparison
    else:  # factual
        return base_top_k


def optimize_context_window(documents, metadatas, question_type):
    """
    Optimize context window by removing duplicates and truncating content based on question type.
    """
    if not documents or not metadatas:
        return documents, metadatas
    
    # 1. Remove duplicate content
    seen_content = set()
    unique_docs = []
    unique_metas = []
    
    for doc, meta in zip(documents, metadatas):
        # Create a fingerprint based on URL and first 100 characters
        url = meta.get('url', '')
        content_fingerprint = f"{url}:{doc[:100]}"
        
        if content_fingerprint not in seen_content:
            seen_content.add(content_fingerprint)
            unique_docs.append(doc)
            unique_metas.append(meta)
    
    # 2. Adaptive content truncation based on question type
    optimized_docs = []
    for doc in unique_docs:
        if question_type == 'statistical':
            # Statistical questions need minimal content, focus on metadata
            optimized_docs.append(doc[:300])  # Short content
        elif question_type == 'temporal':
            # Temporal questions need moderate content with time context
            optimized_docs.append(doc[:500])  # Medium content
        elif question_type == 'semantic':
            # Semantic questions need full content for understanding
            optimized_docs.append(doc[:1000])  # Longer content
        elif question_type == 'comparative':
            # Comparative questions need moderate content from multiple sources
            optimized_docs.append(doc[:400])  # Balanced content
        else:  # factual
            optimized_docs.append(doc[:600])  # Standard content
    
    return optimized_docs, unique_metas 


def filter_sources_by_relevance(sources, query, max_sources=5):
    """
    Filter sources to ensure they match the question relevance.
    This addresses the issue where irrelevant sources appear in the UI.
    """
    if not sources:
        return sources
    
    import re
    
    # Extract query keywords for relevance filtering
    query_lower = query.lower()
    clean_query = re.sub(r'[^\w\s]', '', query_lower)
    query_keywords = set(word for word in clean_query.split() if len(word) > 1)
    
    # Score each source for relevance to the query
    scored_sources = []
    for source in sources:
        if isinstance(source, dict):
            # Calculate relevance score for this source
            score = calculate_source_relevance_score(source, query_lower, query_keywords)
            scored_sources.append((source, score))
        else:
            # Handle old format if needed
            scored_sources.append((source, 0.0))
    
    # Sort by relevance score and return top sources
    scored_sources.sort(key=lambda x: x[1], reverse=True)
    
    # Return only sources with positive relevance scores
    relevant_sources = [source for source, score in scored_sources[:max_sources] if score > 0]
    
    # If no relevant sources found, return at least one source to avoid empty results
    if not relevant_sources and scored_sources:
        relevant_sources = [scored_sources[0][0]]
    
    return relevant_sources


def calculate_source_relevance_score(source, query_lower, query_keywords):
    """
    Calculate relevance score for a source based on the query.
    """
    score = 0.0
    
    url = source.get('url', '').lower()
    title = source.get('title', '').lower()
    domain = source.get('domain', '').lower()
    content = source.get('content', '').lower()
    
    # 1. Domain name matching (highest priority)
    for keyword in query_keywords:
        if keyword in ['github', 'linkedin', 'stackoverflow', 'google', 'youtube', 'facebook', 'twitter']:
            if keyword in url or keyword in domain:
                score += 20.0
                break
    
    # 2. Title keyword matching
    title_matches = sum(1 for keyword in query_keywords if keyword in title)
    score += title_matches * 5.0
    
    # 3. Content keyword matching
    content_matches = sum(1 for keyword in query_keywords if keyword in content)
    score += content_matches * 2.0
    
    # 4. URL keyword matching (general)
    url_matches = sum(1 for keyword in query_keywords if keyword in url)
    score += url_matches * 3.0
    
    return score 