"""One-off emitter for shared-base batch-193 — technical domain (virtualization and hypervisors: Proxmox VE, QEMU/KVM, libvirt, Xen, ESXi, Hyper-V, LXC/LXD, Incus, Firecracker, VFIO, virtio, NUMA, UEFI, snapshots).

Writes 50 rows to data/v2/shared/batch_193.tmp.jsonl with ids shared-09601..09650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_193.tmp.jsonl"
ID_OFFSET = 9600

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Consolidated the lab's three standalone ESXi boxes onto a single Proxmox VE 8.2 cluster; the shared Ceph pool lets any node take over a VM in under ten seconds during maintenance.", "milestone", "technical", False,
     [("ESXi", "service"), ("Proxmox VE", "service"), ("Ceph", "database"), ("8.2", "config")],
     [("Proxmox VE", "ESXi", "REPLACES"), ("Proxmox VE", "Ceph", "USES")],
     "which hypervisor stack replaced standalone ESXi nodes and how are VM failovers handled in the cluster",
     "proxmox esxi ceph cluster failover shared pool migrate"),
    # --- 2 ---
    ("Picked QEMU with KVM acceleration over plain QEMU TCG for the CI runners; the nested test suites run about seventeen times faster once the host's virtualization extensions are actually used.", "decision", "technical", False,
     [("QEMU", "tool"), ("KVM", "framework"), ("TCG", "pattern"), ("CI runners", "service")],
     [("KVM", "TCG", "REPLACES"), ("QEMU", "KVM", "USES")],
     "which acceleration backend replaced TCG under QEMU for CI workloads and what speedup did it unlock",
     "qemu kvm tcg accel ci runner nested virtualization speedup"),
    # --- 3 ---
    ("Libvirt now drives every dev-box VM on the workstation; writing raw qemu-system command lines got replaced because the XML domain definitions survive host reinstalls via a single virsh dumpxml backup.", "decision", "technical", False,
     [("Libvirt", "tool"), ("qemu-system", "tool"), ("virsh", "tool"), ("XML domain", "pattern")],
     [("Libvirt", "qemu-system", "REPLACES"), ("virsh", "Libvirt", "USES")],
     "which management stack replaced raw qemu-system invocations on the workstation and what backup path did it enable",
     "libvirt virsh qemu xml domain dumpxml backup workstation vm"),
    # --- 4 ---
    ("virt-manager is the daily driver for GUI VM tweaks on the Rocky Linux 9 host; the CLI virsh edit path stays in-muscle for scripted changes but the GUI wins for live device hot-plug.", "preference", "technical", False,
     [("virt-manager", "tool"), ("virsh", "tool"), ("Rocky Linux", "service"), ("9", "config")],
     [("virt-manager", "virsh", "PREFERS")],
     "which graphical tool sits on top of libvirt for day-to-day VM edits on the Rocky Linux host",
     "virt manager virsh rocky linux gui hot plug device edit"),
    # --- 5 ---
    ("XCP-ng 8.3 replaced the aging Xen Server lab pool; the open-source fork kept the storage XAPI semantics intact so existing VHDs imported without a conversion step.", "milestone", "technical", False,
     [("XCP-ng", "service"), ("Xen Server", "service"), ("8.3", "config"), ("XAPI", "api"), ("VHD", "file")],
     [("XCP-ng", "Xen Server", "REPLACES"), ("XCP-ng", "XAPI", "USES")],
     "which Xen distribution replaced the aging Xen Server pool and how did existing disks migrate over",
     "xcp ng xen server xapi vhd import migrate fork lab pool"),
    # --- 6 ---
    ("VMware ESXi 8.0U3 is pinned for the customer-facing production cluster; the hypervisor still holds the best vendor support matrix for the NetApp storage and Cisco UCS blades we can't replace this year.", "decision", "technical", False,
     [("VMware ESXi", "service"), ("8.0U3", "config"), ("NetApp", "service"), ("Cisco UCS", "service")],
     [("VMware ESXi", "NetApp", "APPLIES_TO"), ("VMware ESXi", "Cisco UCS", "APPLIES_TO")],
     "why did the customer-facing cluster keep ESXi 8.0U3 rather than moving to an open-source hypervisor",
     "vmware esxi 8 netapp cisco ucs support vendor production"),
    # --- 7 ---
    ("Hyper-V on Windows Server 2025 runs the AD domain controllers in a failover cluster; the Live Migration over SMB Direct saturates the 25 GbE fabric cleanly without CPU overhead from compression.", "architecture", "technical", False,
     [("Hyper-V", "service"), ("Windows Server 2025", "service"), ("Live Migration", "pattern"), ("SMB Direct", "protocol"), ("25 GbE", "config")],
     [("Hyper-V", "Live Migration", "USES"), ("Live Migration", "SMB Direct", "USES")],
     "which Hyper-V migration mechanism drives lossless AD failover across the 25 GbE fabric",
     "hyper v windows server 2025 live migration smb direct ad cluster"),
    # --- 8 ---
    ("VirtualBox 7.1 still wins on the instructor laptops because it ships a guest additions installer that works across thirty student-owned Windows and Ubuntu images without a per-machine kernel rebuild.", "preference", "technical", False,
     [("VirtualBox", "tool"), ("7.1", "config"), ("guest additions", "pattern"), ("Windows", "service"), ("Ubuntu", "service")],
     [("VirtualBox", "guest additions", "USES")],
     "which desktop hypervisor stayed on instructor laptops and what cross-OS feature kept it there",
     "virtualbox 7 guest additions instructor laptop cross os image"),
    # --- 9 ---
    ("UTM on the M3 MacBook runs ARM64 Linux guests under Apple's Virtualization.framework with near-native throughput; the x86 QEMU-emulation path exists but drops to a tenth of the speed for CI.", "fact", "technical", False,
     [("UTM", "tool"), ("M3 MacBook", "platform"), ("Virtualization.framework", "framework"), ("QEMU", "tool"), ("ARM64", "platform")],
     [("UTM", "Virtualization.framework", "USES")],
     "which Apple Silicon hypervisor path does UTM take for native ARM64 Linux guests versus x86 emulation",
     "utm m3 macbook virtualization framework arm64 x86 qemu emulation"),
    # --- 10 ---
    ("Parallels Desktop 20 is the preferred Windows-on-Apple-Silicon host for the design team; CrossOver and UTM both trailed on DirectX 12 game compatibility in the evaluation last quarter.", "decision", "technical", False,
     [("Parallels Desktop", "tool"), ("20", "config"), ("Apple-Silicon", "platform"), ("CrossOver", "tool"), ("UTM", "tool"), ("DirectX 12", "framework")],
     [("Parallels Desktop", "CrossOver", "PREFERS"), ("Parallels Desktop", "UTM", "PREFERS")],
     "which Windows-on-Apple-Silicon hypervisor did the design team pick and which rivals did it beat",
     "parallels desktop 20 apple silicon crossover utm directx 12 compat"),
    # --- 11 ---
    ("AlmaLinux 9.4 became the standard KVM host OS across the hypervisor fleet; the CentOS Stream path got abandoned after the vendor-supported kernel cadence stopped aligning with our backport SLA.", "decision", "technical", False,
     [("AlmaLinux", "service"), ("9.4", "config"), ("KVM", "framework"), ("CentOS Stream", "service")],
     [("AlmaLinux", "CentOS Stream", "REPLACES"), ("AlmaLinux", "KVM", "APPLIES_TO")],
     "which RHEL-compatible host OS replaced CentOS Stream across the KVM hypervisor fleet",
     "almalinux centos stream kvm host fleet kernel backport rhel"),
    # --- 12 ---
    ("Nutanix AHV runs the hyperconverged pod in the remote DR site; the built-in Prism control plane removed the separate vCenter license line item entirely after the ESXi lift-and-shift.", "milestone", "technical", False,
     [("Nutanix AHV", "service"), ("Prism", "tool"), ("vCenter", "service"), ("ESXi", "service"), ("DR site", "service")],
     [("Nutanix AHV", "ESXi", "REPLACES"), ("Prism", "vCenter", "REPLACES")],
     "which hyperconverged stack took over the DR site and which VMware component did it retire",
     "nutanix ahv prism vcenter esxi dr hyperconverged lift shift"),
    # --- 13 ---
    ("oVirt 4.5 still drives the academic research cluster because the GlusterFS storage domain lets the grad students rebuild nodes without touching the SAN fabric.", "fact", "technical", False,
     [("oVirt", "service"), ("4.5", "config"), ("GlusterFS", "database"), ("storage domain", "pattern")],
     [("oVirt", "GlusterFS", "USES")],
     "which oVirt feature keeps the research cluster self-service for grad students touching compute nodes",
     "ovirt 4 5 glusterfs storage domain academic research cluster"),
    # --- 14 ---
    ("LXC containers run the lightweight workloads that don't need a full kernel; the privileged-container path got retired entirely because the user-namespace mapping closed the escape surface that bit us in 2024.", "decision", "technical", False,
     [("LXC", "framework"), ("privileged-container", "pattern"), ("user-namespace", "pattern")],
     [("user-namespace", "privileged-container", "REPLACES")],
     "which LXC security pattern replaced privileged containers after the 2024 escape incident",
     "lxc privileged container user namespace escape security lightweight"),
    # --- 15 ---
    ("LXD 5.21 LTS serves the internal build cluster; the REST API and cluster mode let CI pipelines create ephemeral containers at three-per-second peak without tripping the host's cgroup limits.", "fact", "technical", False,
     [("LXD", "service"), ("5.21 LTS", "config"), ("REST API", "protocol"), ("cluster mode", "pattern"), ("cgroup", "pattern")],
     [("LXD", "REST API", "USES")],
     "which LXD features keep the CI build cluster responsive under three-per-second ephemeral container churn",
     "lxd 5 21 rest api cluster mode cgroup ci ephemeral build"),
    # --- 16 ---
    ("Migrated the LXD installation to Incus after Canonical forked the licensing posture; the config export path round-trips cleanly and the storage pools attached in place without a reimport.", "milestone", "technical", False,
     [("Incus", "service"), ("LXD", "service"), ("Canonical", "service"), ("storage pools", "pattern")],
     [("Incus", "LXD", "REPLACES")],
     "which LXC-family project replaced LXD on our hosts after the Canonical licensing change",
     "incus lxd canonical fork license storage pool config export"),
    # --- 17 ---
    ("systemd-nspawn handles the single-binary service sandboxes on the edge gateway; the footprint is smaller than a full LXC container and the --ephemeral flag torches state on exit without bespoke teardown scripts.", "architecture", "technical", False,
     [("systemd-nspawn", "tool"), ("LXC", "framework"), ("--ephemeral", "config"), ("edge gateway", "service")],
     [("systemd-nspawn", "LXC", "PREFERS")],
     "which sandbox runtime handles single-binary services on the edge gateway and why was it picked over LXC",
     "systemd nspawn lxc ephemeral edge gateway sandbox single binary"),
    # --- 18 ---
    ("Firecracker powers the Function-as-a-Service layer; boot time lands under one hundred and twenty-five milliseconds cold, which made the generic QEMU path no longer a serious contender for request-scoped VMs.", "decision", "technical", False,
     [("Firecracker", "service"), ("Function-as-a-Service", "pattern"), ("QEMU", "tool")],
     [("Firecracker", "QEMU", "REPLACES")],
     "which microVM runtime drives FaaS cold boots and what QEMU-class rival did it displace",
     "firecracker faas cold boot microvm qemu request scoped function"),
    # --- 19 ---
    ("Cloud-Hypervisor runs the multi-tenant GPU worker boxes; the Rust codebase and vhost-user-blk stack gave us an easier audit story than the sprawling QEMU device model.", "decision", "technical", False,
     [("Cloud-Hypervisor", "service"), ("Rust", "language"), ("vhost-user-blk", "protocol"), ("QEMU", "tool")],
     [("Cloud-Hypervisor", "QEMU", "PREFERS")],
     "which Rust-based hypervisor replaced QEMU on the multi-tenant GPU workers and why",
     "cloud hypervisor rust vhost user blk qemu gpu worker multi tenant"),
    # --- 20 ---
    ("crosvm runs the ChromeOS Linux guest via the vm_concierge service; picking it over QEMU kept the security-team-owned fuzzing corpus directly applicable to production traffic.", "fact", "technical", False,
     [("crosvm", "tool"), ("ChromeOS", "service"), ("vm_concierge", "service"), ("QEMU", "tool")],
     [("crosvm", "QEMU", "PREFERS")],
     "which hypervisor backs the ChromeOS Linux guest and what security alignment justified the pick over QEMU",
     "crosvm chromeos vm concierge qemu fuzz security corpus"),
    # --- 21 ---
    ("ZFS root on the Proxmox hosts enabled snapshot-before-upgrade rollbacks; two kernel regressions this year were recovered by a single zfs rollback rpool/ROOT@preupgrade within the maintenance window.", "architecture", "technical", False,
     [("ZFS", "database"), ("Proxmox", "service"), ("snapshot", "pattern"), ("zfs rollback", "command"), ("rpool/ROOT", "config")],
     [("ZFS", "snapshot", "USES")],
     "how do the Proxmox hosts recover from a kernel regression during an upgrade window",
     "zfs root proxmox snapshot rollback kernel upgrade regression"),
    # --- 22 ---
    ("BTRFS subvolumes host the libvirt images on the dev box; qcow2 copy-on-write got disabled with chattr +C on the subvolume because the double-CoW made VM disk latency spike under heavy churn.", "problem", "technical", False,
     [("BTRFS", "database"), ("libvirt", "tool"), ("qcow2", "file"), ("chattr +C", "command"), ("subvolume", "pattern")],
     [("BTRFS", "qcow2", "APPLIES_TO")],
     "which BTRFS setting tamed the double-copy-on-write latency for qcow2 disks on the dev subvolume",
     "btrfs subvolume qcow2 chattr nocow double cow latency libvirt"),
    # --- 23 ---
    ("VFIO PCI passthrough gives the transcoder VM direct access to the NVIDIA RTX 4070; the host's amdgpu driver surrendered the card via vfio-pci ids set in /etc/modprobe.d/vfio.conf on boot.", "architecture", "technical", False,
     [("VFIO", "framework"), ("NVIDIA RTX 4070", "service"), ("vfio-pci", "tool"), ("amdgpu", "tool"), ("/etc/modprobe.d/vfio.conf", "file")],
     [("VFIO", "vfio-pci", "USES")],
     "how does the transcoder VM claim the RTX 4070 from the host at boot using VFIO",
     "vfio pci passthrough rtx 4070 amdgpu modprobe vfio conf transcoder"),
    # --- 24 ---
    ("SR-IOV on the Mellanox ConnectX-6 splits the 100 GbE port into sixteen virtual functions; each Proxmox guest attaches a VF directly and skips the host's linux bridge entirely for line-rate networking.", "architecture", "technical", False,
     [("SR-IOV", "framework"), ("Mellanox ConnectX-6", "service"), ("100 GbE", "config"), ("virtual functions", "pattern"), ("Proxmox", "service")],
     [("SR-IOV", "virtual functions", "USES"), ("Proxmox", "SR-IOV", "USES")],
     "which NIC offload pattern gives Proxmox guests line-rate 100 GbE without going through the host bridge",
     "sr iov mellanox connectx 100 gbe virtual function proxmox bridge"),
    # --- 25 ---
    ("virtio-blk replaced the emulated IDE controller across the VM fleet; random-read IOPS jumped from around four thousand to over ninety thousand on the same NVMe-backed host dataset.", "fact", "technical", False,
     [("virtio-blk", "framework"), ("IDE controller", "pattern"), ("NVMe", "service"), ("IOPS", "concept")],
     [("virtio-blk", "IDE controller", "REPLACES")],
     "which virtio driver replaced emulated IDE across the fleet and what IOPS jump did it produce",
     "virtio blk ide controller nvme iops random read fleet replace"),
    # --- 26 ---
    ("NUMA pinning for the OLTP VM binds vCPUs to socket 0 and pre-allocates memory from node 0 via numactl --membind=0 qemu-system-x86_64; cross-socket remote-memory stalls dropped the p99 query latency by a third.", "reference", "technical", False,
     [("NUMA pinning", "pattern"), ("numactl", "tool"), ("--membind=0", "config"), ("qemu-system-x86_64", "tool"), ("OLTP", "service")],
     [("numactl", "qemu-system-x86_64", "USES")],
     "which NUMA configuration cut the OLTP VM's p99 latency by pinning CPU and memory to one socket",
     "numa pin numactl membind qemu x86 oltp socket p99 latency"),
    # --- 27 ---
    ("CPU pinning on the real-time audio guest uses cset shield and isolcpus=8-15 in the host's kernel cmdline; jitter under load measured consistently below eighty microseconds on the pinned cores.", "architecture", "technical", False,
     [("CPU pinning", "pattern"), ("cset shield", "command"), ("isolcpus", "config"), ("kernel cmdline", "pattern"), ("real-time audio", "service")],
     [("cset shield", "isolcpus", "USES")],
     "which host-side pinning stack keeps the real-time audio guest under eighty-microsecond jitter",
     "cpu pin cset shield isolcpus kernel cmdline real time audio jitter"),
    # --- 28 ---
    ("Memory ballooning via virtio-balloon was disabled on the Postgres VMs after the workingset-shrink path evicted hot pages during backup windows; every DB guest now gets static RAM pre-allocated.", "problem", "technical", False,
     [("virtio-balloon", "framework"), ("Postgres", "database"), ("workingset-shrink", "pattern"), ("static RAM", "config")],
     [("static RAM", "virtio-balloon", "REPLACES")],
     "which ballooning behaviour forced us to pre-allocate static RAM for the Postgres guests",
     "virtio balloon postgres workingset shrink backup static ram"),
    # --- 29 ---
    ("TPM emulation via swtpm attaches a software vTPM 2.0 to each Windows 11 guest; the BitLocker recovery keys are escrowed in the host's libvirt secrets so a migrated VM still boots unlocked.", "architecture", "technical", False,
     [("swtpm", "tool"), ("vTPM 2.0", "framework"), ("Windows 11", "service"), ("BitLocker", "framework"), ("libvirt secrets", "pattern")],
     [("swtpm", "vTPM 2.0", "USES"), ("BitLocker", "swtpm", "APPLIES_TO")],
     "which TPM emulation path keeps BitLocker-sealed Windows 11 guests bootable after a live migration",
     "swtpm vtpm 2 windows 11 bitlocker libvirt secret migrate boot"),
    # --- 30 ---
    ("UEFI OVMF boot replaced SeaBIOS on every new VM spec; Secure Boot gets enrolled with the Microsoft UEFI CA by default and the legacy-BIOS path only survives for two ancient Windows Server 2008 guests.", "decision", "technical", False,
     [("OVMF", "framework"), ("SeaBIOS", "framework"), ("Secure Boot", "pattern"), ("Microsoft UEFI CA", "service"), ("Windows Server 2008", "service")],
     [("OVMF", "SeaBIOS", "REPLACES"), ("OVMF", "Secure Boot", "USES")],
     "which firmware replaced SeaBIOS for new VMs and which Secure Boot CA gets enrolled by default",
     "ovmf seabios uefi secure boot microsoft ca windows 2008"),
    # --- 31 ---
    ("Proxmox VE snapshot semantics differ between LVM-thin and ZFS storage: LVM-thin snapshots are linear and expire with the chain, while ZFS snapshots are independent and rollback-friendly across branches.", "reference", "technical", False,
     [("Proxmox VE", "service"), ("LVM-thin", "database"), ("ZFS", "database")],
     [("Proxmox VE", "LVM-thin", "USES"), ("Proxmox VE", "ZFS", "USES")],
     "how do snapshot semantics differ between LVM-thin and ZFS storage backends on Proxmox",
     "proxmox snapshot lvm thin zfs chain rollback branch storage"),
    # --- 32 ---
    ("KVM nested virtualization flag is enabled via kvm-intel.nested=1 on the build farm hosts so Vagrant-in-VM workflows can spin inner KVM guests; the AMD-V counterpart sets kvm-amd.nested=1 the same way.", "reference", "technical", False,
     [("KVM", "framework"), ("kvm-intel.nested", "config"), ("kvm-amd.nested", "config"), ("Vagrant", "tool"), ("AMD-V", "framework")],
     [],
     "which modprobe parameters turn on nested KVM on Intel and AMD host CPUs for Vagrant-in-VM flows",
     "kvm nested intel amd kvm intel kvm amd vagrant build farm flag"),
    # --- 33 ---
    ("Live migration on Proxmox uses secure QEMU migration over the dedicated 10 GbE backbone VLAN; the insecure plain-TCP mode got disabled in datacenter.cfg after a pen-test flagged memory pages traversing in the clear.", "decision", "technical", False,
     [("Live migration", "pattern"), ("Proxmox", "service"), ("QEMU", "tool"), ("datacenter.cfg", "file"), ("10 GbE", "config")],
     [("QEMU", "Live migration", "USES")],
     "which migration security mode did we enforce on Proxmox after the pen-test flagged in-clear memory pages",
     "live migration proxmox qemu secure plain tcp datacenter cfg pen test"),
    # --- 34 ---
    ("ESXi storage vMotion between the NetApp AFF and the new Pure Storage FlashArray relied on VAAI XCOPY offload; a single-pass TB move wrapped in forty minutes instead of the six hours the host-copy path projected.", "milestone", "technical", False,
     [("ESXi", "service"), ("NetApp AFF", "service"), ("Pure Storage FlashArray", "service"), ("VAAI", "framework"), ("XCOPY", "command")],
     [("ESXi", "VAAI", "USES"), ("VAAI", "XCOPY", "USES")],
     "which VAAI primitive compressed the storage vMotion window from NetApp to Pure from six hours to forty minutes",
     "esxi storage vmotion netapp pure flasharray vaai xcopy offload"),
    # --- 35 ---
    ("QEMU qcow2 disk images default to cluster_size=64k on fresh creation but the high-IO Postgres guests switched to cluster_size=2M; the larger cluster cut metadata overhead and halved write amplification during WAL flushes.", "decision", "technical", False,
     [("qcow2", "file"), ("QEMU", "tool"), ("cluster_size", "config"), ("Postgres", "database"), ("WAL", "concept")],
     [("qcow2", "Postgres", "APPLIES_TO")],
     "which qcow2 cluster_size tweak halved Postgres write amplification during WAL flushes",
     "qcow2 cluster size qemu postgres wal write amplification metadata"),
    # --- 36 ---
    ("Hyper-V Dynamic Memory stayed disabled on the SQL Server 2022 guests; the Windows Server team confirmed hot-add memory doesn't retroactively rebalance the buffer pool, so static 128 GB is the default.", "preference", "technical", False,
     [("Hyper-V Dynamic Memory", "framework"), ("SQL Server 2022", "database"), ("buffer pool", "pattern"), ("128 GB", "config")],
     [("Hyper-V Dynamic Memory", "SQL Server 2022", "APPLIES_TO")],
     "why did the SQL Server 2022 guests stay on static 128 GB rather than Hyper-V Dynamic Memory",
     "hyper v dynamic memory sql server 2022 buffer pool static hot add"),
    # --- 37 ---
    ("Proxmox backup uses PBS 3.3 with dirty-bitmap incremental snapshots; full runs shrank from six hours to twenty minutes once the VM guests carried persistent bitmaps across daily cycles.", "milestone", "technical", False,
     [("PBS", "service"), ("3.3", "config"), ("dirty-bitmap", "pattern"), ("Proxmox", "service")],
     [("PBS", "dirty-bitmap", "USES")],
     "which PBS feature shrank the daily Proxmox backup window from six hours to twenty minutes",
     "proxmox backup pbs 3 3 dirty bitmap incremental snapshot daily"),
    # --- 38 ---
    ("virtiofsd replaced 9pfs for host-to-guest directory sharing on the build VMs; ninepfs caching bugs kept handing out stale dentries on Gradle watch rebuilds during heavy concurrent writes.", "problem", "technical", False,
     [("virtiofsd", "tool"), ("9pfs", "framework"), ("Gradle", "tool"), ("dentries", "pattern")],
     [("virtiofsd", "9pfs", "REPLACES")],
     "which shared-filesystem replaced 9pfs for host-to-guest mounts after Gradle watch hit stale dentry issues",
     "virtiofsd 9pfs gradle dentry stale cache build host guest"),
    # --- 39 ---
    ("The ESXi pool runs vSphere 8 with vSAN ESA on NVMe; the legacy vSAN OSA format got migrated in place over a weekend because the claim-rules-by-capacity-tier path auto-tagged the drives.", "milestone", "technical", False,
     [("ESXi", "service"), ("vSphere 8", "service"), ("vSAN ESA", "framework"), ("vSAN OSA", "framework"), ("NVMe", "service")],
     [("vSAN ESA", "vSAN OSA", "REPLACES"), ("vSphere 8", "vSAN ESA", "USES")],
     "which vSAN storage architecture replaced OSA on the vSphere 8 pool and how did the migration auto-tag disks",
     "vsphere 8 vsan esa osa nvme claim rule capacity tier migrate"),
    # --- 40 ---
    ("Xen HVM guests on XCP-ng run with viridian=true to expose Hyper-V enlightenments; Windows 11 guests notice the paravirt clock and skip the TSC calibration loop that used to pin a core at boot.", "fact", "technical", False,
     [("Xen HVM", "framework"), ("XCP-ng", "service"), ("viridian", "config"), ("Hyper-V enlightenments", "pattern"), ("Windows 11", "service"), ("TSC", "concept")],
     [("XCP-ng", "viridian", "USES")],
     "which XCP-ng guest flag hands Windows 11 Hyper-V enlightenments and skips TSC calibration at boot",
     "xen hvm xcp ng viridian hyper v enlightenment windows 11 tsc"),
    # --- 41 ---
    ("Picked QEMU blk-mq with four queues per virtio-blk disk on the high-IOPS NVMe guests; single-queue mode serialised the block layer and capped the workload a long way under hardware ceiling.", "decision", "technical", False,
     [("QEMU", "tool"), ("blk-mq", "framework"), ("virtio-blk", "framework"), ("NVMe", "service")],
     [("blk-mq", "virtio-blk", "APPLIES_TO")],
     "which QEMU block-layer mode unblocked the high-IOPS NVMe guests that single-queue mode capped",
     "qemu blk mq virtio blk nvme queue iops block layer serialise"),
    # --- 42 ---
    ("KSM page-merging ran on the dev host and saved about thirty percent of RAM; it's turned off on the production OLTP host because the scanner's CPU cost showed up in query p99 latency during peak traffic.", "fact", "technical", False,
     [("KSM", "framework"), ("OLTP", "service"), ("page-merging", "pattern")],
     [("KSM", "page-merging", "USES")],
     "where is KSM page-merging kept enabled versus disabled and why does the OLTP host opt out",
     "ksm page merging dev oltp cpu p99 latency ram save scanner"),
    # --- 43 ---
    ("Cloud-init drives Proxmox VM provisioning from a single ci-user.yaml template; the legacy guest-agent exec path was too host-dependent and kept drifting when the OS template changed between Debian and Ubuntu releases.", "architecture", "technical", False,
     [("Cloud-init", "tool"), ("Proxmox", "service"), ("ci-user.yaml", "file"), ("Debian", "service"), ("Ubuntu", "service")],
     [("Cloud-init", "Proxmox", "APPLIES_TO")],
     "which provisioning path drives Proxmox VM first boot and what brittle mechanism did it replace",
     "cloud init proxmox ci user yaml debian ubuntu provision first boot"),
    # --- 44 ---
    ("The break room's bean-to-cup coffee machine grinds between six and eight in the morning and between one and two in the afternoon; a little sticky note lists who refills the beans this week.", "fact", "noise", True, [], [], None, None),
    # --- 45 ---
    ("Hyper-V Shielded VMs with vTPM and Host Guardian Service protect the finance guests; an unauthenticated host refuses to boot the encrypted VHDX even if the file is copied out of the cluster storage.", "architecture", "technical", False,
     [("Hyper-V", "service"), ("Shielded VMs", "framework"), ("vTPM", "framework"), ("Host Guardian Service", "service"), ("VHDX", "file")],
     [("Shielded VMs", "Host Guardian Service", "USES"), ("Shielded VMs", "vTPM", "USES")],
     "how do Shielded VMs prevent an unauthenticated host from booting a copied finance VHDX",
     "hyper v shielded vm vtpm host guardian vhdx finance encrypt"),
    # --- 46 ---
    ("Proxmox VE 8 replication via pvesr runs every fifteen minutes for critical ZFS datasets; the async replication window means the DR node starts up to fifteen minutes stale but an RPO of that size was agreed.", "reference", "technical", False,
     [("Proxmox VE", "service"), ("8", "config"), ("pvesr", "tool"), ("ZFS", "database"), ("RPO", "concept")],
     [("pvesr", "ZFS", "USES")],
     "which Proxmox tool schedules ZFS replication and what RPO does the fifteen-minute cadence imply",
     "proxmox pvesr zfs replication fifteen minute rpo dr async"),
    # --- 47 ---
    ("QEMU -cpu host exposes the physical CPU model to guests on same-family clusters; the production pool had to drop back to -cpu Skylake-Server-v4 once a single Cascade-Lake node joined the migration group.", "preference", "technical", False,
     [("QEMU", "tool"), ("-cpu host", "config"), ("-cpu Skylake-Server-v4", "config"), ("Cascade-Lake", "platform")],
     [("-cpu Skylake-Server-v4", "-cpu host", "REPLACES")],
     "which QEMU CPU-model downgrade was forced when a Cascade-Lake node joined the previously uniform pool",
     "qemu cpu host skylake server cascade lake migration model cluster"),
    # --- 48 ---
    ("Incus migration from LXD preserved the cluster token trust by reusing the existing certificate store; every node was rejoined with incus cluster edit rather than a cold reinit.", "reference", "technical", False,
     [("Incus", "service"), ("LXD", "service"), ("cluster token", "pattern"), ("incus cluster edit", "command")],
     [("Incus", "LXD", "REPLACES")],
     "which Incus command lets the LXD-to-Incus migration keep the cluster's existing certificate trust",
     "incus lxd cluster edit certificate token trust migrate rejoin"),
    # --- 49 ---
    ("Firecracker's jailer wraps each microVM in a cgroup v2 slice and a seccomp filter per guest; the seccomp deny list is generated from the kernel-command-line profile at jailer startup.", "reference", "technical", False,
     [("Firecracker", "service"), ("jailer", "tool"), ("cgroup v2", "pattern"), ("seccomp", "framework")],
     [("jailer", "cgroup v2", "USES"), ("jailer", "seccomp", "USES")],
     "which Firecracker component applies the cgroup v2 slice and seccomp filter per microVM",
     "firecracker jailer cgroup v2 seccomp filter microvm kernel"),
    # --- 50 ---
    ("After the Friday lunch pizza run an intern left two mushroom slices on the reception coffee table and someone drew an angry arrow at them with a dry-erase marker.", "fact", "noise", True, [], [], None, None),
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
