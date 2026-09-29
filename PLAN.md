# Berkshire shareholder letter skills: build plan

## Implementation status (September 2026)

The repository has a local corpus pipeline, a reproducible multi-agent analysis workflow, eight agent skills, a fictional example, and a working PDF build. All 48 letters, per-letter reviews, and synthesis reports live in ignored local storage. Corpus validation and the private full-review validator both report 48/48. The tracked repository contains methodology and original skill instructions, but no source-derived analysis. Public release remains subject to the rights review in `research/rights.md`.

## Goal

Build a repository modeled on `tomdale/inside-mac`: reproducible research, a set of installable agent skills, review rules, examples, and a Markdown-to-PDF book pipeline. The subject is the communication and reasoning techniques in **Warren Buffett's Berkshire Hathaway annual shareholder letters**, not a collection of republished letters or a generator that claims to be Buffett.

The first release should help an agent write and review clear, evidence-backed owner updates about a business. It should also produce a polished, cited example booklet from original text.

## Scope and source boundary

- Primary corpus: the 48 annual letters in Berkshire's Buffett archive, 1977–2024. Treat the year as the fiscal year discussed; separately record the letter's actual publication or signature date when available.
- Exclude 2025 from the Buffett corpus. Berkshire lists it under Greg Abel's letters. Do not silently mix the two authors.
- The official site mentions a book containing 1965–2024 letters. Years 1965–1976 are not in the public Buffett web archive; treat them as a separate, rights-cleared extension, not as missing records to scrape from third-party mirrors.
- Exclude Berkshire annual reports, meeting transcripts, interviews, special letters, and Charlie Munger/Wesco letters from the first research corpus. They may be separate later studies.
- Record format per source (HTML or PDF), canonical archive entry, access date, checksum, extraction method, and any OCR or table quality issues.

## Repository shape

```text
README.md
LICENSE                         # original code and skill prose only
.gitignore                      # corpus files and extracted text
research/
  methodology.md                # selection, sampling, coding, limitations
  source-manifest.json          # URL-free schema scaffold
  analyze.workflow.js           # parallel private analysis and skill synthesis
scripts/
  fetch-sources.*               # explicit opt-in local fetch; rate limited
  extract-text.*                # HTML/PDF normalization and diagnostics
  validate-corpus.*             # year, hash, format, and extraction checks
  build-book.*                  # Markdown to PDF
skills/
  owner-letter-style/SKILL.md   # router and shared contract
  owner-letter-architecture/SKILL.md
  owner-letter-voice/SKILL.md
  owner-letter-performance/SKILL.md
  owner-letter-capital-allocation/SKILL.md
  owner-letter-risk-and-errors/SKILL.md
  owner-letter-review/SKILL.md
  owner-letter-pdf-book/SKILL.md
  owner-letter-style/references/sources.md
examples/
  sample-owner-update/         # wholly original, sourced or fictional and clearly labeled
tests/
  fixtures/                    # small synthetic extraction fixtures
```

The skill names are provisional. Keep each `SKILL.md` short enough to route work, with detailed checklists in references. Use the standard skill frontmatter and document how to copy `skills/` into an agent's skill directory. The PDF skill should work on an ordinary Markdown project, independent of a particular agent runtime.

## Work phases

### 1. Establish rights and publication rules

Read Berkshire's current legal terms and seek written permission or legal review before publicly distributing any source files, extracted text, analysis, substantial excerpts, or source links. Keep the fetched corpus and every source-derived research artifact local and ignored by Git. The distributable package contains only original skill instructions and its license.

**Gate:** a documented decision for what the public repository may contain. A local research workflow may proceed before this gate; public release may not.

### 2. Build the reproducible corpus pipeline

Create a checked manifest for every archive year. Fetch locally only on explicit command, with a descriptive user agent, modest request spacing, retries, and hash recording. Normalize HTML and PDF separately; retain page numbers for PDFs, headings and tables where possible, and original text offsets. Emit diagnostics for replacement characters, missing pages, repeated headers, broken tables, and unexpectedly short extractions. Verify that all 48 years resolve and that output can be regenerated from a clean checkout given authorized source access.

**Gate:** a corpus report lists all years and every extraction warning; manual spot checks include early HTML, a format-transition year, and a recent PDF.

