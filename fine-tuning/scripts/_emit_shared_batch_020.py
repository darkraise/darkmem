"""One-off emitter for shared-base batch-020 — cross domain.

Slice: hobby-gadget projects. Each non-noise row pairs a hobby/activity with
a tool/service/library/infrastructure entity. Writes 50 rows to
data/v2/shared/batch_020.tmp.jsonl with ids shared-00951..01000. The main
session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_020.tmp.jsonl"
ID_OFFSET = 950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Polar H10 heart-rate straps now feed cycling workouts straight into a Golang ingester that writes to InfluxDB.", "architecture", "cross", False,
     [("Polar H10", "tool"), ("cycling", "activity"), ("Golang", "language"), ("InfluxDB", "database")],
     [("Polar H10", "InfluxDB", "COMMUNICATES_WITH")],
     "how do my ride heart-rate traces land in the timeseries store",
     "chest strap bike session custom ingest time database"),
    # --- 2 ---
    ("Weekend home-brewing of a Belgian dubbel pairs with an ESP32 sensor node that posts fermentation gravity to a basement dashboard.", "architecture", "cross", False,
     [("home-brewing", "hobby"), ("Belgian dubbel", "food"), ("ESP32", "infrastructure")],
     [],
     "what watches the beer carboy downstairs during primary",
     "craft ale side project microcontroller sugar reading"),
    # --- 3 ---
    ("Switched photo editing from Capture One to darktable because the Linux workstation in the studio refused to run the macOS licence check.", "decision", "cross", False,
     [("Capture One", "tool"), ("darktable", "tool"), ("Linux", "platform"), ("macOS", "platform")],
     [("darktable", "Capture One", "REPLACES")],
     "why did the RAW processor change on the studio desktop",
     "photography editor swap licence check operating system"),
    # --- 4 ---
    ("The 3D printing rig pushes every slicer job through OrcaSlicer after PrusaSlicer lost support for the Bambu X1C profiles.", "decision", "cross", False,
     [("3D printing", "hobby"), ("OrcaSlicer", "tool"), ("PrusaSlicer", "tool"), ("Bambu X1C", "infrastructure")],
     [("OrcaSlicer", "PrusaSlicer", "REPLACES")],
     "which slicing program took over for the new printer",
     "resin additive job toolchain profile compatibility"),
    # --- 5 ---
    ("The model-train club layout runs an Arduino Mega driving twelve servo turnouts wired along the benchwork.", "fact", "cross", False,
     [("model-train", "hobby"), ("Arduino Mega", "infrastructure")],
     [],
     "what microcontroller runs the club's benchwork point motors",
     "rail modelling servo turnout layout board"),
    # --- 6 ---
    ("Saturdays for amateur radio revolve around GQRX on a HackRF One tuned to the 40-metre band from the garage.", "architecture", "cross", False,
     [("amateur radio", "hobby"), ("GQRX", "tool"), ("HackRF One", "infrastructure")],
     [("GQRX", "HackRF One", "DEPENDS_ON")],
     "what software-radio stack powers the weekend ham sessions",
     "SDR receiver shortwave garage listening hobby"),
    # --- 7 ---
    ("Weekly board-game night scores are captured in BGStats and synced to a Supabase table for the annual Elo recap.", "architecture", "cross", False,
     [("board-game", "hobby"), ("BGStats", "tool"), ("Supabase", "database"), ("Elo", "algorithm")],
     [("BGStats", "Supabase", "COMMUNICATES_WITH")],
     "how do the tabletop results reach the yearly ranking calculator",
     "hobby night score log cloud postgres ranking system"),
    # --- 8 ---
    ("The fantasy football draft prep leans on a Jupyter notebook pulling stats from the Sleeper API every Sunday morning.", "architecture", "cross", False,
     [("fantasy football", "hobby"), ("Jupyter", "tool"), ("Sleeper", "api")],
     [("Jupyter", "Sleeper", "DEPENDS_ON")],
     "how does the weekly draft sheet get refreshed before kickoff",
     "league projection notebook stats endpoint weekend ritual"),
    # --- 9 ---
    ("Our backyard weather monitoring runs an Ecowitt GW2000 gateway feeding Weewx on a Raspberry Pi 4.", "architecture", "cross", False,
     [("weather monitoring", "hobby"), ("Ecowitt GW2000", "tool"), ("Weewx", "library"), ("Raspberry Pi 4", "infrastructure")],
     [("Weewx", "Raspberry Pi 4", "DEPLOYED_ON")],
     "how is the garden rain and wind data collected at home",
     "home station gateway logging daemon small board computer"),
    # --- 10. noise ---
    ("Hold on, I'll grab that information in a second.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Evenings of music production prefer Reaper over Logic Pro because the Reaper ReaScript API unlocks custom MIDI routing.", "preference", "cross", False,
     [("music production", "hobby"), ("Reaper", "tool"), ("Logic Pro", "tool"), ("ReaScript", "api")],
     [("Reaper", "Logic Pro", "PREFERS")],
     "which DAW wins the nightly writing sessions and why",
     "audio software pick scripting hook weeknight studio"),
    # --- 12 ---
    ("The film scanning workflow upgraded from a Plustek 8200i to an Epson V850 after negative strip throughput doubled.", "milestone", "cross", False,
     [("film scanning", "hobby"), ("Plustek 8200i", "tool"), ("Epson V850", "tool")],
     [("Epson V850", "Plustek 8200i", "REPLACES")],
     "what hardware change unlocked faster negative digitisation",
     "analog photo scanner swap throughput weekend chore"),
    # --- 13 ---
    ("The bird-detection camera on the deck runs BirdNET-Pi on an Orange Pi 5 and pings me when a pileated woodpecker shows up.", "architecture", "cross", False,
     [("bird-detection", "hobby"), ("BirdNET-Pi", "library"), ("Orange Pi 5", "infrastructure")],
     [("BirdNET-Pi", "Orange Pi 5", "DEPLOYED_ON")],
     "how does the backyard feeder cam identify visitors automatically",
     "avian spotting acoustic model single board alert"),
    # --- 14 ---
    ("The climbing training app Lattice replaced a paper logbook the week I finally sent my first V6 boulder.", "milestone", "cross", False,
     [("climbing", "hobby"), ("Lattice", "tool"), ("paper logbook", "pattern"), ("V6", "goal")],
     [("Lattice", "paper logbook", "REPLACES")],
     "when did the training tracker go digital for bouldering",
     "rock gym progression paper to app grade milestone"),
    # --- 15 ---
    ("For music collecting, the Beets library manager tags the CD rips on the NAS before Navidrome serves them to the kitchen speaker.", "architecture", "cross", False,
     [("music collecting", "hobby"), ("Beets", "tool"), ("NAS", "infrastructure"), ("Navidrome", "service")],
     [("Navidrome", "NAS", "DEPENDS_ON")],
     "how do ripped albums reach the kitchen sound system cleanly",
     "metadata tagger home storage streaming daemon playback"),
    # --- 16 ---
    ("My chess analysis on Lichess leans on a local Stockfish 16 binary pinned at depth 22 for overnight game reviews.", "architecture", "cross", False,
     [("chess", "hobby"), ("Lichess", "service"), ("Stockfish 16", "tool")],
     [("Lichess", "Stockfish 16", "USES")],
     "what engine powers the post-mortem of last night's games",
     "board game evaluator depth setting cloud interface"),
    # --- 17 ---
    ("My retro gaming moved from RetroArch on the old laptop to a MiSTer FPGA on the shelf once the CRT arrived.", "decision", "cross", False,
     [("retro gaming", "hobby"), ("RetroArch", "tool"), ("MiSTer FPGA", "infrastructure"), ("CRT", "tool")],
     [("MiSTer FPGA", "RetroArch", "REPLACES")],
     "what hardware shift came with bringing the tube display home",
     "emulator swap reconfigurable logic tube display shelf"),
    # --- 18 ---
    ("The gardening sensor network strings six Zigbee soil probes into a Home Assistant dashboard tracking bed moisture.", "architecture", "cross", False,
     [("gardening", "hobby"), ("Zigbee", "protocol"), ("Home Assistant", "service")],
     [],
     "how is the vegetable bed moisture watched across the yard",
     "backyard probe mesh automation hub dashboard"),
    # --- 19 ---
    ("Strava segment chasing on the gravel loop now pulls Wahoo Elemnt Roam GPX files instead of the old Garmin Edge 530.", "decision", "cross", False,
     [("Strava", "service"), ("gravel", "activity"), ("Wahoo Elemnt Roam", "tool"), ("Garmin Edge 530", "tool")],
     [("Wahoo Elemnt Roam", "Garmin Edge 530", "REPLACES")],
     "which head unit feeds the ride site for the dirt route laps",
     "cycling computer swap track file upload segment"),
    # --- 20 ---
    ("Lightroom replaced RawTherapee for the wedding hobby gigs because the face tagging on the Fuji files improved noticeably.", "preference", "cross", False,
     [("Lightroom", "tool"), ("RawTherapee", "tool"), ("wedding", "activity"), ("Fuji", "organization")],
     [("Lightroom", "RawTherapee", "PREFERS")],
     "which editor now handles the side wedding shoots",
     "photo culling preference face index mirrorless files"),
    # --- 21 ---
    ("The birthday marathon goal moved to 2026-09-12 after the Whoop recovery scores suggested an earlier race was too soon.", "decision", "cross", False,
     [("marathon", "goal"), ("2026-09-12", "date"), ("Whoop", "tool")],
     [],
     "when is the big birthday race and what data pushed it",
     "endurance target reschedule band recovery metric"),
    # --- 22 ---
    ("The homelab media stack improves on an older Kodi setup by running Jellyfin on a Proxmox VM with hardware transcoding.", "architecture", "cross", False,
     [("homelab", "hobby"), ("Kodi", "tool"), ("Jellyfin", "service"), ("Proxmox", "platform")],
     [("Jellyfin", "Kodi", "IMPROVES_ON"), ("Jellyfin", "Proxmox", "DEPLOYED_ON")],
     "what media server took over from the old living-room box",
     "home theatre software upgrade hypervisor virtual machine"),
    # --- 23 ---
    ("The ham radio logbook migrated to an SQLite file synced by Syncthing across the shack laptop and the tower laptop.", "architecture", "cross", False,
     [("ham radio", "hobby"), ("SQLite", "database"), ("Syncthing", "service")],
     [],
     "how do contest logs stay in step between my two stations",
     "amateur QSO log embedded store peer sync"),
    # --- 24 ---
    ("A PrusaSlicer profile fix unblocked the 3D printing enclosure job after the nozzle kept clogging on 2026-03-29.", "problem", "cross", False,
     [("PrusaSlicer", "tool"), ("3D printing", "hobby"), ("2026-03-29", "date")],
     [],
     "what printing issue got resolved in late March",
     "slicer settings clog nozzle enclosure project date"),
    # --- 25 ---
    ("Reading The Art of Electronics by Horowitz and Hill before any hobby electronics bench session prevented a second blown ESP32 board.", "reference", "cross", False,
     [("The Art of Electronics", "publication"), ("Horowitz", "person"), ("Hill", "person"), ("hobby electronics", "hobby"), ("ESP32", "infrastructure")],
     [("The Art of Electronics", "Horowitz", "AUTHORED_BY")],
     "which circuit book now sits next to the soldering iron",
     "analog reference textbook bench hobby study microcontroller"),
    # --- 26. noise ---
    ("Give me a minute while I pull up the document.", "fact", "noise", True, [], [], None, None),
    # --- 27 ---
    ("The backyard astrophotography pipeline runs ASIAIR captures through PixInsight and ends in a Flickr upload each Sunday.", "architecture", "cross", False,
     [("astrophotography", "hobby"), ("ASIAIR", "tool"), ("PixInsight", "tool"), ("Flickr", "service")],
     [("ASIAIR", "PixInsight", "COMMUNICATES_WITH")],
     "how do the deep-sky frames travel from telescope to public gallery",
     "mount controller stacking software weekly sharing hobby"),
    # --- 28 ---
    ("Dialled in a Rodecaster Pro 2 for the local history podcasting side project recorded in the basement on Sunday evenings.", "fact", "cross", False,
     [("podcasting", "hobby"), ("Rodecaster Pro 2", "tool")],
     [],
     "what mixer anchors the weekend history show",
     "audio interface hobby podcast basement evening"),
    # --- 29 ---
    ("My hiking trip planning switched from Gaia GPS to CalTopo because the custom slope-angle overlays matter for the winter couloir routes.", "preference", "cross", False,
     [("hiking", "hobby"), ("Gaia GPS", "tool"), ("CalTopo", "tool")],
     [("CalTopo", "Gaia GPS", "PREFERS")],
     "which route-planning app won for snowy alpine terrain",
     "trail planner swap gradient layer backcountry winter"),
    # --- 30 ---
    ("MuseScore 4 rendered the violin arrangement for the niece's recital on 2026-04-05 and exported a MIDI for the accompanist.", "milestone", "cross", False,
     [("MuseScore 4", "tool"), ("violin", "activity"), ("2026-04-05", "date"), ("MIDI", "protocol")],
     [],
     "when did the niece's concert score get finalised and exported",
     "notation software string piece recital date keyboard file"),
    # --- 31 ---
    ("The bouldering strength block ended on 2026-02-28 with a hangboard PR logged in the Crimpd app.", "milestone", "cross", False,
     [("bouldering", "hobby"), ("2026-02-28", "date"), ("Crimpd", "tool")],
     [],
     "when did the finger-strength cycle wrap for the climbing season",
     "training block finish fingerboard record coach app"),
    # --- 32 ---
    ("Dungeons and Dragons campaign notes live in Obsidian vaults synced by Git over the weekly group call.", "architecture", "cross", False,
     [("Dungeons and Dragons", "hobby"), ("Obsidian", "tool"), ("Git", "tool")],
     [("Obsidian", "Git", "USES")],
     "how does the tabletop lore stay shared across the play group",
     "RPG campaign notebook vault version control sync"),
    # --- 33 ---
    ("The custom Strava clone for running depends on a FastAPI backend and a SolidJS dashboard deployed on Fly.io.", "architecture", "cross", False,
     [("Strava", "service"), ("running", "activity"), ("FastAPI", "framework"), ("SolidJS", "framework"), ("Fly.io", "platform")],
     [("SolidJS", "FastAPI", "DEPENDS_ON"), ("FastAPI", "Fly.io", "DEPLOYED_ON")],
     "what stack underpins my personal training dashboard replacement",
     "athlete activity clone API layer frontend hosting"),
    # --- 34 ---
    ("Prefers the Suunto Wing bone-conduction headset over AirPods for long trail-running sessions because the situational awareness matters.", "preference", "cross", False,
     [("Suunto Wing", "tool"), ("AirPods", "tool"), ("trail-running", "activity")],
     [("Suunto Wing", "AirPods", "PREFERS")],
     "which headphones win for forest path runs",
     "bone conduction earbud swap outdoor safety hobby"),
    # --- 35 ---
    ("The Bluesound Node builds on an older Squeezebox setup with Roon integration for the vinyl rip library.", "architecture", "cross", False,
     [("Bluesound Node", "tool"), ("Squeezebox", "tool"), ("Roon", "service"), ("vinyl", "hobby")],
     [("Bluesound Node", "Squeezebox", "BUILDS_ON")],
     "what streamer succeeds the old living-room audio server",
     "network player heir stack software record digitisation"),
    # --- 36 ---
    ("The trail camera in the woods runs a YOLO-v8 model on a Jetson Nano to tag deer and skip raccoons before uploading.", "architecture", "cross", False,
     [("trail camera", "hobby"), ("YOLO-v8", "library"), ("Jetson Nano", "infrastructure")],
     [("YOLO-v8", "Jetson Nano", "DEPLOYED_ON")],
     "how does the woodland cam filter uninteresting critters on device",
     "wildlife detector edge board species triage"),
    # --- 37 ---
    ("My kayaking log book switched to Paddle Logger on the iPhone after the old Notion template kept choking on route maps.", "decision", "cross", False,
     [("kayaking", "hobby"), ("Paddle Logger", "tool"), ("iPhone", "infrastructure"), ("Notion", "tool")],
     [("Paddle Logger", "Notion", "REPLACES")],
     "what app took over the paddling journal on the water",
     "boat trip diary swap mobile tool note workspace"),
    # --- 38 ---
    ("The coffee roasting log on Artisan reads the Phidget thermocouple curve and exports to a shared Google Sheet weekly.", "architecture", "cross", False,
     [("coffee roasting", "hobby"), ("Artisan", "tool"), ("Phidget", "tool"), ("Google Sheet", "service")],
     [("Artisan", "Phidget", "COMMUNICATES_WITH")],
     "how do the bean roast profiles reach the shared weekly log",
     "home roaster temperature probe spreadsheet export"),
    # --- 39 ---
    ("The pinball restoration project fixed a Williams Funhouse Sound Board by 2026-01-30 using a Pinscore replacement kit.", "milestone", "cross", False,
     [("pinball restoration", "hobby"), ("Williams Funhouse", "tool"), ("2026-01-30", "date"), ("Pinscore", "tool")],
     [],
     "when did the arcade cabinet audio come back online",
     "machine repair sound board fix date replacement kit"),
    # --- 40 ---
    ("SDR++ improves on SDR# for the garage amateur radio post because cross-platform support lets the Linux mini PC drive the upconverter.", "preference", "cross", False,
     [("SDR++", "tool"), ("SDR#", "tool"), ("amateur radio", "hobby"), ("Linux", "platform")],
     [("SDR++", "SDR#", "IMPROVES_ON")],
     "which radio front-end runs the cross-platform shack now",
     "software defined receiver swap host operating kit"),
    # --- 41 ---
    ("The music production rig crashed Ableton Live mid-recording on 2026-03-14 when the Focusrite Scarlett driver lost sync over USB 3.", "problem", "cross", False,
     [("music production", "hobby"), ("Ableton Live", "tool"), ("2026-03-14", "date"), ("Focusrite Scarlett", "tool"), ("USB 3", "protocol")],
     [],
     "what bug killed the mid-March studio session recording",
     "DAW crash interface driver bus standard take"),
    # --- 42 ---
    ("Plans to rebuild the gardening irrigation with Rachio 3 controllers and add drip lines before summer 2026.", "fact", "cross", False,
     [("gardening", "hobby"), ("Rachio 3", "tool"), ("summer 2026", "date")],
     [],
     "what backyard watering overhaul is queued for the warm season",
     "yard upgrade controller drip line target season"),
    # --- 43 ---
    ("Reading Zen Mind, Beginner's Mind by Shunryu Suzuki has reshaped how I approach practice at the local aikido dojo.", "reference", "cross", False,
     [("Zen Mind, Beginner's Mind", "publication"), ("Shunryu Suzuki", "person"), ("aikido", "hobby")],
     [("Zen Mind, Beginner's Mind", "Shunryu Suzuki", "AUTHORED_BY")],
     "which book changed my mindset on the mat this year",
     "philosophy title martial art practice attitude"),
    # --- 44 ---
    ("The woodworking shop notebook moved from index cards to Notion after the router table plans kept disappearing.", "decision", "cross", False,
     [("woodworking", "hobby"), ("Notion", "tool"), ("index cards", "pattern")],
     [("Notion", "index cards", "REPLACES")],
     "why did the shop plans stop living on paper",
     "hobby bench notebook digital workspace lost plans"),
    # --- 45 ---
    ("My mountain biking GPX files get merged into a single yearly heatmap using a small Rust CLI and uploaded to Tracestrack.", "architecture", "cross", False,
     [("mountain biking", "hobby"), ("Rust", "language"), ("Tracestrack", "service")],
     [],
     "how do my singletrack rides turn into the annual map",
     "trail route aggregation small tool yearly visualization"),
    # --- 46 ---
    ("My fly fishing trip notes depend on Troutbitten articles more than Orvis ones after two seasons of tippet experiments.", "reference", "cross", False,
     [("fly fishing", "hobby"), ("Troutbitten", "publication"), ("Orvis", "organization")],
     [("fly fishing", "Troutbitten", "DEPENDS_ON")],
     "which fishing resource outranks the big-box guide for my river notes",
     "stream angling blog preference retail guide tippet"),
    # --- 47 ---
    ("The fantasy baseball draft spreadsheet on Google Sheets now imports FanGraphs projections via an Apps Script nightly job.", "architecture", "cross", False,
     [("fantasy baseball", "hobby"), ("Google Sheets", "service"), ("FanGraphs", "service"), ("Apps Script", "language")],
     [("Google Sheets", "FanGraphs", "COMMUNICATES_WITH")],
     "how do the nightly player projections refresh on the draft sheet",
     "league prep workbook stats site scripted import"),
    # --- 48 ---
    ("The BoardGameGeek tracker for board-gaming builds on an older Airtable base with a new Hono API and a Turso SQLite store.", "architecture", "cross", False,
     [("BoardGameGeek", "service"), ("board-gaming", "hobby"), ("Airtable", "tool"), ("Hono", "framework"), ("Turso", "database")],
     [("Hono", "Airtable", "BUILDS_ON"), ("Hono", "Turso", "DEPENDS_ON")],
     "what backend took over from the no-code base for the tabletop tracker",
     "collection service evolution edge API cloud store"),
    # --- 49 ---
    ("The birding life list hit 300 species on 2026-04-10 after the Merlin recording confirmed a vesper sparrow in the meadow.", "milestone", "cross", False,
     [("birding", "hobby"), ("2026-04-10", "date"), ("Merlin", "tool")],
     [],
     "when did the life list clear three hundred with acoustic help",
     "bird watching target count app identification recording"),
    # --- 50 ---
    ("Deep frustration spiked for the 3D printing hobby when the OctoPrint webcam stream kept cutting mid-print on the Ender 3, until a powered USB hub fixed it.", "problem", "cross", False,
     [("frustration", "emotion"), ("3D printing", "hobby"), ("OctoPrint", "tool"), ("Ender 3", "infrastructure")],
     [],
     "what dropped the live view on the filament machine during long runs",
     "print host camera feed hub power fix"),
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
