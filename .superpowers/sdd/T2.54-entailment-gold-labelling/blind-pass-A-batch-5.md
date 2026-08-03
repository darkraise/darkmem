# T2.54 blind pass A, batch 5

You are labeller A. Follow the protocol below exactly; it is your complete rulebook.

Output file: /tmp/claude-0/-root-repositories-darkmem/8be3da95-78a0-427b-a2ed-b0d158efc5b4/scratchpad/step5/pass-A-batch-5.json

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
    "id": "eg-0194",
    "premise": "github actions replaces jenkins",
    "hypothesis": "Jenkins replaces GitHub Actions."
  },
  {
    "id": "eg-0195",
    "premise": "internal package mirror uses client",
    "hypothesis": "The internal package mirror uses the client for all artifact fetches."
  },
  {
    "id": "eg-0196",
    "premise": "redis replaces memcached",
    "hypothesis": "Redis is the replacement for Memcached."
  },
  {
    "id": "eg-0197",
    "premise": "expense uses ocr worker",
    "hypothesis": "The OCR worker has at least one consumer."
  },
  {
    "id": "eg-0198",
    "premise": "compactor uses loki",
    "hypothesis": "The compactor uses Loki and deletes chunks older than 30 days."
  },
  {
    "id": "eg-0199",
    "premise": "ci runners uses docker-in-docker",
    "hypothesis": "The CI runners use Docker-in-Docker."
  },
  {
    "id": "eg-0200",
    "premise": "iot-gw-1 uses firmware check",
    "hypothesis": "A firmware check is employed by iot-gw-1."
  },
  {
    "id": "eg-0201",
    "premise": "thumbs queue deployed on queue-01",
    "hypothesis": "The thumbs queue is deployed on cache-01."
  },
  {
    "id": "eg-0202",
    "premise": "apps/portal keeps audit-log entries for 180 days.",
    "hypothesis": "apps/portal keeps audit-log entries for 90 days."
  },
  {
    "id": "eg-0203",
    "premise": "status dashboard uses vite",
    "hypothesis": "The status dashboard makes use of Vite."
  },
  {
    "id": "eg-0204",
    "premise": "glitchtip replaces sentry",
    "hypothesis": "Sentry has been superseded."
  },
  {
    "id": "eg-0205",
    "premise": "memcached deployed on cache-02",
    "hypothesis": "The analytics ETL depends on the orders database."
  },
  {
    "id": "eg-0206",
    "premise": "grafana uses infra",
    "hypothesis": "Grafana uses the infra repository for all of its alert rules."
  },
  {
    "id": "eg-0207",
    "premise": "config management agent causes lp-relay",
    "hypothesis": "Restic uses the wiki volume."
  },
  {
    "id": "eg-0208",
    "premise": "The booking schedule sync runs at 04:15 every morning.",
    "hypothesis": "The booking schedule sync runs at 05:45 every morning."
  },
  {
    "id": "eg-0209",
    "premise": "restic uses nas",
    "hypothesis": "Restic stores every backup snapshot on the NAS."
  },
  {
    "id": "eg-0210",
    "premise": "lp-relay uses office label printers",
    "hypothesis": "lp-relay drives all four office label printers over IPP."
  },
  {
    "id": "eg-0211",
    "premise": "grafana uses nginx",
    "hypothesis": "The monthly payroll export uses sftp-02."
  },
  {
    "id": "eg-0212",
    "premise": "directory replica deployed on acs-01",
    "hypothesis": "The directory replica is deployed on acs-01 as a read-only mirror of the primary directory."
  },
  {
    "id": "eg-0213",
    "premise": "Pi-hole handled DNS for the lab from June 2024 until it was replaced by AdGuard Home in April 2026.",
    "hypothesis": "In early 2025, DNS in the lab was handled by Pi-hole."
  },
  {
    "id": "eg-0214",
    "premise": "Pi-hole handled DNS for the lab from June 2024 until it was replaced by AdGuard Home in April 2026.",
    "hypothesis": "Pi-hole currently handles DNS for the lab."
  },
  {
    "id": "eg-0215",
    "premise": "Since the March 2026 rebuild, the hypervisor fleet has run Proxmox 8.2.",
    "hypothesis": "As of August 2026, the hypervisor fleet runs Proxmox 8.2."
  },
  {
    "id": "eg-0216",
    "premise": "The guest Wi-Fi password was rotated on 1 May 2026 and is scheduled to rotate again after 60 days.",
    "hypothesis": "The guest Wi-Fi password set on 1 May 2026 is still the active one."
  },
  {
    "id": "eg-0217",
    "premise": "The NAS ran in degraded mode during the disk rebuild in May 2026.",
    "hypothesis": "The NAS is no longer in degraded mode."
  },
  {
    "id": "eg-0218",
    "premise": "Docker Swarm orchestrated the lab's containers from 2023 until the January 2026 migration to k3s.",
    "hypothesis": "In March 2026, the lab's containers were orchestrated by Docker Swarm."
  },
  {
    "id": "eg-0219",
    "premise": "Since 12 February 2026, the reverse proxy role has been held by Traefik, with no successor planned or deployed.",
    "hypothesis": "Traefik currently serves as the reverse proxy."
  },
  {
    "id": "eg-0220",
    "premise": "A trial Tailscale mesh was enabled on 20 April 2026 with a 30-day evaluation window.",
    "hypothesis": "The Tailscale mesh is currently enabled."
  },
  {
    "id": "eg-0221",
    "premise": "The lab's metrics were stored in InfluxDB 1.8 from mid-2023 until the February 2026 cutover to VictoriaMetrics.",
    "hypothesis": "During 2024, lab metrics lived in InfluxDB 1.8."
  },
  {
    "id": "eg-0222",
    "premise": "The lab's metrics were stored in InfluxDB 1.8 from mid-2023 until the February 2026 cutover to VictoriaMetrics.",
    "hypothesis": "Lab metrics are stored in InfluxDB 1.8 today."
  },
  {
    "id": "eg-0223",
    "premise": "Deploys were paused for the datacentre move during the first week of July 2026.",
    "hypothesis": "Deploys are paused."
  },
  {
    "id": "eg-0224",
    "premise": "Since the June 2026 firmware update, the access point broadcasts the IoT SSID on channel 6.",
    "hypothesis": "As of July 2026, the IoT SSID is broadcast on channel 6."
  },
  {
    "id": "eg-0225",
    "premise": "The temporary port-forward for the game server was opened on 3 May 2026 and closed on 10 May 2026.",
    "hypothesis": "The port-forward for the game server is still open."
  },
  {
    "id": "eg-0226",
    "premise": "The Let's Encrypt certificate for cloud.lab.internal was issued on 2 June 2026 with a 90-day lifetime.",
    "hypothesis": "The cloud.lab.internal certificate is currently within its validity period."
  },
  {
    "id": "eg-0227",
    "premise": "Home Assistant ran in a VM on hv-27 from its installation in 2022 until it moved to a dedicated NUC in March 2026.",
    "hypothesis": "In 2024, Home Assistant was running in a VM on hv-27."
  },
  {
    "id": "eg-0228",
    "premise": "Home Assistant ran in a VM on hv-27 from its installation in 2022 until it moved to a dedicated NUC in March 2026.",
    "hypothesis": "Home Assistant currently runs in a VM on hv-27."
  },
  {
    "id": "eg-0229",
    "premise": "The rack UPS ran on bypass while its batteries were swapped on 14 June 2026.",
    "hypothesis": "The rack UPS has returned to normal operation."
  },
  {
    "id": "eg-0230",
    "premise": "The orders database has been in read-only mode since the 28 July 2026 incident; the incident review has not yet cleared a return to writes.",
    "hypothesis": "As of 3 August 2026, the orders database is in read-only mode."
  },
  {
    "id": "eg-0231",
    "premise": "The loaner switch was installed on 5 March 2026 for an expected six-to-eight-week stay.",
    "hypothesis": "The loaner switch is still installed."
  },
  {
    "id": "eg-0232",
    "premise": "Gitea hosted the lab's repositories until the November 2025 migration to Forgejo.",
    "hypothesis": "The lab's repositories are hosted on Gitea."
  },
  {
    "id": "eg-0233",
    "premise": "The guest VLAN used the 192.168.50.0/24 range from its creation in 2023 until the July 2026 renumbering to 10.60.0.0/24.",
    "hypothesis": "In 2025, the guest VLAN used 192.168.50.0/24."
  },
  {
    "id": "eg-0234",
    "premise": "Alerting was routed to email only until Q2 2025.",
    "hypothesis": "After Q2 2025, alerting was routed to additional channels beyond email."
  },
  {
    "id": "eg-0235",
    "premise": "The backup target has been the offsite MinIO bucket since 9 January 2026, with no change since.",
    "hypothesis": "Backups currently go to the offsite MinIO bucket."
  },
  {
    "id": "eg-0236",
    "premise": "The mosquitto broker listened on 1883 without TLS until the May 2026 hardening, when plaintext was disabled.",
    "hypothesis": "Since June 2026, the mosquitto broker has accepted plaintext connections on 1883."
  },
  {
    "id": "eg-0237",
    "premise": "The spare node was lent to the robotics club on 15 July 2026 for about a month.",
    "hypothesis": "The spare node is currently in the lab."
  },
  {
    "id": "eg-0238",
    "premise": "Nightly backups ran at 01:00 from 2024 until the schedule moved to 02:30 in April 2026.",
    "hypothesis": "In January 2026, nightly backups ran at 01:00."
  },
  {
    "id": "eg-0239",
    "premise": "Nightly backups ran at 01:00 from 2024 until the schedule moved to 02:30 in April 2026.",
    "hypothesis": "Nightly backups currently run at 01:00."
  },
  {
    "id": "eg-0240",
    "premise": "The old wiki stayed online in read-only mode during the six-week content migration that began in June 2026.",
    "hypothesis": "The old wiki has been taken offline."
  },
  {
    "id": "eg-0241",
    "premise": "hv-27 has pinned kernel 6.8 since the March 2026 GPU passthrough regression; the pin has never been lifted.",
    "hypothesis": "As of August 2026, hv-27 still runs a pinned 6.8 kernel."
  }
]```
