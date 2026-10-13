from __future__ import annotations

import argparse
from pathlib import Path

from .block_drilldown_report import (
    build_block_drilldown_data,
    write_block_drilldown_report,
    write_block_fallback_phrases_report,
    write_block_bot_messages_report,
    write_block_next_blocks_report,
    write_block_overview_report,
    write_block_phrases_to_current_report,
    write_block_phrases_to_next_report,
    write_block_previous_bot_messages_report,
    write_block_previous_user_messages_report,
    write_block_previous_blocks_report,
)
from .conversation_graph_report import (
    create_conversation_graph_html_report,
    create_conversation_graph_report,
)
from .fallback_circular_report import create_fallback_circular_report
from .io import CliError
from .last_block_report import create_last_block_report
from .tag_conversation_graph_report import (
    create_tag_conversation_graph_html_report,
    create_tag_conversation_graph_report,
    create_tag_drop_terminal_report,
)


def command_last_block_report(args: argparse.Namespace) -> int:
    summary = create_last_block_report(
        zip_path=Path(args.zip_path).expanduser(),
        output_path=Path(args.output_path).expanduser(),
        percentage_base=args.percentage_base,
    )

    print(f"Processed sessions: {summary.total_sessions}")
    print(f"Resolved last blocks: {summary.resolved_sessions}")
    print(f"Unresolved sessions: {summary.unresolved_sessions}")
    print(f"Wrote XLSX: {summary.output_path}")
    return 0


def command_fallback_circular_report(args: argparse.Namespace) -> int:
    summary = create_fallback_circular_report(
        zip_path=Path(args.zip_path).expanduser(),
        output_path=Path(args.output_path).expanduser(),
    )

    print(f"Processed sessions: {summary.total_sessions}")
    print(f"Sessions with block visits: {summary.sessions_with_block_visits}")
    print(f"Sessions with fallback episodes: {summary.sessions_with_fallback_episodes}")
    print(f"Wrote XLSX: {summary.output_path}")
    return 0


def _build_and_write_block_report(args: argparse.Namespace, writer) -> int:
    zip_path = Path(args.zip_path).expanduser()
    output_path = Path(args.output_path).expanduser()
    data = build_block_drilldown_data(zip_path=zip_path, target_block_id=args.block_id)
    writer(data, output_path)
    print(f"Target block id: {data.target_block_id}")
    print(f"Target block name: {data.target_block_name}")
    print(f"Sessions with target block: {data.sessions_with_target_block}")
    print(f"Wrote XLSX: {output_path}")
    return 0


def command_block_overview_report(args: argparse.Namespace) -> int:
    return _build_and_write_block_report(args, write_block_overview_report)


def command_block_phrases_to_next_report(args: argparse.Namespace) -> int:
    return _build_and_write_block_report(args, write_block_phrases_to_next_report)


def command_block_fallback_phrases_report(args: argparse.Namespace) -> int:
    return _build_and_write_block_report(args, write_block_fallback_phrases_report)


def command_block_next_blocks_report(args: argparse.Namespace) -> int:
    return _build_and_write_block_report(args, write_block_next_blocks_report)


def command_block_previous_blocks_report(args: argparse.Namespace) -> int:
    return _build_and_write_block_report(args, write_block_previous_blocks_report)


def command_block_phrases_to_current_report(args: argparse.Namespace) -> int:
    return _build_and_write_block_report(args, write_block_phrases_to_current_report)


def command_block_bot_messages_report(args: argparse.Namespace) -> int:
    return _build_and_write_block_report(args, write_block_bot_messages_report)


def command_block_previous_bot_messages_report(args: argparse.Namespace) -> int:
    return _build_and_write_block_report(args, write_block_previous_bot_messages_report)


def command_block_previous_user_messages_report(args: argparse.Namespace) -> int:
    return _build_and_write_block_report(args, write_block_previous_user_messages_report)


def command_block_drilldown_report(args: argparse.Namespace) -> int:
    return _build_and_write_block_report(args, write_block_drilldown_report)


