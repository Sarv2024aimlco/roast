# ROAST Codebase Study Guide

This document is meant for studying the repo, not just browsing it.

The goal is:

1. Start from the product flow, so the code feels intuitive.
2. Then zoom into each folder.
3. Then zoom into each file.
4. Then walk top-to-bottom through the important functions and code blocks so you understand why each piece exists.

This is not a copy-paste dump of source files. It is a guided reading of the repo.

---

## 1. What This Repo Is

ROAST is a resume analysis product with three major layers:

1. A FastAPI backend that accepts a PDF resume, creates a session, runs multiple analysis agents, stores intermediate state in Redis, and streams results.
2. A React frontend that collects user inputs, uploads the resume, watches progress over WebSocket, and renders the final review.
3. An ingestion and retrieval system that builds a market-intelligence corpus in SQLite so the app can compare a resume against live hiring signals instead of giving generic advice.

If you keep only one mental model in mind, keep this one:

`resume PDF -> extract text -> retrieve market signals -> run agent pipeline -> stream sections -> show final review`

---

## 2. How To Study This Repo

The cleanest order is:

1. Read the top-level files.
2. Read backend entrypoints.
3. Read the analysis pipeline.
4. Read the agent contracts and prompts.
5. Read storage and retrieval.
6. Read the frontend flow.
7. Read ingestion.
8. Read tests last, because they tell you what the author expected, even where the code drifted.

If you start from individual utility files first, the repo will feel fragmented. If you start from the main request flow, almost everything else becomes obvious.

---

## 3. Top-Level Folder Map

### `backend/`

The live application server. This is the heart of the product.

It contains:

- API routes
- session handling
- PDF parsing
- LLM provider clients
- analysis agents
- orchestration logic
- retrieval logic
- Redis-backed state

### `frontend/`

The browser app.

It contains:

- the landing/upload UI
- the progress screen
- the results screen
- helper hooks for WebSocket state and local UI preferences

### `ingestion/`

The offline market-data builder.

It contains:

- SQLite schema and search
- Tavily search clients
- web-content extraction
- embeddings
- Levels.fyi scraping
- the bulk ingestion pipeline

### `scripts/`

Operator scripts for preparing and maintaining the data layer.

### `tests/`

Basic tests and manual verification scripts for backend behavior.

### `.idea/`, `.vscode/`

Editor/project metadata. Useful for understanding local dev setup, but not part of application logic.

### `.venv/`, `frontend/node_modules/`, `frontend/dist/`, `.pytest_cache/`

Generated or vendored artifacts.

These are in the repo state you have locally, but they are not the handwritten application logic you should learn first.

### `.git/`

Git internals. Not app logic.

---

## 4. Top-Level Files

### `README.md`

This is the product-facing overview.

It explains:

- what ROAST claims to do
- the intended architecture
- the agent lineup
- the ingestion idea
- the stack

Important study note:

Treat this as the design intent, not the final source of truth. The actual code has drift in some places, so the implementation files matter more.

### `pyproject.toml`

This defines the Python project:

- project name: `roast`
- Python version floor: `>=3.12`
- dependencies for FastAPI, Redis, Groq, Gemini, PDF reading, tracing, search, and utilities

Study value:

This file tells you what the backend relies on conceptually:

- `fastapi[standard]` means async web server
- `pymupdf` means PDF parsing
- `upstash-redis` means cloud Redis usage
- `groq`, `google-genai`, `langfuse` show the LLM and observability story

### `uv.lock`

This is the exact Python dependency lockfile.

Study value:

Not useful for learning logic line by line, but useful for reproducibility and knowing this repo is managed with `uv`.

### `Dockerfile`

This explains the deployment shape.

Top-to-bottom flow:

1. Build the frontend with Node in stage 1.
2. Build the Python runtime in stage 2.
3. Install system libraries needed for PyMuPDF.
4. Install `uv`.
5. Sync Python dependencies from `pyproject.toml` and `uv.lock`.
6. Copy backend, ingestion, scripts, and the SQLite DB.
7. Copy built frontend assets from stage 1.
8. Run `uvicorn backend.main:app`.

The key idea is that deployment serves:

- API routes from FastAPI
- static frontend files from `frontend/dist`

### `.env.example`

This is the configuration template.

It shows every environment variable the app expects:

- app env and CORS
- LLM provider keys
- Tavily keys
- Redis
- QStash
- Resend
- Langfuse
- optional Discord notifications

Use this file to understand the system boundaries. Every external integration is visible here.

### `.env`

This is the local real config file.

For study, the important fact is not the values but the fact that this repo is wired for:

- multiple LLM providers
- multiple Tavily keys
- Redis
- cron/webhook auth
- email token unlocks
- tracing

### `.gitignore`

This reveals what the repo considers generated or secret.

Interesting detail:

The comment says the SQLite DB is intentionally tracked because it contains pre-populated market signals.

### `.python-version`

Pins local Python to `3.12`.

### `roastv2.txt`

A large text artifact in the root. It is not part of the runtime code path. Treat it as a side artifact, not a core application module.

### `test_pdf.txt`

This is a plaintext extracted-resume sample. It helps you see what the PDF parser is expected to produce after cleaning.

---

## 5. The Full Runtime Flow

Before reading folders individually, understand the live app flow from first click to final result.

### Step 1: Frontend starts on `App`

The browser loads `frontend/src/main.jsx`, which renders `App`.

`App` decides whether the user is on:

- the landing page
- the analysis/progress view
- the results view

### Step 2: User creates or reuses a session

The landing page calls `/api/session-init`.

This creates a Redis-backed session with:

- role
- market
- company type
- experience level
- created timestamp
- status

### Step 3: User uploads a PDF

The frontend submits a multipart form to `/api/analyse`.

The backend:

1. checks the session
2. blocks suspiciously fast requests
3. checks daily rate limit
4. validates that the file is a PDF
5. writes it to a temp file
6. extracts text
7. extracts annotation-layer links like LinkedIn/GitHub
8. stores session state
9. launches the analysis pipeline as a background task

### Step 4: Backend pipeline runs

The orchestrator does:

1. optional JD parsing
2. DIVE retrieval from SQLite and breaking-signal overlay
3. MarketContextAgent first
4. RedFlagAgent, SixSecondAgent, CompetitiveAgent, TechnicalDepthAgent in parallel
5. ReviewAgent last
6. Redis section storage and WebSocket section streaming
7. optional anonymised corpus storage
8. optional bullet-candidate curation

### Step 5: Frontend watches progress

The frontend opens `/api/ws/{session_id}`.

As each section completes, the backend emits `section_complete` events.

If the socket dies, the frontend falls back to polling `/api/session/{session_id}/state`.

### Step 6: Results render

The frontend composes:

- bottom-line verdict
- market pulse
- full review sections
- percentile/CTC card
- follow-up questions
- feedback and token-unlock UI

That is the whole product.

Everything else in the repo exists to support one part of that flow.

---

## 6. `backend/` Folder

This folder is the live server.

Read it in this order:

1. `config.py`
2. `main.py`
3. `pdf_reader.py`
4. `routes/`
5. `pipeline/orchestrator.py`
6. `agents/`
7. `llm/`
8. `retrieval/`
9. `storage/`
10. `corpus/`

---

## 7. `backend/config.py`

This file loads environment variables and converts them into module-level constants.

### Flow

1. `load_dotenv()` loads `.env`.
2. `get_required_key()` centralizes "this env var must exist".
3. `get_optional_key()` centralizes optional config reads.
4. The rest of the file assigns constants in topic blocks:
   - app
   - LLM providers
   - search/scraping
   - storage
   - scheduling
   - security
   - CORS
   - observability
   - PDF limits

### Functions

#### `get_required_key(key: str) -> str`

Purpose:

Read an env var and fail fast if missing.

Why it exists:

Without this, the app would fail later and more confusingly when a provider client tries to use a missing key.

#### `get_optional_key(key: str, default=None)`

Purpose:

Read env vars that are allowed to be missing.

### Important constants

