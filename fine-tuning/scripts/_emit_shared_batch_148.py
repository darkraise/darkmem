"""One-off emitter for shared-base batch-148 — API gateways and service mesh (Kong, Envoy, Istio, Linkerd, Traefik, HAProxy, NPM, Consul Connect, Cilium, Gloo, Ambassador, Tyk, KrakenD, Emissary; mTLS, circuit breakers, retries, rate limiting, canary, sidecar, ambient, gRPC, WAF, eBPF).

Writes 50 rows to data/v2/shared/batch_148.tmp.jsonl with ids shared-07351..07400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_148.tmp.jsonl"
ID_OFFSET = 7350

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Replaced Nginx Proxy Manager at the edge with Traefik v3 so dynamic Docker labels drive the router table; manual NPM GUI edits were lagging behind the Compose stack on every deploy.", "decision", "technical", False,
     [("Nginx Proxy Manager", "tool"), ("Traefik", "tool"), ("Docker", "platform"), ("Compose", "tool")],
     [("Traefik", "Nginx Proxy Manager", "REPLACES"), ("Traefik", "Docker", "USES")],
     "which edge router took over from Nginx Proxy Manager and what drove the switch",
     "traefik npm nginx proxy manager docker label compose edge router"),
    # --- 2 ---
    ("Kong Gateway now fronts the internal REST tier with a declarative kong.yml checked into git; plugin ordering for key-auth before rate-limiting had to be pinned to avoid leaking quota to anonymous callers.", "architecture", "technical", False,
     [("Kong Gateway", "tool"), ("kong.yml", "file"), ("key-auth", "pattern"), ("rate-limiting", "pattern")],
     [("Kong Gateway", "key-auth", "USES"), ("key-auth", "rate-limiting", "RELATED_TO")],
     "how is Kong configured declaratively and why does plugin ordering matter for quota safety",
     "kong declarative kong yml plugin key auth rate limit ordering quota"),
    # --- 3 ---
    ("Adopted Istio ambient mode on the staging cluster; removing the per-pod Envoy sidecar cut memory by roughly forty percent and ztunnel now handles L4 mTLS at the node level.", "milestone", "technical", False,
     [("Istio", "tool"), ("Envoy", "tool"), ("ztunnel", "service"), ("mTLS", "protocol")],
     [("Istio", "Envoy", "REPLACES"), ("ztunnel", "mTLS", "IMPLEMENTS")],
     "which Istio data-plane change cut sidecar memory in staging and what handles L4 encryption now",
     "istio ambient ztunnel envoy sidecar memory mtls node l4"),
    # --- 4 ---
    ("Linkerd beat Istio on the internal bake-off for the payment mesh; the Rust-based linkerd2-proxy sidecar has a tighter tail latency profile and no Envoy CVE churn to track each quarter.", "decision", "technical", False,
     [("Linkerd", "tool"), ("Istio", "tool"), ("linkerd2-proxy", "service"), ("Envoy", "tool")],
     [("Linkerd", "Istio", "PREFERS"), ("linkerd2-proxy", "Envoy", "REPLACES")],
     "which service mesh won the payment-tier bake-off and which sidecar property sealed it",
     "linkerd istio rust proxy payment mesh tail latency cve bake off"),
    # --- 5 ---
    ("Consul Connect wires mTLS between the legacy VM workloads and the Nomad jobs; Istio was ruled out because half the fleet is still on bare metal without a Kubernetes CNI to hook into.", "decision", "technical", False,
     [("Consul Connect", "tool"), ("Nomad", "tool"), ("Istio", "tool"), ("Kubernetes", "platform"), ("mTLS", "protocol")],
     [("Consul Connect", "mTLS", "IMPLEMENTS"), ("Consul Connect", "Nomad", "USES")],
     "which mesh fit the mixed VM and Nomad fleet and why Istio was ruled out",
     "consul connect nomad vm bare metal istio kubernetes cni mtls"),
    # --- 6 ---
    ("Cilium Service Mesh replaced Istio on the observability cluster; eBPF handles L7 routing without a sidecar, and the Hubble UI gave the SRE team a richer flow view than Kiali did.", "decision", "technical", False,
     [("Cilium Service Mesh", "tool"), ("Istio", "tool"), ("eBPF", "technology"), ("Hubble", "tool"), ("Kiali", "tool")],
     [("Cilium Service Mesh", "Istio", "REPLACES"), ("Cilium Service Mesh", "eBPF", "USES")],
     "which eBPF-based mesh took over from Istio on the observability cluster and which UI replaced Kiali",
     "cilium ebpf istio service mesh hubble kiali sidecarless observability"),
    # --- 7 ---
    ("Envoy handles east-west traffic in the mesh and the control plane is plain xDS over gRPC; we skipped Istio's full install and run a custom operator that only ships listeners and clusters.", "fact", "technical", False,
     [("Envoy", "tool"), ("xDS", "protocol"), ("gRPC", "protocol"), ("Istio", "tool")],
     [("Envoy", "xDS", "USES"), ("xDS", "gRPC", "USES")],
     "how is Envoy configured in the custom mesh and what control-plane protocol does the operator speak",
     "envoy xds grpc control plane custom operator listener cluster"),
    # --- 8 ---
    ("The HAProxy front door keeps the legacy TCP passthrough for the MySQL replica pool; Traefik handles the HTTP tier but HAProxy's PROXY v2 support was cleaner for the database VIPs.", "fact", "technical", False,
     [("HAProxy", "tool"), ("Traefik", "tool"), ("MySQL", "database"), ("PROXY v2", "protocol")],
     [("HAProxy", "PROXY v2", "USES"), ("HAProxy", "MySQL", "APPLIES_TO")],
     "which proxy handles TCP passthrough for the MySQL pool and which protocol kept it preferable",
     "haproxy traefik mysql tcp passthrough proxy v2 replica vip database"),
    # --- 9 ---
    ("Ambassador Edge Stack fronts the public GraphQL gateway; the Mapping CRD model maps cleanly to the platform team's GitOps flow and removed the need for a separate WAF box in front.", "decision", "technical", False,
     [("Ambassador Edge Stack", "tool"), ("GraphQL", "technology"), ("Mapping", "api"), ("GitOps", "pattern"), ("WAF", "pattern")],
     [("Ambassador Edge Stack", "GraphQL", "APPLIES_TO"), ("Ambassador Edge Stack", "WAF", "REPLACES")],
     "which edge stack fronts the public GraphQL tier and what separate appliance did it retire",
     "ambassador edge stack graphql mapping crd gitops waf public"),
    # --- 10. noise ---
    ("Someone left a rubber duck on top of the rack-room KVM and nobody has been willing to claim it for three weeks.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Tyk Gateway handles the partner API tier with per-consumer quotas backed by Redis; Kong was the earlier pick but the Tyk dashboard's analytics view matched what the partner-success team already reported on.", "decision", "technical", False,
     [("Tyk Gateway", "tool"), ("Kong", "tool"), ("Redis", "database")],
     [("Tyk Gateway", "Kong", "REPLACES"), ("Tyk Gateway", "Redis", "USES")],
     "which gateway replaced Kong on the partner tier and what backing store holds per-consumer quotas",
     "tyk gateway kong partner api redis quota consumer analytics dashboard"),
    # --- 12 ---
    ("KrakenD aggregates the mobile BFF endpoints into a single response; the old Node gateway was hand-rolling fan-out and timeouts were inconsistent across squads owning the upstreams.", "decision", "technical", False,
     [("KrakenD", "tool"), ("BFF", "pattern"), ("Node", "platform")],
     [("KrakenD", "Node", "REPLACES"), ("KrakenD", "BFF", "IMPLEMENTS")],
     "which aggregation gateway replaced the hand-rolled Node BFF for mobile fan-out",
     "krakend bff mobile aggregation fan out node timeout squad upstream"),
    # --- 13 ---
    ("Emissary-ingress fronts the internal-tools cluster on EKS; being the open-source split of Ambassador, it kept the Mapping CRD workflow but without the enterprise licence gate on rate-limit policies.", "milestone", "technical", False,
     [("Emissary-ingress", "tool"), ("Ambassador", "tool"), ("EKS", "platform"), ("Mapping", "api")],
     [("Emissary-ingress", "Ambassador", "BUILDS_ON"), ("Emissary-ingress", "EKS", "DEPLOYED_ON")],
     "which ingress did we pick for the internal-tools EKS cluster and how does it relate to Ambassador",
     "emissary ingress ambassador eks mapping crd rate limit enterprise license"),
    # --- 14 ---
    ("Gloo Edge replaces the hand-rolled Envoy config on the checkout path; the function-level routing lets us shift canary traffic by weight without a Helm redeploy per shift.", "architecture", "technical", False,
     [("Gloo Edge", "tool"), ("Envoy", "tool"), ("Helm", "tool"), ("canary", "pattern")],
     [("Gloo Edge", "Envoy", "USES"), ("Gloo Edge", "canary", "IMPLEMENTS")],
     "which edge controller replaced raw Envoy on checkout and what canary shift workflow did it unlock",
     "gloo edge envoy checkout canary helm redeploy function routing weight"),
    # --- 15 ---
    ("mTLS between every service in the mesh uses SPIFFE identities with SPIRE issuing SVIDs; the old static client-cert PKI got retired after a rotation window was missed and caused a four-hour outage.", "milestone", "technical", False,
     [("SPIFFE", "protocol"), ("SPIRE", "tool"), ("SVID", "concept"), ("PKI", "pattern"), ("mTLS", "protocol")],
     [("SPIRE", "SVID", "PRODUCES"), ("SPIFFE", "PKI", "REPLACES")],
     "which workload-identity stack replaced the static client-cert PKI after the rotation outage",
     "spiffe spire svid pki mtls rotation outage identity mesh client cert"),
    # --- 16 ---
    ("Circuit breaker on the recommendation client is an Envoy outlier-detection rule: five consecutive 5xx in a thirty-second window ejects the endpoint for one minute and halves the ejection multiplier on recovery.", "fact", "technical", False,
     [("Envoy", "tool"), ("outlier-detection", "pattern"), ("Circuit breaker", "pattern"), ("recommendation", "service")],
     [("Envoy", "outlier-detection", "IMPLEMENTS")],
     "how is the recommendation circuit breaker configured with Envoy outlier detection thresholds",
     "envoy outlier detection circuit breaker recommendation 5xx eject recovery"),
    # --- 17 ---
    ("Retry budget in Linkerd capped at twenty percent of the original request rate; unbounded retries on a flapping downstream amplified load by 4x during the March incident and masked the real fault.", "problem", "technical", False,
     [("Linkerd", "tool"), ("Retry budget", "pattern"), ("March incident", "event")],
     [("Linkerd", "Retry budget", "CONFIGURES")],
     "how did we cap retry amplification in Linkerd after the March incident exposed a flapping downstream",
     "linkerd retry budget cap percent amplify flap march incident load"),
    # --- 18 ---
    ("Timeouts are set per-route in Envoy with a global upper bound of 30s at the edge and 5s between services; the old global 60s default hid slow upstreams in the checkout path behind patient gateways.", "fact", "technical", False,
     [("Envoy", "tool"), ("Timeouts", "concept"), ("checkout", "service")],
     [("Envoy", "Timeouts", "CONFIGURES")],
     "how are per-route timeouts configured in Envoy after the old global default hid slow checkout upstreams",
     "envoy timeout per route edge internal checkout slow upstream default"),
    # --- 19 ---
    ("Kong rate-limiting plugin uses a sliding-window counter in Redis instead of the local in-memory policy; the in-memory path drifted across nodes and let a burst through during a traffic spike.", "problem", "technical", False,
     [("Kong", "tool"), ("rate-limiting", "pattern"), ("Redis", "database"), ("sliding-window", "algorithm")],
     [("Kong", "Redis", "USES"), ("sliding-window", "rate-limiting", "IMPLEMENTS")],
     "which rate-limit backing store replaced Kong's local policy after a burst leaked through",
     "kong rate limit redis sliding window local memory burst drift spike"),
    # --- 20 ---
    ("Canary deploy for the pricing service uses Argo Rollouts driving Istio VirtualService weights; the analysis template reads Prometheus success rate and auto-aborts on a two-percent regression.", "architecture", "technical", False,
     [("Argo Rollouts", "tool"), ("Istio", "tool"), ("VirtualService", "api"), ("Prometheus", "tool"), ("pricing", "service")],
     [("Argo Rollouts", "Istio", "USES"), ("Argo Rollouts", "Prometheus", "USES")],
     "how is the pricing-service canary wired between Argo Rollouts, Istio weights, and Prometheus analysis",
     "argo rollouts istio virtualservice prometheus canary pricing abort weight"),
    # --- 21 ---
    ("Traffic splitting on the search rollout landed as a 90/10 weight at the Envoy route level; sticky cookies keep a session pinned to the new version so back-button reloads don't bounce A/B tests.", "architecture", "technical", False,
     [("Envoy", "tool"), ("search", "service"), ("sticky cookie", "pattern")],
     [("Envoy", "sticky cookie", "USES")],
     "how does the search rollout split traffic and keep user sessions pinned across reloads",
     "envoy traffic split search 90 10 weight sticky cookie session pin"),
    # --- 22 ---
    ("Sidecar proxy injection is gated by a namespace label to keep the batch-job namespace out of the mesh; an injected sidecar blocked Job completion because the app exited before Envoy drained.", "preference", "technical", False,
     [("sidecar", "pattern"), ("Job", "api"), ("Envoy", "tool"), ("namespace label", "config")],
     [("namespace label", "sidecar", "CONFIGURES")],
     "why are batch-job namespaces excluded from sidecar injection and what failure mode drove the exclusion",
     "sidecar injection namespace label batch job envoy drain exit gate"),
    # --- 23 ---
    ("Ambient mode on the reporting cluster uses the Istio waypoint proxy only for L7 policies that need it; everything below is L4 ztunnel, which keeps the per-workload cost near zero.", "architecture", "technical", False,
     [("Ambient mode", "pattern"), ("Istio", "tool"), ("waypoint proxy", "service"), ("ztunnel", "service")],
     [("Istio", "Ambient mode", "IMPLEMENTS"), ("waypoint proxy", "ztunnel", "EXTENDS")],
     "how does Istio ambient split L7 waypoint proxies from L4 ztunnel in the reporting cluster",
     "istio ambient waypoint ztunnel l4 l7 reporting cluster per workload"),
    # --- 24 ---
    ("gRPC routing for the recommendations service uses Envoy's HTTP/2 filter chain with per-method timeouts; the earlier L4 balancer pinned connections to a single backend and starved new pods on scale-up.", "decision", "technical", False,
     [("gRPC", "protocol"), ("Envoy", "tool"), ("HTTP/2", "protocol"), ("recommendations", "service")],
     [("Envoy", "HTTP/2", "USES"), ("Envoy", "gRPC", "APPLIES_TO")],
     "which gRPC routing upgrade fixed the connection-pinning starvation on recommendation scale-ups",
     "grpc envoy http2 recommendations per method timeout pin starve scale"),
    # --- 25 ---
    ("HTTP/2 enabled end-to-end from Traefik through to the FastAPI services behind it; the earlier HTTP/1.1 hop at the ingress throttled multiplexing and streaming endpoints felt choppy under load.", "fact", "technical", False,
     [("HTTP/2", "protocol"), ("Traefik", "tool"), ("FastAPI", "framework"), ("HTTP/1.1", "protocol")],
     [("Traefik", "HTTP/2", "USES"), ("HTTP/2", "HTTP/1.1", "REPLACES")],
     "why was end-to-end HTTP/2 enabled through Traefik into FastAPI instead of dropping to HTTP/1.1",
     "http2 traefik fastapi http1 multiplex stream choppy ingress hop"),
    # --- 26 ---
    ("WAF rules on the public edge use the Coraza engine embedded in Envoy; the OWASP CRS v4 ruleset shipped with only two false positives on the login path after tuning exception lists.", "milestone", "technical", False,
     [("WAF", "pattern"), ("Coraza", "tool"), ("Envoy", "tool"), ("OWASP CRS", "publication"), ("login", "service")],
     [("Coraza", "Envoy", "DEPLOYED_ON"), ("Coraza", "OWASP CRS", "USES")],
     "which WAF engine runs in Envoy and which ruleset did it ship with for the public login path",
     "coraza envoy waf owasp crs login false positive ruleset edge"),
    # --- 27 ---
    ("Cilium's eBPF L7 policies replaced the old NetworkPolicy CIDR rules; pod identity is the subject now, and IP churn from auto-scaling no longer invalidates every rule on the fleet.", "architecture", "technical", False,
     [("Cilium", "tool"), ("eBPF", "technology"), ("NetworkPolicy", "api"), ("CIDR", "concept")],
     [("Cilium", "NetworkPolicy", "REPLACES"), ("Cilium", "eBPF", "USES")],
     "how did eBPF pod-identity policies replace CIDR-based NetworkPolicy under autoscaling churn",
     "cilium ebpf networkpolicy cidr pod identity autoscale churn l7 rule"),
    # --- 28 ---
    ("Istio authorization policies use SPIFFE IDs rather than service accounts; this matched the cross-cluster federation plan and avoided re-binding policies after a namespace rename on the billing cluster.", "decision", "technical", False,
     [("Istio", "tool"), ("SPIFFE", "protocol"), ("authorization policies", "api"), ("billing", "service")],
     [("Istio", "SPIFFE", "USES"), ("authorization policies", "SPIFFE", "USES")],
     "which identity format anchors Istio authorization policies and what cross-cluster benefit drove the pick",
     "istio authorization spiffe service account billing federation rename"),
    # --- 29 ---
    ("Linkerd's service profile CRD drives per-route retry and timeout policy for the inventory client; hand-rolled Envoy configs were out of date whenever the REST contract shifted.", "decision", "technical", False,
     [("Linkerd", "tool"), ("service profile", "api"), ("inventory", "service"), ("Envoy", "tool")],
     [("Linkerd", "service profile", "USES"), ("service profile", "Envoy", "REPLACES")],
     "which Linkerd CRD took over retry and timeout policy from hand-rolled Envoy configs",
     "linkerd service profile inventory retry timeout envoy route config"),
    # --- 30 ---
    ("Nginx Proxy Manager still fronts the homelab services because its UI is friendlier for the housemate-admin use case; production-grade Traefik sits on the other cluster where GitOps owns the routes.", "preference", "technical", False,
     [("Nginx Proxy Manager", "tool"), ("Traefik", "tool"), ("homelab", "project"), ("GitOps", "pattern")],
     [("Nginx Proxy Manager", "homelab", "DEPLOYED_ON")],
     "why does the homelab keep Nginx Proxy Manager while production runs Traefik under GitOps",
     "npm nginx proxy manager homelab traefik gitops housemate admin ui"),
    # --- 31 ---
    ("Tyk's GraphQL middleware enforces query depth and complexity limits; a partner sent a nested introspection that previously spiked the upstream to 100 percent CPU for thirty seconds on a cold cache.", "fact", "technical", False,
     [("Tyk", "tool"), ("GraphQL", "technology"), ("introspection", "pattern")],
     [("Tyk", "GraphQL", "APPLIES_TO")],
     "which Tyk middleware stopped partner GraphQL introspections from spiking upstream CPU",
     "tyk graphql depth complexity introspection partner cpu cold cache"),
    # --- 32 ---
    ("Ambassador's RateLimitService talks to an external Go service backed by Redis cells sharded by consumer; the in-process limiter couldn't hold global quota across the four-replica deployment.", "architecture", "technical", False,
     [("Ambassador", "tool"), ("RateLimitService", "api"), ("Redis", "database"), ("Go", "language")],
     [("Ambassador", "RateLimitService", "USES"), ("RateLimitService", "Redis", "DEPENDS_ON")],
     "how is Ambassador's global rate-limit quota held consistent across four replicas",
     "ambassador rate limit service redis go consumer shard global quota"),
    # --- 33 ---
    ("Gloo's transformation filter rewrites legacy XML requests into JSON before they hit the upstream; the alternative would have been a new adapter service, which the team vetoed on maintenance grounds.", "decision", "technical", False,
     [("Gloo", "tool"), ("XML", "technology"), ("JSON", "technology"), ("transformation filter", "pattern")],
     [("Gloo", "transformation filter", "USES")],
     "which Gloo feature rewrote legacy XML to JSON without standing up a new adapter service",
     "gloo transformation filter xml json legacy adapter rewrite upstream"),
    # --- 34 ---
    ("Kong's key-auth plugin indexes API keys in PostgreSQL with a hashed-column lookup; the earlier plaintext column leaked via a read-replica snapshot to a training environment and triggered a key rotation.", "decision", "technical", False,
     [("Kong", "tool"), ("key-auth", "pattern"), ("PostgreSQL", "database"), ("read-replica", "pattern")],
     [("Kong", "PostgreSQL", "USES"), ("key-auth", "PostgreSQL", "DEPENDS_ON")],
     "which Kong lookup change followed the read-replica leak of plaintext API keys into training",
     "kong key auth postgresql hash column plaintext leak replica rotate"),
    # --- 35 ---
    ("Envoy's lua filter adds a request-id header when one is missing and strips the inbound value at the edge; this closed a spoofing path where downstream logs trusted client-supplied trace ids blindly.", "problem", "technical", False,
     [("Envoy", "tool"), ("lua filter", "pattern"), ("request-id", "config")],
     [("Envoy", "lua filter", "USES"), ("lua filter", "request-id", "CONFIGURES")],
     "which Envoy filter rewrote request-id at the edge after logs trusted spoofed trace ids",
     "envoy lua filter request id edge strip spoof trace log downstream"),
    # --- 36 ---
    ("HAProxy runtime socket lets us drain a backend without a reload; the earlier hard-reload path dropped long-lived WebSocket sessions and support tickets spiked every deploy window.", "fact", "technical", False,
     [("HAProxy", "tool"), ("runtime socket", "api"), ("WebSocket", "protocol")],
     [("HAProxy", "runtime socket", "USES")],
     "which HAProxy interface avoids a hard reload and keeps WebSocket sessions alive during deploys",
     "haproxy runtime socket drain reload websocket session deploy support"),
    # --- 37 ---
    ("KrakenD endpoint definitions live in a flexible-config JSON loaded at boot; templating lets a single upstream definition feed the iOS, Android, and web BFFs with their own field-selection projections.", "architecture", "technical", False,
     [("KrakenD", "tool"), ("iOS", "platform"), ("Android", "platform"), ("BFF", "pattern")],
     [("KrakenD", "BFF", "APPLIES_TO")],
     "how does KrakenD share one upstream definition across iOS, Android, and web BFFs",
     "krakend flexible config template ios android web bff upstream field"),
    # --- 38 ---
    ("Emissary's Host CRD binds the TLS cert to the hostname separately from the Mapping; before the split, rotating a wildcard cert forced an edit of every route that used that host.", "architecture", "technical", False,
     [("Emissary", "tool"), ("Host", "api"), ("Mapping", "api"), ("TLS", "protocol")],
     [("Emissary", "Host", "USES"), ("Host", "TLS", "CONFIGURES")],
     "how did Emissary's Host CRD decouple TLS cert rotation from route definitions",
     "emissary host crd mapping tls wildcard cert rotate hostname route"),
    # --- 39 ---
    ("Linkerd 2.14 added native mesh-expansion so the external billing VM is a mesh member without a sidecar on the VM itself; a gateway on the cluster edge handles the mTLS hop for that workload.", "milestone", "technical", False,
     [("Linkerd", "tool"), ("mesh-expansion", "pattern"), ("billing", "service"), ("mTLS", "protocol")],
     [("Linkerd", "mesh-expansion", "IMPLEMENTS"), ("mesh-expansion", "mTLS", "USES")],
     "which Linkerd 2.14 feature let the external billing VM join the mesh without a VM sidecar",
     "linkerd 2 14 mesh expansion billing vm gateway mtls external"),
    # --- 40 ---
    ("Consul's intention API pins service-to-service allow rules declaratively; deny-by-default was the default switch we flipped after a drift audit turned up eight legacy allow-all pairs.", "milestone", "technical", False,
     [("Consul", "tool"), ("intention", "api"), ("allow-all", "config")],
     [("Consul", "intention", "USES"), ("intention", "allow-all", "REPLACES")],
     "which Consul API pinned service allow rules and what audit finding drove deny-by-default",
     "consul intention allow deny default audit legacy service pair drift"),
    # --- 41 ---
    ("Istio's EnvoyFilter is a last-resort hammer; the team treats every EnvoyFilter PR as an RFC with a migration plan because control-plane upgrades have broken these patches twice already.", "preference", "technical", False,
     [("Istio", "tool"), ("EnvoyFilter", "api")],
     [("Istio", "EnvoyFilter", "USES")],
     "why does the team treat every EnvoyFilter PR as an RFC with a migration plan",
     "istio envoyfilter rfc migration control plane upgrade break patch"),
    # --- 42 ---
    ("Tyk's Python middleware hook enriches JWT claims from an internal user service; Lua was the first pick but Python matched the existing serverless codebase and cut the learning curve for the team.", "preference", "technical", False,
     [("Tyk", "tool"), ("Python", "language"), ("Lua", "language"), ("JWT", "protocol")],
     [("Tyk", "Python", "USES"), ("Python", "Lua", "PREFERS")],
     "why did Tyk JWT enrichment land in Python instead of Lua despite Lua being the first pick",
     "tyk python middleware jwt claim lua enrich serverless learning curve"),
    # --- 43. noise ---
    ("The office coffee grinder is down to one speed setting and everyone is negotiating whose bag of beans it is this week.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Kong Ingress Controller is the source of truth for the staging cluster routes; any manual kubectl edit gets reverted by the controller within thirty seconds and we stopped trying.", "reference", "technical", False,
     [("Kong Ingress Controller", "tool"), ("kubectl", "command")],
     [("Kong Ingress Controller", "kubectl", "REPLACES")],
     "why did manual kubectl edits stop being a viable workflow on the staging cluster",
     "kong ingress controller kubectl staging route revert source truth"),
    # --- 45 ---
    ("Envoy access logs ship in ECS-compatible JSON to the logging pipeline; grep-friendly plaintext was tempting but the field schema drift across services made downstream dashboards brittle.", "reference", "technical", False,
     [("Envoy", "tool"), ("ECS", "publication"), ("JSON", "technology"), ("access log", "concept")],
     [("Envoy", "JSON", "USES"), ("Envoy", "ECS", "IMPLEMENTS")],
     "why did Envoy access logs standardise on ECS JSON rather than plaintext for the pipeline",
     "envoy access log ecs json plaintext grep schema drift dashboard"),
    # --- 46 ---
    ("Cilium's Hubble exports flow metadata to OTLP; the Kiali view on the old Istio install was siloed inside the mesh and never reached the platform team's unified observability stack.", "reference", "technical", False,
     [("Cilium", "tool"), ("Hubble", "tool"), ("OTLP", "protocol"), ("Kiali", "tool"), ("Istio", "tool")],
     [("Hubble", "OTLP", "USES"), ("Hubble", "Kiali", "REPLACES")],
     "how does Hubble export flow metadata and which siloed Istio view did it retire",
     "cilium hubble otlp kiali istio observability platform unified flow"),
    # --- 47 ---
    ("Traefik's middleware chain applies the security headers first, then rate-limit, then auth-forward to Authelia; swapping the order once bypassed rate-limit on authenticated paths in a scary way.", "reference", "technical", False,
     [("Traefik", "tool"), ("Authelia", "tool"), ("middleware chain", "pattern")],
     [("Traefik", "Authelia", "USES"), ("Traefik", "middleware chain", "CONFIGURES")],
     "why does the Traefik middleware chain put security headers before rate-limit and Authelia",
     "ordering hsts throttle forward auth bypass swap risk"),
    # --- 48 ---
    ("HAProxy's Stick-Table tracks per-IP request rate for a three-minute rolling window; the data exposed over the stats socket feeds a Prometheus exporter that already sits beside the node.", "reference", "technical", False,
     [("HAProxy", "tool"), ("Stick-Table", "api"), ("Prometheus", "tool"), ("stats socket", "api")],
     [("HAProxy", "Stick-Table", "USES"), ("Stick-Table", "Prometheus", "COMMUNICATES_WITH")],
     "how does HAProxy's Stick-Table feed per-IP request-rate data into the Prometheus exporter",
     "haproxy stick table per ip rate stats socket prometheus exporter"),
    # --- 49 ---
    ("Consul Connect's proxy defaults hold the global timeout and retry policy; per-service overrides live in the service-defaults config entry, which the platform team owns in a separate repo.", "reference", "technical", False,
     [("Consul Connect", "tool"), ("proxy defaults", "config"), ("service-defaults", "config")],
     [("Consul Connect", "proxy defaults", "CONFIGURES")],
     "where do Consul Connect's global and per-service timeout and retry defaults live",
     "consul connect proxy default service default timeout retry config entry"),
    # --- 50 ---
    ("Cut over the public API from Kong OSS to Kong Gateway Enterprise for the developer portal and workspace features; the open-source build was patched with custom plugins that a staff engineer owned alone.", "milestone", "technical", False,
     [("Kong OSS", "tool"), ("Kong Gateway Enterprise", "tool"), ("developer portal", "service"), ("workspace", "api")],
     [("Kong Gateway Enterprise", "Kong OSS", "REPLACES"), ("Kong Gateway Enterprise", "developer portal", "IMPLEMENTS")],
     "which Kong edition took over the public API to get the developer portal and workspace features",
     "kong oss enterprise developer portal workspace custom plugin staff"),
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
