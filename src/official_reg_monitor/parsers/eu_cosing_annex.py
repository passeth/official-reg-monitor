from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any

from . import ParseResult, RegulatoryItem


ANNEX_STATUS = {
    "II": "prohibited",
    "III": "restricted",
    "IV": "colorant",
    "V": "preservative",
    "VI": "uv_filter",
}


class EuCosingAnnexParser:
    version = "0.1.0"

    def parse(self, path: Path, source: dict[str, Any], snapshot) -> ParseResult:
        warnings: list[str] = []
        try:
            rows = read_csv_rows(path)
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            return ParseResult(status="ok", warnings=[f"Could not read EU CosIng annex CSV: {exc}"])

        header_index = detect_header_index(rows)
        if header_index is None:
            return ParseResult(
                status="ok",
                warnings=["No EU CosIng annex table header was found; no regulatory items were parsed."],
            )

        header = rows[header_index]
        columns = classify_columns(header)
        annex = annex_code(source)
        status = ANNEX_STATUS.get(annex or "", "annex_item")
        items: list[RegulatoryItem] = []
        skipped = 0
        for row in rows[header_index + 1 :]:
            if not any(clean_cell(cell) for cell in row):
                continue
            if looks_like_same_header(row, header):
                continue
            row_values = values_by_index(row, len(header))
            item = item_from_row(row_values, columns, source, annex, status)
            if item is None:
                skipped += 1
                continue
            items.append(item)

        if skipped:
            warnings.append(f"Skipped {skipped} EU CosIng row(s) without a reference number or substance name.")
        if not items:
            warnings.append("EU CosIng annex CSV contained a header but no data rows were parsed.")
        return ParseResult(status="ok", records_parsed=len(items), warnings=warnings, items=items)


def read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def detect_header_index(rows: list[list[str]]) -> int | None:
    for index, row in enumerate(rows):
        normalized = [normalize_header(cell) for cell in row]
        has_reference = any(is_reference_header(cell) for cell in normalized)
        has_name = any(is_name_header(cell) for cell in normalized)
        has_identity = any(is_cas_header(cell) or is_ec_header(cell) for cell in normalized)
        if has_reference and (has_name or has_identity):
            return index
    return None


def classify_columns(header: list[str]) -> dict[str, int]:
    columns: dict[str, int] = {}
    normalized = [normalize_header(cell) for cell in header]

    for index, cell in enumerate(normalized):
        if "reference_no" not in columns and is_reference_header(cell):
            columns["reference_no"] = index
        elif "cas_number_raw" not in columns and is_cas_header(cell):
            columns["cas_number_raw"] = index
        elif "ec_number_raw" not in columns and is_ec_header(cell):
            columns["ec_number_raw"] = index
        elif "max_concentration_raw" not in columns and is_max_concentration_header(cell):
            columns["max_concentration_raw"] = index
        elif "warning_label" not in columns and is_warning_header(cell):
            columns["warning_label"] = index
        elif "note_raw" not in columns and is_note_header(cell):
            columns["note_raw"] = index
        elif "product_body_scope" not in columns and is_product_body_header(cell):
            columns["product_body_scope"] = index
        elif "product_scope" not in columns and is_product_scope_header(cell):
            columns["product_scope"] = index
        elif "body_part_scope" not in columns and is_body_part_header(cell):
            columns["body_part_scope"] = index
        elif "conditions_raw" not in columns and is_conditions_header(cell):
            columns["conditions_raw"] = index

    for index, cell in enumerate(normalized):
        if "ingredient_name_raw" not in columns and is_name_header(cell):
            columns["ingredient_name_raw"] = index
    return columns


