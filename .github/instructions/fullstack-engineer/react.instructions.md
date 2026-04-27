---
name: "Fullstack-engineer / Reacts"
description: "Enterprise Specification: React & React Native Frontend Standard"
layer: digital-generic-team
---
# Enterprise Specification: React & React Native Frontend Standard

---

## 1. Purpose

This document defines the enterprise standard for building frontend applications using React (web) and React Native (mobile).

The objective is to ensure:

* Unified frontend architecture across web and mobile
* Maximum code reuse where appropriate
* Consistent developer experience and tooling
* Scalable, maintainable, and performant applications
* Alignment with backend, design systems, and platform standards

---

## 2. Scope

This specification applies to:

* Web applications using React
* Mobile applications using React Native
* Shared component libraries
* Cross-platform design systems
* Fullstack applications using React-based frontends

---

## 3. Technology Standard

Approved technologies include:

### 3.1 Web

* React (latest stable version)
* TypeScript (mandatory)
* Vite / Webpack (approved build tools)

### 3.2 Mobile

* React Native (latest stable version)
* Expo (preferred for standard apps) or React Native CLI

---

## 4. Core Principles

* Component-driven development
* Cross-platform reuse where practical
* Separation of business logic from UI
* Unidirectional data flow
* Performance and accessibility by default

---

## 5. Architecture Standards

### 5.1 Monorepo Recommendation

Projects SHOULD use a monorepo structure:

```text
apps/
  web/
  mobile/
packages/
  ui/
  hooks/
  services/
  utils/
```

---

### 5.2 Layered Architecture

```text
UI Components → Hooks / State → Services → Backend APIs
```

---

### 5.3 Feature-Based Organization

* Code MUST be organized by domain/feature
* Shared logic MUST reside in reusable packages

---

## 6. Component Design

### 6.1 Cross-Platform Components

* Shared components SHOULD be implemented where feasible
* Platform-specific components MUST be isolated

---

### 6.2 UI Layer

* Web uses HTML/CSS-based components
* Mobile uses React Native primitives

---

### 6.3 Styling

Approved approaches:

* Web:

  * CSS Modules
  * Tailwind CSS
  * Styled components

* Mobile:

  * React Native StyleSheet
  * Theming systems

Design tokens MUST be shared across platforms.

---

## 7. State Management

* Local state MUST use React hooks
* Global state SHOULD be minimized
* Shared state logic SHOULD be reusable across platforms

---

## 8. Navigation

* Web: routing libraries (e.g., React Router)
* Mobile: navigation libraries (e.g., React Navigation)

Navigation patterns MUST be consistent with platform conventions.

---

## 9. API Integration

* API communication MUST be centralized in service layers
* Data fetching MUST follow consistent patterns
* Error handling MUST be standardized

---

## 10. Performance Standards

### 10.1 Web

* Code splitting and lazy loading MUST be used
* Bundle size MUST be optimized

### 10.2 Mobile

* Rendering MUST be optimized for smooth UI
* Memory and battery usage MUST be controlled

---

## 11. Accessibility (A11y)

* Web MUST comply with WCAG guidelines
* Mobile MUST follow platform accessibility standards
* Keyboard and screen reader support MUST be ensured

---

## 12. Security Standards

* Input validation MUST be enforced
* Sensitive data MUST NOT be exposed
* Secure storage MUST be used on mobile (Keychain/Keystore)

---

## 13. Testing Standards

### 13.1 Test Types

* Unit tests (components, hooks)
* Integration tests
* End-to-end tests

---

### 13.2 Tooling

Approved tools include:

* Jest
* React Testing Library
* Playwright / Cypress (web)
* Detox (mobile)

---

## 14. Build and Tooling

* Build pipelines MUST be standardized
* Linting and formatting MUST be enforced
* Type safety MUST be ensured via TypeScript

---

## 15. CI/CD and Deployment

### 15.1 Web

* Automated builds and deployments
* CDN-based distribution

### 15.2 Mobile

* Automated builds for iOS and Android
* Distribution via:

  * App Store
  * Google Play
  * Enterprise channels

---

## 16. Observability

* Error tracking MUST be implemented
* Performance monitoring SHOULD be enabled
* User behavior analytics MAY be used

---

## 17. Documentation

* Components MUST be documented (e.g., Storybook)
* Shared libraries MUST include usage guidelines
* Setup and development workflows MUST be documented

---

## 18. Governance

* Code reviews MUST enforce standards
* Architecture MUST be consistent across platforms
* Design system compliance MUST be validated
* Exceptions MUST be documented and approved

---

## 19. Further Reading

* [React Documentation](https://react.dev?utm_source=chatgpt.com)
* [React Native Docs](https://reactnative.dev?utm_source=chatgpt.com)
* [Expo Docs](https://docs.expo.dev?utm_source=chatgpt.com)
* [TypeScript Docs](https://www.typescriptlang.org/docs?utm_source=chatgpt.com)

---

## 20. Summary

This standard ensures unified, scalable, and high-quality frontend development across web and mobile using React and React Native within enterprise environments.
