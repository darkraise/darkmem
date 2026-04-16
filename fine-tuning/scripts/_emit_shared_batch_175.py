"""One-off emitter for shared-base batch-175 — technical domain (SRE and chaos engineering: SLO, error budgets, incident tooling, chaos frameworks, DR, progressive delivery, capacity planning).

Writes 50 rows to data/v2/shared/batch_175.tmp.jsonl with ids shared-08701..08750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_175.tmp.jsonl"
ID_OFFSET = 8700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Replaced the flat latency SLA with a user-journey SLO tied to checkout p99 below 400 ms; the error budget now throttles risky deploys instead of letting release cadence drift unchecked.", "decision", "technical", False,
     [("SLA", "concept"), ("SLO", "concept"), ("error budget", "concept"), ("checkout", "service")],
     [("SLO", "SLA", "REPLACES"), ("error budget", "SLO", "DEPENDS_ON")],
     "which reliability target replaced the flat latency SLA for the checkout journey and what does it gate",
     "slo sla error budget checkout p99 latency throttle deploy"),
    # --- 2 architecture ---
    ("Burn-rate alerts fan out of a multi-window multi-burn detector: a fast 1h window at 14.4x and a slow 6h window at 6x both need to fire before paging the on-call engineer.", "architecture", "technical", False,
     [("Burn-rate alerts", "concept"), ("multi-window multi-burn", "method"), ("on-call", "concept")],
     [("Burn-rate alerts", "multi-window multi-burn", "USES")],
     "how does the alerting pipeline avoid noisy pages while still catching fast error-budget burns",
     "burn rate multi window alert fast slow page on call detector"),
    # --- 3 milestone ---
    ("Cut MTTR for the payments incident class from 47 minutes to 11 minutes after the Q1 runbook refresh; the checklist now lives beside the PagerDuty service definition in code.", "milestone", "technical", False,
     [("MTTR", "concept"), ("payments", "service"), ("runbook", "publication"), ("PagerDuty", "platform")],
     [("runbook", "PagerDuty", "DEPLOYED_ON")],
     "what operational metric dropped after the Q1 runbook work and where does the checklist now live",
     "mttr payments runbook pagerduty q1 incident service code"),
    # --- 4 decision ---
    ("Migrated the rotation from PagerDuty to Opsgenie because the parent org already pays for Atlassian; escalation policies map one-to-one and the schedule import kept on-call fairness intact.", "decision", "technical", False,
     [("PagerDuty", "platform"), ("Opsgenie", "platform"), ("Atlassian", "organization"), ("on-call", "concept")],
     [("Opsgenie", "PagerDuty", "REPLACES"), ("Opsgenie", "Atlassian", "DEPENDS_ON")],
     "why did the on-call rotation move from PagerDuty to Opsgenie and what made the migration safe",
     "pagerduty opsgenie atlassian on call schedule rotation fairness"),
    # --- 5 architecture ---
    ("incident.io now owns the incident channel lifecycle: slash command opens Slack, declares severity, spins up a Zoom bridge, and files the postmortem doc template before responders even join.", "architecture", "technical", False,
     [("incident.io", "platform"), ("Slack", "platform"), ("Zoom", "platform"), ("postmortem", "publication")],
     [("incident.io", "Slack", "USES"), ("incident.io", "Zoom", "USES"), ("incident.io", "postmortem", "PRODUCES")],
     "which tool coordinates the incident channel lifecycle and what artefacts does it spin up on declare",
     "incident io slack zoom postmortem channel severity bridge template"),
    # --- 6 preference ---
    ("On-call prefers FireHydrant for retros because the timeline builder pulls Slack messages and deploy markers automatically; manual copy-paste into Confluence was the old friction point.", "preference", "technical", False,
     [("FireHydrant", "platform"), ("Slack", "platform"), ("Confluence", "platform"), ("retro", "concept")],
     [("FireHydrant", "Slack", "COMMUNICATES_WITH"), ("FireHydrant", "Confluence", "REPLACES")],
     "which retro tool does on-call favour and which manual step did it eliminate from the old workflow",
     "firehydrant retro slack confluence timeline deploy marker copy"),
    # --- 7 fact ---
    ("Blameless postmortems at the company follow a strict template: timeline, contributing factors, action items with owners, and a learning section that explicitly separates cause from blame.", "fact", "technical", False,
     [("Blameless", "method"), ("postmortem", "publication"), ("action items", "concept")],
     [("postmortem", "Blameless", "USES")],
     "which postmortem style does the company follow and what structural sections does the template enforce",
     "blameless postmortem template timeline action item learning cause"),
    # --- 8 architecture ---
    ("Jeli sits downstream of the incident timeline and clusters themes across the last ninety days; the weekly reliability review now starts from a Jeli pattern report rather than a single incident.", "architecture", "technical", False,
     [("Jeli", "platform"), ("reliability review", "event"), ("pattern report", "publication")],
     [("Jeli", "pattern report", "PRODUCES")],
     "which analytics tool feeds the weekly reliability review and what cross-incident signal does it surface",
     "jeli reliability review pattern report cluster ninety day weekly"),
    # --- 9 milestone ---
    ("Shipped the first company-wide game day on 2026-02-18 exercising multi-region failover from us-east-1 to us-west-2; RTO landed at 14 minutes, under the 30-minute target.", "milestone", "technical", False,
     [("game day", "event"), ("2026-02-18", "date"), ("us-east-1", "infrastructure"), ("us-west-2", "infrastructure"), ("RTO", "concept")],
     [("game day", "2026-02-18", "HAPPENED_ON")],
     "when did the first company game day run and what RTO did the multi-region failover hit",
     "game day failover us east us west rto 14 minute target 2026"),
    # --- 10 noise ---
    ("The office espresso machine grew a second drip tray over the weekend and nobody will admit where it came from.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Chose Gremlin over Chaos Monkey for the first chaos programme because blast-radius controls and scheduled experiments were first-class; Chaos Monkey suited a narrower instance-kill scope.", "decision", "technical", False,
     [("Gremlin", "platform"), ("Chaos Monkey", "tool"), ("blast-radius", "concept")],
     [("Gremlin", "Chaos Monkey", "PREFERS")],
     "which chaos platform did the programme pick first and what feature tipped the choice away from Chaos Monkey",
     "gremlin chaos monkey blast radius experiment schedule instance kill"),
    # --- 12 architecture ---
    ("Kubernetes chaos runs on Chaos Mesh in the staging cluster; network partition and pod kill experiments are declared as CRDs and trigger from the release pipeline before promotion.", "architecture", "technical", False,
     [("Chaos Mesh", "tool"), ("Kubernetes", "platform"), ("CRD", "concept"), ("staging", "infrastructure")],
     [("Chaos Mesh", "Kubernetes", "DEPLOYED_ON"), ("Chaos Mesh", "CRD", "USES")],
     "which chaos tool drives Kubernetes staging experiments and how are the experiments declared",
     "chaos mesh kubernetes crd staging network partition pod kill"),
    # --- 13 decision ---
    ("Adopted Litmus for the open-source chaos workflow after Gremlin licensing fell out of budget; the experiment catalog covers most of the Chaos Mesh parity targets we care about.", "decision", "technical", False,
     [("Litmus", "tool"), ("Gremlin", "platform"), ("Chaos Mesh", "tool")],
     [("Litmus", "Gremlin", "REPLACES")],
     "why did the chaos workflow move off Gremlin and what replaced it for the open-source path",
     "litmus gremlin chaos mesh licensing budget parity catalog workflow"),
    # --- 14 reference ---
    ("Pumba is the Docker-level chaos tool used in the offline dev loop; killing containers and injecting packet loss at the local docker-compose layer keeps cloud chaos bills bounded.", "reference", "technical", False,
     [("Pumba", "tool"), ("Docker", "platform"), ("docker-compose", "tool")],
     [("Pumba", "Docker", "USES")],
     "which Docker-level chaos tool handles the offline dev loop and what does it inject locally",
     "pumba docker compose chaos kill container packet loss dev loop"),
    # --- 15 architecture ---
    ("Toxiproxy fronts the integration test suite so tests can inject latency, timeouts, and bandwidth limits against the payments API without touching production network paths.", "architecture", "technical", False,
     [("Toxiproxy", "tool"), ("integration test", "concept"), ("payments API", "api")],
     [("Toxiproxy", "payments API", "APPLIES_TO")],
     "which proxy tool lets integration tests inject network faults against the payments API safely",
     "toxiproxy integration test latency timeout bandwidth payments api"),
    # --- 16 fact ---
    ("The Chaos Monkey lineage started inside Netflix as the Simian Army; the modern fork runs on a Spinnaker hook and only targets instances tagged opt-in for the experiment.", "fact", "technical", False,
     [("Chaos Monkey", "tool"), ("Netflix", "organization"), ("Simian Army", "project"), ("Spinnaker", "tool")],
     [("Chaos Monkey", "Netflix", "AUTHORED_BY"), ("Chaos Monkey", "Spinnaker", "USES")],
     "which deployment tool does the modern Chaos Monkey hook into and which tagging gate limits its scope",
     "chaos monkey netflix simian army spinnaker hook opt in instance"),
    # --- 17 decision ---
    ("LaunchDarkly won the feature flag bake-off against Unleash and Flagsmith; the percentage rollout and targeting rule UI shaved onboarding time for non-engineer stakeholders.", "decision", "technical", False,
     [("LaunchDarkly", "platform"), ("Unleash", "platform"), ("Flagsmith", "platform"), ("feature flag", "concept")],
     [("LaunchDarkly", "Unleash", "PREFERS"), ("LaunchDarkly", "Flagsmith", "PREFERS")],
     "which feature flag vendor won the bake-off and which UI feature drove the choice for non-engineers",
     "launchdarkly unleash flagsmith flag bakeoff targeting rollout ui"),
    # --- 18 architecture ---
    ("Progressive delivery uses Argo Rollouts with a canary analysis that compares Prometheus error-rate and latency metrics between canary and stable for 15 minutes before promoting.", "architecture", "technical", False,
     [("Argo Rollouts", "tool"), ("canary", "pattern"), ("Prometheus", "tool"), ("analysis", "method")],
     [("Argo Rollouts", "Prometheus", "USES"), ("canary", "Argo Rollouts", "DEPENDS_ON")],
     "how does the progressive delivery pipeline decide whether to promote a canary to stable",
     "argo rollout canary prometheus error rate latency promotion analysis"),
    # --- 19 preference ---
    ("Service owners prefer blue/green over canary for the billing plane because rollback is a single router flip; canary analysis windows are hard to tune for low-QPS critical endpoints.", "preference", "technical", False,
     [("blue/green", "pattern"), ("canary", "pattern"), ("billing", "service")],
     [("blue/green", "canary", "PREFERS")],
     "which release pattern do billing owners prefer and what makes canary analysis unreliable for their traffic",
     "blue green canary billing rollback router flip low qps analysis"),
    # --- 20 milestone ---
    ("First zero-downtime DR drill completed on 2026-03-05; RTO measured at 8 minutes and RPO at 42 seconds, both inside the contractual 10-minute and 60-second ceilings.", "milestone", "technical", False,
     [("DR drill", "event"), ("2026-03-05", "date"), ("RTO", "concept"), ("RPO", "concept")],
     [("DR drill", "2026-03-05", "HAPPENED_ON")],
     "when did the zero-downtime DR drill succeed and what RTO and RPO did the run measure",
     "dr drill zero downtime rto rpo 2026 march contractual ceiling"),
    # --- 21 reference ---
    ("The Google SRE book defines error budget as one minus the SLO, spent by incidents and risky changes; the local reliability handbook cites chapter three verbatim in the onboarding path.", "reference", "technical", False,
     [("Google SRE book", "publication"), ("error budget", "concept"), ("SLO", "concept"), ("reliability handbook", "publication")],
     [("reliability handbook", "Google SRE book", "BUILDS_ON"), ("error budget", "SLO", "RELATED_TO")],
     "which canonical text does the reliability handbook cite for its definition of the error budget",
     "google sre book error budget slo handbook chapter three onboarding"),
    # --- 22 fact ---
    ("Critical user journeys are pinned in the SLO catalog: signup, checkout, search, and playback each have an availability and latency SLI with a 28-day rolling window.", "fact", "technical", False,
     [("Critical user journeys", "concept"), ("SLO catalog", "publication"), ("SLI", "concept"), ("28-day rolling window", "concept")],
     [("Critical user journeys", "SLI", "HAS_PART")],
     "which user journeys are pinned in the SLO catalog and what measurement window do their SLIs use",
     "cuj slo catalog sli signup checkout search playback 28 day window"),
    # --- 23 problem ---
    ("Page-flood incident on 2026-02-22 traced to a missing denominator filter in the availability SLI; the alert fired because scraper health events polluted the success counter.", "problem", "technical", False,
     [("availability SLI", "concept"), ("2026-02-22", "date"), ("scraper", "service"), ("Page-flood", "event")],
     [("scraper", "Page-flood", "CAUSES"), ("Page-flood", "2026-02-22", "HAPPENED_ON")],
     "what caused the 2026-02-22 page flood and which SLI definition bug let the scraper pollute the signal",
     "page flood scraper availability sli denominator filter success 2026"),
    # --- 24 architecture ---
    ("Load shedding kicks in at 85% of the service's cpu budget via an envoy admission filter; low-priority traffic categories drop first, keeping the checkout and auth paths protected.", "architecture", "technical", False,
     [("Load shedding", "concept"), ("envoy", "tool"), ("checkout", "service"), ("auth", "service")],
     [("envoy", "Load shedding", "IMPLEMENTS"), ("Load shedding", "checkout", "SUPPORTS")],
     "how does the platform shed load under cpu pressure and which user paths stay protected during shedding",
     "load shed envoy cpu 85 admission checkout auth priority drop"),
    # --- 25 decision ---
    ("Capacity planning switched from quarterly static forecasts to a weekly regression against leading indicators; the signups-to-search-qps coefficient is the single largest driver in the current model.", "decision", "technical", False,
     [("Capacity planning", "concept"), ("regression", "method"), ("signups-to-search-qps", "concept")],
     [("regression", "Capacity planning", "APPLIES_TO")],
     "how did capacity planning shift its cadence and which leading indicator dominates the current model",
     "capacity planning regression weekly signup search qps forecast"),
    # --- 26 architecture ---
    ("Multi-region failover uses Route 53 health checks with a 30-second TTL and Aurora Global Database replication; the promote-replica runbook is a single Makefile target now.", "architecture", "technical", False,
     [("Route 53", "service"), ("Aurora Global Database", "database"), ("failover", "concept"), ("Makefile", "file")],
     [("failover", "Route 53", "USES"), ("failover", "Aurora Global Database", "DEPENDS_ON")],
     "which DNS and database technologies drive multi-region failover and how is promote-replica invoked now",
     "route 53 aurora global failover ttl makefile promote replica multi"),
    # --- 27 fact ---
    ("Error budget policy is codified: once a service burns 100% in a quarter, all non-critical changes freeze until the SRE council signs off on a reliability plan.", "fact", "technical", False,
     [("Error budget policy", "publication"), ("SRE council", "organization"), ("reliability plan", "publication")],
     [("Error budget policy", "reliability plan", "PRODUCES")],
     "what happens when a service burns its full quarterly error budget under the codified policy",
     "error budget policy sre council freeze quarter reliability plan"),
    # --- 28 decision ---
    ("Chose Flagsmith for the on-prem tier because LaunchDarkly required egress and the self-hosted Unleash operator lagged on SSO; Flagsmith shipped OIDC in the 2.x line already.", "decision", "technical", False,
     [("Flagsmith", "platform"), ("LaunchDarkly", "platform"), ("Unleash", "platform"), ("OIDC", "protocol")],
     [("Flagsmith", "LaunchDarkly", "REPLACES"), ("Flagsmith", "OIDC", "SUPPORTS")],
     "which flag vendor won the on-prem tier and which auth feature tipped the decision",
     "flagsmith launchdarkly unleash on prem oidc sso self hosted 2"),
    # --- 29 architecture ---
    ("Every runbook lives in the service repo as a Markdown file next to the code; the on-call bot surfaces the nearest runbook by page label and links straight to the file on the main branch.", "architecture", "technical", False,
     [("runbook", "publication"), ("Markdown", "language"), ("on-call bot", "tool"), ("main branch", "concept")],
     [("on-call bot", "runbook", "USES")],
     "where do runbooks live in the current setup and how does on-call get the right one during a page",
     "runbook markdown service repo on call bot page label main branch"),
    # --- 30 problem ---
    ("Burn-rate page missed a slow leak because the 1h window never tripped and nobody had added a 24h slow burn; added a 3-window detector after the 2026-01-30 retro.", "problem", "technical", False,
     [("Burn-rate", "concept"), ("slow leak", "event"), ("2026-01-30", "date"), ("3-window detector", "method")],
     [("3-window detector", "Burn-rate", "IMPROVES_ON"), ("slow leak", "2026-01-30", "HAPPENED_ON")],
     "which class of incident slipped past the burn-rate alert and how did the detector design change after the retro",
     "burn rate slow leak three window detector retro 2026 january miss"),
    # --- 31 milestone ---
    ("Moved every Tier-1 service onto a codified SLO in Sloth by end of Q4; the generator now ships Prometheus recording rules and burn-rate alert groups as a single PR per service.", "milestone", "technical", False,
     [("SLO", "concept"), ("Sloth", "tool"), ("Prometheus", "tool"), ("Tier-1", "concept")],
     [("Sloth", "Prometheus", "PRODUCES"), ("SLO", "Sloth", "USES")],
     "which generator rolled out SLOs for Tier-1 services and what artefacts does it emit per service",
     "sloth slo tier 1 prometheus recording rule burn rate pr quarter"),
    # --- 32 architecture ---
    ("Game day scenarios are written in Chaos Toolkit JSON and stored in a shared repo; each scenario declares steady-state hypotheses and rollback actions that run even on early abort.", "architecture", "technical", False,
     [("Chaos Toolkit", "framework"), ("Game day", "event"), ("steady-state", "concept")],
     [("Game day", "Chaos Toolkit", "USES")],
     "which framework does the team use to declare game-day scenarios and what safety nets does it build in",
     "chaos toolkit game day steady state hypothesis rollback abort json"),
    # --- 33 reference ---
    ("The Principles of Chaos Engineering site lays out the five tenets; the onboarding deck quotes build-a-hypothesis and minimise-blast-radius as the two every new SRE must memorise.", "reference", "technical", False,
     [("Principles of Chaos Engineering", "publication"), ("blast-radius", "concept"), ("hypothesis", "concept")],
     [("hypothesis", "Principles of Chaos Engineering", "PUBLISHED_IN")],
     "which canonical reference states the chaos tenets and which two does the onboarding deck emphasise",
     "principles chaos engineering hypothesis blast radius tenet onboarding"),
    # --- 34 fact ---
    ("Every incident of severity two or higher auto-creates a Jira epic linked to the incident.io record; action items close only when the Jira ticket moves to done and a reviewer signs off.", "fact", "technical", False,
     [("Jira", "platform"), ("incident.io", "platform"), ("action item", "concept")],
     [("incident.io", "Jira", "COMMUNICATES_WITH")],
     "how do incident action items track to closure across incident.io and Jira for severity two incidents",
     "jira incident io action item severity two epic close reviewer"),
    # --- 35 decision ---
    ("Killed the legacy Nagios rig in favour of Prometheus plus Alertmanager; the rule DSL expresses burn-rate math cleanly and the Alertmanager routing tree mirrors the PagerDuty escalation policy.", "decision", "technical", False,
     [("Nagios", "tool"), ("Prometheus", "tool"), ("Alertmanager", "tool"), ("PagerDuty", "platform")],
     [("Prometheus", "Nagios", "REPLACES"), ("Alertmanager", "PagerDuty", "COMMUNICATES_WITH")],
     "which monitoring stack replaced Nagios and how does alert routing line up with the PagerDuty policy",
     "nagios prometheus alertmanager pagerduty burn rate dsl routing tree"),
    # --- 36 architecture ---
    ("Synthetic probes run from three regions against every CUJ endpoint every 30 seconds; the probe results feed the availability SLI denominator so real-user silence never hides an outage.", "architecture", "technical", False,
     [("Synthetic probes", "method"), ("CUJ", "concept"), ("availability SLI", "concept")],
     [("Synthetic probes", "availability SLI", "SUPPORTS")],
     "how do synthetic probes defend the availability SLI from gaps in real-user traffic coverage",
     "synthetic probe region 30 second cuj availability sli denominator"),
    # --- 37 preference ---
    ("The SRE team prefers prose postmortems over bullet-only templates; a readable narrative forces contributors to reason about why the system surprised us, not just list what happened.", "preference", "technical", False,
     [("postmortem", "publication"), ("narrative", "concept"), ("SRE team", "organization")],
     [("SRE team", "narrative", "PREFERS")],
     "which postmortem style does the SRE team favour and what reasoning benefit does the format push for",
     "postmortem prose narrative bullet template surprise cause team sre"),
    # --- 38 decision ---
    ("Frozen the chaos experiment schedule during peak shopping windows; the blast-radius calculus for Black Friday risk exceeds any signal we would gain from an extra fault injection run.", "decision", "technical", False,
     [("chaos experiment", "concept"), ("Black Friday", "event"), ("blast-radius", "concept")],
     [("chaos experiment", "Black Friday", "APPLIES_TO")],
     "when does the chaos programme suspend experiments and what reasoning drives the freeze",
     "chaos experiment black friday freeze peak blast radius schedule"),
    # --- 39 architecture ---
    ("Feature flag targeting rules evaluate in a sidecar exposed as a local Unix socket; the hot path never crosses a network boundary, so a flag lookup adds under 80 microseconds p99.", "architecture", "technical", False,
     [("Feature flag", "concept"), ("sidecar", "pattern"), ("Unix socket", "protocol")],
     [("Feature flag", "sidecar", "DEPLOYED_ON"), ("sidecar", "Unix socket", "USES")],
     "how does the feature flag client keep evaluation latency low without going over the network each check",
     "feature flag sidecar unix socket 80 microsecond p99 hot path local"),
    # --- 40 problem ---
    ("Canary promote stuck at 10% because the error-rate SLI was calculated over a 5-minute window that never accumulated enough samples; shortened the window to 90 seconds with a minimum-count guard.", "problem", "technical", False,
     [("Canary", "pattern"), ("error-rate SLI", "concept"), ("minimum-count guard", "method")],
     [("minimum-count guard", "error-rate SLI", "FIXES")],
     "why did canary promotion stall at 10% and which SLI tweak unblocked the progressive rollout",
     "canary promote 10 percent error rate sli window sample minimum"),
    # --- 41 fact ---
    ("On-call rotations run one week primary with a 24-hour handoff overlap; the secondary engineer sits in the incident channel during the overlap so context never blinks off between shifts.", "fact", "technical", False,
     [("On-call rotations", "concept"), ("handoff", "event"), ("incident channel", "concept")],
     [("handoff", "On-call rotations", "HAS_PART")],
     "what is the on-call shift cadence and how does the handoff protect incident context between engineers",
     "on call rotation week handoff 24 hour overlap secondary incident"),
    # --- 42 reference ---
    ("Dickerson's reliability hierarchy sits on the wall of the war room: monitoring, incident response, postmortems, testing, capacity, development, product, each layer standing on the one below.", "reference", "technical", False,
     [("Dickerson's reliability hierarchy", "publication"), ("war room", "place"), ("monitoring", "concept")],
     [("monitoring", "Dickerson's reliability hierarchy", "PUBLISHED_IN")],
     "which reliability framework is printed in the war room and what are the layered stages it names",
     "dickerson hierarchy war room monitoring incident postmortem testing"),
    # --- 43 noise ---
    ("Someone labelled the office kettle with a sticker that says do not use for noodles and now we all want to know the backstory.", "fact", "noise", True, [], [], None, None),
    # --- 44 architecture ---
    ("Disaster recovery drills copy production traffic into the warm-standby region with a 5% mirror via Envoy's request shadowing; mirrored responses are dropped and only stats feed back.", "architecture", "technical", False,
     [("Disaster recovery drills", "event"), ("warm-standby", "concept"), ("Envoy", "tool"), ("request shadowing", "method")],
     [("Disaster recovery drills", "Envoy", "USES"), ("request shadowing", "warm-standby", "APPLIES_TO")],
     "how does the DR drill rehearse the standby region without affecting real user responses",
     "dr drill warm standby envoy request shadow 5 percent mirror stats"),
    # --- 45 decision ---
    ("Retired the custom fault-injection script in favour of AWS Fault Injection Simulator for infrastructure-level chaos; the declarative experiment templates replaced 1200 lines of bespoke Python.", "decision", "technical", False,
     [("AWS Fault Injection Simulator", "service"), ("fault-injection script", "tool"), ("Python", "language")],
     [("AWS Fault Injection Simulator", "fault-injection script", "REPLACES")],
     "which AWS-native service replaced the bespoke fault-injection script and how much code did it retire",
     "aws fault injection simulator python script template chaos 1200"),
    # --- 46 fact ---
    ("Postmortem action items must declare an owner and a due date or the template lint fails in CI; action items without both dropped from 34% to 3% of closed incidents in Q3.", "fact", "technical", False,
     [("Postmortem", "publication"), ("action items", "concept"), ("CI", "concept")],
     [("CI", "Postmortem", "CONFIGURES"), ("action items", "Postmortem", "HAS_PART")],
     "which template lint rule closes the action-item accountability gap and what Q3 metric did it move",
     "postmortem action item owner due date ci lint q3 34 3 percent"),
    # --- 47 reference ---
    ("The internal reliability wiki links to Rachel Bythell's STAMP incident analysis write-up as the canonical pointer for system-level causal thinking beyond the five-whys reflex.", "reference", "technical", False,
     [("STAMP", "method"), ("reliability wiki", "publication"), ("Rachel Bythell", "person"), ("five-whys", "method")],
     [("reliability wiki", "STAMP", "USES"), ("STAMP", "Rachel Bythell", "AUTHORED_BY")],
     "which causal-analysis method does the reliability wiki recommend beyond the five-whys reflex",
     "stamp reliability wiki rachel bythell five whys causal analysis"),
    # --- 48 decision ---
    ("Decided to keep error budgets per user journey rather than per service; two services can share a CUJ and misaligned per-service budgets were masking real customer-visible burns.", "decision", "technical", False,
     [("error budget", "concept"), ("user journey", "concept"), ("CUJ", "concept")],
     [("error budget", "user journey", "APPLIES_TO")],
     "why did the error-budget accounting switch from per-service to per-journey and which signal was it hiding",
     "error budget user journey per service cuj customer visible burn mask"),
    # --- 49 milestone ---
    ("Achieved an uninterrupted quarter on 2026-03-31 with zero Sev-1 incidents across the payments fleet; the reliability review celebrated it as a budget underrun rather than proof of over-engineering.", "milestone", "technical", False,
     [("Sev-1", "concept"), ("payments", "service"), ("2026-03-31", "date"), ("reliability review", "event")],
     [("reliability review", "2026-03-31", "HAPPENED_ON")],
     "which reliability milestone did the payments fleet hit on 2026-03-31 and how did the review frame it",
     "sev 1 payments quarter zero incident 2026 march budget underrun"),
    # --- 50 problem ---
    ("RPO regression found during a DR drill: log shipping lagged by 11 minutes under sustained write load because the S3 multipart uploader's buffer was too small on the ingest tier.", "problem", "technical", False,
     [("RPO", "concept"), ("DR drill", "event"), ("S3", "service"), ("ingest tier", "infrastructure")],
     [("S3", "RPO", "CAUSES"), ("RPO", "DR drill", "RELATED_TO")],
     "which DR drill finding exposed an RPO regression and what component configuration caused the lag",
     "rpo dr drill log shipping s3 multipart buffer ingest lag regression"),
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
