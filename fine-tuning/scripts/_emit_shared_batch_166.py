"""One-off emitter for shared-base batch-166 — technical domain (retrieval-augmented generation and prompt engineering: chunking, reranking, HyDE, GraphRAG, prompt injection defences).

Writes 50 rows to data/v2/shared/batch_166.tmp.jsonl with ids shared-08251..08300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_166.tmp.jsonl"
ID_OFFSET = 8250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the naive fixed-size chunker for RecursiveCharacterTextSplitter with a 200-token overlap; retrieval recall on the legal corpus climbed eight points because clauses stopped getting sliced mid-sentence.", "decision", "technical", False,
     [("RecursiveCharacterTextSplitter", "algorithm"), ("fixed-size chunker", "algorithm"), ("legal corpus", "concept")],
     [("RecursiveCharacterTextSplitter", "fixed-size chunker", "REPLACES")],
     "which chunker replaced the naive fixed-size splitter and what overlap setting lifted legal recall",
     "recursive character splitter overlap legal corpus recall chunk"),
    # --- 2 ---
    ("Semantic chunking by sentence-embedding cosine drift replaced token-window chunking for the docs site; chunks now break on topic shifts and dense tutorial pages stopped spilling concepts across neighbours.", "architecture", "technical", False,
     [("Semantic chunking", "algorithm"), ("token-window chunking", "algorithm"), ("sentence-embedding", "concept")],
     [("Semantic chunking", "token-window chunking", "REPLACES")],
     "which chunking strategy replaced token-window splitting on the docs site and what boundary does it detect",
     "semantic chunking sentence embedding drift token window docs topic"),
    # --- 3 ---
    ("Parent-child retrieval indexes 300-token child chunks but returns the 1500-token parent to the LLM; precision of the dense lookup survives while context quality matches what a human researcher would send.", "reference", "technical", False,
     [("Parent-child retrieval", "pattern"), ("child chunks", "concept"), ("parent", "concept")],
     [],
     "how does parent-child retrieval keep dense-lookup precision while giving the LLM human-sized context",
     "parent child retrieval small index large context chunk llm"),
    # --- 4 ---
    ("HyDE generates a hypothetical answer with the LLM first, then embeds that synthetic passage for the dense search; the query-to-passage distribution mismatch that tanked zero-shot recall on FAQ style prompts disappeared.", "decision", "technical", False,
     [("HyDE", "method"), ("zero-shot recall", "concept"), ("FAQ", "concept")],
     [],
     "which technique embeds a synthetic answer to fix the query-to-passage distribution gap on FAQ prompts",
     "hyde hypothetical document embedding synthetic answer faq recall"),
    # --- 5 ---
    ("Query expansion through an LLM rewrite generates five paraphrased variants per user query; the union of top-10 from each variant feeds MMR dedup, and ambiguous short queries finally surface the right doc.", "architecture", "technical", False,
     [("Query expansion", "method"), ("MMR", "algorithm"), ("LLM rewrite", "pattern")],
     [("Query expansion", "MMR", "USES")],
     "how does LLM-driven query expansion improve recall on ambiguous short queries without duplicate bloat",
     "query expansion paraphrase mmr dedup short ambiguous llm rewrite"),
    # --- 6 ---
    ("Query decomposition splits a multi-hop question into atomic sub-queries via a planner prompt; each sub-query retrieves independently and the synthesiser stitches cited paragraphs before the final answer.", "architecture", "technical", False,
     [("Query decomposition", "method"), ("planner prompt", "pattern"), ("synthesiser", "pattern")],
     [],
     "how does query decomposition handle multi-hop questions and what role does the synthesiser play",
     "query decomposition multi hop sub query planner synthesise cite"),
    # --- 7 ---
    ("Step-back prompting asks the LLM for a more general background question first; retrieving against that abstraction catches the conceptual prerequisites that a verbatim query would miss on tricky reasoning prompts.", "decision", "technical", False,
     [("Step-back prompting", "method"), ("abstraction", "concept"), ("reasoning prompts", "concept")],
     [],
     "which prompting trick retrieves background context by abstracting the user question before searching",
     "step back prompting abstract background prerequisite reasoning general"),
    # --- 8 ---
    ("MMR with lambda=0.7 replaced top-k cosine in the retrieval stage; diversity-aware ranking cut near-duplicate chunks from the same page and the answer generator stopped repeating itself.", "decision", "technical", False,
     [("MMR", "algorithm"), ("top-k cosine", "algorithm"), ("lambda=0.7", "config")],
     [("MMR", "top-k cosine", "REPLACES")],
     "which diversity-aware reranker replaced top-k cosine and what lambda value tuned the tradeoff",
     "mmr maximal marginal relevance top k cosine diversity lambda 0.7"),
    # --- 9 ---
    ("BGE reranker v2-m3 sits behind the dense retriever as a cross-encoder rerank stage; nDCG@10 on the enterprise corpus gained six points over pure bi-encoder scores without a latency blow-up.", "milestone", "technical", False,
     [("BGE reranker v2-m3", "tool"), ("dense retriever", "pattern"), ("cross-encoder", "concept"), ("bi-encoder", "concept")],
     [("BGE reranker v2-m3", "dense retriever", "IMPROVES_ON")],
     "which cross-encoder reranker lifted nDCG over a pure bi-encoder stack by six points",
     "bge reranker v2 m3 cross encoder bi encoder ndcg dense rerank"),
    # --- 10. noise ---
    ("The lab kettle finally gave up last Tuesday and the replacement has a touch-panel interface that nobody actually trusts.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Cohere rerank-3 is the fallback when self-hosted rerankers are unavailable; the hosted API adds 40 ms per query but consistently beats in-house bi-encoder scores on the support-ticket corpus.", "fact", "technical", False,
     [("Cohere rerank-3", "service"), ("bi-encoder", "concept"), ("support-ticket corpus", "concept")],
     [("Cohere rerank-3", "bi-encoder", "IMPROVES_ON")],
     "which hosted reranker is the fallback when self-hosted ones are down and what is its latency cost",
     "cohere rerank 3 fallback hosted api support ticket bi encoder"),
    # --- 12 ---
    ("ColBERT-v2 late-interaction retrieval replaced the single-vector index for high-precision code search; token-level maxsim scoring catches function-name matches that mean-pooled embeddings blur together.", "decision", "technical", False,
     [("ColBERT-v2", "algorithm"), ("single-vector index", "algorithm"), ("maxsim", "method")],
     [("ColBERT-v2", "single-vector index", "REPLACES")],
     "which late-interaction retriever replaced a single-vector index for code search and why",
     "colbert v2 late interaction maxsim single vector code search token"),
    # --- 13 ---
    ("Contextual compression wraps the retriever in an LLMChainExtractor that keeps only sentences relevant to the query; token bills on long-document answers dropped forty percent with no measurable quality regression.", "reference", "technical", False,
     [("Contextual compression", "pattern"), ("LLMChainExtractor", "tool"), ("long-document", "concept")],
     [("LLMChainExtractor", "Contextual compression", "IMPLEMENTS")],
     "how did contextual compression cut token bills on long-document answers without quality loss",
     "contextual compression llm chain extractor token cost long document"),
    # --- 14 ---
    ("Self-query retriever parses the user prompt into a filter expression plus a semantic query; price ranges and date filters that used to be ignored now apply as proper metadata constraints on pgvector.", "reference", "technical", False,
     [("Self-query retriever", "pattern"), ("pgvector", "database"), ("metadata constraints", "concept")],
     [("Self-query retriever", "pgvector", "USES")],
     "how does the self-query retriever apply price and date filters as metadata constraints",
     "self query retriever metadata filter pgvector price date constraint"),
    # --- 15 ---
    ("Long-context Claude-3.5 handles the 200k-token onboarding packet directly; RAG was kept for the knowledge base where freshness and citation auditing matter more than raw recall over a frozen document.", "decision", "technical", False,
     [("Claude-3.5", "service"), ("RAG", "pattern"), ("onboarding packet", "concept")],
     [("Claude-3.5", "RAG", "REPLACES")],
     "when did long-context Claude replace RAG for onboarding material and where was RAG kept",
     "claude 3.5 long context rag onboarding packet knowledge freshness"),
    # --- 16 ---
    ("GraphRAG builds a community-summary layer over an entity graph extracted from the corpus; global questions like summarise the main themes that flat vector search could not answer now route through the graph.", "reference", "technical", False,
     [("GraphRAG", "framework"), ("community-summary", "pattern"), ("entity graph", "concept")],
     [("GraphRAG", "entity graph", "USES")],
     "which RAG variant uses community summaries over an entity graph to answer global thematic questions",
     "graphrag community summary entity graph global theme flat vector"),
    # --- 17 ---
    ("LightRAG supplanted the heavier GraphRAG pipeline for the wiki corpus; dual-level retrieval on low-level entities plus high-level themes delivers comparable answer quality at one-third the indexing cost.", "milestone", "technical", False,
     [("LightRAG", "framework"), ("GraphRAG", "framework"), ("dual-level retrieval", "method")],
     [("LightRAG", "GraphRAG", "REPLACES")],
     "which graph RAG variant replaced GraphRAG on the wiki corpus and what indexing cost did it save",
     "lightrag graphrag dual level retrieval wiki indexing cost cheaper"),
    # --- 18 ---
    ("Anthropic contextual retrieval prepends a 50-to-100-token chunk-specific context summary before embedding; retrieval failure rate on the reference benchmark fell by roughly 49 percent once the prefix was in place.", "milestone", "technical", False,
     [("Anthropic contextual retrieval", "method"), ("chunk-specific context", "pattern"), ("reference benchmark", "concept")],
     [],
     "which Anthropic retrieval trick prepends a context summary per chunk and what recall gain did it produce",
     "anthropic contextual retrieval chunk prefix summary failure rate"),
    # --- 19 ---
    ("Few-shot examples in the system prompt drive structured-extraction reliability; three diverse examples covering edge cases beats twelve near-duplicate ones when the model tends to pattern-match on surface form.", "preference", "technical", False,
     [("Few-shot examples", "pattern"), ("structured-extraction", "concept"), ("system prompt", "pattern")],
     [],
     "why do three varied demonstrations outperform a dozen near-duplicates when pattern-matching on surface form",
     "demonstration variety surface pattern edge case reliability"),
    # --- 20 ---
    ("System prompt layering splits role, task, constraints, and examples into four clearly labelled blocks; drift across a long conversation dropped because the model re-reads the constraints block on each turn.", "architecture", "technical", False,
     [("System prompt layering", "pattern"), ("role", "concept"), ("constraints", "concept")],
     [],
     "how does system-prompt layering into role, task, constraints, and examples reduce long-conversation drift",
     "system prompt layer role task constraint example block drift"),
    # --- 21 ---
    ("Output schemas enforced with Pydantic validated against the LLM's JSON output; malformed completions get a single retry with the validator error appended, and downstream parse errors vanished from the logs.", "decision", "technical", False,
     [("Pydantic", "library"), ("Output schemas", "pattern"), ("JSON", "technology")],
     [("Pydantic", "Output schemas", "IMPLEMENTS")],
     "how does Pydantic validation of LLM JSON output handle malformed completions without hard failures",
     "pydantic output schema json validation retry validator llm fail"),
    # --- 22 ---
    ("Refusal handling now classifies a model refusal before retrying; a policy-triggered refusal routes to a human reviewer while a safety-false-positive retries with a rephrased prompt and a clarifying system hint.", "problem", "technical", False,
     [("Refusal handling", "pattern"), ("policy-triggered refusal", "concept"), ("safety-false-positive", "concept")],
     [],
     "how does refusal handling split policy refusals from false positives and what happens to each",
     "refusal handling policy safety false positive retry reviewer route"),
    # --- 23 ---
    ("Prompt injection defences layer input sanitisation, instruction hierarchy, and a guard-LLM that flags adversarial spans; exfiltration attempts via document content dropped after the guard-LLM was put inline.", "milestone", "technical", False,
     [("Prompt injection", "pattern"), ("guard-LLM", "pattern"), ("instruction hierarchy", "pattern")],
     [("guard-LLM", "Prompt injection", "FIXES")],
     "which three defences stack for prompt injection and which layer caught exfiltration attempts",
     "prompt injection defence sanitise instruction hierarchy guard llm"),
    # --- 24 ---
    ("Hypothetical answer retrieval differs from HyDE: instead of embedding the answer, it uses the hypothetical text as a BM25 query to pull lexical matches that the dense model misses on rare acronyms.", "fact", "technical", False,
     [("Hypothetical answer retrieval", "method"), ("HyDE", "method"), ("BM25", "algorithm")],
     [("Hypothetical answer retrieval", "HyDE", "RELATED_TO")],
     "how does hypothetical answer retrieval differ from HyDE in how it uses the generated text",
     "hypothetical answer retrieval hyde bm25 lexical acronym dense"),
    # --- 25 ---
    ("Hybrid search fuses BM25 lexical scores with dense embeddings via reciprocal rank fusion; technical queries with model names and SKU codes stopped falling off the first page once the lexical leg was blended back in.", "decision", "technical", False,
     [("BM25", "algorithm"), ("reciprocal rank fusion", "algorithm"), ("Hybrid search", "pattern")],
     [("Hybrid search", "reciprocal rank fusion", "USES")],
     "which retrieval blend recovers the lexical leg so acronyms and SKU codes stop falling off page one",
     "hybrid bm25 dense rrf sku acronym lexical leg blend"),
    # --- 26 ---
    ("Chunk overlap was tuned from 50 to 150 tokens after ablation on the FiQA benchmark; recall at 10 improved about four points and the synthesiser stopped losing mid-sentence numeric values at chunk boundaries.", "fact", "technical", False,
     [("Chunk overlap", "config"), ("FiQA", "concept"), ("recall at 10", "concept")],
     [],
     "which ablation on FiQA drove the chunk-overlap change and what mid-sentence problem did it fix",
     "chunk overlap tune fiqa ablation recall 10 numeric boundary"),
    # --- 27 ---
    ("Sentence chunking with NLTK PunktSentenceTokenizer replaced whitespace splitting on the legal corpus; citations that span sentence boundaries were being fragmented before and dropped semantic coherence.", "problem", "technical", False,
     [("NLTK", "library"), ("PunktSentenceTokenizer", "tool"), ("whitespace splitting", "algorithm")],
     [("PunktSentenceTokenizer", "whitespace splitting", "REPLACES")],
     "which sentence tokeniser replaced whitespace splitting for legal chunking and what did it fix",
     "nltk punkt sentence tokeniser whitespace legal chunk citation boundary"),
    # --- 28 ---
    ("Reranker calibration trains an isotonic regressor on the raw cross-encoder scores so the top-1 is picked only when its calibrated confidence beats a 0.65 threshold; otherwise the pipeline asks for clarification.", "fact", "technical", False,
     [("isotonic regressor", "algorithm"), ("cross-encoder", "concept"), ("calibration", "method")],
     [("isotonic regressor", "cross-encoder", "APPLIES_TO")],
     "how does reranker calibration decide when to answer versus ask for clarification",
     "reranker calibration isotonic regressor cross encoder threshold confidence"),
    # --- 29 ---
    ("The retrieval eval harness now reports MRR, nDCG@10, and recall@20 per slice; paraphrase and typo slices drove the 2026-04 augmentation work once the breakdown made the weak spots visible.", "milestone", "technical", False,
     [("MRR", "concept"), ("nDCG@10", "concept"), ("recall@20", "concept")],
     [],
     "which three retrieval metrics does the eval harness report per slice and what did the breakdown expose",
     "mrr ndcg recall slice paraphrase typo augmentation eval harness"),
    # --- 30 ---
    ("Query routing sends dense-friendly conceptual questions to the vector store and exact-match lookups like order-ID patterns to Postgres full-text search; a tiny logistic classifier decides based on regex features.", "reference", "technical", False,
     [("Query routing", "pattern"), ("Postgres full-text search", "database"), ("logistic classifier", "algorithm")],
     [("Query routing", "logistic classifier", "USES")],
     "how does query routing pick between vector search and Postgres full-text search for each query",
     "query routing vector postgres full text logistic classifier regex"),
    # --- 31 ---
    ("The context-window budget allocator reserves 30 percent for system prompt and schema, 50 percent for retrieved context, and 20 percent for the answer; runaway retrieved context that starved the answer stopped.", "decision", "technical", False,
     [("context-window budget", "pattern"), ("system prompt", "pattern"), ("retrieved context", "concept")],
     [],
     "how does the context-window budget allocator split tokens across system, retrieval, and answer",
     "context window budget allocator system schema retrieval answer split"),
    # --- 32 ---
    ("LangChain ConversationalRetrievalChain with a history-aware rewriter rephrases follow-up questions using chat history before retrieval; pronoun-heavy multi-turn dialogs stopped retrieving the wrong entity.", "architecture", "technical", False,
     [("LangChain", "framework"), ("ConversationalRetrievalChain", "pattern"), ("history-aware rewriter", "pattern")],
     [("ConversationalRetrievalChain", "history-aware rewriter", "USES")],
     "which LangChain chain rephrases follow-up questions using history and what problem did it fix",
     "langchain conversational retrieval chain history rewriter pronoun turn"),
    # --- 33 ---
    ("Citations are appended as inline [S1], [S2] markers keyed to a footer source list; the system prompt requires a marker for every factual claim or the validator strips the answer and retries once.", "reference", "technical", False,
     [("Citations", "pattern"), ("validator", "pattern"), ("source list", "concept")],
     [],
     "how does the answer formatter enforce inline citation markers and what happens if they are missing",
     "citation marker inline source list validator retry factual claim"),
    # --- 34 ---
    ("Embedding model upgraded from text-embedding-ada-002 to text-embedding-3-large with Matryoshka truncation; 1536-dim truncation keeps storage flat while full 3072-dim is used for reranking hot queries.", "milestone", "technical", False,
     [("text-embedding-ada-002", "service"), ("text-embedding-3-large", "service"), ("Matryoshka", "method")],
     [("text-embedding-3-large", "text-embedding-ada-002", "REPLACES")],
     "which embedding model replaced ada-002 and how does Matryoshka balance storage versus rerank quality",
     "text embedding 3 large ada 002 matryoshka truncation storage rerank"),
    # --- 35 ---
    ("System prompts should state the desired failure mode explicitly: say I do not know rather than guess is a line we always include for RAG answers, and hallucination rates dropped noticeably in the eval set.", "preference", "technical", False,
     [("System prompts", "pattern"), ("failure mode", "concept"), ("hallucination", "concept")],
     [],
     "which one-line system-prompt rule cut hallucination rates in the RAG eval set",
     "system prompt failure mode do not know hallucination rag eval"),
    # --- 36 ---
    ("Citations are verified post-generation by re-embedding each claim sentence and checking overlap with the cited chunk; citations below 0.55 cosine get flagged and the answer is regenerated with tighter grounding.", "fact", "technical", False,
     [("re-embedding", "method"), ("cosine", "method"), ("claim sentence", "concept")],
     [],
     "how does post-generation citation verification detect hallucinated citations and what happens to them",
     "citation verification re embed cosine claim flag regenerate grounding"),
    # --- 37 ---
    ("Instruction hierarchy is enforced by tagging user content with <user> and tool output with <tool>; the system prompt tells the model that only <system> tags can update policy, which blocks most jailbreak attempts.", "decision", "technical", False,
     [("Instruction hierarchy", "pattern"), ("<system> tags", "pattern"), ("jailbreak", "pattern")],
     [("Instruction hierarchy", "jailbreak", "FIXES")],
     "how does tagged instruction hierarchy block jailbreak attempts from user content",
     "instruction hierarchy tag system user tool jailbreak block policy"),
    # --- 38 ---
    ("RAGAS evaluation scores faithfulness, answer relevance, and context precision on a held-out set; the faithfulness regression from 0.82 to 0.71 flagged a retrieval change before users noticed hallucinations.", "milestone", "technical", False,
     [("RAGAS", "tool"), ("faithfulness", "concept"), ("context precision", "concept")],
     [],
     "which RAG evaluation framework flagged a faithfulness regression before users saw hallucinations",
     "ragas faithfulness answer relevance context precision regression eval"),
    # --- 39 ---
    ("Qdrant is the vector store of choice for payload filtering plus HNSW; Weaviate was considered but payload indexing ergonomics and the BM42 hybrid story tipped the decision toward Qdrant.", "decision", "technical", False,
     [("Qdrant", "database"), ("Weaviate", "database"), ("HNSW", "algorithm"), ("BM42", "algorithm")],
     [("Qdrant", "Weaviate", "PREFERS")],
     "which vector store was picked over Weaviate and which features tipped the decision",
     "qdrant weaviate hnsw bm42 payload filter hybrid vector store pick"),
    # --- 40 ---
    ("Cross-encoder latency is capped by reranking only the top-50 bi-encoder candidates; deeper rerank pools kept bloating p99 without moving nDCG, so 50 became the ops-friendly default for production.", "fact", "technical", False,
     [("Cross-encoder", "concept"), ("bi-encoder", "concept"), ("top-50", "config")],
     [],
     "how many candidates does the cross-encoder rerank and what latency tradeoff drove that cap",
     "cross encoder rerank top 50 bi encoder p99 latency ndcg cap"),
    # --- 41 ---
    ("Small-to-big retrieval indexes single-sentence chunks and expands to the containing paragraph at response time; precision jumps on narrow factoid queries without losing the local context the LLM wants to cite.", "architecture", "technical", False,
     [("Small-to-big retrieval", "pattern"), ("single-sentence chunks", "concept"), ("paragraph", "concept")],
     [],
     "how does small-to-big retrieval combine sentence-level precision with paragraph-level context for citing",
     "small to big retrieval sentence paragraph factoid precision expand"),
    # --- 42 ---
    ("Negative examples in few-shot sets matter: adding three examples of what NOT to output alongside two positive ones cut the format-drift rate in half during long-context extraction passes.", "preference", "technical", False,
     [("Negative examples", "pattern"), ("few-shot sets", "pattern"), ("format-drift", "concept")],
     [],
     "why do negative examples in few-shot prompts help and what drift did they cut in half",
     "negative example few shot format drift extraction long context"),
    # --- 43. noise ---
    ("The new intern brought in that cursed bag of liquorice and nobody has the heart to tell them it has been aging on the shared desk for two weeks.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Token-window chunking stays as the fallback for logs and unstructured telemetry where sentence boundaries are meaningless; recursive and semantic splitters are reserved for prose-heavy corpora.", "preference", "technical", False,
     [("Token-window chunking", "algorithm"), ("recursive", "algorithm"), ("semantic splitters", "algorithm")],
     [],
     "when is token-window chunking preferred over recursive or semantic splitters and why",
     "token window chunking logs telemetry recursive semantic prose fallback"),
    # --- 45 ---
    ("Prompt template versioning ships every template with a semver in the metadata and logs it alongside each completion; regressions get bisected by version instead of spelunking through git blame on the prompts directory.", "architecture", "technical", False,
     [("Prompt template versioning", "pattern"), ("semver", "concept"), ("metadata", "concept")],
     [],
     "how does prompt-template versioning make regressions bisectable without spelunking through git blame",
     "prompt template versioning semver metadata log bisect regression"),
    # --- 46 ---
    ("Fusion-in-Decoder was evaluated against vanilla RAG for multi-document QA; FiD scored higher on long-form synthesis but the latency cost and T5 dependency pushed the decision back to RAG for production.", "problem", "technical", False,
     [("Fusion-in-Decoder", "framework"), ("RAG", "pattern"), ("T5", "service")],
     [("RAG", "Fusion-in-Decoder", "PREFERS")],
     "why did production stay on vanilla RAG over Fusion-in-Decoder despite the synthesis score win",
     "fusion in decoder fid rag multi document t5 latency cost synthesis"),
    # --- 47 ---
    ("Sparse-dense hybrid retrieval ships in pgvector via the halfvec type plus a tsvector column; one index query returns both candidates and RRF happens in SQL without a second roundtrip.", "architecture", "technical", False,
     [("pgvector", "database"), ("halfvec", "concept"), ("tsvector", "concept"), ("RRF", "algorithm")],
     [("pgvector", "RRF", "SUPPORTS")],
     "how does pgvector implement sparse-dense hybrid retrieval with RRF in a single query",
     "pgvector halfvec tsvector rrf hybrid sparse dense single query"),
    # --- 48 ---
    ("Retrieval cache keys include the normalised query plus the index version; bumping the embedding model invalidates the cache cleanly without a manual purge, and stale answers from the old model stopped leaking through.", "fact", "technical", False,
     [("Retrieval cache", "pattern"), ("index version", "concept"), ("embedding model", "concept")],
     [],
     "how does retrieval-cache keying avoid leaking stale answers when the embedding model is bumped",
     "retrieval cache key index version embedding model invalidate stale"),
    # --- 49 ---
    ("Chain-of-verification has the LLM draft an answer, generate verification questions, answer them from retrieval, and revise; extractive factual tasks hit measurably higher precision at the cost of a second LLM round trip.", "decision", "technical", False,
     [("Chain-of-verification", "method"), ("verification questions", "concept"), ("extractive factual", "concept")],
     [],
     "which multi-step prompting method drafts, verifies, and revises and what precision gain did it buy",
     "chain verification draft question answer revise extractive factual"),
    # --- 50 ---
    ("A retrieval-augmented answer that cites no chunk is treated as a soft refusal; the orchestrator returns a did-not-find response rather than letting the model fabricate when retrieval scored every candidate below floor.", "architecture", "technical", False,
     [("soft refusal", "pattern"), ("orchestrator", "pattern"), ("below floor", "concept")],
     [],
     "how does the orchestrator convert a zero-citation answer into a soft refusal instead of a fabrication",
     "soft refusal orchestrator retrieval floor no citation fabricate answer"),
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
