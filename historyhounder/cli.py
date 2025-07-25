import argparse
import json
from historyhounder import history_extractor
from historyhounder.extract_chrome_history import available_browsers, BROWSER_PATHS
from historyhounder import content_fetcher
from historyhounder.embedder import get_embedder
from historyhounder.vector_store import ChromaVectorStore
from historyhounder.llm.ollama_qa import answer_question_ollama
import os
import re
from urllib.parse import urlparse
from datetime import datetime
from historyhounder.utils import parse_comma_separated_values, should_ignore, convert_metadata_for_chroma
from historyhounder.pipeline import extract_and_process_history
from historyhounder.search import semantic_search, llm_qa_search


def validate_file_path(file_path):
    """
    Validate file path to prevent path traversal attacks.
    Returns True if path is safe, False otherwise.
    """
    if not file_path or not isinstance(file_path, str):
        return False
    
    # Check for path traversal attempts in the original path
    if '..' in file_path:
        return False
    
    # Normalize the path to resolve any .. or . components
    try:
        normalized_path = os.path.normpath(file_path)
        absolute_path = os.path.abspath(normalized_path)
    except Exception:
        return False
    
    # Reject absolute paths that could access system files
    # Allow only relative paths or paths in safe directories
    if file_path.startswith('/'):
        # Check if it's in a temporary directory
        temp_dirs = ['/tmp', '/var/tmp', '/private/tmp', '/var/folders', '/private/var/folders']
        user_home = os.path.expanduser('~')
        
        is_temp = any(absolute_path.startswith(temp_dir) for temp_dir in temp_dirs)
        is_user_home = absolute_path.startswith(user_home)
        
        if not (is_temp or is_user_home):
            return False
    
    # Check for Windows-style paths with colons (except drive letters)
    if ':' in file_path and not (len(file_path) >= 2 and file_path[1] == ':' and file_path[0].isalpha()):
        return False
    
    # Ensure the file exists and is accessible
    if not os.path.exists(absolute_path):
        return False
    
    # Check if it's a file (not a directory)
    if not os.path.isfile(absolute_path):
        return False
    
    return True


def extract_command(args):
    browsers = available_browsers()
    browser = args.browser
    db_path = args.db_path
    
    if not db_path:
        if browser:
            if browser in browsers:
                db_path = browsers[browser]
            else:
                print(f"Unknown browser: {browser}")
                print(f"Available: {list(browsers.keys())}")
                return
        else:
            if not browsers:
                print("No supported browser history files found.")
                print(f"Checked: {BROWSER_PATHS}")
                return
            print("Available browsers:")
            for i, (name, path) in enumerate(browsers.items()):
                print(f"  {i+1}. {name} ({path})")
            try:
                choice = int(input("Select browser [1]: ") or "1")
                browser = list(browsers.keys())[choice-1]
                db_path = browsers[browser]
            except (ValueError, IndexError):
                print("Invalid selection.")
                return
    
    # Validate the database path to prevent path traversal
    if not validate_file_path(db_path):
        print(f"Error: Invalid or unsafe database path: {db_path}")
        print("Please provide a valid path to a browser history database file.")
        return
    
    # Parse comma-separated ignore values
    ignore_domains = parse_comma_separated_values(args.ignore_domain) if args.ignore_domain else []
    ignore_patterns = parse_comma_separated_values(args.ignore_pattern) if args.ignore_pattern else []
    
    def progress(msg):
        print(msg)
    
    # Remove debug information to prevent information disclosure
    result = extract_and_process_history(
        browser=browser,
        db_path=db_path,
        days=args.days,
        ignore_domains=ignore_domains,
        ignore_patterns=ignore_patterns,
        with_content=args.with_content,
        embed=args.embed,
        embedder_backend=args.embedder,
        progress_callback=progress,
        persist_directory=args.chroma_dir,
        url_limit=args.url_limit
    )
    
    if result['status'] == 'no_history':
        print("No history found for the given criteria.")
        return
    
    if args.embed:
        print(f"Stored {result.get('num_embedded', 0)} documents in Chroma.")
    else:
        # Print results as JSON
        def isoformat_last_visit(item):
            if 'last_visit_time' in item and hasattr(item['last_visit_time'], 'isoformat'):
                item['last_visit_time'] = item['last_visit_time'].isoformat()
            return item
        print(json.dumps([isoformat_last_visit(dict(r)) for r in result['results']], indent=2))

def search_command(args):
    if args.llm == 'ollama':
        result = llm_qa_search(args.query, top_k=args.top_k, llm=args.llm, llm_model=args.llm_model)
        print("\nAnswer:")
        print(result['answer'])
        print("\nSources:")
        for i, src in enumerate(result['sources'], 1):
            print(f"[{i}] {src[:200]}{'...' if len(src) > 200 else ''}")
    else:
        # Remove debug information to prevent information disclosure
        results = semantic_search(args.query, top_k=args.top_k, embedder_backend=args.embedder, persist_directory=args.chroma_dir)
        print(json.dumps(results, indent=2))

def main():
    parser = argparse.ArgumentParser(description="HistoryHounder: Chat with your browser history.")
    subparsers = parser.add_subparsers(dest='command')

    # Extract command (default)
    extract_parser = subparsers.add_parser('extract', help='Extract and (optionally) embed history')
    extract_parser.add_argument('--browser', type=str, help='Browser name (chrome, brave, edge, safari, firefox:profile)')
    extract_parser.add_argument('--db-path', type=str, help='Custom path to history database')
    extract_parser.add_argument('--days', type=int, help='Number of days to look back (default: all)')
    extract_parser.add_argument('--with-content', action='store_true', help='Fetch and extract main content/metadata for each URL')
    extract_parser.add_argument('--embed', action='store_true', help='Embed content and store in Chroma vector DB')
    extract_parser.add_argument('--embedder', type=str, default='sentence-transformers', help='Embedder backend to use')
    extract_parser.add_argument('--ignore-domain', type=str, help='Ignore URLs from these domains (comma-separated, e.g., "google.com,facebook.com")')
    extract_parser.add_argument('--ignore-pattern', type=str, help='Ignore URLs matching these patterns or substrings (comma-separated, e.g., "login,logout,/admin")')
    extract_parser.add_argument('--chroma-dir', type=str, default='chroma_db', help='Chroma vector DB directory to use')
    extract_parser.add_argument('--url-limit', type=int, default=None, help='Limit the number of URLs to extract (default: all)')
    extract_parser.set_defaults(func=extract_command)

    # Search command
    search_parser = subparsers.add_parser('search', help='Semantic search your history')
    search_parser.add_argument('--query', type=str, required=True, help='Natural language search query')
    search_parser.add_argument('--top-k', type=int, default=5, help='Number of results to return')
    search_parser.add_argument('--embedder', type=str, default='sentence-transformers', help='Embedder backend to use')
    search_parser.add_argument('--llm', type=str, default=None, help='LLM to use for Q&A (e.g., ollama)')
    search_parser.add_argument('--llm-model', type=str, default='llama3', help='Ollama model to use (default: llama3)')
    search_parser.add_argument('--chroma-dir', type=str, default='chroma_db', help='Chroma vector DB directory to use')
    search_parser.set_defaults(func=search_command)

    # If no subcommand, default to extract
    args = parser.parse_args()
    if not args.command:
        args.command = 'extract'
        args.func = extract_command
    args.func(args)

if __name__ == '__main__':
    main() 