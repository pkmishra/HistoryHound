#!/usr/bin/env python3
"""
HistoryHounder CLI
Command-line interface for HistoryHounder functionality
"""

import argparse
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import server first (it has minimal dependencies)
from historyhounder.server import start_server

# Import other modules conditionally to avoid dependency issues
try:
    from historyhounder.extract_chrome_history import extract_history_from_sqlite, available_browsers
    from historyhounder.pipeline import extract_and_process_history
    from historyhounder.search import semantic_search, llm_qa_search
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="HistoryHounder - Chat with your browser history using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  historyhounder extract                    # Extract history from all browsers
  historyhounder extract --browser chrome   # Extract from Chrome only
  historyhounder search "python tutorial"   # Search history
  historyhounder qa "What did I learn?"     # Ask AI about history
  historyhounder server                     # Start backend server
  historyhounder server --port 8080         # Start server on specific port
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract browser history')
    extract_parser.add_argument('--browser', choices=['chrome', 'edge', 'brave', 'firefox', 'safari'], 
                               help='Specific browser to extract from')
    extract_parser.add_argument('--output', type=str, help='Output file path')
    extract_parser.add_argument('--days', type=int, help='Number of days back to extract')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search browser history')
    search_parser.add_argument('query', type=str, help='Search query')
    search_parser.add_argument('--top-k', type=int, default=5, help='Number of results to return')
    search_parser.add_argument('--embedder', type=str, default='sentence-transformers', 
                              help='Embedding backend to use')
    
    # Q&A command
    qa_parser = subparsers.add_parser('qa', help='Ask AI questions about history')
    qa_parser.add_argument('question', type=str, help='Question to ask')
    qa_parser.add_argument('--top-k', type=int, default=5, help='Number of context items')
    qa_parser.add_argument('--llm', type=str, default='ollama', help='LLM backend to use')
    qa_parser.add_argument('--model', type=str, default='llama3', help='LLM model to use')
    
    # Server command
    server_parser = subparsers.add_parser('server', help='Start backend server for browser extension')
    server_parser.add_argument('--port', type=int, default=8080, help='Port to run server on')
    server_parser.add_argument('--host', type=str, default='localhost', help='Host to bind server to')
    
    # List browsers command
    browsers_parser = subparsers.add_parser('browsers', help='List available browsers')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'server':
            handle_server(args)
        elif not DEPENDENCIES_AVAILABLE:
            print("❌ Other commands require additional dependencies")
            print("Please install: pip install beautifulsoup4 sentence-transformers chromadb instructor")
            return
        elif args.command == 'extract':
            handle_extract(args)
        elif args.command == 'search':
            handle_search(args)
        elif args.command == 'qa':
            handle_qa(args)
        elif args.command == 'browsers':
            handle_browsers(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def handle_extract(args):
    """Handle extract command"""
    print("🔍 Extracting browser history...")
    
    if args.browser:
        print(f"Targeting browser: {args.browser}")
        browsers = {args.browser: available_browsers().get(args.browser, {})}
    else:
        print("Scanning all available browsers...")
        browsers = available_browsers()
    
    if not browsers:
        print("❌ No browsers found")
        return
    
    for browser_name, browser_info in browsers.items():
        if not browser_info:
            print(f"⚠️  {browser_name}: Not available")
            continue
            
        print(f"\n📊 Extracting from {browser_name}...")
        try:
            # Get browser path
            browsers = available_browsers()
            if browser_name not in browsers:
                print(f"❌ Browser {browser_name} not found")
                continue
                
            db_path = browsers[browser_name]
            history_data = extract_history_from_sqlite(db_path, browser_name)
            
            if history_data:
                print(f"✅ Extracted {len(history_data)} history items from {browser_name}")
                
                # Process the data through the pipeline
                result = extract_and_process_history(
                    browser=browser_name,
                    db_path=db_path,
                    days=args.days,
                    with_content=True,
                    embed=False
                )
                
                if result['status'] != 'no_history':
                    processed_data = result['results']
                    print(f"✅ Processed {len(processed_data)} items through pipeline")
                else:
                    print(f"⚠️  No history data to process")
                    processed_data = []
                
                if args.output:
                    output_path = Path(args.output)
                    if browser_name != 'chrome':
                        output_path = output_path.with_name(f"{output_path.stem}_{browser_name}{output_path.suffix}")
                    
                    import json
                    with open(output_path, 'w') as f:
                        json.dump(processed_data, f, indent=2, default=str)
                    print(f"💾 Saved to {output_path}")
            else:
                print(f"⚠️  No history data found for {browser_name}")
                
        except Exception as e:
            print(f"❌ Error extracting from {browser_name}: {e}")


def handle_search(args):
    """Handle search command"""
    print(f"🔍 Searching history for: '{args.query}'")
    
    try:
        results = semantic_search(
            args.query, 
            top_k=args.top_k,
            embedder_backend=args.embedder
        )
        
        if results:
            print(f"\n✅ Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result.get('title', 'Untitled')}")
                print(f"   URL: {result.get('url', 'N/A')}")
                print(f"   Domain: {result.get('domain', 'N/A')}")
                print(f"   Visit Time: {result.get('visit_time', 'N/A')}")
                print(f"   Distance: {result.get('distance', 'N/A'):.4f}")
        else:
            print("❌ No results found")
            
    except Exception as e:
        print(f"❌ Search failed: {e}")


def handle_qa(args):
    """Handle Q&A command"""
    print(f"🤖 Asking: '{args.question}'")
    
    try:
        result = llm_qa_search(
            args.question,
            top_k=args.top_k,
            llm=args.llm,
            llm_model=args.model
        )
        
        print(f"\n💡 Answer:")
        print(result['answer'])
        
        if result.get('sources'):
            print(f"\n📚 Sources:")
            for i, source in enumerate(result['sources'], 1):
                print(f"{i}. {source}")
                
    except Exception as e:
        print(f"❌ Q&A failed: {e}")


def handle_server(args):
    """Handle server command"""
    print("🚀 Starting HistoryHounder Backend Server...")
    print(f"📍 Server will be available at: http://{args.host}:{args.port}")
    print("🔗 Browser extension can connect to this server for enhanced features")
    print("📖 API Documentation:")
    print("   GET  /api/health           - Health check")
    print("   GET  /api/search?q=query   - Semantic search")
    print("   POST /api/qa               - AI Q&A")
    print("   POST /api/process-history  - Process browser history")
    print("   GET  /api/stats            - Get statistics")
    print("\nPress Ctrl+C to stop the server")
    
    start_server(args.host, args.port)


def handle_browsers(args):
    """Handle browsers command"""
    print("🌐 Available browsers:")
    
    browsers = available_browsers()
    if not browsers:
        print("❌ No browsers found")
        return
    
    for browser_name, browser_info in browsers.items():
        if browser_info:
            print(f"✅ {browser_name}: {browser_info.get('path', 'Path not found')}")
        else:
            print(f"❌ {browser_name}: Not available")


if __name__ == "__main__":
    main() 