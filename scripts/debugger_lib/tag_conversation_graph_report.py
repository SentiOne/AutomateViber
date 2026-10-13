from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import subprocess
import tempfile

from openpyxl import Workbook
from openpyxl.styles import Font

from .conversation_graph_report import START_NODE_ID, START_NODE_NAME
from .interactive_graph_html import write_interactive_graph_html
from .io import CliError, iter_message_records
from .models import MessageRecord


END_COMMAND_TYPES = frozenset({"disconnect", "redirect"})


@dataclass(frozen=True)
class TagGraphNode:
    tag: str
    occurrences: int
    runs: int
    sessions: int
    drop_runs: int
    fallback_rate: float
    drop_rate: float
    terminal_sessions: int
    terminal_rate: float


@dataclass(frozen=True)
class TagGraphEdge:
    source_tag: str
    destination_tag: str
    transition_count: int
    outgoing_percentage: float


@dataclass(frozen=True)
class TagConversationGraphData:
    total_sessions: int
    total_nodes: int
    total_edges: int
    include_start_node: bool
    nodes: dict[str, TagGraphNode]
    edges: list[TagGraphEdge]


@dataclass(frozen=True)
class TagConversationGraphSummary:
    total_sessions: int
    total_nodes: int
    total_edges: int
    filtered_nodes: int
    filtered_edges: int
    output_path: Path
    dot_output_path: Path | None


@dataclass(frozen=True)
class TagDropTerminalSummary:
    total_sessions: int
    total_tags: int
    output_path: Path


def _scale(value: int, *, smallest: int, largest: int, minimum: float, maximum: float) -> float:
    if largest == smallest:
        return (minimum + maximum) / 2.0

    ratio = (value - smallest) / (largest - smallest)
    return minimum + ratio * (maximum - minimum)


def _escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _build_start_edge(destination_tag: str, transition_count: int, total_sessions: int) -> TagGraphEdge:
    outgoing_percentage = (transition_count / total_sessions) if total_sessions else 0.0
    return TagGraphEdge(
        source_tag=START_NODE_ID,
        destination_tag=destination_tag,
        transition_count=transition_count,
        outgoing_percentage=outgoing_percentage,
    )


def _build_transition_edge(
    source_tag: str,
    destination_tag: str,
    transition_count: int,
    source_run_count: int,
) -> TagGraphEdge:
    outgoing_percentage = (transition_count / source_run_count) if source_run_count else 0.0
    return TagGraphEdge(
        source_tag=source_tag,
        destination_tag=destination_tag,
        transition_count=transition_count,
        outgoing_percentage=outgoing_percentage,
    )


def _flatten_tag_events(rows: list[MessageRecord]) -> list[tuple[str, int]]:
    rows.sort(key=lambda row: (row.time, row.row_id))

    sequence: list[tuple[str, int]] = []
    for row_index, row in enumerate(rows):
        for tag in row.tags:
            sequence.append((tag, row_index))
    return sequence


def _has_later_user_message(rows: list[MessageRecord], row_index: int) -> bool:
    return any(row.message.strip() for row in rows[row_index + 1 :])


def _has_end_command_at_or_after(rows: list[MessageRecord], row_index: int) -> bool:
    for row in rows[row_index:]:
        for command in row.commands:
            if command.strip().lower() in END_COMMAND_TYPES:
                return True
    return False


