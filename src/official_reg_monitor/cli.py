from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .config import read_registry, select_sources
from .db import connect, upsert_sources
from .fetcher import monitor_source
from .normalize import latest_snapshots, normalize_snapshot


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--registry", default=None, help="Registry JSON path. Defaults to the bundled registry.")
    parser.add_argument("--db", default="monitoring.sqlite")
    parser.add_argument("--out", default="snapshots")
    parser.add_argument("--source", help="Optional source_id")


def fetch_cmd(args: argparse.Namespace) -> int:
    registry = read_registry(args.registry)
    conn = connect(args.db)
    upsert_sources(conn, registry)
    sources = select_sources(registry, args.source)
    results = [
        monitor_source(
            conn,
            source,
            args.out,
            force=args.force,
            respect_cadence=not args.no_cadence,
            capture_assets=not args.no_assets,
        )
        for source in sources
    ]
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    return 0 if all(result["ok"] for result in results) else 1


def normalize_cmd(args: argparse.Namespace) -> int:
    registry = read_registry(args.registry)
    source_map = {source["source_id"]: source for source in registry["sources"]}
    conn = connect(args.db)
    upsert_sources(conn, registry)
    snapshots = latest_snapshots(conn, args.source)
    results = []
    for snapshot in snapshots:
        source = source_map.get(snapshot["source_id"])
        if not source:
            continue
        results.append(normalize_snapshot(conn, source, snapshot))
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    return 0 if all(result["ok"] for result in results) else 1


def status_cmd(args: argparse.Namespace) -> int:
    registry = read_registry(args.registry)
    conn = connect(args.db)
    upsert_sources(conn, registry)
    rows = conn.execute(
        """
        SELECT s.source_id, s.jurisdiction, s.cadence,
               max(ss.fetched_at) AS last_fetched_at,
               sum(CASE WHEN ss.changed = 1 THEN 1 ELSE 0 END) AS changed_count,
               sum(CASE WHEN ss.error IS NOT NULL THEN 1 ELSE 0 END) AS error_count
        FROM sources s
        LEFT JOIN source_snapshots ss ON ss.source_id = s.source_id
        GROUP BY s.source_id
        ORDER BY s.source_id
        """
    ).fetchall()
    print(json.dumps({"sources": [dict(row) for row in rows]}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="official-reg-monitor")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    fetch = subparsers.add_parser("fetch", help="Fetch official source snapshots")
    add_common_args(fetch)
    fetch.add_argument("--force", action="store_true", help="Fetch even when cadence says the source is not due")
    fetch.add_argument("--no-cadence", action="store_true", help="Ignore source cadence and fetch every selected source")
    fetch.add_argument("--no-assets", action="store_true", help="Do not capture same-origin linked JS/CSS/PDF assets")
    fetch.set_defaults(func=fetch_cmd)

    normalize = subparsers.add_parser("normalize", help="Run structured parsers against latest snapshots")
    add_common_args(normalize)
    normalize.set_defaults(func=normalize_cmd)

    status = subparsers.add_parser("status", help="Show source monitoring status")
    status.add_argument("--registry", default=None, help="Registry JSON path. Defaults to the bundled registry.")
    status.add_argument("--db", default="monitoring.sqlite")
    status.set_defaults(func=status_cmd)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
