---
name: "Runtime Execution Standards"
description: "Mandatory infrastructure patterns for local execution and dependency management"
applyTo: "**"
layer: digital-generic-team
---
# Runtime Execution Standards


### Violation Pattern (❌ WRONG)
```bash
# DO NOT DO THIS
pip install -r requirements.txt
python3 my_script.py
```

### Correct Patterns (✅ RIGHT)

#### Pattern 1: Layer-Based Virtual Environment (Preferred)

Use the layer venv located at `.digital-runtime/layers/<layer-name>/`:

```bash
# Bootstrap or sync layer venv (run once or after dependency changes)
make layer-venv-sync

# Activate and run Python code
source .digital-runtime/layers/python-runtime/venv/bin/activate
python3 my_script.py
```

**When to use:** 
- One-off scripts or debugging
- Local testing before commit
- Quick validation during development

#### Pattern 2: Container-Orchestrated Execution (Default)

Route commands through the shared/shell registry with container fallback:

```bash
# Set environment variable to prefer container execution
export RUN_TOOL_PREFER_CONTAINER=1

# Invoke tool through registry (automatic container provisioning if local unavailable)
bash .github/skills/shared/shell/scripts/run-tool.sh python3 my_script.py
```

**When to use:**
- CI/CD pipelines (already configured)
- Cross-platform execution (macOS/Linux/Windows)
- When local dependencies are unavailable
- Repeatable, auditable execution
- Any registered external CLI unless a bootstrap exception is explicitly documented

#### Pattern 3: Inline Script with Explicit Layer Venv

For agent-driven execution (this pattern):

```bash
# Activate layer venv inline, then execute
source .digital-runtime/layers/python-runtime/venv/bin/activate && python3 my_script.py
```

**When to use:**
- Agent chains or multi-step workflows
- Temporary execution within a terminal session
- Bootstrap and repair paths where the registry wrapper itself cannot yet supply the runtime

---

## Directory Locations

### Runtime Data
```
.digital-runtime/layers/
├── python-runtime/
│   ├── venv/bin/python3
│   ├── npm-cache/                 # npm/nodejs ephemeral caches
│   └── ...
└── digital-iot-team/
    ├── bin/python3
    └── ...
```

**NEVER** create directories outside the repository root for runtime or experiments.
**REQUIRED** location for experiments and temporary agent work: `.digital-runtime/`.

**NEVER** store runtime data under `.digital-team/` or project root.

### Test Outputs
```
.tests/
├── coverage/                       # Coverage reports
├── pytest-reports/                 # XML/HTML reports
└── temp/                           # Temporary test files
```

**NEVER** store under `.digital-team/` or project root.

---

## Skill Dependencies

Each skill declares its Python dependencies in `requirements.txt` within its own skill directory:

```
.github/skills/
├── huggingface/
│   ├── requirements.txt            # huggingface_hub>=0.20.0
│   └── scripts/
├── powerpoint/
│   ├── requirements.txt            # python-pptx, cairosvg, Pillow>=9.0.0
│   └── scripts/
└── shared/shell/
    └── scripts/metadata/tools.csv  # Registered tools for container fallback
```

**Do NOT** maintain a manual root-level `requirements.txt`. Use skill-scoped files.

### Layer Sync Command
```bash
# Auto-discovers all skill requirements.txt and merges into layer venv
make layer-venv-sync
```

---

## Infrastructure Decision Tree

```
┌─ Do I need Python packages?
│
├─→ YES
│  ├─ Am I in CI/CD or multi-machine context?
│  │  ├─→ YES: Use container-orchestrated execution (Pattern 2)
│  │  └─→ NO: Use layer venv (Pattern 1 or 3)
│  │
│  └─ Packages already in layer venv?
│     ├─→ NO: Run `make layer-venv-sync` first
│     └─→ YES: Proceed with execution
│
└─ Do I need registered tools (ffmpeg, jq, etc.)?
   ├─→ YES: Use container registry (Pattern 2)
   └─→ NO: Use layer venv or direct CLI
```

---

## Enforcement & Oversight

### For Copilot/Agents
- **NEVER** attempt `pip install -r ...` without explicit user approval
- **ALWAYS** check whether `.digital-runtime/layers/<layer>/` exists
- **MUST** use `make layer-venv-sync` if layer venv is missing or stale
- **PREFER** container-orchestrated execution for repeatable workflows
- **STOP** and ask user before violating this standard

### For Development
- If you see a script violating this, mark the violation in `.github/instructions/` or memory
- Document the correct pattern in handoff or escalation reports
- Create a `[@handoff](...)` reference to this document if infrastructure issues arise

---

## Examples by Scenario

### Scenario: Generate PowerPoint Template

**Wrong:**
```bash
pip install -r .github/skills/powerpoint/requirements.txt
python3 .github/skills/powerpoint/scripts/create_standard_template.py --layer digital-generic-team
```

**Correct (Pattern 1):**
```bash
make layer-venv-sync
source .digital-runtime/layers/python-runtime/venv/bin/activate
python3 .github/skills/powerpoint/scripts/create_standard_template.py --layer digital-generic-team
```

**Correct (Pattern 3 - Single Line):**
```bash
make layer-venv-sync
source .digital-runtime/layers/python-runtime/venv/bin/activate && \
  python3 .github/skills/powerpoint/scripts/create_standard_template.py --layer digital-generic-team
```

### Scenario: Run Skill Tests with Coverage

**Correct:**
```bash
make layer-venv-sync
source .digital-runtime/layers/python-runtime/venv/bin/activate && \
  pytest .github/skills/huggingface/scripts/tests/ --cov=.github/skills/huggingface/scripts --cov-report=xml:.tests/coverage/huggingface.xml
```

### Scenario: Use FFmpeg in Multi-Platform Context

**Correct (Container Registry):**
```bash
export RUN_TOOL_PREFER_CONTAINER=1
bash .github/skills/shared/shell/scripts/run-tool.sh ffmpeg -i input.mp3 output.wav
```

---

## Related Files
- `.github/instructions/` — All governance and execution standards
- `.github/skills/shared/shell/` — Container registry backend
- `.github/copilot-instructions.md` — Runtime behavior for agents
- `Makefile` — `make layer-venv-sync` target
- `.digital-runtime/` — Runtime storage (gitignored)
- `.github/.gitignore` — Exemptions for committed metadata
