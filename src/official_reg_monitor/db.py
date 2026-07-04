from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .paths import bundled_data_path
from .timeutil import parse_utc, utc_now


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    with bundled_data_path("schema.sql").open("r", encoding="utf-8") as f:
        conn.executescript(f.read())


def upsert_sources(conn: sqlite3.Connection, registry: dict[str, Any]) -> None:
    now = utc_now()
    for source in registry["sources"]:
        conn.execute(
            """
            INSERT INTO sources (
              source_id, jurisdiction, name, official_owner, url, kind,
              cadence, parser, registry_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
              jurisdiction=excluded.jurisdiction,
              name=excluded.name,
              official_owner=excluded.official_owner,
              url=excluded.url,
              kind=excluded.kind,
              cadence=excluded.cadence,
              parser=excluded.parser,
              registry_json=excluded.registry_json,
              updated_at=excluded.updated_at
            """,
            (
                source["source_id"],
                source.get("jurisdiction"),
                source.get("name"),
                source.get("official_owner"),
                source.get("url"),
                source.get("kind"),
                source.get("cadence"),
                source.get("parser"),
                json.dumps(source, ensure_ascii=False, sort_keys=True),
                now,
                now,
            ),
        )
    conn.commit()


def previous_hash(conn: sqlite3.Connection, source_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT sha256
        FROM source_snapshots
        WHERE source_id = ? AND error IS NULL AND sha256 IS NOT NULL
        ORDER BY fetched_at DESC, id DESC
        LIMIT 1
        """,
        (source_id,),
    ).fetchone()
    return row["sha256"] if row else None


def latest_success_at(conn: sqlite3.Connection, source_id: str):
    row = conn.execute(
        """
        SELECT fetched_at
        FROM source_snapshots
        WHERE source_id = ? AND error IS NULL
        ORDER BY fetched_at DESC, id DESC
        LIMIT 1
        """,
        (source_id,),
    ).fetchone()
    return parse_utc(row["fetched_at"]) if row else None


def record_snapshot(conn: sqlite3.Connection, source: dict[str, Any], result: dict[str, Any], changed: bool, error: str | None = None) -> int:
    cursor = conn.execute(
        """
        INSERT INTO source_snapshots (
          source_id, fetched_at, url, http_status, content_type, etag,
          last_modified, sha256, byte_size, path, changed, error
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source["source_id"],
            utc_now(),
            source["url"],
            result.get("http_status"),
            result.get("content_type"),
            result.get("etag"),
            result.get("last_modified"),
            result.get("sha256"),
            result.get("byte_size"),
            result.get("path"),
            1 if changed else 0,
            error,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def record_asset(conn: sqlite3.Connection, snapshot_id: int, asset: dict[str, Any], error: str | None = None) -> None:
    conn.execute(
        """
        INSERT INTO snapshot_assets (
          source_snapshot_id, url, http_status, content_type, sha256,
          byte_size, path, error
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            asset.get("url"),
            asset.get("http_status"),
            asset.get("content_type"),
            asset.get("sha256"),
            asset.get("byte_size"),
            asset.get("path"),
            error,
        ),
    )
    conn.commit()

