"""One-off emitter for classification top-up batch-007 — team/process slice.

Contrastive decision vs. architecture pairs: each pair expresses a team-process
choice the org made (memory_type=decision) paired with the resulting ongoing
process structure (memory_type=architecture).

Writes 100 rows (50 pairs) to data/v2/classification/batch_007.tmp.jsonl.
Ids: class-00601..class-00700. Pair ids: cls-pair-00301..cls-pair-00350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_007.tmp.jsonl"
ID_OFFSET = 600
PAIR_OFFSET = 300

# (decision_text, decision_domain, architecture_text, architecture_domain)
PAIRS: list[tuple[str, str, str, str]] = [
    # --- pair 1 : branching strategy
    ("Moved to trunk-based development after two long feature branches collided during a release freeze.",
     "ai_coding",
     "All engineers commit to main behind feature flags; short-lived branches merge within 24 hours and the release is cut from main every Thursday.",
     "ai_coding"),
    # --- pair 2 : review process
    ("We chose mandatory two-reviewer approval after a silent auth regression slipped through a single-approver merge last quarter.",
     "ai_coding",
     "Pull requests require two human approvals plus a green CI run before the merge queue will accept them; the CODEOWNERS file routes security-sensitive paths to the platform team.",
     "ai_coding"),
    # --- pair 3 : CI/CD gates
    ("We adopted a merge queue because concurrent PR merges kept breaking main two or three times per week.",
     "ai_coding",
     "GitHub's merge queue serialises integration: each PR is rebased onto the tip, re-runs the full test matrix, and only lands if the pipeline stays green for the whole sequence.",
     "ai_coding"),
    # --- pair 4 : release cadence
    ("We moved from biweekly trains to daily releases once the smoke-test pipeline dropped below ten minutes.",
     "ai_coding",
     "Every green build on main promotes to staging at 10:00 UTC and to production at 15:00 UTC on business days, gated by an automated canary analysis that watches error rate and latency for fifteen minutes.",
     "ai_coding"),
    # --- pair 5 : incident response
    ("We adopted a commander-plus-scribe-plus-comms role split after our first SEV1 lasted four hours because nobody was driving.",
     "ai_coding",
     "Every SEV1 page opens a dedicated Slack channel, assigns an incident commander, a scribe, and a communications lead; the commander owns technical decisions while the scribe keeps a running timeline for the postmortem.",
     "ai_coding"),
    # --- pair 6 : on-call rotation
    ("We chose a follow-the-sun rotation because the EU on-call was paging at 3 AM twice a week.",
     "ai_coding",
     "Three regional rotations cover US-West, EU, and APAC in eight-hour windows; the primary on-call owns acknowledgement within five minutes and handoffs happen in a shared channel with an explicit written summary of open incidents.",
     "ai_coding"),
    # --- pair 7 : sprint cadence
    ("We dropped two-week sprints in favour of continuous flow after retros kept surfacing the same end-of-sprint crunch.",
     "ai_coding",
     "Work is tracked on a single pull-based board with explicit work-in-progress limits per column; weekly demos replace sprint reviews and planning happens as a thirty-minute backlog refinement each Monday.",
     "ai_coding"),
    # --- pair 8 : code ownership
    ("We adopted CODEOWNERS-enforced ownership after an orphaned service caused a seven-hour outage with no clear responder.",
     "ai_coding",
     "Every top-level directory maps to exactly one owning team in CODEOWNERS; ownership changes require a signed ADR and the platform team audits the mapping quarterly against the service catalog.",
     "ai_coding"),
    # --- pair 9 : RFC process
    ("We introduced a lightweight RFC process after three teams independently built their own feature-flag systems in the same quarter.",
     "ai_coding",
     "Any change with cross-team impact lands as a markdown RFC in the architecture repo, collects comments for five business days, and is ratified by the principal engineers' group before implementation begins.",
     "ai_coding"),
    # --- pair 10 : postmortems
    ("We switched to blameless postmortems after engineers started hiding near-misses to avoid being named in the writeups.",
     "ai_coding",
     "Every SEV2-and-above incident gets a written postmortem within five business days; the document focuses on contributing factors and systemic fixes, names no individuals as at fault, and its action items are tracked to completion in the issue tracker.",
     "ai_coding"),
    # --- pair 11 : hiring pipeline
    ("We moved to structured interviews with calibrated rubrics after a hiring manager audit showed wildly different bars across loops.",
     "ai_coding",
     "Every candidate goes through the same four stages: recruiter screen, a coding exercise, a system-design round, and a values interview; each stage has a written rubric and two interviewers must independently submit scores before the debrief.",
     "ai_coding"),
    # --- pair 12 : onboarding
    ("We chose a buddy-plus-checklist onboarding model after new hires reported feeling lost for their entire first month.",
     "ai_coding",
     "Each new engineer is paired with a buddy for thirty days, works through a written onboarding checklist covering environment setup, first PR, first on-call shadow, and first incident readout, and checks in weekly with their manager against that list.",
     "ai_coding"),
    # --- pair 13 : code review SLAs
    ("We set a four-hour review SLA after throughput data showed PRs sitting unreviewed for a median of two business days.",
     "ai_coding",
     "Pull requests awaiting review ping the owning team's channel after four business hours and escalate to the team lead after eight; a weekly dashboard tracks the median time-in-review per team.",
     "ai_coding"),
    # --- pair 14 : deployment freeze policy
    ("We adopted a Friday and holiday-eve deploy freeze after three Friday deploys turned into weekend incidents.",
     "ai_coding",
     "Production deploys are blocked from Friday 14:00 UTC through Monday 09:00 UTC and for twenty-four hours before recognised holidays; exceptions require the on-call director's written approval in the deploy channel.",
     "ai_coding"),
    # --- pair 15 : rollback policy
    ("We made rollback the default response for production SEV1s after a forward-fix attempt doubled the length of the outage.",
     "ai_coding",
     "Any SEV1 that correlates with a recent deploy triggers an automatic rollback within ten minutes unless the incident commander explicitly opts for a forward-fix and documents the reason in the channel.",
     "ai_coding"),
    # --- pair 16 : feature flag lifecycle
    ("We introduced a flag-expiry policy after discovering more than two hundred stale flags that nobody remembered owning.",
     "ai_coding",
     "Every new feature flag is created with an owner and an expiry date; a weekly job opens a tracking ticket for any flag past its expiry and flags more than ninety days old fail the release readiness check.",
     "ai_coding"),
    # --- pair 17 : error budget policy
    ("We adopted an error-budget-based freeze rule after the reliability team and product kept arguing about when to slow feature work.",
     "ai_coding",
     "Each service has a monthly error budget derived from its SLO; once the budget is exhausted feature deploys are automatically blocked and only reliability fixes ship until the rolling window recovers.",
     "ai_coding"),
    # --- pair 18 : security review
    ("We made threat modelling a required gate after a high-severity data-exposure bug shipped without any security sign-off.",
     "ai_coding",
     "Features touching authentication, authorization, or PII require a written threat model reviewed by the security team before implementation begins; the review is linked from the RFC and tracked on the release checklist.",
     "ai_coding"),
    # --- pair 19 : pair programming policy
    ("We started requiring pairing on critical-path changes after a solo refactor of the payments module caused a two-hour incident.",
     "ai_coding",
     "Any change to code paths tagged critical in the service catalog is authored in a pairing session; the pairing partner co-signs the PR and the session is noted in the commit trailer.",
     "ai_coding"),
    # --- pair 20 : retrospective cadence
    ("We moved retros from ad-hoc to biweekly after three months of retros happening only when something went wrong.",
     "ai_coding",
     "Each squad runs a sixty-minute retrospective every second Friday using a start-stop-continue template; action items are captured in the team board and the squad lead reviews progress against them at the next retro.",
     "ai_coding"),
    # --- pair 21 : performance review cycle
    ("We shifted from annual to semi-annual performance reviews after engineers said yearly feedback came too late to act on.",
     "ai_coding",
     "Performance reviews run every six months on a fixed calendar; each review combines manager assessment, peer feedback from three nominated colleagues, and a self-reflection, all captured in the HR system for continuity.",
     "ai_coding"),
    # --- pair 22 : internal open source model
    ("We adopted an inner-source model after platform teams became a bottleneck for every cross-team feature request.",
     "ai_coding",
     "Shared infrastructure repositories accept pull requests from any engineer in the company; each repo has a published contributing guide, a maintainer rotation, and an SLA for first response on outside contributions.",
     "ai_coding"),
    # --- pair 23 : design review gate
    ("We made design review mandatory for all services with customer-facing APIs after two teams shipped incompatible webhook shapes.",
     "ai_coding",
     "Any service exposing an external API runs a design review with the API council before the first endpoint ships; the council checks naming, versioning, error shape, and rate-limit defaults against the company API guidelines.",
     "ai_coding"),
    # --- pair 24 : data migration process
    ("We moved to expand-contract migrations after a destructive alter-table locked the orders database for twenty minutes.",
     "ai_coding",
     "Schema changes ship in two deploys: the first adds the new shape and dual-writes, the second removes the old shape after a verified backfill; destructive statements run only behind a feature flag and a documented rollback script.",
     "ai_coding"),
    # --- pair 25 : dependency upgrade cadence
    ("We adopted a monthly dependency upgrade train after a six-month-stale library left us exposed to a published CVE.",
     "ai_coding",
     "A scheduled job opens upgrade PRs the first Monday of each month for every direct dependency; the platform team triages and merges them by the end of that week, and any unmerged upgrades roll into the next month's review.",
     "ai_coding"),
    # --- pair 26 : documentation ownership
    ("We made docs a release-blocker after an incident revealed the runbook for a tier-one service hadn't been updated in a year.",
     "ai_coding",
     "Each service has a runbook and an architecture page owned by the same team that owns the code; a CI check fails the deploy if either page has not been touched in the last ninety days and the service had a code change in that window.",
     "ai_coding"),
    # --- pair 27 : escalation policy
    ("We formalised escalation levels after an on-call engineer struggled alone on a customer-visible outage for ninety minutes.",
     "ai_coding",
     "Every SEV1 escalates to the secondary on-call after ten minutes without acknowledgement, to the engineering manager after thirty, and to the director after sixty; the escalation path is encoded in the pager policy and tested monthly via game days.",
     "ai_coding"),
    # --- pair 28 : bug triage
    ("We adopted a weekly bug bash plus a rotating triage role after the backlog crossed one thousand open issues.",
     "ai_coding",
     "A triage engineer rotates weekly across the squad and owns all incoming bugs: every new issue is labelled, severity-scored, and either routed to a milestone or closed within two business days, and the team spends Friday afternoons on a themed bug bash.",
     "ai_coding"),
    # --- pair 29 : experiment review
    ("We introduced a weekly experiment council after three A/B tests shipped with overlapping audiences and unreadable results.",
     "ai_coding",
     "Every experiment is registered in the experiment platform before launch and reviewed in a Tuesday council meeting; the council checks audience overlap, power analysis, and stopping criteria, and signs off before the flag is turned on.",
     "ai_coding"),
    # --- pair 30 : code style
    ("We chose Black plus Ruff on autoformat after a style debate dominated three consecutive engineering all-hands.",
     "ai_coding",
     "Every Python repository runs Black and Ruff in a pre-commit hook and in CI; style discussions in PRs are closed by pointing at the configured tooling and any rule change requires a one-line RFC in the style repo.",
     "ai_coding"),
    # --- pair 31 : test coverage policy
    ("We set a coverage floor on changed lines only after a blanket eighty-percent rule pushed teams to write useless tests.",
     "ai_coding",
     "The CI check enforces that at least seventy-five percent of lines changed in a PR are exercised by tests; whole-file coverage is reported as a trend but does not block merges, keeping the incentive on testing new work.",
     "ai_coding"),
    # --- pair 32 : security incident runbook
    ("We separated security incidents from reliability incidents after a credential leak got lost in the general ops channel.",
     "ai_coding",
     "Security incidents follow a distinct runbook and page the security team first; the response channel is access-controlled, evidence is preserved in a dedicated bucket, and legal is looped in within the first hour for any data-exposure class.",
     "ai_coding"),
    # --- pair 33 : accessibility review
    ("We made accessibility review a launch gate for customer-facing UI after an external audit found WCAG violations on the checkout flow.",
     "ai_coding",
     "Every customer-visible UI change is reviewed against the WCAG 2.2 AA checklist by the accessibility guild before launch; automated axe-core tests run in CI and block merges on new violations.",
     "ai_coding"),
    # --- pair 34 : internal tooling policy
    ("We chose to buy rather than build for observability tooling after the internal metrics stack consumed half of an SRE team for a year.",
     "ai_coding",
     "Observability runs on a vendor platform with a clear integration layer; the SRE team owns the integration and dashboards while product engineers consume the tooling through a thin internal SDK, freeing the team to focus on reliability work.",
     "ai_coding"),
    # --- pair 35 : test environment strategy
    ("We moved to ephemeral preview environments after a shared staging cluster became the bottleneck for every large feature.",
     "ai_coding",
     "Each PR spins up its own namespaced environment on the dev cluster with seeded data; the environment is torn down automatically when the PR merges or after forty-eight hours of inactivity, and a shared long-lived staging is reserved for end-to-end regression tests.",
     "ai_coding"),
    # --- pair 36 : feature kickoff
    ("We adopted a written kickoff doc for every epic after multiple features shipped without clear success criteria.",
     "ai_coding",
     "Each epic begins with a one-page kickoff doc covering problem statement, success metrics, non-goals, and rollout plan; engineering manager, product manager, and tech lead all sign off before the first ticket is opened.",
     "ai_coding"),
    # --- pair 37 : tech debt allocation
    ("We reserved twenty percent of each quarter for tech-debt work after two years of debt tickets never making it into sprints.",
     "ai_coding",
     "Each team's quarterly plan allocates a dedicated debt bucket equal to one in five engineer-weeks; debt items are prioritised by the tech lead and reported alongside feature progress in the quarterly business review.",
     "ai_coding"),
    # --- pair 38 : production access policy
    ("We locked down production shell access after an accidental rm on a live host caused a two-hour data recovery effort.",
     "ai_coding",
     "Direct shell access to production hosts is disabled; engineers use an audited break-glass tool that opens a time-boxed session, records every command, and requires a peer's approval before granting elevated privileges.",
     "ai_coding"),
    # --- pair 39 : vendor onboarding
    ("We introduced a formal vendor review after a shadow-IT SaaS purchase exposed customer data to an unvetted processor.",
     "ai_coding",
     "Any new third-party service that touches customer or production data goes through a joint security, legal, and procurement review; approved vendors are listed in a shared registry and renewals trigger an automatic re-review.",
     "ai_coding"),
    # --- pair 40 : goals framework
    ("We adopted quarterly OKRs after yearly goal-setting kept drifting out of relevance by the third month.",
     "ai_coding",
     "Each team sets three to five objectives with measurable key results at the start of every quarter; progress is reviewed at a mid-quarter checkpoint and scored publicly at the end, and the results feed into the next quarter's planning.",
     "ai_coding"),
    # --- pair 41 : release approval
    ("We replaced change advisory board approval with automated release readiness checks after CAB meetings added a day of latency with no measurable safety gain.",
     "ai_coding",
     "Releases are approved by an automated readiness pipeline that verifies green tests, a signed-off runbook entry, an up-to-date rollback script, and the absence of active incidents; exceptions still require a director's written approval.",
     "ai_coding"),
    # --- pair 42 : architecture decision records
    ("We committed to writing ADRs for every significant choice after an architecture quiz showed half the team could not explain why we picked Kafka.",
     "ai_coding",
     "Architecture decisions land as numbered ADRs in the docs repo using the context-decision-consequences template; every PR that introduces a new service or replaces an existing one must link to the relevant ADR, and the index is reviewed at the quarterly architecture summit.",
     "ai_coding"),
    # --- pair 43 : demo cadence
    ("We introduced a weekly Friday demo after stakeholders complained they only saw finished work at quarter boundaries.",
     "ai_coding",
     "Every Friday at 16:00 local, each squad shows a fifteen-minute demo of shipped or shippable work; recordings go to a shared Drive folder and the engineering newsletter links the week's highlights for asynchronous viewers.",
     "ai_coding"),
    # --- pair 44 : chaos engineering
    ("We adopted a monthly game day after a region-failover drill revealed nobody had actually tested the DNS switch under load.",
     "ai_coding",
     "Each month one squad runs a pre-announced game day that injects a realistic failure mode in staging and, quarterly, in production under a tight blast radius; findings are tracked as normal incidents with owned remediation items.",
     "ai_coding"),
    # --- pair 45 : runbook quality
    ("We introduced a runbook drill after an on-call engineer couldn't follow an outdated Redis failover doc during a real page.",
     "ai_coding",
     "Each tier-one service's runbook is exercised by its on-call once per quarter in a staging drill; any step that doesn't work is fixed inside the drill window and the runbook's last-verified date is stamped at the top of the page.",
     "ai_coding"),
    # --- pair 46 : open-source contribution
    ("We committed to upstreaming internal patches after maintaining a private fork of a key library consumed weeks of engineer time every upgrade.",
     "ai_coding",
     "Every internal patch to an external dependency is opened as a pull request upstream within two weeks; until it lands we track the fork in a shared board and the platform team owns keeping the fork rebased against the upstream main branch.",
     "ai_coding"),
    # --- pair 47 : knowledge sharing
    ("We started a biweekly engineering talk after survey feedback flagged lack of cross-team technical visibility.",
     "ai_coding",
     "A thirty-minute engineering talk runs every other Wednesday with a rotating speaker drawn from the signup sheet; talks are recorded, slides are archived in the learning repo, and attendance is optional but counted towards the growth rubric.",
     "ai_coding"),
    # --- pair 48 : decision log for experiments
    ("We adopted a shared experiment log after three teams re-ran the same onboarding experiment unaware of each other's results.",
     "ai_coding",
     "Every experiment writes an entry in the company-wide experiment log with hypothesis, setup, result, and decision; the log is searchable by feature area and new experiment proposals must check for prior art before approval.",
     "ai_coding"),
    # --- pair 49 : promotion process
    ("We moved promotions to a calibrated committee review after manager-only promotions produced noticeable inconsistencies between teams.",
     "ai_coding",
     "Promotion packets are written against a public rubric by the candidate's manager, reviewed by a cross-team committee that calibrates against anonymised past packets, and decided in a single meeting that produces a written rationale for each outcome.",
     "ai_coding"),
    # --- pair 50 : blameless change management
    ("We dropped formal change approval forms in favour of a lightweight change log after the forms became copy-paste rituals everyone ignored.",
     "ai_coding",
     "Every production-impacting change posts a structured message in the change channel with author, scope, rollback plan, and monitoring link; the log is archived for audit and reviewed in the weekly reliability meeting for patterns.",
     "ai_coding"),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (dec_text, dec_dom, arch_text, arch_dom) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            dec_row = {
                "id": f"class-{ID_OFFSET + (2 * i - 1):05d}",
                "domain": dec_dom,
                "text": dec_text,
                "memory_type": "decision",
                "pair_id": pair_id,
            }
            arch_row = {
                "id": f"class-{ID_OFFSET + (2 * i):05d}",
                "domain": arch_dom,
                "text": arch_text,
                "memory_type": "architecture",
                "pair_id": pair_id,
            }
            f.write(json.dumps(dec_row, ensure_ascii=False) + "\n")
            f.write(json.dumps(arch_row, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
