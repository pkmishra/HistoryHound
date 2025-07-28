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
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting llm_qa_search with query: {query}")
    logger.info(f"Using model: {llm_model}, top_k: {top_k}")
    
    # Check if this is a statistical question
    # More precise detection to avoid treating specific domain questions as statistical
    statistical_keywords = [
        'most visited', 'most frequent', 'highest visits', 'visit count', 
        'statistics', 'how many total', 'count total', 'frequency total',
        'popular', 'top visited', 'most popular', 'highest frequency',
        'most often', 'most times', 'most frequently'
    ]
    
    # Check for specific domain questions that should use semantic search
    domain_specific_keywords = [
        'github', 'linkedin', 'amazon', 'google', 'facebook', 'twitter',
        'youtube', 'reddit', 'stackoverflow', 'medium', 'wikipedia',
        'slickdeals', 'timesofindia', 'keybase', 'apple', 'microsoft'
    ]
    
    query_lower = query.lower()
    
    # If the question mentions a specific domain, use semantic search
    has_specific_domain = any(domain in query_lower for domain in domain_specific_keywords)
    
    # Only treat as statistical if it's asking about overall patterns, not specific domains
    is_statistical = (
        any(keyword in query_lower for keyword in statistical_keywords) and 
        not has_specific_domain
    )
    
    embedder = get_embedder(embedder_backend)
    store = ChromaVectorStore(persist_directory=persist_directory)
    
    if is_statistical:
        logger.info("Detected statistical question, retrieving by visit count")
        # For statistical questions, get all documents and sort by visit count
        collection = store.collection
        if collection:
            all_results = collection.get()
            if all_results and all_results['documents']:
                # Create list of (doc, meta, visit_count) tuples
                docs_with_counts = []
                for i, (doc, meta) in enumerate(zip(all_results['documents'], all_results['metadatas'])):
                    visit_count = meta.get('visit_count', 1)
                    docs_with_counts.append((doc, meta, visit_count))
                
                # Sort by visit count (descending) and take top_k
                docs_with_counts.sort(key=lambda x: x[2], reverse=True)
                documents = [doc for doc, meta, count in docs_with_counts[:top_k]]
                metadatas = [meta for doc, meta, count in docs_with_counts[:top_k]]
                
                logger.info(f"Retrieved {len(documents)} documents sorted by visit count")
                for i, (doc, meta, count) in enumerate(docs_with_counts[:top_k]):
                    logger.info(f"Document {i+1}: {meta.get('title', 'No title')} - {meta.get('url', 'No URL')} - visits: {count}")
            else:
                logger.warning("No documents found in collection")
                documents = []
                metadatas = []
        else:
            logger.warning("No collection found")
            documents = []
            metadatas = []
    else:
        logger.info("Using semantic search for non-statistical question")
        
        # For domain-specific questions, use direct URL matching instead of semantic search
        collection = store.collection
        if collection and has_specific_domain:
            logger.info("Detected domain-specific question, using direct URL matching")
            all_results = collection.get()
            if all_results and all_results['documents']:
                # Find documents that match the domain in URL or title
                matching_docs = []
                for doc, meta in zip(all_results['documents'], all_results['metadatas']):
                    url = meta.get('url', '').lower()
                    title = meta.get('title', '').lower()
                    
                    # Check if any domain keyword matches the URL or title
                    for domain in domain_specific_keywords:
                        if domain in url or domain in title:
                            matching_docs.append((doc, meta))
                            break
                
                # Sort by visit count and take top_k
                matching_docs.sort(key=lambda x: x[1].get('visit_count', 1), reverse=True)
                documents = [doc for doc, meta in matching_docs[:top_k]]
                metadatas = [meta for doc, meta in matching_docs[:top_k]]
                
                logger.info(f"Retrieved {len(documents)} documents via URL matching")
                for i, (doc, meta) in enumerate(zip(documents, metadatas)):
                    logger.info(f"Document {i+1}: {meta.get('title', 'No title')} - {meta.get('url', 'No URL')}")
            else:
                logger.warning("No documents found in collection")
                documents = []
                metadatas = []
        else:
            # Use regular semantic search for non-domain questions
            query_emb = embedder.embed([query])[0]
            results = store.query(query_emb, top_k=top_k)
            documents = results['documents'][0] if results['documents'] else []
            metadatas = results['metadatas'][0] if results['metadatas'] else []
            
            logger.info(f"Retrieved {len(documents)} documents via semantic search")
            for i, (doc, meta) in enumerate(zip(documents, metadatas)):
                logger.info(f"Document {i+1}: {meta.get('title', 'No title')} - {meta.get('url', 'No URL')}")
    
    # Create a simple retriever-like object
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.documents import Document
    
    class SimpleRetriever(BaseRetriever):
        def __init__(self, docs, metas):
            super().__init__()
            self._docs = docs
            self._metas = metas
        
        def get_relevant_documents(self, query):
            # Create documents with both content and metadata for statistical analysis
            documents = []
            for doc, meta in zip(self._docs, self._metas):
                # Format metadata for better context including visit count
                visit_count = meta.get('visit_count', 1)
                metadata_str = f"URL: {meta.get('url', 'N/A')}\nTitle: {meta.get('title', 'N/A')}\nVisit Time: {meta.get('visit_time', 'N/A')}\nDomain: {meta.get('domain', 'N/A')}\nVisit Count: {visit_count}"
                full_content = f"Page Content:\n{doc}\n\nMetadata:\n{metadata_str}"
                documents.append(Document(page_content=full_content, metadata=meta))
            return documents
        
        async def aget_relevant_documents(self, query):
            return self.get_relevant_documents(query)
    
    retriever = SimpleRetriever(documents, metadatas)
    
    logger.info("Calling answer_question_ollama")
    result = answer_question_ollama(query, retriever, model=llm_model)
    
    logger.info(f"QA result: {result.get('answer', '')[:100]}...")
    
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