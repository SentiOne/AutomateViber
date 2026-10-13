# Chunker OpenAPI Reference

> Prefer `POST /ingest` for anything RAG- or knowledge-base-bound: it takes only a
> source and decides routing and chunking itself. The older endpoints below expose
> options that are usually better left to the server.

## Authentication

Every conversion and chunking endpoint requires `X-API-Key`. `/status`, `/ui/*`,
`/docs`, `/openapi.json`, `/swagger.yaml` and `/robots.txt` are open. The key also
selects which Azure deployments serve the request, so callers never pass backend
credentials.

The helper reads the key from the OS keychain
(`python -m keyring set sentione-chunker default`), falling back to the
`CHUNKER_API_KEY` environment variable for CI. Obtain the key from your
Chunker administrator.

## `POST /ingest`

Multipart fields, all optional except that at least one source is required:

- `files`: uploads. PDF/DOCX/TXT/HTML/MD/ZIP are converted and chunked; a CSV/XLSX
  with a `content` column is treated as an existing KB export and merged unchanged.
- `urls`: newline- or comma-separated, or a JSON array. A URL whose content type is
  a document (PDF, DOCX, Markdown) is downloaded and converted through the file
  pipeline; anything else is crawled as a page. A bare host gains `https://`.
- `domain`: seed URL; crawls that host breadth-first. Documents linked from those
  pages are fetched and converted, sharing the page cap rather than adding to it.
- `max_pages`, `max_depth`: crawl caps, clamped to the server ceilings.
- `metadata_json`: per-source metadata keyed by filename or URL, e.g.
  `{"report.pdf": {"description": "FY2025"}}`. A bare string is the description.

Returns XLSX with `title`, `url`, `description`, `content`. Counts come back in
`X-Ingest-Documents`, `X-Ingest-Chunks`, `X-Ingest-Crawled-Pages`,
`X-Ingest-Fetched-Documents` and `X-Ingest-Passthrough-Rows`. Oversized requests
are refused with 413 up front rather than timing out.


Source: `https://chunker.chatbots.sentione.com/swagger.yaml`

Retrieved: 2026-08-14

API title/version from spec: `AI Converter` / `1.1.0`

Default service base URL:

```text
https://chunker.chatbots.sentione.com
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/status` | Health/status check. |
| `POST` | `/convert` | Convert uploaded files to Markdown. Multipart form-data. |
| `POST` | `/ingest` | **Recommended.** Files, URLs, a crawled domain and/or already-KB-shaped CSV/XLSX in one call. Returns XLSX. Multipart form-data. |
| `POST` | `/convert-chunk` | Convert uploaded files to Markdown and immediately chunk them. Multipart form-data. |
| `POST` | `/convert-url` | Convert one or more HTTP/HTTPS URLs. JSON body. |
| `POST` | `/convert-text` | Convert raw text to a converted document. JSON body. |
| `POST` | `/chunk` | Chunk a Markdown string. JSON body, optional `output_format` query parameter. |
| `POST` | `/export` | Export chunks as `json` or `csv`. JSON body. |

## Core Request Shapes

### `/convert`

Multipart fields:

- `files`: one or more uploaded files, ZIP allowed
- `title`: optional string
- `url`: optional source URL
- `description`: optional string
- `pdf_strategy`: `auto`, `legacy`, `pymupdf`, `openai`, or `azure_di`; default `auto`
- `pdf_openai_config_json`: JSON string; required when `pdf_strategy=openai`, optional with `auto`
- `pdf_document_intelligence_config_json`: JSON string; optional, falls back to the server's Document Intelligence configuration. With it available, `auto` routes table-dense, scanned and mixed pages to layout analysis.

Response: `ConvertResponse`.

### `/convert-chunk`

Multipart fields:

- all `/convert` fields
- `chunk_format`: `json`, `csv`, or `xlsx`; default `json`
- `strategy`: `by_header` or `semantic`; default `by_header`
- `header_level`: optional integer, used with `by_header`
- `semantic_options_json`: optional JSON string, used with `semantic`

Response: `ConvertAndChunkResponse` for JSON output. Non-JSON formats may return file content.

### `/convert-url`

JSON fields:

- `urls`: required array of HTTP/HTTPS URL strings
- `title`: optional string
- `description`: optional string
- `response_format`: `json`, `csv`, or `xlsx`; default `json`
- `strategy`: `by_header` or `semantic`; default `by_header`
- `header_level`: optional integer
- `semantic_options_json`: optional JSON string

Response: `ConvertResponse` for JSON output. Non-JSON formats may return file content.

### `/convert-text`

JSON fields:

- `filename`: required string
- `ext`: required one of `pdf`, `docx`, `txt`, `html`, `md`
- `text`: required string
- `metadata`: optional `FileMetadata`

Response: `ConvertedDocument`.

### `/chunk`

JSON fields:

- `markdown`: required full Markdown string
- `document_id`: optional stable id for chunk ids
- `metadata`: optional `FileMetadata`
- `strategy`: `by_header` or `semantic`; default `by_header`
- `header_level`: optional integer from 1 to 6
- `semantic_options`: optional object, for example `model`, `max_chars`, `overlap`

Query parameter:

- `output_format`: string, default `json`

Response: `ChunkResponse` for JSON output.

### `/export`

JSON fields:

- `document_id`: optional string
- `chunks`: optional array of `Chunk`
- `format`: `json` or `csv`; default `json`
- `filename`: optional string

Response schema is unspecified in Swagger; treat it as raw response content and write it to a file.

## Core Response Shapes

### `ConvertedDocument`

- `document_id`: string
- `filename`: string
- `ext`: `pdf`, `docx`, `txt`, `html`, or `md`
- `markdown`: string
- `metadata`: `FileMetadata`
- `conversion_diagnostics`: optional object

### `Chunk`

- `chunk_id`: string
- `index`: integer
- `markdown`: string
- `metadata`: optional object

### `ChunkResponse`

- `document_id`: string
- `chunks`: array of `Chunk`
- `stats`: optional object

### `ChunkedDocument`

- `document_id`: string
- `filename`: string
- `ext`: string
- `chunks`: array of `Chunk`
- `chunk_stats`: object
- `metadata`: `FileMetadata`

### `ConvertAndChunkResponse`

- `documents`: array of `ChunkedDocument`
- `stats`: optional object

### `ConvertResponse`

- `documents`: array of `ConvertedDocument`
- `stats`: object

### `FileMetadata`

- `title`: optional string
- `url`: optional URI string
- `description`: optional string
- `source_name`: optional string

## Error Shapes

`400` and `413` errors use:

- `error`: string
- `detail`: optional string

`422` validation errors use FastAPI-style validation detail with `loc`, `msg`, and `type`.
