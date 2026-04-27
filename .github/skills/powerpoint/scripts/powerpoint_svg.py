"""SVG background generators for deterministic futuristic templates."""

from __future__ import annotations

import random

PALETTES = {
    "title": ("#071426", "#0b2a4a", "#16e0bd", "#59b3ff"),
    "content": ("#f7fbff", "#deebff", "#1f4e79", "#2a9d8f"),
}


def make_background_svg(width: int, height: int, seed: int, variant: str) -> str:
    """Return deterministic abstract SVG for a slide background."""
    rng = random.Random(seed)
    bg, tone, accent, line = PALETTES[variant]
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        f"<rect width='100%' height='100%' fill='{bg}'/>",
    ]
    for _ in range(18):
        x = rng.randint(0, width)
        y = rng.randint(0, height)
        r = rng.randint(40, 220)
        alpha = rng.uniform(0.06, 0.22)
        parts.append(
            f"<circle cx='{x}' cy='{y}' r='{r}' fill='{tone}' fill-opacity='{alpha:.3f}'/>"
        )
    for _ in range(22):
        x1 = rng.randint(0, width)
        y1 = rng.randint(0, height)
        x2 = min(width, x1 + rng.randint(80, 420))
        y2 = min(height, y1 + rng.randint(-240, 240))
        alpha = rng.uniform(0.12, 0.38)
        w = rng.uniform(0.8, 2.2)
        parts.append(
            f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{line}' "
            f"stroke-width='{w:.2f}' stroke-opacity='{alpha:.3f}'/>"
        )
    for _ in range(8):
        x = rng.randint(0, width - 300)
        y = rng.randint(0, height - 200)
        w = rng.randint(120, 360)
        h = rng.randint(40, 160)
        alpha = rng.uniform(0.08, 0.2)
        parts.append(
            f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='14' fill='{accent}' "
            f"fill-opacity='{alpha:.3f}'/>"
        )
    parts.append("</svg>")
    return "".join(parts)
