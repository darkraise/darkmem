"""One-off emitter for shared-base batch-236 — knowledge domain (history of chemistry: Lavoisier, Dalton, Avogadro, Mendeleev, Kekule, Arrhenius, Haber-Bosch, Bakelite, Langmuir-Blodgett, Pauling, Ziegler-Natta, Woodward-Hoffmann, Corey, Sharpless, Noyori, Grubbs, click chemistry, Heck-Negishi-Suzuki, MOFs, nanotubes, fullerenes, graphene).

Writes 50 rows to data/v2/shared/batch_236.tmp.jsonl with ids shared-11751..11800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_236.tmp.jsonl"
ID_OFFSET = 11750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("Antoine Lavoisier dethroned the phlogiston theory in the 1770s by weighing reactions before and after combustion; the conserved mass forced chemists to treat oxygen as the agent of burning rather than invoking a released fluid.", "decision", "knowledge", False,
     [("Antoine Lavoisier", "person"), ("phlogiston theory", "concept"), ("oxygen", "concept"), ("combustion", "concept")],
     [("Antoine Lavoisier", "phlogiston theory", "REPLACES"), ("oxygen", "combustion", "APPLIES_TO")],
     "who overturned phlogiston by quantitative weighing experiments and which element took its explanatory role",
     "lavoisier phlogiston oxygen combustion conservation mass weigh"),
    # --- 2 --- fact
    ("The law of conservation of mass, formalised by Lavoisier in the Traite elementaire de chimie in 1789, became the bedrock axiom that all subsequent stoichiometry assumed without further argument.", "fact", "knowledge", False,
     [("law of conservation of mass", "concept"), ("Lavoisier", "person"), ("Traite elementaire de chimie", "publication"), ("stoichiometry", "concept")],
     [("law of conservation of mass", "stoichiometry", "APPLIES_TO"), ("Lavoisier", "Traite elementaire de chimie", "PRODUCES")],
     "which 1789 textbook codified the mass conservation axiom that stoichiometry would lean on for two centuries",
     "lavoisier conservation mass traite chimie stoichiometry axiom 1789"),
    # --- 3 --- decision
    ("John Dalton proposed the atomic theory between 1803 and 1808, fixing indivisible atoms with element-specific weights as the ontology chemists would use to read combining ratios.", "decision", "knowledge", False,
     [("John Dalton", "person"), ("atomic theory", "concept"), ("atoms", "concept"), ("combining ratios", "concept")],
     [("John Dalton", "atomic theory", "PRODUCES"), ("atoms", "combining ratios", "APPLIES_TO")],
     "who proposed that elements are built from indivisible atoms with characteristic weights in the early 1800s",
     "dalton atomic theory atom weight combining ratio 1803 indivisible"),
    # --- 4 --- reference
    ("Dalton's 1808 A New System of Chemical Philosophy is still the canonical citation for the law of multiple proportions; later historians lean on it to date the shift from equivalent weights to atomic weights.", "reference", "knowledge", False,
     [("Dalton", "person"), ("A New System of Chemical Philosophy", "publication"), ("law of multiple proportions", "concept"), ("atomic weights", "concept")],
     [("Dalton", "A New System of Chemical Philosophy", "PRODUCES"), ("A New System of Chemical Philosophy", "law of multiple proportions", "SUPPORTS")],
     "which 1808 treatise anchors the law of multiple proportions in the historical record of chemistry",
     "dalton new system chemical philosophy multiple proportion atomic weight"),
    # --- 5 --- fact
    ("Amedeo Avogadro proposed in 1811 that equal volumes of gases at equal temperature and pressure contain equal numbers of particles; the hypothesis later canonised as Avogadro's law separated molecule from atom a full half-century before the discipline accepted the distinction.", "fact", "knowledge", False,
     [("Amedeo Avogadro", "person"), ("Avogadro's law", "concept"), ("gases", "concept"), ("molecule", "concept"), ("atom", "concept")],
     [("Amedeo Avogadro", "Avogadro's law", "PRODUCES"), ("molecule", "atom", "DEPENDS_ON")],
     "which 1811 proposal linked equal gas volumes to equal particle counts and split molecules from atoms",
     "avogadro law equal volume gas molecule atom particle 1811"),
    # --- 6 --- reference
    ("Stanislao Cannizzaro revived Avogadro's hypothesis at the 1860 Karlsruhe Congress, handing out a pamphlet that finally let chemists reconcile atomic weights and molecular formulas after decades of drift.", "reference", "knowledge", False,
     [("Stanislao Cannizzaro", "person"), ("Avogadro's hypothesis", "concept"), ("Karlsruhe Congress", "event"), ("atomic weights", "concept")],
     [("Stanislao Cannizzaro", "Avogadro's hypothesis", "SUPPORTS"), ("Karlsruhe Congress", "atomic weights", "APPLIES_TO")],
     "which 1860 congress and advocate pulled Avogadro's hypothesis back into mainstream chemistry",
     "cannizzaro karlsruhe avogadro pamphlet atomic weight reconcile 1860"),
    # --- 7 --- milestone
    ("Dmitri Mendeleev published the periodic table in 1869, ordering elements by atomic weight and leaving deliberate gaps whose predicted properties matched gallium and germanium within a decade.", "milestone", "knowledge", False,
     [("Dmitri Mendeleev", "person"), ("periodic table", "concept"), ("gallium", "concept"), ("germanium", "concept")],
     [("Dmitri Mendeleev", "periodic table", "PRODUCES"), ("periodic table", "gallium", "SUPPORTS")],
     "who arranged the elements into a periodic table in 1869 and which predicted elements later confirmed it",
     "mendeleev periodic table 1869 gap gallium germanium predict element"),
    # --- 8 --- decision
    ("Mendeleev opted to order by atomic weight but reversed tellurium and iodine on chemical grounds; later Henry Moseley re-anchored the table on atomic number, vindicating the swap without overturning the scheme.", "decision", "knowledge", False,
     [("Mendeleev", "person"), ("atomic weight", "concept"), ("tellurium", "concept"), ("iodine", "concept"), ("Henry Moseley", "person"), ("atomic number", "concept")],
     [("atomic number", "atomic weight", "IMPROVES_ON"), ("Henry Moseley", "atomic number", "PRODUCES")],
     "which pair of elements did Mendeleev swap against their atomic weights and whose later work justified it",
     "mendeleev tellurium iodine swap moseley atomic number weight"),
    # --- 9 --- decision
    ("August Kekule reported in 1865 that benzene's six carbons form a closed ring with alternating double bonds, a structural insight he famously credited to a daydream of a snake biting its own tail.", "decision", "knowledge", False,
     [("August Kekule", "person"), ("benzene", "concept"), ("ring", "concept"), ("double bonds", "concept")],
     [("August Kekule", "benzene", "PRODUCES"), ("ring", "benzene", "APPLIES_TO")],
     "who first proposed that benzene closes into a six-carbon ring with alternating double bonds",
     "kekule benzene ring six carbon double bond 1865 snake dream"),
    # --- 10 --- noise
    ("The departmental coffee machine in the chemistry common room has been reporting the wrong time since the daylight-saving change and nobody wants to be the one to reset it.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- reference
    ("Svante Arrhenius defended his 1884 thesis on electrolytic dissociation in Uppsala to a lukewarm committee; the same argument earned him the 1903 Nobel in Chemistry once ionic conduction was widely accepted.", "reference", "knowledge", False,
     [("Svante Arrhenius", "person"), ("electrolytic dissociation", "concept"), ("Uppsala", "place"), ("Nobel in Chemistry", "event"), ("ionic conduction", "concept")],
     [("Svante Arrhenius", "electrolytic dissociation", "PRODUCES"), ("Nobel in Chemistry", "Svante Arrhenius", "SUPPORTS")],
     "whose 1884 ionic-dissociation thesis was dismissed at defence yet later won a chemistry Nobel",
     "arrhenius electrolytic dissociation uppsala nobel 1903 ion conduction"),
    # --- 12 --- fact
    ("Arrhenius framed acids as proton donors in aqueous solution and bases as hydroxide donors; the definition ruled textbooks until Bronsted-Lowry broadened acids to any proton donor regardless of solvent.", "fact", "knowledge", False,
     [("Arrhenius", "person"), ("acids", "concept"), ("bases", "concept"), ("Bronsted-Lowry", "concept")],
     [("Bronsted-Lowry", "Arrhenius", "IMPROVES_ON"), ("Arrhenius", "acids", "APPLIES_TO")],
     "which definition of acids did Arrhenius propose and which later framework broadened it beyond water",
     "arrhenius acid base proton hydroxide bronsted lowry definition aqueous"),
    # --- 13 --- decision
    ("Fritz Haber demonstrated direct ammonia synthesis from nitrogen and hydrogen in 1909; Carl Bosch scaled the process at BASF by 1913, decoupling nitrogen fertiliser from Chilean saltpetre imports.", "decision", "knowledge", False,
     [("Fritz Haber", "person"), ("ammonia synthesis", "concept"), ("Carl Bosch", "person"), ("BASF", "organization"), ("Chilean saltpetre", "concept")],
     [("Fritz Haber", "ammonia synthesis", "PRODUCES"), ("Carl Bosch", "BASF", "APPLIES_TO"), ("ammonia synthesis", "Chilean saltpetre", "REPLACES")],
     "which 1909-1913 pair industrialised direct ammonia synthesis and what import did it displace",
     "haber bosch ammonia synthesis nitrogen hydrogen basf saltpetre 1913"),
    # --- 14 --- decision
    ("BASF ran the Haber-Bosch loop over a promoted iron catalyst near 200 atmospheres and 450 degrees Celsius; the osmium catalyst Haber used in the lab demo was deemed too scarce for tonnage production.", "decision", "knowledge", False,
     [("Haber-Bosch", "concept"), ("iron catalyst", "concept"), ("osmium catalyst", "concept"), ("BASF", "organization")],
     [("iron catalyst", "osmium catalyst", "REPLACES"), ("BASF", "Haber-Bosch", "APPLIES_TO")],
     "which catalyst did BASF pick for industrial Haber-Bosch ammonia and which lab-scale one did it replace",
     "haber bosch iron osmium catalyst basf ammonia industrial 200 atm"),
    # --- 15 --- milestone
    ("Leo Baekeland filed his Bakelite patent in 1907, describing the first wholly synthetic thermoset from a phenol and formaldehyde condensation that cures into an infusible, insulating solid.", "milestone", "knowledge", False,
     [("Leo Baekeland", "person"), ("Bakelite", "concept"), ("thermoset", "concept"), ("phenol", "concept"), ("formaldehyde", "concept")],
     [("Leo Baekeland", "Bakelite", "PRODUCES"), ("Bakelite", "thermoset", "APPLIES_TO")],
     "who patented the first fully synthetic thermoset in 1907 and which two monomers did it condense",
     "baekeland bakelite phenol formaldehyde thermoset 1907 synthetic patent"),
    # --- 16 --- fact
    ("Bakelite found early traction as insulation in radio housings and electrical switchboards because its cross-linked network refused to flow once cured, a property that predecessors like celluloid lacked entirely.", "fact", "knowledge", False,
     [("Bakelite", "concept"), ("radio housings", "concept"), ("electrical switchboards", "concept"), ("celluloid", "concept")],
     [("Bakelite", "celluloid", "IMPROVES_ON"), ("Bakelite", "radio housings", "APPLIES_TO")],
     "which early electrical applications relied on Bakelite and which plastic did it outperform on heat",
     "bakelite radio insulation switchboard celluloid thermoset cross link"),
    # --- 17 --- architecture
    ("Irving Langmuir and Katharine Blodgett refined monolayer transfer at General Electric in the 1930s, producing the Langmuir-Blodgett film technique that still anchors modern studies of molecular thin films.", "architecture", "knowledge", False,
     [("Irving Langmuir", "person"), ("Katharine Blodgett", "person"), ("General Electric", "organization"), ("Langmuir-Blodgett film", "concept")],
     [("Irving Langmuir", "Langmuir-Blodgett film", "PRODUCES"), ("Katharine Blodgett", "Langmuir-Blodgett film", "PRODUCES"), ("General Electric", "Langmuir-Blodgett film", "APPLIES_TO")],
     "which two General Electric scientists developed the monolayer-transfer film technique that bears their names",
     "langmuir blodgett film monolayer general electric thin film 1930s"),
    # --- 18 --- fact
    ("Langmuir-Blodgett deposition works by compressing an amphiphilic monolayer on a water surface then dipping a substrate through it; each pass lays down one molecular layer in controlled orientation.", "fact", "knowledge", False,
     [("Langmuir-Blodgett", "concept"), ("amphiphilic monolayer", "concept"), ("water surface", "concept"), ("substrate", "concept")],
     [("Langmuir-Blodgett", "amphiphilic monolayer", "APPLIES_TO")],
     "how does Langmuir-Blodgett deposition put down a single molecular layer with controlled orientation",
     "langmuir blodgett deposit amphiphile monolayer water dip substrate"),
    # --- 19 --- reference
    ("Linus Pauling's 1939 monograph The Nature of the Chemical Bond gathered resonance, hybridisation, and electronegativity into a single framework that every undergraduate curriculum still borrows from.", "reference", "knowledge", False,
     [("Linus Pauling", "person"), ("The Nature of the Chemical Bond", "publication"), ("resonance", "concept"), ("hybridisation", "concept"), ("electronegativity", "concept")],
     [("Linus Pauling", "The Nature of the Chemical Bond", "PRODUCES"), ("The Nature of the Chemical Bond", "electronegativity", "SUPPORTS")],
     "which 1939 Pauling monograph packaged resonance, hybridisation, and electronegativity for chemists",
     "pauling nature chemical bond resonance hybridisation electronegativity 1939"),
    # --- 20 --- fact
    ("Pauling's electronegativity scale assigned fluorine the highest value around 4.0 and caesium near 0.7; the numbers fell out of bond-dissociation energy differences rather than any first-principles argument.", "fact", "knowledge", False,
     [("Pauling", "person"), ("electronegativity scale", "concept"), ("fluorine", "concept"), ("caesium", "concept"), ("bond-dissociation energy", "concept")],
     [("electronegativity scale", "bond-dissociation energy", "DEPENDS_ON")],
     "which two elements anchor the extremes of Pauling's electronegativity scale and how were the numbers derived",
     "pauling electronegativity scale fluorine caesium bond dissociation energy"),
    # --- 21 --- milestone
    ("Karl Ziegler and Giulio Natta won the 1963 Nobel in Chemistry for the titanium-aluminium Ziegler-Natta catalysts that polymerise ethylene and propylene at low pressure with stereoregular control previously unavailable.", "milestone", "knowledge", False,
     [("Karl Ziegler", "person"), ("Giulio Natta", "person"), ("Ziegler-Natta catalysts", "concept"), ("ethylene", "concept"), ("propylene", "concept"), ("Nobel in Chemistry", "event")],
     [("Karl Ziegler", "Ziegler-Natta catalysts", "PRODUCES"), ("Giulio Natta", "Ziegler-Natta catalysts", "PRODUCES"), ("Nobel in Chemistry", "Karl Ziegler", "SUPPORTS")],
     "which 1963 Nobel pair introduced titanium-aluminium catalysts for stereoregular polyolefins",
     "ziegler natta catalyst titanium aluminium polyethylene polypropylene 1963 nobel"),
    # --- 22 --- decision
    ("Polyolefin plants switched from high-pressure radical processes to Ziegler-Natta catalysis in the 1950s and 1960s; the change dropped reactor pressures by an order of magnitude and made isotactic polypropylene practical.", "decision", "knowledge", False,
     [("high-pressure radical", "concept"), ("Ziegler-Natta catalysis", "concept"), ("isotactic polypropylene", "concept")],
     [("Ziegler-Natta catalysis", "high-pressure radical", "REPLACES"), ("Ziegler-Natta catalysis", "isotactic polypropylene", "APPLIES_TO")],
     "which polymerisation route did Ziegler-Natta catalysis replace and which stereoregular product did it unlock",
     "ziegler natta polyolefin high pressure radical isotactic polypropylene"),
    # --- 23 --- reference
    ("Robert Woodward and Roald Hoffmann published the Woodward-Hoffmann rules between 1965 and 1969, orbital-symmetry arguments that explain why pericyclic reactions proceed suprafacially or antarafacially under thermal versus photochemical conditions.", "reference", "knowledge", False,
     [("Robert Woodward", "person"), ("Roald Hoffmann", "person"), ("Woodward-Hoffmann rules", "concept"), ("pericyclic reactions", "concept")],
     [("Robert Woodward", "Woodward-Hoffmann rules", "PRODUCES"), ("Roald Hoffmann", "Woodward-Hoffmann rules", "PRODUCES"), ("Woodward-Hoffmann rules", "pericyclic reactions", "APPLIES_TO")],
     "which pair published orbital-symmetry rules that govern thermal and photochemical pericyclic selectivity",
     "woodward hoffmann orbital symmetry pericyclic suprafacial photochemical"),
    # --- 24 --- architecture
    ("The Woodward-Hoffmann rules reduce pericyclic selectivity to electron count parity: 4n+2 electrons prefer suprafacial-suprafacial under thermal activation while 4n electrons flip under photochemical excitation.", "architecture", "knowledge", False,
     [("Woodward-Hoffmann rules", "concept"), ("pericyclic selectivity", "concept"), ("4n+2", "concept"), ("photochemical excitation", "concept")],
     [("Woodward-Hoffmann rules", "pericyclic selectivity", "APPLIES_TO")],
     "how do the Woodward-Hoffmann rules compress pericyclic selectivity into an electron-count parity argument",
     "woodward hoffmann pericyclic 4n 2 suprafacial photochemical thermal"),
    # --- 25 --- decision
    ("Elias James Corey formalised retrosynthetic analysis in the 1960s and collected the methodology in a framework that won him the 1990 Nobel in Chemistry for reshaping how chemists plan total syntheses.", "decision", "knowledge", False,
     [("Elias James Corey", "person"), ("retrosynthetic analysis", "concept"), ("total syntheses", "concept"), ("Nobel in Chemistry", "event")],
     [("Elias James Corey", "retrosynthetic analysis", "PRODUCES"), ("retrosynthetic analysis", "total syntheses", "APPLIES_TO"), ("Nobel in Chemistry", "Elias James Corey", "SUPPORTS")],
     "who formalised retrosynthetic analysis and earned the 1990 Nobel for reshaping total synthesis planning",
     "corey retrosynthesis disconnection 1990 nobel total synthesis"),
    # --- 26 --- architecture
    ("Retrosynthesis flips the usual forward plan: the chemist picks a target, applies disconnections at strategic bonds, and walks backwards to commercial starting materials before committing any flask time.", "architecture", "knowledge", False,
     [("Retrosynthesis", "concept"), ("target", "concept"), ("disconnections", "concept"), ("starting materials", "concept")],
     [("Retrosynthesis", "disconnections", "APPLIES_TO"), ("disconnections", "starting materials", "DEPENDS_ON")],
     "how does the retrosynthesis workflow traverse from a complex target back to commercial starting materials",
     "retrosynthesis target disconnection starting material backward plan"),
    # --- 27 --- decision
    ("Barry Sharpless disclosed asymmetric epoxidation of allylic alcohols in 1980 using titanium tetraisopropoxide with a chiral tartrate additive; the reaction gave high ee across a remarkable substrate scope.", "decision", "knowledge", False,
     [("Barry Sharpless", "person"), ("asymmetric epoxidation", "concept"), ("titanium tetraisopropoxide", "concept"), ("chiral tartrate", "concept"), ("allylic alcohols", "concept")],
     [("Barry Sharpless", "asymmetric epoxidation", "PRODUCES"), ("asymmetric epoxidation", "allylic alcohols", "APPLIES_TO")],
     "which 1980 asymmetric epoxidation used titanium tetraisopropoxide with a chiral tartrate and on what substrates",
     "sharpless asymmetric epoxidation allylic alcohol titanium tartrate 1980"),
    # --- 28 --- architecture
    ("Ryoji Noyori developed BINAP-ruthenium catalysts for asymmetric hydrogenation of ketones and olefins; the work shared the 2001 Nobel in Chemistry alongside Sharpless and Knowles.", "architecture", "knowledge", False,
     [("Ryoji Noyori", "person"), ("BINAP-ruthenium", "concept"), ("asymmetric hydrogenation", "concept"), ("Sharpless", "person"), ("Knowles", "person"), ("Nobel in Chemistry", "event")],
     [("Ryoji Noyori", "BINAP-ruthenium", "PRODUCES"), ("BINAP-ruthenium", "asymmetric hydrogenation", "APPLIES_TO"), ("Nobel in Chemistry", "Ryoji Noyori", "SUPPORTS")],
     "which Noyori catalyst family drove asymmetric hydrogenation and which 2001 Nobel did it share",
     "noyori binap ruthenium asymmetric hydrogenation 2001 nobel sharpless knowles"),
    # --- 29 --- decision
    ("Pharmaceutical process chemists increasingly picked Noyori hydrogenation over classical resolutions once BINAP-ruthenium hit the catalogue; skipping the racemic discard halved the tonnage of starting material per chiral kilo.", "decision", "knowledge", False,
     [("Noyori hydrogenation", "concept"), ("classical resolutions", "concept"), ("BINAP-ruthenium", "concept"), ("Pharmaceutical process chemists", "person")],
     [("Noyori hydrogenation", "classical resolutions", "REPLACES"), ("Pharmaceutical process chemists", "Noyori hydrogenation", "PREFERS")],
     "why did process chemistry shift from classical resolutions to Noyori hydrogenation once BINAP-ruthenium was commercial",
     "noyori hydrogenation classical resolution binap process pharma yield"),
    # --- 30 --- milestone
    ("Robert Grubbs disclosed well-defined ruthenium alkylidene catalysts for olefin metathesis in the 1990s; Richard Schrock's molybdenum systems and Yves Chauvin's mechanism shared the 2005 Nobel in Chemistry with him.", "milestone", "knowledge", False,
     [("Robert Grubbs", "person"), ("ruthenium alkylidene", "concept"), ("olefin metathesis", "concept"), ("Richard Schrock", "person"), ("Yves Chauvin", "person"), ("Nobel in Chemistry", "event")],
     [("Robert Grubbs", "ruthenium alkylidene", "PRODUCES"), ("ruthenium alkylidene", "olefin metathesis", "APPLIES_TO"), ("Nobel in Chemistry", "Robert Grubbs", "SUPPORTS")],
     "which three figures shared the 2005 Nobel for olefin metathesis and what catalyst class did Grubbs contribute",
     "grubbs schrock chauvin ruthenium alkylidene metathesis 2005 nobel"),
    # --- 31 --- architecture
    ("The Chauvin mechanism for olefin metathesis cycles through a metallacyclobutane intermediate; every Grubbs-style catalyst design tunes the ancillary ligand set to stabilise that ring against unproductive decomposition.", "architecture", "knowledge", False,
     [("Chauvin mechanism", "concept"), ("olefin metathesis", "concept"), ("metallacyclobutane", "concept"), ("Grubbs-style catalyst", "concept"), ("ligand", "concept")],
     [("Chauvin mechanism", "olefin metathesis", "APPLIES_TO"), ("Grubbs-style catalyst", "metallacyclobutane", "DEPENDS_ON")],
     "which intermediate anchors the Chauvin mechanism and which design lever do Grubbs catalysts tune around it",
     "chauvin mechanism metathesis metallacyclobutane grubbs ligand intermediate"),
    # --- 32 --- decision
    ("Sharpless and Morten Meldal independently disclosed the copper-catalysed azide-alkyne cycloaddition around 2001-2002, and the reaction became the canonical click chemistry transformation almost overnight.", "decision", "knowledge", False,
     [("Sharpless", "person"), ("Morten Meldal", "person"), ("azide-alkyne cycloaddition", "concept"), ("click chemistry", "concept")],
     [("Sharpless", "click chemistry", "PRODUCES"), ("Morten Meldal", "azide-alkyne cycloaddition", "PRODUCES"), ("azide-alkyne cycloaddition", "click chemistry", "APPLIES_TO")],
     "which two chemists independently reported the copper-catalysed azide-alkyne reaction that launched click chemistry",
     "sharpless meldal copper azide alkyne cycloaddition click 2001 2002"),
    # --- 33 --- preference
    ("Carolyn Bertozzi extended click chemistry into living cells with strain-promoted azide-alkyne cycloaddition chemistry that needs no copper; the bioorthogonal programme shared the 2022 Nobel in Chemistry with Sharpless and Meldal.", "preference", "knowledge", False,
     [("Carolyn Bertozzi", "person"), ("strain-promoted azide-alkyne cycloaddition", "concept"), ("bioorthogonal", "concept"), ("Sharpless", "person"), ("Meldal", "person"), ("Nobel in Chemistry", "event")],
     [("Carolyn Bertozzi", "strain-promoted azide-alkyne cycloaddition", "PRODUCES"), ("strain-promoted azide-alkyne cycloaddition", "bioorthogonal", "APPLIES_TO"), ("Nobel in Chemistry", "Carolyn Bertozzi", "SUPPORTS")],
     "whose copper-free strain-promoted click variant extended the chemistry into living cells and won 2022",
     "bertozzi bioorthogonal strain promoted copper free click 2022 nobel"),
    # --- 34 --- preference
    ("Bioconjugation workflows routinely prefer copper-free click over the copper-catalysed variant once the target is a live cell or whole organism; the cytotoxicity of residual copper outweighs the rate advantage.", "preference", "knowledge", False,
     [("Bioconjugation workflows", "person"), ("copper-free click", "concept"), ("copper-catalysed", "concept"), ("cytotoxicity", "concept")],
     [("Bioconjugation workflows", "copper-free click", "PREFERS"), ("copper-catalysed", "cytotoxicity", "APPLIES_TO")],
     "why do bioconjugation workflows in living systems prefer copper-free click over the copper-catalysed variant",
     "bioconjugation copper free click cytotoxicity live cell organism prefer"),
    # --- 35 --- architecture
    ("Richard Heck, Ei-ichi Negishi, and Akira Suzuki shared the 2010 Nobel in Chemistry for palladium-catalysed cross-coupling reactions that knit aryl halides to carbon nucleophiles with unprecedented generality.", "architecture", "knowledge", False,
     [("Richard Heck", "person"), ("Ei-ichi Negishi", "person"), ("Akira Suzuki", "person"), ("palladium-catalysed cross-coupling", "concept"), ("Nobel in Chemistry", "event")],
     [("Richard Heck", "palladium-catalysed cross-coupling", "PRODUCES"), ("Ei-ichi Negishi", "palladium-catalysed cross-coupling", "PRODUCES"), ("Akira Suzuki", "palladium-catalysed cross-coupling", "PRODUCES"), ("Nobel in Chemistry", "Richard Heck", "SUPPORTS")],
     "which three cross-coupling pioneers shared the 2010 Nobel for palladium-catalysed carbon-carbon bond construction",
     "heck negishi suzuki palladium cross coupling 2010 nobel aryl halide"),
    # --- 36 --- decision
    ("Medicinal chemists default to Suzuki-Miyaura coupling when a biaryl disconnection is viable; the boronic acid partner tolerates functional-group clutter better than the organozinc reagents used in Negishi work.", "decision", "knowledge", False,
     [("Medicinal chemists", "person"), ("Suzuki-Miyaura coupling", "concept"), ("boronic acid", "concept"), ("organozinc", "concept"), ("Negishi", "concept")],
     [("Medicinal chemists", "Suzuki-Miyaura coupling", "PREFERS"), ("Suzuki-Miyaura coupling", "Negishi", "IMPROVES_ON")],
     "why does medicinal chemistry reach for Suzuki-Miyaura over Negishi when a biaryl disconnection is available",
     "suzuki miyaura biaryl boronic acid functional group tolerance negishi"),
    # --- 37 --- architecture
    ("Palladium cross-coupling cycles through oxidative addition of the aryl halide, transmetalation with the nucleophile, and reductive elimination to release the product; ligand bulk tunes every step.", "architecture", "knowledge", False,
     [("Palladium cross-coupling", "concept"), ("oxidative addition", "concept"), ("transmetalation", "concept"), ("reductive elimination", "concept"), ("ligand", "concept")],
     [("Palladium cross-coupling", "oxidative addition", "APPLIES_TO"), ("reductive elimination", "Palladium cross-coupling", "APPLIES_TO")],
     "which three catalytic steps make up a palladium cross-coupling cycle and what role does ligand bulk play",
     "palladium cycle oxidative addition transmetalation reductive elimination ligand"),
    # --- 38 --- problem
    ("Omar Yaghi reported the first reticular metal-organic framework MOF-5 in 1999, crystallising zinc clusters with terephthalate linkers to give a stable porous solid with unprecedented surface area.", "problem", "knowledge", False,
     [("Omar Yaghi", "person"), ("MOF-5", "concept"), ("metal-organic framework", "concept"), ("zinc clusters", "concept"), ("terephthalate", "concept")],
     [("Omar Yaghi", "MOF-5", "PRODUCES"), ("MOF-5", "metal-organic framework", "APPLIES_TO")],
     "who crystallised the zinc-terephthalate MOF-5 in 1999 and what porosity milestone did it set",
     "yaghi mof 5 metal organic framework zinc terephthalate reticular 1999"),
    # --- 39 --- architecture
    ("Reticular chemistry treats metal-organic frameworks as tinker-toy networks: a secondary building unit fixes the node geometry, and organic linkers of chosen length set the pore aperture of the final crystal.", "architecture", "knowledge", False,
     [("Reticular chemistry", "concept"), ("metal-organic frameworks", "concept"), ("secondary building unit", "concept"), ("organic linkers", "concept"), ("pore aperture", "concept")],
     [("Reticular chemistry", "metal-organic frameworks", "APPLIES_TO"), ("organic linkers", "pore aperture", "DEPENDS_ON")],
     "how does reticular chemistry decompose MOF design into node geometry and linker length",
     "reticular chemistry mof secondary building unit linker pore aperture"),
    # --- 40 --- architecture
    ("MOFs have been prototyped for hydrogen storage, carbon dioxide capture, and water harvesting from desert air; each application tunes aperture size, hydrophilicity, and framework stability independently.", "architecture", "knowledge", False,
     [("MOFs", "concept"), ("hydrogen storage", "concept"), ("carbon dioxide capture", "concept"), ("water harvesting", "concept"), ("aperture size", "concept")],
     [("MOFs", "hydrogen storage", "APPLIES_TO"), ("MOFs", "water harvesting", "APPLIES_TO")],
     "which three application classes have MOFs been tuned for and which material parameters change per target",
     "mof hydrogen storage carbon capture water harvesting aperture"),
    # --- 41 --- milestone
    ("Sumio Iijima identified multi-walled carbon nanotubes in arc-discharge soot at NEC in 1991 using high-resolution transmission electron microscopy; a single-walled variant followed two years later.", "milestone", "knowledge", False,
     [("Sumio Iijima", "person"), ("multi-walled carbon nanotubes", "concept"), ("arc-discharge", "concept"), ("NEC", "organization"), ("single-walled", "concept")],
     [("Sumio Iijima", "multi-walled carbon nanotubes", "PRODUCES"), ("Sumio Iijima", "NEC", "APPLIES_TO")],
     "who characterised multi-walled carbon nanotubes in 1991 and at which industrial lab did it happen",
     "iijima carbon nanotube arc discharge nec 1991 multi walled single"),
    # --- 42 --- reference
    ("Iijima's 1991 Nature paper remains the standard citation when dating the carbon nanotube field; the preceding electron-microscopy hints in Soviet literature rarely feature in introductory textbooks.", "reference", "knowledge", False,
     [("Iijima", "person"), ("Nature paper", "publication"), ("carbon nanotube", "concept"), ("Soviet literature", "publication")],
     [("Iijima", "Nature paper", "PRODUCES"), ("Nature paper", "carbon nanotube", "SUPPORTS")],
     "which 1991 publication anchors the carbon nanotube field and what earlier record tends to be omitted from textbooks",
     "iijima nature 1991 carbon nanotube soviet electron microscopy citation"),
    # --- 43 --- noise
    ("The stockroom keeps losing its pack of 10 mm cuvettes every semester and someone always blames undergraduates who weren't even enrolled in the class that term.", "fact", "noise", True, [], [], None, None),
    # --- 44 --- milestone
    ("Harry Kroto, Robert Curl, and Richard Smalley discovered buckminsterfullerene C60 in laser-vaporised graphite in 1985; the cage geometry mirrored the geodesic domes they invoked while naming it.", "milestone", "knowledge", False,
     [("Harry Kroto", "person"), ("Robert Curl", "person"), ("Richard Smalley", "person"), ("buckminsterfullerene C60", "concept"), ("graphite", "concept"), ("geodesic domes", "concept")],
     [("Harry Kroto", "buckminsterfullerene C60", "PRODUCES"), ("Robert Curl", "buckminsterfullerene C60", "PRODUCES"), ("Richard Smalley", "buckminsterfullerene C60", "PRODUCES")],
     "which trio discovered C60 buckminsterfullerene in 1985 and what architectural metaphor inspired the name",
     "kroto curl smalley fullerene c60 graphite geodesic dome 1985"),
    # --- 45 --- fact
    ("C60 is a truncated icosahedron with sixty equivalent carbon vertices, twelve pentagonal faces, and twenty hexagonal faces; the three-dimensional aromaticity was exactly what Kroto suspected from interstellar spectra.", "fact", "knowledge", False,
     [("C60", "concept"), ("truncated icosahedron", "concept"), ("pentagonal faces", "concept"), ("hexagonal faces", "concept"), ("interstellar spectra", "concept")],
     [("C60", "truncated icosahedron", "APPLIES_TO")],
     "which polyhedron describes C60 geometry and how many pentagonal versus hexagonal faces does it carry",
     "c60 truncated icosahedron pentagon hexagon interstellar fullerene"),
    # --- 46 --- milestone
    ("Andre Geim and Konstantin Novoselov isolated single-layer graphene from graphite with adhesive tape at the University of Manchester in 2004, work that won the 2010 Nobel in Physics.", "milestone", "knowledge", False,
     [("Andre Geim", "person"), ("Konstantin Novoselov", "person"), ("graphene", "concept"), ("University of Manchester", "organization"), ("Nobel in Physics", "event")],
     [("Andre Geim", "graphene", "PRODUCES"), ("Konstantin Novoselov", "graphene", "PRODUCES"), ("Nobel in Physics", "Andre Geim", "SUPPORTS")],
     "which Manchester pair isolated graphene with adhesive tape in 2004 and which Nobel did it earn",
     "geim novoselov graphene manchester adhesive tape 2010 nobel physics 2004"),
    # --- 47 --- preference
    ("Condensed-matter labs often prefer mechanical exfoliation over chemical vapour deposition when they need the cleanest single-layer graphene for transport measurements; the tape flakes show the lowest defect densities.", "preference", "knowledge", False,
     [("Condensed-matter labs", "person"), ("mechanical exfoliation", "concept"), ("chemical vapour deposition", "concept"), ("graphene", "concept"), ("transport measurements", "concept")],
     [("Condensed-matter labs", "mechanical exfoliation", "PREFERS"), ("mechanical exfoliation", "chemical vapour deposition", "IMPROVES_ON")],
     "why do condensed-matter labs often reach for mechanical exfoliation over CVD when probing graphene transport",
     "graphene exfoliation cvd mechanical tape transport defect prefer"),
    # --- 48 --- preference
    ("Industrial scale-up, by contrast, prefers chemical vapour deposition on copper foils for graphene films; wafer-scale area outweighs the residual grain boundaries for most device targets.", "preference", "knowledge", False,
     [("Industrial scale-up", "person"), ("chemical vapour deposition", "concept"), ("copper foils", "concept"), ("graphene films", "concept"), ("grain boundaries", "concept")],
     [("Industrial scale-up", "chemical vapour deposition", "PREFERS"), ("chemical vapour deposition", "copper foils", "APPLIES_TO")],
     "why does industrial graphene production prefer CVD on copper foils despite grain boundary defects",
     "graphene cvd copper foil industrial wafer scale grain boundary"),
    # --- 49 --- problem
    ("Early graphene field-effect devices suffered large contact resistance from metal electrodes; edge-contact geometries in hexagonal boron nitride stacks eventually cut the parasitic drop by nearly an order of magnitude.", "problem", "knowledge", False,
     [("graphene field-effect devices", "concept"), ("contact resistance", "concept"), ("metal electrodes", "concept"), ("edge-contact", "concept"), ("hexagonal boron nitride", "concept")],
     [("edge-contact", "metal electrodes", "IMPROVES_ON"), ("edge-contact", "hexagonal boron nitride", "DEPENDS_ON")],
     "which contact geometry reduced the parasitic resistance in graphene field-effect devices",
     "graphene field effect contact resistance edge hexagonal boron nitride"),
    # --- 50 --- problem
    ("Fullerene synthesis using arc-discharge produced milligram quantities contaminated with soot and higher cages; chromatography on alumina with a toluene eluent eventually gave pure C60 samples at research scale.", "problem", "knowledge", False,
     [("Fullerene synthesis", "concept"), ("arc-discharge", "concept"), ("chromatography", "concept"), ("alumina", "concept"), ("C60", "concept")],
     [("chromatography", "Fullerene synthesis", "APPLIES_TO"), ("chromatography", "arc-discharge", "IMPROVES_ON")],
     "which purification step pulled research-grade C60 out of arc-discharge soot after the 1985 discovery",
     "fullerene c60 arc discharge chromatography alumina toluene soot purify"),
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
