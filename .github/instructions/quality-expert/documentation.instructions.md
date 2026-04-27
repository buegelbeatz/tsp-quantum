---
name: "Quality-expert / Documentations"
description: "Enterprise Documentation Rendering Strategy"
layer: digital-generic-team
---
# Enterprise Documentation Rendering Strategy  
(PlantUML + Mermaid + Graphviz)

This document defines the standardized rendering strategy for all diagrams in this repository.

Goals:
- Deterministic rendering
- CI-agnostic execution
- No manual image generation
- No vendor lock-in (GitHub/Bitbucket compatible)
- Reproducible documentation artifacts
- Consistent diagram styling across the organization

---

# Enterprise Script Documentation Policy (Mandatory)

All repository shell scripts must include enterprise header sections with concrete content:

- `# Purpose:` followed by specific operational intent.
- `# Security:` followed by explicit boundary/scope constraints.

Prohibited header content:

- Placeholder text such as `TODO`, `TBD`, `placeholder`, or `describe the purpose of this script`.
- Empty section bodies (`#` only lines without semantic content).

Quality enforcement:

- `/quality` must flag placeholder or empty `Purpose` / `Security` text as documentation findings.
- `/quality-fix` must not generate placeholder header text and should normalize legacy placeholders when feasible.

---

# 1. Supported Diagram Technologies

The following diagram languages are officially supported:

| Technology | Use Case |
|------------|----------|
| PlantUML   | Architecture, Sequence, Component, Deployment diagrams |
| Mermaid    | Lightweight flow diagrams in Markdown |
| Graphviz   | Directed graphs, dependency trees |

Rules:
- Choose the simplest tool that fits the use case.
- Do not mix diagram styles in the same conceptual layer.

---

# 2. Directory Structure (Mandatory)

```
docs/
  diagrams/
    plantuml/
      architecture.puml
      sequence_login.puml
    mermaid/
      flow_auth.mmd
    graphviz/
      dependency.dot

  images/
    plantuml/
    mermaid/
    graphviz/

scripts/
  render_plantuml.sh
  render_mermaid.sh
  render_graphviz.sh
  render_all.sh
```

Rules:
- Source files must never be placed directly in `docs/images/`.
- Generated files must not be manually edited.
- Images must always be reproducible from sources.

---

# 3. Rendering Philosophy

- Rendering must be automated.
- Rendering must be CI-independent.
- Rendering must be runnable locally.
- No manual export from IDEs allowed.
- Diagrams must be version-controlled as source (`.puml`, `.mmd`, `.dot`).

---

# 4. Standard Rendering Targets

Preferred output format:

| Use Case | Format |
|----------|--------|
| README / Markdown | SVG (preferred) |
| PDFs | SVG or PNG |
| External systems | PNG fallback |

SVG is preferred because:
- Scalable
- Diffable
- Smaller
- Cleaner Git history

---

# 5. Rendering Scripts (CI-Agnostic)

All rendering logic must live in `scripts/`.

Example: `render_plantuml.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT="docs/diagrams/plantuml"
OUTPUT="docs/images/plantuml"

mkdir -p "$OUTPUT"

for file in "$INPUT"/*.puml; do
  plantuml -tsvg "$file" -o "../../images/plantuml"
done
```

Example: `render_graphviz.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT="docs/diagrams/graphviz"
OUTPUT="docs/images/graphviz"

mkdir -p "$OUTPUT"

for file in "$INPUT"/*.dot; do
  dot -Tsvg "$file" -o "$OUTPUT/$(basename "$file" .dot).svg"
done
```

Example: `render_mermaid.sh` (using mermaid-cli)

```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT="docs/diagrams/mermaid"
OUTPUT="docs/images/mermaid"

mkdir -p "$OUTPUT"

for file in "$INPUT"/*.mmd; do
  mmdc -i "$file" -o "$OUTPUT/$(basename "$file" .mmd).svg"
done
```

Master script:

```bash
#!/usr/bin/env bash
set -euo pipefail

./scripts/render_plantuml.sh
./scripts/render_graphviz.sh
./scripts/render_mermaid.sh
```

---

# 6. CI Integration (Vendor-Agnostic)

CI must:

1. Install required tools
2. Run `scripts/render_all.sh`
3. Fail if generated images differ from committed ones

Optional:
- Auto-commit rendered changes (controlled environments only)

CI must not:
- Contain diagram logic
- Hardcode rendering commands inline

---

# 7. Governance Rules

## 7.1 No Manual PNGs

- Manual exports from VS Code, IntelliJ, or web tools are prohibited.
- All images must be generated via scripts.

## 7.2 No Editing Generated Images

- `docs/images/` is treated as generated content.
- Direct modification is not allowed.

## 7.3 Naming Conventions

PlantUML:
- `architecture_<domain>.puml`
- `sequence_<flow>.puml`

Mermaid:
- `flow_<feature>.mmd`

Graphviz:
- `graph_<domain>.dot`

Generated files:
- Must have identical base name
- Only extension differs

---

# 8. Copilot Governance

`.github/copilot-instructions.md` must include:

- Use PlantUML for architecture diagrams.
- Use Mermaid for simple flow diagrams in Markdown.
- Do not embed inline PNG blobs.
- Always place diagrams in `docs/diagrams/<type>/`.
- Never commit manually exported images.

---

# 9. Dockerized Rendering (Recommended for Enterprise)

Provide a Docker image for consistent rendering:

```
Dockerfile.docs
```

Contains:
- OpenJDK
- PlantUML
- Graphviz
- Mermaid CLI
- Node (for mmdc)

This ensures:
- Identical rendering across machines
- No "works on my machine" issues
- Stable CI behavior

---

# 10. Optional: Pre-Commit Hook

Optional pre-commit hook:

- Detect changed `.puml`, `.mmd`, `.dot`
- Run render script
- Stage updated images

Prevents:
- Out-of-sync diagrams

---

# 11. Anti-Patterns (Prohibited)

- ❌ Storing only PNG without source
- ❌ Mixing manual and automated exports
- ❌ Embedding rendered images in Markdown without versioned source
- ❌ Rendering inside CI YAML directly
- ❌ Tool version drift across developers

---

# 12. Enterprise Recommendation

For large organizations:

- Maintain a shared "Documentation Toolchain Container"
- Standardize diagram theme (fonts/colors)
- Add diagram linting step
- Enforce rendering check in CI
- Version-lock PlantUML, Graphviz, Mermaid CLI

---

# 13. Summary

Source of truth:  
`.puml`, `.mmd`, `.dot`

Generated artifacts:  
`.svg` (preferred), `.png` (fallback)

Rendering logic location:  
`scripts/`

CI responsibility:  
Execute scripts, verify consistency

Governance responsibility:  
`.github/` instructions only
