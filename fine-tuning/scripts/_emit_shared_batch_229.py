"""One-off emitter for shared-base batch-229 — knowledge domain (linguistics: phonetics, phonology, morphology, syntax, semantics, pragmatics, sociolinguistics, typology).

Writes 50 rows to data/v2/shared/batch_229.tmp.jsonl with ids shared-11401..11450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_229.tmp.jsonl"
ID_OFFSET = 11400

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("For the new phonetics course we adopted the IPA over the older Americanist transcription so vowel quality and tone diacritics would line up with the textbook exercises.", "decision", "knowledge", False,
     [("IPA", "theory"), ("Americanist transcription", "theory"), ("phonetics", "concept")],
     [("IPA", "Americanist transcription", "REPLACES")],
     "which transcription standard replaced the Americanist one for the phonetics course and why",
     "ipa americanist transcription phonetics vowel tone diacritic textbook"),
    # --- 2 --- architecture
    ("Formant analysis in the lab pipeline pulls F1 and F2 from a Praat script, then plots the vowel space per speaker so dialect differences surface without hand-measuring spectrograms.", "architecture", "knowledge", False,
     [("Praat", "tool"), ("F1", "concept"), ("F2", "concept"), ("vowel space", "concept")],
     [("Praat", "vowel space", "PRODUCES")],
     "how does the lab pipeline extract formants and visualise dialect differences per speaker",
     "praat formant f1 f2 vowel space dialect speaker spectrogram plot"),
    # --- 3 --- fact
    ("Voice onset time separates English /p/ from /b/ mostly by aspiration lag: voiceless stops run roughly sixty milliseconds of VOT while voiced stops hover near zero or go prevoiced.", "fact", "knowledge", False,
     [("Voice onset time", "concept"), ("VOT", "concept"), ("/p/", "concept"), ("/b/", "concept")],
     [("VOT", "Voice onset time", "RELATED_TO")],
     "which acoustic measure distinguishes English p from b and roughly what millisecond values separate them",
     "voice onset time vot aspiration voiceless voiced stop english"),
    # --- 4 --- decision
    ("For the phonology seminar we decided to teach Optimality Theory before rule-based SPE so students would meet constraint ranking before deriving surface forms through ordered rules.", "decision", "knowledge", False,
     [("Optimality Theory", "framework"), ("SPE", "framework"), ("constraint ranking", "concept")],
     [("Optimality Theory", "SPE", "PREFERS")],
     "which phonological framework did the seminar teach first and what pedagogical reason sealed the order",
     "optimality theory spe constraint ranking rule order phonology seminar"),
    # --- 5 --- reference
    ("Chomsky and Halle's Sound Pattern of English remains the canonical reference for rule-based generative phonology; later course readers treat it as the foil against which OT is introduced.", "reference", "knowledge", False,
     [("Chomsky", "person"), ("Halle", "person"), ("Sound Pattern of English", "publication"), ("OT", "framework")],
     [("Sound Pattern of English", "OT", "CONTRADICTS")],
     "which 1968 phonology reference is treated as the foil against Optimality Theory in course readers",
     "chomsky halle sound pattern english spe generative phonology ot"),
    # --- 6 --- architecture
    ("Autosegmental phonology represents tone and segments on separate tiers linked by association lines; the Obligatory Contour Principle then blocks adjacent identical tones on the same tier.", "architecture", "knowledge", False,
     [("Autosegmental phonology", "framework"), ("Obligatory Contour Principle", "concept"), ("tone", "concept"), ("association lines", "concept")],
     [("Obligatory Contour Principle", "Autosegmental phonology", "APPLIES_TO")],
     "how does autosegmental representation separate tone from segments and which principle polices tier adjacency",
     "autosegmental tier tone association line obligatory contour ocp"),
    # --- 7 --- milestone
    ("Prince and Smolensky's 1993 manuscript on Optimality Theory reframed phonology around violable ranked constraints; within a decade it displaced rule ordering in most graduate syllabi.", "milestone", "knowledge", False,
     [("Prince", "person"), ("Smolensky", "person"), ("Optimality Theory", "framework"), ("rule ordering", "concept")],
     [("Optimality Theory", "rule ordering", "REPLACES")],
     "which 1993 phonology manuscript shifted graduate syllabi from rule ordering to violable ranked constraints",
     "prince smolensky optimality theory violable constraint rank rule 1993"),
    # --- 8 --- fact
    ("Inflectional morphology marks grammatical features like tense and number without changing the part of speech, whereas derivational morphology produces a new lexeme often of a different category.", "fact", "knowledge", False,
     [("Inflectional morphology", "concept"), ("derivational morphology", "concept"), ("lexeme", "concept")],
     [("Inflectional morphology", "derivational morphology", "CONTRADICTS")],
     "which two morphology types split on whether the process changes part of speech or produces a new lexeme",
     "inflectional derivational morphology lexeme part speech tense number"),
    # --- 9 --- reference
    ("For the typology unit the reading list uses Baker's The Polysynthesis Parameter to frame how polysynthesis in languages like Mohawk packs a full clause into a single verbal word.", "reference", "knowledge", False,
     [("Baker", "person"), ("The Polysynthesis Parameter", "publication"), ("Mohawk", "language"), ("polysynthesis", "concept")],
     [("The Polysynthesis Parameter", "polysynthesis", "APPLIES_TO")],
     "which reference frames polysynthesis in languages like Mohawk for the typology unit",
     "baker polysynthesis parameter mohawk verbal word typology clause"),
    # --- 10. noise ---
    ("The department coffee machine started grinding on odd beats this week and nobody wants to be the one to call the service line again.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- architecture
    ("Semitic morphology is modelled as root-and-pattern: a triconsonantal root like k-t-b interleaves with a vocalic template to produce katab, kaatib, kitaab without concatenative affixation.", "architecture", "knowledge", False,
     [("Semitic morphology", "concept"), ("triconsonantal root", "concept"), ("k-t-b", "concept"), ("vocalic template", "concept")],
     [("triconsonantal root", "vocalic template", "RELATED_TO")],
     "how does Semitic morphology derive forms like katab and kitaab without concatenative affixation",
     "semitic root pattern triconsonantal ktb vocalic template arabic hebrew"),
    # --- 12 --- milestone
    ("Chomsky's 1957 Syntactic Structures launched generative grammar by arguing that finite rule systems could generate the infinite set of grammatical sentences a native speaker accepts.", "milestone", "knowledge", False,
     [("Chomsky", "person"), ("Syntactic Structures", "publication"), ("generative grammar", "framework")],
     [("Syntactic Structures", "generative grammar", "APPLIES_TO")],
     "which 1957 monograph launched generative grammar and what was its central productivity argument",
     "chomsky syntactic structures 1957 generative grammar finite rule infinite"),
    # --- 13 --- decision
    ("For the syntax proseminar we moved from Government and Binding to the Minimalist Program; Merge and Agree let students derive the same constructions with fewer stipulated modules.", "decision", "knowledge", False,
     [("Government and Binding", "framework"), ("Minimalist Program", "framework"), ("Merge", "concept"), ("Agree", "concept")],
     [("Minimalist Program", "Government and Binding", "REPLACES")],
     "which syntactic framework replaced Government and Binding in the proseminar and which two operations drove the shift",
     "government binding minimalist merge agree syntax proseminar module"),
    # --- 14 --- architecture
    ("HPSG encodes grammatical information as typed feature structures unified across sign descriptions; constraints sit in the lexicon rather than in transformational derivations.", "architecture", "knowledge", False,
     [("HPSG", "framework"), ("typed feature structures", "concept"), ("sign", "concept"), ("lexicon", "concept")],
     [("HPSG", "typed feature structures", "USES")],
     "how does HPSG encode grammatical constraints and where do most of them live relative to derivations",
     "hpsg typed feature structure sign unification lexicon constraint"),
    # --- 15 --- architecture
    ("LFG splits grammatical representation into c-structure for constituency and f-structure for functional relations; the two are linked by a projection function rather than by movement.", "architecture", "knowledge", False,
     [("LFG", "framework"), ("c-structure", "concept"), ("f-structure", "concept"), ("projection function", "concept")],
     [("LFG", "c-structure", "USES"), ("LFG", "f-structure", "USES")],
     "which two representations does LFG use for syntax and how are they related without movement",
     "lfg c structure f projection function constituency grammatical relation"),
    # --- 16 --- fact
    ("Dependency grammar describes sentence structure as head-dependent links between words, making it a natural fit for free-word-order languages and most current parser treebanks.", "fact", "knowledge", False,
     [("Dependency grammar", "framework"), ("head", "concept"), ("dependent", "concept"), ("treebank", "concept")],
     [("Dependency grammar", "treebank", "APPLIES_TO")],
     "what makes head-dependent link models the default for treebanks and flexible word-order analysis",
     "dependency grammar head dependent free word order treebank parser"),
    # --- 17 --- decision
    ("For the combinatory-category course we picked Steedman's CCG over categorial grammar alternatives because type-raising and function composition let coordination and extraction fall out of the calculus directly.", "decision", "knowledge", False,
     [("Steedman", "person"), ("CCG", "framework"), ("type-raising", "concept"), ("function composition", "concept"), ("categorial grammar", "framework")],
     [("CCG", "categorial grammar", "PREFERS"), ("CCG", "type-raising", "USES")],
     "which grammar flavour did the combinatory-category course pick and which operations sealed the choice",
     "steedman ccg combinatory category type raising composition coordination"),
    # --- 18 --- decision
    ("For the lexical-semantics track we preferred Jackendoff's Conceptual Semantics over pure Montagovian translation; it gave students a representation for event structure beyond truth conditions.", "decision", "knowledge", False,
     [("Jackendoff", "person"), ("Conceptual Semantics", "framework"), ("Montagovian translation", "framework"), ("event structure", "concept")],
     [("Conceptual Semantics", "Montagovian translation", "PREFERS")],
     "which semantic framework did the lexical-semantics track prefer over Montagovian translation and why",
     "jackendoff conceptual semantics montague event structure lexical truth"),
    # --- 19 --- milestone
    ("Richard Montague's 1970 paper English as a Formal Language fused natural-language syntax with higher-order logic, effectively founding formal semantics as a research programme.", "milestone", "knowledge", False,
     [("Richard Montague", "person"), ("English as a Formal Language", "publication"), ("formal semantics", "framework"), ("higher-order logic", "concept")],
     [("English as a Formal Language", "formal semantics", "APPLIES_TO")],
     "which 1970 paper founded formal semantics by binding English syntax to higher-order logic",
     "montague english formal language 1970 semantics higher order logic"),
    # --- 20 --- architecture
    ("For the semantics core we chose to build compositional interpretation on the lambda calculus: every syntactic node carries a typed meaning, and mother nodes come from functional application over their daughters.", "decision", "knowledge", False,
     [("lambda calculus", "concept"), ("compositional interpretation", "concept"), ("functional application", "concept"), ("typed meaning", "concept")],
     [("compositional interpretation", "lambda calculus", "USES")],
     "how does the course compute sentence meaning compositionally using typed nodes and functional application",
     "lambda calculus compositional functional application typed meaning node"),
    # --- 21 --- fact
    ("For the anaphora unit we adopted Dynamic semantics over static truth-conditional treatments because meaning as context-change potential let an indefinite introduce a discourse referent that later pronouns pick up cleanly.", "decision", "knowledge", False,
     [("Dynamic semantics", "framework"), ("context-change potential", "concept"), ("discourse referent", "concept"), ("truth-conditional", "concept")],
     [("Dynamic semantics", "truth-conditional", "PREFERS"), ("Dynamic semantics", "discourse referent", "USES")],
     "which semantic framework did the anaphora unit adopt over static truth-conditional treatments and what won the choice",
     "dynamic semantics context change discourse referent anaphora indefinite pronoun"),
    # --- 22 --- decision
    ("For the donkey-anaphora problem the seminar chose File Change Semantics over classical Montague; Heim's file cards handled indefinites as referent introductions without ad-hoc scoping.", "decision", "knowledge", False,
     [("File Change Semantics", "framework"), ("Montague", "person"), ("Heim", "person"), ("donkey-anaphora", "concept")],
     [("File Change Semantics", "Montague", "PREFERS")],
     "which semantic framework did the seminar pick over classical Montague to handle donkey anaphora",
     "file change semantics heim donkey anaphora indefinite montague card"),
    # --- 23 --- reference
    ("H.P. Grice's Logic and Conversation is still the default pragmatics reading; his four maxims of quantity, quality, relation, and manner frame the implicature examples students work through.", "reference", "knowledge", False,
     [("H.P. Grice", "person"), ("Logic and Conversation", "publication"), ("maxims", "concept"), ("implicature", "concept")],
     [("Logic and Conversation", "maxims", "APPLIES_TO")],
     "which Grice text anchors the pragmatics reading and which four maxims drive the implicature exercises",
     "grice logic conversation maxim quantity quality relation manner implicature"),
    # --- 24 --- fact
    ("Conversational implicature is cancellable and context-dependent, so saying some but not all in a follow-up cancels the scalar inference that some implied not all.", "fact", "knowledge", False,
     [("Conversational implicature", "concept"), ("scalar inference", "concept"), ("some", "concept")],
     [("scalar inference", "Conversational implicature", "APPLIES_TO")],
     "which property of conversational implicature lets a scalar inference from some to not all be cancelled in context",
     "implicature cancellable scalar some all quantity context pragmatic"),
    # --- 25 --- architecture
    ("Presupposition projects through entailment-cancelling operators unless something explicitly plugs it; the projection problem drives the family-of-sentences test students run on each operator.", "architecture", "knowledge", False,
     [("Presupposition", "concept"), ("projection problem", "concept"), ("family-of-sentences test", "method")],
     [("family-of-sentences test", "Presupposition", "APPLIES_TO")],
     "which diagnostic probes presupposition projection through entailment-cancelling operators in class",
     "presupposition projection problem family sentences test operator plug"),
    # --- 26 --- decision
    ("For the pragmatics elective we adopted Sperber and Wilson's Relevance Theory over strict Gricean derivations; it let students predict implicatures without stacking four separate maxim violations.", "decision", "knowledge", False,
     [("Sperber", "person"), ("Wilson", "person"), ("Relevance Theory", "framework"), ("Gricean", "framework")],
     [("Relevance Theory", "Gricean", "PREFERS")],
     "which pragmatics framework did the elective adopt instead of strict Gricean derivations and what did it simplify",
     "sperber wilson relevance theory gricean maxim implicature derive"),
    # --- 27 --- milestone
    ("William Labov's 1963 Martha's Vineyard study tied centralised diphthongs to local identity and launched variationist sociolinguistics as a quantitative field rather than an impressionistic one.", "milestone", "knowledge", False,
     [("William Labov", "person"), ("Martha's Vineyard", "place"), ("variationist sociolinguistics", "framework"), ("centralised diphthongs", "concept")],
     [("Martha's Vineyard", "variationist sociolinguistics", "APPLIES_TO")],
     "what did the early-sixties island fieldwork link to islander identity and how did it reshape the field",
     "labov marthas vineyard 1963 centralised diphthong variationist identity"),
    # --- 28 --- fact
    ("Labov's department-store study on postvocalic r in New York stratified production by social class through brief service encounters rather than long sociolinguistic interviews.", "fact", "knowledge", False,
     [("Labov", "person"), ("department-store study", "method"), ("postvocalic r", "concept"), ("New York", "place")],
     [("department-store study", "postvocalic r", "APPLIES_TO")],
     "which brief-encounter method did Labov use in New York to stratify postvocalic r by social class",
     "labov department store postvocalic r new york class interview"),
    # --- 29 --- reference
    ("Penelope Eckert's Jocks and Burnouts ethnography is on the sociolinguistics reading list because it foregrounds communities of practice over broad demographic buckets.", "reference", "knowledge", False,
     [("Penelope Eckert", "person"), ("Jocks and Burnouts", "publication"), ("communities of practice", "concept")],
     [("Jocks and Burnouts", "communities of practice", "APPLIES_TO")],
     "which Eckert ethnography anchors the communities-of-practice unit on the sociolinguistics reading list",
     "eckert jocks burnouts ethnography community practice sociolinguistics demographic"),
    # --- 30 --- architecture
    ("The variationist pipeline codes each token for a dependent phonetic variable plus speaker, style, and lexical class predictors, then fits a mixed-effects logistic model in Rbrul.", "architecture", "knowledge", False,
     [("variationist pipeline", "pattern"), ("Rbrul", "tool"), ("mixed-effects logistic", "method"), ("speaker", "concept")],
     [("variationist pipeline", "Rbrul", "USES")],
     "which statistical pipeline does the variationist lab use to fit speaker and style effects on phonetic variables",
     "variationist token code speaker style lexical mixed effect rbrul"),
    # --- 31 --- milestone
    ("Greenberg's 1963 paper Some Universals of Grammar with Particular Reference to the Order of Meaningful Elements proposed implicational universals that still frame word-order typology.", "milestone", "knowledge", False,
     [("Greenberg", "person"), ("Some Universals of Grammar", "publication"), ("implicational universals", "concept"), ("word-order typology", "concept")],
     [("Some Universals of Grammar", "implicational universals", "APPLIES_TO")],
     "what early-sixties monograph grounded modern word-order typology on implicational patterns across languages",
     "greenberg universals 1963 implicational word order typology element"),
    # --- 32 --- fact
    ("Greenberg universal 20 states that noun-phrase internal order of demonstrative, numeral, and adjective is mostly mirrored when the nominal heads to the right rather than the left.", "fact", "knowledge", False,
     [("Greenberg universal 20", "concept"), ("demonstrative", "concept"), ("numeral", "concept"), ("adjective", "concept")],
     [],
     "which Greenberg universal constrains the order of demonstrative numeral and adjective within a noun phrase",
     "greenberg universal 20 demonstrative numeral adjective mirror noun"),
    # --- 33 --- reference
    ("WALS serves as the go-to typological atlas in the course; its feature maps on basic word order, adposition type, and case marking are referenced in most problem sets.", "reference", "knowledge", False,
     [("WALS", "publication"), ("word order", "concept"), ("adposition", "concept"), ("case marking", "concept")],
     [("WALS", "word order", "APPLIES_TO")],
     "which typological atlas does the course rely on for basic word order and case-marking feature maps",
     "wals world atlas language typology word order adposition case map"),
    # --- 34 --- architecture
    ("Optimality Theory factors phonological generation into GEN and EVAL: GEN proposes candidate outputs and EVAL picks the one with the least serious ranked-constraint violation.", "architecture", "knowledge", False,
     [("Optimality Theory", "framework"), ("GEN", "concept"), ("EVAL", "concept"), ("ranked-constraint", "concept")],
     [("Optimality Theory", "GEN", "USES"), ("Optimality Theory", "EVAL", "USES")],
     "which two components split candidate generation from evaluation in Optimality Theory",
     "optimality theory gen eval candidate rank constraint violation factor"),
    # --- 35 --- problem
    ("A recurring problem in fieldwork transcription is that novice transcribers confuse narrow IPA and broad IPA, so we now require narrow brackets for allophonic detail and slashes for phonemic abstraction.", "problem", "knowledge", False,
     [("fieldwork transcription", "concept"), ("narrow IPA", "concept"), ("broad IPA", "concept"), ("allophonic", "concept")],
     [],
     "which transcription-notation discipline did the fieldwork course impose after novices kept mixing narrow and broad IPA",
     "fieldwork transcription narrow broad ipa allophone phoneme bracket slash"),
    # --- 36 --- decision
    ("For low-resource language documentation we preferred ELAN over plain audacity annotation; tiered alignment to the media file made later forced-alignment export a one-click job.", "decision", "knowledge", False,
     [("ELAN", "tool"), ("audacity", "tool"), ("forced-alignment", "method"), ("tiered alignment", "concept")],
     [("ELAN", "audacity", "PREFERS")],
     "what annotation application won the documentation bake-off thanks to tier-to-media linking and easy aligner export",
     "elan audacity tier alignment forced align documentation low resource"),
    # --- 37 --- milestone
    ("The Leipzig Glossing Rules project consolidated interlinear gloss conventions in 2008 so cross-linguistic papers could be read without each author inventing a private abbreviation set.", "milestone", "knowledge", False,
     [("Leipzig Glossing Rules", "theory"), ("interlinear gloss", "concept"), ("abbreviation", "concept")],
     [("Leipzig Glossing Rules", "interlinear gloss", "APPLIES_TO")],
     "what late-2000s standards effort let comparative papers drop bespoke morpheme-label tables",
     "leipzig glossing rule 2008 interlinear abbreviation cross linguistic"),
    # --- 38 --- fact
    ("The ergative-absolutive alignment seen in languages like Dyirbal marks the subject of a transitive verb distinctly from both the intransitive subject and the transitive object, flipping the accusative pattern.", "fact", "knowledge", False,
     [("ergative-absolutive", "concept"), ("Dyirbal", "language"), ("accusative", "concept"), ("transitive verb", "concept")],
     [("ergative-absolutive", "accusative", "CONTRADICTS")],
     "how does ergative-absolutive alignment in languages like Dyirbal differ from the accusative pattern",
     "ergative absolutive dyirbal accusative alignment transitive intransitive"),
    # --- 39 --- preference
    ("The lab prefers IPA with explicit tone letters over Chao digits for tonal-language transcription because spectrogram alignment training generalises better when pitch shape is visually anchored.", "preference", "knowledge", False,
     [("IPA", "theory"), ("tone letters", "concept"), ("Chao digits", "theory"), ("spectrogram", "concept")],
     [("tone letters", "Chao digits", "PREFERS")],
     "which tonal notation does the lab prefer and how does it help students read spectrograms",
     "ipa tone letter chao digit tonal spectrogram alignment visual"),
    # --- 40 --- architecture
    ("Minimalist derivations use Merge to build hierarchical structure and Agree to share feature values between a probe and a goal; movement is recast as internal Merge with a copy.", "architecture", "knowledge", False,
     [("Minimalist", "framework"), ("Merge", "concept"), ("Agree", "concept"), ("internal Merge", "concept")],
     [("Minimalist", "Merge", "USES"), ("Minimalist", "Agree", "USES")],
     "how do Merge and Agree build and link structure in Minimalist derivations and what becomes of movement",
     "minimalist merge agree internal probe goal feature movement copy"),
    # --- 41 --- milestone
    ("The 1979 publication of Kempson's Semantic Theory widened UK graduate programmes' coverage of truth-conditional semantics beyond Katz and Fodor's earlier feature-list approach.", "milestone", "knowledge", False,
     [("Kempson", "person"), ("Semantic Theory", "publication"), ("truth-conditional semantics", "framework"), ("Katz and Fodor", "framework")],
     [("Semantic Theory", "Katz and Fodor", "REPLACES")],
     "what late-seventies British textbook pushed semantics teaching past feature-list decomposition",
     "kempson semantic theory 1979 truth conditional katz fodor feature"),
    # --- 42 --- preference
    ("Students prefer dependency-bank tree diagrams over phrase-structure brackets for typology homework because cross-language comparison reads more cleanly when only head-dependent links remain.", "preference", "knowledge", False,
     [("dependency-bank", "concept"), ("phrase-structure brackets", "concept"), ("typology", "concept")],
     [("dependency-bank", "phrase-structure brackets", "PREFERS")],
     "which visualisation do students prefer for typology homework and why does it read more cleanly cross-linguistically",
     "dependency bank tree phrase structure bracket typology head link"),
    # --- 43. noise ---
    ("Somebody rearranged the shelved journals by cover colour and the librarians put a gentle sign back on Monday.", "fact", "noise", True, [], [], None, None),
    # --- 44 --- decision
    ("For the computational semantics module we picked CCG-based parsers over constituency parsers; the lambda terms fall out of the categorial derivation without a separate interpretation step.", "decision", "knowledge", False,
     [("CCG-based parsers", "tool"), ("constituency parsers", "tool"), ("lambda terms", "concept"), ("computational semantics", "framework")],
     [("CCG-based parsers", "constituency parsers", "PREFERS")],
     "which parser style did the computational semantics module pick over constituency parsers and what did it simplify",
     "ccg parser constituency lambda categorial computational semantics"),
    # --- 45 --- problem
    ("A perennial problem in Optimality Theory is constraint ranking indeterminacy when two grammars generate the same winner; stochastic OT and partial rankings were introduced to cope.", "problem", "knowledge", False,
     [("Optimality Theory", "framework"), ("constraint ranking", "concept"), ("stochastic OT", "framework"), ("partial rankings", "concept")],
     [("stochastic OT", "constraint ranking", "IMPROVES_ON")],
     "which two extensions of Optimality Theory cope with constraint ranking indeterminacy across grammars",
     "optimality constraint rank indeterminacy stochastic partial grammar winner"),
    # --- 46 --- fact
    ("A perennial teaching problem is that undergraduate papers keep defending Sapir-Whorf strong determinism even though only weaker linguistic-relativity effects on colour naming and spatial frames survive in controlled psycholinguistic experiments.", "problem", "knowledge", False,
     [("Sapir-Whorf", "concept"), ("linguistic-relativity", "concept"), ("colour naming", "concept"), ("spatial frames", "concept")],
     [("linguistic-relativity", "Sapir-Whorf", "IMPROVES_ON")],
     "which weaker form of linguistic relativity survives controlled experiments after strong Sapir-Whorf was rejected",
     "sapir whorf linguistic relativity colour naming spatial frame experiment"),
    # --- 47 --- reference
    ("Heim and Kratzer's textbook Semantics in Generative Grammar is the default compositional-semantics course reader; its type-driven translation method walks students through the lambda machinery explicitly.", "reference", "knowledge", False,
     [("Heim and Kratzer", "person"), ("Semantics in Generative Grammar", "publication"), ("type-driven translation", "method"), ("lambda machinery", "concept")],
     [("Semantics in Generative Grammar", "type-driven translation", "APPLIES_TO")],
     "which Heim and Kratzer textbook anchors the compositional-semantics course and what method does it walk through",
     "heim kratzer semantics generative type driven translation lambda textbook"),
    # --- 48 --- architecture
    ("For the corpus-phonetics workflow we went with the Montreal Forced Aligner, Praat, and PostgreSQL together rather than ad-hoc spreadsheets, so alignment feeds formant extraction and per-token measurements land in a sliceable schema.", "decision", "knowledge", False,
     [("Montreal Forced Aligner", "tool"), ("Praat", "tool"), ("PostgreSQL", "database"), ("corpus-phonetics", "concept")],
     [("Montreal Forced Aligner", "Praat", "PRODUCES"), ("corpus-phonetics", "PostgreSQL", "USES")],
     "which three tools form the corpus-phonetics stack from alignment to database and what flows between them",
     "montreal forced aligner praat postgresql corpus phonetics formant"),
    # --- 49 --- preference
    ("For undergraduate intro to syntax we prefer dependency grammar first and phrase-structure second; dependency trees make argument roles obvious before constituency abstractions are introduced.", "preference", "knowledge", False,
     [("dependency grammar", "framework"), ("phrase-structure", "framework"), ("argument roles", "concept")],
     [("dependency grammar", "phrase-structure", "PREFERS")],
     "which syntax formalism do we teach first in the undergraduate intro and what pedagogical payoff drives the order",
     "dependency grammar phrase structure argument role undergraduate intro"),
    # --- 50 --- preference
    ("The typology reading-group preferred Comrie's Language Universals and Linguistic Typology over Croft's textbook for a first pass because Comrie's cross-linguistic examples are shorter and easier to glossing-check.", "preference", "knowledge", False,
     [("Comrie", "person"), ("Language Universals and Linguistic Typology", "publication"), ("Croft", "person"), ("typology reading-group", "concept")],
     [("Language Universals and Linguistic Typology", "Croft", "PREFERS")],
     "which typology textbook did the reading-group prefer for a first pass and why over Croft",
     "comrie language universals linguistic typology croft reading group gloss"),
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
