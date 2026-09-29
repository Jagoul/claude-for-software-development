"""Frontmatter parsing, glob matching, and git-ignore checks."""

import fnmatch
import re
import subprocess
from functools import cache
from pathlib import Path

import yaml

FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)(.*)\Z", re.DOTALL)
SKIPPED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}


class FrontmatterError(ValueError):
    """The file's YAML frontmatter is present but unparseable."""


def read_frontmatter(path: Path) -> tuple[dict, str]:
    """Return (frontmatter, body). A file without frontmatter returns ({}, whole text)."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        return {}, text
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"{path}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise FrontmatterError(f"{path}: frontmatter must be a mapping")
    return data, match.group(2)


def as_list(value: object) -> list[str]:
    """Normalise a frontmatter list that may be a YAML list or a comma-separated string."""
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(item).strip() for item in value]


def expand_braces(pattern: str) -> list[str]:
    match = re.search(r"\{([^{}]*)\}", pattern)
    if not match:
        return [pattern]
    head, tail = pattern[: match.start()], pattern[match.end() :]
    return [
        expanded
        for option in match.group(1).split(",")
        for expanded in expand_braces(head + option + tail)
    ]


@cache
def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a gitignore-style glob (`**` spans directories, `*` does not) to a regex."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def glob_matches(pattern: str, relpath: str) -> bool:
    relpath = relpath.replace("\\", "/").removeprefix("./")
    return any(glob_to_regex(p.removeprefix("./")).match(relpath) for p in expand_braces(pattern))


def project_files(root: Path) -> list[str]:
    """Every file under root as a POSIX relative path, skipping tool and environment folders."""
    files = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_file() and not SKIPPED_DIRS.intersection(rel.parts):
            files.append(rel.as_posix())
    return sorted(files)


def is_git_ignored(root: Path, relpath: str) -> bool:
    """Ask git when root is a repository; otherwise fall back to reading .gitignore."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", "--no-index", relpath],
            capture_output=True,
            timeout=10,
        )
        if result.returncode in (0, 1):
            return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        pass
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return False
    for line in gitignore.read_text(encoding="utf-8").splitlines():
        rule = line.strip().rstrip("/")
        if not rule or rule.startswith("#"):
            continue
        rule = rule.removeprefix("/")
        if fnmatch.fnmatch(relpath, rule) or fnmatch.fnmatch(Path(relpath).name, rule):
            return True
        if relpath.startswith(rule + "/"):
            return True
    return False
