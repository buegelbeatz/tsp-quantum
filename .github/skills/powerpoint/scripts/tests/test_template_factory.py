from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest

from test_helpers import load_module

pytest.importorskip("pptx")

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WfM9eQAAAAASUVORK5CYII="
)


def test_ensure_template_creates_once(tmp_path, monkeypatch) -> None:
    """Verify that ensure_template creates a PPTX on first call and skips on second."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    portraits = load_module("powerpoint_portraits")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    sys.modules["powerpoint_portraits"] = portraits
    factory = load_module("template_factory")

    # Each call to _svg_to_png_file must return a fresh, non-deleted file because
    # create_template unlinks each PNG in its own try/finally block.
    call_count = 0

    def make_fresh_png(_svg: str) -> Path:
        """TODO: add docstring for make_fresh_png."""
        nonlocal call_count
        call_count += 1
        p = tmp_path / f"bg_{call_count}.png"
        p.write_bytes(PNG_1X1)
        return p

    monkeypatch.setattr(factory, "_svg_to_png_file", make_fresh_png)
    # Stub team slide so the test has no dependency on portraits.png
    monkeypatch.setattr(factory, "_add_team_slide", lambda *_a, **_kw: None)

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    template = tmp_path / "layer_template.pptx"
    first, created_first = factory.ensure_template(repo_root, "layer", template)
    second, created_second = factory.ensure_template(repo_root, "layer", template)

    assert first.exists()
    assert second == first
    assert created_first is True
    assert created_second is False