def command_conversation_graph_report(args: argparse.Namespace) -> int:
    summary = create_conversation_graph_report(
        zip_path=Path(args.zip_path).expanduser(),
        output_path=Path(args.output_path).expanduser(),
        min_node_turns=args.min_node_turns,
        min_edge_count=args.min_edge_count,
        min_edge_percent=args.min_edge_percent,
        top_outgoing=args.top_outgoing,
        dot_output_path=Path(args.dot_output).expanduser() if args.dot_output else None,
    )
    print(f"Processed sessions: {summary.total_sessions}")
    print(f"Total nodes: {summary.total_nodes}")
    print(f"Total edges: {summary.total_edges}")
    print(f"Filtered nodes: {summary.filtered_nodes}")
    print(f"Filtered edges: {summary.filtered_edges}")
    if summary.dot_output_path is not None:
        print(f"Wrote DOT: {summary.dot_output_path}")
    print(f"Wrote SVG: {summary.output_path}")
    return 0


def command_tag_conversation_graph_report(args: argparse.Namespace) -> int:
    summary = create_tag_conversation_graph_report(
        zip_path=Path(args.zip_path).expanduser(),
        output_path=Path(args.output_path).expanduser(),
        min_node_occurrences=args.min_node_occurrences,
        min_edge_count=args.min_edge_count,
        min_edge_percent=args.min_edge_percent,
        top_outgoing=args.top_outgoing,
        dot_output_path=Path(args.dot_output).expanduser() if args.dot_output else None,
    )
    print(f"Processed sessions: {summary.total_sessions}")
    print(f"Total nodes: {summary.total_nodes}")
    print(f"Total edges: {summary.total_edges}")
    print(f"Filtered nodes: {summary.filtered_nodes}")
    print(f"Filtered edges: {summary.filtered_edges}")
    if summary.dot_output_path is not None:
        print(f"Wrote DOT: {summary.dot_output_path}")
    print(f"Wrote SVG: {summary.output_path}")
    return 0


def command_conversation_graph_html_report(args: argparse.Namespace) -> int:
    summary = create_conversation_graph_html_report(
        zip_path=Path(args.zip_path).expanduser(),
        output_path=Path(args.output_path).expanduser(),
        min_node_turns=args.min_node_turns,
        min_edge_count=args.min_edge_count,
        min_edge_percent=args.min_edge_percent,
        top_outgoing=args.top_outgoing,
    )
    print(f"Processed sessions: {summary.total_sessions}")
    print(f"Total nodes: {summary.total_nodes}")
    print(f"Total edges: {summary.total_edges}")
    print(f"Visible nodes at load: {summary.filtered_nodes}")
    print(f"Visible edges at load: {summary.filtered_edges}")
    print(f"Wrote HTML: {summary.output_path}")
    return 0


def command_tag_conversation_graph_html_report(args: argparse.Namespace) -> int:
    summary = create_tag_conversation_graph_html_report(
        zip_path=Path(args.zip_path).expanduser(),
        output_path=Path(args.output_path).expanduser(),
        min_node_occurrences=args.min_node_occurrences,
        min_edge_count=args.min_edge_count,
        min_edge_percent=args.min_edge_percent,
        top_outgoing=args.top_outgoing,
    )
    print(f"Processed sessions: {summary.total_sessions}")
    print(f"Total nodes: {summary.total_nodes}")
    print(f"Total edges: {summary.total_edges}")
    print(f"Visible nodes at load: {summary.filtered_nodes}")
    print(f"Visible edges at load: {summary.filtered_edges}")
    print(f"Wrote HTML: {summary.output_path}")
    return 0


