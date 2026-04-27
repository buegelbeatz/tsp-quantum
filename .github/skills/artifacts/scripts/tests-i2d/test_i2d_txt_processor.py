"""Tests for text translation fallback behavior in i2d_txt_processor."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_txt_processor  # noqa: E402  # type: ignore[import-not-found]


def test_process_txt_file_returns_model_translation_when_available() -> None:
    """Model response should be used as-is when API call succeeds."""

    def _api_call(_prompt: str, _content: str) -> str:
        return (
            '{"translation":"English body","inferred_type":"project",'
            '"research_hints":["hint-a"],"review_note":"ok"}'
        )

    result = i2d_txt_processor.process_txt_file("Deutscher Inhalt", api_call_fn=_api_call)
    assert result["translation"] == "English body"
    assert result["inferred_type"] == "project"
    assert result["research_hints"] == ["hint-a"]
    assert result["review_note"] == "ok"


def test_process_txt_file_uses_fallback_for_localized_input() -> None:
    """Localized content should receive deterministic fallback translation on API failure."""

    def _api_call(_prompt: str, _content: str) -> str:
        raise RuntimeError("DIGITAL_TEAM_VISION_API_URL or DIGITAL_TEAM_VISION_API_KEY not set")

    source = """
Heute passiert die Bewertung oft:
- zu spaet (Wartezeit auf geeignete Experten)
- zu uneinheitlich (kein durchgaengiges Gate-Format)
""".strip()

    result = i2d_txt_processor.process_txt_file(source, api_call_fn=_api_call)
    translation = str(result["translation"])

    assert "error" not in result
    assert "Today, assessment often happens" in translation
    assert "too late" in translation
    assert "too inconsistent" in translation
    assert "heute passiert" not in translation.lower()
    assert "zu spaet" not in translation.lower()
    assert result["inferred_type"] == "project"


def test_process_txt_file_returns_error_for_non_localized_input() -> None:
    """Non-localized content should keep strict error behavior on API failure."""

    def _api_call(_prompt: str, _content: str) -> str:
        raise RuntimeError("network unavailable")

    result = i2d_txt_processor.process_txt_file("Pure English content", api_call_fn=_api_call)
    assert "error" in result


def test_process_txt_file_translates_problem_statement_markdown_structure() -> None:
    """Markdown problem statements should keep structure while translating common German sections."""

    def _api_call(_prompt: str, _content: str) -> str:
        raise RuntimeError("DIGITAL_TEAM_VISION_API_URL or DIGITAL_TEAM_VISION_API_KEY not set")

    source = """
title: "Problem Statement — digital-generic-team als selbstverwaltetes virtuelles Team"

## 1. Ausgangslage

Ein kleines Team kann nicht dauerhaft alle Fachrollen parallel besetzen (Architektur, Security, Data/ML, UX, Delivery). Gleichzeitig entstehen laufend neue Ideen, die schnell und belastbar bewertet werden muessen.

## 2. Kernproblem

> Wie ersetzt ein kleines Team fehlende Fachkompetenzen durch virtuelle MCP-Expertenrollen und trifft trotzdem schnelle, nachvollziehbare Stage-Entscheidungen mit klaren Exit-Gates?

## 5. Erfolgskennzahlen (erste Messung)

- **Nacharbeit:** < 20% Rueckfragen durch fehlende Kontextangaben im Intake.

## 7. Nutzenhypothese

- **Schneller:** Ideen werden nicht mehr durch Expertenverfuegbarkeit blockiert.
""".strip()

    result = i2d_txt_processor.process_txt_file(source, api_call_fn=_api_call)
    translation = str(result["translation"])

    assert 'title: "Problem Statement — digital-generic-team as a self-managed virtual team"' in translation
    assert "## 1. Initial Situation" in translation
    assert "A small team cannot permanently staff all specialist roles in parallel" in translation
    assert "## 2. Core Problem" in translation
    assert "How does a small team replace missing specialist expertise with virtual MCP expert roles" in translation
    assert "## 5. Success Metrics (Initial Measurement)" in translation
    assert "follow-up questions caused by missing context in the intake" in translation
    assert "## 7. Value Hypothesis" in translation
    assert "Ideas are no longer blocked by expert availability" in translation
    assert "Ausgangslage" not in translation
    assert "Kernproblem" not in translation
    assert "Rueckfragen" not in translation
