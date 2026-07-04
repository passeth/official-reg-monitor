from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RegulatoryItem:
    jurisdiction: str
    source_code: str
    ingredient_name_raw: str
    status: str
    official_row_hash: str
    annex_or_part: str | None = None
    reference_no: str | None = None
    cas_number_raw: str | None = None
    ec_number_raw: str | None = None
    max_percent: float | None = None
    max_concentration_raw: str | None = None
    product_scope: str | None = None
    body_part_scope: str | None = None
    warning_label: str | None = None
    conditions_raw: str | None = None
    note_raw: str | None = None


@dataclass
class ParseResult:
    status: str
    records_parsed: int = 0
    records_inserted: int = 0
    warnings: list[str] = field(default_factory=list)
    items: list[RegulatoryItem] = field(default_factory=list)
