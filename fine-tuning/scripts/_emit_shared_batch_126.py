"""One-off emitter for shared-base batch-126 — cross domain.

Slice: streaming and home-theater meets tech (media server/streamer software,
hardware transcoding, HDR/Atmos, remotes, subtitles). Writes 50 rows to
data/v2/shared/batch_126.tmp.jsonl with ids shared-06251..06300. The main
session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_126.tmp.jsonl"
ID_OFFSET = 6250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the living-room library from Plex to Jellyfin on 2026-02-11 after the Plex Pass lifetime deal jumped again and the remote-watch telemetry finally pushed Mei over the edge.", "decision", "cross", False,
     [("Plex", "service"), ("Jellyfin", "service"), ("2026-02-11", "date"), ("Plex Pass", "service"), ("Mei", "person")],
     [("Jellyfin", "Plex", "REPLACES")],
     "when did the family media server swap off of Plex and what triggered it",
     "media server migration lifetime pass price telemetry privacy complaint"),
    # --- 2 ---
    ("Infuse on the Apple TV 4K replaced the stock tvOS Jellyfin client because the Dolby Vision passthrough finally pipes through Infuse without the washed-out color the Jellyfin client was producing.", "decision", "cross", False,
     [("Infuse", "service"), ("Apple TV 4K", "infrastructure"), ("tvOS", "infrastructure"), ("Jellyfin", "service"), ("Dolby Vision", "concept")],
     [("Infuse", "Jellyfin", "IMPROVES_ON"), ("Infuse", "Apple TV 4K", "DEPLOYED_ON")],
     "which front-end won on the Apple TV for HDR playback and why",
     "dolby vision passthrough client player washed colors tvos front end"),
    # --- 3 ---
    ("The Intel N100 mini-PC running Jellyfin handles three simultaneous 4K HEVC transcodes over QuickSync without the fan spinning up above 35C in the media closet.", "architecture", "cross", False,
     [("Intel N100", "infrastructure"), ("Jellyfin", "service"), ("HEVC", "concept"), ("QuickSync", "concept")],
     [("Jellyfin", "QuickSync", "USES"), ("Jellyfin", "Intel N100", "DEPLOYED_ON")],
     "what hardware actually carries the 4K transcoding for the house",
     "mini pc quicksync hardware transcode hevc thermal headroom media closet"),
    # --- 4 ---
    ("Sonarr v4 replaced Sonarr v3 on 2026-01-18 after the v4 custom-format scoring finally treated the Framestor WEB-DL group as higher priority than random REMUX rips for the anime library.", "milestone", "cross", False,
     [("Sonarr v4", "service"), ("Sonarr v3", "service"), ("2026-01-18", "date"), ("Framestor", "organization"), ("WEB-DL", "concept"), ("REMUX", "concept")],
     [("Sonarr v4", "Sonarr v3", "REPLACES")],
     "when did the TV grabber upgrade and what quality ranking finally behaved",
     "sonarr version upgrade custom format score release group priority anime"),
    # --- 5 ---
    ("Bazarr replaced the manual OpenSubtitles habit for the whole Radarr library once the Mei-only Spanish track auto-download rule stopped missing the Almodóvar catalog.", "decision", "cross", False,
     [("Bazarr", "service"), ("OpenSubtitles", "service"), ("Radarr", "service"), ("Mei", "person"), ("Spanish", "language"), ("Almodóvar", "person")],
     [("Bazarr", "OpenSubtitles", "REPLACES"), ("Bazarr", "Radarr", "COMMUNICATES_WITH")],
     "how did subtitle management stop being a manual chore for the movie library",
     "subtitle automation secondary language download rule auteur catalog"),
    # --- 6. noise ---
    ("Hold on, pulling up the playback log now.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("qBittorrent on Debian replaced Deluge after the Deluge 2.x WebUI kept dropping the session between the Sonarr and the VPN-gateway container restarts.", "decision", "cross", False,
     [("qBittorrent", "service"), ("Debian", "infrastructure"), ("Deluge", "service"), ("Sonarr", "service"), ("VPN", "concept")],
     [("qBittorrent", "Deluge", "REPLACES")],
     "which download client took over after the WebUI flakiness got old",
     "torrent client swap webui session drop vpn gateway container restart"),
    # --- 8 ---
    ("Usenet through Newshosting plus NZBGeek indexer replaced the public-tracker workflow on 2025-12-04 because the 3000-day retention finally covered the BBC Planet Earth re-rip backfill.", "milestone", "cross", False,
     [("Newshosting", "service"), ("NZBGeek", "service"), ("2025-12-04", "date"), ("BBC", "organization"), ("Planet Earth", "publication")],
     [("Newshosting", "NZBGeek", "COMMUNICATES_WITH")],
     "when did the library move from public trackers to Usenet and what pushed it",
     "usenet provider retention indexer public tracker swap nature documentary"),
    # --- 9 ---
    ("Netflix's top nav keeps being the first thing to open on the LG C2, so Kodi lives one Harmony button deep because the Night-In activity maps the orange button to Kodi directly.", "architecture", "cross", False,
     [("Netflix", "service"), ("LG C2", "infrastructure"), ("Kodi", "service"), ("Harmony", "tool")],
     [("Harmony", "Kodi", "COMMUNICATES_WITH")],
     "how does the remote actually get to the self-hosted library without menu digging",
     "activity based remote custom button mapping oled tv streaming launch"),
    # --- 10 ---
    ("Apple TV+ and Disney+ sit on the Apple TV 4K because the tvOS apps do Dolby Atmos passthrough to the Denon AVR-X3800H cleanly, which the Chromecast with Google TV couldn't manage last year.", "architecture", "cross", False,
     [("Apple TV+", "service"), ("Disney+", "service"), ("Apple TV 4K", "infrastructure"), ("tvOS", "infrastructure"), ("Dolby Atmos", "concept"), ("Denon AVR-X3800H", "infrastructure"), ("Chromecast with Google TV", "infrastructure")],
     [("Apple TV+", "Apple TV 4K", "DEPLOYED_ON"), ("Apple TV 4K", "Chromecast with Google TV", "PREFERS")],
     "which streamer hardware carries the premium streaming apps and why",
     "atmos passthrough avr streamer puck hardware choice ecosystem app"),
    # --- 11 ---
    ("Prefers Prime Video on the Fire TV Cube over the same app on the LG C2 because the Cube's eARC pipe keeps the Atmos flag alive through the soundbar switch.", "preference", "cross", False,
     [("Prime Video", "service"), ("Fire TV Cube", "infrastructure"), ("LG C2", "infrastructure"), ("eARC", "protocol"), ("Atmos", "concept")],
     [("Fire TV Cube", "LG C2", "PREFERS")],
     "which device runs Prime Video in the living room and what audio chain reason wins",
     "earc atmos flag preservation streamer puck app device pairing"),
    # --- 12 ---
    ("Max replaced HBO Max on the Roku Ultra on 2026-03-01 but the profile migration wiped the kids' Continue Watching list for Bluey, which sent Mei into a 45-minute recovery spiral.", "problem", "cross", False,
     [("Max", "service"), ("HBO Max", "service"), ("Roku Ultra", "infrastructure"), ("2026-03-01", "date"), ("Bluey", "publication"), ("Mei", "person")],
     [("Max", "HBO Max", "REPLACES")],
     "what went sideways on the HBO-to-Max rebrand for the kids' profile",
     "rebrand app swap continue watching loss kid profile recovery"),
    # --- 13 ---
    ("Crunchyroll replaced the self-hosted anime shares on the Chromecast because Noa prefers simulcast subs the day of release and the seasonal backfill stopped being worth the seedbox cost.", "decision", "cross", False,
     [("Crunchyroll", "service"), ("Chromecast", "infrastructure"), ("Noa", "person")],
     [("Crunchyroll", "Chromecast", "DEPLOYED_ON")],
     "why did anime streaming move to Crunchyroll for Noa",
     "simulcast anime subscription kid preference seedbox cost trade off"),
    # --- 14 ---
    ("Radarr v5 with the TRaSH Guides custom formats finally stopped grabbing Dolby Vision Profile 7 files that the Apple TV couldn't decode, after six months of the library being a mess.", "milestone", "cross", False,
     [("Radarr v5", "service"), ("TRaSH Guides", "publication"), ("Dolby Vision Profile 7", "concept"), ("Apple TV", "infrastructure")],
     [("Radarr v5", "TRaSH Guides", "USES")],
     "when did the movie grabber stop pulling incompatible HDR profiles",
     "custom format profile 7 dual layer hdr compatibility tv box decode"),
    # --- 15 ---
    ("Prefers hardware transcoding on the Intel Arc A380 over the old nVidia P400 because the QuickSync AV1 decode lane finally lets the 4K YouTube rips stream to the Pixel Tablet without a software fallback.", "preference", "cross", False,
     [("Intel Arc A380", "infrastructure"), ("nVidia P400", "infrastructure"), ("QuickSync", "concept"), ("AV1", "concept"), ("YouTube", "service"), ("Pixel Tablet", "infrastructure")],
     [("Intel Arc A380", "nVidia P400", "REPLACES"), ("Intel Arc A380", "QuickSync", "USES")],
     "which GPU now does the server-side transcoding and what codec support tipped it",
     "arc gpu quicksync av1 decode transcode low profile media server"),
    # --- 16 ---
    ("The LG C2's Filmmaker Mode replaced the Cinema HDR preset on 2026-02-05 after Vincent Teoh's calibration walkthrough showed the gamma tracking was actually closer to spec out of the box.", "decision", "cross", False,
     [("LG C2", "infrastructure"), ("Filmmaker Mode", "concept"), ("Cinema HDR", "concept"), ("2026-02-05", "date"), ("Vincent Teoh", "person")],
     [("Filmmaker Mode", "Cinema HDR", "REPLACES")],
     "when did the TV picture preset change and who convinced you",
     "filmmaker mode calibration gamma tracking hdr preset oled review"),
    # --- 17 ---
    ("Atmos layout moved to 5.1.4 on 2025-11-19 when the two extra Klipsch RP-500SA ceiling-bounce modules got mounted on the rear surrounds behind the couch.", "milestone", "cross", False,
     [("2025-11-19", "date"), ("Klipsch RP-500SA", "infrastructure")],
     [],
     "when did the surround layout add the extra ceiling-bounce height channels",
     "atmos layout upgrade height speaker ceiling bounce module rear surround"),
    # --- 18 ---
    ("Prefers the SwitchBot Hub 2 over the Harmony Elite for the Atmos-activity macro because Logitech shutting down Harmony's cloud broke half the Prime Video device-command routines last winter.", "preference", "cross", False,
     [("SwitchBot Hub 2", "tool"), ("Harmony Elite", "tool"), ("Atmos", "concept"), ("Logitech", "organization"), ("Harmony", "tool"), ("Prime Video", "service")],
     [("SwitchBot Hub 2", "Harmony Elite", "REPLACES")],
     "which universal remote controls the home theater now and what killed the old one",
     "universal remote replacement cloud shutdown activity macro atmos scene"),
    # --- 19 ---
    ("The Nvidia Shield TV Pro still wins for Kodi because the Tegra's HD audio bitstreaming keeps DTS-HD MA tracks intact and the Jellyfin for Kodi add-on treats it like a thin client.", "architecture", "cross", False,
     [("Nvidia Shield TV Pro", "infrastructure"), ("Kodi", "service"), ("Tegra", "infrastructure"), ("DTS-HD MA", "concept"), ("Jellyfin", "service")],
     [("Kodi", "Nvidia Shield TV Pro", "DEPLOYED_ON"), ("Kodi", "Jellyfin", "USES")],
     "which box runs Kodi for lossless audio in the theater room",
     "shield tegra bitstream lossless audio kodi jellyfin thin client"),
    # --- 20 ---
    ("Excitement spiked the first time the 2026-03-22 Dune Part Two 4K UHD disc hit Plex Bitrate via MakeMKV and the Denon locked the Atmos flag without a single audio dropout all night.", "milestone", "cross", False,
     [("Excitement", "emotion"), ("2026-03-22", "date"), ("Dune Part Two", "publication"), ("Plex", "service"), ("MakeMKV", "tool"), ("Denon", "organization"), ("Atmos", "concept")],
     [("MakeMKV", "Plex", "COMMUNICATES_WITH")],
     "when did the Dune Part Two rip finally play cleanly in the theater",
     "uhd rip makemkv atmos flag avr lock playback dropout sci fi film"),
    # --- 21 ---
    ("Readarr finally replaced the Calibre auto-add folder because the Fable Aeterna audiobook feed from MyAnonamouse lands straight into the Audiobookshelf library now without a manual move.", "architecture", "cross", False,
     [("Readarr", "service"), ("Calibre", "tool"), ("Fable Aeterna", "publication"), ("MyAnonamouse", "service"), ("Audiobookshelf", "service")],
     [("Readarr", "Calibre", "REPLACES"), ("Readarr", "Audiobookshelf", "COMMUNICATES_WITH")],
     "how do audiobooks reach the library now without touching Calibre",
     "audiobook automation grabber indexer library import manual move elimination"),
    # --- 22 ---
    ("Plex library sharing with Dad replaced the external-drive Christmas tradition on 2025-12-25 because Plex remote share finally kept the skip-intro data per user on his Roku stick.", "milestone", "cross", False,
     [("Plex", "service"), ("Dad", "person"), ("2025-12-25", "date"), ("Roku", "infrastructure")],
     [("Plex", "Dad", "COMMUNICATES_WITH")],
     "when did Dad's movie library migrate from hard drives to streaming",
     "family library share remote access per user settings skip intro"),
    # --- 23 ---
    ("The Unifi U6 Enterprise access point in the theater replaced the Nest Wifi because the 6 GHz band finally carried the Apple TV 4K's 4K HDR streams without dropping to 1080p SDR under peak evening load.", "decision", "cross", False,
     [("Unifi U6 Enterprise", "infrastructure"), ("Nest Wifi", "infrastructure"), ("Apple TV 4K", "infrastructure")],
     [("Unifi U6 Enterprise", "Nest Wifi", "REPLACES")],
     "why did the theater Wi-Fi upgrade happen and what symptom was it fixing",
     "wifi 6e access point streamer 4k hdr downgrade peak evening bandwidth"),
    # --- 24 ---
    ("Prefers Tautulli notifications over Plex's built-in emails because Tautulli's Pushover integration flags the Dad-remote-plays within ten seconds of playback start.", "preference", "cross", False,
     [("Tautulli", "service"), ("Plex", "service"), ("Pushover", "service"), ("Dad", "person")],
     [("Tautulli", "Plex", "IMPROVES_ON"), ("Tautulli", "Pushover", "USES")],
     "which notification layer catches remote plays and how",
     "tautulli pushover plex notification remote play alert latency"),
    # --- 25 ---
    ("Overseerr plugged into Sonarr and Radarr so Mei can request Ted Lasso episodes from her phone without pinging me, which killed the old WhatsApp request queue from the 2025 holiday stretch.", "architecture", "cross", False,
     [("Overseerr", "service"), ("Sonarr", "service"), ("Radarr", "service"), ("Mei", "person"), ("Ted Lasso", "publication"), ("WhatsApp", "service")],
     [("Overseerr", "Sonarr", "COMMUNICATES_WITH"), ("Overseerr", "Radarr", "COMMUNICATES_WITH"), ("Overseerr", "WhatsApp", "REPLACES")],
     "how does the household actually request new shows now",
     "request portal self service family queue messaging replacement"),
    # --- 26. noise ---
    ("Okay, scrolling through my watchlist now.", "fact", "noise", True, [], [], None, None),
    # --- 27 ---
    ("Annoyance spiked when the Netflix app on the LG C2 dropped to SDR at 24fps every single Sunday until the 2026-03-14 webOS firmware patch finally fixed the HDMI handshake with the Denon AVR-X3800H.", "problem", "cross", False,
     [("Annoyance", "emotion"), ("Netflix", "service"), ("LG C2", "infrastructure"), ("webOS", "infrastructure"), ("2026-03-14", "date"), ("Denon AVR-X3800H", "infrastructure")],
     [],
     "what was wrong with Sunday-night Netflix and when did it finally get patched",
     "hdmi handshake hdr downgrade firmware patch weekly recurring fault"),
    # --- 28 ---
    ("Prowlarr replaced Jackett on 2026-02-27 because managing 14 indexers from one place and syncing them to Sonarr, Radarr, and Readarr all at once was the only way to keep the Torznab URL drift contained.", "decision", "cross", False,
     [("Prowlarr", "service"), ("Jackett", "service"), ("2026-02-27", "date"), ("Sonarr", "service"), ("Radarr", "service"), ("Readarr", "service"), ("Torznab", "protocol")],
     [("Prowlarr", "Jackett", "REPLACES"), ("Prowlarr", "Sonarr", "COMMUNICATES_WITH")],
     "which indexer manager consolidated the *arr stack and why",
     "prowlarr jackett indexer manager torznab url drift arr stack"),
    # --- 29 ---
    ("The 2026-04-02 Criterion Channel trial got canceled before the free period ended because Jellyfin already had the Wes Anderson box-set rip and the browser-only web player on the Roku was a UX mess.", "decision", "cross", False,
     [("2026-04-02", "date"), ("Criterion Channel", "service"), ("Jellyfin", "service"), ("Wes Anderson", "person"), ("Roku", "infrastructure")],
     [],
     "why did the Criterion Channel trial get dropped",
     "streaming trial cancellation native app absence self hosted alternative"),
    # --- 30 ---
    ("Tdarr replaced the manual HandBrake batch queue on the NAS because the node-based distributed encoding finishes a 400-file H.265 re-encode overnight instead of chewing through a week of evenings.", "decision", "cross", False,
     [("Tdarr", "service"), ("HandBrake", "tool"), ("NAS", "infrastructure"), ("H.265", "concept")],
     [("Tdarr", "HandBrake", "REPLACES")],
     "how did the re-encode backlog stop being a weeknight chore",
     "distributed transcode node cluster batch encode library normalization"),
    # --- 31 ---
    ("Prefers the Apple TV 4K's Siri Remote over the Fire TV Cube's Alexa remote for the Mei living-room flow because the Siri Remote's touchpad scrub is the only way the Severance rewatch actually lands on the right shot.", "preference", "cross", False,
     [("Apple TV 4K", "infrastructure"), ("Siri Remote", "infrastructure"), ("Fire TV Cube", "infrastructure"), ("Alexa", "service"), ("Mei", "person"), ("Severance", "publication")],
     [("Siri Remote", "Alexa", "PREFERS")],
     "which streamer remote wins in the living room and why",
     "remote touchpad scrub precise frame rewind streamer hardware choice"),
    # --- 32 ---
    ("The Gluetun-wrapped qBittorrent container lost connection during the 2026-03-08 ProtonVPN port-forwarding change and silently stalled for two days until Tautulli's zero-grab alert finally fired.", "problem", "cross", False,
     [("Gluetun", "service"), ("qBittorrent", "service"), ("2026-03-08", "date"), ("ProtonVPN", "service"), ("Tautulli", "service")],
     [("qBittorrent", "Gluetun", "DEPLOYED_ON"), ("qBittorrent", "ProtonVPN", "USES")],
     "what caught the two-day download stall in early March",
     "vpn container port forward break zero grab alert delay diagnosis"),
    # --- 33 ---
    ("Audyssey MultEQ on the Denon AVR-X3800H got replaced by Dirac Live after the 2026-04-01 subscription unlock because the sub-bass correction below 40 Hz finally stopped booming out of the corner kick drum.", "decision", "cross", False,
     [("Audyssey MultEQ", "concept"), ("Denon AVR-X3800H", "infrastructure"), ("Dirac Live", "service"), ("2026-04-01", "date")],
     [("Dirac Live", "Audyssey MultEQ", "REPLACES")],
     "why did the room correction software change on the receiver",
     "room correction upgrade sub bass dip boom kick drum avr calibration"),
    # --- 34 ---
    ("Prefers Emby over Jellyfin specifically for Dad's setup because the Emby Premiere family-account permissions are less confusing than the Jellyfin user-library toggles Dad always double-clicks past.", "preference", "cross", False,
     [("Emby", "service"), ("Jellyfin", "service"), ("Dad", "person"), ("Emby Premiere", "service")],
     [("Emby", "Jellyfin", "PREFERS")],
     "which media server does Dad's remote household run on and why",
     "emby jellyfin family permission ux older relative library visibility"),
    # --- 35 ---
    ("The 2026-03-05 Super Bowl watch party streamed Paramount+ 4K to the projector and the Wi-Fi 6E chain held a 40 Mbps steady feed across twelve guests checking Instagram on the same AP.", "milestone", "cross", False,
     [("2026-03-05", "date"), ("Super Bowl", "publication"), ("Paramount+", "service"), ("Wi-Fi 6E", "protocol"), ("Instagram", "service")],
     [("Paramount+", "Wi-Fi 6E", "USES")],
     "how did the Super Bowl stream hold up with a crowd on the Wi-Fi",
     "live sports 4k stream wireless capacity party concurrent client load"),
    # --- 36 ---
    ("The Madrigal Sony BRAVIA XR A95L replaced the LG C9 in the theater because the QD-OLED panel finally pushes 1000-nit highlights on the Dolby Vision Alien re-release without the C9's near-black crush.", "decision", "cross", False,
     [("Sony BRAVIA XR A95L", "infrastructure"), ("LG C9", "infrastructure"), ("QD-OLED", "concept"), ("Dolby Vision", "concept"), ("Alien", "publication")],
     [("Sony BRAVIA XR A95L", "LG C9", "REPLACES")],
     "which TV took over the theater room and what HDR weakness drove it",
     "qd oled hdr highlight near black crush panel replacement sci fi"),
    # --- 37 ---
    ("Jellyseerr replaced Overseerr once the Jellyfin cutover was finished on 2026-02-11 because Overseerr's Plex-only OAuth couldn't talk to the Jellyfin user database for Mei's requests.", "decision", "cross", False,
     [("Jellyseerr", "service"), ("Overseerr", "service"), ("Jellyfin", "service"), ("2026-02-11", "date"), ("Plex", "service"), ("OAuth", "protocol"), ("Mei", "person")],
     [("Jellyseerr", "Overseerr", "REPLACES"), ("Jellyseerr", "Jellyfin", "USES")],
     "which request portal swapped in after the Jellyfin cutover",
     "jellyseerr overseerr fork jellyfin oauth user database request portal"),
    # --- 38 ---
    ("The Shokugeki no Soma library had a wrong-season-order problem for six months until the Anime-IDs custom mapping in Bazarr finally got the English subs aligned with the Japanese dub audio.", "problem", "cross", False,
     [("Shokugeki no Soma", "publication"), ("Anime-IDs", "publication"), ("Bazarr", "service"), ("English", "language"), ("Japanese", "language")],
     [("Bazarr", "Anime-IDs", "USES")],
     "what fixed the long-standing anime subtitle misalignment",
     "anime custom mapping season numbering subtitle audio sync dub"),
    # --- 39 ---
    ("Night Mode on the Denon AVR-X3800H replaced the manual volume-ducking habit after the baby's bedtime because the dynamic-range compression finally stopped flattening the Dune dialogue into mush.", "decision", "cross", False,
     [("Night Mode", "concept"), ("Denon AVR-X3800H", "infrastructure"), ("Dune", "publication")],
     [],
     "how does late-night movie watching stay quiet without losing dialogue now",
     "night mode dynamic compression baby bedtime dialogue intelligibility"),
    # --- 40 ---
    ("Apple VideoToolbox on the M2 Mac mini handles the Infuse library thumbnails in seconds, which the Intel N100 QuickSync queue used to chew through overnight.", "fact", "cross", False,
     [("Apple VideoToolbox", "concept"), ("M2 Mac mini", "infrastructure"), ("Infuse", "service"), ("Intel N100", "infrastructure"), ("QuickSync", "concept")],
     [("Infuse", "Apple VideoToolbox", "USES")],
     "how did the thumbnail-generation job stop taking all night",
     "apple silicon videotoolbox thumbnail batch hardware acceleration speed"),
    # --- 41 ---
    ("Prefers Kodi on the living-room HTPC over Jellyfin Media Player because the Kodi Estuary MOD V2 skin with the fanart-tv plugin actually surfaces the Star Wars saga collection art the way Plex used to.", "preference", "cross", False,
     [("Kodi", "service"), ("Jellyfin Media Player", "service"), ("Estuary MOD V2", "library"), ("fanart-tv", "service"), ("Star Wars", "publication"), ("Plex", "service")],
     [("Kodi", "Jellyfin Media Player", "PREFERS"), ("Kodi", "Estuary MOD V2", "USES")],
     "which front-end wins for browsing collection art in the living room",
     "kodi skin fanart collection art browsing experience saga movie"),
    # --- 42 ---
    ("The 2026-02-19 Super Bowl LX rewatch lived on the Jellyfin DVR recording of the NFL Network feed because Paramount+'s VOD chopped out the halftime show for rights reasons.", "fact", "cross", False,
     [("2026-02-19", "date"), ("Super Bowl LX", "publication"), ("Jellyfin DVR", "service"), ("NFL Network", "organization"), ("Paramount+", "service")],
     [("Jellyfin DVR", "NFL Network", "USES")],
     "where does the Super Bowl rewatch actually live given the VOD edits",
     "dvr recording live capture vod edit rights stripped halftime show"),
    # --- 43 ---
    ("Radarr's Recyclarr sync replaced the manual TRaSH-Guide JSON import on the nightly schedule, which finally stopped the config drift between the anime Radarr and the movie Radarr instances.", "architecture", "cross", False,
     [("Radarr", "service"), ("Recyclarr", "service"), ("TRaSH-Guide", "publication"), ("JSON", "concept")],
     [("Recyclarr", "TRaSH-Guide", "USES"), ("Recyclarr", "Radarr", "COMMUNICATES_WITH")],
     "how did the two Radarr instances stop drifting apart on custom formats",
     "recyclarr trash guide sync config drift anime movie instance parity"),
    # --- 44 ---
    ("Curiosity turned to respect when the 2026-01-30 Better Call Saul S06 rewatch on Netflix finally did Dolby Vision Profile 5 right on the Apple TV 4K chain after last year's banding issue.", "milestone", "cross", False,
     [("Curiosity", "emotion"), ("2026-01-30", "date"), ("Better Call Saul", "publication"), ("Netflix", "service"), ("Dolby Vision Profile 5", "concept"), ("Apple TV 4K", "infrastructure")],
     [("Netflix", "Apple TV 4K", "DEPLOYED_ON")],
     "when did the Netflix HDR banding problem on the Apple TV finally go away",
     "dolby vision profile 5 banding streamer hdr tone map rewatch respect"),
    # --- 45 ---
    ("Prefers Mullvad VPN over ProtonVPN for the Gluetun container because Mullvad's Wireguard config doesn't drop the port-forward when Europe-Stockholm-2 rotates at midnight UTC.", "preference", "cross", False,
     [("Mullvad VPN", "service"), ("ProtonVPN", "service"), ("Gluetun", "service"), ("Wireguard", "protocol")],
     [("Mullvad VPN", "ProtonVPN", "PREFERS"), ("Gluetun", "Mullvad VPN", "USES")],
     "which VPN wins under the download gateway and why",
     "mullvad protonvpn wireguard port forward rotation stability comparison"),
    # --- 46 ---
    ("Calm settled in after the 2026-03-28 wiring redo finally ran eARC-rated HDMI 2.1 cables from the LG C2 through the Denon to the Panasonic UB820 without the occasional audio dropout.", "milestone", "cross", False,
     [("Calm", "emotion"), ("2026-03-28", "date"), ("eARC", "protocol"), ("HDMI 2.1", "protocol"), ("LG C2", "infrastructure"), ("Denon", "organization"), ("Panasonic UB820", "infrastructure")],
     [],
     "when did the theater cable redo finally end the audio dropouts",
     "hdmi 2.1 rewire earc certified cable dropout eliminate theater chain"),
    # --- 47 ---
    ("The Lidarr library for lossless FLAC replaced the Spotify Premium download habit for the road-trip car system because the Qobuz-sourced Yeah Yeah Yeahs discography sounds cleaner on the car's Apple CarPlay chain.", "decision", "cross", False,
     [("Lidarr", "service"), ("FLAC", "concept"), ("Spotify Premium", "service"), ("Qobuz", "service"), ("Yeah Yeah Yeahs", "person"), ("Apple CarPlay", "service")],
     [("Lidarr", "Spotify Premium", "REPLACES"), ("Lidarr", "Qobuz", "USES")],
     "how did the car-trip music library swap to lossless files",
     "lidarr flac lossless car audio carplay qobuz source spotify download"),
    # --- 48 ---
    ("The Jellyfin for Kodi add-on replaced direct Jellyfin Media Player on the theater HTPC because the Kodi library integration finally let the Yatse Android remote scrub playback from the couch.", "decision", "cross", False,
     [("Jellyfin for Kodi", "service"), ("Jellyfin Media Player", "service"), ("Kodi", "service"), ("Yatse", "tool"), ("Android", "infrastructure")],
     [("Jellyfin for Kodi", "Jellyfin Media Player", "REPLACES"), ("Yatse", "Kodi", "COMMUNICATES_WITH")],
     "how did the phone remote finally regain scrub control in the theater",
     "jellyfin kodi sync add on phone remote scrub library integration"),
    # --- 49 ---
    ("Unpackerr replaced the manual post-download extraction glue because the RARBG-style nested archive from the old German release-group feed was otherwise blocking Sonarr imports for hours.", "architecture", "cross", False,
     [("Unpackerr", "service"), ("RARBG", "organization"), ("Sonarr", "service"), ("German", "language")],
     [("Unpackerr", "Sonarr", "COMMUNICATES_WITH")],
     "what cleared the stuck Sonarr imports on nested archive releases",
     "unpackerr nested archive extract post download glue arr import stall"),
    # --- 50 ---
    ("Joy cracked through on 2026-04-09 when Noa asked for My Neighbor Totoro on the Apple TV and the Overseerr-to-Jellyseerr-to-Radarr chain had the 4K HDR rip playing in under ten minutes.", "milestone", "cross", False,
     [("Joy", "emotion"), ("2026-04-09", "date"), ("Noa", "person"), ("My Neighbor Totoro", "publication"), ("Apple TV", "infrastructure"), ("Jellyseerr", "service"), ("Radarr", "service")],
     [("Jellyseerr", "Radarr", "COMMUNICATES_WITH")],
     "when did the full request-to-play pipeline finally feel instant for Noa",
     "request pipeline kid request fulfillment ghibli 4k hdr speed end to end"),
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
