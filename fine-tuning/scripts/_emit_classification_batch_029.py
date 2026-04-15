"""One-off emitter for classification top-up batch-029 — multi_type mode, cross-domain slice.

Writes 100 rows to data/v2/classification/batch_029.tmp.jsonl with ids class-02801..02900.

Distribution (exact):
  fact         : 15
  decision     : 15
  preference   : 15
  problem      : 15
  architecture : 15
  milestone    : 15
  reference    : 10 (each with a citable source)

Every row mixes a personal-life artefact with a tech/software/hardware artefact.
No pair_id. Schema: {id, domain, text, memory_type}.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_029.tmp.jsonl"
ID_OFFSET = 2800

# Each row: (text, domain, memory_type). Text length 15–45 words.
ROWS: list[tuple[str, str, str]] = [
    # ---------------- fact (15) ----------------
    (
        "My Garmin Fenix 7 watch uploads daily heart-rate variability data to Garmin Connect over Bluetooth, and the Health Sync Android app mirrors those same readings into Apple Health on my partner's iPhone.",
        "cross",
        "fact",
    ),
    (
        "The Anova Precision Cooker holds water temperature within 0.1 degrees Celsius, and its iOS companion app uses Bluetooth Low Energy for nearby control and the cloud bridge only when the phone is off the home Wi-Fi.",
        "cross",
        "fact",
    ),
    (
        "My Kindle Paperwhite syncs the furthest-read position of every book to Amazon's Whispersync service, so when I switch to the Kindle iPad app on the couch the last page is already waiting without manual action.",
        "cross",
        "fact",
    ),
    (
        "The Sony A7 IV writes dual card slots simultaneously in backup mode, and Lightroom Classic's tethered capture over USB-C pulls RAW files into a dated folder structure defined by my import preset.",
        "cross",
        "fact",
    ),
    (
        "Spotify Connect lets my phone act as a remote control while the audio stream is served directly from Spotify's backend to my Sonos speakers, which keeps my phone battery flat instead of relaying the audio locally.",
        "cross",
        "fact",
    ),
    (
        "My Nintendo Switch cloud saves are tied to my Nintendo Switch Online membership, and the service explicitly excludes a short list of titles including Animal Crossing and Splatoon from cloud backup for gameplay-fairness reasons.",
        "cross",
        "fact",
    ),
    (
        "The Aqara FP2 presence sensor uses millimeter-wave radar on the 60 GHz band to detect stationary humans, and it publishes zone occupancy events to Home Assistant through the local Matter over Thread bridge.",
        "cross",
        "fact",
    ),
    (
        "My Obsidian vault is stored as plain Markdown files inside an iCloud Drive folder, and the Obsidian Sync service only comes into play when I want end-to-end encrypted syncing across devices that skip iCloud entirely.",
        "cross",
        "fact",
    ),
    (
        "YNAB imports transactions from my Chase credit card through a third-party aggregator, and the service categorizes them client-side using rules I configured, never shipping my raw transaction text to a language model.",
        "cross",
        "fact",
    ),
    (
        "Amazon's one-click checkout stores a hashed reference to my default payment method, and the Subscribe and Save pipeline schedules orders through an internal cron that runs once per day per delivery region.",
        "cross",
        "fact",
    ),
    (
        "Our cat's Sure Petcare microchip door reads the 15-digit FDX-B identifier embedded in his subcutaneous chip, and the hub reports each entry and exit event to the Sure Petcare cloud over Ethernet.",
        "cross",
        "fact",
    ),
    (
        "My raised garden bed uses a LoRaWAN soil moisture probe that reports once every fifteen minutes through The Things Network, and Home Assistant ingests the payload through an MQTT bridge on the local network.",
        "cross",
        "fact",
    ),
    (
        "My Tesla Model 3 uploads trip telemetry to Tesla's servers over LTE, and the TeslaMate self-hosted companion captures the same data locally by polling the owner API every few seconds while the car is awake.",
        "cross",
        "fact",
    ),
    (
        "Plex Media Server transcodes my 4K HEVC library on the fly when my parents stream to their older Roku, and the transcoder selects the NVENC path automatically because the server GPU exposes hardware encoding to the container.",
        "cross",
        "fact",
    ),
    (
        "My Ghost blog runs on a small VPS with SQLite as its datastore, and every published post triggers a webhook that invalidates the Cloudflare cache for the affected URLs within a few seconds of publication.",
        "cross",
        "fact",
    ),

    # ---------------- decision (15) ----------------
    (
        "I decided to drop Strava Premium after renewing Garmin Connect Plus, because the Garmin training readiness metric already covers the analytics I actually look at and the overlap did not justify two subscriptions.",
        "cross",
        "decision",
    ),
    (
        "We chose the Breville Oracle Touch over a Lelit Bianca for the kitchen because my partner wanted one-button espresso and the companion firmware updates through a USB stick kept the machine out of our Wi-Fi policy.",
        "cross",
        "decision",
    ),
    (
        "I decided to migrate my reading list from Goodreads to The StoryGraph because the StoryGraph API exposes a clean CSV export and Goodreads has quietly frozen its public developer API for years.",
        "cross",
        "decision",
    ),
    (
        "After a long trial I switched my photo catalog from Lightroom Classic to Capture One because the tethered capture latency on my Sony A7 IV was measurably lower and the color science matched my editorial look.",
        "cross",
        "decision",
    ),
    (
        "I decided to cancel my Sonos subscription to Sonos Radio HD and route Tidal Connect directly to the speakers instead, because I never touched the Sonos-only stations and the audio quality was equivalent.",
        "cross",
        "decision",
    ),
    (
        "For the living room we picked an LG C3 OLED over a Samsung S90C because LG's WebOS exposes a local HDMI-CEC API that Home Assistant can drive, while Samsung's Tizen equivalent requires a cloud-connected account.",
        "cross",
        "decision",
    ),
    (
        "I decided to self-host Home Assistant on a Raspberry Pi 5 rather than subscribe to Nabu Casa from day one, because the local-only setup is sufficient for my automations and I can add the cloud tier later if needed.",
        "cross",
        "decision",
    ),
    (
        "I chose Logseq over Obsidian for my personal PKM because the outliner model fits how I actually take meeting notes, even though Obsidian's plugin ecosystem is considerably larger today.",
        "cross",
        "decision",
    ),
    (
        "We decided to replace Mint with Monarch Money after the Mint shutdown announcement rather than switch to YNAB, because the joint-account view and automatic rule learning matched our existing workflow with less friction.",
        "cross",
        "decision",
    ),
    (
        "I decided to stop using Amazon Subscribe and Save for laundry detergent and switched to a local grocery delivery app instead, because the shipping carbon and packaging volume outweighed the small convenience advantage.",
        "cross",
        "decision",
    ),
    (
        "We picked the Litter-Robot 4 with WiFi connectivity over the cheaper Litter-Robot 3 because the MQTT integration for Home Assistant lets us route cleaning-cycle failures directly into our notification channel without the vendor app.",
        "cross",
        "decision",
    ),
    (
        "I decided to irrigate the vegetable bed with a Rachio 3 controller over a Rain Bird ESP-TM2 because Rachio exposes a first-class webhook API that Home Assistant can drive without any cloud polling workaround.",
        "cross",
        "decision",
    ),
    (
        "I chose to pay for Tesla's Premium Connectivity for another year instead of relying only on Wi-Fi map updates, because the live traffic rerouting genuinely saves me time on my twice-weekly commute across the bay.",
        "cross",
        "decision",
    ),
    (
        "For the family movie server we decided to move from Plex to Jellyfin because Plex's recent account-linking changes made local-only streaming awkward and Jellyfin's Android TV client now renders our HDR library correctly.",
        "cross",
        "decision",
    ),
    (
        "I decided to publish my personal blog on Astro with a static build pipeline rather than continue on WordPress, because the CVE maintenance burden on self-hosted WordPress outweighed the convenience of the admin UI.",
        "cross",
        "decision",
    ),

    # ---------------- preference (15) ----------------
    (
        "I prefer letting my Apple Watch auto-detect outdoor runs over manually starting a workout in the Nike Run Club app, because the auto-pause and GPS lock on the watch are noticeably more reliable during cold mornings.",
        "cross",
        "preference",
    ),
    (
        "When meal-prepping on Sundays I prefer Paprika 3 over Mealime for recipe management, because Paprika's self-hosted sync and clean web clipper let me archive recipes from any food blog without vendor lock-in.",
        "cross",
        "preference",
    ),
    (
        "For long non-fiction I prefer reading on a Kobo Libra 2 rather than the Kindle Paperwhite, because the Kobo natively opens the EPUB files I buy directly from publishers without a Send-to-Kindle conversion step.",
        "cross",
        "preference",
    ),
    (
        "I prefer editing photos on an iPad Pro with Affinity Photo for travel work, because the Apple Pencil workflow for masking feels more natural to me than the same tooling on a Windows desktop with a Wacom tablet.",
        "cross",
        "preference",
    ),
    (
        "I like using Roon for home listening rather than Apple Music even on the same speakers, because Roon's metadata and room-correction DSP materially change how the system sounds on a lossless FLAC library.",
        "cross",
        "preference",
    ),
    (
        "For family co-op nights I prefer the Steam Deck docked to the TV over the Nintendo Switch, because the wider Steam library plus Proton compatibility means every game we already own is one click away.",
        "cross",
        "preference",
    ),
    (
        "My default for home automation dashboards is the Home Assistant iOS app on a wall-mounted old iPad rather than a Google Nest Hub, because I keep all presence and voice logic local rather than routed through the cloud.",
        "cross",
        "preference",
    ),
    (
        "When capturing meeting notes from reading I prefer Readwise Reader over Matter, because the Readwise highlight export pipeline lands cleanly in my Obsidian vault without a second automation to massage the Markdown.",
        "cross",
        "preference",
    ),
    (
        "I prefer tracking every household expense in a shared Google Sheet linked to Tiller Money over a full app like YNAB, because the spreadsheet gives my partner and me direct control over categories and running totals.",
        "cross",
        "preference",
    ),
    (
        "For buying everyday goods I prefer the Instacart app on iOS to the Amazon Fresh website, because the substitution flow is more transparent and the delivery driver actually texts me through the app without a relay number.",
        "cross",
        "preference",
    ),
    (
        "I prefer Tractive GPS trackers over Apple AirTags for our dogs, because Tractive uses LTE-M for live location and the AirTag network only returns a fix when a stranger's iPhone happens to walk past the dog.",
        "cross",
        "preference",
    ),
    (
        "For tracking seed-starting dates in the greenhouse I prefer the Seedtime app on Android over a paper calendar, because the push notifications for transplant windows sync to my Google Calendar without an extra copy step.",
        "cross",
        "preference",
    ),
    (
        "I prefer controlling my Model 3 through the native Tesla app rather than through Siri shortcuts, because the shortcut path goes through Apple's servers and introduces a lag of several seconds for preconditioning.",
        "cross",
        "preference",
    ),
    (
        "For late-night movies I prefer the Apple TV 4K over the LG webOS built-in apps, because the Apple TV handles 24 frames per second content correctly and the webOS interface injects motion interpolation I cannot fully disable.",
        "cross",
        "preference",
    ),
    (
        "When drafting blog posts I prefer iA Writer on macOS over Ulysses, because iA Writer treats files as plain Markdown on disk and I can commit the same files into my Hugo site's content directory without any export dance.",
        "cross",
        "preference",
    ),

    # ---------------- problem (15) ----------------
    (
        "My Garmin Fenix 7 stopped syncing workouts to Strava last weekend, because the Garmin Connect iOS app silently lost its OAuth link to Strava after the latest TestFlight build reset my third-party authorizations.",
        "cross",
        "problem",
    ),
    (
        "Our Anova sous-vide cooker has been disconnecting from the 5 GHz Wi-Fi mid-cook, and the vendor firmware only supports 2.4 GHz, so the Eero mesh is silently steering the device onto a band it cannot actually use.",
        "cross",
        "problem",
    ),
    (
        "My Kindle Paperwhite started failing to render a specific sideloaded EPUB after I converted it with Calibre, because the KFX conversion plugin emitted an unsupported font descriptor that the Kindle's reader silently rejects.",
        "cross",
        "problem",
    ),
    (
        "The Sony A7 IV is refusing to connect to the Creators' App on my Pixel 8 for remote capture, and the pairing fails whenever the phone is on the Pixel VPN because the discovery relies on mDNS traffic that the VPN intercepts.",
        "cross",
        "problem",
    ),
    (
        "My Sonos Arc has been dropping out of the living room group for a few seconds several times per evening, and the pattern correlates exactly with the smart plug on the same circuit switching the floor lamp.",
        "cross",
        "problem",
    ),
    (
        "My Steam Deck refuses to wake from sleep when a specific Bluetooth controller is paired, because the controller's firmware advertises a rapid wake event that triggers the Deck's power manager before the kernel finishes resuming.",
        "cross",
        "problem",
    ),
    (
        "The Aqara door sensor on the front door keeps dropping off the Zigbee network, because the nearest Ikea Tradfri repeater was replaced and the mesh routing table has not converged to the new topology for almost a week.",
        "cross",
        "problem",
    ),
    (
        "My Obsidian vault's Dataview queries have been returning stale results on the iPad app, because the iOS Obsidian file indexer does not watch iCloud Drive changes until the Files app is opened to the vault folder at least once.",
        "cross",
        "problem",
    ),
    (
        "Monarch Money has been double-counting a recurring Netflix charge on my credit card for the past two months, because the Plaid connector is returning both a pending and a posted transaction without reconciling them correctly.",
        "cross",
        "problem",
    ),
    (
        "Amazon keeps canceling my Subscribe and Save order for cat food at the last minute, because the default payment method expired and the account flows silently retry the old card without surfacing the failure in the app.",
        "cross",
        "problem",
    ),
    (
        "The Litter-Robot 4 has been throwing cat-sensor faults every few cycles, because the infrared emitter window accumulated dust and the Home Assistant integration only surfaces the fault after it repeats three times in a row.",
        "cross",
        "problem",
    ),
    (
        "The Rachio irrigation controller skipped the evening schedule for the tomato bed, because the Weather Intelligence feature interpreted a thunderstorm forecast as enough rainfall even though the actual precipitation totaled under a millimeter.",
        "cross",
        "problem",
    ),
    (
        "My Tesla Model 3 is failing to wake up for scheduled TeslaMate polling at night, because the car firmware moved some endpoints to require fleet telemetry and the self-hosted integration has not yet migrated to that API path.",
        "cross",
        "problem",
    ),
    (
        "Jellyfin on the Nvidia Shield has been buffering in the middle of 4K HDR movies, because the Shield's built-in LAN driver negotiates only 100 megabit on the old Cat5 cable behind the TV despite the switch offering gigabit.",
        "cross",
        "problem",
    ),
    (
        "My Ghost blog started returning 502 responses on every publish, because the SQLite database reached the default WAL size ceiling and the Ghost process could not checkpoint while the Cloudflare tunnel kept long-lived connections open.",
        "cross",
        "problem",
    ),

    # ---------------- architecture (15) ----------------
    (
        "My home fitness stack pulls Garmin data through Garmin Connect, mirrors it into Apple Health via Health Sync, and then exports a weekly CSV to a Supabase Postgres that powers a personal Grafana dashboard on my NAS.",
        "cross",
        "architecture",
    ),
    (
        "The kitchen inventory system is a FastAPI service on a Raspberry Pi, reading barcodes through a handheld USB scanner, reconciling against a Grocy database, and pushing low-stock alerts to our shared iOS reminder list via Shortcuts.",
        "cross",
        "architecture",
    ),
    (
        "My reading pipeline chains Readwise Reader as capture, a Python script on a cron to fetch highlights through the Readwise API, and an Obsidian plugin that writes per-book Markdown notes into a dated folder in my vault.",
        "cross",
        "architecture",
    ),
    (
        "My photography workflow is organized as an ingest service on a Synology NAS that watches a memory card reader, invokes ExifTool to normalize metadata, and forwards new RAW files to Capture One via a Syncthing share.",
        "cross",
        "architecture",
    ),
    (
        "My home audio architecture uses a Roon Core running on an Intel NUC, serving Roon Ready endpoints in three rooms over wired Ethernet, with a Qobuz streaming account bridged through Roon for cloud content playback.",
        "cross",
        "architecture",
    ),
    (
        "The game-streaming setup runs Sunshine on my desktop as the host, Moonlight on the Steam Deck as the client, and a dedicated VLAN on the Unifi network carries the stream to avoid interference with the rest of the household.",
        "cross",
        "architecture",
    ),
    (
        "The home automation core runs Home Assistant in a Docker container on a Raspberry Pi 5, with a Zigbee2MQTT bridge on a separate Sonoff coordinator and an MQTT broker that also serves occupancy events to my Grafana stack.",
        "cross",
        "architecture",
    ),
    (
        "My personal knowledge management architecture keeps Obsidian as the authoring surface, a Syncthing cluster replicating the vault across three devices, and a nightly job that snapshots the vault into a restic repository on Backblaze B2.",
        "cross",
        "architecture",
    ),
    (
        "Our household budgeting stack uses Monarch Money as the transaction aggregator, a webhook exporter to Google Sheets for weekly review, and an IFTTT applet that files any transaction over five hundred dollars into a shared Todoist inbox.",
        "cross",
        "architecture",
    ),
    (
        "My grocery ordering flow starts in a shared Paprika recipe list, a Siri shortcut turns that list into an Instacart cart, and a Tasker routine on my Pixel logs the completed order into a Notion database for cost tracking.",
        "cross",
        "architecture",
    ),
    (
        "The pet-care architecture combines a Sure Petcare hub for door events, a Litter-Robot 4 reporting cycles over MQTT, and a single Node-RED flow that correlates both streams into a weekly wellness summary in Home Assistant.",
        "cross",
        "architecture",
    ),
    (
        "My greenhouse runs a LoRaWAN sensor network feeding The Things Network, which forwards payloads through a Mosquitto broker into InfluxDB, and Grafana alerts me through Pushover when soil moisture drops below a crop-specific threshold.",
        "cross",
        "architecture",
    ),
    (
        "The smart-car integration stack has TeslaMate polling the owner API into a Postgres database, a Node-RED flow translating charge events into Home Assistant sensors, and a Shortcuts automation that preheats the cabin at a scheduled time.",
        "cross",
        "architecture",
    ),
    (
        "Our home theater architecture places a Jellyfin server on an Unraid box with GPU transcoding, a dedicated cache drive for active media, and a reverse proxy in Nginx Proxy Manager that exposes the interface over Tailscale only.",
        "cross",
        "architecture",
    ),
    (
        "My personal blogging stack is an Astro project built by GitHub Actions on every push, deployed to Cloudflare Pages, and a scheduled Cloudflare Worker regenerates the RSS feed whenever the Ghost CMS webhook reports a new post.",
        "cross",
        "architecture",
    ),

    # ---------------- milestone (15) ----------------
    (
        "I finally closed my first full marathon training block last Sunday, and Garmin Connect recorded four hundred and eighty kilometers across sixteen weeks without a single missed long run logged on the Fenix 7.",
        "cross",
        "milestone",
    ),
    (
        "We completed our kitchen renovation this weekend, and the Breville Oracle Touch made its first espresso on the new counter while the Home Assistant energy dashboard started logging the circuit draw with the updated CT clamp.",
        "cross",
        "milestone",
    ),
    (
        "I hit my fifty-books-in-a-year reading goal last night, and the StoryGraph export finally passed the annual challenge marker after I finished the final essay collection I had queued in the Kindle app since January.",
        "cross",
        "milestone",
    ),
    (
        "I shipped the first printed photo book from my family archive this week, generated in Lightroom Classic and printed through Artifact Uprising after a full weekend of color-checking on the calibrated BenQ display.",
        "cross",
        "milestone",
    ),
    (
        "The home listening room project finished this week, with a pair of KEF LS50 Metas, a REL T7x subwoofer, and a Roon Nucleus all commissioned on the dedicated circuit and room-corrected through Dirac Live on a miniDSP.",
        "cross",
        "milestone",
    ),
    (
        "I completed my first hundred-hour run of Baldur's Gate 3 on the Steam Deck this week, and the cloud save successfully transferred back to the desktop for the post-game content through Steam Cloud's automatic sync.",
        "cross",
        "milestone",
    ),
    (
        "The whole-house Matter migration finished this weekend, and the last legacy Hue bridge was decommissioned after I successfully moved every bulb to the Aqara M3 hub running Thread and Matter controllers natively.",
        "cross",
        "milestone",
    ),
    (
        "I crossed the one-thousand-note mark in my Obsidian vault this morning, and the Dataview summary now reports four years of continuous daily-note coverage synced cleanly across my laptop, phone, and backup NAS.",
        "cross",
        "milestone",
    ),
    (
        "We finally paid off the last credit card this month, and Monarch Money's debt dashboard officially dropped to zero after the final payment cleared through the Chase connector early this morning.",
        "cross",
        "milestone",
    ),
    (
        "I completed my first full year of grocery deliveries through Instacart this week, and the annual report in the app showed I saved roughly ninety hours compared to my previous pattern of in-store shopping on Saturdays.",
        "cross",
        "milestone",
    ),
    (
        "Our rescue dog finished his GPS-tracked recall training program this weekend, and the Tractive app logged the first off-leash hike where his live location never left the polygon I drew around the trail network.",
        "cross",
        "milestone",
    ),
    (
        "The first tomato harvest from the smart garden came in this week, and the Home Assistant long-term statistics confirmed we hit the moisture-temperature envelope consistently for the full ten-week growing window tracked in InfluxDB.",
        "cross",
        "milestone",
    ),
    (
        "I completed the first fifty-thousand-kilometer service interval on the Model 3 this week, and TeslaMate's report showed cumulative regen captured roughly nine hundred kilowatt hours of energy that never touched the brake pads.",
        "cross",
        "milestone",
    ),
    (
        "We finished migrating the family media library from Plex to Jellyfin this weekend, and every relative's Roku was re-provisioned with the Jellyfin client and tested against a calibration HDR clip before the old server was shut down.",
        "cross",
        "milestone",
    ),
    (
        "I published the hundredth post on my personal blog this morning, and the Cloudflare analytics dashboard crossed one million lifetime pageviews on the same Astro deployment that replaced WordPress roughly two years ago.",
        "cross",
        "milestone",
    ),

    # ---------------- reference (10) — each has a real citable source ----------------
    (
        "Per the Apple Health Developer documentation for HKWorkout, workouts recorded by watchOS 10 on the Apple Watch are automatically aggregated into the Fitness summary, which is how Strava pulls its mirrored workouts on iOS.",
        "cross",
        "reference",
    ),
    (
        "According to the Anova Precision Cooker user guide published by Anova Applied Electronics, the Bluetooth Low Energy range is specified as up to ten meters indoors, which explains why our kitchen-to-bedroom connection drops out.",
        "cross",
        "reference",
    ),
    (
        "Per Amazon's Kindle Direct Publishing guidelines section on supported formats, sideloaded EPUB files are automatically converted to KF8 when delivered through Send to Kindle, as documented on the official KDP help pages.",
        "cross",
        "reference",
    ),
    (
        "According to Adobe's Lightroom Classic help page on tethered capture, the Sony A7 IV is supported over USB-C through the native tethering plugin as of Lightroom Classic version 12.0, released in October 2022.",
        "cross",
        "reference",
    ),
    (
        "Per the Sonos developer documentation for S2, the Sonos Connect API exposes a playback control surface over local HTTP on port 1400, which is the endpoint my Node-RED flows use for group management at home.",
        "cross",
        "reference",
    ),
    (
        "According to Nintendo's Switch Online FAQ published on their official support site, specific titles including Animal Crossing New Horizons are excluded from Save Data Cloud backup, as the publisher explicitly notes in the compatibility table.",
        "cross",
        "reference",
    ),
    (
        "Per the Matter 1.2 specification published by the Connectivity Standards Alliance, Thread border routers are required to advertise their presence through SRP, which is why my Aqara M3 shows up in the Home Assistant Matter integration.",
        "cross",
        "reference",
    ),
    (
        "According to the Obsidian official help page on iCloud sync, Obsidian on iOS relies on Apple's file coordination APIs, and the help explicitly warns that iCloud Drive updates may require opening the Files app to trigger indexing.",
        "cross",
        "reference",
    ),
    (
        "Per the Plaid developer documentation on Transactions endpoints, both pending and posted transactions can be returned for the same underlying event, which is the behavior Monarch's support article on duplicate charges references directly.",
        "cross",
        "reference",
    ),
    (
        "According to Tesla's Fleet API migration notice published on the Tesla developer portal, several vehicle command endpoints moved from the owner API to the Fleet API effective 2024, which TeslaMate's GitHub issues track as an active migration.",
        "cross",
        "reference",
    ),
]


def emit() -> int:
    assert len(ROWS) == 100, f"expected 100 rows, got {len(ROWS)}"
    counts: dict[str, int] = {}
    for _, _, mt in ROWS:
        counts[mt] = counts.get(mt, 0) + 1
    expected = {
        "fact": 15,
        "decision": 15,
        "preference": 15,
        "problem": 15,
        "architecture": 15,
        "milestone": 15,
        "reference": 10,
    }
    assert counts == expected, f"distribution mismatch: {counts} != {expected}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, domain, mt) in enumerate(ROWS, start=1):
            row_id = f"class-{ID_OFFSET + i:05d}"
            f.write(
                json.dumps(
                    {"id": row_id, "domain": domain, "text": text, "memory_type": mt},
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
