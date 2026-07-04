from __future__ import annotations

from pathlib import Path
from typing import Any

from . import ParseResult


class JpMhlwPdfParser:
    version = "0.1.0"

    def parse(self, path: Path, source: dict[str, Any], snapshot) -> ParseResult:
        if path.suffix.lower() != ".pdf":
            return ParseResult(status="error", warnings=[f"Expected PDF, got {path.suffix}"])
        return ParseResult(
            status="skipped",
            warnings=[
                "PDF snapshot captured. Structured JP parsing requires a PDF table extractor such as pdfplumber.",
                f"Raw PDF is preserved at {path}.",
            ],
        )