- `ENVIRONMENT`
- `GROQ_API_KEYS`
- `GEMINI_API_KEYS`
- `TAVILY_API_KEY_DEEP`
- `TAVILY_API_KEY_GENERAL`
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`
- `HMAC_SECRET`
- `ALLOWED_ORIGINS`
- `LANGFUSE_*`
- `MAX_FILE_SIZE_MB`
- `MAX_PAGES`
- `MIN_CHARS`
- `MAX_CHARS`

Study insight:

This file defines the app's trust boundaries and deployment assumptions.

---

## 8. `backend/main.py`

This is the application entrypoint for FastAPI.

### Top-to-bottom reading

1. Import FastAPI and middleware/static helpers.
2. Import routers.
3. Build the FastAPI app object.
4. Attach CORS middleware.
5. register routers.
6. define `/health`
7. define `/robots.txt`
8. if frontend `dist` exists, mount static assets and serve SPA fallback

### Functions

#### `health_check()`

Purpose:

Returns:

- service status
- app name
- total analysis count from Redis

Why it matters:

The frontend visitor badge uses this.

#### `robots()`

Purpose:

Return a simple robots file that blocks `/api/`.

### SPA serving behavior

The bottom block is important.

If `frontend/dist` exists:

- `/assets` serves compiled frontend assets
- `/favicon.svg` serves favicon
- every non-API path returns `frontend/dist/index.html`

That means this backend can serve the frontend directly in production.

---

## 9. `backend/pdf_reader.py`

This file is the input sanitation layer for resumes.

The whole app depends on this file doing three jobs well:

1. clean extracted text
2. validate the resume shape
3. extract hidden links from PDF annotations

### Functions

#### `clean_text(raw: str) -> str`

Flow:

1. split text into lines
2. strip each line
3. join lines again
4. collapse 3+ blank lines to 2
5. trim final output

Why:

Raw PDF text extraction is messy. This normalizes it before the agents see it.

#### `is_valid_resume_text(text: str) -> tuple[bool, str]`

Checks the extracted text against `MIN_CHARS` and `MAX_CHARS`.

Why:

- too little text often means image/scanned PDF
- too much text often means CV, not resume

#### `extract_links(pdf_path: str) -> dict`

This is one of the smarter parts of the file.

It does not rely on visible text to find URLs.

Instead it:

1. opens the PDF with `fitz`
2. checks encryption
3. iterates pages
4. reads annotation-layer links via `page.get_links()`
5. filters out empty URIs and `mailto:`
6. records:
   - all URLs
   - first LinkedIn URL
   - first GitHub URL

Why:

Many resumes show clickable icons but not the raw URL in text. This captures those links correctly.

#### `verify_link(url: str, timeout: int = 5) -> dict`

Sends a HEAD request and records:

- reachable
- status code
- error text

The intent is to cheaply validate external profile links.

#### `extract_text_from_pdf(pdf_path: str) -> dict`

This is the main pipeline:

1. check file size
2. open PDF
3. check page count
4. extract page text
5. clean each page
6. collect per-page metadata
7. join full text
8. validate text size
9. return structured result

This function shapes the data the entire analysis pipeline depends on.

---

## 10. `backend/storage/`

This folder is about Redis-backed persistence.

### `redis_client.py`

Tiny file.

It just does:

1. `load_dotenv()`
2. `Redis.from_env()`

This becomes the shared Redis client used almost everywhere else.

### `session_store.py`

This is simple session CRUD over Redis.

#### `create_session(...)`

Flow:

1. generate UUID
2. build session dict
3. set Redis key `session:{id}` with TTL
4. return the session dict

The stored session includes:

- user calibration inputs
- creation time
- current status

#### `get_session(session_id)`

Reads Redis key and JSON-decodes it.

#### `update_session(session_id, updates)`

Reads existing session, merges updates, writes it back with fresh TTL.

### `rate_limit.py`

This file enforces free daily analysis limits.

#### `_seconds_until_midnight_ist()`

Computes TTL until the next midnight in India time.

Why:

The daily limit resets at IST midnight, not server UTC midnight.

#### `check_and_increment_rate_limit(ip: str)`

Flow:

1. `INCR` the per-IP Redis key
2. if first request, set TTL to midnight IST
3. compare against `FREE_ANALYSES_PER_DAY`
4. if over limit, undo increment
5. return allowed/count/remaining/limit

#### `get_rate_limit_status(ip: str)`

Read-only version for status checks.

---

## 11. `backend/routes/`

This folder contains the HTTP and WebSocket surface of the backend.

Read these as the public API of the system.

### `session.py`

Handles session creation and retrieval.

#### Models

- `SessionInitRequest`
- `SessionInitResponse`

These define the shape of incoming/outgoing JSON.

#### `session_init(body)`

Calls `create_session()` and returns the ID plus a human message.

#### `get_session_route(session_id)`

Fetches the session or returns 404.

### `analyse.py`

This is the main entrypoint for the actual product.

#### `_run_pipeline_and_stream(...)`

Background task wrapper around the orchestrator.

It:

1. builds a `PipelineRequest`
2. awaits `run_pipeline`
3. emits `complete` on success
4. marks session failed and emits `error` on failure

#### `analyse(...)`

This is the most important route in the app.

Read it as a guarded funnel:

1. validate session exists
2. stop duplicate processing
3. apply timing gate against bots
4. apply rate limit
5. validate PDF MIME type
6. save upload to temp file
7. extract text and links
8. reject invalid PDFs
9. update session with extracted data
10. prepare profile links
11. launch background analysis task
12. return immediately with processing status

This route is intentionally short on heavy analysis logic. It delegates the hard work to the orchestrator.

### `websocket.py`

This handles real-time status streaming and recovery.

#### `websocket_endpoint(websocket, session_id)`

Flow:

1. accept socket via ws manager
2. start heartbeat loop
3. immediately replay already-completed sections
4. keep the socket alive
5. react to pongs and timeouts
6. disconnect cleanly on close

This is what makes reconnecting safe. A client does not lose progress if it reconnects mid-analysis.

#### `session_state(session_id)`

Polling fallback endpoint.

Returns:

- current status
- completed sections
- pending sections
- cached results

#### `share_preview(session_id)`

Public-safe TL;DR preview route.

It deliberately exposes only a small subset of the final review.

#### `_get_completed_sections(session_id)`

Reads Redis section keys and JSON-decodes them.

### `ws_manager.py`

Small connection manager.

#### `connect(session_id, websocket)`

Accepts and stores socket by session ID.

#### `disconnect(session_id)`

Removes it from the active mapping.

#### `emit(session_id, event, data)`

Central send helper used by the pipeline.

If the client is gone, it silently does nothing.

#### `heartbeat_loop(session_id, interval=10)`

Sends `ping` messages periodically so slow jobs do not look dead.

### `followup.py`

This is for post-review follow-up questions.

#### `FollowUpRequest`

Carries:

- session ID
- section name
- clicked question

#### `followup(body)`

Flow:

1. validate session exists
2. enforce one follow-up per section
3. read resume and context from session
4. fetch stored review section from Redis if available
5. mark follow-up as used before execution
6. run follow-up agent
7. return answer

The "mark before run" detail is important. It prevents double-click race conditions.

### `token_feedback.py`

This file contains two independent features:

1. token unlocks for an extra free analysis
2. useful/not useful feedback

#### `TokenRequest`

Carries email.

#### `TokenVerifyRequest`

Carries token and session ID.

#### `request_token(body)`

Flow:

1. normalize and validate email
2. block multiple sends per email per day
3. generate UUID token
4. store token and email flags in Redis
5. if no Resend key, return dev token directly
6. otherwise email token
7. clean up if email send fails

#### `verify_token(body)`

Flow:

1. validate token exists
2. delete token immediately
3. create `token_unlocked:{session_id}` Redis flag
4. return success

This does not directly modify the rate-limit key. Instead it grants one bypass flag checked by `/analyse`.

#### `_send_token_email(email, token)`

Resend integration wrapper.

#### `FeedbackRequest`

Carries session and combo metadata.

#### `feedback(body)`

Flow:

1. increment useful/not-useful counters
2. increment combo-specific counters
3. try to send score to Langfuse
4. log and return thank-you

### `cron.py`

This is the scheduled market-refresh endpoint.

Conceptually it does four things:

1. verify QStash signature
2. decide which role/company/market combos are "active"
3. refresh ingestion for those combos
4. optionally notify Discord

#### `_verify_qstash_signature(body, signature)`

HMAC check.

In development, verification is skipped if the signing key is missing.

#### `_get_active_combinations()`

Builds the refresh set from:

- a hardcoded Tier 1 list
- plus any combo with enough real analysis volume in Redis

This is how the app slowly learns which combinations deserve maintenance.

#### `refresh_market_intel(request)`

This is the actual cron route.

It validates request authenticity, loops through combinations, refreshes ingestion, and returns summary output.

#### `_notify_discord(message)`

Utility for operational alerting.

---

## 12. `backend/pipeline/orchestrator.py`

This is the single most important file in the backend.

If you understand this file, you understand the product.

### High-level responsibility

It coordinates:

- retrieval
- agent execution order
- parallelism
- Redis section storage
- streaming events
- post-processing

### Helper: `_emit(session_id, event, data)`

Lazy imports the ws manager and forwards events.

Why lazy:

Avoid circular imports between routes and pipeline.

### Data models

#### `PipelineRequest`

Everything needed for one analysis run:

- session ID
- resume text
- calibration fields
- optional JD text
- profile links
- corpus opt-in

#### `PipelineResult`

Structured return value containing every major section and runtime duration.

### Semaphores

This file declares shared concurrency limits:

- `_groq_sem`
- `_gemini_sem`
- `_global_sem`
- `_tech_depth_sem`

These protect external provider budgets and stop the service from stampeding itself.

### `run_pipeline(request)`

Wrapper that enforces global concurrency by entering `_global_sem`, then calling `_run_pipeline_inner`.

### `_run_pipeline_inner(request)`

Read this function in stages.

#### Stage 0: initialize

- record start time
- log pipeline start
- mark session as `in_progress`

#### Stage 1: optional JD parsing

If JD text exists and is long enough:

- mark step as `parsing_jd`
- call `parse_jd`

This produces structured job requirements used later by some agents.

#### Stage 2: DIVE retrieval

- mark step as `fetching_market_intel`
- call `run_dive`
- convert distilled context into text form for the first agent

This is where the market-aware nature of the app begins.

#### Stage 3: MarketContextAgent

- mark step as `market_context_agent`
- run market-context agent under Groq semaphore
- store `market_context`
- emit `section_complete`
- also store and emit simplified `market_intel`

Important design choice:

This agent runs alone first because downstream agents depend on its calibration.

#### Stage 4: parallel agents

- mark step as `parallel_agents`
- prepare profile links
- run:
  - red flag agent
  - six second agent
  - competitive agent
  - technical depth agent

These run with different concurrency rules depending on provider risk.

#### Stage 5: graceful fallback handling

`asyncio.gather(..., return_exceptions=True)` is used so one failed agent does not kill the whole analysis.

Each failed agent gets converted into a safe fallback output object.

This is a strong reliability choice:

the product prefers degraded output over total failure.

#### Stage 6: store parallel results

Each result is:

- stored in Redis
- emitted to the client

This is why the frontend can show sections as they complete.

#### Stage 7: ReviewAgent

- mark step as `review_agent`
- run the final synthesis agent
- store review
- emit review section

This is the prose-writing phase that turns structured partial analyses into the user-facing roast.

#### Stage 8: finalize session

- mark session completed
- store duration
- increment total analysis counter
- increment combo counter

#### Stage 9: post-pipeline extras

If corpus opt-in is enabled:

- build anonymised signal
- store it in Redis corpus

Then always try:

- bullet candidate extraction
- bullet curation queue storage

This stage never blocks the main user flow.

### Small helpers

#### `_run_with_groq_sem(coro)`

Wrap a coroutine under Groq semaphore.

#### `_run_with_tech_depth_sem(coro)`

Wrap under technical-depth semaphore.

#### `_run_with_gemini_sem(coro)`

Defined for symmetry, though not central in this flow.

#### `_format_distilled_context(ctx)`

Turns structured DIVE output into human-readable text for prompt input.

#### `_store_section(session_id, section, data)`

Central Redis write helper for streamable sections.

---

## 13. `backend/retrieval/dive.py`

This file is the retrieval brain.

The acronym is:

`Deterministic Intelligence Vector Extraction`

Its job is to turn:

`role + company_type + market + experience_level`

into:

`distilled market context + breaking signal`

### Output models

#### `DistilledMarketContext`

Contains:

- hiring sentiment
- top skills
- pool description
- salary band
- red flag triggers
- format expectations
- weight map
- confidence
- freshness label

#### `FullMarketContext`

Wraps:

- distilled context
- breaking signal text
- whether breaking signal exists
- raw signal count

### Retrieval pipeline functions

#### `_build_retrieval_queries(...)`

Expands one structured combo into six different query intents.

Why:

Different downstream needs require different retrieval angles:

- sentiment
- skills
- applicant pool
- expectations
- red flags
- salary/format

#### `_parallel_search(...)`

Runs:

- BM25 full-text retrieval
- embedding similarity retrieval

in parallel.

Important idea:

The repo is deliberately hybrid retrieval, not just keyword search or just vector search.

#### `_rrf_fusion(...)`

Combines BM25 and vector rankings via reciprocal-rank fusion.

Why:

Documents that rank reasonably well in both systems get promoted.

#### `_hash_dedup(results, limit=15)`

Hashes the first 200 chars of content and removes near-duplicates.

Why:

Search results often repeat the same signal from different queries.

#### `_distill_context(...)`

Takes top signals, formats them into a prompt, calls `call_groq_8b`, parses JSON, and returns `DistilledMarketContext`.

This is the compression step:

many raw snippets become one structured market summary.

#### `_get_freshness_label(signals)`

Maps signal age to:

- `Current`
- `Recent`
- `Needs Refresh`

### Breaking-signal helpers

These functions build and fetch a short-term hiring-news overlay.

- `_breaking_signal_key`
- `_role_to_category`
- `_get_breaking_signal`
- `_get_breaking_signal_with_fetch`

The app treats long-lived market context and short-lived breaking news as separate layers.

### Snapshot-cache helpers

- `_snapshot_key`
- `_snapshot_prev_key`
- `_get_cached_snapshot`
- `_cache_snapshot`

This is the Redis caching layer over distilled retrieval results.

### `run_dive(...)`

This is the public entrypoint.

Flow:

1. check Redis snapshot cache
2. if hit, fetch breaking signal and return
3. if no SQLite data exists, return low-confidence baseline
4. otherwise:
   - build queries
   - run hybrid search
   - fuse results
   - dedup
   - distill
   - cache distilled result
   - fetch breaking signal
   - return full context

This file is what makes ROAST not just "upload resume to LLM".

---

## 14. `backend/agents/`

This folder contains the structured reasoning stages of the product.

The clean reading order is:

1. `schemas.py`
2. `json_utils.py`
3. `prompts/`
4. each agent implementation
5. `followup_agent.py`
6. `tech_search.py`

### `schemas.py`

This is the contract file for agent outputs.

Read it first because every other agent file makes more sense once you know the schema.

#### Models

- `JDRequirements`
- `MarketContextOutput`
- `GapSignal`
- `SixSecondAndTrajectoryOutput`
- `RedFlag`
- `RedFlagOutput`
- `PercentileEstimate`
- `CompetitiveOutput`
- `ReviewOutput`
- `FollowUpOutput`

These models do three jobs:

1. document expected structure
2. validate parsed LLM JSON
3. make downstream orchestration safer

### `json_utils.py`

#### `extract_json(text)`

This is a defensive parser for messy model output.

It handles:

- `<think>` blocks
- fenced code blocks
- extra prose around JSON
- malformed JSON repair through `json-repair`

This utility is essential because the entire agent architecture assumes "LLM returns parseable JSON", which is never perfectly reliable.

### `tech_search.py`

This is a real-time niche-tech lookup helper.

#### `lookup_technology(tech_name, context="")`

Searches DuckDuckGo and returns a short combined snippet.

#### `_ddg_search(query)`

Synchronous DDGS wrapper used inside a thread.

#### `lookup_multiple(technologies, context="")`

Parallel multi-search convenience function.

This file exists mainly to support the technical-depth agent.

### `market_context_agent.py`

This file has two distinct roles:

1. parse a JD if provided
2. interpret distilled market data into weightings and norms

#### `parse_jd(jd_text, session_id="")`

Flow:

1. reject tiny JD strings
2. build parser prompt
3. call `call_groq_8b`
4. parse JSON
5. validate into `JDRequirements`
6. return `None` on failure

#### `run_market_context_agent(...)`

Flow:

1. choose active prompt version
2. build system prompt from shared template
3. optionally attach JD requirements
4. send market-intel text plus user context
5. parse JSON
6. coerce weird model output shapes into safe defaults
7. return validated `MarketContextOutput`
8. if anything fails, return a LOW-confidence fallback object

This is the "calibration" layer of the system.

### `red_flag_agent.py`

This agent hunts for liabilities.

#### `_passes_quality_gate(flag)`

Rejects weak flags by checking:

- location length
- fix length
- inference-chain length
- generic banned phrase count

This is important because low-quality red flags would make the product feel shallow and templated.

#### `run_red_flag_agent(...)`

Flow:

1. build system prompt
2. attach JD rules if present
3. attach profile links if present
4. build a resume-plus-market trigger prompt
5. call primary red-flag model path
6. if primary fails, fall back
7. parse JSON
8. validate `RedFlag` items
9. run quality gate
10. return filtered output

Design insight:

This file is trying hard to force concrete recruiter inference chains, not vague advice.

### `six_second_agent.py`

This agent simulates recruiter first-impression plus trajectory reading.

#### `run_six_second_trajectory_agent(...)`

Flow:

1. build system prompt
2. extract first 200 words for the scan simulation
3. include full resume and optional profile links
4. call model
5. parse JSON
6. validate `GapSignal` objects
7. coerce missing optional strings
8. return structured output

This separates:

- what jumps out instantly
- what the full resume story says after a deeper read

### `competitive_agent.py`

This agent estimates relative standing in the applicant pool.

#### `run_competitive_agent(...)`

Flow:

1. build prompt
2. optionally include corpus signals if enough exist
3. optionally include JD requirements
4. call model
5. parse JSON
6. fill required defaults if model omitted fields
7. force percentile estimate to exist
8. normalize confidence to `estimated` or `calibrated`
9. return `CompetitiveOutput`
10. on failure, return fallback output

This file is where product claims like percentile and expected CTC are assembled.

### `technical_depth_agent.py`

This is the most agentic file.

Its job is not just to summarize projects but to judge what they genuinely prove.

#### Output models

- `ProjectEvaluation`
- `TechnicalDepthOutput`

#### `_should_skip_search(query)`

Rejects searches for concepts the model should already know.

Why:

This avoids wasting tool calls on mainstream technologies.

#### `_parse_output(data)`

Validates project-evaluation objects and assembles `TechnicalDepthOutput`.

#### `_run_agentic_loop(client, messages, session_id)`

This is the core tool-calling loop.

Flow:

1. call Groq model with tool definition
2. inspect returned tool calls
3. if no tool call, parse final JSON and return
4. if tool calls exist:
   - parse arguments
   - skip low-value searches
   - run DuckDuckGo lookup for niche items
   - append tool results back into the conversation
5. stop after max tool calls
6. force a final no-tool answer if needed

This is the closest thing in the repo to an autonomous agent loop.

#### `run_technical_depth_agent(...)`

Builds prompt context and runs the agentic loop under timeout protection.

#### `_fallback_evaluation(...)`

If the agentic path fails or times out, do a simpler no-tool evaluation with `llama-3.1-8b-instant`.

This reliability fallback is important because technical-depth is useful, but the product must not die if tool use gets messy.

### `review_agent.py`

This is the final writer.

It converts structured upstream outputs into the polished user-facing review.

#### `_count_words(review)`

Counts words across prose sections.

#### `_passes_quality_gate(review)`

Ensures:

- total length is reasonable
- follow-up question lists are present

#### `_build_upstream_summary(...)`

This function matters a lot.

It is deterministic Python, not LLM logic.

Its purpose is to assemble all upstream results into one compact structured summary for the ReviewAgent to consume.

Important design choice:

technical-depth output leads the summary, then recruiter-style views support it.

#### `run_review_agent(...)`

Flow:

1. build system prompt
2. build upstream summary
3. send resume text plus upstream analysis to model router
4. parse and repair JSON
5. ensure required fields exist
6. coerce list/string mismatches
7. validate into `ReviewOutput`
8. run quality gate
9. if quality fails on first attempt, ask for rewrite
10. if all attempts fail, fall back to partial review assembly

This is the user-facing "voice" of the product.

#### `_assemble_partial_review(...)`

Last-resort manual fallback built from upstream structured outputs.

### `followup_agent.py`

This powers the clickable follow-up questions in the frontend.

#### `_followup_key(...)`

Builds Redis key.

#### `has_used_followup(...)`

Checks if a follow-up has already been consumed for a section.

#### `mark_followup_used(...)`

Marks it as used with TTL.

#### `run_followup_agent(...)`

Builds a short focused prompt from:

- resume summary
- review summary
- clicked question

Then returns a short prose answer.

### `prompts/`

This folder contains versioned prompt text.

Treat prompt files as configuration, not control flow.

#### `template.py`

This is the shared prompt-construction layer.

##### `get_role_calibration(role, company_type)`

This is one of the most product-important functions in the whole repo.

Why:

It prevents the agents from applying generic software-engineering expectations to every role.

It contains domain calibrations for:

- SDE
- AI/ML
- Data Scientist
- Data Engineer
- Data Analyst
- Embedded
- VLSI
- DevOps/SRE
- Product Manager
- Business Analyst

This is how the app avoids nonsense like asking embedded candidates for React deployment evidence.

##### `get_city_hint(market, company_type)`

Adds market-level interpretation, especially for India role/company patterns.

##### `build_system_prompt(...)`

This composes:

- app context
- role context
- city/market hint
- universal anti-prompt-injection constraints
- agent-specific task and output rules

This function is the common shell around every agent prompt.

#### `market_context_prompt.py`

Defines the MarketContextAgent task and output expectations.

#### `red_flag_prompt.py`

Defines red-flag categories, recruiter inference-chain format, banned phrases, and role-specific exceptions.

#### `six_second_prompt.py`

Defines the two-part scan-plus-trajectory output.

#### `competitive_prompt.py`

Defines percentile and salary expectations, especially same-experience-level calibration.

#### `review_prompt.py`

Defines the long-form review style, structure, and quality expectations.

#### `follow_up_prompt.py`

Defines short, direct answers for clicked follow-up questions.

---

## 15. `backend/llm/`

This folder abstracts provider behavior.

The key design pattern is:

- individual provider clients handle provider-specific quirks
- `router.py` decides fallback chains
- `circuit_breaker.py` provides resilience
- `langfuse_client.py` provides tracing

### `circuit_breaker.py`

#### `CircuitBreaker`

Tracks:

- failure count
- last failure time
- state: `closed`, `open`, `half_open`

Methods:

- `record_failure()`
- `record_success()`
- `should_skip()`

The point is to stop repeatedly slamming a broken provider.

Module-level singletons:

- `groq_circuit`
- `gemini_circuit`
- `cerebras_circuit`
- `openrouter_circuit`
- `nim_circuit`

### `groq_client.py`

This is the richest provider client.

It handles:

- multiple API keys
- round-robin selection
- daily request budget tracking in Redis
- rate-limit retries
- proactive logging when RPM gets low
- optional Langfuse tracing

#### `_get_client()`

Selects a key round-robin and returns `(client, index)`.

#### `_rotate(current_idx)`

Move to next key after rate limit.

#### `_rpd_key(model, key_index)`

Redis key builder for daily request tracking.

#### `_check_rpd(model)`

Checks whether any key still has daily budget for a model.

#### `_increment_rpd(model, key_idx=0)`

Updates the per-model per-key daily count and sets TTL to midnight UTC.

#### `groq_chat(...)`

The main Groq wrapper.

Flow:

1. circuit-breaker gate
2. RPD gate
3. choose key
4. call provider
5. strip `</think>` artifacts if necessary
6. increment RPD
7. inspect RPM remaining header if available
8. record success
9. build metadata
10. optionally trace to Langfuse
11. retry/rotate on 429

This function is a good example of pragmatic production wrapping around a simple API.

### `gemini_client.py`

Similar idea, simpler implementation.

Key behaviors:

- key rotation
- circuit breaker
- no-thinking generation config

Functions:

- `_get_client()`
- `_rotate()`
- `gemini_chat(...)`

### `cerebras_client.py`

Single-provider wrapper around Cerebras chat endpoint.

Main function:

- `cerebras_chat(...)`

### `nvidia_nim_client.py`

Single-provider wrapper for NVIDIA NIM.

Main function:

- `nim_chat(...)`

### `openrouter_client.py`

Last-resort provider wrapper.

Main function:

- `openrouter_chat(...)`

### `langfuse_client.py`

Observability wrapper.

#### `_init()`

Lazy initialization of Langfuse client.

#### `trace_llm_call(...)`

Creates a generation observation with:

- system/user snippets
- output text
- model/provider metadata
- token usage
- latency

#### `trace_feedback(session_id, useful)`

Sends feedback score.

### `router.py`

This file expresses policy, not provider mechanics.

#### `REVIEW_MODEL_CHAIN`

This ordered list is the final review fallback chain.

#### `call_review_agent(...)`

Iterates through provider/model choices until one succeeds.

#### `call_groq_8b(...)`

Convenience wrapper for the cheap/frequent Groq 8B path.

#### `call_red_flag_agent(...)`

Special fallback logic for red-flag generation.

#### `call_technical_depth_agent(...)`

Primary `gpt-oss-120b` path with fallback.

#### `call_six_second_agent(...)`

Primary qwen path with fallback.

#### `call_competitive_agent(...)`

Primary qwen path with NVIDIA fallback.

#### `_messages_to_prompt(messages)`

Converts chat messages into plain prompt text for providers that do not take the same interface.

---

## 16. `backend/corpus/`

This is not needed for the first analysis, but it supports long-term product learning.

### `corpus_store.py`

Purpose:

Store anonymized signals from opted-in analyses.

#### `AnonymisedSignal`

Holds stripped-down comparative data:

- role
- market
- company type
- week
- red-flag counts
- GitHub presence
- quantified bullet presence
- inferred college tier
- YOE band
- percentile range
- review model used

#### `_corpus_key(...)`

Builds Redis key.

#### `_current_week()`

Returns `YYYY-WNN`.

#### `store_signal(signal)`

Pushes JSON signal into a Redis list and refreshes TTL.

#### `get_signals(...)`

Reads recent weeks of signals back.

#### `get_corpus_size(...)`

Counts recent signals.

#### `build_signal_from_pipeline(...)`

This translates live analysis output into anonymised comparative features.

It uses heuristics for:

- quantified bullets
- GitHub presence
- college tier
- YOE band

### `bullet_curator.py`

Purpose:

Extract potential weak-bullet/rewrite pairs for later human review.

#### `BulletCandidate`

Carries:

- role/company/market
- weak bullet
- suggested rewrite
- review context
- session ID

#### `flag_bullet_candidate(candidate)`

Push candidate into Redis queue and trims queue length.

#### `get_candidates(limit=50)`

Reads queue back.

#### `extract_bullet_candidates(...)`

Uses regex heuristics to extract rewrite candidates from review text.

This is a curation-support feature, not a live user feature.

---

## 17. `ingestion/`

This folder powers the offline market corpus.

It is separate from live resume analysis, but the analysis experience depends on its output.

### `database.py`

This is the SQLite schema layer.

#### `get_connection()`

Open DB connection and set row factory.

#### `init_db()`

Creates:

- `market_signals`
- combo index
- FTS5 virtual table
- insert trigger
- delete trigger

This file explains how search works structurally:

- normal table for storage
- FTS5 for keyword retrieval
- embeddings stored as BLOBs for vector retrieval

### `search.py`

This is the query/update layer over SQLite.

#### `insert_signal(...)`

Insert one market signal row.

#### `search_signals(...)`

FTS5/BM25 retrieval within:

- same role
- same company type
- same market
- recent time window

#### `delete_signals_for_combo(...)`

Delete all signals for one combination before refresh.

#### `count_signals_for_combo(...)`

Count available signals for freshness/skip decisions.

### `embeddings.py`

This file manages semantic search vectors.

#### `_get_client()`

Build Gemini client from rotating API keys.

#### `embed_text(text)`

Flow:

1. choose current key
2. call Gemini embedding model
3. convert to float32 numpy array
4. normalize vector
5. return raw bytes
6. rotate key on 429

#### `bytes_to_vector(blob)`

Reverse storage encoding.

#### `cosine_similarity(a, b)`

Because vectors are normalized, dot product gives cosine similarity.

#### `update_embedding(row_id, text)`

Generate and persist one embedding.

#### `embed_all_missing()`

Find rows with null embedding and fill them.

#### `search_by_embedding(...)`

Embed the query, fetch all matching combo rows with stored embeddings, score them, sort them, and return the top matches.

This is the semantic half of DIVE retrieval.

### `tavily_client.py`

Small wrapper around Tavily search API.

#### `TavilyClient`

Tracks per-client monthly budget via Redis.

Methods:

- `get_budget()`
- `_increment_budget()`
- `budget_remaining()`
- `search(...)`

Two shared instances:

- `deep`
- `general`

### `groq_client.py`

Separate lightweight Groq helper for ingestion tasks.

Functions:

- `_get_client()`
- `_rotate()`
- `groq_complete(...)`

This file is smaller than the runtime Groq wrapper because ingestion needs fewer features.

### `extractor.py`

This file turns raw scraped text into structured hiring signals.

#### `SourceTier`

Classifies source quality:

- job posting
- recruiter post
- salary survey
- developer community
- technical blog
- discard

#### `TRUST_WEIGHTS`

Maps source category to confidence weight.

#### `HiringSignal`

Structured extracted object:

- signal type
- skills
- salary range
- sentiment
- trust weight
- source tier
- key insight
- red flag triggers
- format signals

#### `_get_client()` and `_rotate()`

Groq client rotation helpers.

#### `process_raw_text(text, role, market)`

This is the core ingestion extractor.

Flow:

1. truncate raw content
2. prompt model to classify and extract in one call
3. strip markdown noise
4. parse JSON
5. discard low-quality or irrelevant sources
6. validate minimal useful content
7. return `HiringSignal`

This file is the bridge from messy web text to clean retrieval corpus rows.

#### `classify_source(text)`

Backward-compatibility wrapper around the combined extractor.

### `levels_scraper.py`

This collects compensation-like data from Levels.fyi.

#### `fetch_levels_salary(company, role)`

Builds slugs, fetches page, parses HTML.

#### `_extract_salary_data(soup, company, role, url)`

Extracts:

- company
- role
- source URL
- visible text sample
- any table rows that look like level comp rows

### `breaking_signal.py`

This is the short-term hiring-news overlay.

#### `_breaking_key(...)`

Redis key builder.

#### `_role_to_category(role)`

Groups role into broader bucket for cache reuse.

#### `get_breaking_signal(...)`

Cache-first public entrypoint.

#### `_fetch_breaking_signal(...)`

Flow:

1. build two recent-news queries
2. fetch search results from Tavily general
3. gather short text snippets
4. if none exist, return empty
5. synthesize a 2-3 sentence summary with `call_groq_8b`

This is intentionally lightweight and failure-tolerant.

### `pipeline.py`

This is the offline refresh pipeline for one combo.

#### `_build_queries(role, company_type, market)`

Build the Tavily query set.

#### `COMPANY_TYPE_TO_LEVELS_COMPANIES`

Maps company type to which companies are worth checking on Levels.

#### `IngestionSummary`

Tracks results of one refresh job.

#### `_process_one(text, role, market, source, company_type)`

Flow:

1. classify and extract under Groq semaphore
2. discard if low quality
3. insert key insight into SQLite
4. return whether storage succeeded

#### `run_ingestion_for_combo(...)`

This is the big one.

Flow:

1. skip if enough fresh data exists unless forcing refresh
2. run all Tavily deep/general queries in parallel
3. fetch full text through Jina Reader when Tavily is truncated
4. abort refresh if results are too thin
5. only then delete old combo signals
6. optionally scrape Levels.fyi companies
7. process all text results in parallel
8. generate embeddings for stored rows
9. return summary

This function is careful not to destroy useful old data unless replacement data actually exists.

#### `_source_from_url(url)`

Map URL domain to clean source name.

#### `_fetch_jina(url)`

Pull full page text through `r.jina.ai` when normal snippets are too short.

---

## 18. `scripts/`

These are operator scripts, not imported modules in the main app path.

### `prepopulate.py`

Purpose:

Run ingestion across many role/company/market combinations.

Important structure:

- large `COMBINATIONS` list
- async `main()` loops through combinations
- each combo calls `run_ingestion_for_combo`
- waits a bit between combos

This is how the SQLite corpus gets initially filled.

### `reembed.py`

Purpose:

Backfill embeddings for rows missing them.

Top-to-bottom flow:

1. open DB
2. fetch rows with null embedding
3. loop them
4. call `update_embedding`
5. sleep lightly between requests
6. back off longer if rate-limited

This is maintenance logic for the vector-search layer.

---

## 19. `frontend/`

The frontend is much smaller than the backend, so you can understand it quickly once the backend is clear.

Read it in this order:

1. `src/main.jsx`
2. `src/App.jsx`
3. `src/lib/api.js`
4. `src/hooks/useWebSocket.js`
5. `src/components/LandingPage.jsx`
6. `src/components/AnalysisProgress.jsx`
7. `src/components/ResultsPage.jsx`
8. `src/components/ReviewDocument.jsx`
9. smaller helper components
10. `src/index.css`

### `package.json`

This shows the frontend stack:

- React
- Vite
- Tailwind v4
- Framer Motion
- Lucide icons

### `vite.config.js`

Important dev-server behavior:

- frontend default port
- proxy `/api` to backend
- WebSocket proxy enabled

This is why local frontend and backend can run separately but still feel like one app.

### `index.html`

Simple Vite HTML shell with `#root`.

### `src/main.jsx`

One responsibility:

- render `App` into `root`

### `src/App.jsx`

This is the frontend entrypoint and page-state switcher.

#### `getAnalysisCount()` and `incrementAnalysisCount()`

LocalStorage helpers used for simple client-side analysis count tracking.

#### `VisitorCounter()`

Calls `/health` and shows total roasts delivered if available.

#### `NavBar({ view, onBack })`

Renders brand, visitor badge, and back button when in analysis view.

#### `Footer()`

Shows author attribution and privacy/process note.

#### `AnalysisView({ sessionId, meta })`

Uses `useWebSocket(sessionId)`.

If review is done, show `ResultsPage`.
Otherwise show `AnalysisProgress`.

#### `App()`

Holds high-level state:

- current view
- session ID
- metadata

When analysis starts, it:

1. increments local count
2. stores session/meta
3. switches from landing to analysis

### `src/lib/api.js`

This is the frontend transport layer.

Functions:

- `sessionInit(...)`
- `submitAnalysis(...)`
- `getSessionState(sessionId)`
- `submitFollowup(...)`
- `submitFeedback(...)`
- `requestToken(email)`
- `verifyToken(...)`
- `createWebSocket(sessionId)`

Study insight:

This file is the clean map of backend API usage from the frontend side.

### `src/hooks/useWebSocket.js`

This hook manages live streaming and recovery.

#### `useWebSocket(sessionId)`

State:

- `sections`
- `status`
- `error`
- refs for websocket, poller, and missed-ping counter

Important internal behaviors:

- `addSection` merges completed sections into state
- `startPolling` begins fallback polling
- main effect opens WebSocket, handles messages, and starts heartbeat monitoring

This hook is the frontend reliability layer.

### `src/hooks/useInferenceToggle.js`

Small preference hook backed by localStorage.

Lets the user toggle inference-chain display on the review screen.

### `src/components/LandingPage.jsx`

This is the largest frontend file because it owns the input funnel.

#### `RoastingOverlay()`

Animated blocking overlay shown after submission.

#### Local constants

- `ROLES`
- `COMPANY_TYPES`
- `MARKETS`
- `EXPERIENCE_LEVELS`
- `FEATURES`

These define the frontend user-input vocabulary.

#### Inner `DropZone({ onFile })`

This file defines its own dropzone component locally, even though a separate `DropZone.jsx` also exists elsewhere.

Behavior:

- validate PDF type
- validate size
- track drag state
- allow clearing file

#### `AutoTextarea(...)`

Auto-resizing textarea helper.

#### `LandingPage({ onAnalysisStarted })`

This is the main intake screen.

State includes:

- file
- role/company/market/experience selections
- optional user context
- JD text
- GitHub URL
- consent
- corpus opt-in
- loading/roasting/error
- session ID

Important behavior:

On mount, it pre-creates a default session.

On submit:

1. validate required inputs
2. reuse or create session
3. call `submitAnalysis`
4. show roasting overlay
5. move to analysis screen
6. retry with a fresh session if timing gate says "too fast"

This component owns almost the entire user onboarding and upload experience.

### `src/components/AnalysisProgress.jsx`

Purpose:

Show staged progress while the backend pipeline runs.

#### `STEPS`

Human-readable step list.

#### `ROAST_QUOTES`

Rotating text lines to make waiting feel active.

#### `AnalysisProgress({ sessionId, sections })`

Key behavior:

- rotates quotes every few seconds
- polls session state every few seconds
- derives current step from completed sections
- renders terminal-style progress UI

This file is purely presentation plus polling logic.

### `src/components/ResultsPage.jsx`

This assembles the final analysis view.

#### `Card(...)`

Animated card wrapper.

#### `SectionLabel(...)`

Small header helper.

#### `PercentileBar({ range, confidence })`

Parses percentile strings and turns them into a progress bar with confidence label.

#### `CopyAllButton(...)`

Builds a plaintext export of the review and copies it to clipboard.

#### `ResultsPage({ sections, sessionId, meta, analysisCount })`

Composes:

- header
- TLDR card
- market pulse
- review document
- percentile/CTC section
- token-unlock widget after enough analyses
- feedback widget

This file is the final assembly layer for the user experience.

### `src/components/ReviewDocument.jsx`

This is the structured review renderer.

#### `SECTION_CONFIG`

Visual mapping of section type to colors/icons.

#### `parseContent(text)`

Splits prose and tries to detect inference-chain lines.

#### `parseActionPlan(text)`

Heuristically converts numbered prose into a step list.

#### `InferenceChain({ content })`

Renders recruiter inference chains visually.

#### `ActionSteps({ steps })`

Renders action-plan steps.

#### `SectionContent({ content, configKey, showInference })`

Chooses how to render a section:

- action plan as steps if possible
- hurting section with inference-chain highlighting if toggle is on
- otherwise plain prose

#### `Section(...)`

Collapsible section component.

It also owns:

- follow-up question clicks
- follow-up answer loading
- follow-up used-state

#### `ReviewDocument({ review, sessionId, loading })`

Composes all major review sections and the inference toggle.

This is where the backend’s JSON review becomes a usable studyable UI document.

### Smaller components

#### `MarketPulse.jsx`

Displays:

- market summary
- salary band
- top skills
- competitive pool summary
- breaking signal

#### `TLDRBlock.jsx`

Displays:

- shortlist chance
- biggest blocker
- fix first
- copy shortcut

#### `Feedback.jsx`

Contains:

- `FeedbackButton`
- `ThirdAnalysisUnlock`

#### `SkeletonLoader.jsx`

Generic loading placeholder lines.

#### `DropZone.jsx`

Standalone dropzone component, but note that the landing page currently defines and uses its own internal DropZone instead.

### `src/index.css`

This is the real styling file the app uses.

It defines:

- imported fonts
- CSS variables for ROAST theme
- body/background/mesh/noise styles
- form controls
- buttons
- cards
- terminal visuals
- skeletons
- progress bars
- nav/footer
- small utility-like handcrafted component classes

This file is the visual system.

### `src/App.css`

This looks like template residue from an earlier Vite starter.

It is not the main styling source for the current app flow.

### `public/`

- `favicon.svg`
- `icons.svg`

Static public assets.

### `dist/`

Built frontend output.

This is generated production output, not source-of-truth logic.

### `node_modules/`

Third-party frontend dependencies.

Do not study this to understand the app.

---

## 20. `tests/`

These are useful because they show intent, but they are not all aligned with current implementation.

### `test_pdf_reader.py`

Verifies PDF extraction basics.

### `test_phase1.py`

Manual-style test for:

- full extraction
- link extraction
- link verification

### `test_session_store.py`

Walks through session create/fetch/update flow.

### `test_rate_limit.py`

Intends to test daily limit behavior, though its expected counts do not match the current code.

### `test_config.py`

Intends to validate config loading, but the env names it imports do not match the current implementation.

### `test_levels_scraper.py`

Manual async test for Levels.fyi scraping.

### `test_tavily_client.py`

Manual async test for Tavily clients.

### `sample_resume.pdf`

Fixture resume for parser tests.

Study note:

These tests are best read as "what the author wanted to verify", not "guaranteed current truth".

---

