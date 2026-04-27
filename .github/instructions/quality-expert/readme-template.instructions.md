---
name: "Quality-expert / README Template Standard"
description: "Enterprise README template standard with badge governance, QuickStart patterns, and section requirements"
applyTo: "README.md"
layer: digital-generic-team
---
# Enterprise README Template Standard

Defines the mandatory structure, badge policy, and QuickStart pattern for all `README.md` files in `digital-*` repositories.

---

## 1. Badge Policy

### Rule: Only include badges that are real and backed by CI/CD or published registries.

**Allowed badge categories:**

| Category | Condition |
|----------|-----------|
| Python version | Only if a `python_requires` or `pyproject.toml` / `setup.cfg` entry exists |
| Linting (ruff) | Only if `ruff.toml` or `ruff` config is present in the repo |
| Type checking (mypy) | Only if `mypy.ini` is present in the repo |
| Test coverage | Only if coverage reporting is configured (`.coveragerc` or `pytest.ini` with coverage target) |
| CI status | Only if a GitHub Actions or equivalent CI pipeline is active |
| License | Only if a `LICENSE` file is present |
| Docker image | Only if image is published to a registry (GHCR, DockerHub, Quay) |

**Forbidden badge patterns:**
- Badges linking to non-existent workflows or coverage services that are not configured
- Static/hardcoded badge values ("passing", "100%") not backed by real data
- Shields.io style-badges for vanity metrics without semantic meaning
- Duplicate badges for the same property

**Badge placement:** Top of README, after the project title and short description, in a single horizontal line or small grouped block.

**Badge style:** `flat-square` preferred for consistency.

---

## 2. Mandatory README Sections

Every README must include the following sections in order:

```
# <Project Title>

> <one-line project description>

<badges>

---

## Overview
## Prerequisites
## QuickStart
## Repository Structure
## Development
## Testing
## Contributing (optional, omit if trivial)
## License
```

### Section Requirements

#### `## Overview`
- 2–5 sentences describing what this repo does, its layer position, and its relationship to sibling/parent repos.
- Include a Mermaid layer diagram if the repo participates in a multi-layer inheritance model.

### Stage Concept Documentation (Mandatory when stage flows exist)

- If stage prompts/instructions are present, README must contain a stable "Stage Concepts" subsection.
- The subsection must explicitly cover both:
  - `exploration` (intent, readiness/failure indicators, transition role)
  - `project` (intent, readiness/failure indicators, transition role)
- The subsection must point to canonical source files (instructions/prompt/runtime) instead of duplicating dynamic planning state.

### Diagram Explanation Rule (Mandatory)

- Diagrams must not appear as a raw image list without explanatory text.
- Insert concise explanation blocks between diagrams that state:
  - what the diagram represents,
  - which stage decision/gate it supports,
  - how it should be interpreted by readers.

### Stable-vs-Dynamic Content Boundary (Mandatory)

- README must document stable operational guidance only.
- Do **not** embed dynamic planning/runtime state in README.
  - Excluded examples: `.digital-artifacts/50-planning/**`, `project-assessment.md`, current checklist score snapshots, transient open-question lists, generated feature suggestion lists.
- Dynamic state must remain in planning artifacts, board refs, and wiki/project runtime outputs.
- README may mention *how* to generate current planning state (for example `/project`), but must not mirror the generated state itself.

#### `## Prerequisites`
- List all required tools with minimum versions.
- Reference `tools.csv` when available: `.github/skills/shared/shell/scripts/metadata/tools.csv`
- Include `.env` setup instructions referencing `.env.example`.

#### `## QuickStart`
- **MUST** use the standardized clone-run-clean pattern (see Section 3).
- MUST cover public repo path.
- MUST cover private repo path (GH_TOKEN variant) when `visibility: private` applies.
- MUST NOT hardcode tokens or credentials.

#### `## Repository Structure`
- Use a directory tree with inline comments.
- Highlight key entry points (`install.sh`, `extend.sh`, `Makefile`, `.github/`).

#### `## Development`
- Cover the layer venv sync: `make layer-venv-sync`
- Cover test execution pattern.
- Reference `make help` for all available targets.

#### `## Testing`
- Test command: `make test` or equivalent.
- Coverage output location: `.tests/`
- Do NOT reference `pytest` directly without the layer venv activation.

---

## 3. QuickStart Clone Pattern

### Detecting Git Remote and Layer Chain

