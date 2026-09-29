# Owner letter skills

An independent research and agent-skill project about clear annual communication with business owners. Inspired by the repository structure of `tomdale/inside-mac`, it contains a reproducible private research workflow, eight installable skills, an original fictional example, and a PDF book builder. It is **not affiliated with or endorsed by Berkshire Hathaway or Warren Buffett**. The skills do not ask an agent to impersonate either party or give investment advice.

## What is here

- `research/`: the reproducible agent workflow, methodology, a URL-free manifest scaffold, and the rights boundary. It contains no source-derived analysis.
- `scripts/corpus.py`: initialize a private manifest, optionally fetch authorized sources, extract text, and validate coverage and quality.
- `skills/`: a router plus architecture, voice, performance, capital allocation, risk, review, and PDF skills. Copy the folders into your agent's skills directory or point your agent at this repo's `skills/` directory.
- `examples/sample-owner-update/`: an original fictional letter with a calculation ledger.
- `scripts/build-book.py` and `output/pdf/sample-owner-update.pdf`: a repeatable example book build and its result.

The 48 entries correspond to fiscal years 1977–2024 in Berkshire's Buffett shareholder-letter archive. The 2025 letter is outside this corpus. This workspace has all 48 source files, extracted letters, per-letter reviews, and synthesis reports in ignored `.local/` files. Corpus and private-review validation both report 48/48. The validators prove provenance and coverage metadata, not independent coder agreement or perfect extraction. See `research/methodology.md` for the method and limits. The repository and skill ZIP intentionally omit the source-derived analyses.

## Use the skills

Copy `skills/owner-letter-*` directories to an agent's skills folder (for example, a project `.agents/skills/` directory), then ask:

> Use owner-letter-style to draft an annual update for our owners from these statements and operating notes. List any unsupported claims, then run owner-letter-review.

Give the agent the business facts and their sources. It should keep a claim/source ledger, identify assumptions, and avoid filling gaps with invented facts. For a narrow task, use a specialist skill directly, such as `owner-letter-performance` or `owner-letter-review`.

To create the **skill-only distribution** from this private workspace, run:

```sh
python3 scripts/package-skills.py
```

The resulting `output/owner-letter-skills.zip` contains only the eight skill folders and `LICENSE`. The command rejects external URLs, letter-level source IDs, and unexpected files inside `skills/`. It excludes the corpus, analysis, examples, scripts, private source ledger, and generated PDFs. Inspect the ZIP before distributing it; packaging is a content boundary, not legal clearance.

## Reproduce the local research pipeline

Python 3.10+ is required. Install `requirements.txt` for PDF extraction and book building; HTML-only corpus commands use the standard library. The commands below create ignored files under `.local/`; they do not fetch anything until the explicit fetch command. Read `research/rights.md` and assess your authorization before supplying sources or running a fetch. The public manifest deliberately contains no URLs.

```sh
python3 -m pip install -r requirements.txt
```

```sh
python3 scripts/corpus.py init
# Edit .local/source-manifest.json with authorized source_url or source_path and format.
python3 scripts/corpus.py fetch --allow-network  # only for authorized network sources
python3 scripts/corpus.py extract
python3 scripts/corpus.py validate
```

`extract` processes locally available source files. PDF extraction uses Poppler `pdftotext` when available and otherwise falls back to `pypdf` from `requirements.txt`; see diagnostics for quality information. Validation reports missing years and extraction warnings rather than treating partial coverage as complete. The full corpus is not bundled, and a clean checkout will not pass full-corpus validation until authorized sources are supplied. See `python3 scripts/corpus.py --help` for options.

Run the synthetic pipeline checks with:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/audit-release.py
```

`python3 scripts/analyze.py prepare --compact` makes ignored reading jobs under `.local/analysis-jobs/`. Then run [`research/analyze.workflow.js`](research/analyze.workflow.js) with a workflow runner that provides `agent()`, `parallel()`, `phase()`, and `log()`, such as `pi-dynamic-workflows`. Pass three absolute paths:

- `args.jobs`: `.local/analysis-jobs`
- `args.privateOut`: an output directory under `.local/`, such as `.local/workflow-run`
- `args.out`: a candidate skill directory, preferably `.local/generated-skills` for review

The workflow sends one small-model agent to every letter, consolidates four eras in parallel, and sends those private summaries to one large-model synthesis agent. All per-letter reports, era reports, and synthesis notes go to `args.privateOut`. Only original candidate skill instructions go to `args.out`. Review the candidate skills before copying them into `skills/`.

One concrete local setup uses Pi and the Dynamic Workflows runner that supports the workflow's `small` and `big` model tiers:

```sh
npm install -g @mariozechner/pi-coding-agent
pi install npm:@quintinshaw/pi-dynamic-workflows
cd /absolute/path/to/buffett-letters
pi
```

Authenticate with `/login` if needed. In Pi, run the following, replacing the repository prefix if your checkout is elsewhere:

```text
/workflows run Read /absolute/path/to/buffett-letters/research/analyze.workflow.js and invoke the workflow tool with that file's exact JavaScript as the script. Pass this args object: {"jobs":"/absolute/path/to/buffett-letters/.local/analysis-jobs","privateOut":"/absolute/path/to/buffett-letters/.local/workflow-run","out":"/absolute/path/to/buffett-letters/.local/generated-skills"}. Keep all analysis and synthesis rationale under privateOut. Do not copy candidate skills into the tracked skills directory.
```

The runner accepts workflow source through its tool rather than executing this file with `node`. After completion, validate the new per-letter records and inspect the generated skills:

```sh
python3 scripts/analyze.py validate-full --analyses .local/workflow-run
diff -ru skills .local/generated-skills
python3 scripts/audit-release.py
```

`python3 scripts/analyze.py validate-full` checks the existing private review records against source hashes and prepared chunk coverage; it cannot certify reading quality. `python3 scripts/index-corpus.py` creates a private navigation index. Neither command writes analysis into Git.

## Build the example PDF

The builder accepts a directory with `book.json` and ordered Markdown chapters. It supports headings, paragraphs, bullets, simple pipe tables, bold/italic/code spans, and web links. It generates a contents page, PDF bookmarks, running heads, and page numbers. It intentionally rejects some malformed input rather than claiming to be a full CommonMark renderer.

```sh
python3 scripts/build-book.py examples/sample-owner-update --output output/pdf/sample-owner-update.pdf
```

This requires Python `reportlab` from `requirements.txt`. In Codex Desktop, the bundled workspace Python already includes it. The generated PDF is an example of the tooling, not a publication of Berkshire material. Check extracted text and rendered pages when adapting the builder for a new manuscript. The PDF has bookmarks but is not a tagged PDF; accessibility requirements beyond readable layout and extractable text need a separate production workflow.

A real-company illustration based on NVIDIA's FY2026 filing is kept under ignored `.local/examples/nvidia-fy2026/` with its own source notes and PDF. It is an independent model letter, not a NVIDIA communication, and is excluded from the skill-only ZIP.

## Release status

The code, skills, methodology, and fictional example are original. Berkshire's site states restrictions on reproduction, distribution, and linking. The fetched corpus, extracted text, analysis, synthesis reports, and private URLs are Git ignored. **Rights review is pending**, so this repository has not been cleared for public publication. A local build or passing test does not change that status. See `research/rights.md` before distributing the repository or generated files.

The original code and prose in this repository are offered under the MIT License in `LICENSE`; that license does not cover any third-party source material obtained separately.
