---
name: automate-api
description: Use this skill when the task is to operate on SentiOne Automate through the local Public API helper, including setup validation, host/profile selection, projects export/import, conversation search/messages/recordings, AI credentials, knowledge base documents or items, and dialer contacts without exposing API secrets in chat, CLI parameters, or environment variables.
---

# Automate API

Use this skill for SentiOne Automate API operations that should go through the local helper in `scripts/automate`.

Do not use this skill for direct flow editing once the project is already unpacked. After export, follow the normal repository procedures from `AGENTS.md` and `AUTOMATE_EXPORT_PLAYBOOK.md`.

## Safety rules

- Never ask the user to paste the API key into chat.
- Never pass the API key through CLI arguments or environment variables.
- Use only the local non-secret config file plus OS keychain lookup handled by `scripts/automate`.
- Never print `X-Api-Key` values or raw auth material from config or logs.
- Treat `--publish-flows` as opt-in. Do not enable it unless the user asked for publish behavior.
- Treat recording deletion and knowledge-base imports/upserts as destructive. Do not run them unless the user explicitly asked for that operation and the target host/profile is clear.

## Preconditions

Before making API calls, confirm the local helper is healthy:

```bash
scripts/automate doctor
```

If the user needs setup help, use:

```bash
scripts/automate config-path
scripts/automate init-config
```

For the expected config shape and host layout, read only the relevant setup section in `README.md`.

## Host and profile selection

Prefer a named profile when one matches the task. Use a host override only when the user wants to point the same profile at a different deployment.

Discovery:

```bash
scripts/automate hosts
scripts/automate projects --profile <profile>
scripts/automate projects --host <host>
```

Rules:

- `--profile` selects project, directories, and keychain identity together.
- `--host` overrides only the selected Automate deployment.
- `--project-id` on import overrides only the target project ID. Use it for creating a new project without changing local config.
- If the user names neither, use the default profile from the local config.
- If a command fails because the configured project does not exist on the selected host, stop and correct the profile or host rather than retrying blindly.

## Core project workflow

List projects:

```bash
scripts/automate projects
scripts/automate projects --profile <profile>
scripts/automate projects --host <host>
```

Export the configured project:

```bash
scripts/automate export
scripts/automate export --profile <profile>
scripts/automate export --host <host>
```

Import a ZIP back into the configured project:

```bash
scripts/automate import output/<zip-name>.zip
scripts/automate import output/<zip-name>.zip --profile <profile>
scripts/automate import output/<zip-name>.zip --host <host>
scripts/automate import output/<zip-name>.zip --project-id <newProjectUuid>
scripts/automate import output/<zip-name>.zip --publish-flows
```

Workflow:

1. Run `scripts/automate doctor`.
2. Confirm the target host or profile.
3. Run `scripts/automate export` before editing when the task needs the latest project state.
4. Perform the repo-local flow, NLU, integration, or test changes.
5. Repackage to `output/`.
6. Run `scripts/automate import <zip>` only after local validation passes.

Lessons from building a bot from scratch:

- `scripts/automate doctor` does not check that the configured default project still exists. If `export` answers 404, do not retry: import into a new project with `--project-id <new UUID>` (the same UUID as `project.json.uuid` in the ZIP) after the user has agreed on the target.
- If a generator or build script can fail halfway, confirm that it finished and that the ZIP timestamp is new before importing. Importing a stale ZIP looks identical to a successful import.
- After an import, export the project again with `--project-id` and compare it with what was built. It shows what the platform kept (contexts, `conversationEndingContextRef`, NLU files, credential ids).
- The public API does not train the NLU, so tell the user to train it after every import.

## Conversations

Use the conversations subcommands when the task involves historical sessions, transcripts, or recordings.

Search sessions:

```bash
scripts/automate conversations search --from 2026-01-01T00:00:00.000Z --to 2026-01-31T23:59:59.000Z
scripts/automate conversations search --project-id <projectId> --limit 100
scripts/automate conversations search --output output/conversations.json
```

Fetch message history for one session:

```bash
scripts/automate conversations messages <internalSessionId>
scripts/automate conversations messages <internalSessionId> --include-bot-logs
scripts/automate conversations messages <internalSessionId> --json
```

Download or play a recording:

```bash
scripts/automate conversations recording <internalSessionId>
scripts/automate conversations recording <internalSessionId> --play
```

Delete or schedule deletion of a recording:

```bash
scripts/automate conversations recording-delete <internalSessionId>
scripts/automate conversations recording-schedule-deletion <internalSessionId> 2026-05-01T12:00:00.000Z
```

Rules:

- Use `--output` when the user needs a saved artifact instead of terminal output.
- Use `--json` when the task needs exact API payload structure.
- Distinguish `system.sessionId` from `system.internalSessionId`: the former is the external Gateway `suid` and can span multiple Automate conversations, while the latter identifies exactly one conversation for message and recording endpoints.
- `POST /conversations/search` does not provide an author request filter. For same-author history inside a flow, restrict the search with `projectIds`, sort newest first, filter returned `author` values against non-empty `system.author`, and exclude the active `system.internalSessionId` before fetching messages.
- Do not load cross-session history when `system.author` is empty; anonymous-author matching can mix unrelated users.
- Keep `includeBotLogs` disabled when transcript text will become LLM context. Bot logs are designer diagnostics and may contain implementation details or sensitive data.
- Do not fetch recordings unless the user asked for them.
- Do not delete or schedule deletion of recordings unless the user explicitly asked for deletion behavior.

## AI credentials

List organization AI credentials when a knowledge-base document upload needs an embeddings credential:

```bash
scripts/automate ai-credentials
scripts/automate ai-credentials --json
scripts/automate ai-credentials --output output/ai-credentials.json
```

Use only credential IDs returned by the API or clearly supplied by the user. Do not infer credential IDs from names when multiple credentials have similar names.

IDs returned by the API are not always UUIDs (for example `openai`), while `flows.schema.json` only allows a UUID or `null` for `credentialsId`. Report that mismatch instead of hiding it.

## Knowledge base

Use the knowledge commands for the public API knowledge-base endpoints. Knowledge base content is organization-wide, not part of a project ZIP.

Documents:

```bash
scripts/automate knowledge documents list
scripts/automate knowledge documents get <key>
scripts/automate knowledge documents upsert <key> output/kb-document.csv
scripts/automate knowledge documents upsert <key> output/kb-document.xlsx --embeddings-credentials-id <credentialId>
scripts/automate knowledge documents export <key> --format csv output/kb-document.csv
scripts/automate knowledge documents export <key> --format xlsx output/kb-document.xlsx
```

Items:

```bash
scripts/automate knowledge items export output/knowledge-items.csv
scripts/automate knowledge items import output/knowledge-items.csv
```

Rules:

- Confirm the active host/profile before importing items or upserting documents.
- Use `ai-credentials` first when a document must use a specific embeddings credential.
- Use default embeddings credentials only when that is acceptable for the target environment.
- Before importing items, inspect the CSV shape: `key`, `value`, optional `expiresAt`.
- Respect the API row cap for item import. The spec documents a maximum of 10,000 rows.
- When preparing RAG document CSV/XLSX files from source documents, use `.agents/skills/chunker-api/SKILL.md` and `scripts/chunker` first, then upload the reviewed output through `knowledge documents upsert`.

## Dialer

Use the dialer command to add a contact to an existing campaign:

```bash
scripts/automate dialer contacts add <campaignId> \
  --phone-number "+48 123 456 789" \
  --calling-start 2026-07-08T09:00:00+0000 \
  --calling-end 2026-07-09T09:00:00+0000 \
  --call-attempts-limit-per-day 3 \
  --call-param clientName="John Doe"
```

For complex payloads, prefer an untracked local JSON file:

```bash
scripts/automate dialer contacts add <campaignId> --payload-file input/contact.json
```

Rules:

- Confirm the campaign ID before adding contacts.
- Do not put sensitive customer data in tracked files.
- Use `--payload-file` for larger payloads so command history does not capture personal data unnecessarily.

## Verification

After export:

- confirm the ZIP was created under the configured export directory
- confirm unpacking produced the expected workspace directory
- if the task is about editing the bot, switch to the repo flow-editing rules before changing files

After import:

- confirm the import request succeeded
- tell the user whether `publishFlows` was enabled
- if the change affected NLU, remind the user that training may still be required in Automate

After conversation retrieval:

- confirm the session count or target session id
- if saving files, report the output path
- if playback was requested, report whether the file was opened successfully

After recording deletion or scheduled deletion:

- report the internal session id
- report the scheduled deletion time when applicable

After knowledge-base operations:

- for document list/get/upsert, report the document key and indexation status when available
- for document/item exports, report the saved output path
- for item import, report added, updated, and unchanged counts from the API response
- remind the user that knowledge base changes are organization-wide when that affects delivery risk

After dialer contact creation:

- report the campaign ID
- report whether the API accepted the contact

## Failure handling

- If `doctor` fails on config or keychain lookup, stop and fix local setup before using the API.
- If project listing works but export or import returns `404`, verify the selected host and configured `projectId`.
- If a conversation endpoint returns no data, confirm the time range, project filter, and session id before assuming an API defect.
- If knowledge document upsert returns `400`, verify the file type, CSV/XLSX structure, and embeddings credential ID.
- If knowledge item import returns `FileTooBig`, `DuplicateKeys`, `InvalidCsv`, or `ImportFailed`, fix the CSV locally before retrying.
- If recording deletion returns `RecordingNotDeletable`, the recording is externally hosted and cannot be deleted through this API.
- If dialer contact creation fails, verify campaign ID, ISO-8601 date-time fields, phone number format, and required call-attempt limit.
- If the command surface is unclear, inspect `scripts/automate --help` or the relevant subcommand help instead of guessing flags.
