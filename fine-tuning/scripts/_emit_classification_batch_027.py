"""One-off emitter for classification top-up batch-027 — short_ambiguous mode, cross-domain slice.

Writes 100 rows to data/v2/classification/batch_027.tmp.jsonl with ids class-02601..02700.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_027.tmp.jsonl"
ID_OFFSET = 2600

# (text, domain, memory_type) — no pair_id
# All rows: domain=cross, 3-12 words, mixing personal-life artefacts with tech/software.
ROWS: list[tuple[str, str, str]] = [
    # --- fact (~14) ---
    ("Strava syncs automatically with Apple Health.", "cross", "fact"),
    ("Paprika stores recipes offline on iOS.", "cross", "fact"),
    ("Kindle books sync last-read page via Whispersync.", "cross", "fact"),
    ("Spotify Wrapped drops every December.", "cross", "fact"),
    ("Steam Deck runs SteamOS on Arch Linux.", "cross", "fact"),
    ("Hue bridge supports up to 50 bulbs.", "cross", "fact"),
    ("Obsidian vaults are plain markdown folders.", "cross", "fact"),
    ("YNAB uses zero-based budgeting.", "cross", "fact"),
    ("Lightroom presets are .xmp files.", "cross", "fact"),
    ("Garmin watches export activities as FIT files.", "cross", "fact"),
    ("Notion databases support rollup columns.", "cross", "fact"),
    ("Peloton classes stream at 30 frames per second.", "cross", "fact"),
    ("PlantIn identifies species from phone photos.", "cross", "fact"),
    ("Sonos speakers discover each other over mDNS.", "cross", "fact"),

    # --- decision (~14) ---
    ("Moving my recipes from Paprika to Notion.", "cross", "decision"),
    ("Switching from Spotify to Apple Music next month.", "cross", "decision"),
    ("Going with Obsidian instead of Roam for notes.", "cross", "decision"),
    ("Ditching MyFitnessPal for Cronometer.", "cross", "decision"),
    ("Replacing the Echo with a HomePod mini.", "cross", "decision"),
    ("We'll use YNAB instead of a spreadsheet.", "cross", "decision"),
    ("Swapping Kindle for Kobo going forward.", "cross", "decision"),
    ("Migrating photos from iCloud to Immich.", "cross", "decision"),
    ("Picking Todoist over Things for cross-platform sync.", "cross", "decision"),
    ("Switching Garmin for an Apple Watch Ultra.", "cross", "decision"),
    ("Dropping Peloton for a Zwift setup.", "cross", "decision"),
    ("Moving the smart plugs to Home Assistant.", "cross", "decision"),
    ("Going with Plex instead of Jellyfin again.", "cross", "decision"),
    ("Consolidating all budgets into Monarch Money.", "cross", "decision"),

    # --- preference (~14) ---
    ("I prefer Kindle over physical books.", "cross", "preference"),
    ("I like Spotify's algorithm better than Apple Music's.", "cross", "preference"),
    ("Prefer Obsidian to Evernote for daily notes.", "cross", "preference"),
    ("I like warm white over daylight bulbs.", "cross", "preference"),
    ("Prefer mechanical keyboards for gaming.", "cross", "preference"),
    ("I like Strava segments over plain GPS tracks.", "cross", "preference"),
    ("Prefer shooting RAW over JPEG.", "cross", "preference"),
    ("I like Notion templates for meal planning.", "cross", "preference"),
    ("Prefer Monarch Money to Mint.", "cross", "preference"),
    ("I like Zwift over outdoor rides in winter.", "cross", "preference"),
    ("Prefer AeroPress to espresso machines.", "cross", "preference"),
    ("I like Audible for long commutes.", "cross", "preference"),
    ("Prefer Libby over buying ebooks.", "cross", "preference"),
    ("I like Letterboxd for tracking films.", "cross", "preference"),

    # --- problem (~14) ---
    ("Hue bulbs flicker after firmware update.", "cross", "problem"),
    ("Strava drops GPS in tall buildings.", "cross", "problem"),
    ("Spotify Connect keeps dropping my speakers.", "cross", "problem"),
    ("Kindle won't sync last page across devices.", "cross", "problem"),
    ("Notion search misses tagged pages.", "cross", "problem"),
    ("Robot vacuum keeps getting stuck under the sofa.", "cross", "problem"),
    ("Lightroom catalog corrupts on cloud sync.", "cross", "problem"),
    ("Peloton tablet reboots mid-class.", "cross", "problem"),
    ("Apple Watch battery dies by noon now.", "cross", "problem"),
    ("Home Assistant loses Zigbee devices overnight.", "cross", "problem"),
    ("YNAB import fails on the new bank.", "cross", "problem"),
    ("Switchbot thermostat drifts by two degrees.", "cross", "problem"),
    ("Sonos refuses to group after router reboot.", "cross", "problem"),
    ("Plex stutters on 4K HDR remux files.", "cross", "problem"),

    # --- reference (~14) ---
    ("Recipe is saved in Paprika under 'weeknight'.", "cross", "reference"),
    ("Training plan is in the Garmin Connect app.", "cross", "reference"),
    ("Budget lives in the YNAB 2026 profile.", "cross", "reference"),
    ("Lightroom presets are in the Mastin pack.", "cross", "reference"),
    ("Packing list is in Notion under 'travel'.", "cross", "reference"),
    ("Smart home flows documented in Home Assistant.", "cross", "reference"),
    ("Book notes are in Readwise export.", "cross", "reference"),
    ("Garden log is in the Planta app.", "cross", "reference"),
    ("Workout history is in Strava's training calendar.", "cross", "reference"),
    ("Playlist is shared on Spotify as 'focus'.", "cross", "reference"),
    ("Movie list tracked on Letterboxd as 'watchlist'.", "cross", "reference"),
    ("Scan is saved in the Paperless-ngx inbox.", "cross", "reference"),
    ("Receipts are archived in the 1Password vault.", "cross", "reference"),
    ("Album sits in the Immich shared library.", "cross", "reference"),

    # --- architecture (~14) ---
    ("Hue bridge talks Zigbee, phone talks WiFi.", "cross", "architecture"),
    ("Home Assistant sits between sensors and automations.", "cross", "architecture"),
    ("Sonos speakers mesh over a private WiFi channel.", "cross", "architecture"),
    ("Garmin syncs to Connect, Connect pushes to Strava.", "cross", "architecture"),
    ("Obsidian vault syncs via iCloud to all devices.", "cross", "architecture"),
    ("Immich server runs on NAS, phone uploads nightly.", "cross", "architecture"),
    ("Plex server streams to AppleTV over local network.", "cross", "architecture"),
    ("YNAB pulls transactions via Plaid.", "cross", "architecture"),
    ("Switchbot hub bridges Bluetooth devices to cloud.", "cross", "architecture"),
    ("Lightroom catalog sits on SSD, previews on cloud.", "cross", "architecture"),
    ("Readwise ingests Kindle, Pocket, and Instapaper.", "cross", "architecture"),
    ("Zwift pairs sensors over ANT+ and Bluetooth.", "cross", "architecture"),
    ("Paperless watches a Syncthing folder for new scans.", "cross", "architecture"),
    ("Eufy camera records locally, alerts push to phone.", "cross", "architecture"),

    # --- milestone (~16 to reach 100) ---
    ("Hit 1000 kilometres on Strava this year.", "cross", "milestone"),
    ("Finished importing every recipe into Paprika.", "cross", "milestone"),
    ("Closed all three Apple Watch rings for 100 days.", "cross", "milestone"),
    ("Migrated 20k photos from iCloud to Immich.", "cross", "milestone"),
    ("Logged my 500th book in Goodreads.", "cross", "milestone"),
    ("Hit zero inbox in Todoist for the first time.", "cross", "milestone"),
    ("Finished the Couch to 5K program on Nike Run.", "cross", "milestone"),
    ("Got the last badge on Duolingo Spanish tree.", "cross", "milestone"),
    ("Reached Platinum on my Peloton leaderboard.", "cross", "milestone"),
    ("Completed the smart home migration to Home Assistant.", "cross", "milestone"),
    ("Paid off the last card in YNAB.", "cross", "milestone"),
    ("Finished cataloguing vinyl in Discogs.", "cross", "milestone"),
    ("Hit 10k streak days on Wordle.", "cross", "milestone"),
    ("Completed the Zwift Tour de Zwift series.", "cross", "milestone"),
    ("Finished digitising all old family photos.", "cross", "milestone"),
    ("Published my first Obsidian Publish site.", "cross", "milestone"),
]


def emit() -> int:
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
