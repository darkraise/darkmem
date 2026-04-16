"""One-off emitter for shared-base batch-167 — technical domain (fine-tuning and PEFT methods: LoRA, QLoRA, DoRA, DPO, ORPO, GRPO, Unsloth, axolotl, TRL, PEFT, SFT, RLHF, schedules, packing, eval harnesses, forgetting).

Writes 50 rows to data/v2/shared/batch_167.tmp.jsonl with ids shared-08301..08350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_167.tmp.jsonl"
ID_OFFSET = 8300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched the 7B chat fine-tune from full fine-tuning to QLoRA on a single A100; the nf4 quantised base plus rank-16 adapters drop VRAM from 80 GB to 24 GB without a quality regression on MT-Bench.", "decision", "technical", False,
     [("QLoRA", "method"), ("full fine-tuning", "method"), ("A100", "platform"), ("nf4", "algorithm"), ("MT-Bench", "tool")],
     [("QLoRA", "full fine-tuning", "REPLACES"), ("QLoRA", "nf4", "USES")],
     "which PEFT method replaced full fine-tuning on the 7B chat job and what quantisation backs it",
     "qlora full fine tune nf4 a100 rank 16 adapter vram mt bench"),
    # --- 2 ---
    ("LoRA adapters are merged back into the base weights before export so the inference path does not pay the two-matmul penalty; training kept them separate for checkpoint size and A/B swaps.", "architecture", "technical", False,
     [("LoRA", "method"), ("base weights", "concept"), ("inference", "concept")],
     [("LoRA", "base weights", "APPLIES_TO")],
     "how does the export pipeline avoid the two-matmul cost of LoRA at inference time",
     "lora merge base weight export inference matmul adapter checkpoint"),
    # --- 3 ---
    ("Adopted DoRA over plain LoRA for the instruction-following run; decomposing the update into magnitude and direction recovered about a point of MMLU that rank-8 LoRA was leaving on the table.", "decision", "technical", False,
     [("DoRA", "method"), ("LoRA", "method"), ("MMLU", "tool"), ("instruction-following", "concept")],
     [("DoRA", "LoRA", "IMPROVES_ON")],
     "which PEFT variant recovered about a point of MMLU that rank-8 LoRA was missing",
     "dora lora magnitude direction mmlu rank 8 instruction follow"),
    # --- 4 ---
    ("VeRA shares a single pair of frozen random projection matrices across all layers and only trains the per-layer scaling vectors; adapter count drops by two orders of magnitude at similar quality.", "fact", "technical", False,
     [("VeRA", "method"), ("random projection matrices", "concept"), ("scaling vectors", "concept")],
     [],
     "how does VeRA shrink trainable parameter count compared to per-layer LoRA adapters",
     "vera random projection scaling vector shared frozen trainable param"),
    # --- 5 ---
    ("LoRA+ uses a higher learning rate on the B matrix than the A matrix; the asymmetric schedule pulled an extra two points of GSM8K on the 8B model compared to the naive equal-LR LoRA baseline.", "decision", "technical", False,
     [("LoRA+", "method"), ("LoRA", "method"), ("B matrix", "concept"), ("A matrix", "concept"), ("GSM8K", "tool")],
     [("LoRA+", "LoRA", "IMPROVES_ON")],
     "which asymmetric learning-rate trick did LoRA+ apply to squeeze more GSM8K out of the 8B model",
     "lora plus b matrix a matrix learning rate asymmetric gsm8k 8b"),
    # --- 6 ---
    ("NEFTune sprinkles uniform noise on the input embeddings during SFT; the embedding jitter consistently lifts AlpacaEval win-rate by three to five points with no change to the optimiser or data.", "fact", "technical", False,
     [("NEFTune", "method"), ("SFT", "method"), ("AlpacaEval", "tool"), ("embedding", "concept")],
     [("NEFTune", "SFT", "APPLIES_TO")],
     "which training-time noise trick lifts AlpacaEval win-rate without touching the optimiser or data",
     "neftune embedding noise sft alpaca eval win rate uniform jitter"),
    # --- 7 ---
    ("DPO replaces the PPO rollout loop with a direct preference-pair loss; the preference dataset goes in, the reference model stays frozen, and there is no separate reward model to keep aligned.", "architecture", "technical", False,
     [("DPO", "method"), ("PPO", "algorithm"), ("reference model", "concept"), ("reward model", "concept")],
     [("DPO", "PPO", "REPLACES")],
     "how does DPO remove the PPO rollout loop and the separate reward model from preference tuning",
     "dpo ppo preference pair loss reference model reward model rollout"),
    # --- 8 ---
    ("IPO fixes the DPO overfitting pathology on deterministic preferences by adding an identity-preference regulariser; chosen-versus-rejected margins stop blowing up late in training.", "decision", "technical", False,
     [("IPO", "method"), ("DPO", "method"), ("identity-preference regulariser", "concept")],
     [("IPO", "DPO", "IMPROVES_ON")],
     "which regulariser does IPO add on top of DPO to curb margin blow-up on deterministic preferences",
     "ipo dpo identity preference regulariser margin overfit determinism"),
    # --- 9 ---
    ("KTO trains on unpaired binary feedback instead of chosen-rejected pairs; the single-label signal made it practical to reuse thumbs-up and thumbs-down logs that never had a paired completion.", "decision", "technical", False,
     [("KTO", "method"), ("binary feedback", "concept"), ("thumbs-up", "concept")],
     [],
     "which preference-learning method works on unpaired binary feedback so thumbs logs become usable",
     "kto unpaired binary feedback thumbs up down chosen rejected signal"),
    # --- 10. noise ---
    ("The office plant in the corner is on its third rebirth and someone has been feeding it leftover pour-over dregs.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("ORPO folds SFT and preference optimisation into a single stage with an odds-ratio penalty; the two-stage SFT-then-DPO recipe got cut to one run and checkpoint churn went with it.", "architecture", "technical", False,
     [("ORPO", "method"), ("SFT", "method"), ("DPO", "method"), ("odds-ratio", "concept")],
     [("ORPO", "SFT", "REPLACES"), ("ORPO", "DPO", "REPLACES")],
     "which single-stage alignment method folded SFT and DPO into one run via an odds-ratio term",
     "orpo sft dpo odds ratio single stage checkpoint churn alignment"),
    # --- 12 ---
    ("RLHF pipeline has three phases: SFT warm-up on curated demonstrations, reward-model training on ranked pairs, and a PPO loop that optimises the policy under a KL penalty against the SFT model.", "architecture", "technical", False,
     [("RLHF", "method"), ("SFT", "method"), ("PPO", "algorithm"), ("KL penalty", "concept")],
     [("RLHF", "PPO", "USES"), ("PPO", "KL penalty", "USES")],
     "which three phases make up classical RLHF and how does PPO stay anchored to the SFT model",
     "rlhf sft reward model ppo kl penalty three phase policy anchor"),
    # --- 13 ---
    ("RLAIF swaps the human ranker stage of RLHF for a critic LLM that produces the preference labels; throughput went from a thousand labels a day to a million with a tenth of the per-label cost.", "decision", "technical", False,
     [("RLAIF", "method"), ("RLHF", "method"), ("critic LLM", "concept")],
     [("RLAIF", "RLHF", "IMPROVES_ON")],
     "which label-source swap does RLAIF make over RLHF and what throughput win did it unlock",
     "rlaif rlhf critic llm preference label throughput cost swap"),
    # --- 14 ---
    ("GRPO drops the value model and estimates advantages from a group of sampled rollouts per prompt; memory savings versus PPO let us fit the 14B reasoning fine-tune on four H100s.", "decision", "technical", False,
     [("GRPO", "algorithm"), ("PPO", "algorithm"), ("value model", "concept"), ("H100", "platform")],
     [("GRPO", "PPO", "REPLACES")],
     "which RL algorithm replaced PPO for the 14B reasoning fine-tune and how did it save memory",
     "grpo ppo value model group rollout advantage h100 14b memory"),
    # --- 15 ---
    ("Picked Unsloth over vanilla PEFT for the single-GPU runs; the fused kernels and manual backward paths roughly double tokens per second on LoRA training at 4k context on a 4090.", "preference", "technical", False,
     [("Unsloth", "tool"), ("PEFT", "library"), ("4090", "platform"), ("LoRA", "method")],
     [("Unsloth", "PEFT", "PREFERS")],
     "which fine-tuning stack did we pick over plain PEFT for single-GPU throughput on the 4090",
     "unsloth peft 4090 lora single gpu fused kernel tokens second"),
    # --- 16 ---
    ("axolotl drives all of the multi-node runs; its yaml-first config feeds into TRL and DeepSpeed with the FSDP option toggled, and reproducibility is one config file instead of eight scattered flags.", "architecture", "technical", False,
     [("axolotl", "tool"), ("TRL", "library"), ("DeepSpeed", "library"), ("FSDP", "method")],
     [("axolotl", "TRL", "USES"), ("axolotl", "DeepSpeed", "USES")],
     "which orchestrator runs the multi-node fine-tunes and what does it delegate TRL and DeepSpeed to",
     "axolotl trl deepspeed fsdp yaml multi node config reproducible"),
    # --- 17 ---
    ("Hugging Face TRL gives us the SFTTrainer, DPOTrainer, and PPOTrainer in one package; the trainer APIs line up so swapping objective from SFT to DPO is a trainer-class change plus a dataset swap.", "fact", "technical", False,
     [("TRL", "library"), ("SFTTrainer", "api"), ("DPOTrainer", "api"), ("PPOTrainer", "api")],
     [("TRL", "SFTTrainer", "HAS_PART"), ("TRL", "DPOTrainer", "HAS_PART")],
     "which library hosts SFTTrainer, DPOTrainer, and PPOTrainer under one unified API",
     "trl sft trainer dpo trainer ppo trainer huggingface api swap"),
    # --- 18 ---
    ("The PEFT library exposes LoRA, prompt tuning, prefix tuning, and P-tuning v2 behind one get_peft_model call; swapping methods became a config change rather than a code refactor.", "fact", "technical", False,
     [("PEFT", "library"), ("LoRA", "method"), ("prompt tuning", "method"), ("prefix tuning", "method"), ("P-tuning", "method"), ("get_peft_model", "api")],
     [("PEFT", "LoRA", "IMPLEMENTS"), ("PEFT", "prompt tuning", "IMPLEMENTS"), ("PEFT", "prefix tuning", "IMPLEMENTS")],
     "which single API in the PEFT library hides LoRA versus prompt, prefix, and P-tuning choices",
     "peft library lora prompt prefix p tuning get peft model api"),
    # --- 19 ---
    ("Classical prompt tuning learns a small bank of continuous soft-prompt vectors prepended to the input; the base model stays frozen and each task gets its own few-kilobyte prompt file.", "fact", "technical", False,
     [("prompt tuning", "method"), ("soft-prompt", "concept")],
     [],
     "which PEFT method trains a bank of continuous soft-prompt vectors while freezing the base model",
     "prompt tuning soft prompt continuous vector frozen base per task"),
    # --- 20 ---
    ("With prefix tuning we prepend trainable key-value pairs at every attention layer instead of just the input; the extra capacity beats prompt tuning on generation tasks but doubles the per-task footprint.", "decision", "technical", False,
     [("prefix tuning", "method"), ("prompt tuning", "method"), ("attention", "concept")],
     [("prefix tuning", "prompt tuning", "IMPROVES_ON")],
     "which PEFT upgrade prepends trainable KV pairs at every attention layer rather than just the input",
     "prefix tuning prompt tuning key value attention generation task"),
    # --- 21 ---
    ("P-tuning v2 beat plain prompt tuning on smaller base models by injecting learnable prompts into every transformer layer; sub-3B models finally matched full-model fine-tuning on GLUE.", "fact", "technical", False,
     [("P-tuning", "method"), ("prompt tuning", "method"), ("GLUE", "tool"), ("transformer", "framework")],
     [("P-tuning", "prompt tuning", "IMPROVES_ON")],
     "which P-tuning revision made sub-3B models match full fine-tuning on GLUE",
     "p tuning v2 prompt layer inject glue sub 3b transformer match"),
    # --- 22 ---
    ("The Houlsby-style adapter layers add a down-up bottleneck inside each transformer block; stacked multi-task adapters let us host six task heads off a single shared base with negligible extra VRAM.", "architecture", "technical", False,
     [("adapter layers", "method"), ("Houlsby", "pattern"), ("transformer", "framework")],
     [],
     "how do Houlsby-style adapter layers let one shared base host multiple task heads cheaply",
     "adapter layer houlsby down up bottleneck transformer multi task"),
    # --- 23 ---
    ("The Hugging Face Trainer orchestrates the SFT loop with gradient accumulation, mixed precision, and checkpointing out of the box; custom TrainerCallback hooks track the eval-harness scores per step.", "architecture", "technical", False,
     [("Hugging Face Trainer", "library"), ("TrainerCallback", "api"), ("gradient accumulation", "concept"), ("mixed precision", "concept")],
     [("Hugging Face Trainer", "TrainerCallback", "HAS_PART")],
     "which built-in Trainer features run the SFT loop and where do the per-step eval hooks plug in",
     "hugging face trainer callback gradient accumulation mixed precision"),
    # --- 24 ---
    ("SFT runs use a cosine schedule with a five-percent warmup and DPO runs use a linear schedule; the split followed a sweep that showed cosine overshoots when the loss landscape is preference-shaped.", "decision", "technical", False,
     [("cosine schedule", "method"), ("linear schedule", "method"), ("SFT", "method"), ("DPO", "method"), ("warmup", "concept")],
     [("cosine schedule", "SFT", "APPLIES_TO"), ("linear schedule", "DPO", "APPLIES_TO")],
     "which learning-rate schedules did we pick for SFT versus DPO and what sweep drove the split",
     "cosine linear schedule warmup sft dpo sweep preference landscape"),
    # --- 25 ---
    ("The label smoothing factor at 0.1 stays on for cross-entropy SFT but gets disabled for DPO; smoothing the preference logits blurred the chosen-rejected margin and hurt win-rate on the held-out set.", "problem", "technical", False,
     [("label smoothing", "method"), ("cross-entropy", "algorithm"), ("SFT", "method"), ("DPO", "method")],
     [("label smoothing", "SFT", "APPLIES_TO")],
     "why does label smoothing stay on for SFT but get disabled for DPO in our recipes",
     "label smoothing cross entropy sft dpo preference margin win rate"),
    # --- 26 ---
    ("The effective batch size is fixed at 256 across all SFT runs regardless of hardware: a smaller micro-batch plus more gradient accumulation steps gets us there on the 4090 and on the 8xA100 pod.", "fact", "technical", False,
     [("effective batch size", "concept"), ("gradient accumulation", "concept"), ("4090", "platform"), ("A100", "platform")],
     [],
     "how does the pipeline keep the effective batch size constant across the 4090 and the 8xA100 pod",
     "effective batch size 256 gradient accumulation micro 4090 a100"),
    # --- 27 ---
    ("The sequence packing pass concatenates short examples up to the 4096 context and masks attention across document boundaries; throughput roughly doubled versus padding-to-max on the ShareGPT mix.", "decision", "technical", False,
     [("sequence packing", "method"), ("attention", "concept"), ("ShareGPT", "tool")],
     [("sequence packing", "attention", "USES")],
     "which packing trick doubled throughput over padding-to-max on the ShareGPT mix and how are docs separated",
     "sequence packing 4096 attention mask document boundary share gpt"),
    # --- 28 ---
    ("The sequence length bucketing stage groups examples into 512, 1024, 2048, and 4096 buckets; samples inside a bucket pad only to the bucket boundary, which cut wasted tokens by about forty percent.", "architecture", "technical", False,
     [("sequence length bucketing", "method"), ("bucket", "concept")],
     [],
     "how does sequence-length bucketing cut wasted padding tokens across the SFT dataset",
     "sequence length bucket 512 1024 2048 4096 pad waste token"),
    # --- 29 ---
    ("The data mixing step is controlled by a ratio manifest: fifty percent instruction data, thirty percent code, fifteen percent math, five percent safety refusals; the mixer streams weighted samples per step.", "architecture", "technical", False,
     [("data mixing", "method"), ("ratio manifest", "concept"), ("safety refusal", "concept")],
     [],
     "which manifest controls the instruction, code, math, and safety data ratios during SFT",
     "data mix ratio manifest instruction code math safety refusal stream"),
    # --- 30 ---
    ("Our synthetic data generation for the math slice runs through Qwen3.5:4b with a rubric-scored filter; only responses that pass a solver check land in the training set, so garbage-in stays bounded.", "architecture", "technical", False,
     [("synthetic data", "method"), ("Qwen3.5:4b", "technology"), ("rubric-scored filter", "concept"), ("solver check", "concept")],
     [("synthetic data", "Qwen3.5:4b", "USES"), ("solver check", "synthetic data", "APPLIES_TO")],
     "how does the synthetic math pipeline keep garbage out of the training set",
     "synthetic data qwen3 5 4b rubric filter solver check math slice"),
    # --- 31 ---
    ("lm-evaluation-harness runs nightly on every checkpoint against MMLU, ARC-C, HellaSwag, TruthfulQA, and GSM8K; a regression gate blocks the merge if any task drops more than half a point.", "architecture", "technical", False,
     [("lm-evaluation-harness", "tool"), ("MMLU", "tool"), ("ARC-C", "tool"), ("HellaSwag", "tool"), ("GSM8K", "tool")],
     [("lm-evaluation-harness", "MMLU", "USES"), ("lm-evaluation-harness", "GSM8K", "USES")],
     "which eval harness gates checkpoint merges and which task suite does it cover nightly",
     "lm eval harness mmlu arc hellaswag truthful qa gsm8k nightly"),
    # --- 32 ---
    ("Picked lm-evaluation-harness over HELM for the internal gate; HELM stays in quarterly reports since its broader scenario coverage is overkill for per-checkpoint signal but useful for stakeholder comms.", "decision", "technical", False,
     [("lm-evaluation-harness", "tool"), ("HELM", "tool")],
     [("lm-evaluation-harness", "HELM", "PREFERS")],
     "which eval harness won the per-checkpoint gate and what role does HELM still play",
     "lm eval harness helm quarterly report scenario gate checkpoint"),
    # --- 33 ---
    ("Hit catastrophic forgetting on the code fine-tune: MMLU dropped four points after a math-only continuation run; a replay buffer of the original SFT mix at ten percent restored the score.", "problem", "technical", False,
     [("catastrophic forgetting", "concept"), ("replay buffer", "method"), ("MMLU", "tool"), ("SFT", "method")],
     [("replay buffer", "catastrophic forgetting", "FIXES")],
     "which replay strategy fixed the four-point MMLU drop from the math-only continuation run",
     "catastrophic forgetting mmlu math replay buffer sft mix restore"),
    # --- 34 ---
    ("LoRA rank landed at 16 after a sweep from 4 to 64; gains flattened past 16 on MMLU and GSM8K while checkpoint size kept climbing, so rank 16 became the default in the training config.", "decision", "technical", False,
     [("LoRA", "method"), ("MMLU", "tool"), ("GSM8K", "tool"), ("training config", "config")],
     [],
     "which LoRA rank did the sweep settle on and what two benchmarks drove the pick",
     "lora rank 16 sweep 4 64 mmlu gsm8k flatten checkpoint size"),
    # --- 35 ---
    ("QLoRA target modules include q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, and down_proj; dropping gate/up/down costs about a point of GSM8K so all-linear stays the default.", "decision", "technical", False,
     [("QLoRA", "method"), ("q_proj", "concept"), ("gate_proj", "concept"), ("GSM8K", "tool")],
     [],
     "which QLoRA target modules did we settle on after the GSM8K ablation",
     "qlora target module q proj gate up down gsm8k ablation all linear"),
    # --- 36 ---
    ("FSDP with full-shard plus cpu-offload runs the 70B DPO job on 8xH100 80GB; ZeRO-3 via DeepSpeed was tried first but ran out of memory at the reference-model forward on the same hardware.", "problem", "technical", False,
     [("FSDP", "method"), ("ZeRO-3", "method"), ("DeepSpeed", "library"), ("H100", "platform"), ("DPO", "method")],
     [("FSDP", "ZeRO-3", "REPLACES")],
     "which distributed-training setup replaced ZeRO-3 for the 70B DPO job on 8xH100",
     "fsdp zero 3 deepspeed h100 70b dpo reference model oom offload"),
    # --- 37 ---
    ("Training run 2026-03-14 landed the 8B DPO checkpoint that cleared a 68.5 MT-Bench score; the recipe is now the template for every subsequent chat-tune in the lab notebook.", "milestone", "technical", False,
     [("DPO", "method"), ("MT-Bench", "tool"), ("2026-03-14", "date")],
     [],
     "which dated run produced the 8B DPO checkpoint that set the MT-Bench template at 68.5",
     "training run 2026 03 14 8b dpo mt bench 68 5 template chat"),
    # --- 38 ---
    ("First successful QLoRA SFT of the 13B base landed on 2026-02-09 on a single 3090; the run proved that prosumer hardware could fine-tune mid-size models and unblocked the hobbyist fork of the roadmap.", "milestone", "technical", False,
     [("QLoRA", "method"), ("SFT", "method"), ("3090", "platform"), ("2026-02-09", "date")],
     [("QLoRA", "3090", "DEPLOYED_ON")],
     "which dated milestone proved QLoRA SFT of a 13B base on a single 3090 was viable",
     "qlora sft 13b 3090 2026 02 09 prosumer milestone hobbyist fork"),
    # --- 39 ---
    ("First end-to-end RLHF run finished on 2026-01-22 with a reward-model AUC of 0.78 and a PPO policy that held its KL under three against the SFT reference for the full eighty-thousand steps.", "milestone", "technical", False,
     [("RLHF", "method"), ("PPO", "algorithm"), ("SFT", "method"), ("2026-01-22", "date")],
     [],
     "which dated RLHF milestone hit reward-model AUC 0.78 and kept PPO KL under three",
     "rlhf 2026 01 22 reward model auc 0 78 ppo kl sft eighty thousand"),
    # --- 40 ---
    ("First DPO run replacing the PPO pipeline shipped on 2026-02-28 and cut total wall-clock time from eighteen hours to four on the same 8xA100 node with a better AlpacaEval score.", "milestone", "technical", False,
     [("DPO", "method"), ("PPO", "algorithm"), ("A100", "platform"), ("AlpacaEval", "tool"), ("2026-02-28", "date")],
     [("DPO", "PPO", "REPLACES")],
     "which dated DPO run cut an eighteen-hour PPO pipeline down to four hours on the same A100 node",
     "dpo ppo 2026 02 28 a100 alpaca eval wall clock eighteen four"),
    # --- 41 ---
    ("Paged-AdamW-8bit via bitsandbytes keeps optimiser state off the main VRAM budget; the swap from fp32 AdamW freed about sixteen gigs on the 70B QLoRA run and eliminated the OOM at step one.", "problem", "technical", False,
     [("bitsandbytes", "library"), ("AdamW", "algorithm"), ("QLoRA", "method")],
     [("bitsandbytes", "AdamW", "IMPROVES_ON")],
     "which optimiser change freed sixteen gigs of VRAM on the 70B QLoRA run and fixed the OOM",
     "bitsandbytes paged adamw 8bit optimiser state qlora 70b vram"),
    # --- 42 ---
    ("The LoRA dropout is pinned to 0.05 and scaling alpha to 32 in the training config; lower alpha under-fit the math slice and higher dropout washed out gains on the small instruction set.", "reference", "technical", False,
     [("LoRA", "method"), ("training config", "config"), ("dropout", "concept"), ("alpha", "concept")],
     [],
     "which LoRA dropout and alpha values did the training config settle on",
     "lora dropout 0 05 alpha 32 training config math instruction"),
    # --- 43. noise ---
    ("The microwave in the ops kitchen has a sticky note that has survived three leadership changes and one rebrand.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Use TRL when you want objective swaps with minimal glue; reach for axolotl when multi-node FSDP is on the table; keep Unsloth for the one-GPU hackathon path.", "preference", "technical", False,
     [("TRL", "library"), ("axolotl", "tool"), ("Unsloth", "tool"), ("FSDP", "method")],
     [("axolotl", "FSDP", "SUPPORTS")],
     "which fine-tuning tool do we reach for single-GPU versus multi-node versus objective swaps",
     "trl axolotl unsloth fsdp single gpu multi node objective swap"),
    # --- 45 ---
    ("Prefer DPO over PPO for new preference-tuning work unless a live reward model already exists; the reduced infra surface more than pays for the slight quality cost on adversarial probes.", "preference", "technical", False,
     [("DPO", "method"), ("PPO", "algorithm"), ("preference-tuning", "concept")],
     [("DPO", "PPO", "PREFERS")],
     "which preference-tuning method do we pick by default and when does PPO still win",
     "dpo ppo preference tuning default reward model adversarial probe"),
    # --- 46 ---
    ("Store every training config as yaml under configs/ with the git sha of the codebase embedded; reproducing an old run is a checkout plus a single axolotl train command with no hidden state.", "reference", "technical", False,
     [("axolotl", "tool"), ("yaml", "language"), ("git sha", "concept"), ("configs/", "file")],
     [],
     "how does the repo make a past fine-tune reproducible from a config and a checkout",
     "axolotl yaml config git sha repro train hidden state checkout"),
    # --- 47 ---
    ("The lm-evaluation-harness invocation pattern is documented in docs/eval/harness.md with the exact task list, few-shot counts, and decoding parameters per benchmark; deviations go in the run-log notebook.", "reference", "technical", False,
     [("lm-evaluation-harness", "tool"), ("docs/eval/harness.md", "file"), ("few-shot", "concept")],
     [],
     "which doc pins the harness invocation per benchmark and where do deviations get logged",
     "lm eval harness docs eval harness md few shot decoding run log"),
    # --- 48 ---
    ("The canonical SFT recipe lives in docs/fine-tuning/sft-recipe.md: cosine schedule, 2e-5 base LR, 256 effective batch, 4096 packed sequences, NEFTune 5.0, and label smoothing 0.1.", "reference", "technical", False,
     [("SFT", "method"), ("docs/fine-tuning/sft-recipe.md", "file"), ("NEFTune", "method"), ("label smoothing", "method")],
     [],
     "which doc pins the canonical SFT recipe including NEFTune alpha and the learning-rate schedule",
     "sft recipe doc cosine 2e 5 256 batch 4096 packed neftune smoothing"),
    # --- 49 ---
    ("The checkpoint naming convention is model-base-stage-rank-date: llama3-8b-dpo-r16-20260314; the schema is parsed by the lm-evaluation-harness runner to route the right task list and few-shot config per stage.", "reference", "technical", False,
     [("checkpoint", "concept"), ("lm-evaluation-harness", "tool"), ("llama3-8b", "technology")],
     [],
     "which checkpoint naming convention does the eval runner parse to pick the right task list",
     "checkpoint naming convention model stage rank date llama3 8b dpo"),
    # --- 50 ---
    ("The fine-tune tracking spreadsheet lives at docs/fine-tuning/runs.md and holds one row per run with dataset sha, recipe sha, harness scores, and a link to the wandb dashboard for loss curves.", "reference", "technical", False,
     [("docs/fine-tuning/runs.md", "file"), ("wandb", "service"), ("dataset sha", "concept"), ("harness", "tool")],
     [],
     "which tracking doc pairs each fine-tune run with dataset sha, recipe sha, and its wandb link",
     "docs fine tuning runs md wandb dataset sha recipe harness score"),
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
