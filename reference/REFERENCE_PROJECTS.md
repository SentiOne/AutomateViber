# Reference Projects

## Reference: Log Examples

### Summary
A minimal Polish-language reference project for Automate designer-visible logging. It demonstrates the new `log` block plus the logging switches on `Integration`, `llm-integration`, and `say-llm` states. Logs produced by these mechanisms are visible to bot designers in the Conversation module and through API-accessible conversation data; they are not sent to the end user as chat messages.

Reference export:
- `reference/log-examples.zip`

### Recommended use
Use this reference when working on:
- adding a standalone `log` state for designer diagnostics
- enabling request/response logging on new `Integration` states with `logRequestResponse`
- enabling prompt/response logging on new `llm-integration` states with `logParametersAndResponse`
- enabling prompt/tool-parameter logging on new `say-llm` states with `logParameters`
- validating the exact exported shape of logging-related fields
- teaching future project-generation work how to expose useful runtime details to bot designers

Do not use it as an architecture reference for production conversation design, global fallback, RAG, authorization, or multi-context transactional flows. It is intentionally small and exists to show logging structures.

### Project profile
- **Language:** Polish
- **Bot type:** Logging feature reference
- **Multi-language:** No
- **LLM blocks:** Yes
- **RAG:** No
- **Authorization:** No
- **Tests:** No
- **Integrations:** Yes
- **Voice-like patterns:** No
- **Best suited for:** Logging block/schema examples and observability defaults

### Main flow areas
- Initializing simple and complex memory values
- Writing a designer-visible Log block message
- Logging a structured object from memory through the Log block
- Calling an HTTP Integration with request/response logging enabled
- Running an `llm-integration` block with parameters-and-response logging enabled
- Running a `say-llm` block with parameters logging enabled

### Reusable patterns

#### Block shape patterns
- **Standalone Log block** — `type: "log"` with `message` as a standard expression object and `objects` as an array of `{ key, params }` entries.
- **Integration logging** — new `Integration` states can include `logRequestResponse: true` so designers can inspect the actual request/response data during conversation review.
- **LLM Integration logging** — new `llm-integration` states can include `logParametersAndResponse: true` so designers can inspect both the LLM inputs and generated machine-readable result.
- **LLM Say logging** — new `say-llm` states can include `logParameters: true` so designers can inspect prompt context and tool-call parameters while the generated answer remains normal user-facing output.

#### Observability patterns
- **Logs close to their source** — the Log block is placed immediately after memory initialization, making the logged values easy to correlate with the state that produced them.
- **Structured log objects** — complex memory values are logged as named objects instead of being flattened into the human-readable message.
- **Designer-only diagnostics** — logging provides debugging context without adding extra bot responses or exposing diagnostics to the end user.

#### Adaptation notes
- Enable logging by default on new `Integration`, `llm-integration`, and `say-llm` blocks when it helps designers debug the bot.
- Do not log secrets, credentials, access tokens, raw authentication payloads, or sensitive personal data.
- Use `conversationMetadata` when data must become durable business/debug metadata; use Log blocks and logging flags when the goal is designer-visible conversation diagnostics.
- Keep the Log block connected in normal flow routing; it has outputs and transitions like other states even though it does not speak to the user.

---

## Reference: simple-naive-polish-RAG

### Summary
A minimal Polish-language RAG reference project for a new Automate bot. It shows the smallest useful flow-level pattern: ask for a user question, detect an exit phrase, run `knowledge.semanticSearch`, answer with a constrained `say-llm` block when context exists, handle no-match results, and loop for another question.

Reference export:
- `reference/simple-naive-polish-RAG.zip`

### Recommended use
Use this reference when working on:
- new simple Polish RAG bots
- proof-of-concept knowledge-base assistants
- flows that should avoid NLU-heavy routing
- projects where the main behavior is question-answering over one Automate Knowledge Base document
- examples of `knowledge.semanticSearch` feeding a narrow `say-llm` response block
- minimal happy-path and no-match test-suite structure

