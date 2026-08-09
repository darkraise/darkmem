# T2.54 blind pass A, batch 2

You are labeller A. Follow the protocol below exactly; it is your complete rulebook.

Output file: /tmp/claude-0/-root-repositories-darkmem/8be3da95-78a0-427b-a2ed-b0d158efc5b4/scratchpad/step5/pass-A-batch-2.json

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
    "id": "eg-0050",
    "premise": "terraform uses tf-state",
    "hypothesis": "Jenkins runs on the ci-01 host."
  },
  {
    "id": "eg-0051",
    "premise": "license-report depends on internal package mirror",
    "hypothesis": "license-report depends on the internal package mirror."
  },
  {
    "id": "eg-0052",
    "premise": "The monitoring stack has the alert router as one of its parts.",
    "hypothesis": "The alert router has the monitoring stack as one of its parts."
  },
  {
    "id": "eg-0053",
    "premise": "unleash uses oidc",
    "hypothesis": "Grafana is fronted by nginx."
  },
  {
    "id": "eg-0054",
    "premise": "nightly integration suite uses junit",
    "hypothesis": "The nightly integration suite uses JUnit."
  },
  {
    "id": "eg-0055",
    "premise": "kibana has part elk",
    "hypothesis": "Kibana has at least one component."
  },
  {
    "id": "eg-0056",
    "premise": "terraform uses minio",
    "hypothesis": "MinIO has at least one consumer."
  },
  {
    "id": "eg-0057",
    "premise": "redis deployed on cache-01",
    "hypothesis": "Redis is deployed on cache-01 as the only service on that host."
  },
  {
    "id": "eg-0058",
    "premise": "caddy improves on nginx",
    "hypothesis": "Nginx improves on Caddy."
  },
  {
    "id": "eg-0059",
    "premise": "rooftop weather station uses iot-gw-1",
    "hypothesis": "The weather station on the roof makes use of iot-gw-1."
  },
  {
    "id": "eg-0060",
    "premise": "telegraf uses influxdb",
    "hypothesis": "InfluxDB is put to use by Telegraf."
  },
  {
    "id": "eg-0061",
    "premise": "sftp-02 ships its syslog stream to the log collector on port 5514.",
    "hypothesis": "sftp-02 ships its syslog stream to the log collector on port 6514."
  },
  {
    "id": "eg-0062",
    "premise": "apps-02 deployed on rack ups",
    "hypothesis": "The rack UPS is deployed on apps-02."
  },
  {
    "id": "eg-0063",
    "premise": "jenkins deployed on ci-01",
    "hypothesis": "Jenkins is deployed on ci-01."
  },
  {
    "id": "eg-0064",
    "premise": "restic uses wiki volume",
    "hypothesis": "Restic makes use of at least one volume."
  },
  {
    "id": "eg-0065",
    "premise": "mobile app uses edge-cdn-4",
    "hypothesis": "The mobile app is a consumer of edge-cdn-4."
  },
  {
    "id": "eg-0066",
    "premise": "Vault issues CI job tokens with a TTL of 60 minutes.",
    "hypothesis": "Vault issues CI job tokens with a TTL of 90 minutes."
  },
  {
    "id": "eg-0067",
    "premise": "nightly integration suite uses artifacts bucket",
    "hypothesis": "The nightly integration suite makes use of at least one bucket."
  },
  {
    "id": "eg-0068",
    "premise": "typesense deployed on search-01",
    "hypothesis": "Typesense is deployed on at least one host."
  },
  {
    "id": "eg-0069",
    "premise": "postgres deployed on stg-db-01",
    "hypothesis": "Postgres 15.6 is deployed on stg-db-01."
  },
  {
    "id": "eg-0070",
    "premise": "github actions replaces jenkins",
    "hypothesis": "GitHub Actions replaces Jenkins."
  },
  {
    "id": "eg-0071",
    "premise": "internal package mirror uses client",
    "hypothesis": "The client is put to use by the internal package mirror."
  },
  {
    "id": "eg-0072",
    "premise": "redis replaces memcached",
    "hypothesis": "Memcached has been supplanted by Redis."
  },
  {
    "id": "eg-0073",
    "premise": "expense uses ocr worker",
    "hypothesis": "expense runs every submitted receipt through the OCR worker."
  },
  {
    "id": "eg-0074",
    "premise": "compactor uses loki",
    "hypothesis": "The compactor uses Loki."
  },
  {
    "id": "eg-0075",
    "premise": "ci runners uses docker-in-docker",
    "hypothesis": "Docker-in-Docker uses the CI runners."
  },
  {
    "id": "eg-0076",
    "premise": "iot-gw-1 uses firmware check",
    "hypothesis": "A firmware check is in use."
  },
  {
    "id": "eg-0077",
    "premise": "thumbs queue deployed on queue-01",
    "hypothesis": "The thumbs queue is deployed on queue-01."
  },
  {
    "id": "eg-0078",
    "premise": "apps/portal uses audit-log",
    "hypothesis": "audit-log has at least one consumer."
  },
  {
    "id": "eg-0079",
    "premise": "status dashboard uses vite",
    "hypothesis": "The status dashboard uses Vite."
  },
  {
    "id": "eg-0080",
    "premise": "glitchtip replaces sentry",
    "hypothesis": "GlitchTip has taken Sentry's place."
  },
  {
    "id": "eg-0081",
    "premise": "memcached deployed on cache-02",
    "hypothesis": "Memcached is the only workload deployed on cache-02."
  },
  {
    "id": "eg-0082",
    "premise": "grafana uses infra",
    "hypothesis": "Infra uses Grafana."
  },
  {
    "id": "eg-0083",
    "premise": "config management agent causes lp-relay",
    "hypothesis": "lp-relay is brought about by the config management agent."
  },
  {
    "id": "eg-0084",
    "premise": "fleet-cfg related to booking schedule",
    "hypothesis": "There is a connection between fleet-cfg and the booking schedule."
  },
  {
    "id": "eg-0085",
    "premise": "restic uses nas",
    "hypothesis": "Restic uses the NAS."
  },
  {
    "id": "eg-0086",
    "premise": "lp-relay uses office label printers",
    "hypothesis": "lp-relay makes use of printers."
  },
  {
    "id": "eg-0087",
    "premise": "grafana uses nginx",
    "hypothesis": "There is at least one consumer of nginx."
  },
  {
    "id": "eg-0088",
    "premise": "directory replica deployed on acs-01",
    "hypothesis": "The directory replica is deployed on apps-02."
  },
  {
    "id": "eg-0089",
    "premise": "monthly payroll export uses sftp-02",
    "hypothesis": "The monthly payroll export uploads its files to sftp-02 over TLS."
  },
  {
    "id": "eg-0090",
    "premise": "search-01 is a typesense",
    "hypothesis": "search-01 is a typesense node running version 0.25."
  },
  {
    "id": "eg-0091",
    "premise": "redis deployed on queue-01",
    "hypothesis": "queue-01 is deployed on Redis."
  },
  {
    "id": "eg-0092",
    "premise": "prod-db-01 deployed on postgres",
    "hypothesis": "prod-db-01 is deployed on Postgres."
  },
  {
    "id": "eg-0093",
    "premise": "hv-27 has part scratch partition",
    "hypothesis": "The scratch partition has hv-27 as a part."
  },
  {
    "id": "eg-0094",
    "premise": "billing-sync deployed on apps-02",
    "hypothesis": "billing-sync is deployed on apps-02."
  },
  {
    "id": "eg-0095",
    "premise": "nightly dump related to orders database",
    "hypothesis": "The nightly dump is a full backup of the orders database."
  },
  {
    "id": "eg-0096",
    "premise": "artifacts-prod deployed on minio",
    "hypothesis": "artifacts-prod is hosted on MinIO."
  },
  {
    "id": "eg-0097",
    "premise": "postfix deployed on mail-01",
    "hypothesis": "Postfix is deployed on mail-01."
  }
]```
