"""One-off emitter for shared-base batch-056 — ai_coding domain (architecture decisions / ADRs / RFC process / engineering decision making).

Writes 50 rows to data/v2/shared/batch_056.tmp.jsonl with ids shared-02751..02800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_056.tmp.jsonl"
ID_OFFSET = 2750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Picked the MADR template over Michael Nygard's original because the structured context and consequence sections survived contact with PR review better.", "decision", "ai_coding", False,
     [("MADR", "pattern"), ("Michael Nygard", "person")],
     [("MADR", "Michael Nygard", "PREFERS")],
     "which ADR template did the team standardise on and what made it stick during reviews",
     "madr template nygard choice structured section review friction"),
    # --- 2 ---
    ("ADRs live under doc/adr at the repo root; the adr-tools CLI creates a new file with the next sequence number and opens it in the editor.", "architecture", "ai_coding", False,
     [("doc/adr", "file"), ("adr-tools", "tool")],
     [],
     "where do architecture decision records live in the repo and which tool creates them",
     "adr location doc folder sequence number cli create new record"),
    # --- 3 ---
    ("Every ADR starts in status proposed; it only flips to accepted after the PR hits approval plus a 48-hour silent window on the team channel.", "architecture", "ai_coding", False,
     [("proposed", "pattern"), ("accepted", "pattern")],
     [("accepted", "proposed", "REPLACES")],
     "how does an architecture decision record move from draft to accepted in this team",
     "adr status lifecycle proposal accept silent window approval flip"),
    # --- 4 ---
    ("When a new ADR overrides an older one, the new file sets status to accepted and the old one flips to superseded with a back-link to the successor id.", "architecture", "ai_coding", False,
     [("superseded", "pattern"), ("accepted", "pattern")],
     [("accepted", "superseded", "REPLACES")],
     "how do we record that one decision record replaces another without losing history",
     "superseded adr link successor status change bidirectional audit"),
    # --- 5 ---
    ("RFC lifecycle has five named stages: idea, draft, comment, decision and retro; each stage has an owner and a maximum duration before escalation.", "architecture", "ai_coding", False,
     [("RFC", "pattern"), ("comment", "pattern"), ("retro", "pattern")],
     [],
     "which named stages does the RFC process walk through from seed to post mortem",
     "rfc stage idea draft comment decision retro owner timeout"),
    # --- 6 ---
    ("Comment window for an RFC runs two calendar weeks by default; the author can compress to one if it blocks a release but must note the rush in the header.", "preference", "ai_coding", False,
     [("RFC", "pattern")],
     [],
     "how long does the comment window on an RFC stay open and when can it shrink",
     "rfc comment window two weeks compress release blocker note"),
    # --- 7 ---
    ("We run decisions under DACI rather than RACI because naming a single Approver and a single Driver keeps the bystander-approver trap at bay.", "decision", "ai_coding", False,
     [("DACI", "pattern"), ("RACI", "pattern")],
     [("DACI", "RACI", "PREFERS")],
     "which decision framework did we adopt over the classic responsibility matrix and why",
     "daci raci rapid framework approver driver single owner clarity"),
    # --- 8 ---
    ("Disagree and commit is written into the engineering handbook: once a decision is accepted, raising the same argument again requires new evidence, not taste.", "preference", "ai_coding", False,
     [("engineering handbook", "publication")],
     [],
     "which norm governs how we reopen an accepted decision in the team handbook",
     "disagree commit norm reopen decision new evidence taste rule"),
    # --- 9 ---
    ("Tech spec template forces a Non-Goals section before the Design section; reviewers catch scope creep there before it hides inside the implementation plan.", "architecture", "ai_coding", False,
     [("Non-Goals", "pattern"), ("Design", "pattern")],
     [],
     "which tech spec section do we require before the design in order to catch scope creep",
     "non goals section tech spec scope control reviewer catch creep"),
    # --- 10. noise ---
    ("The neighbour's cat keeps trying to climb the fig tree and meowing until someone opens the window.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Adopted Amazon's six-pager for group-wide strategy reviews but kept a two-page PRFAQ for product-facing launch decisions; the depth matches the audience.", "decision", "ai_coding", False,
     [("six-pager", "pattern"), ("PRFAQ", "pattern")],
     [],
     "which long-form and short-form Amazon narrative formats did we adopt for which audiences",
     "six pager prfaq amazon narrative strategy product launch split"),
    # --- 12 ---
    ("Inception review happens before the ADR is drafted; the design review happens before implementation starts — the two checkpoints never collapse into one meeting.", "architecture", "ai_coding", False,
     [("Inception", "event"), ("design review", "event")],
     [],
     "which two review checkpoints gate a new architecture change and why keep them separate",
     "inception design review checkpoint separation gate timing rule"),
    # --- 13 ---
    ("Decisions that got rejected still get a ghost ADR with status not-accepted; it stops the same debate resurrecting every six months with no memory of why.", "preference", "ai_coding", False,
     [("ghost ADR", "pattern"), ("not-accepted", "pattern")],
     [],
     "how do we stop rejected design ideas from being revisited without context later",
     "ghost adr not accepted record reject rationale institutional memory"),
    # --- 14 ---
    ("Codified our layering conventions as architecture fitness functions that run in CI; a PR that breaks the domain-to-infrastructure import rule fails before review.", "architecture", "ai_coding", False,
     [("fitness functions", "pattern"), ("CI", "infrastructure")],
     [],
     "which automated mechanism enforces our layering rules so reviewers do not have to",
     "architecture fitness function ci gate import layering enforce"),
    # --- 15 ---
    ("Ran an ATAM-style evaluation on the ingestion redesign: two scenario workshops surfaced a latency risk the original proposal had buried under throughput claims.", "fact", "ai_coding", False,
     [("ATAM", "method"), ("ingestion", "concept")],
     [],
     "which architecture evaluation method exposed a latency risk in the ingestion redesign",
     "atam scenario workshop tradeoff latency risk surface hidden"),
    # --- 16 ---
    ("Every system in the catalogue ships a C4 context, container and component diagram; the code-level view is generated from the repo on demand, not hand-drawn.", "architecture", "ai_coding", False,
     [("C4", "method"), ("container", "concept"), ("component", "concept")],
     [],
     "which diagram model do we publish for each service and which level is generated",
     "c4 model context container component diagram generated code level"),
    # --- 17 ---
    ("Design docs follow the arc42 template; the cross-cutting concerns and runtime view sections catch the non-functional gaps our old free-form docs missed.", "decision", "ai_coding", False,
     [("arc42", "pattern")],
     [],
     "which German-origin design-doc template did we adopt and which sections proved valuable",
     "arc42 template cross cutting concern runtime view non functional"),
    # --- 18 ---
    ("Team decision log lives on the wiki as a flat table; lightweight rulings that do not deserve a full ADR end up there with a date, author, and one-line rationale.", "architecture", "ai_coding", False,
     [("decision log", "pattern"), ("wiki", "tool")],
     [],
     "where do small rulings that do not merit a full ADR get recorded in the team",
     "decision log wiki table lightweight ruling date author rationale"),
    # --- 19 ---
    ("Lightweight ADRs started in GitHub Discussions for speed; the heavy, cross-team ones still land in Confluence because product and legal read there.", "decision", "ai_coding", False,
     [("GitHub Discussions", "platform"), ("Confluence", "platform")],
     [("GitHub Discussions", "Confluence", "PREFERS")],
     "which platforms host our lightweight versus heavy architecture decision records and why",
     "github discussions confluence adr split audience product legal"),
    # --- 20 ---
    ("The handbook distinguishes a decision — recorded, owned, reversible with process — from a conclusion that ends a discussion but binds nobody.", "preference", "ai_coding", False,
     [("handbook", "publication")],
     [],
     "which distinction does our handbook draw between a decision and a mere conclusion",
     "decision conclusion distinction binding record ownership handbook"),
    # --- 21 ---
    ("Onboarding reading list pulls the latest ten accepted ADRs into a curated folder; new hires can trace current design back to its rationale without a guide.", "architecture", "ai_coding", False,
     [("Onboarding", "event")],
     [],
     "how do ADRs feed into the engineering onboarding path for new hires",
     "onboarding reading list curated adr rationale ramp up self serve"),
    # --- 22. noise ---
    ("The office plant by the south window finally flowered after six months of very polite neglect from everyone.", "fact", "noise", True, [], [], None, None),
    # --- 23 ---
    ("RFC template now requires an Alternatives Considered section with at least two rejected options; reviewers bounce the doc back if the section is a formality.", "preference", "ai_coding", False,
     [("Alternatives Considered", "pattern")],
     [],
     "which RFC section gates the proposal and how many real alternatives must it list",
     "alternatives considered section rfc reject option minimum serious"),
    # --- 24 ---
    ("Meta-ADR zero defines the ADR process itself; changing sequencing, storage or template requires bumping ADR-0000 rather than patching rules in the wiki.", "architecture", "ai_coding", False,
     [("ADR-0000", "config"), ("wiki", "tool")],
     [],
     "which bootstrap document governs the ADR process and how do we change the rules",
     "meta adr zero process governance bump template storage rules"),
    # --- 25 ---
    ("PR-based ADR reviews require two approvals from different teams; a single team nodding through cross-cutting decisions was how the logging rewrite ambushed SRE.", "preference", "ai_coding", False,
     [("PR", "pattern"), ("SRE", "organization")],
     [],
     "which review rule prevents a single team from landing cross-cutting architecture decisions alone",
     "pr adr review two team approval cross cutting sre ambush"),
    # --- 26 ---
    ("Design doc graveyard keeps retired proposals under /docs/retired with a redirect stub; search results still find them but with a prominent do-not-use banner.", "architecture", "ai_coding", False,
     [("/docs/retired", "file")],
     [],
     "how do we keep abandoned design docs searchable without luring readers into following them",
     "design doc graveyard retired redirect stub banner search warn"),
    # --- 27 ---
    ("Decision expiry dates are required on any ADR tagged time-bound; the doc bot opens a review issue 30 days before the expiry so it never rots quietly.", "architecture", "ai_coding", False,
     [("doc bot", "tool"), ("time-bound", "pattern")],
     [],
     "how do time-bound decisions get re-examined before their rationale silently expires",
     "decision expiry date bot review issue thirty day rot avoid"),
    # --- 28 ---
    ("ADR ids are zero-padded four digits; adr-0042 sorts before adr-0100 in every tool we touch, including the dumb terminal listings our ops scripts emit.", "preference", "ai_coding", False,
     [("adr-0042", "config"), ("adr-0100", "config")],
     [],
     "which ADR id format keeps lexicographic sort working across every tool the team uses",
     "adr id zero pad four digit sort lexicographic tool compatibility"),
    # --- 29 ---
    ("Every RFC carries a one-line tl;dr at the top; reviewers who only read the first paragraph still capture the proposed change correctly seven times out of ten.", "fact", "ai_coding", False,
     [("RFC", "pattern"), ("tl;dr", "pattern")],
     [],
     "which habit at the top of each RFC improves skim-reader comprehension measurably",
     "tldr one line rfc top summary skim reviewer capture rate"),
    # --- 30 ---
    ("Shadow-owners are explicit on every ADR: the person who drafted it, the team who lives with it, and the architect on call for escalation sit in three named slots.", "architecture", "ai_coding", False,
     [("ADR", "pattern")],
     [],
     "which three named roles appear on every architecture decision record header",
     "adr role draft owner team living architect escalate three slot"),
    # --- 31 ---
    ("A rejected ADR still runs the full review; skipping the write-up because everyone knows the answer is how we lost the rationale behind the websocket rejection in 2024.", "preference", "ai_coding", False,
     [("ADR", "pattern"), ("2024", "date")],
     [],
     "why do we insist on completing the full ADR write-up even for obviously rejected proposals",
     "rejected adr full write up rationale capture skip lost memory"),
    # --- 32 ---
    ("Decision retrospectives run six months after acceptance; the retro note appends to the original ADR instead of spawning a new file so the history stays linear.", "architecture", "ai_coding", False,
     [("ADR", "pattern")],
     [],
     "when do we retro an accepted decision and where does the retrospective land",
     "retro six month decision append original adr history linear"),
    # --- 33 ---
    ("Introduced tech-radar entries tied to ADRs: moving a technology from assess to adopt always has an ADR id on the radar card, never a free-form note.", "architecture", "ai_coding", False,
     [("tech-radar", "tool"), ("assess", "pattern"), ("adopt", "pattern")],
     [("adopt", "assess", "REPLACES")],
     "which artefact links our tech radar rings to the architecture decision records behind them",
     "tech radar entry ring assess adopt adr id link card"),
    # --- 34 ---
    ("The engineering council meets monthly to rule on RFCs that cross team boundaries; in-team RFCs stop at the team lead and never touch the council agenda.", "architecture", "ai_coding", False,
     [("engineering council", "organization")],
     [],
     "which body decides cross-team RFCs and which ones bypass it entirely",
     "engineering council monthly cross team rfc scope lead bypass"),
    # --- 35 ---
    ("Our ADR writing style forbids marketing adjectives: words like robust, scalable and elegant get flagged by the linter until the author replaces them with measurable claims.", "preference", "ai_coding", False,
     [("ADR", "pattern")],
     [],
     "which lint rule reshapes ADR prose toward measurable claims and away from marketing words",
     "adr lint adjective robust scalable measurable claim writing style"),
    # --- 36 ---
    ("Promoted the API deprecation process to its own ADR once three teams had made ad-hoc decisions that contradicted each other on the same public surface.", "decision", "ai_coding", False,
     [("API", "concept"), ("ADR", "pattern")],
     [],
     "which recurring cross-team contradiction pushed us to codify a deprecation process in an ADR",
     "deprecation process adr cross team contradiction codify ad hoc"),
    # --- 37 ---
    ("RFC authors pick exactly one primary decision-maker in the header; a single name makes the async review end cleanly instead of drifting into collective silence.", "preference", "ai_coding", False,
     [("RFC", "pattern")],
     [],
     "which RFC header field forces a named terminator for the async review",
     "rfc primary decision maker header named terminator async review"),
    # --- 38 ---
    ("Adopted the improves-on relation between ADRs when the change is additive rather than contradictory; the older doc keeps status accepted and grows a successor link.", "architecture", "ai_coding", False,
     [("improves-on", "pattern"), ("ADR", "pattern")],
     [("improves-on", "ADR", "BUILDS_ON")],
     "which ADR relation covers additive follow-ons without flipping the predecessor to superseded",
     "improves on relation additive follow on accepted successor link"),
    # --- 39 ---
    ("Design review checklist includes a reversibility question: can we undo this in one sprint, one quarter or never? One-way-door calls trigger a mandatory second opinion.", "architecture", "ai_coding", False,
     [("Design review", "event")],
     [],
     "which reversibility question on the design review checklist escalates to a second opinion",
     "reversibility one way door sprint quarter never second opinion"),
    # --- 40 ---
    ("Kept design docs out of the main repo for two years and regretted it; folded them back under /docs so a git blame on code reaches the rationale via one click.", "problem", "ai_coding", False,
     [("/docs", "file"), ("git blame", "command")],
     [],
     "which location decision for design docs did we reverse and what did it unlock",
     "design doc repo location folder blame rationale link reverse"),
    # --- 41 ---
    ("RFC authors must pick a decision format upfront: consensus, consent or dictator-for-a-day; changing mid-thread is the fastest way to a stuck review.", "preference", "ai_coding", False,
     [("consensus", "pattern"), ("consent", "pattern"), ("dictator-for-a-day", "pattern")],
     [],
     "which decision format choice must an RFC author commit to before the review opens",
     "consensus consent dictator format rfc upfront stuck review"),
    # --- 42 ---
    ("Shifted RFC storage from shared drive PDFs to plain markdown in the repo on 2025-11-03; grep finally works across the decision history and diffs are reviewable.", "milestone", "ai_coding", False,
     [("2025-11-03", "date"), ("markdown", "language")],
     [],
     "when did RFC storage move to markdown in the repository and what practical win did that bring",
     "rfc markdown repo migrate pdf shared drive grep diff review"),
    # --- 43 ---
    ("ADR-0000 lists the five statuses we recognise: proposed, accepted, superseded, deprecated and rejected; no project invents a sixth without bumping zero.", "reference", "ai_coding", False,
     [("ADR-0000", "config"), ("deprecated", "pattern"), ("rejected", "pattern")],
     [],
     "which five ADR statuses are sanctioned and who can add a new one",
     "adr status enumeration five proposed accepted superseded deprecated reject"),
    # --- 44 ---
    ("Decision outcomes thread into onboarding as a two-hour architecture walk; the walk leader picks the five ADRs most likely to bite a new hire in their first quarter.", "architecture", "ai_coding", False,
     [("onboarding", "event"), ("ADR", "pattern")],
     [],
     "how do recent architecture decisions reach a new engineer during their onboarding",
     "onboarding architecture walk two hour five adr new hire quarter"),
    # --- 45 ---
    ("Rejected a heavyweight RFC gate for bugfix-grade changes; the overhead was burying fix-forward momentum under ceremony and the data showed no defect reduction.", "decision", "ai_coding", False,
     [("RFC", "pattern")],
     [],
     "which heavyweight process did we reject for bugfix work and what evidence justified it",
     "rfc gate bugfix reject ceremony overhead fix forward defect data"),
    # --- 46 ---
    ("Each ADR carries a confidence tag of low, medium or high; a low tag commits us to a revisit date and a small experiment ticket before the next quarter closes.", "architecture", "ai_coding", False,
     [("ADR", "pattern")],
     [],
     "which calibration tag on an ADR forces a scheduled revisit and a pilot experiment",
     "adr confidence tag low medium high revisit experiment schedule"),
    # --- 47 ---
    ("Design spec template ends with an Open Questions block that ships with the PR; questions get issue ids assigned by a bot so none of them slip through after merge.", "architecture", "ai_coding", False,
     [("Open Questions", "pattern"), ("bot", "tool")],
     [],
     "which closing section of the design spec keeps post-merge questions from getting lost",
     "open questions section design spec issue id bot track merge"),
    # --- 48 ---
    ("Architecture office hours run every Thursday; engineers bring a half-formed idea and leave with either an ADR skeleton or a documented reason not to write one.", "architecture", "ai_coding", False,
     [("Architecture office hours", "event")],
     [],
     "which weekly forum turns half-formed architecture ideas into either a draft ADR or a pass",
     "architecture office hours thursday weekly skeleton pass reason"),
    # --- 49 ---
    ("A decision is only considered landed once the ADR is merged and the linked runbook, dashboard or alert has been updated; code-only merges do not count.", "preference", "ai_coding", False,
     [("ADR", "pattern"), ("runbook", "publication")],
     [],
     "which completion criterion defines when an architecture decision is considered landed",
     "decision landed criterion adr runbook dashboard alert update code"),
    # --- 50 ---
    ("Swapped the quarterly architecture all-hands for a rolling ADR digest email; attendance was optional, the digest is not, and net read-through went up measurably.", "decision", "ai_coding", False,
     [("ADR", "pattern"), ("all-hands", "event")],
     [("ADR", "all-hands", "REPLACES")],
     "which communication ritual replaced the quarterly architecture meeting and why",
     "adr digest email quarterly all hands replace read through attendance"),
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
