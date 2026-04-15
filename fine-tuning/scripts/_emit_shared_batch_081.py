"""One-off emitter for shared-base batch-081 — cross domain.

Slice: gaming meets tech (consumer hobby crossing software/hardware). Writes
50 rows to data/v2/shared/batch_081.tmp.jsonl with ids shared-04001..04050. The
main session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_081.tmp.jsonl"
ID_OFFSET = 4000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Steam Deck replaced the gaming laptop on 2026-02-11 once Elden Ring ran better at 40 fps on the OLED than the RTX 3060 mobile chip ever managed thermally throttled.", "decision", "cross", False,
     [("Steam Deck", "infrastructure"), ("2026-02-11", "date"), ("Elden Ring", "project"), ("OLED", "infrastructure"), ("RTX 3060", "infrastructure")],
     [("Steam Deck", "RTX 3060", "REPLACES")],
     "when did the handheld take over from the gaming laptop and why",
     "handheld replacement thermal throttle frame rate cap OLED screen"),
    # --- 2 ---
    ("Proton GE replaced the dual-boot Windows partition for almost everything except Destiny 2 because the BattlEye anti-cheat still kicks Linux sessions out of crucible matches.", "decision", "cross", False,
     [("Proton GE", "tool"), ("Windows", "platform"), ("Destiny 2", "project"), ("BattlEye", "service"), ("Linux", "platform")],
     [("Proton GE", "Windows", "REPLACES")],
     "what got rid of the Windows dual boot and what is still holding it back",
     "compatibility layer anti cheat kernel level dual boot retirement"),
    # --- 3 ---
    ("Prefers the 8BitDo Ultimate over the Xbox Elite Series 2 controller because the Hall-effect sticks haven't drifted after a year of Hades II runs and the dongle works on the Steam Deck dock.", "preference", "cross", False,
     [("8BitDo Ultimate", "infrastructure"), ("Xbox Elite Series 2", "infrastructure"), ("Hades II", "project"), ("Steam Deck", "infrastructure")],
     [("8BitDo Ultimate", "Xbox Elite Series 2", "PREFERS")],
     "which controller wins for the handheld dock setup and what made the difference",
     "hall effect sticks drift dongle compatibility roguelike controller"),
    # --- 4 ---
    ("EmuDeck improves on bare RetroArch because the per-system shader presets and the Steam ROM Manager scrape land Saturn and Dreamcast titles in the SteamOS library without a manual pcsx2.ini edit.", "architecture", "cross", False,
     [("EmuDeck", "tool"), ("RetroArch", "tool"), ("Steam ROM Manager", "tool"), ("Saturn", "platform"), ("Dreamcast", "platform"), ("SteamOS", "platform")],
     [("EmuDeck", "RetroArch", "IMPROVES_ON"), ("EmuDeck", "Steam ROM Manager", "USES")],
     "how does the emulation stack actually surface obscure consoles in the handheld library",
     "emulation frontend shader preset scraper console library handheld"),
    # --- 5 ---
    ("The 2026-03-22 Discord server migration moved the Tuesday Helldivers 2 squad off the old college server because Lowtax kept pinging everyone with Soundboard memes during operations.", "milestone", "cross", False,
     [("2026-03-22", "date"), ("Discord", "service"), ("Helldivers 2", "project"), ("Lowtax", "person"), ("Soundboard", "tool")],
     [("Lowtax", "Discord", "USES")],
     "when did the squad leave the old discord and who pushed the move",
     "discord server migration squad nightly play soundboard ping spam"),
    # --- 6. noise ---
    ("Hold on, let me pull that up.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Stardew Valley Expanded plus the SMAPI mod loader replaced vanilla Stardew on the 2026-04-01 farm restart because the Ridgeside Village content adds a full second year of NPCs.", "decision", "cross", False,
     [("Stardew Valley Expanded", "project"), ("SMAPI", "framework"), ("Stardew", "project"), ("2026-04-01", "date"), ("Ridgeside Village", "project")],
     [("Stardew Valley Expanded", "Stardew", "REPLACES"), ("Stardew Valley Expanded", "SMAPI", "DEPENDS_ON")],
     "what overhaul mod took over the new Stardew save and why it was worth it",
     "mod overhaul farming sim mod loader content expansion second year"),
    # --- 8 ---
    ("The RTX 4070 Super upgrade landed on 2026-01-19 because Cyberpunk 2077 with path tracing on at 1440p was hitching on the old 3060 Ti even with DLSS Performance.", "milestone", "cross", False,
     [("RTX 4070 Super", "infrastructure"), ("2026-01-19", "date"), ("Cyberpunk 2077", "project"), ("3060 Ti", "infrastructure"), ("DLSS", "technology")],
     [("RTX 4070 Super", "3060 Ti", "REPLACES")],
     "when did the GPU upgrade happen and which game forced the issue",
     "gpu upgrade path tracing upscaler hitching frame time replacement"),
    # --- 9 ---
    ("Prefers Playnite over the Steam, Epic, GOG and Battle.net launchers separately because the unified library plus the HowLongToBeat plugin actually surfaces the 30-hour backlog candidates.", "preference", "cross", False,
     [("Playnite", "tool"), ("Steam", "platform"), ("Epic", "platform"), ("GOG", "platform"), ("Battle.net", "platform"), ("HowLongToBeat", "service")],
     [("Playnite", "Steam", "REPLACES"), ("Playnite", "HowLongToBeat", "USES")],
     "which library manager won the multi store backlog problem and how",
     "unified library launcher backlog filter plugin completion time"),
    # --- 10 ---
    ("The ROG Ally X stays on the dock for Monster Hunter Wilds while the Steam Deck OLED handles the couch sessions because the Ally's Z1 Extreme actually holds 60 fps in the Plenty hub.", "architecture", "cross", False,
     [("ROG Ally X", "infrastructure"), ("Monster Hunter Wilds", "project"), ("Steam Deck OLED", "infrastructure"), ("Z1 Extreme", "infrastructure"), ("Plenty", "place")],
     [("ROG Ally X", "Z1 Extreme", "USES")],
     "how do the two handhelds split duty between docked and couch play",
     "handheld split docked couch frame rate hub town target performance"),
    # --- 11 ---
    ("Backloggd replaced HLTB as the primary hour-tracking app on 2026-02-28 because the Backloggd review feed actually surfaces what Manny and the rest of the friend group finished that week.", "decision", "cross", False,
     [("Backloggd", "service"), ("HLTB", "service"), ("2026-02-28", "date"), ("Manny", "person")],
     [("Backloggd", "HLTB", "REPLACES")],
     "when did the backlog tracker change and what made the social side worth it",
     "backlog tracker swap social feed friend group reviews completion"),
    # --- 12 ---
    ("Twitch viewing dropped to almost zero after Northernlion moved the daily Isaac runs to YouTube on 2026-03-09 because the YouTube Premium subscription kills the mid-roll that broke immersion.", "fact", "cross", False,
     [("Twitch", "service"), ("Northernlion", "person"), ("Isaac", "project"), ("YouTube", "service"), ("2026-03-09", "date"), ("YouTube Premium", "service")],
     [("Northernlion", "YouTube", "USES")],
     "what shifted the daily watch pattern away from Twitch this spring",
     "streamer platform shift daily series ad free subscription view habit"),
    # --- 13 ---
    ("The PS5 cloud-save sync to PlayStation Plus Premium broke on 2026-02-04 for the Final Fantasy VII Rebirth save because the upload queue silently failed when rest mode dropped Wi-Fi mid push.", "problem", "cross", False,
     [("PS5", "infrastructure"), ("PlayStation Plus Premium", "service"), ("2026-02-04", "date"), ("Final Fantasy VII Rebirth", "project")],
     [("PS5", "PlayStation Plus Premium", "USES")],
     "what went wrong with the cloud save on the PS5 that week",
     "cloud save sync silent failure rest mode wifi drop upload queue"),
    # --- 14 ---
    ("Skyrim Special Edition with Wabbajack's Living Skyrim 4 list replaced the hand-curated Mod Organizer 2 setup on the gaming PC because the Wabbajack install survived the 2026-03 Bethesda script-extender break.", "decision", "cross", False,
     [("Skyrim Special Edition", "project"), ("Wabbajack", "tool"), ("Living Skyrim 4", "project"), ("Mod Organizer 2", "tool"), ("Bethesda", "organization")],
     [("Wabbajack", "Mod Organizer 2", "REPLACES"), ("Living Skyrim 4", "Wabbajack", "DEPENDS_ON")],
     "what mod management approach replaced the manual setup and why",
     "mod list installer curated overhaul script extender break recovery"),
    # --- 15 ---
    ("Prefers the Razer Huntsman V3 Pro over the Logitech G915 because the analog Hall-effect actuation feels right for the Counter-Strike 2 movement keys and the wired latency is just lower.", "preference", "cross", False,
     [("Razer Huntsman V3 Pro", "infrastructure"), ("Logitech G915", "infrastructure"), ("Counter-Strike 2", "project")],
     [("Razer Huntsman V3 Pro", "Logitech G915", "PREFERS")],
     "which keyboard wins for the competitive shooter setup and why",
     "keyboard analog actuation wired latency competitive shooter feel"),
    # --- 16 ---
    ("Frustration spiked when the Switch Online Expansion Pack DLC for Tears of the Kingdom didn't migrate to the new Switch 2 profile and Nintendo support wanted a 14-day ticket window.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Switch Online Expansion Pack", "service"), ("Tears of the Kingdom", "project"), ("Switch 2", "infrastructure"), ("Nintendo", "organization")],
     [],
     "what soured the Switch 2 transfer for the Zelda DLC entitlement",
     "console transfer dlc entitlement loss support ticket waiting period"),
    # --- 17 ---
    ("Sunshine plus Moonlight replaced Steam Link on the living-room TV because Moonlight on the Apple TV 4K finally beats the Steam Link app at HDR pass-through for Alan Wake 2.", "decision", "cross", False,
     [("Sunshine", "tool"), ("Moonlight", "tool"), ("Steam Link", "service"), ("Apple TV 4K", "infrastructure"), ("Alan Wake 2", "project")],
     [("Sunshine", "Steam Link", "REPLACES"), ("Moonlight", "Apple TV 4K", "DEPLOYED_ON")],
     "what game streaming stack took over the living room and what unlocked it",
     "game stream host client HDR pass through living room television"),
    # --- 18 ---
    ("The Diablo IV in-game gold market collapsed on 2026-01-29 when Blizzard's Season 8 patch nuked the Mystic enchant rerolls and the Auction House liquidity dried up overnight.", "fact", "cross", False,
     [("Diablo IV", "project"), ("2026-01-29", "date"), ("Blizzard", "organization"), ("Season 8", "event"), ("Mystic", "concept"), ("Auction House", "concept")],
     [("Season 8", "Diablo IV", "APPLIES_TO")],
     "what tanked the Diablo IV economy at the end of January",
     "in game economy patch reroll cost market liquidity season reset"),
    # --- 19 ---
    ("Pre-ordered the Switch 2 from My Nintendo Store on 2026-04-02 instead of GameStop because the Joy-Con drift warranty defaults to 12 months on the Nintendo direct purchase versus 30 days at GameStop.", "decision", "cross", False,
     [("Switch 2", "infrastructure"), ("My Nintendo Store", "service"), ("2026-04-02", "date"), ("GameStop", "organization"), ("Joy-Con", "infrastructure"), ("Nintendo", "organization")],
     [("My Nintendo Store", "GameStop", "PREFERS")],
     "where did the Switch 2 preorder land and what drove the choice",
     "console preorder warranty length controller defect direct retailer"),
    # --- 20 ---
    ("Curiosity drove the move from Forge to NeoForge on 2026-03-15 for the Minecraft 1.21 modpack because the All The Mods 10 dev branch only ships NeoForge builds going forward.", "milestone", "cross", False,
     [("Curiosity", "emotion"), ("Forge", "framework"), ("NeoForge", "framework"), ("2026-03-15", "date"), ("Minecraft", "project"), ("All The Mods 10", "project")],
     [("NeoForge", "Forge", "REPLACES"), ("All The Mods 10", "NeoForge", "DEPENDS_ON")],
     "when did the Minecraft mod loader change and what forced it",
     "mod loader fork migration modpack dev branch upstream commitment"),
    # --- 21 ---
    ("The Logitech G Pro Superlight 2 stayed but the MX Master mouse moved to the work laptop because Valorant's flick aim actually feels different on the lighter sensor across desk surfaces.", "architecture", "cross", False,
     [("Logitech G Pro Superlight 2", "infrastructure"), ("MX Master", "infrastructure"), ("Valorant", "project")],
     [("Logitech G Pro Superlight 2", "MX Master", "PREFERS")],
     "how did the gaming and work mice get split across the two machines",
     "mouse split competitive aim sensor weight desk surface routine"),
    # --- 22 ---
    ("RetroAchievements integrated with EmuDeck means the Pokémon Emerald replay on the Steam Deck on 2026-03-30 actually counts hours and milestones the way modern Steam profiles do.", "architecture", "cross", False,
     [("RetroAchievements", "service"), ("EmuDeck", "tool"), ("Pokémon Emerald", "project"), ("Steam Deck", "infrastructure"), ("2026-03-30", "date"), ("Steam", "platform")],
     [("RetroAchievements", "EmuDeck", "USES")],
     "how do the retro replays earn achievements that match the modern Steam profile feel",
     "retro achievement tracker emulation integration milestone replay"),
    # --- 23 ---
    ("Joy hit when the friend group's Foundry VTT campaign on 2026-04-05 finally got the Pathfinder 2e module to render the Maps with proper line-of-sight after the Levels module update.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Foundry VTT", "tool"), ("2026-04-05", "date"), ("Pathfinder 2e", "project"), ("Levels", "library")],
     [("Pathfinder 2e", "Foundry VTT", "DEPLOYED_ON")],
     "when did the virtual tabletop campaign finally get line of sight working",
     "virtual tabletop module update line of sight tactical map render"),
    # --- 24 ---
    ("Twitch chat ban from the LIRIK channel on 2026-02-19 was actually triggered by 7TV emote spam from a stale browser tab in the background, not anything I typed.", "problem", "cross", False,
     [("Twitch", "service"), ("LIRIK", "person"), ("2026-02-19", "date"), ("7TV", "tool")],
     [("7TV", "Twitch", "EXTENDS")],
     "what actually caused the chat ban in the variety channel that week",
     "chat ban third party emote extension stale tab background spam"),
    # --- 25 ---
    ("Prefers the Series X over the PS5 for Game Pass Day One drops because Starfield, Forza Motorsport and the Activision back catalog all stream at 1440p over xCloud to the Steam Deck.", "preference", "cross", False,
     [("Series X", "infrastructure"), ("PS5", "infrastructure"), ("Game Pass", "service"), ("Starfield", "project"), ("Forza Motorsport", "project"), ("xCloud", "service")],
     [("Series X", "PS5", "PREFERS"), ("Game Pass", "xCloud", "USES")],
     "which console wins for the subscription day one library and why",
     "subscription day one cloud streaming back catalog handheld access"),
    # --- 26 ---
    ("The Apex Legends ranked grind ended on 2026-01-15 once the Diamond promotion got matched against three-stack Predators using Aim Labs warmup routines that solo queue couldn't keep up with.", "milestone", "cross", False,
     [("Apex Legends", "project"), ("2026-01-15", "date"), ("Diamond", "concept"), ("Predators", "concept"), ("Aim Labs", "tool")],
     [("Aim Labs", "Apex Legends", "APPLIES_TO")],
     "when did the competitive grind on Apex actually end and what broke it",
     "ranked grind pred lobbies solo queue aim trainer mismatch quit"),
    # --- 27 ---
    ("ProtonDB plus the Glorious Eggroll release notes are the reference reading whenever a new Steam game gets added to the wishlist and Linux compatibility is a question mark.", "reference", "cross", False,
     [("ProtonDB", "service"), ("Glorious Eggroll", "person"), ("Steam", "platform"), ("Linux", "platform")],
     [("ProtonDB", "Linux", "APPLIES_TO")],
     "where do the compatibility checks come from before adding a Linux purchase",
     "compatibility database release notes wishlist vetting linux gaming"),
    # --- 28 ---
    ("Frustration set in when the Helldivers 2 Steam achievement for Super Earth Citizen unlocked but Backloggd's Steam scraper kept missing it for three days because of the GetPlayerAchievements rate limit.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Helldivers 2", "project"), ("Steam", "platform"), ("Super Earth Citizen", "concept"), ("Backloggd", "service"), ("GetPlayerAchievements", "api")],
     [("Backloggd", "GetPlayerAchievements", "USES")],
     "what blocked the achievement showing up in the tracker that week",
     "achievement tracker scraper rate limit propagation delay missing"),
    # --- 29 ---
    ("The Anbernic RG556 stayed in the drawer once the Steam Deck OLED took over because EmuDeck on the Deck actually saves cloud progress through Syncthing back to the NAS.", "decision", "cross", False,
     [("Anbernic RG556", "infrastructure"), ("Steam Deck OLED", "infrastructure"), ("EmuDeck", "tool"), ("Syncthing", "tool"), ("NAS", "infrastructure")],
     [("Steam Deck OLED", "Anbernic RG556", "REPLACES"), ("EmuDeck", "Syncthing", "USES")],
     "why did the Anbernic handheld get retired in favor of the Deck",
     "android handheld retirement save sync nas backup emulation"),
    # --- 30 ---
    ("The 2026-04-08 Path of Exile 2 league launch crushed the in-game Currency Exchange because Ruthless mode poured Divine Orbs into the market faster than awakeners could vendor them.", "fact", "cross", False,
     [("2026-04-08", "date"), ("Path of Exile 2", "project"), ("Currency Exchange", "concept"), ("Ruthless", "concept"), ("Divine Orbs", "concept")],
     [("Ruthless", "Path of Exile 2", "APPLIES_TO")],
     "what shocked the league economy at the April PoE2 launch",
     "arpg league launch currency market sink supply imbalance trade"),
    # --- 31 ---
    ("Prefers the Bambu Lab P1S printed Gloomhaven organizer over the Broken Token wood kit because the PETG dividers actually survive a Switch travel-bag toss without cracking.", "preference", "cross", False,
     [("Bambu Lab P1S", "infrastructure"), ("Gloomhaven", "project"), ("Broken Token", "organization"), ("PETG", "concept"), ("Switch", "infrastructure")],
     [("Bambu Lab P1S", "Broken Token", "PREFERS")],
     "which board game organizer won and what made the printed one tougher",
     "board game insert print versus wood durability travel bag hobby"),
    # --- 32 ---
    ("The HotS friend group on Discord migrated to a Mumble server on 2026-02-25 because the spatial audio plugin worked for the Squad nights and Discord still doesn't have positional voice.", "decision", "cross", False,
     [("HotS", "project"), ("Discord", "service"), ("Mumble", "service"), ("2026-02-25", "date"), ("Squad", "project")],
     [("Mumble", "Discord", "REPLACES")],
     "why did the squad voice chat leave Discord and what tipped the move",
     "voice chat migration positional audio milsim squad room plugin"),
    # --- 33 ---
    ("Stardew Multiplayer save with Mei broke on 2026-03-12 after the SVE update because the SpaceCore dependency mismatch corrupted the farmhand's inventory and SMAPI logged the trace cleanly enough to roll back.", "problem", "cross", False,
     [("Stardew", "project"), ("Mei", "person"), ("2026-03-12", "date"), ("SVE", "project"), ("SpaceCore", "library"), ("SMAPI", "framework")],
     [("SVE", "SpaceCore", "DEPENDS_ON"), ("SMAPI", "SVE", "USES")],
     "what corrupted the co op farm save in March and how was it caught",
     "multiplayer save corruption mod dependency mismatch log rollback"),
    # --- 34. noise ---
    ("Yeah, that one is a tough call.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Razer Kishi V2 replaced the Backbone One on the iPhone 15 Pro because the Kishi's USB-C pass-through actually keeps the phone charging during a two-hour Genshin Impact Spiral Abyss run.", "decision", "cross", False,
     [("Razer Kishi V2", "infrastructure"), ("Backbone One", "infrastructure"), ("iPhone 15 Pro", "infrastructure"), ("Genshin Impact", "project"), ("Spiral Abyss", "concept")],
     [("Razer Kishi V2", "Backbone One", "REPLACES")],
     "what mobile controller took over from the Backbone and why",
     "mobile controller swap pass through charge long session gacha"),
    # --- 36 ---
    ("ShadowPlay's instant-replay buffer caught the 2026-04-09 Marvel Rivals clutch ace by Kai because the Nvidia App finally lets the buffer keep 5 minutes at 1440p without thrashing the SSD.", "milestone", "cross", False,
     [("ShadowPlay", "tool"), ("2026-04-09", "date"), ("Marvel Rivals", "project"), ("Kai", "person"), ("Nvidia App", "tool"), ("SSD", "infrastructure")],
     [("ShadowPlay", "Nvidia App", "DEPLOYED_ON")],
     "what captured the friend group's clutch moment that night and what made it possible",
     "instant replay buffer capture friend clutch ssd headroom recording"),
    # --- 37 ---
    ("Prefers Lutris over Bottles for non-Steam Windows games on the Linux desktop because the Lutris install scripts handle the Battle.net launcher tutorial dance automatically.", "preference", "cross", False,
     [("Lutris", "tool"), ("Bottles", "tool"), ("Steam", "platform"), ("Windows", "platform"), ("Linux", "platform"), ("Battle.net", "platform")],
     [("Lutris", "Bottles", "PREFERS")],
     "which Wine launcher wins for non-Steam windows games on the Linux box",
     "wine launcher install script third party launcher automation"),
    # --- 38 ---
    ("The Final Fantasy XIV free trial WoL Maya is up to Endwalker on 2026-03-26 because the new Dawntrail subscription started and the Mare Synchronos plugin finally rendered Eorzea Collection mods correctly.", "milestone", "cross", False,
     [("Final Fantasy XIV", "project"), ("Maya", "person"), ("Endwalker", "event"), ("2026-03-26", "date"), ("Dawntrail", "event"), ("Mare Synchronos", "library"), ("Eorzea Collection", "service")],
     [("Mare Synchronos", "Eorzea Collection", "USES")],
     "where is the FFXIV character at and what plugin work paid off",
     "mmo expansion progression mod sync collection plugin completion"),
    # --- 39 ---
    ("Steam Family Sharing replaced the second Steam account on 2026-03-01 once Valve let library splits work per-game and the Baldur's Gate 3 co-op save survived the Mei handoff cleanly.", "decision", "cross", False,
     [("Steam Family Sharing", "service"), ("Steam", "platform"), ("2026-03-01", "date"), ("Valve", "organization"), ("Baldur's Gate 3", "project"), ("Mei", "person")],
     [("Steam Family Sharing", "Steam", "REPLACES")],
     "what replaced the duplicate steam account setup and what proved it worked",
     "library sharing per game split co op save handoff family group"),
    # --- 40 ---
    ("Confusion erupted when Pokemon Sleep on the Pixel 9 stopped syncing with the Pokemon GO Plus+ on 2026-02-08 because the Niantic Kit firmware update bricked the Bluetooth handoff.", "problem", "cross", False,
     [("Confusion", "emotion"), ("Pokemon Sleep", "project"), ("Pixel 9", "infrastructure"), ("Pokemon GO Plus+", "infrastructure"), ("2026-02-08", "date"), ("Niantic Kit", "framework"), ("Bluetooth", "protocol")],
     [("Niantic Kit", "Bluetooth", "USES")],
     "what broke the sleep tracker integration with the Pokemon device",
     "wearable firmware update bluetooth pairing break tracker sync"),
    # --- 41 ---
    ("HowLongToBeat says Persona 5 Royal is 103 hours but the Backloggd time-played pulled from PSN for the 2026-03-18 platinum trophy run actually came in at 117 hours.", "fact", "cross", False,
     [("HowLongToBeat", "service"), ("Persona 5 Royal", "project"), ("Backloggd", "service"), ("PSN", "service"), ("2026-03-18", "date")],
     [("Backloggd", "PSN", "USES")],
     "how off was the HLTB estimate for Persona 5 Royal versus the actual save",
     "completion estimate accuracy platinum trophy actual hours discrepancy"),
    # --- 42 ---
    ("Joy washed in when the Tetris Effect Connected weekend on the PSVR2 with Mei on 2026-04-12 hit the journey ending and the haptic floor feedback synced with the Headphones X audio cleanly.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Tetris Effect Connected", "project"), ("PSVR2", "infrastructure"), ("Mei", "person"), ("2026-04-12", "date"), ("Headphones X", "technology")],
     [("Tetris Effect Connected", "PSVR2", "DEPLOYED_ON")],
     "when did the VR Tetris session land and what made the audio sync work",
     "vr rhythm puzzle haptic feedback spatial audio shared session"),
    # --- 43 ---
    ("The CRT Royale shader replaced the simple-scanlines preset in RetroArch for the Sega Genesis library because Sonic 3 sprites finally look right with the dot-mask phosphor simulation.", "decision", "cross", False,
     [("CRT Royale", "tool"), ("RetroArch", "tool"), ("Sega Genesis", "platform"), ("Sonic 3", "project")],
     [("CRT Royale", "RetroArch", "EXTENDS")],
     "what shader took over the genesis emulation and why it was worth the GPU cost",
     "emulation shader phosphor dot mask sprite rendering nostalgia"),
    # --- 44 ---
    ("Prefers PCSX2's Vulkan backend over the OpenGL one for Persona 4 because the upscaling artifacts on the velvet room background go away and the Steam Deck holds 60 fps without a thermal kick.", "preference", "cross", False,
     [("PCSX2", "tool"), ("Vulkan", "api"), ("OpenGL", "api"), ("Persona 4", "project"), ("Steam Deck", "infrastructure")],
     [("PCSX2", "Vulkan", "PREFERS"), ("Vulkan", "OpenGL", "REPLACES")],
     "which PCSX2 renderer wins on the Deck and what game proved it",
     "ps2 emulator backend upscaling artifact handheld thermal stability"),
    # --- 45 ---
    ("The 2026-04-13 Twitch Drops campaign for Once Human required watching forsen for two hours but uBlock Origin's pre-roll ad block kept the drop counter ticking on the Firefox tab.", "fact", "cross", False,
     [("2026-04-13", "date"), ("Twitch Drops", "service"), ("Once Human", "project"), ("forsen", "person"), ("uBlock Origin", "tool"), ("Firefox", "tool")],
     [("uBlock Origin", "Twitch Drops", "USES")],
     "how did the Twitch Drop count tick without watching the ads",
     "drops campaign streamer watch ad block extension counter tick"),
    # --- 46 ---
    ("Disappointment set in when the Logitech G Cloud handheld got shelved because xCloud streaming for Hellblade 2 on hotel Wi-Fi maxed out at 720p with constant macroblocking.", "problem", "cross", False,
     [("Disappointment", "emotion"), ("Logitech G Cloud", "infrastructure"), ("xCloud", "service"), ("Hellblade 2", "project")],
     [("Logitech G Cloud", "xCloud", "USES")],
     "why did the cloud handheld get shelved after the travel test",
     "cloud handheld shelved hotel wifi bitrate macroblocking quality"),
    # --- 47 ---
    ("The R6 Siege Operation Battle Pass got skipped on 2026-03-04 because the friend group voted to switch the Tuesday rotation to The Finals and Embark's Season 5 Sponsor system was actually grindable.", "decision", "cross", False,
     [("R6 Siege", "project"), ("Operation Battle Pass", "concept"), ("2026-03-04", "date"), ("The Finals", "project"), ("Embark", "organization"), ("Season 5", "event")],
     [("The Finals", "R6 Siege", "REPLACES")],
     "what game took over the Tuesday squad night and what made the swap stick",
     "battle pass skip friend group rotation seasonal grind sponsor"),
    # --- 48 ---
    ("Plex replaced Stremio for the Saturday game-night background TV because the Plex DVR with the HDHomeRun finally records the Frost Giant StarCraft 2 weekend tournaments without buffering.", "decision", "cross", False,
     [("Plex", "tool"), ("Stremio", "tool"), ("HDHomeRun", "infrastructure"), ("Frost Giant", "organization"), ("StarCraft 2", "project")],
     [("Plex", "Stremio", "REPLACES"), ("Plex", "HDHomeRun", "USES")],
     "what handled the esports background stream on game nights now",
     "tuner dvr esports tournament background broadcast buffer free"),
    # --- 49 ---
    ("The DexerTo article from 2026-04-07 about the Marvel Rivals competitive ban wave is the reference because it actually names the Cheat Engine signature the EasyAntiCheat update started flagging.", "reference", "cross", False,
     [("DexerTo", "publication"), ("2026-04-07", "date"), ("Marvel Rivals", "project"), ("Cheat Engine", "tool"), ("EasyAntiCheat", "service")],
     [("EasyAntiCheat", "Cheat Engine", "FIXES")],
     "where is the writeup on the Marvel Rivals ban wave that names the actual signature",
     "competitive ban wave anti cheat signature article reference"),
    # --- 50 ---
    ("Pride landed when the speedrun.com submission for the Celeste any% on 2026-04-11 verified at 28:14 because the LiveSplit AutoSplitter routed the timer through the SteamOS gamemode without dropping a frame.", "milestone", "cross", False,
     [("Pride", "emotion"), ("speedrun.com", "service"), ("Celeste", "project"), ("2026-04-11", "date"), ("LiveSplit", "tool"), ("SteamOS", "platform")],
     [("LiveSplit", "SteamOS", "DEPLOYED_ON")],
     "when did the Celeste any% submission verify and what kept the timer honest",
     "speedrun submission verification autosplitter handheld gamemode"),
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
