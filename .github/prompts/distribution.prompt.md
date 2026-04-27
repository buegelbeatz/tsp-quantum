<!-- layer: digital-generic-team -->
---
mode: agent
description: Zeigt eine Zeilen-Verteilungstabelle (Scripts, Tests, Docs, Config) für das aktuelle Repository an.
---

# Prompt: /distribution

Analysiere die Codeverteilung im aktuellen Repository und rendere eine Markdown-Tabelle mit Kategorien, Zeilenzahlen und prozentualen Anteilen.

## Information flow

| Field    | Value |
|----------|-------|
| Producer | `distribution.py` (scannt repo-Verzeichnis) |
| Consumer | User (Markdown-Tabelle in der Chat-Antwort) |
| Trigger  | User ruft `/distribution` auf |
| Payload  | Zeilenanzahl pro Kategorie, Gesamtzahl, Prozentanteile |

## Steps

`[progress][/distribution] step=1/2 action=collect-line-counts`

Bestimme das Repo-Root und führe `distribution.py` aus:

```bash
make distribution
```

`[progress][/distribution] step=2/2 action=render-table`

Bette die Ausgabe in die Antwort ein. Antworte mit:
- Der vollständigen Markdown-Tabelle aus der Skriptausgabe
- Einem einzeiligen Kommentar, welche Verzeichnisse geskippt wurden (`Skip-Pattern` laut Skript: `.git`, `.digital-runtime`, `__pycache__`, `.venv`, `venv`, `node_modules`, `.tests`, `.mypy_cache`, `.ruff_cache`)

## Output Format

```
| Category      | Files | Lines  | % Total |
|---------------|-------|--------|---------|
| Scripts       |    42 |  3 210 |   38.2% |
| Tests         |    18 |  1 540 |   18.3% |
| Documentation |    11 |  2 100 |   25.0% |
| Configuration |    27 |  1 560 |   18.5% |
| **Total**     |    98 |  8 410 | 100.0%  |
```

## Error Handling

- Falls `distribution.py` nicht ausführbar ist (Env fehlt): führe `make layer-venv-sync` aus und wiederhole.
- Falls das Verzeichnis kein Git-Repo ist: brich ab mit `ERROR: Not in a repository root`.
