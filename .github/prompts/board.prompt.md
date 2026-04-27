<!-- layer: digital-generic-team -->
---
mode: agent
description: Zeigt ein oder mehrere git-basierte Lifecycle-Boards aus refs/board/*-Namespaces und unterstützt den Agent-Checkout-Workflow für verteilte Koordination.
---

# Prompt: /board

Lese die Board-Konfiguration aus `.digital-team/board.yaml`, synchronisiere lokale Refs mit dem Remote und rendere die konfigurierten Lifecycle-Boards. Standardmäßig sollen alle konfigurierten Boards getrennt aufgeschlüsselt dargestellt werden.

## Information flow

| Field    | Value |
|----------|-------|
| Producer | `board-ticket.sh` (git refs) + `board-show.py` (Rendering) |
| Consumer | User (Kanban-Board im Terminal / Chat-Ausgabe) |
| Trigger  | User ruft `/board` auf |
| Payload  | YAML-Ticket-Blobs aus den konfigurierten Board-Namespaces, gerendert als Unicode-Boxen |

## Steps

`[progress][/board] step=1/3 action=read-config`

Lese `.digital-team/board.yaml` und bestimme:
- `primary_system` (`github`, `jira`, oder `none`)
- `default_board`
- konfigurierte Boards mit `ref_prefix` und Spalten

`[progress][/board] step=2/3 action=fetch-refs`

Synchronisiere Ticket-Refs aller konfigurierten Boards vom Remote:

```bash
make board-sync
```

Falls kein Remote konfiguriert ist oder der Fetch fehlschlägt: mit lokalen Refs fortfahren und Warnung ausgeben.

`[progress][/board] step=3/3 action=render-board`

Rendere standardmäßig alle Boards getrennt. Falls nur ein bestimmtes Board angefragt wird, kann alternativ `--board <name>` verwendet werden.

```bash
make board
# optional: make board BOARD=<name>
```

## Agent Checkout Workflow

Agents koordinieren sich über atomische Ticket-Locks:

```console
# 1. Refs synchronisieren
make board-sync

# 2. Ticket atomar sperren (schlägt fehl, wenn ein anderer Agent zuerst war)
BOARD_NAME=project BOARD_AGENT=my-agent BOARD_PUSH=1 \
  bash .github/skills/board/scripts/board-ticket.sh checkout TASK-001

# 3. Arbeit ausführen ...

# 4. Ticket in done verschieben und freigeben
BOARD_NAME=project BOARD_PUSH=1 bash .github/skills/board/scripts/board-ticket.sh move TASK-001 in-progress done
```

Der `--force-with-lease`-Mechanismus stellt sicher, dass nur ein Agent gleichzeitig ein Ticket sperren kann.

## Board-Konfiguration (`.digital-team/board.yaml`)

```yaml
primary_system: github  # github | jira | none
git_board:
  enabled: true
  ref_prefix: refs/board
  default_board: project
  boards:
    project:
      ref_prefix: refs/board/project
      columns: [backlog, in-progress, blocked, done]
    exploration:
      ref_prefix: refs/board/exploration
      columns: [backlog, in-progress, blocked, done]
github:
  project_number: 1
atlassian:
  base_url: ""
  project_key: ""
```

## Atlassian / Jira (zukünftig)

Wenn `primary_system: jira` gesetzt ist und `atlassian.base_url` + `atlassian.project_key` befüllt sind, kann eine zukünftige Integration Tickets direkt aus Jira lesen. Bis dahin bleibt `git_board` der aktive Backend.

## Environment Variables

| Variable       | Standard | Beschreibung |
|---------------|---------|--------------|
| `BOARD_REMOTE` | `origin` | Git-Remote für fetch/push |
| `BOARD_NAME`  | konfiguriertes `default_board` | Ziel-Board für create/move/checkout/list |
| `BOARD_AGENT`  | `$USER`  | Agent-ID für Ticket-Lock |
| `BOARD_PUSH`   | `0`      | `1` = automatisch nach Remote pushen |

## Error Handling

- Board-Konfiguration fehlt: Warnung ausgeben, Standard-Werte annehmen (`primary_system: none`, Spalten: backlog/in-progress/blocked/done).
- Keine Tickets vorhanden: Board mit leeren Spalten anzeigen.
- Fetch schlägt fehl: lokale Refs verwenden, Warnung `WARNING: Could not fetch from remote` ausgeben.
