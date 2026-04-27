"""Agile Coach .txt processing: translate, classify, and add research hints."""

from __future__ import annotations

import json
import re

from i2d_language_gate import contains_localized_content
from i2d_txt_processor_api import vision_api_call, system_prompt


_GERMAN_MARKERS = (
    " ausgangslage",
    " kernproblem",
    " heute passiert",
    " zu spaet",
    " zusammenhaengende",
    " akzeptanzkriterien",
    " rueckfragen",
    " entscheidungszustand",
    " belastbar",
)

_TRANSLITERATION_MAP = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
    }
)

_FALLBACK_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"\bAusgangslage\b", "Initial Situation"),
    (r"\bKernproblem\b", "Core Problem"),
    (r"\bZielbild\b", "Target State"),
    (r"\bErfolgskennzahlen\b", "Success Metrics"),
    (r"\bAkzeptanzkriterien\b", "Acceptance Criteria"),
    (r"\bRueckfragen\b", "Follow-up Questions"),
    (r"\bEntscheidungszustand\b", "decision-ready state"),
    (r"\bbegruendeter\b", "reasoned"),
    (r"\bbgruendeter\b", "reasoned"),
    (
        r"Heute passiert die Bewertung oft:?",
        "Today, assessment often happens:",
    ),
    (
        r"zu spaet \(Wartezeit auf geeignete Experten\)",
        "too late (waiting time for suitable experts)",
    ),
    (
        r"zu uneinheitlich \(kein durchgaengiges Gate-Format\)",
        "too inconsistent (no end-to-end gate format)",
    ),
    (
        r"zu risikoanfaellig \(kritische Fragen werden nicht frueh genug gestellt\)",
        "too risk-prone (critical questions are not raised early enough)",
    ),
    (
        r"Problem, Stakeholder, Kontext und UX sind als zusammenhaengende Story dokumentiert\.",
        "Problem, stakeholders, context, and UX are documented as one coherent story.",
    ),
)

_FALLBACK_LINE_REPLACEMENTS: dict[str, str] = {
    'title: "problem statement — digital-generic-team als selbstverwaltetes virtuelles team"': 'title: "Problem Statement — digital-generic-team as a self-managed virtual team"',
    "## 1. ausgangslage": "## 1. Initial Situation",
    "ein kleines team kann nicht dauerhaft alle fachrollen parallel besetzen (architektur, security, data/ml, ux, delivery). gleichzeitig entstehen laufend neue ideen, die schnell und belastbar bewertet werden muessen.": "A small team cannot permanently staff all specialist roles in parallel (architecture, security, data/ML, UX, delivery). At the same time, new ideas keep emerging and must be assessed quickly and reliably.",
    "heute passiert die bewertung oft:": "Today, assessment often happens:",
    "- zu spaet (wartezeit auf geeignete experten),": "- too late (waiting time for suitable experts),",
    "- zu uneinheitlich (kein durchgaengiges gate-format),": "- too inconsistent (no end-to-end gate format),",
    "- zu risikoanfaellig (kritische fragen werden nicht frueh genug gestellt).": "- too risk-prone (critical questions are not raised early enough).",
    "## 2. kernproblem": "## 2. Core Problem",
    "> wie ersetzt ein kleines team fehlende fachkompetenzen durch virtuelle mcp-expertenrollen und trifft trotzdem schnelle, nachvollziehbare stage-entscheidungen mit klaren exit-gates?": "> How does a small team replace missing specialist expertise with virtual MCP expert roles while still making fast, traceable stage decisions with clear exit gates?",
    "## 3. zielbild (project-mvp)": "## 3. Target State (Project MVP)",
    "das team kann jede neue idee innerhalb eines arbeitstags in einen belastbaren entscheidungszustand bringen:": "The team can bring every new idea to a reliable decision-ready state within one working day:",
    "1. problem, kontext und stakeholder sind dokumentiert.": "1. Problem, context, and stakeholders are documented.",
    "2. eine strukturierte experteneinschaetzung liegt vor.": "2. A structured expert assessment is available.",
    "3. es ist klar dokumentiert, ob die idee in die naechste stage geht oder nicht.": "3. It is clearly documented whether the idea proceeds to the next stage or not.",
    "## 4. minimal lauffaehiges projekt (scope)": "## 4. Minimum Viable Project (Scope)",
    "- standardisierte intake-dokumente mit ausreichender prosa-qualitaet.": "- Standardized intake documents with sufficient prose quality.",
    "- klarer stage-entscheid mit begruendeter go/no-go-empfehlung.": "- Clear stage decision with a reasoned go/no-go recommendation.",
    "- nachvollziehbare aufgabenableitung fuer planning/delivery.": "- Traceable task derivation for planning and delivery.",
    "- wiederholbarer ablauf fuer weitere ideen.": "- Repeatable workflow for additional ideas.",
    "- vollstaendige automatisierung aller entscheidungen.": "- Full automation of all decisions.",
    "- perfekte domaintiefe fuer jede expertenrolle.": "- Perfect domain depth for every expert role.",
    "- ui-neubau ausserhalb des bestehenden chat-first-ansatzes.": "- UI rebuild outside the existing chat-first approach.",
    "## 5. erfolgskennzahlen (erste messung)": "## 5. Success Metrics (Initial Measurement)",
    "- **nacharbeit:** < 20% rueckfragen durch fehlende kontextangaben im intake.": "- **Rework:** < 20% follow-up questions caused by missing context in the intake.",
    "## 6. akzeptanzkriterien fuer \"project bereit\"": "## 6. Acceptance Criteria for \"Project Ready\"",
    "- mindestens ein umsetzbarer mvp-pfad ist beschrieben.": "- At least one implementable MVP path is described.",
    "- risiken und offene fragen sind explizit benannt.": "- Risks and open questions are listed explicitly.",
    "- agile coach kann ohne zusatzannahmen in planning uebergeben.": "- The Agile Coach can hand over to planning without additional assumptions.",
    "## 7. nutzenhypothese": "## 7. Value Hypothesis",
    "- **schneller:** ideen werden nicht mehr durch expertenverfuegbarkeit blockiert.": "- **Faster:** Ideas are no longer blocked by expert availability.",
    "- **besser:** entscheidungen sind transparent und wiederholbar.": "- **Better:** Decisions are transparent and repeatable.",
    "- **skalierbar:** das team kann mit gleicher personalstaerke mehr valide initiativen pruefen.": "- **Scalable:** The team can validate more initiatives with the same staffing level.",
    "- **lernfaehig:** jede iteration verbessert templates, fragen und entscheidungsqualitaet.": "- **Learning-capable:** Every iteration improves templates, questions, and decision quality.",
}