Do not use it as the primary reference for large production assistants with authorization, multiple business processes, global listener/fallback logic, handoff, or complex transactional behavior. Use Insurance Bot or Administration Bot for those patterns.

### Project profile
- **Language:** Polish
- **Bot type:** Simple RAG / FAQ
- **Multi-language:** No
- **LLM blocks:** Yes
- **RAG:** Yes
- **Authorization:** No
- **Tests:** Yes
- **Integrations:** No
- **Voice-like patterns:** No
- **Best suited for:** Small structures and new-project bootstrapping

### Main flow areas
- Asking for a knowledge-base question
- Exit phrase detection through a `custom` state
- Semantic search against an Automate Knowledge Base document
- Context-grounded answer generation with `say-llm`
- No-match response
- Looping for the next user question

### Reusable patterns

#### Context structure patterns
- **Single-context RAG loop** — the whole assistant lives in one context with a clear left-to-right loop, making it easy to inspect and adapt for small projects.
- **External knowledge dependency isolated in one custom block** — the Knowledge Base key, semantic search limit, threshold, context formatting, and answer instructions are centralized in the search block.
- **No NLU dependency for the main path** — user questions are handled directly from `system.userInput`; the only deterministic classification is the exit phrase check.

#### Path patterns
- **Found vs no-match branch** — semantic search success and failure are routed as separate outputs, so the bot does not call the LLM when no useful context exists.
- **Answer then re-ask loop** — successful answers return to a short follow-up prompt instead of ending the conversation.
- **Explicit user-controlled termination** — common Polish exit phrases end the conversation through a `terminate` state.

#### Mechanism patterns
- **`knowledge.semanticSearch` for retrieval** — retrieved matches are formatted into a text context block before being passed to `say-llm`.
- **Grounded `say-llm` prompt** — the LLM is instructed to answer only from retrieved context and to say when information is missing.
- **Minimal tests** — the export includes one happy-path test and one no-match/failure-path test as a baseline for new RAG projects.

#### Adaptation notes
- Replace the default Knowledge Base document key `simple_naive_polish_rag` before reuse, or upload a document under that key.
- Replace the LLM `credentialsId` with a credential available in the target environment.
- Adjust domain-specific wording, tags, memory paths, and tests for the new project.
- Knowledge Base documents are external to the ZIP and must be uploaded separately.

---

## Reference: simple-agentic-polish-RAG

### Summary
A minimal Polish-language agentic RAG reference project for a new Automate bot. It shows the tool-calling RAG pattern: the LLM creates a search query, emits a tool call, the flow executes `knowledge.semanticSearch` in a `custom` block, writes tool results back to memory, and loops into the same `say-llm` block for the final grounded answer.

Reference export:
- `reference/simple-agentic-polish-RAG.zip`

### Recommended use
Use this reference when working on:
- new simple Polish agentic RAG bots
- proof-of-concept assistants where the LLM should formulate or refine the search query
- flows where semantic search is exposed as an LLM tool
- examples of `toolCallsMemoryPath` / `toolResultsMemoryPath` wiring
- examples of returning Knowledge Base results in the required `{ id, result }` tool-result shape
- simple agentic search loops with a deterministic retry limit

Prefer `simple-naive-polish-RAG` when deterministic pre-search is enough. Prefer this reference when the LLM should decide how to query the Knowledge Base and optionally retry with a better query.

### Project profile
- **Language:** Polish
- **Bot type:** Simple agentic RAG / FAQ
- **Multi-language:** No
- **LLM blocks:** Yes
- **RAG:** Yes
- **Authorization:** No
- **Tests:** Yes
- **Integrations:** No
- **Voice-like patterns:** No
- **Best suited for:** Small structures and agentic-search bootstrapping

### Main flow areas
- Asking for a knowledge-base question
- Exit phrase detection through a `custom` state
- Resetting stale tool calls and tool results before each new question
- Agentic `say-llm` with a `search_knowledge_base` tool
- Semantic search execution in a downstream `custom` state
- Tool-result feedback loop into the same `say-llm` block
- Search retry limit handling

### Reusable patterns

