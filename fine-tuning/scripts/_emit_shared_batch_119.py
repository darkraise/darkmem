"""One-off emitter for shared-base batch-119 — personal domain (grief, loss, and life-transition slice).

Writes 50 rows to data/v2/shared/batch_119.tmp.jsonl with ids shared-05901..05950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_119.tmp.jsonl"
ID_OFFSET = 5900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Dad died on 2025-11-14 at St Luke's Hospice; the grief counsellor said to expect the first anniversary to hit harder than the funeral week itself.", "milestone", "personal", False,
     [("Dad", "person"), ("2025-11-14", "date"), ("St Luke's Hospice", "organization"), ("grief counsellor", "person"), ("funeral week", "event")],
     [],
     "when did my father pass and what warning did the bereavement worker give about the timeline",
     "father death date hospice grief counsellor first anniversary warning"),
    # --- 2 ---
    ("Chose a natural-burial plot at Greenhaven Meadow for Mum over the family plot at St Agnes'; she had asked for no headstone and the meadow allows only a wooden marker.", "decision", "personal", False,
     [("Greenhaven Meadow", "place"), ("Mum", "person"), ("family plot", "place"), ("St Agnes'", "organization"), ("wooden marker", "tool")],
     [("Greenhaven Meadow", "family plot", "REPLACES")],
     "which burial site won out for my mother and what drove the swap from the family one",
     "natural burial meadow over family plot wish no headstone wooden marker"),
    # --- 3 ---
    ("The eulogy for Grandad was drafted across three evenings 2025-12-03 to 2025-12-05; settled on the rag-and-bone story over the war-service one because the room would laugh.", "decision", "personal", False,
     [("eulogy", "concept"), ("Grandad", "person"), ("2025-12-03", "date"), ("2025-12-05", "date"), ("rag-and-bone story", "concept"), ("war-service", "concept")],
     [("rag-and-bone story", "war-service", "PREFERS")],
     "when did I write the tribute for my grandfather and which anecdote beat the other",
     "eulogy draft evenings grandfather rag and bone over war service laugh"),
    # --- 4 ---
    ("Prefers writing the obituary for the local paper over the national listing; the Herald's Marta edits with care, the Times obit desk cuts the warmth out.", "preference", "personal", False,
     [("obituary", "concept"), ("Herald", "organization"), ("Marta", "person"), ("Times", "organization")],
     [("Herald", "Times", "PREFERS")],
     "which obituary outlet wins out and why the editing makes the difference",
     "obituary local paper over national editor warmth cut comparison"),
    # --- 5 ---
    ("The post-funeral tea at The Anchor on 2025-11-22 drew 84 people; the cousins' table stayed until 17:30, which was longer than Dad had ever managed at a pub.", "fact", "personal", False,
     [("The Anchor", "place"), ("2025-11-22", "date"), ("cousins", "person"), ("Dad", "person")],
     [("The Anchor", "cousins", "RELATED_TO")],
     "when was the wake held and what was the turnout like",
     "post funeral tea pub date headcount cousins table stayed late"),
    # --- 6 ---
    ("Reading On Grief and Grieving by David Kessler made the five-stage framing stop feeling like homework; the sixth-stage meaning chapter is the one I keep returning to.", "reference", "personal", False,
     [("On Grief and Grieving", "concept"), ("David Kessler", "person"), ("five-stage framing", "method"), ("sixth-stage meaning chapter", "concept")],
     [("sixth-stage meaning chapter", "five-stage framing", "IMPROVES_ON")],
     "which bereavement book reframed the stages for me and which chapter keeps drawing me back",
     "on grief grieving kessler five stage sixth meaning chapter return"),
    # --- 7 ---
    ("Scattered Grandad's ashes at Brantwood Head on 2026-03-15 with Siobhan and Rafael; half the jar went into the wind, the rest we buried under the rowan tree.", "milestone", "personal", False,
     [("Grandad", "person"), ("Brantwood Head", "place"), ("2026-03-15", "date"), ("Siobhan", "person"), ("Rafael", "person"), ("rowan tree", "concept")],
     [("Grandad", "Brantwood Head", "LOCATED_IN")],
     "when did we scatter my grandfather's remains and who was there and what did we do with them",
     "ashes scatter headland siblings rowan tree half wind half buried date"),
    # --- 8 ---
    ("The estate-clearing of Mum's flat at 44 Linden Court took nine weekends from 2026-01-10 through 2026-03-08; the hardest shelf was the photo albums, not the paperwork.", "architecture", "personal", False,
     [("44 Linden Court", "place"), ("2026-01-10", "date"), ("2026-03-08", "date"), ("photo albums", "concept"), ("paperwork", "concept")],
     [],
     "how long did clearing my mother's flat take and what was the hardest part",
     "estate clear flat weekends date range photo albums harder than paperwork"),
    # --- 9 ---
    ("The empty-nest transition hit on 2025-09-08 when Noor left for Durham; kept her room as-is for six weeks then turned it into the reading room on 2025-10-20.", "milestone", "personal", False,
     [("empty-nest", "concept"), ("2025-09-08", "date"), ("Noor", "person"), ("Durham", "place"), ("reading room", "place"), ("2025-10-20", "date")],
     [("reading room", "empty-nest", "RELATED_TO")],
     "when did the kids leaving home actually land and how long before I changed the room",
     "empty nest child leave university room kept then reading room date"),
    # --- 10. noise ---
    ("Give me a minute — I need to sit with that one for a second.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Divorce from Oisin finalised on 2026-02-12; the transition chapter is harder than the legal one, since the shared Sunday pattern is what needs rebuilding, not the paperwork.", "milestone", "personal", False,
     [("Divorce", "event"), ("Oisin", "person"), ("2026-02-12", "date"), ("Sunday pattern", "concept"), ("paperwork", "concept")],
     [("Sunday pattern", "paperwork", "PREFERS")],
     "when did the divorce land and what part of the change was heavier than expected",
     "divorce finalise date transition shared sunday pattern over paperwork"),
    # --- 12 ---
    ("The miscarriage on 2025-07-03 at 11 weeks reshaped how I see the next pregnancy attempt; no scan photos on the fridge this time, no telling people before 16 weeks.", "decision", "personal", False,
     [("miscarriage", "event"), ("2025-07-03", "date"), ("scan photos", "concept"), ("fridge", "place")],
     [],
     "what did the pregnancy loss change about how I will approach the next one",
     "miscarriage date week no scan fridge no early telling 16 weeks boundary"),
    # --- 13 ---
    ("Lost my job at Harbrook Studios on 2026-01-30 after 11 years; the transition itself — losing the daily team ritual — stings more than the income hit so far.", "problem", "personal", False,
     [("Harbrook Studios", "organization"), ("2026-01-30", "date"), ("daily team ritual", "concept"), ("income", "concept")],
     [("daily team ritual", "income", "PREFERS")],
     "when did the layoff hit and what part of the change surprised me most",
     "job loss date company tenure team ritual sting over income hit"),
    # --- 14 ---
    ("Retired on 2026-04-01 after 34 years at Merrow Engineering; the gold-watch moment was fine, the following Tuesday with no 07:20 alarm was the actual edge.", "milestone", "personal", False,
     [("Retired", "event"), ("2026-04-01", "date"), ("Merrow Engineering", "organization"), ("gold-watch moment", "concept"), ("07:20 alarm", "concept")],
     [],
     "when did retirement happen and which moment was the real transition",
     "retirement date tenure years gold watch fine no alarm tuesday edge"),
    # --- 15 ---
    ("Came out to Mum and Dad on 2025-06-18 at the kitchen table; she cried, he said nothing for six hours then hugged me and asked if I was eating enough.", "milestone", "personal", False,
     [("Mum", "person"), ("Dad", "person"), ("2025-06-18", "date"), ("kitchen table", "place")],
     [],
     "when did I come out to my parents and how did each of them respond",
     "coming out parents date kitchen table mother cry father silent hug"),
    # --- 16 ---
    ("The relocation from Karachi to Bristol on 2025-04-22 is a cultural transition, not a moving one; the boxes were unpacked in a week, the calibration of how much to say in meetings took nine months.", "fact", "personal", False,
     [("Karachi", "place"), ("Bristol", "place"), ("2025-04-22", "date"), ("cultural transition", "concept"), ("meetings", "event")],
     [("cultural transition", "Bristol", "LOCATED_IN")],
     "when was the international move and which layer of the change was the real work",
     "karachi bristol relocation cultural calibration meetings speech nine months"),
    # --- 17 ---
    ("The Parkinson's diagnosis on 2025-10-11 was the beginning of a new life chapter, not just a new treatment plan; Dr Oyelaran called it 'living with' from the first visit.", "milestone", "personal", False,
     [("Parkinson's", "concept"), ("2025-10-11", "date"), ("Dr Oyelaran", "person"), ("living with", "concept")],
     [("living with", "Parkinson's", "RELATED_TO")],
     "when did the neurological diagnosis come and how did the doctor frame the shift",
     "parkinson diagnosis date doctor living with framing chapter not plan"),
    # --- 18 ---
    ("The first-anniversary ritual for Nan is a walk up Pen y Fan on 2026-05-02 with a flask of her tea blend; chose the walk over a church service because she had not been inside a church in 40 years.", "decision", "personal", False,
     [("first-anniversary ritual", "concept"), ("Nan", "person"), ("Pen y Fan", "place"), ("2026-05-02", "date"), ("tea blend", "food"), ("church service", "event")],
     [("first-anniversary ritual", "church service", "REPLACES")],
     "what is the year-after ritual for my grandmother and why it is a hill not a church",
     "first anniversary ritual walk mountain tea flask over church service reason"),
    # --- 19 ---
    ("Replaced the weekly grief-journal habit with the Thursday walk-and-talk with Priya from 2026-02-15; the journal had started repeating itself and the walk does not.", "decision", "personal", False,
     [("grief-journal", "tool"), ("Thursday", "date"), ("walk-and-talk", "activity"), ("Priya", "person"), ("2026-02-15", "date")],
     [("walk-and-talk", "grief-journal", "REPLACES")],
     "which bereavement practice took over from the journalling and what was the reason",
     "grief journal swap walk talk thursday partner repetition freshness date"),
    # --- 20 ---
    ("Whiskers the cat died on 2026-03-28 after 17 years; the shape of the evening routine is what hurts most, not the empty bed — the 18:00 tin-opener click was a ritual.", "problem", "personal", False,
     [("Whiskers", "concept"), ("2026-03-28", "date"), ("evening routine", "concept"), ("18:00 tin-opener click", "concept")],
     [("18:00 tin-opener click", "evening routine", "RELATED_TO")],
     "when did the cat die and which piece of the absence is hitting hardest",
     "cat death date age seventeen evening routine tin opener ritual loss"),
    # --- 21 ---
    ("The obituary-writing workshop run by Marigold Press on 2026-01-24 taught the 'three verbs, one fact, one kindness' frame; used it on Auntie Bea's piece the next month.", "reference", "personal", False,
     [("obituary-writing workshop", "event"), ("Marigold Press", "organization"), ("2026-01-24", "date"), ("three verbs, one fact, one kindness", "method"), ("Auntie Bea", "person")],
     [],
     "which obituary course gave me a working template and how quickly did I apply it",
     "obituary workshop publisher date three verb one fact kindness template"),
    # --- 22 ---
    ("Prefers Francis Weller's The Wild Edge of Sorrow to Joan Didion's The Year of Magical Thinking for this stage; Weller gives a practice, Didion gives a mirror.", "preference", "personal", False,
     [("Francis Weller", "person"), ("The Wild Edge of Sorrow", "concept"), ("Joan Didion", "person"), ("The Year of Magical Thinking", "concept"), ("practice", "concept"), ("mirror", "concept")],
     [("The Wild Edge of Sorrow", "The Year of Magical Thinking", "PREFERS")],
     "which grief book is doing the heavier lifting for me now and what is each giving",
     "wild edge sorrow weller over year magical thinking didion practice mirror"),
    # --- 23 ---
    ("The Dad-shaped gap in Sunday mornings is now a standing call with Siobhan at 09:30; started 2025-12-07, unbroken for 18 weeks.", "architecture", "personal", False,
     [("Dad", "person"), ("Sunday", "date"), ("Siobhan", "person"), ("2025-12-07", "date")],
     [],
     "how did I fill the sunday morning hole after my father's death",
     "sunday call sister replacement father gap start date weeks unbroken"),
    # --- 24 ---
    ("The widow's-mite stage — when practical help has dried up and the casseroles stop — landed around week seven after Mum died; Reverend Okafor had warned me about it in week two.", "fact", "personal", False,
     [("widow's-mite stage", "concept"), ("casseroles", "food"), ("Mum", "person"), ("Reverend Okafor", "person")],
     [("widow's-mite stage", "casseroles", "RELATED_TO")],
     "when did the post-funeral support fall off and who had warned me it would",
     "widows mite casserole dry up week seven reverend warning earlier"),
    # --- 25 ---
    ("Chose to keep Dad's wedding ring on a chain rather than on my right hand; the neck does not catch on keyboards and the ring stays off the laundry drum.", "decision", "personal", False,
     [("Dad", "person"), ("wedding ring", "tool"), ("chain", "tool"), ("right hand", "concept"), ("laundry drum", "infrastructure")],
     [("chain", "right hand", "PREFERS")],
     "which way of keeping my father's ring close won out and why",
     "wedding ring chain over right hand keyboard laundry drum reason"),
    # --- 26 ---
    ("The sibling estate-clearing meeting on 2026-02-01 divided the china between four households using a slip-draw; Rafael got the blue plates, Siobhan the teapot.", "decision", "personal", False,
     [("sibling estate-clearing meeting", "event"), ("2026-02-01", "date"), ("china", "concept"), ("slip-draw", "method"), ("Rafael", "person"), ("Siobhan", "person"), ("teapot", "tool")],
     [],
     "how did we split Mum's china among the siblings and which items landed where",
     "estate meeting china divide slip draw blue plates teapot sibling date"),
    # --- 27 ---
    ("Prefers the group bereavement circle at Ash Lodge on Wednesday evenings to one-to-one counselling; the circle reminds me I am not the exception.", "preference", "personal", False,
     [("group bereavement circle", "activity"), ("Ash Lodge", "place"), ("Wednesday", "date"), ("one-to-one counselling", "activity")],
     [("group bereavement circle", "one-to-one counselling", "PREFERS")],
     "which grief-support format wins out for me and what the group gives that the chair does not",
     "bereavement circle group over one to one counselling not exception"),
    # --- 28 ---
    ("The divorce-as-transition reading list starts with Bruce Feiler's Life Is in the Transitions; skipped the trendier Untamed because the frame is narrower than the title suggests.", "preference", "personal", False,
     [("Bruce Feiler", "person"), ("Life Is in the Transitions", "concept"), ("Untamed", "concept")],
     [("Life Is in the Transitions", "Untamed", "PREFERS")],
     "which transition-focused book leads my divorce reading and which one got skipped",
     "feiler life transitions over untamed divorce reading list reason"),
    # --- 29 ---
    ("The first Christmas without Dad on 2025-12-25 kept the roast but dropped the carol service; the church would have been the room where the grief got loudest.", "decision", "personal", False,
     [("Christmas", "event"), ("Dad", "person"), ("2025-12-25", "date"), ("roast", "food"), ("carol service", "event"), ("church", "place")],
     [("roast", "carol service", "PREFERS")],
     "what did the first holiday without my father keep and what did it drop and why",
     "first christmas without father roast keep carol service drop church loud"),
    # --- 30 ---
    ("The handwritten letters Mum left in the biscuit tin — one per grandchild — were found on 2026-01-18 under the old tea towels; handed them out at the scattering.", "milestone", "personal", False,
     [("handwritten letters", "concept"), ("Mum", "person"), ("biscuit tin", "tool"), ("2026-01-18", "date"), ("tea towels", "tool"), ("scattering", "event")],
     [("handwritten letters", "biscuit tin", "LOCATED_IN")],
     "when did I find my mother's hidden letters and when were they handed out",
     "handwritten letters mother biscuit tin grandchild found date scattering"),
    # --- 31 ---
    ("Replaced the anniversary dinner-out ritual with a dawn walk along Chesil Beach on 2026-02-12; dinner had become a performance, the walk just exists.", "decision", "personal", False,
     [("anniversary dinner-out", "event"), ("dawn walk", "activity"), ("Chesil Beach", "place"), ("2026-02-12", "date")],
     [("dawn walk", "anniversary dinner-out", "REPLACES")],
     "which ritual swap marked the first divorce-anniversary marker and why",
     "dinner out replaced dawn walk beach divorce anniversary performance"),
    # --- 32 ---
    ("The empty-nest depression dip hit in week 11; Dr Halima ruled out clinical depression on 2025-11-24 and named it 'transition grief' instead.", "milestone", "personal", False,
     [("empty-nest", "concept"), ("Dr Halima", "person"), ("2025-11-24", "date"), ("transition grief", "concept"), ("clinical depression", "concept")],
     [("transition grief", "clinical depression", "REPLACES")],
     "when did the post-kids slump get named and what did the doctor rule out",
     "empty nest dip week eleven doctor transition grief not clinical depression"),
    # --- 33 ---
    ("Chose cremation over burial for Whiskers at Fern Valley Pet Services; Noor wanted a spot, the garden is rented, cremation keeps the option open.", "decision", "personal", False,
     [("cremation", "method"), ("burial", "method"), ("Whiskers", "concept"), ("Fern Valley Pet Services", "organization"), ("Noor", "person"), ("garden", "place")],
     [("cremation", "burial", "PREFERS")],
     "which farewell option won for the cat and what made the rental situation decide it",
     "pet cremation over burial rented garden child spot option open"),
    # --- 34. noise ---
    ("Sorry, the kettle just clicked off, one moment.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The coming-out to the wider family on 2025-08-30 at the summer barbecue went better than the parents reveal; Uncle Declan had guessed in 2014 and said so on the patio.", "fact", "personal", False,
     [("coming-out", "event"), ("2025-08-30", "date"), ("summer barbecue", "event"), ("Uncle Declan", "person"), ("patio", "place")],
     [],
     "when did the extended-family come out happen and who made it easy",
     "coming out extended family summer barbecue date uncle guessed patio"),
    # --- 36 ---
    ("The redundancy-transition coach Beatriz Souza from 2026-02-09 to 2026-04-06 was worth £1,400; reframed the gap as a sabbatical, not a wound.", "fact", "personal", False,
     [("redundancy-transition coach", "person"), ("Beatriz Souza", "person"), ("2026-02-09", "date"), ("2026-04-06", "date"), ("sabbatical", "concept"), ("wound", "concept")],
     [("sabbatical", "wound", "PREFERS")],
     "which coach helped with the layoff transition and how did she reframe the time",
     "redundancy coach name date range fee sabbatical over wound reframe"),
    # --- 37 ---
    ("The diagnosis-transition journal with Dr Oyelaran tracks motor symptoms weekly since 2025-10-18; the emotional pages are longer than the tremor pages so far.", "architecture", "personal", False,
     [("diagnosis-transition journal", "tool"), ("Dr Oyelaran", "person"), ("2025-10-18", "date"), ("motor symptoms", "finding"), ("tremor", "finding")],
     [],
     "how is the diagnosis notebook structured and what does it show about the first months",
     "diagnosis journal doctor weekly motor symptoms emotional longer tremor"),
    # --- 38 ---
    ("Prefers the 'continuing bonds' frame from Klass, Silverman and Nickman to the 'let go and move on' advice Aunt Philippa keeps offering.", "preference", "personal", False,
     [("continuing bonds", "concept"), ("Klass", "person"), ("Silverman", "person"), ("Nickman", "person"), ("let go and move on", "concept"), ("Aunt Philippa", "person")],
     [("continuing bonds", "let go and move on", "PREFERS")],
     "which grief framework lands for me and which folk advice am I pushing back on",
     "bereavement model authors trio preferred family elder platitude reject"),
    # --- 39 ---
    ("The retirement-transition plan uses Nancy Schlossberg's 4S model — situation, self, support, strategies — pinned on the inside of the wardrobe door.", "reference", "personal", False,
     [("retirement-transition plan", "concept"), ("Nancy Schlossberg", "person"), ("4S model", "method"), ("wardrobe door", "place")],
     [("4S model", "wardrobe door", "LOCATED_IN")],
     "which framework is scaffolding my retirement plan and where does it live physically",
     "later life career end scaffold schlossberg four esses closet interior pin"),
    # --- 40 ---
    ("Chose to keep Oisin's cookbook collection on the shelf post-divorce rather than boxing them; the recipes are mine too now and the kitchen is already quieter.", "decision", "personal", False,
     [("Oisin", "person"), ("cookbook collection", "concept"), ("shelf", "place"), ("kitchen", "place")],
     [("shelf", "kitchen", "LOCATED_IN")],
     "what did I decide about the ex-partner's books and what drove it",
     "ex cookbook kept shelf not boxed recipes mine kitchen quieter reason"),
    # --- 41 ---
    ("The miscarriage-anniversary ritual on 2026-07-03 is a candle on the mantel at 14:20, the time the scan confirmed it; the same time the next year is already on the calendar.", "architecture", "personal", False,
     [("miscarriage-anniversary ritual", "concept"), ("2026-07-03", "date"), ("candle", "tool"), ("mantel", "place"), ("14:20", "date"), ("calendar", "tool")],
     [("candle", "mantel", "LOCATED_IN")],
     "how is the pregnancy-loss anniversary marked and how far ahead is it booked",
     "miscarriage anniversary candle mantel time scan calendar ahead"),
    # --- 42 ---
    ("Replaced the daily obituary-section reading habit with the Marginalian newsletter from 2026-03-01; the obits were tilting the day dark before 07:00.", "decision", "personal", False,
     [("obituary-section", "concept"), ("Marginalian newsletter", "concept"), ("2026-03-01", "date")],
     [("Marginalian newsletter", "obituary-section", "REPLACES")],
     "which morning reading took over from the obituaries and why the swap",
     "obituary section swap marginalian newsletter morning tone dark before"),
    # --- 43 ---
    ("The post-divorce identity-transition therapy with Amara Kofi on Tuesdays at 18:00 is twelve sessions, CBT-adjacent; session five was the breakpoint.", "reference", "personal", False,
     [("identity-transition therapy", "activity"), ("Amara Kofi", "person"), ("Tuesdays", "date"), ("CBT-adjacent", "method"), ("session five", "event")],
     [],
     "how is the post-divorce therapy structured and which session was the turning point",
     "identity therapy tuesday cbt twelve session count five breakpoint"),
    # --- 44 ---
    ("Prefers the Irish-wake format with open coffin and night-long sitting over the English funeral-home viewing-hour; had the Irish form for Dad, skipped the viewing for Mum.", "preference", "personal", False,
     [("Irish-wake format", "method"), ("open coffin", "concept"), ("English funeral-home", "organization"), ("viewing-hour", "event"), ("Dad", "person"), ("Mum", "person")],
     [("Irish-wake format", "viewing-hour", "PREFERS")],
     "which farewell custom wins for me and which parent got which format",
     "irish wake over english funeral viewing father irish mother skipped"),
    # --- 45 ---
    ("The week-one post-diagnosis fatigue peaked around 2025-10-18 and was more grief than biology; Dr Halima called the first week 'anticipatory mourning' and it fit.", "problem", "personal", False,
     [("2025-10-18", "date"), ("Dr Halima", "person"), ("anticipatory mourning", "concept"), ("biology", "concept")],
     [("anticipatory mourning", "biology", "PREFERS")],
     "what hit in the first week after the diagnosis and what name made sense of it",
     "week one diagnosis fatigue grief over biology anticipatory mourning fit"),
    # --- 46 ---
    ("The cross-cultural-transition counselling through Bristol Bridge on 2025-09-15 to 2026-02-02 ran 18 sessions; the homesickness was grief for a version of me, not a place.", "milestone", "personal", False,
     [("cross-cultural-transition counselling", "activity"), ("Bristol Bridge", "organization"), ("2025-09-15", "date"), ("2026-02-02", "date"), ("homesickness", "concept")],
     [],
     "how long did the cultural-adjustment counselling run and what did it reveal the homesickness was",
     "cross cultural counselling date range sessions homesickness self grief"),
    # --- 47 ---
    ("The memory-box for Nan lives on the top shelf of the airing cupboard: lavender handkerchief, recipe cards, the 1978 seaside photo, her reading glasses.", "reference", "personal", False,
     [("memory-box", "tool"), ("Nan", "person"), ("airing cupboard", "place"), ("lavender handkerchief", "tool"), ("recipe cards", "concept"), ("1978 seaside photo", "concept"), ("reading glasses", "tool")],
     [("memory-box", "airing cupboard", "LOCATED_IN")],
     "where does my grandmother's keepsake box live and what is inside it",
     "memory box grandmother airing cupboard hanky recipe photo glasses"),
    # --- 48 ---
    ("Replaced the 'moving on' phrase in the family vocabulary with 'carrying with' after a nudge from Marigold Press editor Tamsin on 2026-02-14.", "decision", "personal", False,
     [("moving on", "concept"), ("family vocabulary", "concept"), ("carrying with", "concept"), ("Marigold Press", "organization"), ("Tamsin", "person"), ("2026-02-14", "date")],
     [("carrying with", "moving on", "REPLACES")],
     "which phrase did the family retire and what replaced it and who suggested the swap",
     "moving on replaced carrying with family phrase editor nudge date"),
    # --- 49 ---
    ("The sibling-loss after Rafael's death on 2024-08-02 changed the birth-order feeling on 2026-04-02 when I turned 41 and became older than he ever would be.", "milestone", "personal", False,
     [("sibling-loss", "concept"), ("Rafael", "person"), ("2024-08-02", "date"), ("birth-order feeling", "concept"), ("2026-04-02", "date")],
     [],
     "when did the sibling grief shift and which birthday triggered it",
     "sibling loss brother death date birth order feeling birthday older than"),
    # --- 50 ---
    ("The anniversary-of-loss candle on 2026-11-14 is already planned: St Luke's hospice chapel at 11:00, then a walk to the pier with Dad's thermos.", "architecture", "personal", False,
     [("anniversary-of-loss", "concept"), ("2026-11-14", "date"), ("St Luke's", "organization"), ("chapel", "place"), ("pier", "place"), ("Dad", "person"), ("thermos", "tool")],
     [("chapel", "St Luke's", "LOCATED_IN")],
     "what is the plan for the one-year mark and what props anchor it",
     "anniversary candle date hospice chapel eleven walk pier father thermos"),
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
