# HistoryHounder: Chat with Your Browser History

HistoryHounder is a local, privacy-first tool that lets you search and chat with your browser history using natural language. It supports Chrome, Brave, Edge, Firefox, and Safari, and can extract, embed, and semantically search your browsing history. You can use local LLMs (like Ollama) for true Q&A over your history.

---

## Features
- **Browser-agnostic**: Works with Chrome, Brave, Edge, Firefox, Safari
- **Content extraction**: Fetches and extracts main text from articles, metadata from videos (YouTube, etc.)
- **Semantic search**: Embeds your history and lets you search with natural language
- **LLM Q&A**: Use local LLMs (Ollama) to answer questions using your browsing history as context
- **Domain/URL filtering**: Ignore specific domains or URL patterns during extraction, embedding, and search
- **URL limiting**: Control the number of distinct URLs processed for testing or subset processing
- **Robust metadata handling**: All metadata (including datetime, None, lists, dicts) is safely converted to ChromaDB-compatible types; edge cases are tested
- **Pluggable architecture**: Swap out embedders, LLMs, and vector stores
- **Local-first**: All data stays on your machine
- **Security hardened**: Comprehensive input validation, path sanitization, and security testing
- **Comprehensive test coverage**: Extensive test suite covering unit tests, integration tests, edge cases, error handling, and real-world scenarios
- **Robust end-to-end integration tests**: The test suite uses real, public URLs (externalized in `tests/real_world_urls.txt`) to verify the full pipeline, including extraction, embedding, and semantic search. No mocking is used in integration tests—real network calls and embeddings are performed. YouTube extraction is handled by yt-dlp and is robust to real-world metadata fields.

---

## Architecture

### Core Components

HistoryHounder follows a modular, loosely-coupled architecture with clear separation of concerns:

#### 1. **History Extraction Layer**
- **`history_extractor.py`**: Browser-agnostic history extraction with support for Chrome, Brave, Edge, Firefox, and Safari
- **`extract_chrome_history.py`**: Browser detection and path management
- **Secure temporary file handling**: Uses context managers for safe database copying and cleanup

#### 2. **Content Processing Layer**
- **`content_fetcher.py`**: Hybrid content extraction using readability-lxml for articles and yt-dlp for videos
- **URL validation**: Comprehensive security validation to prevent command injection
- **Fallback mechanisms**: Multiple extraction strategies for robust content handling

#### 3. **Vector Storage Layer**
- **`vector_store.py`**: ChromaDB integration with persistent client for test isolation
- **Metadata conversion**: Safe handling of complex data types (datetime, None, lists, dicts)
- **Collection management**: Proper cleanup and resource management

#### 4. **Embedding Layer**
- **`embedder/`**: Pluggable embedding backends (sentence-transformers, etc.)
- **Registry pattern**: Easy addition of new embedding models
- **Batch processing**: Efficient handling of large document sets

#### 5. **LLM Integration Layer**
- **`llm/ollama_qa.py`**: LangChain integration with Ollama for local Q&A
- **Retrieval-Augmented Generation (RAG)**: Context-aware question answering
- **Prompt engineering**: Optimized prompts for browser history context

#### 6. **Pipeline Orchestration**
- **`pipeline.py`**: Main orchestration logic coordinating all components
- **Filtering**: Domain and pattern-based URL filtering
- **Progress tracking**: User feedback during long-running operations

#### 7. **CLI Interface**
- **`cli.py`**: Thin CLI layer with argument parsing and user interaction
- **No business logic**: All core functionality delegated to modules
- **Error handling**: User-friendly error messages and validation

### Data Flow

```
Browser History DB → History Extractor → Content Fetcher → Embedder → Vector Store
                                                              ↓
User Query → Search/LLM → Vector Store → Results/Answers
```

### Security Architecture

- **Input Validation**: All user inputs (URLs, file paths, CLI args) are validated
- **Path Sanitization**: File operations restricted to safe directories
- **Subprocess Security**: URL validation prevents command injection
- **Error Sanitization**: Sensitive information removed from error messages
- **Temporary File Security**: Secure creation, permissions, and cleanup

---

## Technology Choices

### Core Technologies

#### **Python 3.9+**
- **Rationale**: Modern Python features, excellent ecosystem for ML/AI, strong typing support
- **Benefits**: Rich library ecosystem, easy deployment, cross-platform compatibility

#### **ChromaDB (Vector Database)**
- **Rationale**: Local-first, Python-native, excellent for embeddings and metadata
- **Benefits**: 
  - No external dependencies (runs locally)
  - Excellent metadata support
  - Persistent client for test isolation
  - Active development and community

#### **Sentence Transformers (Embeddings)**
- **Rationale**: High-quality, fast, local embedding models
- **Benefits**: 
  - No API calls required
  - Excellent semantic search performance
  - Multiple model options (all-MiniLM-L6-v2, etc.)
  - Easy to swap models

#### **LangChain (LLM Framework)**
- **Rationale**: Mature framework for LLM applications, excellent RAG support
- **Benefits**:
  - Proven RAG patterns
  - Multiple LLM provider support
  - Active development and community
  - Future-proofed for LangChain 1.0+

#### **Ollama (Local LLM)**
- **Rationale**: Easy-to-use local LLM runner, privacy-first
- **Benefits**:
  - No data leaves your machine
  - Multiple model support
  - Simple setup and management
  - Active development

### Content Extraction Technologies

#### **readability-lxml**
- **Rationale**: Excellent article content extraction, used by major platforms
- **Benefits**: Robust HTML parsing, handles complex layouts, fallback mechanisms

