#!/usr/bin/env python3
"""Create a skill-only ZIP; reject source data, links, and unexpected files."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile


def package(root: Path, output: Path) -> int:
    skills = root / "skills"
    if not skills.is_dir():
        raise ValueError("skills/ is missing")
    files = sorted(p for p in skills.rglob("*") if p.is_file())
    if not files:
        raise ValueError("skills/ has no files")
    folders = sorted(p for p in skills.iterdir() if p.is_dir())
    if any(not (folder / "SKILL.md").is_file() for folder in folders):
        raise ValueError("Every skill folder must contain SKILL.md")
    if len(folders) != 8:
        raise ValueError(f"Expected 8 skills, found {len(folders)}")
    for path in files:
        if path.is_symlink() or path.suffix != ".md":
            raise ValueError(f"Unexpected skill asset: {path}")
        content = path.read_text(encoding="utf-8")
        if "https://" in content or "http://" in content:
            raise ValueError(f"External URL in skill package: {path}")
        if re.search(r"\bB-\d{4}\b", content):
            raise ValueError(f"Letter-level source identifier in skill package: {path}")
        if len(content) > 100_000:
            raise ValueError(f"Unexpectedly large skill file: {path}")
    license_path = root / "LICENSE"
    if not license_path.is_file():
        raise ValueError("LICENSE is missing")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(license_path, "LICENSE")
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
    print(f"Packaged {len(folders)} skills and LICENSE into {output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("output/owner-letter-skills.zip"))
    args = parser.parse_args()
    try:
        return package(args.root, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
