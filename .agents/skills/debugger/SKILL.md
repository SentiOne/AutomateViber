---
name: debugger
description: Use this skill when the task is to analyze a SentiOne conversation export from the application UI, especially when producing XLSX reports from ZIP files that contain sessions.json and messages.json in NDJSON format.
---

# Debugger

Use this skill for analysis of conversation exports downloaded from the application UI.

## Input contract

- The source artifact is a ZIP file exported from the UI.
- The ZIP is expected to contain `sessions.json` and may also contain `messages.json`.
- Treat both files as NDJSON: one JSON object per line.

## Workflow

1. Inspect the ZIP contents first.
2. Prefer `sessions.json` when the report is about final session state.
3. Use `messages.json` only when the requested analysis genuinely requires per-message detail.
4. Stream the NDJSON rows instead of loading the entire export into memory.
5. Write generated artifacts to `output/` unless the user asks for a different path.
6. When grouping blocks for logic analysis, use `dialogState.id` as the primary key and treat `dialogState.name` as display-only metadata.

## `messages.json` dialogState semantics

When analyzing `messages.json`, treat each row as a user turn with the bot reply that followed it.

- `dialogState.id` and `dialogState.name` identify the block that requested the user input on that row.
- The row `message` is the user's reply to that `dialogState` block.
- The row `botMessages` are the bot replies produced after that user reply, so they usually belong to the next block, not to the row's `dialogState` block.
- To describe the bot messages for block `A`, use `botMessages` from the previous chronological row before a row whose `dialogState.id` is `A`.
- To describe the next bot messages after a user reply in block `A`, use `botMessages` from the same row whose `dialogState.id` is `A`.
- `dialogState: null` usually means there was no previous block requesting user input, for example a welcome-only turn.
- Do not calculate actual drop-off or terminal-block metrics from the last `dialogState` alone; it only identifies the last block that requested user input, not necessarily the final bot block or the reason the conversation ended.

## Last block report

For last-block frequency analysis:

- Use `sessions.json`.
- Read `dialogState.id` and `dialogState.name` as the canonical last-block fields.
- Treat `dialogState: null` as unresolved and report the unresolved count separately.
- Do not try to reconstruct unresolved last blocks from `messages.json` unless the export format changes and the task explicitly requires a fallback investigation.

Run:

```bash
scripts/debugger last-block-report <zip-path> <xlsx-path>
```

Optional:

```bash
scripts/debugger last-block-report <zip-path> <xlsx-path> --percentage-base resolved
```

## Fallback / circular report

For repeated same-block analysis:

- Use `messages.json`.
- Treat consecutive identical non-null `dialogState.id` rows within the same session as one heuristic repeated-input run.
- Because `dialogState.id` identifies the block that requested user input, repeated block fallback/circular metrics indicate repeated answers to the same input-requesting block, not guaranteed exact runtime current-state truth.
- Interpret each extra stay in the same run as a fallback/circular step:
  - run length `2` -> bucket `1`
  - run length `3` -> bucket `2`
  - run length `4+` -> bucket `3+`
- Count those buckets per block and sort the report by total fallback episodes descending.

Run:

```bash
scripts/debugger fallback-circular-report <zip-path> <xlsx-path>
```

## Block drilldown reports

For block-specific drilldown analysis:

- Use `messages.json`.
- Follow the `messages.json` dialogState semantics above; do not treat row `botMessages` as messages from the same row's `dialogState` block.
- Use `dialogState.id` as the canonical block identifier.
- Treat `dialogState.name` as display-only and derive one stable display label per id from the export data.
- Include `dialogState.context` as the context name in block-listing XLSX sheets when it is available in the export.
- Group consecutive rows with the same block id in one session into one block run.
- Use the last message of the previous block run as the incoming user message that led to the current block run.
- Use bot messages from the previous chronological turn before each block turn as the current block's bot messages.
- Use messages recorded on block turns as user replies for that block.
- Use bot messages recorded on the block run as the next bot messages after those user replies.
- Use the last message of a block run as the non-fallback user message when a next block run exists.
- Treat earlier messages inside a repeated same-block run as fallback phrases. This is a useful heuristic for repeated prompting or circular behavior, but not proof that the runtime engine stayed in the exact same current block.

Run:

```bash
scripts/debugger block-overview-report <zip-path> <block-id> <xlsx-path>
scripts/debugger block-phrases-to-next-report <zip-path> <block-id> <xlsx-path>
scripts/debugger block-fallback-phrases-report <zip-path> <block-id> <xlsx-path>
scripts/debugger block-next-blocks-report <zip-path> <block-id> <xlsx-path>
scripts/debugger block-previous-blocks-report <zip-path> <block-id> <xlsx-path>
scripts/debugger block-phrases-to-current-report <zip-path> <block-id> <xlsx-path>
scripts/debugger block-bot-messages-report <zip-path> <block-id> <xlsx-path>
scripts/debugger block-previous-bot-messages-report <zip-path> <block-id> <xlsx-path>
scripts/debugger block-previous-user-messages-report <zip-path> <block-id> <xlsx-path>
scripts/debugger block-drilldown-report <zip-path> <block-id> <xlsx-path>
```

