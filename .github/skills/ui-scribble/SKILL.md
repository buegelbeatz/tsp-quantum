---
name: "ui-scribble"
description: Generate pencil-style SVG UI sketches from Markdown descriptions
layer: digital-generic-team
---

# UI Scribble Generator

## Purpose

Transform Markdown-based UI descriptions into low-fidelity sketch-style SVG artifacts for UX exploration and review.

---

## Input

- Markdown files in:
  .digital-artifacts/10-data/**
  .digital-artifacts/30-specification/**

---

## Output

- SVG:
  docs/ux/scribbles/<name>-scribble.svg

- Optional PNG:
  docs/ux/scribbles/<name>-scribble.png

---

## Instructions

1. Read the Markdown description
2. Extract:
   - layout regions
   - UI elements
   - hierarchy
   - interaction hints

3. Generate SVG with:
   - rough layout blocks
   - annotations
   - arrows
   - placeholder text

---

## Style Guide

- Hand-drawn pencil style is mandatory (must look like a human UX sketch)
- Optional colored-pencil accents are allowed for emphasis (for example CTA, warnings, navigation)
- Avoid polished/vector-perfect visual language; keep intentional wobble and pressure variation
- Imperfect lines and annotations are required (simulate hand drawing)
- No pixel-perfect UI components
- Focus on structure, flow, and intent over visual polish

### Visual Acceptance Heuristics

- Stroke roughness must be visible (no uniform CAD-like strokes)
- Include at least one handwritten-style annotation area
- Include at least one flow arrow with non-linear path shape
- If color is used, prefer muted pencil-like tones (not saturated UI colors)

---

## SVG Rules

- Use <g> groups with semantic IDs
- Keep text editable (<text>)
- Avoid path-heavy rendering for text
- Keep file deterministic (diff-friendly)

---

## PNG Handling

If PNG is required:

- Use script:
  scripts/render_svg_to_png.py

- Input:
  SVG file

- Output:
  PNG file in same directory