"""One-off emitter for retrieval top-up batch-016 — paraphrase kind, shared rows at line offsets 1500..1599.

Writes 100 rows to data/v2/retrieval/batch_016.tmp.jsonl with ids ret-01501..01600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_016.tmp.jsonl"
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 1500
SHARED_OFFSET = 1500
QUERY_KIND = "paraphrase"

# One query per source row, in the same order as the source rows.
QUERIES: list[str] = [
    # 1501: Bronze Age collapse ~1177 BCE, Mycenaean/Hittite/Levantine palatial systems
    "date and scope of the late-second-millennium eastern Mediterranean palace societies collapse",
    # 1502: Hobsbawm Age of Extremes 1994, short 20th century 1914-1991
    "which Hobsbawm volume frames 1914 to 1991 as a single compressed century",
    # 1503: Radiocarbon dating replaces typology for organics under ~50ky
    "method preferred over artefact typology for dating organic finds within the last fifty millennia",
    # 1504: Gobekli Tepe dig from 1995, monumental stone arch ~9500 BCE pre-farming
    "site whose 1995 excavation pushed monumental masonry back before the advent of agriculture",
    # 1505: Braudel Mediterranean 1949, Annales longue duree over event history
    "Braudel work that grounded Annales commitment to slow temporal structures over events",
    # 1506: Denisovan admixture first identified 2010 from Siberian finger bone
    "year and specimen that first confirmed ancient hominin ancestry beyond Neanderthals in modern genomes",
    # 1507: Meiji restoration 1868 replaced Tokugawa with imperial centralisation
    "what ended feudal shogunal rule in Japan and launched rapid industrialisation in the late 1860s",
    # 1508: Malinowski Argonauts 1922, participant observation standard
    "which 1922 monograph codified immersive fieldwork as the discipline's core ethnographic practice",
    # 1509: Clovis-first ice-free corridor ~13000 BCE vs pre-Clovis Monte Verde
    "orthodox peopling-of-the-Americas model contradicted by South American pre-Clovis evidence",
    # 1510: noise, fetch site report before quoting date
    "what hedging remark delayed citing a date until the report could be consulted",
    # 1511: Dendrochronology calibrates C14 via tree-ring sequences >12ky, European oaks
    "how European oak ring sequences refine radiocarbon chronology over twelve-thousand-year spans",
    # 1512: Spence Search for Modern China 1990, standard late Ming to Deng era survey
    "which 1990 anglophone textbook became the default survey from late Ming through Deng",
    # 1513: Levi-Strauss Tristes Tropiques 1955, memoir + structuralism Amazonia
    "Levi-Strauss travel-meditation blending fieldwork memoir with structural reflection on Amazonian peoples",
    # 1514: Optically stimulated luminescence dates last sunlight on buried sediments
    "technique estimating last exposure to daylight for sediments beyond the radiocarbon ceiling",
    # 1515: Carolingian renaissance Aachen Charlemagne from 780s, standard script, classical learning
    "eighth-century court reform programme under Charlemagne that revived ancient scholarship and unified handwriting",
    # 1516: Tuchman Guns of August 1962, opening month WWI diplomatic miscalculation
    "Tuchman narrative treating August 1914 as a cascade of chancellery blunders",
    # 1517: Catalhoyuk Hodder from 1993, dense Neolithic settlement Anatolia
    "Anatolian Neolithic site whose post-1993 re-excavation under Hodder set the benchmark for packed villages",
    # 1518: Prefers microhistory over macro with dense archives single community
    "preferred scale when working from thick archival records about a single locality or individual",
    # 1519: Mauss The Gift 1925, archaic exchange obligations
    "Mauss essay arguing that premodern giving bound donor and recipient through reciprocal duties",
    # 1520: Sutton Hoo ship burial 1939, richest Anglo-Saxon elite material culture
    "1939 East Anglian ship burial that transformed understanding of early medieval English aristocracy",
    # 1521: Post-war decolonisation after 1945, arbitrary colonial borders Asia/Africa
    "post-1945 wave of independence movements across Asia and Africa and the borders they inherited",
    # 1522: Vindolanda waterlogged Roman wooden writing tablets, frontier life
    "northern-frontier Roman fort whose damp soil preserved wooden tablets documenting garrison daily life",
    # 1523: Big history David Christian 1990s, narrative back to Big Bang
    "cross-disciplinary course associated with David Christian that begins narrative at cosmic origins",
    # 1524: Han dynasty 202 BCE-220 CE, bureaucratic state East Asia
    "Chinese imperial dynasty whose bureaucratic model underpinned governance for two thousand years",
    # 1525: Ginzburg Cheese and the Worms 1976, Menocchio miller inquisition microhistory
    "which 1976 Ginzburg monograph used an inquisitorial file to reconstruct a heretical miller's worldview",
    # 1526: Neanderthal introgression 1-2% non-African genomes
    "approximate share of archaic Neanderthal ancestry carried by most people outside Africa",
    # 1527: Beard SPQR 2015, Roman politics for general readers
    "Mary Beard trade book that reframed Roman political history using recent inscriptions and digs",
    # 1528: Natufian Levant 12500-9500 BCE sedentary hunter-gatherers pre-farming
    "Levantine culture showing settled village life before the shift to agriculture",
    # 1529: Foucault Discipline and Punish 1975, spectacle to surveillance
    "which 1975 Foucault book traced the modern prison's move from public execution toward surveillance",
    # 1530: Dmanisi Georgia 1.8 million year old hominin skulls
    "Caucasus site whose ancient hominin skulls complicate a late African exodus model",
    # 1531: Anderson Imagined Communities 1983, nations via print capitalism
    "Anderson thesis treating nationhood as a cultural artefact produced through vernacular print markets",
    # 1532: Thompson Making of English Working Class 1963, history from below
    "which 1963 Thompson study restored agency to industrialising workers against elite narratives",
    # 1533: Agricultural origins wheat barley Fertile Crescent ~10000 BCE
    "estimated date and region where cereals were first brought under cultivation in southwest Asia",
    # 1534: noise, re-read chapter before taking notes
    "what aside about revisiting a chapter before note-taking appeared in the transcript",
    # 1535: Evans-Pritchard The Nuer 1940, segmentary lineage British anthropology
    "Nilotic ethnography that became the model for segmentary descent analysis in British schools",
    # 1536: Bayesian chronological modelling stratigraphic priors tighter sequences
    "probabilistic approach combining layer ordering with date likelihoods for sharper site chronologies",
    # 1537: Graeber Wengrow Dawn of Everything 2021, contested band-to-hierarchy progression
    "2021 synthesis that rejects the assumed march from egalitarian foragers to farming hierarchies",
    # 1538: Antikythera mechanism 1st century BCE shipwreck, earliest geared calculator
    "ancient Aegean wreck find that counts as the earliest surviving mechanical astronomical device",
    # 1539: Laetoli footprints 3.66 million years ago, bipedal australopithecines
    "trackway whose redating to the mid-Pliocene confirmed upright walking in early human ancestors",
    # 1540: Strontium tooth enamel reconstructs childhood mobility vs geology
    "isotope method using enamel ratios to match an individual's early home soils",
    # 1541: Nag Hammadi codices 1945, reshape early Christian diversity via Gnostic gospels
    "1945 Egyptian manuscript find that broadened scholarly views of early Christian heterodoxy",
    # 1542: Said Orientalism 1978, Western scholarship on Middle East as imperial discourse
    "Said thesis framing Western Middle East studies as a discourse that served empire",
    # 1543: Prefers isotopic palaeodiet over artefact typology for subsistence shifts
    "preferred line of evidence for tracking prehistoric diet change rather than relying on object styles",
    # 1544: Pompeii 79 CE Vesuvius, Roman town preserved stratigraphically
    "Campanian town whose volcanic sealing left an unmatched stratified record of provincial Roman life",
    # 1545: Foley Mirazon Lahr 1997 dispersed African origin modern humans
    "1997 proposal reframing our species' origin as pan-continental rather than a single source point",
    # 1546: Venus of Willendorf ~28000 BCE Upper Palaeolithic female figurative
    "Palaeolithic limestone figurine central to arguments about ice-age female symbolism",
    # 1547: Bloch Febvre Annales journal 1929, structures and mentalities
    "pair of historians whose 1929 journal launched a turn toward long structures and mental worlds",
    # 1548: Dravidian kinship bifurcate-merging vs Eskimo English pattern
    "south-Indian kinship terminology that contrasts structurally with the English classification system",
    # 1549: Ancient DNA Yamnaya steppe ~3000 BCE reshaped European gene pool
    "which steppe-origin migration transformed Bronze Age European ancestry around five thousand years ago",
    # 1550: Ginzburg evidential paradigm essay 1979, Morelli Freud Holmes clues
    "1979 Ginzburg piece linking connoisseurship, psychoanalysis, and detective reasoning under one inferential method",
    # 1551: Optimality Theory phonology ranked violable constraints parallel
    "phonological framework replacing ordered rewrite rules with parallel evaluation of rankable constraints",
    # 1552: Construction Grammar form-meaning pairings basic unit
    "grammar framework treating stored form-meaning units as primitive instead of separate lexicon and rules",
    # 1553: Distributed Morphology Halle Marantz 1993 split word formation
    "1993 Halle and Marantz theory distributing word-building across syntax and post-syntactic insertion",
    # 1554: Proto-Indo-European reconstructed ancestor comparative method
    "reconstructed prehistoric parent tongue for languages from Iceland to Bangladesh",
    # 1555: Austronesian Taiwan fan out to Madagascar Rapa Nui early 2nd millennium
    "maritime expansion spreading from Taiwan to East Africa and the farthest Pacific islands",
    # 1556: Sino-Tibetan groups Chinese with Tibeto-Burman subgrouping contested
    "language family linking Chinese with Himalayan tongues though deeper branching remains disputed",
    # 1557: Labov 1962 NYC department store /r/ prestige variable class
    "Labov's department-store study demonstrating that postvocalic r varied with social class in New York",
    # 1558: Trudgill Norwich 1974 women lead prestige variants
    "Norwich sociolinguistic study formalising women's lead in adopting high-status speech forms",
    # 1559: Hawaiian revitalisation Punana Leo 1984 immersion Kaiapuni
    "Hawaiian language revival programme built on nest preschools begun in the mid-1980s",
    # 1560: noise, grab publication year from shelf
    "what hedge about checking a publication year from a physical bookshelf appeared in the transcript",
    # 1561: Joyce Ulysses 1922 Paris banned US until Woolsey 1933
    "when the American ban on Joyce's 1922 novel was lifted and by whose ruling",
    # 1562: Proust In Search of Lost Time, Swann's Way 1913, Time Regained 1927 posthumous
    "span of years over which Proust's long novel appeared from its opening to the posthumous close",
    # 1563: Morrison Beloved Pulitzer 1988
    "year Toni Morrison's slavery novel took the fiction Pulitzer, sealing her canonical standing",
    # 1564: Dostoevsky Brothers Karamazov 1879-1880 Russian Messenger, Alyosha graveyard
    "Dostoevsky final novel serialised in 1879 to 1880 and ending beside the schoolboys' grave",
    # 1565: Achebe Things Fall Apart 1958 Heinemann African Writers Series
    "1958 Achebe debut that opened Heinemann's African list and answered colonial-era novels",
    # 1566: Modernism early 20C broke Victorian realism fragmentation stream consciousness mythic method
    "formal techniques by which early-20th-century fiction broke away from Victorian realist convention",
    # 1567: Magical realism Latin American crystallised around Garcia Marquez 1967 One Hundred Years
    "which 1967 Garcia Marquez novel fixed the magical-realist tag onto Latin American fiction",
    # 1568: Lost Generation 1920s Paris Stein Hemingway Fitzgerald
    "interwar Paris circle of expatriate American writers clustered around Gertrude Stein",
    # 1569: Beats late-1940s NY Ginsberg Kerouac Burroughs 1955 Six Gallery
    "San Francisco reading event in 1955 that consolidated the Beat movement publicly",
    # 1570: Postcolonial writing anticolonial + Said Orientalism 1978
    "the 1978 theoretical book that helped crystallise postcolonial literary criticism",
    # 1571: Venuti Translator's Invisibility 1995 foreignisation vs domestication
    "Venuti argument pushing against smoothing source texts into fluent Anglo-American prose",
    # 1572: Skopos theory Vermeer 1978 target purpose over source fidelity
    "Vermeer translation framework prioritising the commissioned goal over literal source loyalty",
    # 1573: Pevear Volokhonsky Tolstoy vs Garnett Edwardian
    "translator pair whose Tolstoy versions displaced Garnett's polished Victorian prose among contemporary readers",
    # 1574: International Booker 2016 split translator paid equally
    "which translation prize separated from its parent award in 2016 and pays translators alongside authors",
    # 1575: Goncourt Paris November 1903 ten euro cheque sales impact
    "French November literary award whose token cheque belies its huge sales effect",
    # 1576: Akutagawa twice-yearly Japan since 1935 emerging literary fiction
    "Japanese debut-fiction award given every six months since the mid-1930s",
    # 1577: Prefers Pevear and Volokhonsky over Garnett teaching Tolstoy syntax closeness
    "preferred Tolstoy translators for classroom use when Russian syntactic closeness trumps Victorian ease",
    # 1578: Prefers foreignisation over domestication translating poetry source markers
    "preferred translation stance for verse when retaining source-culture cues matters most",
    # 1579: 2019 Nobel Literature controversy Handke Milosevic defence
    "author whose earlier support for a Yugoslav-war leader drove backlash against his 2019 Nobel",
    # 1580: Derrida Of Grammatology Spivak 1976 Anglophone deconstruction logocentrism
    "Spivak translation that brought deconstruction to English-speaking humanities in the mid-1970s",
    # 1581: New Criticism mid-century Anglophone close reading self-contained poem
    "Anglophone critical school that isolated the poem as autonomous verbal object for close analysis",
    # 1582: Structuralist narratology Propp 1928 morphology tales Genette 1972
    "lineage connecting Propp's folk-tale morphology to Genette's early 1970s narrative poetics",
    # 1583: Bakhtin Dialogic Imagination 1930s translated 1981 heteroglossia dialogism
    "when the Bakhtin essays on multi-voiced language reached English readers after decades in manuscript",
    # 1584: noise, check which translation quoting
    "what aside about verifying the source translation paused the discussion",
    # 1585: Showalter Literature of Their Own 1977 British women novelists Brontes to Lessing
    "1977 Showalter study charting a continuous British women's novel tradition from the Victorians onward",
    # 1586: Sapir-Whorf grammatical categories shape thought strong version abandoned
    "linguistic-relativity claim whose strong formulation is no longer mainstream in the field",
    # 1587: Grimm's Law Proto-Germanic from Proto-Indo-European consonant shifts
    "sound-change law accounting for the Germanic branch's split from its Indo-European parent consonants",
    # 1588: Chomsky Aspects 1965 competence performance deep structure
    "Chomsky 1965 book that introduced deep structure and the competence versus performance split",
    # 1589: Minimalist Program replaces Government and Binding economy interface
    "generative framework that supplanted GB by stripping the architecture to interface economy",
    # 1590: HPSG Generalised PSG typed unification feature structures
    "constraint-based grammar extending GPSG through typed unification over elaborate feature bundles",
    # 1591: Gricean maxims implicature pragmatics neo-Gricean relevance rivals
    "Grice's conversational principles alongside the rival neo-Gricean and relevance pragmatics traditions",
    # 1592: Hugo 2015 Sad Puppies Rabid Puppies slates fandom politics
    "2015 voting slate campaign that split science fiction fandom along political lines",
    # 1593: Borges Ficciones 1944 Latin American fantastic pre-magical realism
    "1944 Borges story collection that anchored Latin American fantastic fiction before the boom",
    # 1594: Calvino Invisible Cities 1972 Marco Polo Kublai Khan 55 cities
    "1972 Calvino work staging Marco Polo describing imagined urban visions to the Mongol emperor",
    # 1595: Ngugi Decolonising the Mind 1986 abandon English indigenous languages
    "Ngugi manifesto urging African writers to drop colonial languages for their mother tongues",
    # 1596: Ainu revitalisation Hokkaido 1997 Act 2019 indigenous recognition
    "Hokkaido language revival built on the late-1990s cultural promotion law and 2019 indigenous status",
    # 1597: Welsh revitalisation Bangor research 1993 Welsh Language Act overtook Irish
    "which Celtic revival programme outperformed Irish by combining university research with 1993 statutory schooling",
    # 1598: Kafka posthumous Brod against wishes The Trial The Castle Amerika
    "how Kafka's major novels survived to shape modernism despite the author's destruction instructions",
    # 1599: Spivak Can the Subaltern Speak 1988 postcolonial pivot revisions 1990s
    "1988 Spivak essay central to postcolonial theory that she reworked across the following decade",
    # 1600: Corpus linguistics replaces introspection with frequency data BNC
    "approach swapping armchair grammaticality judgements for frequency counts in large text archives",
]


def emit() -> int:
    with SHARED.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    sources = [json.loads(lines[SHARED_OFFSET + i]) for i in range(100)]
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as out:
        for i, (query, src) in enumerate(zip(QUERIES, sources), start=1):
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": src["id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
