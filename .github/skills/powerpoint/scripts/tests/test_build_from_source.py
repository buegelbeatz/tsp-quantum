from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from test_helpers import load_module

pptx_mod = pytest.importorskip("pptx")
Presentation = pptx_mod.Presentation


def test_main_builds_deck_from_file(tmp_path, monkeypatch, capsys) -> None:
    """TODO: add docstring for test_main_builds_deck_from_file."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")

    src = tmp_path / "spec.md"
    src.write_text("# Title\nBody", encoding="utf-8")
    tpl = tmp_path / "tpl.pptx"
    Presentation().save(str(tpl))
    monkeypatch.setattr(script, "ensure_template", lambda *_args: (tpl, False))

    out = tmp_path / "out.pptx"
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
            str(out),
        ],
    )

    assert script.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert out.exists()


def test_main_uses_docs_powerpoints_as_default_output(
    tmp_path, monkeypatch, capsys
) -> None:
    """TODO: add docstring for test_main_uses_docs_powerpoints_as_default_output."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")

    src = tmp_path / "spec.md"
    src.write_text("# Title\nBody", encoding="utf-8")
    tpl = tmp_path / "tpl.pptx"
    Presentation().save(str(tpl))
    monkeypatch.setattr(script, "ensure_template", lambda *_args: (tpl, False))

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
        ],
    )

    assert script.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert "/docs/powerpoints/" in payload["output"].replace("\\", "/")


def test_main_builds_stage_stakeholder_briefing_with_structured_content(
    tmp_path, monkeypatch, capsys
) -> None:
    """Canonical stage markdown should generate structured stakeholder slides."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")

    src = tmp_path / "PROJECT.md"
    src.write_text(
        "\n".join(
            [
                "# Project",
                "",
                "## Vision",
                "Build a reliable delivery workflow.",
                "",
                "## Goals",
                "- Goal A",
                "- Goal B",
                "",
                "## Constraints",
                "- Constraint A",
                "",
                "## Open Questions",
                "- none",
            ]
        ),
        encoding="utf-8",
    )
    tpl = tmp_path / "tpl.pptx"
    Presentation().save(str(tpl))
    monkeypatch.setattr(script, "ensure_template", lambda *_args: (tpl, False))

    out = tmp_path / "stakeholder.pptx"
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
            str(out),
        ],
    )

    assert script.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert out.exists()
    generated = Presentation(str(out))
    assert len(generated.slides) >= 4
    all_text = []
    for slide in generated.slides:
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                all_text.append(shape.text_frame.text)
    rendered = "\n".join(all_text)
    assert "Current Context" in rendered
    assert "Constraints, Risks, and Next Step" in rendered
    assert "BACKUP" in rendered


def test_fit_body_lines_clips_to_safe_slide_budget() -> None:
    """Body fitting should cap the line count and append a continuation marker."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")

    long_lines = [f"line {idx}" for idx in range(20)]
    fit_body = getattr(script, "_fit_body_lines")
    fitted = fit_body(long_lines, max_lines=6, max_chars=20)
    assert len(fitted) == 6
    assert fitted[-1].startswith("... see source")


def test_discover_visual_assets_prefers_known_workspace_locations(tmp_path) -> None:
    """Visual asset discovery should include candidate images from stage-adjacent and docs folders."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")

    source = tmp_path / "PROJECT.md"
    source.write_text("# Stage\n", encoding="utf-8")
    (tmp_path / "assets").mkdir(parents=True, exist_ok=True)
    (tmp_path / "assets" / "overview.png").write_bytes(b"png")
    (tmp_path / "docs" / "images" / "mermaid").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "images" / "mermaid" / "map.jpg").write_bytes(b"jpg")

    discover_assets = getattr(script, "_discover_visual_assets")
    assets = discover_assets(tmp_path, source)
    normalized = [str(path).replace("\\", "/") for path in assets]
    assert any(path.endswith("/assets/overview.png") for path in normalized)
    assert any(path.endswith("/docs/images/mermaid/map.jpg") for path in normalized)


def test_discover_visual_assets_includes_svg_candidates(tmp_path) -> None:
    """Asset discovery should also include SVG visuals for later conversion."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")

    source = tmp_path / "PROJECT.md"
    source.write_text("# Stage\n", encoding="utf-8")
    (tmp_path / "assets").mkdir(parents=True, exist_ok=True)
    (tmp_path / "assets" / "diagram.svg").write_text("<svg />", encoding="utf-8")

    discover_assets = getattr(script, "_discover_visual_assets")
    assets = discover_assets(tmp_path, source)
    assert any(path.suffix.lower() == ".svg" for path in assets)


