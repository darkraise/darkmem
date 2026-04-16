"""One-off emitter for shared-base batch-188 — technical domain (low-level graphics APIs: Vulkan, DirectX 12, Metal 3, WebGPU, command buffers, pipelines, descriptors, barriers, mesh shaders, DirectStorage, RenderDoc, PIX).

Writes 50 rows to data/v2/shared/batch_188.tmp.jsonl with ids shared-09351..09400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_188.tmp.jsonl"
ID_OFFSET = 9350

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Ported the renderer from OpenGL to Vulkan so the studio finally controls command buffer submission explicitly; the driver-hidden state that OpenGL kept papering over stopped biting profile builds on Linux.", "decision", "technical", False,
     [("OpenGL", "technology"), ("Vulkan", "technology"), ("command buffer", "concept"), ("Linux", "platform")],
     [("Vulkan", "OpenGL", "REPLACES")],
     "which graphics API did the renderer move to for explicit command submission and which host platform benefited",
     "vulkan opengl command buffer linux explicit driver state port"),
    # --- 2 ---
    ("Pipeline state objects are hashed by a 128-bit xxhash of the blend, raster, depth, and shader bytecode so compiled PSOs survive across runs through a disk cache keyed by that hash.", "decision", "technical", False,
     [("Pipeline state object", "concept"), ("xxhash", "algorithm"), ("PSO", "concept"), ("disk cache", "pattern")],
     [("PSO", "disk cache", "APPLIES_TO")],
     "how does the engine persist compiled pipeline state objects across runs and what identifier keys the cache",
     "pipeline state object xxhash psoo disk cache hash persist"),
    # --- 3 ---
    ("DirectX 12 descriptor heaps are split into one large CBV_SRV_UAV heap per frame-in-flight and a single sampler heap shared across the whole process; ring-allocated tables sit inside the per-frame heap.", "architecture", "technical", False,
     [("DirectX 12", "technology"), ("CBV_SRV_UAV heap", "concept"), ("sampler heap", "concept"), ("frame-in-flight", "pattern")],
     [("CBV_SRV_UAV heap", "frame-in-flight", "APPLIES_TO")],
     "how is the descriptor heap layout split between per-frame resources and samplers on the DX12 backend",
     "directx 12 descriptor heap cbv srv uav sampler frame in flight ring"),
    # --- 4 ---
    ("Timeline semaphores replaced the old binary semaphore plus fence pair for queue synchronisation; monotonic values across queues made cross-queue waits trivial and retired a swarm of ad-hoc wait lists.", "decision", "technical", False,
     [("Timeline semaphores", "concept"), ("binary semaphore", "concept"), ("fence", "concept"), ("queue", "concept")],
     [("Timeline semaphores", "binary semaphore", "REPLACES")],
     "which Vulkan synchronisation primitive replaced binary semaphore plus fence pairs for cross-queue waits",
     "timeline semaphore binary fence queue sync monotonic cross wait"),
    # --- 5 ---
    ("Moved bindless descriptors in on the AAA backend: a single 1M-entry SRV table holds every texture, and shaders index it by a 32-bit handle rather than binding per draw.", "milestone", "technical", False,
     [("bindless descriptors", "concept"), ("SRV table", "concept"), ("texture", "concept")],
     [("bindless descriptors", "SRV table", "USES")],
     "how does the bindless path index into a million-entry SRV table instead of binding textures per draw",
     "bindless descriptor srv table texture handle shader index draw"),
    # --- 6 ---
    ("Vulkan 1.3 dynamic rendering retired most of our VkRenderPass plumbing; attachments are declared per command buffer with vkCmdBeginRendering and no subpass object survives in hot paths.", "architecture", "technical", False,
     [("Vulkan 1.3", "technology"), ("dynamic rendering", "concept"), ("VkRenderPass", "api"), ("vkCmdBeginRendering", "api"), ("subpass", "concept")],
     [("dynamic rendering", "VkRenderPass", "REPLACES")],
     "which Vulkan 1.3 feature replaced VkRenderPass plumbing and how are attachments declared now",
     "vulkan 1 3 dynamic rendering renderpass subpass vkcmdbeginrendering attachment"),
    # --- 7 ---
    ("Pipeline barriers are batched with VK_KHR_synchronization2; a single vkCmdPipelineBarrier2 per stage transition replaced the scattered pre- and post-pass barriers and cut validation-layer noise by half.", "decision", "technical", False,
     [("VK_KHR_synchronization2", "api"), ("vkCmdPipelineBarrier2", "api"), ("Pipeline barriers", "concept"), ("validation-layer", "tool")],
     [("VK_KHR_synchronization2", "Pipeline barriers", "IMPROVES_ON")],
     "which Vulkan extension consolidated pipeline barriers and how did it change validation layer noise",
     "vulkan synchronization2 pipeline barrier vkcmdpipelinebarrier2 validation noise"),
    # --- 8 ---
    ("Metal 3 argument buffers replaced our per-draw descriptor rebind on the Apple Silicon backend; a single persistent encoder references a Tier 2 argument buffer holding thousands of resource handles.", "architecture", "technical", False,
     [("Metal 3", "technology"), ("argument buffers", "concept"), ("Apple Silicon", "platform"), ("Tier 2", "config")],
     [("argument buffers", "Metal 3", "APPLIES_TO")],
     "which Metal 3 resource binding model replaced per-draw descriptor rebinds on Apple Silicon",
     "metal 3 argument buffer apple silicon tier 2 descriptor rebind"),
    # --- 9 ---
    ("MoltenVK wraps Vulkan calls onto Metal for the macOS port; most of the code path stays shared with the Linux and Windows Vulkan backends but MSL-only quirks like lack of geometry shaders shape a few shaders.", "architecture", "technical", False,
     [("MoltenVK", "library"), ("Vulkan", "technology"), ("Metal", "technology"), ("macOS", "platform"), ("MSL", "language"), ("geometry shaders", "concept")],
     [("MoltenVK", "Vulkan", "APPLIES_TO")],
     "how does the macOS port reuse the Vulkan backend and which MSL limitation shapes specific shaders",
     "moltenvk vulkan metal macos msl geometry shader port share"),
    # --- 10. noise ---
    ("The office espresso machine hissed through the afternoon stand-up and nobody wanted to be the one to refill the beans again.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("bgfx is the thin render backend for the mobile demo: a single draw-call API hides GLES, Vulkan, and Metal differences while letting the tool pipeline compile shaders once into bin blobs.", "decision", "technical", False,
     [("bgfx", "library"), ("GLES", "technology"), ("Vulkan", "technology"), ("Metal", "technology"), ("mobile demo", "project")],
     [("bgfx", "mobile demo", "APPLIES_TO")],
     "which render abstraction hides GLES, Vulkan, and Metal differences on the mobile demo backend",
     "bgfx gles vulkan metal mobile demo draw call abstract shader bin"),
    # --- 12 ---
    ("Swapped The Forge in as the baseline renderer for the cross-platform research branch; its already-unified descriptor model across Vulkan and DirectX 12 spared us a custom abstraction we'd have had to maintain.", "decision", "technical", False,
     [("The Forge", "framework"), ("Vulkan", "technology"), ("DirectX 12", "technology"), ("research branch", "project")],
     [("The Forge", "research branch", "APPLIES_TO")],
     "which cross-platform renderer became the baseline for the research branch and what did it save us from",
     "the forge vulkan directx 12 research branch descriptor abstract"),
    # --- 13 ---
    ("Diligent Engine drives the editor viewport because its GL fallback on ancient machines stays usable while the D3D12 path lights up on the newer artist workstations.", "fact", "technical", False,
     [("Diligent Engine", "framework"), ("GL", "technology"), ("D3D12", "technology"), ("editor viewport", "project")],
     [("Diligent Engine", "editor viewport", "APPLIES_TO")],
     "which rendering engine powers the editor viewport and how does it serve both old and new artist boxes",
     "diligent engine gl d3d12 editor viewport artist workstation fallback"),
    # --- 14 ---
    ("Unity HDRP was ruled out for the console title because its render graph baking cost on mid-gen hardware pushed a full frame over budget during boss transitions; a custom SRP took its place.", "decision", "technical", False,
     [("Unity HDRP", "framework"), ("render graph", "concept"), ("SRP", "framework"), ("console title", "project")],
     [("SRP", "Unity HDRP", "REPLACES")],
     "why did the console title drop Unity HDRP and which render pipeline replaced it",
     "unity hdrp srp render graph console boss frame budget custom"),
    # --- 15 ---
    ("Unreal RHI abstracts Vulkan, DirectX 12, and Metal uniformly so gameplay code stays platform-neutral; platform-specific shader permutations are emitted at cook time by ShaderCompileWorker.", "reference", "technical", False,
     [("Unreal RHI", "framework"), ("Vulkan", "technology"), ("DirectX 12", "technology"), ("Metal", "technology"), ("ShaderCompileWorker", "tool")],
     [("Unreal RHI", "ShaderCompileWorker", "USES")],
     "how does the RHI keep gameplay code platform-neutral while handling platform-specific shader permutations",
     "unreal rhi vulkan directx 12 metal shadercompileworker cook permutation"),
    # --- 16 ---
    ("Command buffer recording is threaded at eight workers; each worker owns a secondary command buffer and the primary command buffer on the render thread records only inheritance plus the final execute-commands call.", "milestone", "technical", False,
     [("secondary command buffer", "concept"), ("primary command buffer", "concept"), ("render thread", "concept"), ("execute-commands", "api")],
     [("secondary command buffer", "primary command buffer", "APPLIES_TO")],
     "how does the renderer parallelise command recording across workers while keeping the primary buffer thin",
     "command buffer secondary primary render thread worker execute inherit"),
    # --- 17 ---
    ("VkDescriptorSet allocation moved to a per-frame pool with reset-pool on frame retire; the old free-list-per-type approach fragmented after an hour of play and allocation started failing in the city hub.", "milestone", "technical", False,
     [("VkDescriptorSet", "api"), ("per-frame pool", "pattern"), ("free-list", "pattern"), ("city hub", "place")],
     [("per-frame pool", "free-list", "REPLACES")],
     "which descriptor allocation strategy replaced the free-list and which long-session failure did it fix",
     "vkdescriptorset per frame pool free list fragment city hub reset"),
    # --- 18 ---
    ("Subpass self-dependencies drive the tile-based input attachment reads on Mali hardware; on desktop the same render graph unrolls into separate passes because input attachment benefits disappear.", "fact", "technical", False,
     [("Subpass", "concept"), ("input attachment", "concept"), ("Mali", "platform"), ("render graph", "concept")],
     [("Subpass", "Mali", "APPLIES_TO")],
     "how does the render graph switch between subpass self-dependencies on Mali and unrolled passes on desktop",
     "subpass self dependency input attachment mali tile desktop unroll"),
    # --- 19 ---
    ("Render pass attachments declare load and store ops per attachment so tile-based GPUs can skip untouched writes; the mobile build measured twelve percent bandwidth savings just from auditing store ops.", "milestone", "technical", False,
     [("Render pass", "concept"), ("attachments", "concept"), ("load and store ops", "api"), ("tile-based GPUs", "platform")],
     [("Render pass", "tile-based GPUs", "APPLIES_TO")],
     "which render pass attribute drove the twelve-percent bandwidth win on tile-based mobile GPUs",
     "render pass attachment load store op tile mobile bandwidth saving"),
    # --- 20 ---
    ("GPU-driven rendering moved draw-call emission into a compute dispatch indirect chain: culling writes visible draw args, the indirect buffer feeds vkCmdDrawIndexedIndirectCount, and the CPU stops iterating draw lists entirely.", "milestone", "technical", False,
     [("GPU-driven rendering", "concept"), ("compute dispatch indirect", "concept"), ("vkCmdDrawIndexedIndirectCount", "api"), ("culling", "concept")],
     [("GPU-driven rendering", "compute dispatch indirect", "USES")],
     "how does the GPU-driven path emit draws without CPU iteration and which indirect call consumes the buffer",
     "gpu driven render dispatch indirect vkcmddrawindexed culling argument"),
    # --- 21 ---
    ("Mesh shaders replaced the geometry-shader expansion path for the foliage impostor system on DX12 Ultimate hardware; per-meshlet culling killed three percent of GPU frame time at the overlook.", "milestone", "technical", False,
     [("Mesh shaders", "concept"), ("geometry-shader", "concept"), ("foliage impostor", "pattern"), ("meshlet", "concept"), ("DX12 Ultimate", "technology")],
     [("Mesh shaders", "geometry-shader", "REPLACES")],
     "which shader stage replaced geometry-shader expansion for foliage impostors and what performance did it reclaim",
     "mesh shader meshlet foliage impostor geometry dx12 ultimate cull"),
    # --- 22 ---
    ("Variable-rate shading kicks in on the peripheral tiles outside the gaze cone when eye tracking is active; flat 2x2 rate at the edges buys back enough time for the DLSS pass.", "fact", "technical", False,
     [("Variable-rate shading", "concept"), ("gaze cone", "concept"), ("eye tracking", "concept"), ("DLSS", "technology")],
     [("Variable-rate shading", "DLSS", "APPLIES_TO")],
     "how does variable-rate shading interact with eye tracking and which upscaler gets the reclaimed budget",
     "variable rate shading gaze cone eye tracking dlss periphery tile"),
    # --- 23 ---
    ("DirectStorage 1.2 streams asset bundles straight from NVMe into GPU memory through the DStorage queue; the old CPU staging buffer detour added about forty ms to load-screen hitches.", "decision", "technical", False,
     [("DirectStorage", "technology"), ("NVMe", "technology"), ("DStorage queue", "concept"), ("CPU staging buffer", "pattern")],
     [("DirectStorage", "CPU staging buffer", "REPLACES")],
     "which asset streaming path retired the CPU staging detour and what load-screen latency did it save",
     "directstorage dstorage queue nvme gpu memory cpu staging load"),
    # --- 24 ---
    ("AgilitySDK is pinned at version 1.613 so the game ships with Shader Model 6.7 wave intrinsics and mesh shader fixes without waiting for OS-level D3D12 rollouts; the redistributable sits under D3D12/ in the install.", "fact", "technical", False,
     [("AgilitySDK", "library"), ("Shader Model 6.7", "technology"), ("wave intrinsics", "concept"), ("D3D12", "technology")],
     [("AgilitySDK", "D3D12", "APPLIES_TO")],
     "how does AgilitySDK let the game ship newer D3D12 features without waiting for an OS-level update",
     "agilitysdk shader model 6 7 wave intrinsic d3d12 redist install"),
    # --- 25 ---
    ("RenderDoc captures the gbuffer pass on demand with a keyboard bind; a trimmed capture mode skips the particle pass when frame size would otherwise blow past the one gigabyte cap.", "fact", "technical", False,
     [("RenderDoc", "tool"), ("gbuffer pass", "concept"), ("particle pass", "concept"), ("trimmed capture", "pattern")],
     [("RenderDoc", "gbuffer pass", "APPLIES_TO")],
     "how does the game arm on-demand RenderDoc captures and what keeps the capture size under the cap",
     "renderdoc gbuffer particle trimmed capture bind one gigabyte cap"),
    # --- 26 ---
    ("PIX on Windows is the primary profiler for the DirectX 12 backend; timing captures get committed to the perf regression repo so nightly runs diff against the previous green baseline.", "fact", "technical", False,
     [("PIX", "tool"), ("DirectX 12", "technology"), ("perf regression repo", "project")],
     [("PIX", "DirectX 12", "APPLIES_TO")],
     "which profiler drives the DirectX 12 perf regression workflow and how are captures tracked over time",
     "pix directx 12 profiler perf regression nightly baseline commit"),
    # --- 27 ---
    ("GPU crash on the streaming thread traced to a write-after-read hazard with no VkImageMemoryBarrier between the compute dispatch and the subsequent sampler read; adding an explicit barrier pinned the fix.", "problem", "technical", False,
     [("GPU crash", "concept"), ("write-after-read", "concept"), ("VkImageMemoryBarrier", "api"), ("compute dispatch", "concept")],
     [("VkImageMemoryBarrier", "GPU crash", "FIXES")],
     "which synchronisation hazard caused the streaming-thread GPU crash and which barrier closed it",
     "gpu crash write after read vkimagememorybarrier compute dispatch sample"),
    # --- 28 ---
    ("WebGPU native via wgpu drives the in-browser scene viewer; SPIR-V is cross-compiled to WGSL at build time and the same pipeline layouts run native on desktop when users open the exported scene in the standalone viewer.", "architecture", "technical", False,
     [("WebGPU", "technology"), ("wgpu", "library"), ("SPIR-V", "technology"), ("WGSL", "language"), ("scene viewer", "project")],
     [("wgpu", "WebGPU", "USES"), ("SPIR-V", "WGSL", "REPLACES")],
     "which native WebGPU stack runs the scene viewer and how are SPIR-V shaders routed into WGSL",
     "webgpu wgpu spir v wgsl scene viewer cross compile native"),
    # --- 29 ---
    ("Timeline semaphore values are a 64-bit monotonic counter shared across the async-compute and graphics queues; a waitSemaphoreValues array on submit makes cross-queue barriers explicit and debuggable.", "architecture", "technical", False,
     [("Timeline semaphore", "concept"), ("async-compute", "concept"), ("graphics queue", "concept"), ("waitSemaphoreValues", "api")],
     [("Timeline semaphore", "async-compute", "APPLIES_TO")],
     "how does the renderer coordinate async-compute and graphics queues through shared timeline semaphore values",
     "timeline semaphore async compute graphics queue wait values monotonic"),
    # --- 30 ---
    ("Compute dispatch indirect drives the hierarchical-Z occlusion cull; the dispatch count itself lives in a GPU buffer written by the previous frame's visibility pass so the CPU never learns the value.", "architecture", "technical", False,
     [("Compute dispatch indirect", "concept"), ("hierarchical-Z", "algorithm"), ("occlusion cull", "concept"), ("visibility pass", "concept")],
     [("Compute dispatch indirect", "hierarchical-Z", "USES")],
     "how does hierarchical-Z occlusion culling drive its own dispatch count without CPU readback",
     "compute dispatch indirect hierarchical z occlusion cull visibility gpu"),
    # --- 31 ---
    ("Bindless on the Xbox Series backend uses the SM6.6 ResourceDescriptorHeap directly; the shared HLSL path #ifdefs between that and the DXR-style root descriptor table fallback for older PC GPUs.", "architecture", "technical", False,
     [("Xbox Series", "platform"), ("SM6.6", "technology"), ("ResourceDescriptorHeap", "api"), ("HLSL", "language"), ("root descriptor", "concept")],
     [("ResourceDescriptorHeap", "root descriptor", "REPLACES")],
     "how does the HLSL path toggle between ResourceDescriptorHeap on Xbox Series and the root descriptor fallback",
     "xbox series sm6 6 resourcedescriptorheap hlsl root descriptor bindless"),
    # --- 32 ---
    ("Validation layers were flipping false-positive descriptor-update-after-bind warnings during the first minute of play; the fix was enabling VK_EXT_descriptor_indexing's update-unused-while-pending flag on the bindless set.", "problem", "technical", False,
     [("Validation layers", "tool"), ("VK_EXT_descriptor_indexing", "api"), ("update-unused-while-pending", "config"), ("bindless set", "concept")],
     [("update-unused-while-pending", "Validation layers", "FIXES")],
     "which descriptor-indexing flag silenced the spurious update-after-bind validation warnings on the bindless set",
     "vk ext descriptor indexing update unused while pending bindless validation"),
    # --- 33 ---
    ("Swapchain recreation on resize races against in-flight frames; the fix was a deviceWaitIdle gate plus a versioned swapchain handle so stale render passes bail at begin rather than submit.", "problem", "technical", False,
     [("Swapchain", "concept"), ("deviceWaitIdle", "api"), ("versioned swapchain", "pattern"), ("render passes", "concept")],
     [("deviceWaitIdle", "Swapchain", "FIXES")],
     "which gating plus handle-versioning fixed the swapchain recreation race with in-flight frames",
     "swapchain recreate resize devicewaitidle versioned render pass stale"),
    # --- 34 ---
    ("Prefer Vulkan over DirectX 12 for the shipped Linux and Steam Deck targets; the same backend slots into Windows nicely, so maintaining a dual stack isn't worth the ongoing cost for our team size.", "preference", "technical", False,
     [("Vulkan", "technology"), ("DirectX 12", "technology"), ("Steam Deck", "platform"), ("Windows", "platform")],
     [("Vulkan", "DirectX 12", "PREFERS")],
     "which graphics API does the team prefer as the shipped backend and why is a dual stack rejected",
     "vulkan directx 12 steam deck windows linux prefer dual stack"),
    # --- 35 ---
    ("HLSL is authored as the single source language and cross-compiled to SPIR-V via DXC with -spirv; the old glslang path was retired after waveops-intrinsic coverage lagged on the Vulkan side for half a year.", "decision", "technical", False,
     [("HLSL", "language"), ("SPIR-V", "technology"), ("DXC", "tool"), ("glslang", "tool"), ("waveops", "concept")],
     [("DXC", "glslang", "REPLACES")],
     "which shader toolchain replaced glslang for cross-compiling HLSL into SPIR-V and why",
     "hlsl spir v dxc glslang waveops cross compile vulkan shader"),
    # --- 36 ---
    ("Prefer command-buffer reuse with VK_COMMAND_BUFFER_USAGE_SIMULTANEOUS_USE_BIT off across frames; re-record every frame is simpler than hunting down the aliasing bugs that simultaneous use invites.", "preference", "technical", False,
     [("command-buffer", "concept"), ("VK_COMMAND_BUFFER_USAGE_SIMULTANEOUS_USE_BIT", "api")],
     [],
     "why does the renderer prefer re-recording command buffers each frame over simultaneous-use reuse",
     "command buffer simultaneous use bit re record frame alias prefer"),
    # --- 37 ---
    ("Aftermath hooks into the D3D12 backend for post-crash minidump enrichment; a TDR event now carries the last-executed draw and the shader pdb offset so kernel-timeout crashes actually triage in a morning.", "architecture", "technical", False,
     [("Aftermath", "tool"), ("D3D12", "technology"), ("TDR", "concept"), ("minidump", "concept"), ("shader pdb", "concept")],
     [("Aftermath", "TDR", "APPLIES_TO")],
     "how does Aftermath turn a D3D12 TDR event into actionable triage info with draw and shader context",
     "aftermath d3d12 tdr minidump draw shader pdb kernel timeout"),
    # --- 38 ---
    ("Upload heap is a per-frame ring mapped WRITE_COMBINE; the old per-resource UploadBuffer allocation pattern thrashed the page mapper and showed up as intermittent 14 ms spikes in the trace.", "decision", "technical", False,
     [("Upload heap", "concept"), ("WRITE_COMBINE", "config"), ("UploadBuffer", "pattern"), ("page mapper", "concept")],
     [("Upload heap", "UploadBuffer", "REPLACES")],
     "which upload strategy retired per-resource UploadBuffer allocation and what frametime spike did it eliminate",
     "upload heap ring write combine uploadbuffer page mapper spike"),
    # --- 39 ---
    ("The render graph auto-inserts image layout transitions by tracking last-usage per resource handle; manual vkCmdPipelineBarrier calls in high-level code were banned in the style guide last quarter.", "decision", "technical", False,
     [("render graph", "concept"), ("image layout", "concept"), ("vkCmdPipelineBarrier", "api"), ("style guide", "publication")],
     [("render graph", "vkCmdPipelineBarrier", "REPLACES")],
     "which layer took ownership of image-layout transitions and what coding-style rule enforced the shift",
     "render graph image layout vkcmdpipelinebarrier last usage style guide"),
    # --- 40 ---
    ("Shipped the shader permutation cache milestone: 240k permutations cook in seven minutes on the build farm, down from thirty-eight minutes, thanks to parallel DXC invocations sharded by shader stage.", "milestone", "technical", False,
     [("shader permutation", "concept"), ("DXC", "tool"), ("build farm", "project")],
     [("DXC", "build farm", "APPLIES_TO")],
     "which milestone cut shader permutation cook time from thirty-eight minutes down to seven on the build farm",
     "shader permutation dxc cook build farm parallel shard stage milestone"),
    # --- 41 ---
    ("Query pools for GPU timestamps wrap with a two-frame latency so readback never stalls; the previous synchronous readback pattern dropped the frame rate during the profiler HUD overlay.", "decision", "technical", False,
     [("Query pools", "concept"), ("GPU timestamps", "concept"), ("readback", "concept"), ("profiler HUD", "tool")],
     [("Query pools", "readback", "IMPROVES_ON")],
     "which query-pool latency pattern stopped the profiler HUD from tanking frame rate through sync readback",
     "query pool gpu timestamp readback latency profiler hud sync drop"),
    # --- 42 ---
    ("Rectangle scissor-based VRS tiles are overlaid with a debug heatmap in the dev build; toggling the overlay flushes the pipeline but only fires when someone presses the VRS debug key.", "fact", "technical", False,
     [("scissor", "concept"), ("VRS", "concept"), ("debug heatmap", "tool"), ("dev build", "project")],
     [("VRS", "debug heatmap", "APPLIES_TO")],
     "which debug overlay visualises VRS tile rates and what is the cost of toggling it during development",
     "vrs scissor tile debug heatmap dev build overlay flush pipeline"),
    # --- 43. noise ---
    ("Someone finally cleaned out the mini-fridge in the kitchenette and a mystery yogurt had apparently been composing poetry since 2025.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Prefer a single VkQueue of type GRAPHICS_BIT | COMPUTE_BIT for the desktop backend rather than juggling separate families; async compute moves to a second queue only when profiling proves we're bottlenecked on fixed-function.", "preference", "technical", False,
     [("VkQueue", "api"), ("GRAPHICS_BIT", "config"), ("COMPUTE_BIT", "config"), ("async compute", "concept")],
     [("async compute", "VkQueue", "APPLIES_TO")],
     "why does the desktop backend prefer a single combined queue and when is a second async-compute queue added",
     "vkqueue graphics compute bit async queue desktop profile prefer"),
    # --- 45 ---
    ("Prefer RenderDoc over PIX for day-to-day shader debugging; PIX stays as the profiling workhorse but the frame inspector ergonomics in RenderDoc are better for Vulkan captures.", "preference", "technical", False,
     [("RenderDoc", "tool"), ("PIX", "tool"), ("Vulkan", "technology")],
     [("RenderDoc", "PIX", "PREFERS")],
     "which GPU tool do engineers prefer for Vulkan shader debugging and which role does PIX retain",
     "renderdoc pix shader debug profile vulkan frame inspector prefer"),
    # --- 46 ---
    ("Shader source maps are generated from DXC with -Zi and shipped alongside the pdb so RenderDoc and PIX step through the original HLSL on production builds; the symbol server hosts the pdbs gated behind a VPN.", "reference", "technical", False,
     [("DXC", "tool"), ("Shader source maps", "concept"), ("pdb", "concept"), ("symbol server", "service"), ("VPN", "technology")],
     [("DXC", "pdb", "USES")],
     "how do RenderDoc and PIX step through original HLSL on production builds and where do the pdbs live",
     "dxc zi shader source map pdb symbol server vpn renderdoc step"),
    # --- 47 ---
    ("The Khronos Vulkan 1.3 specification mandates dynamic rendering, sync2, and extended dynamic state as core features; our minimum device requirement was bumped to the 1.3 feature set in the engine readme.", "reference", "technical", False,
     [("Khronos", "publication"), ("Vulkan 1.3", "technology"), ("dynamic rendering", "concept"), ("sync2", "api"), ("extended dynamic state", "concept")],
     [("Khronos", "Vulkan 1.3", "APPLIES_TO")],
     "which Khronos specification defines the 1.3 feature core and which minimum device tier did the engine adopt",
     "khronos vulkan 1 3 specification dynamic rendering sync2 extended state"),
    # --- 48 ---
    ("Microsoft's Direct3D 12 programming guide chapter on resource binding is the reference for our descriptor tables; root signature layout follows its recommended three-table structure with samplers split out.", "reference", "technical", False,
     [("Microsoft", "organization"), ("Direct3D 12", "technology"), ("resource binding", "concept"), ("root signature", "concept"), ("samplers", "concept")],
     [("Microsoft", "Direct3D 12", "APPLIES_TO")],
     "which vendor document anchors the descriptor-table layout and how does the root signature split samplers",
     "microsoft direct3d 12 resource binding root signature sampler reference"),
    # --- 49 ---
    ("The Apple Metal Shading Language specification is the canonical reference for argument-buffer tier limits and the resource visibility rules we consult when the validation layer flags aliasing on iOS devices.", "reference", "technical", False,
     [("Apple", "organization"), ("Metal Shading Language", "language"), ("argument-buffer", "concept"), ("iOS", "platform")],
     [("Apple", "Metal Shading Language", "APPLIES_TO")],
     "which Apple specification resolves argument-buffer tier limits and resource visibility questions on iOS",
     "apple metal shading language argument buffer tier ios visibility"),
    # --- 50 ---
    ("The Vulkan Sample Kit from LunarG hosts the dynamic-rendering and timeline-semaphore examples we pattern our boilerplate on; the repo serves as the onboarding reference for new graphics hires.", "reference", "technical", False,
     [("Vulkan Sample Kit", "publication"), ("LunarG", "organization"), ("dynamic-rendering", "concept"), ("timeline-semaphore", "concept")],
     [("Vulkan Sample Kit", "LunarG", "APPLIES_TO")],
     "which LunarG reference repository anchors the team's dynamic-rendering and timeline-semaphore boilerplate",
     "vulkan sample kit lunarg dynamic rendering timeline semaphore onboard"),
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