### 3. Analyze communication patterns, not investment prescriptions

Use a written coding rubric across the full set, then close-read a stratified sample spanning decades and changing formats. Track each candidate technique with year, location, context, a paraphrased observation, counterexamples, and a confidence level. Look for: owner audience and candid framing; definitions of the scorecard; separation of reported figures from underlying economics; capital allocation explanations; uncertainty and probabilistic language; mistakes and changed views; time horizon; analogies; business-specific detail; and the placement of tables or calculations. Distinguish recurring techniques from one-off choices and from claims that depend on historical context.

**Gate:** each rule that enters a skill has multiple traceable examples or is explicitly labeled as a limited observation. A reviewer can reproduce the reasoning without accepting a style claim on faith.

### 4. Write the skill package

- **Style/router:** chooses the relevant skill and imposes a common output contract: audience, period, business facts, source ledger, open questions, and review status.
- **Architecture:** annual update structure, reader orientation, key developments, financial context, risk, and outlook.
- **Voice:** plain language, specificity, explanation of terms, useful analogies, and restraint. Do not ask an agent to impersonate Buffett or claim endorsement.
- **Performance:** define metrics, periods, denominators, comparators, and adjustments; distinguish accounting results from economic interpretation.
- **Capital allocation:** explain alternatives, tradeoffs, deployment criteria, and what was learned, without turning historical examples into current investment advice.
- **Risk and errors:** make uncertainty, adverse results, mistakes, and unresolved questions visible.
- **Review:** check factual support, arithmetic, period consistency, omitted bad news, invented quotes, overconfidence, and whether the reader can tell fact from interpretation.
- **PDF book:** compile original Markdown into a navigable, print-quality PDF with contents, running heads, accessible headings, and source notes.

Include positive and negative examples using fictional businesses or authorized public facts. Any example financial data should have a checked calculation and source ledger.

**Gate:** a fresh agent can use only the installed skills to draft and review an owner update without access to the local letter corpus.

### 5. Produce and test an end-to-end example

Write an original multi-section owner update for a clearly fictional company, including a short metric table, one material mistake, an allocation decision, risks, and a reasoned outlook. Run the review skill, record the issues it catches, revise, and build the PDF. Include source Markdown and a reproduction command. Test skill installation, corpus validation, PDF generation, links/bookmarks, text extraction, and visual layout. Run a second cold-start prompt to check that the router picks the right skill and does not fabricate facts.

**Gate:** clean-checkout instructions reproduce the example PDF; the review catches seeded errors in arithmetic, unsupported claims, and year attribution.

### 6. Publish only after the release gate

Write a README that explains purpose, install/use commands, corpus scope, methodology, limits, and non-affiliation. License only original code and prose. Verify the repository contains no source PDFs, extracted letter text, unreviewed quotations, or unapproved links. If rights clearance is incomplete, keep the repository private or publish only the standalone original skills and tooling allowed by review.

## Suggested implementation order

1. Rights note and source manifest schema.
2. Fetch/extract/validate scripts for three representative years, then all 48.
3. Coding rubric and private evidence-backed analysis.
4. Router, voice, architecture, and review skills as the smallest usable set.
5. Remaining specialist skills and example.
6. PDF pipeline, clean-checkout verification, and release review.

## Definition of done

- The corpus coverage and extraction limits are explicit and reproducible.
- Every material skill rule traces to research evidence and is written as an original, portable instruction.
- The package installs as agent skills and successfully drafts, reviews, and renders a complete original example.
- The README states that the project is independent of Berkshire Hathaway and Warren Buffett.
- Public contents pass the documented rights review.

## Research references checked for this plan

- `tomdale/inside-mac` README: skill router, specialist skills, research workflow, ignored local corpus, examples, and PDF pipeline.
- Berkshire Hathaway official Buffett shareholder-letter archive: 1977–2024, with its note about the 1965–2024 book.
- Berkshire Hathaway official Greg Abel shareholder-letter archive: 2025 listed separately.
- Berkshire Hathaway legal disclaimer: explicit restrictions on reproduction, distribution, and linking without written permission.

These references are descriptions for planning. Add URLs to a public repository only after the rights gate above.
