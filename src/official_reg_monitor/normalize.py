from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .parsers import RegulatoryItem
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


def normalize_snapshot(conn: sqlite3.Connection, source: dict[str, Any], snapshot: sqlite3.Row) -> dict[str, Any]:
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
        records = parser.parse(Path(snapshot["path"]), source, snapshot)
        if records.status == "ok" and records.items:
            source_version_id = create_source_version(
                conn,
                source,
                snapshot,
                parser_version=getattr(parser, "version", "0.1.0"),
            )
            records.records_inserted = insert_regulatory_items(conn, source_version_id, records.items)
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


def create_source_version(
    conn: sqlite3.Connection,
    source: dict[str, Any],
    snapshot: sqlite3.Row,
    *,
    parser_version: str,
) -> int:
    source_code = source["source_id"]
    conn.execute(
        """
        INSERT INTO regulatory_sources (
          source_code, source_id, jurisdiction, official_owner, official_url, parser, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_code) DO UPDATE SET
          source_id=excluded.source_id,
          jurisdiction=excluded.jurisdiction,
          official_owner=excluded.official_owner,
          official_url=excluded.official_url,
          parser=excluded.parser,
          notes=excluded.notes
        """,
        (
            source_code,
            source["source_id"],
            source.get("jurisdiction"),
            source.get("official_owner"),
            source.get("url"),
            source.get("parser"),
            source.get("notes"),
        ),
    )
    existing = conn.execute(
        """
        SELECT id
        FROM source_versions
        WHERE source_code = ? AND source_snapshot_id = ? AND parser_version = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (source_code, snapshot["id"], parser_version),
    ).fetchone()
    if existing:
        source_version_id = int(existing["id"])
        conn.execute(
            """
            DELETE FROM regulatory_item_conditions
            WHERE regulatory_item_id IN (
              SELECT id FROM regulatory_items WHERE source_version_id = ?
            )
            """,
            (source_version_id,),
        )
        conn.execute("DELETE FROM regulatory_items WHERE source_version_id = ?", (source_version_id,))
        return source_version_id
    cursor = conn.execute(
        """
        INSERT INTO source_versions (
          source_code, source_snapshot_id, version_label, parsed_at, parser_version
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            source_code,
            snapshot["id"],
            snapshot["sha256"] or snapshot["fetched_at"],
            utc_now(),
            parser_version,
        ),
    )
    return int(cursor.lastrowid)


def insert_regulatory_items(conn: sqlite3.Connection, source_version_id: int, items: list[RegulatoryItem]) -> int:
    for item in items:
        conn.execute(
            """
            INSERT INTO regulatory_items (
              source_version_id, jurisdiction, source_code, annex_or_part, reference_no,
              ingredient_name_raw, cas_number_raw, ec_number_raw, status, max_percent,
              max_concentration_raw, product_scope, body_part_scope, warning_label,
              conditions_raw, note_raw, official_row_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_version_id,
                item.jurisdiction,
                item.source_code,
                item.annex_or_part,
                item.reference_no,
                item.ingredient_name_raw,
                item.cas_number_raw,
                item.ec_number_raw,
                item.status,
                item.max_percent,
                item.max_concentration_raw,
                item.product_scope,
                item.body_part_scope,
                item.warning_label,
                item.conditions_raw,
                item.note_raw,
                item.official_row_hash,
            ),
        )
    return len(items)
