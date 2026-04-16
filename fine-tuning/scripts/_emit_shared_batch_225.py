"""One-off emitter for shared-base batch-225 — knowledge domain (statistics and causal inference: frequentist vs Bayesian, regression, GAM, Stan, PyMC, Pearl, Rubin, DAGs, IVs, propensity scores).

Writes 50 rows to data/v2/shared/batch_225.tmp.jsonl with ids shared-11201..11250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_225.tmp.jsonl"
ID_OFFSET = 11200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The analytics team standardised on Bayesian posterior summaries for all headline metrics; the frequentist NHST reports survived only as an appendix because p-values kept getting misread as the probability the null was true.", "decision", "knowledge", False,
     [("Bayesian", "theory"), ("NHST", "method"), ("p-values", "concept"), ("frequentist", "theory")],
     [("Bayesian", "NHST", "REPLACES")],
     "which inference paradigm took over the headline dashboards after p-value misreadings piled up",
     "bayesian frequentist nhst p value posterior headline metric appendix"),
    # --- 2 ---
    ("Confidence intervals flipped to credible intervals in the experiment write-up template; reviewers kept interpreting the 95% CI as a probability statement about the parameter, which is exactly what a credible interval actually is.", "decision", "knowledge", False,
     [("Confidence intervals", "concept"), ("credible intervals", "concept"), ("95% CI", "concept")],
     [("credible intervals", "Confidence intervals", "REPLACES")],
     "why did the experiment template swap confidence intervals for credible intervals",
     "confidence credible interval 95 ci probability parameter template"),
    # --- 3 ---
    ("The AB-test harness now reports a Welch t-test by default; the equal-variance Student's t-test was demoted because most real traffic splits have heteroskedastic variance across the arms.", "architecture", "knowledge", False,
     [("Welch t-test", "method"), ("Student's t-test", "method"), ("AB-test", "method")],
     [("Welch t-test", "Student's t-test", "REPLACES")],
     "which t-test variant became the default in the AB-test harness and why was the equal-variance form demoted",
     "welch student t test ab variance heteroskedastic default harness"),
    # --- 4 ---
    ("Categorical-outcome checks use Fisher's exact test when any expected cell count falls below five; the chi-squared test's large-sample approximation stopped being trustworthy on our low-traffic segment cuts.", "decision", "knowledge", False,
     [("Fisher's exact", "method"), ("chi-squared test", "method"), ("expected cell count", "concept")],
     [("Fisher's exact", "chi-squared test", "REPLACES")],
     "which categorical test replaces chi-squared on low-traffic segment cuts and what triggers the switch",
     "fisher exact chi squared expected cell count low traffic segment"),
    # --- 5 ---
    ("Non-parametric comparisons default to the Mann-Whitney U for two independent samples and the Wilcoxon signed-rank for paired samples; normal-theory tests kept failing the Shapiro-Wilk gate on skewed revenue data.", "architecture", "knowledge", False,
     [("Mann-Whitney U", "method"), ("Wilcoxon signed-rank", "method"), ("Shapiro-Wilk", "method"), ("Non-parametric", "concept")],
     [("Mann-Whitney U", "Shapiro-Wilk", "APPLIES_TO")],
     "which two non-parametric tests cover independent and paired samples when normality fails on revenue",
     "mann whitney u wilcoxon signed rank shapiro wilk skewed revenue"),
    # --- 6 ---
    ("Distribution-shape comparisons run a two-sample Kolmogorov-Smirnov against the production baseline; drift alerts fire when the KS statistic crosses 0.1 on the daily feature rollup.", "fact", "knowledge", False,
     [("Kolmogorov-Smirnov", "method"), ("KS statistic", "concept"), ("drift", "concept")],
     [("Kolmogorov-Smirnov", "drift", "APPLIES_TO")],
     "which test powers the distribution-drift alert and at what threshold does it fire",
     "kolmogorov smirnov ks statistic drift threshold feature rollup daily"),
    # --- 7 ---
    ("Churn model shipped as a logistic regression with elastic-net regularisation; the linear regression baseline kept producing out-of-range probabilities and the team wanted a proper Bernoulli link.", "decision", "knowledge", False,
     [("logistic regression", "method"), ("linear regression", "method"), ("elastic-net", "method"), ("Bernoulli link", "concept")],
     [("logistic regression", "linear regression", "REPLACES")],
     "which model replaced linear regression for churn and what link function motivated the switch",
     "logistic linear regression elastic net bernoulli link churn probability"),
    # --- 8 ---
    ("Support-ticket counts per hour are modelled with a Poisson regression; the overdispersion test flagged the raw counts so we eventually moved to a negative-binomial GLM for the longer forecasts.", "problem", "knowledge", False,
     [("Poisson regression", "method"), ("overdispersion", "concept"), ("negative-binomial", "method"), ("GLM", "method")],
     [("negative-binomial", "Poisson regression", "REPLACES")],
     "which overdispersion fix replaced Poisson for long-horizon ticket-count forecasts",
     "poisson negative binomial glm overdispersion ticket count forecast"),
    # --- 9 ---
    ("Random-effects models for the multi-site trial use lme4 in R for point estimates and rstanarm for full posteriors; mixing the two lets the team sanity-check REML against HMC on the same design.", "architecture", "knowledge", False,
     [("lme4", "library"), ("rstanarm", "library"), ("REML", "method"), ("HMC", "algorithm"), ("Random-effects models", "method")],
     [("lme4", "rstanarm", "RELATED_TO")],
     "which two R packages pair up on the multi-site trial and what cross-check do they enable",
     "lme4 rstanarm reml hmc mixed model multi site trial cross check"),
    # --- 10. noise ---
    ("The office plant on the window ledge finally bloomed after three months of nobody remembering to water it on schedule.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Exposure-response curves are fit with GAM splines via mgcv in R; the polynomial regression kept overshooting at the tails and Simon Wood's thin-plate splines gave monotone behaviour with fewer knots.", "decision", "knowledge", False,
     [("GAM", "method"), ("mgcv", "library"), ("Simon Wood", "person"), ("thin-plate splines", "method"), ("polynomial regression", "method")],
     [("GAM", "polynomial regression", "REPLACES"), ("mgcv", "Simon Wood", "AUTHORED_BY")],
     "which spline approach from mgcv replaced polynomial regression on exposure-response curves",
     "gam mgcv simon wood thin plate spline polynomial exposure response"),
    # --- 12 ---
    ("Hierarchical models now compile through Stan via the brms front-end; the earlier JAGS workflow was retired because HMC mixed faster on the funnel-shaped random-effects posteriors.", "decision", "knowledge", False,
     [("Stan", "library"), ("brms", "library"), ("JAGS", "library"), ("HMC", "algorithm"), ("Hierarchical models", "method")],
     [("Stan", "JAGS", "REPLACES"), ("brms", "Stan", "USES")],
     "which Stan front-end replaced JAGS for hierarchical fits and which sampler property drove the move",
     "stan brms jags hmc hierarchical funnel posterior sampler replace"),
    # --- 13 ---
    ("Production forecasting jobs run PyMC on a GPU pool; NumPyro is held in reserve for the vectorised posterior predictive because JAX vmap lets us push batch sizes an order of magnitude higher.", "architecture", "knowledge", False,
     [("PyMC", "library"), ("NumPyro", "library"), ("JAX", "library"), ("vmap", "method"), ("posterior predictive", "concept")],
     [("NumPyro", "JAX", "USES")],
     "which Python Bayesian stack runs the forecasts and which backup handles vectorised posterior predictives",
     "pymc numpyro jax vmap posterior predictive gpu batch forecast"),
    # --- 14 ---
    ("Upgraded the R stack from base-R pipelines to the tidyverse: dplyr handles the wrangling, ggplot2 draws the diagnostics, and readr replaces read.csv for everything touching quoted strings.", "milestone", "knowledge", False,
     [("tidyverse", "library"), ("dplyr", "library"), ("ggplot2", "library"), ("readr", "library"), ("base-R", "library")],
     [("tidyverse", "base-R", "REPLACES"), ("tidyverse", "dplyr", "HAS_PART")],
     "which tidyverse packages took over wrangling, plotting, and CSV reads in the R stack",
     "tidyverse dplyr ggplot2 readr base r wrangle diagnostic quote"),
    # --- 15 ---
    ("For the largest event-log aggregations the team keeps data.table around; dplyr's copy-on-modify semantics blew past memory limits on the hundred-million-row join that data.table handles in-place.", "preference", "knowledge", False,
     [("data.table", "library"), ("dplyr", "library"), ("copy-on-modify", "concept")],
     [("data.table", "dplyr", "REPLACES")],
     "why does the team keep data.table for the largest joins instead of standardising on dplyr",
     "data table dplyr copy on modify event log join memory limit"),
    # --- 16 ---
    ("The Bayesian reading list for new hires is Gelman's BDA3 followed by McElreath's Statistical Rethinking; the pairing gives a rigorous reference and a code-forward tutorial on the same ideas.", "reference", "knowledge", False,
     [("BDA3", "publication"), ("Gelman", "person"), ("Statistical Rethinking", "publication"), ("McElreath", "person")],
     [("BDA3", "Gelman", "AUTHORED_BY"), ("Statistical Rethinking", "McElreath", "AUTHORED_BY")],
     "which two Bayesian texts make the new-hire reading list and what does each one contribute",
     "bda3 gelman statistical rethinking mcelreath bayesian reading new hire"),
    # --- 17 ---
    ("Causal-inference onboarding hands out Judea Pearl's Causality and The Book of Why; the first builds the do-calculus machinery and the second pitches counterfactual reasoning to readers with no graph background.", "reference", "knowledge", False,
     [("Causality", "publication"), ("The Book of Why", "publication"), ("Judea Pearl", "person"), ("do-calculus", "method"), ("counterfactual", "concept")],
     [("Causality", "Judea Pearl", "AUTHORED_BY"), ("The Book of Why", "Judea Pearl", "AUTHORED_BY")],
     "which two Pearl books anchor causal-inference onboarding and what is the division of labour between them",
     "pearl causality book why do calculus counterfactual onboarding"),
    # --- 18 ---
    ("Experimentation stack formalised on the Rubin causal model: every A/B analysis declares units, treatments, and potential outcomes in the pre-registration so SUTVA violations surface before data collection.", "architecture", "knowledge", False,
     [("Rubin causal model", "theory"), ("potential outcomes", "concept"), ("SUTVA", "concept"), ("pre-registration", "method")],
     [("Rubin causal model", "potential outcomes", "HAS_PART")],
     "which causal framework underpins the pre-registration template and what design flaw does it catch early",
     "rubin causal model potential outcome sutva pre registration ab"),
    # --- 19 ---
    ("DAGs are drawn in dagitty before any regression spec is written; the graph-driven adjustment set replaces the old practice of dumping every covariate into the model and hoping for the best.", "decision", "knowledge", False,
     [("DAGs", "method"), ("dagitty", "tool"), ("adjustment set", "concept"), ("covariate", "concept")],
     [("DAGs", "adjustment set", "HAS_PART")],
     "which graph tool informs the adjustment set and what kitchen-sink practice did it retire",
     "dag dagitty adjustment set covariate regression kitchen sink"),
    # --- 20 ---
    ("The pricing team adopted an instrumental variables estimator for the demand model; OLS was biased by endogeneity between price and unobserved quality and the IV gives a consistent elasticity.", "decision", "knowledge", False,
     [("instrumental variables", "method"), ("OLS", "method"), ("endogeneity", "concept"), ("elasticity", "concept")],
     [("instrumental variables", "OLS", "REPLACES")],
     "which estimator replaced OLS on the demand model and what bias source forced the change",
     "instrumental variable ols endogeneity elasticity demand pricing bias"),
    # --- 21 ---
    ("Observational-study readouts use propensity score matching before outcome regression; the raw comparison had a three-standard-deviation imbalance on tenure that the matched sample brings under 0.1.", "architecture", "knowledge", False,
     [("propensity score", "method"), ("matching", "method"), ("imbalance", "concept"), ("Observational-study", "method")],
     [("propensity score", "imbalance", "FIXES")],
     "which pre-processing step precedes outcome regression on observational studies and what does it fix",
     "propensity score matching imbalance tenure observational outcome"),
    # --- 22 ---
    ("Donald Rubin's 1974 potential-outcomes paper is required reading before anyone touches the causal stack; the quote about fundamental problem of causal inference lives pinned in the team wiki.", "reference", "knowledge", False,
     [("Donald Rubin", "person"), ("potential-outcomes", "concept"), ("fundamental problem of causal inference", "claim")],
     [("potential-outcomes", "Donald Rubin", "AUTHORED_BY")],
     "which Rubin paper is required pre-reading for the causal stack and what claim gets pinned in the wiki",
     "donald rubin potential outcome fundamental problem causal wiki 1974"),
    # --- 23 ---
    ("Natural-experiment playbook is Angrist and Pischke's Mostly Harmless Econometrics; the team leans on Joshua Angrist's LATE interpretation whenever the IV is weak or the compliance is partial.", "reference", "knowledge", False,
     [("Joshua Angrist", "person"), ("Mostly Harmless Econometrics", "publication"), ("LATE", "concept"), ("compliance", "concept")],
     [("Mostly Harmless Econometrics", "Joshua Angrist", "AUTHORED_BY"), ("LATE", "Joshua Angrist", "AUTHORED_BY")],
     "which Angrist reference and which estimand anchor the natural-experiment playbook",
     "angrist mostly harmless econometrics late compliance iv weak natural"),
    # --- 24 ---
    ("Heterogeneous treatment effects run through Susan Athey's causal forest implementation in grf; the old subgroup-by-subgroup t-tests inflated the family-wise error rate past the pre-registered threshold.", "decision", "knowledge", False,
     [("Susan Athey", "person"), ("causal forest", "method"), ("grf", "library"), ("subgroup t-tests", "method"), ("family-wise error rate", "concept")],
     [("causal forest", "subgroup t-tests", "REPLACES"), ("causal forest", "Susan Athey", "AUTHORED_BY")],
     "which Athey-led method replaced subgroup t-tests for heterogeneous treatment effects",
     "susan athey causal forest grf subgroup t test family wise error"),
    # --- 25 ---
    ("Retired the one-tailed p-value from the lift report; the Bayesian posterior probability that lift exceeds zero is what stakeholders actually asked for and it maps cleanly onto the decision rule.", "decision", "knowledge", False,
     [("one-tailed p-value", "concept"), ("posterior probability", "concept"), ("lift", "concept"), ("decision rule", "concept")],
     [("posterior probability", "one-tailed p-value", "REPLACES")],
     "which Bayesian summary replaced the one-tailed p-value on lift reports and why",
     "one tailed p value posterior probability lift decision rule stakeholder"),
    # --- 26 ---
    ("Stan model diagnostics are gated on R-hat below 1.01 and effective sample size above 400 per parameter; anything worse rejects the run from the experiment registry before a lift number is ever quoted.", "architecture", "knowledge", False,
     [("R-hat", "concept"), ("effective sample size", "concept"), ("Stan", "library"), ("experiment registry", "method")],
     [("R-hat", "Stan", "APPLIES_TO")],
     "which Stan convergence thresholds gate a run from entering the experiment registry",
     "stan r hat ess effective sample size experiment registry gate"),
    # --- 27 ---
    ("Weakly-informative priors on log-odds coefficients default to Normal(0, 1.5); Gelman's recommendation of flat priors kept producing non-identifiable posteriors on the small-sample auth-flow experiments.", "decision", "knowledge", False,
     [("Weakly-informative priors", "concept"), ("Normal(0, 1.5)", "concept"), ("Gelman", "person"), ("flat priors", "concept"), ("log-odds", "concept")],
     [("Weakly-informative priors", "flat priors", "REPLACES")],
     "which prior choice replaced flat priors on log-odds coefficients for small-sample experiments",
     "weakly informative prior normal 1 5 gelman flat log odds identify"),
    # --- 28 ---
    ("Quasi-experimental analyses lean on difference-in-differences when parallel trends hold; the synthetic control method is the fallback when the treated unit has no obvious comparable control group.", "architecture", "knowledge", False,
     [("difference-in-differences", "method"), ("parallel trends", "concept"), ("synthetic control", "method"), ("Quasi-experimental", "method")],
     [("synthetic control", "difference-in-differences", "REPLACES")],
     "which quasi-experimental method steps in when parallel trends fail for difference-in-differences",
     "difference in differences parallel trends synthetic control quasi"),
    # --- 29 ---
    ("Bootstrap confidence intervals use the BCa variant for skewed statistics; the percentile bootstrap undercovered by roughly five points on the median-absolute-deviation stat we report on latency tails.", "problem", "knowledge", False,
     [("BCa", "method"), ("percentile bootstrap", "method"), ("Bootstrap", "method"), ("median-absolute-deviation", "concept")],
     [("BCa", "percentile bootstrap", "REPLACES")],
     "which bootstrap variant replaced the percentile method on latency-tail stats and what coverage gap forced it",
     "bca percentile bootstrap coverage median absolute deviation latency"),
    # --- 30 ---
    ("The multi-arm bandit allocator uses Thompson sampling against a Beta-Bernoulli posterior; the epsilon-greedy baseline kept wasting traffic on arms the posterior had already ruled out.", "decision", "knowledge", False,
     [("Thompson sampling", "algorithm"), ("Beta-Bernoulli", "method"), ("epsilon-greedy", "algorithm"), ("multi-arm bandit", "method")],
     [("Thompson sampling", "epsilon-greedy", "REPLACES")],
     "which bandit allocator replaced epsilon-greedy and what Bayesian model sits underneath",
     "thompson sampling beta bernoulli epsilon greedy bandit allocator"),
    # --- 31 ---
    ("Causal-discovery experiments run PC and FCI from causal-learn; the output DAGs get validated against do-calculus identifiability rules before any backdoor adjustment goes into a regression.", "fact", "knowledge", False,
     [("PC", "algorithm"), ("FCI", "algorithm"), ("causal-learn", "library"), ("do-calculus", "method"), ("backdoor adjustment", "method")],
     [("causal-learn", "PC", "HAS_PART"), ("do-calculus", "backdoor adjustment", "HAS_PART")],
     "which causal-discovery algorithms run before a backdoor adjustment and what validates their DAGs",
     "pc fci causal learn do calculus backdoor adjustment discovery dag"),
    # --- 32 ---
    ("Shifted the survival analysis from Kaplan-Meier curves alone to Cox proportional hazards with time-varying covariates; the step-function visualisation stays but hazard ratios now carry the headline.", "milestone", "knowledge", False,
     [("Kaplan-Meier", "method"), ("Cox proportional hazards", "method"), ("time-varying covariates", "concept"), ("hazard ratio", "concept")],
     [("Cox proportional hazards", "Kaplan-Meier", "REPLACES")],
     "which survival model now carries the headline instead of Kaplan-Meier and what covariate feature was added",
     "kaplan meier cox proportional hazard time varying covariate survival"),
    # --- 33 ---
    ("Team preference for plotting went from base R graphics to ggplot2; the grammar-of-graphics layering matches how analysts verbally describe a chart and the faceting saves hours of manual panel layout.", "preference", "knowledge", False,
     [("base R graphics", "library"), ("ggplot2", "library"), ("grammar-of-graphics", "theory"), ("faceting", "method")],
     [("ggplot2", "base R graphics", "REPLACES")],
     "why did analyst plotting standardise on ggplot2 over base R graphics",
     "base r graphics ggplot2 grammar graphics facet layering analyst"),
    # --- 34 ---
    ("Two-stage least squares runs via the AER package for the canonical homework example and via fixest for the production pipeline; fixest's high-dimensional fixed effects are what pushed it into production.", "architecture", "knowledge", False,
     [("Two-stage least squares", "method"), ("AER", "library"), ("fixest", "library"), ("fixed effects", "concept")],
     [("fixest", "AER", "REPLACES")],
     "which R package handles production two-stage least squares and why over the textbook package",
     "two stage least squares aer fixest fixed effect high dimension"),
    # --- 35 ---
    ("Hit the 10k-experiment milestone on the Bayesian workbench; decision-theory-based stopping rules now close about forty percent of experiments early versus the old fixed-horizon NHST design.", "milestone", "knowledge", False,
     [("10k-experiment", "finding"), ("Bayesian workbench", "method"), ("decision-theory", "theory"), ("NHST", "method"), ("fixed-horizon", "concept")],
     [("decision-theory", "NHST", "REPLACES")],
     "which stopping-rule approach closes experiments early on the Bayesian workbench versus fixed-horizon NHST",
     "10k experiment bayesian workbench decision theory stopping nhst"),
    # --- 36 ---
    ("Heteroskedasticity-robust standard errors via HC3 are the default in the linear-model summaries; the classical OLS standard errors only show up when a homoskedasticity test explicitly passes.", "decision", "knowledge", False,
     [("HC3", "method"), ("Heteroskedasticity-robust", "method"), ("OLS", "method"), ("linear-model", "method")],
     [("HC3", "OLS", "REPLACES")],
     "which standard-error default replaced classical OLS in linear-model summaries",
     "hc3 heteroskedasticity robust ols linear model standard error default"),
    # --- 37 ---
    ("Shipped a reproducible R environment via renv and targets; the old source-it-and-pray workflow lost a quarter of analyses to package-version drift between the analyst's laptop and the CI runner.", "milestone", "knowledge", False,
     [("renv", "library"), ("targets", "library"), ("reproducible", "concept"), ("CI runner", "concept")],
     [("renv", "targets", "RELATED_TO")],
     "which two R packages now back the reproducible analysis environment and what drift problem did they fix",
     "renv targets reproducible r environment ci runner drift package"),
    # --- 38 ---
    ("Gelman himself wrote the folk theorem of statistical computing and the team playbook cites it: when sampling is slow or divergent, the model is usually mis-specified, so the fix starts with the prior and likelihood rather than the sampler settings.", "reference", "knowledge", False,
     [("folk theorem of statistical computing", "claim"), ("Gelman", "person"), ("mis-specified", "concept"), ("prior", "concept"), ("likelihood", "concept")],
     [("folk theorem of statistical computing", "Gelman", "AUTHORED_BY")],
     "which heuristic about slow samplers from Gelman does the team playbook cite and where does it redirect debugging",
     "gelman folk theorem statistical computing sampler prior likelihood"),
    # --- 39 ---
    ("Mediation analysis uses Imai's sensitivity framework rather than Baron-Kenny; unmeasured-confounding bounds on the indirect effect make the conclusions robust without a heroic no-confounding assumption.", "decision", "knowledge", False,
     [("Imai", "person"), ("Baron-Kenny", "method"), ("Mediation analysis", "method"), ("unmeasured-confounding", "concept"), ("indirect effect", "concept")],
     [("Imai", "Baron-Kenny", "REPLACES")],
     "which mediation framework replaced Baron-Kenny and what robustness feature motivated it",
     "imai sensitivity baron kenny mediation indirect unmeasured confounding"),
    # --- 40 ---
    ("The observational-study stack added doubly-robust estimation via targeted maximum likelihood; if either the outcome model or the propensity model is correct the estimate stays consistent, which saved us on the last subscription-churn readout.", "architecture", "knowledge", False,
     [("doubly-robust", "method"), ("targeted maximum likelihood", "method"), ("outcome model", "concept"), ("propensity model", "concept")],
     [("doubly-robust", "targeted maximum likelihood", "HAS_PART")],
     "which estimation approach stays consistent if either the outcome or propensity model is right",
     "doubly robust targeted maximum likelihood outcome propensity model"),
    # --- 41 ---
    ("Shrinkage priors on the industry-level fixed effects use horseshoe instead of ridge; sparsity in the true effect vector matches the horseshoe's heavy tails better than the Gaussian ridge penalty.", "decision", "knowledge", False,
     [("horseshoe", "method"), ("ridge", "method"), ("Shrinkage priors", "concept"), ("sparsity", "concept")],
     [("horseshoe", "ridge", "REPLACES")],
     "which shrinkage prior replaced ridge on the industry-level fixed effects and why",
     "horseshoe ridge shrinkage prior sparsity industry fixed effect"),
    # --- 42 ---
    ("Posterior predictive checks are a required gate before any Bayesian model ships; if the observed test statistic lies outside the 50% posterior predictive interval the model goes back for structural changes.", "architecture", "knowledge", False,
     [("Posterior predictive checks", "method"), ("Bayesian model", "concept"), ("test statistic", "concept"), ("posterior predictive interval", "concept")],
     [("Posterior predictive checks", "Bayesian model", "APPLIES_TO")],
     "which gate blocks a Bayesian model from shipping and what posterior-predictive threshold sends it back",
     "posterior predictive check bayesian model ship 50 interval"),
    # --- 43. noise ---
    ("Someone left a half-eaten sandwich under the third-floor stairwell for the entire long weekend and the smell lingered until Wednesday.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Regression-discontinuity studies fit local-linear models with a triangular kernel at the cutoff; the global polynomial fit from the pilot produced boundary artefacts that inflated the treatment effect by a factor of two.", "problem", "knowledge", False,
     [("Regression-discontinuity", "method"), ("local-linear", "method"), ("triangular kernel", "method"), ("global polynomial", "method")],
     [("local-linear", "global polynomial", "REPLACES")],
     "which regression-discontinuity fit replaced the global polynomial and what artefact drove the change",
     "regression discontinuity local linear triangular kernel global polynomial"),
    # --- 45 ---
    ("Power analyses default to simulation rather than closed-form formulas; a quick PyMC prior-predictive loop handles designs like cluster-randomised trials where the classical power equation stops applying.", "preference", "knowledge", False,
     [("Power analyses", "method"), ("simulation", "method"), ("PyMC", "library"), ("cluster-randomised", "method"), ("closed-form", "concept")],
     [("simulation", "closed-form", "REPLACES")],
     "which power-analysis approach replaced closed-form formulas and which design class forced the move",
     "power analysis simulation pymc cluster randomised closed form"),
    # --- 46 ---
    ("Causal inference pipelines call out Hernan and Robins' What If as the operational textbook; the treatment of time-varying confounding with g-methods is what the team reaches for on longitudinal data.", "reference", "knowledge", False,
     [("Hernan", "person"), ("Robins", "person"), ("What If", "publication"), ("g-methods", "method"), ("time-varying confounding", "concept")],
     [("What If", "Hernan", "AUTHORED_BY"), ("What If", "Robins", "AUTHORED_BY")],
     "which textbook and method family handle time-varying confounding on longitudinal causal work",
     "hernan robins what if g method time varying confounding textbook"),
    # --- 47 ---
    ("Hit the milestone where every production decision model publishes a DAG alongside its regression spec; the causal review now runs before the code review and has caught four backdoor-path errors this quarter.", "milestone", "knowledge", False,
     [("production decision model", "concept"), ("DAG", "method"), ("causal review", "method"), ("backdoor-path", "concept")],
     [("DAG", "backdoor-path", "APPLIES_TO")],
     "which review step now precedes code review on decision models and how many backdoor errors did it catch",
     "production decision dag causal review backdoor path code review"),
    # --- 48 ---
    ("Front-door adjustment came out of the archive for the recommendations readout; the treatment-outcome pair had an unobserved confounder but a clean mediator let us recover the causal effect anyway.", "problem", "knowledge", False,
     [("Front-door adjustment", "method"), ("unobserved confounder", "concept"), ("mediator", "concept"), ("causal effect", "concept")],
     [("Front-door adjustment", "unobserved confounder", "FIXES")],
     "which Pearl adjustment salvaged the recommendations readout when the confounder was unobserved",
     "front door adjustment unobserved confounder mediator causal effect"),
    # --- 49 ---
    ("The team formally prefers simulation-based calibration over eyeballing trace plots; SBC catches a class of miscoded likelihoods that visual diagnostics miss until the posterior is already wrong.", "preference", "knowledge", False,
     [("simulation-based calibration", "method"), ("trace plots", "method"), ("miscoded likelihoods", "concept"), ("SBC", "method")],
     [("simulation-based calibration", "trace plots", "REPLACES")],
     "which diagnostic replaced trace-plot eyeballing for Bayesian models and what bug class does it catch",
     "simulation based calibration sbc trace plot miscoded likelihood"),
    # --- 50 ---
    ("Landed hierarchical partial pooling on the country-level conversion model; fully-pooled and no-pooled baselines both underperformed out-of-sample and the partial-pooling posterior actually matches the McElreath tutorial figures.", "milestone", "knowledge", False,
     [("partial pooling", "method"), ("fully-pooled", "method"), ("no-pooled", "method"), ("conversion model", "concept"), ("McElreath", "person")],
     [("partial pooling", "fully-pooled", "IMPROVES_ON"), ("partial pooling", "no-pooled", "IMPROVES_ON")],
     "which pooling strategy won on the country-level conversion model and whose tutorial does the posterior match",
     "partial pooling fully no pooled country conversion mcelreath"),
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
