"""One-off emitter for shared-base batch-162 — technical domain (model serving and inference: Triton, vLLM, TGI, TensorRT-LLM, SGLang, LMDeploy, Ollama, Groq, Cerebras, batching, speculative decoding, KV cache, PagedAttention, quantization, autoscaling).

Writes 50 rows to data/v2/shared/batch_162.tmp.jsonl with ids shared-08051..08100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_162.tmp.jsonl"
ID_OFFSET = 8050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the 70B Llama backend from TGI to vLLM on the chat gateway; PagedAttention kept throughput steady under a bursty 200 rps load where TGI was queueing aggressively.", "decision", "technical", False,
     [("TGI", "service"), ("vLLM", "service"), ("PagedAttention", "algorithm"), ("Llama", "technology")],
     [("vLLM", "TGI", "REPLACES"), ("vLLM", "PagedAttention", "USES")],
     "which inference server replaced TGI for the chat gateway and which memory feature held throughput",
     "vllm tgi paged attention llama chat gateway throughput burst"),
    # --- 2 ---
    ("Continuous batching in vLLM merged prefill and decode tokens in the same step so small follow-up requests stopped waiting behind a long generation; median latency dropped about forty percent.", "architecture", "technical", False,
     [("Continuous batching", "pattern"), ("vLLM", "service"), ("prefill", "concept"), ("decode", "concept")],
     [("vLLM", "Continuous batching", "IMPLEMENTS")],
     "how did continuous batching in vLLM cut median latency for short follow-up requests",
     "continuous batching vllm prefill decode latency merge step"),
    # --- 3 ---
    ("The edge deployment runs llama.cpp with a Q4_K_M GGUF on a Jetson Orin; CPU-only fallback exists but real users never hit it because the iGPU offload holds tokens/sec above interactive.", "fact", "technical", False,
     [("llama.cpp", "library"), ("Q4_K_M", "config"), ("GGUF", "config"), ("Jetson Orin", "platform")],
     [("llama.cpp", "Jetson Orin", "DEPLOYED_ON")],
     "which quantised format and runtime pair drive the Jetson Orin edge deployment and how is CPU used",
     "llama cpp gguf q4 k m jetson orin igpu offload edge"),
    # --- 4 ---
    ("Ollama handles the local developer tier — one-command pull and serve beat the rolled Docker stack on onboarding; the ops team still keeps vLLM for production because OpenAI-style streaming isn't Ollama's strong suit.", "decision", "technical", False,
     [("Ollama", "service"), ("Docker", "technology"), ("vLLM", "service"), ("OpenAI", "api")],
     [("Ollama", "Docker", "REPLACES")],
     "which runtime owns the local dev tier and why does production still run vLLM instead",
     "ollama docker vllm developer local production streaming openai"),
    # --- 5 ---
    ("TensorRT-LLM with in-flight batching is the backbone for the 8xH100 production pod; the ahead-of-time compile step is painful but steady-state tokens/sec beat vLLM by a comfortable margin on the 70B.", "architecture", "technical", False,
     [("TensorRT-LLM", "library"), ("H100", "infrastructure"), ("in-flight batching", "pattern"), ("vLLM", "service")],
     [("TensorRT-LLM", "H100", "DEPLOYED_ON"), ("TensorRT-LLM", "vLLM", "IMPROVES_ON")],
     "which compiled runtime wins the 8xH100 pod over vLLM and what is the tradeoff",
     "tensorrt llm h100 in flight batching vllm compile tokens"),
    # --- 6 ---
    ("Triton Inference Server fronts the recommendation stack because the ensemble graph lets us chain a CPU preprocessor, a GPU embedder, and an ONNX ranker in one client call without three hops.", "decision", "technical", False,
     [("Triton Inference Server", "service"), ("ONNX", "protocol"), ("ensemble graph", "pattern")],
     [("Triton Inference Server", "ensemble graph", "USES")],
     "which server hosts the recommendation stack and what pattern collapses the three-hop pipeline",
     "triton ensemble onnx recommendation cpu gpu embedder rank"),
    # --- 7 ---
    ("Prefix caching in SGLang reused the system prompt's KV block across 14k sessions sharing the same system message, which cut the time-to-first-token for the agent fleet roughly by half.", "fact", "technical", False,
     [("SGLang", "service"), ("Prefix caching", "pattern"), ("KV block", "concept"), ("time-to-first-token", "concept")],
     [("SGLang", "Prefix caching", "IMPLEMENTS")],
     "which SGLang feature halved time-to-first-token across agent fleets sharing one system prompt",
     "sglang prefix cache kv block ttft agent system prompt share"),
    # --- 8 ---
    ("Picked LMDeploy's TurboMind backend over vLLM for the internal code-assist because the AWQ path on a single A100 held 180 tokens/sec where vLLM's GPTQ build stalled around 120 under the same prompts.", "decision", "technical", False,
     [("LMDeploy", "service"), ("TurboMind", "library"), ("vLLM", "service"), ("AWQ", "algorithm"), ("GPTQ", "algorithm"), ("A100", "infrastructure")],
     [("LMDeploy", "vLLM", "PREFERS"), ("TurboMind", "AWQ", "USES")],
     "which runtime plus quantisation combo beat vLLM on a single A100 for internal code-assist",
     "lmdeploy turbomind vllm awq gptq a100 tokens code assist"),
    # --- 9 ---
    ("Groq's LPU handles the latency-critical voice agent because first-token is consistently sub-50ms; we keep an OpenRouter fallback wired in so a Groq outage routes to Fireworks AI within the same second.", "architecture", "technical", False,
     [("Groq", "organization"), ("LPU", "infrastructure"), ("OpenRouter", "service"), ("Fireworks AI", "organization"), ("voice agent", "project")],
     [("Groq", "voice agent", "APPLIES_TO"), ("OpenRouter", "Fireworks AI", "COMMUNICATES_WITH")],
     "which LPU serves the voice agent path and how does the OpenRouter fallback stay sub-second",
     "groq lpu voice latency openrouter fireworks fallback first token"),
    # --- 10. noise ---
    ("The office coffee grinder started making a sound somewhere between a hairdryer and a modem; replacement burrs are on order but apparently backordered until May.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("BentoML packages the classifier service along with its tokenizer, thresholds, and a health probe into a single bento, and the deployment artefact goes to Modal for cold-start-aware autoscaling.", "architecture", "technical", False,
     [("BentoML", "framework"), ("Modal", "platform"), ("bento", "concept"), ("cold-start", "pattern")],
     [("BentoML", "Modal", "DEPLOYED_ON")],
     "which packaging tool bundles the classifier service and which platform handles cold-start autoscaling",
     "bentoml modal bento autoscale cold start classifier package"),
    # --- 12 ---
    ("Ray Serve orchestrates the multi-model graph across four nodes; each deployment has its own replica count and a shared Ray actor holds the feature store client so we don't reopen pools per call.", "architecture", "technical", False,
     [("Ray Serve", "framework"), ("Ray actor", "pattern"), ("feature store", "service")],
     [("Ray Serve", "Ray actor", "USES")],
     "how does Ray Serve avoid reopening feature-store pools and scale multi-model graphs across nodes",
     "ray serve actor feature store replica multi model graph pool"),
    # --- 13 ---
    ("Speculative decoding with a 1.1B draft model in front of the 70B target lifted throughput by roughly 1.8x on the summarisation queue; acceptance rate held at 0.62 on real user prompts.", "milestone", "technical", False,
     [("Speculative decoding", "algorithm"), ("draft model", "concept"), ("summarisation queue", "project")],
     [("Speculative decoding", "summarisation queue", "APPLIES_TO")],
     "which decoding trick gave the summarisation queue a 1.8x throughput win and what was acceptance",
     "speculative decoding draft target 70b acceptance summarisation throughput"),
    # --- 14 ---
    ("The KV cache eviction policy in the chat pod moved from LRU to an attention-score-weighted scheme; long-lived conversations survived the hot set for longer without pushing out high-importance tokens.", "decision", "technical", False,
     [("KV cache", "concept"), ("LRU", "algorithm"), ("attention-score-weighted", "algorithm"), ("chat pod", "infrastructure")],
     [("attention-score-weighted", "LRU", "REPLACES")],
     "which KV cache eviction policy replaced LRU in the chat pod and what conversation class benefited",
     "kv cache lru attention score evict chat pod long conversation"),
    # --- 15 ---
    ("PagedAttention lets vLLM store the KV cache in non-contiguous pages with a block table, so a 32k context request no longer reserves a huge contiguous slab up front and small requests stop starving.", "fact", "technical", False,
     [("PagedAttention", "algorithm"), ("vLLM", "service"), ("block table", "pattern"), ("KV cache", "concept")],
     [("vLLM", "PagedAttention", "USES")],
     "how does PagedAttention free long-context requests from reserving a contiguous KV slab",
     "paged attention vllm block table kv cache page 32k context"),
    # --- 16 ---
    ("Moved the stable-diffusion generation path from TorchServe to Ray Serve; the handler abstraction in TorchServe was fine for one model but broke down once we needed a LoRA router and a VAE decoder in the same graph.", "decision", "technical", False,
     [("TorchServe", "service"), ("Ray Serve", "framework"), ("stable-diffusion", "technology"), ("LoRA", "algorithm"), ("VAE", "algorithm")],
     [("Ray Serve", "TorchServe", "REPLACES")],
     "which server replaced TorchServe for the stable-diffusion path once LoRA routing entered the graph",
     "torch serve ray serve stable diffusion lora vae router handler"),
    # --- 17 ---
    ("Autoscaling the GPU pool on Modal is gated by queue depth rather than CPU; scale-out triggers when pending requests exceed twice the per-replica concurrency, and scale-in waits three minutes of idle.", "architecture", "technical", False,
     [("Modal", "platform"), ("GPU pool", "infrastructure"), ("Autoscaling", "pattern"), ("queue depth", "concept")],
     [("Modal", "Autoscaling", "CONFIGURES")],
     "which signal drives Modal's GPU autoscaling and what hysteresis keeps scale-in from flapping",
     "modal gpu autoscale queue depth concurrency scale in hysteresis"),
    # --- 18 ---
    ("Replicate hosted the first public demo of the model but the cost curve at 2k rps made it a non-starter; the production workload runs on Together AI at roughly a third the per-token rate.", "decision", "technical", False,
     [("Replicate", "platform"), ("Together AI", "organization")],
     [("Together AI", "Replicate", "REPLACES")],
     "which serverless host carried the public demo and why did production migrate to Together AI",
     "replicate together ai cost per token demo production migration"),
    # --- 19 ---
    ("Request coalescing on the embedding endpoint batches up to 32 incoming requests within a 3ms window before firing the GPU call; throughput doubled and p99 latency only drifted up by 2ms.", "architecture", "technical", False,
     [("Request coalescing", "pattern"), ("embedding endpoint", "api"), ("p99", "concept")],
     [],
     "how does request coalescing on the embedding endpoint trade a tiny p99 bump for double throughput",
     "request coalesce embed batch 32 window gpu p99 throughput"),
    # --- 20 ---
    ("Cerebras CS-3 runs the 405B inference benchmark at interactive speeds because the full model fits on-wafer and there is no cross-GPU all-reduce in the decode path, which kills latency on 8xH100 setups.", "fact", "technical", False,
     [("Cerebras", "organization"), ("CS-3", "infrastructure"), ("all-reduce", "algorithm"), ("H100", "infrastructure")],
     [("Cerebras", "all-reduce", "REPLACES")],
     "which Cerebras property lets the 405B hold interactive speed where 8xH100 stalls in decode",
     "cerebras cs 3 405b all reduce h100 wafer decode latency"),
    # --- 21 ---
    ("Fireworks AI is wired into the router as the primary for 70B completions because their fused FlashAttention-3 kernels come out-of-the-box on Hopper; we would have had to maintain that in vLLM ourselves.", "decision", "technical", False,
     [("Fireworks AI", "organization"), ("FlashAttention-3", "algorithm"), ("Hopper", "infrastructure"), ("vLLM", "service")],
     [("Fireworks AI", "FlashAttention-3", "USES")],
     "which provider became the primary for 70B completions and which kernel saved us from rolling our own",
     "fireworks ai flash attention 3 hopper vllm kernel 70b primary"),
    # --- 22 ---
    ("AWQ quantisation on the 13B routing model dropped VRAM from 26 GB to about 7.5 GB with a quality delta under 0.3 on the internal eval; GPTQ got close but the dequant kernel was measurably slower.", "milestone", "technical", False,
     [("AWQ", "algorithm"), ("GPTQ", "algorithm"), ("VRAM", "infrastructure"), ("routing model", "project")],
     [("AWQ", "GPTQ", "PREFERS")],
     "which quantisation cut the 13B router from 26 GB to 7.5 GB and why did GPTQ lose the comparison",
     "awq gptq 13b vram quantise routing dequant kernel eval"),
    # --- 23 ---
    ("Picked INT4 weight-only quantisation on TensorRT-LLM with activations kept in FP16 for the 70B; full INT4 activations had collapsed the function-calling format on the JSON eval set in bench.", "decision", "technical", False,
     [("INT4", "config"), ("TensorRT-LLM", "library"), ("FP16", "config"), ("function-calling", "pattern")],
     [("TensorRT-LLM", "INT4", "USES")],
     "how does TensorRT-LLM's INT4 weight-only path keep function-calling quality intact",
     "int4 tensorrt llm fp16 activation weight only function calling"),
    # --- 24 ---
    ("Scheduling inside vLLM uses a priority queue with a fairness shim: premium-tier requests get 3x weight but a long-running premium call cannot starve the free tier for more than 200ms of scheduler cycles.", "architecture", "technical", False,
     [("vLLM", "service"), ("priority queue", "algorithm"), ("fairness shim", "pattern")],
     [("vLLM", "priority queue", "USES")],
     "how does vLLM's scheduler weight premium traffic without starving the free tier past a 200ms bound",
     "vllm schedule priority queue fairness premium free starve 200ms"),
    # --- 25 ---
    ("Cold-start mitigation on Modal pins one always-on replica per region and snapshots the model into a persistent volume; a fresh container hydrates in roughly 4 seconds instead of the raw 45.", "problem", "technical", False,
     [("Modal", "platform"), ("Cold-start", "pattern"), ("persistent volume", "infrastructure"), ("region", "place")],
     [("Modal", "Cold-start", "FIXES")],
     "which Modal cold-start tricks brought container hydration down from 45 to about 4 seconds",
     "modal cold start always on replica snapshot volume hydrate"),
    # --- 26 ---
    ("Dynamic batching in Triton was tuned to max_queue_delay_microseconds of 2000 and preferred_batch_size of [4, 8, 16]; throughput climbed 3.2x with a p95 latency hit under 8ms on the classifier.", "fact", "technical", False,
     [("Triton", "service"), ("Dynamic batching", "pattern"), ("max_queue_delay_microseconds", "config"), ("preferred_batch_size", "config")],
     [("Triton", "Dynamic batching", "CONFIGURES")],
     "which two Triton dynamic-batching knobs pushed classifier throughput to 3.2x with minimal p95 impact",
     "triton dynamic batch max queue delay preferred size classifier"),
    # --- 27 ---
    ("The router normalises OpenRouter, Fireworks AI, Together AI, and Lepton AI behind one internal OpenAI-compatible schema so a failing provider gets swapped via config and no application code moves.", "architecture", "technical", False,
     [("OpenRouter", "service"), ("Fireworks AI", "organization"), ("Together AI", "organization"), ("Lepton AI", "organization"), ("OpenAI", "api")],
     [],
     "which abstraction lets the router swap Fireworks, Together, and Lepton without touching app code",
     "openrouter fireworks together lepton openai schema router swap"),
    # --- 28 ---
    ("LocalAI covers the air-gapped customer install because it re-exports OpenAI's endpoint shape on top of llama.cpp and ggml backends; the customer's SDK code ported across unchanged.", "fact", "technical", False,
     [("LocalAI", "service"), ("OpenAI", "api"), ("llama.cpp", "library"), ("ggml", "library")],
     [("LocalAI", "llama.cpp", "USES")],
     "which local runtime satisfies air-gapped installs by re-exporting OpenAI's endpoint shape",
     "localai openai llama cpp ggml air gapped customer sdk port"),
    # --- 29 ---
    ("Speculative decoding in vLLM needs the draft and target to share vocab; we tried a cross-vocab draft via tokenizer retargeting and acceptance tanked to 0.18, so the experiment got shelved.", "problem", "technical", False,
     [("Speculative decoding", "algorithm"), ("vLLM", "service"), ("tokenizer retargeting", "method"), ("vocab", "concept")],
     [],
     "why did the cross-vocab speculative decoding experiment in vLLM fail and what was the acceptance figure",
     "speculative decoding vllm cross vocab tokenizer retarget acceptance"),
    # --- 30 ---
    ("Turned on chunked prefill in vLLM after the 100k-context calls kept monopolising the GPU during peak; 512-token slices let decode for other requests interleave instead of queue.", "decision", "technical", False,
     [("chunked prefill", "pattern"), ("vLLM", "service"), ("decode", "concept")],
     [("vLLM", "chunked prefill", "IMPLEMENTS")],
     "how does chunked prefill in vLLM stop long-context requests from monopolising the GPU",
     "chunked prefill vllm 512 slice decode interleave 100k context peak"),
    # --- 31 ---
    ("Prometheus scrapes Triton's /metrics and vLLM's /metrics into the same dashboard; requests-in-flight plus gpu_cache_usage_perc are the two signals the on-call uses to spot saturation early.", "reference", "technical", False,
     [("Prometheus", "tool"), ("Triton", "service"), ("vLLM", "service"), ("gpu_cache_usage_perc", "config")],
     [("Prometheus", "Triton", "COMMUNICATES_WITH"), ("Prometheus", "vLLM", "COMMUNICATES_WITH")],
     "which two metrics from Triton and vLLM feed the on-call saturation dashboard via Prometheus",
     "prometheus triton vllm metrics dashboard gpu cache usage on call"),
    # --- 32 ---
    ("The reference deployment doc for the 70B pod lists vLLM 0.6.3, CUDA 12.4, NCCL 2.20, and an H100 with 80 GB HBM3 per card; older NCCL versions deadlock on TP=8 during graph capture.", "reference", "technical", False,
     [("vLLM", "service"), ("CUDA", "framework"), ("NCCL", "library"), ("H100", "infrastructure"), ("HBM3", "infrastructure")],
     [("vLLM", "CUDA", "DEPENDS_ON"), ("vLLM", "NCCL", "DEPENDS_ON")],
     "which pinned versions does the 70B pod reference doc call out and which older lib deadlocks at TP=8",
     "vllm cuda nccl h100 hbm3 70b tp 8 deadlock graph capture"),
    # --- 33 ---
    ("Tensor parallelism of 8 with pipeline parallelism of 1 won the 405B layout on a single 8xH100 node; PP=2 with TP=4 added an extra cross-stage bubble that decode could not hide.", "decision", "technical", False,
     [("Tensor parallelism", "algorithm"), ("pipeline parallelism", "algorithm"), ("H100", "infrastructure"), ("decode", "concept")],
     [("Tensor parallelism", "pipeline parallelism", "PREFERS")],
     "why did TP=8 with PP=1 beat TP=4 with PP=2 for the 405B on a single 8xH100 node",
     "tensor parallel pipeline 405b h100 tp 8 pp 1 bubble decode"),
    # --- 34 ---
    ("Preferred the Lepton AI managed vLLM over self-hosting for the 8B chat model because operating PagedAttention under spot-GPU churn was eating two engineer-days a week with no product upside.", "preference", "technical", False,
     [("Lepton AI", "organization"), ("vLLM", "service"), ("PagedAttention", "algorithm"), ("spot-GPU", "infrastructure")],
     [("Lepton AI", "vLLM", "USES")],
     "why did the 8B chat model land on Lepton AI managed vLLM instead of self-hosted PagedAttention",
     "lepton ai vllm paged attention spot gpu 8b chat managed self"),
    # --- 35 ---
    ("User's preference is to keep llama.cpp for the offline laptop demos even when Ollama would be easier; wrapping llama.cpp directly gives tighter control over n_batch, n_ubatch, and rope scaling knobs.", "preference", "technical", False,
     [("llama.cpp", "library"), ("Ollama", "service"), ("n_batch", "config"), ("n_ubatch", "config"), ("rope scaling", "config")],
     [("llama.cpp", "Ollama", "PREFERS")],
     "why does the user pick llama.cpp over Ollama for offline demos despite Ollama being easier",
     "llama cpp ollama offline demo n batch ubatch rope scale knob"),
    # --- 36 ---
    ("Prefix caching is on for the system-prompt bank but explicitly off for user prompts because leakage across tenants is unacceptable; the cache key includes tenant id to belt-and-braces the isolation.", "preference", "technical", False,
     [("Prefix caching", "pattern"), ("tenant", "concept"), ("cache key", "concept")],
     [],
     "how does the system keep prefix caching safe across tenants while still exploiting the system-prompt bank",
     "prefix cache tenant system prompt user leakage isolation key"),
    # --- 37 ---
    ("Preference: always run a small canary with a live traffic mirror before flipping a TensorRT-LLM engine upgrade into the main pool; a silent regression in attention sinks cost us two hours last quarter.", "preference", "technical", False,
     [("TensorRT-LLM", "library"), ("canary", "pattern"), ("traffic mirror", "pattern"), ("attention sinks", "algorithm")],
     [],
     "which rollout safeguard does the team require before a TensorRT-LLM engine swap and why",
     "tensorrt llm canary traffic mirror attention sink regression rollout"),
    # --- 38 ---
    ("vLLM worker processes hang during CUDA graph capture on TP=8 when NCCL_P2P_DISABLE is set; leaving that env var unset is now the documented baseline for the 70B pod launcher.", "fact", "technical", False,
     [("vLLM", "service"), ("NCCL_P2P_DISABLE", "config"), ("CUDA graph", "framework"), ("TP=8", "config")],
     [],
     "which env-var combination deadlocked vLLM workers at TP=8 and what was the minimal fix",
     "vllm nccl p2p disable cuda graph tp 8 deadlock worker hang"),
    # --- 39 ---
    ("OOMs on the 70B pod traced to leaked KV blocks when clients disconnected mid-stream; the abort path now runs free_seq in the scheduler before the socket close returns to the router.", "problem", "technical", False,
     [("OOM", "error"), ("KV blocks", "concept"), ("free_seq", "command"), ("scheduler", "pattern")],
     [("free_seq", "OOM", "FIXES")],
     "which leak caused OOMs on the 70B pod and how did the abort path stop stale KV blocks from piling up",
     "oom 70b kv block leak disconnect abort free seq scheduler"),
    # --- 40 ---
    ("Shipped the first production SGLang deployment on the agent platform on 2026-03-02; structured decoding with regex masks stopped the JSON-schema failures that vLLM guided decoding had left open.", "milestone", "technical", False,
     [("SGLang", "service"), ("structured decoding", "algorithm"), ("regex masks", "pattern"), ("vLLM", "service"), ("2026-03-02", "date")],
     [("SGLang", "vLLM", "REPLACES")],
     "when did SGLang ship on the agent platform and which decoding issue did it close versus vLLM",
     "sglang 2026 03 02 agent structured decoding regex mask json vllm"),
    # --- 41 ---
    ("Cut over the embedding fleet to Triton's TensorRT backend on 2026-02-14; p99 dropped from 42ms to 18ms on the catalog-search path and the CPU-fallback replicas were retired the same week.", "milestone", "technical", False,
     [("Triton", "service"), ("TensorRT", "library"), ("embedding fleet", "project"), ("2026-02-14", "date")],
     [("Triton", "TensorRT", "USES")],
     "which cutover in February 2026 moved embedding p99 from 42ms to 18ms on catalog search",
     "triton tensor rt embedding fleet 2026 02 14 p99 catalog search"),
    # --- 42 ---
    ("First speculative-decoding rollout to 100% of summarisation traffic landed on 2026-03-19; draft model was an eagle-style head trained on our own distillation corpus rather than a stock 1B checkpoint.", "milestone", "technical", False,
     [("speculative-decoding", "algorithm"), ("eagle-style head", "method"), ("distillation corpus", "concept"), ("2026-03-19", "date")],
     [],
     "which date saw speculative decoding roll to all summarisation traffic and what was unusual about the draft",
     "speculative decoding eagle distillation 2026 03 19 summarisation draft"),
    # --- 43 ---
    ("Peak milestone: sustained 12k tokens/sec across a single 8xH100 node running TensorRT-LLM with INT4 weights and FP8 KV cache; breaking 10k had been the Q1 goal and we cleared it by 2026-03-28.", "milestone", "technical", False,
     [("TensorRT-LLM", "library"), ("H100", "infrastructure"), ("INT4", "config"), ("FP8", "config"), ("2026-03-28", "date")],
     [("TensorRT-LLM", "H100", "DEPLOYED_ON")],
     "which throughput milestone did the 8xH100 TensorRT-LLM setup hit on 2026-03-28 and what was the Q1 target",
     "tensorrt llm h100 int4 fp8 kv 12k tokens 2026 03 28 q1 target"),
    # --- 44 ---
    ("Chose to migrate the classifier fleet off Ray Serve onto BentoML because the bento build artefact was easier to sign and promote through the internal artefact registry on each release.", "decision", "technical", False,
     [("Ray Serve", "framework"), ("BentoML", "framework"), ("artefact registry", "service")],
     [("BentoML", "Ray Serve", "REPLACES")],
     "what drove the classifier-fleet move off Ray Serve to BentoML and what ops concern did it address",
     "ray serve bentoml classifier fleet artefact registry sign promote"),
    # --- 45 ---
    ("Graduated the Groq path from canary to primary for voice on 2026-04-05 after two weeks of side-by-side error-rate parity; the Fireworks AI fallback stays armed at 10% of traffic as a warm pool.", "milestone", "technical", False,
     [("Groq", "organization"), ("Fireworks AI", "organization"), ("voice", "project"), ("2026-04-05", "date")],
     [("Groq", "voice", "APPLIES_TO")],
     "when did Groq become primary for voice and how is the Fireworks AI path kept warm",
     "groq fireworks ai voice primary 2026 04 05 canary warm pool"),
    # --- 46 ---
    ("Reference: NVIDIA's Triton model_repository layout wants config.pbtxt per model with instance_group counting GPU slots; missing dynamic_batching there is why preferred_batch_size silently had no effect last sprint.", "reference", "technical", False,
     [("Triton", "service"), ("model_repository", "config"), ("config.pbtxt", "file"), ("instance_group", "config"), ("dynamic_batching", "pattern")],
     [],
     "which Triton config file controls instance_group and dynamic_batching and what was the silent pitfall",
     "triton model repository config pbtxt instance group dynamic batch"),
    # --- 47 ---
    ("Reference: vLLM's OpenAI-compatible server exposes /v1/chat/completions, /v1/completions, and /v1/embeddings; the legacy /generate remains for old clients but does not support tool-calls.", "reference", "technical", False,
     [("vLLM", "service"), ("/v1/chat/completions", "api"), ("/v1/embeddings", "api"), ("/generate", "api"), ("tool-calls", "pattern")],
     [],
     "which vLLM endpoints does the OpenAI-compatible server expose and what does the legacy one not support",
     "vllm v1 chat completions embeddings generate tool call openai"),
    # --- 48 ---
    ("Reference: TensorRT-LLM's trtllm-build command takes --use_paged_context_fmha for chunked prefill and --gemm_plugin fp8 for H100 FP8 paths; forgetting either silently falls back to a slower kernel.", "reference", "technical", False,
     [("TensorRT-LLM", "library"), ("trtllm-build", "command"), ("--use_paged_context_fmha", "config"), ("--gemm_plugin", "config"), ("H100", "infrastructure")],
     [],
     "which trtllm-build flags turn on paged-context FMHA and FP8 GEMM on H100 and what is the silent penalty",
     "trtllm build paged context fmha gemm plugin fp8 h100 kernel"),
    # --- 49 ---
    ("Reference: llama.cpp's --n-gpu-layers and --ctx-size pair are the knobs to watch on Jetson Orin; pushing ctx above 8192 with all layers on GPU evicts model weights and stalls decode.", "reference", "technical", False,
     [("llama.cpp", "library"), ("--n-gpu-layers", "config"), ("--ctx-size", "config"), ("Jetson Orin", "platform")],
     [],
     "which llama.cpp flags interact badly on Jetson Orin and at which context does decode stall",
     "llama cpp n gpu layers ctx size jetson orin 8192 decode stall"),
    # --- 50. noise ---
    ("A small flock of geese has adopted the building's retention pond and now honks at the shuttle bus every morning between 7:40 and 7:55 without fail.", "fact", "noise", True, [], [], None, None),
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
