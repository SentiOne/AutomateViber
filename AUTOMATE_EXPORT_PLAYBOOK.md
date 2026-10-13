# SentiOne Automate Export Editing Playbook

Verified procedural guidance for editing SentiOne Automate project exports in this repository.

---

## Purpose and scope

This file is a catalog of **verified, repeatable procedures** for the atomic editing operations that occur over and over when modifying SentiOne Automate exports. It complements the rest of the framework:

- `AGENTS.md` — defines **rules and constraints** (what must and must not happen).
- `flows.schema.json` — defines **structural validity** (what shape is allowed in `flows/*.json`).
- `README.md` — defines the repository workflow, local API tooling, and ZIP fallback handling.
- `AUTOMATE_EXPORT_PLAYBOOK.md` (this file) — defines **how to perform individual editing operations safely**, step by step.

Procedures are **not** new rules. They always defer to `AGENTS.md`, to `flows.schema.json`, and to verified templates from the target export or the selected reference project from reference. When a procedure and a rule disagree, the rule wins.

**Scope:** this file covers **editing of existing project exports** and **bootstrapping a new Polish-language project from the verified baseline ZIP** at `reference/empty polish project.zip`. It does not cover inventing a greenfield project schema from scratch, and it does not define a generic starter for other languages unless a verified baseline export is added for them. For non-bootstrap work, it still assumes a target export already exists with at least a main flow file, an NLU folder, and the standard Automate export layout.

This file is designed to be reusable across any SentiOne Automate project. Domain-specific examples are avoided on purpose. Placeholder names like `<endpointName>`, `<preferenceName>`, `<purpose>` appear where a real project would substitute its own values.

If a task needs an operation not covered here, and no verified template exists in the target or reference export, and the Automate documentation does not clarify, **stop and report the gap** instead of improvising.

---

## How the agent should use this file

In the analysis phase:

1. If the task is to create a new Polish bot from scratch, start with Procedure 0.1 before planning any deeper flow work.
2. Build the minimal change plan as instructed in the task.
3. For each planned change, name the procedure from this file that covers it.
4. If a planned change has no matching procedure, flag it in the "Risks or ambiguities" section of the analysis output.

In the implementation phase:

1. If the task is greenfield Polish project creation, apply Procedure 0.1 first and treat the unpacked baseline as the target export from that point onward.
2. For every approved change, follow the matching procedure step by step.
3. Do not skip verification sub-steps — they exist because real Automate imports have failed in those exact ways.
4. After all procedures are applied, run the Preflight checklist (Procedure H2) before packaging the result or importing it through the API.

---

## How to read a procedure

Every procedure is written with the same structure:

- **When to use** — the concrete trigger.
- **Prerequisites** — what must already be true in the export.
- **Template source** — where a verified example lives.
- **Procedure** — ordered steps.
- **Verify** — post-conditions to check before considering the procedure done.
- **Pitfalls** — failure modes observed in practice.

---

# Category 0 — Project bootstrapping

These procedures apply only when the task is to create a new project and there is no existing target export yet.

## 0.1 · bootstrap-new-polish-project-from-baseline

**When to use:** the user wants a new bot project created from scratch in Polish.
**Prerequisites:** no existing target export is being edited; `reference/empty polish project.zip` is available.
**Template source:** `reference/empty polish project.zip`.

**Observed baseline contents:**

- `project.json` with Polish language settings (`language: "pl"`, `botResponseLanguages: ["pl"]`, `defaultBotResponseLanguage: "pl"`).
- One flow file with `flowVersion: 7`, one context, and a minimal `start -> say -> terminate` path.
- One Polish NLU folder with `modelType: "simple"` and empty `intents.csv`, `entities.csv`, `phrases.csv`, and `labels.csv`.
- `integrations.json` as an empty array.
- `errorHandlingContextRef: null` in the baseline flow.

**Procedure:**

1. Copy `reference/empty polish project.zip` and unpack it into the new target working directory. Treat that unpacked export as the source of truth for the new project.
2. Rename the human-readable project identity everywhere it appears:
   - `project.json.name`
   - `flows/<flow file>.json` file name and the flow object's `name`
   - `nlu/<NLU folder>/` folder name and `nlu/.../data.json.name`
3. Keep the language Polish unless the task explicitly says otherwise:
   - `project.json.language` stays `pl`
   - `project.json.botResponseLanguages` stays `["pl"]`
   - `project.json.defaultBotResponseLanguage` stays `pl`
4. Generate fresh UUIDs for every project-owned artifact so the baseline or reference export is not reused as-is across multiple bots:
   - `project.json.uuid` — this is the project ID used by API import/export workflows. Always generate a new value for a new project, and never reuse the UUID from the baseline or any reference project; doing so can cause an API upload to overwrite that existing project.
   - `project.json.mainFlowId`
   - every flow `uuid` and `referenceName`
   - every flow `defaultNluId`
   - every NLU `uuid` and `referenceName`
   - every integration `uuid` and `referenceName` if the new project includes copied integrations
   - every integration request `uuid` and `referenceName` if the new project includes copied requests
   - every context `uuid` and `referenceName`
   - every optional context model `uuid` when present in the export shape
   - every state `id`
   - every output `id`
   - every conditional response `id`
5. Keep cross-file references aligned while regenerating IDs:
   - `project.json.mainFlowId` must equal the flow `referenceName`
   - flow `defaultNluId` must equal the NLU `referenceName`
   - every `Integration` state `integrationReferenceName` and `requestReferenceName` must point to the regenerated integration/request `referenceName`
   - every context caller `contextReferenceName` must point to the regenerated destination context `referenceName`
   - every `errorHandlingContextRef` must point to the regenerated error-handling context `referenceName`
   - every `conversationEndingContextRef`, when present and non-null, must point to the regenerated conversation-ending context `referenceName`
   - every transition `from` and `to` must be updated if the related output or state id changed
6. Do not blindly regenerate external dependency identifiers that are not owned by the export, such as LLM `credentialsId` values or Knowledge Base references. Verify those against the target environment separately.
7. Preserve the minimal baseline structure until actual requirements are known. The empty starter is only a skeleton, not a recommended final architecture. One thing must change as soon as real flows are generated or pasted in: the baseline context `model` is `{x, y, states, transitions}`, while every export that carries real flows uses `{name, uuid, notes, states, transitions}` with `model.uuid` equal to the context `uuid`. Give new or generated contexts the second shape (see B12).
8. Once requirements are known, choose the relevant reference project from `reference/REFERENCE_PROJECTS.md` for architectural patterns. Do not treat the empty baseline as a substitute for a real reference project.
9. Replace the placeholder greeting and terminal path only when the first real conversation requirement is being implemented. After bootstrapping, use the normal state, wiring, NLU, test, and layout procedures in this file.

**Verify:**

- The new export still matches the standard Automate folder layout exactly.
- `project.json.uuid` is a fresh project ID and does not match the baseline, selected reference export, or any known target project unless the task explicitly asks to update that existing project.
- `project.json.mainFlowId` points to the regenerated flow `referenceName`.
- Every flow `defaultNluId` points to a regenerated NLU `referenceName`.
- Every non-null `errorHandlingContextRef` and `conversationEndingContextRef` points to an existing context `referenceName`.
- All project-owned UUIDs in `project.json`, `flows/*.json`, `nlu/**/data.json`, and `integrations.json` are regenerated for the new project.
- No baseline or reference UUID remains reused accidentally in project, flow, NLU, integration, request, context, state, output, or conditional response identifiers.
- The starter flow still imports structurally: one start state, one reachable conversational state, one terminal state, and valid output-to-state transitions.
- `flows/*.json` validates against `flows.schema.json`.

**Pitfalls:**

- Reusing the baseline UUIDs unchanged across multiple new projects.
- Reusing a reference project's `project.json.uuid`; API upload/import can target or overwrite the project with that ID instead of the intended new project.
- Regenerating flow, NLU, or integration UUIDs without updating the linked reference fields that point to them.
- Blindly changing external IDs such as credentials, causing an otherwise valid import to fail at runtime.
- Renaming files or folders without updating the internal `name` or linked `referenceName` fields.
- Treating the empty baseline as an architecture template for integrations, fallbacks, global listeners, or tests. It is only a minimal starter.
- Changing the starter into a non-Polish project without a verified non-Polish baseline.

---

# Category A — Discovery

These procedures run **before** any editing. They make sure the agent knows exactly which block to copy, and how the current wiring works.

## A1 · locate-template-state

**When to use:** before adding or modifying any state.
**Prerequisites:** target export unpacked; reference export unpacked (if present).
**Template source, in order of preference:**

1. Target export — a state already working in a similar role.
2. The selected reference project from reference (unpacked) — a structurally plain example.
3. Local Automate documentation export (`docs/`) — consult only when neither export contains a usable template, and only to confirm supported schema. Documentation examples are **not** to be copied verbatim; they inform which fields are supported and what values they accept.
4. Online Automate documentation (`https://automate.help.sentione.com/docs/`) — consult when the local export is missing, ambiguous, or may be stale.

**Procedure:**

1. Decide the required `type` using the enum in `flows.schema.json` (`start`, `say`, `say-conditional`, `say-fallback`, `custom`, `conversationMetadata`, `log`, `empty`, `context`, `Integration`, `say-llm`, `llm-integration`, `nluModel`, `ask`, `ApiConnector`, `botResponseLanguage`, `redirect`, `end`, `terminate`).
2. Grep `flows/*.json` in the target export for a state with that `type` that is already functioning in a similar role.
3. If none exists in the target, search the reference export.
4. If still none, consult Automate documentation to understand the supported shape — then stop and report to the user before fabricating a block. Do not silently invent the schema.
5. Prefer templates that are structurally plain — avoid picking a voicebot `say` loaded with ASR commands if you need a text `say`.
6. Copy the full state object as the structural starting point. Change only the fields that must change: `id`, `name`, `position`, and the semantically relevant payload (`responses`, `memory`, `inputParameters`, `integrationReferenceName`, `developerMessage`, etc.).

**Verify:** the copied template still validates against `flows.schema.json` after edits, including all required arrays/objects that must exist even when empty (`commands`, `conditionalResponses`, `inputParameters`, `memory`, `metadata`, `outputs`, `redirect`, `tags`).

**Pitfalls:**

- Inheriting `commands` from a voice template into a text context by accident.
- Using a template whose memory keys are read elsewhere in the source flow — the reuse will silently couple unrelated contexts.
- Dropping "empty-looking" arrays that are actually required by the schema.
- Copying absolute `position` coordinates from a dense reference context into a sparse target — see Procedure G1.

---

## A2 · trace-transition-wiring

**When to use:** before touching any routing; whenever a state has more than one output; whenever a state is being deleted or replaced.
**Prerequisites:** you know the context `uuid` and the affected `state.id`.

**Procedure:**

