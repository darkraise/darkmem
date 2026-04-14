"""One-off emitter for shared-base batch-017 — knowledge domain (social sciences slice).

Writes 50 rows to data/v2/shared/batch_017.tmp.jsonl with ids shared-00801..00850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_017.tmp.jsonl"
ID_OFFSET = 800

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Simon's bounded rationality frames decision making under cognitive and informational limits rather than perfect optimisation.", "fact", "knowledge", False,
     [("Simon", "person"), ("bounded rationality", "theory"), ("decision making", "concept")],
     [("bounded rationality", "Simon", "AUTHORED_BY")],
     "which theory explains choice under cognitive and informational constraints",
     "limited cognition satisficing decision framework origin"),
    # --- 2 ---
    ("Tversky and Kahneman's prospect theory shows losses loom roughly twice as large as equivalent gains in risky choice.", "fact", "knowledge", False,
     [("Tversky", "person"), ("Kahneman", "person"), ("prospect theory", "theory"), ("risky choice", "concept")],
     [("prospect theory", "Kahneman", "AUTHORED_BY"), ("prospect theory", "Tversky", "AUTHORED_BY")],
     "which framework quantifies asymmetric weighting of gains and losses",
     "loss aversion risky choice behavioural theory coefficient"),
    # --- 3 ---
    ("Prospect theory improves on expected utility theory by capturing reference dependence and probability weighting.", "decision", "knowledge", False,
     [("Prospect theory", "theory"), ("expected utility theory", "theory")],
     [("Prospect theory", "expected utility theory", "IMPROVES_ON")],
     "which behavioural model upgrades the classical utility baseline for risk",
     "reference dependence probability weight upgrade baseline"),
    # --- 4 ---
    ("Banerjee and Duflo's development work pushed randomised controlled trials to the centre of poverty economics.", "reference", "knowledge", False,
     [("Banerjee", "person"), ("Duflo", "person"), ("randomised controlled trials", "method"), ("poverty economics", "field")],
     [],
     "whose programme mainstreamed field experiments in development economics",
     "development economics RCT mainstream authors method"),
    # --- 5 ---
    ("Card and Krueger's 1994 New Jersey fast-food study found minimum wage rises did not cut employment as classical theory predicted.", "fact", "knowledge", False,
     [("Card", "person"), ("Krueger", "person"), ("1994", "date"), ("New Jersey", "place"), ("minimum wage", "concept")],
     [],
     "which study challenged textbook predictions about minimum wage and jobs",
     "minimum wage employment natural experiment labour finding"),
    # --- 6 ---
    ("Self-determination theory posits autonomy, competence, and relatedness as the three core psychological needs.", "architecture", "knowledge", False,
     [("Self-determination theory", "theory"), ("autonomy", "concept"), ("competence", "concept"), ("relatedness", "concept")],
     [],
     "which motivation framework identifies three basic psychological needs",
     "intrinsic motivation three needs psychology framework"),
    # --- 7 ---
    ("Bowlby's attachment theory grounds adult relational patterns in infant caregiver interactions and internal working models.", "reference", "knowledge", False,
     [("Bowlby", "person"), ("attachment theory", "theory"), ("internal working models", "concept")],
     [("attachment theory", "Bowlby", "AUTHORED_BY")],
     "whose developmental theory links infant bonds to adult relationships",
     "attachment foundation developmental psychology author framework"),
    # --- 8 ---
    ("Festinger's cognitive dissonance explains attitude change as tension reduction between conflicting beliefs or behaviours.", "fact", "knowledge", False,
     [("Festinger", "person"), ("cognitive dissonance", "theory"), ("attitude change", "concept")],
     [("cognitive dissonance", "Festinger", "AUTHORED_BY")],
     "which theory attributes attitude shifts to internal inconsistency pressure",
     "dissonance reduction belief behaviour conflict mechanism"),
    # --- 9 ---
    ("The Stanford marshmallow experiment's predictive power eroded once later replications controlled for family background.", "problem", "knowledge", False,
     [("Stanford marshmallow experiment", "finding"), ("replications", "method"), ("family background", "concept")],
     [],
     "which famous self-control study weakened after controlling for background",
     "delay gratification famous study replication erosion control"),
    # --- 10. noise ---
    ("Hold on, I want to pull the exact effect size before I commit to that claim.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Dweck's growth mindset literature shows classroom effects that shrink substantially in large-scale replications and meta-analyses.", "problem", "knowledge", False,
     [("Dweck", "person"), ("growth mindset", "theory"), ("meta-analyses", "method")],
     [],
     "whose educational theory shows shrinking effects in larger replications",
     "mindset intervention effect shrinkage synthesis evidence"),
    # --- 12 ---
    ("Behavioural insights units prefer field trials over lab-only evidence, with the explicit goal of honest policy impact.", "preference", "knowledge", False,
     [("Behavioural insights units", "organization"), ("field trials", "method"), ("lab-only evidence", "method"), ("honest policy impact", "goal")],
     [("field trials", "lab-only evidence", "PREFERS")],
     "which evidence source wins for nudge units deploying at scale",
     "policy nudge unit field evidence ecological validity"),
    # --- 13 ---
    ("The UK Behavioural Insights Team was spun out of the Cabinet Office on 2014-02-05 as a social-purpose joint venture.", "milestone", "knowledge", False,
     [("UK Behavioural Insights Team", "organization"), ("Cabinet Office", "organization"), ("2014-02-05", "date")],
     [],
     "when did the UK nudge unit leave government as a social-purpose venture",
     "nudge unit spinout government venture date"),
    # --- 14 ---
    ("Kahneman's Thinking Fast and Slow popularised dual-process reasoning for a broad non-technical audience.", "reference", "knowledge", False,
     [("Kahneman", "person"), ("Thinking Fast and Slow", "publication"), ("dual-process reasoning", "concept")],
     [("Thinking Fast and Slow", "Kahneman", "AUTHORED_BY")],
     "which trade book brought two-system reasoning to general readers",
     "popular behavioural economics book dual system reasoning"),
    # --- 15 ---
    ("Game theory supplies the formal backbone for auction design, matching markets, and industrial organisation analysis.", "fact", "knowledge", False,
     [("Game theory", "field"), ("auction design", "concept"), ("matching markets", "concept"), ("industrial organisation", "field")],
     [],
     "which mathematical toolkit underpins auctions and market design",
     "strategic interaction formalism market design applications"),
    # --- 16 ---
    ("Roth and Shapley shared the 2012 Nobel Prize ceremony for matching theory applied to kidney exchanges and school assignment.", "milestone", "knowledge", False,
     [("Roth", "person"), ("Shapley", "person"), ("2012 Nobel Prize ceremony", "event"), ("matching theory", "theory"), ("kidney exchanges", "concept")],
     [],
     "which economists won for matching markets work in the kidney exchange era",
     "matching theory Nobel applied market designer authors"),
    # --- 17 ---
    ("Rational choice theory treats individuals as utility maximisers operating on stable, consistent preferences.", "architecture", "knowledge", False,
     [("Rational choice theory", "theory"), ("utility maximisers", "concept")],
     [],
     "which framework models agents as consistent utility maximisers",
     "classical rational agent consistent preference framework"),
    # --- 18 ---
    ("Heuristics and biases replaced the rational agent default in much of descriptive decision research during the 1980s.", "decision", "knowledge", False,
     [("Heuristics and biases", "theory"), ("rational agent", "concept")],
     [("Heuristics and biases", "rational agent", "REPLACES")],
     "which descriptive tradition displaced rational agent models in decision research",
     "descriptive decision tradition eighties heuristics bias shift"),
    # --- 19 ---
    ("Longitudinal cohort studies trace the same panel over years; the British 1970 Birth Cohort is a canonical example.", "fact", "knowledge", False,
     [("Longitudinal cohort studies", "method"), ("British 1970 Birth Cohort", "project")],
     [],
     "which design follows one panel for years with a canonical British example",
     "longitudinal panel cohort famous British birth year"),
    # --- 20 ---
    ("The Framingham Heart Study has tracked cardiovascular risk since 1948 across three generations of residents.", "milestone", "knowledge", False,
     [("Framingham Heart Study", "project"), ("1948", "date"), ("cardiovascular risk", "concept")],
     [],
     "which long-running cohort seeded much modern cardiovascular epidemiology",
     "cardiovascular cohort town multi-generation longitudinal start"),
    # --- 21 ---
    ("Randomised field experiments usually improve on observational surveys when causal identification is the research goal.", "decision", "knowledge", False,
     [("Randomised field experiments", "method"), ("observational surveys", "method")],
     [("Randomised field experiments", "observational surveys", "IMPROVES_ON")],
     "which evidence form beats surveys when causation matters most",
     "field experiment over survey causal design upgrade"),
    # --- 22 ---
    ("Ecological validity critiques warn that lab findings often fail to generalise to messy real-world settings.", "problem", "knowledge", False,
     [("Ecological validity", "concept"), ("lab findings", "concept")],
     [],
     "which critique flags lab-to-field generalisation failures",
     "lab generalisation field setting validity critique"),
    # --- 23 ---
    ("Pre-registered replication reports now anchor credibility checks across flagship psychology journals.", "architecture", "knowledge", False,
     [("Pre-registered replication reports", "method"), ("psychology journals", "organization")],
     [],
     "which publishing format has become the credibility anchor in psychology",
     "pre-registered report replication credibility journal norm"),
    # --- 24 ---
    ("Registered Reports build on preregistration by adding stage-one peer review of design before data collection.", "decision", "knowledge", False,
     [("Registered Reports", "method"), ("preregistration", "method"), ("stage-one peer review", "concept")],
     [("Registered Reports", "preregistration", "BUILDS_ON")],
     "which review format layers pre-data peer review on top of plan locking",
     "two-stage review design acceptance before data extension"),
    # --- 25 ---
    ("Meta-science's credibility revolution treats open data and open code as first-class requirements, not nice-to-haves.", "fact", "knowledge", False,
     [("Meta-science", "field"), ("credibility revolution", "concept"), ("open data", "concept"), ("open code", "concept")],
     [],
     "which reform movement promoted open data and code to required status",
     "meta-science reform openness first-class norm requirement"),
    # --- 26 ---
    ("The Many Labs 2 replication project reported that thirteen of twenty-eight classic effects replicated at full sample.", "fact", "knowledge", False,
     [("Many Labs 2", "project"), ("classic effects", "concept")],
     [],
     "which multi-lab replication reported roughly half of effects holding up",
     "replication consortium classic effects half hold fraction"),
    # --- 27 ---
    ("Acemoglu and Robinson's Why Nations Fail argues extractive institutions explain persistent development gaps.", "reference", "knowledge", False,
     [("Acemoglu", "person"), ("Robinson", "person"), ("Why Nations Fail", "publication"), ("extractive institutions", "concept")],
     [("Why Nations Fail", "Acemoglu", "AUTHORED_BY"), ("Why Nations Fail", "Robinson", "AUTHORED_BY")],
     "which book attributes long-run development gaps to institutional extraction",
     "institutions development popular economics book authors"),
    # --- 28 ---
    ("Development economists often prefer difference-in-differences to simple before-after comparisons when a control panel exists.", "preference", "knowledge", False,
     [("Development economists", "organization"), ("difference-in-differences", "method"), ("before-after comparisons", "method")],
     [("difference-in-differences", "before-after comparisons", "PREFERS")],
     "which quasi-experimental design is favoured when a control panel is available",
     "dif-in-dif over simple pre post trend control design"),
    # --- 29 ---
    ("The RAND Health Insurance Experiment randomised cost sharing from 1971 to 1982 and found modest utilisation sensitivity.", "milestone", "knowledge", False,
     [("RAND Health Insurance Experiment", "project"), ("1971", "date"), ("1982", "date"), ("cost sharing", "concept")],
     [],
     "which classic insurance RCT ran through the seventies into the eighties",
     "insurance experiment cost sharing utilisation decade long"),
    # --- 30 ---
    ("School voucher and charter-school evaluations yield mixed effects; heterogeneity across cities dominates the literature.", "problem", "knowledge", False,
     [("School voucher", "concept"), ("charter-school evaluations", "method")],
     [],
     "which education-policy evidence base is dominated by city-level heterogeneity",
     "school choice voucher charter mixed evidence heterogeneity"),
    # --- 31 ---
    ("The Tennessee STAR class-size experiment randomised students in the late 1980s and found durable small-class benefits.", "fact", "knowledge", False,
     [("Tennessee STAR", "project"), ("class-size experiment", "method"), ("1980s", "date")],
     [],
     "which classic class-size RCT produced durable small-class gains",
     "class size experiment state durable gain decade"),
    # --- 32 ---
    ("Piketty's Capital in the Twenty-First Century framed rising inequality as driven by r greater than g over long horizons.", "reference", "knowledge", False,
     [("Piketty", "person"), ("Capital in the Twenty-First Century", "publication"), ("inequality", "concept")],
     [("Capital in the Twenty-First Century", "Piketty", "AUTHORED_BY")],
     "which book popularised the r greater than g framing of inequality",
     "inequality long horizon popular economics book author"),
    # --- 33 ---
    ("Milgram's obedience findings remain contested; reanalysis shows variation across versions that the original paper downplayed.", "problem", "knowledge", False,
     [("Milgram", "person"), ("obedience findings", "finding")],
     [],
     "which classic social-psych result has been reopened by version-level reanalysis",
     "obedience study version reanalysis contested classic"),
    # --- 34. noise ---
    ("Give me a second, I need to look up the effect size before I say anything specific.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Putnam's Bowling Alone documents declining civic participation across postwar America as a social capital erosion story.", "reference", "knowledge", False,
     [("Putnam", "person"), ("Bowling Alone", "publication"), ("social capital", "concept")],
     [("Bowling Alone", "Putnam", "AUTHORED_BY")],
     "which book frames falling civic engagement as social capital loss",
     "civic engagement decline postwar social capital book"),
    # --- 36 ---
    ("Instrumental variables often replace ordinary least squares when unobserved confounding threatens coefficient interpretation.", "decision", "knowledge", False,
     [("Instrumental variables", "method"), ("ordinary least squares", "method"), ("unobserved confounding", "concept")],
     [("Instrumental variables", "ordinary least squares", "REPLACES")],
     "which estimator takes over when unmeasured confounders threaten OLS",
     "instrumental variable over OLS confounder threat swap"),
    # --- 37 ---
    ("Regression discontinuity designs exploit sharp cutoff rules to approximate randomisation around the threshold.", "architecture", "knowledge", False,
     [("Regression discontinuity designs", "method"), ("cutoff rules", "concept")],
     [],
     "which design uses sharp cutoffs to mimic randomisation locally",
     "cutoff threshold local random quasi-experiment approach"),
    # --- 38 ---
    ("Synthetic control methods build on difference-in-differences by constructing a data-driven weighted comparison unit.", "decision", "knowledge", False,
     [("Synthetic control methods", "method"), ("difference-in-differences", "method")],
     [("Synthetic control methods", "difference-in-differences", "BUILDS_ON")],
     "which case-study estimator extends dif-in-dif with a weighted control",
     "single unit policy synthetic weighted control extension"),
    # --- 39 ---
    ("Abadie's 2003 synthetic control paper applied the method to the Basque region terrorism case and anchored adoption.", "milestone", "knowledge", False,
     [("Abadie", "person"), ("2003", "date"), ("synthetic control", "method"), ("Basque region", "place")],
     [("synthetic control", "Abadie", "AUTHORED_BY")],
     "which early synthetic control paper used a Spanish regional case to launch the method",
     "synthetic control foundational paper regional case year"),
    # --- 40 ---
    ("Nash equilibrium is a strategy profile where no player gains by unilateral deviation, a claim routinely used to predict stable play.", "fact", "knowledge", False,
     [("Nash equilibrium", "concept"), ("strategy profile", "concept"), ("predict stable play", "claim")],
     [],
     "what solution concept requires no profitable unilateral deviation",
     "game theory stable strategy profile deviation condition"),
    # --- 41 ---
    ("Political scientists running Stan models prefer multilevel regression with poststratification to raw survey weighting for subnational estimates.", "preference", "knowledge", False,
     [("Political scientists", "organization"), ("Stan", "tool"), ("multilevel regression with poststratification", "method"), ("raw survey weighting", "method")],
     [("multilevel regression with poststratification", "raw survey weighting", "PREFERS")],
     "which survey estimator beats raw weighting for small-area politics",
     "small area political survey estimator weighting upgrade"),
    # --- 42 ---
    ("The WHO Global Burden of Disease project standardises disability-adjusted life years across countries and causes.", "reference", "knowledge", False,
     [("WHO", "organization"), ("Global Burden of Disease", "project"), ("disability-adjusted life years", "concept")],
     [],
     "which worldwide initiative harmonises disease burden measurement using DALYs",
     "global health metric standardised DALY cross country project"),
    # --- 43 ---
    ("Public health surveillance relies on notifiable disease reporting pipelines that feed national and regional dashboards.", "architecture", "knowledge", False,
     [("Public health surveillance", "method"), ("notifiable disease reporting", "method")],
     [],
     "how do health agencies feed national dashboards from the clinic level",
     "notifiable reporting pipeline dashboard surveillance backbone"),
    # --- 44 ---
    ("Vaccination coverage metrics typically report doses administered per eligible population; herd effects need higher thresholds for measles.", "fact", "knowledge", False,
     [("Vaccination coverage", "concept"), ("herd effects", "concept"), ("measles", "concept")],
     [],
     "which disease has a notably high herd-immunity threshold in coverage metrics",
     "coverage ratio herd threshold measles immunity metric"),
    # --- 45 ---
    ("The Grameen Bank microfinance model scaled group-lending repayment in Bangladesh from 1983 and drew close academic study.", "milestone", "knowledge", False,
     [("Grameen Bank", "organization"), ("microfinance", "concept"), ("Bangladesh", "place"), ("1983", "date"), ("group-lending", "method")],
     [],
     "which microfinance institution anchored the group-lending literature from 1983",
     "microfinance group lending Bangladesh institution start year"),
    # --- 46 ---
    ("Microfinance RCTs like Banerjee et al. 2015 reported modest business effects and little measurable poverty reduction.", "fact", "knowledge", False,
     [("Microfinance RCTs", "method"), ("Banerjee", "person"), ("2015", "date"), ("poverty reduction", "concept")],
     [],
     "which mid-2010s synthesis showed microfinance only modestly helping businesses",
     "microfinance experimental synthesis modest effect year"),
    # --- 47 ---
    ("Robust standard errors replace homoskedastic ones when residual variance plainly depends on covariates in the fit.", "decision", "knowledge", False,
     [("Robust standard errors", "method"), ("homoskedastic", "concept"), ("residual variance", "concept")],
     [("Robust standard errors", "homoskedastic", "REPLACES")],
     "which correction should the analyst use once heteroskedasticity is visible",
     "heteroskedasticity robust standard error replacement swap"),
    # --- 48 ---
    ("Duncan's sociological mobility tables formalised intergenerational status transitions long before modern panel data arrived.", "fact", "knowledge", False,
     [("Duncan", "person"), ("mobility tables", "method"), ("intergenerational status", "concept")],
     [("mobility tables", "Duncan", "AUTHORED_BY")],
     "whose classical sociological tool formalised intergenerational status flow",
     "mobility table classical sociology intergenerational author"),
    # --- 49 ---
    ("The Programme for International Student Assessment reports country-level reading, maths, and science scores every three years.", "reference", "knowledge", False,
     [("Programme for International Student Assessment", "project"), ("reading", "concept"), ("maths", "concept"), ("science", "concept")],
     [],
     "which triennial assessment publishes cross-country student competence scores",
     "international student assessment cross country triennial subjects"),
    # --- 50 ---
    ("Development field studies prefer cluster randomisation over pure individual assignment when interventions spill across households.", "preference", "knowledge", False,
     [("Development field studies", "method"), ("cluster randomisation", "method"), ("individual assignment", "method")],
     [("cluster randomisation", "individual assignment", "PREFERS")],
     "which randomisation design wins when household-level spillovers are real",
     "cluster design over individual randomisation spillover control"),
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
