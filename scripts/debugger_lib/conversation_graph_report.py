from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
from pathlib import Path
import subprocess
import tempfile

from .io import CliError, iter_message_records
from .interactive_graph_html import write_interactive_graph_html
from .models import MessageRecord

START_NODE_ID = "__start__"
START_NODE_NAME = "Start"


@dataclass(frozen=True)
class GraphNode:
    block_id: str
    block_name: str
    context_name: str
    turns: int
    runs: int
    sessions: int
    fallback_rate: float
    quick_reply_offers: int
    quick_reply_rate: float


@dataclass(frozen=True)
class GraphEdge:
    source_block_id: str
    destination_block_id: str
    transition_count: int
    outgoing_percentage: float


@dataclass(frozen=True)
class ConversationGraphData:
    total_sessions: int
    total_nodes: int
    total_edges: int
    include_start_node: bool
    show_context_labels: bool
    nodes: dict[str, GraphNode]
    edges: list[GraphEdge]


@dataclass(frozen=True)
class ConversationGraphSummary:
    total_sessions: int
    total_nodes: int
    total_edges: int
    filtered_nodes: int
    filtered_edges: int
    output_path: Path
    dot_output_path: Path | None


@dataclass(frozen=True)
class _HtmlBlockRun:
    internal_session_id: str
    block_id: str
    rows: tuple[MessageRecord, ...]
    previous_rows: tuple[MessageRecord | None, ...]
    previous_block_id: str | None
    next_block_id: str | None


@dataclass(frozen=True)
class _SampleOccurrence:
    row: MessageRecord
    kind: str
    bot_message_index: int | None = None


class _ConversationSampleIndex:
    def __init__(self, session_rows: dict[str, tuple[MessageRecord, ...]], *, sample_limit: int = 3) -> None:
        self._session_rows = session_rows
        self._sample_limit = sample_limit
        self._candidates: defaultdict[str, list[_SampleOccurrence]] = defaultdict(list)
        self._metadata: dict[str, tuple[str, str]] = {}

    def key_for(self, scope: str, section_title: str, label: str) -> str:
        digest = hashlib.sha1(f"{scope}\0{section_title}\0{label}".encode("utf-8")).hexdigest()[:16]
        return f"sample-{digest}"

    def add(
        self,
        *,
        scope: str,
        section_title: str,
        label: str,
        row: MessageRecord,
        kind: str,
        bot_message_index: int | None = None,
    ) -> None:
        if not label:
            return

        sample_key = self.key_for(scope, section_title, label)
        self._metadata[sample_key] = (section_title, label)
        self._candidates[sample_key].append(
            _SampleOccurrence(row=row, kind=kind, bot_message_index=bot_message_index)
        )

    def keys_for(self, scope: str, section_title: str, counter: Counter[str]) -> dict[str, str]:
        sample_keys: dict[str, str] = {}
        for label in counter:
            sample_key = self.key_for(scope, section_title, label)
            if sample_key in self._candidates:
                sample_keys[label] = sample_key
        return sample_keys

    def build_payload(self) -> tuple[dict[str, object], dict[str, object]]:
        sample_conversations: dict[str, object] = {}
        sample_sessions: dict[str, object] = {}

        for sample_key, candidates in self._candidates.items():
            section_title, label = self._metadata[sample_key]
            samples: list[dict[str, object]] = []
            seen_sessions: set[str] = set()

            for candidate in candidates:
                internal_session_id = candidate.row.internal_session_id
                if internal_session_id in seen_sessions:
                    continue
                session_rows = self._session_rows.get(internal_session_id)
                if not session_rows:
                    continue

                seen_sessions.add(internal_session_id)
                sample_sessions.setdefault(
                    internal_session_id,
                    _serialize_sample_session(internal_session_id, session_rows),
                )
                selected: dict[str, object] = {
                    "rowId": candidate.row.row_id,
                    "kind": candidate.kind,
                }
                if candidate.bot_message_index is not None:
                    selected["botMessageIndex"] = candidate.bot_message_index

                samples.append(
                    {
                        "sessionId": candidate.row.session_id,
                        "internalSessionId": internal_session_id,
                        "selected": selected,
                    }
                )
                if len(samples) >= self._sample_limit:
                    break

            if samples:
                sample_conversations[sample_key] = {
                    "section": section_title,
                    "message": label,
                    "samples": samples,
                }

        return sample_conversations, sample_sessions


