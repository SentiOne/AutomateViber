---
name: chunker-api
description: Use this skill when preparing RAG or knowledge-base content with the SentiOne Chunker API - converting files, URLs, or a whole domain into Automate-ready chunks, and merging existing knowledge-base exports. Covers the local Chunker helper script and the Automate upload handoff.
---

# Chunker API

Use this skill when source material must be prepared for RAG or knowledge-base
ingestion.

## One command does it

```bash
scripts/chunker ingest docs/handbook.pdf --output output/kb.xlsx
```

`ingest` converts and chunks any mix of sources into a single XLSX with the
`title`, `url`, `description`, `content` columns Automate expects. Combine sources
freely in one call:

```bash
scripts/chunker ingest \
  docs/handbook.pdf docs/faq.docx existing-kb.csv \
  --url https://example.com/help \
  --domain https://docs.example.com/ \
  --output output/kb.xlsx
```

- **Files** — PDF, DOCX, TXT, HTML, MD, ZIP are converted and chunked.
- **`--url`** — repeatable. A web page is fetched and chunked. A URL pointing
  straight at a PDF or DOCX is downloaded and converted instead of scraped, so a
  linked document gets the same treatment as an uploaded one.
- **`--domain`** — crawls that host breadth-first. PDFs and DOCX linked from the
  crawled pages are downloaded and converted too, sharing the page cap rather than
  adding to it. Page and depth caps are enforced by the server; `--max-pages` and
  `--max-depth` may lower them but not exceed them.
- **CSV/XLSX that is already Automate KB shaped** (has a `content` column) is
  merged as-is, without re-chunking, because those rows are chunks someone already
  curated.

**Do not pass chunking or conversion options.** There are none on `ingest`. The
server classifies each PDF page and routes it, picks between header-based and
semantic chunking per document, and resolves backend credentials from the API key.
Choosing these yourself would be guessing at decisions the server makes from the
document itself.

## Authentication

The API requires a key. Store it in the OS keychain, the same way the Automate key
is stored:

```bash
python -m keyring set sentione-chunker default
```

Obtain the key from whoever administers your Chunker deployment and store it
in the OS keychain with the command above.
Never paste a key into a file, a ticket or a chat message.

On CI, where there is no keychain, set `CHUNKER_API_KEY` in the environment
instead — as a masked credential, never as a command-line flag, since flags are
visible in the process list. A stored keychain entry takes precedence, so a
leftover `export` cannot silently shadow it.

Avoid typing `export CHUNKER_API_KEY=...` at an interactive prompt: the whole line
lands in your shell history.

The key also determines which conversion backends serve the request, so no Azure
or OpenAI credentials are ever passed by the caller. A missing or rejected key
gives HTTP 401, and the helper prints how to fix it.

## Then upload to Automate

```bash
scripts/automate knowledge documents upsert <document-key> output/kb.xlsx
```

See [automate-api](../automate-api/SKILL.md). The document key is Automate's
identity for the document; re-upserting the same key replaces its content.

## Metadata

Titles and URLs are derived, so leave them alone:

- **`title`** comes from the document's own first heading, falling back to the
  filename.
- **`url`** is only ever real. Anything reached by URL carries it, a PDF downloaded
  from a link included; an uploaded file leaves the cell empty, because a filename
  is not something a reader can follow.
- **`description`** is empty unless you supply it. Nothing is generated - an
  invented summary is worse than a blank cell.

Add a description per source when it is genuinely useful:

```bash
scripts/chunker ingest docs/handbook.pdf \
  --describe "docs/handbook.pdf=Employee handbook, 2026 edition" \
  --output output/kb.xlsx
```

`--describe` accepts the path you typed or a URL. A name matching no source in the
request is an error, so a typo will not pass silently.

## Verification

`ingest` prints the counts to stderr, e.g.
`ingested: chunks=48, crawled-pages=12, documents=5, fetched-documents=3, passthrough-rows=2`.
`fetched-documents` counts URLs that turned out to be documents rather than pages.

Before uploading, confirm:

- the XLSX exists, is non-empty, and has the four expected columns
- the document count matches the sources you passed
- `crawled-pages` looks sane for a `--domain` run - hitting the cap exactly may mean
  the crawl was truncated
- spot-check a few `content` cells: chunks should not begin or end mid-sentence, and
  a table should not be split across rows
- `url` is populated for anything fetched by URL — pages and downloaded documents
  alike — and empty for uploaded files
- no secrets appear anywhere in the output

If chunk boundaries are poor, or a PDF's tables come out mangled, that is a Chunker
issue to report - not something to patch locally. Include the source document and
the observed output.

## Older endpoints

`ingest` replaces the usual reasons for calling these directly. They remain for
narrower jobs:

| Command | Use when |
| --- | --- |
| `rechunk-csv` (API) | An existing chunk CSV must be **re-chunked**, not merged as-is |
| `chunk` | Markdown already exists and only needs splitting |
| `convert` | Markdown output is wanted without chunking |
| `export` | Chunks exist and only need reserialising |

`scripts/chunker --help` lists them. They expose conversion and chunking options;
prefer `ingest` unless one of the cases above applies.

## Safety

- Never paste API keys into chat, command flags, or committed files.
- `--domain` crawls a live site. Confirm the target with the user first, and keep
  the caps low on a first run.
- Treat generated chunks as draft content. Knowledge-base upserts are destructive:
  they replace the document under that key.
