"""One-off emitter for classification top-up batch-022 — contrastive_decision_architecture mode, ML training slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_022.tmp.jsonl with ids class-02101..02200.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_022.tmp.jsonl"
ID_OFFSET = 2100
PAIR_OFFSET = 800

# (decision_text, decision_domain, architecture_text, architecture_domain)
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. distributed training framework — FSDP vs DeepSpeed
    (
        "Switched the SFT pipeline from DeepSpeed ZeRO-3 to PyTorch FSDP after memory fragmentation killed the last two 70B runs past step 4000.",
        "technical",
        "SFT jobs run on 8xH100 nodes with PyTorch FSDP full-shard strategy, bf16 mixed precision, gradient checkpointing on every other transformer block, and Weights & Biases for metric streaming.",
        "technical",
    ),
    # 2. parallelism strategy — tensor parallel adoption
    (
        "Adopted 4-way tensor parallelism on top of data parallel after single-GPU activation memory for the 34B model spilled into host RAM and wrecked throughput.",
        "technical",
        "The 34B pretraining topology uses TP=4 within each 8-GPU node and DP=16 across nodes, with NCCL over a 400 Gb/s InfiniBand fabric and activation recomputation in every MLP block.",
        "technical",
    ),
    # 3. optimiser — Lion over AdamW
    (
        "Picked Lion over AdamW for the 7B continued-pretrain run after an ablation showed comparable loss at 40% less optimiser state memory.",
        "technical",
        "Continued-pretraining uses the Lion optimiser at lr=3e-5 with beta1=0.9, beta2=0.99, weight_decay=0.1, and a distributed ShardedOptimizer wrapper checkpointed every 1000 steps.",
        "technical",
    ),
    # 4. dataset pipeline — WebDataset over HF streaming
    (
        "Moved the pretraining corpus from Hugging Face streaming to WebDataset shards on S3 after DataLoader stalls throttled effective throughput below 45% MFU.",
        "technical",
        "Pretraining data lives as 8 GB WebDataset tar shards on S3, prefetched by a torchdata DataPipe with 16 worker processes per node and a 2 GB on-disk local cache for hot shards.",
        "technical",
    ),
    # 5. tokenizer — SentencePiece rebuild
    (
        "Decided to retrain the SentencePiece tokenizer from scratch on the code-heavy mix after OOV rate on Rust and Solidity files exceeded 11% with the inherited Llama tokenizer.",
        "technical",
        "The tokenizer is a 64k-vocabulary SentencePiece unigram model trained on 120 GB of deduplicated code and prose, with byte fallback enabled and NFC normalisation applied before encoding.",
        "technical",
    ),
    # 6. mixed precision — bf16 lock-in
    (
        "Locked the whole training stack to bf16 after fp16 runs on the reward model diverged twice at step 9000 with loss-scale underflow.",
        "technical",
        "All forward, backward, and optimiser-update passes run in bf16 on H100 tensor cores, with master weights kept in bf16 and no GradScaler since dynamic loss scaling is disabled.",
        "technical",
    ),
    # 7. checkpointing — async to object storage
    (
        "Adopted torch.distributed.checkpoint asynchronous saving after synchronous full-state checkpoints stalled the job for 90 seconds every 2000 steps.",
        "technical",
        "Checkpoints are written every 2000 steps through torch.distributed.checkpoint in async mode to a dedicated S3 bucket with per-rank sharded tensors and a single metadata file resolved by the coordinator rank.",
        "technical",
    ),
    # 8. eval harness — lm-evaluation-harness
    (
        "Standardised on EleutherAI lm-evaluation-harness over an in-house eval script after two engineers reported different MMLU numbers on the same checkpoint.",
        "technical",
        "Offline evals run lm-evaluation-harness v0.4 inside a pinned container on a dedicated 2xA100 box, scoring MMLU, HellaSwag, ARC-Challenge, GSM8K, and TruthfulQA with a fixed seed and loglikelihood requests.",
        "technical",
    ),
    # 9. hyperparameter search — Ray Tune ASHA
    (
        "Picked Ray Tune with ASHA over a grid search after the twelve-point learning-rate sweep ate three weeks of GPU time for no meaningful gain.",
        "technical",
        "Hyperparameter search runs Ray Tune 2.10 with the ASHA scheduler over 64 concurrent trials on a dedicated 4-node A100 cluster, reporting into a shared MLflow tracking server.",
        "technical",
    ),
    # 10. experiment tracking — W&B over TensorBoard
    (
        "Migrated experiment tracking from local TensorBoard event files to Weights & Biases after cross-run comparisons across branches became impossible to share with reviewers.",
        "technical",
        "Every training job streams metrics, system stats, and artefact manifests into Weights & Biases under the darkmem-llm project, with per-branch groups and per-run config hashes for deterministic replay.",
        "technical",
    ),
    # 11. artefact storage — S3 with content-addressed
    (
        "Moved model artefacts from an NFS share to a content-addressed S3 layout after two engineers overwrote each other's checkpoints on the same path.",
        "technical",
        "Final and intermediate checkpoints live under s3://darkmem-artefacts/ keyed by sha256 of the state_dict manifest, with a sqlite index mapping run_id, step, and git_sha to the corresponding S3 prefix.",
        "technical",
    ),
    # 12. reward modelling — preference pair format
    (
        "Chose a Bradley-Terry pairwise reward model over a pointwise scalar regressor after inter-annotator agreement on absolute scores collapsed below 0.4 kappa.",
        "technical",
        "The reward model is a 7B transformer with a scalar head trained on 180k Bradley-Terry preference pairs, using a margin-ranking loss with beta=0.1 and a 10% chosen/rejected swap regulariser.",
        "technical",
    ),
    # 13. RLHF loop — DPO instead of PPO
    (
        "Swapped the PPO rollout loop for DPO after PPO hyperparameter sensitivity caused three consecutive runs to collapse into repetition within 500 steps.",
        "technical",
        "The alignment stage is a single-phase DPO run over 120k preference pairs with beta=0.1, reference model frozen in bf16, and a constant lr=5e-7 schedule over 3 epochs.",
        "technical",
    ),
    # 14. SFT stack — TRL SFTTrainer
    (
        "Adopted the TRL SFTTrainer over a hand-rolled Trainer subclass after the packing and response-only loss masking code kept drifting between the chat and code variants.",
        "technical",
        "SFT runs on TRL 0.9 SFTTrainer with sequence packing enabled at 8192 tokens, DataCollatorForCompletionOnlyLM masking the prompt, and a Hugging Face Accelerate launcher for FSDP configuration.",
        "technical",
    ),
    # 15. LoRA/QLoRA — QLoRA for instruction tune
    (
        "Chose QLoRA with 4-bit NF4 quantisation for the instruction-tune experiments after full fine-tune on the 13B base blew the 80 GB VRAM budget per GPU.",
        "technical",
        "Instruction tuning uses QLoRA with bitsandbytes NF4 quantisation, LoRA adapters of rank 64 and alpha 16 on all linear layers, paged AdamW 8-bit optimiser, and merged weights exported to safetensors at the end.",
        "technical",
    ),
    # 16. DPO — beta sweep
    (
        "Set DPO beta to 0.05 for the safety-tuned variant after higher beta values made the model refuse benign prompts at a 9% false-positive rate on the internal eval set.",
        "technical",
        "The safety DPO run trains the 7B SFT checkpoint for two epochs at beta=0.05 over 60k harmlessness-preference pairs, with ref_model shared across ranks and reported win-rate on a held-out 2k-prompt slice.",
        "technical",
    ),
    # 17. evaluation cadence — per-step slice evals
    (
        "Adopted a fast slice-eval every 250 steps after full MMLU at checkpoint time meant regressions were only caught after an eight-hour run completed.",
        "technical",
        "Training launches a sidecar eval worker that every 250 steps runs a 500-example slice covering MMLU-STEM, GSM8K-100, and an internal refusal probe, reporting deltas back into the W&B run as custom charts.",
        "technical",
    ),
    # 18. early stopping — patience on eval loss
    (
        "Enabled early stopping with patience 5 on eval perplexity after three long runs overfit past step 18k with no validation-loss improvement for 10k steps.",
        "technical",
        "The SFT trainer uses a patience-5 early-stopping callback on held-out eval loss, checkpointing the best state and aborting the remainder of the schedule when patience is exhausted.",
        "technical",
    ),
    # 19. gradient accumulation — micro-batch tuning
    (
        "Raised gradient accumulation from 4 to 16 after reducing micro-batch size to fit the 70B model, targeting a constant global batch size of 1024 sequences.",
        "technical",
        "The 70B SFT run uses a per-device micro batch of 1, gradient accumulation of 16, and 64-way data parallelism for a fixed global batch of 1024 sequences, with all-reduce fused into the backward pass.",
        "technical",
    ),
    # 20. scheduler — cosine with warmup
    (
        "Switched from linear decay to a cosine schedule with a 2% warmup after the earlier run's loss curve showed a sharp plateau at the 40% mark of training.",
        "technical",
        "The learning-rate schedule is a single cosine decay from lr=2e-5 to 2e-6 over 30k steps with a 600-step linear warmup, implemented via transformers.get_cosine_schedule_with_warmup.",
        "technical",
    ),
    # 21. data curation — dedup with MinHashLSH
    (
        "Added a MinHashLSH near-dedup pass over the raw web crawl after a memorisation probe showed 2.3% of training strings appeared verbatim in held-out eval prompts.",
        "technical",
        "The pretraining data pipeline runs a Spark MinHashLSH job with 128 permutations and Jaccard threshold 0.8, emitting a deduplicated Parquet dataset keyed by document hash before tokenisation.",
        "technical",
    ),
    # 22. activation checkpointing — selective recompute
    (
        "Switched from full activation recomputation to selective checkpointing on only attention blocks after profiling showed the MLPs were 30% cheaper to rerun.",
        "technical",
        "Activation checkpointing wraps only the attention submodule in each transformer block via torch.utils.checkpoint, keeping MLP activations resident and reducing step time by 18% on the 34B run.",
        "technical",
    ),
    # 23. FlashAttention — v3 adoption
    (
        "Upgraded to FlashAttention-3 on the H100 fleet after kernel benchmarks showed 1.7x throughput over FA-2 for the 8192-context training workload.",
        "technical",
        "All attention layers use FlashAttention-3 with FP8 accumulation paths disabled, window_size left at defaults, and a fallback to FA-2 on the older A100 pre-training nodes through a runtime dispatch shim.",
        "technical",
    ),
    # 24. context length — curriculum extension
    (
        "Adopted a two-phase context-length curriculum after directly training at 32k from step zero wasted 35% of compute on padding within shorter documents.",
        "technical",
        "Pretraining runs 80% of tokens at 4k context and 20% at 32k with linearly interpolated RoPE theta scaling, using the same tokenised corpus reshuffled into length-bucketed packs per phase.",
        "technical",
    ),
    # 25. RoPE scaling — YaRN over linear
    (
        "Chose YaRN over linear RoPE scaling for the long-context extension after linear scaling degraded needle-in-a-haystack recall below 60% past 16k tokens.",
        "technical",
        "The 32k-context variant applies YaRN scaling with alpha=1, beta=32, and an attention temperature factor of 0.1, fine-tuned for 4B tokens of long-document data on top of the 4k base checkpoint.",
        "technical",
    ),
    # 26. reward hacking mitigation — length normalisation
    (
        "Added response-length normalisation to the reward signal after RLHF-trained outputs drifted to verbose essays that scored higher purely from length bias.",
        "technical",
        "The RLHF reward pipeline subtracts a log-length penalty (alpha=0.02) from the raw reward-model score and clips the result to [-3, 3] before feeding it into the DPO or PPO loss.",
        "technical",
    ),
    # 27. synthetic data — self-instruct mix
    (
        "Added a 15% self-instruct synthetic mix after ablation showed it lifted GSM8K by 4 points without hurting HumanEval performance.",
        "technical",
        "The SFT dataset is a 1.2M-example mix of 70% human-written instructions, 15% self-instruct expansions from a Llama-3-70B teacher, and 15% code-specific synthetic reasoning pairs, deduplicated against all eval prompts.",
        "technical",
    ),
    # 28. code corpus — license filtering
    (
        "Restricted the code pretraining corpus to permissive licenses only after legal review flagged GPL contamination in two downstream customer-facing builds.",
        "technical",
        "The code pretraining corpus is a 420 GB filtered slice of The Stack v2 limited to MIT, Apache-2.0, BSD, and ISC licenses, with file-level license detection via scancode-toolkit and a SHA-256 dedup pass.",
        "technical",
    ),
    # 29. tokeniser — chat template pinning
    (
        "Pinned the chat template in tokenizer_config.json after downstream serving drifted from the training-time format and caused a 6-point regression on IFEval.",
        "technical",
        "The released tokenizer ships with a fixed Jinja chat_template rendering <|im_start|>role\\ncontent<|im_end|> markers, matching the SFT training wrapper exactly and covered by a unit test on every release.",
        "technical",
    ),
    # 30. PPO — KL control
    (
        "Replaced fixed KL coefficient with an adaptive KL controller after PPO runs either collapsed to degenerate outputs or failed to move off the reference policy.",
        "technical",
        "The PPO loop uses an adaptive KL controller targeting KL=6 nats per token, updating the coefficient every rollout batch of 512 prompts with a step size of 0.1 and clipped advantage normalisation.",
        "technical",
    ),
    # 31. vllm — inference-time rollout
    (
        "Adopted vLLM for PPO rollouts after the HuggingFace generate loop capped rollout throughput at 40 tokens per second per GPU.",
        "technical",
        "PPO rollouts run through a dedicated vLLM 0.5 server pool of 4xH100 with tensor parallelism 2, serving the current policy via a continuous-batching API that the trainer hits with sampling_params per prompt.",
        "technical",
    ),
    # 32. safety red-team — adversarial eval
    (
        "Added an AdvBench and JailbreakBench regression on every candidate release after an unrelated SFT change silently regressed refusal rate on harmful requests by 12 points.",
        "technical",
        "The release pipeline runs a 400-prompt adversarial eval against vLLM-served candidates, reporting attack-success-rate per category into W&B and blocking promotion if the rate exceeds the prior release by more than 1%.",
        "technical",
    ),
    # 33. curriculum sampling — domain weights
    (
        "Reweighted the domain mix to 45% code, 30% web, 20% books, 5% math after ablation showed the prior 70% web mix plateaued on HumanEval below 40%.",
        "technical",
        "The pretraining data sampler draws document batches with per-domain Dirichlet weights (code 0.45, web 0.30, books 0.20, math 0.05) re-normalised every 500M tokens and logged as a stacked-area chart in W&B.",
        "technical",
    ),
    # 34. launcher — torchrun over accelerate
    (
        "Switched the launcher from Accelerate to plain torchrun after silent rank-binding mismatches on multi-node jobs caused NCCL timeouts at init.",
        "technical",
        "Multi-node training is launched by torchrun with rdzv_backend=c10d and a dedicated etcd coordinator, using SLURM srun only to allocate nodes and export NCCL_SOCKET_IFNAME for InfiniBand.",
        "technical",
    ),
    # 35. numerical stability — logit cap
    (
        "Added a softmax logit cap of 30 after the pretraining loss spiked to NaN at step 11k when a single head produced logits in the hundreds.",
        "technical",
        "The model applies a tanh-based soft logit cap of 30 on the final LM-head output, following the Gemma 2 recipe, implemented as a fused triton kernel to avoid an extra pass over the vocabulary tensor.",
        "technical",
    ),
    # 36. data tokenisation — offline pre-tokenisation
    (
        "Moved tokenisation out of the DataLoader into an offline Spark job after on-the-fly tokenisation bottlenecked CPU utilisation at 98% and starved the GPUs.",
        "technical",
        "The pretraining corpus is pre-tokenised by a Spark job into 4k-token packed sequences stored as int32 Arrow files on S3, read at training time with a zero-copy memory-mapped loader and no per-batch tokenisation.",
        "technical",
    ),
    # 37. reproducibility — deterministic seeding
    (
        "Mandated full deterministic seeding (torch, numpy, python random, cuDNN, NCCL) after two nominally identical runs diverged in eval loss by 0.02 nats.",
        "technical",
        "Every training job seeds torch, numpy, random, and os.environ['PYTHONHASHSEED'] from a single run_id, sets torch.use_deterministic_algorithms(True), and pins cuDNN benchmark off and NCCL_ALGO to Ring.",
        "technical",
    ),
    # 38. resume — step-granular resume
    (
        "Built a step-granular resume mechanism after a node preemption at step 24k forced the entire run to restart from the last epoch boundary.",
        "technical",
        "Resume logic reads the latest torch.distributed.checkpoint shard plus a separate dataloader-state file recording (epoch, shard_id, sample_offset, rng_state) so training resumes within one step of the preemption point.",
        "technical",
    ),
    # 39. gradient clipping — global norm cap
    (
        "Lowered the global-norm gradient clip from 1.0 to 0.5 after instability spikes on the 70B run correlated with isolated grad-norm excursions above 3.0.",
        "technical",
        "Gradient clipping is applied globally at max_norm=0.5 on the all-reduced gradients under FSDP, with the pre- and post-clip norms logged every step for anomaly detection.",
        "technical",
    ),
    # 40. weight init — scaled init for depth
    (
        "Adopted depth-scaled residual initialisation after the 40-layer model diverged within 200 steps using standard transformers init.",
        "technical",
        "Residual projection weights are initialised with std = 0.02 / sqrt(2 * n_layers) following the GPT-NeoX recipe, while all other linear layers use torch default Xavier-uniform init.",
        "technical",
    ),
    # 41. MoE — expert parallelism
    (
        "Chose 8-way expert parallelism for the 8x22B MoE run after all-to-all bandwidth profiling showed EP=8 kept comms under 15% of step time.",
        "technical",
        "The MoE stage runs 8-way expert parallelism with 4-way tensor parallelism and 4-way data parallelism on a 128xH100 cluster, using Megablocks grouped-GEMM kernels and a capacity factor of 1.25.",
        "technical",
    ),
    # 42. router loss — auxiliary load balancing
    (
        "Added a 0.01 coefficient load-balancing loss after two experts in the MoE collapsed to near-zero utilisation within the first 3k steps.",
        "technical",
        "The MoE router applies a Switch Transformer style auxiliary loss with coefficient 0.01 plus a z-loss of 1e-3 on router logits, with per-expert token-usage histograms exported every 500 steps.",
        "technical",
    ),
    # 43. evaluation reproducibility — harness pinning
    (
        "Froze lm-evaluation-harness to commit d1abf5a after a point release silently changed MMLU prompt formatting and invalidated two months of comparison runs.",
        "technical",
        "Evaluation runs always execute inside a pinned Docker image containing lm-evaluation-harness commit d1abf5a, transformers 4.41, torch 2.3, and a hash-verified tokenizer_config bundle per candidate model.",
        "technical",
    ),
    # 44. torch compile — selective regions
    (
        "Enabled torch.compile only on the transformer block after compiling the full forward caused recompilation storms whenever batch shapes changed.",
        "technical",
        "torch.compile is applied at the TransformerBlock module level with mode=max-autotune-no-cudagraphs and dynamic=False, compiled once per distinct sequence-length bucket with a 16-entry cache.",
        "technical",
    ),
    # 45. data quality — perplexity filtering
    (
        "Added a KenLM perplexity filter on raw web data after inspection showed roughly 8% of docs were auto-generated SEO spam with degenerate n-gram stats.",
        "technical",
        "The data pipeline runs a KenLM 5-gram model trained on Wikipedia over every candidate document, dropping the top and bottom 1% by log-perplexity and logging the filtered histogram per snapshot.",
        "technical",
    ),
    # 46. evaluation — human preference gate
    (
        "Added a human preference gate (pairwise battles on 200 prompts) before any release after two models with identical benchmark scores had drastically different user feedback.",
        "technical",
        "Release candidates are evaluated by a pairwise side-by-side UI that shows 200 curated prompts to three in-house raters, with Bradley-Terry aggregation and a required win-rate of 55% over the prior release.",
        "technical",
    ),
    # 47. continual learning — replay buffer
    (
        "Introduced a 5% replay buffer from the original SFT mix during the domain-specific fine-tune after the math-tuned variant regressed 7 points on generic instruction-following.",
        "technical",
        "Domain fine-tuning draws each batch as 95% domain data and 5% uniformly sampled general-SFT examples from a pre-built replay shard, with the replay fraction tracked in W&B per step.",
        "technical",
    ),
    # 48. packing — BFD sequence packing
    (
        "Adopted Best-Fit-Decreasing sequence packing after random packing left 14% of every 8k-token pack as pad tokens on the SFT dataset.",
        "technical",
        "SFT training packs multiple conversations into each 8192-token sequence using a Best-Fit-Decreasing packer with EOS boundary tokens and an attention mask that isolates conversations within the same pack.",
        "technical",
    ),
    # 49. safety fine-tune — constitutional AI pass
    (
        "Ran a Constitutional AI revision pass after the first safety DPO produced overly terse refusals that users flagged as unhelpful.",
        "technical",
        "The safety stack appends a Constitutional AI revision phase: 40k prompts are generated from the SFT model, revised by a critic-model loop against a 23-rule constitution, and the (original, revised) pairs feed a second DPO at beta=0.1.",
        "technical",
    ),
    # 50. ablation — shadow evals
    (
        "Established a shadow-eval policy requiring every data or hyperparameter change to ship alongside a 7B ablation run after a quiet mix change cost two weeks of 70B compute.",
        "technical",
        "Every non-trivial training PR triggers a shadow 7B run on a dedicated 8xA100 pool for 5B tokens, with automated eval deltas on MMLU, GSM8K, HumanEval, and IFEval posted as a comment on the PR before approval.",
        "technical",
    ),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (dec_text, dec_domain, arch_text, arch_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            dec_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            arch_id = f"class-{ID_OFFSET + (2 * i):05d}"
            f.write(json.dumps({"id": dec_id, "domain": dec_domain, "text": dec_text, "memory_type": "decision", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"id": arch_id, "domain": arch_domain, "text": arch_text, "memory_type": "architecture", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