1. Read the `outputs` array of the source state; list every `output.id` and `output.name`.
2. In the same context's `transitions` array, list every transition whose `from` matches one of those output ids.
3. Confirm every transition's `to` is a real `state.id` inside the **same context**.
4. Write the mapping explicitly: `source state → output.id → transition → destination state.id`.
5. Decide which transitions must be preserved, which must be deleted, and which must be added.

**Verify:**

- Every output has exactly one outgoing transition unless the output is intentionally unused.
- No transition references a `from` or `to` UUID that does not exist in the context.
- No orphan transitions left after deleting outputs.

**Pitfalls:**

- Assuming transitions connect `state.id → state.id`. They do not. They connect `output.id → state.id`.
- Duplicating an output id across different states. Output ids must be unique.
- Moving a state between contexts without re-wiring — transitions are context-local.

---

## A3 · inventory-memory-usage

**When to use:** before introducing a new memory key, or before changing the shape of an existing one.
**Prerequisites:** target export unpacked.

**Procedure:**

1. Grep `flows/*.json` for the proposed memory path (e.g. `memory.response.<endpointName>`).
2. List every state that reads the path (usually in `inputParameters`, `conditions`, `responses`, `memory`, `developerMessage`, `userMessage`).
3. List every state that writes the path (usually `custom`, `Integration.outputValues`, `llm-integration.responseMemoryPath`).
4. Decide whether to reuse, extend, or choose a new path.

**Verify:** there is exactly one writer for each "canonical" key, or the multiple writers are intentional (for example happy path + fallback reset).

**Pitfalls:**

- Reusing a generic key like `memory.result` that turns out to be written by three unrelated contexts.
- Writing to a normalized path while downstream states still read the raw API path.

---

## A4 · author-ael-expression

**When to use:** before writing or changing any AEL expression in responses, quick replies, Custom memory values, output conditions, conditional response conditions, command params, integration input params, or metadata values.
**Reference source:** local documentation under `docs/Expression language/`, especially:

- `docs/Expression language/expression-language-overview/index.md`
- `docs/Expression language/expression-language-overview/operators.md`
- `docs/Expression language/expression-language-overview/conditions.md`
- `docs/Expression language/expression-language-overview/memory.md`
- `docs/Expression language/methods-and-apis-overview/index.md`
- the relevant method page under `docs/Expression language/methods-and-apis-overview/`

**Procedure:**

1. Identify where the expression will run, because syntax differs by field:
   - Responses: wrap each AEL expression in `{...}` and leave normal text outside the braces.
   - Quick replies: use the same `{...}` interpolation style as responses.
   - Input fields such as `memory.*.value`, `condition.left.value`, `condition.right.value`, `command.params.value`, `inputParameters.*.value`, and metadata values: do **not** wrap in `{}`. The whole field is the expression.
   - Integration request templates in `integrations.json` are a separate placeholder context. For JSON bodies, follow Procedure B4a and use single or double braces according to whether the placeholder represents a complete JSON node or string content inside existing quotes.
2. Set `useJS` intentionally:
   - `useJS: false` for AEL literals, memory/NLU/system reads, method chains, arithmetic, comparisons, `if...else`, and simple array/object processing supported by AEL.
   - `useJS: true` only for JavaScript that genuinely needs assignments, loops, helper functions, dynamic object mutation, or multi-step transformation.
3. Use valid AEL data types only: string, number, boolean, array, object, DateTime, or `null`.
4. Use normal AEL access patterns:
   - memory: `memory.user.name`, `memory.response.slots[0]`, `memory.someObject["dynamic-key"]`
   - NLU: `nlu.intent`, `nlu.variablesList`, `nlu.variables.<name>`
   - system: `system.userInput`, `system.currentTime`, `system.author`, `system.projectId`, `system.sessionId`, `system.internalSessionId`, `system.source`
5. Use AEL methods before reaching for JavaScript when the transformation is still one expression:
   - strings: `"hello".toUpper()`, `system.userInput.toLower()`, `"10.5".toNumber()`
   - arrays: `memory.items.length()`, `memory.items.filter(item => item.active = true)`, `memory.items.map(item => item.name)`
   - objects: `memory.payload.property(memory.keyName)`, `memory.payload.getKeys()`
   - dates: `system.currentTime.plusDays(1).formatAsDate()`, `"2026-07-03T10:00+02:00".toDateTime()`
6. For conditions, keep the export shape separate from the expression syntax:
   - In structured exported conditions, keep `{ left, type, right, operator }` and use the schema-supported `operator` values from `flows.schema.json`.
   - Inside raw AEL expression strings, equality is `=`, not JavaScript assignment.
7. For `if...else`, always include the `else` branch because AEL expressions must return a value:
   - `if (nlu.variables.numeral != null) nlu.variables.numeral.value else 0`
8. Guard array indexing and optional properties before reading them. Prefer a prior condition such as `memory.items.length() > 0` before `memory.items[0]`, or use an `if...else` expression where appropriate.
9. Keep strings in input-field AEL inside double quotes. Do not use single quotes.
10. Avoid trailing whitespace in expression fields.
11. Do not use regular expressions in flow blocks, neither in AEL nor in JavaScript (`.test(`, `.match(`, `replace(/…/)`, `split(/…/)`, `RegExp`). Recognition belongs in the NLU module (Procedures E0-E6). In JavaScript, normalise strings with `split(x).join(y)`, `slice`, `indexOf` and character loops.
12. AEL methods verified in `docs/Expression language/methods-and-apis-overview/strings.md` and `datetime-api.md`: `replace(old,new)`, `length()`, `slice(a,b)`, `toNumber()`, `toLower()`, `contains(s)`, `formatAsDate()`. A conditional value is `if (cond) a else b` (the `else` is mandatory).

**Verify:**

- Every `useJS: false` value is valid AEL, not JavaScript accidentally stored as text.
- Every response interpolation uses `{...}` only around expressions.
- Every input-field expression omits response-style `{...}`.
- Every method call is supported by the value's data type; do not call array methods on strings, DateTime methods on strings, etc.
- Every comparison uses compatible types, especially DateTime comparisons. Convert strings with `.toDateTime()` before comparing them with `system.currentTime`.
- Every array index read is guarded by a length check or otherwise proven safe.

**Pitfalls:**

- Writing `$memory.foo`; verified local docs and exports use `memory.foo`.
- Treating `system.sessionId` as one Automate conversation. It is the external Gateway `suid` and may be reused after a bot conversation ends; use `system.internalSessionId` when addressing one conversation through the Public API.
- Loading cross-session history without an identified `system.author`. An empty author must not be matched to other anonymous sessions.
- Using JavaScript equality or assignment syntax in AEL (`===`, `const`, `let`, `return`) while `useJS` is `false`.
- Putting `{memory.foo}` in input fields where the platform expects the raw expression `memory.foo`.
- Using single-quoted strings in AEL input fields.
- Comparing incompatible types, such as `system.currentTime > "2026-07-03"` instead of `system.currentTime > "2026-07-03".toDateTime()`.
- Reading `memory.items[0]` when `memory.items` can be empty.

---

# Category B — State editing

These procedures cover the addition, modification, or removal of specific state types. All of them depend on Procedure A1 for template discovery.

> **Prerequisite note for this category.** Several procedures below assume structural components already exist in the project: integrations (B4), destination contexts (B5), LLM credentials (B6, B7), and so on. When a prerequisite is missing, the procedure body points at the bootstrap procedure needed to create it — usually Procedure B12 (`add-new-context`). If the bootstrap procedure also can't be applied in the target project, stop and report instead of improvising.

## B1 · add-say-state

**When to use:** bot must deliver a fixed or lightly conditional utterance.
**Template source:** existing `say` or `say-conditional` from the same channel (voice or text).

**Procedure:**

1. Run Procedure A1.
2. Assign a fresh UUID for `id`.
3. Replace the `responses` array content; each response must keep a unique `_id`.
4. Mirror `requestUserInput` from the template (text channels usually differ from voice here).
5. If the state is voice and you do not want ASR tuning, strip the template's `commands` array down to `[]`. If you want tuning, use Procedure B14 separately.
6. Position with Procedure G1 and wire the incoming transition with Procedure C1.

**Verify:** the state has all required empty arrays/objects per `flows.schema.json`; the `responses` render correctly in Automate preview.

**Pitfalls:**

- Forgetting `quickReplies`, `attachments`, `conditionalResponses`, `commands`, `memory`, `metadata`, `outputs`, `redirect`, `tags`, `inputParameters` when any of them are required as empty containers.
- Reusing the template's `_id` for a new response, which breaks Automate's internal reference.

---

## B2 · add-say-conditional-router

**When to use:** branching based on memory, NLU, or derived values, without needing to speak different text per branch.
**Template source:** existing `say-conditional` that already routes on similar data.

**Procedure:**

1. Run Procedure A1 on a `say-conditional` template.
2. Build the `conditionalResponses` list in the **priority order** you want evaluated; the first matching condition wins.
3. Each `conditionalResponses` entry must contain `id`, `name`, `responses`, `conditions`, `attachments`, `quickReplies` — all required by `flows.schema.json`.
4. Each `condition` object uses the strict shape: `{ left, type, right, operator }`, with `type` in `and | or` and `operator` in `== != > < >= <=`.
5. Each branch you need must also exist as an explicit `output` on the state, with conditions matching the branch. Add one default output for the else case.
6. Wire outgoing transitions per output using Procedure C1.

**Verify:**

- Every `output.id` has a transition.
- Every `conditionalResponses[].conditions` entry validates against `flows.schema.json`.
- The default branch is reachable (outputs ordered predictably).

**Pitfalls:**

- Encoding multi-clause logic inside a single string expression instead of using the structured `condition` object.
- Forgetting the else output and leaving one code path dead.

---

## B3 · add-custom-memory-write

**When to use:** you must derive, normalize, filter, rank, or compose a value and persist it.
**Template source:** a verified `custom` state using the indexed memory-entry shape.

**Memory shape:** each entry is `{ index, useJS, value }`. This is the normative shape — see `AGENTS.md` under **"Memory write rule"** for the rule, and `flows.schema.json` under `indexedExpression` for the schema. Do not invent a different shape.

**Procedure:**

1. Run Procedure A1 on a `custom` state that already writes to memory.
2. Plan the memory keys. Use stable, human-readable paths (e.g. `memory.response.<endpointName>`, `memory.user.<preferenceName>`, `memory.counter.<purpose>`).
3. For each value, use Procedure A4 to decide whether the expression should be AEL (`useJS: false`) or JavaScript (`useJS: true`).
4. For each key, add an entry to the state's `memory` object with:
   - `index` — unique per entry, contiguous from 0 within this state.
   - `useJS` — `true` only when the value genuinely needs JavaScript. For plain strings or AEL expressions, `false`.
   - `value` — the expression or literal.
5. Follow the readability rules from `AGENTS.md`:
   - Indent and break lines.
   - Use intermediate named variables.
   - Separate logical blocks with blank lines.
   - No one-line chained expressions when a clearer multi-line version exists.

