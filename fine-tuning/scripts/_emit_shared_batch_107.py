"""One-off emitter for shared-base batch-107 — knowledge domain (particle physics, high-energy physics, mathematical physics).

Writes 50 rows with ids shared-05301..05350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_107.tmp.jsonl"
ID_OFFSET = 5300

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Standard Model of particle physics, assembled across the 1960s and 1970s, unifies the electromagnetic, weak, and strong interactions as gauge theories with SU(3) x SU(2) x U(1) symmetry.", "architecture", "knowledge", False,
     [("Standard Model", "theory"), ("electromagnetic", "concept"), ("weak", "concept"), ("strong interactions", "concept"), ("SU(3) x SU(2) x U(1)", "concept")],
     [("Standard Model", "SU(3) x SU(2) x U(1)", "DEPENDS_ON")],
     "which gauge-theoretic framework unifies the three non-gravitational interactions under a product symmetry",
     "Standard Model particle gauge SU3 SU2 U1 product symmetry interactions"),
    # --- 2 ---
    ("Richard Feynman introduced diagrammatic perturbation techniques in his 1949 Physical Review paper, replacing the unwieldy Tomonaga-Schwinger operator calculus for most QED computations.", "reference", "knowledge", False,
     [("Richard Feynman", "person"), ("Physical Review", "publication"), ("1949", "date"), ("Tomonaga-Schwinger operator calculus", "method"), ("QED", "theory")],
     [("Physical Review", "Richard Feynman", "AUTHORED_BY"), ("Richard Feynman", "Tomonaga-Schwinger operator calculus", "REPLACES")],
     "which 1949 journal paper made Feynman diagrams the default QED tool over Tomonaga-Schwinger methods",
     "Feynman diagrams Physical Review QED Tomonaga Schwinger successor calculus year"),
    # --- 3 ---
    ("Julian Schwinger's covariant renormalisation of QED, published in Physical Review in 1948, computed the electron anomalous magnetic moment to one loop as alpha over two pi.", "reference", "knowledge", False,
     [("Julian Schwinger", "person"), ("QED", "theory"), ("Physical Review", "publication"), ("1948", "date"), ("electron anomalous magnetic moment", "concept")],
     [("Physical Review", "Julian Schwinger", "AUTHORED_BY")],
     "who computed the one-loop electron anomalous moment in the 1948 Physical Review",
     "Schwinger anomalous magnetic moment one loop alpha two pi year"),
    # --- 4 ---
    ("The Glashow-Weinberg-Salam electroweak theory, assembled between 1961 and 1968, improves on Fermi's four-fermion interaction by mediating weak decays through massive W and Z bosons.", "reference", "knowledge", False,
     [("Glashow-Weinberg-Salam", "theory"), ("Fermi", "person"), ("four-fermion interaction", "theory"), ("W", "concept"), ("Z", "concept")],
     [("Glashow-Weinberg-Salam", "four-fermion interaction", "IMPROVES_ON")],
     "which electroweak synthesis superseded the Fermi four-fermion interaction with massive gauge bosons",
     "Glashow Weinberg Salam electroweak Fermi four fermion predecessor W Z bosons"),
    # --- 5 ---
    ("Peter Higgs and Francois Englert independently proposed spontaneous electroweak symmetry breaking in 1964, generating gauge-boson masses through a scalar field later named the Higgs field.", "milestone", "knowledge", False,
     [("Peter Higgs", "person"), ("Francois Englert", "person"), ("1964", "date"), ("Higgs field", "concept")],
     [("Higgs field", "Peter Higgs", "AUTHORED_BY"), ("Higgs field", "Francois Englert", "AUTHORED_BY")],
     "which two 1964 papers introduced the scalar mechanism generating gauge-boson masses",
     "Higgs Englert spontaneous electroweak symmetry breaking scalar 1964"),
    # --- 6 ---
    ("The ATLAS and CMS collaborations announced discovery of a 125 GeV Higgs boson on 4 July 2012 using LHC proton-proton collisions at 7 and 8 TeV.", "milestone", "knowledge", False,
     [("ATLAS", "organization"), ("CMS", "organization"), ("125 GeV", "concept"), ("Higgs boson", "concept"), ("4 July 2012", "date"), ("LHC", "infrastructure")],
     [("ATLAS", "Higgs boson", "DEPENDS_ON"), ("CMS", "Higgs boson", "DEPENDS_ON")],
     "which two LHC collaborations announced the 125 GeV Higgs discovery in July 2012",
     "ATLAS CMS Higgs boson 125 GeV discovery LHC July 2012 announcement"),
    # --- 7 ---
    ("Gerard 't Hooft's 1971 thesis work at Utrecht proved that spontaneously broken non-abelian gauge theories are renormalisable, rescuing the electroweak programme.", "milestone", "knowledge", False,
     [("Gerard 't Hooft", "person"), ("1971", "date"), ("Utrecht", "place"), ("non-abelian gauge theories", "theory"), ("electroweak programme", "concept")],
     [("non-abelian gauge theories", "Gerard 't Hooft", "AUTHORED_BY")],
     "who rescued the Yang-Mills unification programme by proving a renormalisability result during doctoral studies",
     "Dutch student dissertation renormalisability Yang Mills quantisation revival"),
    # --- 8 ---
    ("Quantum chromodynamics was established as the theory of the strong force after David Gross, Frank Wilczek, and David Politzer discovered asymptotic freedom in 1973.", "milestone", "knowledge", False,
     [("Quantum chromodynamics", "theory"), ("David Gross", "person"), ("Frank Wilczek", "person"), ("David Politzer", "person"), ("asymptotic freedom", "concept"), ("1973", "date")],
     [("Quantum chromodynamics", "asymptotic freedom", "DEPENDS_ON"), ("asymptotic freedom", "David Gross", "AUTHORED_BY")],
     "who discovered the 1973 asymptotic freedom result underpinning QCD",
     "asymptotic freedom Gross Wilczek Politzer QCD strong force 1973"),
    # --- 9 ---
    ("Kenneth Wilson's renormalisation group framework, published in Reviews of Modern Physics in 1975, improves on earlier field-theoretic renormalisation by organising physics scale by scale.", "reference", "knowledge", False,
     [("Kenneth Wilson", "person"), ("renormalisation group", "method"), ("Reviews of Modern Physics", "publication"), ("1975", "date"), ("field-theoretic renormalisation", "method")],
     [("renormalisation group", "Kenneth Wilson", "AUTHORED_BY"), ("renormalisation group", "field-theoretic renormalisation", "IMPROVES_ON")],
     "whose 1975 Reviews of Modern Physics article reframed renormalisation as a scale-by-scale flow",
     "Wilson renormalisation group Reviews Modern Physics scale 1975"),
    # --- 10. noise ---
    ("Let me double-check that cross-section normalisation against the published Physical Review supplement before citing it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Kobayashi-Maskawa matrix, proposed in a 1973 Progress of Theoretical Physics paper, accommodates CP violation through a three-generation quark mixing matrix with a single irreducible phase.", "reference", "knowledge", False,
     [("Kobayashi-Maskawa matrix", "theory"), ("Progress of Theoretical Physics", "publication"), ("1973", "date"), ("CP violation", "concept")],
     [("Kobayashi-Maskawa matrix", "CP violation", "DEPENDS_ON")],
     "which 1973 Japanese paper introduced the three-generation mixing matrix accommodating CP violation",
     "Kobayashi Maskawa CKM 1973 Progress Theoretical Physics three generation CP phase"),
    # --- 12 ---
    ("Makoto Kobayashi and Toshihide Maskawa shared the 2008 Nobel Prize in Physics for the quark-mixing matrix that bears their names.", "milestone", "knowledge", False,
     [("Makoto Kobayashi", "person"), ("Toshihide Maskawa", "person"), ("2008", "date"), ("Nobel Prize in Physics", "event")],
     [],
     "which two physicists received the 2008 Nobel Prize for the CKM mixing matrix",
     "Kobayashi Maskawa 2008 Nobel Prize CKM quark mixing matrix"),
    # --- 13 ---
    ("The path-integral quantisation of gauge fields, codified by Faddeev and Popov in a 1967 Physics Letters B paper, replaced canonical operator gauge fixing in most non-abelian computations.", "reference", "knowledge", False,
     [("Faddeev", "person"), ("Popov", "person"), ("Physics Letters B", "publication"), ("1967", "date"), ("canonical operator gauge fixing", "method"), ("path-integral quantisation", "method")],
     [("path-integral quantisation", "canonical operator gauge fixing", "REPLACES")],
     "which 1967 Physics Letters B paper introduced path-integral gauge fixing over canonical methods",
     "Faddeev Popov ghosts path integral gauge fixing 1967 Physics Letters B"),
    # --- 14 ---
    ("Lattice QCD, formulated by Kenneth Wilson in a 1974 Physical Review D paper, discretises spacetime onto a hypercubic grid so that non-perturbative strong-coupling physics can be computed numerically.", "architecture", "knowledge", False,
     [("Lattice QCD", "method"), ("Kenneth Wilson", "person"), ("1974", "date"), ("Physical Review D", "publication"), ("hypercubic grid", "concept")],
     [("Lattice QCD", "Kenneth Wilson", "AUTHORED_BY")],
     "which 1974 Physical Review D paper founded the lattice formulation of QCD",
     "lattice QCD Wilson 1974 Physical Review D hypercubic discretisation non perturbative"),
    # --- 15 ---
    ("Modern lattice QCD calculations of the proton mass, reported by the BMW collaboration in Science in 2008, reproduce the experimental value to within a few per cent from first principles.", "reference", "knowledge", False,
     [("lattice QCD", "method"), ("proton mass", "concept"), ("BMW collaboration", "organization"), ("Science", "publication"), ("2008", "date")],
     [],
     "which collaboration computed the nucleon mass ab initio and published the result in a 2008 general-science journal",
     "Budapest Marseille Wuppertal first principles hadron spectrum journal Science year"),
    # --- 16 ---
    ("Supersymmetry, developed by Wess and Zumino in a 1974 Nuclear Physics B paper, pairs each Standard Model boson with a fermionic partner to address the hierarchy problem.", "reference", "knowledge", False,
     [("Supersymmetry", "theory"), ("Wess", "person"), ("Zumino", "person"), ("1974", "date"), ("Nuclear Physics B", "publication"), ("hierarchy problem", "concept")],
     [("Supersymmetry", "Wess", "AUTHORED_BY"), ("Supersymmetry", "Zumino", "AUTHORED_BY")],
     "which 1974 Nuclear Physics B paper developed the four-dimensional supersymmetry framework",
     "Wess Zumino supersymmetry Nuclear Physics B 1974 hierarchy boson fermion partner"),
    # --- 17 ---
    ("ATLAS and CMS searches published in Physical Review Letters through 2023 have excluded minimal supersymmetric gluinos below roughly 2.3 TeV under standard decay assumptions.", "fact", "knowledge", False,
     [("ATLAS", "organization"), ("CMS", "organization"), ("Physical Review Letters", "publication"), ("2023", "date"), ("gluinos", "concept"), ("2.3 TeV", "concept")],
     [],
     "which two collider experiments together set a lower bound near 2.3 TeV on supersymmetric coloured octets",
     "LHC general purpose detectors coloured octet superpartner lower bound PRL year"),
    # --- 18 ---
    ("The Sudbury Neutrino Observatory reported in Physical Review Letters in 2001 that solar neutrinos change flavour en route to Earth, confirming neutrino oscillations.", "milestone", "knowledge", False,
     [("Sudbury Neutrino Observatory", "organization"), ("Physical Review Letters", "publication"), ("2001", "date"), ("solar neutrinos", "concept"), ("neutrino oscillations", "theory")],
     [("Physical Review Letters", "Sudbury Neutrino Observatory", "AUTHORED_BY")],
     "which Canadian heavy-water detector announced the flavour-change confirmation in PRL",
     "underground Ontario heavy water detector solar deficit resolved flavour change journal year"),
    # --- 19 ---
    ("Super-Kamiokande announced atmospheric neutrino oscillations in a 1998 Physical Review Letters paper based on a zenith-angle asymmetry in muon-neutrino events.", "milestone", "knowledge", False,
     [("Super-Kamiokande", "organization"), ("1998", "date"), ("Physical Review Letters", "publication"), ("atmospheric neutrino oscillations", "theory"), ("muon-neutrino events", "concept")],
     [("Physical Review Letters", "Super-Kamiokande", "AUTHORED_BY")],
     "which 1998 Physical Review Letters paper reported atmospheric neutrino oscillation from a zenith asymmetry",
     "Super Kamiokande atmospheric neutrino oscillation 1998 zenith muon PRL"),
    # --- 20 ---
    ("The Fermilab Muon g-2 experiment reported in Physical Review Letters in 2021 a value for the muon anomalous magnetic moment that sits about 4.2 standard deviations above the data-driven Standard Model prediction.", "fact", "knowledge", False,
     [("Fermilab", "organization"), ("Muon g-2", "project"), ("Physical Review Letters", "publication"), ("2021", "date"), ("muon anomalous magnetic moment", "concept"), ("Standard Model", "theory")],
     [],
     "which Illinois-based storage-ring measurement revealed a 4.2 sigma tension with the data-driven expectation",
     "Fermilab storage ring lepton anomaly theory tension journal letters year"),
    # --- 21 ---
    ("The Large Hadron Collider, commissioned at CERN near Geneva in 2008, is a 27-kilometre superconducting proton-proton ring that replaced the LEP electron-positron collider in the same tunnel.", "architecture", "knowledge", False,
     [("Large Hadron Collider", "infrastructure"), ("CERN", "organization"), ("Geneva", "place"), ("2008", "date"), ("LEP", "infrastructure")],
     [("Large Hadron Collider", "LEP", "REPLACES")],
     "which Swiss-border hadron ring took over the 27 km electron-positron tunnel at commissioning",
     "CERN Geneva superconducting proton ring successor electron positron tunnel year"),
    # --- 22 ---
    ("The Tevatron proton-antiproton collider at Fermilab ran from 1983 to 2011 and delivered the 1995 CDF and D0 discovery of the top quark near 173 GeV.", "milestone", "knowledge", False,
     [("Tevatron", "infrastructure"), ("Fermilab", "organization"), ("1983", "date"), ("2011", "date"), ("CDF", "organization"), ("D0", "organization"), ("top quark", "concept")],
     [("CDF", "top quark", "DEPENDS_ON"), ("D0", "top quark", "DEPENDS_ON")],
     "which Fermilab collider hosted the 1995 CDF and D0 top-quark discovery",
     "Tevatron Fermilab CDF D0 top quark 1995 173 GeV discovery"),
    # --- 23 ---
    ("SLAC's deep inelastic scattering experiments of 1968 and 1969, analysed by Bjorken and Feynman, provided the first evidence for point-like partons inside the proton.", "milestone", "knowledge", False,
     [("SLAC", "organization"), ("deep inelastic scattering", "method"), ("1968", "date"), ("Bjorken", "person"), ("Feynman", "person"), ("partons", "concept"), ("proton", "concept")],
     [],
     "which Stanford electron-beam programme first revealed substructure inside the nucleon",
     "Stanford linear accelerator scaling inelastic Bjorken x structure function pointlike"),
    # --- 24 ---
    ("The LEP electron-positron collider at CERN measured the Z boson resonance between 1989 and 1995, constraining the number of light neutrino species to three.", "fact", "knowledge", False,
     [("LEP", "infrastructure"), ("CERN", "organization"), ("Z boson", "concept"), ("1989", "date"), ("1995", "date"), ("light neutrino species", "concept")],
     [],
     "which CERN ring constrained the active neutrino family count via Z lineshape fits",
     "invisible width three families lineshape fits resonance LEP run years"),
    # --- 25 ---
    ("Paul Dirac's 1928 Proceedings of the Royal Society A paper introduced the relativistic electron equation and predicted antimatter through its negative-energy solutions.", "reference", "knowledge", False,
     [("Paul Dirac", "person"), ("1928", "date"), ("Proceedings of the Royal Society A", "publication"), ("relativistic electron equation", "theory"), ("antimatter", "concept")],
     [("Proceedings of the Royal Society A", "Paul Dirac", "AUTHORED_BY")],
     "which British theorist's late-1920s Royal Society article foretold the positron from negative-energy states",
     "Cambridge theorist spinor wave equation hole theory Royal Society article year"),
    # --- 26 ---
    ("Steven Weinberg's 1967 Physical Review Letters article A Model of Leptons fused the Glashow SU(2) x U(1) structure with Higgs breaking to give masses to the leptons.", "reference", "knowledge", False,
     [("Steven Weinberg", "person"), ("1967", "date"), ("Physical Review Letters", "publication"), ("A Model of Leptons", "publication"), ("SU(2) x U(1)", "concept")],
     [("A Model of Leptons", "Steven Weinberg", "AUTHORED_BY")],
     "whose late-1960s PRL essay married the Glashow gauge group to spontaneous scalar breaking for charged-lepton masses",
     "Harvard theorist electroweak synthesis letters article lepton mass generation year"),
    # --- 27 ---
    ("Sheldon Glashow's 1961 Nuclear Physics paper first proposed the SU(2) x U(1) electroweak gauge structure before the Higgs mechanism was added.", "reference", "knowledge", False,
     [("Sheldon Glashow", "person"), ("1961", "date"), ("Nuclear Physics", "publication"), ("SU(2) x U(1)", "concept")],
     [("Nuclear Physics", "Sheldon Glashow", "AUTHORED_BY")],
     "who proposed the SU(2) x U(1) electroweak gauge structure in a 1961 Nuclear Physics paper",
     "Glashow 1961 Nuclear Physics SU2 U1 electroweak structure"),
    # --- 28 ---
    ("Abdus Salam presented the same electroweak unification at the 1968 Eighth Nobel Symposium in Lerum, for which he shared the 1979 Nobel Prize with Glashow and Weinberg.", "milestone", "knowledge", False,
     [("Abdus Salam", "person"), ("1968", "date"), ("Eighth Nobel Symposium", "event"), ("Lerum", "place"), ("1979", "date"), ("Glashow", "person"), ("Weinberg", "person")],
     [],
     "which 1968 Swedish symposium hosted Salam's electroweak presentation that led to the 1979 Nobel",
     "Salam 1968 Nobel Symposium Lerum electroweak Glashow Weinberg 1979 Nobel"),
    # --- 29 ---
    ("Edward Witten's 1981 Nuclear Physics B paper Dynamical Breaking of Supersymmetry introduced the index now central to modern supersymmetric-field-theory arguments.", "reference", "knowledge", False,
     [("Edward Witten", "person"), ("1981", "date"), ("Nuclear Physics B", "publication"), ("Dynamical Breaking of Supersymmetry", "publication")],
     [("Dynamical Breaking of Supersymmetry", "Edward Witten", "AUTHORED_BY")],
     "whose early-1980s Nuclear Physics article defined the now-standard topological invariant for SUSY ground states",
     "Princeton theorist topological invariant ground state counting SUSY journal article year"),
    # --- 30 ---
    ("Juan Maldacena's 1998 Advances in Theoretical and Mathematical Physics paper proposed the AdS/CFT correspondence between type IIB string theory on AdS5 x S5 and N=4 super Yang-Mills in four dimensions.", "reference", "knowledge", False,
     [("Juan Maldacena", "person"), ("1998", "date"), ("Advances in Theoretical and Mathematical Physics", "publication"), ("AdS/CFT correspondence", "theory"), ("N=4 super Yang-Mills", "theory")],
     [("AdS/CFT correspondence", "Juan Maldacena", "AUTHORED_BY")],
     "which 1998 paper conjectured the AdS5 x S5 to N=4 super Yang-Mills duality",
     "Maldacena 1998 AdS CFT correspondence type IIB N=4 super Yang Mills"),
    # --- 31 ---
    ("Michael Atiyah and Isadore Singer's index theorem, proved in a 1963 announcement and a 1968 Annals of Mathematics series, links the analytic index of an elliptic operator to a topological invariant.", "reference", "knowledge", False,
     [("Michael Atiyah", "person"), ("Isadore Singer", "person"), ("1963", "date"), ("1968", "date"), ("Annals of Mathematics", "publication"), ("index theorem", "theory")],
     [("index theorem", "Michael Atiyah", "AUTHORED_BY"), ("index theorem", "Isadore Singer", "AUTHORED_BY")],
     "which 1960s theorem connected analytic indices of elliptic operators with topological invariants",
     "Atiyah Singer index theorem Annals Mathematics elliptic operator 1963 1968"),
    # --- 32 ---
    ("The Wightman axioms, formulated by Arthur Wightman in a 1956 Physical Review paper, give a mathematically rigorous framework for relativistic quantum field theory in terms of operator-valued tempered distributions.", "reference", "knowledge", False,
     [("Wightman axioms", "framework"), ("Arthur Wightman", "person"), ("1956", "date"), ("Physical Review", "publication"), ("relativistic quantum field theory", "theory")],
     [("Wightman axioms", "Arthur Wightman", "AUTHORED_BY")],
     "which 1956 Physical Review paper laid out the rigorous axioms for relativistic quantum field theory",
     "Wightman axioms 1956 Physical Review relativistic QFT tempered distributions"),
    # --- 33 ---
    ("Edward Witten's 1989 Communications in Mathematical Physics paper Quantum Field Theory and the Jones Polynomial recast the Jones knot invariant through Chern-Simons gauge theory.", "reference", "knowledge", False,
     [("Edward Witten", "person"), ("1989", "date"), ("Communications in Mathematical Physics", "publication"), ("Quantum Field Theory and the Jones Polynomial", "publication"), ("Chern-Simons gauge theory", "theory")],
     [("Quantum Field Theory and the Jones Polynomial", "Edward Witten", "AUTHORED_BY")],
     "which late-1980s CMP essay interpreted a knot invariant through topological gauge theory",
     "knot invariant topological gauge partition function Wilson loop three manifold"),
    # --- 34. noise ---
    ("Hmm, I need to verify whether that preprint used MS-bar or on-shell renormalisation before comparing the numbers.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The BaBar experiment at SLAC published measurements in Physical Review D between 2001 and 2008 that established CP violation in the B-meson system consistent with the CKM picture.", "fact", "knowledge", False,
     [("BaBar", "organization"), ("SLAC", "organization"), ("Physical Review D", "publication"), ("2001", "date"), ("2008", "date"), ("B-meson system", "concept"), ("CKM", "concept")],
     [],
     "which Stanford-based B-factory confirmed the Kobayashi-Maskawa picture across the 2000s",
     "California asymmetric B factory CP asymmetry quark mixing pattern PRD decade"),
    # --- 36 ---
    ("The Belle collaboration at KEK co-published in Physical Review Letters in 2001 a measurement of sin(2 beta) from B meson decays that confirmed the KM prediction.", "fact", "knowledge", False,
     [("Belle", "organization"), ("KEK", "organization"), ("Physical Review Letters", "publication"), ("2001", "date"), ("sin(2 beta)", "concept"), ("KM prediction", "theory")],
     [],
     "which Japanese B-factory matched the Kobayashi-Maskawa expectation in a millennium-era PRL",
     "Tsukuba asymmetric accelerator unitarity triangle angle B meson letters article"),
    # --- 37 ---
    ("Murray Gell-Mann's 1964 Physics Letters note A Schematic Model of Baryons and Mesons introduced the quark hypothesis with fractional electric charges.", "reference", "knowledge", False,
     [("Murray Gell-Mann", "person"), ("1964", "date"), ("Physics Letters", "publication"), ("A Schematic Model of Baryons and Mesons", "publication"), ("quark hypothesis", "theory")],
     [("A Schematic Model of Baryons and Mesons", "Murray Gell-Mann", "AUTHORED_BY")],
     "which mid-1960s brief letter first proposed constituents carrying third-integer charges inside hadrons",
     "Caltech theorist short note hadron constituents third integer charges schematic"),
    # --- 38 ---
    ("The MS-bar renormalisation scheme, introduced by Bardeen, Buras, Duke, and Muta in a 1978 Physical Review D paper, is usually preferred over on-shell subtraction for precision QCD calculations.", "preference", "knowledge", False,
     [("MS-bar renormalisation scheme", "method"), ("Bardeen", "person"), ("Buras", "person"), ("Duke", "person"), ("Muta", "person"), ("1978", "date"), ("Physical Review D", "publication"), ("on-shell subtraction", "method")],
     [("MS-bar renormalisation scheme", "on-shell subtraction", "PREFERS")],
     "which 1978 Physical Review D renormalisation scheme is usually preferred over on-shell for QCD",
     "MS-bar Bardeen Buras Duke Muta 1978 Physical Review D QCD on shell comparison"),
    # --- 39 ---
    ("Next-to-leading order QCD corrections to Drell-Yan, computed by Altarelli, Ellis, and Martinelli in a 1978 Nuclear Physics B paper, improve on leading-order matrix elements by capturing large logarithmic enhancements.", "reference", "knowledge", False,
     [("Next-to-leading order", "method"), ("QCD", "theory"), ("Drell-Yan", "concept"), ("Altarelli", "person"), ("Ellis", "person"), ("Martinelli", "person"), ("1978", "date"), ("Nuclear Physics B", "publication")],
     [("Next-to-leading order", "Altarelli", "AUTHORED_BY"), ("Next-to-leading order", "QCD", "IMPROVES_ON")],
     "which 1978 Nuclear Physics B paper computed NLO QCD corrections to Drell-Yan",
     "NLO Drell Yan Altarelli Ellis Martinelli 1978 Nuclear Physics B leading order"),
    # --- 40 ---
    ("Faddeev-Popov ghosts, introduced in the 1967 Physics Letters B paper, restore unitarity in perturbative non-abelian gauge theory and are absent from the earlier abelian-style treatments they improve on.", "reference", "knowledge", False,
     [("Faddeev-Popov ghosts", "concept"), ("1967", "date"), ("Physics Letters B", "publication"), ("perturbative non-abelian gauge theory", "theory"), ("abelian-style treatments", "method")],
     [("Faddeev-Popov ghosts", "abelian-style treatments", "IMPROVES_ON")],
     "which 1967 construction restored unitarity in non-abelian gauge theory beyond naive abelian treatments",
     "Faddeev Popov ghosts 1967 Physics Letters B unitarity non abelian comparison abelian"),
    # --- 41 ---
    ("The discovery of the J/psi charmonium state, announced simultaneously at SLAC and Brookhaven in November 1974, is conventionally treated as the November Revolution of particle physics.", "milestone", "knowledge", False,
     [("J/psi", "concept"), ("SLAC", "organization"), ("Brookhaven", "organization"), ("November 1974", "date"), ("November Revolution", "event")],
     [],
     "which November 1974 charmonium discovery is called the November Revolution of particle physics",
     "J/psi charmonium SLAC Brookhaven November 1974 Revolution discovery"),
    # --- 42 ---
    ("The Froissart bound, derived by Marcel Froissart in a 1961 Physical Review paper, constrains high-energy hadronic total cross-sections to grow at most as the square of the logarithm of the centre-of-mass energy.", "reference", "knowledge", False,
     [("Froissart bound", "theory"), ("Marcel Froissart", "person"), ("1961", "date"), ("Physical Review", "publication"), ("hadronic total cross-sections", "concept")],
     [("Froissart bound", "Marcel Froissart", "AUTHORED_BY")],
     "whose 1961 analyticity argument caps high-energy strong-interaction totals at log-squared growth",
     "analyticity unitarity strong interaction asymptotic limit French theorist journal year"),
    # --- 43 ---
    ("The Seiberg-Witten solution of N=2 super Yang-Mills, reported in two 1994 Nuclear Physics B papers, improves on perturbative handling of the moduli space by giving an exact low-energy effective action.", "reference", "knowledge", False,
     [("Seiberg-Witten solution", "theory"), ("N=2 super Yang-Mills", "theory"), ("1994", "date"), ("Nuclear Physics B", "publication"), ("moduli space", "concept")],
     [("Seiberg-Witten solution", "moduli space", "IMPROVES_ON")],
     "which 1994 Nuclear Physics B papers gave the exact low-energy N=2 super Yang-Mills solution",
     "Seiberg Witten 1994 Nuclear Physics B N=2 super Yang Mills moduli exact"),
    # --- 44 ---
    ("Gabriele Veneziano's 1968 Nuovo Cimento paper on dual resonance amplitudes, with its Euler-beta-function ansatz, is widely treated as the birth of string theory.", "milestone", "knowledge", False,
     [("Gabriele Veneziano", "person"), ("1968", "date"), ("Nuovo Cimento", "publication"), ("dual resonance amplitudes", "concept"), ("Euler-beta-function ansatz", "method"), ("string theory", "theory")],
     [("dual resonance amplitudes", "Gabriele Veneziano", "AUTHORED_BY")],
     "which 1968 Nuovo Cimento paper is treated as the seed of string theory",
     "Veneziano 1968 Nuovo Cimento dual resonance Euler beta string theory birth"),
    # --- 45 ---
    ("Green and Schwarz's 1984 Physics Letters B paper on anomaly cancellation for SO(32) type I string theory triggered the First Superstring Revolution.", "milestone", "knowledge", False,
     [("Green", "person"), ("Schwarz", "person"), ("1984", "date"), ("Physics Letters B", "publication"), ("SO(32)", "concept"), ("type I string theory", "theory"), ("First Superstring Revolution", "event")],
     [],
     "which mid-1980s letter showing anomaly freedom for the open-string gauge group ignited renewed interest in strings",
     "orthogonal thirty two open string anomaly freedom mid eighties letters article revival"),
    # --- 46 ---
    ("Alain Connes's noncommutative-geometry reformulation of the Standard Model, published in Communications in Mathematical Physics in 1996, improves on conventional gauge-theoretic presentations by deriving the gauge group from a spectral triple.", "reference", "knowledge", False,
     [("Alain Connes", "person"), ("noncommutative-geometry", "theory"), ("Standard Model", "theory"), ("Communications in Mathematical Physics", "publication"), ("1996", "date"), ("spectral triple", "concept")],
     [("noncommutative-geometry", "Alain Connes", "AUTHORED_BY"), ("noncommutative-geometry", "Standard Model", "IMPROVES_ON")],
     "whose mid-1990s CMP article recovered the electroweak-plus-colour gauge group from a spectral-triple data set",
     "French mathematician spectral triple gauge recovery mid nineties CMP article"),
    # --- 47 ---
    ("Yoichiro Nambu and Jona-Lasinio's 1961 Physical Review paper on dynamical symmetry breaking provided the prototype for the chiral-symmetry-breaking ideas that reshaped QCD.", "reference", "knowledge", False,
     [("Yoichiro Nambu", "person"), ("Jona-Lasinio", "person"), ("1961", "date"), ("Physical Review", "publication"), ("dynamical symmetry breaking", "theory"), ("QCD", "theory")],
     [("Physical Review", "Yoichiro Nambu", "AUTHORED_BY")],
     "whose early-1960s Physical Review article gave the template for chiral breaking that colour theory later adopted",
     "superconductor analogy four fermion condensate chiral prototype Osaka Chicago theorists"),
    # --- 48 ---
    ("The Cabibbo angle, introduced by Nicola Cabibbo in a 1963 Physical Review Letters paper, mixed the down and strange quarks and was later generalised by Kobayashi and Maskawa to three generations.", "reference", "knowledge", False,
     [("Cabibbo angle", "concept"), ("Nicola Cabibbo", "person"), ("1963", "date"), ("Physical Review Letters", "publication"), ("Kobayashi", "person"), ("Maskawa", "person")],
     [("Cabibbo angle", "Nicola Cabibbo", "AUTHORED_BY")],
     "which 1963 Physical Review Letters paper introduced the Cabibbo angle later generalised to CKM",
     "Cabibbo angle 1963 Physical Review Letters down strange two generation KM generalisation"),
    # --- 49 ---
    ("Osterwalder and Schrader's 1973 Communications in Mathematical Physics reconstruction theorem links Euclidean Schwinger functions to Lorentzian Wightman theories, improving on purely Minkowskian axiomatisations.", "reference", "knowledge", False,
     [("Osterwalder", "person"), ("Schrader", "person"), ("1973", "date"), ("Communications in Mathematical Physics", "publication"), ("Schwinger functions", "concept"), ("Wightman theories", "framework")],
     [("Schwinger functions", "Wightman theories", "IMPROVES_ON")],
     "which 1973 Communications in Mathematical Physics theorem reconstructs Wightman theories from Euclidean Schwinger functions",
     "Osterwalder Schrader 1973 Communications Mathematical Physics Euclidean Schwinger Wightman reconstruction"),
    # --- 50 ---
    ("The LHCb collaboration reported in Nature Physics in 2022 lepton-flavour-universality tests in B to K* decays that, after improved selection, no longer showed a significant deviation from Standard Model predictions.", "fact", "knowledge", False,
     [("LHCb", "organization"), ("Nature Physics", "publication"), ("2022", "date"), ("lepton-flavour-universality", "concept"), ("B to K*", "concept"), ("Standard Model", "theory")],
     [],
     "which CERN flavour experiment's 2022 update dissolved the earlier muon-electron ratio anomaly in rare kaon-mode B decays",
     "CERN bottom flavour experiment reanalysis muon electron ratio rare mode Nature journal"),
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
