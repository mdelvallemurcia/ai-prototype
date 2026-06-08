# Verify Report: worker-cli-ingestion

## Verdict: PASS WITH WARNINGS -- ready to archive

## Fresh test evidence (actually executed, this session)
- uv run pytest -> 85 passed, 1 warning (pre-existing langchain-community deprecation, unrelated). Total coverage 95.94 percent (gate 80 percent). Per-module: cli.py 95pct, pipeline.py 100pct, router.py 100pct, metadata.py 96pct, tasks.py 96pct, container.py 100pct.
- uv run pytest tests/integration/ --no-cov -v -> Docker daemon reachable. 2/2 integration tests PASSED:
  - test_ingest_pdf_task_persists_chunks_with_full_metadata PASSED
  - test_ingest_pdf_task_rerun_same_source_skips_without_new_rows PASSED
- uv run ruff check . -> All checks passed.
- uv run ruff format --check . -> 38 files already formatted.

This supersedes the apply-progress claim (engram id 460) that integration tests were WRITTEN but NOT EXECUTED -- that record is stale. The bugfix note (engram id 463) confirms they WERE later run, found a real bug (UndefinedTable on fresh DB), it was fixed, and the suite now passes at 85/85, 95.94 percent coverage. Current code on disk matches the post-fix state.

## Requirement-by-requirement compliance matrix

| Num | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Task-list parsing (YAML+JSON, errors) | PASS | src/worker/tasks.py (load_task_file, _parse_raw, _parse_entry); tests/unit/worker/test_tasks.py 10 tests covering valid YAML/JSON, missing file, malformed YAML/JSON, empty list, missing type/source, unknown type, non-list top-level -- all pass |
| 2 | Source-type routing | PASS | src/worker/router.py (loader_for: pdf real, youtube/web NotImplementedError, unknown ValueError); tests/unit/worker/test_router.py 4 tests pass; integration E2E proves PDF routes end-to-end |
| 3 | PDF E2E load-chunk-embed-store | PASS | src/worker/pipeline.py::ingest_task; integration test test_ingest_pdf_task_persists_chunks_with_full_metadata PASSED against real Testcontainers pgvector |
| 4 | Metadata contract (5 fields) | PASS | src/worker/metadata.py (build_base_metadata, enrich_documents); integration test asserts ALL 5 fields present in real langchain_pg_embedding.cmetadata rows |
| 5 | Idempotent re-ingest (dedup) | PASS | Integration test test_ingest_pdf_task_rerun_same_source_skips_without_new_rows PASSED -- re-ingest against REAL DB, status skipped, chunks 0, row count unchanged |
| 6 | content_hash determinism | PASS | src/worker/metadata.py::compute_content_hash -- pure SHA-256, tests/unit/worker/test_metadata.py covers same/different content, hexdigest, whitespace strip |
| 7 | Per-task error isolation + exit codes | PASS | src/worker/cli.py::run_tasks wraps ingest_task in try/except, continues, prints status lines, returns 1 if any failed else 0; tests/unit/worker/test_cli.py covers all scenarios |
| 8 | Quality gates | PASS | 85 tests AAA-structured with proper naming; coverage 95.94pct; integration uses real PostgresContainer + DeterministicFakeEmbedding |

All 8 requirements: PASS.

## Decision and scope adherence checks
- CLI exposes ONLY --tasks (grep for --source returns zero matches in src/, tests/, docs/)
- distance_strategy="cosine" set explicitly in src/core/container.py line 76, covered by test_container_vector_store_uses_cosine_distance_strategy
- Chunking uses RecursiveCharacterTextSplitter() with library defaults (pipeline.py line 50), per ADR-005
- DI Container not bypassed -- pipeline.py and cli.py consume Container via engine/vector_store/create_container
- pyyaml>=6.0 and testcontainers[postgres]>=4.14.2 both present in pyproject.toml
- docs/architecture.md Section 3 rewritten -- no longer a stub, documents --tasks runner, references ADR-005
- YouTube/Web correctly deferred -- router raises NotImplementedError, docs state deferred, tasks.md D.1/D.2 unchecked
## Issues found

### CRITICAL
None.

### WARNING
1. Stale BLOCKER note in openspec/changes/worker-cli-ingestion/tasks.md (lines 81, 83-100) -- Task 8.4 is checked done but annotated as BLOCKED, and the accompanying Phase 8 BLOCKER NOTE section claims testcontainers is NOT an installed dependency and No Docker daemon was reachable, instructing the developer to approve the dependency and run the suite manually. Both conditions are now FALSE: testcontainers[postgres]>=4.14.2 IS in pyproject.toml dev deps, Docker IS running, and the integration suite runs and passes (verified fresh this session -- 85/85, including the 2 E2E tests). This note was written during PR3 apply (before the dedup bugfix recorded in engram id 463 added the dependency and ran the suite) and was never updated/removed afterward. Where: openspec/changes/worker-cli-ingestion/tasks.md lines 81 and 83-100.
2. apply-progress (engram id 460) is stale/superseded but not marked as such -- it states the integration suite was WRITTEN but NOT EXECUTED, blocked on missing testcontainers dependency and no Docker daemon, and frames the change as NEARLY FULLY IMPLEMENTED with the ONE open item being Phase 8.4. The later bugfix record (engram id 463) shows this was resolved (dependency added with approval, Docker started, bug found and fixed, 85/85 passing). The two engram records are now contradictory for any future reader who only finds id 460. Where: engram sdd/worker-cli-ingestion/apply-progress (id 460), superseded in spirit by id 463 but not formally linked or updated.

### SUGGESTION
1. Update openspec/changes/worker-cli-ingestion/tasks.md Phase 8 to remove or replace the now-resolved BLOCKER note with a short note referencing the dedup-on-fresh-DB fix (id 463) and confirming 8.4 is done -- keeps the artifact trail accurate for archive and future readers.
2. Consider linking engram id 463 (bugfix) from the apply-progress record (id 460) or appending a SUPERSEDED -- see id 463 marker, since id 460's Overall change status section is now factually outdated.

## Tasks vs code-state cross-check
- Phases 1-7, 9: all checked done and verified DONE in code (matches implementation 1:1).
- Phase 8 (8.1-8.4): checked done -- code IS done and tests DO pass (verified fresh), but the inline annotation/BLOCKER note text is contradictory/stale (see WARNING 1). Net: task is correctly checked, but the supporting note misrepresents current reality.
- Deferred items D.1-D.3: correctly left unchecked -- YouTube/Web loaders genuinely not wired (NotImplementedError), replace/delete policy genuinely not decided. Correctly scoped out, not falsely marked done.

## Overall verdict
PASS WITH WARNINGS. All 8 spec requirements are implemented and proven by passing tests (unit + real-DB integration), all design decisions (cosine distance, ADR-005 chunking defaults, DI container usage, --tasks-only CLI, dependency additions) are honored, and quality gates (85/85 tests, 95.94 percent coverage, ruff clean) are met with FRESH evidence gathered this session. The only issues are two WARNING-level documentation staleness items (a contradictory BLOCKER note in tasks.md and an outdated apply-progress record) -- neither blocks correctness or archive-readiness, but should ideally be cleaned up before or during archive so the artifact trail does not mislead future readers.

Ready to archive -- no CRITICAL issues. Recommend updating the stale Phase 8 BLOCKER note in tasks.md as part of, or just before, archive.
