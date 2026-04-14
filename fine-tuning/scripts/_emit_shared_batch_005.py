"""One-off emitter for shared-base batch-005 — cross domain.

Cross rows intentionally mix entities across personal, technical, ai_coding,
and knowledge domains. Appends 50 rows to data/v2/shared/shared.jsonl with
ids shared-00201..00250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 200  # batches 001..004 consumed shared-00001..00200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Using Obsidian for personal notes as well as engineering design documents at Lumen.", "preference", "cross", False,
     [("Obsidian", "tool"), ("Lumen", "organization")],
     [],
     "which tool stores both engineering docs and my private diary",
     "single markdown editor spanning job and life contexts"),
    # --- 2 ---
    ("Chose Anki over Quizlet for Spanish vocabulary review; the spaced repetition fit my commute time.", "decision", "cross", False,
     [("Anki", "tool"), ("Quizlet", "tool"), ("Spanish", "hobby")],
     [("Anki", "Quizlet", "REPLACES")],
     "which flashcard app won for studying the second language on the go",
     "memorisation app pick train-ride learning switch"),
    # --- 3 ---
    ("The Garmin watch stopped syncing step counts on Fridays after a firmware update broke Bluetooth pairing.", "problem", "cross", False,
     [("Garmin", "tool"), ("Bluetooth", "protocol")],
     [],
     "why did activity data fail to reach the phone at week's end",
     "wrist wearable sync failure update regression"),
    # --- 4 ---
    ("Shipped the marathon training tracker app on 2026-03-15 after six months of weekend coding.", "milestone", "cross", False,
     [("marathon training tracker", "project"), ("2026-03-15", "date")],
     [],
     "when did my personal running side project go live",
     "fitness side build launch date release"),
    # --- 5 ---
    ("The deliberate practice chapter in Peak by Anders Ericsson reshaped how I structure code review sessions.", "reference", "cross", False,
     [("Peak", "publication"), ("Anders Ericsson", "person"), ("code review", "activity")],
     [("Peak", "Anders Ericsson", "AUTHORED_BY")],
     "which book changed my approach to reviewing teammates' diffs",
     "skill acquisition title engineering feedback influence"),
    # --- 6 ---
    ("Daily schedule uses Todoist for personal errands and Linear for work tickets, synced by a Zapier rule.", "architecture", "cross", False,
     [("Todoist", "tool"), ("Linear", "tool"), ("Zapier", "tool")],
     [],
     "how do home and office tasks stay aligned across apps",
     "two-app split automation between errands and tickets"),
    # --- 7 ---
    ("Prefers reading technical papers on the Kindle over a tablet; fewer distractions and a week of battery.", "preference", "cross", False,
     [("Kindle", "tool"), ("tablet", "tool"), ("technical papers", "publication")],
     [("Kindle", "tablet", "PREFERS")],
     "what device wins for reading dense academic PDFs",
     "e-ink reader versus LCD study reading habit"),
    # --- 8 ---
    ("Spotify's family plan kept kicking Jamie off after IP changes on our home network.", "problem", "cross", False,
     [("Spotify", "service"), ("Jamie", "person")],
     [],
     "what streaming subscription issue hit my partner at home",
     "music app family member address rotation bug"),
    # --- 9 ---
    ("Switched running playlists from Apple Music to Spotify after the algorithm surfaced better pace-matched tracks.", "decision", "cross", False,
     [("Apple Music", "service"), ("Spotify", "service"), ("running playlists", "activity")],
     [("Spotify", "Apple Music", "REPLACES")],
     "what streaming service took over for workouts",
     "media app swap tempo-aware recommendation reason"),
    # --- 10. noise ---
    ("Let me take a quick look and get back to you.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Training a small GLiNER model on my RTX 5060 at home takes roughly 40 minutes per epoch.", "fact", "cross", False,
     [("GLiNER", "library"), ("RTX 5060", "infrastructure")],
     [],
     "how long does one pass of the local extraction model take at home",
     "consumer GPU epoch wall time NER training"),
    # --- 12 ---
    ("Ran the first LAN party at our flat on 2026-02-14 with four friends and a self-hosted Minecraft server.", "milestone", "cross", False,
     [("LAN party", "event"), ("2026-02-14", "date"), ("Minecraft", "tool")],
     [],
     "when did the debut home gaming meetup happen",
     "multiplayer evening flat hosting Valentine block game"),
    # --- 13 ---
    ("Watching Andrej Karpathy's neural network lectures on YouTube before bed most weekends.", "architecture", "cross", False,
     [("Andrej Karpathy", "person"), ("neural network", "concept"), ("YouTube", "service")],
     [],
     "whose deep learning videos get weekend viewing here",
     "tutorial series creator evening routine learner"),
    # --- 14 ---
    ("Stress from the product launch triggered the migraines again until I cut evening Slack notifications.", "problem", "cross", False,
     [("Stress", "emotion"), ("product launch", "event"), ("Slack notifications", "config")],
     [],
     "how did I shut down the headaches caused by a release crunch",
     "shipping pressure chronic pain messaging cutoff"),
    # --- 15 ---
    ("Picked Proxmox over Unraid for the home lab because the cluster features matter for my failover experiments.", "decision", "cross", False,
     [("Proxmox", "platform"), ("Unraid", "platform"), ("home lab", "infrastructure")],
     [("Proxmox", "Unraid", "REPLACES")],
     "which hypervisor won the hobby server selection and why",
     "cluster-friendly virtualisation pick failover hobby"),
    # --- 16 ---
    ("Home network has a UniFi gateway, a separate IoT VLAN, and a WireGuard tunnel I open when travelling.", "architecture", "cross", False,
     [("UniFi", "tool"), ("IoT VLAN", "infrastructure"), ("WireGuard", "library")],
     [],
     "how is the flat's networking segmented and accessed remotely",
     "home router layout smart-device isolation remote access"),
    # --- 17 ---
    ("Prefers async standups over daily video calls; typed updates fit the neurodiverse team rhythm better.", "preference", "cross", False,
     [("async standups", "pattern"), ("daily video calls", "pattern")],
     [("async standups", "daily video calls", "PREFERS")],
     "which standup format works better for the group's makeup",
     "written status versus synchronous meeting preference"),
    # --- 18 ---
    ("Running Ollama on the Mac Studio for local summarisation of personal journals every Sunday.", "architecture", "cross", False,
     [("Ollama", "service"), ("Mac Studio", "infrastructure"), ("journals", "activity")],
     [],
     "what weekend task uses the home AI setup on my desktop",
     "local model Apple desktop diary condensing routine"),
    # --- 19 ---
    ("Reached 200k step count in a single week on 2026-04-10 during the walking-focused holiday in Kyoto.", "milestone", "cross", False,
     [("Kyoto", "place"), ("2026-04-10", "date")],
     [],
     "when did I hit the biggest step week ever and where was I",
     "peak pedometer week trip Japanese city"),
    # --- 20 ---
    ("The vacation photo sync broke because iCloud Photos hit the free-tier 5 GB cap mid-trip.", "problem", "cross", False,
     [("iCloud Photos", "service")],
     [],
     "why did holiday pictures stop backing up halfway through the trip",
     "cloud storage free quota exhaustion travel issue"),
    # --- 21 ---
    ("Dr. Huberman's episode on caffeine and sleep informs the 2 PM cutoff in my work calendar blocks.", "reference", "cross", False,
     [("Dr. Huberman", "person"), ("caffeine", "food"), ("work calendar", "tool")],
     [],
     "which podcast guidance shapes my afternoon coffee rule at the office",
     "neuroscience advice stimulant boundary agenda policy"),
    # --- 22 ---
    ("Moved the family budget from a Google Sheet to YNAB; Sam found the envelope model easier to audit.", "decision", "cross", False,
     [("Google Sheet", "tool"), ("YNAB", "tool"), ("Sam", "person")],
     [("YNAB", "Google Sheet", "REPLACES")],
     "why did household finance tracking migrate tools",
     "budgeting spreadsheet swap envelope method audit"),
    # --- 23 ---
    ("Uses Markdown for everything — work notes, recipes, even birthday card drafts.", "preference", "cross", False,
     [("Markdown", "language")],
     [],
     "which plain text format covers all my writing contexts",
     "lightweight markup universal writing habit across life"),
    # --- 24 ---
    ("The home Kubernetes cluster runs Immich for photos, Paperless-ngx for documents, and a Ghost blog.", "architecture", "cross", False,
     [("Kubernetes", "platform"), ("Immich", "service"), ("Paperless-ngx", "service"), ("Ghost", "service")],
     [("Immich", "Kubernetes", "DEPLOYED_ON"), ("Paperless-ngx", "Kubernetes", "DEPLOYED_ON"), ("Ghost", "Kubernetes", "DEPLOYED_ON")],
     "what self-hosted apps run on top of the home orchestrator",
     "container cluster photo scan blog workload mix"),
    # --- 25 ---
    ("Laptop dotfiles, shell config, and personal Python utilities all live in one repo managed by chezmoi.", "architecture", "cross", False,
     [("dotfiles", "file"), ("Python", "language"), ("chezmoi", "tool")],
     [],
     "how is my developer environment kept consistent across machines",
     "config management single repo shell tooling approach"),
    # --- 26. noise ---
    ("Give me a second — I need to re-read the last part.", "fact", "noise", True, [], [], None, None),
    # --- 27 ---
    ("Finished fine-tuning my first embedder on 2026-04-12 using the laptop's RTX 5060 and six hours of patience.", "milestone", "cross", False,
     [("embedder", "project"), ("2026-04-12", "date"), ("RTX 5060", "infrastructure")],
     [],
     "when did my very first embedding model training complete at home",
     "side project representation model wrap consumer hardware"),
    # --- 28 ---
    ("Swapped Gmail for Fastmail; keeping Anna's wedding thread searchable outweighed the convenience loss.", "decision", "cross", False,
     [("Gmail", "service"), ("Fastmail", "service"), ("Anna", "person")],
     [("Fastmail", "Gmail", "REPLACES")],
     "what email provider change was driven by a family archival need",
     "mail service swap friend correspondence searchable"),
    # --- 29 ---
    ("GPS accuracy on the Apple Watch drops in the Dolomites canyons, which threw off my hiking route logs.", "problem", "cross", False,
     [("Apple Watch", "tool"), ("Dolomites", "place")],
     [],
     "where did my smartwatch's positioning fail me on a hike",
     "wearable satellite reception mountain trail data loss"),
    # --- 30 ---
    ("Reads Tolstoy in paperback and textbooks on a reMarkable; screens are fine for technical material but not fiction.", "preference", "cross", False,
     [("Tolstoy", "person"), ("reMarkable", "tool")],
     [],
     "how do I split my reading between paper and an e-paper device",
     "novel versus study medium split literary reading"),
    # --- 31 ---
    ("The Nix configuration for my ThinkPad also sets up Jamie's work laptop with the same dev environment.", "architecture", "cross", False,
     [("Nix", "tool"), ("ThinkPad", "infrastructure"), ("Jamie", "person")],
     [],
     "what config tool bridges my computer and my partner's work one",
     "reproducible environment shared household developer setup"),
    # --- 32 ---
    ("Andy Matuschak's working notes on evergreen notes shaped how I structure both code comments and family recipes.", "reference", "cross", False,
     [("Andy Matuschak", "person"), ("evergreen notes", "concept")],
     [],
     "whose note-taking philosophy influences my code and kitchen docs alike",
     "atomic note author influence dev and recipe writing"),
    # --- 33 ---
    ("Runs a Postgres instance on the home server for the habit tracker, meal planner, and training log.", "architecture", "cross", False,
     [("Postgres", "database"), ("habit tracker", "project"), ("meal planner", "project"), ("training log", "project")],
     [("habit tracker", "Postgres", "DEPENDS_ON"), ("meal planner", "Postgres", "DEPENDS_ON"), ("training log", "Postgres", "DEPENDS_ON")],
     "what database backs the personal side-project apps at home",
     "home server datastore routine nutrition fitness apps"),
    # --- 34 ---
    ("Using Tailscale over a self-hosted VPN for getting Maya into the shared Plex library remotely.", "decision", "cross", False,
     [("Tailscale", "service"), ("self-hosted VPN", "service"), ("Maya", "person"), ("Plex", "service")],
     [("Tailscale", "self-hosted VPN", "REPLACES")],
     "what networking layer did we pick for letting a friend reach the home media server",
     "mesh network choice friend remote media library"),
    # --- 35 ---
    ("The dog's GPS collar drained its battery faster than it could get through the fence; returned it.", "problem", "cross", False,
     [("GPS collar", "tool")],
     [],
     "why did the pet tracker gadget go back to the store",
     "canine locator battery disappointment return"),
    # --- 36 ---
    ("Finally automated the bill-splitting spreadsheet with a Google Apps Script macro on 2026-03-30.", "milestone", "cross", False,
     [("bill-splitting spreadsheet", "project"), ("Google Apps Script", "library"), ("2026-03-30", "date")],
     [],
     "when did the shared expense sheet go from manual to automatic",
     "household finance sheet macro script automation date"),
    # --- 37 ---
    ("Prefers to take calls from the outdoor desk with the Kyoto skyline view over the home office.", "preference", "cross", False,
     [("outdoor desk", "place"), ("Kyoto", "place"), ("home office", "place")],
     [("outdoor desk", "home office", "PREFERS")],
     "where do I like to hold video meetings most",
     "open-air workspace scenic backdrop remote call"),
    # --- 38 ---
    ("The AeroPress brew ratio I settled on is 14 grams of coffee to 220 ml of water at 85 degrees.", "fact", "cross", False,
     [("AeroPress", "tool"), ("coffee", "food")],
     [],
     "what are the fixed numbers for my morning cup",
     "manual brewer gram millilitre temperature recipe"),
    # --- 39 ---
    ("The Getting Things Done framework by David Allen is the backbone of both my work inbox and my grocery list.", "reference", "cross", False,
     [("Getting Things Done", "publication"), ("David Allen", "person")],
     [("Getting Things Done", "David Allen", "AUTHORED_BY")],
     "which productivity framework organises both my job tasks and errands",
     "GTD methodology author unified life management"),
    # --- 40 ---
    ("Started paying for ChatGPT Plus because Sarah's college applications needed serious editing help.", "decision", "cross", False,
     [("ChatGPT Plus", "service"), ("Sarah", "person")],
     [],
     "what prompted the upgrade to the paid AI assistant tier",
     "AI subscription daughter academic admissions help"),
    # --- 41 ---
    ("Home automation routes through Home Assistant; motion in the hallway triggers the kids' night lights.", "architecture", "cross", False,
     [("Home Assistant", "service"), ("motion", "pattern"), ("night lights", "tool")],
     [],
     "how does the house respond when someone walks at night",
     "smart home hub corridor movement bedroom lighting"),
    # --- 42 ---
    ("VS Code crashed every time I opened the Whole30 meal-plan spreadsheet via the SQLite extension.", "problem", "cross", False,
     [("VS Code", "tool"), ("Whole30", "organization"), ("SQLite", "database")],
     [],
     "which combination of app and plugin caused the repeatable freeze",
     "editor database plugin diet plan file crash"),
    # --- 43 ---
    ("For family travel bookings, Kayak's predictions beat Google Flights for the Berlin-Lisbon routes.", "preference", "cross", False,
     [("Kayak", "service"), ("Google Flights", "service"), ("Berlin", "place"), ("Lisbon", "place")],
     [("Kayak", "Google Flights", "PREFERS")],
     "which flight search tool wins for our Europe trips",
     "airfare aggregator pick transcontinental route"),
    # --- 44 ---
    ("My RTX 5060 handles both gaming with the kids and fine-tuning GLiNER without thermal throttling.", "fact", "cross", False,
     [("RTX 5060", "infrastructure"), ("GLiNER", "library")],
     [],
     "how does the home GPU cope with both play and model training",
     "consumer GPU dual-use kids games extraction training"),
    # --- 45 ---
    ("Gave my first conference talk about home lab observability at DevOpsCon Kyoto on 2026-04-08.", "milestone", "cross", False,
     [("home lab", "infrastructure"), ("DevOpsCon Kyoto", "event"), ("2026-04-08", "date")],
     [],
     "when and where did I give my debut speaking slot",
     "first public talk monitoring topic Japanese venue"),
    # --- 46 ---
    ("The ZFS pool on the NAS holds the full personal photo archive back to 2005 with snapshots taken weekly.", "architecture", "cross", False,
     [("ZFS", "technology"), ("NAS", "infrastructure"), ("2005", "date")],
     [],
     "where does the long-term family picture history live",
     "copy-on-write filesystem photo vault weekly snapshot"),
    # --- 47 ---
    ("Chose Logseq over Notion for personal notes; the local-first store meant my medical records stayed on-device.", "decision", "cross", False,
     [("Logseq", "tool"), ("Notion", "tool")],
     [("Logseq", "Notion", "REPLACES")],
     "which personal note app won on data sovereignty grounds",
     "outliner pick offline-first health data privacy"),
    # --- 48 ---
    ("Followed Atul Gawande's checklist philosophy when designing the pre-flight checks for the deployment pipeline.", "reference", "cross", False,
     [("Atul Gawande", "person"), ("checklist", "concept"), ("deployment pipeline", "project")],
     [],
     "whose medical-world framework inspired our release gating",
     "surgeon author guideline adoption CI gate"),
    # --- 49 ---
    ("Pairing the Garmin with Strava doubled my runs in the weekly leaderboard with the running group.", "problem", "cross", False,
     [("Garmin", "tool"), ("Strava", "service"), ("running group", "organization")],
     [],
     "what integration double-counted my training sessions",
     "wearable social app sync leaderboard duplicate"),
    # --- 50 ---
    ("Family calendar is shared via a Radicale server on the NAS; all phones sync through CalDAV over WireGuard.", "architecture", "cross", False,
     [("Radicale", "service"), ("NAS", "infrastructure"), ("CalDAV", "protocol"), ("WireGuard", "library")],
     [("Radicale", "NAS", "DEPLOYED_ON")],
     "how does the household share schedules across devices",
     "self-hosted calendar protocol mesh networking household"),
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
