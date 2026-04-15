"""One-off emitter for shared-base batch-068 — technical domain (storage systems / filesystems / object stores).

Writes 50 rows to data/v2/shared/batch_068.tmp.jsonl with ids shared-03351..03400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_068.tmp.jsonl"
ID_OFFSET = 3350

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Ceph replaced GlusterFS for the OpenStack Cinder backend; CRUSH placement plus RBD snapshots beat the brick-replication model on rebalance speed.", "decision", "technical", False,
     [("Ceph", "technology"), ("GlusterFS", "technology"), ("OpenStack Cinder", "service"), ("CRUSH", "algorithm"), ("RBD", "technology")],
     [("Ceph", "GlusterFS", "REPLACES")],
     "which distributed store displaced GlusterFS behind the Cinder volumes",
     "Ceph CRUSH RBD Cinder block backend rebalance swap"),
    # --- 2 ---
    ("MinIO ran the on-prem S3 layer for the analytics cluster; erasure coding at EC:4+2 delivered the durability target without paying RF3 storage cost.", "architecture", "technical", False,
     [("MinIO", "service"), ("S3", "service"), ("EC:4+2", "config")],
     [],
     "which on-prem object store fronted the analytics cluster with EC coding",
     "MinIO erasure coding 4 plus 2 durability storage cost"),
    # --- 3 ---
    ("AWS S3 Intelligent-Tiering replaced the cron-driven lifecycle policy on the cold dataset; access-pattern monitoring shifted blocks without rewrite jobs.", "decision", "technical", False,
     [("AWS S3 Intelligent-Tiering", "service")],
     [],
     "which S3 feature retired the manual lifecycle cron for cold data tiering",
     "intelligent tiering monitor pattern lifecycle cron retire"),
    # --- 4 ---
    ("ZFS on the backup pool gave snapshot-and-send replication for free; ext4 on the previous box needed rsync plus LVM snapshots glued together.", "decision", "technical", False,
     [("ZFS", "technology"), ("ext4", "technology"), ("LVM", "technology"), ("rsync", "tool")],
     [("ZFS", "ext4", "IMPROVES_ON")],
     "which filesystem brought first-class snapshot send to the backup pool",
     "ZFS snapshot send receive ext4 LVM rsync replace pool"),
    # --- 5 ---
    ("Btrfs subvolumes replaced separate ext4 partitions on the dev workstations; copy-on-write snapshots let CI rollback an apt-get gone wrong in seconds.", "decision", "technical", False,
     [("Btrfs", "technology"), ("ext4", "technology"), ("CI", "service"), ("apt-get", "command")],
     [("Btrfs", "ext4", "REPLACES")],
     "which filesystem replaced ext4 partitions to enable CoW rollbacks on dev",
     "Btrfs subvolume copy on write snapshot rollback dev box"),
    # --- 6 ---
    ("XFS was preferred over ext4 on the database volumes; the allocator handled the 12 TB log directories without the inode pressure ext4 hit at scale.", "preference", "technical", False,
     [("XFS", "technology"), ("ext4", "technology")],
     [("XFS", "ext4", "PREFERS")],
     "which filesystem won on the multi-TB database log volumes",
     "XFS allocator inode pressure database log volume scale"),
    # --- 7 ---
    ("Lustre on the HPC cluster spread the simulation output across 128 OSTs; throughput hit 240 GB/s aggregate on the burst write phase.", "architecture", "technical", False,
     [("Lustre", "technology"), ("HPC", "infrastructure"), ("OSTs", "infrastructure")],
     [],
     "which parallel filesystem absorbed the HPC burst write at 240 GB/s",
     "Lustre OST stripe HPC simulation aggregate burst write"),
    # --- 8 ---
    ("CephFS replaced NFSv4 for the shared homedirs; multi-MDS scaling held the metadata latency flat as the user count crossed 5000.", "decision", "technical", False,
     [("CephFS", "technology"), ("NFSv4", "protocol"), ("MDS", "service")],
     [("CephFS", "NFSv4", "REPLACES")],
     "which networked filesystem took over from NFSv4 on the shared homedirs",
     "CephFS multi MDS metadata latency homedir scale swap"),
    # --- 9 ---
    ("S3 strong read-after-write consistency landed in 2020; the legacy retry-until-200 loop in the ingest job was finally deleted from the pipeline.", "milestone", "technical", False,
     [("S3", "service")],
     [],
     "which S3 semantics change let the retry-until-200 loop be deleted",
     "S3 strong read after write consistency retry loop remove"),
    # --- 10. noise ---
    ("Hold on, the rebalance is still chewing through the placement groups.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Google Cloud Storage Nearline replaced the manual bucket-rotation script; access cost on quarterly reports beat Standard once dwell time crossed 60 days.", "decision", "technical", False,
     [("Google Cloud Storage Nearline", "service"), ("Standard", "service")],
     [("Google Cloud Storage Nearline", "Standard", "REPLACES")],
     "which GCS class displaced Standard for the 60-day-plus reports",
     "Nearline access cost dwell day report swap class GCS"),
    # --- 12 ---
    ("Glacier Deep Archive held the seven-year compliance copies; restore latency was 12 hours bulk but the per-GB storage line was a tenth of S3 IA.", "architecture", "technical", False,
     [("Glacier Deep Archive", "service"), ("S3 IA", "service")],
     [],
     "which AWS tier held the seven-year compliance copies cheaply",
     "Glacier Deep Archive restore latency bulk compliance year"),
    # --- 13 ---
    ("S3 multipart upload split the 80 GB build artifact into 64 MB parts; parallel PUTs cut total upload from 41 minutes to under 6.", "milestone", "technical", False,
     [("S3", "service")],
     [],
     "which S3 mechanism shrank the 80 GB artifact upload window past 10x",
     "multipart upload parallel part build artifact upload time"),
    # --- 14 ---
    ("HDFS was retired on the new lake; S3-compatible MinIO over erasure coding took the role without the NameNode single-point-of-failure problem.", "decision", "technical", False,
     [("HDFS", "technology"), ("MinIO", "service"), ("NameNode", "service")],
     [("MinIO", "HDFS", "REPLACES")],
     "which storage swap retired HDFS and the NameNode SPOF on the lake",
     "HDFS NameNode single point failure object store retire"),
    # --- 15 ---
    ("Alluxio cached the hot Parquet files in front of S3; per-query latency on Trino dropped 4x on the dashboard workload.", "architecture", "technical", False,
     [("Alluxio", "technology"), ("Parquet", "technology"), ("S3", "service"), ("Trino", "service")],
     [],
     "which cache layer fronted S3 Parquet reads for the Trino dashboard",
     "Alluxio Parquet cache S3 Trino dashboard query latency"),
    # --- 16 ---
    ("Object lifecycle policy on the bucket transitioned objects to Glacier after 90 days; non-current versions expired at 30 to clip the version-bloat tail.", "decision", "technical", False,
     [("Glacier", "service")],
     [],
     "which lifecycle rule clipped the version-bloat tail on the bucket",
     "lifecycle transition expire non current version bloat tail"),
    # --- 17 ---
    ("Block storage on EBS gp3 replaced gp2 across the EKS node fleet; baseline 3000 IOPS at lower per-GB cost matched the Postgres workload.", "decision", "technical", False,
     [("EBS gp3", "service"), ("gp2", "service"), ("EKS", "service"), ("Postgres", "database")],
     [("EBS gp3", "gp2", "REPLACES")],
     "which EBS class swap landed on the EKS Postgres node fleet",
     "EBS gp3 gp2 IOPS baseline cost Postgres EKS swap class"),
    # --- 18 ---
    ("File-level NFS mounts were dropped from the render farm; the artists moved to an SMB3 share on a Windows storage spaces direct cluster.", "decision", "technical", False,
     [("NFS", "protocol"), ("SMB3", "protocol"), ("Windows", "platform")],
     [("SMB3", "NFS", "REPLACES")],
     "which file protocol replaced NFS on the artists' render farm",
     "NFS SMB3 share Windows storage spaces render farm swap"),
    # --- 19 ---
    ("Ceph BlueStore replaced FileStore on the OSD layer; bypassing the local XFS journal cut write amplification by roughly half on RBD volumes.", "decision", "technical", False,
     [("Ceph BlueStore", "technology"), ("FileStore", "technology"), ("XFS", "technology"), ("RBD", "technology")],
     [("Ceph BlueStore", "FileStore", "REPLACES")],
     "which OSD backend retired FileStore and cut write amplification",
     "BlueStore FileStore XFS journal write amplification swap"),
    # --- 20 ---
    ("Erasure coding at EC:8+3 was preferred over RF3 on the cold tier; storage overhead dropped from 200 percent to 38 percent for the same durability.", "preference", "technical", False,
     [("EC:8+3", "config"), ("RF3", "config")],
     [("EC:8+3", "RF3", "PREFERS")],
     "which durability scheme beat triple replication on the cold tier",
     "erasure code EC 8 plus 3 RF3 storage overhead durability"),
    # --- 21 ---
    ("S3 Object Lock with Compliance mode held the SEC 17a-4 archive bucket; even root could not delete inside the retention window.", "architecture", "technical", False,
     [("S3 Object Lock", "service"), ("SEC 17a-4", "concept")],
     [],
     "which S3 feature held the SEC 17a-4 archive bucket immutable",
     "object lock compliance retention root delete archive bucket"),
    # --- 22 ---
    ("Cross-region replication on the S3 backups went to eu-central-1; failover RPO sat under 15 minutes on the asynchronous channel.", "architecture", "technical", False,
     [("S3", "service"), ("eu-central-1", "place")],
     [],
     "which S3 replication target backed the 15-minute RPO failover",
     "cross region replication eu central RPO failover async"),
    # --- 23 ---
    ("Ceph rebalance after adding a new OSD caused a slow request spike; PG autoscaler defaults overshot the placement-group count for the pool size.", "problem", "technical", False,
     [("Ceph", "technology"), ("OSD", "service"), ("PG", "concept")],
     [],
     "which Ceph tunable misfired and produced the slow request spike",
     "PG autoscaler OSD add rebalance slow request placement"),
    # --- 24 ---
    ("Data Lake Storage Gen2 replaced raw Azure Blob for the analytics path; the hierarchical namespace let Spark prune by directory not by prefix scan.", "decision", "technical", False,
     [("Data Lake Storage Gen2", "service"), ("Azure Blob", "service"), ("Spark", "framework")],
     [("Data Lake Storage Gen2", "Azure Blob", "REPLACES")],
     "which Azure storage swap fixed the prefix-scan pain on Spark jobs",
     "ADLS Gen2 hierarchical namespace prefix scan prune Spark"),
    # --- 25 ---
    ("S3 Express One Zone hosted the shuffle spill bucket; single-digit-millisecond GETs beat the round trip to the multi-AZ Standard tier.", "decision", "technical", False,
     [("S3 Express One Zone", "service"), ("Standard", "service")],
     [("S3 Express One Zone", "Standard", "IMPROVES_ON")],
     "which S3 class displaced Standard for the shuffle spill latency",
     "Express One Zone single millisecond GET shuffle spill bucket"),
    # --- 26 ---
    ("Quobyte was rejected as the HPC scratch filesystem; the licensing model and per-node agent overhead lost to a tuned Lustre deploy.", "decision", "technical", False,
     [("Quobyte", "technology"), ("Lustre", "technology"), ("HPC", "infrastructure")],
     [],
     "which scratch filesystem lost the HPC bake-off against tuned Lustre",
     "Quobyte license per node agent overhead scratch filesystem"),
    # --- 27 ---
    ("ZFS ARC sized at 96 GB on the storage head let the metadata workload land in RAM; cold-cache cold reads still touched the spinning rust pool.", "architecture", "technical", False,
     [("ZFS", "technology"), ("ARC", "technology"), ("RAM", "infrastructure")],
     [],
     "which ZFS cache knob held the metadata workload in memory",
     "ZFS ARC size metadata RAM cold cache spinning pool"),
    # --- 28 ---
    ("ZFS L2ARC on NVMe replaced the previous bcache layer in front of the SATA pool; the read miss path no longer routed through the kernel block layer twice.", "decision", "technical", False,
     [("ZFS", "technology"), ("L2ARC", "technology"), ("NVMe", "technology"), ("bcache", "technology"), ("SATA", "technology")],
     [("L2ARC", "bcache", "REPLACES")],
     "which ZFS read cache took bcache's place on the SATA pool front",
     "L2ARC NVMe bcache SATA read miss block layer swap"),
    # --- 29 ---
    ("S3 Transfer Acceleration was preferred over a self-built CloudFront upload trick for the global ingestion endpoint; signed URL flow stayed unchanged.", "preference", "technical", False,
     [("S3 Transfer Acceleration", "service"), ("CloudFront", "service")],
     [("S3 Transfer Acceleration", "CloudFront", "PREFERS")],
     "which S3 path beat the CloudFront upload trick for global ingest",
     "transfer acceleration signed URL global ingest path swap"),
    # --- 30 ---
    ("S3 versioning plus MFA Delete protected the artifact bucket; an accidental aws s3 rb --force on staging was recovered in under five minutes.", "milestone", "technical", False,
     [("S3", "service"), ("MFA Delete", "service")],
     [],
     "which S3 protection caught the accidental rb --force on staging",
     "version MFA delete protect bucket recover accidental wipe"),
    # --- 31 ---
    ("BeeGFS was the parallel filesystem on the CFD cluster; metadata servers ran on dedicated NVMe to keep the small-file open path fast.", "architecture", "technical", False,
     [("BeeGFS", "technology"), ("CFD", "concept"), ("NVMe", "technology")],
     [],
     "which parallel filesystem ran on the CFD cluster's metadata path",
     "BeeGFS metadata server NVMe small file open CFD cluster"),
    # --- 32 ---
    ("Wasabi Hot Cloud Storage replaced AWS S3 Standard for the media archive; egress-free pricing won at the 90 TB monthly read pattern.", "decision", "technical", False,
     [("Wasabi Hot Cloud Storage", "service"), ("AWS S3 Standard", "service")],
     [("Wasabi Hot Cloud Storage", "AWS S3 Standard", "REPLACES")],
     "which object store displaced S3 Standard on the 90 TB media archive",
     "Wasabi egress free media archive read pattern monthly swap"),
    # --- 33 ---
    ("Backblaze B2 backed the offsite backup of the homelab; the S3-compatible API meant restic could write without a custom backend plugin.", "decision", "technical", False,
     [("Backblaze B2", "service"), ("restic", "tool")],
     [],
     "which cheap object store took the offsite restic repo",
     "Backblaze B2 S3 compatible restic offsite backup repo"),
    # --- 34. noise ---
    ("Hang on, the bucket listing is still paginating.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("OpenZFS native encryption replaced the LUKS layer below the pool; raw send to the offsite host kept the data encrypted at rest end-to-end.", "decision", "technical", False,
     [("OpenZFS", "technology"), ("LUKS", "technology")],
     [("OpenZFS", "LUKS", "REPLACES")],
     "which encryption layer took LUKS's place below the ZFS pool",
     "native encryption raw send offsite encrypt end to end LUKS"),
    # --- 36 ---
    ("S3 Select pushed the Parquet predicate evaluation to the storage layer; the dashboard query payload dropped from 1.2 GB scanned to 38 MB returned.", "architecture", "technical", False,
     [("S3 Select", "service"), ("Parquet", "technology")],
     [],
     "which S3 feature pushed Parquet predicates into the storage layer",
     "S3 Select push down Parquet predicate scan return drop"),
    # --- 37 ---
    ("Object versioning surfaced a silent overwrite bug in the ETL writer; a stale partition replay had been clobbering the day's manifest.json.", "problem", "technical", False,
     [("ETL", "concept"), ("manifest.json", "file")],
     [],
     "which storage feature exposed the silent overwrite bug in the ETL writer",
     "version overwrite ETL partition replay manifest clobber bug"),
    # --- 38 ---
    ("Garage replaced MinIO on the geo-distributed object store; native multi-region replication beat the MinIO site replication operational story.", "decision", "technical", False,
     [("Garage", "technology"), ("MinIO", "service")],
     [("Garage", "MinIO", "REPLACES")],
     "which object store displaced MinIO on the geo-distributed deploy",
     "Garage multi region replication MinIO site geo distribute"),
    # --- 39 ---
    ("SeaweedFS handled the small-file storage tier; the volume server design dodged the inode-per-file cost that ext4 paid on the previous setup.", "architecture", "technical", False,
     [("SeaweedFS", "technology"), ("ext4", "technology")],
     [("SeaweedFS", "ext4", "IMPROVES_ON")],
     "which object store dodged the inode-per-file cost of ext4 small files",
     "SeaweedFS small file volume server inode cost ext4 swap"),
    # --- 40 ---
    ("JuiceFS over S3 fronted the ML training data; POSIX semantics on top of object storage let PyTorch DataLoader workers mmap files cleanly.", "architecture", "technical", False,
     [("JuiceFS", "technology"), ("S3", "service"), ("PyTorch", "framework"), ("DataLoader", "library")],
     [],
     "which filesystem layer gave POSIX over S3 for PyTorch DataLoader",
     "JuiceFS POSIX object storage mmap DataLoader training data"),
    # --- 41 ---
    ("S3 access points replaced bucket policies for cross-team sharing; per-team policy isolation cut the policy review effort by an order of magnitude.", "decision", "technical", False,
     [("S3 access points", "service"), ("bucket policies", "concept")],
     [("S3 access points", "bucket policies", "REPLACES")],
     "which S3 sharing primitive retired the cross-team bucket policy mess",
     "access point per team policy isolation review effort swap"),
    # --- 42 ---
    ("FUSE mounts via s3fs were rejected for the production write path; eventual consistency on directory listings broke the build artifact promotion job.", "decision", "technical", False,
     [("FUSE", "technology"), ("s3fs", "tool")],
     [],
     "which FUSE adapter was rejected on the production artifact write path",
     "FUSE s3fs eventual list directory build promotion break"),
    # --- 43 ---
    ("Mountpoint for Amazon S3 was preferred over s3fs on the read-heavy training pipeline; multi-part GETs and prefetch landed deep in the page cache.", "preference", "technical", False,
     [("Mountpoint for Amazon S3", "tool"), ("s3fs", "tool")],
     [("Mountpoint for Amazon S3", "s3fs", "PREFERS")],
     "which S3 mount tool beat s3fs on the read-heavy training pipeline",
     "Mountpoint Amazon S3 prefetch multipart GET page cache swap"),
    # --- 44 ---
    ("AWS Storage Gateway in cached-volume mode replaced the on-prem iSCSI SAN tail; cold blocks sat in S3 while the hot working set stayed local.", "decision", "technical", False,
     [("AWS Storage Gateway", "service"), ("iSCSI", "protocol"), ("SAN", "infrastructure"), ("S3", "service")],
     [("AWS Storage Gateway", "iSCSI", "REPLACES")],
     "which gateway swap put the cold iSCSI blocks into S3 transparently",
     "Storage Gateway cache volume iSCSI SAN cold block hot set"),
    # --- 45 ---
    ("AWS S3 documentation on consistency model is the reference for the ingestion pipeline; the strongly consistent read-after-write contract removed the need for the polling barrier.", "reference", "technical", False,
     [("AWS S3", "service")],
     [],
     "which documentation guided the polling barrier removal in ingestion",
     "S3 documentation consistency model read after write barrier"),
    # --- 46 ---
    ("ZFS scrub finished on the 80 TB pool with zero checksum errors; the monthly scrub cron caught two URE candidates over the previous year.", "milestone", "technical", False,
     [("ZFS", "technology")],
     [],
     "which storage health check caught the URE candidates over the year",
     "ZFS scrub checksum URE error month cron pool clean"),
    # --- 47 ---
    ("EBS Multi-Attach was rejected for the Postgres HA cluster; the filesystem was not cluster-aware and the corruption risk was real on a split brain.", "decision", "technical", False,
     [("EBS Multi-Attach", "service"), ("Postgres", "database")],
     [],
     "which EBS feature was rejected on the Postgres HA cluster and why",
     "Multi Attach cluster aware filesystem corruption split brain"),
    # --- 48 ---
    ("S3 batch operations re-encrypted 14 million objects with the new KMS key; the manifest-driven job ran for four hours and cost under twenty dollars.", "milestone", "technical", False,
     [("S3", "service"), ("KMS", "service")],
     [],
     "which S3 capability re-encrypted 14 million objects with the new key",
     "batch operation re encrypt KMS key manifest driven cost"),
    # --- 49 ---
    ("CSI driver for Ceph RBD was deployed on the Kubernetes cluster; PVCs bound to RBD images replaced the static hostPath volumes the team used before.", "decision", "technical", False,
     [("CSI", "framework"), ("Ceph RBD", "technology"), ("Kubernetes", "platform"), ("PVCs", "concept"), ("hostPath", "config")],
     [("Ceph RBD", "hostPath", "REPLACES")],
     "which CSI driver retired hostPath volumes on the Kubernetes cluster",
     "CSI driver Ceph RBD PVC hostPath Kubernetes volume swap"),
    # --- 50 ---
    ("Tiered storage on Pulsar pushed sealed segments to S3 on 2026-02-18; the broker disk footprint dropped from 3.4 TB to under 280 GB per node.", "milestone", "technical", False,
     [("Pulsar", "service"), ("S3", "service"), ("2026-02-18", "date")],
     [],
     "when did Pulsar tiered storage offload sealed segments to S3",
     "tiered storage Pulsar sealed segment S3 broker disk drop"),
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
