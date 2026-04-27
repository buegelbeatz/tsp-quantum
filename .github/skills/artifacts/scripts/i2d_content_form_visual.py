"""Visual form-signal detection helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def _update_bounds(
    y: int, x: int, min_y: int, max_y: int, min_x: int, max_x: int
) -> tuple[int, int, int, int]:
    """Update bounding box with new coordinate."""
    return min(min_y, y), max(max_y, y), min(min_x, x), max(max_x, x)


def _get_valid_neighbors(
    y: int, x: int, h: int, w: int, mask, visited
) -> list[tuple[int, int]]:
    """Get unvisited neighbors within bounds and mask."""
    neighbors = []
    for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
            neighbors.append((ny, nx))
    return neighbors


def _expand_component(y: int, x: int, mask, visited) -> tuple[int, int, int, int, int]:
    """Flood-fill one connected edge component; return (min_y, max_y, min_x, max_x, pixel_count)."""
    h, w = mask.shape
    stack = [(y, x)]
    visited[y, x] = True
    min_y = max_y = y
    min_x = max_x = x
    pixel_count = 0

    while stack:
        cy, cx = stack.pop()
        pixel_count += 1
        min_y, max_y, min_x, max_x = _update_bounds(cy, cx, min_y, max_y, min_x, max_x)

        for ny, nx in _get_valid_neighbors(cy, cx, h, w, mask, visited):
            visited[ny, nx] = True
            stack.append((ny, nx))

    return min_y, max_y, min_x, max_x, pixel_count


def _is_valid_component_candidate(bw: int, bh: int) -> bool:
    """Check if bounding box meets minimum dimensions."""
    return bw >= 30 and bh >= 8


def _is_input_box_candidate(aspect: float, bh: int, density: float) -> bool:
    """Check if component matches input-box heuristics."""
    return 2.4 <= aspect <= 14.0 and 10 <= bh <= 90 and density <= 0.33


def _is_button_candidate(aspect: float, bh: int, density: float) -> bool:
    """Check if component matches button heuristics."""
    return 1.1 <= aspect <= 4.5 and 18 <= bh <= 120 and density <= 0.48


def _classify_component(bw: int, bh: int, pixel_count: int) -> str:
    """Classify component as input-box, button, or neither.

    Returns one of: 'input_box', 'button', or 'neither'.
    """
    if not _is_valid_component_candidate(bw, bh):
        return "neither"

    aspect = bw / float(bh)
    density = pixel_count / float(max(1, bw * bh))

    if _is_input_box_candidate(aspect, bh, density):
        return "input_box"
    if _is_button_candidate(aspect, bh, density):
        return "button"
    return "neither"


def _scan_components(mask) -> tuple[int, int]:
    """Count input-box and button candidates from connected edge components."""
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    input_boxes = 0
    buttons = 0

    for y in range(h):
        for x in range(w):
            if not mask[y, x] or visited[y, x]:
                continue

            min_y, max_y, min_x, max_x, pixel_count = _expand_component(
                y, x, mask, visited
            )
            bw = max_x - min_x + 1
            bh = max_y - min_y + 1

            component_type = _classify_component(bw, bh, pixel_count)
            if component_type == "input_box":
                input_boxes += 1
            elif component_type == "button":
                buttons += 1

    return input_boxes, buttons


def local_visual_signals(path: Path) -> tuple[int, int]:
    """Detect likely input-box and button regions from image geometry."""
    try:
        from PIL import Image, ImageFilter  # type: ignore[import-untyped]
    except ImportError:
        return 0, 0

    try:
        try:
            from pillow_heif import register_heif_opener  # type: ignore[import-untyped]

            register_heif_opener()
        except ImportError:
            pass

        with Image.open(path) as img:
            gray = img.convert("L")
            max_dim = max(gray.width, gray.height)
            if max_dim > 1400:
                scale = 1400.0 / float(max_dim)
                gray = gray.resize(
                    (int(gray.width * scale), int(gray.height * scale)),
                    resample=Image.Resampling.BILINEAR,
                )
            edge = gray.filter(ImageFilter.FIND_EDGES)
    except (OSError, RuntimeError, ValueError):
        return 0, 0

    arr = np.asarray(edge, dtype=np.uint8)
    return _scan_components(arr > 70)
