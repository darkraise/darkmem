"""One-off emitter for shared-base batch-031 — knowledge domain (history/anthropology/archaeology/human prehistory).

Writes 50 rows with ids shared-01501..01550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_031.tmp.jsonl"
ID_OFFSET = 1500

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Bronze Age collapse around 1177 BCE saw the near-simultaneous fall of Mycenaean, Hittite, and Levantine palatial systems across the eastern Mediterranean.", "fact", "knowledge", False,
     [("Bronze Age collapse", "event"), ("1177 BCE", "date"), ("Mycenaean", "concept"), ("Hittite", "concept"), ("eastern Mediterranean", "place")],
     [],
     "when did the palace economies of the late second millennium unravel together",
     "late bronze collapse palace system Mediterranean simultaneous fall"),
    # --- 2 ---
    ("Hobsbawm's The Age of Extremes, published in 1994, framed the short twentieth century as running from 1914 to the Soviet collapse in 1991.", "reference", "knowledge", False,
     [("Hobsbawm", "person"), ("The Age of Extremes", "publication"), ("1994", "date"), ("short twentieth century", "concept"), ("Soviet collapse", "event"), ("1991", "date")],
     [("The Age of Extremes", "Hobsbawm", "AUTHORED_BY")],
     "which synthesis defined the twentieth century as bracketed by world war and Soviet end",
     "short twentieth century Marxist synthesis Hobsbawm extremes periodisation"),
    # --- 3 ---
    ("Radiocarbon dating replaces typological cross-dating for organic archaeological material younger than about fifty thousand years.", "decision", "knowledge", False,
     [("Radiocarbon dating", "method"), ("typological cross-dating", "method"), ("organic archaeological material", "concept")],
     [("Radiocarbon dating", "typological cross-dating", "REPLACES")],
     "which absolute dating technique supplanted relative seriation for organic finds",
     "carbon 14 absolute date organic sample replace typology"),
    # --- 4 ---
    ("Gobekli Tepe, excavated from 1995 onward, pushed the earliest monumental stone architecture back to roughly 9500 BCE, before settled farming.", "milestone", "knowledge", False,
     [("Gobekli Tepe", "place"), ("1995", "date"), ("monumental stone architecture", "concept"), ("9500 BCE", "date")],
     [],
     "when did excavation reveal pre-agricultural monumental architecture in southeastern Anatolia",
     "pre-pottery neolithic Anatolia T-pillar hunter-gatherer monument"),
    # --- 5 ---
    ("Braudel's The Mediterranean, first published in 1949, grounded the Annales school's focus on the longue duree over event-history.", "reference", "knowledge", False,
     [("Braudel", "person"), ("The Mediterranean", "publication"), ("1949", "date"), ("Annales school", "concept"), ("longue duree", "concept")],
     [("The Mediterranean", "Braudel", "AUTHORED_BY")],
     "which work anchored the Annales emphasis on slow-moving structures",
     "Annales longue duree Mediterranean structures geography history"),
    # --- 6 ---
    ("Denisovan admixture in modern human genomes was first identified in 2010 from a finger bone in Denisova Cave, Siberia.", "milestone", "knowledge", False,
     [("Denisovan", "concept"), ("modern human genomes", "concept"), ("2010", "date"), ("Denisova Cave", "place"), ("Siberia", "place")],
     [],
     "when was a distinct archaic human population first identified from ancient DNA alone",
     "archaic introgression ancient DNA finger bone Siberia discovery"),
    # --- 7 ---
    ("The Meiji restoration of 1868 replaced the Tokugawa shogunate with a centralised imperial government and rapid industrial reform.", "fact", "knowledge", False,
     [("Meiji restoration", "event"), ("1868", "date"), ("Tokugawa shogunate", "concept"), ("centralised imperial government", "concept")],
     [("Meiji restoration", "Tokugawa shogunate", "REPLACES")],
     "which 1868 event ended feudal Japanese rule and launched industrial reform",
     "Meiji Tokugawa restoration industrialisation imperial centralisation"),
    # --- 8 ---
    ("Malinowski's Argonauts of the Western Pacific, published in 1922, established participant observation as the standard ethnographic method.", "milestone", "knowledge", False,
     [("Malinowski", "person"), ("Argonauts of the Western Pacific", "publication"), ("1922", "date"), ("participant observation", "method")],
     [("Argonauts of the Western Pacific", "Malinowski", "AUTHORED_BY")],
     "when did the founding text of participant-observation fieldwork appear",
     "Trobriand kula participant observation ethnography founding year"),
    # --- 9 ---
    ("The Clovis-first model claims the earliest Americans arrived via an ice-free corridor around 13000 BCE, a view contradicted by pre-Clovis sites like Monte Verde.", "problem", "knowledge", False,
     [("Clovis-first model", "theory"), ("ice-free corridor", "concept"), ("13000 BCE", "date"), ("pre-Clovis sites", "concept"), ("Monte Verde", "place")],
     [("Clovis-first model", "pre-Clovis sites", "CONTRADICTS")],
     "which peopling-of-the-Americas model has been undermined by recent site evidence",
     "Clovis first peopling Americas pre-Clovis Monte Verde challenge"),
    # --- 10. noise ---
    ("Let me dig out the site report before I quote that date.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Dendrochronology calibrates radiocarbon dates by cross-matching tree-ring sequences stretching back more than twelve thousand years in some European oak chronologies.", "fact", "knowledge", False,
     [("Dendrochronology", "method"), ("radiocarbon dates", "concept"), ("European oak chronologies", "concept")],
     [("Dendrochronology", "radiocarbon dates", "SUPPORTS")],
     "which method anchors the radiocarbon calibration curve deep into the Holocene",
     "tree ring calibration oak chronology radiocarbon anchor"),
    # --- 12 ---
    ("Spence's The Search for Modern China, published in 1990, became the standard anglophone survey of Chinese history from the late Ming to the Deng era.", "reference", "knowledge", False,
     [("Spence", "person"), ("The Search for Modern China", "publication"), ("1990", "date"), ("late Ming", "concept"), ("Deng era", "concept")],
     [("The Search for Modern China", "Spence", "AUTHORED_BY")],
     "which textbook shaped English-language teaching of late imperial and modern China",
     "Spence modern China survey textbook late Ming Deng anglophone"),
    # --- 13 ---
    ("Levi-Strauss's Tristes Tropiques, published in 1955, wove ethnographic memoir with structuralist reflection on Amazonian societies.", "reference", "knowledge", False,
     [("Levi-Strauss", "person"), ("Tristes Tropiques", "publication"), ("1955", "date"), ("structuralist reflection", "concept"), ("Amazonian societies", "concept")],
     [("Tristes Tropiques", "Levi-Strauss", "AUTHORED_BY")],
     "which memoir-ethnography married structuralism with Amazonian fieldwork",
     "Tristes Tropiques structuralism memoir ethnography Amazon"),
    # --- 14 ---
    ("Optically stimulated luminescence dating estimates when buried sediments were last exposed to sunlight, extending chronologies beyond the radiocarbon ceiling.", "fact", "knowledge", False,
     [("Optically stimulated luminescence dating", "method"), ("buried sediments", "concept"), ("radiocarbon ceiling", "concept")],
     [],
     "which luminescence method pushes sediment chronologies past the radiocarbon limit",
     "OSL luminescence sediment burial sunlight age beyond radiocarbon"),
    # --- 15 ---
    ("The Carolingian renaissance centred on Aachen under Charlemagne, who sponsored a standardised script and revived classical learning from the 780s.", "fact", "knowledge", False,
     [("Carolingian renaissance", "event"), ("Aachen", "place"), ("Charlemagne", "person"), ("780s", "date")],
     [("Carolingian renaissance", "Charlemagne", "AUTHORED_BY")],
     "which late-eighth-century revival centred on Aachen under a Frankish monarch",
     "Carolingian renaissance Aachen Charlemagne minuscule classical revival"),
    # --- 16 ---
    ("Tuchman's The Guns of August, published in 1962, reconstructed the opening month of the First World War as a study in diplomatic miscalculation.", "reference", "knowledge", False,
     [("Tuchman", "person"), ("The Guns of August", "publication"), ("1962", "date"), ("First World War", "event")],
     [("The Guns of August", "Tuchman", "AUTHORED_BY")],
     "which narrative history framed August 1914 as avoidable miscalculation",
     "Guns of August Tuchman 1914 July crisis narrative history"),
    # --- 17 ---
    ("Catalhoyuk, excavated systematically by Ian Hodder from 1993, remains the richest evidence for densely clustered Neolithic settlement in Anatolia.", "reference", "knowledge", False,
     [("Catalhoyuk", "place"), ("Ian Hodder", "person"), ("1993", "date"), ("Neolithic settlement", "concept"), ("Anatolia", "place")],
     [],
     "which Anatolian tell dominates interpretations of Neolithic dense settlement",
     "Catalhoyuk Hodder neolithic dense settlement tell Anatolia"),
    # --- 18 ---
    ("Prefers microhistory over macrohistorical synthesis when working with dense archival records about single communities or cases.", "preference", "knowledge", False,
     [("microhistory", "method"), ("macrohistorical synthesis", "method"), ("archival records", "concept")],
     [("microhistory", "macrohistorical synthesis", "PREFERS")],
     "which scale of historical inquiry wins when archives are rich and local",
     "microhistory macro synthesis scale archive preference methodology"),
    # --- 19 ---
    ("Mauss's The Gift, first published in 1925, argued that archaic exchange bound giver and receiver through obligations of return and hospitality.", "reference", "knowledge", False,
     [("Mauss", "person"), ("The Gift", "publication"), ("1925", "date"), ("archaic exchange", "concept")],
     [("The Gift", "Mauss", "AUTHORED_BY")],
     "which 1925 essay framed gift exchange as obligatory reciprocal bonding",
     "Mauss gift reciprocity obligation archaic exchange essay"),
    # --- 20 ---
    ("The Sutton Hoo ship burial, excavated in 1939, provided the richest surviving evidence for early Anglo-Saxon elite material culture.", "fact", "knowledge", False,
     [("Sutton Hoo", "place"), ("1939", "date"), ("Anglo-Saxon elite material culture", "concept")],
     [],
     "which 1939 English excavation transformed knowledge of Anglo-Saxon elites",
     "Sutton Hoo ship burial Anglo Saxon helmet East Anglia elite"),
    # --- 21 ---
    ("Post-war decolonisation after 1945 replaced European colonial administration across Asia and Africa with independent states, often along arbitrary colonial borders.", "fact", "knowledge", False,
     [("Post-war decolonisation", "event"), ("1945", "date"), ("European colonial administration", "concept"), ("Asia", "place"), ("Africa", "place")],
     [("Post-war decolonisation", "European colonial administration", "REPLACES")],
     "which post-1945 process dismantled European empires into successor nation-states",
     "decolonisation post war empire Africa Asia independence successor"),
    # --- 22 ---
    ("Vindolanda's waterlogged deposits preserved hundreds of Roman wooden writing tablets, revolutionising understanding of frontier military life.", "fact", "knowledge", False,
     [("Vindolanda", "place"), ("Roman wooden writing tablets", "concept"), ("frontier military life", "concept")],
     [],
     "which Hadrian's Wall site yielded Latin wooden letters from the garrison",
     "Vindolanda tablets Roman letters Hadrian wall garrison waterlogged"),
    # --- 23 ---
    ("Big history, associated with David Christian's teaching from the 1990s, extends historical narrative back to the Big Bang and integrates natural-science chronology.", "decision", "knowledge", False,
     [("Big history", "concept"), ("David Christian", "person"), ("1990s", "date"), ("Big Bang", "concept"), ("natural-science chronology", "concept")],
     [("Big history", "David Christian", "AUTHORED_BY")],
     "which historiographical school integrates cosmological chronology into the human story",
     "big history David Christian cosmology integration narrative scale"),
    # --- 24 ---
    ("The Han dynasty ruled China from 202 BCE to 220 CE, consolidating the bureaucratic state model that shaped East Asian governance for two millennia.", "fact", "knowledge", False,
     [("Han dynasty", "concept"), ("202 BCE", "date"), ("220 CE", "date"), ("bureaucratic state model", "concept"), ("East Asian governance", "concept")],
     [],
     "which four-century Chinese dynasty set the template for East Asian statecraft",
     "Han dynasty bureaucracy imperial China template East Asia"),
    # --- 25 ---
    ("Ginzburg's The Cheese and the Worms, published in 1976, reconstructed the cosmology of a sixteenth-century miller from inquisitorial records as a microhistory exemplar.", "reference", "knowledge", False,
     [("Ginzburg", "person"), ("The Cheese and the Worms", "publication"), ("1976", "date"), ("sixteenth-century miller", "concept"), ("microhistory", "method")],
     [("The Cheese and the Worms", "Ginzburg", "AUTHORED_BY")],
     "which miller's inquisition file became a defining case for microhistorical practice",
     "Ginzburg Menocchio cheese worms microhistory inquisition miller"),
    # --- 26 ---
    ("Neanderthal introgression contributes roughly one to two percent of the genome in most non-African modern humans.", "fact", "knowledge", False,
     [("Neanderthal introgression", "concept"), ("genome", "concept"), ("non-African modern humans", "concept")],
     [],
     "what share of genome in non-Africans traces to Neanderthal admixture",
     "Neanderthal admixture percentage non African introgression modern"),
    # --- 27 ---
    ("Beard's SPQR, published in 2015, reinterpreted Roman political history for general readers while integrating recent epigraphic and archaeological evidence.", "reference", "knowledge", False,
     [("Beard", "person"), ("SPQR", "publication"), ("2015", "date"), ("Roman political history", "concept")],
     [("SPQR", "Beard", "AUTHORED_BY")],
     "which popular Roman history synthesised epigraphy and archaeology for lay readers",
     "SPQR Beard Roman history popular synthesis epigraphy"),
    # --- 28 ---
    ("The Natufian culture of the Levant, dated to roughly 12500 to 9500 BCE, shows the earliest evidence of sedentary hunter-gatherer villages before farming.", "fact", "knowledge", False,
     [("Natufian culture", "concept"), ("Levant", "place"), ("12500 to 9500 BCE", "date"), ("sedentary hunter-gatherer villages", "concept")],
     [],
     "which Levantine culture documents pre-agricultural sedentism",
     "Natufian Levant sedentism hunter gatherer pre agricultural village"),
    # --- 29 ---
    ("Foucault's Discipline and Punish, published in 1975, traced the shift from spectacular punishment to disciplinary surveillance in the modern prison.", "reference", "knowledge", False,
     [("Foucault", "person"), ("Discipline and Punish", "publication"), ("1975", "date"), ("spectacular punishment", "concept"), ("disciplinary surveillance", "concept")],
     [("Discipline and Punish", "Foucault", "AUTHORED_BY")],
     "which genealogy reframed the prison as the hinge of modern disciplinary power",
     "Foucault discipline punish panopticon genealogy prison surveillance"),
    # --- 30 ---
    ("Dmanisi in Georgia yielded 1.8-million-year-old hominin skulls that complicate the narrative of a late Out-of-Africa dispersal.", "milestone", "knowledge", False,
     [("Dmanisi", "place"), ("Georgia", "place"), ("hominin skulls", "concept"), ("Out-of-Africa dispersal", "concept")],
     [],
     "which Caucasus site produced 1.8-million-year-old hominin remains outside Africa",
     "Dmanisi Georgia hominin skull early dispersal Caucasus"),
    # --- 31 ---
    ("Anderson's Imagined Communities, published in 1983, framed nations as culturally constructed through print-capitalism and vernacular literacy.", "reference", "knowledge", False,
     [("Anderson", "person"), ("Imagined Communities", "publication"), ("1983", "date"), ("print-capitalism", "concept"), ("vernacular literacy", "concept")],
     [("Imagined Communities", "Anderson", "AUTHORED_BY")],
     "which work explained nationalism as an artefact of print-capitalism",
     "Imagined Communities Anderson nationalism print capitalism vernacular"),
    # --- 32 ---
    ("Thompson's The Making of the English Working Class, published in 1963, recovered agency and consciousness in early-industrial labour from below.", "milestone", "knowledge", False,
     [("Thompson", "person"), ("The Making of the English Working Class", "publication"), ("1963", "date"), ("early-industrial labour", "concept")],
     [("The Making of the English Working Class", "Thompson", "AUTHORED_BY")],
     "which 1963 book made history-from-below a mainstream method in labour history",
     "Thompson English working class history from below agency labour"),
    # --- 33 ---
    ("The agricultural origins debate places the earliest domestication of wheat and barley in the Fertile Crescent around 10000 BCE.", "fact", "knowledge", False,
     [("agricultural origins debate", "concept"), ("domestication of wheat and barley", "concept"), ("Fertile Crescent", "place"), ("10000 BCE", "date")],
     [],
     "which region hosts the earliest secure evidence for cereal domestication",
     "agricultural origin Fertile Crescent cereal domestication Neolithic"),
    # --- 34. noise ---
    ("Hold on, I want to re-read that chapter before taking notes.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Evans-Pritchard's The Nuer, published in 1940, set the template for segmentary lineage analysis in British social anthropology.", "reference", "knowledge", False,
     [("Evans-Pritchard", "person"), ("The Nuer", "publication"), ("1940", "date"), ("segmentary lineage analysis", "method"), ("British social anthropology", "field")],
     [("The Nuer", "Evans-Pritchard", "AUTHORED_BY")],
     "which 1940 ethnography canonised segmentary lineage models",
     "Nuer 1940 lineage kinship east African cattle pastoralist field"),
    # --- 36 ---
    ("Bayesian chronological modelling improves on simple radiocarbon averaging by combining stratigraphic priors with date likelihoods for tighter site sequences.", "decision", "knowledge", False,
     [("Bayesian chronological modelling", "method"), ("radiocarbon averaging", "method"), ("stratigraphic priors", "concept")],
     [("Bayesian chronological modelling", "radiocarbon averaging", "IMPROVES_ON")],
     "which statistical approach tightens site chronologies by combining stratigraphy with dates",
     "Bayesian chronology OxCal stratigraphy prior radiocarbon refinement"),
    # --- 37 ---
    ("Graeber and Wengrow's The Dawn of Everything, published in 2021, contested the standard progression from egalitarian bands to agrarian hierarchy.", "reference", "knowledge", False,
     [("Graeber", "person"), ("Wengrow", "person"), ("The Dawn of Everything", "publication"), ("2021", "date"), ("agrarian hierarchy", "concept")],
     [("The Dawn of Everything", "Graeber", "AUTHORED_BY"), ("The Dawn of Everything", "Wengrow", "AUTHORED_BY")],
     "which recent synthesis challenged the linear story from bands to agricultural states",
     "Graeber Wengrow Dawn of Everything origins inequality deep history"),
    # --- 38 ---
    ("The Antikythera mechanism, recovered from a first-century-BCE shipwreck, is the earliest known geared astronomical calculator.", "fact", "knowledge", False,
     [("Antikythera mechanism", "concept"), ("first-century-BCE shipwreck", "concept"), ("geared astronomical calculator", "concept")],
     [],
     "which Hellenistic artefact is the earliest surviving geared computational device",
     "Antikythera mechanism geared astronomical computer Hellenistic wreck"),
    # --- 39 ---
    ("Dating of the Laetoli footprints to 3.66 million years ago provided the clearest evidence for bipedal locomotion in early australopithecines.", "milestone", "knowledge", False,
     [("Laetoli footprints", "concept"), ("3.66 million years ago", "date"), ("bipedal locomotion", "concept"), ("australopithecines", "concept")],
     [],
     "which Tanzanian trackway fixed bipedalism deep into the Pliocene",
     "Laetoli footprints bipedal Australopithecus Pliocene Tanzania trace"),
    # --- 40 ---
    ("Strontium isotope analysis of tooth enamel reconstructs childhood mobility by matching ratios to underlying geological zones.", "fact", "knowledge", False,
     [("Strontium isotope analysis", "method"), ("tooth enamel", "concept"), ("geological zones", "concept")],
     [],
     "which isotopic technique reconstructs where an individual grew up",
     "strontium isotope enamel mobility provenance geology childhood"),
    # --- 41 ---
    ("The Nag Hammadi codices, unearthed in 1945, reshaped understanding of early Christian diversity by preserving Gnostic gospel texts.", "fact", "knowledge", False,
     [("Nag Hammadi codices", "concept"), ("1945", "date"), ("early Christian diversity", "concept"), ("Gnostic gospel texts", "concept")],
     [],
     "which 1945 Egyptian discovery forced reassessment of early Christian variety",
     "Nag Hammadi Gnostic codex early Christianity Egypt discovery"),
    # --- 42 ---
    ("Said's Orientalism, published in 1978, argued Western scholarship on the Middle East constructed a discursive object that justified imperial control.", "reference", "knowledge", False,
     [("Said", "person"), ("Orientalism", "publication"), ("1978", "date"), ("Western scholarship", "concept"), ("Middle East", "place")],
     [("Orientalism", "Said", "AUTHORED_BY")],
     "which 1978 critique tied imperial power to scholarly representation of the East",
     "Said Orientalism discourse imperial Middle East critique"),
    # --- 43 ---
    ("Prefers isotopic palaeodiet reconstruction over artefact typology when inferring subsistence shifts in prehistoric populations.", "preference", "knowledge", False,
     [("isotopic palaeodiet reconstruction", "method"), ("artefact typology", "method"), ("prehistoric populations", "concept")],
     [("isotopic palaeodiet reconstruction", "artefact typology", "PREFERS")],
     "which line of evidence wins when inferring ancient diet over tool forms",
     "palaeodiet isotope carbon nitrogen subsistence preference typology"),
    # --- 44 ---
    ("Pompeii's burial under Vesuvian ash in 79 CE preserved a Roman provincial town in exceptional stratigraphic detail.", "fact", "knowledge", False,
     [("Pompeii", "place"), ("Vesuvian ash", "concept"), ("79 CE", "date"), ("Roman provincial town", "concept")],
     [],
     "which 79 CE eruption sealed the richest snapshot of Roman urban life",
     "Pompeii Vesuvius 79 CE Roman urban preservation ash"),
    # --- 45 ---
    ("Foley and Mirazon Lahr proposed the dispersed African origin model in 1997, reframing modern human emergence as a multi-regional African process.", "milestone", "knowledge", False,
     [("Foley", "person"), ("Mirazon Lahr", "person"), ("dispersed African origin model", "theory"), ("1997", "date"), ("modern human emergence", "concept")],
     [("dispersed African origin model", "Foley", "AUTHORED_BY"), ("dispersed African origin model", "Mirazon Lahr", "AUTHORED_BY")],
     "when was the pan-African dispersed model of modern human origins proposed",
     "dispersed African origin pan African modern human multi regional"),
    # --- 46 ---
    ("The Venus of Willendorf, dated to about 28000 BCE, remains a key artefact for debates about Upper Palaeolithic female figurative symbolism.", "reference", "knowledge", False,
     [("Venus of Willendorf", "concept"), ("28000 BCE", "date"), ("Upper Palaeolithic", "concept")],
     [],
     "which Upper Palaeolithic figurine anchors debates about prehistoric female imagery",
     "Venus Willendorf Upper Palaeolithic figurine symbolism prehistoric"),
    # --- 47 ---
    ("Bloch and Febvre founded the Annales journal in 1929, launching the school that reoriented French history toward structures and mentalities.", "milestone", "knowledge", False,
     [("Bloch", "person"), ("Febvre", "person"), ("Annales journal", "publication"), ("1929", "date"), ("French history", "field"), ("mentalities", "concept")],
     [("Annales journal", "Bloch", "AUTHORED_BY"), ("Annales journal", "Febvre", "AUTHORED_BY")],
     "when was the journal that launched structural French history founded",
     "Annales 1929 Bloch Febvre structures mentalities French history"),
    # --- 48 ---
    ("Kinship systems in Dravidian societies use bifurcate-merging terminology, structurally distinct from the English Eskimo pattern.", "fact", "knowledge", False,
     [("Kinship systems", "concept"), ("Dravidian societies", "concept"), ("bifurcate-merging terminology", "concept"), ("Eskimo pattern", "concept")],
     [],
     "which kinship terminology contrasts most cleanly with the English Eskimo pattern",
     "Dravidian kinship bifurcate merging terminology contrast Eskimo"),
    # --- 49 ---
    ("Ancient DNA analysis of the Yamnaya steppe culture shows a major migration into Bronze Age Europe around 3000 BCE that reshaped the continental gene pool.", "fact", "knowledge", False,
     [("Ancient DNA analysis", "method"), ("Yamnaya steppe culture", "concept"), ("Bronze Age Europe", "concept"), ("3000 BCE", "date")],
     [],
     "which steppe migration reshaped European ancestry at the start of the Bronze Age",
     "Yamnaya steppe migration ancient DNA Bronze Age Europe ancestry"),
    # --- 50 ---
    ("Carlo Ginzburg's evidential paradigm essay of 1979 framed clues, symptoms, and traces as the shared logic of Morelli, Freud, and Sherlock Holmes.", "reference", "knowledge", False,
     [("Carlo Ginzburg", "person"), ("evidential paradigm", "concept"), ("1979", "date"), ("Morelli", "person"), ("Freud", "person"), ("Sherlock Holmes", "concept")],
     [("evidential paradigm", "Carlo Ginzburg", "AUTHORED_BY")],
     "which essay unified connoisseurship, psychoanalysis, and detection under one method",
     "evidential paradigm clues Ginzburg Morelli Freud detective method"),
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
