"""One-off emitter for shared-base batch-009 — knowledge domain (round 2).

Appends 50 rows to data/v2/shared/shared.jsonl with ids shared-00401..00450.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 400

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The second law of thermodynamics states that entropy of an isolated system never decreases.", "fact", "knowledge", False,
     [("second law of thermodynamics", "theory"), ("entropy", "concept")],
     [],
     "what does the classical thermodynamics rule imply for closed systems",
     "isolated system disorder direction universal constraint"),
    # --- 2 ---
    ("Dawkins's The Selfish Gene reframed evolution around the replicator rather than the organism.", "reference", "knowledge", False,
     [("Dawkins", "person"), ("The Selfish Gene", "publication"), ("evolution", "concept")],
     [("The Selfish Gene", "Dawkins", "AUTHORED_BY")],
     "which book recast natural selection around replicators",
     "gene-centric Darwinism popular science title"),
    # --- 3 ---
    ("Preregistration replaces open-ended hypothesis drift; the analysis plan is locked before data collection.", "decision", "knowledge", False,
     [("Preregistration", "method"), ("hypothesis drift", "concept")],
     [("Preregistration", "hypothesis drift", "REPLACES")],
     "what practice locks in the analysis before data arrives",
     "study plan commitment analytic lock data collection"),
    # --- 4 ---
    ("The scientific method cycles through observation, hypothesis, experiment, analysis, and revision.", "architecture", "knowledge", False,
     [("scientific method", "concept")],
     [],
     "what five stages make up the canonical inquiry cycle",
     "inquiry cycle hypothesise test refine loop"),
    # --- 5 ---
    ("P-hacking shows up when analysts try many tests and report only those reaching significance.", "problem", "knowledge", False,
     [("P-hacking", "finding")],
     [],
     "what analysis behaviour exploits flexible testing to manufacture significance",
     "selective reporting multiple testing significance inflation"),
    # --- 6 ---
    ("The ATLAS and CMS collaborations announced the Higgs boson discovery on 2012-07-04.", "milestone", "knowledge", False,
     [("ATLAS", "project"), ("CMS", "project"), ("Higgs boson", "concept"), ("2012-07-04", "date")],
     [],
     "when did the two LHC collaborations confirm the scalar boson",
     "collider announcement particle discovery summer date"),
    # --- 7 ---
    ("Prefers SciPy over MATLAB for new analyses; reproducibility is easier when collaborators share the stack.", "preference", "knowledge", False,
     [("SciPy", "tool"), ("MATLAB", "tool")],
     [("SciPy", "MATLAB", "PREFERS")],
     "which scientific stack wins for collaboration and repeatability",
     "open scientific library over proprietary numerical suite"),
    # --- 8 ---
    ("Godel's first incompleteness theorem implies any sufficiently expressive consistent system has undecidable statements.", "fact", "knowledge", False,
     [("Godel", "person"), ("incompleteness theorem", "theory")],
     [("incompleteness theorem", "Godel", "AUTHORED_BY")],
     "what does this logic result say about strong formal systems",
     "formal system expressive consistent undecidable limit"),
    # --- 9 ---
    ("Kuhn's Structure of Scientific Revolutions introduced paradigm shifts as the vocabulary for scientific change.", "reference", "knowledge", False,
     [("Kuhn", "person"), ("Structure of Scientific Revolutions", "publication"), ("paradigm shifts", "concept")],
     [("Structure of Scientific Revolutions", "Kuhn", "AUTHORED_BY")],
     "which book taught the field to talk about paradigm-level change",
     "philosophy of science classic paradigm shift vocabulary"),
    # --- 10. noise ---
    ("Let me look up the exact figures before we continue.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Single-blind peer review biases evaluations toward known author affiliations, studies show repeatedly.", "problem", "knowledge", False,
     [("Single-blind peer review", "method")],
     [],
     "what weakness of a common review method keeps surfacing in studies",
     "review anonymity partial affiliation bias repeat finding"),
    # --- 12 ---
    ("The Human Genome Project's first draft arrived on 2000-06-26 and the finished sequence in 2003.", "milestone", "knowledge", False,
     [("Human Genome Project", "project"), ("2000-06-26", "date"), ("2003", "date")],
     [],
     "when did the massive sequencing effort hit draft and finished phases",
     "reference genome draft finish timeline landmark"),
    # --- 13 ---
    ("For causal questions the lab picks randomisation over quasi-experiments whenever ethics and logistics allow.", "decision", "knowledge", False,
     [("randomisation", "method"), ("quasi-experiments", "method")],
     [("randomisation", "quasi-experiments", "REPLACES")],
     "which design choice takes priority for causal identification",
     "randomised assignment over natural comparison causal ID"),
    # --- 14 ---
    ("Avogadro's number, 6.022 times 10 to the 23, counts particles in one mole.", "fact", "knowledge", False,
     [("Avogadro's number", "concept"), ("mole", "concept")],
     [],
     "what constant links a mole to a particle count",
     "particles per mole chemistry constant numerical value"),
    # --- 15 ---
    ("Institutional review boards sign off on protocols before participant recruitment can begin.", "architecture", "knowledge", False,
     [("Institutional review boards", "organization")],
     [],
     "which body approves a study before participants are approached",
     "ethics committee protocol clearance recruitment gate"),
    # --- 16 ---
    ("Nature papers follow a strict structured-abstract format of up to 200 words with a dedicated significance line.", "reference", "knowledge", False,
     [("Nature", "publication"), ("structured-abstract", "concept")],
     [],
     "what summary format does the flagship journal enforce",
     "flagship weekly journal abstract length significance line"),
    # --- 17 ---
    ("Researcher degrees of freedom inflate false-positive rates because tiny analysis choices compound invisibly.", "problem", "knowledge", False,
     [("Researcher degrees of freedom", "finding")],
     [],
     "why do small analytic choices balloon into false positives",
     "flexible analysis pipeline silent choice inflation"),
    # --- 18 ---
    ("The GLP-1 receptor-agonist class cleared pivotal phase 3 obesity endpoints in 2021 with the STEP trials.", "milestone", "knowledge", False,
     [("GLP-1 receptor-agonist", "concept"), ("STEP trials", "project"), ("2021", "date")],
     [],
     "which drug class hit late-stage obesity endpoints and in which trials",
     "weight loss trial programme late stage endpoint year"),
    # --- 19 ---
    ("Double-blind single-arm studies improve on open-label designs for subjective endpoint bias control.", "decision", "knowledge", False,
     [("Double-blind", "method"), ("open-label", "method")],
     [("Double-blind", "open-label", "IMPROVES_ON")],
     "which blinding upgrade reduces subjective endpoint bias",
     "blinded participant and evaluator subjective outcome control"),
    # --- 20 ---
    ("The Ebbinghaus forgetting curve quantifies how unreinforced memory fades roughly exponentially over hours.", "fact", "knowledge", False,
     [("Ebbinghaus forgetting curve", "finding")],
     [],
     "what early empirical curve describes hourly memory decay",
     "memory decay function nineteenth century psychology result"),
    # --- 21 ---
    ("NIH grant reviews run through study sections; primary reviewers score and lead discussion during panel.", "architecture", "knowledge", False,
     [("NIH", "organization"), ("study sections", "concept")],
     [],
     "how are US federal biomedical grants actually scored",
     "federal biomedical grant panel primary reviewer discussion"),
    # --- 22 ---
    ("The Cochrane Handbook's chapter 10 covers analysing dichotomous outcomes across included trials.", "reference", "knowledge", False,
     [("Cochrane Handbook", "publication"), ("dichotomous outcomes", "concept")],
     [],
     "which guide documents the analysis of binary outcomes across trials",
     "systematic review guide binary outcome chapter location"),
    # --- 23 ---
    ("WEIRD-sample bias describes the over-reliance on Western, educated, industrialised populations in psychology.", "problem", "knowledge", False,
     [("WEIRD-sample bias", "finding")],
     [],
     "what bias captures overuse of one population slice in psychology",
     "limited demographic convenience sample generalisation risk"),
    # --- 24 ---
    ("The first pulsar PSR B1919+21 was detected by Jocelyn Bell Burnell in 1967 during PhD radio sky surveys.", "milestone", "knowledge", False,
     [("PSR B1919+21", "finding"), ("Jocelyn Bell Burnell", "person"), ("1967", "date")],
     [],
     "who first spotted a pulsar and when",
     "rotating neutron star discoverer radio survey year"),
    # --- 25 ---
    ("Variational inference replaces MCMC when posteriors must be fast and approximate suffices for the decision.", "decision", "knowledge", False,
     [("Variational inference", "method"), ("MCMC", "method")],
     [("Variational inference", "MCMC", "REPLACES")],
     "which Bayesian approximation wins when speed matters more than exactness",
     "approximate posterior fast trade sampling replacement"),
    # --- 26 ---
    ("Prefers Zotero over Mendeley for reference management; group libraries sync without Elsevier's policy churn.", "preference", "knowledge", False,
     [("Zotero", "tool"), ("Mendeley", "tool")],
     [("Zotero", "Mendeley", "PREFERS")],
     "which reference manager wins for shared libraries",
     "citation manager pick group library vendor neutrality"),
    # --- 27 ---
    ("Thermodynamic arrow of time ties macroscopic time directionality to entropy growth, not fundamental laws.", "fact", "knowledge", False,
     [("Thermodynamic arrow of time", "concept"), ("entropy", "concept")],
     [],
     "what physical direction concept rests on entropy rather than equations",
     "time direction statistical origin macro-level asymmetry"),
    # --- 28 ---
    ("Clinical trials progress through phases 1, 2, 3, and sometimes 4 for post-approval safety surveillance.", "architecture", "knowledge", False,
     [("Clinical trials", "method")],
     [],
     "how are drug trials typically staged from first in human onward",
     "drug development stages safety efficacy post-marketing"),
    # --- 29 ---
    ("Flyvbjerg showed megaproject cost overruns are systematic rather than bad luck; optimism bias dominates.", "reference", "knowledge", False,
     [("Flyvbjerg", "person"), ("megaproject cost overruns", "finding"), ("optimism bias", "concept")],
     [],
     "whose research showed large projects overrun by pattern not by chance",
     "planner cost underestimation systematic pattern reference"),
    # --- 30 ---
    ("Measurement invariance must be checked before comparing latent scores across groups or time.", "problem", "knowledge", False,
     [("Measurement invariance", "method")],
     [],
     "what psychometric check precedes group or longitudinal comparisons",
     "latent score comparability invariance prerequisite check"),
    # --- 31 ---
    ("The ENCODE project's 2012 release annotated 80 percent of the human genome as biochemically functional.", "milestone", "knowledge", False,
     [("ENCODE project", "project"), ("2012", "date"), ("human genome", "concept")],
     [],
     "which release claimed broad biochemical function across the genome",
     "annotation consortium percentage claim genome release"),
    # --- 32 ---
    ("For small-sample inference the lab now prefers Bayesian estimation over null hypothesis testing.", "preference", "knowledge", False,
     [("Bayesian estimation", "method"), ("null hypothesis testing", "method")],
     [("Bayesian estimation", "null hypothesis testing", "PREFERS")],
     "which inference philosophy wins when sample sizes are tight",
     "posterior inference under limited data over dichotomous testing"),
    # --- 33 ---
    ("Prefers BibTeX for automated citation over hand-typed reference lists; the style files do the heavy lifting.", "preference", "knowledge", False,
     [("BibTeX", "tool"), ("hand-typed reference lists", "method")],
     [("BibTeX", "hand-typed reference lists", "PREFERS")],
     "what citation workflow wins over manual list keeping",
     "automated citation format style file reuse"),
    # --- 34. noise ---
    ("Give me one moment, I need to double-check the source.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Occam's razor says prefer the simpler hypothesis when competing explanations fit the data equally.", "fact", "knowledge", False,
     [("Occam's razor", "concept")],
     [],
     "which parsimony principle picks between equally-fitting explanations",
     "parsimony heuristic simpler model equal fit choice"),
    # --- 36 ---
    ("Systematic reviews run identification, screening, eligibility, and inclusion stages in PRISMA-compliant work.", "architecture", "knowledge", False,
     [("Systematic reviews", "method")],
     [],
     "what four stages structure a compliant synthesis of the literature",
     "screen eligibility include four-step evidence aggregation"),
    # --- 37 ---
    ("Popper's falsifiability criterion separates scientific claims from unfalsifiable ones in his 1959 Logic of Scientific Discovery.", "reference", "knowledge", False,
     [("Popper", "person"), ("falsifiability", "concept"), ("Logic of Scientific Discovery", "publication"), ("1959", "date")],
     [("Logic of Scientific Discovery", "Popper", "AUTHORED_BY")],
     "whose criterion draws the scientific boundary around testable claims",
     "demarcation criterion falsifiable author classic text"),
    # --- 38 ---
    ("Publication bias skews literature because null results reach print far less often than positive ones.", "problem", "knowledge", False,
     [("Publication bias", "finding")],
     [],
     "which bias filters the published record toward positive findings",
     "null result invisibility publishing skew positive preference"),
    # --- 39 ---
    ("JWST released its first full-colour images of deep field galaxies on 2022-07-11.", "milestone", "knowledge", False,
     [("JWST", "tool"), ("2022-07-11", "date")],
     [],
     "when did the space telescope unveil its first colour galaxy images",
     "infrared observatory first science release summer date"),
    # --- 40 ---
    ("Meta-regression usually replaces subgroup analysis when moderators are continuous variables in a review.", "decision", "knowledge", False,
     [("Meta-regression", "method"), ("subgroup analysis", "method")],
     [("Meta-regression", "subgroup analysis", "REPLACES")],
     "which moderator analysis wins when predictors are continuous",
     "continuous moderator regression over categorical split"),
    # --- 41 ---
    ("Zipf's law describes how the nth most frequent token in a corpus occurs with frequency proportional to 1/n.", "fact", "knowledge", False,
     [("Zipf's law", "finding")],
     [],
     "what empirical pattern links token rank to frequency in corpora",
     "frequency rank inverse law linguistic regularity"),
    # --- 42 ---
    ("ERC grants run a two-stage panel with a remote review pool feeding into a central panel interview.", "architecture", "knowledge", False,
     [("ERC", "organization")],
     [],
     "how does the European research council structure its grant review",
     "European council grant two-stage panel interview funnel"),
    # --- 43 ---
    ("NIH's open-access policy requires peer-reviewed manuscripts to land in PubMed Central within 12 months.", "reference", "knowledge", False,
     [("NIH", "organization"), ("PubMed Central", "publication")],
     [],
     "what open-access rule governs federally funded manuscripts",
     "federal biomedical grant deposit repository deadline"),
    # --- 44 ---
    ("Small-sample null hypothesis tests misbehave when distributional assumptions quietly fail at low n.", "problem", "knowledge", False,
     [("null hypothesis tests", "method")],
     [],
     "when do significance tests become unreliable with little data",
     "distribution assumption breakdown low sample inference"),
    # --- 45 ---
    ("Cryo-EM at 1.8 angstrom resolution on the ribosome was reported in 2023 by the Scheres group.", "milestone", "knowledge", False,
     [("Cryo-EM", "method"), ("ribosome", "concept"), ("Scheres", "person"), ("2023", "date")],
     [],
     "who hit sub-two-angstrom ribosome imaging and when",
     "imaging resolution ribosome breakthrough group year"),
    # --- 46 ---
    ("Multiple imputation for missing data replaces listwise deletion whenever the missingness mechanism is MAR or MCAR.", "decision", "knowledge", False,
     [("Multiple imputation", "method"), ("listwise deletion", "method"), ("MAR", "concept"), ("MCAR", "concept")],
     [("Multiple imputation", "listwise deletion", "REPLACES")],
     "which missing-data handler takes over when MAR or MCAR holds",
     "imputation swap complete-case deletion mechanism MAR"),
    # --- 47 ---
    ("Prefers Overleaf over local LaTeX for joint papers; the live sync avoids the merge-conflict dance.", "preference", "knowledge", False,
     [("Overleaf", "tool"), ("local LaTeX", "tool")],
     [("Overleaf", "local LaTeX", "PREFERS")],
     "which writing environment wins for co-authored papers",
     "cloud document typesetting collaboration synchronisation"),
    # --- 48 ---
    ("Shannon's entropy ties information content to the logarithm of probability, in bits when the base is two.", "fact", "knowledge", False,
     [("Shannon", "person"), ("entropy", "concept")],
     [("entropy", "Shannon", "AUTHORED_BY")],
     "who defined the bit-scale measure linking surprise to rare outcomes",
     "information theory founder log probability bit unit"),
    # --- 49 ---
    ("Triple-anonymised review hides authors, reviewers, and handling editors from each other across the cycle.", "architecture", "knowledge", False,
     [("Triple-anonymised review", "method")],
     [],
     "which review setup hides all three parties from each other",
     "fully hidden review cycle author reviewer editor opaque"),
    # --- 50 ---
    ("The OECD AI Principles, adopted in 2019, frame international guidance on trustworthy AI development.", "reference", "knowledge", False,
     [("OECD AI Principles", "publication"), ("2019", "date")],
     [],
     "which intergovernmental text sets out guidance for responsible AI",
     "intergovernmental AI framework trustworthy guidance year"),
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
