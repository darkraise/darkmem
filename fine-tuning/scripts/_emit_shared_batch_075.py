"""One-off emitter for shared-base batch-075 — personal domain (daily routines / time management slice).

Writes 50 rows to data/v2/shared/batch_075.tmp.jsonl with ids shared-03701..03750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_075.tmp.jsonl"
ID_OFFSET = 3700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The morning ritual starts at 05:40 with a glass of water, ten minutes of mobility, and the espresso pulled before any screen.", "architecture", "personal", False,
     [("morning ritual", "activity"), ("05:40", "date"), ("mobility", "activity"), ("espresso", "food")],
     [],
     "how is the wake-up sequence structured and what is off-limits until coffee",
     "morning ritual wake time water mobility espresso screen delay"),
    # --- 2 ---
    ("Switched from the Hobonichi Cousin to the Midori MD planner on 2026-01-04; the Cousin's thin paper was bleeding through fountain pen ink.", "decision", "personal", False,
     [("Hobonichi Cousin", "tool"), ("Midori MD planner", "tool"), ("2026-01-04", "date"), ("fountain pen", "tool")],
     [("Midori MD planner", "Hobonichi Cousin", "REPLACES")],
     "which paper planner took over at the year-change and why the swap",
     "planner change hobonichi to midori paper ghost fountain pen bleed date"),
    # --- 3 ---
    ("Prefers time-blocking the morning hours and keeping afternoons loose; the cognitive edge drops off after 13:00 and forced blocks just slip.", "preference", "personal", False,
     [("time-blocking", "method"), ("cognitive edge", "concept"), ("13:00", "date")],
     [],
     "which part of the day gets the scheduled blocks and which stays loose",
     "time block morning loose afternoon cognitive edge afternoon drop"),
    # --- 4 ---
    ("The Sunday weekly review runs from 19:00 to 20:00 at the kitchen table: inbox to zero, calendar scan two weeks out, three priorities picked for Monday.", "architecture", "personal", False,
     [("weekly review", "activity"), ("Sunday", "date"), ("kitchen table", "place"), ("inbox", "tool"), ("calendar", "tool")],
     [("weekly review", "kitchen table", "LOCATED_IN")],
     "how is the Sunday planning block structured and where is it held",
     "weekly review sunday evening kitchen inbox zero calendar scan priorities"),
    # --- 5 ---
    ("The evening wind-down at 21:30 kills all overhead lights and swaps to the salt lamp; phone goes into the kitchen drawer, never the bedroom.", "architecture", "personal", False,
     [("evening wind-down", "activity"), ("21:30", "date"), ("salt lamp", "tool"), ("phone", "tool"), ("kitchen drawer", "place")],
     [("phone", "kitchen drawer", "LOCATED_IN")],
     "how does the nightly shutdown routine actually look and where does the phone sleep",
     "wind down evening light swap salt lamp phone drawer no bedroom"),
    # --- 6 ---
    ("Moved the calendar from Google Calendar to Fantastical on 2026-02-15; the natural-language entry saves thirty seconds a pop and the widget is cleaner.", "decision", "personal", False,
     [("Google Calendar", "tool"), ("Fantastical", "tool"), ("2026-02-15", "date"), ("widget", "tool")],
     [("Fantastical", "Google Calendar", "REPLACES")],
     "which calendar app replaced the Google one and what specifically won",
     "calendar swap fantastical over google natural language widget speed"),
    # --- 7 ---
    ("The Pomodoro timer sits on the desk as a physical cube from Ticktime; the phone app was always hijacked by a notification mid-block.", "decision", "personal", False,
     [("Pomodoro timer", "tool"), ("Ticktime", "tool"), ("desk", "place"), ("phone app", "tool")],
     [("Ticktime", "phone app", "REPLACES")],
     "which focus timer took over from the app and why",
     "pomodoro hardware cube ticktime over phone app notification hijack"),
    # --- 8 ---
    ("Prefers the 90/20 ultradian block over the classic 25/5 Pomodoro; the 25-minute cut interrupts deep flow just as it lands.", "preference", "personal", False,
     [("ultradian block", "method"), ("Pomodoro", "method"), ("deep flow", "concept")],
     [("ultradian block", "Pomodoro", "PREFERS")],
     "which focus-cadence wins and what is wrong with the shorter one",
     "ultradian 90 20 over pomodoro 25 5 deep flow cut reason"),
    # --- 9 ---
    ("The commute routine on the 07:42 train is phone-free: a paper book in one hand, coffee in the other, no headphones till the return leg.", "architecture", "personal", False,
     [("commute routine", "activity"), ("07:42 train", "infrastructure"), ("paper book", "tool"), ("coffee", "food"), ("headphones", "tool")],
     [],
     "how is the morning rail trip structured and what stays forbidden until the ride home",
     "rail ride morning no device paperback caffeine music ban outbound leg"),
    # --- 10. noise ---
    ("Hold on, let me check the clock.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Lunch is a fixed 30-minute walk-and-eat from 12:15 to 12:45; desk eating got ditched after December 2025 when the afternoon slumps were tracked to it.", "decision", "personal", False,
     [("Lunch", "activity"), ("walk-and-eat", "method"), ("December 2025", "date"), ("desk eating", "activity"), ("afternoon slumps", "concept")],
     [("walk-and-eat", "desk eating", "REPLACES")],
     "which lunch pattern replaced the old one and what data forced the change",
     "lunch walk eat over desk afternoon slump tracked correlation date"),
    # --- 12 ---
    ("Saturday is the batch-cooking day: two hours at the stove from 10:00, five portions of the week's lunch into glass containers in the fridge.", "architecture", "personal", False,
     [("Saturday", "date"), ("batch-cooking", "activity"), ("stove", "tool"), ("glass containers", "tool"), ("fridge", "tool")],
     [],
     "how does the weekend meal-prep block work and what does it produce",
     "batch cooking saturday two hour stove portions containers fridge"),
    # --- 13 ---
    ("Errands are consolidated onto Tuesday evenings: post office, bank drop, hardware store, one 45-minute loop from the flat.", "architecture", "personal", False,
     [("Errands", "activity"), ("Tuesday", "date"), ("post office", "place"), ("bank", "organization"), ("hardware store", "place"), ("flat", "place")],
     [],
     "which weekday holds the bundled errand run and what is the circuit",
     "weekly task bundle midweek night loop mail financial DIY store route"),
    # --- 14 ---
    ("Took up the Bullet Journal method in earnest on 2026-03-01 after two failed starts; the migration step is the keystone I kept skipping.", "milestone", "personal", False,
     [("Bullet Journal", "method"), ("2026-03-01", "date"), ("migration step", "concept")],
     [],
     "when did the bullet-journal practice finally take and what was I missing",
     "bullet journal start date migration step keystone failed attempts"),
    # --- 15 ---
    ("Prefers the ink-and-paper shutdown ritual to the digital end-of-day review; writing tomorrow's three MITs by hand commits them in a way typing never did.", "preference", "personal", False,
     [("shutdown ritual", "activity"), ("digital end-of-day review", "method"), ("MITs", "concept")],
     [("shutdown ritual", "digital end-of-day review", "PREFERS")],
     "which end-of-workday closure wins and what is it about handwriting that sticks",
     "shutdown ritual paper over digital MIT three handwriting commit"),
    # --- 16 ---
    ("The morning pages habit locked in after 63 consecutive days; three A4 sides at the kitchen table, long-hand, before looking at any feed.", "milestone", "personal", False,
     [("morning pages", "activity"), ("A4", "concept"), ("kitchen table", "place")],
     [("morning pages", "kitchen table", "LOCATED_IN")],
     "when did the freewriting habit finally feel automatic and what is the format",
     "morning pages streak sixty three three pages long hand pre feed"),
    # --- 17 ---
    ("Chose the Filofax Personal size over the A5 on 2025-12-10; the A5 lived on the desk, the Personal actually fit the jacket pocket and came with me.", "decision", "personal", False,
     [("Filofax Personal", "tool"), ("A5", "concept"), ("2025-12-10", "date"), ("jacket pocket", "place")],
     [("Filofax Personal", "A5", "REPLACES")],
     "which planner size took over and why the bigger one lost",
     "filofax personal over A5 jacket pocket portability desk captive date"),
    # --- 18 ---
    ("The Sunday chore cadence is strict: laundry before 10:00, ironing during the podcast slot at 11:00, floors last because the dust always comes up.", "architecture", "personal", False,
     [("Sunday", "date"), ("chore cadence", "method"), ("laundry", "activity"), ("ironing", "activity"), ("podcast", "tool"), ("floors", "place")],
     [],
     "how are the weekend household chores ordered and why floors last",
     "sunday chore order laundry ironing podcast floors dust reason"),
    # --- 19 ---
    ("Prefers a single deep-focus block from 09:00 to 11:30 over splitting it into three shorter ones; context-switching was eating twenty percent of the morning.", "preference", "personal", False,
     [("deep-focus block", "method"), ("09:00", "date"), ("11:30", "date"), ("context-switching", "concept")],
     [],
     "which morning-focus layout wins and what is the hidden tax on splitting",
     "single deep focus block over split three context switch cost"),
    # --- 20 ---
    ("The 21:00 reading hour in the armchair is sacred: no phone, paperback only, a chamomile tea, lights dimmed to the warm setting.", "architecture", "personal", False,
     [("reading hour", "activity"), ("21:00", "date"), ("armchair", "place"), ("paperback", "tool"), ("chamomile tea", "food")],
     [("reading hour", "armchair", "LOCATED_IN")],
     "how does the nightly reading block look and what does it exclude",
     "reading hour armchair paperback chamomile dim light no phone nine pm"),
    # --- 21 ---
    ("Abandoned Getting Things Done in favour of a plain Kanban with three columns on 2026-02-20; the GTD context lists were overhead I never paid off.", "decision", "personal", False,
     [("Getting Things Done", "method"), ("Kanban", "method"), ("2026-02-20", "date"), ("context lists", "concept")],
     [("Kanban", "Getting Things Done", "REPLACES")],
     "which personal productivity system replaced GTD and what specifically felt heavy",
     "GTD dropped kanban three column context list overhead date swap"),
    # --- 22 ---
    ("The monthly review sits on the first Saturday of the month at Amelie's Cafe; an hour with the planner, a flat white, and a pastry, no laptop.", "architecture", "personal", False,
     [("monthly review", "activity"), ("Saturday", "date"), ("Amelie's Cafe", "place"), ("flat white", "food"), ("pastry", "food")],
     [("monthly review", "Amelie's Cafe", "LOCATED_IN")],
     "how does the monthly retrospective run and what is the setting",
     "monthly review first saturday cafe flat white pastry no laptop hour"),
    # --- 23 ---
    ("Prefers the Lamy Safari with the F nib for the daily planner over the fountain pen sampler; one pen, always inked, no decision fatigue at the start of the day.", "preference", "personal", False,
     [("Lamy Safari", "tool"), ("F nib", "concept"), ("daily planner", "tool"), ("fountain pen sampler", "tool"), ("decision fatigue", "concept")],
     [("Lamy Safari", "fountain pen sampler", "PREFERS")],
     "which writing tool wins for the daily planner and what problem does it kill",
     "lamy safari F over pen sampler one pen decision fatigue start day"),
    # --- 24 ---
    ("The commute train on 2026-03-18 was cancelled at Worthing Junction; added a standing rule to leave 12 minutes earlier on Mondays after quarter-end.", "problem", "personal", False,
     [("commute train", "infrastructure"), ("2026-03-18", "date"), ("Worthing Junction", "place"), ("Mondays", "date")],
     [],
     "what commute failure prompted the earlier Monday rule and when",
     "train cancel worthing junction monday buffer rule quarter end date"),
    # --- 25 ---
    ("Replaced the smartphone alarm with a Lumie sunrise lamp on 2026-01-20; the gradient wake feels civilised and the phone stays out of the bedroom.", "decision", "personal", False,
     [("smartphone alarm", "tool"), ("Lumie sunrise lamp", "tool"), ("2026-01-20", "date"), ("bedroom", "place")],
     [("Lumie sunrise lamp", "smartphone alarm", "REPLACES")],
     "which wake-up device took over and what bedroom rule follows from it",
     "sunrise lamp lumie over phone alarm bedroom free gradient date"),
    # --- 26 ---
    ("The habit tracker lives on a laminated index card in the kitchen; six rows, thirty-one columns, a dry-erase marker clipped to the fridge magnet.", "reference", "personal", False,
     [("habit tracker", "tool"), ("index card", "tool"), ("kitchen", "place"), ("dry-erase marker", "tool"), ("fridge magnet", "tool")],
     [("habit tracker", "kitchen", "LOCATED_IN")],
     "where does the habit grid live and what is the format",
     "habit tracker index card laminated six rows thirty one columns kitchen"),
    # --- 27 ---
    ("Chose to consolidate errands by neighbourhood rather than by day of week; the Highcliffe loop and the Town Centre loop are my two geographic buckets.", "decision", "personal", False,
     [("errands", "activity"), ("Highcliffe", "place"), ("Town Centre", "place")],
     [],
     "how did the errand-bundling strategy shift and what are the two routes",
     "errand consolidation by neighbourhood over weekday highcliffe town centre loops"),
    # --- 28 ---
    ("The Friday afternoon energy slump is handled with a 20-minute walk around Beaulieu Gardens at 15:00; always the same loop, always alone.", "architecture", "personal", False,
     [("Friday", "date"), ("energy slump", "concept"), ("Beaulieu Gardens", "place"), ("15:00", "date")],
     [("energy slump", "Beaulieu Gardens", "RELATED_TO")],
     "how does the Friday afternoon dip get handled and where does the walk go",
     "friday slump walk fix beaulieu gardens fifteen hundred same loop alone"),
    # --- 29 ---
    ("Prefers written to-do lists in the planner over a digital task app; the act of crossing out in pen is a dopamine hit the tick in Todoist never matched.", "preference", "personal", False,
     [("to-do lists", "tool"), ("planner", "tool"), ("task app", "tool"), ("Todoist", "tool")],
     [("to-do lists", "Todoist", "PREFERS")],
     "which task-capture medium wins and what is the psychological pull",
     "paper to do over todoist crossing out pen dopamine tick comparison"),
    # --- 30 ---
    ("The time-blocking experiment of themed days failed within three weeks in February 2026; Deep Work Monday collapsed the first time a plumber called.", "problem", "personal", False,
     [("time-blocking", "method"), ("themed days", "method"), ("February 2026", "date"), ("Deep Work Monday", "concept"), ("plumber", "person")],
     [],
     "what time-management experiment fell apart and what was the breaking point",
     "themed days failure deep work monday plumber interrupt three weeks date"),
    # --- 31 ---
    ("The pre-sleep checklist on the nightstand runs four items: water glass filled, alarm off (lamp on), planner tomorrow open, book on the armchair.", "reference", "personal", False,
     [("pre-sleep checklist", "tool"), ("nightstand", "place"), ("water glass", "tool"), ("alarm", "tool"), ("lamp", "tool"), ("planner", "tool")],
     [("pre-sleep checklist", "nightstand", "LOCATED_IN")],
     "what does the bedtime checklist cover and where does it live",
     "pre sleep checklist nightstand water alarm lamp planner book four items"),
    # --- 32 ---
    ("Replaced the 06:30 gym slot with a 06:00 walk on 2026-03-10; the shower-at-home flow saves 25 minutes and the heart rate data is still in zone two.", "decision", "personal", False,
     [("gym slot", "activity"), ("06:30", "date"), ("walk", "activity"), ("06:00", "date"), ("2026-03-10", "date"), ("zone two", "concept")],
     [("walk", "gym slot", "REPLACES")],
     "which morning-movement choice took over and what is the time saving",
     "gym swap morning walk shower home time save zone two heart rate date"),
    # --- 33 ---
    ("Prefers the MIT approach (Most Important Tasks, three daily) over a long-tail to-do list; the list gets smeared, the three get done.", "preference", "personal", False,
     [("MIT approach", "method"), ("to-do list", "tool")],
     [("MIT approach", "to-do list", "PREFERS")],
     "which personal task-selection method wins out and what is the failure mode of the other",
     "MIT three over long to do list smear done comparison"),
    # --- 34. noise ---
    ("Give me a second to flip the page.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Wednesday mid-week reset at 20:00 is a shorter review: re-read Sunday's three priorities, move what slipped, pick the Thursday MIT.", "architecture", "personal", False,
     [("Wednesday", "date"), ("mid-week reset", "activity"), ("20:00", "date"), ("Sunday", "date"), ("Thursday", "date")],
     [],
     "how does the midweek checkpoint work and what does it carry forward",
     "wednesday reset evening reread sunday priorities slip thursday MIT"),
    # --- 36 ---
    ("The shared Cozi family calendar was kept only for the kids; my own weekly planning stays on paper to avoid the notification spiral.", "decision", "personal", False,
     [("Cozi", "tool"), ("family calendar", "tool"), ("paper", "tool"), ("notification spiral", "concept")],
     [("paper", "Cozi", "PREFERS")],
     "which calendar split did I settle on and what am I avoiding",
     "cozi family kids paper personal planning notification spiral split"),
    # --- 37 ---
    ("Prefers the Eisenhower box drawn by hand in the planner over the app version; the manual act of placing a task forces the classification.", "preference", "personal", False,
     [("Eisenhower box", "method"), ("planner", "tool"), ("app version", "tool")],
     [("Eisenhower box", "app version", "PREFERS")],
     "which prioritisation grid wins and what does handwriting it add",
     "eisenhower box hand drawn over app classify force manual reason"),
    # --- 38 ---
    ("The no-meeting Thursday rule has held since 2025-10-01 for personal appointments; dentist, optician, barber all get moved to Friday or Tuesday.", "fact", "personal", False,
     [("no-meeting Thursday", "method"), ("2025-10-01", "date"), ("dentist", "person"), ("optician", "person"), ("barber", "person")],
     [],
     "which day stays appointment-free and since when has the rule held",
     "no meeting thursday personal appointments moved rule holding since date"),
    # --- 39 ---
    ("The Sunday-evening meal plan is written on a chalkboard in the pantry; seven dinners listed, flexible within the row, never changed after shopping.", "reference", "personal", False,
     [("meal plan", "tool"), ("Sunday", "date"), ("chalkboard", "tool"), ("pantry", "place"), ("shopping", "activity")],
     [("chalkboard", "pantry", "LOCATED_IN")],
     "where does the weekly dinner plan get posted and what is the flex rule",
     "meal plan chalkboard pantry seven dinners flexible post shopping locked"),
    # --- 40 ---
    ("Replaced the 22:00 news scroll with a 15-minute crossword on 2026-02-08; the sleep latency on the Oura ring dropped by nine minutes within a fortnight.", "decision", "personal", False,
     [("news scroll", "activity"), ("crossword", "activity"), ("2026-02-08", "date"), ("sleep latency", "finding"), ("Oura ring", "tool")],
     [("crossword", "news scroll", "REPLACES")],
     "which pre-bed swap took place and what did the ring actually measure",
     "news scroll swap crossword pre bed oura sleep latency drop date"),
    # --- 41 ---
    ("The morning journal prompt lives on the inside cover of the planner: one sentence on yesterday, one intention for today, one gratitude, no fourth line.", "reference", "personal", False,
     [("morning journal", "activity"), ("planner", "tool"), ("intention", "concept"), ("gratitude", "emotion")],
     [("morning journal", "planner", "LOCATED_IN")],
     "what is the exact format of the morning writing prompt and where is it written",
     "morning journal three line yesterday intention gratitude no fourth planner cover"),
    # --- 42 ---
    ("Prefers the 52/17 rule for desk work over strict hours-on-hours-off; the DeskTime study matched what I had drifted into already.", "preference", "personal", False,
     [("52/17 rule", "method"), ("DeskTime", "publication")],
     [("52/17 rule", "DeskTime", "BUILDS_ON")],
     "which work-rest cadence wins and what outside source backed the intuition",
     "fifty two seventeen rule over hours on off desktime study match"),
    # --- 43 ---
    ("The Friday evening shutdown at 17:30 closes every browser tab, writes next week's three priorities, and sets a physical closed card on the desk.", "architecture", "personal", False,
     [("Friday", "date"), ("shutdown", "activity"), ("17:30", "date"), ("browser tab", "tool"), ("closed card", "tool")],
     [],
     "how does the week-closure ritual run and what sits on the desk afterwards",
     "friday shutdown evening close tabs next week three priorities closed card"),
    # --- 44 ---
    ("The weekend always includes a long walk on Sunday morning, 90 minutes along Hengistbury Head, alone, no podcast, just an OS map in the pocket.", "architecture", "personal", False,
     [("long walk", "activity"), ("Sunday", "date"), ("Hengistbury Head", "place"), ("podcast", "tool"), ("OS map", "tool")],
     [("long walk", "Hengistbury Head", "LOCATED_IN")],
     "how does the Sunday walk look and what is banned from the experience",
     "long walk sunday morning ninety minutes hengistbury head no podcast map"),
    # --- 45 ---
    ("The 08:15 school-run handoff happens at the front door with a thirty-second checklist: bag, lunch, water, coat, shoes; missed the coat once, never again.", "problem", "personal", False,
     [("school-run", "activity"), ("08:15", "date"), ("front door", "place"), ("checklist", "tool"), ("coat", "tool")],
     [("checklist", "front door", "LOCATED_IN")],
     "what morning-handover failure created the door checklist and what is on it",
     "school run handoff front door checklist bag lunch water coat shoes"),
    # --- 46 ---
    ("Took up the Autofocus single-list method on 2026-03-22; the long list with a moving cursor works better than the MIT trio on light-load days.", "milestone", "personal", False,
     [("Autofocus", "method"), ("single-list", "concept"), ("2026-03-22", "date"), ("MIT trio", "method")],
     [("Autofocus", "MIT trio", "REPLACES")],
     "when did the Autofocus list take over on quieter days and from what",
     "autofocus single list over MIT trio light load days date"),
    # --- 47 ---
    ("Prefers a 72-hour horizon on the calendar over week-at-a-glance for morning planning; anything past three days is a planning problem, not a scheduling one.", "preference", "personal", False,
     [("72-hour horizon", "concept"), ("calendar", "tool"), ("week-at-a-glance", "concept")],
     [("72-hour horizon", "week-at-a-glance", "PREFERS")],
     "which calendar-window wins for daily planning and why the longer view loses",
     "72 hour over week at glance planning scheduling distinction reason"),
    # --- 48 ---
    ("The commute-home routine at 17:55 is the decompression switch: headphones on, instrumental only, one stop walked from Preston Park instead of Brighton.", "architecture", "personal", False,
     [("commute-home routine", "activity"), ("17:55", "date"), ("headphones", "tool"), ("Preston Park", "place"), ("Brighton", "place")],
     [("commute-home routine", "Preston Park", "LOCATED_IN")],
     "how does the evening trip home reset the day and where does the walk start",
     "commute home headphones instrumental preston park over brighton walk"),
    # --- 49 ---
    ("The 2026-01-05 experiment with 04:45 wakes lasted eleven days before collapsing; sleep debt compounded faster than the extra morning time gained.", "problem", "personal", False,
     [("04:45", "date"), ("wakes", "activity"), ("2026-01-05", "date"), ("sleep debt", "concept")],
     [],
     "when did the ultra-early rise experiment fall apart and what went wrong",
     "early wake experiment forty five am collapse eleven days sleep debt date"),
    # --- 50 ---
    ("The daily shutdown phrase is literally said aloud — 'schedule shutdown, complete' — a trick lifted from Deep Work that actually killed the after-hours spiral.", "fact", "personal", False,
     [("shutdown phrase", "method"), ("Deep Work", "publication"), ("after-hours spiral", "concept")],
     [("shutdown phrase", "Deep Work", "BUILDS_ON")],
     "what verbal closure ends the workday and where did the trick come from",
     "shutdown complete spoken phrase deep work after hours spiral kill"),
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
