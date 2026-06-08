from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from src.core.container import create_container
from src.worker.pipeline import ingest_task
from src.worker.tasks import TaskFileError, load_task_file

if TYPE_CHECKING:
    from src.core.container import Container
    from src.worker.tasks import Task


def run_tasks(container: Container, tasks: list[Task]) -> int:
    if not tasks:
        print("No tasks to run.")
        return 0

    failed = False
    for task in tasks:
        try:
            result = ingest_task(container, task)
        except Exception as exc:  # noqa: BLE001 - isolate per-task failures, continue the run
            failed = True
            print(f"[failed] {task.source}: {exc}")
            continue

        if result.status == "failed":
            failed = True
            print(f"[failed] {result.source}: {result.reason}")
        else:
            print(f"[{result.status}] {result.source} ({result.chunks} chunks)")

    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="MealMate content ingestion CLI")
    subparsers = parser.add_subparsers(dest="command")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest content into vector store")
    ingest_parser.add_argument(
        "--tasks", required=True, help="Path to a YAML or JSON task-list file"
    )

    args = parser.parse_args()

    if args.command == "ingest":
        try:
            tasks = load_task_file(args.tasks)
        except TaskFileError as exc:
            print(f"Error: {exc}")
            sys.exit(1)

        container = create_container()
        sys.exit(run_tasks(container, tasks))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
