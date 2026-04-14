"""One-off emitter for shared-base batch-043 — personal domain (parenting / kids / childcare slice).

Writes 50 rows to data/v2/shared/batch_043.tmp.jsonl with ids shared-02101..02150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_043.tmp.jsonl"
ID_OFFSET = 2100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The newborn sleep routine locks a 7pm bath, feed, swaddle, then dark room by 7:30pm; naps at 9, 12, 3 during the day.", "architecture", "personal", False,
     [("newborn sleep routine", "method"), ("7pm", "date"), ("7:30pm", "date"), ("dark room", "place")],
     [],
     "how is the infant bedtime sequence structured from bath to lights-out",
     "baby evening wind down bath feed swaddle dark room nap schedule"),
    # --- 2 ---
    ("Switched from the bouncer seat to a proper Ergobaby carrier on 2026-02-18 after the pediatrician flagged hip position concerns.", "decision", "personal", False,
     [("bouncer seat", "tool"), ("Ergobaby", "tool"), ("2026-02-18", "date"), ("pediatrician", "person")],
     [("Ergobaby", "bouncer seat", "REPLACES")],
     "which baby-wearing option took over from the bouncy chair and why",
     "infant carrier swap hip dysplasia pediatrician flag brand date"),
    # --- 3 ---
    ("Potty-training with Maya hit a regression in week three; the reward chart lost momentum, so I dropped stickers and went to verbal praise only.", "problem", "personal", False,
     [("Maya", "person"), ("reward chart", "tool"), ("stickers", "tool"), ("verbal praise", "method")],
     [("verbal praise", "stickers", "REPLACES")],
     "what derailed the toilet-learning plan with my daughter and what reward shift fixed it",
     "toddler toilet training regression week three sticker drop praise method"),
    # --- 4 ---
    ("Prefers the Montessori floor bed to a crib for the 14-month-old; she falls asleep without intervention three nights out of four now.", "preference", "personal", False,
     [("Montessori floor bed", "tool"), ("crib", "tool"), ("14-month-old", "person")],
     [("Montessori floor bed", "crib", "PREFERS")],
     "which sleeping arrangement won over the traditional cot for the toddler",
     "floor mattress self settle toddler cot swap independence rate"),
    # --- 5 ---
    ("Leo hit his first 12 steps in a row on 2026-03-11 from the couch to the TV stand; we called both grandparents that evening.", "milestone", "personal", False,
     [("Leo", "person"), ("2026-03-11", "date"), ("grandparents", "person")],
     [],
     "when did my son take his first sustained walking streak and who got the call",
     "toddler first walk unassisted living room date grandparents share"),
    # --- 6 ---
    ("The daycare rota splits the week: Monday and Wednesday at Little Acorns, Tuesday and Thursday with Nana, Friday home with me.", "architecture", "personal", False,
     [("Little Acorns", "organization"), ("Monday", "date"), ("Wednesday", "date"), ("Tuesday", "date"), ("Thursday", "date"), ("Nana", "person"), ("Friday", "date")],
     [],
     "how is the weekly childcare coverage divided between nursery, family, and home",
     "childcare schedule nursery grandparent home split weekday assignment"),
    # --- 7 ---
    ("Chose Brookside Primary over St Anne's on 2026-04-01 after the school tour; the nurture group programme was the deciding factor.", "decision", "personal", False,
     [("Brookside Primary", "organization"), ("St Anne's", "organization"), ("2026-04-01", "date"), ("nurture group", "method")],
     [("Brookside Primary", "St Anne's", "PREFERS")],
     "which primary school won out for enrolment and what programme tipped it",
     "school choice primary nurture group decision tour visit date"),
    # --- 8 ---
    ("The bedtime story rule: two picture books for Maya, then one chapter from the Narnia omnibus for Leo, lights out by 8:15pm.", "architecture", "personal", False,
     [("Maya", "person"), ("Narnia omnibus", "publication"), ("Leo", "person"), ("8:15pm", "date")],
     [],
     "what is the fixed story routine each kid gets before the lights go off",
     "bedtime story routine picture chapter book kid split lights time"),
    # --- 9 ---
    ("The pediatrician at Riverside Clinic is Dr Hamid; he handles both kids and keeps the MMR and boosters on a shared calendar reminder.", "reference", "personal", False,
     [("Riverside Clinic", "organization"), ("Dr Hamid", "person"), ("MMR", "concept")],
     [("Dr Hamid", "Riverside Clinic", "WORKS_AT")],
     "who is the family doctor for the children and how does he track their shots",
     "paediatrician clinic name shared vaccine calendar MMR booster track"),
    # --- 10. noise ---
    ("Hold on, I can hear the baby stirring upstairs.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Leo's first loose tooth came out on 2026-03-22 at the dinner table into a slice of pear; tooth fairy left £2 under the pillow.", "milestone", "personal", False,
     [("Leo", "person"), ("2026-03-22", "date"), ("pear", "food"), ("tooth fairy", "concept")],
     [],
     "when did my son lose his first baby tooth and how did the tooth fairy respond",
     "first tooth loss dinner fruit bite date tooth fairy reward amount"),
    # --- 12 ---
    ("The screen-time rule for the kids is 30 minutes on weekdays after homework, 90 minutes on weekends; nothing after 6pm either way.", "architecture", "personal", False,
     [("screen-time rule", "concept"), ("weekdays", "date"), ("weekends", "date"), ("6pm", "date")],
     [],
     "how do I cap the children's daily viewing across school days and free days",
     "screen time policy weekday weekend cap homework evening cutoff"),
    # --- 13 ---
    ("Prefers co-sleeping side-car style to full room-sharing with the six-month-old; we get unbroken hands-free feeding without rolling risk.", "preference", "personal", False,
     [("co-sleeping", "method"), ("side-car", "method"), ("room-sharing", "method"), ("six-month-old", "person")],
     [("side-car", "room-sharing", "PREFERS")],
     "which night setup won out for feeding the infant safely",
     "bedside cot attached sleep arrangement feed safe infant roll risk"),
    # --- 14 ---
    ("Maya's first swim lesson at Waverley Leisure was 2026-02-07 with teacher Jen; she submerged her face voluntarily in week four.", "milestone", "personal", False,
     [("Maya", "person"), ("Waverley Leisure", "organization"), ("2026-02-07", "date"), ("Jen", "person")],
     [("Maya", "Waverley Leisure", "LOCATED_IN")],
     "when did my daughter start swimming lessons and when did she first go underwater",
     "swim lesson start date pool teacher face submerge milestone week"),
    # --- 15 ---
    ("The tantrum strategy that finally worked with Leo at 3: name the feeling, offer two low-stakes choices, then step back and wait three minutes.", "reference", "personal", False,
     [("Leo", "person")],
     [],
     "what three-step approach calms my son during his big outbursts at age three",
     "toddler meltdown plan emotion label limited choice wait three minute"),
    # --- 16 ---
    ("Replaced the Cocomelon YouTube rotation with the Bluey library on 2026-01-14 after Maya started copying the shrieky characters.", "decision", "personal", False,
     [("Cocomelon", "publication"), ("YouTube", "platform"), ("Bluey", "publication"), ("2026-01-14", "date"), ("Maya", "person")],
     [("Bluey", "Cocomelon", "REPLACES")],
     "which show took over my daughter's viewing and what behaviour triggered the swap",
     "kid show swap screen behaviour mimic shrieky replace date"),
    # --- 17 ---
    ("The sibling room-share in the back bedroom lasted eleven months; Leo's 6am wake-ups broke Maya's sleep, so we split them in March.", "problem", "personal", False,
     [("back bedroom", "place"), ("Leo", "person"), ("Maya", "person"), ("March", "date")],
     [],
     "why did the kids stop sharing a room and what timing pattern forced it",
     "sibling share bedroom split early wake disrupt sleep month decision"),
    # --- 18 ---
    ("Chose a shared nanny arrangement with the Fosters over a nursery place for the two-year-old; two kids per adult beat the 1:4 ratio.", "decision", "personal", False,
     [("shared nanny", "method"), ("Fosters", "person"), ("nursery", "organization"), ("two-year-old", "person")],
     [("shared nanny", "nursery", "PREFERS")],
     "which childcare form won for the toddler and on what staffing ratio argument",
     "shared nanny family arrangement nursery ratio toddler choice"),
    # --- 19 ---
    ("The first-phone negotiation landed on 2026-04-02: a Nokia 2660 flip for calls and texts only, no smartphone until year seven.", "milestone", "personal", False,
     [("2026-04-02", "date"), ("Nokia 2660", "tool"), ("smartphone", "tool"), ("year seven", "concept")],
     [],
     "when did we settle the first mobile for the kid and what device did we land on",
     "first phone negotiation flip model no smartphone date age gate school"),
    # --- 20 ---
    ("Prefers babyled weaning to spoon-fed purees for Leo; he hits a wider range of textures and the mealtime dynamic stays calmer.", "preference", "personal", False,
     [("babyled weaning", "method"), ("spoon-fed purees", "method"), ("Leo", "person")],
     [("babyled weaning", "spoon-fed purees", "PREFERS")],
     "which solids introduction method won out for my son and why",
     "baby led weaning over puree texture range mealtime calm compare"),
    # --- 21 ---
    ("The parent-teacher conference at Brookside on 2026-03-28 flagged Maya's reading is strong but handwriting grip needs the pencil hugger.", "reference", "personal", False,
     [("Brookside", "organization"), ("2026-03-28", "date"), ("Maya", "person"), ("pencil hugger", "tool")],
     [],
     "what did my daughter's teacher meeting surface about reading versus writing",
     "parent teacher meeting daughter reading strength grip aid recommendation"),
    # --- 22 ---
    ("Vaccination schedule with Dr Hamid is on the fridge: 12-month MMR done 2025-11-03, pre-school booster due 2029-04 for Leo.", "reference", "personal", False,
     [("Dr Hamid", "person"), ("MMR", "concept"), ("2025-11-03", "date"), ("2029-04", "date"), ("Leo", "person")],
     [],
     "where is the kids' shot calendar kept and what are the nearest dates on it",
     "vaccine schedule fridge MMR booster pre-school date doctor pediatrician"),
    # --- 23 ---
    ("The bedtime rift with Priya was the 7:30pm lights out versus her 8:30pm preference; we compromised on 7:45 on school nights, 8:30 on weekends.", "problem", "personal", False,
     [("Priya", "person"), ("7:30pm", "date"), ("8:30pm", "date"), ("7:45", "date"), ("school nights", "date"), ("weekends", "date")],
     [],
     "how did we resolve the bedtime disagreement with my partner across night types",
     "co-parent bedtime disagreement school night weekend compromise time"),
    # --- 24 ---
    ("Leo's kindergarten birthday party on 2026-02-15 was at the Clip 'n Climb Brookfield; ten kids, £175 all-in with cake and party bags.", "fact", "personal", False,
     [("Leo", "person"), ("2026-02-15", "date"), ("Clip 'n Climb Brookfield", "place")],
     [],
     "where did my son's kindergarten birthday happen and what was the headline cost",
     "kid birthday party venue climb indoor cost price cake bag count"),
    # --- 25 ---
    ("Prefers the car-seat-free bike trailer to the front-mount seat for both kids; the Thule holds two and the side-by-side stops the elbow fights.", "preference", "personal", False,
     [("bike trailer", "tool"), ("front-mount seat", "tool"), ("Thule", "tool")],
     [("bike trailer", "front-mount seat", "PREFERS")],
     "which bicycle kid carrier wins for both children and what social benefit comes with it",
     "bike trailer side by side two kid front seat swap elbow peace"),
    # --- 26 ---
    ("The chickenpox bout ran from 2026-01-22 through 2026-02-02 with both kids back to back; calamine, oat baths, and two missed swim lessons.", "problem", "personal", False,
     [("chickenpox", "concept"), ("2026-01-22", "date"), ("2026-02-02", "date"), ("calamine", "tool"), ("oat baths", "method"), ("swim lessons", "event")],
     [],
     "when did the pox episode run through the kids and what did we lean on to get through it",
     "chickenpox both kids back to back date range relief bath miss activity"),
    # --- 27 ---
    ("Registered Maya for Rainbows on 2026-03-05; first badge is the introducing badge and meetings are Tuesdays at the church hall from 5:30pm.", "milestone", "personal", False,
     [("Maya", "person"), ("Rainbows", "organization"), ("2026-03-05", "date"), ("Tuesdays", "date"), ("church hall", "place"), ("5:30pm", "date")],
     [("Maya", "Rainbows", "WORKS_AT")],
     "when did my daughter start with the rainbow group and what is the weekly rhythm",
     "Rainbows sign up first badge meeting night venue time weekly"),
    # --- 28 ---
    ("The custody week for Priya runs Monday 8am drop at school to Sunday 6pm handover at the park; my week mirrors it with swim and football built-in.", "architecture", "personal", False,
     [("Priya", "person"), ("Monday", "date"), ("Sunday", "date"), ("park", "place"), ("swim", "activity"), ("football", "activity")],
     [],
     "how are the alternating custody weeks shaped across both households",
     "custody week schedule alternate week parent activity handoff pickup"),
    # --- 29 ---
    ("Leo transitioned out of naps entirely on 2026-03-30; the 6:30pm bedtime shifted back to 7:15 and he now sleeps through a full eleven hours.", "milestone", "personal", False,
     [("Leo", "person"), ("2026-03-30", "date"), ("6:30pm", "date"), ("7:15", "date")],
     [],
     "when did my son drop his day sleep and what bedtime shift followed",
     "nap drop preschool age date bedtime push back sleep length"),
    # --- 30 ---
    ("The playdate rotation covers four families: Okoye, Harris, Patel, Nguyen; hosts alternate Saturdays, snacks shared, no sugar before noon.", "architecture", "personal", False,
     [("Okoye", "person"), ("Harris", "person"), ("Patel", "person"), ("Nguyen", "person"), ("Saturdays", "date")],
     [],
     "how is the weekend playdate circle structured across the four families",
     "playdate circle host rotation weekend snack rule sugar limit families"),
    # --- 31 ---
    ("Replaced the white-noise machine with the Yoto Mini on 2026-02-24; Maya settles faster with the Owl Babies audiobook on repeat.", "decision", "personal", False,
     [("white-noise machine", "tool"), ("Yoto Mini", "tool"), ("2026-02-24", "date"), ("Maya", "person"), ("Owl Babies", "publication")],
     [("Yoto Mini", "white-noise machine", "REPLACES")],
     "which sleep sound device took over for my daughter and what content replaced the static",
     "sleep sound device swap audio box story book settle faster date"),
    # --- 32 ---
    ("Prefers Bulleh's Nursery to Rainbow Cottage for the part-time spot; the garden access and key-worker stability outweighed the £40/week price gap.", "preference", "personal", False,
     [("Bulleh's Nursery", "organization"), ("Rainbow Cottage", "organization"), ("key-worker", "person")],
     [("Bulleh's Nursery", "Rainbow Cottage", "PREFERS")],
     "which nursery won the part-time placement and what pros beat the price gap",
     "nursery choice part time garden key worker price premium reasoning"),
    # --- 33 ---
    ("The homework battle with Maya over spelling practice ended after we moved it from post-dinner to pre-dinner; fifteen minutes only, done before play.", "problem", "personal", False,
     [("Maya", "person"), ("spelling practice", "activity")],
     [],
     "what timing shift fixed the spelling homework standoff with my daughter",
     "homework battle spelling shift pre dinner short window before play"),
    # --- 34. noise ---
    ("Ah, the school bus just pulled up outside.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Chose the cycle balance bike strategy over stabilisers for Leo; he moved to pedals in six weeks versus the eight-month average with training wheels.", "decision", "personal", False,
     [("balance bike", "method"), ("stabilisers", "tool"), ("Leo", "person"), ("pedals", "tool"), ("training wheels", "tool")],
     [("balance bike", "stabilisers", "REPLACES")],
     "which bike learning method won for my son and how much faster was it",
     "balance bike learn strategy stabiliser skip pedals fast transition"),
    # --- 36 ---
    ("The ear infection cycle with Maya broke after grommets went in on 2026-01-09 at Ellesmere ENT; four infections the prior winter, zero since.", "milestone", "personal", False,
     [("Maya", "person"), ("grommets", "tool"), ("2026-01-09", "date"), ("Ellesmere ENT", "organization")],
     [],
     "when did my daughter's repeat ear infections stop and what intervention made it",
     "ear infection grommet tube ENT surgery date winter count before after"),
    # --- 37 ---
    ("The car-seat handover rule with grandma: the Cybex Solution goes with whoever has the kids that weekend; the base stays in her Yaris.", "reference", "personal", False,
     [("grandma", "person"), ("Cybex Solution", "tool"), ("Yaris", "tool")],
     [("Cybex Solution", "Yaris", "LOCATED_IN")],
     "how do we handle the kid's booster seat across households with my mother",
     "car seat handover rule booster weekend rotate base fixed grandparent car"),
    # --- 38 ---
    ("The teenage independence milestone for the 13-year-old neighbour kid was the solo bus ride to town; Priya and I logged it for Maya's future benchmark.", "reference", "personal", False,
     [("13-year-old", "person"), ("solo bus ride", "activity"), ("Priya", "person"), ("Maya", "person")],
     [],
     "what independence step did we note from the older neighbour kid as a benchmark",
     "teen independence solo bus ride benchmark note future child comparison"),
    # --- 39 ---
    ("Prefers the child-led park hour to the structured music class on Saturdays; the open time does more for Leo's social picks than the instrument rotation.", "preference", "personal", False,
     [("child-led park hour", "activity"), ("music class", "activity"), ("Saturdays", "date"), ("Leo", "person")],
     [("child-led park hour", "music class", "PREFERS")],
     "which Saturday activity won for my son over the formal session and what did he gain",
     "free play park saturday over music class toddler social compare"),
    # --- 40 ---
    ("Switched the kids from cow's milk to oat milk on 2026-02-11 after Maya's skin flared; her eczema patches cleared within ten days.", "decision", "personal", False,
     [("cow's milk", "food"), ("oat milk", "food"), ("2026-02-11", "date"), ("Maya", "person"), ("eczema", "concept")],
     [("oat milk", "cow's milk", "REPLACES")],
     "which milk swap did we try for my daughter's skin and how fast did it help",
     "dairy to oat swap kids eczema skin flare clear window date"),
    # --- 41 ---
    ("The first driving lesson for Aunt Preeti's 17-year-old was 2026-04-05 with RED Driving School; useful prep data for when Maya gets there.", "fact", "personal", False,
     [("Aunt Preeti", "person"), ("17-year-old", "person"), ("2026-04-05", "date"), ("RED Driving School", "organization"), ("Maya", "person")],
     [],
     "when did my niece start driving lessons and why do I care about the detail",
     "first driving lesson school instructor date niece future reference own child"),
    # --- 42 ---
    ("The weekend morning protocol: kids handle breakfast solo from 7am if parents' door is shut; cereal, fruit, and the milk jug at floor height.", "architecture", "personal", False,
     [("breakfast", "food"), ("7am", "date"), ("cereal", "food"), ("fruit", "food"), ("milk jug", "tool")],
     [],
     "how do the kids self-serve the morning meal on weekends to give us a lie-in",
     "weekend morning self serve breakfast cereal fruit milk door closed cue"),
    # --- 43 ---
    ("Leo's reading level hit pink book band on 2026-03-15 after six weeks of paired reading each night; Priya tracked it in the parent-school diary.", "milestone", "personal", False,
     [("Leo", "person"), ("pink book band", "concept"), ("2026-03-15", "date"), ("paired reading", "method"), ("Priya", "person"), ("parent-school diary", "tool")],
     [],
     "when did my son move up the reading band and what practice got him there",
     "reading band jump pink pair reading nightly date diary track progress"),
    # --- 44 ---
    ("The croup episode on 2025-12-19 sent us to Queen Alexandra A&E at 2am; steam bathroom before the drive bought the barking cough time.", "problem", "personal", False,
     [("croup", "concept"), ("2025-12-19", "date"), ("Queen Alexandra A&E", "organization"), ("2am", "date"), ("steam bathroom", "method")],
     [],
     "when did the night-time breathing scare happen and what home trick bought us time",
     "croup middle of night hospital run steam bathroom barking cough relief"),
    # --- 45 ---
    ("Prefers the Saturday morning pancake ritual with both kids to the sit-down weekday breakfast; they help flip and it builds 40 minutes of together time.", "preference", "personal", False,
     [("pancake ritual", "activity"), ("Saturday morning", "date"), ("weekday breakfast", "activity")],
     [("pancake ritual", "weekday breakfast", "PREFERS")],
     "which family meal format wins for bonding with both children",
     "saturday pancake ritual bond weekday breakfast swap together minute"),
    # --- 46 ---
    ("The school-run carpool covers Brookside pickup Monday and Thursday with the Harris family; saves the 4pm commute collision with Priya's shifts.", "architecture", "personal", False,
     [("Brookside", "organization"), ("Monday", "date"), ("Thursday", "date"), ("Harris family", "person"), ("4pm", "date"), ("Priya", "person")],
     [],
     "how is the school pickup split with the Harris household across the week",
     "carpool split weekday school pickup neighbour shift collision avoid"),
    # --- 47 ---
    ("The teething relief ladder: chilled silicone ring first, cold flannel second, Calpol last and only after 6pm if needed; works for both kids.", "reference", "personal", False,
     [("silicone ring", "tool"), ("cold flannel", "tool"), ("Calpol", "tool"), ("6pm", "date")],
     [],
     "what three-step comfort sequence do I use when the babies are teething",
     "teething ladder silicone ring cold cloth paracetamol evening cap both kids"),
    # --- 48 ---
    ("Chose the SIMS parent portal over the text message service on 2026-01-20 for Maya's school; more detail and attendance shows same day.", "decision", "personal", False,
     [("SIMS parent portal", "tool"), ("text message service", "tool"), ("2026-01-20", "date"), ("Maya", "person")],
     [("SIMS parent portal", "text message service", "PREFERS")],
     "which school communication channel won for my daughter's updates and why",
     "school parent portal swap SMS detail attendance same day date"),
    # --- 49 ---
    ("Leo's fear of the bath drain kicked in on 2025-12-05 after a loud gurgle; we covered it with a silicone stopper and introduced rubber ducks.", "problem", "personal", False,
     [("Leo", "person"), ("bath drain", "tool"), ("2025-12-05", "date"), ("silicone stopper", "tool"), ("rubber ducks", "tool")],
     [],
     "what triggered my son's bath-time fear and how did we work around it",
     "bath drain fear loud gurgle cover stopper duck distract toddler"),
    # --- 50 ---
    ("The 2026 summer camp booking for both kids went to Woodland Adventure on 2026-04-10 for the week of 2026-08-03; deposit £120, balance in June.", "milestone", "personal", False,
     [("Woodland Adventure", "organization"), ("2026-04-10", "date"), ("2026-08-03", "date"), ("June", "date")],
     [],
     "when did we lock in the kids' summer camp and what does the payment plan look like",
     "summer camp booking date week deposit balance month payment plan both kids"),
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
    with OUT.open("a", encoding="utf-8") as f:
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
