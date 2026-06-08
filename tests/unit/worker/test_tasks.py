"""Unit tests for src/worker/tasks.py — task-list file parsing and validation."""

import pytest

from src.worker.tasks import Task, TaskFileError, load_task_file

# ---------------------------------------------------------------------------
# load_task_file — valid YAML
# ---------------------------------------------------------------------------


def test_load_task_file_valid_yaml_returns_tasks(tmp_path):
    # Arrange
    task_file = tmp_path / "tasks.yaml"
    task_file.write_text(
        "- type: pdf\n"
        "  source: /recipes/pasta.pdf\n"
        "  metadata:\n"
        "    title: Pasta Carbonara\n"
        "- type: youtube\n"
        "  source: https://youtube.com/watch?v=abc\n",
        encoding="utf-8",
    )

    # Act
    result = load_task_file(str(task_file))

    # Assert
    assert result == [
        Task(source_type="pdf", source="/recipes/pasta.pdf", metadata={"title": "Pasta Carbonara"}),
        Task(source_type="youtube", source="https://youtube.com/watch?v=abc", metadata={}),
    ]


# ---------------------------------------------------------------------------
# load_task_file — valid JSON
# ---------------------------------------------------------------------------


def test_load_task_file_valid_json_returns_tasks(tmp_path):
    # Arrange
    task_file = tmp_path / "tasks.json"
    task_file.write_text(
        '[{"type": "pdf", "source": "/recipes/soup.pdf", "metadata": {"title": "Soup"}},'
        ' {"type": "web", "source": "https://example.com/recipe"}]',
        encoding="utf-8",
    )

    # Act
    result = load_task_file(str(task_file))

    # Assert
    assert result == [
        Task(source_type="pdf", source="/recipes/soup.pdf", metadata={"title": "Soup"}),
        Task(source_type="web", source="https://example.com/recipe", metadata={}),
    ]


# ---------------------------------------------------------------------------
# load_task_file — error cases
# ---------------------------------------------------------------------------


def test_load_task_file_missing_file_raises_task_file_error(tmp_path):
    # Arrange
    missing_path = tmp_path / "does-not-exist.yaml"

    # Act & Assert
    with pytest.raises(TaskFileError, match="not found"):
        load_task_file(str(missing_path))


def test_load_task_file_malformed_yaml_raises_task_file_error(tmp_path):
    # Arrange
    task_file = tmp_path / "tasks.yaml"
    task_file.write_text("type: pdf\n  source: [unbalanced\n", encoding="utf-8")

    # Act & Assert
    with pytest.raises(TaskFileError, match="malformed|parse"):
        load_task_file(str(task_file))


def test_load_task_file_malformed_json_raises_task_file_error(tmp_path):
    # Arrange
    task_file = tmp_path / "tasks.json"
    task_file.write_text("{not valid json", encoding="utf-8")

    # Act & Assert
    with pytest.raises(TaskFileError, match="malformed|parse"):
        load_task_file(str(task_file))


def test_load_task_file_empty_list_returns_empty_list(tmp_path):
    # Arrange
    task_file = tmp_path / "tasks.yaml"
    task_file.write_text("[]\n", encoding="utf-8")

    # Act
    result = load_task_file(str(task_file))

    # Assert
    assert result == []


def test_load_task_file_entry_missing_required_field_raises_task_file_error(tmp_path):
    # Arrange
    task_file = tmp_path / "tasks.yaml"
    task_file.write_text("- type: pdf\n", encoding="utf-8")

    # Act & Assert
    with pytest.raises(TaskFileError, match="source"):
        load_task_file(str(task_file))


def test_load_task_file_entry_missing_type_field_raises_task_file_error(tmp_path):
    # Arrange
    task_file = tmp_path / "tasks.yaml"
    task_file.write_text("- source: /recipes/pasta.pdf\n", encoding="utf-8")

    # Act & Assert
    with pytest.raises(TaskFileError, match="type"):
        load_task_file(str(task_file))


def test_load_task_file_unknown_type_raises_task_file_error(tmp_path):
    # Arrange
    task_file = tmp_path / "tasks.yaml"
    task_file.write_text("- type: spotify\n  source: /recipes/song.mp3\n", encoding="utf-8")

    # Act & Assert
    with pytest.raises(TaskFileError, match="spotify"):
        load_task_file(str(task_file))


def test_load_task_file_unknown_top_level_structure_raises_task_file_error(tmp_path):
    # Arrange
    task_file = tmp_path / "tasks.yaml"
    task_file.write_text("type: pdf\nsource: /recipes/pasta.pdf\n", encoding="utf-8")

    # Act & Assert
    with pytest.raises(TaskFileError, match="list"):
        load_task_file(str(task_file))
