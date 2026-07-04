from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs}
        if tag.lower() == "script" and attr_map.get("src"):
            self.links.append(attr_map["src"] or "")
        elif tag.lower() == "link" and attr_map.get("href"):
            rel = (attr_map.get("rel") or "").lower()
            href = attr_map.get("href") or ""
            if any(token in rel for token in ["stylesheet", "modulepreload", "preload"]):
                self.links.append(href)
        elif tag.lower() == "a" and attr_map.get("href", "").lower().endswith((".pdf", ".xls", ".xlsx", ".csv", ".xml", ".json")):
            self.links.append(attr_map.get("href") or "")


def same_origin_links(base_url: str, html: bytes) -> list[str]:
    parser = LinkExtractor()
    parser.feed(html.decode("utf-8", errors="replace"))
    base = urlparse(base_url)
    result: list[str] = []
    seen: set[str] = set()
    for link in parser.links:
        url = urljoin(base_url, link)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != base.netloc:
            continue
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result

