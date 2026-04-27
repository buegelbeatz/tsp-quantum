"""Portrait extraction and selection from team sprite sheet.

This module provides functionality to:
- Load the deterministic portrait sprite sheet (portraits.png)
- Extract individual portraits based on index or seed
- Return portrait images for team member slides
"""

from __future__ import annotations

import random
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image  # type: ignore[import-not-found]


PORTRAITS_FILE = Path(__file__).resolve().parent.parent / "templates" / "portraits.png"

# Grid dimensions of the sprite sheet
PORTRAIT_GRID_COLS = 5
PORTRAIT_GRID_ROWS = 5
PORTRAIT_COUNT = PORTRAIT_GRID_COLS * PORTRAIT_GRID_ROWS


def _load_sprite_sheet() -> Image.Image:
    """Load the portrait sprite sheet from disk.

    Returns:
        PIL.Image: The full sprite sheet image (1254x1254).

    Raises:
        FileNotFoundError: If portraits.png is not found.
        IOError: If the image cannot be loaded.
    """
    if not PORTRAITS_FILE.exists():
        raise FileNotFoundError(f"Portrait sprite sheet not found: {PORTRAITS_FILE}")
    return Image.open(str(PORTRAITS_FILE))


def get_portrait_by_index(index: int) -> Image.Image:
    """Extract a single portrait from the sprite sheet by index.

    The sprite sheet contains 25 portraits arranged in a 5x5 grid.
    Indices wrap around using modulo arithmetic.

    Args:
        index: Portrait index (0-24). Indices >= 25 wrap using modulo.

    Returns:
        PIL.Image: Cropped portrait image (250x250 pixels).

    Raises:
        FileNotFoundError: If portrait sprite sheet is missing.
        IOError: If image loading fails.
    """
    sprite = _load_sprite_sheet()

    # Normalize index to 0-24 range
    index = index % PORTRAIT_COUNT

    # Calculate grid position
    row = index // PORTRAIT_GRID_COLS
    col = index % PORTRAIT_GRID_COLS

    # Calculate pixel coordinates (each portrait is 250x250 in a 1254x1254 sheet)
    portrait_size = sprite.width // PORTRAIT_GRID_COLS
    left = col * portrait_size
    top = row * portrait_size
    right = left + portrait_size
    bottom = top + portrait_size

    # Extract and return the portrait
    return sprite.crop((left, top, right, bottom))


def get_portrait_by_seed(seed: int) -> Image.Image:
    """Extract a portrait from the sprite sheet using a deterministic seed.

    This function provides deterministic portrait selection based on a seed value,
    ensuring that the same seed always produces the same portrait.

    Args:
        seed: Random seed for deterministic portrait selection.

    Returns:
        PIL.Image: Cropped portrait image (250x250 pixels).

    Raises:
        FileNotFoundError: If portrait sprite sheet is missing.
        IOError: If image loading fails.
    """
    rng = random.Random(seed)
    index = rng.randint(0, PORTRAIT_COUNT - 1)
    return get_portrait_by_index(index)


def portrait_to_png_file(portrait: Image.Image) -> Path:
    """Convert a portrait image to a temporary PNG file.

    This helper creates a temporary PNG file suitable for embedding
    in PowerPoint presentations.

    Args:
        portrait: PIL Image object containing the portrait.

    Returns:
        Path: Path to the temporary PNG file.

    Note:
        The caller is responsible for deleting the temporary file
        after use via Path.unlink(missing_ok=True).
    """
    with NamedTemporaryFile(prefix="ppt-portrait-", suffix=".png", delete=False) as tmp:
        portrait.save(tmp.name, format="PNG")
        return Path(tmp.name)


def get_portrait_png_file_by_seed(seed: int) -> Path:
    """Extract a portrait and save it to a temporary PNG file (convenience wrapper).

    Combines portrait extraction and PNG transformation in a single call.

    Args:
        seed: Random seed for deterministic portrait selection.

    Returns:
        Path: Path to the temporary PNG file containing the portrait.

    Note:
        The caller is responsible for deleting the temporary file
        after use via Path.unlink(missing_ok=True).
    """
    portrait = get_portrait_by_seed(seed)
    return portrait_to_png_file(portrait)
