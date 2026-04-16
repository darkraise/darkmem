"""One-off emitter for shared-base batch-210 — personal domain (yoga and meditation: Ashtanga, Iyengar, Vinyasa, Yin, Kundalini, asanas, pranayama, vipassana, MBSR, meditation apps).

Writes 50 rows to data/v2/shared/batch_210.tmp.jsonl with ids shared-10451..10500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_210.tmp.jsonl"
ID_OFFSET = 10450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Committed to the Ashtanga Primary series six mornings a week after a month of Vinyasa classes left the hip openers feeling undercooked; the fixed sequence finally gave my practice a spine.", "decision", "personal", False,
     [("Ashtanga Primary series", "activity"), ("Vinyasa", "activity"), ("hip openers", "activity")],
     [("Ashtanga Primary series", "Vinyasa", "PREFERS")],
     "which yoga style won out over Vinyasa for daily morning practice and what gap pushed the switch",
     "ashtanga primary vinyasa morning practice hip opener fixed sequence"),
    # --- 2. architecture ---
    ("Home shala setup runs three practice zones: a cork mat corner for Ashtanga led classes, a wall rope and bolster rack for Iyengar restoratives, and a heated nook for Bikram-style sequences on winter mornings.", "architecture", "personal", False,
     [("cork mat corner", "place"), ("Ashtanga", "activity"), ("wall rope", "tool"), ("bolster rack", "tool"), ("Iyengar", "activity"), ("heated nook", "place"), ("Bikram", "activity")],
     [("wall rope", "Iyengar", "APPLIES_TO"), ("heated nook", "Bikram", "APPLIES_TO")],
     "how is the home yoga space partitioned by style across mat, props, and heated zones",
     "home shala cork mat wall rope bolster iyengar ashtanga bikram zone"),
    # --- 3. milestone ---
    ("First clean Bakasana hold landed this Sunday after six months of slow approach work; the knees finally stacked on the triceps without a drift and I held it for a full five breaths.", "milestone", "personal", False,
     [("Bakasana", "activity"), ("Sunday", "date"), ("triceps", "activity")],
     [],
     "when did the crow-pose balance finally click and how long did the first clean hold last",
     "bakasana crow pose hold sunday six month triceps five breath balance"),
    # --- 4. fact ---
    ("Pattabhi Jois systematised the modern Ashtanga method at the Mysore shala and his grandson Sharath Jois kept the Mysore-style self-practice format after taking over the lineage.", "fact", "personal", False,
     [("Pattabhi Jois", "person"), ("Ashtanga", "activity"), ("Mysore", "place"), ("Sharath Jois", "person"), ("Mysore-style", "activity")],
     [("Sharath Jois", "Pattabhi Jois", "KNOWS"), ("Ashtanga", "Pattabhi Jois", "AUTHORED_BY")],
     "which teacher formalised modern Ashtanga in Mysore and who inherited the lineage afterwards",
     "pattabhi jois sharath mysore ashtanga lineage grandson self practice"),
    # --- 5. decision ---
    ("Picked Iyengar over Vinyasa for the injury-recovery block after the shoulder strain; the prop-heavy alignment work from BKS Iyengar's system let me load the joint progressively without reaggravating it.", "decision", "personal", False,
     [("Iyengar", "activity"), ("Vinyasa", "activity"), ("BKS Iyengar", "person"), ("shoulder strain", "emotion")],
     [("Iyengar", "Vinyasa", "PREFERS"), ("Iyengar", "BKS Iyengar", "AUTHORED_BY")],
     "which yoga approach replaced Vinyasa during the shoulder-rehab block and why did the choice stick",
     "iyengar vinyasa shoulder injury prop alignment bks iyengar rehab"),
    # --- 6. reference ---
    ("The Patañjali Yoga Sutras stay pinned on the shelf in the Edwin Bryant translation; chapter two's niyamas keep getting revisited whenever the home practice starts drifting into performance mode.", "reference", "personal", False,
     [("Patañjali Yoga Sutras", "publication"), ("Edwin Bryant", "person"), ("niyamas", "concept")],
     [("Patañjali Yoga Sutras", "Edwin Bryant", "AUTHORED_BY")],
     "which translation of the Yoga Sutras sits on the reference shelf and which chapter gets reread most",
     "patanjali yoga sutra edwin bryant translation niyama chapter two"),
    # --- 7. problem ---
    ("Sirsasana headstand kept collapsing onto the crown until a teacher pointed out the forearm tripod was splaying; locking the elbows shoulder-width and seating the weight into the wrists fixed it in one session.", "problem", "personal", False,
     [("Sirsasana", "activity"), ("forearm tripod", "activity"), ("elbows", "activity"), ("wrists", "activity")],
     [],
     "which headstand alignment flaw was collapsing the pose and what cue corrected it",
     "sirsasana headstand forearm tripod elbow wrist splay collapse cue"),
    # --- 8. architecture ---
    ("Daily pranayama sits between asana and meditation: ten rounds of Nadi Shodhana to balance, then Ujjayi carried through the sitting, with Kapalabhati only on heavier days when the mind refuses to settle.", "architecture", "personal", False,
     [("pranayama", "activity"), ("Nadi Shodhana", "activity"), ("Ujjayi", "activity"), ("Kapalabhati", "activity")],
     [("Ujjayi", "Nadi Shodhana", "BUILDS_ON")],
     "how is the breathwork block sequenced across alternate-nostril, ocean breath, and the more intense skull-shining practice",
     "pranayama nadi shodhana ujjayi kapalabhati sequence daily breath"),
    # --- 9. decision ---
    ("Dropped Bhastrika from the morning set after it kept spiking the resting pulse into the afternoon; Bhramari humming breath at ten rounds gives the same calming handle without the sympathetic kickback.", "decision", "personal", False,
     [("Bhastrika", "activity"), ("Bhramari", "activity")],
     [("Bhramari", "Bhastrika", "REPLACES")],
     "which forceful breath got cut from the morning routine and which gentler technique replaced it",
     "bhastrika bhramari humming breath morning pulse spike replace calm"),
    # --- 10. noise ---
    ("The studio's front window box is overdue for a repaint and the tenants upstairs keep leaving the hallway light on at odd hours.", "fact", "noise", True, [], [], None, None),
    # --- 11. fact ---
    ("Drishti gaze points anchor each asana in the Ashtanga system: nasagrai for standing poses, bhrumadhya for Urdhva Mukha, and angushtha madhyai for the sun salutation upward reach.", "fact", "personal", False,
     [("Drishti", "concept"), ("Ashtanga", "activity"), ("nasagrai", "concept"), ("bhrumadhya", "concept"), ("Urdhva Mukha", "activity"), ("angushtha madhyai", "concept")],
     [("Drishti", "Ashtanga", "APPLIES_TO")],
     "how are gaze points assigned across standing poses and upward dog in the Ashtanga method",
     "drishti gaze point ashtanga nasagrai bhrumadhya angushtha madhyai"),
    # --- 12. architecture ---
    ("The three bandhas layer inward from the body: Mula bandha at the pelvic floor, Uddiyana bandha under the navel, and Jalandhara bandha at the throat, engaged in that order at the start of every practice.", "architecture", "personal", False,
     [("Mula bandha", "concept"), ("Uddiyana bandha", "concept"), ("Jalandhara bandha", "concept")],
     [("Uddiyana bandha", "Mula bandha", "BUILDS_ON"), ("Jalandhara bandha", "Uddiyana bandha", "BUILDS_ON")],
     "which three internal locks get engaged at practice start and in what body-upward order",
     "bandha mula uddiyana jalandhara lock pelvic navel throat order"),
    # --- 13. decision ---
    ("Switched the Tuesday evening practice from Power yoga to Yin yoga; long five-minute holds in pigeon and saddle did more for the hip capsule than any heated vinyasa session the whole winter.", "decision", "personal", False,
     [("Power yoga", "activity"), ("Yin yoga", "activity"), ("pigeon", "activity"), ("saddle", "activity"), ("hip capsule", "activity")],
     [("Yin yoga", "Power yoga", "REPLACES")],
     "which evening yoga style replaced the heated Power class and which tissue target drove the change",
     "yin power yoga pigeon saddle hip capsule long hold tuesday evening"),
    # --- 14. milestone ---
    ("Completed the ten-day Goenka Vipassana retreat in Dhamma Mahi this May; ten hours of sitting a day and no talking for the whole stretch reset the baseline concentration more than a year of home practice had.", "milestone", "personal", False,
     [("Goenka", "person"), ("Vipassana", "activity"), ("Dhamma Mahi", "place"), ("May", "date")],
     [("Vipassana", "Goenka", "AUTHORED_BY")],
     "when did the first ten-day silent retreat finish and how much daily sitting did it demand",
     "goenka vipassana ten day retreat dhamma mahi may silent sitting"),
    # --- 15. reference ---
    ("Sharon Salzberg's Lovingkindness book sits on the nightstand as the main metta reference; the phrases she teaches for the four directions transferred cleanly into the evening sit.", "reference", "personal", False,
     [("Sharon Salzberg", "person"), ("Lovingkindness", "publication"), ("metta", "activity")],
     [("Lovingkindness", "Sharon Salzberg", "AUTHORED_BY")],
     "which book serves as the primary loving-kindness reference and what practice element transferred from it",
     "sharon salzberg lovingkindness metta four direction nightstand reference"),
    # --- 16. decision ---
    ("Uninstalled Headspace after a year in favour of the Waking Up app; Sam Harris's theory tracks and the unguided timer at the end of each lesson was the feature that actually built the habit.", "decision", "personal", False,
     [("Headspace", "tool"), ("Waking Up", "tool"), ("Sam Harris", "person")],
     [("Waking Up", "Headspace", "REPLACES"), ("Waking Up", "Sam Harris", "AUTHORED_BY")],
     "which meditation app replaced Headspace and which feature sealed the switch",
     "headspace waking up sam harris theory unguided timer replace habit"),
    # --- 17. preference ---
    ("Insight Timer is the default app for group sits because the live circles let me join a Thich Nhat Hanh-style walking group at seven each morning without setting anything up locally.", "preference", "personal", False,
     [("Insight Timer", "tool"), ("Thich Nhat Hanh", "person")],
     [],
     "which meditation app is preferred for group sits and which teacher's walking-group tradition shows up there",
     "insight timer group sit thich nhat hanh walking seven morning"),
    # --- 18. architecture ---
    ("Morning routine layers in this order: twenty minutes of Ashtanga opening, ten rounds of Nadi Shodhana, thirty minutes of shamatha breath anchor, then journaling before anything work-related gets opened.", "architecture", "personal", False,
     [("Ashtanga", "activity"), ("Nadi Shodhana", "activity"), ("shamatha", "activity"), ("journaling", "activity")],
     [("shamatha", "Nadi Shodhana", "BUILDS_ON")],
     "how are asana, breathwork, seated meditation, and journaling sequenced in the morning routine",
     "morning routine ashtanga nadi shodhana shamatha journaling sequence"),
    # --- 19. problem ---
    ("Knees kept pinching in full Padmasana during long sits; dropped to quarter lotus with a bolster under the higher knee and the pain went from five-minute onset to a non-issue past forty minutes.", "problem", "personal", False,
     [("Padmasana", "activity"), ("quarter lotus", "activity"), ("bolster", "tool"), ("knee", "emotion")],
     [("quarter lotus", "Padmasana", "REPLACES")],
     "which seated-pose modification fixed the knee pinch during long sits and how much time did it buy",
     "padmasana lotus quarter knee bolster pinch sit modification"),
    # --- 20. decision ---
    ("Picked Jivamukti over Sivananda for the Saturday class because the chanting and readings from the Bhagavad Gita land closer to how I want the ethical side of practice framed.", "decision", "personal", False,
     [("Jivamukti", "activity"), ("Sivananda", "activity"), ("Bhagavad Gita", "publication")],
     [("Jivamukti", "Sivananda", "PREFERS"), ("Jivamukti", "Bhagavad Gita", "USES")],
     "which Saturday class style won out over Sivananda and what text-based element drove the decision",
     "jivamukti sivananda saturday chanting bhagavad gita ethics class"),
    # --- 21. milestone ---
    ("Held Pincha Mayurasana freestanding in the middle of the room this week after months of wall work; forearm placement finally clicked once the pinky edge rooted instead of the index side.", "milestone", "personal", False,
     [("Pincha Mayurasana", "activity"), ("wall work", "activity"), ("forearm", "activity")],
     [],
     "when did the forearm stand finally go freestanding away from the wall and which cue unlocked it",
     "pincha mayurasana forearm stand freestanding wall pinky edge cue"),
    # --- 22. architecture ---
    ("Weekly class grid is split by style: Mysore self-practice Monday through Friday, Iyengar technical on Saturday, and a Restorative yoga session at the neighbourhood studio on Sunday evening.", "architecture", "personal", False,
     [("Mysore", "activity"), ("Iyengar", "activity"), ("Restorative yoga", "activity"), ("Sunday", "date")],
     [],
     "how is the weekly yoga grid partitioned across self-practice, technical, and restorative slots",
     "weekly grid mysore iyengar restorative monday saturday sunday class"),
    # --- 23. decision ---
    ("Dropped the 10% Happier app subscription last renewal; Dan Harris's interviews were great but the actual guided library wasn't getting opened anymore next to the Waking Up course track.", "decision", "personal", False,
     [("10% Happier", "tool"), ("Dan Harris", "person"), ("Waking Up", "tool")],
     [("Waking Up", "10% Happier", "PREFERS")],
     "which meditation subscription got cut and which competing app was actually carrying the daily practice",
     "10 percent happier dan harris waking up subscription drop daily app"),
    # --- 24. fact ---
    ("Trikonasana in the Iyengar method rotates the trailing foot forty-five degrees and squares the pelvis rather than the Ashtanga ninety-degree foot and open hip; the knee loading changes noticeably.", "fact", "personal", False,
     [("Trikonasana", "activity"), ("Iyengar", "activity"), ("Ashtanga", "activity"), ("pelvis", "activity")],
     [],
     "how does the Iyengar triangle-pose alignment differ from the Ashtanga foot angle and what changes in loading",
     "trikonasana triangle iyengar ashtanga forty five degree pelvis knee"),
    # --- 25. reference ---
    ("Kept Jon Kabat-Zinn's Full Catastrophe Living on the meditation shelf as the MBSR anchor; the body scan script in chapter five became the late-night go-to whenever sleep wouldn't land.", "reference", "personal", False,
     [("Jon Kabat-Zinn", "person"), ("Full Catastrophe Living", "publication"), ("MBSR", "method"), ("body scan", "activity")],
     [("Full Catastrophe Living", "Jon Kabat-Zinn", "AUTHORED_BY"), ("MBSR", "Jon Kabat-Zinn", "AUTHORED_BY")],
     "which MBSR book serves as the late-night reference and which practice from it gets used for sleep",
     "jon kabat zinn full catastrophe living mbsr body scan chapter five"),
    # --- 26. architecture ---
    ("Evening sit protocol runs twenty minutes of shamatha breath anchor followed by ten minutes of metta in the Sharon Salzberg phrasing; closing with Trataka candle gaze on Friday nights only.", "architecture", "personal", False,
     [("shamatha", "activity"), ("metta", "activity"), ("Sharon Salzberg", "person"), ("Trataka", "activity"), ("Friday", "date")],
     [("metta", "Sharon Salzberg", "AUTHORED_BY")],
     "how is the evening sitting session layered across concentration, loving-kindness, and candle-gaze work",
     "evening sit shamatha metta trataka candle salzberg friday twenty"),
    # --- 27. decision ---
    ("Chose Urdhva Dhanurasana drop-backs against the wall rather than unassisted from standing; the sacroiliac twinge from a month of free drop-backs disappeared within a week of wall-pressed practice.", "decision", "personal", False,
     [("Urdhva Dhanurasana", "activity"), ("drop-backs", "activity"), ("sacroiliac", "emotion")],
     [],
     "which backbend drill got swapped out to fix the sacroiliac twinge and what support did the replacement use",
     "urdhva dhanurasana drop back wall sacroiliac twinge backbend support"),
    # --- 28. problem ---
    ("Kundalini kriyas from the Yogi Bhajan lineage kept leaving me wired late in the evening; moving the whole Kundalini block to early morning and pairing it with Bhramari at night stopped the sleep disruption cold.", "problem", "personal", False,
     [("Kundalini", "activity"), ("Yogi Bhajan", "person"), ("Bhramari", "activity")],
     [("Kundalini", "Yogi Bhajan", "AUTHORED_BY"), ("Bhramari", "Kundalini", "FIXES")],
     "which lineage of Kundalini kriyas disrupted sleep and how did rescheduling plus humming breath settle it",
     "kundalini yogi bhajan kriya sleep bhramari morning evening fix"),
    # --- 29. fact ---
    ("Joseph Goldstein and Sharon Salzberg co-founded the Insight Meditation Society in Barre, Massachusetts; their early vipassana teachings shaped the secular mindfulness lineage that MBSR later branched from.", "fact", "personal", False,
     [("Joseph Goldstein", "person"), ("Sharon Salzberg", "person"), ("Insight Meditation Society", "organization"), ("Barre", "place"), ("vipassana", "activity"), ("MBSR", "method")],
     [("Insight Meditation Society", "Joseph Goldstein", "AUTHORED_BY"), ("Insight Meditation Society", "Sharon Salzberg", "AUTHORED_BY"), ("MBSR", "vipassana", "BUILDS_ON")],
     "who co-founded the Insight Meditation Society and how does their teaching connect to the MBSR lineage",
     "joseph goldstein sharon salzberg insight meditation society barre mbsr"),
    # --- 30. milestone ---
    ("Stopped alternating zazen and shamatha inside the same sit; pinned zazen to Tuesday and Thursday evenings as a separate practice and concentration on the breath stopped flickering mid-session.", "milestone", "personal", False,
     [("zazen", "activity"), ("shamatha", "activity"), ("Tuesday", "date"), ("Thursday", "date")],
     [],
     "which two sitting traditions got separated across the week to stop cross-contaminating the concentration thread",
     "zazen shamatha tuesday thursday separate sit concentration flicker"),
    # --- 31. reference ---
    ("Mantra practice uses a 108-bead mala of rudraksha seeds; one full round of Om Namah Shivaya counts as a japa cycle and three rounds bookend the evening sit on new-moon days.", "reference", "personal", False,
     [("mala", "tool"), ("rudraksha", "tool"), ("Om Namah Shivaya", "concept"), ("japa", "activity"), ("new-moon", "date")],
     [("japa", "mala", "USES")],
     "how does the mantra practice use a mala, which specific mantra, and when do the three-round bookends happen",
     "mala rudraksha om namah shivaya japa 108 new moon evening sit"),
    # --- 32. milestone ---
    ("Held a full hour of unbroken shamatha breath anchor for the first time this Wednesday; the sit crossed the forty-minute restlessness wall without the usual mid-session fidget reset.", "milestone", "personal", False,
     [("shamatha", "activity"), ("Wednesday", "date"), ("forty-minute", "date")],
     [],
     "when did the first unbroken hour of breath-anchor meditation land and which restlessness threshold did it clear",
     "shamatha hour wednesday forty minute restless unbroken breath anchor"),
    # --- 33. reference ---
    ("Thich Nhat Hanh's Miracle of Mindfulness lives on the bedside table as the walking-meditation primer; the exercises in chapter two framed how I do the morning garden loop.", "reference", "personal", False,
     [("Thich Nhat Hanh", "person"), ("Miracle of Mindfulness", "publication"), ("walking-meditation", "activity")],
     [("Miracle of Mindfulness", "Thich Nhat Hanh", "AUTHORED_BY")],
     "which bedside reference anchors the walking-meditation habit and which chapter shaped the garden routine",
     "thich nhat hanh miracle mindfulness walking bedside chapter two garden"),
    # --- 34. preference ---
    ("Prefer Mysore-style self-practice over led classes for weekday mornings; the room's quiet, the teacher adjusts without interrupting the breath count, and the sequence gets memorised faster.", "preference", "personal", False,
     [("Mysore-style", "activity"), ("led classes", "activity"), ("weekday", "date")],
     [("Mysore-style", "led classes", "PREFERS")],
     "which Ashtanga class format is preferred for weekdays and what three qualities make it work better",
     "mysore self practice led class weekday morning quiet adjust memorise"),
    # --- 35. decision ---
    ("Chose Calm over Headspace for the kids' bedtime wind-down; the Matthew McConaughey sleep stories actually keep them in bed and the parental library splits into age tiers cleanly.", "decision", "personal", False,
     [("Calm", "tool"), ("Headspace", "tool"), ("Matthew McConaughey", "person")],
     [("Calm", "Headspace", "PREFERS")],
     "which app won the kids-bedtime bake-off against Headspace and what specific feature carried it",
     "calm headspace matthew mcconaughey bedtime kid sleep story library"),
    # --- 36. fact ---
    ("Ujjayi breath constricts the glottis to produce the ocean-sound that paces every Ashtanga inhale and exhale; losing the sound is the usual first signal that the vinyasa is moving faster than the breath can sustain.", "fact", "personal", False,
     [("Ujjayi", "activity"), ("glottis", "activity"), ("Ashtanga", "activity"), ("vinyasa", "activity")],
     [("Ujjayi", "Ashtanga", "APPLIES_TO")],
     "how does Ujjayi breath pace Ashtanga and what signal shows the flow has outrun the breath",
     "ujjayi glottis ocean sound ashtanga vinyasa pace breath signal"),
    # --- 37. architecture ---
    ("Props kit for Iyengar sessions layers by frequency of use: two blocks on the near shelf, a wall rope and two belts mid-shelf, and the inversion bench and chair behind for deeper backbend work.", "architecture", "personal", False,
     [("Iyengar", "activity"), ("blocks", "tool"), ("wall rope", "tool"), ("belts", "tool"), ("inversion bench", "tool"), ("chair", "tool")],
     [("wall rope", "Iyengar", "APPLIES_TO"), ("inversion bench", "Iyengar", "APPLIES_TO")],
     "how is the Iyengar prop kit organised across shelves by how often each item gets pulled",
     "iyengar prop block wall rope belt inversion bench chair shelf layer"),
    # --- 38. fact ---
    ("Warrior III kept tipping the standing knee inward until a cue to screw the foot into the mat clockwise stabilised it; the old hip-first correction wasn't addressing the ground reaction at all.", "fact", "personal", False,
     [("Warrior III", "activity"), ("knee", "emotion"), ("hip", "activity"), ("mat", "tool")],
     [],
     "which balance-pose fault caused the standing knee to cave and which cue replaced the old hip-first fix",
     "warrior three knee screw foot mat clockwise hip cue balance"),
    # --- 39. decision ---
    ("Settled on Downward Dog with a slight heel-lift rather than chasing flat heels; the hamstring length wasn't the bottleneck and forcing heels down was flattening the lumbar instead of lengthening the spine.", "decision", "personal", False,
     [("Downward Dog", "activity"), ("heel-lift", "activity"), ("hamstring", "activity"), ("lumbar", "activity")],
     [],
     "which Downward Dog variation got adopted and what spinal trade-off drove the choice away from flat heels",
     "downward dog heel lift hamstring lumbar spine flat bottleneck"),
    # --- 40. milestone ---
    ("Finished the eight-week MBSR course through Palouse Mindfulness this March; Dave Potter's free curriculum mirrors Jon Kabat-Zinn's syllabus and the body scan stuck around as the daily anchor afterwards.", "milestone", "personal", False,
     [("MBSR", "method"), ("Palouse Mindfulness", "organization"), ("March", "date"), ("Dave Potter", "person"), ("Jon Kabat-Zinn", "person"), ("body scan", "activity")],
     [("Palouse Mindfulness", "Dave Potter", "AUTHORED_BY"), ("MBSR", "Jon Kabat-Zinn", "AUTHORED_BY")],
     "which MBSR course got completed in March and which practice element carried forward as the daily anchor",
     "mbsr palouse mindfulness dave potter jon kabat zinn body scan march"),
    # --- 41. decision ---
    ("Picked the Ashtanga Intermediate series Nadi Shodhana section to start learning now rather than chasing Advanced A poses; the teacher at the Mysore room cleared me only for the first half and I trust the gatekeeping.", "decision", "personal", False,
     [("Ashtanga Intermediate series", "activity"), ("Nadi Shodhana", "activity"), ("Advanced A", "activity"), ("Mysore", "place")],
     [("Ashtanga Intermediate series", "Advanced A", "PREFERS")],
     "which Ashtanga progression was chosen this season and what gatekeeping decision shaped it",
     "ashtanga intermediate nadi shodhana advanced mysore teacher gatekeeping"),
    # --- 42. reference ---
    ("Light on Yoga by BKS Iyengar is the pose dictionary on the shelf; whenever alignment for a new asana feels off the photo plates and timings in that book settle the question fast.", "reference", "personal", False,
     [("Light on Yoga", "publication"), ("BKS Iyengar", "person")],
     [("Light on Yoga", "BKS Iyengar", "AUTHORED_BY")],
     "which Iyengar pose dictionary settles alignment questions and what specific content makes it the go-to",
     "light on yoga bks iyengar pose dictionary alignment photo plate"),
    # --- 43. noise ---
    ("The studio lost-and-found box has three mismatched socks and a library card from a city none of the regulars live in.", "fact", "noise", True, [], [], None, None),
    # --- 44. architecture ---
    ("Retreat packing list splits into three dry bags: meditation cushion and shawl in one, the yoga mat and two cork blocks in another, and the journal with the Patañjali Yoga Sutras in a small waterproof pouch.", "architecture", "personal", False,
     [("meditation cushion", "tool"), ("yoga mat", "tool"), ("cork blocks", "tool"), ("journal", "tool"), ("Patañjali Yoga Sutras", "publication")],
     [],
     "how is the retreat kit split across three dry bags and which reference makes it into the waterproof pouch",
     "retreat pack dry bag cushion shawl mat block journal patanjali"),
    # --- 45. preference ---
    ("Prefer a zafu cushion on a zabuton mat over a bench for long sits; the slight forward tilt from the zafu keeps the lumbar lifted without me grinding on the sit bones past the hour mark.", "preference", "personal", False,
     [("zafu", "tool"), ("zabuton", "tool"), ("bench", "tool"), ("sit bones", "activity")],
     [("zafu", "bench", "PREFERS")],
     "which seated-meditation setup is preferred for long sits and which mechanical reason drove the pick",
     "zafu zabuton bench long sit lumbar sit bone tilt prefer"),
    # --- 46. fact ---
    ("Kapalabhati is classed as a shatkarma cleansing practice in the Hatha Yoga Pradipika rather than a pranayama proper; the rapid abdominal expulsions are meant to clear the frontal sinuses before breath regulation begins.", "fact", "personal", False,
     [("Kapalabhati", "activity"), ("shatkarma", "concept"), ("Hatha Yoga Pradipika", "publication"), ("pranayama", "activity"), ("sinuses", "activity")],
     [("Kapalabhati", "shatkarma", "IS_A"), ("Hatha Yoga Pradipika", "Kapalabhati", "APPLIES_TO")],
     "how is Kapalabhati classified in the Hatha Yoga Pradipika and what function does it serve before pranayama",
     "kapalabhati shatkarma hatha yoga pradipika sinus cleansing frontal"),
    # --- 47. decision ---
    ("Switched from a loud kitchen timer to the Insight Timer app's Tibetan bowl bell for sit start and close; the softer ring stopped jolting the nervous system at the exact moment the sit was meant to end gently.", "decision", "personal", False,
     [("Insight Timer", "tool"), ("Tibetan bowl", "tool"), ("kitchen timer", "tool")],
     [("Insight Timer", "kitchen timer", "REPLACES")],
     "which timer replaced the kitchen one for sits and why did the softer bell matter at session close",
     "insight timer tibetan bowl kitchen bell sit close nervous jolt"),
    # --- 48. preference ---
    ("Prefer early Bhagavad Gita chanting in the Eknath Easwaran translation for Jivamukti-style classes; the meter reads naturally aloud and the commentary at the back stays out of the way during actual chanting.", "preference", "personal", False,
     [("Bhagavad Gita", "publication"), ("Eknath Easwaran", "person"), ("Jivamukti", "activity")],
     [("Bhagavad Gita", "Eknath Easwaran", "AUTHORED_BY")],
     "which Bhagavad Gita translation is preferred for class chanting and what property of it makes it work",
     "bhagavad gita eknath easwaran jivamukti chant meter commentary"),
    # --- 49. milestone ---
    ("Cracked Urdhva Dhanurasana stand-up from the floor this April after a year of assisted walk-ups; the fingertip push and breath cue from Sharath Jois's workshop notes finally synced the hip drive with the shoulder stack.", "milestone", "personal", False,
     [("Urdhva Dhanurasana", "activity"), ("April", "date"), ("Sharath Jois", "person"), ("hip drive", "activity")],
     [],
     "when did the unassisted stand-up from wheel pose land and whose cue carried the final synchronisation",
     "urdhva dhanurasana stand up april sharath jois cue hip shoulder"),
    # --- 50. architecture ---
    ("Journal after each sit captures three fields: duration in minutes, dominant hindrance from the five Patañjali kleshas, and a one-line intention carried into the day so the afternoon can be compared against it.", "architecture", "personal", False,
     [("Journal", "tool"), ("Patañjali", "person"), ("kleshas", "concept"), ("intention", "concept")],
     [("kleshas", "Patañjali", "AUTHORED_BY")],
     "which three fields structure the post-sit journal and how do the kleshas feed the hindrance slot",
     "journal sit duration klesha patanjali hindrance intention afternoon"),
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
