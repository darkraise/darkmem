"""One-off emitter for shared-base batch-004 — knowledge domain.

Same pattern as _emit_shared_batch_003.py; only ENTRIES changes.
Appends 50 rows to data/v2/shared/shared.jsonl with ids shared-00151..00200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 150  # batches 001..003 consumed shared-00001..00150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. fact: physics ---
    ("The speed of light in a vacuum is exactly 299792458 metres per second since the 1983 SI redefinition.", "fact", "knowledge", False,
     [("speed of light", "concept"), ("SI", "concept")],
     [],
     "what is the defined value for light's vacuum velocity",
     "constant photon velocity SI redefinition year"),
    # --- 2. reference: paper ---
    ("Vaswani et al. introduced the transformer architecture in the 2017 paper Attention Is All You Need.", "reference", "knowledge", False,
     [("Vaswani et al.", "person"), ("transformer architecture", "concept"), ("Attention Is All You Need", "publication")],
     [("Attention Is All You Need", "Vaswani et al.", "AUTHORED_BY")],
     "where was the transformer architecture first formally proposed",
     "2017 attention paper original authorship"),
    # --- 3. decision: methodology ---
    ("The lab adopted Bayesian model averaging over single-model selection for the climate ensemble work.", "decision", "knowledge", False,
     [("Bayesian model averaging", "method"), ("single-model selection", "method")],
     [("Bayesian model averaging", "single-model selection", "REPLACES")],
     "which approach did the climate group switch to for ensembles",
     "weighting strategy choice climate study methodology"),
    # --- 4. fact: biology ---
    ("Mitochondria carry their own circular DNA inherited only from the maternal line in most animals.", "fact", "knowledge", False,
     [("Mitochondria", "concept"), ("circular DNA", "concept")],
     [("Mitochondria", "circular DNA", "HAS_PART")],
     "what genetic material do these organelles carry and from whom",
     "organelle genome maternal inheritance pattern"),
    # --- 5. preference: framework ---
    ("For exploratory analysis the team prefers tidyverse over base R; pipe chains read more clearly.", "preference", "knowledge", False,
     [("tidyverse", "tool"), ("base R", "tool")],
     [("tidyverse", "base R", "PREFERS")],
     "which R toolkit do we reach for during data exploration",
     "data wrangling library choice piping readability"),
    # --- 6. problem: replication ---
    ("The 2015 reproducibility study failed to replicate roughly 60 percent of the social psychology findings sampled.", "problem", "knowledge", False,
     [("reproducibility study", "finding"), ("social psychology", "field")],
     [],
     "what proportion of social findings did not hold up on retest",
     "replication crisis behavioural research failure rate"),
    # --- 7. milestone: discovery ---
    ("CRISPR-Cas9 gene editing was first demonstrated in human cells on 2013-01-03 by Zhang's group.", "milestone", "knowledge", False,
     [("CRISPR-Cas9", "method"), ("Zhang", "person"), ("2013-01-03", "date")],
     [],
     "when did genome editing first work in human cells",
     "Cas9 mammalian breakthrough demonstration date"),
    # --- 8. architecture: theory framing ---
    ("General relativity reframes gravity as curvature of spacetime rather than a force acting at a distance.", "architecture", "knowledge", False,
     [("General relativity", "theory"), ("gravity", "concept"), ("spacetime", "concept")],
     [("General relativity", "gravity", "APPLIES_TO")],
     "how does the geometric theory recast the gravitational interaction",
     "Einstein curvature gravity geometry reframing"),
    # --- 9. noise ---
    ("That sounds like a reasonable starting point, I think.", "fact", "noise", True, [], [], None, None),
    # --- 10. fact: chemistry ---
    ("Water reaches its maximum density near 4 degrees Celsius, which is why ice floats on lakes.", "fact", "knowledge", False,
     [("Water", "concept")],
     [],
     "why does ice end up sitting on top of liquid water",
     "H2O density anomaly four degree maximum"),
    # --- 11. reference: textbook ---
    ("The standard reference for convex optimization remains Boyd and Vandenberghe's 2004 textbook.", "reference", "knowledge", False,
     [("convex optimization", "field"), ("Boyd", "person"), ("Vandenberghe", "person")],
     [],
     "which textbook is canonical for the convex optimisation field",
     "2004 Boyd Vandenberghe canonical optimisation source"),
    # --- 12. decision: model class ---
    ("Switched from random forests to gradient-boosted trees for the churn model; lift was about 8 percent.", "decision", "knowledge", False,
     [("random forests", "method"), ("gradient-boosted trees", "method")],
     [("gradient-boosted trees", "random forests", "REPLACES")],
     "which classifier replaced the older one in the churn pipeline",
     "tree ensemble swap subscription dropoff lift"),
    # --- 13. preference: notation ---
    ("Most reviewers prefer Einstein summation notation over explicit sigmas in tensor-heavy proofs.", "preference", "knowledge", False,
     [("Einstein summation notation", "concept"), ("sigmas", "concept")],
     [("Einstein summation notation", "sigmas", "PREFERS")],
     "which notation style wins in tensor manipulation work",
     "implicit index convention versus written summation symbol"),
    # --- 14. fact: economics ---
    ("Diminishing marginal utility implies that the second slice of cake satisfies less than the first.", "fact", "knowledge", False,
     [("Diminishing marginal utility", "concept")],
     [],
     "what principle explains the falling satisfaction from extra units",
     "utility decline successive consumption microeconomic principle"),
    # --- 15. problem: data quality ---
    ("Survey responses from the 2024 cohort showed acquiescence bias that distorted the agreement scales.", "problem", "knowledge", False,
     [("acquiescence bias", "finding"), ("2024 cohort", "concept")],
     [],
     "what response pattern skewed the recent survey results",
     "yes-saying tendency rating scale distortion sample"),
    # --- 16. milestone: theory development ---
    ("Plate tectonics moved from fringe hypothesis to mainstream consensus during the 1960s.", "milestone", "knowledge", False,
     [("Plate tectonics", "theory")],
     [],
     "when did continental drift become widely accepted geology",
     "earth science mainstream shift 1960s consensus"),
    # --- 17. architecture: framework ---
    ("Kahneman's dual-process model splits cognition into a fast intuitive system and a slow deliberative one.", "architecture", "knowledge", False,
     [("Kahneman", "person"), ("dual-process model", "theory")],
     [("dual-process model", "Kahneman", "AUTHORED_BY")],
     "how does the dual-process picture of thinking break down",
     "two-system cognition fast slow framework attribution"),
    # --- 18. fact: linguistics ---
    ("Universal Grammar posits an innate language faculty common to all neurotypical humans.", "fact", "knowledge", False,
     [("Universal Grammar", "theory")],
     [],
     "what does this hypothesis claim about innate language ability",
     "Chomsky innate faculty cross-population claim"),
    # --- 19. reference: standard ---
    ("Statistical reporting follows the APA 7th edition guidelines for figures, tables, and effect sizes.", "reference", "knowledge", False,
     [("APA 7th edition", "publication")],
     [],
     "which style guide governs how stats get presented in papers",
     "psychology format manual seventh revision rules"),
    # --- 20. decision: method ---
    ("For the meta-analysis we used random-effects models because between-study heterogeneity was high.", "decision", "knowledge", False,
     [("meta-analysis", "method"), ("random-effects models", "method")],
     [],
     "why did the meta-analysis go with random rather than fixed effects",
     "pooled study modelling heterogeneity rationale"),
    # --- 21. preference: software ---
    ("For symbolic mathematics the group reaches for Mathematica before SymPy when expressions get hairy.", "preference", "knowledge", False,
     [("Mathematica", "tool"), ("SymPy", "tool")],
     [("Mathematica", "SymPy", "PREFERS")],
     "which symbolic system handles the gnarliest expressions for us",
     "computer algebra package complex symbolic preference"),
    # --- 22. problem: measurement ---
    ("The Hubble tension persists because local-distance and CMB-based measurements yield incompatible expansion rates.", "problem", "knowledge", False,
     [("Hubble tension", "finding"), ("CMB", "concept")],
     [],
     "why does cosmology have an open problem around expansion rates",
     "universe rate disagreement cosmic background versus local"),
    # --- 23. milestone: result ---
    ("AlphaFold 2 reached experimental-quality structure prediction on the 2020 CASP14 benchmark.", "milestone", "knowledge", False,
     [("AlphaFold 2", "tool"), ("CASP14", "concept")],
     [],
     "when did protein structure prediction match wet-lab quality",
     "structure prediction breakthrough biennial benchmark"),
    # --- 24. architecture: review process ---
    ("Conference reviews use a double-blind protocol with three reviewers and a meta-reviewer per paper.", "architecture", "knowledge", False,
     [("double-blind protocol", "method")],
     [],
     "how is paper review structured at this venue",
     "anonymous peer evaluation reviewer count workflow"),
    # --- 25. fact: math ---
    ("The fundamental theorem of calculus links differentiation and integration as inverse operations.", "fact", "knowledge", False,
     [("fundamental theorem of calculus", "theory")],
     [],
     "which classical result pairs up rates of change with area under curves",
     "calculus duality bridging derivative antiderivative"),
    # --- 26. reference: dataset ---
    ("Benchmarks for English NER usually cite CoNLL-2003 as the de facto evaluation set.", "reference", "knowledge", False,
     [("CoNLL-2003", "publication"), ("NER", "concept")],
     [],
     "which dataset is the standard for English entity tagging benchmarks",
     "named entity gold corpus annotation reference"),
    # --- 27. decision: scale ---
    ("Switched the readability metric from Flesch-Kincaid to LIX after the multilingual review.", "decision", "knowledge", False,
     [("Flesch-Kincaid", "method"), ("LIX", "method")],
     [("LIX", "Flesch-Kincaid", "REPLACES")],
     "what index took over for measuring prose difficulty after the cross-language audit",
     "text difficulty metric swap non-English coverage"),
    # --- 28. preference: source type ---
    ("For epidemiology questions the group leans on Cochrane reviews before single trials.", "preference", "knowledge", False,
     [("Cochrane reviews", "publication"), ("epidemiology", "field")],
     [],
     "what evidence type does the group consult first in epi questions",
     "systematic review priority single trial alternative"),
    # --- 29. problem: bias ---
    ("Selection bias in the recruitment process inflated the apparent effect by an estimated 18 percent.", "problem", "knowledge", False,
     [("Selection bias", "finding")],
     [],
     "how much did the recruitment artefact distort the headline effect",
     "sampling skew effect size inflation estimate"),
    # --- 30. milestone: prize ---
    ("Carolyn Bertozzi won the Nobel in chemistry in 2022 for click chemistry and bioorthogonal reactions.", "milestone", "knowledge", False,
     [("Carolyn Bertozzi", "person"), ("click chemistry", "concept"), ("bioorthogonal reactions", "concept"), ("2022", "date")],
     [],
     "which researcher took home the 2022 prize for bio-compatible coupling",
     "Bertozzi bioconjugation award year recognition"),
    # --- 31. architecture: framework ---
    ("FAIR data principles ask that records be findable, accessible, interoperable, and reusable.", "architecture", "knowledge", False,
     [("FAIR data principles", "concept")],
     [],
     "what does the FAIR acronym stand for in data stewardship",
     "data stewardship four-letter framework expansion"),
    # --- 32. fact: history ---
    ("The Library of Alexandria's decline was gradual rather than the result of any single catastrophic fire.", "fact", "knowledge", False,
     [("Library of Alexandria", "concept")],
     [],
     "how did the famed ancient library actually fade from relevance",
     "Alexandrian collection slow decline historiographical view"),
    # --- 33. reference: protocol ---
    ("The CONSORT 2010 statement is the citable checklist for reporting randomised trials.", "reference", "knowledge", False,
     [("CONSORT 2010", "publication")],
     [],
     "which checklist do RCT papers cite for reporting completeness",
     "trial reporting standard 2010 update document"),
    # --- 34. decision: language choice ---
    ("Picked Julia over Python for the differential equations service because the loops ran 40 times faster.", "decision", "knowledge", False,
     [("Julia", "tool"), ("Python", "tool")],
     [("Julia", "Python", "REPLACES")],
     "what language took over the ODE service and why",
     "scientific compute swap loop performance reason"),
    # --- 35. noise ---
    ("Okay, give me a moment to look that up properly.", "fact", "noise", True, [], [], None, None),
    # --- 36. preference: study design ---
    ("Whenever possible we run within-subjects designs over between-subjects ones to control individual variance.", "preference", "knowledge", False,
     [("within-subjects designs", "method"), ("between-subjects", "method")],
     [("within-subjects designs", "between-subjects", "PREFERS")],
     "which experimental layout do we default to in practice",
     "repeated measures versus independent groups choice"),
    # --- 37. problem: theory limit ---
    ("Newtonian mechanics breaks down once velocities approach a non-trivial fraction of light's speed.", "problem", "knowledge", False,
     [("Newtonian mechanics", "theory")],
     [],
     "where does classical mechanics stop being a good description",
     "low-energy theory failure relativistic regime threshold"),
    # --- 38. milestone: result ---
    ("LIGO detected the first gravitational wave signal on 2015-09-14 from a binary black hole merger.", "milestone", "knowledge", False,
     [("LIGO", "tool"), ("2015-09-14", "date")],
     [],
     "when was the first direct gravitational wave detection",
     "interferometer first signal binary merger date"),
    # --- 39. architecture: workflow ---
    ("Systematic reviews follow PRISMA stages: identification, screening, eligibility, and inclusion.", "architecture", "knowledge", False,
     [("PRISMA", "method")],
     [],
     "what stages structure a systematic review under the standard guideline",
     "review pipeline four-stage flow guideline"),
    # --- 40. fact: ethics ---
    ("Informed consent requires capacity, voluntariness, and adequate disclosure of foreseeable risks.", "fact", "knowledge", False,
     [("Informed consent", "concept")],
     [],
     "what three elements does valid consent rest on",
     "research ethics consent triad capacity disclosure"),
    # --- 41. reference: encyclopaedia ---
    ("The Stanford Encyclopedia of Philosophy entry on free will is the standard starting point for the debate.", "reference", "knowledge", False,
     [("Stanford Encyclopedia of Philosophy", "publication"), ("free will", "concept")],
     [],
     "where do graduate students usually start the free will debate",
     "philosophy reference work entry agency starting source"),
    # --- 42. decision: hypothesis ---
    ("Adopted the hierarchical Dirichlet prior for topic count selection after the AIC and BIC disagreed.", "decision", "knowledge", False,
     [("hierarchical Dirichlet prior", "method"), ("AIC", "method"), ("BIC", "method")],
     [],
     "what prior did we settle on when standard criteria conflicted",
     "topic model selection nonparametric prior choice"),
    # --- 43. preference: replication ---
    ("Two independent replications outweigh a single high-powered original in our team's evidence weighting.", "preference", "knowledge", False,
     [("replications", "method")],
     [],
     "how does the team weight repeated studies against one large original",
     "evidence calibration multiple replication versus single trial"),
    # --- 44. problem: theory clash ---
    ("Quantum mechanics and general relativity contradict each other at Planck-scale energies.", "problem", "knowledge", False,
     [("Quantum mechanics", "theory"), ("general relativity", "theory"), ("Planck-scale", "concept")],
     [("Quantum mechanics", "general relativity", "CONTRADICTS")],
     "where do the two pillars of modern physics fail to agree",
     "small-scale gravity quantum reconciliation problem"),
    # --- 45. milestone: technique ---
    ("Cryo-electron microscopy revolutionised structural biology, recognised by the 2017 Nobel chemistry prize.", "milestone", "knowledge", False,
     [("Cryo-electron microscopy", "method"), ("2017", "date")],
     [],
     "which imaging technique reshaped structural biology recently",
     "frozen sample electron imaging Nobel chemistry recognition"),
    # --- 46. architecture: model ---
    ("The standard model of particle physics organises fermions and bosons into three generations.", "architecture", "knowledge", False,
     [("standard model", "theory"), ("fermions", "concept"), ("bosons", "concept")],
     [("standard model", "fermions", "HAS_PART"), ("standard model", "bosons", "HAS_PART")],
     "how does the particle physics framework group its constituents",
     "particle taxonomy three generation organising scheme"),
    # --- 47. fact: medicine ---
    ("Penicillin's discovery in 1928 by Fleming changed the trajectory of bacterial infection treatment.", "fact", "knowledge", False,
     [("Penicillin", "concept"), ("Fleming", "person"), ("1928", "date")],
     [("Penicillin", "Fleming", "AUTHORED_BY")],
     "who first noticed the antibiotic effect that became penicillin",
     "antibiotic discovery early twentieth century chance finding"),
    # --- 48. reference: corpus ---
    ("ImageNet remains the foundational benchmark for image classification papers from the 2010s onward.", "reference", "knowledge", False,
     [("ImageNet", "publication")],
     [],
     "which dataset shaped the last decade of vision benchmarks",
     "large-scale labelled image collection vision evaluation"),
    # --- 49. decision: prior ---
    ("Switched the spatial smoothing prior from Gaussian to Matern; the latter handled local roughness better.", "decision", "knowledge", False,
     [("Gaussian", "method"), ("Matern", "method")],
     [("Matern", "Gaussian", "REPLACES")],
     "which spatial smoothing prior took over and why",
     "geostatistics covariance prior swap roughness handling"),
    # --- 50. preference: open access ---
    ("The lab prefers preprints on arXiv before journal publication; feedback loops are tighter.", "preference", "knowledge", False,
     [("arXiv", "tool")],
     [],
     "where does the lab post early drafts before formal venues",
     "open repository early sharing preference review loop"),
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
    with OUT.open("a", encoding="utf-8") as f:
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
