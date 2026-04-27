"""Helpers for enforcing English-only canonical downstream artifact content."""

from __future__ import annotations

from dataclasses import dataclass


_LOCALIZED_MARKERS = (
    " ausgangslage",
    " kernproblem",
    " heute passiert",
    " zu spaet",
    " zusammenhaengende",
    " akzeptanzkriterien",
    " rueckfragen",
    " entscheidungszustand",
    " belastbar",
    " begruendeter",
    " fachrollen",
    " expertenverfuegbarkeit",
)


@dataclass(frozen=True)
class LanguageGateResult:
    """Result of validating whether canonical text is English-only enough downstream."""

    status: str
    note: str


def contains_localized_content(content: str) -> bool:
    """Return True when content appears to contain localized source fragments."""
    lowered = f" {content.lower()} "
    if any(marker in lowered for marker in _LOCALIZED_MARKERS):
        return True
    return any(ch in content for ch in "äöüßÄÖÜ")


def evaluate_english_language_gate(content: str) -> LanguageGateResult:
    """Evaluate whether downstream canonical content satisfies the English-only gate."""
    if not content.strip():
        return LanguageGateResult(
            status="not-applicable",
            note="Language gate skipped because no canonical content was extracted.",
        )
    if contains_localized_content(content):
        return LanguageGateResult(
            status="failed",
            note=(
                "Canonical downstream content still contains localized fragments; "
                "translate or normalize before planning promotion."
            ),
        )
    return LanguageGateResult(
        status="passed",
        note="Canonical downstream content passed the English-only gate.",
    )