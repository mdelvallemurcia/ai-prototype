# Tasks: Worker CLI Ingestion Pipeline (PDF-first)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~650-750 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 â†’ PR 2 â†’ PR 3 |
| Delivery strategy | ask-on-risk (resolved â†’ chained PRs) |
| Chain strategy | stacked-to-main |

Decision needed before apply: Resolved â€” see decisions (id 455)
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Pure helpers: `tasks.py` (parser) + `metadata.py` (hash/contract) + container `distance_strategy` + pyyaml dep, fully tested | PR 1 | ~220 lines incl. tests; no I/O; foundation for rest |
| 2 | `router.py` + `pipeline.py` orchestration (loadâ†’enrichâ†’dedupâ†’chunkâ†’store) with unit tests (mocked loader/embeddings/dedup) | PR 2 | ~250 lines incl. tests; depends on PR 1 |
| 3 | `cli.py` `--tasks` runner + Testcontainers integration fixture/test + docs update | PR 3 | ~200 lines incl. tests/docs; depends on PR 2 |

## Phase 1: Setup & Dependencies

- [x] 1.1 Add `pyyaml>=6.0` to `[project].dependencies` in `pyproject.toml`
- [x] 1.2 Run `uv sync` to install the new dependency

## Phase 2: Task-list Parsing (`src/worker/tasks.py`)

- [x] 2.1 RED â€” write `tests/unit/worker/test_tasks.py::test_load_task_file_valid_yaml_returns_tasks`
- [x] 2.2 RED â€” write `test_load_task_file_valid_json_returns_tasks`
- [x] 2.3 RED â€” write `test_load_task_file_missing_file_raises_error`, `test_load_task_file_malformed_content_raises_error`, `test_load_task_file_empty_list_returns_empty_list`, `test_load_task_file_missing_required_field_raises_error`, `test_load_task_file_unknown_type_raises_error`
- [x] 2.4 GREEN â€” create `src/worker/tasks.py`: `Task` frozen dataclass (`source_type`, `source`, `metadata`) and `load_task_file(path) -> list[Task]`, dispatch by extension (`.yaml/.yml` â†’ pyyaml, `.json` â†’ json), validate `type`/`source`/unknown-type/empty-list per spec req. 1
- [x] 2.5 REFACTOR â€” confirm all Phase 2 tests pass and clean up parsing helpers

## Phase 3: Metadata Contract & content_hash (`src/worker/metadata.py`)

- [x] 3.1 RED â€” write `tests/unit/worker/test_metadata.py::test_compute_content_hash_same_content_returns_same_hash` and `test_compute_content_hash_different_content_returns_different_hash` (pure, in-memory, no I/O)
- [x] 3.2 GREEN â€” implement `compute_content_hash(docs: list[Document]) -> str`: join `page_content` in loader order with `"\n"`, `.strip()`, UTF-8 encode, SHA-256 hexdigest
- [x] 3.3 RED â€” write `test_build_base_metadata_title_override_uses_task_metadata_title` and `test_build_base_metadata_no_override_falls_back_to_filename`
- [x] 3.4 GREEN â€” implement `build_base_metadata(task, docs) -> dict`: `source_url`, `source_type`, `title` (task override > loader-derived > `Path(source).stem`), `content_hash`
- [x] 3.5 RED â€” write `test_enrich_documents_assigns_sequential_chunk_index_and_constant_fields`
- [x] 3.6 GREEN â€” implement `enrich_documents(docs, base_metadata) -> list[Document]`: merge `{**doc.metadata, **base_metadata}` (reserved keys win, no clobber of loader-native keys) and assign 0-based `chunk_index` post-split
- [x] 3.7 REFACTOR â€” confirm Phase 3 tests pass and metadata helpers stay pure/I/O-free

## Phase 4: Source-type Routing (`src/worker/router.py`)

- [x] 4.1 RED â€” write `tests/unit/worker/test_router.py::test_loader_for_pdf_returns_pdf_loader`, `test_loader_for_youtube_raises_not_implemented_error`, `test_loader_for_web_raises_not_implemented_error`, `test_loader_for_unknown_type_raises_value_error`
- [x] 4.2 GREEN â€” implement `loader_for(source_type: str) -> Callable[[str], list[Document]]`: explicit factory; `pdf` â†’ existing PDF loader; `youtube`/`web` raise `NotImplementedError`; unknown raises `ValueError`

## Phase 5: Pipeline Orchestration & Dedup/SKIP (`src/worker/pipeline.py`)

- [x] 5.1 RED â€” write `tests/unit/worker/test_pipeline.py::test_ingest_task_existing_content_hash_skips_without_storing` (+ `_content_hash_exists` true/false/bound-param tests)
- [x] 5.2 GREEN â€” implement dedup check `_content_hash_exists(container, content_hash) -> bool` via raw parameterized SQL `text("SELECT 1 FROM langchain_pg_embedding WHERE cmetadata->>'content_hash' = :content_hash LIMIT 1")` using `Container.engine.connect()` + bound params (verified table/column names against installed langchain-postgres 0.0.17 source)
- [x] 5.3 RED â€” write `test_ingest_task_new_source_stores_chunks_with_full_metadata`
- [x] 5.4 RED â€” write `test_ingest_task_new_source_uses_per_source_content_hash`
- [x] 5.5 GREEN â€” implement `IngestResult` dataclass (`status`, `source`, `chunks`, `reason`) and `ingest_task(container, task) -> IngestResult`: load via `loader_for` â†’ `build_base_metadata` (per-source content_hash) â†’ dedup check â†’ SKIP or split (`RecursiveCharacterTextSplitter()` library defaults, ADR-005) â†’ `enrich_documents` re-attaches `chunk_index` â†’ `container.vector_store.add_documents()` â†’ `stored`
- [x] 5.6 REFACTOR â€” confirm Phase 5 tests pass; mocks cover loader, vector_store/embeddings, and dedup query via mocked `container.engine.connect()` (no real DB/network)

