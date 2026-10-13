#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any


DEFAULT_BASE_URL = "https://chunker.chatbots.sentione.com"
API_KEY_ENV = "CHUNKER_API_KEY"
KEYRING_SERVICE = "sentione-chunker"
KEYRING_USERNAME = "default"

_KEY_CACHE: tuple[str, str] | None = None


class CliError(RuntimeError):
    pass


def _key_from_keyring() -> str:
    """The key from the OS keychain, or empty if it cannot be read.

    keyring is optional here on purpose: this CLI is otherwise stdlib-only and has
    to keep working on a bare CI runner, where there is no keychain and no reason
    to install one. Every failure therefore falls through to the environment
    rather than raising.
    """
    try:
        import keyring
        from keyring.errors import KeyringError
    except ImportError:
        return ""

    try:
        return (keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) or "").strip()
    except KeyringError:
        return ""


def load_api_key() -> tuple[str, str]:
    """Return (key, source). The keychain wins over the environment.

    The keychain is this repo's convention for API keys (see README) and keeps the
    key out of shell history, out of dotfiles and out of the process environment
    that every child process inherits. The environment variable stays supported
    because CI has no keychain -- but it does not override a stored key, so a
    forgotten `export` in a shell profile cannot silently shadow it.

    Cached: on macOS each keychain read can prompt, and one command may make
    several requests.
    """
    global _KEY_CACHE
    if _KEY_CACHE is None:
        key = _key_from_keyring()
        if key:
            _KEY_CACHE = (key, "keychain")
        else:
            _KEY_CACHE = (os.environ.get(API_KEY_ENV, "").strip(), API_KEY_ENV)
    return _KEY_CACHE


def api_key_headers() -> dict[str, str]:
    """Auth header for every request.

    Deliberately not a command-line flag: flags end up in shell history and in the
    process list, and the key selects which paid conversion backends serve the
    request.
    """
    key, _source = load_api_key()
    return {"X-API-Key": key} if key else {}


def missing_key_hint() -> str:
    """What to do about a 401. Never prints the key itself."""
    key, source = load_api_key()
    if key:
        return (
            f"A key was sent (from {source}) but the server rejected it. "
            "Check it is the current key for this deployment."
        )
    return (
        "No API key found. Store it in the OS keychain (preferred):\n"
        f"  python -m keyring set {KEYRING_SERVICE} {KEYRING_USERNAME}\n"
        f"or, on CI only, set {API_KEY_ENV} in the environment (never as a flag).\n"
        "Ask your Chunker administrator for a key."
    )


def normalize_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    if not base_url:
        raise CliError("Base URL cannot be empty.")
    return base_url


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CliError(f"Cannot read file: {path}\n{exc}") from exc


def load_json_arg(value: str | None, *, label: str) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise CliError(f"{label} is not valid JSON: {exc}") from exc


def load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CliError(f"Cannot read JSON file: {path}\n{exc}") from exc
    except json.JSONDecodeError as exc:
        raise CliError(f"JSON file is not valid: {path}\n{exc}") from exc


