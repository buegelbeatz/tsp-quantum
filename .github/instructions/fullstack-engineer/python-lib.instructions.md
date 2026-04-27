---
name: "Fullstack-engineer / Python-libs"
description: "Python Library Template Instructions"
layer: digital-generic-team
---
# Python Library Template Instructions  
(Reusable Library, PIP/PyPI-Compatible, CI & Git Transparent)

These rules define the structure and governance for a reusable **Python library template**
that can optionally be published to **PyPI** (or a private index) and integrated into other projects.

The goals are:
- Clean packaging
- Deterministic builds
- CI-friendly testing
- Optional PyPI publishing
- Long-term maintainability
- Compatibility with modern Python tooling

---

# 1. Core Principles

- The library must be installable via `pip`.
- The library must not depend on local paths.
- Packaging must follow modern standards (PEP 517 / PEP 621).
- Source code must live under `src/`.
- Tests must not import from local paths directly.
- Versioning must follow Semantic Versioning (SemVer).

---

# 2. Recommended Repository Structure

```
project-root/
│
├── src/
│   └── yourlib/
│       ├── __init__.py
│       ├── core.py
│       ├── utils.py
│       └── _version.py
│
├── tests/
│   ├── test_core.py
│   └── test_utils.py
│
├── examples/
│   └── basic_usage.py
│
├── scripts/
│   ├── build.sh
│   ├── publish.sh
│   └── version_bump.sh
│
├── docs/
│   ├── index.md
│   └── api.md
│
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
└── Makefile
```

Rules:
- Use the `src/` layout (mandatory).
- Tests must import the installed package, not relative modules.
- Keep business logic in `src/`, not in scripts.

---

# 3. Packaging Standard (Mandatory)

Use `pyproject.toml` (PEP 621).

Minimum required fields:

- name
- version
- description
- authors
- license
- dependencies
- requires-python

Build backend must be one of:
- setuptools
- hatchling
- poetry-core
- flit

No legacy `setup.py`-only packaging.

---

# 4. Versioning

- Follow Semantic Versioning:
  - MAJOR.MINOR.PATCH
- Increment:
  - PATCH → bugfix
  - MINOR → new backward-compatible features
  - MAJOR → breaking changes
- Version must be defined in a single source of truth:
  - either `pyproject.toml`
  - or `src/yourlib/_version.py`

Avoid duplicate version definitions.

---

# 5. Dependency Management

- Pin minimal supported versions in `pyproject.toml`.
- Do not over-pin dependencies unless required.
- Separate:
  - runtime dependencies
  - optional dependencies (`extras`)
  - development dependencies

Example extras:

- `dev`
- `docs`
- `test`

---

# 6. Testing Requirements

**Coverage specification is defined in `.github/instructions/testing/testing.instructions.md`.**

Mandatory:
- Use `pytest`.
- Achieve ≥ 80% code coverage (libraries typically cannot waive this).
- Tests must run via:

```
make test
```

Rules:
- No network calls in unit tests.
- Use mocks for external services.
- Keep tests deterministic.

Optional:
- property-based testing for algorithm-heavy code.

---

# 7. Linting & Formatting

Mandatory:
- Type hints on public functions.
- Docstrings (NumPy or Google style).
- Linting via:
  - ruff / flake8
  - mypy (recommended)
- Formatting via:
  - black (recommended)

Must run via:

```
make lint
```

---

# 8. Documentation

Mandatory:
- README with:
  - Installation
  - Quickstart
  - Example
  - Version compatibility
- API documentation under `docs/`
- All public functions must have docstrings.

If publishing to PyPI:
- Long description must render correctly (Markdown preferred).

---

# 9. Build & Publish Workflow

Build must be reproducible:

```
make build
```

This must:
- clean previous builds
- build sdist
- build wheel

Publishing must:
- use API token from environment variable
- never hardcode credentials
- run via:

```
make publish
```

Publishing to PyPI must require:
- version bump
- passing tests
- tagged commit

---

# 10. Makefile Requirements

Required targets:

- make help
- make lint
- make test
- make build
- make publish
- make clean

Make must be the single orchestration layer for:
- local development
- CI pipelines
- publishing

CI must only invoke:

```
make check
```

---

# 11. CI/CD Requirements

CI must:

- install dependencies
- run lint
- run tests
- build package
- fail on errors

Optional:
- publish on tagged releases only

CI must not:
- duplicate Makefile logic inline.

---

# 12. Security & Secrets

- Never commit:
  - PyPI API tokens
  - private keys
  - credentials
- Use environment variables:
  - `PYPI_API_TOKEN`
- `.env` must be ignored.
- Provide `.env.example`.

---

# 13. Optional: Publishing to PyPI

If publishing:

- Ensure unique package name.
- Verify metadata completeness.
- Ensure `pip install yourlib` works in clean environment.
- Test installation in fresh virtual environment before release.

Release process:

1. Bump version
2. Commit
3. Tag
4. Push
5. CI builds & publishes

---

# 14. Anti-Patterns (Prohibited)

- ❌ No `src/` layout
- ❌ Importing from relative paths in tests
- ❌ Hardcoded credentials
- ❌ Manual wheel uploads
- ❌ Mixing library code with CLI scripts without separation
- ❌ Unpinned Python version compatibility
- ❌ Publishing without CI validation

---

# 15. Optional Enhancements (Recommended)

- Pre-commit hooks
- Type checking enforcement
- Mutation testing for core logic
- Automated changelog generation
- Signed release tags
- GitHub Release notes generation
- Reproducible builds via Docker

---

# 16. Philosophy

A Python library must be:

- Installable
- Testable
- Documented
- Versioned
- Secure
- Deterministic

Make is the orchestration layer.
pyproject.toml is the packaging contract.
CI is the quality gate.
