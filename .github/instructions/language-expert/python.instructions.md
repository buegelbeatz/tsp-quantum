---
name: "Language-expert / Pythons"
description: "Python Instructions"
layer: digital-generic-team
---
# Python Instructions


## Naming Conventions
- **Test files:** Prefix with `test_*.py`
- Use snake_case for modules and functions

## Code Quality
- Type hints for all function signatures
- Docstrings following NumPy/SciPy format
- Maximum line length: 100 characters
- Less than 100 lines per module where possible

## Linting (Single Point of Truth for Python)

This section is the authoritative linting reference for Python in this repository.

Mandatory gates:
- `ruff format --check .`
- `ruff check .`
- `mypy .` or `pyright` if type-checking is configured for the project

Rules:
- Run linting before tests.
- New lint/type errors are not allowed.
- Store lint outputs and temporary artifacts under `.tests/python/`.

## Testing & Coverage

**Test specification (naming, location, output, coverage) is defined in `.github/instructions/testing/testing.instructions.md`.**  
**If your language instructions conflict with that file, the testing.instructions.md takes priority.**

Key points:
- **Naming:** Test files and functions must start with `test_` prefix.
- **Location:** Store tests as close as possible to the code they test (colocated).
- **Output:** All test artifacts (cache, reports, temp files) must go to `.tests/python/`.
- **Coverage:** Maintain ≥80% code coverage (see testing.instructions.md for exceptions and waivers).

---

Specifics for Python:
- Use `pytest` for unit tests
- Use `pytest-cov` for coverage reporting

## Documentation
- Update docstrings for every function
- Document parameters, return values, and exceptions
- Include usage examples where appropriate
- Every module should include concise inline comments for non-obvious logic

## Dependencies
- Document all dependencies in `requirements.txt`
- Pin versions for reproducibility
- Comment version constraints with rationale