## 21. Editor And Local State Folders

These are part of the repo state you asked me to study, but not part of the application logic.

### `.idea/`

PyCharm/JetBrains project metadata.

Interesting practical details:

- project is configured as a Python module
- `.venv` is excluded
- Git root is mapped
- workspace state shows recent local usage

### `.vscode/settings.json`

Very small local editor config. Here it just disables Amazon Q telemetry.

### `.pytest_cache/`

Generated Pytest cache.

### `.venv/`

Local Python virtual environment, including installed binaries and packages.

### `frontend/node_modules/`

Installed frontend packages.

### `frontend/dist/`

Compiled frontend bundle.

---

## 22. Files And Folders You Should Learn Deeply Vs Lightly

### Learn deeply

- `backend/main.py`
- `backend/routes/analyse.py`
- `backend/pipeline/orchestrator.py`
- `backend/retrieval/dive.py`
- `backend/agents/*`
- `backend/llm/router.py`
- `backend/storage/*`
- `ingestion/pipeline.py`
- `ingestion/search.py`
- `ingestion/embeddings.py`
- `frontend/src/App.jsx`
- `frontend/src/components/LandingPage.jsx`
- `frontend/src/hooks/useWebSocket.js`
- `frontend/src/components/ResultsPage.jsx`
- `frontend/src/components/ReviewDocument.jsx`

### Learn lightly

- `Dockerfile`
- `.env.example`
- `frontend/package.json`
- `frontend/vite.config.js`
- `scripts/*`

### Mostly reference only

- `.idea/*`
- `.vscode/*`
- `.venv/*`
- `frontend/node_modules/*`
- `frontend/dist/*`
- `.pytest_cache/*`

---

## 23. The Most Important Cross-File Relationships

These are the relationships that make the codebase click.

### Relationship 1: upload route -> orchestrator

`backend/routes/analyse.py` does input validation and background-task launch.

`backend/pipeline/orchestrator.py` does the real work.

This separation keeps the HTTP request fast and the pipeline logic testable.

### Relationship 2: DIVE -> MarketContextAgent -> parallel agents

`backend/retrieval/dive.py` retrieves market signals.

`backend/agents/market_context_agent.py` interprets them.

Only then do the downstream agents run.

This means the app first calibrates the target market before judging the resume.

### Relationship 3: Redis as the session spine

Redis is used for:

- session storage
- per-section result storage
- rate limits
- counters
- token unlocks
- share previews
- corpus signals
- curation queue

Redis is not just cache here. It is the cross-request state backbone.

### Relationship 4: frontend socket + backend section storage

The frontend relies on real-time sections.

The backend stores sections in Redis as soon as each is complete.

That makes reconnection and polling recovery easy.

### Relationship 5: ingestion -> SQLite -> DIVE

The ingestion pipeline is offline preparation.

DIVE is online retrieval over that prepared corpus.

The product quality depends heavily on this split.

---

## 24. What To Read First If You Want To Modify Something

### If you want to change upload validation

Read:

- `backend/routes/analyse.py`
- `backend/pdf_reader.py`
- `backend/config.py`

### If you want to change the review quality or tone

Read:

- `backend/agents/review_agent.py`
- `backend/agents/prompts/review_prompt.py`
- `backend/agents/schemas.py`

### If you want to change market intelligence behavior

Read:

- `ingestion/pipeline.py`
- `ingestion/extractor.py`
- `ingestion/search.py`
- `backend/retrieval/dive.py`

### If you want to change frontend flow

Read:

- `frontend/src/App.jsx`
- `frontend/src/components/LandingPage.jsx`
- `frontend/src/hooks/useWebSocket.js`
- `frontend/src/components/ResultsPage.jsx`

### If you want to change concurrency or fallback behavior

Read:

- `backend/pipeline/orchestrator.py`
- `backend/llm/router.py`
- `backend/llm/groq_client.py`
- `backend/llm/circuit_breaker.py`

---

## 25. Final Mental Model

The cleanest way to hold this codebase in your head is:

### Layer A: inputs and state

- `frontend/src/components/LandingPage.jsx`
- `backend/routes/session.py`
- `backend/routes/analyse.py`
- `backend/pdf_reader.py`
- `backend/storage/session_store.py`

### Layer B: market context

- `ingestion/*`
- `backend/retrieval/dive.py`
- `backend/agents/market_context_agent.py`

### Layer C: resume judgment

- `backend/agents/red_flag_agent.py`
- `backend/agents/six_second_agent.py`
- `backend/agents/competitive_agent.py`
- `backend/agents/technical_depth_agent.py`

### Layer D: synthesis

- `backend/agents/review_agent.py`

### Layer E: delivery

- `backend/routes/websocket.py`
- `backend/routes/ws_manager.py`
- `frontend/src/hooks/useWebSocket.js`
- `frontend/src/components/AnalysisProgress.jsx`
- `frontend/src/components/ResultsPage.jsx`
- `frontend/src/components/ReviewDocument.jsx`

If you study the repo in that order, it stops looking like many separate files and starts looking like one coherent system.

---

## 26. Practical Caveat While Studying

The repo contains some implementation drift:

- some tests do not match current code
- some comments/README claims lag behind implementation
- some generated/frontend artifact state is checked in

So when documentation and code disagree, trust the source files in the live runtime path first:

1. `backend/main.py`
2. `backend/routes/*`
3. `backend/pipeline/orchestrator.py`
4. `backend/agents/*`
5. `backend/retrieval/dive.py`
6. `frontend/src/*`

That is the real product behavior.

---

## 27. Interview Mode: Annotated Code Walkthroughs

The earlier sections explained architecture and flow.

This section does the thing you asked for explicitly:

- real code
- grouped under the relevant function
- with inline comments beside each line or line group
- written to help you explain the code in an interview

Important note:

For a repo this size, doing that for every single line of every single file would turn the document into a copy of the whole codebase and make it harder to study. So this section focuses on the interview-critical code paths first:

1. config loading
2. PDF extraction
3. session creation
4. analyse route
5. orchestrator
6. DIVE retrieval
7. review synthesis
8. frontend request flow
9. frontend WebSocket recovery flow

If you understand these deeply, you can usually answer most interview questions about the system.

---

## 28. Annotated Backend Code

### 28.1 `backend/config.py`

This file is often discussed in interviews under "how do you manage configuration safely?"

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Loads key-value pairs from .env into process environment variables.


def get_required_key(key: str) -> str:
    value = os.getenv(key)  # Read one env var from the current process.
    if value is None:  # Fail fast if a required secret/config is missing.
        raise ValueError(f"Required environment variable '{key}' is not set. Check your .env file.")
    return value  # Return the validated value.


def get_optional_key(key: str, default=None):
    return os.getenv(key, default)  # Same read path, but with fallback allowed.


ENVIRONMENT = get_optional_key("ENVIRONMENT", "production")  # Safe default for deployed app.
GROQ_API_KEYS = get_required_key("GROQ_API_KEYS")  # Mandatory because core agents depend on Groq.
GEMINI_API_KEYS = get_required_key("GEMINI_API_KEYS")  # Mandatory because embeddings depend on Gemini.
UPSTASH_REDIS_REST_URL = get_required_key("UPSTASH_REDIS_REST_URL")  # Required for Redis state.
UPSTASH_REDIS_REST_TOKEN = get_required_key("UPSTASH_REDIS_REST_TOKEN")  # Required auth token.
```

How to explain this in an interview:

- `load_dotenv()` is local-dev convenience.
- `get_required_key()` creates a fail-fast startup contract.
- the module exposes config as constants so downstream code imports one shared source of truth.

---

### 28.2 `backend/pdf_reader.py -> clean_text`

This is a classic preprocessing function.

```python
def clean_text(raw: str) -> str:
    lines = raw.splitlines()  # Split the raw PDF-extracted string into individual lines.
    cleaned = []  # We will rebuild a normalized version line by line.
    for line in lines:
        stripped = line.strip()  # Remove leading/trailing spaces and tabs from each line.
        cleaned.append(stripped)  # Keep the cleaned line, even if it becomes empty.

    rejoined = "\n".join(cleaned)  # Rebuild the full text after line-level cleanup.

    rejoined = re.sub(r"\n{3,}", "\n\n", rejoined)  # Collapse huge blank gaps into cleaner paragraph spacing.

    return rejoined.strip()  # Final trim so output has no blank noise at start or end.
```

Interview explanation:

- PDF text extraction often produces ugly whitespace.
- This function normalizes formatting before any AI sees it.
- The point is not "make it pretty"; the point is "make downstream parsing stable".

---

### 28.3 `backend/pdf_reader.py -> extract_links`

This is one of the more thoughtful input-processing functions in the repo.

```python
def extract_links(pdf_path: str) -> dict:
    links = {
        "page_count": 0,  # Track PDF page count for later validation/debugging.
        "validation_error": None,  # If the PDF is encrypted, we record it here.
        "all_urls": [],  # Collect every non-email URL found in annotation layer.
        "linkedin": None,  # First LinkedIn URL found.
        "github": None,  # First GitHub URL found.
    }

    with fitz.open(pdf_path) as doc:  # Open the PDF using PyMuPDF.
        if doc.is_encrypted:  # Stop early if the file is password-protected.
            links["validation_error"] = "PDF is encrypted. Please upload an unencrypted resume."
            return links

        links["page_count"] = len(doc)  # Save how many pages the PDF has.

        for page_number in range(len(doc)):  # Visit every page.
            page = doc.load_page(page_number)  # Load the current page object.
            for link in page.get_links():  # Read annotation-layer links, not visible text.
                uri = link.get("uri", "")  # Pull the hyperlink target if present.
                if not uri or uri.startswith("mailto:"):  # Ignore empty links and email links.
                    continue

                links["all_urls"].append(uri)  # Save every normal URL.

                parsed = urlparse(uri)  # Break URL into components.
                domain = parsed.netloc.lower()  # Normalize domain for matching.

                if "linkedin.com" in domain and links["linkedin"] is None:
                    links["linkedin"] = uri  # Save first LinkedIn profile.
                if "github.com" in domain and links["github"] is None:
                    links["github"] = uri  # Save first GitHub profile.

    return links  # Return all collected link metadata.
```

Why this is interview-worthy:

- it shows the author knew resume links may exist in annotation layer, not visible text
- this is a concrete example of domain-specific input handling

---

### 28.4 `backend/pdf_reader.py -> extract_text_from_pdf`

This is the main resume parsing pipeline.

```python
def extract_text_from_pdf(pdf_path: str) -> dict:
    from backend.config import MAX_PAGES, MAX_FILE_SIZE_MB  # Pull limits from shared config.
    import os

    result = {
        "page_count": 0,  # Number of pages in the PDF.
        "full_text": "",  # Final merged resume text.
        "pages": [],  # Per-page extracted data.
        "is_valid": False,  # Final validation result.
        "validation_error": None,  # Human-readable validation error if invalid.
        "error": None,  # Unexpected parser/runtime error string.
    }

    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)  # Convert raw bytes to MB for size gating.
    if size_mb > MAX_FILE_SIZE_MB:
        result["validation_error"] = f"File too large ({size_mb:.1f}MB). Max is {MAX_FILE_SIZE_MB}MB."
        return result  # Reject oversized file before parsing.

    try:
        with fitz.open(pdf_path) as doc:  # Open PDF safely.
            result["page_count"] = len(doc)  # Save page count.

            if len(doc) > MAX_PAGES:
                result["validation_error"] = f"Too many pages ({len(doc)}). Max is {MAX_PAGES}. Please upload a resume, not a CV."
                return result  # Reject long CV-style documents.

            all_text_parts = []  # Accumulate cleaned page text.
            for page_number in range(len(doc)):
                page = doc.load_page(page_number)  # Load one page.
                page_text_raw = page.get_text("text")  # Extract plain text from that page.
                page_text = page_text_raw if isinstance(page_text_raw, str) else ""  # Guard against weird output.
                cleaned = clean_text(page_text)  # Normalize whitespace and blank lines.

                result["pages"].append({
                    "page_number": page_number + 1,  # Human-friendly 1-based index.
                    "text": cleaned,  # Clean text for this page.
                    "char_count": len(cleaned),  # Useful for debugging and validation.
                })

                all_text_parts.append(cleaned)  # Save text so we can build final full resume.

            result["full_text"] = "\n\n".join(all_text_parts)  # Merge all pages with paragraph spacing.

    except Exception as e:
        result["error"] = str(e)  # Save parsing failure for caller.
        return result

    valid, reason = is_valid_resume_text(result["full_text"])  # Validate extracted text length.
    result["is_valid"] = valid  # Save boolean validation outcome.
    if not valid:
        result["validation_error"] = reason  # Save explanation for client.

    return result
```

Interview framing:

- "We validate as early as possible."
- "We distinguish validation errors from parser exceptions."
- "We keep both per-page structure and full merged text."

---

### 28.5 `backend/storage/session_store.py -> create_session`

```python
def create_session(role: str, market: str, company_type: str, experience_level: str = "Junior") -> dict:
    session_id = str(uuid.uuid4())  # Generate unique analysis session ID.
    session = {
        "session_id": session_id,  # Primary identifier for later HTTP/WebSocket lookups.
        "role": role,  # Target role selected by user.
        "market": market,  # Market selected by user.
        "company_type": company_type,  # Company type selected by user.
        "experience_level": experience_level,  # Used for market calibration and prompts.
        "created_at": int(time.time()),  # Unix timestamp used by timing gate and TTL reasoning.
        "status": "pending"  # Initial state before file upload/processing starts.
    }
    redis.setex(f"session:{session_id}", SESSION_TTL, json.dumps(session))  # Store serialized session with 1h TTL.
    return session  # Return the object immediately to the caller.
```

What to say in an interview:

- Redis is being used as lightweight session state, not relational persistence.
- The session object becomes the shared context spine across routes and the pipeline.

---

### 28.6 `backend/routes/analyse.py -> analyse`

This is the most important request handler in the repo.

```python
@router.post("/analyse")
async def analyse(
    request: Request,  # Gives access to headers and client IP.
    background_tasks: BackgroundTasks,  # Lets us launch long-running work after response returns.
    session_id: str = Form(...),  # Session ID sent from frontend multipart form.
    role: str = Form(...),  # Role calibration field.
    company_type: str = Form(...),  # Company-type calibration field.
    market: str = Form(...),  # Market calibration field.
    experience_level: str = Form(...),  # Experience calibration field.
    user_context: str = Form(default=""),  # Optional user-supplied context.
    jd_text: str = Form(default=""),  # Optional pasted job description.
    github_url: str = Form(default=""),  # Optional manual GitHub URL.
    opted_in_corpus: bool = Form(default=False),  # Privacy-controlled corpus opt-in.
    file: UploadFile = File(...),  # Uploaded resume PDF.
):
    session = get_session(session_id)  # Load session from Redis.
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Call /session-init first.")  # Hard fail if session missing.

    if session["status"] in ("processing", "completed"):
        return {
            "session_id": session_id,  # Reuse same ID.
            "status": session["status"],  # Tell frontend current status instead of duplicating work.
            "message": "Analysis already in progress or complete.",
        }

    elapsed = time.time() - session["created_at"]  # Measure time since session creation.
    if elapsed < BOT_TIMING_GATE_SECONDS:
        raise HTTPException(status_code=429, detail="Request too fast.")  # Crude bot/timing gate.

    client = request.client  # FastAPI client info.
    xff = request.headers.get("x-forwarded-for")  # Respect proxy-forwarded client IP if present.
    if xff:
        client_ip = xff.split(",")[0].strip()  # Use first forwarded IP.
    elif client and hasattr(client, "host"):
        client_ip = client.host  # Fallback to direct client host.
    elif client:
        client_ip = client[0]  # Final compatibility fallback.
    else:
        client_ip = "unknown"  # Never leave rate-limit key empty.

    from backend.config import ENVIRONMENT
    rate = check_and_increment_rate_limit(client_ip)  # Consume one analysis credit for this IP.
    if not rate["allowed"] and ENVIRONMENT == "production":
        token_unlocked = redis.get(f"token_unlocked:{session_id}")  # Check one-time unlock bypass.
        if not token_unlocked:
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit reached ({rate['limit']} analyses/day). Resets at midnight IST."
            )
        redis.delete(f"token_unlocked:{session_id}")  # Consume unlock if present.

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail=f"Only PDF files accepted. Got: {file.content_type}")  # Reject non-PDF uploads.

    contents = await file.read()  # Read full uploaded file into memory.

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)  # Save bytes to temp file because PyMuPDF works with file path.
        tmp_path = tmp.name  # Remember temp path.

    try:
        pdf_result = extract_text_from_pdf(tmp_path)  # Parse and validate text.
        links = extract_links(tmp_path)  # Extract annotation-layer profile URLs.
    finally:
        os.unlink(tmp_path)  # Always clean up temp file.

    if pdf_result["error"]:
        raise HTTPException(status_code=422, detail=f"PDF read error: {pdf_result['error']}")  # Parser failure path.

    if not pdf_result["is_valid"]:
        raise HTTPException(status_code=422, detail=pdf_result["validation_error"])  # Validation failure path.

    update_session(session_id, {
        "status": "processing",  # Mark live processing state.
        "resume_text": pdf_result["full_text"],  # Save extracted text for later agent access.
        "resume_links": links,  # Save extracted links for profile-aware analysis.
        "page_count": pdf_result["page_count"],  # Save metadata for debugging/results.
        "role": role,  # Persist final role chosen by user.
        "company_type": company_type,  # Persist final company type.
        "market": market,  # Persist final market.
        "experience_level": experience_level,  # Persist final experience level.
    })

    profile_links = {}  # Build compact profile-links payload for pipeline.
    if links.get("linkedin"):
        profile_links["linkedin"] = links["linkedin"]
    if links.get("github"):
        profile_links["github"] = links["github"]

    background_tasks.add_task(
        _run_pipeline_and_stream,  # Launch long-running analysis after response returns.
        session_id=session_id,
        resume_text=pdf_result["full_text"],
        role=role,
        company_type=company_type,
        market=market,
        experience_level=experience_level,
        user_context=user_context,
        jd_text=jd_text,
        profile_links=profile_links,
        github_url=github_url,
        opted_in_corpus=opted_in_corpus,
    )

    return {
        "session_id": session_id,  # Frontend needs this for socket and recovery endpoints.
        "status": "processing",  # Lets frontend switch to progress UI.
        "message": "Analysis started. Connect to /ws/{session_id} for real-time updates.",
        "pages": pdf_result["page_count"],  # Useful metadata.
        "chars": len(pdf_result["full_text"]),  # Useful metadata.
    }
```

Interview explanation:

- This route is intentionally a controller, not the analysis engine.
- It validates and schedules work, then returns quickly.
- Heavy compute is pushed to the background pipeline.

---

### 28.7 `backend/pipeline/orchestrator.py -> run_pipeline` and `_run_pipeline_inner`

Start with the thin wrapper:

```python
async def run_pipeline(request: PipelineRequest) -> PipelineResult:
    async with _global_sem:  # Limit how many complete end-to-end pipelines run at once.
        return await _run_pipeline_inner(request)  # Delegate actual business logic to inner function.
```

Now the real engine:

```python
async def _run_pipeline_inner(request: PipelineRequest) -> PipelineResult:
    start = time.time()  # Start stopwatch for duration tracking.
    sid = request.session_id  # Short local alias because session ID is used everywhere.

    logger.info(
        "pipeline_started",  # Structured log event name.
        session_id=sid,
        role=request.role,
        market=request.market,
        company_type=request.company_type,
    )

    update_session(sid, {"status": "in_progress", "step": "starting"})  # Persist live pipeline state.

    jd_requirements: JDRequirements | None = None  # Default: no parsed JD context.
    if request.jd_text and len(request.jd_text.strip()) > 50:
        update_session(sid, {"step": "parsing_jd"})  # Surface current stage to client/recovery API.
        jd_requirements = await parse_jd(request.jd_text, session_id=sid)  # Parse optional job description into structured fields.

    update_session(sid, {"step": "fetching_market_intel"})  # Advance step state.
    full_market_ctx = await run_dive(
        role=request.role,
        company_type=request.company_type,
        market=request.market,
        experience_level=request.experience_level,
        session_id=sid,
    )  # Retrieve market intelligence from SQLite + caches + breaking-signal layer.

    distilled_text = _format_distilled_context(full_market_ctx)  # Convert structured retrieval output into promptable text.

    update_session(sid, {"step": "market_context_agent"})  # Show next phase.
    async with _groq_sem:
        market_context = await run_market_context_agent(
            distilled_context=distilled_text,  # Retrieved market facts.
            role=request.role,
            company_type=request.company_type,
            market=request.market,
            experience_level=request.experience_level,
            user_context=request.user_context,
            jd_requirements=jd_requirements,
            session_id=sid,
        )  # First agent interprets market data into calibration rules.

    _store_section(sid, "market_context", market_context.model_dump())  # Save section to Redis for recovery/UI.
    await _emit(sid, "section_complete", {"section": "market_context", "result": market_context.model_dump()})  # Stream it live to frontend.
```

That first part gives you the structure:

- parse JD
- retrieve market data
- interpret market data
- stream section

Now the parallel stage:

```python
    update_session(sid, {"step": "parallel_agents"})  # Move into concurrent analysis stage.

    profile_links = request.profile_links  # Start with extracted links from PDF.
    if request.github_url:
        profile_links["github"] = request.github_url  # Manual GitHub URL overrides/adds if provided by user.

    red_flags_task = _run_with_groq_sem(
        run_red_flag_agent(
            resume_text=request.resume_text,
            market_context=market_context,  # Use calibrated market context, not just raw resume text.
            role=request.role,
            company_type=request.company_type,
            market=request.market,
            experience_level=request.experience_level,
            user_context=request.user_context,
            jd_requirements=jd_requirements,
            profile_links=profile_links,
            session_id=sid,
        )
    )

    six_second_task = run_six_second_trajectory_agent(
        resume_text=request.resume_text,
        market_context=market_context,
        role=request.role,
        company_type=request.company_type,
        market=request.market,
        experience_level=request.experience_level,
        user_context=request.user_context,
        profile_links=profile_links,
        session_id=sid,
    )  # Runs independently because it uses a different model path.

    competitive_task = run_competitive_agent(
        resume_text=request.resume_text,
        market_context=market_context,
        breaking_signal=full_market_ctx.breaking_signal,  # This agent also cares about short-term market movement.
        role=request.role,
        company_type=request.company_type,
        market=request.market,
        experience_level=request.experience_level,
        user_context=request.user_context,
        jd_requirements=jd_requirements,
        session_id=sid,
    )

    technical_depth_task = _run_with_tech_depth_sem(run_technical_depth_agent(
        resume_text=request.resume_text,
        role=request.role,
        company_type=request.company_type,
        market=request.market,
        experience_level=request.experience_level,
        session_id=sid,
    ))  # Serialized because this path is the most expensive/token-sensitive.

    red_flags, six_second, competitive, technical_depth = await asyncio.gather(
        red_flags_task,
        six_second_task,
        competitive_task,
        technical_depth_task,
        return_exceptions=True,  # Important: one agent can fail without collapsing the whole pipeline.
    )
```

Why this is strong interview material:

- it shows deliberate concurrency
- it shows provider-aware semaphore design
- it shows graceful degradation with `return_exceptions=True`

Now the synthesis and completion stage:

```python
    _store_section(sid, "red_flags", red_flags.model_dump())  # Cache result for reconnectable UI.
    await _emit(sid, "section_complete", {"section": "red_flags", "result": red_flags.model_dump()})
    _store_section(sid, "six_second", six_second.model_dump())  # Same pattern for each section.
    await _emit(sid, "section_complete", {"section": "six_second", "result": six_second.model_dump()})
    _store_section(sid, "competitive", competitive.model_dump())
    await _emit(sid, "section_complete", {"section": "competitive", "result": competitive.model_dump()})
    _store_section(sid, "technical_depth", technical_depth.model_dump())
    await _emit(sid, "section_complete", {"section": "technical_depth", "result": technical_depth.model_dump()})

    update_session(sid, {"step": "review_agent"})  # Last major stage before completion.
    review = await run_review_agent(
        resume_text=request.resume_text,
        market_context=market_context,
        red_flags=red_flags,
        six_second=six_second,
        competitive=competitive,
        role=request.role,
        company_type=request.company_type,
        market=request.market,
        experience_level=request.experience_level,
        user_context=request.user_context,
        jd_requirements=jd_requirements,
        technical_depth=technical_depth,
        session_id=sid,
    )  # Final synthesis agent writes the user-facing review.

    _store_section(sid, "review", review.model_dump())  # Save final review.
    await _emit(sid, "section_complete", {"section": "review", "result": review.model_dump()})  # Stream review immediately.

    duration = round(time.time() - start, 2)  # Compute total pipeline runtime.

    update_session(sid, {
        "status": "completed",  # Mark session done.
        "step": "done",
        "duration_seconds": duration,
    })

    redis.incr("counter:total_analyses")  # Global analytics counter.
    redis.incr(f"combo_count:{request.role}:{request.company_type}:{request.market}")  # Usage tracking for active market combos.
