#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
import urllib.parse
import zipfile


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_config_template() -> dict:
    repo_root = repository_root()

    return {
        "defaultProfile": "default",
        "defaultHost": "production",
        "hosts": {
            "production": {
                "server": "https://chatbots.sentione.com",
            }
        },
        "profiles": {
            "default": {
                "host": "production",
                "projectId": "00000000-0000-0000-0000-000000000000",
                "directories": {
                    "exportZips": str(repo_root / "input"),
                    "workspaceRoot": str(repo_root / "work"),
                    "importZips": str(repo_root / "output"),
                },
                "apiKey": {
                    "service": "sentione-automate",
                    "username": "default",
                },
            }
        },
    }


class CliError(RuntimeError):
    pass


def import_keyring() -> tuple[Any, Any]:
    try:
        import keyring
        from keyring.errors import KeyringError
    except ImportError as exc:
        raise CliError(
            "Missing dependency: keyring\n"
            "Install the local CLI dependencies with:\n"
            "  python -m pip install -r scripts/requirements.txt"
        ) from exc

    return keyring, KeyringError


def import_requests() -> Any:
    try:
        import requests
    except ImportError as exc:
        raise CliError(
            "Missing dependency: requests\n"
            "Install the local CLI dependencies with:\n"
            "  python -m pip install -r scripts/requirements.txt"
        ) from exc

    return requests


def user_config_path() -> Path:
    home = Path.home()

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else home / "AppData" / "Roaming"
        return base / "SentiOneAutomate" / "config.json"

    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "SentiOneAutomate" / "config.json"

    return home / ".config" / "sentione-automate" / "config.json"
def load_config() -> dict:
    config_path = user_config_path()
    if not config_path.exists():
        raise CliError(
            f"Config file not found: {config_path}\n"
            "Run `scripts/automate init-config` to create a template, then fill in the non-secret values."
        )

    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CliError(f"Config file is not valid JSON: {config_path}\n{exc}") from exc


def profile_name_from_args(args: argparse.Namespace) -> str | None:
    value = getattr(args, "profile", None)
    return value.strip() if isinstance(value, str) and value.strip() else None


def host_name_from_args(args: argparse.Namespace) -> str | None:
    value = getattr(args, "host", None)
    return value.strip() if isinstance(value, str) and value.strip() else None


def active_profile_name(config: dict, requested_profile: str | None = None) -> str:
    if requested_profile:
        return requested_profile

    default_profile = config.get("defaultProfile")
    if not isinstance(default_profile, str) or not default_profile.strip():
        raise CliError("Config is missing a valid `defaultProfile` value.")

    return default_profile.strip()


def active_profile(config: dict, requested_profile: str | None = None) -> tuple[str, dict]:
    profile_name = active_profile_name(config, requested_profile)
    profiles = config.get("profiles")

    if not isinstance(profiles, dict) or profile_name not in profiles:
        if requested_profile:
            raise CliError(f"Config is missing a `profiles.{profile_name}` entry.")
        raise CliError("Config is missing a `profiles` entry for `defaultProfile`.")

    profile = profiles[profile_name]
    if not isinstance(profile, dict):
        raise CliError("Active profile must be a JSON object.")

    return profile_name, profile


def normalize_base_url(server: str) -> str:
    value = server.rstrip("/")
    if value.endswith("/api/public/v1"):
        return value
    return value + "/api/public/v1"


def require_string(data: dict, key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CliError(f"Missing required string `{key}` in {context}.")
    return value.strip()


def require_directories(profile: dict) -> dict:
    directories = profile.get("directories")
    if not isinstance(directories, dict):
        raise CliError("Profile is missing the `directories` object.")
    return directories


def require_hosts(config: dict) -> dict:
    hosts = config.get("hosts")
    if not isinstance(hosts, dict):
        raise CliError("Config is missing the `hosts` object.")
    return hosts


def resolve_profile_server(
    config: dict,
    profile: dict,
    requested_host: str | None = None,
) -> tuple[str | None, str]:
    host_name = requested_host

    if not host_name:
        profile_host = profile.get("host")
        if isinstance(profile_host, str) and profile_host.strip():
            host_name = profile_host.strip()

    if host_name:
        hosts = require_hosts(config)
        host_entry = hosts.get(host_name)
        if not isinstance(host_entry, dict):
            raise CliError(f"Config is missing a `hosts.{host_name}` entry.")
        server = require_string(host_entry, "server", f"hosts.{host_name}")
        return host_name, server

    direct_server = profile.get("server")
    if isinstance(direct_server, str) and direct_server.strip():
        return None, direct_server.strip()

    default_host = config.get("defaultHost")
    if isinstance(default_host, str) and default_host.strip():
        hosts = require_hosts(config)
        host_name = default_host.strip()
        host_entry = hosts.get(host_name)
        if not isinstance(host_entry, dict):
            raise CliError(f"Config is missing a `hosts.{host_name}` entry.")
        server = require_string(host_entry, "server", f"hosts.{host_name}")
        return host_name, server

    raise CliError(
        "Could not resolve the Automate host for the active profile.\n"
        "Set `profiles.<name>.host`, add `defaultHost`, or keep a backward-compatible `profiles.<name>.server`."
    )


def require_api_key_reference(profile: dict) -> tuple[str, str]:
    api_key = profile.get("apiKey")
    if not isinstance(api_key, dict):
        raise CliError("Profile is missing the `apiKey` object.")

    service = require_string(api_key, "service", "profile.apiKey")
    username = require_string(api_key, "username", "profile.apiKey")
    return service, username


def load_api_key(profile: dict) -> str:
    service, username = require_api_key_reference(profile)
    keyring, KeyringError = import_keyring()

    try:
        secret = keyring.get_password(service, username)
    except KeyringError as exc:
        raise CliError(
            "Failed to read the API key from the OS keychain.\n"
            "Ensure the `keyring` backend is available on this machine."
        ) from exc

    if not secret:
        raise CliError(
            "API key not found in the OS keychain.\n"
            f"Expected keyring entry: service={service!r}, username={username!r}\n"
            "Store it locally with:\n"
            f"  python -m keyring set {service} {username}"
        )

    return secret


def build_session(config: dict, profile: dict, requested_host: str | None = None) -> tuple[Any, str | None]:
    requests = import_requests()
    host_name, server = resolve_profile_server(config, profile, requested_host=requested_host)
    api_key = load_api_key(profile)

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            "X-Api-Key": api_key,
        }
    )
    session.base_url = normalize_base_url(server)
    return session, host_name


