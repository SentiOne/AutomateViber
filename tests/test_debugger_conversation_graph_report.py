from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.debugger_lib.conversation_graph_report import (
    build_conversation_graph_data,
    create_conversation_graph_html_report,
    create_conversation_graph_report,
)


class ConversationGraphReportTests(unittest.TestCase):
    def _make_zip(self, zip_path: Path) -> None:
        def state(block_id: str, name: str, context: str | None = None) -> dict[str, str]:
            dialog_state = {"id": block_id, "name": name}
            if context is not None:
                dialog_state["context"] = context
            return dialog_state

        message_rows = [
            {"id": 1, "internalSessionId": "sid-1", "time": 100, "message": "", "tags": ["welcome"], "botMessages": ["hello"], "dialogState": None},
            {"id": 2, "internalSessionId": "sid-1", "time": 200, "message": "x", "tags": ["entry", "faq"], "botMessages": ["ask-a"], "botMessagesCreatedAt": [210], "commands": [{"type": "redirect", "params": {"queue": "support"}}], "nluModels": {"model-a": {"intents": {"intent-a": 0.9}, "variables": [{"name": "city", "value": "Warsaw", "score": 1.0}]}}, "processTime": 12, "nluTime": 3, "integrationsTime": 4, "extraData": {"debug": "value"}, "conversationMetadata": {"trace": ["abc"]}, "quickReplies": [["Yes", "No"], ["Maybe"]], "dialogState": {"id": "a", "name": "say:A", "context": "Main", "contextUuid": "ctx-a", "tags": ["state-tag"]}},
            {"id": 3, "internalSessionId": "sid-1", "time": 300, "message": "Yes", "tags": ["faq"], "botMessages": ["repeat-a"], "dialogState": state("a", "say:A renamed", "Main")},
            {"id": 4, "internalSessionId": "sid-1", "time": 400, "message": "z", "tags": ["handoff"], "botMessages": ["to-b"], "dialogState": state("b", "say:B", "Support")},
            {"id": 5, "internalSessionId": "sid-1", "time": 500, "message": "w", "tags": ["done"], "botMessages": ["to-c"], "dialogState": state("c", "say:C", "Exit")},
            {"id": 6, "internalSessionId": "sid-2", "time": 100, "message": "a2", "tags": ["entry"], "botMessages": ["ask-a"], "dialogState": state("a", "say:A", "Main")},
            {"id": 7, "internalSessionId": "sid-2", "time": 200, "message": "b2", "tags": ["handoff"], "botMessages": ["to-b"], "dialogState": state("b", "say:B", "Support")},
            {"id": 8, "internalSessionId": "sid-3", "time": 100, "message": "a3", "tags": ["entry"], "botMessages": ["ask-a"], "dialogState": state("a", "say:A", "Main")},
            {"id": 9, "internalSessionId": "sid-3", "time": 200, "message": "d3", "tags": ["done"], "botMessages": ["to-d"], "dialogState": state("d", "say:D", "Exit")},
            {"id": 10, "internalSessionId": "sid-4", "time": 100, "message": "e4", "tags": ["entry"], "botMessages": ["only-e"], "dialogState": state("e", "say:E", "Entry")},
            {"id": 11, "internalSessionId": "sid-5", "time": 100, "message": "", "tags": ["silent"], "botMessages": ["silent"], "dialogState": None},
            {"id": 12, "internalSessionId": "sid-6", "time": 100, "message": "a6", "tags": ["entry"], "botMessages": ["ask-a"], "dialogState": state("a", "say:A", "Main")},
            {"id": 13, "internalSessionId": "sid-6", "time": 200, "message": "b6", "tags": ["handoff"], "botMessages": ["to-b"], "dialogState": state("b", "say:B", "Support")},
            {"id": 14, "internalSessionId": "sid-6", "time": 300, "message": "a6-again", "tags": ["return"], "botMessages": ["return-a"], "dialogState": state("a", "say:A", "Main")},
        ]

        for row in message_rows:
            row.setdefault("sessionId", f"public-{row['internalSessionId']}")
            row.setdefault("author", "Secret Author")

        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr(
                "messages.json",
                "".join(json.dumps(row) + "\n" for row in message_rows),
            )

    def test_build_conversation_graph_data_collapses_repeated_turns_and_filters_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "conversations.zip"
            self._make_zip(zip_path)

            data = build_conversation_graph_data(
                zip_path,
                min_node_turns=2,
                min_edge_count=1,
                min_edge_percent=40.0,
                top_outgoing=1,
            )

            self.assertEqual(data.total_sessions, 6)
            self.assertEqual(data.total_nodes, 6)
            self.assertEqual(data.total_edges, 6)
            self.assertTrue(data.include_start_node)
            self.assertTrue(data.show_context_labels)
            self.assertEqual(sorted(data.nodes), ["a", "b"])
            self.assertEqual(data.nodes["a"].block_name, "say:A")
            self.assertEqual(data.nodes["a"].context_name, "Main")
            self.assertEqual(data.nodes["a"].turns, 6)
            self.assertEqual(data.nodes["a"].runs, 5)
            self.assertEqual(data.nodes["a"].sessions, 4)
            self.assertAlmostEqual(data.nodes["a"].fallback_rate, 1 / 5)
            self.assertEqual(data.nodes["a"].quick_reply_offers, 1)
            self.assertAlmostEqual(data.nodes["a"].quick_reply_rate, 1.0)
            self.assertEqual(data.nodes["b"].turns, 3)
            self.assertEqual(len(data.edges), 2)
            start_edge = data.edges[0]
            self.assertEqual(start_edge.source_block_id, "__start__")
            self.assertEqual(start_edge.destination_block_id, "a")
            self.assertEqual(start_edge.transition_count, 4)
            self.assertAlmostEqual(start_edge.outgoing_percentage, 4 / 6)
            edge = data.edges[1]
            self.assertEqual(edge.source_block_id, "a")
            self.assertEqual(edge.destination_block_id, "b")
            self.assertEqual(edge.transition_count, 3)
            self.assertAlmostEqual(edge.outgoing_percentage, 3 / 5)

    def test_create_conversation_graph_report_writes_svg_and_dot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            zip_path = base / "conversations.zip"
            output_path = base / "graph.svg"
            dot_output_path = base / "graph.dot"
            self._make_zip(zip_path)

            summary = create_conversation_graph_report(
                zip_path,
                output_path,
                dot_output_path=dot_output_path,
            )

            self.assertEqual(summary.total_sessions, 6)
            self.assertEqual(summary.total_nodes, 6)
            self.assertEqual(summary.total_edges, 6)
            self.assertEqual(summary.filtered_nodes, 6)
            self.assertEqual(summary.filtered_edges, 6)
            self.assertTrue(output_path.exists())
            self.assertTrue(dot_output_path.exists())
            self.assertIn("<svg", output_path.read_text(encoding="utf-8"))

            dot_content = dot_output_path.read_text(encoding="utf-8")
            self.assertIn(f'"__start__" [label="Start\\nSessions: 6"', dot_content)
            self.assertIn('label="66.7% (4)"', dot_content)
            self.assertIn('label="60.0% (3)"', dot_content)
            self.assertIn('label="say:A\\na\\nTurns: 6 | Runs: 5\\nFallback: 20.0%\\nQuick replies: 100.0% (1)"', dot_content)
            self.assertIn('Fallback: 20.0%', dot_content)
            self.assertIn('Quick replies: 100.0% (1)', dot_content)
            self.assertNotIn('Drop:', dot_content)
            self.assertNotIn('Terminal:', dot_content)

    def test_create_conversation_graph_html_report_writes_interactive_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            zip_path = base / "conversations.zip"
            output_path = base / "graph.html"
            self._make_zip(zip_path)

            summary = create_conversation_graph_html_report(zip_path, output_path)

            self.assertEqual(summary.total_sessions, 6)
            self.assertEqual(summary.total_nodes, 6)
            self.assertEqual(summary.total_edges, 6)
            html = output_path.read_text(encoding="utf-8")
            self.assertIn("Conversation Block Graph", html)
            self.assertIn("cytoscape@3.34.0", html)
            self.assertIn("Open+Sans", html)
            self.assertIn("#7C6DFD", html)
            self.assertIn('aria-label="SentiOne Automate logo"', html)
            self.assertIn("brandmark", html)
            self.assertIn("overflow: hidden;", html)
            self.assertIn("overflow-y: auto;", html)
            self.assertIn("overscroll-behavior: contain;", html)
            self.assertIn('"title": "say:A"', html)
            self.assertIn('"label": "Main\\nsay:A\\na"', html)
            self.assertIn('"Context name": "Main"', html)
            self.assertIn("Name of the flow context where this block was observed.", html)
            self.assertIn('"label": "60.0% (3)"', html)
            self.assertIn('"fallbackRate": 20.0', html)
            self.assertIn('"quickReplyRate": 100.0', html)
            self.assertIn('id="node-border-legend"', html)
            self.assertIn("Block fallback rate border", html)
            self.assertIn("borderRateColor(borderRate)", html)
            self.assertIn('"title": "Previous blocks"', html)
            self.assertIn('"title": "Previous user messages"', html)
            self.assertIn('"title": "Bot messages"', html)
            self.assertIn('"title": "User replies"', html)
            self.assertIn('"title": "Tags"', html)
            self.assertIn('"title": "Non-fallback user messages"', html)
            self.assertIn('"title": "Next bot messages"', html)
            self.assertIn('"title": "Fallback bot replies"', html)
            self.assertIn('"title": "Bot messages before transition"', html)
            self.assertIn('"title": "User messages before transition"', html)
            self.assertIn('"title": "Bot replies in destination block"', html)
            self.assertIn('<details class="details-section">', html)
            self.assertIn('class="section-help"', html)
            self.assertIn('id="section-help-floating"', html)
            self.assertIn('id="conversation-modal"', html)
            self.assertIn('"sampleConversations"', html)
            self.assertIn('"sampleSessions"', html)
            self.assertIn('"sampleKey": "sample-', html)
            self.assertIn('class="details-list-click"', html)
            self.assertIn('role="tablist"', html)
            self.assertIn('data-sample-tab', html)
            self.assertIn('conversation-sample-panel', html)
            self.assertIn('conversation-message--selected', html)
            self.assertIn('conversation-message-text', html)
            self.assertIn('"sessionId": "public-sid-1"', html)
            self.assertIn('"type": "redirect"', html)
            self.assertIn('"nluModels"', html)
            self.assertIn('"processTime": 12', html)
            self.assertIn('"extraData": {"debug": "value"}', html)
            self.assertIn("NLU results", html)
            self.assertIn("Quick Reply Rate", html)
            self.assertIn("Quick Reply offers", html)
            self.assertIn("Share of inferred quick-reply offers from this block where the next exported user message exactly matched one offered quick reply.", html)
            self.assertIn("conversation-chip-section", html)
            self.assertIn("conversation-tag-list", html)
            self.assertIn("conversation-tag-button", html)
            self.assertIn("conversation-quick-reply-section", html)
            self.assertIn("conversation-quick-reply-list", html)
            self.assertIn("conversation-quick-reply-button", html)
            self.assertIn('"quickReplies": [["Yes", "No"], ["Maybe"]]', html)
            self.assertIn("conversation-diagnostics", html)
            self.assertIn("Technical details", html)
            self.assertLess(
                html.index("${renderQuickReplies(row.quickReplies)}"),
                html.index("${renderTags(row.tags)}"),
            )
            self.assertLess(
                html.index("${renderTags(row.tags)}"),
                html.index("${renderTurnDiagnostics(row)}"),
            )
            self.assertIn("Block that requested this reply", html)
            self.assertIn("Context that requested this reply", html)
            self.assertNotIn("Secret Author", html)
            self.assertIn('data-help-title="${helpTitle}"', html)
            self.assertIn('details-list-row--stacked', html)
            self.assertIn('Number of exported turns recorded for this block.', html)
            self.assertIn('Stable block identifier used for grouping.', html)
            self.assertIn('Blocks that usually came before this block.', html)
            self.assertIn('User messages that appeared just before this block became active.', html)
            self.assertIn('Bot messages that users replied to while they were in this block.', html)
            self.assertIn('Tags recorded while this block was active.', html)
            self.assertIn('User replies after which the conversation appears to stay in this block instead of moving forward.', html)
            self.assertIn('Bot messages shown before the user took this transition.', html)
            self.assertIn('User messages that led to this transition.', html)
            self.assertIn('Bot replies shown after this transition.', html)
            graph_payload = json.loads(
                html.split('<script type="application/json" id="graph-data">', 1)[1]
                .split("</script>", 1)[0]
            )
            node_a = next(node for node in graph_payload["nodes"] if node["id"] == "a")
            self.assertEqual(node_a["label"], "Main\nsay:A\na")
            self.assertEqual(node_a["metrics"]["Context name"], "Main")
            tag_section = next(section for section in node_a["sections"] if section["title"] == "Tags")
            self.assertEqual(
                [row["label"] for row in tag_section["rows"]],
                ["entry", "faq", "handoff", "welcome"],
            )
            self.assertNotIn("return", [row["label"] for row in tag_section["rows"]])
            self.assertIn('"label": "say:B (b)"', html)
            self.assertIn('"label": "ask-a"', html)
            self.assertIn('"value": "4 (66.7%)"', html)
            self.assertNotIn('"Drop rate"', html)
            self.assertNotIn('"Terminal rate"', html)
            self.assertGreaterEqual(html.count("Number(edge.count || 0) >= minEdgeCount"), 2)
            self.assertGreaterEqual(html.count("Number(edge.percent || 0) >= minEdgePercent"), 2)
            ordered_titles = [
                '"title": "Previous blocks"',
                '"title": "Previous user messages"',
                '"title": "Bot messages"',
                '"title": "User replies"',
                '"title": "Next bot messages"',
                '"title": "Tags"',
                '"title": "Non-fallback user messages"',
                '"title": "Fallback user messages"',
                '"title": "Fallback bot replies"',
                '"title": "Next blocks"',
            ]
            positions = [html.index(title) for title in ordered_titles]
            self.assertEqual(positions, sorted(positions))
            edge_ordered_titles = [
                '"title": "Bot messages before transition"',
                '"title": "User messages before transition"',
                '"title": "Bot replies in destination block"',
            ]
            edge_positions = [html.index(title) for title in edge_ordered_titles]
            self.assertEqual(edge_positions, sorted(edge_positions))

    def test_edge_percentage_uses_all_source_runs_including_drop_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "conversations.zip"
            self._make_zip(zip_path)

            data = build_conversation_graph_data(zip_path)

            edge_map = {
                (edge.source_block_id, edge.destination_block_id): edge
                for edge in data.edges
            }
            self.assertAlmostEqual(edge_map[("a", "b")].outgoing_percentage, 3 / 5)
            self.assertAlmostEqual(edge_map[("a", "d")].outgoing_percentage, 1 / 5)
            self.assertAlmostEqual(edge_map[("b", "c")].outgoing_percentage, 1 / 3)

    def test_entry_nodes_keep_a_start_edge_even_if_start_top_outgoing_would_hide_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "conversations.zip"
            self._make_zip(zip_path)

            data = build_conversation_graph_data(
                zip_path,
                min_node_turns=1,
                min_edge_count=1,
                min_edge_percent=0.0,
                top_outgoing=1,
            )

            edge_map = {
                (edge.source_block_id, edge.destination_block_id): edge
                for edge in data.edges
            }
            self.assertIn(("__start__", "a"), edge_map)
            self.assertIn(("__start__", "e"), edge_map)
            self.assertAlmostEqual(edge_map[("__start__", "e")].outgoing_percentage, 1 / 6)

    def test_orphaned_nodes_restore_real_incoming_edge_before_start_edge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "conversations.zip"
            self._make_zip(zip_path)

            data = build_conversation_graph_data(
                zip_path,
                min_node_turns=1,
                min_edge_count=1,
                min_edge_percent=40.0,
                top_outgoing=1,
            )

            edge_map = {
                (edge.source_block_id, edge.destination_block_id): edge
                for edge in data.edges
            }
            self.assertIn(("b", "c"), edge_map)
            self.assertNotIn(("__start__", "c"), edge_map)


if __name__ == "__main__":
    unittest.main()
