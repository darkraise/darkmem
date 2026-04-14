"""One-off emitter for shared-base batch-019 — cross domain (personal productivity meets household software).

Cross rows mix personal entities with technical, ai_coding, or knowledge entities.
Writes 50 rows to data/v2/shared/batch_019.tmp.jsonl with ids shared-00901..00950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_019.tmp.jsonl"
ID_OFFSET = 900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Moved the shared household recipe binder from Paprika to Mealie so my husband Diego could edit from his Linux laptop.", "decision", "cross", False,
     [("Paprika", "tool"), ("Mealie", "service"), ("Diego", "person"), ("Linux", "platform")],
     [("Mealie", "Paprika", "REPLACES")],
     "which kitchen recipe tool took over so my partner could contribute too",
     "cookbook software swap cross-platform partner editing"),
    # --- 2 ---
    ("AnyList keeps the weekly grocery list in sync between my iPhone and Mara's Android so aisle detours stop happening.", "architecture", "cross", False,
     [("AnyList", "service"), ("iPhone", "infrastructure"), ("Mara", "person"), ("Android", "platform")],
     [("AnyList", "iPhone", "COMMUNICATES_WITH")],
     "how do two different phones share the same shopping items without drift",
     "grocery list sync mixed ecosystem household couple"),
    # --- 3 ---
    ("Copilot Money replaced YNAB for joint budgeting after Olivia wanted automatic Chase imports instead of manual envelopes.", "decision", "cross", False,
     [("Copilot Money", "service"), ("YNAB", "tool"), ("Olivia", "person"), ("Chase", "organization")],
     [("Copilot Money", "YNAB", "REPLACES")],
     "why did the household budget app change to auto-import from the bank",
     "budget tool swap automatic transaction partner preference"),
    # --- 4 ---
    ("Prefers 1Password families over Bitwarden for sharing streaming credentials with my sister because the travel mode hides work vaults.", "preference", "cross", False,
     [("1Password", "service"), ("Bitwarden", "service"), ("sister", "person")],
     [("1Password", "Bitwarden", "PREFERS")],
     "which password manager handles sibling sharing plus border-crossing",
     "vault family plan travel mode cross-device sharing"),
    # --- 5 ---
    ("Shared an Apple Family calendar with Tomas in 2026-02-14 so pediatrician visits show up on his Outlook at the office.", "architecture", "cross", False,
     [("Apple Family", "service"), ("Tomas", "person"), ("2026-02-14", "date"), ("Outlook", "service")],
     [("Apple Family", "Outlook", "COMMUNICATES_WITH")],
     "how do the kids' doctor appointments reach my spouse's work calendar",
     "cross-ecosystem family calendar bridge appointments work view"),
    # --- 6 ---
    ("Our Readwise Reader highlight stream funnels Aunt Rita's New Yorker clippings straight into a shared Notion database.", "architecture", "cross", False,
     [("Readwise Reader", "service"), ("Aunt Rita", "person"), ("New Yorker", "publication"), ("Notion", "tool")],
     [("Readwise Reader", "Notion", "COMMUNICATES_WITH")],
     "how does a relative's magazine reading land in the family knowledge base",
     "article highlight pipeline extended family shared workspace"),
    # --- 7 ---
    ("Immich on the home server replaced Google Photos for Grandma's weekly slideshow because she refused the subscription price hike.", "decision", "cross", False,
     [("Immich", "service"), ("Google Photos", "service"), ("Grandma", "person")],
     [("Immich", "Google Photos", "REPLACES")],
     "which photo archive won for an older relative after cloud pricing changed",
     "self-hosted gallery swap grandparent subscription avoidance"),
    # --- 8 ---
    ("Set up Pi-hole on the living-room Raspberry Pi 5 so the in-laws stop getting autoplay ads during Sunday dinner video calls.", "decision", "cross", False,
     [("Pi-hole", "service"), ("Raspberry Pi 5", "infrastructure"), ("in-laws", "person")],
     [("Pi-hole", "Raspberry Pi 5", "DEPLOYED_ON")],
     "why did the household add network-wide ad blocking last month",
     "DNS sinkhole single board computer family dinner ads"),
    # --- 9 ---
    ("Monarch Money pulled three Wells Fargo accounts into a single household dashboard Julia reviews every Sunday night.", "architecture", "cross", False,
     [("Monarch Money", "service"), ("Wells Fargo", "organization"), ("Julia", "person")],
     [],
     "how does the weekly family finance review come together in one place",
     "budget aggregation multi-bank household ritual"),
    # --- 10. noise ---
    ("Give me just a second to think about that.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Bear notes on my iPad and Kenji's Mac both sync through iCloud Drive to keep the 2026 renovation log current.", "architecture", "cross", False,
     [("Bear", "tool"), ("iPad", "infrastructure"), ("Kenji", "person"), ("Mac", "infrastructure"), ("iCloud Drive", "service")],
     [("Bear", "iCloud Drive", "DEPENDS_ON")],
     "how does the home remodel journal stay current across two devices",
     "note app cloud sync couple renovation diary"),
    # --- 12 ---
    ("Fastmail calendar shares a read-only CalDAV link with Gabriela's Thunderbird so the vet visits are never double-booked.", "architecture", "cross", False,
     [("Fastmail", "service"), ("CalDAV", "protocol"), ("Gabriela", "person"), ("Thunderbird", "tool")],
     [("Fastmail", "Thunderbird", "COMMUNICATES_WITH")],
     "how does my partner see the dog appointments without switching mail providers",
     "calendar read-only share protocol partner pet schedule"),
    # --- 13 ---
    ("Switched the toddler's story archive to Kobo because Kindle's partner library locked Farah out of the shared purchases.", "decision", "cross", False,
     [("Kobo", "tool"), ("Kindle", "tool"), ("Farah", "person")],
     [("Kobo", "Kindle", "REPLACES")],
     "why did the family ebook reader change after a sharing limitation",
     "ereader swap partner access child books library"),
    # --- 14 ---
    ("Photoprism running on the attic NAS catalogs every Christmas photo back to 2010 with face tags for Mom, Dad, and the twins.", "architecture", "cross", False,
     [("Photoprism", "service"), ("Christmas", "event"), ("Mom", "person"), ("Dad", "person"), ("twins", "person")],
     [],
     "how is the family holiday photo archive organized by person and year",
     "self-hosted gallery face recognition holiday decade archive"),
    # --- 15 ---
    ("Smart Lock sharing via Aqara lets the cleaner Valentina enter weekdays from 9 to noon without needing a spare key.", "architecture", "cross", False,
     [("Aqara", "tool"), ("Valentina", "person")],
     [],
     "how does the weekday helper get into the house without a physical key",
     "smart lock scheduled access household service provider"),
    # --- 16 ---
    ("Eufy doorbell retention was cut to seven days after Sofia pointed out we never review clips older than a week.", "decision", "cross", False,
     [("Eufy", "tool"), ("Sofia", "person")],
     [],
     "why did the porch camera history window get shortened at home",
     "doorbell video retention policy partner feedback"),
    # --- 17 ---
    ("My elderly neighbour Henryk now receives a daily MedMinder Telegram reminder instead of the paper pill chart his son taped up.", "decision", "cross", False,
     [("Henryk", "person"), ("MedMinder", "service"), ("Telegram", "service"), ("son", "person")],
     [("MedMinder", "Telegram", "USES")],
     "how did the neighbour's medication prompt go from paper to phone",
     "medication reminder bot elder family substitution"),
    # --- 18 ---
    ("Lunch Money categorises Priyanka's freelance invoices so the household tax spreadsheet for 2026 stays clean.", "architecture", "cross", False,
     [("Lunch Money", "service"), ("Priyanka", "person")],
     [],
     "how does the self-employed side income stay tidy for April filings",
     "budget tool freelance categorisation tax prep couple"),
    # --- 19 ---
    ("Started using Todoist shared projects with my mother on 2026-01-09 so grocery runs for her apartment stop falling through.", "milestone", "cross", False,
     [("Todoist", "service"), ("mother", "person"), ("2026-01-09", "date")],
     [],
     "when did the weekly errand list get synced with a parent",
     "task app shared project parent errand tracking"),
    # --- 20 ---
    ("Joy hit when the Synology family share survived a power surge because Wojtek had insisted on the UPS last autumn.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Synology", "tool"), ("Wojtek", "person"), ("UPS", "infrastructure")],
     [],
     "what emotional moment came after the home NAS dodged an electrical event",
     "network storage survival power protection family credit"),
    # --- 21 ---
    ("The family Plex library is mirrored to a Backblaze B2 bucket every Sunday so Julio's niche cinema never ends up re-ripped.", "architecture", "cross", False,
     [("Plex", "service"), ("Backblaze B2", "service"), ("Julio", "person")],
     [("Plex", "Backblaze B2", "COMMUNICATES_WITH")],
     "how is the home media collection protected from an accidental wipe",
     "media library cloud backup partner film archive"),
    # --- 22 ---
    ("Getting Things Done by David Allen still shapes how the 2026-03-30 household retreat agenda is captured in OmniFocus.", "reference", "cross", False,
     [("Getting Things Done", "publication"), ("David Allen", "person"), ("2026-03-30", "date"), ("OmniFocus", "tool")],
     [("Getting Things Done", "David Allen", "AUTHORED_BY")],
     "which productivity book underpins how a family planning day gets captured",
     "GTD methodology task manager household offsite agenda"),
    # --- 23 ---
    ("Home Assistant announces via Sonos when the washing machine finishes so Elena does not leave wet laundry overnight.", "architecture", "cross", False,
     [("Home Assistant", "service"), ("Sonos", "tool"), ("Elena", "person")],
     [("Home Assistant", "Sonos", "COMMUNICATES_WITH")],
     "how does the laundry end-of-cycle alert reach the living room",
     "automation hub speaker announcement appliance spouse"),
    # --- 24 ---
    ("Tried Superhuman for a month but went back to Gmail because Raya could not share a filter set for school PTA mail.", "problem", "cross", False,
     [("Superhuman", "service"), ("Gmail", "service"), ("Raya", "person"), ("PTA", "organization")],
     [],
     "why did the premium email client experiment end after just weeks",
     "email trial rollback partner filter sharing school group"),
    # --- 25 ---
    ("A shared One Medical vault on Proton Drive stores the kids' vaccination records so Daniela can pull them at any pediatric visit.", "architecture", "cross", False,
     [("One Medical", "organization"), ("Proton Drive", "service"), ("Daniela", "person")],
     [],
     "how do the kids' shot records follow whichever parent is at the clinic",
     "health record vault encrypted cloud parental access"),
    # --- 26. noise ---
    ("Let me double-check that figure before I answer.", "fact", "noise", True, [], [], None, None),
    # --- 27 ---
    ("Atomic-shared Cozi Gold calendar prefers coloured tags over Google Calendar's labels so grandparents instantly see Lina's dance nights.", "preference", "cross", False,
     [("Cozi Gold", "service"), ("Google Calendar", "service"), ("Lina", "person")],
     [("Cozi Gold", "Google Calendar", "PREFERS")],
     "which family scheduler won because colour coding helps older relatives",
     "household calendar app colour tags accessibility grandparent"),
    # --- 28 ---
    ("Meal-planning in Plan to Eat pipes the week's ingredients to Instacart automatically every Thursday for Leo's pickup slot.", "architecture", "cross", False,
     [("Plan to Eat", "service"), ("Instacart", "service"), ("Leo", "person")],
     [("Plan to Eat", "Instacart", "COMMUNICATES_WITH")],
     "how does the weekly dinner plan turn into a Thursday grocery order",
     "meal planner grocery delivery automation spouse pickup"),
    # --- 29 ---
    ("Skylight frame in the hallway rotates photos that Mirabel emails from boarding school so Grandpa Luis never feels out of touch.", "architecture", "cross", False,
     [("Skylight", "tool"), ("Mirabel", "person"), ("Grandpa Luis", "person")],
     [],
     "how does a distant grandparent see fresh photos without a smartphone",
     "digital photo frame email ingestion boarding school grandparent"),
    # --- 30 ---
    ("Bitwarden Emergency Access granted to my brother Ethan on 2026-03-05 so the estate paperwork survives if I vanish.", "milestone", "cross", False,
     [("Bitwarden", "service"), ("Ethan", "person"), ("2026-03-05", "date")],
     [],
     "when did a sibling get break-glass rights to the credential vault",
     "password manager emergency access sibling estate planning"),
    # --- 31 ---
    ("Tailscale Funnel exposes Mylio Photos just for Aunt Beatriz so she views grandkid pictures without a cloud account.", "architecture", "cross", False,
     [("Tailscale Funnel", "service"), ("Mylio Photos", "tool"), ("Aunt Beatriz", "person")],
     [("Mylio Photos", "Tailscale Funnel", "USES")],
     "how does an aunt without cloud accounts reach the private photo library",
     "mesh networking remote share photo app extended family"),
    # --- 32 ---
    ("Switched the shared family reading list from Goodreads to Storygraph because Marco hated the Amazon data policy.", "decision", "cross", False,
     [("Goodreads", "service"), ("Storygraph", "service"), ("Marco", "person"), ("Amazon", "organization")],
     [("Storygraph", "Goodreads", "REPLACES")],
     "why did the household book-tracking site change after a policy debate",
     "reading list app swap data privacy partner concern"),
    # --- 33 ---
    ("Frustration rose when Alexa routines kept waking the baby Aurora at 3 AM due to a bad Home Assistant automation I wrote.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Alexa", "service"), ("Aurora", "person"), ("Home Assistant", "service")],
     [("Alexa", "Home Assistant", "DEPENDS_ON")],
     "what domestic disturbance traced back to a bug in my smart home rules",
     "voice assistant false trigger infant automation error emotion"),
    # --- 34 ---
    ("Karin and I chose Proton Calendar over Fastmail for the shared menstrual tracker because of the end-to-end encryption.", "decision", "cross", False,
     [("Karin", "person"), ("Proton Calendar", "service"), ("Fastmail", "service")],
     [("Proton Calendar", "Fastmail", "REPLACES")],
     "why did the couples' cycle tracking schedule change providers",
     "encrypted calendar partner cycle tracker privacy choice"),
    # --- 35 ---
    ("The Hatch Rest's Matter integration produced a morning wake routine that finally matched Sienna's preschool arrival time.", "architecture", "cross", False,
     [("Hatch Rest", "tool"), ("Matter", "protocol"), ("Sienna", "person")],
     [("Hatch Rest", "Matter", "USES")],
     "how does the kids' bedroom light align with school drop-off now",
     "children sleep light smart home protocol preschool schedule"),
    # --- 36 ---
    ("Migrated the wedding RSVP spreadsheet into Airtable so Mariana's aunt can edit dietary notes from her ancient Dell.", "decision", "cross", False,
     [("Airtable", "service"), ("Mariana", "person"), ("Dell", "organization")],
     [],
     "why did the big-day guest list move into a hosted database",
     "event planning spreadsheet migration extended family access"),
    # --- 37 ---
    ("Obsidian Sync holds the shared financial playbook Francesca and I review before any purchase above 2000 euros.", "architecture", "cross", False,
     [("Obsidian Sync", "service"), ("Francesca", "person")],
     [],
     "how do large-spend decisions stay grounded in a shared written rulebook",
     "notes sync couple finance policy reference encrypted"),
    # --- 38 ---
    ("Atomic Habits' implementation intention template is why Rafael's Sunday chore checklist got pinned inside Apple Reminders.", "reference", "cross", False,
     [("Atomic Habits", "publication"), ("Rafael", "person"), ("Apple Reminders", "service")],
     [],
     "which self-help book shaped how a family chore routine gets encoded",
     "habit template chore checklist reminders household lean"),
    # --- 39 ---
    ("AnyList grocery list now auto-generates from Mealie recipe tags since Rowan hates adding staples by hand.", "architecture", "cross", False,
     [("AnyList", "service"), ("Mealie", "service"), ("Rowan", "person")],
     [("AnyList", "Mealie", "DEPENDS_ON")],
     "how does the shopping app fill itself from the week's chosen recipes",
     "meal plan to grocery pipeline partner preference automation"),
    # --- 40 ---
    ("Paid Kagi family plan replaced DuckDuckGo across five household devices after Alina's school research kept returning spam.", "decision", "cross", False,
     [("Kagi", "service"), ("DuckDuckGo", "service"), ("Alina", "person")],
     [("Kagi", "DuckDuckGo", "REPLACES")],
     "why did the family search engine switch after schoolwork frustrations",
     "search engine household swap child research quality"),
    # --- 41 ---
    ("Launched the neighborhood bill-split bot on Signal on 2026-02-25 for the monthly shared lawn-care fund.", "milestone", "cross", False,
     [("Signal", "service"), ("2026-02-25", "date")],
     [],
     "when did the shared yard-care kitty go from spreadsheet to chat bot",
     "messenger bot neighborhood shared expense launch date"),
    # --- 42 ---
    ("Prefers Matter-over-Thread bulbs to Zigbee for the nursery because Bastian found Thread recovered faster after blackouts.", "preference", "cross", False,
     [("Matter", "protocol"), ("Thread", "protocol"), ("Zigbee", "protocol"), ("Bastian", "person")],
     [("Thread", "Zigbee", "PREFERS")],
     "which smart bulb radio won for the baby room after reliability tests",
     "protocol preference nursery smart lighting partner data"),
    # --- 43 ---
    ("The Deep Work idea of scheduling shutdown complete at 5 PM is how Karolina stops checking Slack during dinner.", "reference", "cross", False,
     [("Deep Work", "publication"), ("Karolina", "person"), ("Slack", "service")],
     [],
     "which book concept helped a household member unplug from work messages",
     "focus ritual work-life boundary messenger partner discipline"),
    # --- 44 ---
    ("Fell in love with Beeper Desktop because one inbox now covers my WhatsApp, Telegram, and Signal threads with Abuela.", "preference", "cross", False,
     [("Beeper Desktop", "tool"), ("WhatsApp", "service"), ("Telegram", "service"), ("Signal", "service"), ("Abuela", "person")],
     [("Beeper Desktop", "WhatsApp", "COMMUNICATES_WITH")],
     "which messaging aggregator won for staying in touch with a grandparent",
     "unified inbox multi-messenger grandmother daily chats"),
    # --- 45 ---
    ("Self-hosted Actual Budget on a Mini PC replaced Mint once Intuit shut the app down and Viktor refused cloud alternatives.", "decision", "cross", False,
     [("Actual Budget", "service"), ("Mini PC", "infrastructure"), ("Mint", "service"), ("Intuit", "organization"), ("Viktor", "person")],
     [("Actual Budget", "Mint", "REPLACES"), ("Actual Budget", "Mini PC", "DEPLOYED_ON")],
     "what replaced the shuttered budgeting app for the privacy-conscious spouse",
     "budget self-host partner cloud aversion shutdown migration"),
    # --- 46 ---
    ("Pinboard archive of Tomiko's favourite knitting patterns gets exported to a printed zine every Christmas.", "architecture", "cross", False,
     [("Pinboard", "service"), ("Tomiko", "person"), ("Christmas", "event"), ("knitting", "hobby")],
     [],
     "how does a relative's craft bookmark collection turn into a yearly gift",
     "bookmark archive printed zine hobby holiday present"),
    # --- 47 ---
    ("Relief settled in once the Quad9 DNS swap stopped the phishing popups hitting Babcia's iPad during her morning news.", "milestone", "cross", False,
     [("Relief", "emotion"), ("Quad9", "service"), ("Babcia", "person"), ("iPad", "infrastructure")],
     [("Quad9", "iPad", "COMMUNICATES_WITH")],
     "how did changing the resolver fix the scam pop-ups on a grandparent's tablet",
     "DNS swap phishing block grandmother tablet emotional relief"),
    # --- 48 ---
    ("Bought two Yubikey 5C NFC in Reykjavik during the 2026-03-17 trip so Nils and I share a backup for the household vault.", "milestone", "cross", False,
     [("Yubikey 5C NFC", "tool"), ("Reykjavik", "place"), ("2026-03-17", "date"), ("Nils", "person")],
     [],
     "when and where did we buy the shared hardware keys for the family vault",
     "hardware key purchase partner travel location date"),
    # --- 49 ---
    ("Immich upload from Genoveva's Pixel now feeds directly into a shared timeline the whole family browses on the Apple TV.", "architecture", "cross", False,
     [("Immich", "service"), ("Genoveva", "person"), ("Pixel", "infrastructure"), ("Apple TV", "infrastructure")],
     [("Immich", "Pixel", "COMMUNICATES_WITH")],
     "how do a relative's phone pictures end up on the living-room screen",
     "self-host gallery android upload living room tv display"),
    # --- 50 ---
    ("The 2026-04-09 household retro decided PlainTextAccounting plus Beancount beats Monarch for Alba and me long term.", "decision", "cross", False,
     [("2026-04-09", "date"), ("PlainTextAccounting", "method"), ("Beancount", "tool"), ("Monarch", "service"), ("Alba", "person")],
     [("Beancount", "Monarch", "REPLACES")],
     "when did the family finance system pivot to plain text accounting",
     "ledger method swap hosted app couple long-term choice"),
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
