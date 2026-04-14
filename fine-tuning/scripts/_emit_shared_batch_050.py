"""One-off emitter for shared-base batch-050 — cross domain.

Slice: civic life / local politics / community organising meets tech tooling.
Writes 50 rows to data/v2/shared/batch_050.tmp.jsonl with ids
shared-02451..02500. The main session aggregates the tmp file into
shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_050.tmp.jsonl"
ID_OFFSET = 2450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the Maple Street neighbourhood chat from Slack to Discord once the free-tier 90-day message cap started swallowing the block-party planning threads.", "decision", "cross", False,
     [("Maple Street", "place"), ("Slack", "service"), ("Discord", "service"), ("block-party", "event")],
     [("Discord", "Slack", "REPLACES")],
     "why did the neighbourhood group chat leave the old workspace tool",
     "neighbourhood chat migration message retention free tier block planning threads"),
    # --- 2 ---
    ("Prefers Signal groups over Nextdoor for the mutual-aid pod on Oak Avenue because the Nextdoor feed kept surfacing the pod requests to people outside the trust circle.", "preference", "cross", False,
     [("Signal", "service"), ("Nextdoor", "service"), ("mutual-aid", "activity"), ("Oak Avenue", "place")],
     [("Signal", "Nextdoor", "PREFERS")],
     "which platform won for the mutual-aid pod on the small residential street",
     "encrypted group chat mutual aid neighbourhood privacy trust circle"),
    # --- 3 ---
    ("The Lincoln Elementary PTA website now runs on a Gatsby build deployed to Netlify, with the meeting minutes coming out of a shared Google Drive folder.", "architecture", "cross", False,
     [("Lincoln Elementary", "organization"), ("PTA", "organization"), ("Gatsby", "framework"), ("Netlify", "service"), ("Google Drive", "service")],
     [("Gatsby", "Netlify", "DEPLOYED_ON"), ("Gatsby", "Google Drive", "DEPENDS_ON")],
     "how does the parent-teacher site at the elementary school publish its meeting notes",
     "PTA website static generator deploy host shared drive minutes pipeline"),
    # --- 4 ---
    ("Swapped SignUpGenius for Volgistics on the food pantry volunteer roster because Volgistics handled the background-check attestations Wisconsin requires.", "decision", "cross", False,
     [("SignUpGenius", "service"), ("Volgistics", "service"), ("food pantry", "organization"), ("Wisconsin", "place")],
     [("Volgistics", "SignUpGenius", "REPLACES")],
     "which volunteer scheduler took over once the state paperwork became mandatory",
     "volunteer scheduling platform swap background check attestation compliance pantry"),
    # --- 5 ---
    ("Canvass routes for the Ward 6 school board run were exported from MiniVAN on Saturday morning so the walkers could work without cell signal in the river-valley blocks.", "architecture", "cross", False,
     [("Ward 6", "place"), ("school board", "organization"), ("MiniVAN", "service"), ("river-valley", "place")],
     [],
     "how did the school board canvassers get their walk lists for the Saturday push",
     "canvass route export offline walk list school board ward river valley coverage"),
    # --- 6. noise ---
    ("Let me grab that note and circle back.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Voter-registration tabling at the Juneteenth festival used three iPads running TurboVote so the queue moved while the wifi on the Common was rattling.", "architecture", "cross", False,
     [("Juneteenth", "event"), ("iPads", "infrastructure"), ("TurboVote", "service"), ("the Common", "place")],
     [("TurboVote", "iPads", "DEPLOYED_ON")],
     "how did the registration table keep moving at the summer festival with bad wifi",
     "voter registration tabling tablet kiosk festival network queue throughput"),
    # --- 8 ---
    ("Pulled the 311 complaint CSV from the Boston Socrata open-data portal to prep a city-council comment on the Dorchester pothole backlog.", "fact", "cross", False,
     [("311", "service"), ("Boston", "place"), ("Socrata", "platform"), ("city-council", "organization"), ("Dorchester", "place")],
     [("Socrata", "311", "USES")],
     "where did the data for the pothole comment at city hall actually come from",
     "open data portal service request export council comment neighbourhood pothole"),
    # --- 9 ---
    ("ActBlue stayed as the donation processor for Councillor Alvarez's re-election because the WinRed rails would have spooked the volunteer treasurer on compliance.", "decision", "cross", False,
     [("ActBlue", "service"), ("Councillor Alvarez", "person"), ("WinRed", "service"), ("treasurer", "person")],
     [("ActBlue", "WinRed", "PREFERS")],
     "why did the councillor's campaign keep its donation processor unchanged",
     "political donation rails processor choice compliance volunteer treasurer comfort"),
    # --- 10 ---
    ("The Saturday OpenStreetMap edit party at the Carnegie Library cleaned up 412 missing sidewalks in the South End after the accessibility audit flagged them.", "milestone", "cross", False,
     [("OpenStreetMap", "platform"), ("Carnegie Library", "place"), ("South End", "place"), ("accessibility audit", "activity")],
     [],
     "what did the weekend mapping event at the old library actually accomplish",
     "OSM edit party sidewalk coverage accessibility mapping volunteer session neighbourhood"),
    # --- 11 ---
    ("After the July flood, the POI cleanup on OpenStreetMap rerouted the food-bank Mapbox dashboard so the Riverside shelter stopped showing as open.", "problem", "cross", False,
     [("OpenStreetMap", "platform"), ("food-bank", "organization"), ("Mapbox", "platform"), ("Riverside", "place")],
     [("Mapbox", "OpenStreetMap", "DEPENDS_ON")],
     "how did the relief dashboard correct its shelter data after the flooding",
     "post flood map cleanup POI correction shelter status routing dashboard"),
    # --- 12 ---
    ("Kobo Toolbox surveys replaced the paper clipboards on the door-knocking shifts for the renter-protection ballot measure on 2026-03-07.", "decision", "cross", False,
     [("Kobo Toolbox", "platform"), ("door-knocking", "activity"), ("renter-protection", "concept"), ("2026-03-07", "date")],
     [("Kobo Toolbox", "door-knocking", "USES")],
     "what replaced clipboards for the renter-protection door campaign in early March",
     "mobile survey tool door canvass paperless renter measure ballot offline"),
    # --- 13 ---
    ("NationBuilder runs the Ramirez school-board CRM because ActionNetwork's list-hygiene tools kept dropping the bilingual outreach contacts.", "decision", "cross", False,
     [("NationBuilder", "service"), ("Ramirez", "person"), ("school-board", "organization"), ("ActionNetwork", "service"), ("bilingual outreach", "activity")],
     [("NationBuilder", "ActionNetwork", "REPLACES")],
     "which CRM ended up running the school-board campaign and why",
     "campaign CRM choice list hygiene bilingual contact preservation school board"),
    # --- 14 ---
    ("Shared the stormwater GIS layers on QGIS Cloud so the neighbourhood association meeting could project them without anyone installing the desktop client.", "architecture", "cross", False,
     [("stormwater", "concept"), ("QGIS Cloud", "platform"), ("neighbourhood association", "organization")],
     [],
     "how did the residents' meeting show the stormwater maps without installing software",
     "GIS cloud share map layer community meeting projection no install workflow"),
    # --- 15 ---
    ("The Cedar Grove HOA piloted Loomio for the short-term rental policy vote because Robert's Rules on Zoom was producing inconclusive minutes.", "decision", "cross", False,
     [("Cedar Grove", "place"), ("HOA", "organization"), ("Loomio", "service"), ("Robert's Rules", "method"), ("Zoom", "service")],
     [("Loomio", "Zoom", "REPLACES")],
     "what governance tool did the HOA adopt for the rental policy decision",
     "homeowner association governance online deliberation rental policy inconclusive minutes"),
    # --- 16 ---
    ("Decidim is powering the Riverside participatory budget pilot with a 1.8 million dollar envelope and 14 neighbourhood tables running in parallel.", "architecture", "cross", False,
     [("Decidim", "platform"), ("Riverside", "place"), ("participatory budget", "concept")],
     [],
     "which platform hosts the neighbourhood participatory budget in Riverside",
     "participatory budgeting platform community tables budget pilot civic tech"),
    # --- 17 ---
    ("Poll-worker shifts for the 2026-04-07 municipal primary sit in a shared Google Calendar with each precinct colour-coded and the check-in times pinned.", "architecture", "cross", False,
     [("2026-04-07", "date"), ("municipal primary", "event"), ("Google Calendar", "service"), ("precinct", "place")],
     [],
     "how are the poll worker shifts organised for the April primary",
     "election worker shift calendar colour code precinct assignment primary election"),
    # --- 18 ---
    ("Filed the public-records request through the FOIA Machine portal after the clerk's office stopped answering the plain-email requests about the 2024 contract ledgers.", "decision", "cross", False,
     [("FOIA Machine", "platform"), ("clerk's office", "organization"), ("contract ledgers", "concept")],
     [],
     "how did the records request on the old contracts finally go out",
     "public records request portal clerk office contract transparency civic request"),
    # --- 19 ---
    ("The Tuesday Zoom town hall on zoning adds closed captions via Otter.ai so the older residents without hearing aids can still follow the staff presentations.", "architecture", "cross", False,
     [("Zoom", "service"), ("zoning", "concept"), ("Otter.ai", "service")],
     [("Zoom", "Otter.ai", "DEPENDS_ON")],
     "how does the zoning town hall stay accessible for hard-of-hearing residents",
     "virtual town hall captioning accessibility zoning presentation older residents"),
    # --- 20 ---
    ("Prefers Change.org over MoveOn for the crosswalk-safety petition since the Change.org signature widget embedded cleanly in the PTA's Gatsby site.", "preference", "cross", False,
     [("Change.org", "service"), ("MoveOn", "service"), ("crosswalk-safety", "concept"), ("PTA", "organization"), ("Gatsby", "framework")],
     [("Change.org", "MoveOn", "PREFERS"), ("Gatsby", "Change.org", "USES")],
     "which petition platform fit the PTA crosswalk campaign better",
     "petition platform choice signature widget embed static site school safety"),
    # --- 21 ---
    ("The online comment portal for the Waterfront planning permission took 2,400 submissions through the city's custom Drupal form before the hearing on 2026-02-19.", "milestone", "cross", False,
     [("Waterfront", "place"), ("planning permission", "concept"), ("Drupal", "framework"), ("2026-02-19", "date")],
     [],
     "how many comments came through the waterfront planning portal before the hearing",
     "public comment portal planning hearing submission volume city CMS form"),
    # --- 22 ---
    ("Voter-education night at the Dudley branch library leaned on the Wicked Free Wi-Fi out front so the spillover crowd on the sidewalk could pull up the sample ballot.", "reference", "cross", False,
     [("Dudley", "place"), ("Wicked Free Wi-Fi", "infrastructure"), ("sample ballot", "concept")],
     [],
     "how did the library's voter education night reach the folks who couldn't fit inside",
     "municipal wifi library event voter education sample ballot outdoor access"),
    # --- 23 ---
    ("Bikeshare trip data from the Bluebikes public feed backed the Brookline bike-lane argument at the 2026-03-15 Select Board meeting.", "fact", "cross", False,
     [("Bluebikes", "service"), ("Brookline", "place"), ("bike-lane", "concept"), ("Select Board", "organization"), ("2026-03-15", "date")],
     [],
     "what data did residents bring to the March bike-lane hearing",
     "bikeshare data public feed bike lane advocacy select board testimony"),
    # --- 24 ---
    ("Parks Department permits for the Dorothea block fair moved to AccelaGov because the Excel-by-email loop had lost two permits the year before.", "decision", "cross", False,
     [("Parks Department", "organization"), ("Dorothea", "place"), ("block fair", "event"), ("AccelaGov", "platform"), ("Excel", "tool")],
     [("AccelaGov", "Excel", "REPLACES")],
     "why did the block fair permits stop going through the old email workflow",
     "parks permit workflow migration lost permits event permitting platform"),
    # --- 25 ---
    ("A Slack bot in the ward captains' workspace posts every 311 ticket tagged 'rat sighting' within the precinct so the captains can update the residents by Tuesday.", "architecture", "cross", False,
     [("Slack", "service"), ("ward captains", "person"), ("311", "service"), ("rat sighting", "concept"), ("precinct", "place")],
     [("Slack", "311", "COMMUNICATES_WITH")],
     "how do the ward captains get a heads up about pest complaints in their precinct",
     "311 integration slack bot ward captain precinct pest tickets community update"),
    # --- 26 ---
    ("Hope sparked after the Decidim participatory budget pilot crossed 4,000 registered voters on 2026-04-09, the first time any city process beat the library-card sign-up numbers for the month.", "milestone", "cross", False,
     [("Hope", "emotion"), ("Decidim", "platform"), ("participatory budget", "concept"), ("2026-04-09", "date"), ("library-card", "concept")],
     [],
     "when did the participatory budget pilot hit a civic engagement milestone",
     "participatory budget signup milestone civic engagement library card benchmark"),
    # --- 27 ---
    ("The lost-pet network on Nextdoor reunited Councillor Park's beagle with her by Tuesday because a retiree in Bayview cross-posted to the neighbourhood Facebook group.", "fact", "cross", False,
     [("Nextdoor", "service"), ("Councillor Park", "person"), ("Bayview", "place"), ("Facebook", "service")],
     [],
     "how did the councillor's missing dog actually get home",
     "lost pet alert neighbourhood platform cross post facebook beagle reunification"),
    # --- 28 ---
    ("Frustration peaked when the NGP VAN sync to MiniVAN dropped the Spanish-language voter flags on the Eastside turf for three days before the primary.", "problem", "cross", False,
     [("Frustration", "emotion"), ("NGP VAN", "platform"), ("MiniVAN", "service"), ("Eastside", "place"), ("primary", "event")],
     [("MiniVAN", "NGP VAN", "DEPENDS_ON")],
     "what broke in the canvass data right before the primary election",
     "voter file sync regression language flag loss canvass turf pre primary"),
    # --- 29 ---
    ("Councilmember Nguyen's office publishes its weekly constituent update through Beehiiv instead of Mailchimp because the city ethics office had flagged Mailchimp's engagement tracking.", "decision", "cross", False,
     [("Councilmember Nguyen", "person"), ("Beehiiv", "service"), ("Mailchimp", "service"), ("ethics office", "organization")],
     [("Beehiiv", "Mailchimp", "REPLACES")],
     "why did the councilmember's newsletter move off the old email platform",
     "constituent newsletter platform swap ethics tracking concerns council office"),
    # --- 30 ---
    ("The volunteer canvass training on 2026-02-24 used a shared Google Jamboard so the new folks from the Midtown chapter could map their first turf together.", "milestone", "cross", False,
     [("2026-02-24", "date"), ("Google Jamboard", "service"), ("Midtown", "place")],
     [],
     "how did the February canvass training onboard the new chapter members",
     "canvass training onboarding whiteboard new chapter turf walkthrough community"),
    # --- 31 ---
    ("A CKAN instance at data.statecourts.gov replaced the old FTP folder for county dockets because the scraping community kept hammering the FTP with unthrottled bots.", "decision", "cross", False,
     [("CKAN", "platform"), ("data.statecourts.gov", "infrastructure"), ("FTP", "protocol"), ("county dockets", "concept")],
     [("CKAN", "FTP", "REPLACES")],
     "why did the state courts move their docket data off the old file server",
     "open data portal migration FTP replacement rate limit civic transparency courts"),
    # --- 32 ---
    ("Prefers Action Network event RSVPs over Eventbrite for the immigrant-rights rally because the Action Network tag system mapped cleanly onto the existing organiser shift tiers.", "preference", "cross", False,
     [("Action Network", "service"), ("Eventbrite", "service"), ("immigrant-rights", "concept"), ("shift tiers", "concept")],
     [("Action Network", "Eventbrite", "PREFERS")],
     "which RSVP tool fit the rally's volunteer structure better",
     "event RSVP platform choice tag mapping volunteer shift tier organiser"),
    # --- 33 ---
    ("Organiser Adaeze in Bed-Stuy flagged that the Loomio mobile app collapsed the Yoruba-language thread under a single bullet after 2026-03-30.", "problem", "cross", False,
     [("Adaeze", "person"), ("Bed-Stuy", "place"), ("Loomio", "service"), ("Yoruba", "language"), ("2026-03-30", "date")],
     [],
     "what i18n bug did a Brooklyn organiser catch in the governance app",
     "mobile deliberation app language rendering bug non latin script organiser report"),
    # --- 34 ---
    ("The bilingual voter-education flyer in Somali and English came out of a Canva template and a Pandoc pipeline because the canvass team needed both print and Telegram-sized variants by Friday.", "architecture", "cross", False,
     [("Somali", "language"), ("Canva", "tool"), ("Pandoc", "tool"), ("canvass", "activity"), ("Telegram", "service")],
     [("Pandoc", "Canva", "USES")],
     "how did the weekly bilingual flyer reach both the print and messaging channels",
     "flyer design pipeline multilingual template conversion print messenger variants"),
    # --- 35 ---
    ("City Council member Okonkwo's office swapped the Google Forms intake for Tally after an open-records request revealed Google's form-response metadata had leaked constituent IP ranges.", "decision", "cross", False,
     [("Okonkwo", "person"), ("Google Forms", "service"), ("Tally", "service"), ("open-records", "concept")],
     [("Tally", "Google Forms", "REPLACES")],
     "why did the council office change its constituent intake form tool",
     "constituent intake form platform swap metadata leak privacy open records finding"),
    # --- 36 ---
    ("The OpenElections Python scraper fed the Excel hearing prep the League of Women Voters brought to the 2026-04-11 redistricting panel at Faneuil Hall.", "architecture", "cross", False,
     [("OpenElections", "project"), ("Python", "language"), ("Excel", "tool"), ("League of Women Voters", "organization"), ("2026-04-11", "date"), ("Faneuil Hall", "place")],
     [("OpenElections", "Python", "USES"), ("Excel", "OpenElections", "DEPENDS_ON")],
     "how did the LWV prep their numbers for the redistricting panel downtown",
     "election data scraper spreadsheet hearing prep redistricting advocacy civic data"),
    # --- 37 ---
    ("Hooked the Signal mutual-aid group to a tiny Python bot that posts the Wednesday grocery-run roster from a Nextcloud calendar every Tuesday night.", "architecture", "cross", False,
     [("Signal", "service"), ("mutual-aid", "activity"), ("Python", "language"), ("grocery-run", "activity"), ("Nextcloud", "service")],
     [("Python", "Signal", "COMMUNICATES_WITH"), ("Python", "Nextcloud", "USES")],
     "how does the mutual aid crew see the week's grocery runs automatically",
     "mutual aid bot calendar sync group message weekly roster volunteer coordination"),
    # --- 38 ---
    ("The 2026-01-30 tenants' union launch meeting ran on Jitsi Meet after the rent-court story in the Globe made the organisers nervous about Zoom's attendance logs.", "milestone", "cross", False,
     [("2026-01-30", "date"), ("tenants' union", "organization"), ("Jitsi Meet", "service"), ("rent-court", "concept"), ("the Globe", "publication"), ("Zoom", "service")],
     [("Jitsi Meet", "Zoom", "REPLACES")],
     "what platform did the tenant organising launch use and why not the usual one",
     "tenant union launch meeting privacy platform swap attendance log concern news"),
    # --- 39 ---
    ("Organiser Tomás in Pilsen prefers receiving the canvass packet as a Docx with the Spanish translation on the right-hand page because the print shop on 18th Street always flakes on two-file jobs.", "preference", "cross", False,
     [("Tomás", "person"), ("Pilsen", "place"), ("Docx", "concept"), ("Spanish", "language"), ("18th Street", "place")],
     [],
     "how does the Pilsen organiser want the bilingual canvass packet delivered",
     "canvass packet format bilingual layout print shop single file preference organiser"),
    # --- 40 ---
    ("The Google Sheet tracking Fairmount station accessibility tickets got archived into Airtable on 2026-03-20 once the transit justice coalition grew past 12 lead volunteers.", "decision", "cross", False,
     [("Google Sheet", "service"), ("Fairmount", "place"), ("Airtable", "service"), ("2026-03-20", "date"), ("transit justice", "concept")],
     [("Airtable", "Google Sheet", "REPLACES")],
     "why did the transit accessibility tracker move off the old spreadsheet",
     "coalition tracker migration accessibility tickets volunteer scale station civic"),
    # --- 41 ---
    ("Overlaid the heat-index GeoJSON from the NOAA feed on a Leaflet map so the cooling-centre canvass could prioritise Dorchester and Mattapan blocks on 2026-04-06.", "architecture", "cross", False,
     [("NOAA", "organization"), ("Leaflet", "library"), ("cooling-centre", "place"), ("Dorchester", "place"), ("Mattapan", "place"), ("2026-04-06", "date")],
     [("Leaflet", "NOAA", "USES")],
     "how did the cooling centre canvass decide which blocks to hit first",
     "heat index overlay map canvass priority cooling centre climate outreach"),
    # --- 42 ---
    ("The county elections board moved its live results page from a WordPress plugin to an 11ty static site because the refresh storms on primary night kept knocking the CMS over.", "decision", "cross", False,
     [("county elections board", "organization"), ("WordPress", "service"), ("11ty", "framework"), ("primary night", "event")],
     [("11ty", "WordPress", "REPLACES")],
     "why did the elections board leave WordPress for their results page",
     "election results page migration static site scalability refresh storm CMS outage"),
    # --- 43 ---
    ("Running the annual Newton Rec basketball league now uses TeamSnap alongside a tiny Python script that syncs the court permits from the Parks Dept spreadsheet.", "architecture", "cross", False,
     [("Newton Rec", "organization"), ("basketball league", "event"), ("TeamSnap", "service"), ("Python", "language"), ("Parks Dept", "organization")],
     [("Python", "TeamSnap", "COMMUNICATES_WITH")],
     "how does the rec basketball league sync its permits and schedules",
     "rec league scheduler permit sync parks department spreadsheet automation community"),
    # --- 44 ---
    ("Relief washed over the organising team when the Decidim instance survived the 2026-04-08 budget-vote spike that had 3,100 residents voting in a single hour.", "milestone", "cross", False,
     [("Relief", "emotion"), ("Decidim", "platform"), ("2026-04-08", "date"), ("budget-vote", "event")],
     [],
     "when did the participatory budget platform handle its biggest traffic spike",
     "platform load test civic vote traffic spike participatory budget relief team"),
    # --- 45 ---
    ("The Backblaze B2 archive of the tenants' union's Signal export runs nightly through Restic because losing the 2023 eviction-survey thread would be unrecoverable.", "architecture", "cross", False,
     [("Backblaze B2", "service"), ("tenants' union", "organization"), ("Signal", "service"), ("Restic", "tool"), ("eviction-survey", "activity")],
     [("Restic", "Backblaze B2", "DEPENDS_ON"), ("Restic", "Signal", "USES")],
     "how does the tenant group protect its chat history against another data loss",
     "offsite backup community chat export encrypted snapshot tenant organising archive"),
    # --- 46 ---
    ("Grammarly stayed on the communications staffer's laptop for the ward newsletter but got pulled off the intake-form account because the tone suggestions were softening the language on constituent complaints.", "decision", "cross", False,
     [("Grammarly", "service"), ("ward newsletter", "publication"), ("intake-form", "pattern")],
     [],
     "why does the writing assistant only run on one of the council office accounts",
     "grammar assistant scope split constituent complaint preservation tone softening"),
    # --- 47 ---
    ("Anxiety surged when the AccelaGov portal rejected the Juneteenth block-party permit at 11:47pm on 2026-03-31, one hour before the 30-day filing window closed.", "problem", "cross", False,
     [("Anxiety", "emotion"), ("AccelaGov", "platform"), ("Juneteenth", "event"), ("block-party", "event"), ("2026-03-31", "date")],
     [],
     "what went wrong with the Juneteenth permit filing right at the deadline",
     "permit portal rejection deadline block party filing window civic event panic"),
    # --- 48 ---
    ("The school-board candidate forum on 2026-04-03 at Roxbury Community College streamed on Vimeo with a parallel ASL interpretation feed routed through OBS.", "milestone", "cross", False,
     [("2026-04-03", "date"), ("Roxbury Community College", "organization"), ("Vimeo", "service"), ("ASL", "language"), ("OBS", "tool")],
     [("OBS", "Vimeo", "COMMUNICATES_WITH")],
     "how did the spring school-board forum reach the Deaf community online",
     "candidate forum stream interpretation accessibility community college broadcast setup"),
    # --- 49 ---
    ("Prefers uMap over Google My Maps for the neighbourhood tree-canopy walk because the uMap export to GeoJSON plugs straight into the coalition's QGIS model.", "preference", "cross", False,
     [("uMap", "platform"), ("Google My Maps", "service"), ("tree-canopy", "concept"), ("GeoJSON", "concept"), ("QGIS", "tool")],
     [("uMap", "Google My Maps", "PREFERS"), ("QGIS", "uMap", "USES")],
     "which mapping tool fit the coalition's GIS pipeline better",
     "community mapping tool choice GeoJSON export GIS pipeline canopy walk"),
    # --- 50. noise ---
    ("Hold on, let me find that.", "fact", "noise", True, [], [], None, None),
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
