"""One-off emitter for shared-base batch-222 — knowledge domain (philosophy of science and epistemology).

Writes 50 rows to data/v2/shared/batch_222.tmp.jsonl with ids shared-11051..11100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_222.tmp.jsonl"
ID_OFFSET = 11050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Adopted falsifiability as the demarcation criterion for the epistemology seminar syllabus; Karl Popper's The Logic of Scientific Discovery grounds the first three weeks before Kuhn enters the picture.", "decision", "knowledge", False,
     [("falsifiability", "concept"), ("Karl Popper", "person"), ("The Logic of Scientific Discovery", "publication"), ("Kuhn", "person")],
     [("The Logic of Scientific Discovery", "Karl Popper", "AUTHORED_BY"), ("falsifiability", "Karl Popper", "RELATED_TO")],
     "which demarcation criterion opens the seminar and which Popper book anchors the first weeks",
     "falsifiability popper logic scientific discovery syllabus demarcation"),
    # --- 2 architecture ---
    ("The course reading map threads Popper, Kuhn, and Lakatos into one arc: conjectures and refutations first, then paradigm shifts, then research programmes as a compromise between normal science and bold conjectures.", "architecture", "knowledge", False,
     [("Popper", "person"), ("Kuhn", "person"), ("Lakatos", "person"), ("paradigm shifts", "concept"), ("research programmes", "theory"), ("normal science", "concept")],
     [("research programmes", "Lakatos", "AUTHORED_BY"), ("paradigm shifts", "Kuhn", "AUTHORED_BY"), ("research programmes", "paradigm shifts", "BUILDS_ON")],
     "how does the reading map sequence Popper Kuhn and Lakatos into a single philosophical arc",
     "popper kuhn lakatos conjecture paradigm research programme arc"),
    # --- 3 fact ---
    ("The Structure of Scientific Revolutions introduced the paradigm shift vocabulary in 1962 and reframed normal science as puzzle-solving inside a shared disciplinary matrix rather than cumulative truth-building.", "fact", "knowledge", False,
     [("The Structure of Scientific Revolutions", "publication"), ("paradigm shift", "concept"), ("1962", "date"), ("normal science", "concept"), ("disciplinary matrix", "concept")],
     [("paradigm shift", "The Structure of Scientific Revolutions", "PUBLISHED_IN"), ("normal science", "disciplinary matrix", "LOCATED_IN")],
     "which 1962 book introduced paradigm shift and what did it call routine scientific work",
     "structure scientific revolutions kuhn paradigm shift 1962 normal science"),
    # --- 4 reference ---
    ("For the Bayesian epistemology unit the primary text is E.T. Jaynes's Probability Theory: The Logic of Science, with Cox's theorem as the formal bridge from plausibility to real-valued probability.", "reference", "knowledge", False,
     [("E.T. Jaynes", "person"), ("Probability Theory: The Logic of Science", "publication"), ("Cox's theorem", "theory"), ("Bayesian epistemology", "field"), ("plausibility", "concept")],
     [("Probability Theory: The Logic of Science", "E.T. Jaynes", "AUTHORED_BY"), ("Cox's theorem", "Bayesian epistemology", "APPLIES_TO")],
     "which Jaynes book anchors the Bayesian unit and which theorem bridges plausibility to probability",
     "jaynes probability logic science cox theorem bayesian plausibility"),
    # --- 5 decision ---
    ("Chose Lakatos's methodology of scientific research programmes over strict Popperian falsificationism for the case-study week; the hard core versus protective belt distinction handles actual history of physics more gracefully.", "decision", "knowledge", False,
     [("Lakatos", "person"), ("scientific research programmes", "theory"), ("Popperian falsificationism", "theory"), ("hard core", "concept"), ("protective belt", "concept")],
     [("scientific research programmes", "Popperian falsificationism", "IMPROVES_ON"), ("hard core", "scientific research programmes", "HAS_PART"), ("protective belt", "scientific research programmes", "HAS_PART")],
     "which methodology replaced strict falsificationism for the case-study week and why",
     "lakatos research programme hard core protective belt falsification"),
    # --- 6 architecture ---
    ("The realism debate sits on a two-axis grid: scientific realism versus anti-realism on the truth axis, and constructive empiricism versus instrumentalism on the aim axis; Van Fraassen occupies the anti-realism plus empirical adequacy corner.", "architecture", "knowledge", False,
     [("scientific realism", "theory"), ("anti-realism", "theory"), ("constructive empiricism", "theory"), ("instrumentalism", "theory"), ("Van Fraassen", "person"), ("empirical adequacy", "concept")],
     [("constructive empiricism", "Van Fraassen", "AUTHORED_BY"), ("constructive empiricism", "scientific realism", "CONTRADICTS"), ("empirical adequacy", "constructive empiricism", "HAS_PART")],
     "how is the realism debate laid out on a two-axis grid and where does Van Fraassen land",
     "scientific realism anti realism constructive empiricism van fraassen grid"),
    # --- 7 fact ---
    ("The pessimistic meta-induction argues that since most past successful theories were eventually abandoned, current successful theories are probably false too, which cuts directly against the no-miracles argument for scientific realism.", "fact", "knowledge", False,
     [("pessimistic meta-induction", "claim"), ("no-miracles argument", "claim"), ("scientific realism", "theory")],
     [("pessimistic meta-induction", "no-miracles argument", "CONTRADICTS"), ("no-miracles argument", "scientific realism", "SUPPORTS")],
     "which induction-style argument cuts against the no-miracles defence of scientific realism",
     "pessimistic meta induction no miracles argument realism abandon"),
    # --- 8 milestone ---
    ("Finished the Gettier unit: three sessions covered the 1963 three-page paper, Lehrer and Paxson's indefeasibility response, and Goldman's causal theory, ending with reliabilism as the stable modern alternative to justified true belief.", "milestone", "knowledge", False,
     [("Gettier", "person"), ("1963", "date"), ("Lehrer and Paxson", "person"), ("Goldman", "person"), ("reliabilism", "theory"), ("justified true belief", "concept"), ("causal theory", "theory")],
     [("causal theory", "Goldman", "AUTHORED_BY"), ("reliabilism", "justified true belief", "REPLACES")],
     "which unit wrapped with reliabilism supplanting justified true belief and who bridged the gap",
     "gettier lehrer paxson goldman reliabilism justified true belief causal"),
    # --- 9 decision ---
    ("Dropped Hempel's DN model from the explanation lecture in favour of pragmatic accounts; symmetry and irrelevance counterexamples from Salmon made the deductive-nomological story too fragile to teach as primary.", "decision", "knowledge", False,
     [("Hempel", "person"), ("DN model", "theory"), ("Salmon", "person"), ("pragmatic accounts", "theory"), ("deductive-nomological", "concept")],
     [("pragmatic accounts", "DN model", "REPLACES"), ("DN model", "Hempel", "AUTHORED_BY"), ("Salmon", "DN model", "CONTRADICTS")],
     "which explanation model did the lecture drop after Salmon's counterexamples and what replaced it",
     "hempel dn model deductive nomological salmon pragmatic explanation"),
    # --- 10. noise ---
    ("The seminar room radiator hissed through the first hour and the whiteboard markers kept rolling off the ledge onto the tile floor.", "fact", "noise", True, [], [], None, None),
    # --- 11 reference ---
    ("Assigned reading for the induction week: Carnap's Logical Foundations of Probability for inductive logic, paired with Goodman's Fact, Fiction, and Forecast for the grue paradox counterpunch.", "reference", "knowledge", False,
     [("Carnap", "person"), ("Logical Foundations of Probability", "publication"), ("Goodman", "person"), ("Fact, Fiction, and Forecast", "publication"), ("grue paradox", "concept"), ("inductive logic", "field")],
     [("Logical Foundations of Probability", "Carnap", "AUTHORED_BY"), ("Fact, Fiction, and Forecast", "Goodman", "AUTHORED_BY"), ("grue paradox", "Goodman", "AUTHORED_BY")],
     "which Carnap and Goodman readings pair up for the induction week and why",
     "carnap logical foundations probability goodman grue fact fiction forecast"),
    # --- 12 architecture ---
    ("The Quine-Duhem thesis anchors the underdetermination lecture: no hypothesis faces the tribunal of experience alone, so any failed prediction can be rescued by adjusting auxiliary assumptions somewhere in the web of belief.", "architecture", "knowledge", False,
     [("Quine-Duhem thesis", "theory"), ("underdetermination", "concept"), ("auxiliary assumptions", "concept"), ("web of belief", "concept")],
     [("Quine-Duhem thesis", "underdetermination", "SUPPORTS"), ("Quine-Duhem thesis", "auxiliary assumptions", "HAS_PART"), ("web of belief", "Quine-Duhem thesis", "RELATED_TO")],
     "how does the Quine-Duhem thesis frame the underdetermination lecture around auxiliary assumptions",
     "quine duhem underdetermination auxiliary web belief tribunal experience"),
    # --- 13 fact ---
    ("Quine's Two Dogmas of Empiricism dismantled the analytic-synthetic distinction and reductionism in one 1951 paper, collapsing the Carnapian program into holistic confirmation against the whole theory.", "fact", "knowledge", False,
     [("Two Dogmas of Empiricism", "publication"), ("Quine", "person"), ("analytic-synthetic distinction", "concept"), ("reductionism", "concept"), ("1951", "date"), ("holistic confirmation", "concept"), ("Carnap", "person")],
     [("Two Dogmas of Empiricism", "Quine", "AUTHORED_BY"), ("Two Dogmas of Empiricism", "analytic-synthetic distinction", "CONTRADICTS"), ("holistic confirmation", "reductionism", "REPLACES")],
     "which 1951 Quine paper killed analytic-synthetic and reductionism in one go and what replaced them",
     "quine two dogmas empiricism analytic synthetic reductionism holism 1951"),
    # --- 14 decision ---
    ("Opted to teach Feyerabend's Against Method as a deliberate counterweight rather than a straw man; the anything-goes slogan is a methodological anarchism aimed at Lakatos and late Popper, not at science itself.", "decision", "knowledge", False,
     [("Feyerabend", "person"), ("Against Method", "publication"), ("anything-goes", "concept"), ("methodological anarchism", "theory"), ("Lakatos", "person"), ("Popper", "person")],
     [("Against Method", "Feyerabend", "AUTHORED_BY"), ("methodological anarchism", "Feyerabend", "AUTHORED_BY"), ("Against Method", "Lakatos", "CONTRADICTS")],
     "how is Feyerabend's Against Method taught and against whom is the anarchism actually aimed",
     "feyerabend against method anything goes methodological anarchism lakatos"),
    # --- 15 architecture ---
    ("The justification-structure week contrasts coherentism with foundationalism directly: coherence among beliefs as mutual support versus a privileged base of non-inferential beliefs that props the rest of the web.", "architecture", "knowledge", False,
     [("coherentism", "theory"), ("foundationalism", "theory"), ("non-inferential beliefs", "concept"), ("mutual support", "concept")],
     [("coherentism", "foundationalism", "CONTRADICTS"), ("foundationalism", "non-inferential beliefs", "HAS_PART"), ("coherentism", "mutual support", "USES")],
     "how does the justification-structure week frame coherentism against foundationalism",
     "coherentism foundationalism non inferential belief base web mutual"),
    # --- 16 milestone ---
    ("Completed the Wittgenstein double-header: one session on the Tractatus picture theory of meaning and truth-functional logic, the second on the later turn to language games in Philosophical Investigations.", "milestone", "knowledge", False,
     [("Wittgenstein", "person"), ("Tractatus", "publication"), ("picture theory", "theory"), ("Philosophical Investigations", "publication"), ("language games", "concept"), ("truth-functional logic", "concept")],
     [("Tractatus", "Wittgenstein", "AUTHORED_BY"), ("Philosophical Investigations", "Wittgenstein", "AUTHORED_BY"), ("picture theory", "Tractatus", "PUBLISHED_IN"), ("language games", "Philosophical Investigations", "PUBLISHED_IN")],
     "which Wittgenstein double-header ran and what were the themes of each session",
     "wittgenstein tractatus picture theory philosophical investigations language games"),
    # --- 17 fact ---
    ("The no-miracles argument claims scientific realism is the only philosophy that does not make the success of science a miracle, since approximate truth of theories explains why predictions keep working.", "fact", "knowledge", False,
     [("no-miracles argument", "claim"), ("scientific realism", "theory"), ("approximate truth", "concept"), ("success of science", "concept")],
     [("no-miracles argument", "scientific realism", "SUPPORTS"), ("approximate truth", "success of science", "CAUSES")],
     "what does the no-miracles argument say about realism and the success of scientific prediction",
     "no miracles argument realism approximate truth success science predict"),
    # --- 18 decision ---
    ("Switched the probability semantics unit from frequentism to subjective Bayesianism; Dutch book arguments and De Finetti's representation theorem give a cleaner decision-theoretic grounding than long-run frequencies.", "decision", "knowledge", False,
     [("frequentism", "theory"), ("subjective Bayesianism", "theory"), ("Dutch book arguments", "method"), ("De Finetti", "person"), ("representation theorem", "theory")],
     [("subjective Bayesianism", "frequentism", "REPLACES"), ("Dutch book arguments", "subjective Bayesianism", "SUPPORTS"), ("representation theorem", "De Finetti", "AUTHORED_BY")],
     "which probability semantics replaced frequentism and which arguments did the swap lean on",
     "frequentism subjective bayesian dutch book de finetti representation"),
    # --- 19 reference ---
    ("For the Kuhn-Popper debate session the core texts are Lakatos and Musgrave's Criticism and the Growth of Knowledge plus Popper's Normal Science and Its Dangers as a direct reply to Kuhn.", "reference", "knowledge", False,
     [("Criticism and the Growth of Knowledge", "publication"), ("Lakatos and Musgrave", "person"), ("Normal Science and Its Dangers", "publication"), ("Popper", "person"), ("Kuhn", "person")],
     [("Criticism and the Growth of Knowledge", "Lakatos and Musgrave", "AUTHORED_BY"), ("Normal Science and Its Dangers", "Popper", "AUTHORED_BY"), ("Normal Science and Its Dangers", "Kuhn", "CONTRADICTS")],
     "which paired texts ground the Kuhn-Popper debate session and who replies directly to Kuhn",
     "popper kuhn debate lakatos musgrave criticism growth knowledge normal"),
    # --- 20 architecture ---
    ("The replication crisis case study layers three ideas: Ioannidis's Why Most Published Research Findings Are False as the wake-up, p-hacking as the mechanism, and pre-registration as the proposed fix.", "architecture", "knowledge", False,
     [("replication crisis", "concept"), ("Ioannidis", "person"), ("Why Most Published Research Findings Are False", "publication"), ("p-hacking", "method"), ("pre-registration", "method")],
     [("Why Most Published Research Findings Are False", "Ioannidis", "AUTHORED_BY"), ("p-hacking", "replication crisis", "CAUSES"), ("pre-registration", "p-hacking", "FIXES")],
     "how does the replication-crisis case study layer Ioannidis p-hacking and pre-registration",
     "replication crisis ioannidis false findings p hacking pre registration"),
    # --- 21 milestone ---
    ("Finalised the Open Science Framework workflow for graduate projects: all hypotheses pre-registered before data collection, analysis scripts committed before unblinding, and deviations logged as amendments.", "milestone", "knowledge", False,
     [("Open Science Framework", "platform"), ("pre-registered", "method"), ("analysis scripts", "concept"), ("unblinding", "concept"), ("amendments", "concept")],
     [("pre-registered", "Open Science Framework", "DEPLOYED_ON"), ("analysis scripts", "unblinding", "RELATED_TO")],
     "how does the graduate-project workflow on Open Science Framework order pre-registration and unblinding",
     "open science framework pre register analysis unblind amendment workflow"),
    # --- 22 problem ---
    ("The p-hacking pattern keeps surfacing in student replication projects: researchers try multiple subgroup cuts and only report the significant one, which inflates false-positive rates well past the nominal alpha.", "problem", "knowledge", False,
     [("p-hacking", "method"), ("subgroup cuts", "concept"), ("false-positive rates", "concept"), ("alpha", "concept")],
     [("p-hacking", "false-positive rates", "CAUSES"), ("subgroup cuts", "p-hacking", "HAS_PART")],
     "which researcher practice keeps inflating false positives in the replication projects",
     "p hacking subgroup false positive alpha significance inflate replicate"),
    # --- 23 fact ---
    ("Process reliabilism defines knowledge as true belief produced by a reliable cognitive process, which sidesteps Gettier cases by making the truth-tracking mechanism itself part of the justification condition.", "fact", "knowledge", False,
     [("reliabilism", "theory"), ("reliable cognitive process", "concept"), ("Gettier cases", "concept"), ("true belief", "concept")],
     [("reliabilism", "Gettier cases", "FIXES"), ("reliabilism", "reliable cognitive process", "USES")],
     "how does reliabilism redefine knowledge and why does it sidestep Gettier counterexamples",
     "reliabilism true belief reliable process gettier case cognitive track"),
    # --- 24 decision ---
    ("Chose to treat the Duhem-Quine thesis and underdetermination as one combined topic rather than two lectures; students conflated them anyway, so a single careful treatment reduced the confusion from midterms.", "decision", "knowledge", False,
     [("Duhem-Quine thesis", "theory"), ("underdetermination", "concept"), ("midterms", "event")],
     [("Duhem-Quine thesis", "underdetermination", "SUPPORTS")],
     "why did the Duhem-Quine thesis and underdetermination collapse into one lecture",
     "duhem quine underdetermination combine lecture midterm confusion"),
    # --- 25 architecture ---
    ("Bayesian confirmation theory slots into the course as the formal reply to Hume's induction problem: priors move under evidence by conditionalisation, and long-run convergence falls out of the washing-out theorems.", "architecture", "knowledge", False,
     [("Bayesian confirmation theory", "theory"), ("Hume", "person"), ("induction problem", "concept"), ("conditionalisation", "method"), ("washing-out theorems", "theory")],
     [("Bayesian confirmation theory", "induction problem", "FIXES"), ("conditionalisation", "Bayesian confirmation theory", "USES"), ("induction problem", "Hume", "AUTHORED_BY")],
     "how does Bayesian confirmation theory respond to Hume's induction problem in the course",
     "bayesian confirmation hume induction conditionalisation washing out prior"),
    # --- 26 preference ---
    ("I prefer teaching Popper before Kuhn even though Kuhn's book came out later; the falsifiability framing gives students a target the paradigm-shift critique can then complicate productively.", "preference", "knowledge", False,
     [("Popper", "person"), ("Kuhn", "person"), ("falsifiability", "concept"), ("paradigm-shift", "concept")],
     [("paradigm-shift", "falsifiability", "CONTRADICTS")],
     "which ordering do I prefer for Popper and Kuhn in the syllabus and what pedagogical reason drives it",
     "popper kuhn teach order falsifiability paradigm shift target critique"),
    # --- 27 fact ---
    ("Van Fraassen's constructive empiricism holds that the aim of science is empirical adequacy rather than truth, so accepting a theory means believing it saves the phenomena, not that its unobservable posits exist.", "fact", "knowledge", False,
     [("Van Fraassen", "person"), ("constructive empiricism", "theory"), ("empirical adequacy", "concept"), ("unobservable posits", "concept")],
     [("constructive empiricism", "Van Fraassen", "AUTHORED_BY"), ("constructive empiricism", "empirical adequacy", "USES")],
     "what does Van Fraassen's constructive empiricism say the aim of science actually is",
     "van fraassen constructive empiricism empirical adequacy save phenomena"),
    # --- 28 decision ---
    ("Locked in Jaynes's maximum entropy principle as the default prior-choice story for the Bayesian module; it gives a principled answer where uniform priors are obviously wrong without sliding into subjective hand-waving.", "decision", "knowledge", False,
     [("Jaynes", "person"), ("maximum entropy principle", "method"), ("prior-choice", "concept"), ("uniform priors", "concept"), ("Bayesian module", "project")],
     [("maximum entropy principle", "Jaynes", "AUTHORED_BY"), ("maximum entropy principle", "uniform priors", "REPLACES")],
     "which principle won as the default prior-choice story in the Bayesian module and why",
     "jaynes maximum entropy prior uniform bayesian module principled choice"),
    # --- 29 architecture ---
    ("The scientific-change week has three candidate engines stacked side by side: Popperian conjecture-and-refutation, Kuhnian paradigm shifts, and Lakatosian progressive versus degenerating research programmes.", "architecture", "knowledge", False,
     [("conjecture-and-refutation", "method"), ("paradigm shifts", "concept"), ("progressive", "concept"), ("degenerating", "concept"), ("research programmes", "theory"), ("Popper", "person"), ("Kuhn", "person"), ("Lakatos", "person")],
     [("conjecture-and-refutation", "Popper", "AUTHORED_BY"), ("paradigm shifts", "Kuhn", "AUTHORED_BY"), ("research programmes", "Lakatos", "AUTHORED_BY")],
     "which three engines of scientific change sit side by side in that week of the course",
     "popper conjecture refutation kuhn paradigm lakatos progressive degenerate"),
    # --- 30 milestone ---
    ("Wrapped the Gettier problem week with a unified tree: every fix either strengthens justification via reliabilism, adds a no-defeaters clause, or goes externalist; the tree itself became the take-home exam prompt.", "milestone", "knowledge", False,
     [("Gettier problem", "concept"), ("reliabilism", "theory"), ("no-defeaters clause", "concept"), ("externalist", "theory"), ("take-home exam", "event")],
     [("reliabilism", "Gettier problem", "FIXES"), ("no-defeaters clause", "Gettier problem", "FIXES"), ("externalist", "Gettier problem", "FIXES")],
     "how did the Gettier problem week close and what became the exam prompt",
     "gettier problem reliabilism defeaters externalist take home exam tree"),
    # --- 31 reference ---
    ("For the confirmation-theory lecture the recommended backup reading is Howson and Urbach's Scientific Reasoning: The Bayesian Approach alongside Earman's Bayes or Bust for the critical side.", "reference", "knowledge", False,
     [("Howson and Urbach", "person"), ("Scientific Reasoning: The Bayesian Approach", "publication"), ("Earman", "person"), ("Bayes or Bust", "publication")],
     [("Scientific Reasoning: The Bayesian Approach", "Howson and Urbach", "AUTHORED_BY"), ("Bayes or Bust", "Earman", "AUTHORED_BY"), ("Bayes or Bust", "Scientific Reasoning: The Bayesian Approach", "CONTRADICTS")],
     "which two books pair up as pro and con readings for the confirmation-theory lecture",
     "howson urbach scientific reasoning bayesian earman bayes bust confirmation"),
    # --- 32 decision ---
    ("Decided to close each methods session with a short Carnap versus Popper framing exercise; Carnap's inductive logic gives a degree-of-confirmation reading while Popper refuses confirmation and sticks to corroboration.", "decision", "knowledge", False,
     [("Carnap", "person"), ("Popper", "person"), ("inductive logic", "field"), ("degree-of-confirmation", "concept"), ("corroboration", "concept")],
     [("inductive logic", "Carnap", "AUTHORED_BY"), ("corroboration", "Popper", "AUTHORED_BY"), ("degree-of-confirmation", "corroboration", "CONTRADICTS")],
     "how is each methods session closed with a Carnap versus Popper exercise",
     "carnap popper inductive logic confirmation corroboration methods framing"),
    # --- 33 preference ---
    ("My preference in epistemology office hours is to push students toward virtue reliabilism rather than pure process reliabilism; tying justification to cognitive character dodges the generality problem about process types.", "preference", "knowledge", False,
     [("virtue reliabilism", "theory"), ("process reliabilism", "theory"), ("generality problem", "concept"), ("cognitive character", "concept")],
     [("virtue reliabilism", "process reliabilism", "IMPROVES_ON"), ("virtue reliabilism", "generality problem", "FIXES")],
     "which reliabilism flavour do I push in office hours and which problem does it dodge",
     "virtue reliabilism process generality problem cognitive character prefer"),
    # --- 34 problem ---
    ("Students consistently misread the Duhem-Quine thesis as saying theories can never be tested, rather than saying hypotheses never face the tribunal alone; the fix was a worked-example problem set on auxiliary-assumption swaps.", "problem", "knowledge", False,
     [("Duhem-Quine thesis", "theory"), ("tribunal", "concept"), ("auxiliary-assumption swaps", "method")],
     [("auxiliary-assumption swaps", "Duhem-Quine thesis", "APPLIES_TO")],
     "which misreading of the Duhem-Quine thesis keeps recurring and how did the fix look",
     "duhem quine misread test tribunal auxiliary assumption swap problem"),
    # --- 35 architecture ---
    ("Scientific-realism debate gets a layered map: entity realism at the bottom, structural realism in the middle, and full-blown theoretical realism on top; pessimistic meta-induction attacks the top two directly.", "architecture", "knowledge", False,
     [("entity realism", "theory"), ("structural realism", "theory"), ("theoretical realism", "theory"), ("pessimistic meta-induction", "claim")],
     [("structural realism", "entity realism", "BUILDS_ON"), ("theoretical realism", "structural realism", "BUILDS_ON"), ("pessimistic meta-induction", "theoretical realism", "CONTRADICTS")],
     "how is the scientific-realism debate layered and which level does pessimistic meta-induction hit",
     "entity structural theoretical realism pessimistic meta induction layer"),
    # --- 36 fact ---
    ("Kuhn's incommensurability thesis says that successive paradigms do not share a neutral observation language, so rival theories cannot be compared point-by-point, which blocks the cumulative-progress picture.", "fact", "knowledge", False,
     [("Kuhn", "person"), ("incommensurability thesis", "theory"), ("observation language", "concept"), ("cumulative-progress", "concept")],
     [("incommensurability thesis", "Kuhn", "AUTHORED_BY"), ("incommensurability thesis", "cumulative-progress", "CONTRADICTS")],
     "what does Kuhn's incommensurability thesis deny and which picture of science does it block",
     "kuhn incommensurability observation language cumulative progress paradigm"),
    # --- 37 milestone ---
    ("Shipped the updated epistemology reading pack after the 2026 revision: Wittgenstein's two works, Quine's Two Dogmas, Gettier's three pages, and Goldman on reliabilism now come in one bound coursepack.", "milestone", "knowledge", False,
     [("Wittgenstein", "person"), ("Quine", "person"), ("Two Dogmas", "publication"), ("Gettier", "person"), ("Goldman", "person"), ("reliabilism", "theory"), ("2026", "date")],
     [("Two Dogmas", "Quine", "AUTHORED_BY"), ("reliabilism", "Goldman", "AUTHORED_BY")],
     "which texts made the 2026 epistemology coursepack revision",
     "epistemology reading pack 2026 wittgenstein quine gettier goldman reliabilism"),
    # --- 38 decision ---
    ("Opted against pure foundationalism when designing the theory-of-justification rubric; coherentism plus a mild externalist check on the base beliefs handles sceptical regress without requiring incorrigible foundations.", "decision", "knowledge", False,
     [("foundationalism", "theory"), ("coherentism", "theory"), ("externalist", "theory"), ("sceptical regress", "concept"), ("incorrigible foundations", "concept")],
     [("coherentism", "foundationalism", "REPLACES"), ("coherentism", "sceptical regress", "FIXES")],
     "which justification stance did the rubric adopt instead of pure foundationalism",
     "foundationalism coherentism externalist sceptical regress rubric justification"),
    # --- 39 reference ---
    ("Anchor texts for the philosophy-of-science comprehensive exam: Popper's Conjectures and Refutations, Kuhn's Structure, Lakatos and Musgrave volume, Feyerabend's Against Method, and Jaynes's Probability Theory.", "reference", "knowledge", False,
     [("Conjectures and Refutations", "publication"), ("Popper", "person"), ("Structure", "publication"), ("Kuhn", "person"), ("Lakatos and Musgrave volume", "publication"), ("Against Method", "publication"), ("Feyerabend", "person"), ("Probability Theory", "publication"), ("Jaynes", "person")],
     [("Conjectures and Refutations", "Popper", "AUTHORED_BY"), ("Structure", "Kuhn", "AUTHORED_BY"), ("Against Method", "Feyerabend", "AUTHORED_BY"), ("Probability Theory", "Jaynes", "AUTHORED_BY")],
     "which five anchor texts make up the philosophy-of-science comprehensive exam list",
     "popper kuhn lakatos feyerabend jaynes comprehensive exam anchor reading"),
    # --- 40 fact ---
    ("Bayesian epistemology ties degree of belief to betting behaviour through Dutch book arguments: any agent whose credences violate the probability axioms can be offered a combination of bets that guarantees a loss.", "fact", "knowledge", False,
     [("Bayesian epistemology", "field"), ("Dutch book arguments", "method"), ("degree of belief", "concept"), ("probability axioms", "concept")],
     [("Dutch book arguments", "Bayesian epistemology", "SUPPORTS"), ("Dutch book arguments", "probability axioms", "USES")],
     "how do Dutch book arguments connect degree of belief to the probability axioms",
     "bayesian epistemology dutch book degree belief probability axiom bet"),
    # --- 41 architecture ---
    ("The three-argument anti-realism case study stacks pessimistic meta-induction, underdetermination, and the Duhem-Quine thesis as independent pressures on the realist's inference from predictive success to approximate truth.", "architecture", "knowledge", False,
     [("pessimistic meta-induction", "claim"), ("underdetermination", "concept"), ("Duhem-Quine thesis", "theory"), ("anti-realism", "theory"), ("predictive success", "concept"), ("approximate truth", "concept")],
     [("pessimistic meta-induction", "anti-realism", "SUPPORTS"), ("underdetermination", "anti-realism", "SUPPORTS"), ("Duhem-Quine thesis", "anti-realism", "SUPPORTS")],
     "which three independent arguments stack as pressure on the realist inference in the case study",
     "pessimistic underdetermination duhem quine anti realism predict approximate"),
    # --- 42 preference ---
    ("Preference in grading essays: mark down any student who uses falsifiability as a synonym for scientific; Popper's criterion is about risky prohibitions, not a sociological stamp of approval.", "preference", "knowledge", False,
     [("falsifiability", "concept"), ("Popper", "person"), ("risky prohibitions", "concept")],
     [("falsifiability", "risky prohibitions", "USES"), ("falsifiability", "Popper", "AUTHORED_BY")],
     "which essay mistake about falsifiability draws an automatic grade deduction",
     "falsifiability synonym scientific popper risky prohibition essay grade"),
    # --- 43. noise ---
     ("The department coffee maker finally started producing drinkable espresso after the new grinder calibration took hold this morning.", "fact", "noise", True, [], [], None, None),
    # --- 44 milestone ---
    ("Finished migrating the seminar's reading list onto Open Science Framework so every assigned paper links to its pre-registration, replication attempts, and any retraction notices in one click.", "milestone", "knowledge", False,
     [("Open Science Framework", "platform"), ("pre-registration", "method"), ("replication attempts", "concept"), ("retraction notices", "concept")],
     [("pre-registration", "Open Science Framework", "DEPLOYED_ON"), ("replication attempts", "Open Science Framework", "DEPLOYED_ON")],
     "which platform migration lets seminar papers link to pre-registrations and retractions in one click",
     "open science framework reading list pre registration replication retraction"),
    # --- 45 decision ---
    ("Dropped naive falsificationism from the introductory slides after repeated objections from students who'd seen the Duhem-Quine thesis earlier; sophisticated falsificationism from Lakatos takes its slot now.", "decision", "knowledge", False,
     [("naive falsificationism", "theory"), ("sophisticated falsificationism", "theory"), ("Duhem-Quine thesis", "theory"), ("Lakatos", "person")],
     [("sophisticated falsificationism", "naive falsificationism", "REPLACES"), ("sophisticated falsificationism", "Lakatos", "AUTHORED_BY"), ("Duhem-Quine thesis", "naive falsificationism", "CONTRADICTS")],
     "which falsificationism flavour replaced naive falsificationism in the intro slides and why",
     "naive sophisticated falsificationism duhem quine lakatos slide replace"),
    # --- 46 fact ---
    ("Carnap's inductive logic builds a confirmation function c(h,e) that outputs a real number between zero and one, with logical probability defined over state descriptions in a formal language.", "fact", "knowledge", False,
     [("Carnap", "person"), ("inductive logic", "field"), ("confirmation function", "method"), ("logical probability", "concept"), ("state descriptions", "concept")],
     [("inductive logic", "Carnap", "AUTHORED_BY"), ("confirmation function", "inductive logic", "HAS_PART")],
     "how does Carnap's inductive logic formalise confirmation and over what kind of objects is logical probability defined",
     "carnap inductive logic confirmation function state description formal language"),
    # --- 47 architecture ---
    ("The Bayesian module pipelines three stages: elicit prior with maximum entropy, update via conditionalisation on evidence, and feed the posterior back into decision theory for expected-utility action.", "architecture", "knowledge", False,
     [("Bayesian module", "project"), ("maximum entropy", "method"), ("conditionalisation", "method"), ("posterior", "concept"), ("decision theory", "field"), ("expected-utility", "concept")],
     [("maximum entropy", "Bayesian module", "USES"), ("conditionalisation", "Bayesian module", "USES"), ("decision theory", "Bayesian module", "DEPENDS_ON")],
     "how does the Bayesian module pipeline prior elicitation update and decision stages",
     "bayesian module maximum entropy conditionalisation posterior decision utility"),
    # --- 48 problem ---
    ("The replication crisis case reviews keep hitting the garden of forking paths: honest researchers run reasonable but data-dependent analyses, which still inflates false-positive rates the way outright p-hacking does.", "problem", "knowledge", False,
     [("replication crisis", "concept"), ("garden of forking paths", "concept"), ("data-dependent analyses", "method"), ("false-positive rates", "concept"), ("p-hacking", "method")],
     [("garden of forking paths", "false-positive rates", "CAUSES"), ("garden of forking paths", "p-hacking", "RELATED_TO")],
     "which analysis pattern shows up as a sibling of p-hacking in the replication-crisis reviews",
     "garden forking paths replication crisis data dependent false positive"),
    # --- 49 milestone ---
    ("Published the final version of the epistemology handout with the expanded triangle linking Gettier, reliabilism, and virtue epistemology; the graduate cohort has confirmed it replaces the previous justified-true-belief table.", "milestone", "knowledge", False,
     [("epistemology handout", "publication"), ("Gettier", "person"), ("reliabilism", "theory"), ("virtue epistemology", "theory"), ("justified-true-belief", "concept")],
     [("reliabilism", "justified-true-belief", "REPLACES"), ("virtue epistemology", "reliabilism", "BUILDS_ON")],
     "which expanded triangle landed in the final epistemology handout and what did it replace",
     "epistemology handout gettier reliabilism virtue triangle justified true belief"),
    # --- 50 reference ---
    ("For the Feyerabend week the supplementary pairing is Lakatos's History of Science and Its Rational Reconstructions plus Hacking's Representing and Intervening as a realism-friendly counterweight.", "reference", "knowledge", False,
     [("Feyerabend", "person"), ("Lakatos", "person"), ("History of Science and Its Rational Reconstructions", "publication"), ("Hacking", "person"), ("Representing and Intervening", "publication")],
     [("History of Science and Its Rational Reconstructions", "Lakatos", "AUTHORED_BY"), ("Representing and Intervening", "Hacking", "AUTHORED_BY"), ("Representing and Intervening", "Feyerabend", "CONTRADICTS")],
     "which two supplementary readings pair with Feyerabend for balance that week",
     "feyerabend lakatos history rational reconstruction hacking representing intervening"),
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