#### Context structure patterns
- **Single-context agentic RAG loop** — the assistant keeps the user question, tool call, search execution, and final answer loop in one readable context.
- **Tool execution outside the LLM block** — the `say-llm` block only emits tool calls; a `custom` state executes `knowledge.semanticSearch` and writes the result back to memory.
- **Per-question cleanup** — `memory.toolCalls`, `memory.toolResults`, and the search counter are reset before each new user question to avoid stale tool state.

#### Path patterns
- **Tool-call branch** — the `say-llm` output routes to search when `memory.toolCalls[0].name` is `search_knowledge_base`.
- **Tool-result loop** — after search execution, the flow returns to the same `say-llm` block so the model can answer from `memory.toolResults` or request a better search.
- **Deterministic retry limit** — the search execution state increments a counter and routes to a fallback response after repeated searches.

#### Mechanism patterns
- **Semantic search as an LLM tool** — the tool definition contains a required `query` argument, but the actual search is performed by flow logic with `knowledge.semanticSearch`.
- **Required tool-result shape** — tool results are written as an array of objects with the original tool call `id` and a `result` payload.
- **Grounded answer prompt** — the LLM is instructed to answer only from tool results, not from its own knowledge.

#### Adaptation notes
- Replace the default Knowledge Base document key `simple_agentic_polish_rag` before reuse, or upload a document under that key.
- Replace or configure the LLM `credentialsId` in the target environment.
- Adjust the tool description, prompt, tags, retry limit, and tests for the target domain.
- Knowledge Base documents are external to the ZIP and must be uploaded separately.

---

## Reference: Agentic Search Demo

### Summary
A production-shaped Polish logistics assistant demonstrating agentic search across multiple specialized Knowledge Base documents. It combines deterministic intent routing with tool-calling `say-llm` agents, iterative retrieval, parcel tracking, shipment pricing, safety checks, and address-based parcel-locker lookup.

Reference export:
- `reference/agentic-search-demo.zip`

### Recommended use
Use this reference when working on:
- multi-tool agentic RAG with one tool per knowledge domain
- query rewriting before retrieval
- repeated semantic search with accumulated tool results
- LLM intent routing into deterministic business contexts
- bounded shipment-pricing or data-collection agents
- prompt-injection and unsafe-input detection before business routing
- combining Knowledge Base answers with trusted transactional data already held in memory
- location normalization and geocoding integrations

Prefer `simple-agentic-polish-RAG` for a minimal single-tool teaching example. Use this project when the task needs a larger production-shaped router, several specialized knowledge sources, or agentic search alongside transactional paths.

### Project profile
- **Language:** Polish
- **Bot type:** Agentic RAG and transactional logistics demo
- **Multi-language:** No
- **LLM blocks:** Yes
- **RAG:** Yes
- **Authorization:** No
- **Tests:** No
- **Integrations:** Yes
- **Voice-like patterns:** No
- **Best suited for:** Multi-tool agentic retrieval and hybrid routing
- **Export compatibility:** Flow version 8; platform version 265.17

### Main flow areas
- LLM-based top-level intent routing
- Multi-domain DPD FAQ retrieval with eleven search tools
- Query rewriting before the FAQ agent
- Iterative retrieval with a deterministic search limit
- Shipment pricing agent with domestic and international tools
- Parcel tracking through an external integration
- Parcel-locker lookup using location normalization and Google Maps geocoding
- Prompt-injection and safety checks
- Global commands for agent handoff, restart, and conversation termination

### Reusable patterns

#### Agentic retrieval patterns
- **One tool per knowledge domain** — the FAQ agent exposes separate tools for general FAQ, complaints, domestic and international pricing, packaging, restricted goods, parcel parameters, terms, and branch locations instead of searching one undifferentiated corpus.
- **Tool-to-database allowlist** — a downstream `custom` state maps known tool names to fixed Knowledge Base document keys. The model cannot choose an arbitrary database identifier.
- **Accumulated tool results** — retrieval preserves prior `{ id, result }` entries by tool-call ID, avoids rerunning an existing call, and returns the complete result array to the same `say-llm` block for another decision.
- **Bounded retry loop** — deterministic counters limit repeated retrieval attempts and route exhausted searches to a fallback path.
- **Specialized fallback search** — broad fallback retrieval is offered as a distinct last-resort tool rather than the default first search.

