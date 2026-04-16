"""One-off emitter for shared-base batch-226 — knowledge domain (game theory and mechanism design).

Writes 50 rows to data/v2/shared/batch_226.tmp.jsonl with ids shared-11251..11300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_226.tmp.jsonl"
ID_OFFSET = 11250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1: milestone ---
    ("von Neumann and Morgenstern published Theory of Games and Economic Behavior in 1944, founding game theory as a distinct field and cementing expected utility as the decision-theoretic backbone.", "milestone", "knowledge", False,
     [("von Neumann", "person"), ("Morgenstern", "person"), ("Theory of Games and Economic Behavior", "publication"), ("game theory", "field"), ("expected utility", "concept")],
     [("Theory of Games and Economic Behavior", "von Neumann", "AUTHORED_BY"), ("Theory of Games and Economic Behavior", "Morgenstern", "AUTHORED_BY"), ("game theory", "Theory of Games and Economic Behavior", "BUILDS_ON")],
     "which 1944 book by von Neumann and Morgenstern founded the field and what decision framework did it anchor",
     "von neumann morgenstern 1944 theory games economic behavior expected utility"),
    # --- 2: decision ---
    ("The discipline treats John Nash's 1950 proof that every finite game with mixed strategies admits at least one Nash equilibrium as the default solution concept of non-cooperative game theory.", "decision", "knowledge", False,
     [("John Nash", "person"), ("Nash equilibrium", "concept"), ("mixed strategies", "concept"), ("non-cooperative game theory", "field")],
     [("Nash equilibrium", "John Nash", "AUTHORED_BY"), ("Nash equilibrium", "non-cooperative game theory", "APPLIES_TO")],
     "which 1950 existence theorem by John Nash underlies the central solution concept of non-cooperative games",
     "nash equilibrium 1950 mixed strategy finite game existence non cooperative"),
    # --- 3: fact ---
    ("A Nash equilibrium is a strategy profile from which no player can improve by unilaterally deviating, provided every other player sticks with their own strategy.", "fact", "knowledge", False,
     [("Nash equilibrium", "concept"), ("strategy profile", "concept"), ("unilaterally deviating", "concept")],
     [("Nash equilibrium", "strategy profile", "IS_A")],
     "how does a Nash equilibrium characterise a strategy profile in terms of unilateral deviations",
     "nash equilibrium strategy profile unilateral deviation definition"),
    # --- 4: preference ---
    ("Treat Nash equilibrium as necessary but not sufficient for predicting behaviour: multiple equilibria, refinements like subgame-perfection, and off-equilibrium beliefs all constrain what actually gets played.", "preference", "knowledge", False,
     [("Nash equilibrium", "concept"), ("subgame-perfection", "concept"), ("off-equilibrium beliefs", "concept")],
     [("subgame-perfection", "Nash equilibrium", "IMPROVES_ON")],
     "why should Nash equilibrium be treated as necessary but not sufficient when predicting play in real games",
     "nash equilibrium refinement subgame perfection off equilibrium belief"),
    # --- 5: milestone ---
    ("Reinhard Selten introduced subgame-perfect equilibrium in 1965 to rule out Nash equilibria sustained by non-credible threats in extensive-form games.", "milestone", "knowledge", False,
     [("Reinhard Selten", "person"), ("subgame-perfect equilibrium", "concept"), ("non-credible threats", "concept"), ("extensive-form games", "concept")],
     [("subgame-perfect equilibrium", "Reinhard Selten", "AUTHORED_BY"), ("subgame-perfect equilibrium", "non-credible threats", "FIXES")],
     "which refinement did Selten propose in 1965 and which class of equilibria did it eliminate",
     "selten subgame perfect equilibrium non credible threat extensive form 1965"),
    # --- 6: fact ---
    ("Backward induction solves finite extensive-form games of perfect information by working from terminal nodes upward, producing the unique subgame-perfect equilibrium when payoffs are generic.", "fact", "knowledge", False,
     [("Backward induction", "method"), ("extensive-form games", "concept"), ("perfect information", "concept"), ("subgame-perfect equilibrium", "concept")],
     [("Backward induction", "subgame-perfect equilibrium", "APPLIES_TO")],
     "how does backward induction produce the unique subgame-perfect equilibrium of a finite perfect-information game",
     "backward induction extensive form perfect information terminal node subgame"),
    # --- 7: architecture ---
    ("John Harsanyi showed how to convert games of incomplete information into Bayesian games with a prior over types, giving a tractable equilibrium concept where players best-respond conditional on type.", "architecture", "knowledge", False,
     [("John Harsanyi", "person"), ("Bayesian games", "concept"), ("incomplete information", "concept"), ("prior over types", "concept")],
     [("Bayesian games", "John Harsanyi", "AUTHORED_BY"), ("Bayesian games", "incomplete information", "APPLIES_TO")],
     "which transformation by Harsanyi made games of incomplete information tractable and what construct does it introduce",
     "harsanyi bayesian game incomplete information prior type best respond"),
    # --- 8: decision ---
    ("The committee chose Selten, Nash, and Harsanyi for the 1994 Nobel Prize in Economics, citing foundational work on non-cooperative game theory and Bayesian equilibrium analysis.", "decision", "knowledge", False,
     [("Selten", "person"), ("Nash", "person"), ("Harsanyi", "person"), ("non-cooperative game theory", "field")],
     [],
     "which three game theorists shared the 1994 Nobel and for which overlapping contributions",
     "selten nash harsanyi 1994 nobel non cooperative bayesian"),
    # --- 9: fact ---
    ("The Shapley value assigns each participant in a cooperative game the average of marginal contributions taken over all possible join orders of the coalition.", "fact", "knowledge", False,
     [("Shapley value", "concept"), ("cooperative game", "concept"), ("marginal contributions", "concept"), ("coalition", "concept")],
     [("Shapley value", "cooperative game", "APPLIES_TO")],
     "what formula underlies fair payoff allocation in coalition games under the Shapley concept",
     "shapley value cooperative game marginal contribution coalition order"),
    # --- 10: noise ---
    ("The faculty coffee machine in the economics building has been broken since October and people keep leaving passive-aggressive post-its on the hopper.", "fact", "noise", True, [], [], None, None),
    # --- 11: decision ---
    ("The Nobel committee awarded Lloyd Shapley and Alvin Roth jointly in 2012 for the theory of stable allocations and the practice of market design, building on the Gale-Shapley deferred acceptance algorithm.", "decision", "knowledge", False,
     [("Lloyd Shapley", "person"), ("Alvin Roth", "person"), ("deferred acceptance", "method"), ("market design", "field")],
     [("Alvin Roth", "market design", "APPLIES_TO"), ("deferred acceptance", "Lloyd Shapley", "AUTHORED_BY")],
     "which pair shared the 2012 Nobel for stable allocations and which matching algorithm grounded the prize",
     "shapley roth 2012 nobel stable allocation market design deferred acceptance"),
    # --- 12: architecture ---
    ("Alvin Roth redesigned the National Resident Matching Program and the New England kidney exchange on top of deferred-acceptance mechanisms, turning theoretical stability into deployed infrastructure.", "architecture", "knowledge", False,
     [("Alvin Roth", "person"), ("National Resident Matching Program", "method"), ("kidney exchange", "method"), ("deferred-acceptance", "method")],
     [("National Resident Matching Program", "Alvin Roth", "AUTHORED_BY"), ("kidney exchange", "deferred-acceptance", "BUILDS_ON")],
     "which real-world matching markets did Alvin Roth redesign using deferred-acceptance mechanisms",
     "roth resident match kidney exchange deferred acceptance market design deploy"),
    # --- 13: decision ---
    ("Theorists cite Kenneth Arrow's 1951 impossibility theorem as the reason to reject any claim that a rank-order voting rule can simultaneously satisfy unrestricted domain, Pareto efficiency, independence of irrelevant alternatives, and non-dictatorship.", "decision", "knowledge", False,
     [("Kenneth Arrow", "person"), ("impossibility theorem", "theory"), ("independence of irrelevant alternatives", "concept"), ("non-dictatorship", "concept")],
     [("impossibility theorem", "Kenneth Arrow", "AUTHORED_BY")],
     "which four axioms does Arrow's theorem prove cannot be jointly satisfied by any rank-order rule",
     "arrow impossibility theorem 1951 unrestricted domain pareto iia dictator"),
    # --- 14: decision ---
    ("Reject any paper claiming a voting rule is simultaneously fair, efficient, and non-manipulable on all preference profiles, citing Arrow's impossibility theorem as the basis for dismissal.", "decision", "knowledge", False,
     [("Arrow's impossibility theorem", "theory"), ("voting rule", "concept"), ("preference profiles", "concept")],
     [("Arrow's impossibility theorem", "voting rule", "APPLIES_TO")],
     "when should Arrow's impossibility theorem be invoked as a sanity check on claims about voting rules",
     "arrow impossibility voting rule fair efficient manipulable preference"),
    # --- 15: decision ---
    ("When predicting one-shot play, favour a dominant strategy whenever one exists because it yields at least as high a payoff as any alternative regardless of what the opponents do.", "decision", "knowledge", False,
     [("dominant strategy", "concept"), ("one-shot play", "concept")],
     [],
     "why favour a dominant strategy when predicting one-shot play and what payoff guarantee does it carry",
     "dominant strategy payoff regardless opponent one shot play prefer"),
    # --- 16: fact ---
    ("In a mixed strategy a player randomises over pure actions with specific probabilities; equilibria in mixed strategies exist for every finite game by Nash's theorem even when no pure-strategy equilibrium does.", "fact", "knowledge", False,
     [("mixed strategy", "concept"), ("pure actions", "concept"), ("Nash's theorem", "theory")],
     [("mixed strategy", "Nash's theorem", "APPLIES_TO")],
     "how does a mixed strategy randomise over pure actions and what guarantee does Nash's theorem give for existence",
     "mixed strategy pure action randomise probability nash existence finite"),
    # --- 17: preference ---
    ("Prefer dominant-strategy incentive compatibility over Bayesian incentive compatibility when designing mechanisms meant to survive misspecified priors; the stronger solution concept is more robust in practice.", "preference", "knowledge", False,
     [("dominant-strategy incentive compatibility", "concept"), ("Bayesian incentive compatibility", "concept"), ("misspecified priors", "concept")],
     [("dominant-strategy incentive compatibility", "Bayesian incentive compatibility", "IMPROVES_ON")],
     "why prefer dominant-strategy incentive compatibility over Bayesian when priors might be misspecified",
     "dominant strategy incentive compatibility bayesian misspecified prior robust"),
    # --- 18: decision ---
    ("Adopt von Neumann's minimax theorem as the default solver for any two-player zero-sum game, since it reduces the strategic problem to a linear program over mixed strategies.", "decision", "knowledge", False,
     [("zero-sum game", "concept"), ("minimax theorem", "theory"), ("von Neumann", "person"), ("mixed strategies", "concept")],
     [("minimax theorem", "von Neumann", "AUTHORED_BY"), ("minimax theorem", "zero-sum game", "APPLIES_TO")],
     "which theorem solves the two-player zero-sum case and what computational form does the solution take",
     "zero sum game payoff minimax theorem two player von neumann linear"),
    # --- 19: fact ---
    ("The Prisoner's Dilemma has mutual defection as its unique Nash equilibrium even though mutual cooperation Pareto dominates it, making it the canonical example of individually rational but collectively suboptimal outcomes.", "fact", "knowledge", False,
     [("Prisoner's Dilemma", "concept"), ("Nash equilibrium", "concept"), ("Pareto dominates", "concept")],
     [("Prisoner's Dilemma", "Nash equilibrium", "APPLIES_TO")],
     "why is mutual defection the unique Nash equilibrium of the Prisoner's Dilemma despite cooperation being Pareto-dominant",
     "prisoner dilemma mutual defection nash cooperation pareto dominant"),
    # --- 20: decision ---
    ("Classify the Stag Hunt game under coordination rather than defection problems, since it has two pure-strategy Nash equilibria, stag-stag and hare-hare, whose selection is the central strategic question.", "decision", "knowledge", False,
     [("Stag Hunt", "concept"), ("pure-strategy Nash equilibria", "concept"), ("coordination", "concept")],
     [("Stag Hunt", "coordination", "IS_A")],
     "which two pure-strategy equilibria does the Stag Hunt admit and what strategic question does that pose",
     "stag hunt coordination pure strategy nash equilibrium hare"),
    # --- 21: decision ---
    ("Model brinksmanship scenarios with the Chicken game rather than the Prisoner's Dilemma: Chicken admits two asymmetric pure-strategy equilibria in which one player swerves while the other stays, plus a mixed equilibrium whose crash probability is positive.", "decision", "knowledge", False,
     [("Chicken", "concept"), ("Prisoner's Dilemma", "concept"), ("asymmetric pure-strategy equilibria", "concept"), ("mixed equilibrium", "concept")],
     [("Chicken", "Prisoner's Dilemma", "IMPROVES_ON")],
     "why model brinksmanship with Chicken over Prisoner's Dilemma and which equilibria does Chicken admit",
     "chicken game asymmetric swerve stay mixed equilibrium crash probability"),
    # --- 22: fact ---
    ("Battle of the Sexes is a coordination game with two Pareto-ranked pure-strategy equilibria, one favouring each player, plus a symmetric mixed equilibrium nobody actually prefers.", "fact", "knowledge", False,
     [("Battle of the Sexes", "concept"), ("coordination game", "concept"), ("Pareto-ranked", "concept"), ("symmetric mixed equilibrium", "concept")],
     [("Battle of the Sexes", "coordination game", "IS_A")],
     "which equilibrium structure characterises Battle of the Sexes and why is the mixed equilibrium unpopular",
     "battle sexes coordination pareto rank mixed equilibrium pure asymmetric"),
    # --- 23: architecture ---
    ("Repeated games open the door to cooperation by letting players condition today's action on past history, which trigger strategies exploit to sustain payoffs above any stage-game Nash equilibrium.", "architecture", "knowledge", False,
     [("Repeated games", "concept"), ("trigger strategies", "method"), ("stage-game Nash equilibrium", "concept")],
     [("trigger strategies", "Repeated games", "APPLIES_TO")],
     "how do repeated games sustain cooperation via trigger strategies above the stage-game Nash benchmark",
     "repeat game trigger strategy history cooperation stage nash equilibrium"),
    # --- 24: reference ---
    ("Reference the folk theorem whenever justifying cooperation in infinitely repeated games: any feasible payoff profile dominating the minmax can be sustained as a subgame-perfect equilibrium when players are patient enough.", "reference", "knowledge", False,
     [("folk theorem", "theory"), ("minmax", "concept"), ("subgame-perfect equilibrium", "concept"), ("infinitely repeated games", "concept")],
     [("folk theorem", "infinitely repeated games", "APPLIES_TO")],
     "which class of payoff profiles does the folk theorem sustain as subgame-perfect equilibria under patience",
     "folk theorem minmax feasible subgame perfect infinite repeat patience"),
    # --- 25: decision ---
    ("Robert Axelrod's round-robin tournaments in the late 1970s settled on tit-for-tat, submitted by Anatol Rapoport, as the winning strategy against a field of more elaborate entries in the iterated Prisoner's Dilemma.", "decision", "knowledge", False,
     [("Robert Axelrod", "person"), ("tit-for-tat", "method"), ("Anatol Rapoport", "person"), ("iterated Prisoner's Dilemma", "concept")],
     [("tit-for-tat", "Anatol Rapoport", "AUTHORED_BY"), ("Robert Axelrod", "iterated Prisoner's Dilemma", "APPLIES_TO")],
     "which strategy won Axelrod's late-1970s tournaments and who submitted it",
     "axelrod tournament tit for tat rapoport iterated prisoner dilemma"),
    # --- 26: fact ---
    ("Tit-for-tat cooperates on the first move then copies the opponent's last action, earning the labels nice, retaliatory, forgiving, and clear that Axelrod credited with its robustness.", "fact", "knowledge", False,
     [("Tit-for-tat", "method"), ("Axelrod", "person")],
     [],
     "which four properties did Axelrod credit for tit-for-tat's robustness and how does the rule actually behave",
     "tit for tat cooperate copy opponent nice retaliatory forgiving clear"),
    # --- 27: decision ---
    ("John Maynard Smith imported game theory into biology by defining an evolutionarily stable strategy as one that cannot be invaded by a rare mutant strategy playing against the incumbent population.", "decision", "knowledge", False,
     [("John Maynard Smith", "person"), ("evolutionarily stable strategy", "concept"), ("game theory", "field")],
     [("evolutionarily stable strategy", "John Maynard Smith", "AUTHORED_BY"), ("evolutionarily stable strategy", "game theory", "BUILDS_ON")],
     "which biological solution concept did Maynard Smith introduce and how does invasion resistance define it",
     "maynard smith ess evolutionary stable strategy invasion mutant biology"),
    # --- 28: architecture ---
    ("Evolutionary game theory studies dynamics of strategy frequencies under replicator equations, with ESS characterising the rest points that survive small-perturbation invasions in infinite populations.", "architecture", "knowledge", False,
     [("Evolutionary game theory", "field"), ("replicator equations", "method"), ("ESS", "concept"), ("infinite populations", "concept")],
     [("ESS", "Evolutionary game theory", "APPLIES_TO")],
     "how do replicator equations and ESS fit together in evolutionary game theory under small perturbations",
     "evolutionary game theory replicator equation ess rest point perturbation"),
    # --- 29: architecture ---
    ("A first-price sealed-bid auction awards the item to the highest bid at that bid's price; bidders shade below their valuation, and optimal shading depends on the prior over rivals' types.", "architecture", "knowledge", False,
     [("first-price sealed-bid auction", "method"), ("shading", "concept"), ("prior over rivals' types", "concept")],
     [],
     "how does a first-price sealed-bid auction price the winning bid and why do bidders shade below their valuations",
     "first price sealed bid auction shade valuation prior rival type"),
    # --- 30: preference ---
    ("Prefer a second-price sealed-bid auction over first-price when simplicity of bidder advice matters, because truthful bidding is a weakly dominant strategy for every independent-private-values bidder.", "preference", "knowledge", False,
     [("second-price sealed-bid auction", "method"), ("first-price", "method"), ("truthful bidding", "concept"), ("independent-private-values", "concept")],
     [("second-price sealed-bid auction", "first-price", "PREFERS")],
     "why prefer a second-price auction over first-price when bidder advice simplicity matters",
     "second price sealed bid truthful weakly dominant independent private value"),
    # --- 31: milestone ---
    ("William Vickrey introduced the second-price auction in 1961 and shared the 1996 Nobel Prize for foundational work on incentives under asymmetric information.", "milestone", "knowledge", False,
     [("William Vickrey", "person"), ("second-price auction", "method"), ("asymmetric information", "concept")],
     [("second-price auction", "William Vickrey", "AUTHORED_BY")],
     "which auction format did Vickrey introduce in 1961 and what did his 1996 Nobel cite",
     "vickrey 1961 second price auction 1996 nobel asymmetric information"),
    # --- 32: architecture ---
    ("The Vickrey-Clarke-Groves mechanism generalises the second-price rule to multi-item allocations, charging each winner the externality they impose on other participants and preserving dominant-strategy truthfulness.", "architecture", "knowledge", False,
     [("Vickrey-Clarke-Groves", "method"), ("second-price rule", "method"), ("multi-item allocations", "concept"), ("externality", "concept")],
     [("Vickrey-Clarke-Groves", "second-price rule", "IMPROVES_ON")],
     "how does the VCG mechanism generalise the second-price idea while preserving dominant-strategy truthfulness",
     "vcg mechanism second price multi item externality dominant truthful"),
    # --- 33: problem ---
    ("VCG payments can fail budget balance and individual rationality jointly in combinatorial settings, which is a standard gotcha when recommending it as a real-world mechanism.", "problem", "knowledge", False,
     [("VCG", "method"), ("budget balance", "concept"), ("individual rationality", "concept"), ("combinatorial settings", "concept")],
     [("VCG", "combinatorial settings", "APPLIES_TO")],
     "which two desiderata can VCG fail jointly in combinatorial settings and why does that caution real deployments",
     "vcg budget balance individual rationality combinatorial gotcha"),
    # --- 34: reference ---
    ("Cite the revelation principle whenever justifying a focus on direct truthful mechanisms: any social choice function implementable by some mechanism can also be implemented by a direct truthful mechanism, which is why theorists restrict attention there.", "reference", "knowledge", False,
     [("revelation principle", "theory"), ("social choice function", "concept"), ("direct truthful mechanism", "concept")],
     [("revelation principle", "direct truthful mechanism", "APPLIES_TO")],
     "which theorem lets mechanism designers restrict attention to direct truthful mechanisms without loss of generality",
     "revelation principle social choice direct truthful mechanism design"),
    # --- 35: milestone ---
    ("Roger Myerson derived the optimal auction for a single indivisible good with independent types in 1981, introducing the virtual valuation and ironing procedure that dominate modern auction theory.", "milestone", "knowledge", False,
     [("Roger Myerson", "person"), ("optimal auction", "method"), ("virtual valuation", "concept"), ("ironing procedure", "method")],
     [("optimal auction", "Roger Myerson", "AUTHORED_BY"), ("virtual valuation", "Roger Myerson", "AUTHORED_BY")],
     "which 1981 Myerson result gave the optimal single-item auction and which technical tools did it introduce",
     "myerson 1981 optimal auction virtual valuation ironing independent type"),
    # --- 36: reference ---
    ("Cite the Myerson-Satterthwaite impossibility as the reason no mechanism can be simultaneously incentive-compatible, individually rational, budget-balanced, and ex-post efficient for bilateral trade with two-sided private information.", "reference", "knowledge", False,
     [("Myerson-Satterthwaite", "theory"), ("incentive-compatible", "concept"), ("individually rational", "concept"), ("budget-balanced", "concept"), ("bilateral trade", "concept")],
     [("Myerson-Satterthwaite", "bilateral trade", "APPLIES_TO")],
     "which four properties did Myerson and Satterthwaite prove jointly impossible for bilateral trade with two-sided private info",
     "myerson satterthwaite 1983 bilateral trade incentive individual budget efficient"),
    # --- 37: reference ---
    ("Cite the revenue equivalence theorem when comparing auction formats: under independent private values and symmetric risk-neutral bidders, any auction allocating to the highest type and giving zero rent to the lowest type produces the same expected revenue.", "reference", "knowledge", False,
     [("revenue equivalence", "theory"), ("independent private values", "concept"), ("symmetric risk-neutral bidders", "concept"), ("expected revenue", "concept")],
     [("revenue equivalence", "independent private values", "APPLIES_TO")],
     "which assumptions drive the revenue equivalence theorem and what revenue conclusion do they deliver",
     "revenue equivalence independent private value symmetric risk neutral auction"),
    # --- 38: problem ---
    ("The two-sided private information problem in bilateral bargaining means every Bayesian game with a commonly known prior still leaves room for ex-post inefficient trade outcomes even at equilibrium.", "problem", "knowledge", False,
     [("two-sided private information", "concept"), ("bilateral bargaining", "concept"), ("Bayesian game", "concept"), ("commonly known prior", "concept")],
     [("two-sided private information", "bilateral bargaining", "APPLIES_TO")],
     "which information structure problem prevents efficient trade even in Bayesian equilibrium bilateral bargaining",
     "two sided private information bilateral bargain bayesian inefficient trade"),
    # --- 39: architecture ---
    ("Nash proposed the axiomatic bargaining solution in 1950: the unique point maximising the product of utility gains over the disagreement point satisfies Pareto efficiency, symmetry, invariance, and independence of irrelevant alternatives.", "architecture", "knowledge", False,
     [("Nash", "person"), ("axiomatic bargaining solution", "method"), ("disagreement point", "concept"), ("Pareto efficiency", "concept")],
     [("axiomatic bargaining solution", "Nash", "AUTHORED_BY")],
     "which four axioms characterise the Nash bargaining solution and what does it maximise",
     "nash bargain axiom product utility gain disagreement pareto symmetry"),
    # --- 40: architecture ---
    ("Signaling models formalise how informed parties credibly convey their type through costly actions, with separating equilibria requiring the cost of the signal to cross-diverge across types.", "architecture", "knowledge", False,
     [("Signaling models", "theory"), ("informed parties", "concept"), ("separating equilibria", "concept"), ("cost of the signal", "concept")],
     [("separating equilibria", "Signaling models", "APPLIES_TO")],
     "which equilibrium structure lets costly signals credibly convey type and what cost condition must hold",
     "signaling model informed type separating equilibrium cost cross type"),
    # --- 41: decision ---
    ("Michael Spence grounded the economics of education on the 1973 job-market signalling model by treating schooling as a credible signal of productivity rather than a productivity-enhancing investment, with separating equilibria sustained whenever schooling is more costly for low-ability workers.", "decision", "knowledge", False,
     [("Michael Spence", "person"), ("job-market signalling", "theory"), ("education", "concept"), ("separating equilibria", "concept")],
     [("job-market signalling", "Michael Spence", "AUTHORED_BY"), ("job-market signalling", "education", "APPLIES_TO")],
     "what role does education play in Spence's job-market signalling model and which cost condition sustains separation",
     "spence 1973 job market signal education productivity separating cost"),
    # --- 42: milestone ---
    ("Spence shared the 2001 Nobel Prize with Akerlof and Stiglitz for foundational analysis of markets with asymmetric information, anchoring signalling, screening, and lemons to a single research programme.", "milestone", "knowledge", False,
     [("Spence", "person"), ("Akerlof", "person"), ("Stiglitz", "person"), ("asymmetric information", "concept")],
     [],
     "which trio shared the 2001 Nobel for information economics and which phenomena does that literature tie together",
     "spence akerlof stiglitz 2001 nobel asymmetric information signal screen lemons"),
    # --- 43: noise ---
    ("The departmental printer ate a stack of exams last Tuesday and the TA mailing list devolved into twelve hours of recrimination.", "fact", "noise", True, [], [], None, None),
    # --- 44: reference ---
    ("Reference the seven Nobel awards of 1994, 1996, 2001, 2005, 2007, 2012, and 2020 when assembling a reading list for modern game theory and mechanism design.", "reference", "knowledge", False,
     [("game theory", "field"), ("mechanism design", "field")],
     [("mechanism design", "game theory", "BUILDS_ON")],
     "which Nobel Prize years trace the canonical awards shaping modern game theory and mechanism design",
     "nobel prize 1994 1996 2001 2007 2012 2020 game theory mechanism design"),
    # --- 45: milestone ---
    ("Hurwicz, Maskin, and Myerson shared the 2007 Nobel Prize for laying the foundations of mechanism design theory, including the revelation principle and implementation under incentive constraints.", "milestone", "knowledge", False,
     [("Hurwicz", "person"), ("Maskin", "person"), ("Myerson", "person"), ("mechanism design", "field"), ("revelation principle", "theory")],
     [("mechanism design", "Hurwicz", "AUTHORED_BY"), ("mechanism design", "Maskin", "AUTHORED_BY"), ("mechanism design", "Myerson", "AUTHORED_BY")],
     "which three economists shared the 2007 Nobel for mechanism-design foundations",
     "hurwicz maskin myerson 2007 nobel mechanism design revelation implementation"),
    # --- 46: milestone ---
    ("Paul Milgrom and Robert Wilson shared the 2020 Nobel Prize for improvements to auction theory and inventions of new formats, including the simultaneous multiple-round auction used for spectrum allocation.", "milestone", "knowledge", False,
     [("Paul Milgrom", "person"), ("Robert Wilson", "person"), ("simultaneous multiple-round auction", "method"), ("spectrum allocation", "concept")],
     [("simultaneous multiple-round auction", "Paul Milgrom", "AUTHORED_BY"), ("simultaneous multiple-round auction", "spectrum allocation", "APPLIES_TO")],
     "which pair won the 2020 Nobel for auction theory and which format did they pioneer for spectrum sales",
     "milgrom wilson 2020 nobel auction spectrum simultaneous multiple round"),
    # --- 47: reference ---
    ("Cite Myerson's 1991 textbook Game Theory: Analysis of Conflict as the standard graduate-level reference on Bayesian games, mechanism design, and the revelation principle together in one volume.", "reference", "knowledge", False,
     [("Myerson", "person"), ("Game Theory: Analysis of Conflict", "publication"), ("Bayesian games", "concept"), ("mechanism design", "field")],
     [("Game Theory: Analysis of Conflict", "Myerson", "AUTHORED_BY")],
     "which 1991 Myerson textbook anchors graduate-level teaching of Bayesian games and mechanism design",
     "myerson 1991 game theory analysis conflict textbook bayesian mechanism"),
    # --- 48: architecture ---
    ("For an applied introduction to matching and market design, the reading list pairs Alvin Roth's 2015 Who Gets What and Why with the Gale-Shapley 1962 paper on college admissions and marriage stability.", "architecture", "knowledge", False,
     [("Alvin Roth", "person"), ("Who Gets What and Why", "publication"), ("Gale-Shapley", "method"), ("college admissions", "concept")],
     [("Who Gets What and Why", "Alvin Roth", "AUTHORED_BY"), ("Gale-Shapley", "college admissions", "APPLIES_TO")],
     "which accessible Roth book and 1962 Gale-Shapley paper together cover matching and market design for new readers",
     "roth who gets what why gale shapley 1962 college admission marriage"),
    # --- 49: problem ---
    ("The focal-point problem Thomas Schelling raised in 1960 is that coordination games with multiple equilibria leave standard game theory silent on which one players actually pick absent culturally salient cues.", "problem", "knowledge", False,
     [("focal-point", "concept"), ("Thomas Schelling", "person"), ("coordination games", "concept"), ("multiple equilibria", "concept")],
     [("focal-point", "Thomas Schelling", "AUTHORED_BY"), ("focal-point", "coordination games", "APPLIES_TO")],
     "which equilibrium-selection problem did Schelling identify for coordination games with multiple equilibria",
     "schelling focal point coordination multiple equilibrium selection cue"),
    # --- 50: preference ---
    ("When choosing between a first-price and second-price format for a one-shot symmetric auction, default to second-price for simpler strategic advice; switch to first-price when revenue dominance under risk-averse bidders matters more than bidder simplicity.", "preference", "knowledge", False,
     [("first-price", "method"), ("second-price", "method"), ("risk-averse bidders", "concept")],
     [("second-price", "first-price", "PREFERS")],
     "how should a designer choose between first-price and second-price auctions given risk aversion and bidder simplicity",
     "first price second price auction risk averse bidder simple revenue"),
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
