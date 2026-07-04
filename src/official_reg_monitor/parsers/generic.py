from __future__ import annotations

from pathlib import Path
from typing import Any

from . import ParseResult


class GenericParser:
    version = "0.1.0"

    def __init__(self, name: str) -> None:
        self.name = name

    def parse(self, path: Path, source: dict[str, Any], snapshot) -> ParseResult:
        suffix = path.suffix.lower()
        warnings = [
            f"No structured parser is implemented for parser={self.name}.",
            f"Raw source is preserved at {path}.",
        ]
        if suffix in {".html", ".htm"}:
            text = path.read_text(errors="replace")
            if "<table" not in text.lower():
                warnings.append("HTML snapshot contains no static table; source may require API or rendered-app capture.")
        return ParseResult(status="skipped", warnings=warnings)

