"""One-off emitter for shared-base batch-114 — technical domain (virtualization & container runtime internals).

Writes 50 rows to data/v2/shared/batch_114.tmp.jsonl with ids shared-05651..05700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_114.tmp.jsonl"
ID_OFFSET = 5650

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("KVM plus QEMU powered the Linux virtualization host; the kernel module handled the vmx traps while QEMU stayed in userspace for device emulation.", "architecture", "technical", False,
     [("KVM", "technology"), ("QEMU", "tool"), ("Linux", "technology")],
     [("QEMU", "KVM", "BUILDS_ON")],
     "which hypervisor stack handled the Linux host with a userspace device model",
     "kernel module vmx trap userspace device emulation split"),
    # --- 2 ---
    ("KVM replaced Xen on the self-hosted fleet; the paravirtualized console and vhost-net already outpaced Xen's domU boot on the same hardware.", "decision", "technical", False,
     [("KVM", "technology"), ("Xen", "technology"), ("vhost-net", "technology")],
     [("KVM", "Xen", "REPLACES")],
     "which hypervisor displaced Xen on the self-hosted fleet and why",
     "paravirt console boot speed hypervisor swap domU fleet"),
    # --- 3 ---
    ("Proxmox VE was chosen over VMware ESXi for the homelab; the ZFS-on-root installer and free clustering beat the vSphere license hit.", "decision", "technical", False,
     [("Proxmox VE", "platform"), ("VMware ESXi", "platform"), ("ZFS", "technology"), ("vSphere", "platform")],
     [("Proxmox VE", "VMware ESXi", "REPLACES")],
     "which hypervisor platform replaced ESXi on the homelab cluster",
     "ZFS root installer cluster free license hypervisor swap"),
    # --- 4 ---
    ("Incus took over LXD's role after the Canonical fork; the container and VM unification stayed, but the license and governance were cleaner.", "decision", "technical", False,
     [("Incus", "tool"), ("LXD", "tool"), ("Canonical", "organization")],
     [("Incus", "LXD", "REPLACES")],
     "which container manager replaced LXD after the Canonical fork",
     "fork governance license container VM unify manager swap"),
    # --- 5 ---
    ("Firecracker micro-VMs backed the AWS Lambda isolation layer; boot-to-hello dropped under 125 ms by stripping the QEMU device model down to virtio-net and virtio-block.", "architecture", "technical", False,
     [("Firecracker", "technology"), ("AWS Lambda", "service"), ("QEMU", "tool"), ("virtio-net", "technology"), ("virtio-block", "technology")],
     [("Firecracker", "QEMU", "REPLACES")],
     "which micro-VM monitor underpinned the Lambda isolation boundary",
     "micro VM boot strip device model virtio function isolate"),
    # --- 6 ---
    ("Firecracker replaced long-running VMs for the function workload; snapshot-and-restore kept p50 cold start under 200 ms even on the cold pool.", "decision", "technical", False,
     [("Firecracker", "technology")],
     [],
     "which runtime took over long-running VMs for short-lived functions",
     "snapshot restore cold start function pool swap runtime"),
    # --- 7 ---
    ("Kata Containers wrapped the multi-tenant CI jobs in a per-pod VM; the kernel isolation stopped the escape-from-runc class of bugs cold.", "architecture", "technical", False,
     [("Kata Containers", "technology"), ("runc", "tool")],
     [],
     "which sandbox gave the multi-tenant CI per-pod kernel isolation",
     "VM per pod kernel isolate escape runc class bug stop"),
    # --- 8 ---
    ("gVisor was rejected for the CI sandbox; syscall interception on glibc-heavy Go binaries crashed on obscure futex paths twice in testing.", "decision", "technical", False,
     [("gVisor", "technology"), ("glibc", "technology"), ("Go", "language"), ("futex", "technology")],
     [],
     "which user-space kernel was rejected for CI sandboxing and why",
     "syscall intercept futex path obscure crash sandbox reject"),
    # --- 9 ---
    ("containerd replaced dockerd on the Kubernetes 1.24 nodes; the CRI shim was direct, so the docker-shim removal landed without kubelet churn.", "decision", "technical", False,
     [("containerd", "tool"), ("dockerd", "tool"), ("Kubernetes", "framework"), ("CRI", "protocol")],
     [("containerd", "dockerd", "REPLACES")],
     "which runtime took over from dockerd when Kubernetes 1.24 shipped",
     "CRI shim removal node runtime swap kubelet direct"),
    # --- 10. noise ---
    ("Hold on, my VM is still resuming from snapshot.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("CRI-O ran the OpenShift nodes; the systemd-per-pod cgroup model matched the platform's supervision style better than containerd's slice layout.", "architecture", "technical", False,
     [("CRI-O", "tool"), ("OpenShift", "platform"), ("systemd", "technology"), ("containerd", "tool")],
     [],
     "which container runtime served the OpenShift nodes and why",
     "systemd per pod cgroup slice supervision style platform"),
    # --- 12 ---
    ("crun was preferred over runc for the dense-workload nodes; the C implementation cut container start from 80 ms to 12 ms versus the Go runc.", "preference", "technical", False,
     [("crun", "tool"), ("runc", "tool"), ("C", "language"), ("Go", "language")],
     [("crun", "runc", "IMPROVES_ON")],
     "which OCI runtime beat runc on container start time for dense nodes",
     "C implementation start time improve runc Go dense workload"),
    # --- 13 ---
    ("runc stayed on the managed Kubernetes nodes; cloud vendor support for crun was still patchy and the 12 ms win did not justify a divergence.", "decision", "technical", False,
     [("runc", "tool"), ("crun", "tool"), ("Kubernetes", "framework")],
     [],
     "which OCI runtime stayed on managed K8s despite the crun start-time win",
     "vendor support patch diverge managed node runtime keep"),
    # --- 14 ---
    ("cgroups v2 replaced cgroups v1 on the RHEL 9 fleet; the unified hierarchy fixed the memory.max accounting drift that bit the JVM workloads.", "decision", "technical", False,
     [("cgroups v2", "technology"), ("cgroups v1", "technology"), ("RHEL 9", "platform"), ("JVM", "technology")],
     [("cgroups v2", "cgroups v1", "REPLACES")],
     "which cgroup version fixed the JVM memory accounting drift on RHEL 9",
     "unified hierarchy memory max accounting drift JVM fleet"),
    # --- 15 ---
    ("cgroups v2 was required for rootless Podman with memory limits; without the unified controller delegation, non-root users could not cap RSS.", "fact", "technical", False,
     [("cgroups v2", "technology"), ("Podman", "tool")],
     [],
     "which cgroup model rootless Podman needed for memory limits",
     "controller delegation non root RSS cap requirement rootless"),
    # --- 16 ---
    ("User namespaces mapped the rootless container UID 0 to an unprivileged host UID; the /etc/subuid range of 65536 covered the common image needs.", "architecture", "technical", False,
     [("User namespaces", "technology"), ("/etc/subuid", "config")],
     [],
     "which kernel feature mapped rootless UID 0 to an unprivileged host user",
     "namespace UID map subuid range rootless image coverage"),
    # --- 17 ---
    ("Rootless Podman replaced rootful Docker on the developer laptops; the daemonless model and fork-exec-per-container fit the ad-hoc workflow.", "decision", "technical", False,
     [("Rootless Podman", "tool"), ("Docker", "tool")],
     [("Rootless Podman", "Docker", "REPLACES")],
     "which runtime swap landed rootless containers on developer laptops",
     "daemonless fork exec per container ad hoc laptop swap"),
    # --- 18 ---
    ("seccomp profile generation used oci-seccomp-bpf-hook to record the syscall set; the strict profile then cut the attack surface to 74 syscalls from 368.", "milestone", "technical", False,
     [("oci-seccomp-bpf-hook", "tool"), ("seccomp", "technology")],
     [],
     "which tool recorded the syscall set for the strict seccomp profile",
     "BPF hook record syscall strict profile attack surface cut"),
    # --- 19 ---
    ("Default Docker seccomp profile left ptrace blocked; the debug workflow used --cap-add SYS_PTRACE only on the ephemeral dev container.", "fact", "technical", False,
     [("Docker", "tool"), ("ptrace", "technology"), ("SYS_PTRACE", "config")],
     [],
     "which Docker seccomp knob guarded ptrace on ephemeral dev containers",
     "default profile block capability add ephemeral debug flow"),
    # --- 20 ---
    ("Kubernetes CRI was the stable interface between kubelet and the runtime; containerd and CRI-O both implemented it, letting dockerd-shim retirement stay no-op for workloads.", "reference", "technical", False,
     [("Kubernetes CRI", "protocol"), ("kubelet", "tool"), ("containerd", "tool"), ("CRI-O", "tool")],
     [],
     "which Kubernetes interface insulated workloads from the runtime swap",
     "CRI kubelet runtime interface shim retire workload no op"),
    # --- 21 ---
    ("libvirt wrapped the QEMU and KVM management for the Proxmox-less bare-metal boxes; virsh scripts replaced the hand-rolled tmux QEMU launchers.", "decision", "technical", False,
     [("libvirt", "tool"), ("QEMU", "tool"), ("KVM", "technology"), ("virsh", "tool")],
     [("libvirt", "QEMU", "BUILDS_ON")],
     "which management layer replaced the ad-hoc QEMU tmux launchers",
     "libvirt virsh manage bare metal box wrap QEMU launch"),
    # --- 22 ---
    ("virt-manager was kept for the desktop VM workflow; the CLI-only virsh flow stayed on the servers, but snapshot and USB passthrough were faster in the GUI.", "preference", "technical", False,
     [("virt-manager", "tool"), ("virsh", "tool")],
     [],
     "which libvirt client stayed for the desktop VM workflow",
     "GUI snapshot USB passthrough desktop workflow client keep"),
    # --- 23 ---
    ("Hyper-V on Windows Server hosted the Active Directory domain controllers; Generation 2 VMs with Secure Boot matched the enterprise compliance policy.", "architecture", "technical", False,
     [("Hyper-V", "technology"), ("Windows Server", "platform"), ("Active Directory", "service"), ("Secure Boot", "technology")],
     [],
     "which hypervisor hosted the AD domain controllers with Secure Boot",
     "Gen 2 VM secure boot enterprise compliance AD domain host"),
    # --- 24 ---
    ("WSL2 used a lightweight Hyper-V utility VM under the hood; the Linux workloads got KVM-style performance without installing a second hypervisor manually.", "fact", "technical", False,
     [("WSL2", "technology"), ("Hyper-V", "technology"), ("Linux", "technology")],
     [("WSL2", "Hyper-V", "BUILDS_ON")],
     "which Hyper-V primitive powered the WSL2 Linux VM on Windows",
     "utility VM lightweight Linux workload second hypervisor avoid"),
    # --- 25 ---
    ("OCI image spec v1.1 governed the multi-arch manifest index; the manifest list let the arm64 and amd64 pulls share one tag without a client rewrite.", "reference", "technical", False,
     [("OCI image spec", "technology"), ("arm64", "technology"), ("amd64", "technology")],
     [],
     "which spec defined the multi-arch manifest index for shared tags",
     "manifest list multi arch share tag client rewrite avoid"),
    # --- 26 ---
    ("Distroless base images replaced Debian slim for the Go binaries; the attack surface dropped from 180 packages to 4 with no shell and no package manager.", "decision", "technical", False,
     [("Distroless", "technology"), ("Debian slim", "technology"), ("Go", "language")],
     [("Distroless", "Debian slim", "REPLACES")],
     "which base image swap cut the Go container attack surface",
     "no shell no package manager attack surface package count"),
    # --- 27 ---
    ("Chainguard Wolfi images replaced Alpine on the Python services; glibc-based musl-free builds fixed the wheel compatibility issues at scale.", "decision", "technical", False,
     [("Chainguard Wolfi", "technology"), ("Alpine", "technology"), ("Python", "language"), ("glibc", "technology"), ("musl", "technology")],
     [("Chainguard Wolfi", "Alpine", "REPLACES")],
     "which slim base replaced Alpine on the Python image fleet",
     "Wolfi glibc musl wheel compatibility Python base swap"),
    # --- 28 ---
    ("Alpine base stayed on the Go services; the static binary didn't need glibc, and the 6 MB image won on pull time in the edge cache.", "decision", "technical", False,
     [("Alpine", "technology"), ("Go", "language"), ("glibc", "technology")],
     [],
     "which language kept Alpine as the base despite the Wolfi migration",
     "static binary image size pull time edge cache keep"),
    # --- 29 ---
    ("Nix-built container images replaced the Dockerfile stack for the research toolbox; the closure graph gave byte-identical reproducibility across machines.", "decision", "technical", False,
     [("Nix", "tool"), ("Dockerfile", "technology")],
     [("Nix", "Dockerfile", "REPLACES")],
     "which image build replaced the Dockerfile for the research toolbox",
     "closure graph byte identical reproduce machine research tool"),
    # --- 30 ---
    ("buildkit replaced the legacy Docker builder on the CI; concurrent multi-stage steps and remote cache mounts cut the 9-minute build to 2 minutes.", "milestone", "technical", False,
     [("buildkit", "tool"), ("Docker", "tool")],
     [("buildkit", "Docker", "IMPROVES_ON")],
     "which builder replaced the legacy Docker one on CI",
     "concurrent multi stage cache mount build minute cut CI"),
    # --- 31 ---
    ("OCI image spec content-addressed layers allowed cross-image sharing; a Debian base pulled once was reused across 40 tags without a re-download.", "fact", "technical", False,
     [("OCI image spec", "technology"), ("Debian", "technology")],
     [],
     "which OCI spec property let Debian base reuse across 40 tags",
     "content address layer share base reuse tag re download avoid"),
    # --- 32 ---
    ("Podman pods grouped the sidecar containers on the laptop dev; Kubernetes-like pod semantics ran without a control plane and shipped straight to k3s later.", "architecture", "technical", False,
     [("Podman", "tool"), ("Kubernetes", "framework"), ("k3s", "platform")],
     [],
     "which Podman primitive let laptop dev mirror Kubernetes pod semantics",
     "pod group sidecar dev ship k3s control plane avoid"),
    # --- 33 ---
    ("containerd-only nodes replaced the dockerd plus containerd pair on the Kubernetes fleet; removing the extra daemon cut memory by 180 MB per node.", "decision", "technical", False,
     [("containerd", "tool"), ("dockerd", "tool"), ("Kubernetes", "framework")],
     [("containerd", "dockerd", "REPLACES")],
     "which fleet change trimmed 180 MB per node by removing a daemon",
     "single daemon memory per node trim extra remove runtime"),
    # --- 34. noise ---
    ("Could you pass the external SSD? The VM image lives there.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("virtio-fs replaced 9p-over-virtio for the Kata Containers host share; the FUSE-backed path handled POSIX flock semantics that 9p dropped.", "decision", "technical", False,
     [("virtio-fs", "technology"), ("9p", "protocol"), ("Kata Containers", "technology"), ("FUSE", "technology")],
     [("virtio-fs", "9p", "REPLACES")],
     "which filesystem protocol took over host sharing for Kata",
     "virtio fs 9p host share POSIX flock sematic Kata swap"),
    # --- 36 ---
    ("OverlayFS powered the copy-on-write layer stack for containerd; the fuse-overlayfs fallback only kicked in for rootless nodes on older kernels.", "architecture", "technical", False,
     [("OverlayFS", "technology"), ("containerd", "tool"), ("fuse-overlayfs", "technology")],
     [],
     "which filesystem powered the containerd copy-on-write layer stack",
     "overlay FS COW layer fallback rootless older kernel node"),
    # --- 37 ---
    ("Firecracker jailer sandboxed the VMM process with chroot, namespaces, and seccomp; the defence-in-depth kept a VMM CVE from reaching the host.", "architecture", "technical", False,
     [("Firecracker", "technology"), ("jailer", "tool"), ("seccomp", "technology")],
     [],
     "which Firecracker helper sandboxed the VMM process for defence in depth",
     "jailer chroot namespace seccomp VMM CVE host reach block"),
    # --- 38 ---
    ("Cloud Hypervisor was evaluated alongside Firecracker; the richer device set fit the general-purpose VM shape, but the function workload stayed on Firecracker.", "decision", "technical", False,
     [("Cloud Hypervisor", "technology"), ("Firecracker", "technology")],
     [],
     "which micro-VM was evaluated alongside Firecracker for general VMs",
     "cloud hypervisor general purpose device set function stay"),
    # --- 39 ---
    ("Xen still ran the legacy AWS EC2 fleet; the Nitro migration carried most volume off Xen onto KVM-based hardware over 2019 to 2023.", "fact", "technical", False,
     [("Xen", "technology"), ("AWS EC2", "service"), ("Nitro", "technology"), ("KVM", "technology")],
     [("Nitro", "Xen", "REPLACES")],
     "which AWS fleet migration moved volume from Xen onto KVM hardware",
     "legacy Xen fleet Nitro migration KVM hardware year range"),
    # --- 40 ---
    ("Proxmox VE ran LXC containers alongside KVM guests on the same node; the /etc/pve/lxc configs stayed next to the qemu-server configs without clash.", "architecture", "technical", False,
     [("Proxmox VE", "platform"), ("LXC", "technology"), ("KVM", "technology"), ("/etc/pve/lxc", "config")],
     [],
     "which Proxmox layout kept LXC and KVM side by side on one node",
     "LXC KVM node share config directory co exist Proxmox"),
    # --- 41 ---
    ("The OCI runtime spec was the common contract across runc, crun, and youki; the JSON config and rootfs layout let the runtime binary swap with no image rebuild.", "reference", "technical", False,
     [("OCI runtime spec", "technology"), ("runc", "tool"), ("crun", "tool"), ("youki", "tool")],
     [],
     "which spec let runc, crun, and youki swap with no image rebuild",
     "OCI runtime spec JSON config rootfs swap binary no rebuild"),
    # --- 42 ---
    ("youki was trialed as a Rust runtime alternative to runc; container create latency matched crun but the ecosystem support still lagged.", "problem", "technical", False,
     [("youki", "tool"), ("runc", "tool"), ("crun", "tool"), ("Rust", "language")],
     [],
     "which Rust OCI runtime was trialed against runc and crun",
     "Rust runtime latency match ecosystem support lag trial"),
    # --- 43 ---
    ("Docker Desktop on macOS used a LinuxKit VM under Apple Virtualization Framework; the switch from HyperKit trimmed CPU use in idle by about 30 percent.", "milestone", "technical", False,
     [("Docker Desktop", "tool"), ("macOS", "platform"), ("LinuxKit", "technology"), ("Apple Virtualization Framework", "technology"), ("HyperKit", "tool")],
     [("Apple Virtualization Framework", "HyperKit", "REPLACES")],
     "which macOS virtualization framework displaced HyperKit under Docker Desktop",
     "Apple framework LinuxKit VM idle CPU trim HyperKit swap"),
    # --- 44 ---
    ("Colima replaced Docker Desktop on the Mac dev laptops; the Lima-backed VM and containerd nerdctl flow dropped the licensing cost per seat.", "decision", "technical", False,
     [("Colima", "tool"), ("Docker Desktop", "tool"), ("Lima", "tool"), ("containerd", "tool"), ("nerdctl", "tool")],
     [("Colima", "Docker Desktop", "REPLACES")],
     "which tool replaced Docker Desktop on the Mac dev laptops",
     "Lima VM containerd nerdctl license seat cost Mac laptop"),
    # --- 45 ---
    ("Image signing shifted to cosign keyless with Fulcio and Rekor; the OIDC identity path removed the long-lived private key in the release pipeline.", "decision", "technical", False,
     [("cosign", "tool"), ("Fulcio", "service"), ("Rekor", "service"), ("OIDC", "protocol")],
     [("cosign", "OIDC", "BUILDS_ON")],
     "which signing flow replaced the long-lived private key in release",
     "keyless cosign Fulcio Rekor OIDC identity private key remove"),
    # --- 46 ---
    ("Dockerfile multi-stage builds trimmed the final image by dropping the build toolchain; the final stage copied only the static binary and a CA bundle.", "architecture", "technical", False,
     [("Dockerfile", "technology")],
     [],
     "which Dockerfile pattern trimmed final images by dropping build tools",
     "multi stage build toolchain drop static binary CA bundle"),
    # --- 47 ---
    ("Image pull-through cache on Harbor absorbed the Docker Hub rate-limit hit; the upstream pulls per node dropped from 400 per day to 12.", "problem", "technical", False,
     [("Harbor", "tool"), ("Docker Hub", "service")],
     [],
     "which registry layer absorbed the Docker Hub rate-limit pressure",
     "pull through cache upstream node count rate limit drop"),
    # --- 48 ---
    ("Podman quadlets replaced the systemd generator script for container units; the .container files landed natively in /etc/containers/systemd with unit semantics.", "decision", "technical", False,
     [("Podman", "tool"), ("quadlets", "technology"), ("systemd", "technology")],
     [("quadlets", "systemd", "IMPROVES_ON")],
     "which Podman feature replaced the custom systemd generator script",
     "quadlet container unit systemd native drop hand script"),
    # --- 49 ---
    ("User namespace remapping on Docker daemon was enabled for the shared CI hosts; container root mapped to host UID 100000 so any escape landed on an unprivileged user.", "architecture", "technical", False,
     [("User namespace", "technology"), ("Docker", "tool"), ("CI", "concept")],
     [],
     "which Docker daemon setting protected shared CI hosts from root escape",
     "userns remap daemon shared host UID escape land unpriv"),
    # --- 50 ---
    ("Kata Containers 3.0 with Dragonball landed on the workload on 2026-02-17; the Rust-based micro-VM cut per-pod memory overhead by 40 MB versus the QEMU backend.", "milestone", "technical", False,
     [("Kata Containers", "technology"), ("Dragonball", "technology"), ("QEMU", "tool"), ("Rust", "language"), ("2026-02-17", "date")],
     [("Dragonball", "QEMU", "IMPROVES_ON")],
     "when did Kata 3.0 land with Dragonball and what overhead did it cut",
     "Kata Dragonball Rust micro VM pod memory overhead date"),
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
