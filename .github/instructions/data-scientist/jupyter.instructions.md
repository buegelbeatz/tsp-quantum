---
name: "Data-scientist / Jupyters"
description: "Jupyter Notebook Development Instructions"
layer: digital-generic-team
---
# Jupyter Notebook Development Instructions  
(Project Structure, Reproducibility, and Best Practices)

These rules apply to all Jupyter Notebooks in this repository.

Notebooks must be:
- Reproducible
- Structured
- Clean
- Deterministic
- Suitable for CI validation

---

# 1. Project Structure (Mandatory)

Use the following structure:

```
project-root/
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_model_training.ipynb
│   └── 03_evaluation.ipynb
│
├── src/
│   ├── data/
│   ├── models/
│   ├── utils/
│   └── __init__.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
│
├── tests/
│
├── requirements.txt / pyproject.toml
├── README.md
└── .gitignore
```

Rules:
- Business logic must live in `src/`, not inside notebooks.
- Notebooks are orchestration + documentation layers.
- Large datasets must not be committed.
- Raw data is immutable.

---

# 2. Notebook Naming Convention

- Prefix with ordered numbers:
  - `01_`
  - `02_`
  - `03_`
- Use snake_case.
- Names must describe purpose.

Example:
- `01_data_cleaning.ipynb`
- `02_feature_engineering.ipynb`
- `03_model_validation.ipynb`

---

# 3. Notebook Structure (Mandatory Layout)

Every notebook must follow this structure:

## 1️⃣ Title & Metadata (Markdown)
- Purpose
- Author
- Date
- Dependencies
- Expected runtime

## 2️⃣ Imports (Single Cell)
All imports must be in one cell at the top.

## 3️⃣ Configuration
- Random seeds
- Paths
- Environment settings

Example:

```python
import random
import numpy as np

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
```

## 4️⃣ Functions / Helpers
- No complex logic inline.
- Use functions from `src/`.

## 5️⃣ Execution Sections
- Data loading
- Transformation
- Training
- Evaluation

## 6️⃣ Results / Visualization
- Clear labeling
- Reproducible plots

## 7️⃣ Conclusions (Markdown)

---

# 4. Reproducibility (Mandatory)

- All notebooks must run top-to-bottom without manual intervention.
- No hidden state.
- No reliance on execution order.
- Restart kernel → Run all must succeed.

Environment activation policy:
- In layer repositories, do not create a repository-root virtual environment. Use the shared layer runtime environment at `.digital-runtime/layers/python-runtime/venv`.
- In app repositories, do not use `venv` or `.venv` at repository root. Use one dedicated runtime environment under `.digital-runtime/layers/<app-runtime>/venv`.
- Do not create parallel environments for the same runtime intent.
- Install notebook dependencies using the active runtime interpreter and pip from that interpreter.
- Register and select the kernel from the active runtime interpreter.

Recommended setup commands:

```
make layer-venv-sync
```

Layer repository kernel registration example:

```
source .digital-runtime/layers/python-runtime/venv/bin/activate
python3 -m ipykernel install --user --name python-runtime --display-name "Python (python-runtime)"
```

App repository dedicated runtime example:

```
python3 -m venv .digital-runtime/layers/<app-runtime>/venv
source .digital-runtime/layers/<app-runtime>/venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m ipykernel install --user --name <app-runtime> --display-name "Python (<app-runtime>)"
```

Dependency source policy:
- Layer repositories: dependencies are declared in skill-level `requirements.txt` files and synchronized via `make layer-venv-sync`.
- App repositories: dependencies are declared in `requirements.txt` or `pyproject.toml` and installed only into `.digital-runtime/layers/<app-runtime>/venv`.

Minimal `requirements.txt` snippet for notebooks:

```txt
# Minimal notebook and data-workflow runtime dependencies (pinned for reproducibility)
ipykernel==7.2.0
jupyter==1.1.1
numpy==2.4.2
pandas==3.0.1
matplotlib==3.10.8
```

Randomness:
- Fix seeds.
- Document nondeterminism if unavoidable.

Environment:
- All dependencies pinned in `requirements.txt` or `pyproject.toml`.
- Document Python version.

---

# 5. Data Handling Rules

- Do not hardcode absolute paths.
- Use relative paths from project root.
- Do not commit large datasets.
- Add large files to `.gitignore`.

Sensitive Data:
- Never commit PII.
- Never commit credentials.
- Use `.env` for secrets (ignored by Git).

---

# 6. Code Quality

- Keep cells small and focused.
- Avoid duplicate code.
- Move reusable logic into `src/`.
- Use type hints in Python modules.
- Use meaningful variable names.

---

# 7. Output & Cleanliness

Before committing:
- Clear all notebook outputs.
- Remove debugging prints.
- Remove exploratory scratch cells.

Recommended tools:
- `nbstripout`
- `pre-commit`
- `nbqa`

---

# 8. Version Control Best Practices

- Do not commit large binary outputs.
- Use text-based diff tools if possible.
- Consider Jupytext pairing for serious projects.

Optional:
- Pair notebooks with `.py` files via Jupytext.

---

# 9. Testing Strategy

- Core logic must be tested in `tests/`.
- Do not test logic inside notebooks.
- Notebooks may have smoke tests in CI:
  - Execute via `nbconvert --execute`.

Example CI step:

```
jupyter nbconvert --to notebook --execute notebooks/01_data_exploration.ipynb
```

---

# 10. Visualization Standards

- Label axes.
- Add titles.
- Avoid unreadable default styles.
- Ensure plots render without interactive backend requirements unless documented.

---

# 11. Performance Guidelines

- Avoid loading full datasets unnecessarily.
- Use sampling for exploration.
- Avoid recomputing expensive steps.
- Cache intermediate artifacts where reasonable.

---

# 12. Anti-Patterns (Prohibited)

- ❌ Business logic only in notebooks
- ❌ Hardcoded secrets
- ❌ Manual execution order dependency
- ❌ Hidden state reliance
- ❌ Gigantic notebook files with no structure
- ❌ Mixing exploration and production logic

---

# 13. CI / Automation (Recommended)

Add notebook validation to CI:

- Lint with `nbqa`
- Execute critical notebooks
- Validate import structure
- Enforce output stripping

Minimum validity checks to prevent GitHub "Invalid Notebook" errors:

```bash
# 1) strict JSON parse
python3 -m json.tool notebooks/<notebook>.ipynb >/dev/null

# 2) notebook schema parse (nbformat)
python3 -c "import nbformat; nbformat.read('notebooks/<notebook>.ipynb', as_version=4)"

# 3) optional execution check (headless)
jupyter nbconvert --to notebook --execute notebooks/<notebook>.ipynb
```

If a notebook is generated or edited by tooling, always re-run checks (1) and (2) before commit.

---

# 14. Collaboration Rules

- Add Markdown explanations.
- Write for future readers.
- Document assumptions.
- Keep notebooks readable and educational.

---

# 15. Minimum Quality Gate Before Merge

- Notebook runs top-to-bottom
- Outputs cleared
- Dependencies documented
- No secrets committed
- Core logic extracted to `src/`
- Tests exist for business logic
