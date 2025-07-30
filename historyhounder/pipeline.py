from historyhounder import history_extractor, content_fetcher
from historyhounder.embedder import get_embedder
from historyhounder.vector_store import ChromaVectorStore
from historyhounder.utils import should_ignore, convert_metadata_for_chroma


def extract_and_process_history(
    browser,
    db_path,
    days=None,
    ignore_domains=None,
    ignore_patterns=None,
    with_content=False,
    embed=False,
    embedder_backend='sentence-transformers',
    progress_callback=None,
    persist_directory='chroma_db',
    url_limit=None,
    existing_urls=None,
):
    """
    Orchestrate extraction, filtering, content fetching, embedding, and storing.
    Returns a dict with results and status.
    """
    ignore_domains = ignore_domains or []
    ignore_patterns = ignore_patterns or []
    # 1. Extract history
    history = history_extractor.extract_history(browser, db_path, days=days)
    # 2. Filter
    if ignore_domains or ignore_patterns:
        history = [h for h in history if not should_ignore(h['url'], ignore_domains, ignore_patterns)]
    if not history:
        return {'status': 'no_history', 'results': []}
    
    # 3. Apply URL limit if specified
    if url_limit is not None and url_limit >= 0:
        history = history[:url_limit]
    
    # 3.5. Filter out existing URLs if provided (incremental processing)
    if existing_urls:
        original_count = len(history)
        history = [h for h in history if h.get('url') not in existing_urls]
        filtered_count = len(history)
        if progress_callback:
            progress_callback(f"Filtered out {original_count - filtered_count} existing URLs, processing {filtered_count} new URLs")
        print(f"DEBUG: Filtered out {original_count - filtered_count} existing URLs, processing {filtered_count} new URLs")
        
        # If no new URLs to process, return early
        if len(history) == 0:
            return {'status': 'no_new_documents', 'results': [], 'num_embedded': 0}
    
    results = []
    # 4. Fetch content (only for new URLs after filtering)
    if with_content or embed:
        if progress_callback:
            progress_callback(f"Fetching content for {len(history)} URLs...")
        for i, h in enumerate(history, 1):
            if progress_callback:
                progress_callback(f"[{i}/{len(history)}] {h['url']}")
            content = content_fetcher.fetch_and_extract(h['url'])
            results.append({**h, **content})
    else:
        results = history
    
    # 5. Embed and store
    if embed:
        if progress_callback:
            progress_callback("Embedding and storing in Chroma...")
        # Filter out documents with errors or empty text/description
        valid_results = [r for r in results if not r.get('error') and (r.get('text') or r.get('description'))]
        
        print(f"DEBUG: Total results: {len(results)}, Valid results: {len(valid_results)}")
        for i, r in enumerate(results[:3]):  # Show first 3 results for debugging
            print(f"DEBUG: Result {i}: error={r.get('error')}, text={bool(r.get('text'))}, description={bool(r.get('description'))}")
        
        if not valid_results:
            return {'status': 'no_valid_documents', 'results': results, 'num_embedded': 0}
        
        # Deduplicate by URL, keeping the most recent entry
        url_map = {}
        for r in valid_results:
            url = r.get('url', '')
            if url:
                # Keep the most recent entry for each URL
                if url not in url_map or r.get('lastVisitTime', 0) > url_map[url].get('lastVisitTime', 0):
                    url_map[url] = r
        
        # Convert back to list
        deduplicated_results = list(url_map.values())
        
        embedder = get_embedder(embedder_backend)
        docs = [r.get('text') or r.get('description') or '' for r in deduplicated_results]
        embeddings = embedder.embed(docs)
        
        # Prepare metadata with proper field mapping
        metadatas = []
        for r in deduplicated_results:
            metadata = {k: v for k, v in r.items() if k not in ('text', 'description')}
            # Map last_visit_time to visit_time for the search API
            if 'last_visit_time' in metadata:
                metadata['visit_time'] = metadata['last_visit_time']
            
            # Extract domain from URL if not already present
            if 'domain' not in metadata or not metadata['domain']:
                url = metadata.get('url', '')
                if url:
                    try:
                        from urllib.parse import urlparse
                        parsed_url = urlparse(url)
                        metadata['domain'] = parsed_url.netloc
                    except:
                        metadata['domain'] = 'unknown'
                else:
                    metadata['domain'] = 'unknown'
            
            metadatas.append(convert_metadata_for_chroma(metadata))
        
        store = ChromaVectorStore(persist_directory=persist_directory)
        store.add(docs, embeddings, metadatas)
        store.close()
        return {'status': 'embedded', 'results': deduplicated_results, 'num_embedded': len(docs)}
    
    return {'status': 'fetched', 'results': results} 