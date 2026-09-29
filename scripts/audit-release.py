#!/usr/bin/env python3
"""Fail when private research artifacts appear in Git or distributable skills."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATHS = {"research/observations.md"}
FORBIDDEN_PREFIXES = (".local/", "research/analyses/")
SOURCE_ID = re.compile(r"\bB-\d{4}\b")


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = [line for line in result.stdout.splitlines() if line]
    issues: list[str] = []

    for name in tracked:
        if name in FORBIDDEN_PATHS or name.startswith(FORBIDDEN_PREFIXES):
            issues.append(f"private research path tracked: {name}")

    for path in sorted((ROOT / "skills").rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        if "https://" in content or "http://" in content:
            issues.append(f"external URL in skill: {relative}")
        if SOURCE_ID.search(content):
            issues.append(f"letter-level source identifier in skill: {relative}")

    if issues:
        for issue in issues:
            print(issue)
        return 1

    print(f"Release boundary passed: {len(tracked)} tracked files; no tracked private analysis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
