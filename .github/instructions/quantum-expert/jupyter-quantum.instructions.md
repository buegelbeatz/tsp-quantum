---
name: "Quantum-expert / Jupyter-quantums"
description: "Qiskit Quantum Implementation — Jupyter Notebook Template Instructions"
layer: digital-generic-team
---
# Qiskit Quantum Implementation — Jupyter Notebook Template Instructions

These rules define how quantum algorithms implemented with **Qiskit** must be structured
inside Jupyter Notebooks in this repository.

The goals are:

- Reproducibility  
- Deterministic execution  
- Clear separation of quantum and classical logic  
- Hardware-agnostic execution (simulator + optional real backend)  
- CI-friendly validation  
- Research-grade documentation quality  

This template applies to all quantum notebooks.

---

# 1. Project Structure (Mandatory)

Quantum notebooks must follow this structure:

```
project-root/
│
├── notebooks/
│   ├── 01_problem_definition.ipynb
│   ├── 02_quantum_circuit.ipynb
│   ├── 03_execution_and_results.ipynb
│   └── 04_analysis.ipynb
│
├── src/
│   ├── quantum/
│   │   ├── circuits.py
│   │   ├── algorithms.py
│   │   └── backends.py
│   ├── classical/
│   └── utils/
│
├── results/
├── figures/
├── requirements.txt / pyproject.toml
├── README.md
└── Makefile
```

Rules:

- Quantum circuit construction must live in `src/quantum/`.
- Notebooks orchestrate experiments and document reasoning.
- Avoid large quantum circuit definitions directly inside notebook cells.
- No hidden state between cells.

---

# 2. Notebook Structure (Mandatory Sections)

Each quantum notebook must include:

---

## 2.1 Title & Metadata

- Algorithm name
- Problem description
- Qiskit version
- Backend type (simulator / hardware)
- Random seed (if applicable)

---

## 2.2 Environment & Version Block (Mandatory)

```python
import qiskit
import numpy as np
import random
import platform

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

print("Qiskit:", qiskit.__version__)
print("Platform:", platform.platform())
```

Rules:

- Set deterministic seeds where applicable.
- Print versions for reproducibility.
- Do not rely on implicit randomness.

---

## 2.3 Problem Definition (Classical)

- Define mathematical formulation.
- Define input parameters.
- Define constraints clearly.
- Separate classical preprocessing from quantum construction.

---

## 2.4 Quantum Circuit Construction (Modularized)

Quantum circuits must be created via functions:

```python
from src.quantum.circuits import build_circuit

qc = build_circuit(params)
```

Rules:

- No monolithic 200-line cell circuits.
- Use clear naming for registers.
- Document qubit mapping.
- Avoid hardcoded magic numbers.

---

## 2.5 Backend Selection (Hardware-Agnostic)

Must support:

- Statevector simulator
- QASM simulator
- Optional real backend

Example pattern:

```python
from src.quantum.backends import get_backend

backend = get_backend("statevector")
result = backend.run(qc, shots=1024)
```

Rules:

- Backend selection must be configurable.
- Do not hardcode IBM credentials.
- Real backend usage must be optional.

---

## 2.6 Execution

Clearly separate:

- Circuit creation
- Transpilation
- Execution
- Result extraction

Example structure:

```python
from qiskit import transpile

tqc = transpile(qc, backend)
job = backend.run(tqc, shots=1024)
result = job.result()
counts = result.get_counts()
```

Rules:

- Explicitly transpile before execution.
- Fix number of shots.
- Document shot count reasoning.

---

## 2.7 Measurement & Decoding

- Explain bitstring interpretation.
- Provide classical decoding function.
- Avoid ambiguous bit ordering.
- Clearly define mapping (little-endian vs big-endian).

---

## 2.8 Visualization

- Use consistent plotting style.
- Label axes clearly.
- Save figures programmatically:

```python
plt.savefig("figures/quantum_result.svg", dpi=300)
```

Rules:

- Do not manually edit figures.
- All figures must be reproducible.

---

## 2.9 Classical Post-Processing

- Separate from quantum execution.
- Compute metrics clearly.
- Include confidence intervals where applicable.
- Report variance across runs if stochastic.

---

# 3. Reproducibility Requirements

Mandatory:

- Fixed random seed.
- Pinned Qiskit version.
- Deterministic shot count.
- No implicit backend selection.
- No reliance on external runtime state.

Notebook must pass:

- Kernel restart
- Run all cells successfully

Runtime and kernel policy:
- In layer repositories, use `.digital-runtime/layers/python-runtime/venv` and do not create repository-root `venv` or `.venv`.
- In app repositories, use a dedicated runtime under `.digital-runtime/layers/<app-runtime>/venv`.
- Install dependencies only through the active runtime interpreter.
- Register the notebook kernel from the active runtime interpreter.

---

# 4. Backend Governance

## Simulator Usage

Preferred for:
- Algorithm validation
- Development
- CI testing

Must use:

- Aer simulator (statevector or qasm)

---

## Real Hardware Usage (Optional)

Rules:

- Credentials must be environment-based.
- Never hardcode API keys.
- Hardware execution must be clearly separated from simulation.
- Document noise considerations.

---

# 5. CI Compatibility

CI must be able to:

- Execute notebooks in headless mode.
- Use simulator only.
- Fail on execution errors.

Recommended:

```
jupyter nbconvert --to notebook --execute notebooks/02_quantum_circuit.ipynb
```

Mandatory validity checks before commit:

```bash
# strict JSON validity
python3 -m json.tool notebooks/<quantum-notebook>.ipynb >/dev/null

# nbformat structural validity
python3 -c "import nbformat; nbformat.read('notebooks/<quantum-notebook>.ipynb', as_version=4)"
```

Real hardware execution must not be part of CI.

---

# 6. Code Quality Rules

- Use type hints in `src/`.
- Avoid deprecated Qiskit APIs.
- Keep functions small and testable.
- Use clear naming for:
  - qubits
  - classical registers
  - parameters

---

# 7. Algorithm Documentation

Each algorithm notebook must include:

- Mathematical background
- Circuit diagram
- Complexity discussion
- Expected theoretical outcome
- Comparison with classical baseline (if applicable)

---

# 8. Anti-Patterns (Prohibited)

- ❌ Hardcoded IBM tokens
- ❌ Hidden randomness
- ❌ Inline monolithic circuit definitions
- ❌ Mixing classical logic and quantum logic in one large cell
- ❌ Relying on outdated Qiskit modules
- ❌ Executing real hardware in CI
- ❌ Manual result editing

---

# 9. Recommended Enhancements

- Parameter sweep experiments
- Visualization of statevector amplitudes
- Heatmaps of measurement distributions
- Repeated runs with statistical summary
- Noise simulation comparison
- Benchmark vs classical solution

---

# 10. Optional Enterprise Extensions

- Dockerized quantum environment
- Version-locked Qiskit container
- Automated experiment logging
- Structured result export (CSV/JSON)
- Integration with experiment tracking tools

---

# 11. Philosophy

A quantum notebook is:

- A reproducible scientific artifact
- A documented algorithmic experiment
- A deterministic computational pipeline
- Not a scratchpad

Quantum logic belongs in modular functions.
The notebook documents the reasoning.
The backend is abstracted.
Results are reproducible.