def test_discover_visual_assets_excludes_generic_scribble_for_tsp_topic(tmp_path) -> None:
    """Generic UX scribbles must be ignored when source topic is TSP/quantum."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")

    source = tmp_path / "PROJECT.md"
    source.write_text("# Project\nTraveling Salesman Problem (TSP) and quantum comparison", encoding="utf-8")

    (tmp_path / "docs" / "ux" / "scribbles").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "ux" / "scribbles" / "generic-home-flow.svg").write_text("<svg />", encoding="utf-8")

    (tmp_path / "docs" / "wiki" / "assets" / "visualizations").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "wiki" / "assets" / "visualizations" / "tsp-route-map.png").write_bytes(b"png")

    discover_assets = getattr(script, "_discover_visual_assets")
    assets = discover_assets(tmp_path, source)
    names = [path.name for path in assets]
    assert "tsp-route-map.png" in names
    assert "generic-home-flow.svg" not in names


def test_prepare_visual_asset_for_ppt_converts_svg_when_cairosvg_available(
    tmp_path, monkeypatch
) -> None:
    """SVG assets should be converted to PNG before embedding into PPT slides."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")

    asset = tmp_path / "diagram.svg"
    asset.write_text("<svg></svg>", encoding="utf-8")
    temp_dir = tmp_path / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    class _FakeCairoSvg:
        @staticmethod
        def svg2png(url: str, write_to: str) -> None:
            del url
            Path(write_to).write_bytes(b"png")

    monkeypatch.setattr(script, "CAIROSVG", _FakeCairoSvg)
    prepare_asset = getattr(script, "_prepare_visual_asset_for_ppt")
    converted = prepare_asset(asset, temp_dir)
    assert converted is not None
    assert converted.suffix.lower() == ".png"
    assert converted.exists()


def test_prepare_visual_asset_for_ppt_skips_svg_without_cairosvg(
    tmp_path, monkeypatch
) -> None:
    """SVG assets should be skipped when conversion dependency is unavailable."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")

    asset = tmp_path / "diagram.svg"
    asset.write_text("<svg></svg>", encoding="utf-8")
    temp_dir = tmp_path / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(script, "CAIROSVG", None)
    prepare_asset = getattr(script, "_prepare_visual_asset_for_ppt")
    assert prepare_asset(asset, temp_dir) is None


def test_apply_sections_keeps_unused_slides_behind_backup_divider(
    tmp_path,
) -> None:
    """Template slides stay unchanged behind BACKUP while front slides are copied."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("build_from_source")

    # Build a 7-slide template. Front content must be built as copies and the
    # full original template must remain behind BACKUP unchanged.
    tpl_path = tmp_path / "tpl.pptx"
    prs_tpl = Presentation()
    blank_layout = prs_tpl.slide_layouts[6]
    for _ in range(7):
        prs_tpl.slides.add_slide(blank_layout)
    prs_tpl.save(str(tpl_path))

    prs = Presentation(str(tpl_path))
    sections = [("S1", "b1"), ("S2", "b2"), ("S3", "b3"), ("S4", "b4"), ("S5", "b5")]
    apply_fn = getattr(script, "_apply_sections_to_template")
    apply_fn(prs, sections)

    # For 5 sections -> 8 front copies (title+agenda+chapter+3 content+team+closing)
    # + 1 BACKUP divider + 7 original template slides.
    assert len(prs.slides) == 16

    backup_slide = prs.slides[8]
    texts = [
        shape.text_frame.text
        for shape in backup_slide.shapes
        if getattr(shape, "has_text_frame", False)
    ]
    assert any("BACKUP" in t for t in texts)

    # All template slides are preserved behind BACKUP (7 slides total).
    post_backup_indices = list(range(9, len(prs.slides)))
    assert len(post_backup_indices) == 7
