# Proposal: Worker CLI Ingestion Pipeline (PDF-first vertical slice)

Wire the `src/worker/` stub into a working ingestion pipeline that loads a source, chunks it, embeds it, and stores it in pgvector — driven by a CLI that reads a task-list file. Ship PDF end-to-end first; YouTube and Web are mechanical follow-up slices on the same pattern.

## Why (problem statement)

The vector store cannot be populated today. `src/worker/cli.py` is a stub that only prints `"Ingesting from: {source}"` — there is no routing, no chunking, no embedding, no storage. The three loaders (`pdf`, `youtube`, `web`) each work in isolation and return `list[Document]`, but nothing strings them through to `Container.vector_store`. The chunking splitter is documented (ADR-005) but never wired (`docs/architecture.md:87`). Until this pipeline exists, the planned RAG chain in `src/web/` has no data to retrieve.

The leverage here is NOT infrastructure (pgvector + the `recipes` collection already exist and `langchain-postgres` auto-manages its schema). The leverage is two foundational contracts that every future source and the future retrieval layer will depend on:
1. A **normalized document metadata contract** across source types.
2. An **idempotent re-ingest** mechanism so re-running a task does not duplicate chunks.

## What changes (scope)

### In scope
1. **Document metadata contract** (Phase 0 / foundation) — a normalized metadata dict attached to every `Document` before chunking, identical in shape across all source types.
2. **Transform + store stage** — a new `src/worker/pipeline.py` module: `chunk (RecursiveCharacterTextSplitter, ADR-005 library defaults) → embed + store via Container.vector_store.add_documents()`, with idempotent dedup.
3. **CLI task-list runner** — `cli.py` reads a YAML/JSON task-list file, routes each entry by `type` to its loader, runs the pipeline per task, and continues-and-reports on per-task failure.
4. **Source-type → loader routing** — a small factory mapping `type` to the existing loader function.
5. **PDF slice end-to-end** — the first source fully wired (load → contract → chunk → embed → store) plus the first Testcontainers integration test, establishing the pattern.
6. **Explicit `distance_strategy="cosine"` on PGVector** — small in-scope hardening (see Decision 4).
7. **Doc update** — `docs/architecture.md` ingestion section to reflect the implemented pipeline.

### Non-goals (explicitly out of scope)
- **YouTube and Web slices** — mechanical follow-ups; this change ships PDF only. Routing is built so they drop in, but they are NOT implemented or tested here.
- **Retrieval / RAG chain** (`src/web/`) — separate future change. This change only writes to the store; it does not read.
- **Chunking tuning** — `chunk_size`/`chunk_overlap` stay at library defaults per ADR-005 and CLAUDE.md. No new config fields.
- **Custom DB schema / Alembic migrations** — `langchain-postgres` owns the schema; the sqlalchemy-alembic skill's migration-safety rules do NOT apply here. No hand-written tables.
- **Backfilling metadata** onto rows from prior ingests — there are none; greenfield store.
- **Concurrency / parallel ingestion / scheduling** — tasks run sequentially. No daemon, no queue.

## Approach

### Pipeline stages (one pipeline, sliced by source type)

```
task-list file → [per entry] → router(type) → loader(source) → list[Document]
   → enrich metadata (contract) → chunk (RecursiveCharacterTextSplitter, defaults)
   → dedup check → Container.vector_store.add_documents(chunks, ids=...)
   → report
```

### Module layout

| Module | Responsibility |
|--------|----------------|
| `src/worker/cli.py` | Parse args, read + validate task-list file, drive the run, aggregate the report. No domain logic. |
| `src/worker/router.py` (new) | `loader_for(type) -> Callable[[str], list[Document]]`. Maps `type` string → existing loader function. Raises on unknown type. |
| `src/worker/pipeline.py` (new) | `ingest_documents(container, docs, base_metadata) -> IngestResult`: enrich metadata → chunk → dedup → store. Consumes the injected `Container`; never builds its own services. |
| `src/worker/metadata.py` (new) | Builds the normalized metadata dict and computes `content_hash`. Pure, easily unit-tested. |
| `src/worker/loaders/*.py` | Unchanged. |

