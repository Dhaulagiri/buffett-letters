#!/usr/bin/env python3
"""Local, opt-in Berkshire letter corpus workflow. No source links are bundled."""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zlib
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen

YEARS = range(1977, 2025)
DEFAULT_MANIFEST = Path(".local/source-manifest.json")
BLOCKS = {"p", "div", "li", "blockquote", "section", "article", "br"}
HEADINGS = {f"h{i}" for i in range(1, 7)}


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("letters"), list):
        raise ValueError("Manifest needs schema_version 1 and a letters array")
    return data


def source_file(raw_dir: Path, row: dict) -> Path:
    fmt = row.get("format")
    return raw_dir / f"{row['year']}.{fmt}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def decode_http_body(content: bytes, encoding: str | None) -> bytes:
    """Decode transport compression before saving and hashing a source file."""
    if not encoding or encoding.lower() == "identity":
        return content
    if encoding.lower() == "gzip":
        return zlib.decompress(content, wbits=31)
    if encoding.lower() == "br":
        try:
            import brotli
        except ImportError:
            node = shutil.which("node")
            if not node:
                raise RuntimeError("Brotli response needs Python brotli or Node.js")
            result = subprocess.run(
                [node, "-e", "let b=[];process.stdin.on('data',d=>b.push(d));process.stdin.on('end',()=>process.stdout.write(require('zlib').brotliDecompressSync(Buffer.concat(b))))"],
                input=content, capture_output=True, check=True,
            )
            return result.stdout
        return brotli.decompress(content)
    raise RuntimeError(f"Unsupported HTTP content encoding: {encoding}")


def init(args: argparse.Namespace) -> None:
    if args.manifest.exists():
        raise ValueError(f"Manifest already exists: {args.manifest}")
    save_json(args.manifest, {
        "schema_version": 1,
        "letters": [{
            "year": year, "author": "Warren Buffett", "format": None,
            "archive_entry": None, "publication_date": None,
            "source_url": None, "source_path": None, "sha256": None,
            "accessed_at": None, "extraction_method": None, "quality_issues": [],
        } for year in YEARS],
    })
    print(f"Created {args.manifest} with 48 private source slots")


def fetch(args: argparse.Namespace) -> None:
    if not args.allow_network:
        raise ValueError("Network access requires --allow-network")
    data = load_manifest(args.manifest)
    selected = set(args.years or YEARS)
    fetched = 0
    for row in data["letters"]:
        if row.get("year") not in selected:
            continue
        url = row.get("source_url")
        fmt = row.get("format")
        if not url or fmt not in {"html", "pdf"}:
            continue
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {"berkshirehathaway.com", "www.berkshirehathaway.com"}:
            raise ValueError(f"Year {row['year']}: expected an official HTTPS source")
        destination = source_file(args.raw_dir, row)
        if destination.exists() and not args.replace:
            print(f"{row['year']}: existing source retained")
            continue
        req = Request(url, headers={"User-Agent": "OwnerLetterResearch/0.1 (personal, rate-limited research)"})
        error = None
        for attempt in range(3):
            try:
                with urlopen(req, timeout=30) as response:
                    content = response.read(30 * 1024 * 1024 + 1)
                    encoding = response.headers.get("Content-Encoding")
                if len(content) > 30 * 1024 * 1024:
                    raise ValueError("source exceeds 30 MiB limit")
                content = decode_http_body(content, encoding)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
                row["sha256"] = sha256(destination)
                row["accessed_at"] = datetime.now(timezone.utc).isoformat()
                fetched += 1
                print(f"{row['year']}: fetched {len(content)} bytes")
                break
            except Exception as exc:
                error = exc
                if attempt < 2:
                    time.sleep(2 ** attempt + 1)
        else:
            print(f"{row['year']}: fetch failed: {error}", file=sys.stderr)
        if fetched:
            save_json(args.manifest, data)
        time.sleep(args.delay)
    print(f"Fetched {fetched} sources")


class LetterHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.segments: list[dict] = []
        self.parts: list[str] = []
        self.line = 1
        self.column = 0
        self.kind = "paragraph"
        self.skip = 0
        self.table = 0
        self.cell = 0
        self.max_colspan = 1
        self.text_offset = 0
        self.in_pre = False
        self.pre_parts: list[str] = []
        self.pre_line = 1
        self.pre_column = 0

    def flush(self) -> None:
        value = re.sub(r"\s+", " ", "".join(self.parts)).strip()
        if value:
            segment = {"kind": self.kind, "text": value, "source_line": self.line,
                       "source_column": self.column,
                       "start": self.text_offset, "end": self.text_offset + len(value)}
            if self.kind == "table_row":
                segment["cell_count"] = self.cell
                segment["max_colspan"] = self.max_colspan
            self.segments.append(segment)
            self.text_offset += len(value) + 1
        self.parts = []
        self.kind = "paragraph"

    def flush_pre(self) -> None:
        value = "".join(self.pre_parts).strip()
        if value:
            self.segments.append({"kind": "pre_line", "text": value,
                                  "source_line": self.pre_line, "source_column": self.pre_column,
                                  "start": self.text_offset, "end": self.text_offset + len(value)})
            self.text_offset += len(value) + 1
        self.pre_parts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "title"}:
            self.skip += 1
        if self.skip:
            return
        if tag == "pre":
            self.flush()
            self.in_pre = True
            self.pre_line, self.pre_column = self.getpos()
            return
        if self.in_pre:
            if tag == "br":
                self.flush_pre()
                self.pre_line = self.getpos()[0] + 1
                self.pre_column = 0
            return
        if tag in HEADINGS or tag in BLOCKS or tag in {"tr", "table"}:
            self.flush()
        if tag in HEADINGS:
            self.kind = "heading"
            self.line, self.column = self.getpos()
        elif tag == "table":
            self.table += 1
        elif tag == "tr":
            self.kind = "table_row"
            self.line, self.column = self.getpos()
            self.cell = 0
            self.max_colspan = 1
        elif tag in {"td", "th"}:
            if self.cell:
                self.parts.append(" | ")
            self.cell += 1
            values = dict(attrs)
            try:
                self.max_colspan = max(self.max_colspan, int(values.get("colspan") or 1))
            except ValueError:
                pass
        elif not self.parts:
            self.line, self.column = self.getpos()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "title"}:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == "pre":
            self.flush_pre()
            self.in_pre = False
            return
        if self.in_pre:
            return
        if tag in HEADINGS or tag in BLOCKS or tag == "tr":
            self.flush()
        if tag == "tr":
            self.cell = 0
            self.max_colspan = 1
        if tag == "table":
            self.table = max(0, self.table - 1)

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        if self.in_pre:
            if not self.pre_parts:
                self.pre_line, self.pre_column = self.getpos()
            for part in data.splitlines(keepends=True):
                if part.endswith(("\n", "\r")):
                    self.pre_parts.append(part.rstrip("\r\n"))
                    self.flush_pre()
                    self.pre_line += 1
                    self.pre_column = 0
                else:
                    self.pre_parts.append(part)
            return
        if not data.strip():
            return
        if not self.parts:
            self.line, self.column = self.getpos()
        self.parts.append(data)


def extract_html(path: Path) -> tuple[list[dict], list[str], str]:
    raw = path.read_bytes()
    decoded = raw.decode("utf-8", errors="replace")
    # Older letters may use Western encodings. Avoid replacing visible glyphs.
    if "\ufffd" in decoded:
        decoded = raw.decode("cp1252", errors="replace")
    parser = LetterHTMLParser()
    parser.feed(decoded)
    parser.flush()
    return parser.segments, [], "stdlib.HTMLParser"


def extract_pdf(path: Path) -> tuple[list[dict], list[str], str]:
    warnings = []
    if shutil.which("pdftotext"):
        result = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
                                check=True, capture_output=True, text=True)
        pages = result.stdout.split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
        method = "poppler.pdftotext-layout"
        if shutil.which("pdfinfo"):
            info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
            match = re.search(r"^Pages:\s*(\d+)", info.stdout, re.MULTILINE)
            if match and int(match.group(1)) != len(pages):
                warnings.append(f"page_count_mismatch:{match.group(1)}:{len(pages)}")
    else:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF extraction requires Poppler pdftotext or Python pypdf") from exc
        reader = PdfReader(str(path))
        pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
        method = "pypdf.layout"
    if not pages:
        warnings.append("no_pages")
    segments = []
    offset = 0
    for page_number, page in enumerate(pages, 1):
        if not page.strip():
            warnings.append(f"empty_page:{page_number}")
        for line_number, line in enumerate(page.splitlines(), 1):
            value = line.rstrip()
            if not value.strip():
                continue
            segments.append({"kind": "line", "text": value, "page": page_number,
                             "page_line": line_number, "start": offset, "end": offset + len(value)})
            offset += len(value) + 1
    return segments, warnings, method