```

How to explain this in an interview:

- This file is effectively the service orchestration layer.
- It separates retrieval, agent fan-out, final synthesis, and state streaming.
- It is designed to favor partial success over catastrophic failure.

---

### 28.8 `backend/retrieval/dive.py -> run_dive`

```python
async def run_dive(
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    session_id: str = "",
) -> FullMarketContext:
    cached = _get_cached_snapshot(role, company_type, market)  # Check Redis for previously distilled market snapshot.
    if cached:
        logger.info("dive_cache_hit", role=role, market=market, session_id=session_id)
        breaking, breaking_available = await _get_breaking_signal_with_fetch(
            role, company_type, market, session_id
        )  # Even if long-term snapshot is cached, breaking news can still refresh separately.
        return FullMarketContext(
            distilled=cached,  # Reuse cached market summary.
            breaking_signal=breaking,
            breaking_available=breaking_available,
            raw_signal_count=0,  # Zero because we did not re-query SQLite this time.
        )

    signal_count = count_signals_for_combo(role, company_type, market)  # Ask SQLite whether this combo has any data.

    if signal_count == 0:
        logger.warning(
            "dive_no_signals",
            role=role, company_type=company_type, market=market,
            session_id=session_id,
        )
        breaking, breaking_available = await _get_breaking_signal_with_fetch(
            role, company_type, market, session_id
        )  # Even if deep data is missing, breaking signal may still exist.
        return FullMarketContext(
            distilled=DistilledMarketContext(
                hiring_sentiment="neutral",  # Baseline fallback because no structured corpus exists yet.
                top_required_skills=[],
                competitive_pool_signal="No market data available for this combination yet.",
                salary_band="data unavailable",
                red_flag_triggers=[],
                format_expectations="Standard resume format",
                weight_map={
                    "dsa": 0.7, "projects": 0.7, "cgpa": 0.5,
                    "experience": 0.7, "open_source": 0.4, "college_tier": 0.4
                },
                confidence="LOW",
                freshness_label="Needs Refresh",
            ),
            breaking_signal=breaking,
            breaking_available=breaking_available,
            raw_signal_count=0,
        )

    queries = _build_retrieval_queries(role, company_type, market, experience_level)  # Expand one combo into six retrieval intents.

    bm25_results, vector_results = await _parallel_search(
        role=role,
        company_type=company_type,
        market=market,
        queries=queries,
    )  # Run text search and semantic search simultaneously.

    fused = _rrf_fusion(bm25_results, vector_results)  # Merge rankings so dual-signal hits rise upward.
    deduped = _hash_dedup(fused, limit=15)  # Remove repeated near-identical signals.

    distilled = await _distill_context(
        signals=deduped,
        role=role,
        company_type=company_type,
        market=market,
        experience_level=experience_level,
        session_id=session_id,
    )  # Ask the distiller model to compress raw signals into structured market summary.

    _cache_snapshot(role, company_type, market, distilled)  # Save distilled snapshot for future requests.

    breaking, breaking_available = await _get_breaking_signal_with_fetch(
        role, company_type, market, session_id
    )  # Overlay short-term news after long-term snapshot is ready.

    return FullMarketContext(
        distilled=distilled,
        breaking_signal=breaking,
        breaking_available=breaking_available,
        raw_signal_count=len(deduped),  # Useful debug/observability field for how much evidence was used.
    )
```

The interview explanation is:

- Redis snapshot cache avoids recomputing expensive retrieval compression.
- SQLite stores the long-lived market corpus.
- BM25 and embeddings are both used because they fail differently and complement each other.

---

### 28.9 `backend/agents/review_agent.py -> _build_upstream_summary`

This function is an underrated interview talking point because it is deterministic, not prompt magic.

```python
def _build_upstream_summary(
    market_context: MarketContextOutput,
    red_flags: RedFlagOutput,
    six_second: SixSecondAndTrajectoryOutput,
    competitive: CompetitiveOutput,
    jd_requirements: JDRequirements | None,
    technical_depth: TechnicalDepthOutput | None = None,
) -> str:
    high_flags = [f for f in red_flags.red_flags if f.severity == "HIGH"]  # Separate severe issues because they matter most to final review.
    other_flags = [f for f in red_flags.red_flags if f.severity != "HIGH"]  # Keep lower-severity issues separate.

    flags_text = ""  # We are going to manually build a compact textual summary.
    if high_flags:
        flags_text += "HIGH SEVERITY FLAGS:\n"
        for f in high_flags:
            flags_text += f"- {f.flag}\n  Quote: \"{f.location}\"\n  Inference: {f.inference_chain}\n  Fix: {f.fix}\n\n"
            # For severe flags, include full detail because ReviewAgent must talk about them concretely.

    if other_flags:
        flags_text += "OTHER FLAGS:\n"
        for f in other_flags[:5]:
            flags_text += f"- [{f.severity}] {f.flag} | Fix: {f.fix}\n"
            # Lower-severity flags are compressed so prompt stays smaller.

    jd_text = ""
    if jd_requirements:
        jd_text = f"""
JD REQUIREMENTS:
Required skills: {', '.join(jd_requirements.required_skills)}
Preferred skills: {', '.join(jd_requirements.preferred_skills)}
Experience range: {jd_requirements.experience_range}
"""
        # Convert parsed JD object into compact readable text for final review prompt.

    tech_text = ""
    if technical_depth and technical_depth.project_evaluations:
        tech_text = "TECHNICAL DEPTH EVALUATION:\n"
        tech_text += f"Overall: {technical_depth.overall_technical_level}\n"
        tech_text += f"Most differentiated signal: {technical_depth.most_differentiated_signal}\n"
        tech_text += f"Biggest technical gap: {technical_depth.biggest_technical_gap}\n"
        tech_text += f"Communication gap: {technical_depth.communication_gap}\n"
        tech_text += f"Honest summary: {technical_depth.honest_summary}\n"
        # This makes technical-depth output lead the final synthesis instead of being buried.

    return f"""{tech_text}
MARKET CONTEXT:
Sentiment: {market_context.live_context_summary}
Weight map: {json.dumps(market_context.weight_map)}
Format expectations: {market_context.format_expectations}
Competitive pool: {market_context.competitive_pool_description}

SIX-SECOND SCAN (how a non-technical recruiter sees this):
Survived cut: {six_second.survived_cut_assessment}
First impression: {six_second.first_impression}
Remembered: {', '.join(six_second.remembered[:3])}
Career story: {six_second.career_story}
Progression: {six_second.progression_signal}

RED FLAGS (recruiter perspective):
{flags_text or 'No significant red flags found.'}
Visual scan: {red_flags.visual_scan_notes}

COMPETITIVE POSITION:
Percentile: {competitive.percentile_estimate.range} ({competitive.percentile_estimate.confidence})
Reasoning: {competitive.percentile_estimate.reasoning}
Expected CTC range: {competitive.expected_ctc_range or 'Not estimated'}
Highest leverage change: {competitive.highest_leverage_change}
{jd_text}"""
    # Final output is one deterministic, compact, model-readable summary string.
```

Interview explanation:

- This function is what keeps the final prompt structured.
- It reduces prompt chaos by compressing upstream structured outputs before the final synthesis call.

---

## 29. Annotated Frontend Code

### 29.1 `frontend/src/lib/api.js -> submitAnalysis`

```javascript
export async function submitAnalysis({
  sessionId,      // Redis session identifier created earlier.
  file,           // Uploaded PDF file object from browser.
  role,           // User-selected role.
  company_type,   // User-selected company type.
  market,         // User-selected market.
  experience_level, // User-selected experience level.
  userContext,    // Optional extra context.
  jdText,         // Optional job description.
  githubUrl,      // Optional manual GitHub URL.
  optedInCorpus   // Privacy-controlled corpus opt-in.
}) {
  const form = new FormData()  // Multipart form is required because we are uploading a file.
  form.append('session_id', sessionId)
  form.append('role', role)
  form.append('company_type', company_type)
  form.append('market', market)
  form.append('experience_level', experience_level)
  form.append('user_context', userContext || '')
  form.append('jd_text', jdText || '')
  form.append('github_url', githubUrl || '')
  form.append('opted_in_corpus', optedInCorpus ? 'true' : 'false')
  form.append('file', file)

  const res = await fetch(`${BASE}/analyse`, { method: 'POST', body: form }) // Browser sets multipart boundary automatically.
  if (!res.ok) {
    const body = await res.text()  // Read raw error body for better surfacing.
    throw new Error(body)  // Bubble backend message to caller.
  }
  return res.json()  // Return processing metadata to landing page.
}
```

Interview explanation:

- JSON is not used here because file upload requires multipart form data.
- The frontend sends both the file and calibration metadata in one request.

---

### 29.2 `frontend/src/hooks/useWebSocket.js -> useWebSocket`

```javascript
export function useWebSocket(sessionId) {
  const [sections, setSections] = useState({}) // Holds completed result sections by name.
  const [status, setStatus] = useState('connecting') // Tracks live connection state for UI.
  const [error, setError] = useState(null) // Holds backend-streamed error message if any.
  const wsRef = useRef(null) // Stores active WebSocket object across renders.
  const pollRef = useRef(null) // Stores fallback polling interval ID.
  const missedPings = useRef(0) // Tracks heartbeat health.

  const addSection = useCallback((section, result) => {
    setSections(prev => ({ ...prev, [section]: result })) // Merge newly completed section into existing section map.
  }, [])

  const startPolling = useCallback(() => {
    if (pollRef.current) return // Avoid starting duplicate polling intervals.
    pollRef.current = setInterval(async () => {
      try {
        const state = await getSessionState(sessionId) // Poll recovery endpoint.
        Object.entries(state.results || {}).forEach(([section, result]) => {
          addSection(section, result) // Rehydrate all completed sections from server state.
        })
        if (state.status === 'completed') {
          setStatus('complete') // If server says done, stop polling and mark final state.
          clearInterval(pollRef.current)
          pollRef.current = null
        }
      } catch (e) {
        // Polling errors are ignored because this is fallback recovery, not primary path.
      }
    }, 5000)
  }, [sessionId, addSection])

  useEffect(() => {
    if (!sessionId) return // Do nothing until we have a valid session ID.

    const connect = () => {
      const ws = createWebSocket(sessionId) // Build `ws://` or `wss://` socket URL.
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('streaming') // Switch UI to live-streaming state.
        missedPings.current = 0 // Reset heartbeat failure count.
        if (pollRef.current) {
          clearInterval(pollRef.current) // Stop fallback polling if socket recovered.
          pollRef.current = null
        }
      }

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data) // Backend sends structured JSON events.

          if (msg.event === 'ping') {
            ws.send('pong') // Respond to server heartbeat so connection stays healthy.
            missedPings.current = 0
            return
          }

          if (msg.event === 'section_complete') {
            addSection(msg.data.section, msg.data.result) // Store streamed result chunk.
          }

          if (msg.event === 'complete') {
            setStatus('complete') // Final pipeline event.
          }

          if (msg.event === 'error') {
            setError(msg.data.message) // Surface backend failure message.
            setStatus('error')
          }
        } catch (e) {
          // Ignore malformed socket messages instead of crashing UI.
        }
      }

      ws.onclose = () => {
        startPolling() // If socket closes, fall back to polling server state.
      }

      ws.onerror = () => {
        startPolling() // Same fallback on socket error.
      }
    }

    connect() // Start primary realtime connection.

    const heartbeatCheck = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        missedPings.current += 1 // Assume one ping cycle was missed until proven otherwise.
        if (missedPings.current >= 3) {
          startPolling() // If heartbeats stop arriving, recover through polling.
        }
      }
    }, 15000)

    return () => {
      clearInterval(heartbeatCheck) // Cleanup heartbeat interval on unmount/change.
      if (pollRef.current) clearInterval(pollRef.current) // Cleanup fallback polling.
      if (wsRef.current) wsRef.current.close() // Close socket cleanly.
    }
  }, [sessionId, addSection, startPolling])

  return { sections, status, error } // Expose live result state to components.
}
```

Interview explanation:

- The key idea is graceful realtime degradation.
- WebSocket is primary.
- polling is fallback.
- Redis-backed section storage on backend makes that recovery possible.

---

### 29.3 `frontend/src/components/LandingPage.jsx -> handleSubmit`

This is the frontend counterpart to the backend analyse route.

```javascript
const handleSubmit = async () => {
  if (!canSubmit || loading) return // Prevent invalid or duplicate submissions.
  setLoading(true) // Disable UI and show loading state.
  setError('') // Clear previous error before new attempt.

  try {
    let sid = sessionId // Reuse existing pre-created session if available.
    if (!sid) {
      const session = await sessionInit({ role, market, company_type: companyType, experience_level: experienceLevel })
      sid = session.session_id // If no existing session, create one now.
    }

    await submitAnalysis({
      sessionId: sid,
      file,
      role,
      company_type: companyType,
      market,
      experience_level: experienceLevel,
      userContext,
      jdText,
      githubUrl,
      optedInCorpus: optedIn
    }) // Kick off backend processing.

    setRoasting(true) // Show animated roasting overlay.
    await new Promise(r => setTimeout(r, 2500)) // Hold overlay briefly for UX smoothness.
    onAnalysisStarted(sid, { role, companyType, market, experienceLevel }) // Switch app into analysis/progress view.

  } catch (e) {
    if (e.message?.includes('too fast')) { // Special case for backend timing gate.
      try {
        const session = await sessionInit({ role, market, company_type: companyType, experience_level: experienceLevel })
        await new Promise(r => setTimeout(r, 4000)) // Wait long enough to satisfy backend timing rule.
        await submitAnalysis({
          sessionId: session.session_id,
          file,
          role,
          company_type: companyType,
          market,
          experience_level: experienceLevel,
          userContext,
          jdText,
          githubUrl,
          optedInCorpus: optedIn
        })
        setRoasting(true)
        await new Promise(r => setTimeout(r, 2500))
        onAnalysisStarted(session.session_id, { role, companyType, market, experienceLevel })
        return
      } catch (e2) {
        setError(e2.message || 'Something went wrong.') // Surface retry failure.
        setLoading(false)
        return
      }
    }

    let msg = 'Something went wrong. Please try again.'
    try {
      const p = JSON.parse(e.message) // Backend sometimes sends JSON error body as raw string.
      msg = p.detail || e.message
    } catch {
      msg = e.message || msg // Fallback to raw text message.
    }
    setError(msg) // Show final user-facing error.
    setLoading(false)
  }
}
```

Interview explanation:

- The frontend intentionally contains a special retry path because the backend enforces a session-age timing gate.
- This is a UX adaptation to backend anti-bot logic.

---

## 30. How To Use These Annotated Blocks In Interviews

When asked about a function, answer in this order:

1. say its purpose in one sentence
2. say the input/output contract
3. explain the major steps top to bottom
4. explain one good engineering decision inside it
5. explain one tradeoff or limitation

Example for `analyse()`:

- Purpose: accept the uploaded resume and trigger background analysis.
- Contract: multipart form in, processing metadata out.
- Steps: validate session, rate limit, parse PDF, save session state, launch background pipeline.
- Good decision: keep heavy work out of request-response cycle.
- Tradeoff: temp-file write means extra disk I/O, but simplifies PDF library compatibility.

That answer style sounds much stronger than reading code line by line out loud.

---

## 31. Exhaustive Backend File Inventory

This section is the strict backend completeness pass.

I am listing every backend file and stating what is inside it, even if the file is tiny.

### `backend/__init__.py`

Contents:

- empty package marker

Why it exists:

- tells Python that `backend` is an importable package

No functions.

---

### `backend/config.py`

Already covered in detail above.

Functions in this file:

- `get_required_key`
- `get_optional_key`

Role:

- central config loader and validator

---

### `backend/main.py`

Already covered in detail above.

Functions in this file:

- `health_check`
- `robots`
- `favicon` inside static-file block
- `serve_spa` inside static-file block

Role:

- FastAPI app entrypoint and static frontend host

---

### `backend/pdf_reader.py`

Already covered in detail above.

Functions in this file:

- `clean_text`
- `is_valid_resume_text`
- `extract_links`
- `verify_link`
- `extract_text_from_pdf`

Role:

- resume PDF text and link extraction

---

## 32. Exhaustive `backend/storage/`

### `backend/storage/__init__.py`

Contents:

- empty package marker

No functions.

### `backend/storage/redis_client.py`

Contents:

- `load_dotenv()`
- `redis = Redis.from_env()`

No custom functions.

Role:

- shared Redis client singleton

### `backend/storage/session_store.py`

Functions:

- `create_session`
- `get_session`
- `update_session`

Already explained earlier. This is Redis-backed session CRUD.

### `backend/storage/rate_limit.py`

Functions:

- `_seconds_until_midnight_ist`
- `check_and_increment_rate_limit`
- `get_rate_limit_status`

Already explained earlier. This is daily per-IP quota control.

---

## 33. Exhaustive `backend/routes/`

### `backend/routes/__init__.py`

Contents:

- empty package marker

No functions.

### `backend/routes/session.py`

Classes:

- `SessionInitRequest`
- `SessionInitResponse`

Functions:

- `session_init`
- `get_session_route`

Meaning:

- creates and retrieves session state

Annotated logic summary:

- `session_init` validates request body through Pydantic, calls Redis session creation, returns session ID
- `get_session_route` fetches stored session or 404s

### `backend/routes/followup.py`

Classes:

- `FollowUpRequest`

Functions:

- `followup`

Meaning:

- one follow-up answer per section per session

Important implementation ideas:

- session existence check
- one-use enforcement
- pulls stored review section from Redis
- marks section as used before running agent

### `backend/routes/analyse.py`

Functions:

- `_run_pipeline_and_stream`
- `analyse`

Already covered in detail above.

### `backend/routes/websocket.py`

Functions:

- `websocket_endpoint`
- `session_state`
- `share_preview`
- `_get_completed_sections`

#### `websocket_endpoint`

Purpose:

- primary realtime channel for progress/results

Key logic:

- accept socket
- start heartbeat task
- replay already finished sections on reconnect
- wait for client messages or timeout
- break when session becomes completed/failed

#### `session_state`

Purpose:

- polling fallback recovery endpoint

Returns:

- status
- completed section names
- pending section names
- result payloads

#### `share_preview`

Purpose:

- safe public preview of only TLDR-level summary

Key logic:

- cache in Redis for 7 days
- read stored review
- expose only shortlist chance, blocker, fix first, role, market

#### `_get_completed_sections`

Purpose:

- build in-memory dict of finished sections from Redis

### `backend/routes/ws_manager.py`

Functions:

- `connect`
- `disconnect`
- `emit`
- `heartbeat_loop`

Already discussed, but for completeness:

- `connect` stores accepted socket by session ID
- `disconnect` removes it
- `emit` sends event JSON if socket exists
- `heartbeat_loop` periodically sends `ping`

### `backend/routes/token_feedback.py`

Classes:

- `TokenRequest`
- `TokenVerifyRequest`
- `FeedbackRequest`

Functions:

- `request_token`
- `verify_token`
- `_send_token_email`
- `feedback`

#### `request_token`

Purpose:

- one token per email per day for extra free analysis

Key steps:

- validate email
- block duplicate daily sends
- create UUID token
- store token and email sent-flag in Redis
- send email via Resend or return dev token if email service absent

#### `verify_token`

Purpose:

- convert token into one-time session unlock

Key steps:

- validate token exists
- delete token immediately
- set `token_unlocked:{session_id}`

#### `_send_token_email`

Purpose:

- provider-specific Resend API call wrapper

#### `feedback`

Purpose:

- collect thumbs-up/down product feedback

Key steps:

- increment global counters
- increment per-combination counters
- best-effort trace to Langfuse

### `backend/routes/cron.py`

Functions:

- `_verify_qstash_signature`
- `_get_active_combinations`
- `refresh_market_intel`
- `_notify_discord`

#### `_verify_qstash_signature`

Purpose:

- authenticate scheduled webhook calls using HMAC

#### `_get_active_combinations`

Purpose:

- decide which role/company/market combinations deserve refresh

Sources:

- hardcoded Tier 1 list
- Redis combo usage counts

#### `refresh_market_intel`

Purpose:

- run ingestion refresh over selected combinations

Major flow:

- verify signature
- load active combos
- iterate combo refreshes
- collect success/failure stats
- optionally notify Discord

#### `_notify_discord`

Purpose:

- operational alert helper

---

## 34. Exhaustive `backend/pipeline/`

### `backend/pipeline/__init__.py`

Contents:

- empty package marker

No functions.

### `backend/pipeline/orchestrator.py`

Classes:

- `PipelineRequest`
- `PipelineResult`

Functions:

- `_emit`
- `run_pipeline`
- `_run_pipeline_inner`
- `_run_with_groq_sem`
- `_run_with_tech_depth_sem`
- `_run_with_gemini_sem`
- `_format_distilled_context`
- `_store_section`

We already covered the main orchestration flow. For completeness:

#### `_format_distilled_context`

Purpose:

- convert structured DIVE output into compact prompt text

Why it exists:

- prompt text is easier to hand into the market-context agent than a raw object

#### `_store_section`

Purpose:

- save one completed section as Redis JSON with TTL

Why it exists:

- reconnectable frontend
- share preview generation
- polling fallback

---

## 35. Exhaustive `backend/retrieval/`

### `backend/retrieval/__init__.py`

Contents:

- empty package marker

No functions.

### `backend/retrieval/dive.py`

Classes:

- `DistilledMarketContext`
- `FullMarketContext`

Functions:

- `_build_retrieval_queries`
- `_parallel_search`
- `_rrf_fusion`
- `_hash_dedup`
- `_distill_context`
- `_get_freshness_label`
- `_breaking_signal_key`
- `_role_to_category`
- `_get_breaking_signal`
- `_get_breaking_signal_with_fetch`
- `_snapshot_key`
- `_snapshot_prev_key`
- `_get_cached_snapshot`
- `_cache_snapshot`
- `run_dive`

Already covered conceptually above. For completeness:

#### `_parallel_search`

Purpose:

- run BM25 and vector search at the same time

Sub-logic:

- local `_bm25_search()` loops through generated queries
- local `_vector_search()` embeds combined query text

#### `_rrf_fusion`

Purpose:

- combine two ranked lists without needing calibrated score scales

#### `_hash_dedup`

Purpose:

- stop repeated signals from dominating prompt evidence

#### `_distill_context`

Purpose:

- convert top retrieved signals into one structured market summary via LLM

#### `_get_freshness_label`

Purpose:

- communicate how old the evidence is

#### snapshot helpers

Purpose:

- Redis memoization around expensive retrieval distillation

---

## 36. Exhaustive `backend/corpus/`

### `backend/corpus/__init__.py`

Contents:

- empty package marker

### `backend/corpus/corpus_store.py`

Class:

- `AnonymisedSignal`

Functions:

- `_corpus_key`
- `_current_week`
- `store_signal`
- `get_signals`
- `get_corpus_size`
- `build_signal_from_pipeline`

#### `_corpus_key`

Purpose:

- consistent Redis naming for anonymised corpus buckets

#### `_current_week`

Purpose:

- weekly partitioning key

#### `store_signal`

Purpose:

- push one anonymised pipeline summary into Redis list

#### `get_signals`

Purpose:

- load recent historical anonymised signals

#### `get_corpus_size`

Purpose:

- quick count helper

#### `build_signal_from_pipeline`

Purpose:

- translate rich resume analysis output into privacy-safe structured metadata

### `backend/corpus/bullet_curator.py`

Class:

- `BulletCandidate`

Functions:

- `flag_bullet_candidate`
- `get_candidates`
- `extract_bullet_candidates`

#### `flag_bullet_candidate`

Purpose:

- queue candidate rewrite examples for human review

#### `get_candidates`

Purpose:

- inspect pending queue

#### `extract_bullet_candidates`

Purpose:

- regex-based mining of "weak bullet -> rewrite" pairs from review prose

---

## 37. Exhaustive `backend/llm/`

### `backend/llm/__init__.py`

Contents:

- empty package marker

### `backend/llm/circuit_breaker.py`

Class:

- `CircuitBreaker`

Methods:

- `__init__`
- `record_failure`
- `record_success`
- `should_skip`

Singletons:

- `groq_circuit`
- `gemini_circuit`
- `cerebras_circuit`
- `openrouter_circuit`
- `nim_circuit`

### `backend/llm/router.py`

Constants:

- `REVIEW_MODEL_CHAIN`

Functions:

- `call_review_agent`
- `call_groq_8b`
- `call_red_flag_agent`
- `call_technical_depth_agent`
- `call_six_second_agent`
- `call_competitive_agent`
- `_messages_to_prompt`

#### `call_review_agent`

Purpose:

- ordered fallback chain for final review generation

#### `call_groq_8b`

Purpose:

- standard helper for quick structured calls

#### `call_red_flag_agent`

Purpose:

- red-flag-specific primary and fallback model strategy

#### `call_technical_depth_agent`

Purpose:

- primary frontier model path with simple fallback

#### `call_six_second_agent`

Purpose:

- primary qwen path for scan/trajectory

#### `call_competitive_agent`

Purpose:

- primary qwen path plus NIM fallback

#### `_messages_to_prompt`

Purpose:

- flatten chat-style messages for providers that need prompt text

### `backend/llm/groq_client.py`

Functions:

- `_get_client`
- `_rotate`
- `_rpd_key`
- `_check_rpd`
- `_increment_rpd`
- `groq_chat`

Already discussed above.

### `backend/llm/gemini_client.py`

Functions:

- `_get_client`
- `_rotate`
- `gemini_chat`

Purpose:

- key-rotating Gemini text generation wrapper

### `backend/llm/cerebras_client.py`

Functions:

- `cerebras_chat`

Purpose:

- Cerebras chat completion wrapper

### `backend/llm/nvidia_nim_client.py`

Functions:

- `nim_chat`

Purpose:

- NVIDIA NIM chat completion wrapper

### `backend/llm/openrouter_client.py`

Functions:

- `openrouter_chat`

Purpose:

- last-resort free OpenRouter fallback

### `backend/llm/langfuse_client.py`

Functions:

- `_init`
- `trace_llm_call`
- `trace_feedback`

Purpose:

- observability and feedback scoring

---

## 38. Exhaustive `backend/agents/`

### `backend/agents/__init__.py`

Contents:

- empty package marker

### `backend/agents/schemas.py`

Classes:

- `JDRequirements`
- `MarketContextOutput`
- `GapSignal`
- `SixSecondAndTrajectoryOutput`
- `RedFlag`
- `RedFlagOutput`
- `PercentileEstimate`
- `CompetitiveOutput`
- `ReviewOutput`
- `FollowUpOutput`

Imported from technical-depth file:

- `TechnicalDepthOutput`
- `ProjectEvaluation`

Purpose:

- the schema contract layer for all agent I/O

### `backend/agents/json_utils.py`

Functions:

- `extract_json`

Purpose:

- parse unreliable model outputs into valid JSON

### `backend/agents/tech_search.py`

Functions:

- `lookup_technology`
- `_ddg_search`
- `lookup_multiple`

Purpose:

- niche-tech research support for technical-depth agent

### `backend/agents/market_context_agent.py`

Functions:

- `parse_jd`
- `run_market_context_agent`

Already covered.

### `backend/agents/red_flag_agent.py`

Functions:

- `_passes_quality_gate`
- `run_red_flag_agent`

#### `_passes_quality_gate`

Purpose:

- reject generic, weak, or too-short red flags

#### `run_red_flag_agent`

Purpose:

- produce concrete resume liabilities and recruiter inference chains

### `backend/agents/six_second_agent.py`

Functions:

- `run_six_second_trajectory_agent`

Purpose:

- simulate instant recruiter scan plus broader career-trajectory reading

### `backend/agents/competitive_agent.py`

Functions:

- `run_competitive_agent`

Purpose:

- estimate where candidate sits in peer pool and what offer range fits

### `backend/agents/technical_depth_agent.py`

Classes:

- `ProjectEvaluation`
- `TechnicalDepthOutput`

Functions:

- `_should_skip_search`
- `_parse_output`
- `_run_agentic_loop`
- `run_technical_depth_agent`
- `_fallback_evaluation`

Already covered conceptually above.

### `backend/agents/review_agent.py`

Functions:

- `_count_words`
- `_passes_quality_gate`
- `_build_upstream_summary`
- `run_review_agent`
- `_assemble_partial_review`

Already covered conceptually above.

### `backend/agents/followup_agent.py`

Functions:

- `_followup_key`
- `has_used_followup`
- `mark_followup_used`
- `run_followup_agent`

Purpose:

- small follow-up Q&A generation and one-use enforcement

---

## 39. Exhaustive `backend/agents/prompts/`

These files do not contain normal control-flow functions except `template.py`, but they are still part of backend behavior.

### `backend/agents/prompts/__init__.py`

Contents:

- empty package marker

### `backend/agents/prompts/template.py`

Constants:

- `UNIVERSAL_CONSTRAINTS`

Functions:

- `get_role_calibration`
- `get_city_hint`
- `build_system_prompt`

#### `get_role_calibration`

Purpose:

- role- and company-type-specific evaluation rules

It has explicit branches for:

- SDE / software / full stack / backend
- AI/ML engineer
- data scientist
- data engineer
- data analyst
- embedded systems engineer
- VLSI design engineer
- DevOps / SRE
- product manager
- business analyst
- generic fallback

#### `get_city_hint`

Purpose:

- market/city heuristics, especially for Indian company-type patterns

#### `build_system_prompt`

Purpose:

- compose shared prompt shell around each agent task

### `backend/agents/prompts/market_context_prompt.py`

Contents:

- `VERSIONS`
- `ACTIVE`

Role:

- instruct MarketContextAgent what output shape and weighting logic to use

### `backend/agents/prompts/red_flag_prompt.py`

Contents:

- `VERSIONS`
- `ACTIVE`

Role:

- define red-flag hunt rules, banned generic chains, and role-specific exceptions

### `backend/agents/prompts/six_second_prompt.py`

Contents:

- `VERSIONS`
- `ACTIVE`

Role:

- define scan-plus-trajectory JSON output

### `backend/agents/prompts/competitive_prompt.py`

Contents:

- `VERSIONS`
- `ACTIVE`

Role:

- define percentile/CTC expectations and same-experience-level calibration

### `backend/agents/prompts/review_prompt.py`

Contents:

- `VERSIONS`
- `ACTIVE`

Role:

- define final prose review structure and quality rules

### `backend/agents/prompts/follow_up_prompt.py`

Contents:

- `VERSIONS`
- `ACTIVE`

Role:

- define short answer tone/length

---

## 40. Exhaustive Frontend File Inventory

This is the strict frontend completeness pass.

### `frontend/.gitignore`

Purpose:

- ignore logs, local env-like files, `node_modules`, `dist`, editor junk

No functions.

### `frontend/README.md`

Purpose:

- default Vite/React template README

It is not the real product manual.

### `frontend/package.json`

Purpose:

- frontend dependency and script manifest

Important script entries:

- `dev`
- `build`
- `lint`
- `preview`

### `frontend/package-lock.json`

Purpose:

- exact frontend dependency resolution

Generated, not handwritten logic.

### `frontend/eslint.config.js`

Purpose:

- lint configuration for JS/JSX

No runtime app functions.

### `frontend/vite.config.js`

Purpose:

- dev server config and API/WebSocket proxy

No app UI functions.

### `frontend/index.html`

Purpose:

- HTML shell with `#root`

