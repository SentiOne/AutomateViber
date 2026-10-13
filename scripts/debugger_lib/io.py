from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Iterator

from .models import DialogState, MessageRecord, SessionRecord


class CliError(RuntimeError):
    pass


def _require_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CliError(f"Missing required string in {context}.")
    return value.strip()


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _parse_dialog_state(value: object, line_number: int) -> DialogState | None:
    if value is None:
        return None

    if not isinstance(value, dict):
        raise CliError(f"Invalid dialogState at sessions.json line {line_number}: expected object or null.")

    return DialogState(
        block_id=_require_string(value.get("id"), f"sessions.json line {line_number} dialogState.id"),
        block_name=_require_string(value.get("name"), f"sessions.json line {line_number} dialogState.name"),
        context=_optional_string(value.get("context")),
        context_uuid=_optional_string(value.get("contextUuid")),
        tags=_parse_tags(value.get("tags"), f"sessions.json line {line_number} dialogState.tags"),
    )


def _parse_tags(value: object, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CliError(f"Invalid tags in {context}: expected array or null.")

    parsed_tags: list[str] = []
    for index, item in enumerate(value):
        parsed_tags.append(_require_string(item, f"{context}[{index}]"))
    return tuple(parsed_tags)


def _parse_command_types(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()

    command_types: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            command_types.append(item.strip())
            continue

        if not isinstance(item, dict):
            continue

        command_type = item.get("type") or item.get("name") or item.get("command")
        if isinstance(command_type, str) and command_type.strip():
            command_types.append(command_type.strip())

    return tuple(command_types)


def _parse_json_list(value: object) -> tuple[object, ...]:
    if isinstance(value, list):
        return tuple(value)
    return ()


def iter_session_records(zip_path: Path) -> Iterator[SessionRecord]:
    if not zip_path.exists():
        raise CliError(f"ZIP file not found: {zip_path}")

    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise CliError(f"Invalid ZIP file: {zip_path}") from exc

    with archive:
        try:
            session_file = archive.open("sessions.json", "r")
        except KeyError as exc:
            raise CliError("ZIP does not contain required file: sessions.json") from exc

        with session_file:
            for line_number, raw_line in enumerate(session_file, start=1):
                if not raw_line.strip():
                    continue

                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise CliError(f"Invalid JSON at sessions.json line {line_number}: {exc}") from exc

                if not isinstance(payload, dict):
                    raise CliError(f"Invalid sessions.json line {line_number}: expected JSON object.")

                yield SessionRecord(
                    internal_session_id=_require_string(
                        payload.get("internalSessionId"),
                        f"sessions.json line {line_number} internalSessionId",
                    ),
                    dialog_state=_parse_dialog_state(payload.get("dialogState"), line_number),
                )


def iter_message_dialog_states(zip_path: Path) -> Iterator[tuple[str, int, DialogState | None]]:
    if not zip_path.exists():
        raise CliError(f"ZIP file not found: {zip_path}")

    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise CliError(f"Invalid ZIP file: {zip_path}") from exc

    with archive:
        try:
            message_file = archive.open("messages.json", "r")
        except KeyError as exc:
            raise CliError("ZIP does not contain required file: messages.json") from exc

        with message_file:
            for line_number, raw_line in enumerate(message_file, start=1):
                if not raw_line.strip():
                    continue

                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise CliError(f"Invalid JSON at messages.json line {line_number}: {exc}") from exc

                if not isinstance(payload, dict):
                    raise CliError(f"Invalid messages.json line {line_number}: expected JSON object.")

                time_value = payload.get("time")
                if not isinstance(time_value, int):
                    raise CliError(f"Missing required integer in messages.json line {line_number} time.")

                yield (
                    _require_string(
                        payload.get("internalSessionId"),
                        f"messages.json line {line_number} internalSessionId",
                    ),
                    time_value,
                    _parse_dialog_state(payload.get("dialogState"), line_number),
                )


def iter_message_records(zip_path: Path) -> Iterator[MessageRecord]:
    if not zip_path.exists():
        raise CliError(f"ZIP file not found: {zip_path}")

    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise CliError(f"Invalid ZIP file: {zip_path}") from exc

    with archive:
        try:
            message_file = archive.open("messages.json", "r")
        except KeyError as exc:
            raise CliError("ZIP does not contain required file: messages.json") from exc

        with message_file:
            for line_number, raw_line in enumerate(message_file, start=1):
                if not raw_line.strip():
                    continue

                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise CliError(f"Invalid JSON at messages.json line {line_number}: {exc}") from exc

                if not isinstance(payload, dict):
                    raise CliError(f"Invalid messages.json line {line_number}: expected JSON object.")

                time_value = payload.get("time")
                if not isinstance(time_value, int):
                    raise CliError(f"Missing required integer in messages.json line {line_number} time.")

                row_id = payload.get("id")
                if not isinstance(row_id, int):
                    raise CliError(f"Missing required integer in messages.json line {line_number} id.")

                message = payload.get("message")
                if message is None:
                    message = ""
                if not isinstance(message, str):
                    raise CliError(f"Invalid message in messages.json line {line_number}: expected string or null.")

                internal_session_id = _require_string(
                    payload.get("internalSessionId"),
                    f"messages.json line {line_number} internalSessionId",
                )
                command_details = _parse_json_list(payload.get("commands"))

                yield MessageRecord(
                    session_id=_optional_string(payload.get("sessionId")) or internal_session_id,
                    internal_session_id=internal_session_id,
                    row_id=row_id,
                    time=time_value,
                    message=message,
                    tags=_parse_tags(payload.get("tags"), f"messages.json line {line_number} tags"),
                    bot_messages=_parse_tags(payload.get("botMessages"), f"messages.json line {line_number} botMessages"),
                    commands=_parse_command_types(command_details),
                    command_details=command_details,
                    nlu_models=payload.get("nluModels"),
                    process_time=_optional_int(payload.get("processTime")),
                    nlu_time=_optional_int(payload.get("nluTime")),
                    integrations_time=_optional_int(payload.get("integrationsTime")),
                    extra_data=payload.get("extraData"),
                    conversation_metadata=payload.get("conversationMetadata"),
                    error=payload.get("error"),
                    quick_replies=_parse_json_list(payload.get("quickReplies")),
                    bot_messages_created_at=_parse_json_list(payload.get("botMessagesCreatedAt")),
                    dialog_state=_parse_dialog_state(payload.get("dialogState"), line_number),
                )
