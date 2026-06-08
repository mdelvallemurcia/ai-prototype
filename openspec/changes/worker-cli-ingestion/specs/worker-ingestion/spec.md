# Worker Ingestion Specification

## Purpose

Defines the manual CLI ingestion pipeline (`src/worker/`) that loads source content (PDF first; YouTube/Web deferred), normalizes metadata, chunks and embeds it, and stores it idempotently in pgvector via the DI `Container`.

## Requirements

### Requirement: Task-list parsing

The CLI MUST read a task-list file in YAML or JSON, validating structure before running any task. Each entry MUST contain `type` (one of `pdf`, `youtube`, `web`) and `source` (path or URL); `metadata` is OPTIONAL and shallow-merged into derived metadata. The CLI MUST fail fast with a clear error before processing any task if the file is missing, malformed, empty, or contains an entry with a missing required field or unknown `type`.

#### Scenario: Valid YAML task-list
- GIVEN a `tasks.yaml` file with `tasks: [{type: pdf, source: "recipes/cake.pdf"}]`
- WHEN the CLI runs `ingest --tasks tasks.yaml`
- THEN the file is parsed into one task entry and the run proceeds

#### Scenario: Valid JSON task-list
- GIVEN a `tasks.json` file with the equivalent JSON structure
- WHEN the CLI runs `ingest --tasks tasks.json`
- THEN the file is parsed identically to the YAML case

#### Scenario: Task-list file not found
- GIVEN a `--tasks` path that does not exist
- WHEN the CLI runs
- THEN it reports a file-not-found error and exits non-zero without attempting any ingestion

#### Scenario: Malformed file
- GIVEN a file with invalid YAML/JSON syntax
- WHEN the CLI parses it
- THEN it reports a parse error with the file path and exits non-zero before running any task

#### Scenario: Empty task list
- GIVEN a valid file with `tasks: []`
- WHEN the CLI runs
- THEN it reports "no tasks to run" and exits zero (not an error — nothing to do)

#### Scenario: Entry missing required field
- GIVEN a task entry missing `source`
- WHEN the CLI validates the list
- THEN it reports a validation error naming the entry index and missing field, and exits non-zero before running any task

#### Scenario: Unknown type value
- GIVEN a task entry with `type: csv`
- WHEN the CLI validates the list
- THEN it reports a validation error naming the entry and the unsupported type, and exits non-zero before running any task

### Requirement: Source-type routing

The router MUST map each task `type` to its loader via an explicit factory (no auto-detection). `pdf` MUST route to the existing PDF loader and run end-to-end. `youtube` and `web` are RECOGNIZED but UNSUPPORTED FOR NOW: the router MUST raise a clear "not implemented" error for these types, which the per-task error isolation layer reports as a failed task (not a crash).

#### Scenario: PDF type routes to PDF loader
- GIVEN a task with `type: pdf`
- WHEN the router resolves a loader for it
- THEN it returns the PDF loader callable and the pipeline runs against it

#### Scenario: YouTube/Web type recognized but deferred
- GIVEN a task with `type: youtube` or `type: web`
- WHEN the router resolves a loader for it
- THEN it raises a "not implemented for this slice" error, which is captured per-task (run continues with remaining tasks)

### Requirement: PDF end-to-end ingestion (load → chunk → embed → store)

For a `pdf` task, the system MUST load the document(s), enrich them with normalized metadata, chunk them with `RecursiveCharacterTextSplitter` (ADR-005 library defaults — no custom chunk size/overlap config), embed via `Container.embeddings`, and persist via `Container.vector_store.add_documents()`, with each stored chunk carrying the full normalized metadata contract.

#### Scenario: Happy path PDF ingest
- GIVEN a valid PDF task pointing to an existing readable PDF file
- WHEN the pipeline runs the task
- THEN the PDF is loaded, split into chunks using default `RecursiveCharacterTextSplitter` settings, embedded, and stored in the `recipes` collection
- AND each persisted chunk's metadata contains `source_url`, `source_type`, `title`, `chunk_index`, and `content_hash`

### Requirement: Normalized metadata contract

Every `Document` MUST be enriched with a normalized metadata dict, identical in shape across source types, BEFORE chunking, containing: `source_url` (str — original path/URL of the source), `source_type` (str — the task `type`), `title` (str — derived as: explicit task `metadata.title` override > loader-derived title > filename/URL fallback for PDF), `content_hash` (str — see content_hash requirement), and `chunk_index` (int, 0-based — assigned per chunk after splitting). Optional `metadata` from the task entry MUST be shallow-merged on top of derived fields, with task-supplied values taking precedence.

#### Scenario: PDF metadata derivation without override
- GIVEN a PDF task with no `metadata.title` override and source `recipes/chocolate-cake.pdf`
- WHEN metadata is built
- THEN `source_url` is the given path, `source_type` is `"pdf"`, and `title` falls back to the filename (`chocolate-cake.pdf` or its derived form)

