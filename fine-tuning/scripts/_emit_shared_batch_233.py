"""One-off emitter for shared-base batch-233 — knowledge domain (history of mathematics and seminal results).

Writes 50 rows to data/v2/shared/batch_233.tmp.jsonl with ids shared-11601..11650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_233.tmp.jsonl"
ID_OFFSET = 11600

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Around 300 BCE in Alexandria, Euclid compiled the Elements, a thirteen-book axiomatic treatment of plane geometry and number theory that framed mathematical proof for the next two millennia.", "milestone", "knowledge", False,
     [("Euclid", "person"), ("Alexandria", "place"), ("Elements", "publication"), ("plane geometry", "concept")],
     [("Elements", "Euclid", "AUTHORED_BY"), ("Elements", "plane geometry", "APPLIES_TO")],
     "who wrote the thirteen-book axiomatic geometry treatise in Alexandria around three hundred BCE",
     "euclid elements alexandria thirteen book axiomatic geometry proof"),
    # --- 2 ---
    ("Archimedes of Syracuse pinned pi between 223/71 and 22/7 by inscribing and circumscribing 96-gons around a circle, a method of exhaustion that prefigured integral calculus by almost two thousand years.", "fact", "knowledge", False,
     [("Archimedes", "person"), ("Syracuse", "place"), ("pi", "concept"), ("method of exhaustion", "method"), ("integral calculus", "concept")],
     [("Archimedes", "method of exhaustion", "USES"), ("integral calculus", "method of exhaustion", "BUILDS_ON")],
     "which Syracusan mathematician bounded pi using 96-sided polygons and what later technique did his method anticipate",
     "archimedes syracuse pi 96 gon exhaustion bound integral calculus"),
    # --- 3 ---
    ("In ninth-century Baghdad, Al-Khwarizmi wrote Al-jabr wa'l-muqabala, a systematic treatise on solving linear and quadratic equations; the word algebra descends directly from its title.", "milestone", "knowledge", False,
     [("Al-Khwarizmi", "person"), ("Baghdad", "place"), ("Al-jabr", "publication"), ("quadratic equations", "concept"), ("algebra", "concept")],
     [("Al-jabr", "Al-Khwarizmi", "AUTHORED_BY"), ("algebra", "Al-jabr", "BUILDS_ON")],
     "which Baghdad scholar produced the ninth-century treatise whose title became the word algebra",
     "al khwarizmi baghdad al jabr quadratic linear equation algebra origin"),
    # --- 4 ---
    ("Fibonacci's 1202 Liber Abaci introduced Hindu-Arabic numerals to European merchants and showcased the recurrence F(n) = F(n-1) + F(n-2) through the rabbit-population problem.", "fact", "knowledge", False,
     [("Fibonacci", "person"), ("Liber Abaci", "publication"), ("Hindu-Arabic numerals", "concept"), ("rabbit-population problem", "concept")],
     [("Liber Abaci", "Fibonacci", "AUTHORED_BY"), ("Liber Abaci", "Hindu-Arabic numerals", "APPLIES_TO")],
     "which 1202 book carried Hindu-Arabic numerals into European commerce and popularised the rabbit recurrence",
     "fibonacci liber abaci 1202 hindu arabic numeral rabbit recurrence"),
    # --- 5 ---
    ("Cardano's 1545 Ars Magna published the cubic formula that Tartaglia had shown him under oath of secrecy; the breach is still the standard anecdote for priority disputes in mathematics.", "problem", "knowledge", False,
     [("Cardano", "person"), ("Ars Magna", "publication"), ("Tartaglia", "person"), ("cubic formula", "concept")],
     [("Ars Magna", "Cardano", "AUTHORED_BY"), ("Ars Magna", "cubic formula", "APPLIES_TO")],
     "which 1545 publication broke a vow of secrecy to print the cubic formula and who had shared it privately",
     "cardano ars magna 1545 tartaglia cubic formula secrecy priority"),
    # --- 6 ---
    ("Descartes appended La Géométrie to his 1637 Discours de la méthode, fusing algebra and geometry through coordinates and launching what we now call analytic geometry.", "architecture", "knowledge", False,
     [("Descartes", "person"), ("La Géométrie", "publication"), ("Discours de la méthode", "publication"), ("analytic geometry", "concept"), ("coordinates", "concept")],
     [("La Géométrie", "Descartes", "AUTHORED_BY"), ("analytic geometry", "La Géométrie", "BUILDS_ON")],
     "which 1637 appendix welded algebra to geometry via coordinates and founded the analytic approach",
     "descartes la geometrie 1637 discours methode coordinate analytic"),
    # --- 7 ---
    ("Newton's 1687 Principia Mathematica derived Kepler's laws from the inverse-square law of gravitation using a synthetic geometric proof style rather than the fluxional notation he had developed privately.", "milestone", "knowledge", False,
     [("Newton", "person"), ("Principia Mathematica", "publication"), ("Kepler", "person"), ("inverse-square law", "concept"), ("fluxional notation", "concept")],
     [("Principia Mathematica", "Newton", "AUTHORED_BY"), ("Principia Mathematica", "inverse-square law", "APPLIES_TO")],
     "which 1687 treatise derived Kepler's laws from gravity using geometric rather than fluxional proofs",
     "newton principia 1687 kepler inverse square gravitation fluxion geometric"),
    # --- 8 ---
    ("Leibniz's dy/dx and the integral sign he introduced in 1684 proved more flexible than Newton's dotted fluxions, which is why continental Europe outpaced Britain in analysis through the eighteenth century.", "decision", "knowledge", False,
     [("Leibniz", "person"), ("dy/dx", "concept"), ("integral sign", "concept"), ("Newton", "person"), ("fluxions", "concept")],
     [("dy/dx", "Leibniz", "AUTHORED_BY"), ("dy/dx", "fluxions", "REPLACES")],
     "why did continental analysis outrun the British school after 1684 over notation choices for calculus",
     "leibniz dy dx integral sign 1684 newton fluxion notation analysis"),
    # --- 9 ---
    ("Euler's 1748 Introductio in Analysin Infinitorum unified functions, series, and exponentials around e^{ix} = cos x + i sin x, giving modern analysis a vocabulary it still uses.", "reference", "knowledge", False,
     [("Euler", "person"), ("Introductio in Analysin Infinitorum", "publication"), ("e^{ix}", "concept"), ("series", "concept")],
     [("Introductio in Analysin Infinitorum", "Euler", "AUTHORED_BY")],
     "which 1748 Euler treatise built modern analysis around the complex exponential identity",
     "euler introductio 1748 analysin infinitorum eix series exponential"),
    # --- 10. noise ---
    ("The upstairs archive's dehumidifier started wheezing on rainy mornings and the facilities log has five identical tickets filed against it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Gauss's 1801 Disquisitiones Arithmeticae compiled congruences, quadratic reciprocity, and the theory of forms into a single book that defined number theory as an autonomous discipline.", "decision", "knowledge", False,
     [("Gauss", "person"), ("Disquisitiones Arithmeticae", "publication"), ("quadratic reciprocity", "concept"), ("number theory", "concept"), ("congruences", "concept")],
     [("Disquisitiones Arithmeticae", "Gauss", "AUTHORED_BY"), ("number theory", "Disquisitiones Arithmeticae", "BUILDS_ON")],
     "which 1801 book turned number theory into an autonomous field around reciprocity and congruences",
     "gauss disquisitiones arithmeticae 1801 quadratic reciprocity congruence"),
    # --- 12 ---
    ("Cauchy's 1821 Cours d'Analyse insisted on epsilon-delta rigour for limits and continuity, displacing the looser infinitesimal prose that Euler and Lagrange had been content with.", "decision", "knowledge", False,
     [("Cauchy", "person"), ("Cours d'Analyse", "publication"), ("epsilon-delta", "concept"), ("Euler", "person"), ("Lagrange", "person")],
     [("Cours d'Analyse", "Cauchy", "AUTHORED_BY"), ("epsilon-delta", "Cours d'Analyse", "APPLIES_TO")],
     "which 1821 textbook forced epsilon-delta rigour onto analysis and whose looser style did it push aside",
     "cauchy cours analyse 1821 epsilon delta rigour limit continuity"),
    # --- 13 ---
    ("Riemann's 1859 paper on the prime-counting function conjectured that every non-trivial zero of the zeta function lies on the critical line Re(s) = 1/2; the Riemann hypothesis remains the most famous open problem in pure mathematics.", "problem", "knowledge", False,
     [("Riemann", "person"), ("zeta function", "concept"), ("critical line", "concept"), ("Riemann hypothesis", "concept"), ("prime-counting function", "concept")],
     [("Riemann hypothesis", "Riemann", "AUTHORED_BY"), ("Riemann hypothesis", "zeta function", "APPLIES_TO")],
     "which 1859 conjecture pins the non-trivial zeros of the zeta function to a single vertical line",
     "riemann 1859 zeta critical line hypothesis prime counting zero"),
    # --- 14 ---
    ("Cantor proved in 1874 that the reals are uncountable via the diagonal argument, founding set theory and forcing mathematics to admit actual infinities of distinct sizes.", "fact", "knowledge", False,
     [("Cantor", "person"), ("diagonal argument", "method"), ("set theory", "concept"), ("reals", "concept")],
     [("Cantor", "diagonal argument", "USES"), ("set theory", "diagonal argument", "BUILDS_ON")],
     "which 1874 argument established uncountability of the reals and founded set theory",
     "cantor 1874 diagonal uncountable real set theory infinity"),
    # --- 15 ---
    ("Dedekind's 1872 Stetigkeit und irrationale Zahlen constructed the real line as Dedekind cuts in the rationals, giving analysis a foundation that did not lean on geometric intuition about a continuous line.", "architecture", "knowledge", False,
     [("Dedekind", "person"), ("Stetigkeit und irrationale Zahlen", "publication"), ("Dedekind cuts", "concept"), ("rationals", "concept")],
     [("Stetigkeit und irrationale Zahlen", "Dedekind", "AUTHORED_BY"), ("Dedekind cuts", "rationals", "APPLIES_TO")],
     "how did Dedekind build the reals from rationals without borrowing from geometric continuum intuition",
     "dedekind 1872 stetigkeit cut rational real foundation analysis"),
    # --- 16 ---
    ("Hilbert's 1900 Paris address listed 23 problems that set the agenda for twentieth-century mathematics; his broader Hilbert program sought to ground all mathematics in a consistent finite axiom system.", "architecture", "knowledge", False,
     [("Hilbert", "person"), ("Hilbert program", "concept"), ("23 problems", "concept"), ("Paris address", "event")],
     [("Hilbert program", "Hilbert", "AUTHORED_BY"), ("23 problems", "Hilbert", "AUTHORED_BY")],
     "which 1900 address and which broader formalist agenda shaped twentieth-century mathematical research",
     "hilbert 1900 paris 23 problem program formalist axiom consistent"),
    # --- 17 ---
    ("Russell and Whitehead spent a decade producing Principia Mathematica between 1910 and 1913, a derivation of arithmetic from logic rooted in type theory that famously takes several hundred pages to prove 1 + 1 = 2.", "reference", "knowledge", False,
     [("Russell", "person"), ("Whitehead", "person"), ("Principia Mathematica", "publication"), ("type theory", "concept"), ("arithmetic", "concept")],
     [("Principia Mathematica", "Russell", "AUTHORED_BY"), ("Principia Mathematica", "Whitehead", "AUTHORED_BY")],
     "which 1910 to 1913 work derived arithmetic from logic using type theory and took hundreds of pages for 1 + 1 = 2",
     "russell whitehead principia mathematica 1910 type theory arithmetic"),
    # --- 18 ---
    ("Gödel's 1931 incompleteness theorems proved that any consistent system strong enough to encode arithmetic contains true statements it cannot prove, decisively closing off the Hilbert program and its formalist dream.", "problem", "knowledge", False,
     [("Gödel", "person"), ("incompleteness theorems", "concept"), ("Hilbert program", "concept"), ("arithmetic", "concept")],
     [("incompleteness theorems", "Gödel", "AUTHORED_BY"), ("incompleteness theorems", "Hilbert program", "REPLACES")],
     "which 1931 results closed off the formalist dream by showing arithmetic systems are necessarily incomplete",
     "godel 1931 incompleteness consistent arithmetic hilbert formalist"),
    # --- 19 ---
    ("The Church-Turing thesis identifies the intuitive notion of effective computability with Turing machines and Church's lambda calculus; Kleene's 1943 survey made the equivalence the working definition.", "decision", "knowledge", False,
     [("Church-Turing thesis", "concept"), ("Turing machines", "concept"), ("lambda calculus", "concept"), ("Kleene", "person"), ("Church", "person")],
     [("Church-Turing thesis", "Turing machines", "APPLIES_TO"), ("Church-Turing thesis", "lambda calculus", "APPLIES_TO")],
     "which thesis tied the informal notion of effective computation to both Turing machines and the lambda calculus",
     "church turing thesis lambda calculus kleene 1943 computable"),
    # --- 20 ---
    ("Turing's 1936 paper reduced the Entscheidungsproblem to the halting problem and proved the latter undecidable by a clean diagonalisation over machine descriptions.", "milestone", "knowledge", False,
     [("Turing", "person"), ("halting problem", "concept"), ("Entscheidungsproblem", "concept"), ("diagonalisation", "method")],
     [("halting problem", "Turing", "AUTHORED_BY"), ("halting problem", "Entscheidungsproblem", "APPLIES_TO")],
     "whose 1936 work established undecidability of the halting problem via a diagonal argument on machines",
     "turing 1936 halting problem entscheidungs diagonal undecidable"),
    # --- 21 ---
    ("Cohen's 1963 forcing technique showed that the continuum hypothesis is independent of ZFC, completing Gödel's earlier consistency result and opening modern set theory to model-theoretic engineering.", "decision", "knowledge", False,
     [("Cohen", "person"), ("forcing", "method"), ("continuum hypothesis", "concept"), ("ZFC", "concept"), ("Gödel", "person")],
     [("forcing", "Cohen", "AUTHORED_BY"), ("forcing", "continuum hypothesis", "APPLIES_TO")],
     "which 1963 technique established independence of the continuum hypothesis from ZFC",
     "cohen forcing 1963 continuum hypothesis zfc independence godel"),
    # --- 22 ---
    ("The Bourbaki collective began publishing Éléments de mathématique in 1939, pushing an axiomatic structuralist presentation that reshaped postwar French mathematical pedagogy for several generations.", "architecture", "knowledge", False,
     [("Bourbaki", "person"), ("Éléments de mathématique", "publication"), ("structuralist", "concept"), ("axiomatic", "concept")],
     [("Éléments de mathématique", "Bourbaki", "AUTHORED_BY")],
     "which collective started a structuralist axiomatic series in 1939 that reshaped French mathematical teaching",
     "bourbaki elements mathematique 1939 structuralist axiomatic french"),
    # --- 23 ---
    ("The Atiyah-Singer index theorem proved in 1963 equates the analytic index of an elliptic operator with a topological index computed from characteristic classes, tying analysis, topology, and geometry into one bridge.", "architecture", "knowledge", False,
     [("Atiyah", "person"), ("Singer", "person"), ("index theorem", "concept"), ("elliptic operator", "concept"), ("characteristic classes", "concept")],
     [("index theorem", "Atiyah", "AUTHORED_BY"), ("index theorem", "Singer", "AUTHORED_BY")],
     "which 1963 theorem equates the analytic and topological indices of an elliptic operator",
     "atiyah singer index theorem 1963 elliptic operator characteristic"),
    # --- 24 ---
    ("Perelman's 2002 to 2003 preprints used Hamilton's Ricci flow with surgery to settle the Poincaré conjecture; he declined both the Fields Medal and the Clay Millennium Prize.", "milestone", "knowledge", False,
     [("Perelman", "person"), ("Ricci flow", "method"), ("Poincaré conjecture", "concept"), ("Fields Medal", "concept"), ("Clay Millennium Prize", "concept")],
     [("Poincaré conjecture", "Perelman", "AUTHORED_BY"), ("Ricci flow", "Poincaré conjecture", "APPLIES_TO")],
     "which mathematician used Ricci flow with surgery around 2003 to resolve the Poincaré conjecture",
     "perelman ricci flow surgery poincare 2003 fields clay decline"),
    # --- 25 ---
    ("Wiles's 1995 proof of Fermat's Last Theorem proceeded via the modularity theorem for semistable elliptic curves, closing a 358-year-old question that Fermat had scribbled in the margin of Diophantus.", "milestone", "knowledge", False,
     [("Wiles", "person"), ("Fermat's Last Theorem", "concept"), ("modularity theorem", "concept"), ("elliptic curves", "concept"), ("Fermat", "person")],
     [("Fermat's Last Theorem", "Wiles", "AUTHORED_BY"), ("modularity theorem", "Fermat's Last Theorem", "APPLIES_TO")],
     "which 1995 proof settled a 358-year-old margin note by routing through modular elliptic curves",
     "wiles 1995 fermat last theorem modularity elliptic semistable"),
    # --- 26 ---
    ("The Langlands program posits a web of correspondences between Galois representations and automorphic forms; it organises large swathes of modern number theory and representation theory under one umbrella.", "architecture", "knowledge", False,
     [("Langlands program", "concept"), ("Galois representations", "concept"), ("automorphic forms", "concept"), ("number theory", "concept"), ("representation theory", "concept")],
     [("Langlands program", "Galois representations", "APPLIES_TO"), ("Langlands program", "automorphic forms", "APPLIES_TO")],
     "which grand conjectural web links Galois representations to automorphic forms across number theory",
     "langlands program galois automorphic representation number theory"),
    # --- 27 ---
    ("Terence Tao's 2004 Green-Tao theorem proved that the primes contain arbitrarily long arithmetic progressions, an additive-combinatorial result that leans on Szemerédi's theorem as its main lever.", "fact", "knowledge", False,
     [("Terence Tao", "person"), ("Green-Tao theorem", "concept"), ("primes", "concept"), ("Szemerédi's theorem", "concept")],
     [("Green-Tao theorem", "Terence Tao", "AUTHORED_BY"), ("Szemerédi's theorem", "Green-Tao theorem", "APPLIES_TO")],
     "which 2004 theorem proved arithmetic progressions of every length sit inside the primes",
     "tao green tao 2004 prime arithmetic progression szemeredi"),
    # --- 28 ---
    ("Euclid's parallel postulate quietly refused to follow from the first four axioms; Lobachevsky and Bolyai independently built hyperbolic geometry in the 1820s by denying it and finding no contradiction.", "decision", "knowledge", False,
     [("Euclid", "person"), ("parallel postulate", "concept"), ("Lobachevsky", "person"), ("Bolyai", "person"), ("hyperbolic geometry", "concept")],
     [("hyperbolic geometry", "Lobachevsky", "AUTHORED_BY"), ("hyperbolic geometry", "Bolyai", "AUTHORED_BY")],
     "which two 1820s mathematicians independently discovered hyperbolic geometry by rejecting the parallel postulate",
     "lobachevsky bolyai 1820 parallel postulate hyperbolic geometry"),
    # --- 29 ---
    ("Galois died in an 1832 duel at twenty, but the letter he wrote the previous night sketched Galois theory itself: the correspondence between field extensions and permutation groups that today bears his name.", "fact", "knowledge", False,
     [("Galois", "person"), ("field extensions", "concept"), ("permutation groups", "concept"), ("Galois theory", "concept")],
     [("Galois theory", "Galois", "AUTHORED_BY"), ("Galois theory", "field extensions", "APPLIES_TO")],
     "which twenty-year-old wrote the 1832 letter the night before his duel that founded Galois theory",
     "galois 1832 duel letter field extension permutation group theory"),
    # --- 30 ---
    ("Abel's 1824 proof that the general quintic has no solution in radicals killed three centuries of effort from Cardano's Italian school onward, even though Abel died of tuberculosis before he was widely read.", "decision", "knowledge", False,
     [("Abel", "person"), ("quintic", "concept"), ("Cardano", "person"), ("radicals", "concept")],
     [("quintic", "Abel", "AUTHORED_BY"), ("quintic", "radicals", "APPLIES_TO")],
     "which 1824 result killed three centuries of effort to solve the quintic by radicals",
     "abel 1824 quintic radical solve cardano italian school tuberculosis"),
    # --- 31 ---
    ("In 1918 Noether published Noether's theorem, tying every differentiable symmetry of a physical action to a conserved quantity — a result that later became foundational for gauge theory in theoretical physics.", "fact", "knowledge", False,
     [("Noether", "person"), ("Noether's theorem", "concept"), ("symmetry", "concept"), ("gauge theory", "concept"), ("conserved quantity", "concept")],
     [("Noether's theorem", "Noether", "AUTHORED_BY"), ("gauge theory", "Noether's theorem", "BUILDS_ON")],
     "which 1918 theorem maps continuous symmetries of an action to conservation laws",
     "noether 1918 theorem symmetry conservation gauge physics action"),
    # --- 32 ---
    ("Poincaré's 1895 Analysis Situs invented the tools of algebraic topology — fundamental group, homology, Betti numbers — and posed the three-dimensional conjecture that would outlast him by a century.", "architecture", "knowledge", False,
     [("Poincaré", "person"), ("Analysis Situs", "publication"), ("algebraic topology", "concept"), ("fundamental group", "concept"), ("Betti numbers", "concept")],
     [("Analysis Situs", "Poincaré", "AUTHORED_BY"), ("algebraic topology", "Analysis Situs", "BUILDS_ON")],
     "which 1895 memoir by Poincaré invented the foundational tools of algebraic topology",
     "poincare 1895 analysis situs algebraic topology fundamental betti"),
    # --- 33. noise ---
    ("The number-theory seminar moved from room 114 to the fourth-floor lounge because the projector in 114 keeps dropping to a sickly green whenever HVAC cycles.", "fact", "noise", True, [], [], None, None),
    # --- 34 ---
    ("Riemann's 1854 Habilitationsvortrag on the hypotheses underlying geometry introduced manifolds and the metric viewpoint that Einstein would lean on for general relativity six decades later.", "architecture", "knowledge", False,
     [("Riemann", "person"), ("Habilitationsvortrag", "publication"), ("manifolds", "concept"), ("Einstein", "person"), ("general relativity", "concept")],
     [("Habilitationsvortrag", "Riemann", "AUTHORED_BY"), ("general relativity", "manifolds", "BUILDS_ON")],
     "which 1854 Riemann lecture introduced manifolds that general relativity would later adopt",
     "riemann 1854 habilitation manifold geometry metric einstein relativity"),
    # --- 35 ---
    ("Grothendieck rebuilt algebraic geometry in the 1960s around schemes and the functor of points, a level of abstraction that the Séminaire de Géométrie Algébrique volumes made canonical for the next generation.", "decision", "knowledge", False,
     [("Grothendieck", "person"), ("schemes", "concept"), ("functor of points", "concept"), ("algebraic geometry", "concept"), ("Séminaire de Géométrie Algébrique", "publication")],
     [("schemes", "Grothendieck", "AUTHORED_BY"), ("algebraic geometry", "schemes", "BUILDS_ON")],
     "which 1960s rebuilding of algebraic geometry placed schemes and the functor of points at its centre",
     "grothendieck scheme functor points algebraic geometry sga 1960"),
    # --- 36 ---
    ("Erdős published roughly 1,500 papers with more than 500 collaborators; the Erdős number counting coauthorship distance is the folkloric tribute that grew out of the habit.", "architecture", "knowledge", False,
     [("Erdős", "person"), ("Erdős number", "concept"), ("coauthorship", "concept")],
     [("Erdős number", "Erdős", "AUTHORED_BY")],
     "which prolific twentieth-century mathematician is the origin point of the collaboration-distance number",
     "erdos 1500 paper 500 collaborator erdos number coauthor"),
    # --- 37 ---
    ("Hypatia of Alexandria headed the Neoplatonic school in the late fourth century and wrote commentaries on Diophantus's Arithmetica and Apollonius's Conics that kept Hellenistic mathematics alive for two more centuries.", "reference", "knowledge", False,
     [("Hypatia", "person"), ("Alexandria", "place"), ("Diophantus", "person"), ("Arithmetica", "publication"), ("Apollonius", "person")],
     [("Hypatia", "Arithmetica", "APPLIES_TO")],
     "which late-antique Alexandrian philosopher wrote commentaries that preserved Diophantus and Apollonius",
     "hypatia alexandria neoplatonic diophantus arithmetica apollonius"),
    # --- 38 ---
    ("Kovalevskaya's 1888 Prix Bordin result on the motion of a rigid body about a fixed point was the first major prize won by a woman in analytic mechanics; she had already been the first woman appointed to a full European chair.", "reference", "knowledge", False,
     [("Kovalevskaya", "person"), ("Prix Bordin", "concept"), ("rigid body", "concept"), ("analytic mechanics", "concept")],
     [("Prix Bordin", "Kovalevskaya", "AUTHORED_BY")],
     "which 1888 Prix Bordin-winning result on rigid-body motion belonged to the first woman to hold a European chair",
     "kovalevskaya 1888 prix bordin rigid body mechanics women chair"),
    # --- 39 ---
    ("Ramanujan arrived in Cambridge in 1914 with notebooks of unproved identities; his 1918 collaboration with Hardy on the partition function produced the asymptotic p(n) formula that opened modular forms to analytic methods.", "decision", "knowledge", False,
     [("Ramanujan", "person"), ("Hardy", "person"), ("partition function", "concept"), ("modular forms", "concept")],
     [("partition function", "Ramanujan", "AUTHORED_BY"), ("partition function", "Hardy", "AUTHORED_BY")],
     "which Hardy-Ramanujan collaboration gave the asymptotic formula for p(n) and linked partitions to modular forms",
     "ramanujan hardy 1918 partition asymptotic modular cambridge 1914"),
    # --- 40 ---
    ("Von Neumann's 1932 Mathematische Grundlagen der Quantenmechanik axiomatised quantum mechanics inside Hilbert space, and the same decade saw him sketch minimax and the Von Neumann architecture for computing.", "reference", "knowledge", False,
     [("Von Neumann", "person"), ("Mathematische Grundlagen der Quantenmechanik", "publication"), ("Hilbert space", "concept"), ("minimax", "concept"), ("Von Neumann architecture", "concept")],
     [("Mathematische Grundlagen der Quantenmechanik", "Von Neumann", "AUTHORED_BY"), ("Mathematische Grundlagen der Quantenmechanik", "Hilbert space", "APPLIES_TO")],
     "which 1932 treatise axiomatised quantum mechanics inside Hilbert space and who wrote it",
     "von neumann 1932 quantum hilbert minimax architecture grundlagen"),
    # --- 41 ---
    ("Nash's 1950 two-page thesis generalised Von Neumann's minimax to non-cooperative games via the Nash equilibrium, reshaping economics before he turned to geometric embeddings of Riemannian manifolds.", "decision", "knowledge", False,
     [("Nash", "person"), ("Nash equilibrium", "concept"), ("minimax", "concept"), ("Riemannian manifolds", "concept"), ("Von Neumann", "person")],
     [("Nash equilibrium", "Nash", "AUTHORED_BY"), ("Nash equilibrium", "minimax", "IMPROVES_ON")],
     "which 1950 two-page thesis generalised minimax to non-cooperative games and reshaped economics",
     "nash 1950 equilibrium minimax non cooperative riemannian embed"),
    # --- 42 ---
    ("Shannon's 1948 A Mathematical Theory of Communication defined entropy as the measure of information, gave the channel capacity formula, and essentially invented information theory in one paper.", "milestone", "knowledge", False,
     [("Shannon", "person"), ("A Mathematical Theory of Communication", "publication"), ("entropy", "concept"), ("channel capacity", "concept"), ("information theory", "concept")],
     [("A Mathematical Theory of Communication", "Shannon", "AUTHORED_BY"), ("information theory", "A Mathematical Theory of Communication", "BUILDS_ON")],
     "which 1948 paper defined information entropy and channel capacity in a single stroke",
     "shannon 1948 mathematical communication entropy channel capacity"),
    # --- 43 ---
    ("Kolmogorov's 1933 Grundbegriffe axiomatised probability on measurable spaces, displacing the frequentist prose that dominated before and finally lining probability up with the Lebesgue integral.", "decision", "knowledge", False,
     [("Kolmogorov", "person"), ("Grundbegriffe", "publication"), ("probability", "concept"), ("measurable spaces", "concept"), ("Lebesgue integral", "concept")],
     [("Grundbegriffe", "Kolmogorov", "AUTHORED_BY"), ("Grundbegriffe", "probability", "APPLIES_TO")],
     "which 1933 monograph axiomatised probability on measurable spaces and aligned it with Lebesgue integration",
     "kolmogorov 1933 grundbegriffe probability measure lebesgue axiom"),
    # --- 44 ---
    ("Weierstrass built the epsilon-delta style rigorously in his Berlin lectures of the 1860s and 1870s; his 1872 everywhere-continuous nowhere-differentiable function ended naive geometric intuition about continuity.", "fact", "knowledge", False,
     [("Weierstrass", "person"), ("epsilon-delta", "concept"), ("continuity", "concept"), ("Berlin", "place")],
     [("epsilon-delta", "Weierstrass", "AUTHORED_BY")],
     "which 1870s Berlin lecturer produced an everywhere-continuous nowhere-differentiable function that broke intuition",
     "weierstrass 1872 berlin epsilon delta continuous nowhere differentiable"),
    # --- 45 ---
    ("The Clay Mathematics Institute listed seven Millennium Prize Problems in 2000 at a million dollars each; only the Poincaré conjecture has been resolved so far, by Perelman between 2002 and 2003.", "reference", "knowledge", False,
     [("Clay Mathematics Institute", "organization"), ("Millennium Prize Problems", "concept"), ("Poincaré conjecture", "concept"), ("Perelman", "person")],
     [("Poincaré conjecture", "Perelman", "AUTHORED_BY"), ("Millennium Prize Problems", "Clay Mathematics Institute", "AUTHORED_BY")],
     "which institute listed seven million-dollar problems in 2000 and which one has been resolved",
     "clay mathematics 2000 millennium prize seven problem poincare"),
    # --- 46 ---
    ("Grothendieck's 1966 Fields Medal citation credited schemes, étale cohomology, and the Riemann-Roch-Grothendieck theorem; he boycotted the Moscow ceremony over political objections to the Soviet regime.", "decision", "knowledge", False,
     [("Grothendieck", "person"), ("Fields Medal", "concept"), ("étale cohomology", "concept"), ("Riemann-Roch-Grothendieck", "concept"), ("Moscow", "place")],
     [("étale cohomology", "Grothendieck", "AUTHORED_BY"), ("Riemann-Roch-Grothendieck", "Grothendieck", "AUTHORED_BY")],
     "which 1966 Fields Medalist boycotted the Moscow ceremony and what three achievements did the citation highlight",
     "grothendieck 1966 fields medal etale cohomology riemann roch moscow"),
    # --- 47 ---
    ("For serious expository study Terence Tao prefers his Analysis I and Analysis II textbooks that start from the Peano axioms, on the grounds that building the reals from scratch gives undergraduates sturdier intuition than a black-box axiomatic start.", "preference", "knowledge", False,
     [("Terence Tao", "person"), ("Analysis I", "publication"), ("Analysis II", "publication"), ("Peano axioms", "concept")],
     [("Analysis I", "Terence Tao", "AUTHORED_BY"), ("Analysis II", "Terence Tao", "AUTHORED_BY")],
     "which Tao textbooks favour building analysis from the Peano axioms upward for pedagogical sturdiness",
     "tao analysis i ii peano axiom undergraduate real build scratch"),
    # --- 48 ---
    ("Bourbaki preferred the structuralist language of sets and universal properties over concrete example-driven exposition; the result was a school that valued generality and clean abstraction over computational feel.", "preference", "knowledge", False,
     [("Bourbaki", "person"), ("structuralist", "concept"), ("universal properties", "concept"), ("sets", "concept")],
     [("Bourbaki", "structuralist", "USES")],
     "which stylistic preference did Bourbaki pick between structuralist abstraction and example-led exposition",
     "bourbaki structuralist universal property set abstract general clean"),
    # --- 49 ---
    ("Serre preferred concise lemma-by-lemma manuscripts over the sprawling SGA style, and his 1955 Faisceaux Algébriques Cohérents became the canonical example of that terseness for a generation of algebraic geometers.", "preference", "knowledge", False,
     [("Serre", "person"), ("Faisceaux Algébriques Cohérents", "publication"), ("SGA", "publication"), ("algebraic geometers", "concept")],
     [("Faisceaux Algébriques Cohérents", "Serre", "AUTHORED_BY")],
     "which 1955 Serre manuscript became the canonical terse alternative to the sprawling SGA style",
     "serre 1955 faisceaux algebriques coherent fac sga terse concise"),
    # --- 50 ---
    ("For accessible history-of-mathematics reading the editorial preference leans on Katz's A History of Mathematics over Boyer and Merzbach, citing richer non-Western coverage of Indian, Arabic, and Chinese traditions.", "preference", "knowledge", False,
     [("Katz", "person"), ("A History of Mathematics", "publication"), ("Boyer", "person"), ("Merzbach", "person")],
     [("A History of Mathematics", "Katz", "AUTHORED_BY"), ("A History of Mathematics", "Boyer", "PREFERS")],
     "which history-of-mathematics textbook wins the editorial preference for broader non-Western coverage",
     "katz history mathematics boyer merzbach indian arabic chinese"),
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