def diagnostics(segments: list[dict], warnings: list[str]) -> list[str]:
    joined = "\n".join(item["text"] for item in segments)
    if len(joined) < 300:
        warnings.append(f"short_extraction:{len(joined)}")
    if "\ufffd" in joined:
        warnings.append(f"replacement_characters:{joined.count(chr(0xfffd))}")
    pages = {}
    for item in segments:
        if "page" in item:
            pages.setdefault(item["page"], []).append(item["text"].strip())
    if pages:
        first_lines = [lines[0] for lines in pages.values() if lines]
        if len(first_lines) >= 3 and max(first_lines.count(line) for line in set(first_lines)) >= 3:
            warnings.append("repeated_page_headers")
        for number, lines in pages.items():
            if not "".join(lines).strip():
                warnings.append(f"empty_page:{number}")
    for item in segments:
        if (item["kind"] == "table_row" and "|" not in item["text"]
                and item.get("max_colspan", 1) == 1):
            warnings.append(f"single_cell_table_row:{item['source_line']}")
    return sorted(set(warnings))


def extract(args: argparse.Namespace) -> None:
    data = load_manifest(args.manifest)
    selected = set(args.years or YEARS)
    count = 0
    for row in data["letters"]:
        if row.get("year") not in selected or row.get("format") not in {"html", "pdf"}:
            continue
        path = source_file(args.raw_dir, row)
        if not path.exists() and row.get("source_path"):
            path = Path(row["source_path"])
        if not path.exists():
            print(f"{row['year']}: missing local source", file=sys.stderr)
            continue
        if row["format"] == "html":
            segments, warnings, method = extract_html(path)
        else:
            segments, warnings, method = extract_pdf(path)
        warnings = diagnostics(segments, warnings)
        row["sha256"] = sha256(path)
        row["extraction_method"] = method
        row["quality_issues"] = warnings
        save_json(args.extracted_dir / f"{row['year']}.json", {
            "year": row["year"], "author": row["author"], "format": row["format"],
            "source_sha256": row["sha256"], "method": method, "warnings": warnings,
            "segments": segments,
        })
        print(f"{row['year']}: {len(segments)} segments; {len(warnings)} warnings")
        count += 1
    save_json(args.manifest, data)
    print(f"Extracted {count} sources")


def validate(args: argparse.Namespace) -> int:
    data = load_manifest(args.manifest)
    rows = data["letters"]
    issues: list[str] = []
    years = [row.get("year") for row in rows]
    if len(rows) != 48 or sorted(years) != list(YEARS):
        issues.append("manifest must contain each year 1977–2024 exactly once")
    report = []
    for row in rows:
        year = row.get("year")
        state = "ready"
        row_issues = []
        if row.get("author") != "Warren Buffett":
            row_issues.append("author mismatch")
        if row.get("format") not in {"html", "pdf"}:
            row_issues.append("format missing or invalid")
        if not row.get("source_url") and not row.get("source_path"):
            row_issues.append("source locator missing")
        if row.get("format") in {"html", "pdf"}:
            raw = source_file(args.raw_dir, row)
            if not raw.exists() and row.get("source_path"):
                raw = Path(row["source_path"])
            if not raw.exists():
                row_issues.append("source file missing")
            elif row.get("sha256") != sha256(raw):
                row_issues.append("source hash missing or mismatched")
            output = args.extracted_dir / f"{year}.json"
            if not output.exists():
                row_issues.append("extraction missing")
            else:
                doc = json.loads(output.read_text(encoding="utf-8"))
                if doc.get("source_sha256") != row.get("sha256"):
                    row_issues.append("extraction source hash mismatch")
                if not doc.get("segments"):
                    row_issues.append("extraction empty")
        if row_issues:
            state = "incomplete"
            issues.extend(f"{year}: {item}" for item in row_issues)
        report.append({"year": year, "state": state, "warnings": row.get("quality_issues", []), "issues": row_issues})
    result = {"coverage": {"expected": 48, "ready": sum(r["state"] == "ready" for r in report)},
              "issues": issues, "letters": report}
    if args.report:
        save_json(args.report, result)
    print(json.dumps(result["coverage"]))
    for issue in issues:
        print(issue)
    for row in report:
        for warning in row["warnings"]:
            print(f"{row['year']}: warning: {warning}")
    return 0 if not issues else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=Path(".local/corpus/raw"))
    parser.add_argument("--extracted-dir", type=Path, default=Path(".local/corpus/extracted"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    fetch_parser = sub.add_parser("fetch")
    fetch_parser.add_argument("--allow-network", action="store_true")
    fetch_parser.add_argument("--replace", action="store_true")
    fetch_parser.add_argument("--delay", type=float, default=2.0)
    fetch_parser.add_argument("--years", nargs="*", type=int)
    extract_parser = sub.add_parser("extract")
    extract_parser.add_argument("--years", nargs="*", type=int)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--report", type=Path, default=Path(".local/corpus/report.json"))
    args = parser.parse_args()
    try:
        if args.command == "init":
            init(args)
        elif args.command == "fetch":
            fetch(args)
        elif args.command == "extract":
            extract(args)
        else:
            return validate(args)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
