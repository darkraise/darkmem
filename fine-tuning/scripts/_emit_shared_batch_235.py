"""One-off emitter for shared-base batch-235 — knowledge domain (history of biology and key discoveries).

Writes 50 rows to data/v2/shared/batch_235.tmp.jsonl with ids shared-11701..11750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_235.tmp.jsonl"
ID_OFFSET = 11700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Charles Darwin published On the Origin of Species in 1859, laying out natural selection as the mechanism that shaped the tree of life; the book drew on Galapagos finches and years of pigeon-breeding notes.", "reference", "knowledge", False,
     [("Charles Darwin", "person"), ("On the Origin of Species", "project"), ("1859", "date"), ("natural selection", "concept"), ("Galapagos finches", "concept")],
     [("Charles Darwin", "On the Origin of Species", "PRODUCES"), ("On the Origin of Species", "natural selection", "APPLIES_TO")],
     "which 1859 book introduced the mechanism of natural selection and what field observations underpinned it",
     "darwin origin species natural selection galapagos finch 1859 pigeon"),
    # --- 2 ---
    ("Alfred Russel Wallace independently arrived at natural selection from fieldwork in the Malay Archipelago and mailed his 1858 manuscript to Darwin, which triggered the joint Linnean Society presentation.", "fact", "knowledge", False,
     [("Alfred Russel Wallace", "person"), ("Malay Archipelago", "concept"), ("Linnean Society", "organization"), ("1858", "date")],
     [("Alfred Russel Wallace", "Linnean Society", "APPLIES_TO")],
     "how did Wallace's parallel discovery of natural selection reach the scientific community in 1858",
     "wallace malay archipelago linnean society 1858 darwin joint paper"),
    # --- 3 ---
    ("Gregor Mendel crossed pea plants in the Brno monastery garden from 1856 to 1863 and published the ratios in 1866; his work sat ignored for 34 years until three botanists rediscovered it in 1900.", "milestone", "knowledge", False,
     [("Gregor Mendel", "person"), ("Brno", "place"), ("1866", "date"), ("1900", "date"), ("pea plants", "concept")],
     [("Gregor Mendel", "pea plants", "APPLIES_TO")],
     "which monk ran the pea-plant crosses that founded genetics and when was the work rediscovered",
     "mendel pea brno monastery 1866 1900 rediscovery ratio genetics"),
    # --- 4 ---
    ("Thomas Hunt Morgan's fly room at Columbia University mapped Drosophila genes to chromosomes from 1910 onward; the white-eyed mutant male tied inheritance to the X chromosome.", "architecture", "knowledge", False,
     [("Thomas Hunt Morgan", "person"), ("Columbia University", "organization"), ("Drosophila", "concept"), ("X chromosome", "concept"), ("white-eyed mutant", "concept")],
     [("Thomas Hunt Morgan", "Drosophila", "APPLIES_TO"), ("white-eyed mutant", "X chromosome", "APPLIES_TO")],
     "which lab demonstrated chromosomal inheritance by mapping a fly eye-colour mutant to the X chromosome",
     "morgan drosophila fly room columbia x chromosome white eye mutant"),
    # --- 5 ---
    ("James Watson and Francis Crick proposed the DNA double helix in 1953 at Cambridge using Rosalind Franklin's Photo 51 X-ray data; the one-page Nature paper reshaped molecular biology overnight.", "milestone", "knowledge", False,
     [("James Watson", "person"), ("Francis Crick", "person"), ("Rosalind Franklin", "person"), ("Photo 51", "concept"), ("DNA double helix", "concept"), ("1953", "date"), ("Nature", "organization")],
     [("James Watson", "DNA double helix", "PRODUCES"), ("Francis Crick", "DNA double helix", "PRODUCES"), ("Photo 51", "DNA double helix", "APPLIES_TO")],
     "which 1953 Cambridge paper used Franklin's X-ray image to solve the structure of DNA",
     "watson crick franklin photo 51 dna double helix 1953 cambridge"),
    # --- 6 ---
    ("Oswald Avery, Colin MacLeod, and Maclyn McCarty showed in 1944 that DNA, not protein, carried the transforming principle in pneumococcus; the result reframed the molecular target of genetics.", "fact", "knowledge", False,
     [("Oswald Avery", "person"), ("Colin MacLeod", "person"), ("Maclyn McCarty", "person"), ("1944", "date"), ("pneumococcus", "concept"), ("transforming principle", "concept")],
     [("Oswald Avery", "transforming principle", "APPLIES_TO")],
     "whose 1944 pneumococcus experiments pinned the carrier of heredity on DNA rather than protein",
     "avery macleod mccarty 1944 pneumococcus transforming principle dna"),
    # --- 7 ---
    ("Matthew Meselson and Franklin Stahl ran their density-gradient centrifugation experiment in 1958 and confirmed semiconservative replication of DNA; each daughter helix keeps one parental strand.", "milestone", "knowledge", False,
     [("Matthew Meselson", "person"), ("Franklin Stahl", "person"), ("1958", "date"), ("density-gradient centrifugation", "method"), ("semiconservative replication", "concept")],
     [("Matthew Meselson", "semiconservative replication", "APPLIES_TO"), ("density-gradient centrifugation", "semiconservative replication", "APPLIES_TO")],
     "which 1958 centrifugation experiment demonstrated that DNA replicates semiconservatively",
     "meselson stahl 1958 density gradient semiconservative replication"),
    # --- 8 ---
    ("Francois Jacob and Jacques Monod described the lac operon in 1961 at the Institut Pasteur, introducing the operator-repressor model that explained bacterial gene regulation.", "architecture", "knowledge", False,
     [("Francois Jacob", "person"), ("Jacques Monod", "person"), ("lac operon", "concept"), ("Institut Pasteur", "organization"), ("1961", "date")],
     [("Francois Jacob", "lac operon", "PRODUCES"), ("Jacques Monod", "lac operon", "PRODUCES")],
     "which 1961 Pasteur paper introduced the operon model of bacterial gene regulation",
     "jacob monod lac operon 1961 pasteur operator repressor regulation"),
    # --- 9 ---
    ("Crick articulated the central dogma of molecular biology in 1958, stating that sequence information flows from DNA to RNA to protein and not back from protein into nucleic acids.", "reference", "knowledge", False,
     [("Crick", "person"), ("central dogma", "concept"), ("1958", "date"), ("DNA", "concept"), ("RNA", "concept"), ("protein", "concept")],
     [("Crick", "central dogma", "PRODUCES")],
     "what principle did Crick formalise in 1958 about the direction of sequence information flow",
     "crick central dogma 1958 dna rna protein information flow"),
    # --- 10. noise ---
    ("The library's replacement boiler kept kicking on at 3 a.m. and the janitor finally traced it to a cracked pressure gauge.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Kary Mullis invented the polymerase chain reaction in 1983 at Cetus Corporation; the Nobel citation came a decade later and PCR became the workhorse of every molecular biology lab.", "milestone", "knowledge", False,
     [("Kary Mullis", "person"), ("polymerase chain reaction", "method"), ("1983", "date"), ("Cetus Corporation", "organization")],
     [("Kary Mullis", "polymerase chain reaction", "PRODUCES"), ("Cetus Corporation", "polymerase chain reaction", "APPLIES_TO")],
     "which 1983 Cetus invention let labs amplify DNA from vanishingly small starting material",
     "mullis pcr polymerase chain reaction 1983 cetus amplification"),
    # --- 12 ---
    ("Fred Sanger developed chain-termination sequencing in 1977 at the MRC Laboratory of Molecular Biology in Cambridge, which earned him a second Nobel Prize and anchored three decades of genomics.", "decision", "knowledge", False,
     [("Fred Sanger", "person"), ("chain-termination sequencing", "method"), ("MRC Laboratory of Molecular Biology", "organization"), ("1977", "date")],
     [("Fred Sanger", "chain-termination sequencing", "PRODUCES")],
     "whose 1977 Cambridge method became the default for reading DNA sequence for thirty years",
     "sanger chain termination sequencing 1977 mrc cambridge nobel"),
    # --- 13 ---
    ("The Human Genome Project ran from 1990 to 2003 as an international public consortium; the declared draft came in 2001 and the finished reference landed on the fiftieth anniversary of the double helix.", "milestone", "knowledge", False,
     [("Human Genome Project", "project"), ("1990", "date"), ("2003", "date"), ("2001", "date")],
     [],
     "which public consortium ran from 1990 to 2003 to produce the first reference human genome",
     "human genome project 1990 2003 2001 draft reference consortium"),
    # --- 14 ---
    ("Craig Venter launched Celera Genomics in 1998 to sequence the human genome with whole-genome shotgun assembly, which pressured the public project and produced the parallel 2001 draft.", "decision", "knowledge", False,
     [("Craig Venter", "person"), ("Celera Genomics", "organization"), ("1998", "date"), ("whole-genome shotgun", "method"), ("2001", "date")],
     [("Craig Venter", "Celera Genomics", "PRODUCES"), ("Celera Genomics", "whole-genome shotgun", "USES")],
     "which private-sector push used shotgun assembly to race the public genome project",
     "venter celera 1998 whole genome shotgun assembly human draft 2001"),
    # --- 15 ---
    ("Francis Collins led the NIH side of the Human Genome Project as director of NHGRI and later ran the NIH itself from 2009 to 2021; he also co-discovered the CFTR cystic fibrosis gene in 1989.", "fact", "knowledge", False,
     [("Francis Collins", "person"), ("NIH", "organization"), ("NHGRI", "organization"), ("CFTR", "concept"), ("1989", "date")],
     [("Francis Collins", "NHGRI", "APPLIES_TO"), ("Francis Collins", "CFTR", "PRODUCES")],
     "which NIH leader ran the public genome project and also found the cystic fibrosis gene",
     "collins nih nhgri human genome cftr cystic fibrosis 1989"),
    # --- 16 ---
    ("CRISPR-Cas9 as a programmable genome editor was reported by Jennifer Doudna and Emmanuelle Charpentier in 2012, with guide RNAs directing Cas9 to specific DNA sites.", "decision", "knowledge", False,
     [("CRISPR-Cas9", "method"), ("Jennifer Doudna", "person"), ("Emmanuelle Charpentier", "person"), ("2012", "date"), ("guide RNAs", "concept")],
     [("Jennifer Doudna", "CRISPR-Cas9", "PRODUCES"), ("Emmanuelle Charpentier", "CRISPR-Cas9", "PRODUCES"), ("guide RNAs", "CRISPR-Cas9", "APPLIES_TO")],
     "which 2012 paper showed Cas9 could be programmed with guide RNAs to cut specific genome sites",
     "crispr cas9 doudna charpentier 2012 guide rna genome editor"),
    # --- 17 ---
    ("Feng Zhang at the Broad Institute demonstrated CRISPR-Cas9 editing in mammalian cells in early 2013, which kicked off the patent dispute between Broad and UC Berkeley over priority.", "fact", "knowledge", False,
     [("Feng Zhang", "person"), ("Broad Institute", "organization"), ("CRISPR-Cas9", "method"), ("2013", "date"), ("UC Berkeley", "organization")],
     [("Feng Zhang", "CRISPR-Cas9", "APPLIES_TO"), ("Feng Zhang", "Broad Institute", "APPLIES_TO")],
     "which 2013 mammalian-cell CRISPR demonstration ignited the Broad versus Berkeley patent fight",
     "zhang broad 2013 crispr mammalian cell patent berkeley"),
    # --- 18 ---
    ("Stanley Prusiner proposed the prion hypothesis in 1982, arguing that a protein-only infectious agent caused scrapie and CJD; the community resisted for years before the misfolding evidence accumulated.", "decision", "knowledge", False,
     [("Stanley Prusiner", "person"), ("prion", "concept"), ("1982", "date"), ("scrapie", "concept"), ("CJD", "concept")],
     [("Stanley Prusiner", "prion", "PRODUCES"), ("prion", "scrapie", "APPLIES_TO")],
     "whose 1982 protein-only infection hypothesis eventually explained scrapie and CJD",
     "prusiner prion 1982 protein only scrapie cjd misfolding"),
    # --- 19 ---
    ("Andrew Fire and Craig Mello reported RNA interference in C. elegans in 1998; double-stranded RNA silenced matching transcripts, and the Nobel followed just eight years later.", "milestone", "knowledge", False,
     [("Andrew Fire", "person"), ("Craig Mello", "person"), ("RNA interference", "concept"), ("C. elegans", "concept"), ("1998", "date")],
     [("Andrew Fire", "RNA interference", "PRODUCES"), ("Craig Mello", "RNA interference", "PRODUCES"), ("RNA interference", "C. elegans", "APPLIES_TO")],
     "which 1998 worm study demonstrated that double-stranded RNA triggered sequence-specific gene silencing",
     "fire mello rna interference c elegans 1998 double stranded silencing"),
    # --- 20 ---
    ("Ada Yonath at the Weizmann Institute pioneered ribosome crystallography in the 1980s through cryo-crystallography of halophile ribosomes, clearing the path for full atomic structures.", "architecture", "knowledge", False,
     [("Ada Yonath", "person"), ("Weizmann Institute", "organization"), ("ribosome crystallography", "method"), ("halophile ribosomes", "concept")],
     [("Ada Yonath", "ribosome crystallography", "PRODUCES"), ("ribosome crystallography", "halophile ribosomes", "APPLIES_TO")],
     "who seeded ribosome crystallography by freezing halophile ribosomes at the Weizmann Institute",
     "yonath weizmann ribosome crystallography halophile cryo crystal"),
    # --- 21 ---
    ("Venki Ramakrishnan solved the 30S ribosomal subunit structure in 2000 at the MRC Laboratory of Molecular Biology, which let the field read codon-anticodon decoding at atomic resolution.", "architecture", "knowledge", False,
     [("Venki Ramakrishnan", "person"), ("30S ribosomal subunit", "concept"), ("2000", "date"), ("MRC Laboratory of Molecular Biology", "organization")],
     [("Venki Ramakrishnan", "30S ribosomal subunit", "PRODUCES")],
     "whose 2000 Cambridge structure of the small ribosomal subunit revealed codon decoding mechanics",
     "ramakrishnan 30s ribosome 2000 mrc cambridge codon decoding"),
    # --- 22 ---
    ("Thomas Steitz solved the 50S ribosomal subunit in 2000 at Yale and showed the peptidyl-transferase centre was RNA, which cemented the ribosome-as-ribozyme view.", "architecture", "knowledge", False,
     [("Thomas Steitz", "person"), ("50S ribosomal subunit", "concept"), ("Yale", "organization"), ("2000", "date"), ("peptidyl-transferase centre", "concept")],
     [("Thomas Steitz", "50S ribosomal subunit", "PRODUCES"), ("peptidyl-transferase centre", "50S ribosomal subunit", "APPLIES_TO")],
     "which 2000 Yale structure placed peptide-bond catalysis on ribosomal RNA rather than protein",
     "steitz 50s ribosome 2000 yale peptidyl transferase ribozyme"),
    # --- 23 ---
    ("DeepMind released AlphaFold 2 in 2020 at CASP14 with median GDT-TS around 92, effectively solving protein structure prediction from sequence for most single-chain cases.", "milestone", "knowledge", False,
     [("DeepMind", "organization"), ("AlphaFold 2", "tool"), ("2020", "date"), ("CASP14", "concept"), ("GDT-TS", "concept")],
     [("DeepMind", "AlphaFold 2", "PRODUCES"), ("AlphaFold 2", "CASP14", "APPLIES_TO")],
     "which 2020 CASP14 entry from DeepMind pushed GDT-TS above 90 and broke the protein-folding problem",
     "deepmind alphafold 2 2020 casp14 gdt ts protein folding"),
    # --- 24 ---
    ("AlphaFold's 2021 open release of the human proteome put 350,000 predicted structures into the EBI database and changed how structural biologists spend the first hour of a project.", "fact", "knowledge", False,
     [("AlphaFold", "tool"), ("2021", "date"), ("human proteome", "concept"), ("EBI", "organization")],
     [("AlphaFold", "human proteome", "APPLIES_TO"), ("human proteome", "EBI", "APPLIES_TO")],
     "which 2021 AlphaFold release made predicted human proteome structures freely queryable at EBI",
     "alphafold 2021 human proteome ebi database predicted structure"),
    # --- 25 ---
    ("Lynn Margulis published the serial endosymbiotic theory in 1967 under her married name Sagan; she argued mitochondria and chloroplasts descend from engulfed free-living bacteria.", "decision", "knowledge", False,
     [("Lynn Margulis", "person"), ("endosymbiotic theory", "concept"), ("1967", "date"), ("mitochondria", "concept"), ("chloroplasts", "concept")],
     [("Lynn Margulis", "endosymbiotic theory", "PRODUCES"), ("endosymbiotic theory", "mitochondria", "APPLIES_TO"), ("endosymbiotic theory", "chloroplasts", "APPLIES_TO")],
     "who traced organelles back to engulfed prokaryotes in the 1967 Sagan paper on cellular ancestry",
     "margulis endosymbiotic 1967 mitochondria chloroplast bacteria"),
    # --- 26 ---
    ("Evo-devo coalesced in the 1980s when Walter Gehring's Basel lab found that homeobox sequences in fruit fly Hox genes were conserved in vertebrates, revealing a shared developmental toolkit.", "architecture", "knowledge", False,
     [("Evo-devo", "concept"), ("Walter Gehring", "person"), ("Basel", "place"), ("homeobox", "concept"), ("Hox genes", "concept")],
     [("Walter Gehring", "homeobox", "PRODUCES"), ("homeobox", "Hox genes", "APPLIES_TO")],
     "which Basel lab's homeobox discovery anchored evo-devo as a discipline in the 1980s",
     "evo devo gehring basel homeobox hox conservation vertebrate"),
    # --- 27 ---
    ("Eugene Odum formalised ecosystem ecology in his 1953 textbook Fundamentals of Ecology, which treated energy flow and nutrient cycling as the core unit rather than species lists.", "reference", "knowledge", False,
     [("Eugene Odum", "person"), ("Fundamentals of Ecology", "project"), ("1953", "date"), ("ecosystem ecology", "concept")],
     [("Eugene Odum", "Fundamentals of Ecology", "PRODUCES"), ("Fundamentals of Ecology", "ecosystem ecology", "APPLIES_TO")],
     "which 1953 textbook reframed ecology around ecosystem-level energy and nutrient flow",
     "odum 1953 fundamentals ecology ecosystem energy flow textbook"),
    # --- 28 ---
    ("E.O. Wilson introduced sociobiology in his 1975 book Sociobiology: The New Synthesis at Harvard, applying evolutionary theory to animal and human social behaviour.", "reference", "knowledge", False,
     [("E.O. Wilson", "person"), ("Sociobiology: The New Synthesis", "project"), ("1975", "date"), ("Harvard", "organization")],
     [("E.O. Wilson", "Sociobiology: The New Synthesis", "PRODUCES")],
     "which 1975 Harvard book launched sociobiology as an application of evolution to social behaviour",
     "wilson sociobiology new synthesis 1975 harvard evolution social"),
    # --- 29 ---
    ("Linus Pauling won the 1954 chemistry Nobel largely for the alpha helix, the first solved secondary structure of proteins; he missed DNA by refusing to share Franklin's data.", "problem", "knowledge", False,
     [("Linus Pauling", "person"), ("alpha helix", "concept"), ("1954", "date"), ("Franklin", "person")],
     [("Linus Pauling", "alpha helix", "PRODUCES")],
     "whose 1954 Nobel rested on the alpha helix yet who also missed the DNA structure",
     "pauling alpha helix 1954 nobel protein secondary structure franklin"),
    # --- 30 ---
    ("Barbara McClintock discovered transposable elements in maize chromosomes in the 1940s at Cold Spring Harbor; the community dismissed jumping genes until the 1983 Nobel vindicated her.", "decision", "knowledge", False,
     [("Barbara McClintock", "person"), ("transposable elements", "concept"), ("maize", "concept"), ("Cold Spring Harbor", "organization"), ("1983", "date")],
     [("Barbara McClintock", "transposable elements", "PRODUCES"), ("transposable elements", "maize", "APPLIES_TO")],
     "which maize geneticist found jumping genes in the 1940s and was vindicated by the 1983 Nobel",
     "mcclintock transposable maize cold spring harbor jumping gene 1983"),
    # --- 31 ---
    ("Hamilton's 1964 inclusive-fitness papers introduced kin selection and explained altruism in social insects by weighting relatedness against the benefit-to-cost ratio.", "reference", "knowledge", False,
     [("Hamilton", "person"), ("1964", "date"), ("inclusive-fitness", "concept"), ("kin selection", "concept"), ("social insects", "concept")],
     [("Hamilton", "kin selection", "PRODUCES"), ("kin selection", "social insects", "APPLIES_TO")],
     "which 1964 papers introduced kin selection and the relatedness weighting behind altruism",
     "hamilton 1964 inclusive fitness kin selection altruism social insect"),
    # --- 32 ---
    ("Carl Woese proposed a three-domain tree of life in 1977 based on 16S ribosomal RNA sequences from the University of Illinois, which pulled Archaea out of the bacterial kingdom.", "decision", "knowledge", False,
     [("Carl Woese", "person"), ("three-domain tree", "concept"), ("1977", "date"), ("16S ribosomal RNA", "method"), ("Archaea", "concept"), ("University of Illinois", "organization")],
     [("Carl Woese", "three-domain tree", "PRODUCES"), ("16S ribosomal RNA", "three-domain tree", "APPLIES_TO")],
     "whose 1977 16S rRNA phylogeny split Archaea out and gave us the three-domain tree",
     "woese 1977 16s rrna three domain archaea illinois tree"),
    # --- 33 ---
    ("The Nirenberg and Matthaei 1961 poly-U experiment at the NIH translated UUU into phenylalanine, cracking the first codon and kicking off the decode of the full genetic code by 1966.", "architecture", "knowledge", False,
     [("Nirenberg", "person"), ("Matthaei", "person"), ("1961", "date"), ("poly-U", "method"), ("NIH", "organization"), ("phenylalanine", "concept"), ("1966", "date")],
     [("Nirenberg", "poly-U", "PRODUCES"), ("poly-U", "phenylalanine", "APPLIES_TO")],
     "which 1961 NIH poly-U experiment assigned UUU to phenylalanine and started cracking the genetic code",
     "nirenberg matthaei 1961 poly u nih phenylalanine genetic code"),
    # --- 34 ---
    ("Rosalind Franklin's X-ray fibre diffraction work at King's College London produced Photo 51 in 1952; Wilkins showed the image to Watson without her knowledge in 1953.", "problem", "knowledge", False,
     [("Rosalind Franklin", "person"), ("King's College London", "organization"), ("Photo 51", "concept"), ("1952", "date"), ("Wilkins", "person"), ("Watson", "person")],
     [("Rosalind Franklin", "Photo 51", "PRODUCES"), ("Photo 51", "King's College London", "APPLIES_TO")],
     "whose 1952 X-ray fibre image of DNA was shown to Watson without consent and became Photo 51",
     "franklin photo 51 kings college 1952 xray diffraction wilkins"),
    # --- 35 ---
    ("Darwin's 1871 The Descent of Man extended natural selection to humans and introduced sexual selection to explain traits like peacock tails that pure survival selection could not.", "reference", "knowledge", False,
     [("Darwin", "person"), ("The Descent of Man", "project"), ("1871", "date"), ("sexual selection", "concept"), ("peacock tails", "concept")],
     [("Darwin", "The Descent of Man", "PRODUCES"), ("The Descent of Man", "sexual selection", "APPLIES_TO")],
     "which 1871 Darwin book extended evolution to humans and introduced sexual selection",
     "darwin descent of man 1871 sexual selection human peacock"),
    # --- 36 ---
    ("Kimura's neutral theory of molecular evolution, published in 1968 from the National Institute of Genetics, argued most DNA variation is selectively neutral and drifts to fixation by chance.", "decision", "knowledge", False,
     [("Kimura", "person"), ("neutral theory", "concept"), ("1968", "date"), ("National Institute of Genetics", "organization")],
     [("Kimura", "neutral theory", "PRODUCES")],
     "whose 1968 theory argued most molecular variation drifts neutrally rather than being selected",
     "kimura neutral theory 1968 molecular evolution drift japan"),
    # --- 37 ---
    ("Severo Ochoa isolated polynucleotide phosphorylase in 1955 at NYU and used it to make the synthetic RNAs that Nirenberg later fed into the cell-free translation assay.", "fact", "knowledge", False,
     [("Severo Ochoa", "person"), ("polynucleotide phosphorylase", "concept"), ("1955", "date"), ("NYU", "organization"), ("Nirenberg", "person")],
     [("Severo Ochoa", "polynucleotide phosphorylase", "PRODUCES"), ("polynucleotide phosphorylase", "Nirenberg", "APPLIES_TO")],
     "which 1955 NYU enzyme isolation gave Nirenberg the synthetic RNAs for the codon experiments",
     "ochoa polynucleotide phosphorylase 1955 nyu synthetic rna nirenberg"),
    # --- 38 ---
    ("The Cambrian explosion around 540 million years ago produced most major animal phyla in a geologically short window, a pattern Stephen Jay Gould popularised in Wonderful Life in 1989.", "fact", "knowledge", False,
     [("Cambrian explosion", "concept"), ("540 million years ago", "date"), ("Stephen Jay Gould", "person"), ("Wonderful Life", "project"), ("1989", "date")],
     [("Stephen Jay Gould", "Wonderful Life", "PRODUCES"), ("Wonderful Life", "Cambrian explosion", "APPLIES_TO")],
     "which 1989 Gould book popularised the Cambrian explosion and the Burgess Shale fossils",
     "cambrian explosion 540 million gould wonderful life 1989 burgess"),
    # --- 39 ---
    ("Shinya Yamanaka induced pluripotent stem cells from mouse fibroblasts in 2006 at Kyoto University with four transcription factors: Oct4, Sox2, Klf4, and c-Myc.", "decision", "knowledge", False,
     [("Shinya Yamanaka", "person"), ("induced pluripotent stem cells", "concept"), ("2006", "date"), ("Kyoto University", "organization"), ("Oct4", "concept"), ("Sox2", "concept"), ("Klf4", "concept"), ("c-Myc", "concept")],
     [("Shinya Yamanaka", "induced pluripotent stem cells", "PRODUCES")],
     "which 2006 Kyoto discovery reset fibroblasts into pluripotent cells with four transcription factors",
     "yamanaka ips 2006 kyoto oct4 sox2 klf4 c myc pluripotent"),
    # --- 40 ---
    ("Allan Wilson's molecular clock work at UC Berkeley in 1967 calibrated primate divergence from albumin immunological distance, shortening the estimated human-chimp split to roughly five million years.", "decision", "knowledge", False,
     [("Allan Wilson", "person"), ("molecular clock", "method"), ("UC Berkeley", "organization"), ("1967", "date"), ("albumin", "concept")],
     [("Allan Wilson", "molecular clock", "PRODUCES"), ("molecular clock", "albumin", "APPLIES_TO")],
     "which 1967 Berkeley study used an albumin molecular clock to bring the human-chimp split to five million years",
     "wilson molecular clock 1967 berkeley albumin human chimp split"),
    # --- 41 ---
    ("Sydney Brenner picked C. elegans as a model organism in 1963 at the LMB, and John Sulston later traced its entire 959-cell lineage by direct microscopy, which opened developmental biology to cell-by-cell analysis.", "architecture", "knowledge", False,
     [("Sydney Brenner", "person"), ("C. elegans", "concept"), ("1963", "date"), ("LMB", "organization"), ("John Sulston", "person"), ("959-cell lineage", "concept")],
     [("Sydney Brenner", "C. elegans", "PRODUCES"), ("John Sulston", "959-cell lineage", "PRODUCES"), ("959-cell lineage", "C. elegans", "APPLIES_TO")],
     "which nematode became a model organism thanks to Brenner's 1963 choice and Sulston's full-lineage trace",
     "brenner c elegans 1963 lmb sulston 959 cell lineage model"),
    # --- 42 ---
    ("Harold Varmus and Michael Bishop showed in 1976 at UCSF that the src oncogene in Rous sarcoma virus came from a normal cellular gene, which reframed cancer as dysregulation of native proto-oncogenes.", "decision", "knowledge", False,
     [("Harold Varmus", "person"), ("Michael Bishop", "person"), ("1976", "date"), ("UCSF", "organization"), ("src", "concept"), ("Rous sarcoma virus", "concept"), ("proto-oncogenes", "concept")],
     [("Harold Varmus", "proto-oncogenes", "PRODUCES"), ("src", "proto-oncogenes", "APPLIES_TO")],
     "which 1976 UCSF work linked the src retroviral oncogene to a normal cellular proto-oncogene",
     "varmus bishop 1976 ucsf src rous sarcoma proto oncogene"),
    # --- 43. noise ---
    ("The city fountain froze solid on Tuesday and a crow spent twenty minutes trying to crack the ice for a drink.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Dolly the sheep was cloned from an adult mammary cell at the Roslin Institute in 1996 by Ian Wilmut's team, which proved that differentiated nuclei could be reprogrammed to totipotency.", "problem", "knowledge", False,
     [("Dolly", "concept"), ("Roslin Institute", "organization"), ("1996", "date"), ("Ian Wilmut", "person"), ("mammary cell", "concept")],
     [("Ian Wilmut", "Dolly", "PRODUCES"), ("Dolly", "Roslin Institute", "APPLIES_TO")],
     "which 1996 Roslin experiment cloned a sheep from an adult mammary-cell nucleus",
     "dolly sheep roslin 1996 wilmut mammary clone nuclear transfer"),
    # --- 45 ---
    ("The lipid bilayer model of cell membranes went from the Gorter-Grendel monolayer-pair in 1925 to the Singer-Nicolson fluid mosaic model in 1972, which embedded proteins floating in a lateral lipid sea.", "architecture", "knowledge", False,
     [("lipid bilayer", "concept"), ("Gorter-Grendel", "person"), ("1925", "date"), ("Singer-Nicolson", "person"), ("fluid mosaic model", "concept"), ("1972", "date")],
     [("Singer-Nicolson", "fluid mosaic model", "PRODUCES")],
     "which 1972 membrane model replaced the 1925 monolayer-pair picture with embedded floating proteins",
     "gorter grendel 1925 singer nicolson 1972 fluid mosaic bilayer"),
    # --- 46 ---
    ("Peter Mitchell's chemiosmotic hypothesis in 1961 proposed that ATP synthesis is driven by a proton gradient across the inner mitochondrial membrane; the field resisted it for a decade.", "decision", "knowledge", False,
     [("Peter Mitchell", "person"), ("chemiosmotic hypothesis", "concept"), ("1961", "date"), ("proton gradient", "concept"), ("inner mitochondrial membrane", "concept")],
     [("Peter Mitchell", "chemiosmotic hypothesis", "PRODUCES"), ("chemiosmotic hypothesis", "proton gradient", "APPLIES_TO")],
     "whose 1961 proton-gradient idea explained ATP synthesis and faced a decade of pushback",
     "mitchell chemiosmotic 1961 proton gradient atp mitochondria"),
    # --- 47 ---
    ("Lynn Margulis also championed the Gaia hypothesis alongside James Lovelock in 1974, framing the biosphere as a self-regulating system that holds atmospheric composition within habitable bounds.", "preference", "knowledge", False,
     [("Lynn Margulis", "person"), ("Gaia hypothesis", "concept"), ("James Lovelock", "person"), ("1974", "date"), ("biosphere", "concept")],
     [("James Lovelock", "Gaia hypothesis", "PRODUCES"), ("Lynn Margulis", "Gaia hypothesis", "APPLIES_TO")],
     "which 1974 Lovelock and Margulis hypothesis framed the biosphere as a self-regulating system",
     "margulis lovelock gaia 1974 biosphere self regulation atmosphere"),
    # --- 48 ---
    ("Jane Goodall documented tool use in wild chimpanzees at Gombe Stream in 1960, which forced anthropologists to drop the tool-maker definition of humanity that had stood since Kenneth Oakley.", "preference", "knowledge", False,
     [("Jane Goodall", "person"), ("chimpanzees", "concept"), ("Gombe Stream", "place"), ("1960", "date"), ("Kenneth Oakley", "person")],
     [("Jane Goodall", "chimpanzees", "APPLIES_TO")],
     "which 1960 Gombe observation forced anthropologists to rewrite the tool-use definition of humanity",
     "goodall gombe 1960 chimpanzee tool use oakley human definition"),
    # --- 49 ---
    ("The Miller-Urey experiment in 1953 at the University of Chicago sparked gases thought to resemble the early atmosphere and recovered amino acids, supporting an abiotic origin of organic chemistry.", "preference", "knowledge", False,
     [("Miller-Urey experiment", "method"), ("1953", "date"), ("University of Chicago", "organization"), ("amino acids", "concept")],
     [("Miller-Urey experiment", "amino acids", "APPLIES_TO")],
     "which 1953 Chicago experiment recovered amino acids from simulated early-atmosphere sparking",
     "miller urey 1953 chicago amino acid spark origin life atmosphere"),
    # --- 50 ---
    ("Jennifer Doudna preferred the ethical-pause frame on germline CRISPR editing after the 2018 He Jiankui twins affair, which she criticised as premature and poorly monitored.", "preference", "knowledge", False,
     [("Jennifer Doudna", "person"), ("germline CRISPR", "concept"), ("2018", "date"), ("He Jiankui", "person")],
     [("Jennifer Doudna", "germline CRISPR", "APPLIES_TO")],
     "which stance did Doudna take after the 2018 He Jiankui twins used germline CRISPR clinically",
     "doudna germline crispr 2018 he jiankui twins ethical pause"),
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
