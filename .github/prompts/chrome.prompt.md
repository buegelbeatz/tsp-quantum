<!-- layer: digital-generic-team -->
# /chrome Prompt

Run a Chrome MCP browser task from a URL and produce a markdown report in .specifications.

Default command:

```bash
make chrome URL="https://www.google.com/search?q=Skoda+Elroq" JOB="Find top 5 links, load text from pages and create a markdown summary of findings"
```

Optional command (custom limit and MCP endpoint):

```bash
make chrome URL="https://www.google.com/search?q=Skoda+Elroq" JOB="Find top 5 links, load text from pages and create a markdown summary of findings" LIMIT=5 MCP_BROWSER_URL="http://[::1]:9222"
```

## Execution contract

1. Validate required inputs `URL` and `JOB`.
2. Use Chrome DevTools MCP connected to the dedicated VSCode browser runtime.
3. Open the source URL and collect the top homepage links (up to `LIMIT`, default 5).
4. Visit each homepage and extract page title plus compact text excerpt.
5. Create one markdown report with links and findings.
6. Save the report under `.specifications/` and print the report path.

## Documentation contract

- Keep prompt examples make-based only.
- Keep this command listed exactly once in `/help`.
- Keep matching skill metadata in `skills/prompt-chrome/SKILL.md`.

## Verification

Run:

```bash
make chrome URL="https://www.google.com/search?q=Skoda+Elroq" JOB="Find top 5 links, load text from pages and create a markdown summary of findings" LIMIT=5
```

Expected result:

- command exits with status 0
- JSON output contains `status: ok` and `report`
- markdown report exists under `.specifications/`
