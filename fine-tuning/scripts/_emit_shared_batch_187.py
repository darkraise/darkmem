"""One-off emitter for shared-base batch-187 — technical domain (WebGL and WebGPU: WGSL, Three.js, Babylon.js, bind groups, compute shaders, wgpu-rs, Dawn, ANGLE, native parity).

Writes 50 rows to data/v2/shared/batch_187.tmp.jsonl with ids shared-09301..09350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_187.tmp.jsonl"
ID_OFFSET = 9300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Ported the voxel renderer from WebGL 2.0 to WebGPU; bind groups replaced the flat uniform-location slots and the draw-call budget tripled on Chrome 121 without touching geometry LOD.", "milestone", "technical", False,
     [("WebGL 2.0", "api"), ("WebGPU", "api"), ("bind groups", "concept"), ("Chrome", "platform")],
     [("WebGPU", "WebGL 2.0", "REPLACES")],
     "which graphics API swap tripled the voxel renderer draw-call budget on modern Chrome",
     "webgpu webgl voxel renderer bind group draw call budget chrome"),
    # --- 2 ---
    ("Picked wgpu-rs over Dawn for the native backend; the Rust ergonomics and out-of-the-box Vulkan/Metal/DX12 coverage made the cross-platform story cleaner than maintaining a C++ submodule.", "decision", "technical", False,
     [("wgpu-rs", "library"), ("Dawn", "library"), ("Vulkan", "api"), ("Metal", "api"), ("DX12", "api")],
     [("wgpu-rs", "Dawn", "PREFERS")],
     "which native WebGPU implementation won the backend bake-off and what drove the choice over the Google alternative",
     "wgpu rs dawn native backend vulkan metal dx12 rust cross platform"),
    # --- 3 ---
    ("WGSL replaced the authored GLSL shader library for the editor preview; the SPIR-V round-trip via Tint exposed two type-promotion bugs that had been silently costing us one fragment per triangle.", "problem", "technical", False,
     [("WGSL", "language"), ("GLSL", "language"), ("SPIR-V", "language"), ("Tint", "tool")],
     [("WGSL", "GLSL", "REPLACES")],
     "which shader language swap in the editor preview surfaced latent type-promotion bugs via the intermediate compiler",
     "wgsl glsl spir v tint shader editor type promotion bug fragment"),
    # --- 4 ---
    ("Three.js powers the product configurator; the BatchedMesh addition in r160 collapsed the thousand-draw hero scene into a single indirect draw and the first-paint dropped by 340 ms.", "milestone", "technical", False,
     [("Three.js", "library"), ("BatchedMesh", "api"), ("r160", "date")],
     [("BatchedMesh", "Three.js", "HAS_PART")],
     "which Three.js feature in its early 160s release consolidated the configurator scene into one draw call",
     "three js batched mesh r160 configurator indirect draw first paint"),
    # --- 5 ---
    ("Babylon.js 7 ships a WebGPU engine alongside the WebGL2 one; the shared scene graph means we flip backends with a single constructor flag and keep the same asset pipeline end-to-end.", "fact", "technical", False,
     [("Babylon.js", "library"), ("WebGPU", "api"), ("WebGL2", "api"), ("scene graph", "concept")],
     [("Babylon.js", "WebGPU", "SUPPORTS"), ("Babylon.js", "WebGL2", "SUPPORTS")],
     "how does the seventh Babylon release let an app flip between the two browser graphics backends without rewriting assets",
     "babylon js webgpu webgl2 engine scene graph backend flag asset"),
    # --- 6 ---
    ("PlayCanvas stays on WebGL2 for the ad-network embed target; enterprise analytics ran the numbers and WebGPU coverage below sixty percent of weekly actives made the switch premature.", "decision", "technical", False,
     [("PlayCanvas", "framework"), ("WebGL2", "api"), ("WebGPU", "api")],
     [("WebGL2", "WebGPU", "PREFERS")],
     "why did the ad-network embed keep PlayCanvas on the older graphics API despite the newer one being available",
     "playcanvas webgl2 webgpu embed ad network coverage weekly actives"),
    # --- 7 ---
    ("regl abstracts the WebGL2RenderingContext for the data-viz prototypes; the command-captures model lets Deck.gl layers compose without each library reaching for the raw context and clobbering state.", "architecture", "technical", False,
     [("regl", "library"), ("WebGL2RenderingContext", "api"), ("Deck.gl", "library")],
     [("regl", "WebGL2RenderingContext", "USES"), ("Deck.gl", "regl", "DEPENDS_ON")],
     "which wrapper around the raw browser graphics context lets multiple data-viz layers cooperate without trampling state",
     "regl webgl2 rendering context deck gl command capture state data viz"),
    # --- 8 ---
    ("twgl fills in for the boilerplate-heavy parts of the WebGL2RenderingContext API; uniform-block setup and vertex-array construction that used to be fifty lines of glue now fit in five.", "fact", "technical", False,
     [("twgl", "library"), ("WebGL2RenderingContext", "api"), ("uniform-block", "concept"), ("vertex-array", "concept")],
     [("twgl", "WebGL2RenderingContext", "USES")],
     "which small helper library shrinks the uniform-block and vertex-array setup boilerplate for the raw browser API",
     "twgl webgl2 uniform block vertex array boilerplate helper library"),
    # --- 9 ---
    ("Render pipelines in WebGPU are immutable: the project baked 47 pipeline variants at load and the hot path swaps them with setPipeline rather than patching state between draws.", "architecture", "technical", False,
     [("Render pipelines", "concept"), ("WebGPU", "api"), ("setPipeline", "api")],
     [("Render pipelines", "WebGPU", "IS_A")],
     "how does the renderer handle the immutable-pipeline constraint of the newer browser graphics API at draw time",
     "render pipeline webgpu immutable bake variant set pipeline swap draw"),
    # --- 10. noise ---
    ("The office pinball machine is stuck on free-play mode and someone taped a hand-written rule sheet to the glass.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Bind groups are laid out in four frequencies: per-frame, per-pass, per-material, per-draw; swapping only the highest-frequency group on repeat draws keeps the validation cost under control.", "architecture", "technical", False,
     [("Bind groups", "concept"), ("per-frame", "pattern"), ("per-material", "pattern"), ("per-draw", "pattern")],
     [("Bind groups", "per-frame", "HAS_PART")],
     "which four-level frequency partition does the engine use for resource binding across the frame",
     "bind group frequency per frame pass material draw swap validation"),
    # --- 12 ---
    ("Compute shaders handle the particle simulation on WebGPU; a single storage buffer carries position, velocity, and lifetime and the workgroup size of 64 matched the M2's execution width cleanly.", "architecture", "technical", False,
     [("Compute shaders", "concept"), ("WebGPU", "api"), ("storage buffer", "concept"), ("workgroup", "concept"), ("M2", "platform")],
     [("Compute shaders", "storage buffer", "USES")],
     "which shader stage and buffer type does the particle sim use and why is the workgroup size tuned to Apple silicon",
     "compute shader webgpu storage buffer particle workgroup 64 m2 apple"),
    # --- 13 ---
    ("Uniform buffers got a 16-byte-alignment audit after a WGSL struct mismatch silently zeroed the roughness field on Intel iGPUs; std140-style padding rules now live in a codegen step.", "problem", "technical", False,
     [("Uniform buffers", "concept"), ("WGSL", "language"), ("Intel iGPU", "platform"), ("std140", "pattern")],
     [("std140", "Uniform buffers", "APPLIES_TO")],
     "which alignment oversight silently zeroed a material field on integrated GPUs and how did codegen plug the gap",
     "uniform buffer alignment 16 byte wgsl struct intel igpu std140 pad"),
    # --- 14 ---
    ("MSAA is fixed at 4x on desktop and disabled on mobile; the resolve step is folded into the post-process pass so we don't pay the bandwidth for a separate blit on tile-based GPUs.", "decision", "technical", False,
     [("MSAA", "concept"), ("post-process pass", "pattern"), ("tile-based GPU", "platform")],
     [("MSAA", "post-process pass", "APPLIES_TO")],
     "which anti-aliasing setup does the renderer use and how does it avoid extra bandwidth on mobile tile architectures",
     "msaa 4x desktop mobile resolve post process tile based gpu bandwidth"),
    # --- 15 ---
    ("MRT in the deferred path writes albedo, normal-roughness, and motion vectors into three RGBA16F targets; a fourth 8-bit channel carries material id packed into the alpha of the normal target.", "architecture", "technical", False,
     [("MRT", "concept"), ("deferred path", "pattern"), ("RGBA16F", "concept"), ("material id", "concept")],
     [("MRT", "deferred path", "APPLIES_TO")],
     "which multi-render-target layout does the deferred renderer use and where does the material id live",
     "mrt deferred albedo normal roughness motion rgba16f material id pack"),
    # --- 16 ---
    ("GPU timing queries land in a ring buffer and resolve two frames late so the readback never stalls the submission thread; the profiler UI averages over a sixty-frame window for stability.", "architecture", "technical", False,
     [("GPU timing queries", "concept"), ("ring buffer", "pattern"), ("readback", "concept"), ("profiler", "tool")],
     [("GPU timing queries", "ring buffer", "USES")],
     "how does the engine collect per-pass GPU timings without stalling submission and how does the UI smooth the numbers",
     "gpu timing query ring buffer readback stall profiler frame window"),
    # --- 17 ---
    ("CanvasKit renders the 2D UI layer over the WebGPU scene; Skia's shader compiler outputs SkSL that gets cross-compiled to WGSL through a thin Tint invocation in the build step.", "architecture", "technical", False,
     [("CanvasKit", "library"), ("WebGPU", "api"), ("Skia", "library"), ("SkSL", "language"), ("WGSL", "language"), ("Tint", "tool")],
     [("CanvasKit", "WebGPU", "DEPLOYED_ON"), ("SkSL", "WGSL", "APPLIES_TO")],
     "how does the 2D UI layer reach the browser graphics backend and which shader cross-compilation step sits in the build",
     "canvaskit webgpu skia sksl wgsl tint cross compile ui 2d layer"),
    # --- 18 ---
    ("ANGLE sits between our desktop build's WebGL calls and the host's D3D11 or Metal driver; the shader translator's GLSL-to-HLSL path hid a varying-packing bug we only saw on Windows 11 laptops.", "problem", "technical", False,
     [("ANGLE", "library"), ("WebGL", "api"), ("D3D11", "api"), ("GLSL", "language"), ("HLSL", "language"), ("Windows 11", "platform")],
     [("ANGLE", "D3D11", "COMMUNICATES_WITH")],
     "which translation layer routes browser GL calls to native drivers and where did a shader conversion bug show up",
     "angle webgl d3d11 metal glsl hlsl varying packing windows 11 shader"),
    # --- 19 ---
    ("Dawn powers the Electron shell for the offline editor; matching the Chromium release cadence kept native/WebGPU parity tight and avoided the WGSL dialect drift we saw with stale branches.", "decision", "technical", False,
     [("Dawn", "library"), ("Electron", "framework"), ("Chromium", "platform"), ("WebGPU", "api"), ("WGSL", "language")],
     [("Dawn", "Chromium", "DEPENDS_ON")],
     "which native graphics runtime does the offline Electron editor use and what drove the release-cadence pin",
     "dawn electron chromium webgpu wgsl parity offline editor cadence"),
    # --- 20 ---
    ("Deck.gl 9 moved to a luma.gl core that abstracts over both WebGL2 and WebGPU; a single Layer implementation now picks the right backend based on the adapter returned by navigator.gpu.", "milestone", "technical", False,
     [("Deck.gl", "library"), ("luma.gl", "library"), ("WebGL2", "api"), ("WebGPU", "api"), ("navigator.gpu", "api")],
     [("Deck.gl", "luma.gl", "DEPENDS_ON"), ("luma.gl", "WebGPU", "SUPPORTS")],
     "which library core lets the data-viz framework target either browser graphics API from a single layer implementation",
     "deck gl luma gl webgl2 webgpu adapter navigator gpu layer"),
    # --- 21 ---
    ("Shader hot-reload uses a WGSL source watcher in dev mode; a file change triggers a new createShaderModule, pipeline recreate, and cache eviction, all on the worker so the main thread never blocks.", "fact", "technical", False,
     [("WGSL", "language"), ("createShaderModule", "api"), ("pipeline", "concept"), ("worker", "concept")],
     [("createShaderModule", "WGSL", "USES")],
     "how does shader hot-reload rebuild the pipeline after an edit without blocking the browser main thread",
     "wgsl hot reload create shader module pipeline cache worker main thread"),
    # --- 22 ---
    ("Picked WebGPU's render bundle API for the terrain chunks; recording once and replaying across frames dropped JS overhead by 41 percent on the Intel UHD integrated GPU target.", "decision", "technical", False,
     [("WebGPU", "api"), ("render bundle", "api"), ("terrain chunks", "concept"), ("Intel UHD", "platform")],
     [("render bundle", "WebGPU", "HAS_PART")],
     "which recording-and-replay feature of the newer browser graphics API cut JS overhead for terrain chunks on integrated graphics",
     "webgpu render bundle terrain chunk intel uhd js overhead replay"),
    # --- 23 ---
    ("WebGL 1.0 survives only in the legacy embed path for pre-2020 browsers; extensions like OES_texture_float are optional there and the fallback quietly downgrades shadows to a hard step.", "architecture", "technical", False,
     [("WebGL 1.0", "api"), ("OES_texture_float", "api"), ("legacy embed", "project")],
     [("OES_texture_float", "WebGL 1.0", "EXTENDS")],
     "which legacy browser graphics API still lives in the old embed path and how does it degrade when float textures are missing",
     "webgl 1 0 oes texture float legacy embed shadow fallback downgrade"),
    # --- 24 ---
    ("Storage buffers let compute shaders write back into the scene; a single round-trip readback per animation step got replaced by a GPU-side ring that the render pass samples directly.", "problem", "technical", False,
     [("Storage buffers", "concept"), ("compute shaders", "concept"), ("readback", "concept"), ("render pass", "concept")],
     [("Storage buffers", "readback", "REPLACES")],
     "which GPU-resident data flow retired the per-step readback between compute and render stages",
     "storage buffer compute readback ring render pass round trip sample"),
    # --- 25 ---
    ("Adopted SPIR-V as the archive format for offline shader compilation; glslang produces SPIR-V once and naga transpiles to WGSL, MSL, or HLSL at engine load depending on the platform.", "architecture", "technical", False,
     [("SPIR-V", "language"), ("glslang", "tool"), ("naga", "tool"), ("WGSL", "language"), ("MSL", "language"), ("HLSL", "language")],
     [("naga", "SPIR-V", "USES"), ("glslang", "SPIR-V", "PRODUCES")],
     "which intermediate representation holds the offline shader archive and what pair of tools bookend the pipeline",
     "spir v glslang naga wgsl msl hlsl archive offline shader pipeline"),
    # --- 26 ---
    ("Native/WebGPU parity cracks on subgroup ops: Safari's Metal backend supports a different subgroup size than Chrome's Vulkan path, so the bitonic sort compute shader has two workgroup variants.", "problem", "technical", False,
     [("WebGPU", "api"), ("Safari", "platform"), ("Chrome", "platform"), ("subgroup ops", "concept"), ("bitonic sort", "algorithm")],
     [("Safari", "Chrome", "CONTRADICTS")],
     "which compute feature has inconsistent behaviour across browser backends and what duplication did it force on a sort shader",
     "webgpu subgroup safari chrome metal vulkan bitonic sort workgroup"),
    # --- 27 ---
    ("The scene description is GLTF 2.0; a custom KHR_materials_variants extension drives product configuration swaps and both the Three.js and Babylon.js loaders honour it after a small patch we upstreamed.", "fact", "technical", False,
     [("GLTF 2.0", "protocol"), ("KHR_materials_variants", "api"), ("Three.js", "library"), ("Babylon.js", "library")],
     [("Three.js", "KHR_materials_variants", "SUPPORTS"), ("Babylon.js", "KHR_materials_variants", "SUPPORTS")],
     "which scene format and extension drive configurator material swaps and which two runtimes learned to honour it",
     "gltf khr materials variants three js babylon loader configurator"),
    # --- 28 ---
    ("Compute-driven culling runs on the WebGPU path; the CPU frustum pass is gone and the indirect-draw count comes straight out of the cull compute, saving a command-encoder round trip per view.", "architecture", "technical", False,
     [("Compute-driven culling", "pattern"), ("WebGPU", "api"), ("indirect-draw", "concept"), ("command-encoder", "api")],
     [("Compute-driven culling", "WebGPU", "DEPLOYED_ON")],
     "which culling architecture replaced the CPU frustum pass and what round trip did it save per view",
     "compute culling webgpu indirect draw command encoder cpu frustum"),
    # --- 29 ---
    ("Dropped per-frame pipeline layout creation after the profiler showed it costing 0.6 ms on Firefox Nightly; layouts are cached keyed by a canonical bind-group-layout hash at pipeline build time.", "problem", "technical", False,
     [("pipeline layout", "concept"), ("Firefox Nightly", "platform"), ("bind-group-layout", "concept"), ("profiler", "tool")],
     [("bind-group-layout", "pipeline layout", "APPLIES_TO")],
     "which per-frame allocation showed up in the profiler on a pre-release browser and how did the cache key resolve it",
     "pipeline layout firefox nightly bind group hash cache per frame 0 6 ms"),
    # --- 30 ---
    ("regl's command caching conflicted with Deck.gl's state restoration in the mixed dashboard; we pinned regl to a dedicated offscreen canvas and composited the result via a transparent overlay.", "problem", "technical", False,
     [("regl", "library"), ("Deck.gl", "library"), ("offscreen canvas", "concept"), ("dashboard", "project")],
     [("regl", "offscreen canvas", "DEPLOYED_ON")],
     "which state-collision between two viz libraries forced a canvas isolation workaround in the mixed dashboard",
     "regl deck gl offscreen canvas state restore dashboard overlay conflict"),
    # --- 31 ---
    ("Picked WGSL for the node-graph shader editor output; the reflection info from the Tint parse surface binding names cleanly, which let the editor autogenerate the parameter UI without a hand-written schema.", "decision", "technical", False,
     [("WGSL", "language"), ("Tint", "tool"), ("node-graph shader editor", "project")],
     [("Tint", "WGSL", "USES")],
     "which shader language and parser pairing feeds the node-graph editor's auto-generated parameter UI",
     "wgsl tint node graph shader editor reflection binding parameter ui"),
    # --- 32 ---
    ("Three.js's WebGPURenderer needs a one-liner init flag for linear workflow on Safari; missing it yields sRGB-squared output and designers spent a week chasing a gamma ghost until we documented it.", "problem", "technical", False,
     [("Three.js", "library"), ("WebGPURenderer", "api"), ("Safari", "platform"), ("sRGB", "concept")],
     [("WebGPURenderer", "Three.js", "HAS_PART")],
     "which colour-space gotcha in the Three.js WebGPU renderer cost the team a week of gamma debugging on Safari",
     "three js webgpu renderer safari srgb linear gamma workflow flag"),
    # --- 33 ---
    ("Babylon.js's Node Material Editor still targets GLSL under the hood; the WGSL backend generates equivalent code but the editor preview shows the GLSL source by default for familiarity.", "fact", "technical", False,
     [("Babylon.js", "library"), ("Node Material Editor", "tool"), ("GLSL", "language"), ("WGSL", "language")],
     [("Node Material Editor", "GLSL", "PRODUCES")],
     "which shader source does the Babylon node material editor show by default and which backend compiles the same graph for WebGPU",
     "babylon node material editor glsl wgsl backend preview source"),
    # --- 34 ---
    ("PlayCanvas tags its Engine v2 WebGPU support as experimental; the editor still bakes lightmaps through the WebGL2 renderer because the compute-shader path hasn't landed in the public asset server.", "fact", "technical", False,
     [("PlayCanvas", "framework"), ("Engine v2", "date"), ("WebGPU", "api"), ("WebGL2", "api"), ("compute-shader", "concept")],
     [("PlayCanvas", "WebGL2", "USES")],
     "why does the PlayCanvas editor still use the older graphics API for lightmap baking even as it experiments with the newer one",
     "playcanvas engine v2 webgpu webgl2 lightmap bake compute shader"),
    # --- 35 ---
    ("Swapchain format is bgra8unorm-srgb on the desktop build but rgba16float on the HDR path; the post-process chain branches on the color attachment format to insert or skip the tonemap at the end.", "architecture", "technical", False,
     [("Swapchain", "concept"), ("bgra8unorm-srgb", "config"), ("rgba16float", "config"), ("tonemap", "pattern")],
     [("rgba16float", "tonemap", "APPLIES_TO")],
     "which two swapchain formats does the build use and where does the tonemap live in the post-process chain",
     "swapchain bgra8unorm srgb rgba16float hdr tonemap post process branch"),
    # --- 36 ---
    ("Command encoders are pooled per frame with a generation counter; submit hands off ownership to the queue and the encoder returns to the pool on the next frame's begin, avoiding per-frame allocation.", "architecture", "technical", False,
     [("Command encoders", "api"), ("generation counter", "pattern"), ("queue", "concept")],
     [("Command encoders", "queue", "COMMUNICATES_WITH")],
     "which pooling pattern keeps command-encoder allocations off the hot path without risking stale reuse",
     "command encoder pool generation counter queue submit frame allocation"),
    # --- 37 ---
    ("Texture uploads use writeTexture instead of the older copyExternalImageToTexture for mipmapped assets; the mip chain is generated in a compute pass rather than trusting the browser's synthesis path.", "decision", "technical", False,
     [("writeTexture", "api"), ("copyExternalImageToTexture", "api"), ("mip chain", "concept"), ("compute pass", "concept")],
     [("writeTexture", "copyExternalImageToTexture", "REPLACES")],
     "which upload path and mip-generation approach does the asset pipeline use instead of the browser synthesis path",
     "write texture copy external image mip chain compute pass browser"),
    # --- 38 ---
    ("Deck.gl's GeoJsonLayer crashed on Android Chrome with a WebGPU adapter loss; the root cause was a storage-buffer size that nudged past the adapter limit, and a chunked upload path fixed it.", "problem", "technical", False,
     [("Deck.gl", "library"), ("GeoJsonLayer", "api"), ("Android Chrome", "platform"), ("WebGPU", "api"), ("adapter", "concept")],
     [("GeoJsonLayer", "Deck.gl", "HAS_PART")],
     "which data-viz layer hit an adapter-loss crash on mobile Chrome with WebGPU and what upload pattern stabilised it",
     "deck gl geo json layer android chrome webgpu adapter loss chunk upload"),
    # --- 39 ---
    ("Native parity test suite runs the same WGSL snapshots through Dawn, wgpu-rs, and the Chrome-shipped Tint; a reference-image diff flags any backend that drifts beyond one percent pixel delta.", "fact", "technical", False,
     [("WGSL", "language"), ("Dawn", "library"), ("wgpu-rs", "library"), ("Tint", "tool"), ("Chrome", "platform")],
     [("Dawn", "Tint", "USES"), ("wgpu-rs", "Tint", "USES")],
     "which cross-backend snapshot suite catches WGSL drift between native and browser graphics runtimes",
     "wgsl dawn wgpu rs tint chrome snapshot reference image diff parity"),
    # --- 40 ---
    ("Picked bind-group-layout reflection over a hand-authored binding table; the WGSL-first workflow means adding a sampler takes one line in the shader and the JS side picks it up through the reflection API.", "decision", "technical", False,
     [("bind-group-layout", "concept"), ("WGSL", "language"), ("sampler", "concept"), ("reflection API", "api")],
     [("bind-group-layout", "WGSL", "DEPENDS_ON")],
     "which authoring workflow replaced the hand-written binding table once shader-first became the default",
     "bind group layout reflection wgsl sampler binding table hand author"),
    # --- 41 ---
    ("Milestone: first full frame under 4 ms on WebGPU for the indoor scene on an M1 Air; compute-culling plus render bundles plus a single-queue submission shaved 2.6 ms off the previous baseline.", "milestone", "technical", False,
     [("WebGPU", "api"), ("M1 Air", "platform"), ("compute-culling", "pattern"), ("render bundles", "api"), ("single-queue submission", "pattern")],
     [("compute-culling", "WebGPU", "DEPLOYED_ON")],
     "which combination of techniques first drove the indoor scene under four milliseconds on Apple silicon",
     "webgpu m1 air compute culling render bundle single queue indoor 4 ms"),
    # --- 42 ---
    ("Query sets for timestamp writes are pinned to the primary queue only; multi-queue submission tripped a Chrome validation warning when a query set was shared across queues, and the fix was keeping it single-queue.", "problem", "technical", False,
     [("Query sets", "concept"), ("timestamp writes", "api"), ("primary queue", "concept"), ("Chrome", "platform")],
     [("Query sets", "primary queue", "APPLIES_TO")],
     "which validation warning on cross-queue query sets forced the timing infrastructure back to a single queue",
     "query set timestamp write primary queue chrome validation multi queue"),
    # --- 43. noise ---
    ("The lobby bonsai tree has been slowly dying and three engineers keep rotating unsolicited watering advice.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Reference implementation for tonemap is ACES Filmic as a WGSL function; an earlier Reinhard pass clipped highlights on bright product shots and the switch was settled after a shootout in the review build.", "reference", "technical", False,
     [("ACES Filmic", "algorithm"), ("WGSL", "language"), ("Reinhard", "algorithm"), ("tonemap", "pattern")],
     [("ACES Filmic", "Reinhard", "REPLACES")],
     "which filmic tonemap reference replaced the simpler operator after highlight clipping on product shots",
     "aces filmic wgsl reinhard tonemap highlight clip product shot"),
    # --- 45 ---
    ("Reference: the WebGPU explainer's canonical bind-group frequency split is the north star for our resource layout; any deviation from the per-frame/pass/material/draw quartet needs an architecture note.", "reference", "technical", False,
     [("WebGPU explainer", "publication"), ("bind-group", "concept"), ("per-frame/pass/material/draw", "pattern")],
     [("bind-group", "WebGPU explainer", "PUBLISHED_IN")],
     "which canonical document sets the bind-group frequency model the engine is expected to follow",
     "webgpu explainer bind group frequency per frame pass material draw north star"),
    # --- 46 ---
    ("Prefer WGSL attribute-based entry points over legacy vertex_main/fragment_main naming conventions; the @vertex and @fragment decorators make shader reflection less fragile when a function gets renamed.", "preference", "technical", False,
     [("WGSL", "language"), ("@vertex", "api"), ("@fragment", "api"), ("shader reflection", "concept")],
     [("@vertex", "WGSL", "IS_A")],
     "which WGSL entry-point style does the team prefer and which brittleness does the older naming convention introduce",
     "wgsl vertex fragment attribute entry point reflection rename brittle"),
    # --- 47 ---
    ("Prefer the wgpu-rs typed BufferUsages flags to raw integer constants in the native build; the compile-time check caught three cases where STORAGE was missing from a buffer used in a compute shader.", "preference", "technical", False,
     [("wgpu-rs", "library"), ("BufferUsages", "api"), ("STORAGE", "config"), ("compute shader", "concept")],
     [("BufferUsages", "wgpu-rs", "HAS_PART")],
     "which typed-flag preference in the native WebGPU binding caught missing storage usages on compute buffers at compile time",
     "wgpu rs buffer usages storage compute shader flag typed compile time"),
    # --- 48 ---
    ("Prefer Three.js's WebGPURenderer over a manual WebGPU integration for the marketing site; the asset-loader ergonomics win, even though the raw API gives more headroom for the product viewer team.", "preference", "technical", False,
     [("Three.js", "library"), ("WebGPURenderer", "api"), ("WebGPU", "api"), ("marketing site", "project")],
     [("WebGPURenderer", "WebGPU", "USES")],
     "which rendering choice does the team prefer for the marketing site even though raw access offers more headroom",
     "three js webgpu renderer marketing site manual integration asset loader"),
    # --- 49 ---
    ("Reference profile of Deck.gl versus a hand-rolled WebGPU pipeline for the mapping demo: the library wins on time-to-first-frame while the bespoke pipeline wins on sustained fps once the scene warms.", "reference", "technical", False,
     [("Deck.gl", "library"), ("WebGPU", "api"), ("mapping demo", "project")],
     [("Deck.gl", "WebGPU", "USES")],
     "which benchmark compared the viz library against a bespoke browser graphics pipeline and what did each win",
     "deck gl webgpu mapping demo first frame sustained fps bespoke pipeline"),
    # --- 50 ---
    ("Reference: the W3C WebGPU spec's error-scope section is the authoritative source for how the engine handles validation and out-of-memory scopes; any handler change gets cross-checked against the spec before merge.", "reference", "technical", False,
     [("W3C WebGPU spec", "publication"), ("error-scope", "concept"), ("validation", "concept"), ("out-of-memory", "concept")],
     [("error-scope", "W3C WebGPU spec", "PUBLISHED_IN")],
     "which spec section governs how the engine structures its error handling across validation and memory scopes",
     "w3c webgpu spec error scope validation out of memory handler"),
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
