---
name: "Test-expert / E2e-testss"
description: "E2E Testing Instructions"
applyTo: "**/{e2e,tests}/**/*.{py,ts,js,md,yml,yaml},**/*e2e*.{py,ts,js}"
layer: digital-generic-team
---
# E2E Testing Instructions


**Overview:** Use this guide for browser-level end-to-end (E2E) tests across authentication, routing, and critical user journeys.

**Test Naming, Location, and Output:** 
Core test specification (naming, location, artifact output) is centralized in `.github/instructions/testing/testing.instructions.md`.  
**If this section conflicts with that file, the testing.instructions.md takes priority.**

---

## 1) Goals and Scope

E2E tests must verify:
- Critical user flows from a real browser perspective.
- Integration boundaries (UI, auth provider, proxy/sidecar, API behavior).
- Security-relevant behavior (redirects, cookie handling, session lifecycle).

E2E tests must not:
- Replace unit/integration tests.
- Depend on unstable external services when stubs/mocks are sufficient.
- Assert fragile implementation details (DOM internals, animation timing).

## 2) Tooling Strategy

Preferred approach:
1. Primary browser automation: Selenium or Playwright (project choice).
2. API preconditions/fixtures: direct setup via test helpers or HTTP APIs.
3. Real-device/mobile edge flows: dedicated device tests, not desktop-only emulation.

When Selenium Headless makes sense:
- Regression checks for desktop login/redirect/session behavior.
- Cookie and header handoff verification.
- Stable smoke tests in CI.

When Selenium Headless is not enough:
- iOS-specific browser/OS behavior (Safari passkeys, camera permissions, QR scanner handoff).
- Real passkey platform authenticator behavior.
- Camera-driven QR scanning flow.

## 3) WebAuthn, iOS, and QR Scanning Reality

Important limitations:
- Headless desktop browsers cannot reliably validate real iOS Safari behavior.
- Desktop emulation of mobile user agents is not equivalent to iOS runtime behavior.
- QR scanning in production-like flows requires camera + second-device interaction.

Recommended split:
- **Tier A (CI, deterministic):**
  - Desktop E2E flow with mocked or test-mode authenticator behavior.
  - Redirect and cookie/session continuity checks.
- **Tier B (nightly/manual/real device):**
  - iOS Safari + passkey + camera QR scanning.
  - Device handoff validation (desktop -> mobile -> desktop).

For iOS automation at scale, evaluate Appium + Safari on real devices/simulator, but expect higher maintenance and lower determinism than desktop CI tests.

## 4) Security and OWASP-Oriented Assertions

E2E suites must include checks for:
- No sensitive tokens in browser URL after authentication completes.
- Secure cookie behavior (`HttpOnly`, `Secure`, `SameSite` according to deployment policy).
- Redirect allowlist behavior (no open redirects).
- Session invalidation/expiry behavior.
- Proper unauthorized handling (401/403 and controlled redirect behavior).

Do not store tokens in test logs, screenshots, or artifacts.

## 5) Test Design Principles

- Use deterministic fixtures and explicit timeouts.
- Prefer explicit polling with bounded retries over arbitrary sleeps.
- Keep tests small and scenario-focused.
- Use stable selectors (`data-testid` or semantic selectors).
- Capture diagnostics on failure (screenshots, console logs, network events) without leaking secrets.

## 6) Test Naming and Structure

- Test files must start with `test_`.
- Group by business flow, not by page object only.
- Use clear scenario names:
  - `test_admin_bootstrap_redirects_to_register`
  - `test_desktop_login_completes_without_token_in_url`
  - `test_session_expiry_redirects_to_login`

Suggested layout:
- `tests/e2e/desktop/` for CI-stable desktop tests.
- `tests/e2e/mobile/` for device-specific or Appium-backed tests.
- `tests/e2e/support/` for fixtures and helpers.

## 7) Environment and Data Management

- Use dedicated test environment variables; never hardcode secrets.
- Reset test state between runs when possible.
- Use short-lived test credentials and disposable data.
- Ensure every required key in `.env` is reflected in `.env.example`.

## 8) CI Policy

Recommended pipeline layering:
1. Unit tests (fastest).
2. Integration tests.
3. Desktop E2E smoke tests (headless).
4. Optional extended E2E (nightly or pre-release).
5. Real-device/mobile passkey/QR checks (scheduled or release-gate).

A failing security-critical E2E test should block releases.

## 9) Minimum Coverage for Auth-Critical Apps

At minimum, include E2E coverage for:
- Unauthenticated access -> correct auth redirect.
- Successful desktop login -> protected view visible.
- Registration completion -> session established without login loop.
- Invalid/expired session -> controlled re-auth flow.
- Token not present in final URL.

## 10) Maintenance Guidance

- Keep E2E tests version-aware for browser/tool upgrades.
- Quarantine flaky tests with issue tracking and owner assignment.
- Review failing E2E tests weekly; do not allow permanent flaky state.
- Prefer fixing root causes over adding retries.