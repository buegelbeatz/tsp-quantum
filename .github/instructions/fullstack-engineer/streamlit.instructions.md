---
name: "Fullstack-engineer / Streamlits"
description: "Streamlit Project Instructions"
layer: digital-generic-team
---
# Streamlit Project Instructions  
(Project Structure, Reproducibility, and Best Practices)


These rules apply to all Streamlit apps in this repository.

Streamlit apps must be:
- Reproducible
- Secure (no secrets in code)
- Performant (cache where appropriate)
- Testable (logic separated from UI)
- Deployable (container/CI friendly)

---

## 1. Project Structure (Mandatory)

Use the following structure:

```
project-root/
│
├── app/
│   ├── Home.py                    # main entry / landing page
│   ├── pages/
│   │   ├── 01_Data_Explorer.py
│   │   ├── 02_Model_Insights.py
│   │   └── 03_Admin_Tools.py
│   ├── components/
│   │   ├── charts.py
│   │   ├── filters.py
│   │   └── layout.py
│   └── assets/
│       ├── styles.css
│       └── images/
│
├── src/
│   ├── data/
│   ├── services/
│   ├── models/
│   ├── utils/
│   └── __init__.py
│
├── tests/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
│
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
│
├── requirements.txt / pyproject.toml
├── README.md
├── Dockerfile (optional)
└── .gitignore
```

Rules:
- UI code lives in `app/`.
- Business logic must live in `src/`.
- Reusable UI elements go into `app/components/`.
- Pages must be placed in `app/pages/` and use ordered naming.

---

## 2. App Entry & Pages

- Use a single main entry file:
  - `app/Home.py` (or `app/app.py` if repo convention differs)
- Use multipage apps via `app/pages/`.
- Page filenames should start with an order prefix:
  - `01_...`, `02_...`

Rules:
- Keep each page focused and small.
- Avoid mixing heavy computation into UI code.

---

## 3. Configuration & Secrets (Mandatory)

### Secrets
- Never hardcode secrets in code.
- Use Streamlit secrets:
  - `.streamlit/secrets.toml` (must NOT be committed)
- Commit only:
  - `.streamlit/secrets.toml.example`

Add to `.gitignore`:

```
.streamlit/secrets.toml
.env
!.env.example
```

### Environment Variables
- Use `.env` for local development (ignored).
- Provide `.env.example` (committed).

Rules:
- Do not print secrets in logs/UI.
- Do not store credentials in session state.

---

## 4. Reproducibility

- Pin dependencies in `requirements.txt` or `pyproject.toml`.
- Document Python version.
- App must run deterministically from a clean environment.

---

## 5. Code Quality & Architecture

- Keep UI and logic separated:
  - `app/` = Streamlit rendering + orchestration
  - `src/` = domain logic, data access, algorithms
- Prefer pure functions in `src/` for testability.
- Avoid duplicated code; centralize shared logic.

---

## 6. State Management (Mandatory)

- Use `st.session_state` intentionally and sparingly.
- Initialize session keys in one place (per page or in a shared initializer).

Example:

```python
import streamlit as st

if "filters" not in st.session_state:
    st.session_state["filters"] = {"country": None, "year": None}
```

Rules:
- Do not store large dataframes in session state unless necessary.
- Prefer cached functions for heavy data.

---

## 7. Performance: Caching (Mandatory)

Use Streamlit caching appropriately:

- `@st.cache_data` for data loading / transformations
- `@st.cache_resource` for expensive resources (models, DB clients)

Examples:

```python
import streamlit as st
import pandas as pd

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)
```

```python
import streamlit as st

@st.cache_resource
def get_client():
    # create DB client / ML model / API client
    return object()
```

Rules:
- Always validate cache keys (inputs must fully define outputs).
- Avoid caching secrets.
- Invalidate caches when data sources change.

---

## 8. Data Handling Rules

- Do not hardcode absolute paths.
- Use project-relative paths.
- Do not commit large datasets.
- Use sampling for exploration views.

Sensitive data:
- Must not be displayed without explicit role-based access logic.
- Must not be logged.

---

## 9. UI Standards

- Each page must include:
  - Title
  - Short description (Markdown)
  - Clear controls (sidebar if appropriate)
- Label charts and tables clearly.
- Use consistent formatting across pages.

Recommended layout pattern:
- Sidebar: filters/settings
- Main: results/visualizations
- Bottom: details/downloads

---

## 10. Error Handling & User Feedback

- Fail gracefully:
  - Use `st.error()` for user-facing failures
  - Provide actionable guidance
- Do not show raw stack traces to users in production deployments.
- Log detailed errors server-side if logging is configured.

Example:

```python
try:
    df = load_data("data/processed/data.csv")
except FileNotFoundError:
    st.error("Data file not found. Please run the preprocessing step first.")
    st.stop()
```

---

## 11. Testing Strategy

- Test business logic in `src/` using `pytest`.
- Avoid testing Streamlit rendering directly unless necessary.
- Use integration tests for:
  - data loading pipelines
  - service clients
  - model inference

Optional:
- Add smoke checks that import pages without executing heavy logic.

---

## 12. Deployment & Containerization (Recommended)

- Provide a Dockerfile if the app is deployed via containers.
- App must bind to:
  - `0.0.0.0`
- Port should be configurable via env var.

Recommended Streamlit run:
- `streamlit run app/Home.py --server.address 0.0.0.0 --server.port ${PORT}`

---

## 13. Security (Mandatory)

- Never commit secrets.
- Never expose admin functionality without access controls.
- Avoid showing system internals (paths, tokens, stack traces).
- Validate external input before use (file uploads, query params).
- If file uploads exist:
  - enforce size/type constraints
  - do not trust extensions

---

## 14. Anti-Patterns (Prohibited)

- ❌ Business logic inside Streamlit UI blocks
- ❌ No caching for heavy operations
- ❌ Secrets in code or committed files
- ❌ Huge session_state objects without reason
- ❌ Unbounded file uploads
- ❌ Hardcoded ports/hosts for deployment

---

## 15. Minimum Quality Gate Before Merge

- App runs from clean environment
- Dependencies pinned
- No secrets committed
- Heavy operations cached appropriately
- Business logic extracted to `src/`
- Tests exist for core logic
- Pages follow naming + structure conventions