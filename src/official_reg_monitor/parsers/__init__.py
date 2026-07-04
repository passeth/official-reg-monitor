from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParseResult:
    status: str
    records_parsed: int = 0
    records_inserted: int = 0
    warnings: list[str] = field(default_factory=list)


def get_parser(name: str):
    from .generic import GenericParser
    from .jp_mhlw_pdf import JpMhlwPdfParser
    from .us_ecfr_xml import UsEcfrXmlParser

    if name == "us_ecfr":
        return UsEcfrXmlParser()
    if name == "jp_mhlw_pdf":
        return JpMhlwPdfParser()
    return GenericParser(name)
