<!-- layer: digital-generic-team -->
---
mode: agent
description: Zeigt einen farbcodierten Layer-Baum aller .github/-Assets mit Layer-Herkunft und Override-Erkennung.
---

# Prompt: /layers

Scanne alle Assets unter `.github/` (Agents, Skills, Instructions, Prompts, Handoffs, Hooks, Make) und rendere eine farbcodierte Ausgabe mit Layer-Herkunft und Override-Erkennung.

Standardmodus ist **kompakt/kumulativ** (Kategorie-Summen plus zuletzt geänderte Markdown-Dateien).
Für den vollständigen Detailbaum verwende `LAYERS_MODE=full`.

## Information flow

| Field    | Value |
|----------|-------|
| Producer | `layers-tree.py` (liest `.digital-team/layers.yaml` + `.github/`) |
| Consumer | User (ANSI-Tree im Terminal / Chat-Ausgabe) |
| Trigger  | User ruft `/layers` auf |
| Payload  | Layer-Baum mit Farbkodierung und Override-Markierungen |

## Steps

`[progress][/layers] step=1/2 action=scan-github-assets`

Prüfe, ob `.digital-team/layers.yaml` vorhanden ist, und führe `layers-tree.py` aus:

```bash
make layers
```

Optional für Vollansicht:

```bash
make layers LAYERS_MODE=full
```

`[progress][/layers] step=2/2 action=render-tree`

Gib die vollständige Baumausgabe des Skripts verbatim aus. Falls ANSI-Codes nicht gerendert werden, erkläre die Farbkodierung:

| Farbe / Stil       | Bedeutung |
|--------------------|-----------|
| Fett + Grün        | Aktueller Layer (eigene Assets) |
| Gelb               | Intermediärer Layer (vererbt) |
| Blau               | Layer 0 Basis-Assets |
| Gedimmt            | Layer unbekannt |
| Rot `⛭ override-registered` | Expliziter Override aus `.digital-team/overrides.yaml` |
| Grün `✦ local-layer` | Lokales Asset des aktuellen Layers |
| Gedimmt `◌ overridden-by-child` | Parent-Pfad ist als Child-Override registriert |

## Override Detection

Ein Override gilt als **enterprise-valid**, wenn der Pfad in `.digital-team/overrides.yaml` registriert ist.
`/layers` markiert registrierte Overrides mit `⛭ override-registered`.

## Error Handling

- Falls `.digital-team/layers.yaml` fehlt: Hinweis ausgeben, dass dies ein Layer-0-Repo ist (keine Parent-Layer).
- Falls `.github/` leer oder nicht vorhanden: `WARNING: No .github assets found`.