## Phase 6: Container `distance_strategy`

- [x] 6.1 RED â€” write/extend `tests/unit/core/test_container.py::test_vector_store_uses_cosine_distance_strategy`
- [x] 6.2 GREEN â€” add `distance_strategy="cosine"` to the `PGVector(...)` construction in `src/core/container.py` `vector_store` lazy property

## Phase 7: CLI Runner â€” `--tasks` (`src/worker/cli.py`)

- [x] 7.1 RED â€” write `tests/unit/worker/test_cli.py::test_main_tasks_flag_runs_all_tasks_and_prints_summary` (mock pipeline; assert summary contains stored/skipped/failed counts)
- [x] 7.2 RED â€” write `test_main_continues_after_task_failure_and_records_reason` and `test_main_exits_zero_when_no_failures`, `test_main_exits_nonzero_when_any_task_failed`
- [x] 7.3 GREEN â€” rewrite `src/worker/cli.py`: replace `--source` with `--tasks <file>`; load tasks via `tasks.load_task_file`, route via `router.loader_for`, run via `pipeline.ingest_documents` inside try/except per task (continue-and-report), accumulate `IngestResult`s, print summary, exit 1 if any `failed` else 0
- [x] 7.4 REFACTOR â€” confirm `--source` flag fully removed and CLI tests pass

## Phase 8: Integration Test (Greenfield Testcontainers Fixture)

- [x] 8.1 Create `tests/integration/conftest.py`: session-scoped `pg_container` fixture (`pgvector/pgvector:pg17`, `CREATE EXTENSION vector`), `container` fixture wrapping `Container(Settings(db_url=tc_url))` with `_embeddings` overridden by deterministic `FakeEmbeddings` (hash-to-fixed-vector, no network)
- [x] 8.2 RED â€” write `tests/integration/worker/test_pdf_ingestion.py::test_ingest_pdf_task_persists_chunks_with_full_metadata` (real pgvector + mocked embeddings, asserts `source_url/source_type/title/chunk_index/content_hash` present in `langchain_pg_embedding`)
- [x] 8.3 RED â€” write `test_ingest_pdf_task_rerun_same_source_skips_without_new_rows`
- [x] 8.4 (BLOCKED — see notes below) GREEN â€” wire fixtures + sample PDF asset until both integration tests pass against real Testcontainers pgvector

### Phase 8 — BLOCKER NOTE (developer action required)

Tasks 8.1-8.3 were written in full (greenfield Testcontainers fixture in
`tests/integration/conftest.py` + 2 E2E tests in `tests/integration/test_ingest_pdf_e2e.py`,
using a real pgvector store and `DeterministicFakeEmbedding` for embeddings).
Task 8.4 ("wire fixtures until tests pass") is BLOCKED for two reasons:

1. The `testcontainers` package is NOT an installed dependency (absent from
   `pyproject.toml` `[dependency-groups].dev` and from `uv.lock`). Per CLAUDE.md
   ("Never add new libraries or dependencies without asking first") it was NOT
   added without developer approval.
2. No Docker daemon was reachable in the apply environment (`docker ps` failed
   to connect to the Docker API).

ACTION NEEDED: developer approves adding `testcontainers[postgres]` to the dev
dependency group, runs `uv sync`, ensures Docker Desktop/daemon is running, then
runs `uv run pytest tests/integration/` to confirm both E2E tests pass against a
real pgvector container (it could not be executed in this apply environment).

## Phase 9: Documentation

- [x] 9.1 Update `docs/architecture.md`: replace worker-stub status notes with the implemented PDF-first ingestion pipeline description (loadâ†’enrichâ†’dedupâ†’chunkâ†’store), reference ADR-005 for chunking defaults
- [x] 9.2 Confirm `uv run pytest --no-cov` and `uv run pytest` (80% coverage) pass, then `uv run ruff check .` and `uv run ruff format .`

## Deferred (explicitly out of scope for this change)

- [ ] D.1 (deferred) Implement YouTube loader wiring in `router.py` (replace `NotImplementedError` with real loader call) â€” separate change
- [ ] D.2 (deferred) Implement Web loader wiring in `router.py` (replace `NotImplementedError` with real loader call) â€” separate change
- [ ] D.3 (deferred) Decide and implement replace/delete policy for changed-content re-ingest (currently additive-only by design, documented as interim behavior) â€” separate change

## Review Workload Forecast

Estimated changed lines: 650-750
400-line budget risk: High
Chained PRs recommended: Yes
Decision needed before apply: Yes

Rationale: This change creates 4 new modules (`tasks.py`, `metadata.py`, `router.py`, `pipeline.py`), rewrites `cli.py`, modifies `container.py`, adds a greenfield Testcontainers integration fixture, and requires test-first coverage (RED+GREEN pairs) for ~9 unit-test files plus 2 integration tests plus docs â€” comfortably exceeding the 400-line budget as a single PR. Proposed split:
- PR 1 (~220 lines): `tasks.py` + `metadata.py` + `pyproject.toml`/`distance_strategy` + their unit tests â€” pure, no dependencies on routing/pipeline.
- PR 2 (~250 lines): `router.py` + `pipeline.py` + unit tests (mocked loader/embeddings/dedup) â€” depends on PR 1's metadata contract.
- PR 3 (~200 lines): `cli.py` rewrite + Testcontainers conftest + integration tests + docs update â€” depends on PR 2's pipeline/router being complete.


