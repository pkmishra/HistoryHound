# HistoryHounder – Comprehensive Improvement Plan

## 1. Overview of Current State

HistoryHounder is a fully-functional, locally-running AI system that lets users query their browser history. Key strengths include a privacy-first architecture, robust FastAPI backend, Chrome extension, ChromaDB vector store, SentenceTransformer embeddings, and an extensive integration-test suite. However, several areas can be enhanced:

* Security: open CORS policy, no authentication / rate-limit, permissive error logs.
* Performance: synchronous content fetching, single-threaded embeddings, no async I/O.
* Architecture: tight coupling between modules, manual dependency wiring, duplicate logging / settings logic.
* Dependency management: `requirements.txt` in parallel with `pyproject.toml`; no hash-pinning.
* Dev-Experience: CLI uses argparse; Typer would simplify commands & auto-docs.
* Observability: minimal structured logging, no metrics.
* Extension UX: limited error feedback, no dark-mode styles.

## 2. Overview of Final State

The goal is to elevate HistoryHounder to production-grade quality:

* Hardened security (scoped CORS, optional API key auth, request rate-limiting).
* High-performance pipeline (async content fetch via `httpx`, batched embeddings, optional multiprocessing).
* Modular architecture with dependency-injection (providers for vector store, embedder, LLM).
* Single source of dependency truth – `pyproject.toml` with exact versions + `uv lock` hashes.
* Modern, ergonomic CLI built with Typer; auto-generates shell completions & help.
* Structured logging with `structlog` and OpenTelemetry metrics hooks.
* Improved extension UX (error banners, dark mode, link to API health page).
* Documentation updates reflecting new architecture & best practices.

## 3. Files to Change (Text Description)

| Area | File(s) | Changes |
|------|---------|---------|
| Security | `historyhounder/server.py` | 1) Replace custom CORS with `fastapi.middleware.cors.CORSMiddleware` configured via env-vars. 2) Add API-key header dependency + rate-limit middleware using `slowapi`. |
| Async Pipeline | `historyhounder/content_fetcher.py`, `pipeline.py` | Refactor to async functions, use `httpx.AsyncClient`, gather tasks; add `asyncio.Semaphore` for concurrency limit. |
| Embedding Batch | `embedder/__init__.py` | Ensure `SentenceTransformer.encode(batch, batch_size=… , convert_to_numpy=False)` batching; expose param in `get_embedder`. |
| Multiprocessing | `pipeline.py` | Optional `concurrent.futures.ProcessPoolExecutor` for CPU-bound embedding batches when running large datasets. |
| Dependency Injection | new `historyhounder/di.py` | Simple provider pattern returning configured instances (vector store, embedder, llm). |
| CLI | `historyhounder/cli.py` => Typer rewrite | Migrate argparse to Typer commands; add sub-command auto-docs. |
| Config | new `historyhounder/config.py` | Centralise env-var parsing & defaults. |
| Logging | all modules | Replace `logging` calls with `structlog`, add JSON formatter when `LOG_JSON=1`. |
| Metrics | `server.py` | Hook OpenTelemetry FastAPI instrumentation; expose `/metrics` for Prometheus. |
| Dependency Mgmt | `pyproject.toml`, delete `requirements.txt` | Pin versions & hashes; run `uv lock`. |
| Tests | `tests/…` | Add tests for new async pipeline, API-key auth, rate-limiting, CLI commands. |
| Extension | `extension/popup.js`, `extension/background.js`, `extension/popup.css` | Add error banner, dark-mode styles, handle 401/429 responses. |
| Docs | `README.md`, new `docs/architecture.md` | Update setup instructions, diagrams, and architecture description. |

## 4. Checklist of Tasks

- [ ] Implement central `config.py` with typed settings (pydantic-settings).
  - [ ] Migrate existing env-var reads to new config.
- [ ] Replace custom CORS with configurable CORS middleware.
- [ ] Add API-key auth dependency in FastAPI routes.
- [ ] Integrate `slowapi` for rate-limiting (per-IP & per-key).
- [ ] Switch to `structlog`; update all logging calls.
- [ ] Add OpenTelemetry FastAPI instrumentation and `/metrics` endpoint.
- [ ] Refactor `content_fetcher` to async `httpx`; update callers.
- [ ] Add batch embedding support using `SentenceTransformer.encode` with `batch_size`.
  - [ ] Make batch size configurable.
- [ ] Support optional multiprocessing for embeddings in `pipeline.py`.
- [ ] Create `di.py` for dependency injection; refactor modules to use it.
- [ ] Rewrite `cli.py` with Typer; parity with existing commands.
  - [ ] Auto-generate shell completion scripts.
- [ ] Consolidate dependencies: remove `requirements.txt`, update `pyproject.toml` with exact versions & hashes.
- [ ] Update tests:
  - [ ] Add async pipeline tests.
  - [ ] Add auth + rate-limit tests.
  - [ ] Add CLI command tests via `CliRunner`.
- [ ] Enhance extension UI:
  - [ ] Graceful error handling
  - [ ] Dark-mode CSS
  - [ ] Health-check status badge.
- [ ] Update documentation (README + new architecture doc).

---

This plan focuses on pragmatic, incremental improvements that strengthen security, performance, maintainability, and developer experience while respecting the project’s local-first philosophy.