# Source Model

The collector separates three layers:

1. Raw source capture
   - Official URL fetch.
   - Immutable file snapshot saved by SHA-256.
   - HTTP metadata and change flag stored in `source_snapshots`.

2. Source-specific parsing
   - Parser modules read snapshots.
   - Each parser handles the source's native structure: HTML app shell, XML, PDF, spreadsheet, or law page.
   - Parser runs are recorded in `parser_runs`, including skipped or partial runs.

3. Normalized regulatory facts
   - Structured rows belong in `regulatory_items`.
   - Ingredient identity and aliases belong in `ingredients` and `ingredient_aliases`.
   - Conditions such as concentration limits, product scope, body-part scope, and warning text belong in `regulatory_item_conditions`.

The raw snapshot layer must remain append-only. A bad parser can be fixed and rerun against old source snapshots without losing provenance.

