"""Unit tests for src/worker/cli.py — --tasks runner with continue-and-report."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from src.worker.cli import main, run_tasks
from src.worker.pipeline import IngestResult
from src.worker.tasks import Task, TaskFileError

# ---------------------------------------------------------------------------
# run_tasks()
# ---------------------------------------------------------------------------


def test_run_tasks_all_succeed_returns_zero_exit_code(capsys):
    # Arrange
    tasks = [Task(source_type="pdf", source="a.pdf"), Task(source_type="pdf", source="b.pdf")]
    container = MagicMock()
    results = [
        IngestResult(status="stored", source="a.pdf", chunks=3),
        IngestResult(status="skipped", source="b.pdf", chunks=0),
    ]

    # Act
    with patch("src.worker.cli.ingest_task", side_effect=results) as mock_ingest:
        exit_code = run_tasks(container, tasks)

    # Assert
    assert exit_code == 0
    assert mock_ingest.call_count == 2
    captured = capsys.readouterr()
    assert "stored" in captured.out
    assert "skipped" in captured.out


def test_run_tasks_one_failure_continues_and_returns_nonzero_exit_code(capsys):
    # Arrange
    tasks = [
        Task(source_type="pdf", source="good.pdf"),
        Task(source_type="pdf", source="bad.pdf"),
        Task(source_type="pdf", source="also-good.pdf"),
    ]
    container = MagicMock()

    def fake_ingest(_container, task):
        if task.source == "bad.pdf":
            raise ValueError("boom")
        return IngestResult(status="stored", source=task.source, chunks=1)

    # Act
    with patch("src.worker.cli.ingest_task", side_effect=fake_ingest) as mock_ingest:
        exit_code = run_tasks(container, tasks)

    # Assert
    assert exit_code == 1
    assert mock_ingest.call_count == 3
    captured = capsys.readouterr()
    assert "good.pdf" in captured.out
    assert "also-good.pdf" in captured.out
    assert "failed" in captured.out
    assert "boom" in captured.out


def test_run_tasks_empty_list_returns_zero_exit_code(capsys):
    # Arrange
    container = MagicMock()

    # Act
    with patch("src.worker.cli.ingest_task") as mock_ingest:
        exit_code = run_tasks(container, [])

    # Assert
    assert exit_code == 0
    mock_ingest.assert_not_called()
    captured = capsys.readouterr()
    assert "no tasks" in captured.out.lower()


# ---------------------------------------------------------------------------
# main() dispatcher
# ---------------------------------------------------------------------------


def test_main_tasks_flag_loads_file_and_runs_tasks():
    # Arrange
    argv = ["cli", "ingest", "--tasks", "tasks.yaml"]
    fake_tasks = [Task(source_type="pdf", source="a.pdf")]
    fake_container = MagicMock()

    # Act
    with (
        patch.object(sys, "argv", argv),
        patch("src.worker.cli.load_task_file", return_value=fake_tasks) as mock_load,
        patch("src.worker.cli.create_container", return_value=fake_container) as mock_create,
        patch("src.worker.cli.run_tasks", return_value=0) as mock_run,
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    # Assert
    mock_load.assert_called_once_with("tasks.yaml")
    mock_create.assert_called_once()
    mock_run.assert_called_once_with(fake_container, fake_tasks)
    assert exc_info.value.code == 0


def test_main_tasks_flag_propagates_run_tasks_exit_code():
    # Arrange
    argv = ["cli", "ingest", "--tasks", "tasks.yaml"]

    # Act
    with (
        patch.object(sys, "argv", argv),
        patch("src.worker.cli.load_task_file", return_value=[]),
        patch("src.worker.cli.create_container", return_value=MagicMock()),
        patch("src.worker.cli.run_tasks", return_value=1),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    # Assert
    assert exc_info.value.code == 1


def test_main_tasks_flag_invalid_file_exits_with_1(capsys):
    # Arrange
    argv = ["cli", "ingest", "--tasks", "missing.yaml"]

    # Act
    with (
        patch.object(sys, "argv", argv),
        patch("src.worker.cli.load_task_file", side_effect=TaskFileError("Task file not found")),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    # Assert
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Task file not found" in captured.out + captured.err


def test_main_exits_with_1_when_no_subcommand():
    # Arrange
    argv = ["cli"]

    # Act / Assert
    with patch.object(sys, "argv", argv):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
