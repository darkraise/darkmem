"""One-off emitter for shared-base batch-077 — knowledge domain (biology, ecology, evolution).

Writes 50 rows with ids shared-03801..03850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_077.tmp.jsonl"
ID_OFFSET = 3800

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Charles Darwin's On the Origin of Species, published in 1859, argued that descent with modification under natural selection accounts for the diversity of life.", "reference", "knowledge", False,
     [("Charles Darwin", "person"), ("On the Origin of Species", "publication"), ("1859", "date"), ("natural selection", "theory")],
     [("On the Origin of Species", "Charles Darwin", "AUTHORED_BY")],
     "which 1859 book introduced descent with modification under natural selection",
     "Darwin Origin Species natural selection descent year publication"),
    # --- 2 ---
    ("Alfred Russel Wallace independently formulated natural selection and co-presented it with Darwin at the Linnean Society of London in 1858.", "milestone", "knowledge", False,
     [("Alfred Russel Wallace", "person"), ("natural selection", "theory"), ("Linnean Society of London", "organization"), ("1858", "date")],
     [("natural selection", "Alfred Russel Wallace", "AUTHORED_BY")],
     "which naturalist co-presented natural selection with Darwin in 1858",
     "Wallace Linnean Society joint reading Darwin year"),
    # --- 3 ---
    ("Gregor Mendel's 1866 pea experiments, published as Versuche uber Pflanzenhybriden, established the particulate basis of heredity that later underpinned genetics.", "reference", "knowledge", False,
     [("Gregor Mendel", "person"), ("Versuche uber Pflanzenhybriden", "publication"), ("1866", "date"), ("genetics", "field")],
     [("Versuche uber Pflanzenhybriden", "Gregor Mendel", "AUTHORED_BY")],
     "whose 1866 pea paper grounded the particulate theory of heredity",
     "Mendel pea hybrid Versuche Pflanzenhybriden heredity year"),
    # --- 4 ---
    ("The Modern Synthesis of the 1930s and 1940s, articulated by Fisher, Haldane, Wright, Dobzhansky, Mayr, and Simpson, fused Mendelian genetics with Darwinian selection and improves on earlier saltationist alternatives.", "architecture", "knowledge", False,
     [("Modern Synthesis", "theory"), ("Fisher", "person"), ("Haldane", "person"), ("Wright", "person"), ("Dobzhansky", "person"), ("Mayr", "person"), ("saltationist alternatives", "theory")],
     [("Modern Synthesis", "saltationist alternatives", "IMPROVES_ON")],
     "which mid-century framework merged Mendelian genetics with natural selection",
     "Modern Synthesis Fisher Haldane Wright Dobzhansky Mayr saltationism"),
    # --- 5 ---
    ("Theodosius Dobzhansky's Genetics and the Origin of Species, published in 1937, linked population genetics to speciation and became a cornerstone of the Modern Synthesis.", "reference", "knowledge", False,
     [("Theodosius Dobzhansky", "person"), ("Genetics and the Origin of Species", "publication"), ("1937", "date"), ("population genetics", "field"), ("speciation", "concept")],
     [("Genetics and the Origin of Species", "Theodosius Dobzhansky", "AUTHORED_BY")],
     "which 1937 book bridged population genetics and speciation in the Modern Synthesis",
     "Dobzhansky Genetics Origin Species population genetics year"),
    # --- 6 ---
    ("Ernst Mayr's 1942 Systematics and the Origin of Species formalised the biological species concept centred on reproductive isolation.", "reference", "knowledge", False,
     [("Ernst Mayr", "person"), ("Systematics and the Origin of Species", "publication"), ("1942", "date"), ("biological species concept", "theory"), ("reproductive isolation", "concept")],
     [("Systematics and the Origin of Species", "Ernst Mayr", "AUTHORED_BY"), ("biological species concept", "Ernst Mayr", "AUTHORED_BY")],
     "whose 1942 book codified species as reproductively isolated populations",
     "Mayr Systematics species concept reproductive isolation year"),
    # --- 7 ---
    ("Motoo Kimura's neutral theory of molecular evolution, introduced in 1968, argues that most nucleotide substitutions are effectively neutral and drift-driven rather than selected.", "reference", "knowledge", False,
     [("Motoo Kimura", "person"), ("neutral theory of molecular evolution", "theory"), ("1968", "date"), ("drift", "concept")],
     [("neutral theory of molecular evolution", "Motoo Kimura", "AUTHORED_BY")],
     "which 1968 theory repositioned most molecular variation as drift rather than selection",
     "Kimura neutral theory molecular evolution drift year"),
    # --- 8 ---
    ("In molecular contexts the neutral theory replaces strict panselectionism as the default null model for sequence divergence.", "decision", "knowledge", False,
     [("neutral theory", "theory"), ("panselectionism", "theory"), ("sequence divergence", "concept")],
     [("neutral theory", "panselectionism", "REPLACES")],
     "which null model displaced strict panselectionism at the molecular level",
     "neutral theory replaces panselectionism molecular null model"),
    # --- 9 ---
    ("William D. Hamilton's 1964 papers in the Journal of Theoretical Biology introduced kin selection and the inclusive fitness inequality known as Hamilton's rule.", "reference", "knowledge", False,
     [("William D. Hamilton", "person"), ("Journal of Theoretical Biology", "publication"), ("1964", "date"), ("kin selection", "theory"), ("Hamilton's rule", "theory")],
     [("kin selection", "William D. Hamilton", "AUTHORED_BY"), ("Hamilton's rule", "William D. Hamilton", "AUTHORED_BY"), ("Hamilton's rule", "Journal of Theoretical Biology", "PUBLISHED_IN")],
     "which theoretical biologist first formalised relatedness-weighted altruism in a 1964 JTB pair of papers",
     "Hamilton relatedness altruism inequality JTB twin paper"),
    # --- 10. noise ---
    ("Let me re-check that generation time against the lab notebook before I quote the figure.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("George C. Williams's Adaptation and Natural Selection, published in 1966, tightened the case for gene-level selection and pushed back against naive group selection.", "reference", "knowledge", False,
     [("George C. Williams", "person"), ("Adaptation and Natural Selection", "publication"), ("1966", "date"), ("gene-level selection", "theory"), ("group selection", "theory")],
     [("Adaptation and Natural Selection", "George C. Williams", "AUTHORED_BY"), ("gene-level selection", "group selection", "REPLACES")],
     "which 1966 book argued for gene-level selection over naive group selection",
     "Williams Adaptation Natural Selection gene group level year"),
    # --- 12 ---
    ("Lynn Margulis's 1967 paper on the origin of mitosing cells revived endosymbiotic theory, claiming mitochondria and chloroplasts descend from engulfed prokaryotes.", "reference", "knowledge", False,
     [("Lynn Margulis", "person"), ("endosymbiotic theory", "theory"), ("1967", "date"), ("mitochondria", "concept"), ("chloroplasts", "concept")],
     [("endosymbiotic theory", "Lynn Margulis", "AUTHORED_BY")],
     "who revived endosymbiotic theory for the origin of mitochondria and chloroplasts",
     "Margulis endosymbiotic mitochondria chloroplast prokaryote year"),
    # --- 13 ---
    ("Stephen Jay Gould and Niles Eldredge's 1972 punctuated equilibria hypothesis improves on strict phyletic gradualism by modelling speciation as rapid bursts at cladogenesis.", "reference", "knowledge", False,
     [("Stephen Jay Gould", "person"), ("Niles Eldredge", "person"), ("punctuated equilibria", "theory"), ("1972", "date"), ("phyletic gradualism", "theory")],
     [("punctuated equilibria", "Stephen Jay Gould", "AUTHORED_BY"), ("punctuated equilibria", "phyletic gradualism", "IMPROVES_ON")],
     "which 1972 hypothesis recast speciation as rapid bursts against gradualism",
     "Eldredge Gould punctuated equilibria gradualism cladogenesis year"),
    # --- 14 ---
    ("John Maynard Smith and George Price's 1973 Nature paper introduced the evolutionarily stable strategy, embedding game theory inside population biology.", "reference", "knowledge", False,
     [("John Maynard Smith", "person"), ("George Price", "person"), ("Nature", "publication"), ("1973", "date"), ("evolutionarily stable strategy", "theory")],
     [("evolutionarily stable strategy", "John Maynard Smith", "AUTHORED_BY"), ("evolutionarily stable strategy", "Nature", "PUBLISHED_IN")],
     "which pair of authors imported game-theoretic equilibria into population biology in a 1973 journal paper",
     "Maynard Smith Price ESS game theory evolutionary equilibrium Nature"),
    # --- 15 ---
    ("Carl Woese's 1977 PNAS paper on ribosomal RNA phylogenetics established Archaea as a third domain of life alongside Bacteria and Eukarya.", "milestone", "knowledge", False,
     [("Carl Woese", "person"), ("PNAS", "publication"), ("1977", "date"), ("phylogenetics", "field"), ("Archaea", "concept"), ("Bacteria", "concept"), ("Eukarya", "concept")],
     [("Archaea", "Carl Woese", "AUTHORED_BY"), ("Archaea", "PNAS", "PUBLISHED_IN")],
     "which 1977 rRNA paper established Archaea as a third domain of life",
     "Woese Archaea rRNA PNAS three domain year"),
    # --- 16 ---
    ("Niche construction theory, developed by Odling-Smee, Laland, and Feldman in their 2003 monograph, treats organisms as active modifiers of their selective environments.", "reference", "knowledge", False,
     [("Niche construction theory", "theory"), ("Odling-Smee", "person"), ("Laland", "person"), ("Feldman", "person"), ("2003", "date")],
     [("Niche construction theory", "Laland", "AUTHORED_BY")],
     "which 2003 framework casts organisms as builders of their own evolutionary pressures",
     "Odling Smee Laland Feldman niche building monograph"),
    # --- 17 ---
    ("Robert T. Paine's 1966 Pisaster removal experiment on Washington's rocky shore introduced the keystone species concept through trophic cascades.", "milestone", "knowledge", False,
     [("Robert T. Paine", "person"), ("Pisaster", "concept"), ("Washington", "place"), ("1966", "date"), ("keystone species", "concept"), ("trophic cascades", "concept")],
     [("keystone species", "Robert T. Paine", "AUTHORED_BY")],
     "whose 1966 starfish removal experiment produced the keystone species idea",
     "Paine Pisaster Washington intertidal keystone trophic cascade year"),
    # --- 18 ---
    ("The 1995 reintroduction of gray wolves into Yellowstone National Park is a canonical case of a trophic cascade restoring riparian vegetation through elk behaviour shifts.", "milestone", "knowledge", False,
     [("gray wolves", "concept"), ("Yellowstone National Park", "place"), ("1995", "date"), ("trophic cascade", "concept"), ("elk", "concept")],
     [("gray wolves", "Yellowstone National Park", "LOCATED_IN"), ("gray wolves", "trophic cascade", "CAUSES")],
     "which 1995 reintroduction produced a trophic cascade across Yellowstone",
     "Yellowstone wolf reintroduction elk riparian cascade year"),
    # --- 19 ---
    ("Robert MacArthur and E. O. Wilson's 1967 Theory of Island Biogeography modelled species richness as a dynamic equilibrium between immigration and extinction.", "reference", "knowledge", False,
     [("Robert MacArthur", "person"), ("E. O. Wilson", "person"), ("Theory of Island Biogeography", "publication"), ("1967", "date"), ("species richness", "concept")],
     [("Theory of Island Biogeography", "Robert MacArthur", "AUTHORED_BY")],
     "which 1967 monograph framed island species richness as immigration-extinction balance",
     "MacArthur Wilson island biogeography immigration extinction year"),
    # --- 20 ---
    ("Eugene P. Odum's Fundamentals of Ecology, first issued in 1953, reframed ecology around ecosystem energetics and nutrient cycling.", "reference", "knowledge", False,
     [("Eugene P. Odum", "person"), ("Fundamentals of Ecology", "publication"), ("1953", "date"), ("ecosystem energetics", "concept"), ("nutrient cycling", "concept")],
     [("Fundamentals of Ecology", "Eugene P. Odum", "AUTHORED_BY")],
     "which 1953 textbook reoriented ecology around ecosystem energetics",
     "Odum textbook biosphere trophic flow nutrient cycle reorientation"),
    # --- 21 ---
    ("Ecological stoichiometry, systematised by Sterner and Elser in their 2002 Princeton monograph, tracks the balance of carbon, nitrogen, and phosphorus through food webs.", "reference", "knowledge", False,
     [("Ecological stoichiometry", "theory"), ("Sterner", "person"), ("Elser", "person"), ("2002", "date"), ("carbon", "concept"), ("nitrogen", "concept"), ("phosphorus", "concept")],
     [("Ecological stoichiometry", "Sterner", "AUTHORED_BY")],
     "which 2002 monograph formalised ecological stoichiometry of C, N, and P",
     "Sterner Elser ecological stoichiometry CNP food web year"),
    # --- 22 ---
    ("The Amazon rainforest is Earth's largest tropical biome and sustains an estimated ten percent of described species within the Neotropical realm.", "fact", "knowledge", False,
     [("Amazon rainforest", "place"), ("tropical biome", "concept"), ("Neotropical realm", "place")],
     [("Amazon rainforest", "Neotropical realm", "LOCATED_IN")],
     "which tropical biome holds roughly a tenth of described species in the Neotropics",
     "Amazon rainforest tropical biome Neotropical species richness"),
    # --- 23 ---
    ("The Serengeti grassland biome of East Africa sustains the annual wildebeest migration that shapes regional fire regimes and soil nutrient fluxes.", "fact", "knowledge", False,
     [("Serengeti grassland", "place"), ("East Africa", "place"), ("wildebeest migration", "event"), ("fire regimes", "concept")],
     [("Serengeti grassland", "East Africa", "LOCATED_IN"), ("wildebeest migration", "fire regimes", "CAUSES")],
     "which East African savanna hosts the yearly ungulate migration that controls fire and nutrient flux",
     "Serengeti Tanzania wildebeest savanna fire nutrient flux"),
    # --- 24 ---
    ("Escherichia coli K-12 strain MG1655 remains a reference lab organism for molecular biology, with its 4.6 megabase genome fully sequenced in 1997.", "reference", "knowledge", False,
     [("Escherichia coli", "concept"), ("MG1655", "concept"), ("1997", "date"), ("molecular biology", "field")],
     [("MG1655", "Escherichia coli", "IS_A")],
     "which E. coli reference strain had its genome fully sequenced in 1997",
     "E coli K12 MG1655 reference lab organism genome year"),
    # --- 25 ---
    ("Caenorhabditis elegans became the first multicellular organism with a fully sequenced genome when the Science consortium paper appeared in 1998.", "milestone", "knowledge", False,
     [("Caenorhabditis elegans", "concept"), ("Science", "publication"), ("1998", "date"), ("fully sequenced genome", "finding")],
     [("fully sequenced genome", "Science", "PUBLISHED_IN"), ("Caenorhabditis elegans", "fully sequenced genome", "HAS_PART")],
     "which nematode was the first multicellular organism with a complete genome in 1998",
     "C elegans nematode first multicellular genome Science year"),
    # --- 26 ---
    ("Sydney Brenner's 1974 Genetics paper established Caenorhabditis elegans as a tractable model for developmental biology and neurobiology.", "reference", "knowledge", False,
     [("Sydney Brenner", "person"), ("Genetics", "publication"), ("1974", "date"), ("Caenorhabditis elegans", "concept"), ("developmental biology", "field")],
     [("Caenorhabditis elegans", "Sydney Brenner", "AUTHORED_BY"), ("Genetics", "Sydney Brenner", "AUTHORED_BY")],
     "whose 1974 paper installed C. elegans as a model organism for development",
     "Brenner C elegans Genetics 1974 model organism development"),
    # --- 27 ---
    ("Thomas Hunt Morgan's Drosophila melanogaster work at Columbia University's Fly Room, culminating in the 1915 Mechanism of Mendelian Heredity, linked genes to chromosomes.", "reference", "knowledge", False,
     [("Thomas Hunt Morgan", "person"), ("Drosophila melanogaster", "concept"), ("Columbia University", "organization"), ("Fly Room", "place"), ("Mechanism of Mendelian Heredity", "publication"), ("1915", "date")],
     [("Mechanism of Mendelian Heredity", "Thomas Hunt Morgan", "AUTHORED_BY"), ("Fly Room", "Columbia University", "LOCATED_IN")],
     "whose Fly Room work linked Drosophila genes to chromosomes in 1915",
     "Morgan Drosophila Columbia Fly Room Mendelian heredity year"),
    # --- 28 ---
    ("Arabidopsis thaliana became the first plant with a fully sequenced genome when the Arabidopsis Genome Initiative published in Nature in 2000.", "milestone", "knowledge", False,
     [("Arabidopsis thaliana", "concept"), ("Arabidopsis Genome Initiative", "organization"), ("Nature", "publication"), ("2000", "date")],
     [("Arabidopsis thaliana", "Arabidopsis Genome Initiative", "AUTHORED_BY"), ("Arabidopsis Genome Initiative", "Nature", "PUBLISHED_IN")],
     "which plant was first to have a fully sequenced genome in 2000",
     "Arabidopsis thaliana first plant genome Nature AGI year"),
    # --- 29 ---
    ("Jennifer Doudna and Emmanuelle Charpentier's 2012 Science paper demonstrated programmable Cas9 cleavage of DNA via a guide RNA, launching CRISPR genome editing.", "milestone", "knowledge", False,
     [("Jennifer Doudna", "person"), ("Emmanuelle Charpentier", "person"), ("Science", "publication"), ("2012", "date"), ("Cas9", "concept"), ("CRISPR", "technology")],
     [("Cas9", "Jennifer Doudna", "AUTHORED_BY"), ("Cas9", "Emmanuelle Charpentier", "AUTHORED_BY"), ("Cas9", "Science", "PUBLISHED_IN")],
     "which 2012 Science paper demonstrated programmable Cas9 DNA cleavage",
     "Doudna Charpentier Science Cas9 CRISPR guide RNA year"),
    # --- 30 ---
    ("CRISPR-Cas9 editing has largely replaced zinc-finger nucleases and TALENs in research labs because programmable guide RNAs avoid the bespoke protein engineering required by earlier platforms.", "decision", "knowledge", False,
     [("CRISPR-Cas9", "technology"), ("zinc-finger nucleases", "technology"), ("TALENs", "technology"), ("guide RNAs", "concept")],
     [("CRISPR-Cas9", "zinc-finger nucleases", "REPLACES"), ("CRISPR-Cas9", "TALENs", "REPLACES")],
     "which genome-editing platform displaced TALENs and zinc-finger nucleases in research",
     "CRISPR Cas9 TALEN zinc finger nuclease replaces editing"),
    # --- 31 ---
    ("Feng Zhang's January 2013 Science paper demonstrated CRISPR-Cas9 editing in mammalian cells at the Broad Institute, extending Doudna and Charpentier's biochemistry to human cell lines.", "milestone", "knowledge", False,
     [("Feng Zhang", "person"), ("Science", "publication"), ("2013", "date"), ("CRISPR-Cas9", "technology"), ("Broad Institute", "organization"), ("mammalian cells", "concept")],
     [("CRISPR-Cas9", "Feng Zhang", "AUTHORED_BY"), ("Feng Zhang", "Broad Institute", "WORKS_AT")],
     "which January 2013 paper extended CRISPR-Cas9 editing into mammalian cells",
     "Zhang Broad Institute Science mammalian CRISPR Cas9 year"),
    # --- 32 ---
    ("The Human Microbiome Project, funded by the NIH Common Fund from 2007 and reported in Nature in 2012, catalogued microbial communities across sixteen body sites in 242 adults.", "milestone", "knowledge", False,
     [("Human Microbiome Project", "project"), ("NIH Common Fund", "organization"), ("2007", "date"), ("Nature", "publication"), ("2012", "date")],
     [("Human Microbiome Project", "NIH Common Fund", "WORKS_AT"), ("Human Microbiome Project", "Nature", "PUBLISHED_IN")],
     "which NIH project catalogued microbial communities across sixteen human body sites",
     "Human Microbiome Project NIH Common Fund Nature body sites year"),
    # --- 33 ---
    ("The 2006 Gordon lab paper in Nature showed that obese mice harbour gut microbiota with elevated energy-harvest capacity, launching microbiome-metabolism research.", "reference", "knowledge", False,
     [("Gordon lab", "organization"), ("Nature", "publication"), ("2006", "date"), ("obese mice", "concept"), ("gut microbiota", "concept"), ("energy-harvest capacity", "finding")],
     [("energy-harvest capacity", "Gordon lab", "AUTHORED_BY"), ("energy-harvest capacity", "Nature", "PUBLISHED_IN")],
     "which 2006 Nature paper linked obesity in mice to increased microbial energy harvest",
     "Gordon lab obese mice gut microbiota energy harvest year"),
    # --- 34. noise ---
    ("Hmm, I should re-check whether that field site is in the 2019 or 2020 sampling cohort.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Willi Hennig's 1966 Phylogenetic Systematics argued that classifications should track shared derived characters, founding the cladistic method that replaces phenetic clustering.", "reference", "knowledge", False,
     [("Willi Hennig", "person"), ("Phylogenetic Systematics", "publication"), ("1966", "date"), ("cladistic method", "method"), ("phenetic clustering", "method")],
     [("Phylogenetic Systematics", "Willi Hennig", "AUTHORED_BY"), ("cladistic method", "phenetic clustering", "REPLACES")],
     "whose 1966 book founded cladistics on shared derived characters",
     "Hennig Phylogenetic Systematics cladistics phenetics synapomorphy year"),
    # --- 36 ---
    ("Joseph Felsenstein's 1981 paper introduced the maximum likelihood algorithm for inferring phylogenies from DNA sequences under an explicit substitution model.", "reference", "knowledge", False,
     [("Joseph Felsenstein", "person"), ("maximum likelihood algorithm", "algorithm"), ("1981", "date"), ("phylogenies", "concept")],
     [("maximum likelihood algorithm", "Joseph Felsenstein", "AUTHORED_BY")],
     "whose 1981 paper introduced maximum likelihood phylogeny inference",
     "Felsenstein maximum likelihood phylogeny DNA substitution year"),
    # --- 37 ---
    ("RAxML, maintained by Alexandros Stamatakis since 2005, became a widely used tool for maximum likelihood phylogenetic inference on large sequence alignments.", "fact", "knowledge", False,
     [("RAxML", "tool"), ("Alexandros Stamatakis", "person"), ("2005", "date"), ("maximum likelihood phylogenetic inference", "method")],
     [("RAxML", "Alexandros Stamatakis", "AUTHORED_BY")],
     "which tool became standard for maximum likelihood phylogenetic inference since 2005",
     "RAxML Stamatakis maximum likelihood phylogeny software year"),
    # --- 38 ---
    ("Mark Pagel's BayesTraits framework applies Bayesian inference to phylogenetic comparative methods, improving on parsimony ancestral-state reconstruction.", "reference", "knowledge", False,
     [("Mark Pagel", "person"), ("BayesTraits", "tool"), ("Bayesian inference", "method"), ("parsimony ancestral-state reconstruction", "method")],
     [("BayesTraits", "Mark Pagel", "AUTHORED_BY"), ("BayesTraits", "parsimony ancestral-state reconstruction", "IMPROVES_ON")],
     "whose software suite brought probabilistic posterior reconstruction to comparative phylogenetics",
     "Pagel posterior comparative suite trait reconstruction software"),
    # --- 39 ---
    ("The 2010 Science paper from the Neanderthal Genome Consortium, led by Svante Paabo at the Max Planck Institute for Evolutionary Anthropology, showed that non-African humans carry one to four percent Neanderthal DNA.", "milestone", "knowledge", False,
     [("Science", "publication"), ("2010", "date"), ("Neanderthal Genome Consortium", "organization"), ("Svante Paabo", "person"), ("Max Planck Institute for Evolutionary Anthropology", "organization"), ("Neanderthal DNA", "finding")],
     [("Neanderthal Genome Consortium", "Svante Paabo", "AUTHORED_BY"), ("Neanderthal DNA", "Science", "PUBLISHED_IN"), ("Svante Paabo", "Max Planck Institute for Evolutionary Anthropology", "WORKS_AT")],
     "which 2010 Science paper reported Neanderthal admixture in non-African humans",
     "Paabo Neanderthal genome Science Max Planck admixture year"),
    # --- 40 ---
    ("Francis Collins and the International Human Genome Sequencing Consortium published the finished human reference sequence in Nature in 2004, improving on the 2001 draft assembly.", "milestone", "knowledge", False,
     [("Francis Collins", "person"), ("International Human Genome Sequencing Consortium", "organization"), ("Nature", "publication"), ("2004", "date"), ("human reference sequence", "finding"), ("draft assembly", "finding")],
     [("human reference sequence", "International Human Genome Sequencing Consortium", "AUTHORED_BY"), ("human reference sequence", "Nature", "PUBLISHED_IN"), ("human reference sequence", "draft assembly", "IMPROVES_ON")],
     "which 2004 Nature paper finalised the human reference genome over the 2001 draft",
     "Collins IHGSC finished human reference genome Nature year"),
    # --- 41 ---
    ("The 2013 Cell paper by Chen, Fischbach, and colleagues characterised the biosynthetic gene cluster landscape of the human microbiome across thousands of metagenomes.", "reference", "knowledge", False,
     [("Cell", "publication"), ("2013", "date"), ("Chen", "person"), ("Fischbach", "person"), ("biosynthetic gene cluster", "concept"), ("human microbiome", "concept")],
     [("biosynthetic gene cluster", "Cell", "PUBLISHED_IN"), ("biosynthetic gene cluster", "Fischbach", "AUTHORED_BY")],
     "which 2013 Cell paper mapped biosynthetic gene clusters across the human microbiome",
     "Chen Fischbach Cell biosynthetic gene cluster microbiome year"),
    # --- 42 ---
    ("The California condor recovery programme brought the species back from 27 surviving individuals in 1987 to over 500 birds by 2020 through captive breeding at the San Diego Zoo.", "milestone", "knowledge", False,
     [("California condor", "concept"), ("1987", "date"), ("2020", "date"), ("captive breeding", "method"), ("San Diego Zoo", "organization")],
     [("California condor", "San Diego Zoo", "LOCATED_IN"), ("captive breeding", "California condor", "CAUSES")],
     "which conservation programme rebuilt the California condor from 27 birds in 1987",
     "California condor captive breeding San Diego Zoo recovery years"),
    # --- 43 ---
    ("Chytridiomycosis, caused by Batrachochytrium dendrobatidis, has driven global amphibian declines documented in the 2019 Science paper by Scheele and colleagues.", "problem", "knowledge", False,
     [("Chytridiomycosis", "concept"), ("Batrachochytrium dendrobatidis", "concept"), ("Science", "publication"), ("2019", "date"), ("Scheele", "person"), ("amphibian declines", "finding")],
     [("Batrachochytrium dendrobatidis", "Chytridiomycosis", "CAUSES"), ("amphibian declines", "Science", "PUBLISHED_IN"), ("amphibian declines", "Scheele", "AUTHORED_BY")],
     "which fungal pathogen drives the global amphibian declines reported in 2019 Science",
     "Bd chytrid amphibian decline Scheele Science year"),
    # --- 44 ---
    ("Peter and Rosemary Grant's long-term Daphne Major finches study, summarised in their 2014 book 40 Years of Evolution, documents rapid natural selection on beak morphology in real time.", "reference", "knowledge", False,
     [("Peter and Rosemary Grant", "person"), ("Daphne Major", "place"), ("40 Years of Evolution", "publication"), ("2014", "date"), ("beak morphology", "concept")],
     [("40 Years of Evolution", "Peter and Rosemary Grant", "AUTHORED_BY")],
     "whose Daphne Major finch study documents rapid selection on beak morphology",
     "Grant Daphne Major finch beak selection 40 years book"),
    # --- 45 ---
    ("Richard Lenski's Long-Term Evolution Experiment, running in E. coli at Michigan State University since 1988, passed 75,000 generations and documented a citrate utilisation trait around generation 31,500.", "milestone", "knowledge", False,
     [("Richard Lenski", "person"), ("Long-Term Evolution Experiment", "project"), ("E. coli", "concept"), ("Michigan State University", "organization"), ("1988", "date"), ("citrate utilisation", "finding")],
     [("Long-Term Evolution Experiment", "Richard Lenski", "AUTHORED_BY"), ("Long-Term Evolution Experiment", "Michigan State University", "LOCATED_IN")],
     "whose long-term E. coli experiment documented citrate utilisation evolution",
     "Lenski LTEE E coli Michigan State citrate year"),
    # --- 46 ---
    ("Svante Paabo's 2008 Cell paper reported a draft Neanderthal mitochondrial genome, preceding the full nuclear genome by two years.", "reference", "knowledge", False,
     [("Svante Paabo", "person"), ("Cell", "publication"), ("2008", "date"), ("Neanderthal mitochondrial genome", "finding")],
     [("Neanderthal mitochondrial genome", "Svante Paabo", "AUTHORED_BY"), ("Neanderthal mitochondrial genome", "Cell", "PUBLISHED_IN")],
     "which 2008 journal article first presented a draft archaic hominin mitochondrial assembly",
     "Paabo archaic hominin mtDNA draft assembly journal"),
    # --- 47 ---
    ("Jane Lubchenco's rocky-intertidal experiments in New England during the late 1970s clarified how herbivore preference and competition jointly structure algal communities.", "reference", "knowledge", False,
     [("Jane Lubchenco", "person"), ("rocky-intertidal experiments", "method"), ("New England", "place"), ("1970s", "date"), ("algal communities", "concept")],
     [("rocky-intertidal experiments", "Jane Lubchenco", "AUTHORED_BY"), ("rocky-intertidal experiments", "New England", "LOCATED_IN")],
     "whose New England intertidal experiments dissected herbivory and competition in algal communities",
     "Lubchenco New England intertidal herbivore algal decade"),
    # --- 48 ---
    ("Carl Bergstrom and colleagues' 2008 PLoS Biology paper formalised the evolution of virulence in horizontally transmitted pathogens using kin selection arguments.", "reference", "knowledge", False,
     [("Carl Bergstrom", "person"), ("PLoS Biology", "publication"), ("2008", "date"), ("evolution of virulence", "theory"), ("kin selection", "theory")],
     [("evolution of virulence", "Carl Bergstrom", "AUTHORED_BY"), ("evolution of virulence", "PLoS Biology", "PUBLISHED_IN")],
     "which 2008 PLoS Biology paper used kin selection to model virulence evolution",
     "Bergstrom virulence evolution PLoS Biology kin selection year"),
    # --- 49 ---
    ("David Tilman's resource-ratio hypothesis, introduced in Resource Competition and Community Structure in 1982, improves on Lotka-Volterra competition models by grounding coexistence in R-star values.", "reference", "knowledge", False,
     [("David Tilman", "person"), ("Resource Competition and Community Structure", "publication"), ("1982", "date"), ("resource-ratio hypothesis", "theory"), ("Lotka-Volterra competition models", "theory")],
     [("Resource Competition and Community Structure", "David Tilman", "AUTHORED_BY"), ("resource-ratio hypothesis", "Lotka-Volterra competition models", "IMPROVES_ON")],
     "whose 1982 monograph improved on Lotka-Volterra via the resource-ratio hypothesis",
     "Tilman resource competition R star Lotka Volterra year"),
    # --- 50 ---
    ("Simon Levin's 1992 MacArthur Award lecture, The Problem of Pattern and Scale in Ecology, argued that ecological inference must explicitly reconcile processes operating at different spatial and temporal scales.", "reference", "knowledge", False,
     [("Simon Levin", "person"), ("The Problem of Pattern and Scale in Ecology", "publication"), ("1992", "date"), ("ecological inference", "concept")],
     [("The Problem of Pattern and Scale in Ecology", "Simon Levin", "AUTHORED_BY")],
     "whose 1992 MacArthur lecture framed the pattern-and-scale problem in ecology",
     "Levin MacArthur pattern scale ecology lecture year"),
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
