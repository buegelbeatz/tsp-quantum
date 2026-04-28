from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from test_helpers import load_module

pptx_mod = pytest.importorskip("pptx")
Presentation = pptx_mod.Presentation
Inches = pytest.importorskip("pptx.util").Inches


def _add_text_slide(prs: Presentation, title: str, body: str) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.0), Inches(0.8))
    title_box.text_frame.text = title
    body_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.0), Inches(4.5))
    body_box.text_frame.text = body


def _build_template(path: Path) -> None:
    prs = Presentation()
    while len(prs.slides) < 7:
        prs.slides.add_slide(prs.slide_layouts[6])
    prs.save(str(path))


def _build_good_deck(path: Path) -> None:
    prs = Presentation()
    _add_text_slide(prs, "Project Briefing", "- Executive summary\n- Stage status")
    _add_text_slide(prs, "Agenda", "- Context\n- Delivery\n- Next steps")
    _add_text_slide(prs, "Context and Objectives", "- Scope is validated\n- Risks are documented")
    _add_text_slide(prs, "Delivery Focus", "- Owner aligned\n- Review prepared")
    _add_text_slide(prs, "Thank You", "- Next decision checkpoint")
    _add_text_slide(prs, "BACKUP", "Template source slides below")
    _add_text_slide(prs, "Reference", "- Supporting material")
    prs.save(str(path))


def _build_bad_deck(path: Path) -> None:
    prs = Presentation()
    _add_text_slide(prs, "x", "todo\ncriterion 1\ncriterion 2\ncriterion 3")
    prs.save(str(path))


def test_review_deck_recommends_proceed_for_structured_deck(tmp_path: Path) -> None:
    reviewer = load_module("review_generated_deck")
    template_path = tmp_path / "template.pptx"
    deck_path = tmp_path / "deck.pptx"
    _build_template(template_path)
    _build_good_deck(deck_path)

    payload = reviewer.review_deck(deck_path, template_path)

    assert payload["recommendation"] == "proceed"
    assert payload["composite_score"] >= 4.0
    assert payload["backup_present"] is True


def test_main_strict_returns_non_zero_when_quality_is_low(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reviewer = load_module("review_generated_deck")
    template_path = tmp_path / "template.pptx"
    deck_path = tmp_path / "deck.pptx"
    report_json = tmp_path / "quality.json"
    report_md = tmp_path / "quality.md"

    _build_template(template_path)
    _build_bad_deck(deck_path)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--deck",
            str(deck_path),
            "--template",
            str(template_path),
            "--min-score",
            "4.0",
            "--report-json",
            str(report_json),
            "--report-md",
            str(report_md),
            "--strict",
        ],
    )

    exit_code = reviewer.main()
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert output["quality_review"]["recommendation"] in {"revise", "redesign"}
    assert report_json.exists()
    assert report_md.exists()


def test_review_deck_adds_source_relevance_and_screenshot_criteria(tmp_path: Path) -> None:
    reviewer = load_module("review_generated_deck")
    template_path = tmp_path / "template.pptx"
    deck_path = tmp_path / "deck.pptx"
    source_path = tmp_path / "source.md"
    screenshots_dir = tmp_path / "shots"

    _build_template(template_path)
    _build_good_deck(deck_path)
    source_path.write_text(
        "Traveling Salesman Problem (TSP) comparison between classical and quantum approaches.",
        encoding="utf-8",
    )
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    (screenshots_dir / "slide-001.png").write_bytes(b"png")

    payload = reviewer.review_deck(
        deck_path,
        template_path,
        source_path=source_path,
        screenshots_dir=screenshots_dir,
    )

    criteria_names = [item["name"] for item in payload["criteria"]]
    assert "Source Relevance" in criteria_names
    assert "Screenshot Coverage" in criteria_names
