"""One-off emitter for shared-base batch-251 — personal domain (guitar and piano practice: instruments, amps, pedals, method books, pedagogy).

Writes 50 rows to data/v2/shared/batch_251.tmp.jsonl with ids shared-12501..12550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_251.tmp.jsonl"
ID_OFFSET = 12500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("Picked the Fender Stratocaster over the Telecaster for blues practice because the middle pickup position gives the glassy quack I'd been chasing in the Hendrix transcriptions.", "decision", "personal", False,
     [("Fender Stratocaster", "tool"), ("Telecaster", "tool"), ("blues", "activity")],
     [("Fender Stratocaster", "Telecaster", "PREFERS"), ("Fender Stratocaster", "blues", "APPLIES_TO")],
     "which Fender body did I settle on for blues woodshedding and what pickup position sold me",
     "fender stratocaster telecaster middle pickup blues hendrix practice"),
    # --- 2 --- architecture
    ("The home practice setup routes the Gibson Les Paul Standard into a Klon Centaur, then an Ibanez Tube Screamer, and finally a Fender Twin Reverb for the cleanest overdrive stack I've assembled.", "architecture", "personal", False,
     [("Gibson Les Paul Standard", "tool"), ("Klon Centaur", "tool"), ("Ibanez Tube Screamer", "tool"), ("Fender Twin Reverb", "tool")],
     [("Gibson Les Paul Standard", "Klon Centaur", "USES"), ("Klon Centaur", "Ibanez Tube Screamer", "USES"), ("Ibanez Tube Screamer", "Fender Twin Reverb", "USES")],
     "how is my home overdrive chain wired from the Les Paul through to the Twin Reverb",
     "les paul klon centaur tube screamer twin reverb overdrive chain"),
    # --- 3 --- milestone
    ("Finally played the Bach Inventions No. 4 in D minor from memory after six weeks of slow work with the Hanon Virtuoso Pianist warmups in the mornings.", "milestone", "personal", False,
     [("Bach Inventions", "publication"), ("Hanon Virtuoso Pianist", "publication"), ("No. 4 in D minor", "event")],
     [("Bach Inventions", "Hanon Virtuoso Pianist", "RELATED_TO")],
     "which two-part invention did I finally nail from memory and what warmup book carried me there",
     "bach invention d minor memory hanon virtuoso pianist warmup six weeks"),
    # --- 4 --- fact
    ("The Taylor 814ce lives in the living room on a permanent stand so I pick it up between meetings instead of fighting a case latch each time.", "fact", "personal", False,
     [("Taylor 814ce", "tool"), ("living room", "place")],
     [("Taylor 814ce", "living room", "LOCATED_IN")],
     "where does the Taylor acoustic live in the house and why was the case retired from daily use",
     "taylor 814ce living room stand case latch between meetings acoustic"),
    # --- 5 --- reference
    ("Mark Levine's Jazz Theory Book is the single best reference I own for voicing ii-V-I progressions on piano and the rootless voicings chapter alone paid for the book twice.", "reference", "personal", False,
     [("Mark Levine", "person"), ("Jazz Theory Book", "publication"), ("piano", "tool")],
     [("Jazz Theory Book", "Mark Levine", "AUTHORED_BY"), ("Jazz Theory Book", "piano", "APPLIES_TO")],
     "which jazz theory reference anchors my ii-V-I voicing work on piano and which chapter stands out",
     "mark levine jazz theory book rootless voicing ii v i piano reference"),
    # --- 6 --- decision
    ("Replaced the gigging amp with a Kemper Profiler for local shows after the Fender Twin Reverb's weight finally wrecked my back on a stairs-only load-in.", "decision", "personal", False,
     [("Kemper Profiler", "tool"), ("Fender Twin Reverb", "tool")],
     [("Kemper Profiler", "Fender Twin Reverb", "REPLACES")],
     "which amp did I swap out of the gig rig after a bad load-in and what replaced it",
     "kemper profiler fender twin reverb gig load in weight back stairs"),
    # --- 7 --- architecture
    ("The silent practice rig runs the Fractal Axe-Fx III over headphones with the Helix LT as the studio backup; both feed the DAW so I can re-amp takes without hauling the real Marshall JCM800 upstairs.", "architecture", "personal", False,
     [("Fractal Axe-Fx III", "tool"), ("Helix LT", "tool"), ("Marshall JCM800", "tool"), ("DAW", "tool")],
     [("Fractal Axe-Fx III", "DAW", "USES"), ("Helix LT", "DAW", "USES")],
     "how is the silent modeller chain set up to avoid running the JCM800 at night",
     "axe fx fractal helix lt marshall jcm800 silent headphone daw reamp"),
    # --- 8 --- preference
    ("I much prefer the Nord Stage 4 over the Yamaha CP88 for live work because the organ section feels closer to a real Hammond under the fingers.", "preference", "personal", False,
     [("Nord Stage 4", "tool"), ("Yamaha CP88", "tool"), ("Hammond", "tool")],
     [("Nord Stage 4", "Yamaha CP88", "PREFERS")],
     "which stage keyboard do I reach for over the Yamaha and what section sealed the preference",
     "nord stage 4 yamaha cp88 hammond organ live stage keyboard prefer"),
    # --- 9 --- problem
    ("The Strymon Timeline kept dumping its presets after a brownout; swapped to a conditioned power supply and the patches have stayed put for three months now.", "problem", "personal", False,
     [("Strymon Timeline", "tool"), ("conditioned power supply", "tool")],
     [("conditioned power supply", "Strymon Timeline", "FIXES")],
     "what caused the Timeline to keep losing its presets and how did I finally stop it",
     "strymon timeline preset lose brownout power supply condition dump"),
    # --- 10. noise ---
    ("The neighbour's cat has started sitting on the windowsill at practice time and stares through the glass until I break out the acoustic.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- milestone
    ("Sight-read the entire first book of Czerny Op 299 cover to cover this week at tempo; the fingering discipline from the Hanon routine clearly paid off.", "milestone", "personal", False,
     [("Czerny Op 299", "publication"), ("Hanon", "publication")],
     [("Czerny Op 299", "Hanon", "BUILDS_ON")],
     "which Czerny book did I just read cover to cover and which warmup discipline made it possible",
     "czerny op 299 sight read cover hanon fingering tempo first book"),
    # --- 12 --- decision
    ("Switched the daily piano practice from the Kawai VPC1 with Pianoteq to the Roland RD-2000 because the Roland's graded hammer action matches the Steinway Model B at my teacher's studio more faithfully.", "decision", "personal", False,
     [("Kawai VPC1", "tool"), ("Pianoteq", "tool"), ("Roland RD-2000", "tool"), ("Steinway Model B", "tool")],
     [("Roland RD-2000", "Kawai VPC1", "REPLACES"), ("Roland RD-2000", "Steinway Model B", "RELATED_TO")],
     "which digital piano took over my daily practice slot and what action feel drove the change",
     "kawai vpc1 pianoteq roland rd 2000 steinway model b hammer action daily"),
    # --- 13 --- architecture
    ("Jazz standards practice runs out of the Real Book on the stand with Jamey Aebersold play-along tracks piped through the Yamaha CP88; I loop eight bars at a time to drill the changes.", "architecture", "personal", False,
     [("Real Book", "publication"), ("Jamey Aebersold", "person"), ("Yamaha CP88", "tool")],
     [("Real Book", "Jamey Aebersold", "RELATED_TO")],
     "how is my standards drilling loop wired with the Real Book, Aebersold tracks, and the stage keyboard",
     "real book jamey aebersold yamaha cp88 play along loop eight bar standard"),
    # --- 14 --- fact
    ("The Martin D-28 sits in a humidified case at forty-five percent because the last winter pulled the top enough to buzz on the low E.", "fact", "personal", False,
     [("Martin D-28", "tool"), ("humidified case", "tool")],
     [("Martin D-28", "humidified case", "LOCATED_IN")],
     "how do I store the Martin to keep the top from buzzing in winter and at what humidity",
     "martin d 28 humidified case forty five percent winter top low e buzz"),
    # --- 15 --- preference
    ("When noodling late at night I reach for the Gibson ES-335 through the Vox AC30 on low volume; the semi-hollow body feels more forgiving than the Les Paul on tired hands.", "preference", "personal", False,
     [("Gibson ES-335", "tool"), ("Vox AC30", "tool"), ("Les Paul", "tool")],
     [("Gibson ES-335", "Les Paul", "PREFERS")],
     "which guitar and amp do I pick for late-night noodling and why over the Les Paul",
     "gibson es 335 vox ac30 les paul late night semi hollow tired hand"),
    # --- 16 --- reference
    ("Alfred's Piano Basic Course sits on the shelf for students; for adult beginners I still think it has the clearest progression from middle C to independent two-hand reading.", "reference", "personal", False,
     [("Alfred's Piano Basic Course", "publication"), ("middle C", "concept")],
     [("Alfred's Piano Basic Course", "middle C", "APPLIES_TO")],
     "which adult-beginner piano method do I still recommend and what progression makes it the pick",
     "alfred piano basic course adult beginner middle c two hand progression"),
    # --- 17 --- decision
    ("Chose the Collings OM2H over a second Taylor for fingerstyle practice because the shorter scale and Adirondack top give more headroom under a heavy thumb.", "decision", "personal", False,
     [("Collings OM2H", "tool"), ("Taylor", "tool"), ("Adirondack", "concept"), ("fingerstyle", "activity")],
     [("Collings OM2H", "Taylor", "PREFERS"), ("Collings OM2H", "fingerstyle", "APPLIES_TO")],
     "which OM body won out for fingerstyle work and what construction detail sold it",
     "collings om2h taylor adirondack top fingerstyle thumb headroom scale"),
    # --- 18 --- fact
    ("Hit a full ninety minutes on the scales and arpeggios routine today without the grey fatigue that used to set in around the F-sharp minor cycle.", "fact", "personal", False,
     [("scales and arpeggios", "activity"), ("F-sharp minor", "concept")],
     [("scales and arpeggios", "F-sharp minor", "HAS_PART")],
     "how long did today's scales-and-arpeggios block run and which key used to stall the routine",
     "scales arpeggio ninety minute f sharp minor fatigue routine full cycle"),
    # --- 19 --- architecture
    ("Ear training runs from a small Anki deck fed by exported intervals and chord qualities; I do fifteen minutes before coffee and ten before bed, seven days a week.", "architecture", "personal", False,
     [("Anki", "tool"), ("Ear training", "activity"), ("intervals", "concept"), ("chord qualities", "concept")],
     [("Anki", "Ear training", "APPLIES_TO"), ("Anki", "intervals", "USES"), ("Anki", "chord qualities", "USES")],
     "how is my daily ear training scheduled and what tool drives the spaced repetition",
     "anki ear training interval chord quality coffee bed fifteen ten minute"),
    # --- 20 --- fact
    ("The Gretsch White Falcon lives in a climate-controlled closet off the practice room because the Cadillac G tailpiece is a magnet for dust in the rehearsal corner.", "fact", "personal", False,
     [("Gretsch White Falcon", "tool"), ("climate-controlled closet", "place"), ("practice room", "place")],
     [("Gretsch White Falcon", "climate-controlled closet", "LOCATED_IN")],
     "where does the White Falcon actually live between sessions and why not the open stand",
     "gretsch white falcon climate closet practice room cadillac g tailpiece dust"),
    # --- 21 --- decision
    ("Committed to the Suzuki method for the nephew's violin path while keeping the Hal Leonard method as my own guitar spine; mixing the two just confused both of us.", "decision", "personal", False,
     [("Suzuki method", "method"), ("Hal Leonard method", "method"), ("nephew", "person"), ("violin", "tool"), ("guitar", "tool")],
     [("Suzuki method", "violin", "APPLIES_TO"), ("Hal Leonard method", "guitar", "APPLIES_TO")],
     "how did I split the two teaching methods between my nephew's violin and my own guitar work",
     "suzuki hal leonard method nephew violin guitar split confuse mix teaching"),
    # --- 22 --- decision
    ("Weekly lesson prep dumps four measure blocks into a practice journal on paper; the digital side stays in MuseScore for new arrangements so I don't mix analysis with draft writing.", "decision", "personal", False,
     [("practice journal", "tool"), ("MuseScore", "tool"), ("Weekly lesson", "event")],
     [("MuseScore", "Weekly lesson", "APPLIES_TO")],
     "how do I split analysis and arrangement work between the paper journal and MuseScore",
     "practice journal musescore weekly lesson four measure block paper draft arrange"),
    # --- 23 --- preference
    ("For classical study I much prefer the Bösendorfer Imperial at the academy rehearsal space over the Fazioli F278; the extra bass octaves make the Rachmaninoff prelude feel right.", "preference", "personal", False,
     [("Bösendorfer Imperial", "tool"), ("Fazioli F278", "tool"), ("academy rehearsal space", "place"), ("Rachmaninoff", "person")],
     [("Bösendorfer Imperial", "Fazioli F278", "PREFERS"), ("Bösendorfer Imperial", "academy rehearsal space", "LOCATED_IN")],
     "which concert grand do I pick for Rachmaninoff work at the academy and what feature sells it",
     "bosendorfer imperial fazioli f278 academy rachmaninoff prelude bass octave prefer"),
    # --- 24 --- milestone
    ("Completed the first book of Chopin Études at performance tempo on the Steinway Model B this Saturday; took three years end to end.", "milestone", "personal", False,
     [("Chopin Études", "publication"), ("Steinway Model B", "tool"), ("Saturday", "date")],
     [("Chopin Études", "Steinway Model B", "APPLIES_TO")],
     "which etude set did I finish at tempo on the Steinway and how long did the three-year arc take",
     "chopin etudes first book steinway model b saturday three year complete"),
    # --- 25 --- reference
    ("Jamey Aebersold Volume 1 How to Play Jazz stays on the piano rack as the first stop for rhythm-section play-alongs; the tempo range is friendly for working slow.", "reference", "personal", False,
     [("Jamey Aebersold Volume 1", "publication"), ("piano rack", "place"), ("rhythm-section", "concept")],
     [("Jamey Aebersold Volume 1", "rhythm-section", "APPLIES_TO")],
     "which Aebersold volume is the go-to rhythm-section play-along and where does it live",
     "jamey aebersold volume 1 piano rack rhythm section play along tempo slow"),
    # --- 26 --- decision
    ("Settled on the Two Rock Studio Signature for the main studio amp after a month of A/B tests against the Mesa Boogie Mark V; the clean headroom matters more for session work than high-gain flexibility.", "decision", "personal", False,
     [("Two Rock Studio Signature", "tool"), ("Mesa Boogie Mark V", "tool"), ("session work", "activity")],
     [("Two Rock Studio Signature", "Mesa Boogie Mark V", "PREFERS"), ("Two Rock Studio Signature", "session work", "APPLIES_TO")],
     "which studio amp won the A/B and what criterion beat the Mesa's high-gain range",
     "two rock studio signature mesa boogie mark v a b session clean headroom"),
    # --- 27 --- architecture
    ("Sight-reading drills happen cold every morning: three minutes on Bach Inventions, three minutes on the Well-Tempered Clavier, and three on whatever jazz standard the wheel lands on.", "architecture", "personal", False,
     [("Sight-reading", "activity"), ("Bach Inventions", "publication"), ("Well-Tempered Clavier", "publication")],
     [("Sight-reading", "Bach Inventions", "USES"), ("Sight-reading", "Well-Tempered Clavier", "USES")],
     "how is the morning sight-reading block split across Bach and a standard each day",
     "sight reading bach invention wtc well tempered clavier jazz standard wheel three"),
    # --- 28 --- problem
    ("The Eventide H9 kept glitching a preset swap mid-song at the last open mic; firmware 5.9 dropped the bug and two rehearsals later it's been clean.", "problem", "personal", False,
     [("Eventide H9", "tool"), ("firmware 5.9", "tool"), ("open mic", "event")],
     [("firmware 5.9", "Eventide H9", "FIXES")],
     "what caused the H9's mid-song preset glitch at the open mic and which firmware cleared it",
     "eventide h9 firmware 5 9 preset swap glitch open mic rehearsal mid song"),
    # --- 29 --- fact
    ("The Kawai Shigeru SK5 at the Sunday recital hall is tuned to 442 Hz because the violin section insists; I adapt my ear before the run-through each week.", "fact", "personal", False,
     [("Kawai Shigeru SK5", "tool"), ("Sunday recital hall", "place"), ("442 Hz", "concept"), ("violin section", "organization")],
     [("Kawai Shigeru SK5", "Sunday recital hall", "LOCATED_IN"), ("Kawai Shigeru SK5", "violin section", "APPLIES_TO")],
     "why does the Sunday hall's Shigeru get tuned sharp and what do I adjust before rehearsal",
     "kawai shigeru sk5 sunday recital hall 442 hz violin section tuning ear"),
    # --- 30 --- decision
    ("Dropped the Jazzmaster from the primary rotation after the tremolo drift on the B string kept ruining takes; the Paul Reed Smith Custom 24 stays in its slot.", "decision", "personal", False,
     [("Jazzmaster", "tool"), ("Paul Reed Smith Custom 24", "tool")],
     [("Paul Reed Smith Custom 24", "Jazzmaster", "REPLACES")],
     "which guitar left the primary rotation because of tremolo drift and what held its place",
     "jazzmaster paul reed smith prs custom 24 tremolo drift b string rotation"),
    # --- 31 --- architecture
    ("Recording takes get a Quad Cortex in the chain as a DI monitor while the actual signal goes into the Fender Twin Reverb and a ribbon mic; double tracks sit eight cents apart for width.", "architecture", "personal", False,
     [("Quad Cortex", "tool"), ("Fender Twin Reverb", "tool"), ("ribbon mic", "tool")],
     [("Quad Cortex", "Fender Twin Reverb", "COMMUNICATES_WITH")],
     "how do the Quad Cortex and the Twin Reverb split monitor and signal duty on record days",
     "quad cortex fender twin reverb ribbon mic di monitor eight cent double track"),
    # --- 32 --- milestone
    ("Learned all twelve major scales hands together on the Yamaha C7 at quarter equals 120 this month; the Hanon sixty exercises mapped straight onto the keys I'd avoided.", "milestone", "personal", False,
     [("major scales", "concept"), ("Yamaha C7", "tool"), ("Hanon", "publication")],
     [("Hanon", "major scales", "APPLIES_TO")],
     "which scale milestone landed on the Yamaha C7 and which Hanon routine carried the avoided keys",
     "major scale twelve yamaha c7 hands together 120 hanon sixty avoid key"),
    # --- 33 --- reference
    ("The Hal Leonard Guitar Method Book 1 still opens my Tuesday lesson with a beginner; the old spiral is beat up but the fingering diagrams never got redrawn this clearly in later editions.", "reference", "personal", False,
     [("Hal Leonard Guitar Method Book 1", "publication"), ("Tuesday lesson", "event"), ("beginner", "person")],
     [("Hal Leonard Guitar Method Book 1", "beginner", "APPLIES_TO")],
     "which beginner book opens the Tuesday lesson and why the old edition over the redrawn ones",
     "hal leonard guitar method book 1 tuesday beginner fingering diagram old edition"),
    # --- 34 --- preference
    ("For solo piano study I always want the Fazioli F278 over the Yamaha C7 when both are free; the action is heavier and forces honest voicing.", "preference", "personal", False,
     [("Fazioli F278", "tool"), ("Yamaha C7", "tool"), ("solo piano", "activity")],
     [("Fazioli F278", "Yamaha C7", "PREFERS"), ("Fazioli F278", "solo piano", "APPLIES_TO")],
     "which concert grand do I choose for solo study when both are free and what feature forces honesty",
     "fazioli f278 yamaha c7 solo piano action heavy voicing honest choice"),
    # --- 35 --- decision
    ("Moved the Strymon BigSky off the amp and onto the recording desk as the master reverb for mixes; the pedalboard ambient slot now holds a small spring reverb instead.", "decision", "personal", False,
     [("Strymon BigSky", "tool"), ("recording desk", "place"), ("spring reverb", "tool"), ("pedalboard", "tool")],
     [("spring reverb", "Strymon BigSky", "REPLACES"), ("Strymon BigSky", "recording desk", "LOCATED_IN")],
     "where did the BigSky move in my signal flow and what replaced it on the pedalboard",
     "strymon bigsky recording desk master reverb pedalboard spring ambient slot"),
    # --- 36 --- architecture
    ("Jazz theory homework runs in parallel with the Mark Levine book on the left and the Real Book on the right; I write out reharmonised changes in pencil on the facing page.", "architecture", "personal", False,
     [("Mark Levine book", "publication"), ("Real Book", "publication"), ("Jazz theory homework", "activity")],
     [("Jazz theory homework", "Mark Levine book", "USES"), ("Jazz theory homework", "Real Book", "USES")],
     "how is my theory homework physically laid out between Levine and the Real Book",
     "mark levine book real book jazz theory homework reharmonise pencil parallel"),
    # --- 37 --- fact
    ("Weekly piano lessons happen at Catherine's studio on Thursdays at seven; she's been teaching for twenty-two years and knows every fingering trick in the Chopin literature.", "fact", "personal", False,
     [("Catherine", "person"), ("Thursdays", "date"), ("Chopin literature", "publication")],
     [("Catherine", "Chopin literature", "KNOWS")],
     "when and with whom do I take the weekly piano lesson and what does she specialise in",
     "catherine thursday piano lesson seven chopin literature fingering twenty two"),
    # --- 38 --- milestone
    ("Ran the first full pass of Bach's Well-Tempered Clavier Book I preludes this quarter; the C-sharp major prelude was the one that finally unlocked after eight weeks of separate-hands work.", "milestone", "personal", False,
     [("Well-Tempered Clavier Book I", "publication"), ("C-sharp major prelude", "event")],
     [("Well-Tempered Clavier Book I", "C-sharp major prelude", "HAS_PART")],
     "which WTC book did I finish a first pass on and which prelude was the late breakthrough",
     "well tempered clavier book i wtc c sharp major prelude eight week hand"),
    # --- 39 --- decision
    ("Picked Pianoteq as the silent practice engine over physical acoustic recording because the latency on the Kawai VPC1 stays under four milliseconds and the Steinway D model is convincing on headphones.", "decision", "personal", False,
     [("Pianoteq", "tool"), ("Kawai VPC1", "tool"), ("Steinway D", "tool"), ("silent practice", "activity")],
     [("Pianoteq", "silent practice", "APPLIES_TO"), ("Pianoteq", "Kawai VPC1", "USES"), ("Pianoteq", "Steinway D", "USES")],
     "which modelling engine won the silent-practice pick and what latency and model sealed it",
     "pianoteq kawai vpc1 steinway d silent practice latency four millisecond headphone"),
    # --- 40 --- reference
    ("Czerny Op 299 The School of Velocity is still my go-to for finger independence drills; number twenty-three in C is the one every student stumbles on and remembers later.", "reference", "personal", False,
     [("Czerny Op 299", "publication"), ("School of Velocity", "publication"), ("number twenty-three in C", "event")],
     [("Czerny Op 299", "School of Velocity", "IS_A")],
     "which Czerny volume do I lean on for finger independence and which number trips every student",
     "czerny op 299 school of velocity finger independence number twenty three c"),
    # --- 41 --- architecture
    ("Pedalboard power routes a Cioks DC7 through a Furman conditioner, then splits into the Klon Centaur and the Eventide H9 on isolated outputs; dirty outputs feed the Ibanez Tube Screamer and the tuner.", "architecture", "personal", False,
     [("Cioks DC7", "tool"), ("Furman", "tool"), ("Klon Centaur", "tool"), ("Eventide H9", "tool"), ("Ibanez Tube Screamer", "tool"), ("tuner", "tool")],
     [("Cioks DC7", "Furman", "USES"), ("Cioks DC7", "Klon Centaur", "USES"), ("Cioks DC7", "Eventide H9", "USES"), ("Cioks DC7", "Ibanez Tube Screamer", "USES")],
     "how does the pedalboard power distribute clean and dirty rails across digital and analog pedals",
     "cioks dc7 furman klon eventide h9 tube screamer tuner isolated dirty power"),
    # --- 42 --- milestone
    ("Memorised the Chopin Ballade No. 1 down to the coda on the Bösendorfer Imperial last Friday after a three-month slog; the octave run still needs two more weeks of slow work.", "milestone", "personal", False,
     [("Chopin Ballade No. 1", "publication"), ("Bösendorfer Imperial", "tool"), ("Friday", "date")],
     [("Chopin Ballade No. 1", "Bösendorfer Imperial", "APPLIES_TO")],
     "which ballade did I memorise on the Bösendorfer and what section still needs slow work",
     "chopin ballade no 1 bosendorfer imperial friday three month coda octave"),
    # --- 43. noise ---
    ("My upstairs neighbour has taken up the accordion on Sunday mornings and the building is split roughly evenly on whether that's charming or grounds for a polite email.", "fact", "noise", True, [], [], None, None),
    # --- 44 --- problem
    ("Telecaster-country tones kept sounding brittle through every modeller preset I tried; stacking the Tube Screamer into a mildly-cranked Vox AC30 finally got the bloom back that real tubes give.", "problem", "personal", False,
     [("Telecaster", "tool"), ("Tube Screamer", "tool"), ("Vox AC30", "tool"), ("country", "activity")],
     [("Tube Screamer", "Vox AC30", "USES"), ("Telecaster", "country", "APPLIES_TO")],
     "what tone problem did the Tube Screamer into the AC30 fix for Telecaster country work",
     "telecaster tube screamer vox ac30 country brittle modeller tube bloom fix"),
    # --- 45 --- decision
    ("Chose to leave the Marshall JCM800 set up in the basement studio year-round rather than hauling it per session; the nightly warm-up routine actually happens now.", "decision", "personal", False,
     [("Marshall JCM800", "tool"), ("basement studio", "place"), ("nightly warm-up routine", "activity")],
     [("Marshall JCM800", "basement studio", "LOCATED_IN"), ("Marshall JCM800", "nightly warm-up routine", "APPLIES_TO")],
     "why did I stop hauling the JCM800 and what habit showed up once it lived in place",
     "marshall jcm800 basement studio haul nightly warm up routine session"),
    # --- 46 --- architecture
    ("Scales practice on guitar mirrors the Hanon structure on piano: thirds, fourths, and broken arpeggios over a metronome click at rising tempos with the Paul Reed Smith Custom 24 plugged direct.", "architecture", "personal", False,
     [("Hanon", "publication"), ("Paul Reed Smith Custom 24", "tool"), ("metronome", "tool"), ("thirds", "concept"), ("fourths", "concept")],
     [("Hanon", "thirds", "USES"), ("Hanon", "fourths", "USES")],
     "how does my guitar scale routine mirror Hanon and what signal path does it use",
     "hanon structure scale guitar third fourth arpeggio metronome prs direct tempo"),
    # --- 47 --- fact
    ("The Fazioli F278 at the conservatory is reserved for masterclass Wednesdays, so most of my lesson weeks hit the Steinway Model B instead.", "fact", "personal", False,
     [("Fazioli F278", "tool"), ("conservatory", "place"), ("masterclass Wednesdays", "event"), ("Steinway Model B", "tool")],
     [("Fazioli F278", "conservatory", "LOCATED_IN"), ("Fazioli F278", "masterclass Wednesdays", "APPLIES_TO")],
     "when does the conservatory's Fazioli sit free and which piano do I actually touch most weeks",
     "fazioli f278 conservatory masterclass wednesday steinway model b lesson week"),
    # --- 48 --- decision
    ("Consolidated all three practice books onto a single adjustable music stand: Hanon Virtuoso Pianist, Czerny Op 299, and the Real Book stack in that order under a magnet clip.", "decision", "personal", False,
     [("Hanon Virtuoso Pianist", "publication"), ("Czerny Op 299", "publication"), ("Real Book", "publication"), ("adjustable music stand", "tool")],
     [("Hanon Virtuoso Pianist", "adjustable music stand", "LOCATED_IN"), ("Czerny Op 299", "adjustable music stand", "LOCATED_IN"), ("Real Book", "adjustable music stand", "LOCATED_IN")],
     "how did I reorganise my daily practice books onto one stand and what stays clipped on top",
     "hanon czerny op 299 real book music stand magnet clip order consolidate"),
    # --- 49 --- reference
    ("The Aebersold scale syllabus on the back of Volume 24 is the single best one-page chord-scale cheat sheet I've found; it lives laminated on the piano side table.", "reference", "personal", False,
     [("Aebersold", "person"), ("Volume 24", "publication"), ("piano side table", "place")],
     [("Volume 24", "Aebersold", "AUTHORED_BY"), ("Volume 24", "piano side table", "LOCATED_IN")],
     "which one-page chord-scale reference do I keep laminated and where does it live",
     "aebersold volume 24 chord scale syllabus laminated piano side table cheat"),
    # --- 50 --- milestone
    ("Played the first public recital on the Yamaha C7 last month: three Chopin Études and a Bill Evans standard, both memorised cold without the score on the rack.", "milestone", "personal", False,
     [("Yamaha C7", "tool"), ("Chopin Études", "publication"), ("Bill Evans", "person"), ("public recital", "event")],
     [("public recital", "Yamaha C7", "APPLIES_TO"), ("public recital", "Chopin Études", "USES"), ("public recital", "Bill Evans", "RELATED_TO")],
     "what pieces did I play at the first public recital and on which instrument",
     "yamaha c7 chopin etudes bill evans standard public recital memorise score"),
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
