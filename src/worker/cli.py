import argparse
import sys


def ingest(source: str) -> None:
    # TODO: route to appropriate loader based on source type
    print(f"Ingesting from: {source}")


def main() -> None:
    parser = argparse.ArgumentParser(description="MealMate content ingestion CLI")
    subparsers = parser.add_subparsers(dest="command")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest content into vector store")
    ingest_parser.add_argument("--source", required=True, help="URL or file path to ingest")

    args = parser.parse_args()

    if args.command == "ingest":
        ingest(args.source)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
