from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .timeutil import utc_now


SCREENING_REGULATION_FIELDS = [
    "country_code",
    "source_code",
    "source_name",
    "annex",
    "status",
    "entry_number",
    "chemical_name",
    "inci_name",
    "cas_number",
    "ec_number",
    "product_type",
    "max_concentration",
    "warnings",
    "other_restrictions",
    "cmr",
    "update_date",
    "raw_url",
]

STATUS_MAP = {
    "prohibited": "banned",
    "restricted": "restricted",
    "colorant": "allowed_colorant",
    "preservative": "allowed_preservative",
    "uv_filter": "allowed_uv_filter",
}


def export_eu_cosing_regulations(
    conn: sqlite3.Connection,
    out_dir: str | Path,
    *,
    prefix: str = "eu_cosing_regulations",
) -> dict[str, Any]:
    out_path = Path(out_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    rows = eu_cosing_regulation_rows(conn)
    csv_path = out_path / f"{prefix}.csv"
    json_path = out_path / f"{prefix}.json"
    write_regulations_csv(csv_path, rows)
    write_regulations_json(json_path, rows)
    return {
        "ok": True,
        "total": len(rows),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "generated_at": utc_now(),
    }


def eu_cosing_regulation_rows(conn: sqlite3.Connection) -> list[dict[str, str | None]]:
    rows = conn.execute(
        """
        WITH latest_versions AS (
          SELECT source_code, max(id) AS source_version_id
          FROM source_versions
          WHERE source_code LIKE 'EU_COSING_ANNEX_%'
          GROUP BY source_code
        )
        SELECT
          ri.annex_or_part,
          ri.reference_no,
          ri.ingredient_name_raw,
          ri.cas_number_raw,
          ri.ec_number_raw,
          ri.status,
          ri.max_concentration_raw,
          ri.product_scope,
          ri.body_part_scope,
          ri.warning_label,
          ri.conditions_raw,
          ri.note_raw,
          rs.official_url
        FROM regulatory_items ri
        JOIN latest_versions lv ON lv.source_version_id = ri.source_version_id
        JOIN regulatory_sources rs ON rs.source_code = ri.source_code
        WHERE ri.jurisdiction = 'EU'
          AND ri.source_code LIKE 'EU_COSING_ANNEX_%'
        ORDER BY
          CASE ri.annex_or_part
            WHEN 'II' THEN 2
            WHEN 'III' THEN 3
            WHEN 'IV' THEN 4
            WHEN 'V' THEN 5
            WHEN 'VI' THEN 6
            ELSE 99
          END,
          ri.reference_no
        """
    ).fetchall()
    return [screening_row(row) for row in rows]


def screening_row(row: sqlite3.Row) -> dict[str, str | None]:
    cmr = note_value(row["note_raw"], "CMR")
    update_date = note_value(row["note_raw"], "Update Date")
    product_type = combined_product_type(row["product_scope"], row["body_part_scope"])
    name = row["ingredient_name_raw"]
    return {
        "country_code": "EU",
        "source_code": "EU_CosIng",
        "source_name": "EU CosIng Annex II-VI",
        "annex": row["annex_or_part"],
        "status": STATUS_MAP.get(row["status"], row["status"]),
        "entry_number": emptyish_to_none(row["reference_no"]),
        "chemical_name": name,
        "inci_name": name,
        "cas_number": emptyish_to_none(row["cas_number_raw"]),
        "ec_number": emptyish_to_none(row["ec_number_raw"]),
        "product_type": emptyish_to_none(product_type),
        "max_concentration": emptyish_to_none(row["max_concentration_raw"]),
        "warnings": emptyish_to_none(row["warning_label"]),
        "other_restrictions": emptyish_to_none(row["conditions_raw"]),
        "cmr": cmr,
        "update_date": update_date,
        "raw_url": row["official_url"],
    }


def write_regulations_csv(path: Path, rows: list[dict[str, str | None]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SCREENING_REGULATION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_regulations_json(path: Path, rows: list[dict[str, str | None]]) -> None:
    payload = {"total": len(rows), "items": rows}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def combined_product_type(product_scope: str | None, body_part_scope: str | None) -> str | None:
    if product_scope and body_part_scope:
        return f"{product_scope}, {body_part_scope}"
    return product_scope or body_part_scope


def emptyish_to_none(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    if cleaned in {"", "-"}:
        return None
    return cleaned


def note_value(note_raw: str | None, label: str) -> str | None:
    if not note_raw:
        return None
    match = re.search(rf"^{re.escape(label)}:\s*(.+)$", note_raw, flags=re.MULTILINE)
    return match.group(1).strip() if match else None