def command_tag_drop_terminal_report(args: argparse.Namespace) -> int:
    summary = create_tag_drop_terminal_report(
        zip_path=Path(args.zip_path).expanduser(),
        output_path=Path(args.output_path).expanduser(),
    )
    print(f"Processed sessions: {summary.total_sessions}")
    print(f"Tags included: {summary.total_tags}")
    print(f"Wrote XLSX: {summary.output_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Conversation export debugger for UI ZIP exports.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser(
        "last-block-report",
        help="Generate an XLSX report of last-block frequencies from a conversation export ZIP.",
    )
    report_parser.add_argument("zip_path", help="Path to the UI export ZIP file.")
    report_parser.add_argument("output_path", help="Path to the XLSX file to create.")
    report_parser.add_argument(
        "--percentage-base",
        choices=["all", "resolved"],
        default="all",
        help="Percentage denominator: all exported sessions or only sessions with a resolved dialogState.",
    )
    report_parser.set_defaults(func=command_last_block_report)

    fallback_parser = subparsers.add_parser(
        "fallback-circular-report",
        help="Generate an XLSX report of same-block fallback/circular episodes from messages.json.",
    )
    fallback_parser.add_argument("zip_path", help="Path to the UI export ZIP file.")
    fallback_parser.add_argument("output_path", help="Path to the XLSX file to create.")
    fallback_parser.set_defaults(func=command_fallback_circular_report)

    def add_block_report_parser(name: str, help_text: str, handler) -> None:
        parser = subparsers.add_parser(name, help=help_text)
        parser.add_argument("zip_path", help="Path to the UI export ZIP file.")
        parser.add_argument("block_id", help="Target dialogState.id block identifier.")
        parser.add_argument("output_path", help="Path to the XLSX file to create.")
        parser.set_defaults(func=handler)

    add_block_report_parser(
        "block-overview-report",
        "Generate a one-sheet XLSX overview for a specific block id.",
        command_block_overview_report,
    )
    add_block_report_parser(
        "block-phrases-to-next-report",
        "Generate a one-sheet XLSX of last-turn user messages for block runs followed by a different next block run.",
        command_block_phrases_to_next_report,
    )
    add_block_report_parser(
        "block-fallback-phrases-report",
        "Generate a one-sheet XLSX of user messages from repeated turns inside the same block run.",
        command_block_fallback_phrases_report,
    )
    add_block_report_parser(
        "block-next-blocks-report",
        "Generate a one-sheet XLSX of next-block frequencies for a specific block id.",
        command_block_next_blocks_report,
    )
    add_block_report_parser(
        "block-previous-blocks-report",
        "Generate a one-sheet XLSX of previous-block frequencies for a specific block id.",
        command_block_previous_blocks_report,
    )
    add_block_report_parser(
        "block-phrases-to-current-report",
        "Generate a one-sheet XLSX of user replies recorded on a specific block id.",
        command_block_phrases_to_current_report,
    )
    add_block_report_parser(
        "block-bot-messages-report",
        "Generate a one-sheet XLSX of next bot messages recorded on a specific block id.",
        command_block_bot_messages_report,
    )
    add_block_report_parser(
        "block-previous-bot-messages-report",
        "Generate a one-sheet XLSX of bot messages associated with a specific block id before user replies.",
        command_block_previous_bot_messages_report,
    )
    add_block_report_parser(
        "block-previous-user-messages-report",
        "Generate a one-sheet XLSX of incoming user messages from the previous block run before a specific block id.",
        command_block_previous_user_messages_report,
    )
    add_block_report_parser(
        "block-drilldown-report",
        "Generate a ten-sheet XLSX drilldown report for a specific block id.",
        command_block_drilldown_report,
    )

    graph_parser = subparsers.add_parser(
        "conversation-graph-report",
        help="Generate an SVG graph of block transitions from messages.json in a conversation export ZIP.",
    )
    graph_parser.add_argument("zip_path", help="Path to the UI export ZIP file.")
    graph_parser.add_argument("output_path", help="Path to the SVG file to create.")
    graph_parser.add_argument(
        "--min-node-turns",
        type=int,
        default=1,
        help="Minimum total turns required for a block node to be included.",
    )
    graph_parser.add_argument(
        "--min-edge-count",
        type=int,
        default=1,
        help="Minimum transition count required for an edge to be included.",
    )
    graph_parser.add_argument(
        "--min-edge-percent",
        type=float,
        default=0.0,
        help="Minimum outgoing percentage, in percent points, required for an edge to be included.",
    )
    graph_parser.add_argument(
        "--top-outgoing",
        type=int,
        default=None,
        help="Keep only the top N outgoing edges per source block after other filters are applied.",
    )
    graph_parser.add_argument(
        "--dot-output",
        default=None,
        help="Optional path to also save the intermediate Graphviz DOT file.",
    )
    graph_parser.set_defaults(func=command_conversation_graph_report)

    graph_html_parser = subparsers.add_parser(
        "conversation-graph-html-report",
        help="Generate an interactive HTML graph of block transitions from messages.json in a conversation export ZIP.",
    )
    graph_html_parser.add_argument("zip_path", help="Path to the UI export ZIP file.")
    graph_html_parser.add_argument("output_path", help="Path to the HTML file to create.")
    graph_html_parser.add_argument(
        "--min-node-turns",
        type=int,
        default=1,
        help="Minimum total turns required for a block node to be included initially.",
    )
    graph_html_parser.add_argument(
        "--min-edge-count",
        type=int,
        default=1,
        help="Minimum transition count required for an edge to be included initially.",
    )
    graph_html_parser.add_argument(
        "--min-edge-percent",
        type=float,
        default=0.0,
        help="Minimum outgoing percentage, in percent points, required for an edge to be included initially.",
    )
    graph_html_parser.add_argument(
        "--top-outgoing",
        type=int,
        default=None,
        help="Keep only the top N outgoing edges per source block in the initial HTML payload.",
    )
    graph_html_parser.set_defaults(func=command_conversation_graph_html_report)

    tag_graph_parser = subparsers.add_parser(
        "tag-conversation-graph-report",
        help="Generate an SVG graph of tag transitions from messages.json in a conversation export ZIP.",
    )
    tag_graph_parser.add_argument("zip_path", help="Path to the UI export ZIP file.")
    tag_graph_parser.add_argument("output_path", help="Path to the SVG file to create.")
    tag_graph_parser.add_argument(
        "--min-node-occurrences",
        type=int,
        default=1,
        help="Minimum total occurrences required for a tag node to be included.",
    )
    tag_graph_parser.add_argument(
        "--min-edge-count",
        type=int,
        default=1,
        help="Minimum transition count required for an edge to be included.",
    )
    tag_graph_parser.add_argument(
        "--min-edge-percent",
        type=float,
        default=0.0,
        help="Minimum outgoing percentage, in percent points, required for an edge to be included.",
    )
    tag_graph_parser.add_argument(
        "--top-outgoing",
        type=int,
        default=None,
        help="Keep only the top N outgoing edges per source tag after other filters are applied.",
    )
    tag_graph_parser.add_argument(
        "--dot-output",
        default=None,
        help="Optional path to also save the intermediate Graphviz DOT file.",
    )
    tag_graph_parser.set_defaults(func=command_tag_conversation_graph_report)

    tag_graph_html_parser = subparsers.add_parser(
        "tag-conversation-graph-html-report",
        help="Generate an interactive HTML graph of tag transitions from messages.json in a conversation export ZIP.",
    )
    tag_graph_html_parser.add_argument("zip_path", help="Path to the UI export ZIP file.")
    tag_graph_html_parser.add_argument("output_path", help="Path to the HTML file to create.")
    tag_graph_html_parser.add_argument(
        "--min-node-occurrences",
        type=int,
        default=1,
        help="Minimum total occurrences required for a tag node to be included initially.",
    )
    tag_graph_html_parser.add_argument(
        "--min-edge-count",
        type=int,
        default=1,
        help="Minimum transition count required for an edge to be included initially.",
    )
    tag_graph_html_parser.add_argument(
        "--min-edge-percent",
        type=float,
        default=0.0,
        help="Minimum outgoing percentage, in percent points, required for an edge to be included initially.",
    )
    tag_graph_html_parser.add_argument(
        "--top-outgoing",
        type=int,
        default=None,
        help="Keep only the top N outgoing edges per source tag in the initial HTML payload.",
    )
    tag_graph_html_parser.set_defaults(func=command_tag_conversation_graph_html_report)

    tag_drop_terminal_parser = subparsers.add_parser(
        "tag-drop-terminal-report",
        help="Generate an XLSX report of tag drop rate and terminal rate statistics from messages.json.",
    )
    tag_drop_terminal_parser.add_argument("zip_path", help="Path to the UI export ZIP file.")
    tag_drop_terminal_parser.add_argument("output_path", help="Path to the XLSX file to create.")
    tag_drop_terminal_parser.set_defaults(func=command_tag_drop_terminal_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except CliError as exc:
        parser.exit(status=1, message=f"Error: {exc}\n")
