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
OUT="${1:-$ROOT/release}"

mkdir -p "$OUT" "$ROOT/dist"
cd "$ROOT"

python3 -m pip wheel . --no-deps --no-build-isolation -w dist
git bundle create "$OUT/official-reg-monitor-$VERSION.bundle" --all
git archive --format=tar.gz -o "$OUT/official-reg-monitor-$VERSION.tar.gz" HEAD
cp "$ROOT/dist/official_reg_monitor-$VERSION-py3-none-any.whl" "$OUT/"

(
  cd "$OUT"
  shasum -a 256 \
    "official-reg-monitor-$VERSION.bundle" \
    "official-reg-monitor-$VERSION.tar.gz" \
    "official_reg_monitor-$VERSION-py3-none-any.whl" \
    > SHA256SUMS
)

echo "Release files written to $OUT"

