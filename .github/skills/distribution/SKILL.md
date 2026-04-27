---
name: distribution
description: Counts and reports code lines, documentation lines, test lines, and config lines across the repository. Emits a Markdown table with file counts, line counts, and percentage share per category.
user-invocable: false
layer: digital-generic-team
---

# Skill: Distribution

Reports the line-level distribution of source code, tests, documentation, and configuration files in the repository.

## Script

- `scripts/distribution.py` — scans repository, emits Markdown table

## Usage

```bash
source .digital-runtime/layers/python-runtime/venv/bin/activate
python3 .github/skills/distribution/scripts/distribution.py [repo-root]

# Fallback when layer runtime is unavailable
bash .github/skills/shared/shell/scripts/run-tool.sh \
	python3 .github/skills/distribution/scripts/distribution.py [repo-root]
```

## Categories

| Category | Included |
|----------|---------|
| Scripts / Source | `.py`, `.sh`, `.ts`, `.js`, `.java`, `.rs`, `.go`, `.cpp`, `.c` (non-test) |
| Tests | Any file matching `test_*`, `*_test.*`, or under a `tests/` directory |
| Documentation | `.md`, `.rst`, `.txt` |
| Configuration | `.yaml`, `.yml`, `.toml`, `.ini`, `.json` |

## Information Flow

| Field    | Value |
|----------|-------|
| Producer | Agent or developer invoking `/distribution` |
| Consumer | Chat output / clipboard |
| Trigger  | User invokes `/distribution` |
| Payload  | Markdown table with file counts, line counts, percentage per category |

## Dependencies

- Python 3.11+ (standard library only, no external packages)
