from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import read_registry
from .db import connect, upsert_sources


def command_status(command: list[str]) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if not executable:
        return {"available": False}
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return {
        "available": True,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def doctor(registry_path: str | None, db_path: str) -> dict[str, Any]:
    checks: dict[str, Any] = {
        "python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
        "sqlite": {
            "module_version": sqlite3.sqlite_version,
        },
    }

    registry = read_registry(registry_path)
    sources = registry.get("sources", [])
    checks["registry"] = {
        "ok": bool(sources),
        "source_count": len(sources),
        "jurisdictions": sorted({source.get("jurisdiction") for source in sources if source.get("jurisdiction")}),
    }

    conn = connect(db_path)
    upsert_sources(conn, registry)
    source_count = conn.execute("SELECT count(*) FROM sources").fetchone()[0]
    snapshot_count = conn.execute("SELECT count(*) FROM source_snapshots").fetchone()[0]
    checks["database"] = {
        "ok": source_count == len(sources),
        "path": str(Path(db_path).expanduser().resolve()),
        "source_count": source_count,
        "snapshot_count": snapshot_count,
    }

    checks["git"] = command_status(["git", "--version"])
    checks["gh"] = command_status(["gh", "auth", "status"])
    checks["ok"] = checks["registry"]["ok"] and checks["database"]["ok"] and checks["git"]["available"]
    return checks