def build_tag_conversation_graph_data(
    zip_path: Path,
    *,
    min_node_occurrences: int = 1,
    min_edge_count: int = 1,
    min_edge_percent: float = 0.0,
    top_outgoing: int | None = None,
) -> TagConversationGraphData:
    session_rows: defaultdict[str, list[MessageRecord]] = defaultdict(list)
    for record in iter_message_records(zip_path):
        session_rows[record.internal_session_id].append(record)

    tag_occurrence_counts: Counter[str] = Counter()
    tag_run_counts: Counter[str] = Counter()
    tag_session_ids: defaultdict[str, set[str]] = defaultdict(set)
    fallback_run_counts: Counter[str] = Counter()
    drop_run_counts: Counter[str] = Counter()
    terminal_session_ids: defaultdict[str, set[str]] = defaultdict(set)
    start_transition_counts: Counter[str] = Counter()
    transition_counts: Counter[tuple[str, str]] = Counter()

    for internal_session_id, rows in session_rows.items():
        tag_events = _flatten_tag_events(rows)
        if not tag_events:
            continue

        grouped_runs: list[tuple[str, int, int]] = []
        current_tag: str | None = None
        current_count = 0
        current_end_row_index = 0

        for tag, row_index in tag_events:
            if tag == current_tag:
                current_count += 1
                current_end_row_index = row_index
                continue

            if current_tag is not None:
                grouped_runs.append((current_tag, current_count, current_end_row_index))

            current_tag = tag
            current_count = 1
            current_end_row_index = row_index

        if current_tag is not None:
            grouped_runs.append((current_tag, current_count, current_end_row_index))

        if grouped_runs:
            start_transition_counts[grouped_runs[0][0]] += 1
            terminal_tag, _, terminal_end_row_index = grouped_runs[-1]
            if not _has_later_user_message(rows, terminal_end_row_index):
                terminal_session_ids[terminal_tag].add(internal_session_id)
                if not _has_end_command_at_or_after(rows, terminal_end_row_index):
                    drop_run_counts[terminal_tag] += 1

        for tag, occurrence_count, _ in grouped_runs:
            tag_occurrence_counts[tag] += occurrence_count
            tag_run_counts[tag] += 1
            tag_session_ids[tag].add(internal_session_id)
            if occurrence_count > 1:
                fallback_run_counts[tag] += 1

        for index in range(len(grouped_runs) - 1):
            source_tag = grouped_runs[index][0]
            destination_tag = grouped_runs[index + 1][0]
            transition_counts[(source_tag, destination_tag)] += 1

    kept_tags = {
        tag
        for tag, occurrence_count in tag_occurrence_counts.items()
        if occurrence_count >= min_node_occurrences
    }

    nodes = {
        tag: TagGraphNode(
            tag=tag,
            occurrences=tag_occurrence_counts[tag],
            runs=tag_run_counts[tag],
            sessions=len(tag_session_ids[tag]),
            drop_runs=drop_run_counts[tag],
            fallback_rate=(fallback_run_counts[tag] / tag_run_counts[tag]) if tag_run_counts[tag] else 0.0,
            drop_rate=(drop_run_counts[tag] / tag_run_counts[tag]) if tag_run_counts[tag] else 0.0,
            terminal_sessions=len(terminal_session_ids[tag]),
            terminal_rate=(len(terminal_session_ids[tag]) / len(tag_session_ids[tag])) if tag_session_ids[tag] else 0.0,
        )
        for tag in sorted(kept_tags)
    }

    total_sessions = len(session_rows)
    filtered_edges_by_source: defaultdict[str, list[TagGraphEdge]] = defaultdict(list)

    for destination_tag, transition_count in start_transition_counts.items():
        if destination_tag not in kept_tags:
            continue
        if transition_count < min_edge_count:
            continue

        outgoing_percentage = (transition_count / total_sessions) if total_sessions else 0.0
        if (outgoing_percentage * 100.0) < min_edge_percent:
            continue

        filtered_edges_by_source[START_NODE_ID].append(
            _build_start_edge(destination_tag, transition_count, total_sessions)
        )

    for (source_tag, destination_tag), transition_count in transition_counts.items():
        if source_tag not in kept_tags or destination_tag not in kept_tags:
            continue
        if transition_count < min_edge_count:
            continue

        outgoing_percentage = (transition_count / tag_run_counts[source_tag]) if tag_run_counts[source_tag] else 0.0
        if (outgoing_percentage * 100.0) < min_edge_percent:
            continue

        filtered_edges_by_source[source_tag].append(
            _build_transition_edge(source_tag, destination_tag, transition_count, tag_run_counts[source_tag])
        )

    edges: list[TagGraphEdge] = []
    for source_tag in sorted(filtered_edges_by_source):
        source_edges = sorted(
            filtered_edges_by_source[source_tag],
            key=lambda edge: (-edge.transition_count, edge.destination_tag),
        )
        if top_outgoing is not None:
            source_edges = source_edges[:top_outgoing]
        edges.extend(source_edges)

    incoming_edge_destinations = {edge.destination_tag for edge in edges}
    for tag in sorted(kept_tags):
        if tag in incoming_edge_destinations:
            continue

        incoming_transition_candidates = [
            (source_tag, transition_count)
            for (source_tag, destination_tag), transition_count in transition_counts.items()
            if destination_tag == tag and source_tag in kept_tags
        ]
        if incoming_transition_candidates:
            source_tag, transition_count = sorted(
                incoming_transition_candidates,
                key=lambda item: (-item[1], item[0]),
            )[0]
            edges.append(
                _build_transition_edge(source_tag, tag, transition_count, tag_run_counts[source_tag])
            )
            continue

        start_transition_count = start_transition_counts.get(tag, 0)
        if start_transition_count <= 0:
            continue

        edges.append(_build_start_edge(tag, start_transition_count, total_sessions))

    return TagConversationGraphData(
        total_sessions=total_sessions,
        total_nodes=len(tag_occurrence_counts) + (1 if start_transition_counts else 0),
        total_edges=len(transition_counts) + len(start_transition_counts),
        include_start_node=bool(start_transition_counts),
        nodes=nodes,
        edges=edges,
    )