#### Routing and safety patterns
- **LLM router with deterministic outputs** — an `llm-integration` classifies input into FAQ, parcel lookup, parcel-locker lookup, pricing, or fallback outputs; ordinary context transitions retain control of the process.
- **Input-length guard** — overly long messages are rejected before LLM routing.
- **Dedicated safety context** — entity-based prompt-injection detection and an LLM safety check run separately from the business contexts.
- **Trusted transactional context** — previously retrieved parcel data is passed to the FAQ agent as trusted memory so it can answer parcel-specific questions without searching the Knowledge Base.
- **Per-agent state reset** — tool calls, tool results, and counters are cleared before entering the FAQ or pricing agent to prevent state leakage between tasks.

#### Transactional patterns
- **Pricing as a focused agent** — a separate `say-llm` agent collects missing shipment parameters, selects exactly one domestic or international pricing tool, and grounds the estimate in retrieved pricing content.
- **Topic-change detection** — a narrow `llm-integration` identifies when the user leaves the pricing process and returns control to the main router.
- **Geocoding after normalization** — location input is normalized before the Google Maps integration, then deterministic logic filters results and selects an active parcel locker.

### Adaptation notes
- The export depends on multiple external Knowledge Base documents: `dpd_faq_general`, `dpd_faq_reklamacje`, the `*_claude` pricing/content documents, `dpd_offices_poland_2026`, and `dpd_demo_rag_2026`.
- Configure an AI credential matching the referenced credential in the target environment; flow-version-8 exports may require credential reselection when imported into older Automate versions.
- Configure the Automate secret `GoogleMapsGeocodeApi` before using geocoding.
- The Make webhook endpoint in this reference was replaced with an inert placeholder. Configure a target-environment parcel-tracking endpoint before use.
- The export contains no test suite. Add happy-path and failure-path tests before adapting it for production work.
- Tool arguments in this flow-version-8 export may omit an empty `enum` field, and delayed-message configuration may omit `repeatDelay`; both shapes are supported by the repository schema.
- Knowledge Base documents are external to the ZIP and must be uploaded separately.

---

## Reference: Insurance Bot

### Summary
A large Polish-language reference project for complex customer service automation in SentiOne Automate. This bot combines hybrid architecture, agentic patterns, LLM-supported flows, RAG-based FAQ handling, and traditional tree-based conversation design. It is a strong reference for advanced, production-style assistants that rely on both deterministic logic and AI-assisted behavior.

### Recommended use
Use this reference when working on:
- large bot structures
- hybrid bots that combine LLM and traditional flow logic
- bots with authorization and customer verification
- RAG-based FAQ flows
- external system integrations
- voice-like conversational patterns
- escalation and redirection to human agents
- operational bots with test coverage and error handling

### Project profile
- **Language:** Polish
- **Bot type:** Hybrid, agentic, LLM-supported, traditional tree-based
- **Multi-language:** No
- **LLM blocks:** Yes
- **RAG:** Yes
- **Authorization:** Yes
- **Tests:** Yes
- **Integrations:** Yes
- **Voice-like patterns:** Yes
- **Best suited for:** Large structures

### Main flow areas
- Client verification
- Redirecting to agents
- Error handling
- Global listener
- Global fallback
- NPS
- FAQ based on RAG
- Retrieving data from an external database (Google Sheets)
- Updating an external database (Google Sheets)
- Checking Jira issue status

### Reusable patterns

#### Context structure patterns
- **Global listener as a separate context** — cross-cutting intents (agent request, goodbye, repeat, silence, emergency) are isolated in a dedicated global listener context, never buried inside business contexts
- **Global fallback with stateful counters** — fallback logic uses retry counters to decide between re-asking, clarifying, and escalating to a human agent; the counter resets on successful recognition
- **Error handler as a named context reference** — `errorHandlingContextRef` points to a dedicated error context that is reused across the whole flow, not duplicated per context

