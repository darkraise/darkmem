"""One-off emitter for shared-base batch-250 — personal domain (music theory: modes, chord construction, functional harmony, voice leading, counterpoint, jazz, rhythm, form, notation software).

Writes 50 rows to data/v2/shared/batch_250.tmp.jsonl with ids shared-12451..12500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_250.tmp.jsonl"
ID_OFFSET = 12450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Finally internalised that Dorian is just the major scale starting on the second degree; playing D Dorian over a C major vamp clicked after I stopped thinking about it as minor with a raised sixth.", "milestone", "personal", False,
     [("Dorian", "concept"), ("major scale", "concept"), ("D Dorian", "concept"), ("C major", "concept")],
     [("Dorian", "major scale", "BUILDS_ON")],
     "which mode finally clicked for me by treating it as the major scale from the second degree instead of altered minor",
     "dorian mode major scale second degree c major vamp raised sixth"),
    # --- 2 ---
    ("Swapped my default minor-key improv language from natural minor to Aeolian with a Phrygian borrow on the iv chord; the half-step descent to the fifth sounds much darker than the plain flat six.", "decision", "personal", False,
     [("Aeolian", "concept"), ("Phrygian", "concept"), ("natural minor", "concept"), ("iv chord", "concept")],
     [("Phrygian", "Aeolian", "APPLIES_TO"), ("Aeolian", "natural minor", "REPLACES")],
     "which mode borrow did I layer on top of Aeolian to darken the iv chord in my minor-key improv",
     "aeolian phrygian minor improv iv chord borrow half step dark"),
    # --- 3 ---
    ("Locrian still feels unusable as a tonic; the diminished fifth under the tonic triad never resolves, so I only reach for it as a passing colour on the vii half-diminished chord in minor keys.", "preference", "personal", False,
     [("Locrian", "concept"), ("diminished fifth", "concept"), ("vii half-diminished", "concept")],
     [("Locrian", "vii half-diminished", "APPLIES_TO")],
     "why do I avoid Locrian as a tonic mode and where do I actually use it instead",
     "locrian diminished fifth tonic vii half diminished minor passing"),
    # --- 4 ---
    ("Decided my Lydian go-to cadence is the I to II major-triad move; Vince Mendoza uses it constantly and the raised fourth landing on the three of the II chord sounds like film scoring.", "decision", "personal", False,
     [("Lydian", "concept"), ("I to II", "pattern"), ("II chord", "concept"), ("Vince Mendoza", "person")],
     [("Lydian", "Vince Mendoza", "APPLIES_TO"), ("I to II", "Lydian", "APPLIES_TO")],
     "which Lydian cadence did I adopt and which arranger convinced me the raised fourth sounds cinematic",
     "lydian cadence one two major triad vince mendoza raised fourth film"),
    # --- 5 ---
    ("Mixolydian is my default over dominant seventh vamps in funk; the flat seventh built into the mode means I stop accidentally landing on the leading tone and breaking the groove.", "fact", "personal", False,
     [("Mixolydian", "concept"), ("dominant seventh", "concept"), ("leading tone", "concept")],
     [("Mixolydian", "dominant seventh", "APPLIES_TO")],
     "which mode do I reach for over static dominant seventh vamps and which note am I avoiding by using it",
     "mixolydian dominant seventh vamp funk flat seven leading tone groove"),
    # --- 6 ---
    ("Ionian as a jazz sound is fine for the first eight bars of a ballad but I try not to stay there; the natural eleventh clashes with the major third so I usually pivot to Lydian by bar nine.", "preference", "personal", False,
     [("Ionian", "concept"), ("Lydian", "concept"), ("natural eleventh", "concept"), ("major third", "concept")],
     [("Lydian", "Ionian", "REPLACES")],
     "why do I leave Ionian after eight bars of a jazz ballad and which mode do I pivot to",
     "ionian lydian ballad eight bar natural eleven major third clash pivot"),
    # --- 7 ---
    ("Harmonic minor finally made sense once I heard it as Aeolian with a raised seventh to get a proper V7 in a minor key; the augmented second between flat six and natural seven is a feature, not a bug.", "fact", "personal", False,
     [("Harmonic minor", "concept"), ("Aeolian", "concept"), ("V7", "concept"), ("augmented second", "concept")],
     [("Harmonic minor", "Aeolian", "BUILDS_ON")],
     "what insight unlocked harmonic minor for me and what does the augmented second actually enable",
     "harmonic minor aeolian raised seventh v7 augmented second minor key"),
    # --- 8 ---
    ("Melodic minor ascending versus descending is a classical rule I ignore in jazz; I use melodic minor ascending in both directions because the jazz minor sound depends on the raised six and seven.", "decision", "personal", False,
     [("melodic minor", "concept"), ("jazz minor", "concept"), ("raised six", "concept")],
     [("jazz minor", "melodic minor", "BUILDS_ON")],
     "which classical melodic-minor rule do I ignore in jazz and why does the jazz minor sound need it",
     "melodic minor ascending descending jazz minor raised six seven rule"),
    # --- 9 ---
    ("Phrygian dominant is my Spanish and klezmer cheat code; it is the fifth mode of harmonic minor, so over an E7 in an A minor tune I just think A harmonic minor and all the notes are right.", "reference", "personal", False,
     [("Phrygian dominant", "concept"), ("harmonic minor", "concept"), ("E7", "concept"), ("A minor", "concept")],
     [("Phrygian dominant", "harmonic minor", "BUILDS_ON")],
     "which parent scale do I actually think when improvising Phrygian dominant over a V7 in a minor key",
     "phrygian dominant spanish klezmer harmonic minor fifth mode e7 a"),
    # --- 10. noise ---
    ("The cat has decided that sitting on the metronome is her contribution to my practice schedule.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Built a mental map of triads by stacking thirds: major is major-third then minor-third, minor flips it, diminished stacks two minor thirds, augmented stacks two major thirds.", "reference", "personal", False,
     [("triad", "concept"), ("major third", "concept"), ("minor third", "concept"), ("diminished", "concept"), ("augmented", "concept")],
     [("triad", "major third", "HAS_PART"), ("triad", "minor third", "HAS_PART")],
     "how do I construct each triad quality from stacked thirds without memorising chord formulas separately",
     "triad stack third major minor diminished augmented interval build"),
    # --- 12 ---
    ("Seventh chords are just triads with one more third on top; I stopped memorising Cmaj7 Cm7 Cdom7 Cm7b5 Cdim7 and started deriving them from the triad plus the added seventh interval.", "milestone", "personal", False,
     [("Seventh chords", "concept"), ("Cmaj7", "concept"), ("Cm7", "concept"), ("Cm7b5", "concept"), ("Cdim7", "concept")],
     [("Cmaj7", "Seventh chords", "IS_A"), ("Cm7", "Seventh chords", "IS_A")],
     "which mental shift stopped me memorising seventh-chord spellings as separate facts",
     "seventh chord triad third stack cmaj7 cm7 cm7b5 derive"),
    # --- 13 ---
    ("Extensions 9, 11, and 13 are just diatonic thirds stacked past the seventh; on a Cmaj7 the nine is D, the sharp eleven is F sharp because the natural eleven clashes, and the thirteen is A.", "reference", "personal", False,
     [("9", "concept"), ("11", "concept"), ("13", "concept"), ("Cmaj7", "concept"), ("sharp eleven", "concept")],
     [("sharp eleven", "Cmaj7", "APPLIES_TO")],
     "how do I derive ninth eleventh and thirteenth extensions and which eleventh do I raise on a major seventh",
     "extension nine eleven thirteen cmaj7 sharp eleven diatonic third"),
    # --- 14 ---
    ("Sus chords let me delay the third's commitment; Csus4 resolving to Cmaj sounds like a suspended question, and I use sus2 voicings whenever I want the chord to stay modally ambiguous.", "decision", "personal", False,
     [("Sus chords", "concept"), ("Csus4", "concept"), ("Cmaj", "concept"), ("sus2", "concept")],
     [("Csus4", "Cmaj", "APPLIES_TO"), ("Csus4", "Sus chords", "IS_A")],
     "which chord flavour do I use to delay committing to major or minor and which resolution do I rely on",
     "sus chord csus4 cmaj sus2 modal ambiguous resolve third delay"),
    # --- 15 ---
    ("add9 chords are my default acoustic-guitar sparkle voicing; Cadd9 is a C major triad plus the ninth, with no seventh in between, and fingerpicking it sounds modern without being jazzy.", "preference", "personal", False,
     [("add9", "concept"), ("Cadd9", "concept"), ("ninth", "concept")],
     [("Cadd9", "add9", "IS_A"), ("Cadd9", "ninth", "HAS_PART")],
     "which acoustic voicing is my go-to sparkle and how does it differ from a ninth chord with the seventh",
     "add9 cadd9 acoustic guitar sparkle voicing ninth no seventh"),
    # --- 16 ---
    ("Slash chords like C over E let me write a bass line without changing the upper harmony; I use C over E and C over G as stepwise passes between I and V instead of a full root-position V chord.", "architecture", "personal", False,
     [("Slash chords", "concept"), ("C over E", "concept"), ("C over G", "concept"), ("I", "concept"), ("V", "concept")],
     [("C over E", "Slash chords", "IS_A"), ("C over G", "Slash chords", "IS_A")],
     "how do I use slash chords to write bass motion without changing the underlying harmony of a progression",
     "slash chord c over e bass line stepwise pass i v voice lead"),
    # --- 17 ---
    ("Quartal voicings stacked in fourths became my McCoy Tyner cheat for modal tunes; three perfect fourths over a D Dorian bass sound richer than a D minor seventh triad-stack and leave more room for the melody.", "architecture", "personal", False,
     [("Quartal voicings", "concept"), ("McCoy Tyner", "person"), ("D Dorian", "concept"), ("D minor seventh", "concept")],
     [("Quartal voicings", "McCoy Tyner", "APPLIES_TO"), ("Quartal voicings", "D Dorian", "APPLIES_TO")],
     "which voicing style did I steal from McCoy Tyner for modal tunes and why over a Dorian bass",
     "quartal voicing fourth mccoy tyner modal d dorian minor seventh"),
    # --- 18 ---
    ("Memorised the circle of fifths by walking around it clockwise adding sharps and counterclockwise adding flats; F is at seven o'clock with one flat, B is at five with five sharps.", "milestone", "personal", False,
     [("circle of fifths", "concept"), ("F", "concept"), ("B", "concept")],
     [("F", "circle of fifths", "APPLIES_TO")],
     "how did I finally memorise the circle of fifths and where do the edge keys like F and B actually land",
     "circle of fifth clockwise sharp counter flat memorise f b"),
    # --- 19 ---
    ("Circle of fifths is also a modulation map: moving one step clockwise changes one note, so I use it to plan key changes that feel like a turn of the wrist rather than a jump-cut.", "architecture", "personal", False,
     [("Circle of fifths", "concept"), ("modulation", "concept")],
     [("modulation", "Circle of fifths", "APPLIES_TO")],
     "how do I use the circle of fifths as a modulation planning tool rather than a key-signature chart",
     "circle fifth modulation plan key change one note step smooth"),
    # --- 20 ---
    ("Functional harmony clicked when I reduced every chord to tonic, dominant, or subdominant; ii and IV both act as predominant so a ii-V-I is really just predominant to dominant to tonic.", "milestone", "personal", False,
     [("tonic", "concept"), ("dominant", "concept"), ("subdominant", "concept"), ("predominant", "concept"), ("ii-V-I", "pattern")],
     [("ii-V-I", "predominant", "HAS_PART"), ("ii-V-I", "dominant", "HAS_PART"), ("ii-V-I", "tonic", "HAS_PART")],
     "which functional reduction finally made every diatonic chord make sense to me as one of three roles",
     "functional harmony tonic dominant subdominant predominant ii v i"),
    # --- 21 ---
    ("Secondary dominants are my favourite way to spice up a stock progression: inserting a V of ii before the ii chord gives a bluesy D7 in C major that pulls properly into Dm7.", "decision", "personal", False,
     [("Secondary dominants", "concept"), ("V of ii", "concept"), ("D7", "concept"), ("Dm7", "concept"), ("C major", "concept")],
     [("D7", "Dm7", "APPLIES_TO"), ("V of ii", "Secondary dominants", "IS_A")],
     "which reharmonisation trick do I use most to pull into a diatonic chord and how does it land in C major",
     "secondary dominant v of ii d7 dm7 c major spice progression"),
    # --- 22 ---
    ("Tritone substitution lives rent-free in my head: any V7 can be replaced by the V7 a tritone away because they share the guide tones; Db7 substitutes for G7 into Cmaj7.", "reference", "personal", False,
     [("Tritone substitution", "concept"), ("V7", "concept"), ("Db7", "concept"), ("G7", "concept"), ("Cmaj7", "concept"), ("guide tones", "concept")],
     [("Db7", "G7", "REPLACES"), ("Tritone substitution", "V7", "APPLIES_TO")],
     "which substitution do I use most on V chords and which shared notes make the swap actually work",
     "tritone sub v7 db7 g7 cmaj7 guide tone share substitution"),
    # --- 23 ---
    ("The Neapolitan sixth is my secret weapon in minor keys; a first-inversion flat II major triad resolving to V sounds like a classical sigh and I wedge it into bridges constantly.", "decision", "personal", False,
     [("Neapolitan", "concept"), ("flat II", "concept"), ("V", "concept"), ("first-inversion", "concept")],
     [("Neapolitan", "V", "APPLIES_TO"), ("Neapolitan", "flat II", "IS_A")],
     "which classical chord do I keep reaching for on bridges in minor keys and which inversion makes it sing",
     "neapolitan sixth flat two first inversion minor bridge classical"),
    # --- 24 ---
    ("Augmented sixth chords come in three flavours I can never quite keep straight: Italian is three notes, French adds the major second above the bass, German adds the perfect fifth instead.", "reference", "personal", False,
     [("Augmented sixth", "concept"), ("Italian", "concept"), ("French", "concept"), ("German", "concept")],
     [("Italian", "Augmented sixth", "IS_A"), ("French", "Augmented sixth", "IS_A"), ("German", "Augmented sixth", "IS_A")],
     "how do I tell Italian French and German augmented sixths apart by their added notes above the bass",
     "augmented sixth italian french german bass added note fifth second"),
    # --- 25 ---
    ("Spent an afternoon drilling voice leading over a ii-V-I in C: the F in Dm7 drops a half-step to E in G7's third, and the F again in G7 drops to E in Cmaj7; no voice moves by more than a step.", "milestone", "personal", False,
     [("voice leading", "concept"), ("ii-V-I", "pattern"), ("Dm7", "concept"), ("G7", "concept"), ("Cmaj7", "concept")],
     [("voice leading", "ii-V-I", "APPLIES_TO")],
     "which drill made voice-leading across a ii-V-I concrete for me and which note moves twice",
     "voice lead ii v i dm7 g7 cmaj7 drill half step no jump"),
    # --- 26 ---
    ("Parallel fifths still sound wrong to my ear even in pop; I route around them by contrary motion in the outer voices or by adding a third voice that moves in the opposite direction.", "decision", "personal", False,
     [("Parallel fifths", "concept"), ("contrary motion", "concept")],
     [("contrary motion", "Parallel fifths", "FIXES")],
     "how do I avoid parallel fifths when voicing pop harmony without sounding overly academic",
     "parallel fifth contrary motion voice pop outer avoid third"),
    # --- 27 ---
    ("Working through Fux Gradus ad Parnassum one species at a time; first species whole-note-against-whole-note forced me to hear dissonance and consonance without rhythm doing the heavy lifting.", "milestone", "personal", False,
     [("Fux", "person"), ("Gradus ad Parnassum", "publication"), ("first species", "concept")],
     [("Gradus ad Parnassum", "Fux", "AUTHORED_BY"), ("first species", "Gradus ad Parnassum", "PUBLISHED_IN")],
     "which counterpoint textbook am I working through and what did the first species exercises teach me",
     "fux gradus ad parnassum species counterpoint first whole note"),
    # --- 28 ---
    ("Second species counterpoint introduces the passing tone on the weak beat; the rule I keep forgetting is that the downbeat must still be consonant, so dissonance only lives between.", "problem", "personal", False,
     [("Second species", "concept"), ("passing tone", "concept"), ("downbeat", "concept")],
     [("passing tone", "Second species", "APPLIES_TO")],
     "which second-species counterpoint rule do I keep forgetting and where is dissonance actually allowed",
     "second species passing tone weak beat downbeat consonant dissonance"),
    # --- 29 ---
    ("Bach chorales are my voice-leading sandbox; I pick one from the Riemenschneider 371 every Sunday morning and figure out why each inner voice moves where it does before looking at the reduction.", "architecture", "personal", False,
     [("Bach", "person"), ("chorale", "concept"), ("Riemenschneider 371", "publication")],
     [("chorale", "Bach", "AUTHORED_BY"), ("chorale", "Riemenschneider 371", "PUBLISHED_IN")],
     "which weekly practice routine uses Bach chorales for voice-leading study and which collection do I pull from",
     "bach chorale riemenschneider 371 voice lead sunday inner voice"),
    # --- 30 ---
    ("Figured out that the 251 in jazz is just functional harmony predominant-dominant-tonic with seventh chords; every standard is mostly stitched-together 251s in different keys.", "milestone", "personal", False,
     [("251", "pattern"), ("predominant", "concept"), ("dominant", "concept"), ("tonic", "concept"), ("seventh chord", "concept")],
     [("251", "predominant", "HAS_PART"), ("251", "dominant", "HAS_PART"), ("251", "tonic", "HAS_PART")],
     "which jazz progression did I finally hear as plain functional harmony and what are standards mostly made of",
     "251 jazz functional predominant dominant tonic seventh standard"),
    # --- 31 ---
    ("Dorian ii-V is the minor-key variant I use when the tune stays on the ii-V without resolving; a half-diminished ii and an altered V sound unresolved on purpose.", "architecture", "personal", False,
     [("Dorian ii-V", "pattern"), ("half-diminished", "concept"), ("altered V", "concept")],
     [("Dorian ii-V", "half-diminished", "HAS_PART"), ("Dorian ii-V", "altered V", "HAS_PART")],
     "which minor-key two-five variant do I use when the progression refuses to resolve and which alterations fit",
     "dorian ii v half diminished altered minor key unresolved"),
    # --- 32 ---
    ("Adopted the Barry Harris 6-diminished scale for comping over a tonic chord; alternating a C6 voicing with a Bdim7 every beat gives the bebop inner voices that move chromatically downward.", "decision", "personal", False,
     [("Barry Harris", "person"), ("6-diminished", "concept"), ("C6", "concept"), ("Bdim7", "concept")],
     [("6-diminished", "Barry Harris", "AUTHORED_BY"), ("C6", "6-diminished", "APPLIES_TO")],
     "which bebop comping device did I adopt for tonic chords and whose method is it based on",
     "barry harris six diminished c6 bdim7 comping bebop inner voice"),
    # --- 33 ---
    ("Modal interchange unlocks pop songwriting for me; borrowing a flat VI major from parallel minor into a major-key chorus adds instant gravitas without fully modulating.", "architecture", "personal", False,
     [("Modal interchange", "concept"), ("flat VI", "concept"), ("parallel minor", "concept")],
     [("flat VI", "parallel minor", "APPLIES_TO"), ("Modal interchange", "parallel minor", "USES")],
     "which borrowing technique do I use to darken a major-key chorus without modulating and which chord do I pull",
     "modal interchange flat six parallel minor major chorus borrow"),
    # --- 34 ---
    ("Negative harmony has stopped being a party trick for me; inverting a G7 around the axis between the third and fourth scale degrees in C gives a Dm6 which actually works as a reharm over the V.", "architecture", "personal", False,
     [("Negative harmony", "concept"), ("G7", "concept"), ("Dm6", "concept"), ("C", "concept")],
     [("Dm6", "G7", "REPLACES"), ("Negative harmony", "C", "APPLIES_TO")],
     "which reharmonisation technique did I finally internalise beyond a party trick and which chord does G7 map to in C",
     "negative harmony g7 dm6 c axis third fourth degree reharm"),
    # --- 35 ---
    ("Jacob Collier popularised negative harmony but the idea comes from Ernst Levy's A Theory of Harmony; I read Levy over Christmas and the axis symmetry makes more sense than Collier's YouTube explanation.", "fact", "personal", False,
     [("Jacob Collier", "person"), ("negative harmony", "concept"), ("Ernst Levy", "person"), ("A Theory of Harmony", "publication")],
     [("A Theory of Harmony", "Ernst Levy", "AUTHORED_BY"), ("negative harmony", "Ernst Levy", "BUILDS_ON")],
     "who actually wrote the theory behind negative harmony and which book did I read to understand the axis symmetry",
     "jacob collier ernst levy theory harmony negative axis symmetry"),
    # --- 36 ---
    ("Polyrhythm 3:2 is baked into every West African groove I love; practising three against two with left-hand quarters and right-hand triplets took a month before my brain stopped fusing them.", "fact", "personal", False,
     [("Polyrhythm", "concept"), ("3:2", "concept"), ("triplet", "concept")],
     [("3:2", "Polyrhythm", "IS_A")],
     "which polyrhythm took me a month of independence practice to stop hearing as a single pulse",
     "polyrhythm three two 3:2 triplet quarter independence west african"),
    # --- 37 ---
    ("Odd meters in 5/4 feel natural once I subdivide them as 3+2 or 2+3; Take Five is 3+2 and the limping feel disappears when I count aloud in two uneven groups.", "fact", "personal", False,
     [("5/4", "concept"), ("Take Five", "publication")],
     [("Take Five", "5/4", "APPLIES_TO")],
     "how do I subdivide 5/4 to make odd meters feel natural and which jazz standard uses the 3 plus 2 grouping",
     "odd meter five four take five 3+2 2+3 subdivision uneven"),
    # --- 38 ---
    ("7/8 I subdivide as 2+2+3 for most of the progressive rock I play; the final beat group of three gives the kick-drum accent that makes the meter feel inevitable instead of arbitrary.", "decision", "personal", False,
     [("7/8", "concept"), ("2+2+3", "pattern"), ("progressive rock", "concept")],
     [("2+2+3", "7/8", "APPLIES_TO")],
     "how do I subdivide 7/8 in progressive rock and which beat group carries the kick accent",
     "seven eight 7/8 2+2+3 progressive rock kick accent subdivision"),
    # --- 39 ---
    ("Swing feel is a rhythmic continuum not a ratio; slow ballads sit near a triplet 2:1, medium swing drifts toward 3:2, and very fast bebop flattens almost back to straight eighths.", "reference", "personal", False,
     [("swing", "concept"), ("triplet", "concept"), ("bebop", "concept"), ("straight eighths", "concept")],
     [("swing", "triplet", "BUILDS_ON")],
     "how does swing ratio change with tempo from ballad to bebop and where does it flatten back out",
     "swing continuum triplet ratio ballad medium bebop straight eighth"),
    # --- 40 ---
    ("Shuffle versus swing tripped me up for years; shuffle hits the triplet upbeat harder and usually implies a backbeat on two and four, swing is smoother and less rock-coded.", "problem", "personal", False,
     [("shuffle", "concept"), ("swing", "concept"), ("backbeat", "concept")],
     [("shuffle", "swing", "RELATED_TO"), ("shuffle", "backbeat", "USES")],
     "what finally separated shuffle from swing in my head and which beats does shuffle accent",
     "shuffle swing backbeat triplet upbeat two four rock smooth"),
    # --- 41 ---
    ("Son clave 3-2 is my reference pattern for Latin grooves; once I internalised the 3-2 side's three strokes on the and-of-one, two, and four I stopped flipping clave direction mid-tune.", "architecture", "personal", False,
     [("Son clave", "concept"), ("3-2", "pattern")],
     [("3-2", "Son clave", "APPLIES_TO")],
     "which Latin reference pattern did I finally internalise and which side has three strokes",
     "son clave 3-2 latin groove stroke and one two four reference"),
    # --- 42 ---
    ("Sonata form is exposition, development, recapitulation with the second-theme key returning to tonic in the recap; once I mapped it onto pop verse-chorus-bridge the architecture stopped feeling alien.", "fact", "personal", False,
     [("Sonata", "concept"), ("exposition", "concept"), ("development", "concept"), ("recapitulation", "concept")],
     [("Sonata", "exposition", "HAS_PART"), ("Sonata", "development", "HAS_PART"), ("Sonata", "recapitulation", "HAS_PART")],
     "which three-part classical form did I map onto pop verse-chorus-bridge to make it click",
     "sonata form exposition development recap tonic second theme pop"),
    # --- 43. noise ---
    ("The practice-room radiator ticks exactly on the eighth note at sixty-two beats per minute and it has ruined slow ballads for me.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("AABA song form is the backbone of the Great American Songbook; eight bars of A with a lyric, eight bars of A repeated, eight-bar bridge in a related key, and the final A wraps it.", "architecture", "personal", False,
     [("AABA", "pattern"), ("Great American Songbook", "publication"), ("bridge", "concept")],
     [("AABA", "Great American Songbook", "APPLIES_TO"), ("AABA", "bridge", "HAS_PART")],
     "which 32-bar song form underlies most standards and how many bars does each section get",
     "aaba song form great american songbook bridge thirty two bar"),
    # --- 45 ---
    ("12-bar blues is my universal jam-session fallback; the I-IV-I-V-IV-I pattern with dominant sevenths on every chord works in any key and anyone who has ever picked up an instrument can play it.", "decision", "personal", False,
     [("12-bar blues", "pattern"), ("I-IV-I-V-IV-I", "pattern"), ("dominant seventh", "concept")],
     [("I-IV-I-V-IV-I", "12-bar blues", "APPLIES_TO"), ("12-bar blues", "dominant seventh", "USES")],
     "which twelve-bar pattern is my universal jam fallback and what chord quality sits on every bar",
     "twelve bar blues i iv v dominant seventh jam session fallback"),
    # --- 46 ---
    ("Ternary ABA form is easier to write than sonata because the A returns literally rather than transformed; I use it for instrumental interludes where thematic drama is not the point.", "decision", "personal", False,
     [("Ternary", "concept"), ("ABA", "pattern"), ("sonata", "concept")],
     [("ABA", "Ternary", "IS_A"), ("Ternary", "sonata", "RELATED_TO")],
     "which three-part form do I use for instrumental interludes and why is it easier than sonata",
     "ternary aba form instrumental interlude sonata literal return"),
    # --- 47 ---
    ("Through-composed pieces force me to plan motivic development carefully; without repeated sections I cannot rely on the listener re-hearing a theme, so every bar has to feel like a consequence.", "problem", "personal", False,
     [("Through-composed", "concept"), ("motivic development", "concept")],
     [("Through-composed", "motivic development", "USES")],
     "which form challenges my motivic planning the most and why can't I lean on repetition there",
     "through composed motivic development plan repeat listener consequence"),
    # --- 48 ---
    ("Transposition by interval stopped being effortful once I drilled the circle of fifths in both directions; I can now move a lead sheet from C to E-flat on sight without a capo or notation tool.", "preference", "personal", False,
     [("Transposition", "concept"), ("circle of fifths", "concept"), ("C", "concept"), ("E-flat", "concept")],
     [("Transposition", "circle of fifths", "USES")],
     "how did drilling the circle of fifths make sight-transposition possible for me at the keyboard",
     "transposition circle fifth c e flat lead sheet sight drill"),
    # --- 49 ---
    ("Switched my main notation software from Sibelius to Dorico after the Steinberg 5 release; the flow-based architecture handles multi-movement pieces much better than Sibelius's single-score model.", "decision", "personal", False,
     [("Sibelius", "tool"), ("Dorico", "tool"), ("Steinberg 5", "date"), ("flow", "concept")],
     [("Dorico", "Sibelius", "REPLACES"), ("Dorico", "flow", "USES")],
     "which notation software did I switch to and which architectural feature sold me over Sibelius",
     "sibelius dorico steinberg flow multi movement notation switch"),
    # --- 50 ---
    ("Keep MuseScore installed for quick lead-sheet sketches and Flat.io for browser collaboration; Lilypond is my typeset-for-print tool when I need something engraving-quality and am willing to edit plain text.", "fact", "personal", False,
     [("MuseScore", "tool"), ("Flat.io", "tool"), ("Lilypond", "tool"), ("lead-sheet", "concept")],
     [("MuseScore", "lead-sheet", "APPLIES_TO")],
     "which notation tools fill my lightweight sketch collaboration and print-quality niches",
     "musescore flat io lilypond lead sheet browser collab engrave"),
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
