# E4 epic-completion review package — hardening & scale

## Standing

E4 closed 13/13 on 2026-08-16. `autonomous-loop.md` §3 narrows runbook §6 to a
Fable review at **epic or version completion**, as the final gate for release,
so this is that review. E4 ships in v1.0.

Your verdict is the gate on E4 being releasable. It is **not** a gate on the
gate-track measurement tasks (`T3.22`, `TH1.10`, `T2.125`), which are separate
and untouched.

## The lens

**Honest security posture, in both directions.**

E4 is the epic that ships a credential, an exposure posture, and two audit
records. Every claim it makes about what protects this box must be true of the
tree — and the failure mode runs both ways:

- **Overclaim** — a surface, doc, or test asserting a defence the code does not
  have. The classic invariant-23 concern.
- **Underclaim** — a surface asserting a *gap* that has since been closed. This
  is not hypothetical here: `T4.04` found the settings card still declaring the
  `api_keys` table "dormant", "unwired", "not available in this deployment",
  with a test in `settings-tabs.test.tsx` **pinning** that claim — three
  landings after `T4.01` wired the credential and `T4.02` stamped the columns.
  An honesty surface that has gone stale tells an operator a live credential
  path does not exist, which is its own security failure.

Sweep for both. The second kind is the one two review rounds already walked
past.

## What to review

The union of these commits on `feat/m1-measurement` (= `master`):

| Task | Commit(s) |
|---|---|
| T4.01 Bearer credential shape + closed scope set | `7ec957ba` |
| T4.02 Stamp `events.api_key_id` / `events.actor` | `2593f59d` |
| T4.03 Exposed-deployment posture | `007d51fc` |
| T4.04 `ApiKey` use in the per-object timeline | `c7a2b9e7` |
| T4.05 Push webhook receiver | `aef0db6e`, `857f8f99`, `d01fe240` |
| T4.06 Inject `watch` mode | `3621641f`, `0c0662c7` |
| T4.07 / T4.08 | `ca7608df`, `e996c8ee` |
| T4.09 In-process assumption audit | `78e9566a`, `dcb74c2e`, `3eaa482a` |
| T4.10 Multi-replica decision record | `833b29d6` |
| T4.11 / T4.12 / T4.13 floor hazards | `5dc8379f`, `8540267a`, `7b8797d1`, `6d810086` |

Task text: `docs/planning/tasks/E4-hardening-and-scale.md`.
Per-task notes and their recorded verification output: `docs/planning/progress.md`.
Ledger: `docs/planning/gate-ledger.md`.

## Claims to attack rather than accept

Each of these is load-bearing and each was decided by the implementer. Refute
them at the tree.

1. **`trust_proxy_headers` is a sound proxy for "TLS exists" (T4.03).** Doc 18
   §9 says the `cookie_secure` tri-state "collapses to enforced the moment TLS
   exists". The implementation keys that collapse on `trust_proxy_headers`,
   which is a *proxy-trust* signal, not a TLS signal. The stated justification
   is that they coincide in this tree because the nginx-in-image fallback is
   recorded and not taken (doc 03 (b)). Decide whether that inference holds, and
   whether clamping an operator's explicit `cookie_secure=false` — rather than
   refusing to boot, or warning and honouring it — is the right shape. The
   in-tree precedent cited is the verification-bar clamp.
2. **The exposed posture's limiter is actually unevadable.**
   `tests/test_exposed_deployment_posture.py` claims a lockout fires on the
   proxy-observed IP while the client rotates the leftmost `X-Forwarded-For`,
   and that a second proxied IP does not inherit that lockout. Attack the
   *pair*: does either test pass vacuously, and is there a bucket-rotation route
   neither covers?
3. **`/mcp` under exposure is a named gap, not a closed one.** The new
   `docs/runbook-exposed-deployment.md` tells the operator not to route `/mcp`
   publicly, because its bearer-required option is designed (doc 18 §5) and
   unshipped. Is a runbook sentence the right weight for that, or does an
   exposed deployment need something enforcing?
4. **Attribution's three states (T4.04).** Keyed / session / keyed-by-a-key-this
   -box-cannot-name. The third exists because `events.api_key_id` carries no
   foreign key. Check the fourth case is handled: while the key list is loading,
   nothing is flagged. Is there a fifth?
5. **T4.09's enumeration.** Its count reached 38 after three rounds, each round
   having undercounted the previous. Its own review record says the third fix
   round's diff is "to be re-checked against its commit message rather than
   taken on it". Do that.
6. **T4.12's cap is memory-shaped on an extrapolation.** Peak worker RSS was
   measured at 4 and 7 workers on an 8-core host; the 16-core figure (~4.3 GB,
   matching the failure record's swap) is extrapolated, not measured, and is
   labelled as such. Decide whether the extrapolation carries the conclusion.

## Deferred minors and parked rulings to triage

`docs/planning/progress.md`'s E4 rows carry recorded-but-untaken items — T4.10's
two "recommendations recorded but deliberately unarmed" (a replica-knob tripwire
test, a process-state review rule), and T4.09's three doc 02 divergences
surfaced as Tier 3 and not corrected. Say which must be fixed before merge and
which are correctly parked.

## What "must fix before merge" means here

E4 is already merged to `master` — the loop merges per task. So a MUST-FIX is a
follow-up task to mint, not a merge block. Name each one at task granularity
with its tier, so it can be added to `E4`'s file or to v1.0's scope directly.
