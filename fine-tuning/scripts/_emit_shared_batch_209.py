"""One-off emitter for shared-base batch-209 — personal domain (strength training and powerlifting: programs, lifts, equipment, RPE/VBT, federations, coaches).

Writes 50 rows to data/v2/shared/batch_209.tmp.jsonl with ids shared-10401..10450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_209.tmp.jsonl"
ID_OFFSET = 10400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Dropped Starting Strength after six months of linear progression stalled at a 140 kg squat; moved onto 5/3/1 with the Boring But Big template for supplemental volume.", "decision", "personal", False,
     [("Starting Strength", "method"), ("5/3/1", "method"), ("Boring But Big", "pattern"), ("squat", "activity")],
     [("5/3/1", "Starting Strength", "REPLACES")],
     "which program replaced Starting Strength once the linear squat progression stalled in the low one-forties",
     "starting strength 5 3 1 boring but big linear stall squat 140"),
    # --- 2 ---
    ("Switched the deadlift stance from conventional to sumo after a year of chronic lower-back pump; sumo keeps the torso more upright and the pull locks out quicker for my build.", "decision", "personal", False,
     [("conventional", "pattern"), ("sumo", "pattern"), ("deadlift", "activity")],
     [("sumo", "conventional", "REPLACES")],
     "why did the deadlift stance change from conventional to sumo after the chronic back pump",
     "sumo conventional deadlift stance torso upright lockout back pump"),
    # --- 3 ---
    ("Hit a 200 kg raw bench press at the USAPL Northeast regional meet on the second attempt; the third at 207.5 stalled mid-press but the lift still counted as a meet PR.", "milestone", "personal", False,
     [("USAPL", "organization"), ("bench press", "activity"), ("Northeast regional", "event")],
     [("USAPL", "Northeast regional", "APPLIES_TO")],
     "which meet produced the 200 kg raw bench press PR and what happened on the third attempt",
     "usapl northeast regional bench press 200 kg pr raw attempt stall"),
    # --- 4 ---
    ("Prefer the Texas Power Bar over the standard Rogue Ohio for heavy squats; the 29 mm shaft whips less under a 220 kg load and the center knurl bites into the traps for a no-slip bar path.", "preference", "personal", False,
     [("Texas Power Bar", "tool"), ("Rogue Ohio", "tool"), ("squat", "activity")],
     [("Texas Power Bar", "Rogue Ohio", "PREFERS")],
     "which barbell does the lifter pick for heavy squats and what property of the shaft drives that choice",
     "texas power bar rogue ohio squat 29mm shaft whip center knurl"),
    # --- 5 ---
    ("The nSuns 5/3/1 LP program runs six days per week with the main lift ramping across nine sets; the spreadsheet autoregulates top-set weight when the AMRAP clears a rep threshold.", "fact", "personal", False,
     [("nSuns", "method"), ("5/3/1", "method"), ("AMRAP", "concept")],
     [("nSuns", "5/3/1", "USES")],
     "how does the nSuns linear-progression variant of 5/3/1 schedule weekly work and what triggers a weight bump",
     "nsuns 5 3 1 lp six day week nine set ramp amrap threshold"),
    # --- 6 ---
    ("Jim Wendler's original 5/3/1 book lays out four training max percentages: 65, 75, and 85 on week one scaling to 75, 85, and 95 on week three with an AMRAP top set.", "fact", "personal", False,
     [("Jim Wendler", "person"), ("5/3/1", "method"), ("training max", "concept"), ("AMRAP", "concept")],
     [("5/3/1", "Jim Wendler", "AUTHORED_BY")],
     "which three weekly percentage schemes define the core loading wave in Wendler's original 5/3/1 book",
     "jim wendler 5 3 1 training max percent 65 75 85 95 amrap top"),
    # --- 7 ---
    ("Moved off high-bar back squat to low-bar for competition after the knee sleeves kept slipping mid-rep; low-bar loads the posterior chain harder and lets me drive with the hips out of the hole.", "decision", "personal", False,
     [("high-bar", "pattern"), ("low-bar", "pattern"), ("back squat", "activity"), ("knee sleeves", "tool")],
     [("low-bar", "high-bar", "REPLACES")],
     "which squat variation replaced high-bar for competition and what biomechanical advantage justified the swap",
     "low bar high bar back squat knee sleeve posterior chain hip drive"),
    # --- 8 ---
    ("Sheiko Prep 29 runs three heavy squat sessions a week with intensities clustered between 75 and 85 percent; the volume is punishing but the classical Russian template has kept form tight.", "fact", "personal", False,
     [("Sheiko Prep 29", "method"), ("squat", "activity"), ("Russian", "place")],
     [],
     "how is weekly squat work distributed in the Sheiko Prep 29 template and what intensity band dominates",
     "sheiko prep 29 squat three session week 75 85 percent russian"),
    # --- 9 ---
    ("The home rack is an EliteFTS Collegiate with a 3x3 upright and 5/8 pin holes; the Rogue Monster Lite was cheaper but the hole spacing on the EliteFTS drops the safeties exactly where I need them for paused benches.", "decision", "personal", False,
     [("EliteFTS", "tool"), ("Rogue Monster Lite", "tool"), ("Collegiate", "tool"), ("paused bench", "activity")],
     [("EliteFTS", "Rogue Monster Lite", "PREFERS")],
     "which power rack won over the Rogue Monster Lite for the home gym and what safety-pin property sealed it",
     "elitefts collegiate rogue monster lite 3x3 upright 5 8 hole pin"),
    # --- 10. noise ---
    ("The cat has claimed the empty protein tub from last month and now naps inside it on the sunny side of the kitchen floor.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("RPE 8 on the top squat single means two reps left in the tank; I log the perceived effort in the Google sheet alongside bar velocity from the Vitruve tracker for autoregulation calls.", "fact", "personal", False,
     [("RPE", "concept"), ("squat", "activity"), ("Vitruve", "tool"), ("autoregulation", "concept")],
     [("Vitruve", "autoregulation", "APPLIES_TO")],
     "how does an RPE-8 top single translate to reps-in-reserve and what tool supplies the bar velocity number",
     "rpe 8 top single squat reps in reserve vitruve velocity autoregulation"),
    # --- 12 ---
    ("Prilepin's chart says 70 percent work should land between twelve and twenty-four total reps; I calibrated the nSuns accessories to that band after a cut week left recovery behind.", "decision", "personal", False,
     [("Prilepin's chart", "concept"), ("nSuns", "method")],
     [("nSuns", "Prilepin's chart", "USES")],
     "how did Prilepin's total-rep recommendation at 70 percent reshape the nSuns accessories after a cut week",
     "prilepin chart 70 percent twelve twenty four total rep nsuns"),
    # --- 13 ---
    ("Picked the SBD knee sleeves over the Rehband 7 mm after a teammate let me borrow a pair for a heavy double; the SBD rebound out of the hole is markedly stiffer at meet-day weights.", "preference", "personal", False,
     [("SBD", "tool"), ("Rehband", "tool"), ("knee sleeves", "tool")],
     [("SBD", "Rehband", "PREFERS")],
     "which brand of knee sleeves replaced the Rehband 7 mm and what heavy-squat property drove the call",
     "sbd rehband 7mm knee sleeve rebound heavy double meet stiff"),
    # --- 14 ---
    ("Built the current block out of Reverse Pyramid Training: top set RPE 9 for three reps, drop 10 percent, drop another 10, then accessory volume from GZCL T3 ranges.", "architecture", "personal", False,
     [("Reverse Pyramid Training", "method"), ("GZCL", "method"), ("RPE", "concept"), ("T3", "concept")],
     [("Reverse Pyramid Training", "GZCL", "USES")],
     "how is the current training block structured across the top set and the backoff sets and which programs feed it",
     "reverse pyramid training rpt rpe 9 top set drop 10 percent gzcl t3"),
    # --- 15 ---
    ("The pause squat at mid-depth for a three-count is in the Wednesday slot; dead-stop drive out of the hole is the primary weak point Coach Brett Gibbs flagged in the last meet video review.", "architecture", "personal", False,
     [("pause squat", "activity"), ("Brett Gibbs", "person"), ("dead-stop", "pattern")],
     [("Brett Gibbs", "pause squat", "APPLIES_TO")],
     "which accessory fills the Wednesday slot to fix the dead-stop drive weakness flagged in the video review",
     "pause squat wednesday three count brett gibbs coach dead stop"),
    # --- 16 ---
    ("Switched federations from USPA to IPF-affiliated USAPL after the rule set changed on sleeved squats; USAPL's stricter depth judging matched my training groove better.", "decision", "personal", False,
     [("USPA", "organization"), ("USAPL", "organization"), ("IPF", "organization"), ("sleeved squat", "activity")],
     [("USAPL", "USPA", "REPLACES")],
     "which federation move followed the USPA sleeved-squat rule shift and what judging difference clinched it",
     "uspa usapl ipf affiliate sleeved squat rule depth judge federation"),
    # --- 17 ---
    ("Eleiko Competition plates showed up two weeks before meet day; the 25 kg collars and the tighter tolerance made the warmup loads feel identical across the chalk and the platform.", "milestone", "personal", False,
     [("Eleiko", "tool"), ("Competition plates", "tool"), ("platform", "place")],
     [("Eleiko", "Competition plates", "APPLIES_TO")],
     "which plate upgrade landed two weeks before meet day and what platform-consistency benefit did it deliver",
     "eleiko competition plate 25 kg collar tolerance warmup meet day"),
    # --- 18 ---
    ("The Inzer Forever lever belt broke in after about fifteen sessions; the prong belt I wore for a decade is now only for warmups because the lever snaps tight to the same notch every rep.", "preference", "personal", False,
     [("Inzer Forever", "tool"), ("lever belt", "tool"), ("prong belt", "tool")],
     [("Inzer Forever", "prong belt", "REPLACES")],
     "which belt replaced the prong for working sets and how many sessions did the break-in take",
     "inzer forever lever belt prong fifteen session break in warmup"),
    # --- 19 ---
    ("Madcow 5x5 ran as the intermediate bridge from Starting Strength into a proper conjugate block; the weekly ramp capped at a five-rep top set and the Friday backoff work stayed at 70 percent.", "decision", "personal", False,
     [("Madcow 5x5", "method"), ("Starting Strength", "method"), ("conjugate", "method")],
     [("Madcow 5x5", "Starting Strength", "REPLACES")],
     "which intermediate template bridged Starting Strength to conjugate work and how did the weekly ramp close",
     "madcow 5x5 starting strength conjugate bridge ramp five rep 70 percent"),
    # --- 20 ---
    ("Smolov base mesocycle shredded the squat one-rep max by 22.5 kg over thirteen weeks; the second cycle with Smolov Jr. on bench added another 10 kg and knee recovery took a full month after.", "milestone", "personal", False,
     [("Smolov", "method"), ("Smolov Jr.", "method"), ("squat", "activity"), ("bench", "activity")],
     [("Smolov Jr.", "bench", "APPLIES_TO")],
     "how much did the Smolov squat block add and what follow-on cycle bumped the bench before recovery slowed",
     "smolov base mesocycle squat 22 5 kg thirteen week junior bench"),
    # --- 21 ---
    ("Velocity-based training with the Vitruve encoder flagged the bar speed dropping below 0.3 m/s on the final top set; that's the cue to cut the AMRAP and save recovery for the next session.", "architecture", "personal", False,
     [("Vitruve", "tool"), ("Velocity-based training", "concept"), ("AMRAP", "concept")],
     [("Vitruve", "Velocity-based training", "USES")],
     "which bar-speed threshold on the Vitruve encoder triggers an early cut of the AMRAP top set",
     "velocity based training vitruve encoder 0 3 m s amrap cut"),
    # --- 22 ---
    ("The Romanian deadlift now sits in the Tuesday slot with a three-second eccentric; the old stiff-leg variation strained the lower back at high percentages and got pulled from the block.", "decision", "personal", False,
     [("Romanian deadlift", "activity"), ("stiff-leg", "activity"), ("eccentric", "concept")],
     [("Romanian deadlift", "stiff-leg", "REPLACES")],
     "which hip-hinge accessory replaced the stiff-leg pull and what tempo cue landed in the Tuesday slot",
     "romanian deadlift tuesday three second eccentric stiff leg swap"),
    # --- 23 ---
    ("Front squat rotation started on alternate weeks to fix the thoracic collapse out of the hole; the zombie-grip variation for the first month locked in the upper-back position before rack grip returned.", "problem", "personal", False,
     [("Front squat", "activity"), ("zombie-grip", "pattern"), ("rack grip", "pattern"), ("thoracic collapse", "pattern")],
     [("Front squat", "thoracic collapse", "FIXES")],
     "how did the front squat rotation address the thoracic collapse and which grip variation came first",
     "front squat zombie grip rack thoracic collapse alternate week"),
    # --- 24 ---
    ("The 2 Board press with a slingshot is the Saturday lockout drill; the carryover to raw bench single has been about 5 kg over the block and the triceps loading stays heavy without wrist stress.", "architecture", "personal", False,
     [("2 Board press", "activity"), ("slingshot", "tool"), ("raw bench", "activity")],
     [("slingshot", "2 Board press", "APPLIES_TO")],
     "how does the 2 Board press with a slingshot slot into Saturday and what carryover shows up on raw bench",
     "2 board press slingshot saturday lockout raw bench 5 kg triceps"),
    # --- 25 ---
    ("A rotator-cuff flare-up after a heavy bench triple turned into an eight-week block on close-grip and floor press only; the arch position was reloading with a slingshot before full touch returned.", "problem", "personal", False,
     [("rotator-cuff", "concept"), ("close-grip", "activity"), ("floor press", "activity"), ("arch", "pattern"), ("slingshot", "tool")],
     [("close-grip", "rotator-cuff", "FIXES")],
     "how did the rotator-cuff flare-up reshape bench work for eight weeks and when did full touch return",
     "rotator cuff bench triple close grip floor press arch slingshot flare"),
    # --- 26 ---
    ("Coach Eric Helms's book The Muscle and Strength Pyramid Training laid out the volume hierarchy I now use: frequency before intensity before volume before exercise selection.", "reference", "personal", False,
     [("Eric Helms", "person"), ("The Muscle and Strength Pyramid Training", "publication")],
     [("The Muscle and Strength Pyramid Training", "Eric Helms", "AUTHORED_BY")],
     "which training hierarchy does the Helms pyramid book advocate and which resource is the source",
     "eric helms muscle strength pyramid training frequency intensity volume"),
    # --- 27 ---
    ("Stefi Cohen's 10X program stressed frequency with squat and deadlift touching four sessions each per week; the volume doubled my old PPL split and recovery demanded an extra sleep hour.", "decision", "personal", False,
     [("Stefi Cohen", "person"), ("10X", "method"), ("squat", "activity"), ("deadlift", "activity"), ("PPL", "method")],
     [("10X", "PPL", "REPLACES")],
     "how did Stefi Cohen's 10X program restructure weekly squat and deadlift frequency relative to the old PPL split",
     "stefi cohen 10x squat deadlift four session ppl frequency sleep"),
    # --- 28 ---
    ("The Texas Method weekly layout is volume Monday, light Wednesday, intensity Friday; the 5x5 at 90 percent on Monday built base then the intensity single on Friday set a new top each week.", "reference", "personal", False,
     [("Texas Method", "method"), ("intensity", "concept"), ("volume", "concept")],
     [("Texas Method", "intensity", "USES")],
     "how does the Texas Method split the weekly stress across Monday Wednesday and Friday sessions",
     "texas method volume monday light wednesday intensity friday 5x5"),
    # --- 29 ---
    ("The safety squat bar sits in the garage rack for heavy walkouts; the camber loads the upper back harder than the Texas Power Bar and builds the erector capacity that chased me off the last meet total.", "architecture", "personal", False,
     [("safety squat bar", "tool"), ("Texas Power Bar", "tool"), ("erector", "concept"), ("walkout", "activity")],
     [("safety squat bar", "Texas Power Bar", "REPLACES")],
     "which specialty bar replaced the Texas Power Bar for walkouts and which muscle group does the camber overload",
     "safety squat bar ssb camber walkout texas power bar erector upper"),
    # --- 30 ---
    ("Added the trap bar deadlift as a fourth pull per week; the high-handle variation cleans up a lower-back twinge that shows up on conventional pulls at the top end of the percentages.", "decision", "personal", False,
     [("trap bar", "tool"), ("deadlift", "activity"), ("conventional", "pattern"), ("high-handle", "pattern")],
     [("trap bar", "conventional", "REPLACES")],
     "how did the trap bar deadlift land as a fourth weekly pull and what issue on conventional did it address",
     "trap bar deadlift high handle fourth pull conventional twinge week"),
    # --- 31 ---
    ("The Coan/Philippi deadlift routine by Ed Coan and Mark Philippi runs ten weeks of RPE-gated pulls; the week-seven triple at 90 percent is the classic make-or-break session and I cut the AMRAP when the speed drops below spec.", "reference", "personal", False,
     [("Coan/Philippi", "method"), ("Ed Coan", "person"), ("deadlift", "activity"), ("AMRAP", "concept")],
     [("Coan/Philippi", "Ed Coan", "AUTHORED_BY")],
     "which legendary deadlift template spans ten weeks of RPE-gated pulls and what week is the make-or-break session",
     "coan philippi deadlift ten week rpe gate triple 90 percent amrap"),
    # --- 32 ---
    ("The football bar sits as the Thursday pressing option; the neutral grip angles saved the elbows during a tendinitis block and the pec hit stayed high without the straight-bar wrist strain.", "problem", "personal", False,
     [("football bar", "tool"), ("tendinitis", "concept"), ("neutral grip", "pattern"), ("straight-bar", "pattern")],
     [("football bar", "tendinitis", "FIXES")],
     "how did the football bar address the elbow tendinitis block without dropping pressing volume",
     "football bar thursday press neutral grip tendinitis elbow wrist"),
    # --- 33 ---
    ("Cronometer tracks the daily macros at 180 g protein, 60 g fat, and 380 g carbs on heavy days; the cut blocks keep protein flat and trim carbs to 220 g to preserve gym performance.", "fact", "personal", False,
     [("Cronometer", "tool"), ("protein", "concept"), ("carbs", "concept")],
     [],
     "which macro splits does the Cronometer log keep across heavy days and cut blocks for gym performance",
     "cronometer macro 180 protein 60 fat 380 carb cut 220 heavy day"),
    # --- 34 ---
    ("Mark Rippetoe's Practical Programming for Strength Training explains the novice-intermediate-advanced progression frames I use to pick templates; each frame maps to a different recovery window.", "reference", "personal", False,
     [("Mark Rippetoe", "person"), ("Practical Programming for Strength Training", "publication")],
     [("Practical Programming for Strength Training", "Mark Rippetoe", "AUTHORED_BY")],
     "which Rippetoe book defines the novice-intermediate-advanced frames that drive template selection",
     "mark rippetoe practical programming strength training novice advanced"),
    # --- 35 ---
    ("The Russian Squat Routine from Smolov's lineage ran as a twelve-week block with squats three times weekly; the volume in weeks four to seven broke the 170 kg barrier on a paused single.", "milestone", "personal", False,
     [("Russian Squat Routine", "method"), ("Smolov", "method"), ("paused single", "activity"), ("squat", "activity")],
     [("Russian Squat Routine", "Smolov", "USES")],
     "how did the Russian Squat Routine block close out the twelve weeks and which squat variation set the PR",
     "russian squat routine twelve week smolov 170 paused single three"),
    # --- 36 ---
    ("Signed up for the WRPF Showdown in November for a first multi-ply meet; the loose gear rules let me pull the Inzer SDP briefs into the squat, which changed the groove above 85 percent.", "milestone", "personal", False,
     [("WRPF", "organization"), ("Inzer SDP", "tool"), ("Showdown", "event"), ("multi-ply", "concept")],
     [("WRPF", "Showdown", "APPLIES_TO")],
     "which federation and meet booked the first multi-ply outing and what squat gear change came with it",
     "wrpf showdown november multi ply inzer sdp brief squat groove"),
    # --- 37 ---
    ("Wrist wraps are IronBull strongman 36 inch for the heavy bench singles; the stiffer wrap drops wrist flex under a 180 kg bar and reuses the same stack as the log press on strongman days.", "preference", "personal", False,
     [("IronBull", "tool"), ("Wrist wraps", "tool"), ("bench", "activity"), ("log press", "activity")],
     [],
     "which wrist wrap spec handles heavy bench singles and which strongman event shares the same wrap",
     "ironbull strongman 36 inch wrist wrap bench 180 kg log press"),
    # --- 38 ---
    ("Moved from a 5-day Upper/Lower split to a 6-day PPL for the hypertrophy block; the extra exposure on chest and back per week pushed muscle measurements up across eight weeks.", "decision", "personal", False,
     [("Upper/Lower", "method"), ("PPL", "method"), ("hypertrophy", "concept")],
     [("PPL", "Upper/Lower", "REPLACES")],
     "which split replaced the Upper/Lower structure for the hypertrophy block and how long did the block run",
     "upper lower 5 day ppl 6 day push pull leg hypertrophy eight week"),
    # --- 39 ---
    ("Knee pain after a heavy high-bar block resolved with two weeks of Cissus supplementation and a return to low-bar; the pain recurred only when the bar path drifted forward out of the hole.", "milestone", "personal", False,
     [("high-bar", "pattern"), ("low-bar", "pattern"), ("Cissus", "tool"), ("bar path", "concept")],
     [("low-bar", "high-bar", "REPLACES")],
     "how did the knee pain from a high-bar block resolve and what bar-path pattern brought it back",
     "knee pain high bar cissus low bar two week recur bar path forward"),
    # --- 40 ---
    ("The daily undulating layout rotates hypertrophy, strength, and power work across Monday Wednesday Friday; the RPE cap floats from 7 on power day to 9 on the strength single for managed fatigue.", "architecture", "personal", False,
     [("daily undulating", "method"), ("hypertrophy", "concept"), ("strength", "concept"), ("RPE", "concept")],
     [("daily undulating", "RPE", "USES")],
     "how is the weekly work split in the daily undulating layout and what RPE caps define each day",
     "daily undulating monday wednesday friday hypertrophy power rpe 7 9"),
    # --- 41 ---
    ("The paused bench at a two-count is the competition-standard cue I drill every Monday; the old touch-and-go style only returned for the Friday speed work after the paused version became automatic.", "architecture", "personal", False,
     [("paused bench", "activity"), ("touch-and-go", "pattern")],
     [("paused bench", "touch-and-go", "REPLACES")],
     "which bench variation owns Monday and where did touch-and-go retreat to in the weekly layout",
     "paused bench two count monday touch and go friday speed automatic"),
    # --- 42 ---
    ("Form-check video review with Coach Brett Gibbs over Zoom runs every two weeks; the last session flagged the hips shooting up first on the deadlift and prescribed wide-grip paused pulls.", "fact", "personal", False,
     [("Brett Gibbs", "person"), ("Zoom", "tool"), ("wide-grip paused pull", "activity"), ("deadlift", "activity")],
     [("Brett Gibbs", "wide-grip paused pull", "APPLIES_TO")],
     "which coach reviews the form-check videos and what fix landed for the deadlift hip-shoot this cycle",
     "brett gibbs zoom form check deadlift hip shoot wide grip paused"),
    # --- 43. noise ---
    ("The garage heater finally quit mid-February and I lifted in three hoodies for a week waiting for the replacement thermostat to ship.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Chalk moved from liquid to block after the liquid chalk evaporated off between warmup and top set; the block from Spider Chalk lasted the whole deadlift meet day and the grip held on the 240 kg pull.", "decision", "personal", False,
     [("Spider Chalk", "tool"), ("liquid chalk", "tool"), ("block", "tool"), ("deadlift", "activity")],
     [("block", "liquid chalk", "REPLACES")],
     "which chalk format replaced liquid chalk on meet day and what pull did it hold for",
     "spider chalk block liquid warmup evaporate 240 kg deadlift meet"),
    # --- 45 ---
    ("GZCL's method splits the week into T1 heavy main work, T2 moderate variations, and T3 high-rep accessories; the 10 percent rule keeps T3 volume honest when fatigue starts to pile up.", "reference", "personal", False,
     [("GZCL", "method"), ("T1", "concept"), ("T2", "concept"), ("T3", "concept")],
     [("GZCL", "T1", "USES")],
     "how does the GZCL method tier weekly work across T1 T2 and T3 and which rule gates T3 volume",
     "gzcl method t1 t2 t3 heavy moderate accessory 10 percent rule"),
    # --- 46 ---
    ("The Sheiko Prep 37 cycle plans bench and squat three times each week with competition-grip pauses on every bench session; the density is brutal but technique locks in by week four.", "reference", "personal", False,
     [("Sheiko Prep 37", "method"), ("bench", "activity"), ("squat", "activity"), ("competition-grip", "pattern")],
     [],
     "how does Sheiko Prep 37 distribute bench and squat work weekly and when does technique consolidate",
     "sheiko prep 37 bench squat three time week pause competition grip"),
    # --- 47 ---
    ("The Inzer SDP squat briefs need two people and a shower of baby powder to get on; the groove above 85 percent is dramatically different and the first session in them felt like learning the squat again.", "fact", "personal", False,
     [("Inzer SDP", "tool"), ("squat briefs", "tool"), ("squat", "activity")],
     [],
     "which squat briefs reshape the groove above 85 percent and what prep ritual is required to put them on",
     "inzer sdp squat brief two person baby powder 85 percent groove"),
    # --- 48 ---
    ("Block periodisation out of the Issurin text drives the current meet prep: four weeks accumulation, three weeks transmutation, two weeks realisation before a taper week and the platform.", "architecture", "personal", False,
     [("Block periodisation", "method"), ("Issurin", "person"), ("accumulation", "concept"), ("transmutation", "concept"), ("realisation", "concept")],
     [("Block periodisation", "Issurin", "AUTHORED_BY")],
     "how is the meet prep structured under Issurin's block periodisation and what phases precede the taper",
     "block periodisation issurin accumulation transmutation realisation meet"),
    # --- 49 ---
    ("The Rogue Ohio Deadlift Bar replaced the standard power bar for pulling sessions; the extra whip and the aggressive knurl in the sleeve section add about 5 kg to the first-pull break off the floor.", "milestone", "personal", False,
     [("Rogue Ohio Deadlift Bar", "tool"), ("power bar", "tool")],
     [("Rogue Ohio Deadlift Bar", "power bar", "REPLACES")],
     "which specialised bar replaced the power bar for pulls and how much did the first-pull break improve",
     "rogue ohio deadlift bar power whip knurl first pull 5 kg floor"),
    # --- 50 ---
    ("Competition day taper drops volume 50 percent eight days out and holds intensity at 85 percent for the openers rehearsal; the Issurin realisation phase shape matches and recovery lands right on meet morning.", "architecture", "personal", False,
     [("taper", "concept"), ("Issurin", "person"), ("realisation", "concept"), ("openers", "concept")],
     [("taper", "realisation", "APPLIES_TO")],
     "how does the eight-day taper split volume and intensity in the lead-up to opener rehearsals on meet day",
     "taper eight day volume 50 percent intensity 85 issurin realisation"),
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