### `frontend/public/favicon.svg`

Purpose:

- favicon asset

### `frontend/public/icons.svg`

Purpose:

- static SVG icon sprite asset

### `frontend/dist/`

Generated production build output.

Files present:

- `index.html`
- `favicon.svg`
- `icons.svg`
- built JS bundle
- built CSS bundle

These are outputs of source code, not the place to learn app logic first.

### `frontend/node_modules/`

Installed third-party packages.

Generated/vendor folder.

---

## 41. Exhaustive `frontend/src/`

### `frontend/src/main.jsx`

Code contents:

- import `createRoot`
- import global CSS
- import `App`
- render `App`

No custom named functions.

### `frontend/src/App.jsx`

Functions:

- `getAnalysisCount`
- `incrementAnalysisCount`
- `VisitorCounter`
- `NavBar`
- `Footer`
- `AnalysisView`
- default export `App`

#### `getAnalysisCount`

Purpose:

- read local client-side count from localStorage

#### `incrementAnalysisCount`

Purpose:

- increment and persist that count

#### `VisitorCounter`

Purpose:

- fetch backend `/health` and show total roasts delivered

#### `NavBar`

Purpose:

- top fixed app bar with logo, count, optional back button

#### `Footer`

Purpose:

- attribution and privacy note

#### `AnalysisView`

Purpose:

- switch between progress UI and final results based on streamed sections

#### `App`

Purpose:

- top-level page controller for landing vs analysis mode

### `frontend/src/App.css`

Contents:

- leftover starter/template CSS

Not central to current app path.

### `frontend/src/index.css`

Purpose:

- real global styling system

Contains:

- imported fonts
- CSS variables
- body and background effects
- component classes for dropzone, inputs, buttons, cards, terminal, copy button, nav, footer
- animation keyframes

No JS functions, but this file is still core to frontend behavior.

### `frontend/src/assets/hero.png`

Static image asset.

### `frontend/src/assets/react.svg`

Static asset.

### `frontend/src/assets/vite.svg`

Static asset.

### `frontend/src/data/`

Currently empty directory.

No files, no functions.

---

## 42. Exhaustive `frontend/src/lib/`

### `frontend/src/lib/api.js`

Functions:

- `sessionInit`
- `submitAnalysis`
- `getSessionState`
- `submitFollowup`
- `submitFeedback`
- `requestToken`
- `verifyToken`
- `createWebSocket`

#### `sessionInit`

Purpose:

- create backend session via JSON POST

#### `submitAnalysis`

Purpose:

- send multipart upload request with file and metadata

#### `getSessionState`

Purpose:

- polling fallback endpoint call

#### `submitFollowup`

Purpose:

- ask one section-specific follow-up question

#### `submitFeedback`

Purpose:

- send thumbs-up/down signal

#### `requestToken`

Purpose:

- request one-time unlock token by email

#### `verifyToken`

Purpose:

- submit token for unlock

#### `createWebSocket`

Purpose:

- build socket URL from current page origin and session ID

---

## 43. Exhaustive `frontend/src/hooks/`

### `frontend/src/hooks/useWebSocket.js`

Functions:

- `useWebSocket`

Already annotated above.

### `frontend/src/hooks/useInferenceToggle.js`

Functions:

- `useInferenceToggle`

Purpose:

- persist whether inference chains should be visible in review document

Flow:

- initialize state from localStorage
- write state back on changes
- return `[showInference, setShowInference]`

---

## 44. Exhaustive `frontend/src/components/`

### `frontend/src/components/SkeletonLoader.jsx`

Functions:

- `SkeletonLoader`

Purpose:

- render variable number of shimmering placeholder lines

Behavior:

- loops `lines` times
- last line is shorter for more realistic loading skeletons

### `frontend/src/components/DropZone.jsx`

Functions:

- `DropZone`

Purpose:

- standalone PDF drop/upload component

Behavior:

- validate PDF MIME type
- validate file size
- track drag state
- allow clear/remove

Important note:

- this component exists, but `LandingPage.jsx` currently uses its own inner `DropZone` implementation instead

### `frontend/src/components/MarketPulse.jsx`

Functions:

- `MarketPulse`

Purpose:

- render current market summary card

Behavior:

- show loading skeleton if still waiting
- read freshness label, breaking signal, skills, salary
- render a freshness badge and market summary blocks

### `frontend/src/components/Feedback.jsx`

Functions:

- `FeedbackButton`
- `ThirdAnalysisUnlock`

#### `FeedbackButton`

Purpose:

- capture one thumbs-up/down vote

Behavior:

- store vote state locally
- send feedback once
- thank user after voting

#### `ThirdAnalysisUnlock`

Purpose:

- email-entry UI for requesting extra analysis token

Behavior:

- manage input/loading/error/sent state
- call `requestToken`
- show success or error card

### `frontend/src/components/TLDRBlock.jsx`

Functions:

- `ShortlistBadge`
- `TLDRBlock`

#### `ShortlistBadge`

Purpose:

- infer badge color/label from shortlist-chance text

#### `TLDRBlock`

Purpose:

- render bottom-line verdict and copy shortcut

Behavior:

- copy formatted TLDR text to clipboard
- render shortlist chance, blocker, fix-first cards

### `frontend/src/components/LandingPage.jsx`

Functions:

- `RoastingOverlay`
- inner `DropZone`
- `AutoTextarea`
- `LandingPage`

Already covered conceptually above.

For completeness:

#### `RoastingOverlay`

Purpose:

- full-screen animated blocking state after submit

#### inner `DropZone`

Purpose:

- local file chooser/drop UI used by landing page

#### `AutoTextarea`

Purpose:

- auto-resize textarea to fit content up to max height

#### `LandingPage`

Purpose:

- full intake screen and upload flow controller

### `frontend/src/components/AnalysisProgress.jsx`

Functions:

- `AnalysisProgress`

Purpose:

- render progress state while backend analysis is running

Behavior:

- rotates status quotes
- polls recovery endpoint
- derives active step
- renders terminal-style progress card and progress bar

### `frontend/src/components/ResultsPage.jsx`

Functions:

- `Card`
- `SectionLabel`
- `PercentileBar`
- `CopyAllButton`
- `ResultsPage`

#### `Card`

Purpose:

- animated reusable content wrapper

#### `SectionLabel`

Purpose:

- lightweight section heading component

#### `PercentileBar`

Purpose:

- convert percentile text into visual bar plus confidence label

#### `CopyAllButton`

Purpose:

- build and copy formatted full review summary

#### `ResultsPage`

Purpose:

- top-level final results composition

### `frontend/src/components/ReviewDocument.jsx`

Functions:

- `parseContent`
- `parseActionPlan`
- `InferenceChain`
- `ActionSteps`
- `SectionContent`
- `Section`
- `ReviewDocument`

#### `parseContent`

Purpose:

- split prose into normal text vs recruiter inference-chain segments

#### `parseActionPlan`

Purpose:

- detect numbered action steps inside prose

#### `InferenceChain`

Purpose:

- render recruiter inference chain with visual distinction

#### `ActionSteps`

Purpose:

- render parsed action-plan list

#### `SectionContent`

Purpose:

- choose best rendering mode for one review section

#### `Section`

Purpose:

- collapsible review section with optional follow-up question support

#### `ReviewDocument`

Purpose:

- assemble all review sections and inference toggle

---

## 45. Frontend And Backend Trees: What Is Empty, Generated, Or Non-Logical

This is part of full completeness so nothing is left ambiguous.

### Backend empty marker files

- `backend/__init__.py`
- `backend/storage/__init__.py`
- `backend/routes/__init__.py`
- `backend/pipeline/__init__.py`
- `backend/retrieval/__init__.py`
- `backend/corpus/__init__.py`
- `backend/llm/__init__.py`
- `backend/agents/__init__.py`
- `backend/agents/prompts/__init__.py`

Purpose:

- package markers only

### Frontend directories with no handwritten logic

- `frontend/public/`
- `frontend/dist/`
- `frontend/node_modules/`
- `frontend/src/assets/`
- `frontend/src/data/` currently empty

Purpose:

- assets or generated artifacts, not app-control logic

---

## 46. If You Want The "Under Relevant Function" Reading Order For Backend/Frontend

Here is the strict reading order by runtime execution:

### Frontend first

1. `frontend/src/main.jsx`
2. `frontend/src/App.jsx`
3. `frontend/src/components/LandingPage.jsx`
4. `frontend/src/lib/api.js`
5. `backend/routes/session.py`
6. `backend/routes/analyse.py`
7. `backend/pdf_reader.py`
8. `backend/pipeline/orchestrator.py`
9. `backend/retrieval/dive.py`
10. `backend/agents/market_context_agent.py`
11. `backend/agents/red_flag_agent.py`
12. `backend/agents/six_second_agent.py`
13. `backend/agents/competitive_agent.py`
14. `backend/agents/technical_depth_agent.py`
15. `backend/agents/review_agent.py`
16. `backend/routes/websocket.py`
17. `backend/routes/ws_manager.py`
18. `frontend/src/hooks/useWebSocket.js`
19. `frontend/src/components/AnalysisProgress.jsx`
20. `frontend/src/components/ResultsPage.jsx`
21. `frontend/src/components/ReviewDocument.jsx`
22. `frontend/src/components/TLDRBlock.jsx`
23. `frontend/src/components/MarketPulse.jsx`
24. `frontend/src/components/Feedback.jsx`

That is the cleanest interview-study path across both trees.

---

## 47. Additional Annotated Backend Functions

This section continues the line-by-line style for the remaining backend functions that were previously only cataloged.

### 47.1 `backend/agents/market_context_agent.py -> parse_jd`

```python
async def parse_jd(jd_text: str, session_id: str = "") -> JDRequirements | None:
    if not jd_text or len(jd_text.strip()) < 50:
        return None  # Ignore missing or too-short JD text because it is not worth a model call.

    messages = [
        {"role": "system", "content": JD_PARSER_SYSTEM},  # System prompt defines exact JSON schema and extraction rules.
        {"role": "user", "content": f"Parse this job description:\n\n{jd_text[:2000]}"},
        # Truncate JD so prompt size stays controlled.
    ]

    try:
        text, _ = await call_groq_8b(
            messages, max_tokens=600, session_id=session_id, agent_name="jd_parser"
        )  # Use the cheap structured-output model path.

        if text.startswith("```"):
            text = text.split("```")[1]  # Strip fenced markdown block if model wrapped JSON.
            if text.startswith("json"):
                text = text[4:]  # Remove optional `json` code-fence language tag.
            text = text.strip()

        data = json.loads(text)  # Parse JSON into Python dict.
        return JDRequirements(**data)  # Validate and coerce into Pydantic model.

    except Exception as e:
        logger.error("jd_parse_failed", error=str(e), session_id=session_id)  # Observability, but no hard failure.
        return None  # JD parsing is optional, so failure degrades gracefully.
```

### 47.2 `backend/agents/market_context_agent.py -> run_market_context_agent`

```python
async def run_market_context_agent(
    distilled_context: str,
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    user_context: str = "",
    jd_requirements: JDRequirements | None = None,
    session_id: str = "",
) -> MarketContextOutput:
    task = MC_VERSIONS[MC_ACTIVE]  # Select active prompt version so prompt text is centrally switchable.

    system = build_system_prompt(
        role=role,
        company_type=company_type,
        market=market,
        experience_level=experience_level,
        agent_task=task,
        agent_output_rules="Return only valid JSON matching the schema above.",
    )  # Build common prompt shell with role/market calibration.

    jd_section = ""
    if jd_requirements:
        jd_section = f"\n\nJD REQUIREMENTS:\n{jd_requirements.model_dump_json(indent=2)}"
        # Include structured JD if available so market interpretation can align with target job.

    user_content = f"""MARKET INTELLIGENCE:
{distilled_context}

USER CONTEXT: {user_context or 'None provided'}
{jd_section}

Produce the MarketContextOutput JSON."""

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    try:
        text, meta = await call_groq_8b(
            messages, max_tokens=1000, temperature=0.1, session_id=session_id,
            agent_name="market_context_agent",
        )  # Low temperature because this should be calibration, not creative writing.

        data = extract_json(text)  # Robust parse helper for messy model output.

        if isinstance(data.get("format_expectations"), dict):
            data["format_expectations"] = json.dumps(data["format_expectations"])
            # Normalize weird model behavior where a string field came back as object.

        for field, default in [
            ("competitive_pool_description", "Competitive pool data unavailable"),
            ("market_norms", ""),
            ("format_expectations", ""),
            ("live_context_summary", ""),
        ]:
            if not data.get(field):
                data[field] = default  # Fill missing required strings with safe defaults.

        if not isinstance(data.get("red_flag_triggers"), list):
            data["red_flag_triggers"] = []  # Defend against schema drift.

        if not isinstance(data.get("weight_map"), dict):
            data["weight_map"] = {
                "dsa": 0.7, "projects": 0.7, "cgpa": 0.5,
                "experience": 0.7, "open_source": 0.4, "college_tier": 0.4
            }  # Conservative default weighting if model failed to produce one.

        if jd_requirements:
            data["jd_requirements"] = jd_requirements.model_dump()  # Carry parsed JD forward into final output object.

        output = MarketContextOutput(**data)  # Final schema validation boundary.
        return output

    except Exception as e:
        logger.error("market_context_agent_failed", error=str(e), session_id=session_id)
        return MarketContextOutput(
            market_norms=f"Standard {role} hiring norms for {market}",
            format_expectations="Standard resume format",
            competitive_pool_description="Competitive pool data unavailable",
            red_flag_triggers=[],
            weight_map={
                "dsa": 0.7, "projects": 0.7, "cgpa": 0.5,
                "experience": 0.7, "open_source": 0.4, "college_tier": 0.4
            },
            live_context_summary="Market intelligence unavailable for this analysis.",
            confidence="LOW",
        )  # Safe low-confidence fallback keeps rest of pipeline alive.
```

### 47.3 `backend/agents/red_flag_agent.py -> _passes_quality_gate`

```python
def _passes_quality_gate(flag: RedFlag) -> bool:
    if len(flag.location) < 10:
        return False  # Exact quoted evidence must be long enough to be meaningful.
    if len(flag.fix) < 20:
        return False  # Suggested fix must be concrete, not trivial.
    if len(flag.inference_chain) < 50:
        return False  # Recruiter reasoning must be detailed enough to be useful.
    chain_lower = flag.inference_chain.lower()
    generic_count = sum(1 for phrase in GENERIC_CHAIN_BLOCKLIST if phrase in chain_lower)
    return generic_count < 2  # Reject generic templated reasoning if too many banned phrases appear.
```

### 47.4 `backend/agents/red_flag_agent.py -> run_red_flag_agent`

```python
async def run_red_flag_agent(
    resume_text: str,
    market_context: MarketContextOutput,
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    user_context: str = "",
    jd_requirements: JDRequirements | None = None,
    profile_links: dict | None = None,
    session_id: str = "",
) -> RedFlagOutput:
    task = RF_VERSIONS[RF_ACTIVE]  # Pick the active prompt version.

    system = build_system_prompt(
        role=role,
        company_type=company_type,
        market=market,
        experience_level=experience_level,
        agent_task=task,
        agent_output_rules="Return only valid JSON with red_flags array and visual_scan_notes string.",
    )

    jd_section = ""
    if jd_requirements:
        jd_section = f"\n\nJD REQUIREMENTS (flag gaps as jd_gap: true):\n{jd_requirements.model_dump_json(indent=2)}"
        # Inject job-description context only if it exists.

    links_section = ""
    if profile_links:
        github = profile_links.get("github", "not found")
        linkedin = profile_links.get("linkedin", "not found")
        links_section = f"\n\nPROFILE LINKS:\nGitHub: {github}\nLinkedIn: {linkedin}"
        # Give model profile-link context because missing/weak links can be part of red-flag analysis.

    prompt = f"""{system}

RESUME TEXT:
{resume_text[:8000]}

MARKET RED FLAG TRIGGERS:
{chr(10).join(f'- {t}' for t in market_context.red_flag_triggers[:8])}

USER CONTEXT: {user_context or 'None provided'}
{jd_section}
{links_section}

Find all red flags and produce the JSON output."""

    text = None
    meta = {}
    try:
        text, meta = await call_red_flag_agent(
            prompt=prompt, max_tokens=2500, session_id=session_id,
        )  # Use specialized router path first.
    except Exception as primary_err:
        logger.warning("red_flag_primary_failed_falling_back", error=str(primary_err), session_id=session_id)
        try:
            text, meta = await call_groq_8b(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
                session_id=session_id,
            )  # Simpler fallback if main red-flag path fails.
        except Exception as groq_err:
            logger.error("red_flag_agent_all_failed", error=str(groq_err), session_id=session_id)
            return RedFlagOutput(red_flags=[], visual_scan_notes="")  # Degrade gracefully.

    try:
        data = extract_json(text)  # Parse model output.
        raw_flags = []
        for f in data.get("red_flags", []):
            try:
                raw_flags.append(RedFlag(**f))  # Validate each raw item individually.
            except Exception:
                continue  # Skip malformed flags instead of killing whole result.

        passed_flags = []
        for flag in raw_flags:
            if _passes_quality_gate(flag):
                passed_flags.append(flag)  # Keep only concrete, non-generic flags.
            else:
                logger.warning("red_flag_quality_gate_failed", flag=flag.flag[:50], session_id=session_id)

        return RedFlagOutput(
            red_flags=passed_flags,
            visual_scan_notes=data.get("visual_scan_notes", ""),
        )

    except Exception as e:
        logger.error("red_flag_agent_parse_failed", error=str(e), session_id=session_id)
        return RedFlagOutput(red_flags=[], visual_scan_notes="")  # Parsing failure becomes empty result, not crash.
