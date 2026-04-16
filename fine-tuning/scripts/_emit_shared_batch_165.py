"""One-off emitter for shared-base batch-165 — technical domain (LLM agent frameworks and tool use: LangChain, LangGraph, LlamaIndex, CrewAI, AutoGen, Semantic Kernel, Haystack, DSPy, Instructor, Guidance, Outlines, MCP, function calling, ReAct, Reflexion, CoT, ToT, Assistants API, multi-agent orchestration, structured outputs, streaming, retry loops).

Writes 50 rows to data/v2/shared/batch_165.tmp.jsonl with ids shared-08201..08250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_165.tmp.jsonl"
ID_OFFSET = 8200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Rewrote the router agent from LangChain AgentExecutor to LangGraph; the state graph expresses retries and branching without the hidden control flow that the old executor hid inside callbacks.", "decision", "technical", False,
     [("LangChain", "framework"), ("AgentExecutor", "pattern"), ("LangGraph", "framework"), ("state graph", "pattern")],
     [("LangGraph", "AgentExecutor", "REPLACES")],
     "which agent runtime replaced LangChain AgentExecutor for the router and what pattern did it expose",
     "langgraph langchain agent executor state graph router retry"),
    # --- 2 ---
    ("Picked LlamaIndex for the corpus ingestion side while leaving orchestration to LangGraph; the split keeps retrieval nodes specialised and avoids pulling the LangChain chain abstractions into the agent loop.", "fact", "technical", False,
     [("LlamaIndex", "framework"), ("LangGraph", "framework"), ("LangChain", "framework"), ("retrieval nodes", "pattern")],
     [("LlamaIndex", "LangGraph", "COMMUNICATES_WITH")],
     "how did ingestion and orchestration split between LlamaIndex and LangGraph for the agent stack",
     "llamaindex langgraph ingestion retrieval orchestration split corpus"),
    # --- 3 ---
    ("CrewAI drives the multi-agent producer-critic loop; each crew member has a role prompt and a tool list, and the manager agent routes tasks rather than a hard-coded python orchestrator.", "milestone", "technical", False,
     [("CrewAI", "framework"), ("producer-critic", "pattern"), ("manager agent", "pattern"), ("role prompt", "pattern")],
     [("CrewAI", "producer-critic", "IMPLEMENTS")],
     "which framework handles the multi-agent producer-critic loop and how does task routing happen",
     "crewai multi agent producer critic manager role prompt routing"),
    # --- 4 ---
    ("Swapped AutoGen GroupChat for a LangGraph supervisor pattern; GroupChat's round-robin speaker selection kept stalling the pipeline when one agent had nothing to add and still consumed a turn.", "decision", "technical", False,
     [("AutoGen", "framework"), ("GroupChat", "pattern"), ("LangGraph", "framework"), ("supervisor pattern", "pattern")],
     [("supervisor pattern", "GroupChat", "REPLACES")],
     "which orchestration pattern replaced AutoGen GroupChat and what stall did the old one cause",
     "autogen group chat langgraph supervisor stall round robin speaker"),
    # --- 5 ---
    ("Semantic Kernel hosts the .NET side of the pipeline and exposes planners over SK-native plugins; the Python services call into it through an MCP bridge rather than sharing in-process state.", "decision", "technical", False,
     [("Semantic Kernel", "framework"), (".NET", "platform"), ("MCP", "protocol"), ("planner", "pattern")],
     [("Semantic Kernel", "MCP", "COMMUNICATES_WITH")],
     "how does the .NET Semantic Kernel side talk to the Python services without sharing process state",
     "semantic kernel dotnet mcp bridge planner plugin python process"),
    # --- 6 ---
    ("Haystack 2.x pipelines drive the RAG side for the FAQ bot; the component DAG makes branching on retrieval confidence explicit and the old bespoke python glue got deleted in the migration.", "milestone", "technical", False,
     [("Haystack", "framework"), ("RAG", "pattern"), ("component DAG", "pattern"), ("FAQ bot", "project")],
     [("Haystack", "component DAG", "USES")],
     "which Haystack feature replaced the bespoke Python glue for the FAQ bot's retrieval branching",
     "haystack 2x rag faq bot component dag branch confidence glue"),
    # --- 7 ---
    ("Rewrote the few-shot selector with DSPy signatures and a BootstrapFewShot compiler; hand-tuned prompt templates went from brittle to optimised against a held-out dev set in one pass.", "decision", "technical", False,
     [("DSPy", "framework"), ("signature", "pattern"), ("BootstrapFewShot", "algorithm"), ("prompt template", "pattern")],
     [("DSPy", "prompt template", "REPLACES")],
     "which DSPy abstraction replaced hand-tuned prompt templates and what compiler optimised the few-shots",
     "dspy signature bootstrap fewshot compile prompt template tune dev"),
    # --- 8 ---
    ("Adopted Instructor for typed OpenAI outputs; Pydantic models double as response schemas and the retry-on-validation-error loop handles the occasional drifted JSON without a custom parser.", "decision", "technical", False,
     [("Instructor", "library"), ("OpenAI", "service"), ("Pydantic", "library"), ("retry-on-validation-error", "pattern")],
     [("Instructor", "Pydantic", "USES")],
     "which library pairs Pydantic models with OpenAI responses and how does it handle drifted JSON",
     "instructor pydantic openai typed output retry validation drift"),
    # --- 9 ---
    ("Guidance handles the constrained-generation path for the SQL writer; token-level regex masks ensure the model can only emit a valid SELECT before the LIMIT clause lands.", "fact", "technical", False,
     [("Guidance", "library"), ("SQL writer", "project"), ("regex mask", "pattern"), ("SELECT", "command")],
     [("Guidance", "regex mask", "USES")],
     "which library enforces token-level constraints on the SQL writer so only valid SELECTs can emit",
     "guidance constrained generation sql select regex mask token"),
    # --- 10. noise ---
    ("The kitchen radio at the coworking space has been stuck on the same reggae station for a month and nobody will admit to owning the remote.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Outlines wraps the local Mistral serving endpoint with a context-free grammar so every function argument parses; the prior free-form JSON path broke on nested arrays about three percent of runs.", "decision", "technical", False,
     [("Outlines", "library"), ("Mistral", "technology"), ("context-free grammar", "pattern"), ("free-form JSON", "pattern")],
     [("Outlines", "free-form JSON", "REPLACES")],
     "which grammar-based library replaced free-form JSON around the local Mistral endpoint",
     "outlines mistral grammar json function argument nested array parse"),
    # --- 12 ---
    ("MCP is the transport for tool discovery across the platform; each backend service exposes a stdio or streamableHttp MCP server and the agent negotiates tool schemas at session start.", "reference", "technical", False,
     [("MCP", "protocol"), ("stdio", "protocol"), ("streamableHttp", "protocol"), ("tool schema", "concept")],
     [("MCP", "tool schema", "PRODUCES")],
     "which protocol carries tool discovery across the platform and what transports does it expose",
     "mcp tool discovery stdio streamable http schema negotiate session"),
    # --- 13 ---
    ("Ported the internal search tool from a custom function-calling bridge to MCP; the agent now lists it via tools/list on connection and the bespoke registry shim got retired along with its stale schemas.", "milestone", "technical", False,
     [("MCP", "protocol"), ("function-calling bridge", "pattern"), ("tools/list", "api"), ("registry shim", "pattern")],
     [("MCP", "registry shim", "REPLACES")],
     "which MCP capability retired the custom function-calling bridge's stale schema registry",
     "mcp tools list function calling bridge registry shim schema port"),
    # --- 14 ---
    ("Function calling on the OpenAI side is parallel tool calling by default now; the single-call retry wrapper from the first release got removed once the model stopped inventing phantom tool ids.", "milestone", "technical", False,
     [("OpenAI", "service"), ("parallel tool calling", "pattern"), ("single-call retry wrapper", "pattern"), ("phantom tool id", "error")],
     [("parallel tool calling", "single-call retry wrapper", "REPLACES")],
     "which OpenAI feature made the single-call retry wrapper obsolete and which bug had blocked it before",
     "openai parallel tool call retry wrapper phantom id single"),
    # --- 15 ---
    ("ReAct prompting still beats pure tool-calling for the research agent on multi-hop queries; the scratchpad trace improves recovery when a tool returns something the model did not expect.", "fact", "technical", False,
     [("ReAct", "pattern"), ("tool-calling", "pattern"), ("scratchpad", "pattern"), ("research agent", "project")],
     [("ReAct", "tool-calling", "IMPROVES_ON")],
     "which prompting pattern beats pure tool-calling on multi-hop research queries and why",
     "react prompt tool calling scratchpad multi hop research recover"),
    # --- 16 ---
    ("Reflexion-style self-critique runs after every failed tool call; the agent writes a short reflection into episodic memory and the next retry seeds the prompt with that trace.", "architecture", "technical", False,
     [("Reflexion", "pattern"), ("self-critique", "pattern"), ("episodic memory", "concept"), ("retry", "pattern")],
     [("Reflexion", "episodic memory", "USES")],
     "how does the Reflexion loop seed the next retry after a failed tool call",
     "reflexion self critique episodic memory retry tool call trace"),
    # --- 17 ---
    ("Chain-of-Thought decoding is off in production for cost reasons; the CoT trace only runs in the eval harness where we score intermediate steps against a rubric.", "decision", "technical", False,
     [("Chain-of-Thought", "pattern"), ("CoT", "pattern"), ("eval harness", "project"), ("rubric", "concept")],
     [("Chain-of-Thought", "eval harness", "APPLIES_TO")],
     "where does Chain-of-Thought decoding actually run in the stack and why not production",
     "chain of thought cot production eval harness rubric cost score"),
    # --- 18 ---
    ("Tree-of-Thoughts search is wired for the planner on puzzle-style tasks; branching factor is capped at four and a value prompt scores each branch before expansion.", "architecture", "technical", False,
     [("Tree-of-Thoughts", "pattern"), ("value prompt", "pattern"), ("planner", "pattern")],
     [("Tree-of-Thoughts", "value prompt", "USES")],
     "which search pattern drives the planner on puzzle tasks and how are branches scored",
     "tree of thoughts tot planner branch value prompt score expand"),
    # --- 19 ---
    ("OpenAI Assistants API powers the hosted chat surface but not the core agent; thread persistence and code-interpreter are nice but tool schema portability pushed us off it for backend flows.", "decision", "technical", False,
     [("OpenAI Assistants API", "api"), ("code-interpreter", "tool"), ("tool schema", "concept"), ("backend flows", "project")],
     [("OpenAI Assistants API", "backend flows", "APPLIES_TO")],
     "which surface still uses the Assistants API and why did backend flows leave it",
     "openai assistants api code interpreter thread schema portability backend"),
    # --- 20 ---
    ("Anthropic computer use is the tool behind the desktop automation agent; screenshots ship back to Claude as images and the action loop is capped at thirty steps per session to contain runaway behaviour.", "architecture", "technical", False,
     [("Anthropic computer use", "tool"), ("Claude", "service"), ("desktop automation agent", "project"), ("action loop", "pattern")],
     [("desktop automation agent", "Anthropic computer use", "USES")],
     "which tool drives the desktop automation agent and what limit contains runaway behaviour",
     "anthropic computer use claude desktop automation action loop cap"),
    # --- 21 ---
    ("Agent planning split into a plan phase and an act phase; the plan is a typed list of step objects validated against a JSON schema before the executor is allowed to start pulling tools.", "architecture", "technical", False,
     [("plan phase", "pattern"), ("act phase", "pattern"), ("step objects", "pattern"), ("JSON schema", "pattern")],
     [("plan phase", "JSON schema", "USES")],
     "how did agent planning split into phases and where does schema validation fit in the pipeline",
     "plan phase act phase step object json schema validate agent"),
    # --- 22 ---
    ("Scratchpad memory lives in a per-session Redis list; each tool call appends a structured trace entry and the prompt builder truncates oldest entries when the budget is under two thousand tokens.", "architecture", "technical", False,
     [("Scratchpad", "pattern"), ("Redis", "database"), ("prompt builder", "pattern"), ("trace entry", "concept")],
     [("Scratchpad", "Redis", "DEPLOYED_ON")],
     "where does scratchpad memory live per session and how does the builder respect the token budget",
     "scratchpad redis session tool trace prompt builder truncate budget"),
    # --- 23 ---
    ("Multi-agent orchestration uses a supervisor plus workers topology; the supervisor holds the task graph while workers are stateless and only see the messages pinned by the router for their turn.", "architecture", "technical", False,
     [("supervisor plus workers", "pattern"), ("task graph", "pattern"), ("router", "pattern"), ("stateless", "pattern")],
     [("supervisor plus workers", "task graph", "USES")],
     "which topology shapes the multi-agent orchestration and how do workers avoid global state",
     "supervisor worker topology task graph router stateless message pin"),
    # --- 24 ---
    ("Tool schemas are authored once as JSON Schema and codegen emits Python TypedDicts, Pydantic models, and the OpenAI tools array; drift between client and server definitions stopped in the second week.", "decision", "technical", False,
     [("JSON Schema", "pattern"), ("TypedDict", "pattern"), ("Pydantic", "library"), ("OpenAI tools array", "api")],
     [("JSON Schema", "TypedDict", "PRODUCES"), ("JSON Schema", "Pydantic", "PRODUCES")],
     "how did authoring tool schemas in one place eliminate client-server drift for the agent",
     "json schema typeddict pydantic openai tools codegen drift author"),
    # --- 25 ---
    ("JSON mode is the minimum bar for structured outputs on OpenAI; we still prefer response_format with a JSON Schema when available because pure JSON mode does not catch enum violations.", "preference", "technical", False,
     [("JSON mode", "pattern"), ("response_format", "api"), ("JSON Schema", "pattern"), ("enum violation", "error")],
     [("response_format", "JSON mode", "IMPROVES_ON")],
     "which structured-output setting does the team prefer on OpenAI and what does plain JSON mode miss",
     "json mode response format schema enum violation openai structured"),
    # --- 26 ---
    ("Streaming with tool calls is the hot path; deltas are buffered per tool_call_id until the arguments parse as JSON, at which point the dispatcher fires the tool without waiting for the full message close.", "architecture", "technical", False,
     [("Streaming", "pattern"), ("tool_call_id", "concept"), ("dispatcher", "pattern"), ("deltas", "concept")],
     [("Streaming", "dispatcher", "COMMUNICATES_WITH")],
     "how does the streaming path dispatch tools before the assistant message is fully closed",
     "stream tool call delta buffer tool_call_id dispatch parse json"),
    # --- 27 ---
    ("Retry and refinement loop for malformed outputs: one re-ask with the validation error in the system tail, then a fallback to a smaller deterministic prompt; third failure raises to the caller instead of looping.", "decision", "technical", False,
     [("Retry and refinement loop", "pattern"), ("validation error", "error"), ("deterministic prompt", "pattern"), ("re-ask", "pattern")],
     [("Retry and refinement loop", "validation error", "FIXES")],
     "which retry and refinement ladder does the agent run on malformed outputs before giving up",
     "retry refinement loop validation error re ask deterministic fallback"),
    # --- 28 ---
    ("LangGraph checkpointer is SQLite for dev and Postgres for prod; the thread id keys the state blob so a resumed session rebuilds the agent scratchpad exactly from the last persisted node.", "fact", "technical", False,
     [("LangGraph", "framework"), ("checkpointer", "pattern"), ("SQLite", "database"), ("Postgres", "database")],
     [("checkpointer", "Postgres", "DEPLOYED_ON")],
     "where does LangGraph persist its checkpoints across dev and prod and what key rebuilds the state",
     "langgraph checkpointer sqlite postgres thread id state resume blob"),
    # --- 29 ---
    ("LlamaIndex query engines wrap the vector store and the fusion retriever; BM25 plus dense is the default and the reranker stage is a cross-encoder called only when top_k exceeds twenty.", "fact", "technical", False,
     [("LlamaIndex", "framework"), ("query engine", "pattern"), ("BM25", "algorithm"), ("cross-encoder", "algorithm")],
     [("query engine", "BM25", "USES")],
     "which retrieval stack does the LlamaIndex query engine default to and when does the reranker kick in",
     "llamaindex query engine bm25 dense fusion cross encoder rerank top k"),
    # --- 30 ---
    ("CrewAI hierarchical mode is off by default; the flat sequential crew proved easier to debug and the manager agent only gets enabled for the long-form writing workflow where planning really pays off.", "preference", "technical", False,
     [("CrewAI", "framework"), ("hierarchical mode", "pattern"), ("sequential crew", "pattern"), ("manager agent", "pattern")],
     [("sequential crew", "hierarchical mode", "PREFERS")],
     "which CrewAI mode is the default and where does the hierarchical manager agent actually get enabled",
     "crewai hierarchical sequential crew manager agent debug long form"),
    # --- 31 ---
    ("AutoGen Studio is useful as a design surface but the deployed agents run in a headless AutoGen Python worker; the Studio project file compiles to a Python module during CI so the two stay in sync.", "milestone", "technical", False,
     [("AutoGen Studio", "tool"), ("AutoGen", "framework"), ("Python worker", "pattern"), ("CI", "service")],
     [("AutoGen Studio", "Python worker", "PRODUCES")],
     "how do AutoGen Studio designs reach the deployed headless workers without drift",
     "autogen studio python worker ci project compile module deploy headless"),
    # --- 32 ---
    ("Semantic Kernel planners got replaced with a handwritten plan function because the Handlebars planner kept emitting plans that referenced plugins the runtime had already unloaded.", "problem", "technical", False,
     [("Semantic Kernel", "framework"), ("Handlebars planner", "pattern"), ("handwritten plan function", "pattern"), ("plugin", "concept")],
     [("handwritten plan function", "Handlebars planner", "REPLACES")],
     "which Semantic Kernel planner got retired and what failure mode forced the switch",
     "semantic kernel handlebars planner handwritten plan plugin unload"),
    # --- 33 ---
    ("Haystack document store is OpenSearch for full-text and Qdrant for vectors; the hybrid retriever node calls both in parallel and fuses scores with reciprocal rank fusion before the reader stage.", "architecture", "technical", False,
     [("Haystack", "framework"), ("OpenSearch", "database"), ("Qdrant", "database"), ("reciprocal rank fusion", "algorithm")],
     [("Haystack", "OpenSearch", "USES"), ("Haystack", "Qdrant", "USES")],
     "which two stores does Haystack fan out to and how does it fuse their scores before the reader",
     "haystack opensearch qdrant hybrid reciprocal rank fusion reader parallel"),
    # --- 34 ---
    ("DSPy Teleprompter compiled a ChainOfThought module for the classifier and lifted accuracy from 71 to 84 on the dev split without touching the signature; the bootstrapped demos carried the win.", "milestone", "technical", False,
     [("DSPy", "framework"), ("Teleprompter", "tool"), ("ChainOfThought", "pattern"), ("classifier", "project")],
     [("Teleprompter", "ChainOfThought", "PRODUCES")],
     "which DSPy compiler produced the classifier accuracy jump and which signature feature stayed untouched",
     "dspy teleprompter chain of thought classifier accuracy bootstrap demo"),
    # --- 35 ---
    ("Instructor's retry kwarg caps at three by default; we dropped it to two after measuring that a third retry almost never flipped the outcome and mostly burned budget on the 4o-mini tier.", "decision", "technical", False,
     [("Instructor", "library"), ("retry kwarg", "config"), ("4o-mini", "technology")],
     [],
     "why did the team drop Instructor's retry cap from three to two on the 4o-mini tier",
     "instructor retry kwarg cap 4o mini budget third flip outcome"),
    # --- 36 ---
    ("Guidance's select primitive replaced a hand-rolled regex for multiple-choice grading; the model can only pick one of the given options and the previous string-matching post-processor is gone.", "decision", "technical", False,
     [("Guidance", "library"), ("select primitive", "pattern"), ("regex", "pattern"), ("multiple-choice", "pattern")],
     [("select primitive", "regex", "REPLACES")],
     "which Guidance primitive replaced hand-rolled regex for multiple-choice grading",
     "guidance select primitive regex multiple choice grade post process"),
    # --- 37 ---
    ("Outlines FSM-based generation fits naturally on top of vLLM and llama.cpp; the backend adapter layer covers both without the caller ever seeing the token-logit manipulation underneath.", "fact", "technical", False,
     [("Outlines", "library"), ("FSM", "algorithm"), ("vLLM", "framework"), ("llama.cpp", "framework")],
     [("Outlines", "vLLM", "DEPLOYED_ON"), ("Outlines", "llama.cpp", "DEPLOYED_ON")],
     "which runtimes back the Outlines FSM generator and what does the adapter layer hide",
     "outlines fsm vllm llama cpp adapter token logit generate"),
    # --- 38 ---
    ("MCP resources versus tools is the cleanest mental split: resources are readable by reference and tools are side-effecting actions; conflating them caused a cache-invalidation mess in the first draft.", "reference", "technical", False,
     [("MCP", "protocol"), ("resource", "concept"), ("tool", "concept"), ("cache-invalidation", "concept")],
     [("resource", "tool", "RELATED_TO")],
     "what is the cleanest split between MCP resources and tools and which bug did conflation cause",
     "mcp resource tool cache invalidation readable side effect split"),
    # --- 39 ---
    ("Tool schemas declare idempotency explicitly; the agent is allowed to retry idempotent tools freely but non-idempotent ones require an explicit user confirmation before the second call goes out.", "reference", "technical", False,
     [("Tool schemas", "concept"), ("idempotency", "concept"), ("retry", "pattern"), ("user confirmation", "pattern")],
     [("idempotency", "retry", "APPLIES_TO")],
     "when is the agent allowed to fire a second call without asking the user first",
     "tool schema idempotency retry confirmation user non idempotent gate"),
    # --- 40 ---
    ("JSON mode combined with a post-hoc Pydantic validation plus one re-ask is the pragmatic default for providers without strict schema mode; it costs a round trip on about two percent of calls.", "reference", "technical", False,
     [("JSON mode", "pattern"), ("Pydantic", "library"), ("re-ask", "pattern"), ("strict schema mode", "pattern")],
     [("re-ask", "JSON mode", "IMPROVES_ON")],
     "which pragmatic default combines JSON mode with Pydantic and re-ask for non-strict providers",
     "json mode pydantic re ask strict schema round trip default"),
    # --- 41 ---
    ("Streaming responses over SSE feed a token-by-token UI while the tool dispatcher listens for delta arguments on a side channel; the two consumers never block each other in the frontend loop.", "architecture", "technical", False,
     [("SSE", "protocol"), ("tool dispatcher", "pattern"), ("side channel", "pattern"), ("frontend loop", "pattern")],
     [("SSE", "tool dispatcher", "COMMUNICATES_WITH")],
     "how does the stream split between a token UI and the tool dispatcher without blocking",
     "sse stream token ui tool dispatcher side channel frontend block"),
    # --- 42 ---
    ("Refinement loop for code-writing agents is bounded by a sandbox-runner verdict; a failing test feeds the trace back into the prompt and the loop gives up after three failed fixes to preserve budget.", "problem", "technical", False,
     [("Refinement loop", "pattern"), ("code-writing agents", "project"), ("sandbox-runner", "tool"), ("trace", "concept")],
     [("Refinement loop", "sandbox-runner", "USES")],
     "which verdict bounds the code-agent refinement loop and what triggers the give-up path",
     "refine loop code agent sandbox runner trace fail fix budget"),
    # --- 43. noise ---
    ("Someone brought in a cat-shaped cookie jar for the team snack shelf and it has been empty for six working days in a row.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("LangSmith traces every agent run and the cost-per-step chart exposed a hot prompt that was pulling a twelve-thousand-token context for a trivial classification; trimming the retriever fixed it.", "problem", "technical", False,
     [("LangSmith", "tool"), ("cost-per-step", "pattern"), ("retriever", "pattern"), ("classification", "pattern")],
     [("LangSmith", "retriever", "APPLIES_TO")],
     "which observability view surfaced the bloated classification prompt and what was the fix",
     "langsmith trace cost per step retriever classification prompt bloat"),
    # --- 45 ---
    ("ReAct traces are stored verbatim in the eval corpus because fine-tuning a smaller model on them recovered about eighty percent of the big model's tool-calling accuracy at a fifth of the spend.", "milestone", "technical", False,
     [("ReAct", "pattern"), ("eval corpus", "project"), ("fine-tuning", "method"), ("tool-calling accuracy", "concept")],
     [("ReAct", "fine-tuning", "APPLIES_TO")],
     "why do we keep ReAct traces verbatim in the eval corpus and what downstream training used them",
     "react trace eval corpus fine tune small model tool accuracy"),
    # --- 46 ---
    ("Preference is Anthropic tool_use blocks for multi-step flows over OpenAI function calls; the explicit input and output blocks make parallel tools cleaner to trace in the message history.", "preference", "technical", False,
     [("Anthropic", "organization"), ("tool_use", "api"), ("OpenAI function calls", "api"), ("message history", "concept")],
     [("tool_use", "OpenAI function calls", "PREFERS")],
     "which tool-calling API does the team prefer for multi-step flows and which feature tipped the choice",
     "anthropic tool use openai function call multi step parallel trace"),
    # --- 47 ---
    ("Planning with ToT plus tool use saw diminishing returns past a branching factor of five; the empirical sweet spot for the research agent settled at three with depth four.", "reference", "technical", False,
     [("ToT", "pattern"), ("tool use", "pattern"), ("branching factor", "concept"), ("research agent", "project")],
     [("ToT", "tool use", "RELATED_TO")],
     "what branching factor and depth settled as the ToT sweet spot for the research agent",
     "tot tool use branching factor depth research agent sweet spot"),
    # --- 48 ---
    ("MCP sampling lets tools call back into the host model; we keep it disabled on untrusted servers because a malicious sampler could otherwise bill tokens against the user without an audit trail.", "reference", "technical", False,
     [("MCP", "protocol"), ("sampling", "pattern"), ("untrusted server", "concept"), ("audit trail", "concept")],
     [("MCP", "sampling", "HAS_PART")],
     "which MCP feature is locked down on untrusted servers and what abuse does the policy prevent",
     "mcp sampling untrusted server malicious token bill audit disable"),
    # --- 49 ---
    ("Prefer Outlines over Guidance for server-side structured output because the JSON Schema path is first-class and the library integrates cleanly with the vLLM logit processor extension point.", "preference", "technical", False,
     [("Outlines", "library"), ("Guidance", "library"), ("JSON Schema", "pattern"), ("vLLM", "framework")],
     [("Outlines", "Guidance", "PREFERS")],
     "which structured-output library wins server-side for JSON Schema work with vLLM",
     "outlines guidance json schema vllm logit processor server side"),
    # --- 50 ---
    ("Session summary: consolidated to LangGraph plus MCP plus Instructor as the backbone; DSPy handles prompt compilation offline and LlamaIndex stays for retrieval. CrewAI keeps the creative-writing lane.", "fact", "technical", False,
     [("LangGraph", "framework"), ("MCP", "protocol"), ("Instructor", "library"), ("DSPy", "framework"), ("LlamaIndex", "framework"), ("CrewAI", "framework")],
     [("LangGraph", "MCP", "COMMUNICATES_WITH"), ("LangGraph", "Instructor", "USES")],
     "which backbone stack did the team consolidate on and which lane kept CrewAI as the primary driver",
     "langgraph mcp instructor dspy llamaindex crewai backbone consolidate lane"),
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
