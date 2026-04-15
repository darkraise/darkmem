"""One-off emitter for shared-base batch-132 — ai_coding domain (LLM integrations in application code: provider SDK calls, tool-use, structured outputs, retries, streaming, prompt frameworks, LLM observability, RAG app patterns, evals, cost tracking).

Writes 50 rows to data/v2/shared/batch_132.tmp.jsonl with ids shared-06551..06600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_132.tmp.jsonl"
ID_OFFSET = 6550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The summariser endpoint migrated from the Anthropic completions API to the messages API; the stop_sequences plumbing disappeared and tool blocks landed cleanly in the request body.", "milestone", "ai_coding", False,
     [("Anthropic", "organization"), ("completions API", "api"), ("messages API", "api"), ("summariser", "service")],
     [("messages API", "completions API", "REPLACES")],
     "which Anthropic API surface did the summariser move to and what fell out of the request plumbing",
     "anthropic messages api migration completions stop sequence tool block"),
    # --- 2 ---
    ("Dropped ad-hoc json.loads on model output in the extraction worker and switched to Instructor with a Pydantic response_model; parse-fail retries are now driven by Instructor's validation loop.", "decision", "ai_coding", False,
     [("json.loads", "method"), ("Instructor", "library"), ("Pydantic", "library"), ("extraction worker", "service")],
     [("Instructor", "json.loads", "REPLACES")],
     "which library replaced raw JSON parsing on LLM output in the extraction worker and what does it buy",
     "instructor pydantic response model replace json loads parse retry"),
    # --- 3 ---
    ("BAML superseded the LangChain prompt-template layer for the agent orchestration service; the typed function signatures and generated clients stopped the template drift across Python and TypeScript callers.", "decision", "ai_coding", False,
     [("BAML", "library"), ("LangChain", "library"), ("agent orchestration", "service"), ("TypeScript", "language"), ("Python", "language")],
     [("BAML", "LangChain", "IMPROVES_ON")],
     "which prompt-framework swap fixed template drift between the Python and TypeScript clients of the agent service",
     "baml langchain prompt template typed function signature drift client"),
    # --- 4 ---
    ("OpenAI's structured-outputs mode with strict=true replaced hand-rolled function-calling for the address-parser; the JSON schema is emitted straight from a Zod definition via zod-to-json-schema.", "architecture", "ai_coding", False,
     [("OpenAI", "organization"), ("structured-outputs", "pattern"), ("function-calling", "pattern"), ("Zod", "library"), ("zod-to-json-schema", "library"), ("address-parser", "service")],
     [("structured-outputs", "function-calling", "REPLACES")],
     "which OpenAI response-shaping mode replaced the tool-calling trick in the address-parser and where does its schema come from",
     "openai structured output strict zod json schema replace function call"),
    # --- 5 ---
    ("Streaming responses via server-sent events replaced the old blocking chat.completions call on the chat UI; time-to-first-token dropped from roughly 2.8 seconds to under 400 ms perceived.", "milestone", "ai_coding", False,
     [("server-sent events", "protocol"), ("chat.completions", "api"), ("chat UI", "project")],
     [("server-sent events", "chat.completions", "REPLACES")],
     "which transport change cut time-to-first-token on the chat UI and by how much",
     "streaming sse blocking completions time to first token chat ui"),
    # --- 6 ---
    ("LangFuse took over LLM-call observability on 2026-03-18, replacing the Helicone proxy we had been running since December; session-level traces and dataset tie-ins made the swap worth the migration cost.", "milestone", "ai_coding", False,
     [("LangFuse", "tool"), ("Helicone", "tool"), ("2026-03-18", "date")],
     [("LangFuse", "Helicone", "REPLACES")],
     "which LLM observability backend replaced Helicone and when did the cutover happen",
     "langfuse helicone observability cutover trace dataset swap"),
    # --- 7 ---
    ("Rate-limit budgets are enforced per tenant in Redis via a token bucket keyed on tenant-id plus model; the 429 path surfaces a Retry-After derived from the bucket refill interval.", "architecture", "ai_coding", False,
     [("Redis", "database"), ("token bucket", "pattern"), ("Retry-After", "config"), ("tenant-id", "pattern")],
     [("token bucket", "Redis", "USES")],
     "how does the gateway share a rate-limit budget per tenant across LLM providers and what drives Retry-After",
     "token bucket redis tenant model rate limit retry after refill"),
    # --- 8 ---
    ("Exponential backoff with full jitter handles 429 and 529 from the Anthropic client; the base is 500 ms, the cap is 30 s, and the retry ceiling is five attempts before we fail the job.", "preference", "ai_coding", False,
     [("Anthropic", "organization"), ("Exponential backoff", "pattern"), ("full jitter", "pattern"), ("429", "config"), ("529", "config")],
     [],
     "which retry strategy does the Anthropic client wrap 429 and 529 responses with",
     "exponential backoff jitter 429 529 anthropic retry cap attempt"),
    # --- 9 ---
    ("Prompt templates moved out of Python string concat into the prompts/ folder and are rendered through Jinja2 with a strict undefined mode; a missing variable now fails fast at render time.", "architecture", "ai_coding", False,
     [("Jinja2", "library"), ("prompts/", "file"), ("strict undefined", "config")],
     [],
     "where do prompt templates live now and how are missing variables caught before reaching the model",
     "jinja prompt template strict undefined variable render folder"),
    # --- 10. noise ---
    ("Someone left a neatly folded origami crane on top of the shared whiteboard eraser this morning.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("LlamaIndex's VectorStoreIndex was swapped for a thin custom retriever that calls pgvector directly; the old abstraction was adding two extra hops on every RAG query.", "decision", "ai_coding", False,
     [("LlamaIndex", "library"), ("VectorStoreIndex", "pattern"), ("pgvector", "library"), ("retriever", "pattern")],
     [("pgvector", "LlamaIndex", "REPLACES")],
     "which retrieval abstraction was dropped in favour of direct pgvector calls and why",
     "llamaindex vector store index pgvector retriever hop drop rag"),
    # --- 12 ---
    ("Chunking for the support-docs RAG index uses a semantic splitter with a 512-token target and 64-token overlap; the naive character splitter was cutting mid-function in code snippets.", "architecture", "ai_coding", False,
     [("semantic splitter", "pattern"), ("support-docs", "project"), ("character splitter", "pattern")],
     [("semantic splitter", "character splitter", "IMPROVES_ON")],
     "which chunking strategy replaced the character splitter on the support-docs index and what sizes did we pick",
     "semantic chunking 512 overlap 64 character splitter code snippet"),
    # --- 13 ---
    ("Embeddings for the RAG index generated with voyage-3-large instead of text-embedding-3-large; recall at 10 jumped from 0.71 to 0.84 on the internal eval set.", "milestone", "ai_coding", False,
     [("voyage-3-large", "technology"), ("text-embedding-3-large", "technology"), ("RAG", "pattern")],
     [("voyage-3-large", "text-embedding-3-large", "REPLACES")],
     "which embedding model did we switch to for the RAG pipeline and what did recall look like after",
     "voyage 3 large text embedding openai recall rag index swap"),
    # --- 14 ---
    ("Tool-use schemas for the agent are authored as Pydantic models and compiled to the Anthropic input_schema via model_json_schema; the two sources of truth problem disappears.", "architecture", "ai_coding", False,
     [("Pydantic", "library"), ("Anthropic", "organization"), ("input_schema", "config"), ("model_json_schema", "method")],
     [],
     "how does the agent keep its tool schemas in sync between Python types and the Anthropic request payload",
     "pydantic tool schema anthropic input schema json compile single"),
    # --- 15 ---
    ("The OpenAI client wrapper returns a typed dataclass via the parse helper with response_format set to a Pydantic class; downstream code never touches raw message content.", "preference", "ai_coding", False,
     [("OpenAI", "organization"), ("parse", "method"), ("response_format", "config"), ("Pydantic", "library")],
     [],
     "which OpenAI SDK helper returns typed dataclasses and keeps raw message content out of downstream code",
     "openai parse response format pydantic typed dataclass wrapper"),
    # --- 16 ---
    ("Promptfoo evals run on every release candidate; the yaml test suite asserts on output with deterministic matchers and a small model-graded panel for open-ended prompts.", "preference", "ai_coding", False,
     [("Promptfoo", "tool"), ("yaml", "pattern"), ("release candidate", "pattern")],
     [],
     "which eval tool gates releases and how does its suite mix deterministic and model-graded checks",
     "promptfoo eval yaml release candidate deterministic model graded"),
    # --- 17 ---
    ("Added DeepEval on top of Promptfoo for the hallucination and faithfulness metrics on the RAG answerer; the scores land in LangFuse dashboards next to the cost numbers.", "architecture", "ai_coding", False,
     [("DeepEval", "tool"), ("Promptfoo", "tool"), ("LangFuse", "tool"), ("RAG answerer", "service")],
     [],
     "which two eval libraries cover the RAG answerer's hallucination checks and where do their scores show up",
     "deepeval promptfoo hallucination faithfulness langfuse dashboard"),
    # --- 18 ---
    ("Cost-tracking dashboard in Grafana pulls from a usage_events table populated by a middleware that tags every call with tenant, model, and feature; token counts come from the provider response.", "architecture", "ai_coding", False,
     [("Grafana", "tool"), ("usage_events", "pattern"), ("middleware", "pattern")],
     [("middleware", "usage_events", "PRODUCES")],
     "how are per-tenant LLM costs tracked end-to-end from SDK call to dashboard",
     "cost tracking grafana usage events middleware tenant model token"),
    # --- 19 ---
    ("The Google Gemini integration uses the google-genai SDK with response_mime_type=application/json and a response_schema; the old google-generativeai package is deprecated in our code.", "decision", "ai_coding", False,
     [("Google", "organization"), ("google-genai", "library"), ("google-generativeai", "library"), ("response_schema", "config")],
     [("google-genai", "google-generativeai", "REPLACES")],
     "which Google SDK did we standardise on for Gemini calls and how do we force JSON output",
     "google genai sdk response mime type schema gemini deprecated"),
    # --- 20 ---
    ("Mistral's chat client is wired through the same retry and budget middleware as Anthropic; adding a new provider is now a matter of implementing a ProviderAdapter interface.", "architecture", "ai_coding", False,
     [("Mistral", "organization"), ("Anthropic", "organization"), ("ProviderAdapter", "pattern"), ("middleware", "pattern")],
     [],
     "which abstraction keeps Mistral, Anthropic, and friends behind the same retry and budget pipeline",
     "mistral anthropic provider adapter middleware retry budget interface"),
    # --- 21 ---
    ("Cohere's rerank-english-v3.0 runs as a second stage on top of the vector search; top-100 from pgvector becomes top-10 after rerank, and nDCG@10 improved from 0.62 to 0.78.", "milestone", "ai_coding", False,
     [("Cohere", "organization"), ("rerank-english-v3.0", "technology"), ("pgvector", "library"), ("nDCG", "concept")],
     [],
     "which reranker did we add on top of pgvector and what happened to nDCG at 10",
     "cohere rerank english pgvector second stage ndcg top 100 10"),
    # --- 22 ---
    ("Guidance was evaluated against Outlines for constrained generation; Outlines won because its regex-FSM backend integrated with our self-hosted vLLM server without running a separate executor.", "decision", "ai_coding", False,
     [("Guidance", "library"), ("Outlines", "library"), ("vLLM", "tool"), ("regex-FSM", "pattern")],
     [("Outlines", "Guidance", "PREFERS")],
     "which constrained-generation library did we pick over Guidance and what sealed the decision",
     "outlines guidance vllm regex fsm constrained generation self host"),
    # --- 23 ---
    ("Marvin handles the ad-hoc classification prompts in the triage worker; cast_to a Literal type returns an enum-like value directly and saves us the switch statement in app code.", "architecture", "ai_coding", False,
     [("Marvin", "library"), ("triage worker", "service"), ("cast_to", "method"), ("Literal", "pattern")],
     [],
     "which library does the triage worker lean on for tiny classification prompts and why Literal types",
     "marvin cast to literal classification triage worker enum switch"),
    # --- 24 ---
    ("Phoenix by Arize is the local tracer for LLM calls in dev; OpenTelemetry spans flow into the Phoenix UI and mirror what LangFuse sees in staging and prod.", "architecture", "ai_coding", False,
     [("Phoenix", "tool"), ("Arize", "organization"), ("OpenTelemetry", "protocol"), ("LangFuse", "tool")],
     [],
     "which local LLM tracer do devs run and how does it line up with staging observability",
     "phoenix arize opentelemetry langfuse local trace dev staging"),
    # --- 25 ---
    ("Humanloop was trialled for prompt versioning but lost out to a git-backed prompts package plus LangFuse prompt management; engineers preferred PR review over a web editor.", "decision", "ai_coding", False,
     [("Humanloop", "tool"), ("LangFuse", "tool"), ("git", "tool"), ("prompts package", "project")],
     [("git", "Humanloop", "PREFERS")],
     "which prompt-management tool was rejected and which setup won on the team's review preference",
     "humanloop langfuse git prompt version editor pr review trial"),
    # --- 26 ---
    ("Tool-use loop on the research agent caps at eight tool calls per turn; an overshoot triggers a summarise-and-handoff prompt so the agent doesn't silently exceed the 200k context window.", "architecture", "ai_coding", False,
     [("research agent", "service"), ("context window", "pattern"), ("200k", "concept")],
     [],
     "which safeguard stops the research agent from blowing through its context budget during long tool-use loops",
     "tool call cap handoff summarise context window agent turn limit"),
    # --- 27 ---
    ("Claude's prompt-caching with cache_control on the system block cut token spend on the docs assistant by around 63 percent after a week of warm traffic.", "milestone", "ai_coding", False,
     [("Claude", "technology"), ("cache_control", "config"), ("docs assistant", "service"), ("prompt-caching", "pattern")],
     [],
     "which Claude feature drove the 63 percent token spend drop on the docs assistant",
     "claude prompt caching cache control docs assistant token spend"),
    # --- 28 ---
    ("A tiny ProviderAdapter test harness replays recorded API responses from VCR-style fixtures; nothing calls the real Anthropic or OpenAI endpoints in CI any more.", "architecture", "ai_coding", False,
     [("ProviderAdapter", "pattern"), ("VCR", "tool"), ("Anthropic", "organization"), ("OpenAI", "organization"), ("CI", "concept")],
     [],
     "how do we keep LLM-caller tests deterministic in CI without hitting real provider endpoints",
     "provider adapter vcr replay fixture anthropic openai ci deterministic"),
    # --- 29 ---
    ("Function-calling descriptions started getting auto-generated from docstrings via a small helper that leans on griffe; the drift between docs and schema descriptions is gone.", "fact", "ai_coding", False,
     [("griffe", "library"), ("Function-calling", "pattern"), ("docstrings", "pattern")],
     [],
     "which helper keeps tool descriptions in sync with Python docstrings in the function-calling wrapper",
     "griffe docstring function calling description sync helper drift"),
    # --- 30 ---
    ("Azure OpenAI deployments are fronted by the same OpenAI Python client via the AsyncAzureOpenAI class; only the base_url and api_version strings differ from the public endpoint wiring.", "architecture", "ai_coding", False,
     [("Azure OpenAI", "organization"), ("AsyncAzureOpenAI", "library"), ("base_url", "config"), ("api_version", "config")],
     [],
     "how does the codebase talk to Azure OpenAI deployments without forking the client wrapper",
     "azure openai async client base url api version python wrapper"),
    # --- 31 ---
    ("The streaming UX batches tokens client-side at 16 ms intervals; piping every chunk straight to the DOM was causing layout thrash on Safari with long responses.", "problem", "ai_coding", False,
     [("Safari", "platform"), ("DOM", "pattern"), ("streaming UX", "pattern")],
     [],
     "which streaming UX tweak fixed the Safari layout thrash on long model responses",
     "stream batch token dom safari layout thrash interval client"),
    # --- 32 ---
    ("Tenant budget overruns emit a structured BudgetExceeded event; the SDK wrapper converts it to a 429-shaped response so upstream callers reuse their existing backoff code.", "architecture", "ai_coding", False,
     [("BudgetExceeded", "pattern"), ("SDK wrapper", "library"), ("429", "config")],
     [],
     "how does the SDK wrapper signal budget overruns so callers can reuse their 429 backoff logic",
     "budget exceeded 429 sdk wrapper tenant overrun backoff reuse"),
    # --- 33 ---
    ("Async call concurrency to Anthropic is bounded by an asyncio.Semaphore of 32 per process; the provider's per-minute limit translates cleanly once we account for average latency.", "fact", "ai_coding", False,
     [("Anthropic", "organization"), ("asyncio.Semaphore", "library"), ("concurrency", "concept")],
     [],
     "how does the Python worker cap its concurrent Anthropic calls to stay under the per-minute ceiling",
     "asyncio semaphore concurrency anthropic rate limit per process 32"),
    # --- 34 ---
    ("The RAG answerer prints citation anchors by smuggling chunk ids in the tool-result content; the client resolves them back to source URLs from a local lookup table.", "architecture", "ai_coding", False,
     [("RAG answerer", "service"), ("citation anchors", "pattern"), ("lookup table", "pattern")],
     [],
     "how does the RAG answerer attach citations that the UI can resolve to source URLs",
     "rag citation anchor chunk id tool result lookup table answerer"),
    # --- 35 ---
    ("OpenAI evals YAML files live next to each prompt; the eval suite runs under promptfoo and fails CI on any regression bigger than 3 percentage points on exact-match.", "preference", "ai_coding", False,
     [("OpenAI evals", "tool"), ("promptfoo", "tool"), ("CI", "concept")],
     [],
     "which eval format sits next to prompts and what regression threshold gates CI",
     "openai evals yaml promptfoo regression threshold exact match gate"),
    # --- 36 ---
    ("Retrying on 500 from OpenAI is capped at two attempts; the SDK's own retries had been layered on top of our wrapper's and the total wait was hitting 90 seconds in the worst case.", "problem", "ai_coding", False,
     [("OpenAI", "organization"), ("500", "config"), ("SDK", "library")],
     [],
     "which layered-retry bug were we hitting with OpenAI 500s and how did we tame the wait time",
     "openai 500 retry layered sdk wrapper wait cap attempt two"),
    # --- 37 ---
    ("Parallel tool-calls are disabled on the booking agent; the downstream inventory API can't tolerate two holds in flight so we flipped parallel_tool_calls to false.", "decision", "ai_coding", False,
     [("parallel_tool_calls", "config"), ("booking agent", "service"), ("inventory API", "api")],
     [],
     "why does the booking agent set parallel_tool_calls to false and what downstream constraint drove it",
     "parallel tool calls booking agent inventory hold concurrent"),
    # --- 38 ---
    ("Structured-output JSON is validated with Pydantic v2's TypeAdapter in one place; the old duplicate validation calls across three services collapsed into a shared schemas package.", "architecture", "ai_coding", False,
     [("Pydantic", "library"), ("TypeAdapter", "method"), ("schemas", "project")],
     [],
     "which refactor consolidated LLM-output validation across services onto one Pydantic entry point",
     "pydantic type adapter schemas package validate structured output"),
    # --- 39 ---
    ("Guardrails are applied after the model call via a tiny post-processor; hard filters run first, then a lightweight classifier decides whether to surface or suppress the answer.", "architecture", "ai_coding", False,
     [("Guardrails", "pattern"), ("post-processor", "pattern"), ("classifier", "pattern")],
     [],
     "which two-stage guardrail design gates LLM output before it reaches the client",
     "guardrail post process hard filter classifier suppress surface"),
    # --- 40 ---
    ("Token counting before send uses tiktoken for OpenAI models and the Anthropic count_tokens endpoint for Claude; rough heuristics had been under-counting by 15 percent on code-heavy prompts.", "problem", "ai_coding", False,
     [("tiktoken", "library"), ("Anthropic", "organization"), ("count_tokens", "api"), ("Claude", "technology")],
     [("tiktoken", "count_tokens", "RELATED_TO")],
     "how do we get honest token counts per provider before sending and why did the heuristic fail",
     "tiktoken anthropic count tokens heuristic under count prompt"),
    # --- 41 ---
    ("The moderation hook calls omni-moderation-latest before the user message ever reaches the main model; a refusal path short-circuits to a canned response and skips the billable call.", "architecture", "ai_coding", False,
     [("omni-moderation-latest", "technology"), ("moderation hook", "pattern")],
     [],
     "which moderation model runs before the main call and what does a refusal short-circuit save",
     "omni moderation latest hook refusal short circuit bill save"),
    # --- 42 ---
    ("Prompt versions carry a semver in the frontmatter; LangFuse links traces to version ids so a regression can be attributed to the exact prompt change.", "preference", "ai_coding", False,
     [("LangFuse", "tool"), ("semver", "pattern"), ("frontmatter", "pattern")],
     [],
     "how does prompt versioning tie regressions back to a specific template change in tracing",
     "prompt semver frontmatter langfuse trace version regression link"),
    # --- 43 ---
    ("The fallback chain goes Claude sonnet, then gpt-4o, then mistral-large on 5xx or circuit-breaker trip; callers get a single typed response and don't know which provider answered.", "architecture", "ai_coding", False,
     [("Claude sonnet", "technology"), ("gpt-4o", "technology"), ("mistral-large", "technology"), ("circuit-breaker", "pattern")],
     [],
     "which provider fallback order does the gateway try on 5xx and how is it hidden from callers",
     "claude sonnet gpt 4o mistral large fallback circuit breaker chain"),
    # --- 44 ---
    ("Helicone's proxy-header approach never sat right with the security team; LangFuse's in-SDK span emission avoids routing traffic through a third-party proxy entirely.", "decision", "ai_coding", False,
     [("Helicone", "tool"), ("LangFuse", "tool"), ("proxy", "pattern")],
     [("LangFuse", "Helicone", "PREFERS")],
     "which observability design choice did security prefer and why did the proxy model lose",
     "helicone proxy header langfuse in sdk span security traffic"),
    # --- 45 ---
    ("Prompt-injection defences live in a middleware that strips zero-width characters, flags delimiter drift, and wraps user text in a marked block the system prompt references.", "architecture", "ai_coding", False,
     [("middleware", "pattern"), ("zero-width characters", "pattern"), ("system prompt", "pattern")],
     [],
     "which middleware patterns harden LLM calls against prompt-injection attempts in user input",
     "prompt injection middleware zero width delimiter drift marked block"),
    # --- 46 ---
    ("Cost per resolved ticket is the business metric; the LangFuse dashboard divides daily LLM spend by the support-ticket resolution count to track it over time.", "fact", "ai_coding", False,
     [("LangFuse", "tool"), ("support-ticket", "pattern"), ("Cost per resolved ticket", "concept")],
     [],
     "which unit-economics metric do we track for the support assistant and how is it computed",
     "cost per resolved ticket langfuse dashboard spend resolution ratio"),
    # --- 47 ---
    ("Streaming aggregation on the server builds a single final message from the delta events; clients that can't stream fall back to the aggregated payload without a code path split.", "architecture", "ai_coding", False,
     [("Streaming aggregation", "pattern"), ("delta events", "pattern"), ("aggregated payload", "pattern")],
     [],
     "how does the server support both streaming and non-streaming clients without duplicating the code path",
     "streaming aggregation delta event fallback payload unified handler"),
    # --- 48 ---
    ("Context-window assembly for RAG composes retrieved chunks with a budget solver; the solver picks chunks under a 60k-token cap to leave headroom for the answer and tool-use.", "architecture", "ai_coding", False,
     [("RAG", "pattern"), ("budget solver", "pattern"), ("60k", "concept")],
     [],
     "how does the RAG pipeline pick retrieved chunks under a context budget and leave room for the answer",
     "context window budget solver rag chunk 60k token headroom"),
    # --- 49. noise ---
    ("The stapler on desk four jams in exactly the same way every third Tuesday regardless of who touches it.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Instructor's max_retries with a validation_context lets the extraction worker hand the model its own failed output plus the validation error; success rate on the first retry jumped from 38 to 71 percent.", "milestone", "ai_coding", False,
     [("Instructor", "library"), ("max_retries", "config"), ("validation_context", "config"), ("extraction worker", "service")],
     [],
     "which Instructor feature boosted first-retry success on the extraction worker and by how much",
     "instructor max retries validation context first retry success rate"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
