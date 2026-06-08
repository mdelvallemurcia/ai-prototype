# Design: Worker CLI Ingestion Pipeline (PDF-first)

## Technical Approach

Wire the `src/worker/` stub into `load → enrich → chunk → dedup → store` driven by a CLI task-list runner. Pure, unit-testable helpers (`metadata.py`, `router.py`) feed an orchestration function (`pipeline.py`) that consumes the injected `Container` (no DI bypass, ADR-004). Loaders stay untouched. PDF ships end-to-end; YouTube/Web raise `NotImplementedError`.

## Module / File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/worker/metadata.py` | Create | Pure: `compute_content_hash`, `build_base_metadata`, `enrich_documents` |
| `src/worker/router.py` | Create | `loader_for(source_type) -> Callable[[str], list[Document]]`; raise on unknown/unimplemented |
| `src/worker/pipeline.py` | Create | `ingest_documents(container, docs, base_metadata) -> IngestResult` |
| `src/worker/tasks.py` | Create | `load_task_file(path) -> list[Task]`; YAML+JSON by extension |
| `src/worker/cli.py` | Modify | `--tasks` arg; drive run; aggregate + print report; exit code |
| `src/core/container.py` | Modify | `distance_strategy="cosine"` on PGVector |
| `pyproject.toml` | Modify | add `pyyaml>=6.0` to `[project].dependencies` |

## Interfaces / Contracts

```python
# tasks.py
@dataclass(frozen=True)
class Task:
    source_type: str            # "pdf" | "youtube" | "web"
    source: str                 # path or URL
    metadata: dict[str, Any]    # optional overrides, shallow-merged

# pipeline.py
@dataclass
class IngestResult:
    status: str                 # "stored" | "skipped" | "failed"
    source: str
    chunks: int = 0
    reason: str | None = None
```

Pipeline data flow (source-agnostic from slice 1):

```
Task ─► loader_for(type)(source) ─► list[Document]
        │
        ▼  enrich_documents(docs, task)  (metadata.py)
   content_hash (per source) + base metadata attached
        │
        ▼  dedup check: exists?(hash) ── yes ─► IngestResult(skipped)
        │  no
        ▼  splitter.split_documents(docs)  (RecursiveCharacterTextSplitter, ADR-005 defaults)
        │  re-attach chunk_index per chunk
        ▼  container.vector_store.add_documents(chunks) ─► IngestResult(stored)
```

## Key Decisions

### Metadata contract (source-agnostic)
`build_base_metadata(task, docs)` derives a dict merged into each `Document.metadata` **without clobbering** loader-native keys (merge as `{**doc.metadata, **base}` so contract keys win only for the 5 reserved fields):
- `source_url` = task.source
- `source_type` = task.source_type
- `title` = task.metadata["title"] > loader metadata `title` > `Path(source).stem`
- `content_hash` = per-source SHA-256 (below)
- `chunk_index` = set AFTER split, 0-based, per chunk

### content_hash — per source, before chunking
**Choice**: SHA-256 hexdigest of normalized raw text, computed ONCE per source. **Rejected**: per-chunk hash (defeats early SKIP, still embeds). **Rationale**: a single existence check skips the whole source, avoiding all embedding API cost. Deterministic normalization (order-fixed): join `page_content` of all loader Documents with `"\n"` in loader order → `strip()` each, `"\n".join` → collapse internal whitespace runs? No — keep minimal and deterministic: `text = "\n".join(d.page_content for d in docs)`, then `text.strip()`, encode `utf-8`. No locale/whitespace collapsing beyond strip, so the hash is reproducible across runs of the same file.

### Dedup / SKIP against PGVector
**Choice (a)**: raw SQLAlchemy read via `Container.engine` — `SELECT 1 FROM langchain_pg_embedding WHERE cmetadata->>'content_hash' = :h LIMIT 1`. **Rejected**: (b) PGVector filter API (couples to internal query semantics, still constructs store); (c) deterministic chunk IDs upsert (good hardening but does not skip embedding cost). **Rationale**: cheapest, runs before embed, reads the JSONB key langchain-postgres already writes. langchain-postgres OWNS the schema — we only READ, no migration, so the alembic skill's migration rules do not apply; we apply its safe-read guidance (parameterized query, `LIMIT 1`, text() bound params). **Limitation**: check-then-write is non-atomic; acceptable under the sequential manual-CLI assumption (documented).

### distance_strategy wiring
Add `distance_strategy="cosine"` to the `PGVector(...)` call in `container.py` inside the existing lazy property — no signature change, no eager connection, existing tests injecting `Container(Settings(...))` unaffected.

### Error handling
Per-task isolation: each task wrapped in try/except in `cli.py`; failure → `IngestResult(failed, reason=str(e))`, run continues. End-of-run summary prints `stored/skipped/failed` counts + per-failure reason. Exit code `1` if any task failed, else `0`. Unimplemented source types surface as `failed` (router raises), not crashes.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `metadata.py` | hash determinism, title fallback precedence, no-clobber merge, chunk_index assignment |
| Unit | `router.py` | pdf returns loader; unknown/youtube/web raise |
| Unit | `tasks.py` | YAML+JSON parse, missing required field errors |
| Unit | `pipeline.py` | mock loader+embeddings+dedup; assert skip path, store path, chunk count |
| Unit | `cli.py` | mock pipeline; assert continue-and-report, exit code, summary |
| Integration | PDF E2E | real pgvector via Testcontainers, MOCKED deterministic embeddings, real `Container(Settings(tc_url))`; assert rows in `langchain_pg_embedding`, re-run SKIPs |

**Integration fixtures (greenfield)** — create `tests/integration/conftest.py`:
- `pg_container` (session-scoped Testcontainers `pgvector/pgvector:pg17`, runs `CREATE EXTENSION vector`).
- `container` fixture = `Container(Settings(db_url=tc_url, ...))` with a `FakeEmbeddings(size=N)` (deterministic per-text vector) injected by overriding `_embeddings`, keeping the REAL vector store. Embeddings determinism: hash text → fixed-length float vector, no network.

## Migration / Rollout
No DB migration — langchain-postgres auto-creates tables on first `add_documents`. New dependency `pyyaml` requires `uv sync`.

## Open Questions / Risks
- [ ] Confirm `langchain_pg_embedding` / `cmetadata` table+column names against installed `langchain-postgres>=0.0.12` (read-only query depends on them; verify in apply).
- [ ] `RecursiveCharacterTextSplitter` import path (`langchain_text_splitters`) availability under current deps — verify in apply.
- Dedup non-atomic under concurrency — accepted (sequential CLI).
- content_hash stability assumes loaders emit pages in stable order — true for PyPDFLoader.