**Verify:**

- Every path you wrote is actually read downstream (use Procedure A3).
- `useJS: false` entries do not accidentally contain JavaScript syntax that will be stored literally.
- `useJS: true` entries parse as valid JavaScript.

**Pitfalls:**

- Storing a JS-looking string with `useJS: false`. It will be written verbatim as text.
- Shadowing an existing memory key written elsewhere.
- Mixing raw API payloads and normalized values into the same key. Keep `memory.response.*` raw and store normalized business objects separately.
- A nested memory path's parent object must already exist at the point in the dialog where anything reads it — otherwise the dialog ends in a runtime error instead of the read quietly evaluating to `null`.
- Do not let one entry of a `custom` block read another entry of the same block. Whether later entries see earlier writes is not guaranteed; put dependent values in the next `custom` state.

**Neutral shape reference (substitute real names from the target project):**

```json
"memory": {
  "response_<endpointName>": {
    "index": 0,
    "useJS": false,
    "value": "memory.api.<endpointName>"
  },
  "<normalizedKey>": {
    "index": 1,
    "useJS": true,
    "value": "// JS block, formatted for readability\nconst raw = memory.nlu && memory.nlu.variablesList;\nconst picked = Array.isArray(raw)\n  ? raw.find(v => v && v.name === '<varName>')\n  : null;\nreturn picked ? picked.value : null;"
  }
}
```

---

## B4 · add-integration-call

**When to use:** calling an HTTP endpoint that already exists in `integrations.json`.
**Prerequisites:** `integrations.json` contains the target integration and the target request. If it does not, edit `integrations.json` first with Procedure B4a (`configure-rest-integration`) and only then wire the flow block.
**Template source:** an existing `Integration` state in the target export.

**Observability default:** enable `logRequestResponse: true` whenever creating a new `Integration` state. Seeing the resolved request and the returned response in the Conversation module or API makes it much easier to test payloads and debug failed API calls. Disable it only when logging could expose secrets, credentials, access tokens, raw PII, or other sensitive data; document that exception in the delivery.

**Procedure:**

1. Do **not** modify `integrations.json` unless the endpoint genuinely does not exist there. Prefer reusing an existing integration + request pair.
2. Run Procedure A1 on a working `Integration` state.
3. Set `integrationReferenceName` to the existing integration UUID.
4. Set `requestReferenceName` to the existing request UUID inside that integration.
5. Populate `inputParameters` with the exact parameter names the request definition expects. Parameter names come from `integrations.json`, not from the flow.
6. Map `outputValues` to memory paths where the response must land. Use `memory.response.*` for raw payloads.
7. Preserve `nluModel`, `useNER`, `requestUserInput`, `skipResponse`, `isRequestStream` as in the template, unless you have a specific reason to change them.
8. Apply the observability default above. Integration request/response logs are visible to bot designers and API consumers, not sent to the end user.
9. Add appropriate outputs for success and failure and wire them (Procedure C1). Tag failure outputs per `AGENTS.md` ("API successes and failures" tag pattern).

**Verify:**

- `integrationReferenceName` and `requestReferenceName` both resolve against `integrations.json`.
- Every input parameter name in `inputParameters` matches the request definition.
- New Integration states include `logRequestResponse: true`, or the exception is documented because logging would expose sensitive data.
- The failure branch is handled, not silently ignored.

**Pitfalls:**

- Renaming an input parameter and breaking the integration silently.
- Writing the raw API payload to the same key as a normalized business object.
- Forgetting to tag the failure branch, which breaks analytics and regression tests.
- Enabling integration request/response logging for tokens, credentials, or sensitive personal data.

---

## B4a · configure-rest-integration

**When to use:** the needed HTTP endpoint does not yet exist in `integrations.json`, or an existing integration needs a new request definition.
**Prerequisites:** a verified integration or request template exists in the target export or in the selected reference project with a similar method, body shape, streaming mode, and header/auth pattern.
**Reference source:** `docs/Integrations/integrations-module/index.md` under **JSON body** and `docs/Flows/integration-blocks/integration.md` under **Best practices**.
**Template source, in order of preference:**

1. Existing integration in the target export with the same `baseUrl` or the same auth/header pattern.
2. Existing integration in the selected reference project with the same method/body type/streaming mode.
3. `integrations.schema.json` in the repository root for structural validation after editing. Use it as a validator, not as a license to invent unsupported fields.

**Procedure:**

1. Decide whether this is:
   - a **new request** inside an existing integration
   - or a **new integration** because the base URL, top-level headers, or overall auth pattern differ materially
2. Start from a verified template. Do not hand-write a new integration from memory.
3. Preserve the observed top-level integration shape:
   - `uuid`
   - `referenceName`
   - `name`
   - `baseUrl`
   - `requests`
   - `headers`
   - `customTimeout`
   - `inputParameters`
   - `authSettings`
4. Preserve the observed request shape:
   - `uuid`
   - `referenceName`
   - `name`
   - `path`
   - `method`
   - `body`
   - `headers`
   - `queryParams`
   - `customOutputValuesMapping`
   - `inputParameters`
   - `bodyType`
   - `isStream`
   - `streamType`
   - `botResponseMapping`
   - `botResponseBuffering`
5. If creating a **new integration**:
   - generate fresh UUIDs for `integration.uuid` and `integration.referenceName`
   - set `name` and `baseUrl`
   - keep `headers` as an array of header objects in the verified shape `{ authType, name, value }`
   - keep `inputParameters` as an object; in the reference exports it is usually empty at integration level
   - keep `authSettings` as `null` unless the target or reference export proves a different supported shape
6. If creating a **new request** inside an existing integration:
   - preserve the parent integration's `uuid`, `referenceName`, `baseUrl`, and existing headers
   - generate fresh UUIDs for `request.uuid` and `request.referenceName`
   - do not rename or rewrite existing request UUIDs/reference names
7. Configure the request carefully:
   - `method` in the observed references is `GET` or `POST`
   - `bodyType` in the observed references is `Raw` or `Json`
   - `headers`, `queryParams`, and `customOutputValuesMapping` are string-to-string maps
   - `inputParameters` is an object keyed by numeric strings such as `0`, `1`, `2`, mapping to parameter names
8. Keep parameter placeholders and `inputParameters` aligned:
   - if the request body, headers, or query params contain placeholders such as `{sessionId}` or `{OPENAI_API_KEY}`, include matching names in `request.inputParameters`
   - keep the numeric keys stable and readable; prefer contiguous numbering from `0` upward for new requests
   - in a JSON-mode request body, use `{someParameter}` without surrounding quotes when the placeholder should produce a complete JSON node; string values are serialized with their own quotes, while arrays and objects retain their JSON type
   - use `{{someParameter}}` when inserting escaped string content inside a JSON string that already has double quotes
   - the same rule applies to a direct memory expression: use `{"someParameter": "{{memory.myStringValue}}"}`, not `{"someParameter": "{memory.myStringValue}"}`
   - never put a single-brace string placeholder inside JSON quotes; if `memory.myStringValue` is `example`, the incorrect template can resolve to `{"someParameter": ""example""}`, which is invalid JSON
8a. For any **sensitive value** — API keys, tokens, passwords, `Authorization` header values — use the Automate **secrets** module, not memory and not a hardcoded literal. Reference it directly in the request field as `{secrets.yourSecretName}` (allowed in headers, query params, body, path, and auth headers — **not** in `baseUrl`). Do this instead of adding an `inputParameter` fed from `memory.*`: a secret reference needs no `inputParameter` and never travels through conversation memory. Name the secret with a stable dotted group, e.g. `rejestr.apiKey` (must start with a letter; letters/digits/`_`/`-`/`.`). The secret itself is created **by the user in the UI** under Organization → Secrets on the target environment — it cannot be set via the public API and must never be placed in the export/repo. Flag this as a required manual setup step in the delivery, and suggest restricting the secret's Allowed domains to the integration host. See `docs/Integrations/integrations-module/secrets.md`.
9. Keep streaming fields internally consistent:
   - non-streaming requests: `isStream: false`, `streamType: null`, `botResponseMapping: null`, `botResponseBuffering: null`
   - streaming requests: copy the exact verified combination from a valid template; in the references this is `isStream: true` with `streamType: "ServerSentEvents"`, `botResponseMapping: "text"`, and `botResponseBuffering: "Word"`
10. Keep top-level headers and request-level headers conceptually separate:
   - integration-level `headers` is an array of `{ authType, name, value }`
   - request-level `headers` is a plain key/value object
11. After editing `integrations.json`, wire the flow block separately using Procedure B4.

**Verify:**

- `integrations.json` validates against `integrations.schema.json`.
- Every integration and request UUID/referenceName is unique within the file.
- Every `Integration` flow state that should call the new request points to the correct `integrationReferenceName` and `requestReferenceName`.
- Request placeholders, `inputParameters`, and flow-level `inputParameters` all use matching parameter names.
- Every JSON-mode request body still parses as valid JSON after substituting representative runtime values, especially string values used inside quoted fields.
- Streaming fields are consistent with the chosen template.
- Raw response payloads still land under `memory.response.*` after the flow wiring step.

**Pitfalls:**

- Mixing the two header shapes: integration-level header array vs request-level header map.
- Renaming an existing request UUID or `referenceName` and breaking all linked flow states.
- Using non-numeric keys in `request.inputParameters`.
- Using `"{someParameter}"` or `"{memory.myStringValue}"` for a string inside a JSON body, which can add a second pair of quotes and produce invalid JSON; use the double-brace form inside existing quotes.
- Setting `isStream: true` but leaving `streamType`, `botResponseMapping`, or `botResponseBuffering` in a non-template state.
- Inventing a new `authSettings` object shape when the verified exports only show `null`.
- Passing an API key/token through an `inputParameter` fed from `memory.*` (or hardcoding it) instead of referencing the secrets module with `{secrets.name}` (step 8a).

---

## B4b · api-context-with-mock-mode

**When to use:** an external API is integrated before its sandbox exists, or the integration contract must be testable without HTTP.

**Procedure:**

1. One context per operation (group "API"): `start` → prepare (`apiAttempt = 0`, `apiOk = false`, `apiErrorCode = ""`, `idempotencyKey` for state-changing calls) → routing `empty` "mock mode?" on `memory.mockMode == true`.
2. Mock branch: one `custom` computes the sandbox answer into `memory.mockResult` (`{ok, body}`), the next `custom` sets exactly what the Integration block sets: `memory.success` and `memory.response` (plus any simulated state, e.g. card status). Real branch: token context, then the `Integration` block.
3. Both branches go to the same evaluation: `apiOk = memory.success == true`, `apiErrorCode = memory.response.errorCode` or a timeout code, then a retry decision (once, only for 429/503/504/timeout/401, same idempotency key), then a routing `empty` with outputs success / retry / handled error / other error.
4. Success: copy the needed response fields to your own memory keys right away (`memory.response` is overwritten by the next call) and `end`. Other error: call the technical-error context. Errors the dialog wants to branch on (for example "already closed") leave through their own output with `apiOk = false`.
5. The mock validates its input like the API (400 for a malformed date) and returns deterministic errors for the special sandbox cases.

