from __future__ import annotations

from .models import ParseResult, RegulatoryItem


def get_parser(name: str):
    from .generic import GenericParser
    from .jp_mhlw_pdf import JpMhlwPdfParser
    from .us_ecfr_xml import UsEcfrXmlParser

    if name == "us_ecfr":
        return UsEcfrXmlParser()
    if name == "jp_mhlw_pdf":
        return JpMhlwPdfParser()
    return GenericParser(name)


__all__ = ["ParseResult", "RegulatoryItem", "get_parser"]
