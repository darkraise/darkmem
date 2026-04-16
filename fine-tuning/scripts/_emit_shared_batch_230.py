"""One-off emitter for shared-base batch-230 — knowledge domain (cognitive science: Simon bounded rationality, Newell SOAR/GOMS, Anderson ACT-R, Marr's levels, Fodor LoT, Dennett, Chomsky UG, Pinker, embodied cognition, Bayesian cognition, connectionism, predictive processing, GWT, IIT, HOT, attention schema, dual-systems, enactivism).

Writes 50 rows to data/v2/shared/batch_230.tmp.jsonl with ids shared-11451..11500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_230.tmp.jsonl"
ID_OFFSET = 11450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Adopted Herbert Simon's bounded rationality as the seminar's decision-making frame; satisficing under cognitive and information constraints replaces the classical utility-maximiser idealisation in every case study.", "decision", "knowledge", False,
     [("Herbert Simon", "person"), ("bounded rationality", "theory"), ("satisficing", "concept"), ("utility-maximiser", "theory")],
     [("bounded rationality", "Herbert Simon", "AUTHORED_BY"), ("bounded rationality", "utility-maximiser", "REPLACES"), ("satisficing", "bounded rationality", "DEPENDS_ON")],
     "which framing replaced classical utility-maximisation in the seminar and who proposed it",
     "simon bounded rationality satisficing utility maximiser decision frame"),
    # --- 2 ---
    ("Allen Newell's Unified Theories of Cognition landed in 1990 and argued that a single cognitive architecture should reproduce the full range of intelligent behaviour rather than a single paradigm task.", "milestone", "knowledge", False,
     [("Allen Newell", "person"), ("Unified Theories of Cognition", "publication"), ("cognitive architecture", "concept")],
     [("Unified Theories of Cognition", "Allen Newell", "AUTHORED_BY"), ("Unified Theories of Cognition", "cognitive architecture", "APPLIES_TO")],
     "which 1990 monograph argued a single architecture should explain the full span of cognition",
     "newell unified theories cognition 1990 architecture paradigm"),
    # --- 3 ---
    ("SOAR, designed by Newell, Laird, and Rosenbloom, treats problem-solving as search in problem spaces with chunking as the sole learning mechanism; production rules fire against a working memory each decision cycle.", "architecture", "knowledge", False,
     [("SOAR", "theory"), ("Newell", "person"), ("chunking", "concept"), ("problem spaces", "concept"), ("production rules", "concept")],
     [("SOAR", "Newell", "AUTHORED_BY"), ("SOAR", "problem spaces", "DEPENDS_ON"), ("chunking", "SOAR", "APPLIES_TO")],
     "how does the SOAR architecture organise problem-solving and which single mechanism handles learning",
     "soar newell laird rosenbloom chunking problem space production rule"),
    # --- 4 ---
    ("GOMS, the Goals-Operators-Methods-Selection-rules model from Card, Moran, and Newell, gives an engineering-grade estimator for expert task time in human-computer interaction without running a user study.", "reference", "knowledge", False,
     [("GOMS", "method"), ("Card", "person"), ("Moran", "person"), ("Newell", "person"), ("human-computer interaction", "field")],
     [("GOMS", "Card", "AUTHORED_BY"), ("GOMS", "human-computer interaction", "APPLIES_TO")],
     "which HCI estimator predicts expert task time without running a user study and who devised it",
     "goms card moran newell goal operator method selection hci"),
    # --- 5 ---
    ("John Anderson's ACT-R integrates a symbolic production system with subsymbolic activation dynamics; declarative chunks decay and reactivate probabilistically, so the architecture fits neural timing data and rule-based behaviour in one model.", "architecture", "knowledge", False,
     [("John Anderson", "person"), ("ACT-R", "theory"), ("production system", "concept"), ("subsymbolic activation", "concept"), ("declarative chunks", "concept")],
     [("ACT-R", "John Anderson", "AUTHORED_BY"), ("ACT-R", "production system", "DEPENDS_ON"), ("declarative chunks", "subsymbolic activation", "DEPENDS_ON")],
     "how does ACT-R combine symbolic rules with subsymbolic dynamics and whose framework is it",
     "act-r anderson production chunk activation subsymbolic decay"),
    # --- 6 ---
    ("David Marr's Vision, published posthumously in 1982, recast visual perception as an information-processing problem solved through a sequence of representations from primal sketch to 3D model.", "milestone", "knowledge", False,
     [("David Marr", "person"), ("Vision", "publication"), ("primal sketch", "concept"), ("3D model", "concept")],
     [("Vision", "David Marr", "AUTHORED_BY"), ("primal sketch", "3D model", "DEPENDS_ON")],
     "which 1982 posthumous book framed perception as an information-processing pipeline of representations",
     "marr vision 1982 primal sketch 3d model representation pipeline"),
    # --- 7 ---
    ("Marr's three levels of analysis separate the computational, algorithmic, and implementational; the seminar insists every theory specify which level it lives at before arguing about its empirical adequacy.", "decision", "knowledge", False,
     [("Marr", "person"), ("three levels of analysis", "theory"), ("computational", "concept"), ("algorithmic", "concept"), ("implementational", "concept")],
     [("three levels of analysis", "Marr", "AUTHORED_BY")],
     "which tri-level scheme does the seminar require every theory to locate itself in",
     "marr three levels computational algorithmic implementation analysis"),
    # --- 8 ---
    ("Jerry Fodor's The Language of Thought argued that cognition operates over a combinatorial mental code called Mentalese; productivity and systematicity of thought are the core arguments, recycled later against connectionism.", "reference", "knowledge", False,
     [("Jerry Fodor", "person"), ("The Language of Thought", "publication"), ("Mentalese", "concept"), ("systematicity", "concept"), ("connectionism", "theory")],
     [("The Language of Thought", "Jerry Fodor", "AUTHORED_BY"), ("The Language of Thought", "connectionism", "CONTRADICTS"), ("Mentalese", "systematicity", "DEPENDS_ON")],
     "which Fodor monograph posited a combinatorial mental code and what arguments support it",
     "fodor language thought mentalese productivity systematicity combinatorial"),
    # --- 9 ---
    ("Fodor's Modularity of Mind hypothesises domain-specific, informationally encapsulated input systems separate from a holistic central cognition; the face-processing module is the canonical example in the perception chapter.", "fact", "knowledge", False,
     [("Fodor", "person"), ("Modularity of Mind", "publication"), ("informationally encapsulated", "concept"), ("input systems", "concept"), ("central cognition", "concept")],
     [("Modularity of Mind", "Fodor", "AUTHORED_BY"), ("input systems", "central cognition", "CONTRADICTS")],
     "which Fodor book partitions mind into encapsulated input modules and a holistic central system",
     "fodor modularity mind informationally encapsulated input central"),
    # --- 10. noise ---
    ("The faculty lounge's kettle lost its whistle gasket on Tuesday and a handwritten sign now demands anyone brewing tea use the spare in the mug cupboard.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Daniel Dennett's intentional stance treats ascribing beliefs and desires as a predictive strategy that works whenever the target behaves rationally; the stance is orthogonal to whether any literal inner representation exists.", "decision", "knowledge", False,
     [("Daniel Dennett", "person"), ("intentional stance", "theory"), ("beliefs", "concept"), ("predictive strategy", "concept")],
     [("intentional stance", "Daniel Dennett", "AUTHORED_BY"), ("intentional stance", "predictive strategy", "DEPENDS_ON")],
     "which Dennett framework treats belief-desire ascription as a predictive strategy rather than literal description",
     "dennett intentional stance belief desire predictive rational strategy"),
    # --- 12 ---
    ("Consciousness Explained by Dennett, 1991, develops the Multiple Drafts model against the Cartesian Theatre; there is no single place in the brain where conscious content becomes definite.", "milestone", "knowledge", False,
     [("Consciousness Explained", "publication"), ("Dennett", "person"), ("Multiple Drafts", "theory"), ("Cartesian Theatre", "theory")],
     [("Consciousness Explained", "Dennett", "AUTHORED_BY"), ("Multiple Drafts", "Cartesian Theatre", "CONTRADICTS")],
     "which Dennett book proposed Multiple Drafts against the Cartesian Theatre picture of consciousness",
     "dennett consciousness explained multiple drafts cartesian theatre 1991"),
    # --- 13 ---
    ("Noam Chomsky's universal grammar posits an innate language faculty whose principles underlie every natural language; cross-linguistic parameter setting accounts for observed variation.", "architecture", "knowledge", False,
     [("Noam Chomsky", "person"), ("universal grammar", "theory"), ("language faculty", "concept"), ("parameter setting", "concept")],
     [("universal grammar", "Noam Chomsky", "AUTHORED_BY"), ("universal grammar", "language faculty", "DEPENDS_ON"), ("parameter setting", "universal grammar", "APPLIES_TO")],
     "whose theory posits an innate grammar whose parameters fix cross-linguistic variation",
     "chomsky universal grammar innate language faculty parameter setting"),
    # --- 14 ---
    ("The poverty-of-stimulus argument claims children acquire grammatical competence their input underdetermines, so some linguistic structure must be innately specified; the auxiliary-inversion case is the textbook illustration.", "fact", "knowledge", False,
     [("poverty-of-stimulus", "theory"), ("grammatical competence", "concept"), ("auxiliary-inversion", "finding")],
     [("poverty-of-stimulus", "grammatical competence", "APPLIES_TO")],
     "which argument infers innate linguistic structure from the gap between input and acquired competence",
     "poverty stimulus grammatical competence auxiliary inversion innate"),
    # --- 15 ---
    ("Steven Pinker's The Language Instinct, 1994, popularised the nativist case by framing language as a biologically-evolved instinct; the book packages Chomskyan arguments for a general audience.", "reference", "knowledge", False,
     [("Steven Pinker", "person"), ("The Language Instinct", "publication"), ("nativist", "claim"), ("Chomskyan", "theory")],
     [("The Language Instinct", "Steven Pinker", "AUTHORED_BY"), ("The Language Instinct", "Chomskyan", "BUILDS_ON")],
     "which 1994 Pinker book packaged the nativist case about language for a general audience",
     "pinker language instinct 1994 nativist chomsky popular evolved"),
    # --- 16 ---
    ("Pinker's How the Mind Works extends an evolutionary-psychology reading of cognition across vision, language, and emotion; the seminar uses its mental-imagery chapter as a counterweight to pure connectionist accounts.", "fact", "knowledge", False,
     [("Pinker", "person"), ("How the Mind Works", "publication"), ("evolutionary-psychology", "field"), ("mental-imagery", "concept"), ("connectionist", "theory")],
     [("How the Mind Works", "Pinker", "AUTHORED_BY"), ("How the Mind Works", "connectionist", "CONTRADICTS")],
     "which Pinker book pushes an evolutionary-psychology reading across vision, language, and emotion",
     "pinker how mind works evolutionary psychology imagery connectionist"),
    # --- 17 ---
    ("George Lakoff and Mark Johnson's Metaphors We Live By argues everyday cognition is structured by conceptual metaphor grounded in sensorimotor experience; the container and journey metaphors recur throughout.", "milestone", "knowledge", False,
     [("George Lakoff", "person"), ("Mark Johnson", "person"), ("Metaphors We Live By", "publication"), ("conceptual metaphor", "theory"), ("sensorimotor", "concept")],
     [("Metaphors We Live By", "George Lakoff", "AUTHORED_BY"), ("Metaphors We Live By", "Mark Johnson", "AUTHORED_BY"), ("conceptual metaphor", "sensorimotor", "DEPENDS_ON")],
     "which Lakoff and Johnson book grounds cognition in sensorimotor-rooted conceptual metaphor",
     "lakoff johnson metaphors we live by conceptual sensorimotor container"),
    # --- 18 ---
    ("Andy Clark's extended mind thesis, co-written with David Chalmers, argues that notebooks and tools can constitute part of a cognitive system when they are reliably coupled to the agent's reasoning.", "fact", "knowledge", False,
     [("Andy Clark", "person"), ("David Chalmers", "person"), ("extended mind", "theory"), ("cognitive system", "concept")],
     [("extended mind", "Andy Clark", "AUTHORED_BY"), ("extended mind", "David Chalmers", "AUTHORED_BY")],
     "whose thesis treats reliably-coupled external tools as parts of a cognitive system",
     "clark chalmers extended mind notebook tool cognitive coupling"),
    # --- 19 ---
    ("The seminar's embodied cognition stance rejects the view that thinking is abstract symbol manipulation and locates meaning in bodily and environmental interaction; it interrogates purely computational accounts throughout.", "decision", "knowledge", False,
     [("embodied cognition", "theory"), ("symbol manipulation", "concept"), ("bodily and environmental interaction", "concept")],
     [("embodied cognition", "symbol manipulation", "CONTRADICTS"), ("embodied cognition", "bodily and environmental interaction", "DEPENDS_ON")],
     "which theoretical stance rejects abstract symbol manipulation in favour of bodily-environmental coupling",
     "embodied cognition symbol manipulation body environment interaction"),
    # --- 20 ---
    ("Joshua Tenenbaum's lab frames cognition as approximate Bayesian inference over structured generative models; the number-game experiment is the seminar's introduction to hierarchical priors in concept learning.", "decision", "knowledge", False,
     [("Joshua Tenenbaum", "person"), ("Bayesian inference", "method"), ("generative models", "concept"), ("number-game", "finding"), ("hierarchical priors", "concept")],
     [("Bayesian inference", "Joshua Tenenbaum", "AUTHORED_BY"), ("Bayesian inference", "generative models", "DEPENDS_ON"), ("number-game", "hierarchical priors", "APPLIES_TO")],
     "whose lab frames cognition as Bayesian inference over generative models and which experiment anchors it",
     "tenenbaum bayesian generative number game hierarchical prior concept"),
    # --- 21 ---
    ("Thomas Griffiths and colleagues showed that rational analyses of memory, categorisation, and causal learning converge on Bayesian posteriors under reasonable priors; the tutorial chapter is assigned in week six.", "fact", "knowledge", False,
     [("Thomas Griffiths", "person"), ("rational analyses", "method"), ("Bayesian posteriors", "concept"), ("causal learning", "field")],
     [("rational analyses", "Thomas Griffiths", "AUTHORED_BY"), ("rational analyses", "Bayesian posteriors", "DEPENDS_ON")],
     "whose rational analyses show memory, categorisation, and causal learning reduce to Bayesian posteriors",
     "griffiths rational analysis memory categorisation causal bayesian"),
    # --- 22 ---
    ("Noah Goodman's probabilistic programming framework treats concepts as stochastic generative programs; the Church language and its successor WebPPL make the inferences first-class objects students can run in a browser.", "architecture", "knowledge", False,
     [("Noah Goodman", "person"), ("probabilistic programming", "method"), ("Church", "tool"), ("WebPPL", "tool"), ("stochastic generative programs", "concept")],
     [("probabilistic programming", "Noah Goodman", "AUTHORED_BY"), ("WebPPL", "Church", "REPLACES"), ("Church", "stochastic generative programs", "APPLIES_TO")],
     "whose probabilistic-programming stack treats concepts as generative programs and which languages implement it",
     "goodman probabilistic programming church webppl stochastic generative"),
    # --- 23 ---
    ("The Rumelhart-McClelland PDP volumes of 1986 launched connectionism as a cognitive paradigm; distributed representations and backprop-trained multilayer networks replaced the pure symbolic account in perception modules.", "milestone", "knowledge", False,
     [("Rumelhart", "person"), ("McClelland", "person"), ("PDP", "publication"), ("connectionism", "theory"), ("distributed representations", "concept"), ("symbolic account", "theory")],
     [("PDP", "Rumelhart", "AUTHORED_BY"), ("PDP", "McClelland", "AUTHORED_BY"), ("connectionism", "symbolic account", "REPLACES"), ("connectionism", "distributed representations", "DEPENDS_ON")],
     "which 1986 two-volume set launched connectionism and displaced pure symbolic accounts in perception",
     "rumelhart mcclelland pdp 1986 connectionism distributed backprop symbol"),
    # --- 24 ---
    ("The past-tense learning model by Rumelhart and McClelland showed a single network producing regular and irregular inflections without explicit rules; Pinker and Prince's rebuttal became the canonical Words-and-Rules counter.", "decision", "knowledge", False,
     [("past-tense learning model", "finding"), ("Rumelhart", "person"), ("McClelland", "person"), ("Pinker and Prince", "claim"), ("Words-and-Rules", "theory")],
     [("past-tense learning model", "Rumelhart", "AUTHORED_BY"), ("Words-and-Rules", "past-tense learning model", "CONTRADICTS")],
     "which connectionist model drew a rule-free account of past tense and which symbolic rebuttal countered it",
     "past tense rumelhart mcclelland pinker prince words rules connectionist"),
    # --- 25 ---
    ("Karl Friston's free energy principle claims self-organising systems minimise variational free energy, which is equivalent to minimising prediction error in a generative model of their world.", "architecture", "knowledge", False,
     [("Karl Friston", "person"), ("free energy principle", "theory"), ("variational free energy", "concept"), ("prediction error", "concept"), ("generative model", "concept")],
     [("free energy principle", "Karl Friston", "AUTHORED_BY"), ("free energy principle", "variational free energy", "DEPENDS_ON"), ("prediction error", "generative model", "DEPENDS_ON")],
     "which Friston principle ties self-organisation to variational free-energy minimisation and prediction error",
     "friston free energy variational prediction error generative self organise"),
    # --- 26 ---
    ("The unit on predictive processing reframes perception, attention, and action as hierarchical Bayesian inference where top-down predictions meet bottom-up sensory prediction errors; Andy Clark's Surfing Uncertainty is the assigned primer.", "decision", "knowledge", False,
     [("predictive processing", "theory"), ("hierarchical Bayesian inference", "method"), ("prediction errors", "concept"), ("Andy Clark", "person"), ("Surfing Uncertainty", "publication")],
     [("predictive processing", "hierarchical Bayesian inference", "DEPENDS_ON"), ("Surfing Uncertainty", "Andy Clark", "AUTHORED_BY"), ("Surfing Uncertainty", "predictive processing", "APPLIES_TO")],
     "which framework casts perception and action as hierarchical Bayesian inference and which Clark book primers it",
     "predictive processing hierarchical bayesian prediction error clark surfing"),
    # --- 27 ---
    ("Bernard Baars' Global Workspace Theory posits a capacity-limited broadcast system that makes selected contents globally available to otherwise modular consumers; consciousness corresponds to workspace access.", "architecture", "knowledge", False,
     [("Bernard Baars", "person"), ("Global Workspace Theory", "theory"), ("broadcast system", "concept"), ("modular consumers", "concept")],
     [("Global Workspace Theory", "Bernard Baars", "AUTHORED_BY"), ("Global Workspace Theory", "broadcast system", "DEPENDS_ON")],
     "which Baars theory models consciousness as capacity-limited broadcast to otherwise modular consumers",
     "baars global workspace broadcast modular consciousness capacity"),
    # --- 28 ---
    ("Stanislas Dehaene's neuronal workspace extends Baars into a neurally-realised account: long-range pyramidal neurons in parietal and prefrontal cortex ignite when a stimulus crosses the access threshold.", "fact", "knowledge", False,
     [("Stanislas Dehaene", "person"), ("neuronal workspace", "theory"), ("Baars", "person"), ("long-range pyramidal neurons", "concept")],
     [("neuronal workspace", "Stanislas Dehaene", "AUTHORED_BY"), ("neuronal workspace", "Baars", "BUILDS_ON")],
     "whose neuronal workspace extends Baars into a neurally-grounded ignition account",
     "dehaene neuronal workspace baars ignition prefrontal parietal pyramidal"),
    # --- 29 ---
    ("Giulio Tononi's Integrated Information Theory formalises consciousness as phi, the integrated information generated by a system above and beyond its parts; the axiomatic derivation is the week-eleven reading.", "architecture", "knowledge", False,
     [("Giulio Tononi", "person"), ("Integrated Information Theory", "theory"), ("phi", "concept"), ("integrated information", "concept")],
     [("Integrated Information Theory", "Giulio Tononi", "AUTHORED_BY"), ("phi", "integrated information", "DEPENDS_ON")],
     "whose theory quantifies consciousness as phi, the information integrated above and beyond parts",
     "tononi iit integrated information phi axiomatic consciousness"),
    # --- 30 ---
    ("IIT and Global Workspace Theory give incompatible verdicts on split-brain and cerebellum cases; the seminar tables these as the primary empirical arbiters between broadcast and integration accounts.", "problem", "knowledge", False,
     [("IIT", "theory"), ("Global Workspace Theory", "theory"), ("split-brain", "finding"), ("cerebellum", "concept")],
     [("IIT", "Global Workspace Theory", "CONTRADICTS"), ("split-brain", "IIT", "APPLIES_TO")],
     "which empirical cases pit IIT against Global Workspace Theory as arbiters of consciousness theories",
     "iit global workspace split brain cerebellum arbiter consciousness"),
    # --- 31 ---
    ("David Rosenthal's Higher-Order Thought theory requires a mental state to be the object of a thought about it to count as conscious; first-order representation alone is not sufficient.", "decision", "knowledge", False,
     [("David Rosenthal", "person"), ("Higher-Order Thought", "theory"), ("first-order representation", "concept")],
     [("Higher-Order Thought", "David Rosenthal", "AUTHORED_BY"), ("Higher-Order Thought", "first-order representation", "CONTRADICTS")],
     "which Rosenthal theory demands a second-order thought for a state to be conscious",
     "rosenthal higher order thought first order representation conscious"),
    # --- 32 ---
    ("The mismatch-case objection to HOT concerns hallucinated higher-order thoughts without a matching first-order state; proponents bite the bullet and call the mismatch itself sufficient for phenomenal character.", "problem", "knowledge", False,
     [("HOT", "theory"), ("mismatch-case", "claim"), ("first-order state", "concept"), ("phenomenal character", "concept")],
     [("mismatch-case", "HOT", "CONTRADICTS"), ("mismatch-case", "first-order state", "APPLIES_TO")],
     "which objection to HOT exploits cases of higher-order thoughts without matching first-order states",
     "hot mismatch case first order phenomenal bite bullet objection"),
    # --- 33 ---
    ("Michael Graziano's attention schema theory treats subjective awareness as the brain's simplified internal model of its own attention; the model's accuracy is less important than its utility for social prediction.", "decision", "knowledge", False,
     [("Michael Graziano", "person"), ("attention schema theory", "theory"), ("attention", "concept"), ("social prediction", "field")],
     [("attention schema theory", "Michael Graziano", "AUTHORED_BY"), ("attention schema theory", "attention", "APPLIES_TO")],
     "whose theory models awareness as the brain's internal model of its own attention",
     "graziano attention schema model awareness social prediction"),
    # --- 34 ---
    ("Daniel Kahneman's dual-systems account distinguishes fast intuitive System 1 from slow deliberate System 2; the cognitive-reflection test is the seminar's introductory diagnostic for switching between them.", "reference", "knowledge", False,
     [("Daniel Kahneman", "person"), ("dual-systems", "theory"), ("System 1", "concept"), ("System 2", "concept"), ("cognitive-reflection test", "method")],
     [("dual-systems", "Daniel Kahneman", "AUTHORED_BY"), ("cognitive-reflection test", "dual-systems", "APPLIES_TO")],
     "whose dual-systems account contrasts fast System 1 with slow System 2 and which test diagnoses switching",
     "kahneman dual systems system 1 system 2 cognitive reflection test"),
    # --- 35 ---
    ("Keith Stanovich refined dual-systems by distinguishing autonomous Type 1 from reflective Type 2 within a tripartite mind that includes an algorithmic level; rationality failures emerge when the reflective mind fails to override.", "fact", "knowledge", False,
     [("Keith Stanovich", "person"), ("Type 1", "concept"), ("Type 2", "concept"), ("tripartite mind", "theory"), ("reflective mind", "concept")],
     [("tripartite mind", "Keith Stanovich", "AUTHORED_BY"), ("tripartite mind", "reflective mind", "DEPENDS_ON")],
     "whose tripartite-mind refinement of dual-systems distinguishes autonomous Type 1 from reflective Type 2",
     "stanovich tripartite mind type 1 type 2 reflective override rationality"),
    # --- 36 ---
    ("Francisco Varela, Evan Thompson, and Eleanor Rosch's The Embodied Mind, 1991, introduced enactivism: cognition is sense-making through the dynamic coupling of a living agent with its environment.", "milestone", "knowledge", False,
     [("Francisco Varela", "person"), ("Evan Thompson", "person"), ("Eleanor Rosch", "person"), ("The Embodied Mind", "publication"), ("enactivism", "theory")],
     [("The Embodied Mind", "Francisco Varela", "AUTHORED_BY"), ("The Embodied Mind", "Evan Thompson", "AUTHORED_BY"), ("enactivism", "The Embodied Mind", "DEPENDS_ON")],
     "which 1991 Varela Thompson Rosch book introduced enactivism as sense-making through agent-environment coupling",
     "varela thompson rosch embodied mind 1991 enactivism sense making"),
    # --- 37 ---
    ("Evan Thompson's Mind in Life extends enactivism with an autopoiesis-based biology of cognition; the seminar pairs its chapter three with Maturana and Varela for the life-mind continuity thesis.", "reference", "knowledge", False,
     [("Evan Thompson", "person"), ("Mind in Life", "publication"), ("enactivism", "theory"), ("autopoiesis", "concept"), ("Maturana", "person"), ("life-mind continuity", "claim")],
     [("Mind in Life", "Evan Thompson", "AUTHORED_BY"), ("Mind in Life", "enactivism", "BUILDS_ON"), ("life-mind continuity", "autopoiesis", "DEPENDS_ON")],
     "which Thompson book extends enactivism into autopoietic biology and underpins life-mind continuity",
     "thompson mind life enactivism autopoiesis maturana life mind continuity"),
    # --- 38 ---
    ("The 4E cognition umbrella bundles embodied, embedded, extended, and enactive approaches; the seminar uses 4E as a label for positions that share a rejection of purely internalist computational cognition.", "architecture", "knowledge", False,
     [("4E cognition", "theory"), ("embodied", "concept"), ("embedded", "concept"), ("extended", "concept"), ("enactive", "concept"), ("internalist computational cognition", "theory")],
     [("4E cognition", "internalist computational cognition", "CONTRADICTS")],
     "which umbrella term covers embodied, embedded, extended, and enactive cognition against internalist computational views",
     "4e cognition embodied embedded extended enactive internalist"),
    # --- 39 ---
    ("Preferred The Language Instinct over How the Mind Works for the intro reading; students land on the nativist argument faster without the evolutionary-psychology scaffolding first.", "preference", "knowledge", False,
     [("The Language Instinct", "publication"), ("How the Mind Works", "publication"), ("nativist", "claim"), ("evolutionary-psychology", "field")],
     [("The Language Instinct", "How the Mind Works", "PREFERS")],
     "which Pinker title does the seminar open with and why over its companion volume",
     "pinker language instinct how mind works nativist evolutionary intro"),
    # --- 40 ---
    ("Preferred ACT-R over SOAR for the modelling-lab track; its subsymbolic activation layer fits reaction-time data tighter without a second-pass calibration.", "preference", "knowledge", False,
     [("ACT-R", "theory"), ("SOAR", "theory"), ("subsymbolic activation", "concept"), ("reaction-time", "finding")],
     [("ACT-R", "SOAR", "PREFERS"), ("subsymbolic activation", "reaction-time", "APPLIES_TO")],
     "which architecture does the modelling-lab track prefer over SOAR and on which empirical grounds",
     "act-r soar subsymbolic reaction time modelling lab preference"),
    # --- 41 ---
    ("Preferred Marr's tri-level frame over Chomsky's competence-performance split for the analytic scaffolding; it generalises outside linguistics without forcing a competence idealisation first.", "preference", "knowledge", False,
     [("Marr", "person"), ("tri-level frame", "theory"), ("Chomsky", "person"), ("competence-performance", "theory")],
     [("tri-level frame", "competence-performance", "PREFERS")],
     "which analytic scaffolding does the seminar prefer to the competence-performance split and why",
     "marr tri level chomsky competence performance scaffolding"),
    # --- 42 ---
    ("The binding problem asks how distributed feature detectors yield unified percepts; temporal-synchrony, attention-based, and predictive-coding solutions remain unresolved across the cognitive-neuroscience literature.", "problem", "knowledge", False,
     [("binding problem", "theory"), ("temporal-synchrony", "method"), ("attention-based", "method"), ("predictive-coding", "theory"), ("cognitive-neuroscience", "field")],
     [("binding problem", "cognitive-neuroscience", "APPLIES_TO"), ("temporal-synchrony", "binding problem", "APPLIES_TO")],
     "which unresolved puzzle asks how distributed features cohere into unified percepts across neuroscience",
     "binding problem temporal synchrony attention predictive coding feature"),
    # --- 43. noise ---
    ("Somebody left a half-finished crossword on the reading-room table and a pencilled note claiming 14-down is probably wrong.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Preferred predictive processing over classical sensorimotor accounts for the action chapter; the top-down prediction machinery handles motor control and perception with one inference scheme.", "preference", "knowledge", False,
     [("predictive processing", "theory"), ("sensorimotor accounts", "theory"), ("motor control", "field"), ("inference scheme", "concept")],
     [("predictive processing", "sensorimotor accounts", "PREFERS"), ("predictive processing", "motor control", "APPLIES_TO")],
     "which framework does the action chapter prefer over sensorimotor accounts for unifying motor and perception",
     "predictive processing sensorimotor motor control inference unified"),
    # --- 45 ---
    ("Jerry Fodor and Zenon Pylyshyn's 1988 critique of connectionism argued that distributed networks lack the systematicity and productivity a theory of thought needs; Smolensky's tensor-product binding is the assigned reply.", "decision", "knowledge", False,
     [("Jerry Fodor", "person"), ("Zenon Pylyshyn", "person"), ("1988 critique of connectionism", "publication"), ("Smolensky", "person"), ("tensor-product binding", "method"), ("systematicity", "concept")],
     [("1988 critique of connectionism", "Jerry Fodor", "AUTHORED_BY"), ("1988 critique of connectionism", "Zenon Pylyshyn", "AUTHORED_BY"), ("tensor-product binding", "Smolensky", "AUTHORED_BY"), ("tensor-product binding", "1988 critique of connectionism", "CONTRADICTS")],
     "which 1988 paper attacked connectionism on systematicity grounds and which reply gets assigned against it",
     "fodor pylyshyn 1988 connectionism systematicity smolensky tensor"),
    # --- 46 ---
    ("The Chinese Room argument by John Searle contends that syntactic symbol manipulation alone cannot constitute understanding; Dennett's systems reply and Churchland's luminous-room parody are paired readings.", "reference", "knowledge", False,
     [("Chinese Room", "theory"), ("John Searle", "person"), ("Dennett", "person"), ("Churchland", "person"), ("systems reply", "claim"), ("luminous-room parody", "claim")],
     [("Chinese Room", "John Searle", "AUTHORED_BY"), ("systems reply", "Dennett", "AUTHORED_BY"), ("systems reply", "Chinese Room", "CONTRADICTS"), ("luminous-room parody", "Churchland", "AUTHORED_BY")],
     "which Searle argument denies syntactic symbol manipulation yields understanding and which replies are paired",
     "searle chinese room syntax understanding dennett churchland luminous"),
    # --- 47 ---
    ("The hard problem of consciousness, framed by David Chalmers in 1995, separates the easy problems of cognitive function from why experience accompanies any of it; it anchors the terminology for the final unit.", "milestone", "knowledge", False,
     [("hard problem of consciousness", "theory"), ("David Chalmers", "person"), ("easy problems", "concept"), ("experience", "concept")],
     [("hard problem of consciousness", "David Chalmers", "AUTHORED_BY"), ("hard problem of consciousness", "easy problems", "CONTRADICTS")],
     "which Chalmers distinction separates the easy problems of cognition from the hard problem of experience",
     "chalmers hard problem consciousness 1995 easy experience"),
    # --- 48 ---
    ("Endel Tulving's episodic-semantic distinction and Baddeley and Hitch's working-memory model anchor the memory unit; the central executive coordinates the phonological loop and visuospatial sketchpad in the 1974 framing.", "architecture", "knowledge", False,
     [("Endel Tulving", "person"), ("episodic-semantic distinction", "theory"), ("Baddeley and Hitch", "person"), ("working-memory model", "theory"), ("central executive", "concept"), ("phonological loop", "concept"), ("visuospatial sketchpad", "concept")],
     [("episodic-semantic distinction", "Endel Tulving", "AUTHORED_BY"), ("working-memory model", "Baddeley and Hitch", "AUTHORED_BY"), ("working-memory model", "central executive", "DEPENDS_ON")],
     "which two frameworks anchor the memory unit and how does the 1974 working-memory model decompose",
     "tulving episodic semantic baddeley hitch working memory executive loop"),
    # --- 49 ---
    ("After the 2015 wave of failed social-priming replications, the seminar adopted a rule re-weighting cognitive-science findings by pre-registration status and effect-size stability before citing any result.", "decision", "knowledge", False,
     [("social-priming", "field"), ("cognitive-science", "field"), ("pre-registration", "method"), ("effect-size stability", "concept")],
     [("pre-registration", "social-priming", "APPLIES_TO"), ("effect-size stability", "cognitive-science", "APPLIES_TO")],
     "which policy did the seminar adopt after 2015 social-priming failures for weighing cognitive-science findings",
     "social priming pre registration 2015 effect size weight cognitive"),
    # --- 50 ---
    ("Ran into a scope clash between IIT and predictive processing in the consciousness unit: IIT scores systems in the absence of input, while predictive processing requires a generative model driven by sensory evidence.", "decision", "knowledge", False,
     [("IIT", "theory"), ("predictive processing", "theory"), ("generative model", "concept"), ("sensory evidence", "concept")],
     [("IIT", "predictive processing", "CONTRADICTS"), ("predictive processing", "generative model", "DEPENDS_ON")],
     "which scope clash pits IIT against predictive processing on whether inputs are required to score consciousness",
     "iit predictive processing scope generative sensory evidence clash"),
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