**Verify:** the logic after the block reads only `memory.success` / `memory.response`; switching `mockMode` does not change any downstream block.

**Pitfalls:** A reporting call must not call the technical-error context (it would report again); mark it non-fatal.

---

## B5 · add-context-call

**When to use:** routing into another context (e.g. global fallback, auth, API orchestration) and returning afterward.
**Prerequisites:** the destination context exists in `flow.contexts`. If it does not, create it first with Procedure B12 (`add-new-context`).
**Template source:** an existing `context` state in the target export.

**Procedure:**

1. Run Procedure A1 on a `context` state.
2. Set `contextReferenceName` to the `referenceName` of the destination context. Verify that context exists inside the same flow file.
3. Pass data via `inputParameters` if the destination context expects them.
4. Make sure the destination context has at least one `end` state so control returns to the caller.
5. Wire outputs. Context blocks typically have a single output representing "returned from context".

**Verify:**

- Destination context exists and its `end` states are reachable.
- Caller output is wired to a follow-up state that handles the return.

**Pitfalls:**

- Calling a context that terminates instead of ending — control never returns.
- Passing parameters under names the destination does not read.

---

## B6 · add-llm-integration-classifier

**When to use:** the model must produce a **machine-readable** result for routing or later logic.
**Prerequisites:** LLM credentials are configured on the target environment; `credentialsId` in the template resolves. If no LLM credentials are available on the target, this procedure cannot be applied.
**Template source:** an existing `llm-integration` state.

**Procedure:**

1. Run Procedure A1 on an `llm-integration` state.
2. Preserve `credentialsId`, `model`, `temperature` from the template unless the target environment differs. **If the template's `credentialsId` does not resolve on the target — a new project, a cross-environment migration, an API import, or a `null` credential — do not guess and do not leave it `null`.** List the organization's credentials with `scripts/automate ai-credentials` (see the "AI credentials" section of the `automate-api` skill), pick one whose `CAPABILITIES` include `ChatCompletions` and whose provider matches `model`, and set `credentialsId` to that ID. Use only IDs returned by the API or clearly supplied by the user; never infer an ID from the credential name. A `say-llm`/`llm-integration` block whose `credentialsId` does not resolve makes the flow publish as `Invalid` (see H2/B9). When a `model` must actually be chosen (not just preserved from a template), prioritize response speed over capability — this block runs inside a live conversation, not a batch job. Do not default to GPT-5; a "mini"-tier model (e.g. GPT-5.4 mini, GPT-4.1 mini, GPT-4o mini) is the right default instead.
3. Write `developerMessage` as a narrow, constrained instruction. Describe the required output fields and their types in prose (e.g. "return `amount` as a number or null, `currency` as an uppercase three-letter ISO code or null") rather than pasting a literal JSON object/schema into the prompt text. The model still returns JSON for `responseMemoryPath` to parse — only the prompt itself should stay JSON-free.
4. Write `userMessage` using memory expressions to inject the actual runtime content.
5. Set `responseMemoryPath` to a dedicated normalized key, not a raw key.
6. For new `llm-integration` states, enable designer-visible logging with `logParametersAndResponse: true` unless the prompt inputs or model response contain secrets, credentials, raw PII, or another value that must not be exposed in Conversation module/API logs.
7. Downstream, route on the normalized key using Procedure B2 (`say-conditional`). Do not let the LLM drive business decisions directly — deterministic logic must decide action.

**Verify:**

- Prompt is bounded and does not ask the model to make business decisions outside its narrow task.
- New `llm-integration` states include `logParametersAndResponse: true`, or the exception is documented because logging would expose sensitive data.
- Downstream routing tolerates unexpected model output (always have a default branch).

**Pitfalls:**

- Over-broad prompts that let the LLM decide whether to book, escalate, or fall back.
- Writing LLM output into a key already used by another writer.
- Omitting a default branch for malformed model output.
- Logging prompt inputs or generated structured results that contain sensitive data.
- Defaulting to GPT-5 for a live conversational block. It responds too slowly for a bot holding a real-time conversation; prefer a "mini"-tier model instead.
- Pasting a full JSON object or schema into `developerMessage`/`userMessage`. Describe the desired fields and types in prose, or interpolate only the specific memory values actually needed.

---

## B7 · add-say-llm-generator

**When to use:** the bot must produce a single naturally-worded utterance and optionally call tools mid-turn.
**Prerequisites:** LLM credentials are configured on the target environment.
**Template source:** an existing `say-llm` state.

**Procedure:**

1. Run Procedure A1 on a `say-llm` state.
2. Preserve `credentialsId`, `model`, `isStream`, `botResponseBuffering`, `delayedMessageConfig`, `previousMessagesContextSize`. **If the template's `credentialsId` does not resolve on the target — a new project, a cross-environment migration, an API import, or a `null` credential — do not guess and do not leave it `null`.** List the organization's credentials with `scripts/automate ai-credentials` (see the "AI credentials" section of the `automate-api` skill), pick one whose `CAPABILITIES` include `ChatCompletions` and whose provider matches `model`, and set `credentialsId` to that ID. Use only IDs returned by the API or clearly supplied by the user; never infer an ID from the credential name. A `say-llm` block whose `credentialsId` does not resolve makes the flow publish as `Invalid` (see H2/B9). When a `model` must actually be chosen (not just preserved from a template), prioritize response speed over capability — this block runs inside a live conversation, not a batch job. Do not default to GPT-5; a "mini"-tier model (e.g. GPT-5.4 mini, GPT-4.1 mini, GPT-4o mini) is the right default instead, **except for a `say-llm` block with tool calling: use a non-mini model such as `gpt-4.1`** (AGENTS.md, LLM Blocks). Always set `botResponseBuffering` to `"Sentence"` (full sentences), not `"Word"` (AGENTS.md).
3. Write `context` as a tight instruction for one specific generation job — a single bounded utterance, not "generate whatever is appropriate". Describe any data the model needs in prose or by interpolating only the specific memory values required — never paste a full JSON object into `context`. Prefer a context pattern that clearly separates:
   - the current user need or query
   - character or tone instructions
   - retrieved context or supporting facts
   - output constraints such as maximum response size
4. Preserve and configure conversational context deliberately:
   - `previousMessagesContextSize` controls how much prior conversation is included
   - `maxTokens` is a truncation limit for the model output, not a business-level output-length guarantee
5. Configure streaming deliberately and reuse verified values from a working template:
   - more granular streaming improves perceived responsiveness in chat
   - coarser buffering is often safer for voice channels
   - do not invent buffering values; copy them from a verified template even when you understand the intended behavior
6. Define `tools` only if the model is allowed to act mid-turn. Populate `toolCallsMemoryPath` and `toolResultsMemoryPath` to the expected paths.
7. When using tool calling, keep the workflow explicit:
   - the `say-llm` block generates tool calls and stores them in the configured memory path
   - downstream workflow executes those tools, usually via `Integration` or `custom` blocks
   - the workflow must write tool results back in the same conversational turn to the configured tool-results memory path
   - the conversation then returns to the same `say-llm` block so it can formulate the final user-facing answer
8. Build tool results in the required shape:
   - an array of objects
   - each object contains `id` and `result`
   - `id` must exactly match the generated tool call id
   - `result` contains the returned payload that the LLM should use
9. For new `say-llm` states, enable designer-visible logging with `logParameters: true` unless the prompt context contains secrets, credentials, raw PII, or another value that must not be exposed in Conversation module/API logs. The generated answer is already user-facing; the logging option is for inspecting the LLM inputs and tool parameters in Conversation module/API logs.
10. Keep the job narrow. If the job is "decide and speak", split it: use `llm-integration` to decide (B6), then `say-llm` (or plain `say`) to speak.

**Verify:**

- The generation job is bounded.
- `previousMessagesContextSize`, `maxTokens`, and streaming settings are copied from a verified template or changed intentionally with clear channel-specific reasoning.
- If no tools are needed, `tools` is `[]` but still present, as the schema requires it.
- If tools are used, `toolCallsMemoryPath` and `toolResultsMemoryPath` are both configured and the workflow actually writes results back in the expected format.
- New `say-llm` states include `logParameters: true`, or the exception is documented because logging would expose sensitive data.
- Tool result objects preserve the original tool-call ids exactly.

**Pitfalls:**

- Letting `say-llm` both decide control flow **and** speak, which makes the bot non-deterministic.
- Treating `maxTokens` as if it were a guaranteed final answer length instruction instead of a hard cut-off.
- Returning tool results in the wrong shape or under the wrong memory path, so the LLM cannot complete the loop.
- Executing tools in a later turn instead of returning results in the same turn.
- Setting `delayedMessageConfig` to a structure the template did not use; reuse verbatim.
- Logging LLM prompt context or tool parameters that contain sensitive data.
- Defaulting to GPT-5 for a live conversational block. It responds too slowly for a bot holding a real-time conversation; prefer a "mini"-tier model instead.
- Pasting a full JSON object into `context` instead of describing the needed data in prose or interpolating only the specific values required.

---

## B7a · add-dynamic-quick-replies

**When to use:** the bot should show quick reply buttons whose labels depend on the previous bot response, search results, API results, or another runtime value.
**Template source:** verified in `/Users/admin/Downloads/[Projects] RAG FAQ_export_14-07-2026T11-07.zip`, context `LLM Answering based on knowledge [query, context, character]`, state `Niestandardowy`.

**Verified shape:**

- The state keeps the normal `quickReplies` array present, usually as `[]`.
- The state adds top-level `dynamicQuickReplies` as a standard expression object: `{ "useJS": true|false, "value": "..." }`.
- The expression returns an array of strings. Each string becomes a quick reply label.
- The state can be a silent `custom` state with an empty response, `requestUserInput: true`, and no memory writes. This lets the previous visible answer remain the conversational context while the dynamic buttons are offered.

**Observed robust pattern:**

1. Generate the user-facing answer first, often with `say-llm`.
2. Use a narrow `llm-integration` block to extract button labels from that generated answer into a dedicated memory path, for example `memory.response`.
3. Add a silent `custom` state immediately after the extractor:
   - `responses`: one empty localized response
   - `quickReplies`: `[]`
   - `requestUserInput`: `true`
   - `dynamicQuickReplies`: expression that parses and validates the memory value
4. Route the silent state to the next classifier/router. When the user clicks a dynamic reply, Automate places the clicked label in `system.userInput`.
5. Downstream, handle the clicked label through deterministic routing, or through a narrow `say-llm` tool/classifier that is explicitly instructed to react only to valid options.

**Example expression from the verified export:**

