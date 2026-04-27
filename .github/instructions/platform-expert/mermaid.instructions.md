---
name: "Platform-architect / Mermaids"
description: "Mermaid Instructions (Git/GitHub Transparent & CI-Friendly)"
layer: digital-generic-team
---
# Mermaid Instructions (Git/GitHub Transparent & CI-Friendly)


These rules apply to all **Mermaid** diagrams in this repository.
Mermaid is used for lightweight diagrams embedded in Markdown and/or rendered into SVG/PNG.

---

## 1. Purpose & Scope

Use Mermaid for:
- simple flowcharts
- sequence diagrams (lightweight)
- state diagrams
- basic architecture overviews
- diagrams that should be readable directly in Markdown

Do NOT use Mermaid for:
- very complex architecture diagrams with heavy styling requirements (use PlantUML)
- diagrams that require Graphviz graph layout tuning (use Graphviz)

---

## 2. Repository Structure (Mandatory)

```
docs/
  diagrams/
    mermaid/
      flow_auth.mmd
      sequence_login.mmd
  images/
    mermaid/
      flow_auth.svg
      sequence_login.svg
.digital-team/bin/
  render-mermaid.sh
Makefile
```

Rules:
- Source files (`.mmd`) live in `docs/diagrams/mermaid/` (or `docs/mermaid/`).
- Generated images live in `docs/images/mermaid/`.
- Do not manually edit generated images.

---

## 3. Naming Conventions

- Use descriptive names and stable prefixes:
  - `flow_<topic>.mmd`
  - `sequence_<flow>.mmd`
  - `state_<topic>.mmd`
- Generated output must keep the same base name:
  - `flow_auth.mmd` → `flow_auth.svg`

---

## 4. Diagram Quality Rules

- Keep diagrams small and focused.
- Prefer multiple small diagrams over one large diagram.
- Use consistent naming for nodes and actors.
- Avoid overly dense diagrams in README; link to diagram files if large.

---

## 5. Rendering Strategy (Mandatory)

- All Mermaid rendering must be automated via:
  - `make render-diagrams` or `make docs`
- Rendering logic must live in `.digital-team/bin/` (CI-agnostic).
- Use Mermaid CLI (`mmdc`) in a controlled toolchain (container preferred in CI).

Preferred output:
- SVG for Markdown/README usage
- PNG only when required

---

## 6. Environment & Determinism

- Mermaid CLI version must be pinned in the toolchain (container or package lock).
- Rendering must be deterministic and produce stable output.
- Avoid diagrams depending on external resources.

---

## 7. Embedding in README

Preferred:

```md
Example output image path: `docs/images/mermaid/flow_auth.svg`
```

Rules:
- Do not embed generated artifacts inline as base64.
- Never reference unrendered `.mmd` in README unless you know the target renderer supports it.

---

## 8. Validation (Recommended)

- CI should fail if:
  - a `.mmd` file changed but corresponding `.svg` is not updated
- Avoid manual review of rendered diffs by keeping diagrams small.

---

## 9. Anti-Patterns (Prohibited)

- ❌ manual export of images from online editors
- ❌ committing generated images without their `.mmd` source
- ❌ mixing Mermaid and PlantUML for the same diagram layer without reason
- ❌ relying on unpinned tool versions