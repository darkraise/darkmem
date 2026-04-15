"""One-off emitter for shared-base batch-133 — personal domain (digital wellness / screen-time management / attention-reset slice).

Writes 50 rows to data/v2/shared/batch_133.tmp.jsonl with ids shared-06601..06650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_133.tmp.jsonl"
ID_OFFSET = 6600

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Set the Apple Screen Time daily limit for Instagram to 15 minutes on 2026-03-04 after noticing a 2h 40m daily average the week before.", "decision", "personal", False,
     [("Apple Screen Time", "tool"), ("Instagram", "platform"), ("2026-03-04", "date")],
     [("Apple Screen Time", "Instagram", "RELATED_TO")],
     "when did I cap the photo-app minutes on the phone and what drove the number",
     "screen time daily limit instagram 15 minutes average baseline date"),
    # --- 2 ---
    ("Prefers the One Sec app pause over a hard Freedom block for Twitter; the one-breath delay kills the impulse without locking the account out entirely.", "preference", "personal", False,
     [("One Sec", "tool"), ("Freedom", "tool"), ("Twitter", "platform")],
     [("One Sec", "Freedom", "PREFERS")],
     "which friction tool wins for the bird app and why a soft pause beats a block",
     "one sec pause over freedom block twitter impulse breath soft"),
    # --- 3 ---
    ("The grayscale-mode experiment ran 2026-02-10 through 2026-02-24; phone pickups dropped from 86 to 54 a day by the second week.", "milestone", "personal", False,
     [("grayscale-mode", "concept"), ("2026-02-10", "date"), ("2026-02-24", "date"), ("phone", "infrastructure")],
     [],
     "when did the black-and-white screen trial run and what did pickup counts do",
     "grayscale experiment pickup count drop two week window date range"),
    # --- 4 ---
    ("Finished Cal Newport Digital Minimalism on 2026-01-18 and pulled the 30-day declutter idea into the February reset plan.", "milestone", "personal", False,
     [("Cal Newport", "person"), ("Digital Minimalism", "publication"), ("2026-01-18", "date"), ("declutter", "method"), ("February", "date")],
     [],
     "when did I finish the Newport book and which idea carried into the next month",
     "digital minimalism newport book finish declutter february plan date"),
    # --- 5 ---
    ("Chose Opal over Cold Turkey for iOS block enforcement; Cold Turkey is desktop-first and Opal handles the Screen Time API more cleanly.", "decision", "personal", False,
     [("Opal", "tool"), ("Cold Turkey", "tool"), ("iOS", "platform"), ("Screen Time API", "api")],
     [("Opal", "Cold Turkey", "PREFERS")],
     "which attention-blocker won on the phone and what tipped the choice",
     "opal over cold turkey iOS screen time API integration reason"),
    # --- 6 ---
    ("Deleted the TikTok account on 2026-03-20 after the third weekend lost to the algorithm; kept Instagram on a read-only web-only toehold.", "milestone", "personal", False,
     [("TikTok", "platform"), ("2026-03-20", "date"), ("algorithm", "concept"), ("Instagram", "platform")],
     [],
     "when did the short-video app go and what of the other networks stayed",
     "tiktok delete account weekend lost algorithm instagram read only date"),
    # --- 7 ---
    ("The phone-free evening rule kicks in at 20:00: handset goes into a drawer in the hall until 07:00 the next morning, no exceptions for work.", "architecture", "personal", False,
     [("phone-free evening", "activity"), ("drawer", "place"), ("hall", "place"), ("handset", "infrastructure")],
     [("handset", "drawer", "LOCATED_IN")],
     "how is the nightly no-phone window structured and where does the device sit",
     "phone free evening drawer hall cut off time morning no work exception"),
    # --- 8 ---
    ("The Freedom block profile called Deep Work runs 09:00 to 12:00 weekdays and covers Reddit, HackerNews, YouTube, and the personal email inbox.", "reference", "personal", False,
     [("Freedom", "tool"), ("Deep Work", "concept"), ("Reddit", "platform"), ("HackerNews", "platform"), ("YouTube", "platform")],
     [("Deep Work", "Freedom", "RELATED_TO")],
     "what does the morning focus block cover and at what hours",
     "freedom deep work profile weekday morning reddit hackernews youtube email"),
    # --- 9 ---
    ("Read Jenny Odell How to Do Nothing on 2025-12-29; the attention-as-commons argument reframed the whole concept of a phone detox.", "fact", "personal", False,
     [("Jenny Odell", "person"), ("How to Do Nothing", "publication"), ("2025-12-29", "date"), ("attention-as-commons", "theory"), ("phone detox", "activity")],
     [],
     "when did I read the Odell book and what idea from it changed my framing",
     "odell how to do nothing attention commons reframe detox date"),
    # --- 10. noise ---
    ("Let me put the phone on the other side of the room for this one.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Light Phone II trial ran 2026-01-06 through 2026-01-20; carried it as the primary handset, kept the iPhone in a drawer for weekend errands only.", "milestone", "personal", False,
     [("Light Phone II", "infrastructure"), ("2026-01-06", "date"), ("2026-01-20", "date"), ("iPhone", "infrastructure"), ("drawer", "place")],
     [("Light Phone II", "iPhone", "REPLACES")],
     "when did the dumbphone trial run and how was the smartphone handled",
     "light phone II trial two week iPhone drawer weekend only date range"),
    # --- 12 ---
    ("Prefers the Boox Palma over a second iPad for evening reading; e-ink kills the reflex to swipe into Instagram when a paragraph gets boring.", "preference", "personal", False,
     [("Boox Palma", "infrastructure"), ("iPad", "infrastructure"), ("Instagram", "platform"), ("e-ink", "technology")],
     [("Boox Palma", "iPad", "PREFERS")],
     "which evening reading device wins over the tablet and why the screen tech matters",
     "boox palma over ipad e-ink evening reading no instagram swipe"),
    # --- 13 ---
    ("The home screen on 2026-02-01 shrank to four tools: Phone, Messages, Maps, Kindle; everything else lives behind a two-tap search.", "architecture", "personal", False,
     [("home screen", "concept"), ("2026-02-01", "date"), ("Phone", "platform"), ("Messages", "platform"), ("Maps", "platform"), ("Kindle", "platform")],
     [],
     "how is the launcher pared down and which apps earned a slot",
     "home screen intentionality four app phone messages maps kindle search"),
    # --- 14 ---
    ("Switched notification setting on iOS to allowlist only: phone calls, texts from five starred contacts, calendar, and the medication reminder.", "decision", "personal", False,
     [("iOS", "platform"), ("notification", "concept"), ("allowlist", "pattern"), ("calendar", "tool"), ("medication reminder", "tool")],
     [("allowlist", "notification", "RELATED_TO")],
     "how were the phone alerts pruned and what earned a pass through",
     "notification hygiene iOS allowlist calls texts starred calendar meds"),
    # --- 15 ---
    ("The Sunday social-media fast runs 07:00 Sunday to 07:00 Monday; Freedom handles the block, Opal handles the widget greyout, One Sec is the safety net.", "architecture", "personal", False,
     [("social-media fast", "activity"), ("Sunday", "date"), ("Monday", "date"), ("Freedom", "tool"), ("Opal", "tool"), ("One Sec", "tool")],
     [("social-media fast", "Freedom", "RELATED_TO")],
     "how is the weekly network-free day layered across the three tools",
     "sunday social media fast freedom opal one sec layered block date"),
    # --- 16 ---
    ("Read Jonathan Haidt The Anxious Generation on 2026-03-02; the phone-free-school argument pushed me to apply the same rule to my own dinner table.", "milestone", "personal", False,
     [("Jonathan Haidt", "person"), ("The Anxious Generation", "publication"), ("2026-03-02", "date"), ("phone-free-school", "concept"), ("dinner table", "place")],
     [],
     "when did I finish the Haidt book and what rule did it nudge me into",
     "haidt anxious generation book phone free school dinner table rule date"),
    # --- 17 ---
    ("The Punkt MP02 ordered on 2026-03-11 is the planned travel-only handset; swap routine keeps the main device at home for weekend trips.", "decision", "personal", False,
     [("Punkt MP02", "infrastructure"), ("2026-03-11", "date")],
     [],
     "when did I buy the minimalist second device and what role does it play on trips",
     "minimalist second handset purchase date travel role smartphone stays"),
    # --- 18 ---
    ("The doom-scrolling window sits between 22:30 and 00:15 if I let it; awareness came from the Screen Time weekly report on 2026-02-16.", "fact", "personal", False,
     [("doom-scrolling", "activity"), ("Screen Time", "tool"), ("2026-02-16", "date")],
     [],
     "when did I pin down my bad-scroll hour and where did the evidence come from",
     "doom scroll late night window screen time weekly report evidence date"),
    # --- 19 ---
    ("Closed the LinkedIn account on 2026-02-12; the passive feed pull outweighed the hiring value since I was not job-hunting.", "decision", "personal", False,
     [("LinkedIn", "platform"), ("2026-02-12", "date"), ("hiring", "concept")],
     [],
     "when did I shut the professional network account and what tipped the decision",
     "linkedin account close passive pull no job hunt value reason date"),
    # --- 20 ---
    ("The evening wind-down ritual from 21:00 is: paper book, chamomile, dim lamp, no screen; replaces the old YouTube-in-bed habit from 2024.", "architecture", "personal", False,
     [("wind-down ritual", "activity"), ("paper book", "tool"), ("chamomile", "food"), ("YouTube", "platform"), ("2024", "date")],
     [("wind-down ritual", "YouTube", "REPLACES")],
     "how is the pre-sleep no-screen routine built and what did it replace",
     "wind down paper book chamomile lamp no screen over youtube bed 2024"),
    # --- 21 ---
    ("The Mudita Pure wishlist entry sits as a backup dumbphone option behind the Light Phone II; battery life is the tie-breaker I have not tested yet.", "reference", "personal", False,
     [("Mudita Pure", "infrastructure"), ("Light Phone II", "infrastructure"), ("battery life", "concept")],
     [("Light Phone II", "Mudita Pure", "PREFERS")],
     "which minimalist phone is the fallback choice and what would settle it",
     "mudita pure light phone II backup battery life untested tiebreaker"),
    # --- 22 ---
    ("The 2026-02-13 to 2026-02-27 personal detox retreat at Cae Mabon stripped all screens for 14 days; came back with a working home-screen template.", "milestone", "personal", False,
     [("2026-02-13", "date"), ("2026-02-27", "date"), ("Cae Mabon", "place"), ("home-screen template", "pattern")],
     [],
     "when was the screen-free retreat and what practical artefact came back with me",
     "personal detox retreat cae mabon two week no screen home template date"),
    # --- 23 ---
    ("Prefers the Screen Time Downtime feature to Focus modes for the 22:00 cutover; Downtime survives a reboot, Focus sometimes does not.", "preference", "personal", False,
     [("Screen Time", "tool"), ("Downtime", "tool"), ("Focus", "tool")],
     [("Downtime", "Focus", "PREFERS")],
     "which bedtime-lock feature wins on iOS and why the reliability gap matters",
     "screen time downtime over focus reboot survive 22 cutover reliability"),
    # --- 24 ---
    ("The attention-reset protocol from the February retreat: 20 minutes of silent sit, walk the lane, then open the laptop; replaces the phone-first morning.", "architecture", "personal", False,
     [("attention-reset", "method"), ("February", "date"), ("silent sit", "activity"), ("laptop", "infrastructure"), ("phone-first morning", "pattern")],
     [("attention-reset", "phone-first morning", "REPLACES")],
     "what is the morning re-sequence and which old habit did it push out",
     "attention reset silent sit walk laptop over phone first morning protocol"),
    # --- 25 ---
    ("The Freedom weekly schedule was moved on 2026-03-09 from 08:00 starts to 07:15 starts; the new buffer made the Deep Work block actually hold.", "decision", "personal", False,
     [("Freedom", "tool"), ("2026-03-09", "date"), ("Deep Work", "concept")],
     [],
     "when did I push the morning block earlier and what did it fix",
     "freedom schedule shift earlier start deep work buffer hold date"),
    # --- 26 ---
    ("The home-screen wallpaper is a plain charcoal gradient, no widgets, no badge counts; chose it to make opening the phone feel deliberate not magnetic.", "decision", "personal", False,
     [("home-screen", "concept"), ("charcoal gradient", "concept"), ("widgets", "concept"), ("badge counts", "concept")],
     [],
     "how is the launcher visually tuned down and what is the intent behind the choice",
     "plain wallpaper no widget no badge count deliberate feel intent reason"),
    # --- 27 ---
    ("The parent-side screen-time rules I imposed on the kids also apply to me at home: no phone at meals, no phone in bedrooms, charger lives in the hall.", "decision", "personal", False,
     [("screen-time", "concept"), ("meals", "event"), ("bedrooms", "place"), ("charger", "tool"), ("hall", "place")],
     [("charger", "hall", "LOCATED_IN")],
     "which kid-side rules did I apply to myself and where do devices charge",
     "parent rules self apply no phone meals bedrooms charger hall"),
    # --- 28 ---
    ("The doom-scrolling log from 2026-01 to 2026-03 shows Reddit as the biggest sink at 41% of idle time; Freedom now has a Reddit-only fast weekday profile.", "fact", "personal", False,
     [("doom-scrolling", "activity"), ("2026-01", "date"), ("2026-03", "date"), ("Reddit", "platform"), ("Freedom", "tool")],
     [],
     "which platform dominated my idle scroll and what block followed the data",
     "doom scroll log reddit 41 percent freedom weekday profile data date"),
    # --- 29 ---
    ("Replaced the bedside iPhone with a Loftie alarm clock on 2026-01-25; removes the reach-for-the-phone reflex that always ate the first 20 minutes.", "decision", "personal", False,
     [("iPhone", "infrastructure"), ("Loftie", "infrastructure"), ("2026-01-25", "date"), ("bedside", "place")],
     [("Loftie", "iPhone", "REPLACES")],
     "when did the standalone alarm take over from the phone bedside and why",
     "loftie alarm over iphone bedside reach reflex morning reclaim date"),
    # --- 30 ---
    ("The social-media fast on 2026-03-15 through 2026-03-21 covered Reddit, Instagram, HackerNews and the Mastodon client Ivory; kept Signal open for family.", "architecture", "personal", False,
     [("2026-03-15", "date"), ("2026-03-21", "date"), ("Reddit", "platform"), ("Instagram", "platform"), ("HackerNews", "platform"), ("Ivory", "tool"), ("Signal", "platform")],
     [],
     "when was the March network-fast and which apps were excluded from the block",
     "march fast reddit instagram hackernews ivory mastodon signal kept date"),
    # --- 31 ---
    ("Prefers the physical Screen Time pin in the wallet over memorising it; a friend set it, and the extra step to fetch the wallet is the whole point.", "preference", "personal", False,
     [("Screen Time", "tool"), ("pin", "concept"), ("wallet", "place"), ("friend", "person")],
     [("pin", "wallet", "LOCATED_IN")],
     "which screen-time pin arrangement wins and why the friction is the feature",
     "screen time pin wallet friend set friction over memorise feature"),
    # --- 32 ---
    ("Kept the Kindle Paperwhite outside the Freedom block list on purpose; reading longform is the replacement I want the blocked time to flow into.", "decision", "personal", False,
     [("Kindle Paperwhite", "infrastructure"), ("Freedom", "tool"), ("longform", "concept")],
     [],
     "which reading device is exempt from the focus block and what is the logic",
     "kindle paperwhite freedom exempt longform replacement target reason"),
    # --- 33 ---
    ("The Digital Wellbeing bedtime mode on the Pixel 8 trial phone worked better than iOS Downtime at enforcing grayscale; iOS kept dropping the setting.", "fact", "personal", False,
     [("Digital Wellbeing", "tool"), ("Pixel 8", "infrastructure"), ("iOS", "platform"), ("Downtime", "tool"), ("grayscale", "concept")],
     [("Digital Wellbeing", "Downtime", "PREFERS")],
     "which platform held grayscale better at night and what was the failure mode",
     "digital wellbeing pixel 8 grayscale over iOS downtime drop reliability"),
    # --- 34. noise ---
    ("I will put this down in a second, promise.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The week-by-week Screen Time report sits in the Sunday journal entry; average, top app, pickups, longest session — four numbers, nothing more.", "architecture", "personal", False,
     [("Screen Time", "tool"), ("Sunday", "date"), ("journal", "tool"), ("pickups", "concept")],
     [],
     "how is the weekly phone-use tracking folded into the journal and what fields",
     "screen time weekly journal sunday four numbers pickup longest entry"),
    # --- 36 ---
    ("The Cal Newport 30-day declutter ran 2026-02-01 through 2026-03-02; survived the cull: Signal, Kindle, Maps, Phone, Messages, Authenticator.", "milestone", "personal", False,
     [("Cal Newport", "person"), ("declutter", "method"), ("2026-02-01", "date"), ("2026-03-02", "date"), ("Signal", "platform"), ("Kindle", "platform"), ("Maps", "platform"), ("Authenticator", "tool")],
     [],
     "when did the thirty-day app declutter run and which tools earned a reinstall",
     "newport declutter 30 day survivors signal kindle maps messages auth date"),
    # --- 37 ---
    ("The Opal session goal for 2026-Q2 is 90 minutes daily social-media screen time, down from the 2026-Q1 measured baseline of 146 minutes.", "reference", "personal", False,
     [("Opal", "tool"), ("2026-Q2", "date"), ("2026-Q1", "date"), ("social-media", "concept")],
     [],
     "what is the quarterly social-screen target and what is the baseline it reduces from",
     "opal Q2 goal 90 minutes social media Q1 baseline 146 reduction"),
    # --- 38 ---
    ("Prefers deleting the app to hiding it behind Screen Time; the re-install friction is what actually holds, the hide is defeated in a swipe.", "preference", "personal", False,
     [("Screen Time", "tool"), ("app", "concept"), ("re-install", "method")],
     [("re-install", "Screen Time", "PREFERS")],
     "which app-containment method wins and why hiding falls short",
     "delete app over hide screen time reinstall friction actually hold"),
    # --- 39 ---
    ("The attention-reset retreat at Gaia House booked for 2026-05-18 to 2026-05-24 is silent and screen-checked at the door; six days, no phone access.", "milestone", "personal", False,
     [("attention-reset", "method"), ("Gaia House", "place"), ("2026-05-18", "date"), ("2026-05-24", "date")],
     [("attention-reset", "Gaia House", "LOCATED_IN")],
     "when is the next silent retreat and what are the device rules on entry",
     "gaia house retreat silent screen check door six days no phone date"),
    # --- 40 ---
    ("The Freedom Mac block on 2026-03-22 replaced the manual /etc/hosts redirects I was maintaining; same blocklist, auto-sync across phone and laptop.", "decision", "personal", False,
     [("Freedom", "tool"), ("Mac", "platform"), ("2026-03-22", "date"), ("/etc/hosts", "file"), ("blocklist", "concept"), ("laptop", "infrastructure")],
     [("Freedom", "/etc/hosts", "REPLACES")],
     "when did the block tooling consolidate and what ad-hoc method did it supersede",
     "freedom mac over hosts file manual redirect sync phone laptop date"),
    # --- 41 ---
    ("The Cold Turkey Pro Frozen Turkey lockout on 2026-04-02 ran from 09:00 to 18:00 with no override; the password was scrambled into a sealed envelope.", "milestone", "personal", False,
     [("Cold Turkey Pro", "tool"), ("Frozen Turkey", "tool"), ("2026-04-02", "date"), ("password", "concept"), ("envelope", "tool")],
     [("Frozen Turkey", "Cold Turkey Pro", "RELATED_TO")],
     "when was the no-override workday lockout and how was the bypass prevented",
     "cold turkey pro frozen full day password envelope seal bypass date"),
    # --- 42 ---
    ("Kept the Instagram account in read-only mode: signed out of the app, kept the web login, muted every story, unfollowed all brand accounts.", "architecture", "personal", False,
     [("Instagram", "platform"), ("read-only mode", "pattern"), ("app", "concept"), ("web", "platform"), ("story", "concept"), ("brand accounts", "concept")],
     [("Instagram", "read-only mode", "RELATED_TO")],
     "how is the photo app kept on a leash without closing the account and what are the settings",
     "instagram read only web app sign out mute brand unfollow leash"),
    # --- 43 ---
    ("Prefers the monthly phone-free camping weekend over a single long detox; three short resets a year beats one dramatic fortnight for retention.", "preference", "personal", False,
     [("phone-free", "activity"), ("camping weekend", "event"), ("detox", "activity"), ("fortnight", "date")],
     [("camping weekend", "detox", "PREFERS")],
     "which detox cadence wins for me and what is the underlying reasoning",
     "monthly camping weekend over single fortnight detox retention cadence"),
    # --- 44 ---
    ("Replaced the YouTube home-feed habit with a Feedbin RSS list on 2026-01-12; fifteen feeds, no recommendations, chronological, stops when it ends.", "decision", "personal", False,
     [("YouTube", "platform"), ("Feedbin", "tool"), ("2026-01-12", "date"), ("RSS", "protocol"), ("recommendations", "algorithm")],
     [("Feedbin", "YouTube", "REPLACES")],
     "when did the RSS reader take over from the video recommendation feed and how is it bounded",
     "feedbin RSS over youtube recommendation chronological finite date swap"),
    # --- 45 ---
    ("The One Sec pause data export for 2026-Q1 shows 1,142 attempts and 684 app-opens blocked; roughly 60% abandonment rate held steady across weeks.", "fact", "personal", False,
     [("One Sec", "tool"), ("2026-Q1", "date"), ("app-opens", "concept"), ("abandonment rate", "finding")],
     [],
     "what did the quarter of pause-app data say about actual blocked opens",
     "one sec export Q1 attempts blocked 60 abandonment rate steady data"),
    # --- 46 ---
    ("The Apple Focus filter named Commute excludes Slack and mail but allows Spotify and CityMapper; set 2026-02-19 after a missed bus over a Slack pile-up.", "fact", "personal", False,
     [("Apple Focus", "tool"), ("Commute", "concept"), ("Slack", "tool"), ("Spotify", "platform"), ("CityMapper", "tool"), ("2026-02-19", "date")],
     [("Commute", "Apple Focus", "RELATED_TO")],
     "what does the commute focus mode let through and when did I set it up",
     "apple focus commute slack mail excluded spotify citymapper allowed date"),
    # --- 47 ---
    ("Prefers the Light Phone II hotspot-tether workflow on travel days over carrying the iPhone; I carry the iPhone in the backpack for emergencies only.", "preference", "personal", False,
     [("Light Phone II", "infrastructure"), ("hotspot-tether", "method"), ("iPhone", "infrastructure"), ("backpack", "place")],
     [("Light Phone II", "iPhone", "PREFERS"), ("iPhone", "backpack", "LOCATED_IN")],
     "which handset wins on travel days and how is the smartphone backstopped",
     "light phone II tether travel iphone backpack emergency only workflow"),
    # --- 48 ---
    ("Closed the Mastodon account on 2026-03-29; moved the seven people worth following into an RSS bundle via their JSON feeds, no client needed.", "decision", "personal", False,
     [("Mastodon", "platform"), ("2026-03-29", "date"), ("RSS", "protocol"), ("JSON", "language")],
     [("RSS", "Mastodon", "REPLACES")],
     "when did the fediverse account go and how did I keep the people I actually read",
     "mastodon close account RSS bundle JSON feed seven people replace date"),
    # --- 49 ---
    ("The screen-time baseline on 2026-01-01 stood at 4h 37m daily; the 2026-Q1 goal was 2h 30m and the quarterly close came in at 2h 48m — a near miss.", "milestone", "personal", False,
     [("screen-time", "concept"), ("2026-01-01", "date"), ("2026-Q1", "date"), ("baseline", "finding")],
     [],
     "what was the quarterly screen-time target and where did the actual land",
     "screen time baseline Q1 goal 2h 30m actual 2h 48m near miss date"),
    # --- 50 ---
    ("The Opal session-budget Deep Focus ran 2026-03-25 at 06:30 to 09:00, blocking Safari, Mail, Slack, and the widget drawer; finished the essay in one sit.", "fact", "personal", False,
     [("Opal", "tool"), ("Deep Focus", "concept"), ("2026-03-25", "date"), ("Safari", "platform"), ("Mail", "tool"), ("Slack", "tool"), ("essay", "concept")],
     [("Deep Focus", "Opal", "RELATED_TO")],
     "what did the morning deep-focus session cover and what did it produce",
     "opal deep focus morning safari mail slack block essay one sit date"),
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
