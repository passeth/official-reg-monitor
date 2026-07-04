from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from . import ParseResult, RegulatoryItem


class UsEcfrXmlParser:
    version = "0.1.0"
    cosmetic_parts = {"700", "701", "710", "720", "740"}
    color_additive_parts = {"70", "71", "73", "74", "80", "81", "82"}

    def parse(self, path: Path, source: dict[str, Any], snapshot) -> ParseResult:
        if path.suffix.lower() != ".xml":
            return ParseResult(
                status="skipped",
                warnings=[f"US eCFR parser expects XML; got {path.name}. Update source URL to bulk XML if needed."],
            )
        root = ET.parse(path).getroot()
        items: list[RegulatoryItem] = []
        detected_parts: list[str] = []
        for node in root.iter():
            part_no = node.attrib.get("N")
            if node.attrib.get("TYPE") != "PART" or part_no not in self.cosmetic_related_parts:
                continue
            part_head = direct_child_text(node, "HEAD")
            detected_parts.append(f"{part_no} {part_head}".strip())
            for section in node.iter():
                if section.attrib.get("TYPE") != "SECTION":
                    continue
                reference_no = section.attrib.get("N") or None
                section_head = direct_child_text(section, "HEAD") or reference_no or f"Part {part_no} section"
                section_text = collapse_text(section.itertext())
                row_hash = official_row_hash(
                    source["source_id"],
                    part_no,
                    reference_no,
                    section_head,
                    section_text,
                )
                items.append(
                    RegulatoryItem(
                        jurisdiction=source.get("jurisdiction") or "US",
                        source_code=source["source_id"],
                        annex_or_part=part_no,
                        reference_no=reference_no,
                        ingredient_name_raw=section_head,
                        status="section",
                        product_scope=part_head,
                        conditions_raw=section_text,
                        note_raw="Section-level eCFR record; ingredient extraction is not yet applied.",
                        official_row_hash=row_hash,
                    )
                )
        warnings = []
        if detected_parts:
            warnings.append("Detected US eCFR cosmetic parts: " + ", ".join(detected_parts) + ".")
        if not items:
            warnings.append(
                "No section-level regulatory items were found in cosmetic Parts 700, 701, 710, 720, 740 "
                "or color additive Parts 70, 71, 73, 74, 80, 81, 82."
            )
        return ParseResult(
            status="ok",
            records_parsed=len(items),
            warnings=warnings,
            items=items,
        )

    @property
    def cosmetic_related_parts(self) -> set[str]:
        return self.cosmetic_parts | self.color_additive_parts


def direct_child_text(node: ET.Element, tag: str) -> str:
    for child in node:
        if child.tag == tag:
            return collapse_text(child.itertext())
    return ""


def collapse_text(parts) -> str:
    return " ".join(" ".join(parts).split())


def official_row_hash(*parts: str | None) -> str:
    normalized = "\x1f".join(part or "" for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
