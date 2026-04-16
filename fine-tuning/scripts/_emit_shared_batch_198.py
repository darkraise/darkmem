"""One-off emitter for shared-base batch-198 — technical domain (network-attached storage and distributed filesystems: TrueNAS, Synology, ZFS, Ceph, MinIO, NFS, SMB, iSCSI, RAID vs RAIDZ).

Writes 50 rows to data/v2/shared/batch_198.tmp.jsonl with ids shared-09851..09900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_198.tmp.jsonl"
ID_OFFSET = 9850

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the home pool from TrueNAS Core to TrueNAS Scale so the same ZFS datasets can be shared over NFSv4.2 while Kubernetes workloads land on the same box without a second appliance.", "decision", "technical", False,
     [("TrueNAS Core", "platform"), ("TrueNAS Scale", "platform"), ("ZFS", "technology"), ("NFSv4.2", "protocol"), ("Kubernetes", "technology")],
     [("TrueNAS Scale", "TrueNAS Core", "REPLACES"), ("TrueNAS Scale", "ZFS", "USES")],
     "which TrueNAS variant replaced Core on the home pool and what dual workload did it unify",
     "truenas scale core zfs nfs kubernetes migrate appliance unify"),
    # --- 2 ---
    ("Chose OpenZFS on Linux over Btrfs for the backup array; Btrfs RAID5 write-hole warnings in the upstream wiki finally pushed the call after a scrub found silent corruption on the old volume.", "decision", "technical", False,
     [("OpenZFS on Linux", "technology"), ("Btrfs", "technology"), ("RAID5", "concept"), ("scrub", "pattern")],
     [("OpenZFS on Linux", "Btrfs", "REPLACES")],
     "why did the backup array swap Btrfs for OpenZFS after a scrub anomaly",
     "openzfs btrfs raid5 write hole scrub silent corruption backup"),
    # --- 3 ---
    ("The storage cluster runs Ceph with three MON, five OSD hosts, and CephFS mounted by the workstations; RBD backs the VM disks and RGW fronts an S3 endpoint for the CI artifact cache.", "architecture", "technical", False,
     [("Ceph", "technology"), ("MON", "infrastructure"), ("OSD", "infrastructure"), ("CephFS", "technology"), ("RBD", "technology"), ("RGW", "infrastructure"), ("S3", "protocol"), ("CI", "service")],
     [("Ceph", "CephFS", "USES"), ("Ceph", "RBD", "USES"), ("RGW", "S3", "IMPLEMENTS"), ("RGW", "CI", "APPLIES_TO")],
     "how does the Ceph cluster serve file, block, and object workloads from one deployment",
     "ceph mon osd cephfs rbd rgw s3 cluster vm artifact"),
    # --- 4 ---
    ("Set an L2ARC NVMe cache device on the media pool after the ARC-hit ratio dropped below 40 percent once the library crossed 12 TB; warm-read latency halved within a week.", "problem", "technical", False,
     [("L2ARC", "infrastructure"), ("NVMe", "technology"), ("ARC", "infrastructure"), ("media pool", "project")],
     [("L2ARC", "media pool", "APPLIES_TO"), ("L2ARC", "ARC", "EXTENDS")],
     "what cache layer fixed the low ARC hit rate on the media pool after it outgrew RAM",
     "l2arc arc nvme cache media pool hit ratio warm read"),
    # --- 5 ---
    ("Added a mirrored Optane SLOG so synchronous NFS writes from the ESXi cluster stopped committing to spinning rust; sync=always datasets dropped their latency from 18 ms to sub-millisecond.", "milestone", "technical", False,
     [("Optane", "technology"), ("SLOG", "infrastructure"), ("NFS", "protocol"), ("ESXi", "platform"), ("sync=always", "config")],
     [("SLOG", "NFS", "APPLIES_TO"), ("Optane", "SLOG", "IMPLEMENTS")],
     "which ZIL hardware change cut synchronous NFS write latency for the ESXi cluster",
     "slog optane zil nfs esxi sync write latency mirror"),
    # --- 6 ---
    ("Laid out the archive pool as RAIDZ2 with eight 18 TB drives; RAIDZ1 would have left us one failure away from a resilver gamble on drives this large.", "decision", "technical", False,
     [("RAIDZ2", "pattern"), ("RAIDZ1", "pattern"), ("resilver", "concept"), ("archive pool", "project")],
     [("RAIDZ2", "RAIDZ1", "PREFERS"), ("RAIDZ2", "archive pool", "APPLIES_TO")],
     "why did the 18 TB archive pool pick RAIDZ2 over RAIDZ1 for its vdev layout",
     "raidz2 raidz1 resilver 18tb archive pool vdev failure"),
    # --- 7 ---
    ("Scrub schedule on the primary pool runs every 14 days with a 12-hour throttle window; the old monthly cadence let bit-rot accumulate past the next snapshot send.", "preference", "technical", False,
     [("Scrub", "pattern"), ("primary pool", "project"), ("snapshot send", "pattern")],
     [("Scrub", "primary pool", "APPLIES_TO")],
     "how often does the primary pool scrub and why the cadence shift",
     "scrub schedule primary pool bit rot snapshot cadence 14 day"),
    # --- 8 ---
    ("Replaced GlusterFS with MinIO for the object-store tier; Gluster's split-brain recoveries kept blocking the weekend batch, and the new workload was S3-native anyway.", "decision", "technical", False,
     [("GlusterFS", "technology"), ("MinIO", "technology"), ("split-brain", "pattern"), ("S3", "protocol")],
     [("MinIO", "GlusterFS", "REPLACES"), ("MinIO", "S3", "IMPLEMENTS")],
     "which object-store swap retired GlusterFS and what failure class drove it",
     "minio gluster split brain object s3 weekend batch"),
    # --- 9 ---
    ("SMB 3.1.1 is the only Windows share protocol enabled on the DSM; SMB1 stayed disabled even after a legacy scanner complained and got replaced rather than downgrading the server.", "preference", "technical", False,
     [("SMB 3.1.1", "protocol"), ("DSM", "platform"), ("SMB1", "protocol")],
     [("SMB 3.1.1", "SMB1", "REPLACES"), ("SMB 3.1.1", "DSM", "APPLIES_TO")],
     "which SMB version does the Synology DSM allow and what was the stance on the legacy scanner",
     "smb 3 1 1 dsm synology smb1 legacy scanner"),
    # --- 10. noise ---
    ("The lobby plant got rotated again because the sun track shifted after the neighbour's tree came down over the weekend.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Deployed SeaweedFS for the photo thumbnail tier behind the gallery; small-object latency on MinIO was fine but SeaweedFS volumes packed 4 KB files more tightly and cut the storage footprint by half.", "decision", "technical", False,
     [("SeaweedFS", "technology"), ("MinIO", "technology"), ("thumbnail tier", "project"), ("gallery", "service")],
     [("SeaweedFS", "MinIO", "REPLACES"), ("SeaweedFS", "thumbnail tier", "APPLIES_TO")],
     "which small-object store replaced MinIO on the thumbnail tier and why",
     "seaweedfs minio thumbnail gallery small object packing footprint"),
    # --- 12 ---
    ("The backup target is a Garage cluster with three nodes across two DCs; its S3 compatibility is strict enough that restic points at it with no vendor-specific flags.", "architecture", "technical", False,
     [("Garage", "technology"), ("S3", "protocol"), ("restic", "tool"), ("DC", "concept")],
     [("Garage", "S3", "IMPLEMENTS"), ("restic", "Garage", "USES")],
     "which object store backs restic across two data centres and how strict is its S3 layer",
     "garage s3 restic backup cluster dc compatibility"),
    # --- 13 ---
    ("LocalStack S3 stands in for the production bucket in integration tests; the CI fixture spins it up per-job so the actual AWS bill never reflects test noise.", "fact", "technical", False,
     [("LocalStack S3", "technology"), ("CI", "service"), ("AWS", "platform")],
     [("LocalStack S3", "AWS", "REPLACES"), ("CI", "LocalStack S3", "USES")],
     "which local S3 stand-in does the CI use to keep test noise off the AWS bill",
     "localstack s3 ci aws integration test fixture"),
    # --- 14 ---
    ("Moved the research workload from NFS to Lustre on the new HPC rack; MDS on an SSD pair and six OSS nodes pushed aggregate read throughput past 22 GB/s for the parallel simulation jobs.", "milestone", "technical", False,
     [("NFS", "protocol"), ("Lustre", "technology"), ("MDS", "infrastructure"), ("OSS", "infrastructure"), ("HPC", "platform")],
     [("Lustre", "NFS", "REPLACES"), ("Lustre", "HPC", "APPLIES_TO")],
     "which filesystem replaced NFS on the HPC rack and what aggregate read number did it hit",
     "lustre nfs mds oss hpc parallel simulation throughput"),
    # --- 15 ---
    ("BeeGFS drives the GPU-training scratch tier; the old shared NFS mount was the bottleneck on four-node distributed training runs and BeeGFS removed the single-server cap entirely.", "decision", "technical", False,
     [("BeeGFS", "technology"), ("NFS", "protocol"), ("GPU-training", "project")],
     [("BeeGFS", "NFS", "REPLACES"), ("BeeGFS", "GPU-training", "APPLIES_TO")],
     "which parallel filesystem took over the GPU-training scratch tier from NFS",
     "beegfs nfs gpu training scratch distributed bottleneck"),
    # --- 16 ---
    ("MooseFS chunkservers are each 10 TB and the master is actively HA with two shadows; replication goal is 2 for general data and 3 for the finance directory subtree.", "architecture", "technical", False,
     [("MooseFS", "technology"), ("chunkserver", "infrastructure"), ("master", "infrastructure"), ("finance directory", "project")],
     [("MooseFS", "finance directory", "APPLIES_TO")],
     "how is the MooseFS cluster sized and how does replication vary across its subtrees",
     "moosefs chunkserver master ha replication goal finance directory"),
    # --- 17 ---
    ("OpenMediaVault runs on the secondary NAS for the camera-recording pool; its mergerfs-plus-SnapRAID combo suits append-heavy CCTV streams better than a full ZFS layout.", "architecture", "technical", False,
     [("OpenMediaVault", "platform"), ("mergerfs", "technology"), ("SnapRAID", "technology"), ("ZFS", "technology"), ("camera-recording pool", "project")],
     [("OpenMediaVault", "camera-recording pool", "APPLIES_TO"), ("mergerfs", "SnapRAID", "DEPENDS_ON")],
     "which NAS stack handles the CCTV pool and why it was picked over ZFS",
     "openmediavault mergerfs snapraid zfs cctv camera recording"),
    # --- 18 ---
    ("unRAID hosts the mixed-drive media vault with parity on two 20 TB disks; the cache pool is a pair of NVMe in ZFS mirror so downloads land on flash before nightly mover runs.", "architecture", "technical", False,
     [("unRAID", "platform"), ("parity", "concept"), ("cache pool", "infrastructure"), ("NVMe", "technology"), ("ZFS mirror", "pattern"), ("mover", "infrastructure")],
     [("unRAID", "cache pool", "USES"), ("cache pool", "ZFS mirror", "IMPLEMENTS")],
     "how is the unRAID box laid out between parity disks, flash cache, and nightly mover",
     "unraid parity cache nvme zfs mirror mover media vault"),
    # --- 19 ---
    ("Rockstor was retired after the Btrfs send/receive on its subvolume schedule kept hanging on kernel 6.6; the pool was flattened and moved to TrueNAS Scale without data loss.", "milestone", "technical", False,
     [("Rockstor", "platform"), ("Btrfs", "technology"), ("send/receive", "pattern"), ("kernel 6.6", "config"), ("TrueNAS Scale", "platform")],
     [("TrueNAS Scale", "Rockstor", "REPLACES")],
     "why was Rockstor retired and what replaced it after the send receive hangs on kernel 6.6",
     "rockstor btrfs send receive kernel 6 6 hang truenas scale migrate"),
    # --- 20 ---
    ("iSCSI LUNs to the VMware cluster live on a dedicated RAIDZ2 ZFS dataset with logbias=throughput and volblocksize=16k; the 4k default caused write amplification that pinned IOPS low.", "decision", "technical", False,
     [("iSCSI", "protocol"), ("VMware", "platform"), ("RAIDZ2", "pattern"), ("logbias=throughput", "config"), ("volblocksize=16k", "config")],
     [("iSCSI", "VMware", "APPLIES_TO"), ("volblocksize=16k", "RAIDZ2", "APPLIES_TO")],
     "which ZFS tunables on the VMware iSCSI dataset cured the write-amplification drag",
     "iscsi vmware raidz2 logbias throughput volblocksize write amplification"),
    # --- 21 ---
    ("Introduced NVMe-oF over RoCEv2 for the database tier; fibre-channel LUNs were retired after latency for OLTP writes on the RDMA fabric landed under 40 microseconds end-to-end.", "milestone", "technical", False,
     [("NVMe-oF", "protocol"), ("RoCEv2", "protocol"), ("fibre-channel", "technology"), ("OLTP", "concept")],
     [("NVMe-oF", "fibre-channel", "REPLACES"), ("NVMe-oF", "RoCEv2", "USES")],
     "which fabric replaced fibre-channel for the DB tier and what latency threshold did it clear",
     "nvme of rocev2 fibre channel oltp rdma latency database"),
    # --- 22 ---
    ("The QNAP TS-873A in the branch office serves the project share over SMB 3.1.1 with ABE enabled; the Windows design team never sees folders they can't open, which cut their support tickets hard.", "fact", "technical", False,
     [("QNAP TS-873A", "platform"), ("SMB 3.1.1", "protocol"), ("ABE", "config"), ("branch office", "project")],
     [("QNAP TS-873A", "branch office", "APPLIES_TO")],
     "which share feature on the QNAP cut design-team support tickets in the branch office",
     "qnap ts-873a smb abe access based enumeration branch office"),
    # --- 23 ---
    ("DAS on the edit bays was pulled in favour of a 25 GbE NAS share; SAN-style block access via iSCSI got evaluated but the media team's workflow was file-based and NFS fit better.", "decision", "technical", False,
     [("DAS", "concept"), ("NAS", "concept"), ("SAN", "concept"), ("iSCSI", "protocol"), ("NFS", "protocol"), ("25 GbE", "technology")],
     [("NAS", "DAS", "REPLACES"), ("NFS", "iSCSI", "PREFERS")],
     "why did the edit bays move from DAS to NAS instead of a SAN-style iSCSI block target",
     "das nas san iscsi nfs edit bay 25gbe file workflow"),
    # --- 24 ---
    ("Resilver on the 14 TB drive took 38 hours on the RAIDZ2 array; moving from classic RAIDZ to dRAID on the next refresh should cap that window by distributing spare capacity across vdevs.", "decision", "technical", False,
     [("Resilver", "concept"), ("RAIDZ2", "pattern"), ("dRAID", "pattern"), ("vdev", "infrastructure")],
     [("dRAID", "RAIDZ2", "IMPROVES_ON")],
     "which ZFS layout should replace classic RAIDZ2 to shrink the next 14 TB resilver window",
     "resilver raidz2 draid 14tb vdev spare distribute"),
    # --- 25 ---
    ("Set compression=zstd-3 as the dataset default; lz4 was fine for hot data but the cold archive dataset gained 22 percent space back after a full rewrite under zstd.", "preference", "technical", False,
     [("compression=zstd-3", "config"), ("lz4", "algorithm"), ("archive dataset", "project")],
     [("compression=zstd-3", "lz4", "REPLACES"), ("compression=zstd-3", "archive dataset", "APPLIES_TO")],
     "which compression default swapped lz4 and how did the archive dataset benefit",
     "zstd lz4 compression archive dataset rewrite space save"),
    # --- 26 ---
    ("XFS still drives the single-node log-ingestion server; its allocation groups handle the append-only write pattern without the overhead of CoW snapshots the ingest box never uses.", "fact", "technical", False,
     [("XFS", "technology"), ("log-ingestion", "project"), ("allocation groups", "concept"), ("CoW snapshots", "pattern")],
     [("XFS", "log-ingestion", "APPLIES_TO")],
     "which filesystem backs the log-ingestion server and why CoW was considered unnecessary",
     "xfs log ingestion allocation group append cow snapshot overhead"),
    # --- 27 ---
    ("ext4 remained on the boot SSDs of every storage node; a switch to Btrfs-root was prototyped but the rollback semantics didn't justify replacing a filesystem that never fails at this workload size.", "decision", "technical", False,
     [("ext4", "technology"), ("Btrfs", "technology"), ("boot SSD", "infrastructure")],
     [("ext4", "Btrfs", "PREFERS"), ("ext4", "boot SSD", "APPLIES_TO")],
     "why did the storage nodes keep ext4 on their boot SSDs instead of adopting Btrfs",
     "ext4 btrfs boot ssd root rollback storage node"),
    # --- 28 ---
    ("The pool import failed after a power event on the JBOD shelf; scrub-after-import and a recent autotrim rollback brought the vdev state back to ONLINE without an explicit -F force import.", "fact", "technical", False,
     [("pool import", "pattern"), ("JBOD", "infrastructure"), ("scrub", "pattern"), ("autotrim", "config"), ("vdev", "infrastructure")],
     [("scrub", "pool import", "APPLIES_TO")],
     "which ZFS recovery steps restored the pool after the JBOD power event without forcing the import",
     "pool import jbod power scrub autotrim vdev online recover"),
    # --- 29 ---
    ("NFSv4.2 server-side copy is on for the dataset shared with the build farm; CI runners doing massive artifact copies stopped pulling bytes across the wire for intra-share clones.", "fact", "technical", False,
     [("NFSv4.2", "protocol"), ("server-side copy", "pattern"), ("build farm", "project"), ("CI", "service")],
     [("NFSv4.2", "build farm", "APPLIES_TO"), ("CI", "NFSv4.2", "USES")],
     "which NFSv4.2 feature spared the build farm from pulling intra-share copies across the wire",
     "nfs v4 2 server side copy build farm ci clone"),
    # --- 30 ---
    ("Ceph CRUSH map was re-weighted after a new OSD host joined; PG_BACKFILL_FULL alerts during initial placement settled once the primary-affinity on the new host was set to 0 until rebalance finished.", "problem", "technical", False,
     [("Ceph", "technology"), ("CRUSH map", "infrastructure"), ("OSD", "infrastructure"), ("PG_BACKFILL_FULL", "config"), ("primary-affinity", "config")],
     [("CRUSH map", "OSD", "APPLIES_TO")],
     "which Ceph knob calmed the backfill alerts when a new OSD host joined the cluster",
     "ceph crush osd backfill full primary affinity rebalance"),
    # --- 31 ---
    ("Snapshot replication between the main pool and the offsite pool runs over zfs send with -Rw so encrypted datasets transfer raw without reading the key on the offsite side.", "architecture", "technical", False,
     [("Snapshot replication", "pattern"), ("main pool", "project"), ("offsite pool", "project"), ("zfs send", "tool")],
     [("zfs send", "main pool", "APPLIES_TO"), ("main pool", "offsite pool", "DEPENDS_ON")],
     "how does snapshot replication keep encrypted datasets sealed while transferring to the offsite pool",
     "zfs send raw recursive encrypt snapshot replication offsite"),
    # --- 32 ---
    ("Dropped dedup on the VM dataset after ARC pressure spiked whenever the DDT grew past 1 GB per TB of pool; compression=zstd recovered most of the space without the RAM tax.", "architecture", "technical", False,
     [("dedup", "config"), ("ARC", "infrastructure"), ("DDT", "infrastructure"), ("compression=zstd", "config"), ("VM dataset", "project")],
     [("compression=zstd", "dedup", "REPLACES")],
     "which ZFS feature replaced dedup on the VM dataset and what RAM pressure did the switch relieve",
     "dedup zstd arc ddt ram pressure vm dataset"),
    # --- 33 ---
    ("The Synology DSM 7.2 upgrade rolled Btrfs metadata redundancy to DUP by default on single-drive volumes; the Hyper Backup schedule kept running without a config change.", "milestone", "technical", False,
     [("Synology", "platform"), ("DSM 7.2", "date"), ("Btrfs", "technology"), ("DUP", "config"), ("Hyper Backup", "tool")],
     [("DSM 7.2", "Synology", "EXTENDS"), ("DUP", "Btrfs", "APPLIES_TO")],
     "which Synology upgrade toggled Btrfs metadata redundancy and did backups survive the change",
     "synology dsm 7 2 btrfs metadata dup hyper backup upgrade"),
    # --- 34 ---
    ("An iSCSI MPIO setup with two 10 GbE paths serves the SQL cluster; round-robin policy balances reads but writes pin to the primary path to avoid out-of-order completion stalls.", "architecture", "technical", False,
     [("iSCSI MPIO", "pattern"), ("10 GbE", "technology"), ("SQL cluster", "project"), ("round-robin", "algorithm")],
     [("iSCSI MPIO", "SQL cluster", "APPLIES_TO")],
     "how does the iSCSI MPIO setup split reads and writes for the SQL cluster",
     "iscsi mpio 10gbe sql round robin primary path stall"),
    # --- 35 ---
    ("CephFS quotas were enforced via recursive attributes on the tenant subtrees; giving each tenant a separate data pool was considered but the ops overhead wasn't worth the tighter isolation.", "decision", "technical", False,
     [("CephFS", "technology"), ("quota", "pattern"), ("tenant subtree", "project"), ("data pool", "infrastructure")],
     [("quota", "tenant subtree", "APPLIES_TO")],
     "which CephFS isolation approach won over per-tenant data pools for multi-tenant quotas",
     "cephfs quota recursive attribute tenant subtree data pool isolation"),
    # --- 36 ---
    ("Hit a silent truncation bug on SMB with very long Unicode filenames over the VPN; protocol capture showed SMB2 TREE_CONNECT fragmenting oddly and raising the MTU on the tunnel fixed it.", "problem", "technical", False,
     [("SMB", "protocol"), ("Unicode", "concept"), ("VPN", "technology"), ("SMB2 TREE_CONNECT", "api"), ("MTU", "config")],
     [("MTU", "SMB", "APPLIES_TO")],
     "which network knob cleared the long-filename truncation seen over SMB on the VPN",
     "smb unicode filename truncate vpn tree connect mtu fragment"),
    # --- 37 ---
    ("The MinIO tenant runs in erasure-coded mode with EC:4 across eight drives per node; parity-only reads keep serving during a full rack reboot which matches the two-nines availability target.", "architecture", "technical", False,
     [("MinIO", "technology"), ("erasure-coded", "pattern"), ("EC:4", "config"), ("rack reboot", "pattern")],
     [("MinIO", "EC:4", "USES")],
     "which erasure-coding profile keeps the MinIO tenant serving through a full rack reboot",
     "minio erasure code ec 4 rack reboot availability parity"),
    # --- 38 ---
    ("Stopped sharing the /home tree over NFS and moved to per-user CephFS subvolumes; the single-writer model under NFS was choking on concurrent IDE indexers across five developer laptops.", "decision", "technical", False,
     [("NFS", "protocol"), ("CephFS", "technology"), ("subvolume", "infrastructure"), ("/home tree", "project")],
     [("CephFS", "NFS", "REPLACES"), ("CephFS", "/home tree", "APPLIES_TO")],
     "which shared-home tech replaced NFS and what concurrency problem drove the move",
     "cephfs subvolume nfs home tree concurrent ide indexer"),
    # --- 39 ---
    ("CephFS snapshot directory is exposed at .snap on each subvolume and users can self-restore from any of the last 24 hourly retention slots without opening a ticket.", "fact", "technical", False,
     [("CephFS", "technology"), (".snap", "api"), ("subvolume", "infrastructure"), ("hourly retention", "pattern")],
     [(".snap", "CephFS", "APPLIES_TO")],
     "which CephFS feature lets users self-restore from hourly snapshots on their subvolume",
     "cephfs snap directory subvolume hourly retention self restore"),
    # --- 40 ---
    ("Reference: TrueNAS docs for pool geometry recommend 6 to 10 disks per RAIDZ2 vdev and striping multiple vdevs for IOPS rather than widening a single vdev past 12 drives.", "reference", "technical", False,
     [("TrueNAS", "platform"), ("RAIDZ2", "pattern"), ("vdev", "infrastructure")],
     [("RAIDZ2", "vdev", "APPLIES_TO")],
     "what disk-count band does the TrueNAS guidance give for RAIDZ2 vdevs before striping",
     "truenas raidz2 vdev 6 10 disk pool geometry iops"),
    # --- 41 ---
    ("Reference: OpenZFS manual notes ARC target size self-tunes but zfs_arc_max should be pinned on servers sharing RAM with application workloads to avoid OOM thrash.", "reference", "technical", False,
     [("OpenZFS", "technology"), ("ARC", "infrastructure"), ("zfs_arc_max", "config"), ("OOM", "concept")],
     [("zfs_arc_max", "ARC", "APPLIES_TO")],
     "what ARC guidance does the OpenZFS manual give for servers colocated with application workloads",
     "openzfs arc zfs arc max oom application server tune"),
    # --- 42 ---
    ("Ceph's 'Red Hat recommends 1 GB RAM per 1 TB OSD' guidance held up in practice; dropping below 0.8 GB per TB triggered the memory-pressure OOM kills we saw last spring.", "fact", "technical", False,
     [("Ceph", "technology"), ("OSD", "infrastructure"), ("RAM", "concept"), ("OOM", "concept")],
     [("RAM", "OSD", "APPLIES_TO")],
     "which Ceph sizing rule matched the OOM-kill threshold observed last spring on the OSDs",
     "ceph osd ram gb tb memory pressure oom kill"),
    # --- 43. noise ---
    ("The office ficus is lopsided again because the south window lets more afternoon sun through than the blinds compensate for.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Reference: SMB 3.1.1 mandates pre-auth integrity and encryption negotiation with AES-128-GCM or AES-256-GCM; any downgrade to SMB 3.0 silently drops those guarantees.", "reference", "technical", False,
     [("SMB 3.1.1", "protocol"), ("AES-128-GCM", "algorithm"), ("AES-256-GCM", "algorithm"), ("SMB 3.0", "protocol")],
     [("SMB 3.1.1", "SMB 3.0", "IMPROVES_ON")],
     "which SMB 3.1.1 security features does a downgrade to 3.0 quietly drop",
     "smb 3 1 1 pre auth aes gcm downgrade 3 0 integrity"),
    # --- 45 ---
    ("Reference: NFSv4.2 added sparse-file support with SEEK_HOLE/SEEK_DATA; older NFSv4.1 clients reading the same export silently zero-fill the holes and waste bandwidth.", "reference", "technical", False,
     [("NFSv4.2", "protocol"), ("NFSv4.1", "protocol"), ("SEEK_HOLE", "api"), ("SEEK_DATA", "api")],
     [("NFSv4.2", "NFSv4.1", "IMPROVES_ON")],
     "which NFSv4.2 seek extension breaks on v4.1 clients reading the same export",
     "nfs v4 2 v4 1 seek hole data sparse zero fill"),
    # --- 46 ---
    ("Reference: Garage's anti-entropy design rejects strong consistency on writes; teams picking it over MinIO need to accept eventual-consistency reads on the control-plane bucket.", "reference", "technical", False,
     [("Garage", "technology"), ("MinIO", "technology"), ("eventual-consistency", "concept"), ("control-plane bucket", "project")],
     [("Garage", "MinIO", "PREFERS")],
     "which consistency trade-off does Garage demand when it replaces MinIO on the control plane",
     "garage minio eventual consistency anti entropy control plane"),
    # --- 47 ---
    ("A preference to keep pool versions pinned across the estate kept us on OpenZFS 2.1 for eighteen months; upgrading to OpenZFS 2.2.2 only happened after the block-cloning bug fix landed.", "preference", "technical", False,
     [("OpenZFS 2.1", "date"), ("OpenZFS 2.2.2", "date"), ("block-cloning", "pattern")],
     [("OpenZFS 2.2.2", "OpenZFS 2.1", "REPLACES"), ("OpenZFS 2.2.2", "block-cloning", "FIXES")],
     "which OpenZFS version finally unblocked the upgrade after a block-cloning regression",
     "openzfs 2 1 2 2 2 2 2 block clone upgrade pin"),
    # --- 48 ---
    ("Ran a week-long bake of Btrfs RAID1C3 on the secondary pool after the RAID5 advice stayed red in upstream status; snapshots and balance both held up under a forced drive failure.", "milestone", "technical", False,
     [("Btrfs", "technology"), ("RAID1C3", "pattern"), ("RAID5", "pattern"), ("secondary pool", "project")],
     [("RAID1C3", "RAID5", "PREFERS"), ("RAID1C3", "secondary pool", "APPLIES_TO")],
     "which Btrfs profile passed the week-long bake on the secondary pool after RAID5 stayed red",
     "btrfs raid1c3 raid5 secondary pool bake drive failure snapshot"),
    # --- 49 ---
    ("The cluster hit a real milestone: zero split-brain incidents for a full quarter after the CephFS MDS active-standby pair moved onto dedicated hardware with a pinned CPU governor.", "milestone", "technical", False,
     [("CephFS", "technology"), ("MDS", "infrastructure"), ("split-brain", "pattern"), ("CPU governor", "config")],
     [("MDS", "CephFS", "USES")],
     "what cluster milestone followed moving the CephFS MDS pair onto dedicated hardware",
     "cephfs mds split brain quarter dedicated hardware cpu governor"),
    # --- 50 ---
    ("Reference: OpenZFS dRAID spare capacity is a distributed reservation rather than a hot-spare drive; the resilver rebuilds into spare blocks in parallel, which is why 14 TB windows shrink versus RAIDZ.", "reference", "technical", False,
     [("OpenZFS", "technology"), ("dRAID", "pattern"), ("RAIDZ", "pattern"), ("resilver", "concept"), ("spare blocks", "infrastructure")],
     [("dRAID", "RAIDZ", "IMPROVES_ON")],
     "how does dRAID lay out spare capacity to shrink resilver windows compared to RAIDZ",
     "openzfs draid raidz resilver distributed spare block 14tb"),
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
