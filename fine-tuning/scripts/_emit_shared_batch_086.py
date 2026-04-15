"""One-off emitter for shared-base batch-086 — ai_coding domain (code review practices and mentoring through review).

Writes 50 rows to data/v2/shared/batch_086.tmp.jsonl with ids shared-04251..04300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_086.tmp.jsonl"
ID_OFFSET = 4250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Adopted a PR template with sections for motivation, risk, and rollback plan; the template lives in .github/PULL_REQUEST_TEMPLATE.md and reviewers refuse PRs that leave the rollback box empty.", "decision", "ai_coding", False,
     [("PR template", "pattern"), (".github/PULL_REQUEST_TEMPLATE.md", "file"), ("rollback", "concept")],
     [],
     "which PR template sections does the team require and where does the file live",
     "pull request template motivation risk rollback github file enforce"),
    # --- 2 ---
    ("Switched to conventional comments so reviewers prefix every note with nit, suggestion, question, or blocking; the old free-form prose left juniors guessing whether a thread was advisory or required.", "decision", "ai_coding", False,
     [("conventional comments", "pattern"), ("nit", "pattern"), ("blocking", "pattern")],
     [("conventional comments", "blocking", "REPLACES")],
     "which review-comment convention did we adopt and what ambiguity did it resolve for new contributors",
     "conventional comments nit suggestion blocking prefix junior clarity"),
    # --- 3 ---
    ("CODEOWNERS routes auth-service paths to the security guild and database-migration paths to the platform team; the manual reviewer ping in Slack is now obsolete.", "architecture", "ai_coding", False,
     [("CODEOWNERS", "file"), ("auth-service", "service"), ("Slack", "platform"), ("security guild", "organization")],
     [("CODEOWNERS", "Slack", "REPLACES")],
     "how does CODEOWNERS routing replace the manual reviewer ping in Slack for sensitive paths",
     "codeowners routing auth migration security guild slack ping retire"),
    # --- 4 ---
    ("Set the review SLA at one business day for first response and three business days for merge; the dashboard pings PR authors when their reviewer is out and reroutes to the guild backup.", "preference", "ai_coding", False,
     [("review SLA", "concept"), ("dashboard", "service")],
     [],
     "which review-cycle SLA did the team commit to and what happens when a reviewer is unavailable",
     "review sla one business day first response three day merge backup"),
    # --- 5 ---
    ("Async-first review culture means every PR carries a written walkthrough in the description; synchronous pairing is reserved for refactors that touch more than four packages.", "decision", "ai_coding", False,
     [("Async-first", "pattern"), ("walkthrough", "concept"), ("pairing", "activity")],
     [],
     "which review culture did we pick as default and when do we still fall back to synchronous pairing",
     "async first review culture walkthrough pairing refactor exception"),
    # --- 6 ---
    ("Migrated from stacked-PR shell scripts to Graphite for chained reviews; the dependency graph between PRs is now explicit and rebases cascade automatically across the stack.", "milestone", "ai_coding", False,
     [("Graphite", "tool"), ("stacked-PR", "pattern"), ("rebase", "command")],
     [("Graphite", "stacked-PR", "REPLACES")],
     "which tool replaced our home-grown stacked-PR scripts and what does it do that the scripts didn't",
     "graphite stacked pr chain rebase cascade dependency graph migrate"),
    # --- 7 ---
    ("Two-reviewer rule kicks in for any change to billing, auth, or migration files; one reviewer must be a CODEOWNER and the other can be any senior engineer outside the team.", "decision", "ai_coding", False,
     [("Two-reviewer rule", "pattern"), ("billing", "service"), ("CODEOWNER", "concept")],
     [],
     "which directories trigger the two-reviewer rule and how are the two slots allocated",
     "two reviewer rule billing auth migration codeowner senior outside"),
    # --- 8 ---
    ("Mentorship pairing assigns each new hire a review buddy for their first ten PRs; the buddy reviews first and tags a senior only if a blocking issue surfaces.", "architecture", "ai_coding", False,
     [("review buddy", "person"), ("new hire", "person"), ("Mentorship", "concept")],
     [],
     "how does the review-buddy pairing protect new hires during their first ten PRs",
     "mentor pair buddy new hire ten pr first review escalate senior"),
    # --- 9 ---
    ("Junior onboarding flow front-loads small documentation PRs in week one so newcomers feel the review loop before touching production code; we tracked time-to-first-merge dropping from nine days to two.", "milestone", "ai_coding", False,
     [("onboarding", "concept"), ("documentation PRs", "pattern"), ("time-to-first-merge", "concept")],
     [],
     "which onboarding pattern shortened time-to-first-merge for juniors and what was the actual delta",
     "junior onboarding doc pr week one time to first merge nine two"),
    # --- 10. noise ---
    ("The barista at the corner cafe started writing tiny seasonal poems on the takeaway cups again this month.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Review fatigue showed up as a 30 percent drop in comments per PR after lunch on Fridays; we capped each reviewer at five active PRs and let the queue surface elsewhere.", "problem", "ai_coding", False,
     [("Review fatigue", "emotion"), ("queue", "concept")],
     [],
     "which signal told us review fatigue was real and what limit did we put on active PRs per reviewer",
     "review fatigue friday afternoon cap five active pr queue rotate"),
    # --- 12 ---
    ("Lint-first triage runs ruff, prettier, and golangci-lint on every push so reviewers never spend a comment on style; humans only weigh in once the bot reports green.", "architecture", "ai_coding", False,
     [("ruff", "tool"), ("prettier", "tool"), ("golangci-lint", "tool"), ("Lint-first", "pattern")],
     [("Lint-first", "ruff", "USES")],
     "which style bots run before humans look at a PR and what does that buy in reviewer attention",
     "lint first ruff prettier golangci style bot triage human attention"),
    # --- 13 ---
    ("The blocking-versus-nit distinction got encoded in danger.js: any thread tagged blocking auto-marks the PR as changes-requested, while nit threads never gate merge.", "architecture", "ai_coding", False,
     [("danger.js", "tool"), ("blocking", "pattern"), ("nit", "pattern"), ("changes-requested", "pattern")],
     [],
     "how does danger.js automate the blocking-versus-nit distinction during code review",
     "danger js blocking nit auto changes requested gate merge enforce"),
    # --- 14 ---
    ("Review-time analytics live in a Looker dashboard fed by GitHub events; median time-to-first-review, time-to-merge, and reviewer load surface per team weekly.", "fact", "ai_coding", False,
     [("Looker", "tool"), ("GitHub", "platform"), ("time-to-first-review", "concept"), ("time-to-merge", "concept")],
     [("Looker", "GitHub", "USES")],
     "which review-time metrics does the Looker dashboard surface and where do the events come from",
     "review analytics looker github median time first merge load weekly"),
    # --- 15 ---
    ("Approving PRs you authored sections of is allowed only if a co-author block in the commit trailer names the other contributor; the pre-merge bot rejects self-approvals otherwise.", "preference", "ai_coding", False,
     [("co-author", "pattern"), ("commit trailer", "pattern"), ("pre-merge bot", "service")],
     [],
     "which rule lets a contributor approve a PR they partially authored and how is it enforced",
     "approve own pr co author trailer commit pre merge bot enforce"),
    # --- 16 ---
    ("Post-merge review for hotfixes lands in a follow-up ticket within 24 hours; the on-call engineer ships the patch immediately, then a CODEOWNER walks the diff after the incident closes.", "architecture", "ai_coding", False,
     [("Post-merge review", "pattern"), ("hotfix", "concept"), ("on-call", "person"), ("CODEOWNER", "concept")],
     [],
     "how does the team handle review on hotfixes that ship before a normal review cycle finishes",
     "post merge review hotfix on call codeowner follow up ticket 24 hour"),
    # --- 17 ---
    ("Cited Software Engineering at Google chapter 9 on code review when arguing for the small-CL norm; the team adopted a 200-line soft cap and a 400-line hard cap on PR size.", "reference", "ai_coding", False,
     [("Software Engineering at Google", "publication"), ("small-CL norm", "concept"), ("PR size", "concept")],
     [("small-CL norm", "Software Engineering at Google", "BUILDS_ON")],
     "which book chapter grounded our small-CL norm and what numeric caps did we agree on",
     "software engineering google chapter nine code review small cl cap"),
    # --- 18 ---
    ("Migrated the kernel-module review flow from email patches to Gerrit; the per-line voting and patch-set rebase tracking immediately killed the merge-conflict ping-pong on big series.", "milestone", "ai_coding", False,
     [("Gerrit", "tool"), ("email patches", "pattern"), ("patch-set", "concept")],
     [("Gerrit", "email patches", "IMPROVES_ON")],
     "which review tool replaced email-patch workflows and which pain points did the migration close",
     "gerrit email patch migrate per line vote patch set rebase track"),
    # --- 19 ---
    ("Reviewable's draft-comment workflow let us batch threads before posting; the noise from ten dribbling comments on a single push went away once everyone learned to publish in one shot.", "preference", "ai_coding", False,
     [("Reviewable", "tool"), ("draft-comment", "pattern")],
     [],
     "which review tool's draft-comment feature did we lean on to avoid spamming notifications",
     "reviewable draft comment batch publish single shot notification noise"),
    # --- 20 ---
    ("Phabricator's Differential is still our reference for revision-based review semantics; the Diff/Revision split influenced how we model stacked changes inside Graphite today.", "reference", "ai_coding", False,
     [("Phabricator", "tool"), ("Differential", "tool"), ("Graphite", "tool")],
     [("Graphite", "Differential", "BUILDS_ON")],
     "which legacy review tool's revision model still informs how we think about stacked diffs",
     "phabricator differential revision diff stacked change graphite influence"),
    # --- 21 ---
    ("The author-driven model means the PR author requests specific reviewers based on file expertise rather than spraying the whole team; CODEOWNERS suggests defaults but the human decides.", "decision", "ai_coding", False,
     [("author-driven", "pattern"), ("CODEOWNERS", "file")],
     [],
     "which review-assignment model does the team prefer and what role does CODEOWNERS play in it",
     "author driven request reviewer expertise codeowners suggest default"),
    # --- 22 ---
    ("Started running review pairing sessions every other Friday: a senior and a junior co-review a hairy PR live, narrating the decision tree out loud for the recording.", "fact", "ai_coding", False,
     [("review pairing", "activity"), ("Friday", "date"), ("recording", "concept")],
     [],
     "which mentoring ritual pairs a senior and junior on a live review and what gets recorded",
     "review pairing friday senior junior live narrate decision recording"),
    # --- 23 ---
    ("Killed the merge-train dashboard when nobody looked at it for six weeks; the GitHub native merge queue carries enough signal once the lint and test gates are green.", "decision", "ai_coding", False,
     [("merge-train", "tool"), ("merge queue", "tool"), ("GitHub", "platform")],
     [("merge queue", "merge-train", "REPLACES")],
     "which review-tooling cleanup removed the merge-train dashboard and what took its place",
     "merge train dashboard retire github merge queue native lint test"),
    # --- 24 ---
    ("Junior reviewers get an explicit license to ask why; the rule is that no question is a nit and senior authors must answer in-thread rather than DMing the answer.", "preference", "ai_coding", False,
     [("Junior reviewers", "person"), ("senior authors", "person")],
     [],
     "which review norm protects juniors who ask basic questions and where must the answer land",
     "junior reviewer ask why answer in thread senior author dm avoid"),
    # --- 25 ---
    ("Banned approving with no comment for any PR over 50 lines; the LGTM-only approval used to hide rubber-stamp behaviour, so reviewers must now leave at least one substantive note.", "preference", "ai_coding", False,
     [("LGTM-only", "pattern"), ("rubber-stamp", "pattern")],
     [("LGTM-only", "rubber-stamp", "CAUSES")],
     "which review anti-pattern did we ban for medium-or-larger PRs and what did the rule replace",
     "lgtm only ban rubber stamp 50 line substantive comment require"),
    # --- 26 ---
    ("The architecture-review checklist piggybacks on the PR description; for any change touching a service boundary, the author fills in a Why-now, Alternatives, and Blast-radius block.", "architecture", "ai_coding", False,
     [("architecture-review", "concept"), ("service boundary", "concept"), ("Blast-radius", "concept")],
     [],
     "which checklist gets attached to PRs that cross a service boundary and what fields does it carry",
     "architecture review checklist service boundary why now blast radius"),
    # --- 27 ---
    ("Shadow reviews let an aspiring senior leave non-binding comments on a PR a staff engineer is reviewing; the staff engineer rolls them up before posting and tags learnings privately.", "fact", "ai_coding", False,
     [("Shadow reviews", "pattern"), ("staff engineer", "person")],
     [],
     "how do shadow reviews work as a mentoring path for engineers aiming for staff",
     "shadow review aspiring senior staff non binding roll up learning"),
    # --- 28 ---
    ("Review-fatigue mitigation includes a hard rule that nobody opens GitHub before 10am on Mondays; the queue is still there, but the deep-work window stays sacred.", "preference", "ai_coding", False,
     [("Review-fatigue", "emotion"), ("Monday", "date"), ("deep-work", "concept")],
     [],
     "which schedule rule guards engineer mornings against the review queue and why",
     "review fatigue monday morning deep work window block github 10am"),
    # --- 29 ---
    ("Adopted a practice of leaving one positive observation per review; the goal is psychological safety, and the lift in junior PR throughput in the next quarter was measurable.", "fact", "ai_coding", False,
     [("positive observation", "pattern"), ("psychological safety", "concept"), ("junior PR throughput", "goal")],
     [],
     "which small ritual did reviewers add to lift psychological safety and what metric moved",
     "positive observation review psychological safety junior throughput"),
    # --- 30 ---
    ("Suggestion blocks via GitHub's apply-suggestion feature replaced the back-and-forth of nit comments on small refactors; authors hit Apply and the change lands without another round trip.", "decision", "ai_coding", False,
     [("Suggestion blocks", "pattern"), ("GitHub", "platform"), ("apply-suggestion", "method"), ("nit comments", "pattern")],
     [("Suggestion blocks", "nit comments", "REPLACES")],
     "which GitHub feature replaced multi-round nit comments on small refactor suggestions",
     "github suggestion block apply nit comment small refactor round trip"),
    # --- 31 ---
    ("First-90-day onboarding includes a guided tour of three exemplar PRs and three exemplar reviews; the new hire annotates what they noticed before pairing with their buddy.", "architecture", "ai_coding", False,
     [("onboarding", "concept"), ("exemplar PRs", "pattern"), ("buddy", "person")],
     [],
     "which 90-day onboarding artefact teaches new hires what good PRs and reviews look like here",
     "onboarding 90 day exemplar pr review annotate buddy pairing tour"),
    # --- 32 ---
    ("Wrote the team's review handbook as a living doc in Notion; the principles, prefix conventions, SLA, and escalation paths all sit in one page that gets a quarterly walk-through.", "fact", "ai_coding", False,
     [("review handbook", "publication"), ("Notion", "tool"), ("escalation", "concept")],
     [],
     "where does the team's review handbook live and what cadence does the walk-through follow",
     "review handbook notion living doc principle prefix sla escalation"),
    # --- 33 ---
    ("CODEOWNERS got auto-generated from a YAML manifest after manual edits drifted; the build step renders .github/CODEOWNERS and fails CI if the manifest and file disagree.", "milestone", "ai_coding", False,
     [("CODEOWNERS", "file"), (".github/CODEOWNERS", "file"), ("YAML manifest", "config")],
     [("YAML manifest", "CODEOWNERS", "PRODUCES")],
     "how does the CODEOWNERS file stay in sync with the source-of-truth YAML manifest",
     "codeowners auto generate yaml manifest drift ci build render gate"),
    # --- 34 ---
    ("The reviewer-load balancer in pull-bot rotates assignments based on open-PR count rather than round-robin; staff engineers stopped getting buried whenever the round robin landed on them.", "problem", "ai_coding", False,
     [("pull-bot", "tool"), ("reviewer-load balancer", "pattern"), ("round-robin", "algorithm")],
     [("reviewer-load balancer", "round-robin", "REPLACES")],
     "which reviewer-assignment algorithm change stopped staff engineers from getting buried in PRs",
     "reviewer load balancer pull bot rotate open pr round robin retire"),
    # --- 35 ---
    ("Spec-first PRs land a design doc as the first commit and the implementation as later commits; reviewers can request changes on the design before any code review begins.", "architecture", "ai_coding", False,
     [("Spec-first", "pattern"), ("design doc", "concept")],
     [],
     "which PR-structure pattern lets reviewers gate the design before reading the implementation",
     "spec first pr design doc first commit implementation later gate"),
    # --- 36 ---
    ("Junior-led architecture-review week rotates a junior engineer into the chair role for a week; the senior chair shadows and the junior runs the meeting, builds the agenda, and posts notes.", "fact", "ai_coding", False,
     [("junior engineer", "person"), ("chair role", "concept"), ("senior chair", "person")],
     [],
     "which mentoring rotation puts a junior in the architecture-review chair seat",
     "junior chair architecture review week rotate senior shadow agenda"),
    # --- 37 ---
    ("The post-mortem on a botched migration noted that nobody had asked the migration question on the PR; we added a What-could-go-wrong-on-replicas prompt to the migration template.", "problem", "ai_coding", False,
     [("post-mortem", "concept"), ("migration", "concept"), ("template", "pattern")],
     [],
     "which review prompt did we add to the migration template after a post-mortem flagged the gap",
     "post mortem migration prompt template replica what could go wrong"),
    # --- 38 ---
    ("Replaced ad-hoc nit and blocking marks across the org with the Conventional Comments spec; the spec at conventionalcomments.org gets linked in the review handbook.", "decision", "ai_coding", False,
     [("Conventional Comments", "publication"), ("conventionalcomments.org", "concept"), ("review handbook", "publication")],
     [("Conventional Comments", "review handbook", "PUBLISHED_IN")],
     "which external spec did we standardise on for review-comment prefixes and where is it linked",
     "conventional comments spec dot org review handbook link standard"),
    # --- 39 ---
    ("Senior engineers run a weekly review-of-reviews where they read three random PR threads and grade tone, signal, and pace; patterns feed the next handbook revision.", "fact", "ai_coding", False,
     [("Senior engineers", "person"), ("review-of-reviews", "activity"), ("handbook", "publication")],
     [],
     "which meta-review ritual feeds back into handbook revisions and what gets graded",
     "review of reviews senior weekly random thread tone signal pace"),
    # --- 40. noise ---
    ("Someone left a small ceramic frog on the printer last week and nobody has admitted to it yet.", "fact", "noise", True, [], [], None, None),
    # --- 41 ---
    ("Cited The Pragmatic Programmer's broken-window principle when arguing for fixing review nits in the same PR; small decay compounds, so we let trivial cleanups land alongside the feature.", "reference", "ai_coding", False,
     [("The Pragmatic Programmer", "publication"), ("broken-window", "concept")],
     [("broken-window", "The Pragmatic Programmer", "PUBLISHED_IN")],
     "which book idea grounded our preference for fixing nits in the same PR rather than deferring",
     "pragmatic programmer broken window nit same pr decay compound"),
    # --- 42 ---
    ("Risk-tier labels on PRs drive the review template: low-risk PRs get a lightweight checklist and high-risk PRs require a recorded walkthrough plus two CODEOWNER approvals.", "architecture", "ai_coding", False,
     [("Risk-tier", "pattern"), ("walkthrough", "concept"), ("CODEOWNER", "concept")],
     [],
     "how do PR risk-tier labels change which review template and approval count gets enforced",
     "risk tier label pr template walkthrough codeowner approval count"),
    # --- 43 ---
    ("Time-zone-aware reviewer assignment routes PRs opened after 4pm local to a colleague in the next time zone; first-response SLA stays under 24 hours despite the global team.", "architecture", "ai_coding", False,
     [("Time-zone-aware", "pattern"), ("global team", "organization"), ("first-response SLA", "concept")],
     [],
     "which assignment heuristic keeps first-response SLA under 24 hours for a globally distributed team",
     "time zone aware reviewer assignment 4pm next zone global sla 24"),
    # --- 44 ---
    ("Killed the daily standup recap of open PRs in favour of a Slack bot that DMs each person their personal review queue at 9am local; the all-hands time savings were immediate.", "decision", "ai_coding", False,
     [("standup", "activity"), ("Slack bot", "service"), ("review queue", "concept")],
     [("Slack bot", "standup", "REPLACES")],
     "which automation replaced the standup recap of open PRs and what time savings did it produce",
     "standup recap retire slack bot dm personal review queue 9am savings"),
    # --- 45 ---
    ("The two-reviewer rule for risky areas has a documented exception: a single Distinguished Engineer can solo-approve a same-day rollback with a written justification appended afterwards.", "fact", "ai_coding", False,
     [("two-reviewer rule", "pattern"), ("Distinguished Engineer", "person"), ("rollback", "concept")],
     [],
     "which carve-out lets a Distinguished Engineer solo-approve a same-day rollback under the two-reviewer rule",
     "two reviewer rule exception distinguished engineer rollback solo justify"),
    # --- 46 ---
    ("Review etiquette guide bans mentioning the author's tenure or seniority in any thread; comments must address the code, not the person, and violations get gently flagged in 1:1s.", "preference", "ai_coding", False,
     [("etiquette guide", "publication"), ("1:1", "activity")],
     [],
     "which review-etiquette rule keeps comments focused on code rather than the author's experience level",
     "etiquette ban tenure seniority mention code not person 1 1 flag"),
    # --- 47 ---
    ("Adopted async stand-in reviewers via a rotation file in .github/ROTATION.yml; if the primary CODEOWNER is on PTO, the stand-in inherits the assignment automatically.", "architecture", "ai_coding", False,
     [(".github/ROTATION.yml", "file"), ("CODEOWNER", "concept"), ("PTO", "concept")],
     [],
     "which rotation mechanism keeps reviews flowing when the primary CODEOWNER is on PTO",
     "rotation yml github stand in codeowner pto async inherit assign"),
    # --- 48 ---
    ("Cited Karl Wiegers's Peer Reviews in Software when arguing for inspection-style reviews on the auth-service; we now run a structured review meeting on changes touching token issuance.", "reference", "ai_coding", False,
     [("Karl Wiegers", "person"), ("Peer Reviews in Software", "publication"), ("auth-service", "service"), ("token issuance", "concept")],
     [("Peer Reviews in Software", "Karl Wiegers", "AUTHORED_BY")],
     "which book grounded the inspection-style review meeting we run for auth-service token changes",
     "wiegers peer reviews software inspection auth service token meeting"),
    # --- 49 ---
    ("Approval-stale-after-push rule resets reviewer approvals whenever the author force-pushes; the bot leaves a comment explaining why so juniors don't think their reviewer ghosted them.", "architecture", "ai_coding", False,
     [("Approval-stale-after-push", "pattern"), ("force-push", "command"), ("bot", "service")],
     [],
     "which protection rule resets approvals on a force-push and how does it explain itself to the author",
     "approval stale force push reset bot comment junior ghost explain"),
    # --- 50 ---
    ("New-hire graduation from buddy review happens once they ship ten merged PRs and have reviewed five PRs of their own; the milestone goes into the engineering ladder doc.", "milestone", "ai_coding", False,
     [("buddy review", "activity"), ("engineering ladder", "publication"), ("New-hire", "person")],
     [],
     "which two thresholds graduate a new hire out of buddy review and where is the milestone tracked",
     "buddy graduation ten merged five reviewed engineering ladder doc"),
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
