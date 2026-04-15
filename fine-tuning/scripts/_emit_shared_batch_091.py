"""One-off emitter for shared-base batch-091 — knowledge domain (chemistry and materials science).

Writes 50 rows with ids shared-04501..04550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_091.tmp.jsonl"
ID_OFFSET = 4500

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Akira Suzuki and Norio Miyaura reported the palladium-catalysed cross-coupling of aryl halides with organoboron reagents in 1979, a reaction later cited in the 2010 Nobel Prize in Chemistry.", "milestone", "knowledge", False,
     [("Akira Suzuki", "person"), ("Norio Miyaura", "person"), ("cross-coupling", "method"), ("aryl halides", "concept"), ("organoboron reagents", "concept"), ("1979", "date")],
     [("cross-coupling", "Akira Suzuki", "AUTHORED_BY"), ("cross-coupling", "Norio Miyaura", "AUTHORED_BY")],
     "which two chemists reported the palladium-catalysed aryl-boron coupling that anchored the 2010 Nobel",
     "Suzuki Miyaura palladium boron aryl halide coupling Nobel year"),
    # --- 2 ---
    ("The Heck reaction, published by Richard Heck in the Journal of Organic Chemistry in 1972, couples aryl halides to alkenes via a palladium cycle and replaced older stoichiometric arylations.", "reference", "knowledge", False,
     [("Heck reaction", "method"), ("Richard Heck", "person"), ("Journal of Organic Chemistry", "publication"), ("1972", "date"), ("aryl halides", "concept"), ("alkenes", "concept"), ("stoichiometric arylations", "method")],
     [("Heck reaction", "Richard Heck", "AUTHORED_BY"), ("Heck reaction", "stoichiometric arylations", "REPLACES")],
     "which 1972 JOC paper described the palladium-cycle arylation of alkenes that superseded stoichiometric routes",
     "Heck palladium aryl alkene coupling JOC year stoichiometric replaced"),
    # --- 3 ---
    ("The Diels-Alder cycloaddition, reported by Otto Diels and Kurt Alder in 1928, forges two sigma bonds in one concerted step and earned the 1950 Nobel Prize in Chemistry.", "milestone", "knowledge", False,
     [("Diels-Alder", "method"), ("Otto Diels", "person"), ("Kurt Alder", "person"), ("1928", "date"), ("1950 Nobel Prize in Chemistry", "event")],
     [("Diels-Alder", "Otto Diels", "AUTHORED_BY"), ("Diels-Alder", "Kurt Alder", "AUTHORED_BY")],
     "which 1928 concerted cycloaddition won its authors the 1950 Nobel in Chemistry",
     "Diels Alder diene dienophile cycloaddition Nobel year"),
    # --- 4 ---
    ("Georg Wittig's 1954 report in Chemische Berichte introduced the phosphorus ylide olefination known as the Wittig reaction and improved on the older Knoevenagel route for stereocontrolled alkene synthesis.", "reference", "knowledge", False,
     [("Georg Wittig", "person"), ("Chemische Berichte", "publication"), ("1954", "date"), ("phosphorus ylide", "concept"), ("Wittig reaction", "method"), ("Knoevenagel", "method")],
     [("Wittig reaction", "Georg Wittig", "AUTHORED_BY"), ("Wittig reaction", "Knoevenagel", "IMPROVES_ON")],
     "which 1954 Chem Ber paper introduced a phosphorus ylide olefination that outperformed Knoevenagel for alkenes",
     "Wittig ylide olefination phosphorus Knoevenagel alkene year"),
    # --- 5 ---
    ("Linus Pauling's The Nature of the Chemical Bond, published by Cornell University Press in 1939, synthesised valence bond theory, electronegativity, and resonance into a single framework.", "reference", "knowledge", False,
     [("Linus Pauling", "person"), ("The Nature of the Chemical Bond", "publication"), ("1939", "date"), ("valence bond theory", "theory"), ("electronegativity", "concept"), ("resonance", "concept")],
     [("The Nature of the Chemical Bond", "Linus Pauling", "AUTHORED_BY")],
     "which 1939 Pauling monograph unified valence bond theory, electronegativity, and resonance",
     "Pauling Nature Chemical Bond valence electronegativity resonance year"),
    # --- 6 ---
    ("Walter Kohn and Lu Jeu Sham's 1965 Physical Review paper recast density functional theory into the self-consistent Kohn-Sham equations that now underpin routine DFT calculations.", "milestone", "knowledge", False,
     [("Walter Kohn", "person"), ("Lu Jeu Sham", "person"), ("Physical Review", "publication"), ("1965", "date"), ("density functional theory", "theory"), ("Kohn-Sham equations", "concept"), ("DFT", "method")],
     [("Kohn-Sham equations", "Walter Kohn", "AUTHORED_BY"), ("DFT", "Kohn-Sham equations", "DEPENDS_ON")],
     "which 1965 PR paper recast DFT into the self-consistent equations used in modern calculations",
     "Kohn Sham DFT density functional self consistent Physical Review year"),
    # --- 7 ---
    ("The B3LYP hybrid functional, combining Becke-88 exchange with Lee-Yang-Parr correlation, became the workhorse of Gaussian calculations after the 1994 Stephens reparametrisation.", "fact", "knowledge", False,
     [("B3LYP", "method"), ("Becke-88", "method"), ("Lee-Yang-Parr", "method"), ("Gaussian", "tool"), ("1994", "date"), ("Stephens", "person")],
     [("B3LYP", "Becke-88", "DEPENDS_ON"), ("B3LYP", "Lee-Yang-Parr", "DEPENDS_ON")],
     "which three-parameter hybrid approximation became the default choice in routine quantum-chemistry jobs",
     "B3LYP Becke LYP Gaussian Stephens reparametrisation hybrid year"),
    # --- 8 ---
    ("ORCA, developed by Frank Neese and distributed freely for academic use since 2000, now challenges commercial packages such as Gaussian for coupled-cluster and multireference work.", "reference", "knowledge", False,
     [("ORCA", "tool"), ("Frank Neese", "person"), ("2000", "date"), ("Gaussian", "tool"), ("coupled-cluster", "method"), ("multireference", "method")],
     [("ORCA", "Frank Neese", "AUTHORED_BY"), ("ORCA", "Gaussian", "IMPROVES_ON")],
     "which free quantum-chemistry code by Frank Neese now rivals Gaussian for coupled-cluster work",
     "ORCA Neese coupled cluster multireference Gaussian free academic"),
    # --- 9 ---
    ("Richard Ernst's Fourier-transform NMR, reported with Weston Anderson in Review of Scientific Instruments in 1966, replaced continuous-wave scanning and won the 1991 Nobel Prize in Chemistry.", "milestone", "knowledge", False,
     [("Richard Ernst", "person"), ("Fourier-transform NMR", "method"), ("Weston Anderson", "person"), ("Review of Scientific Instruments", "publication"), ("1966", "date"), ("continuous-wave scanning", "method"), ("1991 Nobel Prize in Chemistry", "event")],
     [("Fourier-transform NMR", "Richard Ernst", "AUTHORED_BY"), ("Fourier-transform NMR", "continuous-wave scanning", "REPLACES")],
     "which 1966 RSI paper replaced continuous-wave NMR with pulsed FT detection",
     "Ernst Anderson FT NMR pulse continuous wave Nobel year"),
    # --- 10. noise ---
    ("Give me a second, my column just finished eluting and the fraction collector is clicking through.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Kurt Wuthrich's 1982 Journal of Molecular Biology paper on sequential NMR assignment extended protein NMR to solution structures and earned him a share of the 2002 Nobel Prize in Chemistry.", "reference", "knowledge", False,
     [("Kurt Wuthrich", "person"), ("Journal of Molecular Biology", "publication"), ("1982", "date"), ("sequential NMR assignment", "method"), ("protein NMR", "field"), ("2002 Nobel Prize in Chemistry", "event")],
     [("sequential NMR assignment", "Kurt Wuthrich", "AUTHORED_BY")],
     "which 1982 JMB paper by Wuthrich opened solution-structure protein NMR",
     "Wuthrich sequential assignment protein NMR JMB Nobel year"),
    # --- 12 ---
    ("John Fenn's electrospray ionisation, reported in Science in 1989, let mass spectrometry handle intact proteins and largely replaced fast atom bombardment for biomolecular work.", "milestone", "knowledge", False,
     [("John Fenn", "person"), ("electrospray ionisation", "method"), ("Science", "publication"), ("1989", "date"), ("mass spectrometry", "method"), ("fast atom bombardment", "method")],
     [("electrospray ionisation", "John Fenn", "AUTHORED_BY"), ("electrospray ionisation", "fast atom bombardment", "REPLACES")],
     "which 1989 Science paper by Fenn displaced fast atom bombardment for biomolecular mass spec",
     "Fenn electrospray ESI mass spectrometry FAB Science year"),
    # --- 13 ---
    ("Koichi Tanaka's soft laser desorption for macromolecules, published in Rapid Communications in Mass Spectrometry in 1988, seeded the MALDI technique that now dominates peptide fingerprinting.", "reference", "knowledge", False,
     [("Koichi Tanaka", "person"), ("soft laser desorption", "method"), ("Rapid Communications in Mass Spectrometry", "publication"), ("1988", "date"), ("MALDI", "method"), ("peptide fingerprinting", "method")],
     [("MALDI", "soft laser desorption", "BUILDS_ON"), ("soft laser desorption", "Koichi Tanaka", "AUTHORED_BY")],
     "whose 1988 RCMS paper seeded the MALDI method now used for peptide fingerprinting",
     "Tanaka soft laser desorption MALDI peptide RCMS year"),
    # --- 14 ---
    ("Hermann Staudinger's 1920 Berichte paper on macromolecular long-chain structures founded modern polymer science and earned the 1953 Nobel Prize in Chemistry.", "milestone", "knowledge", False,
     [("Hermann Staudinger", "person"), ("Berichte", "publication"), ("1920", "date"), ("macromolecular long-chain structures", "concept"), ("polymer science", "field"), ("1953 Nobel Prize in Chemistry", "event")],
     [("macromolecular long-chain structures", "Hermann Staudinger", "AUTHORED_BY")],
     "which 1920 Berichte paper by Staudinger founded polymer science and drew the 1953 Nobel",
     "Staudinger macromolecules long chain Berichte polymer Nobel year"),
    # --- 15 ---
    ("Karl Ziegler and Giulio Natta's titanium-aluminium catalysts, reported between 1953 and 1955, enabled low-pressure polyethylene and isotactic polypropylene and replaced the older high-pressure ICI process.", "milestone", "knowledge", False,
     [("Karl Ziegler", "person"), ("Giulio Natta", "person"), ("titanium-aluminium catalysts", "concept"), ("1953", "date"), ("1955", "date"), ("polyethylene", "concept"), ("isotactic polypropylene", "concept"), ("high-pressure ICI process", "method")],
     [("titanium-aluminium catalysts", "Karl Ziegler", "AUTHORED_BY"), ("titanium-aluminium catalysts", "Giulio Natta", "AUTHORED_BY"), ("titanium-aluminium catalysts", "high-pressure ICI process", "REPLACES")],
     "whose 1950s titanium catalysts replaced the high-pressure ICI polyethylene process",
     "Ziegler Natta titanium aluminium polyethylene polypropylene ICI years"),
    # --- 16 ---
    ("Paul Flory's Principles of Polymer Chemistry, published by Cornell University Press in 1953, codified statistical thermodynamics of chain molecules and underpinned his 1974 Nobel citation.", "reference", "knowledge", False,
     [("Paul Flory", "person"), ("Principles of Polymer Chemistry", "publication"), ("1953", "date"), ("statistical thermodynamics", "field"), ("1974", "date")],
     [("Principles of Polymer Chemistry", "Paul Flory", "AUTHORED_BY")],
     "which 1953 Flory monograph codified the statistical thermodynamics of polymers",
     "Flory Principles Polymer Chemistry statistical thermodynamics Nobel years"),
    # --- 17 ---
    ("Omar Yaghi's MOF-5, reported in Nature in 1999, became the archetypal metal-organic framework and demonstrated permanent porosity with a surface area exceeding 2900 square metres per gram.", "milestone", "knowledge", False,
     [("Omar Yaghi", "person"), ("MOF-5", "concept"), ("Nature", "publication"), ("1999", "date"), ("metal-organic framework", "concept"), ("permanent porosity", "concept")],
     [("MOF-5", "Omar Yaghi", "AUTHORED_BY"), ("MOF-5", "metal-organic framework", "IS_A")],
     "which 1999 Nature paper by Yaghi introduced the archetypal MOF-5 porous framework",
     "Yaghi MOF-5 Nature porous metal organic framework surface area year"),
    # --- 18 ---
    ("HKUST-1, reported by Chui and co-workers in Science in 1999, pairs copper paddlewheels with trimesate linkers and became the benchmark MOF for CO2 uptake studies.", "reference", "knowledge", False,
     [("HKUST-1", "concept"), ("Chui", "person"), ("Science", "publication"), ("1999", "date"), ("copper paddlewheels", "concept"), ("trimesate linkers", "concept"), ("CO2 uptake", "finding")],
     [("HKUST-1", "Chui", "AUTHORED_BY")],
     "which 1999 Science paper introduced the copper-trimesate MOF benchmark for CO2 uptake",
     "HKUST Chui Science copper trimesate paddlewheel MOF year"),
    # --- 19 ---
    ("Richard Barrer's mid-century synthesis work at Imperial College systematised synthetic zeolites and led to the Mobil ZSM-5 framework later commercialised for catalytic cracking.", "fact", "knowledge", False,
     [("Richard Barrer", "person"), ("Imperial College", "organization"), ("synthetic zeolites", "concept"), ("Mobil", "organization"), ("ZSM-5", "concept"), ("catalytic cracking", "method")],
     [("synthetic zeolites", "Richard Barrer", "AUTHORED_BY"), ("ZSM-5", "Mobil", "AUTHORED_BY")],
     "who at Imperial College systematised zeolite synthesis that later seeded Mobil's ZSM-5",
     "Barrer Imperial zeolite synthesis Mobil ZSM-5 catalytic cracking"),
    # --- 20 ---
    ("Konstantin Novoselov and Andre Geim's 2004 Science paper on mechanical exfoliation of graphite produced the first isolated graphene monolayers and carried the 2010 Nobel Prize in Physics.", "milestone", "knowledge", False,
     [("Konstantin Novoselov", "person"), ("Andre Geim", "person"), ("Science", "publication"), ("2004", "date"), ("mechanical exfoliation", "method"), ("graphene", "concept"), ("2010 Nobel Prize in Physics", "event")],
     [("graphene", "Konstantin Novoselov", "AUTHORED_BY"), ("graphene", "Andre Geim", "AUTHORED_BY")],
     "which 2004 Science paper isolated graphene monolayers by scotch-tape exfoliation",
     "Novoselov Geim graphene exfoliation Science Nobel year"),
    # --- 21 ---
    ("Tsutomu Miyasaka's 2009 JACS report on methylammonium lead iodide as a dye-sensitised absorber seeded the perovskite solar cell field that now challenges silicon for thin-film photovoltaics.", "milestone", "knowledge", False,
     [("Tsutomu Miyasaka", "person"), ("2009", "date"), ("JACS", "publication"), ("methylammonium lead iodide", "concept"), ("perovskite solar cell", "concept"), ("silicon", "concept"), ("thin-film photovoltaics", "field")],
     [("perovskite solar cell", "Tsutomu Miyasaka", "AUTHORED_BY"), ("perovskite solar cell", "silicon", "IMPROVES_ON")],
     "which 2009 JACS paper introduced the methylammonium lead iodide perovskite solar absorber",
     "Miyasaka JACS methylammonium lead iodide perovskite silicon thin film year"),
    # --- 22 ---
    ("John Goodenough's lithium iron phosphate cathode, reported in the Journal of the Electrochemical Society in 1997, now replaces NMC in low-cost electric vehicle packs thanks to thermal stability.", "decision", "knowledge", False,
     [("John Goodenough", "person"), ("lithium iron phosphate", "concept"), ("Journal of the Electrochemical Society", "publication"), ("1997", "date"), ("NMC", "concept"), ("electric vehicle packs", "concept"), ("thermal stability", "finding")],
     [("lithium iron phosphate", "John Goodenough", "AUTHORED_BY"), ("lithium iron phosphate", "NMC", "REPLACES")],
     "which 1997 JES paper introduced the LFP cathode now preferred over NMC in budget EV packs",
     "Goodenough LFP lithium iron phosphate NMC EV JES year"),
    # --- 23 ---
    ("Akira Yoshino's 1985 patent on the lithium-ion cell with a carbonaceous anode and LiCoO2 cathode formed the template that Sony commercialised in 1991 and earned the 2019 Nobel Prize in Chemistry.", "milestone", "knowledge", False,
     [("Akira Yoshino", "person"), ("1985", "date"), ("lithium-ion cell", "concept"), ("carbonaceous anode", "concept"), ("LiCoO2", "concept"), ("Sony", "organization"), ("1991", "date"), ("2019 Nobel Prize in Chemistry", "event")],
     [("lithium-ion cell", "Akira Yoshino", "AUTHORED_BY")],
     "whose 1985 patent set the lithium-ion cell template that Sony commercialised in 1991",
     "Yoshino lithium ion Sony LiCoO2 anode patent commercial Nobel years"),
    # --- 24 ---
    ("Henri Le Chatelier's 1884 principle, published in Comptes rendus, predicts how a chemical system at equilibrium shifts to counter an imposed change in concentration, pressure, or temperature.", "reference", "knowledge", False,
     [("Henri Le Chatelier", "person"), ("1884", "date"), ("Comptes rendus", "publication"), ("chemical system at equilibrium", "concept")],
     [("chemical system at equilibrium", "Henri Le Chatelier", "AUTHORED_BY")],
     "which 1884 Comptes rendus note stated how equilibria respond to imposed perturbations",
     "Le Chatelier equilibrium shift principle Comptes rendus year"),
    # --- 25 ---
    ("Fritz Haber's 1909 ammonia synthesis at 200 bar over osmium catalysts, industrialised by Carl Bosch at BASF, replaced the Birkeland-Eyde arc process and carried Haber's 1918 Nobel Prize in Chemistry.", "milestone", "knowledge", False,
     [("Fritz Haber", "person"), ("1909", "date"), ("ammonia synthesis", "method"), ("Carl Bosch", "person"), ("BASF", "organization"), ("Birkeland-Eyde arc process", "method"), ("1918 Nobel Prize in Chemistry", "event")],
     [("ammonia synthesis", "Fritz Haber", "AUTHORED_BY"), ("ammonia synthesis", "Birkeland-Eyde arc process", "REPLACES")],
     "which 1909 Haber-Bosch catalytic route displaced the Birkeland-Eyde arc process for fixed nitrogen",
     "Haber Bosch BASF ammonia Birkeland Eyde arc Nobel year"),
    # --- 26 ---
    ("IUPAC nomenclature for organic chemistry, first codified at the 1892 Geneva congress and revised in the 1993 Recommendations, standardises systematic names across journals such as JACS and Angewandte Chemie.", "fact", "knowledge", False,
     [("IUPAC nomenclature", "concept"), ("1892", "date"), ("Geneva congress", "event"), ("1993 Recommendations", "publication"), ("JACS", "publication"), ("Angewandte Chemie", "publication")],
     [("1993 Recommendations", "IUPAC nomenclature", "BUILDS_ON")],
     "which 1892 congress and 1993 recommendations set the standard names used by JACS and Angewandte",
     "IUPAC Geneva 1892 1993 nomenclature standard JACS Angewandte"),
    # --- 27 ---
    ("Robert Woodward and Roald Hoffmann's 1965 JACS papers introduced the orbital symmetry rules that now bear their names and unified pericyclic reaction analysis.", "reference", "knowledge", False,
     [("Robert Woodward", "person"), ("Roald Hoffmann", "person"), ("1965", "date"), ("JACS", "publication"), ("orbital symmetry rules", "theory"), ("pericyclic reaction", "concept")],
     [("orbital symmetry rules", "Robert Woodward", "AUTHORED_BY"), ("orbital symmetry rules", "Roald Hoffmann", "AUTHORED_BY")],
     "which 1965 JACS series introduced the Woodward-Hoffmann orbital symmetry rules",
     "Woodward Hoffmann orbital symmetry pericyclic JACS rules year"),
    # --- 28 ---
    ("Elias James Corey's retrosynthetic analysis, articulated in his 1967 Pure and Applied Chemistry essay, reorganised synthesis planning around disconnection logic and won the 1990 Nobel Prize in Chemistry.", "reference", "knowledge", False,
     [("Elias James Corey", "person"), ("retrosynthetic analysis", "method"), ("1967", "date"), ("Pure and Applied Chemistry", "publication"), ("disconnection logic", "concept"), ("1990 Nobel Prize in Chemistry", "event")],
     [("retrosynthetic analysis", "Elias James Corey", "AUTHORED_BY")],
     "whose 1967 Pure and Applied Chemistry essay reframed synthesis around retrosynthetic disconnection",
     "Corey retrosynthetic analysis disconnection PAC Nobel year"),
    # --- 29 ---
    ("Robert Grubbs's ruthenium alkylidene catalyst, reported in JACS in 1992, made olefin metathesis a benchtop technique and replaced Schrock's molybdenum systems for moisture-tolerant work.", "decision", "knowledge", False,
     [("Robert Grubbs", "person"), ("ruthenium alkylidene catalyst", "concept"), ("JACS", "publication"), ("1992", "date"), ("olefin metathesis", "method"), ("Schrock", "person"), ("molybdenum systems", "concept")],
     [("ruthenium alkylidene catalyst", "Robert Grubbs", "AUTHORED_BY"), ("ruthenium alkylidene catalyst", "molybdenum systems", "REPLACES")],
     "which 1992 JACS paper introduced the ruthenium metathesis catalyst preferred over Schrock's molybdenum",
     "Grubbs ruthenium metathesis JACS Schrock molybdenum year"),
    # --- 30 ---
    ("Barry Sharpless's asymmetric dihydroxylation, reported in JACS in 1988 with osmium-cinchona complexes, improves on older chiral-pool routes for enantiopure diols and anchored his 2001 Nobel share.", "reference", "knowledge", False,
     [("Barry Sharpless", "person"), ("asymmetric dihydroxylation", "method"), ("JACS", "publication"), ("1988", "date"), ("osmium-cinchona complexes", "concept"), ("chiral-pool routes", "method"), ("2001", "date")],
     [("asymmetric dihydroxylation", "Barry Sharpless", "AUTHORED_BY"), ("asymmetric dihydroxylation", "chiral-pool routes", "IMPROVES_ON")],
     "which 1988 JACS paper introduced osmium-cinchona asymmetric dihydroxylation",
     "Sharpless asymmetric dihydroxylation osmium cinchona JACS Nobel year"),
    # --- 31 ---
    ("Frances Arnold's directed evolution programme at Caltech, reviewed in Nature in 2001, reframed enzyme engineering around iterative mutation and screening and seeded her 2018 Nobel citation.", "milestone", "knowledge", False,
     [("Frances Arnold", "person"), ("directed evolution", "method"), ("Caltech", "organization"), ("Nature", "publication"), ("2001", "date"), ("enzyme engineering", "field"), ("2018", "date")],
     [("directed evolution", "Frances Arnold", "AUTHORED_BY")],
     "whose Caltech directed-evolution programme earned a 2018 Nobel after the 2001 Nature review",
     "Arnold directed evolution Caltech Nature enzyme engineering Nobel years"),
    # --- 32 ---
    ("Carolyn Bertozzi's 2003 JACS paper on the Staudinger ligation launched bioorthogonal chemistry and led to her share of the 2022 Nobel Prize in Chemistry.", "reference", "knowledge", False,
     [("Carolyn Bertozzi", "person"), ("2003", "date"), ("JACS", "publication"), ("Staudinger ligation", "method"), ("bioorthogonal chemistry", "field"), ("2022 Nobel Prize in Chemistry", "event")],
     [("Staudinger ligation", "Carolyn Bertozzi", "AUTHORED_BY"), ("bioorthogonal chemistry", "Staudinger ligation", "BUILDS_ON")],
     "which 2003 JACS paper launched bioorthogonal Staudinger ligation and led to the 2022 Nobel",
     "Bertozzi Staudinger ligation bioorthogonal JACS Nobel year"),
    # --- 33 ---
    ("Chemical Reviews, a bimonthly ACS journal launched in 1924, publishes comprehensive review articles and now holds one of the highest impact factors in chemistry.", "reference", "knowledge", False,
     [("Chemical Reviews", "publication"), ("ACS", "organization"), ("1924", "date")],
     [("Chemical Reviews", "ACS", "PUBLISHED_IN")],
     "which 1924 ACS journal publishes chemistry's flagship review articles",
     "Chem Rev ACS review journal impact factor chemistry year"),
    # --- 34. noise ---
    ("Wait, is that reflux condenser leaking? I smell something like toluene around my hood.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Nature Materials, launched by Nature Publishing Group in 2002, quickly became the leading venue for perovskite and two-dimensional materials reports, overtaking older Advanced Materials submissions.", "fact", "knowledge", False,
     [("Nature Materials", "publication"), ("Nature Publishing Group", "organization"), ("2002", "date"), ("perovskite", "concept"), ("two-dimensional materials", "concept"), ("Advanced Materials", "publication")],
     [("Nature Materials", "Nature Publishing Group", "PUBLISHED_IN"), ("Nature Materials", "Advanced Materials", "IMPROVES_ON")],
     "which 2002 Nature spinoff overtook Advanced Materials for perovskite and 2D headline reports",
     "Nature Materials NPG perovskite 2D Advanced Materials launch year"),
    # --- 36 ---
    ("Chemical Science, the open-access flagship launched by the Royal Society of Chemistry in 2010, now prefers gold open access over the older subscription route that defined Chem Comm.", "preference", "knowledge", False,
     [("Chemical Science", "publication"), ("Royal Society of Chemistry", "organization"), ("2010", "date"), ("gold open access", "concept"), ("Chem Comm", "publication")],
     [("Chemical Science", "Royal Society of Chemistry", "PUBLISHED_IN"), ("gold open access", "Chem Comm", "PREFERS")],
     "which 2010 RSC flagship prefers gold open access over Chem Comm's subscription route",
     "Chemical Science RSC open access Chem Comm flagship year"),
    # --- 37 ---
    ("Angewandte Chemie International Edition, published by Wiley for the German Chemical Society since 1962, remains a primary venue for rapid cross-coupling and catalysis communications.", "reference", "knowledge", False,
     [("Angewandte Chemie International Edition", "publication"), ("Wiley", "organization"), ("German Chemical Society", "organization"), ("1962", "date"), ("cross-coupling", "method"), ("catalysis", "field")],
     [("Angewandte Chemie International Edition", "Wiley", "PUBLISHED_IN")],
     "which German-rooted Wiley journal has carried flagship cross-coupling work since 1962",
     "Angewandte International Edition Wiley GDCh cross coupling catalysis year"),
    # --- 38 ---
    ("Max Perutz's 1960 Nature paper on haemoglobin's crystal structure, produced at the MRC Laboratory of Molecular Biology, anchored protein crystallography and won him the 1962 Nobel Prize in Chemistry.", "milestone", "knowledge", False,
     [("Max Perutz", "person"), ("1960", "date"), ("Nature", "publication"), ("haemoglobin", "concept"), ("MRC Laboratory of Molecular Biology", "organization"), ("protein crystallography", "field"), ("1962 Nobel Prize in Chemistry", "event")],
     [("haemoglobin", "Max Perutz", "AUTHORED_BY")],
     "whose 1960 Nature paper on haemoglobin crystals won the 1962 Nobel in Chemistry",
     "Perutz haemoglobin MRC LMB Nature crystallography Nobel year"),
    # --- 39 ---
    ("Dorothy Hodgkin solved the structure of vitamin B12 in a 1956 Nature paper, establishing X-ray crystallography as the premier tool for large biomolecules and earning her the 1964 Nobel Prize in Chemistry.", "reference", "knowledge", False,
     [("Dorothy Hodgkin", "person"), ("vitamin B12", "concept"), ("1956", "date"), ("Nature", "publication"), ("X-ray crystallography", "method"), ("1964 Nobel Prize in Chemistry", "event")],
     [("vitamin B12", "Dorothy Hodgkin", "AUTHORED_BY")],
     "whose 1956 Nature paper on vitamin B12 structure earned the 1964 Nobel in Chemistry",
     "Hodgkin vitamin B12 Nature X-ray crystallography Nobel year"),
    # --- 40 ---
    ("Harry Kroto, Richard Smalley, and Robert Curl's 1985 Nature paper on buckminsterfullerene C60 revealed a third allotrope of carbon and earned the 1996 Nobel Prize in Chemistry.", "milestone", "knowledge", False,
     [("Harry Kroto", "person"), ("Richard Smalley", "person"), ("Robert Curl", "person"), ("1985", "date"), ("Nature", "publication"), ("buckminsterfullerene", "concept"), ("C60", "concept"), ("1996 Nobel Prize in Chemistry", "event")],
     [("buckminsterfullerene", "Harry Kroto", "AUTHORED_BY"), ("buckminsterfullerene", "Richard Smalley", "AUTHORED_BY"), ("buckminsterfullerene", "Robert Curl", "AUTHORED_BY")],
     "which 1985 Nature paper unveiled C60 buckminsterfullerene and carried the 1996 Nobel",
     "Kroto Smalley Curl C60 buckminsterfullerene Nature Nobel year"),
    # --- 41 ---
    ("Sumio Iijima's 1991 Nature paper on helical microtubules of graphitic carbon inaugurated the multi-walled carbon nanotube field that later forked into single-walled variants.", "reference", "knowledge", False,
     [("Sumio Iijima", "person"), ("1991", "date"), ("Nature", "publication"), ("helical microtubules", "concept"), ("multi-walled carbon nanotube", "concept"), ("single-walled", "concept")],
     [("multi-walled carbon nanotube", "Sumio Iijima", "AUTHORED_BY")],
     "whose 1991 Nature paper inaugurated the multi-walled carbon nanotube field",
     "Iijima helical microtubules MWCNT SWCNT Nature year"),
    # --- 42 ---
    ("Alan Heeger, Alan MacDiarmid, and Hideki Shirakawa's 1977 Journal of the Chemical Society Chemical Communications paper on iodine-doped polyacetylene opened the field of conducting polymers and carried the 2000 Nobel Prize in Chemistry.", "milestone", "knowledge", False,
     [("Alan Heeger", "person"), ("Alan MacDiarmid", "person"), ("Hideki Shirakawa", "person"), ("1977", "date"), ("Journal of the Chemical Society Chemical Communications", "publication"), ("iodine-doped polyacetylene", "concept"), ("conducting polymers", "field"), ("2000 Nobel Prize in Chemistry", "event")],
     [("iodine-doped polyacetylene", "Alan Heeger", "AUTHORED_BY"), ("iodine-doped polyacetylene", "Alan MacDiarmid", "AUTHORED_BY"), ("iodine-doped polyacetylene", "Hideki Shirakawa", "AUTHORED_BY")],
     "which 1977 JCS Chem Comm paper opened the conducting-polymer field with doped polyacetylene",
     "Heeger MacDiarmid Shirakawa polyacetylene iodine doped Nobel year"),
    # --- 43 ---
    ("George Whitesides's self-assembled monolayers work at Harvard, reviewed in Chemical Reviews in 1996, turned alkanethiols on gold into the standard surface platform for organic electronics and biosensors.", "reference", "knowledge", False,
     [("George Whitesides", "person"), ("self-assembled monolayers", "concept"), ("Harvard", "organization"), ("Chemical Reviews", "publication"), ("1996", "date"), ("alkanethiols on gold", "concept"), ("organic electronics", "field"), ("biosensors", "field")],
     [("self-assembled monolayers", "George Whitesides", "AUTHORED_BY")],
     "whose 1996 Chem Rev review standardised alkanethiol self-assembled monolayers on gold",
     "Whitesides Harvard SAM alkanethiol gold Chem Rev year"),
    # --- 44 ---
    ("Jean-Marie Lehn's supramolecular chemistry programme at Strasbourg, recognised in his 1987 Nobel lecture, reframes molecular recognition around non-covalent interactions and cryptand hosts.", "architecture", "knowledge", False,
     [("Jean-Marie Lehn", "person"), ("supramolecular chemistry", "field"), ("Strasbourg", "place"), ("1987", "date"), ("molecular recognition", "concept"), ("non-covalent interactions", "concept"), ("cryptand hosts", "concept")],
     [("supramolecular chemistry", "Jean-Marie Lehn", "AUTHORED_BY")],
     "whose Strasbourg programme reframed molecular recognition around cryptand hosts",
     "Lehn supramolecular Strasbourg cryptand molecular recognition Nobel year"),
    # --- 45 ---
    ("Donald Cram's 1974 JACS paper on host-guest chemistry with spherands introduced preorganised hosts that improve on Pedersen's crown ether binding constants by several orders of magnitude.", "reference", "knowledge", False,
     [("Donald Cram", "person"), ("1974", "date"), ("JACS", "publication"), ("host-guest chemistry", "field"), ("spherands", "concept"), ("Pedersen", "person"), ("crown ether", "concept")],
     [("spherands", "Donald Cram", "AUTHORED_BY"), ("spherands", "crown ether", "IMPROVES_ON")],
     "which 1974 Cram JACS paper introduced preorganised spherands outperforming crown ethers",
     "Cram host guest spherand Pedersen crown ether JACS year"),
    # --- 46 ---
    ("Michael Gratzel's dye-sensitised solar cell, reported in Nature in 1991 with Brian O'Regan, turned nanoporous titanium dioxide into a cheap photoanode alternative to single-crystal silicon.", "milestone", "knowledge", False,
     [("Michael Gratzel", "person"), ("dye-sensitised solar cell", "concept"), ("Nature", "publication"), ("1991", "date"), ("Brian O'Regan", "person"), ("nanoporous titanium dioxide", "concept"), ("single-crystal silicon", "concept")],
     [("dye-sensitised solar cell", "Michael Gratzel", "AUTHORED_BY"), ("dye-sensitised solar cell", "single-crystal silicon", "IMPROVES_ON")],
     "whose 1991 Nature paper introduced the nanoporous TiO2 dye-sensitised solar cell",
     "Gratzel O'Regan DSSC titanium dioxide Nature silicon year"),
    # --- 47 ---
    ("Ahmed Zewail's femtosecond spectroscopy at Caltech, published in Journal of Chemical Physics in 1987, resolved transition states in real time and earned him the 1999 Nobel Prize in Chemistry.", "reference", "knowledge", False,
     [("Ahmed Zewail", "person"), ("femtosecond spectroscopy", "method"), ("Caltech", "organization"), ("Journal of Chemical Physics", "publication"), ("1987", "date"), ("transition states", "concept"), ("1999 Nobel Prize in Chemistry", "event")],
     [("femtosecond spectroscopy", "Ahmed Zewail", "AUTHORED_BY")],
     "whose 1987 JCP paper resolved transition states in real time and won the 1999 Nobel",
     "Zewail femtochemistry Caltech transition state JCP Nobel year"),
    # --- 48 ---
    ("Nicolas Leonard Sadi Carnot's 1824 Reflexions sur la puissance motrice du feu, published in Paris, framed heat engines around reversible cycles and seeded the later chemical thermodynamics of Gibbs and Helmholtz.", "reference", "knowledge", False,
     [("Nicolas Leonard Sadi Carnot", "person"), ("1824", "date"), ("Reflexions sur la puissance motrice du feu", "publication"), ("Paris", "place"), ("heat engines", "concept"), ("reversible cycles", "concept"), ("chemical thermodynamics", "field"), ("Gibbs", "person"), ("Helmholtz", "person")],
     [("Reflexions sur la puissance motrice du feu", "Nicolas Leonard Sadi Carnot", "AUTHORED_BY")],
     "which 1824 Paris essay framed heat engines around reversible cycles and seeded chemical thermodynamics",
     "Carnot Reflexions puissance motrice feu reversible Paris year"),
    # --- 49 ---
    ("John Pople's Gaussian program, first released in 1970 from Carnegie Mellon, standardised ab initio molecular orbital calculations and underpinned his 1998 Nobel Prize in Chemistry.", "milestone", "knowledge", False,
     [("John Pople", "person"), ("Gaussian", "tool"), ("1970", "date"), ("Carnegie Mellon", "organization"), ("ab initio molecular orbital calculations", "method"), ("1998 Nobel Prize in Chemistry", "event")],
     [("Gaussian", "John Pople", "AUTHORED_BY")],
     "whose 1970 Carnegie Mellon program standardised ab initio molecular orbital calculations",
     "Pople Gaussian Carnegie Mellon ab initio MO Nobel year"),
    # --- 50 ---
    ("Gilbert Newton Lewis's 1916 JACS paper The Atom and the Molecule introduced the shared electron-pair bond and anticipated much of the later Pauling valence bond framework.", "reference", "knowledge", False,
     [("Gilbert Newton Lewis", "person"), ("1916", "date"), ("JACS", "publication"), ("The Atom and the Molecule", "publication"), ("shared electron-pair bond", "concept"), ("Pauling", "person"), ("valence bond", "theory")],
     [("The Atom and the Molecule", "Gilbert Newton Lewis", "AUTHORED_BY"), ("valence bond", "shared electron-pair bond", "BUILDS_ON")],
     "which 1916 JACS paper by Lewis introduced the shared electron-pair bond",
     "Lewis atom molecule electron pair bond JACS valence year"),
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
