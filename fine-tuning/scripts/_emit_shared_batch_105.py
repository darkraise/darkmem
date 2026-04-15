"""One-off emitter for shared-base batch-105 — personal domain (aging and elder-care slice).

Writes 50 rows to data/v2/shared/batch_105.tmp.jsonl with ids shared-05201..05250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_105.tmp.jsonl"
ID_OFFSET = 5200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Moved Dad from in-home care with Bluebird Agency to Oakridge Assisted Living on 2026-02-14 after the third night-time fall in a month.", "decision", "personal", False,
     [("Dad", "person"), ("Bluebird Agency", "organization"), ("Oakridge Assisted Living", "organization"), ("2026-02-14", "date"), ("fall", "event")],
     [("Oakridge Assisted Living", "Bluebird Agency", "REPLACES")],
     "when did the shift from home help to assisted living happen for my father and why",
     "parent move home care to facility assisted living fall night trigger"),
    # --- 2 ---
    ("Mum's dementia progressed from mild to moderate between the 2025-09 and 2026-03 neurology reviews at St Catherine's Hospital; sundowning now starts around 16:30.", "fact", "personal", False,
     [("Mum", "person"), ("dementia", "concept"), ("2025-09", "date"), ("2026-03", "date"), ("St Catherine's Hospital", "organization"), ("sundowning", "concept")],
     [("dementia", "Mum", "RELATED_TO")],
     "how did my mother's cognitive decline track across the last two neurology visits",
     "mum dementia staging progression mild moderate sundowning onset time"),
    # --- 3 ---
    ("Signed the durable power-of-attorney at Hemsworth Solicitors on 2026-01-18 covering Dad's finance and health decisions; my sister Claire is co-agent.", "milestone", "personal", False,
     [("power-of-attorney", "concept"), ("Hemsworth Solicitors", "organization"), ("2026-01-18", "date"), ("Dad", "person"), ("Claire", "person")],
     [],
     "when was the legal proxy for my father's decisions signed and who shares the duty",
     "power of attorney sign date solicitor finance health co-agent sibling"),
    # --- 4 ---
    ("Replaced Mum's old aluminium walker with a Rollz Motion rollator on 2026-03-02; the seat lets her rest mid-walk and the brakes are one-handed.", "decision", "personal", False,
     [("Mum", "person"), ("aluminium walker", "tool"), ("Rollz Motion rollator", "tool"), ("2026-03-02", "date")],
     [("Rollz Motion rollator", "aluminium walker", "REPLACES")],
     "which mobility aid did we swap in for my mother's old frame and what did it add",
     "walker replace rollator seat brake one handed rest mid walk date"),
    # --- 5 ---
    ("The sibling rotation for Dad's Sunday visits: Claire takes the first and third, I take the second and fourth, the fifth is whoever is in town.", "architecture", "personal", False,
     [("Dad", "person"), ("Sunday", "date"), ("Claire", "person")],
     [],
     "how do my sister and I split the weekly visit schedule for our father",
     "caregiver split weekly visit odd even weekend backup rule fallback"),
    # --- 6 ---
    ("Prefers Oakridge Assisted Living over Cedarbrook Gardens for Dad; Oakridge has a dementia-secure wing and a resident-to-carer ratio of 6:1 at night.", "preference", "personal", False,
     [("Oakridge Assisted Living", "organization"), ("Cedarbrook Gardens", "organization"), ("Dad", "person"), ("dementia-secure wing", "infrastructure")],
     [("Oakridge Assisted Living", "Cedarbrook Gardens", "PREFERS")],
     "which senior community did I pick for my father over the alternative and why",
     "assisted living choice dementia wing night staffing ratio tour compare"),
    # --- 7 ---
    ("Mum's medication pill organiser is a seven-day, four-slot Dosett box filled every Sunday evening; the blister pack from Boots is backup only.", "architecture", "personal", False,
     [("Mum", "person"), ("Dosett box", "tool"), ("Sunday", "date"), ("Boots", "organization"), ("blister pack", "tool")],
     [("Dosett box", "blister pack", "PREFERS")],
     "how is my mother's daily pill routine laid out and what is the backup",
     "medication pill organiser seven day four slot sunday fill blister"),
    # --- 8 ---
    ("The hospice decision for Grandpa went in on 2025-12-09 after the oncologist at Addenbrooke's said further chemo would not buy meaningful time.", "decision", "personal", False,
     [("hospice", "organization"), ("Grandpa", "person"), ("2025-12-09", "date"), ("oncologist", "person"), ("Addenbrooke's", "organization"), ("chemo", "method")],
     [],
     "when did we move grandfather to end-of-life care and what drove the call",
     "hospice decision grandpa oncology chemo diminishing returns date"),
    # --- 9 ---
    ("Medicare Part B premium for Dad went up to $185 in 2026; the IRMAA surcharge kicked in once his pension push put the 2024 MAGI over $106k.", "fact", "personal", False,
     [("Medicare Part B", "concept"), ("Dad", "person"), ("2026", "date"), ("IRMAA", "concept"), ("pension", "concept")],
     [("IRMAA", "Medicare Part B", "RELATED_TO")],
     "why did my father's Medicare premium jump this year and what triggered it",
     "medicare part B premium IRMAA surcharge MAGI threshold pension"),
    # --- 10. noise ---
    ("I'll grab a coffee and come back to this in a minute.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Upgraded Mum's hearing aids from the NHS Oticon Engage to private Phonak Audeo Lumity on 2026-02-28; Bluetooth to the TV was the dealbreaker.", "decision", "personal", False,
     [("Mum", "person"), ("Oticon Engage", "tool"), ("Phonak Audeo Lumity", "tool"), ("2026-02-28", "date"), ("Bluetooth", "protocol"), ("TV", "tool")],
     [("Phonak Audeo Lumity", "Oticon Engage", "REPLACES")],
     "which hearing-aid swap did we make for my mother and what won the case",
     "hearing aid NHS to private upgrade bluetooth TV streaming date"),
    # --- 12 ---
    ("Dad refuses to give up driving despite two parking-lot dents in six weeks; the GP referral for a DVLA cognitive assessment went in on 2026-03-22.", "problem", "personal", False,
     [("Dad", "person"), ("GP", "person"), ("DVLA", "organization"), ("cognitive assessment", "method"), ("2026-03-22", "date")],
     [],
     "what is the state of the driving-cessation fight with my father",
     "driving cessation refuse parking dents GP referral DVLA assessment"),
    # --- 13 ---
    ("The estate conversation with Mum on 2026-01-07 landed on splitting the Wollaston house equally three ways and leaving the antique clock to Claire outright.", "decision", "personal", False,
     [("Mum", "person"), ("2026-01-07", "date"), ("Wollaston house", "place"), ("antique clock", "concept"), ("Claire", "person")],
     [],
     "when did the inheritance talk with mother happen and how did it settle out",
     "estate will conversation house three way split antique clock specific bequest"),
    # --- 14 ---
    ("Grandpa passed on 2026-02-04 at 04:12 at Alderbrook Hospice; the vigil rota with Claire and Uncle Ray held both sides of the clock for the last 36 hours.", "milestone", "personal", False,
     [("Grandpa", "person"), ("2026-02-04", "date"), ("Alderbrook Hospice", "organization"), ("Claire", "person"), ("Uncle Ray", "person")],
     [("Grandpa", "Alderbrook Hospice", "LOCATED_IN")],
     "when did my grandfather die and how was the final vigil covered",
     "grandpa death hospice vigil rotation sibling uncle 36 hour coverage"),
    # --- 15 ---
    ("Grief since Grandpa's funeral hits hardest on Thursday mornings; the Cruse drop-in at St Mark's on Thursday evening has helped me name the pattern.", "fact", "personal", False,
     [("Grandpa", "person"), ("Thursday", "date"), ("Cruse", "organization"), ("St Mark's", "place"), ("Grief", "emotion")],
     [("Cruse", "St Mark's", "LOCATED_IN")],
     "when does the mourning after grandfather tend to spike and what is helping",
     "grief pattern weekday morning bereavement drop in church same day"),
    # --- 16 ---
    ("The in-home care plan for Mum runs three two-hour visits a day from Caremark Wiltshire; 07:30 wash-and-breakfast, 12:30 meds-and-lunch, 20:00 settle.", "architecture", "personal", False,
     [("Mum", "person"), ("Caremark Wiltshire", "organization"), ("wash-and-breakfast", "activity"), ("meds-and-lunch", "activity"), ("settle", "activity")],
     [],
     "how is the daily carer schedule for my mother structured across the visits",
     "in home care three visits morning midday evening wash meds settle"),
    # --- 17 ---
    ("Moved Dad's current account to a Lloyds third-party mandate with me as signatory on 2026-02-20; he still controls the debit card for small daily spends.", "milestone", "personal", False,
     [("Dad", "person"), ("Lloyds", "organization"), ("third-party mandate", "concept"), ("2026-02-20", "date"), ("debit card", "tool")],
     [],
     "when did co-signing my father's bank account go through and what autonomy stayed",
     "bank account third party mandate signatory debit card small spend"),
    # --- 18 ---
    ("Prefers the memory-care day programme at Ashleigh Court twice a week over five-day attendance; Mum comes home too tired from full weeks and loses words faster.", "preference", "personal", False,
     [("memory-care day programme", "service"), ("Ashleigh Court", "organization"), ("Mum", "person")],
     [("memory-care day programme", "Ashleigh Court", "LOCATED_IN")],
     "which dementia day-centre cadence wins for my mother and what is the evidence",
     "memory care day programme twice weekly over five fatigue word loss"),
    # --- 19 ---
    ("The stairlift from Stannah went in on 2026-01-30 at Mum's bungalow; six-day install delay from the supplier, threshold plate bent by delivery, fixed on first service.", "problem", "personal", False,
     [("stairlift", "tool"), ("Stannah", "organization"), ("2026-01-30", "date"), ("Mum", "person"), ("threshold plate", "infrastructure")],
     [],
     "what went wrong with the stairlift install at my mother's and how did it resolve",
     "stairlift install delay bent plate first service fix supplier issue"),
    # --- 20 ---
    ("Switched Dad's pharmacy from Boots Romford to LloydsPharmacy Hornchurch on 2026-03-09; Hornchurch does free monthly blister-pack delivery, Romford did not.", "decision", "personal", False,
     [("Dad", "person"), ("Boots Romford", "organization"), ("LloydsPharmacy Hornchurch", "organization"), ("2026-03-09", "date"), ("blister-pack", "tool")],
     [("LloydsPharmacy Hornchurch", "Boots Romford", "REPLACES")],
     "which pharmacy did we move my father to and what made the swap worth it",
     "pharmacy switch blister pack delivery free monthly service gap reason"),
    # --- 21 ---
    ("Anticipating my own late-life move, I prefer a continuing-care community model like Moorside Village over a standalone nursing home; one move, three stages of care.", "preference", "personal", False,
     [("continuing-care community", "concept"), ("Moorside Village", "organization"), ("nursing home", "organization")],
     [("continuing-care community", "nursing home", "PREFERS")],
     "which late-life living model do I want for myself and what is the draw",
     "own aging continuing care retirement community over nursing home one move"),
    # --- 22 ---
    ("The Medicaid spend-down worksheet for Aunt Edna shows she clears the $2k asset limit by 2026-07 if the annuity is restructured; waiver application due 2026-05-15.", "reference", "personal", False,
     [("Medicaid", "concept"), ("Aunt Edna", "person"), ("2026-07", "date"), ("annuity", "concept"), ("2026-05-15", "date")],
     [],
     "when will my aunt qualify for Medicaid on the spend-down and what is the deadline",
     "medicaid spend down asset limit annuity restructure waiver deadline"),
    # --- 23 ---
    ("The care-home contract at Oakridge is £1,420 a week for a single en-suite room; the continuing-healthcare funding decision from the CCG is still outstanding.", "fact", "personal", False,
     [("Oakridge", "organization"), ("en-suite room", "infrastructure"), ("continuing-healthcare funding", "concept"), ("CCG", "organization")],
     [],
     "what is the care-home fee and is any NHS funding layered on yet",
     "care home weekly fee en suite continuing healthcare CHC CCG pending"),
    # --- 24 ---
    ("Prefers video calls over phone with Mum; the Grandpad tablet's two-tap call button bypasses the password loop that always cut the old landline chats short.", "preference", "personal", False,
     [("Mum", "person"), ("Grandpad", "tool"), ("landline", "tool")],
     [("Grandpad", "landline", "PREFERS")],
     "which way of keeping in touch with my mother beats the old one and why",
     "video call grandpad tablet two tap over landline phone password reason"),
    # --- 25 ---
    ("The will with Hemsworth Solicitors was updated on 2026-02-11; added a letter of wishes about cremation, kept the charitable gift to Marie Curie intact.", "milestone", "personal", False,
     [("Hemsworth Solicitors", "organization"), ("2026-02-11", "date"), ("letter of wishes", "concept"), ("cremation", "concept"), ("Marie Curie", "organization")],
     [],
     "when was the will refreshed and what changed versus what stayed",
     "will update letter of wishes cremation charitable gift unchanged date"),
    # --- 26 ---
    ("Mum's medication list holds donepezil 10 mg, memantine 20 mg, amlodipine 5 mg, atorvastatin 40 mg; the GP review on 2026-04-03 is going to flag the statin.", "reference", "personal", False,
     [("Mum", "person"), ("donepezil", "concept"), ("memantine", "concept"), ("amlodipine", "concept"), ("atorvastatin", "concept"), ("2026-04-03", "date")],
     [],
     "what is my mother's current elder-care medication list and what is up for review",
     "medication list donepezil memantine amlodipine statin GP review date"),
    # --- 27 ---
    ("The dementia-friendly design of Mum's bungalow hallway now uses red toilet-door paint and a contrasting grab-rail; cue recognition went up within a fortnight.", "decision", "personal", False,
     [("Mum", "person"), ("bungalow hallway", "place"), ("red toilet-door paint", "tool"), ("grab-rail", "tool"), ("fortnight", "date")],
     [],
     "what dementia-friendly tweak at my mother's home actually moved the needle",
     "dementia home mod red door contrasting grab rail recognition improvement"),
    # --- 28 ---
    ("Dad's fall at Oakridge on 2026-03-17 cracked a rib but missed the hip; the sensor mat by the bed was on its second battery, picked up the exit.", "problem", "personal", False,
     [("Dad", "person"), ("Oakridge", "organization"), ("2026-03-17", "date"), ("rib", "concept"), ("hip", "concept"), ("sensor mat", "tool")],
     [],
     "what happened with my father's recent fall and did the safety kit hold up",
     "fall cracked rib no hip fracture sensor mat exit detection battery"),
    # --- 29 ---
    ("Replaced the paper care diary at Mum's with the Jointly app on 2026-01-15; Claire can see last-meal and last-med in her car-park wait, not a panicked phone call.", "decision", "personal", False,
     [("paper care diary", "tool"), ("Mum", "person"), ("Jointly app", "tool"), ("2026-01-15", "date"), ("Claire", "person")],
     [("Jointly app", "paper care diary", "REPLACES")],
     "which care-log format took over at my mother's and what did it unlock",
     "paper diary to jointly app last meal last med shared view sibling"),
    # --- 30 ---
    ("Anticipation-wise I'm earmarking £18k a year from 2035 for the kind of assisted living I'd want; pension projection from Nutmeg says the pot holds.", "architecture", "personal", False,
     [("2035", "date"), ("assisted living", "service"), ("pension", "concept"), ("Nutmeg", "organization")],
     [],
     "what am I planning for my own eventual care costs and does the math work",
     "own aging assisted living budget annual projection pension pot sufficiency"),
    # --- 31 ---
    ("The NHS continuing-healthcare assessment for Dad on 2026-02-27 scored him at three highs, two moderates; the decision support tool result still tipped to no CHC.", "problem", "personal", False,
     [("NHS", "organization"), ("continuing-healthcare assessment", "method"), ("Dad", "person"), ("2026-02-27", "date"), ("decision support tool", "tool")],
     [],
     "how did my father's NHS fully-funded care assessment land and why not awarded",
     "NHS CHC assessment score highs moderates decision support tool outcome"),
    # --- 32 ---
    ("Claire and I agreed on 2026-03-20 that primary decision-making for Mum sits with Claire because she's 12 miles away; I handle finance and legal only.", "decision", "personal", False,
     [("Claire", "person"), ("2026-03-20", "date"), ("Mum", "person")],
     [],
     "how did my sister and I divide the decision load for our mother and why",
     "sibling caregiving split primary decision local sister proximity finance legal"),
    # --- 33 ---
    ("The funeral plan at Co-op Funeralcare for Grandpa was prepaid in 2019; saved roughly £1,900 against the 2026 rack rate, eased the week after the death.", "fact", "personal", False,
     [("Co-op Funeralcare", "organization"), ("Grandpa", "person"), ("2019", "date"), ("2026", "date")],
     [],
     "how did my grandfather's prepaid funeral plan pay off in practice",
     "prepaid funeral plan savings vs current rate ease logistics post death"),
    # --- 34. noise ---
    ("Let me put the kettle on before we start.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The community dementia nurse from Wiltshire Health & Care, Niamh, visits Mum fortnightly on Wednesdays; she flags tiny changes the carers miss.", "reference", "personal", False,
     [("community dementia nurse", "person"), ("Wiltshire Health & Care", "organization"), ("Niamh", "person"), ("Mum", "person"), ("Wednesdays", "date")],
     [("Niamh", "Wiltshire Health & Care", "WORKS_AT")],
     "who is the specialist dementia nurse visiting my mother and how often",
     "community dementia nurse fortnightly wednesday wiltshire flags change"),
    # --- 36 ---
    ("Prefers bringing Dad home for Sunday lunch over eating in the Oakridge dining room; car transfer is rough but recognition of the kitchen is worth it.", "preference", "personal", False,
     [("Dad", "person"), ("Sunday", "date"), ("Oakridge", "organization"), ("dining room", "place"), ("kitchen", "place")],
     [("kitchen", "dining room", "PREFERS")],
     "where does Sunday lunch with my father work best and what is the trade-off",
     "sunday lunch home over care home dining room kitchen recognition tradeoff"),
    # --- 37 ---
    ("The LPA for Mum went through the Office of the Public Guardian on 2026-03-14 after a nine-week wait; registration fee was £82, two certificate providers from the parish.", "milestone", "personal", False,
     [("LPA", "concept"), ("Mum", "person"), ("Office of the Public Guardian", "organization"), ("2026-03-14", "date"), ("parish", "place")],
     [],
     "when did the lasting power of attorney for mother come through and what did it cost",
     "LPA registered OPG fee wait weeks certificate providers parish date"),
    # --- 38 ---
    ("Dad's GP surgery, Grange Medical Centre, moved to an electronic prescription service direct to LloydsPharmacy on 2026-03-09; the repeat script never hits the post now.", "fact", "personal", False,
     [("Dad", "person"), ("Grange Medical Centre", "organization"), ("electronic prescription service", "service"), ("LloydsPharmacy", "organization"), ("2026-03-09", "date")],
     [("electronic prescription service", "LloydsPharmacy", "COMMUNICATES_WITH")],
     "when did my father's prescriptions go electronic and what changed operationally",
     "electronic prescription service GP to pharmacy direct repeat script date"),
    # --- 39 ---
    ("The grief counsellor referral from the GP lined me up with Mandy at Cruse on 2026-03-02; six sessions allocated, first one was mostly timeline reconstruction.", "milestone", "personal", False,
     [("GP", "person"), ("Mandy", "person"), ("Cruse", "organization"), ("2026-03-02", "date"), ("timeline reconstruction", "method")],
     [("Mandy", "Cruse", "WORKS_AT")],
     "when did counselling after the death start and what was the first session like",
     "grief counsellor referral cruse six sessions timeline first session date"),
    # --- 40 ---
    ("Swapped Mum's ordinary teacup for a Ornamin Dysphagia cup with a nose cutout on 2026-02-16; aspiration coughs at tea-time dropped off within a week.", "decision", "personal", False,
     [("Mum", "person"), ("teacup", "tool"), ("Ornamin Dysphagia cup", "tool"), ("2026-02-16", "date"), ("aspiration coughs", "finding")],
     [("Ornamin Dysphagia cup", "teacup", "REPLACES")],
     "which cup swap helped my mother's swallow and how quickly did it show",
     "dysphagia cup nose cutout replace teacup aspiration cough reduction date"),
    # --- 41 ---
    ("The sibling WhatsApp group with Claire and Uncle Ray holds daily care updates for Mum; rule is reply-within-the-hour or the pin goes to the next person.", "architecture", "personal", False,
     [("Claire", "person"), ("Uncle Ray", "person"), ("Mum", "person"), ("WhatsApp", "platform")],
     [],
     "how do the caregiving family members keep each other updated and what is the escalation rule",
     "sibling whatsapp group daily update reply within hour pin escalation"),
    # --- 42 ---
    ("Prefers the Admiral Nurse helpline to the generic Alzheimer's Society line for a Friday-night crisis; the Admiral nurse on rota actually reads the case notes.", "preference", "personal", False,
     [("Admiral Nurse helpline", "service"), ("Alzheimer's Society", "organization"), ("Friday", "date")],
     [("Admiral Nurse helpline", "Alzheimer's Society", "PREFERS")],
     "which dementia helpline wins out late-night and why in practice",
     "admiral nurse helpline over alzheimers society friday crisis case notes"),
    # --- 43 ---
    ("Mum's diagnosis at the Memory Assessment Service on 2025-06-04 was mixed dementia, Alzheimer's plus vascular; MMSE 21/30 at that visit, 17/30 by 2026-03.", "fact", "personal", False,
     [("Mum", "person"), ("Memory Assessment Service", "organization"), ("2025-06-04", "date"), ("mixed dementia", "concept"), ("MMSE", "method"), ("2026-03", "date")],
     [("mixed dementia", "Mum", "RELATED_TO")],
     "what is my mother's dementia diagnosis and how is the MMSE tracking over time",
     "mixed dementia alzheimers vascular MMSE score drop memory assessment"),
    # --- 44 ---
    ("The grab-rail install at Mum's bathroom by Wiltshire Council OT on 2026-01-22 came free under the minor-adaptations grant; a private quote had been £340.", "fact", "personal", False,
     [("Mum", "person"), ("Wiltshire Council", "organization"), ("OT", "person"), ("2026-01-22", "date"), ("minor-adaptations grant", "concept")],
     [],
     "how did the bathroom grab-rail at my mother's get installed and what did it cost",
     "grab rail OT council minor adaptations grant free private quote date"),
    # --- 45 ---
    ("Chose cremation over burial for Grandpa at the 2025-11 pre-death family meeting; the plot at Eastfield Cemetery stays with Gran, ashes scattered at Stokes Bay.", "decision", "personal", False,
     [("Grandpa", "person"), ("2025-11", "date"), ("Eastfield Cemetery", "place"), ("Gran", "person"), ("Stokes Bay", "place")],
     [("Stokes Bay", "Eastfield Cemetery", "PREFERS")],
     "what did the family settle on for grandfather's funeral and where",
     "cremation over burial pre death meeting plot spouse ashes scatter bay"),
    # --- 46 ---
    ("Dad's care-home room at Oakridge is Room 14 on the Lavender wing, ground floor, window to the courtyard; the dementia unit is a locked one-swipe door.", "reference", "personal", False,
     [("Dad", "person"), ("Oakridge", "organization"), ("Room 14", "place"), ("Lavender wing", "place"), ("courtyard", "place")],
     [("Room 14", "Lavender wing", "LOCATED_IN"), ("Lavender wing", "Oakridge", "LOCATED_IN")],
     "where exactly is my father's room in the care home and how is the wing secured",
     "care home room number wing ground floor courtyard locked dementia door"),
    # --- 47 ---
    ("Prefers the night-time sensor mat from Alertacall over the pendant alarm Dad won't wear; no compliance issue when it's under the mattress.", "preference", "personal", False,
     [("sensor mat", "tool"), ("Alertacall", "organization"), ("pendant alarm", "tool"), ("Dad", "person"), ("mattress", "tool")],
     [("sensor mat", "pendant alarm", "PREFERS")],
     "which fall-alert device wins for my father and what drove the pick",
     "sensor mat over pendant alarm compliance refuses wear mattress discreet"),
    # --- 48 ---
    ("The final Blue Badge renewal for Mum was approved on 2026-02-09; three-year expiry, but the mobility threshold is right at the edge and next time looks borderline.", "milestone", "personal", False,
     [("Blue Badge", "concept"), ("Mum", "person"), ("2026-02-09", "date"), ("mobility threshold", "concept")],
     [],
     "when did the disabled-parking permit for my mother renew and is the next one safe",
     "blue badge renewal three year expiry threshold borderline next review"),
    # --- 49 ---
    ("Replaced the family solicitor Pennington & Co with Hemsworth Solicitors on 2025-10-06 for all elder-care legal work; Hemsworth's elder-law specialist Priya charges flat-fee per matter.", "decision", "personal", False,
     [("Pennington & Co", "organization"), ("Hemsworth Solicitors", "organization"), ("2025-10-06", "date"), ("Priya", "person"), ("elder-law", "field")],
     [("Hemsworth Solicitors", "Pennington & Co", "REPLACES"), ("Priya", "Hemsworth Solicitors", "WORKS_AT")],
     "which law firm took over the elder-care legal work and what was the pull",
     "solicitor switch elder law specialist flat fee per matter transparency"),
    # --- 50 ---
    ("The financial-abuse scare on 2026-01-24 where Dad nearly sent £2,400 to a cold caller was stopped by Lloyds fraud team; we added a trusted-contact flag and a £500 daily transfer cap.", "problem", "personal", False,
     [("Dad", "person"), ("2026-01-24", "date"), ("Lloyds", "organization"), ("cold caller", "person"), ("trusted-contact flag", "config"), ("daily transfer cap", "config")],
     [],
     "what scam close-call hit my father and what safeguards went in afterwards",
     "financial abuse scam cold caller bank fraud team trusted contact transfer cap"),
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
