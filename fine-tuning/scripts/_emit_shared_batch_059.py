"""One-off emitter for shared-base batch-059 — personal domain (friendships and social life slice).

Writes 50 rows to data/v2/shared/batch_059.tmp.jsonl with ids shared-02901..02950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_059.tmp.jsonl"
ID_OFFSET = 2900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Thursday pub crew at The Anvil settled into a rhythm of arriving by 19:30 and ordering food before 20:00 after Sam complained the kitchen kept closing on us.", "architecture", "personal", False,
     [("The Anvil", "place"), ("Thursday", "date"), ("Sam", "person"), ("kitchen", "place")],
     [("Thursday", "The Anvil", "LOCATED_IN")],
     "how does the weekly drinks gathering at our local now run after the food complaint",
     "thursday pub crew arrival order time kitchen close fix routine"),
    # --- 2 ---
    ("Reconnected with Imogen on 2026-02-17 after eight years; she found me through the alumni list and we walked five miles around Hampstead Heath catching up.", "milestone", "personal", False,
     [("Imogen", "person"), ("2026-02-17", "date"), ("alumni list", "tool"), ("Hampstead Heath", "place")],
     [("Imogen", "Hampstead Heath", "VISITED")],
     "when did the long-lost school friend get back in touch and what did we do",
     "reconnect old friend years gap alumni walk park heath catchup date"),
    # --- 3 ---
    ("Hosted Nadia's 35th birthday on 2026-03-22 at the flat: 14 guests, three lasagnas, the lemon-drizzle cake from Violet Bakery, no speeches by request.", "milestone", "personal", False,
     [("Nadia", "person"), ("2026-03-22", "date"), ("flat", "place"), ("lemon-drizzle cake", "food"), ("Violet Bakery", "organization")],
     [("Nadia", "flat", "VISITED")],
     "when was the milestone birthday I threw and what was the menu shape",
     "birthday party 35 host flat guest count lasagna cake source no speech"),
    # --- 4 ---
    ("Prefers small board-game nights of four to the eight-player Catan blowouts; quieter table, faster turns, and Dani actually finishes a game with us.", "preference", "personal", False,
     [("board-game nights", "event"), ("Catan", "concept"), ("Dani", "person")],
     [("board-game nights", "Catan", "PREFERS")],
     "which size of tabletop evening wins out and what makes it work",
     "board game night small group over big catan turn pace finish"),
    # --- 5 ---
    ("Replaced the single huge group chat with three smaller threads on 2026-01-28 — close five, hiking crew, and uni reunion — message volume halved within a week.", "decision", "personal", False,
     [("group chat", "tool"), ("close five", "concept"), ("hiking crew", "concept"), ("uni reunion", "event"), ("2026-01-28", "date")],
     [("close five", "group chat", "REPLACES")],
     "which messaging structure took over from the one big thread and what shifted",
     "group chat split into smaller threads volume drop date close hiking uni"),
    # --- 6 ---
    ("The Sunday brunch standing booking at Café Lila is for six at 11:00; Theo holds the table when one of us runs late on the Northern line.", "reference", "personal", False,
     [("Sunday", "date"), ("Café Lila", "place"), ("Theo", "person"), ("Northern line", "infrastructure")],
     [("Sunday", "Café Lila", "LOCATED_IN")],
     "where and when is the weekly friend brunch held and who covers for late arrivals",
     "sunday brunch standing booking party size cafe friend cover tube line"),
    # --- 7 ---
    ("The friendship with Marcus ended on 2026-02-09 after the loan he never repaid and the cancelled wedding RSVP; deleted the contact and unfollowed quietly.", "milestone", "personal", False,
     [("Marcus", "person"), ("2026-02-09", "date"), ("loan", "concept"), ("wedding RSVP", "event")],
     [],
     "when did the long friendship break up and what triggered the final cut",
     "friendship breakup date loan unpaid wedding rsvp delete contact unfollow"),
    # --- 8 ---
    ("The board-game shelf rotation for friend nights is set: heavy euros for the Tuesday four, party games for Saturday eight, and Wingspan stays out for newcomers.", "architecture", "personal", False,
     [("board-game shelf", "infrastructure"), ("Tuesday", "date"), ("Saturday", "date"), ("Wingspan", "concept"), ("newcomers", "person")],
     [],
     "how is the games collection organised by the night and the crowd that comes",
     "board game shelf rotation heavy euro party game wingspan default new"),
    # --- 9 ---
    ("Prefers the Anvil quiet bar over the Crown's main room for catch-ups; you can hear what Lena is saying without leaning across pint glasses.", "preference", "personal", False,
     [("Anvil quiet bar", "place"), ("Crown", "place"), ("Lena", "person")],
     [("Anvil quiet bar", "Crown", "PREFERS")],
     "which pub setting wins out for proper conversation and why",
     "pub quiet back bar over crowded main room catchup hear voice across"),
    # --- 10. noise ---
    ("Hold on, I think I left my coat back at the table.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The uni reunion at Magdalen on 2026-06-20 is locked in: 42 RSVPs, two pints in the cloister, dinner in the old library, no dress code beyond 'jacket if you have one'.", "milestone", "personal", False,
     [("uni reunion", "event"), ("Magdalen", "place"), ("2026-06-20", "date"), ("cloister", "place"), ("old library", "place")],
     [("uni reunion", "Magdalen", "LOCATED_IN")],
     "when is the college get-together happening and how is the evening shaped",
     "uni reunion college date rsvp count pints cloister dinner library dress"),
    # --- 12 ---
    ("The neighbour at flat 4B, Iris, shares the parcel-collection arrangement; she takes mine on Tuesdays and Thursdays and I take hers on weekends.", "architecture", "personal", False,
     [("flat 4B", "place"), ("Iris", "person"), ("Tuesdays", "date"), ("Thursdays", "date"), ("weekends", "date")],
     [("Iris", "flat 4B", "LIVES_IN")],
     "how is the parcel-swap with the across-the-hall neighbour split through the week",
     "neighbour flat parcel swap weekday split weekend coverage arrangement"),
    # --- 13 ---
    ("The dinner-party rota among the four households resets each January; we host February and June, the Bhattacharyas host April and October, and so on.", "architecture", "personal", False,
     [("dinner-party rota", "event"), ("January", "date"), ("February", "date"), ("June", "date"), ("Bhattacharyas", "person")],
     [],
     "how do the four-couple dinner nights cycle through the year",
     "dinner party rota four households month assignment yearly reset cycle"),
    # --- 14 ---
    ("Awkwardly bumped into ex-flatmate Caleb at the Whitechapel gallery opening on 2026-03-15; we managed eight minutes of small talk before both pretending to need the bar.", "problem", "personal", False,
     [("Caleb", "person"), ("Whitechapel gallery", "place"), ("2026-03-15", "date"), ("bar", "place")],
     [("Caleb", "Whitechapel gallery", "VISITED")],
     "when did the cringe ex-housemate run-in happen and how did we both escape it",
     "awkward run in ex flatmate gallery opening small talk bar exit date"),
    # --- 15 ---
    ("Switched the friend-group calendar from a shared Google Calendar to a Notion board on 2026-02-12; the calendar got cluttered with declined events and nobody could find anything.", "decision", "personal", False,
     [("Google Calendar", "tool"), ("Notion", "tool"), ("2026-02-12", "date"), ("friend-group calendar", "concept")],
     [("Notion", "Google Calendar", "REPLACES")],
     "which planning tool took over for the social schedule and what was wrong with the old one",
     "social calendar swap google to notion clutter declined event find date"),
    # --- 16 ---
    ("Theo's stag weekend lands 2026-05-09 to 2026-05-11 in Lisbon: nine of us, one Airbnb in Alfama, no strippers, mandatory pastel de nata stop on Saturday morning.", "milestone", "personal", False,
     [("Theo", "person"), ("2026-05-09", "date"), ("2026-05-11", "date"), ("Lisbon", "place"), ("Alfama", "place"), ("pastel de nata", "food")],
     [("Theo", "Lisbon", "VISITED")],
     "when is the stag trip booked and how is it shaped on the ground",
     "stag weekend lisbon date range airbnb neighbourhood headcount no stripper food"),
    # --- 17 ---
    ("Prefers planning friend dinners three weeks out to the day-of texting model that worked in our twenties; nobody under 35 has a free Saturday on short notice.", "preference", "personal", False,
     [("friend dinners", "event"), ("day-of texting", "method"), ("twenties", "date")],
     [("friend dinners", "day-of texting", "PREFERS")],
     "which scheduling lead-time wins out for grown-up social plans and why",
     "friend dinner planning weeks ahead over same day text age availability"),
    # --- 18 ---
    ("The board-game night injury count for 2025 sat at three: a sprained finger from Codenames buzzer-slam, two paper cuts, no actual flipping of tables.", "fact", "personal", False,
     [("board-game night", "event"), ("2025", "date"), ("Codenames", "concept"), ("paper cuts", "concept")],
     [],
     "how many minor injuries did the games evenings produce last year",
     "board game night injury tally year codenames buzzer cuts table flip"),
    # --- 19 ---
    ("Reconnected with the secondary-school WhatsApp group of 28 on 2026-01-14 after Hannah dug up the old roster; six of us actually turned up to the pub four weeks later.", "milestone", "personal", False,
     [("WhatsApp group", "tool"), ("2026-01-14", "date"), ("Hannah", "person"), ("pub", "place")],
     [],
     "when did the school-year chat fire back up and how many made it to the meet",
     "school whatsapp group reconnect roster dig pub turnout count weeks"),
    # --- 20 ---
    ("The dinner party seating rule we settled on after the 2025 Christmas disaster: never put Anya next to Felix, never let Karim sit at the head of the table.", "reference", "personal", False,
     [("dinner party", "event"), ("Christmas", "event"), ("Anya", "person"), ("Felix", "person"), ("Karim", "person")],
     [],
     "what are the seating ground rules we keep at our hosted meals",
     "dinner party seating rule names separate not at head table christmas"),
    # --- 21 ---
    ("Chose the Tuesday board-game night at Draughts Hackney over the weekend slots; weeknights get the regulars and the staff actually teach the harder games.", "decision", "personal", False,
     [("Tuesday", "date"), ("Draughts Hackney", "place"), ("weekend", "date"), ("staff", "person")],
     [("Tuesday", "weekend", "PREFERS")],
     "which evening at the games cafe wins for serious play and why",
     "board game cafe weeknight over weekend regulars staff teach hard"),
    # --- 22 ---
    ("The neighbour two doors down, Mr Akadiri, taught me the chequer-pattern lawn-mowing trick over a beer on 2026-04-02; he has been doing his stripes for 31 years.", "fact", "personal", False,
     [("Mr Akadiri", "person"), ("chequer-pattern", "method"), ("lawn-mowing", "activity"), ("2026-04-02", "date")],
     [("Mr Akadiri", "chequer-pattern", "KNOWS")],
     "when did the across-the-way neighbour pass on the lawn-stripe technique",
     "neighbour two doors lawn chequer pattern mow beer date veteran years"),
    # --- 23 ---
    ("The chat group called 'Sunday Roasts' is the only one I read in real time; the rest get triaged once a day at 19:00 over tea.", "preference", "personal", False,
     [("Sunday Roasts", "tool"), ("tea", "food")],
     [],
     "which messaging thread gets live attention and how do I handle the rest",
     "chat group real time read others triage once daily evening tea"),
    # --- 24 ---
    ("Threw the surprise party for Priya's 40th on 2026-04-12 at the Lordship Lane wine bar; 28 turned up, the band overran by 40 minutes, the bar comped a round.", "milestone", "personal", False,
     [("Priya", "person"), ("2026-04-12", "date"), ("Lordship Lane wine bar", "place"), ("band", "person")],
     [("Priya", "Lordship Lane wine bar", "VISITED")],
     "when did the surprise 40th go down and how did the night pan out",
     "surprise birthday 40 wine bar guest count band overrun comp round"),
    # --- 25 ---
    ("The dinner-party menu format I keep returning to is one shared starter, one big roast, three small sides, one cheese plate, no pre-dessert.", "architecture", "personal", False,
     [("dinner-party", "event"), ("starter", "food"), ("roast", "food"), ("sides", "food"), ("cheese plate", "food")],
     [],
     "what shape do my hosted meals usually take across the courses",
     "host meal default sequence single opener centre sides fromage skip sweet midpoint"),
    # --- 26 ---
    ("Replaced the loud Brixton cocktail bar with The Pelican wine list for monthly drinks with Yusuf and Iona; we can hear each other and the train home is closer.", "decision", "personal", False,
     [("Brixton cocktail bar", "place"), ("The Pelican", "place"), ("Yusuf", "person"), ("Iona", "person"), ("train", "infrastructure")],
     [("The Pelican", "Brixton cocktail bar", "REPLACES")],
     "which drinks venue took over for the monthly hangout and why",
     "drinks venue swap loud cocktail to wine bar volume train commute"),
    # --- 27 ---
    ("The friendship with Tomás that drifted in 2024 came back into focus over Whatsapp voice notes in March 2026; we've worked up to bi-weekly walks again.", "milestone", "personal", False,
     [("Tomás", "person"), ("2024", "date"), ("Whatsapp voice notes", "tool"), ("March 2026", "date"), ("walks", "activity")],
     [],
     "when did the dormant friendship come back to life and through which channel",
     "friendship drift recovery voice note medium walks cadence rebuild"),
    # --- 28 ---
    ("The board-game night dietary cheat-sheet pinned to the fridge: Dani is gluten-free, Theo is allergic to walnuts, Iris does not eat pork, everyone is fine with mushrooms.", "reference", "personal", False,
     [("board-game night", "event"), ("fridge", "place"), ("Dani", "person"), ("Theo", "person"), ("walnuts", "food"), ("Iris", "person")],
     [],
     "what dietary needs do my regular tabletop guests have and where do I track them",
     "game night diet sheet fridge gluten allergy nut pork mushroom ok"),
    # --- 29 ---
    ("Prefers the post-mortem walk after dinner parties to the post-mortem text the next day; thirty minutes round the block with Sam unpacks more than two days of replies.", "preference", "personal", False,
     [("post-mortem walk", "activity"), ("dinner parties", "event"), ("post-mortem text", "method"), ("Sam", "person")],
     [("post-mortem walk", "post-mortem text", "PREFERS")],
     "which after-event debrief format wins out and what does the loop look like",
     "post mortem walk after dinner over text next day round block sam"),
    # --- 30 ---
    ("The neighbour upstairs in flat 7, Marcellus, plays trombone Wednesday evenings; we agreed on a 21:30 cut-off after the first month and it has held since 2025-08.", "fact", "personal", False,
     [("flat 7", "place"), ("Marcellus", "person"), ("trombone", "tool"), ("Wednesday", "date"), ("2025-08", "date")],
     [("Marcellus", "flat 7", "LIVES_IN")],
     "what noise truce is in place with the upstairs neighbour and since when",
     "neighbour flat upstairs trombone weekday cutoff time agreement since"),
    # --- 31 ---
    ("Switched my birthday format on 2026-03-30 from a big bar takeover to a Saturday lunch for ten; I want to actually talk to people, not shout at them.", "decision", "personal", False,
     [("birthday", "event"), ("2026-03-30", "date"), ("bar takeover", "event"), ("Saturday lunch", "event")],
     [("Saturday lunch", "bar takeover", "REPLACES")],
     "which birthday format took over from the loud one and why",
     "birthday swap bar takeover to small lunch saturday talk over shout date"),
    # --- 32 ---
    ("The chat thread for the hiking crew of seven uses three reactions only — boot for in, mountain for maybe, sleeping bag for out — voted in on 2026-01-19.", "architecture", "personal", False,
     [("hiking crew", "concept"), ("boot", "concept"), ("mountain", "concept"), ("sleeping bag", "concept"), ("2026-01-19", "date")],
     [],
     "how does the trekking group signal attendance in the chat and since when",
     "hiking crew chat reaction code in maybe out emoji rule date vote"),
    # --- 33 ---
    ("The Lordship Lane neighbours' street WhatsApp has 38 members; mostly bin-day reminders and lost-cat posters, with the occasional rescue dog adoption thread.", "fact", "personal", False,
     [("Lordship Lane", "place"), ("WhatsApp", "tool"), ("bin-day", "event"), ("lost-cat posters", "tool")],
     [("WhatsApp", "Lordship Lane", "RELATED_TO")],
     "what does the residents' messenger thread on my street actually carry",
     "street whatsapp member count bin day lost cat rescue dog content"),
    # --- 34. noise ---
    ("Quick check, are we still doing nine or did Maya bail.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The 2026 social calendar from January through June is at 19 pinned events: 4 birthdays, 3 weddings, 2 reunions, 2 stag/hen, 6 dinners, 2 trips.", "reference", "personal", False,
     [("2026", "date"), ("January", "date"), ("June", "date"), ("birthdays", "event"), ("weddings", "event"), ("reunions", "event")],
     [],
     "how loaded is the first half of the year on the social ledger and what is in it",
     "social calendar pinned event count first half year breakdown category"),
    # --- 36 ---
    ("Chose to skip the Henderson wedding on 2026-05-23 and send a card and gift; the venue clash with Theo's stag was the deciding factor.", "decision", "personal", False,
     [("Henderson wedding", "event"), ("2026-05-23", "date"), ("Theo", "person"), ("stag", "event")],
     [("stag", "Henderson wedding", "PREFERS")],
     "which May ceremony am I missing and what won the clash",
     "wedding skip card gift send venue clash stag priority date may"),
    # --- 37 ---
    ("The friend group dynamic shifted after Eva moved to Berlin in 2025-09; Iona quietly stepped into the central organiser role within four months.", "fact", "personal", False,
     [("Eva", "person"), ("Berlin", "place"), ("2025-09", "date"), ("Iona", "person")],
     [("Eva", "Berlin", "LIVES_IN")],
     "what shifted in the group after the move abroad and who took over coordination",
     "friend group dynamic shift relocation berlin new organiser months date"),
    # --- 38 ---
    ("The dinner-party drinks default rotated from an Aperol spritz round to a chilled Beaujolais welcome glass on 2026-02-08; cheaper, faster pour, fewer leftovers.", "decision", "personal", False,
     [("Aperol spritz", "food"), ("Beaujolais", "food"), ("2026-02-08", "date"), ("dinner-party", "event")],
     [("Beaujolais", "Aperol spritz", "REPLACES")],
     "which welcome drink took over at the hosted meals and what drove it",
     "dinner party welcome drink swap spritz to wine cost speed waste"),
    # --- 39 ---
    ("The board-game cafe outing on 2026-04-08 at Draughts Hackney ended at 23:40 with Wingspan unfinished; Iona stole the round on the last turn anyway.", "fact", "personal", False,
     [("board-game cafe", "place"), ("2026-04-08", "date"), ("Draughts Hackney", "place"), ("Wingspan", "concept"), ("Iona", "person")],
     [],
     "when was the last games cafe night and how did the headline match end",
     "board game cafe outing date end time wingspan unfinished steal round"),
    # --- 40 ---
    ("Awkward Christmas drinks at the office on 2025-12-19 ran into Marcus across the room; we did not speak, both pretended not to notice, the room knew.", "problem", "personal", False,
     [("Christmas drinks", "event"), ("office", "place"), ("2025-12-19", "date"), ("Marcus", "person")],
     [],
     "when did the post-falling-out work-party run-in happen and how did it play",
     "christmas office drinks ex friend run in no speak pretend room aware"),
    # --- 41 ---
    ("Prefers WhatsApp voice notes to texts for keeping in touch with Tomás in São Paulo; eight-hour reply gap stops feeling like a snub when you can hear the laugh.", "preference", "personal", False,
     [("WhatsApp voice notes", "tool"), ("texts", "tool"), ("Tomás", "person"), ("São Paulo", "place")],
     [("WhatsApp voice notes", "texts", "PREFERS"), ("Tomás", "São Paulo", "LIVES_IN")],
     "which medium wins for staying connected with the friend abroad and why",
     "voice note over text long distance friend timezone gap laugh tone"),
    # --- 42 ---
    ("The board-game night at the flat tops out at six players because the dining table seats six and the kitchen island fits two more for the snack queue.", "architecture", "personal", False,
     [("board-game night", "event"), ("flat", "place"), ("dining table", "infrastructure"), ("kitchen island", "infrastructure")],
     [],
     "what caps the size of the games evening at home and what determines it",
     "game night cap player count dining table seats island snack queue"),
    # --- 43 ---
    ("Replaced the annual New Year's Eve dinner with a New Year's Day brunch on 2026-01-01; sober heads, kids welcome, no fight over the cab booking.", "decision", "personal", False,
     [("New Year's Eve dinner", "event"), ("New Year's Day brunch", "event"), ("2026-01-01", "date"), ("kids", "person"), ("cab", "tool")],
     [("New Year's Day brunch", "New Year's Eve dinner", "REPLACES")],
     "which holiday format took over from the late-night one and what improved",
     "new year eve to day brunch swap sober kids welcome no cab fight date"),
    # --- 44 ---
    ("Hen weekend for Iona is in York 2026-07-11 to 2026-07-13; eleven of us, two-night Airbnb, afternoon-tea Saturday, walls-walk Sunday morning before the train.", "milestone", "personal", False,
     [("Iona", "person"), ("York", "place"), ("2026-07-11", "date"), ("2026-07-13", "date"), ("afternoon-tea", "food"), ("walls-walk", "activity")],
     [("Iona", "York", "VISITED")],
     "when is the hen trip booked and how is the weekend shaped",
     "hen weekend york dates headcount airbnb tea saturday walls sunday train"),
    # --- 45 ---
    ("The friend-network shrink after the 2025 move from Bristol to London settled at four kept-close, three drifted, two reconnected once a year through birthdays.", "fact", "personal", False,
     [("Bristol", "place"), ("London", "place"), ("2025", "date"), ("birthdays", "event")],
     [],
     "how did the friendship map redistribute after last year's relocation",
     "friendship map after move count kept drifted reconnect birthday city"),
    # --- 46 ---
    ("The block-party on Lordship Lane on 2026-06-21 needs the council street-closure form by 2026-04-30; Iris is filing it, I am chasing the printer for raffle tickets.", "milestone", "personal", False,
     [("block-party", "event"), ("Lordship Lane", "place"), ("2026-06-21", "date"), ("council", "organization"), ("2026-04-30", "date"), ("Iris", "person")],
     [("block-party", "Lordship Lane", "LOCATED_IN")],
     "when is the street party booked and what is on the run-up checklist",
     "block party street date council form deadline iris file raffle ticket"),
    # --- 47 ---
    ("Prefers the standing Saturday pub trivia at The Junction over the Friday quiz at The Anvil; Friday gets work refugees, Saturday gets the regulars who actually know capitals.", "preference", "personal", False,
     [("Saturday", "date"), ("pub trivia", "event"), ("The Junction", "place"), ("Friday", "date"), ("The Anvil", "place"), ("capitals", "concept")],
     [("Saturday", "Friday", "PREFERS")],
     "which weekly bar quiz wins out and what is the crowd difference",
     "pub trivia saturday over friday junction anvil regulars work crowd"),
    # --- 48 ---
    ("Rebuilt the friendship with Hayden in early 2026 over five long phone calls about the 2024 fight; we agreed in writing not to relitigate, and it has held.", "milestone", "personal", False,
     [("Hayden", "person"), ("2026", "date"), ("phone calls", "tool"), ("2024", "date")],
     [],
     "how did the patched-up friendship get rebuilt and what holds the truce",
     "friendship rebuild phone calls fight year before written rule no relitigate"),
    # --- 49 ---
    ("The dinner-party post-game ritual is loading the dishwasher together with Sam, finishing the last bottle, and ranking the guests by who refilled water without being asked.", "preference", "personal", False,
     [("dinner-party", "event"), ("dishwasher", "tool"), ("Sam", "person"), ("guests", "person")],
     [],
     "what private routine wraps the dinner parties at our place",
     "dinner party post game ritual dishwasher last bottle guest ranking water"),
    # --- 50 ---
    ("The reunion on 2026-09-12 of the 2014 backpacking crew of nine is locked in for a weekend in the Peak District; cottage sleeps ten, two cars, one shared spreadsheet for snacks.", "milestone", "personal", False,
     [("reunion", "event"), ("2026-09-12", "date"), ("2014", "date"), ("backpacking crew", "concept"), ("Peak District", "place"), ("spreadsheet", "tool")],
     [("reunion", "Peak District", "LOCATED_IN")],
     "when is the old travel-mates reunion and how is the weekend resourced",
     "reunion backpacking crew date peak district cottage cars snack sheet"),
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
