"""One-off emitter for shared-base batch-010 — cross domain.

Cross rows intentionally mix entities across personal, technical, ai_coding,
and knowledge domains. Writes 50 rows to data/v2/shared/batch_010.tmp.jsonl
with ids shared-00451..00500. The main session aggregates the tmp file into
shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_010.tmp.jsonl"
ID_OFFSET = 450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Started using Cursor for weekend side-project coding after it completed a SwiftUI view faster than I could sketch it.", "preference", "cross", False,
     [("Cursor", "tool"), ("SwiftUI", "framework")],
     [],
     "what editor changed how I tackle hobby iOS work on Saturdays",
     "AI pair programmer adoption weekend mobile UI"),
    # --- 2 ---
    ("The Whoop band feeds nightly recovery scores into a Grafana board I stare at with morning coffee.", "architecture", "cross", False,
     [("Whoop", "tool"), ("Grafana", "service"), ("coffee", "food")],
     [("Whoop", "Grafana", "COMMUNICATES_WITH")],
     "how do my sleep metrics reach the dashboard I check at breakfast",
     "wearable recovery pipeline visualization morning ritual"),
    # --- 3 ---
    ("Self-hosted Vaultwarden so my mother could manage her bank passwords without trusting a US cloud provider.", "decision", "cross", False,
     [("Vaultwarden", "service"), ("mother", "person")],
     [],
     "why did I stand up a local password manager for a family member",
     "credential vault aging parent data sovereignty"),
    # --- 4 ---
    ("Reading Designing Data-Intensive Applications by Martin Kleppmann pushed me toward SQLite for the tree-sitter cache.", "reference", "cross", False,
     [("Designing Data-Intensive Applications", "publication"), ("Martin Kleppmann", "person"), ("SQLite", "database"), ("tree-sitter", "library")],
     [("Designing Data-Intensive Applications", "Martin Kleppmann", "AUTHORED_BY")],
     "which storage book nudged my parser cache choice",
     "distributed systems title embedded database influence"),
    # --- 5 ---
    ("Duolingo streak hit 400 days on 2026-03-22 the same morning we booked flights to Tokyo.", "milestone", "cross", False,
     [("Duolingo", "tool"), ("2026-03-22", "date"), ("Tokyo", "place")],
     [],
     "when did the language app streak cross four hundred and what trip was locked in",
     "language practice consecutive day mark travel booking overlap"),
    # --- 6 ---
    ("Logs every tomato and cucumber yield in a Logseq graph so I can compare it against last season's planting notes.", "architecture", "cross", False,
     [("tomato", "food"), ("cucumber", "food"), ("Logseq", "tool")],
     [],
     "how is the backyard garden harvest tracked year over year",
     "vegetable patch recording outliner knowledge graph comparison"),
    # --- 7 ---
    ("Picked RAW over HEIC for Lightroom imports on the home server because the Fuji colour profiles need the wider headroom.", "decision", "cross", False,
     [("RAW", "technology"), ("HEIC", "technology"), ("Lightroom", "tool"), ("Fuji", "organization")],
     [("RAW", "HEIC", "PREFERS")],
     "which image format wins for archival edits on the NAS",
     "photography negative file pick mirrorless camera palette"),
    # --- 8 ---
    ("TurboTax kept rejecting the joint return until I realised Hannah's ITIN had the last digit transposed.", "problem", "cross", False,
     [("TurboTax", "service"), ("Hannah", "person"), ("ITIN", "concept")],
     [],
     "what blocked the household filing and how was it traced",
     "tax filing software rejection taxpayer id typo"),
    # --- 9 ---
    ("Teaching my nephew to code through Pico-8 because the 128-pixel constraint forces finishing over polishing.", "preference", "cross", False,
     [("Pico-8", "platform"), ("nephew", "person")],
     [],
     "what tiny game engine am I using for a relative's programming lessons",
     "fantasy console mentorship completion mindset teaching"),
    # --- 10. noise ---
    ("One moment, let me pull that up for you.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Home Assistant pulls real-time Emporia Vue readings and shuts off the dryer when solar drops below 2 kW.", "architecture", "cross", False,
     [("Home Assistant", "service"), ("Emporia Vue", "tool"), ("dryer", "tool")],
     [("Home Assistant", "Emporia Vue", "COMMUNICATES_WITH")],
     "how does the house throttle appliances when the panels dim",
     "automation hub energy monitor load shedding solar"),
    # --- 12 ---
    ("Swapped the August smart lock for a Level Bolt so the Airbnb visitors do not need an extra app.", "decision", "cross", False,
     [("August", "service"), ("Level Bolt", "tool"), ("Airbnb", "organization")],
     [("Level Bolt", "August", "REPLACES")],
     "why did the front door hardware change for short-term guests",
     "entry device swap rental friction mobile app"),
    # --- 13 ---
    ("Google Calendar now shares a custom feed with Outlook at the office so Priya's daycare pickups show up in my work view.", "architecture", "cross", False,
     [("Google Calendar", "service"), ("Outlook", "service"), ("Priya", "person")],
     [],
     "how do the childcare pickups surface in my job calendar",
     "personal schedule work client feed cross-sync pickup"),
    # --- 14 ---
    ("Pocket fills with long-form articles during the commute and Readwise turns them into Anki cards on Sundays.", "architecture", "cross", False,
     [("Pocket", "service"), ("Readwise", "service"), ("Anki", "tool")],
     [("Readwise", "Pocket", "DEPENDS_ON")],
     "what pipeline moves train-ride reading into spaced repetition",
     "saved article highlight flashcard weekly batch flow"),
    # --- 15 ---
    ("Digitised roughly eighty VHS tapes from my parents' attic with a Domesday Duplicator and an LSI capture card.", "milestone", "cross", False,
     [("VHS", "technology"), ("Domesday Duplicator", "tool"), ("LSI", "organization")],
     [],
     "how did the family video archive project actually happen",
     "analog tape rescue specialised capture hardware attic"),
    # --- 16 ---
    ("Built the bedroom monitor rig on a Behringer UMC204HD feeding Ableton Live on a mini PC tucked behind the desk.", "architecture", "cross", False,
     [("Behringer UMC204HD", "tool"), ("Ableton Live", "tool"), ("mini PC", "infrastructure")],
     [("Ableton Live", "mini PC", "DEPLOYED_ON")],
     "how is the home music production setup wired together",
     "audio interface DAW small form factor studio chain"),
    # --- 17 ---
    ("The RTX 5060 drives Baldur's Gate 3 on the TV by evening and a Qwen 3.5 4B fine-tune at night.", "fact", "cross", False,
     [("RTX 5060", "infrastructure"), ("Baldur's Gate 3", "tool"), ("Qwen 3.5 4B", "library")],
     [],
     "how does the single GPU get reused for gaming and model work",
     "consumer card shift living-room play overnight training"),
    # --- 18 ---
    ("Alexa routines switched off after I learned the skill manifest sends every utterance to Amazon in plaintext.", "decision", "cross", False,
     [("Alexa", "service"), ("Amazon", "organization")],
     [],
     "why did the voice assistant routines get disabled at home",
     "smart speaker retirement transcript privacy cloud"),
    # --- 19 ---
    ("Launched the Cleveland Brews podcast on 2026-01-18 with audio recorded on a Shure MV7 and edited in Reaper.", "milestone", "cross", False,
     [("Cleveland Brews", "project"), ("2026-01-18", "date"), ("Shure MV7", "tool"), ("Reaper", "tool")],
     [],
     "when did the beer interview show debut and on what kit",
     "side-podcast first episode microphone editor stack"),
    # --- 20 ---
    ("Twilio auto-texts my wife a Lyft ETA link whenever a late meeting pushes past 8 PM.", "architecture", "cross", False,
     [("Twilio", "service"), ("wife", "person"), ("Lyft", "service")],
     [("Twilio", "Lyft", "COMMUNICATES_WITH")],
     "how does she find out I am running behind without me texting",
     "SMS gateway rideshare alert late work evening"),
    # --- 21 ---
    ("Hooked a Raspberry Pi to the basement freezer; a cron job DMs me on Discord when the temperature drifts above minus 12.", "architecture", "cross", False,
     [("Raspberry Pi", "infrastructure"), ("Discord", "service")],
     [("Raspberry Pi", "Discord", "COMMUNICATES_WITH")],
     "how do I get told when the food storage warms up downstairs",
     "single board computer chat alert freezer sensor"),
    # --- 22 ---
    ("Deep Work by Cal Newport pushed me to block 9 AM to noon on the shared calendar for heads-down refactors.", "reference", "cross", False,
     [("Deep Work", "publication"), ("Cal Newport", "person")],
     [("Deep Work", "Cal Newport", "AUTHORED_BY")],
     "which productivity book drove the morning focus block",
     "focus book author morning calendar protection"),
    # --- 23 ---
    ("Prefers Signal for coordinating with my Berlin team over WhatsApp; end-to-end metadata handling was the deciding factor.", "preference", "cross", False,
     [("Signal", "service"), ("Berlin", "place"), ("WhatsApp", "service")],
     [("Signal", "WhatsApp", "PREFERS")],
     "which chat app do I use with the overseas coworkers",
     "messenger pick distributed team metadata minimisation"),
    # --- 24 ---
    ("iA Writer on iPad syncs to the home Nextcloud where scripts transclude the draft into the Hugo blog.", "architecture", "cross", False,
     [("iA Writer", "tool"), ("iPad", "infrastructure"), ("Nextcloud", "service"), ("Hugo", "framework")],
     [("iA Writer", "Nextcloud", "COMMUNICATES_WITH")],
     "how do tablet drafts end up on the published website",
     "iPad writing cloud sync static site generation chain"),
    # --- 25 ---
    ("The twins' Scratch birthday-card program froze until I realised the stage dimensions were pinned to retro mode.", "problem", "cross", False,
     [("twins", "person"), ("Scratch", "platform")],
     [],
     "what kids' coding bug came down to an obscure stage setting",
     "block programming greeting card freeze legacy canvas"),
    # --- 26. noise ---
    ("Hold on, need to check my notes first.", "fact", "noise", True, [], [], None, None),
    # --- 27 ---
    ("Kept an offline Kiwix copy of Wikipedia on the Steam Deck for the Patagonia trek; signal coverage was non-existent.", "decision", "cross", False,
     [("Kiwix", "tool"), ("Wikipedia", "service"), ("Steam Deck", "infrastructure"), ("Patagonia", "place")],
     [("Kiwix", "Wikipedia", "USES")],
     "what reading stash went on the handheld for the remote trek",
     "offline reference archive handheld console wilderness hike"),
    # --- 28 ---
    ("The Philips Hue bridge dropped every device from Home Assistant after a 2026-02-07 firmware push and a factory reset fixed it.", "problem", "cross", False,
     [("Philips Hue", "tool"), ("Home Assistant", "service"), ("2026-02-07", "date")],
     [],
     "how did the lighting integration recover from a mid-winter outage",
     "lamp bridge automation outage update recovery factory"),
    # --- 29 ---
    ("Moved the kids' allowance from paper envelopes to Greenlight cards after Leo kept losing the cash on the bus.", "decision", "cross", False,
     [("Greenlight", "service"), ("Leo", "person"), ("paper envelopes", "pattern")],
     [("Greenlight", "paper envelopes", "REPLACES")],
     "why did pocket money at home go digital",
     "kid debit card transition misplaced bills commute"),
    # --- 30 ---
    ("Atomic Habits by James Clear is behind the two-minute rule governing my chore list and my Git commit cadence.", "reference", "cross", False,
     [("Atomic Habits", "publication"), ("James Clear", "person"), ("Git", "tool")],
     [("Atomic Habits", "James Clear", "AUTHORED_BY")],
     "what book quietly shapes both my cleaning and versioning habits",
     "behaviour design title chore frequency commit rhythm"),
    # --- 31 ---
    ("Notion Calendar replaced Fantastical for the family because the shared Notion database needed bidirectional links.", "decision", "cross", False,
     [("Notion Calendar", "service"), ("Fantastical", "tool"), ("Notion", "tool")],
     [("Notion Calendar", "Fantastical", "REPLACES")],
     "why did the household calendar app flip again",
     "scheduling app swap linked database household"),
    # --- 32 ---
    ("FreshRSS on a cheap VPS serves the morning news feed and the Hacker News front page to my Fiery reader app.", "architecture", "cross", False,
     [("FreshRSS", "service"), ("VPS", "infrastructure"), ("Hacker News", "service"), ("Fiery", "tool")],
     [("FreshRSS", "VPS", "DEPLOYED_ON")],
     "how is my daily news reading stitched together at home",
     "self-hosted feed aggregator tech news mobile client"),
    # --- 33 ---
    ("Piper TTS reads toddler bedtime stories off a Markdown folder because store-bought audiobooks skip local dialect.", "architecture", "cross", False,
     [("Piper TTS", "library"), ("Markdown", "language")],
     [],
     "how do bedtime narrations get generated at home with a regional voice",
     "speech synthesis child bedtime dialect gap local files"),
    # --- 34 ---
    ("The Kindle Scribe finally replaced the Moleskine for interview note-taking once Whispersync tagged by meeting date.", "decision", "cross", False,
     [("Kindle Scribe", "tool"), ("Moleskine", "tool"), ("Whispersync", "service")],
     [("Kindle Scribe", "Moleskine", "REPLACES")],
     "what digital notebook won over the paper one for job interviews",
     "e-ink notebook switch paper journal meeting metadata"),
    # --- 35 ---
    ("Marcus Aurelius' Meditations sits on the desk next to the on-call runbook; both get opened during rough incidents.", "reference", "cross", False,
     [("Marcus Aurelius", "person"), ("Meditations", "publication"), ("on-call runbook", "file")],
     [("Meditations", "Marcus Aurelius", "AUTHORED_BY")],
     "which ancient book keeps me steady during production incidents",
     "stoic philosophy title production firefight desk companion"),
    # --- 36 ---
    ("Migrated Mum's medical records from the hospital portal to a local Bitwarden-encrypted PDF vault on 2026-04-02.", "milestone", "cross", False,
     [("Bitwarden", "service"), ("2026-04-02", "date")],
     [],
     "when did we finish the personal health record consolidation",
     "hospital export local encrypted archive family health"),
    # --- 37 ---
    ("Prefers pairing on Zed over Tuple for the afternoon open-source sessions with Oscar in Lisbon.", "preference", "cross", False,
     [("Zed", "tool"), ("Tuple", "tool"), ("Oscar", "person"), ("Lisbon", "place")],
     [("Zed", "Tuple", "PREFERS")],
     "which pairing tool won for remote open-source work with a friend",
     "collaborative editor pick afternoon session iberian timezone"),
    # --- 38 ---
    ("The Teslamate stack on Proxmox logs every drive the leased Model 3 takes to daycare and back.", "architecture", "cross", False,
     [("Teslamate", "service"), ("Proxmox", "platform"), ("Model 3", "tool")],
     [("Teslamate", "Proxmox", "DEPLOYED_ON")],
     "what records every short EV trip including daycare runs",
     "vehicle telemetry self-host hypervisor sedan commute"),
    # --- 39 ---
    ("Fine-tuned a local Whisper variant on Mum's Polish accent so voice memos transcribe accurately.", "milestone", "cross", False,
     [("Whisper", "library"), ("Polish", "language"), ("Mum", "person")],
     [],
     "what speech model was tailored for a family member's accent",
     "ASR adaptation non-native voice note accuracy"),
    # --- 40 ---
    ("Our 2026-05-04 Berlin trip is being planned in Kayak because Google Flights keeps hiding the Vueling leg.", "problem", "cross", False,
     [("2026-05-04", "date"), ("Berlin", "place"), ("Kayak", "service"), ("Google Flights", "service"), ("Vueling", "organization")],
     [],
     "why did one travel aggregator lose out for an upcoming European trip",
     "flight search hidden carrier early summer city break"),
    # --- 41 ---
    ("Claude Code writes the tedious pytest fixtures for the side SaaS; I still hand-write the domain logic.", "preference", "cross", False,
     [("Claude Code", "tool"), ("pytest", "framework"), ("SaaS", "project")],
     [],
     "how is the AI assistant slotted into my weekend startup work",
     "coding agent boilerplate tests human business logic split"),
    # --- 42 ---
    ("A Tasmota-flashed Sonoff plug measures the espresso machine warm-up and posts to MQTT for the kitchen dashboard.", "architecture", "cross", False,
     [("Tasmota", "library"), ("Sonoff", "tool"), ("MQTT", "protocol")],
     [("Sonoff", "MQTT", "COMMUNICATES_WITH")],
     "how does the coffee machine energy story reach the morning screen",
     "custom firmware outlet telemetry kitchen display"),
    # --- 43 ---
    ("Cancelled the Pelaton digital subscription because the Apple Fitness Plus workouts fit the Dad-lunchbreak window better.", "decision", "cross", False,
     [("Pelaton", "service"), ("Apple Fitness Plus", "service")],
     [("Apple Fitness Plus", "Pelaton", "REPLACES")],
     "which exercise subscription won after a schedule reshuffle",
     "workout service swap parent midday slot"),
    # --- 44 ---
    ("Joy flooded the room when Leila read her first Polish sentence on 2026-03-11 after six months of Duolingo with me.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Leila", "person"), ("Polish", "language"), ("2026-03-11", "date"), ("Duolingo", "tool")],
     [],
     "when did my daughter read her first heritage language sentence",
     "emotional milestone child bilingual reading date app"),
    # --- 45 ---
    ("The Karpathy micrograd walkthrough taught both me and my teen niece matrix calculus over spring break.", "reference", "cross", False,
     [("Karpathy", "person"), ("micrograd", "project"), ("teen niece", "person")],
     [],
     "which teaching resource bonded a relative over deep learning basics",
     "autograd tutorial mentor relative spring holiday maths"),
    # --- 46 ---
    ("Kagi replaced Google as the default search everywhere because the ad-free results match the home screen-time ethos.", "decision", "cross", False,
     [("Kagi", "service"), ("Google", "service")],
     [("Kagi", "Google", "REPLACES")],
     "which search engine took over across our devices",
     "paid search swap clean results screen time values"),
    # --- 47 ---
    ("Dad's hearing aids pair to the Sonos system so he hears Radio 4 at the same volume as everyone else.", "architecture", "cross", False,
     [("Dad", "person"), ("Sonos", "tool"), ("Radio 4", "service")],
     [("Sonos", "Radio 4", "COMMUNICATES_WITH")],
     "how does the living-room audio include a family member with hearing loss",
     "speaker system accessibility broadcast parent inclusion"),
    # --- 48 ---
    ("Side project deadline for the homelab cookbook is 2026-06-30 so Nadia and I can present it at the Toronto meetup.", "fact", "cross", False,
     [("homelab cookbook", "project"), ("2026-06-30", "date"), ("Nadia", "person"), ("Toronto", "place")],
     [],
     "when is the joint home lab book shipping and which event anchors it",
     "hobby book target date co-author local tech gathering"),
    # --- 49 ---
    ("Reolink doorbell footage gets scrubbed of faces on Frigate before any clip reaches the shared Synology folder.", "architecture", "cross", False,
     [("Reolink", "tool"), ("Frigate", "service"), ("Synology", "tool")],
     [("Frigate", "Reolink", "DEPENDS_ON")],
     "how does front-porch video respect visitors' privacy before archival",
     "doorbell camera face blur local NVR NAS storage"),
    # --- 50 ---
    ("Fine-tuning the embedder on 2026-04-14 stalled overnight because the dehumidifier tripped the studio breaker.", "problem", "cross", False,
     [("embedder", "project"), ("2026-04-14", "date"), ("dehumidifier", "tool")],
     [],
     "why did the weekend training run die before morning",
     "model run interruption humidity appliance circuit trip"),
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
