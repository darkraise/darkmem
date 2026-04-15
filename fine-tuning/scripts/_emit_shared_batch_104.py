"""One-off emitter for shared-base batch-104 — personal domain (dating and romantic relationships slice).

Writes 50 rows to data/v2/shared/batch_104.tmp.jsonl with ids shared-05151..05200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_104.tmp.jsonl"
ID_OFFSET = 5150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Met Clara at a rooftop pub quiz in Shoreditch on 2025-09-14; her team was two answers ahead of ours and she handed us a napkin with her number.", "milestone", "personal", False,
     [("Clara", "person"), ("pub quiz", "event"), ("Shoreditch", "place"), ("2025-09-14", "date")],
     [("pub quiz", "Shoreditch", "LOCATED_IN")],
     "when and where did I first meet my partner and how did the number exchange happen",
     "met partner rooftop pub quiz shoreditch team number napkin date"),
    # --- 2 ---
    ("First proper date with Clara was a walk along the Regent's Canal on 2025-09-21 followed by ramen at Kanada-Ya; we ended up talking past closing time.", "milestone", "personal", False,
     [("Clara", "person"), ("Regent's Canal", "place"), ("2025-09-21", "date"), ("Kanada-Ya", "organization"), ("ramen", "food")],
     [("ramen", "Kanada-Ya", "LOCATED_IN")],
     "what was the first real date with my partner and what did we do",
     "first date canal walk ramen restaurant closing conversation date"),
    # --- 3 ---
    ("Clara said she loved me for the first time on 2025-12-03 after the Christmas market in Cologne; I already knew by the third date but waited to match her.", "milestone", "personal", False,
     [("Clara", "person"), ("2025-12-03", "date"), ("Christmas market", "event"), ("Cologne", "place")],
     [("Christmas market", "Cologne", "LOCATED_IN")],
     "when was the first I-love-you said in the relationship and what was the setting",
     "first I love you christmas market cologne partner waited match date"),
    # --- 4 ---
    ("Prefers Clara's habit of hashing out arguments the same night over my instinct to sleep on it; we agreed to her model after a bad three-day silence.", "preference", "personal", False,
     [("Clara", "person"), ("arguments", "concept"), ("three-day silence", "event")],
     [("arguments", "three-day silence", "CAUSES")],
     "which conflict-handling rhythm did we settle on as a couple and why",
     "argument same night resolve over sleep on it silence triggered change"),
    # --- 5 ---
    ("Introduced Clara to my parents over Sunday roast at their place on 2025-11-16; my dad asked about her thesis, my mum asked about grandchildren.", "milestone", "personal", False,
     [("Clara", "person"), ("Sunday roast", "food"), ("2025-11-16", "date"), ("dad", "person"), ("mum", "person"), ("thesis", "concept")],
     [],
     "when did the partner-meets-parents lunch happen and how did it go",
     "partner meets parents sunday roast thesis grandchildren question date"),
    # --- 6 ---
    ("Replaced the weekly date-night takeaway with a home-cook rota on 2026-01-10; Clara does Tuesday and Thursday, I do Monday and Wednesday, Friday is shared.", "decision", "personal", False,
     [("date-night", "event"), ("takeaway", "food"), ("home-cook rota", "method"), ("2026-01-10", "date"), ("Clara", "person")],
     [("home-cook rota", "takeaway", "REPLACES")],
     "which couple's dinner pattern took over from ordering in and how is it split",
     "date night takeaway swap home cook rota split weekday shared friday"),
    # --- 7 ---
    ("Clara and I moved in together on 2026-02-14 at the flat in Peckham; the lease is joint, the rent is split 55/45 to match our salaries.", "milestone", "personal", False,
     [("Clara", "person"), ("2026-02-14", "date"), ("flat", "place"), ("Peckham", "place"), ("lease", "concept")],
     [("flat", "Peckham", "LOCATED_IN")],
     "when did we move in together and how is the rent actually split",
     "moved in together peckham flat joint lease rent split ratio date"),
    # --- 8 ---
    ("The long-distance stretch with Clara ran from 2025-10-05 to 2025-12-20 while she finished the Edinburgh fellowship; we did one video call a night and alternating weekend flights.", "architecture", "personal", False,
     [("Clara", "person"), ("2025-10-05", "date"), ("2025-12-20", "date"), ("Edinburgh", "place"), ("video call", "activity")],
     [("Clara", "Edinburgh", "LOCATED_IN")],
     "how did we run the long-distance phase and what was the cadence",
     "long distance phase edinburgh fellowship nightly video weekend flight"),
    # --- 9 ---
    ("Prefers the Sunday morning slow coffee with Clara over the Saturday brunch out; the flat is quieter, nobody is rushing us, and the toast is better.", "preference", "personal", False,
     [("Clara", "person"), ("Sunday", "date"), ("Saturday", "date"), ("brunch", "food"), ("toast", "food")],
     [("Sunday", "Saturday", "PREFERS")],
     "which couple's weekend food ritual wins out and why",
     "sunday slow coffee over saturday brunch quieter flat toast reason"),
    # --- 10. noise ---
    ("Give me a sec, I need to find where I put my phone.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Proposed to Clara on 2026-03-30 on the Pembrokeshire coast path near St Davids; used my grandmother's ring and she said yes before I finished the sentence.", "milestone", "personal", False,
     [("Clara", "person"), ("2026-03-30", "date"), ("Pembrokeshire", "place"), ("St Davids", "place"), ("grandmother's ring", "tool")],
     [("St Davids", "Pembrokeshire", "LOCATED_IN")],
     "when and where did the engagement happen and what ring was used",
     "engagement proposal coast path st davids heirloom ring yes date"),
    # --- 12 ---
    ("The wedding planning split is mine for logistics and budget, Clara's for guest list and vibe; we agreed this after a tense Saturday spreadsheet session.", "decision", "personal", False,
     [("wedding planning", "activity"), ("Clara", "person"), ("Saturday", "date"), ("spreadsheet", "tool")],
     [],
     "how did we divide the wedding-planning workload as a couple",
     "wedding planning split logistics budget guest list vibe agreement"),
    # --- 13 ---
    ("Switched couples counselling providers from Relate to a private therapist called Dr Anjali on 2026-01-18 after the NHS waitlist hit fourteen weeks.", "decision", "personal", False,
     [("couples counselling", "activity"), ("Relate", "organization"), ("Dr Anjali", "person"), ("2026-01-18", "date"), ("NHS", "organization")],
     [("Dr Anjali", "Relate", "REPLACES")],
     "which couples therapy route took over and what forced the switch",
     "couples counselling relate to private therapist nhs waitlist swap date"),
    # --- 14 ---
    ("The big fight about children on 2025-11-28 surfaced that Clara wants two by 34 and I was thinking maybe one and later; we're both circling the timing more than the count.", "problem", "personal", False,
     [("Clara", "person"), ("2025-11-28", "date"), ("children", "concept"), ("timing", "concept")],
     [("timing", "children", "RELATED_TO")],
     "when did the kids-timing disagreement surface and where does each of us actually stand",
     "fight children number timing partner want two by age single later"),
    # --- 15 ---
    ("Prefers Clara's climbing gym over our old mixed-couples bouldering night; we belay each other now instead of queueing for different routes.", "preference", "personal", False,
     [("Clara", "person"), ("climbing gym", "place"), ("bouldering night", "event"), ("belay", "activity")],
     [("climbing gym", "bouldering night", "PREFERS")],
     "which shared climbing setup wins for us and why",
     "climbing gym over bouldering night belay pair route queue"),
    # --- 16 ---
    ("The break with Marcus in 2023-07-11 ended a four-year relationship; the trigger was him taking the Berlin job without a conversation, but the rot was older.", "milestone", "personal", False,
     [("Marcus", "person"), ("2023-07-11", "date"), ("Berlin", "place"), ("four-year relationship", "concept")],
     [("Marcus", "Berlin", "LOCATED_IN")],
     "when did the previous long relationship end and what was the trigger",
     "break up ex four year berlin job no conversation older reasons date"),
    # --- 17 ---
    ("Post-break-up routine in 2023-08 was Wednesday boxing, Saturday long walk, Sunday phone call with my sister; held to it for six months.", "architecture", "personal", False,
     [("2023-08", "date"), ("boxing", "hobby"), ("long walk", "activity"), ("sister", "person")],
     [],
     "what did the post-break-up weekly rhythm look like",
     "post break up routine boxing walk sister phone weekly six months"),
    # --- 18 ---
    ("Rekindled briefly with Marcus in 2024-04 when he visited London; two dinners in and we both saw the same wall coming up, called it cleanly.", "milestone", "personal", False,
     [("Marcus", "person"), ("2024-04", "date"), ("London", "place"), ("dinners", "event")],
     [("Marcus", "London", "VISITED")],
     "what happened with the ex revisit last year and how did it end",
     "rekindle ex london dinners wall called it clean second end"),
    # --- 19 ---
    ("Hinge was how Clara and I matched on 2025-09-01; deleted both our profiles the morning after the canal-walk date as an unspoken decision.", "fact", "personal", False,
     [("Hinge", "platform"), ("Clara", "person"), ("2025-09-01", "date"), ("canal-walk", "activity")],
     [],
     "which dating app matched us and when did we delete the profiles",
     "dating app match partner delete both profile morning after date"),
    # --- 20 ---
    ("Chose a city-hall wedding with 18 guests over the big family do Clara's mother wanted; the compromise was a separate family lunch two weeks before.", "decision", "personal", False,
     [("city-hall wedding", "event"), ("Clara", "person"), ("mother", "person"), ("family lunch", "event")],
     [("city-hall wedding", "family lunch", "RELATED_TO")],
     "what wedding format did we settle on and how did we handle the family expectation",
     "city hall small wedding over big family compromise separate lunch"),
    # --- 21 ---
    ("The couples counselling focus with Dr Anjali is shifting from conflict scripts to repair attempts; we are now expected to name the bid during the argument.", "architecture", "personal", False,
     [("couples counselling", "activity"), ("Dr Anjali", "person"), ("conflict scripts", "method"), ("repair attempts", "method"), ("bid", "concept")],
     [("repair attempts", "conflict scripts", "REPLACES")],
     "how is the therapy work structured now and what is the current exercise",
     "couples counselling repair attempts over conflict scripts name bid"),
    # --- 22 ---
    ("Prefers our shared Monzo joint pot for groceries to the old Venmo-me-later pattern; nobody has to hold a mental ledger after Tesco anymore.", "preference", "personal", False,
     [("Monzo", "organization"), ("joint pot", "tool"), ("Venmo", "platform"), ("Tesco", "organization"), ("ledger", "concept")],
     [("joint pot", "Venmo", "PREFERS")],
     "which couple's shopping-money setup wins over the other and why",
     "monzo joint pot over venmo grocery mental ledger tesco"),
    # --- 23 ---
    ("The first Valentine's as a couple on 2026-02-14 was spent unpacking boxes at the Peckham flat and eating pizza on the floor; neither of us minded.", "milestone", "personal", False,
     [("Valentine's", "event"), ("2026-02-14", "date"), ("Peckham", "place"), ("pizza", "food")],
     [],
     "how did we spend our first couple's valentines and where",
     "first valentines couple unpack peckham pizza floor low key date"),
    # --- 24 ---
    ("The long-term goals map Clara and I drew on 2026-03-15 lists kids by 36, one sabbatical each before 40, and keeping two home-country trips a year.", "reference", "personal", False,
     [("Clara", "person"), ("2026-03-15", "date"), ("kids", "concept"), ("sabbatical", "event"), ("home-country trips", "activity")],
     [],
     "what does the couple's long-term plan actually commit to",
     "goals map kids by age sabbatical before forty home country trips"),
    # --- 25 ---
    ("Prefers Clara's morning-person habit over my night-owl default on weekdays; shifted my wake-up to 06:45 after we kept missing shared breakfast.", "preference", "personal", False,
     [("Clara", "person"), ("morning-person", "concept"), ("night-owl", "concept"), ("breakfast", "food")],
     [("morning-person", "night-owl", "PREFERS")],
     "which daily rhythm won out between us and what did I change",
     "morning person over night owl partner wake time breakfast shift"),
    # --- 26 ---
    ("Clara's mother Ileana and I now have a standing Sunday phone call at 17:00; it started as damage control after the Christmas argument and turned real.", "fact", "personal", False,
     [("Clara", "person"), ("Ileana", "person"), ("Sunday", "date"), ("Christmas argument", "event")],
     [("Ileana", "Christmas argument", "RELATED_TO")],
     "how does the in-law relationship sit now and how did that start",
     "mother in law sunday call standing christmas argument damage control"),
    # --- 27 ---
    ("The engagement ring resizing at Beaverbrooks on 2026-04-02 dropped Clara's ring from size M to size K; insurance was re-noted the same afternoon.", "fact", "personal", False,
     [("Beaverbrooks", "organization"), ("2026-04-02", "date"), ("Clara", "person"), ("insurance", "concept")],
     [],
     "when did the ring resize happen and was the insurance sorted",
     "engagement ring resize jeweller size drop insurance update date"),
    # --- 28 ---
    ("Chose the Northcote Road flat over the Herne Hill one after two viewing weekends; Clara's commute won over my slight ceiling-height preference.", "decision", "personal", False,
     [("Northcote Road", "place"), ("Herne Hill", "place"), ("Clara", "person"), ("commute", "concept")],
     [("Northcote Road", "Herne Hill", "PREFERS")],
     "which of the two flats did we pick and what tipped it",
     "flat pick northcote over herne hill commute over ceiling height"),
    # --- 29 ---
    ("Replaced the Friday date-night-out rule with an alternating in-out rhythm on 2026-03-01; the out weeks feel special again instead of obligatory.", "decision", "personal", False,
     [("Friday", "date"), ("date-night", "event"), ("in-out rhythm", "method"), ("2026-03-01", "date")],
     [("in-out rhythm", "date-night", "REPLACES")],
     "which date-night pattern took over and what changed about the feel",
     "friday routine revision cadence swap early 2026 felt stale"),
    # --- 30 ---
    ("The six-month anniversary fell on 2026-03-14 and we spent it at the Prince Charles Cinema watching the Before Sunrise double bill; Clara cried at the ending again.", "milestone", "personal", False,
     [("2026-03-14", "date"), ("Prince Charles Cinema", "place"), ("Before Sunrise", "publication"), ("Clara", "person")],
     [("Before Sunrise", "Prince Charles Cinema", "LOCATED_IN")],
     "how did we mark the six-month milestone and where",
     "six month anniversary cinema double bill cried ending date"),
    # --- 31 ---
    ("The couple's weekly check-in runs Sunday 20:00 over tea; three prompts — what went well, what chafed, what we want next week — and a 30-minute cap.", "architecture", "personal", False,
     [("check-in", "event"), ("Sunday", "date"), ("tea", "food"), ("prompts", "concept")],
     [],
     "how is our weekly couple's check-in structured",
     "weekly check in sunday evening three prompts thirty minute cap"),
    # --- 32 ---
    ("Prefers Clara's instinct to tell me a worry at the start of the week over letting it pile into the weekend; Monday dinners are where most real talks land.", "preference", "personal", False,
     [("Clara", "person"), ("Monday", "date"), ("weekend", "date"), ("dinner", "food"), ("worry", "emotion")],
     [("Monday", "weekend", "PREFERS")],
     "which timing pattern for raising worries won out between us",
     "raise worry monday early over weekend pile up real talk dinner"),
    # --- 33 ---
    ("The couple's shared hobby is bouldering at Arch Climbing Bermondsey on Tuesday and Saturday; we keep a shared grade log and neither of us pushes the other.", "fact", "personal", False,
     [("bouldering", "hobby"), ("Arch Climbing Bermondsey", "organization"), ("Tuesday", "date"), ("Saturday", "date"), ("grade log", "tool")],
     [("bouldering", "Arch Climbing Bermondsey", "LOCATED_IN")],
     "what is our main shared hobby and how do we run it together",
     "couple hobby bouldering gym weekly twice shared grade log no pressure"),
    # --- 34. noise ---
    ("Actually scratch that, I was thinking of a different week.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The disagreement over Clara's Lisbon job offer on 2026-02-20 was the hardest two-week stretch; we landed on her turning it down and me finding remote Fridays instead.", "problem", "personal", False,
     [("Clara", "person"), ("Lisbon", "place"), ("job offer", "event"), ("2026-02-20", "date"), ("remote Fridays", "concept")],
     [("remote Fridays", "Lisbon", "REPLACES")],
     "how did we navigate the partner's overseas job offer and what was the outcome",
     "lisbon job offer partner turn down remote friday compromise date"),
    # --- 36 ---
    ("The engagement party at Clara's uncle's house on 2026-05-02 is capped at 40; mixed sides, one speech each, nobody on the mic more than three minutes.", "reference", "personal", False,
     [("engagement party", "event"), ("Clara", "person"), ("uncle", "person"), ("2026-05-02", "date"), ("speech", "activity")],
     [],
     "how is the engagement party structured and what are the guardrails",
     "engagement party venue cap mixed sides speech limit date"),
    # --- 37 ---
    ("Prefers Clara's family group chat over my family one for day-to-day updates; hers runs on photos, mine runs on forwarded news articles and tension.", "preference", "personal", False,
     [("Clara", "person"), ("group chat", "tool"), ("photos", "concept"), ("news articles", "concept")],
     [("Clara", "group chat", "USES")],
     "which of the two family chats is actually pleasant and why",
     "family group chat partner photos over mine news forward tension"),
    # --- 38 ---
    ("The couple's holiday calendar for 2026 has one big trip — two weeks in Japan in October — and four UK weekend breaks evenly spaced around it.", "reference", "personal", False,
     [("holiday calendar", "tool"), ("2026", "date"), ("Japan", "place"), ("October", "date"), ("UK", "place")],
     [],
     "how is our couple's travel calendar shaped for this year",
     "holiday calendar big trip japan autumn four uk weekend breaks spacing"),
    # --- 39 ---
    ("Clara prefers I tell her plans as they form, not once finalised; I kept defaulting to surprise-reveal and it was landing as exclusion.", "preference", "personal", False,
     [("Clara", "person"), ("surprise-reveal", "method"), ("exclusion", "emotion")],
     [("surprise-reveal", "exclusion", "CAUSES")],
     "which information-sharing style does my partner want from me and why",
     "share plan early over surprise reveal partner exclusion feeling"),
    # --- 40 ---
    ("Replaced the joint Google Calendar with a shared Cron calendar on 2026-02-28; colour-coded per person and the commute layer stopped us double-booking.", "decision", "personal", False,
     [("Google Calendar", "tool"), ("Cron", "tool"), ("2026-02-28", "date"), ("commute layer", "concept")],
     [("Cron", "Google Calendar", "REPLACES")],
     "which shared couple's calendar took over and what did it fix",
     "shared calendar swap google to cron commute layer double booking fix"),
    # --- 41 ---
    ("The wedding venue shortlist as of 2026-04-08 is Fulham Palace, Asylum Chapel, and Clapton Country Club; final pick hinges on Clara's grandmother being able to get in.", "decision", "personal", False,
     [("Fulham Palace", "place"), ("Asylum Chapel", "place"), ("Clapton Country Club", "place"), ("2026-04-08", "date"), ("grandmother", "person"), ("Clara", "person")],
     [],
     "what are the three wedding venues in play and what decides between them",
     "wedding venue shortlist accessibility grandmother decider date"),
    # --- 42 ---
    ("Prefers Clara's habit of bringing back a small thing from every solo trip over us setting a fixed gift budget; the thought lands harder than the price tag.", "preference", "personal", False,
     [("Clara", "person"), ("solo trip", "event"), ("gift budget", "concept"), ("thought", "concept")],
     [("Clara", "gift budget", "PREFERS")],
     "which couple's gift-giving custom won out and why",
     "small gift from trip over fixed budget thought over price partner"),
    # --- 43 ---
    ("The shared pet decision on 2026-03-22 landed on fostering a senior dog from Battersea rather than adopting a puppy; Clara and I can both cover the walks.", "decision", "personal", False,
     [("Battersea", "organization"), ("2026-03-22", "date"), ("senior dog", "concept"), ("puppy", "concept"), ("Clara", "person"), ("walks", "activity")],
     [("senior dog", "puppy", "PREFERS")],
     "what pet decision did we make as a couple and what tipped it",
     "shared pet foster senior over puppy walk coverage battersea date"),
    # --- 44 ---
    ("The ten-year mark with my first marriage to Hazel landed on 2021-06-04; we split amicably seven months later when neither of us could name what we still wanted together.", "milestone", "personal", False,
     [("Hazel", "person"), ("2021-06-04", "date"), ("first marriage", "concept"), ("split", "event")],
     [],
     "what was the ten-year marker in the previous marriage and how did it close",
     "first marriage ten year mark ex amicable split wants unclear date"),
    # --- 45 ---
    ("Prefers introducing Clara as my partner over fiancée in work settings; the ring invites questions I do not want from hiring panels.", "preference", "personal", False,
     [("Clara", "person"), ("partner", "concept"), ("fiancée", "concept"), ("hiring panels", "event")],
     [("partner", "fiancée", "PREFERS")],
     "which label do I use for my partner at work and why",
     "partner over fiancee label work hiring panel question avoidance"),
    # --- 46 ---
    ("The second-honeymoon plan with Hazel to Kyoto in 2019 never happened; we cancelled six weeks out, which I now see as the first real break in that marriage.", "milestone", "personal", False,
     [("Hazel", "person"), ("second-honeymoon", "event"), ("Kyoto", "place"), ("2019", "date"), ("marriage", "concept")],
     [],
     "what was the cancelled second-honeymoon and what does it mean in hindsight",
     "second honeymoon kyoto cancel first break marriage prior partner year"),
    # --- 47 ---
    ("Chose to share the mental-load list with Clara in a shared Notion page on 2026-03-08; invisible tasks like GP reminders and birthday shopping now have an owner.", "decision", "personal", False,
     [("Clara", "person"), ("mental-load list", "tool"), ("Notion", "platform"), ("2026-03-08", "date"), ("GP reminders", "activity"), ("birthday shopping", "activity")],
     [("mental-load list", "Notion", "DEPLOYED_ON")],
     "how did we formalise the invisible-work sharing and where does it live",
     "mental load shared notion page owner invisible tasks gp birthday date"),
    # --- 48 ---
    ("Prefers the long Sunday walk around Brockwell Park with Clara and no phones over the brunch-and-podcast routine we used to do; we actually talk about the week.", "preference", "personal", False,
     [("Brockwell Park", "place"), ("Clara", "person"), ("brunch", "food"), ("podcast", "publication"), ("phones", "tool")],
     [("Brockwell Park", "brunch", "PREFERS")],
     "which Sunday couple ritual did we swap in and what does it do for us",
     "sunday walk brockwell no phones over brunch podcast week review"),
    # --- 49 ---
    ("The 2021 post-divorce therapy block with Dr Ferris ran for 22 weeks; the keeper lesson was that resentment compounds when a repair attempt gets ignored.", "reference", "personal", False,
     [("post-divorce therapy", "activity"), ("Dr Ferris", "person"), ("2021", "date"), ("resentment", "emotion"), ("repair attempt", "concept")],
     [("repair attempt", "resentment", "CAUSES")],
     "what did the post-divorce therapy actually teach that I still carry",
     "post divorce therapy weeks resentment compound ignored repair attempt"),
    # --- 50 ---
    ("Clara and I do a yearly relationship audit every 2026-09-14 anniversary: three things that worked, two that did not, one thing to try — all written before we compare notes.", "architecture", "personal", False,
     [("Clara", "person"), ("2026-09-14", "date"), ("relationship audit", "method"), ("anniversary", "event")],
     [("relationship audit", "anniversary", "HAPPENED_ON")],
     "how do we run the yearly couple's review and when",
     "yearly couple review structure solo note drafting before joint discussion"),
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
