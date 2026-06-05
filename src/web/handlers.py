"""Pure business logic for the MealMate chat interface.

No Streamlit import. All functions accept duck-typed inputs
(objects with .name, .type, .size, .getvalue()) to enable
direct unit testing without a Streamlit runtime.
"""

from __future__ import annotations

import base64
import io
from collections.abc import Iterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from PIL import Image

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "application/pdf",
    }
)

IMAGE_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
    }
)

THUMBNAIL_MAX: tuple[int, int] = (256, 256)

SYSTEM_PROMPT: str = (
    "You are MealMate, an AI recipe and meal-planning assistant. "
    "Help users find, choose, adapt, and discover recipes. "
    "Answer questions about ingredients, cooking techniques, and meal planning. "
    "Stay focused on the food, recipes, and meals domain. "
    "If a question is unrelated to food or cooking, politely redirect the conversation."
)


def to_langchain_messages(history: list[dict]) -> list:
    """Map session history to LangChain message objects.

    Prepends SystemMessage(SYSTEM_PROMPT). Maps role 'user' -> HumanMessage,
    'assistant' -> AIMessage. Only the 'content' field is used; all other keys
    (including 'files') are ignored (satisfies WLI-10).
    """
    messages: list = [SystemMessage(content=SYSTEM_PROMPT)]
    role_map: dict = {"user": HumanMessage, "assistant": AIMessage}
    for entry in history:
        cls = role_map.get(entry["role"])
        if cls is not None:
            messages.append(cls(content=entry["content"]))
    return messages


def stream_reply(chat_model: Any, messages: list) -> Iterator[str]:
    """Yield non-empty text chunks from chat_model.stream(messages).

    Defensively reads chunk.content via getattr; skips falsy values (WLI-07).
    """
    for chunk in chat_model.stream(messages):
        text: str = getattr(chunk, "content", "") or ""
        if text:
            yield text


def _make_thumbnail(data: bytes, max_size: tuple[int, int] = THUMBNAIL_MAX) -> str | None:
    """Decode image bytes, shrink to at most *max_size*, and return a base64 data URI.

    Returns ``None`` on any decode or encode failure so callers never crash.
    """
    try:
        img = Image.open(io.BytesIO(data))
        img.thumbnail(max_size)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None


def extract_file_metadata(file: Any) -> dict:
    """Extract serialisable metadata from an UploadedFile-like object.

    For images the returned dict includes a base64 ``thumbnail`` data URI.
    For PDFs (and all non-image types) ``thumbnail`` is ``None``.

    The raw file bytes are NOT stored in the returned dict.

    Args:
        file: Any object exposing ``.name``, ``.type``, ``.size``,
              and ``.getvalue() -> bytes``.

    Returns:
        ``{"name": str, "type": str, "size": int, "thumbnail": str | None}``
    """
    thumbnail: str | None = None
    if file.type in IMAGE_MIME_TYPES:
        thumbnail = _make_thumbnail(file.getvalue())

    return {
        "name": file.name,
        "type": file.type,
        "size": file.size,
        "thumbnail": thumbnail,
    }


def validate_file_types(files: list[Any]) -> list[Any]:
    """Filter *files* to only those whose MIME type is in ``ALLOWED_MIME_TYPES``.

    This function is result-based — it does NOT raise. Unsupported files are
    silently discarded so the caller can decide how to surface the rejection.

    Args:
        files: List of file-like objects with a ``.type`` attribute.

    Returns:
        A (possibly empty) list containing only files with allowed MIME types.
    """
    return [f for f in files if f.type in ALLOWED_MIME_TYPES]
