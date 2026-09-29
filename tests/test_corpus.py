import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import corpus


class CorpusTests(unittest.TestCase):
    def test_init_has_exact_buffett_years(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            corpus.init(type("Args", (), {"manifest": manifest})())
            rows = corpus.load_manifest(manifest)["letters"]
            self.assertEqual([row["year"] for row in rows], list(range(1977, 2025)))
            self.assertTrue(all(row["source_url"] is None for row in rows))

    def test_html_keeps_headings_rows_and_offsets(self):
        fixture = Path(__file__).parent / "fixtures/sample.html"
        segments, warnings, method = corpus.extract_html(fixture)
        self.assertEqual(method, "stdlib.HTMLParser")
        self.assertEqual(warnings, [])
        self.assertEqual(segments[0]["kind"], "heading")
        self.assertIn("Metric | Value", [item["text"] for item in segments])
        self.assertNotIn("never include", " ".join(item["text"] for item in segments))
        self.assertTrue(all(item["end"] > item["start"] for item in segments))

    def test_spanning_table_caption_is_not_a_single_cell_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "caption.html"
            source.write_text(
                "<table><tr><td colspan='3'>Annual results</td></tr>"
                "<tr><td>Year</td><td>Revenue</td><td>Profit</td></tr></table>",
                encoding="utf-8",
            )
            segments, warnings, _ = corpus.extract_html(source)
            warnings = corpus.diagnostics(segments, warnings)
            caption = next(item for item in segments if item["text"] == "Annual results")
            self.assertEqual(caption["max_colspan"], 3)
            self.assertNotIn(f"single_cell_table_row:{caption['source_line']}", warnings)

    def test_diagnostics_detect_short_and_replacement(self):
        segments = [{"kind": "line", "text": "bad\ufffd", "page": 1}]
        warnings = corpus.diagnostics(segments, [])
        self.assertIn("short_extraction:4", warnings)
        self.assertIn("replacement_characters:1", warnings)

    def test_validate_detects_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            corpus.init(type("Args", (), {"manifest": manifest})())
            data = corpus.load_manifest(manifest)
            data["letters"][0].update({"format": "html", "source_path": str(root / "1977.html"), "sha256": "not-a-hash"})
            corpus.save_json(manifest, data)
            (root / "1977.html").write_text("<p>fiction</p>", encoding="utf-8")
            args = type("Args", (), {"manifest": manifest, "raw_dir": root / "raw",
                                    "extracted_dir": root / "out", "report": root / "report.json"})()
            with patch("builtins.print"):
                self.assertEqual(corpus.validate(args), 1)
            report = json.loads(args.report.read_text())
            self.assertIn("source hash missing or mismatched", report["letters"][0]["issues"])
            self.assertEqual(report["coverage"]["ready"], 0)

    def test_extract_from_local_fixture_records_hash_and_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            corpus.init(type("Args", (), {"manifest": manifest})())
            data = corpus.load_manifest(manifest)
            data["letters"][0].update({
                "format": "html", "source_path": str(Path(__file__).parent / "fixtures/sample.html"),
            })
            corpus.save_json(manifest, data)
            args = type("Args", (), {"manifest": manifest, "raw_dir": root / "raw",
                                    "extracted_dir": root / "out", "years": [1977]})()
            with patch("builtins.print"):
                corpus.extract(args)
            row = corpus.load_manifest(manifest)["letters"][0]
            output = json.loads((args.extracted_dir / "1977.json").read_text())
            self.assertEqual(row["sha256"], corpus.sha256(Path(row["source_path"])))
            self.assertEqual(output["source_sha256"], row["sha256"])
            self.assertTrue(any(warning.startswith("short_extraction") for warning in output["warnings"]))


if __name__ == "__main__":
    unittest.main()
