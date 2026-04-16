"""One-off emitter for retrieval aug batch-004 — paraphrase kind, reference memory_type.

Reads data/v2/retrieval/aug_sources/aug_004.jsonl (100 rows) and writes
data/v2/retrieval/aug_004.tmp.jsonl with ids ret-03551..03650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_004.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_004.tmp.jsonl"
QUERY_KIND = "paraphrase"

# One paraphrase query per source row, in source order.
QUERIES: list[str] = [
    # 001: canvassing clipboard kit stored in hall cupboard
    "where is the door-knocking supply bundle stored at home",
    # 002: move-in ritual: bed, kettle, parents photo
    "what is the first-night routine followed after relocating house",
    # 003: Castells Communication Power, OUP 2009, mass self-communication
    "which book introduced mass self-communication as networked politics concept",
    # 004: 2026 pop-science shelf: Wrangham, Mukherjee
    "which popular science titles are queued for this year's book club",
    # 005: Johnsons' Kwanzaa table layout 2026-12-26
    "arrangement for the Johnson family Kwanzaa altar this December",
    # 006: Ollama HTTP API reference location on GitHub
    "link to the Ollama REST endpoint documentation",
    # 007: Wittig 1954 Chemische Berichte olefination
    "original publication introducing the phosphorus ylide alkene synthesis",
    # 008: GPT-3 paper NeurIPS 2020
    "citation for the 175-billion-parameter few-shot learning paper",
    # 009: Foucault Discipline and Punish 1975
    "text that mapped the move from public punishment to carceral surveillance",
    # 010: Doyle 1983 democratic peace essays
    "articles that revived the claim democracies avoid mutual war",
    # 011: Trudgill Norwich 1974 sociolinguistics
    "study that showed women adopt prestige speech forms earlier",
    # 012: Said Orientalism 1978
    "landmark work critiquing Western discourse about the Middle East",
    # 013: Scalia A Matter of Interpretation 1997 originalism
    "book defending fixed-at-ratification constitutional interpretation",
    # 014: Bo Bardi SESC Pompeia 1986
    "Sao Paulo factory conversion into a civic leisure complex",
    # 015: Gutenberg-Richter law 1944
    "seismology relation between quake magnitude and occurrence frequency",
    # 016: FSA dependent-care $5k, WEX monthly uploads
    "cap and submission routine for the dependent-care spending account",
    # 017: pre-sleep nightstand checklist four items
    "what routine runs through before turning out the light",
    # 018: Katz and Kahn 1966 Social Psychology of Organizations
    "work that brought open-systems thinking into organisational theory",
    # 019: CDM 2026-03-30 Disting NT granular sampler
    "where I read about the eurorack granular algorithm replacement",
    # 020: Atiyah-Singer index theorem 1963/1968
    "papers tying elliptic operator indices to topological invariants",
    # 021: Nadia pilates instructor recommended standing desk
    "who suggested the adjustable desk for my back pain",
    # 022: Ben Van Gogh Amsterdam 2025-09-18
    "when did Ben see the Wheatfield with Crows painting",
    # 023: Levi-Strauss Tristes Tropiques 1955
    "memoir blending ethnography and structuralism in the Amazon",
    # 024: Gutierrez Theology of Liberation 1971
    "founding work of liberation theology from the poor's standpoint",
    # 025: danah boyd It's Complicated Yale 2014
    "foundational study of teenagers and networked publics",
    # 026: Yale Law Journal founded 1891
    "leading venue where legal realism took root after 1891",
    # 027: APA Psychological Review founded 1894
    "flagship APA journal launched in the 1890s by Baldwin and Cattell",
    # 028: Fuller Morality of Law 1964 eight desiderata
    "book listing eight procedural virtues of legal systems",
    # 029: Rawls A Theory of Justice original position
    "treatise grounding liberal equality in a hypothetical choice scenario",
    # 030: Priya Patel structural engineer wall sign-off
    "who approved taking out the load-bearing wall and when",
    # 031: Brown and Campione reciprocal teaching 1980s
    "scaffolded reading method built on four dialogue strategies",
    # 032: Strauss Living Constitution 2010
    "work casting the constitution as a common-law evolving tradition",
    # 033: Kalman 1960 filter paper
    "origin paper of the recursive estimator used in aerospace guidance",
    # 034: Murray and Lopez DALY 1996 World Bank
    "introduction of the disability-adjusted life year metric",
    # 035: Gardner Frames of Mind 1983
    "book proposing multiple intelligences against a single IQ factor",
    # 036: Schumpeter Capitalism, Socialism and Democracy 1942
    "work introducing creative destruction as growth engine",
    # 037: Hallin and Mancini Comparing Media Systems 2004
    "comparative study grouping Western media into three models",
    # 038: Bogleheads thread 2026-02-13 Gemini Earn -> Treasuries
    "forum post that convinced my sister to move her emergency fund",
    # 039: Vitess sharding MySQL VTGate
    "MySQL sharding proxy that lets app code stay single-node-like",
    # 040: Damaska Faces of Justice 1986
    "book contrasting hierarchical and coordinate judicial ideals",
    # 041: Sasha dog walker Tue/Thu 11:30 £15
    "schedule and rate for Hugo's dog-walking arrangement",
    # 042: cousins Secret Santa £25 Elfster 2025-11-30
    "budget and platform for the cousin group gift exchange",
    # 043: Stommel 1948 western boundary currents
    "paper explaining why the Gulf Stream intensifies westward",
    # 044: Showalter A Literature of Their Own 1977
    "survey tracing a British women's novel tradition to Lessing",
    # 045: Greenberg Solomon Pyszczynski 1986 terror management
    "founding chapter of terror management theory on mortality salience",
    # 046: Mum's Christmas Eve fondue since 1998
    "longstanding cheese-pot tradition on Christmas Eve at Mum's",
    # 047: Lana eyebrow threading every eight weeks
    "cadence and style for the regular eyebrow appointment",
    # 048: Zelizer Taking Journalism Seriously Sage 2004
    "cross-disciplinary mapping of journalism scholarship book",
    # 049: Nurses' Health Study 1976 Speizer
    "long-running cohort of American nurses tracking chronic disease",
    # 050: ISO 14040 and 14044 LCA standards
    "standards covering life-cycle assessment boundaries and allocation",
    # 051: Jaspers Axial Age 800-200 BCE
    "concept naming simultaneous spiritual shifts across ancient civilisations",
    # 052: Thaler and Sunstein Nudge 2008
    "book applying behavioural science to choice architecture",
    # 053: Reinhart and Rogoff This Time Is Different 2009
    "survey of eight centuries of financial crises",
    # 054: Bliss and Lomo 1973 long-term potentiation
    "first demonstration of synaptic strengthening as memory model",
    # 055: +1.25 readers Cubitts Marylebone desk and bedside
    "where are my reading-glasses prescription details",
    # 056: Kydland Prescott 1982 real business cycle
    "theory treating business fluctuations as technology-shock responses",
    # 057: Akerlof Market for Lemons 1970
    "paper showing information asymmetry causes market collapse",
    # 058: Simon Administrative Behavior 1947 bounded rationality
    "work grounding organisations in bounded rationality and satisficing",
    # 059: 1998 Saint-Emilion reference bottle Bordeaux Sam's parents
    "which wine anchors my personal quality benchmark",
    # 060: Niamh community dementia nurse Wiltshire fortnightly
    "who visits Mum to check on dementia progression",
    # 061: low-FODMAP reintro: onion and wheat triggers, garlic fine
    "which foods turned out to provoke my IBS symptoms",
    # 062: new-home first-week grocery list
    "shopping list used when stocking a freshly moved-into kitchen",
    # 063: Calvino Invisible Cities 1972
    "novel staging Polo and Kublai Khan across fifty-five imagined cities",
    # 064: Hansen 1981 Science anthropogenic warming
    "early paper projecting detectable human climate signal",
    # 065: Reef2Reef Aquanerd 2026-02-10 Red Sea Coral Pro dosing
    "where I found the dosing tweak for the new reef salt",
    # 066: Crane and Matten Business Ethics 2004
    "European textbook integrating stakeholder theory and corporate citizenship",
    # 067: Bruner Process of Education 1960 spiral curriculum
    "short 1960 book arguing any topic can be taught at any age",
    # 068: Williamson 1985 Economic Institutions of Capitalism
    "work extending Coase with asset specificity and governance choice",
    # 069: Barzilai-Nahon network gatekeeping 2008 JASIST
    "article extending gatekeeping from editors to networked flows",
    # 070: Laupacis and Sackett NNT 1988 NEJM
    "paper popularising the number-needed-to-treat clinical metric",
    # 071: MacIntyre After Virtue fragmented moral discourse
    "book arguing modern ethics are shards of a lost virtue tradition",
    # 072: Lijphart Patterns of Democracy 1999
    "comparative study dividing democracies into consensus and majoritarian",
    # 073: Railton Moral Realism 1986 Philosophical Review
    "article defending naturalistic reductive moral realism",
    # 074: Eisenhardt and Brown 1998 Competing on the Edge
    "change-management book emphasising edge-of-chaos continuous adaptation",
    # 075: Wuthrich 1982 sequential NMR assignment
    "paper that enabled protein solution structures by NMR",
    # 076: Educational Psychologist since 1963 Division 15
    "APA division 15 journal hosting influential theoretical essays",
    # 077: Haavelmo 1944 probability approach in econometrics
    "foundational supplement putting probability at econometrics' core",
    # 078: Bach Well-Tempered Clavier 1722 and 1742
    "keyboard collection pairing prelude and fugue in every key",
    # 079: Protobuf field numbers 19000-19999 reserved
    "which proto field-tag range is reserved and why stay low",
    # 080: Hennig 1966 Phylogenetic Systematics cladistics
    "work founding cladistic classification via shared derived traits",
    # 081: Vine-Matthews-Morley 1963 magnetic stripes
    "hypothesis reading seafloor magnetic stripes as spreading proof",
    # 082: Hesiod Theogony 700 BCE
    "archaic Greek poem recounting the succession of the gods",
    # 083: Kafka KIP-500 KRaft migration runbook
    "authoritative reference for moving Kafka off ZooKeeper",
    # 084: Costa and McCrae NEO-PI 1985 five-factor
    "manual operationalising the big-five trait inventory",
    # 085: Tanaka 1988 soft laser desorption MALDI
    "paper seeding the MALDI mass spectrometry technique for peptides",
    # 086: Anderson Imagined Communities 1983
    "book framing nations as print-capitalism constructs",
    # 087: Aunt Edna Medicaid spend-down worksheet 2026-05-15 deadline
    "filing deadline and asset plan for Aunt Edna's Medicaid waiver",
    # 088: Jay Rosen 2006 People Formerly Known as the Audience
    "essay that redefined audience passivity for the social web",
    # 089: Mikhail 2011 Elements of Moral Cognition
    "book modelling trolley intuitions as innate moral grammar",
    # 090: Mom's pho recipe green notebook page 47
    "which page holds Mom's noodle soup recipe",
    # 091: Great-Aunt Sabine bread book pre-1952 Alsace
    "pantry discovery predating the family's Alsace departure",
    # 092: CockroachDB SQL layer vs Spanner F1
    "open-source alternative to Spanner's F1 SQL layer",
    # 093: He et al. ResNet CVPR 2016
    "paper enabling hundred-layer networks through residual connections",
    # 094: Outback MOT 2026-09-14 Harbourside Auto
    "due date and garage for the Subaru's annual inspection",
    # 095: Rafailov et al. DPO NeurIPS 2023
    "paper replacing PPO in RLHF with a closed-form preference loss",
    # 096: Putnam Bowling Alone civic participation
    "study documenting postwar American social capital decline",
    # 097: Auntie Mei Lunar New Year eight courses fish and dumplings
    "customs governing the reunion feast at Auntie Mei's",
    # 098: Ainsworth Strange Situation 1978 attachment styles
    "procedure that defined secure, avoidant, and ambivalent attachment",
    # 099: Banerjee and Duflo RCTs in development economics
    "duo who centred randomised trials in poverty research",
    # 100: Gordon lab 2006 Nature obese-mice microbiome
    "Nature paper linking gut microbes to obesity energy harvest",
]


def emit() -> int:
    with SOURCES.open("r", encoding="utf-8") as f:
        sources = [json.loads(line) for line in f if line.strip()]
    assert len(sources) == 100, f"expected 100 sources, got {len(sources)}"
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as out:
        for query, src in zip(QUERIES, sources):
            row = {
                "id": src["new_id"],
                "source_id": src["source_id"],
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