```

### 47.5 `backend/agents/six_second_agent.py -> run_six_second_trajectory_agent`

```python
async def run_six_second_trajectory_agent(
    resume_text: str,
    market_context: MarketContextOutput,
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    user_context: str = "",
    profile_links: dict | None = None,
    session_id: str = "",
) -> SixSecondAndTrajectoryOutput:
    task = SS_VERSIONS[SS_ACTIVE]  # Active prompt version controls schema/instructions.

    system = build_system_prompt(
        role=role,
        company_type=company_type,
        market=market,
        experience_level=experience_level,
        agent_task=task,
        agent_output_rules="Return only valid JSON with all fields from both Part A and Part B.",
    )

    words = resume_text.split()  # Tokenize roughly by whitespace.
    first_200 = " ".join(words[:200])  # Build fast-scan subset for recruiter-impression simulation.

    links_section = ""
    if profile_links:
        github = profile_links.get("github", "not found")
        linkedin = profile_links.get("linkedin", "not found")
        links_section = f"\nGitHub URL: {github}\nLinkedIn URL: {linkedin}"

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"""FIRST 200 WORDS (for 6-second scan simulation):
{first_200}

FULL RESUME TEXT:
{resume_text[:8000]}

USER CONTEXT: {user_context or 'None provided'}
{links_section}

Produce the SixSecondAndTrajectory JSON output.""",
        },
    ]

    try:
        text, meta = await _call_agent(
            messages, max_tokens=1500, temperature=0.2, session_id=session_id
        )  # Use specialized router path for this agent family.

        if not text or not text.strip():
            raise ValueError("empty_response")  # Explicitly reject blank success responses.

        data = extract_json(text)

        gaps = [GapSignal(**g) for g in data.get("gaps", [])]  # Validate gap items using schema.
        data["gaps"] = [g.model_dump() for g in gaps]

        for field in [
            "fresher_note", "github_signal", "linkedin_signal",
            "progression_signal", "promotion_velocity", "skill_evolution",
            "career_story", "first_impression", "survived_cut_assessment"
        ]:
            if data.get(field) is None or data.get(field) == "":
                data[field] = data.get(field) or ""  # Normalize empty optional strings.

        return SixSecondAndTrajectoryOutput(**data)

    except Exception as e:
        logger.error("six_second_agent_failed", error=str(e), session_id=session_id)
        return SixSecondAndTrajectoryOutput(
            remembered=[], missed=[],
            first_impression="Analysis unavailable",
            survived_cut_assessment="MAYBE — analysis failed",
            career_story="", progression_signal="", gaps=[],
            promotion_velocity="", skill_evolution="",
            fresher_note="", github_signal="", linkedin_signal="",
        )  # Safe fallback object for downstream review synthesis.
```

### 47.6 `backend/agents/competitive_agent.py -> run_competitive_agent`

```python
async def run_competitive_agent(
    resume_text: str,
    market_context: MarketContextOutput,
    breaking_signal: str,
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    user_context: str = "",
    jd_requirements: JDRequirements | None = None,
    corpus_signals: list[dict] | None = None,
    combo_count: int = 0,
    session_id: str = "",
) -> CompetitiveOutput:
    task = CP_VERSIONS[CP_ACTIVE]  # Prompt version with percentile/CTC rules.

    system = build_system_prompt(
        role=role,
        company_type=company_type,
        market=market,
        experience_level=experience_level,
        agent_task=task,
        agent_output_rules="Return only valid JSON matching the schema.",
    )

    corpus_section = ""
    if corpus_signals and len(corpus_signals) >= 5:
        corpus_section = f"""
ANONYMISED CORPUS SIGNALS ({len(corpus_signals)} opted-in analyses for this combination):
{json.dumps(corpus_signals[:20], indent=2)}
Corpus size: {len(corpus_signals)} — use "calibrated" confidence if >= 30, else "estimated"
"""
        # Only include corpus if it is large enough to be meaningful.

    jd_section = ""
    if jd_requirements:
        jd_section = f"\n\nJD REQUIREMENTS:\n{jd_requirements.model_dump_json(indent=2)}"

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"""RESUME TEXT:
{resume_text[:3000]}

MARKET CONTEXT:
{market_context.competitive_pool_description}
{market_context.live_context_summary}

BREAKING SIGNAL (last 7 days):
{breaking_signal or 'No breaking signal available'}

USER CONTEXT: {user_context or 'None provided'}
{corpus_section}
{jd_section}

Produce the CompetitivePositioning JSON output.""",
        },
    ]

    try:
        text, meta = await _call_agent(
            messages, max_tokens=1000, temperature=0.2, session_id=session_id
        )

        data = extract_json(text)

        data.setdefault("strengths_vs_pool", [])  # Fill missing list fields.
        data.setdefault("weaknesses_vs_pool", [])
        data.setdefault("highest_leverage_change", "No specific recommendation available")
        data.setdefault("estimated_impact", "")
        data.setdefault("jd_fit_score", None)
        data.setdefault("expected_ctc_range", "")

        pe = data.get("percentile_estimate") or {}  # Defensive handling for nested object.
        pe_range = pe.get("range", "")
        if not pe_range or "unable" in pe_range.lower() or "cannot" in pe_range.lower():
            pe["range"] = "50th-60th percentile among fresher applicants (estimated)"
            # Product rule: always provide an estimate, never "unable to estimate".
        pe.setdefault("reasoning", "Estimated from market knowledge — limited corpus data for this combination")
        conf = pe.get("confidence", "estimated")
        pe["confidence"] = conf if conf in ("estimated", "calibrated") else "estimated"
        data["percentile_estimate"] = pe

        return CompetitiveOutput(**data)

    except Exception as e:
        logger.error("competitive_agent_failed", error=str(e), session_id=session_id)
        return CompetitiveOutput(
            strengths_vs_pool=[],
            weaknesses_vs_pool=[],
            percentile_estimate=PercentileEstimate(
                range="Unable to estimate",
                reasoning="Analysis failed",
                confidence="estimated",
            ),
            highest_leverage_change="Analysis unavailable",
            estimated_impact="",
            jd_fit_score=None,
        )
```

### 47.7 `backend/agents/followup_agent.py`

```python
def _followup_key(session_id: str, section: str) -> str:
    return f"followup:{session_id}:{section}"  # Centralized Redis key format for follow-up usage tracking.


def has_used_followup(session_id: str, section: str) -> bool:
    return redis.exists(_followup_key(session_id, section)) == 1  # Redis existence check becomes boolean policy.


def mark_followup_used(session_id: str, section: str) -> None:
    redis.setex(_followup_key(session_id, section), FOLLOWUP_TTL, "1")  # One-hour one-use marker.


async def run_followup_agent(
    question: str,
    section: str,
    resume_text: str,
    review_summary: str,
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    session_id: str = "",
) -> FollowUpOutput:
    task = FU_VERSIONS[FU_ACTIVE]  # Load active follow-up prompt text.

    system = f"""You are an expert resume analyst for {role} roles at {company_type} in {market}.
{task}"""  # Lightweight system prompt instead of full shared template.

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"""RESUME SUMMARY:
{resume_text[:1500]}

REVIEW CONTEXT:
{review_summary[:800]}

SECTION: {section}
QUESTION: {question}

Answer in 100-200 words.""",
        },
    ]

    try:
        text, meta = await call_groq_8b(
            messages, max_tokens=300, temperature=0.3, session_id=session_id
        )  # Small targeted answer path.
        return FollowUpOutput(answer=text.strip())
    except Exception as e:
        logger.error("followup_agent_failed", error=str(e), session_id=session_id)
        return FollowUpOutput(answer="Unable to load answer. Please try again.")
```

### 47.8 `backend/routes/session.py`

```python
class SessionInitRequest(BaseModel):
    role: str  # Target role selected by user.
    market: str  # Geography/market selected by user.
    company_type: str  # Hiring context selected by user.
    experience_level: str = "Junior"  # Default if caller omits it.


class SessionInitResponse(BaseModel):
    session_id: str  # Newly created Redis session ID.
    message: str  # Human-readable next-step message.


@router.post("/session-init", response_model=SessionInitResponse)
def session_init(body: SessionInitRequest):
    session = create_session(body.role, body.market, body.company_type, body.experience_level)
    return SessionInitResponse(
        session_id=session["session_id"],  # Echo newly created ID back to frontend.
        message="Session created. You may now upload your resume.",
    )


@router.get("/session/{session_id}")
def get_session_route(session_id: str):
    session = redis_get_session(session_id)  # Pull raw session object from Redis wrapper.
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")  # Clear contract for missing sessions.
    return session  # Return stored session JSON as-is.
```

### 47.9 `backend/routes/websocket.py`

```python
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await connect(session_id, websocket)  # Accept socket and register it in connection map.
    heartbeat_task = asyncio.create_task(heartbeat_loop(session_id))  # Keep connection alive with pings.

    try:
        completed = _get_completed_sections(session_id)  # Recover already-finished sections for reconnects.
        for section, data in completed.items():
            await websocket.send_text(json.dumps({
                "event": "section_complete",
                "data": {"section": section, "result": data}
            }))  # Replay each completed section immediately.

        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)  # Wait for pong or other messages.
                if msg == "pong":
                    continue  # Heartbeat acknowledgment only.
            except asyncio.TimeoutError:
                session = get_session(session_id)  # If silent, ask Redis whether job is still active.
                if session and session.get("status") in ("completed", "failed"):
                    break  # Stop loop if backend job is finished and no more live updates are needed.
                continue

    except WebSocketDisconnect:
        pass  # Normal client disconnect path.
    finally:
        heartbeat_task.cancel()  # Cleanup background ping task.
        disconnect(session_id)  # Remove connection from manager.
```

```python
@router.get("/session/{session_id}/state")
async def session_state(session_id: str):
    session = get_session(session_id)  # Load canonical session state.
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    status = session.get("status", "pending")  # Defensive default.
    completed = _get_completed_sections(session_id)  # Load streamed sections from Redis.

    all_sections = ["market_context", "red_flags", "six_second", "competitive", "technical_depth", "review"]
    pending = [s for s in all_sections if s not in completed]  # Derive remaining work for recovery UI.

    return {
        "status": status,
        "completed": list(completed.keys()),
        "pending": pending,
        "results": completed,
    }
```

```python
@router.get("/share/{session_id}")
async def share_preview(session_id: str):
    share_key = f"share:{session_id}:tldr"  # Public-share cache key.
    cached = redis.get(share_key)
    if cached:
        return json.loads(cached)  # Reuse cached preview if present.

    review_raw = redis.get(f"session:{session_id}:review")  # Read full review payload from Redis.
    if not review_raw:
        raise HTTPException(status_code=404, detail="Share preview not found or expired.")

    review = json.loads(review_raw)
    session = get_session(session_id)

    tldr = {
        "shortlist_chance": review.get("tldr_shortlist_chance", ""),
        "biggest_blocker": review.get("tldr_biggest_blocker", ""),
        "fix_first": review.get("tldr_fix_first", ""),
        "role": session.get("role", "") if session else "",
        "market": session.get("market", "") if session else "",
    }  # Only expose low-risk public-safe fields.

    redis.setex(share_key, SHARE_TTL, json.dumps(tldr))  # Cache preview for 7 days.
    redis.incr("counter:share_previews_viewed")  # Track preview traffic.

    return tldr
```

```python
def _get_completed_sections(session_id: str) -> dict:
    sections = ["market_context", "red_flags", "six_second", "competitive", "technical_depth", "review"]
    completed = {}
    for section in sections:
        raw = redis.get(f"session:{session_id}:{section}")  # Load one section by deterministic key.
        if raw:
            try:
                completed[section] = json.loads(raw)  # Decode JSON payload if valid.
            except Exception:
                pass  # Ignore corrupted section instead of failing entire recovery response.
    return completed
```

### 47.10 `backend/routes/ws_manager.py`

```python
async def connect(session_id: str, websocket: WebSocket) -> None:
    await websocket.accept()  # Finish WebSocket handshake.
    _connections[session_id] = websocket  # Register this socket under session ID.
    logger.info("ws_connected", session_id=session_id)


def disconnect(session_id: str) -> None:
    _connections.pop(session_id, None)  # Remove active connection if present.
    logger.info("ws_disconnected", session_id=session_id)


async def emit(session_id: str, event: str, data: dict) -> None:
    ws = _connections.get(session_id)  # Find active socket for this session.
    if ws is None:
        return  # Silent no-op because polling fallback can recover.

    try:
        await ws.send_text(json.dumps({"event": event, "data": data}))  # Standardize outbound event envelope.
    except Exception:
        disconnect(session_id)  # Drop broken socket on send failure.


async def heartbeat_loop(session_id: str, interval: int = 10) -> None:
    while session_id in _connections:  # Run only while socket still registered.
        await asyncio.sleep(interval)  # Wait between pings.
        ws = _connections.get(session_id)
        if ws is None:
            break
        try:
            await ws.send_text(json.dumps({"event": "ping"}))  # Keep connection alive and detectable.
        except Exception:
            disconnect(session_id)
            break
```

### 47.11 `backend/routes/token_feedback.py`

```python
@router.post("/token")
async def request_token(body: TokenRequest):
    email = body.email.strip().lower()  # Normalize input to avoid duplicate variants.

    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Invalid email address.")  # Reject malformed email before any provider usage.

    email_key = f"token:email:{email}"
    if redis.exists(email_key):
        raise HTTPException(
            status_code=429,
            detail="A token was already sent to this email today. Check your inbox."
        )  # One send per email per day.

    token = str(uuid.uuid4())  # Generate one-time unlock token.
    token_key = f"token:{token}"

    redis.setex(token_key, TOKEN_TTL, email)  # Store token -> email mapping.
    redis.setex(email_key, TOKEN_TTL, "1")  # Store email-used flag.

    if not RESEND_API_KEY:
        logger.info("dev_token", token=token, email=email)
        return {"message": "Dev mode: no email sent.", "dev_token": token}  # Local-dev shortcut path.

    sent = await _send_token_email(email, token)
    if not sent:
        redis.delete(token_key)  # Roll back Redis state if send failed.
        redis.delete(email_key)
        raise HTTPException(status_code=500, detail="Failed to send email. Please try again.")

    return {"message": "Token sent. Check your email."}
```

```python
@router.post("/token/verify")
async def verify_token(body: TokenVerifyRequest):
    token_key = f"token:{body.token}"
    email = redis.get(token_key)  # Look up token.

    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")

    redis.delete(token_key)  # Immediate one-time-use semantics.
    redis.setex(f"token_unlocked:{body.session_id}", TOKEN_TTL, email)  # Grant one future bypass for this session.

    return {"message": "Token verified. You have one more analysis available."}
```

```python
async def _send_token_email(email: str, token: str) -> bool:
    if not RESEND_API_KEY:
        logger.info("dev_token", token=token, email=email)
        return True  # Dev shortcut.

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "ROAST <onboarding@resend.dev>",
                    "to": [email],
                    "subject": "Your ROAST token",
                    "html": f"""...{token}...""",
                },
            )  # Plain provider call with inline HTML body.
            return response.status_code == 200  # Simple success criterion.
    except Exception as e:
        logger.error("resend_failed", error=str(e))
        return False
```

```python
@router.post("/feedback")
async def feedback(body: FeedbackRequest):
    if body.useful:
        redis.incr("counter:feedback_useful")  # Global positive count.
    else:
        redis.incr("counter:feedback_not_useful")  # Global negative count.

    combo_key = f"feedback:{body.role}:{body.company_type}:{body.market}"  # Per-combination quality monitoring.
    if body.useful:
        redis.incr(f"{combo_key}:useful")
    else:
        redis.incr(f"{combo_key}:not_useful")

    try:
        from backend.llm.langfuse_client import trace_feedback
        trace_feedback(session_id=body.session_id, useful=body.useful)  # Best-effort observability link.
    except Exception:
        pass

    return {"message": "Thanks for the feedback."}
```

### 47.12 `backend/agents/json_utils.py`

```python
def extract_json(text: str) -> dict:
    if "</think>" in text:
        text = text[text.index("</think>") + len("</think>"):].strip()  # Remove qwen thinking preamble if present.

    code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if code_block:
        text = code_block.group(1).strip()  # Extract fenced JSON body only.

    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]  # Heuristic crop to outermost JSON object.

    try:
        return json.loads(text)  # Fast path if output is already valid.
    except json.JSONDecodeError:
        pass

    try:
        from json_repair import repair_json
        repaired = repair_json(text, return_objects=True)  # Attempt recovery from malformed JSON.
        if isinstance(repaired, dict):
            return repaired
    except Exception:
        pass

    return json.loads(text)  # Final raise path preserves original JSON error if all else fails.
```

### 47.13 `backend/agents/tech_search.py`

```python
async def lookup_technology(tech_name: str, context: str = "") -> str:
    query = f"{tech_name} {context} technical explanation what is it used for".strip()
    # Build focused search query instead of sending raw term.

    try:
        results = await asyncio.to_thread(_ddg_search, query)  # Run blocking DDG call off event loop.
        if not results:
            return ""

        snippets = [r.get("body", "") for r in results[:2] if r.get("body")]  # Take short snippets from top hits.
        combined = " ".join(snippets)[:500]  # Keep output compact for LLM context.
        return combined

    except Exception as e:
        logger.warning("tech_lookup_failed", tech=tech_name, error=str(e))
        return ""  # Lookup failure should never crash agent flow.
```

```python
def _ddg_search(query: str) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=3))  # Small result set because this is just a helper signal, not full research.
```

```python
async def lookup_multiple(technologies: list[str], context: str = "") -> dict[str, str]:
    tasks = [lookup_technology(tech, context) for tech in technologies]  # Build async lookups.
    results = await asyncio.gather(*tasks, return_exceptions=True)  # Run in parallel, tolerate individual failures.

    return {
        tech: (result if isinstance(result, str) else "")
        for tech, result in zip(technologies, results)
    }  # Keep ordering aligned with inputs.
```

---

## 48. Additional Annotated Frontend Functions

### 48.1 `frontend/src/hooks/useInferenceToggle.js`

```javascript
export function useInferenceToggle() {
  const [showInference, setShowInference] = useState(() => {
    return localStorage.getItem('roast_inference_toggle') !== 'off'
    // Default is ON unless localStorage explicitly says OFF.
  })

  useEffect(() => {
    localStorage.setItem('roast_inference_toggle', showInference ? 'on' : 'off')
    // Persist preference whenever user toggles it.
  }, [showInference])

  return [showInference, setShowInference] // Custom hook returns state pair like built-in hooks do.
}
```

### 48.2 `frontend/src/App.jsx`

```javascript
function getAnalysisCount() {
  return parseInt(localStorage.getItem('roast_analysis_count') || '0')
  // Read local analysis counter and convert string -> number.
}

