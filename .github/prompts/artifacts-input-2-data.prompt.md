<!-- layer: digital-generic-team -->
# /artifacts-input-2-data Prompt

Process all input files from `.digital-artifacts/00-input/` and create normalized data bundles in `.digital-artifacts/10-data/`.

## Canonical language requirement

All normalized data written to `.digital-artifacts/10-data/` must be English.
This is mandatory for every source type and every original input language.
Any retained source-language material is provenance only and must not replace the English normalized bundle content.

## Skill

- **Skill**: `artifacts`
- **Owner**: `agile-coach`

## Execution contract

1. **Discovery**: Scan `.digital-artifacts/00-input/documents/`, `.digital-artifacts/00-input/features/`, and `.digital-artifacts/00-input/bugs/` for processable files.
2. **Analysis**: For each file:
   - Compute SHA-256 fingerprint
   - Check if already ingested (idempotent)
   - Extract content via markitdown, OCR, or transcription
3. **Translation**: For `.txt` files, call Vision API to:
   - Translate to clear English
   - Infer type (feature, bug, or document)
   - Generate 2-4 research hints
   - Provide review note for downstream planning
4. **Bundle Allocation**: Call `artifacts_tool.py bundle` to allocate a timestamped bundle directory
5. **Metadata**: Write standardized YAML metadata with extraction engine and status
6. **Normalization**: Render bundle markdown with extracted content
   - The rendered normalized bundle content in `10-data` must be English.
   - If the original source is not English, translate before treating the bundle as downstream-ready.
7. **Inventory**: Register bundles in `10-data/INVENTORY.md`
8. **Archival**: Move source files to `.digital-artifacts/20-done/` with audit trail
9. **Audit**: Write execution audit to `.digital-artifacts/70-audits/<date>/`

## Default command

```bash
make artifacts-input-2-data
```

## Environment requirements

- `DIGITAL_TEAM_VISION_API_URL`: Azure OpenAI / compatible endpoint
- `DIGITAL_TEAM_VISION_API_KEY`: API authentication key
- `DIGITAL_TEAM_VISION_MODEL`: Model name (e.g., `gpt-4o-mini`)

## Documentation contract

- Writes only under `.digital-artifacts/`
- Never modifies external services or boards
- All source files are archived with full provenance tracking
- Extraction status recorded for auditability
- English normalized content in `10-data` is the canonical downstream source for stages, planning, and reviews

## Verification

- Progress markers: `[artifacts-input-2-data] processing: <filename> (<classification>)`
- Success markers: `[artifacts-input-2-data] bundle: <item_code>`
- Audit report: `.digital-artifacts/70-audits/<date>/NNNNN-artifacts-input-2-data.md`