def request(
    method: str,
    base_url: str,
    path: str,
    *,
    query: dict[str, str] | None = None,
    json_body: Any | None = None,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    url = normalize_base_url(base_url) + path
    if query:
        url += "?" + urllib.parse.urlencode(query)

    request_headers = api_key_headers()
    request_headers.update(headers or {})
    data = body
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        error_body = exc.read()
        detail = decode_error_body(error_body)
        if exc.code == 401:
            detail += f"\n\n{missing_key_hint()}"
        raise CliError(f"HTTP {exc.code} from {path}\n{detail}") from exc
    except urllib.error.URLError as exc:
        raise CliError(f"Request failed for {url}\n{exc}") from exc


def decode_error_body(body: bytes) -> str:
    if not body:
        return "No response body."
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return body.decode("utf-8", errors="replace")
    return json.dumps(parsed, ensure_ascii=False, indent=2)


def encode_multipart(
    *,
    files: list[Path],
    fields: dict[str, str | None],
) -> tuple[bytes, str]:
    boundary = "----chunker-" + uuid.uuid4().hex
    chunks: list[bytes] = []

    for name, value in fields.items():
        if value is None:
            continue
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")

    for file_path in files:
        if not file_path.is_file():
            raise CliError(f"File does not exist or is not a regular file: {file_path}")
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        try:
            file_bytes = file_path.read_bytes()
        except OSError as exc:
            raise CliError(f"Cannot read file: {file_path}\n{exc}") from exc

        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        disposition = f'Content-Disposition: form-data; name="files"; filename="{file_path.name}"\r\n'
        chunks.append(disposition.encode("utf-8"))
        chunks.append(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
        chunks.append(file_bytes)
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def parse_response_body(headers: dict[str, str], body: bytes) -> Any | bytes:
    content_type = ""
    for key, value in headers.items():
        if key.lower() == "content-type":
            content_type = value.lower()
            break

    if "json" in content_type:
        return json.loads(body.decode("utf-8"))
    return body


def write_response(headers: dict[str, str], body: bytes, output: Path | None) -> None:
    parsed = parse_response_body(headers, body)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(parsed, bytes):
            output.write_bytes(parsed)
        else:
            output.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(output)
        return

    if isinstance(parsed, bytes):
        try:
            sys.stdout.write(parsed.decode("utf-8"))
        except UnicodeDecodeError:
            sys.stdout.buffer.write(parsed)
    else:
        print(json.dumps(parsed, ensure_ascii=False, indent=2))


def metadata_from_args(args: argparse.Namespace) -> dict[str, Any] | None:
    metadata = load_json_arg(getattr(args, "metadata_json", None), label="--metadata-json")
    if metadata is not None:
        if not isinstance(metadata, dict):
            raise CliError("--metadata-json must be a JSON object.")
        return metadata

    result: dict[str, Any] = {}
    for key in ("title", "url", "description", "source_name"):
        value = getattr(args, key, None)
        if value:
            result[key] = value
    return result or None


def pdf_openai_config(args: argparse.Namespace) -> str | None:
    config_path = getattr(args, "pdf_openai_config_file", None)
    if config_path is None:
        return None
    return read_text(config_path)


def ingest_metadata(args: argparse.Namespace) -> str | None:
    """Build the per-source metadata map from --describe NAME=TEXT pairs.

    Users naturally name a file by the path they typed, but multipart sends only the
    basename, which is what the server matches on. Translate paths to basenames here
    rather than making the caller know that.
    """
    if args.metadata_json:
        return args.metadata_json
    if not args.describe:
        return None
    by_basename = {str(path): path.name for path in args.files}
    mapping: dict[str, str] = {}
    for item in args.describe:
        name, _, text = item.partition("=")
        name, text = name.strip(), text.strip()
        if not name or not text:
            raise CliError(
                f"--describe expects NAME=TEXT (filename or URL, then a description): {item!r}"
            )
        mapping[by_basename.get(name, name)] = text
    return json.dumps(mapping, ensure_ascii=False)


def command_ingest(args: argparse.Namespace) -> None:
    if not args.files and not args.url and not args.domain:
        raise CliError("Provide at least one source: FILES, --url, or --domain.")
    fields = {
        "urls": "\n".join(args.url) if args.url else None,
        "domain": args.domain,
        "max_pages": str(args.max_pages) if args.max_pages is not None else None,
        "max_depth": str(args.max_depth) if args.max_depth is not None else None,
        "metadata_json": ingest_metadata(args),
    }
    body, boundary = encode_multipart(files=args.files, fields=fields)
    _, headers, response_body = request(
        "POST",
        args.base_url,
        "/ingest",
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    counts = {
        key.lower().replace("x-ingest-", ""): value
        for key, value in headers.items()
        if key.lower().startswith("x-ingest-")
    }
    if counts:
        summary = ", ".join(f"{name}={value}" for name, value in sorted(counts.items()))
        print(f"ingested: {summary}", file=sys.stderr)
    write_response(headers, response_body, args.output)


def command_status(args: argparse.Namespace) -> None:
    _, headers, body = request("GET", args.base_url, "/status")
    write_response(headers, body, args.output)


def command_convert(args: argparse.Namespace) -> None:
    fields = {
        "title": args.title,
        "url": args.url,
        "description": args.description,
        "pdf_strategy": args.pdf_strategy,
        "pdf_openai_config_json": pdf_openai_config(args),
    }
    body, boundary = encode_multipart(files=args.files, fields=fields)
    _, headers, response_body = request(
        "POST",
        args.base_url,
        "/convert",
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    write_response(headers, response_body, args.output)


def command_convert_chunk(args: argparse.Namespace) -> None:
    fields = {
        "title": args.title,
        "url": args.url,
        "description": args.description,
        "pdf_strategy": args.pdf_strategy,
        "pdf_openai_config_json": pdf_openai_config(args),
        "chunk_format": args.chunk_format,
        "strategy": args.strategy,
        "header_level": str(args.header_level) if args.header_level is not None else None,
        "semantic_options_json": args.semantic_options_json,
    }
    body, boundary = encode_multipart(files=args.files, fields=fields)
    _, headers, response_body = request(
        "POST",
        args.base_url,
        "/convert-chunk",
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    write_response(headers, response_body, args.output)


def command_convert_url(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {
        "urls": args.urls,
        "response_format": args.response_format,
        "strategy": args.strategy,
    }
    for key in ("title", "description", "header_level", "semantic_options_json"):
        value = getattr(args, key)
        if value is not None:
            payload[key] = value

    _, headers, body = request("POST", args.base_url, "/convert-url", json_body=payload)
    write_response(headers, body, args.output)


def command_convert_text(args: argparse.Namespace) -> None:
    text = args.text if args.text is not None else read_text(args.input)
    payload: dict[str, Any] = {
        "filename": args.filename,
        "ext": args.ext,
        "text": text,
    }
    metadata = metadata_from_args(args)
    if metadata is not None:
        payload["metadata"] = metadata

    _, headers, body = request("POST", args.base_url, "/convert-text", json_body=payload)
    write_response(headers, body, args.output)


def command_chunk(args: argparse.Namespace) -> None:
    markdown = args.markdown if args.markdown is not None else read_text(args.markdown_file)
    payload: dict[str, Any] = {
        "markdown": markdown,
        "strategy": args.strategy,
    }
    if args.document_id is not None:
        payload["document_id"] = args.document_id
    if args.header_level is not None:
        payload["header_level"] = args.header_level

    metadata = metadata_from_args(args)
    if metadata is not None:
        payload["metadata"] = metadata

    semantic_options = load_json_arg(args.semantic_options_json, label="--semantic-options-json")
    if semantic_options is not None:
        if not isinstance(semantic_options, dict):
            raise CliError("--semantic-options-json must be a JSON object.")
        payload["semantic_options"] = semantic_options

    _, headers, body = request(
        "POST",
        args.base_url,
        "/chunk",
        query={"output_format": args.output_format},
        json_body=payload,
    )
    write_response(headers, body, args.output)


def extract_chunks(data: Any) -> tuple[str | None, list[dict[str, Any]]]:
    if isinstance(data, list):
        return None, data
    if not isinstance(data, dict):
        raise CliError("Chunks file must contain a JSON object or array.")

    if isinstance(data.get("chunks"), list):
        return data.get("document_id"), data["chunks"]

    documents = data.get("documents")
    if isinstance(documents, list):
        chunks: list[dict[str, Any]] = []
        document_ids: list[str] = []
        for document in documents:
            if not isinstance(document, dict):
                continue
            if isinstance(document.get("document_id"), str):
                document_ids.append(document["document_id"])
            if isinstance(document.get("chunks"), list):
                chunks.extend(document["chunks"])
        return ",".join(document_ids) if document_ids else None, chunks

    raise CliError("Could not find `chunks` or `documents[].chunks` in chunks file.")


def command_export(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {
        "format": args.format,
    }
    if args.filename is not None:
        payload["filename"] = args.filename

    if args.chunks_file is not None:
        document_id, chunks = extract_chunks(load_json_file(args.chunks_file))
        payload["chunks"] = chunks
        payload["document_id"] = args.document_id or document_id
    elif args.document_id is not None:
        payload["document_id"] = args.document_id

    _, headers, body = request("POST", args.base_url, "/export", json_body=payload)
    write_response(headers, body, args.output)


def add_common(parser: argparse.ArgumentParser, *, defaults: bool = True) -> None:
    base_url_kwargs: dict[str, Any] = {
        "help": f"Chunker base URL. Default: {DEFAULT_BASE_URL}",
    }
    output_kwargs: dict[str, Any] = {
        "type": Path,
        "help": "Write response to this path instead of stdout.",
    }
    if defaults:
        base_url_kwargs["default"] = DEFAULT_BASE_URL
    else:
        base_url_kwargs["default"] = argparse.SUPPRESS
        output_kwargs["default"] = argparse.SUPPRESS

    parser.add_argument("--base-url", **base_url_kwargs)
    parser.add_argument("--output", **output_kwargs)


def add_metadata_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--metadata-json", help="Metadata JSON object. Overrides individual metadata flags.")
    parser.add_argument("--title")
    parser.add_argument("--url")
    parser.add_argument("--description")
    parser.add_argument("--source-name")


def add_pdf_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pdf-strategy", default="auto", choices=["auto", "legacy", "pymupdf", "openai"])
    parser.add_argument("--pdf-openai-config-file", type=Path, help="Read pdf_openai_config_json from a local JSON file.")


def add_chunk_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--strategy", default="by_header", choices=["by_header", "semantic"])
    parser.add_argument("--header-level", type=int)
    parser.add_argument("--semantic-options-json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Use the SentiOne Chunker API.")
    add_common(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Recommended. Convert and chunk any mix of files, URLs and a crawled domain into one XLSX.",
        description=(
            "One call, one XLSX. Conversion routing, chunk strategy and backend "
            "credentials are decided by the server, so no tuning flags are needed. "
            "A CSV/XLSX that is already Automate KB shaped is merged as-is."
        ),
    )
    add_common(ingest_parser)
    ingest_parser.add_argument("files", nargs="*", type=Path, help="Files to convert (optional).")
    ingest_parser.add_argument("--url", action="append", help="URL to fetch. Repeatable.")
    ingest_parser.add_argument("--domain", help="Seed URL to crawl, staying on that host.")
    ingest_parser.add_argument("--max-pages", type=int, help="Crawl page cap (server clamps it).")
    ingest_parser.add_argument("--max-depth", type=int, help="Crawl depth cap (server clamps it).")
    ingest_parser.add_argument(
        "--describe",
        action="append",
        metavar="NAME=TEXT",
        help="Optional description for one source, e.g. --describe report.pdf='FY2025 figures'. Repeatable.",
    )
    ingest_parser.add_argument("--metadata-json", help="Raw per-source metadata JSON (overrides --describe).")
    ingest_parser.set_defaults(func=command_ingest, output=None)

    status_parser = subparsers.add_parser("status", help="Call GET /status.")
    add_common(status_parser, defaults=False)
    status_parser.set_defaults(func=command_status)

    convert_parser = subparsers.add_parser("convert", help="Convert uploaded files to Markdown.")
    add_common(convert_parser, defaults=False)
    convert_parser.add_argument("files", type=Path, nargs="+")
    convert_parser.add_argument("--title")
    convert_parser.add_argument("--url")
    convert_parser.add_argument("--description")
    add_pdf_options(convert_parser)
    convert_parser.set_defaults(func=command_convert)

    convert_chunk_parser = subparsers.add_parser("convert-chunk", help="Convert uploaded files and chunk them.")
    add_common(convert_chunk_parser, defaults=False)
    convert_chunk_parser.add_argument("files", type=Path, nargs="+")
    convert_chunk_parser.add_argument("--title")
    convert_chunk_parser.add_argument("--url")
    convert_chunk_parser.add_argument("--description")
    add_pdf_options(convert_chunk_parser)
    add_chunk_options(convert_chunk_parser)
    convert_chunk_parser.add_argument("--chunk-format", default="json", choices=["json", "csv", "xlsx"])
    convert_chunk_parser.set_defaults(func=command_convert_chunk)

    convert_url_parser = subparsers.add_parser("convert-url", help="Convert one or more URLs.")
    add_common(convert_url_parser, defaults=False)
    convert_url_parser.add_argument("urls", nargs="+")
    convert_url_parser.add_argument("--title")
    convert_url_parser.add_argument("--description")
    convert_url_parser.add_argument("--response-format", default="json", choices=["json", "csv", "xlsx"])
    add_chunk_options(convert_url_parser)
    convert_url_parser.set_defaults(func=command_convert_url)

    convert_text_parser = subparsers.add_parser("convert-text", help="Convert raw text to Markdown.")
    add_common(convert_text_parser, defaults=False)
    source = convert_text_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path)
    source.add_argument("--text")
    convert_text_parser.add_argument("--filename", required=True)
    convert_text_parser.add_argument("--ext", required=True, choices=["pdf", "docx", "txt", "html", "md"])
    add_metadata_options(convert_text_parser)
    convert_text_parser.set_defaults(func=command_convert_text)

    chunk_parser = subparsers.add_parser("chunk", help="Chunk Markdown.")
    add_common(chunk_parser, defaults=False)
    markdown_source = chunk_parser.add_mutually_exclusive_group(required=True)
    markdown_source.add_argument("markdown_file", type=Path, nargs="?")
    markdown_source.add_argument("--markdown")
    chunk_parser.add_argument("--document-id")
    chunk_parser.add_argument("--output-format", default="json")
    add_chunk_options(chunk_parser)
    add_metadata_options(chunk_parser)
    chunk_parser.set_defaults(func=command_chunk)

    export_parser = subparsers.add_parser("export", help="Export chunks as JSON or CSV.")
    add_common(export_parser, defaults=False)
    export_parser.add_argument("--chunks-file", type=Path, help="JSON response containing `chunks` or `documents[].chunks`.")
    export_parser.add_argument("--document-id")
    export_parser.add_argument("--format", default="json", choices=["json", "csv"])
    export_parser.add_argument("--filename")
    export_parser.set_defaults(func=command_export)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
