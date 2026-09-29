"""Checks for each part of a shared Claude Code configuration.

Every check returns `Finding`s. `error` means the team setup is broken or unsafe, `warning` means
it works but will surprise someone, and `ok` records what was verified.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from claude_config_check.parsing import (
    FrontmatterError,
    as_list,
    glob_matches,
    is_git_ignored,
    project_files,
    read_frontmatter,
)

CLAUDE_MD_MAX_LINES = 200
FILE_WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SECRET_KEY = re.compile(r"TOKEN|SECRET|PASSWORD|API_?KEY|AUTH", re.IGNORECASE)
ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")
PURE_REF = re.compile(r"^\$\{[A-Za-z_][A-Za-z0-9_]*\}$")
LOOKS_LIKE_SECRET = re.compile(
    r"\b(sk-ant-[\w-]{10,}|ghp_\w{20,}|xox[bp]-[\w-]{10,}|AKIA[0-9A-Z]{16})"
)


@dataclass(frozen=True)
class Finding:
    level: str  # "ok" | "warning" | "error"
    area: str
    message: str


def ok(area: str, message: str) -> Finding:
    return Finding("ok", area, message)


def warning(area: str, message: str) -> Finding:
    return Finding("warning", area, message)


def error(area: str, message: str) -> Finding:
    return Finding("error", area, message)


# --- CLAUDE.md hierarchy ----------------------------------------------------------------------


def check_claude_md(root: Path) -> list[Finding]:
    area = "CLAUDE.md"
    project_file = next(
        (p for p in (root / "CLAUDE.md", root / ".claude" / "CLAUDE.md") if p.exists()), None
    )
    if project_file is None:
        return [error(area, "No project CLAUDE.md: the team has no shared instructions.")]

    rel = project_file.relative_to(root).as_posix()
    findings = []
    if is_git_ignored(root, rel):
        findings.append(error(area, f"{rel} is git-ignored, so teammates never receive it."))
    else:
        findings.append(ok(area, f"{rel} is committed, so every teammate loads it."))

    lines = len(project_file.read_text(encoding="utf-8").splitlines())
    if lines > CLAUDE_MD_MAX_LINES:
        findings.append(
            warning(area, f"{rel} has {lines} lines; move area-specific parts to .claude/rules/.")
        )
    else:
        findings.append(ok(area, f"{rel} is {lines} lines (limit {CLAUDE_MD_MAX_LINES})."))

    if not is_git_ignored(root, "CLAUDE.local.md"):
        findings.append(
            error(area, "CLAUDE.local.md is not git-ignored; personal notes would leak.")
        )
    else:
        findings.append(ok(area, "CLAUDE.local.md is git-ignored (personal, per developer)."))

    for nested in sorted(root.glob("src/**/CLAUDE.md")):
        findings.append(
            ok(area, f"{nested.relative_to(root).as_posix()} loads lazily for its subdirectory.")
        )
    return findings


# --- Path-scoped rules ------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    path: str
    globs: tuple[str, ...]

    @property
    def always_loaded(self) -> bool:
        return not self.globs

    def applies_to(self, relpath: str) -> bool:
        return self.always_loaded or any(glob_matches(g, relpath) for g in self.globs)


def load_rules(root: Path) -> list[Rule]:
    rules = []
    for path in sorted((root / ".claude" / "rules").rglob("*.md")):
        frontmatter, _ = read_frontmatter(path)
        rules.append(
            Rule(path.relative_to(root).as_posix(), tuple(as_list(frontmatter.get("paths"))))
        )
    return rules


def rules_for(root: Path, relpath: str) -> list[Rule]:
    """The rules Claude Code would load when working on `relpath`."""
    return [rule for rule in load_rules(root) if rule.applies_to(relpath)]


def check_rules(root: Path) -> list[Finding]:
    area = "rules"
    rules_dir = root / ".claude" / "rules"
    if not rules_dir.exists():
        return [warning(area, "No .claude/rules/: every convention loads in every session.")]

    findings = []
    files = [f for f in project_files(root) if not f.startswith(".claude/")]
    for path in sorted(rules_dir.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        try:
            frontmatter, body = read_frontmatter(path)
        except FrontmatterError as exc:
            findings.append(error(area, str(exc)))
            continue
        if not body.strip():
            findings.append(error(area, f"{rel} has no content."))
        globs = as_list(frontmatter.get("paths"))
        if not globs:
            findings.append(warning(area, f"{rel} has no `paths`, so it loads in every session."))
            continue
        covered = set()
        for glob in globs:
            matched = [f for f in files if glob_matches(glob, f)]
            if not matched:
                findings.append(warning(area, f"{rel}: glob {glob!r} matches no file (dead glob)."))
            covered.update(matched)
        findings.append(ok(area, f"{rel} is path-scoped to {len(covered)} file(s) via {globs}."))
    return findings


# --- Skills and commands ----------------------------------------------------------------------


def _tool_name(entry: str) -> str:
    return entry.split("(", 1)[0].strip()


def _is_write_capable(entry: str) -> bool:
    """File-editing tools in any form, or Bash without a command pattern."""
    name = _tool_name(entry)
    return name in FILE_WRITE_TOOLS or (name == "Bash" and "(" not in entry)


def check_skills(root: Path) -> list[Finding]:
    area = "skills"
    findings = []
    for skill_file in sorted((root / ".claude" / "skills").glob("*/SKILL.md")):
        rel = skill_file.relative_to(root).as_posix()
        folder = skill_file.parent.name
        try:
            frontmatter, _ = read_frontmatter(skill_file)
        except FrontmatterError as exc:
            findings.append(error(area, str(exc)))
            continue
        if not frontmatter.get("description"):
            findings.append(error(area, f"{rel}: missing `description`; Claude can't select it."))
        name = frontmatter.get("name")
        if name and name != folder:
            findings.append(warning(area, f"{rel}: name {name!r} differs from folder {folder!r}."))

        context = frontmatter.get("context")
        if context is None:
            findings.append(ok(area, f"/{folder} runs inline in the main conversation."))
            continue
        if context != "fork":
            findings.append(error(area, f"{rel}: context must be 'fork', got {context!r}."))
            continue

        tools = as_list(frontmatter.get("allowed-tools"))
        if not tools:
            findings.append(error(area, f"{rel}: forked skill without `allowed-tools`."))
            continue
        writers = [t for t in tools if _is_write_capable(t)]
        if writers:
            findings.append(
                error(area, f"{rel}: forked audit skill grants write-capable tools {writers}.")
            )
            continue
        findings.extend(_check_fork_agent(root, rel, folder, frontmatter.get("agent")))
    return findings


def _check_fork_agent(root: Path, rel: str, folder: str, agent: str | None) -> list[Finding]:
    """`allowed-tools` only pre-approves tools. The fork's real tool set is its agent's `tools`."""
    area = "skills"
    agent = agent or "general-purpose"
    agent_file = root / ".claude" / "agents" / f"{agent}.md"
    if not agent_file.exists():
        return [
            warning(
                area,
                f"{rel}: forks into built-in agent {agent!r}, whose tools `allowed-tools` does not "
                "narrow. Point `agent` at a .claude/agents/ file with a read-only `tools` list.",
            )
        ]
    agent_tools = as_list(read_frontmatter(agent_file)[0].get("tools"))
    if not agent_tools:
        return [error(area, f"{rel}: agent {agent!r} has no `tools` list, so it inherits all.")]
    writers = [t for t in agent_tools if _is_write_capable(t)]
    if writers:
        return [error(area, f"{rel}: agent {agent!r} can write: {writers}.")]
    return [ok(area, f"/{folder} forks into {agent!r}, limited to {agent_tools}.")]


def check_commands(root: Path) -> list[Finding]:
    area = "commands"
    findings = []
    for command in sorted((root / ".claude" / "commands").rglob("*.md")):
        rel = command.relative_to(root).as_posix()
        name = command.relative_to(root / ".claude" / "commands").with_suffix("").as_posix()
        try:
            frontmatter, body = read_frontmatter(command)
        except FrontmatterError as exc:
            findings.append(error(area, str(exc)))
            continue
        problems = []
        if not frontmatter.get("description"):
            problems.append("no `description` (the / menu shows the first line instead)")
        if "$ARGUMENTS" in body and not frontmatter.get("argument-hint"):
            problems.append("uses $ARGUMENTS without an `argument-hint`")
        tools = as_list(frontmatter.get("allowed-tools"))
        if "!`" in body and not any(_tool_name(t) == "Bash" for t in tools):
            problems.append("injects shell output with !`...` but allows no Bash pattern")
        if problems:
            findings.extend(warning(area, f"{rel}: {p}.") for p in problems)
        else:
            findings.append(ok(area, f"/{name} is ready ({frontmatter['description'][:60]}...)."))
    return findings


# --- MCP servers and settings -----------------------------------------------------------------


def mcp_env_vars(root: Path) -> dict[str, str | None]:
    """Every ${VAR} referenced in .mcp.json, mapped to its default (None when required)."""
    path = root / ".mcp.json"
    if not path.exists():
        return {}
    refs: dict[str, str | None] = {}
    for name, default in ENV_REF.findall(path.read_text(encoding="utf-8")):
        refs[name] = default if default else refs.get(name)
    return refs


def _secret_fields(server: dict) -> list[tuple[str, str]]:
    fields = [(f"env.{k}", v) for k, v in (server.get("env") or {}).items()]
    fields += [(f"headers.{k}", v) for k, v in (server.get("headers") or {}).items()]
    return [(key, value) for key, value in fields if SECRET_KEY.search(key.split(".", 1)[1])]


def check_mcp(root: Path) -> list[Finding]:
    area = "mcp"
    path = root / ".mcp.json"
    if not path.exists():
        return [warning(area, "No .mcp.json: the team shares no MCP servers.")]
    text = path.read_text(encoding="utf-8")
    try:
        servers = json.loads(text).get("mcpServers")
    except json.JSONDecodeError as exc:
        return [error(area, f".mcp.json is not valid JSON: {exc}")]
    if not isinstance(servers, dict) or not servers:
        return [error(area, ".mcp.json has no `mcpServers` object.")]

    findings = []
    if LOOKS_LIKE_SECRET.search(text):
        findings.append(error(area, ".mcp.json contains what looks like a real credential."))
    for name, server in servers.items():
        secrets = _secret_fields(server)
        leaks = [key for key, value in secrets if not PURE_REF.match(str(value))]
        if leaks:
            findings.append(
                error(area, f"{name}: {leaks} must be a bare ${{VAR}} reference, not a value.")
            )
        elif secrets:
            keys = [key for key, _ in secrets]
            findings.append(ok(area, f"{name}: credentials {keys} come from environment vars."))
        else:
            findings.append(ok(area, f"{name}: no credentials in config."))
    return findings


def check_settings(root: Path) -> list[Finding]:
    area = "settings"
    path = root / ".claude" / "settings.json"
    if not path.exists():
        return [warning(area, "No .claude/settings.json: no shared permissions or hooks.")]
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [error(area, f".claude/settings.json is not valid JSON: {exc}")]

    findings = []
    if not is_git_ignored(root, ".claude/settings.local.json"):
        findings.append(error(area, ".claude/settings.local.json is not git-ignored."))

    servers = set()
    if (root / ".mcp.json").exists():
        servers = set(
            json.loads((root / ".mcp.json").read_text(encoding="utf-8")).get("mcpServers", {})
        )
    for name in settings.get("enabledMcpjsonServers", []):
        if name not in servers:
            findings.append(error(area, f"enabledMcpjsonServers lists unknown server {name!r}."))

    permissions = settings.get("permissions", {})
    for bucket in ("allow", "ask", "deny"):
        for entry in permissions.get(bucket, []):
            match = re.match(r"mcp__([^_]+(?:-[^_]+)*)__", entry)
            if match and match.group(1) not in servers:
                findings.append(
                    warning(area, f"permissions.{bucket} entry {entry!r} names no known server.")
                )

    for event, groups in settings.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                for script in re.findall(
                    r"\$CLAUDE_PROJECT_DIR/([^\"'\s]+)", hook.get("command", "")
                ):
                    if not (root / script).exists():
                        findings.append(error(area, f"{event} hook script {script} is missing."))

    if not [f for f in findings if f.level == "error"]:
        allow = len(permissions.get("allow", []))
        deny = len(permissions.get("deny", []))
        hooks = sorted(settings.get("hooks", {}))
        findings.append(ok(area, f"{allow} allow / {deny} deny rules; hooks on {hooks}."))
    return findings


ALL_CHECKS = (check_claude_md, check_rules, check_skills, check_commands, check_mcp, check_settings)


def run_all(root: Path) -> list[Finding]:
    return [finding for check in ALL_CHECKS for finding in check(root)]
