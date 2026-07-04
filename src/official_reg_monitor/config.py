from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import bundled_data_path


def default_registry_path() -> Path:
    return bundled_data_path("sources.registry.json")


def read_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = Path(path) if path else default_registry_path()
    with registry_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def select_sources(registry: dict[str, Any], source_id: str | None = None) -> list[dict[str, Any]]:
    sources = registry["sources"]
    if not source_id:
        return sources
    selected = [source for source in sources if source["source_id"] == source_id]
    if not selected:
        raise ValueError(f"Unknown source_id: {source_id}")
    return selected

