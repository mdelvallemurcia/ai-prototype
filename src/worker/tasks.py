from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

KNOWN_SOURCE_TYPES = {"pdf", "youtube", "web"}


class TaskFileError(Exception):
    pass


@dataclass(frozen=True)
class Task:
    source_type: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


def load_task_file(path: str) -> list[Task]:
    file_path = Path(path)
    if not file_path.is_file():
        raise TaskFileError(f"Task file not found: {path}")

    raw_text = file_path.read_text(encoding="utf-8")
    raw_entries = _parse_raw(raw_text, file_path)

    if not isinstance(raw_entries, list):
        type_name = type(raw_entries).__name__
        raise TaskFileError(
            f"Task file must contain a list of task entries, got {type_name}: {path}"
        )

    return [_parse_entry(entry, index) for index, entry in enumerate(raw_entries)]


def _parse_raw(raw_text: str, file_path: Path) -> Any:
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".json":
            return json.loads(raw_text)
        return yaml.safe_load(raw_text)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise TaskFileError(f"Malformed task file, failed to parse {file_path}: {exc}") from exc


def _parse_entry(entry: Any, index: int) -> Task:
    if not isinstance(entry, dict):
        type_name = type(entry).__name__
        raise TaskFileError(f"Task entry at index {index} must be a mapping, got {type_name}")

    if "type" not in entry:
        raise TaskFileError(f"Task entry at index {index} is missing required field 'type'")
    if "source" not in entry:
        raise TaskFileError(f"Task entry at index {index} is missing required field 'source'")

    source_type = entry["type"]
    if source_type not in KNOWN_SOURCE_TYPES:
        raise TaskFileError(
            f"Task entry at index {index} has unknown type '{source_type}', "
            f"expected one of {sorted(KNOWN_SOURCE_TYPES)}"
        )

    metadata = entry.get("metadata") or {}
    return Task(source_type=source_type, source=entry["source"], metadata=metadata)
