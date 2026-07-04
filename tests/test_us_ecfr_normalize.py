from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "US_ECFR_TITLE21_COSMETICS"


def run_cli(*args: str, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, "-m", "official_reg_monitor.cli", *args],
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={"PYTHONPATH": str(ROOT / "src")},
    )


def write_registry(tmp_path: Path, source_file: Path) -> Path:
    registry = {
        "version": 1,
        "created_at": "2026-07-04",
        "sources": [
            {
                "source_id": SOURCE_ID,
                "jurisdiction": "US",
                "name": "eCFR Title 21 bulk XML fixture",
                "official_owner": "U.S. Government Publishing Office / eCFR",
                "url": source_file.as_uri(),
                "kind": "xml_bulk",
                "cadence": "daily",
                "parser": "us_ecfr",
                "notes": "Test fixture for cosmetic eCFR section extraction.",
            }
        ],
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return registry_path


def fetch_and_normalize(tmp_path: Path, source_xml: str):
    source_file = tmp_path / "ECFR-title21.xml"
    source_file.write_text(source_xml, encoding="utf-8")
    registry_path = write_registry(tmp_path, source_file)
    db_path = tmp_path / "monitoring.sqlite"
    fetch = run_cli(
        "fetch",
        "--registry",
        str(registry_path),
        "--db",
        str(db_path),
        "--out",
        str(tmp_path / "snapshots"),
        "--source",
        SOURCE_ID,
        "--force",
        "--no-assets",
        cwd=tmp_path,
    )
    normalize = run_cli(
        "normalize",
        "--registry",
        str(registry_path),
        "--db",
        str(db_path),
        "--source",
        SOURCE_ID,
        cwd=tmp_path,
    )
    return fetch, normalize, db_path


class UsEcfrNormalizeTest(unittest.TestCase):
    def test_us_ecfr_sections_insert_regulatory_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fetch, normalize, db_path = fetch_and_normalize(
                tmp_path,
                """
                <ECFRDOC>
                  <DIV5 TYPE="PART" N="74">
                    <HEAD>PART 74-LISTING OF COLOR ADDITIVES SUBJECT TO CERTIFICATION</HEAD>
                    <DIV8 TYPE="SECTION" N="§ 74.2602">
                      <HEAD>§ 74.2602 D&amp;C Red No. 6.</HEAD>
                      <P>This color additive may be safely used in cosmetics under listed conditions.</P>
                    </DIV8>
                  </DIV5>
                  <DIV5 TYPE="PART" N="700">
                    <HEAD>PART 700-GENERAL</HEAD>
                    <DIV8 TYPE="SECTION" N="§ 700.3">
                      <HEAD>§ 700.3 Definitions.</HEAD>
                      <P>Terms used in cosmetic regulations.</P>
                    </DIV8>
                  </DIV5>
                  <DIV5 TYPE="PART" N="701">
                    <HEAD>PART 701-COSMETIC LABELING</HEAD>
                    <DIV8 TYPE="SECTION" N="§ 701.3">
                      <HEAD>§ 701.3 Designation of ingredients.</HEAD>
                      <P>Ingredient declarations must follow applicable labeling rules.</P>
                    </DIV8>
                  </DIV5>
                  <DIV5 TYPE="PART" N="999">
                    <HEAD>PART 999-OUT OF SCOPE</HEAD>
                    <DIV8 TYPE="SECTION" N="999.1"><HEAD>Ignore me.</HEAD></DIV8>
                  </DIV5>
                </ECFRDOC>
                """,
            )
            self.assertEqual(fetch.returncode, 0, fetch.stderr + fetch.stdout)
            self.assertEqual(normalize.returncode, 0, normalize.stderr + normalize.stdout)
            payload = json.loads(normalize.stdout)
            self.assertEqual(payload["results"][0]["status"], "ok")
            self.assertEqual(payload["results"][0]["records_inserted"], 3)

            repeat = run_cli(
                "normalize",
                "--registry",
                str(tmp_path / "registry.json"),
                "--db",
                str(db_path),
                "--source",
                SOURCE_ID,
                cwd=tmp_path,
            )
            self.assertEqual(repeat.returncode, 0, repeat.stderr + repeat.stdout)

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            self.assertEqual(conn.execute("SELECT count(*) FROM source_versions").fetchone()[0], 1)
            rows = conn.execute(
                """
                SELECT source_code, annex_or_part, reference_no, ingredient_name_raw, status
                FROM regulatory_items
                ORDER BY reference_no
                """
            ).fetchall()
            self.assertEqual(len(rows), 3)
            self.assertEqual({row["annex_or_part"] for row in rows}, {"74", "700", "701"})
            self.assertEqual({row["source_code"] for row in rows}, {SOURCE_ID})
            self.assertEqual({row["status"] for row in rows}, {"section"})
            self.assertIn("§ 700.3", {row["reference_no"] for row in rows})
            latest_run = conn.execute(
                "SELECT status, records_inserted FROM parser_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            self.assertEqual(
                latest_run[:],
                ("ok", 3),
            )

    def test_us_ecfr_no_cosmetic_parts_records_warning_without_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fetch, normalize, db_path = fetch_and_normalize(
                tmp_path,
                """
                <ECFRDOC>
                  <DIV5 TYPE="PART" N="999">
                    <HEAD>PART 999-OUT OF SCOPE</HEAD>
                    <DIV8 TYPE="SECTION" N="999.1"><HEAD>Ignore me.</HEAD></DIV8>
                  </DIV5>
                </ECFRDOC>
                """,
            )
            self.assertEqual(fetch.returncode, 0, fetch.stderr + fetch.stdout)
            self.assertEqual(normalize.returncode, 0, normalize.stderr + normalize.stdout)
            payload = json.loads(normalize.stdout)
            self.assertEqual(payload["results"][0]["status"], "ok")
            self.assertEqual(payload["results"][0]["records_inserted"], 0)
            self.assertTrue(payload["results"][0]["warnings"])

            conn = sqlite3.connect(db_path)
            self.assertEqual(conn.execute("SELECT count(*) FROM regulatory_items").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT count(*) FROM source_versions").fetchone()[0], 0)
            self.assertEqual(
                conn.execute("SELECT status, records_inserted FROM parser_runs").fetchone()[:],
                ("ok", 0),
            )


if __name__ == "__main__":
    unittest.main()