The pipeline receives a `Container` argument so tests inject `Container(Settings(...))` with a Testcontainers DB URL. No bypassing DI.

### Decision 1 — Task-list file schema (YAML, JSON also accepted)

```yaml
tasks:
  - type: pdf            # required: pdf | youtube | web
    source: ./recipes/risotto.pdf   # required: path or URL
    metadata:            # optional: extra fields merged into the contract
      title: "Classic Risotto"
```

- `type` is **required and explicit** (not auto-detected). Auto-detection by extension/URL is brittle (a `.pdf` served over HTTP, ambiguous URLs) and hides intent; an explicit `type` keeps routing deterministic and the file self-documenting. Auto-detection can be a later convenience, not a foundation.
- `source` is required: a local path for `pdf`, a URL for `youtube`/`web`.
- `metadata` is optional and shallow-merged over the loader-derived contract (user override wins for `title`, etc.).
- File format detected by extension (`.yaml`/`.yml` vs `.json`); both parse to the same structure. CLI invocation becomes `ingest --tasks tasks.yaml`. The legacy `--source` single-shot flag MAY be kept as sugar (wraps one task) — decided in spec.

### Decision 2 — Metadata contract and `content_hash`

Normalized fields attached to every `Document.metadata` (stored as JSONB by langchain-postgres):

| Field | Type | Source |
|-------|------|--------|
| `source_url` | str | The task `source` (path or URL), normalized. |
| `source_type` | str | The task `type` (`pdf`/`youtube`/`web`). |
| `title` | str | Task `metadata.title` if given, else loader-derived, else filename/URL fallback. |
| `content_hash` | str | SHA-256 of the **normalized raw concatenated source content**, computed once per source before chunking. |
| `chunk_index` | int | Position of the chunk within the source (0-based), assigned after splitting. |

**`content_hash` is computed at the SOURCE level, not per chunk.** Rationale: dedup must decide "have I already ingested THIS source?" cheaply, before doing expensive chunking/embedding. A per-source hash lets us skip the whole task. A per-chunk hash would only dedup individual chunks (more granular but pointless here — chunks of an unchanged source are deterministic anyway) and still requires re-running the splitter. Source-level is the cheaper level that still guarantees no duplicate chunks. `chunk_index` is carried separately for future citation/ordering, not for dedup.

### Decision 3 — Idempotent SKIP mechanism

**Recommended primary: query-before-write on `content_hash`.**
Before storing, query the existing `recipes` collection for any chunk whose `cmetadata->>'content_hash'` equals the source's hash. If a match exists, SKIP the entire task (report `skipped`); otherwise proceed to chunk/embed/store.

- langchain-postgres exposes metadata filtering on similarity search and stores `cmetadata` as JSONB, so a metadata-filter existence check is feasible. The spec will pin the exact query path (PGVector filter API vs. a direct SQLAlchemy `SELECT 1 ... WHERE cmetadata->>'content_hash' = :h LIMIT 1` via `Container.engine`, which is the most explicit and testable).
- **Limitation (carry to spec):** the check + store is not atomic — two concurrent runs of the same source could both pass the check and double-write. We run tasks sequentially and document this as a non-concurrent-tooling assumption. A stronger guarantee (deterministic chunk IDs derived from `content_hash + chunk_index` passed to `add_documents(ids=...)`, making re-writes idempotent upserts) is noted as a hardening option the spec may adopt instead of, or alongside, the query check. The query approach is recommended first because it also lets us cheaply SKIP before embedding (saves API cost), which the ID-upsert approach alone does not.

### Decision 4 — Explicit `distance_strategy="cosine"`

