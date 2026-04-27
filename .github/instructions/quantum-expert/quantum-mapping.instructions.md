---
name: "Quantum-expert / Quantum-mappings"
description: "Classical → Quantum Replacement Framework"
layer: digital-generic-team
---
# Classical → Quantum Replacement Framework  
(Scalability, Performance Thresholds & Hybrid Design Guidance)

This document describes the classical-to-quantum mapping guidelines with:

- Scalability analysis
- Performance gain modeling
- Break-even criteria
- Hardware feasibility thresholds
- Hybrid architecture recommendations
- Codebase analysis workflow

This framework is intended for analyzing existing systems
and issuing structured recommendations for potential quantum integration.

---

# 1. Core Decision Philosophy

A quantum replacement is justified only if:

1. The asymptotic complexity improves meaningfully.
2. The problem size is large enough to exploit that improvement.
3. State preparation and measurement costs do not negate the speedup.
4. Hardware depth and qubit requirements are realistic.
5. A hybrid architecture is viable.

If these criteria are not satisfied → remain classical.

---

# 2. Scalability Analysis Framework

When evaluating an algorithm, perform:

## 2.1 Classical Complexity Baseline

Document:

- Time complexity (Big-O)
- Space complexity
- Dominant constant factors
- Parallelization potential
- Current hardware performance

Example:

```
Classical: O(N^2)
Parallelizable: yes
Memory bound: no
```

---

## 2.2 Quantum Candidate Complexity

Identify:

- Theoretical quantum complexity
- Oracle cost
- State preparation cost
- Measurement cost
- Circuit depth
- Qubit count

Example:

```
Quantum: O(√N) via Grover
State prep: O(N)
Measurement: O(log N)
```

If state preparation is O(N), the speedup may vanish.

---

# 3. Break-Even Analysis

## 3.1 Theoretical Speedup Threshold

Quantum advantage typically becomes meaningful only when:

- N is sufficiently large
- Classical parallelization saturates
- Overhead terms are negligible relative to asymptotic gain

For quadratic speedup (Grover-like):

Break-even condition:

```
c1 * N  ≈  c2 * √N + encoding_cost
```

If encoding_cost ≈ O(N),
no advantage.

---

## 3.2 Practical NISQ Constraints

In current hardware (NISQ era):

- Qubit count: < 100–1000 practical logical qubits
- Circuit depth: limited by coherence time
- Error mitigation required
- Noise grows with depth

Thus:

Large asymptotic improvements that require deep circuits
are currently not practical.

---

# 4. Replacement Threshold Guidelines

Use these heuristics:

| Scenario | Recommendation |
|----------|---------------|
| N < 10³ | Stay classical |
| N 10³–10⁵ | Evaluate hybrid, simulate first |
| N > 10⁵ with quadratic classical cost | Consider Grover/QAOA |
| Sparse linear system, dimension > 10⁴ | Evaluate HHL (simulation first) |
| Monte Carlo with very high precision demand | Evaluate amplitude estimation |
| Highly parallel classical algorithm | Likely no quantum benefit |

---

# 5. Hardware Feasibility Checklist

Before proposing replacement, compute:

- Required qubits
- Circuit depth
- Gate count
- Error rate tolerance
- Connectivity requirements

If:

- Required qubits > realistic hardware
- Circuit depth > coherence window
- Error amplification unacceptable

→ Recommend classical or hybrid approach.

---

# 6. Input Encoding Cost Analysis (Critical)

Quantum advantage disappears if:

State preparation complexity ≥ classical algorithm complexity.

Document:

- Encoding method
- Data size
- Required amplitude encoding cost
- Classical preprocessing time

If encoding cost scales linearly with N
and quantum gives √N,
benefit only exists for very large N.

---

# 7. Hybrid Architecture Pattern (Preferred Model)

Most realistic performance gains come from:

Classical preprocessing  
↓  
Quantum subroutine (core complexity bottleneck)  
↓  
Classical post-processing  

Examples:

- Classical graph pruning → QAOA core → classical refinement
- Classical sampling → amplitude estimation → classical aggregation
- Classical clustering → quantum kernel evaluation → classical SVM

Never propose full quantum replacement unless mathematically justified.

---

# 8. Codebase Analysis Workflow

When analyzing existing code:

## Step 1 — Identify Hotspots

- Profile runtime
- Identify dominant complexity section
- Extract algorithmic core

## Step 2 — Classify Algorithm Type

Map hotspot to:

- Search
- Optimization
- Linear algebra
- Sampling
- Simulation
- Graph
- Cryptographic

## Step 3 — Evaluate Quantum Candidate

Document:

- Matching quantum algorithm
- Asymptotic improvement
- Encoding cost
- Qubit requirement
- Circuit depth
- Hardware availability

## Step 4 — Estimate Break-Even

Estimate:

- Classical runtime at scale N
- Quantum runtime + overhead
- Required N for crossover

If crossover N unrealistic → do not replace.

---

# 9. Performance Modeling Requirements

Every proposal must include:

- Complexity comparison table
- Qubit estimate
- Circuit depth estimate
- Encoding complexity
- Measurement cost
- Noise impact estimate
- Classical fallback performance

No proposal without quantified modeling.

---

# 10. Scalability Risk Assessment

Assess:

- Sensitivity to noise
- Scalability of qubit requirement
- Depth growth rate
- Connectivity demands
- Error correction overhead (future hardware)

If quantum depth grows faster than logarithmic
and no near-term fault-tolerance exists,
flag as long-term research only.

---

# 11. Recommendation Categories

After analysis, classify:

## A — Not Suitable
No meaningful theoretical or practical advantage.

## B — Research Candidate
Theoretical speedup exists, but hardware infeasible currently.

## C — Hybrid Candidate
Quantum subroutine plausible in near-term hybrid architecture.

## D — Strong Candidate
Clear asymptotic improvement and feasible encoding.

---

# 12. Reporting Format (Mandatory)

Each classical-to-quantum evaluation must include:

1. Classical baseline complexity
2. Quantum candidate algorithm
3. Encoding complexity
4. Qubit requirement
5. Circuit depth estimate
6. NISQ feasibility
7. Break-even analysis
8. Hybrid architecture design (if applicable)
9. Risk assessment
10. Final recommendation category (A–D)

---

# 13. Anti-Patterns (Strictly Prohibited)

- ❌ Claiming “quantum faster” without asymptotic analysis
- ❌ Ignoring encoding cost
- ❌ Comparing theoretical quantum vs naive classical
- ❌ Ignoring classical parallel scaling
- ❌ Ignoring hardware depth limits
- ❌ Proposing full replacement when hybrid suffices

---

# 14. Strategic Guidance

Quantum acceleration is most promising when:

- Classical cost grows superlinearly (≥ O(N²))
- Problem is oracle-based
- Sampling precision is bottleneck
- Problem maps naturally to Hamiltonian formulation
- Data can be encoded efficiently

Quantum acceleration is unlikely when:

- Problem is memory-bound
- Problem is I/O-bound
- Classical algorithm is near-linear and parallelizable
- Encoding cost dominates runtime

---

# 15. Philosophy

Quantum computing is not a drop-in performance upgrade.

It is a specialized computational model
with potential asymptotic advantages
under strict structural constraints.

Scalability analysis and hybrid design
are mandatory before proposing replacement.