#### Scenario: PDF metadata with task-level override
- GIVEN a PDF task with `metadata: {title: "Grandma's Cake"}`
- WHEN metadata is built
- THEN `title` is `"Grandma's Cake"`, overriding any loader-derived or filename-derived title

#### Scenario: chunk_index assigned per chunk
- GIVEN a source that splits into 3 chunks
- WHEN chunks are persisted
- THEN they carry `chunk_index` values `0`, `1`, `2` respectively, all sharing the same `source_url`, `source_type`, `title`, and `content_hash`

### Requirement: Idempotent re-ingest via content_hash

Before chunking and embedding, the pipeline MUST compute `content_hash` once per source (SHA-256 of the deterministically normalized raw concatenated source content) and query the `recipes` collection for any existing chunk whose `cmetadata->>'content_hash'` matches. If a match is found, the task MUST be SKIPPED (no chunking, no embedding, no write) and reported as `skipped`. If the source content has changed (different hash), the task MUST be treated as a new/distinct ingest — its chunks are added alongside any prior version (no replace/delete of old chunks in this slice; this keeps the operation simple and avoids destructive writes). This MUST be documented as current behavior, not a final policy.

#### Scenario: Re-ingesting unchanged source is skipped
- GIVEN a PDF previously ingested successfully (its `content_hash` exists in the `recipes` collection)
- WHEN the same PDF task is run again with unchanged content
- THEN no new chunks are written, the task is reported as `skipped`, and no embedding calls are made

#### Scenario: Changed content is treated as a new ingest
- GIVEN a PDF previously ingested, now modified (different normalized content, different `content_hash`)
- WHEN the task runs again
- THEN the new content is chunked, embedded, and stored as additional chunks (the prior chunks remain; no delete/replace occurs)

### Requirement: Deterministic content_hash normalization

`content_hash` MUST be computed as SHA-256 over a deterministically normalized representation of the source's raw concatenated content, such that the same logical input produces the same hash across runs and machines. Normalization MUST account for: consistent text encoding (UTF-8), consistent whitespace handling, and a fixed page/section join order matching the loader's natural document order. This computation MUST be a pure function, unit-testable without I/O.

#### Scenario: Same content produces same hash across runs
- GIVEN the same PDF file loaded twice (e.g., in two separate CLI runs)
- WHEN `content_hash` is computed both times
- THEN the resulting hash strings are identical

#### Scenario: Different content produces different hash
- GIVEN two PDFs with different text content
- WHEN `content_hash` is computed for each
- THEN the resulting hashes differ

### Requirement: Per-task error isolation (continue-and-report)

A failure in any single task (file not found, loader error, unsupported type, embedding/storage error) MUST NOT abort the run. The CLI MUST accumulate a per-task outcome (`stored`, `skipped`, or `failed` with a reason), continue processing remaining tasks, print a summary report at the end, and exit with a non-zero code if at least one task failed (zero if all tasks succeeded or were skipped).

#### Scenario: One bad task does not stop the run
- GIVEN a task list with 3 PDF tasks where the 2nd points to a missing file
- WHEN the CLI runs
- THEN tasks 1 and 3 are processed normally, task 2 is recorded as `failed` with a "file not found" reason, and the run completes with a summary listing all three outcomes

#### Scenario: Exit code reflects overall outcome
- GIVEN a run where every task either succeeded or was skipped (none failed)
- WHEN the CLI finishes
- THEN it exits with code `0`

#### Scenario: Exit code signals partial failure
- GIVEN a run where at least one task failed
- WHEN the CLI finishes
- THEN it exits with a non-zero code, even though other tasks succeeded

### Requirement: Test coverage and quality gates

Unit tests MUST follow the AAA pattern and `test_<unit>_<scenario>_<expected>` naming, mocking NVIDIA API calls, filesystem, and network — never mocking the unit under test. The integration test for PDF ingestion MUST use a real pgvector store via Testcontainers with MOCKED (deterministic fake) embeddings — no live NVIDIA API key or network access required. Overall coverage MUST meet the project's 80% minimum.

#### Scenario: Unit test isolates pure logic
- GIVEN `metadata.py`'s `content_hash` computation
- WHEN it is unit tested
- THEN the test supplies in-memory text input (no filesystem/network) and asserts on the returned hash, named e.g. `test_content_hash_same_input_returns_same_hash`

#### Scenario: Integration test exercises real store with mocked embeddings
- GIVEN a Testcontainers-backed pgvector instance and a deterministic fake embeddings implementation
- WHEN the PDF E2E integration test runs `ingest_documents` against a sample PDF
- THEN chunks are persisted in the real `recipes` collection with full metadata, and no real NVIDIA API call occurs

## Open Questions

- Exact PGVector existence-check mechanism (PGVector filter API vs. raw SQLAlchemy `SELECT 1` through `Container.engine`) is left to design — both satisfy this spec's "query before write" requirement.
- Whether a legacy `--source` single-file CLI flag remains as sugar alongside `--tasks` is left to design; this spec only mandates `--tasks` task-list support.
