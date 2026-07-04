# Official Reg Monitor

Source-first monitoring for official cosmetic regulation documents.

This project keeps the official source layer separate from derived screening databases. It fetches official pages/files, stores immutable SHA-256 snapshots, records version/change metadata in SQLite, and provides a parser interface for source-specific normalization.

## Install

```bash
git clone <your-repo-url> official-reg-monitor
cd official-reg-monitor
python3 -m pip install -e .
```

Local development without installation:

```bash
PYTHONPATH=src python3 -m official_reg_monitor.cli --version
```

## Fetch Official Sources

Fetch all configured sources now:

```bash
official-reg-monitor fetch --force
```

Fetch one source:

```bash
official-reg-monitor fetch --source EU_COSING_ANNEX_II --force
```

Default output:

- `monitoring.sqlite`: source registry, fetch attempts, asset captures, parser runs.
- `snapshots/<source_id>/<date>/<sha>.<ext>`: immutable raw source snapshots.
- `snapshots/_assets/...`: same-origin linked assets when `capture_assets` is enabled.

The legacy wrapper still works:

```bash
python3 monitor.py --force
```

## Status

```bash
official-reg-monitor status
```

## Doctor

Check Python, SQLite, registry, local DB, git, and GitHub CLI readiness:

```bash
official-reg-monitor doctor
```

## Normalize

```bash
official-reg-monitor normalize
```

The parser layer is intentionally source-specific. Sites do not expose identical tables:

- EU CosIng is an Angular app shell, so static HTML snapshots do not contain the Annex table. Asset capture is enabled so the app bundle can be audited and API/download endpoints can be added.
- US eCFR uses GPO bulk XML in this registry to avoid HTML interstitials.
- JP MHLW is a PDF source and needs PDF table extraction before row-level normalization.
- KR law.go.kr, ASEAN, CN, and RU/EAEU require dedicated parsers or more precise official document URLs.

Current normalization support:

- `us_ecfr`: verifies the XML can be read and records a parser run.
- `jp_mhlw_pdf`: records a PDF parser run as skipped until PDF table extraction is enabled.
- Other parsers: preserve provenance and record a structured `skipped` parser run.

## Schedule On macOS

```bash
./install_launchd.sh
```

The installer uses the current checkout path, so it works after cloning to any local directory.

Logs:

```text
logs/monitor.log
logs/monitor.err.log
```

## Test

```bash
make test
```

## Build

```bash
python3 -m pip wheel . --no-deps --no-build-isolation -w dist
```

## Git Distribution

```bash
git init
git add .
git commit -m "Initial official regulation monitor"
```

Publish to GitHub after `gh auth login`:

```bash
./publish_github.sh <owner/repo> private
```

See [docs/distribution.md](docs/distribution.md).

## Important Boundary

Running `fetch` does not mean every source has been normalized into ingredient-level rows. It means the official source has been captured, hashed, and versioned. Running `normalize` records parser runs and only inserts normalized facts for parsers that have explicit source support.

See [docs/source-model.md](docs/source-model.md).
