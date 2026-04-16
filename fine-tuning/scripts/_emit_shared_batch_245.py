"""One-off emitter for shared-base batch-245 — technical domain (software testing, property-based testing, fuzzing, mutation, snapshot, coverage, contract testing).

Writes 50 rows to data/v2/shared/batch_245.tmp.jsonl with ids shared-12201..12250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_245.tmp.jsonl"
ID_OFFSET = 12200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Swapped the Python project from unittest to pytest for the parametrize decorator and fixture scopes; the old TestCase subclasses still work via collection but new suites live under tests/pytest.", "decision", "technical", False,
     [("unittest", "library"), ("pytest", "library"), ("TestCase", "pattern")],
     [("pytest", "unittest", "REPLACES")],
     "which Python test runner replaced unittest and which two features drove the migration",
     "pytest unittest parametrize fixture testcase python swap"),
    # --- 2 architecture ---
    ("The Node frontend runs Vitest in workspace mode: each package declares its own vite.config.ts and the root orchestrator fans the runs out to worker threads per package.", "architecture", "technical", False,
     [("Vitest", "library"), ("vite.config.ts", "file"), ("worker threads", "pattern")],
     [("Vitest", "worker threads", "USES")],
     "how does the Node monorepo parallelise test runs across packages under Vitest",
     "vitest workspace vite config worker thread monorepo package fan"),
    # --- 3 milestone ---
    ("Cut the end-to-end suite over to Playwright from Selenium; the cross-browser matrix now runs Chromium, Firefox, and WebKit in one CI job and flaky count on the login spec dropped from forty to three.", "milestone", "technical", False,
     [("Playwright", "framework"), ("Selenium", "framework"), ("Chromium", "platform"), ("Firefox", "platform"), ("WebKit", "platform")],
     [("Playwright", "Selenium", "REPLACES")],
     "which browser automation framework replaced Selenium and which three engines run in the single CI job",
     "playwright selenium chromium firefox webkit e2e flaky login"),
    # --- 4 decision ---
    ("Picked Jest over Mocha for the React component suite; the built-in snapshot support and zero-config jsdom environment beat wiring Chai, Sinon, and jsdom by hand.", "decision", "technical", False,
     [("Jest", "framework"), ("Mocha", "framework"), ("Chai", "library"), ("Sinon", "library"), ("jsdom", "library")],
     [("Jest", "Mocha", "PREFERS")],
     "which JavaScript test framework won over Mocha for the React component layer and why",
     "jest mocha chai sinon jsdom react component snapshot zero config"),
    # --- 5 architecture ---
    ("Property-based tests in the core parser use Hypothesis strategies composed from a grammar builder; the generated inputs shrink to minimal counterexamples and the shrink log gets attached to the bug report.", "architecture", "technical", False,
     [("Hypothesis", "library"), ("grammar builder", "pattern"), ("shrink", "concept")],
     [("Hypothesis", "grammar builder", "USES")],
     "how does the parser generate property-based inputs and what does Hypothesis do with a failing case",
     "hypothesis property strategy grammar builder shrink counterexample parser"),
    # --- 6 reference ---
    ("The team reference for Haskell property tests points at QuickCheck; the wiki page links the original Claessen and Hughes paper and a curated list of Arbitrary instances for the domain types.", "reference", "technical", False,
     [("QuickCheck", "library"), ("Haskell", "language"), ("Arbitrary", "pattern")],
     [("QuickCheck", "Haskell", "APPLIES_TO")],
     "where do engineers look up the canonical Haskell property-testing framework and its Arbitrary helpers",
     "quickcheck haskell arbitrary claessen hughes property reference wiki"),
    # --- 7 fact ---
    ("The Rust service uses criterion.rs for microbenchmarks; the baseline JSON lives under target/criterion and PR runs diff against main's committed baseline to flag regressions beyond five percent.", "fact", "technical", False,
     [("criterion.rs", "library"), ("Rust", "language"), ("target/criterion", "file")],
     [("criterion.rs", "Rust", "APPLIES_TO")],
     "which Rust benchmarking library does the service use and how does it detect regressions in PR runs",
     "criterion rs rust benchmark baseline target pr diff regression"),
    # --- 8 fact ---
    ("Go test coverage aggregates across packages with go cover and the merged profile feeds into a threshold gate in CI; the build fails if coverage on the billing/ tree drops below eighty percent.", "fact", "technical", False,
     [("go cover", "tool"), ("Go", "language"), ("billing/", "file")],
     [("go cover", "Go", "APPLIES_TO")],
     "how does the Go CI enforce a coverage floor on the billing subtree across all packages",
     "go cover coverage billing package profile merge ci gate threshold"),
    # --- 9 decision ---
    ("Adopted Stryker for mutation testing on the TypeScript codebase; the Jest runner plug-in feeds surviving mutants back to the PR as review comments so uncovered branches don't slip past coverage theatre.", "decision", "technical", False,
     [("Stryker", "tool"), ("TypeScript", "language"), ("Jest", "framework")],
     [("Stryker", "Jest", "USES")],
     "which mutation testing tool runs against the TypeScript suite and how does it surface surviving mutants",
     "stryker mutation typescript jest mutant survive pr review coverage"),
    # --- 10 noise ---
    ("The kitchen espresso machine throws an E5 error every other morning and the office manager keeps a printed decision tree taped to the side panel.", "fact", "noise", True, [], [], None, None),
    # --- 11 architecture ---
    ("Coverage.py runs with the branch plugin and multiprocessing context enabled; each pytest-xdist worker writes a .coverage.<pid> file that coverage combine merges before report generation.", "architecture", "technical", False,
     [("Coverage.py", "tool"), ("pytest-xdist", "library"), (".coverage", "file")],
     [("Coverage.py", "pytest-xdist", "USES")],
     "how does Coverage.py aggregate branch coverage across pytest-xdist workers before generating the report",
     "coverage py branch multiprocessing xdist worker combine merge"),
    # --- 12 milestone ---
    ("Landed OSS-Fuzz integration for the parser library; the first week of continuous fuzzing caught seven unique crashes and the Google-hosted ClusterFuzz dashboard replaced our weekly manual AFL++ runs.", "milestone", "technical", False,
     [("OSS-Fuzz", "service"), ("ClusterFuzz", "service"), ("AFL++", "tool"), ("Google", "organization")],
     [("ClusterFuzz", "AFL++", "REPLACES"), ("OSS-Fuzz", "Google", "AUTHORED_BY")],
     "which continuous fuzzing service replaced the weekly manual AFL++ runs on the parser library",
     "oss fuzz clusterfuzz afl google parser crash continuous dashboard"),
    # --- 13 decision ---
    ("Picked libFuzzer over honggfuzz for the in-process harness; sanitizer compatibility with AddressSanitizer and coverage guidance via SanitizerCoverage made the build integration a one-flag change on Clang.", "decision", "technical", False,
     [("libFuzzer", "tool"), ("honggfuzz", "tool"), ("AddressSanitizer", "tool"), ("SanitizerCoverage", "tool"), ("Clang", "tool")],
     [("libFuzzer", "honggfuzz", "PREFERS"), ("libFuzzer", "AddressSanitizer", "USES")],
     "which in-process fuzzer beat honggfuzz for the harness and which sanitizer integration sealed the choice",
     "libfuzzer honggfuzz sanitizer address clang coverage harness flag"),
    # --- 14 decision ---
    ("The Rust crate fuzzes parsers with cargo-fuzz driving libFuzzer underneath; corpus minimisation runs nightly and the trophy directory feeds straight into the regression suite as cargo test inputs.", "decision", "technical", False,
     [("cargo-fuzz", "tool"), ("libFuzzer", "tool"), ("Rust", "language"), ("cargo test", "command")],
     [("cargo-fuzz", "libFuzzer", "USES")],
     "how does the Rust crate wire cargo-fuzz into the nightly regression workflow",
     "cargo fuzz rust libfuzzer corpus trophy minimise regression nightly"),
    # --- 15 fact ---
    ("go-fuzz runs on the protobuf decoder pipeline; the corpus lives under fuzz/corpus and the dictionary of known field tags accelerates coverage on rare wire types.", "fact", "technical", False,
     [("go-fuzz", "tool"), ("protobuf", "protocol"), ("fuzz/corpus", "file")],
     [("go-fuzz", "protobuf", "APPLIES_TO")],
     "which Go fuzzer runs on the protobuf decoder and how does the field-tag dictionary help coverage",
     "go fuzz protobuf decoder corpus dictionary tag wire coverage"),
    # --- 16 reference ---
    ("Internal fuzzing playbook links the Nautilus paper for structure-aware grammar fuzzing; the grammar.py examples cover SQL and JSON and are the starting point for any new parser harness.", "reference", "technical", False,
     [("Nautilus", "tool"), ("grammar.py", "file"), ("SQL", "language"), ("JSON", "technology")],
     [("Nautilus", "SQL", "APPLIES_TO")],
     "where does the fuzzing playbook send engineers for structure-aware grammar examples on new parsers",
     "nautilus structure aware grammar sql json playbook parser harness"),
    # --- 17 preference ---
    ("Team prefers fast-check over jsverify for TypeScript property tests; the shrinker is deterministic, the fc.record combinator composes cleanly, and the Vitest integration is a two-line import.", "preference", "technical", False,
     [("fast-check", "library"), ("jsverify", "library"), ("TypeScript", "language"), ("Vitest", "library")],
     [("fast-check", "jsverify", "PREFERS")],
     "which TypeScript property-testing library does the team prefer and which three properties sealed it",
     "fast check jsverify typescript vitest shrinker record combinator"),
    # --- 18 architecture ---
    ("Ruby service runs RSpec with shared contexts per bounded context; the before(:suite) hook loads a frozen fixture snapshot so every spec starts from a deterministic world without a Rails reload.", "architecture", "technical", False,
     [("RSpec", "framework"), ("Ruby", "language"), ("before(:suite)", "api"), ("Rails", "framework")],
     [("RSpec", "Rails", "APPLIES_TO")],
     "how does the Ruby service keep RSpec specs deterministic without reloading Rails between examples",
     "rspec ruby rails before suite shared context fixture bounded deterministic"),
    # --- 19 decision ---
    ("Dropped Cypress for Playwright on the admin portal suite; the parallel shard model, trace viewer, and network interception API outran what Cypress could do without the paid dashboard.", "decision", "technical", False,
     [("Cypress", "framework"), ("Playwright", "framework"), ("trace viewer", "tool")],
     [("Playwright", "Cypress", "REPLACES")],
     "which end-to-end tool took over the admin portal suite and which three capabilities decided it",
     "cypress playwright trace viewer parallel shard network intercept admin"),
    # --- 20 preference ---
    ("Engineers reach for WebdriverIO on the Appium-backed mobile web suite; the devtools service layer and the Mocha-inside-wdio runner make debugging a real iPhone simulator bearable.", "preference", "technical", False,
     [("WebdriverIO", "framework"), ("Appium", "framework"), ("Mocha", "framework"), ("iPhone simulator", "platform")],
     [("WebdriverIO", "Appium", "USES")],
     "which browser-automation framework wraps Appium for the iPhone simulator suite and which runner sits inside it",
     "webdriverio appium mocha iphone simulator mobile web devtools"),
    # --- 21 fact ---
    ("XCTest drives the iOS unit and UI suites; the ui-tests target launches the app with XCUIApplication and screenshots are attached to the test report on failure via XCTAttachment.", "fact", "technical", False,
     [("XCTest", "framework"), ("iOS", "platform"), ("XCUIApplication", "api"), ("XCTAttachment", "api")],
     [("XCTest", "iOS", "APPLIES_TO")],
     "which native framework runs the iOS unit and UI tests and how are failure screenshots attached",
     "xctest ios xcuiapplication attachment ui unit screenshot report"),
    # --- 22 architecture ---
    ("Android instrumentation tests run under Espresso in the emulator and Robolectric in JVM mode; the split means PR CI gets Robolectric speed while nightly runs the full Espresso matrix on four API levels.", "architecture", "technical", False,
     [("Espresso", "framework"), ("Robolectric", "framework"), ("Android", "platform"), ("JVM", "platform")],
     [("Robolectric", "Espresso", "IMPROVES_ON")],
     "how does the Android suite split between Robolectric JVM tests and Espresso emulator tests across CI and nightly",
     "espresso robolectric android jvm emulator api level pr nightly"),
    # --- 23 decision ---
    ("JUnit 5 replaced JUnit 4 on the Spring service after the migration guide landed; parameterised tests, dynamic test containers, and the BeforeAll/AfterAll lifecycle got a lot cleaner with the Jupiter API.", "decision", "technical", False,
     [("JUnit 5", "framework"), ("JUnit 4", "framework"), ("Spring", "framework"), ("Jupiter", "api")],
     [("JUnit 5", "JUnit 4", "REPLACES")],
     "which JUnit major version replaced JUnit 4 on the Spring service and which API surfaced the lifecycle cleanup",
     "junit 5 4 spring jupiter parameterised dynamic container lifecycle"),
    # --- 24 preference ---
    ("TestNG survives on the legacy integration suite because the data-provider decoupling and group-based test ordering still beat JUnit 5's equivalent for our parallel provisioning workflow.", "preference", "technical", False,
     [("TestNG", "framework"), ("JUnit 5", "framework"), ("data-provider", "pattern")],
     [("TestNG", "JUnit 5", "PREFERS")],
     "which legacy Java runner beats JUnit 5 for the integration suite and which two features keep it in place",
     "testng junit 5 data provider group order parallel provision legacy"),
    # --- 25 problem ---
    ("Flaky Playwright tests on the checkout page traced to networkidle waits racing with a polling script; swapping to waitForResponse on the specific order endpoint cut the flake rate by two orders of magnitude.", "problem", "technical", False,
     [("Playwright", "framework"), ("networkidle", "api"), ("waitForResponse", "api"), ("checkout", "project")],
     [("waitForResponse", "networkidle", "REPLACES")],
     "which Playwright wait primitive replaced networkidle to fix the checkout-page flake and how big was the win",
     "playwright networkidle waitforresponse checkout flake race poll"),
    # --- 26 fact ---
    ("Snapshot tests on React components use Jest serializers to strip className hashes and inline event handlers; the golden files live under __snapshots__/ and review surfaces diffs as part of the PR.", "fact", "technical", False,
     [("Jest", "framework"), ("React", "framework"), ("__snapshots__/", "file"), ("className", "concept")],
     [("Jest", "React", "APPLIES_TO")],
     "how do the React snapshot tests avoid churn from className hashes and inline handlers in the golden files",
     "jest react snapshot serializer classname handler golden pr diff"),
    # --- 27 decision ---
    ("Rust CLI tests write golden-file assertions with insta; the accepted snapshots live under snapshots/ and cargo insta review is the only path to approve a change, which keeps drive-by updates out of PRs.", "decision", "technical", False,
     [("insta", "library"), ("Rust", "language"), ("snapshots/", "file"), ("cargo insta review", "command")],
     [("insta", "Rust", "APPLIES_TO")],
     "which Rust snapshot library gates golden-file updates behind a review command and where do the snapshots live",
     "insta rust snapshot cargo review golden cli gate approve"),
    # --- 28 architecture ---
    ("Istanbul via NYC collects coverage on the Express backend; source maps carry the coverage back to .ts files and the lcov report feeds both the Codecov upload and the lcov.info artifact for local viewers.", "architecture", "technical", False,
     [("Istanbul", "tool"), ("NYC", "tool"), ("Express", "framework"), ("Codecov", "service"), ("lcov", "tool")],
     [("NYC", "Istanbul", "USES")],
     "how does the Express backend collect coverage on TypeScript sources and where does the lcov output go",
     "istanbul nyc express codecov lcov source map typescript coverage"),
    # --- 29 fact ---
    ("The C++ service uses gcov with lcov post-processing; the genhtml report lands in build/coverage/html and the SonarQube scanner ingests the intermediate .info file for trend tracking.", "fact", "technical", False,
     [("gcov", "tool"), ("lcov", "tool"), ("SonarQube", "service"), ("genhtml", "command")],
     [("lcov", "gcov", "USES")],
     "which C++ coverage toolchain feeds SonarQube and what post-processing generates the HTML report",
     "gcov lcov genhtml sonarqube cplus coverage html trend info"),
    # --- 30 milestone ---
    ("Flipped Rust coverage from tarpaulin to grcov backed by source-based instrumentation; the run time on the full workspace dropped from nine minutes to one and the line-level output matches rustc exactly.", "milestone", "technical", False,
     [("tarpaulin", "tool"), ("grcov", "tool"), ("Rust", "language"), ("rustc", "tool")],
     [("grcov", "tarpaulin", "REPLACES")],
     "which Rust coverage tool replaced tarpaulin and what runtime win did source-based instrumentation land",
     "tarpaulin grcov rust rustc source instrumentation workspace minute"),
    # --- 31 architecture ---
    ("Consumer-driven contract tests sit between the web app and the orders API via Pact; the web team publishes pacts to the broker and the orders team's CI verifies against the pinned pact version.", "architecture", "technical", False,
     [("Pact", "framework"), ("orders API", "service"), ("web app", "project"), ("broker", "service")],
     [("Pact", "orders API", "APPLIES_TO")],
     "how do the web app and the orders API use Pact to keep their contract from silently drifting",
     "pact consumer driven contract broker orders web verify pin"),
    # --- 32 decision ---
    ("Spring Cloud Contract replaced the ad-hoc OpenAPI round-trip tests on the billing service; Groovy DSL stubs generate WireMock fixtures and the consumers pull them from the Artifactory stubs repository.", "decision", "technical", False,
     [("Spring Cloud Contract", "framework"), ("OpenAPI", "protocol"), ("WireMock", "library"), ("Artifactory", "service"), ("Groovy", "language")],
     [("Spring Cloud Contract", "OpenAPI", "REPLACES")],
     "which contract-first tool replaced the OpenAPI round-trip tests on billing and how do consumers pull the stubs",
     "spring cloud contract openapi wiremock artifactory groovy billing stub"),
    # --- 33 problem ---
    ("The mutmut run on the payment validator kept reporting surviving mutants on a dead branch; root cause was a guard import that pytest discovery never loaded, and adding it to conftest.py collapsed the survivor set.", "problem", "technical", False,
     [("mutmut", "tool"), ("pytest", "library"), ("conftest.py", "file"), ("payment validator", "project")],
     [("mutmut", "pytest", "USES")],
     "which fix on the payment validator made mutmut stop flagging a dead branch as a surviving mutant",
     "mutmut pytest conftest payment validator survivor dead branch guard"),
    # --- 34 architecture ---
    ("PIT drives mutation testing on the JVM side; the history file under build/pitest.bin caches results between runs and incremental mode restricts mutants to files touched in the last commit range.", "architecture", "technical", False,
     [("PIT", "tool"), ("JVM", "platform"), ("build/pitest.bin", "file")],
     [("PIT", "JVM", "APPLIES_TO")],
     "how does PIT avoid re-running every mutant on each PR while still covering changed files",
     "pit mutation jvm pitest history incremental commit range cache"),
    # --- 35 preference ---
    ("Engineers reach for cargo-mutants on Rust libraries over manual fault injection; the JSON output is easy to diff across runs and the skip-calls filter keeps test-only code out of the mutant list.", "preference", "technical", False,
     [("cargo-mutants", "tool"), ("Rust", "language")],
     [("cargo-mutants", "Rust", "APPLIES_TO")],
     "which mutation tool do Rust engineers reach for and which filter keeps test-only code off the mutant list",
     "cargo mutants rust json diff skip calls test library mutation"),
    # --- 36 decision ---
    ("PropEr runs on the Erlang billing subsystem for property-based tests; ScalaCheck did not extend to the OTP behaviours and writing custom generators in PropEr mapped one-to-one to our gen_server states.", "decision", "technical", False,
     [("PropEr", "library"), ("ScalaCheck", "library"), ("Erlang", "language"), ("gen_server", "pattern")],
     [("PropEr", "ScalaCheck", "PREFERS")],
     "which BEAM property-testing library won over ScalaCheck on the Erlang billing subsystem and why",
     "proper scalacheck erlang otp gen server billing property generator"),
    # --- 37 reference ---
    ("Scala reference for property testing is ScalaCheck with the scalatestplus-scalacheck glue; the README links the Scalaz Arbitrary module for FP-shaped generators on the typeclass-heavy services.", "reference", "technical", False,
     [("ScalaCheck", "library"), ("Scala", "language"), ("scalatestplus-scalacheck", "library"), ("Scalaz", "library")],
     [("ScalaCheck", "Scala", "APPLIES_TO")],
     "where do Scala engineers look up the canonical property-testing setup and its FP-friendly generators",
     "scalacheck scala scalatestplus scalaz arbitrary property reference"),
    # --- 38 architecture ---
    ("The differential testing harness compares outputs from the Rust implementation against the reference C one on shared fuzz inputs; mismatches dump both stacks and the triaging script auto-files a ticket on the Rust side.", "architecture", "technical", False,
     [("differential testing", "method"), ("Rust", "language"), ("C", "language"), ("triaging script", "tool")],
     [("Rust", "C", "IMPLEMENTS")],
     "how does the differential harness surface mismatches between the Rust and reference C implementations",
     "differential testing rust c reference fuzz mismatch stack triage"),
    # --- 39 problem ---
    ("Coverage-guided fuzzing on the TLS parser stalled at ninety-two percent coverage; adding an AFL++ dictionary of well-known ciphersuite bytes unblocked the plateau within the next corpus hour.", "problem", "technical", False,
     [("AFL++", "tool"), ("TLS", "protocol"), ("dictionary", "pattern"), ("ciphersuite", "concept")],
     [("AFL++", "TLS", "APPLIES_TO")],
     "what unblocked the AFL++ coverage plateau on the TLS parser and how fast did it move",
     "afl coverage tls ciphersuite dictionary plateau fuzz parser hour"),
    # --- 40 milestone ---
    ("Shipped a zzuf-based mutator in front of the media-decoder fuzz target; the byte-flip density tuning found three heap-overflows in the first afternoon that five weeks of blind fuzzing never hit.", "milestone", "technical", False,
     [("zzuf", "tool"), ("media-decoder", "project"), ("heap-overflow", "error")],
     [("zzuf", "media-decoder", "APPLIES_TO")],
     "which randomising frontend unearthed memory-corruption bugs on the decoder that weeks of raw fuzz inputs had missed",
     "zzuf media decoder heap overflow byte flip density fuzz afternoon"),
    # --- 41 fact ---
    ("Go's built-in test framework runs with -race on the concurrency-heavy scheduler package; the data-race detector is required on every PR touching goroutine-local state and failing it blocks merge.", "fact", "technical", False,
     [("Go", "language"), ("-race", "command"), ("scheduler", "project"), ("goroutine", "concept")],
     [("Go", "scheduler", "APPLIES_TO")],
     "which Go test flag guards the scheduler package from goroutine-local data races on every PR",
     "go test race scheduler goroutine data race concurrency pr block"),
    # --- 42 decision ---
    ("Switched the Rust workspace from the deprecated rustc-test harness to the built-in test framework with #[test] everywhere; the cargo test runner plus nextest shards replaced the bespoke runner wrapper entirely.", "decision", "technical", False,
     [("cargo test", "command"), ("nextest", "tool"), ("rustc-test", "tool"), ("Rust", "language")],
     [("cargo test", "rustc-test", "REPLACES")],
     "which Rust test toolchain replaced the rustc-test wrapper and which sharding tool pairs with cargo test",
     "cargo test nextest rustc shard rust workspace runner wrapper"),
    # --- 43 noise ---
    ("Someone in the back row of the all-hands asked about office plants and the facilities lead now keeps a watering spreadsheet pinned to the fridge.", "fact", "noise", True, [], [], None, None),
    # --- 44 reference ---
    ("End-to-end pipeline records Playwright traces on first retry only; the trace.zip artifact is uploaded to the GitHub Actions run and linked from the flaky-test triage dashboard via a run-id query.", "reference", "technical", False,
     [("Playwright", "framework"), ("trace.zip", "file"), ("GitHub Actions", "service"), ("triage dashboard", "project")],
     [("Playwright", "GitHub Actions", "DEPLOYED_ON")],
     "how does the e2e pipeline surface Playwright traces from flaky retries into the triage dashboard",
     "playwright trace zip github actions flaky retry triage dashboard"),
    # --- 45 milestone ---
    ("Rolled the mutation-testing gate out to the whole platform repo after the pilot on the payments module; Stryker's aggregate score sits at seventy-four and the threshold in CI blocks merges below seventy.", "milestone", "technical", False,
     [("Stryker", "tool"), ("payments module", "project"), ("platform repo", "project")],
     [("Stryker", "platform repo", "APPLIES_TO")],
     "which mutation score threshold did the platform-wide Stryker rollout settle on after the payments pilot",
     "stryker mutation platform payments pilot threshold seventy merge gate"),
    # --- 46 reference ---
    ("Internal fuzzing reference links the libFuzzer tutorial and the sanitizer flag cheatsheet; the onboarding checklist asks every new harness author to read both before writing a FuzzTarget function.", "reference", "technical", False,
     [("libFuzzer", "tool"), ("FuzzTarget", "api"), ("sanitizer", "tool")],
     [("libFuzzer", "sanitizer", "USES")],
     "where does onboarding point fuzz-harness authors to learn libFuzzer conventions and sanitizer flags",
     "libfuzzer fuzz target sanitizer cheatsheet tutorial onboarding harness"),
    # --- 47 milestone ---
    ("Hit fifty thousand Hypothesis examples per night on the currency-conversion core; the shrink database accumulates the minimal failing cases and the CI job reruns them as explicit regression fixtures.", "milestone", "technical", False,
     [("Hypothesis", "library"), ("currency-conversion", "project"), ("shrink database", "pattern")],
     [("Hypothesis", "currency-conversion", "APPLIES_TO")],
     "which nightly property-testing volume did the currency-conversion core hit and how are shrunk failures reused",
     "hypothesis shrink database currency conversion nightly regression example"),
    # --- 48 decision ---
    ("Picked ScalaTest with the FlatSpec style for new Scala services; the given-when-then BDD phrasing reads closer to the acceptance criteria and the Matcher DSL shrank the per-assert boilerplate.", "decision", "technical", False,
     [("ScalaTest", "framework"), ("FlatSpec", "pattern"), ("Scala", "language"), ("Matcher DSL", "api")],
     [("ScalaTest", "Scala", "APPLIES_TO")],
     "which Scala test framework and spec style do new services pick and which DSL shrank assertion boilerplate",
     "scalatest flatspec scala matcher bdd given when then acceptance"),
    # --- 49 reference ---
    ("Mutation-testing playbook references the PIT configuration for our gradle plugin and the Stryker config for the JS monorepo; both link the Offutt mutation-operator taxonomy as the underlying catalogue.", "reference", "technical", False,
     [("PIT", "tool"), ("Stryker", "tool"), ("gradle", "tool"), ("Offutt", "person")],
     [("PIT", "Stryker", "RELATED_TO")],
     "where does the mutation-testing playbook point engineers for PIT and Stryker config plus the operator taxonomy",
     "pit stryker gradle offutt mutation operator playbook catalogue"),
    # --- 50 milestone ---
    ("Made the fuzzing build matrix green on all four sanitizers in one CI job: AddressSanitizer, UndefinedBehaviorSanitizer, MemorySanitizer, and ThreadSanitizer each run the smoke corpus in their own container.", "milestone", "technical", False,
     [("AddressSanitizer", "tool"), ("UndefinedBehaviorSanitizer", "tool"), ("MemorySanitizer", "tool"), ("ThreadSanitizer", "tool")],
     [("AddressSanitizer", "UndefinedBehaviorSanitizer", "RELATED_TO")],
     "which four sanitizers share the green fuzzing matrix and how are they isolated from each other",
     "address undefined memory thread sanitizer fuzz matrix container smoke"),
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
