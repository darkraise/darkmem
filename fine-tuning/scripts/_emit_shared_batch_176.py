"""One-off emitter for shared-base batch-176 — technical domain (load and performance testing: k6, Locust, Gatling, JMeter, wrk, vegeta, Lighthouse CI, Core Web Vitals, percentile latency, Little's law, open vs closed workload models).

Writes 50 rows to data/v2/shared/batch_176.tmp.jsonl with ids shared-08751..08800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_176.tmp.jsonl"
ID_OFFSET = 8750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Replaced the legacy JMeter test plan with a k6 script authored in JavaScript; the new suite runs in CI and emits Prometheus metrics without the XML-driven GUI workflow the team always dreaded.", "decision", "technical", False,
     [("JMeter", "tool"), ("k6", "tool"), ("JavaScript", "language"), ("Prometheus", "service")],
     [("k6", "JMeter", "REPLACES"), ("k6", "Prometheus", "COMMUNICATES_WITH")],
     "which load-testing tool replaced the JMeter plan and where do its metrics land in CI",
     "k6 jmeter javascript prometheus ci replace load test plan"),
    # --- 2 ---
    ("The checkout API ladder uses a ramping-arrival-rate k6 executor targeting an open workload model; fixed VUs masked queueing behaviour on the old closed-model runs and hid the real p99 spike.", "decision", "technical", False,
     [("k6", "tool"), ("ramping-arrival-rate", "pattern"), ("open workload model", "concept"), ("closed-model", "concept"), ("p99", "concept")],
     [("open workload model", "closed-model", "REPLACES")],
     "which k6 executor and workload model did the checkout API ladder adopt to expose queueing at p99",
     "k6 ramping arrival rate open workload closed checkout p99 queue"),
    # --- 3 ---
    ("Locust's master/worker cluster drives the onboarding soak for ten hours on a single node pool; a k6 variant exists but Python test authoring wins for the analytics team's skill mix.", "preference", "technical", False,
     [("Locust", "tool"), ("k6", "tool"), ("Python", "language"), ("onboarding", "project")],
     [("Locust", "k6", "PREFERS")],
     "which load-testing tool did the analytics team prefer for the onboarding soak and why",
     "locust k6 python soak onboarding analytics team preference"),
    # --- 4 ---
    ("Gatling replaced the in-house Scala load harness for the payments gateway; the built-in HTML report cut triage time because p95 and p99 charts come pre-rendered per scenario.", "decision", "technical", False,
     [("Gatling", "tool"), ("Scala", "language"), ("payments gateway", "service"), ("p95", "concept"), ("p99", "concept")],
     [("Gatling", "Scala", "REPLACES")],
     "which load tool replaced the in-house Scala harness for payments and what report did it ship",
     "gatling scala payments load harness html report p95 p99 triage"),
    # --- 5 ---
    ("Artillery is wired into the Playwright browser-mode worker for the login flow smoke at peak traffic; the YAML scenario file reuses the same auth fixture the E2E suite loads.", "decision", "technical", False,
     [("Artillery", "tool"), ("Playwright", "framework"), ("YAML", "technology"), ("login flow", "pattern")],
     [("Artillery", "Playwright", "USES")],
     "how does the login-flow peak-traffic smoke combine Artillery with Playwright at the fixture layer",
     "artillery playwright yaml login flow auth fixture e2e smoke peak"),
    # --- 6 ---
    ("Switched the micro-benchmark harness from wrk to wrk2 because wrk's coordinated omission hides tail latency; the constant-throughput mode in wrk2 now drives the edge-cache baseline.", "decision", "technical", False,
     [("wrk", "tool"), ("wrk2", "tool"), ("coordinated omission", "concept"), ("edge-cache", "service")],
     [("wrk2", "wrk", "REPLACES"), ("wrk2", "coordinated omission", "FIXES")],
     "why did the edge-cache benchmark swap wrk for wrk2 and which artefact did it eliminate",
     "wrk wrk2 coordinated omission edge cache baseline tail latency swap"),
    # --- 7 ---
    ("hey is the go-to quick-and-dirty load probe during incident triage; the single binary ships to any ops jump host and a two-minute run often pinpoints the regressing endpoint before k6 spins up.", "preference", "technical", False,
     [("hey", "tool"), ("k6", "tool"), ("jump host", "infrastructure")],
     [("hey", "k6", "PREFERS")],
     "which quick load probe does the ops team reach for during incident triage and why over k6",
     "hey k6 incident triage jump host quick load probe regression"),
    # --- 8 ---
    ("vegeta drives the constant-rate attack for the public-read endpoint soak; the targets file plus a ten-minute run produces a clean HDR histogram for Tom's latency review doc.", "fact", "technical", False,
     [("vegeta", "tool"), ("HDR histogram", "concept"), ("public-read", "service")],
     [("vegeta", "HDR histogram", "PRODUCES")],
     "which tool drives the constant-rate public-read soak and what output feeds the latency review",
     "vegeta constant rate attack public read soak hdr histogram targets"),
    # --- 9 ---
    ("drill and bombardier share the Rust HTTP-load niche; we standardised on bombardier for reproducible throughput numbers because drill's per-request jitter produced misleading p50 under low concurrency.", "decision", "technical", False,
     [("drill", "tool"), ("bombardier", "tool"), ("Rust", "language"), ("p50", "concept")],
     [("bombardier", "drill", "PREFERS")],
     "which Rust HTTP-load tool won the standardisation and what drove the choice at low concurrency",
     "drill bombardier rust http load throughput p50 concurrency jitter"),
    # --- 10. noise ---
    ("The office fern on the south-facing window has outgrown its pot and someone labelled it 'Fernandez' with a sticky note.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("siege survives in the cron-driven availability watch because its --reps and --concurrent flags match the legacy on-call runbook exactly; a rewrite to k6 is tracked but not scheduled.", "fact", "technical", False,
     [("siege", "tool"), ("k6", "tool"), ("cron", "tool"), ("on-call runbook", "publication")],
     [],
     "which legacy load tool stayed in the cron availability watch and what blocks the k6 rewrite",
     "siege cron availability reps concurrent on call runbook legacy k6"),
    # --- 12 ---
    ("Playwright performance mode captures trace.json with CPU throttle at four-times slowdown to approximate a mid-tier Android device; the navigation-timing deltas feed the weekly perf regression board.", "architecture", "technical", False,
     [("Playwright", "framework"), ("trace.json", "file"), ("Android", "platform"), ("navigation-timing", "api")],
     [],
     "how does Playwright performance mode simulate a mid-tier device and what feeds the weekly perf board",
     "playwright performance trace json cpu throttle android navigation timing"),
    # --- 13 ---
    ("Lighthouse CI gates the marketing-site PRs on an LCP budget of 2.5 seconds and a CLS budget of 0.1; the budget.json lives beside the repo so product can adjust without backend review.", "architecture", "technical", False,
     [("Lighthouse CI", "tool"), ("LCP", "concept"), ("CLS", "concept"), ("budget.json", "file"), ("marketing-site", "project")],
     [("Lighthouse CI", "marketing-site", "APPLIES_TO")],
     "which budgets does Lighthouse CI enforce on marketing-site PRs and where does product adjust them",
     "lighthouse ci lcp cls budget json marketing site pr gate product"),
    # --- 14 ---
    ("Migrated synthetic checkout monitors from WebPageTest to SpeedCurve for the Core Web Vitals dashboard; SpeedCurve's per-deploy marker annotations directly overlay deploy IDs onto LCP and INP lines.", "decision", "technical", False,
     [("WebPageTest", "tool"), ("SpeedCurve", "tool"), ("Core Web Vitals", "concept"), ("LCP", "concept"), ("INP", "concept")],
     [("SpeedCurve", "WebPageTest", "REPLACES")],
     "which synthetic monitoring tool replaced WebPageTest for Core Web Vitals and what feature sealed it",
     "speedcurve webpagetest core web vitals lcp inp deploy marker synthetic"),
    # --- 15 ---
    ("Calibre runs the mobile-first journey suite for the storefront; the budgets feed a Slack webhook the moment any p75 INP sample crosses 200 ms on the catalog navigation step.", "fact", "technical", False,
     [("Calibre", "tool"), ("storefront", "project"), ("INP", "concept"), ("Slack", "service")],
     [("Calibre", "Slack", "COMMUNICATES_WITH")],
     "which synthetic platform runs the storefront mobile suite and how does it surface INP budget breaches",
     "calibre storefront mobile inp slack webhook p75 catalog navigation"),
    # --- 16 ---
    ("LCP on the product-detail page dropped from 3.8 s to 1.9 s after inlining the hero-image fetchpriority=high hint and serving a responsive AVIF; the change landed in the Q3 perf milestone.", "milestone", "technical", False,
     [("LCP", "concept"), ("fetchpriority", "api"), ("AVIF", "technology"), ("product-detail", "project")],
     [("fetchpriority", "LCP", "IMPROVES_ON")],
     "which two changes cut the product-detail LCP from 3.8 s to 1.9 s and when did they land",
     "lcp product detail fetchpriority avif hero image q3 perf milestone"),
    # --- 17 ---
    ("CLS regressed to 0.32 on the blog after an A/B framework injected a late-loading banner; the fix reserved height via aspect-ratio on the slot and the layout-shift score returned to 0.04.", "problem", "technical", False,
     [("CLS", "concept"), ("A/B framework", "framework"), ("aspect-ratio", "api"), ("blog", "project")],
     [("aspect-ratio", "CLS", "FIXES")],
     "which CSS technique fixed the blog CLS regression caused by a late A/B banner injection",
     "cls aspect ratio blog a b framework banner layout shift score"),
    # --- 18 ---
    ("INP replaced FID as the Core Web Vitals interactivity metric in the dashboard after the March 2024 cut-over; we backfilled six months of RUM traces so trend lines bridge the change.", "milestone", "technical", False,
     [("INP", "concept"), ("FID", "concept"), ("Core Web Vitals", "concept"), ("RUM", "concept"), ("March 2024", "date")],
     [("INP", "FID", "REPLACES")],
     "which interactivity metric replaced FID in Core Web Vitals and how did we handle the trend discontinuity",
     "inp fid core web vitals march 2024 rum backfill trend line dashboard"),
    # --- 19 ---
    ("Shipped a RUM agent based on the web-vitals library that batches samples every 30 seconds to the ingestion API; sampling is keyed on session id so high-traffic pages don't drown the pipeline.", "architecture", "technical", False,
     [("RUM", "concept"), ("web-vitals", "library"), ("ingestion API", "api"), ("session id", "concept")],
     [("RUM", "web-vitals", "USES")],
     "how does the RUM agent batch and sample samples to avoid drowning the ingestion pipeline",
     "rum web vitals library batch sample session id ingestion api traffic"),
    # --- 20 ---
    ("Synthetic monitoring from three geo probes runs every five minutes against the login and checkout paths; a probe miss for two consecutive intervals fires the PagerDuty Urgent policy.", "reference", "technical", False,
     [("Synthetic monitoring", "concept"), ("PagerDuty", "service"), ("login", "pattern"), ("checkout", "pattern")],
     [("Synthetic monitoring", "PagerDuty", "COMMUNICATES_WITH")],
     "how often do geo probes hit login and checkout and what alert policy fires on consecutive misses",
     "synthetic monitoring geo probe pagerduty login checkout urgent policy"),
    # --- 21 ---
    ("Percentile reporting standardised on p50, p95, p99, and p999 across every service SLO; averaging used to hide the long-tail incidents that hurt the 0.1 percent of users the most.", "decision", "technical", False,
     [("p50", "concept"), ("p95", "concept"), ("p99", "concept"), ("p999", "concept"), ("SLO", "concept")],
     [("p999", "SLO", "APPLIES_TO")],
     "which percentile set did the SLO stack adopt and which prior metric hid the tail from us",
     "p50 p95 p99 p999 slo percentile long tail average hide incident"),
    # --- 22 ---
    ("Little's law sanity-checks every capacity model: concurrency equals arrival-rate times residence-time, and a spreadsheet column reconciles the load-test arrival rate with the observed worker pool size.", "reference", "technical", False,
     [("Little's law", "theory"), ("concurrency", "concept"), ("arrival-rate", "concept"), ("residence-time", "concept")],
     [],
     "which queueing theorem sanity-checks capacity models and which three quantities does it tie together",
     "little law concurrency arrival rate residence time capacity model"),
    # --- 23 ---
    ("The ramp-up profile for the Black-Friday rehearsal steps up RPS in ten equal blocks over thirty minutes; sudden step loads used to trip autoscalers that couldn't keep up on cold caches.", "reference", "technical", False,
     [("ramp-up profile", "pattern"), ("Black-Friday", "event"), ("RPS", "concept"), ("autoscaler", "service")],
     [],
     "which ramp-up shape does the Black-Friday rehearsal use and which failure mode did it retire",
     "ramp up rps black friday rehearsal autoscaler cold cache step load"),
    # --- 24 ---
    ("Think-time defaults to a Poisson-distributed delay with a mean of 8 seconds between requests; zero think-time runs survive only for backend-only micro-benchmarks where the client is irrelevant.", "decision", "technical", False,
     [("think-time", "concept"), ("Poisson", "algorithm"), ("micro-benchmark", "pattern")],
     [("think-time", "Poisson", "USES")],
     "which distribution shapes think-time in the main suite and when do we drop it to zero",
     "think time poisson distribution delay micro benchmark backend client"),
    # --- 25 ---
    ("Open workload models matter because a closed model caps concurrency at the VU count and hides queueing; k6's arrival-rate executors enforce the open model for user-facing APIs.", "reference", "technical", False,
     [("Open workload models", "concept"), ("closed model", "concept"), ("k6", "tool"), ("arrival-rate", "concept")],
     [("k6", "Open workload models", "IMPLEMENTS")],
     "why does an open workload model matter for user-facing APIs and which k6 executor enforces it",
     "open closed workload model k6 arrival rate vu concurrency queue"),
    # --- 26 ---
    ("Stress tests push past nominal capacity until error rate crosses 1 percent; the breakpoint value lives in the capacity plan alongside the soak and spike numbers for the same service.", "architecture", "technical", False,
     [("Stress tests", "method"), ("breakpoint", "concept"), ("capacity plan", "publication"), ("soak", "method"), ("spike", "method")],
     [],
     "which load-test type finds breakpoint capacity and where does the number live alongside soak and spike",
     "stress test breakpoint capacity plan soak spike error rate threshold"),
    # --- 27 ---
    ("Soak tests run the service at 70 percent of breakpoint for 12 hours to catch memory leaks and connection-pool creep that a one-hour run misses entirely on the inventory service.", "fact", "technical", False,
     [("Soak tests", "method"), ("breakpoint", "concept"), ("connection-pool", "pattern"), ("inventory service", "service")],
     [("Soak tests", "inventory service", "APPLIES_TO")],
     "which failure modes do 12-hour soak runs expose on the inventory service that shorter runs miss",
     "soak test breakpoint memory leak connection pool inventory service"),
    # --- 28 ---
    ("Spike tests triple the arrival rate within 30 seconds and hold for 2 minutes; the cart service failed this profile until we added request-coalescing on the Redis lookup path.", "problem", "technical", False,
     [("Spike tests", "method"), ("arrival rate", "concept"), ("cart service", "service"), ("Redis", "database"), ("request-coalescing", "pattern")],
     [("request-coalescing", "cart service", "FIXES")],
     "how is the spike profile shaped and which fix let the cart service survive it on the Redis path",
     "spike test arrival rate cart redis request coalescing triple 30"),
    # --- 29 ---
    ("Breakpoint analysis on the search API found the knee at 4200 RPS on 8 pods; beyond that, p99 latency climbs non-linearly because the Elasticsearch thread pool queues start backing up.", "milestone", "technical", False,
     [("Breakpoint analysis", "concept"), ("search API", "service"), ("p99", "concept"), ("Elasticsearch", "database"), ("thread pool", "pattern")],
     [],
     "at what RPS does the search API knee and which downstream subsystem drives the non-linear p99 climb",
     "breakpoint search api rps elasticsearch thread pool p99 knee 4200"),
    # --- 30 ---
    ("Grafana k6 Cloud hosts the distributed multi-region runs when local VUs cannot saturate the egress; results stream back into the on-prem Grafana via the same Loki-Mimir stack the platform already uses.", "architecture", "technical", False,
     [("Grafana k6 Cloud", "service"), ("Grafana", "tool"), ("Loki", "service"), ("Mimir", "service"), ("VUs", "concept")],
     [("Grafana k6 Cloud", "Grafana", "COMMUNICATES_WITH")],
     "when do we reach for Grafana k6 Cloud and how do results tie back to the on-prem observability stack",
     "grafana k6 cloud distributed multi region vu egress loki mimir stream"),
    # --- 31 ---
    ("JMeter survives for the SOAP-over-MQ contract test against the mainframe partner; no other tool on the shortlist speaks the JMS transport plus SOAP envelope permutation they expose.", "fact", "technical", False,
     [("JMeter", "tool"), ("SOAP", "protocol"), ("MQ", "service"), ("JMS", "protocol"), ("mainframe", "infrastructure")],
     [("JMeter", "JMS", "COMMUNICATES_WITH")],
     "which JMeter niche cannot be replaced and which partner integration drives it",
     "jmeter soap mq jms mainframe partner contract test envelope permutation"),
    # --- 32 ---
    ("Locust's distributed slave mode sits on an EKS spot fleet for scale-out scenarios; the master coordinates through Redis so spot-preemption of a worker doesn't corrupt the run's aggregate stats.", "architecture", "technical", False,
     [("Locust", "tool"), ("EKS", "platform"), ("Redis", "database"), ("spot", "concept")],
     [("Locust", "Redis", "USES"), ("Locust", "EKS", "DEPLOYED_ON")],
     "where does Locust's distributed slave mode run and how does it survive spot-preemption cleanly",
     "locust eks spot redis master slave distributed preempt aggregate"),
    # --- 33 ---
    ("Gatling's scenario DSL composes a chain of feeders, pauses, and exec blocks; the team prefers the Scala DSL over Java because the implicit conversions keep the test file under 50 lines per journey.", "preference", "technical", False,
     [("Gatling", "tool"), ("Scala", "language"), ("Java", "language"), ("DSL", "concept")],
     [("Scala", "Java", "PREFERS")],
     "why does the team prefer the Scala DSL over Java for Gatling scenarios",
     "gatling scala java dsl feeder pause exec scenario journey 50 lines"),
    # --- 34 ---
    ("Artillery Pro handles the WebSocket load for the live-ticker; the scenario plays 200 subscribe frames per second across 5 000 simulated clients and the duration matches the peak-hour window exactly.", "fact", "technical", False,
     [("Artillery Pro", "tool"), ("WebSocket", "protocol"), ("live-ticker", "service")],
     [("Artillery Pro", "WebSocket", "USES")],
     "which tool drives the live-ticker WebSocket load and what traffic shape does it produce",
     "artillery pro websocket live ticker subscribe frame 5000 client peak"),
    # --- 35 ---
    ("WebPageTest's Private Instance runs on a dedicated bare-metal host behind the corp VPN so the waterfall captures exercise internal CDN PoPs; the public cloud instance would otherwise bypass them.", "preference", "technical", False,
     [("WebPageTest", "tool"), ("VPN", "protocol"), ("CDN", "infrastructure"), ("bare-metal", "infrastructure")],
     [("WebPageTest", "bare-metal", "DEPLOYED_ON")],
     "why does WebPageTest run on a corp-VPN bare-metal host rather than the public cloud instance",
     "webpagetest private instance bare metal vpn cdn pop waterfall capture"),
    # --- 36 ---
    ("SpeedCurve LUX sits alongside the Calibre synthetic run for the same journeys; LUX owns RUM percentile trends while Calibre owns lab regression gates, and the split prevents double-noise on the dashboard.", "architecture", "technical", False,
     [("SpeedCurve LUX", "service"), ("Calibre", "tool"), ("RUM", "concept")],
     [("SpeedCurve LUX", "Calibre", "COMMUNICATES_WITH")],
     "how do SpeedCurve LUX and Calibre split responsibility between RUM trends and lab regression gates",
     "speedcurve lux calibre rum lab journey dashboard split noise"),
    # --- 37 ---
    ("Lighthouse CI assertion matchers broke on the 12.0 upgrade because the LCP category weight shifted; we pinned the action to v11 until the baseline drift could be re-rebaselined against real traffic.", "fact", "technical", False,
     [("Lighthouse CI", "tool"), ("LCP", "concept"), ("12.0", "date"), ("v11", "date")],
     [],
     "why was the Lighthouse CI action pinned to v11 after the 12.0 release and which score shifted",
     "lighthouse ci v12 v11 lcp weight pin assertion baseline drift"),
    # --- 38 ---
    ("Core Web Vitals for the PWA are measured on the subset of origins that pass the field-data eligibility; CrUX feeds a monthly comparison against RUM so we know the lab numbers match the real world.", "architecture", "technical", False,
     [("Core Web Vitals", "concept"), ("PWA", "technology"), ("CrUX", "service"), ("RUM", "concept")],
     [("CrUX", "RUM", "COMMUNICATES_WITH")],
     "how does the PWA reconcile field-data CrUX Core Web Vitals with internal RUM numbers each month",
     "core web vitals pwa crux rum field data origin eligibility monthly"),
    # --- 39 ---
    ("RUM sampling at 10 percent on the marketing site keeps ingestion cost under budget while still yielding sub-second confidence intervals on p75 LCP; the checkout funnel stays at 100 percent.", "decision", "technical", False,
     [("RUM", "concept"), ("marketing site", "project"), ("LCP", "concept"), ("checkout funnel", "pattern")],
     [("RUM", "checkout funnel", "APPLIES_TO")],
     "which RUM sampling split keeps marketing-site cost down while preserving checkout precision",
     "rum sampling 10 100 marketing checkout lcp p75 confidence interval"),
    # --- 40 ---
    ("p999 on the auth token endpoint exceeded 800 ms for three consecutive days; root cause was a JIT-cold GC pause on the first request after deploy, mitigated by a k6 warm-up burst at rollout.", "problem", "technical", False,
     [("p999", "concept"), ("auth token", "service"), ("JIT", "concept"), ("GC pause", "concept"), ("k6", "tool")],
     [("k6", "JIT", "FIXES")],
     "which root cause drove the p999 auth-token breach and how did k6 factor into the mitigation",
     "p999 auth token jit gc pause k6 warm up burst rollout deploy"),
    # --- 41 ---
    ("Little's law showed the new reservation service needed 180 concurrent workers to sustain 1 800 RPS at the 100 ms target residence time; the provisioning PR set min-replicas to 20 and cpu-per-replica to 9.", "milestone", "technical", False,
     [("Little's law", "theory"), ("reservation service", "service"), ("RPS", "concept")],
     [("Little's law", "reservation service", "APPLIES_TO")],
     "how did Little's law drive the reservation service's provisioning numbers and which PR landed them",
     "little law reservation service 180 1800 rps 100 ms replica cpu"),
    # --- 42 ---
    ("Spike scenarios that skip think-time over-report server capacity by roughly 30 percent compared with realistic user modelling; the finding informed the default-think-time rule across all new k6 scripts.", "milestone", "technical", False,
     [("think-time", "concept"), ("Spike scenarios", "method"), ("k6", "tool")],
     [],
     "how much does skipping think-time inflate apparent server capacity in spike tests",
     "think time spike k6 over report capacity 30 percent default rule"),
    # --- 43. noise ---
    ("A colleague brought in home-made kimchi pancakes for the Friday lunch and the break-room fridge smells like garlic until Monday morning.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Breakpoint testing on the image-resize worker found a cliff at 12 pods when the shared S3 throttled PUTs; migrating hot keys to a dedicated bucket lifted the cliff to 32 pods linearly.", "milestone", "technical", False,
     [("Breakpoint testing", "concept"), ("image-resize worker", "service"), ("S3", "service")],
     [("S3", "image-resize worker", "CAUSES")],
     "which shared dependency caused the image-resize breakpoint cliff and what fix lifted the ceiling",
     "breakpoint image resize s3 throttle put dedicated bucket cliff pod"),
    # --- 45 ---
    ("Adopted open-telemetry trace correlation in k6 runs: each VU stamps a traceparent header so backend spans link back to the load-test iteration id in Tempo without manual stitching.", "architecture", "technical", False,
     [("open-telemetry", "framework"), ("k6", "tool"), ("traceparent", "api"), ("Tempo", "service")],
     [("k6", "Tempo", "COMMUNICATES_WITH"), ("k6", "open-telemetry", "USES")],
     "how does k6 correlate its iterations with backend spans so stitching in Tempo is automatic",
     "open telemetry k6 traceparent tempo vu iteration span correlation"),
    # --- 46 ---
    ("Closed workload mode survives only for the partner sandbox smoke where the contract caps concurrency at 10 by design; every other run uses arrival-rate executors to mirror real user arrival.", "decision", "technical", False,
     [("Closed workload mode", "concept"), ("arrival-rate", "concept"), ("partner sandbox", "service")],
     [],
     "where does the closed workload model still apply and which executor family owns the rest",
     "closed workload arrival rate partner sandbox concurrency cap contract"),
    # --- 47 ---
    ("Core Web Vitals dashboard now highlights INP p75 per route; the previous per-site roll-up hid the slow search-suggest endpoint behind faster marketing routes and covered a real user pain point.", "decision", "technical", False,
     [("Core Web Vitals", "concept"), ("INP", "concept"), ("search-suggest", "service"), ("marketing", "project")],
     [],
     "which per-route metric did the Core Web Vitals dashboard add and which endpoint did it uncover",
     "core web vitals inp p75 per route search suggest marketing dashboard"),
    # --- 48 ---
    ("The capacity-plan doc cites Neil Gunther's USL alongside Little's law to bound the reservation service; the USL fit on the breakpoint data predicted the knee within 5 percent of the observed value.", "reference", "technical", False,
     [("USL", "theory"), ("Little's law", "theory"), ("Neil Gunther", "person"), ("capacity-plan", "publication"), ("reservation service", "service")],
     [("USL", "reservation service", "APPLIES_TO"), ("USL", "Neil Gunther", "AUTHORED_BY")],
     "which two analytical models bound the reservation service capacity and how close did USL predict the knee",
     "usl little law neil gunther reservation capacity knee breakpoint 5"),
    # --- 49 ---
    ("Ramp-down at the end of each run mirrors the ramp-up so connection pools drain cleanly; an abrupt stop used to leave TIME_WAIT sockets on the load generators that skewed the next test's baseline.", "reference", "technical", False,
     [("Ramp-down", "pattern"), ("ramp-up", "pattern"), ("connection pool", "pattern"), ("TIME_WAIT", "concept")],
     [("Ramp-down", "TIME_WAIT", "FIXES")],
     "why does the ramp-down mirror the ramp-up and which socket artefact did an abrupt stop create",
     "ramp down up connection pool time wait socket load generator baseline"),
    # --- 50 ---
    ("Shipped the k6 + Lighthouse CI + Calibre triad as the shared performance gate for all new services; the RFC-0042 doc codifies the percentile targets, budget files, and on-call escalation path together.", "milestone", "technical", False,
     [("k6", "tool"), ("Lighthouse CI", "tool"), ("Calibre", "tool"), ("RFC-0042", "publication")],
     [("RFC-0042", "k6", "APPLIES_TO"), ("RFC-0042", "Lighthouse CI", "APPLIES_TO"), ("RFC-0042", "Calibre", "APPLIES_TO")],
     "which three tools make up the shared performance gate for new services and where is it codified",
     "k6 lighthouse ci calibre shared performance gate rfc 0042 escalation"),
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
