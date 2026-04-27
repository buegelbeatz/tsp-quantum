<!-- layer: digital-generic-team -->
# /roles-remove Prompt

Remove an existing agent assignment from a generic role by deleting it from the role's `agents:` list in YAML frontmatter.

```text
/roles-remove generic="<role>" agent="<agent-name>"
```

Example:

```text
/roles-remove generic="deliver" agent="data-scientist"
/roles-remove generic="generic-review" agent="security-expert"
```

## Execution Contract

1. Normalize `generic=` value:
   - if value starts with `generic-`, strip the prefix
   - else use the value as-is
2. Resolve `ROLE_FILE` = `.github/agents/roles/generic-<role>.agent.md`.
3. Validate `ROLE_FILE` exists — if not, emit error and stop:
   ```
   [ERROR] roles-remove: generic role "generic-<role>" not found at <path>
   ```
4. Resolve `AGENT_FILE` = `.github/agents/<agent>.agent.md`.
5. Validate `AGENT_FILE` exists — if not, emit error and stop:
   ```
   [ERROR] roles-remove: agent "<agent>" not found at <path>
   ```
6. Read current `agents:` list from `ROLE_FILE` YAML frontmatter.
7. If `<agent>` is not present in the list, report idempotent result and stop:
   ```
   [INFO] roles-remove: "<agent>" is not assigned to "generic-<role>" — no change
   ```
8. Remove `<agent>` from the `agents:` list.
9. If resulting list is non-empty, keep alphabetical order; if empty, keep `agents:` key and no list items.
10. Write the updated frontmatter back to `ROLE_FILE`.
11. Print confirmation summary:
    ```
    [SUCCESS] roles-remove: "<agent>" x "generic-<role>"
   Updated: agents/roles/generic-<role>.agent.md
    ```
12. Immediately run `/roles` and append the refreshed role tree and unassigned section to the output.

## Documentation Contract

- No documentation files are updated by this prompt.
- `/roles` is executed automatically at the end for immediate visibility.
- Changes to agent files are tracked by git; review with `git diff`.

## Verification

After removal, confirm from the auto-appended `/roles` output that the agent no longer appears under the role and appears under **Unassigned Agents** if not mapped elsewhere.

## Constraints

- `generic=` accepts both `deliver` and `generic-deliver` (same for `expert` and `review`).
- `agent=` must match an existing agent file name exactly (e.g., `security-expert`, not `security-expert.agent.md`).
- Removing one mapping does not remove the agent from other roles.

## Available Generic Roles

| Role token | File |
|---|---|
| `deliver` | `roles/generic-deliver.agent.md` |
| `expert` | `roles/generic-expert.agent.md` |
| `review` | `roles/generic-review.agent.md` |
