"""One-off emitter for shared-base batch-138 — cross domain.

Slice: elder care meets tech (medication reminders, fall detection, monitoring
dashboards, caregiver coordination apps, telehealth, digital POA, voice
assistants, smart pill dispensers). Writes 50 rows to
data/v2/shared/batch_138.tmp.jsonl with ids shared-06851..06900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_138.tmp.jsonl"
ID_OFFSET = 6850

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped MyTherapy for Medisafe on mom's iPhone because the Medisafe Medfriend feature lets my sister Priya get a push alert when the 8pm warfarin dose gets missed.", "decision", "cross", False,
     [("MyTherapy", "service"), ("Medisafe", "service"), ("iPhone", "infrastructure"), ("Priya", "person"), ("warfarin", "concept")],
     [("Medisafe", "MyTherapy", "REPLACES")],
     "which pill reminder app took over for mom and why",
     "medication reminder app swap caregiver escalation missed dose alert"),
    # --- 2 ---
    ("Prefers the Apple Watch Series 10 over the Google Pixel Watch 3 for dad because the fall-detection call to 911 actually worked when he slipped on the Tampa patio on 2026-02-18.", "preference", "cross", False,
     [("Apple Watch Series 10", "infrastructure"), ("Google Pixel Watch 3", "infrastructure"), ("Tampa", "place"), ("2026-02-18", "date")],
     [("Apple Watch Series 10", "Google Pixel Watch 3", "PREFERS")],
     "which wearable wins for dad's fall detection after the real incident",
     "fall detection wearable watch emergency dispatch patio slip event"),
    # --- 3 ---
    ("The GrandCare dashboard in the Oakwood assisted-living room replaced the clipboard daily check-in because the motion-sensor log of overnight bathroom trips is the only thing that caught dad's UTI early.", "decision", "cross", False,
     [("GrandCare", "service"), ("Oakwood", "place"), ("UTI", "concept")],
     [("GrandCare", "UTI", "COMMUNICATES_WITH")],
     "what monitoring setup caught the urinary infection before symptoms escalated",
     "assisted living monitoring motion sensor nocturia trend early warning"),
    # --- 4 ---
    ("Moved the sibling caregiving rotation from a group text to a shared Cozi calendar on 2026-03-06 after Priya and Marcus double-booked the Friday dialysis ride for mom.", "milestone", "cross", False,
     [("Cozi", "service"), ("2026-03-06", "date"), ("Priya", "person"), ("Marcus", "person")],
     [("Cozi", "Priya", "USES")],
     "when did the sibling caregiving schedule move off of group texts",
     "caregiver rotation shared calendar double booking dialysis transport"),
    # --- 5 ---
    ("CareZone holds the medication list and pharmacy barcodes for mom's eight prescriptions while Google Calendar handles the appointment-reminder SMS to aunt Lila who still refuses any app download.", "architecture", "cross", False,
     [("CareZone", "service"), ("Google Calendar", "service"), ("Lila", "person")],
     [("CareZone", "Google Calendar", "PREFERS")],
     "how are mom's meds tracked without forcing aunt Lila onto a new app",
     "medication list barcode scan shared calendar SMS reminder relative"),
    # --- 6. noise ---
    ("Hang on, let me pull that up.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("The Hero smart pill dispenser replaced the weekly plastic pillbox for mom on 2026-01-14 because the auto-dispense at 7am meant she stopped skipping the metformin on the bad-arthritis mornings.", "milestone", "cross", False,
     [("Hero", "infrastructure"), ("2026-01-14", "date"), ("metformin", "concept")],
     [("Hero", "metformin", "USES")],
     "when did the smart pill dispenser take over from the plastic weekly box",
     "automatic pill dispenser adherence arthritis morning diabetes routine"),
    # --- 8 ---
    ("Prefers the Echo Show 10 in dad's kitchen over the Echo Show 8 because the motion-follow camera keeps the Alexa Together video call with Priya framed while he shuffles between the fridge and the stove.", "preference", "cross", False,
     [("Echo Show 10", "infrastructure"), ("Echo Show 8", "infrastructure"), ("Alexa Together", "service"), ("Priya", "person")],
     [("Echo Show 10", "Echo Show 8", "PREFERS"), ("Alexa Together", "Echo Show 10", "DEPLOYED_ON")],
     "which Echo Show sits in dad's kitchen for the daily video call",
     "motion tracking smart display video call elder kitchen framing"),
    # --- 9 ---
    ("Teladoc replaced the Babylon subscription for mom's telehealth visits on 2026-02-22 once the Babylon US shutdown forced a new provider for the every-six-week cardiology follow-ups.", "decision", "cross", False,
     [("Teladoc", "service"), ("Babylon", "service"), ("2026-02-22", "date")],
     [("Teladoc", "Babylon", "REPLACES")],
     "why did the telehealth provider change for mom's cardiology follow-ups",
     "telehealth provider migration shutdown cardiology recurring visit"),
    # --- 10 ---
    ("The Everplans vault holds dad's durable power of attorney PDF, the living will, and the HIPAA release so that Marcus in Seattle can share the documents with the Cleveland Clinic intake desk in under five minutes.", "architecture", "cross", False,
     [("Everplans", "service"), ("PDF", "concept"), ("HIPAA", "concept"), ("Marcus", "person"), ("Seattle", "place"), ("Cleveland Clinic", "organization")],
     [("Everplans", "HIPAA", "USES")],
     "how do dad's legal documents reach an out-of-state hospital intake quickly",
     "digital estate vault power of attorney release form hospital intake"),
    # --- 11 ---
    ("Trust & Will replaced the LegalZoom workflow for mom's estate update on 2026-03-28 because the estate attorney in Sarasota preferred the Trust & Will PDF packet over the LegalZoom output.", "decision", "cross", False,
     [("Trust & Will", "service"), ("LegalZoom", "service"), ("2026-03-28", "date"), ("Sarasota", "place"), ("PDF", "concept")],
     [("Trust & Will", "LegalZoom", "REPLACES")],
     "which estate-planning tool won for mom's Florida estate update",
     "estate planning document tool swap attorney preference packet format"),
    # --- 12 ---
    ("The Kardia 6L ECG feeds directly into the MyChart portal for dad's cardiologist at Mayo because the atrial-fibrillation strips catch episodes that the Apple Watch ECG misses between readings.", "architecture", "cross", False,
     [("Kardia 6L", "infrastructure"), ("MyChart", "service"), ("Mayo", "organization"), ("Apple Watch", "infrastructure")],
     [("Kardia 6L", "MyChart", "COMMUNICATES_WITH"), ("Kardia 6L", "Apple Watch", "PREFERS")],
     "how do dad's afib episodes actually reach the cardiologist's chart",
     "portable ECG strip portal upload atrial fibrillation detection afib"),
    # --- 13 ---
    ("Frustration boiled over when the Nest Cam Indoor feed in mom's living room on 2026-02-09 kept losing the RTSP stream to Home Assistant and we lost a whole afternoon of check-ins.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Nest Cam Indoor", "infrastructure"), ("2026-02-09", "date"), ("RTSP", "protocol"), ("Home Assistant", "platform")],
     [("Nest Cam Indoor", "Home Assistant", "COMMUNICATES_WITH")],
     "what went wrong with mom's living-room camera feed that February afternoon",
     "indoor camera stream drop home automation integration check in gap"),
    # --- 14 ---
    ("The Medicare Plan Finder on medicare.gov replaced the eHealth comparison on 2026-10-18 for mom's 2027 Medicare Advantage pick because the Plan Finder finally showed the Humana formulary for her rivaroxaxban.", "decision", "cross", False,
     [("Medicare Plan Finder", "service"), ("medicare.gov", "service"), ("eHealth", "service"), ("2026-10-18", "date"), ("Humana", "organization")],
     [("Medicare Plan Finder", "eHealth", "REPLACES")],
     "which tool handled mom's 2027 Medicare Advantage enrollment decision",
     "medicare advantage comparison formulary lookup annual enrollment pick"),
    # --- 15 ---
    ("Prefers the PillDrill tablet scanner over the MedMinder cellular dispenser for aunt Lila because PillDrill's RFID sticker workflow survived the Verizon 3G sunset that bricked two MedMinder units.", "preference", "cross", False,
     [("PillDrill", "infrastructure"), ("MedMinder", "infrastructure"), ("Lila", "person"), ("RFID", "protocol"), ("Verizon", "organization")],
     [("PillDrill", "MedMinder", "PREFERS")],
     "which pill dispenser hardware is actually on aunt Lila's counter now",
     "pill dispenser hardware cellular sunset RFID scan tablet workflow"),
    # --- 16 ---
    ("The Empathy grief-support app carried the estate-close checklist after dad's 2026-01-07 passing because the task list covered cancelling the Medicare Advantage plan in a way the funeral home paperwork did not.", "milestone", "cross", False,
     [("Empathy", "service"), ("2026-01-07", "date")],
     [],
     "what tool actually walked the family through the after-death checklist",
     "grief support app estate close task list insurance cancellation after loss"),
    # --- 17 ---
    ("Caring.com forums replaced the AARP community posts for the Parkinson's caregiver research because the Caring.com threads on levodopa timing strategies were deeper than the AARP general advice.", "decision", "cross", False,
     [("Caring.com", "service"), ("AARP", "organization"), ("Parkinson's", "concept"), ("levodopa", "concept")],
     [("Caring.com", "AARP", "REPLACES")],
     "which caregiver community has the deepest Parkinson's medication discussions",
     "caregiver forum community research medication timing disease specific"),
    # --- 18 ---
    ("The Lantern checklist handled the 2026-03-19 Social Security death-benefit filing for dad because the SSA-8 form walkthrough beat the funeral director's photocopied instructions.", "milestone", "cross", False,
     [("Lantern", "service"), ("2026-03-19", "date"), ("Social Security", "organization"), ("SSA-8", "pattern")],
     [],
     "what guided the Social Security lump-sum death benefit filing for dad",
     "after death filing checklist social security form walkthrough benefit"),
    # --- 19 ---
    ("StoryCorps app replaced the handheld Zoom H5 recorder for mom's voice-banking sessions on 2026-02-28 once the DIPG diagnosis meant every hour of her voice mattered for the legacy recording.", "decision", "cross", False,
     [("StoryCorps", "service"), ("Zoom H5", "infrastructure"), ("2026-02-28", "date"), ("DIPG", "concept")],
     [("StoryCorps", "Zoom H5", "REPLACES")],
     "when did mom's legacy voice recordings switch to the StoryCorps app",
     "voice banking legacy recording terminal diagnosis app microphone swap"),
    # --- 20 ---
    ("Relief flooded when Alexa Together's urgent-response line for mom connected to the Papillon response agent within ninety seconds of the 3am 'Alexa call for help' in the Ocala bedroom.", "milestone", "cross", False,
     [("Relief", "emotion"), ("Alexa Together", "service"), ("Papillon", "organization"), ("Ocala", "place")],
     [("Alexa Together", "Papillon", "COMMUNICATES_WITH")],
     "what happened the night the voice assistant actually dispatched urgent response",
     "voice assistant urgent response dispatch overnight call for help elder"),
    # --- 21 ---
    ("The Life360 Silver tier replaced the paper family contact sheet for dad's wallet because the Silver SOS button on his Jitterbug Smart4 actually hit my phone before the EMTs arrived at the Bradenton scene.", "decision", "cross", False,
     [("Life360 Silver", "service"), ("Jitterbug Smart4", "infrastructure"), ("Bradenton", "place")],
     [("Life360 Silver", "Jitterbug Smart4", "DEPLOYED_ON")],
     "which emergency-contact system beat the wallet card for dad",
     "family safety app senior phone SOS button emergency contact dispatch"),
    # --- 22 ---
    ("Moved the shared caregiver log from CareZone to Lotsa Helping Hands on 2026-03-11 because the meal-train coordination for the post-hip-replacement recovery needed the Lotsa volunteer signup grid.", "milestone", "cross", False,
     [("CareZone", "service"), ("Lotsa Helping Hands", "service"), ("2026-03-11", "date")],
     [("Lotsa Helping Hands", "CareZone", "REPLACES")],
     "when did the caregiver coordination move off of CareZone for mom's recovery",
     "caregiver log meal train volunteer signup post surgery recovery coordination"),
    # --- 23 ---
    ("The Ring Stick Up Cam on mom's porch feeds into the Rapid Ring alert on Priya's phone, and the consent notice we printed and taped inside the door keeps the home-health aide comfortable with the coverage.", "architecture", "cross", False,
     [("Ring Stick Up Cam", "infrastructure"), ("Rapid Ring", "service"), ("Priya", "person")],
     [("Ring Stick Up Cam", "Rapid Ring", "COMMUNICATES_WITH")],
     "how does the porch camera stay compliant with the home-health aide's consent",
     "doorbell camera aide consent notice notification family monitoring"),
    # --- 24 ---
    ("Confusion hit when the PlushCare app kept trying to route mom's 2026-02-25 refill request to a Texas-licensed physician instead of the Florida prescriber who knew her lisinopril history.", "problem", "cross", False,
     [("Confusion", "emotion"), ("PlushCare", "service"), ("2026-02-25", "date"), ("Texas", "place"), ("Florida", "place"), ("lisinopril", "concept")],
     [],
     "what went sideways with mom's telehealth refill that late-February morning",
     "telehealth prescriber licensing cross state refill routing medication"),
    # --- 25 ---
    ("The Sonos Voice Control via Alexa on mom's bedside Sonos Era 100 replaced the old Amazon Echo Dot because the Sonos alarm fade-in at 6:45am doesn't startle her into a panic the way the Dot did.", "decision", "cross", False,
     [("Sonos Voice Control", "service"), ("Alexa", "service"), ("Sonos Era 100", "infrastructure"), ("Amazon Echo Dot", "infrastructure")],
     [("Sonos Era 100", "Amazon Echo Dot", "REPLACES")],
     "why did mom's bedside voice speaker get swapped out this spring",
     "smart speaker bedside swap alarm fade in startle response elder"),
    # --- 26 ---
    ("Prefers the Tile Mate on dad's walker over the AirTag because the Tile ring volume actually makes it over his Phonak hearing-aid programming while the AirTag chirp sits below his threshold.", "preference", "cross", False,
     [("Tile Mate", "infrastructure"), ("AirTag", "infrastructure"), ("Phonak", "service")],
     [("Tile Mate", "AirTag", "PREFERS")],
     "which tracker dad actually hears when the walker goes missing",
     "tracker audible range hearing aid frequency accessibility elder use"),
    # --- 27 ---
    ("Google Calendar holds the sibling rotation skeleton for mom's care but a shared Apple Notes document tracks the 'what mom said today' running log because the search across free-text works better there.", "architecture", "cross", False,
     [("Google Calendar", "service"), ("Apple Notes", "service")],
     [("Apple Notes", "Google Calendar", "PREFERS")],
     "how is the day-to-day caregiver narrative captured alongside the schedule",
     "caregiver narrative log free text search sibling rotation coordination"),
    # --- 28 ---
    ("The Arlo Pro 5 camera in dad's memory-care room at Magnolia Grove replaced the Wyze v3 because the Wyze cloud recording stopped respecting the staff-consent privacy schedule on 2026-02-03.", "decision", "cross", False,
     [("Arlo Pro 5", "infrastructure"), ("Wyze v3", "infrastructure"), ("Magnolia Grove", "place"), ("2026-02-03", "date")],
     [("Arlo Pro 5", "Wyze v3", "REPLACES")],
     "which camera sits in dad's memory-care room and what forced the switch",
     "memory care camera swap staff consent privacy schedule cloud recording"),
    # --- 29 ---
    ("Curiosity sparked when the GrandPad tablet's simplified interface finally got aunt Lila to answer the family video calls, while the iPad with FaceTime had sat unused for fourteen months.", "milestone", "cross", False,
     [("Curiosity", "emotion"), ("GrandPad", "infrastructure"), ("Lila", "person"), ("iPad", "infrastructure"), ("FaceTime", "service")],
     [("GrandPad", "iPad", "REPLACES")],
     "which tablet finally cracked aunt Lila's refusal to do family video calls",
     "simplified senior tablet adoption video call interface accessibility"),
    # --- 30 ---
    ("Medisafe's measurements feature tracked mom's systolic blood pressure off the Omron 7 Series cuff for six months, and the trend line caught the slow creep that the PCP missed in quarterly office readings.", "architecture", "cross", False,
     [("Medisafe", "service"), ("Omron 7 Series", "infrastructure")],
     [("Medisafe", "Omron 7 Series", "USES")],
     "how did the slow blood-pressure creep actually get flagged for mom's PCP",
     "home blood pressure trend long term tracking missed clinical signal"),
    # --- 31 ---
    ("Prefers Papa Pals over the local Home Instead franchise for dad's non-medical companion visits because the Papa driver-companion model covers both the Publix run and the afternoon chess game in one three-hour slot.", "preference", "cross", False,
     [("Papa Pals", "service"), ("Home Instead", "organization"), ("Publix", "organization")],
     [("Papa Pals", "Home Instead", "PREFERS")],
     "which companion-care service better fits dad's mixed errand and social need",
     "companion care gig platform grocery errand social visit elder matching"),
    # --- 32 ---
    ("The Samsung Family Hub fridge in mom's kitchen replaced the magnetic whiteboard grocery list because the 'tell Bixby add milk' voice input actually survives her macular-degeneration vision loss.", "decision", "cross", False,
     [("Samsung Family Hub", "infrastructure"), ("Bixby", "service")],
     [("Samsung Family Hub", "Bixby", "USES")],
     "how does mom's grocery list stay current with her failing vision",
     "smart fridge voice list accessibility macular degeneration elder kitchen"),
    # --- 33 ---
    ("CaringBridge kept the extended family updated on dad's 2026-02-16 stroke recovery because the single-post-per-day model stopped the twelve-sibling group text from overwhelming Marcus during the ICU week.", "architecture", "cross", False,
     [("CaringBridge", "service"), ("2026-02-16", "date"), ("Marcus", "person"), ("ICU", "infrastructure")],
     [],
     "how did the family stay informed about dad's stroke without drowning Marcus",
     "family update site single post per day stroke recovery group communication"),
    # --- 34. noise ---
    ("Let me think about that for a moment.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Google Pixel Watch 3 fall-detection SOS broke on 2026-03-02 during aunt Lila's bathroom slip because the Wi-Fi-only Pixel Watch lost the Bluetooth tether when her Pixel 8 was charging in the bedroom.", "problem", "cross", False,
     [("Google Pixel Watch 3", "infrastructure"), ("2026-03-02", "date"), ("Lila", "person"), ("Pixel 8", "infrastructure"), ("Bluetooth", "protocol")],
     [("Google Pixel Watch 3", "Pixel 8", "COMMUNICATES_WITH")],
     "what went wrong with the fall-detection during aunt Lila's bathroom incident",
     "fall detection failure bluetooth tether wifi only phone charging gap"),
    # --- 36 ---
    ("The Envoy at Home tablet replaced the Amazon Show 15 in dad's memory-care room because Envoy's staff-paging integration with the Magnolia Grove nursing call-bell worked out of the box.", "decision", "cross", False,
     [("Envoy at Home", "service"), ("Amazon Show 15", "infrastructure"), ("Magnolia Grove", "place")],
     [("Envoy at Home", "Amazon Show 15", "REPLACES")],
     "which in-room display integrates with the memory-care facility's nurse-call system",
     "in room display nurse call integration memory care facility paging"),
    # --- 37 ---
    ("Prefers Lively Mobile2 over LifeAlert for dad's pendant because the Lively Urgent Response agent can push dispatch straight into the Sarasota county CAD without the LifeAlert call-tree delay.", "preference", "cross", False,
     [("Lively Mobile2", "infrastructure"), ("LifeAlert", "service"), ("Sarasota", "place"), ("CAD", "concept")],
     [("Lively Mobile2", "LifeAlert", "PREFERS")],
     "which medical alert pendant routes faster to local dispatch",
     "PERS pendant medical alert response center dispatch cad county"),
    # --- 38 ---
    ("The Caribou Caregiver financial-tracking app finally replaced the Google Sheet mom and I shared for dad's reimbursable expenses because the receipt OCR handled the Walgreens durable-medical-equipment stack from 2026-02.", "decision", "cross", False,
     [("Caribou Caregiver", "service"), ("Google Sheet", "service"), ("Walgreens", "organization"), ("2026-02", "date")],
     [("Caribou Caregiver", "Google Sheet", "REPLACES")],
     "which app took over the caregiving-expense ledger this spring",
     "caregiver finance tracking receipt OCR durable medical equipment reimbursement"),
    # --- 39 ---
    ("Mom's Aloe Care Smart Hub in the Pensacola condo runs the fall detection through the ceiling-mounted radar sensor instead of a watch because she refuses to wear anything on her wrist.", "architecture", "cross", False,
     [("Aloe Care", "service"), ("Pensacola", "place")],
     [],
     "how does mom's fall detection work when she won't wear a wrist device",
     "ambient radar fall detection ceiling sensor wearable refusal elder"),
    # --- 40 ---
    ("MyChart's proxy-access feature replaced the signed release-of-information stack for dad's Florida Cancer Specialists portal because the proxy link lets Priya actually see the PET-scan reports within an hour of upload.", "decision", "cross", False,
     [("MyChart", "service"), ("Florida Cancer Specialists", "organization"), ("Priya", "person"), ("PET", "concept")],
     [("MyChart", "Priya", "COMMUNICATES_WITH")],
     "how does Priya actually see dad's scan reports without waiting on release forms",
     "patient portal proxy access caregiver records imaging review timely"),
    # --- 41 ---
    ("The shared Google Drive folder 'DadCare-2026' replaced the filing cabinet for dad's medical records on 2026-01-20 because all three siblings needed simultaneous access during the Tampa General discharge planning.", "milestone", "cross", False,
     [("Google Drive", "service"), ("2026-01-20", "date"), ("Tampa General", "organization")],
     [],
     "where did dad's medical records move so all three siblings could work in parallel",
     "shared cloud folder medical records family access discharge planning"),
    # --- 42 ---
    ("SilverCloud's CBT module replaced the weekly in-person therapy for aunt Lila's post-widowhood depression screening because the Kaiser referral finally covered the digital program on 2026-03-04.", "decision", "cross", False,
     [("SilverCloud", "service"), ("Lila", "person"), ("Kaiser", "organization"), ("2026-03-04", "date"), ("CBT", "concept")],
     [("SilverCloud", "Kaiser", "COMMUNICATES_WITH")],
     "which digital mental-health tool insurance actually covered for aunt Lila",
     "digital CBT widowhood depression coverage referral elder mental health"),
    # --- 43 ---
    ("The Notion database that my partner Jonas built tracks the six caregivers rotating through mom's week, and the Telegram bot fires a heads-up when the Saturday-night slot is still uncovered on Thursday morning.", "architecture", "cross", False,
     [("Notion", "tool"), ("Jonas", "person"), ("Telegram", "service")],
     [("Notion", "Telegram", "COMMUNICATES_WITH"), ("Jonas", "Notion", "USES")],
     "what custom system tracks mom's weekly caregiver rotation and flags coverage gaps",
     "custom caregiver database bot alert weekly rotation shift coverage"),
    # --- 44 ---
    ("Confusion spiked when the Alexa Together activity feed showed a 4am 'light on in kitchen' event for dad on 2026-02-28 and we could not tell whether it was the cat or a wandering episode until the Ring doorbell clip cleared it up.", "problem", "cross", False,
     [("Confusion", "emotion"), ("Alexa Together", "service"), ("2026-02-28", "date"), ("Ring", "service")],
     [("Alexa Together", "Ring", "COMMUNICATES_WITH")],
     "how did we figure out if the 4am kitchen alert for dad was a real wander event",
     "activity feed ambient alert false positive wandering dementia verification"),
    # --- 45 ---
    ("DocuSign replaced the notary-in-the-living-room workflow for mom's updated durable power of attorney on 2026-03-22 because Florida finally honored remote online notarization for healthcare directives.", "decision", "cross", False,
     [("DocuSign", "service"), ("2026-03-22", "date"), ("Florida", "place")],
     [("DocuSign", "Florida", "DEPLOYED_ON")],
     "how did mom's updated power of attorney get notarized without a home visit",
     "remote online notarization power of attorney healthcare directive state"),
    # --- 46 ---
    ("Prefers the Jitterbug Smart4 over the Lively Flip for dad because the Smart4 actually runs the MyChart app for his MRI images while the Flip's feature-phone OS blocks every patient-portal workflow.", "preference", "cross", False,
     [("Jitterbug Smart4", "infrastructure"), ("Lively Flip", "infrastructure"), ("MyChart", "service"), ("MRI", "concept")],
     [("Jitterbug Smart4", "Lively Flip", "PREFERS"), ("Jitterbug Smart4", "MyChart", "USES")],
     "which senior phone does dad need so he can actually view his scan results",
     "senior phone smartphone versus feature phone patient portal imaging"),
    # --- 47 ---
    ("Regret lingered after the 2026-02-12 night dad's Amazon Echo Show 8 couldn't reach Alexa Together because the Xfinity outage in Tampa cut the Wi-Fi and the only backup was the landline we had disconnected the month before.", "problem", "cross", False,
     [("Regret", "emotion"), ("2026-02-12", "date"), ("Echo Show 8", "infrastructure"), ("Alexa Together", "service"), ("Xfinity", "organization"), ("Tampa", "place")],
     [],
     "what communication gap got exposed during the February Tampa internet outage",
     "isp outage communication backup landline disconnect single point failure"),
    # --- 48 ---
    ("Moved mom's voice-banking archive off the iPhone Voice Memos into the ModelTalker platform on 2026-03-25 because ModelTalker can actually synthesize her voice back onto the Tobii Dynavox after the laryngeal cancer progression.", "milestone", "cross", False,
     [("iPhone", "infrastructure"), ("Voice Memos", "service"), ("ModelTalker", "service"), ("2026-03-25", "date"), ("Tobii Dynavox", "infrastructure")],
     [("ModelTalker", "Voice Memos", "REPLACES"), ("ModelTalker", "Tobii Dynavox", "COMMUNICATES_WITH")],
     "where did mom's voice recordings move so they could drive her AAC device",
     "voice banking synthesis AAC device laryngeal cancer communication"),
    # --- 49 ---
    ("The AARP Medicare Advantage decision-guide PDF on 2026-10-04 flagged the new UnitedHealthcare Chronic SNP that the medicare.gov Plan Finder underweighted because the dual-eligibility screen wasn't obvious in the Plan Finder UI.", "reference", "cross", False,
     [("AARP", "organization"), ("2026-10-04", "date"), ("PDF", "concept"), ("UnitedHealthcare", "organization"), ("medicare.gov", "service")],
     [("AARP", "medicare.gov", "PREFERS")],
     "which guide surfaced the Chronic SNP option the main Plan Finder underweighted",
     "medicare advantage chronic special needs plan dual eligibility comparison"),
    # --- 50 ---
    ("Joy surged on the 2026-04-09 family Zoom when aunt Lila used the GrandPad's one-touch button to share the photo of her ninetieth-birthday cake, and for the first time she had driven the call herself.", "milestone", "cross", False,
     [("Joy", "emotion"), ("2026-04-09", "date"), ("Zoom", "service"), ("Lila", "person"), ("GrandPad", "infrastructure")],
     [("GrandPad", "Zoom", "USES")],
     "when did aunt Lila first drive a family video call on her own",
     "simplified tablet video call elder independence milestone birthday"),
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
