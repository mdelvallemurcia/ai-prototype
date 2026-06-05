"""Unit tests for src/worker/cli.py — ingest() function and main() dispatcher."""

import sys
from unittest.mock import patch

import pytest

from src.worker.cli import ingest, main

# ---------------------------------------------------------------------------
# ingest()
# ---------------------------------------------------------------------------


def test_ingest_prints_source(capsys):
    # Arrange
    source = "https://example.com"

    # Act
    ingest(source)

    # Assert
    captured = capsys.readouterr()
    assert "Ingesting from: https://example.com" in captured.out


# ---------------------------------------------------------------------------
# main() dispatcher
# ---------------------------------------------------------------------------


def test_main_dispatches_ingest_subcommand():
    # Arrange
    argv = ["cli", "ingest", "--source", "https://x.com"]

    # Act
    with patch.object(sys, "argv", argv), patch("src.worker.cli.ingest") as mock_ingest:
        main()

    # Assert
    mock_ingest.assert_called_once_with("https://x.com")


def test_main_exits_with_1_when_no_subcommand():
    # Arrange
    argv = ["cli"]

    # Act / Assert
    with patch.object(sys, "argv", argv):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
