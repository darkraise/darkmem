"""One-off emitter for retrieval top-up batch-013 — multi-sentence queries.

Reads shared rows at line offsets SHARED_OFFSET..SHARED_OFFSET+99 from
data/v2/shared/shared.jsonl and emits one multi-sentence retrieval row
per source row into data/v2/retrieval/batch_013.tmp.jsonl.

Row schema: {id, source_id, query, positive, query_kind="multi-sentence"}.
Ids: ret-{ID_OFFSET+1:05d} .. ret-{ID_OFFSET+100:05d}.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_013.tmp.jsonl"

ID_OFFSET = 1200
SHARED_OFFSET = 1200
QUERY_KIND = "multi-sentence"
N = 100

# One multi-sentence paragraph-style query per source row (20-60 words, 2-4 sentences).
# Indexed 0..99, aligned with shared-01200..shared-01299.
QUERIES: list[str] = [
    # 0 -> shared-01200 LiteLLM gateway / prompt caching
    "We rolled out a unified gateway in front of every LLM provider last quarter. I want to find the note about prompt caching at that gateway hitting roughly a third of requests on the support assistant. Which memory captured that milestone?",
    # 1 -> shared-01201 Pact provider verification caught rename
    "There is a story about a contract test technique that caught a breaking payload rename before the consumer team even pulled the new build. I need to locate the write-up that names the tool and describes how the catch happened before release.",
    # 2 -> shared-01202 Pact broker stood up 2026-02-15
    "We deployed a shared contract hub so mobile and web clients could publish against the same backend. Which note records the date that broker came online and mentions the billing provider as its first consumer? I think the event was in February.",
    # 3 -> shared-01203 Pact pending state
    "There is a note about letting a new consumer publish failing contracts without breaking the provider pipeline. It describes a quarantine feature that let the spec stabilise while the build stayed green. Which entry was that?",
    # 4 -> shared-01204 fast-check sort stability bug
    "A property-based testing library surfaced a sort stability defect in our leaderboard that targeted unit tests had walked past. Which note names the tool and the ranking feature where the bug showed up? I want the exact entry.",
    # 5 -> shared-01205 Haskell QuickCheck shrink on slug
    "One of our property test shrinkers localised a Unicode edge case in the slug generator that a Python port had drifted past. Which memory names the language and the library involved in that catch?",
    # 6 -> shared-01206 Stryker 62 -> 84
    "The mutation score on the billing service jumped roughly twenty points after we removed a handful of weak smoke tests. Which note captures that milestone, including the tool name and the before and after numbers?",
    # 7 -> shared-01207 mutmut equivalent mutants skip convention
    "We kept re-triaging the same equivalent mutants until someone proposed a skip annotation convention. Which memory describes that problem and the fix, and names the mutation tool we were running at the time?",
    # 8 -> shared-01208 PITest nightly only
    "There is a decision note about running a Java mutation testing tool only at night so that developer loops stay fast. Which entry records that schedule choice and mentions the morning report workflow?",
    # 9 -> shared-01209 libFuzzer -merge=1
    "We trimmed a parser seed bank from around twelve thousand down to three thousand without losing coverage frontiers. Which memory names the fuzz corpus operation that did the pruning and the specific command flag involved?",
    # 10 -> shared-01210 noise: chair lumbar
    "Somewhere in the logs there is a throwaway remark about a new office chair finally arriving with surprising lumbar support. Which entry is that small aside, and where did it land in the sequence?",
    # 11 -> shared-01211 AFL++ TLV overflow
    "A coverage-guided fuzzer caught a stack-based buffer overflow in a TLV reader that three rounds of manual review had missed. Which note names that fuzzer and the component where the overflow lived?",
    # 12 -> shared-01212 go-fuzz tariff panic
    "A Go fuzzer seeded from existing unit tests found an integer-overflow panic in a pricing component on its first weekend run. Which entry captures that first-run finding and names the calculator that blew up?",
    # 13 -> shared-01213 Golden SVG drift Inkscape
    "We had golden fixtures for SVG output thrashing between contributor machines because a renderer rounded coordinates differently across versions. Which memory names the renderer and the fix of pinning it in the dev image?",
    # 14 -> shared-01214 Golden file review label policy
    "There is a policy note that says golden-file updates now need a reviewer approval label rather than a drive-by regenerate. Which decision entry codifies that gate and explains why the previous approach stopped being enough?",
    # 15 -> shared-01215 jest-image-snapshot tolerance tighten
    "Our image snapshot diff tolerance dropped by roughly a factor of five and the CI caught a text anti-aliasing regression that same week. Which milestone note records the exact numbers and the date of the tightening?",
    # 16 -> shared-01216 cargo insta review
    "There is a preference note about a Rust snapshot workflow that makes updates feel like a staged diff rather than a blind regenerate. Which entry endorses that specific review command and why it earns trust?",
    # 17 -> shared-01217 Codecov patch coverage 80%
    "A patch-coverage gate on new lines flagged an unchecked branch in our refund path during review. Which decision note names the coverage service and the threshold that trapped the miss?",
    # 18 -> shared-01218 Coveralls ratchet only
    "We adopted a ratchet-only policy on aggregate coverage so the percentage could not slide quarter after quarter. Which decision entry captures that anti-regression rule and names the coverage service we ran it against?",
    # 19 -> shared-01219 Jacoco two-axis thresholds
    "Our Java coverage gate split the threshold into a line axis and a branch axis because a single blanket number lied about reality. Which decision memory names the tool and both percentages we settled on?",
    # 20 -> shared-01220 Flake quarantine auto-demote
    "There is a note about a label that auto-demotes a test into the nightly-only lane after a small number of flaps inside a week. Which entry explains the mechanism and reports how green rate responded afterwards?",
    # 21 -> shared-01221 Flake dashboard fingerprint RNG
    "Our flake dashboard groups failures by a shared fingerprint, and at one point a single seeded RNG issue explained roughly half of a month's flaps. Which note captures that root-cause insight and names the dashboard?",
    # 22 -> shared-01222 Jenkins matrix drop Windows+JDK8
    "We trimmed a Jenkins build matrix because the cells were multiplying faster than our support. Which decision note names the specific OS and JDK combination we retired because nobody shipped to it anymore?",
    # 23 -> shared-01223 GitHub Actions matrix sharding
    "Integration suite wall time fell from around eighteen minutes to six after we switched how jobs were split up. Which milestone note names the platform and the specific sharding strategy that did it?",
    # 24 -> shared-01224 CircleCI fan-out frontend and contract
    "A pipeline fanned frontend and contract tests into parallel jobs gated on a shared build artifact. Which architecture entry describes that split and names the CI platform it runs on?",
    # 25 -> shared-01225 BuildKit COPY ordering
    "Our Docker cache kept busting on unrelated source edits until we reordered package manifests and source files in the image. Which problem note names the build system and explains the COPY ordering fix?",
    # 26 -> shared-01226 Gradle S3 remote cache
    "A cold cross-machine Gradle build dropped from around nine minutes to two after we pointed a remote cache at object storage. Which milestone note names the backend and records the speedup?",
    # 27 -> shared-01227 Turbo short-lived token
    "We switched a monorepo remote cache to a short-lived token per CI job so stale team-wide credentials stopped leaking into forks. Which note names that cache tool and describes the token rotation behaviour?",
    # 28 -> shared-01228 Nx Cloud distributed task execution
    "Distributed task execution pulled our CI below a pre-merge SLA but we only enabled it on protected branches. Which decision entry names the service and explains why the scope was limited that way?",
    # 29 -> shared-01229 Release train cadence
    "Our release cadence cuts every other Thursday with a feature freeze on the Monday before, and hotfix branches are reserved for the worst incidents. Which decision note codifies that rhythm and the freeze discipline?",
    # 30 -> shared-01230 Flagger canary rollback
    "A progressive delivery tool rolled back a bad deploy inside about four minutes without any human in the loop, keyed on error rate and p99 latency. Which note names that tool and describes the automatic revert?",
    # 31 -> shared-01231 Argo Rollouts Prometheus SLO
    "A canary analysis template reads Prometheus and scores rollouts by SLO burn rate rather than raw error count. Which architecture entry names the progressive delivery controller and describes that metric choice?",
    # 32 -> shared-01232 blue/green over canary payments
    "The payments team picked blue/green over canary for a stateful service because a half-baked canary on a sharded database caused more pain than it saved. Which decision note records that trade-off and names the service?",
    # 33 -> shared-01233 semantic-release conventional commits
    "Our version bumps and tags now flow automatically from conventional commit subjects, and the release notes effectively write themselves. Which decision note names the tool that drives that automation?",
    # 34 -> shared-01234 Renovate auto-merge patch/minor
    "A shared dependency-bot preset auto-merges patch and minor dev updates on green CI but still routes majors through a human. Which decision note names the bot and describes the split policy?",
    # 35 -> shared-01235 Dependabot grouped updates
    "We grouped ecosystem peers so a linter and its plugins travel as one pull request, and our weekly update PR count fell by more than three quarters. Which milestone note names the tool and the drop in numbers?",
    # 36 -> shared-01236 Required checks in YAML
    "The required-check list on our repo is now codified alongside ownership config in version control instead of being clicked into settings. Which architecture note describes that move and names the adjacent owners file?",
    # 37 -> shared-01237 Bors merge queue
    "A merge queue serialised merges on the main branch and finally killed a green-then-red race that kept showing up after merge. Which decision note names the queueing tool and the race condition it fixed?",
    # 38 -> shared-01238 Mergify batch size 3
    "We started landing stacked pull requests in small batches so CI would not re-run from scratch on every one. Which decision note names the merge queue and the batch size we settled on?",
    # 39 -> shared-01239 GitHub merge queue duplicate checks
    "A native merge queue kept misbehaving until we removed a redundant duplication between branch protection and status checks. Which problem note describes that re-run bug and the configuration trim that fixed it?",
    # 40 -> shared-01240 commitlint + lefthook
    "Commit message style is enforced in CI as a hard reject but also as a fast warning from a local Git hook, so the block is rare. Which architecture note names both the CI tool and the local hook runner?",
    # 41 -> shared-01241 gitsign replaces GPG
    "Signed commits used to rely on a GPG key ritual until a keyless sigstore-based approach took over and stopped blocking releases. Which decision note names the replacement tool and records the retirement of GPG?",
    # 42 -> shared-01242 conventional commits warn-only on docs
    "We dialled back conventional-commits enforcement to warn-only for docs-only pull requests because the friction was not earning its keep there. Which decision entry records that scope reduction?",
    # 43 -> shared-01243 git-cliff changelog
    "A changelog generator renders release notes from conventional commits grouped by scope, and we stopped hand-editing them entirely. Which note names that tool and describes the automation?",
    # 44 -> shared-01244 Changesets per-package
    "The packages repo moved to a different changelog tool because per-package versioning fit the publish pipeline better. Which decision entry names the new tool and the repo-type motivation?",
    # 45 -> shared-01245 SLSA level 3 + cosign
    "Release artifacts now carry level-3 provenance and consumers can verify them with a single signing-tool command. Which architecture note names the provenance framework and the verification CLI?",
    # 46 -> shared-01246 GitHub OIDC attestation
    "We wiped long-lived signing keys off our runners by attesting artifact provenance through a GitHub OIDC token instead. Which note names that protocol and describes the zero-key outcome?",
    # 47 -> shared-01247 Semgrep autofix suggest commit
    "A static analyser now proposes a fix commit instead of failing the build outright when it finds a missing null-guard. Which decision entry names that tool and the autofix behaviour?",
    # 48 -> shared-01248 SonarQube duplication gate
    "Our quality gate blocked a pull request because a duplicated-code ratio was too high, and extracting a currency helper dropped the figure under threshold. Which problem note names the quality gate and the helper?",
    # 49 -> shared-01249 Release smoke post-deploy webhook
    "A smoke suite runs after every deploy against a canary namespace and posts its status into the release chat via a webhook. Which architecture note describes that feedback loop and names the target namespace?",
    # 50 -> shared-01250 reproducible CLI 2026-03-11
    "Our CLI releases became byte-identical across runners on a specific date in March, which unblocked downstream packaging. Which milestone note records that reproducible-builds adoption and the exact date?",
    # 51 -> shared-01251 py-spy folded stack regex
    "A sampling profiler dumped a folded stack file that fed a flame graph, and the hot spot landed on a regex inside the request middleware. Which problem note names that Python profiler and the hot call site?",
    # 52 -> shared-01252 memray pandas copy
    "An allocation tracer caught a per-request pandas frame copy that RSS graphs had smoothed into a gentle climb. Which problem note names the tracer and the per-request allocation pattern?",
    # 53 -> shared-01253 clinic.js bcrypt sync
    "A Node diagnostic tool pointed at event loop starvation caused by a synchronous hash call, and switching to the async variant unblocked p99 latency. Which problem note names that diagnostic and the bcrypt swap?",
    # 54 -> shared-01254 Chrome DevTools JSON.parse hydration
    "A browser profiler recorded a long main-thread task that traced back to a huge JSON parse during hydration. Which problem note names the profiler and the payload size that broke the main thread?",
    # 55 -> shared-01255 perf dwarf Rust inlined
    "A Linux profiler run stopped being a wall of question marks once we enabled DWARF call graphs to resolve inlined frames in our Rust service. Which milestone note captures that unwinding fix?",
    # 56 -> shared-01256 dtrace Illumos compaction
    "A dynamic tracer on an Illumos host showed a block-device queue depth blowup during a compaction storm that the application logs never mentioned. Which note names the tracer and the host platform?",
    # 57 -> shared-01257 USDT probes postgres lock-manager
    "Static user-space tracepoints baked into postgres let us correlate query stalls with lock-manager waits without patching or recompiling the server. Which note names that tracepoint technology and the database?",
    # 58 -> shared-01258 bpftrace read amplification
    "A single eBPF one-liner on syscall entry surfaced a read amplification that we had blamed on the storage vendor for two sprints. Which problem note names the tracer and the misdiagnosis it corrected?",
    # 59 -> shared-01259 Pixie auto-instrument HTTP
    "An auto-instrumentation tool let the SRE team watch HTTP spans on a staging cluster without rebuilding any service image. Which decision entry names that eBPF observability product and describes the zero-rebuild outcome?",
    # 60 -> shared-01260 noise: microwave
    "Somewhere there is a throwaway note about an appliance in a nearby room breaking someone's concentration during a bug hunt. Which small aside mentions that distracting buzz?",
    # 61 -> shared-01261 Parca leak under OOMKill
    "A continuous profiler caught a slow memory leak in an API gateway that never tripped the Kubernetes OOMKill threshold. Which note names that profiler and explains how the leak stayed under the cap?",
    # 62 -> shared-01262 Pyroscope replaces pprof
    "Our homegrown pprof scrape loop got replaced by a continuous profiler that also offers one-click differential flame graphs across deploys. Which decision note names the replacement and the old loop it retired?",
    # 63 -> shared-01263 gdb scheduler-locking futex
    "A stuck worker process was inspected live without killing it, and the backtrace showed a futex loop against a misused condition variable. Which problem note names the debugger and the scheduler-locking setting?",
    # 64 -> shared-01264 rr reverse continue
    "A record-and-replay debugger let us reverse-continue backwards from a crash in a flaky crypto test and find an uninitialised byte. Which problem note names that tool and the reverse-step feature?",
    # 65 -> shared-01265 Rust release + debug symbols
    "Profiler samples stopped resolving to raw addresses after we added debug symbols to a dedicated Rust release profile. Which decision note records that build-config change and the symbol-resolution win?",
    # 66 -> shared-01266 Go pprof json.Marshal heap
    "A Go profiler view revealed that a single marshal call owned around thirty percent of heap churn at peak load. Which problem note names the profiler view and the offending call site?",
    # 67 -> shared-01267 Python 3.11 async traceback
    "An interpreter upgrade finally made async stack traces print the full awaiter chain, turning an afternoon-long investigation into a minutes-long one. Which milestone note names the specific version?",
    # 68 -> shared-01268 Node heap snapshot diff breaker
    "Heap snapshot comparisons across two load tests exposed a map that grew without bounds when a circuit breaker tripped in a specific order. Which problem note captures that leak and the ordering trigger?",
    # 69 -> shared-01269 GOGC + GOMEMLIMIT
    "We tuned two Go runtime knobs — one for GC aggressiveness and one for a soft memory cap — and pod kills went to zero while GC pauses fell. Which decision note names both settings and the cap relationship?",
    # 70 -> shared-01270 asyncio task factory hook
    "An introspection hook on our async task factory surfaced an unawaited coroutine leak that was showing up across every tenant. Which problem note names the hook and the cross-tenant blast radius?",
    # 71 -> shared-01271 OpenTelemetry planner dominance
    "Tracing a slow SQL query end to end revealed that the planner was spending more time than execution itself. Which note names the tracing framework and captures the planner-versus-execution split?",
    # 72 -> shared-01272 DHAT short-lived buffer stack
    "A DHAT block lifetime histogram pointed at a short-lived buffer that should have been on the stack, and hot path RSS dropped measurably once we moved it. Which problem note captures that fix?",
    # 73 -> shared-01273 off-CPU flame graph semaphore
    "An off-CPU flame graph showed workers parked on a semaphore rather than burning cycles, making the real culprit obvious. Which note captures that insight about blocking time dominating?",
    # 74 -> shared-01274 off-CPU preference latency
    "There is a preference note recommending off-CPU flame graphs over on-CPU ones for latency debugging because wall-clock waits dominate the budget. Which entry states that preference?",
    # 75 -> shared-01275 JFR boxing cascade
    "A continuous low-overhead production profiler offered an allocation-by-class view that uncovered a hidden boxing cascade. Which note names that JVM profiler and the specific view we used?",
    # 76 -> shared-01276 Perfetto Android binder
    "An Android client's frame misses lined up with a binder call into a system service that occasionally stalled. Which problem note names the tracing tool and the cross-process call involved?",
    # 77 -> shared-01277 Xdebug loop DB call menu
    "A PHP profiler turned up a template helper that called the database inside a loop over menu items. Which problem note names the profiler and the loop-body database call?",
    # 78 -> shared-01278 stackprof Sidekiq MessagePack
    "A Ruby sampling profiler on Sidekiq workers showed Marshal.load dominating, and swapping the serialiser shaved roughly forty percent off. Which milestone note names the profiler and both serialisation libraries?",
    # 79 -> shared-01279 PHP spx Laravel regex
    "A call-graph view in a PHP profiler made one middleware's regex dominance embarrassingly visible, and the offending rule was simplified. Which problem note names the profiler and the framework?",
    # 80 -> shared-01280 PerfView static event handler
    "A .NET profiler traced GC heap retention back to a static event handler that never detached, and the memory curve flattened after the fix. Which problem note names the profiler and the root cause?",
    # 81 -> shared-01281 dotTrace UI stutter logging
    "A .NET timeline view lined up a UI stutter with a background thread contending on a logging queue during traffic bursts. Which problem note names that profiler and the contention source?",
    # 82 -> shared-01282 JetBrains Rider profiler integration
    "Attaching a profiler inside a JetBrains IDE became a simple menu action, and adoption on the .NET side went from rare to default. Which note captures that IDE integration and the adoption shift?",
    # 83 -> shared-01283 Xcode Instruments layout storm
    "An Apple profiler template caught a main-thread layout storm triggered by an offscreen table view's auto-sizing pass. Which problem note names the instrument template and the storm trigger?",
    # 84 -> shared-01284 BPF CO-RE portability
    "A portability feature let us ship a single eBPF binary across kernel versions without per-kernel recompiles, and operator pain during rollouts collapsed. Which milestone note names that feature?",
    # 85 -> shared-01285 PMU LLC-misses arena
    "We programmed hardware counters for last-level-cache misses per function, and the hottest loop turned out to be chasing pointers across a fragmented arena. Which problem note records that PMU finding?",
    # 86 -> shared-01286 Datadog trace-to-profile
    "A vendor's continuous profiler correlated request traces with sampled CPU frames so that jumping from a slow span to the offending code took one click. Which note names that vendor and the correlation?",
    # 87 -> shared-01287 Pyroscope diff deploy tags
    "Diffing profiles between two deploy tags caught a regression in a templating helper before the synthetic monitor fired. Which milestone note names the profiler and describes the diff workflow?",
    # 88 -> shared-01288 perf LBR JIT branch miss
    "A short window of LBR sampling with the Linux perf tool made branch-misprediction hot spots in the JIT stand out like headlights. Which note names the sampling mode and the JIT target?",
    # 89 -> shared-01289 bpftrace one-liner preference
    "There is a preference for bpftrace one-liners over writing long C BPF programs for quick production diagnosis because turnaround wins outweigh the ceiling. Which entry states that preference?",
    # 90 -> shared-01290 Rust debug hides cliff
    "A scaling cliff in our Rust service stayed hidden because debug builds made a quadratic helper fast enough, and only release builds exposed the problem. Which problem note captures that surprise?",
    # 91 -> shared-01291 JFR + thread dump class loader lock
    "A prod JVM stall was diagnosed from a flight recorder dump that bundled a thread dump, and the culprit was a blocked class loader lock. Which problem note describes that combined capture?",
    # 92 -> shared-01292 Tokio console subscriber channel
    "Wrapping a Tokio runtime with a console subscriber listed awaiting tasks by time-blocked, and a poorly bounded channel fell out as the culprit. Which problem note names that diagnostic?",
    # 93 -> shared-01293 async-profiler Kotlin alloc
    "An async-profiler agent on a Kotlin service, run in allocation-event mode, trimmed several boxing hot spots from the profile. Which note names that profiler and the event it was sampling?",
    # 94 -> shared-01294 eBPF tcpretrans AZ loss
    "An eBPF tool hooked into the observability stack finally produced a smoking-gun graph for a low-grade packet-loss pattern between two availability zones. Which problem note names that tool?",
    # 95 -> shared-01295 CPython no-gil GC tuning
    "Switching perf-run CPython builds to a no-gil preview improved single-process scaling but reopened the GC tuning discussion. Which note names that interpreter variant and the tuning follow-up?",
    # 96 -> shared-01296 coredumpctl gdb post-mortem
    "A hard-to-reproduce production crash was finally nailed by capturing a core dump and loading it into gdb later, rather than trying to catch it live under load. Which decision note names both tools and the workflow?",
    # 97 -> shared-01297 V8 heap snapshot nightly CI
    "Node leak regressions flipped from a two-week surprise to same-day failures after we wired V8 heap snapshots into a nightly CI job. Which milestone note captures that automation and the feedback speedup?",
    # 98 -> shared-01298 Go continuous alloc sampling
    "We turned on always-on Go allocation profiling at a low rate and kept roughly a year of history while staying under one percent overhead. Which decision note captures that sampling choice?",
    # 99 -> shared-01299 PerfView DI container transient
    "A .NET heap snapshot diff tied a slow leak to a collection cached inside a DI container, and re-scoping the dependency as transient cleared it. Which problem note names the profiler and the scope fix?",
]


def _word_count(s: str) -> int:
    return len(s.split())


def _sentence_count(s: str) -> int:
    # Terminal punctuation counts; em dashes and colons do not end sentences.
    return sum(s.count(c) for c in (".", "?", "!"))


def main() -> None:
    assert len(QUERIES) == N, f"expected {N} queries, got {len(QUERIES)}"
    for i, q in enumerate(QUERIES):
        wc = _word_count(q)
        sc = _sentence_count(q)
        if not (20 <= wc <= 60):
            raise ValueError(f"query[{i}] word count {wc} out of [20, 60]: {q!r}")
        if not (2 <= sc <= 4):
            raise ValueError(f"query[{i}] sentence count {sc} out of [2, 4]: {q!r}")

    with SHARED.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    src = [json.loads(lines[SHARED_OFFSET + i]) for i in range(N)]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for i, row in enumerate(src):
            out = {
                "id": f"ret-{ID_OFFSET + 1 + i:05d}",
                "source_id": row["id"],
                "query": QUERIES[i],
                "positive": row["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    print(f"wrote {N} rows to {OUT}")


if __name__ == "__main__":
    main()
