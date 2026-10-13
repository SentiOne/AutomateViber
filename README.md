# Vibe Coding Guide for SentiOne Automate Exports

## Purpose

This repository is used to modify SentiOne Automate project exports with an AI coding agent in a safe
and repeatable way.
The preferred workflow is now API-first using the SentiOne Automate Public API, with ZIP-only handling as a fallback.

It is designed for:
- exporting Automate projects through the public API
- analyzing Automate exports
- modifying flows, NLU, and related files
- reusing verified block templates from a reference export
- producing updated importable ZIP files
- importing validated ZIPs back through the public API

This repository is **not** a generic software project.

## Coding agents

`AGENTS.md` is the single source of rules: the mandatory startup sequence, the
export layout, the verified block and memory schemas, and the validation
checklist. It is not written for one particular tool, and every agent reads the
same file — the other entry points are symlinks to it:

| Path | Read by |
| --- | --- |
| `AGENTS.md` | Codex, Cursor, Jules and anything else following the AGENTS.md convention |
| `CLAUDE.md` → `AGENTS.md` | Claude Code |
| `.github/copilot-instructions.md` → `AGENTS.md` | GitHub Copilot |

Task-specific skills live in `.agents/skills/`, with `.claude/skills` and
`.github/skills` symlinked to that directory for the same reason.

Keeping them as symlinks rather than copies is deliberate: a rule verified on
the platform is written once, and no agent can end up following a stale copy of
it. If you add support for another tool, add a symlink — never a second copy.

## Key files

- `AGENTS.md` — the rules every coding agent follows here (see below)
- `senti0ne-automate-public-api.json` — local OpenAPI contract for the Automate public API
- `scripts/automate.py` — cross-platform local API CLI
- `scripts/automate`, `scripts/automate.cmd`, `scripts/automate.ps1` — OS launchers for the CLI
- `scripts/debugger.py` — cross-platform conversation export analysis CLI
- `scripts/debugger`, `scripts/debugger.cmd`, `scripts/debugger.ps1` — OS launchers for the debugger CLI
- `scripts/automate.config.example.json` — non-secret config template
- `scripts/requirements.txt` — Python dependencies for the local helper CLIs
- `scripts/validate_export.py` — structural validation of an unpacked export against the repository checklist
- `scripts/nlu_data/` — reusable NLU material (MTT yes/no pattern entities)
- `reference/` — verified reference exports with valid block structures
- `input/` — place target ZIP files here
- `work/` — unpacked working area for the current target export
- `output/` — updated ZIP files created after modification

## Local API setup

### 1. Install the CLI dependencies

```bash
python -m pip install -r scripts/requirements.txt
```

### 2. Create the local non-secret config

```bash
scripts/automate init-config
```

This writes the config file outside the repository:
- Windows: `%AppData%/SentiOneAutomate/config.json`
- macOS: `~/Library/Application Support/SentiOneAutomate/config.json`
- Linux: `~/.config/sentione-automate/config.json`

Fill in:
- `defaultHost`
- `hosts.<name>.server`
- `profiles.<name>.host`
- `projectId`
- `apiKey.service`
- `apiKey.username`

The generated template automatically points directories at this repository:
- `directories.exportZips`: `input/`
- `directories.workspaceRoot`: `work/`
- `directories.importZips`: `output/`

### 3. Store the API key in the OS keychain

Do this locally on the machine where the scripts will run:

```bash
python -m keyring set sentione-automate default
```

Use the `service` and `username` values from the config.
Do not store the API key in the repository, in the config file, or in environment variables.

If you also use `scripts/chunker`, store its key the same way:

```bash
python -m keyring set sentione-chunker default
```

Obtain both keys from your Automate administrator. The chunker helper falls back to a
`CHUNKER_API_KEY` environment variable, but that exists for CI runners with no
keychain — on a workstation, use the keychain.

### 4. Validate the local setup

```bash
scripts/automate doctor
```

List configured hosts:

```bash
scripts/automate hosts
```

