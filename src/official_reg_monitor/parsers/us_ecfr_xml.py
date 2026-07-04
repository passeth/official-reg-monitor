from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from . import ParseResult


class UsEcfrXmlParser:
    version = "0.1.0"

    def parse(self, path: Path, source: dict[str, Any], snapshot) -> ParseResult:
        if path.suffix.lower() != ".xml":
            return ParseResult(
                status="skipped",
                warnings=[f"US eCFR parser expects XML; got {path.name}. Update source URL to bulk XML if needed."],
            )
        root = ET.parse(path).getroot()
        parts = []
        cosmetic_parts = {"700", "701", "710", "720", "740"}
        for node in root.iter():
            if node.attrib.get("TYPE") == "PART" and node.attrib.get("N") in cosmetic_parts:
                head = ""
                for child in node:
                    if child.tag == "HEAD":
                        head = "".join(child.itertext()).strip()
                        break
                parts.append({"part": node.attrib.get("N"), "head": head})
        return ParseResult(
            status="ok",
            records_parsed=len(parts),
            records_inserted=0,
            warnings=[
                "US eCFR XML was readable. Detected cosmetic-related parts: "
                + ", ".join(f"{part['part']} {part['head']}" for part in parts)
                + ". Section-level regulatory item insertion is not enabled yet.",
            ],
        )