`docs/architecture.md:106` and the RAG plan assume cosine, but `container.py` constructs `PGVector(...)` without passing `distance_strategy`, relying on the library default. **Recommend setting it explicitly** (`PGVector(..., distance_strategy="cosine")` / the `DistanceStrategy.COSINE` enum) in this change. Rationale: it is a one-line hardening that removes a silent dependency on a library default, makes the architecture doc's claim true in code, and is naturally in-scope because this is the first change that actually populates and will be measured against that store. Low risk, high clarity. (If the spec finds the default already is cosine, this remains worth pinning explicitly to prevent future drift.)

### Decision 5 — Error handling: continue-and-report

A failing task (bad path, loader error, network failure on future sources) must NOT abort the whole run. The CLI accumulates per-task outcomes (`stored` / `skipped` / `failed` with reason) and prints a summary at the end, exiting non-zero if any task failed so automation can detect partial failure. This keeps a 50-item task list from dying on item 3.

## Impact

**New files:**
- `src/worker/pipeline.py`, `src/worker/router.py`, `src/worker/metadata.py`
- `tests/unit/worker/test_pipeline.py`, `test_router.py`, `test_metadata.py` (mock loaders/splitter/vector_store)
- `tests/integration/test_ingest_pdf.py` (Testcontainers Postgres+pgvector, real `Container(Settings(...))`)
- `tests/integration/conftest.py` (new Testcontainers fixtures — first of their kind)
- An example task-list fixture (e.g. `tests/fixtures/tasks.yaml`) + a sample PDF fixture.

**Modified files:**
- `src/worker/cli.py` — task-list parsing, routing, run loop, report. `--tasks` arg.
- `src/core/container.py` — add explicit `distance_strategy="cosine"` to `PGVector`.
- `tests/unit/worker/test_cli.py` — replace stub-print assertions with task-list/run/report behavior.
- `docs/architecture.md` — ingestion section: pipeline implemented, metadata contract, dedup, task-list format.

**Dependencies:** YAML parsing needs a parser. If `pyyaml` is not already a dependency, adding it requires user approval per CLAUDE.md — flagged as an open item. JSON-only is the zero-dependency fallback.

## Risks & open questions
- **YAML dependency**: confirm whether `pyyaml` may be added, or restrict task-list to JSON only. (Blocking for the YAML half of Decision 1.)
- **PGVector existence-check API**: exact supported path for a metadata-only existence query (filter API vs. raw SQLAlchemy via `Container.engine`) to be pinned in spec; affects how dedup is implemented and tested.
- **Atomicity of dedup**: check-then-write is not atomic; acceptable under the sequential, manual-CLI assumption — documented, not solved here.
- **NVIDIA embeddings in integration tests**: embedding calls hit the NVIDIA API. The integration test either needs a test API key in CI or must stub the embeddings while keeping the real pgvector store (mock `Container.embeddings` only). Spec must decide what "real" means for the E2E test.
- **`content_hash` normalization**: exact normalization of raw content before hashing (whitespace, encoding, page-join order for multi-page PDFs) must be deterministic and pinned in spec, or re-ingest SKIP becomes unreliable.
- Carried from exploration: ADR-005 fixes chunking to defaults — any recipe-specific tuning is a separate future discussion.

## First-slice boundary (PR #1)

**In PR #1 (PDF end-to-end):**
- Metadata contract + `content_hash` (`metadata.py`)
- Router with PDF wired (youtube/web entries raise "not yet implemented")
- Pipeline (chunk → dedup → store)
- CLI task-list runner + continue-and-report
- Explicit cosine distance strategy
- Full unit coverage + first Testcontainers integration test for PDF
- `docs/architecture.md` update

**Deferred (follow-up slices, same pattern):**
- YouTube slice (wire loader into router + its integration test)
- Web slice (wire loader into router + its integration test)
- Retrieval / RAG chain (separate change in `src/web/`)
