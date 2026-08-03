# T2.54 blind pass B, batch 1

You are labeller B. Follow the protocol below exactly; it is your complete rulebook.

Output file: /tmp/claude-0/-root-repositories-darkmem/8be3da95-78a0-427b-a2ed-b0d158efc5b4/scratchpad/step5/pass-B-batch-1.json

---

# T2.54 blind labelling protocol (both passes, all batches)

You are one of two independent blind labellers for the claim/fact
entailment gold set. You receive pairs as `{id, premise, hypothesis}` and
return a three-way verdict for each, decided ONLY by the rules below.

**Blindness is the instrument.** You must not see the recorded labels,
the other labeller's output, or any other batch's output. Therefore:
**read no file in the repository at all** — your batch brief is fully
self-contained (this protocol is embedded in it by reference; the rules
below are the complete rulebook). Do not open `gold.json`, `LABELLING.md`,
any manifest, any docs, any code. Do not run commands other than writing
your output file. Call no model API; your environment is keyless.

## The three verdicts

- **`entailed`** — a competent reader who accepts the premise as true must
  accept the hypothesis as true. Semantic entailment, not lexical overlap
  and not plausibility.
- **`contradicted`** — accepting the premise requires rejecting the
  hypothesis: the premise asserts (directly, or via a rule below) the
  negation of something the hypothesis asserts.
- **`unsupported`** — neither of the above. The premise is compatible with
  the hypothesis but does not establish it.

## General decision procedure

1. **Score the whole hypothesis.** A claim is entailed only if *all* of it
   is entailed. A conjunction with one supported and one unsupported
   conjunct is `unsupported` — partial credit does not exist.
2. **Use only the premise.** Your domain knowledge, what is "obviously
   true" of homelabs, and what other pairs say are all inadmissible. Some
   hypotheses are true in the wider corpus world but unsupported by their
   premise — score against the premise alone.
3. **Entailment tolerates rewording, never strengthening.** Synonyms,
   voice, clause order, dropping content (weakening) preserve entailment.
   Adding content, tightening a quantifier, upgrading "a factor" to "the
   cause" break it.
4. **Contradiction requires exclusion, not absence.** If the premise
   merely fails to mention what the hypothesis asserts, that is
   `unsupported`. It is `contradicted` only when the premise (with the
   named rules below) excludes it.

## Edge rulings — cite these by name

- **Exclusive-slot rule.** A fact stating a single-valued configuration
  slot — a port, a version of one named instance, a scrape interval, the
  bucket holding a state file, a token lifetime, the kind a named
  instance is, the host a single named instance runs on — states *the*
  operative value. A hypothesis giving a different value for the same
  slot is **contradicted**, not unsupported, even with no surface
  negation. When the slot is genuinely multi-valued (a host running
  several services, a service using many things), the rule does not
  apply and a differing value is `unsupported`.
- **Window rule.** A temporal fact renders its validity window in text. A
  claim time-scoped inside the window is `entailed`; a present-tense
  claim over a window the fact *explicitly closes* — named end event or
  successor — is `contradicted`.
- **Open-window rule.** A fact valid "since X" with no closing event
  entails the same state at any later reference date.
- **Evaluation-time rule.** A hypothesis anchored to "currently"/"now" is
  decidable only if the premise fixes the state at an open or explicitly
  closed window. If its truth depends on an evaluation date the premise
  does not contain (a 90-day certificate and an unanchored "currently"),
  the verdict is `unsupported`.
- **Implicature-is-not-contradiction rule.** "Was frozen during Q1"
  *implicates* the freeze ended but does not assert it. Conversational
  implicature never upgrades `unsupported` to `contradicted`. Only
  asserted content and the rules here count as exclusion.
- **Reversal rule.** A hypothesis reversing an asymmetric relation is
  `contradicted` when one event or slot cannot carry both directions, or
  when the premise negates the reverse explicitly. It is `unsupported`
  when the reverse is merely unasserted and not excluded. The per-relation
  classification below is fixed; apply it, do not re-litigate it.

