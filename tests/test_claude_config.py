"""The shared Claude Code configuration in this repo, checked with check-claude-config."""

import json
import shutil

import pytest

from claude_config_check.checks import (
    check_claude_md,
    check_mcp,
    check_rules,
    check_settings,
    check_skills,
    mcp_env_vars,
    rules_for,
    run_all,
)
from claude_config_check.parsing import glob_matches, read_frontmatter


def errors(findings):
    return [f.message for f in findings if f.level == "error"]


def warnings(findings):
    return [f.message for f in findings if f.level == "warning"]


# --- This repository's configuration passes ---------------------------------------------------


def test_repository_configuration_has_no_errors_or_warnings(project_root):
    findings = run_all(project_root)

    assert errors(findings) == []
    assert warnings(findings) == []


@pytest.mark.parametrize(
    ("file", "expected_rules"),
    [
        ("src/taskboard/api/routes/tasks.py", {"api-conventions"}),
        ("src/taskboard/api/errors.py", {"api-conventions"}),
        ("tests/test_tasks_api.py", {"testing-conventions"}),
        ("tests/conftest.py", {"testing-conventions"}),
        ("src/taskboard/models.py", {"domain-models"}),
        ("src/taskboard/services/tasks.py", {"domain-models"}),
        ("src/team_tracker/server.py", set()),
        ("README.md", set()),
    ],
)
def test_each_file_loads_only_its_own_rules(project_root, file, expected_rules):
    loaded = {
        rule.path.rsplit("/", 1)[-1].removesuffix(".md") for rule in rules_for(project_root, file)
    }

    assert loaded == expected_rules


def test_every_rule_is_path_scoped(project_root):
    rules_dir = project_root / ".claude" / "rules"

    for rule in rules_dir.glob("*.md"):
        frontmatter, body = read_frontmatter(rule)
        assert frontmatter.get("paths"), f"{rule.name} would load in every session"
        assert body.strip()


def test_api_audit_skill_is_forked_and_read_only(project_root):
    frontmatter, body = read_frontmatter(
        project_root / ".claude" / "skills" / "api-audit" / "SKILL.md"
    )

    agent, _ = read_frontmatter(project_root / ".claude" / "agents" / "read-only-auditor.md")

    assert frontmatter["context"] == "fork"
    assert frontmatter["agent"] == "read-only-auditor"
    assert set(frontmatter["allowed-tools"].replace(" ", "").split(",")) == {"Read", "Grep", "Glob"}
    assert set(agent["tools"].replace(" ", "").split(",")) == {"Read", "Grep", "Glob"}
    assert "$ARGUMENTS" in body


def test_mcp_credentials_come_only_from_the_environment(project_root):
    config = json.loads((project_root / ".mcp.json").read_text())

    env = config["mcpServers"]["team-tracker"]["env"]
    assert env["TRACKER_TOKEN"] == "${TRACKER_TOKEN}"
    assert mcp_env_vars(project_root) == {
        "CLAUDE_PROJECT_DIR": ".",
        "TRACKER_TOKEN": None,
        "TRACKER_PROJECT": "TB",
    }


def test_personal_files_are_git_ignored(project_root):
    gitignore = (project_root / ".gitignore").read_text().splitlines()

    for personal in ("CLAUDE.local.md", ".claude/settings.local.json", ".claude/logs/", ".env"):
        assert personal in gitignore


# --- Glob semantics ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("src/taskboard/api/**/*.py", "src/taskboard/api/errors.py", True),
        ("src/taskboard/api/**/*.py", "src/taskboard/api/routes/tasks.py", True),
        ("src/taskboard/api/**/*.py", "src/taskboard/models.py", False),
        ("**/test_*.py", "test_root.py", True),
        ("**/test_*.py", "a/b/test_deep.py", True),
        ("**/test_*.py", "a/b/helper.py", False),
        ("src/*.py", "src/a/b.py", False),
        ("src/**/*.{py,pyi}", "src/a/b.pyi", True),
    ],
)
def test_glob_matching(pattern, path, expected):
    assert glob_matches(pattern, path) is expected


