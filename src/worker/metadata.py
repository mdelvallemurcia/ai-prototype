from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.worker.tasks import Task

if TYPE_CHECKING:
    from langchain_core.documents import Document

RESERVED_METADATA_KEYS = ("source_url", "source_type", "title", "content_hash")


def compute_content_hash(docs: list[Document]) -> str:
    text = "\n".join(doc.page_content for doc in docs).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_base_metadata(task: Task, docs: list[Document]) -> dict[str, Any]:
    return {
        "source_url": task.source,
        "source_type": task.source_type,
        "title": _resolve_title(task, docs),
        "content_hash": compute_content_hash(docs),
    }


def _resolve_title(task: Task, docs: list[Document]) -> str:
    override = task.metadata.get("title")
    if override:
        return override

    for doc in docs:
        loader_title = doc.metadata.get("title")
        if loader_title:
            return loader_title

    return Path(task.source).stem


def enrich_documents(docs: list[Document], base_metadata: dict[str, Any]) -> list[Document]:
    enriched = []
    for chunk_index, doc in enumerate(docs):
        doc.metadata = {**doc.metadata, **base_metadata, "chunk_index": chunk_index}
        enriched.append(doc)
    return enriched
