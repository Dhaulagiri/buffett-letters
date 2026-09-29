# Research methodology

## Question and scope

This project studies how Warren Buffett's Berkshire Hathaway annual shareholder letters communicate business performance, choices, uncertainty, and mistakes. It turns observed communication techniques into portable instructions for an original owner update. It does not provide investment advice, recreate a letter, or impersonate its author.

The official Berkshire archive lists 48 fiscal years, 1977 through 2024. The archive labels the years discussed, not necessarily the dates on which letters were published. Record publication dates separately only when established from the source. The 2025 letter belongs to a separate Greg Abel archive and is outside this corpus. Berkshire mentions a book covering 1965–2024; the 1965–1976 letters are outside the linked web archive and outside this release.

The archive includes HTML and PDF letters. The 2001 archive entry is a choice page with distinct HTML and PDF versions, rather than letter text itself. Resolve the chosen version and record it in the private manifest. Do not assume all archive links are direct letters or infer format from year alone.

## Collection and provenance

The tracked `source-manifest.json` is a 48-year schema scaffold. It contains no source URLs or letter text. A local fetch creates the ignored private manifest and corpus. For each source, record the year, author, format, source path and URL, access time, SHA-256 digest, extraction method, and quality issues. Repeated fetches should compare hashes and flag changed content for review. An archive entry proves availability, not successful extraction or complete authorship attribution within a PDF.

Collect only with the explicit local command in the README. Keep a modest request pace and inspect Berkshire's current terms before fetching. Preserve source bytes locally but out of Git. For PDFs, retain page boundaries and check tables manually; for HTML, preserve heading boundaries and watch character encoding. Never silently treat a short or garbled extraction as complete.

## Coding rubric

For each candidate technique, record a source ID (`B-YYYY`), a location (heading for HTML, page for PDF), a paraphrased observation, its business context, and whether it is fact, interpretation, or a proposal for general writing. Code these dimensions:

1. Who the owner is and what the writer owes that reader.
2. The scorecard: metric definition, period, denominator, comparator, and limits.
3. How the writer separates reported figures from an economic interpretation.
4. Capital allocation: alternatives, tradeoffs, cost, dilution, and opportunity cost.
5. Acknowledgment of adverse results, mistakes, and corrective action.
6. Uncertainty, forecast limits, and time horizon.
7. Concrete business detail, explanation of terms, analogies, and tables.

A high-confidence, transferable rule requires corroboration in at least two distinct years and should survive a search for counterexamples. A single-year observation is labeled limited. A recommendation for a modern writer is a design inference, even when historical examples support it. Record exceptions and changing reporting conventions instead of flattening the archive into one timeless formula.

## Review coverage and current status

All 48 letters were fetched and extracted into ignored local storage. Each letter was divided into indexed text chunks, every indexed chunk was read, and one private structured record was produced per year with source hash, segment and chunk coverage, located findings, counterexamples, and extraction issues. `python3 scripts/analyze.py validate-full` reports 48/48 records consistent with the prepared jobs and source hashes. None of those records is tracked.

This is a complete review of the extracted text, not a claim that extraction reproduced every visual feature or that multiple reviewers independently agreed on every code. The records contain 292 findings, 109 counterexamples, and 40 extraction notes. They support qualitative corroboration and boundary testing; they do not support statistical frequency claims. Tables, appended material, and mixed authorship need source-level checks before fine-grained attribution. The parser recognizes the 1999 spanning table caption, but that table's column headings remain fragmented in extraction.

## Reproduction and review

Run the local corpus commands and validation described in the README. `scripts/analyze.py prepare` creates private extracted-text jobs. `research/analyze.workflow.js` runs parallel per-letter review, private era consolidation, and skill synthesis. `scripts/analyze.py validate-full` checks private structured records against their sources and chunk indexes. Manually inspect at least one early HTML letter, the 2001 HTML/PDF versions, and a recent PDF. When applying the resulting skills, validate facts against the writer's own source ledger; historical letters provide writing examples, not evidence about another business.

See `rights.md` for the release boundary. No tracked file should include fetched source bytes, extracted text, source-derived analysis, substantial quotations, or source links before rights review.
