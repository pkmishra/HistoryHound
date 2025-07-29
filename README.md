# HistoryHounder

Chat with your browser history using AI.

## Python Version Management

This project uses **Python 3.12** and **uv** for dependency management. Follow these steps:

### Initial Setup

1. **Install Python 3.12 with uv**:
   ```bash
   uv python install 3.12
   ```

2. **Pin the project to Python 3.12**:
   ```bash
   uv python pin 3.12
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

### Running the Project

Always use `uv run` for all Python operations:

```bash
# Run tests
uv run pytest

# Start the server
uv run python -m historyhounder.server

# Run any Python script
uv run python your_script.py
```

## Features

- **Advanced Q&A System**: Uses state-of-the-art LLM technology with prompt engineering for different question types (statistical, temporal, semantic, comparative, factual)
- **Intelligent Context Optimization**: Dynamically adjusts context size and filtering based on question type
- **Source Relevance Filtering**: Post-processes results to ensure only highly relevant sources are displayed
- **Model Caching**: Optimized to prevent redundant model downloads and loading
- **Web Interface**: Easy-to-use browser extension for querying your history
- **REST API**: FastAPI backend following OpenAPI specification
- **Comprehensive Testing**: Full test suite with integration tests (no mocking approach)

## Architecture

### Core Components

1. **History Extraction** (`extract_chrome_history.py`): Extracts browsing history from Chrome
2. **Content Fetching** (`content_fetcher.py`): Retrieves and processes web page content
3. **Vector Store** (`vector_store.py`): ChromaDB-based storage for embeddings
4. **Search Engine** (`search.py`): Advanced Q&A with context optimization and source filtering
5. **LLM Integration** (`llm/ollama_qa.py`): Ollama-based question answering with structured output
6. **Web Server** (`server.py`): FastAPI backend
7. **Browser Extension** (`extension/`): Chrome extension for user interface

### Data Flow

1. Browser history → Content fetching → Text processing
2. Text → Embeddings → Vector storage (ChromaDB)  
3. User query → Context optimization → LLM processing → Structured response
4. Response → Source filtering → User interface

## Development Philosophy

This project follows a **comprehensive testing and integration** approach:

- **Integration Tests**: Tests run without mocking when possible for real-world validation
- **Quality Assurance**: All tests must pass (123/123) before committing
- **Performance Focus**: Model caching, context optimization, and efficient vector operations
- **Security First**: Input validation, path sanitization, and comprehensive error handling

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

### **Backend Server for Browser Extension**
Start the backend server to enable browser extension integration:
```sh
# Start server on default port (8080)
uv run python -m historyhounder.cli server

# Start server on custom port
uv run python -m historyhounder.cli server --port 9000

# Start server on all interfaces (for remote access)
uv run python -m historyhounder.cli server --host 0.0.0.0 --port 8080

# Alternative: Run server directly
uv run python -m historyhounder.server --port 8080

# Configure Ollama model (default: llama3.2:latest)
HISTORYHOUNDER_OLLAMA_MODEL=llama3.2:latest uv run python -m historyhounder.server --port 8080
```

The server provides RESTful API endpoints for:
- **Health Check**: `GET /api/health`
- **Semantic Search**: `GET /api/search?q=query`
- **AI Q&A**: `POST /api/qa`
- **History Processing**: `POST /api/process-history`
- **Statistics**: `GET /api/stats`

**API Documentation**:
- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`
- **OpenAPI JSON**: `http://localhost:8080/openapi.json`

### **Ollama Model Configuration**

The server uses Ollama for AI Q&A functionality. You can configure the model using environment variables:

```bash
# Use default model (llama3.2:latest)
uv run python -m historyhounder.server --port 8080

# Use a specific model
HISTORYHOUNDER_OLLAMA_MODEL=llama3.2:latest uv run python -m historyhounder.server --port 8080

# Use a different model
HISTORYHOUNDER_OLLAMA_MODEL=llama3.1:latest uv run python -m historyhounder.server --port 8080

# Use a custom model
HISTORYHOUNDER_OLLAMA_MODEL=my-custom-model uv run python -m historyhounder.server --port 8080
```

**Available Models**:
- `llama3.2:latest` (default) - Latest Llama 3.2 model
- `llama3.1:latest` - Llama 3.1 model
- `llama3:latest` - Llama 3 model
- Any other model available in your Ollama installation

**Check Current Model**:
```bash
curl http://localhost:8080/api/health
```

**Get Model Information**:
```bash
curl http://localhost:8080/api/ollama/model
```

### **Browser Extension Integration**
The backend server enables the HistoryHounder browser extension to:
- Perform semantic search on your browser history
- Ask AI questions about your browsing patterns
- Process and sync history data
- Access enhanced features through the extension UI

- The browser extension now ensures that only the required fields (`id`, `url`, `title`, `lastVisitTime`, `visitCount`) are sent to the backend when syncing history. This prevents 422 Unprocessable Entity errors from the FastAPI backend.

### Troubleshooting

- **422 Unprocessable Entity Error on /api/process-history**: This error means the request body did not match the expected schema. Make sure the extension is up to date and only sends the required fields with the correct types. See the extension's README for more details.

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