When generating the QuickStart section, the agent MUST:
1. Read `.git/config` to extract the `origin` URL for the parent layer(s).
2. Read `.digital-team/layers.yaml` to determine the parent layer chain.
3. Derive the correct `git clone` URL from the `origin` remote — never hardcode it.
4. Determine visibility (private vs. public) from the repo's GitHub settings or presence of a GH_TOKEN guard in existing scripts.

### Public Repository QuickStart Pattern

```bash
# Clone layer, run install, cleanup
git clone --depth 1 <LAYER_ORIGIN_URL> /tmp/<layer-name> \
  && bash /tmp/<layer-name>/install.sh <TARGET_APP_DIR> \
  && rm -rf /tmp/<layer-name>
```

**Example** (derived from `.git/config` origin + target path):
```bash
git clone --depth 1 https://github.com/[org]/[layer-repo].git /tmp/iot-layer \
  && bash /tmp/iot-layer/install.sh /path/to/my-app \
  && rm -rf /tmp/iot-layer
```

### Private Repository QuickStart Pattern

```bash
# Set GitHub token (classic PAT with repo scope, or Fine-grained with Contents: read)
export GH_TOKEN=ghp_xxx

git clone --depth 1 https://x-access-token:${GH_TOKEN}@github.com/<org>/<layer-repo>.git /tmp/<layer-name> \
  && bash /tmp/<layer-name>/install.sh <TARGET_APP_DIR> \
  && rm -rf /tmp/<layer-name>
```

**Rules:**
- NEVER inline the token value — always use `${GH_TOKEN}`.
- Always include a comment explaining the required token scope.
- For Bitbucket: replace GitHub URL with Bitbucket SSH or HTTP URL pattern (see Section 4).

### Multi-Layer Chain Example

When multiple parent layers exist (e.g., App → IoT Team → Generic Team):

```bash
# Step 1: Install base layer
git clone --depth 1 https://github.com/<org>/digital-generic-team.git /tmp/generic-layer \
  && bash /tmp/generic-layer/install.sh /path/to/my-app \
  && rm -rf /tmp/generic-layer

# Step 2: Install domain layer on top
git clone --depth 1 https://github.com/<org>/digital-iot-team.git /tmp/iot-layer \
  && bash /tmp/iot-layer/install.sh /path/to/my-app \
  && rm -rf /tmp/iot-layer
```

> Note: Layer order follows `.digital-team/layers.yaml` — install base layers first.

---

## 4. Git Host Patterns

### GitHub (public)
```
https://github.com/<org>/<repo>.git
```

### GitHub (private, token-based)
```
https://x-access-token:${GH_TOKEN}@github.com/<org>/<repo>.git
```

### Bitbucket (SSH, future)
```
git@bitbucket.org:<workspace>/<repo>.git
```

### Bitbucket (HTTP, future)
```
https://x-token-auth:${BB_TOKEN}@bitbucket.org/<workspace>/<repo>.git
```

> When Bitbucket support is active, a `BB_TOKEN` environment variable must be documented in `.env.example`.

---

## 5. README Generation Rules for Agents

When generating or updating a README:

1. **Read `.git/config`** — extract `[remote "origin"].url`.
2. **Read `.digital-team/layers.yaml`** — extract parent layer list.
3. **Scan the repo root** — detect `LICENSE`, `ruff.toml`, `mypy.ini`, `.coveragerc`, `.github/workflows/`.
4. **Only include badges for detected capabilities** — no speculative badges.
5. **Generate QuickStart from real URLs** — never use placeholder `<org>/<repo>`.
6. **Emit private-repo variant only** — when the origin URL matches a known-private pattern or when `GH_TOKEN` is referenced in existing scripts.
7. **Use `flat-square` badge style** consistently.
8. **Do not include a Contributing section** for Layer 0 internal repos unless explicitly requested.

---

## 6. Example README Header Block

```markdown
# My Project Name

> Short one-line description of the project.

![Ruff](https://img.shields.io/badge/linter-ruff-blue?style=flat-square)
![Mypy](https://img.shields.io/badge/types-mypy-informational?style=flat-square)
![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---
```

> Badges are illustrative. Only include those backed by actual configuration files in your repository.

---

## Related Files

- `.github/instructions/quality-expert/documentation.instructions.md` — Diagram and script documentation policy
- `.github/instructions/quality-expert/versioning.instructions.md` — CHANGELOG and versioning rules
- `.github/skills/quality-expert/` — Quality gate scripts
- `.digital-team/layers.yaml` — Layer inheritance chain
- `.env.example` — Required environment variable documentation