def _render_dot(data: TagConversationGraphData) -> str:
    node_occurrences = [node.occurrences for node in data.nodes.values()]
    smallest_occurrence_count = min(node_occurrences, default=1)
    largest_occurrence_count = max(node_occurrences, default=1)

    lines = [
        "digraph tag_conversation_graph {",
        '  graph [rankdir=LR, overlap=false, splines=true, pad="0.2"];',
        '  node [shape=ellipse, style="filled", fillcolor="#d9fce7", color="#2e7d32", fontname="Helvetica"];',
        '  edge [color="#6b7280", fontname="Helvetica", fontsize=10];',
    ]

    if data.include_start_node:
        start_label = f"{START_NODE_NAME}\nSessions: {data.total_sessions}"
        lines.append(
            f'  "{START_NODE_ID}" [label="{_escape_dot(start_label)}", shape=circle, width=1.3, height=1.3, fontsize=12.0, fillcolor="#f3f4f6", color="#6b7280"];'
        )

    for tag in sorted(data.nodes):
        node = data.nodes[tag]
        width = _scale(
            node.occurrences,
            smallest=smallest_occurrence_count,
            largest=largest_occurrence_count,
            minimum=1.2,
            maximum=3.0,
        )
        fontsize = _scale(
            node.occurrences,
            smallest=smallest_occurrence_count,
            largest=largest_occurrence_count,
            minimum=10.0,
            maximum=18.0,
        )
        label = (
            f"{node.tag}\n"
            f"Occurrences: {node.occurrences} | Runs: {node.runs}\n"
            f"Fallback: {node.fallback_rate * 100.0:.1f}%\n"
            f"Drop: {node.drop_rate * 100.0:.1f}% | Terminal: {node.terminal_rate * 100.0:.1f}%"
        )
        lines.append(
            f'  "{_escape_dot(tag)}" [label="{_escape_dot(label)}", width={width:.2f}, height={width:.2f}, fontsize={fontsize:.1f}];'
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
            f'  "{_escape_dot(edge.source_tag)}" -> "{_escape_dot(edge.destination_tag)}" '
            f'[label="{label}", penwidth={penwidth:.2f}];'
        )

    lines.append("}")
    return "\n".join(lines) + "\n"


