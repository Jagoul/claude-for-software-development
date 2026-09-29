"""The `check-claude-config` command.

check-claude-config                      lint the whole setup (exit 1 on any error)
check-claude-config rules-for <file>...  which rules load when Claude works on these files
check-claude-config mcp-env              which .mcp.json variables are set in this shell
"""

import argparse
import os
import sys
from pathlib import Path

from claude_config_check.checks import mcp_env_vars, rules_for, run_all

MARKS = {"ok": "  ok  ", "warning": " warn ", "error": " FAIL "}


def cmd_check(root: Path) -> int:
    findings = run_all(root)
    area = None
    for finding in findings:
        if finding.area != area:
            area = finding.area
            print(f"\n{area}")
        print(f"  [{MARKS[finding.level]}] {finding.message}")
    errors = sum(f.level == "error" for f in findings)
    warnings = sum(f.level == "warning" for f in findings)
    print(f"\n{errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def cmd_rules_for(root: Path, files: list[str]) -> int:
    for file in files:
        rel = (
            Path(file).resolve().relative_to(root.resolve()).as_posix()
            if Path(file).is_absolute()
            else file
        )
        rules = rules_for(root, rel)
        print(rel)
        if not rules:
            print("  (no rules: only CLAUDE.md applies)")
        for rule in rules:
            why = "always" if rule.always_loaded else "matches " + ", ".join(rule.globs)
            print(f"  -> {rule.path}  ({why})")
    return 0


def cmd_mcp_env(root: Path) -> int:
    refs = mcp_env_vars(root)
    missing = 0
    for name, default in sorted(refs.items()):
        if os.environ.get(name):
            state = "set"
        elif default is not None:
            state = f"unset, falls back to {default!r}"
        else:
            state = "MISSING (required, no default)"
            missing += 1
        print(f"  {name:<20} {state}")
    if missing:
        print("\nExport the missing variables before starting `claude` (see .env.example).")
    return 1 if missing else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check-claude-config", description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root")
    sub = parser.add_subparsers(dest="command")
    rules = sub.add_parser("rules-for", help="show which rules load for the given files")
    rules.add_argument("files", nargs="+")
    sub.add_parser("mcp-env", help="show which .mcp.json variables are set")
    args = parser.parse_args(argv)

    if args.command == "rules-for":
        return cmd_rules_for(args.root, args.files)
    if args.command == "mcp-env":
        return cmd_mcp_env(args.root)
    return cmd_check(args.root)


if __name__ == "__main__":
    sys.exit(main())
