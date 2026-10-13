# Repository Guidelines

This file is the single source of rules for every coding agent working here.
`CLAUDE.md` and `.github/copilot-instructions.md` are symlinks to it, and
`.claude/skills` and `.github/skills` are symlinks to `.agents/skills/`. Always
edit this file, never a symlink target of your own making: a second copy of a
rule will go stale and some agent will then follow the stale one.

## Response language

You, the coding agent working in this repository, always reply to the user in the language they write to you in. This is independent from the language the bot being built will speak to its own end users — that is a separate decision, confirmed explicitly in the Mandatory startup sequence below, never assumed from the language of this instruction or of the conversation around it.

## Learning and self-improvement

This project is in active development which includes building new skills, implementing new scripts, optimizing process, improving documentation, and adding reference projects.

While working on this repository please consider:

- searching for solutions in the online Automate documentation at `https://automate.help.sentione.com`
- updating `AUTOMATE_EXPORT_PLAYBOOK.md` or the relevant `.agents/skills/*/SKILL.md` with any new insights or patterns you discover
- creating helper scripts for any manual steps you find yourself repeating, and adding them to the `scripts/` folder with usage instructions in relevant .md files.

When users will work with this project and you will find any of the above issues, please suggest to improve this repository by adding the missing information, patterns, or scripts. The goal is to make this framework more and more robust and self-sufficient over time, so it can be used as a reliable reference for future bot-generation work.

## Mandatory startup sequence

Before doing anything else in any task, always execute these steps in order:

1. Read `flows.schema.json` in the repository root.
   Use it as a structural validator for all changes to `flows/*.json`.

2. Read `reference/REFERENCE_PROJECTS.md` to understand available reference projects.
   Do not select a reference project automatically.
   Wait until step 4 is complete and task requirements are known.

3. Determine whether the task is:
   - bot/project work on a real Automate export
   - or repository/tooling/documentation work on this framework itself
   If it is repository/tooling/documentation work, do not block on input ZIP handling.
   For those tasks, proceed after step 4 and only use reference projects when they are actually relevant.

4. Extract task requirements from the current conversation context.
   If any information needed to proceed is missing or ambiguous, ask the user before proceeding.
   The bot's target response language is one of these required-but-often-implicit items: if it is not explicit in the task, ask before building — never default it, including defaulting to Polish just because the task or this repository's examples happen to be in Polish.

5. For bot/project work, read `AUTOMATE_EXPORT_PLAYBOOK.md` and identify the procedures that apply to the requested changes.
   This file is the repository's Automate export-editing reference, not an agent skill.

6. For bot/project work, prefer the local Automate Public API workflow over manual ZIP handling.
   Check whether the local API helper scripts are available and whether local API configuration is already set up.
   If they are available, use them to fetch the target project export into `TARGET_WORKDIR`.
   Do not ask the user to paste the API key.
   Do not read secrets from ENV variables.
   Do not require secrets to be passed as explicit script parameters.
   Do not print, log, or echo any secret value.

7. If the local API helper scripts are not available, or local API configuration is not set up, or the user explicitly provides a ZIP-based task, fall back to scanning the `input/` folder.
   If `input/` contains exactly one ZIP file, use it as the input project. Do not ask.
   If it contains more than one ZIP file, list them all and ask the user which one to use before proceeding.
   If it is empty and no API-based workflow is available, ask the user to provide a ZIP file before proceeding.

8. For bot/project work, based on the task requirements from step 4, briefly summarize each available reference project
   and give a clear recommendation with reasoning for which one best fits the task.
   Ask the user to confirm the choice or select a different one before unpacking the reference project.

9. Unpack the selected reference ZIP into `REFERENCE_WORKDIR`.
   If the target export came from a ZIP, unpack it into `TARGET_WORKDIR`.
   If the target export came from the API, keep the exported ZIP and the unpacked project in `TARGET_WORKDIR`.
   Output ZIP will always be written to the `output/` folder unless the task explicitly requires importing through the API.

10. Only after completing the relevant steps above, proceed with the requested phase
   (analysis or implementation).

