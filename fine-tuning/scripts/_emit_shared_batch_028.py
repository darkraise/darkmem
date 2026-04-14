"""One-off emitter for shared-base batch-028 — personal domain (career / work-life slice).

Same pattern as _emit_shared_batch_015.py; only ENTRIES and offsets change.
Writes 50 rows to data/v2/shared/batch_028.tmp.jsonl with ids shared-01351..01400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_028.tmp.jsonl"
ID_OFFSET = 1350

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Turned down the staff engineer offer from Helvetia Analytics on 2026-01-22; the total comp was higher but the on-call rotation would have wrecked the weekends.", "decision", "personal", False,
     [("staff engineer", "goal"), ("Helvetia Analytics", "organization"), ("2026-01-22", "date"), ("on-call rotation", "activity")],
     [],
     "which Swiss-named outfit did I say no to at the senior level and what was the dealbreaker",
     "staff-level offer decline compensation weekend rotation tradeoff date"),
    # --- 2 ---
    ("Negotiated the base up from 165k to 182k at Torrent Labs by waiting twelve days before responding to the verbal.", "milestone", "personal", False,
     [("Torrent Labs", "organization")],
     [],
     "how much did the salary move at the startup and what was the silence tactic",
     "base pay lift seventeen-thousand hush window verbal hold startup"),
    # --- 3 ---
    ("Performance review from Priya on 2025-12-15 flagged my meeting-heavy calendar as the main drag on deep work output.", "reference", "personal", False,
     [("Priya", "person"), ("2025-12-15", "date"), ("meeting-heavy calendar", "concept"), ("deep work", "concept")],
     [],
     "what did the end-of-year assessment from my manager pinpoint as the biggest productivity leak",
     "annual review manager note calendar overload focus-time deficit date"),
    # --- 4 ---
    ("My manager Colin and I stopped talking directly for three weeks after the roadmap meeting on 2025-10-07; HR mediation got us back to a working rhythm.", "problem", "personal", False,
     [("Colin", "person"), ("roadmap meeting", "event"), ("2025-10-07", "date"), ("HR", "organization")],
     [],
     "which autumn planning session triggered the silent stretch with my boss and how did it resolve",
     "manager standoff roadmap date three-week quiet HR mediation outcome"),
    # --- 5 ---
    ("Agreed to mentor Jules weekly for the next two quarters; she reminds me of my own 2018 self right before the first promotion.", "decision", "personal", False,
     [("Jules", "person"), ("2018", "date")],
     [],
     "which junior colleague am I coaching on the weekly cadence and for how long",
     "mentee weekly sessions six-month window recognition earlier career parallel"),
    # --- 6 ---
    ("Filed parental leave paperwork for 2026-07-15; twenty weeks planned, with Hamza taking the back half so we overlap for a week.", "milestone", "personal", False,
     [("parental leave", "event"), ("2026-07-15", "date"), ("Hamza", "person")],
     [],
     "when does the family leave start and how are my partner and I splitting the time",
     "parental leave start date twenty-week partner split overlap week"),
    # --- 7 ---
    ("Sabbatical application went in on 2025-09-18 requesting three months off in late 2026 to finish the woodworking apprenticeship.", "milestone", "personal", False,
     [("Sabbatical", "event"), ("2025-09-18", "date"), ("woodworking apprenticeship", "activity")],
     [],
     "when did I ask for the extended break and what personal project is it meant to unblock",
     "extended leave request autumn submit three-month craft apprenticeship finish"),
    # --- 8 ---
    ("Dropped to four days a week at Meridian Logistics starting 2026-03-01; took a 22 percent pay cut and kept the health plan intact.", "decision", "personal", False,
     [("Meridian Logistics", "organization"), ("2026-03-01", "date"), ("health plan", "concept")],
     [("Meridian Logistics", "health plan", "HAS_PART")],
     "when did the four-day week kick in and what was the financial and benefits hit",
     "part-time shift start date pay reduction benefits retention logistics employer"),
    # --- 9 ---
    ("Career pivot from program management into technical writing is looking real; signed up for the Marigold Tech Comms course on 2026-02-10.", "decision", "personal", False,
     [("program management", "goal"), ("technical writing", "goal"), ("Marigold Tech Comms", "organization"), ("2026-02-10", "date")],
     [("technical writing", "program management", "REPLACES")],
     "which career switch is in motion and what training did I commit to",
     "PM to docs pivot program-to-writing course sign-up date training"),
    # --- 10. noise ---
    ("Hold on, let me pull up the offer letter real quick.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Gave the first all-hands keynote as a director on 2026-04-03 in Austin; 340 people in the room and my hands stopped shaking by slide four.", "milestone", "personal", False,
     [("all-hands keynote", "event"), ("director", "goal"), ("2026-04-03", "date"), ("Austin", "place")],
     [],
     "when was the inaugural director-level company talk and where was it held",
     "first director keynote spring date Texas city crowd size nerves"),
    # --- 12 ---
    ("Commute changed when we moved the office to Rosemont in March; the 52-minute train beats the 40-minute drive on bad-weather days.", "reference", "personal", False,
     [("office", "place"), ("Rosemont", "place"), ("train", "activity"), ("drive", "activity")],
     [("office", "Rosemont", "LOCATED_IN"), ("train", "drive", "PREFERS")],
     "which suburb did the office relocate to and how did my commute math change",
     "office move spring suburb train versus car inclement weather delta"),
    # --- 13 ---
    ("Prefers fully remote Tuesdays and Thursdays over any hybrid mandate; the deep-work blocks only survive when nobody expects me in a chair.", "preference", "personal", False,
     [("fully remote", "activity"), ("hybrid mandate", "concept"), ("deep-work blocks", "concept")],
     [("fully remote", "hybrid mandate", "PREFERS")],
     "which remote cadence do I protect hardest and what does it safeguard",
     "mid-week remote day preference mandate pushback focus block protection"),
    # --- 14 ---
    ("The side consulting with Orchid Systems is capped at eight hours a week so it never touches the main Meridian responsibilities.", "architecture", "personal", False,
     [("Orchid Systems", "organization"), ("Meridian", "organization")],
     [],
     "how is the contracting on the side bounded so it does not bleed into my day job",
     "moonlight gig weekly cap separate employer primary job boundary rule"),
    # --- 15 ---
    ("Attended the Chicago chapter of WIC on 2025-11-12 and reconnected with Maya from the 2019 Kellogg cohort; she is hiring for a VP of Ops.", "milestone", "personal", False,
     [("Chicago", "place"), ("WIC", "organization"), ("2025-11-12", "date"), ("Maya", "person"), ("Kellogg", "organization"), ("VP of Ops", "goal")],
     [("Maya", "Kellogg", "WORKS_AT")],
     "who did I bump into at the networking evening and what role is she trying to fill",
     "city chapter meetup fall date alum reconnection operations lead vacancy"),
    # --- 16 ---
    ("Reached out to Franco from the 2017 grad program this week; he runs product at a Barcelona fintech and wants to chat about a possible role.", "fact", "personal", False,
     [("Franco", "person"), ("2017", "date"), ("Barcelona", "place"), ("fintech", "field")],
     [("Franco", "Barcelona", "LIVES_IN")],
     "which old cohort contact surfaced this week and what is he running",
     "grad program alum reconnection Iberian fintech product lead chat"),
    # --- 17 ---
    ("Signed up for the PMP exam on 2026-05-04 after delaying it for three years; study block is six hours every Saturday until then.", "milestone", "personal", False,
     [("PMP", "concept"), ("2026-05-04", "date")],
     [],
     "when is the deferred project management cert exam and what is my weekly study block",
     "PMP sitting spring date three-year delay Saturday six-hour prep"),
    # --- 18 ---
    ("Moving from healthcare SaaS into renewable energy feels right after the Lumeris sale closed; the mission alignment was missing.", "decision", "personal", False,
     [("healthcare SaaS", "field"), ("renewable energy", "field"), ("Lumeris", "organization"), ("mission alignment", "concept")],
     [("renewable energy", "healthcare SaaS", "REPLACES")],
     "which industry switch am I making post-acquisition and why",
     "sector pivot health to clean energy post-acquisition mission fit reason"),
    # --- 19 ---
    ("Returning to Torrent Labs on 2026-08-04 after the leave; agreed to a phased three-day ramp-up for the first month.", "milestone", "personal", False,
     [("Torrent Labs", "organization"), ("2026-08-04", "date")],
     [],
     "when is the return-to-work date and what is the agreed ramp-up pattern",
     "return from leave August date phased schedule month ramp reboot"),
    # --- 20 ---
    ("Opened the Vanguard retirement projection on 2026-02-28 and realized 57 is still the earliest feasible number even with maxed contributions.", "reference", "personal", False,
     [("Vanguard", "organization"), ("2026-02-28", "date")],
     [],
     "when did I run the retirement number and what age did the math land on",
     "retirement projection date fifty-seven earliest feasible max contribution"),
    # --- 21 ---
    ("Promoted to principal engineer at Meridian on 2025-12-01; the paperwork trailed the announcement by three weeks which stressed me out needlessly.", "milestone", "personal", False,
     [("principal engineer", "goal"), ("Meridian", "organization"), ("2025-12-01", "date")],
     [],
     "when did the principal-level promotion at the logistics firm land and what annoyed me",
     "principal title promotion December date logistics shop paperwork lag stress"),
    # --- 22 ---
    ("Prefers writing performance reviews in one sitting on a Sunday morning over spreading them across a week; the tone stays consistent.", "preference", "personal", False,
     [("performance reviews", "activity"), ("Sunday morning", "date")],
     [],
     "how do I like to draft the team evaluations and why",
     "review writing single-session weekend morning block consistency tone preference"),
    # --- 23 ---
    ("The one-on-one with Mateo on 2025-11-30 was the signal the direct-report relationship had flipped; he is now driving the agenda and I am listening.", "milestone", "personal", False,
     [("Mateo", "person"), ("2025-11-30", "date")],
     [],
     "which report meeting marked the shift in who drives the agenda",
     "one-on-one autumn date direct report dynamic flip agenda ownership"),
    # --- 24 ---
    ("Burned out badly in Q3 2025; the signs were ignoring weekends, flat affect in stand-ups, and skipping the Monday therapist call twice.", "problem", "personal", False,
     [("Q3 2025", "date"), ("weekends", "date"), ("stand-ups", "event"), ("therapist", "person")],
     [],
     "when did the burnout peak and what three signals did I miss",
     "mid-year burnout quarter flags weekend erosion daily meeting numbness therapy skip"),
    # --- 25 ---
    ("Accepted the board observer seat at Halide Robotics on 2026-03-12; four meetings a year, no voting rights, real learning opportunity.", "decision", "personal", False,
     [("board observer", "goal"), ("Halide Robotics", "organization"), ("2026-03-12", "date")],
     [],
     "which non-voting board role did I take on and what is the meeting cadence",
     "observer seat robotics company quarterly meetings no vote learning rationale date"),
    # --- 26 ---
    ("Wrote the first real career narrative document in February; five years mapped out with three decision points if the industry shifts.", "architecture", "personal", False,
     [("career narrative", "concept"), ("February", "date"), ("industry", "concept")],
     [],
     "when did I draft the long-range career plan and how is it structured",
     "career narrative write winter month five-year span branch points plan structure"),
    # --- 27 ---
    ("The exit interview at Lumeris on 2026-01-30 surfaced three things I had buried; honest feedback is easier when you already have the next job lined up.", "reference", "personal", False,
     [("Lumeris", "organization"), ("2026-01-30", "date")],
     [],
     "when was the final interview at the previous employer and what did I finally admit",
     "exit conversation departure date suppressed feedback next gig secured candour"),
    # --- 28 ---
    ("Switched from gmail-based networking to a tiny Fathom CRM in 2025; follow-ups actually happen now instead of dying in threads.", "decision", "personal", False,
     [("gmail", "service"), ("Fathom CRM", "tool"), ("2025", "date")],
     [("Fathom CRM", "gmail", "REPLACES")],
     "what replaced the inbox-only approach to keeping up with my professional circle",
     "CRM tool adoption year inbox method swap follow-up reliability outcome"),
    # --- 29 ---
    ("Dropped out of the certified Scrum Master program on 2025-10-22; the framework stopped matching how we actually run work in the squad.", "decision", "personal", False,
     [("certified Scrum Master", "concept"), ("2025-10-22", "date"), ("squad", "concept")],
     [],
     "which agile credential did I quit mid-way through and why",
     "Scrum credential abandon autumn date methodology mismatch team operating model"),
    # --- 30 ---
    ("The long commute to Lombard used to feel like lost time until I started treating the 45 minutes as dedicated audiobook space; now it is the best part of the day.", "architecture", "personal", False,
     [("Lombard", "place"), ("audiobook", "activity")],
     [],
     "how did I reframe the drive to the western suburb so it stopped feeling wasted",
     "suburban commute reframe audiobook window daily highlight mindset shift"),
    # --- 31 ---
    ("Got the AWS Solutions Architect Professional on 2026-02-19 after failing the first attempt in September; the second try was 890 out of 1000.", "milestone", "personal", False,
     [("AWS Solutions Architect Professional", "concept"), ("2026-02-19", "date"), ("September", "date")],
     [],
     "when did I finally pass the advanced cloud certification and what did I score",
     "cloud pro cert pass winter date earlier fail month high score retake"),
    # --- 32 ---
    ("Lost the promotion bid in the autumn cycle; the written feedback pointed at scope rather than quality, which was at least honest.", "problem", "personal", False,
     [("promotion bid", "concept"), ("autumn cycle", "date")],
     [],
     "which career push did not land and what was the honest reason given",
     "promotion miss autumn round scope gap feedback quality acknowledgement"),
    # --- 33 ---
    ("Prefers the quarterly offsites in Lake Geneva over any remote summit format; the hallway time is where the real alignment happens.", "preference", "personal", False,
     [("quarterly offsites", "event"), ("Lake Geneva", "place"), ("remote summit", "event")],
     [("quarterly offsites", "remote summit", "PREFERS")],
     "which in-person work gathering do I defend against the video alternative",
     "quarterly gathering lake location hallway track video call alternative"),
    # --- 34. noise ---
    ("Give me a sec, checking the W-2.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Coaching conversation with Annika on 2026-03-27 surfaced that I have been avoiding hard people conversations since the Colin standoff.", "reference", "personal", False,
     [("Annika", "person"), ("2026-03-27", "date"), ("Colin", "person")],
     [],
     "which coaching session revealed my avoidance pattern and which earlier conflict did it trace back to",
     "executive coach date avoidance discovery manager standoff origin conflict"),
    # --- 36 ---
    ("Reports now number eight after the reorg on 2026-03-15; six engineers plus two designers, all of whom I inherited from Sonia.", "fact", "personal", False,
     [("Reports", "concept"), ("reorg", "event"), ("2026-03-15", "date"), ("Sonia", "person")],
     [],
     "how big is the team after the restructure and who were they inherited from",
     "team size reorg date eight reports engineer designer split inheritance manager"),
    # --- 37 ---
    ("Prefers blocking Friday afternoons for thinking time over any mandatory planning ritual; the best ideas of 2025 all came from those walks.", "preference", "personal", False,
     [("Friday afternoons", "date"), ("mandatory planning ritual", "event"), ("walks", "activity"), ("2025", "date")],
     [("Friday afternoons", "mandatory planning ritual", "PREFERS")],
     "which weekly block do I guard against the planning meetings and what did it produce last year",
     "Friday slot protection walking thinking time planning ritual alternative year output"),
    # --- 38 ---
    ("Decided the Barcelona role offer from Franco was the wrong shape; exciting company but the relocation blew up the parental leave timing.", "decision", "personal", False,
     [("Barcelona", "place"), ("Franco", "person"), ("relocation", "event"), ("parental leave", "event")],
     [],
     "which European offer did I pass on and what was the family-timing conflict",
     "Iberian offer decline relocation leave clash family timing decision"),
    # --- 39 ---
    ("My 360 results from 2025-12-10 told me what I already suspected: I am seen as strategic but slow to make the hard call.", "reference", "personal", False,
     [("360", "concept"), ("2025-12-10", "date")],
     [],
     "when did the multi-source feedback arrive and what was the consistent weakness flagged",
     "360 assessment December date strategic tag decisiveness gap consistent theme"),
    # --- 40 ---
    ("Blocked the first 30 minutes of every day for solo work starting 2026-01-06; no standups and no Slack before 09:00 local.", "architecture", "personal", False,
     [("solo work", "activity"), ("2026-01-06", "date"), ("standups", "event"), ("Slack", "service"), ("09:00", "date")],
     [("solo work", "standups", "PREFERS")],
     "what morning-protection rule did I adopt in early January and what gets deferred",
     "morning quiet block January start solo time rule meeting chat defer hour"),
    # --- 41 ---
    ("Agreed to speak at the ORD chapter panel on 2026-09-18 on managing remote-first engineering orgs; first external panel as a principal.", "milestone", "personal", False,
     [("ORD", "organization"), ("2026-09-18", "date"), ("principal", "goal")],
     [],
     "when is the industry panel talk and what is the angle at principal level",
     "Chicago chapter panel September date remote-first management principal debut"),
    # --- 42 ---
    ("Considered going independent as a fractional CTO in early 2026 but the health insurance math did not work with two kids under four.", "decision", "personal", False,
     [("fractional CTO", "goal"), ("2026", "date"), ("health insurance", "concept"), ("kids", "person")],
     [],
     "which solo consulting path did I rule out and what was the blocker",
     "independent fractional executive path family coverage calculation young children"),
    # --- 43 ---
    ("The mentorship Donna gave me in 2014 is still how I pattern my own 1:1s with reports today; it is the single biggest compounding gift.", "reference", "personal", False,
     [("Donna", "person"), ("2014", "date"), ("1:1s", "event"), ("reports", "person")],
     [("1:1s", "Donna", "BUILDS_ON")],
     "whose early-career coaching still shapes how I run weekly check-ins",
     "early mentor year one-on-one template compound gift influence career"),
    # --- 44 ---
    ("Performance improvement plan I had to put Rahim on ended on 2025-11-04 with him exiting the company; worst three months of my management year.", "problem", "personal", False,
     [("Rahim", "person"), ("2025-11-04", "date")],
     [],
     "when did the PIP I managed close out and what was the emotional cost",
     "underperformance plan closure autumn date departure emotional toll management year"),
    # --- 45 ---
    ("Attended the Kellogg EMBA alumni summit in Evanston on 2026-05-21; the panel with Serena on second-half careers reframed the next decade for me.", "milestone", "personal", False,
     [("Kellogg", "organization"), ("EMBA", "concept"), ("Evanston", "place"), ("2026-05-21", "date"), ("Serena", "person")],
     [("Kellogg", "Evanston", "LOCATED_IN")],
     "which alumni event in the northern suburb reshaped my ten-year thinking and who spoke",
     "business school alumni summit spring date suburb panel second-half careers speaker"),
    # --- 46 ---
    ("Took a second opinion on the Torrent equity package from Sunita on 2026-01-18 before signing; she caught the cliff clause I had glossed over.", "decision", "personal", False,
     [("Torrent", "organization"), ("Sunita", "person"), ("2026-01-18", "date"), ("cliff clause", "concept")],
     [],
     "which advisor reviewed the startup equity before I signed and what did she flag",
     "equity review January date independent advisor cliff provision catch startup"),
    # --- 47 ---
    ("The imposter feeling at the principal promotion did not fade until about week 11; logging small wins daily was what got me out of it.", "problem", "personal", False,
     [("imposter feeling", "emotion"), ("principal", "goal")],
     [],
     "how long did the post-promotion imposter stretch last and what finally broke it",
     "impostor feeling duration promotion eleven weeks daily small win log breakthrough"),
    # --- 48 ---
    ("Started the retirement glidepath spreadsheet in 2025 with a target of fully out by 58; the 529 plans for both kids are on a parallel track.", "architecture", "personal", False,
     [("retirement glidepath", "concept"), ("2025", "date"), ("58", "date"), ("529 plans", "concept"), ("kids", "person")],
     [],
     "when did the retirement spreadsheet start and what target age plus parallel tracks are in it",
     "retirement planning spreadsheet year fifty-eight target education account parallel kids"),
    # --- 49 ---
    ("Professional identity used to be stapled to the VP title at Lumeris; after the sale closed I realized how hollow that staple was.", "reference", "personal", False,
     [("VP", "goal"), ("Lumeris", "organization")],
     [],
     "which old title did my sense of self hang on and what revealed the shallowness",
     "VP title identity anchor previous employer acquisition close revealed hollow"),
    # --- 50 ---
    ("Prefers annual compensation conversations tied to market data over the ritual of yearly three-percent raises; pulled the last market cut from Levels.fyi on 2026-02-05.", "preference", "personal", False,
     [("market data", "concept"), ("yearly three-percent raises", "concept"), ("Levels.fyi", "service"), ("2026-02-05", "date")],
     [("market data", "yearly three-percent raises", "PREFERS")],
     "which pay-conversation style do I push for and where did the latest benchmarks come from",
     "market benchmark conversation annual ritual raise alternative comp site pull date"),
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
    with OUT.open("a", encoding="utf-8") as f:
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
