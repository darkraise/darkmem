"""One-off emitter for shared-base batch-150 — technical domain (GPU programming and accelerators: CUDA, ROCm, Triton, CUTLASS, NCCL, TensorRT, Hopper, MI300, Metal, MLX, TPU, Flash Attention).

Writes 50 rows to data/v2/shared/batch_150.tmp.jsonl with ids shared-07451..07500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_150.tmp.jsonl"
ID_OFFSET = 7450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the hand-written matmul kernel for CUTLASS tile iterators on H100; the warp-specialised mainloop now overlaps global loads with tensor-core MMAs cleanly on Hopper.", "decision", "technical", False,
     [("CUTLASS", "library"), ("H100", "platform"), ("Hopper", "platform"), ("tensor-core", "concept")],
     [("CUTLASS", "H100", "DEPLOYED_ON"), ("CUTLASS", "tensor-core", "USES")],
     "which matmul library replaced the hand-written kernel on Hopper and what overlap does it buy",
     "cutlass h100 hopper warp specialised tensor core matmul overlap"),
    # --- 2 ---
    ("Triton beat our bespoke CUDA attention by eight percent on A100 once we tiled over the head dimension and let the autotuner pick block sizes; the custom kernel got retired.", "milestone", "technical", False,
     [("Triton", "library"), ("CUDA", "technology"), ("A100", "platform"), ("autotuner", "tool")],
     [("Triton", "CUDA", "REPLACES")],
     "which kernel DSL replaced hand-written CUDA attention on A100 and what tuned the block sizes",
     "triton cuda a100 autotune attention head tile block size retire"),
    # --- 3 ---
    ("Flash Attention v3 replaced the fused QKV pass on Hopper; the warpgroup MMA path plus TMA loads pushed our 70B forward step from 42 to 29 ms per token at context 8192.", "milestone", "technical", False,
     [("Flash Attention v3", "algorithm"), ("Hopper", "platform"), ("warpgroup MMA", "concept"), ("TMA", "concept")],
     [("Flash Attention v3", "Hopper", "DEPLOYED_ON"), ("Flash Attention v3", "TMA", "USES")],
     "which attention kernel cut the 70B forward-step time on Hopper and which Hopper features drove the win",
     "flash attention v3 hopper warpgroup tma 70b forward step token"),
    # --- 4 ---
    ("Migrated the serving stack from vLLM's PagedAttention on A100 to the H200 pool; the 141 GB HBM3e lifted KV-cache capacity enough to drop the paging rate into the noise floor.", "architecture", "technical", False,
     [("vLLM", "framework"), ("PagedAttention", "algorithm"), ("A100", "platform"), ("H200", "platform"), ("HBM3e", "technology")],
     [("PagedAttention", "H200", "DEPLOYED_ON")],
     "which memory tier on H200 let PagedAttention stop thrashing the KV cache after the A100 migration",
     "vllm paged attention a100 h200 hbm3e kv cache paging rate"),
    # --- 5 ---
    ("Coalesced access saved us on the embedding gather: restructuring the index buffer so 32 adjacent threads hit consecutive 4-byte lanes dropped L1 misses from 38% to 4% on an L4.", "fact", "technical", False,
     [("Coalesced access", "pattern"), ("L4", "platform"), ("L1", "infrastructure"), ("embedding gather", "pattern")],
     [("Coalesced access", "embedding gather", "APPLIES_TO")],
     "which access pattern fix cut L1 miss rate on the embedding gather kernel on Ada L4",
     "coalesced access l1 miss embedding gather l4 ada index lane"),
    # --- 6 ---
    ("Picked NCCL over Gloo for multi-node allreduce; the tree algorithm with NVLink intra-node and InfiniBand inter-node sustained 92% of the 400 Gb/s fabric on eight H100 nodes.", "decision", "technical", False,
     [("NCCL", "library"), ("Gloo", "library"), ("NVLink", "infrastructure"), ("InfiniBand", "protocol"), ("H100", "platform")],
     [("NCCL", "Gloo", "PREFERS"), ("NCCL", "NVLink", "USES")],
     "which collective library replaced Gloo for multi-node allreduce and what fabric utilisation did it hit",
     "nccl gloo allreduce nvlink infiniband h100 fabric tree collective"),
    # --- 7 ---
    ("Dropped cuDNN's default convolution heuristic for the explicit IMMA algo 7 on small batches; latency on the 1x3x224x224 path fell 18% after the override went into the serving config.", "fact", "technical", False,
     [("cuDNN", "library"), ("IMMA", "algorithm"), ("1x3x224x224", "config")],
     [("IMMA", "cuDNN", "IMPROVES_ON")],
     "which cuDNN override cut small-batch convolution latency on the 224-input serving path",
     "cudnn imma algo 7 small batch convolution latency override 224"),
    # --- 8 ---
    ("Occupancy analysis flagged our softmax kernel at 25% theoretical on an A100; trimming per-thread registers from 96 to 64 via explicit __launch_bounds__ lifted it to 75% and threw a real speedup.", "fact", "technical", False,
     [("Occupancy", "concept"), ("softmax", "algorithm"), ("A100", "platform"), ("__launch_bounds__", "api")],
     [],
     "which register-count tweak lifted the softmax kernel occupancy on A100 from 25 to 75 percent",
     "occupancy softmax register launch bounds a100 25 75 theoretical"),
    # --- 9 ---
    ("Shared memory bank conflicts dominated the transpose kernel profile on L4; padding the tile to 33 columns instead of 32 eliminated the 32-way conflict and cut kernel time in half.", "fact", "technical", False,
     [("Shared memory", "concept"), ("bank conflict", "pattern"), ("transpose", "algorithm"), ("L4", "platform")],
     [],
     "which tile padding trick killed the 32-way shared memory bank conflict in the transpose kernel",
     "shared memory bank conflict transpose tile pad 33 column l4"),
    # --- 10. noise ---
    ("The coffee machine in the east wing ran out of decaf pods sometime Tuesday and nobody has owned up to restocking it since.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Warp shuffle primitives replaced the shared-memory reduction in the layernorm kernel; __shfl_xor_sync across a 32-lane warp finishes the partial sum with zero shared memory traffic.", "architecture", "technical", False,
     [("Warp shuffle", "concept"), ("__shfl_xor_sync", "api"), ("layernorm", "algorithm"), ("shared memory", "concept")],
     [("Warp shuffle", "shared memory", "REPLACES")],
     "which primitive replaced shared-memory reduction in the layernorm kernel and what traffic did it eliminate",
     "warp shuffle shfl xor sync layernorm reduction shared memory 32"),
    # --- 12 ---
    ("Cooperative groups let the multi-block prefix-sum reuse a grid-wide sync without a kernel relaunch; the grid_group.sync call replaced the two-pass dispatch we had before on A100.", "decision", "technical", False,
     [("Cooperative groups", "api"), ("grid_group", "api"), ("prefix-sum", "algorithm"), ("A100", "platform")],
     [("Cooperative groups", "grid_group", "HAS_PART")],
     "which API replaced the two-pass dispatch for grid-wide prefix-sum sync on A100",
     "cooperative group grid sync prefix sum two pass dispatch a100"),
    # --- 13 ---
    ("Kernel fusion of bias-add, GELU, and dropout into a single CUDA kernel cut three global-memory round trips to one; the fused kernel now sits on the critical path for the MLP block.", "architecture", "technical", False,
     [("Kernel fusion", "pattern"), ("GELU", "algorithm"), ("CUDA", "technology"), ("MLP block", "concept")],
     [("Kernel fusion", "MLP block", "APPLIES_TO")],
     "which fusion cut the MLP block's global-memory round trips and how many trips did it collapse",
     "kernel fusion bias gelu dropout cuda global memory mlp round"),
    # --- 14 ---
    ("Mixed precision FP16 with loss scaling shipped for training; the master weights stay FP32 and the allreduce runs in FP16 over NCCL, which halved gradient bandwidth on the cluster.", "milestone", "technical", False,
     [("FP16", "concept"), ("FP32", "concept"), ("loss scaling", "method"), ("NCCL", "library")],
     [("FP16", "NCCL", "APPLIES_TO")],
     "which mixed precision setup halved gradient bandwidth during allreduce while keeping master weights safe",
     "fp16 fp32 loss scale nccl master weight gradient bandwidth half"),
    # --- 15 ---
    ("BF16 won over FP16 for Llama pretraining on TPU v5p; the wider exponent range let loss scaling go away entirely and removed a class of overflow stalls at high LR.", "decision", "technical", False,
     [("BF16", "concept"), ("FP16", "concept"), ("TPU v5p", "platform"), ("Llama", "project")],
     [("BF16", "FP16", "PREFERS"), ("BF16", "TPU v5p", "DEPLOYED_ON")],
     "which precision format replaced FP16 on TPU v5p for Llama pretraining and what stall class did it remove",
     "bf16 fp16 tpu v5p llama pretrain exponent overflow loss scale"),
    # --- 16 ---
    ("FP8 E4M3 matmuls on H100 shipped behind a feature flag; TransformerEngine handled the scaling factors and the 65B forward pass landed at 1.7x the BF16 throughput without quality loss.", "milestone", "technical", False,
     [("FP8", "concept"), ("E4M3", "concept"), ("H100", "platform"), ("TransformerEngine", "library"), ("BF16", "concept")],
     [("TransformerEngine", "FP8", "USES"), ("FP8", "BF16", "IMPROVES_ON")],
     "which FP8 format shipped on H100 and what speedup over BF16 did TransformerEngine deliver at 65B",
     "fp8 e4m3 h100 transformer engine 65b bf16 throughput scale factor"),
    # --- 17 ---
    ("TensorRT replaced the PyTorch eager path for the ASR encoder in production; the INT8 engine with per-tensor calibration shaved 40% off p99 latency on the L4 serving pool.", "decision", "technical", False,
     [("TensorRT", "framework"), ("PyTorch", "framework"), ("INT8", "concept"), ("L4", "platform"), ("ASR encoder", "project")],
     [("TensorRT", "PyTorch", "REPLACES"), ("TensorRT", "L4", "DEPLOYED_ON")],
     "which inference engine replaced eager PyTorch for ASR and what latency tier did INT8 hit on L4",
     "tensorrt pytorch int8 asr encoder l4 p99 latency calibration"),
    # --- 18 ---
    ("HIP is the portability layer for the ROCm build; the same kernel source compiles to CUDA on NVIDIA and to GCN/CDNA ISA on the MI300X rack with hipify handling the intrinsics.", "architecture", "technical", False,
     [("HIP", "language"), ("ROCm", "platform"), ("CUDA", "technology"), ("MI300X", "platform"), ("hipify", "tool")],
     [("HIP", "ROCm", "USES"), ("HIP", "MI300X", "DEPLOYED_ON")],
     "which portability layer lets one kernel source target both CUDA and the MI300X rack",
     "hip rocm cuda mi300x hipify gcn cdna intrinsic portability"),
    # --- 19 ---
    ("SYCL was evaluated for cross-vendor GPU work and we chose oneAPI's DPC++ for the Intel Max pool; the unified-memory model simplified the host-device pointer juggle in the image pipeline.", "decision", "technical", False,
     [("SYCL", "language"), ("oneAPI", "framework"), ("DPC++", "language"), ("Intel Max", "platform"), ("unified-memory", "concept")],
     [("DPC++", "Intel Max", "DEPLOYED_ON"), ("DPC++", "unified-memory", "USES")],
     "which SYCL toolchain was picked for the Intel Max pool and which memory model simplified the port",
     "sycl oneapi dpcpp intel max unified memory image pipeline host"),
    # --- 20 ---
    ("OpenCL is still the common denominator for the embedded inference SKU; the same kernels run on Mali, Adreno, and Intel iGPU, with a runtime shim picking the binary cache per device.", "fact", "technical", False,
     [("OpenCL", "technology"), ("Mali", "platform"), ("Adreno", "platform"), ("Intel iGPU", "platform")],
     [("OpenCL", "Mali", "DEPLOYED_ON"), ("OpenCL", "Adreno", "DEPLOYED_ON")],
     "which cross-vendor GPU runtime still targets the embedded inference SKU across Mali and Adreno",
     "opencl mali adreno intel igpu embedded inference binary cache"),
    # --- 21 ---
    ("cuBLAS GEMM beat our CUTLASS kernel at batch size 1 on an L4, so the serving path branches: cuBLAS for batch 1, CUTLASS tiles for batches of 8 and up where the tile overlap pays off.", "decision", "technical", False,
     [("cuBLAS", "library"), ("CUTLASS", "library"), ("GEMM", "algorithm"), ("L4", "platform")],
     [("cuBLAS", "GEMM", "IMPLEMENTS"), ("CUTLASS", "GEMM", "IMPLEMENTS")],
     "which library handles which batch size on the L4 GEMM serving path and why is it split",
     "cublas cutlass gemm batch 1 l4 tile overlap split serving"),
    # --- 22 ---
    ("NVLink bandwidth saturation on the DGX H100 is the new bottleneck: intra-node allreduce of a 70B optimiser state hits 780 GB/s peer-to-peer, still 15% off the theoretical 900 GB/s.", "problem", "technical", False,
     [("NVLink", "infrastructure"), ("DGX H100", "platform"), ("allreduce", "algorithm")],
     [("allreduce", "NVLink", "USES")],
     "which fabric is capping intra-node allreduce bandwidth on DGX H100 and how close to theoretical are we",
     "nvlink dgx h100 allreduce 780 gb 900 optimiser state peer"),
    # --- 23 ---
    ("Grace Hopper GH200 evaluation showed the 900 GB/s C2C link beats PCIe Gen5 for host-device tensor streaming; we now prefer GH200 for the embedding-heavy recommendation inference path.", "decision", "technical", False,
     [("GH200", "platform"), ("C2C link", "infrastructure"), ("PCIe Gen5", "protocol")],
     [("GH200", "C2C link", "HAS_PART"), ("C2C link", "PCIe Gen5", "IMPROVES_ON")],
     "which interconnect on GH200 beats PCIe Gen5 for host-device tensor streaming in the recommender path",
     "gh200 c2c link pcie gen5 host device tensor embedding recommender"),
    # --- 24 ---
    ("AMD MI300X wins on HBM capacity: 192 GB per card let the 405B BF16 weights fit on a single device, something that forces tensor parallel across four H100 SXM5s on the NVIDIA side.", "fact", "technical", False,
     [("MI300X", "platform"), ("HBM", "technology"), ("H100 SXM5", "platform"), ("tensor parallel", "pattern")],
     [("MI300X", "HBM", "HAS_PART")],
     "which AMD card fits the 405B weights on one device and what does the NVIDIA side need instead",
     "mi300x hbm 192 gb 405b bf16 h100 sxm5 tensor parallel four"),
    # --- 25 ---
    ("Apple Metal Performance Shaders backs the on-device inference build for iOS; MPSGraph auto-fuses the attention block and we reuse the same weights from the server path via coreml conversion.", "architecture", "technical", False,
     [("Metal Performance Shaders", "library"), ("MPSGraph", "api"), ("iOS", "platform"), ("coreml", "tool")],
     [("MPSGraph", "Metal Performance Shaders", "HAS_PART"), ("MPSGraph", "iOS", "DEPLOYED_ON")],
     "which Apple graph API auto-fuses attention for the on-device iOS inference build",
     "metal performance shader mps graph ios coreml attention fuse"),
    # --- 26 ---
    ("MLX replaced PyTorch on the M3 Max dev boxes for local fine-tuning; the unified-memory lazy-eval model lets us train a 7B LoRA on 128 GB without paging to SSD.", "decision", "technical", False,
     [("MLX", "framework"), ("PyTorch", "framework"), ("M3 Max", "platform"), ("LoRA", "method")],
     [("MLX", "PyTorch", "REPLACES"), ("MLX", "M3 Max", "DEPLOYED_ON")],
     "which Apple framework replaced PyTorch on M3 Max dev boxes for local LoRA fine-tuning",
     "mlx pytorch m3 max lora 7b unified memory lazy paging local"),
    # --- 27 ---
    ("Intel Gaudi2 HLS systems were benched against H100 on BERT-large pretraining; cost per token came in 20% lower but the software stack gap on custom kernels pushed us back to H100 for now.", "decision", "technical", False,
     [("Gaudi2", "platform"), ("H100", "platform"), ("BERT-large", "project"), ("HLS", "infrastructure")],
     [("Gaudi2", "H100", "RELATED_TO")],
     "why did we revert to H100 after the Gaudi2 BERT-large cost-per-token benchmark looked favourable",
     "gaudi2 h100 bert large pretrain cost token hls custom kernel"),
    # --- 28 ---
    ("TPU v5p pods run the pretraining job on JAX with XLA sharding; BF16 compute with FP32 accumulation on the MXU gave us a stable loss curve even at 16k global batch size.", "architecture", "technical", False,
     [("TPU v5p", "platform"), ("JAX", "framework"), ("XLA", "tool"), ("MXU", "infrastructure"), ("BF16", "concept")],
     [("JAX", "XLA", "USES"), ("XLA", "TPU v5p", "DEPLOYED_ON")],
     "which software stack runs pretraining on TPU v5p pods and which accumulator setup stabilised loss",
     "tpu v5p jax xla mxu bf16 fp32 shard pretrain 16k batch stable"),
    # --- 29 ---
    ("Triton autotune configs were pinned to a JSON cache per device-SM pair; the first-run recompile storm on the serving pod went from 42 s to 1.3 s once the cache was baked into the image.", "milestone", "technical", False,
     [("Triton", "library"), ("autotune", "tool"), ("JSON", "technology"), ("SM", "infrastructure")],
     [("Triton", "autotune", "HAS_PART")],
     "which artifact cached Triton autotune configs per SM and how did it change first-run serving latency",
     "triton autotune json cache device sm serving pod recompile 42 s"),
    # --- 30 ---
    ("PTX inspection caught the codegen regression in CUDA 12.4 where our custom atomic was lowered to a red.sys.global instead of red.relaxed; we pinned the toolchain to CUDA 12.3 until the fix lands.", "problem", "technical", False,
     [("PTX", "language"), ("CUDA 12.4", "tool"), ("CUDA 12.3", "tool"), ("red.sys.global", "api")],
     [("CUDA 12.3", "CUDA 12.4", "REPLACES")],
     "which CUDA toolchain got pinned after a PTX codegen regression lowered our atomic to the wrong scope",
     "ptx cuda 12 4 12 3 atomic red sys global relaxed pin toolchain"),
    # --- 31 ---
    ("Nsight Compute flagged tail-effect stalls on the A100 FlashAttention kernel: the last wave ran only eight SMs of 108; reshaping the block-to-SM assignment cut kernel time by 11%.", "fact", "technical", False,
     [("Nsight Compute", "tool"), ("A100", "platform"), ("FlashAttention", "algorithm"), ("SM", "infrastructure")],
     [("Nsight Compute", "FlashAttention", "APPLIES_TO")],
     "which profiler flagged tail-effect stalls on A100 FlashAttention and what reshape fixed the wave",
     "nsight compute a100 flash attention tail effect wave 108 sm 11"),
    # --- 32 ---
    ("Global load uncoalescing on the scatter kernel came from a stride-7 index pattern; switching to a sorted scatter with a two-pass bucket made access sequential and fixed L2 utilisation.", "problem", "technical", False,
     [("scatter kernel", "algorithm"), ("stride-7", "pattern"), ("L2", "infrastructure"), ("two-pass bucket", "algorithm")],
     [("two-pass bucket", "scatter kernel", "FIXES")],
     "which sort pattern fixed uncoalesced global loads from a stride-7 scatter and lifted L2 utilisation",
     "stride 7 scatter kernel coalesce l2 sort two pass bucket sequential"),
    # --- 33 ---
    ("PagedAttention block size of 16 tokens worked best for our Llama-3 70B serving mix; 32-token blocks wasted KV memory on short chats and 8-token blocks raised the block-table lookup cost.", "decision", "technical", False,
     [("PagedAttention", "algorithm"), ("Llama-3 70B", "project"), ("KV memory", "infrastructure"), ("block-table", "pattern")],
     [("PagedAttention", "Llama-3 70B", "APPLIES_TO")],
     "which PagedAttention block size won for Llama-3 70B serving and what failed at 32 and 8 tokens",
     "paged attention block 16 llama 3 70b kv memory table 32 8"),
    # --- 34 ---
    ("TMA descriptors on Hopper let us async-copy a full 128x128 tile into shared memory without a thread cooperation pattern; the SM can start MMAs while the next tile is still landing.", "architecture", "technical", False,
     [("TMA", "concept"), ("Hopper", "platform"), ("shared memory", "concept"), ("SM", "infrastructure")],
     [("TMA", "Hopper", "DEPLOYED_ON")],
     "which Hopper feature async-copies a 128x128 tile into shared memory and overlaps with the next MMA",
     "tma hopper 128 tile shared memory async copy sm mma overlap"),
    # --- 35 ---
    ("Register pressure blew up after enabling FP8 on TransformerEngine; spills to local memory showed in Nsight and we fixed it by splitting the fused GEMM-bias-activation back into two kernels.", "architecture", "technical", False,
     [("Register pressure", "concept"), ("FP8", "concept"), ("TransformerEngine", "library"), ("Nsight", "tool"), ("GEMM", "algorithm")],
     [],
     "which FP8 change blew up register pressure and what refactor got rid of the local-memory spills",
     "register pressure fp8 transformer engine spill nsight gemm split"),
    # --- 36 ---
    ("CUDA graphs captured the whole decoder step and replay on each token; launch overhead on the 72-kernel pipeline fell from 1.8 ms to 0.15 ms on the A100 inference pool.", "milestone", "technical", False,
     [("CUDA graphs", "api"), ("A100", "platform"), ("decoder step", "pattern")],
     [("CUDA graphs", "decoder step", "APPLIES_TO")],
     "which CUDA API replayed the decoder step to cut launch overhead on the A100 inference pool",
     "cuda graphs decoder replay launch overhead 72 kernel a100 1 8 ms"),
    # --- 37 ---
    ("Explicit CUDA streams and events replaced the implicit default stream pattern in the data loader path; overlapping H2D copies with compute on two streams added 9% end-to-end throughput on the DGX.", "decision", "technical", False,
     [("CUDA streams", "api"), ("H2D", "pattern"), ("DGX", "platform"), ("default stream", "pattern")],
     [("CUDA streams", "default stream", "REPLACES")],
     "which stream pattern replaced the default-stream data loader and what H2D overlap did it buy on DGX",
     "stream event default data loader h2d overlap dgx throughput 9"),
    # --- 38 ---
    ("Kernel-authoring guide at docs/gpu/triton-kernels.md documents the Triton block-pointer API we use for masked loads and links the PTX it emits alongside torch.compile integration notes.", "reference", "technical", False,
     [("docs/gpu/triton-kernels.md", "file"), ("Triton", "library"), ("block-pointer", "api"), ("PTX", "language"), ("torch.compile", "tool")],
     [("block-pointer", "Triton", "HAS_PART")],
     "where does the internal kernel-authoring guide live and which Triton API does it center on",
     "triton block pointer docs guide ptx torch compile masked load"),
    # --- 39 ---
    ("GPUDirect RDMA wired the NVMe shard reader to H100 HBM through the NIC; checkpoint load dropped from 73 s to 9 s on the 405B restart path, bypassing host DRAM entirely.", "milestone", "technical", False,
     [("GPUDirect RDMA", "technology"), ("NVMe", "infrastructure"), ("H100", "platform"), ("HBM", "technology")],
     [("GPUDirect RDMA", "NVMe", "USES"), ("GPUDirect RDMA", "H100", "DEPLOYED_ON")],
     "which RDMA path bypassed host DRAM for the 405B checkpoint load and how much did it cut restart time",
     "gpudirect rdma nvme h100 hbm 405b checkpoint restart 73 9 nic"),
    # --- 40 ---
    ("Reference kernel for reduction lives in include/kernels/reduce.cuh; the doc at the top of the file points to the warp-shuffle tree pattern from NVIDIA's cuda-samples repo.", "reference", "technical", False,
     [("reduce.cuh", "file"), ("warp-shuffle", "concept"), ("cuda-samples", "project")],
     [],
     "where does the canonical reduction kernel live and which upstream sample pattern does it document",
     "reduce cuh include kernel warp shuffle cuda samples reduction tree"),
    # --- 41 ---
    ("Docs on occupancy tuning sit in docs/gpu/occupancy.md; it links the CUDA occupancy calculator worksheet and our internal table of register-per-thread thresholds per SM generation.", "reference", "technical", False,
     [("docs/gpu/occupancy.md", "file"), ("CUDA occupancy calculator", "tool"), ("SM", "infrastructure")],
     [],
     "where do we keep the occupancy tuning notes and which upstream worksheet do they cross-reference",
     "docs gpu occupancy md cuda calculator register sm generation thread"),
    # --- 42 ---
    ("NCCL tuning cheat-sheet at docs/infra/nccl.md lists NCCL_IB_HCA, NCCL_ALGO=Tree, and NCCL_SOCKET_IFNAME overrides we validated on the 8-node H100 cluster.", "reference", "technical", False,
     [("docs/infra/nccl.md", "file"), ("NCCL_IB_HCA", "config"), ("NCCL_ALGO", "config"), ("H100", "platform")],
     [],
     "which doc holds the validated NCCL environment overrides for the 8-node H100 cluster",
     "nccl docs infra md ib hca algo tree socket ifname h100 8 node"),
    # --- 43. noise ---
    ("There's a potted fiddle-leaf fig by the window that someone has watered on exactly the wrong schedule for two months running.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Team prefers Triton for new kernels over raw CUDA; the default is to prototype in Triton, profile with Nsight, and only drop to CUDA C++ if a Triton limitation shows up on the critical path.", "preference", "technical", False,
     [("Triton", "library"), ("CUDA", "technology"), ("Nsight", "tool")],
     [("Triton", "CUDA", "PREFERS")],
     "which kernel DSL is the team's default starting point before reaching for raw CUDA",
     "triton cuda nsight prototype kernel default critical path prefer"),
    # --- 45 ---
    ("We prefer BF16 over FP16 for any new training run unless a device forces otherwise; the wider exponent removed a standing class of NaN incidents that used to fill the pager rotation.", "preference", "technical", False,
     [("BF16", "concept"), ("FP16", "concept"), ("NaN", "error")],
     [("BF16", "FP16", "PREFERS")],
     "which precision format is the default for new training runs and which on-call problem did it retire",
     "bf16 fp16 nan training new run default exponent pager on call"),
    # --- 46 ---
    ("Prefer flashinfer over xformers for the attention backend on H100 serving; flashinfer's prefix cache and KV quantisation path hit our throughput target without a custom patch.", "preference", "technical", False,
     [("flashinfer", "library"), ("xformers", "library"), ("H100", "platform"), ("KV quantisation", "method")],
     [("flashinfer", "xformers", "PREFERS"), ("flashinfer", "H100", "DEPLOYED_ON")],
     "which attention backend is preferred on H100 serving and what KV feature sealed the choice",
     "flashinfer xformers h100 attention backend prefix cache kv quant"),
    # --- 47 ---
    ("Prefer capturing decoder steps with CUDA graphs rather than launching kernels per token; a graph replay is the default pattern in new serving code unless dynamic shapes block it.", "preference", "technical", False,
     [("CUDA graphs", "api"), ("decoder step", "pattern")],
     [],
     "which launch pattern is preferred by default in new serving code for the decoder step",
     "cuda graph replay decoder per token launch default dynamic shape"),
    # --- 48 ---
    ("Canonical mixed-precision training recipe is in docs/train/amp.md; it covers BF16 on H100, FP8 with TransformerEngine behind a flag, and the dynamic loss-scale schedule for legacy FP16 paths.", "reference", "technical", False,
     [("docs/train/amp.md", "file"), ("BF16", "concept"), ("H100", "platform"), ("FP8", "concept"), ("TransformerEngine", "library")],
     [],
     "which doc is the canonical recipe for BF16 and FP8 mixed-precision training across H100",
     "docs train amp md bf16 h100 fp8 transformer engine loss scale"),
    # --- 49 ---
    ("Hopper cluster-launch reference in docs/gpu/hopper-clusters.md explains the thread-block clusters and distributed shared memory mechanics used by our grouped-GEMM prototype.", "reference", "technical", False,
     [("docs/gpu/hopper-clusters.md", "file"), ("Hopper", "platform"), ("thread-block clusters", "concept"), ("distributed shared memory", "concept"), ("grouped-GEMM", "algorithm")],
     [("thread-block clusters", "Hopper", "HAS_PART")],
     "which internal reference covers Hopper thread-block clusters and distributed shared memory",
     "hopper thread block cluster distributed shared memory grouped gemm docs"),
    # --- 50 ---
    ("cuBLASLt epilogue fusion handles bias and GELU inside the GEMM call itself on Ampere and newer; the standalone activation kernel we used to launch after every linear got deleted.", "architecture", "technical", False,
     [("cuBLASLt", "library"), ("epilogue fusion", "pattern"), ("GELU", "algorithm"), ("Ampere", "platform"), ("GEMM", "algorithm")],
     [("cuBLASLt", "epilogue fusion", "HAS_PART"), ("epilogue fusion", "GEMM", "APPLIES_TO")],
     "which library feature lets Ampere collapse post-linear activations into the matmul call itself",
     "cublaslt epilogue fusion ampere activation post linear matmul"),
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
