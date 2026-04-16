"""One-off emitter for shared-base batch-281 — knowledge domain (climate science: Arrhenius, Keeling, IPCC, forcings, sensitivity, feedbacks, tipping points, paleoclimate, proxies, models, policy, CDR).

Writes 50 rows to data/v2/shared/batch_281.tmp.jsonl with ids shared-14001..14050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_281.tmp.jsonl"
ID_OFFSET = 14000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Svante Arrhenius published the first quantitative estimate of CO2-driven warming in 1896, calculating that doubling atmospheric CO2 would raise surface temperature by roughly four to five kelvin.", "milestone", "knowledge", False,
     [("Svante Arrhenius", "person"), ("CO2", "concept"), ("1896", "date")],
     [("Svante Arrhenius", "CO2", "APPLIES_TO")],
     "which nineteenth-century chemist first quantified the warming from doubling atmospheric carbon dioxide",
     "arrhenius 1896 co2 doubling warming quantitative climate sensitivity"),
    # --- 2 ---
    ("Charles David Keeling began continuous CO2 monitoring at Mauna Loa in 1958, producing the curve that turned fossil-fuel emissions from a hypothesis into a measured secular trend.", "milestone", "knowledge", False,
     [("Charles David Keeling", "person"), ("Mauna Loa", "project"), ("1958", "date"), ("CO2", "concept")],
     [("Charles David Keeling", "Mauna Loa", "APPLIES_TO")],
     "who started the Mauna Loa CO2 record and what did the resulting curve demonstrate",
     "keeling mauna loa 1958 co2 curve continuous monitoring trend"),
    # --- 3 ---
    ("The IPCC AR6 WG1 Summary for Policymakers landed in August 2021 and formally assessed the Charney equilibrium climate sensitivity range as 2.5 to 4 kelvin, narrower than the prior 1.5 to 4.5 window.", "reference", "knowledge", False,
     [("IPCC", "organization"), ("AR6 WG1", "project"), ("Summary for Policymakers", "publication"), ("Charney", "concept"), ("2021", "date")],
     [("IPCC", "AR6 WG1", "APPLIES_TO")],
     "which IPCC assessment narrowed the equilibrium climate sensitivity window from the Charney range",
     "ipcc ar6 wg1 spm 2021 charney ecs range sensitivity narrow"),
    # --- 4 ---
    ("Adopted the AR6 WG1 forcing breakdown in the internal briefing: CO2 carries about 2.16 W/m², methane 0.54 W/m², N2O 0.21 W/m², with tropospheric aerosols delivering roughly -1.1 W/m² offset.", "decision", "knowledge", False,
     [("AR6 WG1", "project"), ("CO2", "concept"), ("methane", "concept"), ("N2O", "concept"), ("aerosols", "concept")],
     [("AR6 WG1", "CO2", "APPLIES_TO"), ("aerosols", "CO2", "CONTRADICTS")],
     "which assessment's radiative forcing breakdown did the briefing adopt and what offset did aerosols contribute",
     "ar6 radiative forcing co2 methane n2o aerosol watts"),
    # --- 5 ---
    ("Equilibrium climate sensitivity and transient climate response measure different clocks: ECS is the long-run warming after CO2 doubling stabilises, while TCR captures warming at the moment of doubling under a 1 percent per year ramp.", "fact", "knowledge", False,
     [("ECS", "concept"), ("TCR", "concept"), ("CO2", "concept")],
     [("ECS", "TCR", "RELATED_TO")],
     "how do equilibrium climate sensitivity and transient climate response differ in what they measure",
     "ecs tcr climate sensitivity transient doubling ramp equilibrium"),
    # --- 6 ---
    ("The Charney Report fixed the ECS range at 1.5 to 4.5 kelvin in 1979; four decades of paleo and instrumental constraints narrowed it but never escaped that envelope until AR6 tightened both tails.", "reference", "knowledge", False,
     [("Charney Report", "publication"), ("ECS", "concept"), ("1979", "date"), ("AR6", "project")],
     [("AR6", "Charney Report", "IMPROVES_ON")],
     "which 1979 report set the original ECS range and how long did its envelope hold",
     "charney report 1979 ecs range kelvin ar6 narrow"),
    # --- 7 ---
    ("Ice-albedo feedback dominates polar amplification: shrinking sea ice exposes dark ocean, the surface absorbs more shortwave, and the Arctic warms at roughly three times the global mean.", "fact", "knowledge", False,
     [("Ice-albedo", "concept"), ("polar amplification", "concept"), ("Arctic", "place"), ("sea ice", "concept")],
     [("Ice-albedo", "polar amplification", "CAUSES")],
     "which feedback drives polar amplification and by what factor does the Arctic warm relative to the globe",
     "ice albedo feedback polar amplification arctic sea ice shortwave"),
    # --- 8 ---
    ("Water-vapour feedback is the largest positive feedback in the climate system: a warmer troposphere holds more H2O via Clausius-Clapeyron and roughly doubles the direct CO2 forcing.", "fact", "knowledge", False,
     [("Water-vapour", "concept"), ("Clausius-Clapeyron", "algorithm"), ("H2O", "concept"), ("CO2", "concept")],
     [("Water-vapour", "CO2", "APPLIES_TO")],
     "which feedback is the single largest positive amplifier and which thermodynamic relation governs it",
     "water vapour feedback clausius clapeyron co2 troposphere amplify"),
    # --- 9 ---
    ("Cloud feedback remains the dominant uncertainty in ECS: low-cloud response in the subtropics splits CMIP6 models, with some showing strong positive feedback and others near-neutral on shortwave trapping.", "problem", "knowledge", False,
     [("Cloud feedback", "concept"), ("CMIP6", "project"), ("ECS", "concept"), ("subtropics", "place")],
     [("Cloud feedback", "ECS", "APPLIES_TO")],
     "which feedback remains the chief uncertainty in climate sensitivity and where does CMIP6 disagree",
     "cloud feedback cmip6 ecs uncertainty subtropical low shortwave"),
    # --- 10. noise ---
    ("The conference coffee machine produced three distinct foam densities depending on whether morning, afternoon, or late plenary.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("AMOC weakening is treated as a tipping element: paleo reconstructions of the Younger Dryas show a decadal-scale collapse once freshwater forcing crossed a threshold around twelve thousand years ago.", "architecture", "knowledge", False,
     [("AMOC", "concept"), ("Younger Dryas", "concept"), ("tipping element", "concept"), ("freshwater forcing", "concept")],
     [("freshwater forcing", "AMOC", "CAUSES")],
     "which paleo event shows decadal AMOC collapse under freshwater forcing",
     "amoc younger dryas tipping freshwater collapse decadal paleo"),
    # --- 12 ---
    ("Amazon dieback crosses a self-reinforcing threshold once dry-season length exceeds a canopy tolerance; regional rainfall recycles less moisture, savanna replaces forest, and the biome flips.", "architecture", "knowledge", False,
     [("Amazon dieback", "concept"), ("savanna", "concept"), ("dry-season", "concept")],
     [("dry-season", "Amazon dieback", "CAUSES")],
     "which hydrological threshold flips the Amazon into a savanna state",
     "amazon dieback savanna dry season rainfall recycle threshold biome"),
    # --- 13 ---
    ("Greenland ice sheet committed loss: surface melt above the equilibrium-line altitude lowers elevation, exposing ice to warmer air, locking in multi-metre sea-level rise over millennia once the threshold is crossed.", "architecture", "knowledge", False,
     [("Greenland ice sheet", "place"), ("equilibrium-line altitude", "concept"), ("sea-level rise", "concept")],
     [("Greenland ice sheet", "sea-level rise", "CAUSES")],
     "which elevation feedback locks in Greenland sea-level commitment once a threshold is passed",
     "greenland ice sheet equilibrium line altitude sea level commit melt"),
    # --- 14 ---
    ("WAIS marine-ice-sheet instability is the standing risk flagged in the sea-level chapter: the West Antarctic grounding line sits on reverse-sloped bedrock, so any retreat drags the line into deeper water and accelerates, with Thwaites and Pine Island anchoring the risk.", "problem", "knowledge", False,
     [("WAIS", "place"), ("marine-ice-sheet instability", "concept"), ("Thwaites", "place"), ("Pine Island", "place")],
     [("WAIS", "marine-ice-sheet instability", "APPLIES_TO")],
     "which bedrock geometry drives WAIS instability and which glaciers anchor the risk",
     "wais thwaites pine island marine ice sheet instability grounding"),
    # --- 15 ---
    ("Permafrost methane release operates on two timescales: surface thaw emits CO2 on decadal scales, while abrupt thermokarst and subsea clathrates can vent methane on annual-to-centennial windows.", "fact", "knowledge", False,
     [("Permafrost", "concept"), ("methane", "concept"), ("thermokarst", "concept"), ("clathrates", "concept")],
     [("Permafrost", "methane", "CAUSES")],
     "which two timescales govern permafrost carbon release and what form does each take",
     "permafrost methane co2 thermokarst clathrate decadal centennial"),
    # --- 16 ---
    ("Arctic summer sea ice is projected to reach a practically ice-free September under SSP2-4.5 before 2050 in most CMIP6 members; the definition uses the one-million-square-kilometre threshold.", "reference", "knowledge", False,
     [("Arctic", "place"), ("sea ice", "concept"), ("SSP2-4.5", "concept"), ("CMIP6", "project")],
     [("CMIP6", "sea ice", "APPLIES_TO")],
     "under which scenario do CMIP6 models project an ice-free Arctic September and what area threshold defines it",
     "arctic september ice free ssp2 cmip6 million km"),
    # --- 17 ---
    ("Ocean acidification from anthropogenic CO2 uptake: surface pH has dropped from roughly 8.21 preindustrial to 8.10 today, a 30 percent increase in hydrogen-ion concentration, and aragonite saturation horizons shoal into shallower water.", "fact", "knowledge", False,
     [("Ocean acidification", "concept"), ("CO2", "concept"), ("pH", "concept"), ("aragonite", "concept")],
     [("CO2", "Ocean acidification", "CAUSES")],
     "how much has surface ocean pH dropped since preindustrial and what happens to aragonite horizons",
     "ocean acidification ph 8 21 8 10 aragonite saturation horizon"),
    # --- 18 ---
    ("Adopted the Global Carbon Budget partition numbers for the scenario briefing: 46 percent airborne, 26 percent to ocean, 28 percent to land sinks, with the airborne fraction tracked against cumulative emissions each year.", "decision", "knowledge", False,
     [("Global Carbon Budget", "project"), ("airborne fraction", "concept"), ("ocean", "concept"), ("land sinks", "concept")],
     [],
     "which dataset supplied the atmosphere-ocean-land partition numbers adopted in the scenario briefing",
     "global carbon budget airborne fraction ocean land sink adopt"),
    # --- 19 ---
    ("Adopted the full Milankovitch forcing decomposition in the paleo benchmark: eccentricity at 100 kyr, obliquity at 41 kyr, precession at 23 kyr, with CO2 amplification layered on top of the orbital insolation signal.", "decision", "knowledge", False,
     [("Milankovitch", "concept"), ("eccentricity", "concept"), ("obliquity", "concept"), ("precession", "concept"), ("CO2", "concept")],
     [("CO2", "Milankovitch", "CAUSES")],
     "which orbital decomposition was adopted in the paleo benchmark and what sits on top of the insolation signal",
     "milankovitch eccentricity obliquity precession co2 benchmark adopt"),
    # --- 20 ---
    ("Selected EPICA Dome C for the 800 kyr CO2 reconstruction over Vostok because the Dome C record extends further back and shares the same LGM-to-interglacial pattern with tighter dating.", "decision", "knowledge", False,
     [("EPICA", "project"), ("Dome C", "place"), ("Vostok", "place"), ("CO2", "concept"), ("LGM", "concept")],
     [("EPICA", "Vostok", "PREFERS")],
     "which ice core was chosen over Vostok for the 800 kyr CO2 reconstruction and why",
     "epica dome c vostok kyr co2 ice core"),
    # --- 21 ---
    ("Picked WAIS Divide over GISP2 for the glacial-termination chemistry layer because WAIS Divide resolves annual layers and its methane synchrony with Greenland nails the bipolar seesaw.", "decision", "knowledge", False,
     [("WAIS Divide", "project"), ("GISP2", "project"), ("bipolar seesaw", "concept"), ("Greenland", "place"), ("methane", "concept")],
     [("WAIS Divide", "GISP2", "PREFERS")],
     "which ice core won the glacial-termination chemistry slot over GISP2 and why",
     "wais divide gisp2 glacial termination bipolar seesaw methane choice"),
    # --- 22 ---
    ("Shipped the full paleoclimate proxy stack in the briefing layer: foraminifera δ18O for ocean temperature, stalagmites for tropical precipitation, tree rings for recent centuries, and ice cores for atmospheric gases.", "milestone", "knowledge", False,
     [("foraminifera", "concept"), ("δ18O", "concept"), ("stalagmites", "concept"), ("tree rings", "concept"), ("ice cores", "concept")],
     [],
     "which set of paleoclimate proxies shipped together in the briefing layer and what does each cover",
     "foraminifera d18o stalagmite tree ring ice core ship proxy briefing"),
    # --- 23 ---
    ("The PETM at 56 Ma saw a 5-to-8 kelvin warming in under 20 kyr driven by a massive carbon release; the δ13C excursion in benthic foraminifera is the calling card of the event.", "reference", "knowledge", False,
     [("PETM", "concept"), ("benthic foraminifera", "concept"), ("δ13C", "concept"), ("56 Ma", "date")],
     [("PETM", "δ13C", "APPLIES_TO")],
     "which paleoclimate event at 56 Ma is identified by the δ13C excursion and what warming magnitude accompanied it",
     "petm 56 ma d13c benthic foraminifera excursion carbon release"),
    # --- 24 ---
    ("CMIP6 is the coordinated multi-model intercomparison underpinning AR6; participating ESMs include CESM, HadGEM3, E3SM, GISS-E2, and MIROC6, each contributing runs under shared SSP forcings.", "architecture", "knowledge", False,
     [("CMIP6", "project"), ("AR6", "project"), ("CESM", "library"), ("HadGEM3", "library"), ("E3SM", "library"), ("GISS-E2", "library"), ("MIROC6", "library")],
     [("CMIP6", "AR6", "APPLIES_TO")],
     "which model intercomparison underpins AR6 and which major Earth system models participate",
     "cmip6 ar6 cesm hadgem3 e3sm giss miroc esm intercomparison"),
    # --- 25 ---
    ("Standardised on CESM2 as the reference ESM for the regional downscaling pipeline; CESM2 carries the well-tested CAM6 atmosphere and ships complete CMIP6 forcing datasets out of the box.", "decision", "knowledge", False,
     [("CESM2", "library"), ("CAM6", "library"), ("CMIP6", "project"), ("ESM", "concept")],
     [("CESM2", "ESM", "APPLIES_TO")],
     "which Earth system model became the reference for regional downscaling and what components argued for it",
     "cesm2 cam6 esm regional downscale reference cmip6 forcing"),
    # --- 26 ---
    ("Prefer HadGEM3 over GISS-E2 for the North Atlantic storm-track study because HadGEM3 resolves the eddy-driven jet with less bias in the blocking frequency over the study region.", "preference", "knowledge", False,
     [("HadGEM3", "library"), ("GISS-E2", "library"), ("North Atlantic", "place"), ("eddy-driven jet", "concept")],
     [("HadGEM3", "GISS-E2", "PREFERS")],
     "which model was preferred for the North Atlantic storm-track study and what bias argued for it",
     "hadgem3 giss north atlantic storm track eddy jet blocking bias"),
    # --- 27 ---
    ("Paris Agreement in December 2015 set a long-term temperature goal of holding warming well below 2 kelvin and pursuing efforts to limit it to 1.5 kelvin above preindustrial.", "reference", "knowledge", False,
     [("Paris Agreement", "publication"), ("2015", "date"), ("1.5 kelvin", "concept"), ("2 kelvin", "concept")],
     [],
     "what two temperature thresholds did the Paris Agreement pin in its long-term goal",
     "paris agreement 2015 preindustrial long term goal"),
    # --- 28 ---
    ("COP28 in Dubai in 2023 produced the first Global Stocktake text explicitly calling for transitioning away from fossil fuels in energy systems, a linguistic milestone after decades of hedged wording.", "milestone", "knowledge", False,
     [("COP28", "project"), ("Dubai", "place"), ("2023", "date"), ("Global Stocktake", "publication")],
     [("COP28", "Global Stocktake", "APPLIES_TO")],
     "which COP produced the first Global Stocktake text naming fossil-fuel transition and where was it hosted",
     "cop28 dubai 2023 global stocktake fossil fuel transition text"),
    # --- 29 ---
    ("NDCs under the Paris framework are submitted on a five-year cycle; the aggregate ambition gap remains such that even full implementation of current pledges tracks closer to 2.5 kelvin than to 1.5 kelvin.", "problem", "knowledge", False,
     [("NDCs", "publication"), ("Paris", "publication"), ("1.5 kelvin", "concept")],
     [],
     "how often are NDCs refreshed under Paris and how large is the current ambition gap",
     "ndc paris five year cycle ambition gap kelvin"),
    # --- 30 ---
    ("The Climeworks Orca DAC plant in Iceland captures roughly 4 kilotonnes CO2 per year and pumps it into basaltic mineralisation at the Carbfix site; the successor Mammoth plant targets 36 kilotonnes.", "milestone", "knowledge", False,
     [("Climeworks", "organization"), ("Orca", "project"), ("Iceland", "place"), ("Carbfix", "project"), ("Mammoth", "project"), ("DAC", "concept")],
     [("Climeworks", "Carbfix", "USES")],
     "which DAC plant pairs with Carbfix mineralisation and how much CO2 does it capture",
     "climeworks orca iceland carbfix basalt mineral dac mammoth"),
    # --- 31 ---
    ("Carbon Engineering runs a liquid-solvent DAC process using KOH capture and CaCO3 regeneration; the pilot in Squamish informed the 1 Mt/yr Stratos plant under construction with Occidental in Texas.", "architecture", "knowledge", False,
     [("Carbon Engineering", "organization"), ("KOH", "concept"), ("CaCO3", "concept"), ("Squamish", "place"), ("Stratos", "project"), ("Occidental", "organization")],
     [("Carbon Engineering", "Stratos", "APPLIES_TO")],
     "which solvent chemistry does Carbon Engineering use and which 1 Mt/yr facility scales it",
     "carbon engineering koh caco3 squamish stratos occidental dac"),
    # --- 32 ---
    ("Prefer Enhanced rock weathering over biochar for the broadacre pilot: spreading crushed basalt on cropland draws CO2 into bicarbonate, piggybacks on existing agricultural logistics, and adds soil cation benefits the farmers already want.", "preference", "knowledge", False,
     [("Enhanced rock weathering", "concept"), ("biochar", "concept"), ("basalt", "concept"), ("bicarbonate", "concept"), ("CO2", "concept")],
     [("Enhanced rock weathering", "biochar", "PREFERS"), ("Enhanced rock weathering", "CO2", "CONTRADICTS")],
     "which CDR approach was preferred over biochar for the broadacre pilot and what farmer-side benefit sealed it",
     "enhanced rock weathering biochar broadacre basalt bicarbonate prefer"),
    # --- 33 ---
    ("Chose Biochar over cover-crop sequestration for the smallholder CDR pilot because pyrolysed carbon stays recalcitrant for centuries and the field tests show 60 to 80 percent of char carbon surviving in soil.", "decision", "knowledge", False,
     [("Biochar", "concept"), ("CDR", "concept"), ("pyrolysed", "concept"), ("recalcitrant", "concept")],
     [("Biochar", "CDR", "APPLIES_TO")],
     "which CDR approach won the smallholder pilot over cover-crop sequestration and what residence argued for it",
     "biochar cdr pilot pyrolysis recalcitrant centuries smallholder"),
    # --- 34 ---
    ("Ocean alkalinity enhancement dissolves limestone or olivine into seawater so the carbonate system absorbs more CO2 at equilibrium; dispersion and monitoring remain the open engineering questions.", "architecture", "knowledge", False,
     [("Ocean alkalinity", "concept"), ("limestone", "concept"), ("olivine", "concept"), ("CO2", "concept")],
     [("Ocean alkalinity", "CO2", "CONTRADICTS")],
     "how does ocean alkalinity enhancement absorb CO2 and what remain the open engineering questions",
     "ocean alkalinity enhancement limestone olivine carbonate co2 absorb"),
    # --- 35 ---
    ("BECCS stacks bioenergy with carbon capture and storage: biomass combustion yields electricity while flue-gas CO2 is piped to saline aquifer sequestration; the land-use footprint bounds the achievable scale.", "architecture", "knowledge", False,
     [("BECCS", "concept"), ("bioenergy", "concept"), ("carbon capture", "concept"), ("saline aquifer", "concept"), ("CO2", "concept")],
     [("BECCS", "CO2", "CONTRADICTS")],
     "how does BECCS chain bioenergy with storage and what physical constraint caps its scale",
     "beccs bioenergy carbon capture storage biomass saline aquifer land"),
    # --- 36 ---
    ("Added Black carbon as a first-class forcing in the near-term scenario runs rather than folding it into aerosols; deposition on snow and ice lowers albedo and the direct absorption adds roughly 0.1 W/m² positive forcing.", "decision", "knowledge", False,
     [("Black carbon", "concept"), ("aerosols", "concept"), ("albedo", "concept"), ("snow", "concept"), ("ice", "concept")],
     [("Black carbon", "albedo", "CAUSES")],
     "which short-lived forcer got promoted out of the aerosol bucket in the near-term runs and why",
     "black carbon aerosol split albedo snow ice"),
    # --- 37 ---
    ("Solar irradiance variability contributes only tenths of a watt per square metre over the 11-year cycle; it cannot account for the late-twentieth-century warming, which coincides with a flat-to-declining solar trend.", "fact", "knowledge", False,
     [("Solar irradiance", "concept"), ("11-year cycle", "concept")],
     [],
     "how large is solar variability over the 11-year cycle and why can it not explain recent warming",
     "solar irradiance 11 year cycle watts late twentieth century flat"),
    # --- 38 ---
    ("Lapse-rate feedback is modestly negative globally because the tropics warm faster aloft than at the surface, increasing outgoing longwave for a given surface temperature; the Arctic reverses the sign locally.", "fact", "knowledge", False,
     [("Lapse-rate", "concept"), ("tropics", "place"), ("Arctic", "place")],
     [],
     "why is the global lapse-rate feedback negative in the tropics and what happens in the Arctic",
     "lapse rate feedback tropics arctic longwave sign reverse"),
    # --- 39 ---
    ("James Hansen's 1988 Senate testimony framed anthropogenic warming as detectable in the instrumental record; the Scenario B trajectory in the accompanying paper tracked reasonably close to observed global mean temperature for decades.", "milestone", "knowledge", False,
     [("James Hansen", "person"), ("1988", "date"), ("Scenario B", "concept")],
     [("James Hansen", "Scenario B", "APPLIES_TO")],
     "which Hansen testimony year and scenario are cited for framing detectable anthropogenic warming",
     "hansen 1988 senate testimony scenario b detectable warming"),
    # --- 40 ---
    ("Michael Mann's hockey-stick reconstruction combined tree-ring, coral, and ice-core proxies to show the twentieth century exiting the millennial envelope; multiple independent reconstructions have since confirmed the shape.", "reference", "knowledge", False,
     [("Michael Mann", "person"), ("hockey-stick", "concept"), ("tree-ring", "concept"), ("coral", "concept"), ("ice-core", "concept")],
     [("Michael Mann", "hockey-stick", "APPLIES_TO")],
     "which multi-proxy reconstruction by Mann produced the hockey-stick and which proxies fed it",
     "mann hockey stick tree ring coral ice core reconstruction millennium"),
    # --- 41 ---
    ("Katharine Hayhoe's public-communication stance explicitly separates the physical evidence from the values debate; the preferred framing leads with shared community concerns before introducing the science.", "preference", "knowledge", False,
     [("Katharine Hayhoe", "person")],
     [],
     "how does Hayhoe prefer to frame climate communication when facing value-laden audiences",
     "hayhoe communication values community framing science public"),
    # --- 42 ---
    ("Susan Solomon led the science that pinned Antarctic ozone depletion on CFCs, which unlocked the Montreal Protocol; the same forensic approach later informed CFC-11 emissions detection from unexpected eastern-hemisphere sources.", "milestone", "knowledge", False,
     [("Susan Solomon", "person"), ("CFCs", "concept"), ("Montreal Protocol", "publication"), ("Antarctic", "place"), ("CFC-11", "concept")],
     [("Susan Solomon", "Montreal Protocol", "APPLIES_TO")],
     "which Solomon-led science enabled the Montreal Protocol and what later emissions detection used the same methods",
     "solomon cfc antarctic ozone montreal protocol cfc 11 detection"),
    # --- 43. noise ---
    ("The seminar room's second projector has a stuck pixel that lives exactly on the y-axis of every plot it displays.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Adopted SSP2-4.5 as the mid-range baseline scenario for the impact study and SSP5-8.5 as the worst-case stress test; SSP1-2.6 is kept as the Paris-aligned comparison but not the working baseline.", "decision", "knowledge", False,
     [("SSP2-4.5", "concept"), ("SSP5-8.5", "concept"), ("SSP1-2.6", "concept"), ("Paris", "publication")],
     [("SSP2-4.5", "SSP5-8.5", "RELATED_TO")],
     "which SSP scenarios were chosen as baseline and stress test, and which Paris-aligned run stays as comparison",
     "ssp2 ssp5 ssp1 baseline paris aligned scenario"),
    # --- 45 ---
    ("Preferred AR6 WG2 framing over raw CMIP6 output for communicating impacts: WG2 already harmonises risk metrics across sectors, which shaved weeks off the translation layer in the stakeholder briefing.", "preference", "knowledge", False,
     [("AR6 WG2", "project"), ("CMIP6", "project")],
     [("AR6 WG2", "CMIP6", "PREFERS")],
     "which IPCC product was preferred over raw CMIP6 for impact communication and what effort did it save",
     "ar6 wg2 cmip6 impact communication risk harmonise stakeholder"),
    # --- 46 ---
    ("Anchored the internal mitigation narrative on AR6 WG3 1.5-compatible pathways that require rapid cuts plus hundreds of gigatonnes of cumulative CDR; no assessed 1.5-compatible pathway avoids CDR entirely.", "decision", "knowledge", False,
     [("AR6 WG3", "project"), ("1.5-compatible", "concept"), ("CDR", "concept")],
     [("AR6 WG3", "CDR", "APPLIES_TO")],
     "which IPCC product anchors the internal mitigation narrative and what role does CDR play in 1.5-compatible pathways",
     "ar6 wg3 mitigation 1 5 cdr pathway anchor narrative gigatonne"),
    # --- 47 ---
    ("Standardised the internal model benchmark against the HadCRUT5 observational dataset for global mean temperature and against ERA5 for reanalysis fields; GISTEMP stays as the independent cross-check.", "decision", "knowledge", False,
     [("HadCRUT5", "library"), ("ERA5", "library"), ("GISTEMP", "library")],
     [("HadCRUT5", "GISTEMP", "RELATED_TO")],
     "which observational and reanalysis datasets anchor the internal benchmark and which serves as the cross-check",
     "hadcrut5 era5 gistemp observation reanalysis benchmark cross check"),
    # --- 48 ---
    ("E3SM targets exascale hardware and ran the first fully-coupled ESM simulation on Frontier; the design prioritises high-resolution ocean and regional water-cycle fidelity over century-long ensembles.", "architecture", "knowledge", False,
     [("E3SM", "library"), ("Frontier", "platform"), ("ESM", "concept")],
     [("E3SM", "Frontier", "APPLIES_TO")],
     "which ESM targets exascale and on which system did it run the first fully-coupled simulation",
     "e3sm frontier exascale esm coupled ocean resolution water cycle"),
    # --- 49 ---
    ("Bounded the natural CO2 envelope in the communications deck using the EPICA glacial-interglacial range of 180 to 280 ppm, with the preindustrial baseline pinned as the upper bound of that natural swing.", "decision", "knowledge", False,
     [("EPICA", "project"), ("glacial-interglacial", "concept"), ("CO2", "concept"), ("preindustrial", "concept")],
     [("EPICA", "CO2", "APPLIES_TO")],
     "which dataset bounded the natural CO2 envelope in the communications deck and where sits the preindustrial baseline",
     "epica glacial interglacial co2 180 280 ppm preindustrial bound deck"),
    # --- 50 ---
    ("Migrated the regional impact pipeline from RCP4.5/RCP8.5 forcings to SSP2-4.5/SSP5-8.5; the SSP set bundles socioeconomic assumptions with the emissions trajectory and aligns with AR6 outputs downstream.", "architecture", "knowledge", False,
     [("RCP4.5", "concept"), ("RCP8.5", "concept"), ("SSP2-4.5", "concept"), ("SSP5-8.5", "concept"), ("AR6", "project")],
     [("SSP2-4.5", "RCP4.5", "REPLACES"), ("SSP5-8.5", "RCP8.5", "REPLACES")],
     "which scenario framework replaced the RCP set in the regional impact pipeline and what did the SSPs add",
     "rcp ssp scenario framework socioeconomic ar6 replace"),
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