### 5. Use the local API workflow

List available projects:

```bash
scripts/automate projects
```

List projects from a specific configured host alias:

```bash
scripts/automate projects --host staging
```

Export the configured project:

```bash
scripts/automate export
```

Export using a specific profile:

```bash
scripts/automate export --profile production-bot
```

Import a ZIP back to the configured project:

```bash
scripts/automate import output/project_update.zip
```

Import and publish flows:

```bash
scripts/automate import output/project_update.zip --publish-flows
```

Search historical conversations:

```bash
scripts/automate conversations search --from 2026-01-01T00:00:00.000Z --to 2026-01-31T23:59:59.000Z
```

Search historical conversations for one project and save the raw API response:

```bash
scripts/automate conversations search --project-id 89d9552c-4f29-43dd-9871-2621d4e5f5a0 --limit 100 --output output/conversations.json
```

Fetch all messages for one conversation session:

```bash
scripts/automate conversations messages <internalSessionId>
```

Fetch messages including dialog log events and print raw JSON:

```bash
scripts/automate conversations messages <internalSessionId> --include-bot-logs --json
```

Download a conversation recording:

```bash
scripts/automate conversations recording <internalSessionId>
```

Download a conversation recording and open it in the default media player:

```bash
scripts/automate conversations recording <internalSessionId> --play
```

Analyze a UI conversation export ZIP and create a last-block XLSX report:

```bash
scripts/debugger last-block-report input/conversations-export.zip output/last-block-report.xlsx
```

Use resolved sessions only as the percentage denominator:

```bash
scripts/debugger last-block-report input/conversations-export.zip output/last-block-report.xlsx --percentage-base resolved
```

Analyze `messages.json` from a UI conversation export ZIP and create a fallback/circular block XLSX report:

```bash
scripts/debugger fallback-circular-report input/conversations-export.zip output/fallback-circular-report.xlsx
```

Block-related XLSX reports include `Context name` columns on sheets that list blocks, when `dialogState.context` is available in the export.

Generate a one-sheet XLSX overview for a specific block id:

```bash
scripts/debugger block-overview-report input/conversations-export.zip <block-id> output/block-overview.xlsx
```

Generate one-sheet XLSX reports for phrases and neighboring blocks of a specific block id:

```bash
scripts/debugger block-phrases-to-next-report input/conversations-export.zip <block-id> output/block-phrases-to-next.xlsx
scripts/debugger block-fallback-phrases-report input/conversations-export.zip <block-id> output/block-fallback-phrases.xlsx
scripts/debugger block-next-blocks-report input/conversations-export.zip <block-id> output/block-next-blocks.xlsx
scripts/debugger block-previous-blocks-report input/conversations-export.zip <block-id> output/block-previous-blocks.xlsx
scripts/debugger block-phrases-to-current-report input/conversations-export.zip <block-id> output/block-phrases-to-current.xlsx
scripts/debugger block-bot-messages-report input/conversations-export.zip <block-id> output/block-bot-messages.xlsx
scripts/debugger block-previous-bot-messages-report input/conversations-export.zip <block-id> output/block-previous-bot-messages.xlsx
scripts/debugger block-previous-user-messages-report input/conversations-export.zip <block-id> output/block-previous-user-messages.xlsx
```

Generate a multi-sheet drilldown workbook for a specific block id:

```bash
scripts/debugger block-drilldown-report input/conversations-export.zip <block-id> output/block-drilldown.xlsx
```

Generate an SVG graph of block transitions from `messages.json`:

```bash
scripts/debugger conversation-graph-report input/conversations-export.zip output/conversation-graph.svg
```

Generate the graph with readability filters and also save the intermediate Graphviz DOT file:

```bash
scripts/debugger conversation-graph-report input/conversations-export.zip output/conversation-graph.svg --dot-output output/conversation-graph.dot --min-node-turns 10 --min-edge-count 5 --min-edge-percent 2 --top-outgoing 5
```

Generate an advanced interactive HTML version of the block graph:

