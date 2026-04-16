"""One-off emitter for shared-base batch-163 — technical domain (model quantization and distillation: INT8/INT4/FP8/FP4, AWQ, GPTQ, SmoothQuant, GGUF, distillation, pruning, LoRA).

Writes 50 rows to data/v2/shared/batch_163.tmp.jsonl with ids shared-08101..08150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_163.tmp.jsonl"
ID_OFFSET = 8100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Swapped the fp16 Llama-3 70B weights for an AWQ INT4 build; activation-aware scaling kept perplexity within half a point while the checkpoint footprint fell from 140 GB to 38 GB on disk.", "decision", "technical", False,
     [("AWQ", "algorithm"), ("Llama-3 70B", "technology"), ("INT4", "concept"), ("fp16", "concept")],
     [("AWQ", "fp16", "REPLACES")],
     "which INT4 quantisation scheme replaced the fp16 Llama-3 70B weights and what footprint win did it deliver",
     "awq int4 llama 70b fp16 weight replace perplexity footprint"),
    # --- 2 architecture ---
    ("GPTQ calibration runs a one-shot second-order error minimisation per layer, so the INT4 weights absorb rounding error column by column instead of all at once like naive round-to-nearest does.", "architecture", "technical", False,
     [("GPTQ", "algorithm"), ("INT4", "concept"), ("round-to-nearest", "algorithm")],
     [("GPTQ", "round-to-nearest", "IMPROVES_ON")],
     "how does GPTQ distribute rounding error across layer columns compared to naive nearest rounding",
     "gptq calibration second order layer column round nearest error"),
    # --- 3 fact ---
    ("SmoothQuant migrates the activation outlier magnitude into the weight tensor via a per-channel scaling factor, so downstream INT8 kernels see a bounded activation range that quantises cleanly.", "fact", "technical", False,
     [("SmoothQuant", "algorithm"), ("INT8", "concept"), ("per-channel", "method"), ("activation outlier", "concept")],
     [("SmoothQuant", "activation outlier", "FIXES")],
     "how does SmoothQuant rebalance activation outliers to make INT8 activations quantise cleanly",
     "smooth quant activation outlier per channel scale int8 weight migrate"),
    # --- 4 decision ---
    ("Picked bitsandbytes 4-bit NF4 over the older LLM.int8 path for inference on the 24 GB card; NF4 held MMLU within a point while LLM.int8's mixed-precision outlier handling was too slow at batch size one.", "decision", "technical", False,
     [("bitsandbytes", "library"), ("NF4", "concept"), ("LLM.int8", "algorithm"), ("MMLU", "concept")],
     [("NF4", "LLM.int8", "REPLACES")],
     "which 4-bit bitsandbytes format replaced LLM.int8 for single-batch inference on a 24 GB card",
     "bitsandbytes nf4 llm int8 mmlu 24gb inference batch one quant"),
    # --- 5 architecture ---
    ("The serving stack keeps weights in GGUF Q4_K_M while runtime activations stay fp16; llama.cpp dequantises block-wise on the fly, so memory bandwidth is the bottleneck rather than compute.", "architecture", "technical", False,
     [("GGUF", "technology"), ("Q4_K_M", "config"), ("llama.cpp", "tool"), ("fp16", "concept")],
     [("llama.cpp", "GGUF", "USES")],
     "which GGUF quant format does llama.cpp dequantise block-wise at runtime and what does that bottleneck on",
     "gguf q4 k m llama cpp dequant block fp16 memory bandwidth"),
    # --- 6 reference ---
    ("The IQ3_M GGUF variant uses importance-matrix-guided 3-bit quantisation with a few 4-bit outlier blocks; the importance matrix comes from a calibration corpus run before the quant pass.", "reference", "technical", False,
     [("IQ3_M", "config"), ("GGUF", "technology"), ("importance matrix", "method"), ("calibration corpus", "concept")],
     [],
     "which GGUF 3-bit variant leans on an importance matrix and where does that matrix come from",
     "iq3 m gguf importance matrix 3 bit calibration corpus outlier"),
    # --- 7 milestone ---
    ("Finished the FP8 E4M3 migration on the H100 inference tier: KV cache, attention output, and MLP all run in fp8 with per-tensor scales, and quality ablations stayed inside the noise floor.", "milestone", "technical", False,
     [("FP8", "concept"), ("E4M3", "config"), ("H100", "infrastructure"), ("KV cache", "pattern")],
     [],
     "which FP8 format migration shipped on the H100 inference tier and what stayed inside the noise floor",
     "fp8 e4m3 h100 kv cache mlp attention per tensor scale quality"),
    # --- 8 problem ---
    ("Running per-tensor INT8 quantisation tanked the GPT-2 XL perplexity by six points because attention projections had channels with ten-times larger magnitudes than neighbours; switching to per-channel recovered it.", "problem", "technical", False,
     [("per-tensor", "method"), ("per-channel", "method"), ("INT8", "concept"), ("GPT-2 XL", "technology")],
     [("per-channel", "per-tensor", "REPLACES")],
     "which granularity swap rescued GPT-2 XL perplexity from a six-point INT8 regression on attention projections",
     "per tensor per channel int8 gpt 2 xl perplexity attention projection"),
    # --- 9 decision ---
    ("Deployed DistilBERT as the production classifier instead of the bert-base teacher; the student retains about 97 percent of the teacher's GLUE score at 40 percent fewer parameters and 60 percent faster inference.", "decision", "technical", False,
     [("DistilBERT", "technology"), ("bert-base", "technology"), ("GLUE", "concept")],
     [("DistilBERT", "bert-base", "REPLACES")],
     "which distilled student replaced the bert-base teacher in production and what trade-off did it ship on GLUE",
     "distilbert bert base glue student teacher parameter speed production"),
    # --- 10 noise ---
    ("Someone refilled the office espresso hopper with decaf again and the morning standup got unusually mellow.", "fact", "noise", True, [], [], None, None),
    # --- 11 architecture ---
    ("The knowledge distillation pipeline uses a soft-target cross-entropy with temperature 4 on teacher logits plus a hard-label cross-entropy at weight 0.5; the combined loss trains the student for ten epochs on the distillation corpus.", "architecture", "technical", False,
     [("knowledge distillation", "method"), ("soft-target", "concept"), ("cross-entropy", "algorithm"), ("temperature", "config")],
     [],
     "how is the distillation loss composed between soft-target teacher logits and hard labels in the pipeline",
     "knowledge distillation soft target temperature logit cross entropy epoch"),
    # --- 12 fact ---
    ("TinyBERT pushes distillation into intermediate attention and hidden states on top of the output logits; the two-stage general-then-task distillation is what unlocks the 7.5x inference speedup over bert-base.", "fact", "technical", False,
     [("TinyBERT", "technology"), ("bert-base", "technology"), ("attention", "pattern"), ("hidden states", "pattern")],
     [("TinyBERT", "bert-base", "IMPROVES_ON")],
     "which layers does TinyBERT distil beyond output logits to get a 7.5x speedup over bert-base",
     "tinybert bert base attention hidden state distil stage speedup"),
    # --- 13 decision ---
    ("Chose MiniLM-L6 over DistilBERT for the sentence-embedding retriever; the deep self-attention distillation of MiniLM preserves the last-layer attention distribution, which matters more for retrieval than masked-LM perplexity.", "decision", "technical", False,
     [("MiniLM-L6", "technology"), ("DistilBERT", "technology"), ("self-attention distillation", "method")],
     [("MiniLM-L6", "DistilBERT", "PREFERS")],
     "which distilled encoder beat DistilBERT for the sentence-embedding retriever and why",
     "minilm distilbert retriever sentence embedding self attention last layer"),
    # --- 14 architecture ---
    ("The weight-only quantisation path at INT4 leaves activations in fp16 and dequantises weights at matmul time; this keeps kernel precision high for attention softmax while still cutting weight memory by nearly four.", "architecture", "technical", False,
     [("weight-only quantisation", "method"), ("INT4", "concept"), ("fp16", "concept"), ("attention softmax", "pattern")],
     [],
     "how does weight-only INT4 quantisation balance memory savings against kernel precision for attention softmax",
     "weight only int4 fp16 dequant matmul attention softmax memory"),
    # --- 15 decision ---
    ("Switched the calibration corpus from Wikitext-2 to a domain-matched chat transcripts sample of 512 sequences; the AWQ activation scales moved enough that a downstream math eval gained 1.8 points.", "decision", "technical", False,
     [("Wikitext-2", "technology"), ("chat transcripts", "concept"), ("AWQ", "algorithm"), ("calibration corpus", "concept")],
     [("chat transcripts", "Wikitext-2", "REPLACES")],
     "which calibration corpus swap tuned AWQ activation scales and how much math eval gain did it produce",
     "calibration wikitext chat transcript awq activation scale math eval"),
    # --- 16 milestone ---
    ("Shipped SpQR quantisation on the 13B finance model: sensitive weight columns stay in fp16 while the rest run at 3-bit, and the hybrid sparse-quantised representation fits the whole model on a single 24 GB card.", "milestone", "technical", False,
     [("SpQR", "algorithm"), ("fp16", "concept"), ("13B finance model", "project"), ("24 GB card", "infrastructure")],
     [],
     "which hybrid sparse-quantised method shipped on the 13B finance model and what hardware target did it fit",
     "spqr 13b finance fp16 sensitive column 3 bit hybrid 24gb card"),
    # --- 17 fact ---
    ("OmniQuant learns per-layer clipping thresholds and per-channel smoothing factors jointly with a short gradient-based search; the learnt parameters give lower weight quantisation error than hand-set SmoothQuant defaults.", "fact", "technical", False,
     [("OmniQuant", "algorithm"), ("SmoothQuant", "algorithm"), ("clipping threshold", "config"), ("smoothing factor", "config")],
     [("OmniQuant", "SmoothQuant", "IMPROVES_ON")],
     "which two parameter families does OmniQuant learn jointly to beat SmoothQuant defaults",
     "omni quant clipping threshold smoothing factor learn gradient search"),
    # --- 18 decision ---
    ("Replaced the production GPTQ pipeline with HQQ for 2-bit experiments; HQQ skips the calibration corpus by solving a half-quadratic optimisation per layer, which cut quant time from two hours to three minutes on the 7B run.", "decision", "technical", False,
     [("HQQ", "algorithm"), ("GPTQ", "algorithm"), ("half-quadratic", "method"), ("7B run", "project")],
     [("HQQ", "GPTQ", "REPLACES")],
     "which calibration-free quantiser replaced GPTQ for 2-bit experiments and how much faster did it get",
     "hqq gptq half quadratic calibration free 2 bit 7b time"),
    # --- 19 architecture ---
    ("Running dynamic quantisation picks activation scales at inference time from a running min/max window, while static quantisation freezes scales from a calibration pass; the serving tier standardised on static for CPU BERT.", "architecture", "technical", False,
     [("dynamic quantisation", "method"), ("static quantisation", "method"), ("CPU BERT", "project")],
     [("static quantisation", "CPU BERT", "APPLIES_TO")],
     "how do dynamic and static quantisation differ and which did the CPU BERT serving tier standardise on",
     "dynamic static quantisation activation scale min max calibration cpu bert"),
    # --- 20 problem ---
    ("INT4 GPTQ on Mistral 7B silently regressed the coding eval by four points; tracing it to row-wise rather than group-wise quantisation inside the MLP fixed it once we switched to 128-wise groupsize.", "problem", "technical", False,
     [("GPTQ", "algorithm"), ("Mistral 7B", "technology"), ("groupsize", "config"), ("MLP", "pattern")],
     [("groupsize", "GPTQ", "FIXES")],
     "which GPTQ configuration change rescued Mistral 7B coding-eval performance after an INT4 regression",
     "gptq mistral 7b int4 coding regression groupsize 128 mlp"),
    # --- 21 reference ---
    ("The Q5_K_S GGUF variant mixes 5-bit quantisation for most weight tensors with 6-bit for attention.v and small embedding tables; sizes land about 20 percent below Q6_K at similar perplexity on 13B models.", "reference", "technical", False,
     [("Q5_K_S", "config"), ("Q6_K", "config"), ("GGUF", "technology"), ("attention.v", "pattern")],
     [],
     "which GGUF mixed-bit layout sits between Q6_K and Q4 on 13B models and which tensors get the extra bits",
     "q5 k s gguf q6 k 5 bit 6 bit attention v embedding size"),
    # --- 22 architecture ---
    ("Low-Rank Adaptation injects rank-8 update matrices alongside frozen attention projections; the distilled student fine-tunes through LoRA only, so the 40 MB adapter is the only artifact we ship per tenant.", "architecture", "technical", False,
     [("Low-Rank Adaptation", "method"), ("rank-8", "config"), ("attention projection", "pattern")],
     [],
     "how does Low-Rank Adaptation bolt onto frozen attention projections and what artifact ships per tenant",
     "low rank adaptation lora rank 8 attention projection adapter tenant"),
    # --- 23 decision ---
    ("Qwen-2.5 14B got treated with layer pruning, cut from 48 transformer blocks down to 36 with a short continued-pretrain; the pruned student keeps 94 percent of the benchmark average while latency drops 24 percent on A100.", "decision", "technical", False,
     [("Qwen-2.5 14B", "technology"), ("layer pruning", "method"), ("A100", "infrastructure")],
     [("layer pruning", "Qwen-2.5 14B", "APPLIES_TO")],
     "which layer-pruning recipe cut Qwen-2.5 14B from 48 to 36 blocks and what latency win landed on A100",
     "qwen 14b layer pruning block transformer continued pretrain a100"),
    # --- 24 fact ---
    ("The N:M sparsity family (specifically 2:4) runs on Ampere and Hopper sparse tensor cores at roughly 2x the dense matmul throughput when the weight matrix follows the 2-of-4 non-zero pattern per group of four.", "fact", "technical", False,
     [("N:M sparsity", "method"), ("2:4", "config"), ("Ampere", "infrastructure"), ("Hopper", "infrastructure")],
     [],
     "which sparsity ratio maps onto Ampere and Hopper sparse tensor cores and what throughput multiple does it unlock",
     "n m sparsity 2 4 ampere hopper sparse tensor core throughput"),
    # --- 25 milestone ---
    ("Wrapped the structured pruning campaign on the dialogue model: attention heads and MLP channels ranked by a Taylor-first-order importance score got removed in one pass, and three epochs of recovery training closed the quality gap.", "milestone", "technical", False,
     [("structured pruning", "method"), ("attention head", "pattern"), ("Taylor-first-order", "algorithm"), ("MLP channel", "pattern")],
     [],
     "which importance score guides structured pruning of attention heads and MLP channels and how is quality recovered",
     "structured pruning attention head mlp channel taylor importance retrain"),
    # --- 26 milestone ---
    ("Hit parity between the GPTQ-4bit Llama-3 8B student and its fp16 teacher on the customer intent classifier after three rounds of calibration-corpus curation and a groupsize sweep ending at 64.", "milestone", "technical", False,
     [("GPTQ", "algorithm"), ("Llama-3 8B", "technology"), ("fp16", "concept"), ("groupsize", "config")],
     [],
     "which combination of GPTQ knobs got the Llama-3 8B student to fp16 parity on the customer intent task",
     "gptq llama 3 8b fp16 parity group size 64 calibration intent"),
    # --- 27 preference ---
    ("For production CPU inference I prefer static per-channel INT8 over dynamic per-tensor every time; the calibration overhead is a one-off, and dynamic range-tracking adds per-request jitter that murders tail latency.", "preference", "technical", False,
     [("static per-channel", "method"), ("dynamic per-tensor", "method"), ("INT8", "concept")],
     [("static per-channel", "dynamic per-tensor", "PREFERS")],
     "why does the author prefer static per-channel INT8 over dynamic per-tensor for production CPU serving",
     "static per channel int8 dynamic per tensor cpu production tail latency"),
    # --- 28 decision ---
    ("Retired the fp16 teacher on the retrieval reranker once the 4-bit AWQ student passed the staged eval; the teacher checkpoint lives in cold storage for re-distillation but no longer ships to the inference fleet.", "decision", "technical", False,
     [("AWQ", "algorithm"), ("fp16", "concept"), ("retrieval reranker", "project"), ("inference fleet", "infrastructure")],
     [("AWQ", "fp16", "REPLACES")],
     "which 4-bit AWQ student retired the fp16 teacher on the retrieval reranker and where did the teacher end up",
     "awq 4 bit fp16 teacher reranker cold storage fleet retire"),
    # --- 29 architecture ---
    ("Running self-distillation trains a student with exactly the same architecture as the teacher on the teacher's logits; the resulting network generalises slightly better than the teacher despite identical capacity, which is the Born-Again Networks phenomenon.", "architecture", "technical", False,
     [("self-distillation", "method"), ("Born-Again Networks", "concept"), ("teacher", "concept"), ("student", "concept")],
     [],
     "which self-distillation phenomenon trains a same-architecture student to outperform its teacher",
     "self distillation born again network same architecture teacher student"),
    # --- 30 fact ---
    ("FP4 with E2M1 encoding gives four exponent combinations and one mantissa bit plus sign; it is useful for activations that span many orders of magnitude but is too coarse for weight-only quantisation without a separate scale per group.", "fact", "technical", False,
     [("FP4", "concept"), ("E2M1", "config"), ("activation", "concept"), ("weight-only quantisation", "method")],
     [],
     "what does FP4 E2M1 encode per value and why does it need per-group scales for weight-only use",
     "fp4 e2m1 exponent mantissa activation per group scale weight"),
    # --- 31 decision ---
    ("Picked llama.cpp over vLLM for the laptop demo build; GGUF Q4_K_M weights plus Metal backend let a 7B model run at 30 tokens per second on an M2 Pro without pulling a CUDA dependency chain.", "decision", "technical", False,
     [("llama.cpp", "tool"), ("vLLM", "framework"), ("Q4_K_M", "config"), ("M2 Pro", "infrastructure"), ("Metal", "technology")],
     [("llama.cpp", "vLLM", "PREFERS")],
     "which runtime won the laptop demo and what backend plus quant format made it run at 30 tokens per second",
     "llama cpp vllm gguf q4 k m metal m2 pro laptop demo"),
    # --- 32 problem ---
    ("An activation outlier in the attention output projection caused FP8 E4M3 overflow on long-context inputs; a per-tensor scale recalibrated from 99.99th-percentile magnitudes eliminated the overflows without changing kernel code.", "problem", "technical", False,
     [("activation outlier", "concept"), ("FP8", "concept"), ("E4M3", "config"), ("per-tensor scale", "method")],
     [("per-tensor scale", "activation outlier", "FIXES")],
     "which calibration change silenced FP8 E4M3 overflow on long-context attention output projections",
     "activation outlier fp8 e4m3 overflow long context per tensor percentile"),
    # --- 33 milestone ---
    ("Completed the quantisation-aware training pass on the on-device encoder: fake-quant modules in the last fine-tune phase piped gradients through a straight-through estimator, and the final weights deployed cleanly at INT8.", "milestone", "technical", False,
     [("quantisation-aware training", "method"), ("fake-quant", "pattern"), ("straight-through estimator", "algorithm")],
     [],
     "how do fake-quant modules and the straight-through estimator cooperate during quantisation-aware training",
     "quantisation aware training fake quant straight through estimator gradient"),
    # --- 34 decision ---
    ("Rejected post-training INT4 for the speech encoder after a QAT trial beat it by 2.3 WER points; the training cost is acceptable because the same checkpoint lives in five production regions for two years.", "decision", "technical", False,
     [("INT4", "concept"), ("QAT", "method"), ("WER", "concept"), ("speech encoder", "project")],
     [("QAT", "INT4", "REPLACES")],
     "which quantisation approach won on the speech encoder after a head-to-head WER comparison",
     "qat post training int4 wer speech encoder region production"),
    # --- 35 reference ---
    ("DistilBERT pretrains with a triple loss: masked-LM on the student, KL-divergence on the teacher logits at temperature 2, and a cosine alignment between teacher and student hidden states.", "reference", "technical", False,
     [("DistilBERT", "technology"), ("masked-LM", "method"), ("KL-divergence", "algorithm"), ("cosine alignment", "method")],
     [],
     "which three losses compose the DistilBERT pretraining objective and which temperature applies to KL",
     "distilbert triple loss masked lm kl divergence cosine temperature"),
    # --- 36 preference ---
    ("When calibration data is scarce I reach for HQQ before GPTQ; the half-quadratic solver needs no corpus and the resulting weights typically land within a point of GPTQ at four-bit on general-domain models.", "preference", "technical", False,
     [("HQQ", "algorithm"), ("GPTQ", "algorithm"), ("half-quadratic", "method")],
     [("HQQ", "GPTQ", "PREFERS")],
     "why does the author reach for HQQ over GPTQ when calibration data is scarce",
     "hqq gptq half quadratic calibration data scarce four bit general"),
    # --- 37 fact ---
    ("The scale and zero-point parameters of an asymmetric quantisation scheme at INT8 satisfy x_q = round(x / s) + z with x_q clipped to the signed byte range; symmetric quantisation forces z to zero and accepts a slightly larger clipping error.", "fact", "technical", False,
     [("asymmetric quantisation", "method"), ("symmetric quantisation", "method"), ("INT8", "concept"), ("zero-point", "concept")],
     [],
     "how do asymmetric and symmetric INT8 quantisation differ in the zero-point term and clipping error",
     "asymmetric symmetric int8 scale zero point clipping error signed byte"),
    # --- 38 milestone ---
    ("Landed the first NF4 + double-quantisation QLoRA run on Llama-3 70B with a 48 GB A6000; the paged optimiser kept memory below 44 GB during fine-tune and the adapter merged cleanly back into a new NF4 checkpoint.", "milestone", "technical", False,
     [("NF4", "concept"), ("QLoRA", "method"), ("Llama-3 70B", "technology"), ("A6000", "infrastructure"), ("paged optimiser", "tool")],
     [("QLoRA", "NF4", "USES")],
     "which QLoRA recipe landed on Llama-3 70B with an A6000 and what kept memory under 44 GB",
     "qlora nf4 double quant llama 70b a6000 paged optimiser memory"),
    # --- 39 architecture ---
    ("Using teacher ensembling for distillation averages logits from three different-seed teachers before the softmax-temperature step; the student converges two epochs earlier than on a single-teacher setup and gains half a point on SuperGLUE.", "architecture", "technical", False,
     [("teacher ensembling", "method"), ("SuperGLUE", "concept"), ("softmax-temperature", "algorithm")],
     [],
     "how does teacher ensembling alter distillation dynamics and what SuperGLUE gain did it buy",
     "teacher ensemble distillation logit softmax temperature superglue seed"),
    # --- 40 noise ---
    ("A pigeon has taken up residence on the office AC unit and the maintenance team keeps losing the bet on when it will leave.", "fact", "noise", True, [], [], None, None),
    # --- 41 decision ---
    ("Standardised internal inference on AWQ over GPTQ for Llama-style decoders; AWQ's activation-aware scaling matched or beat GPTQ at 4-bit on all our benchmarks and its runtime kernels ship in vLLM and TensorRT-LLM.", "decision", "technical", False,
     [("AWQ", "algorithm"), ("GPTQ", "algorithm"), ("vLLM", "framework"), ("TensorRT-LLM", "framework")],
     [("AWQ", "GPTQ", "PREFERS")],
     "why did the internal standard tilt toward AWQ over GPTQ for Llama-style decoder inference",
     "awq gptq llama decoder activation aware vllm tensor rt benchmark"),
    # --- 42 reference ---
    ("The bitsandbytes 4-bit NF4 format treats weights as normally distributed and uses a quantile codebook with 16 levels; double quantisation compresses the per-block scales themselves to 8-bit to shave another 0.4 bits per parameter.", "reference", "technical", False,
     [("bitsandbytes", "library"), ("NF4", "concept"), ("double quantisation", "method"), ("quantile codebook", "concept")],
     [],
     "which codebook does bitsandbytes 4-bit NF4 use and what does double quantisation squeeze further",
     "bitsandbytes nf4 quantile codebook double quant scale 4 bit"),
    # --- 43 reference ---
    ("GGUF's K-quant family (Q2_K through Q6_K) groups weights into super-blocks of 256 values with a float16 super-scale and per-block sub-scales; the layout is what lets Q4_K_M keep quality close to fp16 at a quarter of the size.", "reference", "technical", False,
     [("GGUF", "technology"), ("Q2_K", "config"), ("Q6_K", "config"), ("Q4_K_M", "config"), ("super-block", "concept")],
     [],
     "which block structure underpins the GGUF K-quant family from Q2_K through Q6_K",
     "gguf k quant q2 q6 super block sub scale 256 value float16"),
    # --- 44 reference ---
    ("SmoothQuant's alpha knob controls how much of the activation outlier magnitude gets migrated into weights; the default 0.8 works for most decoders but smaller models like Phi-2 often need 0.5 to keep weights inside the symmetric INT8 clip.", "reference", "technical", False,
     [("SmoothQuant", "algorithm"), ("INT8", "concept"), ("Phi-2", "technology"), ("alpha", "config")],
     [("alpha", "SmoothQuant", "CONFIGURES")],
     "which SmoothQuant knob governs outlier migration into weights and how does it shift for smaller decoders",
     "smooth quant int8 phi 2 alpha 0 5 0 8 clip outlier decoder"),
    # --- 45 decision ---
    ("Picked per-channel weight quantisation over per-group for the dense MLP, and per-group (groupsize 128) for the attention projections; the split matched our measured sensitivity profile and kept the quant overhead flat.", "decision", "technical", False,
     [("per-channel", "method"), ("per-group", "method"), ("groupsize", "config"), ("MLP", "pattern")],
     [],
     "which split of per-channel versus per-group quantisation did the model use across MLP and attention projections",
     "per channel per group quant mlp attention projection sensitivity 128"),
    # --- 46 architecture ---
    ("An outlier channel detection pass runs pre-quant: any weight column whose max-abs exceeds 3x the tensor's 99th-percentile lands in a fp16 sidecar, and only the remainder goes through INT4 quantisation.", "architecture", "technical", False,
     [("outlier channel detection", "method"), ("fp16 sidecar", "pattern"), ("INT4", "concept"), ("99th-percentile", "concept")],
     [],
     "how does the pre-quant pass decide which weight columns go to the fp16 sidecar instead of INT4",
     "outlier channel detection fp16 sidecar int4 99 percentile max abs"),
    # --- 47 milestone ---
    ("Closed out the OmniQuant rollout on the 34B coder model; the learnt clipping-and-smoothing parameters shaved another 0.7 points off the HumanEval gap between INT4 and fp16 compared to our previous SmoothQuant baseline.", "milestone", "technical", False,
     [("OmniQuant", "algorithm"), ("SmoothQuant", "algorithm"), ("HumanEval", "concept"), ("34B coder model", "project")],
     [("OmniQuant", "SmoothQuant", "REPLACES")],
     "which quantiser closed the INT4-to-fp16 HumanEval gap on the 34B coder beyond the SmoothQuant baseline",
     "omni quant smooth quant 34b coder human eval int4 fp16 gap"),
    # --- 48 preference ---
    ("When I have to choose between pruning and quantisation under a fixed latency budget I start with quantisation; INT4 weight-only usually clears the target with zero architectural change, while pruning risks a multi-epoch recovery run.", "preference", "technical", False,
     [("pruning", "method"), ("quantisation", "method"), ("INT4", "concept"), ("latency budget", "concept")],
     [("quantisation", "pruning", "PREFERS")],
     "why does the author start with quantisation over pruning under a fixed latency budget",
     "pruning quantisation int4 weight only latency budget architectural change"),
    # --- 49 fact ---
    ("Distillation temperature scaling softens the teacher distribution so minority-class probabilities become informative; too high and the signal looks uniform, too low and the student just learns the argmax hard-label, so 2 to 5 is the usual band.", "fact", "technical", False,
     [("temperature scaling", "method"), ("teacher", "concept"), ("student", "concept"), ("argmax", "algorithm")],
     [],
     "which distillation-temperature band balances softened teacher signal against collapsing to hard argmax labels",
     "temperature scaling teacher student soft argmax minority probability band"),
    # --- 50 preference ---
    ("For adapter merging I prefer saving the LoRA weights separately rather than folding them back into the quantised base; the dequant-merge-requant round-trip introduces drift that breaks the clean evaluation lineage.", "preference", "technical", False,
     [("LoRA", "method"), ("adapter merging", "pattern"), ("quantised base", "concept"), ("dequant-merge-requant", "pattern")],
     [("LoRA", "dequant-merge-requant", "PREFERS")],
     "why does the author keep LoRA adapters separate instead of folding them into the quantised base",
     "lora adapter merge quantised base dequant requant drift evaluation"),
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
