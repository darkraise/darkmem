"""One-off emitter for shared-base batch-034 — cross domain.

Slice: gaming as it intersects with tech tooling and personal life. Writes 50
rows to data/v2/shared/batch_034.tmp.jsonl with ids shared-01651..01700. The
main session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_034.tmp.jsonl"
ID_OFFSET = 1650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Steam Deck library finally stabilised once Proton-GE replaced the default Proton build for the weekend Yakuza runs.", "decision", "cross", False,
     [("Steam Deck", "infrastructure"), ("Proton-GE", "tool"), ("Proton", "tool"), ("Yakuza", "concept")],
     [("Proton-GE", "Proton", "REPLACES")],
     "which compatibility layer took over the handheld for weekend RPG sessions",
     "handheld console compatibility fork weekend JRPG swap"),
    # --- 2 ---
    ("SteamOS eats my external SSD's exFAT partition every other boot, so the ROM collection now lives on a btrfs volume managed by CryoUtilities.", "problem", "cross", False,
     [("SteamOS", "platform"), ("SSD", "infrastructure"), ("exFAT", "technology"), ("btrfs", "technology"), ("CryoUtilities", "tool")],
     [("CryoUtilities", "btrfs", "CONFIGURES")],
     "why did the portable game drive get reformatted for the handheld",
     "handheld OS filesystem corruption external drive utility fix"),
    # --- 3 ---
    ("Sharing the Steam Family Library with my sister Priya in Manchester keeps her kids playing Stardew Valley without doubling the purchase.", "architecture", "cross", False,
     [("Steam Family Library", "service"), ("Priya", "person"), ("Manchester", "place"), ("Stardew Valley", "concept")],
     [("Priya", "Manchester", "LIVES_IN")],
     "how does the household share farm games without buying the title twice",
     "library sharing relative remote city farming sim cost avoidance"),
    # --- 4 ---
    ("The Minecraft server for the kids runs on a Raspberry Pi 5 in the hallway cabinet with PaperMC tuned to 32 view-distance.", "architecture", "cross", False,
     [("Minecraft", "concept"), ("Raspberry Pi 5", "infrastructure"), ("PaperMC", "service")],
     [("PaperMC", "Raspberry Pi 5", "DEPLOYED_ON")],
     "where does the household block-building server actually live",
     "kids server single board computer tuned distro lightweight build"),
    # --- 5 ---
    ("Factorio multiplayer with Diego in Buenos Aires pushed us to host a dedicated headless server on Hetzner instead of peer hosting.", "decision", "cross", False,
     [("Factorio", "concept"), ("Diego", "person"), ("Buenos Aires", "place"), ("Hetzner", "organization")],
     [("Diego", "Buenos Aires", "LIVES_IN")],
     "why did the factory game session move off peer hosting for the long-distance friend",
     "automation game remote friend dedicated server latency migration"),
    # --- 6 ---
    ("Sunday evenings now follow the Lichess-to-Stockfish analysis loop with the cloud engine set to depth 22 on the laptop fan profile.", "architecture", "cross", False,
     [("Lichess", "service"), ("Stockfish", "tool"), ("depth 22", "concept")],
     [("Lichess", "Stockfish", "USES")],
     "how does the weekly chess review routine run on the home laptop",
     "chess platform engine depth evening review fan control"),
    # --- 7 ---
    ("Tabletop Simulator plus Foundry VTT handles D&D night for the Thursday group even when Marco has to join from the Milan office.", "architecture", "cross", False,
     [("Tabletop Simulator", "tool"), ("Foundry VTT", "tool"), ("D&D", "hobby"), ("Thursday", "date"), ("Marco", "person"), ("Milan", "place")],
     [],
     "how does the weekly role-playing night keep running when a player is abroad",
     "virtual tabletop RPG session remote player office weeknight"),
    # --- 8 ---
    ("Backloggd replaced the Notion database for game backlog tracking once the import CSV exposed all 412 of my finished titles cleanly.", "decision", "cross", False,
     [("Backloggd", "service"), ("Notion", "service"), ("CSV", "pattern")],
     [("Backloggd", "Notion", "REPLACES")],
     "which tracker won for logging completed games after the bulk import",
     "backlog service notes database CSV migration completion list"),
    # --- 9 ---
    ("Project Zomboid runs cleaner on the gaming desktop after Rin's curated mod list from the Seattle pod ripped out the broken weather overhaul.", "problem", "cross", False,
     [("Project Zomboid", "concept"), ("Rin", "person"), ("Seattle", "place"), ("weather overhaul", "concept")],
     [("Rin", "Seattle", "LIVES_IN")],
     "how did the zombie survival build stop crashing on the big rig",
     "mod manager curated list friend fix climate mod desktop"),
    # --- 10. noise ---
    ("Give me a sec to grab coffee.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("OpenRA now launches from a single Bottles prefix on the Linux workstation so the Red Alert 2 nights with Omar feel native.", "architecture", "cross", False,
     [("OpenRA", "tool"), ("Bottles", "tool"), ("Linux", "platform"), ("Red Alert 2", "concept"), ("Omar", "person")],
     [("OpenRA", "Bottles", "DEPENDS_ON")],
     "how does the classic RTS evening run on the Linux rig with a friend",
     "open source engine prefix manager desktop friend match"),
    # --- 12 ---
    ("RetroArch keeps the SNES and PS1 cores paired to specific 8BitDo controllers so Kenji always gets player two on the Saturday couch co-op.", "preference", "cross", False,
     [("RetroArch", "tool"), ("SNES", "platform"), ("PS1", "platform"), ("8BitDo", "tool"), ("Kenji", "person")],
     [],
     "how does the retro couch night assign the controllers to the right friend",
     "multi-emulator controller pairing couch co-op friend preference"),
    # --- 13 ---
    ("ROM organisation finally clicked after EmulationStation started scraping from ScreenScraper on the living-room HTPC.", "fact", "cross", False,
     [("ROM", "pattern"), ("EmulationStation", "tool"), ("ScreenScraper", "service"), ("HTPC", "infrastructure")],
     [("EmulationStation", "ScreenScraper", "USES")],
     "what tool made the retro library metadata actually readable",
     "frontend scraper metadata living room media box organisation"),
    # --- 14 ---
    ("Voice chat for game night moved off Steam Voice to Mumble on a self-hosted VPS because the Discord push-to-talk delay annoyed Hana.", "decision", "cross", False,
     [("Steam Voice", "service"), ("Mumble", "tool"), ("VPS", "infrastructure"), ("Discord", "service"), ("Hana", "person")],
     [("Mumble", "Steam Voice", "REPLACES"), ("Mumble", "VPS", "DEPLOYED_ON")],
     "why did the game-night voice chat leave the default platforms",
     "low-latency voice self-hosted alternative friend complaint migration"),
    # --- 15 ---
    ("The hobby Twitch channel broadcasting weekly Celeste runs launched on 2026-02-08 from the den PC.", "milestone", "cross", False,
     [("Twitch", "service"), ("Celeste", "concept"), ("2026-02-08", "date"), ("den PC", "infrastructure")],
     [],
     "when did the weekly platformer stream actually go live",
     "streaming service platformer game launch date home PC"),
    # --- 16 ---
    ("OBS profiles sync between the den PC and the laptop through a small Syncthing share so scenes travel with me to Claire's place.", "architecture", "cross", False,
     [("OBS", "tool"), ("den PC", "infrastructure"), ("Syncthing", "tool"), ("Claire", "person")],
     [("OBS", "Syncthing", "DEPENDS_ON")],
     "how do my streaming scenes follow me when I stream from a friend's place",
     "broadcaster config sync portable streaming friend house guest"),
    # --- 17 ---
    ("Bought an Elgato HD60 X capture card specifically to record the Switch speedrun attempts with my nephew Leo over winter break.", "decision", "cross", False,
     [("Elgato HD60 X", "tool"), ("Switch", "platform"), ("Leo", "person"), ("winter break", "event")],
     [],
     "why did the capture card purchase happen and what was it for",
     "capture hardware console speedrun nephew holiday recording"),
    # --- 18 ---
    ("Game night on the shared family calendar now auto-creates a Discord event through a Zapier chain so nobody forgets the 7 PM start.", "architecture", "cross", False,
     [("family calendar", "pattern"), ("Discord", "service"), ("Zapier", "service")],
     [("Zapier", "Discord", "COMMUNICATES_WITH")],
     "how do household gaming nights get announced automatically in chat",
     "calendar automation group chat reminder family evening schedule"),
    # --- 19 ---
    ("Fantasy football in Sleeper uses a custom scoring rule set that Raj drafted to keep the Delhi crew fair against our late Pacific picks.", "reference", "cross", False,
     [("Sleeper", "service"), ("Raj", "person"), ("Delhi", "place"), ("Pacific", "place")],
     [("Raj", "Delhi", "LIVES_IN")],
     "which league format keeps the cross-timezone fantasy draft balanced",
     "fantasy sports league custom rules timezone fairness draft"),
    # --- 20 ---
    ("Prefers the ROG Ally over the Steam Deck for Helldivers 2 because the Ryzen Z1 Extreme handles the dust effects without stutter.", "preference", "cross", False,
     [("ROG Ally", "infrastructure"), ("Steam Deck", "infrastructure"), ("Helldivers 2", "concept"), ("Ryzen Z1 Extreme", "technology")],
     [("ROG Ally", "Steam Deck", "PREFERS")],
     "which handheld won for the co-op shooter and why",
     "handheld comparison shooter particle effects chipset choice"),
    # --- 21 ---
    ("Deck Verified titles get a green tag in my Playnite library, with a small Python script pulling the status from SteamDB nightly.", "architecture", "cross", False,
     [("Deck Verified", "concept"), ("Playnite", "tool"), ("Python", "language"), ("SteamDB", "service")],
     [("Playnite", "SteamDB", "DEPENDS_ON")],
     "how does my game launcher show handheld compatibility at a glance",
     "launcher library compatibility indicator nightly scrape tagging"),
    # --- 22 ---
    ("The Nintendo Switch 2 preorder confirmation landed on 2026-03-12 and locked in the launch-day Mario Kart session with Mia.", "milestone", "cross", False,
     [("Nintendo Switch 2", "platform"), ("2026-03-12", "date"), ("Mario Kart", "concept"), ("Mia", "person")],
     [],
     "when was the next-gen console locked in and with whom for launch day",
     "console preorder date launch day friend racing session"),
    # --- 23 ---
    ("Mods for Skyrim finally installed without breaking saves once MO2 replaced Vortex on the Steam Deck with a Flatseal permission tweak.", "decision", "cross", False,
     [("Skyrim", "concept"), ("MO2", "tool"), ("Vortex", "tool"), ("Steam Deck", "infrastructure"), ("Flatseal", "tool")],
     [("MO2", "Vortex", "REPLACES")],
     "which mod manager became reliable for the portable open-world game",
     "mod organiser replacement handheld sandbox permission fix"),
    # --- 24 ---
    ("The Jellyfin server holds every Game Grumps episode Lina and I watch before Tuesday board-game night at the studio in Lyon.", "architecture", "cross", False,
     [("Jellyfin", "service"), ("Game Grumps", "concept"), ("Lina", "person"), ("Lyon", "place")],
     [("Lina", "Lyon", "LIVES_IN")],
     "where do we store the gaming variety show we watch before tabletop night",
     "media server gaming variety show friend weekly ritual city"),
    # --- 25 ---
    ("Xbox Cloud Gaming on the iPad covers the hotel commute to Osaka for the quarterly client visits so Forza sessions never pause.", "architecture", "cross", False,
     [("Xbox Cloud Gaming", "service"), ("iPad", "infrastructure"), ("Osaka", "place"), ("Forza", "concept")],
     [("Xbox Cloud Gaming", "iPad", "DEPLOYED_ON")],
     "how does the racing game keep going during the quarterly business trips",
     "cloud gaming tablet business travel foreign city racing pause"),
    # --- 26. noise ---
    ("Sure, that makes sense.", "fact", "noise", True, [], [], None, None),
    # --- 27 ---
    ("Sunshine plus Moonlight streams my desktop Baldur's Gate 3 save to the couch tablet so Noa can join mid-encounter from the kitchen.", "architecture", "cross", False,
     [("Sunshine", "tool"), ("Moonlight", "tool"), ("Baldur's Gate 3", "concept"), ("Noa", "person")],
     [("Moonlight", "Sunshine", "COMMUNICATES_WITH")],
     "how does the RPG save reach the couch tablet for the partner to join",
     "game stream host client desktop tablet partner encounter"),
    # --- 28 ---
    ("Switched the D&D initiative tracker from paper to Improved Initiative because Freya's laptop handles the broadcast overlay on Roll20.", "decision", "cross", False,
     [("D&D", "hobby"), ("Improved Initiative", "tool"), ("Freya", "person"), ("Roll20", "service")],
     [("Improved Initiative", "Roll20", "COMMUNICATES_WITH")],
     "which tool replaced the paper initiative tracker at the tabletop night",
     "tabletop turn tracker overlay virtual tabletop partner laptop"),
    # --- 29 ---
    ("Pokemon ROM hacks live in a separate EmulationStation collection so our nine-year-old Hiro only sees the age-appropriate builds.", "architecture", "cross", False,
     [("Pokemon", "concept"), ("EmulationStation", "tool"), ("Hiro", "person")],
     [],
     "how are the retro games filtered so the kid only sees what is allowed",
     "frontend collection parental control child-safe retro set"),
    # --- 30 ---
    ("Completed the 100% Hollow Knight achievement run on 2026-04-03 after syncing the save with HowLongToBeat through a tiny Go script.", "milestone", "cross", False,
     [("Hollow Knight", "concept"), ("2026-04-03", "date"), ("HowLongToBeat", "service"), ("Go", "language")],
     [],
     "when did the metroidvania completion run actually finish and where is it logged",
     "metroidvania completion achievement date playtime service Go bridge"),
    # --- 31 ---
    ("Anxiety about lag during the Tekken 8 tournament dropped once the PowerLine Ethernet adapters landed on the living-room TV.", "problem", "cross", False,
     [("Anxiety", "emotion"), ("Tekken 8", "concept"), ("PowerLine", "tool"), ("Ethernet", "protocol")],
     [],
     "what fixed the competitive fighting game lag at home",
     "fighting game tournament latency home network hardware fix"),
    # --- 32 ---
    ("Preordering Elden Ring: Nightreign locked in a local co-op weekend with my brother Mateo in Porto for the April release.", "milestone", "cross", False,
     [("Elden Ring: Nightreign", "concept"), ("Mateo", "person"), ("Porto", "place"), ("April", "date")],
     [("Mateo", "Porto", "LIVES_IN")],
     "when will the brothers meet up for the souls-like co-op weekend",
     "preorder souls-like release sibling visit port city coop weekend"),
    # --- 33 ---
    ("Controller profile switching on the DualSense moved to reWASD after Steam Input kept forgetting the custom Rocket League gyro curve.", "decision", "cross", False,
     [("DualSense", "tool"), ("reWASD", "tool"), ("Steam Input", "service"), ("Rocket League", "concept")],
     [("reWASD", "Steam Input", "REPLACES")],
     "which utility took over controller config after the gyro curve kept dropping",
     "controller software replacement gyro remap car soccer game"),
    # --- 34 ---
    ("The Dungeons & Dragons campaign notes live in a shared Obsidian vault so Priya, Marco and I all see Sasha's NPC sheet mid-session.", "architecture", "cross", False,
     [("Dungeons & Dragons", "hobby"), ("Obsidian", "tool"), ("Priya", "person"), ("Marco", "person"), ("Sasha", "person")],
     [],
     "how do the DM and players share campaign notes during the weekly session",
     "TTRPG shared vault live notes player DM NPC reference"),
    # --- 35 ---
    ("Prefers the Razer Kishi V2 with the Pixel over a full Backbone rig because the USB-C latch survives the daily backpack commute.", "preference", "cross", False,
     [("Razer Kishi V2", "tool"), ("Pixel", "platform"), ("Backbone", "tool")],
     [("Razer Kishi V2", "Backbone", "PREFERS")],
     "which phone controller won for the daily commute and why",
     "phone controller mobile rig commute durability choice"),
    # --- 36 ---
    ("The annual LAN party in Utrecht every 2026-10-11 booked the Airbnb already because Joren locks the venue six months out.", "milestone", "cross", False,
     [("LAN party", "event"), ("Utrecht", "place"), ("2026-10-11", "date"), ("Airbnb", "service"), ("Joren", "person")],
     [],
     "when is the annual LAN party and who handles the venue booking",
     "annual LAN gathering foreign city accommodation friend organiser date"),
    # --- 37 ---
    ("Bolt's Dreamcast fork boots reliably on the Steam Deck only after the Flycast core replaced Reicast in RetroArch.", "fact", "cross", False,
     [("Dreamcast", "platform"), ("Steam Deck", "infrastructure"), ("Flycast", "tool"), ("Reicast", "tool"), ("RetroArch", "tool")],
     [("Flycast", "Reicast", "REPLACES")],
     "which emulator core fixed the retro console on the handheld",
     "emulator core swap handheld retro console reliability"),
    # --- 38 ---
    ("Twitch chat moderation runs through Sery_Bot with a custom Python handler for the Friday Celeste streams plus a Discord webhook for VOD clips.", "architecture", "cross", False,
     [("Twitch", "service"), ("Sery_Bot", "tool"), ("Python", "language"), ("Celeste", "concept"), ("Discord", "service")],
     [("Sery_Bot", "Discord", "COMMUNICATES_WITH")],
     "how does the weekly platformer stream handle chat moderation and clips",
     "chat moderation bot custom handler weekly stream clip crosspost"),
    # --- 39 ---
    ("Frustration with Nintendo's cloud save limits pushed the family group to JKSV on the Switch to backup Animal Crossing locally.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Nintendo", "organization"), ("JKSV", "tool"), ("Switch", "platform"), ("Animal Crossing", "concept")],
     [("JKSV", "Switch", "DEPLOYED_ON")],
     "what tool rescued the family's island save from the cloud limits",
     "console cloud limit save backup homebrew family island"),
    # --- 40 ---
    ("The Stream Deck on the studio desk has a dedicated page for Amelie's game-night intros so OBS scene swaps happen with one tap.", "architecture", "cross", False,
     [("Stream Deck", "tool"), ("Amelie", "person"), ("OBS", "tool")],
     [("Stream Deck", "OBS", "COMMUNICATES_WITH")],
     "how are the co-host intro scenes triggered during the weekly show",
     "macro keypad co-host intro scene switch one touch workflow"),
    # --- 41 ---
    ("Prefers Mumble over Discord for the competitive Counter-Strike nights because the Opus bitrate cap still feels tighter for callouts.", "preference", "cross", False,
     [("Mumble", "tool"), ("Discord", "service"), ("Counter-Strike", "concept"), ("Opus", "protocol")],
     [("Mumble", "Discord", "PREFERS")],
     "which voice platform wins for competitive shooter callouts and why",
     "voice chat codec competitive shooter callout clarity choice"),
    # --- 42 ---
    ("Yuzu's shutdown pushed the Zelda replay over to Ryujinx on the Arch desktop once the shader cache imported cleanly.", "decision", "cross", False,
     [("Yuzu", "tool"), ("Zelda", "concept"), ("Ryujinx", "tool"), ("Arch", "platform"), ("shader cache", "concept")],
     [("Ryujinx", "Yuzu", "REPLACES")],
     "which emulator picked up the adventure game replay after the shutdown",
     "emulator project shutdown replay migration shader cache desktop"),
    # --- 43 ---
    ("The shared Sleeper league invite from 2026-08-30 puts the cousins Priya, Raj and Mateo into one bracket for the NFL season kickoff.", "milestone", "cross", False,
     [("Sleeper", "service"), ("2026-08-30", "date"), ("Priya", "person"), ("Raj", "person"), ("Mateo", "person"), ("NFL", "event")],
     [],
     "when does the family fantasy bracket lock in and who is in it",
     "fantasy league family bracket season start cousins invite date"),
    # --- 44 ---
    ("Shadow of the Colossus replay on the PS5 triggered a Plex clip archive routed through Tdarr so the highlight reels stay in h265.", "architecture", "cross", False,
     [("Shadow of the Colossus", "concept"), ("PS5", "platform"), ("Plex", "service"), ("Tdarr", "tool"), ("h265", "technology")],
     [("Tdarr", "Plex", "USES")],
     "how do gameplay highlights from the console get stored in the media server",
     "classic replay console capture media library transcode archive"),
    # --- 45 ---
    ("DayZ sessions with the London pod fixed their desync once the community server switched from DayZSA Launcher to DZSA with Rin's mod list.", "problem", "cross", False,
     [("DayZ", "concept"), ("London", "place"), ("DayZSA Launcher", "tool"), ("DZSA", "tool"), ("Rin", "person")],
     [("DZSA", "DayZSA Launcher", "REPLACES")],
     "what combination fixed the open-world survival desync for the remote pod",
     "survival game desync launcher swap curated mod list friend"),
    # --- 46 ---
    ("OBS Studio replaced Streamlabs on the streaming rig once the plugin crashes started eating the Wednesday Apex Legends runs.", "decision", "cross", False,
     [("OBS Studio", "tool"), ("Streamlabs", "tool"), ("Apex Legends", "concept")],
     [("OBS Studio", "Streamlabs", "REPLACES")],
     "which broadcaster survived on the stream rig after the crashes",
     "broadcaster swap plugin stability weekly shooter stream"),
    # --- 47 ---
    ("The GameCube controller adapter finally talks to Dolphin on macOS thanks to the Delfinovin driver Aarav walked me through during the Mumbai call.", "fact", "cross", False,
     [("GameCube", "platform"), ("Dolphin", "tool"), ("macOS", "platform"), ("Delfinovin", "tool"), ("Aarav", "person"), ("Mumbai", "place")],
     [("Dolphin", "Delfinovin", "DEPENDS_ON"), ("Aarav", "Mumbai", "LIVES_IN")],
     "how did the classic console adapter finally get recognised on the Apple laptop",
     "console adapter emulator driver macOS friend debugging remote call"),
    # --- 48 ---
    ("Rocksmith+ subscription sits next to the Focusrite on the practice desk because weekly jam sessions with Noa count as both hobby and music tech.", "preference", "cross", False,
     [("Rocksmith+", "service"), ("Focusrite", "tool"), ("Noa", "person")],
     [],
     "why does the guitar game live on the same desk as the audio interface",
     "rhythm game audio interface practice ritual partner jam"),
    # --- 49 ---
    ("Embarrassment at losing rank in Valorant faded after the Logitech G Pro X Superlight replaced the old Zowie on the streaming rig.", "decision", "cross", False,
     [("Embarrassment", "emotion"), ("Valorant", "concept"), ("Logitech G Pro X Superlight", "tool"), ("Zowie", "tool")],
     [("Logitech G Pro X Superlight", "Zowie", "REPLACES")],
     "what hardware swap helped climb back in the tactical shooter ranks",
     "tactical shooter rank recovery mouse upgrade emotion hardware"),
    # --- 50 ---
    ("The Sunday Tabletop Simulator D&D night adopted a shared Foundry VTT calendar on 2026-01-18 after Sasha grew tired of Doodle polls.", "milestone", "cross", False,
     [("Tabletop Simulator", "tool"), ("D&D", "hobby"), ("Foundry VTT", "tool"), ("2026-01-18", "date"), ("Sasha", "person"), ("Doodle", "service")],
     [("Foundry VTT", "Doodle", "REPLACES")],
     "when did the tabletop group stop using scheduling polls for the weekly session",
     "tabletop scheduling migration calendar poll retirement session cadence"),
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
