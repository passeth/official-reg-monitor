from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .parsers import get_parser
from .timeutil import utc_now


def latest_snapshots(conn: sqlite3.Connection, source_id: str | None = None) -> list[sqlite3.Row]:
    where = "WHERE error IS NULL AND path IS NOT NULL"
    params: tuple[str, ...] = ()
    if source_id:
        where += " AND source_id = ?"
        params = (source_id,)
    return list(
        conn.execute(
            f"""
            SELECT *
            FROM source_snapshots
            {where}
            AND id IN (
              SELECT max(id)
              FROM source_snapshots
              WHERE error IS NULL AND path IS NOT NULL
              GROUP BY source_id
            )
            ORDER BY source_id
            """,
            params,
        )
    )


def normalize_snapshot(conn: sqlite3.Connection, source: dict[str, Any], snapshot: sqlite3.Row, root: Path) -> dict[str, Any]:
    parser_name = source.get("parser") or "generic"
    parser = get_parser(parser_name)
    started_at = utc_now()
    cursor = conn.execute(
        """
        INSERT INTO parser_runs (
          source_snapshot_id, parser, parser_version, started_at, status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (snapshot["id"], parser_name, getattr(parser, "version", "0.1.0"), started_at, "running"),
    )
    run_id = int(cursor.lastrowid)
    try:
        records = parser.parse(root / snapshot["path"], source, snapshot)
        conn.execute(
            """
            UPDATE parser_runs
            SET finished_at = ?, status = ?, records_parsed = ?, records_inserted = ?, warnings = ?
            WHERE id = ?
            """,
            (
                utc_now(),
                records.status,
                records.records_parsed,
                records.records_inserted,
                "\n".join(records.warnings),
                run_id,
            ),
        )
        conn.commit()
        return {
            "source_id": source["source_id"],
            "ok": records.status in {"ok", "skipped"},
            "status": records.status,
            "records_parsed": records.records_parsed,
            "records_inserted": records.records_inserted,
            "warnings": records.warnings,
        }
    except Exception as exc:
        conn.execute(
            """
            UPDATE parser_runs
            SET finished_at = ?, status = ?, error = ?
            WHERE id = ?
            """,
            (utc_now(), "error", str(exc), run_id),
        )
        conn.commit()
        return {
            "source_id": source["source_id"],
            "ok": False,
            "status": "error",
            "error": str(exc),
        }

