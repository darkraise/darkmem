"""One-off emitter for shared-base batch-064 — cross domain.

Slice: fitness and quantified-self meets tech (wearables, training apps, sleep
trackers, indoor cycling, dashboards). Writes 50 rows to
data/v2/shared/batch_064.tmp.jsonl with ids shared-03151..03200. The main
session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_064.tmp.jsonl"
ID_OFFSET = 3150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the Fitbit Charge 6 for a Garmin Forerunner 965 on 2026-02-08 because the daily training-readiness score actually pulled HRV from the night before, while the Fitbit version felt like a toy.", "decision", "cross", False,
     [("Fitbit Charge 6", "infrastructure"), ("Garmin Forerunner 965", "infrastructure"), ("2026-02-08", "date"), ("HRV", "concept")],
     [("Garmin Forerunner 965", "Fitbit Charge 6", "REPLACES")],
     "when did the daily wrist wearable change and what tipped the scales",
     "wearable swap training readiness heart rate variability daily score"),
    # --- 2 ---
    ("Strava replaced MapMyRun for the marathon block because the Garmin auto-upload landed splits in Strava within seconds while MapMyRun still wanted a manual sync from the watch.", "decision", "cross", False,
     [("Strava", "service"), ("MapMyRun", "service"), ("Garmin", "infrastructure")],
     [("Strava", "MapMyRun", "IMPROVES_ON"), ("Garmin", "Strava", "COMMUNICATES_WITH")],
     "which run-tracking platform took over for the marathon training block",
     "run tracking auto upload split sync watch upload pipeline"),
    # --- 3 ---
    ("The Oura Ring Gen 4 replaced the Whoop 4.0 strap on 2026-01-15 once the no-subscription tier launched and the wrist strap chafed under the Apple Watch on long runs.", "decision", "cross", False,
     [("Oura Ring Gen 4", "infrastructure"), ("Whoop 4.0", "infrastructure"), ("2026-01-15", "date"), ("Apple Watch", "infrastructure")],
     [("Oura Ring Gen 4", "Whoop 4.0", "REPLACES")],
     "why did the recovery tracker swap from a strap to a ring",
     "ring versus strap recovery tracker subscription tier wrist comfort"),
    # --- 4 ---
    ("Zwift on the Wahoo Kickr Core handled the indoor cycling base block over the winter because the ERG mode held the Coach Jack workout target wattage even when my legs wanted to coast.", "architecture", "cross", False,
     [("Zwift", "service"), ("Wahoo Kickr Core", "infrastructure"), ("ERG", "concept"), ("Coach Jack", "service")],
     [("Zwift", "Wahoo Kickr Core", "USES")],
     "how did the winter base cycling block actually keep me on target",
     "indoor cycling smart trainer ERG mode workout structured target"),
    # --- 5 ---
    ("Suunto's TrainingPeaks export went stale once Coros Apex 2 Pro started pushing structured workouts via the EVOLab planner, so the Suunto entered the drawer.", "decision", "cross", False,
     [("Suunto", "infrastructure"), ("TrainingPeaks", "service"), ("Coros Apex 2 Pro", "infrastructure"), ("EVOLab", "service")],
     [("Coros Apex 2 Pro", "Suunto", "REPLACES")],
     "which watch took over for structured running workouts and why",
     "structured workout planner watch swap export pipeline drawer"),
    # --- 6. noise ---
    ("Hold on, let me think about this one for a moment.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Built a personal Grafana dashboard on a Raspberry Pi 5 that pulls Garmin Connect data through gcexport.py into Postgres because the Garmin web view buries weekly load trends.", "architecture", "cross", False,
     [("Grafana", "tool"), ("Raspberry Pi 5", "infrastructure"), ("Garmin Connect", "service"), ("gcexport.py", "file"), ("Postgres", "database")],
     [("Grafana", "Postgres", "USES"), ("gcexport.py", "Garmin Connect", "COMMUNICATES_WITH")],
     "where does the home training dashboard pull its data from and how",
     "self hosted dashboard home server export script training load"),
    # --- 8 ---
    ("Cronometer replaced MyFitnessPal for the cut on 2026-03-02 because the micronutrient breakdown actually flagged the magnesium gap that the cramps during long runs hinted at.", "decision", "cross", False,
     [("Cronometer", "service"), ("MyFitnessPal", "service"), ("2026-03-02", "date")],
     [("Cronometer", "MyFitnessPal", "REPLACES")],
     "when did the diet tracker change and what nutrient gap did it surface",
     "diet log app swap micronutrient tracking cramp deficiency cut phase"),
    # --- 9 ---
    ("The Whoop strap kept calling 6 hours of sleep restorative which clashed with how garbage I felt, while the Oura Ring caught the elevated resting heart rate from the wine-and-pizza Friday.", "problem", "cross", False,
     [("Whoop", "infrastructure"), ("Oura Ring", "infrastructure")],
     [("Oura Ring", "Whoop", "IMPROVES_ON")],
     "which sleep tracker actually matched how rough Saturday morning felt",
     "sleep score disagreement resting heart rate alcohol effect tracker"),
    # --- 10 ---
    ("Frustration boiled over when Garmin Connect lost three weeks of FIT files on 2026-02-19 after a sync collision between the Edge 1040 and the Forerunner 965 on the same account.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Garmin Connect", "service"), ("FIT", "concept"), ("2026-02-19", "date"), ("Edge 1040", "infrastructure"), ("Forerunner 965", "infrastructure")],
     [],
     "what blew up the Garmin sync history during February",
     "fit file loss sync collision multi device account corruption"),
    # --- 11 ---
    ("Prefers the Apple Health export over the Garmin Connect API because the XML dump captures the iPhone steps and the Garmin runs in one place that Datasette can ingest.", "preference", "cross", False,
     [("Apple Health", "service"), ("Garmin Connect", "api"), ("XML", "concept"), ("iPhone", "infrastructure"), ("Datasette", "tool")],
     [("Apple Health", "Garmin Connect", "PREFERS"), ("Datasette", "Apple Health", "USES")],
     "which export source feeds the personal fitness Datasette and why",
     "health data export consolidation phone steps watch run ingestion"),
    # --- 12 ---
    ("The 2026-04-05 Boston Marathon qualifier came in at 2:58:14 on the Coros Apex 2 Pro and the post-race Stryd power file lined up with TrainingPeaks within four watts.", "milestone", "cross", False,
     [("2026-04-05", "date"), ("Boston Marathon", "event"), ("Coros Apex 2 Pro", "infrastructure"), ("Stryd", "infrastructure"), ("TrainingPeaks", "service")],
     [("Stryd", "TrainingPeaks", "COMMUNICATES_WITH")],
     "when did the BQ marathon happen and how did the power numbers compare",
     "marathon qualifier finish time running power meter file alignment"),
    # --- 13 ---
    ("Pride hit hard the morning the Strava king-of-the-mountain on the Mount Diablo climb finally fell after eighteen months of Zwift winter base work paid off.", "milestone", "cross", False,
     [("Pride", "emotion"), ("Strava", "service"), ("Mount Diablo", "place"), ("Zwift", "service")],
     [("Strava", "Zwift", "RELATED_TO")],
     "what segment finally fell after the long indoor training base",
     "segment record outdoor climb winter base training payoff feeling"),
    # --- 14 ---
    ("The Hevy app replaced the paper notebook for the powerlifting block because the auto-progression for the 5/3/1 template handled the supplemental volume math I kept screwing up.", "decision", "cross", False,
     [("Hevy", "service"), ("5/3/1", "method")],
     [("Hevy", "5/3/1", "IMPLEMENTS")],
     "which app took over from the paper logbook for the strength cycle",
     "lifting log app template progression volume calculation strength"),
    # --- 15 ---
    ("Prefers the AutoSleep app over the native Apple Health sleep stages because AutoSleep correlates the Apple Watch SpO2 dips with the awakenings my partner Sara complained about.", "preference", "cross", False,
     [("AutoSleep", "service"), ("Apple Health", "service"), ("Apple Watch", "infrastructure"), ("SpO2", "concept"), ("Sara", "person")],
     [("AutoSleep", "Apple Health", "PREFERS")],
     "which sleep analyzer wins on the Apple stack and what corroborates it",
     "sleep stage correlation oxygen saturation apnea partner observation"),
    # --- 16 ---
    ("The Polar H10 chest strap kept beating the Apple Watch optical sensor for tempo runs because the wrist HR dropped 30 bpm on every footstrike-cadence collision.", "fact", "cross", False,
     [("Polar H10", "infrastructure"), ("Apple Watch", "infrastructure")],
     [("Polar H10", "Apple Watch", "IMPROVES_ON")],
     "why does the chest strap still win for tempo workouts on the wrist",
     "optical heart rate cadence lock chest strap tempo workout drift"),
    # --- 17 ---
    ("Anxiety crept in when the Whoop strain-coach insisted on a 14.0 day after I had already booked the Saturday long run, and ignoring it tanked the Sunday brick session.", "problem", "cross", False,
     [("Anxiety", "emotion"), ("Whoop", "infrastructure")],
     [],
     "what happened when the strain coach got overruled before the long run",
     "strain target overshoot consecutive workout failure recovery debt"),
    # --- 18 ---
    ("The Eight Sleep Pod 4 paired with the Oura Ring on 2026-03-12 so the bed temperature schedule shifts an hour earlier when Oura predicts a low readiness score.", "architecture", "cross", False,
     [("Eight Sleep Pod 4", "infrastructure"), ("Oura Ring", "infrastructure"), ("2026-03-12", "date")],
     [("Eight Sleep Pod 4", "Oura Ring", "COMMUNICATES_WITH")],
     "how did the smart mattress start reacting to the recovery score",
     "smart mattress temperature schedule recovery score automation pairing"),
    # --- 19 ---
    ("Dropped Peloton on 2026-01-30 after the iFIT trial on the new NordicTrack treadmill paired cleanly with Garmin Connect and the monthly bill went from 44 to 0 dollars.", "decision", "cross", False,
     [("Peloton", "service"), ("2026-01-30", "date"), ("iFIT", "service"), ("NordicTrack", "infrastructure"), ("Garmin Connect", "service")],
     [("iFIT", "Peloton", "REPLACES")],
     "when did the gym app subscription get cut and what hardware enabled it",
     "gym app subscription cancellation treadmill equipment pairing savings"),
    # --- 20 ---
    ("MyFitnessPal's barcode scanner finally choked on the German muesli imports during the 2026-03 Berlin trip, so Yazio took over because its EU food database actually had the Müsli SKUs.", "decision", "cross", False,
     [("MyFitnessPal", "service"), ("2026-03", "date"), ("Berlin", "place"), ("Yazio", "service"), ("Müsli", "food")],
     [("Yazio", "MyFitnessPal", "REPLACES")],
     "which diet tracker took over for European travel and why",
     "diet app travel barcode database regional food coverage europe"),
    # --- 21 ---
    ("Pressure-tested the Stryd power-pace model against the Coros Apex 2 Pro pace on the 2026-02-22 half marathon and the Stryd was 11 seconds closer to the actual finish-line clock.", "fact", "cross", False,
     [("Stryd", "infrastructure"), ("Coros Apex 2 Pro", "infrastructure"), ("2026-02-22", "date")],
     [("Stryd", "Coros Apex 2 Pro", "IMPROVES_ON")],
     "which pace model was more accurate during the late February half",
     "running power pace prediction half marathon finish accuracy"),
    # --- 22 ---
    ("The Final Surge plan from coach Marcus pulls into Garmin Connect via the TrainingPeaks bridge because Final Surge's direct Garmin push silently dropped on 2026-02-04.", "architecture", "cross", False,
     [("Final Surge", "service"), ("Marcus", "person"), ("Garmin Connect", "service"), ("TrainingPeaks", "service"), ("2026-02-04", "date")],
     [("Final Surge", "TrainingPeaks", "USES"), ("TrainingPeaks", "Garmin Connect", "COMMUNICATES_WITH")],
     "how does the coached plan reach the watch given the broken integration",
     "training plan delivery integration bridge coach workout sync failure"),
    # --- 23 ---
    ("HealthFit on the iPhone uploads the Apple Watch FIT files into Strava because Apple's native Strava integration drops the SpO2 stream during altitude runs in Park City.", "architecture", "cross", False,
     [("HealthFit", "service"), ("iPhone", "infrastructure"), ("Apple Watch", "infrastructure"), ("FIT", "concept"), ("Strava", "service"), ("SpO2", "concept"), ("Park City", "place")],
     [("HealthFit", "Strava", "COMMUNICATES_WITH")],
     "which bridge moves Apple Watch runs into Strava without losing oxygen data",
     "fit file converter altitude oxygen stream preservation ios bridge"),
    # --- 24 ---
    ("The intervals.icu fitness-and-fatigue chart replaced the Garmin Connect training-load view because the Banister model exposes the form trough five days before a peak race.", "preference", "cross", False,
     [("intervals.icu", "service"), ("Garmin Connect", "service"), ("Banister", "method")],
     [("intervals.icu", "Garmin Connect", "PREFERS"), ("intervals.icu", "Banister", "IMPLEMENTS")],
     "which load chart actually predicts when to taper for a race",
     "fitness fatigue model taper window form prediction load chart"),
    # --- 25 ---
    ("Built a Datasette dashboard on a $5 Hetzner box that ingests the Whoop API JSON nightly so the recovery scores live next to the Garmin VO2max for trend analysis.", "architecture", "cross", False,
     [("Datasette", "tool"), ("Hetzner", "organization"), ("Whoop", "api"), ("JSON", "concept"), ("Garmin", "infrastructure"), ("VO2max", "concept")],
     [("Datasette", "Whoop", "USES"), ("Datasette", "Hetzner", "DEPLOYED_ON")],
     "where do the recovery and aerobic metrics live for cross device analysis",
     "personal dashboard data ingestion recovery aerobic capacity trend"),
    # --- 26 ---
    ("Joy hit the moment the Oura Ring detected the pregnancy three weeks before the test confirmed it and the resting heart rate jump matched the published pattern.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Oura Ring", "infrastructure")],
     [],
     "what early signal did the recovery ring catch before the pregnancy test",
     "early biomarker resting heart rate pattern detection life event"),
    # --- 27 ---
    ("Replaced the Withings Body Scan with a Renpho Elis 2 because the Withings Health Mate stopped exporting raw bioimpedance to Apple Health after the 2026-01 firmware rollout.", "decision", "cross", False,
     [("Withings Body Scan", "infrastructure"), ("Renpho Elis 2", "infrastructure"), ("Withings Health Mate", "service"), ("Apple Health", "service"), ("2026-01", "date")],
     [("Renpho Elis 2", "Withings Body Scan", "REPLACES")],
     "why did the smart scale change and what firmware change caused it",
     "smart scale swap bioimpedance export firmware regression apple health"),
    # --- 28 ---
    ("The Concept2 RowErg PM5 ergdata file uploads to Strava through the Concept2 Logbook bridge but only after I scripted a Cron job on the home server because the Bluetooth handoff to the iPhone keeps timing out.", "problem", "cross", False,
     [("Concept2 RowErg", "infrastructure"), ("PM5", "infrastructure"), ("Strava", "service"), ("Concept2 Logbook", "service"), ("Cron", "tool"), ("iPhone", "infrastructure"), ("Bluetooth", "protocol")],
     [("Concept2 Logbook", "Strava", "COMMUNICATES_WITH")],
     "how does the rowing erg actually get its data into Strava reliably",
     "indoor rowing ergometer data sync cron job bluetooth flake home server"),
    # --- 29 ---
    ("Prefers the TrainerRoad adaptive plan over the Zwift training plan because TrainerRoad's machine-learning power-target adjustments respect the failed VO2max intervals from Tuesday.", "preference", "cross", False,
     [("TrainerRoad", "service"), ("Zwift", "service"), ("VO2max", "concept")],
     [("TrainerRoad", "Zwift", "PREFERS")],
     "which structured cycling plan adapts when the workouts go badly",
     "adaptive training plan workout failure handling power target adjust"),
    # --- 30 ---
    ("The Levels CGM trial on 2026-02-11 surprised me by pinning the post-run oatmeal spike at 180 mg/dL, which the Cronometer macro entry would never have caught.", "fact", "cross", False,
     [("Levels", "service"), ("CGM", "infrastructure"), ("2026-02-11", "date"), ("Cronometer", "service")],
     [],
     "what surprised me about the post-run breakfast during the glucose monitor trial",
     "continuous glucose monitor post exercise spike breakfast carb response"),
    # --- 31 ---
    ("The Garmin Edge 1040 Solar replaced the Wahoo Bolt v2 as the bike head unit because the ClimbPro feature surfaces the Mount Hamilton segment effort the Wahoo never knew was coming.", "decision", "cross", False,
     [("Garmin Edge 1040 Solar", "infrastructure"), ("Wahoo Bolt v2", "infrastructure"), ("ClimbPro", "service"), ("Mount Hamilton", "place")],
     [("Garmin Edge 1040 Solar", "Wahoo Bolt v2", "REPLACES")],
     "why did the bike computer change before the spring climbing block",
     "bike computer swap climb preview feature route effort prediction"),
    # --- 32 ---
    ("The Garmin Tactix 7 watch keeps the dive log alongside the run files which removed the Garmin Descent because one wrist replaced two devices for the 2026-04-22 Bonaire trip.", "decision", "cross", False,
     [("Garmin Tactix 7", "infrastructure"), ("Garmin Descent", "infrastructure"), ("2026-04-22", "date"), ("Bonaire", "place")],
     [("Garmin Tactix 7", "Garmin Descent", "REPLACES")],
     "which watch consolidated the dive and run setups before the trip",
     "multi sport watch consolidation dive log unification travel kit"),
    # --- 33 ---
    ("Pulled the Apple Health auto-export XML weekly into a DuckDB file on the M2 MacBook so the personal fitness analytics queries run in a notebook without needing the cloud.", "architecture", "cross", False,
     [("Apple Health", "service"), ("XML", "concept"), ("DuckDB", "database"), ("M2 MacBook", "infrastructure")],
     [("DuckDB", "Apple Health", "USES")],
     "where do the personal fitness analytics queries actually run now",
     "local analytics duckdb apple health export notebook query offline"),
    # --- 34. noise ---
    ("Let me circle back to that in a second.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Garmin Body Battery's drain prediction missed the 2026-03-08 sleep deprivation from the new puppy because the algorithm doesn't weight the 3am wake-ups when total time-in-bed stays high.", "problem", "cross", False,
     [("Garmin Body Battery", "service"), ("2026-03-08", "date")],
     [],
     "where did the energy gauge mislead during the puppy week",
     "energy gauge prediction failure fragmented sleep middle of night wake"),
    # --- 36 ---
    ("The Tonal smart-home gym subscription got canceled on 2026-02-28 because the Hevy plus a barbell rack covered every program the Tonal coach designed at a third of the monthly cost.", "decision", "cross", False,
     [("Tonal", "service"), ("2026-02-28", "date"), ("Hevy", "service")],
     [("Hevy", "Tonal", "REPLACES")],
     "when did the smart gym subscription get cut and what replaced it",
     "smart gym cancellation barbell traditional subscription savings"),
    # --- 37 ---
    ("The Coros training-hub pace zones beat Garmin's auto-detected zones because Coros locks the threshold to the recent lactate-test result instead of guessing from a 5K time trial.", "fact", "cross", False,
     [("Coros", "service"), ("Garmin", "service")],
     [("Coros", "Garmin", "IMPROVES_ON")],
     "which platform sets more honest pace zones for tempo work",
     "training zone calibration lactate threshold pace prediction accuracy"),
    # --- 38 ---
    ("The OpenWeightLifting CSV export combined with my brother Julian's Python script produces a Wilks-coefficient timeline that the Hevy app stubbornly refuses to render.", "fact", "cross", False,
     [("OpenWeightLifting", "service"), ("CSV", "concept"), ("Julian", "person"), ("Python", "language"), ("Wilks", "method"), ("Hevy", "service")],
     [("Julian", "Python", "USES")],
     "what custom tooling produces the strength comparison chart Hevy lacks",
     "lifting export custom analysis bodyweight coefficient timeline chart"),
    # --- 39 ---
    ("Apple Fitness+ replaced the Peloton App for the 2026-Q1 yoga rotation because the Apple Watch ring close at the end of class actually unifies with the rest of the day's activity goals.", "decision", "cross", False,
     [("Apple Fitness+", "service"), ("Peloton App", "service"), ("Apple Watch", "infrastructure")],
     [("Apple Fitness+", "Peloton App", "REPLACES")],
     "which streaming workout service won the yoga rotation this quarter",
     "yoga streaming workout service swap activity ring integration ecosystem"),
    # --- 40 ---
    ("The Wahoo TICKR X chest strap captures running cadence the wrist sensors keep guessing wrong, so it stays on for every track session even with the Polar H10 in the drawer as backup.", "preference", "cross", False,
     [("Wahoo TICKR X", "infrastructure"), ("Polar H10", "infrastructure")],
     [("Wahoo TICKR X", "Polar H10", "PREFERS")],
     "which chest strap stays in rotation for track work and what is the backup",
     "running cadence sensor accuracy track session backup hardware"),
    # --- 41 ---
    ("Curiosity drove the 2026-02-15 Veri CGM trial purchase to chase the post-workout window for the Boston block and the Veri app's overlay of run pace versus glucose finally connected.", "milestone", "cross", False,
     [("Curiosity", "emotion"), ("2026-02-15", "date"), ("Veri", "service"), ("CGM", "infrastructure"), ("Boston", "event")],
     [("Veri", "CGM", "USES")],
     "when did the glucose-and-running overlay finally start making sense",
     "continuous glucose monitor running overlay post workout window analysis"),
    # --- 42 ---
    ("The Polar Vantage V3 fell behind the Garmin ecosystem on connected bike-light integration so the Polar got listed on Backloop after the 2026-03-19 group ride embarrassment when the lights stayed on.", "milestone", "cross", False,
     [("Polar Vantage V3", "infrastructure"), ("Garmin", "infrastructure"), ("Backloop", "service"), ("2026-03-19", "date")],
     [("Garmin", "Polar Vantage V3", "IMPROVES_ON")],
     "what watch got sold off after the embarrassing group ride and why",
     "watch resale ecosystem accessory integration group ride bike light"),
    # --- 43 ---
    ("The Stryd Duo footpod pair landed on 2026-04-01 to capture left-right power balance because the gait tweak from the Marcus PT plan needed harder evidence than feel.", "milestone", "cross", False,
     [("Stryd Duo", "infrastructure"), ("2026-04-01", "date"), ("Marcus", "person")],
     [],
     "when did the running power gear upgrade happen and what motivated it",
     "running power balance asymmetry physical therapy gait change evidence"),
    # --- 44 ---
    ("Sara prefers the Strava Beacon live-tracking link over Garmin LiveTrack because Strava's URL works in iMessage previews while Garmin's link bounces off Sara's iPhone preview rendering.", "preference", "cross", False,
     [("Sara", "person"), ("Strava Beacon", "service"), ("Garmin LiveTrack", "service"), ("iMessage", "service"), ("iPhone", "infrastructure")],
     [("Strava Beacon", "Garmin LiveTrack", "PREFERS")],
     "which live tracking link does my partner prefer and why",
     "live tracking share link message preview rendering partner safety"),
    # --- 45 ---
    ("The Garmin Forerunner 965 firmware 14.10 on 2026-03-22 broke ANT+ pairing with the Stryd Duo, and the workaround was a hard reset documented in the dcrainmaker forum thread.", "problem", "cross", False,
     [("Garmin Forerunner 965", "infrastructure"), ("2026-03-22", "date"), ("ANT+", "protocol"), ("Stryd Duo", "infrastructure"), ("dcrainmaker", "publication")],
     [],
     "what broke after the late March watch firmware push",
     "firmware regression pairing failure protocol footpod hard reset workaround"),
    # --- 46 ---
    ("Goggles on, the Form Smart goggles replaced the Finis Tempo Trainer for pool work because the live pace heads-up display kept the 1500 meter set honest without needing a coach on deck.", "decision", "cross", False,
     [("Form Smart", "infrastructure"), ("Finis Tempo Trainer", "infrastructure")],
     [("Form Smart", "Finis Tempo Trainer", "REPLACES")],
     "which swim wearable took over for solo pool work this season",
     "swim wearable heads up display pace solo workout pool set integrity"),
    # --- 47 ---
    ("Determination kicked in for the 2026-05-30 Western States lottery target after the Suunto Wing bone-conduction headset finally let me listen to ultrarunning podcasts on the long runs without burying ambient sound.", "milestone", "cross", False,
     [("Determination", "emotion"), ("2026-05-30", "date"), ("Western States", "event"), ("Suunto Wing", "infrastructure")],
     [],
     "what gear addition supported the build toward the ultrarunning lottery target",
     "bone conduction headphones long run ambient awareness podcast ultra"),
    # --- 48 ---
    ("Shifted the Whoop charging cadence into a Home Assistant automation because the strap hitting 5% during the Tuesday gym session burned three weeks of strain history before I noticed.", "architecture", "cross", False,
     [("Whoop", "infrastructure"), ("Home Assistant", "platform")],
     [("Home Assistant", "Whoop", "CONFIGURES")],
     "where does the recovery strap charging schedule live now",
     "wearable charging automation home server data loss prevention strain"),
    # --- 49 ---
    ("The Friel Triathlete's Training Bible 5th edition still beats the TrainerRoad adaptive coach for periodization theory because the polarized intensity ladder maps cleanly onto the intervals.icu chart.", "reference", "cross", False,
     [("Friel", "person"), ("Triathlete's Training Bible", "publication"), ("TrainerRoad", "service"), ("intervals.icu", "service")],
     [("Triathlete's Training Bible", "Friel", "AUTHORED_BY")],
     "which periodization reference still wins over the algorithmic coach",
     "periodization theory book adaptive coach polarized intensity ladder"),
    # --- 50 ---
    ("Pride bubbled when the personal fitness Grafana finally surfaced a year-over-year VO2max climb from 51 to 58 on 2026-04-10 thanks to the Coros lab-test integration replacing the watch estimate.", "milestone", "cross", False,
     [("Pride", "emotion"), ("Grafana", "tool"), ("VO2max", "concept"), ("2026-04-10", "date"), ("Coros", "service")],
     [("Coros", "Grafana", "COMMUNICATES_WITH")],
     "when did the dashboard surface the year over year aerobic capacity gain",
     "year over year aerobic capacity dashboard lab test integration milestone"),
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
