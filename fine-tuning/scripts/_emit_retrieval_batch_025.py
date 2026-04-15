"""One-off emitter for retrieval top-up batch-025 — multi-sentence queries.

Each row pairs a longer, paragraph-shaped query (2-4 sentences, 20-60 words) with
its source shared row as the positive. Queries simulate a careful user typing out
context and a specific question instead of a terse search phrase.

Writes 100 rows to data/v2/retrieval/batch_025.tmp.jsonl with ids ret-02401..02500,
pulling positives from shared rows at zero-indexed offsets 2400..2499.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_025.tmp.jsonl"
ID_OFFSET = 2400
SHARED_OFFSET = 2400
QUERY_KIND = "multi-sentence"

# 100 multi-sentence queries, aligned in order with shared rows 2401..2500.
QUERIES: list[str] = [
    # 02401 Qustodio -> Mobicip after Chromebook report gap
    "The Chromebook reporting on our old parental control had gaps during the afternoon school browsing window. Which product did we move to in mid-January, and what specifically about the school-issued browser sessions prompted the switch?",
    # 02402 Apple Family Sharing preferred over Family Link
    "We run two iPad minis for the kids and coordinate with a co-parent. Which family device management setup do we prefer, and why did the Sunday Screen Time email tip the decision over Google's offering?",
    # 02403 Bark trial kept after sextortion DM alert
    "We were trialling a messaging-monitor for the kids earlier this year. Did we keep it at the end of the trial, and what alert in particular made the decision easy for both parents?",
    # 02404 Circle Home Plus on living-room router kid VLAN
    "Guest laptops sometimes show up at family gatherings and hit the wrong Wi-Fi. Which parental control box sits on the router's kid VLAN, and what concrete incident did it prevent during a past visit?",
    # 02405 Eero Secure replaced Circle Home Plus after mesh upgrade
    "Our whole-home Wi-Fi hardware changed in February. What happened to the old parental control box afterwards, and which built-in feature of the new mesh made it redundant?",
    # 02406 NOISE kettle
    "The other side just paused for something in the kitchen. Is this a normal break in the chat, or should I retry what I just asked while they sort it out?",
    # 02407 UniFi kid VLAN isolating nursery smart-home
    "Nursery automations and kid tablets share a house but should not share a network. How are the Fire HD 8 tablets isolated from the smart-home broker, and what gear enforces that separation?",
    # 02408 Khan Academy Kids preferred over Prodigy Math
    "The youngest child keeps bouncing between apps instead of finishing lessons. Which learning app do we prefer on which device for him, and why does the competing option on the school Chromebook not stick?",
    # 02409 iOS 18 update reset Screen Time downtime
    "Our evening supervision quietly stopped working after a phone update in early March. Which OS change silently wiped the downtime schedule, and how much unsupervised time did the kid get before anyone noticed?",
    # 02410 YouTube Kids locked to Learning on Nest Hub
    "Morning cartoons on the kitchen smart display were getting interrupted by toy-unboxing clickbait. Which profile setting did we lock down on YouTube Kids, and on which device does that matter most during breakfast?",
    # 02411 Google Calendar feeds Echo Show morning routine
    "Piano practice was getting missed in the morning scramble. Which calendar backs the announcement, and which hallway speaker actually reads the morning routine out loud before the school bus arrives?",
    # 02412 LEGO Boost -> LEGO Spike Prime for after-school robotics
    "The robotics kit our ten-year-old uses got upgraded in early April. Which set replaced the older one, and what change in his after-school club made the Scratch-style blocks feel too easy?",
    # 02413 Scratch Jr to Scratch handoff moved to iMac
    "Scratch projects kept losing work on the iPad during saves of the larger sprite files. Which household machine took over that workflow recently, and what stage in the kid's programming journey prompted the move?",
    # 02414 Minecraft Education Edition on iPad for FaceTime grandparents
    "Grandparents want to visit worlds but struggle with joining Minecraft on a proper console. Which edition is running on the kitchen iPad now, and what specific feature made world-sharing over FaceTime easier?",
    # 02415 Kindle Kids preferred over Kobo Clara 2E
    "A grandmother wants concrete reading-progress numbers to praise over the phone. Which e-reader do we prefer for our third-grader, and what reporting feature makes it a better fit than the competing device?",
    # 02416 Life360 retained after I-90 bus incident
    "Earlier this year a school bus broke down on a highway shoulder and family location sharing paid off. What was the date, and which app's last-seen pin prevented a longer panic while the teen was stranded?",
    # 02417 AirTag in kindergartener's backpack pings HomePod
    "A small backpack keeps going missing between the mudroom and breakfast table. Which tracker is clipped inside, and which living-room speaker does it ping when the bag has wandered off?",
    # 02418 DuckDuckGo kid-safe replaced Google on Milo's laptop
    "A dinosaur homework project last September surfaced image results that were nowhere near appropriate. Which default search engine did we move away from on the kid's laptop, and what did we replace it with?",
    # 02419 Bark digest zero-alerts milestone
    "The weekly Discord monitoring digest for our daughter had been noisy for a while. What did the early April report finally show for the first time, and why did that feel like a quiet relief?",
    # 02420 Nanit replaced Owlet Cam for baby Juno
    "Our older nursery cam was not keeping up with our late-night feeding decisions. Which baby monitor replaced it in late January, and what analytics feature was actually driving the 2am choices after the swap?",
    # 02421 Self-hosted Pi-hole blocks YouTube Kids ads
    "Even YouTube Kids was still leaking ad domains to the living-room Apple TV. What is running in the basement to block those domains, and on which piece of hardware does it live?",
    # 02422 KidzSearch preferred over Kiddle for homework
    "Our fourth-grader has to cite sources for homework without wandering into the open web. Which kid-safe search engine do we prefer for him, and which feature of it makes citations land cleanly?",
    # 02423 Time-Boss pauses Roblox for Khan Academy
    "Roblox was eating the time our son should have spent on math before dinner. Which rule tool on the family PC now pauses the game, and after how many minutes does it kick in?",
    # 02424 IFTTT dims Hue lights at Bluey time
    "Our toddler's nightly show has become a calm-down ritual. Which automation platform triggers the living-room lights to dim, and what colour do they shift to when the episode starts?",
    # 02425 DuoABC replaced Starfall for preschooler Isla
    "Our preschooler needed the same streak-and-habit loop that made Duolingo stick for adults. Which learning app replaced the older one on her iPad mini, and what about the new one made the habit actually form?",
    # 02426 Micro:bit blinks dishwasher cycle status
    "Our daughter's soldering project from coding club ended up as an actual household helper. Which microcontroller did she build it on, and what status does it now blink on the kitchen counter?",
    # 02427 PhotoCircle replaced iCloud shared album for Android grandparent
    "Grandparent photo sharing across mixed phone ecosystems kept falling apart. Which app replaced the shared iCloud Photos album in mid-March, and whose attempt to link an Android tablet into Apple's ecosystem finally gave out?",
    # 02428 Duet Display turns iPad into homework helper for Zoom tutoring
    "Our kid's tutor now joins by video while I stay on the kitchen island. Which product turns the old iPad into a second screen beside his laptop, and where am I when I join the Zoom call?",
    # 02429 Nest Hub announces Notion chore rotations
    "Chore arguments between two siblings were getting out of hand. Which smart display reads the rotation aloud every Saturday, and where does the underlying chore list actually live in the household tooling?",
    # 02430 Family meeting picked Mobicip as cross-platform control
    "Earlier this year the whole family sat down to pick one parental control to rule them all. What was the meeting date, which product won, and what pilot data sealed that call?",
    # 02431 Life360 stale pin after battery saver
    "One night our eldest's location pin appeared stuck at a strange address. What turned out to be the cause of the stale pin, and what did I end up doing before I could fully relax?",
    # 02432 Owlet Sock preferred over Nanit Pro at 3am
    "For the second baby we reevaluated the nursery gear. Which monitor do we now prefer at 3am, and what specific data stream makes it more actionable than a grainy infrared video feed?",
    # 02433 Raspberry Pi MotionEye replaced Nanit for newborn Eden
    "The Nanit subscription felt like overkill for the third baby. What home-built setup replaced it for our newborn, and which networking layer makes the live feed safely reachable for the grandparents?",
    # 02434 NOISE baby monitor chirp
    "There was a small interruption just now from the other side. Is the baby monitor noise something I should wait out, or should I resend the last question while they attend to it?",
    # 02435 Safe Browser Kiddle replaced Chrome on kid Chromebook
    "The default browser on a kid Chromebook kept letting our son jump to his older cousin's bookmarks. Which browser replaced it for his profile, and what UI difference actually prevented the bookmark-bar hop?",
    # 02436 Omegle incident -> Apple Configurator MDM
    "A scary install happened on the family iPad at the end of March. Which app did our daughter accidentally download, and how is install management being handled now after the full device reset?",
    # 02437 Echo Show replaced iPad FaceTime for toddler dialing
    "Our toddler was tapping her way into unfamiliar FaceTime rooms. Which device now hosts grandparent video calls, and what about the new device's interface keeps her from dialing the wrong person?",
    # 02438 Cozi Family Organizer syncs soccer tournament
    "A soccer tournament is coming up in mid-April and nobody wants a repeat of arriving at the wrong field. Which app now syncs that event to both parents, and what is the tournament date we keyed it off?",
    # 02439 Prodigy Math fractions milestone for Ada
    "Our second-grader had been stuck on the same math unit since January. What happened on the early April weekly report, and which app is giving us that signal at home?",
    # 02440 Pinna audio replaced kid YouTube bookmarks
    "Bedtime routines with a glowing screen were keeping our six-year-old awake too long. Which audio-only service replaced the tangle of YouTube bookmarks, and which speaker in the bedroom does it play from?",
    # 02441 NextDNS family profile on kid VLAN
    "Our son kept reaching sketchy Minecraft mods that were breaking his world on the school laptop. Which DNS service does the kid VLAN resolve through now, and what profile is applied on the family side?",
    # 02442 Bark phone preferred over iPhone SE for eleven-year-old
    "Group chats with classmates matter but a full iPhone felt like too much for our eleven-year-old. Which supervised phone do we prefer instead, and why did default messaging inside that app win over the hand-me-down option?",
    # 02443 Google Family Link region bug pushed us off Android
    "A March bug broke our daughter's Pixel Tablet downtime schedule. What was the date, which controls broke, and what seasonal decision did the household make about Android-first parental controls afterwards?",
    # 02444 Arduino Uno + Scratch at robotics showcase
    "Our daughter demoed a light-sensor project at her school robotics showcase in early April. Which microcontroller did she pair with a block-based environment, and why did she not have to write any C code for the demo?",
    # 02445 Common Sense Media reviews for nephew Dara
    "When my sister wants to vet a new iPad app for my nephew, she asks me first. Which review site do I point her to as the default reference before she hands anything over?",
    # 02446 Kindle Paperwhite Kids preferred for reluctant-reader Theo
    "Our reluctant reader needed a concrete sense of forward motion after each session. Which e-reader do we prefer for him, and what specific report after each reading session finally landed as encouragement?",
    # 02447 Disney+ Kids -> Plex library for Marvel trailers
    "Marvel trailers were sneaking onto Disney+ Kids profiles and triggering nightmares for our five-year-old. What did we migrate to at the end of January, and what exactly did that swap stop showing up on the home screen?",
    # 02448 Eero Secure + NextDNS clean week on Hadi's rig
    "Our teen's Windows gaming rig had been a worry for a while. What did the most recent week of Eero Secure and NextDNS logs show, and what feeling did that finally restore at home?",
    # 02449 Immich on basement NAS replaced Google Photos for shared albums
    "Shared photo albums with the kids kept feeling subscription-fragile on Google. Which self-hosted app took over, and where is it running so future Google subscription disputes cannot wipe the memories?",
    # 02450 Selene's Scratch project shipped to school coding fair
    "In January we set a ship-one-public-project goal for our daughter. What milestone did she actually hit in early April, and what kind of pair sessions in the months before made the shipping possible?",
    # 02451 Neighbourhood chat migrated from Slack to Discord
    "The Maple Street neighbourhood chat was losing block-party planning threads to Slack's 90-day free-tier limit. Which platform did we move the chat to, and what specifically about the Slack tier was making older messages vanish?",
    # 02452 Signal preferred over Nextdoor for mutual-aid pod
    "Our mutual-aid pod on Oak Avenue kept leaking requests to people outside the trust circle. Which messaging tool do we prefer for the group now, and which platform were we trying to leave behind?",
    # 02453 Lincoln Elementary PTA site on Gatsby + Netlify
    "The PTA site for Lincoln Elementary got a rebuild recently. What static site framework is it on, where does it deploy, and how are meeting minutes fed into it from the volunteer workflow?",
    # 02454 Volgistics replaced SignUpGenius for food pantry checks
    "The food pantry volunteer roster needed Wisconsin background-check attestations. Which scheduling tool did we swap it over to, and which older tool could not handle that requirement?",
    # 02455 MiniVAN offline canvass for Ward 6
    "The Ward 6 school board run involves river-valley blocks with no cell signal. Which canvass tool did we export routes from, and on which day were walkers actually out working off that offline data?",
    # 02456 NOISE let me grab that note
    "The other side just said they would grab a note and come back. Is this a normal momentary pause, or should I rephrase the question in the meantime in case the context has been lost?",
    # 02457 TurboVote tabling at Juneteenth festival
    "The wifi at the Common was rattling during our voter registration tabling at the Juneteenth festival. Which app were we running on three iPads so the queue kept moving despite the connectivity problems?",
    # 02458 Boston 311 Socrata pull for Dorchester potholes
    "A city-council comment on the Dorchester pothole backlog needed proper data to back it up. Which dataset did we pull, from which open-data portal, to get the 311 complaint numbers in shape before the hearing?",
    # 02459 ActBlue retained over WinRed for Alvarez campaign
    "Councillor Alvarez's re-election needed a donation processor decision. Which platform stayed in place, which alternative was considered, and what would have spooked the volunteer treasurer about the other rails?",
    # 02460 OpenStreetMap sidewalk cleanup after accessibility audit
    "An accessibility audit flagged missing sidewalks in the South End. Where did Saturday volunteers gather to clean those up on OpenStreetMap, and roughly how many sidewalks ended up added during the edit party?",
    # 02461 OSM POI cleanup fixed Mapbox food-bank routing after flood
    "After the July flood our food-bank dashboard started hiding a shelter that was actually open. What kind of map cleanup fixed the downstream routing, and which shelter was the one mistakenly showing as closed?",
    # 02462 KoboToolbox replaced paper clipboards for ballot canvass
    "The renter-protection ballot measure canvass needed to get off paper. Which survey tool replaced the clipboards, and on what date in early March did that switch actually happen on the door-knocking shifts?",
    # 02463 NationBuilder over ActionNetwork for Ramirez school-board
    "Bilingual outreach contacts kept getting dropped during list hygiene on the Ramirez school-board campaign. Which CRM runs the campaign now, and which competing tool's behaviour pushed the decision?",
    # 02464 QGIS Cloud shared stormwater layers for meeting
    "Our neighbourhood association meeting needed stormwater GIS layers projected without anyone installing desktop GIS. Which hosted service is publishing the layers, and which underlying client was previously required?",
    # 02465 Loomio piloted for Cedar Grove HOA vote
    "Running the short-term rental policy vote under Robert's Rules on Zoom was producing inconclusive minutes. Which HOA piloted a different tool for that vote, and which tool did they actually try?",
    # 02466 Decidim powers Riverside participatory budget
    "A participatory budget pilot in Riverside has a real dollar envelope and neighbourhood tables running in parallel. Which platform is powering it, how big is the envelope, and how many tables are live?",
    # 02467 Poll-worker shifts in shared Google Calendar for April primary
    "Poll-worker shift logistics for the April municipal primary had to be visible to every precinct lead. Which calendar tool holds the schedule, how are precincts distinguished, and what kind of timing is pinned alongside each shift?",
    # 02468 FOIA Machine used after clerk stopped answering
    "The clerk's office stopped responding to plain email requests about the 2024 contract ledgers. Through which portal did we end up filing the public-records request, and what prompted the escalation in the first place?",
    # 02469 Otter.ai captions on Tuesday zoning town hall
    "Older residents without hearing aids were missing the staff presentations on the Tuesday zoning town hall. Which Zoom add-on now provides the captioning, and what specific audience group drove the decision to add it?",
    # 02470 Change.org preferred over MoveOn for crosswalk petition
    "The PTA site already runs on a static framework and needed a petition widget that would embed cleanly. Which petition platform do we prefer for the crosswalk-safety campaign, and which competing service lost out?",
    # 02471 Waterfront comment portal on Drupal, 2400 submissions
    "A waterfront planning permission hearing in February drew massive online engagement. How many comment submissions came through before the hearing, and what kind of form system was the city running behind the scenes?",
    # 02472 Wicked Free Wi-Fi at Dudley branch voter-ed
    "Our voter-education night at the Dudley branch library had a spillover crowd on the sidewalk. Which public Wi-Fi network supported the sample-ballot lookups outside the building, and what was the nature of the overflow?",
    # 02473 Bluebikes feed for Brookline bike-lane argument
    "The March Select Board meeting in Brookline needed hard numbers on bike usage to justify new lanes. Which public data feed provided those trip figures, and on what date was the argument made to the board?",
    # 02474 AccelaGov replaced email-Excel permit loop for Dorothea block fair
    "The Parks Department permit process for the Dorothea block fair had lost two permits the year before. Which portal did permitting move onto, and what kind of workflow did it replace?",
    # 02475 Slack bot posts 311 rat-sighting tickets to ward captains
    "Ward captains need to reach residents about 311 rat sightings quickly. Where does the automation live, what specific ticket tag is it watching, and by what weekday do the captains push updates to residents?",
    # 02476 Decidim crossed 4000 voters on April 9
    "The participatory budget pilot beat a notable civic benchmark on a specific day in early April. What was that benchmark and what date was it crossed, and what kind of civic baseline did it exceed?",
    # 02477 Nextdoor reunited Councillor Park's beagle
    "A councillor's lost dog came home thanks to a cross-posted neighbourhood message. Which pet's owner was it, which site originated the message, and which other platform did a Bayview retiree relay it through?",
    # 02478 NGP VAN sync dropped Spanish voter flags on Eastside
    "During three days before the primary, Spanish-language voter flags vanished from the Eastside turf. Which CRM-to-canvass sync was responsible, and what specifically was it dropping?",
    # 02479 Beehiiv replaced Mailchimp for Nguyen newsletter
    "Councilmember Nguyen's office changed newsletter platforms after ethics-office feedback. Which platform did they switch to, which one were they coming off, and what about the old platform's tracking triggered the flag?",
    # 02480 Google Jamboard at Midtown canvass training
    "New volunteers at a late-February canvass training needed to map their first turf collaboratively. Which shared online whiteboard was used, and which chapter's new folks were the session aimed at?",
    # 02481 CKAN replaced FTP for county dockets
    "The scraping community had been hammering an old court FTP folder with unthrottled bots. Which portal replaced the FTP, what software is it running, and what was the underlying data it was serving?",
    # 02482 Action Network preferred over Eventbrite for rally RSVPs
    "The immigrant-rights rally needed RSVP handling that slotted into existing organiser shift tiers. Which RSVP platform do we prefer for that, and why did a more mainstream event tool lose out on the workflow fit?",
    # 02483 Loomio mobile collapsed Yoruba thread
    "A Bed-Stuy organiser flagged a serious problem with a governance app after late March. What app was it, who reported it, and what specifically happened to a Yoruba-language thread on mobile?",
    # 02484 Canva + Pandoc pipeline for Somali-English flyer
    "The bilingual voter-education flyer needed both a print version and a Telegram-sized one by Friday. Which design tool supplied the template, which document tool handled the conversion, and what languages were involved?",
    # 02485 Tally replaced Google Forms after IP leak
    "A public-records request revealed that an older intake form was leaking constituent IP ranges. Which form tool did Councilmember Okonkwo's office switch to, and what metadata exposure actually drove the change?",
    # 02486 OpenElections scraper for redistricting hearing prep
    "The League of Women Voters brought an Excel hearing prep to a redistricting panel in early April. Which Python scraper produced the underlying data, and where was the panel held?",
    # 02487 Python bot posts Nextcloud grocery roster to Signal
    "The Wednesday grocery-run roster comes out of a household cloud calendar but needs to reach a messaging group. Which messaging platform is the bot posting into, and which calendar application is it reading from?",
    # 02488 Jitsi Meet used for tenants' union launch
    "A Globe story about rent court made tenants' union organisers wary of Zoom attendance logs. Which videoconferencing tool did they switch to for the late-January launch meeting, and what specifically made them nervous about the old option?",
    # 02489 Docx canvass packet with side-by-side Spanish for Pilsen
    "A Pilsen organiser has a print shop that flakes on two-file jobs on 18th Street. Which file format does he prefer for the canvass packet, and how is the Spanish translation laid out on the page to make a single-file print work?",
    # 02490 Airtable replaced Google Sheet for Fairmount accessibility
    "The transit justice coalition outgrew a simple spreadsheet once the volunteer count passed a dozen. When did the migration happen, what station's accessibility tickets were being tracked, and which tool did the data land in afterwards?",
    # 02491 Leaflet + NOAA heat-index for cooling-centre canvass
    "A cooling-centre canvass in early April needed to prioritise the hottest neighbourhoods. Which map library was overlaid with which data feed, and which two areas came out as priorities on the 2026-04-06 date we ran the planning?",
    # 02492 11ty static site replaced WordPress for live results
    "WordPress was tipping over under refresh storms on primary nights. Which framework is the county elections board now using for its live results page, and what kind of plugin-based setup was it replacing?",
    # 02493 TeamSnap + Python script for Newton Rec league
    "The annual Newton Rec basketball league has a roster tool plus a script that handles court permits. Which app runs the team side, what is the script written in, and which city department's spreadsheet does it sync from?",
    # 02494 Decidim survived 3100-voter spike on April 8
    "A participatory budget platform faced a heavy traffic moment in early April. What date was the spike, how many residents voted in that one hour, and how did the organising team feel about the infrastructure holding up?",
    # 02495 Restic + Backblaze B2 archive of Signal export
    "The tenants' union's messaging history includes a 2023 eviction-survey thread that cannot be lost. Which backup tool archives the Signal export nightly, and which cloud storage holds the final copy?",
    # 02496 Grammarly pulled off intake account, kept on newsletter
    "Our communications staffer uses a writing assistant on some accounts but not others now. Which tool is kept for the ward newsletter, which account was it pulled off, and why specifically on the constituent-facing one?",
    # 02497 AccelaGov rejected Juneteenth permit near deadline
    "A Juneteenth block-party permit hit a portal error late at night. Which system rejected the submission, exactly when did that happen, and how close was the rejection to the 30-day filing window closing?",
    # 02498 Vimeo stream with ASL feed via OBS at candidate forum
    "A school-board candidate forum at Roxbury Community College needed an accessible livestream. What streaming platform carried the feed, how was the ASL interpretation routed in, and on what date did the event run?",
    # 02499 uMap preferred over Google My Maps for tree-canopy walk
    "Our neighbourhood tree-canopy walk needs a map that plays nicely with the coalition's GIS model. Which mapping tool do we prefer, which big-name alternative did it beat out, and what export format is the integration hook?",
    # 02500 NOISE hold on let me find that
    "The other side just paused to dig something up. Is there something I should do on my end while they look, or should I simply wait for them to find what they need before asking again?",
]


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    with SHARED.open("r", encoding="utf-8") as f:
        shared_lines = f.readlines()
    positives = [json.loads(l) for l in shared_lines[SHARED_OFFSET:SHARED_OFFSET + 100]]
    assert len(positives) == 100, f"expected 100 positives, got {len(positives)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (query, pos) in enumerate(zip(QUERIES, positives), start=1):
            row_id = f"ret-{ID_OFFSET + i:05d}"
            row = {
                "id": row_id,
                "source_id": pos["id"],
                "query": query,
                "positive": pos["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
