<!-- layer: digital-generic-team -->
# /artifacts-specification-2-stage Prompt

Evaluate specifications against stage readiness and create stage-specific planning documents.

## Skill

- **Skill**: `artifacts`
- **Owner**: `agile-coach`

## Parameters

- `stage=<stage>` — Target stage code in digital-generic-team scope (e.g., `00-exploration`, `05-project`). Extended stages (10+) managed in downstream layers.

## Execution contract

1. **Readiness Assessment**: For each specification bundle and its canonical review in `60-review/<date>/<item_code>/`:
   - Verify specification completeness against stage requirements
   - Evaluate if bundle satisfies stage gate criteria
   - Document gaps or blockers
2. **Stage-Specific Logic**:
   - If `stage=00-exploration`: Minimal requirements, focus on problem clarity
   - If `stage=05-project`: Project charter, team setup, scope definition
3. **Document Creation / Update**:
   - Always create or update the canonical stage document `40-stage/<STAGE>.md`
   - `<STAGE>.md` is the uppercased stage command, for example `PROJECT.md` or `EXPLORATION.md`
   - If blockers exist: persist them inside the canonical stage document and keep `status: in-progress`
   - If blockers are resolved: set `status: active`
   - Render using the governed stage template from `.github/skills/stages-action/templates/project.md`
4. **Metadata Tracking**:
   - Record stage assignment timestamp
   - Link to source specification
   - Mark readiness status

## Default command

```bash
make artifacts-specification-2-stage stage=<stage>
```

## Documentation contract

- Reads from `.digital-artifacts/30-specification/` and `.digital-artifacts/60-review/`
- Writes to `.digital-artifacts/40-stage/`
- Uses governed templates (never freeform)
- Maintains full traceability to source bundle
- No external writes; local only

## Verification

- Stage document: `.digital-artifacts/40-stage/<STAGE>.md`
- Readiness checklist and scoring captured inside `.digital-artifacts/40-stage/<STAGE>.md`
- Template adherence validation