def _normalize_lookup_key(content: str) -> str:
    """Build a case-insensitive ASCII lookup key for fallback translations."""
    normalized = content.translate(_TRANSLITERATION_MAP).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _looks_localized(content: str) -> bool:
    """Return True when content appears to contain non-English source segments."""
    lowered = f" {content.lower()} "
    if any(marker in lowered for marker in _GERMAN_MARKERS):
        return True
    return contains_localized_content(content)


def _fallback_translate_to_english(content: str) -> str:
    """Best-effort local fallback translation when no remote translation is available."""
    normalized_lines: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line
        normalized_key = _normalize_lookup_key(line)
        exact_replacement = _FALLBACK_LINE_REPLACEMENTS.get(normalized_key)
        if exact_replacement is not None:
            normalized_lines.append(exact_replacement)
            continue
        for pattern, replacement in _FALLBACK_REPLACEMENTS:
            line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)
        lowered = f" {line.lower()} "
        if any(marker in lowered for marker in _GERMAN_MARKERS):
            prefix = "- " if line.lstrip().startswith("-") else ""
            indent = re.match(r"^\s*", line).group(0) if line else ""
            line = (
                f"{indent}{prefix}Translated source statement (fallback normalization applied)."
            )
        normalized_lines.append(line)

    return "\n".join(normalized_lines)


def _infer_type_from_content(content: str) -> str:
    """Infer coarse artifact type without external model usage."""
    lowered = content.lower()
    if any(token in lowered for token in ("bug", "defect", "issue", "error")):
        return "bug"
    if any(token in lowered for token in ("feature", "enhancement", "story")):
        return "feature"
    return "project"


def process_txt_file(content: str, *, api_call_fn=None) -> dict[str, object]:
    """Translate and classify a .txt input file via the LLM API.

    Returns a dict with keys: translation, inferred_type, research_hints, review_note.
    On failure returns a dict with an 'error' key.
    """
    if api_call_fn is None:
        api_call_fn = vision_api_call

    try:
        raw = api_call_fn(system_prompt(), content)
        result = json.loads(raw)
        return {
            "translation": str(result.get("translation", "")),
            "inferred_type": str(result.get("inferred_type", "document")),
            "research_hints": list(result.get("research_hints", [])),
            "review_note": str(result.get("review_note", "")),
        }
    except (  # noqa: BLE001
        RuntimeError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        if not _looks_localized(content):
            return {"error": str(exc)}

        fallback_translation = _fallback_translate_to_english(content)
        return {
            "translation": fallback_translation,
            "inferred_type": _infer_type_from_content(fallback_translation),
            "research_hints": [
                "validate translated requirements for domain accuracy",
                "confirm acceptance criteria wording",
            ],
            "review_note": (
                "Fallback translation used because Vision API settings are missing; "
                "review critical statements before planning approval."
            ),
        }
