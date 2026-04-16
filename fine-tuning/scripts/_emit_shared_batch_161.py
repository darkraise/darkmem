"""One-off emitter for shared-base batch-161 — technical domain (deep-learning training frameworks and compilers: PyTorch, Lightning, Accelerate, DeepSpeed, FSDP, JAX, Flax, XLA, TensorFlow, torch.compile, ZeRO, FlashAttention, AdamW, Lion, SOAP).

Writes 50 rows to data/v2/shared/batch_161.tmp.jsonl with ids shared-08001..08050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_161.tmp.jsonl"
ID_OFFSET = 8000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Ported the training loop from raw PyTorch to PyTorch Lightning; the boilerplate around distributed sampler setup and checkpoint saving dropped by about two hundred lines.", "decision", "technical", False,
     [("PyTorch", "framework"), ("PyTorch Lightning", "framework"), ("distributed sampler", "pattern")],
     [("PyTorch Lightning", "PyTorch", "EXTENDS")],
     "which higher-level trainer did we adopt on top of PyTorch and what boilerplate did it retire",
     "pytorch lightning trainer boilerplate distributed sampler checkpoint"),
    # --- 2 ---
    ("Switched the fine-tuning harness from Hugging Face Trainer to Accelerate; we wanted the explicit gradient-accumulation loop rather than the opinionated Trainer callbacks that hid the step order.", "decision", "technical", False,
     [("Hugging Face Trainer", "framework"), ("Accelerate", "library"), ("gradient-accumulation", "pattern")],
     [("Accelerate", "Hugging Face Trainer", "REPLACES")],
     "why did we drop Hugging Face Trainer for Accelerate on the fine-tune harness",
     "accelerate trainer hugging face gradient accumulation step order"),
    # --- 3 ---
    ("DeepSpeed ZeRO stage 3 shards optimizer states, gradients, and parameters; the 13B fine-tune that previously OOMed on 8xA100 now fits with headroom for a sequence length bump.", "milestone", "technical", False,
     [("DeepSpeed", "library"), ("ZeRO stage 3", "pattern"), ("A100", "platform")],
     [("DeepSpeed", "ZeRO stage 3", "IMPLEMENTS")],
     "which ZeRO stage let the 13B fine-tune fit on 8xA100 and what does it shard",
     "deepspeed zero stage 3 shard optimizer gradient parameter a100"),
    # --- 4 ---
    ("FSDP replaced DeepSpeed in the codebase because the team wanted native PyTorch sharding; wrap policy is auto_wrap over transformer blocks and mixed precision runs in bfloat16.", "architecture", "technical", False,
     [("FSDP", "framework"), ("DeepSpeed", "library"), ("auto_wrap", "pattern"), ("bfloat16", "concept")],
     [("FSDP", "DeepSpeed", "REPLACES")],
     "which sharding strategy replaced DeepSpeed and how are transformer blocks wrapped",
     "fsdp deepspeed auto wrap transformer bfloat16 sharding native"),
    # --- 5 ---
    ("Megatron-LM handles the tensor-parallel split for the 70B pretrain; sequence parallelism on top cut activation memory by roughly a third during the long-context phase.", "architecture", "technical", False,
     [("Megatron-LM", "framework"), ("tensor-parallel", "pattern"), ("sequence parallelism", "pattern")],
     [("Megatron-LM", "sequence parallelism", "IMPLEMENTS")],
     "how is tensor parallelism layered with sequence parallelism in the 70B pretrain",
     "megatron tensor parallel sequence parallelism activation memory 70b"),
    # --- 6 ---
    ("FlashAttention v3 replaced the FlashAttention v2 kernel for H100 training; the new warp-specialised schedule lifted sustained TFLOPs from about 540 to 740 on the attention hot path.", "milestone", "technical", False,
     [("FlashAttention v3", "algorithm"), ("FlashAttention v2", "algorithm"), ("H100", "platform")],
     [("FlashAttention v3", "FlashAttention v2", "REPLACES")],
     "which FlashAttention upgrade lifted H100 attention TFLOPs and what schedule enabled it",
     "flash attention v3 v2 h100 warp specialised tflops attention"),
    # --- 7 ---
    ("torch.compile with the Inductor backend gave a 1.8x speedup on the forward pass of our encoder; TorchDynamo traces the graph once and caches the compiled kernels keyed on input shapes.", "fact", "technical", False,
     [("torch.compile", "tool"), ("Inductor", "tool"), ("TorchDynamo", "tool")],
     [("torch.compile", "Inductor", "USES"), ("torch.compile", "TorchDynamo", "USES")],
     "what speedup did torch.compile give on the encoder and which components handled graph capture",
     "torch compile inductor dynamo encoder forward speedup graph trace"),
    # --- 8 ---
    ("AdamW is the default optimiser in the training config; we tested Lion at the same learning rate and the loss curve stalled, so we reverted after a two-run A/B.", "decision", "technical", False,
     [("AdamW", "algorithm"), ("Lion", "algorithm")],
     [("AdamW", "Lion", "PREFERS")],
     "why did the team stick with AdamW after trying Lion on the same learning rate",
     "adamw lion optimiser learning rate loss stall ab test revert"),
    # --- 9 ---
    ("SOAP is on the shortlist to replace AdamW for the next pretrain; the Shampoo-family preconditioner showed better wall-clock convergence than AdamW on the 1B ablation runs.", "preference", "technical", False,
     [("SOAP", "algorithm"), ("AdamW", "algorithm"), ("Shampoo", "algorithm")],
     [("SOAP", "Shampoo", "IS_A")],
     "which Shampoo-family optimiser is queued to replace AdamW and why",
     "soap shampoo adamw preconditioner pretrain 1b ablation convergence"),
    # --- 10. noise ---
    ("The office espresso machine started coughing up cold foam and the repair technician is scheduled for next Tuesday.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("JAX with Flax drives the TPU side of the research stack; Haiku remains in the legacy vision repo but all new work goes straight to Flax nn.Module.", "architecture", "technical", False,
     [("JAX", "framework"), ("Flax", "library"), ("Haiku", "library"), ("TPU", "platform")],
     [("Flax", "Haiku", "REPLACES")],
     "which JAX neural-net library is preferred for new work and which legacy library does it displace",
     "jax flax haiku tpu research nn module legacy vision repo"),
    # --- 12 ---
    ("XLA compiles the JAX graph ahead of time and fuses elementwise ops; the pmap-over-devices pattern scales almost linearly to 256 TPU cores with no extra user code.", "fact", "technical", False,
     [("XLA", "tool"), ("JAX", "framework"), ("pmap", "api"), ("TPU", "platform")],
     [("JAX", "XLA", "USES")],
     "how does JAX scale to 256 TPU cores and which compiler and primitive enable it",
     "xla jax pmap tpu compile fuse elementwise device scale linear"),
    # --- 13 ---
    ("TensorFlow and Keras are only used for the mobile export path; training runs land in PyTorch and we convert checkpoints through ONNX before the tflite conversion step.", "architecture", "technical", False,
     [("TensorFlow", "framework"), ("Keras", "framework"), ("PyTorch", "framework"), ("ONNX", "protocol"), ("tflite", "tool")],
     [("PyTorch", "ONNX", "PRODUCES"), ("ONNX", "TensorFlow", "APPLIES_TO")],
     "which mobile export path bridges PyTorch training to TensorFlow deployment",
     "tensorflow keras pytorch onnx tflite mobile export checkpoint convert"),
    # --- 14 ---
    ("Equinox is the pick for the small research branch that needs filtered pytree transforms; Flax was too heavy for the tiny dynamics experiments and imported a lot of machinery we never used.", "preference", "technical", False,
     [("Equinox", "library"), ("Flax", "library"), ("pytree", "concept")],
     [("Equinox", "Flax", "PREFERS")],
     "which JAX library did the small research branch prefer over Flax and why",
     "equinox flax pytree filter transform small research branch"),
    # --- 15 ---
    ("TinyGrad gets evaluated quarterly as a lean alternative to PyTorch for the embedded lane; the kernel count stays impressively small but the autograd edge cases still cost us time to debug.", "fact", "technical", False,
     [("TinyGrad", "framework"), ("PyTorch", "framework"), ("autograd", "concept")],
     [],
     "which lean PyTorch alternative do we evaluate quarterly for embedded and what keeps biting us",
     "tinygrad pytorch embedded autograd kernel count evaluate quarter"),
    # --- 16 ---
    ("MLX is the training backend on the Apple Silicon workstations; unified memory removed the host-to-device copy cost and a 7B LoRA finishes overnight on a single M3 Max.", "milestone", "technical", False,
     [("MLX", "framework"), ("Apple Silicon", "platform"), ("M3 Max", "platform"), ("LoRA", "method")],
     [("MLX", "Apple Silicon", "DEPLOYED_ON")],
     "which backend handles Apple Silicon training and what hardware trait removed copy overhead",
     "mlx apple silicon m3 max lora unified memory 7b overnight"),
    # --- 17 ---
    ("Mixed-precision training uses bfloat16 weights with an fp32 master copy for the optimiser state; autocast at the module level keeps the casts out of user code.", "architecture", "technical", False,
     [("bfloat16", "concept"), ("fp32", "concept"), ("autocast", "api"), ("optimiser", "concept")],
     [],
     "how is mixed precision structured to keep optimiser state stable while weights are bfloat16",
     "mixed precision bfloat16 fp32 master optimiser autocast module"),
    # --- 18 ---
    ("Gradient accumulation of 16 micro-steps emulates the effective batch size the 8-GPU rig cannot fit in memory; the AdamW step runs every 16th backward.", "fact", "technical", False,
     [("Gradient accumulation", "pattern"), ("AdamW", "algorithm")],
     [],
     "how does gradient accumulation emulate a batch size that will not fit on 8 GPUs",
     "gradient accumulation micro step batch adamw 8 gpu backward"),
    # --- 19 ---
    ("Gradient checkpointing on the transformer blocks trades roughly 30% more compute for a 40% drop in activation memory; the long-context finetune would not close without it.", "decision", "technical", False,
     [("Gradient checkpointing", "pattern"), ("transformer blocks", "concept"), ("long-context", "concept")],
     [],
     "which memory trade did gradient checkpointing unlock and why was the long-context run unreachable otherwise",
     "gradient checkpoint activation memory transformer long context tradeoff"),
    # --- 20 ---
    ("ZeRO stage 2 was the sweet spot for the 7B run: optimizer-state and gradient sharding without the parameter-sharding overhead of ZeRO stage 3 on our slower interconnect.", "decision", "technical", False,
     [("ZeRO stage 2", "pattern"), ("ZeRO stage 3", "pattern"), ("7B", "concept")],
     [("ZeRO stage 2", "ZeRO stage 3", "PREFERS")],
     "why did the 7B run settle on ZeRO stage 2 instead of stage 3",
     "zero stage 2 3 optimizer gradient shard 7b interconnect slow"),
    # --- 21 ---
    ("Pipeline parallelism chunks the 34B model across 4 stages with 8 micro-batches in flight; bubble time dropped from 18% to about 6% after we doubled the micro-batch count.", "problem", "technical", False,
     [("Pipeline parallelism", "pattern"), ("34B", "concept"), ("micro-batch", "concept")],
     [],
     "how did pipeline parallelism bubble time drop on the 34B run",
     "pipeline parallel 34b micro batch bubble stage chunk inflight"),
    # --- 22 ---
    ("Data parallelism with ring allreduce is the fallback when the job fits on one node; NCCL picks the ring topology automatically and bandwidth saturates around the 256MB bucket size.", "fact", "technical", False,
     [("Data parallelism", "pattern"), ("ring allreduce", "algorithm"), ("NCCL", "library")],
     [("NCCL", "ring allreduce", "IMPLEMENTS")],
     "which collective pattern does NCCL pick for single-node data parallelism and where does bandwidth saturate",
     "data parallel ring allreduce nccl bucket bandwidth saturate topology"),
    # --- 23 ---
    ("Cosine learning-rate schedule with 2000 warmup steps gave the cleanest eval curve; the linear warmup then cosine decay profile is hard-coded in the trainer config.", "decision", "technical", False,
     [("cosine", "algorithm"), ("warmup", "pattern"), ("eval curve", "concept")],
     [],
     "which learning-rate schedule shape won on the eval curve and how long is the warmup",
     "cosine warmup 2000 schedule learning rate linear decay eval curve"),
    # --- 24 ---
    ("Lion showed a 15% wall-clock speedup over AdamW on the vision encoder, but generalisation on the held-out split lagged by two points; the team parked it pending more ablations.", "decision", "technical", False,
     [("Lion", "algorithm"), ("AdamW", "algorithm"), ("vision encoder", "concept")],
     [],
     "why did Lion not displace AdamW for the vision encoder despite the wall-clock win",
     "lion adamw vision encoder wall clock speedup generalisation split"),
    # --- 25 ---
    ("PyTorch Ignite drives the older recommender training loop; the Engine/Handler pattern is what the team knows and the metric logging is wired into MLflow through a single handler.", "architecture", "technical", False,
     [("PyTorch Ignite", "framework"), ("Engine", "pattern"), ("Handler", "pattern"), ("MLflow", "service")],
     [("PyTorch Ignite", "MLflow", "COMMUNICATES_WITH")],
     "which trainer runs the older recommender loop and how does it hook into MLflow",
     "ignite engine handler mlflow recommender legacy metric wire"),
    # --- 26 ---
    ("Hugging Face Transformers is the model zoo of record; we load checkpoints via AutoModel and wrap them in our own trainer rather than using the built-in Trainer for new work.", "architecture", "technical", False,
     [("Hugging Face Transformers", "library"), ("AutoModel", "api"), ("Trainer", "framework")],
     [],
     "how do we use Hugging Face Transformers without adopting its built-in Trainer",
     "huggingface transformers automodel trainer zoo checkpoint load wrap"),
    # --- 27 ---
    ("Accelerate config lives in a single YAML and the launcher reads it on every rank; we pinned the DeepSpeed plugin version because a minor bump silently changed the grad-accum semantics.", "decision", "technical", False,
     [("Accelerate", "library"), ("DeepSpeed plugin", "library"), ("YAML", "config")],
     [],
     "why did we pin the DeepSpeed plugin version in the Accelerate config",
     "accelerate deepspeed plugin yaml pin version grad accum semantic"),
    # --- 28 ---
    ("ONNX export is validated with onnxruntime shape inference before the tflite pass; a stray dynamic axis once slipped through and broke the mobile runtime two hours before a release.", "problem", "technical", False,
     [("ONNX", "protocol"), ("onnxruntime", "tool"), ("tflite", "tool"), ("dynamic axis", "concept")],
     [("onnxruntime", "ONNX", "APPLIES_TO")],
     "which validation step did we add to ONNX export after a dynamic axis broke a release",
     "onnx runtime shape infer tflite dynamic axis mobile release break"),
    # --- 29 ---
    ("TorchDynamo falls back to eager on unsupported ops and logs the graph break; we treat any graph break in the core transformer path as a review-blocking regression.", "decision", "technical", False,
     [("TorchDynamo", "tool"), ("graph break", "concept"), ("transformer", "concept")],
     [],
     "how does the team treat TorchDynamo graph breaks inside the transformer path",
     "torchdynamo graph break transformer eager fallback regression review"),
    # --- 30 ---
    ("Inductor now emits Triton kernels for most fused ops on the A100; we dropped the hand-written CUDA kernel for layer-norm once the Triton version matched its throughput within 3%.", "milestone", "technical", False,
     [("Inductor", "tool"), ("Triton", "library"), ("layer-norm", "algorithm"), ("CUDA", "platform")],
     [("Inductor", "Triton", "PRODUCES")],
     "which hand-written CUDA kernel got retired once Inductor Triton matched it",
     "inductor triton layer norm cuda a100 fused kernel retire hand"),
    # --- 31 ---
    ("Sequence parallelism on the Megatron-LM run splits the layernorm and dropout activations across ranks; activation memory fell enough that we bumped the context window from 4k to 8k tokens.", "milestone", "technical", False,
     [("Sequence parallelism", "pattern"), ("Megatron-LM", "framework"), ("layernorm", "algorithm"), ("dropout", "algorithm")],
     [],
     "which Megatron feature cut activation memory enough to double the context window",
     "sequence parallel megatron layernorm dropout activation 4k 8k context"),
    # --- 32 ---
    ("Pipeline parallelism and tensor parallelism compose with ZeRO stage 1 in the 3D-parallel recipe from Megatron-LM; FSDP was ruled out for this config because it does not compose cleanly with the tensor splits.", "decision", "technical", False,
     [("Pipeline parallelism", "pattern"), ("tensor parallelism", "pattern"), ("ZeRO stage 1", "pattern"), ("FSDP", "framework"), ("Megatron-LM", "framework")],
     [("FSDP", "Megatron-LM", "CONTRADICTS")],
     "why was FSDP excluded from the 3D-parallel recipe with Megatron",
     "pipeline tensor parallel zero stage 1 fsdp megatron 3d recipe"),
    # --- 33 ---
    ("The pretrain milestone hit when the 13B model finished a 1T-token pass over the curated corpus; DeepSpeed with ZeRO-Infinity offloaded optimiser states to NVMe during the final epoch.", "milestone", "technical", False,
     [("DeepSpeed", "library"), ("ZeRO-Infinity", "pattern"), ("NVMe", "infrastructure"), ("13B", "concept")],
     [("DeepSpeed", "ZeRO-Infinity", "IMPLEMENTS")],
     "which DeepSpeed feature let us offload optimiser states during the 13B pretrain",
     "deepspeed zero infinity nvme 13b 1t token pretrain offload optimiser"),
    # --- 34 ---
    ("Keras 3 now runs on JAX or PyTorch backends, not only TensorFlow; we still kept Keras off the training path because the team standardised on plain PyTorch modules.", "fact", "technical", False,
     [("Keras 3", "framework"), ("JAX", "framework"), ("PyTorch", "framework"), ("TensorFlow", "framework")],
     [],
     "why did we keep Keras 3 off the training path despite the multi-backend support",
     "keras 3 jax pytorch tensorflow backend train path standard"),
    # --- 35 ---
    ("Reference: the FlashAttention v2 paper reports a 2x speedup over the v1 kernel by reordering the online softmax and removing the unnecessary mask read.", "reference", "technical", False,
     [("FlashAttention v2", "algorithm"), ("online softmax", "algorithm")],
     [("FlashAttention v2", "online softmax", "USES")],
     "what did the FlashAttention v2 paper change to reach a 2x speedup over v1",
     "flash attention v2 v1 paper online softmax mask reorder speedup"),
    # --- 36 ---
    ("Reference: the Lion optimiser paper from Google Brain uses only sign of momentum for the update; memory per parameter is half of AdamW because the second moment is gone.", "reference", "technical", False,
     [("Lion", "algorithm"), ("AdamW", "algorithm"), ("Google Brain", "organization")],
     [("Lion", "Google Brain", "AUTHORED_BY")],
     "what update rule does the Lion paper use and how does its memory per parameter compare to AdamW",
     "lion optimiser paper google brain sign momentum memory second"),
    # --- 37 ---
    ("Reference: the SOAP paper frames Shampoo as a preconditioner over AdamW eigenbases; wall-clock wins appear once the preconditioner update is sharded across ranks.", "reference", "technical", False,
     [("SOAP", "algorithm"), ("Shampoo", "algorithm"), ("AdamW", "algorithm")],
     [("SOAP", "AdamW", "BUILDS_ON")],
     "how does the SOAP paper combine Shampoo and AdamW to win on wall-clock",
     "soap paper shampoo adamw preconditioner eigenbasis shard rank"),
    # --- 38 ---
    ("Reference: the ZeRO paper from DeepSpeed decomposes data-parallel memory into optimiser, gradient, and parameter partitions; each stage shards one more of them across ranks.", "reference", "technical", False,
     [("ZeRO", "pattern"), ("DeepSpeed", "library"), ("data-parallel", "pattern")],
     [("ZeRO", "DeepSpeed", "AUTHORED_BY")],
     "what does the ZeRO paper decompose into shardable partitions across stages",
     "zero paper deepspeed optimiser gradient parameter partition stage"),
    # --- 39 ---
    ("Reference: the Megatron-LM paper introduces column and row tensor parallel for attention and MLP; the split reduces the all-reduce volume compared to the naive approach.", "reference", "technical", False,
     [("Megatron-LM", "framework"), ("tensor parallel", "pattern"), ("attention", "concept"), ("MLP", "concept")],
     [],
     "which column and row parallel split does the Megatron-LM paper introduce",
     "megatron paper column row tensor parallel attention mlp allreduce"),
    # --- 40 ---
    ("Reference: the PyTorch 2.0 release blog pitches torch.compile as the headline feature; the Dynamo frontend traces the Python bytecode and hands the graph to a backend of your choice.", "reference", "technical", False,
     [("PyTorch 2.0", "framework"), ("torch.compile", "tool"), ("Dynamo", "tool")],
     [("torch.compile", "Dynamo", "USES")],
     "what does the PyTorch 2.0 blog pitch as the headline and how does Dynamo capture the graph",
     "pytorch 2.0 blog torch compile dynamo bytecode trace backend"),
    # --- 41 ---
    ("We prefer explicit gradient accumulation over the Trainer's accumulation_steps flag because the explicit form survives debugger breakpoints without the Trainer skipping the stop.", "preference", "technical", False,
     [("gradient accumulation", "pattern"), ("Trainer", "framework"), ("accumulation_steps", "config")],
     [],
     "why do we prefer explicit gradient accumulation over the Trainer flag during debugging",
     "explicit gradient accumulation trainer accumulation steps debugger"),
    # --- 42 ---
    ("The team decided to standardise all new training on bfloat16 rather than fp16 after a loss-scaler blow-up on the mixture-of-experts run; bfloat16 wide exponent eliminated the issue entirely.", "decision", "technical", False,
     [("bfloat16", "concept"), ("fp16", "concept"), ("loss-scaler", "pattern"), ("mixture-of-experts", "concept")],
     [("bfloat16", "fp16", "REPLACES")],
     "why did new runs standardise on bfloat16 instead of fp16 after the MoE incident",
     "bfloat16 fp16 loss scaler mixture experts exponent standardise"),
    # --- 43. noise ---
    ("A small cactus on the GPU shelf finally sprouted a flower this morning and three engineers took photos.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("FSDP mixed-precision buffers leaked into the optimiser master weights on a 0.1 minor upgrade; pinning the PyTorch nightly to the previous week's build unblocked the training run overnight.", "problem", "technical", False,
     [("FSDP", "framework"), ("PyTorch nightly", "tool"), ("mixed-precision", "pattern"), ("optimiser master weights", "concept")],
     [],
     "which FSDP regression forced a PyTorch nightly rollback and what state was corrupted",
     "fsdp mixed precision optimiser master weight nightly pin rollback"),
    # --- 45 ---
    ("Checkpoint sharding with DeepSpeed produces one file per rank; we wrote a consolidator that merges shards into a single Hugging Face safetensors file for downstream eval.", "architecture", "technical", False,
     [("DeepSpeed", "library"), ("safetensors", "protocol"), ("Hugging Face", "organization")],
     [("DeepSpeed", "safetensors", "PRODUCES")],
     "how are DeepSpeed shard checkpoints merged for Hugging Face eval downstream",
     "deepspeed shard checkpoint consolidate safetensors huggingface eval"),
    # --- 46 ---
    ("Our rule of thumb: if the model fits in one node, stick to FSDP; cross-node jobs go to Megatron-LM 3D parallel with DeepSpeed ZeRO stage 1 on top.", "preference", "technical", False,
     [("FSDP", "framework"), ("Megatron-LM", "framework"), ("DeepSpeed", "library"), ("ZeRO stage 1", "pattern")],
     [],
     "which framework split does the team use for single-node versus cross-node training",
     "fsdp megatron deepspeed zero stage 1 single node cross rule thumb"),
    # --- 47 ---
    ("JAX pjit lays out the 34B pretrain across a 4x8 TPU mesh; sharding specs live in a single module and the rest of the code is mesh-agnostic.", "architecture", "technical", False,
     [("JAX", "framework"), ("pjit", "api"), ("TPU", "platform"), ("sharding specs", "concept")],
     [("JAX", "pjit", "USES")],
     "how does JAX pjit lay the 34B pretrain across the TPU mesh with mesh-agnostic code",
     "jax pjit tpu 4x8 mesh sharding spec 34b pretrain module"),
    # --- 48 ---
    ("The 8k-context fine-tune finished on the first attempt after enabling FlashAttention v2 and gradient checkpointing together; neither alone closed within the wall-clock budget.", "milestone", "technical", False,
     [("FlashAttention v2", "algorithm"), ("gradient checkpointing", "pattern"), ("8k-context", "concept")],
     [],
     "which two optimisations together closed the 8k-context fine-tune in one attempt",
     "flash attention v2 gradient checkpointing 8k context finetune budget"),
    # --- 49 ---
    ("Mixed precision on TPU uses bfloat16 natively; no loss scaler is needed and XLA fuses the cast into the surrounding matmul, so the switch was a one-line config change.", "fact", "technical", False,
     [("bfloat16", "concept"), ("TPU", "platform"), ("XLA", "tool"), ("loss scaler", "pattern")],
     [("XLA", "bfloat16", "SUPPORTS")],
     "why is TPU mixed precision a one-line config change and which compiler fuses the cast",
     "bfloat16 tpu xla loss scaler matmul fuse mixed precision config"),
    # --- 50 ---
    ("We adopted AdamW with decoupled weight decay as the production default; the older Adam + L2 coupling was blamed for regularisation drift on the long multilingual run.", "decision", "technical", False,
     [("AdamW", "algorithm"), ("Adam", "algorithm"), ("weight decay", "concept"), ("L2", "concept")],
     [("AdamW", "Adam", "REPLACES")],
     "which optimiser change fixed the regularisation drift on the multilingual run",
     "adamw adam decoupled weight decay l2 multilingual drift regularisation"),
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