## Conversation graph report

For conversation graph visualization:

- Use `messages.json`.
- Follow the `messages.json` dialogState semantics above when populating node and edge details.
- Use `dialogState.id` as the node identifier and treat `dialogState.name` as display-only metadata.
- Collapse consecutive identical non-null `dialogState` rows within the same session into one run before building transitions.
- Build one directed edge for each transition from a run to the next different run in the same session.
- Size nodes by total turns in that block.
- Label edges with outgoing percentage from the source block plus raw transition count.
- Fallback rate is a heuristic: it counts runs where the same `dialogState.id` appears on consecutive user-turn rows, so it means repeated answers to the same input-requesting block rather than guaranteed exact runtime fallback.
- Quick Reply Rate is calculated for the block that offered the quick replies. Because `dialogState.id` is shifted, infer the offering/requesting block from the following row's `dialogState.id`: if the previous chronological row has flattened `quickReplies`, count one quick-reply offer for the following row's block; if the following row's user `message` exactly matches one offered quick reply after trimming, count it as used. The rate is used offers divided by inferred offers.
- In block sidepanel details, show Tags from the previous chronological row for each block turn, not from the current row. Current row tags describe the bot path after the user reply and therefore often belong to later blocks.
- In the interactive HTML block graph, show the block context name under the block id in node details. If the export contains more than one context, include the context name as the first line of each block node label when available.
- In the interactive HTML block graph, fallback rate is visualized on nodes: higher fallback rate makes the node border redder and thicker, with an in-report legend.
- In the interactive HTML block graph, sidepanel user-message and bot-message rows may include clickable sample links that open full conversation examples. Those modal examples must be serialized from an explicit whitelist of diagnostic fields and must not expose `author`.
- In modal conversation examples, show `dialogState` block/context before the user message because they identify the block/context that requested that reply, not the bot replies that follow it.
- Do not include node drop-rate or terminal-rate metrics unless a future export provides an explicit reliable end-state signal.
- Use filtering for readability on larger exports.

Run:

```bash
scripts/debugger conversation-graph-report <zip-path> <svg-path>
```

Optional:

```bash
scripts/debugger conversation-graph-report <zip-path> <svg-path> --dot-output output/conversation-graph.dot --min-node-turns 10 --min-edge-count 5 --min-edge-percent 2 --top-outgoing 5
```

For an advanced interactive browser version of the same block graph:

```bash
scripts/debugger conversation-graph-html-report <zip-path> <html-path>
```

## Tag conversation graph report

For tag-based conversation graph visualization:

- Use `messages.json`.
- Use the top-level message-row `tags` array, not `dialogState.tags`, as the primary event source.
- Within one session, sort rows by `(time, id)`, then read each row's `tags` array in the exact order stored in the export.
- Flatten those ordered tag arrays into one per-session tag sequence.
- Collapse consecutive identical tags into one run before building transitions.
- Build one directed edge for each transition from a tag run to the next different tag run in the same session.
- Size nodes by total tag occurrences.
- Label edges with outgoing percentage plus raw transition count.
- The tag sequence is not shifted like `dialogState`; tag order can be used for end-of-session metrics.
- Tag drop rate is run-based: final tag runs with no later non-empty user `message` and no `Disconnect` or `Redirect` command at or after that final tag row, divided by all runs of that tag.
- Tag terminal rate is session-based: sessions where the tag is the final tag run with no later non-empty user `message` divided by sessions containing that tag.
- In the interactive HTML tag graph, tag drop rate is visualized on nodes: higher drop rate makes the node border redder and thicker, with an in-report legend.

For a tabular XLSX report of tag drop and terminal statistics:

```bash
scripts/debugger tag-drop-terminal-report <zip-path> <xlsx-path>
```

This XLSX includes `Sessions percentage of all sessions` (sessions containing the tag divided by all exported sessions), `Terminal rate` (terminal sessions divided by sessions containing the tag), and `Terminal sessions percentage of all sessions` (terminal sessions divided by all exported sessions).

Run:

```bash
scripts/debugger tag-conversation-graph-report <zip-path> <svg-path>
```

Optional:

```bash
scripts/debugger tag-conversation-graph-report <zip-path> <svg-path> --dot-output output/tag-conversation-graph.dot --min-node-occurrences 10 --min-edge-count 5 --min-edge-percent 2 --top-outgoing 5
```

For an advanced interactive browser version of the same tag graph:

```bash
scripts/debugger tag-conversation-graph-html-report <zip-path> <html-path>
```

## Verification

- Confirm the ZIP contains the required files before running the report.
- Confirm the XLSX sort order matches the requested report.
- Confirm the output includes block name and block id plus the report-specific metrics.
- Report the relevant session totals to the user.
