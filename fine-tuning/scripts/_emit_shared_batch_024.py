"""One-off emitter for shared-base batch-024 — technical domain (ML infra / LLM serving slice).

Writes 50 rows to data/v2/shared/batch_024.tmp.jsonl with ids shared-01151..01200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_024.tmp.jsonl"
ID_OFFSET = 1150

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("vLLM continuous batching raised generation throughput 3x over the old static batcher; PagedAttention kept memory flat.", "milestone", "technical", False,
     [("vLLM", "framework"), ("PagedAttention", "algorithm")],
     [],
     "which serving runtime tripled generation throughput without blowing up memory",
     "continuous batch dynamic request throughput GPU"),
    # --- 2 ---
    ("TensorRT-LLM compiled kernels beat vLLM on single-stream latency for the summarisation endpoint; vLLM still wins on concurrency.", "fact", "technical", False,
     [("TensorRT-LLM", "framework"), ("vLLM", "framework")],
     [],
     "which engine wins for single-request latency versus many concurrent streams",
     "compiled kernel single stream concurrency tradeoff engine"),
    # --- 3 ---
    ("Triton Inference Server backs the multi-model gateway; its ensemble scheduler pipelines a reranker behind the generator.", "architecture", "technical", False,
     [("Triton Inference Server", "service")],
     [],
     "how are multiple models chained behind one HTTP endpoint in our setup",
     "ensemble pipeline reranker chained serving backend"),
    # --- 4 ---
    ("Ray Serve took over from Flask wrappers for model endpoints; autoscaling replicas per deployment cut idle cost noticeably.", "decision", "technical", False,
     [("Ray Serve", "framework"), ("Flask", "framework")],
     [("Ray Serve", "Flask", "REPLACES")],
     "which serving layer replaced the ad-hoc Python web wrappers",
     "replica autoscale deployment python wrapper retire"),
    # --- 5 ---
    ("KServe on Kubernetes exposes the batch scoring jobs via InferenceService CRDs; canary rollout moved to traffic-percentage splits.", "architecture", "technical", False,
     [("KServe", "framework"), ("Kubernetes", "platform"), ("InferenceService", "api")],
     [],
     "how are batch scoring jobs exposed and canaried in the cluster today",
     "CRD inference canary traffic split rollout"),
    # --- 6 ---
    ("BentoML packaging beat hand-rolled Dockerfiles for Python dependency pinning; bentos ship straight into the model registry.", "preference", "technical", False,
     [("BentoML", "framework"), ("Docker", "tool"), ("Python", "language")],
     [("BentoML", "Docker", "PREFERS")],
     "which packaging tool the team picked for model containers and why",
     "packaging python pinning registry artifact prefer"),
    # --- 7 ---
    ("Modal Labs hosts the bursty embedding backfills; cold-start under two seconds via pre-built images beat our own Lambda attempt.", "decision", "technical", False,
     [("Modal Labs", "service"), ("Lambda", "service")],
     [("Modal Labs", "Lambda", "REPLACES")],
     "which serverless provider runs the bursty embedding jobs now",
     "cold start bursty backfill serverless replace attempt"),
    # --- 8 ---
    ("RunPod spot GPUs cover overnight fine-tune jobs; checkpoint-on-preempt hooks made eviction survivable.", "architecture", "technical", False,
     [("RunPod", "service")],
     [],
     "how do overnight training jobs survive on preemptible GPU hosts",
     "spot GPU preempt checkpoint eviction overnight training"),
    # --- 9 ---
    ("MLflow tracking holds every fine-tune run; promoting to the registry requires a signed eval report attached as an artifact.", "architecture", "technical", False,
     [("MLflow", "service")],
     [],
     "what gating step stands between a finished run and a registered model",
     "tracking registry promotion eval artifact signed"),
    # --- 10. noise ---
    ("Hang on, let me check the queue depth.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Weights & Biases sweeps drove the LoRA hyperparameter search; the Bayesian strategy halved trials versus grid.", "decision", "technical", False,
     [("Weights & Biases", "service"), ("LoRA", "algorithm")],
     [],
     "which experiment tracker drove the adapter hyperparameter search",
     "sweep Bayesian grid adapter search trials reduced"),
    # --- 12 ---
    ("Comet was rejected for new projects in favour of Weights & Biases; shared dashboards across teams was the deciding factor.", "decision", "technical", False,
     [("Comet", "service"), ("Weights & Biases", "service")],
     [("Weights & Biases", "Comet", "REPLACES")],
     "which experiment platform is now the default for new projects",
     "tracker default shared dashboard cross team factor"),
    # --- 13 ---
    ("Neptune stayed on for the research group; per-experiment REST access suited the notebook-heavy workflow there.", "fact", "technical", False,
     [("Neptune", "service")],
     [],
     "which teams still run on the older experiment tracker and why",
     "research notebook REST per experiment kept"),
    # --- 14 ---
    ("Feast feature store serves the ranking features online via Redis and offline via Snowflake; one definition file for both paths.", "architecture", "technical", False,
     [("Feast", "framework"), ("Redis", "database"), ("Snowflake", "service")],
     [],
     "how are ranking features kept consistent between online and offline lookups",
     "feature store online offline parity definition single"),
    # --- 15 ---
    ("Tecton was considered but rejected on cost for the small ranking team; Feast plus Redis covered the lookup SLAs.", "decision", "technical", False,
     [("Tecton", "service"), ("Feast", "framework"), ("Redis", "database")],
     [("Feast", "Tecton", "REPLACES")],
     "which managed feature platform lost out to the self-hosted option",
     "managed feature cost small team SLA reject"),
    # --- 16 ---
    ("Hopsworks powered the earlier research cluster; governance features were strong but ops overhead did not scale with one engineer.", "problem", "technical", False,
     [("Hopsworks", "framework")],
     [],
     "what ended the earlier research feature platform experiment",
     "governance ops overhead one engineer retire platform"),
    # --- 17 ---
    ("Qdrant was rejected in favour of pgvector for the shared retrieval path; the team did not want a second database to run.", "decision", "technical", False,
     [("Qdrant", "database"), ("pgvector", "database")],
     [("pgvector", "Qdrant", "REPLACES")],
     "which vector store beat the dedicated engine and why",
     "vector store consolidation second database avoid"),
    # --- 18 ---
    ("Weaviate's hybrid BM25 + vector query returned cleaner top-10 results than Milvus on the internal eval set; we kept it for search.", "fact", "technical", False,
     [("Weaviate", "database"), ("BM25", "algorithm"), ("Milvus", "database")],
     [],
     "which vector database won the hybrid-ranking bake-off against Milvus",
     "hybrid lexical vector top-k eval search winner"),
    # --- 19 ---
    ("Milvus 2.4 stayed on the archival retrieval service; DiskANN indexes handled the 120 million vector corpus on local NVMe.", "architecture", "technical", False,
     [("Milvus 2.4", "database"), ("DiskANN", "algorithm"), ("NVMe", "technology")],
     [],
     "which index powers the 120-million-vector archival store on local disk",
     "disk ANN large corpus index archival retrieval"),
    # --- 20 ---
    ("LanceDB runs embedded in the desktop app; a single file per table keeps offline sync simple for field researchers.", "architecture", "technical", False,
     [("LanceDB", "database")],
     [],
     "which embedded vector store ships inside the desktop researcher app",
     "embedded single file offline sync desktop researcher"),
    # --- 21 ---
    ("Chroma was dropped from the prototype stack after its persistence story kept changing across minor releases.", "decision", "technical", False,
     [("Chroma", "database")],
     [],
     "which prototype vector store fell out of favour and why",
     "persistence churn minor release prototype drop"),
    # --- 22 ---
    ("pgvector's HNSW build time on the 40M-row table dropped after raising maintenance_work_mem to 8 GB; parallel workers finally engaged.", "problem", "technical", False,
     [("pgvector", "database"), ("HNSW", "algorithm")],
     [],
     "why was the big HNSW build slow until a memory knob changed",
     "index build maintenance memory parallel worker speedup"),
    # --- 23 ---
    ("BGE-large-en-v1.5 replaced the older MiniLM embedder for document retrieval; recall@20 climbed from 0.71 to 0.83 on the eval set.", "decision", "technical", False,
     [("BGE-large-en-v1.5", "framework"), ("MiniLM", "framework")],
     [("BGE-large-en-v1.5", "MiniLM", "REPLACES")],
     "which embedding model took over from MiniLM for document recall",
     "embedder swap recall eval retrieval document"),
    # --- 24 ---
    ("E5-Mistral-7B-Instruct is preferred for long-form passages; asymmetric query/passage prompts fit our multilingual help centre content.", "preference", "technical", False,
     [("E5-Mistral-7B-Instruct", "framework")],
     [],
     "which embedder suits long multilingual passages in the help centre",
     "long passage multilingual asymmetric prompt preference"),
    # --- 25 ---
    ("Jina embeddings v3 handled the 8k-token contracts corpus without chunking; the extended context simplified the pipeline.", "architecture", "technical", False,
     [("Jina embeddings v3", "framework")],
     [],
     "which embedder lets contracts flow through without chunk splitting",
     "long context contract corpus chunk avoidance pipeline"),
    # --- 26 ---
    ("Cohere's managed embed-v4 runs the customer-facing search; we accepted the per-call cost to dodge GPU ops.", "decision", "technical", False,
     [("Cohere", "service")],
     [],
     "which managed embedder powers the public search and why",
     "managed API cost GPU ops avoid public search"),
    # --- 27 ---
    ("NVIDIA MIG slices split the A100 into three 20 GB instances; the vLLM serving pod pinned to one slice, training got the rest.", "architecture", "technical", False,
     [("NVIDIA MIG", "technology"), ("A100", "technology"), ("vLLM", "framework")],
     [],
     "how is the big GPU partitioned between serving and training workloads",
     "GPU partition slice isolation serving training split"),
    # --- 28 ---
    ("NVIDIA MPS time-slicing replaced naive CUDA oversubscription for the notebook fleet; per-user memory caps stopped the thrash.", "decision", "technical", False,
     [("NVIDIA MPS", "technology"), ("CUDA", "technology")],
     [("NVIDIA MPS", "CUDA", "REPLACES")],
     "which GPU sharing scheme calmed the shared notebook fleet",
     "multi process service oversubscribe memory cap thrash"),
    # --- 29 ---
    ("xFormers memory-efficient attention cut training VRAM by 40 percent on the 7B model; FlashAttention-2 then shaved another 15.", "milestone", "technical", False,
     [("xFormers", "library"), ("FlashAttention-2", "algorithm")],
     [("FlashAttention-2", "xFormers", "IMPROVES_ON")],
     "which kernel stack delivered the big training VRAM savings",
     "attention kernel memory efficient stack VRAM reduction"),
    # --- 30 ---
    ("FlashAttention-3 on H100 pushed forward pass throughput 1.7x over FlashAttention-2; we upgraded the inference kernels first.", "decision", "technical", False,
     [("FlashAttention-3", "algorithm"), ("H100", "technology"), ("FlashAttention-2", "algorithm")],
     [("FlashAttention-3", "FlashAttention-2", "IMPROVES_ON")],
     "which Hopper-targeted kernel replaced the prior attention implementation",
     "Hopper kernel forward pass throughput inference upgrade"),
    # --- 31 ---
    ("AWQ 4-bit quantisation shipped the Llama-3-70B weights into a single 48 GB card; quality dropped under 0.5 MMLU points.", "decision", "technical", False,
     [("AWQ", "algorithm"), ("Llama-3-70B", "framework")],
     [],
     "which quantisation let the 70B model fit on a single 48 GB card",
     "4 bit weight quant single card quality regression"),
    # --- 32 ---
    ("GPTQ was tried first but AWQ beat it on perplexity at the same bitrate; we standardised on AWQ for production serving.", "decision", "technical", False,
     [("GPTQ", "algorithm"), ("AWQ", "algorithm")],
     [("AWQ", "GPTQ", "REPLACES")],
     "which quantisation method displaced GPTQ in the production serving stack",
     "perplexity same bitrate quant compare standard production"),
    # --- 33 ---
    ("bitsandbytes 8-bit optimizers cut optimizer-state memory for LoRA training; the full-precision baseline would not fit on the RTX 5060.", "fact", "technical", False,
     [("bitsandbytes", "library"), ("LoRA", "algorithm"), ("RTX 5060", "technology")],
     [],
     "which library made LoRA training fit on a consumer card",
     "8 bit optimizer state memory consumer GPU fit"),
    # --- 34. noise ---
    ("Gimme a sec to warm the cache.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("SmoothQuant activation scaling let us do W8A8 on the router model without an output quality regression.", "architecture", "technical", False,
     [("SmoothQuant", "algorithm")],
     [],
     "which method balances activation and weight ranges for clean W8A8 serving",
     "activation scaling weight quant balance regression free"),
    # --- 36 ---
    ("Speculative decoding with a 1B draft model sped the 70B target up 2.4x on common prompts; quality stays bit-exact on acceptance.", "milestone", "technical", False,
     [("Speculative decoding", "algorithm")],
     [],
     "which inference trick paired a small draft model with the big target model",
     "draft verify token accept speculative speedup target"),
    # --- 37 ---
    ("Medusa heads were evaluated against a separate draft model; the draft-model path won on latency variance at our batch sizes.", "decision", "technical", False,
     [("Medusa", "algorithm")],
     [],
     "which speculative approach lost to a plain draft model in our bake-off",
     "parallel head draft compare latency variance batch"),
    # --- 38 ---
    ("PagedAttention memory sharing between sibling requests saved 28 percent KV cache on the chat workload.", "milestone", "technical", False,
     [("PagedAttention", "algorithm")],
     [],
     "which mechanism shaved almost a third off KV memory on chat traffic",
     "KV page share sibling request memory reduction"),
    # --- 39 ---
    ("KV cache eviction moved from LRU to a priority-by-tokens-seen policy; long conversations stopped losing their system prompts.", "decision", "technical", False,
     [("LRU", "algorithm")],
     [],
     "which eviction change fixed long-chat system prompt drop-outs",
     "eviction policy priority tokens seen long chat fix"),
    # --- 40 ---
    ("LoRA adapter hot-swap at request time landed on 2026-03-02; each tenant now hits its own adapter without a cold reload.", "milestone", "technical", False,
     [("LoRA", "algorithm"), ("2026-03-02", "date")],
     [],
     "when did multi-tenant adapter switching go live without reloads",
     "adapter swap multi tenant hot release date"),
    # --- 41 ---
    ("LoRA rank 16 was preferred over rank 32 for on-disk adapter size; eval scores were within noise and serving memory halved.", "preference", "technical", False,
     [("LoRA", "algorithm")],
     [],
     "which adapter rank won on disk size without hurting quality",
     "rank choice disk size eval noise serving memory"),
    # --- 42 ---
    ("LangChain was dropped from the production RAG path; too much abstraction between prompts and retrieval slowed debugging.", "decision", "technical", False,
     [("LangChain", "framework")],
     [],
     "why did the production retrieval stack move off the popular orchestration library",
     "abstraction debug cost prompt retrieval drop reason"),
    # --- 43 ---
    ("LlamaIndex ingestion pipelines still load the knowledge base; node postprocessors slot into the custom serving layer cleanly.", "architecture", "technical", False,
     [("LlamaIndex", "framework")],
     [],
     "which ingestion library survived the RAG stack trim-down",
     "ingestion pipeline node postprocessor kept layer fit"),
    # --- 44 ---
    ("Haystack 2 was considered for the internal RAG but LlamaIndex's connector breadth made migration a wash; no move planned.", "decision", "technical", False,
     [("Haystack 2", "framework"), ("LlamaIndex", "framework")],
     [],
     "which retrieval framework lost out to the incumbent on connector coverage",
     "framework compare connector breadth migration wash"),
    # --- 45 ---
    ("Ragas scores drove the weekly eval; faithfulness and context recall are the two metrics the on-call actually reads.", "architecture", "technical", False,
     [("Ragas", "framework")],
     [],
     "which eval framework feeds the weekly retrieval dashboard",
     "faithfulness context recall weekly metric on-call"),
    # --- 46 ---
    ("Promptfoo runs pre-merge prompt regression checks; config-as-code lets reviewers see the diff without opening the eval UI.", "architecture", "technical", False,
     [("Promptfoo", "tool")],
     [],
     "which tool catches prompt regressions before merge without leaving the PR view",
     "prompt regression pre merge config code reviewer"),
    # --- 47 ---
    ("Helicone proxies the OpenAI traffic for log capture; per-user cost attribution fell out of the session header it injects.", "architecture", "technical", False,
     [("Helicone", "service"), ("OpenAI", "service")],
     [],
     "which proxy captures traffic and attributes cost per user automatically",
     "proxy log capture session header cost attribution"),
    # --- 48 ---
    ("Braintrust experiment views replaced a home-grown Jupyter dashboard; shared eval runs now survive a laptop reboot.", "decision", "technical", False,
     [("Braintrust", "service"), ("Jupyter", "tool")],
     [("Braintrust", "Jupyter", "REPLACES")],
     "which eval dashboard replaced the brittle notebook-based one",
     "eval dashboard notebook replace shared run persist"),
    # --- 49 ---
    ("Langfuse traces every LLM call from the chat app; span-level cost and latency fed the autoscaler's backpressure signal.", "architecture", "technical", False,
     [("Langfuse", "service")],
     [],
     "which observability tool feeds backpressure signals from LLM spans",
     "trace span cost latency backpressure autoscale feed"),
    # --- 50 ---
    ("LiteLLM gateway fronts every provider; prompt caching at the gateway hit 35 percent on the support assistant's system prompts.", "milestone", "technical", False,
     [("LiteLLM", "service")],
     [],
     "which gateway unified providers and started caching system prompts",
     "gateway unify provider prompt cache hit ratio"),
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
