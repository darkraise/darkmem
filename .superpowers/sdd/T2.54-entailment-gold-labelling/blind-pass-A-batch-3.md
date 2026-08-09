# T2.54 blind pass A, batch 3

You are labeller A. Follow the protocol below exactly; it is your complete rulebook.

Output file: /tmp/claude-0/-root-repositories-darkmem/8be3da95-78a0-427b-a2ed-b0d158efc5b4/scratchpad/step5/pass-A-batch-3.json

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
    "id": "eg-0098",
    "premise": "arc-store deployed on minio",
    "hypothesis": "arc-store is deployed on Postgres."
  },
  {
    "id": "eg-0099",
    "premise": "customer-portal uses vault",
    "hypothesis": "Vault uses the customer-portal."
  },
  {
    "id": "eg-0100",
    "premise": "astro replaces mkdocs",
    "hypothesis": "MkDocs has been replaced."
  },
  {
    "id": "eg-0101",
    "premise": "cleanup cron job causes scratch partition",
    "hypothesis": "The scratch partition has a cause."
  },
  {
    "id": "eg-0102",
    "premise": "ntfy related to sms",
    "hypothesis": "ntfy is associated with SMS."
  },
  {
    "id": "eg-0103",
    "premise": "vault uses apps/portal",
    "hypothesis": "apps/portal has at least one consumer."
  },
  {
    "id": "eg-0104",
    "premise": "door-badge uses directory replica",
    "hypothesis": "The directory replica makes use of door-badge."
  },
  {
    "id": "eg-0105",
    "premise": "ocr worker deployed on gpu-01",
    "hypothesis": "The OCR worker is deployed on gpu-01 with CUDA acceleration enabled."
  },
  {
    "id": "eg-0106",
    "premise": "acs-01 depends on ntp",
    "hypothesis": "acs-01 has at least one dependency."
  },
  {
    "id": "eg-0107",
    "premise": "analytics etl depends on orders database",
    "hypothesis": "The orders database is a dependency of the analytics ETL."
  },
  {
    "id": "eg-0108",
    "premise": "nginx uses client certificates",
    "hypothesis": "Caddy improves on nginx."
  },
  {
    "id": "eg-0109",
    "premise": "team wiki deployed on lab-vm-3",
    "hypothesis": "The team wiki is deployed on apps-02."
  },
  {
    "id": "eg-0110",
    "premise": "wireguard deployed on udp",
    "hypothesis": "UDP is deployed on WireGuard."
  },
  {
    "id": "eg-0111",
    "premise": "Prometheus retains metrics for 15 days.",
    "hypothesis": "Prometheus retains metrics for 45 days."
  },
  {
    "id": "eg-0112",
    "premise": "terraform uses tf-state",
    "hypothesis": "Terraform is a consumer of tf-state."
  },
  {
    "id": "eg-0113",
    "premise": "license-report depends on internal package mirror",
    "hypothesis": "The status dashboard uses Vite."
  },
  {
    "id": "eg-0114",
    "premise": "vector related to telegraf",
    "hypothesis": "There is a link between Vector and Telegraf."
  },
  {
    "id": "eg-0115",
    "premise": "unleash uses oidc",
    "hypothesis": "Unleash authenticates every dashboard login through OIDC."
  },
  {
    "id": "eg-0116",
    "premise": "nightly integration suite uses junit",
    "hypothesis": "The nightly integration suite makes use of JUnit."
  },
  {
    "id": "eg-0117",
    "premise": "The Thanos sidecar uploads blocks to the archive bucket every 2 hours.",
    "hypothesis": "The Thanos sidecar uploads blocks to the archive bucket every 6 hours."
  },
  {
    "id": "eg-0118",
    "premise": "terraform uses minio",
    "hypothesis": "MinIO is in use."
  },
  {
    "id": "eg-0119",
    "premise": "redis deployed on cache-01",
    "hypothesis": "cache-01 is deployed on Redis."
  },
  {
    "id": "eg-0120",
    "premise": "The rack UPS in the server closet is an APC Smart-UPS 1500.",
    "hypothesis": "The rack UPS in the server closet is an Eaton 5P 1500."
  },
  {
    "id": "eg-0121",
    "premise": "rooftop weather station uses iot-gw-1",
    "hypothesis": "The rooftop weather station pushes its readings through iot-gw-1 every 30 seconds."
  },
  {
    "id": "eg-0122",
    "premise": "telegraf uses influxdb",
    "hypothesis": "InfluxDB uses Telegraf."
  },
  {
    "id": "eg-0123",
    "premise": "sftp-02 accepts SFTP connections on port 2222.",
    "hypothesis": "sftp-02 accepts SFTP connections on port 22."
  },
  {
    "id": "eg-0124",
    "premise": "apps-02 deployed on rack ups",
    "hypothesis": "apps-02 is deployed on the rack UPS with 30 minutes of battery runtime."
  },
  {
    "id": "eg-0125",
    "premise": "jenkins deployed on ci-01",
    "hypothesis": "It is on ci-01 that Jenkins is deployed."
  },
  {
    "id": "eg-0126",
    "premise": "restic uses wiki volume",
    "hypothesis": "Typesense is deployed on search-01."
  },
  {
    "id": "eg-0127",
    "premise": "mobile app uses edge-cdn-4",
    "hypothesis": "edge-cdn-4 makes use of the mobile app."
  },
  {
    "id": "eg-0128",
    "premise": "Nightly wiki backups land in the MinIO bucket wiki-backups.",
    "hypothesis": "Nightly wiki backups land in the MinIO bucket tf-state."
  },
  {
    "id": "eg-0129",
    "premise": "nightly integration suite uses artifacts bucket",
    "hypothesis": "Postfix is deployed on mail-01."
  },
  {
    "id": "eg-0130",
    "premise": "typesense deployed on search-01",
    "hypothesis": "At least one workload is deployed on search-01."
  },
  {
    "id": "eg-0131",
    "premise": "postgres deployed on stg-db-01",
    "hypothesis": "Postgres is deployed on at least one host."
  },
  {
    "id": "eg-0132",
    "premise": "github actions replaces jenkins",
    "hypothesis": "Jenkins has been superseded."
  },
  {
    "id": "eg-0133",
    "premise": "internal package mirror uses client",
    "hypothesis": "The client uses the internal package mirror."
  },
  {
    "id": "eg-0134",
    "premise": "redis replaces memcached",
    "hypothesis": "Redis has taken the place of Memcached."
  },
  {
    "id": "eg-0135",
    "premise": "expense uses ocr worker",
    "hypothesis": "The compactor uses Loki."
  },
  {
    "id": "eg-0136",
    "premise": "compactor uses loki",
    "hypothesis": "Loki keeps logs for 30 days."
  },
  {
    "id": "eg-0137",
    "premise": "ci runners uses docker-in-docker",
    "hypothesis": "The CI runners use Docker-in-Docker for every build job."
  },
  {
    "id": "eg-0138",
    "premise": "iot-gw-1 uses firmware check",
    "hypothesis": "iot-gw-1 makes use of at least one check."
  },
  {
    "id": "eg-0139",
    "premise": "thumbs queue deployed on queue-01",
    "hypothesis": "The thumbs queue is deployed."
  },
  {
    "id": "eg-0140",
    "premise": "apps/portal uses audit-log",
    "hypothesis": "audit-log is put to use by apps/portal."
  },
  {
    "id": "eg-0141",
    "premise": "status dashboard uses vite",
    "hypothesis": "Vite uses the status dashboard."
  },
  {
    "id": "eg-0142",
    "premise": "glitchtip replaces sentry",
    "hypothesis": "GlitchTip replaces MkDocs."
  },
  {
    "id": "eg-0143",
    "premise": "memcached deployed on cache-02",
    "hypothesis": "Memcached is deployed on cache-02."
  },
  {
    "id": "eg-0144",
    "premise": "grafana uses infra",
    "hypothesis": "Grafana uses infra to provision every one of its dashboards."
  },
  {
    "id": "eg-0145",
    "premise": "The config management agent applies its catalog every 30 minutes.",
    "hypothesis": "The config management agent applies its catalog every 60 minutes."
  }
]```
