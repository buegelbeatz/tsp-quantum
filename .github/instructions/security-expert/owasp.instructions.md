---
name: "Security-expert / Owasps"
description: "OWASP Secure Development Instructions"
layer: digital-generic-team
---
# OWASP Secure Development Instructions


These rules apply to all code in this repository.  
Security is mandatory and must be considered by default in every change.

---

# 1. General Security Principles

- Follow **OWASP Top 10** as baseline security guidance.
- Treat all external input as untrusted.
- Apply the principle of **least privilege**.
- Prefer secure defaults over convenience.
- Fail securely (no silent degradation).
- Do not expose internal implementation details in errors.

---

# 2. Input Validation (OWASP A03: Injection, A01: Broken Access Control)

- Validate all external inputs:
  - HTTP requests (body, query, params)
  - File uploads
  - Environment variables
  - CLI arguments
  - Database inputs
- Prefer allowlists over blocklists.
- Use schema validation libraries where available.
- Reject malformed input early.

---

# 3. Injection Prevention (SQL, OS, LDAP, etc.)

- Never build queries via string concatenation.
- Always use:
  - Prepared statements
  - Parameterized queries
  - ORM safe bindings
- Never pass unsanitized input into:
  - Shell commands
  - SQL queries
  - Dynamic evaluation
- Avoid `eval`-like functionality entirely.

---

# 4. Authentication & Authorization (OWASP A07)

- Do not implement custom crypto or authentication logic.
- Use established authentication libraries.
- Enforce authorization checks server-side.
- Validate permissions at every boundary.
- Never rely solely on client-side authorization.
- Protect sensitive endpoints with proper access control.

---

# 5. Sensitive Data Handling (OWASP A02)

- Never hardcode secrets.
- Store secrets in secure environment variables or secret managers.
- Do not log:
  - Passwords
  - Tokens
  - API keys
  - Personal identifiable information (PII)
- Encrypt sensitive data at rest and in transit (TLS required).
- Use strong hashing for passwords (bcrypt/argon2).

---

# 6. Error Handling & Logging (OWASP A09)

- Do not expose stack traces in production.
- Provide generic error messages to users.
- Log detailed errors internally.
- Ensure logs do not contain sensitive data.
- Implement audit logging for security-relevant events.

---

# 7. Cross-Site Scripting (XSS) Prevention (OWASP A03)

- Escape output by default.
- Use framework auto-escaping mechanisms.
- Never trust user-supplied HTML.
- Avoid dangerouslySetInnerHTML or equivalent unless strictly required and sanitized.

---

# 8. Cross-Site Request Forgery (CSRF)

- Enable CSRF protection where applicable.
- Use SameSite cookies.
- Validate CSRF tokens on state-changing operations.

---

# 9. Dependency & Supply Chain Security (OWASP A06)

- Keep dependencies up to date.
- Use lockfiles.
- Monitor vulnerabilities (SCA tools).
- Avoid unmaintained libraries.
- Do not introduce new dependencies without review.

---

# 10. Secure Configuration (OWASP A05)

- Disable debug mode in production.
- Use secure HTTP headers:
  - Content-Security-Policy
  - X-Frame-Options
  - X-Content-Type-Options
  - Strict-Transport-Security
- Do not expose admin interfaces publicly.
- Use rate limiting where applicable.

---

# 11. File Upload Security

- Validate file type and size.
- Do not trust file extensions.
- Store uploads outside the web root if possible.
- Scan files if the system supports it.

---

# 12. Cryptography

- Use well-known, battle-tested libraries.
- Do not implement custom encryption.
- Use secure random number generators.
- Enforce minimum key lengths.
- Deprecate weak algorithms (MD5, SHA1, etc.).

---

# 13. Secure Coding Practices

- Avoid global mutable state.
- Use secure defaults in configuration.
- Apply input sanitization consistently.
- Do not disable security features without documented justification.

---

# 14. Prohibited Practices

- No hardcoded credentials
- No disabled TLS verification
- No plaintext password storage
- No custom crypto implementations
- No unvalidated redirects
- No silent security bypasses
- No exposing internal errors to clients

---

# 15. Code Review & PR Requirements

Before merging:

- Security implications reviewed
- No hardcoded secrets
- Input validation implemented
- Authorization enforced
- No injection vulnerabilities
- Dependencies checked for known vulnerabilities
- Logging reviewed for sensitive data leakage

---

# 16. Security Testing

- Include unit tests for validation logic.
- Include negative test cases (invalid/malicious input).
- Perform security-focused testing for:
  - Authentication
  - Authorization
  - Injection points
- Run static analysis/security scanners where configured.

---

# 17. Incident Readiness

- Log security events.
- Enable monitoring/alerting for abnormal behavior.
- Ensure logs are tamper-resistant.
- Document response procedures separately.

---

Security is not optional.  
All code must assume hostile input and hostile environments.
