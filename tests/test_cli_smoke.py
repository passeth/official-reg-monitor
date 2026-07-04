from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, "-m", "official_reg_monitor.cli", *args],
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={"PYTHONPATH": str(ROOT / "src")},
    )


class CliSmokeTest(unittest.TestCase):
    def test_help(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("official-reg-monitor", result.stdout)

    def test_doctor(self):
        result = run_cli("doctor")
        self.assertIn(result.returncode, {0, 1})
        payload = json.loads(result.stdout)
        self.assertIn("python", payload)
        self.assertIn("registry", payload)
        self.assertTrue(payload["registry"]["ok"])

    def test_fetch_file_source(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw = tmp_path / "source.html"
            raw.write_text("<html><body><p>official source fixture</p></body></html>", encoding="utf-8")
            registry = {
                "version": 1,
                "created_at": "2026-07-04",
                "sources": [
                    {
                        "source_id": "TEST_SOURCE",
                        "jurisdiction": "TEST",
                        "name": "Test fixture",
                        "official_owner": "Local",
                        "url": raw.as_uri(),
                        "kind": "html",
                        "cadence": "daily",
                        "parser": "generic",
                    }
                ],
            }
            registry_path = tmp_path / "registry.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            result = run_cli(
                "fetch",
                "--registry",
                str(registry_path),
                "--db",
                str(tmp_path / "monitoring.sqlite"),
                "--out",
                str(tmp_path / "snapshots"),
                "--force",
                "--no-assets",
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["results"][0]["ok"])
            self.assertTrue(payload["results"][0]["changed"])
            self.assertTrue(Path(payload["results"][0]["path"]).is_absolute())

            normalize = run_cli(
                "normalize",
                "--registry",
                str(registry_path),
                "--db",
                str(tmp_path / "monitoring.sqlite"),
                cwd=ROOT,
            )
            self.assertEqual(normalize.returncode, 0, normalize.stderr + normalize.stdout)
            normalize_payload = json.loads(normalize.stdout)
            self.assertEqual(normalize_payload["results"][0]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
