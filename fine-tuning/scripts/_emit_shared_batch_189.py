"""One-off emitter for shared-base batch-189 — technical domain (ray tracing and real-time rendering: OptiX, Embree, Radeon Rays, DXR, KHR_ray_tracing, Metal Raytracing, RTXDI, ReSTIR, RTXGI, SVGF, OIDN, NRD, BVH, TLAS/BLAS, path tracing, MIS, pbrt, mitsuba, Lumen, Cyberpunk RT Overdrive).

Writes 50 rows to data/v2/shared/batch_189.tmp.jsonl with ids shared-09401..09450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_189.tmp.jsonl"
ID_OFFSET = 9400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the offline renderer from NVIDIA OptiX 6 legacy pipeline to OptiX 7 SBT-driven programs; ray generation, miss, and closest-hit entry points now live in separate modules and link at SBT build time.", "architecture", "technical", False,
     [("NVIDIA OptiX", "library"), ("OptiX 7", "library"), ("SBT", "concept"), ("closest-hit", "concept")],
     [("OptiX 7", "NVIDIA OptiX", "REPLACES")],
     "how did the offline renderer restructure its OptiX pipeline around shader binding tables",
     "optix 7 sbt ray generation miss closest hit module pipeline"),
    # --- 2 ---
    ("Chose Intel Embree over a hand-rolled BVH traversal for the CPU reference path; the Embree 4 SIMD kernels beat the in-house code by roughly 3x on Sapphire Rapids without any tuning.", "decision", "technical", False,
     [("Intel Embree", "library"), ("Embree 4", "library"), ("BVH", "algorithm"), ("Sapphire Rapids", "platform")],
     [("Embree 4", "BVH", "REPLACES")],
     "which CPU ray tracing library replaced the hand-rolled traversal for the reference path and why",
     "intel embree 4 cpu bvh simd sapphire rapids reference path"),
    # --- 3 ---
    ("AMD Radeon Rays 4 drives the bake farm's GPU path on the RDNA3 workers; HIP targets and a fat binary let the same kernel ship for both CDNA compute nodes and client RDNA cards.", "fact", "technical", False,
     [("AMD Radeon Rays", "library"), ("HIP", "framework"), ("RDNA3", "platform"), ("CDNA", "platform")],
     [("AMD Radeon Rays", "HIP", "USES")],
     "which GPU ray tracing library and runtime handle the bake farm across RDNA3 and CDNA hardware",
     "radeon rays hip rdna3 cdna bake farm fat binary kernel"),
    # --- 4 ---
    ("DirectX Raytracing landed on the Windows build as the primary GPU backend; DXR 1.1 inline ray tracing inside a compute shader replaced the callable-shader fallback for short shadow queries.", "milestone", "technical", False,
     [("DirectX Raytracing", "framework"), ("DXR 1.1", "framework"), ("inline ray tracing", "concept"), ("callable-shader", "concept")],
     [("DXR 1.1", "callable-shader", "REPLACES")],
     "which Windows GPU backend became primary and how did inline ray tracing change the shadow query path",
     "dxr 1.1 inline ray tracing compute shader callable shadow"),
    # --- 5 ---
    ("Vulkan KHR_ray_tracing is the cross-platform path for Linux and Android devkits; VK_KHR_ray_tracing_pipeline plus VK_KHR_acceleration_structure give feature parity with DXR on the Turing-class reference box.", "architecture", "technical", False,
     [("Vulkan KHR_ray_tracing", "framework"), ("VK_KHR_ray_tracing_pipeline", "api"), ("VK_KHR_acceleration_structure", "api"), ("Turing", "platform")],
     [],
     "which Vulkan extensions give the Linux and Android builds feature parity with DXR",
     "vulkan khr ray tracing pipeline acceleration structure turing"),
    # --- 6 ---
    ("Metal Raytracing ships the Mac and iPad path; MTLAccelerationStructure builds run on the async compute queue so the BVH refit doesn't block the frame's GPU submission.", "architecture", "technical", False,
     [("Metal Raytracing", "framework"), ("MTLAccelerationStructure", "api"), ("async compute queue", "concept"), ("BVH refit", "method")],
     [],
     "how does the Apple backend avoid frame stalls when refitting acceleration structures",
     "metal raytracing mtlaccelerationstructure async compute bvh refit"),
    # --- 7 ---
    ("Direct lighting in the interior scenes is handled by RTXDI; the reservoir-based sampler drops one-spp noise on a thousand-light test set that blew out the naive uniform sampler.", "decision", "technical", False,
     [("RTXDI", "framework"), ("reservoir", "concept"), ("uniform sampler", "method")],
     [("RTXDI", "uniform sampler", "REPLACES")],
     "which direct-lighting sampler replaced the naive uniform approach for the thousand-light interior scenes",
     "rtxdi reservoir direct light interior thousand uniform sampler"),
    # --- 8 ---
    ("ReSTIR GI handles indirect bounces after the primary hit; spatial and temporal reuse of reservoirs recovers most of the variance that a single-sample path tracer leaves on the noise floor.", "architecture", "technical", False,
     [("ReSTIR GI", "algorithm"), ("reservoir", "concept"), ("indirect bounces", "concept"), ("path tracer", "concept")],
     [],
     "how does ReSTIR GI recover variance from a one-sample-per-pixel path tracer",
     "restir gi spatial temporal reuse reservoir indirect path variance"),
    # --- 9 ---
    ("RTXGI ships as the dynamic diffuse probe field fallback for platforms without enough ray budget for full ReSTIR; the DDGI probes update a small ray count per frame and still light cave interiors.", "architecture", "technical", False,
     [("RTXGI", "framework"), ("DDGI", "algorithm"), ("ReSTIR", "algorithm"), ("probe field", "concept")],
     [("RTXGI", "ReSTIR", "REPLACES")],
     "which probe-based GI fallback lights platforms that can't afford full ReSTIR",
     "rtxgi ddgi probe field ray budget restir fallback cave"),
    # --- 10. noise ---
    ("The office cafeteria swapped out the espresso machine and morale dropped for a week while the new grinder was calibrated.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("SVGF denoising cleans up the 1spp diffuse signal; the spatiotemporal edge-avoiding a-trous filter preserves contact shadows that a plain bilateral would smear across occluders.", "decision", "technical", False,
     [("SVGF", "algorithm"), ("a-trous filter", "algorithm"), ("bilateral", "algorithm"), ("contact shadows", "concept")],
     [("SVGF", "bilateral", "REPLACES")],
     "which denoising filter replaced the plain bilateral and what contact detail does it preserve",
     "svgf a trous spatiotemporal bilateral contact shadow 1spp diffuse"),
    # --- 12 ---
    ("Intel Open Image Denoise runs as the final-frame cleanup on CPU renders; the oidn U-Net passes the albedo and normal AOV guides alongside the colour buffer so high-frequency textures survive.", "architecture", "technical", False,
     [("Intel Open Image Denoise", "library"), ("U-Net", "algorithm"), ("albedo", "concept"), ("AOV", "concept")],
     [],
     "how does Open Image Denoise keep high-frequency texture detail intact during final-frame cleanup",
     "intel open image denoise oidn u-net albedo normal aov guide"),
    # --- 13 ---
    ("NVIDIA OIDN GPU build runs inside the viewport for progressive preview; Tensor Core acceleration brings the per-frame denoise under 4 ms on an RTX 4080, which fits the interactive budget.", "fact", "technical", False,
     [("NVIDIA OIDN", "library"), ("Tensor Core", "platform"), ("RTX 4080", "platform"), ("viewport", "concept")],
     [("NVIDIA OIDN", "Tensor Core", "USES")],
     "which denoiser runs inside the viewport progressive preview and what hardware drops its latency under 4 ms",
     "nvidia oidn tensor core rtx 4080 viewport progressive 4 ms"),
    # --- 14 ---
    ("NRD denoisers handle specular and diffuse separately in the realtime path; ReBLUR for diffuse and ReLAX for specular each get their own history buffer so a moving highlight doesn't bleed into matte surfaces.", "architecture", "technical", False,
     [("NRD", "library"), ("ReBLUR", "algorithm"), ("ReLAX", "algorithm"), ("history buffer", "concept")],
     [],
     "how does NRD keep specular highlights from bleeding into matte surfaces during realtime denoising",
     "nrd reblur relax specular diffuse history buffer highlight"),
    # --- 15 ---
    ("BVH construction defaulted to the SAH top-down builder for offline quality; the split heuristic took longer to bake but cut intersection counts by about 15% versus the median-split baseline.", "decision", "technical", False,
     [("BVH", "algorithm"), ("SAH", "algorithm"), ("top-down builder", "method"), ("median-split", "algorithm")],
     [("SAH", "median-split", "REPLACES")],
     "which BVH split heuristic replaced the median-split baseline for offline renders and what did it save",
     "sah bvh top down builder median split heuristic intersection"),
    # --- 16 ---
    ("HLBVH kicks in for rebuilds on streaming geometry; Morton-code sorting on GPU finishes in roughly one millisecond on a 500k-triangle delta, which the offline SAH builder could never match.", "decision", "technical", False,
     [("HLBVH", "algorithm"), ("Morton-code", "algorithm"), ("SAH", "algorithm"), ("streaming geometry", "concept")],
     [("HLBVH", "SAH", "REPLACES")],
     "which GPU BVH builder handles streaming geometry rebuilds when SAH is too slow",
     "hlbvh morton sort gpu stream geometry sah rebuild 1 ms"),
    # --- 17 ---
    ("PLOC builder sits between HLBVH and SAH on the quality/speed curve; the parallel locally-ordered clustering keeps BVH quality close to SAH while running on GPU in a few milliseconds per refit.", "architecture", "technical", False,
     [("PLOC", "algorithm"), ("HLBVH", "algorithm"), ("SAH", "algorithm"), ("BVH", "algorithm")],
     [],
     "which builder sits between HLBVH speed and SAH quality for GPU-side refits",
     "ploc parallel locally ordered clustering hlbvh sah bvh refit"),
    # --- 18 ---
    ("TLAS is rebuilt each frame from the instance list while BLAS compactions stream in asynchronously; skinned meshes get a BLAS refit rather than a rebuild, which cut the per-frame budget by about 40%.", "architecture", "technical", False,
     [("TLAS", "concept"), ("BLAS", "concept"), ("BLAS refit", "method"), ("skinned mesh", "concept")],
     [("BLAS refit", "BLAS", "APPLIES_TO")],
     "how are top-level and bottom-level acceleration structures scheduled across frames to cut the budget",
     "tlas blas refit skinned mesh compact async instance frame"),
    # --- 19 ---
    ("Ray payload was trimmed from 64 bytes to 16 bytes by packing throughput into two halves and folding the hit id into the payload's first lane; register pressure dropped enough to hit a higher occupancy on Ampere.", "problem", "technical", False,
     [("Ray payload", "concept"), ("Ampere", "platform"), ("register pressure", "concept")],
     [],
     "which ray-payload packing change reduced register pressure and helped Ampere occupancy",
     "ray payload 16 byte pack throughput register ampere occupancy"),
    # --- 20 ---
    ("Intersection shaders handle the procedural SDF primitives in the volumetric clouds; custom AABBs feed into a sphere-tracing loop that runs inside the intersection program and writes a custom payload.", "architecture", "technical", False,
     [("Intersection shaders", "concept"), ("SDF", "concept"), ("AABB", "concept"), ("sphere-tracing", "algorithm")],
     [],
     "how are procedural SDF clouds intersected in the ray pipeline without baking geometry",
     "intersection shader sdf aabb sphere trace volumetric cloud procedural"),
    # --- 21 ---
    ("Any-hit shaders were swapped for opacity micromaps on the foliage BLAS; the OMM path avoids invoking the any-hit for fully opaque or fully transparent microtriangles and cut alpha-traversal cost by roughly half.", "decision", "technical", False,
     [("Any-hit shaders", "concept"), ("opacity micromaps", "method"), ("foliage", "concept"), ("BLAS", "concept")],
     [("opacity micromaps", "Any-hit shaders", "REPLACES")],
     "which foliage-rendering trick replaced any-hit shaders and what traversal cost did it cut",
     "any hit opacity micromap omm foliage blas alpha traversal"),
    # --- 22 ---
    ("Inline ray tracing inside the depth-prepass compute shader handles screen-space fallback for thin features; rasterised pixels that fail a depth sanity check fire a short ray to resolve the correct occluder.", "architecture", "technical", False,
     [("Inline ray tracing", "concept"), ("depth-prepass", "concept"), ("compute shader", "concept"), ("screen-space", "concept")],
     [],
     "how does the depth-prepass use inline ray tracing to repair thin-feature occlusion errors",
     "inline ray tracing depth prepass compute screen space thin occluder"),
    # --- 23 ---
    ("Full path tracing is enabled for cinematics; the realtime path tracer integrates 4 bounces with Russian roulette termination and NEE at every vertex, which keeps the long-path contribution from exploding.", "architecture", "technical", False,
     [("path tracing", "algorithm"), ("Russian roulette", "method"), ("NEE", "algorithm")],
     [],
     "how does the cinematic path tracer balance bounce count against long-path variance",
     "path tracing russian roulette nee 4 bounce cinematic variance"),
    # --- 24 ---
    ("Light transport integrator is a bidirectional path tracer for reference renders; the unidirectional path tracer ships for realtime while BDPT handles caustics and laser-beam scenes the forward path undersamples.", "decision", "technical", False,
     [("Light transport", "concept"), ("bidirectional path tracer", "algorithm"), ("BDPT", "algorithm"), ("caustics", "concept")],
     [("BDPT", "bidirectional path tracer", "IS_A")],
     "which integrator handles caustic scenes that the forward path tracer undersamples",
     "bidirectional path tracer bdpt caustic laser reference forward"),
    # --- 25 ---
    ("Importance sampling uses a cosine-weighted hemisphere sampler for diffuse lobes and GGX VNDF sampling for the specular; the old uniform hemisphere sampler was retired after variance tests on rough metals.", "decision", "technical", False,
     [("Importance sampling", "concept"), ("GGX VNDF", "algorithm"), ("cosine-weighted hemisphere", "method"), ("uniform hemisphere", "method")],
     [("GGX VNDF", "uniform hemisphere", "REPLACES")],
     "which specular and diffuse samplers replaced the uniform hemisphere sampler and why",
     "cosine weighted ggx vndf importance sampling uniform specular"),
    # --- 26 ---
    ("NEE is shadow-ray sparing against a compact light BVH; next-event estimation picks a light with power-weighted sampling and fires one occlusion ray per vertex instead of relying on the BRDF sampler to stumble onto it.", "architecture", "technical", False,
     [("NEE", "algorithm"), ("light BVH", "concept"), ("power-weighted sampling", "method"), ("BRDF", "concept")],
     [("NEE", "BRDF", "IMPROVES_ON")],
     "how does next-event estimation find lights more reliably than a BRDF-only sampler",
     "nee next event estimation light bvh power weighted brdf shadow"),
    # --- 27 ---
    ("MIS with the balance heuristic combines BRDF and light samples; the power heuristic was dropped after A/B tests on glossy scenes where the balance version had lower variance on average.", "decision", "technical", False,
     [("MIS", "algorithm"), ("balance heuristic", "method"), ("power heuristic", "method"), ("BRDF", "concept")],
     [("balance heuristic", "power heuristic", "REPLACES")],
     "which MIS heuristic replaced the power heuristic after the glossy-scene A/B tests",
     "mis balance heuristic power brdf glossy a b variance"),
    # --- 28 ---
    ("pbrt-v4 is the offline ground-truth renderer for regression suites; every material and light addition gets a pbrt scene captured so the realtime path has a pixel-accurate reference to chase.", "reference", "technical", False,
     [("pbrt", "tool"), ("pbrt-v4", "tool"), ("ground-truth", "concept"), ("regression", "concept")],
     [],
     "which offline renderer serves as the ground truth for realtime material and light regressions",
     "pbrt v4 ground truth regression realtime reference material"),
    # --- 29 ---
    ("Mitsuba renderer is used for BSDF-model validation; mitsuba 3's differentiable path tracer also feeds the material-inversion workflow that solves for fabric parameters from photographs.", "reference", "technical", False,
     [("Mitsuba renderer", "tool"), ("mitsuba 3", "tool"), ("BSDF", "concept"), ("differentiable path tracer", "algorithm")],
     [],
     "which renderer validates BSDF models and supports differentiable material inversion from photos",
     "mitsuba 3 bsdf differentiable path tracer fabric inversion photo"),
    # --- 30 ---
    ("Unreal Engine's Lumen is the baseline realtime GI comparison point; Lumen software ray tracing against distance fields on mid-range cards and the hardware Lumen path on RTX cards both get benchmarked.", "reference", "technical", False,
     [("Lumen", "framework"), ("Unreal Engine", "framework"), ("distance fields", "concept"), ("RTX", "platform")],
     [("Unreal Engine", "Lumen", "HAS_PART")],
     "which engine's GI system serves as the realtime comparison point on both software and hardware paths",
     "lumen unreal software hardware distance field rtx mid range"),
    # --- 31 ---
    ("Cyberpunk RT Overdrive was the spec reference for the path-tracing tier; ReSTIR DI, ReSTIR GI, and NRD denoisers working together set the bar for noise-to-image on a 1spp budget.", "reference", "technical", False,
     [("Cyberpunk RT Overdrive", "project"), ("ReSTIR DI", "algorithm"), ("ReSTIR GI", "algorithm"), ("NRD", "library")],
     [("Cyberpunk RT Overdrive", "ReSTIR DI", "USES")],
     "which shipping title set the reference bar for 1spp path tracing and which algorithms does it chain",
     "cyberpunk rt overdrive restir di gi nrd 1spp reference bar"),
    # --- 32 ---
    ("BLAS compaction runs on the copy queue after each build; VK_KHR_acceleration_structure's query-pool size readback tells the allocator the compact footprint so the scratch buffer shrinks before the next frame.", "architecture", "technical", False,
     [("BLAS compaction", "method"), ("copy queue", "concept"), ("VK_KHR_acceleration_structure", "api"), ("scratch buffer", "concept")],
     [],
     "how does the Vulkan backend reclaim BLAS scratch memory between frames",
     "blas compaction copy queue vulkan scratch buffer shrink"),
    # --- 33 ---
    ("Ray-cone derivatives feed the texture sampler through the hit attribute; the LOD calculation from ray differentials replaced the fixed mip bias used in the early prototype and killed the moire on distant roofs.", "problem", "technical", False,
     [("Ray-cone", "concept"), ("ray differentials", "concept"), ("LOD", "concept"), ("mip bias", "method")],
     [("Ray-cone", "mip bias", "REPLACES")],
     "which LOD method replaced the fixed mip bias and which artefact did it remove",
     "ray cone differential lod mip bias moire distant roof"),
    # --- 34 ---
    ("Stochastic transparency in the foliage sampler uses hashed-alpha sampling instead of order-independent blending; the OIT cost on the dense forest scene dropped by roughly a third.", "decision", "technical", False,
     [("Stochastic transparency", "algorithm"), ("hashed-alpha sampling", "algorithm"), ("OIT", "algorithm"), ("foliage", "concept")],
     [("hashed-alpha sampling", "OIT", "REPLACES")],
     "which sampling trick replaced order-independent transparency in the foliage pass",
     "stochastic transparency hashed alpha oit foliage forest dense"),
    # --- 35 ---
    ("Light tree construction for NEE uses a top-down SAH-style split on light power and position; the old flat power sampler missed small dim lights in a room full of big emitters and this fixed it.", "problem", "technical", False,
     [("Light tree", "algorithm"), ("NEE", "algorithm"), ("SAH", "algorithm"), ("flat power sampler", "method")],
     [("Light tree", "flat power sampler", "REPLACES")],
     "which light-sampling structure replaced the flat power sampler and what failure did it fix",
     "light tree sah nee flat power sampler dim small emitter"),
    # --- 36 ---
    ("Path regularisation truncates the specular roughness on secondary bounces to 0.3; firefly count per million rays dropped by two orders of magnitude without a visible blur on glossy interiors.", "problem", "technical", False,
     [("Path regularisation", "method"), ("firefly", "concept"), ("secondary bounces", "concept")],
     [],
     "which path-tracer hack cut firefly counts two orders of magnitude without visible blur",
     "path regularisation roughness secondary bounce firefly glossy"),
    # --- 37 ---
    ("The renderer team prefers Vulkan KHR_ray_tracing over OpenGL NV_ray_tracing for new code; the NV-prefixed extension is treated as legacy and only the proton-compat path keeps touching it.", "preference", "technical", False,
     [("Vulkan KHR_ray_tracing", "framework"), ("OpenGL NV_ray_tracing", "api"), ("proton-compat", "concept")],
     [("Vulkan KHR_ray_tracing", "OpenGL NV_ray_tracing", "PREFERS")],
     "which ray tracing API do the renderer team pick for new code over the NV-prefixed OpenGL one",
     "vulkan khr ray tracing opengl nv legacy proton prefer"),
    # --- 38 ---
    ("DLSS Ray Reconstruction replaces the separate denoise-then-upscale pipeline on RTX 40 builds; a single neural pass consumes 1spp input and produces the final 4K frame, which tightened frame pacing.", "milestone", "technical", False,
     [("DLSS Ray Reconstruction", "framework"), ("RTX 40", "platform"), ("denoise-then-upscale", "method")],
     [("DLSS Ray Reconstruction", "denoise-then-upscale", "REPLACES")],
     "which neural pass replaced the separate denoise and upscale stages on RTX 40",
     "dlss ray reconstruction rtx 40 denoise upscale 1spp 4k pacing"),
    # --- 39 ---
    ("The art team prefers mitsuba over pbrt for quick material previews; mitsuba's interactive viewer beats pbrt's file-based flow for one-shot iteration on a single BSDF.", "preference", "technical", False,
     [("mitsuba", "tool"), ("pbrt", "tool"), ("BSDF", "concept")],
     [("mitsuba", "pbrt", "PREFERS")],
     "which reference renderer does the art team prefer for quick single-BSDF material previews",
     "mitsuba pbrt art team material preview bsdf interactive"),
    # --- 40 ---
    ("The core rendering team prefers ReSTIR over classic light-cache methods for dynamic indirect lighting; moving emitters expose the light cache's staleness, which the reservoir reuse hides.", "preference", "technical", False,
     [("ReSTIR", "algorithm"), ("light-cache", "method"), ("dynamic indirect lighting", "concept")],
     [("ReSTIR", "light-cache", "PREFERS")],
     "which indirect-lighting method does the core team favour for dynamic emitters and why",
     "restir light cache dynamic indirect reservoir moving emitter stale"),
    # --- 41 ---
    ("Shipped the path-tracing tier on 2026-02-14 with ReSTIR DI, ReSTIR GI, NRD denoising, and DLSS Ray Reconstruction all enabled on RTX 40 class hardware; 4K60 on a 4090 verified against the pbrt reference.", "milestone", "technical", False,
     [("path-tracing tier", "project"), ("ReSTIR DI", "algorithm"), ("ReSTIR GI", "algorithm"), ("DLSS Ray Reconstruction", "framework"), ("2026-02-14", "date"), ("RTX 40", "platform")],
     [("path-tracing tier", "ReSTIR DI", "USES")],
     "when did the path-tracing tier ship and which stack ran on 4090 at 4K60",
     "path tracing tier ship restir nrd dlss 4090 4k60 2026 02 14"),
    # --- 42 ---
    ("Hit-group stride landed wrong in the SBT and every other primitive read the wrong closest-hit program; the fix was to align the stride to the largest hit group's record size and zero-pad the rest.", "problem", "technical", False,
     [("Hit-group", "concept"), ("SBT", "concept"), ("closest-hit", "concept")],
     [],
     "which SBT mistake sent every other primitive to the wrong closest-hit and how was it fixed",
     "hit group stride sbt closest hit align pad record size"),
    # --- 43. noise ---
    ("A pigeon established residency on the studio's fire escape and started intercepting lunch deliveries off the back stairs.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Shader-execution reordering on Ada Lovelace cards reshuffles divergent hit shaders by material id; the SER extension cut path-tracing frame time by about 20% on a diverse-material test scene.", "milestone", "technical", False,
     [("Shader-execution reordering", "method"), ("Ada Lovelace", "platform"), ("SER", "method"), ("hit shader", "concept")],
     [("SER", "Shader-execution reordering", "IS_A")],
     "which Ada Lovelace feature reshuffles divergent hit shaders and how much frame time did it save",
     "shader execution reorder ser ada lovelace divergent material 20%"),
    # --- 45 ---
    ("BLAS built via build-with-compaction returned an invalid footprint on the first driver release; the workaround was to run the build, query the compacted size, and rebuild into a tight allocation on frame boundary.", "problem", "technical", False,
     [("BLAS", "concept"), ("build-with-compaction", "method"), ("driver release", "concept")],
     [],
     "how did the team work around the first-release driver bug in BLAS build-with-compaction",
     "blas build compaction footprint driver bug rebuild allocation"),
    # --- 46 ---
    ("Reference frames are captured with pbrt-v4 and compared to realtime output via a FLIP perceptual metric; any scene above a 0.05 FLIP mean goes back into the queue for investigation.", "architecture", "technical", False,
     [("pbrt-v4", "tool"), ("FLIP", "method"), ("realtime output", "concept")],
     [],
     "how are realtime frames compared to the pbrt reference and which threshold triggers reinvestigation",
     "pbrt v4 flip perceptual reference realtime 0.05 threshold"),
    # --- 47 ---
    ("TLAS instance mask bits encode ray-type visibility; shadow rays set a mask that excludes invisible-to-shadow proxies so the shadow pass skips a traversal layer that camera rays still need.", "fact", "technical", False,
     [("TLAS", "concept"), ("instance mask", "concept"), ("shadow rays", "concept"), ("camera rays", "concept")],
     [],
     "how do TLAS instance masks skip traversal layers per ray type for shadows versus camera",
     "tlas instance mask shadow ray camera proxy visibility traversal"),
    # --- 48 ---
    ("Embree user-geometry callbacks handle the hair primitive traversal; the oriented-curve intersector in Embree 4 handles Bezier hair faster than the stamped capsule fallback used in the early prototype.", "decision", "technical", False,
     [("Embree", "library"), ("Embree 4", "library"), ("user-geometry", "api"), ("Bezier hair", "concept"), ("stamped capsule", "method")],
     [("Embree 4", "stamped capsule", "REPLACES")],
     "which Embree 4 intersector replaced the stamped-capsule fallback for Bezier hair",
     "embree 4 user geometry bezier hair oriented curve capsule"),
    # --- 49 ---
    ("Path-guiding on the offline path samples the incoming radiance field with an online-learned SD-tree; the 5D guiding field converges by frame 10 and cuts variance on the caustic bedroom scene roughly in half.", "architecture", "technical", False,
     [("Path-guiding", "algorithm"), ("SD-tree", "algorithm"), ("caustic", "concept"), ("radiance field", "concept")],
     [],
     "which online-learned structure drives path-guiding and how fast does it converge on the caustic scene",
     "path guiding sd tree online caustic bedroom 5d radiance frame 10"),
    # --- 50 ---
    ("A wavefront path tracer replaced the megakernel tracer on GPU; sorting rays by material id between bounces fixed the divergent-branch stalls the megakernel hit on Turing and kept occupancy high.", "decision", "technical", False,
     [("wavefront path tracer", "algorithm"), ("megakernel tracer", "algorithm"), ("Turing", "platform"), ("material id", "concept")],
     [("wavefront path tracer", "megakernel tracer", "REPLACES")],
     "which GPU path-tracer structure replaced the megakernel and fixed Turing's divergent-branch stalls",
     "wavefront megakernel path tracer sort material turing divergent"),
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
            # Claim spans longest-first to avoid shorter substrings consuming bytes
            # that a longer name needs; then restore original declaration order.
            order = sorted(range(len(ents)), key=lambda k: -len(ents[k][0]))
            spans: dict[int, tuple[int, int]] = {}
            for k in order:
                name, _ = ents[k]
                s, e = _find_span(text, name, used)
                used.append((s, e))
                spans[k] = (s, e)
            entities = []
            for k, (name, typ) in enumerate(ents):
                s, e = spans[k]
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
