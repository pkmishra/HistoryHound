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
    results = []
    # 3. Fetch content
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
    # 4. Embed and store
    if embed:
        if progress_callback:
            progress_callback("Embedding and storing in Chroma...")
        embedder = get_embedder(embedder_backend)
        docs = [r.get('text') or r.get('description') or '' for r in results]
        embeddings = embedder.embed(docs)
        metadatas = [
            convert_metadata_for_chroma({k: v for k, v in r.items() if k not in ('text', 'description')})
            for r in results
        ]
        store = ChromaVectorStore()
        store.add(docs, embeddings, metadatas)
        return {'status': 'embedded', 'results': results, 'num_embedded': len(docs)}
    return {'status': 'fetched', 'results': results} 