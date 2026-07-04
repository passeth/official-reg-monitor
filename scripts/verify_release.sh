#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(python3 - "$ROOT" <<'PY'
from pathlib import Path
import re
import sys

text = (Path(sys.argv[1]) / "src/official_reg_monitor/__init__.py").read_text()
match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
if not match:
    raise SystemExit("Could not find __version__")
print(match.group(1))
PY
)"
RELEASE_DIR="${1:-$ROOT/release}"
BUNDLE="$RELEASE_DIR/official-reg-monitor-$VERSION.bundle"
CLONE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/official-reg-monitor-verify.XXXXXX")"
VENV_DIR="$(mktemp -d "${TMPDIR:-/tmp}/official-reg-monitor-wheel.XXXXXX")"

test -f "$BUNDLE"

git clone "$BUNDLE" "$CLONE_DIR/repo"
cd "$CLONE_DIR/repo"
test "$(git branch --show-current)" = "main"
make test
PYTHONPATH=src python3 -m official_reg_monitor.cli doctor --db "$CLONE_DIR/doctor.sqlite"

python3 -m venv "$VENV_DIR/venv"
"$VENV_DIR/venv/bin/pip" install "$RELEASE_DIR/official_reg_monitor-$VERSION-py3-none-any.whl"
"$VENV_DIR/venv/bin/official-reg-monitor" doctor --db "$CLONE_DIR/installed-doctor.sqlite"

echo "Release verification passed for $RELEASE_DIR"

