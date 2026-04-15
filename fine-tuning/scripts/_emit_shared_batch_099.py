"""One-off emitter for shared-base batch-099 — technical domain (graphics, GPU, and rendering systems).

Writes 50 rows to data/v2/shared/batch_099.tmp.jsonl with ids shared-04901..04950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_099.tmp.jsonl"
ID_OFFSET = 4900

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Vulkan replaced OpenGL on the cross-platform engine's Linux backend; explicit synchronization and per-queue submission cut frame pacing jitter by half.", "decision", "technical", False,
     [("Vulkan", "api"), ("OpenGL", "api")],
     [("Vulkan", "OpenGL", "REPLACES")],
     "which graphics API displaced OpenGL on the engine's Linux backend",
     "Vulkan explicit sync queue submit frame pacing jitter"),
    # --- 2 ---
    ("Metal 3 hosted the macOS renderer instead of the MoltenVK translation layer; argument buffers and MetalFX upscaling paid back the native port work within a release.", "decision", "technical", False,
     [("Metal 3", "api"), ("MoltenVK", "library"), ("MetalFX", "technology")],
     [("Metal 3", "MoltenVK", "REPLACES")],
     "which macOS graphics path took over from the MoltenVK translation shim",
     "Metal argument buffer MetalFX upscale native port macOS"),
    # --- 3 ---
    ("DirectX 12 Ultimate shipped the Windows renderer with mesh shaders and DirectStorage; the DX11 fallback stayed for integrated GPUs older than Ivy Bridge.", "architecture", "technical", False,
     [("DirectX 12 Ultimate", "api"), ("DirectStorage", "technology"), ("DX11", "api"), ("Ivy Bridge", "technology")],
     [],
     "which Windows graphics stack drives the modern renderer and what stayed on DX11",
     "DX12 Ultimate mesh shader DirectStorage fallback integrated"),
    # --- 4 ---
    ("WebGPU replaced WebGL 2 on the in-browser viewer; compute shaders ran the mesh decimation pass the old GLSL ES pipeline could not touch.", "decision", "technical", False,
     [("WebGPU", "api"), ("WebGL 2", "api"), ("GLSL ES", "language")],
     [("WebGPU", "WebGL 2", "REPLACES")],
     "which browser graphics API displaced WebGL 2 for the in-browser viewer",
     "WebGPU compute shader mesh decimate WebGL replace browser"),
    # --- 5 ---
    ("The legacy OpenGL fixed-function path was deleted from the CAD viewer; glBegin and the matrix stack mapped cleanly onto a retained-mode scene graph instead.", "milestone", "technical", False,
     [("OpenGL", "api"), ("glBegin", "command")],
     [],
     "which legacy GL immediate-mode surface disappeared from the CAD viewer",
     "fixed function immediate mode matrix stack retire CAD"),
    # --- 6 ---
    ("Mesa 24 landed the ANV Vulkan driver on the Linux test fleet; RADV on the AMD cards tracked the same RADV-specific extensions without a rebuild.", "fact", "technical", False,
     [("Mesa 24", "library"), ("ANV", "library"), ("Vulkan", "api"), ("RADV", "library"), ("AMD", "organization")],
     [("ANV", "Vulkan", "IMPLEMENTS")],
     "which Mesa Vulkan drivers covered Intel and AMD on the Linux fleet",
     "Mesa ANV RADV Vulkan driver Linux fleet Intel AMD"),
    # --- 7 ---
    ("RenderDoc caught a missing pipeline barrier between the depth pass and the SSAO read; the sync validation layer had hidden the hazard under default settings.", "problem", "technical", False,
     [("RenderDoc", "tool"), ("SSAO", "algorithm")],
     [],
     "which capture tool surfaced the missing depth-to-SSAO barrier",
     "RenderDoc capture pipeline barrier depth SSAO hazard sync"),
    # --- 8 ---
    ("PIX on Windows profiled the DirectX 12 frame; the GPU-capture timing view pinpointed a 3.2 ms stall on descriptor heap copies during shadow map resolves.", "problem", "technical", False,
     [("PIX", "tool"), ("DirectX 12", "api")],
     [],
     "which profiler isolated the descriptor heap stall on shadow resolves",
     "PIX GPU capture descriptor heap copy stall shadow DX12"),
    # --- 9 ---
    ("Nsight Graphics replaced the homegrown frame dumper for NVIDIA hardware debugging; shader debugging on SPIR-V and HLSL dropped turnaround from hours to minutes.", "decision", "technical", False,
     [("Nsight Graphics", "tool"), ("frame dumper", "tool"), ("NVIDIA", "organization"), ("SPIR-V", "language"), ("HLSL", "language")],
     [("Nsight Graphics", "frame dumper", "REPLACES")],
     "which vendor tool took over shader debugging on NVIDIA boards",
     "Nsight shader debug SPIR-V HLSL turnaround frame dumper"),
    # --- 10. noise ---
    ("Hold on, reloading the driver.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Hardware ray tracing on RTX 40-series used the DXR 1.1 inline tracing path; per-ray payload size was capped at 32 bytes to keep the traversal coherent.", "architecture", "technical", False,
     [("RTX 40-series", "technology"), ("DXR 1.1", "api")],
     [],
     "which DXR path drove the inline traversal on the RTX 40 cards",
     "DXR inline ray traversal payload coherent RTX 40 cap"),
    # --- 12 ---
    ("The BVH rebuild was offloaded to a compute queue with async parallel to the gbuffer pass; fit-to-refit heuristic kept the rebuild budget under 0.6 ms a frame.", "architecture", "technical", False,
     [("BVH", "algorithm")],
     [],
     "which async strategy kept the BVH rebuild inside a 0.6 ms budget",
     "BVH refit compute queue async gbuffer budget frame"),
    # --- 13 ---
    ("Vulkan ray tracing via VK_KHR_ray_tracing_pipeline replaced the original NV_ray_tracing extension; the shader binding table layout aligned with DXR for cross-API parity.", "decision", "technical", False,
     [("VK_KHR_ray_tracing_pipeline", "api"), ("NV_ray_tracing", "api"), ("DXR", "api")],
     [("VK_KHR_ray_tracing_pipeline", "NV_ray_tracing", "REPLACES")],
     "which standardized RT extension displaced the NV-only original on Vulkan",
     "KHR ray tracing pipeline SBT DXR parity extension swap"),
    # --- 14 ---
    ("HLSL Shader Model 6.6 replaced the HLSL SM 5.1 authoring path on the engine; wave intrinsics and dynamic resources shaped the bindless transition.", "decision", "technical", False,
     [("HLSL", "language"), ("Shader Model 6.6", "technology"), ("HLSL SM 5.1", "technology")],
     [("Shader Model 6.6", "HLSL SM 5.1", "REPLACES")],
     "which shader model took over the engine's HLSL authoring path",
     "SM 6.6 wave intrinsic dynamic resource bindless HLSL"),
    # --- 15 ---
    ("WGSL shaders were authored directly instead of cross-compiling from GLSL; Naga's SPIR-V and MSL backends kept feature parity across the WebGPU and native targets.", "preference", "technical", False,
     [("WGSL", "language"), ("GLSL", "language"), ("Naga", "tool"), ("SPIR-V", "language"), ("MSL", "language"), ("WebGPU", "api")],
     [("WGSL", "GLSL", "PREFERS")],
     "which shader language was preferred over cross-compiled GLSL for WebGPU",
     "WGSL direct author Naga SPIR-V MSL WebGPU parity"),
    # --- 16 ---
    ("DXC replaced FXC as the HLSL compiler on the build farm; SPIR-V emission for Vulkan targets shared a single source tree with the DX12 path.", "decision", "technical", False,
     [("DXC", "tool"), ("FXC", "tool"), ("HLSL", "language"), ("SPIR-V", "language"), ("Vulkan", "api"), ("DX12", "api")],
     [("DXC", "FXC", "REPLACES")],
     "which HLSL compiler took over from FXC on the build farm",
     "DXC SPIR-V DX12 Vulkan shared tree build farm shader"),
    # --- 17 ---
    ("Unreal Engine 5's RHI abstraction routed the scene to Vulkan on Linux, DX12 on Windows, and Metal on Apple silicon; the null RHI covered headless cook runs.", "architecture", "technical", False,
     [("Unreal Engine 5", "framework"), ("RHI", "concept"), ("Vulkan", "api"), ("DX12", "api"), ("Metal", "api")],
     [("Unreal Engine 5", "RHI", "HAS_PART")],
     "which RHI targets does Unreal 5 route to across the three desktop platforms",
     "UE5 RHI Vulkan DX12 Metal null cook headless route"),
    # --- 18 ---
    ("Unity's URP replaced the Built-in Render Pipeline on the mobile title; SRP Batcher and Forward+ lighting bought a 35 percent frame-time reduction on Adreno 650.", "decision", "technical", False,
     [("URP", "framework"), ("Built-in Render Pipeline", "framework"), ("SRP Batcher", "technology"), ("Adreno 650", "technology")],
     [("URP", "Built-in Render Pipeline", "REPLACES")],
     "which Unity pipeline displaced the legacy Built-in on the mobile title",
     "URP SRP batcher Forward plus Adreno mobile frame time"),
    # --- 19 ---
    ("Bevy on wgpu drove the indie renderer; the wgpu-hal backends mapped onto Vulkan, Metal, DX12, and WebGPU without a custom abstraction layer above.", "architecture", "technical", False,
     [("Bevy", "framework"), ("wgpu", "library"), ("Vulkan", "api"), ("Metal", "api"), ("DX12", "api"), ("WebGPU", "api")],
     [("Bevy", "wgpu", "USES")],
     "which Rust graphics stack gave Bevy its four-backend coverage",
     "Bevy wgpu hal Vulkan Metal DX12 WebGPU Rust indie"),
    # --- 20 ---
    ("Godot 4's Vulkan renderer replaced the GLES3 pipeline on the desktop target; the forward-plus clustered lighting matched the URP feature set at parity.", "decision", "technical", False,
     [("Godot 4", "framework"), ("Vulkan", "api"), ("GLES3", "api"), ("URP", "framework")],
     [("Vulkan", "GLES3", "REPLACES")],
     "which Godot 4 renderer displaced the GLES3 pipeline on desktop",
     "Godot Vulkan GLES3 clustered forward plus URP parity"),
    # --- 21 ---
    ("PhysX GPU cloth was disabled on mid-range cards; the CPU fallback via PhysX CPU kept the tearing animation inside 2 ms per frame without spiking VRAM.", "decision", "technical", False,
     [("PhysX", "library"), ("VRAM", "concept")],
     [],
     "which PhysX path ran the cloth on mid-range GPUs and why",
     "PhysX cloth CPU fallback mid range VRAM spike frame"),
    # --- 22 ---
    ("Lumen replaced the baked lightmap GI pipeline on the open-world title; screen-trace plus surface cache held real-time bounce lighting at 1080p60 on RTX 3070.", "decision", "technical", False,
     [("Lumen", "technology"), ("baked lightmap", "method"), ("RTX 3070", "technology")],
     [("Lumen", "baked lightmap", "IMPROVES_ON")],
     "which GI solution displaced baked lightmaps on the open-world title",
     "Lumen screen trace surface cache real time bounce 1080p"),
    # --- 23 ---
    ("RTXGI probes fed the dynamic GI on the interior scenes; the DDGI irradiance volume improved on SH light probes that the previous engine used.", "architecture", "technical", False,
     [("RTXGI", "technology"), ("DDGI", "algorithm"), ("SH light probes", "method")],
     [("DDGI", "SH light probes", "IMPROVES_ON")],
     "which RTXGI primitive upgraded the interior GI over SH probes",
     "RTXGI DDGI irradiance volume SH probe interior upgrade"),
    # --- 24 ---
    ("SVT-based virtual texturing replaced the megatexture on the open world; on-demand page residency trimmed VRAM by 4 GB and masked streaming hitches.", "decision", "technical", False,
     [("SVT", "technology"), ("megatexture", "technology"), ("VRAM", "concept")],
     [("SVT", "megatexture", "REPLACES")],
     "which virtual texturing system displaced the megatexture approach",
     "sparse virtual texture megatexture page resident VRAM stream"),
    # --- 25 ---
    ("Mesh shaders on DX12 Ultimate replaced the traditional vertex-plus-geometry stage on the foliage pass; amplification shader culling dropped primitives before rasterizer load.", "decision", "technical", False,
     [("Mesh shaders", "technology"), ("DX12 Ultimate", "api"), ("vertex-plus-geometry stage", "technology"), ("amplification shader", "technology")],
     [("Mesh shaders", "vertex-plus-geometry stage", "REPLACES")],
     "which DX12 stage displaced the classic vertex plus geometry on foliage",
     "mesh shader amplification cull vertex geometry replace"),
    # --- 26 ---
    ("Nanite handled the UE5 statue asset without manual LOD chains; the cluster-level culling and SW rasterizer skipped the micropoly draw-call storm.", "architecture", "technical", False,
     [("Nanite", "technology"), ("UE5", "framework"), ("LOD chains", "method")],
     [("Nanite", "LOD chains", "REPLACES")],
     "which UE5 technology retired manual LOD chains on the statue asset",
     "Nanite cluster cull software rasterizer micropoly LOD"),
    # --- 27 ---
    ("NVIDIA Ada Lovelace cards ran the DLSS 3.5 Ray Reconstruction path; the OFA motion vectors fed Frame Generation inside a single GPU frame.", "architecture", "technical", False,
     [("NVIDIA Ada Lovelace", "technology"), ("DLSS 3.5", "technology"), ("OFA", "technology"), ("Frame Generation", "technology")],
     [],
     "which Ada hardware path drove DLSS 3.5 Ray Reconstruction and Frame Gen",
     "Ada Lovelace DLSS 3.5 OFA motion vector frame generation"),
    # --- 28 ---
    ("AMD RDNA 3 cards used FSR 3 frame generation via AMD Fluid Motion Frames; the driver-level hook stayed separate from the in-engine FSR 3.1 integration.", "architecture", "technical", False,
     [("AMD RDNA 3", "technology"), ("FSR 3", "technology"), ("AMD Fluid Motion Frames", "technology"), ("FSR 3.1", "technology")],
     [],
     "which AMD frame-generation hook sat at the driver level on RDNA 3",
     "RDNA 3 FSR 3 Fluid Motion Frames driver engine"),
    # --- 29 ---
    ("RDNA 4 ray-tracing throughput improved on RDNA 3's BVH traversal; the dedicated RT unit was preferred for the path-traced reference at internal benchmarks.", "preference", "technical", False,
     [("RDNA 4", "technology"), ("RDNA 3", "technology"), ("BVH", "algorithm")],
     [("RDNA 4", "RDNA 3", "IMPROVES_ON")],
     "which AMD GPU generation improved on RDNA 3's BVH throughput",
     "RDNA 4 ray tracing BVH traversal path traced benchmark"),
    # --- 30 ---
    ("Apple M3 Max drove the Metal 3 dev kit; hardware-accelerated ray tracing and dynamic caching ran the studio's path tracer at iPad-class power draw.", "fact", "technical", False,
     [("Apple M3 Max", "technology"), ("Metal 3", "api")],
     [],
     "which Apple silicon part ran the studio's Metal 3 path tracer",
     "M3 Max Metal 3 hardware ray trace dynamic caching power"),
    # --- 31 ---
    ("Apple M4 replaced the M2 Pro dev machine for the shader authoring seat; the ray tracing throughput doubled on the studio's BVH microbenchmarks.", "decision", "technical", False,
     [("Apple M4", "technology"), ("M2 Pro", "technology"), ("BVH", "algorithm")],
     [("Apple M4", "M2 Pro", "REPLACES")],
     "which Apple silicon part took over shader authoring from the M2 Pro",
     "M4 shader authoring ray trace BVH microbenchmark double"),
    # --- 32 ---
    ("CUDA interop with Vulkan used the VK_KHR_external_memory extension; the denoiser kernel shared a buffer with the swapchain-fed color target without a host round-trip.", "architecture", "technical", False,
     [("CUDA", "platform"), ("Vulkan", "api"), ("VK_KHR_external_memory", "api")],
     [("CUDA", "Vulkan", "COMMUNICATES_WITH")],
     "which extension let the CUDA denoiser share memory with the Vulkan swapchain",
     "CUDA Vulkan external memory denoiser swapchain interop"),
    # --- 33 ---
    ("OptiX 8 drove the offline denoiser on the film render; the CUDA context shared devices with the real-time viewer without double allocation.", "architecture", "technical", False,
     [("OptiX 8", "library"), ("CUDA", "platform")],
     [],
     "which denoiser stack ran the offline pass alongside the live viewer",
     "OptiX 8 denoiser film CUDA context share device view"),
    # --- 34. noise ---
    ("Just dropped a frame, nothing big.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("OCIO 2.3 wired the ACES 2065-1 working space through Nuke and the in-engine view transform; the display-side OETF stayed ST.2084 for the HDR pass.", "architecture", "technical", False,
     [("OCIO 2.3", "library"), ("ACES 2065-1", "technology"), ("Nuke", "tool"), ("OETF", "concept"), ("ST.2084", "protocol")],
     [("OCIO 2.3", "ACES 2065-1", "USES")],
     "which color pipeline wired ACES across the comp and the engine view",
     "OCIO ACES 2065-1 Nuke OETF ST.2084 HDR working space"),
    # --- 36 ---
    ("ACES 1.3 replaced the homegrown LUT stack on the trailer pipeline; the ODT for Rec.709 kept SDR deliverables inside the studio's spec.", "decision", "technical", False,
     [("ACES 1.3", "technology"), ("LUT stack", "method"), ("ODT", "concept"), ("Rec.709", "protocol")],
     [("ACES 1.3", "LUT stack", "REPLACES")],
     "which color standard displaced the homegrown LUT stack for trailers",
     "ACES 1.3 ODT Rec 709 SDR trailer LUT stack replace"),
    # --- 37 ---
    ("The HDR EOTF on the display-mapped output was PQ via BT.2100; the SDR path kept sRGB piece-wise instead of the approximate 2.2 gamma.", "fact", "technical", False,
     [("PQ", "protocol"), ("BT.2100", "protocol"), ("sRGB", "protocol")],
     [],
     "which EOTF mapped the HDR output and which curve handled SDR",
     "PQ BT.2100 EOTF sRGB piecewise gamma 2.2 HDR SDR"),
    # --- 38 ---
    ("DirectStorage 1.2 replaced the synchronous Win32 file reads for asset streaming; GPU decompression via GDeflate saved CPU cycles on the loading screen.", "decision", "technical", False,
     [("DirectStorage 1.2", "technology"), ("Win32", "api"), ("GDeflate", "algorithm")],
     [("DirectStorage 1.2", "Win32", "REPLACES")],
     "which Windows IO path displaced Win32 reads for asset streaming",
     "DirectStorage GDeflate GPU decompress Win32 load screen"),
    # --- 39 ---
    ("Variable Rate Shading tier 2 was preferred over half-resolution forward passes on the racing title; coarse 4x4 tiles on peripheral areas saved 18 percent pixel cost.", "preference", "technical", False,
     [("Variable Rate Shading", "technology")],
     [],
     "which shading trick beat half-resolution passes on the racing title",
     "VRS tier 2 coarse tile peripheral pixel cost saving"),
    # --- 40 ---
    ("Work Graphs on DX12 replaced the indirect dispatch chain in the particle simulator; producer-consumer nodes ran the kernel graph without CPU stitching.", "decision", "technical", False,
     [("Work Graphs", "technology"), ("DX12", "api"), ("indirect dispatch chain", "pattern")],
     [("Work Graphs", "indirect dispatch chain", "REPLACES")],
     "which DX12 feature took over the particle sim's indirect dispatch chain",
     "Work Graphs producer consumer kernel graph particle sim"),
    # --- 41 ---
    ("SPIR-V 1.6 was targeted by the shader authoring pipeline; the Tint compiler handled WGSL intake and Naga handled the reverse path to MSL.", "architecture", "technical", False,
     [("SPIR-V 1.6", "language"), ("Tint", "tool"), ("WGSL", "language"), ("Naga", "tool"), ("MSL", "language")],
     [("Tint", "WGSL", "USES")],
     "which compilers round-tripped WGSL through SPIR-V and MSL",
     "SPIR-V 1.6 Tint WGSL Naga MSL round trip shader"),
    # --- 42 ---
    ("The Khronos Vulkan specification at version 1.3 is the reference for the engine's synchronization chapter; timeline semaphores supersede binary fences in the main loop.", "reference", "technical", False,
     [("Vulkan", "api"), ("Khronos", "organization")],
     [],
     "which Vulkan spec version anchors the engine's sync documentation",
     "Vulkan 1.3 spec timeline semaphore binary fence sync"),
    # --- 43 ---
    ("Bindless descriptors via VK_EXT_descriptor_indexing replaced the per-draw descriptor set churn; the GPU-driven renderer's material table fit inside a single 1 million slot heap.", "decision", "technical", False,
     [("VK_EXT_descriptor_indexing", "api"), ("per-draw descriptor set", "pattern")],
     [("VK_EXT_descriptor_indexing", "per-draw descriptor set", "REPLACES")],
     "which Vulkan extension retired per-draw descriptor churn on the GPU-driven path",
     "bindless descriptor indexing material table million slot"),
    # --- 44 ---
    ("GPU-driven rendering via ExecuteIndirect on DX12 was preferred over CPU-side draw issuance; the visibility buffer and material resolve passes ran on a single command list.", "preference", "technical", False,
     [("ExecuteIndirect", "api"), ("DX12", "api"), ("CPU-side draw issuance", "pattern"), ("visibility buffer", "technology")],
     [("ExecuteIndirect", "CPU-side draw issuance", "PREFERS")],
     "which DX12 primitive supplanted CPU-side draw issuance",
     "ExecuteIndirect GPU driven visibility buffer material list"),
    # --- 45 ---
    ("GPUOpen's Capsaicin framework was the reference for the studio's GI research; ReSTIR DI and GI integrations shipped as reference implementations alongside ShaderHints.", "reference", "technical", False,
     [("GPUOpen", "organization"), ("Capsaicin", "framework"), ("ReSTIR DI", "algorithm"), ("ShaderHints", "technology")],
     [],
     "which AMD framework anchored the studio's ReSTIR GI reference",
     "GPUOpen Capsaicin ReSTIR DI GI reference ShaderHints"),
    # --- 46 ---
    ("The ReSTIR GI integration replaced the stochastic screen-space integrator on the interior scenes; temporal resampling cut variance at the same sample budget.", "decision", "technical", False,
     [("ReSTIR GI", "algorithm"), ("stochastic screen-space integrator", "algorithm")],
     [("ReSTIR GI", "stochastic screen-space integrator", "IMPROVES_ON")],
     "which GI algorithm improved on the stochastic screen-space integrator",
     "ReSTIR GI temporal resample variance sample budget interior"),
    # --- 47 ---
    ("TAA jitter patterns on the temporal upscaler used the Halton sequence at 8 samples; the Sobol alternative introduced correlation artifacts in flat metallic surfaces.", "decision", "technical", False,
     [("TAA", "technology"), ("Halton sequence", "algorithm"), ("Sobol", "algorithm")],
     [("Halton sequence", "Sobol", "PREFERS")],
     "which jitter sequence beat Sobol on flat metallic TAA surfaces",
     "TAA Halton sequence 8 sample Sobol correlation artifact"),
    # --- 48 ---
    ("The Khronos glTF 2.0 reference with the KHR_materials_transmission extension drove the asset pipeline; USD was used for scene composition, not shading at the boundary.", "reference", "technical", False,
     [("glTF 2.0", "protocol"), ("KHR_materials_transmission", "api"), ("USD", "protocol"), ("Khronos", "organization")],
     [],
     "which asset spec drives shading at the pipeline boundary next to USD",
     "glTF 2.0 KHR materials transmission USD scene composition"),
    # --- 49 ---
    ("Slang shipped as the shader source language on the research branch; its generics and autodiff features improved on HLSL for differentiable rendering prototypes.", "decision", "technical", False,
     [("Slang", "language"), ("HLSL", "language")],
     [("Slang", "HLSL", "IMPROVES_ON")],
     "which shader language improved on HLSL for differentiable rendering",
     "Slang generic autodiff HLSL differentiable research branch"),
    # --- 50 ---
    ("The Hardware Lumen path shipped on 2026-02-14 with RTX 40-series as the tier-1 target; the software Lumen fallback stayed for non-RT Vulkan devices.", "milestone", "technical", False,
     [("Hardware Lumen", "technology"), ("RTX 40-series", "technology"), ("software Lumen", "technology"), ("Vulkan", "api"), ("2026-02-14", "date")],
     [],
     "when did Hardware Lumen ship and which fallback stayed for non-RT devices",
     "Hardware Lumen RTX 40 software fallback Vulkan ship date"),
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
