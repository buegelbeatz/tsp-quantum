<!-- layer: digital-generic-team -->
# /artifacts-data-2-specification Prompt

Transform normalized data bundles into specifications and persist review evidence.

## Skill

- **Skill**: `artifacts`
- **Owner**: `agile-coach`

## Execution contract

1. **Inventory Scan**: Read `.digital-artifacts/10-data/INVENTORY.md` to identify unreviewed bundles
2. **Review Preparation**: For each bundle, use canonical review directory `60-review/<date>/<item_code>/`.
3. **Review Integration**: Persist review evidence in `60-review/<date>/<item_code>/REVIEW.md` with checklist/scoring.
4. **Specification Synthesis (Agile-coach owned)**: Always create or update consolidated specification markdown for each bundle.
5. **Completeness Handling**: Incomplete inputs must be reflected in checklist/scoring fields, not by skipping specification creation.
6. **Traceability**: Maintain reference to source bundle and review log with audit trail

## Default command

```bash
make artifacts-data-2-specification
```

## Documentation contract

- Reads from `.digital-artifacts/10-data/`
- Writes specification documents to `.digital-artifacts/30-specification/`
- Uses canonical reviews in `.digital-artifacts/60-review/<date>/<item_code>/`
- Always synthesizes specifications for every normalized data bundle
- Specifications remain local; no external service writes

## Verification

- Consolidated specification: `.digital-artifacts/30-specification/<date>/<item_code>/<item_code>-specification.md`
- Canonical review: `.digital-artifacts/60-review/<date>/<item_code>/REVIEW.md`