#### Path patterns
- **Main business path left to right** — happy path flows horizontally, fallback and error paths branch downward from the main path
- **Escalation path as a terminal branch** — agent redirection is a one-way path that ends with a `redirect` or `terminate` block, never loops back
- **NPS as a post-conversation context** — satisfaction survey is placed after the main business process ends, called via a `context` block before `terminate`

#### Mechanism patterns
- **RAG-based FAQ mechanism** — knowledge base lookup is handled in a dedicated FAQ context; the main flow routes unrecognized intents to it via a `context` block and returns with `end` if no answer is found
- **Authorization gate** — customer verification runs in its own context before any business logic is entered; result is stored in memory and read by downstream contexts, never re-verified inline
- **LLM narrowly scoped to classification** — LLM blocks classify intent or confirmation, never own the full process; deterministic routing reads the LLM result from memory and decides what happens next

#### Memory patterns
- **Raw API response isolated under `memory.response.*`** — integration output is stored separately from normalized business objects to allow debugging without polluting business logic
- **`conversationMetadata` blocks for observability** — important API payloads and derived values are pushed into metadata at key points so they are visible in the debugger

---

## Reference: Administration Bot

### Summary
A multilingual administrative bot built in SentiOne Automate. This project combines RAG-based FAQ handling with traditional transactional tree-based flows. It is a strong reference for bots that mix knowledge-based assistance, structured operational processes, user data collection, external integrations, and human handoff. Because it covers both broad architecture and smaller reusable patterns, it can support both small changes and larger structural work.

### Recommended use
Use this reference when working on:
- multilingual bots
- FAQ and RAG-based assistants
- traditional transactional flows
- bots with authorization
- data collection and formatting flows
- integrations with external systems
- Jira creation flows
- Google Sheets operations
- Google Calendar integrations
- voice-like conversational patterns
- global listeners, fallback logic, and agent redirection

### Project profile
- **Language:** Polish, English
- **Bot type:** FAQ / RAG, traditional transactional tree-based
- **Multi-language:** Yes
- **LLM blocks:** Yes
- **RAG:** Yes
- **Authorization:** Yes
- **Tests:** Yes
- **Integrations:** Yes
- **Voice-like patterns:** Yes
- **Best suited for:** Both small changes and large structures

### Main flow areas
- Redirecting to agents
- Error handling
- Global listener
- Global fallback
- NPS
- Collecting data and saving it in Automate metadata
- Collecting user input and formatting it
- FAQ
- Retrieving data from an external database, Google Sheets
- Adding rows to an external database, Google Sheets
- Creating Jira issues
- Google Calendar

### Reusable patterns

#### Context structure patterns
- **Language detection at entry** — language is detected early in the main flow and stored in memory; all downstream `say` blocks and conditional responses branch on the stored language value rather than re-detecting it
- **Transactional context per business process** — each operational process (Jira creation, Google Sheets update, Calendar booking) lives in its own context with a clear entry point and `end` block to return to the caller
- **Data collection context with slot filling** — user data is collected in a dedicated context that loops until all required fields are filled, then returns the completed data object to the calling context via memory

#### Path patterns
- **FAQ as a parallel path** — FAQ handling runs as a separate context reachable from the global listener; it does not interrupt the main transactional path
- **Formatting step before external write** — user input is normalized or LLM-formatted in a `custom` or `llm-integration` block before being written to an external system, never written raw
- **Confirmation before write** — all external write operations (Google Sheets, Jira) are preceded by a confirmation step; the write context is only entered after explicit user confirmation

#### Mechanism patterns
- **Multilingual `say-conditional` blocks** — conditional responses inside `say-conditional` states use language stored in memory to select the correct response variant; all text variants live in the same block, not in separate states
- **Google Sheets as a lightweight external database** — read and write operations are isolated in dedicated API contexts; the main flow never calls the integration directly, only reads from memory after the API context returns
- **Jira creation flow** — issue creation is a multi-step context: collect summary, collect description, confirm, call integration, handle success and error outputs separately
- **Metadata collection for debugging** — `conversationMetadata` blocks are placed after each significant integration call to record the request and response payload

