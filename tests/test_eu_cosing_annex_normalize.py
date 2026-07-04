from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from official_reg_monitor.parsers import get_parser


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "EU_COSING_ANNEX_VI"


def run_cli(*args: str, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, "-m", "official_reg_monitor.cli", *args],
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={"PYTHONPATH": str(ROOT / "src")},
    )


def write_registry(tmp_path: Path, source_file: Path, *, annex: str = "VI", source_id: str = SOURCE_ID) -> Path:
    registry = {
        "version": 1,
        "created_at": "2026-07-04",
        "sources": [
            {
                "source_id": source_id,
                "jurisdiction": "EU",
                "name": f"EU CosIng Annex {annex} fixture",
                "official_owner": "European Commission",
                "url": source_file.as_uri(),
                "kind": "csv_export",
                "cadence": "daily",
                "parser": "eu_cosing_annex",
                "annex": annex,
            }
        ],
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return registry_path


def annex_vi_csv() -> str:
    return (
        '"File creation date: 04/07/2026"\n'
        '"ANNEX VI","Last update: 29/06/2026"\n'
        '"LIST OF UV FILTERS ALLOWED IN COSMETIC PRODUCTS"\n'
        '"Reference number","Substance identification","Chemical name/INN/XAN","CAS Number",'
        '"EC Number","Product type, body parts","Maximum concentration in ready for use preparation",'
        '"Other","Wording of conditions of use and warnings"\n'
        '"22","Titanium dioxide","Titanium dioxide","13463-67-7","236-675-5",'
        '"Sunscreen products, face and body","25 %","Not to be used in applications that may lead to exposure '
        "of the end-user's lungs by inhalation.\n"
        'Allowed nano form under listed characteristics.","Avoid inhalation, children under 3 years"\n'
    )


class EuCosingAnnexNormalizeTest(unittest.TestCase):
    def test_parser_lookup_extracts_annex_rows_and_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "annex-vi.csv"
            source_file.write_text(annex_vi_csv(), encoding="utf-8")
            parser = get_parser("eu_cosing_annex")
            result = parser.parse(
                source_file,
                {
                    "source_id": SOURCE_ID,
                    "jurisdiction": "EU",
                    "annex": "VI",
                },
                snapshot=None,
            )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.records_parsed, 1)
        [item] = result.items
        self.assertEqual(item.jurisdiction, "EU")
        self.assertEqual(item.source_code, SOURCE_ID)
        self.assertEqual(item.annex_or_part, "VI")
        self.assertEqual(item.status, "uv_filter")
        self.assertEqual(item.reference_no, "22")
        self.assertEqual(item.ingredient_name_raw, "Titanium dioxide")
        self.assertEqual(item.cas_number_raw, "13463-67-7")
        self.assertEqual(item.ec_number_raw, "236-675-5")
        self.assertEqual(item.product_scope, "Sunscreen products")
        self.assertEqual(item.body_part_scope, "face and body")
        self.assertEqual(item.max_concentration_raw, "25 %")
        self.assertIn("exposure of the end-user's lungs", item.conditions_raw)
        self.assertIn("Allowed nano form", item.conditions_raw)
        self.assertEqual(item.warning_label, "Avoid inhalation, children under 3 years")
        self.assertEqual(len(item.official_row_hash), 64)

    def test_annex_codes_map_to_regulatory_statuses(self):
        expected = {
            "II": "prohibited",
            "III": "restricted",
            "IV": "colorant",
            "V": "preservative",
            "VI": "uv_filter",
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_file = tmp_path / "annex.csv"
            source_file.write_text(
                '"Reference number","Substance identification","CAS Number","EC Number"\n'
                '"1","Example substance","50-00-0","200-001-8"\n',
                encoding="utf-8",
            )
            parser = get_parser("eu_cosing_annex")
            for annex, status in expected.items():
                result = parser.parse(
                    source_file,
                    {
                        "source_id": f"EU_COSING_ANNEX_{annex}",
                        "jurisdiction": "EU",
                        "annex": annex,
                    },
                    snapshot=None,
                )
                self.assertEqual(result.status, "ok")
                self.assertEqual(result.items[0].status, status)

    def test_metadata_only_csv_is_ok_with_warning_and_no_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "annex-ii.csv"
            source_file.write_text(
                '"File creation date: 04/07/2026"\n"ANNEX II","Last update: 29/06/2026"\n',
                encoding="utf-8",
            )
            result = get_parser("eu_cosing_annex").parse(
                source_file,
                {
                    "source_id": "EU_COSING_ANNEX_II",
                    "jurisdiction": "EU",
                    "annex": "II",
                },
                snapshot=None,
            )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.records_parsed, 0)
        self.assertEqual(result.items, [])
        self.assertTrue(result.warnings)

    def test_cli_fetch_and_normalize_inserts_annex_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_file = tmp_path / "annex-vi-export-csv"
            source_file.write_text(annex_vi_csv(), encoding="utf-8")
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

            self.assertEqual(fetch.returncode, 0, fetch.stderr + fetch.stdout)
            fetch_payload = json.loads(fetch.stdout)
            self.assertTrue(fetch_payload["results"][0]["path"].endswith(".csv"))
            self.assertEqual(normalize.returncode, 0, normalize.stderr + normalize.stdout)
            payload = json.loads(normalize.stdout)
            self.assertEqual(payload["results"][0]["status"], "ok")
            self.assertEqual(payload["results"][0]["records_inserted"], 1)

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT jurisdiction, source_code, annex_or_part, reference_no, ingredient_name_raw,
                       cas_number_raw, ec_number_raw, status, max_concentration_raw,
                       product_scope, body_part_scope, warning_label, conditions_raw
                FROM regulatory_items
                """
            ).fetchone()
            self.assertEqual(row["jurisdiction"], "EU")
            self.assertEqual(row["source_code"], SOURCE_ID)
            self.assertEqual(row["annex_or_part"], "VI")
            self.assertEqual(row["reference_no"], "22")
            self.assertEqual(row["ingredient_name_raw"], "Titanium dioxide")
            self.assertEqual(row["cas_number_raw"], "13463-67-7")
            self.assertEqual(row["ec_number_raw"], "236-675-5")
            self.assertEqual(row["status"], "uv_filter")
            self.assertEqual(row["max_concentration_raw"], "25 %")
            self.assertEqual(row["product_scope"], "Sunscreen products")
            self.assertEqual(row["body_part_scope"], "face and body")
            self.assertIn("Allowed nano form", row["conditions_raw"])
            self.assertEqual(row["warning_label"], "Avoid inhalation, children under 3 years")
            conn.close()


if __name__ == "__main__":
    unittest.main()