# --- Broken configurations are caught ---------------------------------------------------------


@pytest.fixture
def repo_copy(project_root, tmp_path):
    """A copy of this repo's config and source tree to break on purpose."""
    for item in (".claude", "src", "tests", "CLAUDE.md", ".mcp.json", ".gitignore"):
        source = project_root / item
        target = tmp_path / item
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("logs", "__pycache__"))
        else:
            shutil.copy(source, target)
    return tmp_path


def test_literal_credential_in_mcp_json_is_an_error(repo_copy):
    config = json.loads((repo_copy / ".mcp.json").read_text())
    config["mcpServers"]["team-tracker"]["env"]["TRACKER_TOKEN"] = "tt_live_abcdef123456"
    (repo_copy / ".mcp.json").write_text(json.dumps(config))

    assert any("bare ${VAR}" in message for message in errors(check_mcp(repo_copy)))


def test_secret_with_a_default_value_is_an_error(repo_copy):
    config = json.loads((repo_copy / ".mcp.json").read_text())
    config["mcpServers"]["team-tracker"]["env"]["TRACKER_TOKEN"] = "${TRACKER_TOKEN:-tt_fallback}"
    (repo_copy / ".mcp.json").write_text(json.dumps(config))

    assert errors(check_mcp(repo_copy))


def test_forked_skill_with_write_tools_is_an_error(repo_copy):
    skill = repo_copy / ".claude" / "skills" / "api-audit" / "SKILL.md"
    skill.write_text(
        skill.read_text().replace(
            "allowed-tools: Read, Grep, Glob", "allowed-tools: Read, Edit, Bash"
        )
    )

    assert any("write-capable" in message for message in errors(check_skills(repo_copy)))


def test_forking_into_a_builtin_agent_is_a_warning(repo_copy):
    # allowed-tools pre-approves tools but doesn't remove the rest: a live run of this skill on
    # the built-in Explore agent still used Bash. Only the agent's own `tools` list restricts.
    skill = repo_copy / ".claude" / "skills" / "api-audit" / "SKILL.md"
    skill.write_text(skill.read_text().replace("agent: read-only-auditor", "agent: Explore"))

    assert any("built-in agent" in message for message in warnings(check_skills(repo_copy)))


def test_fork_agent_with_edit_tool_is_an_error(repo_copy):
    agent = repo_copy / ".claude" / "agents" / "read-only-auditor.md"
    agent.write_text(agent.read_text().replace("tools: Read, Grep, Glob", "tools: Read, Edit"))

    assert any("can write" in message for message in errors(check_skills(repo_copy)))


def test_dead_glob_in_a_rule_is_a_warning(repo_copy):
    rule = repo_copy / ".claude" / "rules" / "api-conventions.md"
    rule.write_text(rule.read_text().replace("src/taskboard/api/**/*.py", "src/api/**/*.py"))

    assert any("dead glob" in message for message in warnings(check_rules(repo_copy)))


def test_rule_without_paths_is_flagged_as_always_loaded(repo_copy):
    (repo_copy / ".claude" / "rules" / "general.md").write_text("# Always\n\n- Be kind.\n")

    assert any("every session" in message for message in warnings(check_rules(repo_copy)))


def test_unignored_claude_local_md_is_an_error(repo_copy):
    gitignore = repo_copy / ".gitignore"
    gitignore.write_text(gitignore.read_text().replace("CLAUDE.local.md\n", ""))

    assert any("CLAUDE.local.md" in message for message in errors(check_claude_md(repo_copy)))


def test_enabling_an_unknown_mcp_server_is_an_error(repo_copy):
    settings_path = repo_copy / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["enabledMcpjsonServers"].append("ghost")
    settings_path.write_text(json.dumps(settings))

    assert any("ghost" in message for message in errors(check_settings(repo_copy)))
