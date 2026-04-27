<!-- layer: digital-generic-team -->
# /pull Prompt

Run deterministic grouped add/commit/push delivery workflow and optionally create a PR (review-gated).

Default command:

```bash
make pull MESSAGE="feat(scope): short summary"
```

Optional command (explicit role + PR creation):

```bash
make pull ROLE="fullstack-engineer" MESSAGE="feat(scope): short summary" CREATE_PR=1 BASE_BRANCH="main" REVIEW_ARTIFACT=".digital-artifacts/review/latest.md"
```

## Execution contract

1. Validate required input `MESSAGE`.
2. Enforce preconditions: no detached HEAD and no unresolved conflicts.
3. Classify changed files into deterministic groups (`docs`, `tests`, `config`, `code`).
4. Stage each group via git skill wrapper (`git-stage-add.sh`).
5. Create one commit per non-empty group via git skill wrapper (`git-commit-create.sh`) using template.
6. Push current branch via git skill wrapper (`git-push-branch.sh`).
7. If `CREATE_PR=1`, require existing review artifact first, then create PR.

## Documentation contract

- Keep prompt examples make-based only.
- Keep this command listed exactly once in `/help`.
- Keep matching skill metadata in `skills/shared/delivery/SKILL.md`.

## Verification

Run:

```bash
make pull MESSAGE="feat(scope): delivery test"
```

Expected result:

- command exits with status 0
- JSON output contains `status: ok`, `branch`, and `commits`
