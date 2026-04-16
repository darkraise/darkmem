"""One-off emitter for shared-base batch-232 — knowledge domain (macroeconomics: Keynes, Hicks IS-LM, Samuelson, Friedman, Lucas, RBC, New Keynesian, DSGE, growth theory, Phillips curve, Taylor rule, VAR, Piketty).

Writes 50 rows to data/v2/shared/batch_232.tmp.jsonl with ids shared-11551..11600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_232.tmp.jsonl"
ID_OFFSET = 11550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Keynes wrote the General Theory in 1936 to dislodge the classical assumption that labour markets clear on their own; aggregate demand became the organising variable and involuntary unemployment stopped being a definitional contradiction.", "milestone", "knowledge", False,
     [("Keynes", "person"), ("General Theory", "publication"), ("1936", "date"), ("aggregate demand", "concept"), ("involuntary unemployment", "concept")],
     [("Keynes", "General Theory", "AUTHORED_BY"), ("General Theory", "aggregate demand", "PRODUCES")],
     "which 1936 book broke with the classical self-clearing labour market and elevated aggregate demand",
     "keynes general theory 1936 aggregate demand unemployment classical"),
    # --- 2 ---
    ("Hicks distilled the General Theory into the IS-LM diagram in his 1937 Econometrica paper, giving the profession a tractable two-curve picture of output and interest determination that textbooks would lean on for decades.", "reference", "knowledge", False,
     [("Hicks", "person"), ("IS-LM", "concept"), ("Econometrica", "publication"), ("1937", "date")],
     [("Hicks", "IS-LM", "AUTHORED_BY")],
     "who formalised Keynes into the IS-LM apparatus and in which journal did it first appear",
     "hicks is lm econometrica 1937 keynes diagram output interest"),
    # --- 3 ---
    ("Samuelson's neoclassical synthesis stitched Keynesian short-run demand management onto the classical long-run equilibrium core; his Foundations of Economic Analysis supplied the maths and Economics made it pedagogy.", "architecture", "knowledge", False,
     [("Samuelson", "person"), ("neoclassical synthesis", "concept"), ("Foundations of Economic Analysis", "publication"), ("Economics", "publication")],
     [("Samuelson", "neoclassical synthesis", "AUTHORED_BY"), ("Samuelson", "Foundations of Economic Analysis", "AUTHORED_BY")],
     "whose synthesis glued Keynesian demand management onto a classical long-run core",
     "samuelson neoclassical synthesis foundations economics keynes classical"),
    # --- 4 ---
    ("Milton Friedman's monetarism argued that inflation is everywhere and always a monetary phenomenon; the permanent-income hypothesis and the k-percent rule followed as natural implications of that single primitive.", "fact", "knowledge", False,
     [("Milton Friedman", "person"), ("monetarism", "concept"), ("permanent-income hypothesis", "concept"), ("k-percent rule", "concept")],
     [("Milton Friedman", "monetarism", "AUTHORED_BY"), ("monetarism", "k-percent rule", "CAUSES")],
     "which doctrine treats inflation as a purely monetary phenomenon and who championed it",
     "friedman monetarism inflation money permanent income k percent rule"),
    # --- 5 ---
    ("The Lucas critique demolished reduced-form policy evaluation by pointing out that agent decision rules shift when the policy rule shifts; any model fitted on one regime cannot be used to rank counterfactual regimes.", "problem", "knowledge", False,
     [("Lucas critique", "concept"), ("reduced-form", "concept"), ("policy rule", "concept"), ("decision rules", "concept")],
     [("Lucas critique", "reduced-form", "REPLACES")],
     "which critique showed that reduced-form policy simulations collapse when the policy regime itself changes",
     "lucas critique reduced form policy rule decision rule regime"),
    # --- 6 ---
    ("Kydland and Prescott launched real business cycle theory with their 1982 Time to Build paper, insisting that a neoclassical growth model with technology shocks could replicate cyclical moments without nominal frictions.", "milestone", "knowledge", False,
     [("Kydland", "person"), ("Prescott", "person"), ("real business cycle", "concept"), ("Time to Build", "publication"), ("1982", "date")],
     [("Kydland", "Time to Build", "AUTHORED_BY"), ("Prescott", "Time to Build", "AUTHORED_BY"), ("Time to Build", "real business cycle", "PRODUCES")],
     "which 1982 paper kicked off real business cycle theory and who wrote it",
     "kydland prescott rbc time to build 1982 technology shock cycle"),
    # --- 7 ---
    ("Woodford's Interest and Prices reconstructed monetary theory without money: the central bank sets an interest rate, expectations about future rates pin down current inflation, and the quantity of base money becomes a passive residual.", "reference", "knowledge", False,
     [("Woodford", "person"), ("Interest and Prices", "publication"), ("central bank", "organization"), ("base money", "concept")],
     [("Woodford", "Interest and Prices", "AUTHORED_BY")],
     "which Woodford treatise laid out monetary policy with interest as the instrument and money as a residual",
     "woodford interest prices monetary central bank rate expectation"),
    # --- 8 ---
    ("Gali's textbook on the New Keynesian framework codified the three-equation canonical model with sticky prices a la Calvo, a dynamic IS equation, and a forward-looking Phillips curve driven by real marginal cost.", "architecture", "knowledge", False,
     [("Gali", "person"), ("New Keynesian", "concept"), ("Calvo", "person"), ("Phillips curve", "concept"), ("dynamic IS", "concept")],
     [("Gali", "New Keynesian", "AUTHORED_BY"), ("New Keynesian", "Calvo", "USES")],
     "which textbook codified the canonical three-equation New Keynesian model and who wrote it",
     "gali new keynesian three equation calvo sticky price phillips is"),
    # --- 9 ---
    ("Bernanke and Gertler's financial accelerator added a credit channel to New Keynesian DSGE: agency costs make external finance premia countercyclical, so balance-sheet shocks amplify and propagate small disturbances.", "architecture", "knowledge", False,
     [("Bernanke", "person"), ("Gertler", "person"), ("financial accelerator", "concept"), ("credit channel", "concept"), ("DSGE", "concept")],
     [("Bernanke", "financial accelerator", "AUTHORED_BY"), ("Gertler", "financial accelerator", "AUTHORED_BY"), ("financial accelerator", "DSGE", "APPLIES_TO")],
     "which mechanism lets balance-sheet frictions amplify shocks inside a DSGE model and who formalised it",
     "bernanke gertler financial accelerator credit channel dsge balance"),
    # --- 10. noise ---
    ("The campus vending machine ate another dollar and the physics grad students taped a handwritten warning to the coin slot.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("DSGE became the lingua franca of central-bank macro in the 2000s; Smets and Wouters estimated an extended New Keynesian model on euro-area data and showed it could beat Bayesian VARs at forecasting horizons out to a year.", "milestone", "knowledge", False,
     [("DSGE", "concept"), ("Smets", "person"), ("Wouters", "person"), ("Bayesian VAR", "concept"), ("euro-area", "place")],
     [("Smets", "DSGE", "USES"), ("Wouters", "DSGE", "USES")],
     "which estimated DSGE model beat Bayesian VAR forecasts on euro-area data in the 2000s",
     "dsge smets wouters bayesian var euro area forecast new keynesian"),
    # --- 12 ---
    ("The Ramsey-Cass-Koopmans model closes the Solow setup by letting households pick consumption to maximise a discounted utility integral; the Euler equation and transversality condition jointly determine the saving rate endogenously.", "architecture", "knowledge", False,
     [("Ramsey-Cass-Koopmans", "concept"), ("Solow", "person"), ("Euler equation", "concept"), ("transversality condition", "concept"), ("saving rate", "concept")],
     [("Ramsey-Cass-Koopmans", "Solow", "IMPROVES_ON")],
     "which growth model endogenises the saving rate by optimising household utility and how",
     "ramsey cass koopmans solow euler transversality saving rate utility"),
    # --- 13 ---
    ("Solow's 1956 growth paper showed that capital accumulation alone cannot sustain per-capita growth; exogenous technological progress has to do the heavy lifting once the economy reaches its steady state.", "fact", "knowledge", False,
     [("Solow", "person"), ("1956", "date"), ("steady state", "concept"), ("technological progress", "concept"), ("capital accumulation", "concept")],
     [("Solow", "steady state", "PRODUCES")],
     "which 1956 paper showed capital accumulation alone cannot drive long-run per-capita growth",
     "solow 1956 growth steady state technology exogenous capital"),
    # --- 14 ---
    ("Romer's 1990 endogenous growth paper modelled ideas as non-rival goods produced by an R&D sector; increasing returns at the aggregate level let technology be an outcome of incentives rather than a free gift.", "milestone", "knowledge", False,
     [("Romer", "person"), ("endogenous growth", "concept"), ("1990", "date"), ("R&D sector", "concept"), ("non-rival goods", "concept")],
     [("Romer", "endogenous growth", "AUTHORED_BY"), ("endogenous growth", "non-rival goods", "USES")],
     "which 1990 paper modelled technological progress as the output of a profit-motivated R&D sector",
     "romer endogenous growth 1990 r and d non rival ideas technology"),
    # --- 15 ---
    ("Lucas's 1988 Mechanics of Economic Development paper used human capital externalities rather than R&D to drive endogenous growth; the same idea animated his later work on city-level spillovers and cross-country income gaps.", "reference", "knowledge", False,
     [("Lucas", "person"), ("Mechanics of Economic Development", "publication"), ("1988", "date"), ("human capital", "concept"), ("endogenous growth", "concept")],
     [("Lucas", "Mechanics of Economic Development", "AUTHORED_BY"), ("Mechanics of Economic Development", "human capital", "USES")],
     "which 1988 Lucas paper routed endogenous growth through human capital externalities",
     "lucas 1988 mechanics human capital externality endogenous growth"),
    # --- 16 ---
    ("The original Phillips curve was an empirical regularity on UK wage inflation against unemployment from 1861 to 1957; the theoretical reinterpretation as a menu for policy came later and did not survive the 1970s.", "fact", "knowledge", False,
     [("Phillips curve", "concept"), ("UK", "place"), ("wage inflation", "concept"), ("1861", "date"), ("1957", "date")],
     [("Phillips curve", "wage inflation", "USES")],
     "which data span did Phillips originally fit and what went wrong when policy treated it as a menu",
     "phillips curve 1861 1957 uk wage inflation unemployment menu 1970"),
    # --- 17 ---
    ("Friedman and Phelps argued the Phillips curve trade-off holds only for unexpected inflation; NAIRU emerged as the long-run rate where expectations catch up and the curve becomes vertical at the natural rate of unemployment.", "fact", "knowledge", False,
     [("Friedman", "person"), ("Phelps", "person"), ("NAIRU", "concept"), ("Phillips curve", "concept"), ("natural rate", "concept")],
     [("Friedman", "NAIRU", "PRODUCES"), ("Phelps", "NAIRU", "PRODUCES")],
     "whose argument made the long-run Phillips curve vertical and introduced the NAIRU",
     "friedman phelps nairu natural rate phillips vertical expectation"),
    # --- 18 ---
    ("The Taylor rule that Stanford's John Taylor proposed in 1993 set the federal funds rate as a linear response to inflation and output gaps with a coefficient above one on inflation; it fit US Fed behaviour remarkably well.", "reference", "knowledge", False,
     [("Taylor rule", "concept"), ("John Taylor", "person"), ("1993", "date"), ("federal funds rate", "concept"), ("US Fed", "organization")],
     [("John Taylor", "Taylor rule", "AUTHORED_BY")],
     "which 1993 rule linked the federal funds rate to inflation and output gaps with a super-unitary inflation coefficient",
     "taylor rule 1993 fed funds inflation output gap coefficient stanford"),
    # --- 19 ---
    ("New Zealand adopted formal inflation targeting in 1990 under the Reserve Bank of New Zealand Act; the UK, Canada, and Sweden followed, and the regime became the default operating framework for inflation-averse central banks.", "milestone", "knowledge", False,
     [("inflation targeting", "concept"), ("New Zealand", "place"), ("1990", "date"), ("Reserve Bank of New Zealand Act", "publication"), ("UK", "place"), ("Canada", "place"), ("Sweden", "place")],
     [("New Zealand", "inflation targeting", "PRODUCES")],
     "which country first adopted formal inflation targeting and under which act did it take effect",
     "inflation targeting new zealand 1990 rbnz uk canada sweden regime"),
    # --- 20 ---
    ("Sims's 1980 Macroeconomics and Reality paper pushed the profession toward VAR analysis; identifying shocks through Choleski ordering or later long-run restrictions sidestepped the incredible identifying assumptions of structural models.", "decision", "knowledge", False,
     [("Sims", "person"), ("Macroeconomics and Reality", "publication"), ("1980", "date"), ("VAR", "concept"), ("Choleski", "method")],
     [("Sims", "VAR", "PRODUCES"), ("Sims", "Macroeconomics and Reality", "AUTHORED_BY")],
     "which 1980 Sims paper made VAR analysis the default alternative to structural macro models",
     "sims 1980 macroeconomics reality var choleski shock identification"),
    # --- 21 ---
    ("FAVAR methods by Bernanke, Boivin, and Eliasz extended the standard VAR with factors extracted from hundreds of time series; the larger information set cured the price puzzle that haunted small recursive VARs.", "architecture", "knowledge", False,
     [("FAVAR", "concept"), ("Bernanke", "person"), ("Boivin", "person"), ("Eliasz", "person"), ("price puzzle", "concept"), ("VAR", "concept")],
     [("FAVAR", "VAR", "IMPROVES_ON"), ("FAVAR", "price puzzle", "FIXES")],
     "which factor-augmented VAR extension cured the price puzzle and who proposed it",
     "favar bernanke boivin eliasz factor var price puzzle information"),
    # --- 22 ---
    ("Bernanke and Blinder's 1988 paper on the credit channel pointed at bank-loan supply as a second transmission route for monetary policy beyond the standard interest-rate channel, especially in bank-dependent sectors.", "reference", "knowledge", False,
     [("Bernanke", "person"), ("Blinder", "person"), ("credit channel", "concept"), ("1988", "date"), ("interest-rate channel", "concept")],
     [("Bernanke", "credit channel", "AUTHORED_BY"), ("Blinder", "credit channel", "AUTHORED_BY")],
     "which 1988 paper identified a bank-lending credit channel alongside the interest-rate channel",
     "bernanke blinder credit channel 1988 bank loan monetary transmission"),
    # --- 23 ---
    ("Reinhart and Rogoff's This Time Is Different compiled eight centuries of debt, default, and inflation episodes; the follow-up Growth in a Time of Debt claimed a 90 percent public-debt threshold, which a later spreadsheet error partially walked back.", "fact", "knowledge", False,
     [("Reinhart", "person"), ("Rogoff", "person"), ("This Time Is Different", "publication"), ("Growth in a Time of Debt", "publication"), ("90 percent", "concept")],
     [("Reinhart", "This Time Is Different", "AUTHORED_BY"), ("Rogoff", "This Time Is Different", "AUTHORED_BY")],
     "which Reinhart Rogoff pair of works proposed the 90 percent debt threshold and what undermined it",
     "reinhart rogoff this time different growth debt 90 percent spreadsheet"),
    # --- 24 ---
    ("Piketty's Capital in the Twenty-First Century argued that when r exceeds g for prolonged periods, the capital share and top wealth shares grow mechanically; the WTID database behind the claims made the empirics auditable.", "reference", "knowledge", False,
     [("Piketty", "person"), ("Capital in the Twenty-First Century", "publication"), ("WTID", "tool"), ("r exceeds g", "concept")],
     [("Piketty", "Capital in the Twenty-First Century", "AUTHORED_BY"), ("Piketty", "WTID", "USES")],
     "which Piketty book built its inequality thesis on r exceeds g and an auditable database",
     "piketty capital twenty first century wtid r g wealth share"),
    # --- 25 ---
    ("Blanchard served as IMF chief economist during the 2008 crisis and spent years coaxing the profession toward fiscal multiplier estimates well above one in downturns, reversing the pre-crisis near-consensus on small multipliers.", "decision", "knowledge", False,
     [("Blanchard", "person"), ("IMF", "organization"), ("fiscal multiplier", "concept"), ("2008 crisis", "event")],
     [("Blanchard", "IMF", "WORKS_AT"), ("Blanchard", "fiscal multiplier", "AUTHORED_BY")],
     "which IMF chief economist pushed large downturn fiscal multipliers after the 2008 crisis",
     "blanchard imf chief economist fiscal multiplier 2008 crisis"),
    # --- 26 ---
    ("Mankiw's undergraduate Macroeconomics textbook became the default intermediate course text in the United States; successive editions tracked the profession's drift from IS-LM as centrepiece to three-equation New Keynesian teaching modules.", "fact", "knowledge", False,
     [("Mankiw", "person"), ("Macroeconomics", "publication"), ("IS-LM", "concept"), ("New Keynesian", "concept"), ("United States", "place")],
     [("Mankiw", "Macroeconomics", "AUTHORED_BY")],
     "which Mankiw textbook's successive editions migrated US intermediate courses from IS-LM to New Keynesian teaching",
     "mankiw macroeconomics textbook intermediate is lm new keynesian us"),
    # --- 27 ---
    ("Acemoglu's Introduction to Modern Economic Growth is a graduate-level brick; it covers Solow, Ramsey-Cass-Koopmans, overlapping generations, endogenous growth, directed technical change, and political-economy models of long-run development in one volume.", "reference", "knowledge", False,
     [("Acemoglu", "person"), ("Introduction to Modern Economic Growth", "publication"), ("overlapping generations", "concept"), ("directed technical change", "concept")],
     [("Acemoglu", "Introduction to Modern Economic Growth", "AUTHORED_BY")],
     "which Acemoglu graduate text covers Solow through directed technical change and political-economy growth in one volume",
     "acemoglu introduction modern economic growth graduate solow overlapping"),
    # --- 28 ---
    ("Stiglitz's public economics work on information asymmetries reshaped the microfoundations macroeconomists were willing to admit; adverse selection and moral hazard became respectable building blocks in models of credit rationing and unemployment.", "architecture", "knowledge", False,
     [("Stiglitz", "person"), ("public economics", "concept"), ("information asymmetries", "concept"), ("adverse selection", "concept"), ("moral hazard", "concept"), ("credit rationing", "concept")],
     [("Stiglitz", "information asymmetries", "AUTHORED_BY"), ("information asymmetries", "credit rationing", "APPLIES_TO")],
     "whose information-asymmetry work put adverse selection and moral hazard into serious macro models",
     "stiglitz public economics asymmetric information adverse selection moral"),
    # --- 29 ---
    ("The zero lower bound on nominal interest rates became the binding constraint for the US Fed, the ECB, and the Bank of Japan after 2008; forward guidance and quantitative easing filled in for rate cuts that could not happen.", "problem", "knowledge", False,
     [("zero lower bound", "concept"), ("US Fed", "organization"), ("ECB", "organization"), ("Bank of Japan", "organization"), ("forward guidance", "concept"), ("quantitative easing", "concept")],
     [("forward guidance", "zero lower bound", "FIXES"), ("quantitative easing", "zero lower bound", "FIXES")],
     "which post-2008 constraint forced central banks to rely on forward guidance and quantitative easing",
     "zero lower bound fed ecb boj 2008 forward guidance qe rate"),
    # --- 30 ---
    ("Modigliani's life-cycle hypothesis and Friedman's permanent-income hypothesis both argued consumption tracks expected lifetime resources rather than current income; the implications for fiscal multipliers are profound and still contested.", "fact", "knowledge", False,
     [("Modigliani", "person"), ("life-cycle hypothesis", "concept"), ("Friedman", "person"), ("permanent-income hypothesis", "concept"), ("fiscal multiplier", "concept")],
     [("Modigliani", "life-cycle hypothesis", "AUTHORED_BY"), ("Friedman", "permanent-income hypothesis", "AUTHORED_BY")],
     "which two hypotheses argued consumption tracks lifetime resources and why it matters for fiscal multipliers",
     "modigliani life cycle friedman permanent income consumption fiscal"),
    # --- 31 ---
    ("Kydland and Prescott's 1977 time-inconsistency paper showed that discretion without commitment yields a systematic inflation bias; the result became the canonical argument for independent central banks bound by explicit mandates.", "decision", "knowledge", False,
     [("Kydland", "person"), ("Prescott", "person"), ("1977", "date"), ("time-inconsistency", "concept"), ("inflation bias", "concept"), ("central bank", "organization")],
     [("Kydland", "time-inconsistency", "PRODUCES"), ("Prescott", "time-inconsistency", "PRODUCES")],
     "which 1977 Kydland-Prescott result motivated independent central banks with explicit mandates",
     "kydland prescott 1977 time inconsistency inflation bias commitment"),
    # --- 32 ---
    ("Calvo pricing, proposed by Guillermo Calvo, assumes a random fraction of firms reset prices each period; the resulting aggregate-supply curve has a forward-looking term in expected inflation plus a current marginal cost driver, which became the backbone of New Keynesian DSGE.", "architecture", "knowledge", False,
     [("Calvo pricing", "concept"), ("Guillermo Calvo", "person"), ("marginal cost", "concept"), ("New Keynesian", "concept"), ("DSGE", "concept")],
     [("Guillermo Calvo", "Calvo pricing", "AUTHORED_BY"), ("Calvo pricing", "New Keynesian", "APPLIES_TO")],
     "which price-setting assumption drives the New Keynesian Phillips curve and who authored it",
     "calvo pricing random reset forward inflation marginal cost nk dsge"),
    # --- 33 ---
    ("Sargent and Wallace's unpleasant monetarist arithmetic showed that if the fiscal authority runs persistent deficits, the monetary authority eventually has to monetise them; central-bank independence alone cannot guarantee price stability.", "problem", "knowledge", False,
     [("Sargent", "person"), ("Wallace", "person"), ("unpleasant monetarist arithmetic", "concept"), ("fiscal authority", "concept"), ("price stability", "concept")],
     [("Sargent", "unpleasant monetarist arithmetic", "AUTHORED_BY"), ("Wallace", "unpleasant monetarist arithmetic", "AUTHORED_BY")],
     "which Sargent-Wallace result shows fiscal deficits can swamp central-bank independence",
     "sargent wallace unpleasant monetarist arithmetic fiscal monetise"),
    # --- 34 ---
    ("The rational expectations hypothesis, formalised by Muth in 1961 and weaponised by Lucas in the 1970s, replaced adaptive expectations in serious macro; forecasts now had to be consistent with the model the modeller was running.", "decision", "knowledge", False,
     [("rational expectations", "concept"), ("Muth", "person"), ("1961", "date"), ("Lucas", "person"), ("adaptive expectations", "concept")],
     [("Muth", "rational expectations", "PRODUCES"), ("rational expectations", "adaptive expectations", "REPLACES")],
     "which expectations formalism did Lucas use to displace adaptive expectations and who first proposed it",
     "rational expectations muth 1961 lucas adaptive macro forecast"),
    # --- 35 ---
    ("Diamond-Mortensen-Pissarides search-and-matching theory explained equilibrium unemployment as the output of a matching function with vacancies and unemployed workers; the 2010 Nobel went to that framework.", "milestone", "knowledge", False,
     [("Diamond", "person"), ("Mortensen", "person"), ("Pissarides", "person"), ("search-and-matching", "concept"), ("Nobel", "concept"), ("2010", "date")],
     [("Diamond", "search-and-matching", "AUTHORED_BY"), ("Mortensen", "search-and-matching", "AUTHORED_BY"), ("Pissarides", "search-and-matching", "AUTHORED_BY")],
     "which 2010 Nobel framework explained equilibrium unemployment through a matching function",
     "diamond mortensen pissarides search matching unemployment nobel 2010"),
    # --- 36 ---
    ("Eggertsson and Krugman revived the liquidity trap in a New Keynesian setting with borrowing constraints; at the zero lower bound, deleveraging shocks make even standard multipliers bigger and paradox of thrift results return.", "architecture", "knowledge", False,
     [("Eggertsson", "person"), ("Krugman", "person"), ("liquidity trap", "concept"), ("zero lower bound", "concept"), ("paradox of thrift", "concept")],
     [("Eggertsson", "liquidity trap", "AUTHORED_BY"), ("Krugman", "liquidity trap", "AUTHORED_BY")],
     "which New Keynesian revival of the liquidity trap brought back the paradox of thrift at the zero lower bound",
     "eggertsson krugman liquidity trap nk zlb paradox thrift multiplier"),
    # --- 37 ---
    ("Okun's law is an empirical rule of thumb that a one-point rise in unemployment tracks about a two-point fall in output growth relative to potential; it holds up reasonably in US data but wobbles across countries and decades.", "fact", "knowledge", False,
     [("Okun's law", "concept"), ("unemployment", "concept"), ("output growth", "concept"), ("US", "place")],
     [("Okun's law", "unemployment", "USES")],
     "which empirical rule links unemployment changes to output-growth gaps and where does it hold best",
     "okun law unemployment output gap growth us decade country"),
    # --- 38 ---
    ("The Fisher equation nominal equals real plus expected inflation is the closure device that lets the Taylor rule pin down real rates; without it, changes in the nominal policy rate cannot be mapped to aggregate demand effects.", "fact", "knowledge", False,
     [("Fisher equation", "concept"), ("nominal", "concept"), ("real", "concept"), ("Taylor rule", "concept"), ("aggregate demand", "concept")],
     [("Taylor rule", "Fisher equation", "USES")],
     "which identity bridges nominal and real rates so the Taylor rule can move aggregate demand",
     "fisher equation nominal real expected inflation taylor rule demand"),
    # --- 39 ---
    ("Barro's 1974 Ricardian equivalence argument showed that with infinite-horizon altruistic households, debt-financed tax cuts are saved rather than spent; dynasties internalise the future tax liability and current consumption does not move.", "reference", "knowledge", False,
     [("Barro", "person"), ("1974", "date"), ("Ricardian equivalence", "concept"), ("tax cuts", "concept"), ("consumption", "concept")],
     [("Barro", "Ricardian equivalence", "AUTHORED_BY")],
     "which 1974 Barro argument claims debt-financed tax cuts get saved rather than spent",
     "barro 1974 ricardian equivalence tax cut debt consumption dynasty"),
    # --- 40 ---
    ("The Blanchard-Kahn 1980 paper gave rational expectations modellers the solvability conditions for linear models with forward-looking variables; the count of unstable eigenvalues has to match the count of jump variables or no solution exists.", "architecture", "knowledge", False,
     [("Blanchard-Kahn", "concept"), ("1980", "date"), ("rational expectations", "concept"), ("eigenvalues", "concept"), ("jump variables", "concept")],
     [("Blanchard-Kahn", "rational expectations", "APPLIES_TO")],
     "which 1980 conditions tell rational-expectations modellers when a linear forward-looking system has a solution",
     "blanchard kahn 1980 rational expectations eigenvalue jump variable"),
    # --- 41 ---
    ("The neo-Fisherian puzzle observes that sustained low policy rates in Japan and the euro area did not raise inflation as standard New Keynesian models implied; Cochrane and others pushed a reinterpretation where raising rates raises inflation.", "problem", "knowledge", False,
     [("neo-Fisherian", "concept"), ("Japan", "place"), ("euro area", "place"), ("Cochrane", "person"), ("New Keynesian", "concept")],
     [("Cochrane", "neo-Fisherian", "AUTHORED_BY")],
     "which reinterpretation of the Fisher relation grew out of the failure of low rates to raise inflation in Japan and Europe",
     "neo fisherian japan euro area cochrane nk low rate inflation"),
    # --- 42 ---
    ("HANK models, which stands for Heterogeneous Agent New Keynesian and were built by Kaplan, Moll, and Violante, add idiosyncratic income risk and a distribution of balance sheets on top of the New Keynesian core; marginal propensities to consume vary sharply across households.", "architecture", "knowledge", False,
     [("HANK", "concept"), ("Kaplan", "person"), ("Moll", "person"), ("Violante", "person"), ("New Keynesian", "concept")],
     [("Kaplan", "HANK", "AUTHORED_BY"), ("Moll", "HANK", "AUTHORED_BY"), ("Violante", "HANK", "AUTHORED_BY"), ("HANK", "New Keynesian", "IMPROVES_ON")],
     "which heterogeneous-agent extension of New Keynesian macro lets marginal propensities to consume differ across households",
     "hank kaplan moll violante heterogeneous mpc new keynesian distribution"),
    # --- 43. noise ---
    ("The library coffee cart is down to two kinds of pastry and the queue at 3 pm still wraps around the atrium.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("The Great Moderation from 1984 through roughly 2007 saw US output and inflation volatility fall by half; whether better monetary policy or structural luck drove it remained a live debate right up until the 2008 crisis ended the moderation.", "fact", "knowledge", False,
     [("Great Moderation", "event"), ("1984", "date"), ("2007", "date"), ("US", "place"), ("2008 crisis", "event")],
     [("Great Moderation", "2008 crisis", "REPLACES")],
     "which 1984 to 2007 period cut US macro volatility in half and what ended it",
     "great moderation 1984 2007 us volatility monetary luck 2008"),
    # --- 45 ---
    ("Reinhart, Reinhart, and Rogoff documented that post-crisis recovery paths systematically run below pre-crisis growth rates for roughly a decade; the paper shaped expectations about the slow US recovery after 2008.", "reference", "knowledge", False,
     [("Reinhart", "person"), ("Rogoff", "person"), ("post-crisis recovery", "concept"), ("2008", "date"), ("US", "place")],
     [("Reinhart", "post-crisis recovery", "AUTHORED_BY"), ("Rogoff", "post-crisis recovery", "AUTHORED_BY")],
     "which post-crisis-recovery paper by Reinhart and Rogoff shaped expectations after 2008",
     "reinhart rogoff post crisis recovery decade slow 2008 us"),
    # --- 46 ---
    ("John Taylor himself preferred a rule-based monetary regime; he criticised the Fed's discretionary deviations from the simple Taylor rule during the 2003-2005 low-rate period as a contributor to the housing boom that preceded the 2008 crisis.", "preference", "knowledge", False,
     [("John Taylor", "person"), ("Taylor rule", "concept"), ("Fed", "organization"), ("2003", "date"), ("2005", "date"), ("2008 crisis", "event")],
     [("John Taylor", "Taylor rule", "PREFERS")],
     "whose rule-based preference blamed Fed deviations in 2003 to 2005 for the housing boom",
     "taylor rule fed 2003 2005 deviation housing boom 2008 discretion"),
    # --- 47 ---
    ("Piketty prefers progressive wealth taxation over income taxation as the lever against r exceeds g dynamics; the policy recommendation is controversial and the practical design questions around enforcement remain open.", "preference", "knowledge", False,
     [("Piketty", "person"), ("wealth taxation", "concept"), ("income taxation", "concept"), ("r exceeds g", "concept")],
     [("Piketty", "wealth taxation", "PREFERS"), ("Piketty", "income taxation", "REPLACES")],
     "which tax instrument does Piketty prefer against r exceeds g dynamics",
     "piketty wealth tax income progressive r g inequality enforcement"),
    # --- 48 ---
    ("Friedman preferred rules over discretion; his proposed k-percent rule fixed money-supply growth regardless of current conditions, and the preference extended to floating exchange rates and a negative income tax.", "preference", "knowledge", False,
     [("Friedman", "person"), ("k-percent rule", "concept"), ("floating exchange rates", "concept"), ("negative income tax", "concept")],
     [("Friedman", "k-percent rule", "PREFERS"), ("Friedman", "floating exchange rates", "PREFERS")],
     "which three rule-based positions did Friedman consistently prefer over discretion",
     "friedman rules discretion k percent float exchange negative income"),
    # --- 49 ---
    ("Stiglitz preferred activist fiscal policy and heavier financial regulation to the Washington Consensus prescriptions he had helped articulate at the World Bank; the preference hardened after the East Asian crisis of 1997.", "preference", "knowledge", False,
     [("Stiglitz", "person"), ("Washington Consensus", "concept"), ("World Bank", "organization"), ("East Asian crisis", "event"), ("1997", "date")],
     [("Stiglitz", "Washington Consensus", "REPLACES"), ("Stiglitz", "World Bank", "WORKS_AT")],
     "whose post-1997 position flipped against the Washington Consensus toward fiscal activism",
     "stiglitz washington consensus world bank east asian 1997 fiscal"),
    # --- 50 ---
    ("The 2008 financial crisis terminated the Great Moderation narrative, triggered coordinated fiscal stimulus across the G20, and reopened debates on liquidity traps, financial frictions, and macroprudential regulation that had seemed settled.", "milestone", "knowledge", False,
     [("2008 financial crisis", "event"), ("Great Moderation", "event"), ("G20", "organization"), ("liquidity trap", "concept"), ("macroprudential regulation", "concept")],
     [("2008 financial crisis", "Great Moderation", "REPLACES"), ("2008 financial crisis", "macroprudential regulation", "PRODUCES")],
     "which 2008 event ended the Great Moderation and reopened debates on liquidity traps and macroprudential regulation",
     "2008 financial crisis great moderation g20 liquidity trap macroprudential"),
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
