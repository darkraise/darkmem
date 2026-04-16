"""One-off emitter for shared-base batch-177 — technical domain (performance profiling and tracing: perf, eBPF, bpftrace, pprof, py-spy, async-profiler, VTune, Nsight, rr, flamegraphs, Pyroscope, Parca).

Writes 50 rows to data/v2/shared/batch_177.tmp.jsonl with ids shared-08801..08850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_177.tmp.jsonl"
ID_OFFSET = 8800

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Swapped the production profiler stack from Linux perf sampling to Parca continuous profiling; the always-on eBPF agent replaces ad-hoc perf record sessions and the flamegraphs are queryable by label.", "decision", "technical", False,
     [("Linux perf", "tool"), ("Parca", "service"), ("eBPF", "technology"), ("flamegraphs", "concept")],
     [("Parca", "Linux perf", "REPLACES"), ("Parca", "eBPF", "USES")],
     "which continuous profiler replaced ad-hoc perf record sessions and what agent tech does it rely on",
     "parca perf ebpf continuous profile flamegraph label queryable"),
    # --- 2 architecture ---
    ("The observability tier layers Pyroscope for always-on CPU profiles on top of OpenTelemetry traces; click a slow span in Jaeger and the linked flamegraph opens at the exact time window.", "architecture", "technical", False,
     [("Pyroscope", "service"), ("OpenTelemetry", "framework"), ("Jaeger", "tool"), ("flamegraph", "concept")],
     [("Pyroscope", "OpenTelemetry", "COMMUNICATES_WITH"), ("Jaeger", "Pyroscope", "USES")],
     "how does the observability stack link a slow Jaeger span to a concrete CPU flamegraph",
     "pyroscope opentelemetry jaeger flamegraph span profile link time"),
    # --- 3 fact ---
    ("bpftrace one-liners dominate the SRE runbook for quick syscall breakdowns; the canonical offcputime.bt script from Brendan Gregg's BCC collection pins blocked stacks by kernel wait reason.", "fact", "technical", False,
     [("bpftrace", "tool"), ("BCC", "library"), ("offcputime.bt", "file"), ("Brendan Gregg", "person")],
     [("bpftrace", "BCC", "RELATED_TO"), ("offcputime.bt", "Brendan Gregg", "AUTHORED_BY")],
     "which bpftrace script attributes blocked stacks to kernel wait reasons in the SRE runbook",
     "bpftrace bcc offcputime brendan gregg kernel wait block stack"),
    # --- 4 decision ---
    ("Chose py-spy over cProfile for the Django workers; sampling without instrumenting the interpreter avoided the fork-bomb that cProfile's deterministic tracing caused under gunicorn preload.", "decision", "technical", False,
     [("py-spy", "tool"), ("cProfile", "library"), ("Django", "framework"), ("gunicorn", "service")],
     [("py-spy", "cProfile", "REPLACES"), ("py-spy", "Django", "APPLIES_TO")],
     "which Python profiler replaced cProfile for Django workers and what issue did it sidestep",
     "py spy cprofile django gunicorn preload sample fork tracing"),
    # --- 5 milestone ---
    ("Shipped continuous profiling for the Go fleet on 2026-03-20; pprof heap and CPU samples now stream to Pyroscope every ten seconds via the Parca agent on each node.", "milestone", "technical", False,
     [("Go", "language"), ("pprof", "tool"), ("Pyroscope", "service"), ("Parca", "service"), ("2026-03-20", "date")],
     [("Parca", "Pyroscope", "COMMUNICATES_WITH"), ("Go", "pprof", "USES")],
     "when did continuous profiling roll out to the Go fleet and how often do samples ship",
     "go pprof pyroscope parca continuous profile march 2026 ship fleet"),
    # --- 6 reference ---
    ("Brendan Gregg's USE method — Utilisation, Saturation, Errors — anchors the first-pass triage; every on-call runbook points at the same method for narrowing a resource hotspot.", "reference", "technical", False,
     [("USE method", "method"), ("Brendan Gregg", "person"), ("on-call runbook", "publication")],
     [("USE method", "Brendan Gregg", "AUTHORED_BY")],
     "which triage method anchors the first pass of on-call hotspot narrowing and who authored it",
     "use method utilisation saturation errors brendan gregg runbook triage"),
    # --- 7 problem ---
    ("perf record on the bare-metal DB box was missing kernel stacks because CONFIG_FRAME_POINTER was off; rebuilt the kernel with frame pointers and the flamegraph finally attributed IO waits.", "problem", "technical", False,
     [("perf record", "command"), ("CONFIG_FRAME_POINTER", "config"), ("flamegraph", "concept")],
     [("CONFIG_FRAME_POINTER", "perf record", "CONFIGURES")],
     "which kernel config knob was missing that broke perf record's kernel stacks on the DB box",
     "perf record config frame pointer kernel stack flamegraph io wait"),
    # --- 8 architecture ---
    ("The JVM services embed async-profiler as an agent and dump JFR files to S3 every five minutes; JMC is the analysis entrypoint for anyone needing a lock-contention breakdown.", "architecture", "technical", False,
     [("async-profiler", "tool"), ("JFR", "technology"), ("JMC", "tool"), ("S3", "service"), ("JVM", "platform")],
     [("async-profiler", "JFR", "PRODUCES"), ("JMC", "JFR", "USES")],
     "how do the JVM services persist async-profiler output and which UI analyses the files",
     "async profiler jfr jmc jvm s3 dump lock contention agent embed"),
    # --- 9 decision ---
    ("Picked Intel VTune over perf for the vector-kernel team; VTune's memory-access analysis highlighted L2 misses that perf's counters couldn't attribute back to the inlined AVX-512 loop.", "decision", "technical", False,
     [("Intel VTune", "tool"), ("perf", "tool"), ("AVX-512", "technology"), ("L2", "concept")],
     [("Intel VTune", "perf", "PREFERS")],
     "which profiler did the vector-kernel team pick over perf and which analysis swung the choice",
     "intel vtune perf avx 512 memory access l2 cache miss inline loop"),
    # --- 10 noise ---
    ("The office coffee machine started beeping an error code at 3 pm every day and nobody on the floor could figure out why.", "fact", "noise", True, [], [], None, None),
    # --- 11 architecture ---
    ("Differential flamegraphs drive release-over-release regression detection; the pipeline captures a baseline and candidate pprof profile per build then renders a red-green diff SVG checked into the artefact store.", "architecture", "technical", False,
     [("Differential flamegraphs", "concept"), ("pprof", "tool"), ("SVG", "technology"), ("artefact store", "infrastructure")],
     [("Differential flamegraphs", "pprof", "USES")],
     "which flamegraph variant drives release regression detection and what format lands in the artefact store",
     "differential flamegraph pprof svg baseline candidate regression diff"),
    # --- 12 fact ---
    ("Linux ftrace exposes the function_graph tracer that records entry and exit of every kernel function matching a filter; it's the first tool the kernel team reaches for when bisecting a scheduling regression.", "fact", "technical", False,
     [("Linux ftrace", "tool"), ("function_graph", "method")],
     [("Linux ftrace", "function_graph", "HAS_PART")],
     "which ftrace tracer logs kernel function entry and exit and where does the kernel team use it",
     "ftrace function graph kernel bisect schedule regression entry exit"),
    # --- 13 decision ---
    ("Adopted rr record/replay for the intermittent auth crash that only reproduced once per thousand runs; the deterministic replay collapsed a week of bisecting into an afternoon of reverse-continue.", "decision", "technical", False,
     [("rr", "tool"), ("reverse-continue", "method"), ("auth crash", "error")],
     [("rr", "auth crash", "APPLIES_TO")],
     "which record-replay tool unblocked the rare auth crash and what debugger feature sealed the deal",
     "rr record replay auth crash reverse continue bisect deterministic"),
    # --- 14 milestone ---
    ("CUDA kernels get profiled with NVIDIA Nsight Compute for per-kernel occupancy, then Nsight Systems strings the kernels together with the host timeline so launch latency is actually visible.", "milestone", "technical", False,
     [("NVIDIA Nsight Compute", "tool"), ("Nsight Systems", "tool"), ("CUDA", "technology")],
     [("NVIDIA Nsight Compute", "CUDA", "APPLIES_TO"), ("Nsight Systems", "CUDA", "APPLIES_TO")],
     "how does the CUDA team combine per-kernel and system-wide profilers to see launch latency",
     "nvidia nsight compute systems cuda kernel occupancy host timeline"),
    # --- 15 preference ---
    ("The platform team prefers scalene over cProfile for mixed Python and NumPy workloads; line-level split between Python time, native time, and GPU time makes C-extension hotspots obvious.", "preference", "technical", False,
     [("scalene", "tool"), ("cProfile", "library"), ("NumPy", "library"), ("Python", "language")],
     [("scalene", "cProfile", "PREFERS")],
     "which Python profiler does the platform team prefer for mixed NumPy workloads and why",
     "scalene cprofile numpy python line level native gpu hotspot extension"),
    # --- 16 decision ---
    ("strace attach slowed the production request path by 40x because every syscall ptraces into the tracer; moved the investigation to bpftrace probes that stayed in-kernel and cost under two percent.", "decision", "technical", False,
     [("strace", "tool"), ("bpftrace", "tool"), ("ptrace", "method")],
     [("bpftrace", "strace", "REPLACES")],
     "which syscall tracer tanked production latency and which in-kernel alternative replaced it",
     "strace bpftrace ptrace syscall production latency slow kernel probe"),
    # --- 17 decision ---
    ("Standardised on Brendan Gregg's TSA method — Thread State Analysis — for latency investigations; off-CPU flamegraphs became the required artefact before any scheduler tuning PR merges.", "decision", "technical", False,
     [("TSA method", "method"), ("Brendan Gregg", "person"), ("off-CPU flamegraphs", "concept")],
     [("TSA method", "Brendan Gregg", "AUTHORED_BY"), ("off-CPU flamegraphs", "TSA method", "APPLIES_TO")],
     "which analysis method does the team require before merging any scheduler tuning change",
     "tsa thread state analysis brendan gregg off cpu flamegraph scheduler"),
    # --- 18 reference ---
    ("viztracer wraps the nightly integration suite; each test produces a perfetto-compatible JSON that ops loads into ui.perfetto.dev to hunt the outlier spans without rerunning the suite.", "reference", "technical", False,
     [("viztracer", "tool"), ("perfetto", "tool"), ("ui.perfetto.dev", "service"), ("integration suite", "project")],
     [("viztracer", "perfetto", "PRODUCES")],
     "which tracer instruments the nightly suite and which UI do ops use to hunt outlier spans",
     "viztracer perfetto nightly integration test json outlier span ui"),
    # --- 19 milestone ---
    ("Closed the quarter by landing Intel PT capture on the lab fleet; branch-level traces now feed hotspot's decoder and the team can rewind a SIGSEGV to its mispredicted indirect call.", "milestone", "technical", False,
     [("Intel PT", "technology"), ("hotspot", "tool"), ("SIGSEGV", "error"), ("lab fleet", "infrastructure")],
     [("hotspot", "Intel PT", "USES")],
     "which branch-level trace tech landed on the lab fleet and which decoder consumes it",
     "intel pt hotspot branch trace lab fleet sigsegv mispredict indirect"),
    # --- 20 reference ---
    ("The perf-tools repository from Netflix is still the canonical reference for the older ftrace wrappers; iosnoop and execsnoop ship in every internal toolbox image.", "reference", "technical", False,
     [("perf-tools", "publication"), ("Netflix", "organization"), ("iosnoop", "tool"), ("execsnoop", "tool"), ("ftrace", "tool")],
     [("perf-tools", "Netflix", "AUTHORED_BY"), ("iosnoop", "ftrace", "USES")],
     "which legacy ftrace wrapper collection ships in every internal toolbox and who authored it",
     "perf tools netflix iosnoop execsnoop ftrace toolbox image reference"),
    # --- 21 fact ---
    ("CPU sampling at 99 Hz avoids the 100 Hz tick-harmonic that produced the phantom hotspot in scheduler_tick; the SRE default in the perf wrapper script is 99 since then.", "fact", "technical", False,
     [("CPU sampling", "method"), ("perf wrapper script", "file"), ("scheduler_tick", "method")],
     [("perf wrapper script", "CPU sampling", "CONFIGURES")],
     "which sampling frequency became the SRE default after the tick-harmonic phantom hotspot incident",
     "cpu sample 99 hz tick harmonic scheduler tick phantom hotspot perf"),
    # --- 22 preference ---
    ("Austin samples the long-running Celery workers in shadow mode: a sidecar reads /proc maps, attributes frames to functions, and emits to the same Pyroscope endpoint as the Go services.", "preference", "technical", False,
     [("Austin", "tool"), ("Celery", "framework"), ("Pyroscope", "service"), ("/proc maps", "file")],
     [("Austin", "Celery", "APPLIES_TO"), ("Austin", "Pyroscope", "COMMUNICATES_WITH")],
     "how does austin sample Celery workers without touching the interpreter and where do frames land",
     "austin celery pyroscope proc maps sidecar shadow frame sample worker"),
    # --- 23 decision ---
    ("Rejected JMC as the day-to-day JVM console in favour of the async-profiler web UI; JMC stays on bench for deep JFR forensic work after an incident, not during live triage.", "decision", "technical", False,
     [("JMC", "tool"), ("async-profiler", "tool"), ("JFR", "technology")],
     [("async-profiler", "JMC", "PREFERS")],
     "which JVM profiler UI won live triage and which stayed as post-incident forensic tool",
     "jmc async profiler jfr live triage forensic jvm console bench"),
    # --- 24 fact ---
    ("Nsight Systems captures were 14 GB per minute on the GH200 box because NVTX ranges fired per element; coarsened the ranges to per-batch and the capture dropped to 200 MB per minute.", "fact", "technical", False,
     [("Nsight Systems", "tool"), ("NVTX", "api"), ("GH200", "platform")],
     [("NVTX", "Nsight Systems", "CONFIGURES")],
     "which NVTX granularity blew up Nsight Systems captures on GH200 and how was it fixed",
     "nsight systems nvtx gh200 range per element batch capture size"),
    # --- 25 architecture ---
    ("The icicle-graph renderer in the internal dashboard flips Brendan Gregg's flamegraph upside down; operators find the root span faster when the entry point sits at the top.", "architecture", "technical", False,
     [("icicle-graph", "concept"), ("flamegraph", "concept"), ("Brendan Gregg", "person")],
     [("icicle-graph", "flamegraph", "IMPROVES_ON")],
     "which inverted flamegraph variant does the internal dashboard render for faster root-span reading",
     "icicle graph flamegraph brendan gregg invert root span dashboard"),
    # --- 26 decision ---
    ("Replaced ltrace with bpftrace uprobes on the glibc symbols we cared about; ltrace's PLT hooking missed calls in the PGO-optimised binary while uprobes resolved them via DWARF.", "decision", "technical", False,
     [("ltrace", "tool"), ("bpftrace", "tool"), ("uprobes", "method"), ("PGO", "technology"), ("DWARF", "technology")],
     [("bpftrace", "ltrace", "REPLACES"), ("uprobes", "DWARF", "USES")],
     "which tracer replaced ltrace for PGO binaries and which symbol source made it work",
     "ltrace bpftrace uprobe plt pgo dwarf glibc symbol tracer resolve"),
    # --- 27 fact ---
    ("LBR — Last Branch Record — on Intel CPUs gives you the most recent 32 branches without full Intel PT; perf record with --call-graph lbr produced usable flamegraphs even in frame-pointer-less binaries.", "fact", "technical", False,
     [("LBR", "technology"), ("Intel PT", "technology"), ("perf record", "command")],
     [("perf record", "LBR", "USES")],
     "which Intel CPU feature produces a 32-branch trace for perf without needing full Intel PT",
     "lbr last branch record intel perf record call graph frame pointer"),
    # --- 28 architecture ---
    ("On-CPU and off-CPU flamegraphs render as a two-panel side-by-side in the incident review template; reviewers can spot whether latency came from compute or from a blocking syscall at a glance.", "architecture", "technical", False,
     [("On-CPU", "concept"), ("off-CPU flamegraphs", "concept"), ("incident review template", "publication")],
     [("incident review template", "On-CPU", "USES"), ("incident review template", "off-CPU flamegraphs", "USES")],
     "which two flamegraph variants sit side by side in the incident review template and why",
     "on cpu off cpu flamegraph incident review two panel latency block"),
    # --- 29 preference ---
    ("Team lead prefers hotspot over the command-line perf report for call-graph browsing; the Qt UI makes LBR traces navigable where perf report only shows flat tables.", "preference", "technical", False,
     [("hotspot", "tool"), ("perf report", "command"), ("LBR", "technology"), ("Qt", "framework")],
     [("hotspot", "perf report", "PREFERS")],
     "which perf analysis UI does the team lead prefer over perf report and why",
     "hotspot perf report qt lbr ui call graph browse flat table"),
    # --- 30 milestone ---
    ("Turned on always-on eBPF sampling across the Kubernetes fleet on 2026-02-10; the Parca DaemonSet added under two percent CPU overhead and unlocked fleet-wide flamegraph search.", "milestone", "technical", False,
     [("eBPF", "technology"), ("Kubernetes", "platform"), ("Parca", "service"), ("DaemonSet", "pattern"), ("2026-02-10", "date")],
     [("Parca", "Kubernetes", "DEPLOYED_ON"), ("Parca", "eBPF", "USES")],
     "when did always-on eBPF sampling land on the Kubernetes fleet and what was the CPU overhead",
     "ebpf kubernetes parca daemonset sampling fleet february 2026 overhead"),
    # --- 31 decision ---
    ("Go runtime/pprof's allocation profile underreported short-lived objects because the default rate is 512 KB; dropped runtime.MemProfileRate to 1 and the GC-pressure investigation finally had signal.", "decision", "technical", False,
     [("runtime/pprof", "library"), ("runtime.MemProfileRate", "config"), ("Go", "language"), ("GC", "concept")],
     [("runtime.MemProfileRate", "runtime/pprof", "CONFIGURES")],
     "which Go runtime knob hid short-lived allocations from pprof and what value unblocked the GC investigation",
     "runtime pprof memprofilerate go gc pressure short lived allocation 512"),
    # --- 32 architecture ---
    ("Pyroscope stores profiles in its own columnar format and queries them by label selector, exactly like Prometheus metrics; the shared label schema means alerts and flamegraphs share selectors.", "architecture", "technical", False,
     [("Pyroscope", "service"), ("Prometheus", "service"), ("label selector", "concept")],
     [("Pyroscope", "Prometheus", "IMPROVES_ON"), ("Pyroscope", "label selector", "USES")],
     "how does Pyroscope align its query model with Prometheus so alerts and flamegraphs share selectors",
     "pyroscope prometheus label selector columnar profile alert flamegraph"),
    # --- 33 reference ---
    ("Brendan Gregg's \"Systems Performance\" second edition is the standing recommendation for new SREs; chapter 6 on CPUs is required reading before touching the perf wrappers.", "reference", "technical", False,
     [("Systems Performance", "publication"), ("Brendan Gregg", "person"), ("perf wrappers", "tool")],
     [("Systems Performance", "Brendan Gregg", "AUTHORED_BY")],
     "which performance book is required onboarding reading for new SREs and which chapter must they read",
     "systems performance brendan gregg sre onboarding chapter 6 cpu perf"),
    # --- 34 decision ---
    ("Dropped JFR continuous recording in favour of async-profiler's wall-clock mode for async-heavy services; JFR's method-sample bias under-counted time spent in CompletableFuture callbacks.", "decision", "technical", False,
     [("JFR", "technology"), ("async-profiler", "tool"), ("CompletableFuture", "api")],
     [("async-profiler", "JFR", "REPLACES")],
     "which JVM profiler replaced JFR for async-heavy services and which class was under-counted",
     "jfr async profiler wall clock completable future method sample bias"),
    # --- 35 architecture ---
    ("CUDA kernel profiling layers three tools: nvprof for quick counter dumps, Nsight Compute for per-SM analysis, and Nsight Systems for host-device interaction — each answers a different question.", "architecture", "technical", False,
     [("nvprof", "tool"), ("Nsight Compute", "tool"), ("Nsight Systems", "tool"), ("CUDA", "technology")],
     [("nvprof", "CUDA", "APPLIES_TO"), ("Nsight Compute", "CUDA", "APPLIES_TO")],
     "which three CUDA profilers layer together and what question does each answer",
     "nvprof nsight compute systems cuda sm counter host device kernel"),
    # --- 36 problem ---
    ("Flamegraphs from the Rust binary merged unrelated inlined callers into one frame; turned off mir-opt-level during release builds for the profiling job so symbolisation matched source lines.", "problem", "technical", False,
     [("Flamegraphs", "concept"), ("Rust", "language"), ("mir-opt-level", "config")],
     [("mir-opt-level", "Flamegraphs", "CONFIGURES")],
     "which Rust compiler knob collapsed inlined frames in flamegraphs and how did the team restore fidelity",
     "rust mir opt level flamegraph inline merge release symbol source line"),
    # --- 37 preference ---
    ("Kernel team prefers perf-tools' execsnoop over auditd for short-lived process investigations; execsnoop captures argv reliably while auditd loses it under burst exec rates.", "preference", "technical", False,
     [("perf-tools", "publication"), ("execsnoop", "tool"), ("auditd", "service")],
     [("execsnoop", "auditd", "PREFERS")],
     "which process-tracing tool does the kernel team prefer for short-lived procs and why",
     "execsnoop perf tools auditd short lived process argv burst exec"),
    # --- 38 architecture ---
    ("The continuous-profiling backend fans profiles into three sinks: Pyroscope for interactive flamegraphs, S3 Parquet for offline diff jobs, and Grafana Loki for structured profile metadata.", "architecture", "technical", False,
     [("Pyroscope", "service"), ("S3", "service"), ("Parquet", "technology"), ("Grafana Loki", "service")],
     [("Pyroscope", "S3", "COMMUNICATES_WITH"), ("S3", "Parquet", "USES")],
     "which three sinks does the continuous-profiling backend fan profiles into and what role does each play",
     "pyroscope s3 parquet grafana loki fan out sink profile metadata diff"),
    # --- 39 milestone ---
    ("Completed the Intel VTune rollout to the HPC batch cluster in the first week of 2026-01; hotspot analysis now runs alongside every nightly MPI benchmark and publishes a top-10 hotspots diff.", "milestone", "technical", False,
     [("Intel VTune", "tool"), ("HPC batch cluster", "infrastructure"), ("MPI", "protocol"), ("2026-01", "date")],
     [("Intel VTune", "HPC batch cluster", "DEPLOYED_ON"), ("Intel VTune", "MPI", "APPLIES_TO")],
     "when did VTune reach the HPC batch cluster and what nightly artefact does it publish now",
     "intel vtune hpc batch mpi january 2026 hotspot diff nightly benchmark"),
    # --- 40 decision ---
    ("Rejected FlameScope after an evaluation week because its sub-second heatmap duplicated what Pyroscope already shows in the time-range slider; kept differential flamegraphs as the specialised artefact.", "decision", "technical", False,
     [("FlameScope", "tool"), ("Pyroscope", "service"), ("differential flamegraphs", "concept")],
     [("Pyroscope", "FlameScope", "PREFERS")],
     "which sub-second-heatmap tool did the team reject after evaluation and which existing feature covered it",
     "flamescope pyroscope differential flamegraph sub second heatmap slider"),
    # --- 41 milestone ---
    ("Chrome tracing JSON from viztracer and perfetto protos from the native side merge into one timeline through the trace_processor CLI; devs see cross-language spans without switching tools.", "milestone", "technical", False,
     [("viztracer", "tool"), ("perfetto", "tool"), ("trace_processor", "command"), ("Chrome tracing JSON", "technology")],
     [("trace_processor", "viztracer", "COMMUNICATES_WITH"), ("trace_processor", "perfetto", "COMMUNICATES_WITH")],
     "which CLI merges Chrome tracing JSON and perfetto protos into one cross-language timeline",
     "viztracer perfetto trace processor chrome tracing json timeline cross"),
    # --- 42 fact ---
    ("CPU sampling is statistical and cheap while tracing is exhaustive and expensive; the internal decision matrix pins sampling for production and tracing for staging reproductions under one minute.", "fact", "technical", False,
     [("CPU sampling", "method"), ("tracing", "method"), ("decision matrix", "publication")],
     [("decision matrix", "CPU sampling", "APPLIES_TO"), ("decision matrix", "tracing", "APPLIES_TO")],
     "how does the internal matrix split CPU sampling and tracing between production and staging",
     "cpu sampling tracing statistical exhaustive decision matrix production staging"),
    # --- 43 noise ---
    ("Someone replaced the office plant in the window with a plastic one and no one noticed for two months until the watering schedule was audited.", "fact", "noise", True, [], [], None, None),
    # --- 44 problem ---
    ("py-spy couldn't attach inside the hardened container because CAP_SYS_PTRACE was dropped; added the capability to the profiler sidecar only, not the app container, and attach worked.", "problem", "technical", False,
     [("py-spy", "tool"), ("CAP_SYS_PTRACE", "config"), ("profiler sidecar", "service")],
     [("CAP_SYS_PTRACE", "py-spy", "CONFIGURES")],
     "which Linux capability did py-spy need to attach inside a hardened container and where was it granted",
     "py spy cap sys ptrace hardened container sidecar capability attach"),
    # --- 45 reference ---
    ("The flamegraphs.pl Perl script from Brendan Gregg's FlameGraph repo is still the reference implementation; every internal renderer's output is validated against its SVG layout.", "reference", "technical", False,
     [("flamegraphs.pl", "file"), ("FlameGraph", "publication"), ("Brendan Gregg", "person")],
     [("flamegraphs.pl", "FlameGraph", "HAS_PART"), ("FlameGraph", "Brendan Gregg", "AUTHORED_BY")],
     "which flamegraph script is treated as the reference implementation for layout validation",
     "flamegraph brendan gregg perl script reference svg layout validate"),
    # --- 46 architecture ---
    ("Off-CPU analysis pipeline joins sched:sched_switch events from eBPF with the on-CPU pprof samples using timestamp and pid; the combined flamegraph attributes the wait to a futex owner.", "architecture", "technical", False,
     [("eBPF", "technology"), ("pprof", "tool"), ("sched:sched_switch", "method"), ("futex", "concept")],
     [("pprof", "eBPF", "COMMUNICATES_WITH")],
     "how does the off-CPU pipeline join eBPF sched_switch with pprof samples to name the futex owner",
     "off cpu ebpf sched switch pprof join timestamp pid futex owner"),
    # --- 47 decision ---
    ("Standardised on 97 Hz perf sampling alongside 997 Hz for eBPF stack traces; the prime frequencies avoid aliasing against the 100 and 1000 Hz kernel timers that created phantom peaks.", "decision", "technical", False,
     [("perf", "tool"), ("eBPF", "technology"), ("kernel timers", "concept")],
     [("perf", "kernel timers", "CONFIGURES")],
     "which prime sampling frequencies became standard for perf and eBPF to avoid kernel-timer aliasing",
     "perf ebpf 97 997 hz prime sample kernel timer alias phantom peak"),
    # --- 48 milestone ---
    ("Retired the homegrown flamegraph aggregator on 2026-03-05; Parca's backend now owns the fleet-wide merge and the old Python cron job was deleted after a month of parallel validation.", "milestone", "technical", False,
     [("Parca", "service"), ("Python", "language"), ("cron", "tool"), ("2026-03-05", "date")],
     [("Parca", "Python", "REPLACES")],
     "when did the homegrown flamegraph aggregator retire and which service took over fleet-wide merges",
     "parca flamegraph aggregator python cron retire march 2026 fleet merge"),
    # --- 49 fact ---
    ("async-profiler uses AsyncGetCallTrace instead of JVMTI's GetStackTrace because AGCT can be called from a signal handler; that's what makes wall-clock sampling possible on running Java threads.", "fact", "technical", False,
     [("async-profiler", "tool"), ("AsyncGetCallTrace", "api"), ("JVMTI", "api"), ("Java", "language")],
     [("async-profiler", "AsyncGetCallTrace", "USES"), ("AsyncGetCallTrace", "JVMTI", "REPLACES")],
     "which JVM internal does async-profiler call from a signal handler to enable wall-clock sampling",
     "async profiler asyncgetcalltrace jvmti signal handler wall clock java"),
    # --- 50 reference ---
    ("The Parca documentation's \"profiling in Kubernetes\" guide is the onboarding doc for new cluster operators; it covers the DaemonSet rollout, RBAC, and the label schema in one page.", "reference", "technical", False,
     [("Parca", "service"), ("Kubernetes", "platform"), ("DaemonSet", "pattern"), ("RBAC", "concept")],
     [("Parca", "Kubernetes", "DEPLOYED_ON")],
     "where do new cluster operators start learning Parca on Kubernetes in a single concise doc",
     "parca kubernetes daemonset rbac label schema onboarding guide rollout"),
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
