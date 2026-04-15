"""One-off emitter for retrieval top-up batch-019 — acronym-kind queries slice.

Writes 100 rows to data/v2/retrieval/batch_019.tmp.jsonl with ids ret-01801..01900.
Each row references a source row in shared.jsonl at lines SHARED_OFFSET+1..SHARED_OFFSET+100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_PATH = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_019.tmp.jsonl"
ID_OFFSET = 1800
SHARED_OFFSET = 1800
QUERY_KIND = "acronym"

QUERIES: list[str] = [
    # 1801 Karpenter vs Cluster Autoscaler, spot fleet
    "Karpenter swapped CA on spot fleet; node launch <30s",
    # 1802 Cluster Autoscaler stays on stateful ASGs
    "CA kept on stateful NGs; ASG shape beat Karpenter bin-pack",
    # 1803 PodDisruptionBudget maxUnavailable blocked drain
    "PDB maxUnavail=0 stalled drain; minAvail unblocked RR",
    # 1804 GPU taint NoExecute, Helm tolerations
    "GPU pool NoExec taint; tolerations only in inference HV",
    # 1805 EndpointSlices replaced Endpoints, kube-proxy CPU
    "EPS replaced EP obj; kube-proxy CPU down 22% on big svc",
    # 1806 Cilium NetworkPolicy FQDN egress to LLM
    "Cilium NP w/ FQDN gates egress to LLM; IP-block DNS churn",
    # 1807 Gateway API HTTPRoute rollout behind ingress
    "GW API behind IGW on 2026-02-18; HTTPRoute w/ Ing 3-wk bake",
    # 1808 nginx-ingress deprecated, Envoy Gateway default
    "nginx-IC deprecated for new svcs; GW API + EG is default",
    # 1809 KEDA scales Kafka consumer on lag, HPA blind
    "KEDA scales Kafka off lag; HPA blind to backlog",
    # 1810 noise
    "1 sec, gonna peek at pod evts",
    # 1811 VPA recommend-only, restarts batch
    "VPA in rec-only on prod; auto updates killed LR batch pods",
    # 1812 Helm subcharts flattened, values tree
    "Helm subcharts flattened after 4-lvl values override tree",
    # 1813 Kustomize overlays + Helm for third-party
    "Kustomize OLs for env patches; Helm stays for 3P charts",
    # 1814 Crossplane replaces Terraform for RDS and S3
    "XP runs RDS + S3 from k8s; TF retired on those classes",
    # 1815 ArgoCD ApplicationSet git generator per tenant
    "ACD AppSet w/ git gen = 1 App per tenant dir",
    # 1816 FluxCD vs ArgoCD UI tie-breaker
    "Flux vs ACD; ACD UI won w/ support team driving rollouts",
    # 1817 Velero restore drill monthly PodSecurityPolicy
    "Velero restore drill monthly; dry run caught missing PSP map",
    # 1818 etcd compaction auto-compaction-retention
    "etcd compact lag broke API 2026-03-08; ACR 1h -> 8h fix",
    # 1819 kube-apiserver APF priority levels CronJob
    "APF priority lvls shielded health EP from CJ list-pods loop",
    # 1820 CoreDNS NodeLocal cache DNS p99
    "CoreDNS NL cache cut in-cluster DNS p99 80ms -> 4ms",
    # 1821 Prometheus federation -> Thanos sidecar S3
    "Prom fed replaced by Thanos SC uploads to OS",
    # 1822 Mimir beat Thanos at 3M samples/s
    "Mimir beat Thanos at 3M samp/s; MT backend moved to Mimir",
    # 1823 Cortex vs Mimir fork roadmap
    "Cortex vs Mimir; fork split, Mimir got the feature pace",
    # 1824 Loki TSDB shipper replaces BoltDB
    "Loki TSDB shipper replaced BoltDB; 14d label Q 18s -> <3s",
    # 1825 Tempo monolithic to S3, no ES or Cassandra
    "Tempo mono binary ships traces to S3; no ES/C* backend",
    # 1826 Grafana Alloy replaces Grafana Agent
    "GA Alloy replaced legacy GA on collectors; 1 cfg for M/L/T",
    # 1827 OpenTelemetry Collector pipeline OTLP no SDK
    "OTel Col pipe: sampler -> batch -> OTLP; no vendor SDK in app",
    # 1828 Jaeger Cassandra retired, Tempo S3 replaces
    "Jaeger on C* retired after compaction storms; Tempo S3 in",
    # 1829 Datadog APM, Honeycomb trace analytics
    "DD carries APM; HC added for deep trace the DD UI flattens",
    # 1830 New Relic lost RFP vs Datadog pricing 1000 hosts
    "NR lost RFP vs DD on cost past 1k hosts; pricing curve decided",
    # 1831 Prometheus exemplars link histograms to Tempo
    "Exemplars wire Prom histos to Tempo TIDs; 1-click to span",
    # 1832 RED metrics API, USE for nodes
    "RED on API tier; USE kept for node-level resource view",
    # 1833 SLO multi-window burn rate 2h 24h pair
    "SLO burn rate 2h/24h MW pair; fast pages, slow emails",
    # 1834 noise
    "1 sec, need to check node conds",
    # 1835 Google SRE workbook 14.4 and 6 factors
    "MBR alert defn from Google SRE WB; 14.4 & 6 saved a wk tuning",
    # 1836 blameless postmortem Markdown GitHub
    "Blameless PM in MD template w/ TL/CF/RT; lives in runbook GH repo",
    # 1837 Descheduler nightly LowNodeUtilization
    "Descheduler nightly; LNU plugin rebal after taint shifts",
    # 1838 NodeLocal DNSCache mesh DNS errors
    "NL DNSCache replaced per-pod resolver; mesh DNS errs -> 0",
    # 1839 Argo Rollouts AnalysisTemplate Prometheus
    "AR drives canary/BG w/ AT; Prom Q gates auto next step",
    # 1840 Flagger vs Argo Rollouts ArgoCD UI
    "Flagger tried first for PD; AR UI w/ ACD won the bake-off",
    # 1841 Kyverno replaces Gatekeeper Rego YAML
    "Kyverno replaced GK for AP; YAML native vs wrestling Rego",
    # 1842 cert-manager DNS01 vs HTTP01 private subnets
    "CM w/ DNS01 issues cluster-wide certs; HTTP01 killed by priv subnets",
    # 1843 External Secrets Operator Vault sidecar retired
    "ESO pulls from HV into k8s secrets; VA SC pattern retired",
    # 1844 Istio ambient mode sidecar injection retained
    "Istio AM live on TD 2026-03-22; SC inj stays for per-pod policy",
    # 1845 Linkerd replaced by Istio payments mTLS
    "Linkerd replaced by Istio on payments; mTLS + AP covered compliance",
    # 1846 OpenCost cost per namespace Prometheus
    "OC reports cost/NS off Prom; finance stopped manual exports",
    # 1847 Falco syscall SIEM kubectl exec payments
    "Falco -> SIEM syscall evts; default RS caught exec on payments pod <40s",
    # 1848 Tetragon eBPF alongside Falco dedup
    "Tetragon eBPF alongside Falco; feeds converge no dedup noise",
    # 1849 kube-bench CIS weekly CronJob
    "kube-bench weekly CJ per node; CIS drift = ticket, not audit surprise",
    # 1850 Robusta Prometheus Slack runbook
    "Robusta routes Prom alerts to Slack; runbook links in payload",
    # 1851 GraalVM native-image Micronaut cold start reflection
    "GVM NI cut MN cold start 1.4s -> 38ms; TA runs produced refl cfg",
    # 1852 GraalVM reflection Jackson polymorphic JIT fallback
    "GVM refl caveat hit Jackson poly deser; RM metadata over JIT fallback",
    # 1853 ZGC replaces G1 trading gateway generational
    "ZGC replaced G1 on LL trading GW; tail pauses <1ms w/ gen ZGC",
    # 1854 Shenandoah vs ZGC analytics JVM 200 GB
    "Shenandoah vs ZGC on analytics JVM; ZGC won past 200 GB heap",
    # 1855 Project Loom virtual threads Netty JDBC
    "PL VTs swept Netty TP juggling; blocking JDBC stopped starving exec",
    # 1856 Project Panama foreign linker JNI ICU4C
    "PP FL replaced JNI for ICU4C bindings; Java side stayed TS",
    # 1857 Project Valhalla value types map tiles
    "PV VTs landed for coord class; map tiles heap -1/3",
    # 1858 Truffle GraalVM PEG parser policy DSL
    "Truffle on GVM reused PEG parser across policy DSL + scripting; PE covered speed",
    # 1859 V8 hidden classes inline caches late field
    "V8 HCs penalised evt obj when late field changed shape; IC restored",
    # 1860 noise
    "1 sec, pulling up that bench log",
    # 1861 Node 22 permission model postinstall allowlist
    "N22 perm model scoped build tool to AL paths; postinstall exfil killed",
    # 1862 Deno KV session edge worker auth
    "DKV backed session store for EW; single-region SC kept auth MW simple",
    # 1863 Bun fetch HTTP client origin webhook
    "Bun fetch reuses 1 HTTP client/origin; WH fan-out conn churn dropped",
    # 1864 CPython PEP 659 adaptive interpreter
    "CPy PEP 659 AI specialised hot attr BC; num loops faster, no C-ext",
    # 1865 PyPy JIT warmup CLI CPython admin
    "PyPy JIT WU still hurt short CLIs; CPy on admin, PyPy on LR workers",
    # 1866 Ruby YJIT Rails dashboard exec-mem
    "Ruby YJIT ~1.4x on Rails DB EPs; exec-mem cap raise absorbed uplift",
    # 1867 Erlang BEAM hot code reload two-version
    "BEAM HCR shipped pricing fix w/ 0 dropped sess; 2-ver module ran old callers",
    # 1868 Elixir LiveView morphdom JS bundle
    "EX LV drove dash w/ server-rendered diffs; JS = LV client + morphdom",
    # 1869 Crystal type inference CLI codegen cache
    "Crystal TI carried CLI rewrite w/ few annot; inc codegen reuses ll.bc",
    # 1870 Nim ORC vs ARC backend daemon cycles
    "Nim ORC replaced ARC on BE daemon; cycle GC stopped Mon mem growth",
    # 1871 Zig comptime protocol parser build time
    "Zig CT gen protocol parser at BT from schema; RT dispatch tbl gone",
    # 1872 Rust GATs async Stream boxed future
    "Rust GATs kept async Stream adapter ZC; boxed-fut shim dropped since 21",
    # 1873 Rust async traits stable dyn-compat plugin
    "Rust AT stable closed last dyn-compat WA for plugin IF; crate out of DT",
    # 1874 Go generics pipeline refactor interface
    "Go generics adoption stalled on old DP; constraint-heavy IFs uglier",
    # 1875 Kotlin Multiplatform Android iOS domain
    "KMP shared domain + net layer across Android + iOS; view stayed native",
    # 1876 Scala 3 inline metaprogramming macro-paradise schema
    "Scala 3 inline MP replaced macro-paradise on schema deriv lib; CE point at user code",
    # 1877 Swift macros Codable DTO SwiftSyntax
    "Swift macros gen Codable conf for net DTOs; prev SS codegen skipped",
    # 1878 OCaml multicore domains SAT 16-core
    "OCaml MC domains unblocked SAT encoder; 16c CPU past old 1c ceiling",
    # 1879 Roc lambda sets closure tag union
    "Roc LS closed closure-alloc Q; every cb site flat tag union no boxing",
    # 1880 Gleam OTP Erlang supervision interop
    "Gleam OTP wrappers let BEAM team adopt lang; Erlang module interop stayed sym",
    # 1881 F# computation expression retry timeout payments
    "F# CEs modelled retry/TO DSL for payments client; effect stays inspectable",
    # 1882 WebAssembly component model WIT image plugin
    "WASM CM let img proc plugin ship as 1 .wasm; host imports via WIT world",
    # 1883 WASI 0.2 preview2 filesystem sockets polyfill
    "WASI 0.2 landed P2 FS + sockets API; CLI dropped custom stdin polyfill",
    # 1884 noise
    "1 sec, pulling FG now",
    # 1885 Cranelift wasmtime vs LLVM cold compile
    "CL backend in wasmtime compiled cold fns ~6x faster than LLVM; SS w/i 10%",
    # 1886 Dafny ring buffer decreases Hoare
    "Dafny caught OBO in ring-buf enqueue pre-merge; proof needed decreases clause",
    # 1887 Idris elaborator reflection JSON derivation
    "Idris ER gen JSON codec at TC time; lib shipped w/o sep deriv macro",
    # 1888 MLIR dialects tensor IR frontend backend
    "MLIR dialects carried tensor IR FE -> BE; mono IR split into 3 dialects",
    # 1889 LLVM 19 ThinLTO cache link time
    "LLVM 19 TLTO cache inval avoided full re-link on hdr edit; CI LT -18%",
    # 1890 CRaC Spring Boot startup canary
    "CRaC CR cut SB startup <100ms on canary fleet; warm caches survived restore",
    # 1891 OpenJ9 batch class data sharing HotSpot
    "OJ9 stayed on LR batch JVMs; CDS + shared caches beat HS footprint",
    # 1892 Julia precompilation 1.9 first-plot
    "Julia pkg PC cached native code on 1.9; first-plot lat complaints ended",
    # 1893 Mojo MLIR Python C extension kernels
    "Mojo MLIR pipe lowers Py-like code to vendor kernels; no C-ext fast path",
    # 1894 GCC 14 -fhardened firmware mitigation
    "GCC 14 -fhardened flipped whole mit set for FW build; bespoke list dropped",
    # 1895 Haskell GHC 9.10 delimited continuations CPS
    "GHC 9.10 DC prim let effect lib drop CPS-xform WA; TEs improved",
    # 1896 D BetterC embedded bootloader 32 KB
    "D BC subset powered embedded BL; RT-free code kept bin <32 KB",
    # 1897 Chicken Scheme blocking GC generational pricing
    "Chicken blocking-mode GC made pricing tool lat predictable; gen mode hit 20ms tail",
    # 1898 Erlang JIT BeamAsm OTP 26 routing
    "BeamAsm JIT on OTP 26 gave routing svc ~30% TP; no src changes needed",
    # 1899 LuaJIT trace compiler rules engine NYI
    "LJ TC still beat port candidates on rules engine; NYI BL caught escapes",
    # 1900 TypeScript 5.5 regex capture groups d.ts
    "TS 5.5 inferred types on regex cap groups; hand d.ts overrides removed",
]


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)

    with SHARED_PATH.open("r", encoding="utf-8") as f:
        source_lines = f.readlines()

    rows = []
    for i, query in enumerate(QUERIES):
        shared_line_idx = SHARED_OFFSET + i
        source_row = json.loads(source_lines[shared_line_idx])
        source_id = source_row["id"]
        positive = source_row["text"]

        row_id = f"ret-{ID_OFFSET + i + 1:05d}"
        rows.append({
            "id": row_id,
            "source_id": source_id,
            "query": query,
            "positive": positive,
            "query_kind": QUERY_KIND,
        })

    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
