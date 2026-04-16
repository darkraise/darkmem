"""One-off emitter for shared-base batch-264 — knowledge domain (archaeology: methods, landmark sites, cultures, people, institutions).

Writes 50 rows to data/v2/shared/batch_264.tmp.jsonl with ids shared-13151..13200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_264.tmp.jsonl"
ID_OFFSET = 13150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Stratigraphy on the Göbekli Tepe T-pillar enclosures was recorded as a Harris matrix before any section drawing, so the superimposition of Layer III megaliths over Layer II walls reads unambiguously in the archive.", "architecture", "knowledge", False,
     [("Göbekli Tepe", "place"), ("Harris matrix", "method"), ("Layer III", "concept"), ("Layer II", "concept")],
     [("Harris matrix", "Göbekli Tepe", "APPLIES_TO")],
     "how did the excavation at the T-pillar site record overlapping layers before the paper section drawings",
     "gobekli tepe harris matrix stratigraphy layer iii ii pillar"),
    # --- 2 ---
    ("Radiocarbon dating by C-14 AMS on the charred grain from Çatalhöyük building 77 returned a calibrated range of 7100 to 6900 BCE, narrower than the earlier bulk-sample runs by roughly two centuries.", "decision", "knowledge", False,
     [("C-14 AMS", "method"), ("Çatalhöyük", "place"), ("building 77", "concept")],
     [("C-14 AMS", "Çatalhöyük", "APPLIES_TO")],
     "which dating technique narrowed the Neolithic grain age at the Konya plain tell and by how much",
     "catalhoyuk radiocarbon ams charred grain building 77 calibrated"),
    # --- 3 ---
    ("Kathleen Kenyon's trench at Jericho is the textbook reference for section-based excavation; her stratigraphic discipline from the 1950s still anchors Levantine chronologies today.", "reference", "knowledge", False,
     [("Kathleen Kenyon", "person"), ("Jericho", "place"), ("section-based excavation", "method")],
     [("Kathleen Kenyon", "Jericho", "APPLIES_TO")],
     "whose mid-century trench at the Jordan Valley tell became the reference example for section recording",
     "kenyon jericho section trench stratigraphy levantine chronology"),
    # --- 4 ---
    ("Ian Hodder ran the post-processual Çatalhöyük programme from 1993 to 2017, deliberately pairing micromorphology on floor sequences with reflexive field journals so interpretation travelled with the data.", "milestone", "knowledge", False,
     [("Ian Hodder", "person"), ("Çatalhöyük", "place"), ("micromorphology", "method")],
     [("Ian Hodder", "Çatalhöyük", "APPLIES_TO"), ("micromorphology", "Çatalhöyük", "APPLIES_TO")],
     "which post-processual director paired floor micromorphology with field journals at the Konya site",
     "hodder catalhoyuk post processual micromorphology floor reflexive"),
    # --- 5 ---
    ("LiDAR survey over Tikal flown in 2018 revealed roughly 60000 previously unmapped Maya structures under the Petén canopy, revising density estimates for the Classic period by an order of magnitude.", "milestone", "knowledge", False,
     [("LiDAR survey", "method"), ("Tikal", "place"), ("Maya", "concept"), ("Petén", "place")],
     [("LiDAR survey", "Tikal", "APPLIES_TO")],
     "which airborne remote-sensing run over the Guatemalan rainforest rewrote Classic Maya settlement density",
     "lidar tikal maya peten 2018 canopy structure density classic"),
    # --- 6 ---
    ("The dendrochronology on oak beams from Mycenae's Treasury of Atreus cross-dated against the Aegean master chronology places construction tightly around 1250 BCE, agreeing with Wiener's Late Helladic IIIB phasing.", "reference", "knowledge", False,
     [("dendrochronology", "method"), ("Mycenae", "place"), ("Treasury of Atreus", "concept"), ("Late Helladic IIIB", "concept")],
     [("dendrochronology", "Mycenae", "APPLIES_TO")],
     "which tree-ring technique pinned the Mycenaean tholos tomb to the thirteenth century BCE",
     "dendrochronology mycenae atreus late helladic iiib 1250 bce tholos"),
    # --- 7 ---
    ("Howard Carter's 1922 discovery of KV62 at the Valley of the Kings is the archetype for intact-tomb documentation; the card-index system he used for Tutankhamun's grave goods runs to over 5000 objects.", "milestone", "knowledge", False,
     [("Howard Carter", "person"), ("KV62", "place"), ("Valley of the Kings", "place"), ("Tutankhamun", "person")],
     [("Howard Carter", "KV62", "APPLIES_TO"), ("KV62", "Valley of the Kings", "APPLIES_TO")],
     "which 1922 find in the Theban necropolis set the standard for cataloguing intact royal burials",
     "carter kv62 tutankhamun 1922 valley kings card index 5000 object"),
    # --- 8 ---
    ("Ground-penetrating radar GPR and magnetometry were combined at Stonehenge during the Hidden Landscapes Project, locating a ring of buried pits at Durrington Walls without turning a single spade of earth.", "architecture", "knowledge", False,
     [("GPR", "method"), ("magnetometry", "method"), ("Stonehenge", "place"), ("Durrington Walls", "place")],
     [("GPR", "Stonehenge", "APPLIES_TO"), ("magnetometry", "Durrington Walls", "APPLIES_TO")],
     "which pair of geophysical surveys found the buried pit ring near the Wiltshire henge without excavation",
     "gpr magnetometry stonehenge durrington walls hidden landscapes pit"),
    # --- 9 ---
    ("The potassium-argon dating on volcanic tuff layers sandwiching hominin fossils at Olduvai Gorge is what let Louis Leakey and Mary Leakey push Zinjanthropus back to 1.75 million years in the 1959 Nature note.", "reference", "knowledge", False,
     [("potassium-argon", "method"), ("Olduvai Gorge", "place"), ("Louis Leakey", "person"), ("Mary Leakey", "person"), ("Zinjanthropus", "concept")],
     [("potassium-argon", "Olduvai Gorge", "APPLIES_TO")],
     "which radiometric method underwrote the 1.75 million year date for the East African hominid the Leakeys announced",
     "potassium argon olduvai leakey zinjanthropus 1959 tuff 1 75 million"),
    # --- 10. noise ---
    ("Somebody in the departmental lounge is again warming fish curry in the microwave despite the three separate laminated signs asking them not to.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The thermoluminescence on hearth-fired ceramics from the Natufian occupation at Ain Mallaha produced a 12000 BP result that corroborated the independent C-14 AMS runs on the same context.", "architecture", "knowledge", False,
     [("thermoluminescence", "method"), ("Natufian", "concept"), ("Ain Mallaha", "place"), ("C-14 AMS", "method")],
     [("thermoluminescence", "Natufian", "APPLIES_TO")],
     "which luminescence method on fired hearth pottery agreed with AMS radiocarbon in the Epipalaeolithic Levant",
     "thermoluminescence natufian ain mallaha ceramic hearth 12000 bp"),
    # --- 12 ---
    ("The uranium-series dating on flowstone capping the Denisova Cave Layer 11 deposits bracketed the juvenile finger-bone between roughly 76000 and 52000 years, consistent with the aDNA age estimate.", "fact", "knowledge", False,
     [("uranium-series", "method"), ("Denisova Cave", "place"), ("Layer 11", "concept"), ("aDNA", "method")],
     [("uranium-series", "Denisova Cave", "APPLIES_TO")],
     "which dating technique on cave flowstone bracketed the Altai finger-bone age alongside ancient DNA work",
     "uranium series denisova cave layer 11 finger bone flowstone adna"),
    # --- 13 ---
    ("The aDNA sequencing from the Denisova phalanx was done by the Max Planck team in 2010, establishing Denisovans as a sister lineage to Neanderthals and rewriting Late Pleistocene hominin taxonomy.", "milestone", "knowledge", False,
     [("aDNA", "method"), ("Denisova", "concept"), ("Max Planck", "organization"), ("Neanderthals", "concept")],
     [("aDNA", "Denisova", "APPLIES_TO")],
     "which 2010 sequencing result established a new sister lineage to Neanderthals from a single Altai bone",
     "adna denisova phalanx max planck 2010 neanderthal sister lineage"),
    # --- 14 ---
    ("X-ray fluorescence XRF on Olmec jade celts sourced them to a single Motagua Valley quarry, overturning a long-standing assumption that multiple source regions supplied San Lorenzo workshops.", "decision", "knowledge", False,
     [("XRF", "method"), ("Olmec", "concept"), ("Motagua Valley", "place"), ("San Lorenzo", "place")],
     [("XRF", "Olmec", "APPLIES_TO")],
     "which portable elemental technique traced Gulf Coast jade celts back to a single Guatemalan source",
     "xrf olmec jade celt motagua san lorenzo provenance quarry"),
    # --- 15 ---
    ("The stable isotope analysis of tooth enamel on the Machu Picchu burials showed roughly a third of the retainer population grew up outside the Cuzco heartland, matching chronicle accounts of yanakuna service.", "fact", "knowledge", False,
     [("stable isotope analysis", "method"), ("Machu Picchu", "place"), ("Cuzco", "place"), ("yanakuna", "concept")],
     [("stable isotope analysis", "Machu Picchu", "APPLIES_TO")],
     "which enamel-based method confirmed non-local origins for a third of the Inca estate's retainer burials",
     "isotope enamel machu picchu cuzco yanakuna retainer provenance"),
    # --- 16 ---
    ("Lewis Binford's 1962 Archaeology as Anthropology paper is still the defining statement of processual method; the insistence on middle-range theory frames how faunal assemblages at Olduvai are read today.", "reference", "knowledge", False,
     [("Lewis Binford", "person"), ("processual method", "method"), ("middle-range theory", "concept"), ("Olduvai", "place")],
     [("Lewis Binford", "processual method", "APPLIES_TO")],
     "which 1962 paper grounds the processual reading of East African faunal assemblages",
     "binford 1962 archaeology anthropology processual middle range olduvai"),
    # --- 17 ---
    ("Colin Renfrew's tree-ring calibration of radiocarbon dates in the 1970s collapsed the diffusionist chronology for European megaliths; Newgrange came out older than the Mycenaean tholoi it had supposedly inspired.", "decision", "knowledge", False,
     [("Colin Renfrew", "person"), ("radiocarbon", "method"), ("Newgrange", "place"), ("Mycenaean tholoi", "concept")],
     [("Colin Renfrew", "radiocarbon", "APPLIES_TO")],
     "whose 1970s recalibration made the Boyne Valley passage tomb predate the Aegean tholoi it was said to copy",
     "renfrew tree ring calibration newgrange mycenaean diffusion megalith"),
    # --- 18 ---
    ("The Uruk IV tablet phase, dated by stratified C-14 AMS at Warka, fixes the proto-cuneiform debut around 3200 BCE, anchoring the broader Sumerian administrative sequence.", "architecture", "knowledge", False,
     [("Uruk", "place"), ("C-14 AMS", "method"), ("Warka", "place"), ("proto-cuneiform", "concept")],
     [("C-14 AMS", "Uruk", "APPLIES_TO")],
     "which stratified radiocarbon sequence at the southern Mesopotamian tell pinned proto-cuneiform to circa 3200 BCE",
     "uruk iv warka proto cuneiform 3200 bce c14 ams sumerian tablet"),
    # --- 19 ---
    ("Ur excavations by Leonard Woolley during 1922 to 1934 produced the Royal Tombs PG/789 and PG/800, whose lyre and standard of Ur are now the British Museum's flagship Sumerian pieces.", "milestone", "knowledge", False,
     [("Ur", "place"), ("Leonard Woolley", "person"), ("Royal Tombs", "concept"), ("British Museum", "organization")],
     [("Leonard Woolley", "Ur", "APPLIES_TO"), ("British Museum", "Ur", "APPLIES_TO")],
     "whose interwar dig at the southern Iraq tell supplied the British Museum's headline Sumerian lyre and standard",
     "woolley ur 1922 1934 royal tomb pg 789 800 british museum"),
    # --- 20 ---
    ("Knossos architecture under Arthur Evans was reconstructed in concrete on the Minoan palace from 1900 onward; the choice still splits field opinion between preservation advocates and critics of speculative rebuild.", "problem", "knowledge", False,
     [("Knossos", "place"), ("Arthur Evans", "person"), ("Minoan palace", "concept")],
     [("Arthur Evans", "Knossos", "APPLIES_TO")],
     "which early twentieth-century concrete reconstruction at the Cretan palace still divides the discipline",
     "evans knossos minoan concrete reconstruction 1900 preservation"),
    # --- 21 ---
    ("Troy / Hisarlik's nine-layer sequence, from Troy I through Troy IX, was first separated by Heinrich Schliemann and refined by Carl Blegen's Cincinnati expedition in the 1930s.", "architecture", "knowledge", False,
     [("Troy", "place"), ("Hisarlik", "place"), ("Heinrich Schliemann", "person"), ("Carl Blegen", "person")],
     [("Heinrich Schliemann", "Troy", "APPLIES_TO"), ("Carl Blegen", "Troy", "APPLIES_TO")],
     "which two excavators between them produced the nine-layer chronology of the northwest Anatolian tell",
     "troy hisarlik nine layer schliemann blegen cincinnati i through ix"),
    # --- 22 ---
    ("Giza pyramid construction chronology rests on C-14 AMS of mortar charcoal inclusions; the Khufu pyramid clusters around 2570 BCE, a century earlier than older bulk-date ranges had placed it.", "fact", "knowledge", False,
     [("Giza", "place"), ("C-14 AMS", "method"), ("Khufu", "person")],
     [("C-14 AMS", "Giza", "APPLIES_TO")],
     "which radiocarbon approach on mortar charcoal tightened the Old Kingdom Great Pyramid date",
     "giza khufu pyramid c14 ams mortar charcoal 2570 bce chronology"),
    # --- 23 ---
    ("Pompeii's plaster-cast technique for voids in the ash was perfected by Giuseppe Fiorelli in 1863; every cast since, including the more recent resin variants, inherits that field protocol.", "reference", "knowledge", False,
     [("Pompeii", "place"), ("Giuseppe Fiorelli", "person"), ("plaster-cast", "method")],
     [("Giuseppe Fiorelli", "Pompeii", "APPLIES_TO")],
     "which 1863 Italian superintendent invented the cast-the-void method still followed at the Vesuvian city",
     "pompeii fiorelli 1863 plaster cast void ash resin vesuvian"),
    # --- 24 ---
    ("Herculaneum's waterlogged boathouses preserved an intact skeletal assemblage of 300 individuals; stable isotope analysis on their bones reconstructed a diet heavier in marine protein than Pompeii's nearby inland fallen.", "fact", "knowledge", False,
     [("Herculaneum", "place"), ("stable isotope analysis", "method"), ("Pompeii", "place")],
     [("stable isotope analysis", "Herculaneum", "APPLIES_TO")],
     "which bone-chemistry study at the Vesuvian coastal site showed a more marine-leaning diet than its neighbour",
     "herculaneum boathouse isotope marine protein pompeii diet skeleton"),
    # --- 25 ---
    ("The Nazca Lines mapping programme by Maria Reiche between 1946 and her death in 1998 produced the first systematic geoglyph catalogue; modern drone LiDAR now fills in features her ground traverses could not resolve.", "milestone", "knowledge", False,
     [("Nazca Lines", "place"), ("Maria Reiche", "person"), ("LiDAR", "method")],
     [("Maria Reiche", "Nazca Lines", "APPLIES_TO"), ("LiDAR", "Nazca Lines", "APPLIES_TO")],
     "whose decades of ground mapping on the Peruvian pampa formed the first geoglyph catalogue later supplemented by drone survey",
     "nazca reiche 1946 1998 geoglyph drone lidar pampa catalogue"),
    # --- 26 ---
    ("Teotihuacan's Pyramid of the Sun was cored in 2003 by the Oriental Institute Chicago team; the obsidian micro-debris recovered from the fill was fingerprinted by XRF to the Pachuca source.", "decision", "knowledge", False,
     [("Teotihuacan", "place"), ("Oriental Institute Chicago", "organization"), ("XRF", "method"), ("Pachuca", "place")],
     [("Oriental Institute Chicago", "Teotihuacan", "APPLIES_TO"), ("XRF", "Teotihuacan", "APPLIES_TO")],
     "which 2003 coring programme at the central Mexican pyramid sourced its obsidian to a specific Hidalgo outcrop",
     "teotihuacan sun pyramid 2003 oriental institute chicago xrf pachuca"),
    # --- 27 ---
    ("Chichén Itzá's Sacred Cenote was dredged by Edward Thompson from 1904 to 1910 and again with airlift by the Peabody Museum in the 1960s; both campaigns fed the bulk of Maya gold at the Smithsonian and Peabody.", "decision", "knowledge", False,
     [("Chichén Itzá", "place"), ("Edward Thompson", "person"), ("Peabody Museum", "organization"), ("Smithsonian", "organization")],
     [("Edward Thompson", "Chichén Itzá", "APPLIES_TO"), ("Peabody Museum", "Chichén Itzá", "APPLIES_TO")],
     "which two cenote-dredging campaigns supplied the bulk of Maya gold objects now in major US museums",
     "chichen itza cenote thompson 1904 peabody 1960 smithsonian dredge"),
    # --- 28 ---
    ("Caral in the Supe Valley was confirmed as third-millennium BCE urbanism by Ruth Shady's 2001 C-14 AMS runs, pushing Andean civic monumentality back nearly a thousand years before Chavín.", "decision", "knowledge", False,
     [("Caral", "place"), ("Supe Valley", "place"), ("Ruth Shady", "person"), ("C-14 AMS", "method"), ("Chavín", "concept")],
     [("Ruth Shady", "Caral", "APPLIES_TO"), ("C-14 AMS", "Caral", "APPLIES_TO")],
     "whose 2001 radiocarbon work on the coastal Peruvian site pushed Andean monumentality a millennium earlier than Chavín",
     "caral supe shady 2001 c14 ams chavin urbanism third millennium"),
    # --- 29 ---
    ("Angkor Wat's moat sediment cores dated by C-14 AMS and correlated with dendrochronology droughts in the region support a 15th-century climate-stress hypothesis for the Khmer capital's decline.", "fact", "knowledge", False,
     [("Angkor Wat", "place"), ("C-14 AMS", "method"), ("dendrochronology", "method"), ("Khmer", "concept")],
     [("C-14 AMS", "Angkor Wat", "APPLIES_TO"), ("dendrochronology", "Angkor Wat", "APPLIES_TO")],
     "which combined moat-sediment and tree-ring evidence supports a drought-driven decline at the Cambodian capital",
     "angkor moat sediment c14 tree ring drought khmer 15th century"),
    # --- 30 ---
    ("Atapuerca's Sima de los Huesos yielded over 6500 hominin fossils from a single pit; uranium-series dating on bone apatite puts the accumulation around 430000 years, within the Homo heidelbergensis range.", "fact", "knowledge", False,
     [("Atapuerca", "place"), ("Sima de los Huesos", "place"), ("uranium-series", "method"), ("Homo heidelbergensis", "concept")],
     [("uranium-series", "Sima de los Huesos", "APPLIES_TO")],
     "which Spanish pit site holds 6500 hominin fossils dated around 430000 years by uranium-series",
     "atapuerca sima huesos uranium series heidelbergensis 430000 pit"),
    # --- 31 ---
    ("Zhoukoudian Peking Man's Locality 1 fauna was re-dated with uranium-series and ESR in 2009 to roughly 770000 BP, aligning the Homo erectus teeth with MIS 19 rather than the older MIS 16 estimate.", "fact", "knowledge", False,
     [("Zhoukoudian", "place"), ("Peking Man", "concept"), ("uranium-series", "method"), ("Homo erectus", "concept")],
     [("uranium-series", "Zhoukoudian", "APPLIES_TO")],
     "which 2009 redating aligned the Beijing-area Homo erectus teeth with the MIS 19 interglacial",
     "zhoukoudian peking man u series esr 770000 mis 19 erectus"),
    # --- 32 ---
    ("Lascaux cave was closed to the public in 1963 after CO2 and fungal outbreaks damaged the Hall of the Bulls; Chauvet was never opened at all, and a replica handles visitor traffic instead.", "decision", "knowledge", False,
     [("Lascaux", "place"), ("Chauvet", "place"), ("Hall of the Bulls", "concept")],
     [("Lascaux", "Chauvet", "APPLIES_TO")],
     "which 1963 access decision at the French painted caves set the pattern later followed by its younger neighbour",
     "lascaux 1963 closure chauvet replica hall bulls co2 fungal"),
    # --- 33 ---
    ("The Metropolitan Museum's Cesnola Collection from Cyprus has been reviewed under XRF provenance analysis since 2015; a non-trivial fraction of the allegedly Cypriot terracottas returned eastern Aegean signatures.", "decision", "knowledge", False,
     [("Metropolitan", "organization"), ("Cesnola Collection", "concept"), ("XRF", "method"), ("Cyprus", "place")],
     [("Metropolitan", "Cesnola Collection", "APPLIES_TO"), ("XRF", "Cesnola Collection", "APPLIES_TO")],
     "which post-2015 provenance programme on the Met's Cypriot collection challenged its stated origins",
     "metropolitan cesnola cyprus xrf provenance 2015 aegean terracotta"),
    # --- 34 ---
    ("The Cambridge McDonald Institute prefers Bayesian modelling of radiocarbon series over eyeballed single dates; its OxCal-based chronologies for British Neolithic causewayed enclosures reset start dates by roughly a century.", "preference", "knowledge", False,
     [("Cambridge McDonald Institute", "organization"), ("Bayesian modelling", "method"), ("OxCal", "tool"), ("causewayed enclosures", "concept")],
     [("Cambridge McDonald Institute", "Bayesian modelling", "APPLIES_TO")],
     "which Cambridge institute insists on Bayesian chronology modelling for British Neolithic radiocarbon series",
     "cambridge mcdonald bayesian oxcal causewayed enclosure neolithic"),
    # --- 35 ---
    ("Harappan Indus Valley provenance work on steatite seals favours XRF over petrography; the Mohenjo-daro workshop signature turns out to be distinguishable from the Harappa one despite the visual similarity.", "preference", "knowledge", False,
     [("Harappan", "concept"), ("XRF", "method"), ("Mohenjo-daro", "place"), ("Harappa", "place")],
     [("XRF", "Harappan", "APPLIES_TO")],
     "which non-destructive elemental technique is preferred over petrography for Indus Valley steatite seals",
     "harappan indus xrf steatite mohenjo daro seal petrography"),
    # --- 36 ---
    ("The Akkadian empire collapse around 2150 BCE is increasingly tied to the 4.2 ka event via speleothem stable isotope analysis from Mesopotamian cave records; the climate-collapse reading is not universally accepted.", "problem", "knowledge", False,
     [("Akkadian", "concept"), ("4.2 ka event", "concept"), ("stable isotope analysis", "method")],
     [("stable isotope analysis", "Akkadian", "APPLIES_TO")],
     "which isotope-based climate event is linked to the late-third-millennium Akkadian collapse and why is the link contested",
     "akkadian 2150 bce 4 2 ka speleothem isotope collapse mesopotamia"),
    # --- 37 ---
    ("The Hittite capital Hattusa's tablet archive was excavated by Hugo Winckler starting in 1906; cuneiform Luwian and Hittite were later cross-referenced against Boğazköy Archive accession numbers still in use.", "decision", "knowledge", False,
     [("Hittite", "concept"), ("Hattusa", "place"), ("Hugo Winckler", "person"), ("Boğazköy Archive", "concept")],
     [("Hugo Winckler", "Hattusa", "APPLIES_TO"), ("Hattusa", "Boğazköy Archive", "APPLIES_TO")],
     "whose 1906 excavation at the Anatolian capital produced the archive whose accession numbers still anchor Hittitology",
     "hittite hattusa winckler 1906 bogazkoy archive luwian cuneiform"),
    # --- 38 ---
    ("The Sea Peoples question keeps picking up new data: stable isotope analysis on Philistine burials at Ashkelon from 2019 suggested non-local origins for part of the incoming population, cautiously supporting migration models.", "decision", "knowledge", False,
     [("Sea Peoples", "concept"), ("stable isotope analysis", "method"), ("Philistine", "concept"), ("Ashkelon", "place")],
     [("stable isotope analysis", "Ashkelon", "APPLIES_TO")],
     "which 2019 isotope study on southern Levant burials cautiously supported a migration reading of the Sea Peoples",
     "sea peoples philistine ashkelon 2019 isotope migration levant"),
    # --- 39 ---
    ("The Smithsonian's repatriation policy under NAGPRA has returned over 6000 sets of ancestral remains since 1990, and recent X-ray fluorescence XRF on grave-goods has been done in-situ on tribal land instead of at the museum.", "decision", "knowledge", False,
     [("Smithsonian", "organization"), ("NAGPRA", "concept"), ("XRF", "method")],
     [("Smithsonian", "NAGPRA", "APPLIES_TO"), ("XRF", "Smithsonian", "APPLIES_TO")],
     "which US federal statute reshaped the Smithsonian's handling of ancestral remains and how did that change XRF fieldwork",
     "smithsonian nagpra 1990 repatriation xrf in situ tribal"),
    # --- 40 ---
    ("The magnetometry over the Amarna workers' village revealed a previously unmapped square of ovens outside the walled precinct; excavation followed the geophysical anomaly map and hit the feature on the first trench.", "architecture", "knowledge", False,
     [("magnetometry", "method"), ("Amarna", "place"), ("workers' village", "concept")],
     [("magnetometry", "Amarna", "APPLIES_TO")],
     "which geophysical survey at the Eighteenth Dynasty workers' village guided the trench directly onto a bread-oven cluster",
     "magnetometry amarna workers village oven anomaly geophysics"),
    # --- 41 ---
    ("The micromorphology thin-sections from the Natufian floor at Eynan distinguished in-situ plant processing from post-depositional trampling, a distinction bulk flotation could not make on the same samples.", "architecture", "knowledge", False,
     [("micromorphology", "method"), ("Natufian", "concept"), ("Eynan", "place")],
     [("micromorphology", "Natufian", "APPLIES_TO")],
     "which thin-section technique at the Epipalaeolithic Levantine site separated in-situ plant work from trampling",
     "micromorphology natufian eynan thin section plant trampling flotation"),
    # --- 42 ---
    ("Knossos Linear B tablets were baked accidentally by the destruction fire around 1375 BCE; the taphonomic accident is why Mycenae's clay archive survived in readable form while the papyrus and parchment did not.", "architecture", "knowledge", False,
     [("Knossos", "place"), ("Linear B", "concept"), ("Mycenae", "place")],
     [("Knossos", "Linear B", "APPLIES_TO")],
     "which destruction-fire accident preserved the Aegean palace clay archive when organic media had no chance",
     "knossos linear b 1375 bce fire bake mycenae clay archive"),
    # --- 43. noise ---
    ("The department's espresso machine has started making a hissing noise on the second pull of the morning and nobody is taking responsibility for descaling it.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("The dendrochronology on the Ötzi Iceman's yew-wood bow and copper-axe haft places the tools solidly in the late fourth millennium BCE; the result was cross-checked against C-14 AMS on his gut contents.", "preference", "knowledge", False,
     [("dendrochronology", "method"), ("Ötzi Iceman", "person"), ("C-14 AMS", "method")],
     [("dendrochronology", "Ötzi Iceman", "APPLIES_TO"), ("C-14 AMS", "Ötzi Iceman", "APPLIES_TO")],
     "which two independent techniques agree on a late-fourth-millennium date for the Tyrolean ice mummy's gear",
     "dendrochronology otzi iceman yew bow copper axe c14 ams gut"),
    # --- 45 ---
    ("The British Museum's Parthenon Marbles debate reopened in 2022 after Greek authorities proposed a long-term loan arrangement; the institutional position still defers any deaccessioning decision to the 1963 Act.", "problem", "knowledge", False,
     [("British Museum", "organization"), ("Parthenon Marbles", "concept"), ("1963 Act", "concept")],
     [("British Museum", "Parthenon Marbles", "APPLIES_TO")],
     "which 2022 proposal reopened the Elgin Marbles question and which UK statute still blocks deaccessioning",
     "british museum parthenon marbles 2022 loan 1963 act greece"),
    # --- 46 ---
    ("The Oriental Institute Chicago's preferred format for excavation archives is born-digital field tablets with Harris matrix nodes linked to context sheets, in deliberate contrast to retroactive paper digitisation.", "preference", "knowledge", False,
     [("Oriental Institute Chicago", "organization"), ("Harris matrix", "method"), ("context sheet", "concept")],
     [("Oriental Institute Chicago", "Harris matrix", "APPLIES_TO")],
     "which Chicago institute prefers born-digital field tablets linked into Harris matrix nodes for excavation records",
     "oriental institute chicago born digital tablet harris matrix context"),
    # --- 47 ---
    ("Mary Leakey's 1976 discovery of the Laetoli footprints, preserved in volcanic tuff and dated by potassium-argon to 3.6 million years, established bipedal locomotion for Australopithecus afarensis before Lucy's full skeleton had even been fully described.", "milestone", "knowledge", False,
     [("Mary Leakey", "person"), ("Laetoli", "place"), ("potassium-argon", "method"), ("Australopithecus afarensis", "concept")],
     [("Mary Leakey", "Laetoli", "APPLIES_TO"), ("potassium-argon", "Laetoli", "APPLIES_TO")],
     "whose 1976 volcanic-tuff footprint find in Tanzania established early hominin bipedalism before Lucy was fully described",
     "leakey laetoli 1976 footprint potassium argon 3 6 million afarensis"),
    # --- 48 ---
    ("Uruk's Eanna precinct excavation archive is housed in Berlin and Baghdad jointly; the institutional split is a legacy of the 1912 partage agreement and still complicates cross-museum object studies today.", "decision", "knowledge", False,
     [("Uruk", "place"), ("Eanna", "place"), ("Berlin", "place"), ("Baghdad", "place")],
     [("Uruk", "Eanna", "APPLIES_TO")],
     "which 1912 partage arrangement split the southern Mesopotamian precinct archive across two capitals",
     "uruk eanna berlin baghdad 1912 partage archive split"),
    # --- 49 ---
    ("Pompeii's Regio V excavations resuming in 2018 adopted photogrammetry at each context's removal; the 3D archive is now referenced by the Harris matrix nodes instead of the older paper-only plan sheets.", "architecture", "knowledge", False,
     [("Pompeii", "place"), ("photogrammetry", "method"), ("Harris matrix", "method")],
     [("photogrammetry", "Pompeii", "APPLIES_TO"), ("Harris matrix", "Pompeii", "APPLIES_TO")],
     "how does the 2018 Vesuvian dig link photogrammetric 3D captures to its stratigraphic Harris matrix",
     "pompeii regio v 2018 photogrammetry harris matrix 3d context"),
    # --- 50 ---
    ("The default reference handbook for archaeological field method in Anglophone programmes remains the Colin Renfrew and Paul Bahn Archaeology: Theories, Methods, and Practice, cited across Cambridge McDonald Institute and Oriental Institute Chicago syllabi alike.", "reference", "knowledge", False,
     [("Colin Renfrew", "person"), ("Cambridge McDonald Institute", "organization"), ("Oriental Institute Chicago", "organization")],
     [("Cambridge McDonald Institute", "Colin Renfrew", "APPLIES_TO"), ("Oriental Institute Chicago", "Colin Renfrew", "APPLIES_TO")],
     "which Renfrew-and-Bahn handbook is the shared default method reference at Cambridge McDonald and Chicago Oriental institutes",
     "renfrew bahn archaeology theories methods practice cambridge chicago"),
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
