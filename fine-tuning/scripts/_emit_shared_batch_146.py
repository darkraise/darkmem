"""One-off emitter for shared-base batch-146 — serverless platforms and edge functions.

Writes 50 rows to data/v2/shared/batch_146.tmp.jsonl with ids shared-07251..07300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_146.tmp.jsonl"
ID_OFFSET = 7250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Moved the image-thumbnail path from AWS Lambda on x86 to Graviton2 arm64; 250 ms p50 cold starts dropped to 180 ms and the per-invocation bill came down roughly twenty percent.", "decision", "technical", False,
     [("AWS Lambda", "service"), ("Graviton2", "infrastructure"), ("arm64", "platform"), ("x86", "platform")],
     [("AWS Lambda", "Graviton2", "DEPLOYED_ON"), ("Graviton2", "x86", "REPLACES")],
     "which architecture swap cut Lambda cold starts and costs on the thumbnail workload",
     "lambda graviton2 arm64 x86 cold start cost thumbnail"),
    # --- 2 ---
    ("Enabled provisioned concurrency on the checkout Lambda handler at 40 warm instances; cold-start tail on Black Friday went from 900 ms p99 to under 80 ms after the reservation kicked in.", "milestone", "technical", False,
     [("provisioned concurrency", "config"), ("Lambda", "service"), ("checkout", "project"), ("Black Friday", "event")],
     [("provisioned concurrency", "Lambda", "CONFIGURES")],
     "which Lambda concurrency feature flattened the Black Friday p99 cold-start tail on checkout",
     "lambda provisioned concurrency cold start p99 checkout black friday"),
    # --- 3 ---
    ("Lambda@Edge was wrong for the auth rewrite because origin-request triggers add 50 ms and run in a full Node runtime; CloudFront Functions fit the header-mutation use case better at sub-millisecond dispatch.", "decision", "technical", False,
     [("Lambda@Edge", "service"), ("CloudFront Functions", "service"), ("origin-request", "config"), ("Node", "framework")],
     [("CloudFront Functions", "Lambda@Edge", "REPLACES")],
     "why did the auth rewrite drop Lambda@Edge in favour of CloudFront Functions for header mutation",
     "cloudfront functions lambda edge header mutation node runtime"),
    # --- 4 ---
    ("Google Cloud Run sits behind an HTTPS load balancer with min-instances=2 on the API service; keeping two containers warm eats about nine dollars a month and kills the 1.2 s cold start entirely.", "decision", "technical", False,
     [("Google Cloud Run", "service"), ("HTTPS load balancer", "infrastructure"), ("min-instances", "config"), ("API service", "project")],
     [("API service", "Google Cloud Run", "DEPLOYED_ON")],
     "how is the API service kept warm on Cloud Run to kill a 1.2 second cold start",
     "cloud run min instances https load balancer warm cold start"),
    # --- 5 ---
    ("Cloud Functions 2nd gen is effectively Cloud Run under the hood; we consolidated 40 first-gen HTTP functions onto Cloud Run services and dropped a whole deployment stack from Terraform.", "milestone", "technical", False,
     [("Cloud Functions 2nd gen", "service"), ("Cloud Run", "service"), ("Terraform", "tool"), ("HTTP functions", "pattern")],
     [("Cloud Functions 2nd gen", "Cloud Run", "BUILDS_ON")],
     "which platform consolidation removed a deployment stack from the Terraform layout",
     "cloud functions 2nd gen cloud run terraform http consolidate"),
    # --- 6 ---
    ("Batch video transcodes run on Cloud Run Jobs with a 60-minute timeout and parallelism 20; the old Kubernetes CronJob setup was abandoned because autoscaling a sustained GPU pool cost three times more.", "decision", "technical", False,
     [("Cloud Run Jobs", "service"), ("Kubernetes CronJob", "service"), ("video transcodes", "project"), ("GPU pool", "infrastructure")],
     [("Cloud Run Jobs", "Kubernetes CronJob", "REPLACES")],
     "which batch runtime replaced the Kubernetes CronJob for the video transcode fleet",
     "cloud run jobs kubernetes cronjob video transcode gpu cost"),
    # --- 7 ---
    ("Azure Functions on the Flex Consumption plan gives us per-instance concurrency control; the classic Consumption plan capped at one HTTP request per worker and throttled under bursty Teams webhooks.", "decision", "technical", False,
     [("Azure Functions", "service"), ("Flex Consumption", "config"), ("Consumption plan", "config"), ("Teams", "platform")],
     [("Flex Consumption", "Consumption plan", "REPLACES")],
     "which Azure Functions plan unblocked bursty Teams webhook throughput",
     "azure functions flex consumption plan teams webhook burst"),
    # --- 8 ---
    ("Cloudflare Workers run on V8 isolates, so the shared process handles thousands of tenants with 5 ms cold starts; the 128 MB memory ceiling and 50 ms CPU limit shaped the URL-shortener rewrite.", "architecture", "technical", False,
     [("Cloudflare Workers", "service"), ("V8 isolates", "infrastructure"), ("URL-shortener", "project")],
     [("Cloudflare Workers", "V8 isolates", "USES")],
     "which runtime primitive gives Cloudflare Workers 5 ms cold starts and what limits shaped the rewrite",
     "cloudflare workers v8 isolate cold start memory cpu limit"),
    # --- 9 ---
    ("Durable Objects back the collaborative cursor state for the drawing app; a single object per room pins to one colo and serialises websocket fan-out without a separate Redis cluster.", "architecture", "technical", False,
     [("Durable Objects", "service"), ("drawing app", "project"), ("Redis", "database"), ("websocket", "protocol"), ("colo", "infrastructure")],
     [("drawing app", "Durable Objects", "USES"), ("Durable Objects", "Redis", "REPLACES")],
     "which Cloudflare primitive replaced a Redis cluster for collaborative cursor fan-out",
     "durable objects redis websocket cursor drawing colo pin"),
    # --- 10. noise ---
    ("The office dart-board was re-hung after someone knocked it off while wheeling a monitor through the side corridor.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Cloudflare KV is eventually consistent with a 60 second propagation window, so we keep rate-limit counters in Durable Objects instead; KV is reserved for feature-flag reads where stale is acceptable.", "architecture", "technical", False,
     [("Cloudflare KV", "database"), ("Durable Objects", "service"), ("rate-limit", "pattern"), ("feature-flag", "pattern")],
     [("rate-limit", "Durable Objects", "USES"), ("feature-flag", "Cloudflare KV", "USES")],
     "how did we split state between Cloudflare KV and Durable Objects based on consistency needs",
     "cloudflare kv durable objects rate limit feature flag consistency"),
    # --- 12 ---
    ("Cloudflare R2 hosts user-uploaded avatars with zero egress fees; we left S3 for the ML training bucket because Athena and SageMaker still expect an S3 endpoint and the transfer wasn't worth it.", "decision", "technical", False,
     [("Cloudflare R2", "database"), ("S3", "database"), ("Athena", "service"), ("SageMaker", "service"), ("avatars", "project")],
     [("Cloudflare R2", "S3", "REPLACES")],
     "why did avatars move to R2 while the ML training bucket stayed on S3",
     "r2 s3 avatar ml training athena sagemaker egress"),
    # --- 13 ---
    ("Vercel Edge Functions run on the same V8 isolate runtime as Workers but can only read from Vercel KV and Edge Config; we moved auth middleware there to cut 80 ms off the geo-redirect hop.", "decision", "technical", False,
     [("Vercel Edge Functions", "service"), ("Vercel KV", "database"), ("Edge Config", "config"), ("auth middleware", "pattern")],
     [("auth middleware", "Vercel Edge Functions", "DEPLOYED_ON")],
     "which Vercel runtime hosts auth middleware and what shaved 80 ms from geo-redirects",
     "vercel edge functions kv edge config auth middleware geo redirect"),
    # --- 14 ---
    ("Netlify Functions default to AWS Lambda us-east-1 regardless of site region; Netlify Edge Functions run on Deno Deploy, so the A/B test router was ported to the edge flavour to keep latency sane for EU users.", "fact", "technical", False,
     [("Netlify Functions", "service"), ("Netlify Edge Functions", "service"), ("Deno Deploy", "service"), ("A/B test router", "project")],
     [("Netlify Edge Functions", "Deno Deploy", "DEPLOYED_ON")],
     "why did the A/B test router move off Netlify Functions to the edge flavour for EU users",
     "netlify functions edge deno deploy ab test router eu latency"),
    # --- 15 ---
    ("Deno Deploy runs JavaScript on V8 isolates in 35 regions with a 10 ms CPU budget per request; the JWT-signing middleware we profiled fit inside 3 ms, which left plenty of headroom.", "fact", "technical", False,
     [("Deno Deploy", "service"), ("V8 isolates", "infrastructure"), ("JWT-signing", "pattern")],
     [("Deno Deploy", "V8 isolates", "USES")],
     "what CPU budget does Deno Deploy give per request and how did the JWT-signing middleware fit",
     "deno deploy v8 isolate region cpu budget jwt sign"),
    # --- 16 ---
    ("Bun Edge is still preview-only so we didn't migrate production, but the prototype booted a Hono app in 1.8 ms versus 4 ms on Workers; the faster start might matter once it ships GA.", "reference", "technical", False,
     [("Bun Edge", "service"), ("Hono", "framework"), ("Workers", "service")],
     [("Hono", "Bun Edge", "DEPLOYED_ON")],
     "which preview edge runtime beat Workers on Hono boot time and by how much",
     "bun edge hono workers preview boot start ga prototype"),
    # --- 17 ---
    ("Fastly Compute@Edge runs WebAssembly via Lucet, so every deploy ships a .wasm artifact instead of a container; cold starts are sub-millisecond because modules are AOT-compiled ahead of each POP warm.", "architecture", "technical", False,
     [("Fastly Compute@Edge", "service"), ("Lucet", "framework"), ("WebAssembly", "technology"), (".wasm", "file"), ("POP", "infrastructure")],
     [("Fastly Compute@Edge", "Lucet", "USES"), ("Fastly Compute@Edge", "WebAssembly", "USES")],
     "which WebAssembly runtime powers Fastly Compute@Edge and why are cold starts sub-millisecond",
     "fastly compute edge lucet wasm aot pop cold start module"),
    # --- 18 ---
    ("AWS Lambda runs each sandbox on Firecracker microVMs; a fresh microVM boots in roughly 125 ms, which sets the floor for any true cold start before your handler init even runs.", "reference", "technical", False,
     [("AWS Lambda", "service"), ("Firecracker", "technology"), ("microVM", "infrastructure")],
     [("AWS Lambda", "Firecracker", "USES")],
     "which microVM technology underpins Lambda sandboxes and what floor does it put on cold starts",
     "lambda firecracker microvm boot cold start floor sandbox"),
    # --- 19 ---
    ("Google Cloud Run uses gVisor for the first-generation execution environment and a Linux kernel sandbox for the second; switching to gen2 fixed a syscall compat bug in our native image and added NFS mount support.", "fact", "technical", False,
     [("Cloud Run", "service"), ("gVisor", "technology"), ("gen2", "config"), ("NFS", "protocol")],
     [("Cloud Run", "gVisor", "USES"), ("gen2", "gVisor", "REPLACES")],
     "which Cloud Run execution environment fixed the syscall compat bug and added NFS support",
     "cloud run gvisor gen2 syscall compat nfs mount native image"),
    # --- 20 ---
    ("Knative Serving backs the internal FaaS platform on our GKE cluster; scale-to-zero is on for 90% of services and the activator adds about 200 ms on a cold request when the pod needs to spin back up.", "reference", "technical", False,
     [("Knative Serving", "framework"), ("GKE", "service"), ("activator", "pattern"), ("FaaS", "concept")],
     [("FaaS", "Knative Serving", "USES"), ("Knative Serving", "GKE", "DEPLOYED_ON")],
     "which open-source serverless framework backs the internal FaaS on GKE and what is the activator cost",
     "knative serving gke faas activator scale zero cold pod"),
    # --- 21 ---
    ("OpenFaaS was evaluated for the on-prem edge boxes but we chose Knative because the queue-worker model in OpenFaaS lacked request-level autoscaling and our workload was bursty HTTP, not async.", "decision", "technical", False,
     [("OpenFaaS", "framework"), ("Knative", "framework"), ("queue-worker", "pattern")],
     [("Knative", "OpenFaaS", "PREFERS")],
     "why did on-prem edge pick Knative over OpenFaaS for a bursty HTTP workload",
     "openfaas knative queue worker autoscale bursty http edge"),
    # --- 22 ---
    ("Fission dropped out of the shortlist because the pool-manager approach warms Python pods per function and our 300-function tenancy would pin too much idle memory on the worker nodes.", "decision", "technical", False,
     [("Fission", "framework"), ("pool-manager", "pattern"), ("Python", "language")],
     [],
     "why did the serverless shortlist drop Fission given a 300-function tenancy",
     "fission pool manager python warm pod tenancy idle memory"),
    # --- 23 ---
    ("API Gateway HTTP API in front of Lambda costs 1 dollar per million requests versus 3.50 for REST API; the trade-off is no request validation, so we moved JSON schema checks into the handler.", "decision", "technical", False,
     [("API Gateway HTTP API", "service"), ("REST API", "service"), ("Lambda", "service"), ("JSON schema", "technology")],
     [("API Gateway HTTP API", "REST API", "REPLACES")],
     "which API Gateway flavour did Lambda pick for the cost win and what got moved into the handler",
     "api gateway http rest lambda json schema cost validation"),
    # --- 24 ---
    ("The SnapStart feature on AWS Lambda for Java cut JVM cold starts on the Spring Boot payment service from 6 seconds to 450 ms; the snapshot replay trick simply isn't available on Python or Go yet.", "milestone", "technical", False,
     [("SnapStart", "config"), ("AWS Lambda", "service"), ("Java", "language"), ("Spring Boot", "framework"), ("payment service", "project")],
     [("SnapStart", "AWS Lambda", "CONFIGURES")],
     "which Lambda feature cut Spring Boot cold starts from 6 seconds to 450 ms",
     "snapstart lambda java spring boot payment cold start snapshot"),
    # --- 25 ---
    ("Cloudflare Workers has a 1 MB compressed script-size limit, which hit us when the PDF-signing worker tried to bundle pdf-lib; the fix was streaming the PDF through R2 and keeping the worker under 400 KB.", "problem", "technical", False,
     [("Cloudflare Workers", "service"), ("pdf-lib", "library"), ("R2", "database"), ("PDF-signing", "project")],
     [("PDF-signing", "R2", "USES")],
     "which Workers size limit broke the PDF-signing bundle and how was the bundle slimmed",
     "cloudflare workers script size pdf lib r2 bundle limit"),
    # --- 26 ---
    ("Azure Functions Durable Functions implement the orchestration as an event-sourced replay; the orchestrator code must be deterministic, which surprised a dev who added DateTime.Now and saw the run diverge on replay.", "fact", "technical", False,
     [("Durable Functions", "framework"), ("Azure Functions", "service"), ("DateTime.Now", "api"), ("event-sourced", "pattern")],
     [("Durable Functions", "event-sourced", "USES")],
     "why does a Durable Functions orchestrator fail on DateTime.Now and what pattern is at play",
     "durable functions azure event source replay datetime determinism"),
    # --- 27 ---
    ("Cloud Run sidecars shipped GA in 2024 and we moved the Envoy proxy next to the main container to terminate mTLS; the old init-container hack that spliced certs into a tmpfs volume is retired.", "milestone", "technical", False,
     [("Cloud Run", "service"), ("sidecars", "pattern"), ("Envoy", "service"), ("mTLS", "protocol"), ("init-container", "pattern")],
     [("sidecars", "init-container", "REPLACES")],
     "which Cloud Run feature replaced the init-container cert hack for mTLS termination",
     "cloud run sidecar envoy mtls init container cert tmpfs"),
    # --- 28 ---
    ("Lambda function URLs let small services skip API Gateway entirely; the webhook receiver for Stripe events gets a direct HTTPS endpoint, IAM auth, and 6 MB payload cap with zero Gateway configuration.", "architecture", "technical", False,
     [("Lambda function URLs", "config"), ("API Gateway", "service"), ("Stripe", "organization"), ("IAM", "service")],
     [("Lambda function URLs", "API Gateway", "REPLACES")],
     "which Lambda feature lets the Stripe webhook skip API Gateway and what payload cap applies",
     "lambda function url api gateway stripe webhook iam payload"),
    # --- 29 ---
    ("Vercel's fluid compute billing charges per CPU-millisecond when the function isn't waiting on I/O; a chatty OpenAI-proxy route that streams tokens paid about 30% less after the switch from serverless billing.", "milestone", "technical", False,
     [("fluid compute", "config"), ("Vercel", "service"), ("OpenAI", "organization"), ("serverless billing", "config")],
     [("fluid compute", "serverless billing", "REPLACES")],
     "which Vercel billing mode cut cost for the OpenAI streaming proxy and why",
     "vercel fluid compute openai proxy stream billing cpu ms"),
    # --- 30 ---
    ("Deno Deploy added Fresh framework auto-routing on subhosted projects, so the content pages ship without a Node build step; TypeScript lands straight on the runtime and imports from JSR resolve at deploy time.", "fact", "technical", False,
     [("Deno Deploy", "service"), ("Fresh", "framework"), ("Node", "framework"), ("TypeScript", "language"), ("JSR", "service")],
     [("Fresh", "Deno Deploy", "DEPLOYED_ON")],
     "which Fresh feature lets content pages ship on Deno Deploy without a Node build step",
     "deno deploy fresh typescript jsr node build subhost"),
    # --- 31 ---
    ("Workers AI exposes Llama-3-8B as a bindings-based model call from a Worker; for our moderation path it beats OpenAI latency because the inference runs in the same colo as the request and skips a round trip.", "decision", "technical", False,
     [("Workers AI", "service"), ("Llama-3-8B", "technology"), ("Worker", "service"), ("OpenAI", "organization"), ("moderation", "project")],
     [("moderation", "Workers AI", "USES"), ("Workers AI", "OpenAI", "REPLACES")],
     "which in-colo inference service replaced OpenAI for the moderation path and why",
     "workers ai llama 3 openai colo moderation bindings latency"),
    # --- 32 ---
    ("AWS Lambda extensions run in the same execution environment as the function and can hook into INVOKE and SHUTDOWN phases; the Datadog extension buffers logs and flushes on SHUTDOWN instead of per-line.", "architecture", "technical", False,
     [("AWS Lambda extensions", "config"), ("Datadog", "tool"), ("INVOKE", "pattern"), ("SHUTDOWN", "pattern")],
     [("Datadog", "AWS Lambda extensions", "USES")],
     "how does the Datadog Lambda extension avoid per-line log flushes during INVOKE",
     "lambda extension datadog invoke shutdown buffer log flush"),
    # --- 33 ---
    ("The cold-start P99 for Python 3.12 on Lambda measured 420 ms on a 512 MB function and 260 ms at 3008 MB; we pin payment services at 2048 MB because CPU scales linearly with memory and the extra RAM is fine.", "fact", "technical", False,
     [("Python 3.12", "language"), ("Lambda", "service"), ("payment services", "project")],
     [("payment services", "Lambda", "DEPLOYED_ON")],
     "how do Python 3.12 Lambda cold starts scale with memory and what RAM setting did payments pick",
     "python lambda cold start p99 memory cpu ram payment"),
    # --- 34 ---
    ("WebAssembly System Interface preview 2 is what Compute@Edge targets, which means our Rust crates need wasi-0.2 shims; the migration off wasi-0.1 broke a half-dozen crates that hadn't been republished yet.", "problem", "technical", False,
     [("WebAssembly System Interface", "technology"), ("Compute@Edge", "service"), ("Rust", "language"), ("wasi-0.2", "technology"), ("wasi-0.1", "technology")],
     [("Compute@Edge", "WebAssembly System Interface", "USES"), ("wasi-0.2", "wasi-0.1", "REPLACES")],
     "which WASI version does Compute@Edge target now and which Rust crates broke on the migration",
     "wasi preview 2 compute edge rust shim wasi 0.1 crate"),
    # --- 35 ---
    ("Cloudflare Queues consumed by a Worker replaced SQS for the webhook dispatch; a queue-per-tenant and batch size of 10 gives end-to-end delivery under 900 ms without managing a consumer fleet.", "decision", "technical", False,
     [("Cloudflare Queues", "service"), ("Worker", "service"), ("SQS", "service"), ("webhook dispatch", "project")],
     [("webhook dispatch", "Cloudflare Queues", "USES"), ("Cloudflare Queues", "SQS", "REPLACES")],
     "which queue service replaced SQS for webhook dispatch and what batch size did we land on",
     "cloudflare queues sqs worker webhook dispatch batch tenant"),
    # --- 36 ---
    ("EventBridge Pipes glues DynamoDB Streams into Lambda with filtering and transformation inline; the old Kinesis-plus-Lambda fan-out is gone and we saved a shard-management headache during ramp events.", "architecture", "technical", False,
     [("EventBridge Pipes", "service"), ("DynamoDB Streams", "service"), ("Lambda", "service"), ("Kinesis", "service")],
     [("EventBridge Pipes", "Kinesis", "REPLACES")],
     "which AWS glue service replaced Kinesis between DynamoDB Streams and Lambda",
     "eventbridge pipes dynamodb streams lambda kinesis fan out shard"),
    # --- 37 ---
    ("Cloud Run CPU-always-allocated mode lets background goroutines keep running between requests; with CPU-throttled mode a gRPC server-streaming RPC starves after the response and misses heartbeats.", "fact", "technical", False,
     [("Cloud Run", "service"), ("CPU-always-allocated", "config"), ("CPU-throttled", "config"), ("gRPC", "protocol")],
     [],
     "which Cloud Run CPU mode keeps background goroutines alive for gRPC server streaming",
     "cloud run cpu always allocated throttle grpc streaming heartbeat"),
    # --- 38 ---
    ("Azure Static Web Apps pairs the site with linked Functions for the API; the managed API trusts the front-end's x-ms-client-principal header, which is injected at the edge after Azure AD B2C validates the token.", "architecture", "technical", False,
     [("Azure Static Web Apps", "service"), ("Functions", "service"), ("Azure AD B2C", "service"), ("x-ms-client-principal", "api")],
     [("Azure Static Web Apps", "Functions", "USES")],
     "how does Azure Static Web Apps pass an authenticated identity from Azure AD B2C into the linked API",
     "azure static web apps functions ad b2c client principal"),
    # --- 39 ---
    ("Netlify on-demand builders generate and cache long-tail pages the first time a user hits them; it dropped a 45-minute full-site build to two minutes because only the hot pages get pre-rendered now.", "milestone", "technical", False,
     [("Netlify", "service"), ("on-demand builders", "pattern"), ("long-tail pages", "pattern")],
     [],
     "which Netlify feature cut the 45-minute full-site build and how does it handle long-tail pages",
     "netlify on demand builder long tail build cache prerender"),
    # --- 40 ---
    ("Lambda SnapStart for .NET hit GA in late 2024 and it now pre-warms the CLR before checkpointing; our Rider-based internal CRUD service loads in 200 ms instead of the 4.5 s managed framework boot.", "milestone", "technical", False,
     [("SnapStart", "config"), ("Lambda", "service"), (".NET", "framework"), ("CLR", "technology"), ("CRUD service", "project")],
     [("CRUD service", "Lambda", "DEPLOYED_ON"), ("SnapStart", "CLR", "CONFIGURES")],
     "which Lambda feature pre-warms the CLR and what cold-start drop did the CRUD service see",
     "lambda snapstart dotnet clr crud cold start ga 2024"),
    # --- 41 ---
    ("Cloudflare Hyperdrive pools connections to a regional Postgres so a Worker can keep pg-level connections below 50 even under a burst of 10k concurrent invocations that would otherwise exhaust the database.", "architecture", "technical", False,
     [("Cloudflare Hyperdrive", "service"), ("Postgres", "database"), ("Worker", "service"), ("pg", "tool")],
     [("Worker", "Cloudflare Hyperdrive", "USES"), ("Cloudflare Hyperdrive", "Postgres", "COMMUNICATES_WITH")],
     "which Cloudflare feature keeps Postgres connections bounded when 10k Workers burst a query",
     "cloudflare hyperdrive postgres worker connection pool burst"),
    # --- 42 ---
    ("Vercel Edge Middleware runs before cache lookup, so a personalisation header check adds latency to every request; we moved it to an after-cache Node function and the cache hit rate jumped from 60% to 91%.", "problem", "technical", False,
     [("Vercel Edge Middleware", "service"), ("Node function", "service"), ("personalisation", "pattern")],
     [("Node function", "Vercel Edge Middleware", "REPLACES")],
     "why did personalisation move off Vercel Edge Middleware and what happened to the cache hit rate",
     "vercel edge middleware cache personalisation hit rate node"),
    # --- 43. noise ---
    ("The kitchen coffee grinder squeaks slightly when the beans get low and someone finally labelled the hopper with a sticky note.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Fastly Compute@Edge instance lifetime is a single request, so there is no warm-pool idle state to exploit; shared caches have to go through KV Store or Fanout, which the chat fan-out project picked for presence.", "reference", "technical", False,
     [("Compute@Edge", "service"), ("KV Store", "database"), ("Fanout", "service"), ("chat fan-out", "project")],
     [("chat fan-out", "Fanout", "USES")],
     "how does Compute@Edge handle shared state when each instance serves a single request",
     "compute edge instance lifetime kv store fanout chat presence"),
    # --- 45 ---
    ("Lambda init-phase code runs outside the billed duration for the first invocation, so pulling secrets from Parameter Store at module scope is effectively free; per-invocation fetches add 30 ms each.", "preference", "technical", False,
     [("Lambda", "service"), ("Parameter Store", "service"), ("init-phase", "pattern")],
     [("Lambda", "Parameter Store", "COMMUNICATES_WITH")],
     "why should Lambda fetch Parameter Store secrets at module scope rather than per invocation",
     "lambda init phase parameter store secret module scope billed"),
    # --- 46 ---
    ("We prefer writing new edge code in TypeScript with workerd for local dev; Miniflare got deprecated in favour of the same Cloudflare runtime binary that production uses, which kills the bindings-mismatch class of bugs.", "preference", "technical", False,
     [("TypeScript", "language"), ("workerd", "tool"), ("Miniflare", "tool"), ("Cloudflare", "organization")],
     [("workerd", "Miniflare", "REPLACES")],
     "which local dev tool replaced Miniflare for Cloudflare Workers and why do we prefer it",
     "typescript workerd miniflare cloudflare local dev binding"),
    # --- 47 ---
    ("Preference: pin Lambda runtimes to the specific version like nodejs20.x rather than using nodejs-latest; AWS deprecated 16.x on a 30-day window in 2024 and the implicit upgrades broke native addons silently.", "preference", "technical", False,
     [("Lambda", "service"), ("nodejs20.x", "technology"), ("nodejs-latest", "config"), ("AWS", "organization")],
     [],
     "why pin Lambda to nodejs20.x rather than nodejs-latest and what 2024 incident illustrated the risk",
     "lambda nodejs runtime pin version latest deprecate native addon"),
    # --- 48 ---
    ("Team preference: default new workloads to Cloud Run rather than GKE unless we need CronJob, DaemonSet, or StatefulSet semantics; the Cloud Run + Cloud Scheduler combo covers about 80% of what we ship.", "preference", "technical", False,
     [("Cloud Run", "service"), ("GKE", "service"), ("Cloud Scheduler", "service"), ("CronJob", "pattern"), ("DaemonSet", "pattern"), ("StatefulSet", "pattern")],
     [("Cloud Run", "GKE", "PREFERS")],
     "which GCP default did the team pick between Cloud Run and GKE and what workloads still merit GKE",
     "cloud run gke cron daemonset statefulset preference default"),
    # --- 49 ---
    ("OpenFaaS on K3s still runs the air-gapped lab in Building 7; the watchdog shim wraps arbitrary binaries as HTTP functions and the pipeline produces Docker images signed with Cosign before the cluster pulls them.", "reference", "technical", False,
     [("OpenFaaS", "framework"), ("K3s", "service"), ("watchdog", "pattern"), ("Docker", "technology"), ("Cosign", "tool"), ("Building 7", "place")],
     [("OpenFaaS", "K3s", "DEPLOYED_ON"), ("Docker", "Cosign", "USES")],
     "which serverless framework runs in the air-gapped Building 7 lab and how are its images signed",
     "openfaas k3s watchdog docker cosign air gapped building"),
    # --- 50 ---
    ("Knative scale-to-zero with the Horizontal Pod Autoscaler class fights the Knative Pod Autoscaler on the same deployment; documentation recommends picking one, and we went KPA because panic-mode scaling handled traffic spikes faster.", "reference", "technical", False,
     [("Knative", "framework"), ("Horizontal Pod Autoscaler", "pattern"), ("Knative Pod Autoscaler", "pattern"), ("panic-mode", "pattern")],
     [("Knative Pod Autoscaler", "Horizontal Pod Autoscaler", "PREFERS")],
     "why did the Knative deployments pick KPA over HPA for scale-to-zero behaviour",
     "knative kpa hpa pod autoscaler scale zero panic mode spike"),
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
