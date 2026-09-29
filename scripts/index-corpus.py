#!/usr/bin/env python3
"""Scan every extracted letter locally and write a private navigation index.

The index is a retrieval aid, not a content analysis or proof that every
occurrence has been interpreted. It stays under `.local/` by default.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TOPICS = {
    "owner_audience": [r"\bshareholders?\b", r"\bowners?\b", r"\bpartners?\b"],
    "scorecard": [r"\bbook value\b", r"\bintrinsic value\b", r"\boperating earnings?\b", r"\bper.share\b", r"\bnet worth\b"],
    "capital": [r"\bacquisitions?\b", r"\brepurchases?\b", r"\bdividends?\b", r"\bcapital allocation\b", r"\binvestments?\b"],
    "setbacks": [r"\bmistakes?\b", r"\berrors?\b", r"\bloss(?:es)?\b", r"\bdisappoint\w*\b"],
    "uncertainty": [r"\buncertain\w*\b", r"\brisk\w*\b", r"\bforecasts?\b", r"\bexpect\w*\b", r"\bpredict\w*\b"],
}


def scan(extracted_dir: Path, output: Path) -> int:
    records = []
    missing = []
    for year in range(1977, 2025):
        path = extracted_dir / f"{year}.json"
        if not path.is_file():
            missing.append(year)
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        segments = doc.get("segments", [])
        if doc.get("year") != year or not segments:
            raise ValueError(f"Bad or empty extraction: {path}")
        topic_hits = {name: [] for name in TOPICS}
        patterns = {name: [re.compile(p, re.I) for p in terms] for name, terms in TOPICS.items()}
        words = 0
        for segment_id, segment in enumerate(segments, 1):
            body = segment.get("text", "")
            words += len(re.findall(r"\b[\w'-]+\b", body))
            for name, matchers in patterns.items():
                found = sum(len(m.findall(body)) for m in matchers)
                if found:
                    location = f"p. {segment['page']} line {segment.get('page_line', '?')}" if "page" in segment else f"HTML line {segment.get('source_line', '?')}"
                    topic_hits[name].append({
                        "segment_id": segment_id, "location": location, "matches": found,
                        "context": body[:500],
                    })
        records.append({
            "year": year,
            "source_sha256": doc.get("source_sha256"),
            "format": doc.get("format"),
            "segments_scanned": len(segments),
            "word_count_approx": words,
            "extraction_warnings": doc.get("warnings", []),
            "topics": {
                name: {
                    "matching_segments": len(hits),
                    "match_count": sum(hit["matches"] for hit in hits),
                    "navigation_examples": sorted(hits, key=lambda h: h["matches"], reverse=True)[:8],
                } for name, hits in topic_hits.items()
            },
        })
    if missing:
        raise ValueError("Missing extracted years: " + ", ".join(map(str, missing)))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"scope": "private navigation only", "letters": records}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Indexed {len(records)} complete extracted letters at {output}")
    print(f"Approximate words scanned: {sum(row['word_count_approx'] for row in records):,}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extracted", type=Path, default=Path(".local/corpus/extracted"))
    parser.add_argument("--output", type=Path, default=Path(".local/corpus/navigation-index.json"))
    args = parser.parse_args()
    try:
        return scan(args.extracted, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
