"""One-off emitter for shared-base batch-003 — personal domain.

Same pattern as _emit_shared_batch_002.py; only ENTRIES changes.
Appends 50 rows to data/v2/shared/shared.jsonl with ids shared-00101..00150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 100  # batches 001 + 002 consumed shared-00001..00100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. milestone: wedding ---
    ("Married Jamie in Kyoto on 2026-06-15 after seven years together.", "milestone", "personal", False,
     [("Jamie", "person"), ("Kyoto", "place"), ("2026-06-15", "date")],
     [],
     "when and where did the wedding with Jamie happen",
     "marriage ceremony Japan seven year relationship"),
    # --- 2. decision: summer destination ---
    ("Chose Barcelona over Lisbon for the summer trip; the food scene won us over.", "decision", "personal", False,
     [("Barcelona", "place"), ("Lisbon", "place")],
     [("Barcelona", "Lisbon", "PREFERS")],
     "which city did we pick for the summer holiday",
     "Iberian travel pick culinary reason"),
    # --- 3. preference: exercise ---
    ("Prefers morning runs along the riverfront over the gym.", "preference", "personal", False,
     [("morning runs", "activity"), ("gym", "activity"), ("riverfront", "place")],
     [("morning runs", "gym", "PREFERS")],
     "what workout does the user like most in the early hours",
     "outdoor jog riverside beats weight training"),
    # --- 4. problem: neighbor dispute ---
    ("Long-running parking feud with the upstairs neighbor Martin still isn't resolved.", "problem", "personal", False,
     [("Martin", "person")],
     [],
     "what unresolved dispute involves someone in the building",
     "garage space conflict upstairs unit unresolved"),
    # --- 5. reference: family recipe ---
    ("Mom's pho recipe lives in the green notebook on page 47.", "reference", "personal", False,
     [("pho", "food")],
     [],
     "where are the handwritten noodle soup instructions filed",
     "Vietnamese broth family cookbook location"),
    # --- 6. architecture: weekly routine ---
    ("Every Sunday evening, meal prep and journaling take the two hours before bedtime.", "architecture", "personal", False,
     [("meal prep", "activity"), ("journaling", "activity")],
     [],
     "what weekly rituals happen before bed at the week's end",
     "batch cooking plus reflection weekend wind-down"),
    # --- 7. fact: family date ---
    ("Dad's birthday falls on 1961-09-12; he turns 65 this year.", "fact", "personal", False,
     [("1961-09-12", "date")],
     [],
     "what date was Dad born",
     "father DOB 65th year reminder"),
    # --- 8. milestone: marathon ---
    ("Finished the Tokyo Marathon on 2026-03-01 after training for eight months.", "milestone", "personal", False,
     [("Tokyo Marathon", "event"), ("2026-03-01", "date")],
     [],
     "which race did we cross off after a long training block",
     "26.2 mile Japan early spring finish"),
    # --- 9. decision: language learning ---
    ("Signed up for Spanish lessons and dropped French; Mexico trips make Spanish more useful.", "decision", "personal", False,
     [("Spanish", "hobby"), ("French", "hobby"), ("Mexico", "place")],
     [("Spanish", "French", "REPLACES")],
     "which second language took over the learning slot this year",
     "language swap travel utility trip destination"),
    # --- 10. preference: drinks ---
    ("Oat milk in coffee, never dairy — switched after the reflux started.", "preference", "personal", False,
     [("Oat milk", "food"), ("coffee", "food"), ("dairy", "food")],
     [("Oat milk", "dairy", "REPLACES")],
     "what creamer goes into the morning brew now",
     "non-dairy swap stomach trigger reason"),
    # --- 11. problem: savings stall ---
    ("The goal of saving 15000 euros stalled when rent jumped again in January.", "problem", "personal", False,
     [("saving 15000 euros", "goal"), ("January", "date")],
     [],
     "why did the savings target slip this year",
     "housing hike shortfall Euro target delay"),
    # --- 12. reference: recipe source ---
    ("The chicken piccata recipe came from Bon Appétit magazine, November 2023 issue.", "reference", "personal", False,
     [("chicken piccata", "food"), ("Bon Appétit", "organization")],
     [],
     "where did the lemony chicken dish instructions originate",
     "food magazine issue late 2023 recipe origin"),
    # --- 13. architecture: budget review ---
    ("Sam and I review the 50/30/20 budget split on the first of every month.", "architecture", "personal", False,
     [("Sam", "person")],
     [],
     "what monthly money planning ritual is shared at home",
     "three-tier household expense review day"),
    # --- 14. fact: pet diet ---
    ("Our dog refuses every food except salmon and peanut butter.", "fact", "personal", False,
     [("salmon", "food"), ("peanut butter", "food")],
     [],
     "what two items will the pet actually eat",
     "picky canine menu approved proteins"),
    # --- 15. milestone: quit smoking ---
    ("Quit smoking cold turkey on 2025-01-01; fourteen months clean now.", "milestone", "personal", False,
     [("smoking", "activity"), ("2025-01-01", "date")],
     [],
     "when did the nicotine habit end",
     "cigarette cessation anniversary New Year start"),
    # --- 16. decision: relocation ---
    ("Moving to Berlin in April 2027 to be closer to Jamie's family after eight years in Amsterdam.", "decision", "personal", False,
     [("Berlin", "place"), ("April 2027", "date"), ("Jamie", "person"), ("Amsterdam", "place")],
     [("Berlin", "Amsterdam", "REPLACES")],
     "where are we relocating and why",
     "German capital move partner's relatives relocation"),
    # --- 17. preference: hangouts ---
    ("Quiet bookshop cafes always beat loud nightclub bars, even for catching up with friends.", "preference", "personal", False,
     [("bookshop cafes", "place"), ("nightclub bars", "place")],
     [("bookshop cafes", "nightclub bars", "PREFERS")],
     "what kind of hangout spot wins for meeting up",
     "calm literary hideout versus pulsing dance venue"),
    # --- 18. problem: family conflict ---
    ("The inheritance dispute with Rachel over Grandpa's cabin dragged into arbitration.", "problem", "personal", False,
     [("Rachel", "person"), ("cabin", "place")],
     [],
     "what family legal fight is now out of our hands",
     "sibling mountain property probate mediation"),
    # --- 19. reference: article ---
    ("The NYT piece on why we sleep less from 2025-11-14 changed how I think about caffeine.", "reference", "personal", False,
     [("NYT", "organization"), ("2025-11-14", "date")],
     [],
     "which published article reshaped my coffee habits",
     "Times feature nocturnal rest stimulant essay"),
    # --- 20. architecture: weekend shopping ---
    ("Weekly grocery run happens every Saturday morning at the farmers market with Maya.", "architecture", "personal", False,
     [("grocery run", "activity"), ("Saturday morning", "date"), ("farmers market", "place"), ("Maya", "person")],
     [],
     "what weekend food errand is locked on the calendar",
     "produce shopping outing friend weekly routine"),
    # --- 21. fact: family location ---
    ("Grandma Helena has lived alone in Lisbon since 2019.", "fact", "personal", False,
     [("Helena", "person"), ("Lisbon", "place"), ("2019", "date")],
     [("Helena", "Lisbon", "LIVES_IN")],
     "where has Grandma stayed for years",
     "matriarch Portuguese capital residency timeline"),
    # --- 22. milestone: debt paid ---
    ("Closed the last student loan account at BMO on 2026-02-28 after eleven years of chipping away.", "milestone", "personal", False,
     [("BMO", "organization"), ("2026-02-28", "date")],
     [],
     "when did the education debt finally finish",
     "long-running repayment closed bank date"),
    # --- 23. decision: class swap ---
    ("Dropped yoga in favour of reformer pilates; the core strength gains felt faster.", "decision", "personal", False,
     [("yoga", "hobby"), ("reformer pilates", "hobby")],
     [("reformer pilates", "yoga", "REPLACES")],
     "why did we swap our weekly class type",
     "mat practice to machine workout change reason"),
    # --- 24. preference: cuisine ---
    ("Thai curry wins over Indian curry nine times out of ten in this household.", "preference", "personal", False,
     [("Thai curry", "food"), ("Indian curry", "food")],
     [("Thai curry", "Indian curry", "PREFERS")],
     "which spicy cuisine usually beats the other at dinner",
     "Southeast Asian dish versus subcontinental pick"),
    # --- 25. problem: travel ---
    ("The Bali flight in June got cancelled; airline booked a replacement routing through Singapore.", "problem", "personal", False,
     [("Bali", "place"), ("June", "date"), ("Singapore", "place")],
     [],
     "what travel plan blew up and how did it get patched",
     "Indonesian holiday reroute layover itinerary"),
    # --- 26. reference: book framework ---
    ("The tidying approach I'm using comes from Marie Kondo's chapter on the life-changing magic.", "reference", "personal", False,
     [("Marie Kondo", "person")],
     [],
     "whose book guides the current decluttering effort",
     "KonMari author tidy framework chapter"),
    # --- 27. architecture: date night ---
    ("Every Friday is date night with Jamie, rotating between a new restaurant and a film.", "architecture", "personal", False,
     [("date night", "event"), ("Jamie", "person")],
     [],
     "what end-of-week ritual sticks with my partner",
     "Friday couple tradition dining cinema rotation"),
    # --- 28. fact: pet origin ---
    ("The dog came from the Kensington shelter on 2021-04-03.", "fact", "personal", False,
     [("Kensington shelter", "organization"), ("2021-04-03", "date")],
     [],
     "when and where did the family pet come home",
     "rescue centre adoption canine arrival day"),
    # --- 29. milestone: first 5k ---
    ("Ran my first 5k at the Cherry Blossom Run on 2026-04-05 in 28 minutes.", "milestone", "personal", False,
     [("Cherry Blossom Run", "event"), ("2026-04-05", "date")],
     [],
     "which short race did I complete under thirty minutes",
     "sakura springtime charity run debut finish"),
    # --- 30. decision: therapy ---
    ("Started couples therapy with Dr. Chen after Jake and I kept circling the same argument.", "decision", "personal", False,
     [("Dr. Chen", "person"), ("Jake", "person")],
     [],
     "what new professional support did we choose for the relationship",
     "pair counselling sessions recurring dispute fix"),
    # --- 31. preference: wine ---
    ("Red wine from the Rhône beats anything from Napa for the same money.", "preference", "personal", False,
     [("Rhône", "place"), ("Napa", "place")],
     [("Rhône", "Napa", "PREFERS")],
     "which wine region gives better value",
     "French valley versus Californian pick compare"),
    # --- 32. problem: health trigger ---
    ("Work stress kept triggering migraines; cut late-afternoon caffeine and they dropped by half.", "problem", "personal", False,
     [("stress", "emotion"), ("caffeine", "food")],
     [],
     "how did we reduce the recurring head pain",
     "office pressure headache trigger coffee cutoff"),
    # --- 33. reference: recommended read ---
    ("Anna recommended a book on the power of now last Christmas; finally finished it last week.", "reference", "personal", False,
     [("Anna", "person"), ("Christmas", "event")],
     [],
     "whose book recommendation did I just wrap up",
     "holiday gift friend endorsement done"),
    # --- 34. architecture: early morning ---
    ("Saturday mornings start with a 6am swim at the community pool before the kids are up.", "architecture", "personal", False,
     [("swim", "activity"), ("community pool", "place")],
     [],
     "what do early weekend hours look like before the family wakes",
     "dawn pool laps kid-free routine"),
    # --- 35. fact: pet allergy ---
    ("The cat is allergic to fish; she swells up after even a tiny bite of tuna.", "fact", "personal", False,
     [("fish", "food"), ("tuna", "food")],
     [],
     "what protein sets off the pet's allergy",
     "feline reaction seafood particular ingredient"),
    # --- 36. milestone: promotion ---
    ("Got promoted to senior engineering manager at Lumen on 2026-03-20, three years after joining.", "milestone", "personal", False,
     [("Lumen", "organization"), ("2026-03-20", "date")],
     [],
     "when did the step up to senior management happen",
     "career ladder title date employer tenure"),
    # --- 37. decision: training block ---
    ("This year's training focus builds on last year's strength base; switched to hypertrophy blocks.", "decision", "personal", False,
     [("hypertrophy blocks", "activity"), ("strength base", "activity")],
     [("hypertrophy blocks", "strength base", "BUILDS_ON")],
     "how is this year's gym plan evolving",
     "muscle growth phase foundational lift progression"),
    # --- 38. preference: reading ---
    ("Paper books in the evening, ebooks only for travel; screens wreck the wind-down.", "preference", "personal", False,
     [("Paper books", "hobby"), ("ebooks", "hobby")],
     [("Paper books", "ebooks", "PREFERS")],
     "how do I choose between print and digital reading",
     "bedtime print habit screen avoidance sleep"),
    # --- 39. problem: injury ---
    ("Skipped the gym for five weeks after the knee flare-up; rehab with Dr. Rosen starts Monday.", "problem", "personal", False,
     [("gym", "activity"), ("Dr. Rosen", "person")],
     [],
     "why have the workouts paused and when does recovery kick off",
     "joint injury break physiotherapy appointment scheduled"),
    # --- 40. reference: podcast ---
    ("The sleep protocol comes from Dr. Huberman's podcast episode on morning light exposure.", "reference", "personal", False,
     [("Dr. Huberman", "person")],
     [],
     "whose audio content informs the current sleep routine",
     "neuroscience podcast daylight episode hack"),
    # --- 41. architecture: meals ---
    ("Weeknight dinners are cooked fresh; only weekends lean on leftovers or takeout.", "architecture", "personal", False,
     [("Weeknight dinners", "activity"), ("leftovers", "food"), ("takeout", "food")],
     [],
     "how does the cooking schedule split between weekdays and weekends",
     "midweek fresh meals pantry shortcuts rhythm"),
    # --- 42. fact: anniversary ---
    ("Our wedding anniversary is 2019-07-04, which always clashes with the neighbor's fireworks party.", "fact", "personal", False,
     [("2019-07-04", "date")],
     [],
     "what date does the marriage celebration land on",
     "yearly couple marker summer holiday overlap"),
    # --- 43. milestone: sobriety ---
    ("Reached one year sober on 2026-04-07 after starting the program with Jess.", "milestone", "personal", False,
     [("2026-04-07", "date"), ("Jess", "person")],
     [],
     "when did the sobriety anniversary hit",
     "alcohol-free twelve months support friend"),
    # --- 44. noise ---
    ("Let me think about that for a minute before I answer.", "fact", "noise", True, [], [], None, None),
    # --- 45. decision: pilates format ---
    ("Picked the Reformer pilates class; it improves on the mat class's range of motion for my hip.", "decision", "personal", False,
     [("Reformer pilates class", "hobby"), ("mat class", "hobby")],
     [("Reformer pilates class", "mat class", "IMPROVES_ON")],
     "which pilates format works better for my hip",
     "spring machine variant beats floor routine"),
    # --- 46. preference: outdoor ---
    ("Prefers hiking in the Dolomites over camping in the Alps; day routes beat cold nights.", "preference", "personal", False,
     [("Dolomites", "place"), ("Alps", "place"), ("hiking", "hobby"), ("camping", "hobby")],
     [("hiking", "camping", "PREFERS")],
     "which mountain trip style wins for me",
     "Italian range day trek Swiss tent overnight"),
    # --- 47. problem: friendships ---
    ("Losing touch with the college crew after Priya moved to Singapore and Ben went freelance.", "problem", "personal", False,
     [("Priya", "person"), ("Singapore", "place"), ("Ben", "person")],
     [],
     "why are the old university friendships fading",
     "uni group drift overseas relocation freelance pivot"),
    # --- 48. reference: diet plan ---
    ("Cooking mostly follows the Whole30 program framework; day 14 is where cravings drop off.", "reference", "personal", False,
     [("Whole30", "organization")],
     [],
     "which diet plan shapes the kitchen right now",
     "clean-eating month challenge structured rules"),
    # --- 49. architecture: screen-free night ---
    ("Every Friday evening is phone-off time; we play board games with the kids until nine.", "architecture", "personal", False,
     [("Friday evening", "event"), ("board games", "activity")],
     [],
     "what screen-free family ritual closes the workweek",
     "parents offline tabletop night wind-down"),
    # --- 50. noise ---
    ("Hmm, I'm not sure what to make of that yet.", "fact", "noise", True, [], [], None, None),
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
