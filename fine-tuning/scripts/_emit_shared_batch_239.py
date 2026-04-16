"""One-off emitter for shared-base batch-239 — technical domain (Go ecosystem: goroutines, channels, context, errors, generics, stdlib, web frameworks, RPC, tooling, testing, profiling, build/embed, modules, PGO, CGO).

Writes 50 rows to data/v2/shared/batch_239.tmp.jsonl with ids shared-11901..11950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_239.tmp.jsonl"
ID_OFFSET = 11900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the worker pool from raw goroutines spawned per job to a bounded goroutine pool reading off a buffered channel; unbounded fan-out was pushing the scheduler over ten thousand Gs and chewing memory.", "decision", "technical", False,
     [("goroutines", "concept"), ("goroutine pool", "pattern"), ("buffered channel", "pattern"), ("scheduler", "concept")],
     [("goroutine pool", "goroutines", "REPLACES")],
     "which worker pool pattern replaced per-job goroutine spawning and which runtime pressure drove the switch",
     "goroutine pool buffered channel worker scheduler bound fan out"),
    # --- 2 ---
    ("Cancellation propagation now uses context.WithCancel chained through every service call; the ad-hoc boolean stopCh pattern left goroutines leaking whenever an intermediate layer forgot to forward the close.", "architecture", "technical", False,
     [("context.WithCancel", "api"), ("stopCh", "pattern"), ("goroutines", "concept")],
     [("context.WithCancel", "stopCh", "REPLACES")],
     "which cancellation primitive replaced the ad-hoc stopCh boolean and which leak class did it retire",
     "context withcancel stopch boolean goroutine leak propagate cancel"),
    # --- 3 ---
    ("Every outbound HTTP client call is wrapped in context.WithTimeout at two seconds for the p99 budget; a missing timeout in one call path stalled the pool for forty minutes on a dead upstream in March.", "fact", "technical", False,
     [("context.WithTimeout", "api"), ("HTTP client", "concept"), ("p99", "concept")],
     [("context.WithTimeout", "HTTP client", "APPLIES_TO")],
     "which timeout wrapper became mandatory on outbound HTTP calls after a dead-upstream stall in March",
     "context withtimeout http client p99 budget upstream stall"),
    # --- 4 ---
    ("Deadlines at the gateway are set with context.WithDeadline anchored to the incoming request header rather than a fresh clock read; downstream services now share one absolute cut-off instead of each computing their own.", "architecture", "technical", False,
     [("context.WithDeadline", "api"), ("gateway", "service")],
     [("context.WithDeadline", "gateway", "APPLIES_TO")],
     "how does the gateway share one absolute deadline across downstream services instead of per-hop timers",
     "context withdeadline gateway absolute downstream header anchor"),
    # --- 5 ---
    ("Banned context.WithValue for anything except request-scoped trace ids and tenant tokens; a previous handler stuffed a db.Conn in there and we hit a closed-conn panic after the parent context got cancelled.", "preference", "technical", False,
     [("context.WithValue", "api"), ("trace id", "concept"), ("db.Conn", "api")],
     [],
     "which context primitive is restricted to trace ids and tenant tokens and which past bug motivated the restriction",
     "context withvalue trace id tenant db conn panic restrict"),
    # --- 6 ---
    ("Error wrapping migrated to fmt.Errorf with %w plus errors.Is for sentinel checks; the pkg/errors stack-trace wrapper got retired once 1.20 made the stdlib path capable of multi-error unwrap.", "reference", "technical", False,
     [("fmt.Errorf", "api"), ("errors.Is", "api"), ("pkg/errors", "library"), ("1.20", "date")],
     [("errors.Is", "pkg/errors", "REPLACES")],
     "which error-wrapping stack replaced pkg/errors and which stdlib capability made the switch viable",
     "fmt errorf errors is pkg errors sentinel wrap unwrap 1.20"),
    # --- 7 ---
    ("errors.As is the only way we extract typed errors across package boundaries; direct type assertions broke silently once one repo started wrapping with %w two layers deep.", "preference", "technical", False,
     [("errors.As", "api"), ("type assertion", "pattern"), ("%w", "api")],
     [("errors.As", "type assertion", "REPLACES")],
     "which error extraction api became mandatory once wrapping went two layers deep across packages",
     "errors as type assertion wrap boundary typed extract package"),
    # --- 8 ---
    ("Generics from 1.18 let the collection helpers drop interface{}; the old reflect-based Map and Filter were about eight times slower than the generic versions in the benchmark harness.", "milestone", "technical", False,
     [("Generics", "concept"), ("1.18", "date"), ("interface{}", "api"), ("reflect", "library")],
     [("Generics", "reflect", "REPLACES")],
     "which Go version introduced the generics that retired the reflect-based Map and Filter helpers",
     "generics 1.18 interface reflect map filter collection helper"),
    # --- 9 ---
    ("Status codes are declared with iota enums backed by a stringer-generated String method; the old string-constant approach let typos sneak past the compiler until runtime comparisons silently mismatched.", "architecture", "technical", False,
     [("iota", "api"), ("stringer", "tool"), ("String method", "api"), ("string-constant", "pattern")],
     [("iota", "string-constant", "REPLACES")],
     "which enum pattern replaced string constants for status codes and how is the String method generated",
     "iota enum stringer string method status code typo compiler"),
    # --- 10. noise ---
    ("The office espresso machine started grinding louder than the build server and someone taped a paper cone to the hopper to muffle it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Mutex protection for the session cache uses sync.Mutex rather than sync.RWMutex; the read-to-write ratio measured below three-to-one and the RWMutex overhead was actually losing on our traffic profile.", "decision", "technical", False,
     [("sync.Mutex", "api"), ("sync.RWMutex", "api"), ("session cache", "concept")],
     [("sync.Mutex", "sync.RWMutex", "PREFERS")],
     "which mutex flavour won the session-cache bake-off and what read-to-write ratio drove the choice",
     "sync mutex rwmutex session cache read write ratio overhead"),
    # --- 12 ---
    ("The config hot-reload path switched to sync.RWMutex because readers outnumber writers by roughly five hundred to one; the old sync.Mutex was serialising every request needlessly.", "decision", "technical", False,
     [("sync.RWMutex", "api"), ("sync.Mutex", "api"), ("config hot-reload", "pattern")],
     [("sync.RWMutex", "sync.Mutex", "REPLACES")],
     "which lock type replaced sync.Mutex on the config hot-reload path and what read-write skew justified it",
     "sync rwmutex mutex config hot reload reader writer skew serialise"),
    # --- 13 ---
    ("Batch jobs synchronise completion with sync.WaitGroup; the Add call is hoisted above the goroutine launch so a racing Wait never returns before the last Add, which tripped us once on a small pool.", "fact", "technical", False,
     [("sync.WaitGroup", "api"), ("Add", "api"), ("Wait", "api"), ("goroutine", "concept")],
     [],
     "which sync primitive drives batch-job completion and why is Add hoisted above the goroutine launch",
     "sync waitgroup add wait goroutine race batch job hoist launch"),
    # --- 14 ---
    ("Singleton initialisation went from a double-checked locking dance to sync.Once; the earlier code worked on paper but failed the race detector once a warm-path reader raced a cold-path initialiser.", "decision", "technical", False,
     [("sync.Once", "api"), ("double-checked locking", "pattern"), ("race detector", "tool")],
     [("sync.Once", "double-checked locking", "REPLACES")],
     "which initialisation primitive replaced double-checked locking after the race detector flagged a data race",
     "sync once double checked locking race detector singleton init"),
    # --- 15 ---
    ("Fan-in across three upstream feeds uses select with a default case to keep the consumer non-blocking; a prior blocking select caused a head-of-line stall when one upstream went silent for thirty seconds.", "problem", "technical", False,
     [("select", "api"), ("Fan-in", "pattern"), ("default case", "api")],
     [],
     "which select-statement tweak fixed the head-of-line stall on the three-upstream fan-in",
     "select default fan in head of line stall upstream non blocking"),
    # --- 16 ---
    ("Channels between producer and consumer are now buffered at one times the consumer parallelism; unbuffered channels were serialising producers against slow consumers during the upload spike.", "decision", "technical", False,
     [("channels", "concept"), ("buffered", "pattern"), ("unbuffered", "pattern"), ("parallelism", "concept")],
     [("buffered", "unbuffered", "REPLACES")],
     "which channel buffering choice fixed producer serialisation during the upload spike",
     "buffered unbuffered channel producer consumer parallelism upload spike"),
    # --- 17 ---
    ("The HTTP API stack sits on standard net/http with a thin router; the benchmark showed gin, fiber, and chi all within five percent of stdlib once middleware was equalised, so the extra dep was not worth it.", "reference", "technical", False,
     [("net/http", "library"), ("gin", "framework"), ("fiber", "framework"), ("chi", "framework")],
     [("net/http", "gin", "PREFERS"), ("net/http", "fiber", "PREFERS"), ("net/http", "chi", "PREFERS")],
     "which web framework was preferred over gin fiber and chi and what benchmark signal justified it",
     "net http gin fiber chi framework benchmark middleware router"),
    # --- 18 ---
    ("The internal admin panel uses echo because its group middleware and template helpers kept the admin-specific code tiny; the public API sticks with stdlib for perf headroom.", "preference", "technical", False,
     [("echo", "framework"), ("stdlib", "library"), ("admin panel", "service")],
     [("echo", "admin panel", "APPLIES_TO")],
     "which web framework drives the admin panel while the public API stays on net/http",
     "echo framework admin panel group middleware template net http"),
    # --- 19 ---
    ("Adopted chi for the new events service after a side-by-side with gin: chi's router composes with net/http handlers directly, so existing middlewares dropped in without adaptors.", "decision", "technical", False,
     [("chi", "framework"), ("gin", "framework"), ("net/http", "library"), ("events service", "service")],
     [("chi", "gin", "PREFERS")],
     "which router won the events service bake-off and which interop property sealed the choice",
     "chi gin router events service net http middleware interop adapter"),
    # --- 20 ---
    ("The push-notifications service uses fiber because its fasthttp base shaved roughly forty percent off the per-request allocation in the load test; net/http is still the default everywhere else.", "fact", "technical", False,
     [("fiber", "framework"), ("fasthttp", "library"), ("net/http", "library"), ("push-notifications", "service")],
     [("fiber", "push-notifications", "APPLIES_TO")],
     "which framework drives the push-notifications service and what allocation win earned it the spot",
     "fiber fasthttp net http push notifications allocation load test"),
    # --- 21 ---
    ("Internal RPC migrated from REST-over-http to grpc-go; request latency at p99 dropped from 42 ms to 11 ms and the generated client code eliminated a whole class of field-name typos.", "milestone", "technical", False,
     [("grpc-go", "library"), ("REST", "protocol"), ("p99", "concept")],
     [("grpc-go", "REST", "REPLACES")],
     "which RPC stack replaced REST for internal traffic and what p99 improvement did it deliver",
     "grpc go rest internal rpc p99 latency client field typo"),
    # --- 22 ---
    ("Proto definitions are pinned via buf modules with CI breakage checks on every PR; the old protoc Makefile drifted across repos and we shipped a backwards-incompatible change once because of it.", "reference", "technical", False,
     [("buf", "tool"), ("protoc", "tool"), ("CI", "concept")],
     [("buf", "protoc", "REPLACES")],
     "which proto tooling replaced the protoc Makefile and what breakage class did buf's CI checks retire",
     "buf protoc proto module ci break check makefile drift"),
    # --- 23 ---
    ("Browser-facing services expose connect-go endpoints alongside grpc-go; connect's http/1.1 compatibility means the single-page app talks to the same backend without a gateway translating frames.", "architecture", "technical", False,
     [("connect-go", "library"), ("grpc-go", "library"), ("http/1.1", "protocol"), ("single-page app", "service")],
     [("connect-go", "single-page app", "APPLIES_TO")],
     "which library exposes browser-facing endpoints alongside grpc-go and which transport property avoids a gateway",
     "connect go grpc go http 1.1 browser spa gateway transport"),
    # --- 24 ---
    ("CLIs are built on cobra with viper binding env vars, flags, and config files in that precedence; the ad-hoc flag-parsing tools we had before had three different precedence orders across the org.", "reference", "technical", False,
     [("cobra", "framework"), ("viper", "library"), ("env vars", "concept"), ("flag", "concept")],
     [("viper", "flag", "APPLIES_TO")],
     "which CLI stack standardised env, flag, and config file precedence across the organisation",
     "cobra viper cli env flag config file precedence standard"),
    # --- 25 ---
    ("Logging standardised on zerolog for hot paths and zap for services that need a richer structured encoder; a prior split between logrus and the stdlib log left field names inconsistent across tenants.", "decision", "technical", False,
     [("zerolog", "library"), ("zap", "library"), ("logrus", "library"), ("stdlib log", "library")],
     [("zerolog", "logrus", "REPLACES"), ("zap", "logrus", "REPLACES")],
     "which pair of loggers replaced logrus and how is the split between them decided",
     "zerolog zap logrus stdlib log structured hot path field"),
    # --- 26 ---
    ("Sentry-go is wired as a slog handler so every ERROR-level log with an error field becomes a Sentry event automatically; explicit sentry.CaptureException calls are reserved for recovered panics.", "reference", "technical", False,
     [("Sentry-go", "library"), ("slog", "library"), ("CaptureException", "method"), ("panic", "concept")],
     [("Sentry-go", "slog", "USES")],
     "how does sentry-go hook into slog and when is CaptureException still called explicitly",
     "sentry go slog handler capture exception error panic recover"),
    # --- 27 ---
    ("Unit tests use testify/assert for readable failure output plus testify/require when a failed precondition should stop the test; a bare t.Fatal-only style was mixing control flow with assertions confusingly.", "preference", "technical", False,
     [("testify", "library"), ("assert", "method"), ("require", "method"), ("t.Fatal", "api")],
     [("testify", "t.Fatal", "PREFERS")],
     "which test helpers replaced bare t.Fatal style and when is require chosen over assert",
     "testify assert require t fatal unit test helper precondition"),
    # --- 28 ---
    ("Interfaces are mocked with gomock via mockgen; hand-rolled mocks drifted every time a method got added and CI started flagging missing methods only after merge.", "decision", "technical", False,
     [("gomock", "library"), ("mockgen", "tool"), ("Interfaces", "concept")],
     [("gomock", "Interfaces", "APPLIES_TO")],
     "which mocking tool replaced hand-rolled mocks and which drift problem did generated mocks retire",
     "gomock mockgen interface mock hand roll drift method ci"),
    # --- 29 ---
    ("BDD-style integration tests for the reports service use gomega assertions inside ginkgo specs; the readable Describe and Context blocks made onboarding juniors onto the suite noticeably faster.", "fact", "technical", False,
     [("gomega", "library"), ("ginkgo", "library"), ("Describe", "api"), ("Context", "api"), ("reports service", "service")],
     [("ginkgo", "reports service", "APPLIES_TO")],
     "which BDD-style test stack covers the reports service and which block names aid onboarding",
     "gomega ginkgo describe context bdd reports service onboarding"),
    # --- 30 ---
    ("Production profiling uses net/http/pprof exposed on a private port; a runtime/trace capture for a minute every hour feeds a flamegraph dashboard that caught a goroutine leak last week.", "milestone", "technical", False,
     [("net/http/pprof", "library"), ("runtime/trace", "library"), ("flamegraph", "tool"), ("goroutine leak", "pattern")],
     [("net/http/pprof", "goroutine leak", "FIXES")],
     "which profiling tools catch production issues and how did they surface a goroutine leak last week",
     "pprof runtime trace flamegraph goroutine leak profile production"),
    # --- 31 ---
    ("Static assets are shipped with go:embed into a single binary; the old external templates directory failed silently when the deploy playbook skipped a step and the service came up template-less.", "decision", "technical", False,
     [("go:embed", "api"), ("templates", "concept"), ("binary", "concept")],
     [("go:embed", "templates", "REPLACES")],
     "which embed directive replaced the external templates directory after a silent deploy failure",
     "go embed templates directory deploy playbook silent failure binary"),
    # --- 32 ---
    ("Migration SQL files are served via embed.FS to the migrator so a deployed binary contains every migration it needs; no more shipping a sibling migrations folder next to the container image.", "architecture", "technical", False,
     [("embed.FS", "api"), ("SQL", "language"), ("migrator", "service"), ("container", "concept")],
     [("embed.FS", "migrator", "APPLIES_TO")],
     "how does the migrator carry its SQL files inside the deployed binary instead of a sibling folder",
     "embed fs sql migrator container migration binary sibling folder"),
    # --- 33 ---
    ("Platform-specific code gates with build tags: //go:build linux for cgroup probes and //go:build darwin for the dev-only Finder integration; the old runtime.GOOS branches were not stripped by the compiler.", "reference", "technical", False,
     [("build tags", "concept"), ("//go:build", "api"), ("runtime.GOOS", "api"), ("cgroup", "concept")],
     [("build tags", "runtime.GOOS", "REPLACES")],
     "which build-gate mechanism replaced runtime.GOOS branches and what dead-code benefit did it unlock",
     "build tag go build runtime goos linux darwin cgroup finder gate"),
    # --- 34 ---
    ("Release artefacts cross-compile from a single Linux runner via GOOS and GOARCH matrix; macOS arm64 and Windows amd64 drop out of the same make target without a second VM in the pipeline.", "milestone", "technical", False,
     [("GOOS", "api"), ("GOARCH", "api"), ("macOS arm64", "platform"), ("Windows amd64", "platform")],
     [],
     "which environment variables drive the cross-compile matrix and which target platforms fall out of it",
     "goos goarch cross compile macos arm64 windows amd64 matrix linux"),
    # --- 35 ---
    ("Dependency graph is pinned in go.mod with go.sum enforced under -mod=readonly in CI; a rogue transitive update slipped in once before we flipped that flag and broke a client for two hours.", "decision", "technical", False,
     [("go.mod", "file"), ("go.sum", "file"), ("-mod=readonly", "api"), ("CI", "concept")],
     [("-mod=readonly", "go.mod", "APPLIES_TO")],
     "which module flag closed the rogue transitive update hole after a two-hour client outage",
     "go mod sum readonly transitive dependency ci pin lock outage"),
    # --- 36 ---
    ("A replace directive in go.mod swaps the upstream oauth2 package for an internal fork while the CVE fix sits in review upstream; the replace scope is local only and never shipped to consumers.", "problem", "technical", False,
     [("replace directive", "api"), ("go.mod", "file"), ("oauth2", "library"), ("CVE", "concept")],
     [("replace directive", "oauth2", "APPLIES_TO")],
     "which go.mod directive pins the oauth2 fork while the upstream CVE fix is in review",
     "replace directive go mod oauth2 cve fork upstream review scope"),
    # --- 37 ---
    ("Monorepo uses go.work to expose the shared types module and the services that consume it; before workspaces, we juggled local replace directives across seven services and forgot one every refactor.", "milestone", "technical", False,
     [("go.work", "file"), ("workspace", "concept"), ("types module", "service"), ("replace directive", "api")],
     [("go.work", "replace directive", "REPLACES")],
     "which workspace file replaced the scattered replace directives across seven services in the monorepo",
     "go work workspace replace directive monorepo types module refactor"),
    # --- 38 ---
    ("Profile-guided optimisation landed in 1.21 and now ships with the hot services; a profile collected from prod replays into the compiler, and the rps uplift hit about nine percent on the search path.", "milestone", "technical", False,
     [("Profile-guided optimisation", "concept"), ("1.21", "date"), ("search path", "service"), ("compiler", "tool")],
     [("Profile-guided optimisation", "search path", "APPLIES_TO")],
     "which Go version introduced PGO and what rps improvement did the search path see after rollout",
     "profile guided optimisation pgo 1.21 rps uplift search production"),
    # --- 39 ---
    ("Native crypto bits still call into CGO for the hardware-backed PKCS11 HSM; pure-Go was not an option because the vendor driver is C-only and the ABI shifts per firmware.", "architecture", "technical", False,
     [("CGO", "concept"), ("PKCS11", "protocol"), ("HSM", "technology")],
     [("CGO", "PKCS11", "APPLIES_TO")],
     "why does the HSM integration still rely on CGO instead of pure-Go crypto",
     "cgo pkcs11 hsm native crypto vendor driver abi firmware"),
    # --- 40 ---
    ("Editor stack standardised on gopls with staticcheck integration; delve handles debugging and the earlier mix of guru, godef, and gocode across developer machines gave inconsistent rename results.", "decision", "technical", False,
     [("gopls", "tool"), ("staticcheck", "tool"), ("delve", "tool"), ("guru", "tool"), ("godef", "tool"), ("gocode", "tool")],
     [("gopls", "guru", "REPLACES"), ("gopls", "godef", "REPLACES"), ("gopls", "gocode", "REPLACES")],
     "which language server replaced the guru godef gocode mix and which companions did it pair with",
     "gopls staticcheck delve guru godef gocode rename language server"),
    # --- 41 ---
    ("Select across a done channel and a work channel is the cancellation template in every worker; the pattern is codified in the internal/workerutil package so new services adopt it without reinventing.", "architecture", "technical", False,
     [("Select", "api"), ("done channel", "pattern"), ("work channel", "pattern"), ("internal/workerutil", "library")],
     [("internal/workerutil", "Select", "USES")],
     "which internal package codifies the done-plus-work select template for worker cancellation",
     "select done work channel cancellation worker internal workerutil"),
    # --- 42 ---
    ("Panic recovery sits in a top-level middleware that logs the stack and returns 500; handlers no longer sprinkle defer recover blocks because the panic then got swallowed without a log line, masking bugs.", "decision", "technical", False,
     [("panic", "concept"), ("recover", "api"), ("middleware", "pattern"), ("defer", "api")],
     [("middleware", "recover", "USES")],
     "which recovery pattern replaced ad-hoc defer-recover in handlers and which visibility bug did it close",
     "panic recover middleware defer handler top level log swallow"),
    # --- 43. noise ---
    ("Somebody in the kitchen keeps stacking empty oat-milk cartons into a tower and the latest attempt is leaning dangerously toward the coffee grinder.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Benchmarks run under go test -bench with a -cpuprofile capture; the results feed back into the PGO input so the hot services ship with profiles gathered on the same workload as their CI benchmarks.", "fact", "technical", False,
     [("go test", "tool"), ("-bench", "api"), ("-cpuprofile", "api"), ("PGO", "concept")],
     [("go test", "PGO", "APPLIES_TO")],
     "how do go test benchmarks feed into the PGO input pipeline for hot services",
     "go test bench cpuprofile pgo benchmark ci input pipeline"),
    # --- 45 ---
    ("Race detector runs on every CI integration test with -race; a subtle unsync write to a map under a shared pointer surfaced in staging only after we turned the detector on across the whole suite.", "fact", "technical", False,
     [("Race detector", "tool"), ("-race", "api"), ("CI", "concept"), ("map", "concept")],
     [("Race detector", "map", "APPLIES_TO")],
     "which CI flag catches unsync map writes and which staging bug did it surface",
     "race detector go test race ci map unsync pointer staging"),
    # --- 46 ---
    ("The billing calculations package ships as a generic type-parameterised aggregator so integer and decimal variants share one code path; pre-1.18 we had two near-identical copies drifting apart every quarter.", "fact", "technical", False,
     [("generic", "concept"), ("1.18", "date"), ("aggregator", "service"), ("billing", "service")],
     [("generic", "billing", "APPLIES_TO")],
     "which Go 1.18 feature unified the integer and decimal billing aggregator into one code path",
     "generics 1.18 aggregator billing integer decimal type parameter"),
    # --- 47 ---
    ("Structured errors carry a sentinel per domain, wrapped with fmt.Errorf and checked by errors.Is at the boundary; handlers map sentinels to HTTP codes in one table so the mapping stays auditable.", "architecture", "technical", False,
     [("sentinel", "pattern"), ("fmt.Errorf", "api"), ("errors.Is", "api"), ("HTTP", "protocol")],
     [("errors.Is", "sentinel", "APPLIES_TO")],
     "how do sentinels map to HTTP codes at the handler boundary in one auditable table",
     "sentinel fmt errorf errors is http code handler boundary table"),
    # --- 48 ---
    ("Tracing context is propagated through grpc-go interceptors and net/http middleware that both write into the same context.Context keys; the admin tools stopped losing spans across the gateway hop.", "architecture", "technical", False,
     [("grpc-go", "library"), ("net/http", "library"), ("context.Context", "api"), ("interceptor", "pattern")],
     [("interceptor", "context.Context", "USES")],
     "which interceptor and middleware combo propagates trace context across grpc-go and net/http hops",
     "grpc go net http interceptor middleware context trace span gateway"),
    # --- 49 ---
    ("The CLI suite was ported from spf13/pflag-only parsing to cobra plus viper; subcommands, shell-completion, and env-var binding came along for free and the custom help-text hacks were deleted.", "milestone", "technical", False,
     [("cobra", "framework"), ("viper", "library"), ("pflag", "library"), ("shell-completion", "concept")],
     [("cobra", "pflag", "REPLACES")],
     "which CLI migration retired the pflag-only parser and what built-in features came along with it",
     "cobra viper pflag cli subcommand shell completion env var bind"),
    # --- 50 ---
    ("Panic traces go through a structured logger with zerolog hooks that scrub pii fields before the Sentry bridge fires; a past incident shipped a customer email into the Sentry event payload before the scrub existed.", "problem", "technical", False,
     [("zerolog", "library"), ("Sentry", "library"), ("pii", "concept"), ("Panic", "concept")],
     [("zerolog", "Sentry", "USES")],
     "which logger hook scrubs pii before Sentry ingests panic traces and which past leak motivated it",
     "zerolog sentry go hook pii scrub panic trace customer email leak"),
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
