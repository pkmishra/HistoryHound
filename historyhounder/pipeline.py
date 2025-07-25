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
    
    results = []
    # 4. Fetch content
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
        if not valid_results:
            return {'status': 'no_valid_documents', 'results': results, 'num_embedded': 0}
        embedder = get_embedder(embedder_backend)
        docs = [r.get('text') or r.get('description') or '' for r in valid_results]
        embeddings = embedder.embed(docs)
        metadatas = [
            convert_metadata_for_chroma({k: v for k, v in r.items() if k not in ('text', 'description')})
            for r in valid_results
        ]
        store = ChromaVectorStore(persist_directory=persist_directory)
        store.add(docs, embeddings, metadatas)
        store.close()
        return {'status': 'embedded', 'results': valid_results, 'num_embedded': len(docs)}
    return {'status': 'fetched', 'results': results} 