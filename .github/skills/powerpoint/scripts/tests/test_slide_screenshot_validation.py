from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

from test_helpers import load_module

try:
    importlib.import_module("cairosvg")
except (ImportError, OSError) as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"Cairo runtime unavailable: {exc}", allow_module_level=True)

pptx_mod = pytest.importorskip("pptx")
Presentation = pptx_mod.Presentation
Image = pytest.importorskip("PIL.Image")
ImageStat = pytest.importorskip("PIL.ImageStat")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_powerpoint_visual_snapshots_are_deterministic(tmp_path, monkeypatch, capsys) -> None:
    """Generate a temporary deck twice and compare exported slide screenshots."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")
    screenshot_mod = load_module("render_slide_screenshots")

    office_bin = getattr(screenshot_mod, "_find_office_binary")()
    if not office_bin:
        pytest.skip("LibreOffice/soffice is required for slide screenshot tests")

    src = tmp_path / "PROJECT.md"
    src.write_text(
        "\n".join(
            [
                "# Project",
                "",
                "## Vision",
                "Reliable project delivery.",
                "",
                "## Goals",
                "- Keep handoffs deterministic",
                "- Keep reporting transparent",
                "",
                "## Constraints",
                "- Human approval before done",
            ]
        ),
        encoding="utf-8",
    )

    tpl = tmp_path / "tpl.pptx"
    prs = Presentation()
    blank = prs.slide_layouts[6]
    for _ in range(7):
        prs.slides.add_slide(blank)
    prs.save(str(tpl))
    monkeypatch.setattr(script, "ensure_template", lambda *_args: (tpl, False))

    deck_a = tmp_path / "generated-a.pptx"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--repo-root",
            str(tmp_path),
            "--layer",
            "layer-x",
            "--source",
            str(src),
            "--output",
            str(deck_a),
        ],
    )
    assert script.main() == 0
    payload_a = json.loads(capsys.readouterr().out)
    assert payload_a["status"] == "ok"

    deck_b = tmp_path / "generated-b.pptx"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--repo-root",
            str(tmp_path),
            "--layer",
            "layer-x",
            "--source",
            str(src),
            "--output",
            str(deck_b),
        ],
    )
    assert script.main() == 0
    payload_b = json.loads(capsys.readouterr().out)
    assert payload_b["status"] == "ok"

    render = getattr(screenshot_mod, "render_slide_screenshots")
    shots_a = render(deck_a, tmp_path / "shots-a")
    shots_b = render(deck_b, tmp_path / "shots-b")

    slide_count = len(Presentation(str(deck_a)).slides)
    assert len(shots_a) == slide_count
    assert len(shots_b) == slide_count

    for idx, (left, right) in enumerate(zip(shots_a, shots_b), start=1):
        assert _file_sha256(left) == _file_sha256(right), f"slide {idx} screenshot differs"
        with Image.open(left) as image:
            grayscale = image.convert("L")
            assert grayscale.getbbox() is not None
            assert ImageStat.Stat(grayscale).stddev[0] > 0.5
