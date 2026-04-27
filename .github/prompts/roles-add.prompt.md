<!-- layer: digital-generic-team -->
# /roles-add Prompt

Assign an existing non-generic agent to a generic role by adding it to the role's `agents:` list in YAML frontmatter.

```text
/roles-add generic="<role>" agent="<agent-name>"
```

Example:

```text
/roles-add generic="deliver" agent="data-scientist"
/roles-add generic="review" agent="security-expert"
/roles-add generic="expert" agent="mcp-expert"
```

## Execution Contract

1. Normalize `generic=` value:
   - if value starts with `generic-`, strip the prefix
   - else use the value as-is
2. Resolve `ROLE_FILE` = `.github/agents/roles/generic-<role>.agent.md`.
3. Validate `ROLE_FILE` exists — if not, emit error and stop:
   ```
   [ERROR] roles-add: generic role "generic-<role>" not found at <path>
   ```
4. Resolve `AGENT_FILE` = `.github/agents/<agent>.agent.md`.
5. Validate `AGENT_FILE` exists — if not, emit error and stop:
   ```
   [ERROR] roles-add: agent "<agent>" not found at <path>
   ```
6. Reject if `<agent>` matches `generic-*` pattern (cannot assign a generic role to another generic role).
7. Read current `agents:` list from `ROLE_FILE` YAML frontmatter.
8. If `<agent>` is already present in the list, report idempotent result and stop:
   ```
   [INFO] roles-add: "<agent>" is already assigned to "generic-<role>" — no change
   ```
9. Add `<agent>` to the `agents:` list and maintain alphabetical order.
10. Write the updated frontmatter back to `ROLE_FILE`.
11. Print confirmation summary:
    ```
    [SUCCESS] roles-add: "<agent>" → "generic-<role>"
   Updated: agents/roles/generic-<role>.agent.md
    ```
12. Immediately run `/roles` and append the refreshed role tree and unassigned section to the output.

## Documentation Contract

- No documentation files are updated by this prompt.
- `/roles` is executed automatically at the end for immediate visibility.
- Changes to agent files are tracked by git; review with `git diff`.

## Verification

After assignment, confirm from the auto-appended `/roles` output that the agent appears under the correct role and is removed from the **Unassigned Agents** section.

## Constraints

- Only non-generic agents (files NOT matching `generic-*.agent.md`) can be assigned.
- Each agent may be assigned to multiple roles (many-to-many allowed).
- Alphabetical order in the `agents:` list is enforced on write.
- `generic=` accepts both `deliver` and `generic-deliver` (same for `expert` and `review`).
- `agent=` must match an existing agent file name exactly (e.g., `security-expert`, not `security-expert.agent.md`).

## Available Generic Roles

| Role token | File |
|---|---|
| `deliver` | `roles/generic-deliver.agent.md` |
| `expert` | `roles/generic-expert.agent.md` |
| `review` | `roles/generic-review.agent.md` |