```json
"dynamicQuickReplies": {
  "useJS": true,
  "value": "(function () {\n  var raw = memory.response;\n  var titles = [];\n\n  try {\n    titles = typeof raw === \"string\" ? JSON.parse(raw) : raw;\n  } catch (e) {\n    return [];\n  }\n\n  if (!Array.isArray(titles)) return [];\n\n  return titles;\n})()"
}
```

**Verify:**

- The expression returns an array even when the source memory is missing, malformed, or empty.
- The array items are short user-facing labels, not objects, JSON strings, or long paragraphs.
- The downstream path can handle both button clicks and free text.
- If labels are extracted by LLM, the extractor is constrained to return strict JSON and a safe empty array on no match.
- The state still validates against `flows.schema.json`.

**Pitfalls:**

- Returning objects such as `{ pl: "..." }` instead of strings; the verified export uses plain strings.
- Letting an unconstrained LLM generate arbitrary button labels that downstream logic cannot handle.
- Forgetting `requestUserInput: true`; the buttons may render but the flow will not wait where intended.
- Putting important business actions directly behind dynamic labels without a deterministic confirmation or validation step.

---

## B8 · add-conversationMetadata-debug

**When to use:** pushing important runtime values into conversation metadata for observability and regression tests.
**Template source:** an existing `conversationMetadata` state.

**Procedure:**

1. Run Procedure A1 on a `conversationMetadata` state.
2. Add fields mapping metadata keys to memory expressions (API request, API response, derived selection, retry counters).
3. Place it right after the step that produces the value, not at the end of the flow (easier debugging).

**Verify:** metadata shows up in the conversation inspector; test suites can assert on it.

**Pitfalls:**

- Leaking sensitive values (tokens, raw PII) into metadata.
- Creating "write-only" metadata that no one reads or asserts against.

---

## B8a · add-log-block

**When to use:** adding designer-visible diagnostic information to the conversation timeline without sending anything to the end user.
**Template source:** an existing `log` state from the target export or a verified reference export. The export `input/[Projects] Log examples_export_08-07-2026T15-50.zip` shows the verified shape.

**Procedure:**

1. Run Procedure A1 on a `log` state.
2. Write `message` as an expression object `{ useJS, value }`. Use it for a short human-readable summary, for example the phase being entered or a key non-sensitive value.
3. Add structured `objects` only when raw or complex data will help designers debug the flow. Each object uses:
   - `key` — the label shown for the logged object
   - `params` — an expression object `{ useJS, value }` that resolves to the value to log
4. Keep the block non-user-facing. It should not contain `responses`, `attachments`, or `quickReplies` unless copied from a future verified template that proves otherwise.
5. Wire the log block like any other state with a normal output transition. It should sit close to the state that produces the value being logged.
6. Do not log secrets, credentials, access tokens, raw authentication payloads, or sensitive personal data.

**Verify:**

- The state type is `log`.
- `message` is present and uses the standard expression shape.
- `objects` is present; use `[]` when there are no structured objects.
- Every object has `{ key, params }`, and `params` uses the standard expression shape.
- The log block is connected and does not interrupt user-facing output.

**Pitfalls:**

- Treating Log as a bot response. It is visible to bot designers in Conversation module and through API logs, not to the chatting end user.
- Logging sensitive data because it is "internal"; Conversation module/API logs are still observable surfaces.
- Placing logs far from the related Integration/LLM/custom state, which makes debugging harder.

---

## B9 · add-empty-quickpoint

**When to use:** structural helpers to make the canvas readable and to centralize branching.
**Template source:** an existing `empty` state of the same kind: a pure quick point (one output, no conditions) or a routing block (several outputs with conditions plus an else output).

**Procedure:**

1. Run Procedure A1 on an `empty` state of the right kind.
2. Use it only for **structure and readability**, never for business logic.
3. Copy the full field set of the template — in particular it **must** include `requestUserInput` (normally `false`).
4. Decide the kind and set the flags accordingly:
   - **pure quick point** — exactly one output without conditions: keep `isEmptyPoint: true` and `useNER: false`. The canvas draws it as a diamond.
   - **routing block** — several outputs and/or conditions (one output per branch plus an else output with empty `conditions`): do **not** set `isEmptyPoint`, `isQuickPoint` or `useNER`. Finance Bot's and Medical Bot's routing `empty` blocks have none of them.
5. Wire outputs; a pure quick-point has exactly one output, a routing block has one per branch.

**Pitfalls:** Empty blocks that quietly accrete logic over time turn into mystery nodes. Keep them empty. **Omitting `requestUserInput` on an `empty` state makes the whole flow fail publication with `status: "Invalid"` and no error message** — the public API gives no reason, so this is easy to misdiagnose (it is not caused by an untrained NLU; `OutSync` NLU does not block publishing). **Setting `isEmptyPoint: true` (or `isQuickPoint: true`, found the same way in a generated bot: a routing block copied from a one-output quick point) on a routing block makes the canvas draw a diamond without outputs and no connector is visible anywhere in that context, although the flow still runs** (every output shows "+"). It was found by bisecting throwaway projects; ids, positions, JSON formatting and extra state keys were ruled out.

---

## B10 · add-nluModel-state

**When to use:** routing the next step based on NLU recognition of the user's last utterance. This is the primary entry to intent-driven branching.
**Prerequisites:** the target project has a valid NLU (referenced by `project.json.defaultNluId` or by a per-state `nluModel` value). The NLU folder (`nlu/<NLU>/`) exists with `data.json`, `intents.csv`, `phrases.csv`.
**Template source:** an existing `nluModel` state in the target or reference export.

**Procedure:**

1. Run Procedure A1 on an `nluModel` state.
2. Assign a fresh UUID for `id`.
3. Set `nluModel` to the reference of the NLU to use — typically matches `project.json.defaultNluId`, or a dedicated model if the context uses a specialized NLU.
4. Mirror `useNER` from the template. Set `true` when entity extraction (`nlu.variablesList`) is read downstream; `false` when only intents matter.
5. Mirror `requestUserInput` from the template. Usually `true` — the state waits for user input, then classifies it.
6. Route the single output to a downstream router (usually a `custom` or `say-conditional`) that reads `nlu.intent` / `nlu.variablesList` and branches.
7. Wire incoming transition with Procedure C1.

**Verify:**

- `nluModel` resolves to an existing NLU in the project.
- Downstream routing reads intent names that actually exist in `nlu/<NLU>/intents.csv`.
- `useNER` matches downstream needs.

**Pitfalls:**

- Setting `nluModel` to a non-existent reference — the state will fail silently at runtime.
- Assuming the NLU will recognize a specific intent that was never trained — always cross-check against `intents.csv` and `phrases.csv`.
- Using `useNER: false` and then reading `memory.nlu.variablesList` downstream — the list will be empty.

---

## B11 · add-start-or-end-state

**When to use:** creating a new context (requires one `start`), or when a context must return to the caller (`end`), or when the conversation must finish entirely (`terminate`).
**Template source:** any `start` / `end` / `terminate` state in the target or reference export.

**Procedure:**

1. Run Procedure A1 on the appropriate template.
2. Assign a fresh UUID for `id`.
3. Semantics:
   - `start` — entry point into a subgraph. A context may contain more than one `start` block, but each one must lead into its own separate, non-overlapping tree of states — never route two `start` blocks into the same downstream subgraph. Each individual `start` still has exactly one outgoing transition and no incoming transition.
   - `end` — exits **this context**; control returns to the caller. Use when a context is called via a `context` state.
   - `terminate` — ends the **entire conversation**. Use only for final termination (handover, goodbye, full error).
4. Wire incoming transitions (for `end` / `terminate`) with Procedure C1. For `start`, only wire the outgoing transition.

**Verify:**

- Every `start` block in a context leads into a fully separate subgraph from every other `start` in that context — no shared downstream states between them.
- No `start` has incoming transitions.
- No `end` / `terminate` has outgoing transitions.
- `terminate` is used only when the conversation should not continue.

**Pitfalls:**

- Using `terminate` where the caller expects control to return — the conversation dies silently.
- Two `start` blocks in the same context feeding into the same downstream tree — keep each `start`'s subgraph fully separate.
- Leaving a context without an `end` when it's called from elsewhere — control never returns.

---

## B12 · add-new-context

**When to use:** the target flow needs a context that does not yet exist (Global Listener, Global Fallback, Error Handling, a new business process, an auth context, etc.). This is the bootstrap procedure several other procedures depend on.
**Prerequisites:** the reference export contains a context playing the role you need, **or** the target has an analogous context that can serve as a template.
**Template source:** a verified context from the selected reference project from reference matching the intended role.

**Procedure:**

1. Identify a reference context whose role matches the new one (e.g. `Global Fallback`, `Global Listener`, `Error Handling`, a business-process context).
2. Copy the entire context object.
3. Generate a fresh UUID for `context.uuid` **and** a fresh UUID for `context.referenceName`. Both are required by `flows.schema.json`. They may be different values.
4. Preserve the `context.model` container shape of the verified template. For contexts that carry real flows use `{name, uuid, notes, states, transitions}` with `model.uuid` equal to the context `uuid` and `model.name` equal to the context name (Finance, Insurance, Administration, Agentic Search and Log examples all have it; some also keep `x`/`y`). The `{x, y, states, transitions}` shape of `reference/empty polish project.zip` is a starter skeleton: do not copy it onto generated contexts.
5. Rename `context.name` to fit the target's naming convention. If the copied template also contains a model-level display name field, update it too; otherwise do not add one.
6. Set `context.group` to match the target's grouping convention, or `null` if the target does not use groups.
7. Walk every state inside `context.model.states`:
   - Generate a fresh UUID for each `state.id`.
   - Generate a fresh UUID for each `output.id`.
   - Rename memory keys that reference the source project's domain to target-appropriate keys.
   - Strip or adjust `commands` that do not fit the target channel.
8. Walk every transition in `context.model.transitions`:
   - Update `from` to the new `output.id` generated in step 7.
   - Update `to` to the new `state.id` generated in step 7.
9. Append the new context to `flow.contexts`.
10. Wire it in:
    - If it is a Global Listener / Global Fallback / Error Handling context, connect it via the appropriate flow-level mechanism (for Error Handling see Procedure B13; for Global Listener/Fallback see Procedure D1/D2).
    - If it is a business-process context, add a `context` state in the caller (Procedure B5) pointing at the new `referenceName`.

**Verify:**

- No UUID collision with any existing context, state, output, or transition anywhere in the flow.
- All internal transitions route `output.id → state.id` within the new context only.
- `flow.contexts` contains the new entry; `flows.schema.json` still validates.
- `context.model` still matches the shape of the target/reference export you copied from; no invented nested fields were added.
- Memory keys used inside do not unintentionally overlap with memory keys used elsewhere in the flow (run Procedure A3).

**Pitfalls:**

