"""One-off emitter for shared-base batch-060 — personal domain (mindfulness and mental-health practices slice).

Writes 50 rows to data/v2/shared/batch_060.tmp.jsonl with ids shared-02951..03000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_060.tmp.jsonl"
ID_OFFSET = 2950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The morning sit on the zafu lasts 22 minutes by the Insight Timer bell; legs cross to the right because the left hip locks if it leads.", "architecture", "personal", False,
     [("zafu", "tool"), ("Insight Timer", "tool"), ("right", "concept"), ("left hip", "concept")],
     [],
     "how is the early-day cushion practice timed and which leg crosses on top",
     "morning meditation cushion duration timer leg cross hip lock side"),
    # --- 2 ---
    ("Switched the evening journal from the bullet-point format to the morning-pages style on 2026-02-14; three full A5 pages, no editing, no rereading.", "decision", "personal", False,
     [("bullet-point format", "method"), ("morning-pages style", "method"), ("2026-02-14", "date"), ("A5", "concept")],
     [("morning-pages style", "bullet-point format", "REPLACES")],
     "which journaling style took over for the nighttime entries and what does it look like",
     "journal swap bullet to morning pages volume rule no edit date"),
    # --- 3 ---
    ("Prefers Tara Brach's RAIN talks over the Sam Harris guided sessions on Waking Up; the pacing leaves room to actually feel rather than chase insight.", "preference", "personal", False,
     [("Tara Brach", "person"), ("RAIN", "method"), ("Sam Harris", "person"), ("Waking Up", "tool")],
     [("Tara Brach", "Sam Harris", "PREFERS")],
     "which guided-meditation voice wins out and why the pacing matters",
     "RAIN talks over waking up guided pacing room feel insight chase"),
    # --- 4 ---
    ("Started weekly therapy with Dr Halpern on 2026-01-08 after a bad three months; CBT-leaning, 50 minutes, Wednesdays at 14:00, video by default.", "milestone", "personal", False,
     [("Dr Halpern", "person"), ("2026-01-08", "date"), ("CBT", "method"), ("Wednesdays", "date")],
     [],
     "when did the weekly therapy slot begin and how is the session shaped",
     "therapy start date clinician CBT slot length day video format"),
    # --- 5 ---
    ("The box-breathing pattern for the 06:40 train is four-four-four-four for ten cycles; longer holds spike the lightheadedness, not the calm.", "fact", "personal", False,
     [("box-breathing", "method"), ("06:40 train", "place"), ("ten cycles", "concept"), ("lightheadedness", "emotion")],
     [],
     "how is the commute breathing drill paced and what happens with longer holds",
     "box breathing commute pattern count cycles long hold side effect"),
    # --- 6 ---
    ("Replaced the Calm subscription with Insight Timer on 2026-03-02; the teacher variety matters more than the polished UI and the price difference is real.", "decision", "personal", False,
     [("Calm", "tool"), ("Insight Timer", "tool"), ("2026-03-02", "date"), ("UI", "concept")],
     [("Insight Timer", "Calm", "REPLACES")],
     "which mindfulness app took over the subscription and what drove the change",
     "calm to insight timer swap teacher range polish price reason date"),
    # --- 7 ---
    ("The gratitude practice is three concrete items at lights-out, said aloud not written; abstractions like \"my health\" don't count, the orange at lunch does.", "architecture", "personal", False,
     [("gratitude practice", "activity"), ("lights-out", "event"), ("orange", "food"), ("lunch", "event")],
     [],
     "how is the bedtime thankfulness ritual structured and what counts as valid",
     "gratitude three items aloud bedtime concrete rule abstraction skip"),
    # --- 8 ---
    ("The mood log in Daylio shows seven straight low-mood days from 2026-03-19 through 2026-03-25; the trigger column points at the work review, not the weather.", "fact", "personal", False,
     [("Daylio", "tool"), ("2026-03-19", "date"), ("2026-03-25", "date"), ("work review", "event"), ("low-mood days", "emotion"), ("weather", "concept")],
     [("work review", "low-mood days", "CAUSES")],
     "what does the recent mood-tracker streak show and what does it pin as the cause",
     "daylio downbeat run trigger column blamed deadline not climate week"),
    # --- 9 ---
    ("The ten-day Vipassana retreat at Dhamma Dipa is booked for 2026-09-04 through 2026-09-14; phone surrendered, noble silence, 4 a.m. wake bell.", "milestone", "personal", False,
     [("Vipassana", "method"), ("Dhamma Dipa", "place"), ("2026-09-04", "date"), ("2026-09-14", "date"), ("noble silence", "concept")],
     [("Vipassana", "Dhamma Dipa", "LOCATED_IN")],
     "when is the silent retreat scheduled and what are the conditions on entry",
     "vipassana retreat booking centre date range silence wake bell phone"),
    # --- 10. noise ---
    ("Hold on, let me grab a glass of water before we keep going.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The grief sessions for Nan use the continuing-bonds frame from Dr Halpern, not the five-stages model; permission to keep talking to her was the unlock.", "fact", "personal", False,
     [("Nan", "person"), ("continuing-bonds", "theory"), ("Dr Halpern", "person"), ("five-stages model", "theory")],
     [("continuing-bonds", "five-stages model", "REPLACES")],
     "which bereavement framework is therapy using for losing my grandmother and what shifted",
     "grief framing continuing bonds over five stages permission talk unlock"),
    # --- 12 ---
    ("Prefers the Headspace sleepcasts to the Calm sleep stories; the slow-pace narration in the sleepcasts actually slows my own breath, the stories don't.", "preference", "personal", False,
     [("Headspace", "tool"), ("sleepcasts", "tool"), ("Calm", "tool"), ("sleep stories", "tool")],
     [("sleepcasts", "sleep stories", "PREFERS")],
     "which wind-down audio wins for falling asleep and why the pacing matters",
     "headspace sleepcasts over calm stories slow narration breath effect"),
    # --- 13 ---
    ("The anxiety coping kit in the desk drawer is a 4-7-8 cue card, a peppermint tin, a spare pen, and a creased copy of the values list.", "reference", "personal", False,
     [("anxiety coping kit", "tool"), ("desk drawer", "place"), ("4-7-8", "method"), ("peppermint tin", "tool"), ("values list", "tool")],
     [("anxiety coping kit", "desk drawer", "LOCATED_IN")],
     "where is the panic-moment toolkit kept and what is in it",
     "anxiety kit desk drawer breathing card peppermint values list inventory"),
    # --- 14 ---
    ("The body-scan length on Friday nights is 32 minutes; anything shorter and I skim the legs, anything longer and I fall asleep before the shoulders.", "preference", "personal", False,
     [("body-scan", "method"), ("Friday", "date"), ("legs", "concept"), ("shoulders", "concept")],
     [],
     "how long does the weekend somatic scan need to land properly and where do shorter or longer slip",
     "body scan duration friday optimum skim leg fall asleep shoulder"),
    # --- 15 ---
    ("Started the loving-kindness practice on 2026-02-09 to soften the morning resentment about Marcus; the neutral-person phase is still the hardest one.", "milestone", "personal", False,
     [("loving-kindness practice", "method"), ("2026-02-09", "date"), ("Marcus", "person"), ("neutral-person phase", "concept")],
     [],
     "when did the metta practice start and which stage still resists",
     "loving kindness start date target person neutral phase difficulty"),
    # --- 16 ---
    ("The therapy homework binder lives on the second shelf in the bedroom; thought records, the pie chart of responsibility, the bedtime worry-time worksheet.", "reference", "personal", False,
     [("therapy homework binder", "tool"), ("second shelf", "place"), ("thought records", "tool"), ("pie chart", "tool"), ("worry-time worksheet", "tool")],
     [("therapy homework binder", "second shelf", "LOCATED_IN")],
     "where is the CBT homework folder kept and what worksheets are in it",
     "therapy binder shelf thought record pie chart worry time worksheet"),
    # --- 17 ---
    ("Switched from journaling on the laptop to a Leuchtturm1917 hardback on 2026-03-15; the typing made me edit, the pen made me actually finish a thought.", "decision", "personal", False,
     [("laptop", "tool"), ("Leuchtturm1917", "tool"), ("2026-03-15", "date")],
     [("Leuchtturm1917", "laptop", "REPLACES")],
     "which writing surface took over for the journal and what behaviour shifted",
     "journal swap laptop to notebook hardback edit habit finish thought"),
    # --- 18 ---
    ("The walking meditation loop in Stanpit Park is 1.4 km on the gravel side; counting steps in tens, hands behind the back, gaze a metre ahead.", "architecture", "personal", False,
     [("walking meditation", "method"), ("Stanpit Park", "place"), ("gravel side", "place"), ("hands", "concept")],
     [("walking meditation", "Stanpit Park", "LOCATED_IN")],
     "how is the slow-walk practice structured around the park and what are the form rules",
     "walking meditation loop park distance count gaze hand position"),
    # --- 19 ---
    ("The panic episode on 2026-02-27 in the Tesco queue lasted six minutes; the fix was naming five things by texture, not the breathing exercise I expected.", "problem", "personal", False,
     [("panic episode", "emotion"), ("2026-02-27", "date"), ("Tesco", "place"), ("texture", "concept")],
     [("texture", "panic episode", "FIXES")],
     "what helped the supermarket panic spell that day and what surprisingly did not",
     "panic supermarket queue duration grounding texture five senses fix"),
    # --- 20 ---
    ("Prefers the in-person therapy slot to the video slot when the diary allows; eye contact across the room reads cleaner than across a webcam.", "preference", "personal", False,
     [("in-person therapy", "method"), ("video", "method"), ("eye contact", "concept"), ("webcam", "tool")],
     [("in-person therapy", "video", "PREFERS")],
     "which therapy delivery format wins out when the calendar permits and why",
     "therapy in person over video eye contact reading webcam difference"),
    # --- 21 ---
    ("The breath-count drill at the desk runs twenty inhales between emails; reset to one on any thought-snag, no judgement, just the count.", "architecture", "personal", False,
     [("breath-count drill", "method"), ("desk", "place"), ("inhales", "concept"), ("emails", "concept")],
     [],
     "how is the inbox-pause breathing routine structured and how do snags get handled",
     "breath count desk twenty inhale email reset rule no judgement"),
    # --- 22 ---
    ("Replaced the wine-with-dinner habit with chamomile and a gratitude line on 2026-01-19; sleep architecture shifted inside two weeks per the Oura ring.", "decision", "personal", False,
     [("wine", "food"), ("chamomile", "food"), ("gratitude line", "activity"), ("2026-01-19", "date"), ("Oura ring", "tool")],
     [("chamomile", "wine", "REPLACES")],
     "which evening ritual swap stuck and what did the sleep tracker notice",
     "wine swap chamomile gratitude bedtime sleep architecture oura two week"),
    # --- 23 ---
    ("The Sunday self-care block is 16:00 to 19:00, no calendar invites allowed; bath, journal, slow tea, no screens until the lights go down.", "architecture", "personal", False,
     [("Sunday", "date"), ("self-care block", "activity"), ("bath", "activity"), ("tea", "food")],
     [],
     "how is the weekly recharge window protected and what fills it",
     "sunday self care window bath journal tea no screens calendar block"),
    # --- 24 ---
    ("The grief letter to Nan written on 2026-03-22 stays sealed in the second-shelf binder; therapy uses it as an anchor, not something I reread alone.", "fact", "personal", False,
     [("grief letter", "tool"), ("Nan", "person"), ("2026-03-22", "date"), ("second-shelf binder", "tool")],
     [("grief letter", "second-shelf binder", "LOCATED_IN")],
     "where does the bereavement letter live and what is the rule about reading it",
     "grief letter sealed binder anchor therapy not reread alone date"),
    # --- 25 ---
    ("Prefers the Plum Village app over Insight Timer for guided walking sessions; the bell intervals are tuned for outdoor pace and the voices are unhurried.", "preference", "personal", False,
     [("Plum Village", "tool"), ("Insight Timer", "tool"), ("bell intervals", "concept")],
     [("Plum Village", "Insight Timer", "PREFERS")],
     "which app wins for guided walking practice and why the bell pacing matters",
     "plum village over insight timer walking bell interval outdoor pace"),
    # --- 26 ---
    ("The mental-health day cap is one per quarter, taken before things wobble not after; logged on 2026-03-06 with no agenda beyond a long walk and soup.", "decision", "personal", False,
     [("mental-health day", "activity"), ("quarter", "date"), ("2026-03-06", "date"), ("soup", "food"), ("walk", "activity")],
     [],
     "how is the wellbeing day budget set and what did the most recent one look like",
     "mental health day quarterly cap proactive timing recent date plan"),
    # --- 27 ---
    ("The thought-record template stuck after three weeks: situation, emotion 0-100, hot thought, evidence for, evidence against, balanced thought.", "reference", "personal", False,
     [("thought-record template", "tool"), ("hot thought", "concept"), ("evidence for", "concept"), ("evidence against", "concept"), ("balanced thought", "concept")],
     [],
     "what fields does my CBT thought record have and how is the rating done",
     "cognitive worksheet columns scenario feeling scale automatic belief pro con reframe"),
    # --- 28 ---
    ("Switched from Headspace sleep meditations to the Nothing Much Happens podcast on 2026-02-21; story arcs land me before the second commercial break does.", "decision", "personal", False,
     [("Headspace", "tool"), ("Nothing Much Happens", "publication"), ("2026-02-21", "date")],
     [("Nothing Much Happens", "Headspace", "REPLACES")],
     "which bedtime audio replaced the meditation app and how fast does it work",
     "headspace sleep swap nothing much happens podcast story arc duration"),
    # --- 29 ---
    ("Joined the men's grief circle at Harbourside Centre on 2026-04-02; six attendees, hour and a half, no fixing-language, no advice unless asked.", "milestone", "personal", False,
     [("men's grief circle", "organization"), ("Harbourside Centre", "place"), ("2026-04-02", "date"), ("fixing-language", "concept")],
     [("men's grief circle", "Harbourside Centre", "LOCATED_IN")],
     "when did I start the bereavement support group and what are the conversation rules",
     "men grief circle start size duration ground rules fix advice"),
    # --- 30 ---
    ("The Stoic evening review takes ten minutes: what went well, what went poorly, what to do tomorrow; framed from Aurelius via the Daily Stoic prompts.", "reference", "personal", False,
     [("Stoic evening review", "method"), ("Aurelius", "person"), ("Daily Stoic", "publication")],
     [("Stoic evening review", "Daily Stoic", "BUILDS_ON")],
     "how is the nighttime examen structured and where does the framing come from",
     "stoic evening review three questions duration aurelius daily stoic source"),
    # --- 31 ---
    ("The morning anxiety spike at 05:40 is treated as data not threat; cold water on the face, write the thought down, decide if it's actionable before 07:00.", "architecture", "personal", False,
     [("morning anxiety spike", "emotion"), ("05:40", "date"), ("cold water", "concept"), ("07:00", "date")],
     [],
     "how is the early-hours dread protocol set up and what is the cutoff for action",
     "morning anxiety spike data not threat cold water write decision time"),
    # --- 32 ---
    ("Prefers the open-monitoring style on Saturday mornings to the breath-anchor style; weekday-anchor focus is fine but on Saturday the wide aperture works better.", "preference", "personal", False,
     [("open-monitoring style", "method"), ("Saturday", "date"), ("breath-anchor style", "method"), ("weekday-anchor", "concept")],
     [("open-monitoring style", "breath-anchor style", "PREFERS")],
     "which meditation style wins on the weekend morning and how it differs from weekdays",
     "open monitoring saturday over breath anchor weekday focus aperture"),
    # --- 33. noise ---
    ("Anyway, where was I before the kettle boiled.", "fact", "noise", True, [], [], None, None),
    # --- 34 ---
    ("The DBT distress-tolerance card in the wallet lists TIPP: Temperature, Intense exercise, Paced breathing, Paired muscle relaxation; used twice this month.", "reference", "personal", False,
     [("DBT", "method"), ("distress-tolerance card", "tool"), ("wallet", "place"), ("TIPP", "method")],
     [("DBT", "TIPP", "HAS_PART")],
     "which crisis-skills card sits in the wallet and what does the acronym unpack to",
     "dialectical crisis prompt billfold acronym thermal cardio paced inhale muscle release usage"),
    # --- 35 ---
    ("Prefers the silent zazen sit at the Hampshire Zen group to the chanted opening; the chanting cues a thinking mind and the silence does not.", "preference", "personal", False,
     [("silent zazen", "method"), ("Hampshire Zen group", "organization"), ("chanted opening", "method")],
     [("silent zazen", "chanted opening", "PREFERS")],
     "which sit-format wins at the local Zen group and what the chanting did",
     "zazen silent over chant cue thinking mind hampshire group reason"),
    # --- 36 ---
    ("The sleep-hygiene rules I keep from CBT-i: bed only for sleep, fixed wake time, no clock-watching, leave the room after 20 minutes awake.", "reference", "personal", False,
     [("sleep-hygiene", "method"), ("CBT-i", "method"), ("fixed wake time", "concept"), ("clock-watching", "concept")],
     [("sleep-hygiene", "CBT-i", "BUILDS_ON")],
     "which insomnia-protocol rules actually stuck and what is the room rule",
     "sleep hygiene CBT-i bed sleep only fixed wake leave room twenty"),
    # --- 37 ---
    ("The journaling streak hit 90 days on 2026-04-09; missed two days early on, restarted same evening, no zero-day rule still holds.", "milestone", "personal", False,
     [("journaling streak", "activity"), ("2026-04-09", "date"), ("no zero-day rule", "concept")],
     [],
     "when did the writing streak hit ninety and what rule keeps it going through misses",
     "journal streak ninety day milestone restart rule no zero day date"),
    # --- 38 ---
    ("The Finch app stays installed for streak nudge but the meditation content was thin; pair it with Insight Timer and let Finch just track.", "decision", "personal", False,
     [("Finch", "tool"), ("Insight Timer", "tool")],
     [("Finch", "Insight Timer", "COMMUNICATES_WITH")],
     "what role does the streak app play now and which app is doing the actual practice work",
     "finch role tracker insight timer practice content split tools"),
    # --- 39 ---
    ("The breath-focused 4-7-8 pattern beats the longer Wim Hof drill for pre-meeting nerves; the holds in Wim Hof spike adrenaline I do not want before talking.", "preference", "personal", False,
     [("4-7-8", "method"), ("Wim Hof", "method"), ("pre-meeting", "event"), ("adrenaline", "concept")],
     [("4-7-8", "Wim Hof", "PREFERS")],
     "which breathwork wins right before a meeting and what does the alternative do wrong",
     "4 7 8 over wim hof pre meeting nerves adrenaline spike unwanted"),
    # --- 40 ---
    ("The values clarification done on 2026-01-29 with Dr Halpern surfaced four anchors: craft, candour, contact, contribution; pinned to the office wall.", "milestone", "personal", False,
     [("values clarification", "method"), ("2026-01-29", "date"), ("Dr Halpern", "person"), ("craft", "concept"), ("candour", "concept"), ("contact", "concept")],
     [],
     "when did the values exercise happen and what anchors came out of it",
     "values clarification session four anchors office pin date"),
    # --- 41 ---
    ("The morning meditation app rotates: Insight Timer Monday and Wednesday, Plum Village Tuesday and Thursday, no app on Friday — silence with a kitchen timer.", "architecture", "personal", False,
     [("Insight Timer", "tool"), ("Monday", "date"), ("Wednesday", "date"), ("Plum Village", "tool"), ("Friday", "date"), ("kitchen timer", "tool")],
     [],
     "how is the weekday meditation tool rotation set and what happens on the last weekday",
     "meditation app rotation week split insight plum village friday silent timer"),
    # --- 42 ---
    ("The grief wave hit hard on 2026-03-30 at the kitchen sink; sat with it for eleven minutes per the Insight Timer log, did not reach for a podcast.", "fact", "personal", False,
     [("grief wave", "emotion"), ("2026-03-30", "date"), ("kitchen sink", "place"), ("Insight Timer", "tool"), ("podcast", "tool")],
     [],
     "what happened with the bereavement surge that day and how did I sit with it",
     "grief wave kitchen sink sit duration timer not podcast date"),
    # --- 43 ---
    ("The therapy fee is £80 a session paid by standing order on the 1st; the sliding-scale conversation got tabled until the next contract review.", "reference", "personal", False,
     [("therapy fee", "concept"), ("standing order", "method"), ("sliding-scale", "method")],
     [],
     "how is the therapy bill paid and what is the deferred conversation about",
     "therapy fee monthly standing order sliding scale defer contract review"),
    # --- 44 ---
    ("The mindful-eating rule for the first bite is twenty chews and the fork down between bites; collapses by mid-meal but the first three bites land.", "fact", "personal", False,
     [("mindful-eating rule", "method"), ("fork", "tool"), ("first three bites", "concept")],
     [],
     "what is the slow-eating rule that actually holds and where does it fall apart",
     "conscious dining opening mouthful chewing target utensil pause discipline lapses halfway"),
    # --- 45 ---
    ("The Sunday self-compassion break uses Kristin Neff's three steps: this is a moment of suffering, suffering is part of life, may I be kind to myself.", "reference", "personal", False,
     [("Sunday", "date"), ("self-compassion break", "method"), ("Kristin Neff", "person"), ("suffering", "concept")],
     [("self-compassion break", "Kristin Neff", "AUTHORED_BY")],
     "what three-step compassion script anchors the weekend practice and who shaped it",
     "self compassion break sunday three step neff suffering kindness script"),
    # --- 46 ---
    ("Replaced the doom-scroll first-thing-AM habit with the Insight Timer kindness bell on 2026-02-12; the cortisol spike on waking is visibly smaller per the ring.", "decision", "personal", False,
     [("doom-scroll", "activity"), ("Insight Timer", "tool"), ("kindness bell", "tool"), ("2026-02-12", "date"), ("cortisol", "concept"), ("ring", "tool")],
     [("kindness bell", "doom-scroll", "REPLACES")],
     "which morning habit got swapped out and what did the body actually register",
     "doom scroll swap kindness bell morning cortisol spike ring date"),
    # --- 47 ---
    ("The MBSR eight-week course at Riverside Hall ran 2026-01-13 through 2026-03-03; the home-practice CD was the part I undervalued going in.", "milestone", "personal", False,
     [("MBSR", "method"), ("Riverside Hall", "place"), ("2026-01-13", "date"), ("2026-03-03", "date"), ("home-practice CD", "tool")],
     [("MBSR", "Riverside Hall", "LOCATED_IN")],
     "when did the MBSR programme run and what part landed harder than expected",
     "MBSR eight week venue date range home practice CD undervalued"),
    # --- 48 ---
    ("Prefers the morning anxiety check on paper to the Daylio app for the 06:00 entry; the friction of opening the phone overrides the friction of writing.", "preference", "personal", False,
     [("paper", "tool"), ("Daylio", "tool"), ("06:00", "date"), ("phone", "tool")],
     [("paper", "Daylio", "PREFERS")],
     "which dawn check-in surface wins at six and why the friction matters",
     "paper over daylio dawn entry friction phone open writing tradeoff"),
    # --- 49 ---
    ("The retreat packing list is short: two sets of loose layers, sandals, ear plugs, a notebook, no books, no electronics, no scented soap.", "reference", "personal", False,
     [("retreat", "event"), ("loose layers", "concept"), ("sandals", "tool"), ("ear plugs", "tool"), ("notebook", "tool"), ("scented soap", "concept")],
     [],
     "what goes into the silent-retreat bag and what is explicitly left out",
     "monastic getaway luggage clothing footwear hearing protection writing pad bans gadget perfumed wash"),
    # --- 50 ---
    ("The breath-anchor cue on the lock screen reads \"long exhale\"; lasted three weeks before becoming wallpaper, replaced by a Rumi line on 2026-03-25.", "fact", "personal", False,
     [("lock screen", "tool"), ("long exhale", "concept"), ("Rumi", "person"), ("2026-03-25", "date")],
     [("Rumi", "long exhale", "REPLACES")],
     "what cue sits on the phone-lock and what took it over after habituation",
     "lock screen cue exhale wallpaper habituation rumi line replace date"),
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