def write_tag_drop_terminal_report(data: TagConversationGraphData, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Tag Drop Terminal"
    sheet.freeze_panes = "A2"

    headers = [
        "Tag",
        "Occurrences",
        "Runs",
        "Sessions",
        "Sessions percentage of all sessions",
        "Drop runs",
        "Drop rate",
        "Terminal sessions",
        "Terminal sessions percentage of all sessions",
        "Terminal rate",
    ]
    sheet.append(headers)

    for cell in sheet[1]:
        cell.font = Font(bold=True)

    rows = sorted(
        data.nodes.values(),
        key=lambda node: (
            -node.drop_rate,
            -node.drop_runs,
            -node.terminal_rate,
            -node.terminal_sessions,
            node.tag,
        ),
    )

    for node in rows:
        sheet.append(
            [
                node.tag,
                node.occurrences,
                node.runs,
                node.sessions,
                (node.sessions / data.total_sessions) if data.total_sessions else 0.0,
                node.drop_runs,
                node.drop_rate,
                node.terminal_sessions,
                (node.terminal_sessions / data.total_sessions) if data.total_sessions else 0.0,
                node.terminal_rate,
            ]
        )

    sheet.auto_filter.ref = sheet.dimensions
    sheet.column_dimensions["A"].width = 42
    sheet.column_dimensions["B"].width = 14
    sheet.column_dimensions["C"].width = 12
    sheet.column_dimensions["D"].width = 12
    sheet.column_dimensions["E"].width = 34
    sheet.column_dimensions["F"].width = 14
    sheet.column_dimensions["G"].width = 14
    sheet.column_dimensions["H"].width = 18
    sheet.column_dimensions["I"].width = 38
    sheet.column_dimensions["J"].width = 16

    for column in ("E", "G", "I", "J"):
        for cell in sheet[column][1:]:
            cell.number_format = "0.0%"

    workbook.save(output_path)


def create_tag_drop_terminal_report(zip_path: Path, output_path: Path) -> TagDropTerminalSummary:
    data = build_tag_conversation_graph_data(zip_path)
    write_tag_drop_terminal_report(data, output_path)
    return TagDropTerminalSummary(
        total_sessions=data.total_sessions,
        total_tags=len(data.nodes),
        output_path=output_path,
    )


def create_tag_conversation_graph_report(
    zip_path: Path,
    output_path: Path,
    *,
    min_node_occurrences: int = 1,
    min_edge_count: int = 1,
    min_edge_percent: float = 0.0,
    top_outgoing: int | None = None,
    dot_output_path: Path | None = None,
) -> TagConversationGraphSummary:
    if min_node_occurrences < 1:
        raise CliError("--min-node-occurrences must be at least 1.")
    if min_edge_count < 1:
        raise CliError("--min-edge-count must be at least 1.")
    if min_edge_percent < 0.0:
        raise CliError("--min-edge-percent cannot be negative.")
    if top_outgoing is not None and top_outgoing < 1:
        raise CliError("--top-outgoing must be at least 1 when provided.")

    data = build_tag_conversation_graph_data(
        zip_path,
        min_node_occurrences=min_node_occurrences,
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

    return TagConversationGraphSummary(
        total_sessions=data.total_sessions,
        total_nodes=data.total_nodes,
        total_edges=data.total_edges,
        filtered_nodes=len(data.nodes) + (1 if data.include_start_node else 0),
        filtered_edges=len(data.edges),
        output_path=output_path,
        dot_output_path=dot_output_path,
    )


def create_tag_conversation_graph_html_report(
    zip_path: Path,
    output_path: Path,
    *,
    min_node_occurrences: int = 1,
    min_edge_count: int = 1,
    min_edge_percent: float = 0.0,
    top_outgoing: int | None = None,
) -> TagConversationGraphSummary:
    data = build_tag_conversation_graph_data(
        zip_path,
        min_node_occurrences=min_node_occurrences,
        min_edge_count=min_edge_count,
        min_edge_percent=min_edge_percent,
        top_outgoing=top_outgoing,
    )

    nodes = []
    if data.include_start_node:
        nodes.append(
            {
                "id": START_NODE_ID,
                "label": START_NODE_NAME,
                "detail": f"{START_NODE_NAME} | Sessions: {data.total_sessions}",
                "occurrences": data.total_sessions,
                "isStart": True,
                "title": START_NODE_NAME,
                "metrics": {
                    "Sessions": data.total_sessions,
                },
            }
        )

    for tag in sorted(data.nodes):
        node = data.nodes[tag]
        nodes.append(
            {
                "id": tag,
                "label": tag,
                "detail": tag,
                "occurrences": node.occurrences,
                "dropRate": node.drop_rate * 100.0,
                "terminalRate": node.terminal_rate * 100.0,
                "isStart": False,
                "title": tag,
                "metrics": {
                    "Occurrences": node.occurrences,
                    "Runs": node.runs,
                    "Sessions": node.sessions,
                    "Fallback rate": f"{node.fallback_rate * 100.0:.1f}%",
                    "Drop rate": f"{node.drop_rate * 100.0:.1f}%",
                    "Terminal rate": f"{node.terminal_rate * 100.0:.1f}%",
                },
            }
        )

    edges = []
    for edge in data.edges:
        edges.append(
            {
                "source": edge.source_tag,
                "target": edge.destination_tag,
                "count": edge.transition_count,
                "percent": edge.outgoing_percentage * 100.0,
                "label": f"{edge.outgoing_percentage * 100.0:.1f}% ({edge.transition_count})",
                "title": f"{edge.source_tag} -> {edge.destination_tag}",
                "metrics": {
                    "Transitions": edge.transition_count,
                    "Outgoing percentage": f"{edge.outgoing_percentage * 100.0:.1f}%",
                    "Source": edge.source_tag,
                    "Target": edge.destination_tag,
                },
            }
        )

    write_interactive_graph_html(
        output_path=output_path,
        title="Conversation Tag Graph",
        graph_kind_label="Tags",
        node_metric_label="Minimum occurrences",
        node_metric_key="occurrences",
        total_sessions=data.total_sessions,
        total_nodes=data.total_nodes,
        total_edges=data.total_edges,
        nodes=nodes,
        edges=edges,
    )

    return TagConversationGraphSummary(
        total_sessions=data.total_sessions,
        total_nodes=data.total_nodes,
        total_edges=data.total_edges,
        filtered_nodes=len(nodes),
        filtered_edges=len(edges),
        output_path=output_path,
        dot_output_path=None,
    )
