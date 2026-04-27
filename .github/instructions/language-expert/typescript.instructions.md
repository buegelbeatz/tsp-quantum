---
name: "Language-expert / Typescripts"
description: "TypeScript Instructions (Node + React)"
layer: digital-generic-team
---
# TypeScript Instructions (Node + React)

These rules apply to all TypeScript code in this repository for **Node.js** and **React** (including Next.js if applicable).

---

## 1. Language & Tooling

- Use **TypeScript** for all new code.
- Follow repository configs as source of truth:
  - `tsconfig.json`
  - ESLint config
  - Prettier config
- Prefer **ESM** modules if the repo uses ESM (follow existing conventions).
- Do not hand-format against Prettier; always run formatter/linter.

---

## 2. Project Structure

Recommended layout:

```
src/
  server/            # Node backend (routes, services, db, jobs)
  client/            # React UI (components, pages, hooks)
  shared/            # Shared types/utilities
tests/
```

Rules:
- Avoid circular dependencies.
- Use path aliases if configured (e.g. `@/shared/...`) and keep imports consistent.
- Do not mix client-only and server-only code in shared modules.

---

## 3. Naming Conventions

- Files/folders: follow repo convention consistently (`kebab-case` or `camelCase`)
- Types / Interfaces / Classes / Enums: `PascalCase`
- Functions / variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE`
- Booleans: prefix with `is/has/can/should` (e.g., `isLoading`)

---

## 4. Formatting & Linting (Mandatory)

- Prettier for formatting.
- ESLint for linting.
- Fix lint errors before committing.
- No disabled lint rules unless documented with rationale.

---

## 5. Type Safety (Mandatory)

- Avoid `any`. Prefer `unknown` and narrow safely.
- Use strict typing (`"strict": true`).
- Prefer `readonly`, `as const`, discriminated unions.
- Avoid type assertions (`as X`) unless unavoidable and safe.

---

## 6. Exports & Public API

- Prefer **named exports** over default exports (React component default export is allowed if repo convention requires it).
- Keep public API small; avoid exporting internal helpers.
- Avoid deep imports across modules.

---

# Node.js (Backend) Rules

## 7. Environment Variables & Config

- Never hardcode secrets.
- Read env vars via a config module, not scattered across the codebase.
- Validate env vars at startup (use existing validator if present, e.g., Zod).

Example:

```ts
// If zod is part of the project:
import { z } from "zod";

const EnvSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().min(1),
});

export const env = EnvSchema.parse(process.env);
```

---

## 8. Error Handling (Node)

- Use typed errors (`class XError extends Error`) for expected failures.
- Do not swallow errors silently.
- Provide actionable messages at boundaries (HTTP handlers, job runners).
- Prefer structured logging (use the project logger, not `console.log`).

---

## 9. Async / Promises (Node)

- Prefer `async/await`.
- Always handle promise rejections.
- Use `Promise.all` for parallelizable independent operations.
- Avoid mixing callbacks with promises unless required by a library.

---

## 10. HTTP APIs (if applicable)

- Validate all request inputs (body, params, query) before use.
- Return consistent error shapes.
- Do not leak internal error details to clients.
- Keep handlers thin; put logic into services.

---

## 11. Security (Node)

- Never log secrets or tokens.
- Avoid `eval` / `new Function`.
- Sanitize inputs used in file paths, shell commands, or queries.
- Use safe defaults (rate limiting / helmet / CORS) if those libraries are part of the project.

---

# React (Frontend) Rules

## 12. Components & Hooks

- Prefer **function components** only.
- Keep components small and single-purpose.
- Extract reusable logic into custom hooks.
- Follow the Rules of Hooks (no conditional hook calls).

---

## 13. Component File Conventions

- Components: `PascalCase.tsx`
- Hooks: `useSomething.ts`
- Pure utilities: `.ts` (not `.tsx`)

---

## 14. Props & State

- Props must be fully typed.
- Prefer `type` for component props unless repo convention prefers `interface`.
- Prefer local state for UI-only concerns; lift state only when required.
- Avoid unnecessary re-renders:
  - Use `useMemo` / `useCallback` only when it measurably helps.
  - Prefer stable component boundaries over premature memoization.

Example:

```tsx
type ButtonProps = {
  label: string;
  onClick: () => void;
  disabled?: boolean;
};

export function Button({ label, onClick, disabled = false }: ButtonProps) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}>
      {label}
    </button>
  );
}
```

---

## 15. Side Effects & Data Fetching

- Side effects belong in `useEffect` (or a project-approved data fetching library).
- Always clean up effects when needed (subscriptions, timers).
- Prefer a dedicated data layer if present (React Query / SWR / Redux Toolkit Query).
- Do not fetch in render.

---

## 16. Forms & Validation

- Validate user input before submission.
- Prefer existing form libs if present (React Hook Form, Formik).
- Keep validation schemas close to the form.

---

## 17. Accessibility (A11y)

- All interactive elements must be keyboard accessible.
- Use semantic HTML first (`button`, `label`, `input`).
- Provide `aria-*` attributes when necessary.
- Images must have `alt` text unless purely decorative.

---

## 18. Styling

- Follow repo styling conventions (CSS Modules / Tailwind / styled-components).
- Do not introduce new styling systems without justification.
- Keep classnames readable and consistent.

---

# Testing (Node + React)

## 19. Testing Rules

**Test specification (naming, location, output) is defined in `.github/instructions/testing/testing.instructions.md`.**  
**If this section conflicts with that file, the testing.instructions.md takes priority.**

Key points:
- **Naming:** Test files must start with `test_` prefix.
- **Location:** Store tests as close as possible to the code they test (colocated).
- **Output:** All test artifacts (cache, reports, temp files) must go to `.tests/typescript/`.

---

Specifics for TypeScript/Node/React:
- Use the repo test runner (Jest / Vitest).
- Tests must be deterministic.
- Prefer Arrange–Act–Assert.
- Backend:
  - unit test services and utilities
  - integration test API routes if configured
- Frontend:
  - prefer React Testing Library for UI behavior tests (if configured)
  - test user behavior, not implementation details

---

## 20. Prohibited Practices

- No `any` in new code (unless explicitly approved)
- No non-null assertions (`!`) without justification
- No side effects at import time
- No commented-out dead code
- No secrets in code or logs

---

## 21. PR Requirements

Before merging:
- Typecheck passes (`tsc --noEmit` or repo equivalent)
- Lint passes with no errors
- Tests pass
- Code formatted with Prettier
- New/changed behavior has tests
- Public API changes documented

---

## 22. Inline Documentation

- Add JSDoc comments for exported functions, classes, hooks, and complex types.
- Document parameters, return values, and thrown errors where applicable.
- Add concise inline comments for non-obvious control flow and business rules.
