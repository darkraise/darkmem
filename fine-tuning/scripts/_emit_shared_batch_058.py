"""One-off emitter for shared-base batch-058 — personal domain (pets and animal companions slice).

Writes 50 rows to data/v2/shared/batch_058.tmp.jsonl with ids shared-02851..02900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_058.tmp.jsonl"
ID_OFFSET = 2850

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Adopted Mochi, a tortoiseshell kitten, from Cats Protection Bridgwater on 2026-02-14 after a four-week foster trial that mostly tested the curtains.", "milestone", "personal", False,
     [("Mochi", "person"), ("Cats Protection Bridgwater", "organization"), ("2026-02-14", "date"), ("foster trial", "event"), ("curtains", "concept")],
     [("Mochi", "Cats Protection Bridgwater", "RELATED_TO")],
     "when did the new kitten join the household and how was she vetted",
     "kitten adoption rescue date foster trial period curtain test"),
    # --- 2 ---
    ("The vet at Cedar Lane Veterinary booked Hugo's annual booster for 2026-05-09; lepto and kennel cough together this round, no rabies needed for the UK stay.", "fact", "personal", False,
     [("Cedar Lane Veterinary", "organization"), ("Hugo", "person"), ("2026-05-09", "date"), ("lepto", "concept"), ("kennel cough", "concept"), ("rabies", "concept")],
     [("Hugo", "Cedar Lane Veterinary", "RELATED_TO")],
     "when is the dog due his next shots and which jabs are on the slate",
     "vet booster appointment dog vaccine schedule lepto bordetella rabies skip"),
    # --- 3 ---
    ("Switched Mochi from Royal Canin Kitten to Orijen Cat & Kitten on 2026-03-22 after the loose-stool patch cleared on a vet-suggested chicken-only week.", "decision", "personal", False,
     [("Mochi", "person"), ("Royal Canin Kitten", "service"), ("Orijen Cat & Kitten", "service"), ("2026-03-22", "date"), ("chicken-only week", "method")],
     [("Orijen Cat & Kitten", "Royal Canin Kitten", "REPLACES")],
     "which kitten food took over from the old brand and why the transition",
     "kitten kibble swap brand change loose stool fix elimination diet date"),
    # --- 4 ---
    ("Hugo gets the long-line lead at Westover Common and the short flexi at Heath Path; the common has a deer corridor I do not trust him near.", "preference", "personal", False,
     [("Hugo", "person"), ("long-line lead", "tool"), ("Westover Common", "place"), ("flexi", "tool"), ("Heath Path", "place"), ("deer corridor", "place")],
     [("long-line lead", "flexi", "PREFERS")],
     "which lead matches which walking spot for the dog and what is the reason",
     "dog lead choice common path long line versus flexi deer wildlife caution"),
    # --- 5 ---
    ("Replaced Hugo's nylon harness with the Ruffwear Front Range on 2026-01-18 after the chest strap chafed a bald patch under his left foreleg.", "decision", "personal", False,
     [("Hugo", "person"), ("nylon harness", "tool"), ("Ruffwear Front Range", "tool"), ("2026-01-18", "date"), ("foreleg", "concept")],
     [("Ruffwear Front Range", "nylon harness", "REPLACES")],
     "which dog harness took over from the old one and what triggered the change",
     "harness swap nylon to ruffwear chafe bald patch under leg date"),
    # --- 6 ---
    ("The bearded dragon Tofu basks at 38 C on the hot side and 25 C on the cool; UVB tube replaced every six months on the calendar reminder.", "architecture", "personal", False,
     [("Tofu", "person"), ("bearded dragon", "concept"), ("UVB tube", "tool"), ("six months", "date")],
     [("Tofu", "bearded dragon", "IS_A")],
     "how is the lizard's vivarium temperature and lighting regime set",
     "bearded dragon basking gradient UVB replacement cadence cool side warm"),
    # --- 7 ---
    ("The boarding kennel Greenfields refused Hugo's intact-male booking once they found out, so we moved the August holiday cover to Pawhaven instead.", "problem", "personal", False,
     [("Greenfields", "organization"), ("Hugo", "person"), ("August", "date"), ("Pawhaven", "organization")],
     [("Pawhaven", "Greenfields", "REPLACES")],
     "which boarding place fell through for the dog and what replaced it",
     "kennel rejection intact male alternative boarding holiday cover venue"),
    # --- 8 ---
    ("Mochi's litter setup is two trays, both the high-sided IKEA Vargon, with World's Best clumping corn; one in the utility, one on the landing.", "reference", "personal", False,
     [("Mochi", "person"), ("IKEA Vargon", "service"), ("World's Best", "service"), ("utility", "place"), ("landing", "place")],
     [],
     "how is the cat's toileting set up across the house",
     "litter tray count brand layout utility landing high sided corn clump"),
    # --- 9 ---
    ("The koi pond pH at 8.1 on 2026-04-03 was higher than the 7.4 target; partial water change planned and a peat bag added to the filter sump.", "problem", "personal", False,
     [("koi pond", "infrastructure"), ("pH", "concept"), ("2026-04-03", "date"), ("peat bag", "tool"), ("filter sump", "infrastructure")],
     [],
     "what was the koi water reading off-spec and what is the planned fix",
     "koi pond pH high reading remedy water change peat filter date"),
    # --- 10. noise ---
    ("Hold on, the cat's at the door again.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Switched Hugo's training from clicker to verbal-marker on 2026-02-09; the clicker kept getting lost in pockets and the marker travels with my voice.", "decision", "personal", False,
     [("Hugo", "person"), ("clicker", "tool"), ("verbal-marker", "method"), ("2026-02-09", "date")],
     [("verbal-marker", "clicker", "REPLACES")],
     "which dog-training cue replaced the mechanical one and why the change",
     "training swap clicker to verbal marker pocket loss portability date"),
    # --- 12 ---
    ("The grooming appointment for Hugo at Wagtails on 2026-03-15 is a hand-strip not a clip; the wire coat needs the texture kept for weatherproofing.", "fact", "personal", False,
     [("Hugo", "person"), ("Wagtails", "organization"), ("2026-03-15", "date"), ("hand-strip", "method"), ("clip", "method")],
     [("hand-strip", "clip", "PREFERS")],
     "when is the dog booked for grooming and which method is being used",
     "grooming booking salon date hand strip not clip wire coat reason"),
    # --- 13 ---
    ("Improved the recall game with Hugo by cutting the reward distance from ten metres to three; nine in ten returns now versus four out of ten before.", "milestone", "personal", False,
     [("Hugo", "person"), ("recall", "method"), ("ten metres", "concept"), ("three", "concept")],
     [("three", "ten metres", "IMPROVES_ON")],
     "what training tweak lifted the dog's recall reliability and by how much",
     "recall improvement reward distance cut return rate before after metric"),
    # --- 14 ---
    ("The breed club for Welsh Terriers, the WTA, runs the Spring Open at Stoneleigh on 2026-05-23; entries close 2026-04-30 and Hugo is signed up.", "reference", "personal", False,
     [("WTA", "organization"), ("Welsh Terriers", "concept"), ("Stoneleigh", "place"), ("2026-05-23", "date"), ("2026-04-30", "date"), ("Hugo", "person")],
     [("WTA", "Welsh Terriers", "RELATED_TO")],
     "which breed-club show has the dog entered and what are the deadlines",
     "welsh terrier club open show date venue entry cutoff dog signup"),
    # --- 15 ---
    ("Mochi prefers the cardboard scratcher under the bay window to the carpeted post in the lounge; the post has been ignored since week two.", "preference", "personal", False,
     [("Mochi", "person"), ("cardboard scratcher", "tool"), ("bay window", "place"), ("carpeted post", "tool"), ("lounge", "place")],
     [("cardboard scratcher", "carpeted post", "PREFERS")],
     "which scratching surface wins out for the cat and where is it",
     "cat scratcher choice cardboard over carpet location bay window"),
    # --- 16 ---
    ("The end-of-life appointment for Biscuit on 2026-01-07 was at home with Dr Patel from Cedar Lane; sedation first, then the rest, on her bed in the kitchen.", "milestone", "personal", False,
     [("Biscuit", "person"), ("2026-01-07", "date"), ("Dr Patel", "person"), ("Cedar Lane", "organization"), ("kitchen", "place")],
     [],
     "when did the home euthanasia happen and how was it set up",
     "end of life cat home visit vet date sedation place kitchen bed"),
    # --- 17 ---
    ("Switched the parakeet seed mix from Trill to Versele-Laga Prestige on 2026-03-01; Trill had too much sunflower and Pip's keel was getting padded.", "decision", "personal", False,
     [("Trill", "service"), ("Versele-Laga Prestige", "service"), ("2026-03-01", "date"), ("Pip", "person"), ("keel", "concept")],
     [("Versele-Laga Prestige", "Trill", "REPLACES")],
     "which budgie mix took over from the old one and what was the trigger",
     "parakeet seed brand swap sunflower fat keel score date change"),
    # --- 18 ---
    ("Hugo's microchip number 985112004128756 is registered with Petlog; updated the address there on 2026-04-02 the day after the move.", "fact", "personal", False,
     [("Hugo", "person"), ("985112004128756", "concept"), ("Petlog", "service"), ("2026-04-02", "date")],
     [("Hugo", "Petlog", "RELATED_TO")],
     "where is the dog's chip registered and when did the address get refreshed",
     "microchip registry update post move date dog identifier provider"),
    # --- 19 ---
    ("Replaced the koi pond UV clarifier with the Oase Bitron 36C on 2026-02-20; the old TMC ran for nine years and the algae bloom in January was the tell.", "decision", "personal", False,
     [("koi pond", "infrastructure"), ("UV clarifier", "tool"), ("Oase Bitron 36C", "tool"), ("2026-02-20", "date"), ("TMC", "service"), ("algae bloom", "event")],
     [("Oase Bitron 36C", "TMC", "REPLACES")],
     "which pond UV unit took over from the old one and what was the trigger",
     "UV clarifier swap pond brand old age algae bloom tell date"),
    # --- 20 ---
    ("The cat-flap on the back door is set to Sureflap chip-only with Mochi's chip whitelisted; the neighbour's tabby Otis used to walk in and eat her food.", "architecture", "personal", False,
     [("cat-flap", "infrastructure"), ("Sureflap", "service"), ("Mochi", "person"), ("Otis", "person")],
     [("cat-flap", "Sureflap", "USES")],
     "how is the cat door configured and which intruder prompted the lockdown",
     "cat flap chip whitelist neighbour cat raid food prevention setup"),
    # --- 21 ---
    ("The daily ritual at 06:40 is the same: kettle on, Hugo out the back door, Mochi's wet sachet down, then ten minutes of training before breakfast.", "fact", "personal", False,
     [("06:40", "date"), ("Hugo", "person"), ("Mochi", "person"), ("training", "activity")],
     [],
     "what is the morning routine with the pets and in what order",
     "morning rhythm dog out cat fed training block pre breakfast time"),
    # --- 22 ---
    ("Pip the budgie sleeps under a cotton cover from 21:00 to 07:00; the cover halved the early-morning chatter that was waking the toddler next door.", "decision", "personal", False,
     [("Pip", "person"), ("budgie", "concept"), ("cotton cover", "tool"), ("21:00", "date"), ("07:00", "date"), ("toddler", "person")],
     [("Pip", "budgie", "IS_A")],
     "what change to the bird's night setup fixed the noise complaint",
     "budgie cover sleep window noise reduction neighbour toddler quiet"),
    # --- 23 ---
    ("Tofu the bearded dragon eats live dubia roaches three times a week; greens are kale and rocket daily, never spinach due to oxalate binding.", "reference", "personal", False,
     [("Tofu", "person"), ("dubia roaches", "food"), ("kale", "food"), ("rocket", "food"), ("spinach", "food"), ("oxalate", "concept")],
     [],
     "what does the bearded dragon eat and which greens are off the menu",
     "lizard feeding live insect cadence daily greens spinach exclusion reason"),
    # --- 24 ---
    ("Prefers the slow-feeder bowl over the standard for Hugo; the standard bowl saw a meal vanish in 90 seconds and the slow one stretches it past five minutes.", "preference", "personal", False,
     [("slow-feeder bowl", "tool"), ("Hugo", "person"), ("standard", "tool")],
     [("slow-feeder bowl", "standard", "PREFERS")],
     "which dog bowl wins out and how does the meal length compare",
     "slow feeder over standard bowl meal pace seconds versus minutes"),
    # --- 25 ---
    ("The wildlife camera on the back fence caught a hedgehog at 23:14 on 2026-04-08; left the gap under the shed open and added a shallow water dish.", "milestone", "personal", False,
     [("wildlife camera", "tool"), ("hedgehog", "concept"), ("23:14", "date"), ("2026-04-08", "date"), ("shed", "place"), ("water dish", "tool")],
     [],
     "when did the trail cam first catch a hedgehog and what changed in the garden",
     "wildlife camera hedgehog sighting date time garden access water dish"),
    # --- 26 ---
    ("Hugo's pet insurance moved from Petplan to Bought By Many on 2026-01-02; same lifetime cover, £18 less per month, and the app actually loads.", "decision", "personal", False,
     [("Hugo", "person"), ("Petplan", "organization"), ("Bought By Many", "organization"), ("2026-01-02", "date")],
     [("Bought By Many", "Petplan", "REPLACES")],
     "which pet insurer took over from the old one and what was the swing",
     "insurance switch dog provider lifetime cover monthly saving app date"),
    # --- 27 ---
    ("The dog walker Sasha takes Hugo Tuesday and Thursday at 11:30 for an hour; £15 per walk, off-lead at the riverbank loop she knows well.", "reference", "personal", False,
     [("Sasha", "person"), ("Hugo", "person"), ("Tuesday", "date"), ("Thursday", "date"), ("riverbank loop", "place")],
     [("Sasha", "riverbank loop", "VISITED")],
     "who walks the dog and on what schedule and where",
     "dog walker name days time price route off lead riverbank loop"),
    # --- 28 ---
    ("Mochi's flea treatment is Bravecto Plus monthly, alternating with the Stronghold the prior cat had; the Bravecto cleared the round-worm flare in March.", "fact", "personal", False,
     [("Mochi", "person"), ("Bravecto Plus", "service"), ("Stronghold", "service"), ("round-worm", "concept"), ("March", "date")],
     [("Bravecto Plus", "Stronghold", "REPLACES")],
     "which parasite treatment is on the cat and what did it sort out",
     "flea wormer brand swap monthly cycle round worm flare month outcome"),
    # --- 29 ---
    ("The reactive-dog class at Pawsitive Steps on 2026-03-12 covered threshold distance and look-at-that drills; Hugo got from twelve metres to seven by week four.", "milestone", "personal", False,
     [("Pawsitive Steps", "organization"), ("2026-03-12", "date"), ("look-at-that", "method"), ("Hugo", "person"), ("twelve metres", "concept"), ("seven", "concept")],
     [("seven", "twelve metres", "IMPROVES_ON")],
     "what did the dog reactivity course teach and what was the progress metric",
     "reactive class threshold distance LAT drill metres improvement weeks"),
    # --- 30 ---
    ("Prefers the Adaptil collar over the diffuser for Hugo on fireworks weekends; the collar travels with the dog and the diffuser only covers the lounge.", "preference", "personal", False,
     [("Adaptil", "service"), ("collar", "tool"), ("diffuser", "tool"), ("Hugo", "person"), ("fireworks", "event"), ("lounge", "place")],
     [("collar", "diffuser", "PREFERS")],
     "which calming format wins for the dog on bonfire night and why",
     "adaptil collar over diffuser fireworks portability whole house coverage"),
    # --- 31 ---
    ("The koi feeding rate drops to once every two days when the pond temp falls below 10 C; metabolism shuts down and uneaten pellets foul the bottom.", "architecture", "personal", False,
     [("koi", "concept"), ("two days", "date"), ("pond", "infrastructure"), ("10 C", "concept"), ("pellets", "food")],
     [("koi", "pond", "LIVES_IN")],
     "how does the fish-feeding cadence change in cold weather and why",
     "koi feeding rate cold temp threshold metabolism uneaten pellet fouling"),
    # --- 32 ---
    ("Tofu's vet at ExoticPet Clinic flagged a slightly retained shed on the left back toe on 2026-03-18; warm soak nightly for a week, no tweezing.", "problem", "personal", False,
     [("Tofu", "person"), ("ExoticPet Clinic", "organization"), ("retained shed", "concept"), ("2026-03-18", "date"), ("warm soak", "method")],
     [("Tofu", "ExoticPet Clinic", "RELATED_TO")],
     "what did the reptile vet spot and what is the home treatment",
     "bearded dragon retained shed toe vet finding soak nightly date no tweeze"),
    # --- 33 ---
    ("The kitten-proofing list for the front room is done: blind cords short-tied, cables in conduit, philodendron rehomed to the bathroom, fish tank lid latched.", "architecture", "personal", False,
     [("front room", "place"), ("blind cords", "concept"), ("conduit", "tool"), ("philodendron", "concept"), ("bathroom", "place"), ("fish tank", "infrastructure")],
     [],
     "what kitten-proofing measures went into the lounge",
     "kitten proof front room cords cables plant move tank lid checklist"),
    # --- 34. noise ---
    ("Sorry, the dog wants out, give me a sec.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Joined the Cornish Rex breed forum on 2026-02-11 to research before the second cat; thread on hereditary patellar luxation pulled me toward an outcross line.", "milestone", "personal", False,
     [("Cornish Rex", "concept"), ("2026-02-11", "date"), ("patellar luxation", "concept"), ("outcross line", "concept")],
     [],
     "when did I join the breed community and what shaped the second-cat plan",
     "cornish rex forum signup research second cat heredity outcross direction"),
    # --- 36 ---
    ("Hugo's recall whistle is the Acme 211.5 on a black lanyard kept by the back door; never moved, never washed in pocket, three short pips means come.", "reference", "personal", False,
     [("Hugo", "person"), ("Acme 211.5", "tool"), ("lanyard", "tool"), ("back door", "place")],
     [("Acme 211.5", "back door", "LOCATED_IN")],
     "what whistle gear does the dog respond to and where does it live",
     "recall whistle model pitch lanyard back door storage cue pattern"),
    # --- 37 ---
    ("Replaced the koi pond pellet brand from Tetra Pond to Saki-Hikari Growth on 2026-04-01; growth tracking on the two-year-olds picked up by 2 mm in three weeks.", "decision", "personal", False,
     [("koi pond", "infrastructure"), ("Tetra Pond", "service"), ("Saki-Hikari Growth", "service"), ("2026-04-01", "date"), ("two-year-olds", "concept")],
     [("Saki-Hikari Growth", "Tetra Pond", "REPLACES")],
     "which koi pellet took over from the old one and what was the gain",
     "koi pellet brand swap growth measure increase weeks date change"),
    # --- 38 ---
    ("The dog-training treat pouch is the PetSafe Treat Pouch Sport on the right hip; left hip carries poo bags and the whistle, never mixed up under pressure.", "preference", "personal", False,
     [("PetSafe Treat Pouch Sport", "tool"), ("right hip", "place"), ("left hip", "place"), ("poo bags", "tool"), ("whistle", "tool")],
     [],
     "how do I split the dog-walk gear between the hips and why",
     "treat pouch right hip bags whistle left muscle memory gear split"),
    # --- 39 ---
    ("The koi pond fits eight adult fish at 1500 litres; rule of thumb is one inch of fish per ten gallons and we sit just under that on the spreadsheet.", "fact", "personal", False,
     [("koi pond", "infrastructure"), ("eight adult fish", "concept"), ("1500 litres", "concept"), ("inch of fish per ten gallons", "method"), ("spreadsheet", "tool")],
     [],
     "how is the koi stocking limit calculated against the pond volume",
     "pond stocking adult count litre volume rule inch per gallon margin"),
    # --- 40 ---
    ("Pip the budgie joined a free-flight session on 2026-03-29 in the conservatory; closed all blinds first, mirrors down, fan unplugged, two clear hours.", "milestone", "personal", False,
     [("Pip", "person"), ("2026-03-29", "date"), ("conservatory", "place"), ("blinds", "tool"), ("mirrors", "tool"), ("fan", "tool")],
     [("Pip", "conservatory", "VISITED")],
     "when did the budgie's first free-flight happen and what safety prep went in",
     "budgie free flight date conservatory blinds mirrors fan prep duration"),
    # --- 41 ---
    ("Improved Mochi's carrier acceptance by leaving the carrier out as a bed for six weeks; she went from 30 seconds to twenty minutes inside before stress vocalising.", "milestone", "personal", False,
     [("Mochi", "person"), ("carrier", "tool"), ("six weeks", "date"), ("twenty minutes", "concept"), ("30 seconds", "concept")],
     [("twenty minutes", "30 seconds", "IMPROVES_ON")],
     "what change extended the cat's tolerance for the travel box",
     "carrier desensitisation bed leave out duration calm window improvement"),
    # --- 42 ---
    ("Chose home boarding with Sasha over kennels for the September trip; Hugo needs a settled house, not a cell, and Sasha already does the weekday walks.", "decision", "personal", False,
     [("home boarding", "service"), ("Sasha", "person"), ("kennels", "service"), ("September", "date"), ("Hugo", "person")],
     [("home boarding", "kennels", "PREFERS")],
     "which holiday-care option won for the dog and what made it the obvious pick",
     "home board over kennel walker familiar dog temperament september cover"),
    # --- 43 ---
    ("The grooming schedule for Hugo is hand-strip every 12 weeks, ear pluck monthly, nail trim fortnightly with a Dremel rather than clippers.", "architecture", "personal", False,
     [("Hugo", "person"), ("hand-strip", "method"), ("12 weeks", "date"), ("ear pluck", "method"), ("nail trim", "activity"), ("Dremel", "tool"), ("clippers", "tool")],
     [("Dremel", "clippers", "PREFERS")],
     "how is the dog's grooming cadence laid out across coat, ears, and nails",
     "grooming schedule hand strip cadence ear plucking nail dremel choice"),
    # --- 44 ---
    ("The pet-sitter agreement with Sasha is one A4 page in the kitchen drawer: keys, vet contact, feeding amounts, the vet's emergency line, and the insurance number.", "reference", "personal", False,
     [("Sasha", "person"), ("kitchen drawer", "place"), ("vet", "person"), ("emergency line", "concept")],
     [("Sasha", "kitchen drawer", "RELATED_TO")],
     "where is the sitter's brief stored and what does it cover",
     "pet sitter agreement drawer location keys vet contact feeding amounts"),
    # --- 45 ---
    ("Mochi got stuck behind the dishwasher on 2026-03-08; pulled the kickboard, blocked the gap with a 50 mm offcut from the workshop, never again.", "problem", "personal", False,
     [("Mochi", "person"), ("dishwasher", "infrastructure"), ("2026-03-08", "date"), ("kickboard", "concept"), ("offcut", "tool"), ("workshop", "place")],
     [],
     "when did the cat get trapped in the kitchen and what was the permanent fix",
     "cat stuck appliance gap kickboard offcut block workshop date repair"),
    # --- 46 ---
    ("The end-of-life paw-print mould of Biscuit was done at Cedar Lane on 2026-01-07 and now sits on the mantel beside her collar.", "milestone", "personal", False,
     [("paw-print mould", "tool"), ("Biscuit", "person"), ("Cedar Lane", "organization"), ("2026-01-07", "date"), ("mantel", "place"), ("collar", "tool")],
     [("paw-print mould", "mantel", "LOCATED_IN")],
     "where is the late cat's keepsake kept and when was it made",
     "paw print mould memorial mantel placement date vet location collar"),
    # --- 47 ---
    ("The household has agreed: no more pets after Mochi and Hugo until 2028 at the earliest; the boarding cost stack and the holiday logistics are already taut.", "decision", "personal", False,
     [("Mochi", "person"), ("Hugo", "person"), ("2028", "date"), ("boarding cost", "concept"), ("holiday logistics", "concept")],
     [],
     "what is the family rule on adding more animals and on what timeline",
     "no new pet rule horizon year boarding cost holiday logistic constraint"),
    # --- 48 ---
    ("Improved Mochi's hairball frequency from weekly to roughly monthly by switching to the Whiskas malt paste twice a week and brushing every other day.", "milestone", "personal", False,
     [("Mochi", "person"), ("hairball", "concept"), ("Whiskas malt paste", "service"), ("brushing", "activity"), ("monthly", "date"), ("weekly", "date")],
     [("monthly", "weekly", "IMPROVES_ON")],
     "what intervention cut down the cat's hairball episodes and by how much",
     "hairball reduction malt paste cadence brushing rhythm frequency change"),
    # --- 49 ---
    ("The local Dogs Trust rehoming evening on 2026-05-02 is just to learn the foster route; not bringing a second dog home until the kitchen extension is done.", "fact", "personal", False,
     [("Dogs Trust", "organization"), ("2026-05-02", "date"), ("foster route", "concept"), ("kitchen extension", "infrastructure")],
     [],
     "what is the plan for the rescue evening and what is the constraint on a new dog",
     "dogs trust evening attend purpose foster learn extension constraint date"),
    # --- 50 ---
    ("The wildlife-friendly garden tweaks for 2026 are a hedgehog highway in the back fence, a stumpery in the shaded corner, and no more slug pellets anywhere.", "decision", "personal", False,
     [("hedgehog highway", "infrastructure"), ("back fence", "place"), ("stumpery", "infrastructure"), ("shaded corner", "place"), ("slug pellets", "tool"), ("2026", "date")],
     [("hedgehog highway", "back fence", "LOCATED_IN")],
     "what wildlife-supporting changes are planned for the garden this year",
     "hedgehog hole fence stumpery shade slug pellet ban year wildlife plan"),
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
