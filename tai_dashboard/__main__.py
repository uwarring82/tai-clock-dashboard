"""Run with python -m tai_dashboard."""

import argparse
import sqlite3
from pathlib import Path

from .ingest import build_database
from .web import serve

DEFAULT_DATABASE = Path("build/tai.sqlite3")
DEFAULT_MANIFEST = Path("fixtures/manifest.json")


def main():
    parser = argparse.ArgumentParser(description="Explore synthetic clock history and monthly weights.")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Verify the fixture archive and build the SQLite snapshot.")
    build.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    start = commands.add_parser("serve", help="Run the read-only dashboard locally.")
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=8000)
    for command in (build, start):
        command.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    try:
        if args.command == "build":
            build_database(args.manifest, args.database)
            print(f"Built {args.database}")
        else:
            serve(args.database, args.host, args.port)
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