```bash
scripts/debugger conversation-graph-html-report input/conversations-export.zip output/conversation-graph.html
```

In the interactive block graph, higher fallback rate is shown with a redder and thicker node border; the HTML report includes a legend for this encoding.

Block graph node details include `Context name`; when the export contains multiple contexts, node labels also show the context name above the block name.

Block graph node details include `Quick Reply Rate`, calculated as the share of inferred quick-reply offers from that block where the next user message matches one offered quick reply.

Block graph node details show `Tags` from the previous exported row for each block turn, because current-row tags describe the bot path after the user's reply and may belong to later blocks.

Clickable user-message and bot-message rows in the block graph sidepanel open modal sample conversations. The modal includes session IDs, commands, tags, NLU results, timing metrics, and extra diagnostic data, but it intentionally omits author information. Block and context details are shown before the user reply because they describe the block/context that requested that reply.

Generate an SVG graph of ordered tag transitions from `messages.json`:

```bash
scripts/debugger tag-conversation-graph-report input/conversations-export.zip output/tag-conversation-graph.svg
```

Generate the tag graph with readability filters and also save the intermediate Graphviz DOT file:

```bash
scripts/debugger tag-conversation-graph-report input/conversations-export.zip output/tag-conversation-graph.svg --dot-output output/tag-conversation-graph.dot --min-node-occurrences 10 --min-edge-count 5 --min-edge-percent 2 --top-outgoing 5
```

Generate an advanced interactive HTML version of the tag graph:

```bash
scripts/debugger tag-conversation-graph-html-report input/conversations-export.zip output/tag-conversation-graph.html
```

In the interactive tag graph, higher tag drop rate is shown with a redder and thicker node border; the HTML report includes a legend for this encoding. Tag drop rate excludes endings with explicit `Disconnect` or `Redirect` commands.

Create an XLSX report with tag drop rate and terminal rate statistics:

```bash
scripts/debugger tag-drop-terminal-report input/conversations-export.zip output/tag-drop-terminal-report.xlsx
```

The tag XLSX includes `Sessions percentage of all sessions` for tag reach, `Terminal rate` for sessions that contained the tag, and `Terminal sessions percentage of all sessions` for terminal sessions against the whole export. `Drop rate` counts final tag runs with no later user message only when the export has no later/same-row `Disconnect` or `Redirect` command.

## Multi-host configuration

The CLI now supports multiple Automate deployments in one local config.

- Define each deployment under `hosts`
- Point each profile at a host alias with `profiles.<name>.host`
- Use `defaultHost` as the fallback when a profile does not define `host`
- Override the selected host at runtime with `--host <alias>` when needed
- Override the selected profile at runtime with `--profile <name>`

Example:

```json
{
  "defaultProfile": "viber-prod",
  "defaultHost": "production",
  "hosts": {
    "production": {
      "server": "https://chatbots.sentione.com"
    },
    "staging": {
      "server": "https://staging-chatbots.sentione.com"
    }
  },
  "profiles": {
    "viber-prod": {
      "host": "production",
      "projectId": "00000000-0000-0000-0000-000000000000",
      "directories": {
        "exportZips": "/Users/admin/repos/AIP/viber/input",
        "workspaceRoot": "/Users/admin/repos/AIP/viber/work",
        "importZips": "/Users/admin/repos/AIP/viber/output"
      },
      "apiKey": {
        "service": "sentione-automate",
        "username": "default"
      }
    },
    "viber-staging": {
      "host": "staging",
      "projectId": "11111111-1111-1111-1111-111111111111",
      "directories": {
        "exportZips": "/Users/admin/repos/AIP/viber/input",
        "workspaceRoot": "/Users/admin/repos/AIP/viber/work",
        "importZips": "/Users/admin/repos/AIP/viber/output"
      },
      "apiKey": {
        "service": "sentione-automate",
        "username": "staging"
      }
    }
  }
}
```

Backward compatibility:

