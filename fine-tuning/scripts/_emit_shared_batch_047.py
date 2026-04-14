"""One-off emitter for shared-base batch-047 — knowledge domain (climate / environmental science / sustainability).

Writes 50 rows to data/v2/shared/batch_047.tmp.jsonl with ids shared-02301..02350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_047.tmp.jsonl"
ID_OFFSET = 2300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Keeling Curve, maintained at Mauna Loa since 1958 by Charles David Keeling, provides the longest continuous record of atmospheric CO2 concentration.", "milestone", "knowledge", False,
     [("Keeling Curve", "publication"), ("Mauna Loa", "place"), ("1958", "date"), ("Charles David Keeling", "person"), ("CO2", "concept")],
     [("Keeling Curve", "Charles David Keeling", "AUTHORED_BY")],
     "which observatory record tracks rising atmospheric carbon dioxide continuously since the late 1950s",
     "Mauna Loa CO2 monitoring baseline long term record observatory"),
    # --- 2 ---
    ("IPCC AR6 Working Group I, released in 2021, concluded that human influence on the climate system is unequivocal.", "reference", "knowledge", False,
     [("IPCC AR6", "publication"), ("Working Group I", "organization"), ("2021", "date")],
     [("IPCC AR6", "Working Group I", "AUTHORED_BY")],
     "which 2021 assessment stated that human climate influence is unequivocal",
     "IPCC sixth assessment physical science basis unequivocal human"),
    # --- 3 ---
    ("The SSP scenario family replaces the earlier RCP nomenclature for driving CMIP6 climate projections with socioeconomic narratives.", "decision", "knowledge", False,
     [("SSP", "framework"), ("RCP", "framework"), ("CMIP6", "project")],
     [("SSP", "RCP", "REPLACES")],
     "which scenario naming framework superseded RCPs for the sixth-phase intercomparison",
     "shared socioeconomic pathway scenario matrix CMIP6 projection"),
    # --- 4 ---
    ("Hansen's 1981 Science paper projected anthropogenic warming signals that would emerge from natural variability by the end of the twentieth century.", "reference", "knowledge", False,
     [("Hansen", "person"), ("1981", "date"), ("Science", "publication")],
     [],
     "which early-1980s paper forecast detectable greenhouse warming within two decades",
     "Hansen Science 1981 detection attribution early projection"),
    # --- 5 ---
    ("Michael Mann's hockey stick reconstruction, published in 1998, showed twentieth-century Northern Hemisphere temperatures rising sharply above the preceding millennium.", "milestone", "knowledge", False,
     [("Michael Mann", "person"), ("hockey stick", "finding"), ("1998", "date"), ("Northern Hemisphere", "place")],
     [("hockey stick", "Michael Mann", "AUTHORED_BY")],
     "which 1998 paleoclimate reconstruction made the twentieth-century temperature spike famous",
     "millennial reconstruction hockey stick proxy Northern Hemisphere"),
    # --- 6 ---
    ("World Weather Attribution runs rapid attribution studies that quantify how anthropogenic climate change altered the likelihood of individual extreme events.", "fact", "knowledge", False,
     [("World Weather Attribution", "organization"), ("attribution studies", "method")],
     [("World Weather Attribution", "attribution studies", "IMPLEMENTS")],
     "which consortium issues rapid assessments of human influence on specific extreme events",
     "WWA attribution rapid extreme event likelihood change"),
    # --- 7 ---
    ("The planetary boundaries framework, proposed by Johan Rockstrom and colleagues in 2009, defines a safe operating space across nine Earth system processes.", "milestone", "knowledge", False,
     [("planetary boundaries framework", "framework"), ("Johan Rockstrom", "person"), ("2009", "date"), ("safe operating space", "concept")],
     [("planetary boundaries framework", "Johan Rockstrom", "AUTHORED_BY")],
     "when did the nine Earth-system safe-operating-space framework first appear",
     "planetary boundaries Rockstrom safe operating space nine processes year"),
    # --- 8 ---
    ("Kate Raworth's Doughnut Economics, published in 2017, pairs the planetary boundaries ceiling with a social foundation floor.", "reference", "knowledge", False,
     [("Kate Raworth", "person"), ("Doughnut Economics", "publication"), ("2017", "date"), ("planetary boundaries", "concept"), ("social foundation", "concept")],
     [("Doughnut Economics", "Kate Raworth", "AUTHORED_BY"), ("Doughnut Economics", "planetary boundaries", "BUILDS_ON")],
     "which 2017 book adds a social-foundation floor beneath the ecological ceiling",
     "doughnut economics ceiling floor social foundation year"),
    # --- 9 ---
    ("CMIP6 coordinates dozens of climate models worldwide through a shared experimental protocol to support IPCC assessments.", "architecture", "knowledge", False,
     [("CMIP6", "project"), ("climate models", "concept"), ("IPCC", "organization")],
     [("CMIP6", "IPCC", "DEPENDS_ON")],
     "which sixth-phase intercomparison project feeds climate model output into IPCC assessments",
     "coupled model intercomparison project sixth phase protocol"),
    # --- 10. noise ---
    ("Let me re-check the latest AR6 page numbers before I quote them.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Atlantic Meridional Overturning Circulation, or AMOC, shows proxy-based evidence of weakening over the twentieth century.", "fact", "knowledge", False,
     [("Atlantic Meridional Overturning Circulation", "concept"), ("AMOC", "concept")],
     [],
     "what deep-ocean circulation system appears to have lost strength across the last century",
     "AMOC thermohaline overturning slowdown proxy Atlantic"),
    # --- 12 ---
    ("Mass coral bleaching at widespread reef scale is triggered once sea-surface temperatures exceed the local summer maximum by about one degree Celsius for several weeks.", "fact", "knowledge", False,
     [("coral bleaching", "concept"), ("sea-surface temperatures", "concept")],
     [("coral bleaching", "sea-surface temperatures", "DEPENDS_ON")],
     "what temperature anomaly threshold drives mass coral bleaching events",
     "bleaching threshold degree week heat stress reef summer maximum"),
    # --- 13 ---
    ("The permafrost carbon feedback could release hundreds of gigatonnes of CO2 and methane as frozen organic matter thaws across the Arctic.", "fact", "knowledge", False,
     [("permafrost carbon feedback", "concept"), ("methane", "concept"), ("Arctic", "place")],
     [],
     "which northern-latitude feedback threatens to release buried organic carbon as warming proceeds",
     "permafrost thaw carbon release methane Arctic feedback"),
    # --- 14 ---
    ("The IEA Net Zero by 2050 roadmap, released in 2021, mapped sectoral milestones required to keep warming to 1.5C.", "reference", "knowledge", False,
     [("IEA", "organization"), ("Net Zero by 2050", "publication"), ("2021", "date"), ("1.5C", "concept")],
     [("Net Zero by 2050", "IEA", "AUTHORED_BY")],
     "which 2021 agency roadmap sequenced sector milestones for a 1.5C-compatible world",
     "IEA net zero 2050 roadmap sectoral milestone 1.5C"),
    # --- 15 ---
    ("The Science Based Targets initiative validates corporate emissions reduction targets against the level required to limit warming to well below two degrees.", "fact", "knowledge", False,
     [("Science Based Targets initiative", "organization"), ("corporate emissions", "concept")],
     [("Science Based Targets initiative", "corporate emissions", "IMPLEMENTS")],
     "which body approves corporate climate targets against a science-aligned trajectory",
     "SBTi validation corporate target well below two degrees"),
    # --- 16 ---
    ("Climeworks prefers modular direct air capture over point-source carbon capture to address dispersed legacy emissions.", "preference", "knowledge", False,
     [("Climeworks", "organization"), ("direct air capture", "technology"), ("point-source carbon capture", "technology")],
     [("direct air capture", "point-source carbon capture", "PREFERS")],
     "which Swiss firm favours direct air capture over flue-gas point-source solutions",
     "Climeworks modular DAC legacy emissions scalable preference"),
    # --- 17 ---
    ("Carbon Engineering's direct air capture plant in Texas is designed to capture one megatonne of CO2 per year at commercial scale.", "fact", "knowledge", False,
     [("Carbon Engineering", "organization"), ("direct air capture", "technology"), ("Texas", "place")],
     [("Carbon Engineering", "direct air capture", "IMPLEMENTS")],
     "which Canadian firm is building a megatonne-scale DAC facility in Texas",
     "Carbon Engineering Texas DAC megatonne commercial plant"),
    # --- 18 ---
    ("Weathering-based removal via enhanced rock weathering spreads crushed basalt on farmland to accelerate mineral reactions that lock CO2 into stable carbonates.", "fact", "knowledge", False,
     [("enhanced rock weathering", "method"), ("basalt", "concept"), ("farmland", "concept")],
     [("enhanced rock weathering", "basalt", "DEPENDS_ON")],
     "which land-based carbon removal spreads crushed volcanic rock on fields",
     "ERW basalt weathering farmland mineral CO2 lock"),
    # --- 19 ---
    ("Soil amendments like biochar, produced by pyrolysis of biomass under low oxygen, stabilise a portion of biogenic carbon in soils for decades to centuries.", "fact", "knowledge", False,
     [("biochar", "concept"), ("pyrolysis", "method"), ("biomass", "concept")],
     [("biochar", "pyrolysis", "DEPENDS_ON")],
     "which pyrolysis-derived soil amendment sequesters biomass carbon long-term",
     "biochar pyrolysis biomass soil sequestration residence"),
    # --- 20 ---
    ("IPCC guidelines distinguish afforestation, reforestation, and avoided deforestation for land-use carbon accounting.", "fact", "knowledge", False,
     [("IPCC", "organization"), ("afforestation", "concept"), ("reforestation", "concept"), ("avoided deforestation", "concept")],
     [],
     "how does the standard land-sector accounting framework handle new planting versus replanting versus saved forest",
     "IPCC land use carbon accounting afforestation reforestation guideline"),
    # --- 21 ---
    ("The question of soil carbon permanence remains contested because recent studies find that added organic carbon often cycles back out within a few decades.", "problem", "knowledge", False,
     [("soil carbon permanence", "concept"), ("organic carbon", "concept")],
     [],
     "why is soil-carbon sequestration flagged as uncertain for long-term drawdown",
     "soil carbon permanence cycling decadal uncertainty drawdown"),
    # --- 22 ---
    ("PAS 2060 specifies organisational carbon neutrality claims with reduction and offset requirements, while ISO 14064 standardises greenhouse gas accounting.", "fact", "knowledge", False,
     [("PAS 2060", "framework"), ("ISO 14064", "framework"), ("carbon neutrality", "concept")],
     [],
     "which British standard governs carbon neutrality claims alongside ISO 14064 accounting",
     "PAS 2060 carbon neutrality ISO 14064 GHG accounting standard"),
    # --- 23 ---
    ("The GHG Protocol structures corporate emissions into Scope 1 direct, Scope 2 purchased energy, and Scope 3 value chain categories.", "reference", "knowledge", False,
     [("GHG Protocol", "framework"), ("Scope 1", "concept"), ("Scope 2", "concept"), ("Scope 3", "concept")],
     [],
     "how do corporate greenhouse gas inventories carve up their reporting responsibility into three tiers",
     "GHG Protocol scope 1 2 3 direct indirect value chain"),
    # --- 24 ---
    ("Most voluntary carbon offsets trade outside compliance markets and have repeatedly been criticised for inflated emission reduction claims.", "problem", "knowledge", False,
     [("voluntary carbon offsets", "concept"), ("compliance markets", "concept")],
     [],
     "why do voluntary offsets attract persistent criticism compared with compliance schemes",
     "voluntary offset market integrity additionality inflation critique"),
    # --- 25 ---
    ("IPCC AR6 states that limiting warming to 1.5C requires a remaining carbon budget of roughly 500 gigatonnes of CO2 from 2020.", "fact", "knowledge", False,
     [("IPCC AR6", "publication"), ("1.5C", "concept"), ("carbon budget", "concept"), ("2020", "date")],
     [],
     "which assessment quotes a remaining carbon budget of about 500 Gt CO2 for 1.5C",
     "remaining carbon budget 500 gigatonne 1.5C 2020 AR6"),
    # --- 26 ---
    ("Residual cloud feedback uncertainty remains one of the largest contributors to the spread in equilibrium climate sensitivity across models.", "problem", "knowledge", False,
     [("cloud feedback", "concept"), ("equilibrium climate sensitivity", "concept")],
     [],
     "which feedback dominates the inter-model spread in climate sensitivity",
     "cloud feedback sensitivity ECS spread model uncertainty"),
    # --- 27 ---
    ("Anthropogenic aerosol cooling partly masks greenhouse warming by scattering sunlight and seeding brighter clouds, with the magnitude still poorly constrained.", "fact", "knowledge", False,
     [("aerosol cooling", "concept"), ("greenhouse warming", "concept")],
     [],
     "which anthropogenic forcing masks part of the greenhouse signal with bright-cloud effects",
     "aerosol cooling indirect forcing masking scattering uncertainty"),
    # --- 28 ---
    ("Global methane budgets estimate that oil and gas operations leak far more than official inventories report, based on satellite retrievals.", "fact", "knowledge", False,
     [("methane", "concept"), ("oil and gas operations", "concept"), ("satellite retrievals", "method")],
     [],
     "what do satellite methane retrievals suggest about reported oil and gas emissions",
     "methane budget oil gas leakage satellite retrieval underreport"),
    # --- 29 ---
    ("Hansen's 2023 Earth's Energy Imbalance paper argues that aerosol cleanup and ocean heat uptake imply faster near-term warming than IPCC central estimates.", "reference", "knowledge", False,
     [("Hansen", "person"), ("Earth's Energy Imbalance", "publication"), ("2023", "date"), ("IPCC", "organization")],
     [("Earth's Energy Imbalance", "Hansen", "AUTHORED_BY")],
     "which 2023 Hansen paper argues warming will accelerate beyond IPCC central estimates",
     "Hansen energy imbalance aerosol cleanup acceleration paper"),
    # --- 30. noise ---
    ("I should re-read the methods section before paraphrasing that climate claim.", "fact", "noise", True, [], [], None, None),
    # --- 31 ---
    ("Antarctic ice loss is dominated by ocean-driven thinning of West Antarctic ice shelves, while Arctic sea-ice loss is largely atmospheric in origin.", "fact", "knowledge", False,
     [("Antarctic", "place"), ("West Antarctic", "place"), ("Arctic", "place"), ("sea-ice", "concept")],
     [],
     "how does the dominant driver differ between Antarctic and Arctic ice loss",
     "Antarctic West ice shelf ocean Arctic atmosphere sea ice"),
    # --- 32 ---
    ("Globally integrated ocean heat content measured by the Argo float array absorbs more than 90 percent of the excess energy trapped by anthropogenic forcing.", "fact", "knowledge", False,
     [("ocean heat content", "concept"), ("Argo", "infrastructure"), ("anthropogenic forcing", "concept")],
     [("ocean heat content", "Argo", "DEPENDS_ON")],
     "which float network monitors the dominant sink of excess planetary heat",
     "Argo float ocean heat content 90 percent sink monitoring"),
    # --- 33 ---
    ("Worldwide glacial mass balance, tracked by the World Glacier Monitoring Service since 1894, shows accelerating loss across almost every reference glacier.", "fact", "knowledge", False,
     [("glacial mass balance", "concept"), ("World Glacier Monitoring Service", "organization"), ("1894", "date")],
     [("glacial mass balance", "World Glacier Monitoring Service", "DEPENDS_ON")],
     "which long-running monitoring network tracks global glacier mass balance",
     "WGMS mass balance glacier reference accelerating loss"),
    # --- 34 ---
    ("Advocates of degrowth argue that planned economic contraction in wealthy economies is required to stay within planetary boundaries.", "fact", "knowledge", False,
     [("degrowth", "theory"), ("planetary boundaries", "concept")],
     [("degrowth", "planetary boundaries", "DEPENDS_ON")],
     "which economic proposal ties wealthy-country contraction to staying inside planetary limits",
     "degrowth contraction wealthy economy planetary boundary proposal"),
    # --- 35 ---
    ("Modern attribution science shifted public discussion by showing, for example, that the 2003 European heatwave was made at least twice as likely by human influence.", "fact", "knowledge", False,
     [("attribution science", "field"), ("2003", "date"), ("European heatwave", "event")],
     [],
     "which 2003 European extreme-heat event was shown to be at least twice as likely under anthropogenic influence",
     "2003 European heatwave attribution twice likely finding"),
    # --- 36 ---
    ("IPBES Global Assessment, released in 2019, concluded that around one million species face extinction from combined human pressures.", "milestone", "knowledge", False,
     [("IPBES", "organization"), ("Global Assessment", "publication"), ("2019", "date")],
     [("Global Assessment", "IPBES", "AUTHORED_BY")],
     "which 2019 biodiversity assessment warned that a million species face extinction",
     "IPBES global assessment million species extinction year"),
    # --- 37 ---
    ("The biodiversity hotspots concept, defined by Norman Myers in 1988, prioritises conservation regions combining high endemism and severe habitat loss.", "milestone", "knowledge", False,
     [("biodiversity hotspots", "concept"), ("Norman Myers", "person"), ("1988", "date")],
     [("biodiversity hotspots", "Norman Myers", "AUTHORED_BY")],
     "who defined the hotspots idea linking endemism with habitat loss for conservation priority",
     "biodiversity hotspot Myers endemism habitat loss concept year"),
    # --- 38 ---
    ("The life-cycle assessment conventions set by ISO 14040 and ISO 14044 govern how practitioners draw system boundaries and allocate impacts.", "reference", "knowledge", False,
     [("life-cycle assessment", "method"), ("ISO 14040", "framework"), ("ISO 14044", "framework")],
     [],
     "which pair of ISO standards governs life-cycle assessment methodology",
     "LCA life cycle ISO 14040 14044 boundary allocation standard"),
    # --- 39 ---
    ("Contemporary attribution science prefers event-based probabilistic studies over trend-focused detection for communicating climate change to the public.", "preference", "knowledge", False,
     [("attribution science", "field"), ("event-based probabilistic studies", "method"), ("trend-focused detection", "method")],
     [("event-based probabilistic studies", "trend-focused detection", "PREFERS")],
     "which methodology do attribution scientists favour when communicating with the public",
     "event probabilistic attribution trend detection communication preference"),
    # --- 40 ---
    ("Global-mean sea level rise accelerated from about 1.4 mm per year across the twentieth century to roughly 3.7 mm per year over 2006 to 2018 per IPCC AR6.", "fact", "knowledge", False,
     [("sea level rise", "concept"), ("IPCC AR6", "publication"), ("2006", "date"), ("2018", "date")],
     [],
     "how has the sea level rise rate changed between the twentieth century and recent decades",
     "sea level rise rate acceleration 1.4 3.7 mm per year AR6"),
    # --- 41 ---
    ("IPCC SR15, released in 2018, framed the 1.5C goal as materially distinct from 2C in terms of ecosystem and human impacts.", "milestone", "knowledge", False,
     [("IPCC SR15", "publication"), ("2018", "date"), ("1.5C", "concept"), ("2C", "concept")],
     [],
     "which 2018 special report distinguished 1.5C from 2C impacts for policy",
     "SR15 special report 1.5C 2C difference impact 2018"),
    # --- 42 ---
    ("AR7 drafts are proceeding under an accelerated cycle with an expected Working Group I release in the late 2020s.", "fact", "knowledge", False,
     [("AR7", "publication"), ("Working Group I", "organization")],
     [],
     "which upcoming IPCC assessment cycle is expected to conclude Working Group I in the late 2020s",
     "AR7 seventh assessment Working Group I late 2020s cycle"),
    # --- 43 ---
    ("Early IPCC assessments depended on simple energy-balance models before being replaced by coupled atmosphere-ocean general circulation models in later cycles.", "decision", "knowledge", False,
     [("IPCC", "organization"), ("energy-balance models", "concept"), ("coupled atmosphere-ocean general circulation models", "concept")],
     [("coupled atmosphere-ocean general circulation models", "energy-balance models", "REPLACES")],
     "which model class superseded energy-balance approaches across IPCC assessment cycles",
     "energy balance AOGCM coupled model replacement assessment"),
    # --- 44 ---
    ("Climate policy analysts prefer carbon pricing over voluntary offset reliance for decarbonising tradable-sector emissions.", "preference", "knowledge", False,
     [("carbon pricing", "method"), ("voluntary offset", "concept"), ("tradable-sector emissions", "concept")],
     [("carbon pricing", "voluntary offset", "PREFERS")],
     "what mechanism do economists usually choose ahead of offsets for cutting industrial emissions",
     "carbon pricing tax ETS voluntary offset tradable sector preference"),
    # --- 45 ---
    ("The doughnut economics framework explicitly builds on the planetary boundaries ceiling while extending the model toward social equity.", "fact", "knowledge", False,
     [("doughnut economics", "framework"), ("planetary boundaries", "concept"), ("social equity", "concept")],
     [("doughnut economics", "planetary boundaries", "BUILDS_ON")],
     "how does the doughnut framework extend planetary boundaries toward social concerns",
     "doughnut framework planetary boundary ceiling social equity extension"),
    # --- 46 ---
    ("Modern net-zero pathway modellers improved on single-year target framing by building full cumulative-emissions budgets over multi-decade trajectories.", "decision", "knowledge", False,
     [("net-zero pathway", "method"), ("single-year target framing", "method"), ("cumulative-emissions budgets", "concept")],
     [("cumulative-emissions budgets", "single-year target framing", "IMPROVES_ON")],
     "which budget framing improved on single-year net-zero target modelling",
     "cumulative emissions budget net zero pathway single year improvement"),
    # --- 47 ---
    ("The Paris Agreement of 2015 set a long-term temperature goal of well below 2C with efforts to limit warming to 1.5C.", "milestone", "knowledge", False,
     [("Paris Agreement", "event"), ("2015", "date"), ("2C", "concept"), ("1.5C", "concept")],
     [],
     "which 2015 treaty fixed a temperature goal of well below 2C with a 1.5C ambition",
     "Paris Agreement 2015 temperature goal 2C 1.5C treaty"),
    # --- 48 ---
    ("Satellite-based GRACE measurements, operating since 2002, allow estimates of ice-sheet mass loss directly from Earth gravity field changes.", "fact", "knowledge", False,
     [("GRACE", "infrastructure"), ("2002", "date"), ("ice-sheet mass loss", "concept"), ("Earth gravity field", "concept")],
     [("ice-sheet mass loss", "GRACE", "DEPENDS_ON")],
     "which satellite gravity mission supports direct ice-sheet mass loss estimates since 2002",
     "GRACE gravity mission ice sheet mass balance 2002"),
    # --- 49 ---
    ("Observational ocean heat content datasets improved on early ship-based surveys once the Argo autonomous float programme reached near-global coverage in 2007.", "decision", "knowledge", False,
     [("ocean heat content", "concept"), ("ship-based surveys", "method"), ("Argo", "infrastructure"), ("2007", "date")],
     [("Argo", "ship-based surveys", "IMPROVES_ON")],
     "which ocean observing network improved on patchy ship-based sampling after 2007",
     "Argo float global coverage ship based survey ocean heat improvement"),
    # --- 50 ---
    ("Stephen Pacala and Robert Socolow proposed the stabilisation wedges framework in 2004 to decompose the mitigation challenge into manageable technology portfolios.", "reference", "knowledge", False,
     [("Stephen Pacala", "person"), ("Robert Socolow", "person"), ("stabilisation wedges", "framework"), ("2004", "date")],
     [("stabilisation wedges", "Stephen Pacala", "AUTHORED_BY"), ("stabilisation wedges", "Robert Socolow", "AUTHORED_BY")],
     "which 2004 Princeton framework broke mitigation into portfolio wedges",
     "stabilisation wedges Pacala Socolow portfolio mitigation framework"),
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