- Regenerating some UUIDs but not others — silent collisions with the source context's UUIDs.
- Copying the `x`/`y`-only `model` of the empty starter onto real flows. Do not invent other model-level fields, but `name`, `uuid` and `notes` are the verified ones.
- Inheriting memory keys that the original context used but the target project does not populate.
- Inheriting a `group` value from the reference that does not exist in the target export's grouping convention.
- Copying voice-channel commands into a text-only target.

---

## B13 · set-errorHandlingContextRef

**When to use:** the flow needs a dedicated Error Handling context and the flow-level `errorHandlingContextRef` is `null` or points to a context that no longer exists. This is a **flow-level** edit, not a state-level edit.
**Prerequisites:** the Error Handling context already exists in `flow.contexts`. If it does not, create it first with Procedure B12, using a verified Error Handling context as the template.

**Procedure:**

1. Confirm the Error Handling context exists in `flow.contexts`; note its `referenceName`.
2. Set `flow.errorHandlingContextRef` to that `referenceName` value (a UUID string).

**Verify:**

- The referenced `referenceName` resolves to a context in `flow.contexts`.
- The value is a valid UUID per `flows.schema.json`.
- Importing the flow does not produce a "missing error handler" warning.

**Pitfalls:**

- Using the context's `uuid` instead of its `referenceName`. Both are UUIDs, but Automate resolves `errorHandlingContextRef` against `referenceName`.
- Setting the reference without any actual error-handling logic inside the context — silent failures still go untreated.

---

## B14 · add-commands-to-state

**When to use:** attaching channel-specific behavior to an existing state — ASR tuning, DTMF digit count, recognition model, handover redirect. Typically voice-channel only.
**Prerequisites:** a verified template state of the **same state type and same channel** that already has the required command configured.
**Template source:** existing state with commands in the target or reference export.

**Procedure:**

1. Identify the target state and decide which commands it needs: ASR timeout, DTMF expected digit count, recognition model override, redirect command, etc.
2. Copy the `commands` array entries from a verified template.
3. Preserve the strict shape required by `flows.schema.json`: each command is `{ type, params }` where `params` is an `expression` `{ useJS, value }`.
4. Adjust `params.value` to the target value (e.g. a timeout in seconds as a string or number literal, the DTMF digit count, the redirect target).
5. Do not use commands for business logic — they are channel behavior only.
6. Test the command behavior in a voice test case if voice behavior changes are critical (Procedure F1).

**Verify:**

- Each command has a non-empty `type` string and a valid `params` expression.
- Commands fit the state's channel — voice commands on a text state have no effect and confuse future readers.
- `useJS` on `params` matches the value: `false` for literals, `true` only when the value is computed.

**Pitfalls:**

- Encoding business decisions in commands — they become unreviewable shortcuts.
- Attaching voice commands to text-channel states.
- Setting ASR timeouts too short on states that ask users for complex input.
- Using `useJS: true` on a value that is actually just a literal string.

---

## B15 · remove-state-safely

**When to use:** removing a state that is no longer needed, or as part of replacing a state with a different type (see the note at the end).
**Prerequisites:** Procedure A2 (trace-transition-wiring) completed so you know what connects to the state.

**Procedure:**

1. Identify every transition whose `to` points at the state's `id` — these are the incoming transitions.
2. Identify every transition whose `from` matches one of the state's output IDs — these are the outgoing transitions.
3. Decide upstream rerouting. Common choices:
   - **Bypass:** re-point incoming transitions to whatever was downstream of the removed state.
   - **Replacement:** re-point incoming transitions to a new replacement state.
   - **Full cut:** remove the subgraph entirely, including downstream states that become unreachable.
4. Re-point or delete transitions accordingly. Do not leave any transition referencing a deleted output ID or state ID.
5. Remove the state from `context.model.states`.
6. If the state wrote to memory, use Procedure A3 to check whether downstream states still read those keys. If they do, either provide the write elsewhere or accept that downstream reads become undefined.
7. Update test suites (Procedure F1) if they asserted on the removed state's responses, outputs, or tags.

**Verify:**

- No transition references the removed state's `id` or any of its output IDs.
- The flow has a valid path from each context's `start` to a terminal state (`end` or `terminate`).
- Flow validates against `flows.schema.json`.
- No downstream state reads a memory key that is now unwritten (or the lack of write is intentional).

**Pitfalls:**

- Leaving orphan transitions with dangling UUIDs — import breaks.
- Removing a state without considering its memory writes — downstream silent failures.
- Breaking tests that asserted on the removed state without updating them in the same change set.

**Replacing a state with a different type.** This is not a separate procedure; it is a composed operation: *Procedure B15 (remove-state-safely) + the appropriate B1–B14 procedure to add the replacement + Procedure C1 to rewire*. Do all three in one change set, not across separate commits. When the new state has a different output structure than the old one (e.g. `say-conditional` → `custom`), re-plan the wiring explicitly — a 1-to-1 output mapping usually does not exist.

---

# Category C — Wiring

## C1 · wire-transition

**When to use:** any time a new output or state is added, or routing is changed.

**Procedure:**

1. For each outgoing output on the source state, add a transition with:
   - `from` = the `output.id`
   - `to` = the destination `state.id` in the same context
   - `name` = human-readable label (usually mirrors the output name)
2. Delete any transition whose `from` references an output that no longer exists.
3. Re-run Procedure A2 to confirm the wiring matches intent.

**Verify:** every output is covered by exactly one transition unless explicitly unused; no transition dangles.

**Pitfalls:** see Procedure A2 pitfalls.

---

## C2 · call-and-return-with-end

**When to use:** implementing a reusable subroutine context (auth, token fetch, API orchestration, FAQ).

**Procedure:**

1. The caller uses a `context` state (Procedure B5).
2. The destination context ends each return path with an `end` state, not `terminate`.
3. `terminate` is reserved for conversation-level termination (e.g. handover completed, conversation closed).

**Verify:** calling the context from different places works and returns correctly.

---

# Category D — Global behavior

> **Prerequisite note for this category.** All procedures here assume the Global Listener and/or Global Fallback contexts already exist in the target flow. When a project lacks them, create the context first with Procedure B12 (`add-new-context`), reusing a verified Global Listener / Global Fallback context from the reference export. Then apply the D-category procedure to extend it.

## D0 · attach-global-listener-tree

**When to use:** the Global Listener context must be active in a context where the user can speak.
**Prerequisites:** the Global Listener context exists (B12). Its `start` block carries one output per intent, with `nlu.intent` / `nlu.variables` conditions, and an else output that ends the context.
**Template source:** the Automate canvas of a working bot (a context with two `start` blocks: the normal one, and a second one leading to a `context` block "Global Listener" placed at the very top).

**Procedure:**

1. In every context that waits for the user (and in the contexts that call such contexts, if the listener should also be active there), add a second `start` block named e.g. "Start (Global Listener)".
2. Add a `context` block whose `contextReferenceName` is the Global Listener context and connect the second `start` to it. Put both at the top of the context, above the main path.
3. Leave the output of that `context` block **unconnected**. The platform returns to the interrupted block; the canvas shows `+` on the output. This is the only intended unconnected output.
4. Make the interrupted block repeat its prompt on re-entry: the block that waits for the user should also speak (a `say` with `requestUserInput`), so the question is asked again after the listener returns. Loops for silence, misunderstanding and warnings should only change a prompt value in memory and return to that block.
5. Do not attach the block to contexts that never wait for the user (API, token, step-up without speech, helper contexts).

**Verify:**

- Each `start` of the context leads to its own subgraph (B11).
- The listener block is fed only by its own `start`.
- Global intents are guarded by `nlu.intentScore` (for example `>= 0.6`), and none of their training phrases starts with a word that an answer entity reacts to (see E6).
- `scripts/validate_export.py` reports exactly these unconnected outputs and no others.

**Pitfalls:**

- A floating `context` block without its own `start` (the older Finance Bot layout) is not the pattern used on the current canvas.
- Assuming the interrupted block is simply re-asked after the listener. On the platform its outputs are evaluated again on the current utterance (an answered "kto dzwoni" became "unclear", a "nie" to the listener's own question could become the block's "nie"). Guard with the handled utterance, not a boolean (when the listener itself waited for an answer the platform re-asks the interrupted block instead, and a boolean stays set): the listener stores `memory.listenerInput = nlu.user_input` (also on its own "no" path); each waiting block gets `memory.listenerInput != null && memory.listenerInput == nlu.user_input` as its first output, routed to the fallback context, which clears it and ends without counting; the caller loops back to the same question. Verified by running a test suite on the platform; simulate both return semantics.
- A test runner cannot hang up: do not assert a hang-up outcome tag (ending-context tag) in a test case.
- Wiring the listener's output back to a state "to continue" duplicates behaviour that the platform already provides, and can re-run side effects (an API call) after an interruption.

---

## D1 · extend-global-listener

**When to use:** adding a new cross-cutting intent trigger (agent request, goodbye, repeat, silence, waiting, emergency, out-of-turn preference).

**Procedure:**

1. Work inside the dedicated Global Listener context. Do not embed global logic in business contexts.
2. Add or extend intent matching using existing patterns.
3. Route recognized intent to the appropriate global handler context.
4. Keep the listener itself stateless; counters belong in D2.

**Pitfalls:** Turning the listener into a business context. It must remain a thin dispatcher.

---

## D2 · extend-global-fallback-with-counter

**When to use:** adding a new fallback scenario or tuning retry/clarify/escalate logic.

**Procedure:**

1. Work inside the Global Fallback context.
2. Use counter memory keys (`memory.counter.<purpose>`, e.g. `memory.counter.fallback`, `memory.counter.silence`, `memory.counter.agentRequest`).
3. On each fallback, increment the relevant counter (Procedure B3).
4. Route with `say-conditional` (Procedure B2) based on counter thresholds: retry → clarify → escalate.
5. Tag each outcome per `AGENTS.md` (business milestone, escalation, fallback/error).

**Pitfalls:** Not resetting counters after a successful turn, so the user hits escalation after unrelated errors.

---

# Category E — NLU

## E0 · phrases-csv-row-shape

**When to use:** before adding or editing any row in `nlu/<NLU>/phrases.csv`.

**Procedure:**

1. Treat `phrases.csv` as a **headerless UTF-8 CSV** with exactly **5 columns per row** in this order:
   - `utterance`
   - `intent`
   - `tokens_json`
   - `entities_json`
   - `flag`
2. Keep the row shape aligned with verified exports from this repository. In practice:
   - `utterance` is the full training phrase text
   - `intent` is the target intent name from `intents.csv`
   - `tokens_json` is a JSON array of token objects
   - `entities_json` is a JSON array of entity span objects, or `[]` when no entity spans are labeled
   - `flag` is preserved in the verified export shape and should not be invented ad hoc
3. If `utterance` is not empty, `tokens_json` must **not** be `[]`.
4. Calculate `tokens_json` using **simple whitespace-based tokenization**:
   - split the utterance on whitespace
   - each token keeps the exact text substring found in the utterance
   - compute `startIndex` and `endIndex` against the original utterance text
   - punctuation attached to a token stays attached unless whitespace separates it
