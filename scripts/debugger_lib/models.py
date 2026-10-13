from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DialogState:
    block_id: str
    block_name: str
    context: str | None = None
    context_uuid: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionRecord:
    internal_session_id: str
    dialog_state: DialogState | None


@dataclass(frozen=True)
class MessageRecord:
    session_id: str
    internal_session_id: str
    row_id: int
    time: int
    message: str
    tags: tuple[str, ...]
    bot_messages: tuple[str, ...]
    commands: tuple[str, ...]
    command_details: tuple[object, ...]
    nlu_models: object
    process_time: int | None
    nlu_time: int | None
    integrations_time: int | None
    extra_data: object
    conversation_metadata: object
    error: object
    quick_replies: tuple[object, ...]
    bot_messages_created_at: tuple[object, ...]
    dialog_state: DialogState | None
