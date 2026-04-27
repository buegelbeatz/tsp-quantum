---
name: "Language-expert / Rs"
description: "Enterprise R Package Instructions"
layer: digital-generic-team
---
# Enterprise R Package Instructions  
(Structure, Testing, Documentation, CI, and CRAN/Private Registry Readiness)

These rules define the governance model for **enterprise-grade R packages**.
The goal is to ensure:

- Reproducibility
- Clean dependency management
- Strong test coverage
- High-quality documentation
- CI/CD compatibility
- Optional CRAN or private repository publishing
- Long-term maintainability

All R packages must follow this template unless explicitly approved otherwise.

---

# 1. Core Principles

- The package must be installable via `install.packages()` or `remotes::install_github()`.
- Use standard R package structure.
- All functions must be documented.
- All exported functions must be tested.
- CI must validate build, tests, and documentation.
- No secrets in repository.

---

# 2. Recommended Repository Structure

```
project-root/
│
├── R/
│   ├── core.R
│   ├── utils.R
│   └── model.R
│
├── man/                  # auto-generated (do not edit manually)
│
├── tests/
│   └── testthat/
│       ├── test-core.R
│       └── test-model.R
│
├── vignettes/
│   ├── introduction.Rmd
│   └── advanced_usage.Rmd
│
├── inst/
│   └── extdata/
│
├── data/                 # optional packaged datasets
│
├── DESCRIPTION
├── NAMESPACE
├── LICENSE
├── README.Rmd
├── README.md             # generated
├── .Rbuildignore
├── .gitignore
└── Makefile
```

Rules:
- `R/` contains all source code.
- `man/` must be generated via roxygen2 (never edited manually).
- `tests/testthat/` contains all tests.
- `vignettes/` contains long-form documentation.
- Use `.Rbuildignore` to exclude non-package artifacts.

---

# 3. DESCRIPTION File Requirements (Mandatory)

The `DESCRIPTION` file must include:

- Package
- Title
- Version (SemVer)
- Description
- Authors@R
- License
- Encoding: UTF-8
- Roxygen
- RoxygenNote
- Imports
- Suggests (for testing, docs)
- Depends (only if strictly necessary)

Rules:
- Avoid unnecessary `Depends`.
- Keep Imports minimal and justified.
- Do not include development-only packages in Imports.

---

# 4. Documentation Standards (roxygen2 Mandatory)

- All exported functions must use roxygen2.
- Use `@export` only when needed.
- Include:
  - @param
  - @return
  - @examples
  - @details (if non-trivial)
- Document side effects.

Generate documentation via:

```
devtools::document()
```

Or:

```
make document
```

Never manually edit `man/*.Rd`.

---

# 5. Testing Requirements (Mandatory)

- Use `testthat`.
- All exported functions must have at least one test.
- Target coverage ≥ 80%.
- Use `covr` for coverage checks.

Rules:
- No internet-dependent tests.
- Use test fixtures for reproducibility.
- Set seeds for stochastic functions.
- Keep tests deterministic and fast.

Run tests via:

```
devtools::test()
```

Or:

```
make test
```

---

# 6. Linting & Style

Mandatory:
- Follow tidyverse style guide.
- Use `lintr`.
- No global variables without justification.
- Explicit return values.

This section is the authoritative linting reference for R in this repository.

Mandatory gates:
- `R -q -e "lintr::lint_package()"`
- `R CMD check .` (when package layout exists)

Rules:
- Run linting before tests.
- New lint/check errors are not allowed.
- Store lint outputs and temporary artifacts under `.tests/r/`.

Recommended:
- Use `styler` for formatting.
- Use `goodpractice` for package checks.

---

# 7. Dependency Management

- Keep dependencies minimal.
- Separate:
  - Imports (runtime)
  - Suggests (testing/docs)
- Avoid heavy dependencies unless justified.
- Prefer base R where feasible.

If enterprise reproducibility required:
- Use `renv` for environment locking.
- Commit `renv.lock`.

---

# 8. Vignettes (Recommended for Enterprise)

- Provide at least one vignette for core workflow.
- Vignettes must build without internet.
- Avoid long-running computations in vignettes.
- Use small example datasets.

Build via:

```
devtools::build_vignettes()
```

---

# 9. CI/CD Requirements

CI must validate:

- `R CMD check`
- Unit tests
- Coverage threshold
- Lint checks
- Documentation build
- Package build (tar.gz)

CI must fail if:

- R CMD check produces ERROR
- Coverage < threshold
- Lint errors exceed defined limit

CI must not:
- Publish automatically without tag.

---

# 10. Versioning & Release Process

- Follow Semantic Versioning.
- Increment:
  - PATCH → bugfix
  - MINOR → new feature (backward compatible)
  - MAJOR → breaking change

Release flow:

1. Update version in DESCRIPTION.
2. Update NEWS.md.
3. Run full checks.
4. Tag release.
5. CI builds artifact.
6. Optional publish to CRAN/private registry.

---

# 11. Publishing Options

## CRAN
- Must pass strict `R CMD check --as-cran`.
- Avoid large dependencies.
- Ensure cross-platform compatibility.

## Private Registry
- GitHub Packages
- Internal RStudio Package Manager
- Artifactory

Publishing must:
- use token-based auth
- never hardcode credentials

---

# 12. Data & Security

- Do not commit sensitive data.
- Sample datasets must be sanitized.
- Large datasets should not be bundled unless essential.
- Use `inst/extdata/` for external example files.

---

# 13. Makefile Targets (Required)

Minimum required targets:

- make document
- make test
- make check
- make build
- make clean

CI must invoke:

```
make check
```

---

# 14. Anti-Patterns (Prohibited)

- ❌ Editing `man/` files manually
- ❌ Missing documentation on exported functions
- ❌ Hardcoded credentials
- ❌ Internet-dependent tests
- ❌ Failing R CMD check warnings ignored
- ❌ Large unused dependencies
- ❌ Mixing scripts and package logic

---

# 15. Optional Enterprise Enhancements

- Enforce coverage gates
- Pre-commit hooks for linting
- Signed Git tags
- Automatic NEWS.md generation
- Reverse dependency checks
- Benchmark tests
- Security scanning for dependencies

---

# 16. Philosophy

An enterprise R package must be:

- Installable
- Documented
- Tested
- Deterministic
- Maintainable
- CI-validated
- Release-controlled

Code lives in `R/`.
Docs are generated via roxygen2.
Tests live in `testthat`.
CI is the quality gate.