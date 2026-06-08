from __future__ import annotations

from collections.abc import Callable

from langchain_core.documents import Document

from src.worker.loaders.pdf import load_pdf

LoaderFn = Callable[[str], list[Document]]


def loader_for(source_type: str) -> LoaderFn:
    if source_type == "pdf":
        return load_pdf
    if source_type in ("youtube", "web"):
        raise NotImplementedError(f"Loader for source type '{source_type}' is not implemented yet")
    raise ValueError(f"Unknown source type '{source_type}'")
