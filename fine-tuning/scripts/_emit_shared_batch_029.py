"""One-off emitter for shared-base batch-029 — personal domain (health / wellness / medical slice).

Same pattern as _emit_shared_batch_015.py; only ENTRIES and offsets change.
Writes 50 rows to data/v2/shared/batch_029.tmp.jsonl with ids shared-01401..01450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_029.tmp.jsonl"
ID_OFFSET = 1400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The endocrinologist Dr. Patel adjusted the levothyroxine dose to 75 mcg on 2026-02-11 after the TSH came back at 4.8.", "milestone", "personal", False,
     [("Dr. Patel", "person"), ("levothyroxine", "concept"), ("2026-02-11", "date"), ("TSH", "finding")],
     [],
     "when did the thyroid specialist change my hormone tablet strength and why",
     "hormone clinician titration winter date lab value reason"),
    # --- 2 ---
    ("Swapped the melatonin nightcap for magnesium glycinate at 400 mg; sleep latency dropped from 40 minutes to under fifteen.", "decision", "personal", False,
     [("melatonin", "concept"), ("magnesium glycinate", "concept")],
     [("magnesium glycinate", "melatonin", "REPLACES")],
     "which mineral supplement took over from the pineal-hormone pill for winding down",
     "mineral chelate nightcap swap hormone pill sleep onset speed"),
    # --- 3 ---
    ("Oral allergy syndrome turns every raw apple into an itchy mouth; peeling and a quick microwave zap neutralises it.", "problem", "personal", False,
     [("Oral allergy syndrome", "concept"), ("apple", "food")],
     [],
     "which cross-reactive fruit reaction bothers me and what trick makes it eatable",
     "pollen fruit cross-reaction workaround heat peel"),
    # --- 4 ---
    ("The sleep study at St. Mary's on 2025-10-22 ruled out apnea and pointed at delayed sleep phase instead.", "reference", "personal", False,
     [("St. Mary's", "place"), ("2025-10-22", "date"), ("apnea", "finding"), ("delayed sleep phase", "finding")],
     [],
     "what did the overnight lab test at the hospital rule out and what did it flag",
     "overnight polysomnography outcome circadian shift diagnosis late year date"),
    # --- 5 ---
    ("Prefers the EMDR sessions with Dr. Okafor to the earlier CBT rounds; the trauma processing finally feels like it moves.", "preference", "personal", False,
     [("EMDR", "method"), ("Dr. Okafor", "person"), ("CBT", "method")],
     [("EMDR", "CBT", "PREFERS")],
     "which therapy modality with the current clinician actually outshines the earlier protocol",
     "eye-movement reprocessing over cognitive approach trauma progress clinician"),
    # --- 6 ---
    ("Started the 16:8 eating window on 2026-01-05; morning hunger faded after week three and the afternoon slump stopped.", "milestone", "personal", False,
     [("16:8", "method"), ("2026-01-05", "date")],
     [],
     "when did the daily time-restricted feeding run begin and how did the body settle",
     "eight-hour window start date adjustment hunger afternoon energy"),
    # --- 7 ---
    ("Dr. Lena the dermatologist put me on tretinoin 0.025% for the cystic jaw breakouts; see her again on 2026-05-04.", "fact", "personal", False,
     [("Dr. Lena", "person"), ("tretinoin", "concept"), ("2026-05-04", "date")],
     [],
     "which skin doctor prescribed the retinoid cream and when is the follow-up",
     "dermatology cystic jaw retinoid cream follow-up spring date"),
    # --- 8 ---
    ("The pelvic floor physio with Hana twice a week improved on the Kegel app routine; the leak-on-sneeze stopped by session eight.", "decision", "personal", False,
     [("pelvic floor physio", "activity"), ("Hana", "person"), ("Kegel app", "tool")],
     [("pelvic floor physio", "Kegel app", "IMPROVES_ON")],
     "which in-person pelvic routine outperformed the phone-app squeezes and how fast",
     "in-person pelvic clinician sessions outperform phone app squeezes"),
    # --- 9 ---
    ("The gut biome panel from Thryve on 2026-03-12 flagged low Akkermansia; added kefir and pomegranate daily as the action plan.", "milestone", "personal", False,
     [("gut biome panel", "method"), ("Thryve", "service"), ("2026-03-12", "date"), ("Akkermansia", "finding"), ("kefir", "food"), ("pomegranate", "food")],
     [],
     "when did the microbiome lab kit come back and what dietary response did I pick",
     "stool microbiome test result low mucin microbe ferment fruit plan"),
    # --- 10. noise ---
    ("Let me pull the lab portal up before we go on.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Dropped the ashwagandha after eight weeks; the morning grogginess outweighed the anxiety bump it gave me.", "decision", "personal", False,
     [("ashwagandha", "concept"), ("anxiety", "emotion")],
     [],
     "which adaptogen supplement did I stop after two months and why",
     "Indian ginseng discontinue grogginess anxiety trade-off window"),
    # --- 12 ---
    ("The new eyeglass prescription from Dr. Hoffman on 2026-03-24 went to -3.75 left and -4.00 right; blue-light coating added.", "fact", "personal", False,
     [("Dr. Hoffman", "person"), ("2026-03-24", "date")],
     [],
     "when did the optometrist update my lens numbers and what extra coating went on",
     "optometry spring date diopter update screen filter coating add"),
    # --- 13 ---
    ("Prefers the Dexcom G7 patch on the upper arm to finger-prick strips; continuous data changed how I eat pasta entirely.", "preference", "personal", False,
     [("Dexcom G7", "technology"), ("finger-prick strips", "tool"), ("pasta", "food")],
     [("Dexcom G7", "finger-prick strips", "PREFERS")],
     "which glucose-reading hardware took over from the lancet method and what did it change",
     "continuous sensor arm patch lancet strip swap carb food shift"),
    # --- 14 ---
    ("The dental implant on tooth 19 was placed on 2025-09-30 at the Halsted clinic; integration check is on 2026-06-01.", "milestone", "personal", False,
     [("tooth 19", "concept"), ("2025-09-30", "date"), ("Halsted clinic", "place"), ("2026-06-01", "date")],
     [],
     "when was the lower molar titanium fixture placed and when is the bone-integration review",
     "lower molar fixture placement clinic autumn review summer date"),
    # --- 15 ---
    ("Asthma flared during the wildfire smoke week; the rescue inhaler went from once-a-month to four times a day.", "problem", "personal", False,
     [("Asthma", "finding"), ("wildfire smoke", "concept"), ("rescue inhaler", "tool")],
     [],
     "which respiratory condition flared in the smoky stretch and how did the inhaler use change",
     "reactive airway smoke haze short-acting puffer frequency spike week"),
    # --- 16 ---
    ("Prefers the stand-up desk with the under-desk treadmill to the seated setup; back pain halved within a month.", "preference", "personal", False,
     [("stand-up desk", "tool"), ("under-desk treadmill", "tool"), ("seated setup", "tool")],
     [("stand-up desk", "seated setup", "PREFERS")],
     "which work-surface configuration took over from sitting and what did the back feel",
     "vertical desk walking belt replace chair posture relief month span"),
    # --- 17 ---
    ("Started the Alexander Technique lessons with Marcus on 2026-02-24; neck tension from laptop work eased by lesson four.", "milestone", "personal", False,
     [("Alexander Technique", "method"), ("Marcus", "person"), ("2026-02-24", "date")],
     [],
     "when did the posture re-education lessons start and whose was it",
     "postural re-education teacher start late winter neck unwind"),
    # --- 18 ---
    ("Dropped IBS flares by 70% after the low-FODMAP reintroduction pinned onion and wheat as the triggers; garlic is fine.", "reference", "personal", False,
     [("IBS", "finding"), ("low-FODMAP", "method"), ("onion", "food"), ("wheat", "food"), ("garlic", "food")],
     [],
     "which gut condition settled after the structured diet test and which two foods came out as the culprits",
     "irritable bowel protocol elimination outcome two culprit foods allowed one"),
    # --- 19 ---
    ("Switched primary care from Dr. Novak to Dr. Aziz after the second missed referral; labs already transferred.", "decision", "personal", False,
     [("Dr. Novak", "person"), ("Dr. Aziz", "person")],
     [("Dr. Aziz", "Dr. Novak", "REPLACES")],
     "which general practitioner took over my file and what forced the move",
     "primary doctor handover trigger missed consult referral transfer records"),
    # --- 20 ---
    ("The allergy skin-prick panel on 2026-03-07 confirmed ragweed, dust mite, and cat dander as the big three triggers.", "reference", "personal", False,
     [("allergy skin-prick panel", "method"), ("2026-03-07", "date"), ("ragweed", "finding"), ("dust mite", "finding"), ("cat dander", "finding")],
     [],
     "when did the allergist test come back and which three triggers lit up",
     "skin-prick allergist result early spring three trigger airborne animal"),
    # --- 21 ---
    ("The CGM data changed breakfast: steel-cut oats replaced the banana smoothie; post-meal glucose went from 180 to 125.", "decision", "personal", False,
     [("CGM", "tool"), ("steel-cut oats", "food"), ("banana smoothie", "food")],
     [("steel-cut oats", "banana smoothie", "REPLACES")],
     "which morning food swap came out of the sensor data and what did the glucose do",
     "continuous monitor morning food swap oat fruit blend glucose drop"),
    # --- 22 ---
    ("Prefers the FreeStyle Libre over the Dexcom for the long wear time; swapped brands on 2026-01-18 after two months of trials.", "preference", "personal", False,
     [("FreeStyle Libre", "technology"), ("Dexcom", "technology"), ("2026-01-18", "date")],
     [("FreeStyle Libre", "Dexcom", "PREFERS")],
     "which continuous glucose brand did I pick at the end of the comparison and when",
     "fortnight sensor over weekly sensor wear time winter switch date"),
    # --- 23 ---
    ("The annual flu shot and shingles part-two dose are booked at the Wellspring pharmacy for 2026-04-28.", "fact", "personal", False,
     [("flu shot", "event"), ("shingles", "concept"), ("Wellspring pharmacy", "place"), ("2026-04-28", "date")],
     [],
     "which two vaccinations are queued at the pharmacy and on what date",
     "seasonal respiratory plus varicella booster pharmacy late April date"),
    # --- 24 ---
    ("The perimenopause hormone panel on 2026-01-30 put FSH at 32; Dr. Haddad suggested topical estradiol on the forearms.", "milestone", "personal", False,
     [("perimenopause", "concept"), ("FSH", "concept"), ("2026-01-30", "date"), ("Dr. Haddad", "person"), ("estradiol", "concept")],
     [],
     "when did the hormone transition labs come back and what topical did the gynaecologist suggest",
     "mid-life hormone transition lab winter date arm cream clinician plan"),
    # --- 25 ---
    ("The hearing test at Amplifon on 2025-11-14 showed mild high-frequency loss on the right; no device yet, retest in a year.", "fact", "personal", False,
     [("Amplifon", "place"), ("2025-11-14", "date")],
     [],
     "when did the audiology test happen and what did the right-ear result show",
     "audiology shop late autumn date right ear high pitch drop outcome"),
    # --- 26 ---
    ("Replaced the daily coffee with matcha after the heart-rate variability data showed better recovery scores on the tea days.", "decision", "personal", False,
     [("coffee", "food"), ("matcha", "food"), ("heart-rate variability", "finding")],
     [("matcha", "coffee", "REPLACES")],
     "which morning caffeine swap came out of the HRV tracking and what drove it",
     "bean brew to powdered leaf swap autonomic data recovery score"),
    # --- 27 ---
    ("The fertility work-up at Reproductive Partners on 2026-02-02 confirmed normal AMH at 2.1; the IVF plan pauses for three more months.", "reference", "personal", False,
     [("Reproductive Partners", "place"), ("2026-02-02", "date"), ("AMH", "finding"), ("IVF", "method")],
     [],
     "when did the reproductive clinic work-up happen and what did the ovarian reserve marker say",
     "reproductive clinic winter date ovarian reserve hormone outcome plan pause"),
    # --- 28 ---
    ("The sleep-tracking ring is a Oura Gen 4; wearing it on the index finger gave cleaner data than the ring finger.", "architecture", "personal", False,
     [("Oura Gen 4", "technology"), ("index finger", "concept"), ("ring finger", "concept")],
     [("index finger", "ring finger", "PREFERS")],
     "which finger gives the ring-tracker the best signal on my hand",
     "fourth-gen ring tracker digit placement signal quality hand"),
    # --- 29 ---
    ("Prefers the ACT group at Mindspace on Thursday nights to the solo CBT app; the accountability piece makes the exercises stick.", "preference", "personal", False,
     [("ACT group", "activity"), ("Mindspace", "organization"), ("CBT app", "platform")],
     [("ACT group", "CBT app", "PREFERS")],
     "which acceptance-commitment gathering outshines the solo phone tool and why",
     "Thursday night peer circle mindfulness venue stickiness peer presence"),
    # --- 30 ---
    ("The physio for plantar fasciitis with Jamal ran eight weeks; the frozen-bottle rollout and eccentric calf drops did most of the work.", "milestone", "personal", False,
     [("plantar fasciitis", "concept"), ("Jamal", "person"), ("eccentric calf drops", "activity")],
     [],
     "how long did the heel-pain rehab run and what were the two workhorse exercises",
     "foot fascia rehab duration cold roller calf eccentric drill"),
    # --- 31 ---
    ("Hydration rule: 500 ml on waking, 750 ml between breakfast and lunch; the afternoon headaches mostly vanished inside a week.", "architecture", "personal", False,
     [("Hydration rule", "method")],
     [],
     "what two-slot morning water protocol cleared the afternoon head pain",
     "wake half-litre pre-noon three-quarter litre rule head pain drop"),
    # --- 32 ---
    ("The creatine 5 g trial for eight weeks lifted the deadlift 10 kg and the memory tests nudged up too; keeping it indefinitely.", "decision", "personal", False,
     [("creatine", "concept"), ("deadlift", "goal")],
     [],
     "what two-month supplement run boosted both lifting and cognition",
     "monohydrate powder trial lift gain cognitive bump keep long-term"),
    # --- 33 ---
    ("The cardiologist ordered a 24-hour Holter monitor for the palpitations; pickup at Meridian Heart on 2026-04-19.", "fact", "personal", False,
     [("cardiologist", "person"), ("Holter monitor", "tool"), ("palpitations", "finding"), ("Meridian Heart", "place"), ("2026-04-19", "date")],
     [],
     "which heart specialist kit do I pick up and where is it happening",
     "heart doctor day-long ECG recorder pickup clinic late April date"),
    # --- 34. noise ---
    ("Hmm, let me check the referral form first.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Prefers the slow-release iron bisglycinate to the ferrous sulphate tablets; the stomach upset finally stopped and ferritin climbed from 12 to 48.", "preference", "personal", False,
     [("iron bisglycinate", "concept"), ("ferrous sulphate", "concept"), ("ferritin", "finding")],
     [("iron bisglycinate", "ferrous sulphate", "PREFERS")],
     "which iron form took over from the older salt and what did the stores do",
     "chelated iron over classic sulphate stomach tolerance storage protein climb"),
    # --- 36 ---
    ("Quit the OMAD trial after two weeks on 2025-12-15; evening binges were cancelling the deficit and sleep tanked.", "problem", "personal", False,
     [("OMAD", "method"), ("2025-12-15", "date")],
     [],
     "when did the one-meal-a-day experiment end and what broke it",
     "single-meal protocol abandon December date binge rebound sleep drop"),
    # --- 37 ---
    ("The knee-to-hip strength imbalance the physio flagged is the likely cause of the IT band flare-ups; single-leg bridges daily.", "reference", "personal", False,
     [("IT band", "concept"), ("single-leg bridges", "activity")],
     [],
     "what lower-body strength gap explains the lateral leg band flare-ups",
     "lateral leg band flare-up glute weakness single-sided bridge daily"),
    # --- 38 ---
    ("The colonoscopy on 2026-03-20 was clean; next screening pushed to 2036 given the family history is paternal, not direct.", "milestone", "personal", False,
     [("colonoscopy", "method"), ("2026-03-20", "date"), ("2036", "date")],
     [],
     "when was the lower-GI screen and how far out is the next one",
     "lower GI screen spring date ten-year interval family risk tier"),
    # --- 39 ---
    ("The meditation app Waking Up replaced Calm after the free-trial sampler; the Sam Harris intro course pulled me in.", "decision", "personal", False,
     [("Waking Up", "platform"), ("Calm", "platform"), ("Sam Harris", "person")],
     [("Waking Up", "Calm", "REPLACES")],
     "which mindfulness app took over from the older one and who nudged the switch",
     "meditation app swap primary secondary author intro course trigger"),
    # --- 40 ---
    ("The full-dairy elimination for six weeks cleared the chronic sinus drip; reintroducing yogurt was fine, hard cheese brought it right back.", "reference", "personal", False,
     [("full-dairy elimination", "method"), ("yogurt", "food"), ("hard cheese", "food")],
     [],
     "which food-group cut resolved the sinus issue and which specific reintroduction broke it again",
     "dairy cut sinus clear reintroduction tolerant item aged trigger"),
    # --- 41 ---
    ("Caffeine cutoff moved from 14:00 to 11:00 on 2026-01-22; deep-sleep minutes on the ring went from 58 to 92 inside a fortnight.", "decision", "personal", False,
     [("Caffeine cutoff", "method"), ("14:00", "date"), ("11:00", "date"), ("2026-01-22", "date")],
     [],
     "when did the coffee curfew get pulled earlier and what did deep sleep do",
     "caffeine curfew shift earlier winter date slow-wave sleep minutes jump"),
    # --- 42 ---
    ("The migraine prevention with propranolol 40 mg twice daily started on 2026-02-05; headaches dropped from eight a month to two.", "milestone", "personal", False,
     [("migraine", "finding"), ("propranolol", "concept"), ("2026-02-05", "date")],
     [],
     "when did the beta-blocker preventative regimen begin and how did the headache count change",
     "beta blocker preventative start late winter date headache frequency fall"),
    # --- 43 ---
    ("Prefers the nose-breathing tape at night to the mouth guard; dry-mouth mornings went away and the partner-reported snoring stopped too.", "preference", "personal", False,
     [("nose-breathing tape", "tool"), ("mouth guard", "tool")],
     [("nose-breathing tape", "mouth guard", "PREFERS")],
     "which overnight mouth-intervention took over from the older appliance and what changed",
     "mouth-closure strip over dental splint dry palate morning snoring"),
    # --- 44 ---
    ("The shoulder impingement from bench pressing cost four physio sessions and a six-week deload; Dr. Voss cleared me on 2026-03-28.", "problem", "personal", False,
     [("shoulder impingement", "finding"), ("bench pressing", "activity"), ("Dr. Voss", "person"), ("2026-03-28", "date")],
     [],
     "which upper-body injury from pressing led to a rehab stint and when was I cleared",
     "press-induced upper arm joint issue rehab deload clear spring date"),
    # --- 45 ---
    ("Prefers the real-food electrolyte mix — salt, lime, coconut water — over LMNT packets for the long trail runs.", "preference", "personal", False,
     [("salt", "food"), ("lime", "food"), ("coconut water", "food"), ("LMNT", "service")],
     [("coconut water", "LMNT", "PREFERS")],
     "which homemade trail electrolyte recipe beats the commercial powder for long runs",
     "salt citrus tropical water mix over brand electrolyte sachet endurance"),
    # --- 46 ---
    ("The bone-density scan on 2026-02-26 put the hip T-score at -1.8; Dr. Haddad added weighted vest walks twice a week.", "milestone", "personal", False,
     [("bone-density scan", "method"), ("2026-02-26", "date"), ("T-score", "finding"), ("Dr. Haddad", "person"), ("weighted vest walks", "activity")],
     [],
     "when did the DEXA come back and what new loading activity did the clinician add",
     "DEXA winter date osteopenia range vest loaded walk weekly plan"),
    # --- 47 ---
    ("Blood-pressure rule at home: morning reading within five minutes of waking, seated, arm supported; averages dropped from 138 to 124 once the method settled.", "architecture", "personal", False,
     [("Blood-pressure rule", "method")],
     [],
     "what consistent morning measurement protocol took my home readings down",
     "morning BP technique rigor seated arm support baseline drop"),
    # --- 48 ---
    ("The acupuncture sessions with Wei for the lower-back spasms improved on the TENS unit the chiropractor lent me; six sessions and the spasms stopped.", "decision", "personal", False,
     [("acupuncture", "method"), ("Wei", "person"), ("lower-back spasms", "finding"), ("TENS unit", "tool")],
     [("acupuncture", "TENS unit", "IMPROVES_ON")],
     "which needle-based treatment outperformed the electrical device for the lower back",
     "fine-needle treatment over electrical stimulator lumbar spasm clinician"),
    # --- 49 ---
    ("The vitamin D level came back at 22 ng/mL on 2026-01-09; supplementing 4000 IU daily brought it to 48 by the April recheck.", "reference", "personal", False,
     [("vitamin D", "finding"), ("2026-01-09", "date")],
     [],
     "what was the winter serum D level and where did it land after three months of supplementing",
     "serum D low winter baseline four-thousand IU dose spring recheck climb"),
    # --- 50 ---
    ("Prefers the morning daylight walk inside thirty minutes of waking to the lightbox session; mood and sleep timing both behaved better on the outdoor days.", "preference", "personal", False,
     [("morning daylight walk", "activity"), ("lightbox", "tool")],
     [("morning daylight walk", "lightbox", "PREFERS")],
     "which early-AM circadian trick beats the indoor bright lamp for mood and sleep",
     "early outdoor sunlight over indoor panel circadian mood timing"),
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
