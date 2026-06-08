# Archive Report: worker-cli-ingestion

**Status**: ARCHIVED  
**Date**: 2026-06-08  
**Change**: worker-cli-ingestion  
**Verdict**: PASS WITH WARNINGS (W001: stale task annotation now corrected)  
**Verification Evidence**: 85 passed, 95.94% coverage, 2/2 integration tests, ruff clean

---

## What Shipped

PDF end-to-end ingestion pipeline (worker-cli-ingestion) — fully implemented and verified.

**Core implementation** (PR1 + PR2 + PR3, stacked-to-main):
- `src/worker/tasks.py`: YAML/JSON task-list parser with validation
- `src/worker/metadata.py`: metadata contract builder, content_hash computation (pure, unit-testable)
- `src/worker/router.py`: explicit source-type router (PDF → real loader; YouTube/Web → not-implemented; unknown → error)
- `src/worker/pipeline.py`: orchestration (load → enrich → dedup → chunk → store), with `to_regclass` guard for fresh-DB table-lifecycle bug (see bugfix id 463)
- `src/worker/cli.py`: rewritten `--tasks <file>` runner with per-task error isolation and continue-and-report
- `src/core/container.py`: added explicit `distance_strategy="cosine"` to PGVector
- `pyproject.toml`: added `pyyaml>=6.0` and dev dep `testcontainers[postgres]>=4.14.2`

**Quality evidence**:
- **Unit tests**: 83/85 tests in unit suite (cli, pipeline, router, metadata, tasks, container). All follow AAA pattern with `test_<unit>_<scenario>_<expected>` naming. Mocks cover NVIDIA API, filesystem, network; real Container/vector store interactions tested.
- **Integration tests**: 2/2 E2E tests PASSING (greenfield Testcontainers fixture with real pgvector, deterministic fake embeddings):
  - `test_ingest_pdf_task_persists_chunks_with_full_metadata` — asserts all 5 metadata fields (source_url, source_type, title, chunk_index, content_hash) persisted correctly
  - `test_ingest_pdf_task_rerun_same_source_skips_without_new_rows` — proves idempotent dedup via content_hash
- **Coverage**: 95.94% overall (gate: 80%). Per-module: cli.py 95%, pipeline.py 100%, router.py 100%, metadata.py 96%, tasks.py 96%, container.py 100%.
- **Linting**: `ruff check` and `ruff format` both clean.

---

## Specification Compliance

All 8 requirements from `openspec/specs/worker-ingestion/spec.md` verified PASS:

1. **Task-list parsing** (YAML+JSON, errors) — implemented in `tasks.py`; 10 unit tests cover valid/invalid/edge cases; integration E2E assumes valid input
2. **Source-type routing** — `router.py` explicit factory; PDF real, YouTube/Web recognized-but-not-implemented, unknown raises ValueError
3. **PDF E2E ingestion** (load→chunk→embed→store) — `pipeline.py` + integration test; real pgvector stores chunks with full metadata
4. **Metadata contract** (5 fields: source_url, source_type, title, chunk_index, content_hash) — `metadata.py` + integration test asserts all 5 present in persisted rows
5. **Idempotent re-ingest via content_hash** — integration test `test_*_skips_without_new_rows` PASSED; proves unchanged source skipped on re-run
6. **Deterministic content_hash** (SHA-256 over normalized text) — `compute_content_hash` pure function; unit tests prove same input → same hash, different input → different hash
7. **Per-task error isolation + exit codes** — `cli.py::run_tasks` try/except per task, continue, print summary, exit 1 if failed else 0; unit tests cover success/failure/exit-code paths
8. **Quality gates** (AAA naming, 80% coverage, integration real DB + mocked embeddings) — all criteria met; 95.94% coverage, fresh E2E execution

---

## Key Decisions & Tradeoffs

1. **Task-list schema explicit, not auto-detected**: Forces intent clarity; brittle auto-detect would hide errors.
2. **Dedup check via `to_regclass` guard on fresh DB**: Cleaner than catching `ProgrammingError`; langchain-postgres tables are created lazily on first write.
3. **Additive-only changed-content reingest**: Simplest semantics; replace/delete policy is a separate future decision.
4. **DI Container NOT bypassed**: All services (engine, vector_store, embeddings) injected via `Container`; reinforces ADR-004 discipline.
5. **ADR-005 chunking defaults, no tuning**: Avoids configuration sprawl; future tuning is a separate change.
6. **Testcontainers + DeterministicFakeEmbedding** for integration: Real DB (catches table-lifecycle bugs unit tests miss), no real API calls.

---

## Notable Bug Fixed During Implementation

