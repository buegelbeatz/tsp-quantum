---
name: "Css-expert / Tailwinds"
description: "Enterprise Specification: Tailwind CSS Framework Standard"
layer: digital-generic-team
---
# Enterprise Specification: Tailwind CSS Framework Standard

---

## 1. Purpose

This document defines the standardized usage of Tailwind CSS to ensure:

* Utility-first design consistency
* High development velocity
* Minimal CSS duplication
* Scalable design systems

---

## 2. Scope

Applies to:

* All modern front-end applications
* Component-based architectures
* Design system implementations

---

## 3. Framework Standard

The organization adopts **Tailwind CSS (latest stable version)**.

---

## 4. Core Principles

* Utility-first styling
* Composition over inheritance
* Minimal custom CSS
* Design tokens as single source of truth

---

## 5. Styling Guidelines

* Styling MUST be implemented using Tailwind utility classes
* Custom CSS SHOULD be avoided unless necessary
* Inline utility usage MUST remain readable

---

## 6. Configuration

* `tailwind.config.js` MUST define:

  * Color palette
  * Spacing scale
  * Typography
  * Breakpoints

* Design tokens MUST be centralized

---

## 7. Component Patterns

* Reusable UI components SHOULD be created using composition
* Repetition SHOULD be abstracted into components or templates

---

## 8. Responsiveness

* Responsive utilities (`sm`, `md`, `lg`, `xl`) MUST be used
* Mobile-first design MUST be followed

---

## 9. Performance

* Purge/Content scanning MUST remove unused styles
* Final CSS bundle MUST be optimized

---

## 10. Accessibility

* Semantic HTML MUST be used
* Accessibility MUST NOT be compromised by utility usage

---

## 11. Governance

* Tailwind configuration MUST be centrally managed
* Utility usage MUST follow internal style guidelines

---

## 12. Summary

Tailwind CSS enables highly flexible, maintainable, and scalable UI development through utility-first design.
