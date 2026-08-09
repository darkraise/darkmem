# Entailment gold — Layer 3 resample sheet

93 premise/hypothesis pairs, in the blind export's own shuffled order. Decide one verdict per item (entailed / contradicted / unsupported) against the rules below -- verbatim excerpts of the labelling rulebook, current as of this sheet's generation -- and name the rule you used. Use only the printed premise: no lookup of any recorded answer, no prior labelling run, no corpus or world knowledge outside this text. Fill in the Verdict and `Rule cited` line under each item, in place, and return this same file.

---

## The three verdicts, and the binary G-D scores on

- **`entailed`** — a competent reader who accepts the premise as true must
  accept the hypothesis as true. Semantic entailment, not lexical overlap
  and not plausibility.
- **`contradicted`** — accepting the premise requires rejecting the
  hypothesis: the premise asserts (directly, or via a rule below) the
  negation of something the hypothesis asserts.
- **`unsupported`** — neither of the above. The premise is compatible with
  the hypothesis but does not establish it.

**Grounded ⇔ `entailed`.** That is the whole binary
(`entailment_gold.GROUNDED_VERDICTS`); `contradicted` and `unsupported`
are both ungrounded. The three-way split is kept because the veto consumer
(doc 08 §4.2) is qualified on precision of the *contradiction* verdict from
this same file — collapsing it to a binary would throw that away.

## General decision procedure

1. **Score the whole hypothesis.** A claim is grounded only if *all* of it
   is entailed. A conjunction with one supported and one unsupported
   conjunct is `unsupported` — partial credit is a scorer policy
   decision that belongs to T2.26, not a labelling one.
2. **Use only the premise.** The corpus world, the labeller's domain
   knowledge, and what is "obviously true" of homelabs are all
   inadmissible. Several pairs are deliberately built so the hypothesis is
   *true in the corpus world* but unsupported by this premise: a judge that scores plausibility instead of
   entailment fails them, by design.
3. **Entailment tolerates rewording, never strengthening.** Synonyms,
   voice, clause order, dropping content (weakening) preserve entailment.
   Adding content, tightening a quantifier, upgrading "a factor" to "the
   cause" break it. Whether *exhaustivity* counts as strengthening depends
   on how the hypothesis carries it — see the **exhaustivity rule** below.
4. **Contradiction requires exclusion, not absence.** If the premise merely
   fails to mention what the hypothesis asserts, that is `unsupported`. It
   is `contradicted` only when the premise (with the named rules below)
   excludes it.

## Edge rulings — cite these by name in rationales

- **Exclusive-slot rule.** A fact stating a single-valued configuration
  slot — a port, a version of one instance, a scrape interval, the bucket
  holding a state file, a token lifetime — states *the* operative value.
  A hypothesis giving a different value for the same slot is
  **contradicted**, not unsupported, even though the surface text does not
  contain a negation. This mirrors the production veto's
  purpose: a claim citing the wrong port against the fact must be
  refutable *by* the fact. When a slot is genuinely multi-valued
  (a host running several services, a person holding several roles), the
  rule does not apply and a differing value is `unsupported`.
  **Three further slots are single-valued, ratified by the owner
  2026-08-06** and stated here as rules rather than only as rulings on
  particular pairs, because a rule that lives only in its own precedent is
  not one a later labeller can apply:
  - **the host or platform a single named instance runs on** — a differing
    host for the same named instance is `contradicted`;
  - **the kind a named instance is** (`IS_A`) — a differing kind for the
    same named instance is `contradicted`;
  - **the object of a named replacement or migration** (`REPLACES`) — the
    one thing a named replacement retired. A hypothesis naming a *different*
    replaced object, with the sentence shape otherwise preserved, is
    `contradicted`, not unsupported. This is an object swap, not a reversal,
    so the reversal rule below does not reach it.
