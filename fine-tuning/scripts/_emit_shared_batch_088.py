"""One-off emitter for shared-base batch-088 — personal domain (holidays / celebrations / traditions / anniversaries slice).

Writes 50 rows to data/v2/shared/batch_088.tmp.jsonl with ids shared-04351..04400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_088.tmp.jsonl"
ID_OFFSET = 4350

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Christmas Eve fondue ritual at Mum's place has held since 1998; Gruyere, Emmental, a splash of kirsch, and the same chipped ceramic pot that survived two house moves.", "reference", "personal", False,
     [("Christmas Eve", "date"), ("fondue", "food"), ("Gruyere", "food"), ("Emmental", "food"), ("kirsch", "food"), ("ceramic pot", "tool")],
     [("fondue", "Christmas Eve", "HAPPENED_ON")],
     "what does the 24 December cheese-melt evening look like at my mother's and how old is it",
     "christmas eve fondue gruyere emmental kirsch pot tradition longevity"),
    # --- 2 ---
    ("Hanukkah latke night moved from Dad's apartment to our flat on 2025-12-16 because the landing smoke alarm at his place finally beat his patience.", "milestone", "personal", False,
     [("Hanukkah", "event"), ("latke", "food"), ("2025-12-16", "date"), ("smoke alarm", "tool"), ("flat", "place"), ("Dad's apartment", "place")],
     [("flat", "Dad's apartment", "REPLACES")],
     "when did the potato-pancake evening shift hosts and what forced the change",
     "hanukkah latke hosting venue switch smoke alarm tolerance date"),
    # --- 3 ---
    ("Prefers the Kraft Stove Top stuffing over the sourdough-sage version at Thanksgiving; every attempt at fancy has lost the family vote since 2019.", "preference", "personal", False,
     [("Kraft Stove Top", "food"), ("sourdough-sage", "food"), ("Thanksgiving", "event"), ("2019", "date")],
     [("Kraft Stove Top", "sourdough-sage", "PREFERS")],
     "which stuffing actually wins the holiday table every year and since when",
     "thanksgiving stuffing box mix beats homemade sourdough family vote"),
    # --- 4 ---
    ("The Diwali diya arrangement at Nani's goes on the mantel in a 3-4-3 row, never scattered; same layout since the 1980s Jaipur house.", "architecture", "personal", False,
     [("Diwali", "event"), ("diya", "tool"), ("Nani", "person"), ("Jaipur", "place"), ("1980s", "date")],
     [("diya", "Diwali", "HAPPENED_ON")],
     "how is the festival-of-lights lamp row laid out at grandmother's and where did it start",
     "diwali diya row mantel layout grandmother jaipur origin decades"),
    # --- 5 ---
    ("The Lunar New Year reunion dinner at Auntie Mei's runs eight courses; the whole fish must face the eldest, and the dumplings are sealed by hand only.", "reference", "personal", False,
     [("Lunar New Year", "event"), ("Auntie Mei", "person"), ("whole fish", "food"), ("dumplings", "food")],
     [],
     "how is the new year banquet structured at auntie's and which rules are fixed",
     "lunar new year eight courses fish orientation elder dumpling hand seal"),
    # --- 6 ---
    ("Chose to host Christmas Day ourselves from 2025 onward instead of driving four hours to Grandad's; the kids sleep better in their own beds and the turkey is always warmer.", "decision", "personal", False,
     [("Christmas Day", "date"), ("2025", "date"), ("Grandad", "person"), ("turkey", "food")],
     [("Christmas Day", "Grandad", "PREFERS")],
     "when did the yuletide hosting location flip and what was the tipping point",
     "christmas day hosting switch home over grandad drive kids sleep turkey"),
    # --- 7 ---
    ("Replaced paper Christmas cards with a shared Paperless Post link in 2024 after the postage rose by 23 percent; forty-two recipients, no printing.", "decision", "personal", False,
     [("Christmas cards", "tool"), ("Paperless Post", "service"), ("2024", "date")],
     [("Paperless Post", "Christmas cards", "REPLACES")],
     "which greeting medium took over from stamped cards and what triggered the swap",
     "holiday card digital swap postage rise recipient count paperless year"),
    # --- 8 ---
    ("The Secret Santa cap at the cousins' group sits at £25 per person, drawn on 2025-11-30 via Elfster; twelve people, no re-draws even if you pull your spouse.", "reference", "personal", False,
     [("Secret Santa", "event"), ("2025-11-30", "date"), ("Elfster", "service"), ("spouse", "person")],
     [],
     "how does the cousin gift-draw work and what are the rules around the spouse clause",
     "secret santa cap draw date tool cousins no redraw spouse rule"),
    # --- 9 ---
    ("The Easter egg hunt at Pinefield Cottage has been Saturday morning, not Sunday, since 2018; church then hunt meant cold eggs and worse light for photos.", "fact", "personal", False,
     [("Easter", "event"), ("Pinefield Cottage", "place"), ("Saturday", "date"), ("Sunday", "date"), ("2018", "date")],
     [("Saturday", "Sunday", "PREFERS")],
     "which day does the egg hunt land on at the cottage and what was the original problem",
     "easter egg hunt saturday over sunday cottage church cold photo light"),
    # --- 10. noise ---
    ("The kettle in the hallway is whistling again, I should probably go get that.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Our tenth wedding anniversary on 2026-06-14 is booked at the same Cornish inn where we honeymooned; Room 3, sea window, the one the booking clerk remembers.", "milestone", "personal", False,
     [("wedding anniversary", "event"), ("2026-06-14", "date"), ("Cornish inn", "place"), ("Room 3", "place")],
     [("wedding anniversary", "Cornish inn", "LOCATED_IN")],
     "when is the decade mark and where will we mark it",
     "tenth anniversary cornwall inn honeymoon return specific room booking"),
    # --- 12 ---
    ("The family multi-faith compromise: Hanukkah candles on the sill, Christmas tree in the lounge, no fight over which display faces the street.", "decision", "personal", False,
     [("Hanukkah", "event"), ("Christmas tree", "tool"), ("sill", "place"), ("lounge", "place")],
     [],
     "how did we resolve the dual-observance decoration question at home",
     "multi faith household compromise menorah tree placement window street"),
    # --- 13 ---
    ("Prefers hosting Thanksgiving over visiting my sister's in New Jersey; her oven is too small for a 16 lb bird and the flight back is always the Sunday crush.", "preference", "personal", False,
     [("Thanksgiving", "event"), ("New Jersey", "place"), ("16 lb bird", "food"), ("Sunday", "date")],
     [("Thanksgiving", "New Jersey", "PREFERS")],
     "which thanksgiving arrangement wins and what is the real pain point",
     "thanksgiving hosting over visiting sister oven size flight sunday"),
    # --- 14 ---
    ("Henry's seventh birthday party on 2026-05-09 is at Jump Street trampoline park; fourteen kids, two hours, pizza slot booked for 13:30.", "reference", "personal", False,
     [("Henry", "person"), ("2026-05-09", "date"), ("Jump Street", "place"), ("pizza", "food")],
     [("Henry", "Jump Street", "VISITED")],
     "where is the seven-year-old's party landing and what are the logistics",
     "kid birthday trampoline park headcount duration pizza timing date"),
    # --- 15 ---
    ("Switched the New Year's Eve pattern from pub crowd to home dinner with four friends in 2024; the countdown lands better when no one is shouting over a DJ.", "decision", "personal", False,
     [("New Year's Eve", "event"), ("pub", "place"), ("home dinner", "event"), ("2024", "date")],
     [("home dinner", "pub", "REPLACES")],
     "how did the 31 December pattern change and why the quiet version won",
     "new years eve home dinner over pub countdown noise small group year"),
    # --- 16 ---
    ("Nani's Karva Chauth fast breaks after moonrise with water from a silver lota; she will not use steel no matter how many times I offer the thermos.", "fact", "personal", False,
     [("Karva Chauth", "event"), ("Nani", "person"), ("silver lota", "tool"), ("steel", "concept"), ("thermos", "tool")],
     [("silver lota", "steel", "PREFERS")],
     "how does grandmother break her married-woman fast and what is off limits",
     "karva chauth moonrise silver vessel refuse steel thermos grandmother"),
    # --- 17 ---
    ("The holiday Advent calendar for the kids rotates: chocolate 2024, felt pockets with notes 2025, Lego minis for 2026; Lego won the straw poll by six votes.", "milestone", "personal", False,
     [("Advent calendar", "tool"), ("chocolate", "food"), ("felt pockets", "tool"), ("Lego minis", "tool"), ("2026", "date")],
     [("Lego minis", "felt pockets", "REPLACES")],
     "which advent format landed for the kids this year and how was it picked",
     "advent calendar rotation lego over felt pocket straw poll vote year"),
    # --- 18 ---
    ("Hosted our 30th-birthday-together dinner on 2026-03-22 at Rosa's in Soho; nine friends, the private room downstairs, the set menu with the scallops on.", "milestone", "personal", False,
     [("2026-03-22", "date"), ("Rosa's", "place"), ("Soho", "place"), ("scallops", "food")],
     [("Rosa's", "Soho", "LOCATED_IN")],
     "when did we mark the joint milestone birthday and where exactly",
     "thirtieth birthday joint dinner restaurant soho private room scallops"),
    # --- 19 ---
    ("The Thanksgiving menu evolved in 2023 to swap canned cranberry for a pomegranate-orange relish; only Uncle Ron complained and he eats the relish now.", "fact", "personal", False,
     [("Thanksgiving", "event"), ("2023", "date"), ("canned cranberry", "food"), ("pomegranate-orange relish", "food"), ("Uncle Ron", "person")],
     [("pomegranate-orange relish", "canned cranberry", "REPLACES")],
     "when did the cranberry side change and who held out against it",
     "thanksgiving cranberry swap pomegranate relish uncle holdout year"),
    # --- 20 ---
    ("The Passover Seder plate at Sarah's always has a roasted beet for the shank bone stand-in; she went vegetarian in 2016 and never looked back.", "fact", "personal", False,
     [("Passover", "event"), ("Seder", "event"), ("Sarah", "person"), ("roasted beet", "food"), ("shank bone", "food"), ("2016", "date")],
     [("roasted beet", "shank bone", "REPLACES")],
     "what unusual item sits on the seder plate at my friend's and why",
     "passover seder beet substitute shank bone vegetarian switch year"),
    # --- 21 ---
    ("The anniversary gift tradition follows the traditional British list, not the modern American one; wood for the fifth, tin for the tenth, no kitchen appliances disguised as romance.", "preference", "personal", False,
     [("traditional British list", "concept"), ("modern American one", "concept"), ("wood", "concept"), ("tin", "concept")],
     [("traditional British list", "modern American one", "PREFERS")],
     "which anniversary-material scheme do we use and what is ruled out",
     "anniversary gift traditional british list wood tin reject modern appliance"),
    # --- 22 ---
    ("The Lunar New Year red envelope amounts are 88 for children under 12, 188 for teens, 288 for unmarried adults; Auntie Mei wrote the rule on a Post-it in 2012.", "reference", "personal", False,
     [("Lunar New Year", "event"), ("red envelope", "tool"), ("Auntie Mei", "person"), ("Post-it", "tool"), ("2012", "date")],
     [],
     "how are the new-year cash envelopes sized by recipient and who codified it",
     "red envelope amount tiers children teens unmarried rule origin post it"),
    # --- 23 ---
    ("The decoration rule at our flat: tree up on the first Sunday of Advent, down by Twelfth Night, no flashing lights, no inflatables on the balcony ever.", "reference", "personal", False,
     [("Advent", "event"), ("Twelfth Night", "date"), ("flashing lights", "tool"), ("inflatables", "tool"), ("balcony", "place")],
     [],
     "what are the christmas-decoration ground rules at home and when do things go up or down",
     "yule adornment policy timing uptake removal rooftop ban glow units"),
    # --- 24 ---
    ("The milestone reunion for the 2006 uni cohort landed on 2026-07-11 at The Red Lion in Durham; 28 of 54 replied yes, the old pub quiz team is back together.", "milestone", "personal", False,
     [("2006 uni cohort", "event"), ("2026-07-11", "date"), ("The Red Lion", "place"), ("Durham", "place"), ("pub quiz team", "organization")],
     [("The Red Lion", "Durham", "LOCATED_IN")],
     "when does the university twenty-year catch-up happen and where",
     "uni cohort twenty year reunion pub durham rsvp count quiz team date"),
    # --- 25 ---
    ("Chose the Easter Monday walk over the Good Friday fish supper tradition with in-laws; walking with coffee beats sitting through a three-hour meal in silence.", "decision", "personal", False,
     [("Easter Monday", "date"), ("Good Friday", "date"), ("fish supper", "event"), ("in-laws", "person"), ("coffee", "food")],
     [("Easter Monday", "Good Friday", "PREFERS")],
     "which part of the easter weekend wins with in-laws and why",
     "easter monday walk over good friday fish supper silence in laws"),
    # --- 26 ---
    ("The Raksha Bandhan package to Kolkata must post by 2026-08-14 at the latest; last year it went on the 16th and arrived two days after the ritual.", "problem", "personal", False,
     [("Raksha Bandhan", "event"), ("Kolkata", "place"), ("2026-08-14", "date")],
     [],
     "when must the brother-sister ritual parcel go in the post and what went wrong last time",
     "raksha bandhan parcel post deadline kolkata late delivery prior year"),
    # --- 27 ---
    ("The father's 60th birthday party on 2026-10-03 is booked at Wheatley Hall; 48 guests, jazz trio from 19:30, no speeches requested.", "architecture", "personal", False,
     [("60th birthday", "event"), ("2026-10-03", "date"), ("Wheatley Hall", "place"), ("jazz trio", "organization")],
     [("60th birthday", "Wheatley Hall", "LOCATED_IN")],
     "how is dad's sixtieth laid out and what is the entertainment plan",
     "sixtieth birthday venue guest count jazz trio start time no speeches"),
    # --- 28 ---
    ("The holiday card photo is taken in early November on the back step; the golden hour window is 16:10 to 16:35 and the dog sits still for about 90 seconds total.", "architecture", "personal", False,
     [("holiday card", "tool"), ("November", "date"), ("back step", "place"), ("dog", "concept")],
     [],
     "how is the annual card photo staged and what is the window i have with the dog",
     "holiday card photo back step golden hour november dog patience window"),
    # --- 29 ---
    ("The Christmas stocking fillers cap is £30 a head since 2022; it used to be £50 and the children stopped unwrapping past the first five things anyway.", "decision", "personal", False,
     [("Christmas stocking", "tool"), ("2022", "date"), ("children", "person")],
     [],
     "when did the stocking budget drop and what was the evidence for it",
     "stocking budget cut children attention unwrap past five items year"),
    # --- 30 ---
    ("Switched from the Costco pre-cooked turkey to a Copas farm bronze on 2025-12-25; more work, better skin, worth the extra ninety quid.", "decision", "personal", False,
     [("Costco", "organization"), ("pre-cooked turkey", "food"), ("Copas", "organization"), ("bronze", "food"), ("2025-12-25", "date")],
     [("Copas", "Costco", "REPLACES")],
     "which christmas bird upgrade happened and was the price worth it",
     "turkey costco swap copas bronze farm work skin price year"),
    # --- 31 ---
    ("The named family tradition Pancake Sunday predates my marriage by a decade; Sundays once a month, Linda in charge of batter, no substitutions on the maple syrup.", "reference", "personal", False,
     [("Pancake Sunday", "event"), ("Linda", "person"), ("maple syrup", "food")],
     [],
     "what is the monthly breakfast ritual and who has standing authority over it",
     "pancake sunday monthly batter authority no substitute maple rule"),
    # --- 32 ---
    ("Prefers the low-key fortieth over the surprise-party idea Anna floated; no venue I'd rather be than our kitchen with six close friends and one lasagna.", "preference", "personal", False,
     [("fortieth", "event"), ("surprise-party idea", "event"), ("Anna", "person"), ("kitchen", "place"), ("lasagna", "food")],
     [("fortieth", "surprise-party idea", "PREFERS")],
     "which flavour of fortieth wins the argument and what does it actually look like",
     "fortieth low key over surprise kitchen close friends lasagna choice"),
    # --- 33 ---
    ("The Hanukkah gelt system: chocolate coins on night one, a real gift on night eight, nothing for nights two through seven; keeps the drama predictable.", "architecture", "personal", False,
     [("Hanukkah", "event"), ("gelt", "food"), ("chocolate coins", "food"), ("real gift", "concept")],
     [],
     "how does the eight-night festival gift pattern work at home and why structured that way",
     "hanukkah gelt gift schedule night one and eight only predictable drama"),
    # --- 34. noise ---
    ("Remind me to pick up another bag of rice for the week before payday, it's running low.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Bonfire Night gathering at the Harpers' drew 22 this year; baked potatoes from the chiminea, sparklers in a sand bucket, the dog shut inside for the fireworks.", "fact", "personal", False,
     [("Bonfire Night", "event"), ("the Harpers", "person"), ("baked potatoes", "food"), ("chiminea", "tool"), ("sparklers", "tool")],
     [],
     "how did the fifth of november gathering go and what was the headcount",
     "bonfire night gathering count potatoes chiminea sparklers dog fireworks"),
    # --- 36 ---
    ("Chose to skip Valentine's Day dinner out from 2024 onward; book lunch on the 13th or the 15th and avoid the £90 prix fixe that tastes like effort minus love.", "decision", "personal", False,
     [("Valentine's Day", "event"), ("2024", "date"), ("prix fixe", "food")],
     [],
     "how did the 14 february dining pattern shift and what drove the choice",
     "valentine day dinner skip alternate date avoid prix fixe price year"),
    # --- 37 ---
    ("The Eid al-Fitr morning at Aunt Rukhsana's starts at 06:30 with sheer khurma; the pot is dented, the recipe is memorised, and no one is allowed to improve it.", "reference", "personal", False,
     [("Eid al-Fitr", "event"), ("Aunt Rukhsana", "person"), ("sheer khurma", "food"), ("pot", "tool")],
     [],
     "how does the post-ramadan morning unfold at auntie's and what cannot be changed",
     "eid al fitr morning sheer khurma recipe locked pot early start"),
    # --- 38 ---
    ("The Christmas pudding is made on Stir-up Sunday, last Sunday before Advent; 2026-11-22 on the calendar, fed brandy weekly until the 25th.", "reference", "personal", False,
     [("Christmas pudding", "food"), ("Stir-up Sunday", "date"), ("2026-11-22", "date"), ("Advent", "event"), ("brandy", "food")],
     [("Christmas pudding", "Stir-up Sunday", "HAPPENED_ON")],
     "when is the pudding made and how is it stored before the day",
     "christmas pudding stir up sunday brandy feed weekly schedule advent"),
    # --- 39 ---
    ("Prefers anniversary trips in even-numbered years to anniversary gifts in odd-numbered ones; the suitcase memory outlives whatever the wrapping held.", "preference", "personal", False,
     [("anniversary trips", "activity"), ("anniversary gifts", "concept"), ("even-numbered years", "concept"), ("odd-numbered ones", "concept"), ("suitcase memory", "concept")],
     [("anniversary trips", "anniversary gifts", "PREFERS")],
     "how is the gift-versus-travel pattern split across years and what is the logic",
     "anniversary trip even year gift odd memory over object rationale"),
    # --- 40 ---
    ("The Mother's Day brunch at The Old Rectory is booked on 2026-03-15 at 11:30 for five; same table under the north window that Mum loved last year.", "milestone", "personal", False,
     [("Mother's Day", "event"), ("The Old Rectory", "place"), ("2026-03-15", "date"), ("Mum", "person"), ("north window", "place")],
     [("The Old Rectory", "Mother's Day", "HAPPENED_ON")],
     "when is the mothering-sunday meal locked in and what is the seating detail",
     "mothers day brunch rectory booking table window mum preference date"),
    # --- 41 ---
    ("The Nowruz haft-sin at the Farzanis runs seven items plus the goldfish; Ayda refuses the live fish tradition now and uses a ceramic one on a mirror.", "decision", "personal", False,
     [("Nowruz", "event"), ("haft-sin", "concept"), ("the Farzanis", "person"), ("goldfish", "concept"), ("Ayda", "person"), ("ceramic", "concept")],
     [("ceramic", "goldfish", "REPLACES")],
     "how is the persian new year table set at the farzanis and what changed",
     "nowruz haft sin seven items goldfish ceramic substitute ethics change"),
    # --- 42 ---
    ("The gift-exchange system at the in-laws is adults-draw-one since 2023; sixteen people used to buy sixteen presents and the pile alone took an hour to open.", "architecture", "personal", False,
     [("in-laws", "person"), ("2023", "date"), ("gift-exchange", "event")],
     [],
     "how did the extended-family present system shift and what was it replacing",
     "gift exchange adults draw one reduce gifts in law family year change"),
    # --- 43 ---
    ("Prefers Grandpa's recipe for the Thanksgiving gravy to the turkey-drippings-only version; cornstarch slurry, a splash of Madeira, simmered past what most would call done.", "preference", "personal", False,
     [("Grandpa", "person"), ("Thanksgiving", "event"), ("gravy", "food"), ("cornstarch", "food"), ("Madeira", "food")],
     [("Grandpa", "Thanksgiving", "RELATED_TO")],
     "which gravy method wins at the november table and what makes it distinct",
     "thanksgiving gravy grandpa recipe cornstarch madeira long simmer beat"),
    # --- 44 ---
    ("The Christmas morning running order at ours: coffee then stockings, pause for breakfast, presents from 10:30, no one opens anything before the cinnamon rolls are out.", "architecture", "personal", False,
     [("Christmas morning", "date"), ("stockings", "tool"), ("breakfast", "event"), ("cinnamon rolls", "food")],
     [],
     "how does the 25 december morning unfold at home and what is the hard gate",
     "christmas morning sequence coffee stocking breakfast presents cinnamon rule"),
    # --- 45 ---
    ("The fiftieth anniversary party for my parents on 2026-09-05 needs the Royal Oak function room by 2026-04-30 or the slot goes; deposit already sent, £500.", "problem", "personal", False,
     [("fiftieth anniversary", "event"), ("2026-09-05", "date"), ("Royal Oak", "place"), ("function room", "place"), ("2026-04-30", "date")],
     [("fiftieth anniversary", "Royal Oak", "LOCATED_IN")],
     "when is the parents' golden-anniversary venue due for lockdown and what is on the clock",
     "fiftieth anniversary royal oak function room deposit deadline date"),
    # --- 46 ---
    ("The birthday cake tradition at home: sponge from scratch for kids, Colin the Caterpillar for adults over forty; decided in 2022 and nobody has challenged it since.", "preference", "personal", False,
     [("sponge", "food"), ("Colin the Caterpillar", "food"), ("2022", "date")],
     [("Colin the Caterpillar", "sponge", "PREFERS")],
     "how did the birthday cake split by age settle and when",
     "birthday cake split kids sponge adults caterpillar rule set year"),
    # --- 47 ---
    ("The holiday card list dropped from 64 to 41 in 2025; only people who replied to the 2024 card got one this year, a rule I should have made sooner.", "decision", "personal", False,
     [("holiday card list", "tool"), ("2025", "date"), ("2024", "date")],
     [],
     "how did the greeting-card list get trimmed and what was the criterion",
     "holiday card list size drop reciprocation rule prior year criterion"),
    # --- 48 ---
    ("The Kwanzaa table at the Johnsons' starts on 2026-12-26 with the mkeka mat laid east-west, kinara centred, the unity cup to the left of the bowl.", "reference", "personal", False,
     [("Kwanzaa", "event"), ("the Johnsons", "person"), ("2026-12-26", "date"), ("mkeka mat", "tool"), ("kinara", "tool"), ("unity cup", "tool")],
     [],
     "how is the kwanzaa table arranged at the neighbours and on what day does it begin",
     "kwanzaa table mkeka kinara unity cup layout east west start date"),
    # --- 49 ---
    ("The Lantern Festival walk on 2026-03-03 starts at Victoria Park, loops the canal, ends at the noodle shop where we always order the same three bowls.", "architecture", "personal", False,
     [("Lantern Festival", "event"), ("2026-03-03", "date"), ("Victoria Park", "place"), ("canal", "place"), ("noodle shop", "place")],
     [("Lantern Festival", "Victoria Park", "LOCATED_IN")],
     "how is the fifteenth-day lantern walk routed and where does it finish up",
     "lantern festival walk park canal loop noodle shop three bowls date"),
    # --- 50 ---
    ("The Christmas tree upgrade to a 7 ft Nordmann fir on 2025-12-01 replaced the creaking plastic one from 2011; the needles stay on, the tilt is gone, the cat is confused.", "decision", "personal", False,
     [("Nordmann fir", "tool"), ("2025-12-01", "date"), ("plastic one", "tool"), ("2011", "date"), ("cat", "concept")],
     [("Nordmann fir", "plastic one", "REPLACES")],
     "when did the real tree take over from the artificial and what changed noticeably",
     "christmas tree nordmann real over plastic needle hold tilt fix year"),
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
