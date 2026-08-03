# T2.54 blind pass A, batch 4

You are labeller A. Follow the protocol below exactly; it is your complete rulebook.

Output file: /tmp/claude-0/-root-repositories-darkmem/8be3da95-78a0-427b-a2ed-b0d158efc5b4/scratchpad/step5/pass-A-batch-4.json

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
    "id": "eg-0146",
    "premise": "fleet-cfg pins the vehicle gateways to firmware 4.2.1.",
    "hypothesis": "fleet-cfg pins the vehicle gateways to firmware 4.3.0."
  },
  {
    "id": "eg-0147",
    "premise": "restic uses nas",
    "hypothesis": "The NAS has at least one consumer."
  },
  {
    "id": "eg-0148",
    "premise": "lp-relay uses office label printers",
    "hypothesis": "Telegraf uses InfluxDB."
  },
  {
    "id": "eg-0149",
    "premise": "Grafana's admin session lifetime is 8 hours.",
    "hypothesis": "Grafana's admin session lifetime is 24 hours."
  },
  {
    "id": "eg-0150",
    "premise": "directory replica deployed on acs-01",
    "hypothesis": "acs-01 is deployed on the directory replica."
  },
  {
    "id": "eg-0151",
    "premise": "monthly payroll export uses sftp-02",
    "hypothesis": "The monthly payroll export uses sftp-02."
  },
  {
    "id": "eg-0152",
    "premise": "search-01 is a typesense",
    "hypothesis": "search-01 is a typesense instance serving all production search traffic."
  },
  {
    "id": "eg-0153",
    "premise": "redis deployed on queue-01",
    "hypothesis": "Redis is deployed on queue-01."
  },
  {
    "id": "eg-0154",
    "premise": "prod-db-01 deployed on postgres",
    "hypothesis": "prod-db-01 is deployed on MinIO."
  },
  {
    "id": "eg-0155",
    "premise": "hv-27 has part scratch partition",
    "hypothesis": "hv-27 is a part of the scratch partition."
  },
  {
    "id": "eg-0156",
    "premise": "billing-sync deployed on apps-02",
    "hypothesis": "The team wiki is deployed on lab-vm-3."
  },
  {
    "id": "eg-0157",
    "premise": "nightly dump related to orders database",
    "hypothesis": "The nightly dump is associated with the orders database."
  },
  {
    "id": "eg-0158",
    "premise": "artifacts-prod deployed on minio",
    "hypothesis": "The CI runners use Docker-in-Docker."
  },
  {
    "id": "eg-0159",
    "premise": "postfix deployed on mail-01",
    "hypothesis": "Postfix is deployed on mail-01, accepting connections only from the internal subnet."
  },
  {
    "id": "eg-0160",
    "premise": "arc-store deployed on minio",
    "hypothesis": "Astro replaces MkDocs."
  },
  {
    "id": "eg-0161",
    "premise": "customer-portal uses vault",
    "hypothesis": "The customer-portal fetches all of its database credentials from Vault at startup."
  },
  {
    "id": "eg-0162",
    "premise": "astro replaces mkdocs",
    "hypothesis": "MkDocs replaces Astro."
  },
  {
    "id": "eg-0163",
    "premise": "cleanup cron job causes scratch partition",
    "hypothesis": "The scratch partition causes the cleanup cron job."
  },
  {
    "id": "eg-0164",
    "premise": "The ntfy server listens on port 8093.",
    "hypothesis": "The ntfy server listens on port 8080."
  },
  {
    "id": "eg-0165",
    "premise": "vault uses apps/portal",
    "hypothesis": "Vault uses apps/portal for all of its notification webhooks."
  },
  {
    "id": "eg-0166",
    "premise": "door-badge uses directory replica",
    "hypothesis": "The compactor makes use of Loki."
  },
  {
    "id": "eg-0167",
    "premise": "ocr worker deployed on gpu-01",
    "hypothesis": "The OCR worker is deployed on gpu-01."
  },
  {
    "id": "eg-0168",
    "premise": "acs-01 depends on ntp",
    "hypothesis": "acs-01 depends on NTP."
  },
  {
    "id": "eg-0169",
    "premise": "analytics etl depends on orders database",
    "hypothesis": "The analytics ETL depends on at least one database."
  },
  {
    "id": "eg-0170",
    "premise": "nginx uses client certificates",
    "hypothesis": "Nginx employs client certificates."
  },
  {
    "id": "eg-0171",
    "premise": "team wiki deployed on lab-vm-3",
    "hypothesis": "The team wiki is deployed on lab-vm-3 and backed up nightly to the NAS."
  },
  {
    "id": "eg-0172",
    "premise": "wireguard deployed on udp",
    "hypothesis": "WireGuard is the platform UDP is deployed on."
  },
  {
    "id": "eg-0173",
    "premise": "prometheus uses node exporters",
    "hypothesis": "Prometheus uses at least one exporter."
  },
  {
    "id": "eg-0174",
    "premise": "terraform uses tf-state",
    "hypothesis": "The mobile app uses edge-cdn-4."
  },
  {
    "id": "eg-0175",
    "premise": "The license-report job runs on the first of every month.",
    "hypothesis": "The license-report job runs on the fifteenth of every month."
  },
  {
    "id": "eg-0176",
    "premise": "Vector's on-disk buffer is capped at 512 MB.",
    "hypothesis": "Vector's on-disk buffer is capped at 256 MB."
  },
  {
    "id": "eg-0177",
    "premise": "unleash uses oidc",
    "hypothesis": "OIDC uses Unleash."
  },
  {
    "id": "eg-0178",
    "premise": "nightly integration suite uses junit",
    "hypothesis": "GlitchTip replaces Sentry."
  },
  {
    "id": "eg-0179",
    "premise": "kibana has part elk",
    "hypothesis": "ELK has Kibana as one of its parts."
  },
  {
    "id": "eg-0180",
    "premise": "terraform uses minio",
    "hypothesis": "Terraform makes use of MinIO."
  },
  {
    "id": "eg-0181",
    "premise": "The Redis instance on cache-01 runs version 7.2.",
    "hypothesis": "The Redis instance on cache-01 runs version 6.2."
  },
  {
    "id": "eg-0182",
    "premise": "caddy improves on nginx",
    "hypothesis": "Caddy improves on nginx in every respect."
  },
  {
    "id": "eg-0183",
    "premise": "rooftop weather station uses iot-gw-1",
    "hypothesis": "iot-gw-1 is used by the weather station on the roof."
  },
  {
    "id": "eg-0184",
    "premise": "telegraf uses influxdb",
    "hypothesis": "The rooftop weather station uses iot-gw-1."
  },
  {
    "id": "eg-0185",
    "premise": "sftp-02 uses dns",
    "hypothesis": "sftp-02 uses DNS."
  },
  {
    "id": "eg-0186",
    "premise": "apps-02 deployed on rack ups",
    "hypothesis": "apps-02 runs on the rack UPS."
  },
  {
    "id": "eg-0187",
    "premise": "jenkins deployed on ci-01",
    "hypothesis": "Jenkins is deployed on ci-01 and capped at four concurrent jobs."
  },
  {
    "id": "eg-0188",
    "premise": "restic uses wiki volume",
    "hypothesis": "Restic snapshots the wiki volume nightly at 02:30."
  },
  {
    "id": "eg-0189",
    "premise": "mobile app uses edge-cdn-4",
    "hypothesis": "edge-cdn-4 uses the mobile app."
  },
  {
    "id": "eg-0190",
    "premise": "vault related to .env files",
    "hypothesis": "There is an association between Vault and .env files."
  },
  {
    "id": "eg-0191",
    "premise": "nightly integration suite uses artifacts bucket",
    "hypothesis": "Unleash uses OIDC."
  },
  {
    "id": "eg-0192",
    "premise": "typesense deployed on search-01",
    "hypothesis": "Typesense runs on the search-01 host."
  },
  {
    "id": "eg-0193",
    "premise": "The staging Postgres instance on stg-db-01 listens on port 5433.",
    "hypothesis": "The staging Postgres instance on stg-db-01 listens on port 5432."
  }
]```
