"""One-off emitter for classification top-up batch-012 — short_ambiguous mode, personal slice.

Each row is a standalone short personal sentence (3-12 words) that could plausibly
fit multiple memory_types; we pick the single best fit. Covers family, hobbies,
health, food, feelings, routines, purchases, goals, relationships, and travel.

Writes 100 rows to data/v2/classification/batch_012.tmp.jsonl with ids class-01101..01200.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_012.tmp.jsonl"
ID_OFFSET = 1100

# (text, domain, memory_type) — no pair_id
ROWS: list[tuple[str, str, str]] = [
    # --- fact (~14) ---
    ("My mom turns sixty next March.", "personal", "fact"),
    ("Our anniversary is on the tenth.", "personal", "fact"),
    ("The baby weighs eight pounds now.", "personal", "fact"),
    ("I'm allergic to shellfish.", "personal", "fact"),
    ("My blood type is O negative.", "personal", "fact"),
    ("The dog is nine years old.", "personal", "fact"),
    ("Rent is due on the first.", "personal", "fact"),
    ("My sister lives in Portland.", "personal", "fact"),
    ("I wear size ten shoes.", "personal", "fact"),
    ("The apartment has two bedrooms.", "personal", "fact"),
    ("My resting heart rate is sixty-two.", "personal", "fact"),
    ("We've been dating for four years.", "personal", "fact"),
    ("Dad's birthday is in September.", "personal", "fact"),
    ("The cat weighs twelve pounds.", "personal", "fact"),

    # --- decision (~14) ---
    ("I'm quitting coffee this month.", "personal", "decision"),
    ("We're moving in together in June.", "personal", "decision"),
    ("Going vegetarian starting Monday.", "personal", "decision"),
    ("I'll skip the family reunion this year.", "personal", "decision"),
    ("We're adopting from the shelter, not a breeder.", "personal", "decision"),
    ("I'm cutting alcohol for Lent.", "personal", "decision"),
    ("Booking the Iceland trip over Japan.", "personal", "decision"),
    ("I'm taking the job in Berlin.", "personal", "decision"),
    ("We'll send the kids to public school.", "personal", "decision"),
    ("I'm dropping the gym membership.", "personal", "decision"),
    ("Going with a small wedding, not a big one.", "personal", "decision"),
    ("I'll start therapy again next week.", "personal", "decision"),
    ("We're skipping Christmas travel this year.", "personal", "decision"),
    ("I'm keeping the old car another year.", "personal", "decision"),

    # --- preference (~14) ---
    ("I like mornings better than evenings.", "personal", "preference"),
    ("I prefer tea over coffee.", "personal", "preference"),
    ("I like window seats on flights.", "personal", "preference"),
    ("Prefer quiet dinners to loud parties.", "personal", "preference"),
    ("I like my steak medium rare.", "personal", "preference"),
    ("I prefer hiking to the gym.", "personal", "preference"),
    ("Rather read a book than watch TV.", "personal", "preference"),
    ("I like cats more than dogs.", "personal", "preference"),
    ("Prefer handwritten cards to texts.", "personal", "preference"),
    ("I like cold weather better than hot.", "personal", "preference"),
    ("I prefer cooking at home to eating out.", "personal", "preference"),
    ("Rather stay in on Fridays.", "personal", "preference"),
    ("I like darker roasts than lighter ones.", "personal", "preference"),
    ("Prefer board games to video games.", "personal", "preference"),

    # --- problem (~14) ---
    ("My back has been hurting again.", "personal", "problem"),
    ("Can't sleep past four most nights.", "personal", "problem"),
    ("The dog keeps throwing up after walks.", "personal", "problem"),
    ("My sister and I aren't speaking.", "personal", "problem"),
    ("I've been anxious all week.", "personal", "problem"),
    ("Grocery bills keep climbing.", "personal", "problem"),
    ("My knee swells after every run.", "personal", "problem"),
    ("The furnace is making a weird noise.", "personal", "problem"),
    ("I keep forgetting appointments.", "personal", "problem"),
    ("Our commute has become brutal.", "personal", "problem"),
    ("The kids fight every morning.", "personal", "problem"),
    ("I've been eating way too much sugar.", "personal", "problem"),
    ("My migraines are back.", "personal", "problem"),
    ("Savings are down this quarter.", "personal", "problem"),

    # --- reference (~14) ---
    ("Mom's recipe is in the blue notebook.", "personal", "reference"),
    ("Passport is in the top drawer.", "personal", "reference"),
    ("Insurance card is in my wallet.", "personal", "reference"),
    ("Grandma's letters are in the attic box.", "personal", "reference"),
    ("Wedding photos live on the old iMac.", "personal", "reference"),
    ("Lease copy is in the filing cabinet.", "personal", "reference"),
    ("Vet records are in the fridge folder.", "personal", "reference"),
    ("My therapist's number is on the fridge.", "personal", "reference"),
    ("Spare key is under the left planter.", "personal", "reference"),
    ("The will is at the lawyer's office.", "personal", "reference"),
    ("Tax returns live in the Google Drive folder.", "personal", "reference"),
    ("Dad's will is in his safety deposit box.", "personal", "reference"),
    ("Medical history is in the bedside binder.", "personal", "reference"),
    ("The cookbook lives on the middle shelf.", "personal", "reference"),

    # --- architecture (~14) ---
    ("Mornings are workouts, evenings are family time.", "personal", "architecture"),
    ("Weekdays I cook, weekends my partner does.", "personal", "architecture"),
    ("Mom handles finances, dad handles logistics.", "personal", "architecture"),
    ("We alternate kid pickup every other day.", "personal", "architecture"),
    ("Sundays are meal prep, Wednesdays are laundry.", "personal", "architecture"),
    ("I journal in the morning, read at night.", "personal", "architecture"),
    ("We split chores by room, not by task.", "personal", "architecture"),
    ("Therapy is biweekly, gym is three times a week.", "personal", "architecture"),
    ("Date nights rotate between us each week.", "personal", "architecture"),
    ("Groceries Monday, errands Thursday, rest Saturday.", "personal", "architecture"),
    ("Kids pick dinner once a week, parents the rest.", "personal", "architecture"),
    ("Holidays alternate between her family and mine.", "personal", "architecture"),
    ("Budget meetings happen the first Sunday each month.", "personal", "architecture"),
    ("Evenings split between chores and unwinding.", "personal", "architecture"),

    # --- milestone (~16 to reach 100) ---
    ("Finally ran my first full marathon.", "personal", "milestone"),
    ("Paid off the student loans last Friday.", "personal", "milestone"),
    ("Got engaged over the weekend.", "personal", "milestone"),
    ("Closed on the house yesterday.", "personal", "milestone"),
    ("The baby took her first steps today.", "personal", "milestone"),
    ("Celebrated ten years sober this week.", "personal", "milestone"),
    ("Finished the novel I started in 2020.", "personal", "milestone"),
    ("Hit my goal weight this morning.", "personal", "milestone"),
    ("Got my green card approved.", "personal", "milestone"),
    ("Grandma turned ninety last Sunday.", "personal", "milestone"),
    ("Kid graduated preschool on Friday.", "personal", "milestone"),
    ("We hit our emergency fund goal.", "personal", "milestone"),
    ("Took the dog on his first hike.", "personal", "milestone"),
    ("Reached a thousand days of journaling.", "personal", "milestone"),
    ("Survived the first year of parenthood.", "personal", "milestone"),
    ("Finally paid off the credit card.", "personal", "milestone"),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, domain, mt) in enumerate(ROWS, start=1):
            row_id = f"class-{ID_OFFSET + i:05d}"
            f.write(
                json.dumps(
                    {"id": row_id, "domain": domain, "text": text, "memory_type": mt},
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
