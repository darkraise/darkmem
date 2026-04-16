"""One-off emitter for shared-base batch-278 — personal domain (martial arts: BJJ, Judo, Boxing, Muay Thai, Wrestling, MMA, Karate, Taekwondo).

Writes 50 rows to data/v2/shared/batch_278.tmp.jsonl with ids shared-13851..13900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_278.tmp.jsonl"
ID_OFFSET = 13850

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Earned my blue belt in Brazilian Jiu-Jitsu last spring after three years of steady training at the academy and now the IBJJF window for stripes feels less abstract.", "milestone", "personal", False,
     [("Brazilian Jiu-Jitsu", "activity"), ("IBJJF", "organization"), ("blue belt", "goal")],
     [("blue belt", "Brazilian Jiu-Jitsu", "APPLIES_TO")],
     "when did I hit my first coloured belt in grappling and which governing body sets the stripe cadence",
     "blue belt bjj ibjjf stripe promotion grappling three year"),
    # --- 2 ---
    ("Decided to build my entire open-guard game around the De La Riva hook before branching into berimbolo sweeps; too many white belts chase the berimbolo without the base hook and it shows.", "decision", "personal", False,
     [("De La Riva", "method"), ("berimbolo", "method"), ("open-guard", "concept")],
     [("berimbolo", "De La Riva", "BUILDS_ON")],
     "which open-guard foundation am I locking in before adding the fancier inversion sweeps",
     "de la riva guard berimbolo sweep foundation hook base open"),
    # --- 3 ---
    ("Rickson Gracie's invisible-jiu-jitsu seminar at Marcelo Garcia's academy reframed how I think about connection in the closed guard; weight distribution matters more than the grip I fixated on.", "milestone", "personal", False,
     [("Rickson Gracie", "person"), ("Marcelo Garcia", "person"), ("closed guard", "concept")],
     [("Rickson Gracie", "closed guard", "APPLIES_TO")],
     "which legend's seminar at Marcelo Garcia's gym changed how I think about closed-guard connection",
     "rickson gracie invisible jiu jitsu marcelo garcia seminar closed guard"),
    # --- 4 ---
    ("Made the call to train no-gi two nights a week specifically to work on the knee cut pass under John Danaher-style instructionals; the gi kept hiding weak posture on the shallow cut.", "decision", "personal", False,
     [("no-gi", "activity"), ("knee cut", "method"), ("John Danaher", "person")],
     [("knee cut", "no-gi", "APPLIES_TO")],
     "why did I split my week toward no-gi and which pass am I prioritising from the Danaher system",
     "no gi knee cut pass danaher instructional weak posture gi hide"),
    # --- 5 ---
    ("The Danaher Death Squad's heel-hook curriculum is the single biggest reason I finally understand ashi garami; before the breakdown it was a pile of positions with no ordering principle.", "reference", "personal", False,
     [("Danaher Death Squad", "organization"), ("heel-hook", "method"), ("ashi garami", "concept")],
     [("Danaher Death Squad", "heel-hook", "PRODUCES")],
     "which team's curriculum finally made leg entanglements click for me as an ordered system",
     "danaher death squad heel hook ashi garami leg lock curriculum"),
    # --- 6 ---
    ("Watched Gordon Ryan versus Craig Jones at ADCC in Las Vegas and the body-lock passing pressure was a full-on study session for my own top game; took pages of notes on the plane home.", "milestone", "personal", False,
     [("Gordon Ryan", "person"), ("Craig Jones", "person"), ("ADCC", "event"), ("Las Vegas", "place")],
     [("ADCC", "Las Vegas", "LOCATED_IN")],
     "which ADCC superfight sharpened my top pressure study and where did I see it live",
     "gordon ryan craig jones adcc las vegas body lock passing notes"),
    # --- 7 ---
    ("Prefer training at an Eddie Bravo 10th Planet affiliate for the rubber-guard work even though the gi academy is closer; the systems complement each other rather than competing.", "preference", "personal", False,
     [("Eddie Bravo", "person"), ("10th Planet", "organization"), ("rubber-guard", "method")],
     [("10th Planet", "rubber-guard", "PRODUCES")],
     "which affiliation do I drive further for because of the rubber-guard system",
     "eddie bravo 10th planet rubber guard affiliate commute system"),
    # --- 8 ---
    ("Mica Galvão's instructional on modern half-guard passing is now my default weekend study block; the shoulder-pressure chapter alone paid for the subscription inside two rounds.", "reference", "personal", False,
     [("Mica Galvão", "person"), ("half-guard", "concept"), ("shoulder-pressure", "method")],
     [("Mica Galvão", "half-guard", "APPLIES_TO")],
     "whose modern half-guard instructional became my weekend study and which chapter was the standout",
     "mica galvao half guard pass shoulder pressure instructional weekend"),
    # --- 9 ---
    ("Hit my first Ezekiel choke from mount in live rolling against a purple belt and the surprise on his face was worth the six months of setting up failed attempts from bottom.", "milestone", "personal", False,
     [("Ezekiel choke", "method"), ("mount", "concept"), ("purple belt", "goal")],
     [("Ezekiel choke", "mount", "APPLIES_TO")],
     "which unusual choke did I finally land from mount against a higher belt in live training",
     "ezekiel choke mount purple belt live rolling setup six month"),
    # --- 10. noise ---
    ("The gym lost-and-found bin has three single mouthguards, a lucky sock, and a biography of a mid-century opera singer nobody has claimed.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Adopted the Roger Gracie-style pressure passing template after two years of trying to play like Marcelo Garcia; body type and flexibility were fighting my instincts every round.", "decision", "personal", False,
     [("Roger Gracie", "person"), ("Marcelo Garcia", "person"), ("pressure passing", "method")],
     [("Roger Gracie", "Marcelo Garcia", "REPLACES")],
     "which grappling stylist's template finally stuck for me once I stopped forcing a different body type's game",
     "roger gracie pressure passing marcelo garcia body type switch"),
    # --- 12 ---
    ("Problem with my guard game is the passer keeps isolating my far hip because I open my knee too early on De La Riva; a drill block on hip framing comes next cycle.", "problem", "personal", False,
     [("De La Riva", "method"), ("far hip", "concept"), ("hip framing", "method")],
     [("hip framing", "far hip", "APPLIES_TO")],
     "which bad habit keeps costing me my guard and which drill block am I queuing to fix it",
     "de la riva far hip knee open guard pass frame drill block"),
    # --- 13 ---
    ("My Judo cross-training night is strictly for osoto gari and ippon seoi nage; the Kodokan-style ukemi from day one is what lets me fall into the throws without flinching.", "architecture", "personal", False,
     [("Judo", "activity"), ("osoto gari", "method"), ("ippon seoi nage", "method"), ("Kodokan", "organization"), ("ukemi", "concept")],
     [("osoto gari", "Judo", "APPLIES_TO"), ("ippon seoi nage", "Judo", "APPLIES_TO")],
     "which two Judo throws anchor my cross-training night and what safety skill makes them trainable",
     "judo osoto gari ippon seoi nage kodokan ukemi cross train"),
    # --- 14 ---
    ("Kyuzo Mifune's canon of the Judo kata is my reference for uchi komi form; the footage has held up despite being older than my father and the posture notes still correct my throws.", "reference", "personal", False,
     [("Kyuzo Mifune", "person"), ("Judo", "activity"), ("uchi komi", "method")],
     [("Kyuzo Mifune", "Judo", "APPLIES_TO")],
     "whose archival Judo footage do I keep returning to for posture reference on throw entries",
     "kyuzo mifune judo kata uchi komi reference posture footage"),
    # --- 15 ---
    ("Jigoro Kano founding the Kodokan is the story I always come back to when explaining why Judo feels like a curriculum and not a collection of tricks; framework first, tricks after.", "fact", "personal", False,
     [("Jigoro Kano", "person"), ("Kodokan", "organization"), ("Judo", "activity")],
     [("Jigoro Kano", "Kodokan", "PRODUCES")],
     "which founding story do I cite to explain why Judo reads as a curriculum rather than a trick list",
     "jigoro kano kodokan judo founding curriculum framework story"),
    # --- 16 ---
    ("Yasuhiro Yamashita's unbeaten Olympic gold run is the poster above the mat room; the instructor hung it specifically to anchor what competition-grade uchi komi actually looks like at scale.", "reference", "personal", False,
     [("Yasuhiro Yamashita", "person"), ("Olympic gold", "event"), ("uchi komi", "method")],
     [("Yasuhiro Yamashita", "Olympic gold", "APPLIES_TO")],
     "whose Olympic-gold photo did the instructor hang to anchor competition-grade throw entries",
     "yamashita olympic gold uchi komi poster mat room anchor"),
    # --- 17 ---
    ("Prefer orthodox stance for boxing even though I am naturally left-side dominant; the jab as a measuring tool feels worth the trade versus what I would gain going southpaw.", "decision", "personal", False,
     [("orthodox", "concept"), ("southpaw", "concept"), ("jab", "method"), ("boxing", "activity")],
     [("jab", "orthodox", "APPLIES_TO")],
     "which boxing stance did I settle on despite my natural side dominance and which tool drove the choice",
     "orthodox southpaw jab boxing stance measuring left dominant trade"),
    # --- 18 ---
    ("Drilling the jab-cross with a slip pivot replaces my old bounce-back reset because the old pattern fed my partner a clean counter; the pivot cuts the line and keeps the hand floating.", "architecture", "personal", False,
     [("jab-cross", "method"), ("slip pivot", "method"), ("bounce-back reset", "method")],
     [("slip pivot", "bounce-back reset", "REPLACES")],
     "which defensive footwork replaced my bounce-back reset after feeding counters and why",
     "jab cross slip pivot bounce back reset counter line footwork"),
    # --- 19 ---
    ("Rope work is the drill I refuse to skip in boxing; two three-minute rounds before padwork sets the rhythm for my feet and the cardio debt becomes visible immediately if I cut it.", "preference", "personal", False,
     [("Rope work", "method"), ("padwork", "activity"), ("boxing", "activity")],
     [("Rope work", "boxing", "APPLIES_TO")],
     "which conditioning drill do I refuse to skip in my boxing warmup and what happens if I do",
     "rope work jump skip boxing pad warmup rhythm cardio debt"),
    # --- 20 ---
    ("Cus D'Amato's peek-a-boo is not my style but I borrow the head-movement drills three times a week; the number system on the bag carries over even though I do not fight from a crouch.", "architecture", "personal", False,
     [("Cus D'Amato", "person"), ("peek-a-boo", "method"), ("head-movement", "method")],
     [("Cus D'Amato", "peek-a-boo", "PRODUCES")],
     "which classic trainer's system do I borrow drills from without adopting the whole style",
     "cus d'amato peek a boo head movement number system bag drill"),
    # --- 21 ---
    ("Watched a Freddie Roach mitt session on YouTube and noticed he counts every slip aloud; copying the verbal count made my sparring partner's read of my shoulder drop way harder to catch.", "architecture", "personal", False,
     [("Freddie Roach", "person"), ("mitt session", "activity"), ("slip", "method")],
     [("Freddie Roach", "mitt session", "PRODUCES")],
     "whose mitt-session habit did I copy to make my slip less readable in sparring",
     "freddie roach mitt slip count verbal shoulder drop read youtube"),
    # --- 22 ---
    ("Terence Crawford's switch-hitting on the Spence fight is the clearest demonstration I've ever seen for committing to both sides; I rebuilt my southpaw lead hook drill after that card.", "architecture", "personal", False,
     [("Terence Crawford", "person"), ("switch-hitting", "method"), ("southpaw", "concept"), ("lead hook", "method")],
     [("Terence Crawford", "switch-hitting", "PRODUCES")],
     "which championship fight convinced me to commit real work to both stances in boxing",
     "terence crawford switch hit spence southpaw lead hook card fight"),
    # --- 23 ---
    ("Teofimo Lopez's right hand against Lomachenko is my reference clip for the pivot-step check hook; the timing still feels unreasonable but the mechanics are repeatable.", "reference", "personal", False,
     [("Teofimo Lopez", "person"), ("Lomachenko", "person"), ("check hook", "method")],
     [("Teofimo Lopez", "Lomachenko", "RELATED_TO")],
     "which televised knockdown do I keep rewatching for check-hook mechanics on a fast opponent",
     "teofimo lopez lomachenko check hook pivot step right hand knock"),
    # --- 24 ---
    ("Canelo Alvarez versus Gennady Golovkin is the fight I re-study every six months; the body work in the middle rounds is the template for my own slow pressure in sparring.", "fact", "personal", False,
     [("Canelo", "person"), ("Gennady Golovkin", "person"), ("body work", "method")],
     [("Canelo", "Gennady Golovkin", "RELATED_TO")],
     "which trilogy fight do I re-study twice a year for body-work and slow pressure",
     "canelo golovkin body work pressure middle round trilogy sparring"),
    # --- 25 ---
    ("The teep is the single Muay Thai tool that paid back more than the hours I put into it; every sparring night I cash it in to reset range and cut off aggressive pressure.", "fact", "personal", False,
     [("teep", "method"), ("Muay Thai", "activity"), ("sparring", "activity")],
     [("teep", "Muay Thai", "APPLIES_TO")],
     "which Muay Thai tool gives me the best return per training hour and what does it solve in sparring",
     "teep muay thai sparring range reset aggressive pressure push kick"),
    # --- 26 ---
    ("Built my Muay Thai game around the plum clinch and elbow sweeps because I keep my hips heavy and my cardio is not elite; the clinch is where my body type finally matches my tempo.", "architecture", "personal", False,
     [("plum clinch", "method"), ("elbow sweeps", "method"), ("Muay Thai", "activity")],
     [("plum clinch", "Muay Thai", "APPLIES_TO")],
     "which Muay Thai specialisation matches my body type and tempo rather than fighting them",
     "plum clinch elbow sweep muay thai heavy hip cardio tempo body"),
    # --- 27 ---
    ("Buakaw's knee-in-the-pocket style is my highlight reel but Saenchai's feints are where the actual homework lives; copying highlights without the feints gave me a hollow clinch.", "preference", "personal", False,
     [("Buakaw", "person"), ("Saenchai", "person"), ("feint", "method"), ("clinch", "concept")],
     [("Saenchai", "feint", "PRODUCES")],
     "whose highlight reel is eye candy and whose film study is doing the real work for my clinch",
     "buakaw saenchai knee pocket feint highlight homework clinch"),
    # --- 28 ---
    ("Watching the ONE Championship weekly card replaced K-1 as my default Muay Thai viewing; the modern rules set produces cleaner clinch exchanges for study purposes.", "decision", "personal", False,
     [("ONE Championship", "organization"), ("K-1", "organization"), ("clinch", "concept")],
     [("ONE Championship", "K-1", "REPLACES")],
     "which promotion replaced K-1 as my default study tape and why",
     "one championship k1 muay thai card study clinch modern rule"),
    # --- 29 ---
    ("Added a wrestling-focused Saturday session because my double leg was purely instinctual; Dan Gable footage and a live partner re-taught me the level change I was skipping.", "decision", "personal", False,
     [("wrestling", "activity"), ("double leg", "method"), ("Dan Gable", "person"), ("level change", "method")],
     [("level change", "double leg", "APPLIES_TO")],
     "why did I add a dedicated wrestling day and whose footage re-taught me the level change",
     "wrestling double leg dan gable level change saturday session"),
    # --- 30 ---
    ("Cael Sanderson's undefeated NCAA run is the reference point I use with training partners who think perfection at scale is impossible; the tapes show what relentless position work actually compounds into.", "fact", "personal", False,
     [("Cael Sanderson", "person"), ("NCAA", "organization")],
     [("Cael Sanderson", "NCAA", "APPLIES_TO")],
     "whose undefeated career do I point partners at when they claim elite consistency is unachievable",
     "cael sanderson ncaa undefeated wrestling tape position compound"),
    # --- 31 ---
    ("John Smith's low-single drill is now in my weekly rotation; the knee-tap finish reads as unorthodox until you run it live against a heavier partner and the percentages speak for themselves.", "reference", "personal", False,
     [("John Smith", "person"), ("low-single", "method"), ("knee-tap", "method")],
     [("John Smith", "low-single", "PRODUCES")],
     "which wrestler's single-leg variant earned a weekly slot after live testing against heavier partners",
     "john smith low single knee tap wrestling drill rotation heavy"),
    # --- 32 ---
    ("Chose freestyle over Greco-Roman for cross-training because the leg attacks carry into my MMA scrambles directly; the Greco upper-body work would eat training blocks I need elsewhere.", "decision", "personal", False,
     [("freestyle", "method"), ("Greco-Roman", "method"), ("MMA", "activity")],
     [("freestyle", "Greco-Roman", "REPLACES")],
     "which wrestling style did I pick for cross-training and which transfer to my other training drove the choice",
     "freestyle greco roman wrestling cross train mma scramble leg"),
    # --- 33 ---
    ("UFC event nights are now a pen-and-paper study ritual rather than a casual watch; I track takedown defence and clinch exits per round and the numbers sharpen my own gameplan.", "architecture", "personal", False,
     [("UFC", "organization"), ("takedown defence", "concept"), ("clinch exits", "concept")],
     [("takedown defence", "UFC", "APPLIES_TO")],
     "how did my UFC-watching habit turn into a structured film-study workflow",
     "ufc event pen paper takedown defence clinch exit round track"),
    # --- 34 ---
    ("Khabib Nurmagomedov's chain wrestling is the reason I drill the body-lock trip into every no-gi session; the pressure into the fence is a completely different thesis from sport-jiu-jitsu passing.", "fact", "personal", False,
     [("Khabib Nurmagomedov", "person"), ("chain wrestling", "method"), ("body-lock trip", "method")],
     [("Khabib Nurmagomedov", "chain wrestling", "PRODUCES")],
     "whose MMA style convinced me to drill the body-lock trip into every no-gi session",
     "khabib chain wrestling body lock trip fence pressure no gi"),
    # --- 35 ---
    ("Georges St-Pierre's fight IQ is the prototype I use when I coach new MMA guys; his takedown setups off the superman jab are still the cleanest case for a full-integration game.", "decision", "personal", False,
     [("Georges St-Pierre", "person"), ("superman jab", "method"), ("MMA", "activity")],
     [("Georges St-Pierre", "superman jab", "PRODUCES")],
     "whose career do I use as the textbook for integrated striking-to-wrestling setups when coaching beginners",
     "georges st pierre gsp fight iq superman jab takedown integrate"),
    # --- 36 ---
    ("Jon Jones' oblique kick is a move I will study but not drill; the joint risk for training partners is not worth the handful of extra tools it adds to my own kit.", "decision", "personal", False,
     [("Jon Jones", "person"), ("oblique kick", "method"), ("joint risk", "concept")],
     [("oblique kick", "joint risk", "CAUSES")],
     "which Jon Jones technique did I consciously leave out of my drilling plan and why",
     "jon jones oblique kick study not drill joint risk partner"),
    # --- 37 ---
    ("Islam Makhachev's top-game transitions are what I want my own no-gi passing to look like by the end of this year; the body-lock to mount sequence is the specific target.", "milestone", "personal", False,
     [("Islam Makhachev", "person"), ("body-lock", "method"), ("mount", "concept"), ("no-gi", "activity")],
     [("body-lock", "mount", "APPLIES_TO")],
     "whose top-game is the template for my year-end no-gi goal and which specific sequence am I chasing",
     "islam makhachev top game body lock mount no gi goal sequence"),
    # --- 38 ---
    ("Anderson Silva's front-kick knockout of Vitor Belfort is the clip I show new strikers to explain why the teep and the front kick live in the same family; distance answers intent.", "fact", "personal", False,
     [("Anderson Silva", "person"), ("Vitor Belfort", "person"), ("front kick", "method"), ("teep", "method")],
     [("front kick", "teep", "RELATED_TO")],
     "which iconic knockout do I use to teach beginners why the teep and front kick are cousins",
     "anderson silva vitor belfort front kick knockout teep distance"),
    # --- 39 ---
    ("Alex Pereira's left hook off the calf kick rebuilt how I think about stance disruption; broke down the footage three nights in a row before I trusted the timing in sparring.", "architecture", "personal", False,
     [("Alex Pereira", "person"), ("calf kick", "method"), ("left hook", "method")],
     [("left hook", "calf kick", "BUILDS_ON")],
     "whose striking combination forced me to re-think stance disruption and how long did I study before using it",
     "alex pereira left hook calf kick stance disruption footage study"),
    # --- 40 ---
    ("PRIDE FC archives are my weekend rabbit hole whenever modern MMA study feels sterile; the ruleset differences make direct transfer limited but the creativity floor is clearly higher.", "decision", "personal", False,
     [("PRIDE FC", "organization"), ("MMA", "activity"), ("ruleset", "concept")],
     [("PRIDE FC", "MMA", "APPLIES_TO")],
     "which defunct promotion do I fall back to when current MMA film feels too clinical",
     "pride fc archive mma weekend ruleset creative floor sterile"),
    # --- 41 ---
    ("Signed up for a Bellator grappling seminar in Chicago next month; the travel cost is steep but the roster of coaches on the panel is worth one cancellation elsewhere.", "milestone", "personal", False,
     [("Bellator", "organization"), ("Chicago", "place"), ("seminar", "event"), ("grappling", "activity")],
     [("seminar", "Chicago", "LOCATED_IN")],
     "which grappling event did I commit to travelling for and what did I cancel to free the budget",
     "bellator grappling seminar chicago travel coach panel sign up"),
    # --- 42 ---
    ("Karate kata Bassai Dai is on my solo-practice rotation twice a week even though I no longer compete; the Shotokan footwork fixes leaks in my Muay Thai pivots better than any drill I have tried.", "architecture", "personal", False,
     [("Bassai Dai", "method"), ("Shotokan", "method"), ("Karate", "activity"), ("Muay Thai", "activity")],
     [("Shotokan", "Karate", "APPLIES_TO")],
     "which Karate form do I still run solo and what striking leak does the Shotokan footwork plug",
     "bassai dai shotokan karate kata solo muay thai pivot footwork"),
    # --- 43. noise ---
    ("The change room clock has been stuck at seventeen minutes past four for so long that people schedule by it as if it were accurate.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Kyokushin bare-knuckle conditioning is something I respect but will not train at my age; JKA-style Shotokan gives me the lineage I want without the body debt that comes with full-contact knockdown.", "decision", "personal", False,
     [("Kyokushin", "method"), ("JKA", "organization"), ("Shotokan", "method")],
     [("Shotokan", "Kyokushin", "REPLACES")],
     "which Karate lineage did I pick over Kyokushin and what trade-off drove it",
     "kyokushin jka shotokan bare knuckle lineage age body debt"),
    # --- 45 ---
    ("Ippon seoi nage is the throw I trust most when I'm tired; the entry is short enough that fatigue doesn't rob the mechanics and I have finished it against bigger partners more than any other throw.", "fact", "personal", False,
     [("Ippon seoi nage", "method"), ("fatigue", "emotion")],
     [("Ippon seoi nage", "fatigue", "RELATED_TO")],
     "which throw do I reach for when my gas tank is low and why does it survive fatigue",
     "ippon seoi nage judo tired fatigue short entry bigger partner"),
    # --- 46 ---
    ("Chose WT-style Taekwondo sparring over ITF for my kid's class; the Olympic rule set keeps the session focused on controlled head kicks and leaves the hand work out of an eight-year-old's plate.", "decision", "personal", False,
     [("WT", "organization"), ("ITF", "organization"), ("Taekwondo", "activity"), ("Olympic", "event")],
     [("WT", "ITF", "REPLACES")],
     "which Taekwondo rule set did I pick for my kid's class and what did I deliberately leave out",
     "wt itf taekwondo olympic head kick kid hand work rule set"),
    # --- 47 ---
    ("Running through the taegeuk poomsae set with my daughter is the slowest technical work I do all week; it is also the only training block where she actively corrects my posture.", "preference", "personal", False,
     [("taegeuk poomsae", "method"), ("daughter", "person")],
     [("taegeuk poomsae", "daughter", "RELATED_TO")],
     "which slow technical block do I share with a family member and what unusual feedback loop does it create",
     "taegeuk poomsae taekwondo daughter posture slow technical family"),
    # --- 48 ---
    ("Committed to competing in the IBJJF Pan Ams at blue belt next year; the travel paperwork and ruleset timers need lead time so the decision had to be booked on the calendar early.", "milestone", "personal", False,
     [("IBJJF", "organization"), ("Pan Ams", "event"), ("blue belt", "goal"), ("ruleset timers", "concept")],
     [("Pan Ams", "IBJJF", "APPLIES_TO")],
     "which competition did I lock in for next year and why did booking it require early calendar commitment",
     "ibjjf pan ams blue belt competition travel ruleset timer lead"),
    # --- 49 ---
    ("Keep failing the heel-hook escape timing in drilling rounds because I wait for the foot rotation instead of the initial ashi garami lock; the Craig Jones tap-early mantra is the fix.", "problem", "personal", False,
     [("heel-hook", "method"), ("ashi garami", "concept"), ("Craig Jones", "person")],
     [("ashi garami", "heel-hook", "APPLIES_TO")],
     "which leg-lock escape keeps failing in drilling and whose mantra is the corrective",
     "heel hook escape ashi garami craig jones tap early rotation foot"),
    # --- 50 ---
    ("Nagging knee pain from over-rotating on osoto gari entries forced me to re-drill with a slower pivot; the Judo coach flagged it before it turned into an actual injury and the fix was structural.", "problem", "personal", False,
     [("osoto gari", "method"), ("knee pain", "emotion"), ("Judo", "activity")],
     [("osoto gari", "knee pain", "CAUSES")],
     "which throw entry was causing joint pain and what structural fix did the coach prescribe before it escalated",
     "osoto gari knee pain pivot rotate judo coach drill slow fix"),
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
