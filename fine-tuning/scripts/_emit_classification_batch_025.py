"""One-off emitter for classification top-up batch-025 — contrastive_decision_architecture mode, home and household slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_025.tmp.jsonl with ids class-02401..02500.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_025.tmp.jsonl"
ID_OFFSET = 2400
PAIR_OFFSET = 950

# (decision_text, decision_domain, architecture_text, architecture_domain)
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. heating — per-room radiators
    (
        "Switched the house from a single Nest thermostat to per-room Mysa radiators after the south bedroom kept running eight degrees hotter than the hallway sensor.",
        "personal",
        "Each room runs a Mysa electric radiator on a schedule keyed to occupancy from Home Assistant, with a global 19°C setback between 23:00 and 06:00 and a 21°C wake window in the primary bedroom.",
        "personal",
    ),
    # 2. cooling — portable AC + fans
    (
        "Decided against central air in the rental and bought a 12 000 BTU portable unit for the living room after pricing a mini-split install at nine thousand pounds.",
        "personal",
        "Summer cooling is a living-room portable AC vented out the west window plus three Dyson tower fans on linked Home Assistant automations that pull cool air toward the bedrooms after sunset.",
        "personal",
    ),
    # 3. lighting — circadian
    (
        "Replaced every bulb in the flat with Philips Hue after repeated arguments over whether the kitchen lights should auto-dim in the evening.",
        "personal",
        "Lighting runs on a Hue Bridge with circadian scenes that shift color temperature from 6500 K at 07:00 to 2200 K by 21:30, and motion sensors drive the hallway and bathroom lamps at 10% between 23:00 and 06:00.",
        "personal",
    ),
    # 4. smart locks
    (
        "Installed an August Wi-Fi smart lock on the front door after the cleaner lost the physical key for the third time in a year.",
        "personal",
        "The front door runs an August 4th-gen lock tied to HomeKit with per-user PIN codes, auto-lock after four minutes, and geofenced unlock disabled in favor of explicit tap-to-unlock.",
        "personal",
    ),
    # 5. cameras
    (
        "Chose Reolink PoE cameras over Ring after realizing the cloud subscription would cost more than the hardware across three years.",
        "personal",
        "Outdoor surveillance is four Reolink RLC-811A cameras on a PoE switch recording 24/7 to a Synology DS223 with Surveillance Station, retaining 14 days of continuous and 60 days of motion-only footage.",
        "personal",
    ),
    # 6. irrigation
    (
        "Swapped the hose-timer tap for a Rachio 3 after two summers of either overwatering the tomatoes or forgetting them entirely during heatwaves.",
        "personal",
        "Garden irrigation is a Rachio 3 controller driving six drip zones, scheduled via Flex Daily using local weather and soil-type settings, with a rain-skip threshold of 4 mm in the prior 24 hours.",
        "personal",
    ),
    # 7. laundry cadence
    (
        "Moved from doing laundry whenever the basket overflowed to a fixed Tuesday-and-Saturday rhythm after we ran out of school uniforms on a Monday morning.",
        "personal",
        "Household laundry runs twice weekly: darks plus school uniforms on Tuesday evening, whites plus towels on Saturday morning, with bedding on the first Sunday of each month.",
        "personal",
    ),
    # 8. cleaning rotation
    (
        "Dropped the weekly whole-house deep clean and split the flat into four zones after both of us burned out on Sunday afternoons.",
        "personal",
        "The flat is divided into four cleaning zones — kitchen, bathrooms, living and bedrooms, entry and hallway — each getting a 45-minute deep clean once a week on a rotating Mon/Wed/Fri/Sun pattern.",
        "personal",
    ),
    # 9. grocery restock
    (
        "Cancelled the weekly Ocado big shop and switched to a Monday top-up plus a Thursday fresh-only run after we kept throwing out half a bag of spinach every week.",
        "personal",
        "Grocery replenishment is a two-run cadence: Monday click-and-collect for staples and frozen goods from Sainsbury's, Thursday evening walk to the local greengrocer for produce and bread for the back half of the week.",
        "personal",
    ),
    # 10. pet care schedule
    (
        "Moved the dog's dinner from 18:00 to 19:30 after the vet flagged that the early feed plus the late walk was causing stomach upset.",
        "personal",
        "The labrador is fed twice daily — 07:15 and 19:30, 180 g of kibble — walked 45 minutes before breakfast and 30 minutes before the late meal, and groomed every third Saturday.",
        "personal",
    ),
    # 11. bill splitting
    (
        "Ditched the monthly spreadsheet reconciliation and put every shared bill on Splitwise after a heated argument about who paid the last council tax instalment.",
        "personal",
        "Shared household costs run through a Splitwise group with 55/45 weighting reflecting income, auto-logged from a joint Monzo Plus account that pays rent, utilities, broadband, and the Ocado standing order.",
        "personal",
    ),
    # 12. calendar sync
    (
        "Abandoned the whiteboard on the fridge and moved the family calendar into a shared Google Calendar after the school parents' evening was double-booked with a work trip.",
        "personal",
        "The family runs a shared Google Calendar named Household visible to both adults, overlaid with each person's work calendar and a read-only kids' school calendar imported via iCal, with a morning digest sent to both phones at 07:00.",
        "personal",
    ),
    # 13. weekly meal plan
    (
        "Switched from ad-hoc weeknight cooking to a fixed Sunday meal plan after realizing we ordered takeaway four nights of the week in January.",
        "personal",
        "The meal plan is written every Sunday in a shared Notion page with five weeknight dinners mapped to the Thursday grocery list, one flexible leftovers night on Friday, and a designated batch-cook slot on Saturday morning.",
        "personal",
    ),
    # 14. family chore board
    (
        "Replaced the nagging-based chore system with a Trello board after the 9-year-old asked why the adults never had anything to do.",
        "personal",
        "Chores are tracked on a shared Trello board with one list per family member, cards moving Backlog → This Week → Done, a recurring Butler automation reseeding the weekly cards every Sunday at 18:00.",
        "personal",
    ),
    # 15. childcare handoffs
    (
        "Moved the school run from a shared 50/50 arrangement to me handling mornings and my partner handling pickup after the 08:30 client stand-ups made drop-off impossible twice a week.",
        "personal",
        "Childcare coverage is asymmetric: one parent does breakfast, uniform check, and the 08:20 school walk; the other does 15:30 pickup, after-school snack, and homework supervision until 17:30 when the shared dinner prep begins.",
        "personal",
    ),
    # 16. guest hosting
    (
        "Converted the study to a guest room with a sofa bed after hosting in-laws on the living room floor for a second Christmas running.",
        "personal",
        "The study doubles as a guest room with a Muji sofa bed, a lockable file drawer for work documents, a dedicated Wi-Fi SSID issued per visit, and linens stored in a vacuum bag on the top wardrobe shelf.",
        "personal",
    ),
    # 17. charger placement
    (
        "Relocated the phone-charging station from the kitchen counter to a drawer in the hallway console after both phones ended up next to dinner plates every night.",
        "personal",
        "Device charging lives in the hallway console drawer: a six-port Anker 100W GaN brick powers two MagSafe pucks, a watch stand, and two USB-C cables, with a house rule that all phones dock there between 21:30 and 07:00.",
        "personal",
    ),
    # 18. Wi-Fi layout
    (
        "Tore out the ISP-provided single-router setup and installed a three-node Unifi mesh after the loft office kept dropping to 2 Mbps during video calls.",
        "personal",
        "Home networking runs on a UDM-SE with three U6-Pro access points — hallway, loft, garden room — on a dedicated IoT VLAN for smart devices and a separate guest VLAN with client isolation.",
        "personal",
    ),
    # 19. emergency kit
    (
        "Built a proper grab-bag by the front door after a four-hour power cut in February caught us without torches or cash.",
        "personal",
        "The household emergency kit is a Stanley tote in the front hall containing two headlamps with spare AAA cells, a hand-crank radio, 50 pounds cash in small notes, printed ICE contacts, basic first-aid, and a water purifier tablet sleeve.",
        "personal",
    ),
    # 20. trash/recycling rota
    (
        "Set a Monday-evening bin reminder after missing the fortnightly recycling collection twice in three months.",
        "personal",
        "Bins go out Monday 21:00: black bag weekly to the street, green recycling box and blue paper bag alternating fortnights, food caddy every Monday, with a shared Home Assistant notification sent to both phones at 20:45.",
        "personal",
    ),
    # 21. dishwasher loading
    (
        "Standardized on running the dishwasher every night after dinner instead of when full, once we realized clean-hand dish counts were creeping up and bowls kept running out at breakfast.",
        "personal",
        "The Bosch dishwasher runs nightly at 21:30 on the Eco 50 cycle, loaded according to a fixed scheme — plates front of lower basket, mugs back row of upper, knives points-down in the cutlery rack — and unloaded as part of the morning coffee routine.",
        "personal",
    ),
    # 22. composting
    (
        "Switched from curbside food caddy only to an additional garden Bokashi bin after realizing the council caddy filled up mid-week in summer.",
        "personal",
        "Food waste is split two ways: a Bokashi bucket under the sink fermenting for two weeks before burial in the raised beds, and the council food caddy taking meat, dairy, and cooked leftovers with pickup every Monday.",
        "personal",
    ),
    # 23. houseplant watering
    (
        "Moved from watering houseplants whenever I remembered to a strict Saturday-morning round after losing two fiddle-leaf figs in a year.",
        "personal",
        "Indoor plants are watered every Saturday at 09:00 on a room-by-room route, with moisture meters on the two ficus trees, a weekly rotate-a-quarter-turn rule for even light, and a monthly liquid feed from March through September.",
        "personal",
    ),
    # 24. mail and packages
    (
        "Set up a lockable Amazon Key drop-off box by the gate after the third stolen parcel of the quarter.",
        "personal",
        "Incoming deliveries go into a Yale parcel box bolted to the porch, code rotated monthly and shared with Amazon, DPD, and Royal Mail; mail goes through a slot into an internal cage emptied every evening as part of the lockup routine.",
        "personal",
    ),
    # 25. TV/media room
    (
        "Replaced the living-room cable box with an Apple TV 4K and Plex setup after BT Sport and Netflix kept fighting over HDMI-CEC and confusing the kids.",
        "personal",
        "The living-room media stack is a 65-inch LG C3, Apple TV 4K feeding HomeKit scenes, a Sonos Arc plus two Era 300 rears, and a Plex server on the home NAS indexing the family film library and backed-up Blu-rays.",
        "personal",
    ),
    # 26. thermostat overrides
    (
        "Gave each family member the ability to bump the heat two degrees for one hour via voice, after the 14-year-old kept leaving the heating on 24°C overnight in her room.",
        "personal",
        "Heating overrides are constrained in Home Assistant: any voice request can raise a single zone by at most 2°C for at most 60 minutes before reverting, with a nightly 23:00 reset forcing all zones back to the default schedule.",
        "personal",
    ),
    # 27. visitor Wi-Fi
    (
        "Split the home Wi-Fi into a main and a guest SSID after realizing our babysitter's phone had persistent access to the main network for six months.",
        "personal",
        "Wi-Fi is segmented into three SSIDs on the Unifi controller: Home on the primary VLAN for trusted devices, Guest on an isolated VLAN with a rotating daily password posted on the fridge, and IoT for smart-home devices with no internet except whitelisted endpoints.",
        "personal",
    ),
    # 28. lawn care
    (
        "Hired a fortnightly gardener for the front lawn after the mower broke for the second time and it became cheaper than replacing it.",
        "personal",
        "Outdoor grounds are maintained on a split schedule: a contracted gardener handles mowing, hedges, and leaf blowing every other Thursday; the household handles weeding the beds and topping up the bird feeders every Sunday morning.",
        "personal",
    ),
    # 29. kids' screen time
    (
        "Stopped enforcing ad-hoc screen-time negotiations and rolled out Apple Screen Time with Family Sharing after every weekend devolved into the same argument.",
        "personal",
        "Kids' screen time is governed by Family Sharing: 90 minutes of entertainment apps on weekdays unlocking at 17:00, 180 minutes on weekends, Downtime enforced 21:00 to 07:30, educational apps Always Allowed, and requests for new apps routed to a parent Apple ID.",
        "personal",
    ),
    # 30. key management
    (
        "Bought a small Yale key safe for the porch after giving the cleaner a physical key and then having to rekey the lock when she left the job.",
        "personal",
        "Physical keys are controlled via a YSS/30 key safe bolted to the porch wall holding a single spare, code rotated after any staff change; primary keys live on two Tile-tagged keyrings, one per adult, with a backup set at a neighbour's house.",
        "personal",
    ),
    # 31. grocery budgeting
    (
        "Set a weekly grocery cap of 140 pounds in YNAB after six straight months of going over the food category by roughly 30%.",
        "personal",
        "Grocery spending is enforced through a YNAB category with a weekly 140 pound target, split 70/70 across the Monday Sainsbury's order and the Thursday greengrocer run, and overflow going to an emergency category at week end before being reset on Sunday.",
        "personal",
    ),
    # 32. bedtime routine
    (
        "Moved the children's bedtime forward by 30 minutes after persistent morning crankiness made the school run miserable.",
        "personal",
        "The kids' bedtime routine is fixed: 19:30 bath, 19:50 pyjamas and teeth, 20:00 story with low-color Hue scene, lights-out 20:20; the bedroom Mysa drops to 18°C by 20:30 and the hallway dims to 5% until 06:30.",
        "personal",
    ),
    # 33. morning coffee
    (
        "Retired the old drip machine and put a De'Longhi bean-to-cup on a smart plug after four winter mornings of cold, bitter coffee killed the routine.",
        "personal",
        "Morning coffee is a De'Longhi Magnifica on a Kasa smart plug scheduled to power up at 06:15 weekdays and 07:30 weekends, paired with a Brita-filtered water tank refilled every evening and beans ground fresh from a 250 g Pact bag rotating weekly.",
        "personal",
    ),
    # 34. winter prep
    (
        "Decided to bleed the radiators and service the boiler every October after discovering mid-January that the upstairs loop had been cold all season.",
        "personal",
        "Winter prep runs the first weekend of October: Worcester Bosch boiler service by a Gas Safe engineer, all twelve radiators bled top-down, magnetic filter cleaned, loft insulation checked, and outdoor taps isolated and drained.",
        "personal",
    ),
    # 35. freezer inventory
    (
        "Ditched the mental model of what was in the chest freezer and started a shared Notes list on the freezer door after discovering a two-year-old bag of salmon.",
        "personal",
        "The chest freezer in the garage is inventoried on a laminated checklist with date-written-on tape; items are FIFO-ordered, purged every three months, and logged in a shared Apple Note synced to both adults' phones so contents are visible at the shop.",
        "personal",
    ),
    # 36. bathroom cleaning
    (
        "Put a squeegee on a hook in the main shower after mildew on the grout returned within six weeks of a deep clean.",
        "personal",
        "Bathroom upkeep is a two-tier system: each user squeegees the shower walls after every use, and a weekly 20-minute Saturday deep clean covers toilets, sinks, mirrors, and a monthly grout spray with diluted HG Mould Remover.",
        "personal",
    ),
    # 37. seasonal wardrobe
    (
        "Swapped the four-season wardrobe to a two-season rotation after winter coats kept getting buried behind summer linen in March.",
        "personal",
        "Clothing storage is rotated twice a year — first weekends of April and October — with off-season items vacuum-bagged on top of the wardrobes and in-season items living in the bedroom; a donation bag lives under the stairs and is dropped at the charity shop whenever it fills.",
        "personal",
    ),
    # 38. home gym
    (
        "Converted the shed to a home gym after the third month of 20-pound drop-in charges at the local CrossFit became cheaper amortized than a squat rack.",
        "personal",
        "The garden shed is kitted out as a home gym with rubber mats, a Rogue squat rack, a 20 kg barbell with bumper plates to 140 kg, an Assault Bike, and a 50-inch TV on a Peloton app login; sessions are booked on a shared Google Calendar in 45-minute slots.",
        "personal",
    ),
    # 39. doorbell + intercom
    (
        "Installed a Reolink video doorbell after the courier left a 400-pound parcel in plain view of the street when no one answered.",
        "personal",
        "The front door has a Reolink PoE doorbell tied to Home Assistant; presses trigger a chime on the Sonos Arc, a notification to both adults' phones, and a 30-second clip saved to the Synology, with a snapshot posted to a shared Signal group.",
        "personal",
    ),
    # 40. car charging
    (
        "Had a 7.4 kW Zappi installed on the driveway after realizing granny-charging the Model 3 overnight wasn't keeping up with our actual mileage.",
        "personal",
        "EV charging uses a myenergi Zappi 7.4 kW wall unit tied to the solar PV diverter, scheduled to charge on the Octopus Go 00:30-05:30 window first, then top up from surplus solar between 11:00 and 15:00 whenever the battery is below 80%.",
        "personal",
    ),
    # 41. solar + battery
    (
        "Added a 10 kWh GivEnergy battery to the existing 5 kWp solar array after noticing half the summer generation was being exported at 15p and bought back at 28p.",
        "personal",
        "Energy at home is a 5 kWp SolarEdge roof array, a 10 kWh GivEnergy AC-coupled battery in the utility room, and a Zappi diverter, orchestrated via predbat in Home Assistant to charge the battery on cheap Agile slots and discharge across peak rate.",
        "personal",
    ),
    # 42. home office setup
    (
        "Moved the desk out of the bedroom into the spare room after six months of working, sleeping, and arguing in the same eight-square-metre space.",
        "personal",
        "The home office occupies the small back bedroom with an IKEA Bekant sit-stand desk, a 34-inch LG ultrawide, a Herman Miller Aeron on the local-authority-refurb scheme, a Shure MV7 on a boom arm, and a dedicated Ethernet drop from the hallway UniFi switch.",
        "personal",
    ),
    # 43. school lunch
    (
        "Stopped making school lunches every morning and switched to a Sunday-evening batch prep after oversleeping twice cost the kids their sandwiches in one week.",
        "personal",
        "School lunches are batch-prepped Sunday 17:00: five bento boxes laid out in the fridge with sandwich, fruit, carrot sticks, and a treat, morning routine only requires pulling two boxes out and topping up the thermos with yogurt.",
        "personal",
    ),
    # 44. bike storage
    (
        "Built a wall-mount rack in the garage after tripping over four bikes in the hallway for the last time.",
        "personal",
        "Family bikes live on a wall-mounted Steadyrack system in the garage, one hook per bike, with helmets on a peg rail, a floor pump chained to the rack leg, and a monthly Sunday chain-lube check as part of the cleaning rotation.",
        "personal",
    ),
    # 45. fridge organization
    (
        "Assigned zones inside the fridge after discovering three open packs of feta from different weeks at the back of the top shelf.",
        "personal",
        "Fridge contents follow a zone map taped inside the door: top shelf leftovers in labelled glass containers, middle shelf dairy and eggs, crisper left for greens, crisper right for root veg, door for condiments rotated front-to-back on first use.",
        "personal",
    ),
    # 46. medication schedule
    (
        "Added an Echo Show reminder after my partner missed two evening doses of blood-pressure medication in the same week.",
        "personal",
        "Daily medications are routed through a weekly pill organiser refilled Sunday morning and two Alexa routines — 08:00 morning dose and 21:00 evening dose — that chime on the kitchen Echo Show and escalate to a phone notification after ten minutes of no confirmation.",
        "personal",
    ),
    # 47. family backup
    (
        "Moved all household photos off four separate phones and onto a Synology NAS after one phone drop wiped six months of the baby's pictures.",
        "personal",
        "Family photos are consolidated on a Synology DS223 in the hall cupboard running Synology Photos, mobile clients on four devices auto-upload over Wi-Fi only, and the volume is replicated nightly to a Hyper Backup job on Backblaze B2.",
        "personal",
    ),
    # 48. pantry restock
    (
        "Switched from shopping when shelves looked empty to a fixed pantry-par system after running out of olive oil during the second week of a new job.",
        "personal",
        "The pantry operates on a par-level system listed on the inside of the door: two bottles olive oil, three kilos rice, four tins tomatoes, etc.; the Monday grocery list is generated by walking the door with a pencil and marking gaps against target levels.",
        "personal",
    ),
    # 49. visitor parking
    (
        "Bought a pack of visitor parking permits from the council after the third parking ticket on my mother-in-law's car in six months.",
        "personal",
        "Visitor parking is handled with a pack of 20 council-issued scratch-off permits kept in the hallway console drawer, restocked when fewer than five remain, and a Notion page logging each permit's date, visitor, and plate so usage stays within the annual cap.",
        "personal",
    ),
    # 50. annual house review
    (
        "Put a yearly first-Sunday-of-January household review on the calendar after New-Year resolutions about the house never survived past mid-February.",
        "personal",
        "The household runs an annual review on the first Sunday of January: both adults walk the house room by room with a laptop, updating a shared Notion page covering maintenance due, upcoming expenses, subscriptions to cancel, and one improvement project per quarter.",
        "personal",
    ),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (dec_text, dec_domain, arch_text, arch_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            dec_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            arch_id = f"class-{ID_OFFSET + (2 * i):05d}"
            f.write(json.dumps({"id": dec_id, "domain": dec_domain, "text": dec_text, "memory_type": "decision", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"id": arch_id, "domain": arch_domain, "text": arch_text, "memory_type": "architecture", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