5. Build each token object in this shape:
   - `{ "value": "<token>", "indices": { "startIndex": <int>, "endIndex": <int> } }`
6. Only use `entities_json` spans when the phrase actually labels entities. If the phrase has no labeled entities, keep `entities_json` as `[]`.
7. Keep CSV quoting intact. `tokens_json` and `entities_json` are JSON serialized into CSV cells, so incorrect quoting will break import.

**Verify:**

- Every row has exactly 5 columns.
- Non-empty utterances have non-empty `tokens_json`.
- Every token's `value`, `startIndex`, and `endIndex` match the literal utterance text.
- Every `intent` in `phrases.csv` exists in `intents.csv`.
- Every labeled `variableName` in `entities_json` exists in `entities.csv`.

**Pitfalls:**

- Appending a phrase with `tokens_json` set to `[]`.
- Using character offsets that do not match the original utterance exactly.
- Re-tokenizing punctuation differently from the whitespace-based split used for the row.
- Breaking CSV quoting while editing JSON inside CSV cells.

## E1 · add-intent

**When to use:** a new business-level user intention appears.

**Procedure:**

1. Add one row to `nlu/<NLU>/intents.csv`. Keep intent names stable and human-readable.
2. Add training phrases to `nlu/<NLU>/phrases.csv`, mapping them to the new intent. Use a realistic mix of phrasings, not just one template.
3. Follow Procedure E0 for every new `phrases.csv` row.
4. If a phrase contains labeled entities, keep entity spans and token spans consistent with the utterance text and the entity definitions.
5. Plan a retrain step after import — Automate requires manual training after NLU import.

**Pitfalls:** Invented intent names that break flow conditions or analytics dashboards.

---

## E2 · add-or-extend-entity

**When to use:** new vocabulary, dictionary values, or entity synonyms.

**Procedure:**

1. Prefer extending an existing entity in `entities.csv` over creating a new one.
2. Only create a new entity when the semantics are genuinely different.
3. Keep entity type consistent (keyword, built-in).
4. If the task can be solved **without** editing `entities.csv`, prefer that (per `AGENTS.md`).

**Pitfalls:** Breaking flow expressions that reference the existing entity name.

---

## E3 · add-training-phrases-only

**When to use:** NLU quality is the problem, not vocabulary.

**Procedure:**

1. Add rows to `phrases.csv` only; do not touch `intents.csv` or `entities.csv`.
2. Follow Procedure E0 for every added or edited row.
3. Preserve CSV encoding (UTF-8) and column order.
4. Plan a retrain step.

**Pitfalls:** Regenerating the whole file instead of appending — easy way to lose existing spans.

---

## E4 · add-pattern-entities-mtt

**When to use:** yes/no (confirmation/denial) or other phrase families that need the team's MTT pattern language rather than a list of synonyms.
**Template source:** `scripts/nlu_data/potwierdzenia_zaprzeczenia_encja_pattern.csv` (entities `mtt_yes`, `mtt_no`).

**Procedure:**

1. Copy the rows verbatim into `nlu/<NLU>/entities.csv`. A pattern row is `name,"<multi-line LABEL/UNLABEL script>",,Pattern,[]` — one CSV record per entity, the script is a quoted multi-line cell with doubled quotes. Do not re-wrap or normalise the script.
2. The variable name is the entity name (`nlu.variables.mtt_yes`, `nlu.variables.mtt_no`).
3. In the flow, treat an answer as yes only when `mtt_yes` is present and `mtt_no` is absent, and the other way round. Both present or neither means unclear.
4. Add a keyword entity for hedging ("nie wiem", "chyba", "może") and check it first: the MTT "no" pattern labels "chyba nie" as a denial, which must never trigger an irreversible action.

**Verify:** `entities.csv` parses with a CSV reader into 5 columns per record; training in the NLU module succeeds; test "tak", "nie", "chyba nie", "nie wiem" and "to nie ja" in the NLU tester.

**Pitfalls:** Reading `nlu.intent` for yes/no when the model has only a few intents: a one-word answer is forced into the nearest intent.

---

## E5 · add-keyword-and-regex-entities

**When to use:** a closed vocabulary (sensitive words, hedging words) or a rigid string shape (digit groups) must be recognised deterministically.

**Procedure:**

1. Keyword entity row: `variable,canonical,"synonym1,synonym2",Simple,"[""variable""]"`. Several rows with the same variable and different canonical values are allowed. Polish words are lemmatised, so one inflected form is enough per lemma.
2. Regex entity row: `name,<regex>,,Regex,[]`. The regex lives in the NLU module, not in a flow block. The variable is the entity name and the matched text is `nlu.variables.<name>.match`. Pattern for exactly four digits, numerals or spoken: `(?<![\wąćęłńóśźż])(?:(?:\d|zero|jeden|dwa|trzy|cztery|pięć|sześć|siedem|osiem|dziewięć)(?![a-ząćęłńóśźż])\s*){4}(?!\d)`.
3. Convert the match in a `custom` block without regexes (loop over spoken digits with `split(word).join(digit)`, strip spaces, check length and characters).
4. System entities: `sys.Time,,,System,"[""time""]"`. `nlu.variables.time` is a **single object** (`value`, `grain`, `type`, `values[]`), not an array, so `nlu.variables.time.value.formatAsDate()` gives `yyyy-MM-dd`. Indexing it (`time[0]`) raises `ExpressionError: Bad arguments for getIndex operation, needed single StringValue, got List(LongValue(0))`. Check the shape in the NLU analyzer (Analyze → entity "Variable value preview") before relying on a system entity.

**Verify:** the entity columns are 5 per row; every flow expression names a variable that exists in `entities.csv`.

---

## E6 · read-nlu-results-in-flow

**When to use:** routing on what the NLU recognised.

**Rules:**

- `nlu.intent` plus `nlu.intentScore >= <threshold>` for intents that interrupt the dialog (global intents). Answers to closed questions come from entities, not intents.
- No training phrase of a global intent may start with a word that an answer entity reacts to ("nie …" collides with `mtt_no`).
- A simple (neural) NLU forces every short utterance into the nearest intent, often with a high score: an answer such as "tak, poproszę" was classified as a "repeat" intent (shared word "proszę") with score >= 0.6 and the Global Listener swallowed it (verified by running a test suite on the platform). Defence: (1) raise the guard (`nlu.intentScore >= 0.7`); (2) in the flow, global intents other than "agent" must not fire when the utterance contains an unambiguous yes (`nlu.variables.mtt_yes == null`); (3) handle closed vocabularies ("repeat") with keyword entities instead of intents. Do NOT add yes/no intents (e.g. `potwierdzenie`, `zaprzeczenie`) as contrastive classes: answers are read from the `mtt_yes`/`mtt_no` entities and such intents are not good practice. Add a test where an answer arrives with a noisy global intent.
- Silence is `nlu.user_input` empty or `null`. Do not create an intent to detect it.
- `nlu.variables.<name>` is `null` when absent, so `!= null` / `== null` are the presence tests.
- The public API cannot train the NLU: after every import the NLU must be trained manually, and until then `nlu.intent` is empty and every answer is "unclear".

---

# Category F — Tests

## F1 · add-test-case

**When to use:** a test policy explicitly requires tests; or a change adds a new happy/failure path worth regression-protecting.

**Procedure:**

1. Add a new `*.txt` test file under `testSuites/<suite>/`.
2. Register the file in the suite's `data.json`.
3. Start every test case file with `> *` as the first line. Automate test conversations must be triggered by a user message or an empty user message.
4. Structure the conversation using the verified markers (from `AGENTS.md`):
   - `>` user utterance
   - `<` bot response assertion
   - `*<` wildcard bot response
   - `?<` regex assertion
   - `#` tag assertion
   - `cmd NAME @ PARAMETER` command assertion
   - `<< JSON` mocked extra data
   - `<i JSON` mocked integration response (one per turn)
   - `<t TIME` mocked time
   - `assert ...` JavaScript assertion
5. Mock integrations **before** asserting any command or tag that depends on them.
6. Keep one integration mock per message turn.

**Verify:** every test case starts with `> *`; the test suite runs green after import; assertions cover both a happy path and at least one failure path.

**Pitfalls:** Asserting tags before mocking the integration that emits them, causing nondeterministic failures.

---

# Category G — Layout

> **Prerequisite note for this category.** Procedure G1 reuses position deltas from existing states. If the target context has no neighboring states yet (e.g. just after Procedure B12 created a context from a reference template), take the deltas from the *reference* context and keep them — but match the density to the target, not the absolute coordinates.

## G1 · position-new-state

**When to use:** every time a state is added or moved.

**Procedure:**

1. Do not invent layout schema. Identify a pair of neighboring states in the target or reference context — preferably from a context with **comparable visual density** to the one being edited.
2. Compute the `(Δx, Δy)` delta between those two states (e.g. dense reference: `Δx ≈ 150`, sparse target: `Δx ≈ 280`). Use deltas from a context that matches your target's density.
3. Place the new state by applying that delta relative to the state that precedes it on the main path. Do not paste absolute coordinates from a dense reference into a sparse target — they will collide.
4. Keep the main business path flowing **left to right**.
5. Put fallback, FAQ, and alternative paths **below** the main path.
6. Put confirmation and ending states at the **far right** when possible.
7. Leave extra margin around routing blocks (`say-conditional`, multi-output states).

**Verify:** after import, connectors do not overlap and state names remain readable.

**Pitfalls:**

- Copying absolute coordinates from a denser source into a sparser target — clusters form.
- Minimizing canvas width at the cost of readability. Optimize for readability instead.

---

## G2 · final-layout-pass

**When to use:** after all logic edits are complete, before packaging the result or importing it through the API.

**Procedure:**

1. Walk every edited context and visually check each state's position.
2. Reflow any state that overlaps a connector or another state.
3. Re-group fallback/FAQ paths below the main path.
4. Confirm confirmation/end states are at the far right.
5. Re-run Procedure A2 quickly for every touched state to confirm wiring still holds.

---

# Category H — Packaging and validation

## H1 · preserve-original-export-artifact

**When to use:** every delivery.

**Procedure:**

1. Never overwrite the original source artifact, whether it came from `input/` or from an API export.
2. If the delivery path is ZIP-based, write the new ZIP to `output/` with a distinct name.
3. If the delivery path is API-based, keep the generated ZIP/import artifact distinct from the original export and do not mutate the source export in place.
4. Preserve the exact folder structure of the export: `project.json`, `projectMetadata.json`, `flows/*.json`, `nlu/<NLU>/*`, `integrations.json`, `testSuites/<suite>/*`.

**Pitfalls:** Accidental overwrite of the source export; wrong folder depth in the ZIP (Automate silently rejects).

---

## H2 · preflight-validation

**When to use:** right before packaging or importing, and as the last step of every implementation.

