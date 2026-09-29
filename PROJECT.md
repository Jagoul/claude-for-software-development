# Project Brief: Claude Code for Team Development Workflow

> The design and implementation are documented in [README.md](README.md).

## Scenario

Using Claude Code to accelerate software development. Your team uses it for code
generation, refactoring, debugging, and documentation. You need to integrate it into your
development workflow with custom slash commands, CLAUDE.md configurations, and understand when to
use plan mode vs direct execution.

## Objective

Practice configuring CLAUDE.md hierarchies, custom slash commands, path-specific rules, and MCP
server integration for a multi-developer project.

## Tasks

1. Create a project-level `CLAUDE.md` with universal coding standards and testing conventions.
   Verify that instructions placed at the project level are consistently applied across all team
   members.
2. Create `.claude/rules/` files with YAML frontmatter glob patterns for different code areas
   (e.g., `paths: ["src/api/**/*"]` for API conventions, `paths: ["**/*.test.*"]` for testing
   conventions). Test that rules load only when editing matching files.
3. Create a project-scoped skill in `.claude/skills/` with `context: fork` and `allowed-tools`
   restrictions. Verify the skill runs in isolation without polluting the main conversation
   context.
4. Configure an MCP server in `.mcp.json` with environment variable expansion for credentials. Add
   a personal experimental MCP server in `~/.claude.json` and verify both are available
   simultaneously.
5. Test plan mode versus direct execution on tasks of varying complexity: a single-file bug fix, a
   multi-file library migration, and a new feature with multiple valid implementation approaches.
   Observe when plan mode provides value.
6. Start with the design first, using Mermaid diagrams, and put it in the README. This folder ships
   to GitHub as a standalone project, so the design is the front page of the README.