def api_url(session: Any, path: str) -> str:
    return f"{session.base_url}{path}"


def path_quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def error_message(response: Any) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        code = payload.get("code")
        message = payload.get("message")
        parts = [part for part in [str(code) if code else None, str(message) if message else None] if part]
        if parts:
            return " - ".join(parts)

    return response.text.strip() or response.reason or "Unknown API error"


def ensure_success(response: Any, action: str) -> None:
    if response.ok:
        return

    raise CliError(f"{action} failed with HTTP {response.status_code}: {error_message(response)}")


def safe_name(value: str) -> str:
    normalized = "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in value)
    return normalized.strip("-_") or "project"


def print_table(rows: list[tuple[str, ...]]) -> None:
    if not rows:
        print("No rows.")
        return

    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    for row in rows:
        print("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))


def render_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def maybe_write_json_output(value: Any, output_path: str | None) -> None:
    if not output_path:
        return

    destination = Path(output_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_json(value) + "\n", encoding="utf-8")
    print(f"Wrote JSON: {destination}")


def load_json_value(value: str, label: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise CliError(f"{label} is not valid JSON: {exc}") from exc


def load_json_file(path: str | Path, label: str) -> Any:
    source = Path(path).expanduser()
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CliError(f"Could not read {label}: {source}\n{exc}") from exc
    except json.JSONDecodeError as exc:
        raise CliError(f"{label} is not valid JSON: {source}\n{exc}") from exc


def write_binary_response(response: Any, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)


def output_root(profile: dict, subdir: str) -> Path:
    directories = require_directories(profile)
    import_root = Path(require_string(directories, "importZips", "profile.directories")).expanduser()
    return import_root / subdir


def print_json_or_table(payload: Any, output_path: str | None, json_output: bool, rows: list[tuple[str, ...]]) -> None:
    maybe_write_json_output(payload, output_path)
    if json_output:
        print(render_json(payload))
        return
    print_table(rows)


def response_json_or_empty(response: Any) -> Any:
    if not response.content:
        return {}
    return response.json()


def resolve_output_path(destination: str | None, default_root: Path, default_name: str) -> Path:
    if destination:
        return Path(destination).expanduser()
    return default_root / default_name


def print_conversation_search_results(payload: dict) -> None:
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        print("No conversations found.")
        return

    rows = [
        (
            "INTERNAL SESSION ID",
            "START TIME",
            "UPDATED TIME",
            "SOURCE",
            "USER MSGS",
            "BOT MSGS",
            "ERRORS",
            "RECORDING",
        )
    ]

    for item in results:
        if not isinstance(item, dict):
            continue

        recording = item.get("recording")
        recording_status = ""
        if isinstance(recording, dict):
            recording_status = str(recording.get("status", ""))

        rows.append(
            (
                str(item.get("internalSessionId", "")),
                str(item.get("startTime", "")),
                str(item.get("updateTime", "")),
                str(item.get("source", "")),
                str(item.get("userMessageCount", "")),
                str(item.get("botMessageCount", "")),
                str(item.get("errorsCount", "")),
                recording_status,
            )
        )

    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    for row in rows:
        print("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))

    total_count = payload.get("totalCount")
    next_cursor = payload.get("nextCursor")
    print(f"Total count: {total_count}")
    print(f"Next cursor: {next_cursor or '<none>'}")


def print_conversation_messages(messages: list[dict], include_bot_logs: bool) -> None:
    if not messages:
        print("No messages found.")
        return

    for item in messages:
        timestamp = str(item.get("timestamp", ""))
        print(f"[{timestamp}]")

        user_input = item.get("userInput")
        if isinstance(user_input, dict):
            author = user_input.get("author")
            author_prefix = f"{author}: " if author else ""
            print(f"User: {author_prefix}{user_input.get('message', '')}")

        bot_output = item.get("botOutput")
        if isinstance(bot_output, dict):
            events = bot_output.get("events")
            if isinstance(events, list):
                for event in events:
                    if not isinstance(event, dict):
                        continue

                    event_type = event.get("type")
                    if event_type == "BotReply":
                        print(f"Bot: {event.get('text', '')}")
                    elif event_type == "BotLog" and include_bot_logs:
                        print(f"BotLog: {event.get('message', '')}")

            tags = bot_output.get("tags")
            if isinstance(tags, list) and tags:
                print(f"Tags: {', '.join(str(tag) for tag in tags)}")

            commands = bot_output.get("commands")
            if isinstance(commands, list) and commands:
                command_types = [str(command.get("type", "")) for command in commands if isinstance(command, dict)]
                if command_types:
                    print(f"Commands: {', '.join(command_types)}")

            nlu_results = bot_output.get("nluResults")
            if isinstance(nlu_results, list) and nlu_results:
                for result in nlu_results:
                    if not isinstance(result, dict):
                        continue
                    model_id = str(result.get("modelId", ""))
                    intents = result.get("intents")
                    if isinstance(intents, dict) and intents:
                        intent_summary = ", ".join(f"{name}={score}" for name, score in intents.items())
                        print(f"NLU ({model_id}): {intent_summary}")

        metrics = item.get("metrics")
        if isinstance(metrics, dict):
            print(
                "Metrics: "
                f"process={metrics.get('processTime', '')}ms, "
                f"nlu={metrics.get('nluTime', '')}ms, "
                f"integrations={metrics.get('integrationsTime', '')}ms"
            )

        print()


def default_recordings_root(profile: dict) -> Path:
    return output_root(profile, "recordings")


def guess_recording_extension(content_type: str | None) -> str:
    if not content_type:
        return ".bin"

    mime_type = content_type.split(";", 1)[0].strip().lower()
    if mime_type == "audio/mpeg":
        return ".mp3"

    guessed = mimetypes.guess_extension(mime_type)
    return guessed or ".bin"


def open_media_file(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
            return

        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
            return

        subprocess.Popen(["xdg-open", str(path)])
    except FileNotFoundError as exc:
        raise CliError(
            f"Could not open the recording automatically: {exc}\n"
            f"Open it manually: {path}"
        ) from exc
    except OSError as exc:
        raise CliError(
            f"Could not open the recording automatically: {exc}\n"
            f"Open it manually: {path}"
        ) from exc


def command_config_path(_: argparse.Namespace) -> int:
    print(user_config_path())
    return 0


def command_init_config(args: argparse.Namespace) -> int:
    destination = user_config_path()
    config = default_config_template()

    if destination.exists() and not args.force:
        raise CliError(
            f"Config file already exists: {destination}\n"
            "Use `scripts/automate init-config --force` only if you intend to overwrite it."
        )

    directories = config["profiles"]["default"]["directories"]
    for path in directories.values():
        Path(path).mkdir(parents=True, exist_ok=True)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote config template to {destination}")
    return 0


def command_doctor(_: argparse.Namespace) -> int:
    config_path = user_config_path()
    print(f"Config path: {config_path}")

    if not config_path.exists():
        print("Config file: missing")
        print("Run `scripts/automate init-config` to create a template.")
        return 1

    config = load_config()
    profile_name, profile = active_profile(config, profile_name_from_args(_))
    directories = require_directories(profile)
    host_name, server = resolve_profile_server(config, profile, requested_host=host_name_from_args(_))
    service, username = require_api_key_reference(profile)

    print(f"Active profile: {profile_name}")
    if host_name:
        print(f"Active host: {host_name}")
    print(f"Server: {normalize_base_url(server)}")
    print(f"Project ID: {require_string(profile, 'projectId', 'profile')}")
    print(f"Export ZIP dir: {require_string(directories, 'exportZips', 'profile.directories')}")
    print(f"Workspace root: {require_string(directories, 'workspaceRoot', 'profile.directories')}")
    print(f"Import ZIP dir: {require_string(directories, 'importZips', 'profile.directories')}")
    print(f"Keyring service: {service}")
    print(f"Keyring username: {username}")

    keyring, KeyringError = import_keyring()
    try:
        secret = keyring.get_password(service, username)
    except KeyringError:
        print("API key lookup: failed to access OS keychain")
        return 1

    print("API key lookup: ok" if secret else "API key lookup: missing")
    return 0 if secret else 1


def command_hosts(_: argparse.Namespace) -> int:
    config = load_config()
    hosts = config.get("hosts")

    if not isinstance(hosts, dict) or not hosts:
        print("No configured hosts.")
        return 0

    rows = [("HOST", "SERVER")]
    for host_name in sorted(hosts):
        host_entry = hosts.get(host_name)
        if isinstance(host_entry, dict):
            server = str(host_entry.get("server", ""))
        else:
            server = ""
        rows.append((host_name, normalize_base_url(server) if server else ""))

    print_table(rows)
    return 0


def command_projects(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    response = session.get(api_url(session, "/projects"), timeout=60)
    ensure_success(response, "Listing projects")
    payload = response.json()

    rows = [("ID", "NAME", "CREATED AT")]
    for item in payload:
        rows.append(
            (
                str(item.get("id", "")),
                str(item.get("name", "")),
                str(item.get("createdAt", "")),
            )
        )

    print_table(rows)
    return 0


def project_details(session: Any, project_id: str) -> dict:
    response = session.get(api_url(session, f"/projects/{project_id}"), timeout=60)
    ensure_success(response, "Fetching project details")
    return response.json()


def unpack_zip(zip_path: Path, workspace_root: Path, target_name: str) -> Path:
    destination = workspace_root / safe_name(target_name)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(destination)

    return destination


def command_export(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    directories = require_directories(profile)
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))
    project_id = args.project_id or require_string(profile, "projectId", "profile")

    details = project_details(session, project_id)
    project_name = str(details.get("name") or project_id)

    export_root = Path(require_string(directories, "exportZips", "profile.directories")).expanduser()
    export_root.mkdir(parents=True, exist_ok=True)

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_zip_name = f"{safe_name(project_name)}_{timestamp}.zip"
    zip_path = Path(args.destination).expanduser() if args.destination else export_root / default_zip_name
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    response = session.get(api_url(session, f"/projects/{project_id}/export"), stream=True, timeout=300)
    ensure_success(response, "Exporting project")

    with zip_path.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)

    print(f"Exported ZIP: {zip_path}")

    if args.no_unpack:
        return 0

    workspace_root = Path(require_string(directories, "workspaceRoot", "profile.directories")).expanduser()
    workspace_root.mkdir(parents=True, exist_ok=True)
    unpacked_path = unpack_zip(zip_path, workspace_root, project_name)
    print(f"Unpacked to: {unpacked_path}")
    return 0


def command_import(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))
    project_id = args.project_id or require_string(profile, "projectId", "profile")

    zip_path = Path(args.zip_path).expanduser()
    if not zip_path.exists():
        raise CliError(f"ZIP file not found: {zip_path}")

    with zip_path.open("rb") as handle:
        files = {"file": (zip_path.name, handle, "application/zip")}
        response = session.post(
            api_url(session, f"/projects/{project_id}/import"),
            params={"publishFlows": "true" if args.publish_flows else "false"},
            files=files,
            timeout=300,
        )

    ensure_success(response, "Importing project")
    payload = response.json()

    details = payload.get("projectDetails") or {}
    print(f"Imported project: {details.get('name', project_id)} ({details.get('id', project_id)})")

    publish_results = payload.get("publishResults")
    if publish_results:
        rows = [("STATUS", "FLOW ID", "FLOW NAME", "MESSAGE")]
        for item in publish_results:
            rows.append(
                (
                    str(item.get("status", "")),
                    str(item.get("flowId", "")),
                    str(item.get("flowName", "")),
                    str(item.get("message", "")),
                )
            )
        print_table(rows)

    return 0


def command_conversations_search(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    payload: dict[str, Any] = {}

    if args.project_id:
        payload["projectIds"] = args.project_id
    if args.session_id:
        payload["sessionIds"] = args.session_id
    if args.cursor:
        payload["cursor"] = args.cursor
    if args.limit is not None:
        payload["limit"] = args.limit
    if args.from_time:
        payload["from"] = args.from_time
    if args.to_time:
        payload["to"] = args.to_time
    if args.sort_by:
        payload["sortBy"] = args.sort_by
    if args.sort_order:
        payload["sortOrder"] = args.sort_order
    if args.recording_status:
        payload["recordingStatus"] = args.recording_status

    response = session.post(
        api_url(session, "/conversations/search"),
        json=payload,
        timeout=120,
    )
    ensure_success(response, "Searching conversations")
    response_payload = response.json()

    maybe_write_json_output(response_payload, args.output)

    if args.json:
        print(render_json(response_payload))
        return 0

    print_conversation_search_results(response_payload)
    return 0


def command_conversations_messages(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    response = session.get(
        api_url(session, f"/conversations/{path_quote(args.internal_session_id)}/messages"),
        params={"includeBotLogs": "true" if args.include_bot_logs else "false"},
        timeout=120,
    )
    ensure_success(response, "Fetching conversation messages")
    payload = response.json()

    maybe_write_json_output(payload, args.output)

    if args.json:
        print(render_json(payload))
        return 0

    if not isinstance(payload, list):
        raise CliError("Unexpected API response: conversation messages payload is not a list.")

    print_conversation_messages(payload, include_bot_logs=args.include_bot_logs)
    return 0


def command_conversations_recording(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    response = session.get(
        api_url(session, f"/conversations/{path_quote(args.internal_session_id)}/recording"),
        stream=True,
        timeout=300,
    )
    ensure_success(response, "Fetching conversation recording")

    content_type = response.headers.get("Content-Type")
    extension = guess_recording_extension(content_type)

    if args.destination:
        destination = Path(args.destination).expanduser()
    else:
        recordings_root = default_recordings_root(profile)
        recordings_root.mkdir(parents=True, exist_ok=True)
        destination = recordings_root / f"{safe_name(args.internal_session_id)}{extension}"

    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)

    print(f"Recording saved to: {destination}")
    if content_type:
        print(f"Content-Type: {content_type}")

    if args.play:
        open_media_file(destination)
        print("Opened recording in the default media player.")

    return 0


def command_conversations_recording_delete(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    response = session.delete(
        api_url(session, f"/conversations/{path_quote(args.internal_session_id)}/recording"),
        timeout=120,
    )
    ensure_success(response, "Deleting conversation recording")
    print(f"Deleted recording for internal session: {args.internal_session_id}")
    return 0


def command_conversations_recording_schedule_deletion(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    response = session.post(
        api_url(session, f"/conversations/{path_quote(args.internal_session_id)}/recording/scheduleDeletion"),
        json={"deletionTime": args.deletion_time},
        timeout=120,
    )
    ensure_success(response, "Scheduling conversation recording deletion")
    print(f"Scheduled recording deletion for internal session: {args.internal_session_id}")
    print(f"Deletion time: {args.deletion_time}")
    return 0


def command_ai_credentials(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    response = session.get(api_url(session, "/organization/ai-credentials"), timeout=60)
    ensure_success(response, "Listing AI credentials")
    payload = response.json()

    rows: list[tuple[str, ...]] = [("ID", "NAME", "CAPABILITIES")]
    for item in payload:
        if not isinstance(item, dict):
            continue
        capabilities = item.get("supportedCapabilities")
        if isinstance(capabilities, list):
            capability_text = ", ".join(str(value) for value in capabilities)
        else:
            capability_text = ""
        rows.append((str(item.get("id", "")), str(item.get("name", "")), capability_text))

    print_json_or_table(payload, args.output, args.json, rows)
    return 0


def command_knowledge_documents_list(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    response = session.get(api_url(session, "/knowledge/documents"), timeout=120)
    ensure_success(response, "Listing knowledge base documents")
    payload = response.json()

    rows: list[tuple[str, ...]] = [("KEY", "CREATED AT", "UPDATED AT", "INDEXATION", "EMBEDDINGS CREDENTIALS")]
    for item in payload:
        if not isinstance(item, dict):
            continue
        rows.append(
            (
                str(item.get("key", "")),
                str(item.get("createdAt", "")),
                str(item.get("updatedAt", "")),
                str(item.get("indexationStatus", "")),
                str(item.get("embeddingsCredentialsId", "")),
            )
        )

    print_json_or_table(payload, args.output, args.json, rows)
    return 0


def command_knowledge_documents_get(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    response = session.get(api_url(session, f"/knowledge/documents/{path_quote(args.key)}"), timeout=120)
    ensure_success(response, "Fetching knowledge base document")
    payload = response.json()

    maybe_write_json_output(payload, args.output)
    print(render_json(payload))
    return 0


def document_upsert_params(args: argparse.Namespace) -> dict:
    if args.params_file:
        params = load_json_file(args.params_file, "--params-file")
    elif args.params_json:
        params = load_json_value(args.params_json, "--params-json")
    else:
        params = {}

    if not isinstance(params, dict):
        raise CliError("Document upsert params must be a JSON object.")

    if args.embeddings_credentials_id:
        params["embeddingsCredentialsId"] = args.embeddings_credentials_id

    return params


def command_knowledge_documents_upsert(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    file_path = Path(args.file).expanduser()
    if not file_path.exists():
        raise CliError(f"Document file not found: {file_path}")

    params = document_upsert_params(args)
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    with file_path.open("rb") as handle:
        files = {
            "params": (None, json.dumps(params), "application/json"),
            "file": (file_path.name, handle, mime_type),
        }
        response = session.put(
            api_url(session, f"/knowledge/documents/{path_quote(args.key)}"),
            files=files,
            timeout=300,
        )

    ensure_success(response, "Upserting knowledge base document")
    payload = response.json()
    maybe_write_json_output(payload, args.output)
    print(render_json(payload))
    return 0


def command_knowledge_documents_export(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    export_format = args.format
    response = session.get(
        api_url(session, f"/knowledge/documents/{path_quote(args.key)}/export/{export_format}"),
        stream=True,
        timeout=300,
    )
    ensure_success(response, f"Exporting knowledge base document as {export_format.upper()}")

    destination = resolve_output_path(
        args.destination,
        output_root(profile, "knowledge"),
        f"{safe_name(args.key)}.{export_format}",
    )
    write_binary_response(response, destination)
    print(f"Exported knowledge base document: {destination}")
    return 0


def command_knowledge_items_export(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    response = session.get(api_url(session, "/knowledge/items/export"), stream=True, timeout=300)
    ensure_success(response, "Exporting knowledge base items")

    destination = resolve_output_path(
        args.destination,
        output_root(profile, "knowledge"),
        "knowledge-items.csv",
    )
    write_binary_response(response, destination)
    print(f"Exported knowledge base items: {destination}")
    return 0


def command_knowledge_items_import(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    file_path = Path(args.file).expanduser()
    if not file_path.exists():
        raise CliError(f"Knowledge items CSV file not found: {file_path}")

    with file_path.open("rb") as handle:
        files = {"file": (file_path.name, handle, "text/csv")}
        response = session.post(api_url(session, "/knowledge/items/import"), files=files, timeout=300)

    ensure_success(response, "Importing knowledge base items")
    payload = response.json()
    maybe_write_json_output(payload, args.output)
    print(render_json(payload))
    return 0


def parse_call_params(args: argparse.Namespace) -> dict[str, str] | None:
    params: dict[str, str] = {}

    if args.call_params_file:
        loaded = load_json_file(args.call_params_file, "--call-params-file")
        if not isinstance(loaded, dict):
            raise CliError("--call-params-file must contain a JSON object.")
        params.update({str(key): str(value) for key, value in loaded.items()})

    if args.call_params_json:
        loaded = load_json_value(args.call_params_json, "--call-params-json")
        if not isinstance(loaded, dict):
            raise CliError("--call-params-json must be a JSON object.")
        params.update({str(key): str(value) for key, value in loaded.items()})

    for item in args.call_param or []:
        if "=" not in item:
            raise CliError("--call-param must use KEY=VALUE format.")
        key, value = item.split("=", 1)
        if not key:
            raise CliError("--call-param key cannot be empty.")
        params[key] = value

    return params or None


def dialer_contact_payload(args: argparse.Namespace) -> dict:
    if args.payload_file:
        payload = load_json_file(args.payload_file, "--payload-file")
    elif args.payload_json:
        payload = load_json_value(args.payload_json, "--payload-json")
    else:
        missing = [
            flag
            for flag, value in [
                ("--phone-number", args.phone_number),
                ("--calling-start", args.calling_start),
                ("--calling-end", args.calling_end),
                ("--call-attempts-limit-per-day", args.call_attempts_limit_per_day),
            ]
            if value is None
        ]
        if missing:
            raise CliError(
                "Missing required dialer contact flags when no payload file/json is provided: "
                + ", ".join(missing)
            )
        payload = {
            "phoneNumber": args.phone_number,
            "callingStart": args.calling_start,
            "callingEnd": args.calling_end,
            "callAttemptsLimitPerDay": args.call_attempts_limit_per_day,
        }
        call_params = parse_call_params(args)
        if call_params:
            payload["callParams"] = call_params

    if not isinstance(payload, dict):
        raise CliError("Dialer contact payload must be a JSON object.")
    return payload


def command_dialer_contacts_add(args: argparse.Namespace) -> int:
    config = load_config()
    _, profile = active_profile(config, profile_name_from_args(args))
    session, _ = build_session(config, profile, requested_host=host_name_from_args(args))

    payload = dialer_contact_payload(args)
    response = session.post(
        api_url(session, f"/dialer/campaigns/{path_quote(args.campaign_id)}/contacts"),
        json=payload,
        timeout=120,
    )
    ensure_success(response, "Adding dialer contact")

    response_payload = response_json_or_empty(response)
    maybe_write_json_output(response_payload, args.output)
    print("Added dialer contact.")
    if response_payload:
        print(render_json(response_payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local SentiOne Automate Public API helper.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    remote_parent = argparse.ArgumentParser(add_help=False)
    remote_parent.add_argument(
        "--profile",
        help="Optional config profile name. Defaults to `defaultProfile`.",
    )
    remote_parent.add_argument(
        "--host",
        help="Optional configured host alias override. Uses `profiles.<name>.host` or `defaultHost` when omitted.",
    )

    config_path_parser = subparsers.add_parser("config-path", help="Print the expected local config path.")
    config_path_parser.set_defaults(func=command_config_path)

    init_config_parser = subparsers.add_parser("init-config", help="Create a non-secret config template.")
    init_config_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the local config template if it already exists.",
    )
    init_config_parser.set_defaults(func=command_init_config)

    doctor_parser = subparsers.add_parser(
        "doctor",
        parents=[remote_parent],
        help="Validate local config and keyring setup.",
    )
    doctor_parser.set_defaults(func=command_doctor)

    hosts_parser = subparsers.add_parser("hosts", help="List configured Automate host aliases.")
    hosts_parser.set_defaults(func=command_hosts)

    conversations_parser = subparsers.add_parser("conversations", help="Search conversations, fetch message history, and download recordings.")
    conversations_subparsers = conversations_parser.add_subparsers(dest="conversations_command", required=True)

    conversations_search_parser = conversations_subparsers.add_parser(
        "search",
        parents=[remote_parent],
        help="Search historical conversation sessions.",
    )
    conversations_search_parser.add_argument(
        "--project-id",
        action="append",
        help="Optional project ID filter. Can be provided multiple times.",
    )
    conversations_search_parser.add_argument(
        "--session-id",
        action="append",
        help="Optional session ID filter (external or internal). Can be provided multiple times.",
    )
    conversations_search_parser.add_argument(
        "--from",
        dest="from_time",
        help="Optional ISO-8601 start timestamp, for example 2026-01-01T00:00:00.000Z.",
    )
    conversations_search_parser.add_argument(
        "--to",
        dest="to_time",
        help="Optional ISO-8601 end timestamp, for example 2026-01-31T23:59:59.000Z.",
    )
    conversations_search_parser.add_argument(
        "--limit",
        type=int,
        help="Optional page size. The API supports values from 1 to 1000.",
    )
    conversations_search_parser.add_argument(
        "--cursor",
        help="Optional pagination cursor returned by a previous search response.",
    )
    conversations_search_parser.add_argument(
        "--sort-by",
        choices=["StartTime", "UpdateTime"],
        help="Optional sort field.",
    )
    conversations_search_parser.add_argument(
        "--sort-order",
        choices=["Asc", "Desc"],
        help="Optional sort order.",
    )
    conversations_search_parser.add_argument(
        "--recording-status",
        action="append",
        choices=["Uploaded", "ScheduledForDeletion", "Deleted", "Unavailable"],
        help="Optional recording lifecycle filter. Can be provided multiple times.",
    )
    conversations_search_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full API response as formatted JSON.",
    )
    conversations_search_parser.add_argument(
        "--output",
        help="Optional path to write the full API response as JSON.",
    )
    conversations_search_parser.set_defaults(func=command_conversations_search)

    conversations_messages_parser = conversations_subparsers.add_parser(
        "messages",
        parents=[remote_parent],
        help="Fetch all messages for a historical conversation session.",
    )
    conversations_messages_parser.add_argument(
        "internal_session_id",
        help="Internal session ID returned by `conversations search`.",
    )
    conversations_messages_parser.add_argument(
        "--include-bot-logs",
        action="store_true",
        help="Include BotLog events in the API response and printed output.",
    )
    conversations_messages_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full API response as formatted JSON.",
    )
    conversations_messages_parser.add_argument(
        "--output",
        help="Optional path to write the full API response as JSON.",
    )
    conversations_messages_parser.set_defaults(func=command_conversations_messages)

    conversations_recording_parser = conversations_subparsers.add_parser(
        "recording",
        parents=[remote_parent],
        help="Download a conversation recording and optionally open it in the default media player.",
    )
    conversations_recording_parser.add_argument(
        "internal_session_id",
        help="Internal session ID returned by `conversations search`.",
    )
    conversations_recording_parser.add_argument(
        "destination",
        nargs="?",
        help="Optional destination media file path. Defaults to `output/recordings/<internalSessionId>.<ext>`.",
    )
    conversations_recording_parser.add_argument(
        "--play",
        action="store_true",
        help="Open the downloaded recording in the default media player after saving it.",
    )
    conversations_recording_parser.set_defaults(func=command_conversations_recording)

    conversations_recording_delete_parser = conversations_subparsers.add_parser(
        "recording-delete",
        parents=[remote_parent],
        help="Permanently delete a conversation recording.",
    )
    conversations_recording_delete_parser.add_argument(
        "internal_session_id",
        help="Internal session ID returned by `conversations search`.",
    )
    conversations_recording_delete_parser.set_defaults(func=command_conversations_recording_delete)

    conversations_recording_schedule_deletion_parser = conversations_subparsers.add_parser(
        "recording-schedule-deletion",
        parents=[remote_parent],
        help="Schedule a conversation recording for future deletion.",
    )
    conversations_recording_schedule_deletion_parser.add_argument(
        "internal_session_id",
        help="Internal session ID returned by `conversations search`.",
    )
    conversations_recording_schedule_deletion_parser.add_argument(
        "deletion_time",
        help="Future ISO-8601 timestamp, at most 365 days from now.",
    )
    conversations_recording_schedule_deletion_parser.set_defaults(func=command_conversations_recording_schedule_deletion)

    ai_credentials_parser = subparsers.add_parser(
        "ai-credentials",
        parents=[remote_parent],
        help="List AI credentials available to the organization.",
    )
    ai_credentials_parser.add_argument("--json", action="store_true", help="Print the full API response as formatted JSON.")
    ai_credentials_parser.add_argument("--output", help="Optional path to write the full API response as JSON.")
    ai_credentials_parser.set_defaults(func=command_ai_credentials)

    knowledge_parser = subparsers.add_parser(
        "knowledge",
        help="Operate on public API knowledge base documents and items.",
    )
    knowledge_subparsers = knowledge_parser.add_subparsers(dest="knowledge_command", required=True)

    knowledge_documents_parser = knowledge_subparsers.add_parser(
        "documents",
        help="List, inspect, upsert, and export knowledge base documents.",
    )
    knowledge_documents_subparsers = knowledge_documents_parser.add_subparsers(
        dest="knowledge_documents_command",
        required=True,
    )

    knowledge_documents_list_parser = knowledge_documents_subparsers.add_parser(
        "list",
        parents=[remote_parent],
        help="List knowledge base documents.",
    )
    knowledge_documents_list_parser.add_argument("--json", action="store_true", help="Print the full API response as formatted JSON.")
    knowledge_documents_list_parser.add_argument("--output", help="Optional path to write the full API response as JSON.")
    knowledge_documents_list_parser.set_defaults(func=command_knowledge_documents_list)

    knowledge_documents_get_parser = knowledge_documents_subparsers.add_parser(
        "get",
        parents=[remote_parent],
        help="Get one knowledge base document by key.",
    )
    knowledge_documents_get_parser.add_argument("key", help="Knowledge base document key.")
    knowledge_documents_get_parser.add_argument("--output", help="Optional path to write the full API response as JSON.")
    knowledge_documents_get_parser.set_defaults(func=command_knowledge_documents_get)

    knowledge_documents_upsert_parser = knowledge_documents_subparsers.add_parser(
        "upsert",
        parents=[remote_parent],
        help="Create or update a knowledge base document from CSV or XLSX.",
    )
    knowledge_documents_upsert_parser.add_argument("key", help="Knowledge base document key.")
    knowledge_documents_upsert_parser.add_argument("file", help="CSV or XLSX file to upload.")
    knowledge_documents_upsert_parser.add_argument(
        "--embeddings-credentials-id",
        help="AI credential ID for embeddings. If omitted, Automate uses the default embeddings credential.",
    )
    knowledge_documents_upsert_parser.add_argument(
        "--params-json",
        help="Raw JSON object for the multipart `params` field.",
    )
    knowledge_documents_upsert_parser.add_argument(
        "--params-file",
        help="Path to a JSON file for the multipart `params` field.",
    )
    knowledge_documents_upsert_parser.add_argument("--output", help="Optional path to write the full API response as JSON.")
    knowledge_documents_upsert_parser.set_defaults(func=command_knowledge_documents_upsert)

    knowledge_documents_export_parser = knowledge_documents_subparsers.add_parser(
        "export",
        parents=[remote_parent],
        help="Export one knowledge base document as CSV or XLSX.",
    )
    knowledge_documents_export_parser.add_argument("key", help="Knowledge base document key.")
    knowledge_documents_export_parser.add_argument("--format", choices=["csv", "xlsx"], default="csv")
    knowledge_documents_export_parser.add_argument(
        "destination",
        nargs="?",
        help="Optional destination file. Defaults to configured import ZIP dir under `knowledge/`.",
    )
    knowledge_documents_export_parser.set_defaults(func=command_knowledge_documents_export)

    knowledge_items_parser = knowledge_subparsers.add_parser(
        "items",
        help="Export and import simple knowledge base items.",
    )
    knowledge_items_subparsers = knowledge_items_parser.add_subparsers(dest="knowledge_items_command", required=True)

    knowledge_items_export_parser = knowledge_items_subparsers.add_parser(
        "export",
        parents=[remote_parent],
        help="Export all knowledge base items as CSV.",
    )
    knowledge_items_export_parser.add_argument(
        "destination",
        nargs="?",
        help="Optional destination CSV path. Defaults to configured import ZIP dir under `knowledge/knowledge-items.csv`.",
    )
    knowledge_items_export_parser.set_defaults(func=command_knowledge_items_export)

    knowledge_items_import_parser = knowledge_items_subparsers.add_parser(
        "import",
        parents=[remote_parent],
        help="Import or update knowledge base items from CSV.",
    )
    knowledge_items_import_parser.add_argument("file", help="CSV file with key,value,expiresAt columns.")
    knowledge_items_import_parser.add_argument("--output", help="Optional path to write the full API response as JSON.")
    knowledge_items_import_parser.set_defaults(func=command_knowledge_items_import)

    dialer_parser = subparsers.add_parser(
        "dialer",
        help="Operate on public API dialer endpoints.",
    )
    dialer_subparsers = dialer_parser.add_subparsers(dest="dialer_command", required=True)
    dialer_contacts_parser = dialer_subparsers.add_parser("contacts", help="Operate on dialer campaign contacts.")
    dialer_contacts_subparsers = dialer_contacts_parser.add_subparsers(dest="dialer_contacts_command", required=True)

    dialer_contacts_add_parser = dialer_contacts_subparsers.add_parser(
        "add",
        parents=[remote_parent],
        help="Add a contact to a dialer campaign.",
    )
    dialer_contacts_add_parser.add_argument("campaign_id", help="Dialer campaign ID.")
    dialer_contacts_add_parser.add_argument("--phone-number", help="Contact phone number.")
    dialer_contacts_add_parser.add_argument("--calling-start", help="Calling start date-time in ISO-8601 format.")
    dialer_contacts_add_parser.add_argument("--calling-end", help="Calling end date-time in ISO-8601 format.")
    dialer_contacts_add_parser.add_argument("--call-attempts-limit-per-day", type=int, help="Maximum daily call attempts.")
    dialer_contacts_add_parser.add_argument(
        "--call-param",
        action="append",
        help="Dynamic call param in KEY=VALUE form. Can be provided multiple times.",
    )
    dialer_contacts_add_parser.add_argument("--call-params-json", help="JSON object for dynamic call params.")
    dialer_contacts_add_parser.add_argument("--call-params-file", help="JSON file for dynamic call params.")
    dialer_contacts_add_parser.add_argument("--payload-json", help="Full AddContactRequest JSON object.")
    dialer_contacts_add_parser.add_argument("--payload-file", help="File containing full AddContactRequest JSON object.")
    dialer_contacts_add_parser.add_argument("--output", help="Optional path to write the API response as JSON.")
    dialer_contacts_add_parser.set_defaults(func=command_dialer_contacts_add)

    projects_parser = subparsers.add_parser(
        "projects",
        parents=[remote_parent],
        help="List projects available to the configured API key.",
    )
    projects_parser.set_defaults(func=command_projects)

    export_parser = subparsers.add_parser(
        "export",
        parents=[remote_parent],
        help="Export the configured project as a ZIP.",
    )
    export_parser.add_argument(
        "destination",
        nargs="?",
        help="Optional destination ZIP path. Defaults to the configured export ZIP directory.",
    )
    export_parser.add_argument(
        "--project-id",
        help="Override the configured project ID. Use this to export a project without changing local config.",
    )
    export_parser.add_argument(
        "--no-unpack",
        action="store_true",
        help="Download the ZIP only and skip workspace extraction.",
    )
    export_parser.set_defaults(func=command_export)

    import_parser = subparsers.add_parser(
        "import",
        parents=[remote_parent],
        help="Import a ZIP into the configured project.",
    )
    import_parser.add_argument("zip_path", help="Path to the ZIP file that should be imported.")
    import_parser.add_argument(
        "--project-id",
        help="Override the configured project ID. Use this for creating a new project from a ZIP without changing local config.",
    )
    import_parser.add_argument(
        "--publish-flows",
        action="store_true",
        help="Publish all flows after import.",
    )
    import_parser.set_defaults(func=command_import)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except CliError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        try:
            requests = import_requests()
        except CliError:
            requests = None

        if requests is not None and isinstance(exc, requests.RequestException):
            print(f"Network error: {exc}", file=sys.stderr)
            return 1

        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
