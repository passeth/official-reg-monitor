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

Require GitHub CLI authentication before publishing:

```bash
official-reg-monitor doctor --require-gh
```

## Normalize

```bash
official-reg-monitor normalize
```

Today-run example for the EU CosIng Annex CSV sources:

```bash
official-reg-monitor fetch --force
official-reg-monitor normalize
official-reg-monitor normalize --source EU_COSING_ANNEX_VI
```

The parser layer is intentionally source-specific. Sites do not expose identical tables:

- EU CosIng Annex II-VI use official European Commission CSV exports from `https://api.tech.ec.europa.eu/cosing20/1.0/api/annexes/{II|III|IV|V|VI}/export-csv`. The `eu_cosing_annex` parser normalizes those snapshots into substance-level `regulatory_items` rows.
- US eCFR uses GPO bulk XML in this registry to avoid HTML interstitials.
- JP MHLW is a PDF source and needs PDF table extraction before row-level normalization.
- KR law.go.kr, ASEAN, CN, and RU/EAEU require dedicated parsers or more precise official document URLs.

Current normalization support:

- `eu_cosing_annex`: extracts substance-level Annex II, III, IV, V, and VI rows from official EC CSV snapshots and writes them to `regulatory_sources`, `source_versions`, `regulatory_items`, and `parser_runs`. These rows preserve annex/substance facts from CosIng exports but do not yet perform `ingredient_id` canonical matching. CosIng remains informational and has no legal value; legal authority remains Regulation (EC) No 1223/2009 and its amendments/EUR-Lex texts.
- `us_ecfr`: extracts section-level normalized rows from GPO bulk XML for Title 21 cosmetic parts `700`, `701`, `710`, `720`, `740` and color-additive parts `70`, `71`, `73`, `74`, `80`, `81`, `82`. The rows are written to `regulatory_sources`, `source_versions`, `regulatory_items`, and `parser_runs`.
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

Build release bundle, source archive, wheel, and checksums:

```bash
make release
make verify-release
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

Running `fetch` does not mean every source has been normalized into ingredient-level rows. It means the official source has been captured, hashed, and versioned. Running `normalize` records parser runs and only inserts normalized facts for parsers that have explicit source support. EU CosIng Annex rows are substance-level annex rows and do not yet perform `ingredient_id` canonical matching. US eCFR support is currently section-level; ingredient-level extraction and matching are later parser layers.

See [docs/source-model.md](docs/source-model.md).