## Agent skills

These task-specific skills are separate from the repository-wide procedures in `AUTOMATE_EXPORT_PLAYBOOK.md`.

- `.agents/skills/automate-api/SKILL.md` — operate on SentiOne Automate through the local Public API helper, including project import/export, conversations, AI credentials, knowledge bases, and dialer contacts
- `.agents/skills/chunker-api/SKILL.md` — prepare RAG and knowledge-base content with the SentiOne Chunker API
- `.agents/skills/debugger/SKILL.md` — analyze SentiOne conversation-export ZIPs and generate diagnostic reports

Consult the relevant `SKILL.md` before starting a task covered by its scope.

## Project Structure & Modules
- This repository is a SentiOne Automate project export. Treat the ZIP as the source of truth for bot structure, not as a generic code project.
- This repository also contains a local OpenAPI definition for Automate public integrations:
  - `senti0ne-automate-public-api.json` — local OpenAPI description of the SentiOne Automate Public API
- Keep the root export layout unchanged:
  - `project.json` — project identity, language, main flow reference, bot response languages.
  - `projectMetadata.json` — platform version, supported `flowVersion`, changelog for export compatibility.
  - `flows/*.json` — full flow definitions. In this export there is one main flow file.
  - `nlu/<NLU name>/data.json` — NLU metadata and model settings.
  - `nlu/<NLU name>/intents.csv` — list of intents.
  - `nlu/<NLU name>/entities.csv` — entity dictionaries and built-in entity definitions.
  - `nlu/<NLU name>/phrases.csv` — training phrases mapped to intents.
  - `nlu/<NLU name>/labels.csv` — optional labels file, may be empty.
  - `integrations.json` — reusable HTTP integrations and request definitions.
  - `testSuites/<suite name>/data.json` and `*.txt` — automated conversation tests.
- Do not rename folders or move files. Import/update in Automate expects the export shape described in the docs and used in this ZIP.
- Knowledge Base content is NOT part of the project export. If the flow references `knowledge.*`, those items must exist separately on the target environment.

## Automate Public API workflow
- Prefer local API helper scripts over manual browser work and ad hoc `curl` commands when working with real Automate projects.
- Treat `senti0ne-automate-public-api.json` as the local contract for the public API.
- For project import/export work, the relevant endpoints are:
  - `GET /projects`
  - `GET /projects/{id}`
  - `GET /projects/{id}/export`
  - `POST /projects/{id}/import`
- The API uses header authentication with `X-Api-Key`.
- Never ask the user to paste the API key into chat.
- Never store the API key in the repository.
- Never require the API key through explicit CLI parameters.
- Never require the API key through environment variables.
- Never print the API key, even partially.
- The local scripts must load configuration from an OS-specific user config location outside the repository.
- The local scripts must load the API key from an OS-managed secret store or keychain, not from tracked files.
- The local scripts must work on Windows, Linux, and macOS.
- Prefer one cross-platform implementation with thin platform launchers over three separate feature implementations.
- If the API workflow is configured, use it as the default way to:
  - list available projects
  - export a target project before editing
  - import the result after validation
- If the API workflow is not configured on the current machine, fall back to ZIP-based handling without trying to invent credentials.

## Local API script contract
- Keep the local API scripts in a dedicated `scripts/` area.
- Provide at least these capabilities:
  - list available projects
  - export a configured project to a local ZIP
  - import a ZIP back to a configured project
  - optionally publish flows on import when the task explicitly requires it
- Resolve non-secret configuration from a default user config path, not from explicit parameters or ENV.
- Recommended config content:
  - Automate server URL
  - default organization/profile alias
  - default project ID or project alias map
  - default import/export directories
  - keychain secret name or credential reference, not the secret itself
- Recommended config locations:
  - Windows: `%AppData%/SentiOneAutomate/config.json`
  - macOS: `~/Library/Application Support/SentiOneAutomate/config.json`
  - Linux: `~/.config/sentione-automate/config.json`
