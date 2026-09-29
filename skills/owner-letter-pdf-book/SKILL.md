---
name: owner-letter-pdf-book
description: Turn an original Markdown owner-update manuscript into a navigable, readable PDF and verify its text, links, and layout.
---

# Owner letter PDF book

Work from original or licensed Markdown. Keep the source manuscript editable. Preserve semantic headings, table headers, source notes, and meaningful link text so the PDF can be navigated and understood. In the private project repository, run `python3 scripts/build-book.py examples/sample-owner-update --output output/pdf/sample-owner-update.pdf`. For a standalone skill installation, use the project's documented build command or a Markdown-to-PDF tool that supports a table of contents and PDF bookmarks. Do not silently fetch or embed the historical letter corpus.

Check the generated PDF, not just the build exit code. Extract its text to confirm sections, tables, figures, and notes survived. Inspect representative rendered pages, including the cover, contents, a dense table page, and a closing page. Check that bookmarks and internal links point to the expected sections. Fix clipping, orphaned headings, unreadable type, or broken page flow in the manuscript or build styles and rebuild.

Deliver the PDF together with the source Markdown and a reproduction command. State any limitation in link, bookmark, or accessibility verification. The PDF should identify fictional example material as fictional and should not imply Berkshire Hathaway or Warren Buffett endorsement.