- Older configs that keep `profiles.<name>.server` instead of `hosts` still work
- The new host-alias model is preferred because it makes multiple deployments explicit

## Recommended workflow

### 1. Export the target project
Prefer the local API workflow:

```bash
scripts/automate export
```

If the local API workflow is not configured, copy the target Automate export ZIP into `input/`.

### 2. Open the repo in your coding agent
Work only inside this repository, with local file access. The agent picks up
`AGENTS.md` (or the symlink for its own tool) on its own.

### 3. Start with analysis only
Always begin with an analysis prompt.
Do not let the agent edit files immediately.

The first step should always be:
- export or unpack the target project into `work/current_export`
- inspect the target export
- inspect the reference export
- identify verified reusable block templates
- propose a minimal change plan

### 4. Use the reference export
If a needed block type exists in the selected reference project from reference/, reuse it as a structural template.

Do not let the agent invent block schema.

### 5. Approve the mapping before implementation
Before applying changes, require the agent to show:
- which files will be modified
- which states will be added or changed
- which reference state is used as a template for each new or changed state
- how memory will be written
- whether tests or integrations will be changed

### 6. Apply changes only after approval
Only after reviewing the mapping should the agent modify the unpacked target export.

### 7. Create a new ZIP
The updated ZIP must be created in `output/` in the following format: output/<project_name>_<YYYYMMDD>_<short_description>.zip

Never overwrite the original ZIP from `input/`.

### 8. Import through the API when configured
If the local API workflow is configured, import the validated ZIP back through the API:

```bash
scripts/automate import output/<project_name>_<YYYYMMDD>_<short_description>.zip
```

### 9. Validate manually
After the agent creates the updated ZIP or imports it through the API:
- inspect changed files
- import the ZIP into Automate
- verify the flow on the canvas
- check block correctness
- verify layout readability
- verify memory writes
- verify routing
- run `python3 scripts/validate_export.py <unpacked export>` before importing
- after an import through the API, export the project again and compare it with what was built
- train the NLU in the NLU module (the public API cannot do it) and test the answers in the NLU tester
- if the flow runs but the canvas looks wrong (for example no connectors), bisect on throwaway projects (Playbook J2)

## Important rules

- Always read `AGENTS.md` first.
- Always use analysis first, implementation second.
- Never invent Automate block schema.
- Never guess required fields.
- Never pass the Automate API key through chat, explicit CLI parameters, or environment variables.
- It is acceptable to choose a non-secret host alias or profile with CLI flags such as `--host` and `--profile`.
- Reuse only verified block structures from the target export or the reference export.
- If no valid example exists, stop and ask for clarification.
- Do not modify `integrations.json` unless clearly required.
- Do not add tests unless explicitly requested.
- Do not commit or push automatically unless the user explicitly wants that.

## What to commit

Usually safe to commit:
- `AGENTS.md`
- `README.md`
- `scripts/`
- `.gitignore`
- the selected reference project from reference/

Usually do not commit:
- `input/`
- `work/`
- `output/`
- unpacked reference folders

## Prompting pattern

A good task has two phases:

### Phase 1: analysis
Ask the agent to:
- inspect the target export
- inspect the reference export
- identify files to change
- identify verified template states
- propose a minimal plan

### Phase 2: implementation
Ask the agent to:
- apply only the approved plan
- reuse verified templates
- preserve export structure
- create a new ZIP in `output/`
- summarize all changed files and state mappings

## If something goes wrong

If the export imports but a block is invalid:
- do not continue blindly
- inspect the broken block
- compare it with a valid block from the reference export
- update `AGENTS.md` if a new safety rule should be added

## Goal

The goal is not to let an agent freely generate Automate flows from scratch.

The goal is to use the agent as a safe editor of structured Automate exports, guided by:
- `AGENTS.md`
- verified reference templates
- minimal change plans
- manual approval before implementation

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
Contributions are covered by the same licence; see
[`CONTRIBUTING.md`](CONTRIBUTING.md) for how they are reviewed and applied.
