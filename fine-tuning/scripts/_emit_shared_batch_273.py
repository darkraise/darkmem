"""One-off emitter for shared-base batch-273 — technical domain (Kubernetes networking, CNI plugins, service mesh, ingress, multi-cluster).

Writes 50 rows to data/v2/shared/batch_273.tmp.jsonl with ids shared-13601..13650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_273.tmp.jsonl"
ID_OFFSET = 13600

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("Replaced Flannel with Cilium across the staging fleet because the platform team wanted eBPF-backed NetworkPolicy and Hubble flow visibility without bolting on a separate agent.", "decision", "technical", False,
     [("Flannel", "technology"), ("Cilium", "technology"), ("eBPF", "technology"), ("NetworkPolicy", "api"), ("Hubble", "tool")],
     [("Cilium", "Flannel", "REPLACES"), ("Cilium", "eBPF", "USES"), ("Hubble", "Cilium", "DEPENDS_ON")],
     "which CNI took over from Flannel to bring eBPF policy and flow visibility into staging",
     "cilium flannel ebpf networkpolicy hubble staging replace cni"),
    # --- 2 --- architecture
    ("The production cluster runs Calico in eBPF dataplane mode so that kube-proxy is disabled entirely and service load balancing happens in the kernel without iptables chains.", "architecture", "technical", False,
     [("Calico", "technology"), ("eBPF", "technology"), ("kube-proxy", "service"), ("iptables", "technology")],
     [("Calico", "eBPF", "USES"), ("Calico", "kube-proxy", "REPLACES")],
     "how does the production cluster avoid running kube-proxy while still load-balancing services",
     "calico ebpf dataplane kube proxy iptables bypass kernel service"),
    # --- 3 --- milestone
    ("The 1.28 upgrade finally flipped kube-proxy from iptables to IPVS on the bare-metal pool, and p99 service latency dropped by a third once the per-node rule count stopped growing quadratically.", "milestone", "technical", False,
     [("kube-proxy", "service"), ("iptables", "technology"), ("IPVS", "technology"), ("1.28", "date")],
     [("IPVS", "iptables", "REPLACES")],
     "which kube-proxy mode swap on the bare-metal pool cut p99 service latency after the 1.28 upgrade",
     "kube proxy ipvs iptables 1.28 bare metal latency p99 drop"),
    # --- 4 --- fact
    ("EndpointSlices shard the endpoints of a single Service across multiple objects so that the watch traffic on huge headless Services stops saturating the apiserver during rollouts.", "fact", "technical", False,
     [("EndpointSlices", "api"), ("Service", "api"), ("apiserver", "service")],
     [("EndpointSlices", "Service", "APPLIES_TO")],
     "which Kubernetes object split endpoints to stop apiserver watch storms on huge Services",
     "endpointslices service apiserver watch rollout headless shard"),
    # --- 5 --- architecture
    ("The Gateway API spec defines GatewayClass, Gateway, and HTTPRoute as the three-layer model that is expected to replace the v1 Ingress resource over the next several releases.", "architecture", "technical", False,
     [("Gateway API", "api"), ("GatewayClass", "api"), ("Gateway", "api"), ("HTTPRoute", "api"), ("Ingress", "api")],
     [("Gateway API", "Ingress", "REPLACES")],
     "which three resources define the Gateway API model that is superseding Ingress",
     "gateway api gatewayclass httproute ingress spec three layer replace"),
    # --- 6 --- preference
    ("For new clusters the platform team prefers Cilium over Calico because the Hubble UI and ClusterMesh story land in a single install rather than as separate components to wire up.", "preference", "technical", False,
     [("Cilium", "technology"), ("Calico", "technology"), ("Hubble", "tool"), ("ClusterMesh", "technology")],
     [("Cilium", "Calico", "PREFERS"), ("ClusterMesh", "Cilium", "DEPENDS_ON")],
     "which CNI does the platform team choose for greenfield clusters and which two features seal the call",
     "cilium calico hubble clustermesh prefer greenfield install platform"),
    # --- 7 --- problem
    ("NodeLocalDNSCache stopped answering on two nodes after a kubelet restart left the dummy interface without the expected IP, and Pods fell back to CoreDNS across the wire with visible latency spikes.", "problem", "technical", False,
     [("NodeLocalDNSCache", "service"), ("kubelet", "service"), ("CoreDNS", "service"), ("Pods", "api")],
     [("NodeLocalDNSCache", "CoreDNS", "DEPENDS_ON")],
     "which DNS cache component went silent after kubelet restart and what fallback took the traffic",
     "nodelocaldns cache kubelet coredns pods latency dummy interface"),
    # --- 8 --- decision
    ("The team chose Istio over Linkerd 2 for the regulated tenant because the sidecar-based mTLS story integrated cleanly with the existing SPIFFE identity provider and the ops team already knew Envoy.", "decision", "technical", False,
     [("Istio", "framework"), ("Linkerd 2", "framework"), ("mTLS", "protocol"), ("SPIFFE", "protocol"), ("Envoy", "service")],
     [("Istio", "Linkerd 2", "PREFERS"), ("Istio", "Envoy", "USES"), ("Istio", "SPIFFE", "USES")],
     "which service mesh won over Linkerd 2 for the regulated tenant and which identity layer decided it",
     "istio linkerd2 mtls spiffe envoy mesh regulated tenant sidecar"),
    # --- 9 --- architecture
    ("North-south traffic enters through the Istio Ingress Gateway, which terminates TLS at the edge and feeds L7 Envoy filters that enforce JWT checks before the request hits the mesh proper.", "architecture", "technical", False,
     [("Istio Ingress Gateway", "service"), ("TLS", "protocol"), ("Envoy", "service"), ("JWT", "protocol")],
     [("Istio Ingress Gateway", "Envoy", "USES"), ("Envoy", "JWT", "APPLIES_TO")],
     "how does the Istio Ingress Gateway terminate TLS and run JWT checks before the mesh",
     "istio ingress gateway tls envoy filter jwt north south mesh edge"),
    # --- 10. noise ---
    ("The break-room kettle has been inherited three teams in a row and the descaling schedule is now a tiny sticky note that nobody wants to own.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- milestone
    ("Cilium ClusterMesh went live connecting the eu-west and us-east clusters over a mutually authenticated control plane, so Services in one cluster resolve and route to pods in the other without an external LB.", "milestone", "technical", False,
     [("Cilium ClusterMesh", "technology"), ("eu-west", "infrastructure"), ("us-east", "infrastructure"), ("Services", "api")],
     [("Cilium ClusterMesh", "Services", "APPLIES_TO")],
     "which Cilium feature stitched eu-west and us-east together so cross-cluster Services route without an external LB",
     "cilium clustermesh eu west us east cross cluster service pod route"),
    # --- 12 --- decision
    ("Switched the NGINX Ingress Controller deployments to Traefik on the edge tier because dynamic provider reloads beat the nginx.conf template rebuild under heavy ingress churn.", "decision", "technical", False,
     [("NGINX Ingress Controller", "service"), ("Traefik", "service"), ("nginx.conf", "file")],
     [("Traefik", "NGINX Ingress Controller", "REPLACES")],
     "which ingress controller took over from NGINX Ingress Controller and why the swap under heavy churn",
     "traefik nginx ingress controller reload dynamic churn edge tier"),
    # --- 13 --- milestone
    ("Topology Aware Hints steer ClusterIP traffic to endpoints in the same zone, which cut inter-AZ egress by roughly forty percent on the payments namespace without changing any application code.", "milestone", "technical", False,
     [("Topology Aware Hints", "api"), ("ClusterIP", "api"), ("payments", "project")],
     [("Topology Aware Hints", "ClusterIP", "APPLIES_TO")],
     "which service-routing feature reduced inter-AZ egress for the payments namespace without code changes",
     "topology aware hint clusterip zone egress az payments namespace"),
    # --- 14 --- fact
    ("A Service of type ExternalName resolves to a CNAME record that points outside the cluster, which is how the legacy mainframe gateway gets reached without a ClusterIP or a NodePort allocation.", "fact", "technical", False,
     [("ExternalName", "api"), ("CNAME", "protocol"), ("ClusterIP", "api"), ("NodePort", "api")],
     [("ExternalName", "CNAME", "USES")],
     "how does the cluster reach a legacy off-cluster mainframe without allocating a ClusterIP or NodePort",
     "externalname cname service clusterip nodeport legacy mainframe dns"),
    # --- 15 --- reference
    ("The official docs spell out three Ingress semantics differences between NGINX Ingress Controller, HAProxy Ingress, and Kong Ingress around path rewrites, session stickiness, and per-route timeouts.", "reference", "technical", False,
     [("NGINX Ingress Controller", "service"), ("HAProxy Ingress", "service"), ("Kong Ingress", "service")],
     [],
     "which three ingress controllers diverge on path rewrites, stickiness, and per-route timeouts per the docs",
     "nginx haproxy kong ingress rewrite stickiness timeout difference"),
    # --- 16 --- decision
    ("Replaced the per-node Weave Net pods with Antrea after the encryption overhead on Weave's fastdp path was producing visible tail latency on the internal streaming tier.", "decision", "technical", False,
     [("Weave Net", "technology"), ("Antrea", "technology"), ("fastdp", "protocol")],
     [("Antrea", "Weave Net", "REPLACES")],
     "which CNI took over from Weave Net after fastdp encryption started producing tail latency",
     "antrea weave net fastdp encryption tail latency streaming cni"),
    # --- 17 --- architecture
    ("Kube-router was chosen for the edge appliances because it bundles the CNI, kube-proxy, and BGP-based service advertisement into a single daemon instead of stacking three separate pieces.", "architecture", "technical", False,
     [("Kube-router", "technology"), ("BGP", "protocol"), ("kube-proxy", "service")],
     [("Kube-router", "BGP", "USES"), ("Kube-router", "kube-proxy", "REPLACES")],
     "which single-daemon CNI collapses kube-proxy and BGP service advertisement for edge appliances",
     "kube router bgp edge single daemon kube proxy advertise service"),
    # --- 18 --- preference
    ("For EKS clusters that need direct VPC IPs for Pods the team sticks with the AWS VPC CNI rather than an overlay, since shared security groups and flow logs line up without bridging.", "preference", "technical", False,
     [("EKS", "platform"), ("AWS VPC CNI", "technology"), ("Pods", "api"), ("VPC", "infrastructure")],
     [("AWS VPC CNI", "VPC", "USES")],
     "which CNI does the team prefer on EKS when Pods need native VPC IPs and matched flow logs",
     "aws vpc cni eks pod native security group flow log overlay"),
    # --- 19 --- fact
    ("Azure CNI pulls Pod IPs from the subnet the node lives in, so each Pod is first-class in the VNet and can be reached by non-cluster resources without any NAT hop.", "fact", "technical", False,
     [("Azure CNI", "technology"), ("VNet", "infrastructure"), ("NAT", "protocol"), ("Pod", "api")],
     [("Azure CNI", "VNet", "USES")],
     "how does Azure CNI give Pods VNet-native addresses that non-cluster resources can reach without NAT",
     "azure cni vnet pod subnet native nat free non cluster route"),
    # --- 20 --- decision
    ("Chose GCE CNI instead of Calico on the GKE tier because alias IP ranges and Cloud NAT plumbing already assume native routing and adding an overlay duplicated work.", "decision", "technical", False,
     [("GCE CNI", "technology"), ("Calico", "technology"), ("GKE", "platform"), ("Cloud NAT", "service"), ("alias IP", "technology")],
     [("GCE CNI", "Calico", "PREFERS"), ("GCE CNI", "alias IP", "USES")],
     "why did GKE clusters pick GCE CNI over Calico when Cloud NAT and alias IPs already handle routing",
     "gce cni calico gke alias ip cloud nat native routing overlay"),
    # --- 21 --- milestone
    ("Cilium eBPF with the Envoy integration shipped to the order-service namespace, which moved L7 HTTP and gRPC policy enforcement off the sidecars and into the CNI datapath.", "milestone", "technical", False,
     [("Cilium", "technology"), ("eBPF", "technology"), ("Envoy", "service"), ("gRPC", "protocol"), ("order-service", "project")],
     [("Cilium", "Envoy", "USES"), ("Envoy", "gRPC", "APPLIES_TO")],
     "which Cilium integration pulled L7 gRPC policy out of the sidecars for the order-service namespace",
     "cilium ebpf envoy order service l7 grpc policy datapath sidecar"),
    # --- 22 --- decision
    ("Cilium LB IPAM carves an advertised pool of LoadBalancer IPs and hands them out to Service objects, replacing the external MetalLB speaker layer the cluster used to run.", "decision", "technical", False,
     [("Cilium LB IPAM", "technology"), ("LoadBalancer", "api"), ("Service", "api"), ("MetalLB", "technology")],
     [("Cilium LB IPAM", "MetalLB", "REPLACES"), ("Cilium LB IPAM", "LoadBalancer", "APPLIES_TO")],
     "which Cilium feature hands out LoadBalancer IPs and retired the MetalLB speaker layer",
     "cilium lb ipam loadbalancer service metallb speaker replace"),
    # --- 23 --- decision
    ("Kubeproxy-free mode was enabled cluster-wide after benchmarking showed eBPF socket LB beating the IPVS rule table on short-lived connection bursts in the batch workload.", "decision", "technical", False,
     [("Kubeproxy-free", "pattern"), ("eBPF socket LB", "technology"), ("IPVS", "technology"), ("batch", "project")],
     [("eBPF socket LB", "IPVS", "REPLACES")],
     "which load-balancing mode replaced IPVS cluster-wide after short-burst benchmarks favoured eBPF",
     "kube proxy free ebpf socket lb ipvs batch burst benchmark mode"),
    # --- 24 --- problem
    ("NetworkPolicy egress rules were silently bypassed on legacy nodes because the host kernel predated the cgroup v2 hook Cilium relied on, and the fix was a staged kernel bump before expanding policy coverage.", "problem", "technical", False,
     [("NetworkPolicy", "api"), ("cgroup v2", "technology"), ("Cilium", "technology"), ("kernel", "platform")],
     [("Cilium", "cgroup v2", "DEPENDS_ON"), ("Cilium", "kernel", "DEPENDS_ON")],
     "why were NetworkPolicy egress rules skipped on legacy nodes and which upgrade unblocked coverage",
     "networkpolicy egress legacy kernel cgroup v2 cilium hook bypass"),
    # --- 25 --- reference
    ("The Gardener project documents a seed-shoot topology where each managed cluster runs as a shoot on a shared seed, and the networking section calls out Calico and Cilium as the two validated CNIs.", "reference", "technical", False,
     [("Gardener", "project"), ("Calico", "technology"), ("Cilium", "technology")],
     [],
     "which two CNIs does the Gardener seed-shoot networking doc call out as validated",
     "gardener seed shoot calico cilium cni managed cluster topology"),
    # --- 26 --- architecture
    ("Submariner stitches two on-prem clusters into a flat cross-cluster service fabric by running a gateway engine on one node per cluster and tunnelling pod CIDRs over IPsec between them.", "architecture", "technical", False,
     [("Submariner", "technology"), ("gateway engine", "service"), ("IPsec", "protocol"), ("pod CIDR", "config")],
     [("Submariner", "IPsec", "USES"), ("Submariner", "gateway engine", "HAS_PART")],
     "which multi-cluster tool tunnels pod CIDRs between on-prem clusters over IPsec and how is the gateway placed",
     "submariner ipsec gateway engine pod cidr multi cluster on prem"),
    # --- 27 --- fact
    ("CoreDNS replaced kube-dns as the in-cluster resolver starting with 1.13, and the pluggable chain means custom rewrite, forward, and cache blocks ship as a Corefile rather than as forked images.", "fact", "technical", False,
     [("CoreDNS", "service"), ("kube-dns", "service"), ("1.13", "date"), ("Corefile", "file")],
     [("CoreDNS", "kube-dns", "REPLACES")],
     "which in-cluster DNS server replaced kube-dns and where do the rewrite or forward plugins live now",
     "coredns kube dns 1.13 corefile plugin chain rewrite forward cache"),
    # --- 28 --- decision
    ("Linkerd 2 was picked over Istio on the internal platform cluster because the per-pod memory cost of the Rust proxy was under twenty megabytes and the ops overhead was simpler.", "decision", "technical", False,
     [("Linkerd 2", "framework"), ("Istio", "framework"), ("Rust", "language")],
     [("Linkerd 2", "Istio", "PREFERS"), ("Linkerd 2", "Rust", "USES")],
     "which service mesh won over Istio on the internal platform cluster and which proxy property decided it",
     "linkerd2 istio rust proxy memory internal platform mesh pick"),
    # --- 29 --- architecture
    ("The multi-tenant layer uses Kuma as a universal control plane speaking to Envoy data planes across Kubernetes and legacy VM workloads, so one policy language covers both halves of the estate.", "architecture", "technical", False,
     [("Kuma", "framework"), ("Envoy", "service"), ("Kubernetes", "platform"), ("VM", "infrastructure")],
     [("Kuma", "Envoy", "USES"), ("Kuma", "Kubernetes", "APPLIES_TO"), ("Kuma", "VM", "APPLIES_TO")],
     "which control plane unifies policy across Kubernetes and legacy VMs by talking to Envoy data planes",
     "kuma envoy kubernetes vm universal control plane multi tenant"),
    # --- 30 --- milestone
    ("The Gateway API conformance suite finally went green on the Cilium implementation in the 1.15 release, so HTTPRoute and TLSRoute shipped to staging without the previous Ingress fallback.", "milestone", "technical", False,
     [("Gateway API", "api"), ("Cilium", "technology"), ("HTTPRoute", "api"), ("TLSRoute", "api"), ("1.15", "date")],
     [("Cilium", "Gateway API", "IMPLEMENTS")],
     "which Cilium release passed Gateway API conformance and which two route kinds shipped to staging",
     "gateway api conformance cilium 1.15 httproute tlsroute ingress"),
    # --- 31 --- preference
    ("For network observability the ops team prefers Hubble over stand-alone flow collectors because the eBPF events feed dashboards and policy verdicts from the same pipeline.", "preference", "technical", False,
     [("Hubble", "tool"), ("eBPF", "technology")],
     [("Hubble", "eBPF", "USES")],
     "which observability layer does the ops team prefer for network flows and why the single pipeline wins",
     "hubble ebpf flow observability dashboard policy verdict prefer"),
    # --- 32 --- fact
    ("LoadBalancer Services stopped getting external IPs after a speaker election flap on MetalLB, and pinning the speaker to a single node plus tightening the BGP peer timers stabilised it.", "fact", "technical", False,
     [("LoadBalancer", "api"), ("MetalLB", "technology"), ("BGP", "protocol")],
     [("MetalLB", "BGP", "USES")],
     "which MetalLB failure left LoadBalancer Services without external IPs and what two tweaks stabilised it",
     "loadbalancer metallb speaker election bgp peer timer flap pin"),
    # --- 33 --- reference
    ("The Cilium docs split NetworkPolicy into three layers: L3 IP and identity rules, L4 port rules, and L7 HTTP or Kafka rules that require the Envoy proxy path.", "reference", "technical", False,
     [("Cilium", "technology"), ("NetworkPolicy", "api"), ("Envoy", "service"), ("Kafka", "service")],
     [("Cilium", "Envoy", "USES"), ("NetworkPolicy", "Envoy", "DEPENDS_ON")],
     "which three policy layers does the Cilium NetworkPolicy doc define and which one needs Envoy",
     "cilium networkpolicy l3 l4 l7 envoy kafka layer policy doc"),
    # --- 34 --- decision
    ("Chose Project Calico eBPF mode over the standard iptables dataplane because the per-service rule count on the big catalog namespace was blowing out conntrack insert latency.", "decision", "technical", False,
     [("Project Calico", "technology"), ("eBPF", "technology"), ("iptables", "technology"), ("conntrack", "technology"), ("catalog", "project")],
     [("Project Calico", "iptables", "REPLACES"), ("Project Calico", "eBPF", "USES")],
     "what drove the switch away from the iptables dataplane for the busy catalog workload",
     "project calico ebpf iptables conntrack catalog dataplane replace"),
    # --- 35 --- architecture
    ("The east-west mesh is Istio with its mTLS enforced via PeerAuthentication set to STRICT, and any plaintext traffic between Pods fails at the sidecar rather than in the application.", "architecture", "technical", False,
     [("Istio", "framework"), ("mTLS", "protocol"), ("PeerAuthentication", "api"), ("Pods", "api")],
     [("Istio", "PeerAuthentication", "USES"), ("PeerAuthentication", "mTLS", "CONFIGURES")],
     "which Istio object enforces east-west STRICT mTLS so plaintext fails at the sidecar not the app",
     "istio peerauthentication strict mtls east west sidecar plaintext"),
    # --- 36 --- fact
    ("Headless Services set clusterIP to None, which makes the DNS record return A and AAAA entries for every ready Pod instead of a single virtual IP, and clients load-balance on their own.", "fact", "technical", False,
     [("Headless Services", "api"), ("clusterIP", "config"), ("DNS", "protocol"), ("Pod", "api")],
     [("Headless Services", "DNS", "USES")],
     "how does a Headless Service expose individual Pod IPs via DNS instead of a single virtual IP",
     "headless service clusterip none dns a aaaa pod load balance client"),
    # --- 37 --- milestone
    ("Rolled out NodeLocalDNSCache to every node pool, and the shared CoreDNS deployment saw a roughly seventy percent QPS drop because the local cache absorbed the Pod lookup storm.", "milestone", "technical", False,
     [("NodeLocalDNSCache", "service"), ("CoreDNS", "service"), ("Pod", "api")],
     [("NodeLocalDNSCache", "CoreDNS", "IMPROVES_ON")],
     "which rollout pushed CoreDNS QPS down by absorbing the Pod lookup storm on each node",
     "nodelocaldns cache coredns qps drop node pool pod lookup rollout"),
    # --- 38 --- reference
    ("The Kubernetes docs enumerate four Service types, namely ClusterIP, NodePort, LoadBalancer, and ExternalName, and the selector semantics differ for the last one because it is a DNS CNAME.", "reference", "technical", False,
     [("ClusterIP", "api"), ("NodePort", "api"), ("LoadBalancer", "api"), ("ExternalName", "api"), ("CNAME", "protocol")],
     [("ExternalName", "CNAME", "USES")],
     "which four Service types do the Kubernetes docs list and which one is just a DNS CNAME",
     "service type clusterip nodeport loadbalancer externalname cname doc"),
    # --- 39 --- architecture
    ("Gateway API parent-child routing lets one Gateway own many HTTPRoute objects across namespaces via ReferenceGrant, so the platform team keeps the listener while tenants publish their own routes.", "architecture", "technical", False,
     [("Gateway API", "api"), ("Gateway", "api"), ("HTTPRoute", "api"), ("ReferenceGrant", "api")],
     [("HTTPRoute", "Gateway", "DEPENDS_ON"), ("HTTPRoute", "ReferenceGrant", "DEPENDS_ON")],
     "how does Gateway API let tenants attach HTTPRoute objects to a platform-owned Gateway across namespaces",
     "gateway api httproute referencegrant parent child namespace tenant"),
    # --- 40 --- decision
    ("Picked Antrea on the Windows node pool because the Open vSwitch dataplane was the only option that treated the Windows HNS stack as a first-class target rather than a port.", "decision", "technical", False,
     [("Antrea", "technology"), ("Open vSwitch", "technology"), ("Windows", "platform"), ("HNS", "technology")],
     [("Antrea", "Open vSwitch", "USES"), ("Antrea", "HNS", "APPLIES_TO")],
     "what made the Antrea choice on Microsoft nodes land over every other contender",
     "antrea open vswitch windows hns node pool dataplane first class"),
    # --- 41 --- architecture
    ("The Cilium Hubble Relay component aggregates flow data from every node agent into a single gRPC stream, and the Hubble CLI and UI subscribe to that stream instead of scraping each node.", "architecture", "technical", False,
     [("Cilium Hubble Relay", "service"), ("gRPC", "protocol"), ("Hubble", "tool")],
     [("Cilium Hubble Relay", "gRPC", "USES"), ("Cilium Hubble Relay", "Hubble", "HAS_PART")],
     "which Hubble component fans in flow data from every node agent for the CLI and UI to consume",
     "cilium hubble relay grpc flow node agent cli ui aggregate"),
    # --- 42 --- fact
    ("A NodePort Service reserves a port in the 30000 to 32767 range on every node, and kube-proxy programs the forwarding rule so that traffic to that port reaches any ready backend Pod.", "fact", "technical", False,
     [("NodePort", "api"), ("kube-proxy", "service"), ("Pod", "api")],
     [("kube-proxy", "NodePort", "CONFIGURES")],
     "which port range does a NodePort Service grab and which component programs the forwarding rule",
     "nodeport service 30000 32767 kube proxy forward pod port range"),
    # --- 43. noise ---
    ("The office plant in the kitchen has survived four office moves and now has a nameplate because new hires kept asking who the plant belonged to.", "fact", "noise", True, [], [], None, None),
    # --- 44 --- milestone
    ("The submariner multi-cluster fabric went live across three AKS and two EKS clusters in one weekend, and pods across all five started reaching each other over the Globalnet CIDR without duplicate address pain.", "milestone", "technical", False,
     [("submariner", "technology"), ("AKS", "platform"), ("EKS", "platform"), ("Globalnet", "technology")],
     [("submariner", "Globalnet", "USES"), ("submariner", "AKS", "APPLIES_TO"), ("submariner", "EKS", "APPLIES_TO")],
     "which multi-cluster feature bridged AKS and EKS clusters without duplicate pod CIDRs",
     "submariner aks eks globalnet multi cluster pod cidr duplicate"),
    # --- 45 --- decision
    ("For L7 policy the platform team prefers Envoy filters over writing custom sidecars because the upstream filter chain already covers JWT, rate limiting, and WASM extensions.", "decision", "technical", False,
     [("Envoy", "service"), ("JWT", "protocol"), ("WASM", "technology")],
     [("Envoy", "WASM", "USES"), ("Envoy", "JWT", "USES")],
     "which L7 enforcement stack does the platform team pick over custom sidecars and which three features cover policy",
     "envoy filter jwt wasm rate limit l7 policy sidecar platform team"),
    # --- 46 --- decision
    ("Replaced the homegrown cross-cluster load balancer with Cilium ClusterMesh global Services because the internal cluster-aware DNS hack we were running did not survive the DR failover test.", "decision", "technical", False,
     [("Cilium ClusterMesh", "technology"), ("global Services", "api"), ("DR", "concept")],
     [("Cilium ClusterMesh", "global Services", "USES")],
     "which Cilium feature replaced the cluster-aware DNS hack after the DR failover test exposed it",
     "cilium clustermesh global service dr failover dns hack replace"),
    # --- 47 --- problem
    ("Pods in the same namespace could not reach each other across zones during the node turnover because Topology Aware Hints was steering all traffic to a zone that was being drained; relaxing the hint fixed it.", "problem", "technical", False,
     [("Pods", "api"), ("Topology Aware Hints", "api"), ("zone", "infrastructure")],
     [("Topology Aware Hints", "zone", "APPLIES_TO")],
     "which routing feature starved Pods during zone drain and what relaxation restored cross-zone reachability",
     "pod topology aware hint zone drain node turnover cross zone"),
    # --- 48 --- reference
    ("The CNI spec defines ADD, DEL, CHECK, and VERSION as the four verbs a plugin must implement, and the kubelet invokes them with the container network namespace as the first argument.", "reference", "technical", False,
     [("CNI", "protocol"), ("ADD", "command"), ("DEL", "command"), ("CHECK", "command"), ("VERSION", "command"), ("kubelet", "service")],
     [("kubelet", "CNI", "USES")],
     "which four verbs does the CNI spec require from a plugin and which component invokes them",
     "cni spec add del check version kubelet plugin namespace verb"),
    # --- 49 --- reference
    ("The Kubernetes IPVS proxier supports five scheduler algorithms out of the box, specifically rr, lc, dh, sh, and sed, and the choice is a cluster-wide kube-proxy flag rather than a per-Service setting.", "reference", "technical", False,
     [("IPVS", "technology"), ("kube-proxy", "service"), ("rr", "algorithm"), ("lc", "algorithm"), ("sh", "algorithm")],
     [("kube-proxy", "IPVS", "CONFIGURES")],
     "which five IPVS scheduler algorithms does kube-proxy expose and at which scope are they set",
     "ipvs kube proxy scheduler rr lc dh sh sed flag cluster wide"),
    # --- 50 --- preference
    ("Between Cilium ClusterMesh and submariner the platform team prefers Cilium ClusterMesh for clusters that already run Cilium, and reserves submariner for heterogeneous estates with a mixed CNI story.", "preference", "technical", False,
     [("Cilium ClusterMesh", "technology"), ("submariner", "technology"), ("Cilium", "technology"), ("CNI", "protocol")],
     [("Cilium ClusterMesh", "submariner", "PREFERS"), ("Cilium ClusterMesh", "Cilium", "DEPENDS_ON")],
     "when does the platform team pick Cilium ClusterMesh over submariner and when does the reverse hold",
     "cilium clustermesh submariner cni heterogeneous prefer platform"),
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
