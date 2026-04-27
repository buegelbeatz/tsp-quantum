---
name: "Language-expert / Rusts"
description: "Rust Development Instructions"
layer: digital-generic-team
---
# Rust Development Instructions

These rules apply to all Rust code in this repository.

---

## 1. Toolchain & Edition

- Use **Rust stable** (as pinned by `rust-toolchain.toml` if present).
- Use **Rust 2021 edition** (or repository-defined edition).
- Do not rely on nightly features unless explicitly approved and documented.

---

## 2. Project Structure

Typical layout:

```
src/
  lib.rs
  main.rs
  module.rs
tests/
  integration_test.rs
benches/
examples/
Cargo.toml
```

Rules:
- Keep `lib.rs` and `main.rs` small (wire-up only).
- Put reusable logic in modules under `src/`.
- Prefer feature flags for optional functionality.

---

## 3. Formatting & Linting (Mandatory)

- Format with **rustfmt** (CI must match).
- Lint with **clippy** and fix warnings where feasible.
- Do not suppress clippy lints without a clear rationale.

Commands (project standard):
- `cargo fmt`
- `cargo clippy -- -D warnings`

---

## 4. Naming Conventions

- Crates/modules/files: `snake_case`
- Functions/variables: `snake_case`
- Types (struct/enum/trait): `PascalCase`
- Constants/statics: `UPPER_SNAKE_CASE`
- Lifetimes: short and meaningful (`'a`, `'ctx`)

---

## 5. Error Handling

- Do not use `panic!` for recoverable errors.
- Prefer `Result<T, E>` for fallible operations.
- Use `?` for propagation.
- Use meaningful error types:
  - Prefer `thiserror` if already used in the repo.
  - Otherwise use a small custom `enum` error type.
- Add context at boundaries (CLI/API), not in every helper.

Example:

```rust
pub fn parse_port(s: &str) -> Result<u16, ParsePortError> {
    let port: u16 = s.parse().map_err(|_| ParsePortError::InvalidNumber)?;
    if port == 0 {
        return Err(ParsePortError::OutOfRange);
    }
    Ok(port)
}
```

---

## 6. Ownership, Borrowing, and API Design

- Prefer borrowing (`&T`) over cloning.
- Avoid unnecessary allocations.
- Prefer `&str` over `String` for input parameters when ownership is not required.
- Use `String`/`Vec<T>` in return types when ownership is required.
- Avoid exposing internal implementation details in public APIs.

---

## 7. Safety Rules

- Avoid `unsafe` unless strictly necessary.
- If `unsafe` is used:
  - encapsulate it in a small, well-tested module
  - document invariants and safety requirements
  - provide safe public wrappers
- Do not use `unwrap()` / `expect()` in library code except in tests or when invariants are proven and documented.

---

## 8. Concurrency

- Prefer safe concurrency primitives:
  - `std::sync::{Arc, Mutex, RwLock}`
  - channels (`std::sync::mpsc` or `tokio::sync` if async)
- Document thread-safety expectations.
- Avoid shared mutable global state.

---

## 9. Async (if applicable)

- Follow the repo’s async runtime (Tokio/async-std).
- Do not block in async contexts.
- Prefer `async/await` and structured concurrency patterns.
- Use timeouts where appropriate for IO.

---

## 10. Documentation

- Public items must have Rustdoc comments (`///`).
- Document:
  - purpose and behavior
  - errors returned
  - safety invariants (especially around `unsafe`)
- Include examples for non-trivial public APIs.

Example:

```rust
/// Parses a user ID from a string.
///
/// # Errors
/// Returns `ParseUserIdError` if the input is not a valid ID.
pub fn parse_user_id(s: &str) -> Result<u64, ParseUserIdError> { ... }
```

---

## 11. Testing

- Use `cargo test`.
- Tests must be deterministic and fast.
- Unit tests go next to code (`mod tests`).
- Integration tests go next to the module they validate whenever feasible.
- All test file names must start with `test_`.
- Prefer table-driven tests for multiple cases.
- Store temporary and cache test artifacts only under `.tests/rust/`.

Example:

```rust
#[test]
fn parse_port_rejects_invalid() {
    assert!(parse_port("abc").is_err());
}
```

---

## 12. Dependencies

- Keep dependencies minimal.
- Do not add new crates without justification.
- Prefer widely used, well-maintained crates.
- Keep `Cargo.lock` committed for applications/binaries (follow repo policy).

---

## 13. Performance Guidelines

- Prefer clarity first; optimize only when needed.
- Avoid premature micro-optimizations.
- Use iterators where they improve clarity.
- Benchmark with `criterion` if the repo uses it.

---

## 14. Prohibited Practices

- No `unsafe` without documentation + tests
- No `unwrap()`/`expect()` in production library code
- No panics for recoverable errors
- No global mutable state
- No commented-out dead code
- No TODOs without issue references

---

## 15. PR Requirements

Before merging:
- `cargo fmt` clean
- `cargo clippy` clean (no warnings, where feasible)
- `cargo test` passes
- New/changed behavior includes tests
- Public API changes documented
- Any `unsafe` includes explicit safety docs and tests

---

## 16. Inline Documentation

- Add `///` Rustdoc for all public items.
- Add inline comments for non-obvious logic and safety invariants.
- Complex algorithms should include short implementation notes near the code.
