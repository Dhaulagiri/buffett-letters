#!/usr/bin/env python3
"""Build a compact, navigable PDF book from a directory of Markdown chapters.

Requires reportlab. Files are ordered by an optional book.json `chapters` list,
or lexically when no manifest exists. This intentionally supports a small,
documented Markdown subset rather than silently mangling arbitrary Markdown.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import portrait
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, ListFlowable, ListItem, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


PAGE_SIZE = portrait((7.5 * inch, 9.25 * inch))
INK = colors.HexColor("#20262B")
ACCENT = colors.HexColor("#155A64")
MUTED = colors.HexColor("#637078")


def fonts():
    base = Path("/System/Library/Fonts/Supplemental")
    candidates = [
        ("BookSerif", base / "Georgia.ttf"),
        ("BookSerifBold", base / "Georgia Bold.ttf"),
        ("BookSans", base / "Arial.ttf"),
        ("BookSansBold", base / "Arial Bold.ttf"),
    ]
    for name, path in candidates:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont(name, str(path)))
            except Exception:
                pass
    serif = "BookSerif" if "BookSerif" in pdfmetrics.getRegisteredFontNames() else "Times-Roman"
    serif_bold = "BookSerifBold" if "BookSerifBold" in pdfmetrics.getRegisteredFontNames() else "Times-Bold"
    sans = "BookSans" if "BookSans" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
    sans_bold = "BookSansBold" if "BookSansBold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
    pdfmetrics.registerFontFamily(serif, normal=serif, bold=serif_bold)
    pdfmetrics.registerFontFamily(sans, normal=sans, bold=sans_bold)
    return serif, serif_bold, sans, sans_bold


def styles():
    serif, serif_bold, sans, sans_bold = fonts()
    return {
        "title": ParagraphStyle("Title", fontName=serif_bold, fontSize=24, leading=30, textColor=INK, alignment=TA_CENTER, spaceAfter=18),
        "subtitle": ParagraphStyle("Subtitle", fontName=sans, fontSize=10, leading=15, textColor=MUTED, alignment=TA_CENTER, spaceAfter=20),
        "h1": ParagraphStyle("Heading1", fontName=serif_bold, fontSize=18, leading=23, textColor=ACCENT, spaceBefore=18, spaceAfter=12, keepWithNext=True),
        "h2": ParagraphStyle("Heading2", fontName=sans_bold, fontSize=11.5, leading=15, textColor=INK, spaceBefore=16, spaceAfter=7, keepWithNext=True),
        "h3": ParagraphStyle("Heading3", fontName=sans_bold, fontSize=9.5, leading=13, textColor=INK, spaceBefore=12, spaceAfter=5, keepWithNext=True),
        "body": ParagraphStyle("Body", fontName=serif, fontSize=9.4, leading=14.4, textColor=INK, spaceAfter=8),
        "small": ParagraphStyle("Small", fontName=sans, fontSize=8, leading=11, textColor=MUTED, spaceAfter=7),
        "table": ParagraphStyle("Table", fontName=sans, fontSize=8.2, leading=11, textColor=INK),
        "tablehead": ParagraphStyle("TableHead", fontName=sans_bold, fontSize=8.2, leading=11, textColor=INK),
    }


def inline(text):
    """Convert supported inline Markdown after escaping raw HTML."""
    text = escape(html.unescape(text.strip()))
    text = re.sub(r"\[([^\]]+)\]\((https?://[^ )]+)\)", lambda m: f'<link href="{m.group(2)}" color="#155A64">{m.group(1)}</link>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r"<font name=\"Courier\">\1</font>", text)
    return text


def parse_blocks(markdown):
    """Recognize headings, paragraphs, bullets, and simple pipe tables."""
    lines = markdown.replace("\r\n", "\n").splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("#") and re.match(r"^#{1,3} ", line):
            level = len(line) - len(line.lstrip("#"))
            blocks.append((f"h{level}", line[level:].strip()))
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?[ :|\-]+\|?$", lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not re.match(r"^\|?[ :|\-]+\|?$", lines[i].strip()):
                    rows.append([cell.strip() for cell in lines[i].strip().strip("|").split("|")])
                i += 1
            blocks.append(("table", rows))
            continue
        if line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            blocks.append(("bullets", items))
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3} |\||- )", lines[i].strip()):
            paragraph.append(lines[i].strip())
            i += 1
        blocks.append(("body", " ".join(paragraph)))
    return blocks


class BookDoc(BaseDocTemplate):
    def __init__(self, filename, title, **kw):
        super().__init__(filename, pagesize=PAGE_SIZE, leftMargin=.77*inch,
                         rightMargin=.77*inch, topMargin=.82*inch,
                         bottomMargin=.73*inch, title=title, author="Independent research project", **kw)
        self.book_title = title
        self.section = ""
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="normal", frames=[frame], onPage=self.decorate))

    def decorate(self, canvas, doc):
        canvas.saveState()
        _, _, sans, _ = fonts()
        canvas.setStrokeColor(colors.HexColor("#D8E0E2"))
        canvas.line(self.leftMargin, PAGE_SIZE[1] - .55*inch, PAGE_SIZE[0] - self.rightMargin, PAGE_SIZE[1] - .55*inch)
        canvas.setFont(sans, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(self.leftMargin, PAGE_SIZE[1] - .44*inch, self.book_title[:70])
        canvas.drawRightString(PAGE_SIZE[0] - self.rightMargin, .42*inch, str(doc.page))
        canvas.restoreState()

    def beforeDocument(self):
        # multiBuild makes several passes to resolve the table of contents.
        self.section = ""

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and getattr(flowable, "_book_heading", None):
            level, title, key = flowable._book_heading
            self.canv.bookmarkPage(key)
            if level == 1:
                self.section = title
                self.notify("TOCEntry", (0, title, self.page, key))
                self.canv.addOutlineEntry(title, key, level=0)
            elif level == 2:
                self.notify("TOCEntry", (1, title, self.page, key))


def chapter_files(directory):
    manifest = directory / "book.json"
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        names = data.get("chapters") or []
        files = [directory / name for name in names]
        if not files or any(not p.is_file() or p.suffix != ".md" for p in files):
            raise ValueError("book.json chapters must list existing .md files")
        return data, files
    files = sorted(directory.glob("*.md"))
    if not files:
        raise ValueError("No Markdown chapters found")
    return {"title": directory.name.replace("-", " ").title()}, files


def make_story(data, files, st, width):
    title = data.get("title", "Owner update")
    story = [Spacer(1, 1.4*inch), Paragraph(inline(title), st["title"])]
    if data.get("subtitle"):
        story.append(Paragraph(inline(data["subtitle"]), st["subtitle"]))
    if data.get("edition"):
        story.append(Paragraph(inline(data["edition"]), st["subtitle"]))
    story.extend([PageBreak(), Paragraph("Contents", st["h1"])])
    toc = TableOfContents()
    toc.levelStyles = [st["body"], st["small"]]
    story.extend([toc, PageBreak()])
    heading_count = 0
    for index, path in enumerate(files):
        if index:
            story.append(PageBreak())
        blocks = parse_blocks(path.read_text(encoding="utf-8"))
        if not blocks or blocks[0][0] != "h1":
            raise ValueError(f"{path}: each chapter must start with a level-one heading")
        skip_block = -1
        for block_index, (kind, value) in enumerate(blocks):
            if block_index == skip_block:
                continue
            if kind.startswith("h"):
                level = int(kind[1])
                p = Paragraph(inline(value), st[kind])
                heading_count += 1
                p._book_heading = (level, value, f"h-{heading_count}")
                if level > 1 and block_index + 1 < len(blocks) and blocks[block_index + 1][0] == "body":
                    story.append(KeepTogether([p, Paragraph(inline(blocks[block_index + 1][1]), st["body"])]))
                    skip_block = block_index + 1
                else:
                    story.append(p)
            elif kind == "body":
                story.append(KeepTogether([Paragraph(inline(value), st["body"])]))
            elif kind == "bullets":
                story.append(ListFlowable([ListItem(Paragraph(inline(item), st["body"])) for item in value],
                                           bulletType="bullet", leftIndent=14))
            elif kind == "table":
                ncols = len(value[0])
                if any(len(row) != ncols for row in value):
                    raise ValueError(f"{path}: inconsistent table columns")
                cells = [[Paragraph(inline(cell), st["tablehead"] if ri == 0 else st["table"])
                          for cell in row] for ri, row in enumerate(value)]
                table = Table(cells, colWidths=[width/ncols]*ncols, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EAF1F2")),
                    ("LINEBELOW", (0,0), (-1,0), .6, ACCENT),
                    ("LINEBELOW", (0,-1), (-1,-1), .35, colors.HexColor("#CCD5D8")),
                    ("VALIGN", (0,0), (-1,-1), "TOP"),
                    ("LEFTPADDING", (0,0), (-1,-1), 7),
                    ("RIGHTPADDING", (0,0), (-1,-1), 7),
                    ("TOPPADDING", (0,0), (-1,-1), 6),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ]))
                story.extend([Spacer(1, 5), table, Spacer(1, 11)])
    return story


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Directory with book.json and .md chapters")
    parser.add_argument("--output", required=True, type=Path, help="Output PDF path")
    args = parser.parse_args()
    data, files = chapter_files(args.directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    st = styles()
    doc = BookDoc(str(args.output), title=data.get("title", "Owner update"))
    story = make_story(data, files, st, doc.width)
    doc.multiBuild(story)
    print(f"Wrote {args.output} ({len(files)} chapters)")


if __name__ == "__main__":
    main()