function incrementAnalysisCount() {
  const count = getAnalysisCount() + 1 // Compute next value.
  localStorage.setItem('roast_analysis_count', count) // Persist it.
  return count // Return new count for caller convenience.
}
```

```javascript
function VisitorCounter() {
  const [count, setCount] = useState(null) // Unknown until backend responds.

  useEffect(() => {
    fetch('/health')
      .then(r => r.json()) // Backend health route returns JSON object.
      .then(d => {
        if (d.total_analyses) setCount(d.total_analyses) // Show count only if backend supplies it.
      })
      .catch(() => {}) // Silent failure because counter is decorative, not critical.
  }, [])

  if (!count) return null // Hide entire badge if no count available.

  return (
    <div className="visitor-badge">
      <span className="visitor-dot" />
      <span>{count.toLocaleString()} roasts delivered</span>
    </div>
  )
}
```

```javascript
function AnalysisView({ sessionId, meta }) {
  const { sections, status } = useWebSocket(sessionId) // Central live-results hook.

  if (status === 'complete' || sections.review) {
    return (
      <ResultsPage
        sections={sections}
        sessionId={sessionId}
        meta={meta}
        analysisCount={getAnalysisCount()}
      />
    ) // Switch to final results when review is ready or socket says complete.
  }

  return <AnalysisProgress sessionId={sessionId} sections={sections} /> // Otherwise keep showing progress UI.
}
```

```javascript
export default function App() {
  const [view, setView] = useState('landing') // Top-level page mode.
  const [sessionId, setSessionId] = useState(null) // Active backend session.
  const [meta, setMeta] = useState(null) // Selected role/company/market metadata for results header.

  const handleAnalysisStarted = (sid, metaData) => {
    incrementAnalysisCount() // Local client-side count bump.
    setSessionId(sid) // Save session for socket/results flow.
    setMeta(metaData) // Save header metadata.
    setView('analysis') // Switch from landing to progress/results mode.
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--roast-bg)', color: 'var(--roast-text)' }}>
      <div className="bg-mesh" /> {/* Global atmospheric background layer */}

      <NavBar view={view} onBack={() => setView('landing')} /> {/* Back button appears only in analysis view */}

      <div className="pt-[52px]"> {/* Push page below fixed navbar */}
        <AnimatePresence mode="wait">
          {view === 'landing' && (
            <motion.div key="landing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
              <LandingPage onAnalysisStarted={handleAnalysisStarted} />
              <Footer />
            </motion.div>
          )}

          {view === 'analysis' && (
            <motion.div key="analysis" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
              <AnalysisView sessionId={sessionId} meta={meta} />
              <Footer />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
```

### 48.3 `frontend/src/components/SkeletonLoader.jsx`

```javascript
export function SkeletonLoader({ lines = 3, className = '' }) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton h-4 rounded"
          style={{ width: i === lines - 1 ? '60%' : '100%' }}
          // Make final line shorter so loading block feels more like real text.
        />
      ))}
    </div>
  )
}
```

### 48.4 `frontend/src/components/DropZone.jsx`

```javascript
export function DropZone({ onFile }) {
  const [file, setFile] = useState(null) // Track selected PDF.
  const [dragging, setDragging] = useState(false) // Track drag-hover state for styling.
  const inputRef = useRef() // Hidden file input reference.

  const handleFile = (f) => {
    if (!f || f.type !== 'application/pdf') return // Ignore non-PDF selections.
    if (f.size > 5 * 1024 * 1024) {
      alert('File too large. Max 5MB.') // Client-side guard before upload.
      return
    }
    setFile(f) // Save selected file locally.
    onFile(f) // Notify parent component.
  }

  const handleDrop = (e) => {
    e.preventDefault() // Prevent browser from opening file.
    setDragging(false) // End drag state.
    handleFile(e.dataTransfer.files[0]) // Use first dropped file.
  }

  const clear = (e) => {
    e.stopPropagation() // Prevent outer click behavior.
    setFile(null) // Remove local file.
    onFile(null) // Inform parent.
    inputRef.current.value = '' // Reset native file input so same file can be re-selected.
  }
```

The render part:

- animates border when idle
- changes classes when dragging
- opens file picker on click if no file is selected
- shows either file summary row or upload prompt

### 48.5 `frontend/src/components/MarketPulse.jsx`

```javascript
export function MarketPulse({ marketContext, fullContext, loading }) {
  if (loading) return (
    <div className="space-y-3">
      <h2 className="text-xs font-semibold text-[--roast-muted] uppercase tracking-wider">Market Pulse</h2>
      <SkeletonLoader lines={4} />
    </div>
  ) // Placeholder while waiting for streamed market section.

  if (!marketContext) return null // Hide entirely if no market data exists.

  const freshness = fullContext?.distilled?.freshness_label || 'Current'
  const breaking = fullContext?.breaking_signal
  const breakingAvailable = fullContext?.breaking_available
  const skills = fullContext?.distilled?.top_required_skills?.slice(0, 5) || []
  const salary = fullContext?.distilled?.salary_band || 'data unavailable'
  // Normalize values from backend shape and clip skills list for UI readability.
```

The render then:

- shows freshness badge
- sentiment summary
- salary band
- top skills
- short competitive-pool snippet
- breaking signal notice

### 48.6 `frontend/src/components/Feedback.jsx`

```javascript
export function FeedbackButton({ sessionId, role, market, companyType }) {
  const [voted, setVoted] = useState(null) // null = not voted, boolean = chosen side.

  const vote = async (useful) => {
    if (voted) return // Enforce one vote client-side.
    setVoted(useful) // Update UI immediately.
    await submitFeedback({ sessionId, useful, role, market, company_type: companyType })
    // Fire backend feedback request.
  }
```

If already voted:

- show thank-you text

Else:

- render thumbs-up/down buttons

```javascript
export function ThirdAnalysisUnlock() {
  const [email, setEmail] = useState('') // Form input.
  const [sent, setSent] = useState(false) // Success state.
  const [loading, setLoading] = useState(false) // Request state.
  const [error, setError] = useState('') // Error message state.

  const send = async () => {
    if (!email || loading) return // Prevent empty or duplicate submission.
    setLoading(true)
    setError('')
    try {
      await requestToken(email) // Ask backend to generate/send unlock token.
      setSent(true) // Switch to success card.
    } catch (e) {
      setError(e.message || 'Failed to send token.') // Surface backend error.
    }
    setLoading(false)
  }
```

### 48.7 `frontend/src/components/TLDRBlock.jsx`

```javascript
function ShortlistBadge({ text }) {
  const lower = text.toLowerCase() // Normalize for keyword matching.
  let color, label, dot
  if (lower.includes('strong') || lower.includes('high') || lower.includes('top') || lower.includes('clears')) {
    color = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25'
    dot = 'bg-emerald-400'
    label = 'Strong' // Positive verdict styling.
  } else if (lower.includes('low') || lower.includes('weak') || lower.includes('below') || lower.includes('struggle')) {
    color = 'bg-red-500/15 text-red-400 border-red-500/25'
    dot = 'bg-red-400'
    label = 'Low' // Negative verdict styling.
  } else {
    color = 'bg-yellow-500/15 text-yellow-400 border-yellow-500/25'
    dot = 'bg-yellow-400'
    label = 'Medium' // Neutral fallback.
  }
```

```javascript
export function TLDRBlock({ review }) {
  const [copied, setCopied] = useState(false) // Clipboard feedback state.

  const copy = () => {
    const text = `ROAST RESULTS\n\nShortlist chance: ${review.tldr_shortlist_chance}\nBiggest blocker: ${review.tldr_biggest_blocker}\nFix first: ${review.tldr_fix_first}`
    navigator.clipboard.writeText(text) // Copy concise verdict payload.
    setCopied(true)
    setTimeout(() => setCopied(false), 2000) // Reset icon state after short delay.
  }
```

The render then:

- shows heading row
- badge
- copy button
- shortlist summary card
- blocker card
- fix-first card

### 48.8 `frontend/src/components/ResultsPage.jsx`

```javascript
function Card({ children, delay = 0, className = '' }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} // Enter animation starting state.
      animate={{ opacity: 1, y: 0 }} // End animation state.
      transition={{ duration: 0.45, delay, ease: [0.22, 1, 0.36, 1] }}
      className={`roast-card ${className}`}
    >
      {children}
    </motion.div>
  )
}
```

```javascript
function SectionLabel({ children }) {
  return <div className="section-label">{children}</div> // Small visual heading helper.
}
```

```javascript
function PercentileBar({ range, confidence }) {
  const match = range?.match(/(\d+)(?:th|st|nd|rd)[–\-](\d+)/) // Match range like 60th-70th percentile.
  const single = range?.match(/(\d+)(?:th|st|nd|rd)\s*percentile/) // Match single percentile form.
  let pct = 50 // Default visual midpoint.
  if (match) pct = (parseInt(match[1]) + parseInt(match[2])) / 2 // Average range endpoints.
  else if (single) pct = parseInt(single[1]) // Use single value directly.

  const numericMatch = range?.match(/^([\d\w\-–]+(?:th|st|nd|rd))/) // Separate highlighted numeric prefix from text suffix.
  const numericPart = numericMatch ? numericMatch[0] : range
  const labelPart = numericMatch ? range?.slice(numericPart.length) : ''

  const confidenceLabel = confidence === 'calibrated'
    ? 'Based on real applicant data'
    : 'Estimated from market signals' // Human explanation for confidence mode.
```

```javascript
function CopyAllButton({ review, competitive, marketContext }) {
  const [copied, setCopied] = useState(false)

  const copyAll = () => {
    if (!review) return // Nothing to copy if review not ready.
    const lines = [
      '🔥 ROAST RESULTS',
      '═'.repeat(50),
      '',
      'BOTTOM LINE',
      `Shortlist chance: ${review.tldr_shortlist_chance}`,
      `Biggest blocker: ${review.tldr_biggest_blocker}`,
      `Fix first: ${review.tldr_fix_first}`,
      '',
      competitive ? `WHERE YOU STAND\n${competitive.percentile_estimate?.range}` : '',
      '',
      "WHAT'S WORKING",
      review.whats_working_section,
      '',
      "WHAT'S HURTING YOU",
      review.whats_hurting_section,
      '',
      'CAREER STORY',
      review.career_story_section,
      '',
      'COMPETITIVE POSITION',
      review.competitive_position_section,
      '',
      'ACTION PLAN',
      review.action_plan_section,
      review.jd_alignment_section ? `\nJD ALIGNMENT\n${review.jd_alignment_section}` : '',
      '',
      '─'.repeat(50),
      'Generated by ROAST — roast.dev',
    ].filter(Boolean).join('\n') // Assemble readable export text and drop empty sections.

    navigator.clipboard.writeText(lines)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }
```

```javascript
export function ResultsPage({ sections, sessionId, meta, analysisCount }) {
  const review = sections.review // Final prose review.
  const marketContext = sections.market_context // Calibration/market summary.
  const competitive = sections.competitive // Percentile and CTC section.

  return (
    <div className="min-h-screen px-4 py-8 sm:py-12 relative z-10">
      <div className="max-w-2xl mx-auto space-y-5">
        {/* Then compose header, TLDR, MarketPulse, ReviewDocument, competitive card, token unlock, feedback */}
      </div>
    </div>
  )
}
```

### 48.9 `frontend/src/components/ReviewDocument.jsx`

```javascript
function parseContent(text) {
  if (!text) return [] // No content means no segments.
  const segments = []
  const lines = text.split(/\n+/) // Split prose into logical display lines.
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    if ((trimmed.includes('→') || trimmed.includes('->')) &&
        (trimmed.toLowerCase().includes('recruiter') || trimmed.toLowerCase().includes('sees') || trimmed.toLowerCase().includes('assumes'))) {
      segments.push({ type: 'chain', content: trimmed }) // Special rendering for inference chains.
    } else {
      segments.push({ type: 'text', content: trimmed }) // Normal paragraph line.
    }
  }
  return segments
}
```

```javascript
function parseActionPlan(text) {
  if (!text) return null
  const stepPattern = /(?:^|\n)\s*(?:\d+[\.\)]|Step\s+\d+:?)\s+/gm // Heuristic for numbered steps.
  const hasSteps = stepPattern.test(text)
  if (!hasSteps) return null // If prose is not step-like, fall back to normal paragraph rendering.

  const steps = text
    .split(/\n/)
    .map(l => l.trim())
    .filter(Boolean)
    .reduce((acc, line) => {
      if (/^\d+[\.\)]\s+/.test(line) || /^Step\s+\d+/i.test(line)) {
        acc.push(line.replace(/^\d+[\.\)]\s+/, '').replace(/^Step\s+\d+:?\s*/i, ''))
        // Start a new action step.
      } else if (acc.length > 0) {
        acc[acc.length - 1] += ' ' + line // Continue previous step with wrapped text.
      } else {
        acc.push(line) // Fallback if text began without explicit numbering.
      }
      return acc
    }, [])

  return steps.length >= 2 ? steps : null // Only treat as step list if parsing found enough structure.
}
```

```javascript
function SectionContent({ content, configKey, showInference }) {
  const isAction = configKey === 'action'
  const isHurting = configKey === 'hurting'

  if (isAction) {
    const steps = parseActionPlan(content)
    if (steps) return <ActionSteps steps={steps} /> // Prefer structured rendering for action plan.
  }

  if (isHurting && showInference) {
    const segments = parseContent(content)
    return (
      <div>
        {segments.map((seg, i) => (
          seg.type === 'chain'
            ? <InferenceChain key={i} content={seg.content} />
            : <p key={i} className="text-sm text-[--roast-text-2] leading-[1.8] mb-2">{seg.content}</p>
        ))}
      </div>
    ) // Show recruiter inference chains visually when toggle is ON.
  }

  return <p className="text-sm text-[--roast-text-2] leading-[1.8] whitespace-pre-wrap">{content}</p> // Normal prose fallback.
}
```

```javascript
function Section({ title, content, followups, sessionId, sectionKey, configKey, showInference, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen) // Collapsed/expanded state.
  const [usedFollowup, setUsedFollowup] = useState(false) // One follow-up per section.
  const [activeQuestion, setActiveQuestion] = useState(null) // Which clicked question is active.
  const [answer, setAnswer] = useState('') // Returned follow-up answer.
  const [loadingAnswer, setLoadingAnswer] = useState(false) // Follow-up loading state.
  const cfg = SECTION_CONFIG[configKey] || SECTION_CONFIG.action // Visual styling selection.
  const Icon = cfg.icon

  const handleFollowup = async (question) => {
    if (usedFollowup) return // Guard against duplicate use.
    setActiveQuestion(question)
    setLoadingAnswer(true)
    try {
      const res = await submitFollowup({ sessionId, section: sectionKey, question })
      setAnswer(res.answer) // Store returned explanation.
      setUsedFollowup(true) // Lock section after success.
    } catch {
      setAnswer('Unable to load answer. Please try again.')
    }
    setLoadingAnswer(false)
  }
```

```javascript
export function ReviewDocument({ review, sessionId, loading }) {
  const [showInference, setShowInference] = useInferenceToggle() // User preference for chain rendering.

  if (loading) return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-1">
        <div className="section-label">The Review</div>
      </div>
      <SkeletonLoader lines={8} />
    </div>
  ) // Loading placeholder path.

  if (!review) return null // Hide entire component if no review exists.

  return (
    <div className="space-y-2.5">
      {/* Renders section header, inference toggle, then all review sections in order */}
    </div>
  )
}
```

### 48.10 `frontend/src/components/AnalysisProgress.jsx`

```javascript
export function AnalysisProgress({ sessionId, sections }) {
  const [step, setStep] = useState(1) // State driven by polling endpoint.
  const [quoteIdx, setQuoteIdx] = useState(0) // Rotating flavor text index.

  useEffect(() => {
    const q = setInterval(() => setQuoteIdx(i => (i + 1) % ROAST_QUOTES.length), 3000)
    return () => clearInterval(q) // Rotate messages every 3 seconds.
  }, [])

  useEffect(() => {
    if (!sessionId) return
    const poll = setInterval(async () => {
      try {
        const state = await getSessionState(sessionId) // Poll recovery endpoint.
        const completed = state.completed || []
        if (completed.includes('review')) setStep(8)
        else if (completed.includes('technical_depth')) setStep(7)
        else if (completed.includes('competitive')) setStep(6)
        else if (completed.includes('six_second')) setStep(5)
        else if (completed.includes('red_flags')) setStep(4)
        else if (completed.includes('market_context')) setStep(3)
        else setStep(2) // Map completed section set to a human step number.
        if (state.status === 'completed') clearInterval(poll) // Stop polling once backend says done.
      } catch { /* ignore */ }
    }, 3000)
    return () => clearInterval(poll)
  }, [sessionId])

  const sectionsStep = sections?.review ? 8
    : sections?.technical_depth ? 7
    : sections?.competitive ? 6
    : sections?.six_second ? 5
    : sections?.red_flags ? 4
    : sections?.market_context ? 3
    : 0
  // Derive progress from streamed sections too, so UI advances even before polling catches up.

  const activeStep = Math.max(step, sectionsStep) // Choose furthest-known progress source.
  const pct = Math.round((activeStep / STEPS.length) * 100) // Convert step index into percentage.
```

The render then:

- shows animated flame icon
- rotates status quotes
- shows terminal-style completed/current steps
- shows progress bar and estimated remaining seconds

This file is mostly state derivation plus UI feedback.

## 49. More Literal Annotations For Remaining Backend/Frontend Runtime Files

This section continues the same style, but now focuses on the files that glue the system together:

- FastAPI app boot and SPA serving
- rate limiting
- monthly cron refresh
- LLM routing / fallback strategy
- Groq transport wrapper
- circuit breaker behavior
- technical-depth agent loop and fallback
- remaining frontend API transport helpers
- the remaining `ReviewDocument` helper components

These are the files that interviewers often ask about because they show:

- how the app starts
- how failure is contained
- how external APIs are wrapped
- how frontend and backend are connected

### 49.1 `backend/main.py`

Read this file as: "build the FastAPI app, attach middleware, attach routers, then optionally serve the compiled frontend."

```python
from fastapi import FastAPI                              # Main web framework object.
from fastapi.middleware.cors import CORSMiddleware      # Browser cross-origin control.
from fastapi.staticfiles import StaticFiles             # Serves built frontend assets.
from fastapi.responses import FileResponse, Response    # Return files or raw text responses.
from pathlib import Path                                # Safe filesystem path building.
import os                                               # Imported for environment/file use.

from backend.routes.analyse import router as analyse_router            # Resume analysis API.
from backend.routes.session import router as session_router            # Session-init API.
from backend.routes.followup import router as followup_router          # Follow-up question API.
from backend.routes.websocket import router as websocket_router        # WebSocket + recovery APIs.
from backend.routes.cron import router as cron_router                  # Monthly refresh endpoint.
from backend.routes.token_feedback import router as token_feedback_router  # Token unlock + feedback.
from backend.config import ENVIRONMENT, ALLOWED_ORIGINS               # Runtime config values.

app = FastAPI(                                           # Create the application instance.
    title="ROAST",                                       # Name shown in OpenAPI docs.
    description="Market-aware AI resume critic",         # High-level service description.
    version="0.1.0",                                     # App version metadata.
    docs_url="/docs" if ENVIRONMENT != "production" else None,   # Hide docs in prod.
    redoc_url="/redoc" if ENVIRONMENT != "production" else None, # Hide ReDoc in prod.
)

app.add_middleware(                                      # Install CORS middleware.
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,                       # Which frontend origins may call this API.
    allow_credentials=True if ALLOWED_ORIGINS != ["*"] else False, # Cookies/credentials only when safe.
    allow_methods=["GET", "POST"],                       # API intentionally keeps a narrow method surface.
    allow_headers=["*"],                                 # Permit normal browser request headers.
)

app.include_router(session_router, prefix="/api")        # POST /api/session-init
app.include_router(analyse_router, prefix="/api")        # POST /api/analyse
app.include_router(followup_router, prefix="/api")       # POST /api/followup
app.include_router(websocket_router, prefix="/api")      # WS + session state + share preview
app.include_router(cron_router)                          # /refresh-market-intel is mounted at root
app.include_router(token_feedback_router, prefix="/api") # token + feedback endpoints

@app.get("/health")
def health_check():
    from backend.storage.redis_client import redis       # Imported inside function to keep startup simple.
    total = redis.get("counter:total_analyses")          # Reads a global analysis counter from Redis.
    return {
        "status": "ok",                                  # Liveness signal.
        "service": "roast",                              # Service name for dashboards.
        "total_analyses": int(total) if total else 0,   # Convert Redis string/None into integer.
    }

@app.get("/robots.txt", response_class=Response)
def robots():
    from fastapi.responses import Response               # Re-imported locally, though top import already exists.
    return Response(
        content="User-agent: *\nDisallow: /api/\nAllow: /\n",  # Ask crawlers not to index API paths.
        media_type="text/plain"
    )

_dist = Path(__file__).parent.parent / "frontend" / "dist"  # Location of built frontend bundle.
if _dist.exists():                                          # Only mount static frontend if bundle is present.
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/favicon.svg")
    def favicon():
        return FileResponse(str(_dist / "favicon.svg"))     # Serve built favicon directly.

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("ws/") or full_path == "health":
            from fastapi import HTTPException                # Avoid stealing backend routes.
            raise HTTPException(status_code=404)
        return FileResponse(str(_dist / "index.html"))      # SPA fallback: React router handles the rest.
```

What to say in an interview:

- "This app is a single deployable that serves both API routes and the built React SPA."
- "It avoids route collisions by explicitly refusing to intercept `/api`, `/ws`, and `/health` paths."

### 49.2 `backend/storage/rate_limit.py`

This file is small, but it contains an important behavioral rule: free analyses reset at **midnight IST**, not midnight UTC.

```python
from datetime import datetime, time                  # Used to compute midnight boundary.
from zoneinfo import ZoneInfo                        # Timezone-aware calculations.

from backend.storage.redis_client import redis       # Shared Redis client.

FREE_ANALYSES_PER_DAY = 3                            # Product rule: three free analyses.
IST = ZoneInfo("Asia/Kolkata")                       # Reset timezone.

def _seconds_until_midnight_ist() -> int:
    now = datetime.now(IST)                          # Current time in IST, not server local time.
    midnight = datetime.combine(now.date(), time(0, 0, 0), tzinfo=IST)  # Today at 00:00 IST.

    from datetime import timedelta                   # Local import because only this function needs it.

    if midnight <= now:                              # If today's midnight already passed,
        midnight += timedelta(days=1)                # move to next day's midnight.

    return int((midnight - now).total_seconds())     # TTL in seconds for Redis expiry.

def check_and_increment_rate_limit(ip: str) -> dict:
    key = f"ratelimit:{ip}"                          # One Redis key per client IP.
    count = redis.incr(key)                          # Atomic increment; Redis creates the key if absent.

    if count == 1:
        ttl = _seconds_until_midnight_ist()          # First request today: attach expiry.
        redis.expire(key, ttl)

    allowed = count <= FREE_ANALYSES_PER_DAY         # Business rule check.
    remaining = max(0, FREE_ANALYSES_PER_DAY - count) # Clamp remaining count at zero.

    if not allowed:
        redis.decr(key)                              # Blocked requests do not consume the quota.

    return {
        "allowed": allowed,                          # Whether this request may proceed.
        "count": min(count, FREE_ANALYSES_PER_DAY),  # Report used count capped at max plan size.
        "remaining": remaining,                      # How many free analyses are left today.
        "limit": FREE_ANALYSES_PER_DAY,              # Daily total.
    }

def get_rate_limit_status(ip: str) -> dict:
    key = f"ratelimit:{ip}"                          # Same Redis key format as the mutating function.
    count = redis.get(key)                           # Read current value without incrementing.
    count = int(count) if count else 0               # Normalize Redis response into int.
    return {
        "count": count,                              # Already used today.
        "remaining": max(0, FREE_ANALYSES_PER_DAY - count), # Remaining free quota.
        "limit": FREE_ANALYSES_PER_DAY,              # Daily cap.
    }
```

Key intuition:

- `INCR` gives safe concurrent counting.
- `EXPIRE` turns that counter into a "daily bucket."
- The `DECR` rollback means rejected requests do not silently punish the user.

### 49.3 `backend/routes/cron.py`

This file answers: "How does the system refresh its market corpus every month?"

#### `_verify_qstash_signature`

```python
def _verify_qstash_signature(body: bytes, signature: str) -> bool:
    if not QSTASH_SIGNING_KEY:
        return True                                   # Development mode: skip verification entirely.

    expected = hmac.new(                              # Build server-side HMAC from secret + raw body.
        QSTASH_SIGNING_KEY.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)   # Constant-time compare avoids timing leaks.
```

This is standard webhook hygiene: only trust scheduled calls that prove knowledge of the shared secret.

#### `_get_active_combinations`

```python
def _get_active_combinations() -> list[tuple[str, str, str]]:
    active = set(TIER_1_COMBINATIONS)                 # Start from always-important predefined combos.

    try:
        cursor = 0                                    # Redis SCAN cursor.
        while True:
            cursor, keys = redis.scan(cursor, match="combo_count:*", count=100)  # Iterate lazily over keys.
            for key in keys:
                count = redis.get(key)                # Read popularity count.
                if count and int(count) >= 3:         # Only promote combos with real usage.
                    raw = key.replace("combo_count:", "")  # Strip Redis prefix.
                    parts = raw.split(":")            # Expected order: role:company_type:market
                    if len(parts) == 3:
                        active.add((parts[0], parts[1], parts[2]))  # Add user-driven hot combo.
            if cursor == 0:
                break                                 # Redis SCAN finished.
    except Exception as e:
        logger.warning("combo_scan_failed", error=str(e)) # Refresh still works with Tier 1 only.

    return list(active)                               # Convert back to list for downstream iteration.
```

This means the monthly refresh is not purely static. It adapts to what users actually analyze often.

#### `refresh_market_intel`

```python
@router.post("/refresh-market-intel")
async def refresh_market_intel(request: Request):
    body = await request.body()                       # Raw bytes needed for signature verification.

    signature = request.headers.get("upstash-signature", "") # Scheduler-provided signature header.
    if not _verify_qstash_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature.")  # Reject forged cron hits.

    try:
        from ingestion.tavily_client import deep as tavily_deep, general as tavily_general
        deep_remaining = tavily_deep.budget_remaining()       # Remaining search budget in deep tier.
        general_remaining = tavily_general.budget_remaining() # Remaining search budget in general tier.

        if deep_remaining < 100 or general_remaining < 100:
            logger.warning(
                "cron_skipped_budget_low",
                deep_remaining=deep_remaining,
                general_remaining=general_remaining,
            )
            _notify_discord(                          # Operational alert so humans know why refresh stopped.
                f"⚠️ Monthly cron skipped — Tavily budget too low.\n"
                f"Deep: {deep_remaining} remaining, General: {general_remaining} remaining.\n"
                f"Top up Tavily credits before next run."
            )
            return {"status": "skipped", "reason": "tavily_budget_low",
                    "deep_remaining": deep_remaining, "general_remaining": general_remaining}
    except Exception as e:
        logger.warning("budget_check_failed", error=str(e))  # Budget probe failure is non-fatal.

    redis.setex("cron:running", 7200, "1")           # Set a two-hour flag for UI or ops visibility.

    combinations = _get_active_combinations()        # Decide which role/company/market tuples to refresh.
    logger.info("cron_started", total_combos=len(combinations))

    results = []                                     # Successful refresh summaries.
    errors = []                                      # Failed refresh summaries.

    for role, company_type, market in combinations:
        try:
            summary = await run_ingestion_for_combo(  # Full ingestion pipeline for one market slice.
                role=role,
                company_type=company_type,
                market=market,
                force_refresh=True,
            )
            results.append({
                "combo": f"{role} / {company_type} / {market}",  # Human-readable identifier.
                "stored": summary.signals_stored,                # Newly stored signals.
                "discarded": summary.signals_discarded,          # Filtered/noisy signals.
                "duration_s": summary.duration_seconds,          # Runtime for one combo.
            })
            logger.info("combo_refreshed", role=role, company_type=company_type,
                        market=market, stored=summary.signals_stored)
            await asyncio.sleep(3)                   # Simple pacing to reduce API spikes.

        except Exception as e:
            errors.append({"combo": f"{role} / {company_type} / {market}", "error": str(e)})
            logger.error("combo_refresh_failed", role=role, company_type=company_type,
                         market=market, error=str(e))

    redis.delete("cron:running")                     # Clear running flag regardless of refresh mix.

    try:
        cursor = 0
        invalidated = 0
        while True:
            cursor, keys = redis.scan(cursor, match="snapshot:*", count=100) # Find cached DIVE snapshots.
            for key in keys:
                redis.delete(key)                    # Remove stale retrieval snapshots.
                invalidated += 1
            if cursor == 0:
                break
        logger.info("dive_snapshots_invalidated", count=invalidated)
    except Exception as e:
        logger.warning("snapshot_invalidation_failed", error=str(e))

    total_stored = sum(r["stored"] for r in results) # Aggregate signals stored across all combos.
    msg = (
        f"✅ Monthly cron complete\n"
        f"{len(results)} combos refreshed · {total_stored} signals stored · {len(errors)} errors"
    )
    if errors:
        msg += "\n\nFailed combos:\n" + "\n".join(f"• {e['combo']}: {e['error']}" for e in errors[:5])
    _notify_discord(msg)                             # Final success/failure summary for operators.

    logger.info("cron_complete", refreshed=len(results), errors=len(errors),
                total_stored=total_stored)

    return {
        "status": "complete",
        "refreshed": len(results),
        "errors": len(errors),
        "total_signals_stored": total_stored,
        "results": results,
        "error_details": errors,
    }
```

#### `_notify_discord`

```python
def _notify_discord(message: str) -> None:
    try:
        from backend.config import DISCORD_WEBHOOK_URL   # Read webhook lazily so startup stays cheap.
        if not DISCORD_WEBHOOK_URL:
            return                                       # Notifications are optional.
        import httpx
        httpx.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=5) # Small best-effort fire.
    except Exception:
        pass                                             # Never let alerting break the cron response.
```

### 49.4 `backend/llm/circuit_breaker.py`

This file is the classic resilience pattern: stop hammering a provider that is already failing.

```python
import time                                    # Used for cooldown timing.
import asyncio                                 # Imported but not actually used here.
import structlog                               # Structured logs for state transitions.

logger = structlog.get_logger()

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, cooldown_seconds: int = 300):
        self.name = name                        # Provider name, e.g. "groq".
        self.failure_threshold = failure_threshold # Open after this many failures.
        self.cooldown_seconds = cooldown_seconds    # Wait this long before probe retry.
        self.failures = 0                       # Consecutive failure count.
        self.last_failure_time: float | None = None # Timestamp of last failure.
        self.state = "closed"                   # Initial state: provider is healthy.

    def record_failure(self) -> None:
        self.failures += 1                      # Count another failure.
        self.last_failure_time = time.time()    # Mark when it happened.
        if self.failures >= self.failure_threshold:
            self.state = "open"                 # Stop sending traffic to provider.
            logger.warning("circuit_opened", provider=self.name, failures=self.failures)

    def record_success(self) -> None:
        if self.state == "half_open":
            self.state = "closed"               # Probe succeeded, provider is healthy again.
            self.failures = 0                   # Reset failure count.
            logger.info("circuit_closed", provider=self.name)

    def should_skip(self) -> bool:
        if self.state == "open":
            if self.last_failure_time and time.time() - self.last_failure_time > self.cooldown_seconds:
                self.state = "half_open"        # Cooldown passed: allow one test request.
                logger.info("circuit_half_open", provider=self.name)
                return False
            return True                         # Cooldown not over: skip provider entirely.
        return False                            # Closed or half-open probe mode: allow request.

groq_circuit = CircuitBreaker(name="groq")      # Global singleton used by Groq wrapper.
gemini_circuit = CircuitBreaker(name="gemini")  # Same pattern for Gemini.
cerebras_circuit = CircuitBreaker(name="cerebras")
openrouter_circuit = CircuitBreaker(name="openrouter")
nim_circuit = CircuitBreaker(name="nvidia_nim")
```

Interview framing:

- "The app does not just retry forever. It actively remembers unhealthy providers and cools off."

### 49.5 `backend/llm/router.py`

This file is the policy layer above raw provider SDK calls.

#### `call_review_agent`

```python
async def call_review_agent(
    messages: list[dict],
    max_tokens: int = 3000,
    session_id: str = "",
) -> tuple[str, dict]:
    last_error = None                             # Keep final error for debugging if everything fails.

    for provider, model in REVIEW_MODEL_CHAIN:    # Try providers in configured order.
        try:
            if provider == "groq":
                return await groq_chat(           # Primary path for most review generations.
                    messages=messages, model=model,
                    max_tokens=max_tokens, temperature=0.3,
                    session_id=session_id,
                )
            elif provider == "cerebras":
                return await cerebras_chat(       # Optional fallback provider.
                    messages=messages, max_tokens=max_tokens,
                    session_id=session_id,
                )
            elif provider == "nvidia_nim":
                return await nim_chat(            # Alternative fallback bucket.
                    messages=messages, max_tokens=max_tokens,
                    session_id=session_id,
                )
            elif provider == "gemini":
                prompt = _messages_to_prompt(messages) # Gemini wrapper expects prompt string, not chat array.
                return await gemini_chat(
                    prompt=prompt, model=model,
                    max_tokens=max_tokens, temperature=0.3,
                    session_id=session_id,
                )
            elif provider == "openrouter":
                return await openrouter_chat(     # Last-resort emergency provider.
                    messages=messages, max_tokens=max_tokens,
                    session_id=session_id,
                )

        except Exception as e:
            last_error = e                        # Remember why current attempt failed.
            logger.warning(
                "provider_failed_trying_next",
                provider=provider, model=model,
                error=str(e), session_id=session_id,
            )
            continue                              # Move down the chain.

    raise RuntimeError(f"all_providers_failed: {last_error}") # Nothing worked.
```

#### Small agent-specific wrappers

Read these as "policy shorthands." They centralize which model each agent should use.

```python
async def call_groq_8b(...):
    return await groq_chat(...)                   # Cheap fast helper for lighter tasks.

async def call_red_flag_agent(...):
    try:
        return await groq_chat(...70b...)         # Prefer larger model for nuanced critique.
    except Exception:
        return await groq_chat(...8b...)          # Fall back to faster/smaller model.

async def call_technical_depth_agent(...):
    try:
        return await groq_chat(...gpt-oss-120b...) # Frontier-quality primary.
    except Exception:
        return await groq_chat(...8b...)           # Safe degraded mode.

async def call_six_second_agent(...):
    try:
        text, meta = await groq_chat(...qwen3...)  # Primary summary model.
        if not text or not text.strip():
            raise ValueError("qwen3_32b_empty_response") # Explicitly reject blank answers.
        return text, meta
    except Exception:
        return await groq_chat(...8b...)           # Fallback if Qwen fails or returns empty.

async def call_competitive_agent(...):
    try:
        return await groq_chat(...qwen3...)        # Better reasoning model first.
    except Exception:
        return await nim_chat(...)                 # Different provider family as backup.
```

#### `_messages_to_prompt`

```python
def _messages_to_prompt(messages: list[dict]) -> str:
    parts = []                                     # Accumulates formatted message chunks.
    for msg in messages:
        role = msg.get("role", "user")             # Default unknown roles to user.
        content = msg.get("content", "")           # Message body text.
        if role == "system":
            parts.append(f"[SYSTEM]\n{content}")   # Tag system instructions clearly.
        elif role == "user":
            parts.append(f"[USER]\n{content}")     # Tag user prompt.
        elif role == "assistant":
            parts.append(f"[ASSISTANT]\n{content}") # Tag assistant history.
    return "\n\n".join(parts)                      # Flatten chat into one prompt string.
```

Why it exists:

- some provider wrappers want OpenAI-style `messages`
- some want a single prompt string
- this adapter keeps the rest of the app from caring

### 49.6 `backend/llm/groq_client.py`

This is one of the most operationally important files in the repo. It wraps the Groq SDK with:

- key rotation
- daily-budget tracking
- retries
- circuit breaker protection
- tracing

#### Support helpers

```python
_keys = [k.strip() for k in GROQ_API_KEYS.split(",") if k.strip()] # Parse comma-separated API key pool.
_call_count = 0                                                    # Global round-robin counter.
_call_lock = asyncio.Lock()                                        # Prevent race when choosing next key.

RPD_LIMITS = {                                                     # Manual requests-per-day tracking by model.
    "meta-llama/llama-4-scout-17b-16e-instruct": 1000,
    "llama-3.3-70b-versatile": 1000,
    "qwen/qwen3-32b": 1000,
    "llama-3.1-8b-instant": 14400,
}

RPM_FALLBACK_THRESHOLD = 50                                        # Log when request budget is getting tight.

async def _get_client() -> tuple[AsyncGroq, int]:
    global _call_count
    async with _call_lock:                                          # One caller at a time mutates counter.
        idx = _call_count % len(_keys)                              # Choose next key cyclically.
        _call_count += 1
    return AsyncGroq(api_key=_keys[idx]), idx                       # Return client and key index used.

def _rotate(current_idx: int) -> int:
    return (current_idx + 1) % len(_keys)                           # Next key after a rate-limit hit.

def _rpd_key(model: str, key_index: int) -> str:
    return f"groq:rpd:{model}:{key_index}"                          # Redis key namespace for daily usage.

def _check_rpd(model: str) -> bool:
    limit = RPD_LIMITS.get(model, 1000)                             # Default daily cap if model omitted.
    for i in range(len(_keys)):
        count = redis.get(_rpd_key(model, i))                       # Read usage for each API key.
        used = int(count) if count else 0
        if used < limit:
            return True                                             # At least one key still has budget.
    return False                                                    # Entire key pool exhausted for this model.

def _increment_rpd(model: str, key_idx: int = 0) -> None:
    key = _rpd_key(model, key_idx)
    count = redis.incr(key)                                         # Increment server-side usage tracker.
    if count == 1:
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)                            # Daily reset uses UTC here.
        midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        ttl = int((midnight - now).total_seconds())                 # Expire key at next UTC midnight.
        redis.expire(key, ttl)