## Reversal-exclusivity, per relation

When a hypothesis reverses the premise's relation, the verdict is fixed
by the relation's semantics (unless the premise explicitly negates the
reverse, which always contradicts):

| relation family | reversed claim |
|---|---|
| uses | unsupported (mutual use coherent) |
| depends on | unsupported (circular dependency possible) |
| has part / contains | contradicted (proper parthood antisymmetric) |
| implements | contradicted (spec vs implementation roles cannot swap) |
| extends | contradicted (strict order) |
| replaces | contradicted (one replacement event cannot run both ways) |
| improves on | contradicted (improvement ordering cannot be mutual) |
| is a (kind/instance) | contradicted (antisymmetric for distinct terms) |
| deployed on / hosted on | contradicted (host and guest cannot swap) |
| causes | unsupported (feedback between phenomena coherent) |
| authored by | contradicted (a work's author cannot be authored by it) |
| happened on | contradicted (occurrent and its date/place cannot swap) |
| mentions | unsupported (mutual mention coherent) |
| cites | unsupported (mutual citation coherent) |
| inspired by | unsupported (mutual inspiration not excluded) |
| related to | the reversal is entailed (symmetric relation) |

## Premise register

Many premises are terse lowercase clauses ("grafana uses nginx"). That is
their real shape; treat them as full assertions. A hypothesis's casing
differences never matter to your verdict — only content does.

## Output

Write exactly one JSON file at the path your batch brief names: a list of
`{"id": "...", "verdict": "entailed|contradicted|unsupported",
"rule": "<the rule you decided under, by name, or 'general' with the
procedure step>"}` — one entry per pair in your batch, every id covered,
no extra ids. Then reply with one line: how many pairs you labelled and
your verdict counts. Do not report or discuss individual verdicts in your
reply text.

---

## Your pairs

```json
[
  {
    "id": "eg-0001",
    "premise": "The staging Postgres runs version 15.6 on host stg-db-01.",
    "hypothesis": "Staging Postgres, on host stg-db-01, runs version 15.6."
  },
  {
    "id": "eg-0002",
    "premise": "The VPN is WireGuard on UDP port 51820, handing peers addresses in 10.8.0.0/24.",
    "hypothesis": "The VPN is WireGuard on UDP port 51820 and hands peers addresses in 10.8.0.0/24."
  },
  {
    "id": "eg-0003",
    "premise": "The reverse proxy terminates TLS with certificates issued by Let's Encrypt.",
    "hypothesis": "TLS is terminated at the reverse proxy using Let's Encrypt certificates."
  },
  {
    "id": "eg-0004",
    "premise": "Loki keeps logs for 30 days; the compactor deletes older chunks.",
    "hypothesis": "Loki retains logs for 30 days, and chunks older than that are deleted by the compactor."
  },
  {
    "id": "eg-0005",
    "premise": "Grafana on the monitoring host listens on port 3000 behind the nginx reverse proxy.",
    "hypothesis": "On the monitoring box, the Grafana service is reachable on port 3000, proxied by nginx."
  },
  {
    "id": "eg-0006",
    "premise": "We chose Caddy over nginx for the public reverse proxy because it renews certificates automatically.",
    "hypothesis": "Automatic certificate renewal is why Caddy was picked instead of nginx for the public-facing proxy."
  },
  {
    "id": "eg-0007",
    "premise": "The backup job encrypts archives with age before uploading them to the offsite bucket.",
    "hypothesis": "Before they are pushed to the offsite bucket, archives are encrypted using age."
  },
  {
    "id": "eg-0008",
    "premise": "Prometheus scrapes the node exporters every 15 seconds, double the default interval.",
    "hypothesis": "The node exporters are polled by Prometheus at 15-second intervals, twice the default."
  },
  {
    "id": "eg-0009",
    "premise": "Deploys to production require a green end-to-end suite and a manual approval step in the pipeline.",
    "hypothesis": "Nothing ships to production unless the end-to-end tests pass and someone approves the pipeline step by hand."
  },
  {
    "id": "eg-0010",
    "premise": "The metrics database is sharded by tenant, with one schema per customer.",
    "hypothesis": "Each customer gets its own schema; tenant is the sharding key for the metrics database."
  },
  {
    "id": "eg-0011",
    "premise": "The staging Postgres runs version 15.6 on host stg-db-01.",
    "hypothesis": "The staging database is on Postgres 15."
  },
  {
    "id": "eg-0012",
    "premise": "The Kubernetes workers run k3s v1.29.4 on three Odroid boards.",
    "hypothesis": "The cluster's worker nodes run a v1.29 release of k3s."
  },
  {
    "id": "eg-0013",
    "premise": "The rate limiter allows 100 requests per minute per API key and returns 429 beyond that.",
    "hypothesis": "API requests are rate-limited per key."
  },
  {
    "id": "eg-0014",
    "premise": "The VPN is WireGuard on UDP port 51820, handing peers addresses in 10.8.0.0/24.",
    "hypothesis": "A WireGuard VPN is in use."
  },
  {
    "id": "eg-0015",
    "premise": "Nightly restic backups of the wiki volume run at 02:30 and land on the NAS.",
    "hypothesis": "The wiki volume is backed up on a nightly schedule."
  },
  {
    "id": "eg-0016",
    "premise": "Postgres 15 was the production database from March 2025 until the January 2026 upgrade to Postgres 16.",
    "hypothesis": "Production was still on Postgres 15 in December 2025."
  },
  {
    "id": "eg-0017",
    "premise": "Since the February 2026 migration, object storage is served by MinIO; the old Ceph cluster was decommissioned.",
    "hypothesis": "As of June 2026, MinIO serves object storage."
  },
  {
    "id": "eg-0018",
    "premise": "Postgres 15 was the production database from March 2025 until the January 2026 upgrade to Postgres 16.",
    "hypothesis": "Production currently runs Postgres 15."
  },
  {
    "id": "eg-0019",
    "premise": "The ELK stack was retired in 2025, and Kibana no longer runs anywhere in the lab.",
    "hypothesis": "Kibana is still serving dashboards in the lab."
  },
  {
    "id": "eg-0020",
    "premise": "The staging environment was frozen for the compliance audit during Q1 2026.",
    "hypothesis": "The staging environment is frozen."
  },
  {
    "id": "eg-0021",
    "premise": "The certificate for lab.internal was renewed on 10 March 2026 and is valid for 90 days.",
    "hypothesis": "The lab.internal certificate is currently valid."
  },
  {
    "id": "eg-0022",
    "premise": "After the bake-off, Vector replaced Telegraf for metrics collection.",
    "hypothesis": "After the bake-off, Telegraf replaced Vector for metrics collection."
  },
  {
    "id": "eg-0023",
    "premise": "haproxy load-balances incoming requests across the three app nodes.",
    "hypothesis": "The three app nodes load-balance requests across haproxy instances."
  },
  {
    "id": "eg-0024",
    "premise": "The January migration moved the job queue from Redis to Postgres.",
    "hypothesis": "The January migration moved the job queue from Postgres to Redis."
  },
  {
    "id": "eg-0025",
    "premise": "The auth service depends on the config service at startup.",
    "hypothesis": "The config service depends on the auth service at startup."
  },
  {
    "id": "eg-0026",
    "premise": "DNS queries from the guest VLAN are forwarded to Unbound; Unbound never forwards queries to the guest VLAN.",
    "hypothesis": "Unbound forwards DNS queries to the guest VLAN."
  },
  {
    "id": "eg-0027",
    "premise": "The staging database is on Postgres 15.",
    "hypothesis": "The staging Postgres runs version 15.6 on host stg-db-01."
  },
  {
    "id": "eg-0028",
    "premise": "Backups run nightly.",
    "hypothesis": "Backups run nightly at 02:30 and are verified by a restore test."
  },
  {
    "id": "eg-0029",
    "premise": "The API is rate-limited.",
    "hypothesis": "The API allows at most 100 requests per minute per key."
  },
  {
    "id": "eg-0030",
    "premise": "Grafana sits behind the reverse proxy.",
    "hypothesis": "Grafana sits behind the nginx reverse proxy on port 3000."
  },
  {
    "id": "eg-0031",
    "premise": "Some hosts run a node exporter.",
    "hypothesis": "Every host runs a node exporter."
  },
  {
    "id": "eg-0032",
    "premise": "The postmortem identified a misconfigured health check as one contributing factor in the outage.",
    "hypothesis": "The outage was caused by the misconfigured health check."
  },
  {
    "id": "eg-0033",
    "premise": "Grafana on the monitoring host listens on port 3000 behind the nginx reverse proxy.",
    "hypothesis": "Grafana on the monitoring host listens on port 3300 behind the nginx reverse proxy."
  },
  {
    "id": "eg-0034",
    "premise": "The production Postgres runs version 16.2 on host prod-db-01.",
    "hypothesis": "The production Postgres runs version 15.6 on host prod-db-01."
  },
  {
    "id": "eg-0035",
    "premise": "Prometheus scrapes the node exporters every 15 seconds, double the default interval.",
    "hypothesis": "Prometheus scrapes the node exporters every 30 seconds."
  },
  {
    "id": "eg-0036",
    "premise": "Terraform state lives in the MinIO bucket tf-state with locking enabled.",
    "hypothesis": "Terraform state lives in the MinIO bucket artifacts-prod with locking enabled."
  },
  {
    "id": "eg-0037",
    "premise": "The JWT access-token lifetime is 15 minutes, and refresh tokens last 30 days.",
    "hypothesis": "The JWT access-token lifetime is 30 minutes, and refresh tokens last 15 days."
  },
  {
    "id": "eg-0038",
    "premise": "The mail relay is Postfix on mail-01, accepting connections only from the internal subnet.",
    "hypothesis": "The CI runners are capped at four concurrent jobs."
  },
  {
    "id": "eg-0039",
    "premise": "Internal DNS is Unbound at 192.168.20.53 with a wildcard zone for lab.internal.",
    "hypothesis": "Alert notifications route through ntfy."
  },
  {
    "id": "eg-0040",
    "premise": "The wiki volume is snapshotted before every upgrade.",
    "hypothesis": "The photo library is stored on the NAS."
  },
  {
    "id": "eg-0041",
    "premise": "Deploy notifications are posted to the ops channel.",
    "hypothesis": "The ops channel is archived monthly."
  },
  {
    "id": "eg-0042",
    "premise": "door-badge uses directory replica",
    "hypothesis": "The directory replica uses door-badge."
  },
  {
    "id": "eg-0043",
    "premise": "ocr worker deployed on gpu-01",
    "hypothesis": "The OCR worker is hosted on gpu-01."
  },
  {
    "id": "eg-0044",
    "premise": "acs-01 depends on ntp",
    "hypothesis": "acs-01 relies on NTP."
  },
  {
    "id": "eg-0045",
    "premise": "analytics etl depends on orders database",
    "hypothesis": "The analytics ETL depends on the orders database."
  },
  {
    "id": "eg-0046",
    "premise": "nginx uses client certificates",
    "hypothesis": "Nginx makes use of client certificates."
  },
  {
    "id": "eg-0047",
    "premise": "team wiki deployed on lab-vm-3",
    "hypothesis": "The team wiki is deployed on lab-vm-3 behind the nginx reverse proxy."
  },
  {
    "id": "eg-0048",
    "premise": "wireguard deployed on udp",
    "hypothesis": "WireGuard is deployed on TCP."
  },
  {
    "id": "eg-0049",
    "premise": "prometheus uses node exporters",
    "hypothesis": "Prometheus scrapes the node exporters every 15 seconds."
  }
]```
