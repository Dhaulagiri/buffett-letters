// Reproduce the private full-corpus analysis that informs the owner-letter skills.
// Runs with pi-dynamic-workflows or another runner providing
// agent(), parallel(), phase(), log(), and args.
//
// Optional:
//   args.years      array of fiscal years (defaults to 1977–2024)
//   args.jobs       absolute path to prepared jobs
//   args.privateOut absolute path under .local for private reports
//   args.out        absolute path for generated candidate skills
//
// With no arguments, all inputs and outputs use ignored .local directories
// beneath the current repository.
//
// Every source-derived artifact is written beneath args.privateOut.
// Only original skill instructions are written beneath args.out.

export const meta = {
  name: 'owner_letter_style_analysis',
  description: 'Privately analyze annual shareholder letters and synthesize owner-letter skills',
  phases: [{ title: 'Analyze' }, { title: 'Consolidate' }, { title: 'Synthesize' }],
};

const allYears = Array.from({ length: 48 }, (_, index) => 1977 + index);
const years = args.years ?? allYears;
const root = String(process.cwd()).replace(/\/$/, '');
const jobs = String(args.jobs ?? `${root}/.local/analysis-jobs`);
const privateOut = String(args.privateOut ?? `${root}/.local/workflow-run`);
const skillOut = String(args.out ?? `${root}/.local/generated-skills`);

if (!jobs.startsWith('/') || !privateOut.startsWith('/') || !skillOut.startsWith('/')) {
  throw new Error('args.jobs, args.privateOut, and args.out must be absolute paths');
}
if (!privateOut.split('/').includes('.local')) {
  throw new Error('args.privateOut must be inside an ignored .local directory');
}
if (!years.length || years.some((year) => !allYears.includes(year))) {
  throw new Error('args.years must contain fiscal years from 1977 through 2024');
}

const reviewSchema = {
  type: 'object',
  required: [
    'schema_version',
    'year',
    'format',
    'source_sha256',
    'segment_count',
    'chunk_count',
    'chunks_reviewed',
    'review_scope',
    'findings',
    'counterexamples',
    'extraction_issues',
  ],
  properties: {
    schema_version: { type: 'integer', const: 1 },
    year: { type: 'integer' },
    format: { type: 'string' },
    source_sha256: { type: 'string' },
    segment_count: { type: 'integer' },
    chunk_count: { type: 'integer' },
    chunks_reviewed: { type: 'array', items: { type: 'integer' } },
    review_scope: { type: 'string', const: 'all extracted chunks read' },
    findings: {
      type: 'array',
      minItems: 3,
      items: {
        type: 'object',
        required: ['topic', 'location', 'paraphrase', 'confidence'],
        properties: {
          topic: { type: 'string' },
          location: { type: 'string' },
          paraphrase: { type: 'string' },
          confidence: { type: 'string' },
        },
      },
    },
    counterexamples: {
      type: 'array',
      items: {
        type: 'object',
        required: ['topic', 'location', 'paraphrase'],
        properties: {
          topic: { type: 'string' },
          location: { type: 'string' },
          paraphrase: { type: 'string' },
        },
      },
    },
    extraction_issues: {
      type: 'array',
      items: { type: 'string' },
    },
  },
};

const lens = `Analyze B-YEAR as historical evidence about communication with business owners.
The private reading job is in JOB. Read index.json and EVERY part file listed there. Do not skip or sample parts.

Study owner orientation, scorecard definitions and limits, reported versus underlying economics, capital allocation, adverse results and mistakes, uncertainty and horizon, concrete operating explanation, architecture, and voice. Record material counterexamples that should prevent rigid style rules.

Paraphrase throughout. Do not reproduce source sentences, distinctive phrases, URLs, or investment recommendations. Distinguish the principal author's writing from appendices and guest material.

Use the job metadata to set schema_version to 1, year, format, source_sha256, segment_count, and chunk_count. Set chunks_reviewed to every part number in ascending order and review_scope to exactly "all extracted chunks read". Record extraction or attribution limits in extraction_issues.

Before returning, create PRIVATE if needed and write the same JSON object to PRIVATE/B-YEAR.json. This private file must contain the complete review and no source quotations or URLs.`;

phase('Analyze');
const reports = await parallel(
  years.map((year) => () =>
    agent(
      lens
        .replaceAll('YEAR', String(year))
        .replace('JOB', `${jobs}/B-${year}`)
        .replaceAll('PRIVATE', privateOut),
      { label: `analyze B-${year}`, tier: 'small', schema: reviewSchema },
    ),
  ),
);

const complete = reports.filter(Boolean);
log(`${complete.length}/${years.length} letter reports completed`);
if (complete.length !== years.length) {
  throw new Error(`Missing ${years.length - complete.length} letter reports; synthesis stopped`);
}

const eras = [
  [1977, 1988],
  [1989, 2000],
  [2001, 2012],
  [2013, 2024],
].map(([first, last]) => ({
  first,
  last,
  reports: complete.filter((report) => report.year >= first && report.year <= last),
}));

phase('Consolidate');
const eraReports = await parallel(
  eras.map((era) => () =>
    agent(
      `Consolidate these private reviews for B-${era.first} through B-${era.last}.
Identify recurring techniques, material counterexamples, changing conventions, and extraction or attribution limits. Separate evidence from proposed modern writing guidance. Do not quote source text or include URLs.

Write the complete private consolidation to ${privateOut}/era-${era.first}-${era.last}.md before returning the same text. Keep it under 1,200 words.

PRIVATE REVIEWS:
${era.reports.map((report) => JSON.stringify(report)).join('\n\n')}`,
      { label: `consolidate ${era.first}-${era.last}`, tier: 'small' },
    ).then((report) => ({ era: `${era.first}-${era.last}`, report })),
  ),
);

phase('Synthesize');
const synthesis = await agent(
  `Use these four private era analyses to create an original, portable agent-skill package for annual owner communication.

Write exactly these skill folders under ${skillOut}, each with a SKILL.md:
- owner-letter-style
- owner-letter-architecture
- owner-letter-voice
- owner-letter-performance
- owner-letter-capital-allocation
- owner-letter-risk-and-errors
- owner-letter-review
- owner-letter-pdf-book

The router may also contain references/sources.md, but that file may describe only research scope, method, limits, non-affiliation, and the private-source boundary. Do not include year-by-year evidence, source locations, quotations, source links, or analysis reports anywhere in the skill output.

Use YAML frontmatter with name and a description saying when to use the skill. Make instructions dense, imperative, and useful without access to the corpus. Preserve counterexamples: no fixed architecture, permanent metric, mandatory brevity, manufactured candor, or Buffett impersonation. Require a source ledger for the user's business and distinguish facts, interpretation, and forecasts. The PDF skill must work independently of this workflow.

This is synthesis, not imitation. Use original prose. Do not reproduce source sentences, distinctive phrases, anecdotes, or investment advice. Do not claim endorsement.

Write a private explanation of the synthesis decisions to ${privateOut}/synthesis-report.md. Return a concise completion report after all skill files and the private report are written.

PRIVATE ERA ANALYSES:
${eraReports.map(({ era, report }) => `### ${era}\n${report}`).join('\n\n')}`,
  { label: 'synthesize owner-letter skills', tier: 'big' },
);

return {
  reports: complete.length,
  eras: eraReports.length,
  privateOut,
  skillOut,
  synthesis,
};