#### Memory patterns
- **Collected user data stored under a single structured key** — all fields gathered during data collection (name, date, description, etc.) are stored under one memory path as a composed object, not as individual flat keys
- **Integration result split into status and payload** — after each API call, the status (success/failure) and the response payload are stored separately so routing logic reads only the status without parsing the full response

---

## Reference: Medical Bot

### Summary
A Polish-language transactional medical bot built in SentiOne Automate. This project is designed for appointment booking and combines structured business logic with LLM-supported handling, RAG-based assistance, authorization, external integrations, and voice-like interaction patterns. It is a strong reference for bots that manage complex booking processes, collect multiple user preferences in one conversation, and handle a wide range of operational edge cases.

### Recommended use
Use this reference when working on:
- appointment booking bots
- medical or healthcare-related transactional flows
- bots integrated with scheduling systems or calendars
- complex multi-step authorization
- flows with many edge cases and exceptions
- bots that collect multiple variables in one turn
- advanced JavaScript-based data processing
- voice-like assistants with natural preference collection
- hybrid logic that combines deterministic flow design with LLM support

### Project profile
- **Language:** Polish
- **Bot type:** Transactional bot
- **Multi-language:** No
- **LLM blocks:** Yes
- **RAG:** Yes
- **Authorization:** Yes
- **Tests:** Yes
- **Integrations:** Yes
- **Voice-like patterns:** Yes
- **Best suited for:** Both small changes and large structures

### Main flow areas
- Booking appointments through calendar integration
- Handling many operational edge cases
- Complex JavaScript logic and data transformation
- Detecting multi-intent user input
- Collecting and normalizing visit date preferences
- Collecting visit type preferences
- Collecting doctor preferences
- Routing based on structured booking logic and recognized user needs

### Reusable patterns

#### Context structure patterns
- **Preference collection split across dedicated contexts** — doctor preference, date preference, and visit type are each collected in their own context; they are not merged into one large state machine
- **User preference stored separately from selected result** — what the user expressed (e.g. "Tuesday morning") is stored in a different memory path from the normalized slot that was actually selected; this allows re-asking without losing the original preference
- **API orchestration in a dedicated context** — slot search and booking API calls are isolated in API contexts; the business flow context never calls integrations directly
- **Token retrieval as a standalone reusable context** — authorization token fetch is a separate context called by any other context that needs it, never duplicated inline

#### Path patterns
- **Multi-step preference gathering before availability check** — all preferences are collected first, then a single API call checks availability; the flow does not interleave collection and API calls
- **Availability branch with negotiation loop** — if no slot matches the preference, a negotiation loop offers alternatives with a counter controlling how many times alternatives can be proposed before escalating
- **Edge case paths below the main path** — no available slots, authorization failure, and API errors are handled as downward branches from the main path, each with its own ending state
- **Background passive detection** — a `llm-integration` block passively detects if the user has expressed a new date preference during an unrelated turn, without interrupting the main flow

#### Mechanism patterns
- **LLM for date preference interpretation** — a narrow `llm-integration` block interprets natural language date expressions (e.g. "next week, preferably morning") into a structured object stored in memory; routing is deterministic after that
- **LLM for confirmation classification** — a narrow `llm-integration` block classifies user responses as confirmation or rejection; all downstream routing is deterministic based on the stored classification result
- **LLM for natural slot proposal wording** — a `say-llm` block words the appointment proposal naturally; the slot data is passed in as context, not generated by the model
- **JavaScript for slot ranking and filtering** — `custom` blocks use JavaScript to filter API results, rank slots by preference match, and compose the payload for the booking call; AEL is used only for simple assignments

