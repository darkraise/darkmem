"""One-off emitter for retrieval top-up batch-015 — hard-negative mode.

For each target shared row at line offsets SHARED_OFFSET..SHARED_OFFSET+99,
emit a retrieval row with a query about the target and a topically adjacent
but non-answering shared row as the hard negative.

Row schema: {id, source_id, query, negative, query_kind}.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_015.tmp.jsonl"

ID_OFFSET = 1400
SHARED_OFFSET = 1400
QUERY_KIND = "hard-negative"

# (query, negative_line_offset) — target at line SHARED_OFFSET + i.
# Negative line offsets point at topically adjacent but non-answering rows.
ENTRIES: list[tuple[str, int]] = [
    # i=0  target 1400 (comp conversations tied to market data, Levels.fyi)
    ("which pay-talk approach replaces the yearly three-percent bump and where does the benchmark data come from", 1481),
    # i=1  target 1401 (Dr. Patel levothyroxine TSH 4.8 on 2026-02-11)
    ("when did the thyroid specialist raise the levothyroxine dose and what TSH value drove it", 1424),
    # i=2  target 1402 (magnesium glycinate replaced melatonin, sleep latency)
    ("which mineral supplement took over from the melatonin tablet for getting to sleep", 1411),
    # i=3  target 1403 (oral allergy syndrome, apple, microwave workaround)
    ("which fruit triggers the itchy-mouth pollen cross-reaction and what kitchen trick tames it", 1418),
    # i=4  target 1404 (sleep study at St. Mary's 2025-10-22 ruled out apnea, delayed sleep phase)
    ("when did the overnight sleep study at the hospital run and what diagnosis did it point at", 1446),
    # i=5  target 1405 (EMDR with Dr. Okafor preferred over CBT)
    ("which therapy modality with the current clinician outperforms the earlier CBT rounds", 1429),
    # i=6  target 1406 (16:8 eating window started 2026-01-05)
    ("when did the time-restricted feeding window begin and how did hunger settle", 1441),
    # i=7  target 1407 (Dr. Lena dermatologist, tretinoin 0.025%, follow-up 2026-05-04)
    ("which dermatologist started the retinoid for cystic jaw breakouts and when is the follow-up visit", 1412),
    # i=8  target 1408 (pelvic floor physio Hana improved on Kegel app)
    ("which in-person pelvic routine beat the phone-app squeezes and how many sessions did it take", 1430),
    # i=9  target 1409 (Thryve gut biome panel 2026-03-12, low Akkermansia, kefir+pomegranate)
    ("when did the microbiome lab kit come back and which foods went on the daily plan", 1420),
    # i=10 target 1410 (noise)
    ("what was the throwaway remark about pulling up the lab portal before continuing", 1434),
    # i=11 target 1411 (ashwagandha dropped after eight weeks)
    ("which adaptogen supplement did I stop after two months and why", 1402),
    # i=12 target 1412 (Dr. Hoffman eyeglass prescription 2026-03-24, blue-light coating)
    ("when did the optometrist update my lens numbers and what coating went on", 1425),
    # i=13 target 1413 (Dexcom G7 upper arm preferred over finger-prick strips, pasta)
    ("which glucose-reading hardware took over from finger-prick strips and what food did it reshape", 1422),
    # i=14 target 1414 (dental implant tooth 19 placed 2025-09-30 Halsted clinic, check 2026-06-01)
    ("when was the lower molar implant placed and when is the integration check booked", 1438),
    # i=15 target 1415 (asthma flared during wildfire smoke week, rescue inhaler)
    ("which respiratory condition worsened during the smoky stretch and what changed in inhaler use", 1442),
    # i=16 target 1416 (stand-up desk + treadmill preferred over seated, back pain halved)
    ("which work-surface configuration took over from sitting and what did the back feel", 1443),
    # i=17 target 1417 (Alexander Technique with Marcus started 2026-02-24)
    ("when did the posture re-education lessons begin and who is the teacher", 1448),
    # i=18 target 1418 (IBS low-FODMAP reintroduction pinned onion and wheat as triggers)
    ("which gut condition settled after the structured diet test and which foods came out as culprits", 1440),
    # i=19 target 1419 (switched primary care Dr. Novak to Dr. Aziz after missed referrals)
    ("which general practitioner took over my file and what forced the move", 1407),
    # i=20 target 1420 (allergy skin-prick panel 2026-03-07 ragweed, dust mite, cat dander)
    ("when did the allergist test come back and which three triggers lit up", 1409),
    # i=21 target 1421 (CGM data, steel-cut oats replaced banana smoothie, glucose 180 to 125)
    ("which breakfast food swap came out of the CGM data and what did post-meal glucose do", 1413),
    # i=22 target 1422 (FreeStyle Libre preferred over Dexcom, swapped 2026-01-18)
    ("which continuous glucose brand did I pick at the end of the trial and on what date", 1413),
    # i=23 target 1423 (flu shot + shingles at Wellspring pharmacy 2026-04-28)
    ("which two vaccinations are queued at the pharmacy and on what date", 1433),
    # i=24 target 1424 (perimenopause hormone panel 2026-01-30, FSH 32, Dr. Haddad estradiol)
    ("when did the perimenopause labs come back and what topical did the clinician suggest", 1446),
    # i=25 target 1425 (hearing test Amplifon 2025-11-14, mild high-frequency loss right)
    ("when did the audiology test happen and what did the right-ear result show", 1412),
    # i=26 target 1426 (matcha replaced coffee after HRV data)
    ("which caffeine swap came out of the heart-rate variability tracking", 1421),
    # i=27 target 1427 (fertility work-up Reproductive Partners 2026-02-02, AMH 2.1, IVF pause)
    ("when did the fertility clinic work-up happen and what did the ovarian reserve marker read", 1409),
    # i=28 target 1428 (Oura Gen 4 sleep ring, index finger better than ring finger)
    ("which finger gives the tracker ring its cleanest signal on my hand", 1413),
    # i=29 target 1429 (ACT group at Mindspace Thursday nights preferred over solo CBT app)
    ("which acceptance-commitment gathering outperforms the solo phone app and why", 1405),
    # i=30 target 1430 (physio for plantar fasciitis with Jamal, eight weeks, calf drops)
    ("how long did the heel-pain rehab run and what two exercises did most of the work", 1444),
    # i=31 target 1431 (hydration rule 500 ml on waking, 750 ml mid-morning, headaches gone)
    ("what morning water protocol cleared the afternoon head pain", 1447),
    # i=32 target 1432 (creatine 5g trial eight weeks, deadlift +10kg, memory bump)
    ("which two-month supplement run lifted both my deadlift and memory scores", 1411),
    # i=33 target 1433 (cardiologist Holter monitor, Meridian Heart, 2026-04-19)
    ("which heart monitoring kit am I picking up and where is the appointment", 1442),
    # i=34 target 1434 (noise)
    ("what hedging phrase about checking the referral form appeared in the transcript", 1410),
    # i=35 target 1435 (iron bisglycinate preferred over ferrous sulphate, ferritin 12 to 48)
    ("which iron form took over from the older salt and what did ferritin do", 1449),
    # i=36 target 1436 (OMAD trial quit after two weeks on 2025-12-15, binges, sleep tanked)
    ("when did the one-meal-a-day run end and what broke it", 1406),
    # i=37 target 1437 (knee-to-hip imbalance explains IT band, single-leg bridges daily)
    ("which strength gap explains the lateral-leg band flare-ups and what exercise addresses it", 1430),
    # i=38 target 1438 (colonoscopy 2026-03-20 clean, next in 2036)
    ("when was the lower-GI screen and how far out is the next one", 1414),
    # i=39 target 1439 (Waking Up app replaced Calm, Sam Harris intro course)
    ("which meditation app took over from the old one and who nudged the switch", 1429),
    # i=40 target 1440 (full-dairy elimination cleared sinus drip, yogurt fine, hard cheese trigger)
    ("which food group cut resolved the sinus issue and which reintroduction broke it again", 1418),
    # i=41 target 1441 (caffeine cutoff moved 14:00 to 11:00 on 2026-01-22, deep sleep 58 to 92)
    ("when did the coffee curfew move earlier and what did deep-sleep minutes do", 1406),
    # i=42 target 1442 (migraine prevention propranolol 40mg twice daily from 2026-02-05)
    ("when did the beta-blocker migraine regimen begin and how did headache count change", 1417),
    # i=43 target 1443 (nose-breathing tape preferred over mouth guard, snoring stopped)
    ("which overnight mouth intervention took over from the dental splint and what improved", 1435),
    # i=44 target 1444 (shoulder impingement from bench pressing, Dr. Voss cleared 2026-03-28)
    ("which pressing injury led to a rehab stint and when was I cleared to lift again", 1430),
    # i=45 target 1445 (homemade salt/lime/coconut water preferred over LMNT)
    ("which homemade trail electrolyte recipe beats the branded powder for long runs", 1475),
    # i=46 target 1446 (bone-density scan 2026-02-26, hip T-score -1.8, vest walks)
    ("when did the DEXA come back and what new loading activity did the clinician add", 1424),
    # i=47 target 1447 (blood-pressure rule morning measurement protocol, averages dropped 138 to 124)
    ("what consistent morning measurement protocol took my home BP readings down", 1431),
    # i=48 target 1448 (acupuncture with Wei improved on TENS unit for lower-back spasms)
    ("which needle-based treatment outperformed the electrical stimulator for the lumbar spasms", 1430),
    # i=49 target 1449 (vitamin D 22 ng/mL on 2026-01-09, 4000 IU brought it to 48 by April)
    ("what was the winter serum D level and where did it land after supplementing", 1420),
    # i=50 target 1450 (morning daylight walk preferred over lightbox for mood and sleep)
    ("which early-AM circadian trick beats the indoor bright lamp for mood and sleep", 1441),
    # i=51 target 1451 (kitchen renovation three phases: demolition May, cabinetry July, countertop September)
    ("how is the kitchen overhaul staged across the calendar year", 1492),
    # i=52 target 1452 (heat pump chosen over gas boiler on 2026-03-15, grant covered third)
    ("which heating appliance won over the fossil-fuel unit and on what date", 1474),
    # i=53 target 1453 (upstairs tap drip: worn ceramic cartridge, not washer)
    ("what part was actually leaking in the first-floor faucet after the wrong fix", 1491),
    # i=54 target 1454 (Farrow & Ball Skimming Stone preferred over magnolia for hallway)
    ("which paint shade took over the corridor from the default builder's off-white", 1492),
    # i=55 target 1455 (loft insulation top-up completed 2026-02-28, rating D to C)
    ("when did the attic thermal upgrade finish and what grade did it shift to", 1488),
    # i=56 target 1456 (raised bed layout three frames along south fence, gravel path)
    ("how are the grow boxes arranged along the rear boundary with the walkway", 1478),
    # i=57 target 1457 (Carmichael Electrical for consumer unit upgrade after DIY trips)
    ("which contractor took over the fuse-box job after failed self-attempts", 1468),
    # i=58 target 1458 (bathroom retile took eleven days because screed dipped 9mm)
    ("why did the lavatory tiling project blow out its schedule", 1477),
    # i=59 target 1459 (gutter-cleaning twice a year, late March and early November)
    ("how often and when do I clean the roof drainage channels", 1496),
    # i=60 target 1460 (noise, grab the measuring tape)
    ("what was the throwaway remark about the measuring tape before continuing", 1484),
    # i=61 target 1461 (Hitachi Airhome 3000 specced 8kW after heat-loss survey 6.4kW)
    ("which air-source unit model got picked after the thermal load calculation", 1500),
    # i=62 target 1462 (oil-based decking stain preferred over water-based after two seasons)
    ("which timber-treatment base outperformed the other on the sunny deck", 1475),
    # i=63 target 1463 (MPS Solar quote 2026-04-05 £9,800 for 4.2kWp plus 5kWh battery)
    ("what did the photovoltaic proposal cost and how close were the rival quotes", 1474),
    # i=64 target 1464 (chain-link fence replaced with closeboard along east boundary 2026-01-18)
    ("when did the east-side perimeter fence swap finish and what panel style went up", 1485),
    # i=65 target 1465 (smart thermostat install 2026-03-02, Ecobee needed C-wire adapter)
    ("what wiring piece did the new climate controller demand mid-install", 1497),
    # i=66 target 1466 (hand-pruning three apple trees in February preferred over tree surgeon)
    ("which winter fruit-tree maintenance approach won over bringing in a professional", 1493),
    # i=67 target 1467 (Gravelly Hill Motors services Honda HRX mower, £85 a visit)
    ("which workshop keeps the rotary mower running and what does the visit cost", 1489),
    # i=68 target 1468 (scrapped DIY rewire after reading building regs, need certified sparks)
    ("why did I drop self-rewiring and who took over instead", 1457),
    # i=69 target 1469 (three-bay Dalek compost setup behind shed, sixteen week cycle)
    ("how is the garden waste rotting system organised behind the outbuilding", 1499),
    # i=70 target 1470 (planning permission side extension approved 2026-02-14 after daylight rejection)
    ("when did the lateral house extension get council sign-off and what had blocked it", 1482),
    # i=71 target 1471 (driveway sealing 2026-04-02 took two dry days)
    ("when did the tar drive refresh happen and how much did it perk the surface", 1477),
    # i=72 target 1472 (triple-glazed casements chosen over double for north elevation, U-values)
    ("which window spec won out on the cold side of the house and why", 1488),
    # i=73 target 1473 (fruit tree pruning schedule taped in shed: apples February, plums July)
    ("where is the orchard trimming calendar kept and what months does it cover", 1496),
    # i=74 target 1474 (boiler replacement quote Anchor Heating £3,450 Worcester 30Si)
    ("what did the gas heater quote come to and which model was specced", 1463),
    # i=75 target 1475 (mineral weather-stripping foam preferred over rubber bulb seals on back door)
    ("which draught-sealing material wins on the rear entrance after a cold season", 1443),
    # i=76 target 1476 (side gate hinge snapped 2026-01-05, replaced with stainless and latch)
    ("when did the garden gate pivot give way and what combined upgrade followed", 1464),
    # i=77 target 1477 (oak floor refinished in lounge 2026-03-20, water-based matt lacquer)
    ("when did the living-room timber floor get redone and what finish went on", 1458),
    # i=78 target 1478 (gardening calendar: sow tomatoes 2026-03-10, harden 04-28, plant 05-15)
    ("what is the three-date timetable for the nightshade crop this spring", 1490),
    # i=79 target 1479 (property tax appeal 2026-02-22 dropped band F to E)
    ("when did the council tax challenge succeed and what evidence carried it", 1481),
    # i=80 target 1480 (no-dig method doubled brassica yield versus rotavated patch in 2025)
    ("which bed-prep technique beat rotavating for cabbages last growing season", 1469),
    # i=81 target 1481 (mortgage refinance Halifax 2026-01-28, 4.12% five years, saved £218)
    ("when did the house-loan remortgage close and what was the rate and monthly saving", 1479),
    # i=82 target 1482 (Priya Patel signed off load-bearing wall removal 2026-02-10, steel W8x18)
    ("who approved the interior wall knock-through and what beam went in", 1470),
    # i=83 target 1483 (B&Q Shaker white chosen over Howdens for utility cabinets)
    ("which cabinet supplier won the utility room run over the rival and by how much", 1492),
    # i=84 target 1484 (noise, find the receipt)
    ("what was the throwaway aside about hunting the receipt in the transcript", 1460),
    # i=85 target 1485 (neighbour fence dispute started 2025-11-04, resolved January with surveyor)
    ("when did the boundary argument with next door begin and how did it settle", 1464),
    # i=86 target 1486 (Makita 18V preferred over DeWalt 20V for household tools)
    ("which cordless power tool platform won out and for what reason", 1493),
    # i=87 target 1487 (underfloor heating manifold in downstairs WC cupboard, 1.3 bar at rest)
    ("where is the floor-heat distribution block and what pressure should it hold", 1491),
    # i=88 target 1488 (EPC jumped D60 to B84 on 2026-04-08 after loft, windows, heat pump)
    ("when did the EPC banding jump and which three upgrades stacked to get it there", 1455),
    # i=89 target 1489 (mower blade bent 2025-09-12 hitting buried paving slab)
    ("when did the mower blade get damaged and what hidden object caused it", 1467),
    # i=90 target 1490 (bedding plant rotation: tulips October to April, dahlia May)
    ("how do the front-garden beds switch over across the seasons", 1478),
    # i=91 target 1491 (garden tap isolated 2026-01-22 for split pipe, stopcock behind downstairs panel)
    ("when did the outside tap need shut-off and where does the main valve hide", 1453),
    # i=92 target 1492 (Howdens chosen for kitchen carcasses despite B&Q win, oak matched Karndean)
    ("which supplier won the kitchen cabinets even after the utility decision went the other way", 1483),
    # i=93 target 1493 (Stihl MSA 220 chainsaw preferred over petrol MS 180 for pruning)
    ("which brand chainsaw now wins for pruning work and why", 1486),
    # i=94 target 1494 (washing machine flood 2025-12-02 from failed inlet hose, now change every 5 years)
    ("which laundry appliance leak triggered the maintenance rule I keep now", 1497),
    # i=95 target 1495 (Bevan Builds chosen over Rockhill for extension, finished jobs nearby)
    ("which building firm landed the extension job and on what evidence", 1474),
    # i=96 target 1496 (annual lawn routine one page: scarify early April, aerate late April, feed May+August, overseed September)
    ("what is the single-page lawn calendar I stick to every year", 1473),
    # i=97 target 1497 (Ring doorbell 802.11 band mismatch, hub only 2.4 GHz, dedicated SSID fix)
    ("what network gotcha blocked the front-door camera setup and how was it resolved", 1465),
    # i=98 target 1498 (Grohe Grohtherm replaced old thermostatic shower valve 2026-03-25, 38C lock)
    ("when did the shower mixer get upgraded and what safety feature came with it", 1477),
    # i=99 target 1499 (compost bin half-full of leaf mould from 2025 autumn, spread on roses late April)
    ("what is in the garden bin from last autumn and when does it go on the roses", 1469),
]


def _count_words(s: str) -> int:
    return len(s.split())


def main() -> int:
    assert len(ENTRIES) == 100, f"expected 100 entries, got {len(ENTRIES)}"

    with SHARED.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as out:
        for i, (query, neg_line) in enumerate(ENTRIES):
            target_line = SHARED_OFFSET + i
            if target_line == neg_line:
                raise ValueError(f"entry {i}: negative line equals target line {target_line}")
            wc = _count_words(query)
            if wc < 5 or wc > 25:
                raise ValueError(f"entry {i}: query word count {wc} out of range 5..25: {query!r}")

            target_row = json.loads(lines[target_line - 1])
            negative_row = json.loads(lines[neg_line - 1])

            row = {
                "id": f"retrieval-{ID_OFFSET + i:05d}",
                "source_id": target_row["id"],
                "query": query,
                "negative": negative_row["text"],
                "query_kind": QUERY_KIND,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(ENTRIES)} rows to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
