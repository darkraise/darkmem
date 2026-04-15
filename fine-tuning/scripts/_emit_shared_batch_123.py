"""One-off emitter for shared-base batch-123 — knowledge domain (pure mathematics research, post-1950 frontier).

Writes 50 rows with ids shared-06101..06150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_123.tmp.jsonl"
ID_OFFSET = 6100

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Andrew Wiles's 1995 Annals of Mathematics paper proved the modularity of semistable elliptic curves and thereby settled Fermat's Last Theorem.", "milestone", "knowledge", False,
     [("Andrew Wiles", "person"), ("1995", "date"), ("Annals of Mathematics", "publication"), ("semistable elliptic curves", "concept"), ("Fermat's Last Theorem", "concept")],
     [("Fermat's Last Theorem", "Andrew Wiles", "AUTHORED_BY")],
     "who closed the three-century-old diophantine question by proving a mid-range case of Taniyama-Shimura in 1995",
     "Wiles modularity semistable elliptic curves Fermat Annals year"),
    # --- 2 ---
    ("Richard Taylor and Andrew Wiles's companion paper repaired the Euler-system gap in the original Wiles manuscript and completed the proof of the Taniyama-Shimura conjecture for semistable curves.", "fact", "knowledge", False,
     [("Richard Taylor", "person"), ("Andrew Wiles", "person"), ("Euler-system gap", "concept"), ("Taniyama-Shimura conjecture", "concept")],
     [("Taniyama-Shimura conjecture", "Richard Taylor", "AUTHORED_BY")],
     "which companion paper patched the Euler-system gap in Wiles's first Fermat manuscript",
     "Taylor Wiles Euler system gap Taniyama Shimura semistable repair"),
    # --- 3 ---
    ("Pierre Deligne's 1974 Inventiones proof of the Weil conjectures established the Riemann hypothesis for varieties over finite fields and earned him the 1978 Fields Medal.", "milestone", "knowledge", False,
     [("Pierre Deligne", "person"), ("1974", "date"), ("Inventiones", "publication"), ("Weil conjectures", "concept"), ("Fields Medal", "event")],
     [("Weil conjectures", "Pierre Deligne", "AUTHORED_BY"), ("Weil conjectures", "Pierre Deligne", "IMPROVES_ON")],
     "whose 1974 Inventiones paper proved the Weil conjectures and won the 1978 Fields Medal",
     "Deligne Weil conjectures Riemann hypothesis finite fields Inventiones"),
    # --- 4 ---
    ("Alexander Grothendieck's Elements de geometrie algebrique, published through IHES between 1960 and 1967, refounded algebraic geometry on the language of schemes.", "reference", "knowledge", False,
     [("Alexander Grothendieck", "person"), ("Elements de geometrie algebrique", "publication"), ("IHES", "organization"), ("1960", "date"), ("1967", "date"), ("schemes", "concept")],
     [("Elements de geometrie algebrique", "Alexander Grothendieck", "AUTHORED_BY"), ("schemes", "Alexander Grothendieck", "AUTHORED_BY")],
     "which IHES treatise series refounded algebraic geometry on schemes during the 1960s",
     "EGA Grothendieck schemes IHES refoundation algebraic geometry years"),
    # --- 5 ---
    ("David Mumford's Geometric Invariant Theory, published by Springer in 1965, provided the first rigorous construction of moduli spaces as GIT quotients.", "reference", "knowledge", False,
     [("David Mumford", "person"), ("Geometric Invariant Theory", "publication"), ("Springer", "organization"), ("1965", "date"), ("moduli spaces", "concept"), ("GIT quotients", "concept")],
     [("Geometric Invariant Theory", "David Mumford", "AUTHORED_BY")],
     "which 1965 Springer book first constructed moduli spaces as GIT quotients",
     "Mumford GIT moduli spaces quotients Springer year construction"),
    # --- 6 ---
    ("Robin Hartshorne's Algebraic Geometry, issued by Springer in 1977, consolidated Chapter III sheaf cohomology methods as the standard graduate entry to the field.", "reference", "knowledge", False,
     [("Robin Hartshorne", "person"), ("Algebraic Geometry", "publication"), ("Springer", "organization"), ("1977", "date"), ("Chapter III", "concept"), ("sheaf cohomology", "concept")],
     [("Algebraic Geometry", "Robin Hartshorne", "AUTHORED_BY")],
     "which 1977 Springer textbook standardised Chapter III sheaf cohomology for graduate students",
     "Hartshorne algebraic geometry sheaf cohomology Chapter III textbook year"),
    # --- 7 ---
    ("Grigori Perelman's 2002-2003 arXiv preprints proved the Poincare conjecture via Ricci flow with surgery, superseding two decades of earlier Ricci-flow attempts.", "milestone", "knowledge", False,
     [("Grigori Perelman", "person"), ("2002", "date"), ("2003", "date"), ("arXiv", "organization"), ("Poincare conjecture", "concept"), ("Ricci flow with surgery", "method"), ("earlier Ricci-flow attempts", "concept")],
     [("Poincare conjecture", "Grigori Perelman", "AUTHORED_BY"), ("Ricci flow with surgery", "earlier Ricci-flow attempts", "REPLACES")],
     "which early-2000s preprint series used surgical Ricci evolution to clinch Thurston's topology target in dimension three",
     "Perelman Ricci flow surgery Poincare arXiv preprint years"),
    # --- 8 ---
    ("John Milnor's 1956 Annals paper constructed the first exotic smooth structures on the seven-sphere, opening differential topology as an independent field.", "milestone", "knowledge", False,
     [("John Milnor", "person"), ("1956", "date"), ("Annals", "publication"), ("exotic smooth structures", "concept"), ("seven-sphere", "concept"), ("differential topology", "field")],
     [("exotic smooth structures", "John Milnor", "AUTHORED_BY")],
     "which 1956 Annals paper first produced exotic smooth structures on the seven-sphere",
     "Milnor exotic seven sphere smooth structure differential topology year"),
    # --- 9 ---
    ("William Thurston's geometrisation conjecture, announced in 1982, organised three-manifolds around eight model geometries and improves on the earlier Haken-manifold picture.", "milestone", "knowledge", False,
     [("William Thurston", "person"), ("geometrisation conjecture", "concept"), ("1982", "date"), ("three-manifolds", "concept"), ("eight model geometries", "concept"), ("Haken-manifold picture", "concept")],
     [("geometrisation conjecture", "William Thurston", "AUTHORED_BY"), ("geometrisation conjecture", "Haken-manifold picture", "IMPROVES_ON")],
     "whose 1982 conjecture organised three-manifolds around eight model geometries",
     "Thurston geometrisation eight geometries three manifolds year announcement"),
    # --- 10. noise ---
    ("Let me double-check the sign convention in that Cartan formula before I paste it into the notes.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Saunders Mac Lane's Categories for the Working Mathematician, published by Springer in 1971, remains the canonical graduate introduction to classical 1-category theory.", "reference", "knowledge", False,
     [("Saunders Mac Lane", "person"), ("Categories for the Working Mathematician", "publication"), ("Springer", "organization"), ("1971", "date"), ("1-category theory", "field")],
     [("Categories for the Working Mathematician", "Saunders Mac Lane", "AUTHORED_BY")],
     "which 1971 Springer book became the canonical graduate text on 1-category theory",
     "Mac Lane categories working mathematician Springer 1 category text year"),
    # --- 12 ---
    ("Jacob Lurie's Higher Topos Theory, issued by Princeton University Press in 2009, reworked classical category-theoretic constructions through quasicategories and improves on strict 1-categorical foundations.", "reference", "knowledge", False,
     [("Jacob Lurie", "person"), ("Higher Topos Theory", "publication"), ("Princeton University Press", "organization"), ("2009", "date"), ("quasicategories", "concept"), ("strict 1-categorical foundations", "concept")],
     [("Higher Topos Theory", "Jacob Lurie", "AUTHORED_BY"), ("quasicategories", "strict 1-categorical foundations", "IMPROVES_ON")],
     "which 2009 Princeton book reworked category theory through quasicategories",
     "Lurie HTT quasicategories higher topos theory Princeton year"),
    # --- 13 ---
    ("Andre Joyal's 2008 theory of quasi-categories synthesised simplicial homotopy theory with category theory and was adopted by Lurie as the model for infinity-categories.", "fact", "knowledge", False,
     [("Andre Joyal", "person"), ("2008", "date"), ("quasi-categories", "concept"), ("simplicial homotopy theory", "field"), ("infinity-categories", "concept")],
     [("quasi-categories", "Andre Joyal", "AUTHORED_BY")],
     "who developed the quasi-category model later adopted for infinity-categories",
     "Joyal quasi categories simplicial homotopy infinity model year"),
    # --- 14 ---
    ("Paul Cohen's 1963 forcing method proved the independence of the continuum hypothesis from ZFC and replaced earlier relative-consistency arguments that had only established Godel's one-sided result.", "milestone", "knowledge", False,
     [("Paul Cohen", "person"), ("1963", "date"), ("forcing method", "method"), ("continuum hypothesis", "concept"), ("ZFC", "concept"), ("earlier relative-consistency arguments", "concept")],
     [("forcing method", "Paul Cohen", "AUTHORED_BY"), ("forcing method", "earlier relative-consistency arguments", "REPLACES")],
     "which 1963 method proved the continuum hypothesis independent of ZFC",
     "Cohen forcing continuum hypothesis independence ZFC year replacement"),
    # --- 15 ---
    ("W. Hugh Woodin's work in the 1980s on Woodin cardinals reframed inner model theory by supplying the large-cardinal strength behind projective determinacy.", "reference", "knowledge", False,
     [("W. Hugh Woodin", "person"), ("Woodin cardinals", "concept"), ("inner model theory", "field"), ("projective determinacy", "concept")],
     [("Woodin cardinals", "W. Hugh Woodin", "AUTHORED_BY"), ("projective determinacy", "Woodin cardinals", "DEPENDS_ON")],
     "which set theorist in the late twentieth century lifted inner-model theory by defining the cardinal class that underwrites full analytical determinacy",
     "Woodin cardinals projective determinacy inner model large cardinal"),
    # --- 16 ---
    ("Donald Martin and John Steel's 1988 paper proved projective determinacy from infinitely many Woodin cardinals and was published in the Journal of the American Mathematical Society.", "fact", "knowledge", False,
     [("Donald Martin", "person"), ("John Steel", "person"), ("1988", "date"), ("projective determinacy", "concept"), ("Woodin cardinals", "concept"), ("Journal of the American Mathematical Society", "publication")],
     [("projective determinacy", "Donald Martin", "AUTHORED_BY")],
     "which 1988 paper derived projective determinacy from infinitely many Woodin cardinals",
     "Martin Steel projective determinacy Woodin JAMS year proof"),
    # --- 17 ---
    ("Endre Szemeredi's 1975 regularity lemma, published in Acta Arithmetica, proved that dense subsets of the integers contain arbitrarily long arithmetic progressions.", "milestone", "knowledge", False,
     [("Endre Szemeredi", "person"), ("1975", "date"), ("regularity lemma", "concept"), ("Acta Arithmetica", "publication"), ("arithmetic progressions", "concept")],
     [("regularity lemma", "Endre Szemeredi", "AUTHORED_BY")],
     "which 1975 Acta Arithmetica paper introduced the regularity lemma for dense subsets",
     "Szemeredi regularity lemma dense arithmetic progressions Acta year"),
    # --- 18 ---
    ("Ben Green and Terence Tao's 2008 Annals of Mathematics paper proved that the primes contain arbitrarily long arithmetic progressions and earned Tao the 2006 Fields Medal citation.", "milestone", "knowledge", False,
     [("Ben Green", "person"), ("Terence Tao", "person"), ("2008", "date"), ("Annals of Mathematics", "publication"), ("primes", "concept"), ("Fields Medal", "event")],
     [("primes", "Ben Green", "AUTHORED_BY")],
     "which Cambridge-Princeton collaboration proved that prime sets embed every finite arithmetic pattern",
     "Green Tao primes arithmetic progressions Annals year Fields Medal"),
    # --- 19 ---
    ("Terence Tao and Van Vu's 2010 universality results on random matrices replaced earlier case-by-case bulk estimates and appeared in Acta Mathematica.", "reference", "knowledge", False,
     [("Terence Tao", "person"), ("Van Vu", "person"), ("2010", "date"), ("universality results", "finding"), ("random matrices", "concept"), ("Acta Mathematica", "publication"), ("earlier case-by-case bulk estimates", "concept")],
     [("universality results", "Terence Tao", "AUTHORED_BY"), ("universality results", "earlier case-by-case bulk estimates", "REPLACES")],
     "which 2010 Acta Mathematica paper proved universality for random matrices",
     "Tao Vu universality random matrices Acta Mathematica year"),
    # --- 20 ---
    ("George David Birkhoff's 1931 pointwise ergodic theorem anchors modern ergodic theory and replaced von Neumann's earlier mean-ergodic statement as the primary convergence tool.", "milestone", "knowledge", False,
     [("George David Birkhoff", "person"), ("1931", "date"), ("pointwise ergodic theorem", "concept"), ("ergodic theory", "field"), ("von Neumann's earlier mean-ergodic statement", "concept")],
     [("pointwise ergodic theorem", "George David Birkhoff", "AUTHORED_BY"), ("pointwise ergodic theorem", "von Neumann's earlier mean-ergodic statement", "IMPROVES_ON")],
     "whose 1931 pointwise theorem became the primary convergence tool in ergodic theory",
     "Birkhoff pointwise ergodic theorem von Neumann mean year"),
    # --- 21 ---
    ("Nets Katz and Terence Tao's 2002 work on the Kakeya conjecture combined additive combinatorics with geometric measure theory to push dimension bounds upward.", "fact", "knowledge", False,
     [("Nets Katz", "person"), ("Terence Tao", "person"), ("2002", "date"), ("Kakeya conjecture", "concept"), ("additive combinatorics", "field"), ("geometric measure theory", "field")],
     [("Kakeya conjecture", "Nets Katz", "AUTHORED_BY")],
     "who raised the lower Minkowski bound for Besicovitch line-configurations by borrowing sumset machinery",
     "Katz Tao Kakeya additive combinatorics measure dimension year"),
    # --- 22 ---
    ("Jean-Pierre Serre's 1954 Fields Medal recognised his sheaf-cohomological reworking of Leray's earlier spectral-sequence machinery and set the stage for later French algebraic geometry.", "milestone", "knowledge", False,
     [("Jean-Pierre Serre", "person"), ("1954", "date"), ("Fields Medal", "event"), ("sheaf-cohomological reworking", "concept"), ("Leray's earlier spectral-sequence machinery", "concept")],
     [("sheaf-cohomological reworking", "Jean-Pierre Serre", "AUTHORED_BY"), ("sheaf-cohomological reworking", "Leray's earlier spectral-sequence machinery", "IMPROVES_ON")],
     "which mid-twentieth-century French mathematician was honoured at the Amsterdam ICM for recasting Leray's filtration machinery in sheaf form",
     "Serre Fields Medal sheaf cohomology Leray spectral sequence year"),
    # --- 23 ---
    ("Maryam Mirzakhani's 2014 Fields Medal citation singled out her thesis work on moduli spaces of Riemann surfaces and the Weil-Petersson volume recursions.", "milestone", "knowledge", False,
     [("Maryam Mirzakhani", "person"), ("2014", "date"), ("Fields Medal", "event"), ("moduli spaces of Riemann surfaces", "concept"), ("Weil-Petersson volume recursions", "concept")],
     [("Weil-Petersson volume recursions", "Maryam Mirzakhani", "AUTHORED_BY")],
     "which Iranian-born mathematician was the first woman cited at Seoul for hyperbolic-surface moduli and volume recursions",
     "Mirzakhani Fields Medal Weil Petersson recursion moduli Riemann year"),
    # --- 24 ---
    ("The 2018 Abel Prize awarded to Robert Langlands recognised the Langlands programme as a unifying vision connecting number theory, representation theory, and automorphic forms.", "milestone", "knowledge", False,
     [("2018", "date"), ("Abel Prize", "event"), ("Robert Langlands", "person"), ("Langlands programme", "theory"), ("automorphic forms", "concept")],
     [("Langlands programme", "Robert Langlands", "AUTHORED_BY")],
     "which 2018 Abel Prize recognised the unifying Langlands programme",
     "Abel Prize Langlands programme automorphic forms unifying year"),
    # --- 25 ---
    ("Ngo Bao Chau's 2008 proof of the fundamental lemma for Lie algebras, published in Publications de l'IHES, clinched a long-standing piece of the Langlands programme.", "milestone", "knowledge", False,
     [("Ngo Bao Chau", "person"), ("2008", "date"), ("fundamental lemma", "concept"), ("Lie algebras", "concept"), ("Publications de l'IHES", "publication"), ("Langlands programme", "theory")],
     [("fundamental lemma", "Ngo Bao Chau", "AUTHORED_BY")],
     "which Vietnamese-French researcher clinched a decades-old piece of Langlands by settling orbital-integral identities over unitary groups",
     "Ngo fundamental lemma Lie algebras IHES Langlands year"),
    # --- 26 ---
    ("Manjul Bhargava's 2004 Annals of Mathematics series on higher composition laws generalised Gauss's cubic and quartic composition and won him the 2014 Fields Medal.", "milestone", "knowledge", False,
     [("Manjul Bhargava", "person"), ("2004", "date"), ("Annals of Mathematics", "publication"), ("higher composition laws", "concept"), ("Gauss's cubic and quartic composition", "concept"), ("Fields Medal", "event")],
     [("higher composition laws", "Manjul Bhargava", "AUTHORED_BY"), ("higher composition laws", "Gauss's cubic and quartic composition", "IMPROVES_ON")],
     "which Princeton number theorist generalised Gaussian cubic-quartic identities in a four-paper series early in the 2000s",
     "Bhargava higher composition laws Annals Gauss Fields year"),
    # --- 27 ---
    ("Peter Scholze's 2012 Bonn dissertation introduced perfectoid spaces and reframed p-adic Hodge theory, a contribution recognised by the 2018 Fields Medal.", "milestone", "knowledge", False,
     [("Peter Scholze", "person"), ("2012", "date"), ("Bonn", "place"), ("perfectoid spaces", "concept"), ("p-adic Hodge theory", "field"), ("Fields Medal", "event")],
     [("perfectoid spaces", "Peter Scholze", "AUTHORED_BY"), ("perfectoid spaces", "p-adic Hodge theory", "IMPROVES_ON")],
     "which young German mathematician's doctoral work introduced tilting equivalences that reshaped the p-adic side of arithmetic geometry",
     "Scholze perfectoid p adic Hodge Bonn dissertation Fields year"),
    # --- 28 ---
    ("John Tate's 1950 Princeton thesis recast Hecke L-functions through adelic harmonic analysis and seeded much of modern automorphic theory.", "reference", "knowledge", False,
     [("John Tate", "person"), ("1950", "date"), ("Princeton", "place"), ("Hecke L-functions", "concept"), ("adelic harmonic analysis", "method"), ("automorphic theory", "field")],
     [("Hecke L-functions", "John Tate", "AUTHORED_BY")],
     "which mid-century doctoral work rewrote classical Dirichlet-series analysis in the language of idele-class characters",
     "Tate thesis Hecke L functions adeles Princeton year harmonic"),
    # --- 29 ---
    ("Kenkichi Iwasawa's 1959 theory of Zp-extensions inaugurated Iwasawa theory and tied arithmetic of cyclotomic fields to characteristic-zero power-series rings.", "milestone", "knowledge", False,
     [("Kenkichi Iwasawa", "person"), ("1959", "date"), ("Zp-extensions", "concept"), ("Iwasawa theory", "field"), ("cyclotomic fields", "concept")],
     [("Iwasawa theory", "Kenkichi Iwasawa", "AUTHORED_BY")],
     "which Japanese algebraist seeded the programme tying roots-of-unity towers to characteristic-zero power-series rings",
     "Iwasawa Zp extensions cyclotomic fields theory year founding"),
    # --- 30 ---
    ("Barry Mazur's 1977 IHES paper classifying torsion subgroups of rational elliptic curves produced the celebrated Mazur torsion theorem.", "milestone", "knowledge", False,
     [("Barry Mazur", "person"), ("1977", "date"), ("IHES", "organization"), ("torsion subgroups", "concept"), ("rational elliptic curves", "concept"), ("Mazur torsion theorem", "concept")],
     [("Mazur torsion theorem", "Barry Mazur", "AUTHORED_BY")],
     "which Harvard number-theorist cut down possible finite-order points on elliptic curves over Q in the late 1970s",
     "Mazur torsion theorem rational elliptic curves IHES year"),
    # --- 31 ---
    ("Goro Shimura's 1971 book Introduction to the Arithmetic Theory of Automorphic Functions, issued by Princeton University Press, gave modular forms their definitive graduate treatment.", "reference", "knowledge", False,
     [("Goro Shimura", "person"), ("1971", "date"), ("Introduction to the Arithmetic Theory of Automorphic Functions", "publication"), ("Princeton University Press", "organization"), ("modular forms", "concept")],
     [("Introduction to the Arithmetic Theory of Automorphic Functions", "Goro Shimura", "AUTHORED_BY")],
     "which 1971 Princeton book set the standard graduate treatment of modular forms",
     "Shimura arithmetic automorphic modular forms Princeton textbook year"),
    # --- 32 ---
    ("Michael Atiyah and Isadore Singer's 1963 index theorem, announced at the Bulletin of the American Mathematical Society, linked elliptic operator indices to topological invariants.", "milestone", "knowledge", False,
     [("Michael Atiyah", "person"), ("Isadore Singer", "person"), ("1963", "date"), ("index theorem", "concept"), ("Bulletin of the American Mathematical Society", "publication"), ("topological invariants", "concept")],
     [("index theorem", "Michael Atiyah", "AUTHORED_BY")],
     "whose 1963 Bulletin announcement tied elliptic operator indices to topological invariants",
     "Atiyah Singer index theorem Bulletin elliptic topological year"),
    # --- 33 ---
    ("Simon Donaldson's 1983 Journal of Differential Geometry paper on gauge-theoretic invariants revealed exotic smooth structures on four-dimensional Euclidean space and superseded purely topological four-manifold arguments.", "milestone", "knowledge", False,
     [("Simon Donaldson", "person"), ("1983", "date"), ("Journal of Differential Geometry", "publication"), ("gauge-theoretic invariants", "concept"), ("exotic smooth structures", "concept"), ("purely topological four-manifold arguments", "concept")],
     [("gauge-theoretic invariants", "Simon Donaldson", "AUTHORED_BY"), ("gauge-theoretic invariants", "purely topological four-manifold arguments", "IMPROVES_ON")],
     "whose 1983 JDG paper used gauge theory to expose exotic four-dimensional smooth structures",
     "Donaldson gauge theory four manifold exotic JDG year"),
    # --- 34. noise ---
    ("Hmm, the referee's query about the second cohomology class may need a cleaner counterexample than the one in my draft.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Michael Freedman's 1982 Journal of Differential Geometry paper classified topological four-manifolds and settled the topological Poincare conjecture in dimension four.", "milestone", "knowledge", False,
     [("Michael Freedman", "person"), ("1982", "date"), ("Journal of Differential Geometry", "publication"), ("topological four-manifolds", "concept"), ("topological Poincare conjecture", "concept")],
     [("topological Poincare conjecture", "Michael Freedman", "AUTHORED_BY")],
     "who classified closed simply-connected topological four-manifolds early in the 1980s using Casson handles",
     "Freedman topological four manifolds Poincare JDG dimension four year"),
    # --- 36 ---
    ("Stephen Smale's 1961 Annals paper proved the h-cobordism theorem and the higher-dimensional Poincare conjecture for dimensions at least five.", "milestone", "knowledge", False,
     [("Stephen Smale", "person"), ("1961", "date"), ("Annals", "publication"), ("h-cobordism theorem", "concept"), ("higher-dimensional Poincare conjecture", "concept")],
     [("h-cobordism theorem", "Stephen Smale", "AUTHORED_BY")],
     "who settled the simply-connected cobordism statement and thus Poincare's spherical characterisation in five or more dimensions",
     "Smale h cobordism Poincare higher dimension Annals year"),
    # --- 37 ---
    ("Timothy Gowers's 1998 proof of Szemeredi's theorem using higher Fourier analysis appeared in Geometric and Functional Analysis and earned him the 1998 Fields Medal.", "milestone", "knowledge", False,
     [("Timothy Gowers", "person"), ("1998", "date"), ("Szemeredi's theorem", "concept"), ("higher Fourier analysis", "method"), ("Geometric and Functional Analysis", "publication"), ("Fields Medal", "event")],
     [("Szemeredi's theorem", "Timothy Gowers", "AUTHORED_BY"), ("higher Fourier analysis", "Szemeredi's theorem", "BUILDS_ON")],
     "which British combinatorialist recovered Endre's density result through a new Gowers-norm apparatus",
     "Gowers Szemeredi higher Fourier GAFA Fields Medal year"),
    # --- 38 ---
    ("Hillel Furstenberg's 1977 ergodic-theoretic proof of Szemeredi's theorem, published in Journal d'Analyse Mathematique, reframed the combinatorial statement as a statement about measure-preserving systems.", "milestone", "knowledge", False,
     [("Hillel Furstenberg", "person"), ("1977", "date"), ("Szemeredi's theorem", "concept"), ("Journal d'Analyse Mathematique", "publication"), ("measure-preserving systems", "concept")],
     [("Szemeredi's theorem", "Hillel Furstenberg", "AUTHORED_BY")],
     "whose 1977 ergodic-theoretic proof of Szemeredi's theorem reframed it as a measure-preserving statement",
     "Furstenberg Szemeredi ergodic measure preserving Journal Analyse year"),
    # --- 39 ---
    ("Jean Bourgain's 1989 Annals paper on pointwise ergodic theorems along polynomial subsequences opened harmonic-analytic ergodic theory as a programme.", "reference", "knowledge", False,
     [("Jean Bourgain", "person"), ("1989", "date"), ("Annals", "publication"), ("pointwise ergodic theorems", "concept"), ("polynomial subsequences", "concept"), ("harmonic-analytic ergodic theory", "field")],
     [("pointwise ergodic theorems", "Jean Bourgain", "AUTHORED_BY")],
     "whose 1989 Annals paper launched polynomial-subsequence pointwise ergodic theorems",
     "Bourgain polynomial ergodic Annals harmonic analytic year"),
    # --- 40 ---
    ("The Fields Medal, first awarded in 1936 at the Oslo ICM, recognises outstanding mathematicians under forty and is administered by the International Mathematical Union.", "fact", "knowledge", False,
     [("Fields Medal", "event"), ("1936", "date"), ("Oslo", "place"), ("ICM", "event"), ("International Mathematical Union", "organization")],
     [],
     "which award recognises mathematicians under forty and was first given at the 1936 Oslo ICM",
     "Fields Medal Oslo ICM forty IMU award founding year"),
    # --- 41 ---
    ("The Abel Prize, inaugurated in 2003 by the Norwegian Academy of Science and Letters, was modelled on the Nobel Prize to honour lifetime mathematical achievement.", "fact", "knowledge", False,
     [("Abel Prize", "event"), ("2003", "date"), ("Norwegian Academy of Science and Letters", "organization"), ("Nobel Prize", "event")],
     [],
     "which 2003 prize from the Norwegian Academy honours lifetime mathematical achievement",
     "Abel Prize Norwegian Academy lifetime achievement Nobel year"),
    # --- 42 ---
    ("Acta Mathematica, founded by Gosta Mittag-Leffler in 1882 and published by Institut Mittag-Leffler, retains a selective single-volume-per-year profile.", "reference", "knowledge", False,
     [("Acta Mathematica", "publication"), ("Gosta Mittag-Leffler", "person"), ("1882", "date"), ("Institut Mittag-Leffler", "organization")],
     [("Acta Mathematica", "Gosta Mittag-Leffler", "AUTHORED_BY")],
     "which 1882 Swedish journal founded by Mittag-Leffler still publishes selectively",
     "Acta Mathematica Mittag Leffler Swedish journal founding year"),
    # --- 43 ---
    ("The Annals of Mathematics, edited from Princeton University, is published bimonthly through Princeton University Press and the Institute for Advanced Study.", "fact", "knowledge", False,
     [("Annals of Mathematics", "publication"), ("Princeton University", "organization"), ("Princeton University Press", "organization"), ("Institute for Advanced Study", "organization")],
     [],
     "which bimonthly journal is co-edited from Princeton and the IAS",
     "Annals Mathematics Princeton IAS bimonthly journal editorship"),
    # --- 44 ---
    ("Inventiones Mathematicae, launched by Springer in 1966, quickly became one of the flagship European venues for research in pure mathematics.", "fact", "knowledge", False,
     [("Inventiones Mathematicae", "publication"), ("Springer", "organization"), ("1966", "date")],
     [],
     "which mid-1960s West German serial became a top-tier venue for continental pure-mathematics research",
     "Inventiones Springer European journal founding flagship year"),
    # --- 45 ---
    ("Grothendieck's 1957 Tohoku paper introduced abelian categories and derived functors, superseding the ad hoc spectral-sequence calculations of the Cartan-Eilenberg era.", "milestone", "knowledge", False,
     [("Grothendieck", "person"), ("1957", "date"), ("Tohoku", "publication"), ("abelian categories", "concept"), ("derived functors", "concept"), ("ad hoc spectral-sequence calculations", "concept")],
     [("abelian categories", "Grothendieck", "AUTHORED_BY"), ("abelian categories", "ad hoc spectral-sequence calculations", "REPLACES")],
     "which late-1950s Japanese journal paper replaced Cartan-Eilenberg bookkeeping with a categorical foundation for homology",
     "Sendai homological algebra foundations paper Japanese serial postwar"),
    # --- 46 ---
    ("Daniel Quillen's 1967 Springer Lecture Notes on homotopical algebra axiomatised model categories and improves on earlier simplicial-set-only treatments of homotopy theory.", "reference", "knowledge", False,
     [("Daniel Quillen", "person"), ("1967", "date"), ("Springer Lecture Notes", "publication"), ("homotopical algebra", "field"), ("model categories", "concept"), ("simplicial-set-only treatments", "concept")],
     [("model categories", "Daniel Quillen", "AUTHORED_BY"), ("model categories", "simplicial-set-only treatments", "IMPROVES_ON")],
     "whose 1967 Lecture Notes axiomatised model categories within homotopical algebra",
     "Quillen homotopical algebra model categories Springer Lecture Notes year"),
    # --- 47 ---
    ("William Lawvere's 1964 elementary theory of the category of sets offered a categorical alternative to ZFC-style set theory.", "architecture", "knowledge", False,
     [("William Lawvere", "person"), ("1964", "date"), ("elementary theory of the category of sets", "theory"), ("ZFC-style set theory", "concept")],
     [("elementary theory of the category of sets", "William Lawvere", "AUTHORED_BY"), ("elementary theory of the category of sets", "ZFC-style set theory", "IMPROVES_ON")],
     "whose mid-1960s axiomatisation used a topos-style framing to replace Zermelo-Fraenkel foundations",
     "Buffalo axiomatics structural foundations topos alternative 1960s"),
    # --- 48 ---
    ("Saharon Shelah's 1978 classification theory, published by North-Holland, sorted first-order theories by stability properties and reshaped model theory.", "reference", "knowledge", False,
     [("Saharon Shelah", "person"), ("1978", "date"), ("classification theory", "theory"), ("North-Holland", "organization"), ("first-order theories", "concept"), ("model theory", "field")],
     [("classification theory", "Saharon Shelah", "AUTHORED_BY")],
     "which Israeli logician's late-1970s Dutch-published monograph organised complete theories by their stability spectrum",
     "Shelah classification stability first order model theory North Holland year"),
    # --- 49 ---
    ("Vladimir Voevodsky's 2002 Fields Medal recognised his construction of motivic cohomology and the resolution of the Milnor conjecture on K-theory and Galois cohomology.", "milestone", "knowledge", False,
     [("Vladimir Voevodsky", "person"), ("2002", "date"), ("Fields Medal", "event"), ("motivic cohomology", "concept"), ("Milnor conjecture", "concept"), ("K-theory", "field"), ("Galois cohomology", "field")],
     [("motivic cohomology", "Vladimir Voevodsky", "AUTHORED_BY"), ("Milnor conjecture", "Vladimir Voevodsky", "AUTHORED_BY")],
     "whose 2002 Fields Medal honoured motivic cohomology and the Milnor conjecture",
     "Voevodsky motivic cohomology Milnor conjecture Fields Medal year"),
    # --- 50 ---
    ("Yitang Zhang's 2014 Annals of Mathematics paper establishing bounded gaps between primes broke a long-standing analytic-number-theory barrier and improves on sieve-theoretic bounds from the 2000s.", "milestone", "knowledge", False,
     [("Yitang Zhang", "person"), ("2014", "date"), ("Annals of Mathematics", "publication"), ("bounded gaps between primes", "concept"), ("sieve-theoretic bounds", "concept")],
     [("bounded gaps between primes", "Yitang Zhang", "AUTHORED_BY"), ("bounded gaps between primes", "sieve-theoretic bounds", "IMPROVES_ON")],
     "whose 2014 Annals paper proved bounded gaps between primes",
     "Zhang bounded gaps primes Annals analytic number theory year"),
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
