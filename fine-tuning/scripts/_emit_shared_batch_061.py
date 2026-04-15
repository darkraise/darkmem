"""One-off emitter for shared-base batch-061 — knowledge domain (economics and econometrics).

Writes 50 rows with ids shared-03001..03050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_061.tmp.jsonl"
ID_OFFSET = 3000

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Adam Smith's The Wealth of Nations, published in 1776, recast political economy around division of labour and the invisible hand of market coordination.", "reference", "knowledge", False,
     [("Adam Smith", "person"), ("The Wealth of Nations", "publication"), ("1776", "date"), ("division of labour", "concept"), ("invisible hand", "concept")],
     [("The Wealth of Nations", "Adam Smith", "AUTHORED_BY")],
     "whose 1776 treatise rebuilt classical economics on labour specialisation and a metaphor of market coordination",
     "Smith founding text classical economics labour specialisation market metaphor"),
    # --- 2 ---
    ("David Ricardo's On the Principles of Political Economy and Taxation, issued in 1817, formalised comparative advantage and the labour theory of value.", "reference", "knowledge", False,
     [("David Ricardo", "person"), ("On the Principles of Political Economy and Taxation", "publication"), ("1817", "date"), ("comparative advantage", "theory"), ("labour theory of value", "theory")],
     [("On the Principles of Political Economy and Taxation", "David Ricardo", "AUTHORED_BY"), ("comparative advantage", "David Ricardo", "AUTHORED_BY")],
     "which 1817 treatise grounded trade theory in comparative advantage",
     "Ricardo Principles taxation comparative advantage labour value year"),
    # --- 3 ---
    ("The marginal revolution of the 1870s, advanced independently by William Stanley Jevons, Carl Menger, and Leon Walras, improves on classical value theory by grounding price in marginal utility.", "milestone", "knowledge", False,
     [("marginal revolution", "event"), ("1870s", "date"), ("William Stanley Jevons", "person"), ("Carl Menger", "person"), ("Leon Walras", "person"), ("marginal utility", "theory")],
     [("marginal revolution", "marginal utility", "BUILDS_ON")],
     "which 1870s shift recast value theory around marginal utility instead of embodied labour",
     "Jevons Menger Walras marginal utility revolution decade trio"),
    # --- 4 ---
    ("Alfred Marshall's Principles of Economics, published in 1890, fused supply and demand into the partial-equilibrium scissors that anchored neoclassical pedagogy for a century.", "reference", "knowledge", False,
     [("Alfred Marshall", "person"), ("Principles of Economics", "publication"), ("1890", "date"), ("partial-equilibrium", "method"), ("neoclassical", "concept")],
     [("Principles of Economics", "Alfred Marshall", "AUTHORED_BY")],
     "whose late-Victorian textbook codified the scissors diagram for a century of mainstream training",
     "Marshall Cambridge late Victorian micro textbook supply demand scissors"),
    # --- 5 ---
    ("John Maynard Keynes's The General Theory of Employment, Interest and Money, published in 1936, replaced classical full-employment assumptions with effective-demand analysis of involuntary unemployment.", "reference", "knowledge", False,
     [("John Maynard Keynes", "person"), ("The General Theory of Employment, Interest and Money", "publication"), ("1936", "date"), ("effective-demand analysis", "theory"), ("classical full-employment assumptions", "theory")],
     [("The General Theory of Employment, Interest and Money", "John Maynard Keynes", "AUTHORED_BY"), ("effective-demand analysis", "classical full-employment assumptions", "REPLACES")],
     "which 1936 book replaced classical full-employment economics with effective-demand analysis",
     "Keynes General Theory effective demand involuntary unemployment year"),
    # --- 6 ---
    ("Milton Friedman's monetarist program, articulated in A Monetary History of the United States in 1963, reframed Keynesian fiscal stabilisation around the long-run neutrality of money.", "decision", "knowledge", False,
     [("Milton Friedman", "person"), ("monetarist program", "theory"), ("A Monetary History of the United States", "publication"), ("1963", "date"), ("Keynesian fiscal stabilisation", "theory"), ("neutrality of money", "concept")],
     [("A Monetary History of the United States", "Milton Friedman", "AUTHORED_BY"), ("monetarist program", "Keynesian fiscal stabilisation", "REPLACES")],
     "which 1963 monetarist book displaced Keynesian fiscal stabilisation in policy debates",
     "Friedman Monetary History monetarism Keynesian replacement year"),
    # --- 7 ---
    ("The Phillips curve, plotted by A. W. Phillips in 1958 from a century of British wage data, suggested an empirical trade-off between unemployment and nominal wage inflation.", "reference", "knowledge", False,
     [("Phillips curve", "theory"), ("A. W. Phillips", "person"), ("1958", "date"), ("British wage data", "finding"), ("nominal wage inflation", "concept")],
     [("Phillips curve", "A. W. Phillips", "AUTHORED_BY")],
     "which 1958 paper drew the original empirical trade-off between unemployment and wage inflation",
     "Phillips curve British wages unemployment nominal inflation year"),
    # --- 8 ---
    ("Friedman's 1968 presidential address argued that the Phillips curve is vertical in the long run because rational agents revise inflation expectations.", "reference", "knowledge", False,
     [("Friedman", "person"), ("1968", "date"), ("Phillips curve", "theory"), ("inflation expectations", "concept")],
     [],
     "whose 1968 address argued the long-run Phillips curve is vertical once expectations adjust",
     "Friedman natural rate vertical Phillips expectations address year"),
    # --- 9 ---
    ("Robert Lucas's Lucas critique of 1976 warned that estimated macro relationships break down once policy regimes change because agents re-optimise expectations.", "reference", "knowledge", False,
     [("Robert Lucas", "person"), ("1976", "date"), ("Lucas critique", "claim"), ("policy regimes", "concept")],
     [("Lucas critique", "Robert Lucas", "AUTHORED_BY")],
     "which 1976 paper warned reduced-form macro models break under policy regime change",
     "reduced form macro policy regime change expectations critique year"),
    # --- 10. noise ---
    ("Need to double-check whether that vintage of the national-accounts file uses the chain-weighted deflator before I quote a growth rate.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Kydland and Prescott's 1977 paper Rules Rather Than Discretion formalised time inconsistency and motivated central-bank independence.", "reference", "knowledge", False,
     [("Kydland and Prescott", "person"), ("1977", "date"), ("Rules Rather Than Discretion", "publication"), ("time inconsistency", "theory"), ("central-bank independence", "concept")],
     [("Rules Rather Than Discretion", "Kydland and Prescott", "AUTHORED_BY")],
     "whose late-1970s monetary paper provided the theoretical case for delegating policy to insulated technocrats",
     "Minnesota duo monetary delegation insulated authority technocratic case decade"),
    # --- 12 ---
    ("Real Business Cycle theory, advanced by Kydland and Prescott in 1982, models aggregate fluctuations as efficient responses to technology shocks rather than monetary disturbances.", "reference", "knowledge", False,
     [("Real Business Cycle theory", "theory"), ("Kydland and Prescott", "person"), ("1982", "date"), ("technology shocks", "concept"), ("monetary disturbances", "concept")],
     [("Real Business Cycle theory", "Kydland and Prescott", "AUTHORED_BY"), ("Real Business Cycle theory", "monetary disturbances", "CONTRADICTS")],
     "which 1982 framework recast business cycles as efficient responses to technology shocks",
     "Kydland Prescott real business cycle technology shock year"),
    # --- 13 ---
    ("New Keynesian DSGE models, codified in Michael Woodford's Interest and Prices of 2003, improves on Real Business Cycle theory by reintroducing nominal rigidities and monetary non-neutrality.", "architecture", "knowledge", False,
     [("New Keynesian DSGE models", "framework"), ("Michael Woodford", "person"), ("Interest and Prices", "publication"), ("2003", "date"), ("Real Business Cycle theory", "theory"), ("nominal rigidities", "concept")],
     [("Interest and Prices", "Michael Woodford", "AUTHORED_BY"), ("New Keynesian DSGE models", "Real Business Cycle theory", "IMPROVES_ON")],
     "which 2003 Woodford volume systematised the New Keynesian DSGE workhorse",
     "Woodford Interest Prices New Keynesian DSGE rigidity year"),
    # --- 14 ---
    ("John Nash's 1950 PNAS paper proved existence of Nash equilibrium in mixed strategies for finite non-cooperative games, founding modern game theory.", "milestone", "knowledge", False,
     [("John Nash", "person"), ("1950", "date"), ("PNAS", "publication"), ("Nash equilibrium", "concept"), ("non-cooperative games", "field")],
     [("Nash equilibrium", "John Nash", "AUTHORED_BY")],
     "whose mid-twentieth-century note opened modern strategic analysis with an existence proof on finite games",
     "academy proceedings short paper twentieth century strategic foundation existence"),
    # --- 15 ---
    ("Von Neumann and Morgenstern's Theory of Games and Economic Behavior, published in 1944, founded expected utility theory and cooperative game analysis.", "reference", "knowledge", False,
     [("Von Neumann and Morgenstern", "person"), ("Theory of Games and Economic Behavior", "publication"), ("1944", "date"), ("expected utility theory", "theory"), ("cooperative game analysis", "field")],
     [("Theory of Games and Economic Behavior", "Von Neumann and Morgenstern", "AUTHORED_BY"), ("expected utility theory", "Von Neumann and Morgenstern", "AUTHORED_BY")],
     "which 1944 book launched expected utility and cooperative game analysis",
     "von Neumann Morgenstern Theory Games expected utility year"),
    # --- 16 ---
    ("Reinhard Selten's 1965 subgame perfection refined Nash equilibrium by ruling out non-credible threats in dynamic games.", "reference", "knowledge", False,
     [("Reinhard Selten", "person"), ("1965", "date"), ("subgame perfection", "concept"), ("Nash equilibrium", "concept"), ("non-credible threats", "concept")],
     [("subgame perfection", "Reinhard Selten", "AUTHORED_BY"), ("subgame perfection", "Nash equilibrium", "IMPROVES_ON")],
     "whose 1965 refinement screened out non-credible threats from Nash equilibrium",
     "German theorist refinement credibility dynamic strategic interaction decade"),
    # --- 17 ---
    ("Daniel Kahneman and Amos Tversky's prospect theory, set out in Econometrica in 1979, replaced expected utility maximisation with reference-dependent loss aversion.", "reference", "knowledge", False,
     [("Daniel Kahneman", "person"), ("Amos Tversky", "person"), ("prospect theory", "theory"), ("Econometrica", "publication"), ("1979", "date"), ("expected utility maximisation", "theory"), ("loss aversion", "concept")],
     [("prospect theory", "Daniel Kahneman", "AUTHORED_BY"), ("prospect theory", "expected utility maximisation", "REPLACES")],
     "whose late-1970s journal article displaced expected utility with a reference-dependent risk model",
     "Israeli psychologists journal paper risk model framing reference points decade"),
    # --- 18 ---
    ("Richard Thaler's Nudge, co-authored with Cass Sunstein in 2008, applied behavioural insights to choice architecture and libertarian paternalism.", "reference", "knowledge", False,
     [("Richard Thaler", "person"), ("Nudge", "publication"), ("Cass Sunstein", "person"), ("2008", "date"), ("choice architecture", "concept"), ("libertarian paternalism", "concept")],
     [("Nudge", "Richard Thaler", "AUTHORED_BY")],
     "which 2008 book popularised choice architecture and libertarian paternalism",
     "Thaler Sunstein Nudge choice architecture libertarian paternalism year"),
    # --- 19 ---
    ("Trygve Haavelmo's 1944 Econometrica supplement The Probability Approach in Econometrics grounded structural estimation in explicit probability models.", "reference", "knowledge", False,
     [("Trygve Haavelmo", "person"), ("1944", "date"), ("Econometrica", "publication"), ("The Probability Approach in Econometrics", "publication"), ("structural estimation", "method")],
     [("The Probability Approach in Econometrics", "Trygve Haavelmo", "AUTHORED_BY")],
     "which 1944 Haavelmo monograph anchored econometrics in explicit probability models",
     "Haavelmo probability approach econometrics structural estimation year"),
    # --- 20 ---
    ("Ordinary least squares, formalised by Legendre and Gauss in the early nineteenth century, remains the workhorse estimator for linear regression under classical Gauss-Markov conditions.", "fact", "knowledge", False,
     [("Ordinary least squares", "method"), ("Legendre", "person"), ("Gauss", "person"), ("Gauss-Markov", "theory")],
     [],
     "which estimator dominates linear regression when Gauss-Markov assumptions hold",
     "OLS Legendre Gauss linear regression Gauss Markov classical"),
    # --- 21 ---
    ("Two-stage least squares, developed by Henri Theil and Robert Basmann in the 1950s, addresses endogeneity by projecting regressors onto instrumental variables.", "fact", "knowledge", False,
     [("Two-stage least squares", "method"), ("Henri Theil", "person"), ("Robert Basmann", "person"), ("1950s", "date"), ("endogeneity", "concept"), ("instrumental variables", "method")],
     [("Two-stage least squares", "instrumental variables", "USES")],
     "which 1950s estimator handles endogeneity by projecting regressors onto instruments",
     "Theil Basmann two stage least squares instruments endogeneity decade"),
    # --- 22 ---
    ("Lars Hansen's 1982 generalised method of moments improves on maximum likelihood by avoiding full distributional assumptions while exploiting orthogonality conditions.", "reference", "knowledge", False,
     [("Lars Hansen", "person"), ("1982", "date"), ("generalised method of moments", "method"), ("maximum likelihood", "method"), ("orthogonality conditions", "concept")],
     [("generalised method of moments", "Lars Hansen", "AUTHORED_BY"), ("generalised method of moments", "maximum likelihood", "IMPROVES_ON")],
     "which 1982 estimator avoids full distributional assumptions by exploiting moment conditions",
     "Hansen GMM moments maximum likelihood distribution free year"),
    # --- 23 ---
    ("Donald Rubin's potential outcomes framework, developed across the 1970s, recast causal inference around counterfactual comparisons rather than structural equations.", "architecture", "knowledge", False,
     [("Donald Rubin", "person"), ("potential outcomes framework", "framework"), ("1970s", "date"), ("causal inference", "field"), ("counterfactual comparisons", "concept"), ("structural equations", "method")],
     [("potential outcomes framework", "Donald Rubin", "AUTHORED_BY"), ("potential outcomes framework", "structural equations", "REPLACES")],
     "which Harvard statistician's seventies program built causal analysis on counterfactual contrasts",
     "statistician decade alternative outcome program effect estimation lineage"),
    # --- 24 ---
    ("Donald Thistlethwaite and Donald Campbell introduced regression discontinuity in 1960 to estimate treatment effects at sharp eligibility cut-offs.", "milestone", "knowledge", False,
     [("Donald Thistlethwaite", "person"), ("Donald Campbell", "person"), ("regression discontinuity", "method"), ("1960", "date"), ("treatment effects", "concept")],
     [("regression discontinuity", "Donald Thistlethwaite", "AUTHORED_BY")],
     "which 1960 educational-psychology paper introduced regression discontinuity",
     "Thistlethwaite Campbell regression discontinuity cut off year"),
    # --- 25 ---
    ("Joshua Angrist and Alan Krueger's 1991 quarter-of-birth instrument estimated returns to schooling using compulsory-attendance laws as exogenous variation.", "reference", "knowledge", False,
     [("Joshua Angrist", "person"), ("Alan Krueger", "person"), ("1991", "date"), ("quarter-of-birth instrument", "method"), ("returns to schooling", "finding"), ("compulsory-attendance laws", "concept")],
     [("quarter-of-birth instrument", "Joshua Angrist", "AUTHORED_BY")],
     "which 1991 paper used quarter-of-birth as an instrument for years of schooling",
     "Angrist Krueger quarter birth schooling instrument year"),
    # --- 26 ---
    ("David Card and Alan Krueger's 1994 New Jersey-Pennsylvania study used a difference-in-differences design to argue that a minimum-wage rise did not reduce fast-food employment.", "reference", "knowledge", False,
     [("David Card", "person"), ("Alan Krueger", "person"), ("1994", "date"), ("New Jersey-Pennsylvania study", "publication"), ("difference-in-differences", "method"), ("minimum-wage rise", "concept")],
     [("New Jersey-Pennsylvania study", "David Card", "AUTHORED_BY"), ("New Jersey-Pennsylvania study", "difference-in-differences", "USES")],
     "which 1994 study used difference-in-differences to challenge negative minimum-wage employment effects",
     "Card Krueger New Jersey Pennsylvania minimum wage difference year"),
    # --- 27 ---
    ("Engle and Granger's 1987 cointegration framework formalised long-run equilibrium relationships among integrated time series and earned the 2003 Nobel Prize.", "milestone", "knowledge", False,
     [("Engle and Granger", "person"), ("1987", "date"), ("cointegration framework", "method"), ("integrated time series", "concept"), ("Nobel Prize", "event")],
     [("cointegration framework", "Engle and Granger", "AUTHORED_BY")],
     "which 1987 framework formalised cointegration among integrated time series",
     "Engle Granger cointegration integrated time series Nobel year"),
    # --- 28 ---
    ("Robert Engle's 1982 ARCH model lets variance evolve with past squared shocks, founding the modern volatility-modelling literature in financial econometrics.", "reference", "knowledge", False,
     [("Robert Engle", "person"), ("1982", "date"), ("ARCH model", "method"), ("financial econometrics", "field")],
     [("ARCH model", "Robert Engle", "AUTHORED_BY")],
     "which 1982 paper founded conditional volatility modelling in financial econometrics",
     "Engle ARCH conditional heteroskedasticity volatility year"),
    # --- 29 ---
    ("Tim Bollerslev's 1986 GARCH extension generalised ARCH by adding lagged conditional variance terms, producing the dominant volatility specification of the 1990s.", "reference", "knowledge", False,
     [("Tim Bollerslev", "person"), ("1986", "date"), ("GARCH", "method"), ("ARCH", "method"), ("conditional variance", "concept")],
     [("GARCH", "Tim Bollerslev", "AUTHORED_BY"), ("GARCH", "ARCH", "EXTENDS")],
     "whose 1986 extension added lagged conditional variance to ARCH",
     "Bollerslev GARCH lagged conditional variance volatility year"),
    # --- 30 ---
    ("Heckman's 1979 selection correction addressed sample-selection bias by jointly modelling the participation and outcome equations.", "reference", "knowledge", False,
     [("Heckman", "person"), ("1979", "date"), ("selection correction", "method"), ("sample-selection bias", "concept")],
     [("selection correction", "Heckman", "AUTHORED_BY")],
     "whose late-1970s estimator coupled participation and outcome equations to defuse non-random sampling",
     "Chicago labour econometrician lambda inverse Mills ratio non random sampling decade"),
    # --- 31 ---
    ("Jacob Mincer's 1974 Schooling, Experience and Earnings produced the canonical log-earnings regression that anchors empirical labour economics.", "reference", "knowledge", False,
     [("Jacob Mincer", "person"), ("1974", "date"), ("Schooling, Experience and Earnings", "publication"), ("log-earnings regression", "method"), ("labour economics", "field")],
     [("Schooling, Experience and Earnings", "Jacob Mincer", "AUTHORED_BY")],
     "whose 1974 monograph anchored the log-earnings regression in labour economics",
     "Columbia labour author monograph wage equation seventies decade"),
    # --- 32 ---
    ("Gary Becker's Human Capital, published in 1964, modelled education and training as investment decisions and seeded a generation of labour-economics research.", "reference", "knowledge", False,
     [("Gary Becker", "person"), ("Human Capital", "publication"), ("1964", "date"), ("education", "concept"), ("labour-economics research", "field")],
     [("Human Capital", "Gary Becker", "AUTHORED_BY")],
     "which 1964 book recast education and training as investment in human capital",
     "Becker Human Capital education training investment year"),
    # --- 33 ---
    ("Robert Solow's 1956 Solow growth model attributes long-run output per worker to capital accumulation and exogenous technical progress.", "reference", "knowledge", False,
     [("Robert Solow", "person"), ("1956", "date"), ("Solow growth model", "theory"), ("capital accumulation", "concept"), ("technical progress", "concept")],
     [("Solow growth model", "Robert Solow", "AUTHORED_BY")],
     "which 1956 model assigns long-run growth to capital deepening and exogenous technology",
     "growth model capital accumulation technical progress year"),
    # --- 34. noise ---
    ("Hmm, the deflator base year on that historical series might not match the headline release I am quoting.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Paul Romer's 1990 endogenous growth model improves on the Solow framework by treating ideas as nonrival inputs that generate increasing returns at the aggregate level.", "reference", "knowledge", False,
     [("Paul Romer", "person"), ("1990", "date"), ("endogenous growth model", "theory"), ("Solow framework", "theory"), ("nonrival inputs", "concept")],
     [("endogenous growth model", "Paul Romer", "AUTHORED_BY"), ("endogenous growth model", "Solow framework", "IMPROVES_ON")],
     "whose 1990 model endogenised technical progress through nonrival ideas",
     "Romer endogenous growth nonrival ideas Solow successor year"),
    # --- 36 ---
    ("Daron Acemoglu and James Robinson's Why Nations Fail, published in 2012, argues that inclusive political institutions cause sustained economic prosperity.", "reference", "knowledge", False,
     [("Daron Acemoglu", "person"), ("James Robinson", "person"), ("Why Nations Fail", "publication"), ("2012", "date"), ("inclusive political institutions", "concept")],
     [("Why Nations Fail", "Daron Acemoglu", "AUTHORED_BY"), ("inclusive political institutions", "Daron Acemoglu", "AUTHORED_BY")],
     "which 2012 book attributed long-run prosperity to inclusive political institutions",
     "Acemoglu Robinson Why Nations Fail inclusive institutions year"),
    # --- 37 ---
    ("Esther Duflo and Abhijit Banerjee's Poor Economics, published in 2011, championed randomised controlled trials as the preferred method for evaluating development interventions.", "preference", "knowledge", False,
     [("Esther Duflo", "person"), ("Abhijit Banerjee", "person"), ("Poor Economics", "publication"), ("2011", "date"), ("randomised controlled trials", "method"), ("development interventions", "concept")],
     [("Poor Economics", "Esther Duflo", "AUTHORED_BY"), ("randomised controlled trials", "development interventions", "PREFERS")],
     "which 2011 book championed randomised controlled trials in development economics",
     "Duflo Banerjee Poor Economics randomised trials development year"),
    # --- 38 ---
    ("Thomas Piketty's Capital in the Twenty-First Century, published in 2014, argued that when the rate of return on capital exceeds the growth rate, wealth concentration rises mechanically.", "reference", "knowledge", False,
     [("Thomas Piketty", "person"), ("Capital in the Twenty-First Century", "publication"), ("2014", "date"), ("rate of return on capital", "concept"), ("wealth concentration", "finding")],
     [("Capital in the Twenty-First Century", "Thomas Piketty", "AUTHORED_BY")],
     "which 2014 book argued wealth concentration rises whenever the return on capital exceeds growth",
     "Piketty Capital Twenty First Century r greater g year"),
    # --- 39 ---
    ("The Heckscher-Ohlin model, formalised in the 1930s, predicts that countries export goods intensive in their relatively abundant factor of production.", "reference", "knowledge", False,
     [("Heckscher-Ohlin model", "theory"), ("1930s", "date"), ("factor of production", "concept")],
     [],
     "which mid-century trade model ties export patterns to relative factor endowments",
     "Heckscher Ohlin factor endowment trade model decade"),
    # --- 40 ---
    ("Paul Krugman's 1979 new trade theory introduced increasing returns and product differentiation to explain intra-industry trade among similar economies.", "reference", "knowledge", False,
     [("Paul Krugman", "person"), ("1979", "date"), ("new trade theory", "theory"), ("intra-industry trade", "finding"), ("increasing returns", "concept")],
     [("new trade theory", "Paul Krugman", "AUTHORED_BY")],
     "which 1979 paper explained intra-industry trade through increasing returns and differentiation",
     "Krugman new trade theory increasing returns differentiation year"),
    # --- 41 ---
    ("Joseph Schumpeter's Capitalism, Socialism and Democracy, published in 1942, framed innovation-led growth around creative destruction by entrepreneurial firms.", "reference", "knowledge", False,
     [("Joseph Schumpeter", "person"), ("Capitalism, Socialism and Democracy", "publication"), ("1942", "date"), ("creative destruction", "concept"), ("entrepreneurial firms", "concept")],
     [("Capitalism, Socialism and Democracy", "Joseph Schumpeter", "AUTHORED_BY"), ("creative destruction", "Joseph Schumpeter", "AUTHORED_BY")],
     "which 1942 book popularised creative destruction as the engine of capitalist growth",
     "Schumpeter Capitalism Socialism Democracy creative destruction year"),
    # --- 42 ---
    ("Friedrich Hayek's The Use of Knowledge in Society, published in 1945, argued that decentralised price signals aggregate dispersed local knowledge better than central planning.", "reference", "knowledge", False,
     [("Friedrich Hayek", "person"), ("The Use of Knowledge in Society", "publication"), ("1945", "date"), ("price signals", "concept"), ("central planning", "concept")],
     [("The Use of Knowledge in Society", "Friedrich Hayek", "AUTHORED_BY"), ("price signals", "central planning", "PREFERS")],
     "which 1945 essay argued decentralised prices outperform central planning at aggregating knowledge",
     "Hayek Use Knowledge Society prices central planning year"),
    # --- 43 ---
    ("Kenneth Arrow and Gerard Debreu's 1954 existence proof established that competitive equilibrium exists in a general-equilibrium economy under convexity assumptions.", "reference", "knowledge", False,
     [("Kenneth Arrow", "person"), ("Gerard Debreu", "person"), ("1954", "date"), ("competitive equilibrium", "concept"), ("general-equilibrium economy", "field"), ("convexity assumptions", "concept")],
     [("competitive equilibrium", "Kenneth Arrow", "AUTHORED_BY")],
     "which 1954 paper proved existence of general competitive equilibrium under convexity",
     "Arrow Debreu existence general equilibrium convexity year"),
    # --- 44 ---
    ("George Akerlof's The Market for Lemons, published in 1970, showed that asymmetric information can collapse markets through adverse selection.", "reference", "knowledge", False,
     [("George Akerlof", "person"), ("The Market for Lemons", "publication"), ("1970", "date"), ("asymmetric information", "concept"), ("adverse selection", "concept")],
     [("The Market for Lemons", "George Akerlof", "AUTHORED_BY")],
     "whose 1970 used-car parable showed how hidden quality can collapse a trading venue",
     "Berkeley economist used car parable hidden quality trading venue collapse decade"),
    # --- 45 ---
    ("Elinor Ostrom's Governing the Commons, published in 1990, documented eight design principles under which user communities sustainably manage common-pool resources.", "reference", "knowledge", False,
     [("Elinor Ostrom", "person"), ("Governing the Commons", "publication"), ("1990", "date"), ("design principles", "framework"), ("common-pool resources", "concept")],
     [("Governing the Commons", "Elinor Ostrom", "AUTHORED_BY")],
     "which 1990 book set out eight design principles for sustainable common-pool governance",
     "Ostrom Governing Commons design principles common pool year"),
    # --- 46 ---
    ("Ronald Coase's 1937 essay The Nature of the Firm explained why firms exist as boundaries that economise on transaction costs.", "reference", "knowledge", False,
     [("Ronald Coase", "person"), ("1937", "date"), ("The Nature of the Firm", "publication"), ("transaction costs", "concept")],
     [("The Nature of the Firm", "Ronald Coase", "AUTHORED_BY")],
     "which 1937 essay explained the existence of firms through transaction costs",
     "Coase Nature Firm transaction costs boundary year"),
    # --- 47 ---
    ("Oliver Williamson's 1985 The Economic Institutions of Capitalism extended Coase by mapping asset specificity, opportunism, and bounded rationality onto governance choices.", "reference", "knowledge", False,
     [("Oliver Williamson", "person"), ("1985", "date"), ("The Economic Institutions of Capitalism", "publication"), ("Coase", "person"), ("asset specificity", "concept")],
     [("The Economic Institutions of Capitalism", "Oliver Williamson", "AUTHORED_BY"), ("The Economic Institutions of Capitalism", "Coase", "BUILDS_ON")],
     "whose 1985 book extended Coase by linking asset specificity to governance choice",
     "Williamson Economic Institutions Capitalism asset specificity year"),
    # --- 48 ---
    ("Hyman Minsky's financial instability hypothesis, articulated through the 1970s and 1980s, argues that long expansions endogenously breed Ponzi finance and crisis.", "reference", "knowledge", False,
     [("Hyman Minsky", "person"), ("financial instability hypothesis", "theory"), ("1970s", "date"), ("1980s", "date"), ("Ponzi finance", "concept")],
     [("financial instability hypothesis", "Hyman Minsky", "AUTHORED_BY")],
     "whose post-Keynesian theory argues calm booms endogenously breed speculative leverage and bust",
     "post Keynesian theorist late twentieth century leverage cycle speculative bust"),
    # --- 49 ---
    ("Carmen Reinhart and Kenneth Rogoff's This Time Is Different, published in 2009, surveyed eight centuries of debt and banking crises to argue that financial fragility recurs.", "reference", "knowledge", False,
     [("Carmen Reinhart", "person"), ("Kenneth Rogoff", "person"), ("This Time Is Different", "publication"), ("2009", "date"), ("financial fragility", "finding")],
     [("This Time Is Different", "Carmen Reinhart", "AUTHORED_BY")],
     "whose 2009 monograph compiled long-horizon banking and sovereign-default data to rebut exceptionalism",
     "Harvard duo monograph long horizon banking sovereign default exceptionalism decade"),
    # --- 50 ---
    ("Claudia Goldin's Career and Family, published in 2021, traced a century of women's labour-force outcomes and earned her the 2023 Nobel Memorial Prize in Economic Sciences.", "milestone", "knowledge", False,
     [("Claudia Goldin", "person"), ("Career and Family", "publication"), ("2021", "date"), ("Nobel Memorial Prize in Economic Sciences", "event"), ("2023", "date")],
     [("Career and Family", "Claudia Goldin", "AUTHORED_BY")],
     "whose 2021 book traced a century of women's labour-force outcomes ahead of a 2023 Nobel",
     "Goldin Career Family women labour century Nobel year"),
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