- Keep secrets separate from normal config.
- The agent may read non-secret config structure when needed, but should avoid opening files that may contain raw secrets.
- If the local setup stores secrets in a way that would expose them to agent context, stop and ask for a safer setup before continuing.

## Flow schema rule
- If `flows.schema.json` is present in the repository, use it as an additional structural validation source when editing `flows/*.json`.
- Do not introduce fields that are inconsistent with `flows.schema.json`.
- Treat `flows.schema.json` as a schema-level validator, not as a replacement for verified block templates from the target export or the reference export.
- If the schema, the target export, and the reference export do not clearly support a planned field or block shape, stop and ask instead of guessing.

## How This Export Actually Works
- `project.json.name` is the project name shown in Automate.
- `project.json.language` defines the NLU language for the project.
- `project.json.mainFlowId` points to the `referenceName` of the entry flow file.
- `flows/*.json` store flows as JSON graphs:
  - flow
  - contexts
  - states inside each context
  - transitions between outputs and destination states
- In practice, transitions do **not** connect block id to block id. They connect an **output id** from one state to the destination **state id**. If you edit transitions manually, preserve this rule or the flow will break.
- State `type` values observed in this export include:
  - `start`
  - `say`
  - `say-conditional`
  - `custom`
  - `conversationMetadata`
  - `empty`
  - `context`
  - `Integration`
  - `say-llm`
  - `llm-integration`
  - `redirect`
  - `end`
  - `terminate`
- This export uses grouped contexts as a design convention. The observed groups are:
  - business/self-service contexts
  - helper contexts
  - global contexts
  - error handlers
  - API contexts

