"""One-off emitter for shared-base batch-243 — technical domain (distributed consensus and coordination: Paxos, Raft, Zab, VR, PBFT, HotStuff, IBFT, Tendermint, vector/Lamport/HLC clocks, CRDTs, gossip, 2PC/3PC, saga).

Writes 50 rows to data/v2/shared/batch_243.tmp.jsonl with ids shared-12101..12150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_243.tmp.jsonl"
ID_OFFSET = 12100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Replaced the single-decree Paxos acceptor loop with Multi-Paxos on the metadata service; a stable leader amortises Phase 1 across a long run of commands and halves commit latency under steady load.", "decision", "technical", False,
     [("Paxos", "algorithm"), ("Multi-Paxos", "algorithm"), ("metadata service", "service"), ("Phase 1", "concept")],
     [("Multi-Paxos", "Paxos", "REPLACES")],
     "which consensus variant replaced single-decree Paxos on the metadata service and which phase got amortised",
     "multi paxos single decree phase 1 leader amortise metadata latency"),
    # --- 2 ---
    ("Control plane moved off Zab onto Raft because Diego Ongaro's understandability pitch made on-call rotations less fragile; the old ZooKeeper ensemble survives only for legacy lock recipes.", "decision", "technical", False,
     [("Zab", "algorithm"), ("Raft", "algorithm"), ("ZooKeeper", "service"), ("Diego Ongaro", "person"), ("Control plane", "service")],
     [("Raft", "Zab", "REPLACES"), ("ZooKeeper", "Zab", "USES")],
     "which consensus algorithm replaced Zab for the control plane and whose design pitch drove the switch",
     "raft zab zookeeper ongaro control plane understandability on call"),
    # --- 3 ---
    ("Quorum math for the replicated log is N/2+1 acceptors for a five-node CFT cluster; the BFT variant on the validator ring needs 2f+1 from 3f+1 which pushes the minimum to four nodes for one fault.", "fact", "technical", False,
     [("Quorum", "concept"), ("CFT", "concept"), ("BFT", "concept"), ("replicated log", "pattern"), ("validator ring", "service")],
     [],
     "how does the quorum requirement differ between the CFT replicated log and the BFT validator ring",
     "quorum majority n/2+1 2f+1 3f+1 cft bft replicate log validator"),
    # --- 4 ---
    ("Split-brain killed the primary-replica pair during the cross-AZ partition; we now require a fencing token minted by the lease server before any write hits the storage volume.", "problem", "technical", False,
     [("Split-brain", "concept"), ("primary-replica", "pattern"), ("fencing token", "pattern"), ("lease server", "service"), ("cross-AZ partition", "event")],
     [("fencing token", "Split-brain", "FIXES")],
     "which token mechanism did we add to the lease path after a cross-AZ split-brain corrupted storage",
     "split brain fence token lease server primary replica partition az"),
    # --- 5 ---
    ("Leader election in the coordination layer is Raft PreVote with CheckQuorum on; a flapping follower that briefly partitions no longer bumps the term and churns the cluster for seconds at a time.", "architecture", "technical", False,
     [("Raft PreVote", "pattern"), ("CheckQuorum", "pattern"), ("coordination layer", "service"), ("term", "concept")],
     [],
     "which two Raft options calm leader-election churn when a follower flaps in and out of partition",
     "raft prevote check quorum leader election flap follower term"),
    # --- 6 ---
    ("Log replication through the Raft AppendEntries path batches up to 128 entries per RPC; the old one-entry-per-RPC baseline capped throughput at around 900 commits a second on the 3-node etcd pool.", "milestone", "technical", False,
     [("Raft", "algorithm"), ("AppendEntries", "api"), ("etcd", "service"), ("RPC", "protocol")],
     [("AppendEntries", "Raft", "USES")],
     "which batching knob on AppendEntries broke the 900 commit per second ceiling for the etcd pool",
     "raft append entries batch rpc etcd throughput commit second"),
    # --- 7 ---
    ("Membership changes on the consensus group use Raft joint-consensus (Cold,new then Cnew); the single-server add-remove shortcut was banned after a double-failure window in the 2025 incident.", "decision", "technical", False,
     [("Raft", "algorithm"), ("joint-consensus", "pattern"), ("single-server add-remove", "pattern"), ("2025 incident", "event")],
     [("joint-consensus", "single-server add-remove", "REPLACES")],
     "which membership-change protocol replaced single-server add-remove after the 2025 double-failure incident",
     "raft joint consensus membership cold new single server add remove"),
    # --- 8 ---
    ("Vector clocks on the shopping-cart replicas detect concurrent updates between regions; Lamport timestamps weren't enough because a total order hid real concurrency that should have triggered a merge prompt.", "architecture", "technical", False,
     [("Vector clocks", "algorithm"), ("Lamport timestamps", "algorithm"), ("shopping-cart", "service"), ("merge prompt", "pattern")],
     [("Vector clocks", "Lamport timestamps", "REPLACES")],
     "which clock scheme replaced Lamport timestamps on the shopping-cart and why did total order fail",
     "vector clock lamport timestamp shopping cart concurrent merge region"),
    # --- 9 ---
    ("Hybrid logical clocks anchor the global transaction order in the CockroachDB fork; an HLC ticks within a bounded skew of wall-clock NTP so cross-region reads stay linearisable without a TrueTime box.", "architecture", "technical", False,
     [("HLC", "algorithm"), ("CockroachDB", "service"), ("NTP", "protocol"), ("TrueTime", "service"), ("linearisable", "concept")],
     [("HLC", "TrueTime", "REPLACES")],
     "how does the CockroachDB fork stay linearisable across regions without a TrueTime hardware path",
     "hybrid logical clock hlc cockroach ntp truetime linearisable region"),
    # --- 10. noise ---
    ("The office coffee machine finally learned how to pronounce oat milk on the first try and the morning queue dropped by at least two people.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Fast Paxos was evaluated for the write path and rejected; the reduced round-trip helps only under low contention and our workload conflicts enough that fallback to classic Paxos would dominate.", "decision", "technical", False,
     [("Fast Paxos", "algorithm"), ("classic Paxos", "algorithm"), ("write path", "service")],
     [("classic Paxos", "Fast Paxos", "PREFERS")],
     "why did the write path stay on classic Paxos instead of switching to Fast Paxos",
     "fast paxos classic contention write path round trip reject fallback"),
    # --- 12 ---
    ("Viewstamped Replication was the source material but we shipped Raft; the view-change protocol in VR maps one-to-one onto Raft's leader election which made the porting exercise a rename job.", "reference", "technical", False,
     [("Viewstamped Replication", "algorithm"), ("Raft", "algorithm"), ("view-change", "concept")],
     [("Raft", "Viewstamped Replication", "USES")],
     "which older protocol does Raft's leader election mirror and what did the port mostly amount to",
     "viewstamped replication vr raft view change leader election port"),
    # --- 13 ---
    ("PBFT runs the validator quorum on the permissioned ledger; the three-phase pre-prepare, prepare, commit flow tolerates f Byzantine nodes out of 3f+1 which is the quorum sizing we budget for.", "architecture", "technical", False,
     [("PBFT", "algorithm"), ("permissioned ledger", "service"), ("pre-prepare", "concept"), ("prepare", "concept"), ("commit", "concept")],
     [("PBFT", "permissioned ledger", "APPLIES_TO")],
     "which three-phase BFT flow runs the permissioned ledger validators and what f-of-3f+1 ratio does it tolerate",
     "pbft pre prepare commit byzantine 3f+1 permissioned ledger validator"),
    # --- 14 ---
    ("Tendermint BFT finalises every block with a single commit; the instant finality property is why the chain team picked it over a Nakamoto longest-chain design for the rollup's settlement layer.", "decision", "technical", False,
     [("Tendermint BFT", "algorithm"), ("Nakamoto", "algorithm"), ("instant finality", "concept"), ("rollup", "service"), ("settlement layer", "service")],
     [("Tendermint BFT", "Nakamoto", "PREFERS")],
     "which BFT property sold Tendermint over a Nakamoto-style chain for the rollup settlement layer",
     "tendermint nakamoto instant finality rollup settlement longest chain"),
    # --- 15 ---
    ("HotStuff's linear view-change cost is why the permissioned network upgraded from PBFT; the pipelined three-chain rule gives the same safety with O(n) messages per view instead of O(n^2).", "milestone", "technical", False,
     [("HotStuff", "algorithm"), ("PBFT", "algorithm"), ("three-chain rule", "concept"), ("permissioned network", "service")],
     [("HotStuff", "PBFT", "REPLACES")],
     "which HotStuff property cut the per-view message cost from O(n^2) to O(n) against PBFT",
     "hotstuff pbft view change linear three chain pipeline o(n) message"),
    # --- 16 ---
    ("IBFT 2.0 powers the enterprise Ethereum sidechain; the round-change proof attached to every new round stopped the stuck-view pathology we saw in the original IBFT under a partial partition.", "problem", "technical", False,
     [("IBFT 2.0", "algorithm"), ("IBFT", "algorithm"), ("enterprise Ethereum", "service"), ("round-change proof", "concept"), ("partial partition", "event")],
     [("IBFT 2.0", "IBFT", "REPLACES")],
     "which IBFT 2.0 feature fixed the stuck-view pathology that original IBFT hit under a partial partition",
     "ibft 2.0 enterprise ethereum round change proof stuck view partition"),
    # --- 17 ---
    ("CFT protocols assume crashed-but-honest nodes; BFT assumes actively malicious peers, so the gossip layer on the public network runs with signed messages even though the internal orchestrator trusts its CFT Raft.", "reference", "technical", False,
     [("CFT", "concept"), ("BFT", "concept"), ("gossip layer", "service"), ("public network", "service"), ("Raft", "algorithm"), ("orchestrator", "service")],
     [],
     "how does the threat model of CFT differ from BFT and which layer of ours runs which flavour",
     "cft bft threat model crash fault byzantine gossip raft signed"),
    # --- 18 ---
    ("Lamport clocks still tag log records in the audit trail; a happens-before edge between two records is the only ordering the auditor needs, and wall-clock drift on the audit nodes ruled out NTP-only order.", "fact", "technical", False,
     [("Lamport clocks", "algorithm"), ("audit trail", "service"), ("NTP", "protocol"), ("happens-before", "concept")],
     [],
     "which clock scheme tags audit-trail records and why wasn't wall-clock NTP ordering good enough",
     "lamport clock audit trail ntp happens before wall clock drift"),
    # --- 19 ---
    ("CRDT choice for the presence service is an OR-set; the earlier G-counter kept mispresenting a user as online after a brief reconnect because adds without a matching remove monotonically accumulate.", "decision", "technical", False,
     [("OR-set", "algorithm"), ("G-counter", "algorithm"), ("CRDT", "concept"), ("presence service", "service")],
     [("OR-set", "G-counter", "REPLACES")],
     "which CRDT replaced the G-counter in presence and what staleness bug motivated the swap",
     "or set g counter presence crdt reconnect stale online monotonic"),
    # --- 20 ---
    ("PN-counter tracks the live-viewer tally on the stream service so increments and decrements both converge; the plain G-counter can't model a viewer leaving without a compensating counter pair.", "fact", "technical", False,
     [("PN-counter", "algorithm"), ("G-counter", "algorithm"), ("stream service", "service")],
     [("PN-counter", "G-counter", "IMPROVES_ON")],
     "which CRDT tracks live-viewer tallies with decrements and why does G-counter fall short",
     "pn counter g counter stream viewer increment decrement converge"),
    # --- 21 ---
    ("Collaborative-text editing on the document platform uses an RGA; LWW-based merges dropped concurrent inserts that landed at the same cursor, which showed up as silent keystroke loss in QA traces.", "problem", "technical", False,
     [("RGA", "algorithm"), ("LWW", "algorithm"), ("document platform", "service"), ("QA traces", "publication")],
     [("RGA", "LWW", "REPLACES")],
     "which text CRDT replaced LWW on the document platform after concurrent inserts silently dropped",
     "rga lww document crdt concurrent insert cursor keystroke loss"),
    # --- 22 ---
    ("State-based CRDTs ship full merge payloads on every sync; the mobile client moved to op-based delta-CRDTs because the 3G path couldn't afford a full OR-set every reconnect.", "decision", "technical", False,
     [("State-based CRDTs", "concept"), ("op-based delta-CRDTs", "concept"), ("OR-set", "algorithm"), ("mobile client", "service")],
     [("op-based delta-CRDTs", "State-based CRDTs", "REPLACES")],
     "which CRDT shipping model replaced state-based payloads on the mobile client and why",
     "state based op based delta crdt mobile 3g or set payload"),
    # --- 23 ---
    ("Gossip in the cluster membership layer runs SWIM with suspicion timers tuned per datacentre; Serf's implementation was the starting point but the suspect-propagation rate was retuned after the 2026 flap storm.", "architecture", "technical", False,
     [("SWIM", "algorithm"), ("Serf", "library"), ("cluster membership", "service"), ("2026 flap storm", "event")],
     [("SWIM", "Serf", "USES")],
     "which gossip algorithm runs the cluster membership layer and which library seeded the implementation",
     "swim gossip serf suspicion membership flap storm datacentre"),
    # --- 24 ---
    ("HashiCorp Memberlist is embedded in the sidecar agent; the push-pull anti-entropy round every thirty seconds fills gaps that the UDP ping path misses under packet loss above two percent.", "fact", "technical", False,
     [("HashiCorp Memberlist", "library"), ("sidecar agent", "service"), ("push-pull anti-entropy", "pattern"), ("UDP", "protocol")],
     [],
     "how does Memberlist in the sidecar agent recover from UDP ping loss above two percent",
     "hashicorp memberlist sidecar push pull anti entropy udp ping loss"),
    # --- 25 ---
    ("Anti-entropy on the replica store uses Merkle trees over 4K-row chunks; a diff walk converges two partitioned replicas with bandwidth proportional to the drift rather than the full dataset.", "architecture", "technical", False,
     [("Anti-entropy", "pattern"), ("Merkle trees", "algorithm"), ("replica store", "service")],
     [("Merkle trees", "Anti-entropy", "USES")],
     "which data structure drives anti-entropy on the replica store so bandwidth tracks drift instead of size",
     "anti entropy merkle tree replica 4k chunk diff walk bandwidth"),
    # --- 26 ---
    ("Saga pattern replaced the cross-service 2PC on the checkout flow; each step now has a compensating action so a credit-card decline rolls back inventory and rewards without a blocking coordinator.", "decision", "technical", False,
     [("Saga pattern", "pattern"), ("2PC", "algorithm"), ("checkout flow", "service"), ("inventory", "service"), ("rewards", "service")],
     [("Saga pattern", "2PC", "REPLACES")],
     "which orchestration pattern replaced 2PC on the checkout flow and how does it unwind a decline",
     "saga 2pc checkout compensating inventory rewards credit card decline"),
    # --- 27 ---
    ("Two-phase commit still runs inside one database between the wallet and ledger tables; the coordinator is the same Postgres process so the classic blocking-on-coordinator-failure argument doesn't bite here.", "fact", "technical", False,
     [("Two-phase commit", "algorithm"), ("wallet", "service"), ("ledger", "service"), ("Postgres", "database")],
     [],
     "why is 2PC still acceptable between the wallet and ledger tables despite its coordinator-failure reputation",
     "2pc wallet ledger postgres coordinator failure single database block"),
    # --- 28 ---
    ("Three-phase commit was prototyped to replace 2PC on the cross-region transfer service but shelved; 3PC's non-blocking claim collapses under network partitions, and Saga already solved the blocking problem for us.", "decision", "technical", False,
     [("Three-phase commit", "algorithm"), ("2PC", "algorithm"), ("Saga", "pattern"), ("cross-region transfer", "service")],
     [("Saga", "Three-phase commit", "PREFERS")],
     "why was the 3PC prototype shelved on the cross-region transfer service",
     "three phase commit 2pc saga cross region transfer partition block"),
    # --- 29 ---
    ("Settled on eventual consistency as the default for the user-profile cache; strong reads route through the primary, and the staleness bound was picked at ninety-five percent under 400 ms after the read-path benchmark.", "decision", "technical", False,
     [("eventual consistency", "concept"), ("user-profile cache", "service"), ("primary", "pattern"), ("staleness bound", "concept")],
     [],
     "which consistency model did we settle on for the user-profile cache and what staleness bound got picked",
     "eventual consistency profile cache primary strong read staleness 400ms"),
    # --- 30 ---
    ("Strict serialisable isolation is enforced on the order-book service through a single-writer Raft group; reads go to the leader's read-index so no follower can serve a stale view during leader churn.", "architecture", "technical", False,
     [("Strict serialisable", "concept"), ("order-book service", "service"), ("Raft", "algorithm"), ("read-index", "api")],
     [("order-book service", "Raft", "USES")],
     "which Raft read path enforces strict serialisable reads on the order-book service through leader churn",
     "strict serialisable order book raft read index leader follower stale"),
    # --- 31 ---
    ("Shipped causal consistency across the social-graph replicas using a dependency vector piggybacked on each write; a like that depends on a post now only becomes visible once the post has landed on the reading replica.", "milestone", "technical", False,
     [("causal consistency", "concept"), ("social-graph", "service"), ("dependency vector", "pattern")],
     [],
     "how does the social-graph keep causal order between a post and a dependent like across replicas",
     "causal consistency social graph dependency vector post like replica"),
    # --- 32 ---
    ("Leader leases on the Raft group are bounded by a 500 ms clock-skew budget; a leader that can't refresh its lease before expiry has to step down even if it still sees a quorum of heartbeats.", "fact", "technical", False,
     [("Leader leases", "pattern"), ("Raft", "algorithm"), ("heartbeats", "concept")],
     [],
     "what clock-skew budget bounds the Raft leader lease and what does an expired lease force the leader to do",
     "raft leader lease clock skew 500ms expire step down heartbeat"),
    # --- 33 ---
    ("Fencing tokens on the blob-storage client are monotonic 64-bit integers issued by the lease server; any write with a token older than the storage node's high-water mark is rejected at the storage API.", "architecture", "technical", False,
     [("Fencing tokens", "pattern"), ("blob-storage", "service"), ("lease server", "service"), ("storage API", "api")],
     [],
     "how does the blob-storage client use fencing tokens to reject writes from stale lease holders",
     "fencing token blob storage lease monotonic 64 bit high water reject"),
    # --- 34 ---
    ("Quorum intersection is the invariant that makes Paxos safe; every prepare quorum overlaps every accept quorum in at least one node so a prior chosen value cannot be lost.", "reference", "technical", False,
     [("Quorum intersection", "concept"), ("Paxos", "algorithm"), ("prepare quorum", "concept"), ("accept quorum", "concept")],
     [],
     "which quorum invariant underlies Paxos safety and what does it guarantee about previously-chosen values",
     "quorum intersection paxos prepare accept safety chosen value overlap"),
    # --- 35 ---
    ("Log compaction on the Raft group uses periodic snapshots at 8 MB intervals; followers that fall behind beyond the retained tail get shipped the snapshot over InstallSnapshot rather than replaying entries.", "fact", "technical", False,
     [("Raft", "algorithm"), ("Log compaction", "pattern"), ("snapshots", "pattern"), ("InstallSnapshot", "api")],
     [("InstallSnapshot", "Raft", "USES")],
     "how does the Raft group recover followers that fall behind past the retained log tail",
     "raft log compaction snapshot install snapshot follower behind 8mb"),
    # --- 36 ---
    ("Witness replicas on the stretch cluster vote on consensus but don't hold state; adding one witness lets the cluster survive a datacentre loss without doubling storage footprint.", "architecture", "technical", False,
     [("Witness replicas", "pattern"), ("stretch cluster", "service"), ("datacentre", "place")],
     [],
     "which replica flavour lets the stretch cluster survive a datacentre loss without doubling storage",
     "witness replica stretch cluster vote datacentre loss storage footprint"),
    # --- 37 ---
    ("Epoch numbers on the Zab ensemble prevent a recovered leader from overwriting committed history; an epoch bump is the atomic signal that a new primary has claimed the ensemble and all writes rebase.", "reference", "technical", False,
     [("Zab", "algorithm"), ("Epoch numbers", "concept"), ("ensemble", "service"), ("primary", "pattern")],
     [],
     "how do Zab epoch numbers prevent a recovered leader from overwriting committed history",
     "zab epoch ensemble primary recover committed history overwrite bump"),
    # --- 38 ---
    ("Delivered the milestone that moved the scheduler's config store from ZooKeeper to etcd; the Raft-backed etcd gave us linearisable leases without reimplementing the Zab recipe book.", "milestone", "technical", False,
     [("scheduler", "service"), ("ZooKeeper", "service"), ("etcd", "service"), ("Raft", "algorithm")],
     [("etcd", "ZooKeeper", "REPLACES"), ("etcd", "Raft", "USES")],
     "which migration swapped the scheduler config store onto etcd and which property did it preserve",
     "scheduler config zookeeper etcd raft linearisable lease migrate"),
    # --- 39 ---
    ("Heartbeat interval on the consensus layer prefers 50 ms over 200 ms because the 99th-percentile failover time on the control plane dropped from 1.2 s to 280 ms in the chaos drills.", "preference", "technical", False,
     [("Heartbeat interval", "config"), ("consensus layer", "service"), ("control plane", "service"), ("chaos drills", "method")],
     [],
     "why did the consensus layer settle on a 50 ms heartbeat over the prior 200 ms value",
     "heartbeat 50ms 200ms consensus failover chaos drill 99th percentile"),
    # --- 40 ---
    ("Preference is to expose consensus internals through a read-only introspection endpoint rather than log scraping; the Raft term, commit index, and leader identity are queryable on /debug/consensus.", "preference", "technical", False,
     [("introspection endpoint", "api"), ("Raft", "algorithm"), ("/debug/consensus", "api")],
     [],
     "how do operators prefer to read Raft internals and what three fields does the endpoint expose",
     "introspection endpoint raft term commit leader debug consensus scrape"),
    # --- 41 ---
    ("Hash-graph alternative to classic BFT was surveyed for the permissioned ledger and passed over; the patent constraints and the single-vendor implementation risk outweighed the throughput case against HotStuff.", "decision", "technical", False,
     [("Hash-graph", "algorithm"), ("HotStuff", "algorithm"), ("permissioned ledger", "service")],
     [("HotStuff", "Hash-graph", "PREFERS")],
     "why did the permissioned ledger stay on HotStuff instead of adopting hash-graph",
     "hash graph hotstuff permissioned ledger patent vendor risk throughput"),
    # --- 42 ---
    ("Commit latency for the Raft group is dominated by fsync on the leader's WAL; switching to group-commit batching with a 5 ms wait window raised throughput four-fold without hurting P99.", "milestone", "technical", False,
     [("Raft", "algorithm"), ("fsync", "api"), ("WAL", "pattern"), ("group-commit batching", "pattern")],
     [("group-commit batching", "Raft", "IMPROVES_ON")],
     "which WAL-fsync optimisation raised Raft commit throughput four-fold without hurting tail latency",
     "raft fsync wal group commit batching latency throughput 5ms window"),
    # --- 43. noise ---
    ("The rooftop garden herbs survived the cold snap because someone wrapped the planters in bubble wrap and nobody has claimed the rescue.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Prefers the term primary-replica over the old master-slave wording across runbooks and metrics; the control-plane dashboards were renamed in the same PR that retired the legacy labels.", "preference", "technical", False,
     [("primary-replica", "pattern"), ("master-slave", "pattern"), ("control-plane", "service"), ("runbook", "publication")],
     [("primary-replica", "master-slave", "REPLACES")],
     "which replica naming convention is preferred across runbooks and dashboards over the legacy wording",
     "primary replica master slave runbook dashboard label rename"),
    # --- 45 ---
    ("Prefer Jepsen-style linearisability tests on every consensus release over ad-hoc property tests; a Jepsen nemesis run catches the split-brain class of bug that our unit tests miss by construction.", "preference", "technical", False,
     [("Jepsen", "tool"), ("linearisability test", "pattern"), ("consensus release", "publication"), ("split-brain", "concept")],
     [("Jepsen", "split-brain", "APPLIES_TO")],
     "which testing tool is preferred on every consensus release and which bug class does it catch",
     "jepsen linearisability consensus release split brain nemesis property"),
    # --- 46 ---
    ("The consensus safety proof references Lamport's 2001 paper Paxos Made Simple rather than The Part-Time Parliament; engineers onboarding hit the older paper last and tended to misread the acceptor role.", "reference", "technical", False,
     [("Paxos Made Simple", "publication"), ("The Part-Time Parliament", "publication"), ("Lamport", "person"), ("acceptor", "concept")],
     [("Paxos Made Simple", "The Part-Time Parliament", "PREFERS")],
     "which Lamport paper does onboarding reference first for the consensus safety proof and why",
     "lamport paxos made simple part time parliament acceptor onboarding"),
    # --- 47 ---
    ("Byzantine fault tolerance on the bridge relays is budgeted for one malicious validator out of four; the 3f+1 sizing is documented in the threat model alongside the staking-deposit slashing rules.", "reference", "technical", False,
     [("Byzantine fault tolerance", "concept"), ("bridge relays", "service"), ("3f+1", "concept"), ("threat model", "publication"), ("slashing", "pattern")],
     [],
     "which BFT sizing does the bridge-relays threat model document and how does it tie to slashing",
     "byzantine fault bridge relay 3f+1 validator threat model slashing"),
    # --- 48 ---
    ("Rolled out randomised election timeouts on the Raft group in the 150 to 300 ms window; a synchronised fleet-wide boot no longer triggers the cascading term-bump we saw on the 2025 cold start and the split-vote storms stopped.", "milestone", "technical", False,
     [("Raft", "algorithm"), ("split-vote", "concept"), ("randomised election timeouts", "pattern"), ("2025 cold start", "event")],
     [("randomised election timeouts", "split-vote", "FIXES")],
     "which Raft timing knob bounds split-vote storms after the 2025 cold-start term-bump cascade",
     "raft split vote randomise election timeout 150 300 ms cold start"),
    # --- 49 ---
    ("Decided to cap vector-clock length at 64 entries on the key-value store by evicting the oldest writer; losing the tail rarely matters because an anti-entropy round resurfaces any dropped causality.", "decision", "technical", False,
     [("vector-clock", "algorithm"), ("key-value store", "service"), ("anti-entropy", "pattern")],
     [("anti-entropy", "vector-clock", "APPLIES_TO")],
     "how does the key-value store bound vector-clock size and recover any causality the eviction drops",
     "vector clock prune key value 64 entry anti entropy causality oldest"),
    # --- 50 ---
    ("Shipped the milestone to replace etcd's Raft with a custom HotStuff pipeline for the L2 sequencer; commit latency held at 40 ms under a 200-node validator set where Raft would have sharded.", "milestone", "technical", False,
     [("etcd", "service"), ("Raft", "algorithm"), ("HotStuff", "algorithm"), ("L2 sequencer", "service")],
     [("HotStuff", "Raft", "REPLACES")],
     "which consensus swap let the L2 sequencer hold 40 ms commit latency at 200 validators",
     "hotstuff raft etcd l2 sequencer 200 validator 40ms commit latency"),
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
