# HistoryHounder: Chat with Your Browser History

HistoryHounder is a local, privacy-first tool that lets you search and chat with your browser history using natural language. It supports Chrome, Brave, Edge, Firefox, and Safari, and can extract, embed, and semantically search your browsing history. You can use local LLMs (like Ollama) for true Q&A over your history.

---

## Features
- **Browser-agnostic**: Works with Chrome, Brave, Edge, Firefox, Safari
- **Content extraction**: Fetches and extracts main text from articles, metadata from videos (YouTube, etc.)
- **Semantic search**: Embeds your history and lets you search with natural language
- **LLM Q&A**: Use local LLMs (Ollama) to answer questions using your browsing history as context
- **Domain/URL filtering**: Ignore specific domains or URL patterns during extraction, embedding, and search
- **Robust metadata handling**: All metadata (including datetime, None, lists, dicts) is safely converted to ChromaDB-compatible types; edge cases are tested
- **Pluggable architecture**: Swap out embedders, LLMs, and vector stores
- **Local-first**: All data stays on your machine
- **Robust end-to-end integration tests**: The test suite uses real, public URLs (externalized in `tests/real_world_urls.txt`) to verify the full pipeline, including extraction, embedding, and semantic search. No mocking is used in integration tests—real network calls and embeddings are performed. YouTube extraction is handled by yt-dlp and is robust to real-world metadata fields.

---

## Setup

### 1. Clone the repo and enter the directory
```sh
git clone <repo-url>
cd HistoryHounder
```

### 2. Install [uv](https://github.com/astral-sh/uv) (if not already installed)
```sh
pip install uv
```

### 3. Create a virtual environment and install dependencies
```sh
uv venv
uv pip install -r requirements.txt
```

### 4. (Optional) Install and run [Ollama](https://ollama.com/) for local LLM Q&A
- Download and install Ollama from [https://ollama.com/](https://ollama.com/)
- Start Ollama: `ollama serve`
- Pull a model (e.g., `ollama pull llama3`)

---

## Usage

### **Extract and Embed Your Browser History**
Extract, fetch content, and embed your history from the last 7 days:
```sh
uv run python -m historyhounder.cli extract --days 7 --with-content --embed
```

### **Domain and URL Pattern Filtering**
You can ignore specific domains or URL patterns during extraction, embedding, and search using the `--ignore-domain` and `--ignore-pattern` options. Multiple values can be specified in a single argument, separated by commas:

- `--ignore-domain`: Ignore all URLs from specific domains (comma-separated)
- `--ignore-pattern`: Ignore all URLs matching substrings or regex patterns (comma-separated)

**Examples:**

Ignore all YouTube and Facebook URLs when extracting and embedding:
```sh
uv run python -m historyhounder.cli extract --with-content --embed --ignore-domain "youtube.com,facebook.com"
```

Ignore all URLs containing `/ads/` or matching a regex pattern:
```sh
uv run python -m historyhounder.cli extract --with-content --embed --ignore-pattern "/ads/,.*tracking.*"
```

You can combine these options as needed. The same options are available for the `search` command.

### **Semantic Search**
Search your embedded history with a natural language query:
```sh
uv run python -m historyhounder.cli search --query "Shopify AI tools" --top-k 5
```

### **LLM Q&A with Ollama**
Ask a question and get an answer from your history using a local LLM:
```sh
uv run python -m historyhounder.cli search --query "What was that article I read last week about Shopify and AI tools?" --llm ollama --llm-model llama3
```

- You can change `--llm-model` to any model available in your Ollama installation (e.g., `mistral`, `llama2`, etc.)

---

## Running Tests

To run all tests:
```sh
uv run pytest -v
```

The integration tests use real, public URLs (externalized in `tests/real_world_urls.txt`) to ensure the pipeline works as a real user would experience it. No mocking is used in integration tests. YouTube extraction is powered by yt-dlp and the tests are robust to metadata field variations.

### Integration (End-to-End) Tests
- The test suite includes robust integration tests that simulate the full pipeline: extracting sample browser history, fetching content, embedding, storing in ChromaDB, and performing semantic search.
- Integration tests use pytest fixtures to ensure each test uses a unique ChromaDB collection, providing full isolation and preventing cross-test contamination.
- **Tests now use real datetime objects and edge-case metadata** to ensure all metadata is properly converted and stored in ChromaDB. This catches issues with datetime, None, lists, dicts, and other non-primitive types.

### CLI Design Best Practices

The CLI (`historyhounder/cli.py`) is designed as a thin entry point:
- **No business logic should reside in the CLI.**
- All core logic (history extraction, content fetching, embedding, vector store operations, etc.) lives in modules under `historyhounder/`.
- The CLI is responsible only for argument parsing, user interaction, and delegating to the appropriate functions/classes.
- This separation ensures:
  - **Testability**: Core logic can be tested directly, without invoking the CLI.
  - **Reusability**: Logic can be reused in other interfaces (APIs, GUIs, scripts).
  - **Maintainability**: The CLI remains simple and less prone to bugs.

If you notice business logic in the CLI, consider refactoring it into a module and calling it from the CLI entry point.

---

## Project Structure
```
historyhounder/
  cli.py                # Main CLI entry point
  history_extractor.py  # Extracts browser history
  content_fetcher.py    # Fetches and extracts content from URLs
  vector_store.py       # Chroma vector DB integration
  embedder/             # Pluggable embedders (sentence-transformers, etc.)
  llm/
    ollama_qa.py        # LangChain Q&A with Ollama
  ...
tests/                  # All tests (pytest, including integration)
requirements.txt         # All dependencies
pytest.ini               # Pytest config (warning filters)
README.md                # This file
```

---

## Notes
- All commands should be run with `uv run ...` for correct environment isolation.
- The tool is modular and can be extended to support more LLMs, embedders, or browsers.
- For best results, keep your browser closed while extracting history (to ensure the latest data is flushed to disk).
- The test suite is robust and covers both unit and end-to-end integration scenarios, including real-world and edge-case metadata handling.
- **LangChain integration uses the new split-out packages (`langchain-huggingface`, `langchain-chroma`, `langchain-ollama`) and is future-proofed for LangChain 1.0+.**

---

## License
MIT (or your chosen license) 

---

## ChromaDB Best Practices: PersistentClient for Test Isolation and Multi-Instance Support

- **ChromaDB uses a singleton/shared client by default, which does not allow multiple clients with different settings (such as different persist directories) in the same process.**
- To support integration tests, test isolation, and multiple independent vector stores in the same process, **HistoryHounder uses `chromadb.PersistentClient` instead of `chromadb.Client`**.
- This allows each test or pipeline to specify its own `persist_directory` (via the `path` argument), ensuring that data is isolated and there are no conflicts between tests or runs.
- **If you need to use multiple ChromaDB databases or collections in the same process (e.g., for testing, multi-user, or multi-tenant scenarios), always use `PersistentClient`.**
- Example usage:

```python
import chromadb
client = chromadb.PersistentClient(path="path/to/chroma_db")
collection = client.get_or_create_collection("history")
```

- This is now the default in `historyhounder/vector_store.py` and is required for all integration tests to pass.
- For more details, see [ChromaDB Issue: An instance of Chroma already exists for ... with different settings](https://blog.csdn.net/DLW__/article/details/145953793)

--- 