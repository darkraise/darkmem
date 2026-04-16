"""One-off emitter for shared-base batch-234 — knowledge domain (history of physics and key discoveries).

Writes 50 rows to data/v2/shared/batch_234.tmp.jsonl with ids shared-11651..11700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_234.tmp.jsonl"
ID_OFFSET = 11650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Galileo's inclined-plane experiments in Padua around 1604 established that falling bodies accelerate uniformly, which broke the Aristotelian view that heavier objects fall faster.", "milestone", "knowledge", False,
     [("Galileo", "person"), ("Padua", "place"), ("Aristotelian", "concept")],
     [("Galileo", "Aristotelian", "REPLACES")],
     "which early-seventeenth-century experiments overturned the Aristotelian picture of falling bodies and where",
     "galileo inclined plane padua falling body aristotle acceleration"),
    # --- 2 ---
    ("Kepler's three laws of planetary motion, published between 1609 and 1619, tied ellipses and the harmonic law together and gave Newton the empirical scaffold he later explained by inverse-square gravity.", "decision", "knowledge", False,
     [("Kepler", "person"), ("Newton", "person"), ("inverse-square gravity", "concept")],
     [("Newton", "Kepler", "APPLIES_TO")],
     "how did Kepler's empirical planetary laws feed directly into Newton's later dynamical explanation",
     "kepler three laws planetary motion ellipse harmonic newton gravity"),
    # --- 3 ---
    ("Newton published the Principia in 1687, deriving the universal law of gravitation and the three laws of motion in one geometric treatise that set the template for mathematical physics for two centuries.", "milestone", "knowledge", False,
     [("Newton", "person"), ("Principia", "project"), ("universal law of gravitation", "concept")],
     [("Newton", "Principia", "PRODUCES")],
     "which 1687 treatise bundled universal gravitation with the three laws of motion and who authored it",
     "newton principia 1687 gravitation laws motion geometric treatise"),
    # --- 4 ---
    ("Maxwell's equations, consolidated in his 1865 paper on the electromagnetic field, unified electricity, magnetism, and light as a single field theory and predicted the wave speed of light from two lab constants.", "architecture", "knowledge", False,
     [("Maxwell's equations", "concept"), ("electromagnetic field", "concept")],
     [("Maxwell's equations", "electromagnetic field", "APPLIES_TO")],
     "which 1865 synthesis tied electricity magnetism and light together and whose paper introduced it",
     "maxwell equations 1865 electromagnetic field light wave speed unify"),
    # --- 5 ---
    ("Clausius coined the word entropy in 1865 and stated the second law as heat flows from hot to cold, laying the thermodynamic ground floor that Boltzmann later rebuilt on statistical microstates.", "decision", "knowledge", False,
     [("Clausius", "person"), ("entropy", "concept"), ("Boltzmann", "person"), ("second law", "concept")],
     [("Boltzmann", "Clausius", "IMPROVES_ON")],
     "who introduced the term entropy and which statistical reformulation came after it",
     "clausius entropy 1865 second law thermodynamics boltzmann statistical"),
    # --- 6 ---
    ("Boltzmann's 1877 relation S equals k log W recast thermodynamic entropy as a count of microstates and the formula is carved on his Vienna tombstone as the public summary of his life's work.", "fact", "knowledge", False,
     [("Boltzmann", "person"), ("S equals k log W", "concept"), ("Vienna", "place")],
     [("Boltzmann", "S equals k log W", "PRODUCES")],
     "which 1877 microstate formula summarises Boltzmann's statistical recasting of entropy",
     "boltzmann 1877 entropy microstate k log w vienna tombstone statistical"),
    # --- 7 ---
    ("Planck's quantum hypothesis in December 1900 introduced discrete energy elements h nu to fit the blackbody spectrum, a pragmatic fix that accidentally opened the door to quantum theory.", "fact", "knowledge", False,
     [("Planck", "person"), ("quantum hypothesis", "concept"), ("blackbody", "concept"), ("h nu", "concept")],
     [("Planck", "quantum hypothesis", "PRODUCES")],
     "which December 1900 proposal first quantised radiation to match the blackbody curve",
     "planck quantum hypothesis 1900 blackbody h nu discrete energy"),
    # --- 8 ---
    ("Einstein's 1905 annus mirabilis produced four papers on special relativity, the photoelectric effect, Brownian motion, and mass-energy equivalence, any one of which would have made a career.", "architecture", "knowledge", False,
     [("Einstein", "person"), ("special relativity", "concept"), ("photoelectric effect", "concept"), ("Brownian motion", "concept"), ("mass-energy equivalence", "concept")],
     [("Einstein", "special relativity", "PRODUCES"), ("Einstein", "photoelectric effect", "PRODUCES")],
     "which four breakthroughs did Einstein publish in his 1905 miracle year and on which topics",
     "einstein 1905 annus mirabilis special relativity photoelectric brownian"),
    # --- 9 ---
    ("Einstein's photoelectric effect paper treated light as discrete quanta and earned him the 1921 Nobel Prize, explicitly not for relativity because the committee still considered relativity unsettled.", "fact", "knowledge", False,
     [("Einstein", "person"), ("photoelectric effect", "concept"), ("Nobel Prize", "concept"), ("relativity", "concept")],
     [("Nobel Prize", "photoelectric effect", "APPLIES_TO")],
     "which Einstein paper won him the Nobel and why the committee skipped relativity explicitly",
     "einstein photoelectric nobel 1921 relativity quanta light committee"),
    # --- 10. noise ---
    ("The reading-room printer at the library spat out the day's physics arxiv preprints on green-bar paper long after everyone else had moved to PDFs.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Einstein completed general relativity in November 1915 at the Prussian Academy, finally closing the loop between gravitation and spacetime curvature that special relativity had left open for a decade.", "milestone", "knowledge", False,
     [("Einstein", "person"), ("general relativity", "concept"), ("Prussian Academy", "organization"), ("spacetime curvature", "concept")],
     [("Einstein", "general relativity", "PRODUCES")],
     "where and when did Einstein deliver the completed general relativity equations",
     "einstein general relativity 1915 prussian academy spacetime curvature"),
    # --- 12 ---
    ("Eddington's 1919 Principe eclipse expedition measured starlight deflection around the Sun and the result matched general relativity, turning Einstein overnight into a global public figure.", "decision", "knowledge", False,
     [("Eddington", "person"), ("Principe", "place"), ("general relativity", "concept"), ("Einstein", "person")],
     [("Eddington", "general relativity", "APPLIES_TO")],
     "which 1919 eclipse measurement confirmed general relativity and who led the expedition",
     "eddington 1919 eclipse principe starlight deflection einstein confirm"),
    # --- 13 ---
    ("Bohr's 1913 atomic model quantised electron orbits around the hydrogen nucleus and reproduced the Balmer series, the first concrete stepping stone from classical orbits to quantum structure.", "decision", "knowledge", False,
     [("Bohr", "person"), ("Balmer series", "concept"), ("hydrogen", "concept"), ("atomic model", "concept")],
     [("Bohr", "atomic model", "PRODUCES")],
     "which 1913 atomic picture quantised electron orbits and which spectral series did it reproduce",
     "bohr atom 1913 quantise orbit hydrogen balmer series spectrum"),
    # --- 14 ---
    ("Heisenberg formulated matrix mechanics on Helgoland in June 1925 while convalescing from hay fever, and the non-commuting matrices that fell out of the formalism shocked Born when he recognised them.", "architecture", "knowledge", False,
     [("Heisenberg", "person"), ("matrix mechanics", "concept"), ("Helgoland", "place"), ("Born", "person")],
     [("Heisenberg", "matrix mechanics", "PRODUCES")],
     "where did Heisenberg work out matrix mechanics and who recognised the non-commuting structure",
     "heisenberg matrix mechanics helgoland 1925 born non commuting"),
    # --- 15 ---
    ("Heisenberg's 1927 uncertainty principle set a hard floor on the product of position and momentum uncertainties and killed any lingering hope of a classical deterministic picture beneath quantum phenomena.", "decision", "knowledge", False,
     [("Heisenberg", "person"), ("uncertainty principle", "concept"), ("position", "concept"), ("momentum", "concept")],
     [("Heisenberg", "uncertainty principle", "PRODUCES")],
     "which 1927 principle bounded position and momentum jointly and what classical hope did it end",
     "heisenberg uncertainty 1927 position momentum floor classical determinism"),
    # --- 16 ---
    ("Schrödinger's 1926 wave equation recast quantum mechanics in a continuous language of wavefunctions and was quickly shown to be mathematically equivalent to Heisenberg's matrix mechanics formulation.", "fact", "knowledge", False,
     [("Schrödinger", "person"), ("wave equation", "concept"), ("wavefunction", "concept"), ("matrix mechanics", "concept")],
     [("wave equation", "matrix mechanics", "APPLIES_TO")],
     "which 1926 continuous formulation paralleled Heisenberg's matrices and who derived it",
     "schrodinger wave equation 1926 wavefunction matrix mechanics equivalent"),
    # --- 17 ---
    ("The Copenhagen interpretation, synthesised by Bohr and Heisenberg around 1927, treated measurement as a primitive that collapses the wavefunction and became the pragmatic default in textbooks for decades.", "decision", "knowledge", False,
     [("Copenhagen interpretation", "concept"), ("Bohr", "person"), ("Heisenberg", "person"), ("wavefunction", "concept")],
     [("Bohr", "Copenhagen interpretation", "PRODUCES")],
     "which 1927 interpretation made measurement a primitive and who jointly synthesised it",
     "copenhagen interpretation bohr heisenberg 1927 wavefunction collapse measurement"),
    # --- 18 ---
    ("The Dirac equation, published in 1928, married special relativity with quantum mechanics for the electron, predicted spin as a consequence of the formalism, and implied the existence of antimatter four years before positron discovery.", "architecture", "knowledge", False,
     [("Dirac equation", "concept"), ("antimatter", "concept"), ("positron", "concept"), ("spin", "concept")],
     [("Dirac equation", "antimatter", "APPLIES_TO")],
     "which 1928 equation predicted antimatter as a formal consequence before the positron was seen",
     "dirac equation 1928 relativistic electron spin antimatter positron predict"),
    # --- 19 ---
    ("Anderson's 1932 cloud-chamber positron photograph at Caltech confirmed Dirac's prediction of antimatter and was the first concrete antiparticle ever identified in an experiment.", "decision", "knowledge", False,
     [("Anderson", "person"), ("Caltech", "organization"), ("positron", "concept"), ("Dirac", "person"), ("antimatter", "concept")],
     [("Anderson", "positron", "PRODUCES")],
     "which 1932 cloud-chamber result confirmed antimatter and at which institution did it happen",
     "anderson positron 1932 caltech cloud chamber dirac antimatter"),
    # --- 20 ---
    ("Fermi's December 1942 reactor Chicago Pile-1 achieved the first controlled self-sustaining nuclear chain reaction under the stands of Stagg Field and kicked the atomic age into practical motion.", "milestone", "knowledge", False,
     [("Fermi", "person"), ("Chicago Pile-1", "project"), ("Stagg Field", "place"), ("chain reaction", "concept")],
     [("Fermi", "Chicago Pile-1", "PRODUCES")],
     "which December 1942 reactor achieved the first controlled nuclear chain reaction and where",
     "fermi chicago pile 1 1942 stagg field chain reaction reactor"),
    # --- 21 ---
    ("Feynman's path-integral formulation of quantum mechanics, worked out in his 1942 Princeton thesis under Wheeler, reframed amplitudes as sums over histories and became the working language of modern field theory.", "architecture", "knowledge", False,
     [("Feynman", "person"), ("path-integral", "concept"), ("Wheeler", "person"), ("Princeton", "place")],
     [("Feynman", "path-integral", "PRODUCES")],
     "which Feynman thesis reframed quantum mechanics as a sum over histories and under whom",
     "feynman path integral 1942 princeton wheeler sum histories"),
    # --- 22 ---
    ("Shelter Island in 1947 convened Feynman, Schwinger, and others to tackle the Lamb shift, and the conference is generally treated as the birthplace of renormalised QED as a working theory.", "problem", "knowledge", False,
     [("Shelter Island", "place"), ("Feynman", "person"), ("Schwinger", "person"), ("Lamb shift", "concept"), ("QED", "concept")],
     [("Shelter Island", "QED", "APPLIES_TO")],
     "which 1947 conference kicked off renormalised QED and which experimental anomaly drove it",
     "shelter island 1947 feynman schwinger lamb shift qed renormalise"),
    # --- 23 ---
    ("Dyson's 1949 paper proved that the Feynman, Schwinger, and Tomonaga formulations of QED were equivalent, and his diagrammatic exposition made Feynman diagrams the default calculational tool in field theory.", "decision", "knowledge", False,
     [("Dyson", "person"), ("Feynman", "person"), ("Schwinger", "person"), ("Tomonaga", "person"), ("QED", "concept"), ("Feynman diagrams", "concept")],
     [("Dyson", "Feynman diagrams", "APPLIES_TO")],
     "which 1949 Dyson paper showed the three QED formulations were equivalent and popularised diagrams",
     "dyson 1949 feynman schwinger tomonaga qed equivalent diagrams"),
    # --- 24 ---
    ("Yang-Mills theory from the 1954 Yang and Mills non-abelian gauge paper was a mathematical scaffold that looked like a curiosity at the time but became the backbone of electroweak and strong interactions.", "decision", "knowledge", False,
     [("Yang-Mills", "concept"), ("Yang", "person"), ("Mills", "person"), ("gauge", "concept")],
     [("Yang", "Yang-Mills", "PRODUCES")],
     "which 1954 non-abelian gauge paper later underpinned electroweak and strong force physics",
     "yang mills 1954 non abelian gauge theory electroweak strong"),
    # --- 25 ---
    ("Weinberg's 1967 paper A Model of Leptons built the electroweak unification of weak and electromagnetic interactions via spontaneously broken SU(2)xU(1) symmetry and is one of the most-cited physics papers ever published.", "decision", "knowledge", False,
     [("Weinberg", "person"), ("A Model of Leptons", "project"), ("SU(2)xU(1)", "concept"), ("electroweak", "concept")],
     [("Weinberg", "A Model of Leptons", "PRODUCES")],
     "which Weinberg 1967 paper unified weak and electromagnetic forces via spontaneous symmetry breaking",
     "weinberg 1967 model leptons electroweak su2 u1 spontaneous symmetry"),
    # --- 26 ---
    ("The Higgs mechanism was proposed independently in 1964 by Englert, Brout, and Higgs to give gauge bosons mass without breaking the underlying gauge symmetry of the Lagrangian.", "architecture", "knowledge", False,
     [("Higgs mechanism", "concept"), ("Englert", "person"), ("Brout", "person"), ("Higgs", "person"), ("gauge bosons", "concept")],
     [("Higgs", "Higgs mechanism", "PRODUCES")],
     "which 1964 mechanism gives gauge bosons mass without breaking the symmetry and who proposed it",
     "higgs mechanism 1964 englert brout gauge boson mass symmetry"),
    # --- 27 ---
    ("The Standard Model consolidated electroweak unification and QCD into a single SU(3)xSU(2)xU(1) gauge theory by the mid-1970s and its predictions have passed every collider test inside quoted errors for fifty years.", "reference", "knowledge", False,
     [("Standard Model", "concept"), ("QCD", "concept"), ("SU(3)xSU(2)xU(1)", "concept"), ("electroweak", "concept")],
     [("Standard Model", "QCD", "USES"), ("Standard Model", "electroweak", "USES")],
     "which gauge structure stitches QCD and electroweak theory into the Standard Model",
     "standard model su3 su2 u1 qcd electroweak gauge theory unify"),
    # --- 28 ---
    ("CERN's ATLAS and CMS collaborations announced discovery of a 125 GeV boson consistent with the Higgs on 4 July 2012, completing the particle roster of the Standard Model forty-eight years after the prediction.", "milestone", "knowledge", False,
     [("CERN", "organization"), ("ATLAS", "project"), ("CMS", "project"), ("Higgs", "person"), ("125 GeV", "concept")],
     [("ATLAS", "Higgs", "APPLIES_TO"), ("CMS", "Higgs", "APPLIES_TO")],
     "which two CERN experiments announced the Higgs-like 125 GeV boson on 4 July 2012",
     "cern atlas cms higgs boson 125 gev 2012 discover"),
    # --- 29 ---
    ("Englert and Higgs shared the 2013 Nobel Prize in Physics for the mechanism, announced a year after experimental confirmation and notably omitting Brout, who had died in 2011 and could not be named posthumously.", "fact", "knowledge", False,
     [("Englert", "person"), ("Higgs", "person"), ("Brout", "person"), ("Nobel Prize", "concept")],
     [("Nobel Prize", "Higgs", "APPLIES_TO")],
     "who shared the 2013 physics Nobel for the Higgs mechanism and why Brout was not named",
     "englert higgs nobel 2013 physics brout posthumous mechanism"),
    # --- 30 ---
    ("LIGO's Hanford and Livingston detectors recorded GW150914 on 14 September 2015, the first direct gravitational-wave detection, from the merger of two stellar-mass black holes a billion light-years away.", "milestone", "knowledge", False,
     [("LIGO", "project"), ("GW150914", "concept"), ("Hanford", "place"), ("Livingston", "place"), ("black holes", "concept")],
     [("LIGO", "GW150914", "PRODUCES")],
     "which LIGO detection on 14 September 2015 was the first direct observation of gravitational waves",
     "ligo gw150914 2015 hanford livingston gravitational wave black hole"),
    # --- 31 ---
    ("Weiss, Barish, and Thorne shared the 2017 Nobel Prize in Physics for LIGO, recognising the decades-long instrumentation push that made femtometre-scale strain measurements possible on kilometre-scale interferometers.", "fact", "knowledge", False,
     [("Weiss", "person"), ("Barish", "person"), ("Thorne", "person"), ("LIGO", "project"), ("Nobel Prize", "concept")],
     [("Nobel Prize", "LIGO", "APPLIES_TO")],
     "which three LIGO figures shared the 2017 physics Nobel for gravitational-wave detection",
     "weiss barish thorne nobel 2017 ligo gravitational wave interferometer"),
    # --- 32 ---
    ("The Event Horizon Telescope consortium published the first resolved image of a black hole shadow on 10 April 2019, resolving the ring around M87* via very-long-baseline interferometry across eight global radio dishes.", "milestone", "knowledge", False,
     [("Event Horizon Telescope", "project"), ("M87*", "concept"), ("very-long-baseline interferometry", "method"), ("black hole", "concept")],
     [("Event Horizon Telescope", "M87*", "APPLIES_TO")],
     "which April 2019 collaboration produced the first direct image of a black hole and which target",
     "event horizon telescope m87 2019 black hole shadow vlbi ring"),
    # --- 33 ---
    ("A follow-up EHT result in May 2022 imaged Sagittarius A*, the supermassive black hole at the Milky Way's centre, a technically harder target because its shorter variability timescale blurs single-night snapshots.", "reference", "knowledge", False,
     [("EHT", "project"), ("Sagittarius A*", "concept"), ("Milky Way", "concept")],
     [("EHT", "Sagittarius A*", "APPLIES_TO")],
     "which May 2022 EHT image captured the Milky Way's central supermassive black hole",
     "eht sagittarius a star 2022 milky way black hole variability"),
    # --- 34 ---
    ("Hubble's 1929 redshift-distance relation established that galaxies recede at speeds proportional to distance, the first empirical foundation of modern expanding-universe cosmology.", "architecture", "knowledge", False,
     [("Hubble", "person"), ("redshift-distance", "concept"), ("expanding-universe", "concept")],
     [("Hubble", "redshift-distance", "PRODUCES")],
     "which 1929 relation tied galaxy recession velocity to distance and underpinned expansion cosmology",
     "hubble 1929 redshift distance expansion universe galaxy recession"),
    # --- 35 ---
    ("The WMAP mission's nine-year data release in 2013 pinned the cosmic microwave background power spectrum tightly enough to fix the age of the universe at 13.77 billion years within sub-percent error.", "reference", "knowledge", False,
     [("WMAP", "project"), ("cosmic microwave background", "concept"), ("13.77 billion years", "concept")],
     [("WMAP", "cosmic microwave background", "APPLIES_TO")],
     "which WMAP nine-year release fixed the cosmic age near 13.77 billion years and when",
     "wmap 2013 cmb spectrum age universe 13 77 billion"),
    # --- 36 ---
    ("ESA's Planck mission delivered a higher-resolution CMB map in 2013 and 2015, tightening cosmological parameters and entrenching the Lambda-CDM model as the concordance picture of structure formation.", "reference", "knowledge", False,
     [("Planck mission", "project"), ("ESA", "organization"), ("Lambda-CDM", "concept"), ("CMB", "concept")],
     [("Planck mission", "Lambda-CDM", "APPLIES_TO")],
     "which ESA mission tightened the CMB map after WMAP and which concordance model did it entrench",
     "planck mission 2013 2015 esa cmb lambda cdm concordance cosmology"),
    # --- 37 ---
    ("Zwicky's 1933 Coma Cluster velocity-dispersion analysis inferred missing mass orders of magnitude beyond luminous matter, the first serious quantitative argument for dark matter even if the term came later.", "problem", "knowledge", False,
     [("Zwicky", "person"), ("Coma Cluster", "place"), ("dark matter", "concept")],
     [("Zwicky", "dark matter", "APPLIES_TO")],
     "which 1933 cluster analysis first quantitatively pointed at missing non-luminous mass",
     "zwicky coma cluster 1933 velocity dispersion dark matter missing"),
    # --- 38 ---
    ("Vera Rubin's 1970s galaxy rotation curves showed flat rotation out to large radii, cementing the dark matter case that most of a galaxy's mass sits in an unseen halo rather than tracking the luminous disk.", "decision", "knowledge", False,
     [("Vera Rubin", "person"), ("galaxy rotation curves", "concept"), ("dark matter", "concept"), ("halo", "concept")],
     [("Vera Rubin", "dark matter", "APPLIES_TO")],
     "which 1970s rotation-curve work forced the dark-matter halo picture onto the community",
     "vera rubin galaxy rotation curve flat 1970s dark matter halo"),
    # --- 39 ---
    ("The 1998 supernova surveys led by Perlmutter, Schmidt, and Riess used type Ia supernovae as standard candles and discovered the expansion of the universe is accelerating, which the community named dark energy.", "decision", "knowledge", False,
     [("Perlmutter", "person"), ("Schmidt", "person"), ("Riess", "person"), ("type Ia supernovae", "concept"), ("dark energy", "concept")],
     [("Perlmutter", "dark energy", "APPLIES_TO"), ("Riess", "dark energy", "APPLIES_TO")],
     "which 1998 supernova teams discovered accelerating expansion and what did they call the culprit",
     "perlmutter schmidt riess 1998 supernova type ia dark energy accelerate"),
    # --- 40 ---
    ("The 2011 Nobel Prize in Physics went to Perlmutter, Schmidt, and Riess for the supernova discovery of accelerating expansion, with the citation specifically naming dark energy as the implied driver.", "fact", "knowledge", False,
     [("Nobel Prize", "concept"), ("Perlmutter", "person"), ("Schmidt", "person"), ("Riess", "person"), ("dark energy", "concept")],
     [("Nobel Prize", "dark energy", "APPLIES_TO")],
     "which 2011 physics Nobel cited dark energy and which three laureates shared it",
     "nobel 2011 perlmutter schmidt riess dark energy supernova accelerate"),
    # --- 41 ---
    ("String theory's first superstring revolution in 1984 was triggered by Green and Schwarz showing anomaly cancellation in type I theory, which suddenly made the framework look like a plausible unifier.", "architecture", "knowledge", False,
     [("String theory", "concept"), ("Green", "person"), ("Schwarz", "person"), ("type I theory", "concept"), ("anomaly cancellation", "concept")],
     [("Green", "anomaly cancellation", "PRODUCES")],
     "which 1984 Green-Schwarz result set off the first superstring revolution and on what grounds",
     "string theory 1984 green schwarz anomaly cancellation type i super"),
    # --- 42 ---
    ("Witten's 1995 M-theory proposal at USC unified the five consistent ten-dimensional superstring theories as limits of an eleven-dimensional framework, kicking off the second superstring revolution.", "architecture", "knowledge", False,
     [("Witten", "person"), ("M-theory", "concept"), ("USC", "organization"), ("superstring", "concept")],
     [("Witten", "M-theory", "PRODUCES")],
     "which 1995 Witten proposal unified five superstring theories under an eleven-dimensional roof",
     "witten m theory 1995 usc superstring eleven dimension unify"),
    # --- 43. noise ---
    ("The department coffee urn has a handwritten sign asking people not to pour cold brew over the heating element and nobody is sure who wrote it.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Dyson's 1951 lectures at Cornell, later circulated as the Advanced Quantum Mechanics notes, trained a generation of American theorists in Feynman-diagram methods before any textbook existed on the subject.", "reference", "knowledge", False,
     [("Dyson", "person"), ("Cornell", "organization"), ("Advanced Quantum Mechanics", "project"), ("Feynman-diagram", "concept")],
     [("Dyson", "Advanced Quantum Mechanics", "PRODUCES")],
     "which 1951 Dyson lecture notes taught Feynman-diagram methods before any textbook existed",
     "dyson 1951 cornell advanced quantum mechanics feynman diagram notes"),
    # --- 45 ---
    ("Weinberg's three-volume Quantum Theory of Fields, published between 1995 and 2000, stands as the reference modern pedagogical treatment of QFT from an S-matrix first perspective.", "reference", "knowledge", False,
     [("Weinberg", "person"), ("Quantum Theory of Fields", "project"), ("QFT", "concept"), ("S-matrix", "concept")],
     [("Weinberg", "Quantum Theory of Fields", "PRODUCES")],
     "which Weinberg three-volume work is the reference modern textbook on quantum field theory",
     "weinberg quantum theory fields 1995 2000 qft s matrix textbook"),
    # --- 46 ---
    ("The community preferred the Copenhagen interpretation as the default teaching convention over Bohm's pilot-wave and Everett's many-worlds, largely on pedagogical simplicity rather than resolved ontological argument.", "preference", "knowledge", False,
     [("Copenhagen interpretation", "concept"), ("Bohm", "person"), ("Everett", "person"), ("many-worlds", "concept")],
     [("Copenhagen interpretation", "many-worlds", "PREFERS")],
     "which interpretation won the default teaching slot over pilot-wave and many-worlds and on what grounds",
     "copenhagen bohm pilot wave everett many worlds teaching default"),
    # --- 47 ---
    ("Feynman preferred path-integral intuition over canonical quantisation when teaching QED, and his three-volume Lectures on Physics from 1963 to 1965 locked that preference into a generation of undergraduates.", "preference", "knowledge", False,
     [("Feynman", "person"), ("path-integral", "concept"), ("canonical quantisation", "concept"), ("Lectures on Physics", "project")],
     [("Feynman", "path-integral", "PREFERS")],
     "which quantisation approach did Feynman prefer in teaching and which lecture series carried it",
     "feynman path integral canonical quantisation lectures physics 1963 1965"),
    # --- 48 ---
    ("Bohr preferred the complementarity framing over hidden-variable narratives, a preference he defended publicly against Einstein across the 1927 and 1930 Solvay Conferences with pedagogical thought experiments.", "preference", "knowledge", False,
     [("Bohr", "person"), ("complementarity", "concept"), ("Einstein", "person"), ("Solvay Conferences", "concept"), ("hidden-variable", "concept")],
     [("Bohr", "complementarity", "PREFERS")],
     "which interpretive stance did Bohr defend against Einstein at the Solvay Conferences",
     "bohr complementarity einstein solvay 1927 1930 hidden variable defend"),
    # --- 49 ---
    ("Einstein preferred a deterministic completion of quantum mechanics and his 1935 EPR paper with Podolsky and Rosen argued the theory was incomplete, framing a problem Bell would later make quantitative.", "preference", "knowledge", False,
     [("Einstein", "person"), ("EPR paper", "project"), ("Podolsky", "person"), ("Rosen", "person"), ("Bell", "person")],
     [("Einstein", "EPR paper", "PRODUCES")],
     "which 1935 Einstein paper framed quantum incompleteness and whose later theorem made it quantitative",
     "einstein epr podolsky rosen 1935 deterministic bell incomplete"),
    # --- 50 ---
    ("The hierarchy problem in the Standard Model — why the Higgs mass sits near 125 GeV rather than the Planck scale — remains unresolved after LHC searches failed to turn up the light supersymmetric partners most naturalness arguments predicted.", "problem", "knowledge", False,
     [("hierarchy problem", "concept"), ("Standard Model", "concept"), ("Higgs mass", "concept"), ("Planck scale", "concept"), ("LHC", "organization"), ("supersymmetric", "concept")],
     [("hierarchy problem", "Standard Model", "APPLIES_TO")],
     "which Standard Model puzzle about the Higgs mass remains open after LHC null results on superpartners",
     "hierarchy problem higgs mass planck scale lhc supersymmetric naturalness"),
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
