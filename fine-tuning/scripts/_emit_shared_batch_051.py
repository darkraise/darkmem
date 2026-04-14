"""One-off emitter for shared-base batch-051 — cross domain.

Slice: travel planning meets tech (tooling for trips, lodging, transit). Writes
50 rows to data/v2/shared/batch_051.tmp.jsonl with ids shared-02501..02550. The
main session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_051.tmp.jsonl"
ID_OFFSET = 2500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped Google Flights for Kiwi.com when the Lisbon trip turned into a multi-city open-jaw with a train segment that the Google search refused to price.", "decision", "cross", False,
     [("Google Flights", "service"), ("Kiwi.com", "service"), ("Lisbon", "place")],
     [("Kiwi.com", "Google Flights", "REPLACES")],
     "which flight search tool took over for the messy Portugal itinerary",
     "multi city open jaw train leg flight meta search combinability"),
    # --- 2 ---
    ("Prefers ExpertFlyer over SeatSpy for award-seat hunting because the fare-class rules layer catches United Polaris saver space that SeatSpy's crawler misses.", "preference", "cross", False,
     [("ExpertFlyer", "service"), ("SeatSpy", "service"), ("United Polaris", "service")],
     [("ExpertFlyer", "SeatSpy", "PREFERS")],
     "which award tool wins when chasing business-class availability and why",
     "award seat fare class rules saver space premium cabin hunt"),
    # --- 3 ---
    ("The 2026-05-17 Tokyo trip uses SmartEX for the Shinkansen reservations because the Japan Rail Pass no longer covers the Nozomi and SmartEX handles the IC card tap at the gate.", "architecture", "cross", False,
     [("2026-05-17", "date"), ("Tokyo", "place"), ("SmartEX", "service"), ("Shinkansen", "infrastructure"), ("Japan Rail Pass", "service"), ("Nozomi", "service")],
     [("SmartEX", "Japan Rail Pass", "REPLACES")],
     "how do the bullet train reservations get booked for the spring Japan trip",
     "shinkansen reservation app IC card gate tap rail pass limitation"),
    # --- 4 ---
    ("Moved the shared trip planning from a Google Sheet to Wanderlog on 2026-03-04 once Mei got tired of manually pasting map pins for the Iceland ring-road itinerary.", "milestone", "cross", False,
     [("Google Sheet", "service"), ("Wanderlog", "service"), ("2026-03-04", "date"), ("Mei", "person"), ("Iceland", "place")],
     [("Wanderlog", "Google Sheet", "REPLACES")],
     "when did the Iceland planning leave the spreadsheet and who pushed for it",
     "itinerary app migration map pins ring road shared planning tired"),
    # --- 5 ---
    ("Airalo covers the data eSIM for quick city hops while Holafly handles the month-long Thailand stay because Holafly's unlimited tier doesn't throttle in Chiang Mai.", "decision", "cross", False,
     [("Airalo", "service"), ("Holafly", "service"), ("Thailand", "place"), ("Chiang Mai", "place")],
     [("Holafly", "Airalo", "PREFERS")],
     "which travel eSIM provider handles which kind of trip this year",
     "eSIM short hop long stay unlimited data throttle southeast asia"),
    # --- 6. noise ---
    ("Give me a second to think about that.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Citymapper beat Google Maps for the London transit week because the tube-closure overlays caught the weekend Jubilee line works before either Transport for London alert fired.", "decision", "cross", False,
     [("Citymapper", "service"), ("Google Maps", "service"), ("London", "place"), ("Jubilee", "infrastructure"), ("Transport for London", "organization")],
     [("Citymapper", "Google Maps", "REPLACES")],
     "which transit app was better for the London week and why",
     "transit routing tube closure overlay weekend engineering works alert"),
    # --- 8 ---
    ("Pre-downloaded the Organic Maps region pack for the Dolomites hike because the AllTrails offline tier still pings the server for the route summary.", "architecture", "cross", False,
     [("Organic Maps", "service"), ("Dolomites", "place"), ("AllTrails", "service")],
     [("Organic Maps", "AllTrails", "PREFERS")],
     "how did the Dolomites hiking plan handle zero reception",
     "offline map region pack hiking trail app server ping fallback"),
    # --- 9 ---
    ("The Deutsche Bahn Navigator app replaced Trainline on the phone once the Bahncard 50 discount stopped applying to Trainline-booked ICE tickets.", "decision", "cross", False,
     [("Deutsche Bahn Navigator", "service"), ("Trainline", "service"), ("Bahncard 50", "service"), ("ICE", "service")],
     [("Deutsche Bahn Navigator", "Trainline", "REPLACES")],
     "why did the rail booking app change for German trips",
     "rail app swap discount card eligibility intercity express fare"),
    # --- 10 ---
    ("Splitwise kept the Kyoto trip expenses tidy across four travelers because converting JPY receipts through Wise's card statement matched Splitwise's FX rate exactly.", "architecture", "cross", False,
     [("Splitwise", "service"), ("Kyoto", "place"), ("JPY", "concept"), ("Wise", "service")],
     [("Splitwise", "Wise", "COMMUNICATES_WITH")],
     "how did the Kyoto expenses stay balanced across four travelers",
     "group expense split foreign currency card statement FX rate match"),
    # --- 11 ---
    ("Wise debit replaced Revolut as the primary travel card on 2026-01-22 because Revolut's weekend FX markup burned a hundred euros on the Prague Christmas-markets weekend.", "decision", "cross", False,
     [("Wise", "service"), ("Revolut", "service"), ("2026-01-22", "date"), ("Prague", "place")],
     [("Wise", "Revolut", "REPLACES")],
     "when did the travel debit card get swapped and what triggered it",
     "travel card migration weekend FX markup christmas markets currency"),
    # --- 12 ---
    ("PackPoint generated the base checklist for the Patagonia trek but the custom gear list moved into a Google Keep note because PackPoint couldn't track loaned crampons.", "architecture", "cross", False,
     [("PackPoint", "service"), ("Patagonia", "place"), ("Google Keep", "service"), ("crampons", "hobby")],
     [("Google Keep", "PackPoint", "PREFERS")],
     "how did the packing list actually get maintained for the Patagonia hike",
     "packing list template custom gear tracking loaner equipment notes app"),
    # --- 13 ---
    ("Frustration boiled over when Booking.com's Genius 15% discount silently dropped for the Porto hotel on 2026-02-14 and the refund dispute took three weeks.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Booking.com", "service"), ("Porto", "place"), ("2026-02-14", "date")],
     [],
     "what went wrong with the Valentine's weekend hotel booking in Portugal",
     "genius loyalty discount drop refund dispute delay hotel reservation"),
    # --- 14 ---
    ("Mobile Passport Control replaced the paper Global Entry kiosk on the JFK re-entry after the app pre-filed the customs form before the plane hit the gate.", "decision", "cross", False,
     [("Mobile Passport Control", "service"), ("Global Entry", "service"), ("JFK", "place")],
     [("Mobile Passport Control", "Global Entry", "REPLACES")],
     "how does re-entry at New York skip the paper customs form now",
     "customs form pre file mobile app gate arrival expedited re entry"),
    # --- 15 ---
    ("Prefers Rome2Rio over Google Maps for the planning phase because Rome2Rio surfaces the overnight ferry from Bari to Patras that Google buries under flight results.", "preference", "cross", False,
     [("Rome2Rio", "service"), ("Google Maps", "service"), ("Bari", "place"), ("Patras", "place")],
     [("Rome2Rio", "Google Maps", "PREFERS")],
     "which multi-modal planner found the overnight Mediterranean ferry",
     "multi modal route planner ferry option discovery adriatic crossing"),
    # --- 16 ---
    ("Timeshifter's jet-lag plan for the 2026-06-10 Sydney flight told me to shift bedtime a full hour earlier four nights out, and for the first time the first day in country wasn't wasted.", "fact", "cross", False,
     [("Timeshifter", "service"), ("2026-06-10", "date"), ("Sydney", "place")],
     [],
     "what kept the first day of the Sydney trip from being lost to jet lag",
     "jet lag plan app light exposure bedtime shift long haul recovery"),
    # --- 17 ---
    ("Amex Travel replaced the Chase Ultimate Rewards portal for the Greece honeymoon because the Fine Hotels resort credit actually stacked with the Hilton Aspire benefits at the Santorini property.", "decision", "cross", False,
     [("Amex Travel", "service"), ("Chase Ultimate Rewards", "service"), ("Greece", "place"), ("Hilton Aspire", "service"), ("Santorini", "place")],
     [("Amex Travel", "Chase Ultimate Rewards", "REPLACES")],
     "why did the honeymoon booking go through the Amex portal instead of Chase",
     "travel portal swap resort credit card benefit stacking hotel perks"),
    # --- 18 ---
    ("Paris Navigo Easy on Apple Wallet replaced the paper carnet of 10 metro tickets because the tap-and-go at Châtelet actually worked on the iPhone even with the battery reserve kicked in.", "decision", "cross", False,
     [("Navigo Easy", "service"), ("Apple Wallet", "service"), ("Paris", "place"), ("Châtelet", "place"), ("iPhone", "infrastructure")],
     [("Navigo Easy", "Apple Wallet", "DEPLOYED_ON")],
     "how did the Paris metro fare move off of paper tickets this trip",
     "metro transit mobile wallet tap reserve battery fare card"),
    # --- 19 ---
    ("Anki decks on the iPad synced over iCloud covered 800 Japanese cards during the 2026-05-17 Tokyo flight, and the cards queued up offline finished the moment the Wi-Fi came back at Haneda.", "architecture", "cross", False,
     [("Anki", "tool"), ("iPad", "infrastructure"), ("iCloud", "service"), ("2026-05-17", "date"), ("Tokyo", "place"), ("Haneda", "place")],
     [("Anki", "iCloud", "USES")],
     "how did the language flashcards keep progressing during the Pacific flight",
     "spaced repetition offline review sync resume long haul vocabulary"),
    # --- 20 ---
    ("Curiosity piqued the first time the Rick Steves audio guide auto-advanced through the Borghese Gallery in Rome in sync with the Bluetooth-beacon positioning.", "fact", "cross", False,
     [("Curiosity", "emotion"), ("Rick Steves", "service"), ("Borghese Gallery", "place"), ("Rome", "place"), ("Bluetooth", "protocol")],
     [("Rick Steves", "Bluetooth", "USES")],
     "what audio tool actually made the Borghese visit feel paced correctly",
     "museum audio guide auto advance indoor positioning beacon sync"),
    # --- 21 ---
    ("The Immich selective-sync mode keeps the roaming phone from burning the Holafly data budget while still uploading starred photos from the Marrakech riad every night.", "architecture", "cross", False,
     [("Immich", "service"), ("Holafly", "service"), ("Marrakech", "place")],
     [("Immich", "Holafly", "USES")],
     "how do photos still back up abroad without torching the eSIM plan",
     "selective photo sync roaming data budget favorite upload self hosted"),
    # --- 22 ---
    ("The Polar H10 GPX export fed a bike-rental route into Komoot for the Mallorca training week because Komoot's turn-by-turn on the Garmin beat the Polar watch's barebones prompts.", "architecture", "cross", False,
     [("Polar H10", "infrastructure"), ("GPX", "concept"), ("Komoot", "service"), ("Mallorca", "place"), ("Garmin", "infrastructure")],
     [("Komoot", "Polar H10", "USES"), ("Komoot", "Garmin", "DEPLOYED_ON")],
     "how did the Mallorca cycling week handle turn-by-turn navigation",
     "gpx export cycling route app handoff bike computer guidance island"),
    # --- 23 ---
    ("World Nomads processed the 2026-02-07 trip-interruption claim for the Seoul flight cancellation in nine days after the PDF receipts from Agoda were attached through the portal.", "milestone", "cross", False,
     [("World Nomads", "service"), ("2026-02-07", "date"), ("Seoul", "place"), ("PDF", "concept"), ("Agoda", "service")],
     [],
     "when did the Seoul cancellation claim actually get paid out",
     "travel insurance claim interruption flight cancellation portal payout"),
    # --- 24 ---
    ("Switched the dive-trip log from a paper logbook to the Subsurface app because the Diverse gas-mix export for the Egypt liveaboard needed to feed into my shop's fill records.", "decision", "cross", False,
     [("Subsurface", "tool"), ("Egypt", "place"), ("Diverse", "concept")],
     [],
     "why did the scuba logbook go digital for the Red Sea trip",
     "dive log digitization gas mix export liveaboard shop integration"),
    # --- 25 ---
    ("Google Translate conversation mode on the Pixel 9 carried the Hanoi street-food ordering because the Vietnamese two-way translation ran entirely on-device and didn't need the hostel Wi-Fi.", "architecture", "cross", False,
     [("Google Translate", "service"), ("Pixel 9", "infrastructure"), ("Hanoi", "place"), ("Vietnamese", "language")],
     [("Google Translate", "Pixel 9", "DEPLOYED_ON")],
     "how did the street-food ordering work without dependable data",
     "conversation translation on device offline two way speech street food"),
    # --- 26 ---
    ("Relief washed over me when the Nomad List filters finally surfaced a Lisbon co-working plan under 200 euros a month that matched the fiber-speed cutoff for the video calls.", "milestone", "cross", False,
     [("Relief", "emotion"), ("Nomad List", "service"), ("Lisbon", "place")],
     [],
     "what made the Lisbon co-working search actually end in a booking",
     "digital nomad filter coworking budget fiber speed threshold relief"),
    # --- 27 ---
    ("The Tokyo Metro app stays on the phone alongside Google Maps because the offline station-exit diagrams are the only thing that consistently gets me out at the correct side of Shinjuku.", "architecture", "cross", False,
     [("Tokyo Metro", "service"), ("Google Maps", "service"), ("Shinjuku", "place")],
     [("Tokyo Metro", "Google Maps", "PREFERS")],
     "which transit reference wins for navigating inside massive stations",
     "station exit diagram offline metro app wayfinding shinjuku complex"),
    # --- 28 ---
    ("HealthPassport replaced the paper vaccination card workflow for the 2026-03-29 Kenya trip once the yellow-fever certificate needed to be presented at the Nairobi arrivals desk.", "decision", "cross", False,
     [("HealthPassport", "service"), ("2026-03-29", "date"), ("Kenya", "place"), ("Nairobi", "place")],
     [],
     "how did the yellow fever certificate get presented at the Kenya border",
     "digital vaccination certificate border entry yellow fever arrivals"),
    # --- 29 ---
    ("Booking.com replaced Airbnb for the 2026-04-20 Buenos Aires stay after three Airbnb listings canceled within 48 hours of arrival and the free-cancellation hotel finally calmed the panic.", "milestone", "cross", False,
     [("Booking.com", "service"), ("Airbnb", "service"), ("2026-04-20", "date"), ("Buenos Aires", "place")],
     [("Booking.com", "Airbnb", "REPLACES")],
     "when did lodging swap for the Buenos Aires trip and why",
     "short term rental cancellation spree free cancellation hotel pivot"),
    # --- 30 ---
    ("The Strava route-builder plus a Wahoo Bolt handled the 2026-05-02 Cotswolds bike-packing loop because the Wahoo's GPX turn cues survived two full rainy days the iPhone bar mount didn't.", "architecture", "cross", False,
     [("Strava", "service"), ("Wahoo Bolt", "infrastructure"), ("2026-05-02", "date"), ("Cotswolds", "place"), ("GPX", "concept"), ("iPhone", "infrastructure")],
     [("Wahoo Bolt", "Strava", "USES")],
     "how did the rainy Cotswolds bikepacking navigation stay working",
     "route builder bike computer weatherproof navigation bikepacking loop"),
    # --- 31 ---
    ("Prefers Hipmunk-style agony sort on Matrix ITA over Skyscanner's cheapest-first default because the long-haul layover pain in Doha vs Istanbul actually shows up in the ranking.", "preference", "cross", False,
     [("Matrix ITA", "service"), ("Skyscanner", "service"), ("Doha", "place"), ("Istanbul", "place")],
     [("Matrix ITA", "Skyscanner", "PREFERS")],
     "which search ranking actually surfaces comfortable long-haul routings",
     "agony sort layover comfort metric flight search ranking preference"),
    # --- 32 ---
    ("The Roadtrippers pro subscription was worth it for the 2026-07-04 Pacific Coast Highway trip because the RV-friendly filter caught three low bridges that Google's truck-route overlay missed.", "decision", "cross", False,
     [("Roadtrippers", "service"), ("2026-07-04", "date"), ("Pacific Coast Highway", "place"), ("Google", "service")],
     [("Roadtrippers", "Google", "PREFERS")],
     "which road-trip tool earned its subscription on the California coast drive",
     "road trip planner RV filter low bridge clearance coastal highway"),
    # --- 33 ---
    ("Google Sheets with importHTML still beats every fare alert for long-lead SkyTeam award availability because the pull against the KLM calendar runs every ten minutes on a free App Script trigger.", "architecture", "cross", False,
     [("Google Sheets", "service"), ("importHTML", "command"), ("SkyTeam", "organization"), ("KLM", "organization"), ("App Script", "platform")],
     [("Google Sheets", "App Script", "USES")],
     "how does the long-lead award monitor stay current without a paid fare alert",
     "spreadsheet scraper schedule award alert airline calendar free quota"),
    # --- 34. noise ---
    ("Hmm, let me check my notes on that.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Mobile Passport Control's iOS pre-file broke on 2026-03-18 returning from Mexico City because the passport photo step rejected the dim airplane lighting three times in a row.", "problem", "cross", False,
     [("Mobile Passport Control", "service"), ("iOS", "infrastructure"), ("2026-03-18", "date"), ("Mexico City", "place")],
     [("Mobile Passport Control", "iOS", "DEPLOYED_ON")],
     "what tripped up the Mexico re-entry on the customs app that week",
     "passport photo capture failure cabin lighting rejection border app"),
    # --- 36 ---
    ("The Google Maps offline area for Hokkaido covered every onsen town except Noboribetsu because the download box didn't stretch south far enough and data was spotty at the ryokan.", "problem", "cross", False,
     [("Google Maps", "service"), ("Hokkaido", "place"), ("Noboribetsu", "place")],
     [],
     "which Hokkaido town fell outside the offline map and caused pain",
     "offline map download box coverage gap hot spring town connectivity"),
    # --- 37 ---
    ("Chase Sapphire Reserve's Priority Pass lounge filter replaced the LoungeBuddy search once LoungeBuddy started losing the Lisbon ANA lounge from its database.", "decision", "cross", False,
     [("Chase Sapphire Reserve", "service"), ("Priority Pass", "service"), ("LoungeBuddy", "service"), ("Lisbon", "place"), ("ANA", "organization")],
     [("Priority Pass", "LoungeBuddy", "REPLACES")],
     "which lounge-finder tool took over for airport lounge planning",
     "priority pass lounge locator swap database staleness airport perks"),
    # --- 38 ---
    ("The Gravitymark rental aggregator that my brother Julian built in Go on a Hetzner box beat both Plum Guide and Vrbo for the Sicily villa hunt in 2026.", "fact", "cross", False,
     [("Julian", "person"), ("Go", "language"), ("Hetzner", "organization"), ("Plum Guide", "service"), ("Vrbo", "service"), ("Sicily", "place")],
     [("Julian", "Go", "USES")],
     "what custom-built tool outperformed the usual vacation-rental sites for the Sicily villa",
     "custom aggregator rental search self hosted Go scraper villa hunt"),
    # --- 39 ---
    ("Prefers Uber over Bolt in Lisbon because the Amex Platinum credit only reimburses Uber in euros and the 15-dollar monthly stipend actually covered the Bairro Alto rides.", "preference", "cross", False,
     [("Uber", "service"), ("Bolt", "service"), ("Lisbon", "place"), ("Amex Platinum", "service"), ("Bairro Alto", "place")],
     [("Uber", "Bolt", "PREFERS")],
     "which rideshare won in Lisbon and why",
     "ride share choice card credit reimbursement monthly stipend city"),
    # --- 40 ---
    ("The 2026-02-24 customs delay at Heathrow ruined the connection to Edinburgh but TripIt Pro's auto-rebook pinged the BA alert before the gate agent's queue even formed.", "milestone", "cross", False,
     [("2026-02-24", "date"), ("Heathrow", "place"), ("Edinburgh", "place"), ("TripIt Pro", "service"), ("BA", "organization")],
     [("TripIt Pro", "BA", "COMMUNICATES_WITH")],
     "what caught the missed connection to Edinburgh before the gate agent did",
     "itinerary tracker disruption alert auto rebook airline mobile queue"),
    # --- 41 ---
    ("The Seat Alerts tool on ExpertFlyer pinged a Qatar Qsuites opening on the 2026-08-19 Doha flight at 3am my time, so the Alaska Mileage Plan booking went through before the award space died.", "milestone", "cross", False,
     [("Seat Alerts", "service"), ("ExpertFlyer", "service"), ("Qatar Qsuites", "service"), ("2026-08-19", "date"), ("Doha", "place"), ("Alaska Mileage Plan", "service")],
     [("Seat Alerts", "ExpertFlyer", "IS_A")],
     "how did the business-class Doha award actually get caught in time",
     "award space alert overnight notification partner program redemption"),
    # --- 42 ---
    ("Hotwire's opaque Hot Rate replaced the direct Marriott booking for the Denver layover night because the 4-star property came in at 60 dollars and the points were not worth spending.", "decision", "cross", False,
     [("Hotwire", "service"), ("Marriott", "organization"), ("Denver", "place")],
     [("Hotwire", "Marriott", "REPLACES")],
     "why did the Denver layover hotel get booked through the opaque channel",
     "opaque hotel booking layover night cash versus points savings"),
    # --- 43 ---
    ("The Windy app's wind-gust forecast canceled the 2026-05-09 Santorini ferry run a full day before the Ferryhopper app pulled the operator's cancellation notice.", "fact", "cross", False,
     [("Windy", "service"), ("2026-05-09", "date"), ("Santorini", "place"), ("Ferryhopper", "service")],
     [("Windy", "Ferryhopper", "PREFERS")],
     "what tipped off the Santorini ferry cancellation before the official notice",
     "wind gust forecast maritime cancellation lead time ferry booking"),
    # --- 44 ---
    ("Confusion hit at the Schiphol self-transfer when the KLM app couldn't re-issue the boarding pass because the Delta partner leg had already checked me in on paper at JFK.", "problem", "cross", False,
     [("Confusion", "emotion"), ("Schiphol", "place"), ("KLM", "organization"), ("Delta", "organization"), ("JFK", "place")],
     [],
     "what went wrong re-issuing the boarding pass on the Amsterdam transfer",
     "self transfer boarding pass reissue partner check in conflict"),
    # --- 45 ---
    ("The shared 2026-06-22 Croatia sailing itinerary lives in a Notion database because Wanderlog kept choking on the fourteen marina waypoints the charter captain sent over WhatsApp.", "architecture", "cross", False,
     [("2026-06-22", "date"), ("Croatia", "place"), ("Notion", "tool"), ("Wanderlog", "service"), ("WhatsApp", "service")],
     [("Notion", "Wanderlog", "REPLACES")],
     "where does the sailing itinerary live now that Wanderlog couldn't hold it",
     "charter sailing waypoints itinerary database migration whatsapp handoff"),
    # --- 46 ---
    ("Prefers the DJI Mini 4 Pro over the GoPro 13 for trip footage because Airdata UAV's flight-log import off the DJI actually pairs with the insurance-claim workflow on World Nomads.", "preference", "cross", False,
     [("DJI Mini 4 Pro", "infrastructure"), ("GoPro 13", "infrastructure"), ("Airdata UAV", "service"), ("World Nomads", "service")],
     [("DJI Mini 4 Pro", "GoPro 13", "PREFERS"), ("Airdata UAV", "World Nomads", "COMMUNICATES_WITH")],
     "which camera setup wins for trip video and what tooling reinforces the choice",
     "drone versus action cam flight log insurance claim integration"),
    # --- 47 ---
    ("Regret set in when the 2026-01-30 Bogotá Airbnb lost its hot water for three of the four nights and the Superhost dispute refunded only 40 dollars via the app.", "problem", "cross", False,
     [("Regret", "emotion"), ("2026-01-30", "date"), ("Bogotá", "place"), ("Airbnb", "service")],
     [],
     "what soured the late-January Bogota stay and how did the refund land",
     "short term rental amenity failure partial refund superhost dispute"),
    # --- 48 ---
    ("Moved the expat paperwork tracking from Google Docs to a local Obsidian vault after the Portugal D7 visa renewal on 2026-03-11 needed PDFs organized by consulate appointment.", "milestone", "cross", False,
     [("Google Docs", "service"), ("Obsidian", "tool"), ("Portugal", "place"), ("D7", "pattern"), ("2026-03-11", "date"), ("PDF", "concept")],
     [("Obsidian", "Google Docs", "REPLACES")],
     "when did the visa paperwork move from the cloud doc to the local vault",
     "expat visa document tracking local vault consulate appointment PDF"),
    # --- 49 ---
    ("The Seat31B blog's 2026-03-27 post on Avianca LifeMiles sweet spots tipped me to the Star Alliance routing that Point.me still doesn't surface in its search.", "reference", "cross", False,
     [("Seat31B", "publication"), ("2026-03-27", "date"), ("Avianca LifeMiles", "service"), ("Star Alliance", "organization"), ("Point.me", "service")],
     [],
     "which blog post unlocked the Star Alliance routing the award search missed",
     "miles sweet spot blog post award routing search tool gap"),
    # --- 50 ---
    ("Joy surged when the Remote Year cohort dinner in 2026-04-08 coincided with my Splitwise finally zeroing out against Mei after the messy Chiang Mai month-long split.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Remote Year", "organization"), ("2026-04-08", "date"), ("Splitwise", "service"), ("Mei", "person"), ("Chiang Mai", "place")],
     [("Mei", "Remote Year", "KNOWS")],
     "when did the long-running travel expense ledger with Mei finally zero out",
     "nomad cohort shared expense settlement long stay split ledger"),
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