```

#### `groq_chat`

```python
async def groq_chat(
    messages: list[dict],
    model: str = "llama-3.1-8b-instant",
    max_tokens: int = 1000,
    temperature: float = 0.1,
    session_id: str = "",
    agent_name: str = "",
) -> tuple[str, dict]:
    if groq_circuit.should_skip():
        raise RuntimeError("groq_circuit_open")      # Provider recently unhealthy; skip immediately.

    if not _check_rpd(model):
        raise RuntimeError(f"groq_rpd_exhausted:{model}") # No daily budget left across all keys.

    backoff = [2, 4, 8]                              # Retry sleep durations after transient failures.
    client, key_idx = await _get_client()            # Pick key in round-robin fashion.
    import time

    for attempt in range(3):
        try:
            t0 = time.monotonic()                    # Latency timing start.
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            text = response.choices[0].message.content.strip() # Main generated text.

            if "</think>" in text:
                text = text[text.index("</think>") + len("</think>"):].strip() # Strip Qwen thinking preamble.
            elif text.startswith("<think>"):
                raise RuntimeError("qwen3_thinking_truncated")  # Partial hidden chain means bad/truncated output.

            _increment_rpd(model, key_idx)           # Record successful use against current key budget.

            remaining = None
            if hasattr(response, "headers"):
                remaining_str = response.headers.get("x-ratelimit-remaining-requests")
                if remaining_str:
                    remaining = int(remaining_str)    # Read remaining RPM if provider exposed it.
                    redis.set(f"groq:rpm_remaining:{model}", remaining, ex=60) # Cache for observability.

            groq_circuit.record_success()            # Success heals half-open circuit.

            input_tokens = response.usage.prompt_tokens if response.usage else None
            output_tokens = response.usage.completion_tokens if response.usage else None
            latency_ms = round((time.monotonic() - t0) * 1000, 1) # End-to-end generation latency.

            metadata = {
                "provider": "groq",
                "model": model,
                "key_index": key_idx,
                "rpm_remaining": remaining,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

            if remaining is not None and remaining < RPM_FALLBACK_THRESHOLD:
                logger.warning(
                    "groq_rpm_low",
                    model=model,
                    remaining=remaining,
                    session_id=session_id,
                )                                   # Warning only; higher router decides if fallback is needed.

            if session_id and agent_name:
                try:
                    from backend.llm.langfuse_client import trace_llm_call
                    trace_llm_call(
                        session_id=session_id,
                        agent_name=agent_name,
                        model=model,
                        provider="groq",
                        messages=messages,
                        response_text=text,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency_ms,
                    )                               # Fire-and-forget observability trace.
                except Exception:
                    pass                            # Tracing must never break user flow.

            return text, metadata                   # Successful completion path.

        except RateLimitError:
            logger.warning("groq_rate_limit", model=model, attempt=attempt, session_id=session_id)
            key_idx = _rotate(key_idx)              # Move to another API key when a key hits 429.
            client = AsyncGroq(api_key=_keys[key_idx])
            if attempt < 2:
                await asyncio.sleep(backoff[attempt]) # Retry with progressive backoff.

        except APIStatusError as e:
            groq_circuit.record_failure()           # Provider returned API-level failure.
            logger.error("groq_api_error", error=str(e), model=model, session_id=session_id)
            if attempt < 2:
                await asyncio.sleep(backoff[attempt])
            else:
                raise                               # Exhausted retries for this error type.

        except Exception as e:
            groq_circuit.record_failure()           # Unexpected failure also counts toward circuit open.
            logger.error("groq_unexpected_error", error=str(e), session_id=session_id)
            raise

    raise RuntimeError("groq_all_retries_exhausted") # Defensive final error if loop exits without return.
```

Best interview explanation:

- "This wrapper is where provider unreliability is absorbed so individual agents stay simple."

### 49.7 `backend/agents/technical_depth_agent.py`

This file is more advanced than most other agents because it does **tool calling**.

#### `_should_skip_search`

```python
def _should_skip_search(query: str) -> bool:
    q = query.lower()                               # Normalize for case-insensitive matching.
    return any(term in q for term in SKIP_SEARCH_TERMS) # Block searches the model should already know.
```

Purpose:

- stop wasteful web lookups
- reserve search budget for genuinely niche terms

#### `_parse_output`

```python
def _parse_output(data: dict) -> TechnicalDepthOutput:
    evaluations = []
    for p in data.get("project_evaluations", []):
        try:
            evaluations.append(ProjectEvaluation(**p)) # Validate each project block against schema.
        except Exception:
            continue                                   # Skip malformed project entries, keep rest.
    return TechnicalDepthOutput(
        project_evaluations=evaluations,
        overall_technical_level=data.get("overall_technical_level", ""),
        most_differentiated_signal=data.get("most_differentiated_signal", ""),
        biggest_technical_gap=data.get("biggest_technical_gap", ""),
        communication_gap=data.get("communication_gap", ""),
        honest_summary=data.get("honest_summary", ""),
        unverified_skills=data.get("unverified_skills", []),
    )
```

This turns shaky LLM JSON into typed application data.

#### `_run_agentic_loop`

```python
async def _run_agentic_loop(
    client: AsyncGroq,
    messages: list[dict],
    session_id: str,
) -> TechnicalDepthOutput:
    MAX_TOOL_CALLS = 2                               # Hard cap keeps runtime and cost bounded.
    tool_call_count = 0                              # Number of actual search tool invocations made.
    searches_made = []                               # For logging/observability.

    while tool_call_count <= MAX_TOOL_CALLS:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=[SEARCH_TOOL],                     # Expose exactly one tool to the model.
            tool_choice="auto",                     # Model may choose to call it.
            max_tokens=2000,
            temperature=0.2,
        )

        msg = response.choices[0].message           # Assistant turn generated by model.
        finish_reason = response.choices[0].finish_reason # Tells whether model stopped or wants tools.

        messages.append({
            "role": "assistant",
            "content": msg.content or "",           # Save assistant text into running conversation.
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in (msg.tool_calls or [])
            ] or None,                              # Preserve tool call metadata in chat history.
        })

        if finish_reason == "stop" or not msg.tool_calls:
            data = extract_json(msg.content or "")  # Final answer path: extract JSON from text.
            output = _parse_output(data)            # Validate and shape result.
            logger.info("tech_depth_agent_complete", session_id=session_id,
                        projects_evaluated=len(output.project_evaluations),
                        tool_calls_made=tool_call_count, searches=searches_made)
            return output

        for tool_call in msg.tool_calls:
            if tool_call.function.name != "search_web":
                continue                            # Ignore unexpected tool names defensively.

            args = json.loads(tool_call.function.arguments) # Parse JSON arguments from model.
            query = args.get("query", "")

            if _should_skip_search(query):
                logger.info("tech_depth_search_skipped", query=query, session_id=session_id)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": f"Skipped — '{query}' is a well-known tool/concept, no lookup needed.",
                })                                  # Feed back why the tool was refused.
                continue

            tool_call_count += 1                    # Count a real lookup.
            searches_made.append(query)
            logger.info("tech_depth_search", query=query, call_num=tool_call_count, session_id=session_id)

            result = await lookup_technology(query, context="") # External lookup for niche technology.
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result[:600] if result else "No results found.", # Return concise tool result.
            })

    messages.append({"role": "user", "content": (
        "Research complete. Write the full JSON evaluation now. "
        "Include ALL fields. Do not return null for any field."
    )})                                              # Force final answer after tool-call limit.
    response = await client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        tool_choice="none",                          # Disable any more tools on final answer pass.
        tools=[SEARCH_TOOL],
        max_tokens=3000,
        temperature=0.2,
    )
    data = extract_json(response.choices[0].message.content or "")
    output = _parse_output(data)
    logger.info("tech_depth_agent_complete", session_id=session_id,
                projects_evaluated=len(output.project_evaluations),
                tool_calls_made=tool_call_count, searches=searches_made)
    return output
```

This is the clearest example of an "agentic" loop in the codebase:

- model thinks
- model optionally calls tool
- system feeds tool output back
- model finishes structured answer

#### `run_technical_depth_agent`

```python
async def run_technical_depth_agent(
    resume_text: str,
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    session_id: str = "",
) -> TechnicalDepthOutput:
    from backend.agents.prompts.template import get_role_calibration

    role_calibration = get_role_calibration(role, company_type) # Pull role-specific evaluation expectations.
    system = TECH_DEPTH_SYSTEM.format(
        role=role, company_type=company_type, market=market,
        experience_level=experience_level, role_calibration=role_calibration,
    )

    messages: list[dict] = [
        {"role": "system", "content": system},      # Main evaluator instructions.
        {"role": "user", "content": (
            f"RESUME:\n{resume_text[:8000]}\n\n"    # Truncate resume to keep prompt bounded.
            f"TARGET: {role} at {company_type} in {market} ({experience_level})\n\n"
            "Evaluate technical depth. Search only for genuinely niche/unfamiliar tech. "
            "Produce the final JSON when ready."
        )},
    ]

    client = AsyncGroq(api_key=_keys[0])            # Uses first key directly for this agentic loop.

    try:
        return await asyncio.wait_for(
            _run_agentic_loop(client, messages, session_id), # Hard runtime limit for user experience.
            timeout=55.0,
        )
    except asyncio.TimeoutError:
        logger.warning("tech_depth_timeout_falling_back", session_id=session_id)
        return await _fallback_evaluation(resume_text, role, company_type, market, experience_level, session_id)
    except Exception as e:
        logger.error("tech_depth_agent_failed", error=str(e), session_id=session_id)
        return await _fallback_evaluation(resume_text, role, company_type, market, experience_level, session_id)
```

#### `_fallback_evaluation`

```python
async def _fallback_evaluation(...):
    role_calibration = get_role_calibration(role, company_type) # Rebuild role context for simpler path.
    system = TECH_DEPTH_SYSTEM.format(...)                      # Reuse the same rubric.
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": (
            f"RESUME:\n{resume_text[:8000]}\n\n"
            "Evaluate technical depth based on your existing knowledge. "
            "Return JSON only, no tool calls."
        )},
    ]
    try:
        text, _ = await groq_chat(
            messages=messages, model="llama-3.1-8b-instant",
            max_tokens=2000, temperature=0.2, session_id=session_id,
        )                                              # Cheap non-agentic degraded mode.
        return _parse_output(extract_json(text))       # Still parse into typed output.
    except Exception as e:
        logger.error("tech_depth_fallback_failed", error=str(e), session_id=session_id)
        return TechnicalDepthOutput(
            project_evaluations=[], overall_technical_level="Evaluation unavailable.",
            most_differentiated_signal="", biggest_technical_gap="",
            communication_gap="", honest_summary="Technical depth evaluation failed.",
            unverified_skills=[],
        )                                              # Last-resort safe object so pipeline does not crash.
```

### 49.8 `frontend/src/lib/api.js`

This file is the browser-side transport layer. It turns UI actions into HTTP requests.

```javascript
const BASE = '/api' // Every HTTP endpoint in this app lives under /api.

export async function sessionInit({ role, market, company_type, experience_level }) {
  const res = await fetch(`${BASE}/session-init`, {     // Starts a backend analysis session.
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },    // Sending JSON body.
    body: JSON.stringify({ role, market, company_type, experience_level }), // Payload for session creation.
  })
  if (!res.ok) throw new Error(await res.text())        // Surface backend error body directly.
  return res.json()                                     // Parse response JSON for caller.
}

export async function submitAnalysis({ sessionId, file, role, company_type, market, experience_level, userContext, jdText, githubUrl, optedInCorpus }) {
  const form = new FormData()                           // File uploads require multipart form data.
  form.append('session_id', sessionId)                  // Backend needs current session.
  form.append('role', role)
  form.append('company_type', company_type)
  form.append('market', market)
  form.append('experience_level', experience_level)
  form.append('user_context', userContext || '')        // Optional fields normalized to empty string.
  form.append('jd_text', jdText || '')
  form.append('github_url', githubUrl || '')
  form.append('opted_in_corpus', optedInCorpus ? 'true' : 'false') // Convert boolean into form field.
  form.append('file', file)                             // Actual resume file blob.

  const res = await fetch(`${BASE}/analyse`, { method: 'POST', body: form }) // Kick off backend pipeline.
  if (!res.ok) {
    const body = await res.text()                       // Capture readable backend error.
    throw new Error(body)
  }
  return res.json()                                     // Usually returns accepted/session payload.
}

export async function getSessionState(sessionId) {
  const res = await fetch(`${BASE}/session/${sessionId}/state`) // Recovery/polling endpoint.
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function submitFollowup({ sessionId, section, question }) {
  const res = await fetch(`${BASE}/followup`, {         // Ask one deeper question on one review section.
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, section, question }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function submitFeedback({ sessionId, useful, role, market, company_type }) {
  await fetch(`${BASE}/feedback`, {                     // Fire-and-forget feedback event.
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, useful, role, market, company_type }),
  })
}

export async function requestToken(email) {
  const res = await fetch(`${BASE}/token`, {            // Ask backend to email/unlock a token.
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function verifyToken({ token, sessionId }) {
  const res = await fetch(`${BASE}/token/verify`, {     // Redeem unlock token against a session.
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, session_id: sessionId }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function createWebSocket(sessionId) {
  const wsBase = window.location.protocol === 'https:' ? 'wss:' : 'ws:' // Match current page security.
  return new WebSocket(`${wsBase}//${window.location.host}/api/ws/${sessionId}`) // Session-scoped socket.
}
```

The important design point is that the React components do **not** hardcode endpoint details everywhere. They call these wrappers.

### 49.9 `frontend/src/components/ReviewDocument.jsx` remaining helpers

Earlier sections already covered `parseContent`, `parseActionPlan`, `SectionContent`, `Section`, and `ReviewDocument`.

These two helper components are also worth understanding because they convert plain LLM prose into clearer UI structure.

#### `InferenceChain`

```javascript
function InferenceChain({ content }) {
  const parts = content.split(/→|->/).map(p => p.trim()).filter(Boolean) // Break one chain into stages.
  return (
    <div className="my-3 rounded-lg bg-[--roast-surface-2] border border-[--roast-border] px-3 py-2.5 text-xs font-mono">
      <div className="flex flex-wrap items-center gap-1.5">
        {parts.map((part, i) => (                  // Render each stage in recruiter-thought order.
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-[--roast-placeholder]">→</span>}  // Arrow between steps.
            <span className={
              i === 0 ? 'text-[--roast-muted]' :   // First stage = observed evidence.
              i === parts.length - 1 ? 'text-red-400' : // Final stage = likely negative conclusion.
              'text-yellow-400/80'                 // Middle stages = intermediate assumptions.
            }>{part}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
```

Meaning:

- first fragment = what recruiter notices
- middle fragments = assumption chain
- last fragment = decision or judgment

#### `ActionSteps`

```javascript
function ActionSteps({ steps }) {
  return (
    <ol className="space-y-2.5 mt-1">              // Ordered list for concrete action plan steps.
      {steps.map((step, i) => (
        <li key={i} className="flex items-start gap-3">
          <span className="shrink-0 w-5 h-5 rounded-full bg-orange-500/15 border border-orange-500/25 flex items-center justify-center text-[10px] font-bold text-orange-400 mt-0.5">
            {i + 1}                                 // Human-friendly step number badge.
          </span>
          <p className="text-sm text-[--roast-text-2] leading-relaxed flex-1">{step}</p> // Step body text.
        </li>
      ))}
    </ol>
  )
}
```

This is a good frontend example of "post-process LLM text into stronger UI semantics."

### 49.10 What this new section adds to your interview understanding

After this pass, you should now be able to explain:

- how FastAPI is created and how the React build is served
- how the daily free quota works and why it resets in IST
- how the monthly market-intelligence refresh works
- how provider fallback policy is separated from low-level provider SDK code
- how the Groq wrapper handles retries, budget tracking, and tracing
- how the technical-depth agent performs controlled tool calling
- how the frontend centralizes all HTTP/WebSocket calls
- how the review screen converts raw text into inference chains and action steps

If you keep reading the repo in execution order, the next most useful files to fully annotate are:

- `backend/storage/session_store.py` remaining functions
- `backend/retrieval/dive.py` helper functions
- `backend/routes/followup.py`
- `frontend/src/components/LandingPage.jsx` remaining render helpers
- `frontend/src/components/ResultsPage.jsx` lower-level render details
