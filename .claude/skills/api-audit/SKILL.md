---
name: api-audit
description: Audit the HTTP API layer against the team's API conventions and return a compact findings table. Use when asked to audit, review, or check API routes or endpoints for convention compliance.
argument-hint: "[directory, default src/taskboard/api]"
context: fork
agent: read-only-auditor
allowed-tools: Read, Grep, Glob
---

# API convention audit

You are running in an isolated fork. Your reading stays here; only your final report goes back
to the main conversation, so keep it short.

**Scope:** `$ARGUMENTS`. If that is empty, audit `src/taskboard/api`.

1. Read `.claude/rules/api-conventions.md`. It is the checklist; don't invent extra rules.
2. Find every route decorator in scope (`@router.get`, `.post`, `.patch`, `.put`, `.delete`).
3. Check each endpoint against every rule: prefix and tags, explicit `response_model` and
   `status_code`, 201 on POST and 204 with no body on DELETE, errors through the envelope, a thin
   handler (no `try/except` around service calls, no repository access), and `Depends` for
   services.
4. Read only what you need. Do not edit anything.

## Report format

Return **only** this, at most 25 lines:

```
API audit: <N> endpoints checked, <M> findings

| # | Severity | Endpoint | File:line | Rule broken | Fix |
|---|----------|----------|-----------|-------------|-----|
```

Severity is `high` (clients see wrong behaviour), `medium` (convention drift), or `low`
(style). If there are no findings, say so in one line. No preamble and no file dumps.
