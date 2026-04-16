"""One-off emitter for shared-base batch-227 — knowledge domain (microeconomics: consumer theory, firm theory, market structures, game-theoretic oligopoly, externalities, public goods, information economics, general equilibrium, welfare theorems).

Writes 50 rows to data/v2/shared/batch_227.tmp.jsonl with ids shared-11301..11350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_227.tmp.jsonl"
ID_OFFSET = 11300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("Adopted the neoclassical utility-maximisation framework for the consumer-theory track; preferences are encoded as a complete transitive ordering representable by a continuous utility function under mild regularity.", "decision", "knowledge", False,
     [("utility-maximisation", "theory"), ("consumer-theory", "field"), ("utility function", "concept"), ("preferences", "concept")],
     [("utility function", "preferences", "DEPENDS_ON"), ("utility-maximisation", "consumer-theory", "APPLIES_TO")],
     "which framework anchors the consumer-theory track and which properties must the preference ordering satisfy",
     "utility maximisation consumer preference complete transitive continuous function"),
    # --- 2 --- reference
    ("Hal Varian's Intermediate Microeconomics is the primary textbook for the undergraduate sequence; the ninth-edition chapter on Slutsky decomposition drives the problem sets in week six.", "reference", "knowledge", False,
     [("Hal Varian", "person"), ("Intermediate Microeconomics", "publication"), ("Slutsky decomposition", "concept")],
     [("Intermediate Microeconomics", "Hal Varian", "AUTHORED_BY")],
     "which undergraduate textbook anchors the sequence and whose chapter feeds the Slutsky problem sets",
     "varian intermediate microeconomics textbook slutsky undergraduate reference"),
    # --- 3 --- reference
    ("Mas-Colell, Whinston and Green's Microeconomic Theory is the graduate reference; chapters one through three formalise preferences, choice, and demand before any production theory enters the story.", "reference", "knowledge", False,
     [("Mas-Colell", "person"), ("Whinston", "person"), ("Green", "person"), ("Microeconomic Theory", "publication")],
     [("Microeconomic Theory", "Mas-Colell", "AUTHORED_BY"), ("Microeconomic Theory", "Whinston", "AUTHORED_BY"), ("Microeconomic Theory", "Green", "AUTHORED_BY")],
     "which graduate text formalises preferences and choice before production and who authored it",
     "mas colell whinston green microeconomic theory graduate preference choice demand"),
    # --- 4 --- fact
    ("An indifference curve is the level set of a utility function in commodity space; strict convexity of preferences gives curves that bow toward the origin and a unique interior optimum.", "fact", "knowledge", False,
     [("indifference curve", "concept"), ("utility function", "concept"), ("strict convexity", "concept"), ("commodity space", "concept")],
     [("indifference curve", "utility function", "DEPENDS_ON")],
     "what geometric object represents equal-utility bundles and which property of preferences gives a unique optimum",
     "indifference curve level set utility convex preference interior optimum"),
    # --- 5 --- architecture
    ("Marshallian demand solves the consumer's problem at fixed income; the Lagrangian on the budget constraint yields demand as a function of prices and wealth with the tangency condition setting the MRS equal to the price ratio.", "architecture", "knowledge", False,
     [("Marshallian demand", "concept"), ("budget constraint", "concept"), ("MRS", "concept"), ("Lagrangian", "method")],
     [("Marshallian demand", "budget constraint", "DEPENDS_ON"), ("Marshallian demand", "Lagrangian", "USES")],
     "how does the fixed-income consumer problem derive demand and what tangency condition characterises the optimum",
     "marshallian demand lagrangian budget mrs price ratio tangency wealth"),
    # --- 6 --- architecture
    ("Hicksian demand solves the dual expenditure-minimisation problem at a fixed utility target; it isolates the pure substitution response and never slopes upward in its own price.", "architecture", "knowledge", False,
     [("Hicksian demand", "concept"), ("expenditure-minimisation", "method"), ("substitution", "concept")],
     [("Hicksian demand", "expenditure-minimisation", "DEPENDS_ON")],
     "how does the compensated demand problem isolate substitution effects and what sign restriction does it enforce",
     "hicksian demand expenditure minimisation substitution compensated dual"),
    # --- 7 --- decision
    ("The Slutsky equation decomposes a Marshallian demand price effect into a Hicksian demand substitution term and an income term weighted by the initial quantity; the lecture uses it to sign cross-price effects for normal goods.", "decision", "knowledge", False,
     [("Slutsky equation", "theory"), ("Marshallian demand", "concept"), ("Hicksian demand", "concept"), ("income term", "concept")],
     [("Slutsky equation", "Marshallian demand", "APPLIES_TO"), ("Slutsky equation", "Hicksian demand", "DEPENDS_ON")],
     "which identity splits a price effect into substitution and income pieces and what does it sign for normal goods",
     "slutsky equation decomposition marshallian hicksian substitution income price effect"),
    # --- 8 --- milestone
    ("Paul Samuelson introduced the Weak Axiom of Revealed Preference in 1938, recasting demand theory without appealing to unobservable utility and opening the door to the integrability problem.", "milestone", "knowledge", False,
     [("Paul Samuelson", "person"), ("Weak Axiom of Revealed Preference", "theory"), ("integrability problem", "concept"), ("demand theory", "field")],
     [("Weak Axiom of Revealed Preference", "Paul Samuelson", "AUTHORED_BY"), ("Weak Axiom of Revealed Preference", "demand theory", "APPLIES_TO")],
     "which 1938 axiom recast demand theory without utility and what open question did it raise",
     "samuelson 1938 weak axiom revealed preference utility integrability demand"),
    # --- 9 --- fact
    ("Revealed-preference theory infers ordinal preferences from observed choices; the Strong Axiom of Revealed Preference strengthens the Weak Axiom of Revealed Preference by ruling out cycles of any length in the revealed-at-least-as-good relation.", "fact", "knowledge", False,
     [("Revealed-preference theory", "theory"), ("Strong Axiom of Revealed Preference", "concept"), ("Weak Axiom of Revealed Preference", "theory")],
     [("Strong Axiom of Revealed Preference", "Weak Axiom of Revealed Preference", "IMPROVES_ON")],
     "which choice-based theory recovers preferences from data and how does the strong version strengthen the weak one",
     "revealed preference strong weak axiom cycle observed choice ordinal"),
    # --- 10 --- noise
    ("The department mailroom's pneumatic tube has been gently thumping every forty minutes and nobody on the first floor will claim the package.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- reference
    ("The firm's production function maps input bundles into a maximum output; isoquants are its level sets and the marginal rate of technical substitution plays the role of the MRS on the cost side.", "reference", "knowledge", False,
     [("production function", "concept"), ("isoquant", "concept"), ("marginal rate of technical substitution", "concept")],
     [("isoquant", "production function", "DEPENDS_ON")],
     "how does producer theory mirror consumer theory and what object plays the role of the MRS on the production side",
     "production function isoquant mrts input output level set firm"),
    # --- 12 --- decision
    ("Chose the Cobb-Douglas production function as the baseline for the firm-theory problem set; its constant output elasticities and unit elasticity of substitution make the cost-minimisation algebra clean.", "decision", "knowledge", False,
     [("Cobb-Douglas", "concept"), ("firm-theory", "field"), ("elasticity of substitution", "concept"), ("cost-minimisation", "method")],
     [("Cobb-Douglas", "firm-theory", "APPLIES_TO")],
     "which production function serves as the baseline for the problem set and which algebraic properties recommended it",
     "cobb douglas production elasticity substitution cost minimisation firm baseline"),
    # --- 13 --- decision
    ("The CES production function nests Cobb-Douglas, Leontief, and linear technologies as limits of its substitution parameter; the elasticity of substitution is constant along every isoquant by construction.", "decision", "knowledge", False,
     [("CES", "concept"), ("Cobb-Douglas", "concept"), ("Leontief", "concept"), ("linear technologies", "concept"), ("elasticity of substitution", "concept")],
     [("CES", "Cobb-Douglas", "EXTENDS"), ("CES", "Leontief", "EXTENDS")],
     "which functional form nests Cobb-Douglas and Leontief as limits and what stays constant along its isoquants",
     "ces production function cobb douglas leontief linear elasticity substitution"),
    # --- 14 --- fact
    ("The returns to scale property describes how output changes when every input scales by a common factor; a homogeneous production function of degree k above one exhibits increasing returns and gives decreasing long-run average cost.", "fact", "knowledge", False,
     [("returns to scale", "concept"), ("homogeneous production function", "concept"), ("long-run average cost", "concept")],
     [("returns to scale", "long-run average cost", "APPLIES_TO")],
     "what property of the production function controls returns to scale and how does it shape long-run average cost",
     "returns scale homogeneous production degree increasing decreasing long run average"),
    # --- 15 --- reference
    ("The cost function is derived by solving the firm's cost-minimisation problem given factor prices; Shephard's lemma recovers conditional factor demand as the partial derivative of cost with respect to the input price.", "reference", "knowledge", False,
     [("cost function", "concept"), ("cost-minimisation", "method"), ("Shephard's lemma", "theory"), ("conditional factor demand", "concept")],
     [("cost function", "cost-minimisation", "DEPENDS_ON"), ("conditional factor demand", "Shephard's lemma", "DEPENDS_ON")],
     "how is the cost function obtained from the firm problem and which lemma recovers conditional factor demands",
     "cost function minimisation shephard lemma conditional factor demand input price"),
    # --- 16 --- decision
    ("The perfect competition model is adopted as the benchmark market structure: price-taking firms, free entry and exit, homogeneous product, and perfect information jointly pin down the long-run zero-profit condition.", "decision", "knowledge", False,
     [("perfect competition", "concept"), ("price-taking", "concept"), ("free entry", "concept"), ("zero-profit condition", "concept")],
     [("perfect competition", "zero-profit condition", "CAUSES")],
     "which market-structure benchmark combines four assumptions to force long-run zero profits",
     "perfect competition price taking free entry homogeneous zero profit long run"),
    # --- 17 --- fact
    ("A monopoly faces the whole downward-sloping market demand and sets marginal revenue equal to marginal cost; the resulting Lerner index measures the markup as a function of the own-price elasticity of demand.", "fact", "knowledge", False,
     [("monopoly", "concept"), ("marginal revenue", "concept"), ("marginal cost", "concept"), ("Lerner index", "concept"), ("own-price elasticity", "concept")],
     [("Lerner index", "own-price elasticity", "DEPENDS_ON")],
     "which optimality condition characterises a monopoly price and which index reads off the resulting markup",
     "monopoly marginal revenue cost lerner index markup elasticity demand"),
    # --- 18 --- decision
    ("The monopolistic competition framework is used to model differentiated-product retail; the Dixit-Stiglitz symmetric equilibrium pins down firm-level markups via the elasticity of substitution across varieties.", "decision", "knowledge", False,
     [("monopolistic competition", "concept"), ("Dixit-Stiglitz", "theory"), ("differentiated-product", "concept"), ("elasticity of substitution", "concept")],
     [("Dixit-Stiglitz", "monopolistic competition", "APPLIES_TO")],
     "which oligopoly framework models differentiated retail and what pins down firm-level markups in its symmetric equilibrium",
     "monopolistic competition dixit stiglitz differentiated variety elasticity markup"),
    # --- 19 --- architecture
    ("Cournot duopoly fixes quantities as strategic variables and solves for a Nash equilibrium in best-response quantities; equilibrium output lies strictly between the monopoly and competitive levels.", "architecture", "knowledge", False,
     [("Cournot duopoly", "theory"), ("Nash equilibrium", "concept"), ("best-response", "method"), ("monopoly", "concept")],
     [("Cournot duopoly", "Nash equilibrium", "USES")],
     "which oligopoly model treats quantity as the strategic variable and where does its equilibrium output sit",
     "cournot duopoly quantity nash best response monopoly competitive output"),
    # --- 20 --- architecture
    ("Bertrand competition makes price the strategic variable with homogeneous goods; any price above marginal cost is undercut, so the unique equilibrium collapses to marginal-cost pricing and the Bertrand paradox.", "architecture", "knowledge", False,
     [("Bertrand competition", "theory"), ("marginal cost", "concept"), ("Bertrand paradox", "finding"), ("homogeneous goods", "concept")],
     [("Bertrand competition", "Bertrand paradox", "CAUSES")],
     "which oligopoly model pushes price to marginal cost with homogeneous goods and what puzzle does it produce",
     "bertrand competition price marginal cost undercut paradox homogeneous equilibrium"),
    # --- 21 --- architecture
    ("Stackelberg leadership resolves the Cournot duopoly by giving one firm the move first; the leader internalises the follower's best-response function and secures a first-mover output advantage.", "architecture", "knowledge", False,
     [("Stackelberg leadership", "theory"), ("Cournot duopoly", "theory"), ("best-response", "method"), ("first-mover", "concept")],
     [("Stackelberg leadership", "Cournot duopoly", "EXTENDS")],
     "which oligopoly variant sequences moves and what informational advantage does the leader exploit",
     "stackelberg leader follower cournot sequential best response first mover"),
    # --- 22 --- decision
    ("Antoine Augustin Cournot introduced the quantity-setting duopoly model in 1838 in Recherches sur les principes mathematiques de la theorie des richesses, anticipating Nash equilibrium by more than a century.", "decision", "knowledge", False,
     [("Antoine Augustin Cournot", "person"), ("Recherches sur les principes mathematiques de la theorie des richesses", "publication"), ("Nash equilibrium", "concept"), ("duopoly", "concept")],
     [("Recherches sur les principes mathematiques de la theorie des richesses", "Antoine Augustin Cournot", "AUTHORED_BY")],
     "which 1838 monograph introduced quantity-setting duopoly and which later solution concept did it anticipate",
     "cournot 1838 recherches richesses duopoly quantity nash equilibrium precursor"),
    # --- 23 --- milestone
    ("Joseph Bertrand published his 1883 review of Cournot duopoly in the Journal des Savants and pointed out that price competition collapses the duopoly markup; the critique seeded a century of oligopoly debate.", "milestone", "knowledge", False,
     [("Joseph Bertrand", "person"), ("Journal des Savants", "publication"), ("Cournot duopoly", "theory"), ("price competition", "concept")],
     [("Journal des Savants", "Joseph Bertrand", "AUTHORED_BY"), ("Journal des Savants", "Cournot duopoly", "CONTRADICTS")],
     "which 1883 review argued price competition collapses the duopoly markup and where did it appear",
     "bertrand 1883 journal savants cournot review price competition markup critique"),
    # --- 24 --- decision
    ("The study of externalities is adopted as the canonical market-failure case; a negative externality drives a wedge between the private and social marginal cost curves and yields a deadweight loss at the unregulated equilibrium.", "decision", "knowledge", False,
     [("externalities", "concept"), ("market-failure", "concept"), ("social marginal cost", "concept"), ("deadweight loss", "concept")],
     [("externalities", "deadweight loss", "CAUSES")],
     "which class of market failure drives a wedge between private and social cost and what efficiency loss follows",
     "externality market failure social private marginal cost deadweight loss wedge"),
    # --- 25 --- milestone
    ("Ronald Coase's 1960 paper The Problem of Social Cost published in the Journal of Law and Economics argued that with clearly assigned property rights and zero transaction costs, bargaining internalises externalities regardless of who holds the right.", "milestone", "knowledge", False,
     [("Ronald Coase", "person"), ("The Problem of Social Cost", "publication"), ("Journal of Law and Economics", "publication"), ("property rights", "concept"), ("transaction costs", "concept")],
     [("The Problem of Social Cost", "Ronald Coase", "AUTHORED_BY"), ("The Problem of Social Cost", "Journal of Law and Economics", "PUBLISHED_IN")],
     "which 1960 paper argued that property rights and zero transaction costs let bargaining cure externalities",
     "coase 1960 problem social cost journal law economics property rights bargaining"),
    # --- 26 --- fact
    ("A Pigouvian tax sets the per-unit tax equal to the marginal external damage at the social optimum; the unregulated market then internalises the wedge without requiring quantity regulation.", "fact", "knowledge", False,
     [("Pigouvian tax", "concept"), ("marginal external damage", "concept"), ("social optimum", "concept")],
     [("Pigouvian tax", "marginal external damage", "DEPENDS_ON")],
     "which per-unit tax aligns private and social marginal cost and how is its rate chosen",
     "pigouvian tax marginal external damage social optimum internalise wedge"),
    # --- 27 --- decision
    ("The Coase theorem is preferred over Pigouvian taxation when transaction costs are low and property rights can be clearly assigned; the Pigouvian lever wins when bargaining fails due to numerous parties or hidden damages.", "decision", "knowledge", False,
     [("Coase theorem", "theory"), ("Pigouvian tax", "concept"), ("transaction costs", "concept"), ("property rights", "concept")],
     [("Coase theorem", "Pigouvian tax", "PREFERS")],
     "when is bargaining preferred to a Pigouvian tax for correcting an externality and what flips the preference",
     "coase theorem pigouvian tax transaction cost property right bargaining prefer"),
    # --- 28 --- reference
    ("A public good is non-rival and non-excludable by assumption; the Samuelson condition characterises efficient provision by equating the sum of marginal rates of substitution across consumers to the marginal rate of transformation.", "reference", "knowledge", False,
     [("public good", "concept"), ("Samuelson condition", "theory"), ("marginal rates of substitution", "concept"), ("marginal rate of transformation", "concept")],
     [("Samuelson condition", "public good", "APPLIES_TO")],
     "which two properties define a public good and which condition pins down the efficient level of provision",
     "public good non rival non excludable samuelson condition mrs mrt efficient"),
    # --- 29 --- problem
    ("The free-rider problem blocks voluntary provision of public goods: each consumer prefers to understate willingness to pay, so decentralised contributions fall short of the level prescribed by the Samuelson condition.", "problem", "knowledge", False,
     [("free-rider problem", "concept"), ("public goods", "concept"), ("Samuelson condition", "theory"), ("willingness to pay", "concept")],
     [("free-rider problem", "public goods", "APPLIES_TO")],
     "which incentive failure undermines voluntary public-good provision and what benchmark does it miss",
     "free rider public good samuelson willingness to pay voluntary provision"),
    # --- 30 --- architecture
    ("Lindahl pricing restores efficiency in public goods by charging each consumer a personalised price equal to her marginal valuation; the common quantity at which budgets balance delivers a Pareto-efficient allocation.", "architecture", "knowledge", False,
     [("Lindahl pricing", "method"), ("public good", "concept"), ("Pareto-efficient", "concept"), ("marginal valuation", "concept")],
     [("Lindahl pricing", "public good", "APPLIES_TO")],
     "which personalised-price scheme delivers efficient public-good provision and what balances at the common quantity",
     "lindahl pricing public good personalised marginal valuation pareto efficient"),
    # --- 31 --- milestone
    ("George Akerlof's 1970 paper The Market for Lemons published in the Quarterly Journal of Economics showed that asymmetric information can collapse a used-car market into low-quality trade only, founding modern information economics.", "milestone", "knowledge", False,
     [("George Akerlof", "person"), ("The Market for Lemons", "publication"), ("Quarterly Journal of Economics", "publication"), ("asymmetric information", "concept"), ("information economics", "field")],
     [("The Market for Lemons", "George Akerlof", "AUTHORED_BY"), ("The Market for Lemons", "Quarterly Journal of Economics", "PUBLISHED_IN")],
     "which 1970 paper showed asymmetric information can unravel a used-car market and where did it appear",
     "akerlof 1970 lemons quarterly journal asymmetric information economics"),
    # --- 32 --- problem
    ("The adverse selection failure hits insurance markets when asymmetric information stops insurers distinguishing high-risk from low-risk applicants at the posted premium; low-risk types exit and the pool deteriorates into the high-risk corner.", "problem", "knowledge", False,
     [("adverse selection", "concept"), ("insurance markets", "field"), ("asymmetric information", "concept")],
     [("adverse selection", "insurance markets", "APPLIES_TO")],
     "which asymmetric-information failure empties insurance pools of low-risk buyers and what is the end state",
     "adverse selection insurance premium asymmetric information risk pool unravel"),
    # --- 33 --- problem
    ("The moral hazard problem arises after a contract is signed when the insured action is unobservable to the principal; the risk-sharing contract must trade full insurance against incentives to exert costly effort.", "problem", "knowledge", False,
     [("moral hazard", "concept"), ("principal", "concept"), ("risk-sharing", "concept"), ("effort", "concept")],
     [("moral hazard", "risk-sharing", "APPLIES_TO")],
     "which post-contract information failure forces a trade-off between insurance and incentives",
     "moral hazard unobservable effort principal agent insurance incentive risk"),
    # --- 34 --- architecture
    ("The principal-agent problem sets up a risk-neutral principal writing a contract for a risk-averse agent whose effort is a hidden action; the optimal contract ties pay to a noisy performance signal balancing insurance and effort incentives.", "architecture", "knowledge", False,
     [("principal-agent problem", "theory"), ("risk-averse agent", "concept"), ("hidden action", "concept"), ("performance signal", "concept")],
     [("principal-agent problem", "hidden action", "DEPENDS_ON")],
     "how does the principal-agent model structure contracts when effort is hidden and what does optimal pay depend on",
     "principal agent risk averse hidden effort performance signal contract insurance"),
    # --- 35 --- milestone
    ("Michael Spence's 1973 paper Job Market Signaling published in the Quarterly Journal of Economics introduced signaling theory and showed that costly education can separate high- from low-productivity workers in equilibrium even when education adds no productivity.", "milestone", "knowledge", False,
     [("Michael Spence", "person"), ("Job Market Signaling", "publication"), ("Quarterly Journal of Economics", "publication"), ("signaling", "theory")],
     [("Job Market Signaling", "Michael Spence", "AUTHORED_BY"), ("Job Market Signaling", "Quarterly Journal of Economics", "PUBLISHED_IN")],
     "which 1973 paper used education as a separating device without any productivity effect",
     "spence 1973 job market signaling quarterly journal education productivity separate"),
    # --- 36 --- fact
    ("A separating equilibrium in the Spence signaling model requires the single-crossing condition: high-type indifference curves in effort-wage space must cross low-type curves from below at every point.", "fact", "knowledge", False,
     [("separating equilibrium", "concept"), ("signaling", "theory"), ("single-crossing condition", "concept"), ("Spence", "person")],
     [("separating equilibrium", "single-crossing condition", "DEPENDS_ON")],
     "which geometric condition on indifference curves supports a separating equilibrium in the signaling model",
     "separating equilibrium spence signaling single crossing condition indifference"),
    # --- 37 --- milestone
    ("Rothschild and Stiglitz's 1976 paper Equilibrium in Competitive Insurance Markets published in the Quarterly Journal of Economics introduced screening via self-selecting menus and showed pooling equilibria need not exist in competitive insurance.", "milestone", "knowledge", False,
     [("Rothschild", "person"), ("Stiglitz", "person"), ("Equilibrium in Competitive Insurance Markets", "publication"), ("Quarterly Journal of Economics", "publication"), ("screening", "theory")],
     [("Equilibrium in Competitive Insurance Markets", "Rothschild", "AUTHORED_BY"), ("Equilibrium in Competitive Insurance Markets", "Stiglitz", "AUTHORED_BY"), ("Equilibrium in Competitive Insurance Markets", "Quarterly Journal of Economics", "PUBLISHED_IN")],
     "which 1976 paper introduced screening in insurance and what equilibrium existence result did it prove",
     "rothschild stiglitz 1976 equilibrium competitive insurance screening pooling"),
    # --- 38 --- decision
    ("Used Spence signaling to model sheepskin effects on wages and Rothschild-Stiglitz screening to model insurance menus; signaling moves first with the informed party, screening moves first with the uninformed.", "decision", "knowledge", False,
     [("signaling", "theory"), ("screening", "theory"), ("Spence", "person"), ("Rothschild", "person")],
     [("signaling", "screening", "RELATED_TO")],
     "which information-economics tool fits wage premia from credentials and which fits insurance menu design",
     "signaling screening spence rothschild stiglitz informed uninformed move order"),
    # --- 39 --- architecture
    ("The general equilibrium theory framework closes the consumer and firm problems into a single system: prices clear all markets simultaneously and Walras's law makes one market-clearing condition redundant once the others hold.", "architecture", "knowledge", False,
     [("general equilibrium theory", "theory"), ("Walras's law", "theory"), ("market-clearing", "concept")],
     [("general equilibrium theory", "Walras's law", "USES")],
     "how does general-equilibrium theory close consumer and firm problems and why is one market-clearing condition redundant",
     "general equilibrium walras law market clearing simultaneous prices consumer firm"),
    # --- 40 --- milestone
    ("Kenneth Arrow and Gerard Debreu's 1954 paper Existence of an Equilibrium for a Competitive Economy published in Econometrica proved existence of a competitive equilibrium under convexity and continuity assumptions using a Kakutani fixed-point argument.", "milestone", "knowledge", False,
     [("Kenneth Arrow", "person"), ("Gerard Debreu", "person"), ("Existence of an Equilibrium for a Competitive Economy", "publication"), ("Econometrica", "publication"), ("Kakutani fixed-point", "theory")],
     [("Existence of an Equilibrium for a Competitive Economy", "Kenneth Arrow", "AUTHORED_BY"), ("Existence of an Equilibrium for a Competitive Economy", "Gerard Debreu", "AUTHORED_BY"), ("Existence of an Equilibrium for a Competitive Economy", "Econometrica", "PUBLISHED_IN")],
     "which 1954 paper proved existence of competitive equilibrium and which fixed-point theorem did it invoke",
     "arrow debreu 1954 existence equilibrium econometrica kakutani fixed point"),
    # --- 41 --- reference
    ("The Arrow-Debreu model is the canonical general-equilibrium reference for the graduate sequence; Gerard Debreu's 1959 Theory of Value monograph axiomatised the framework that the 1954 existence paper established.", "reference", "knowledge", False,
     [("Arrow-Debreu model", "theory"), ("Theory of Value", "publication"), ("Gerard Debreu", "person")],
     [("Theory of Value", "Gerard Debreu", "AUTHORED_BY"), ("Theory of Value", "Arrow-Debreu model", "APPLIES_TO")],
     "which Arrow-Debreu monograph axiomatises general equilibrium and who wrote it",
     "arrow debreu theory value 1959 debreu general equilibrium axiomatisation"),
    # --- 42 --- fact
    ("The First Welfare Theorem states that every competitive equilibrium is Pareto efficient under local non-satiation; the proof is elementary and does not require convexity of preferences.", "fact", "knowledge", False,
     [("First Welfare Theorem", "theory"), ("Pareto efficient", "concept"), ("local non-satiation", "concept")],
     [("First Welfare Theorem", "Pareto efficient", "CAUSES")],
     "which welfare theorem links competitive equilibrium to Pareto efficiency and what minimal assumption drives the proof",
     "first welfare theorem competitive equilibrium pareto efficient local non satiation"),
    # --- 43 --- architecture
    ("The Second Welfare Theorem says any Pareto-efficient allocation can be decentralised as a competitive equilibrium after appropriate lump-sum transfers, provided convex preferences and convex production sets hold.", "architecture", "knowledge", False,
     [("Second Welfare Theorem", "theory"), ("Pareto-efficient allocation", "concept"), ("lump-sum transfers", "concept"), ("convex preferences", "concept")],
     [("Second Welfare Theorem", "Pareto-efficient allocation", "APPLIES_TO")],
     "which welfare theorem decentralises an efficient allocation via transfers and what convexity assumption does it need",
     "second welfare theorem pareto lump sum transfer convex preference decentralise"),
    # --- 44 --- preference
    ("Prefer Varian's Microeconomic Analysis over Intermediate Microeconomics for the PhD problem sets; the duality-first treatment of demand and cost dovetails with the Mas-Colell proofs used later in the term.", "preference", "knowledge", False,
     [("Varian", "person"), ("Microeconomic Analysis", "publication"), ("Intermediate Microeconomics", "publication"), ("Mas-Colell", "person")],
     [("Microeconomic Analysis", "Intermediate Microeconomics", "PREFERS"), ("Microeconomic Analysis", "Varian", "AUTHORED_BY")],
     "which Varian book is preferred for PhD problem sets and why does it line up with Mas-Colell",
     "varian microeconomic analysis intermediate phd duality mas colell problem set"),
    # --- 45 --- preference
    ("Prefer Mankiw's Principles of Economics for the introductory undergraduate lecture because its prose-first exposition carries non-majors further than a calculus-first text; Varian takes over once we reach consumer theory.", "preference", "knowledge", False,
     [("Mankiw", "person"), ("Principles of Economics", "publication"), ("Varian", "person"), ("consumer theory", "field")],
     [("Principles of Economics", "Mankiw", "AUTHORED_BY"), ("Principles of Economics", "Varian", "PREFERS")],
     "which introductory textbook is preferred for non-majors and when does the course hand off to Varian",
     "mankiw principles economics introductory undergraduate prose first varian consumer"),
    # --- 46 --- preference
    ("Prefer Mas-Colell, Whinston and Green over Kreps's A Course in Microeconomic Theory for the qualifying-exam reading list; the encyclopaedic coverage is worth the heavier notation when students re-read in year two.", "preference", "knowledge", False,
     [("Mas-Colell", "person"), ("A Course in Microeconomic Theory", "publication"), ("Kreps", "person")],
     [("Mas-Colell", "A Course in Microeconomic Theory", "PREFERS"), ("A Course in Microeconomic Theory", "Kreps", "AUTHORED_BY")],
     "which graduate text is preferred over Kreps for the qualifying-exam list and what trade-off justifies the choice",
     "mas colell kreps course microeconomic theory qualifying exam graduate"),
    # --- 47 --- preference
    ("Prefer Hicksian demand over Marshallian demand when teaching compensating variation and equivalent variation; the compensated curve cleanly delivers the area interpretation that Marshallian consumer surplus only approximates.", "preference", "knowledge", False,
     [("Hicksian demand", "concept"), ("Marshallian demand", "concept"), ("compensating variation", "concept"), ("consumer surplus", "concept")],
     [("Hicksian demand", "Marshallian demand", "PREFERS")],
     "which demand curve is preferred for teaching compensating variation and why is Marshallian surplus only an approximation",
     "hicksian marshallian demand compensating equivalent variation consumer surplus teach"),
    # --- 48 --- decision
    ("Adopt the Edgeworth box as the default visual for two-person two-good exchange economies; the contract curve and the core collapse onto Walrasian equilibria as the economy is replicated, a replication theorem Debreu and Scarf proved in 1963.", "decision", "knowledge", False,
     [("Edgeworth box", "method"), ("contract curve", "concept"), ("core", "concept"), ("Walrasian equilibria", "concept"), ("Debreu and Scarf", "person")],
     [("core", "Walrasian equilibria", "APPLIES_TO")],
     "which visual anchors two-good exchange teaching and which 1963 theorem links the core to Walrasian equilibria",
     "edgeworth box contract curve core walrasian replication debreu scarf 1963"),
    # --- 49 --- decision
    ("Decided the mechanism-design lecture opens with the Vickrey-Clarke-Groves mechanism as the dominant-strategy efficient rule for public-goods provision, deferring Bayesian implementation to the following week.", "decision", "knowledge", False,
     [("mechanism-design", "field"), ("Vickrey-Clarke-Groves", "method"), ("dominant-strategy", "concept"), ("public-goods provision", "concept")],
     [("Vickrey-Clarke-Groves", "public-goods provision", "APPLIES_TO")],
     "which mechanism opens the mechanism-design lecture and what solution concept makes it attractive",
     "vickrey clarke groves mechanism dominant strategy public good design lecture"),
    # --- 50 --- noise
    ("The faculty espresso machine's steam wand has been hissing in F-sharp since the renovation and the chair keeps threatening to tune it.", "fact", "noise", True, [], [], None, None),
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
