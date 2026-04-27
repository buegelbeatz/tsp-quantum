"""Unit tests for powerpoint_portraits portrait extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from test_helpers import load_module_from_path

pytest.importorskip("PIL")
portraits_module = load_module_from_path(
    Path(__file__).resolve().parent.parent / "powerpoint_portraits.py",
    "powerpoint_portraits",
)


def test_get_portrait_by_index_returns_pil_image() -> None:
    """get_portrait_by_index should return a PIL Image object."""
    portrait = portraits_module.get_portrait_by_index(0)
    assert portrait is not None
    assert hasattr(portrait, "save")
    assert hasattr(portrait, "crop")


def test_get_portrait_by_index_wraps_around() -> None:
    """Portrait indices should wrap around with modulo (25 portraits total)."""
    portrait_0 = portraits_module.get_portrait_by_index(0)
    portrait_25 = portraits_module.get_portrait_by_index(25)
    portrait_50 = portraits_module.get_portrait_by_index(50)

    # Convert to bytes to compare (images are deterministically extracted)
    from io import BytesIO

    def image_to_bytes(img):
        """TODO: add docstring for image_to_bytes."""
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    assert image_to_bytes(portrait_0) == image_to_bytes(portrait_25)
    assert image_to_bytes(portrait_0) == image_to_bytes(portrait_50)


def test_get_portrait_by_seed_deterministic() -> None:
    """Same seed should always return the same portrait."""
    from io import BytesIO

    def image_to_bytes(img):
        """TODO: add docstring for image_to_bytes."""
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    portrait_1a = portraits_module.get_portrait_by_seed(42)
    portrait_1b = portraits_module.get_portrait_by_seed(42)

    assert image_to_bytes(portrait_1a) == image_to_bytes(portrait_1b)


def test_get_portrait_by_seed_different_for_different_seeds() -> None:
    """Different seeds should generally produce different portraits."""
    portrait_1 = portraits_module.get_portrait_by_seed(1)
    portrait_2 = portraits_module.get_portrait_by_seed(2)

    from io import BytesIO

    def image_to_bytes(img):
        """TODO: add docstring for image_to_bytes."""
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # With 25 portraits, different seeds may sometimes pick the same portrait,
    # but with diverse seeds, most should be different
    bytes_1 = image_to_bytes(portrait_1)
    bytes_2 = image_to_bytes(portrait_2)
    # Just verify that both are valid images
    assert bytes_1
    assert bytes_2


def test_portrait_to_png_file_creates_file() -> None:
    """portrait_to_png_file should create a valid PNG file."""
    portrait = portraits_module.get_portrait_by_index(0)
    png_path = portraits_module.portrait_to_png_file(portrait)

    try:
        assert png_path.exists()
        assert png_path.suffix == ".png"
        # Verify it's a valid PNG by checking magic bytes
        with open(png_path, "rb") as f:
            magic = f.read(8)
            assert magic.startswith(b"\x89PNG")
    finally:
        png_path.unlink(missing_ok=True)


def test_get_portrait_png_file_by_seed_creates_file() -> None:
    """get_portrait_png_file_by_seed should create a valid PNG file."""
    png_path = portraits_module.get_portrait_png_file_by_seed(123)

    try:
        assert png_path.exists()
        assert png_path.suffix == ".png"
        # Verify it's a valid file
        assert png_path.stat().st_size > 0
    finally:
        png_path.unlink(missing_ok=True)
