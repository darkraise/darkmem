"""One-off emitter for shared-base batch-143 — container runtimes (Docker/Podman/containerd/OCI).

Writes 50 rows to data/v2/shared/batch_143.tmp.jsonl with ids shared-07101..07150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_143.tmp.jsonl"
ID_OFFSET = 7100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped Docker for Podman on the CI runners; rootless pods and the daemonless architecture closed the privileged-socket audit finding that blocked compliance sign-off.", "decision", "technical", False,
     [("Docker", "platform"), ("Podman", "platform"), ("CI runners", "infrastructure")],
     [("Podman", "Docker", "REPLACES"), ("Podman", "CI runners", "DEPLOYED_ON")],
     "which container engine replaced Docker on CI and what audit finding drove the switch",
     "podman docker ci runner rootless daemonless audit privileged socket"),
    # --- 2 ---
    ("containerd is the runtime beneath our Kubernetes nodes; dockershim was ripped out on the 1.24 upgrade and the CRI plugin talks directly to the kubelet.", "architecture", "technical", False,
     [("containerd", "platform"), ("Kubernetes", "platform"), ("dockershim", "technology"), ("CRI", "protocol"), ("kubelet", "service")],
     [("containerd", "dockershim", "REPLACES"), ("containerd", "CRI", "IMPLEMENTS"), ("kubelet", "containerd", "COMMUNICATES_WITH")],
     "which container runtime sits under our Kubernetes nodes after the 1.24 upgrade removed dockershim",
     "containerd kubernetes cri kubelet dockershim 1.24 runtime plugin"),
    # --- 3 ---
    ("Migrated the fleet from runc to crun for the OpenShift clusters; startup latency dropped about forty percent on short-lived job pods because the C implementation has no Go runtime to boot.", "milestone", "technical", False,
     [("runc", "platform"), ("crun", "platform"), ("OpenShift", "platform")],
     [("crun", "runc", "REPLACES"), ("crun", "OpenShift", "DEPLOYED_ON")],
     "which low-level OCI runtime replaced runc on OpenShift and what startup win did it unlock",
     "crun runc openshift oci runtime startup latency short lived job"),
    # --- 4 ---
    ("BuildKit replaced the legacy Docker builder for multi-arch images; parallel stage execution and the inline cache exporter cut a 12-minute CI build down to around 4 minutes.", "decision", "technical", False,
     [("BuildKit", "tool"), ("Docker builder", "tool"), ("multi-arch images", "concept"), ("inline cache", "concept")],
     [("BuildKit", "Docker builder", "REPLACES"), ("BuildKit", "multi-arch images", "SUPPORTS")],
     "which builder replaced the legacy Docker one for multi-arch builds and what cache feature mattered",
     "buildkit docker builder multi arch parallel stage inline cache ci"),
    # --- 5 ---
    ("Image layers are content-addressed by sha256 digest; pushing a rebuilt layer whose contents match an existing one is a no-op because the registry already stores that blob.", "fact", "technical", False,
     [("Image layers", "concept"), ("sha256", "algorithm"), ("registry", "infrastructure")],
     [("Image layers", "sha256", "USES")],
     "why does pushing a rebuilt but identical layer end up as a no-op against the registry",
     "image layer sha256 digest content address registry blob dedup"),
    # --- 6 ---
    ("Standardised on the OCI image-spec v1.1 across all internal registries; the old Docker v2 schema 1 manifests got rejected at push time after the cutover date.", "decision", "technical", False,
     [("OCI image-spec v1.1", "protocol"), ("Docker v2 schema 1", "protocol"), ("internal registries", "infrastructure")],
     [("OCI image-spec v1.1", "Docker v2 schema 1", "REPLACES"), ("internal registries", "OCI image-spec v1.1", "IMPLEMENTS")],
     "which image manifest spec is now mandatory on our registries and what did it retire",
     "oci image spec v1.1 docker v2 schema manifest registry cutover"),
    # --- 7 ---
    ("Rootless Podman on the dev workstations maps the user into a subuid range; the /etc/subuid and /etc/subgid files have to be populated or newuidmap fails with error 125.", "problem", "technical", False,
     [("Rootless Podman", "platform"), ("subuid", "config"), ("/etc/subuid", "file"), ("/etc/subgid", "file"), ("newuidmap", "command")],
     [("Rootless Podman", "subuid", "DEPENDS_ON"), ("newuidmap", "/etc/subuid", "USES")],
     "which subuid files must be populated for rootless Podman to avoid the newuidmap error",
     "rootless podman subuid subgid newuidmap error 125 user namespace"),
    # --- 8 ---
    ("cgroups v2 is the only supported controller hierarchy on the new nodes; hybrid mode got disabled in kernel params because systemd-245 and containerd 1.7 both prefer the unified tree.", "architecture", "technical", False,
     [("cgroups v2", "technology"), ("hybrid mode", "config"), ("systemd-245", "service"), ("containerd 1.7", "platform")],
     [("containerd 1.7", "cgroups v2", "USES"), ("systemd-245", "cgroups v2", "PREFERS")],
     "which cgroup hierarchy is mandated on new nodes and which two components dictated the move",
     "cgroups v2 unified hybrid systemd containerd kernel param controller"),
    # --- 9 ---
    ("User namespaces remap container root to an unprivileged host uid via the userns-remap daemon flag; a stray bind-mount from /var/lib/docker broke because chown expected the mapped range.", "problem", "technical", False,
     [("User namespaces", "technology"), ("userns-remap", "config"), ("/var/lib/docker", "file"), ("chown", "command")],
     [("userns-remap", "User namespaces", "CONFIGURES")],
     "which daemon flag enables user namespace remapping and what bind-mount pitfall surfaced",
     "user namespace userns remap uid bind mount var lib docker chown"),
    # --- 10. noise ---
    ("The front-desk plant finally outgrew its pot and the new ceramic planter clashes with the lobby's paint job.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Docker Compose v2 is the plugin form invoked as 'docker compose'; the hyphenated docker-compose script was removed from the Dockerfile base image for developer machines.", "decision", "technical", False,
     [("Docker Compose v2", "tool"), ("docker compose", "command"), ("docker-compose", "command"), ("Dockerfile", "file")],
     [("Docker Compose v2", "docker-compose", "REPLACES")],
     "which Compose invocation did we standardise on and which old script got dropped from the base image",
     "docker compose v2 plugin hyphenated script base image developer"),
    # --- 12 ---
    ("Skopeo syncs images between Harbor and the air-gapped Quay mirror; --all is required to carry every platform manifest of a multi-arch image across the link.", "reference", "technical", False,
     [("Skopeo", "tool"), ("Harbor", "service"), ("Quay", "service"), ("--all", "config")],
     [("Skopeo", "Harbor", "COMMUNICATES_WITH"), ("Skopeo", "Quay", "COMMUNICATES_WITH")],
     "which flag does the Harbor-to-Quay skopeo sync need so multi-arch manifests survive the copy",
     "skopeo harbor quay air gap mirror all flag multi arch manifest"),
    # --- 13 ---
    ("Buildah handles rootless image builds in the pipeline without a daemon; the buildah-unshare wrapper drops us into a user namespace where mknod and chown succeed on the overlay upperdir.", "architecture", "technical", False,
     [("Buildah", "tool"), ("buildah-unshare", "command"), ("user namespace", "technology"), ("overlay", "technology")],
     [("Buildah", "user namespace", "USES"), ("buildah-unshare", "Buildah", "CONFIGURES")],
     "which Buildah wrapper puts the build into a user namespace so mknod and chown work rootless",
     "buildah unshare rootless user namespace overlay mknod chown upper"),
    # --- 14 ---
    ("CRI-O is the runtime on the bare-metal Kubernetes clusters; its tight OCI-spec scope and the small binary surface make the security team happier than the sprawling dockerd ever did.", "decision", "technical", False,
     [("CRI-O", "platform"), ("Kubernetes", "platform"), ("OCI-spec", "protocol"), ("dockerd", "service")],
     [("CRI-O", "dockerd", "REPLACES"), ("CRI-O", "OCI-spec", "IMPLEMENTS"), ("CRI-O", "Kubernetes", "DEPLOYED_ON")],
     "which runtime runs on bare-metal Kubernetes and what about dockerd did the security review flag",
     "cri-o bare metal kubernetes oci spec dockerd security surface"),
    # --- 15 ---
    ("Adopted multi-stage Dockerfile builds for every Go service; the final stage copies a single static binary into a distroless base, knocking production image sizes under 30 MB.", "decision", "technical", False,
     [("multi-stage", "pattern"), ("Dockerfile", "file"), ("Go", "language"), ("distroless", "platform")],
     [("multi-stage", "Dockerfile", "APPLIES_TO"), ("Go", "distroless", "DEPLOYED_ON")],
     "which Dockerfile pattern and base image combination pushed our Go image sizes under 30 MB",
     "multi stage dockerfile go distroless static binary image size"),
    # --- 16 ---
    ("Image-layer cache invalidation bit us again: reordering COPY lines above a rarely-changing RUN apt-get install invalidated five gigabytes of downstream cache on every build.", "problem", "technical", False,
     [("COPY", "command"), ("RUN", "command"), ("apt-get install", "command")],
     [],
     "which Dockerfile instruction order caused the five-gig cache bust and how should the lines have been sequenced",
     "copy run apt get cache invalidation dockerfile order layer"),
    # --- 17 ---
    ("The registry uses Docker Registry v2 API over TLS with token auth; pulls issue a GET to /v2/<name>/manifests/<ref> and then fan out to /v2/<name>/blobs/<digest> for every layer.", "reference", "technical", False,
     [("Docker Registry v2 API", "protocol"), ("TLS", "protocol"), ("/v2/<name>/manifests/<ref>", "api"), ("/v2/<name>/blobs/<digest>", "api")],
     [("Docker Registry v2 API", "TLS", "USES")],
     "which two registry endpoints does a pull hit to fetch a manifest and then its layer blobs",
     "docker registry v2 api tls token manifest blob endpoint pull"),
    # --- 18 ---
    ("Pinned the base image by digest not tag in every Dockerfile; a floating :latest on the node-alpine parent silently pulled a minor bump that broke npm's peer-dep resolver overnight.", "decision", "technical", False,
     [("Dockerfile", "file"), ("node-alpine", "technology"), ("digest", "concept"), ("npm", "tool")],
     [("Dockerfile", "digest", "USES")],
     "why did we switch base-image references from floating tags to immutable digests",
     "base image digest pin tag latest node alpine npm peer dep"),
    # --- 19 ---
    ("ENTRYPOINT plus CMD is the canonical pattern for our service images; ENTRYPOINT pins the binary so 'docker run image --flag' passes flags through instead of overriding the command.", "reference", "technical", False,
     [("ENTRYPOINT", "command"), ("CMD", "command"), ("docker run", "command")],
     [],
     "how does combining ENTRYPOINT and CMD let docker run pass flags through instead of replacing the command",
     "entrypoint cmd dockerfile pattern docker run flag override pass"),
    # --- 20 ---
    ("Bind mounts on macOS hit the osxfs translation layer and throttle IO; we switched every dev volume to a named volume plus a one-shot rsync sidecar for source sync.", "problem", "technical", False,
     [("Bind mounts", "pattern"), ("osxfs", "technology"), ("named volume", "pattern"), ("rsync", "tool")],
     [("named volume", "Bind mounts", "REPLACES")],
     "which mount strategy replaced macOS bind mounts after osxfs killed IO in the dev stack",
     "bind mount osxfs macos named volume rsync sidecar io throttle"),
    # --- 21 ---
    ("Networking mode for the edge gateway is host; the overlay and bridge modes both added a userspace hop that spiked p99 latency above our 15 ms SLO during peak traffic.", "decision", "technical", False,
     [("host", "config"), ("overlay", "technology"), ("bridge", "technology"), ("edge gateway", "service")],
     [("edge gateway", "host", "USES")],
     "which Docker networking mode does the edge gateway use and what SLO pushed us away from overlay or bridge",
     "host network overlay bridge edge gateway p99 latency slo 15ms"),
    # --- 22 ---
    ("The docker0 bridge was replaced by a custom CNI plugin on Kubernetes nodes; Calico's BGP mode peers with the top-of-rack switch for pod-to-pod routing without NAT.", "architecture", "technical", False,
     [("docker0", "technology"), ("CNI", "protocol"), ("Calico", "platform"), ("BGP", "protocol"), ("top-of-rack switch", "infrastructure")],
     [("Calico", "docker0", "REPLACES"), ("Calico", "CNI", "IMPLEMENTS"), ("Calico", "BGP", "USES")],
     "which CNI plugin took over from docker0 and which routing protocol peers with the rack switch",
     "calico cni bgp docker0 top of rack pod network nat routing"),
    # --- 23 ---
    ("Image signing enforces cosign verification at admission; an unsigned image or a signature against the wrong Fulcio identity gets blocked by the Kyverno policy before pod scheduling.", "architecture", "technical", False,
     [("cosign", "tool"), ("Fulcio", "service"), ("Kyverno", "tool"), ("admission", "concept")],
     [("Kyverno", "cosign", "USES"), ("cosign", "Fulcio", "COMMUNICATES_WITH")],
     "which admission policy blocks unsigned images and which signing tool underpins the check",
     "cosign fulcio kyverno admission image signing verify unsigned block"),
    # --- 24 ---
    ("The Dockerfile uses a non-root USER directive and a read-only rootfs; any write goes to a tmpfs mount on /tmp, which caught three secrets that used to leak into /var/log.", "architecture", "technical", False,
     [("Dockerfile", "file"), ("USER", "command"), ("read-only rootfs", "pattern"), ("tmpfs", "technology"), ("/tmp", "file"), ("/var/log", "file")],
     [("Dockerfile", "USER", "USES")],
     "which two hardening directives reshape the container filesystem and what incident did they prevent",
     "user directive read only rootfs tmpfs tmp var log secret leak"),
    # --- 25 ---
    ("Introduced docker buildx as the default CLI for cross-platform builds on 2024-09-01; the QEMU binfmt emulation handles arm64 from our amd64 runners without a remote builder yet.", "milestone", "technical", False,
     [("docker buildx", "tool"), ("QEMU", "tool"), ("binfmt", "technology"), ("arm64", "platform"), ("amd64", "platform"), ("2024-09-01", "date")],
     [("docker buildx", "QEMU", "USES"), ("QEMU", "binfmt", "USES")],
     "which buildx and QEMU combination lets the amd64 runners produce arm64 images without a remote builder",
     "docker buildx qemu binfmt arm64 amd64 cross platform 2024 remote"),
    # --- 26 ---
    ("Harbor replaced our self-hosted Docker Distribution registry; the replication policies and the Trivy-backed vuln scan integration closed two tickets that Distribution had no answer for.", "decision", "technical", False,
     [("Harbor", "service"), ("Docker Distribution", "service"), ("Trivy", "tool"), ("replication policies", "concept")],
     [("Harbor", "Docker Distribution", "REPLACES"), ("Harbor", "Trivy", "USES")],
     "which registry replaced Docker Distribution and what two features sealed the decision",
     "harbor docker distribution registry trivy replication vuln scan"),
    # --- 27 ---
    ("Pod restart policy for the worker DaemonSet is OnFailure with a 5m backoff cap; CrashLoopBackOff used to wedge nodes during a bad rollout before we pinned the cap.", "decision", "technical", False,
     [("OnFailure", "config"), ("DaemonSet", "concept"), ("CrashLoopBackOff", "error"), ("backoff cap", "config")],
     [],
     "which restart policy and backoff setting on the worker DaemonSet stopped CrashLoopBackOff from wedging nodes",
     "onfailure daemonset crashloopbackoff backoff cap 5m restart policy"),
    # --- 28 ---
    ("Health-check lifecycle hooks live in the Dockerfile HEALTHCHECK instruction; Kubernetes ignores them and prefers its own livenessProbe and readinessProbe, so we mirror the logic in the manifest.", "reference", "technical", False,
     [("HEALTHCHECK", "command"), ("livenessProbe", "config"), ("readinessProbe", "config"), ("Kubernetes", "platform")],
     [("Kubernetes", "HEALTHCHECK", "REPLACES")],
     "why does Kubernetes ignore the HEALTHCHECK instruction and what two probes does it use instead",
     "healthcheck liveness readiness probe kubernetes dockerfile mirror"),
    # --- 29 ---
    ("Image pull secret rotation is automated via the external-secrets operator; the kubelet picks up the new imagePullSecret on the next pod start without a daemonset restart.", "architecture", "technical", False,
     [("external-secrets operator", "tool"), ("kubelet", "service"), ("imagePullSecret", "config")],
     [("external-secrets operator", "imagePullSecret", "CONFIGURES"), ("kubelet", "imagePullSecret", "USES")],
     "which operator rotates imagePullSecrets so the kubelet picks up new credentials without a daemonset bounce",
     "external secrets operator kubelet image pull secret rotate rotation"),
    # --- 30 ---
    ("OverlayFS is the storage driver everywhere; devicemapper and aufs got purged in a node-image rebuild because copy-up cost on first-write dominated our image-heavy workloads.", "milestone", "technical", False,
     [("OverlayFS", "technology"), ("devicemapper", "technology"), ("aufs", "technology"), ("copy-up", "concept")],
     [("OverlayFS", "devicemapper", "REPLACES"), ("OverlayFS", "aufs", "REPLACES")],
     "which container storage driver replaced both devicemapper and aufs in the node-image rebuild",
     "overlayfs devicemapper aufs storage driver copy up image workload"),
    # --- 31 ---
    ("Secrets never land in image layers: docker build --secret mounts them at build time via the BuildKit secret frontend, and the mount leaves no trace in the final manifest.", "architecture", "technical", False,
     [("docker build --secret", "command"), ("BuildKit", "tool"), ("image layers", "concept")],
     [("docker build --secret", "BuildKit", "USES")],
     "which build-time mechanism keeps secrets out of image layers without touching the final manifest",
     "docker build secret buildkit frontend mount image layer manifest"),
    # --- 32 ---
    ("Ephemeral init containers set sysctls via runtime-class privilege; unprivileged pods can't twist net.core.somaxconn, so the init hop owns the kernel-knob changes and exits.", "architecture", "technical", False,
     [("init containers", "concept"), ("runtime-class", "config"), ("net.core.somaxconn", "config"), ("sysctls", "technology")],
     [("init containers", "sysctls", "CONFIGURES")],
     "how do unprivileged pods set restricted sysctls like net.core.somaxconn without granting the whole pod privilege",
     "init container runtime class sysctl somaxconn privileged unprivileged"),
    # --- 33 ---
    ("gVisor runs the untrusted tenant workloads; the runsc runtime intercepts syscalls in userspace so a kernel CVE in the host doesn't cross the sandbox boundary as easily as runc would.", "architecture", "technical", False,
     [("gVisor", "platform"), ("runsc", "platform"), ("runc", "platform")],
     [("gVisor", "runc", "REPLACES"), ("gVisor", "runsc", "USES")],
     "which sandboxed runtime hosts untrusted tenants and why does it beat runc for kernel-CVE containment",
     "gvisor runsc runc untrusted tenant syscall userspace sandbox cve"),
    # --- 34 ---
    ("Kata Containers provide VM-isolated pods for the PCI-regulated namespace; each pod gets a lightweight firecracker VM instead of a shared kernel with the rest of the node.", "architecture", "technical", False,
     [("Kata Containers", "platform"), ("firecracker", "platform"), ("PCI-regulated namespace", "concept")],
     [("Kata Containers", "firecracker", "USES")],
     "which VM-isolated runtime hosts the PCI-regulated namespace and what hypervisor drives its pod boundary",
     "kata containers firecracker pci regulated vm isolation kernel pod"),
    # --- 35 ---
    ("Container logs ship through the containerd CRI log path to a Fluent Bit daemonset; stdout lines land in JSON files under /var/log/containers and get tailed with a 10 MB rotation.", "architecture", "technical", False,
     [("containerd", "platform"), ("Fluent Bit", "tool"), ("/var/log/containers", "file"), ("CRI log path", "concept")],
     [("Fluent Bit", "/var/log/containers", "USES"), ("containerd", "CRI log path", "IMPLEMENTS")],
     "which log path and shipper pair carries container stdout into the cluster logging plane",
     "containerd cri log fluent bit var log containers rotation stdout"),
    # --- 36 ---
    ("nerdctl is the preferred CLI on the containerd-only nodes; it speaks native containerd namespaces so 'nerdctl -n k8s.io ps' surfaces the kubelet-managed pods without ctr.", "preference", "technical", False,
     [("nerdctl", "tool"), ("containerd", "platform"), ("ctr", "tool"), ("k8s.io", "config")],
     [("nerdctl", "containerd", "USES"), ("nerdctl", "ctr", "PREFERS")],
     "which CLI do we prefer on containerd-only nodes for listing kubelet-managed pods",
     "nerdctl containerd ctr k8s.io namespace ps kubelet pod cli"),
    # --- 37 ---
    ("Prefer distroless over alpine for production images; musl segfaults in one of our ORM drivers kept surfacing under load, and the attack surface on a minimal base is smaller anyway.", "preference", "technical", False,
     [("distroless", "platform"), ("alpine", "platform"), ("musl", "library"), ("ORM", "library")],
     [("distroless", "alpine", "PREFERS")],
     "which base image do we prefer for prod and which ORM-under-musl symptom drove the choice",
     "distroless alpine musl orm segfault base image attack surface"),
    # --- 38 ---
    ("The Dockerfile best-practice guide pins every apt-get install line with --no-install-recommends and a version; unbounded installs added 400 MB and a CVE that the SCA scanner flagged within a week.", "reference", "technical", False,
     [("Dockerfile", "file"), ("apt-get install", "command"), ("--no-install-recommends", "config"), ("SCA scanner", "tool")],
     [],
     "which apt-get flag is mandatory in our Dockerfile guide and what downstream problem did unbounded installs cause",
     "apt get no install recommends dockerfile cve sca scanner version"),
    # --- 39 ---
    ("We prefer docker compose profiles over separate compose.override files; profiles keep one canonical compose.yaml and flip dev vs ci vs staging service sets with --profile on the command line.", "preference", "technical", False,
     [("docker compose profiles", "tool"), ("compose.override", "file"), ("compose.yaml", "file"), ("--profile", "config")],
     [("docker compose profiles", "compose.override", "PREFERS")],
     "which Compose feature did we standardise on for dev vs ci vs staging over override files",
     "docker compose profile override compose yaml dev ci staging"),
    # --- 40 ---
    ("Volume driver for the stateful sets is the CSI driver from rook-ceph; local-path provisioner survives only for ephemeral scratch space on the CI worker pool.", "architecture", "technical", False,
     [("CSI driver", "protocol"), ("rook-ceph", "platform"), ("local-path provisioner", "tool"), ("CI worker pool", "infrastructure")],
     [("rook-ceph", "CSI driver", "IMPLEMENTS")],
     "which storage driver backs stateful sets and where does local-path provisioner still fit",
     "csi rook ceph local path provisioner stateful set ci worker"),
    # --- 41 ---
    ("Pod security standards at Restricted baseline: no hostPath, no privileged, no hostNetwork, and seccomp profile RuntimeDefault on every container in the namespace.", "reference", "technical", False,
     [("Pod security standards", "concept"), ("hostPath", "config"), ("hostNetwork", "config"), ("seccomp", "technology"), ("RuntimeDefault", "config")],
     [("Pod security standards", "seccomp", "CONFIGURES")],
     "which four constraints define the Restricted pod security baseline we apply namespace-wide",
     "pod security standards restricted hostpath privileged hostnetwork seccomp"),
    # --- 42 ---
    ("Registry garbage collection runs weekly after manifest-list pruning; untagged blobs older than seven days get swept, which reclaims roughly 140 GB per cycle on the main Harbor instance.", "fact", "technical", False,
     [("garbage collection", "concept"), ("manifest-list", "concept"), ("Harbor", "service")],
     [("Harbor", "garbage collection", "USES")],
     "how often does our Harbor registry run garbage collection and roughly how much does it reclaim",
     "registry garbage collection harbor manifest list untagged blob prune"),
    # --- 43. noise ---
     ("The office espresso machine finally got descaled and the Wednesday mocha queue is back under ten minutes for the first time all quarter.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("CRI runtime classes let us pin sensitive workloads to gVisor and everything else to runc; the RuntimeClass handler on the pod spec picks the right runtime at admission.", "architecture", "technical", False,
     [("CRI runtime classes", "concept"), ("gVisor", "platform"), ("runc", "platform"), ("RuntimeClass", "config")],
     [("CRI runtime classes", "RuntimeClass", "IMPLEMENTS")],
     "how do we route sensitive workloads to gVisor while keeping runc for the rest at admission",
     "cri runtime class gvisor runc pod spec admission handler sensitive"),
    # --- 45 ---
    ("OCI image layout on disk keeps the blobs/sha256 directory flat and a single index.json at the root; skopeo and oras both read this layout without any daemon running.", "reference", "technical", False,
     [("OCI image layout", "concept"), ("blobs/sha256", "file"), ("index.json", "file"), ("skopeo", "tool"), ("oras", "tool")],
     [("skopeo", "OCI image layout", "USES"), ("oras", "OCI image layout", "USES")],
     "which two files define the on-disk OCI image layout and which daemonless tools can read it",
     "oci image layout blobs sha256 index json skopeo oras daemonless"),
    # --- 46 ---
    ("Removed the privileged: true flag from the monitoring agent DaemonSet; CAP_SYS_ADMIN plus host PID namespace access was enough for the ebpf probe and the audit finding cleared.", "problem", "technical", False,
     [("privileged: true", "config"), ("CAP_SYS_ADMIN", "config"), ("host PID namespace", "concept"), ("ebpf", "technology"), ("DaemonSet", "concept")],
     [("CAP_SYS_ADMIN", "privileged: true", "REPLACES")],
     "which capability swap replaced privileged:true on the monitoring DaemonSet while keeping the ebpf probe working",
     "privileged cap sys admin host pid ebpf daemonset monitoring audit"),
    # --- 47 ---
    ("The staging cluster's first pod ran on 2023-11-12 under CRI-O 1.28; that date is still the baseline we compare regression numbers against for pod-start p50 latency.", "milestone", "technical", False,
     [("staging cluster", "infrastructure"), ("CRI-O 1.28", "platform"), ("2023-11-12", "date")],
     [("staging cluster", "CRI-O 1.28", "USES"), ("staging cluster", "2023-11-12", "HAPPENED_ON")],
     "which date and runtime version anchor our pod-start regression baseline on the staging cluster",
     "staging cluster cri-o 1.28 2023 11 12 pod start baseline regression"),
    # --- 48 ---
    ("The ocp-4.14 upgrade swapped the default network plugin from OpenShift SDN to OVN-Kubernetes; egress IP policies now get programmed into OVN flows instead of iptables rules on each node.", "milestone", "technical", False,
     [("ocp-4.14", "platform"), ("OpenShift SDN", "technology"), ("OVN-Kubernetes", "technology"), ("iptables", "tool"), ("egress IP", "concept")],
     [("OVN-Kubernetes", "OpenShift SDN", "REPLACES"), ("OVN-Kubernetes", "iptables", "REPLACES")],
     "which CNI swap landed with ocp-4.14 and how did egress IP programming change as a result",
     "ocp 4.14 openshift sdn ovn kubernetes iptables egress ip flow"),
    # --- 49 ---
    ("Image pull performance on cold nodes improved after enabling containerd's zstd:chunked support; lazy-pull streams individual chunks so the first byte of the container's main process fires before the layer finishes.", "milestone", "technical", False,
     [("containerd", "platform"), ("zstd:chunked", "technology"), ("lazy-pull", "concept")],
     [("containerd", "zstd:chunked", "USES")],
     "which containerd image feature let cold-node pulls start a container before the layer finished downloading",
     "containerd zstd chunked lazy pull cold node image layer stream"),
    # --- 50 ---
    ("The baseline Dockerfile template ships with ARG BASE_DIGEST and a HEALTHCHECK on /healthz; service teams inherit it via FROM the internal golang-base image and don't re-declare either.", "fact", "technical", False,
     [("Dockerfile", "file"), ("ARG BASE_DIGEST", "command"), ("HEALTHCHECK", "command"), ("/healthz", "api"), ("golang-base", "platform"), ("FROM", "command")],
     [("Dockerfile", "golang-base", "USES")],
     "which two Dockerfile directives does our golang-base template ship so service teams inherit them via FROM",
     "dockerfile arg base digest healthcheck healthz golang base from template"),
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
