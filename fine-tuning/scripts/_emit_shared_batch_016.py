"""One-off emitter for shared-base batch-016 — knowledge domain (hard sciences).

Writes 50 rows to data/v2/shared/batch_016.tmp.jsonl with ids shared-00751..00800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_016.tmp.jsonl"
ID_OFFSET = 750

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Noether's theorem ties every continuous symmetry of a physical system to a conserved quantity.", "fact", "knowledge", False,
     [("Noether's theorem", "theory"), ("continuous symmetry", "concept"), ("conserved quantity", "concept")],
     [],
     "which theorem links symmetries of an action to conservation laws",
     "symmetry conservation law bridge classical mechanics result"),
    # --- 2 ---
    ("Griffiths's Introduction to Electrodynamics remains the standard undergraduate text for Maxwell-era physics.", "reference", "knowledge", False,
     [("Griffiths", "person"), ("Introduction to Electrodynamics", "publication"), ("Maxwell-era physics", "concept")],
     [("Introduction to Electrodynamics", "Griffiths", "AUTHORED_BY")],
     "which textbook anchors undergraduate Maxwell-era electrodynamics teaching",
     "undergraduate classical electromagnetism canonical textbook author"),
    # --- 3 ---
    ("For ultracold atoms the group prefers laser cooling over buffer-gas cooling; the temperatures reachable differ by orders of magnitude.", "preference", "knowledge", False,
     [("laser cooling", "method"), ("buffer-gas cooling", "method"), ("ultracold atoms", "concept")],
     [("laser cooling", "buffer-gas cooling", "PREFERS")],
     "which atom-cooling approach wins when the target is microkelvin regimes",
     "atomic physics cooling technique choice low temperature regime"),
    # --- 4 ---
    ("Loop quantum gravity builds on general relativity by quantising spacetime geometry rather than treating gravity as a field on a background.", "decision", "knowledge", False,
     [("Loop quantum gravity", "theory"), ("general relativity", "theory")],
     [("Loop quantum gravity", "general relativity", "BUILDS_ON")],
     "which quantum gravity programme extends general relativity by quantising geometry itself",
     "spin network background independence quantum geometry programme"),
    # --- 5 ---
    ("Cosmic microwave background temperature sits at 2.725 kelvin, with fluctuations of order one part in a hundred thousand.", "fact", "knowledge", False,
     [("Cosmic microwave background", "concept"), ("2.725 kelvin", "concept")],
     [],
     "what mean temperature and fluctuation level characterise the relic radiation",
     "relic radiation mean temperature anisotropy amplitude cosmology"),
    # --- 6 ---
    ("The Event Horizon Telescope released its first resolved image of the M87 supermassive black hole on 2019-04-10.", "milestone", "knowledge", False,
     [("Event Horizon Telescope", "project"), ("M87", "concept"), ("supermassive black hole", "concept"), ("2019-04-10", "date")],
     [],
     "when did a global VLBI array first resolve a black hole shadow",
     "black hole shadow first image date VLBI collaboration"),
    # --- 7 ---
    ("Dark energy surveys routinely hit a tension between Type Ia supernova calibrations and CMB-derived expansion histories.", "problem", "knowledge", False,
     [("Dark energy", "concept"), ("Type Ia supernova", "concept"), ("CMB", "concept")],
     [],
     "what tension keeps resurfacing between supernova and microwave-background distance ladders",
     "cosmological parameter tension distance ladder disagreement"),
    # --- 8 ---
    ("Rubin's 1970s rotation-curve measurements of spiral galaxies cemented the empirical case for dark matter.", "reference", "knowledge", False,
     [("Rubin", "person"), ("rotation-curve measurements", "method"), ("dark matter", "concept")],
     [("rotation-curve measurements", "Rubin", "AUTHORED_BY")],
     "whose galactic rotation data nailed the case for missing mass",
     "spiral galaxy flat rotation curve empirical dark matter evidence"),
    # --- 9 ---
    ("The IceCube neutrino observatory confirmed TXS 0506+056 as an astrophysical neutrino source in 2018.", "milestone", "knowledge", False,
     [("IceCube", "tool"), ("TXS 0506+056", "concept"), ("neutrino", "concept"), ("2018", "date")],
     [],
     "when did Antarctic neutrino detection first tie a blazar to high-energy neutrinos",
     "blazar neutrino identification year Antarctic detector finding"),
    # --- 10. noise ---
    ("Let me pull up the reference before I go further.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Bell-test experiments repeatedly violate local-hidden-variable bounds, leaving quantum nonlocality as the remaining explanation.", "fact", "knowledge", False,
     [("Bell-test experiments", "method"), ("local-hidden-variable bounds", "concept"), ("quantum nonlocality", "concept")],
     [],
     "what repeatedly violated classical bounds forces nonlocal quantum correlations",
     "entanglement test inequality violation foundational experiment"),
    # --- 12 ---
    ("The atomic clock ensemble at NIST keeps UTC with fractional frequency stability near ten-to-the-minus-sixteen.", "architecture", "knowledge", False,
     [("NIST", "organization"), ("UTC", "concept"), ("atomic clock", "tool")],
     [],
     "how precise is the US national timekeeping ensemble",
     "national timekeeping fractional stability atomic clock ensemble"),
    # --- 13 ---
    ("Planck's constant was fixed at 6.62607015 times ten-to-the-minus-34 joule-seconds with the 2019 SI redefinition.", "milestone", "knowledge", False,
     [("Planck's constant", "concept"), ("2019 SI redefinition", "event"), ("joule-seconds", "concept")],
     [],
     "when did the kilogram's redefinition freeze Planck's constant at an exact value",
     "fundamental constant fixed SI redefinition year unit basis"),
    # --- 14 ---
    ("Peebles's Physical Cosmology set out the Friedmann-Lemaitre framework as the backbone for modern cosmological measurement.", "reference", "knowledge", False,
     [("Peebles", "person"), ("Physical Cosmology", "publication"), ("Friedmann-Lemaitre framework", "theory")],
     [("Physical Cosmology", "Peebles", "AUTHORED_BY")],
     "whose textbook made the expanding-universe equations the measurement backbone",
     "cosmology textbook expanding universe equations author"),
    # --- 15 ---
    ("The laboratory prefers inductively coupled plasma mass spectrometry over flame atomic absorption for trace metal work.", "preference", "knowledge", False,
     [("inductively coupled plasma mass spectrometry", "method"), ("flame atomic absorption", "method"), ("trace metal", "concept")],
     [("inductively coupled plasma mass spectrometry", "flame atomic absorption", "PREFERS")],
     "which elemental analysis wins when trace metals need sub-ppb detection",
     "analytical chemistry trace metal instrument choice detection limit"),
    # --- 16 ---
    ("Pauling's The Nature of the Chemical Bond reframed bonding around hybridisation and resonance.", "reference", "knowledge", False,
     [("Pauling", "person"), ("The Nature of the Chemical Bond", "publication"), ("hybridisation", "concept"), ("resonance", "concept")],
     [("The Nature of the Chemical Bond", "Pauling", "AUTHORED_BY")],
     "whose book made hybridisation and resonance the vocabulary of chemical bonding",
     "chemical bonding landmark text hybridisation resonance author"),
    # --- 17 ---
    ("Suzuki-Miyaura cross-coupling improves on Stille coupling for pharmaceutical scale-up because the boron by-products are far less toxic.", "decision", "knowledge", False,
     [("Suzuki-Miyaura cross-coupling", "method"), ("Stille coupling", "method")],
     [("Suzuki-Miyaura cross-coupling", "Stille coupling", "IMPROVES_ON")],
     "which palladium cross-coupling wins when scale-up demands benign by-products",
     "palladium catalysis cross-coupling scale up by-product toxicity"),
    # --- 18 ---
    ("Benzene's aromaticity rests on a planar ring of six pi electrons satisfying Huckel's rule.", "fact", "knowledge", False,
     [("Benzene", "concept"), ("aromaticity", "concept"), ("Huckel's rule", "theory"), ("pi electrons", "concept")],
     [],
     "why does benzene qualify as aromatic under Huckel counting",
     "planar ring pi electron count aromatic criterion benzene"),
    # --- 19 ---
    ("Bartlett's 1962 synthesis of xenon hexafluoroplatinate shattered the dogma that noble gases are chemically inert.", "milestone", "knowledge", False,
     [("Bartlett", "person"), ("xenon hexafluoroplatinate", "concept"), ("noble gases", "concept"), ("1962", "date")],
     [],
     "whose synthesis first proved noble gases can form stable compounds",
     "noble gas chemistry first compound chemist year breakthrough"),
    # --- 20 ---
    ("Le Chatelier's principle predicts how an equilibrium shifts when a system is perturbed in concentration, pressure, or temperature.", "fact", "knowledge", False,
     [("Le Chatelier's principle", "theory"), ("equilibrium", "concept")],
     [],
     "which principle forecasts equilibrium response to external perturbations",
     "equilibrium shift perturbation prediction rule chemistry"),
    # --- 21 ---
    ("Protein quantification runs now prefer the BCA assay over Bradford because the response is more linear across detergent-containing buffers.", "preference", "knowledge", False,
     [("BCA assay", "method"), ("Bradford", "method"), ("Protein quantification", "concept")],
     [("BCA assay", "Bradford", "PREFERS")],
     "which protein quantification method wins when detergents are in the buffer",
     "protein assay detergent tolerance linearity workflow choice"),
    # --- 22 ---
    ("Endosymbiotic theory claims mitochondria and chloroplasts descend from free-living prokaryotes engulfed by an ancestral eukaryote.", "fact", "knowledge", False,
     [("Endosymbiotic theory", "theory"), ("mitochondria", "concept"), ("chloroplasts", "concept"), ("eukaryote", "concept")],
     [],
     "what evolutionary theory explains the prokaryotic origin of organelles",
     "mitochondria chloroplast prokaryote ancestor engulfment explanation"),
    # --- 23 ---
    ("Watson and Crick's 1953 Nature paper laid out the DNA double helix based on Franklin's diffraction data.", "milestone", "knowledge", False,
     [("Watson", "person"), ("Crick", "person"), ("Franklin", "person"), ("DNA double helix", "concept"), ("1953", "date")],
     [],
     "whose paper set out the double-helix structure and when",
     "DNA structure landmark paper authors year diffraction"),
    # --- 24 ---
    ("Kimura's neutral theory of molecular evolution argues most genetic variation is selectively neutral rather than adaptive.", "reference", "knowledge", False,
     [("Kimura", "person"), ("neutral theory of molecular evolution", "theory"), ("genetic variation", "concept")],
     [("neutral theory of molecular evolution", "Kimura", "AUTHORED_BY")],
     "whose theory claims most molecular variation sits outside selection",
     "molecular evolution neutral drift population genetics architect"),
    # --- 25 ---
    ("Long-read sequencing from PacBio replaced short-read Illumina as the primary platform for the reference assembly.", "decision", "knowledge", False,
     [("PacBio", "tool"), ("Illumina", "tool"), ("reference assembly", "concept")],
     [("PacBio", "Illumina", "REPLACES")],
     "which sequencing platform took over from short-read for the reference assembly",
     "long-read sequencing platform switch reference genome assembly"),
    # --- 26 ---
    ("Ecosystem service valuation frameworks still struggle with double-counting between provisioning services and regulating services.", "problem", "knowledge", False,
     [("Ecosystem service valuation", "method"), ("provisioning services", "concept"), ("regulating services", "concept")],
     [],
     "which accounting problem plagues ecosystem service valuations",
     "ecosystem service accounting double-counting category overlap"),
    # --- 27 ---
    ("Keeling's Mauna Loa CO2 record, started in 1958, established the modern trajectory of atmospheric carbon dioxide.", "milestone", "knowledge", False,
     [("Keeling", "person"), ("Mauna Loa", "place"), ("CO2 record", "finding"), ("1958", "date")],
     [],
     "whose Hawaiian monitoring series captured the rising CO2 curve",
     "atmospheric carbon dioxide trend Pacific observatory year founder"),
    # --- 28 ---
    ("Modern paleoclimate reconstructions prefer ice-core isotope proxies over tree-ring width for sub-millennial temperature signals.", "preference", "knowledge", False,
     [("ice-core isotope proxies", "method"), ("tree-ring width", "method"), ("paleoclimate reconstructions", "concept")],
     [("ice-core isotope proxies", "tree-ring width", "PREFERS")],
     "which paleoclimate proxy wins for sub-millennial temperature reconstruction",
     "paleoclimate proxy choice ice core tree ring temperature signal"),
    # --- 29 ---
    ("Wegener's 1915 Origin of Continents and Oceans proposed continental drift decades before the seafloor evidence arrived.", "reference", "knowledge", False,
     [("Wegener", "person"), ("Origin of Continents and Oceans", "publication"), ("continental drift", "theory"), ("1915", "date")],
     [("Origin of Continents and Oceans", "Wegener", "AUTHORED_BY")],
     "whose 1915 book argued for drifting continents before the seafloor data",
     "continental drift early advocate publication year geology"),
    # --- 30 ---
    ("Thermohaline circulation problems show up in climate models as North Atlantic sinking weakens under freshwater forcing.", "problem", "knowledge", False,
     [("Thermohaline circulation", "concept"), ("North Atlantic", "place"), ("freshwater forcing", "concept")],
     [],
     "which overturning component weakens when models add surface freshwater",
     "overturning current weakening surface freshening sensitivity"),
    # --- 31 ---
    ("Ocean acidification runs on the same proton chemistry as carbonate buffer attacks: absorbed CO2 lowers seawater pH.", "fact", "knowledge", False,
     [("Ocean acidification", "concept"), ("carbonate buffer", "concept"), ("CO2", "concept"), ("seawater pH", "concept")],
     [],
     "what proton chemistry drives the pH drop in surface oceans",
     "ocean pH decrease dissolved CO2 carbonate equilibrium mechanism"),
    # --- 32 ---
    ("The CHIRP radar on ESA missions replaced fixed-frequency pulse radar for ice-sheet sounding on Mars analog studies.", "decision", "knowledge", False,
     [("CHIRP radar", "method"), ("fixed-frequency pulse radar", "method"), ("ice-sheet sounding", "concept"), ("ESA", "organization")],
     [("CHIRP radar", "fixed-frequency pulse radar", "REPLACES")],
     "which sounding radar took over from fixed-frequency pulses on ESA ice-penetrating missions",
     "ice penetrating radar chirp signal resolution bandwidth replacement"),
    # --- 33 ---
    ("Kepler's three laws of planetary motion describe orbits as ellipses, with equal areas in equal times and a period-distance law.", "fact", "knowledge", False,
     [("Kepler", "person"), ("laws of planetary motion", "theory"), ("ellipses", "concept")],
     [("laws of planetary motion", "Kepler", "AUTHORED_BY")],
     "whose three laws describe elliptical planetary orbits and harmonic periods",
     "planetary motion ellipse equal area harmonic law author"),
    # --- 34. noise ---
    ("Hold on, let me grab the paper to confirm the figure.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Exoplanet transit photometry from Kepler pushed the field from dozens of known planets to several thousand confirmed detections.", "milestone", "knowledge", False,
     [("transit photometry", "method"), ("Kepler", "project"), ("Exoplanet", "concept")],
     [],
     "which mission drove exoplanet counts from dozens into the thousands",
     "transit method exoplanet census space mission confirmed count"),
    # --- 36 ---
    ("Schrodinger's equation governs the time evolution of the nonrelativistic wavefunction for a quantum system.", "fact", "knowledge", False,
     [("Schrodinger's equation", "theory"), ("wavefunction", "concept")],
     [("Schrodinger's equation", "wavefunction", "APPLIES_TO")],
     "which equation drives nonrelativistic wavefunction evolution",
     "wavefunction time evolution nonrelativistic foundational equation"),
    # --- 37 ---
    ("The group prefers GROMACS over AMBER for molecular dynamics when large membrane systems dominate the workload.", "preference", "knowledge", False,
     [("GROMACS", "tool"), ("AMBER", "tool"), ("molecular dynamics", "method"), ("membrane systems", "concept")],
     [("GROMACS", "AMBER", "PREFERS")],
     "which MD engine wins for large membrane simulations",
     "molecular dynamics engine choice membrane simulation throughput"),
    # --- 38 ---
    ("Density functional theory made ab-initio chemistry tractable by replacing wavefunction methods for most ground-state property calculations.", "decision", "knowledge", False,
     [("Density functional theory", "method"), ("wavefunction methods", "method"), ("ab-initio chemistry", "concept")],
     [("Density functional theory", "wavefunction methods", "REPLACES")],
     "which electronic-structure method took over from wavefunction calculations for routine ground states",
     "electronic structure tractability ground state routine calculation"),
    # --- 39 ---
    ("Fossil calibration of molecular clocks still introduces large uncertainty windows on divergence dates across metazoan lineages.", "problem", "knowledge", False,
     [("Fossil calibration", "method"), ("molecular clocks", "method"), ("metazoan lineages", "concept")],
     [],
     "which calibration source keeps widening uncertainty on deep metazoan divergence dates",
     "molecular clock calibration fossil uncertainty divergence window"),
    # --- 40 ---
    ("The CERN Large Hadron Collider is an underground synchrotron spanning 27 kilometres of superconducting magnets across the Franco-Swiss border.", "architecture", "knowledge", False,
     [("CERN", "organization"), ("Large Hadron Collider", "tool"), ("superconducting magnets", "concept")],
     [],
     "how is the flagship European collider physically laid out",
     "European collider layout circumference magnet technology location"),
    # --- 41 ---
    ("Bjerknes's 1904 paper framed weather forecasting as an initial-value problem in the primitive equations of the atmosphere.", "reference", "knowledge", False,
     [("Bjerknes", "person"), ("weather forecasting", "field"), ("primitive equations", "theory"), ("1904", "date")],
     [("primitive equations", "Bjerknes", "AUTHORED_BY")],
     "whose 1904 paper turned forecasting into an initial-value problem",
     "numerical weather prediction foundational paper author year"),
    # --- 42 ---
    ("Richter-scale magnitudes were superseded by the moment-magnitude scale for large earthquake characterisation in modern seismology.", "decision", "knowledge", False,
     [("moment-magnitude scale", "method"), ("Richter-scale magnitudes", "method"), ("seismology", "field")],
     [("moment-magnitude scale", "Richter-scale magnitudes", "REPLACES")],
     "which magnitude scale took over from Richter for large-earthquake work",
     "earthquake magnitude scale modernisation seismology replacement"),
    # --- 43 ---
    ("South-pole ozone monitoring by the British Antarctic Survey detected the springtime ozone hole in 1985.", "milestone", "knowledge", False,
     [("British Antarctic Survey", "organization"), ("ozone hole", "finding"), ("1985", "date")],
     [],
     "when did Antarctic monitoring first flag the springtime ozone hole",
     "Antarctic ozone hole detection year monitoring survey"),
    # --- 44 ---
    ("Hardy-Weinberg equilibrium in population genetics holds when a population has no selection, mutation, migration, drift, or assortative mating.", "fact", "knowledge", False,
     [("Hardy-Weinberg equilibrium", "theory"), ("population genetics", "field")],
     [],
     "under what five conditions does allele frequency stay constant generation to generation",
     "population genetics equilibrium assumption list frequency stability"),
    # --- 45 ---
    ("The group now prefers nanopore direct RNA sequencing over cDNA Illumina for detecting base modifications.", "preference", "knowledge", False,
     [("nanopore direct RNA sequencing", "method"), ("cDNA Illumina", "method"), ("base modifications", "concept")],
     [("nanopore direct RNA sequencing", "cDNA Illumina", "PREFERS")],
     "which RNA-seq workflow wins when RNA base modifications matter",
     "direct RNA sequencing modification detection platform preference"),
    # --- 46 ---
    ("LSST's Vera C. Rubin Observatory began its ten-year Legacy Survey of Space and Time on 2025-10-24.", "milestone", "knowledge", False,
     [("LSST", "project"), ("Vera C. Rubin Observatory", "tool"), ("Legacy Survey of Space and Time", "project"), ("2025-10-24", "date")],
     [],
     "when did the Rubin Observatory start its decade-long optical survey",
     "wide fast deep optical survey start date Chilean observatory"),
    # --- 47 ---
    ("The laboratory favours ATAC-seq over DNase-seq for chromatin accessibility profiling because the input requirement is far lower.", "preference", "knowledge", False,
     [("ATAC-seq", "method"), ("DNase-seq", "method"), ("chromatin accessibility", "concept")],
     [("ATAC-seq", "DNase-seq", "PREFERS")],
     "which chromatin accessibility assay wins when input material is scarce",
     "chromatin accessibility protocol choice low input assay"),
    # --- 48 ---
    ("Standard mantle plume models struggle to explain why the Hawaiian hotspot track shows a sharp bend near 47 million years ago.", "problem", "knowledge", False,
     [("mantle plume models", "theory"), ("Hawaiian hotspot track", "finding"), ("47 million years ago", "date")],
     [],
     "which hotspot track feature keeps eluding plume-model explanations",
     "hotspot track bend age mantle plume explanation gap"),
    # --- 49 ---
    ("Reviewers expect IUPAC nomenclature for chemical names in primary literature, reserving trivial names for introductions only.", "architecture", "knowledge", False,
     [("IUPAC nomenclature", "method"), ("trivial names", "method"), ("primary literature", "concept")],
     [],
     "which naming convention is required in chemistry primary literature",
     "chemistry nomenclature standard reviewer expectation naming rule"),
    # --- 50 ---
    ("Gravitational wave astronomy took a second leap with GW170817, the 2017-08-17 binary neutron star merger with electromagnetic counterpart.", "milestone", "knowledge", False,
     [("GW170817", "finding"), ("binary neutron star merger", "concept"), ("2017-08-17", "date"), ("Gravitational wave astronomy", "field")],
     [],
     "which 2017 multimessenger event paired gravitational waves with an EM counterpart",
     "binary neutron star merger multimessenger gravitational wave date"),
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
