from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import text

from src.worker.metadata import build_base_metadata, enrich_documents
from src.worker.router import loader_for
from src.worker.tasks import Task

if TYPE_CHECKING:
    from src.core.container import Container

# langchain-postgres creates langchain_pg_embedding lazily on the first add_documents().
# Guard the lookup so a fresh database (table not created yet) is treated as "nothing stored".
_TABLE_EXISTS_QUERY = text("SELECT to_regclass('langchain_pg_embedding')")
_EXISTENCE_QUERY = text(
    "SELECT 1 FROM langchain_pg_embedding WHERE cmetadata->>'content_hash' = :content_hash LIMIT 1"
)


@dataclass
class IngestResult:
    status: str
    source: str
    chunks: int = 0
    reason: str | None = None


def _content_hash_exists(container: Container, content_hash: str) -> bool:
    with container.engine.connect() as connection:
        if connection.execute(_TABLE_EXISTS_QUERY).scalar() is None:
            return False
        row = connection.execute(_EXISTENCE_QUERY, {"content_hash": content_hash}).first()
    return row is not None


def ingest_task(container: Container, task: Task) -> IngestResult:
    loader = loader_for(task.source_type)
    docs = loader(task.source)

    base_metadata = build_base_metadata(task, docs)
    content_hash = base_metadata["content_hash"]

    if _content_hash_exists(container, content_hash):
        return IngestResult(status="skipped", source=task.source, chunks=0)

    splitter = RecursiveCharacterTextSplitter()
    chunks = splitter.split_documents(docs)
    enriched_chunks = enrich_documents(chunks, base_metadata)

    container.vector_store.add_documents(enriched_chunks)

    return IngestResult(status="stored", source=task.source, chunks=len(enriched_chunks))
