"""One-off emitter for classification top-up batch-015 — multi_type mode, personal+knowledge slice.

Writes 100 rows to data/v2/classification/batch_015.tmp.jsonl with ids class-01401..01500.
Distribution: 15 fact, 15 decision, 15 preference, 15 problem, 15 architecture, 15 milestone, 10 reference.
Domains: ~50 personal, ~50 knowledge. No pair_id.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_015.tmp.jsonl"
ID_OFFSET = 1400

# (domain, text, memory_type)
ROWS: list[tuple[str, str, str]] = [
    # ---------- fact (15): 8 personal, 7 knowledge ----------
    ("personal", "My apartment lease runs from the first of September through the end of August, and the landlord charges a flat fee for any late rent payment submitted past the fifth.", "fact"),
    ("personal", "The family cabin in Vermont was built by my grandfather in 1962 using lumber milled from spruce trees he cleared off the back lot himself.", "fact"),
    ("personal", "My driver's license expires on my birthday in 2029, and the state requires an in-person vision test before it can be renewed for another eight years.", "fact"),
    ("personal", "My partner grew up bilingual in Portuguese and English because her mother moved from Lisbon to Boston at the age of twenty-three for graduate school.", "fact"),
    ("personal", "The oak tree in the front yard is about ninety years old, according to the previous owner who counted the rings on a fallen limb during a storm cleanup.", "fact"),
    ("personal", "My father retired from the postal service in 2018 after thirty-four years of delivering mail along the same rural route in eastern Pennsylvania.", "fact"),
    ("personal", "Our dog Biscuit is a nine-year-old rescue beagle who weighs twenty-six pounds and takes a daily thyroid tablet with his breakfast.", "fact"),
    ("personal", "The local farmers market operates every Saturday from May through October in the public library parking lot, and nearly forty vendors set up each week.", "fact"),
    ("knowledge", "The Amazon rainforest produces roughly six percent of the planet's atmospheric oxygen and stores an estimated one hundred fifty billion tonnes of carbon in its biomass.", "fact"),
    ("knowledge", "The human genome contains approximately three billion base pairs distributed across twenty-three chromosome pairs, with protein-coding genes making up less than two percent of the total.", "fact"),
    ("knowledge", "Mount Everest grows roughly four millimeters taller each year due to the ongoing collision between the Indian and Eurasian tectonic plates along the Himalayan range.", "fact"),
    ("knowledge", "Honeybees communicate the direction and distance of nectar sources through a figure-eight waggle dance whose angle encodes the sun's bearing relative to the flowers.", "fact"),
    ("knowledge", "The Library of Congress in Washington holds over one hundred seventy million items across its collections, making it the largest library in the world by volume.", "fact"),
    ("knowledge", "Saturn's rings are composed almost entirely of water ice particles ranging from dust grains to boulders several meters across, orbiting within a band only tens of meters thick.", "fact"),
    ("knowledge", "The Great Barrier Reef stretches roughly two thousand three hundred kilometers along the northeastern coast of Australia and is visible from low earth orbit.", "fact"),

    # ---------- decision (15): 8 personal, 7 knowledge ----------
    ("personal", "I decided to switch from a gas stove to an induction cooktop when we remodel the kitchen next spring because of the faster heating and easier cleanup.", "decision"),
    ("personal", "After two years of commuting by car, I chose to sell the sedan and start biking to work because parking downtown had become both expensive and unreliable.", "decision"),
    ("personal", "We decided to postpone the honeymoon trip to Japan until next autumn so we could spend the summer renovating the new house without financial pressure.", "decision"),
    ("personal", "I committed to dropping the evening gym membership and training at home instead, since the hour-long round trip was cutting into time I wanted with the kids.", "decision"),
    ("personal", "After weighing tuition versus scholarships, I chose the in-state university over the private college and will redirect the savings toward a down payment on a condo.", "decision"),
    ("personal", "My sister and I agreed to split the cost of hiring a caregiver for our mother three afternoons a week rather than placing her in assisted living.", "decision"),
    ("personal", "I decided to stop drinking coffee after two in the afternoon because late caffeine was clearly fragmenting my sleep according to the sleep tracker data.", "decision"),
    ("personal", "We picked the smaller pediatric clinic across town over the large hospital network because their same-day appointment availability has been much more consistent.", "decision"),
    ("knowledge", "The World Health Organization decided in 2022 to add monkeypox to its list of public health emergencies of international concern, triggering coordinated surveillance across member states.", "decision"),
    ("knowledge", "In 1969 NASA chose lunar orbit rendezvous over direct ascent for Apollo missions because it dramatically reduced the mass that had to be launched from Earth.", "decision"),
    ("knowledge", "The European Central Bank decided to maintain its deposit facility rate unchanged through the first quarter of 2026 while monitoring core inflation in the eurozone.", "decision"),
    ("knowledge", "The International Astronomical Union decided in 2006 to reclassify Pluto as a dwarf planet after establishing a formal definition requiring orbital clearance of surrounding debris.", "decision"),
    ("knowledge", "The Japanese government decided to begin releasing treated water from the Fukushima Daiichi site into the Pacific in 2023 following IAEA safety review.", "decision"),
    ("knowledge", "The Intergovernmental Panel on Climate Change chose in its sixth assessment cycle to present scenario pathways rather than a single probabilistic forecast of future warming.", "decision"),
    ("knowledge", "The Nobel Committee in Stockholm decided to award the 2024 prize in physics jointly to two researchers whose foundational work laid the groundwork for artificial neural networks.", "decision"),

    # ---------- preference (15): 8 personal, 7 knowledge ----------
    ("personal", "I strongly prefer cooking with cast iron over nonstick pans because the seasoning improves with use and I can move the same pan from stovetop to oven without worry.", "preference"),
    ("personal", "My morning routine is non-negotiable: I like black tea rather than coffee, a short walk rather than a run, and thirty minutes of reading before checking any messages.", "preference"),
    ("personal", "When traveling I would rather stay in small family-run guesthouses than chain hotels because the hosts usually point me toward the best local food spots.", "preference"),
    ("personal", "For weekend dinners I prefer slow braises and stews over quick sears because the house smells wonderful for hours and leftovers actually taste better the next day.", "preference"),
    ("personal", "I like paperback novels much more than e-readers for fiction, though I happily use the tablet for cookbooks and technical references that benefit from search.", "preference"),
    ("personal", "My dad prefers watching baseball on the radio to watching on television because the announcers paint a more vivid picture and the pace feels less frantic.", "preference"),
    ("personal", "I would rather hike an unfamiliar trail in early spring than midsummer because the lack of foliage makes it easier to read the landscape and navigate without a map.", "preference"),
    ("personal", "When it comes to gifts, I like handwritten letters and homemade food far more than anything bought in a store, even if the store-bought item costs more.", "preference"),
    ("knowledge", "Many classical musicians prefer gut strings over synthetic ones for baroque repertoire because the warmer overtones better match the tonal expectations of period performance.", "preference"),
    ("knowledge", "Field ecologists tend to prefer camera traps over live trapping when studying nocturnal mammals because the method is far less stressful for the animals and yields longer observation windows.", "preference"),
    ("knowledge", "Sommeliers typically prefer decanting older reds for thirty minutes rather than an hour because the delicate aromatics of aged wine can dissipate with too much air exposure.", "preference"),
    ("knowledge", "Astronomers generally prefer ground-based adaptive optics for nearby targets but still favor space telescopes like Hubble and JWST for deep-field infrared surveys.", "preference"),
    ("knowledge", "Pastry chefs often prefer European-style butter with higher fat content over American supermarket butter because lamination for croissants becomes noticeably more forgiving.", "preference"),
    ("knowledge", "Professional translators working with poetry tend to prefer preserving rhythm and image over literal fidelity because readers respond more strongly to cadence than to exact word choice.", "preference"),
    ("knowledge", "Long-distance runners often prefer negative splits over even pacing in marathons because finishing with a faster second half tends to correlate with better overall times and lower injury rates.", "preference"),

    # ---------- problem (15): 8 personal, 7 knowledge ----------
    ("personal", "The upstairs bathroom has been leaking into the ceiling below for at least a week, and the drywall is now showing a brown ring roughly the size of a dinner plate.", "problem"),
    ("personal", "My car has been making a grinding noise whenever I brake at low speed, and the dealership told me the rear rotors are warped and will need to be replaced.", "problem"),
    ("personal", "My son has been struggling with math homework all semester because the teacher moved on from long division before he had fully grasped place-value reasoning.", "problem"),
    ("personal", "The backyard fence collapsed during last week's windstorm, and the neighbor's dog has already crossed into our yard three times looking for our compost bin.", "problem"),
    ("personal", "I have been dealing with chronic wrist pain that flares up every afternoon at my desk, and the physical therapist suspects a repetitive strain injury from poor posture.", "problem"),
    ("personal", "The basement floods every spring because the exterior grading slopes toward the foundation on the east side, and last year's sump pump could not keep up.", "problem"),
    ("personal", "My mother has been forgetting medication doses more frequently, and her weekly pill organizer is not enough structure anymore to keep her schedule reliable.", "problem"),
    ("personal", "Our home internet drops out every evening around seven, and the modem logs suggest the cable segment is being oversubscribed once the neighborhood streams.", "problem"),
    ("knowledge", "Antibiotic resistance is spreading faster than new drug development pipelines can keep up, and several gram-negative pathogens now have no reliably effective treatment options.", "problem"),
    ("knowledge", "Coral reefs worldwide are experiencing mass bleaching events at accelerating intervals because sea surface temperatures are rising beyond the thermal tolerance of symbiotic zooxanthellae.", "problem"),
    ("knowledge", "Urban light pollution has reduced visible star counts in most major cities to fewer than two dozen, disrupting migratory bird navigation and circadian biology in several species.", "problem"),
    ("knowledge", "Groundwater aquifers across the American Southwest are being depleted faster than natural recharge can replenish them, threatening both agricultural output and municipal water supplies.", "problem"),
    ("knowledge", "Microplastic contamination has been detected in human placental tissue, raising unresolved questions about long-term developmental effects that current toxicology studies cannot yet answer.", "problem"),
    ("knowledge", "The global bee population has declined significantly over the past two decades due to combined pressures from neonicotinoid pesticides, Varroa mites, and habitat loss.", "problem"),
    ("knowledge", "Arctic permafrost is thawing at rates that release stored methane faster than climate models anticipated, creating a feedback loop that accelerates further warming.", "problem"),

    # ---------- architecture (15): 8 personal, 7 knowledge ----------
    ("personal", "My monthly budget splits net income fifty, thirty, and twenty percent across fixed bills, flexible spending, and brokerage transfers, with a separate buffer account holding one full month of expenses.", "architecture"),
    ("personal", "Our household laundry system runs on a three-basket rotation by color in the bedroom, with a single hamper downstairs for towels and linens washed on Sundays.", "architecture"),
    ("personal", "The family calendar layers a shared Google account for appointments, a paper whiteboard in the kitchen for weekly meals, and a private notebook for each parent's work commitments.", "architecture"),
    ("personal", "My pantry is organized by meal type on four shelves: breakfast grains up top, baking supplies middle, savory staples below that, and snacks at eye level for the kids.", "architecture"),
    ("personal", "The garden is divided into four raised beds rotated annually through tomatoes, brassicas, legumes, and cover crops to keep soil-borne disease pressure manageable.", "architecture"),
    ("personal", "Our emergency plan designates one out-of-state relative as the family contact, a meeting spot at the corner park, and a waterproof binder holding document copies in the hall closet.", "architecture"),
    ("personal", "My weekly meal prep splits Sunday afternoon into three stages: roast a tray of vegetables, cook two grains, and portion five protein servings into glass containers for the week.", "architecture"),
    ("personal", "The household finances run on a two-account structure where one checking account receives all paychecks and a second account covers discretionary spending after the monthly auto-transfer.", "architecture"),
    ("knowledge", "The three-branch structure of the United States federal government distributes legislative, executive, and judicial authority across Congress, the presidency, and the federal courts with explicit checks on each branch.", "architecture"),
    ("knowledge", "A coral reef ecosystem is structured in vertical zones from the reef crest down through the fore-reef slope, with distinct communities of fish and invertebrates adapted to each depth and light regime.", "architecture"),
    ("knowledge", "The human circulatory system runs as a double loop: the pulmonary circuit exchanges gases between heart and lungs while the systemic circuit delivers oxygenated blood to the rest of the body.", "architecture"),
    ("knowledge", "A Gothic cathedral distributes its load through pointed arches, flying buttresses, and ribbed vaults, which together allowed medieval builders to open walls for large stained glass windows.", "architecture"),
    ("knowledge", "The scientific method cycles through observation, hypothesis, prediction, experimentation, and analysis, with each iteration refining the working model against empirical evidence.", "architecture"),
    ("knowledge", "A symphony orchestra is organized into four sections — strings, woodwinds, brass, and percussion — arranged on stage by volume and blend so the conductor can balance the overall sound.", "architecture"),
    ("knowledge", "The Dewey Decimal System partitions all of human knowledge into ten top-level classes, each subdivided into ten divisions and further into ten sections for finer cataloging.", "architecture"),

    # ---------- milestone (15): 8 personal, 7 knowledge ----------
    ("personal", "Last weekend I finally finished refinishing the hardwood floors in the living room, capping off a six-month renovation that included the kitchen cabinets and the downstairs bathroom.", "milestone"),
    ("personal", "My daughter learned to ride her bike without training wheels on the first warm Saturday of April after two weeks of wobbling practice in the cul-de-sac.", "milestone"),
    ("personal", "I paid off the final installment of my student loans last Friday, closing out nearly twelve years of monthly payments that began right after graduate school.", "milestone"),
    ("personal", "Our anniversary trip to Iceland in June marked the first overseas vacation my wife and I have taken together since our honeymoon more than a decade ago.", "milestone"),
    ("personal", "I ran my first half marathon last autumn, finishing the thirteen-point-one-mile course in just under two hours after six months of progressively longer weekend training runs.", "milestone"),
    ("personal", "My grandmother celebrated her ninetieth birthday in March, with four generations of the family gathered at her home in rural Michigan for a surprise afternoon party.", "milestone"),
    ("personal", "I got promoted to senior analyst last quarter after leading the migration project that consolidated four regional reporting workflows into a single automated pipeline.", "milestone"),
    ("personal", "My son took his first steps on the kitchen tile three days before his first birthday, wobbling from the refrigerator to my chair while laughing the entire way.", "milestone"),
    ("knowledge", "Humanity first reached the summit of Mount Everest in 1953 when Edmund Hillary and Tenzing Norgay climbed the final ridge and planted the flags of four nations at the top.", "milestone"),
    ("knowledge", "The Human Genome Project released its first complete draft sequence in 2001, marking a fundamental milestone in molecular biology that took over a decade and three billion dollars.", "milestone"),
    ("knowledge", "In July 1969 Apollo 11 landed the first humans on the lunar surface, with Neil Armstrong and Buzz Aldrin spending roughly two and a half hours outside the module.", "milestone"),
    ("knowledge", "The Large Hadron Collider announced the discovery of the Higgs boson in July 2012, completing the standard model of particle physics after nearly five decades of theoretical prediction.", "milestone"),
    ("knowledge", "The World Health Organization declared smallpox globally eradicated in 1980, the first and still only human infectious disease eliminated entirely through coordinated vaccination campaigns.", "milestone"),
    ("knowledge", "The International Space Station welcomed its first long-duration crew in November 2000, beginning a continuous human presence in low earth orbit that has not yet been interrupted.", "milestone"),
    ("knowledge", "James Webb Space Telescope captured its first full-color deep field image in July 2022, showing thousands of galaxies and the faint distortions of gravitational lensing around a foreground cluster.", "milestone"),

    # ---------- reference (10): 5 personal, 5 knowledge ----------
    ("personal", "According to the appraisal report filed by Sanderson Valuation Associates on March 14, 2025, the property's fair market value is recorded as four hundred twenty-seven thousand dollars.", "reference"),
    ("personal", "My pediatrician's clinical note dated September 8th, 2025 states that my daughter's growth curve is tracking in the seventieth percentile for height and the sixtieth for weight.", "reference"),
    ("personal", "The homeowners association covenant, section 4.2, specifies that exterior paint colors must be selected from the approved palette listed in Appendix B of the governing document.", "reference"),
    ("personal", "My employment contract, clause 11 on remote work, allows up to two in-person days per month to be waived with written approval from the direct supervisor.", "reference"),
    ("personal", "According to the veterinary records from Brookline Animal Hospital on February 2nd, 2025, our dog's rabies vaccination remains valid through February of 2028.", "reference"),
    ("knowledge", "The CDC's Morbidity and Mortality Weekly Report, volume 73, issue 12, documents the seasonal influenza hospitalization rates for the 2024 through 2025 flu season across reporting states.", "reference"),
    ("knowledge", "The Intergovernmental Panel on Climate Change Sixth Assessment Report, working group one chapter four, projects a likely range of global mean surface temperature rise through 2100 under several scenarios.", "reference"),
    ("knowledge", "Darwin's 'On the Origin of Species,' first edition published in 1859, introduces the mechanism of natural selection in chapter four under the heading of struggle for existence.", "reference"),
    ("knowledge", "The Bureau of Labor Statistics Occupational Outlook Handbook, 2024 through 2025 edition, projects employment for registered nurses to grow by six percent over the coming decade.", "reference"),
    ("knowledge", "According to the Oxford English Dictionary, third edition entry for 'serendipity', the word was coined by Horace Walpole in a letter written on January 28th, 1754.", "reference"),
]


def emit() -> int:
    assert len(ROWS) == 100, f"expected 100 rows, got {len(ROWS)}"
    # Distribution check
    from collections import Counter
    mt_counts = Counter(mt for _, _, mt in ROWS)
    expected = {"fact": 15, "decision": 15, "preference": 15, "problem": 15, "architecture": 15, "milestone": 15, "reference": 10}
    assert dict(mt_counts) == expected, f"memory_type distribution mismatch: {mt_counts}"
    dom_counts = Counter(d for d, _, _ in ROWS)
    assert dom_counts["personal"] + dom_counts["knowledge"] == 100, f"domain mismatch: {dom_counts}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (domain, text, mt) in enumerate(ROWS, start=1):
            row_id = f"class-{ID_OFFSET + i:05d}"
            wc = len(text.split())
            assert 15 <= wc <= 45, f"{row_id} word count {wc} out of range: {text}"
            f.write(json.dumps({"id": row_id, "domain": domain, "text": text, "memory_type": mt}, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