- **Exhaustivity rule**. Procedure 3 breaks entailment on strengthening, and exhaustivity
  is strengthening only when the hypothesis **asserts** it.
  - Exhaustivity carried by **information structure** — a cleft or
    pseudo-cleft ("X is what causes Y", "X is why Y"), focus, or a definite
    predicate nominal ("X is the replacement for Y") — is presupposed and
    defeasible, not asserted. It does **not** break entailment.
  - Exhaustivity carried **lexically** — "only", "sole", "alone", "every",
    "all" — is asserted content and does.
  - Independently of how it is carried, exhaustivity that clashes with a
    premise **explicitly marking** non-exhaustivity ("one contributing
    factor", "some hosts") strengthens. This is the case
    procedure 3's own "a factor" → "the cause" example is calibrated on.

  A bare relation rendering (`X causes Y`) marks exhaustivity neither way,
  so it neither licenses nor blocks on its own. This is the entailment-side
  counterpart of the implicature-is-not-contradiction rule below:
  non-asserted content does not move a verdict in **either** direction.
- **Window rule.** A temporal fact renders its validity window in text. A
  claim time-scoped inside the window is `entailed`; a
  present-tense claim over a window the fact *explicitly closes* — named
  end event or successor — is `contradicted`.
- **Open-window rule.** A fact valid "since X" with no closing event
  entails the same state at any later reference date. This is
  the convention the production veto needs: `knowledge_triples` rows with
  `invalid_at` NULL are current.
- **Evaluation-time rule.** A hypothesis anchored to "currently"/"now" is
  decidable only if the premise fixes the state at an open or explicitly
  closed window. If its truth depends on an evaluation date the premise
  does not contain (a 90-day certificate and an unanchored "currently"),
  the verdict is `unsupported`.
- **Implicature-is-not-contradiction rule.** "Was frozen during Q1"
  *implicates* the freeze ended but does not assert it. Conversational
  implicature never upgrades `unsupported` to `contradicted`.
  Only asserted content and the rules above count as exclusion.
- **Reversal rule.** A hypothesis reversing an asymmetric relation is
  `contradicted` when one event or slot cannot carry both directions —
  replacement, a migration's from/to — or when the
  premise negates the reverse explicitly. It is `unsupported`
  when the reverse is merely unasserted and not excluded: dependency,
  load-balancing roles.

## Reversal-exclusivity, pre-classified for every relation

Decided per relation from its **semantics alone** — before any pair
existed — so a `direction` pair's verdict falls out mechanically from
which relation the seeded assignment handed its author, never from a
per-pair judgment call. **Exclusive** means one pair of endpoints cannot
carry both directions at once, so the reversed claim is `contradicted`
(reversal rule, exclusive case); **non-exclusive** means the reverse is
possible alongside the fact, so the reversed claim is `unsupported` —
unless the premise itself negates the reverse explicitly, which
always contradicts. **Symmetric** relations are ineligible for `direction`
pairs: the reversal is entailed, and the slice admits no such verdict.

| relation | class | reversed-claim verdict | why |
|---|---|---|---|
| `USES` | non-exclusive | unsupported | mutual use is coherent (two services calling each other) |
| `DEPENDS_ON` | non-exclusive | unsupported | circular dependency is not excluded by meaning |
| `HAS_PART` | exclusive | contradicted | proper parthood is antisymmetric: a part cannot contain its whole |
| `IMPLEMENTS` | exclusive | contradicted | spec and implementation are incompatible roles for one ordered pair |
| `EXTENDS` | exclusive | contradicted | extension is a strict order; mutual extension is incoherent |
| `REPLACES` | exclusive | contradicted | one replacement event cannot run both ways |
| `IMPROVES_ON` | exclusive | contradicted | an improvement ordering over one comparison cannot be mutual |
| `IS_A` | exclusive | contradicted | instance/kind (and proper subkind) is antisymmetric for distinct terms |
| `DEPLOYED_ON` | exclusive | contradicted | host and guest cannot swap for the same pair: a platform is not deployed on its own workload |
| `CAUSES` | non-exclusive | unsupported | feedback between phenomena is coherent (stress causes insomnia causes stress) |
| `AUTHORED_BY` | exclusive | contradicted | a work's author cannot be authored by that work; holds under the legacy folds (WORKS_AT, PUBLISHED_IN) too |
| `HAPPENED_ON` | exclusive | contradicted | the occurrent and its date/place cannot swap roles; holds under the legacy folds (VISITED, LIVES_IN) |
| `MENTIONS` | non-exclusive | unsupported | two documents can mention each other |
| `CITES` | non-exclusive | unsupported | mutual citation is coherent (companion papers) |
| `INSPIRED_BY` | non-exclusive | unsupported | mutual inspiration between ongoing works/projects is not excluded |
| `RELATED_TO` | symmetric | — (direction-ineligible) | the reversal is entailed by symmetry; a direction slot landing here is a mandatory logged skip |

This table covers `RELATIONSHIP_TYPES` in `app/taxonomy.py` exhaustively
(16 relations, checked against the source on 2026-08-03).

---

## Item 1 — eg-0225

**Premise:** The temporary port-forward for the game server was opened on 3 May 2026 and closed on 10 May 2026.

**Hypothesis:** The port-forward for the game server is still open.

**Verdict:** 

**Rule cited:** 

---

## Item 2 — eg-0287

**Premise:** The CI runner pool is pinned to Docker Engine 24.0.

**Hypothesis:** The CI runner pool is pinned to Docker Engine 20.10.

**Verdict:** 

**Rule cited:** 

---

## Item 3 — eg-0343

**Premise:** The standby database was promoted to primary on 14 June 2026, ending its standby role.

**Hypothesis:** The database is currently a standby.

**Verdict:** 

**Rule cited:** 

---

## Item 4 — eg-0093

**Premise:** hv-27 has part scratch partition

**Hypothesis:** The scratch partition has hv-27 as a part.

**Verdict:** 

**Rule cited:** 

---

## Item 5 — eg-0175

**Premise:** The license-report job runs on the first of every month.

**Hypothesis:** The license-report job runs on the fifteenth of every month.

**Verdict:** 

**Rule cited:** 

---

## Item 6 — eg-0220

**Premise:** A trial Tailscale mesh was enabled on 20 April 2026 with a 30-day evaluation window.

**Hypothesis:** The Tailscale mesh is currently enabled.

**Verdict:** 

**Rule cited:** 

---

## Item 7 — eg-0278

**Premise:** The internal package mirror serves clients on port 8081.

**Hypothesis:** The internal package mirror serves clients on port 3128.

**Verdict:** 

**Rule cited:** 

---

## Item 8 — eg-0236

**Premise:** The mosquitto broker listened on 1883 without TLS until the May 2026 hardening, when plaintext was disabled.

**Hypothesis:** Since June 2026, the mosquitto broker has accepted plaintext connections on 1883.

**Verdict:** 

**Rule cited:** 

---

## Item 9 — eg-0061

**Premise:** sftp-02 ships its syslog stream to the log collector on port 5514.

**Hypothesis:** sftp-02 ships its syslog stream to the log collector on port 6514.

**Verdict:** 

**Rule cited:** 

---

## Item 10 — eg-0222

**Premise:** The lab's metrics were stored in InfluxDB 1.8 from mid-2023 until the February 2026 cutover to VictoriaMetrics.

**Hypothesis:** Lab metrics are stored in InfluxDB 1.8 today.

**Verdict:** 

**Rule cited:** 

---

## Item 11 — eg-0194

**Premise:** github actions replaces jenkins

**Hypothesis:** Jenkins replaces GitHub Actions.

**Verdict:** 

**Rule cited:** 

---

## Item 12 — eg-0302

**Premise:** The office label printers accept jobs on port 631.

**Hypothesis:** The office label printers accept jobs on port 9100.

**Verdict:** 

**Rule cited:** 

---

## Item 13 — eg-0019

**Premise:** The ELK stack was retired in 2025, and Kibana no longer runs anywhere in the lab.

**Hypothesis:** Kibana is still serving dashboards in the lab.

**Verdict:** 

**Rule cited:** 

---

## Item 14 — eg-0193

**Premise:** The staging Postgres instance on stg-db-01 listens on port 5433.

**Hypothesis:** The staging Postgres instance on stg-db-01 listens on port 5432.

**Verdict:** 

**Rule cited:** 

---

## Item 15 — eg-0018

**Premise:** Postgres 15 was the production database from March 2025 until the January 2026 upgrade to Postgres 16.

**Hypothesis:** Production currently runs Postgres 15.

**Verdict:** 

**Rule cited:** 

---

## Item 16 — eg-0181

**Premise:** The Redis instance on cache-01 runs version 7.2.

**Hypothesis:** The Redis instance on cache-01 runs version 6.2.

**Verdict:** 

**Rule cited:** 

---

## Item 17 — eg-0162

**Premise:** astro replaces mkdocs

**Hypothesis:** MkDocs replaces Astro.

**Verdict:** 

**Rule cited:** 

---

## Item 18 — eg-0179

**Premise:** kibana has part elk

**Hypothesis:** ELK has Kibana as one of its parts.

**Verdict:** 

**Rule cited:** 

---

## Item 19 — eg-0161

**Premise:** customer-portal uses vault

**Hypothesis:** The customer-portal fetches all of its database credentials from Vault at startup.

**Verdict:** 

**Rule cited:** 

---

## Item 20 — eg-0142

**Premise:** glitchtip replaces sentry

**Hypothesis:** GlitchTip replaces MkDocs.

**Verdict:** 

**Rule cited:** 

---

## Item 21 — eg-0045

**Premise:** analytics etl depends on orders database

**Hypothesis:** The analytics ETL depends on the orders database.

**Verdict:** 

**Rule cited:** 

---

## Item 22 — eg-0155

**Premise:** hv-27 has part scratch partition

**Hypothesis:** hv-27 is a part of the scratch partition.

**Verdict:** 

**Rule cited:** 

---

## Item 23 — eg-0190

**Premise:** vault related to .env files

**Hypothesis:** There is an association between Vault and .env files.

**Verdict:** 

**Rule cited:** 

---

## Item 24 — eg-0146

**Premise:** fleet-cfg pins the vehicle gateways to firmware 4.2.1.

**Hypothesis:** fleet-cfg pins the vehicle gateways to firmware 4.3.0.

**Verdict:** 

**Rule cited:** 

---

## Item 25 — eg-0164

**Premise:** The ntfy server listens on port 8093.

**Hypothesis:** The ntfy server listens on port 8080.

**Verdict:** 

**Rule cited:** 

---

## Item 26 — eg-0062

**Premise:** apps-02 deployed on rack ups

**Hypothesis:** The rack UPS is deployed on apps-02.

**Verdict:** 

**Rule cited:** 

---

## Item 27 — eg-0268

**Premise:** Restic keeps 14 nightly snapshots of the wiki volume.

**Hypothesis:** Restic keeps 30 nightly snapshots of the wiki volume.

**Verdict:** 

**Rule cited:** 

---

## Item 28 — eg-0119

**Premise:** redis deployed on cache-01

**Hypothesis:** cache-01 is deployed on Redis.

**Verdict:** 

**Rule cited:** 

---

## Item 29 — eg-0342

**Premise:** Log shipping used rsyslog until Vector took over in October 2025.

**Hypothesis:** Log shipping still goes through rsyslog.

**Verdict:** 

**Rule cited:** 

---

## Item 30 — eg-0037

**Premise:** The JWT access-token lifetime is 15 minutes, and refresh tokens last 30 days.

**Hypothesis:** The JWT access-token lifetime is 30 minutes, and refresh tokens last 15 days.

**Verdict:** 

**Rule cited:** 

---

## Item 31 — eg-0114

**Premise:** vector related to telegraf

**Hypothesis:** There is a link between Vector and Telegraf.

**Verdict:** 

**Rule cited:** 

---

## Item 32 — eg-0147

**Premise:** restic uses nas

**Hypothesis:** The NAS has at least one consumer.

**Verdict:** 

**Rule cited:** 

---

## Item 33 — eg-0208

**Premise:** The booking schedule sync runs at 04:15 every morning.

**Hypothesis:** The booking schedule sync runs at 05:45 every morning.

**Verdict:** 

**Rule cited:** 

---

## Item 34 — eg-0052

**Premise:** The monitoring stack has the alert router as one of its parts.

**Hypothesis:** The alert router has the monitoring stack as one of its parts.

**Verdict:** 

**Rule cited:** 

---

## Item 35 — eg-0248

**Premise:** Terraform stores its state in the MinIO bucket tf-state.

**Hypothesis:** Terraform stores its state in the MinIO bucket artifacts-prod.

**Verdict:** 

**Rule cited:** 

---

## Item 36 — eg-0036

**Premise:** Terraform state lives in the MinIO bucket tf-state with locking enabled.

**Hypothesis:** Terraform state lives in the MinIO bucket artifacts-prod with locking enabled.

**Verdict:** 

**Rule cited:** 

---

## Item 37 — eg-0117

**Premise:** The Thanos sidecar uploads blocks to the archive bucket every 2 hours.

**Hypothesis:** The Thanos sidecar uploads blocks to the archive bucket every 6 hours.

**Verdict:** 

**Rule cited:** 

---

## Item 38 — eg-0320

**Premise:** postgres deployed on stg-db-01

**Hypothesis:** stg-db-01 is deployed on Postgres.

**Verdict:** 

**Rule cited:** 

---

## Item 39 — eg-0267

**Premise:** jenkins deployed on ci-01

**Hypothesis:** ci-01 is deployed on Jenkins.

**Verdict:** 

**Rule cited:** 

---

## Item 40 — eg-0033

**Premise:** Grafana on the monitoring host listens on port 3000 behind the nginx reverse proxy.

**Hypothesis:** Grafana on the monitoring host listens on port 3300 behind the nginx reverse proxy.

**Verdict:** 

**Rule cited:** 

---

## Item 41 — eg-0079

**Premise:** status dashboard uses vite

**Hypothesis:** The status dashboard uses Vite.

**Verdict:** 

**Rule cited:** 

---

## Item 42 — eg-0251

**Premise:** github actions replaces jenkins

**Hypothesis:** GitHub Actions is replaced by Jenkins.

**Verdict:** 

**Rule cited:** 

---

## Item 43 — eg-0149

**Premise:** Grafana's admin session lifetime is 8 hours.

**Hypothesis:** Grafana's admin session lifetime is 24 hours.

**Verdict:** 

**Rule cited:** 

---

## Item 44 — eg-0111

**Premise:** Prometheus retains metrics for 15 days.

**Hypothesis:** Prometheus retains metrics for 45 days.

**Verdict:** 

**Rule cited:** 

---

## Item 45 — eg-0066

**Premise:** Vault issues CI job tokens with a TTL of 60 minutes.

**Hypothesis:** Vault issues CI job tokens with a TTL of 90 minutes.

**Verdict:** 

**Rule cited:** 

---

## Item 46 — eg-0026

**Premise:** DNS queries from the guest VLAN are forwarded to Unbound; Unbound never forwards queries to the guest VLAN.

**Hypothesis:** Unbound forwards DNS queries to the guest VLAN.

**Verdict:** 

**Rule cited:** 

---

## Item 47 — eg-0024

**Premise:** The January migration moved the job queue from Redis to Postgres.

**Hypothesis:** The January migration moved the job queue from Postgres to Redis.

**Verdict:** 

**Rule cited:** 

---

## Item 48 — eg-0154

**Premise:** prod-db-01 deployed on postgres

**Hypothesis:** prod-db-01 is deployed on MinIO.

**Verdict:** 

**Rule cited:** 

---

## Item 49 — eg-0091

**Premise:** redis deployed on queue-01

**Hypothesis:** queue-01 is deployed on Redis.

**Verdict:** 

**Rule cited:** 

---

## Item 50 — eg-0265

**Premise:** Grafana serves its UI on port 3000.

**Hypothesis:** Grafana serves its UI on port 8080.

**Verdict:** 

**Rule cited:** 

---

## Item 51 — eg-0245

**Premise:** postfix deployed on mail-01

**Hypothesis:** Postfix is deployed on ci-01.

**Verdict:** 

**Rule cited:** 

---

## Item 52 — eg-0035

**Premise:** Prometheus scrapes the node exporters every 15 seconds, double the default interval.

**Hypothesis:** Prometheus scrapes the node exporters every 30 seconds.

**Verdict:** 

**Rule cited:** 

---

## Item 53 — eg-0218

**Premise:** Docker Swarm orchestrated the lab's containers from 2023 until the January 2026 migration to k3s.

**Hypothesis:** In March 2026, the lab's containers were orchestrated by Docker Swarm.

**Verdict:** 

**Rule cited:** 

---

## Item 54 — eg-0344

**Premise:** TLS 1.0 support was removed from the edge proxy in the November 2025 hardening pass.

**Hypothesis:** The edge proxy still accepts TLS 1.0.

**Verdict:** 

**Rule cited:** 

---

## Item 55 — eg-0201

**Premise:** thumbs queue deployed on queue-01

**Hypothesis:** The thumbs queue is deployed on cache-01.

**Verdict:** 

**Rule cited:** 

---

## Item 56 — eg-0232

**Premise:** Gitea hosted the lab's repositories until the November 2025 migration to Forgejo.

**Hypothesis:** The lab's repositories are hosted on Gitea.

**Verdict:** 

**Rule cited:** 

---

## Item 57 — eg-0341

**Premise:** The wiki ran on lab-vm-2 until the January 2026 move to lab-vm-3.

**Hypothesis:** The wiki currently runs on lab-vm-2.

**Verdict:** 

**Rule cited:** 

---

## Item 58 — eg-0048

**Premise:** wireguard deployed on udp

**Hypothesis:** WireGuard is deployed on TCP.

**Verdict:** 

**Rule cited:** 

---

## Item 59 — eg-0330

**Premise:** search-01 is a typesense

**Hypothesis:** Typesense is a search-01.

**Verdict:** 

**Rule cited:** 

---

## Item 60 — eg-0084

**Premise:** fleet-cfg related to booking schedule

**Hypothesis:** There is a connection between fleet-cfg and the booking schedule.

**Verdict:** 

**Rule cited:** 

---

## Item 61 — eg-0088

**Premise:** directory replica deployed on acs-01

**Hypothesis:** The directory replica is deployed on apps-02.

**Verdict:** 

**Rule cited:** 

---

## Item 62 — eg-0120

**Premise:** The rack UPS in the server closet is an APC Smart-UPS 1500.

**Hypothesis:** The rack UPS in the server closet is an Eaton 5P 1500.

**Verdict:** 

**Rule cited:** 

---

## Item 63 — eg-0166

**Premise:** door-badge uses directory replica

**Hypothesis:** The compactor makes use of Loki.

**Verdict:** 

**Rule cited:** 

---

## Item 64 — eg-0290

**Premise:** prod-db-01 deployed on postgres

**Hypothesis:** prod-db-01 is deployed on redis.

**Verdict:** 

**Rule cited:** 

---

## Item 65 — eg-0098

**Premise:** arc-store deployed on minio

**Hypothesis:** arc-store is deployed on Postgres.

**Verdict:** 

**Rule cited:** 

---

## Item 66 — eg-0172

**Premise:** wireguard deployed on udp

**Hypothesis:** WireGuard is the platform UDP is deployed on.

**Verdict:** 

**Rule cited:** 

---

## Item 67 — eg-0200

**Premise:** iot-gw-1 uses firmware check

**Hypothesis:** A firmware check is employed by iot-gw-1.

**Verdict:** 

**Rule cited:** 

---

## Item 68 — eg-0291

**Premise:** artifacts-prod deployed on minio

**Hypothesis:** MinIO is deployed on artifacts-prod.

**Verdict:** 

**Rule cited:** 

---

## Item 69 — eg-0109

**Premise:** team wiki deployed on lab-vm-3

**Hypothesis:** The team wiki is deployed on apps-02.

**Verdict:** 

**Rule cited:** 

---

## Item 70 — eg-0022

**Premise:** After the bake-off, Vector replaced Telegraf for metrics collection.

**Hypothesis:** After the bake-off, Telegraf replaced Vector for metrics collection.

**Verdict:** 

**Rule cited:** 

---

## Item 71 — eg-0334

**Premise:** The mobile app's API refresh tokens expire after 30 days.

**Hypothesis:** The mobile app's API refresh tokens expire after 7 days.

**Verdict:** 

**Rule cited:** 

---

## Item 72 — eg-0058

**Premise:** caddy improves on nginx

**Hypothesis:** Nginx improves on Caddy.

**Verdict:** 

**Rule cited:** 

---

## Item 73 — eg-0150

**Premise:** directory replica deployed on acs-01

**Hypothesis:** acs-01 is deployed on the directory replica.

**Verdict:** 

**Rule cited:** 

---

## Item 74 — eg-0303

**Premise:** apps-02 deployed on rack ups

**Hypothesis:** Kibana has ELK as a component.

**Verdict:** 

**Rule cited:** 

---

## Item 75 — eg-0176

**Premise:** Vector's on-disk buffer is capped at 512 MB.

**Hypothesis:** Vector's on-disk buffer is capped at 256 MB.

**Verdict:** 

**Rule cited:** 

---

## Item 76 — eg-0214

**Premise:** Pi-hole handled DNS for the lab from June 2024 until it was replaced by AdGuard Home in April 2026.

**Hypothesis:** Pi-hole currently handles DNS for the lab.

**Verdict:** 

**Rule cited:** 

---

## Item 77 — eg-0345

**Premise:** The legacy FTP endpoint was decommissioned in March 2026 when sftp-02 replaced it.

**Hypothesis:** The legacy FTP endpoint is still serving transfers.

**Verdict:** 

**Rule cited:** 

---

## Item 78 — eg-0202

**Premise:** apps/portal keeps audit-log entries for 180 days.

**Hypothesis:** apps/portal keeps audit-log entries for 90 days.

**Verdict:** 

**Rule cited:** 

---

## Item 79 — eg-0128

**Premise:** Nightly wiki backups land in the MinIO bucket wiki-backups.

**Hypothesis:** Nightly wiki backups land in the MinIO bucket tf-state.

**Verdict:** 

**Rule cited:** 

---

## Item 80 — eg-0110

**Premise:** wireguard deployed on udp

**Hypothesis:** UDP is deployed on WireGuard.

**Verdict:** 

**Rule cited:** 

---

## Item 81 — eg-0123

**Premise:** sftp-02 accepts SFTP connections on port 2222.

**Hypothesis:** sftp-02 accepts SFTP connections on port 22.

**Verdict:** 

**Rule cited:** 

---

## Item 82 — eg-0228

**Premise:** Home Assistant ran in a VM on hv-27 from its installation in 2022 until it moved to a dedicated NUC in March 2026.

**Hypothesis:** Home Assistant currently runs in a VM on hv-27.

**Verdict:** 

**Rule cited:** 

---

## Item 83 — eg-0256

**Premise:** The door-badge reader polls the directory replica every 5 minutes.

**Hypothesis:** The door-badge reader polls the directory replica every 15 minutes.

**Verdict:** 

**Rule cited:** 

---

## Item 84 — eg-0315

**Premise:** The backup pipeline has the pruning stage as one of its parts.

**Hypothesis:** The pruning stage has the backup pipeline as one of its parts.

**Verdict:** 

**Rule cited:** 

---

## Item 85 — eg-0090

**Premise:** search-01 is a typesense

**Hypothesis:** search-01 is a typesense node running version 0.25.

**Verdict:** 

**Rule cited:** 

---

## Item 86 — eg-0171

**Premise:** team wiki deployed on lab-vm-3

**Hypothesis:** The team wiki is deployed on lab-vm-3 and backed up nightly to the NAS.

**Verdict:** 

**Rule cited:** 

---

## Item 87 — eg-0301

**Premise:** thumbs queue deployed on queue-01

**Hypothesis:** queue-01 is deployed on the thumbs queue.

**Verdict:** 

**Rule cited:** 

---

## Item 88 — eg-0335

**Premise:** The nightly dump of the orders database starts at 02:30.

**Hypothesis:** The nightly dump of the orders database starts at 04:30.

**Verdict:** 

**Rule cited:** 

---

## Item 89 — eg-0298

**Premise:** The Unleash instance runs version 5.7.

**Hypothesis:** The Unleash instance runs version 4.2.

**Verdict:** 

**Rule cited:** 

---

## Item 90 — eg-0145

**Premise:** The config management agent applies its catalog every 30 minutes.

**Hypothesis:** The config management agent applies its catalog every 60 minutes.

**Verdict:** 

**Rule cited:** 

---

## Item 91 — eg-0034

**Premise:** The production Postgres runs version 16.2 on host prod-db-01.

**Hypothesis:** The production Postgres runs version 15.6 on host prod-db-01.

**Verdict:** 

**Rule cited:** 

---

## Item 92 — eg-0239

**Premise:** Nightly backups ran at 01:00 from 2024 until the schedule moved to 02:30 in April 2026.

**Hypothesis:** Nightly backups currently run at 01:00.

**Verdict:** 

**Rule cited:** 

---

## Item 93 — eg-0294

**Premise:** Loki retains logs for 30 days.

**Hypothesis:** Loki retains logs for 90 days.

**Verdict:** 

**Rule cited:** 

---

