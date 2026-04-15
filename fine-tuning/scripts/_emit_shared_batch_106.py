"""One-off emitter for shared-base batch-106 — knowledge domain (pedagogy, education research, learning theory).

Writes 50 rows with ids shared-05251..05300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_106.tmp.jsonl"
ID_OFFSET = 5250

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Jean Piaget's genetic epistemology, developed across Geneva studies from the 1920s, models child cognition through the four stages of sensorimotor, preoperational, concrete operational, and formal operational thought.", "reference", "knowledge", False,
     [("Jean Piaget", "person"), ("genetic epistemology", "theory"), ("Geneva", "place"), ("sensorimotor", "concept"), ("preoperational", "concept"), ("formal operational", "concept")],
     [("genetic epistemology", "Jean Piaget", "AUTHORED_BY")],
     "which Swiss epistemologist mapped child cognition into four sequential operational stages",
     "Piaget Geneva stages sensorimotor concrete formal operational child"),
    # --- 2 ---
    ("Lev Vygotsky introduced the Zone of Proximal Development in Mind in Society, posthumously compiled in 1978, to describe the gap between independent performance and assisted capability.", "reference", "knowledge", False,
     [("Lev Vygotsky", "person"), ("Zone of Proximal Development", "concept"), ("Mind in Society", "publication"), ("1978", "date")],
     [("Zone of Proximal Development", "Lev Vygotsky", "AUTHORED_BY"), ("Mind in Society", "Lev Vygotsky", "AUTHORED_BY")],
     "which Soviet psychologist formulated the gap between solo and assisted performance as a developmental zone",
     "Vygotsky ZPD proximal development assisted scaffolding Mind Society"),
    # --- 3 ---
    ("Jerome Bruner's The Process of Education, published in 1960, argues that any subject can be taught in an intellectually honest form to any child at any stage through the spiral curriculum.", "reference", "knowledge", False,
     [("Jerome Bruner", "person"), ("The Process of Education", "publication"), ("1960", "date"), ("spiral curriculum", "concept")],
     [("The Process of Education", "Jerome Bruner", "AUTHORED_BY"), ("spiral curriculum", "Jerome Bruner", "AUTHORED_BY")],
     "which 1960 book proposed the spiral curriculum and the teachability of any subject",
     "Bruner Process Education spiral curriculum intellectually honest year"),
    # --- 4 ---
    ("Benjamin Bloom's 1956 Taxonomy of Educational Objectives ordered cognitive goals from knowledge through evaluation and became the backbone of learning-outcome design.", "reference", "knowledge", False,
     [("Benjamin Bloom", "person"), ("Taxonomy of Educational Objectives", "publication"), ("1956", "date"), ("cognitive goals", "concept")],
     [("Taxonomy of Educational Objectives", "Benjamin Bloom", "AUTHORED_BY")],
     "which 1956 taxonomy arranged cognitive objectives from knowledge to evaluation",
     "Bloom taxonomy cognitive domain educational objectives year"),
    # --- 5 ---
    ("The 2001 Anderson and Krathwohl revision replaces Bloom's original noun-based levels with verb-based processes and adds a separate knowledge dimension.", "decision", "knowledge", False,
     [("Anderson and Krathwohl revision", "framework"), ("2001", "date"), ("Bloom", "person"), ("knowledge dimension", "concept")],
     [("Anderson and Krathwohl revision", "Bloom", "REPLACES"), ("Anderson and Krathwohl revision", "Bloom", "IMPROVES_ON")],
     "which millennial update recast the classic objectives taxonomy as verbs and added an orthogonal content axis",
     "Anderson Krathwohl revised objectives taxonomy verbs content axis"),
    # --- 6 ---
    ("David Kolb's Experiential Learning, published in 1984, frames learning as a four-stage cycle of concrete experience, reflective observation, abstract conceptualisation, and active experimentation.", "reference", "knowledge", False,
     [("David Kolb", "person"), ("Experiential Learning", "publication"), ("1984", "date"), ("concrete experience", "concept"), ("abstract conceptualisation", "concept")],
     [("Experiential Learning", "David Kolb", "AUTHORED_BY")],
     "which 1984 book laid out a four-stage experiential cycle from concrete experience to active experimentation",
     "Kolb experiential learning cycle four stage reflection abstract"),
    # --- 7 ---
    ("Richard Mayer's Cognitive Theory of Multimedia Learning, consolidated in the 2001 Cambridge Handbook chapter, derives twelve instructional design principles from dual-channel processing.", "reference", "knowledge", False,
     [("Richard Mayer", "person"), ("Cognitive Theory of Multimedia Learning", "theory"), ("2001", "date"), ("dual-channel processing", "concept")],
     [("Cognitive Theory of Multimedia Learning", "Richard Mayer", "AUTHORED_BY")],
     "whose handbook account turned twin-channel ideas into a dozen design rules for slideware and video",
     "Mayer slideware video design rules twin channel handbook"),
    # --- 8 ---
    ("John Sweller's Cognitive Load Theory, introduced in a 1988 Cognitive Science paper, distinguishes intrinsic, extraneous, and germane load as levers for instructional design.", "reference", "knowledge", False,
     [("John Sweller", "person"), ("Cognitive Load Theory", "theory"), ("Cognitive Science", "publication"), ("1988", "date"), ("intrinsic", "concept"), ("extraneous", "concept"), ("germane load", "concept")],
     [("Cognitive Load Theory", "John Sweller", "AUTHORED_BY")],
     "which 1988 paper split instructional load into intrinsic, extraneous, and germane components",
     "Sweller cognitive load intrinsic extraneous germane instructional year"),
    # --- 9 ---
    ("Robert and Elizabeth Bjork's desirable difficulties programme argues that interventions slowing initial performance, such as spacing and interleaving, improve long-term retention.", "reference", "knowledge", False,
     [("Robert and Elizabeth Bjork", "person"), ("desirable difficulties", "concept"), ("spacing", "method"), ("interleaving", "method"), ("long-term retention", "finding")],
     [("desirable difficulties", "Robert and Elizabeth Bjork", "AUTHORED_BY")],
     "which UCLA memory couple argued that harder practice pays off weeks later even when it hurts today",
     "UCLA harder practice pays off weeks later spaced mixed"),
    # --- 10. noise ---
    ("Let me double-check that effect size against the 2023 meta-analysis before I quote it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("John Hattie's Visible Learning, published in 2009, synthesised over 800 meta-analyses and benchmarked classroom influences against a hinge-point effect size of 0.40.", "reference", "knowledge", False,
     [("John Hattie", "person"), ("Visible Learning", "publication"), ("2009", "date"), ("effect size", "concept")],
     [("Visible Learning", "John Hattie", "AUTHORED_BY")],
     "which New Zealand megasynthesis popularised the 0.40 d-value threshold for what counts as worthwhile teaching",
     "Hattie hinge point Visible Learning barometer influences ranked"),
    # --- 12 ---
    ("John Dewey's Democracy and Education, published in 1916, frames schooling as a laboratory of democratic life and grounds the progressive education movement.", "reference", "knowledge", False,
     [("John Dewey", "person"), ("Democracy and Education", "publication"), ("1916", "date"), ("progressive education", "concept")],
     [("Democracy and Education", "John Dewey", "AUTHORED_BY"), ("progressive education", "John Dewey", "AUTHORED_BY")],
     "which 1916 Dewey book treated schools as laboratories of democratic life",
     "Dewey Democracy Education progressive schooling laboratory year"),
    # --- 13 ---
    ("Maria Montessori opened the first Casa dei Bambini in San Lorenzo, Rome, in 1907 and codified the prepared environment and self-directed work cycle that define her method.", "milestone", "knowledge", False,
     [("Maria Montessori", "person"), ("Casa dei Bambini", "place"), ("San Lorenzo", "place"), ("Rome", "place"), ("1907", "date"), ("prepared environment", "concept")],
     [("Casa dei Bambini", "Maria Montessori", "AUTHORED_BY")],
     "when and where did Montessori open the first Casa dei Bambini",
     "Montessori Casa Bambini San Lorenzo Rome prepared environment year"),
    # --- 14 ---
    ("Rudolf Steiner launched the first Waldorf school in Stuttgart in 1919 for the children of Waldorf-Astoria factory workers, centring anthroposophy and seven-year developmental phases.", "milestone", "knowledge", False,
     [("Rudolf Steiner", "person"), ("Waldorf school", "concept"), ("Stuttgart", "place"), ("1919", "date"), ("anthroposophy", "concept")],
     [("Waldorf school", "Rudolf Steiner", "AUTHORED_BY")],
     "when did Steiner launch the first Waldorf school in Stuttgart",
     "Steiner Waldorf Stuttgart anthroposophy seven year phases founding"),
    # --- 15 ---
    ("Ernst von Glasersfeld's radical constructivism, articulated through the 1990s, holds that learners actively construct knowledge rather than receiving objective content.", "reference", "knowledge", False,
     [("Ernst von Glasersfeld", "person"), ("radical constructivism", "theory"), ("learners", "concept")],
     [("radical constructivism", "Ernst von Glasersfeld", "AUTHORED_BY")],
     "whose radical constructivism argues learners build knowledge rather than receive it",
     "Glasersfeld radical constructivism knowledge construction learners"),
    # --- 16 ---
    ("The 2006 Kirschner, Sweller, and Clark paper in Educational Psychologist argued that minimally guided instruction fails novices and should yield to direct instruction.", "decision", "knowledge", False,
     [("Kirschner, Sweller, and Clark", "person"), ("2006", "date"), ("Educational Psychologist", "publication"), ("minimally guided instruction", "method"), ("direct instruction", "method")],
     [("direct instruction", "minimally guided instruction", "REPLACES"), ("direct instruction", "minimally guided instruction", "IMPROVES_ON")],
     "which 2006 paper argued direct instruction should replace minimally guided approaches for novices",
     "Kirschner Sweller Clark minimally guided direct instruction Educational Psychologist"),
    # --- 17 ---
    ("The OECD Programme for International Student Assessment, first administered in 2000, measures fifteen-year-olds in reading, mathematics, and science across participating economies every three years.", "reference", "knowledge", False,
     [("OECD", "organization"), ("Programme for International Student Assessment", "publication"), ("2000", "date"), ("reading", "concept"), ("mathematics", "concept"), ("science", "concept")],
     [("Programme for International Student Assessment", "OECD", "AUTHORED_BY")],
     "which triennial OECD assessment has measured fifteen-year-olds since 2000",
     "PISA OECD fifteen year triennial reading mathematics science assessment"),
    # --- 18 ---
    ("The Trends in International Mathematics and Science Study, run by the IEA from 1995, benchmarks grade four and grade eight achievement against curriculum-referenced frameworks.", "reference", "knowledge", False,
     [("Trends in International Mathematics and Science Study", "publication"), ("IEA", "organization"), ("1995", "date"), ("grade four", "concept"), ("grade eight", "concept")],
     [("Trends in International Mathematics and Science Study", "IEA", "AUTHORED_BY")],
     "which IEA study has benchmarked grade four and grade eight maths and science since 1995",
     "TIMSS IEA fourth eighth grade mathematics science curriculum benchmark"),
    # --- 19 ---
    ("Carol Dweck's Mindset, published in 2006, reframes achievement around a growth mindset of malleable ability that supersedes older fixed-trait framings.", "reference", "knowledge", False,
     [("Carol Dweck", "person"), ("Mindset", "publication"), ("2006", "date"), ("growth mindset", "theory"), ("fixed-trait framings", "concept")],
     [("Mindset", "Carol Dweck", "AUTHORED_BY"), ("growth mindset", "fixed-trait framings", "REPLACES"), ("growth mindset", "fixed-trait framings", "IMPROVES_ON")],
     "which Stanford psychologist's trade book argued intelligence is grown rather than fixed at birth",
     "Dweck mindset popular volume malleability praise effort Carol"),
    # --- 20 ---
    ("Henry Roediger and Jeffrey Karpicke's 2006 Psychological Science paper showed that repeated retrieval practice improves on repeated re-reading for long-term retention.", "reference", "knowledge", False,
     [("Henry Roediger", "person"), ("Jeffrey Karpicke", "person"), ("2006", "date"), ("Psychological Science", "publication"), ("retrieval practice", "method"), ("re-reading", "method")],
     [("retrieval practice", "re-reading", "IMPROVES_ON"), ("retrieval practice", "Henry Roediger", "AUTHORED_BY")],
     "which Washington University lab demonstrated the testing effect against passive rehearsal in a flagship journal",
     "Roediger Karpicke swahili word-pair delayed recall retrieval recall"),
    # --- 21 ---
    ("Albert Bandura's Social Learning Theory, formalised in 1977, positions observational learning and self-efficacy as central mechanisms of classroom behaviour change.", "reference", "knowledge", False,
     [("Albert Bandura", "person"), ("Social Learning Theory", "theory"), ("1977", "date"), ("observational learning", "concept"), ("self-efficacy", "concept")],
     [("Social Learning Theory", "Albert Bandura", "AUTHORED_BY")],
     "whose late-seventies framework made modelling and belief-in-one's-capability core levers of pupil conduct",
     "Bandura Bobo doll vicarious reinforcement agency SLT imitation"),
    # --- 22 ---
    ("Paulo Freire's Pedagogy of the Oppressed, published in Portuguese in 1968, rejects the banking model of education and proposes dialogic problem-posing pedagogy.", "reference", "knowledge", False,
     [("Paulo Freire", "person"), ("Pedagogy of the Oppressed", "publication"), ("1968", "date"), ("banking model", "concept"), ("problem-posing pedagogy", "method")],
     [("Pedagogy of the Oppressed", "Paulo Freire", "AUTHORED_BY"), ("problem-posing pedagogy", "banking model", "REPLACES")],
     "which 1968 Freire book replaced the banking model with problem-posing dialogic pedagogy",
     "Freire Pedagogy Oppressed banking problem posing dialogic year"),
    # --- 23 ---
    ("Howard Gardner's Frames of Mind, published in 1983, advances the theory of multiple intelligences against the single general-factor account of ability.", "reference", "knowledge", False,
     [("Howard Gardner", "person"), ("Frames of Mind", "publication"), ("1983", "date"), ("multiple intelligences", "theory"), ("general-factor account", "concept")],
     [("Frames of Mind", "Howard Gardner", "AUTHORED_BY"), ("multiple intelligences", "general-factor account", "IMPROVES_ON")],
     "which Harvard book from the early eighties split cognitive talents into several kinds rather than one",
     "Gardner MI linguistic musical spatial bodily kinesthetic IQ critique"),
    # --- 24 ---
    ("Jean Lave and Etienne Wenger's Situated Learning, published in 1991, frames learning as legitimate peripheral participation within communities of practice.", "reference", "knowledge", False,
     [("Jean Lave", "person"), ("Etienne Wenger", "person"), ("Situated Learning", "publication"), ("1991", "date"), ("legitimate peripheral participation", "concept"), ("communities of practice", "concept")],
     [("Situated Learning", "Jean Lave", "AUTHORED_BY"), ("Situated Learning", "Etienne Wenger", "AUTHORED_BY")],
     "which early nineties anthropological monograph cast apprenticeship as the core unit of learning",
     "Lave Wenger tailors midwives quartermasters legitimate peripheral apprentice"),
    # --- 25 ---
    ("The socio-constructivist turn in education research, consolidated through the 1990s, builds on Vygotsky by framing cognition as culturally mediated and distributed across tools and peers.", "architecture", "knowledge", False,
     [("socio-constructivist turn", "theory"), ("Vygotsky", "person"), ("cognition", "concept"), ("tools and peers", "concept")],
     [("socio-constructivist turn", "Vygotsky", "BUILDS_ON")],
     "which theoretical turn extended Vygotsky by distributing cognition across tools and peers",
     "socio constructivist Vygotsky distributed cognition cultural mediation"),
    # --- 26 ---
    ("The Review of Educational Research has served as the American Educational Research Association's flagship synthesis journal since its founding in 1931.", "reference", "knowledge", False,
     [("Review of Educational Research", "publication"), ("American Educational Research Association", "organization"), ("1931", "date")],
     [("Review of Educational Research", "American Educational Research Association", "AUTHORED_BY")],
     "which AERA journal has served as its flagship synthesis venue since 1931",
     "Review Educational Research AERA synthesis flagship journal year"),
    # --- 27 ---
    ("Educational Psychologist, published by Division 15 of the American Psychological Association, has hosted many of the field's most-cited theoretical essays since its 1963 launch.", "reference", "knowledge", False,
     [("Educational Psychologist", "publication"), ("Division 15", "organization"), ("American Psychological Association", "organization"), ("1963", "date")],
     [("Educational Psychologist", "Division 15", "AUTHORED_BY")],
     "which APA Division 15 journal has hosted the field's theoretical essays since 1963",
     "Educational Psychologist APA Division 15 theoretical essays founding"),
    # --- 28 ---
    ("B. F. Skinner's programmed instruction, piloted through his Harvard teaching machines in the 1950s, applied operant conditioning to curriculum sequencing.", "reference", "knowledge", False,
     [("B. F. Skinner", "person"), ("programmed instruction", "method"), ("Harvard", "organization"), ("1950s", "date"), ("operant conditioning", "theory")],
     [("programmed instruction", "B. F. Skinner", "AUTHORED_BY"), ("programmed instruction", "operant conditioning", "BUILDS_ON")],
     "which behaviourist pioneer built mid-century drilling devices that ordered lessons by reinforcement schedule",
     "Skinner teaching machine frames linear branching shaping TMI programmed"),
    # --- 29 ---
    ("Benjamin Bloom's 1984 two-sigma problem observed that one-to-one mastery tutoring lifted average students roughly two standard deviations above conventional classroom peers.", "reference", "knowledge", False,
     [("Benjamin Bloom", "person"), ("two-sigma problem", "finding"), ("1984", "date"), ("mastery tutoring", "method")],
     [("two-sigma problem", "Benjamin Bloom", "AUTHORED_BY")],
     "which mid-eighties article asked why private coaching beats a whole-class lesson by two sd units",
     "Bloom 2 sigma Educational Researcher mastery tutoring comparison"),
    # --- 30 ---
    ("Universal Design for Learning, codified by CAST in the 2000s, organises instruction around multiple means of engagement, representation, and action and expression.", "reference", "knowledge", False,
     [("Universal Design for Learning", "framework"), ("CAST", "organization"), ("2000s", "date"), ("engagement", "concept"), ("representation", "concept")],
     [("Universal Design for Learning", "CAST", "AUTHORED_BY")],
     "which three-pronged accessibility-rooted framework grew out of a Massachusetts nonprofit's early-2000s guidelines",
     "UDL CAST Rose Meyer barriers-to-learning curriculum variability profile"),
    # --- 31 ---
    ("Shulman's 1986 Educational Researcher article introduced pedagogical content knowledge as a distinct teacher-knowledge category bridging subject matter and pedagogy.", "reference", "knowledge", False,
     [("Shulman", "person"), ("1986", "date"), ("Educational Researcher", "publication"), ("pedagogical content knowledge", "concept")],
     [("pedagogical content knowledge", "Shulman", "AUTHORED_BY")],
     "which Stanford scholar's mid-eighties essay named the know-how that sits between a discipline and teaching it",
     "Shulman PCK missing paradigm signature pedagogies subject category"),
    # --- 32 ---
    ("Formative assessment, defined through Paul Black and Dylan Wiliam's 1998 Assessment in Education review, improves on summative-only testing by feeding evidence back into instruction.", "reference", "knowledge", False,
     [("Formative assessment", "method"), ("Paul Black", "person"), ("Dylan Wiliam", "person"), ("1998", "date"), ("Assessment in Education", "publication"), ("summative-only testing", "method")],
     [("Formative assessment", "Paul Black", "AUTHORED_BY"), ("Formative assessment", "summative-only testing", "IMPROVES_ON")],
     "which 1998 Black and Wiliam review redefined formative assessment as feedback into instruction",
     "Black Wiliam formative assessment Inside Black Box summative year"),
    # --- 33 ---
    ("The flipped classroom, popularised by Jonathan Bergmann and Aaron Sams around 2007, replaces in-class lecture with pre-class video so live time supports practice.", "decision", "knowledge", False,
     [("flipped classroom", "method"), ("Jonathan Bergmann", "person"), ("Aaron Sams", "person"), ("2007", "date"), ("in-class lecture", "method")],
     [("flipped classroom", "in-class lecture", "REPLACES"), ("flipped classroom", "Jonathan Bergmann", "AUTHORED_BY")],
     "which Colorado chemistry-teacher duo swapped direct-teach time for homework screencasts in the late 2000s",
     "Bergmann Sams Woodland Park inverted instruction asynchronous video"),
    # --- 34. noise ---
    ("Hmm, I should re-check whether that pre-registration covered the delayed post-test or only the immediate one.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Eric Mazur's peer instruction, developed at Harvard in the early 1990s, restructures introductory physics around ConcepTests and neighbour discussion instead of monologue lecture.", "reference", "knowledge", False,
     [("Eric Mazur", "person"), ("peer instruction", "method"), ("Harvard", "organization"), ("1990s", "date"), ("ConcepTests", "concept"), ("monologue lecture", "method")],
     [("peer instruction", "Eric Mazur", "AUTHORED_BY"), ("peer instruction", "monologue lecture", "IMPROVES_ON")],
     "whose early-1990s Harvard method rebuilt introductory physics around ConcepTests and peer discussion",
     "Mazur peer instruction ConcepTests Harvard physics decade"),
    # --- 36 ---
    ("Anders Ericsson's deliberate practice framework, consolidated in a 1993 Psychological Review article, argues that expert performance is built from effortful, feedback-rich practice rather than raw hours.", "reference", "knowledge", False,
     [("Anders Ericsson", "person"), ("deliberate practice", "theory"), ("1993", "date"), ("Psychological Review", "publication"), ("expert performance", "concept")],
     [("deliberate practice", "Anders Ericsson", "AUTHORED_BY")],
     "whose 1993 Psychological Review article defined deliberate practice as feedback-rich effortful work",
     "Ericsson deliberate practice Psychological Review expertise 1993"),
    # --- 37 ---
    ("Piaget's constructivism and Vygotsky's socio-cultural account depend on fundamentally different units of analysis, with Piaget centring the individual and Vygotsky the mediated social activity.", "problem", "knowledge", False,
     [("Piaget", "person"), ("constructivism", "theory"), ("Vygotsky", "person"), ("socio-cultural account", "theory"), ("mediated social activity", "concept")],
     [("socio-cultural account", "mediated social activity", "DEPENDS_ON"), ("constructivism", "Piaget", "AUTHORED_BY")],
     "how do Piaget's and Vygotsky's units of analysis differ in learning theory",
     "Piaget Vygotsky individual social mediation unit analysis constructivism"),
    # --- 38 ---
    ("Hermann Ebbinghaus's 1885 memory curve, reported in Uber das Gedachtnis, remains the empirical anchor for later spacing and retrieval-practice research in education.", "reference", "knowledge", False,
     [("Hermann Ebbinghaus", "person"), ("memory curve", "finding"), ("1885", "date"), ("Uber das Gedachtnis", "publication"), ("spacing", "method"), ("retrieval-practice", "method")],
     [("memory curve", "Hermann Ebbinghaus", "AUTHORED_BY"), ("spacing", "memory curve", "BUILDS_ON")],
     "which 1885 study produced the forgetting curve that anchors modern spacing research",
     "Ebbinghaus forgetting curve memory Uber Gedachtnis spacing year"),
    # --- 39 ---
    ("Self-Determination Theory, developed by Edward Deci and Richard Ryan from 1985, organises motivation around autonomy, competence, and relatedness as basic psychological needs.", "reference", "knowledge", False,
     [("Self-Determination Theory", "theory"), ("Edward Deci", "person"), ("Richard Ryan", "person"), ("1985", "date"), ("autonomy", "concept"), ("competence", "concept"), ("relatedness", "concept")],
     [("Self-Determination Theory", "Edward Deci", "AUTHORED_BY"), ("Self-Determination Theory", "Richard Ryan", "AUTHORED_BY")],
     "whose 1985 theory organises motivation around autonomy, competence, and relatedness",
     "Deci Ryan Self Determination autonomy competence relatedness year"),
    # --- 40 ---
    ("The PISA 2018 results, reporting on 79 participating economies, showed stagnant OECD-wide reading performance despite substantial expenditure increases since 2003.", "fact", "knowledge", False,
     [("PISA 2018", "event"), ("OECD", "organization"), ("reading performance", "finding"), ("2003", "date")],
     [],
     "what did the pre-pandemic international literacy cycle show about flat scores versus rising school budgets",
     "PISA 2018 Volume I Schleicher benchmarking Finland Singapore trajectory"),
    # --- 41 ---
    ("Ann Brown and Joseph Campione's reciprocal teaching, developed in the 1980s, scaffolds reading comprehension through predicting, questioning, clarifying, and summarising.", "reference", "knowledge", False,
     [("Ann Brown", "person"), ("Joseph Campione", "person"), ("reciprocal teaching", "method"), ("1980s", "date"), ("reading comprehension", "concept")],
     [("reciprocal teaching", "Ann Brown", "AUTHORED_BY"), ("reciprocal teaching", "Joseph Campione", "AUTHORED_BY")],
     "which Michigan pair built a four-strategy scaffold for text understanding during the Reagan years",
     "Brown Campione predict-question-clarify-summarise comprehension dialogue"),
    # --- 42 ---
    ("Problem-based learning, launched at McMaster University's medical programme in 1969, replaces front-loaded lectures with ill-structured clinical cases as the curricular unit.", "milestone", "knowledge", False,
     [("Problem-based learning", "method"), ("McMaster University", "organization"), ("1969", "date"), ("front-loaded lectures", "method"), ("clinical cases", "concept")],
     [("Problem-based learning", "McMaster University", "AUTHORED_BY"), ("Problem-based learning", "front-loaded lectures", "REPLACES")],
     "which Canadian medical school traded upfront didactics for case-driven inquiry at the end of the sixties",
     "McMaster Barrows PBL tutorial group Hamilton pilot founder"),
    # --- 43 ---
    ("Seymour Papert's Mindstorms, published in 1980, articulates constructionism as building knowledge through making shareable artefacts and grounded the Logo programming tradition.", "reference", "knowledge", False,
     [("Seymour Papert", "person"), ("Mindstorms", "publication"), ("1980", "date"), ("constructionism", "theory"), ("Logo", "concept")],
     [("Mindstorms", "Seymour Papert", "AUTHORED_BY"), ("constructionism", "Seymour Papert", "AUTHORED_BY")],
     "which 1980 Papert book articulated constructionism and grounded the Logo tradition",
     "Papert Mindstorms constructionism Logo artefacts year"),
    # --- 44 ---
    ("Lee Cronbach's 1957 American Psychologist address called for aptitude-treatment interaction research that matches instructional treatments to learner profiles.", "reference", "knowledge", False,
     [("Lee Cronbach", "person"), ("1957", "date"), ("American Psychologist", "publication"), ("aptitude-treatment interaction", "concept"), ("learner profiles", "concept")],
     [("aptitude-treatment interaction", "Lee Cronbach", "AUTHORED_BY")],
     "which 1957 Cronbach address launched aptitude-treatment interaction research",
     "Cronbach aptitude treatment interaction American Psychologist address year"),
    # --- 45 ---
    ("The Coleman Report, published in 1966 as Equality of Educational Opportunity, argued that family background outweighs school resources in explaining US achievement gaps.", "reference", "knowledge", False,
     [("Coleman Report", "publication"), ("1966", "date"), ("Equality of Educational Opportunity", "publication"), ("family background", "concept"), ("school resources", "concept")],
     [],
     "which Civil Rights era federal survey concluded that home origins explain more of the test-score gap than district funding",
     "Coleman EEO 1966 household SES sociologist ESEA desegregation data"),
    # --- 46 ---
    ("John Biggs's constructive alignment, introduced in a 1996 Higher Education article, builds curriculum design on matching intended outcomes, learning activities, and assessment tasks.", "reference", "knowledge", False,
     [("John Biggs", "person"), ("constructive alignment", "framework"), ("1996", "date"), ("Higher Education", "publication"), ("assessment tasks", "concept")],
     [("constructive alignment", "John Biggs", "AUTHORED_BY")],
     "whose 1996 Higher Education article introduced constructive alignment as a curriculum design principle",
     "Biggs constructive alignment outcomes activities assessment Higher Education"),
    # --- 47 ---
    ("Etienne Wenger's Communities of Practice, published in 1998, deepens the situated-learning framework by detailing mutual engagement, joint enterprise, and shared repertoire as structural dimensions.", "reference", "knowledge", False,
     [("Etienne Wenger", "person"), ("Communities of Practice", "publication"), ("1998", "date"), ("situated-learning framework", "framework"), ("mutual engagement", "concept"), ("shared repertoire", "concept")],
     [("Communities of Practice", "Etienne Wenger", "AUTHORED_BY"), ("Communities of Practice", "situated-learning framework", "BUILDS_ON")],
     "which 1998 Wenger book detailed mutual engagement, joint enterprise, and shared repertoire",
     "Wenger Communities Practice mutual engagement joint enterprise repertoire year"),
    # --- 48. noise ---
    ("Remind me to pull the appendix table from that handbook chapter before the meeting tomorrow.", "fact", "noise", True, [], [], None, None),
    # --- 49 ---
    ("The Every Student Succeeds Act, signed in 2015, replaced the No Child Left Behind accountability regime with wider state discretion over standards and testing consequences.", "milestone", "knowledge", False,
     [("Every Student Succeeds Act", "publication"), ("2015", "date"), ("No Child Left Behind", "publication"), ("state discretion", "concept")],
     [("Every Student Succeeds Act", "No Child Left Behind", "REPLACES")],
     "which 2015 US law replaced No Child Left Behind with wider state discretion",
     "ESSA Every Student Succeeds No Child Left Behind state discretion year"),
    # --- 50 ---
    ("Gloria Ladson-Billings's The Dreamkeepers, published in 1994, developed culturally relevant pedagogy as a framework for academic success alongside cultural competence and critical consciousness.", "reference", "knowledge", False,
     [("Gloria Ladson-Billings", "person"), ("The Dreamkeepers", "publication"), ("1994", "date"), ("culturally relevant pedagogy", "framework"), ("critical consciousness", "concept")],
     [("The Dreamkeepers", "Gloria Ladson-Billings", "AUTHORED_BY"), ("culturally relevant pedagogy", "Gloria Ladson-Billings", "AUTHORED_BY")],
     "which 1994 Ladson-Billings book developed culturally relevant pedagogy as a framework",
     "Ladson Billings Dreamkeepers culturally relevant pedagogy critical consciousness year"),
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
