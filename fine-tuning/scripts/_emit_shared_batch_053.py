"""One-off emitter for shared-base batch-053 — technical domain (compilers / build systems / linkers / package registries at infrastructure level).

Writes 50 rows to data/v2/shared/batch_053.tmp.jsonl with ids shared-02601..02650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_053.tmp.jsonl"
ID_OFFSET = 2600

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("BuildBuddy handled the remote-execution farm for the Bazel monorepo; p95 action wall time halved once the self-hosted executors came online in us-east-2.", "milestone", "technical", False,
     [("BuildBuddy", "service"), ("Bazel", "tool"), ("us-east-2", "place")],
     [],
     "which remote-execution backend cut wall time for the monorepo once self-hosted",
     "remote build farm executor regional fleet wall time halve"),
    # --- 2 ---
    ("EngFlow was evaluated against BuildBuddy for the Bazel RE tier; BuildBuddy won on unit price for our cache-miss profile even though EngFlow had stronger scheduler fairness.", "decision", "technical", False,
     [("EngFlow", "service"), ("BuildBuddy", "service"), ("Bazel", "tool")],
     [("BuildBuddy", "EngFlow", "PREFERS")],
     "which remote-execution vendor lost the bakeoff on unit pricing",
     "vendor compare price fairness scheduler miss profile pick"),
    # --- 3 ---
    ("Buck2 replaced Bazel on the Rust-heavy subtree; Starlark DAG traversal was fine but Buck2's daemon gave a much snappier no-op build on cold caches.", "decision", "technical", False,
     [("Buck2", "tool"), ("Bazel", "tool"), ("Rust", "language"), ("Starlark", "language")],
     [("Buck2", "Bazel", "REPLACES")],
     "which build tool took over the Rust subtree after the Bazel era",
     "daemon no-op cold cache subtree swap incremental build"),
    # --- 4 ---
    ("Hermetic C++ toolchains now come from a Nix derivation pinned by narHash; the Bazel CROSSTOOL no longer pulls the host /usr/bin/clang by accident.", "architecture", "technical", False,
     [("Nix", "tool"), ("Bazel", "tool"), ("CROSSTOOL", "config"), ("clang", "tool")],
     [],
     "how did the monorepo stop leaking the host compiler into hermetic Bazel builds",
     "toolchain derivation pinned hash crosstool host leak fix"),
    # --- 5 ---
    ("mold 2.4 swapped in for lld on the release link step; a 1.2 GB server binary linked in 3.1 seconds versus 11 with lld on the same box.", "milestone", "technical", False,
     [("mold 2.4", "tool"), ("lld", "tool")],
     [("mold 2.4", "lld", "REPLACES")],
     "which linker took over the release link step and how much did wall time drop",
     "parallel linker speed release binary wall time compare"),
    # --- 6 ---
    ("lld stayed on the Apple Silicon builders because mold's Mach-O support was still experimental at the time of the cutover window.", "fact", "technical", False,
     [("lld", "tool"), ("mold", "tool"), ("Mach-O", "pattern"), ("Apple Silicon", "technology")],
     [],
     "which linker kept the macOS builds because the replacement lacked format support",
     "Mach-O experimental macOS build keep linker stay gap"),
    # --- 7 ---
    ("sccache with an S3 backend cut a cold Rust CI run from 22 minutes to 7; the local redis layer we tried first choked at four concurrent workers.", "decision", "technical", False,
     [("sccache", "tool"), ("S3", "service"), ("Rust", "language"), ("redis", "database")],
     [("sccache", "redis", "REPLACES")],
     "which cache backend finally made the Rust CI run consistently fast",
     "compiler cache object store cold CI minute drop backend"),
    # --- 8 ---
    ("ccache 4.9's depend_mode let us share the cache across clang-format-driven header reshuffles; hit rate rose from 61 to 88 percent on the core repo.", "milestone", "technical", False,
     [("ccache 4.9", "tool"), ("clang-format", "tool")],
     [],
     "which ccache mode restored cache hits across header reshuffles",
     "dependency mode cache hit rate header shuffle formatter"),
    # --- 9 ---
    ("distcc-over-ssh was retired once the mesh tailnet delivered low-latency direct links; sccache+S3 carried the remote compile load without the middle hop.", "decision", "technical", False,
     [("distcc", "tool"), ("ssh", "protocol"), ("tailnet", "infrastructure"), ("sccache", "tool"), ("S3", "service")],
     [("sccache", "distcc", "REPLACES")],
     "which remote compile setup retired after the mesh VPN rolled out",
     "retire tunnel direct link mesh VPN middle hop drop"),
    # --- 10. noise ---
    ("Hold on, my laptop fan just spun up again.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Ninja generators replaced the Make fallbacks in the CMake preset; the no-op rebuild on a warm tree dropped from 2.3 seconds to 180 milliseconds.", "decision", "technical", False,
     [("Ninja", "tool"), ("Make", "tool"), ("CMake", "tool")],
     [("Ninja", "Make", "REPLACES")],
     "which build generator took over from Make in the preset flow",
     "generator swap warm rebuild no-op millisecond preset"),
    # --- 12 ---
    ("CMake presets with CMAKE_EXPORT_COMPILE_COMMANDS=ON standardised the compile_commands.json drop; clangd-based editors stopped drifting across developer laptops.", "architecture", "technical", False,
     [("CMake", "tool"), ("CMAKE_EXPORT_COMPILE_COMMANDS", "config"), ("compile_commands.json", "file"), ("clangd", "tool")],
     [],
     "which CMake settings kept editor index files consistent across developer machines",
     "preset compile commands export index editor stable drop"),
    # --- 13 ---
    ("Zig 0.13's cross-compile mode became our glibc-targeting linker-and-libc wrapper; a single host toolchain covered five target triples that used to need sysroots.", "milestone", "technical", False,
     [("Zig 0.13", "tool"), ("glibc", "library")],
     [],
     "which toolchain collapsed five cross-compile sysroots into a single host installation",
     "cross target triple sysroot collapse host wrapper libc"),
    # --- 14 ---
    ("Zig's ld.lld alternative shipped the Linux cross-link for aarch64 targets; the vendored ld from the old SDK was purged from the repository entirely.", "decision", "technical", False,
     [("Zig", "tool"), ("ld.lld", "tool"), ("aarch64", "technology")],
     [("Zig", "ld.lld", "USES")],
     "which wrapper around ld.lld handled the aarch64 cross link for Linux builds",
     "vendored SDK purge cross link arm64 alternative ship"),
    # --- 15 ---
    ("The Reproducible Builds project's 2021 SOURCE_DATE_EPOCH spec still anchors our packaging guidelines; the normative behaviour for timestamp fallbacks is cited verbatim in the release runbook.", "reference", "technical", False,
     [("Reproducible Builds", "project"), ("SOURCE_DATE_EPOCH", "config"), ("2021", "date")],
     [],
     "which upstream specification anchors the SOURCE_DATE_EPOCH rules in the release runbook",
     "canonical spec timestamp fallback normative behaviour cite"),
    # --- 16 ---
    ("Position-Independent Executables became mandatory for the Debian 13 release tier; hardening scripts now flake the build when -fPIE is absent from CFLAGS.", "decision", "technical", False,
     [("Debian 13", "platform"), ("-fPIE", "config")],
     [],
     "which hardening requirement gates the Debian 13 release build on PIE flags",
     "position independent executable mandatory flag hardening gate"),
    # --- 17 ---
    ("Debug info split via objcopy --only-keep-debug and a strip pass landed on the release pipeline; the shipped artefact dropped 140 MB without losing crash symbolication.", "architecture", "technical", False,
     [("objcopy", "tool"), ("strip", "command")],
     [],
     "how did the release pipeline shed debug weight without losing crash symbolisation",
     "split keep debug info strip artefact size symbolicate"),
    # --- 18 ---
    ("tsan and ubsan opt-in builds now run nightly on a dedicated Bazel config; the release pipeline stays asan-free because of the 2x runtime cost.", "architecture", "technical", False,
     [("tsan", "tool"), ("ubsan", "tool"), ("Bazel", "tool"), ("asan", "tool")],
     [],
     "which sanitizers run nightly on Bazel without weighing the release pipeline down",
     "thread undefined behavior nightly sanitizer optional release"),
    # --- 19 ---
    ("msan adoption stalled on the Rust crates because third-party C dependencies lacked instrumented builds; we scoped msan to the pure-C subtree for now.", "problem", "technical", False,
     [("msan", "tool"), ("Rust", "language"), ("C", "language")],
     [],
     "why is msan scoped to only the C subtree and not the Rust crates",
     "memory sanitizer third party instrument gap crate scope"),
    # --- 20 ---
    ("AutoFDO samples from production profiled a month of live traffic; the PGO relink improved request p99 by 9 percent and cut icache misses noticeably.", "milestone", "technical", False,
     [("AutoFDO", "tool"), ("PGO", "method")],
     [],
     "which profile-feedback flow delivered the production p99 latency win",
     "profile feedback sample live traffic relink latency instruction cache"),
    # --- 21 ---
    ("Propeller layout on top of AutoFDO trimmed another 3 percent off p99 once we wired the BOLT-style post-link layout into the release script.", "milestone", "technical", False,
     [("Propeller", "tool"), ("AutoFDO", "tool"), ("BOLT", "tool")],
     [("Propeller", "AutoFDO", "BUILDS_ON")],
     "which post-link layout tool stacked extra latency gains on top of AutoFDO",
     "post link layout latency percent additional gain stack"),
    # --- 22 ---
    ("Full LTO was reserved for the yearly hardening release after the nightly relink times blew past the 45-minute budget; ThinLTO stayed on daily CI.", "preference", "technical", False,
     [("Full LTO", "algorithm"), ("ThinLTO", "algorithm")],
     [],
     "which LTO mode handles the yearly hardening release despite the long relink",
     "link time optimization yearly hardening budget nightly relink"),
    # --- 23 ---
    ("SOURCE_DATE_EPOCH threaded through the Debian, Nix, and npm package outputs; diffoscope stopped flagging timestamp-only variance across identical-input rebuilds.", "architecture", "technical", False,
     [("SOURCE_DATE_EPOCH", "config"), ("Debian", "platform"), ("Nix", "tool"), ("npm", "service"), ("diffoscope", "tool")],
     [],
     "which environment variable silenced timestamp-only diffoscope noise across packagers",
     "epoch packagers timestamp reproducible identical input diff"),
    # --- 24 ---
    ("Nix store path hashing caught a hidden dependency on the host's OpenSSL 3.2; the narHash diverged between builders until the derivation pinned libssl explicitly.", "problem", "technical", False,
     [("Nix", "tool"), ("OpenSSL 3.2", "library"), ("libssl", "library")],
     [],
     "which hashing mechanism exposed the hidden host OpenSSL leak in the derivation",
     "store hash host dependency leak divergence pin libssl"),
    # --- 25 ---
    ("Guix ran alongside Nix on the reproducibility bench; Guix won on bit-for-bit results for Scheme-heavy packages while Nix kept the Python data-science closures.", "preference", "technical", False,
     [("Guix", "tool"), ("Nix", "tool"), ("Scheme", "language"), ("Python", "language")],
     [],
     "which packager handled Scheme-heavy closures better on the bit-for-bit bench",
     "reproducibility bench compare Scheme Python closure prefer"),
    # --- 26 ---
    ("Debian's reproducible-builds initiative landed certification for 96 percent of the server base image on 2026-03-04; the remaining drift came from two Go binaries with buildid leakage.", "milestone", "technical", False,
     [("Debian", "platform"), ("reproducible-builds", "project"), ("2026-03-04", "date"), ("Go", "language")],
     [],
     "when did the Debian base image cross 96 percent reproducible coverage",
     "certification percent date base image Go buildid leakage remain"),
    # --- 27 ---
    ("Content-addressable build outputs under Bazel's remote_cache=grpcs backend let two geographic sites share artefacts without registry replication lag.", "architecture", "technical", False,
     [("Bazel", "tool"), ("remote_cache", "config"), ("grpcs", "protocol")],
     [],
     "how did two geographic sites share Bazel outputs without waiting on a registry sync",
     "content address remote cache geographic share replication lag"),
    # --- 28 ---
    ("JFrog Artifactory carried the binary promotion pipeline from dev to staging to prod; release signatures stay pinned to the build_info document per stage.", "architecture", "technical", False,
     [("JFrog Artifactory", "service"), ("build_info", "file")],
     [],
     "which registry carries the dev-staging-prod binary promotion with signed build metadata",
     "promotion registry stage dev staging prod signature pipeline"),
    # --- 29 ---
    ("Cloudsmith replaced a self-hosted Sonatype Nexus for the Maven and npm registries; the ops burden of Nexus HA clusters stopped justifying the licence savings.", "decision", "technical", False,
     [("Cloudsmith", "service"), ("Sonatype Nexus", "service"), ("Maven", "tool"), ("npm", "service")],
     [("Cloudsmith", "Sonatype Nexus", "REPLACES")],
     "which managed registry took over from the self-hosted Nexus cluster",
     "managed registry self host HA cluster licence burden swap"),
    # --- 30 ---
    ("Local Verdaccio mirror in front of the public npm registry kept offline laptops building; cache prewarm on every dependabot merge cut first-fetch latency for new deps.", "architecture", "technical", False,
     [("Verdaccio", "service"), ("npm", "service"), ("dependabot", "service")],
     [],
     "which local npm mirror kept offline developer laptops productive",
     "offline mirror cache prewarm dependency merge first fetch"),
    # --- 31 ---
    ("PyPI mirror via devpi on a homelab box fed the restricted-network CI runners; wheel caches rebuild nightly from the upstream simple index.", "architecture", "technical", False,
     [("devpi", "tool"), ("PyPI", "service")],
     [],
     "which PyPI proxy fed the air-gapped CI runners from the homelab",
     "proxy homelab restricted network wheel cache rebuild index"),
    # --- 32 ---
    ("Local Cargo mirror using panamax caught the leftpad-style yank incident last week; builds stayed reproducible because yanked crates remained cached locally.", "problem", "technical", False,
     [("panamax", "tool"), ("Cargo", "tool")],
     [],
     "which local Rust mirror shielded the org from the upstream crate yank event",
     "mirror yank incident cache reproducible crate local copy"),
    # --- 33 ---
    ("Sigstore cosign signing landed on the npm publish step for the public SDK; rekor transparency logs cross-reference to the GitHub Actions workflow run.", "architecture", "technical", False,
     [("cosign", "tool"), ("npm", "service"), ("rekor", "service"), ("GitHub Actions", "service")],
     [],
     "which signing flow now backs the public npm SDK releases with a transparency log",
     "signature transparency log publish cross reference workflow run"),
    # --- 34. noise ---
    ("Anyway, who moved my coffee cup.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Gradle remote build cache migrated from the S3-backed bucket to Develocity's managed node; build-scan analytics made regressions far easier to bisect than the raw object store logs.", "decision", "technical", False,
     [("Gradle", "tool"), ("Develocity", "service"), ("S3", "service")],
     [("Develocity", "S3", "REPLACES")],
     "which managed cache replaced the S3 Gradle cache and why",
     "managed build cache analytics bisect regression swap object store"),
    # --- 36 ---
    ("mill replaced sbt for the new Scala services; sbt's incremental compiler quirks on cold clones of the CI shards made mill's straight-line task graph the easier sell.", "decision", "technical", False,
     [("mill", "tool"), ("sbt", "tool"), ("Scala", "language")],
     [("mill", "sbt", "REPLACES")],
     "which Scala build tool took over from sbt on the CI shards",
     "incremental compiler cold clone task graph straight line swap"),
    # --- 37 ---
    ("sbt stayed on the Akka-based legacy services; the plugin surface area we depend on would need a full rewrite to land on mill, and the maintenance is already freezing.", "fact", "technical", False,
     [("sbt", "tool"), ("Akka", "framework"), ("mill", "tool")],
     [],
     "which build tool stayed on the frozen Akka legacy services and why",
     "plugin surface legacy maintenance freeze migration cost wait"),
    # --- 38 ---
    ("Cargo workspaces with shared target directory cut a fresh checkout compile on the monorepo from 14 minutes to 6; sccache piled the rest of the gains on top.", "milestone", "technical", False,
     [("Cargo", "tool"), ("sccache", "tool")],
     [("Cargo", "sccache", "USES")],
     "which Cargo structure plus cache combo delivered the compile-time drop",
     "workspace shared target fresh checkout compile minute drop"),
    # --- 39 ---
    ("buck2 on the Rust subtree outran Cargo workspaces when the dep graph crossed 1200 crates; Cargo's serial resolver was the bottleneck not the compiler.", "preference", "technical", False,
     [("buck2", "tool"), ("Cargo", "tool"), ("Rust", "language")],
     [("buck2", "Cargo", "PREFERS")],
     "which Rust build tool took the 1200-crate subtree ahead of Cargo",
     "large graph crate resolver serial bottleneck compile split"),
    # --- 40 ---
    ("Bazel remote_download_outputs=minimal plus BwoB on BuildBuddy stopped materialising intermediate artefacts on developer laptops; disk pressure on the dev fleet dropped sharply.", "architecture", "technical", False,
     [("Bazel", "tool"), ("remote_download_outputs", "config"), ("BwoB", "config"), ("BuildBuddy", "service")],
     [],
     "which Bazel flag pair kept developer laptops from downloading intermediate artefacts",
     "build without bytes minimal output laptop disk pressure drop"),
    # --- 41 ---
    ("Gradle configuration cache combined with the Develocity predictive test selection trimmed CI dollar cost; the accountant stopped asking about the Android build bill.", "milestone", "technical", False,
     [("Gradle", "tool"), ("Develocity", "service"), ("Android", "platform")],
     [],
     "which Gradle features cut the CI dollar cost for the Android build",
     "configuration cache predictive test selection bill drop dollar"),
    # --- 42 ---
    ("CMake FetchContent was retired in favour of a CPM cache prewarm step; reproducibility suffered when a GitHub tag got force-moved upstream and slipped past the SHA pin.", "decision", "technical", False,
     [("CMake", "tool"), ("FetchContent", "tool"), ("CPM", "tool"), ("GitHub", "service")],
     [("CPM", "FetchContent", "REPLACES")],
     "which CMake dependency fetcher was swapped out after the upstream tag move",
     "fetch content package manager tag move SHA pin slip swap"),
    # --- 43 ---
    ("Bazel hermetic Python toolchain landed via rules_python on 2026-02-27; the shared PyPI mirror still fed wheels but interpreter binaries no longer came from the host.", "milestone", "technical", False,
     [("Bazel", "tool"), ("rules_python", "library"), ("PyPI", "service"), ("2026-02-27", "date")],
     [],
     "when did the Bazel Python toolchain stop pulling the interpreter from the host",
     "hermetic interpreter rules language date mirror wheel host"),
    # --- 44 ---
    ("rules_rust with the prebuilt toolchain URL replaced the in-tree rustc_binary pattern; CI warm-cache startup shaved 90 seconds without giving up the pinned channel.", "decision", "technical", False,
     [("rules_rust", "library"), ("rustc_binary", "pattern")],
     [("rules_rust", "rustc_binary", "REPLACES")],
     "which rules layout took over the Rust toolchain on CI and why",
     "prebuilt toolchain URL warm cache startup pin channel swap"),
    # --- 45 ---
    ("Nix flakes locked the C++ toolchain for embedded firmware; CI builders reproduce the same gcc-arm-none-eabi 13.2.1 down to patch level without a vendored tarball.", "architecture", "technical", False,
     [("Nix", "tool"), ("gcc-arm-none-eabi 13.2.1", "tool")],
     [],
     "which packaging mechanism locks the embedded C++ toolchain down to the patch version",
     "flake embedded firmware pin patch level vendored tarball skip"),
    # --- 46 ---
    ("Guix channel file pinned reproducibility for the scientific Python stack; colleagues cloning the repo get an identical numpy and BLAS layout without conda-forge drift.", "architecture", "technical", False,
     [("Guix", "tool"), ("Python", "language"), ("numpy", "library"), ("BLAS", "library"), ("conda-forge", "service")],
     [],
     "which packaging mechanism holds the scientific Python stack identical across collaborators",
     "channel file scientific stack math library drift free collaborator"),
    # --- 47 ---
    ("Release signing keys moved from local Yubikeys into a Fulcio-backed keyless flow; engineers no longer wait on a keyholder to sign the weekly Cargo publish.", "decision", "technical", False,
     [("Yubikey", "technology"), ("Fulcio", "service"), ("Cargo", "tool")],
     [("Fulcio", "Yubikey", "REPLACES")],
     "which signing mechanism replaced the hardware-key step in the weekly publish",
     "keyless sign hardware token weekly release wait remove swap"),
    # --- 48 ---
    ("Artifact promotion gate on the Conan registry enforced SBOM attachment; CycloneDX JSON alongside the .tgz is verified before the staging tag is applied.", "architecture", "technical", False,
     [("Conan", "tool"), ("SBOM", "concept"), ("CycloneDX", "pattern")],
     [],
     "which artifact gate requires a CycloneDX SBOM before staging promotion",
     "SBOM attach promotion registry verify staging tag gate"),
    # --- 49 ---
    ("Linker-level dead-code elimination via -ffunction-sections plus -Wl,--gc-sections trimmed the embedded image by 22 percent; the IAP bootloader could finally keep its reserved sector.", "milestone", "technical", False,
     [("-ffunction-sections", "config"), ("-Wl,--gc-sections", "config"), ("IAP", "protocol")],
     [],
     "which compiler-linker flag pair shaved the embedded image to fit the bootloader sector",
     "dead code elimination function section image size bootloader fit"),
    # --- 50 ---
    ("Hermetic CUDA toolchain via rules_cuda and a Bazel repo_env pin landed on 2026-04-02; the GPU test farm now reproduces driver-version-sensitive failures that bit us in January.", "milestone", "technical", False,
     [("CUDA", "technology"), ("rules_cuda", "library"), ("Bazel", "tool"), ("2026-04-02", "date")],
     [("rules_cuda", "Bazel", "USES")],
     "when did the hermetic CUDA toolchain land on the Bazel GPU test farm",
     "GPU hermetic driver version pin reproduce farm test date"),
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
