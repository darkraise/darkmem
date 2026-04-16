"""One-off emitter for shared-base batch-196 — technical domain (backup strategies and snapshotting: restic, Borg, Kopia, rsync, ZFS/Btrfs snapshots, VSS, chunking, 3-2-1 retention, Velero).

Writes 50 rows to data/v2/shared/batch_196.tmp.jsonl with ids shared-09751..09800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_196.tmp.jsonl"
ID_OFFSET = 9750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the fileserver backups from rsnapshot to restic against a Wasabi bucket; content-addressed chunking plus client-side encryption shrank the wire footprint by a factor of four and retention pruning finally runs in under a minute.", "decision", "technical", False,
     [("rsnapshot", "tool"), ("restic", "tool"), ("Wasabi", "service"), ("content-addressed chunking", "pattern"), ("client-side encryption", "pattern")],
     [("restic", "rsnapshot", "REPLACES"), ("restic", "Wasabi", "USES")],
     "which backup tool replaced rsnapshot for the fileserver and what backend did it target",
     "restic rsnapshot wasabi chunking encryption fileserver prune"),
    # --- 2 ---
    ("Borg Backup drives the laptop fleet to a hardened SSH endpoint; append-only mode on the server repo means a compromised client cannot rewrite or delete older archives even with full credentials.", "decision", "technical", False,
     [("Borg Backup", "tool"), ("SSH", "protocol"), ("append-only mode", "pattern")],
     [("Borg Backup", "append-only mode", "USES")],
     "which Borg feature prevents a compromised laptop from rewriting older archives on the server",
     "borg backup ssh append only laptop compromise ransomware immutable"),
    # --- 3 ---
    ("Kopia replaced Duplicati on the home NAS after two corruption incidents where Duplicati's SQLite index got out of sync with the remote store; Kopia's content-addressed layout survived a yanked USB cable cleanly.", "decision", "technical", False,
     [("Kopia", "tool"), ("Duplicati", "tool"), ("SQLite", "database"), ("NAS", "platform")],
     [("Kopia", "Duplicati", "REPLACES")],
     "which backup tool replaced Duplicati on the home NAS and what class of failure drove it out",
     "kopia duplicati sqlite nas index corruption yank cable"),
    # --- 4 ---
    ("Duplicacy sits on the media workstation because its lock-free design lets four concurrent machines push to the same B2 repository without a coordinator; the cross-machine dedup ratio landed near seventy percent.", "fact", "technical", False,
     [("Duplicacy", "tool"), ("B2", "service"), ("lock-free", "pattern"), ("cross-machine dedup", "pattern")],
     [("Duplicacy", "B2", "USES")],
     "which backup tool drives concurrent pushes to a shared B2 repository without a coordinator",
     "duplicacy b2 backblaze lock free concurrent dedup workstation"),
    # --- 5 ---
    ("Kept rsync for the photo-library mirror between the primary NAS and the cold-storage box; it is not a proper backup tool but the --link-dest chain gives a decent snapshot history for pennies of extra disk.", "preference", "technical", False,
     [("rsync", "tool"), ("photo-library", "project"), ("--link-dest", "config"), ("cold-storage", "pattern")],
     [("rsync", "--link-dest", "USES")],
     "why does the photo-library mirror still run on rsync instead of a proper backup tool",
     "rsync link dest photo library nas cold storage hardlink history"),
    # --- 6 ---
    ("rclone with crypt wrapping handles the offsite push of already-deduped borg repos to S3 Glacier Deep Archive; layering encryption twice is cheap and gives defence in depth against a provider breach.", "decision", "technical", False,
     [("rclone", "tool"), ("crypt", "pattern"), ("S3 Glacier Deep Archive", "service"), ("borg", "tool")],
     [("rclone", "S3 Glacier Deep Archive", "USES"), ("rclone", "borg", "APPLIES_TO")],
     "how does the offsite push layer encryption on top of the already-encrypted borg repos",
     "rclone crypt s3 glacier deep archive borg offsite defence depth"),
    # --- 7 ---
    ("ZFS send and receive now pipes hourly incremental snapshots of the tank pool from the primary to the DR box over a dedicated 10G link; after last month's cutover the receiving side is read-only to stop accidental writes from drifting the replica.", "milestone", "technical", False,
     [("ZFS", "technology"), ("tank pool", "concept"), ("DR box", "platform"), ("10G link", "config")],
     [("ZFS", "DR box", "APPLIES_TO")],
     "which ZFS mechanism replicates the tank pool to the DR box and how is the replica kept clean",
     "zfs send receive tank pool dr box read only 10g incremental"),
    # --- 8 ---
    ("Btrfs read-only snapshots run every fifteen minutes on the workstation home subvolume; a snapper timeline keeps hourlies for a day, dailies for a month, and monthlies for a year without operator intervention.", "preference", "technical", False,
     [("Btrfs", "technology"), ("snapper", "tool"), ("home subvolume", "concept"), ("timeline", "pattern")],
     [("snapper", "Btrfs", "USES")],
     "which snapshot tool manages the Btrfs home subvolume retention tiers on the workstation",
     "btrfs snapper snapshot home subvolume timeline hourly daily monthly"),
    # --- 9 ---
    ("LVM thin snapshots gate the pre-upgrade rollback on the bare-metal Postgres host; the snapshot is taken while the service is briefly checkpointed, and a botched upgrade is one lvconvert --merge away from the prior state.", "fact", "technical", False,
     [("LVM", "technology"), ("thin snapshots", "pattern"), ("Postgres", "database"), ("lvconvert --merge", "command")],
     [("LVM", "Postgres", "APPLIES_TO")],
     "how does the Postgres host roll back a failed upgrade using LVM snapshots",
     "lvm thin snapshot postgres rollback lvconvert merge upgrade host"),
    # --- 10. noise ---
    ("The office plant on the printer counter survived another three-week outage while nobody remembered to water it on the team trip.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Windows VSS coordinates application-consistent snapshots across SQL Server and the Exchange mailstore on the legacy file host; the VSS writer framework flushes in-flight transactions before the shadow copy pivots.", "reference", "technical", False,
     [("VSS", "api"), ("SQL Server", "database"), ("Exchange", "service"), ("VSS writer", "pattern")],
     [("VSS", "SQL Server", "APPLIES_TO"), ("VSS", "Exchange", "APPLIES_TO")],
     "how does the legacy Windows host get application-consistent snapshots across SQL Server and Exchange",
     "vss writer sql server exchange shadow copy application consistent"),
    # --- 12 ---
    ("Time Machine covers the design team's Macs to a Synology AFP target; APFS local snapshots carry the day between offsite sweeps, which is important because the office link drops half the afternoons.", "fact", "technical", False,
     [("Time Machine", "tool"), ("Synology", "platform"), ("APFS", "technology"), ("AFP", "protocol")],
     [("Time Machine", "Synology", "USES")],
     "how do the design Macs stay protected when the office uplink flaps in the afternoon",
     "time machine synology afp apfs local snapshot mac design team"),
    # --- 13 ---
    ("Encryption-at-rest for the restic repository uses the stock AES-256 chunk encryption with a passphrase stored in a hardware token; an attacker holding only the S3 bucket learns nothing about file sizes beyond the chunker's floor.", "reference", "technical", False,
     [("restic", "tool"), ("AES-256", "algorithm"), ("hardware token", "pattern"), ("S3 bucket", "service")],
     [("restic", "AES-256", "USES")],
     "which encryption scheme protects the restic repository and where does the passphrase live",
     "restic aes 256 hardware token s3 bucket encryption rest passphrase"),
    # --- 14 ---
    ("FastCDC replaced the older Rabin fingerprint chunker inside the in-house backup agent; throughput on modern cores jumped and the boundary-shift resilience on small inserts stayed effectively identical.", "decision", "technical", False,
     [("FastCDC", "algorithm"), ("Rabin", "algorithm"), ("in-house backup agent", "project")],
     [("FastCDC", "Rabin", "REPLACES")],
     "which content-defined chunker replaced Rabin fingerprinting in the in-house agent and what improved",
     "fastcdc rabin fingerprint chunker throughput boundary shift insert"),
    # --- 15 ---
    ("BuzHash drives the rolling-window chunker in the legacy ingest path; we keep it because the existing deduplication index is keyed on BuzHash chunk boundaries and a recut would force a full rewrite of ten terabytes.", "preference", "technical", False,
     [("BuzHash", "algorithm"), ("rolling-window chunker", "pattern"), ("legacy ingest", "project")],
     [("BuzHash", "rolling-window chunker", "USES")],
     "why did the legacy ingest path stay on BuzHash instead of moving to a modern chunker",
     "buzhash rolling window chunker legacy ingest dedup index rewrite"),
    # --- 16 ---
    ("Deduplication ratios on the nightly database dumps landed near nine to one after we moved to content-defined chunking; block-aligned chunks were splitting most of the dedup opportunity across boundary shifts.", "milestone", "technical", False,
     [("content-defined chunking", "pattern"), ("block-aligned chunks", "pattern"), ("database dumps", "concept")],
     [("content-defined chunking", "block-aligned chunks", "REPLACES")],
     "which chunker change unlocked the nine-to-one dedup ratio on the nightly database dumps",
     "content defined chunking block aligned dedup database dump ratio"),
    # --- 17 ---
    ("The restic repository on Wasabi runs in object-lock governance mode for fourteen days; accidental prune commands cannot remove packs inside the lock window even with root credentials on the bucket.", "decision", "technical", False,
     [("restic", "tool"), ("Wasabi", "service"), ("object-lock", "pattern"), ("governance mode", "config")],
     [("restic", "object-lock", "USES")],
     "which Wasabi feature stops an accidental restic prune from deleting pack files within the retention window",
     "restic wasabi object lock governance immutable pack prune window"),
    # --- 18 ---
    ("Retention policy across the backup estate follows 3-2-1: three copies of each dataset, on two media types, with one copy offsite; the offsite leg has been S3 Glacier Deep Archive since the last audit review.", "reference", "technical", False,
     [("3-2-1", "pattern"), ("S3 Glacier Deep Archive", "service")],
     [],
     "what retention rule governs the backup estate and where does the offsite copy land",
     "3 2 1 rule retention backup glacier deep archive offsite copy"),
    # --- 19 ---
    ("Pull-mode backups from a hardened collector replaced the previous push-from-server model; production hosts hold no credentials to the backup repo, so a server takeover cannot encrypt or delete the history.", "decision", "technical", False,
     [("Pull-mode", "pattern"), ("push-from-server", "pattern"), ("hardened collector", "platform")],
     [("Pull-mode", "push-from-server", "REPLACES")],
     "which backup topology replaced the push-from-server model and what attack class does it shut down",
     "pull push backup hardened collector credential ransomware takeover"),
    # --- 20 ---
    ("The air-gapped tape leg runs weekly: a rotation of LTO-9 cartridges gets dumped via Bacula to a caddy that physically disconnects from the network afterward and rides a courier to a bank vault.", "architecture", "technical", False,
     [("LTO-9", "infrastructure"), ("Bacula", "tool"), ("bank vault", "place"), ("air-gapped tape", "pattern")],
     [("Bacula", "LTO-9", "USES")],
     "how does the air-gapped tape leg keep physical separation between the backup media and the network",
     "lto 9 bacula tape vault air gap courier caddy weekly rotation"),
    # --- 21 ---
    ("Ransomware resilience leans on three independent layers: immutable S3 via object-lock, append-only borg over SSH, and the LTO-9 offline rotation; losing any two still leaves a recoverable timeline.", "architecture", "technical", False,
     [("S3", "service"), ("object-lock", "pattern"), ("borg", "tool"), ("LTO-9", "infrastructure")],
     [("borg", "object-lock", "APPLIES_TO")],
     "which three layers back the ransomware resilience plan and what survives if two of them fall",
     "ransomware resilience s3 object lock borg append only lto tape"),
    # --- 22 ---
    ("pg_basebackup went live nightly against the primary Postgres node last sprint and writes a base that the WAL archive stream can replay against; point-in-time recovery to any second within seven days became achievable from this pair.", "milestone", "technical", False,
     [("pg_basebackup", "tool"), ("Postgres", "database"), ("WAL archive", "pattern"), ("point-in-time recovery", "pattern")],
     [("pg_basebackup", "Postgres", "APPLIES_TO")],
     "how does the Postgres backup plan achieve point-in-time recovery down to the second",
     "pg basebackup postgres wal archive pitr point in time recovery"),
    # --- 23 ---
    ("Logical pg_dump still runs once a week alongside pg_basebackup; the dump survives a format change that would break a physical restore and is the disaster-recovery backstop for a corrupted data directory.", "preference", "technical", False,
     [("pg_dump", "tool"), ("pg_basebackup", "tool"), ("data directory", "concept")],
     [],
     "why does the weekly pg_dump still run when pg_basebackup already covers nightly physical backups",
     "pg dump logical pg basebackup physical format corrupt directory"),
    # --- 24 ---
    ("Percona XtraBackup handles the MySQL fleet because it takes a non-blocking hot backup off a running InnoDB instance; mysqldump was retired after the primary stopped fitting in the maintenance window.", "decision", "technical", False,
     [("Percona XtraBackup", "tool"), ("mysqldump", "tool"), ("InnoDB", "technology"), ("MySQL", "database")],
     [("Percona XtraBackup", "mysqldump", "REPLACES")],
     "which MySQL backup tool replaced mysqldump and why did the old one stop working",
     "percona xtrabackup mysqldump innodb mysql hot backup maintenance window"),
    # --- 25 ---
    ("mongodump runs against a hidden secondary in the replica set so the primary's working set never flushes for the dump; the hidden member is otherwise non-voting and exists purely for this job.", "architecture", "technical", False,
     [("mongodump", "tool"), ("hidden secondary", "pattern"), ("replica set", "pattern"), ("primary", "concept")],
     [("mongodump", "hidden secondary", "USES")],
     "which MongoDB topology keeps mongodump from disturbing the primary's working set",
     "mongodump hidden secondary replica set primary working set mongo"),
    # --- 26 ---
    ("Velero backs up the production Kubernetes cluster to a dedicated object store with restic integration for PVC contents; the schedule covers hourly cluster-state and four-hourly persistent volume snapshots.", "architecture", "technical", False,
     [("Velero", "tool"), ("Kubernetes", "platform"), ("restic", "tool"), ("PVC", "concept")],
     [("Velero", "restic", "USES")],
     "how does Velero split cluster-state backups from persistent-volume contents on the production cluster",
     "velero kubernetes restic pvc object store schedule cluster state"),
    # --- 27 ---
    ("Velero restore testing runs in an isolated namespace every Sunday; a synthetic app is torn down, restored from the previous night's snapshot, and a smoke suite asserts the data came back intact.", "milestone", "technical", False,
     [("Velero", "tool"), ("isolated namespace", "pattern"), ("smoke suite", "concept")],
     [],
     "how does the team validate that Velero restores actually work end-to-end every week",
     "velero restore test namespace sunday synthetic smoke suite weekly"),
    # --- 28 ---
    ("ZFS snapshots are atomic at the pool level and cost nothing until divergence; we rely on this to take a pre-deploy snapshot of the database dataset before any schema migration lands on the primary.", "fact", "technical", False,
     [("ZFS", "technology"), ("pre-deploy snapshot", "pattern"), ("schema migration", "concept")],
     [("ZFS", "pre-deploy snapshot", "USES")],
     "which cheap ZFS primitive protects the database dataset before a schema migration",
     "zfs atomic snapshot pool pre deploy schema migration database"),
    # --- 29 ---
    ("Btrfs send piped into ssh replaced plain rsync between the two home-lab NAS boxes; the send stream carries block-level diffs and the receiver reconstructs an identical read-only subvolume.", "decision", "technical", False,
     [("Btrfs send", "command"), ("rsync", "tool"), ("read-only subvolume", "pattern")],
     [("Btrfs send", "rsync", "REPLACES")],
     "which Btrfs replication primitive replaced rsync between the two home-lab NAS boxes",
     "btrfs send ssh rsync nas home lab replication subvolume block diff"),
    # --- 30 ---
    ("Hardware token unlock for the restic passphrase broke on the laptop after a firmware update; rolled back to a file-based keyfile in an encrypted vault while the udev quirk ships upstream.", "problem", "technical", False,
     [("restic", "tool"), ("Hardware token", "pattern"), ("udev", "technology"), ("keyfile", "pattern")],
     [("keyfile", "Hardware token", "REPLACES")],
     "why did the restic laptop unlock move from a hardware token back to a file-based keyfile",
     "restic hardware token firmware udev keyfile vault laptop unlock"),
    # --- 31 ---
    ("Immutable repositories on the backup NAS are enforced at the filesystem level with ZFS snapshots plus a cron that clears the delete bit on new files; a rogue admin still cannot mutate yesterday's backup.", "architecture", "technical", False,
     [("ZFS", "technology"), ("Immutable repositories", "pattern"), ("delete bit", "concept"), ("cron", "tool")],
     [("ZFS", "Immutable repositories", "USES")],
     "how does the backup NAS enforce immutability so a rogue admin cannot rewrite yesterday's backup",
     "immutable repository zfs snapshot delete bit cron admin rogue nas"),
    # --- 32 ---
    ("The 3-2-1-1-0 extension adds one offline copy and zero errors to the baseline rule; we adopted it last quarter after the insurance audit flagged the lack of a verified-clean check.", "decision", "technical", False,
     [("3-2-1-1-0", "pattern"), ("insurance audit", "concept"), ("verified-clean", "pattern")],
     [],
     "which retention-rule extension replaced 3-2-1 after the insurance audit and what did it add",
     "3 2 1 1 0 retention rule insurance audit verified clean offline"),
    # --- 33 ---
    ("Kopia's maintenance job is scheduled outside business hours through a dedicated cron entry; the job runs Sunday 03:00 on the collector and a lock file coordinates against the nightly snapshot pipeline so the NAS never sees both at once.", "architecture", "technical", False,
     [("Kopia", "tool"), ("maintenance job", "pattern"), ("NAS", "platform"), ("Sunday 03:00", "config")],
     [("Kopia", "maintenance job", "USES")],
     "how does the Kopia maintenance job avoid colliding with the nightly snapshot pipeline on the NAS",
     "kopia maintenance job cron sunday collector lock file nas pipeline"),
    # --- 34 ---
    ("Repository check on the borg archive runs with --verify-data once per month; it reads every chunk and confirms the stored hash, which caught a silent bitrot on a cold drive before the next restore needed it.", "fact", "technical", False,
     [("borg", "tool"), ("--verify-data", "config"), ("bitrot", "concept")],
     [("borg", "--verify-data", "USES")],
     "which borg command catches bitrot in cold chunks before a real restore needs them",
     "borg verify data repository check bitrot cold drive monthly"),
    # --- 35 ---
    ("A Backblaze B2 Application Key scoped to a single bucket with write-only permissions backs the laptop fleet; a stolen laptop cannot list or delete prior archives, only append new ones.", "milestone", "technical", False,
     [("Backblaze B2", "service"), ("Application Key", "concept"), ("write-only permissions", "pattern")],
     [("Application Key", "Backblaze B2", "APPLIES_TO")],
     "which B2 credential shape stops a stolen laptop from deleting prior archives",
     "backblaze b2 application key write only laptop fleet bucket scope"),
    # --- 36 ---
    ("Snapshot consistency for the KVM guests goes through libvirt's qemu-agent freeze hook; the guest filesystem quiesces, the host takes the LVM thin snapshot, and the guest thaws within a couple hundred milliseconds.", "architecture", "technical", False,
     [("KVM", "technology"), ("libvirt", "tool"), ("qemu-agent", "tool"), ("LVM thin snapshot", "pattern")],
     [("qemu-agent", "KVM", "APPLIES_TO")],
     "how do KVM guests get filesystem-consistent snapshots with only a brief freeze window",
     "kvm libvirt qemu agent freeze lvm thin snapshot guest quiesce"),
    # --- 37 ---
    ("VSS writer for the SQL Server instance failed after a Windows Update bumped the SqlWriter service out of the VSS provider list; re-registering the provider restored application-consistent snapshots.", "problem", "technical", False,
     [("VSS", "api"), ("SQL Server", "database"), ("SqlWriter", "service"), ("Windows Update", "event")],
     [("VSS", "SqlWriter", "USES")],
     "how did the SQL Server VSS writer break after a Windows Update and what restored it",
     "vss sql server sqlwriter windows update provider register snapshot"),
    # --- 38 ---
    ("Retention on the restic repo prunes hourlies after 48 hours, dailies after 30 days, weeklies after a year, and keeps monthlies forever; the forget command runs from the collector and never from a client.", "reference", "technical", False,
     [("restic", "tool"), ("forget", "command"), ("collector", "platform")],
     [("forget", "restic", "APPLIES_TO")],
     "what retention tiers apply to the restic repository and which host runs the forget command",
     "restic forget retention hourly daily weekly monthly collector prune"),
    # --- 39 ---
    ("APFS local snapshots on macOS fill the gap when Time Machine cannot reach the Synology target; the daemon keeps 24 hours of hourlies locally and fuses them into the offsite history once the link returns.", "fact", "technical", False,
     [("APFS", "technology"), ("Time Machine", "tool"), ("Synology", "platform"), ("daemon", "service")],
     [("APFS", "Time Machine", "APPLIES_TO")],
     "how does macOS keep a backup history when the office link to the Synology is down",
     "apfs local snapshot time machine synology mac offline gap daemon"),
    # --- 40 ---
    ("The monthly restore drill picks one random workload per service tier and recovers it into a scratch environment; failures in Q2 flagged a broken Velero resource-filter regex that silently skipped the ingress objects.", "milestone", "technical", False,
     [("restore drill", "pattern"), ("Velero", "tool"), ("ingress objects", "concept"), ("Q2", "date")],
     [("Velero", "ingress objects", "APPLIES_TO")],
     "which monthly exercise caught the Velero resource-filter regex that was dropping ingress objects",
     "restore drill velero ingress regex scratch environment monthly q2"),
    # --- 41 ---
    ("Deduplication across the fleet deliberately does not cross the security boundary between tenants; each tenant gets its own restic repository even though global dedup would have cut cost, because cross-tenant chunk knowledge leaks file sizes.", "decision", "technical", False,
     [("restic", "tool"), ("tenant", "concept"), ("Deduplication", "pattern"), ("security boundary", "pattern")],
     [("Deduplication", "security boundary", "APPLIES_TO")],
     "why does each tenant get a separate restic repository instead of sharing a global deduplicated store",
     "restic dedup tenant security boundary chunk leak file size isolate"),
    # --- 42 ---
    ("Wasabi egress fees are zero when the restore rate stays under the stored-data baseline, which made it cheaper than S3 Standard for the warm-archive tier; the cost model broke even around eighteen months of retention.", "fact", "technical", False,
     [("Wasabi", "service"), ("S3 Standard", "service"), ("warm-archive", "pattern")],
     [("Wasabi", "S3 Standard", "REPLACES")],
     "at what retention horizon did Wasabi beat S3 Standard on cost for the warm-archive tier",
     "wasabi s3 standard egress warm archive cost retention eighteen month"),
    # --- 43. noise ---
    ("The hallway poster someone printed of a cat in a spacesuit has been realigned every Tuesday morning for six weeks by an unknown colleague.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Bacula director replaced Amanda on the tape rotation after Amanda's catalog corruption ate a quarterly backup set; Bacula's Postgres-backed catalog survives crashes that previously required a manual replay of bconsole commands.", "decision", "technical", False,
     [("Bacula", "tool"), ("Amanda", "tool"), ("Postgres", "database"), ("bconsole", "tool")],
     [("Bacula", "Amanda", "REPLACES")],
     "which tape backup system replaced Amanda and what catalog reliability gap drove the move",
     "bacula amanda tape director postgres catalog corruption bconsole"),
    # --- 45 ---
    ("The backup compliance reference lives in the internal wiki page titled Backup & Recovery Standards; it codifies RPO of fifteen minutes for tier-one data and RTO of four hours, with the 3-2-1 rule baked in.", "reference", "technical", False,
     [("Backup & Recovery Standards", "publication"), ("RPO", "concept"), ("RTO", "concept"), ("3-2-1", "pattern")],
     [],
     "which internal document defines the RPO and RTO targets alongside the 3-2-1 rule",
     "backup recovery standards rpo rto 3 2 1 tier one compliance wiki"),
    # --- 46 ---
    ("Encryption keys for the borg repos are managed by a Vault transit mount; a nightly job unseals the key just long enough to derive the repokey and never writes the raw secret to disk on the collector.", "architecture", "technical", False,
     [("borg", "tool"), ("Vault", "tool"), ("transit mount", "pattern"), ("repokey", "concept")],
     [("borg", "Vault", "USES")],
     "how does the collector derive the borg repokey each night without persisting the raw secret",
     "borg vault transit mount repokey collector unseal key nightly"),
    # --- 47 ---
    ("Snapshot-based backups of the GitLab omnibus instance proved incomplete because the bundled Redis AOF was not flushed; added a gitlab-rake gitlab:backup:create job that the snapshot wraps to get a clean state.", "problem", "technical", False,
     [("GitLab omnibus", "service"), ("Redis", "database"), ("AOF", "pattern"), ("gitlab-rake", "tool")],
     [("gitlab-rake", "GitLab omnibus", "APPLIES_TO")],
     "why did snapshot-only backups of GitLab omnibus miss state and what job now wraps them",
     "gitlab omnibus redis aof snapshot gitlab rake backup create flush"),
    # --- 48 ---
    ("The 2026 quarterly review marked the first clean DR exercise in three years: the tier-one stack stood up in the DR site from restic plus Velero in under two hours, inside the documented RTO.", "milestone", "technical", False,
     [("DR exercise", "event"), ("restic", "tool"), ("Velero", "tool"), ("RTO", "concept"), ("2026 quarterly review", "date")],
     [("Velero", "restic", "USES")],
     "which DR exercise first hit the documented RTO target and which tools carried the recovery",
     "dr exercise quarterly review restic velero rto two hour clean 2026"),
    # --- 49 ---
    ("Offsite transport for the LTO-9 tapes uses a bonded courier with a tamper-evident bag; chain-of-custody scans happen at both ends and the vault barcodes feed into the asset tracker on the same evening.", "reference", "technical", False,
     [("LTO-9", "infrastructure"), ("tamper-evident bag", "pattern"), ("asset tracker", "tool"), ("bonded courier", "service")],
     [],
     "how is the chain of custody tracked for the LTO-9 tapes between the office and the vault",
     "lto 9 bonded courier tamper evident bag chain custody asset tracker"),
    # --- 50 ---
    ("Velero plugin for CSI snapshots took over PVC protection from the older restic-only flow; CSI native snapshots complete in seconds on the ceph-csi driver while the restic path still covers non-CSI volumes.", "architecture", "technical", False,
     [("Velero", "tool"), ("CSI", "api"), ("PVC", "concept"), ("ceph-csi", "tool"), ("restic", "tool")],
     [("CSI", "restic", "REPLACES"), ("Velero", "CSI", "USES")],
     "how did the Velero plugin split PVC protection between CSI snapshots and the older restic path",
     "velero csi snapshot pvc ceph csi restic plugin driver volume"),
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
