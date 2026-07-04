from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from . import db
from .html_links import same_origin_links
from .timeutil import utc_day


USER_AGENT = "official-reg-monitor/0.1 (+source-first cosmetic regulation monitoring)"


def safe_ext(content_type: str | None, url: str) -> str:
    lowered = (content_type or "").lower()
    url_lower = url.lower()
    if "pdf" in lowered or url_lower.endswith(".pdf"):
        return ".pdf"
    if "json" in lowered or url_lower.endswith(".json"):
        return ".json"
    if "xml" in lowered or url_lower.endswith(".xml"):
        return ".xml"
    if "csv" in lowered or url_lower.endswith(".csv"):
        return ".csv"
    if "excel" in lowered or url_lower.endswith((".xls", ".xlsx")):
        return ".xlsx"
    if "javascript" in lowered or url_lower.endswith(".js"):
        return ".js"
    if "css" in lowered or url_lower.endswith(".css"):
        return ".css"
    return ".html"


def due_for_fetch(source: dict[str, Any], last_success_at: dt.datetime | None, now: dt.datetime) -> bool:
    if last_success_at is None:
        return True
    cadence = (source.get("cadence") or "daily").lower()
    cadence_hours = {
        "hourly": 1,
        "daily": 24,
        "weekly": 24 * 7,
        "monthly": 24 * 30,
    }.get(cadence, 24)
    return (now - last_success_at) >= dt.timedelta(hours=cadence_hours)


def fetch_url(url: str, out_dir: Path, source_id: str) -> dict[str, Any]:
    out_dir = out_dir.expanduser().resolve()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
        content_type = resp.headers.get("content-type")
        result = {
            "url": url,
            "http_status": getattr(resp, "status", 200),
            "content_type": content_type,
            "etag": resp.headers.get("etag"),
            "last_modified": resp.headers.get("last-modified"),
            "body": body,
        }

    sha = hashlib.sha256(body).hexdigest()
    ext = safe_ext(result["content_type"], url)
    source_dir = out_dir / source_id / utc_day()
    source_dir.mkdir(parents=True, exist_ok=True)
    path = source_dir / f"{sha}{ext}"
    if not path.exists():
        path.write_bytes(body)

    result.update(
        {
            "sha256": sha,
            "byte_size": len(body),
            "path": str(path),
        }
    )
    return result


def monitor_source(
    conn: sqlite3.Connection,
    source: dict[str, Any],
    out_dir: str | Path,
    *,
    force: bool = False,
    respect_cadence: bool = True,
    capture_assets: bool = True,
) -> dict[str, Any]:
    out_path = Path(out_dir)
    if respect_cadence and not force:
        last_success = db.latest_success_at(conn, source["source_id"])
        if not due_for_fetch(source, last_success, dt.datetime.now(dt.timezone.utc)):
            return {
                "source_id": source["source_id"],
                "ok": True,
                "skipped": True,
                "changed": False,
                "reason": f"not due for cadence={source.get('cadence') or 'daily'}",
            }

    old_hash = db.previous_hash(conn, source["source_id"])
    try:
        result = fetch_url(source["url"], out_path, source["source_id"])
        changed = old_hash != result["sha256"]
        snapshot_id = db.record_snapshot(conn, source, result, changed)
        assets = []
        if capture_assets and source.get("capture_assets", False):
            content_type = (result.get("content_type") or "").lower()
            if "html" in content_type:
                for asset_url in same_origin_links(source["url"], result["body"]):
                    try:
                        asset = fetch_url(asset_url, out_path / "_assets", source["source_id"])
                        db.record_asset(conn, snapshot_id, asset)
                        assets.append({"url": asset_url, "ok": True, "path": asset["path"]})
                    except (urllib.error.URLError, TimeoutError, OSError) as exc:
                        db.record_asset(conn, snapshot_id, {"url": asset_url}, error=str(exc))
                        assets.append({"url": asset_url, "ok": False, "error": str(exc)})
        return {
            "source_id": source["source_id"],
            "ok": True,
            "changed": changed,
            "sha256": result["sha256"],
            "bytes": result["byte_size"],
            "path": result["path"],
            "asset_count": len(assets),
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        db.record_snapshot(conn, source, {}, False, error=str(exc))
        return {
            "source_id": source["source_id"],
            "ok": False,
            "changed": False,
            "error": str(exc),
        }