#### **yt-dlp**
- **Rationale**: Most comprehensive video metadata extraction
- **Benefits**: Supports multiple platforms, rich metadata, active maintenance

#### **BeautifulSoup**
- **Rationale**: Fallback HTML parsing when readability fails
- **Benefits**: Robust, handles malformed HTML, extensive documentation

### Development and Testing

#### **pytest**
- **Rationale**: Modern, feature-rich testing framework
- **Benefits**: Fixtures, parametrization, excellent reporting, plugin ecosystem

#### **uv (Package Management)**
- **Rationale**: Fast, modern Python package manager
- **Benefits**: Faster than pip, better dependency resolution, virtual environment management

#### **requests**
- **Rationale**: Simple, reliable HTTP library
- **Benefits**: Excellent documentation, wide adoption, good error handling

### Security Technologies

#### **Input Validation**
- **Custom validation functions**: URL and file path validation
- **shlex**: Shell command escaping
- **urllib.parse**: URL parsing and validation

#### **File Operations**
- **tempfile**: Secure temporary file creation
- **contextlib**: Context managers for resource cleanup
- **os.path**: Safe path operations

### Alternative Technologies Considered

#### **Vector Databases**
- **Pinecone**: Rejected due to cloud dependency and privacy concerns
- **Weaviate**: Rejected due to complexity and external dependencies
- **Qdrant**: Considered but ChromaDB better suited for local-first approach

#### **Embedding Models**
- **OpenAI Embeddings**: Rejected due to API dependency and privacy concerns
- **Cohere**: Rejected due to API dependency
- **Hugging Face Inference API**: Rejected due to API dependency

#### **LLM Providers**
- **OpenAI GPT**: Rejected due to privacy concerns and API dependency
- **Anthropic Claude**: Rejected due to privacy concerns and API dependency
- **Local models via Hugging Face**: Considered but Ollama provides better UX

#### **Content Extraction**
- **newspaper3k**: Considered but readability-lxml more robust
- **trafilatura**: Considered but readability-lxml more widely adopted
- **youtube-dl**: Rejected in favor of yt-dlp (more active development)

### Performance Considerations

#### **Embedding Performance**
- **Batch processing**: Efficient handling of large document sets
- **Model selection**: all-MiniLM-L6-v2 provides good speed/quality balance
- **Caching**: ChromaDB provides efficient similarity search

#### **Content Extraction Performance**
- **Parallel processing**: Future enhancement for multiple URLs
- **Caching**: requests-cache for network requests
- **Timeout handling**: Prevents hanging on slow responses

#### **Memory Management**
- **Streaming**: Large datasets processed in batches
- **Cleanup**: Proper resource cleanup in all components
- **Garbage collection**: Explicit cleanup in vector store operations

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

### **Limit Number of URLs Processed**
You can limit the number of distinct URLs processed using the `--url-limit` option. This is useful for testing or when you want to process only a subset of your history:

```sh
# Process only the first 10 URLs from your history
uv run python -m historyhounder.cli extract --url-limit 10 --with-content

# Process only the first 5 URLs and embed them
uv run python -m historyhounder.cli extract --url-limit 5 --with-content --embed

# Process only the first 3 URLs from the last 30 days
uv run python -m historyhounder.cli extract --days 30 --url-limit 3 --with-content
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

To run security tests specifically:
```sh
uv run pytest tests/test_security.py -v
```

The integration tests use real, public URLs (externalized in `tests/real_world_urls.txt`) to ensure the pipeline works as a real user would experience it. No mocking is used in integration tests. YouTube extraction is powered by yt-dlp and the tests are robust to metadata field variations.

### Test Coverage
The test suite provides comprehensive coverage including:

- **Unit Tests**: Individual component testing with proper mocking
- **Integration Tests**: End-to-end pipeline testing with real data
- **Security Tests**: Input validation, path traversal, command injection, error handling
- **Edge Case Tests**: Error handling, malformed input, empty results
- **CLI Tests**: Argument parsing, error messages, malformed input
- **Error Handling Tests**: Database failures, network timeouts, corrupted data
- **Real-world Scenarios**: Using actual public URLs and content

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
  pipeline.py           # Main orchestration logic
  utils.py              # Utility functions
  ...
tests/                  # All tests (pytest, including integration)
  test_security.py      # Security-focused tests
  real_world_urls.txt   # Real URLs for integration testing
SECURITY.md             # Security guidelines and best practices
requirements.txt         # All dependencies
pytest.ini               # Pytest config (warning filters)
README.md                # This file
```

---

## Security

HistoryHounder implements comprehensive security measures:

- **Input Validation**: All user inputs are validated and sanitized
- **Path Security**: File operations restricted to safe directories
- **Subprocess Security**: URL validation prevents command injection
- **Error Handling**: Sensitive information removed from error messages
- **Security Testing**: Automated tests for all security measures

See `SECURITY.md` for detailed security guidelines and best practices.

---

## Notes
- All commands should be run with `uv run ...` for correct environment isolation.
- The tool is modular and can be extended to support more LLMs, embedders, or browsers.
- For best results, keep your browser closed while extracting history (to ensure the latest data is flushed to disk).
- The test suite is robust and covers both unit and end-to-end integration scenarios, including real-world and edge-case metadata handling.
- **LangChain integration uses the new split-out packages (`langchain-huggingface`, `langchain-chroma`, `langchain-ollama`) and is future-proofed for LangChain 1.0+.**
- **Comprehensive error handling and edge case testing ensures reliability in production environments.**
- **Security is a first-class concern with automated testing and validation.**

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