def item_from_row(
    row: list[str],
    columns: dict[str, int],
    source: dict[str, Any],
    annex: str | None,
    status: str,
) -> RegulatoryItem | None:
    reference_no = value_at(row, columns.get("reference_no"))
    ingredient_name = value_at(row, columns.get("ingredient_name_raw"))
    if not reference_no and not ingredient_name:
        return None

    product_scope = value_at(row, columns.get("product_scope"))
    body_part_scope = value_at(row, columns.get("body_part_scope"))
    combined_scope = value_at(row, columns.get("product_body_scope"))
    if combined_scope and not (product_scope or body_part_scope):
        product_scope, body_part_scope = split_product_body_scope(combined_scope)

    cas_number = value_at(row, columns.get("cas_number_raw"))
    ec_number = value_at(row, columns.get("ec_number_raw"))
    max_concentration = value_at(row, columns.get("max_concentration_raw"))
    conditions = value_at(row, columns.get("conditions_raw"))
    warning = value_at(row, columns.get("warning_label"))
    note = value_at(row, columns.get("note_raw"))
    row_hash = official_row_hash(
        source["source_id"],
        annex,
        status,
        reference_no,
        ingredient_name,
        cas_number,
        ec_number,
        max_concentration,
        product_scope,
        body_part_scope,
        conditions,
        warning,
        note,
    )
    return RegulatoryItem(
        jurisdiction="EU",
        source_code=source["source_id"],
        annex_or_part=annex,
        reference_no=reference_no,
        ingredient_name_raw=ingredient_name or reference_no or "EU CosIng annex row",
        cas_number_raw=cas_number,
        ec_number_raw=ec_number,
        status=status,
        max_concentration_raw=max_concentration,
        product_scope=product_scope,
        body_part_scope=body_part_scope,
        warning_label=warning,
        conditions_raw=conditions,
        note_raw=note,
        official_row_hash=row_hash,
    )


def values_by_index(row: list[str], width: int) -> list[str]:
    padded = list(row[:width])
    padded.extend([""] * (width - len(padded)))
    return padded


def value_at(row: list[str], index: int | None) -> str | None:
    if index is None or index >= len(row):
        return None
    return clean_cell(row[index]) or None


def clean_cell(value: str | None) -> str:
    return " ".join((value or "").replace("\ufeff", "").split())


def normalize_header(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", ascii_value.lower())).strip()


def is_reference_header(value: str) -> bool:
    return (
        "reference number" in value
        or value in {"ref no", "reference no", "order no", "order number", "no"}
        or ("reference" in value and "number" in value)
    )


def is_name_header(value: str) -> bool:
    if "substance identification" in value:
        return True
    if "chemical name" in value or "ingredient name" in value or "inci name" in value:
        return True
    return value in {"name", "substance", "colour index number", "color index number"}


def is_cas_header(value: str) -> bool:
    return ("cas" in value and "number" in value) or value in {"cas", "cas no", "cas n"}


def is_ec_header(value: str) -> bool:
    return (
        "ec number" in value
        or "einecs" in value
        or "elincs" in value
        or value in {"ec", "ec no"}
        or ("ec" in value and "number" in value)
    )


def is_max_concentration_header(value: str) -> bool:
    return "maximum concentration" in value or "max concentration" in value or "maximum authorised concentration" in value


def is_product_body_header(value: str) -> bool:
    return ("product" in value or "type of product" in value) and "bod" in value


def is_product_scope_header(value: str) -> bool:
    return "field of application" in value or "product type" in value or "type of product" in value


def is_body_part_header(value: str) -> bool:
    return "body part" in value or "body parts" in value


def is_warning_header(value: str) -> bool:
    return "warning" in value or "wording of conditions" in value


def is_conditions_header(value: str) -> bool:
    return value == "other" or "other conditions" in value or value == "conditions" or "restrictions" in value


def is_note_header(value: str) -> bool:
    return value in {"note", "notes", "remarks", "remark"}


def split_product_body_scope(value: str) -> tuple[str | None, str | None]:
    if "," not in value:
        return value, None
    product, body = value.split(",", 1)
    return clean_cell(product) or None, clean_cell(body) or None


def looks_like_same_header(row: list[str], header: list[str]) -> bool:
    row_normalized = [normalize_header(cell) for cell in row[: len(header)]]
    header_normalized = [normalize_header(cell) for cell in header]
    return row_normalized == header_normalized


def annex_code(source: dict[str, Any]) -> str | None:
    if source.get("annex"):
        return str(source["annex"]).strip().upper()
    source_id = str(source.get("source_id") or "")
    suffix = source_id.rsplit("_", 1)[-1].strip().upper()
    return suffix or None


def official_row_hash(*parts: str | None) -> str:
    normalized = "\x1f".join(part or "" for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