#### Memory patterns
- **`memory.response.*` for raw API output** — raw API responses are always stored under `memory.response.*` before normalization
- **Separate normalized business objects** — filtered and ranked slots are stored under a distinct memory path, never mixed with the raw API response
- **Counters for loop control** — fallback counter, silence counter, negotiation counter, and agent request counter are stored as individual memory keys and incremented in `custom` blocks

---

## Reference: Finance Bot

### Summary
A Polish-language transactional bot built in SentiOne Automate. This project is designed for financial service processes and combines structured transactional logic with LLM-supported response formatting, authorization, external integrations, and voice-like interaction patterns. It is a strong reference for bots that handle debt-related conversations, customer negotiation flows, case intake, and operational ticket creation.

### Recommended use
Use this reference when working on:
- transactional financial bots
- debt handling and repayment-related flows
- customer verification and authorization
- negotiation processes
- bots that format user responses with LLM support
- case intake and issue reporting
- Jira-based service workflows
- Google Sheets integrations
- voice-like assistants with structured business logic
- bots that combine deterministic process handling with selected AI-supported steps

### Project profile
- **Language:** Polish
- **Bot type:** Transactional
- **Multi-language:** No
- **LLM blocks:** Yes
- **RAG:** No
- **Authorization:** Yes
- **Tests:** Yes
- **Integrations:** Yes
- **Voice-like patterns:** Yes
- **Best suited for:** Both small changes and large structures

### Main flow areas
- Client verification
- Error handling
- Global listener
- Global fallback
- NPS
- Formatting user responses via ChatGPT
- Retrieving data from an external database, Google Sheets
- Updating an external database, Google Sheets
- Creating Jira issues
- Negotiating a new installment amount with the customer
- Informing the customer about debt details
- Receiving customer requests and creating Jira tickets

### Reusable patterns

#### Context structure patterns
- **Verification context as a hard gate** — client identity verification runs in a dedicated context at the start of the flow; no business context is entered until verification succeeds
- **Debt information context as a read-only display flow** — retrieving and presenting debt details is a self-contained context that reads from memory and presents data without modifying any external state
- **Negotiation as a stateful looping context** — installment negotiation runs as its own context with internal counters controlling offer rounds; it returns a negotiation outcome to the calling context via memory
- **Case intake context for unstructured requests** — free-form customer requests are collected, LLM-formatted, and submitted as Jira tickets inside a dedicated intake context

#### Path patterns
- **Verification failure as an early terminal path** — if verification fails after a defined number of attempts, the flow exits to a terminal state without entering any business context
- **Debt detail path before negotiation** — the bot always presents the current debt situation before entering negotiation; the negotiation context is never entered without the customer having seen their debt details first
- **Negotiation outcome branch** — after negotiation ends, the flow branches on outcome: accepted proposal, rejected proposal, and max rounds reached are handled as separate paths with distinct endings
- **Jira creation as a post-process step** — ticket creation happens after the main business transaction is confirmed, not during; it is a separate concluding context called before NPS

#### Mechanism patterns
- **LLM for response formatting only** — LLM blocks are used exclusively to reword or format structured data (e.g. debt summary, proposed installment) into natural language; they never make business decisions
- **Google Sheets as the customer data source** — customer record retrieval and update are isolated in API contexts; the main flow reads only from memory after the API context completes
- **Negotiation counter controlling offer depth** — a counter in memory tracks how many installment proposals have been made; routing logic reads the counter to decide whether to make another offer or escalate
- **`conversationMetadata` at negotiation milestones** — key negotiation events (offer made, offer accepted, offer rejected, max rounds reached) are pushed into metadata for analytics and post-call review

#### Memory patterns
- **Customer record stored as a structured object** — all fields retrieved from Google Sheets (debt amount, due date, case ID, etc.) are stored under one memory path as a composed object after the API context returns
- **Negotiation state isolated in dedicated keys** — current proposed amount, round counter, and final outcome are stored as separate memory keys so the negotiation context can be inspected independently of the customer record
- **LLM formatting input and output stored separately** — the structured data passed to the LLM formatter and the formatted response returned by it are stored under distinct memory paths, allowing the structured data to be reused if reformatting is needed
