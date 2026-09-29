#!/usr/bin/env python3
"""Prepare private reading jobs and validate private review coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

YEARS = range(1977, 2025)
RUBRIC = """Analyze this one annual shareholder letter as historical evidence for owner communication.\n\nRecord only original paraphrases, never source sentences or URLs. For each observation, identify a heading or PDF page and distinguish the letter's claim from your inference. Look for scorecard definitions and limits, adverse results, allocation reasoning, uncertainty, owner orientation, and concrete operating detail. Note counterexamples and extraction defects. Do not treat this letter as investment advice or imitate the author's identity. Output one JSON file with year, format, inspected_sections, observations (each with finding, location, and optional topic/confidence), and extraction_or_access_issues.\n\nSource segments follow with their local positions. Verify ambiguous text against the original file.\n"""


def prepare(extracted: Path, jobs: Path, years: list[int], chunk_chars: int = 24000,
            compact: bool = False) -> int:
    jobs.mkdir(parents=True, exist_ok=True)
    missing = []
    for year in years:
        path = extracted / f"{year}.json"
        if not path.exists():
            missing.append(year)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("year") != year or not isinstance(data.get("segments"), list):
            raise ValueError(f"Malformed extraction: {path}")
        header = f"# B-{year}\n\nFormat: {data.get('format')}\nSource SHA-256: {data.get('source_sha256')}\nExtraction warnings: {data.get('warnings', [])}\nSegments: {len(data['segments'])}\nWhitespace compacted: {compact}\n\n"
        segments = []
        for index, seg in enumerate(data["segments"], 1):
            location = f"p. {seg['page']}, line {seg.get('page_line', '?')}" if "page" in seg else f"HTML line {seg.get('source_line', '?')}"
            value = seg.get("text", "")
            if compact:
                value = re.sub(r"[ \t]+", " ", value).strip()
            segments.append(f"[{index}; {location}] {value}")
        (jobs / f"B-{year}.md").write_text(header + RUBRIC + "\n".join(segments) + "\n", encoding="utf-8")
        chunks: list[tuple[int, int, str]] = []
        current: list[str] = []
        first = 1
        size = 0
        for index, line in enumerate(segments, 1):
            if current and size + len(line) + 1 > chunk_chars:
                chunks.append((first, index - 1, "\n".join(current)))
                current, first, size = [], index, 0
            current.append(line)
            size += len(line) + 1
        if current:
            chunks.append((first, len(segments), "\n".join(current)))
        chunk_dir = jobs / f"B-{year}"
        chunk_dir.mkdir(exist_ok=True)
        for part, (start, end, body) in enumerate(chunks, 1):
            (chunk_dir / f"part-{part:03}.md").write_text(
                header + f"Part {part}/{len(chunks)}; segments {start}–{end}.\n\n" + RUBRIC + body + "\n",
                encoding="utf-8",
            )
        (chunk_dir / "index.json").write_text(json.dumps({
            "year": year, "source_sha256": data.get("source_sha256"),
            "total_segments": len(segments), "parts": [
                {"part": part, "first_segment": start, "last_segment": end}
                for part, (start, end, _) in enumerate(chunks, 1)
            ], "extraction_warnings": data.get("warnings", []),
        }, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(years) - len(missing)} private agent briefs in {jobs}")
    if missing:
        print("Missing extracted years: " + ", ".join(map(str, missing)))
    return 0 if not missing else 1


def validate_full(analyses: Path, jobs: Path, extracted: Path, years: list[int]) -> int:
    """Check private review records against every extracted chunk and source hash.

    This validates declared coverage and provenance, not the truth of an analyst's
    claim that they read each chunk. A human still has to assess each finding.
    """
    issues = []
    for year in years:
        path = analyses / f"B-{year}.json"
        index_path = jobs / f"B-{year}" / "index.json"
        source_path = extracted / f"{year}.json"
        if not path.exists() or not index_path.exists() or not source_path.exists():
            issues.append(f"B-{year}: missing analysis, job index, or extraction")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            index = json.loads(index_path.read_text(encoding="utf-8"))
            source = json.loads(source_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            issues.append(f"B-{year}: invalid JSON: {exc}")
            continue
        expected_parts = list(range(1, len(index["parts"]) + 1))
        expected_hash = source.get("source_sha256")
        checks = {
            "schema_version": data.get("schema_version") == 1,
            "year": data.get("year") == year,
            "format": data.get("format") == source.get("format"),
            "source_sha256": data.get("source_sha256") == expected_hash == index.get("source_sha256"),
            "segment_count": data.get("segment_count") == len(source.get("segments", [])) == index.get("total_segments"),
            "chunk_count": data.get("chunk_count") == len(expected_parts),
            "chunks_reviewed": data.get("chunks_reviewed") == expected_parts,
            "review_scope": data.get("review_scope") == "all extracted chunks read",
            "findings": isinstance(data.get("findings"), list) and len(data.get("findings", [])) >= 3,
            "counterexamples": isinstance(data.get("counterexamples"), list),
            "extraction_issues": isinstance(data.get("extraction_issues"), list),
        }
        for name, valid in checks.items():
            if not valid:
                issues.append(f"B-{year}: {name} invalid or inconsistent")
        for number in expected_parts:
            if not (jobs / f"B-{year}" / f"part-{number:03}.md").exists():
                issues.append(f"B-{year}: private part {number} missing")
        for number, item in enumerate(data.get("findings", []), 1):
            if not isinstance(item, dict) or not all(item.get(key) for key in ("topic", "location", "paraphrase", "confidence")):
                issues.append(f"B-{year}: finding {number} incomplete")
        for number, item in enumerate(data.get("counterexamples", []), 1):
            if not isinstance(item, dict) or not all(item.get(key) for key in ("topic", "location", "paraphrase")):
                issues.append(f"B-{year}: counterexample {number} incomplete")
        raw = path.read_text(encoding="utf-8")
        if "https://" in raw or "http://" in raw:
            issues.append(f"B-{year}: source URL in private analysis")
    for issue in issues:
        print(issue)
    print(f"Private full-analysis coverage: {len(years) - len(set(x.split(':')[0] for x in issues))}/{len(years)} valid records")
    return 1 if issues else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="Create ignored one-letter briefs from local extracted corpus")
    prep.add_argument("--extracted", type=Path, default=Path(".local/corpus/extracted"))
    prep.add_argument("--jobs", type=Path, default=Path(".local/analysis-jobs"))
    prep.add_argument("--chunk-chars", type=int, default=24000,
                      help="Maximum approximate characters in each private reading part")
    prep.add_argument("--compact", action="store_true",
                      help="Collapse horizontal whitespace in private briefs; original extraction is unchanged")
    full_check = sub.add_parser("validate-full", help="Check private full-text review coverage and provenance")
    full_check.add_argument("--analyses", type=Path, default=Path(".local/analysis-full"))
    full_check.add_argument("--jobs", type=Path, default=Path(".local/analysis-jobs"))
    full_check.add_argument("--extracted", type=Path, default=Path(".local/corpus/extracted"))
    for cmd in (prep, full_check):
        cmd.add_argument("--year", type=int, action="append", choices=YEARS, dest="years")
    args = parser.parse_args()
    years = sorted(set(args.years or YEARS))
    if args.command == "prepare":
        if args.chunk_chars < 1000:
            parser.error("--chunk-chars must be at least 1000")
        return prepare(args.extracted, args.jobs, years, args.chunk_chars, args.compact)
    return validate_full(args.analyses, args.jobs, args.extracted, years)


if __name__ == "__main__":
    raise SystemExit(main())
