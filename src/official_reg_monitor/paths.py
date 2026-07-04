from __future__ import annotations

from importlib import resources
from pathlib import Path


def bundled_data_path(name: str) -> Path:
    return Path(str(resources.files("official_reg_monitor").joinpath("data", name)))

