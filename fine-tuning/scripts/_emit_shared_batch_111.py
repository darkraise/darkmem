"""One-off emitter for shared-base batch-111 — cross domain.

Slice: music listening meets tech (streaming service choices, scrobbling, hi-res
libraries, hardware streamers, smart speakers, concert calendars). Writes 50
rows to data/v2/shared/batch_111.tmp.jsonl with ids shared-05501..05550. The
main session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_111.tmp.jsonl"
ID_OFFSET = 5500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Dropped Spotify for Apple Music on 2026-02-01 after the lossless ALAC rollout finally landed on the HomePod mini stereo pair and Spotify's HiFi tier still hadn't shipped.", "decision", "cross", False,
     [("Spotify", "service"), ("Apple Music", "service"), ("2026-02-01", "date"), ("ALAC", "concept"), ("HomePod mini", "infrastructure")],
     [("Apple Music", "Spotify", "REPLACES"), ("Apple Music", "HomePod mini", "DEPLOYED_ON")],
     "when did the household streaming service swap away from Spotify and why",
     "lossless alac rollout stereo pair hifi tier delay streaming migration"),
    # --- 2 ---
    ("Prefers Qobuz over Tidal for classical because the Berliner Philharmoniker Digital Concert Hall discount only applies to Qobuz Studio subscribers in Germany.", "preference", "cross", False,
     [("Qobuz", "service"), ("Tidal", "service"), ("Berliner Philharmoniker", "organization"), ("Germany", "place")],
     [("Qobuz", "Tidal", "PREFERS")],
     "which hi-res service wins for classical listening and why",
     "classical catalog hi res partnership concert hall discount bundle"),
    # --- 3 ---
    ("Scrobbling moved from Last.fm to ListenBrainz on 2026-03-09 after the Last.fm Spotify bridge silently stopped logging podcasts and the lifetime count froze for a week.", "milestone", "cross", False,
     [("Last.fm", "service"), ("ListenBrainz", "service"), ("2026-03-09", "date"), ("Spotify", "service")],
     [("ListenBrainz", "Last.fm", "REPLACES")],
     "when did the listening history move off of Last.fm and what triggered it",
     "scrobble bridge silent failure podcast logging lifetime count freeze"),
    # --- 4 ---
    ("Soundiiz migrated 214 playlists from Spotify to Tidal in the 2026-01-15 trial but the 'Sunday Slow Burn' mix lost 38 tracks that only existed on Spotify's editorial catalog.", "problem", "cross", False,
     [("Soundiiz", "service"), ("Spotify", "service"), ("Tidal", "service"), ("2026-01-15", "date"), ("Sunday Slow Burn", "concept")],
     [("Soundiiz", "Spotify", "COMMUNICATES_WITH"), ("Soundiiz", "Tidal", "COMMUNICATES_WITH")],
     "what broke when the playlist migration tool moved my library to Tidal",
     "playlist transfer editorial catalog gap missing tracks mood mix"),
    # --- 5 ---
    ("The Roon Nucleus on 192.168.1.40 serves the hi-res FLAC library off the Synology NAS to the Naim Atom HE in the living room because Tidal Connect alone couldn't address the USB DAC upstream.", "architecture", "cross", False,
     [("Roon", "service"), ("Synology", "infrastructure"), ("Naim Atom HE", "infrastructure"), ("Tidal", "service"), ("DAC", "infrastructure")],
     [("Roon", "Synology", "USES"), ("Roon", "Naim Atom HE", "COMMUNICATES_WITH")],
     "how does the local FLAC library actually reach the living room streamer",
     "roon core nas backend streamer endpoint usb dac routing topology"),
    # --- 6. noise ---
    ("Let me pull that up for you real quick.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Bandcamp replaced iTunes Store purchases on 2026-01-30 for indie releases because Bandcamp Friday waives the platform cut and the 24-bit WAV download lands straight on the NAS.", "decision", "cross", False,
     [("Bandcamp", "service"), ("iTunes Store", "service"), ("2026-01-30", "date"), ("NAS", "infrastructure")],
     [("Bandcamp", "iTunes Store", "REPLACES")],
     "where do indie album purchases land now instead of the iTunes Store",
     "bandcamp friday artist cut waiver high res download nas archive"),
    # --- 8 ---
    ("Prefers Plexamp over Jellyfin for the headphone-out session on the laptop because the Sonic Analysis sonic sorting weaves Tycho into Bonobo more smoothly than the Jellyfin smart playlist.", "preference", "cross", False,
     [("Plexamp", "service"), ("Jellyfin", "service"), ("Tycho", "organization"), ("Bonobo", "organization")],
     [("Plexamp", "Jellyfin", "PREFERS")],
     "which self-hosted client feels better for focus listening and why",
     "sonic analysis smart playlist segue artist transition self hosted"),
    # --- 9 ---
    ("The Discogs collection export on 2026-03-22 counted 412 records and CollectorzApp replaced it for the insurance photos because Discogs doesn't store sleeve-condition close-ups.", "decision", "cross", False,
     [("Discogs", "service"), ("2026-03-22", "date"), ("CollectorzApp", "tool")],
     [("CollectorzApp", "Discogs", "REPLACES")],
     "which app actually tracks the vinyl collection now for insurance purposes",
     "vinyl collection catalog insurance sleeve condition photo documentation"),
    # --- 10 ---
    ("The Sonos Arc, Era 300 pair, and Sub Mini all run on the 2026-03-14 S2 firmware because the S1 holdouts in the kitchen finally got retired with the Era 100 upgrade.", "architecture", "cross", False,
     [("Sonos Arc", "infrastructure"), ("Era 300", "infrastructure"), ("Sub Mini", "infrastructure"), ("2026-03-14", "date"), ("Era 100", "infrastructure")],
     [("Era 300", "Sonos Arc", "COMMUNICATES_WITH")],
     "what is the current state of the multi-room Sonos firmware mix",
     "multi room speaker firmware unification legacy retirement upgrade"),
    # --- 11 ---
    ("Joy hit hard at the 2026-02-20 Four Tet show at Brooklyn Steel because Bandsintown's pre-sale alert fired 40 minutes before Songkick's and the tickets cleared before the code expired.", "milestone", "cross", False,
     [("Joy", "emotion"), ("2026-02-20", "date"), ("Four Tet", "organization"), ("Brooklyn Steel", "place"), ("Bandsintown", "service"), ("Songkick", "service")],
     [("Bandsintown", "Songkick", "PREFERS")],
     "which concert alert caught the Four Tet show in time this winter",
     "concert pre sale alert race notification lead time ticket window"),
    # --- 12 ---
    ("CarPlay on the Mazda head unit refuses to surface the Apple Music Library view over Bluetooth so the USB-C tether stays wired to the center console for every commute.", "problem", "cross", False,
     [("CarPlay", "service"), ("Mazda", "infrastructure"), ("Apple Music", "service"), ("Bluetooth", "protocol"), ("USB-C", "protocol")],
     [("CarPlay", "Apple Music", "USES")],
     "why does the car music setup still need a cable instead of wireless",
     "carplay bluetooth library view limitation wired tether commute"),
    # --- 13 ---
    ("The Bluesound Node on the bedroom Cambridge Audio CXA81 replaced a Raspberry Pi 4 volumio build because the Pi's USB out kept dropping clicks on DSD128 files from the NAS.", "decision", "cross", False,
     [("Bluesound Node", "infrastructure"), ("Cambridge Audio CXA81", "infrastructure"), ("Raspberry Pi 4", "infrastructure"), ("volumio", "tool"), ("DSD128", "concept"), ("NAS", "infrastructure")],
     [("Bluesound Node", "Raspberry Pi 4", "REPLACES")],
     "why did the bedroom streamer get upgraded from the Pi build",
     "network streamer dac usb dropout dsd playback silicon upgrade"),
    # --- 14 ---
    ("Tune My Music picked up where Soundiiz choked on the 2026-02-09 library backup because Tune My Music handled the YouTube Music uploaded tracks that Soundiiz silently skipped.", "decision", "cross", False,
     [("Tune My Music", "service"), ("Soundiiz", "service"), ("2026-02-09", "date"), ("YouTube Music", "service")],
     [("Tune My Music", "Soundiiz", "REPLACES")],
     "which migration tool actually handled the YouTube Music uploads correctly",
     "playlist migration uploaded track user library coverage silent skip"),
    # --- 15 ---
    ("Prefers the HD 660S2 over the Arya Organic for long mixing sessions because the Sennheiser pair doesn't fatigue after three hours on the RME ADI-2 headphone out.", "preference", "cross", False,
     [("HD 660S2", "infrastructure"), ("Arya Organic", "infrastructure"), ("Sennheiser", "organization"), ("RME ADI-2", "infrastructure")],
     [("HD 660S2", "Arya Organic", "PREFERS")],
     "which headphone wins for long listening sessions and why",
     "headphone fatigue dynamic versus planar long session dac amp"),
    # --- 16 ---
    ("The FLAC archive on the Synology DS923+ hit 1.4 TB on 2026-03-01 after ripping the remaining 62 SACD isos with dBpoweramp and tagging through MusicBrainz Picard.", "milestone", "cross", False,
     [("Synology DS923+", "infrastructure"), ("2026-03-01", "date"), ("SACD", "concept"), ("dBpoweramp", "tool"), ("MusicBrainz Picard", "tool")],
     [("dBpoweramp", "MusicBrainz Picard", "COMMUNICATES_WITH")],
     "when did the local music archive cross over a terabyte and how was it tagged",
     "flac archive rip workflow sacd iso tagging nas capacity milestone"),
    # --- 17 ---
    ("Scratched the Echo Studio from the kitchen listening rotation on 2026-02-28 because Alexa kept mishearing 'play Low Roar' as 'play low rock' and Spotify Connect handoff lagged.", "problem", "cross", False,
     [("Echo Studio", "infrastructure"), ("2026-02-28", "date"), ("Alexa", "service"), ("Low Roar", "organization"), ("Spotify Connect", "service")],
     [("Echo Studio", "Spotify Connect", "USES")],
     "why did the kitchen Echo fall out of the daily listening rotation",
     "voice assistant misrecognition artist name handoff lag kitchen speaker"),
    # --- 18 ---
    ("The Rega Planar 3 with the Ortofon 2M Bronze feeds a Schiit Mani 2 into the Audeze Deckard on the desk because the Apollon Mimas integrated only has one phono input and it's in the living room.", "architecture", "cross", False,
     [("Rega Planar 3", "infrastructure"), ("Ortofon 2M Bronze", "infrastructure"), ("Schiit Mani 2", "infrastructure"), ("Audeze Deckard", "infrastructure"), ("Apollon Mimas", "infrastructure")],
     [("Rega Planar 3", "Schiit Mani 2", "COMMUNICATES_WITH")],
     "how is the desk turntable chain wired given the living room constraint",
     "turntable cartridge phono stage amp desk chain vinyl signal path"),
    # --- 19 ---
    ("Prefers mobile Tidal over Qobuz on the Pixel 9 because Tidal's Android Auto rendering keeps the lock-screen artwork live, which Qobuz's 2026-03 update still breaks intermittently.", "preference", "cross", False,
     [("Tidal", "service"), ("Qobuz", "service"), ("Pixel 9", "infrastructure"), ("Android Auto", "service")],
     [("Tidal", "Android Auto", "DEPLOYED_ON")],
     "which hi-res app works more reliably in the car on Android",
     "android auto rendering lock screen artwork stability hi res mobile"),
    # --- 20 ---
    ("The 2026-03-18 audition at In Living Stereo of the LS50 Wireless II versus the KEF LSX II convinced me the larger pair was worth the Manhattan trip after the bedroom demo felt lifeless.", "milestone", "cross", False,
     [("2026-03-18", "date"), ("In Living Stereo", "place"), ("LS50 Wireless II", "infrastructure"), ("KEF LSX II", "infrastructure"), ("Manhattan", "place")],
     [("LS50 Wireless II", "KEF LSX II", "PREFERS")],
     "what came out of the Manhattan speaker audition in mid-March",
     "speaker audition comparison active wireless dealer demo purchase pivot"),
    # --- 21 ---
    ("Moved the podcast listening off Apple Podcasts to Pocket Casts on 2026-02-14 because Pocket Casts's per-show silence trimming shaved 22 minutes off the Acquired back catalog.", "decision", "cross", False,
     [("Apple Podcasts", "service"), ("Pocket Casts", "service"), ("2026-02-14", "date"), ("Acquired", "publication")],
     [("Pocket Casts", "Apple Podcasts", "REPLACES")],
     "why did the podcast app change for the daily commute",
     "podcast client silence trimming speed listening time savings switch"),
    # --- 22 ---
    ("The Songkick concert calendar merged into the Google Calendar via IFTTT on 2026-03-05 so the 'Gigs' subcalendar shows alongside the work schedule without flipping apps.", "architecture", "cross", False,
     [("Songkick", "service"), ("Google Calendar", "service"), ("IFTTT", "service"), ("2026-03-05", "date"), ("Gigs", "concept")],
     [("IFTTT", "Songkick", "USES"), ("IFTTT", "Google Calendar", "COMMUNICATES_WITH")],
     "how do concert dates surface alongside work meetings without app flipping",
     "concert calendar sync subcalendar automation work schedule overlay"),
    # --- 23 ---
    ("YouTube Music stays as the secondary service for rare live sets because the Boiler Room rips and Dekmantel streams disappear from everywhere else inside a year.", "decision", "cross", False,
     [("YouTube Music", "service"), ("Boiler Room", "organization"), ("Dekmantel", "organization")],
     [],
     "why does YouTube Music still hang on as a backup service",
     "rare live set preservation boiler room dekmantel catalog niche recording"),
    # --- 24 ---
    ("The Topping D90SE DAC replaced the RME ADI-2 on the reference desk on 2026-01-18 after an A/B at Mei's place showed the Topping's NOS filter matched vinyl better on acoustic material.", "decision", "cross", False,
     [("Topping D90SE", "infrastructure"), ("RME ADI-2", "infrastructure"), ("2026-01-18", "date"), ("Mei", "person")],
     [("Topping D90SE", "RME ADI-2", "REPLACES")],
     "when did the reference DAC change on the desk and why",
     "dac upgrade filter comparison vinyl tonality acoustic reference swap"),
    # --- 25 ---
    ("Prefers Navidrome over Jellyfin for the phone client because Substreamer against the Navidrome API handles the 60k FLAC library without the Jellyfin mobile app's scroll stutter.", "preference", "cross", False,
     [("Navidrome", "tool"), ("Jellyfin", "service"), ("Substreamer", "service"), ("FLAC", "concept")],
     [("Substreamer", "Navidrome", "USES"), ("Navidrome", "Jellyfin", "PREFERS")],
     "which self-hosted music server feels better on mobile for the big library",
     "self hosted music server mobile client subsonic api large library scroll"),
    # --- 26 ---
    ("Excitement spiked when the 2026-04-04 Sigur Rós announcement hit Bandsintown for the Kings Theatre date exactly three minutes after the band's newsletter went out.", "fact", "cross", False,
     [("Excitement", "emotion"), ("2026-04-04", "date"), ("Sigur Rós", "organization"), ("Bandsintown", "service"), ("Kings Theatre", "place")],
     [],
     "what tour announcement caught the concert tracker right after the newsletter",
     "artist tour announcement concert alert newsletter delivery race"),
    # --- 27 ---
    ("The Bluesound Pulse Flex in the bathroom replaced an old HomePod Mini on 2026-03-10 because the HomePod refused to join AirPlay groups once the mesh SSID changed.", "decision", "cross", False,
     [("Bluesound Pulse Flex", "infrastructure"), ("HomePod Mini", "infrastructure"), ("2026-03-10", "date"), ("AirPlay", "protocol")],
     [("Bluesound Pulse Flex", "HomePod Mini", "REPLACES")],
     "why did the bathroom speaker change after the Wi-Fi reconfiguration",
     "airplay group join failure mesh ssid rename speaker replacement"),
    # --- 28 ---
    ("The Chord Mojo 2 lives in the work bag because the MacBook Pro's built-in DAC hisses on the Focal Bathys whenever the USB-C hub pulls from a monitor.", "architecture", "cross", False,
     [("Chord Mojo 2", "infrastructure"), ("MacBook Pro", "infrastructure"), ("Focal Bathys", "infrastructure"), ("USB-C", "protocol")],
     [("Chord Mojo 2", "MacBook Pro", "COMMUNICATES_WITH")],
     "why does a portable DAC travel with the laptop every day",
     "portable dac laptop hub ground hiss bluetooth headphone wired fallback"),
    # --- 29 ---
    ("Prefers the Pro-Ject Debut Carbon Evo over the Fluance RT85 for the office deck because the Pro-Ject's speed switch is physical and the Fluance's electronic button kept double-firing.", "preference", "cross", False,
     [("Pro-Ject Debut Carbon Evo", "infrastructure"), ("Fluance RT85", "infrastructure")],
     [("Pro-Ject Debut Carbon Evo", "Fluance RT85", "PREFERS")],
     "which budget turntable earned the office spot and why",
     "turntable speed switch reliability physical button double fire preference"),
    # --- 30 ---
    ("Shipped the first private last.fm-to-ListenBrainz backfill script on 2026-03-21 that paged the 47k-track history through the ListenBrainz import token without tripping the rate limit.", "milestone", "cross", False,
     [("last.fm", "service"), ("ListenBrainz", "service"), ("2026-03-21", "date")],
     [("ListenBrainz", "last.fm", "IMPROVES_ON")],
     "when did the scrobble history backfill script actually finish",
     "scrobble backfill pagination api token rate limit history export"),
    # --- 31 ---
    ("Apple Music Classical replaced Idagio on the phone after the 2026-02-27 update finally let the Vienna Philharmonic Beethoven 9 cycle play gapless across the four movements.", "decision", "cross", False,
     [("Apple Music Classical", "service"), ("Idagio", "service"), ("2026-02-27", "date"), ("Vienna Philharmonic", "organization"), ("Beethoven 9", "pattern")],
     [("Apple Music Classical", "Idagio", "REPLACES")],
     "why did the classical app change this winter",
     "classical streaming app gapless playback symphony cycle metadata"),
    # --- 32 ---
    ("The Bose QuietComfort Ultra replaced the Sony WH-1000XM5 in the travel kit because the Immersive Audio mode on Qobuz spatial tracks worked on the Lisbon flight without a Sony account login.", "decision", "cross", False,
     [("Bose QuietComfort Ultra", "infrastructure"), ("Sony WH-1000XM5", "infrastructure"), ("Qobuz", "service"), ("Lisbon", "place")],
     [("Bose QuietComfort Ultra", "Sony WH-1000XM5", "REPLACES")],
     "which travel headphones won for the Lisbon flight and why",
     "noise canceling headphone travel swap spatial audio immersive mode"),
    # --- 33 ---
    ("Pianolytics by Mei ran the MusicBrainz dedup pass on the FLAC library and collapsed 4,200 duplicate tracks from inconsistent 'feat.' spelling on 2026-03-25.", "milestone", "cross", False,
     [("Pianolytics", "tool"), ("Mei", "person"), ("MusicBrainz", "service"), ("FLAC", "concept"), ("2026-03-25", "date")],
     [("Pianolytics", "MusicBrainz", "USES")],
     "when did the FLAC duplicate cleanup run and who wrote the tool",
     "dedup pass metadata canonicalization feat spelling tag tool batch"),
    # --- 34. noise ---
    ("Sorry, I'm still catching up on the question.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The AudioQuest DragonFly Cobalt fed the iPhone 15 Pro into the Sennheiser IE 600 on the 2026-03-02 Amtrak to Boston because the Apple Music lossless over Lightning wouldn't hit 24/96 without it.", "fact", "cross", False,
     [("AudioQuest DragonFly Cobalt", "infrastructure"), ("iPhone 15 Pro", "infrastructure"), ("Sennheiser IE 600", "infrastructure"), ("2026-03-02", "date"), ("Amtrak", "organization"), ("Apple Music", "service")],
     [("AudioQuest DragonFly Cobalt", "iPhone 15 Pro", "COMMUNICATES_WITH")],
     "how did the train listening hit true hi-res on the iPhone that day",
     "dongle dac iem lossless mobile sample rate lightning train commute"),
    # --- 36 ---
    ("Discogs's Inventory feature replaced the old Numbers spreadsheet for the vinyl-for-sale pile because Discogs calculates median market price and the spreadsheet was six months stale.", "decision", "cross", False,
     [("Discogs", "service"), ("Numbers", "tool")],
     [("Discogs", "Numbers", "REPLACES")],
     "why did the vinyl for-sale tracker move off the spreadsheet",
     "discogs inventory market price lookup spreadsheet retirement pricing"),
    # --- 37 ---
    ("The Roon ARC app handled remote listening on the 2026-01-26 Berlin work trip by tunneling to the Nucleus at home over the WireGuard VPN when the UPnP punch-through refused to open port 55000.", "architecture", "cross", False,
     [("Roon ARC", "service"), ("2026-01-26", "date"), ("Berlin", "place"), ("Nucleus", "infrastructure"), ("WireGuard", "tool"), ("UPnP", "protocol")],
     [("Roon ARC", "WireGuard", "USES")],
     "how did remote Roon listening work from Berlin when UPnP didn't cooperate",
     "remote streaming vpn tunnel upnp failure port forward travel roon arc"),
    # --- 38 ---
    ("Prefers the KEF LS60 Wireless over the Dynaudio Focus 30 as the main pair because the LS60 runs Roon Ready without the Dynaudio's clunky Dirac setup dance.", "preference", "cross", False,
     [("KEF LS60 Wireless", "infrastructure"), ("Dynaudio Focus 30", "infrastructure"), ("Roon Ready", "concept"), ("Dirac", "tool")],
     [("KEF LS60 Wireless", "Dynaudio Focus 30", "PREFERS")],
     "which active main pair won the listening room and why",
     "active floorstander roon ready room correction setup comparison"),
    # --- 39 ---
    ("The 2026-03-30 Aphex Twin surprise drop on Warp's Bleep store got pulled into the Navidrome library inside two hours via a Syncthing relay off the desktop's Bleep download folder.", "milestone", "cross", False,
     [("2026-03-30", "date"), ("Aphex Twin", "organization"), ("Warp", "organization"), ("Bleep", "service"), ("Navidrome", "tool"), ("Syncthing", "tool")],
     [("Syncthing", "Navidrome", "COMMUNICATES_WITH")],
     "how did the surprise Aphex drop land in the home library so fast",
     "surprise release automation download sync local library ingest pipeline"),
    # --- 40 ---
    ("Frustration set in when Spotify's 2026-03-11 algorithmic DJ feature shoehorned a Post Malone cut into a night-drive playlist that had been 100% downtempo for two years.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Spotify", "service"), ("2026-03-11", "date"), ("Post Malone", "organization")],
     [],
     "what ruined the night drive playlist this month on Spotify",
     "algorithmic dj genre drift mismatched injection downtempo mood break"),
    # --- 41 ---
    ("The Rega Fono Mini A2D replaced the built-in phono stage of the Marantz 2238B on 2026-02-16 because the Marantz's left channel hummed once the Ground Control wiring was cleaned up.", "decision", "cross", False,
     [("Rega Fono Mini A2D", "infrastructure"), ("Marantz 2238B", "infrastructure"), ("2026-02-16", "date"), ("Ground Control", "concept")],
     [("Rega Fono Mini A2D", "Marantz 2238B", "REPLACES")],
     "why did the vintage receiver's phono stage get bypassed",
     "external phono stage ground hum vintage receiver bypass upgrade"),
    # --- 42 ---
    ("Prefers Beatsource Pro over Beatport Streaming for DJ practice because the DJcity edits and the DJ pool remixes on Beatsource aren't on Beatport at all.", "preference", "cross", False,
     [("Beatsource Pro", "service"), ("Beatport Streaming", "service"), ("DJcity", "service")],
     [("Beatsource Pro", "Beatport Streaming", "PREFERS")],
     "which DJ streaming service wins for practice sets and why",
     "dj pool edit remix catalog exclusive streaming subscription"),
    # --- 43 ---
    ("Moved the bedroom Echo Dot onto the 'Night' Sonos group via the 2026-02-25 Matter-over-Thread firmware because the Alexa routine could finally trigger the Ikea Symfonisk bookshelves.", "milestone", "cross", False,
     [("Echo Dot", "infrastructure"), ("Sonos", "organization"), ("2026-02-25", "date"), ("Matter", "protocol"), ("Thread", "protocol"), ("Alexa", "service"), ("Ikea Symfonisk", "infrastructure")],
     [("Echo Dot", "Sonos", "COMMUNICATES_WITH")],
     "when did the voice-triggered night music group finally work end to end",
     "matter thread firmware cross vendor speaker group voice routine"),
    # --- 44 ---
    ("Prefers Sonos Voice Control over Alexa on the Era 300 for music commands because Sonos Voice Control doesn't hallucinate a SiriusXM station when the Apple Music request fails.", "preference", "cross", False,
     [("Sonos Voice Control", "service"), ("Alexa", "service"), ("Era 300", "infrastructure"), ("SiriusXM", "service"), ("Apple Music", "service")],
     [("Sonos Voice Control", "Alexa", "PREFERS")],
     "which voice assistant won for speaker control and why",
     "voice control assistant fallback behavior service substitution music"),
    # --- 45 ---
    ("The Resident Advisor 2026-03-28 feature on deep house improved on the old XLR8R archive for the weekly listening queue because RA's in-app audio samples play inline now.", "reference", "cross", False,
     [("Resident Advisor", "publication"), ("2026-03-28", "date"), ("XLR8R", "publication")],
     [("Resident Advisor", "XLR8R", "IMPROVES_ON")],
     "which electronic music publication replaced the old archive for discovery",
     "electronic music publication discovery in app audio sample inline"),
    # --- 46 ---
    ("The Oppo UDP-205 stays in the rack purely as a SACD transport into the Topping D90SE via coax because no modern streamer I tested passed DSD bit-perfect over the same link.", "architecture", "cross", False,
     [("Oppo UDP-205", "infrastructure"), ("SACD", "concept"), ("Topping D90SE", "infrastructure"), ("DSD", "concept")],
     [("Oppo UDP-205", "Topping D90SE", "COMMUNICATES_WITH")],
     "why does the old disc player still sit in the rack next to the streamer",
     "disc transport sacd coax bit perfect dsd signal chain legacy player"),
    # --- 47 ---
    ("Regret struck after the 2026-01-08 Dead Oceans sale when I forgot to grab the Phoebe Bridgers ice-blue reissue before Rough Trade sold out in 40 minutes.", "problem", "cross", False,
     [("Regret", "emotion"), ("2026-01-08", "date"), ("Dead Oceans", "organization"), ("Phoebe Bridgers", "organization"), ("Rough Trade", "organization")],
     [],
     "what vinyl release got away during the January label sale",
     "label sale limited color variant sell out regret vinyl reissue"),
    # --- 48 ---
    ("The iFi Zen Stream replaced the Chromecast Audio that powered the guest room on 2026-03-06 because Google End-of-Life on the Chromecast broke Spotify Connect group playback.", "decision", "cross", False,
     [("iFi Zen Stream", "infrastructure"), ("Chromecast Audio", "infrastructure"), ("2026-03-06", "date"), ("Google", "organization"), ("Spotify Connect", "service")],
     [("iFi Zen Stream", "Chromecast Audio", "REPLACES")],
     "why did the guest room streamer get swapped this March",
     "chromecast audio end of life network streamer replacement group playback"),
    # --- 49 ---
    ("The 2026-03-12 Stereophile review of the Hegel H190V improved on the old TAS piece by actually measuring the DAC's jitter over USB input.", "reference", "cross", False,
     [("2026-03-12", "date"), ("Stereophile", "publication"), ("Hegel H190V", "infrastructure"), ("TAS", "publication")],
     [("Stereophile", "TAS", "IMPROVES_ON")],
     "which integrated amp review actually measured jitter this spring",
     "integrated amp review dac jitter measurement usb input audiophile"),
    # --- 50 ---
    ("Calm settled in on the 2026-04-02 commute when the Audeze Maxwell over 2.4 GHz wireless on the Pixel 9 finally streamed a clean Qobuz hi-res feed end to end for the whole Ocean-bound ride.", "milestone", "cross", False,
     [("Calm", "emotion"), ("2026-04-02", "date"), ("Audeze Maxwell", "infrastructure"), ("Pixel 9", "infrastructure"), ("Qobuz", "service")],
     [("Audeze Maxwell", "Pixel 9", "COMMUNICATES_WITH"), ("Audeze Maxwell", "Qobuz", "USES")],
     "when did the wireless headphone chain finally run hi-res cleanly on the commute",
     "wireless headphone sub ghz dongle hi res streaming mobile stability"),
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