## Flow Architecture Rules
- Build bots as small contexts with clear responsibility, not as one giant canvas.
- Keep reusable external logic in dedicated API contexts. In this export, token retrieval and API orchestration are isolated instead of duplicated everywhere.
- Use `context` blocks for routing between contexts. Use `end` to leave a context and return to the previous caller. Use `terminate` only when the whole conversation should end.
- Use `empty` quick points for canvas readability and branching. They are structural helpers, not business logic.
- Use `conversationMetadata` blocks for observability and debugging. In this export they are used to push important API payloads and derived values into metadata.
- Do not leave any block unconnected. Every added state should have valid incoming and outgoing routing unless it is intentionally final.
- A context may contain more than one `start` block, but each one must lead into its own separate, non-overlapping tree of states. Never wire two `start` blocks into the same downstream subgraph.
- Global Listener is a context, and it only works when it is attached as a parent tree: in every context where the user can speak, add a second `start` block that leads to a `context` block calling the Global Listener context, placed at the very top of that context. Leave that block's output unconnected (the canvas shows `+`); the platform returns to the interrupted block. This is the one intended exception to "no unconnected outputs", and `scripts/validate_export.py` reports it.
- Let the block that waits for the user also speak the prompt (a `say` with `requestUserInput`), so that returning from the Global Listener repeats the current prompt. Silence, misunderstanding and similar loops should change a prompt memory value and loop back to that block.
- Observed on the platform: after the Global Listener context ends, the interrupted block is not simply re-asked; its outputs are evaluated again against the same (or, after a question asked inside the listener, the latest) user utterance. Without a guard, an answered "kto dzwoni" falls into the block's "unclear" output and counts as a misunderstanding, and a "nie" given to a question asked inside the listener can be read as the block's own "nie" (an irreversible action). When the listener itself waited for an answer (a confirmation question), the platform was also seen to just ask the interrupted block again, so a boolean flag stays set and swallows the next real answer. Pattern: the listener stores the handled utterance (`memory.listenerInput = nlu.user_input`, also on its own "no" path before it ends); every waiting block has `memory.listenerInput != null && memory.listenerInput == nlu.user_input` as its FIRST output, leading to the fallback context, whose first branch clears it and ends without touching counters or the prompt mode; the caller then loops back to the question. Test every scenario under both return semantics (re-evaluate outputs / re-ask).
- When generating contexts from code, give `context.model` the shape of exports that carry real flows: `name`, `uuid` (equal to the context `uuid`), `notes`, `states`, `transitions`. The `x`/`y`-only model of `reference/empty polish project.zip` imports and runs, but the canvas then shows no connectors and every output looks unconnected.
- An `empty` block that routes (several outputs or conditions) must not carry `isEmptyPoint`, `isQuickPoint` or `useNER`. Only a pure quick point (one output, no conditions) has `isEmptyPoint: true`. A routing block flagged that way is drawn as a diamond without outputs and the canvas then shows no connectors in the whole context, although the flow still runs (bisected on throwaway projects in this repo's history). `isQuickPoint: true` on routing blocks caused the same symptom: no Finance/Medical routing block has it.
- The conversation ending context (`conversationEndingContextRef`, changelog v266) runs after every ending, including endings caused by the bot. Anything reported from it needs a "already reported" guard.

## No regular expressions in flow blocks
- Do not put regular expressions in `flows/*.json`: not in AEL, and not in JavaScript (`.test(`, `.match(`, `replace(/…/)`, `split(/…/)`, `RegExp`). Recognition belongs in the NLU module: intents, keyword entities, regex entities, pattern (MTT) entities.
- Read yes/no from the MTT pattern entities (`mtt_yes`, `mtt_no`; reference rows in `scripts/nlu_data/`). Treat an answer as yes only when `mtt_yes` is present without `mtt_no`, and the other way round. Add a keyword entity for hedging ("nie wiem", "chyba", "może") and let it win over both, so "chyba nie" is never an unambiguous "no".
- Never take an irreversible action (blocking a card, cancelling, deleting) on anything but an unambiguous "no"/"yes"; unclear answers lead to a clarification.
- Check that the user said anything with `nlu.user_input` (empty or `null` means silence). Do not add an intent only to detect that.
- Guard global intents with `nlu.intentScore` (for example `>= 0.6`) and keep their training phrases away from the entities that decide answers: a phrase that starts with "nie" collides with `mtt_no`.
- `nlu.variables.time` is a single object (`value`, `grain`, `type`, `values[]`), not an array: use `nlu.variables.time.value.formatAsDate()`. `time[0]` fails at runtime with `Bad arguments for getIndex operation, needed single StringValue, got List(LongValue(0))`. Verified in the NLU analyzer's variable preview. Use `nlu.variables.time.values[0].value` only when the first alternative is needed.
- The public API cannot train an NLU. After every import the NLU must be trained manually, and until then `nlu.intent` is empty.

## NLU Structure
- `nlu/.../data.json` defines the NLU itself. In this export:
  - model type is `llm`
  - confidence threshold is configured in JSON
  - the flow references this NLU through `defaultNluId`
- `intents.csv` is a flat list of intents. Keep intent names stable, because flow conditions and analytics often depend on them.
- `entities.csv` contains entity name, canonical value, synonyms, entity type, and optional config. This export mixes:
  - keyword entities for business vocabulary
  - doctor lists
  - built-in entities such as surname, numeral, time, duration
- `phrases.csv` maps user utterances to intents and stores token spans. Edit with care. If you regenerate phrases incorrectly, NLU quality will drop even if the file still imports.
- After importing only NLUs, Automate requires manual training. Plan this into every delivery.

## Integrations
- `integrations.json` stores shared HTTP integration definitions. Each integration contains:
  - integration UUID and reference name
  - base URL
  - request definitions
  - methods, paths, headers, bodies, input parameters
  - optional auth settings
- Flow `Integration` blocks do not embed full HTTP config. They reference:
  - `integrationReferenceName`
  - `requestReferenceName`
- Because of that, when you clone or edit integrations manually:
  - do not change request UUIDs or reference names unless you also update every matching block in flows
  - preserve input parameter names expected by the flow
- In JSON-mode integration request bodies, placeholder braces control how values are serialized:
  - `{someParameter}` inserts a complete JSON node; a string value is serialized with its own quotes
  - `{{someParameter}}` inserts escaped string content and must be used when the placeholder is already inside JSON quotes
  - for example, use `{"someParameter": "{{memory.myStringValue}}"}`, not `{"someParameter": "{memory.myStringValue}"}`; the single-brace form can produce doubled quotes and invalid JSON
- Validate the resolved request body with representative runtime values, not only the unresolved template.
- This export shows a good separation:
  - OAuth/token integrations
  - business APIs
  - mock/demo data integration
- Integration request bodies may contain production-shaped placeholders. Keep placeholders intact and only change values that are actually meant to be dynamic.

## LLM Blocks
- This export uses both `say-llm` and `llm-integration`.
- Use `say-llm` when the block should generate conversational output or make a tool call during the dialogue.
- Use `llm-integration` when the model should return a machine-readable result into memory for routing or later use.
- Keep prompts tightly bounded. In this export, LLM modules are deliberately narrow:
  - classify confirmation vs rejection
  - interpret date preference
  - passively detect a new date preference in the background
  - word a single appointment proposal naturally
- Do not let LLM blocks own the entire process. Deterministic logic still decides:
  - whether a slot exists
  - which slot is best
  - whether escalation happens
  - whether booking is attempted
- This hybrid pattern is safer than giving full control to the model.
- Favor response speed when choosing a model for `say-llm`/`llm-integration` blocks — the bot is holding a live conversation with a user, not running a batch job. Do not default to GPT-5; in practice it responds too slowly for this use case. A "mini"-tier model (e.g. GPT-5.4 mini, GPT-4.1 mini, GPT-4o mini) is the right default for blocks without tool calling.
- Exception: a `say-llm` block that uses tool calling (non-empty `tools`) must use a model from outside the "mini" group, e.g. `gpt-4.1`. Mini models are not reliable enough at choosing when to call a tool and at filling its arguments. Still do not pick GPT-5 for speed reasons.
- Streaming (`botResponseBuffering`) in every `say-llm` block is ALWAYS set to full sentences: the exported value is `"Sentence"` (verified from a manual UI change exported from the NBP invoice project; reference templates carry `"Word"`, which must not be copied).
- Never paste a full JSON object into a prompt field (`context`, `developerMessage`, `userMessage`). To describe an expected response shape, describe the fields and types in prose; to pass data in, interpolate only the specific values actually needed.

## Memory, AEL, and JavaScript
- Simple assignments should stay in plain AEL.
- Use JavaScript only where transformation is genuinely complex:
  - filtering arrays
  - ranking results
  - composing payload objects
  - extracting normalized values from `nlu.variablesList`
  - formatting derived structures for later blocks
- In AEL, comparison is written with a single `=`, not `==` as in JavaScript. For example, a simple conditional checking the channel is `if (system.source = "phone") ... else ...`, not `system.source == "phone"`. Use `==` and `===` only when the field is JavaScript (`useJS: true`).
  - This applies to raw AEL expression strings. Structured output conditions in `flows/*.json` keep the export shape `{ left, type, right, operator }`, where `operator` is one of the values allowed by `flows.schema.json` (including `==`); do not change that.
- Preserve `useJS` flags correctly. A string that looks like JS but is stored with `useJS: false` will be treated as plain text.
- Important observed memory design patterns:
  - raw API results kept under `memory.response.*`
  - normalized business objects stored separately
  - user preference stored separately from selected best term
  - counters for fallback, silence, agent request, and negotiation loops
  - debug-ready request/response payloads saved into memory and metadata
- Prefer stable, readable memory keys.
- Always write AEL and JavaScript in a human-readable way.
- Prefer readable formatting over compressed one-line expressions.
- Use indentation, spacing, and line breaks so the logic is easy to inspect and debug.
- In `custom` blocks, keep JavaScript structured into clear steps instead of dense chained expressions when possible.
- Prefer clear variable names and intermediate variables when they improve readability.
- Separate logical parts with blank lines when it makes the code easier for a human to follow.
- Do not optimize for shortest code. Optimize for maintainability and safe manual review.
- When modifying existing code, preserve or improve readability.
- A nested memory key's parent object (e.g. `memory.invoice` for `memory.invoice.date`) must already exist at the point in the dialog where anything reads it, or the conversation ends in a runtime error. Initialize the parent explicitly earlier in the dialog (e.g. in the start/reset state) before any nested read, or avoid the nesting and use a flat key instead (e.g. `memory.invoiceDate`).

## Memory write rule
- Do not assume a generic memory-write schema.
- Reuse the exact memory structure from a valid reference block.
- In this repository, valid `custom` blocks may use a `memory` object where each entry contains:
  - `index`
  - `useJS`
  - `value`
- Before finalizing a change, explicitly confirm:
  - which state writes to memory
  - which memory path is written
  - which exact field structure is used
  - whether the written value is raw input or normalized data
- If no verified memory-write template exists, stop and ask instead of guessing.

## Commands and Voice-Specific Behavior
- Commands can be attached to blocks and are channel-dependent.
- This export shows a voicebot pattern with ASR and DTMF tuning on PESEL collection.
- Use commands for channel behavior, not for business logic.
- For voice flows, keep special attention on:
  - ASR timeout length
  - DTMF expected digit count
  - recognize model for names, spelling, or addresses
  - redirect commands for handover
- Test command assertions in test suites when the command matters to the user experience.

### Voice text must be phonetic (TTS and ASR friendly)
- A bot that serves the voice channel always speaks digits, numbers, amounts, dates, codes and abbreviations phonetically, as words that a TTS reads correctly and an ASR can recognize, for example "cztery tysiące trzysta siedemdziesiąt pięć złotych" instead of `4 375,00 zł`, "dwudziestego piątego września dwa tysiące dwudziestego szóstego" instead of `2026-09-25`, "en be pe" instead of `NBP`. No digits or symbols such as `%`, `/`, `-`, `zł`, and no currency codes, in anything the bot says on voice, static `say` texts included.
- The text channel keeps normal digits. When a bot serves both, set the channel once per turn from `system.source` into a memory key and branch on it.
- Compute the spoken forms deterministically in JS (cardinal numbers with correct declension of the unit, ordinal dates, rates digit by digit after the comma) and hand them to the LLM as separate fields; never rely on the LLM to convert numbers itself. Decide this at plan time, not after the first voice test.
- Expect the user's voice input in words or digits ("dwanaście tysięcy pięćset"); the LLM tool or NLU must write them as digits in structured fields.

## Global Listener and Global Fallback
- Keep them as separate contexts.
- Global Listener should catch cross-cutting intents such as:
  - agent request
  - goodbye
  - repeat
  - silence
  - waiting
  - emergency
  - new date preference spoken out of turn
- Global Fallback should be stateful. In this export, counters are used to decide whether to retry, clarify, or escalate.
- Do not bury global logic inside the main business context. It becomes unmaintainable very quickly.

## Canvas layout and spacing rules
- Preserve readable spacing between states on the canvas.
- Keep generous horizontal and vertical spacing between blocks.
- Do not place blocks tightly next to each other.
- Leave enough space so state names, outputs, and connectors remain readable after import.
- Prefer a clean left-to-right main path.
- Keep each business path visually separated from other paths.
- Keep FAQ, fallback, and “not recognized” paths below the main path when possible.
- Keep alternative paths, such as status-check flows, visually separate from reporting flows.
- Keep confirmation and ending states at the far right of the flow when possible.
- Avoid overlapping connectors.
- Avoid placing return loops directly on top of main-path connections.
- Leave extra spacing around routing blocks such as `say-conditional` and blocks with multiple outputs.
- After finishing the logic, perform a final layout pass focused only on readability.
- Reuse positioning patterns from valid states already present in the target export or the reference export.
- Do not invent layout schema.
- If the positioning structure is unclear, stop and ask instead of guessing.
- Optimize for readability after import, not for minimal canvas width.

## SentiOne Automate documentation
- The SentiOne Automate documentation is available here:
  - `https://automate.help.sentione.com/docs/getting-started`
- Use the documentation as an additional reference when the target export, the reference export, and `flows.schema.json` do not fully clarify how a supported Automate feature should work.
- Prefer the current export and verified reference examples over generic assumptions.
- Do not invent unsupported block structure even if the documentation is incomplete or ambiguous.
- If the documentation, the target export, and the reference export do not clearly confirm a planned change, stop and report the ambiguity instead of guessing.

## Analytics and Tags
- Use tags deliberately.
- This export tags:
  - business milestones
  - API successes and failures
  - authorization results
  - escalations
  - fallback/error scenarios
- Keep tag names stable. They often drive analytics, regression tests, and post-implementation reporting.

## Test Suites
- Treat `testSuites` as part of the bot, not as optional extras.
- `data.json` in the suite lists the included test cases.
- Each `*.txt` file is a scripted conversation and may include:
  - every test case must start with `> *` as the first line, because Automate test conversations must be triggered by a user message or an empty user message
  - `>` user utterance
  - `<` bot response assertion
  - `*<` wildcard bot response assertion
  - `?<` regex assertion
  - `#` tag assertions
  - `cmd NAME @ PARAMETER` command assertions
  - `<< JSON` mocked extra data
  - `<i JSON` mocked integration response
  - `<t TIME` mocked current time
  - `assert ...` JavaScript assertions
- When you change flow logic, update tests in the same change set.

Unless explicitly requested otherwise: always add/update at least one happy-path test and one failure-path test for the changed context

## Hidden Dependencies and Migration Risks
- The export alone is **not** the full runtime environment.
- This ZIP clearly depends on things that are external to the export:
  - Knowledge Base items such as doctor data and calendar phrasing
  - LLM credentials referenced by `credentialsId`
  - channel configuration
  - environment-specific integrations and secrets
- Before calling a project “ready”, verify all of the above on the target environment.
- Never assume that importing the ZIP is enough to make the bot production-ready.

## Safe Editing Rules
- Preserve all UUIDs, reference names, and output ids unless you intentionally rebuild the affected graph.
- When editing a state:
  - keep its `id`
  - keep existing outputs unless routing is consciously changed
  - keep transitions aligned with output ids
- When editing a context block that calls another context:
  - preserve `contextReferenceName`
  - verify the destination context still exists
- When editing an Integration block:
  - preserve `integrationReferenceName`
  - preserve `requestReferenceName`
  - verify `outputValues` still map into the expected memory paths
- When editing tests:
  - every test case must start with `> *` as the first line
  - mock integrations before asserting commands or tags
  - keep one integration mock per message turn
- When editing NLU:
  - keep intent names stable
  - keep entity naming consistent with flow expressions
  - retrain after import

## Naming Conventions
- Keep context names human-readable. They are a working interface for designers.
- Use state names that describe intent, not UI appearance.
- Good examples from this export:
  - “zapisz request searchVisit”
  - “czy są dostępne terminy u danego lekarza?”
  - “ostatnia szansa na rozpoznanie”
  - “push memory.api to metadata”
- Prefer names that reveal purpose in the debugger and on the canvas.

## Validation Checklist Before Re-Zipping
- Confirm `project.json.mainFlowId` points to an existing flow `referenceName`.
- Confirm every `contextReferenceName` points to an existing context in the flow.
- Confirm every `integrationReferenceName` and `requestReferenceName` exists in `integrations.json`.
- Confirm output transitions still point from output ids to valid state ids.
- Confirm every generated or edited `flows/*.json` file matches `flows.schema.json` in the repository root.
- Confirm all edited AEL and JS expressions are syntactically valid.
- Confirm NLU files stay in UTF-8 CSV/JSON format.
- Confirm tests cover the changed scenarios.
- Confirm any required Knowledge Base items exist outside the ZIP.
- Confirm the target environment has the needed credentials and channels.
- Confirm the ZIP preserves the folder structure exactly.
- Confirm every new/changed `say-llm` or `llm-integration` block's model choice favors response speed (a "mini"-tier model such as GPT-5.4 mini, GPT-4.1 mini, or GPT-4o mini) rather than GPT-5, for this live-conversation use case, except `say-llm` blocks with tool calling, which use a non-mini model such as `gpt-4.1`.
- Confirm every new/changed `say-llm` block streams full sentences (`botResponseBuffering`), not words.
- Confirm that a bot serving the voice channel writes digits, numbers, amounts, dates and abbreviations phonetically, and that the text channel keeps normal digits.
- Confirm every context with more than one `start` block has each `start` leading into its own fully separate subgraph, with no shared downstream states.
- Confirm no `say-llm`/`llm-integration` prompt field contains a pasted full JSON object instead of a prose description or targeted value interpolation.
- Confirm every nested memory path read in the flow (e.g. `memory.x.y`) has its parent object initialized earlier in the dialog than the first read, or is written as a flat key instead.
- Confirm no flow block contains a regular expression (`.test(`, `.match(`, `replace(/…/)`, `split(/…/)`, `RegExp`); recognition lives in the NLU module.
- Confirm every `empty` block that routes (several outputs or conditions) has no `isEmptyPoint`, no `isQuickPoint` and no `useNER`, and that only pure one-output quick points carry `isEmptyPoint: true`.
- Confirm every context `model` has `name`, `uuid` (equal to the context `uuid`), `notes`, `states`, `transitions` (not the `x`/`y`-only starter shape).
- Confirm the Global Listener is attached as a parent `start` tree in every context where the user can speak, and that its output is the only intentionally unconnected output.
- Confirm yes/no is read from the answer entities with a hedging entity first, and that no irreversible action follows an unclear answer.
- Confirm the ZIP being imported was produced by a build that finished (new timestamp), and compare an export of the imported project with what was built.
- Confirm the delivery tells the user that the NLU must be trained manually after import.

## Verified block schema rule
- Never invent the schema of an Automate block.
- Never guess required fields.
- Always reuse the structure of a valid block from the current export or from a provided reference export.
- Before editing, identify the exact reference state used as the template.

## Memory write rule
- Do not assume a generic key/value memory format.
- Reuse the exact memory schema from a valid reference block.
- In this repository, valid custom blocks may use a `memory` object where each entry contains:
  - `index`
  - `useJS`
  - `value`
- Before finalizing changes, explicitly confirm:
  - which state writes to memory
  - what memory path is written
  - what exact field structure is used

## Delivery Rules For Future Bot-Generation Work
- Produce full importable project exports, not only snippets, when the task requires an Automate-ready ZIP.
- When local API scripts are configured, prefer exporting the current project through the API before editing and importing the validated result back through the API after editing.
- If only one part changes, edit the minimum required files:
  - usually `flows/*.json`
  - sometimes `integrations.json`
  - sometimes `nlu/.../*`
  - often `testSuites/.../*`
- Always add or update fallback handling.
- Always include at least one regression test for the main happy path and one for a key failure path.
- If the bot uses authorization, keep that process separate from the main business flow.
- If the bot uses LLM, constrain it to narrow jobs and protect the process with deterministic logic.

## What Was Learned From This Specific Export
- SentiOne Automate exports are highly structured and can be edited outside the platform if you respect identifiers and graph wiring.
- The most important technical unit is not the whole flow file, but the trio:
  - **state**
  - **output**
  - **transition**
- A robust Automate bot is usually hybrid:
  - NLU for intent/entity capture
  - deterministic blocks for control
  - integrations for external actions
  - LLM for narrow interpretation or natural language generation
  - test suites for regression safety
- The cleanest long-term pattern is separation of:
  - conversation flow
  - external API calls
  - global behaviour
  - fallbacks
  - tests
  - NLU data

## Reference project rule
This framework may use multiple reference exports.

Before creating or modifying any state, first check whether the same block type or structural pattern already exists in:
- the target export
- the most relevant reference project selected for the task

Select the reference project based on the task type, bot architecture, and required implementation pattern.
Do not treat all reference projects as interchangeable.

Reuse the structure of a verified state or pattern and change only the minimum necessary fields.
If no valid example exists in either the target export or the selected reference project, stop and report the gap instead of guessing.

See `REFERENCE_PROJECTS.md` for the catalog and recommended usage of each reference project.
