# Source Model

The collector separates three layers:

1. Raw source capture
   - Official URL fetch.
   - Immutable file snapshot saved by SHA-256.
   - HTTP metadata and change flag stored in `source_snapshots`.

2. Source-specific parsing
   - Parser modules read snapshots.
   - Each parser handles the source's native structure: CSV export, XML, PDF, spreadsheet, HTML app shell, or law page.
   - Parser runs are recorded in `parser_runs`, including skipped or partial runs.

3. Normalized regulatory facts
   - Structured rows belong in `regulatory_items`.
   - Ingredient identity and aliases belong in `ingredients` and `ingredient_aliases`.
   - Conditions such as concentration limits, product scope, body-part scope, and warning text belong in `regulatory_item_conditions`.

The raw snapshot layer must remain append-only. A bad parser can be fixed and rerun against old source snapshots without losing provenance.

## EU CosIng Annex CSV exports

`EU_COSING_ANNEX_II` through `EU_COSING_ANNEX_VI` fetch official European Commission CSV exports from `https://api.tech.ec.europa.eu/cosing20/1.0/api/annexes/{II|III|IV|V|VI}/export-csv`. The `eu_cosing_annex` parser normalizes those snapshots into substance-level Annex rows in `regulatory_items`.

Those rows preserve official CosIng export facts, but they are not legal determinations and do not yet perform `ingredient_id` canonical matching. CosIng remains informational and has no legal value; legal authority remains Regulation (EC) No 1223/2009 and its amendments/EUR-Lex texts.