def _preferred_name(name_counts: Counter[str]) -> str:
    return sorted(name_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _preferred_context_name(context_counts: Counter[str]) -> str:
    if not context_counts:
        return ""
    return sorted(context_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _scale(value: int, *, smallest: int, largest: int, minimum: float, maximum: float) -> float:
    if largest == smallest:
        return (minimum + maximum) / 2.0

    ratio = (value - smallest) / (largest - smallest)
    return minimum + ratio * (maximum - minimum)


def _escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _clean_phrase(value: str) -> str:
    return value.strip()


def _flatten_string_values(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []

    values: list[str] = []
    for item in value:
        if isinstance(item, (list, tuple)):
            values.extend(_flatten_string_values(item))
        elif isinstance(item, str):
            cleaned_item = _clean_phrase(item)
            if cleaned_item:
                values.append(cleaned_item)
    return values


def _turn_uses_quick_reply(row: MessageRecord, previous_row: MessageRecord | None) -> bool:
    if previous_row is None:
        return False

    message = _clean_phrase(row.message)
    if not message:
        return False

    return message in set(_flatten_string_values(previous_row.quick_replies))


def _previous_row_offered_quick_reply(previous_row: MessageRecord | None) -> bool:
    return bool(previous_row is not None and _flatten_string_values(previous_row.quick_replies))


def _serialize_dialog_state(dialog_state: object) -> dict[str, object] | None:
    if dialog_state is None:
        return None

    serialized: dict[str, object] = {
        "id": dialog_state.block_id,
        "name": dialog_state.block_name,
    }
    if dialog_state.context:
        serialized["context"] = dialog_state.context
    if dialog_state.context_uuid:
        serialized["contextUuid"] = dialog_state.context_uuid
    if dialog_state.tags:
        serialized["tags"] = list(dialog_state.tags)
    return serialized


def _serialize_sample_row(row: MessageRecord) -> dict[str, object]:
    return {
        "rowId": row.row_id,
        "time": row.time,
        "sessionId": row.session_id,
        "internalSessionId": row.internal_session_id,
        "dialogState": _serialize_dialog_state(row.dialog_state),
        "userMessage": row.message,
        "botMessages": list(row.bot_messages),
        "botMessagesCreatedAt": list(row.bot_messages_created_at),
        "commands": list(row.command_details),
        "tags": list(row.tags),
        "nluModels": row.nlu_models,
        "timing": {
            "processTime": row.process_time,
            "nluTime": row.nlu_time,
            "integrationsTime": row.integrations_time,
        },
        "extraData": row.extra_data,
        "conversationMetadata": row.conversation_metadata,
        "error": row.error,
        "quickReplies": list(row.quick_replies),
    }


def _serialize_sample_session(internal_session_id: str, rows: tuple[MessageRecord, ...]) -> dict[str, object]:
    session_id = rows[0].session_id if rows else internal_session_id
    return {
        "sessionId": session_id,
        "internalSessionId": internal_session_id,
        "rows": [_serialize_sample_row(row) for row in rows],
    }


def _build_start_edge(
    destination_block_id: str,
    transition_count: int,
    total_sessions: int,
) -> GraphEdge:
    outgoing_percentage = (transition_count / total_sessions) if total_sessions else 0.0
    return GraphEdge(
        source_block_id=START_NODE_ID,
        destination_block_id=destination_block_id,
        transition_count=transition_count,
        outgoing_percentage=outgoing_percentage,
    )


def _build_transition_edge(
    source_block_id: str,
    destination_block_id: str,
    transition_count: int,
    source_run_count: int,
) -> GraphEdge:
    outgoing_percentage = (transition_count / source_run_count) if source_run_count else 0.0
    return GraphEdge(
        source_block_id=source_block_id,
        destination_block_id=destination_block_id,
        transition_count=transition_count,
        outgoing_percentage=outgoing_percentage,
    )


def _load_block_run_details(
    zip_path: Path,
) -> tuple[dict[str, list[_HtmlBlockRun]], dict[str, str], dict[str, tuple[MessageRecord, ...]]]:
    session_rows: defaultdict[str, list[MessageRecord]] = defaultdict(list)
    block_name_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)

    for record in iter_message_records(zip_path):
        session_rows[record.internal_session_id].append(record)
        if record.dialog_state is not None:
            block_name_counts[record.dialog_state.block_id][record.dialog_state.block_name] += 1

    block_display_names = {
        block_id: _preferred_name(name_counts)
        for block_id, name_counts in block_name_counts.items()
    }

    session_runs: dict[str, list[_HtmlBlockRun]] = {}
    sorted_session_rows: dict[str, tuple[MessageRecord, ...]] = {}
    for internal_session_id, rows in session_rows.items():
        rows.sort(key=lambda row: (row.time, row.row_id))
        sorted_session_rows[internal_session_id] = tuple(rows)
        previous_row_by_row_id: dict[int, MessageRecord | None] = {}
        previous_row: MessageRecord | None = None
        for row in rows:
            previous_row_by_row_id[row.row_id] = previous_row
            previous_row = row

        non_null_rows = [row for row in rows if row.dialog_state is not None]
        if not non_null_rows:
            session_runs[internal_session_id] = []
            continue

        grouped_runs: list[tuple[str, list[MessageRecord]]] = []
        current_block_id: str | None = None
        current_rows: list[MessageRecord] = []

        for row in non_null_rows:
            block_id = row.dialog_state.block_id
            if block_id == current_block_id:
                current_rows.append(row)
                continue

            if current_block_id is not None:
                grouped_runs.append((current_block_id, current_rows))

            current_block_id = block_id
            current_rows = [row]

        if current_block_id is not None:
            grouped_runs.append((current_block_id, current_rows))

        runs: list[_HtmlBlockRun] = []
        for index, (block_id, run_rows) in enumerate(grouped_runs):
            runs.append(
                _HtmlBlockRun(
                    internal_session_id=internal_session_id,
                    block_id=block_id,
                    rows=tuple(run_rows),
                    previous_rows=tuple(
                        previous_row_by_row_id[row.row_id]
                        for row in run_rows
                    ),
                    previous_block_id=grouped_runs[index - 1][0] if index > 0 else None,
                    next_block_id=grouped_runs[index + 1][0] if index + 1 < len(grouped_runs) else None,
                )
            )
        session_runs[internal_session_id] = runs

    return session_runs, block_display_names, sorted_session_rows


def _format_counter_rows(
    counter: Counter[str],
    *,
    limit: int = 5,
    total: int | None = None,
    sample_keys: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for label, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]:
        if total:
            value = f"{count} ({(count / total) * 100.0:.1f}%)"
        else:
            value = str(count)
        row = {"label": label, "value": value}
        if sample_keys and label in sample_keys:
            row["sampleKey"] = sample_keys[label]
        rows.append(row)
    return rows


def _build_block_html_sections(
    *,
    block_id: str,
    display_names: dict[str, str],
    sample_index: _ConversationSampleIndex | None = None,
    scope: str | None = None,
    previous_blocks: Counter[str],
    previous_user_messages: Counter[str],
    previous_bot_messages: Counter[str],
    next_blocks: Counter[str],
    incoming_phrases: Counter[str],
    outgoing_phrases: Counter[str],
    fallback_phrases: Counter[str],
    block_tags: Counter[str],
    next_bot_messages: Counter[str],
    fallback_bot_messages: Counter[str],
) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = []

    def message_sample_keys(section_title: str, counter: Counter[str]) -> dict[str, str] | None:
        if sample_index is None or scope is None:
            return None
        return sample_index.keys_for(scope, section_title, counter)

    if previous_blocks:
        previous_total = sum(previous_blocks.values())
        sections.append(
            {
                "title": "Previous blocks",
                "rows": _format_counter_rows(
                    Counter(
                        {
                            f"{display_names.get(other_block_id, other_block_id)} ({other_block_id[:8]})": count
                            for other_block_id, count in previous_blocks.items()
                        }
                    ),
                    total=previous_total,
                ),
            }
        )

    if previous_user_messages:
        title = "Previous user messages"
        sections.append(
            {
                "title": title,
                "rows": _format_counter_rows(
                    previous_user_messages,
                    total=sum(previous_user_messages.values()),
                    sample_keys=message_sample_keys(title, previous_user_messages),
                ),
            }
        )

    if previous_bot_messages:
        title = "Bot messages"
        sections.append(
            {
                "title": title,
                "rows": _format_counter_rows(
                    previous_bot_messages,
                    total=sum(previous_bot_messages.values()),
                    sample_keys=message_sample_keys(title, previous_bot_messages),
                ),
            }
        )

    if incoming_phrases:
        title = "User replies"
        sections.append(
            {
                "title": title,
                "rows": _format_counter_rows(
                    incoming_phrases,
                    total=sum(incoming_phrases.values()),
                    sample_keys=message_sample_keys(title, incoming_phrases),
                ),
            }
        )

    if next_bot_messages:
        title = "Next bot messages"
        sections.append(
            {
                "title": title,
                "rows": _format_counter_rows(
                    next_bot_messages,
                    total=sum(next_bot_messages.values()),
                    sample_keys=message_sample_keys(title, next_bot_messages),
                ),
            }
        )

    if block_tags:
        sections.append(
            {
                "title": "Tags",
                "rows": _format_counter_rows(block_tags, total=sum(block_tags.values())),
            }
        )

    if outgoing_phrases:
        title = "Non-fallback user messages"
        sections.append(
            {
                "title": title,
                "rows": _format_counter_rows(
                    outgoing_phrases,
                    total=sum(outgoing_phrases.values()),
                    sample_keys=message_sample_keys(title, outgoing_phrases),
                ),
            }
        )
 
    if fallback_phrases:
        title = "Fallback user messages"
        sections.append(
            {
                "title": title,
                "rows": _format_counter_rows(
                    fallback_phrases,
                    total=sum(fallback_phrases.values()),
                    sample_keys=message_sample_keys(title, fallback_phrases),
                ),
            }
        )

    if fallback_bot_messages:
        title = "Fallback bot replies"
        sections.append(
            {
                "title": title,
                "rows": _format_counter_rows(
                    fallback_bot_messages,
                    total=sum(fallback_bot_messages.values()),
                    sample_keys=message_sample_keys(title, fallback_bot_messages),
                ),
            }
        )

    if next_blocks:
        next_total = sum(next_blocks.values())
        sections.append(
            {
                "title": "Next blocks",
                "rows": _format_counter_rows(
                    Counter(
                        {
                            f"{display_names.get(other_block_id, other_block_id)} ({other_block_id[:8]})": count
                            for other_block_id, count in next_blocks.items()
                        }
                    ),
                    total=next_total,
                ),
            }
        )

    if not sections:
        sections.append(
            {
                "title": "Details",
                "rows": [{"label": "No additional detail", "value": "No drilldown summary available."}],
            }
        )

    return sections


def build_conversation_graph_data(
    zip_path: Path,
    *,
    min_node_turns: int = 1,
    min_edge_count: int = 1,
    min_edge_percent: float = 0.0,
    top_outgoing: int | None = None,
) -> ConversationGraphData:
    session_rows: defaultdict[str, list[MessageRecord]] = defaultdict(list)
    block_name_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    block_context_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    observed_context_names: set[str] = set()

    for record in iter_message_records(zip_path):
        session_rows[record.internal_session_id].append(record)
        if record.dialog_state is not None:
            block_name_counts[record.dialog_state.block_id][record.dialog_state.block_name] += 1
            if record.dialog_state.context:
                block_context_counts[record.dialog_state.block_id][record.dialog_state.context] += 1
                observed_context_names.add(record.dialog_state.context)

    block_turn_counts: Counter[str] = Counter()
    block_run_counts: Counter[str] = Counter()
    block_session_ids: defaultdict[str, set[str]] = defaultdict(set)
    fallback_run_counts: Counter[str] = Counter()
    quick_reply_offer_counts: Counter[str] = Counter()
    quick_reply_turn_counts: Counter[str] = Counter()
    start_transition_counts: Counter[str] = Counter()
    transition_counts: Counter[tuple[str, str]] = Counter()

    for internal_session_id, rows in session_rows.items():
        rows.sort(key=lambda row: (row.time, row.row_id))
        previous_row: MessageRecord | None = None
        for row in rows:
            if row.dialog_state is not None and _previous_row_offered_quick_reply(previous_row):
                block_id = row.dialog_state.block_id
                quick_reply_offer_counts[block_id] += 1
                if _turn_uses_quick_reply(row, previous_row):
                    quick_reply_turn_counts[block_id] += 1
            previous_row = row

        non_null_rows = [row for row in rows if row.dialog_state is not None]
        if not non_null_rows:
            continue

        grouped_runs: list[tuple[str, list[MessageRecord]]] = []
        current_block_id: str | None = None
        current_rows: list[MessageRecord] = []

        for row in non_null_rows:
            block_id = row.dialog_state.block_id
            if block_id == current_block_id:
                current_rows.append(row)
                continue

            if current_block_id is not None:
                grouped_runs.append((current_block_id, current_rows))

            current_block_id = block_id
            current_rows = [row]

        if current_block_id is not None:
            grouped_runs.append((current_block_id, current_rows))

        if grouped_runs:
            start_transition_counts[grouped_runs[0][0]] += 1

        for block_id, run_rows in grouped_runs:
            block_turn_counts[block_id] += len(run_rows)
            block_run_counts[block_id] += 1
            block_session_ids[block_id].add(internal_session_id)
            if len(run_rows) > 1:
                fallback_run_counts[block_id] += 1

        for index in range(len(grouped_runs) - 1):
            source_block_id = grouped_runs[index][0]
            destination_block_id = grouped_runs[index + 1][0]
            transition_counts[(source_block_id, destination_block_id)] += 1

    kept_node_ids = {
        block_id
        for block_id, turn_count in block_turn_counts.items()
        if turn_count >= min_node_turns
    }

    nodes = {
        block_id: GraphNode(
            block_id=block_id,
            block_name=_preferred_name(block_name_counts[block_id]),
            context_name=_preferred_context_name(block_context_counts[block_id]),
            turns=block_turn_counts[block_id],
            runs=block_run_counts[block_id],
            sessions=len(block_session_ids[block_id]),
            fallback_rate=(fallback_run_counts[block_id] / block_run_counts[block_id]) if block_run_counts[block_id] else 0.0,
            quick_reply_offers=quick_reply_offer_counts[block_id],
            quick_reply_rate=(quick_reply_turn_counts[block_id] / quick_reply_offer_counts[block_id]) if quick_reply_offer_counts[block_id] else 0.0,
        )
        for block_id in sorted(kept_node_ids)
    }

    total_sessions = len(session_rows)
    filtered_edges_by_source: defaultdict[str, list[GraphEdge]] = defaultdict(list)
    for destination_block_id, transition_count in start_transition_counts.items():
        if destination_block_id not in kept_node_ids:
            continue
        if transition_count < min_edge_count:
            continue

        outgoing_total = total_sessions
        outgoing_percentage = (transition_count / outgoing_total) if outgoing_total else 0.0
        if (outgoing_percentage * 100.0) < min_edge_percent:
            continue

        filtered_edges_by_source[START_NODE_ID].append(
            _build_start_edge(destination_block_id, transition_count, total_sessions)
        )

    for (source_block_id, destination_block_id), transition_count in transition_counts.items():
        if source_block_id not in kept_node_ids or destination_block_id not in kept_node_ids:
            continue
        if transition_count < min_edge_count:
            continue

        outgoing_total = block_run_counts[source_block_id]
        outgoing_percentage = (transition_count / outgoing_total) if outgoing_total else 0.0
        if (outgoing_percentage * 100.0) < min_edge_percent:
            continue

        filtered_edges_by_source[source_block_id].append(
            _build_transition_edge(
                source_block_id,
                destination_block_id,
                transition_count,
                block_run_counts[source_block_id],
            )
        )

    edges: list[GraphEdge] = []
    for source_block_id in sorted(filtered_edges_by_source):
        source_edges = sorted(
            filtered_edges_by_source[source_block_id],
            key=lambda edge: (
                -edge.transition_count,
                edge.destination_block_id,
            ),
        )
        if top_outgoing is not None:
            source_edges = source_edges[:top_outgoing]
        edges.extend(source_edges)

    incoming_edge_destinations = {edge.destination_block_id for edge in edges}
    for block_id in sorted(kept_node_ids):
        if block_id in incoming_edge_destinations:
            continue

        incoming_transition_candidates = [
            (source_block_id, transition_count)
            for (source_block_id, destination_block_id), transition_count in transition_counts.items()
            if destination_block_id == block_id and source_block_id in kept_node_ids
        ]
        if incoming_transition_candidates:
            source_block_id, transition_count = sorted(
                incoming_transition_candidates,
                key=lambda item: (-item[1], item[0]),
            )[0]
            edges.append(
                _build_transition_edge(
                    source_block_id,
                    block_id,
                    transition_count,
                    block_run_counts[source_block_id],
                )
            )
            continue

        start_transition_count = start_transition_counts.get(block_id, 0)
        if start_transition_count <= 0:
            continue

        edges.append(_build_start_edge(block_id, start_transition_count, total_sessions))

    return ConversationGraphData(
        total_sessions=total_sessions,
        total_nodes=len(block_turn_counts) + (1 if start_transition_counts else 0),
        total_edges=len(transition_counts) + len(start_transition_counts),
        include_start_node=bool(start_transition_counts),
        show_context_labels=len(observed_context_names) > 1,
        nodes=nodes,
        edges=edges,
    )


def _render_dot(data: ConversationGraphData) -> str:
    node_turn_values = [node.turns for node in data.nodes.values()]
    smallest_turn_count = min(node_turn_values, default=1)
    largest_turn_count = max(node_turn_values, default=1)

    lines = [
        "digraph conversation_graph {",
        '  graph [rankdir=LR, overlap=false, splines=true, pad="0.2"];',
        '  node [shape=ellipse, style="filled", fillcolor="#d7ecff", color="#4a6fa5", fontname="Helvetica"];',
        '  edge [color="#6b7280", fontname="Helvetica", fontsize=10];',
    ]

    if data.include_start_node:
        start_label = f"{START_NODE_NAME}\nSessions: {data.total_sessions}"
        lines.append(
            f'  "{START_NODE_ID}" [label="{_escape_dot(start_label)}", shape=circle, width=1.3, height=1.3, fontsize=12.0, fillcolor="#f3f4f6", color="#6b7280"];'
        )

    for block_id in sorted(data.nodes):
        node = data.nodes[block_id]
        width = _scale(
            node.turns,
            smallest=smallest_turn_count,
            largest=largest_turn_count,
            minimum=1.2,
            maximum=3.0,
        )
        fontsize = _scale(
            node.turns,
            smallest=smallest_turn_count,
            largest=largest_turn_count,
            minimum=10.0,
            maximum=18.0,
        )
        label = (
            f"{node.block_name}\n"
            f"{node.block_id[:8]}\n"
            f"Turns: {node.turns} | Runs: {node.runs}\n"
            f"Fallback: {node.fallback_rate * 100.0:.1f}%\n"
            f"Quick replies: {node.quick_reply_rate * 100.0:.1f}% ({node.quick_reply_offers})"
        )
        lines.append(
            f'  "{_escape_dot(block_id)}" [label="{_escape_dot(label)}", width={width:.2f}, height={width:.2f}, fontsize={fontsize:.1f}];'
        )

    for edge in data.edges:
        label = f"{edge.outgoing_percentage * 100.0:.1f}% ({edge.transition_count})"
        penwidth = _scale(
            edge.transition_count,
            smallest=min((item.transition_count for item in data.edges), default=1),
            largest=max((item.transition_count for item in data.edges), default=1),
            minimum=1.2,
            maximum=4.0,
        )
        lines.append(
            f'  "{_escape_dot(edge.source_block_id)}" -> "{_escape_dot(edge.destination_block_id)}" '
            f'[label="{label}", penwidth={penwidth:.2f}];'
        )

    lines.append("}")
    return "\n".join(lines) + "\n"


def create_conversation_graph_report(
    zip_path: Path,
    output_path: Path,
    *,
    min_node_turns: int = 1,
    min_edge_count: int = 1,
    min_edge_percent: float = 0.0,
    top_outgoing: int | None = None,
    dot_output_path: Path | None = None,
) -> ConversationGraphSummary:
    if min_node_turns < 1:
        raise CliError("--min-node-turns must be at least 1.")
    if min_edge_count < 1:
        raise CliError("--min-edge-count must be at least 1.")
    if min_edge_percent < 0.0:
        raise CliError("--min-edge-percent cannot be negative.")
    if top_outgoing is not None and top_outgoing < 1:
        raise CliError("--top-outgoing must be at least 1 when provided.")

    data = build_conversation_graph_data(
        zip_path,
        min_node_turns=min_node_turns,
        min_edge_count=min_edge_count,
        min_edge_percent=min_edge_percent,
        top_outgoing=top_outgoing,
    )
    dot_content = _render_dot(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if dot_output_path is not None:
        dot_output_path.parent.mkdir(parents=True, exist_ok=True)
        dot_output_path.write_text(dot_content, encoding="utf-8")
        dot_path = dot_output_path
    else:
        with tempfile.NamedTemporaryFile("w", suffix=".dot", delete=False, encoding="utf-8") as handle:
            handle.write(dot_content)
            dot_path = Path(handle.name)

    try:
        try:
            subprocess.run(
                ["dot", "-Tsvg", str(dot_path), "-o", str(output_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise CliError("Graphviz 'dot' command is not installed on this machine.") from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else str(exc)
            raise CliError(f"Graphviz rendering failed: {stderr}") from exc
    finally:
        if dot_output_path is None and dot_path.exists():
            dot_path.unlink()

    return ConversationGraphSummary(
        total_sessions=data.total_sessions,
        total_nodes=data.total_nodes,
        total_edges=data.total_edges,
        filtered_nodes=len(data.nodes) + (1 if data.include_start_node else 0),
        filtered_edges=len(data.edges),
        output_path=output_path,
        dot_output_path=dot_output_path,
    )


def create_conversation_graph_html_report(
    zip_path: Path,
    output_path: Path,
    *,
    min_node_turns: int = 1,
    min_edge_count: int = 1,
    min_edge_percent: float = 0.0,
    top_outgoing: int | None = None,
) -> ConversationGraphSummary:
    data = build_conversation_graph_data(
        zip_path,
        min_node_turns=min_node_turns,
        min_edge_count=min_edge_count,
        min_edge_percent=min_edge_percent,
        top_outgoing=top_outgoing,
    )
    session_runs, display_names, session_rows = _load_block_run_details(zip_path)
    sample_index = _ConversationSampleIndex(session_rows)

    incoming_phrases_by_block: defaultdict[str, Counter[str]] = defaultdict(Counter)
    outgoing_phrases_by_block: defaultdict[str, Counter[str]] = defaultdict(Counter)
    fallback_phrases_by_block: defaultdict[str, Counter[str]] = defaultdict(Counter)
    previous_user_messages_by_block: defaultdict[str, Counter[str]] = defaultdict(Counter)
    previous_bot_messages_by_block: defaultdict[str, Counter[str]] = defaultdict(Counter)
    block_tags_by_block: defaultdict[str, Counter[str]] = defaultdict(Counter)
    next_bot_messages_by_block: defaultdict[str, Counter[str]] = defaultdict(Counter)
    fallback_bot_messages_by_block: defaultdict[str, Counter[str]] = defaultdict(Counter)
    previous_blocks_by_block: defaultdict[str, Counter[str]] = defaultdict(Counter)
    next_blocks_by_block: defaultdict[str, Counter[str]] = defaultdict(Counter)

    edge_session_ids: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    edge_source_bot_messages: defaultdict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    edge_user_messages: defaultdict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    edge_destination_bot_messages: defaultdict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for runs in session_runs.values():
        for index, run in enumerate(runs):
            node_scope = f"node:{run.block_id}"
            for previous_row in run.previous_rows:
                if previous_row is None:
                    continue
                for tag in previous_row.tags:
                    cleaned_tag = _clean_phrase(tag)
                    if cleaned_tag:
                        block_tags_by_block[run.block_id][cleaned_tag] += 1
            for row in run.rows:
                for bot_message_index, bot_message in enumerate(row.bot_messages):
                    cleaned_bot_message = _clean_phrase(bot_message)
                    if cleaned_bot_message:
                        next_bot_messages_by_block[run.block_id][cleaned_bot_message] += 1
                        sample_index.add(
                            scope=node_scope,
                            section_title="Next bot messages",
                            label=cleaned_bot_message,
                            row=row,
                            kind="bot",
                            bot_message_index=bot_message_index,
                        )

            for row in run.rows:
                phrase = _clean_phrase(row.message)
                if phrase:
                    incoming_phrases_by_block[run.block_id][phrase] += 1
                    sample_index.add(
                        scope=node_scope,
                        section_title="User replies",
                        label=phrase,
                        row=row,
                        kind="user",
                    )

            if run.previous_block_id is not None:
                previous_blocks_by_block[run.block_id][run.previous_block_id] += 1
                previous_row = runs[index - 1].rows[-1]
                previous_message = _clean_phrase(previous_row.message)
                if previous_message:
                    previous_user_messages_by_block[run.block_id][previous_message] += 1
                    sample_index.add(
                        scope=node_scope,
                        section_title="Previous user messages",
                        label=previous_message,
                        row=previous_row,
                        kind="user",
                    )

            for previous_row in run.previous_rows:
                if previous_row is None:
                    continue
                for bot_message_index, bot_message in enumerate(previous_row.bot_messages):
                    cleaned_bot_message = _clean_phrase(bot_message)
                    if cleaned_bot_message:
                        previous_bot_messages_by_block[run.block_id][cleaned_bot_message] += 1
                        sample_index.add(
                            scope=node_scope,
                            section_title="Bot messages",
                            label=cleaned_bot_message,
                            row=previous_row,
                            kind="bot",
                            bot_message_index=bot_message_index,
                        )

            if run.next_block_id is not None:
                next_blocks_by_block[run.block_id][run.next_block_id] += 1
                last_phrase = _clean_phrase(run.rows[-1].message)
                if last_phrase:
                    outgoing_phrases_by_block[run.block_id][last_phrase] += 1
                    sample_index.add(
                        scope=node_scope,
                        section_title="Non-fallback user messages",
                        label=last_phrase,
                        row=run.rows[-1],
                        kind="user",
                    )

                edge_key = (run.block_id, run.next_block_id)
                edge_scope = f"edge:{run.block_id}->{run.next_block_id}"
                edge_session_ids[edge_key].add(run.internal_session_id)
                previous_row = run.previous_rows[-1] if run.previous_rows else None
                if previous_row is not None:
                    for bot_message_index, bot_message in enumerate(previous_row.bot_messages):
                        cleaned_bot_message = _clean_phrase(bot_message)
                        if cleaned_bot_message:
                            edge_source_bot_messages[edge_key][cleaned_bot_message] += 1
                            sample_index.add(
                                scope=edge_scope,
                                section_title="Bot messages before transition",
                                label=cleaned_bot_message,
                                row=previous_row,
                                kind="bot",
                                bot_message_index=bot_message_index,
                            )
                last_phrase = _clean_phrase(run.rows[-1].message)
                if last_phrase:
                    edge_user_messages[edge_key][last_phrase] += 1
                    sample_index.add(
                        scope=edge_scope,
                        section_title="User messages before transition",
                        label=last_phrase,
                        row=run.rows[-1],
                        kind="user",
                    )
                for bot_message_index, bot_message in enumerate(run.rows[-1].bot_messages):
                    cleaned_bot_message = _clean_phrase(bot_message)
                    if cleaned_bot_message:
                        edge_destination_bot_messages[edge_key][cleaned_bot_message] += 1
                        sample_index.add(
                            scope=edge_scope,
                            section_title="Bot replies in destination block",
                            label=cleaned_bot_message,
                            row=run.rows[-1],
                            kind="bot",
                            bot_message_index=bot_message_index,
                        )

            if len(run.rows) > 1:
                for row in run.rows[:-1]:
                    fallback_phrase = _clean_phrase(row.message)
                    if fallback_phrase:
                        fallback_phrases_by_block[run.block_id][fallback_phrase] += 1
                        sample_index.add(
                            scope=node_scope,
                            section_title="Fallback user messages",
                            label=fallback_phrase,
                            row=row,
                            kind="user",
                        )
                    for bot_message_index, bot_message in enumerate(row.bot_messages):
                        cleaned_bot_message = _clean_phrase(bot_message)
                        if cleaned_bot_message:
                            fallback_bot_messages_by_block[run.block_id][cleaned_bot_message] += 1
                            sample_index.add(
                                scope=node_scope,
                                section_title="Fallback bot replies",
                                label=cleaned_bot_message,
                                row=row,
                                kind="bot",
                                bot_message_index=bot_message_index,
                            )

    nodes = []
    if data.include_start_node:
        nodes.append(
            {
                "id": START_NODE_ID,
                "label": START_NODE_NAME,
                "detail": f"{START_NODE_NAME} | Sessions: {data.total_sessions}",
                "turns": data.total_sessions,
                "isStart": True,
                "title": START_NODE_NAME,
                "metrics": {
                    "Sessions": data.total_sessions,
                },
                "sections": [
                    {
                        "title": "Meaning",
                        "rows": [
                            {
                                "label": "Definition",
                                "value": "Represents all exported conversations before the first resolved block is recorded in messages.json.",
                            }
                        ],
                    }
                ],
            }
        )

    for block_id in sorted(data.nodes):
        node = data.nodes[block_id]
        node_scope = f"node:{block_id}"
        label_lines = [node.block_name, block_id[:8]]
        if data.show_context_labels and node.context_name:
            label_lines.insert(0, node.context_name)
        nodes.append(
            {
                "id": block_id,
                "label": "\n".join(label_lines),
                "detail": f"{node.block_name} {block_id}",
                "turns": node.turns,
                "fallbackRate": node.fallback_rate * 100.0,
                "quickReplyRate": node.quick_reply_rate * 100.0,
                "isStart": False,
                "title": node.block_name,
                "metrics": {
                    "Block id": block_id,
                    "Context name": node.context_name or "Not available",
                    "Turns": node.turns,
                    "Runs": node.runs,
                    "Sessions": node.sessions,
                    "Fallback rate": f"{node.fallback_rate * 100.0:.1f}%",
                    "Quick Reply offers": node.quick_reply_offers,
                    "Quick Reply Rate": f"{node.quick_reply_rate * 100.0:.1f}%",
                },
                "sections": _build_block_html_sections(
                    block_id=block_id,
                    display_names=display_names,
                    sample_index=sample_index,
                    scope=node_scope,
                    previous_blocks=previous_blocks_by_block[block_id],
                    previous_user_messages=previous_user_messages_by_block[block_id],
                    previous_bot_messages=previous_bot_messages_by_block[block_id],
                    next_blocks=next_blocks_by_block[block_id],
                    incoming_phrases=incoming_phrases_by_block[block_id],
                    outgoing_phrases=outgoing_phrases_by_block[block_id],
                    fallback_phrases=fallback_phrases_by_block[block_id],
                    block_tags=block_tags_by_block[block_id],
                    next_bot_messages=next_bot_messages_by_block[block_id],
                    fallback_bot_messages=fallback_bot_messages_by_block[block_id],
                ),
            }
        )

    edges = []
    for edge in data.edges:
        edge_key = (edge.source_block_id, edge.destination_block_id)
        edge_scope = f"edge:{edge.source_block_id}->{edge.destination_block_id}"
        if edge.source_block_id == START_NODE_ID:
            source_label = START_NODE_NAME
        else:
            source_label = display_names.get(edge.source_block_id, edge.source_block_id)
        target_label = display_names.get(edge.destination_block_id, edge.destination_block_id)
        title = f"{source_label} -> {target_label}"
        edges.append(
            {
                "source": edge.source_block_id,
                "target": edge.destination_block_id,
                "count": edge.transition_count,
                "percent": edge.outgoing_percentage * 100.0,
                "label": f"{edge.outgoing_percentage * 100.0:.1f}% ({edge.transition_count})",
                "title": title,
                "metrics": {
                    "Transitions": edge.transition_count,
                    "Sessions with transition": len(edge_session_ids[edge_key]),
                    "Outgoing percentage": f"{edge.outgoing_percentage * 100.0:.1f}%",
                    "Source": f"{source_label} ({edge.source_block_id[:8]})" if edge.source_block_id != START_NODE_ID else source_label,
                    "Target": f"{target_label} ({edge.destination_block_id[:8]})",
                },
                "sections": [
                    {
                        "title": "Bot messages before transition",
                        "rows": _format_counter_rows(
                            edge_source_bot_messages[edge_key],
                            total=sum(edge_source_bot_messages[edge_key].values()),
                            sample_keys=sample_index.keys_for(
                                edge_scope,
                                "Bot messages before transition",
                                edge_source_bot_messages[edge_key],
                            ),
                        ) or [{"label": "No bot message", "value": "No source-block bot message was available for this transition."}],
                    },
                    {
                        "title": "User messages before transition",
                        "rows": _format_counter_rows(
                            edge_user_messages[edge_key],
                            total=sum(edge_user_messages[edge_key].values()),
                            sample_keys=sample_index.keys_for(
                                edge_scope,
                                "User messages before transition",
                                edge_user_messages[edge_key],
                            ),
                        ) or [{"label": "No user message", "value": "No user message was recorded on the last turn of the source block run for this transition."}],
                    },
                    {
                        "title": "Bot replies in destination block",
                        "rows": _format_counter_rows(
                            edge_destination_bot_messages[edge_key],
                            total=sum(edge_destination_bot_messages[edge_key].values()),
                            sample_keys=sample_index.keys_for(
                                edge_scope,
                                "Bot replies in destination block",
                                edge_destination_bot_messages[edge_key],
                            ),
                        ) or [{"label": "No bot reply", "value": "No bot reply was recorded on the first turn of the destination block run for this transition."}],
                    },
                ],
            }
        )

    sample_conversations, sample_sessions = sample_index.build_payload()
    write_interactive_graph_html(
        output_path=output_path,
        title="Conversation Block Graph",
        graph_kind_label="Blocks",
        node_metric_label="Minimum turns",
        node_metric_key="turns",
        total_sessions=data.total_sessions,
        total_nodes=data.total_nodes,
        total_edges=data.total_edges,
        nodes=nodes,
        edges=edges,
        sample_conversations=sample_conversations,
        sample_sessions=sample_sessions,
    )

    return ConversationGraphSummary(
        total_sessions=data.total_sessions,
        total_nodes=data.total_nodes,
        total_edges=data.total_edges,
        filtered_nodes=len(nodes),
        filtered_edges=len(edges),
        output_path=output_path,
        dot_output_path=None,
    )