Run through the **"Validation Checklist Before Re-Zipping"** section in `AGENTS.md`. That checklist is the normative preflight. This procedure exists only to make sure it is actually executed — under time pressure, this is the step most often skipped.

Additionally, validate every edited `flows/*.json` against `flows.schema.json` using a JSON Schema validator. Schema validation catches silent structural drift (missing required empty arrays, wrong `type` values, malformed `indexedExpression` shapes) that a prose checklist does not cover on its own.

Note that `flows.schema.json` alone is **not** sufficient for publish-safety: it marks `requestUserInput` as optional, but the platform rejects an `empty` state that lacks it (publish `status: "Invalid"`, no message — see B9). When publish returns `Invalid` with no detail, compare the flow block-by-block against a published reference and check for fields that are schema-optional but platform-required, before suspecting the NLU (an `OutSync`/untrained NLU does not block publishing).

If any item on either layer fails, stop and fix before producing the ZIP or importing through the API.

---

## H3 · import-and-verify-round-trip

**When to use:** every import through the API.

**Procedure:**

1. Rebuild the ZIP and check that the build finished (exit code, new ZIP timestamp). A build that dies halfway leaves the previous ZIP in `output/`, and importing it looks like a successful import.
2. Import into the intended project (`--project-id <UUID>`; for a new project the UUID in `project.json` must be new, never a reference's).
3. Export the project again and compare it with what was built: contexts, `conversationEndingContextRef`, NLU files, credential ids, integrations.
4. Tell the user what cannot be checked through the API: NLU training, canvas appearance, publication status (publishing is opt-in).

**Pitfalls:** `scripts/automate doctor` does not check that the configured default project still exists.

---

# Category I — Decision guides

These are not procedures, they are tie-breakers for the recurring "which one?" questions.

## I1 · say-llm vs llm-integration

- Use `say-llm` when the **bot speaks** the model's output to the user (natural phrasing, single utterance, optional mid-turn tools).
- Use `llm-integration` when the model output is **data for routing or logic**, read from memory by subsequent deterministic blocks.
- If in doubt, split the job: `llm-integration` decides, `say-llm` (or plain `say`) speaks.

## I2 · AEL vs JavaScript

- Plain literal values, direct memory writes, concatenation, and simple conditions → **AEL**.
- Supported one-expression method chains on strings, numbers, arrays, objects, and DateTime values → **AEL**. Examples: `system.userInput.toLower()`, `memory.items.filter(item => item.active = true)`, `memory.items.map(item => item.name)`, `system.currentTime.plusDays(1).formatAsDate()`.
- Multi-step transformations, assignments, loops, helper functions, dynamic object mutation, complex ranking, or logic that is unreadable as one expression → **JavaScript** (`useJS: true`).
- Never use JavaScript just because it feels more familiar. A `useJS: false` AEL expression is cheaper and easier to maintain.
- If a value can be expressed clearly with AEL methods documented under `docs/Expression language/methods-and-apis-overview/`, prefer AEL.

## I3 · New context vs extend existing context

- New context when the responsibility is genuinely separable (authorization, a specific business process, API orchestration, global handler).
- Extend existing context when the change belongs to the same business responsibility and would not be reused.
- Never mix auth, business logic, and global behavior inside one context.

## I4 · When to edit entities.csv

- Only if the task genuinely requires new vocabulary.
- If adding training phrases solves the problem, prefer E3 over E2.
- If the task can be fully solved in flows/JS, prefer that.

## I5 · When to touch integrations.json

- Only if the required endpoint does not exist.
- Prefer reusing an existing integration + request pair via Procedure B4.
- If you must add a request, do not change UUIDs or reference names of existing ones — every matching flow block must be updated, and that is where most manual-edit bugs appear.
- Put every sensitive value (API key, token, `Authorization`) in the secrets module and reference it as `{secrets.name}` — never via `memory.*` inputParameters or a hardcoded literal (B4a step 8a). The secret is created by the user in the UI on the target environment and cannot be set via the API.

## I6 · When to add a test

- Unless explicitly requested otherwise, always add or update at least one happy-path test and one failure-path test for the changed context.
- Always add the needed integration mocks when the change depends on external responses.
- If the task changes flow logic and no tests were updated, treat that as a gap to explain and fix, not as the default outcome.

## I7 · When to use Chunker API for RAG content

- Use `.agents/skills/chunker-api/SKILL.md` and `scripts/chunker` when the task is to prepare source files, URLs, raw text, or Markdown for RAG or knowledge-base ingestion.
- Prefer `ingest`: it takes any mix of files, URLs and a crawled domain in one call and returns an Automate-ready XLSX. It has no conversion or chunking options, because the server decides routing and chunk strategy per document.
- Reach for `chunk` only when Markdown already exists and just needs splitting, or `rechunk-csv` when an existing chunk CSV must be re-chunked rather than merged as-is.
- If generated chunks have incomplete sentences, duplicated overlap, or broken table rows, treat it as a Chunker API/configuration issue first; tune Chunker settings or report a backend issue instead of adding local post-processing scripts unless explicitly requested.
- Treat Chunker output as draft knowledge-base material: inspect chunk boundaries, metadata, source provenance, and accidental secrets before import.
- When reviewed chunks must be uploaded into Automate, use `.agents/skills/automate-api/SKILL.md` and `scripts/automate knowledge documents upsert`; knowledge base content is organization-wide and is not part of the project ZIP.

## I8 · Agentic RAG with LLM tool calling

- Use `reference/simple-agentic-polish-RAG.zip` for the minimal Polish pattern where the LLM formulates the semantic-search query as a tool call.
- Do not assume Automate executes Knowledge Base search directly from the tool definition. Verified exports define a normal LLM tool, then route by `memory.toolCalls[0].name` to a downstream `custom` state.
- Execute search in flow logic with `knowledge.semanticSearch(...)`, then write `memory.toolResults` as an array of objects containing the original tool-call `id` and a `result` payload.
- Route back to the same `say-llm` block after writing tool results so the model can answer from the returned context or request a better search.
- Reset stale `memory.toolCalls`, `memory.toolResults`, and the per-question search counter before each new user question.
- Add a deterministic search retry limit; do not let the model loop indefinitely.

---

# Category J — Generating a bot from code

## J1 · generate-the-export-with-a-script

**When to use:** a bot is built from a requirements document and will be rebuilt many times.

**Principles:**

1. The script is the source of truth; never hand-edit the exported JSON. Every state factory copies a verified shape and parametrises only what must change.
2. Keep memory keys flat unless the parent object is created earlier; keep entries of one `custom` block independent.
3. Keep JavaScript out of regexes (A4), recognition in the NLU module (E4-E6), the Global Listener as a parent tree (D0), the API calls in mockable contexts (B4b).
4. Generate the test suite from an offline simulation of the same flow; use `*<` wildcards for lines that depend on the date or on random sandbox ids.
5. Validate (`scripts/validate_export.py`), unit-test the JavaScript snippets, simulate every acceptance scenario, then import and compare (H3).

## J2 · bisect-a-canvas-problem-on-throwaway-projects

**When to use:** the flow runs, but the canvas shows something wrong that the JSON does not explain (invisible connectors, empty blocks).

**Procedure:**

1. Take a minimal project that displays correctly (the empty polish starter) and import it as a new project with a new UUID, named `ZZ debug …`.
2. Import variants that each change one thing relative to it: positions and JSON formatting; fresh ids; a routing `empty` block; the context `model` shape; the extra keys on states. Ask the user which variants display correctly.
3. Narrow down with the user's yes/no answers, then fix the generator, rebuild and import into the real project.
4. Ask the user to delete the throwaway projects (the helper CLI cannot).

**Verified outcome:** invisible connectors came from `isEmptyPoint: true` on routing `empty` blocks (B9); a second occurrence came from `isQuickPoint: true`. Before bisecting, diff the key sets of every generated state type against the same type in Finance/Medical Bot: a key that no reference state of that shape carries is the first suspect.

---

# Anti-patterns (quick index)

- Letting an LLM decide business actions. Use B6 + deterministic routing.
- Connecting transitions state-to-state. Transitions are `output.id → state.id`.
- Inventing memory schema. Always reuse the `{ index, useJS, value }` shape (B3).
- Copying a context via B12 without regenerating every nested UUID (context, model, state, output). Silent collisions will result.
- Setting `errorHandlingContextRef` to a `uuid` instead of a `referenceName` (B13).
- Leaving a new state without outgoing transitions "for now".
- Creating an `empty` state without `requestUserInput` — flow publishes as `Invalid` with no message (B9). Not an NLU-training problem.
- Minimizing canvas width at the cost of readability (G1, G2).
- Copying absolute position coordinates from a dense reference into a sparse target (G1).
- Removing a state without updating transitions that pointed at its outputs (B15).
- Using commands for business logic (B14).
- Overwriting the original source export artifact (H1).
- Omitting required happy-path and failure-path regression tests for a changed context.
- Editing `integrations.json` to rename things "for clarity".
- Invented fields in `flows/*.json` that are not in `flows.schema.json`, the target export, or the reference export.
- Starting a new bot project by hand instead of bootstrapping from `reference/empty polish project.zip`.
- Two `start` blocks in one context sharing the same downstream subgraph instead of each leading its own separate tree (B11).
- Defaulting an LLM block to GPT-5 instead of a "mini"-tier model — too slow for a live conversation (B6, B7). Exception: `say-llm` with tool calling uses a non-mini model such as `gpt-4.1`.
- Voice bots that read digits, amounts, dates or abbreviations as written: voice text must be phonetic and computed in JS (AGENTS.md, Commands and Voice-Specific Behavior).
- Pasting a full JSON object into a `say-llm`/`llm-integration` prompt field instead of describing fields in prose or interpolating only the needed values (B6, B7).
- Regular expressions inside flow blocks (AEL or JavaScript); use NLU entities (A4, E4-E6).
- Setting `isEmptyPoint: true` or `isQuickPoint: true` on a routing `empty` block: the canvas then shows no connectors (B9).
- Reading `nlu.variables.time[0]`: the entity is one object, not an array (E5).
- Copying the `x`/`y`-only context `model` of the empty starter onto real flows (B12).
- Attaching the Global Listener as a floating `context` block, or wiring its output back into the context, instead of the parent `start` tree (D0).
- Detecting yes/no with a few intents instead of the MTT answer entities plus a hedging entity (E4).
- Importing a ZIP without checking that the build finished (H3).
- Reading a nested memory path (e.g. `memory.x.y`) before its parent object has ever been created — the dialog errors instead of the read evaluating to `null` (B3).

---

# When a procedure is missing

If the task needs an operation that has no matching procedure in this file, **and** no verified template in the target or reference export covers it, **and** Automate documentation does not clarify, the agent must:

1. Stop.
2. Describe the gap in the analysis output.
3. Ask for an explicit decision before editing.

That pause is the whole point of this framework.
