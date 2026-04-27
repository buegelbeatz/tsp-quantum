<!-- layer: digital-generic-team -->
# /roles Prompt

Discover and display all generic roles and their associated agents in a deterministic tree hierarchy.

This prompt provides visibility into the role-to-agent architecture by scanning all `generic-<role>.agent.md` files in `.github/agents/roles/` and showing which agents are available under each role.

## Purpose
- Understand available roles in the current workspace
- List agents available within each role
- Verify role-to-agent mappings are consistent
- Support troubleshooting of role/agent configuration issues

## Typical Usage

```text
/roles
```

Output will display a tree followed by an unassigned section:

```
💼 Role Tree – .github/agents/roles/

generic-deliver
└── fullstack-engineer

generic-expert
└── (no agents listed)

generic-review
└── (no agents listed)

🔓 Unassigned Agents (not mapped to any generic role)
  - agile-coach
   - data-scientist
  - mcp-expert
  - platform-architect
  - pullrequest-reviewer
  - quality-expert
  - quantum-expert
  - security-expert
  - ux-designer

Use /roles-add to assign an agent to a role.
```

## Execution Contract

1. Scan `.github/agents/roles/` directory for files matching `generic-*.agent.md`.
2. Parse YAML frontmatter for each role file.
3. Extract `agents:` list (if present) and sort alphabetically.
4. Print tree structure in deterministic order (roles sorted by name).
5. Skip roles with empty agent lists; mark as `(no agents listed)`.
6. Report missing or malformed YAML files with diagnostics.
7. Support both terminal and markdown rendering.
8. After the role tree, collect all `*.agent.md` files **not** matching `generic-*.agent.md` (non-generic agents).
9. Compute the set of all agent names referenced in any `agents:` field across all role files.
10. Print an **Unassigned Agents** section listing non-generic agents absent from all role `agents:` lists, sorted alphabetically.
11. Use `/roles-add` to assign an unassigned agent to a role.

## Role Discovery Logic

For each file `generic-<ROLE>.agent.md`:
1. Read YAML frontmatter block (between `---` markers).
2. Extract `agents:` array.
3. If agents exist, list them indented under the role.
4. If no agents field exists, mark as unassigned.
5. If YAML parse fails, emit diagnostic message.

## Output Format

Deterministic tree output:
- Roles sorted alphabetically by name
- Agents within each role sorted alphabetically
- Tree characters: `├──`, `└──` for hierarchy
- UTF-8 symbols for clarity (optional: fallback ASCII if terminal lacks UTF-8)

## Validation & Diagnostics

If role files are missing or malformed:
- Report file path and error reason
- Continue processing other roles
- Do not crash on partial failures

Example diagnostic:
```
[WARNING] agents/roles/generic-custom.agent.md: YAML parse error on line 3
[SUCCESS] 4 roles discovered, 3 assigned agents, 10 unassigned agents
```

## Open Question Resolutions (Spec 006)

1. **Should `/roles` include inactive/deprecated agents?**
   - **Decision:** Include all agents listed in the `agents:` field. The role/agent file status determines visibility, not marking within the tree.
   
2. **Should it support filters by role prefix or workspace folder?**
   - **Decision:** MVP includes full tree only. Future enhancement can add `--role=<pattern>` or `--workspace=<folder>` filters.

## Execution Notes

- This prompt requires no implementation changes or git operations.
- Output is read-only and diagnostic only.
- Run `make help` to see other available prompts.
