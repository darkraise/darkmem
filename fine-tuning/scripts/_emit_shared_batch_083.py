"""One-off emitter for shared-base batch-083 — technical domain (API gateways and service mesh).

Writes 50 rows to data/v2/shared/batch_083.tmp.jsonl with ids shared-04101..04150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_083.tmp.jsonl"
ID_OFFSET = 4100

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Envoy replaced nginx as the L7 proxy in front of the checkout cluster; xDS dynamic config let the routes update without a reload SIGHUP.", "decision", "technical", False,
     [("Envoy", "service"), ("nginx", "service"), ("xDS", "protocol")],
     [("Envoy", "nginx", "REPLACES")],
     "which L7 proxy took over from nginx for dynamic checkout routing",
     "L7 proxy dynamic config xDS reload swap front cluster"),
    # --- 2 ---
    ("Istio sidecar injection added Envoy to every pod via the istio-proxy container; pod startup ballooned by 2 seconds because of the iptables init.", "fact", "technical", False,
     [("Istio", "framework"), ("Envoy", "service"), ("istio-proxy", "service"), ("iptables", "tool")],
     [("Istio", "Envoy", "USES")],
     "what slowed pod startup after Istio sidecar injection landed",
     "sidecar inject init container pod start iptables delay"),
    # --- 3 ---
    ("Linkerd replaced Istio for the platform team; the Rust micro-proxy cut sidecar memory from 120 MB to 18 MB per pod.", "decision", "technical", False,
     [("Linkerd", "framework"), ("Istio", "framework"), ("Rust", "language")],
     [("Linkerd", "Istio", "REPLACES")],
     "which mesh took over from Istio to drop sidecar memory cost",
     "mesh swap micro proxy memory footprint sidecar Rust"),
    # --- 4 ---
    ("Cilium service mesh in ambient mode replaced the kube-proxy plus Envoy sidecar combo; eBPF datapath kept L4 routing in kernel without per-pod proxy hops.", "decision", "technical", False,
     [("Cilium", "framework"), ("kube-proxy", "service"), ("Envoy", "service"), ("eBPF", "technology")],
     [("Cilium", "kube-proxy", "REPLACES")],
     "which mesh datapath collapsed kube-proxy and the Envoy sidecar",
     "eBPF kernel datapath ambient kube proxy sidecar replace"),
    # --- 5 ---
    ("Ambient mesh on Istio improves on the sidecar model; ztunnel handles L4 mTLS and waypoint proxies opt in for L7, cutting baseline overhead per pod.", "architecture", "technical", False,
     [("Istio", "framework"), ("ztunnel", "service")],
     [("Istio", "Istio", "IMPROVES_ON")],
     "which Istio mode improves on sidecar by splitting L4 and L7 layers",
     "ambient sidecar L4 L7 split waypoint baseline overhead"),
    # --- 6 ---
    ("Consul Connect handled mesh mTLS for the VM-and-Kubernetes hybrid fleet; SPIFFE IDs spanned both worlds because Istio assumed pure k8s identity.", "architecture", "technical", False,
     [("Consul Connect", "framework"), ("SPIFFE", "protocol"), ("Istio", "framework"), ("Kubernetes", "platform")],
     [("Consul Connect", "Istio", "REPLACES")],
     "which mesh fit the hybrid VM-and-Kubernetes identity story best",
     "hybrid VM mesh identity span SPIFFE assume pure k8s"),
    # --- 7 ---
    ("Kong gateway sat at the north-south edge for the public APIs; the plugin model carried the OIDC validator that the in-cluster mesh never saw.", "architecture", "technical", False,
     [("Kong", "service"), ("OIDC", "protocol")],
     [],
     "which gateway carried the OIDC plugin at the public north-south edge",
     "north south gateway plugin OIDC public API edge mesh"),
    # --- 8 ---
    ("Tyk replaced Kong for the partner API tier; the GraphQL universal data layer collapsed three downstream REST calls into one federated schema.", "decision", "technical", False,
     [("Tyk", "service"), ("Kong", "service"), ("GraphQL", "technology"), ("REST", "protocol")],
     [("Tyk", "Kong", "REPLACES")],
     "which gateway took over Kong's role for the partner GraphQL tier",
     "GraphQL federate downstream REST collapse partner gateway"),
    # --- 9 ---
    ("KrakenD stitched together six microservice REST endpoints into a single mobile-friendly aggregate; the declarative config beat hand-written BFFs on maintenance.", "decision", "technical", False,
     [("KrakenD", "service"), ("REST", "protocol"), ("BFF", "pattern")],
     [("KrakenD", "BFF", "REPLACES")],
     "which gateway replaced hand-rolled BFFs for the mobile aggregate",
     "aggregate stitch declarative mobile backend frontend swap"),
    # --- 10. noise ---
     ("hold up the control plane is reconciling", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("AWS API Gateway HTTP API replaced the REST API variant on the lambda webhook surface; cost fell 70 percent and JWT authorizers ran natively.", "decision", "technical", False,
     [("AWS API Gateway", "service"), ("JWT", "protocol")],
     [("AWS API Gateway", "AWS API Gateway", "REPLACES")],
     "which API Gateway flavor took over from the REST variant on Lambda",
     "HTTP API REST flavor swap JWT authorizer cost drop"),
    # --- 12 ---
    ("Apigee X handled the monetized partner program; quota tiers and analytics dashboards were sold to non-engineering owners more easily than Kong's admin API.", "decision", "technical", False,
     [("Apigee X", "service"), ("Kong", "service")],
     [("Apigee X", "Kong", "REPLACES")],
     "which gateway took the monetized partner tier from Kong",
     "monetize quota analytic non engineer owner sell partner"),
    # --- 13 ---
    ("gRPC routing through Envoy used HTTP/2 stream multiplexing; the per-method route table beat REST path globs on the inventory service fan-out.", "architecture", "technical", False,
     [("gRPC", "protocol"), ("Envoy", "service"), ("HTTP/2", "protocol"), ("REST", "protocol")],
     [("gRPC", "REST", "IMPROVES_ON")],
     "which routing model fit the inventory gRPC fan-out cleanly",
     "gRPC HTTP2 stream method route table REST path swap"),
    # --- 14 ---
    ("mTLS in the Linkerd mesh rotated identities every 24 hours; the trust anchor was held offline and the issuer cert rolled monthly via cert-manager.", "architecture", "technical", False,
     [("Linkerd", "framework"), ("mTLS", "protocol"), ("cert-manager", "tool")],
     [("Linkerd", "mTLS", "USES")],
     "which mesh handled the 24-hour mTLS identity rotation cleanly",
     "mTLS rotate trust anchor issuer cert mesh identity"),
    # --- 15 ---
    ("Traffic shaping on Istio split 5 percent of checkout traffic to the v2 service; the VirtualService weight matched the deploy controller's canary stage.", "architecture", "technical", False,
     [("Istio", "framework"), ("VirtualService", "config")],
     [],
     "which Istio object held the 5 percent canary weight on checkout",
     "weight split canary stage virtual service traffic shape"),
    # --- 16 ---
    ("Envoy retry policy on the orders route was capped at 2 attempts with 25 ms jitter; uncapped retries had amplified the cascading 503 storm during the Redis blip.", "decision", "technical", False,
     [("Envoy", "service"), ("Redis", "database")],
     [],
     "which retry cap on Envoy stopped the cascading 503 storm",
     "retry cap jitter cascade 503 storm policy backoff"),
    # --- 17 ---
    ("Timeouts at the mesh layer were standardized at 2 seconds via Linkerd ServiceProfile; per-call deadlines from clients still won when shorter.", "architecture", "technical", False,
     [("Linkerd", "framework"), ("ServiceProfile", "config")],
     [],
     "which Linkerd object set the standard 2-second mesh timeout",
     "timeout mesh standard deadline client shorter override"),
    # --- 18 ---
    ("Sidecar observability with Envoy emitted access logs in JSON to Loki; the per-request trace ID stitched the proxy log to the application span.", "architecture", "technical", False,
     [("Envoy", "service"), ("Loki", "service")],
     [],
     "which observability path linked Envoy access logs to app spans",
     "access log JSON trace ID stitch proxy span sidecar"),
    # --- 19 ---
    ("Gateway API spec replaced the older Ingress resource for the platform; HTTPRoute and ReferenceGrant gave cleaner cross-namespace delegation than annotations.", "decision", "technical", False,
     [("Gateway API", "api"), ("Ingress", "api"), ("HTTPRoute", "config"), ("ReferenceGrant", "config")],
     [("Gateway API", "Ingress", "REPLACES")],
     "which Kubernetes API took over from Ingress for the gateway layer",
     "Gateway API HTTPRoute reference grant Ingress annotation swap"),
    # --- 20 ---
    ("Rate limiting policy on Kong used the redis strategy across 6 nodes; the local strategy had drifted between pods and let bursts through.", "decision", "technical", False,
     [("Kong", "service"), ("redis", "database")],
     [],
     "which Kong rate-limit strategy stopped the per-pod burst leak",
     "rate limit redis strategy local drift burst leak swap"),
    # --- 21 ---
    ("JWT validation at the Envoy gateway used the jwt_authn filter; the JWKS endpoint was cached for 5 minutes to absorb the IdP rotation hiccups.", "architecture", "technical", False,
     [("Envoy", "service"), ("jwt_authn", "config"), ("JWKS", "protocol"), ("IdP", "service")],
     [],
     "which Envoy filter handled JWT validation at the gateway edge",
     "JWT filter JWKS cache IdP rotation gateway validate"),
    # --- 22 ---
    ("Canary routing on Linkerd via Flagger rolled the new payments service; success-rate plus p99 latency gates promoted the canary in 6 stages.", "architecture", "technical", False,
     [("Linkerd", "framework"), ("Flagger", "tool")],
     [("Flagger", "Linkerd", "USES")],
     "which canary controller drove the payments rollout on Linkerd",
     "Flagger canary success rate latency gate stage promote"),
    # --- 23 ---
    ("Kuma mesh was rejected for the multi-zone build; the federation story trailed Istio's east-west gateway in late 2025 evaluations.", "decision", "technical", False,
     [("Kuma", "framework"), ("Istio", "framework")],
     [],
     "which mesh lost the multi-zone evaluation against Istio",
     "Kuma multi zone federate east west gateway evaluate reject"),
    # --- 24 ---
    ("Envoy WASM filters carried the custom auth header rewrite; Lua scripts had been replaced because the WASM ABI matched the production binary cleanly.", "decision", "technical", False,
     [("Envoy", "service"), ("WASM", "technology"), ("Lua", "language")],
     [("WASM", "Lua", "REPLACES")],
     "which extension model took over from Lua for Envoy auth rewrites",
     "WASM filter Lua script auth rewrite ABI prod swap"),
    # --- 25 ---
    ("Solo.io Gloo Edge fronted the gRPC services with web client transcoding; the grpc-web bridge avoided maintaining a parallel REST layer.", "architecture", "technical", False,
     [("Solo.io Gloo Edge", "service"), ("gRPC", "protocol"), ("grpc-web", "protocol"), ("REST", "protocol")],
     [("Solo.io Gloo Edge", "REST", "REPLACES")],
     "which gateway transcoded gRPC for the browser without a REST tier",
     "Gloo Edge gRPC web transcode bridge browser REST avoid"),
    # --- 26 ---
    ("Traefik ingress was preferred over nginx-ingress on the dev clusters; the dynamic provider model picked up CRDs without a reload cycle.", "preference", "technical", False,
     [("Traefik", "service"), ("nginx-ingress", "service"), ("CRDs", "config")],
     [("Traefik", "nginx-ingress", "PREFERS")],
     "which ingress beat nginx-ingress on dev for dynamic CRD pickup",
     "Traefik dynamic provider CRD reload dev cluster ingress"),
    # --- 27 ---
    ("Tyk Gateway open-source edition handled the internal admin API; the dashboard tier was skipped because Grafana already covered the metrics view.", "decision", "technical", False,
     [("Tyk Gateway", "service"), ("Grafana", "tool")],
     [],
     "which Tyk tier was used for the internal admin API surface",
     "Tyk OSS dashboard skip Grafana metric view admin API"),
    # --- 28 ---
    ("KrakenD was rejected for the partner-write API; the gateway's read-aggregate sweet spot did not cover the transactional write path needs.", "decision", "technical", False,
     [("KrakenD", "service")],
     [],
     "why did KrakenD lose the partner write API gateway slot",
     "read aggregate sweet spot transactional write reject"),
    # --- 29 ---
    ("AWS API Gateway WebSocket API carried the live-quote stream for the trading desk; the connection registry on DynamoDB scaled past 80k concurrent clients.", "architecture", "technical", False,
     [("AWS API Gateway", "service"), ("WebSocket", "protocol"), ("DynamoDB", "database")],
     [],
     "which AWS gateway flavor held the live-quote WebSocket fan-out",
     "WebSocket gateway live quote stream connection registry"),
    # --- 30 ---
    ("Apigee X analytics caught a rogue partner pulling 12x their quota; the spike alert on the per-key dashboard fired before billing noticed.", "milestone", "technical", False,
     [("Apigee X", "service")],
     [],
     "which Apigee tool caught the rogue partner quota burn",
     "analytic per key spike dashboard quota burn partner"),
    # --- 31 ---
    ("gRPC keepalive at the Envoy sidecar sent pings every 30 s; idle connections to the inventory service had been killed by the cloud LB at 60 s.", "problem", "technical", False,
     [("gRPC", "protocol"), ("Envoy", "service")],
     [],
     "which keepalive interval kept gRPC alive past the LB idle cut",
     "gRPC keepalive ping LB idle close 60 second sidecar"),
    # --- 32 ---
    ("mTLS in Cilium service mesh used SPIFFE IDs from the agent; the identity was tied to pod labels not IP, so churn during scale-up did not break trust.", "architecture", "technical", False,
     [("Cilium", "framework"), ("mTLS", "protocol"), ("SPIFFE", "protocol")],
     [("Cilium", "mTLS", "IMPLEMENTS")],
     "which Cilium identity model held mTLS trust through pod scale-up",
     "SPIFFE pod label identity scale churn trust mesh mTLS"),
    # --- 33 ---
    ("Traffic shaping with Linkerd TrafficSplit moved 1 percent of reads to the new search index; latency-based metrics promoted weekly after gate review.", "architecture", "technical", False,
     [("Linkerd", "framework"), ("TrafficSplit", "config")],
     [],
     "which Linkerd object split 1 percent of reads to the new index",
     "TrafficSplit weight read shift gate review weekly promote"),
    # --- 34. noise ---
    ("brb the DNS just stopped resolving for the cluster", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Retries were disabled on the payments POST in the Istio VirtualService; idempotency tokens were not yet wired and double charges had hit production once.", "decision", "technical", False,
     [("Istio", "framework"), ("VirtualService", "config")],
     [],
     "which mesh setting stopped duplicate payment POST retries",
     "retry disable POST payment idempotent token double charge"),
    # --- 36 ---
    ("Observability sidecars with the OpenTelemetry collector replaced the Datadog agent on every pod; one collector per node halved the resource hit.", "decision", "technical", False,
     [("OpenTelemetry", "framework"), ("Datadog", "service")],
     [("OpenTelemetry", "Datadog", "REPLACES")],
     "which observability model retired the per-pod Datadog agent",
     "OTel collector per node Datadog agent pod resource swap"),
    # --- 37 ---
    ("Ambient mesh waypoint proxies handled L7 policies only for the namespaces that opted in; the L4-only path stayed cheap on the noisy log shippers.", "architecture", "technical", False,
     [("waypoint", "service")],
     [],
     "which ambient component took L7 policy without forcing every pod",
     "waypoint opt in L7 policy L4 cheap log shipper namespace"),
    # --- 38 ---
    ("Gateway API GAMMA initiative was the reference for the mesh integration roadmap; service-to-service routing semantics aligned across Istio, Linkerd, and Cilium.", "reference", "technical", False,
     [("Gateway API", "api"), ("GAMMA", "concept"), ("Istio", "framework"), ("Linkerd", "framework"), ("Cilium", "framework")],
     [],
     "which spec drove the cross-mesh service routing alignment",
     "GAMMA mesh integration spec align cross product service"),
    # --- 39 ---
    ("Rate limiting at the Envoy global ratelimit service used a Lyft-style descriptor list; the Redis backend behind the descriptor cache held the token state.", "architecture", "technical", False,
     [("Envoy", "service"), ("Redis", "database")],
     [],
     "which Envoy rate-limit pattern used descriptor lists with Redis",
     "global ratelimit descriptor Lyft Redis token cache state"),
    # --- 40 ---
    ("JWT validation at the Kong gateway used the jwt-signer plugin with JWKS rotation; the upstream service trusted the validated principal claim header.", "architecture", "technical", False,
     [("Kong", "service"), ("jwt-signer", "config"), ("JWKS", "protocol")],
     [],
     "which Kong plugin handled the JWT validation and JWKS rotation",
     "Kong plugin JWT signer JWKS rotate principal claim header"),
    # --- 41 ---
    ("Canary routing via Argo Rollouts plus Istio held the deploy decisions; SLO-based analysis on Prometheus metrics auto-rolled back two regressions last quarter.", "architecture", "technical", False,
     [("Argo Rollouts", "tool"), ("Istio", "framework"), ("Prometheus", "tool")],
     [("Argo Rollouts", "Istio", "USES")],
     "which canary controller used Prometheus SLO gates with Istio",
     "Argo Rollouts SLO gate auto rollback canary Prometheus"),
    # --- 42 ---
    ("Envoy circuit breakers were configured on the inventory cluster; max_pending_requests at 50 stopped the queue blow-up when the DB went read-only.", "decision", "technical", False,
     [("Envoy", "service")],
     [],
     "which Envoy setting stopped the queue blow-up during DB read-only",
     "circuit breaker max pending request queue DB read only"),
    # --- 43 ---
    ("Linkerd multicluster mirror service replaced a homegrown DNS-stub bridge; service discovery across the two regions stopped drifting after the swap.", "decision", "technical", False,
     [("Linkerd", "framework"), ("DNS", "protocol")],
     [("Linkerd", "DNS", "REPLACES")],
     "which Linkerd feature took over the DNS-stub cross-region bridge",
     "multi cluster mirror DNS stub region drift service swap"),
    # --- 44 ---
    ("Kong Mesh added Kuma's mesh capabilities to the Kong control plane; the unified policy surface beat running a separate mesh CLI alongside.", "decision", "technical", False,
     [("Kong Mesh", "service"), ("Kuma", "framework"), ("Kong", "service")],
     [("Kong Mesh", "Kuma", "BUILDS_ON")],
     "which product unified Kong's gateway with Kuma's mesh policies",
     "Kong Mesh Kuma unify control plane policy CLI single"),
    # --- 45 ---
    ("Envoy ext_authz delegated authorization to OPA; policies were authored in Rego and reloaded over xDS without restarting the data plane.", "architecture", "technical", False,
     [("Envoy", "service"), ("ext_authz", "config"), ("OPA", "tool"), ("Rego", "language"), ("xDS", "protocol")],
     [("Envoy", "OPA", "USES")],
     "which Envoy filter delegated authz to OPA without a restart",
     "ext authz OPA Rego policy reload xDS data plane delegate"),
    # --- 46 ---
    ("HAProxy was retired from the legacy ingress tier in favor of Envoy; xDS-driven config caught up to HAProxy's runtime API on the operational checklist.", "decision", "technical", False,
     [("HAProxy", "service"), ("Envoy", "service"), ("xDS", "protocol")],
     [("Envoy", "HAProxy", "REPLACES")],
     "which proxy retired HAProxy on the legacy ingress tier",
     "HAProxy retire ingress xDS runtime API checklist swap"),
    # --- 47 ---
    ("Tyk Gateway plugins were authored in Go via the gRPC plugin model; the in-process JS plugins had hit memory caps under sustained partner load.", "decision", "technical", False,
     [("Tyk Gateway", "service"), ("Go", "language"), ("gRPC", "protocol"), ("JS", "language")],
     [],
     "which Tyk plugin model replaced the in-process JS plugins",
     "Go gRPC plugin JS in process memory cap partner swap"),
    # --- 48 ---
    ("AWS API Gateway plus AWS WAF enforced rate limits and bot rules at the edge; the Lambda authorizer focused only on per-route business policy.", "architecture", "technical", False,
     [("AWS API Gateway", "service"), ("AWS WAF", "service"), ("Lambda", "service")],
     [("AWS API Gateway", "AWS WAF", "USES")],
     "which AWS pair handled edge rate limits and bot rules cleanly",
     "WAF rate limit bot edge gateway Lambda authorizer split"),
    # --- 49 ---
    ("Service mesh interface SMI was abandoned in 2025; concrete CRDs from Istio and Linkerd plus Gateway API GAMMA drove the integration story instead.", "milestone", "technical", False,
     [("SMI", "api"), ("Istio", "framework"), ("Linkerd", "framework"), ("Gateway API", "api"), ("GAMMA", "concept"), ("2025", "date")],
     [("Gateway API", "SMI", "REPLACES")],
     "when did the SMI mesh spec lose to vendor CRDs and GAMMA",
     "SMI abandon vendor CRD GAMMA Gateway API 2025 spec"),
    # --- 50 ---
    ("Cilium mesh ingress shipped on 2026-02-18 across the platform; the eBPF datapath plus L7 Envoy on demand kept p99 latency under 4 ms for the hottest service.", "milestone", "technical", False,
     [("Cilium", "framework"), ("Envoy", "service"), ("eBPF", "technology"), ("2026-02-18", "date")],
     [("Cilium", "Envoy", "USES")],
     "when did the Cilium mesh ingress ship and what was the p99 win",
     "Cilium ingress eBPF datapath Envoy demand p99 ship date"),
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
