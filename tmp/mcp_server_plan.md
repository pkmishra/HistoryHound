# Model Context Protocol (MCP) Server for Browser History – Feature Plan

## 1. Overview of Current State

* HistoryHounder has a FastAPI server (`server.py`) that provides REST API endpoints for semantic search and Q&A functionality.
* Browser history extraction logic exists in `extract_chrome_history.py` and `history_extractor.py` but is not exposed as an MCP server.
* No MCP (Model Context Protocol) server implementation exists - this is a new feature that will allow AI models to directly access browser history data through the standardized MCP protocol.
* Current architecture focuses on semantic search and Q&A rather than raw data access for AI model context.
* The project follows a modular structure with separate modules like `llm/` for specific functionality.

## 2. Overview of Final State

A new **Model Context Protocol (MCP) Server** will:

* Implement the MCP specification to provide browser history data as context for AI models.
* Expose browser history through standardized MCP tools (list_tools, call_tool, etc.).
* Support multiple browsers (Chrome, Firefox, Edge, Safari) with cross-platform compatibility.
* Provide filtering capabilities (date ranges, domains, visit counts) via MCP tool parameters.
* Run as a standalone server that AI models can connect to for context retrieval.
* Include comprehensive unit and integration tests following MCP specification.
* Support both synchronous and asynchronous tool calls as per MCP standards.
* Follow the existing modular architecture pattern with a dedicated `mcp/` module.

## 3. Files to Change (Text Description)

| Area | File(s) | Changes |
|------|---------|---------|
| MCP Module | `historyhounder/mcp/__init__.py` | Initialize the MCP module with proper exports. |
| MCP Server Core | `historyhounder/mcp/server.py` | New MCP server implementing the protocol with tools for browser history access. |
| MCP Tools | `historyhounder/mcp/tools.py` | MCP tool definitions for history retrieval, filtering, and statistics. |
| MCP Models | `historyhounder/mcp/models.py` | Pydantic models for MCP request/response structures. |
| Cross-Platform Browser Support | `historyhounder/mcp/browser_detection.py` | Cross-platform browser detection and path resolution. |
| CLI Integration | `historyhounder/cli.py` | Add `mcp-server` command to start the MCP server. |
| Configuration | `historyhounder/mcp/config.py` | MCP server configuration with cross-platform support. |
| Tests - Unit | `tests/test_mcp_server.py` | Unit tests for MCP server functionality and tool implementations. |
| Tests - Integration | `tests/test_mcp_integration.py` | Integration tests with real browser history data and MCP client simulation. |
| Tests - Cross-Platform | `tests/test_mcp_cross_platform.py` | Tests for browser detection across different operating systems. |
| Dependencies | `pyproject.toml` | Add MCP-related dependencies (mcp, asyncio, websockets). |
| Documentation | `README.md` | Add MCP server documentation and usage examples. |

## 4. Checklist of Tasks

- [ ] **MCP Module Structure**
  - [ ] Create `historyhounder/mcp/` directory following the `llm/` module pattern.
  - [ ] Create `__init__.py` with proper module exports.
  - [ ] Organize MCP components into separate files within the module.
- [ ] **Cross-Platform Browser Support**
  - [ ] Create `browser_detection.py` for cross-platform browser path detection.
  - [ ] Support Windows, macOS, and Linux browser paths.
  - [ ] Implement fallback mechanisms for different browser installations.
  - [ ] Add browser-specific history file format handling.
- [ ] **MCP Server Implementation**
  - [ ] Create `mcp/server.py` implementing the MCP protocol.
  - [ ] Implement `initialize` method for server setup.
  - [ ] Implement `list_tools` method to expose available tools.
  - [ ] Implement `call_tool` method for executing history retrieval tools.
  - [ ] Add proper error handling and logging for MCP operations.
- [ ] **MCP Tools Development**
  - [ ] Create `mcp/tools.py` with tool definitions.
  - [ ] Implement `get_browser_history` tool with filtering parameters.
  - [ ] Implement `get_history_statistics` tool for analytics.
  - [ ] Implement `list_supported_browsers` tool for cross-platform browser detection.
  - [ ] Add parameter validation and error handling for all tools.
- [ ] **MCP Models**
  - [ ] Create `mcp/models.py` with Pydantic models for MCP structures.
  - [ ] Define request/response models for tool calls.
  - [ ] Define tool parameter schemas with proper validation.
- [ ] **Configuration Management**
  - [ ] Create `mcp/config.py` with cross-platform configuration.
  - [ ] Add environment variable support for MCP server settings.
  - [ ] Implement platform-specific default paths and settings.
- [ ] **CLI Integration**
  - [ ] Add `mcp-server` command to `cli.py`.
  - [ ] Implement server startup with proper configuration.
- [ ] **Unit Tests**
  - [ ] Write `test_mcp_server.py` with comprehensive test coverage.
  - [ ] Test MCP protocol compliance (initialize, list_tools, call_tool).
  - [ ] Test tool parameter validation and error handling.
  - [ ] Test browser history extraction through MCP tools.
- [ ] **Integration Tests**
  - [ ] Write `test_mcp_integration.py` with real browser history data.
  - [ ] Test MCP client-server communication.
  - [ ] Test tool execution with various parameter combinations.
  - [ ] Test error scenarios and edge cases.
- [ ] **Cross-Platform Tests**
  - [ ] Write `test_mcp_cross_platform.py` for browser detection tests.
  - [ ] Test browser path resolution on different operating systems.
  - [ ] Test fallback mechanisms for missing browsers.
  - [ ] Test history file format compatibility across platforms.
- [ ] **Dependencies**
  - [ ] Add MCP-related dependencies to `pyproject.toml`.
  - [ ] Ensure compatibility with existing HistoryHounder dependencies.
  - [ ] Add cross-platform path handling dependencies if needed.
- [ ] **Documentation**
  - [ ] Update `README.md` with MCP server documentation.
  - [ ] Add usage examples for AI model integration.
  - [ ] Document MCP tool parameters and capabilities.
  - [ ] Document cross-platform browser support and requirements.

---

This plan creates a proper Model Context Protocol server that allows AI models to access browser history data through the standardized MCP specification, with comprehensive testing and documentation. The implementation follows the existing modular architecture pattern and ensures cross-platform compatibility for browser history access.