**Dedup query crash on fresh DB** (bugfix id 463):
- The `_content_hash_exists` query crashed with `psycopg.errors.UndefinedTable: relation "langchain_pg_embedding" does not exist` during the first ingest on an empty database.
- Root cause: langchain-postgres creates tables lazily, only on first `add_documents()`. Pipeline dedup queries before that, so on fresh DB the table doesn't exist.
- Fix: Guard with `SELECT to_regclass('langchain_pg_embedding')` before running the dedup lookup; return False if table doesn't exist yet.
- Detection: Unit tests (mocked DB) hid this; PR3 Testcontainers E2E integration test caught it (exactly why we run real-DB integration tests).
- Consequence: Added regression test; full suite now passes 85/85.

---

## Deferred Scopes (Out of This Change)

- YouTube loader wiring (Phase D.1) — deferred to separate change
- Web loader wiring (Phase D.2) — deferred to separate change
- Replace/delete policy for changed-content re-ingest (Phase D.3) — deferred to separate change
- Retrieval/RAG chain integration (separate `src/web/` change)

---

## Artifact Integrity & Archive Warnings

### W001 (WARNING, now resolved)
**Stale blocker annotation in Phase 8 (tasks.md, lines 81, 83–100)**

**What was wrong**: Task 8.4 was checked `[x]` but annotated "(BLOCKED — see notes below)" with a "Phase 8 — BLOCKER NOTE (developer action required)" section claiming:
- `testcontainers` was NOT an installed dependency
- No Docker daemon was reachable
- Developer approval and manual action required

**Why it was stale**: Both conditions became FALSE:
- User approved adding `testcontainers[postgres]>=4.14.2` to dev deps (now in `pyproject.toml`)
- Docker Desktop was running during PR3 apply; integration suite executed and passed (2/2)
- Dedup bug found+fixed via `to_regclass` guard (bugfix id 463)
- Fresh verification (sdd-verify, report id 464) confirmed: 85/85 passing, 95.94% coverage

**Corrective action**: During archive, the stale "Phase 8 — BLOCKER NOTE" section was replaced with a concise "Phase 8 — Resolution" summary confirming all tasks done and both integration tests passing. The task checklist (8.4) was updated to remove the "(BLOCKED)" label. This keeps the artifact trail accurate for future readers and prevents confusion about whether manual developer action is still required.

---

## Observation IDs (Engram Traceability)

| Artifact | ID | Type | Topic Key |
|----------|----|----|-----------|
| Proposal | 456 | architecture | sdd/worker-cli-ingestion/proposal |
| Spec | 458 | architecture | sdd/worker-cli-ingestion/spec |
| Design | 457 | architecture | sdd/worker-cli-ingestion/design |
| Tasks | 459 | architecture | sdd/worker-cli-ingestion/tasks |
| Apply-progress | 460 | architecture | sdd/worker-cli-ingestion/apply-progress |
| Verify-report | 464 | architecture | sdd/worker-cli-ingestion/verify-report |
| Bugfix (dedup to_regclass) | 463 | bugfix | — (merged into apply-progress) |
| Archive-report | (this document) | architecture | sdd/worker-cli-ingestion/archive-report |

---

## Handoff to Developer

The change is **ready for commit** (uncommitted in working tree per CLAUDE.md). Three stacked-to-main commits recommended:
1. PR1: tasks.py, metadata.py, container distance_strategy, pyyaml dep
2. PR2: router.py, pipeline.py (with to_regclass fix), test files
3. PR3: cli.py rewrite, Testcontainers fixture, integration tests, docs update, .vscode/launch.json, examples/

All code verified PASS. Developer handles git commit/push.

---

## SDD Cycle Summary

**Proposal** (id 456): Defined PDF-first vertical slice, metadata normalization, dedup strategy, risk assessment.  
**Spec** (id 458): 8 detailed requirements with scenarios (all NEW domain: worker-ingestion).  
**Design** (id 457): Module layout, interfaces, key decisions, testing strategy, DI usage.  
**Tasks** (id 459): 9 phases (setup, parsing, metadata, routing, pipeline, container, CLI, integration, docs); chained PR recommendation (HIGH budget risk).  
**Apply** (id 460): PR1+PR2+PR3 fully implemented; dedup bug found and fixed; fresh verification executed; ready to archive.  
**Verify** (id 464): PASS WITH WARNINGS (W001 stale annotation, now corrected); 85/85 tests, 95.94% coverage, 2/2 integration, ruff clean.  
**Archive** (this report): Specs synced to main, change folder moved to archive, stale warning resolved, observation IDs recorded.

**Cycle status: CLOSED. Ready for next change.**
