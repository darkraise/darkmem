"""One-off emitter for classification top-up batch-017 — contrastive_reference_fact mode, economics slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_017.tmp.jsonl with ids class-01601..01700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_017.tmp.jsonl"
ID_OFFSET = 1600
PAIR_OFFSET = 550

# Each pair is: (ref_text, ref_domain, fact_text, fact_domain)
# ref_text MUST contain a citable source (named paper + year, DOI, named journal, named working paper).
# fact_text MUST NOT contain a citation — it is the same underlying economic claim stated without the source.
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. Arrow impossibility (social choice / micro theory)
    (
        "Kenneth Arrow, 'Social Choice and Individual Values' (Cowles Foundation Monograph 12, Wiley, 1951), proved that no social welfare function can simultaneously satisfy unrestricted domain, non-dictatorship, Pareto efficiency, and independence of irrelevant alternatives when there are at least three alternatives.",
        "knowledge",
        "No voting rule over three or more alternatives can jointly satisfy unrestricted domain, non-dictatorship, the Pareto criterion, and independence of irrelevant alternatives.",
        "knowledge",
    ),
    # 2. Fama-French three-factor model (financial econ)
    (
        "Fama and French, 'Common risk factors in the returns on stocks and bonds', Journal of Financial Economics 33 (1993) 3-56, introduced the three-factor model augmenting the market factor with size (SMB) and value (HML) factors.",
        "knowledge",
        "Cross-sectional variation in average stock returns is captured reasonably well by three common risk factors: the market excess return, a small-minus-big size factor, and a high-minus-low book-to-market factor.",
        "knowledge",
    ),
    # 3. Reinhart-Rogoff debt-growth (macro / public finance) — note the dataset dispute
    (
        "Reinhart and Rogoff, 'Growth in a Time of Debt', American Economic Review 100 (2010) 573-578, reported that median real GDP growth falls noticeably once gross public debt exceeds roughly 90 percent of GDP, a finding later revised after spreadsheet errors were identified by Herndon, Ash, and Pollin (Cambridge Journal of Economics 2014).",
        "knowledge",
        "Cross-country data show a negative correlation between very high public debt-to-GDP ratios and subsequent real growth, though the strength and threshold of this relationship remain contested.",
        "knowledge",
    ),
    # 4. Card-Krueger minimum wage (labour econ)
    (
        "Card and Krueger, 'Minimum Wages and Employment: A Case Study of the Fast-Food Industry in New Jersey and Pennsylvania', American Economic Review 84 (1994) 772-793, found no evidence that the 1992 New Jersey minimum wage increase reduced fast-food employment relative to Pennsylvania.",
        "knowledge",
        "A natural experiment comparing fast-food employment in New Jersey and Pennsylvania around a minimum wage increase found no meaningful employment reduction in the treated state.",
        "knowledge",
    ),
    # 5. Acemoglu-Johnson-Robinson colonial origins (development econ)
    (
        "Acemoglu, Johnson, and Robinson, 'The Colonial Origins of Comparative Development: An Empirical Investigation', American Economic Review 91 (2001) 1369-1401, used settler mortality as an instrument to identify a large causal effect of institutions on long-run per-capita income.",
        "knowledge",
        "Differences in long-run income across former colonies are largely explained by differences in early extractive versus inclusive institutions, rather than by geography alone.",
        "knowledge",
    ),
    # 6. Kahneman-Tversky prospect theory (behavioural econ)
    (
        "Kahneman and Tversky, 'Prospect Theory: An Analysis of Decision under Risk', Econometrica 47 (1979) 263-291, documented loss aversion and a value function concave in gains and convex in losses, contrary to expected utility.",
        "knowledge",
        "People evaluate risky prospects relative to a reference point and treat losses as roughly twice as painful as equivalent gains are pleasurable.",
        "knowledge",
    ),
    # 7. Mincer earnings equation (labour econ)
    (
        "Jacob Mincer, 'Schooling, Experience, and Earnings' (NBER, 1974), estimated log-earnings as a linear function of years of schooling and a quadratic in experience, the specification now known as the Mincer equation.",
        "knowledge",
        "Log hourly earnings are approximately linear in years of schooling and concave in potential labour market experience, with each additional year of schooling typically associated with about an eight to ten percent earnings premium.",
        "knowledge",
    ),
    # 8. Solow growth model (macro / growth)
    (
        "Robert Solow, 'A Contribution to the Theory of Economic Growth', Quarterly Journal of Economics 70 (1956) 65-94, introduced the neoclassical one-sector growth model with diminishing returns to capital and exogenous technical progress.",
        "knowledge",
        "In a one-sector neoclassical growth model with diminishing returns to capital, long-run growth in output per worker is driven by exogenous technological progress rather than by capital accumulation alone.",
        "knowledge",
    ),
    # 9. Lucas critique (macroeconometrics)
    (
        "Robert E. Lucas Jr., 'Econometric Policy Evaluation: A Critique', Carnegie-Rochester Conference Series on Public Policy 1 (1976) 19-46, argued that reduced-form parameters estimated under one policy regime are generally not invariant to policy changes.",
        "knowledge",
        "Econometric models whose coefficients are not derived from agents' structural optimization problems will generally mislead policy evaluation because agents adjust expectations when policy changes.",
        "knowledge",
    ),
    # 10. Black-Scholes option pricing (financial econ)
    (
        "Black and Scholes, 'The Pricing of Options and Corporate Liabilities', Journal of Political Economy 81 (1973) 637-654, derived the closed-form price of a European option under geometric Brownian motion and no arbitrage.",
        "knowledge",
        "Under geometric Brownian motion for the underlying asset and a constant risk-free rate, the no-arbitrage price of a European call option admits a closed-form solution involving the cumulative standard normal distribution.",
        "knowledge",
    ),
    # 11. Modigliani-Miller capital structure (corporate finance)
    (
        "Modigliani and Miller, 'The Cost of Capital, Corporation Finance and the Theory of Investment', American Economic Review 48 (1958) 261-297, showed that in frictionless markets firm value is invariant to capital structure.",
        "knowledge",
        "In a world without taxes, bankruptcy costs, or information asymmetries, the total value of a firm is independent of how that firm is financed through debt or equity.",
        "knowledge",
    ),
    # 12. Nash equilibrium (game theory)
    (
        "John Nash, 'Equilibrium Points in N-Person Games', PNAS 36 (1950) 48-49, proved existence of mixed-strategy equilibria in every finite n-player non-cooperative game.",
        "knowledge",
        "Every finite non-cooperative game with a finite number of players and strategies admits at least one equilibrium in which no player can benefit by unilaterally deviating, possibly in mixed strategies.",
        "knowledge",
    ),
    # 13. Akerlof lemons (information economics)
    (
        "George Akerlof, 'The Market for Lemons: Quality Uncertainty and the Market Mechanism', Quarterly Journal of Economics 84 (1970) 488-500, showed that asymmetric information about quality can cause adverse selection and market unraveling.",
        "knowledge",
        "When sellers know product quality but buyers do not, adverse selection can drive high-quality goods out of the market even when mutually beneficial trades exist.",
        "knowledge",
    ),
    # 14. Spence signalling (labour / information econ)
    (
        "Michael Spence, 'Job Market Signaling', Quarterly Journal of Economics 87 (1973) 355-374, formalized education as a signal of innate productivity in a labour market with asymmetric information.",
        "knowledge",
        "Costly education can serve as a signal of underlying worker productivity in labour markets with asymmetric information, even when schooling itself adds no human capital.",
        "knowledge",
    ),
    # 15. Diamond-Dybvig bank runs (financial econ)
    (
        "Diamond and Dybvig, 'Bank Runs, Deposit Insurance, and Liquidity', Journal of Political Economy 91 (1983) 401-419, modeled banks as providing maturity transformation with multiple equilibria, one of which is a self-fulfilling run.",
        "knowledge",
        "Demand-deposit banks that transform illiquid long-term assets into liquid liabilities are vulnerable to self-fulfilling runs, which deposit insurance can eliminate by ruling out the bad equilibrium.",
        "knowledge",
    ),
    # 16. Vickrey auction (mechanism design)
    (
        "William Vickrey, 'Counterspeculation, Auctions, and Competitive Sealed Tenders', Journal of Finance 16 (1961) 8-37, showed that the sealed-bid second-price auction has truthful bidding as a dominant strategy.",
        "knowledge",
        "In a sealed-bid second-price auction with private values, bidding one's true valuation is a weakly dominant strategy.",
        "knowledge",
    ),
    # 17. Gale-Shapley deferred acceptance (matching / mechanism design)
    (
        "Gale and Shapley, 'College Admissions and the Stability of Marriage', American Mathematical Monthly 69 (1962) 9-15, introduced the deferred acceptance algorithm producing a stable matching in two-sided markets.",
        "knowledge",
        "The deferred acceptance algorithm always produces a stable matching in a two-sided market with strict preferences, and the outcome is optimal for the proposing side.",
        "knowledge",
    ),
    # 18. Heckman selection (econometrics)
    (
        "James Heckman, 'Sample Selection Bias as a Specification Error', Econometrica 47 (1979) 153-161, proposed a two-step estimator correcting for non-random sample selection using the inverse Mills ratio.",
        "knowledge",
        "Ordinary least squares regression on a non-randomly selected sample produces biased estimates unless the selection process is modeled explicitly, for example by including a correction term constructed from a first-stage probit.",
        "knowledge",
    ),
    # 19. Angrist-Imbens LATE (econometrics)
    (
        "Imbens and Angrist, 'Identification and Estimation of Local Average Treatment Effects', Econometrica 62 (1994) 467-475, showed that an instrumental variable identifies the local average treatment effect for compliers under monotonicity.",
        "knowledge",
        "Under monotonicity, an instrumental variables estimator recovers the average treatment effect for those subjects whose treatment status is shifted by the instrument, rather than for the full population.",
        "knowledge",
    ),
    # 20. Dickey-Fuller unit root (time-series econometrics)
    (
        "Dickey and Fuller, 'Distribution of the Estimators for Autoregressive Time Series With a Unit Root', Journal of the American Statistical Association 74 (1979) 427-431, derived the non-standard limiting distribution of the t-statistic for the unit-root null.",
        "knowledge",
        "The t-statistic for testing a unit root in an autoregressive process does not follow a standard normal distribution under the null, so tabulated non-standard critical values must be used.",
        "knowledge",
    ),
    # 21. Engle ARCH (financial econometrics)
    (
        "Robert Engle, 'Autoregressive Conditional Heteroscedasticity with Estimates of the Variance of United Kingdom Inflation', Econometrica 50 (1982) 987-1007, introduced the ARCH family of models for time-varying conditional variances.",
        "knowledge",
        "The conditional variance of many financial and macroeconomic time series is itself time-varying and can be modeled as a function of past squared innovations.",
        "knowledge",
    ),
    # 22. Granger cointegration (time series)
    (
        "Engle and Granger, 'Co-Integration and Error Correction: Representation, Estimation, and Testing', Econometrica 55 (1987) 251-276, established the equivalence between cointegrated systems and error-correction representations.",
        "knowledge",
        "When two non-stationary time series share a common stochastic trend, their deviations from that trend are stationary and can be represented as an error-correction mechanism.",
        "knowledge",
    ),
    # 23. Pissarides search-matching (labour / macro)
    (
        "Mortensen and Pissarides, 'Job Creation and Job Destruction in the Theory of Unemployment', Review of Economic Studies 61 (1994) 397-415, developed the canonical search-and-matching model of equilibrium unemployment.",
        "knowledge",
        "Equilibrium unemployment arises naturally from a search and matching friction in which vacancies and unemployed workers meet through a stochastic matching function.",
        "knowledge",
    ),
    # 24. Taylor rule (monetary policy)
    (
        "John B. Taylor, 'Discretion versus policy rules in practice', Carnegie-Rochester Conference Series on Public Policy 39 (1993) 195-214, proposed a simple rule setting the federal funds rate as a function of inflation and the output gap.",
        "knowledge",
        "A simple monetary policy rule that moves the short-term nominal interest rate more than one-for-one with inflation and in the same direction as the output gap tracks historical Federal Reserve behaviour reasonably well.",
        "knowledge",
    ),
    # 25. Friedman permanent income (consumption)
    (
        "Milton Friedman, 'A Theory of the Consumption Function' (NBER, Princeton University Press, 1957), formulated the permanent income hypothesis, whereby consumption depends on expected long-run income rather than current income.",
        "knowledge",
        "Households smooth consumption against transitory income fluctuations, so consumption responds much more strongly to changes in perceived permanent income than to transitory shocks.",
        "knowledge",
    ),
    # 26. Lucas-Prescott rational expectations (macro)
    (
        "Lucas and Prescott, 'Investment Under Uncertainty', Econometrica 39 (1971) 659-681, solved a dynamic rational-expectations equilibrium model of industry investment under stochastic demand.",
        "knowledge",
        "In a rational-expectations competitive equilibrium, firms' investment decisions are consistent with the equilibrium stochastic process they generate for prices.",
        "knowledge",
    ),
    # 27. Piketty-Saez top income shares (distribution / public econ)
    (
        "Piketty and Saez, 'Income Inequality in the United States, 1913-1998', Quarterly Journal of Economics 118 (2003) 1-39, reconstructed the long-run share of income accruing to the top one percent from US tax return data.",
        "knowledge",
        "The share of total US pre-tax income going to the top one percent of earners fell sharply from the 1930s through the 1970s and then rose again from the 1980s onwards, approaching pre-Depression levels.",
        "knowledge",
    ),
    # 28. Chetty geography of opportunity (public / labour econ)
    (
        "Chetty, Hendren, Kline, and Saez, 'Where is the Land of Opportunity? The Geography of Intergenerational Mobility in the United States', Quarterly Journal of Economics 129 (2014) 1553-1623, used de-identified tax records covering tens of millions of children to map intergenerational mobility across US commuting zones.",
        "knowledge",
        "Intergenerational income mobility in the United States varies substantially across regions, with some metropolitan areas exhibiting mobility rates comparable to the most mobile European countries and others much lower.",
        "knowledge",
    ),
    # 29. Banerjee-Duflo RCTs in development (development econ)
    (
        "Banerjee, Duflo, Glennerster, and Kinnan, 'The Miracle of Microfinance? Evidence from a Randomized Evaluation', American Economic Journal: Applied Economics 7 (2015) 22-53, reported modest impacts of microcredit access in Hyderabad.",
        "knowledge",
        "Randomized evaluations of microcredit in low-income urban settings have generally found modest effects on business creation and no transformative effects on household consumption or welfare.",
        "knowledge",
    ),
    # 30. Ostrom commons (institutional / environmental econ)
    (
        "Elinor Ostrom, 'Governing the Commons: The Evolution of Institutions for Collective Action' (Cambridge University Press, 1990), documented eight design principles under which communities successfully self-govern common-pool resources.",
        "knowledge",
        "Common-pool resources such as fisheries, forests, and irrigation systems can be sustainably managed by user communities themselves when institutions satisfy design principles such as clear boundaries, graduated sanctions, and collective-choice arrangements.",
        "knowledge",
    ),
    # 31. Nordhaus DICE (environmental econ / climate)
    (
        "William Nordhaus, 'An Optimal Transition Path for Controlling Greenhouse Gases', Science 258 (1992) 1315-1319, introduced the DICE integrated assessment model coupling a Ramsey growth model with a climate module.",
        "knowledge",
        "An integrated assessment model that couples a neoclassical growth framework with a simple carbon-cycle and temperature module can be used to compute optimal paths of emissions abatement and a social cost of carbon.",
        "knowledge",
    ),
    # 32. Weitzman dismal theorem (environmental econ)
    (
        "Martin Weitzman, 'On Modeling and Interpreting the Economics of Catastrophic Climate Change', Review of Economics and Statistics 91 (2009) 1-19, argued that fat-tailed uncertainty about climate sensitivity can dominate standard cost-benefit analysis.",
        "knowledge",
        "Standard cost-benefit analysis of climate policy can give misleading results when the distribution of possible climate damages has a sufficiently fat right tail, because expected marginal utility losses can be unbounded.",
        "knowledge",
    ),
    # 33. Krugman new trade theory (international trade)
    (
        "Paul Krugman, 'Increasing Returns, Monopolistic Competition, and International Trade', Journal of International Economics 9 (1979) 469-479, developed a model of intra-industry trade driven by love-of-variety and increasing returns.",
        "knowledge",
        "Trade between similar countries in similar products can be explained by consumer preferences for variety combined with firm-level increasing returns to scale, even in the absence of comparative advantage.",
        "knowledge",
    ),
    # 34. Melitz heterogeneous firms (trade)
    (
        "Marc Melitz, 'The Impact of Trade on Intra-Industry Reallocations and Aggregate Industry Productivity', Econometrica 71 (2003) 1695-1725, introduced firm heterogeneity into trade theory, with only the most productive firms exporting.",
        "knowledge",
        "Trade liberalization reallocates market share toward the most productive firms within an industry, raising aggregate industry productivity through selection into exporting.",
        "knowledge",
    ),
    # 35. Autor-Dorn-Hanson China shock (trade / labour)
    (
        "Autor, Dorn, and Hanson, 'The China Syndrome: Local Labor Market Effects of Import Competition in the United States', American Economic Review 103 (2013) 2121-2168, estimated the impact of rising Chinese import competition on US commuting zones.",
        "knowledge",
        "Rising import competition from China between 1990 and 2007 caused significant and persistent declines in manufacturing employment, wages, and labour force participation in the most exposed US local labour markets.",
        "knowledge",
    ),
    # 36. Tiebout local public goods (public finance)
    (
        "Charles Tiebout, 'A Pure Theory of Local Expenditures', Journal of Political Economy 64 (1956) 416-424, argued that mobile households reveal their preferences for local public goods by sorting across jurisdictions.",
        "knowledge",
        "When households can freely move across jurisdictions offering different bundles of local public goods and taxes, their location choices can efficiently reveal preferences and support an efficient provision of those goods.",
        "knowledge",
    ),
    # 37. Feldstein saving-investment puzzle (international finance)
    (
        "Feldstein and Horioka, 'Domestic Saving and International Capital Flows', Economic Journal 90 (1980) 314-329, documented a high correlation between national saving and domestic investment rates among OECD economies.",
        "knowledge",
        "Despite apparent international capital mobility, national saving rates and domestic investment rates are strongly correlated across advanced economies.",
        "knowledge",
    ),
    # 38. Bernanke-Gertler financial accelerator (macro / monetary)
    (
        "Bernanke, Gertler, and Gilchrist, 'The Financial Accelerator in a Quantitative Business Cycle Framework', in Handbook of Macroeconomics Vol. 1C (Elsevier, 1999) 1341-1393, embedded costly external finance in a DSGE model.",
        "knowledge",
        "Balance-sheet frictions that make external finance more costly than internal funds amplify and propagate shocks through the business cycle.",
        "knowledge",
    ),
    # 39. Shiller excess volatility (asset pricing)
    (
        "Robert Shiller, 'Do Stock Prices Move Too Much to be Justified by Subsequent Changes in Dividends?', American Economic Review 71 (1981) 421-436, showed that stock price volatility far exceeds that implied by the present-value model with constant discount rates.",
        "knowledge",
        "Aggregate US stock prices have historically been far more volatile than the ex-post present value of dividends, challenging simple constant-discount-rate efficient markets models.",
        "knowledge",
    ),
    # 40. Mehra-Prescott equity premium puzzle (asset pricing)
    (
        "Mehra and Prescott, 'The Equity Premium: A Puzzle', Journal of Monetary Economics 15 (1985) 145-161, showed that the historical US equity premium is far larger than a representative-agent consumption-CAPM with plausible risk aversion can justify.",
        "knowledge",
        "The historical excess return of equities over safe bonds in the US is much larger than can be rationalized by a representative-agent consumption-based asset pricing model with conventional levels of risk aversion.",
        "knowledge",
    ),
    # 41. Klemperer IO pricing (industrial organization)
    (
        "Klemperer, 'Markets with Consumer Switching Costs', Quarterly Journal of Economics 102 (1987) 375-394, analyzed how switching costs soften price competition and can raise equilibrium prices.",
        "knowledge",
        "When consumers face costs of switching between suppliers, firms effectively compete for future market share by pricing low initially and then exploiting locked-in customers, leading to higher average prices than under frictionless competition.",
        "knowledge",
    ),
    # 42. Bresnahan-Reiss entry (IO)
    (
        "Bresnahan and Reiss, 'Entry and Competition in Concentrated Markets', Journal of Political Economy 99 (1991) 977-1009, estimated how the market size required to support each additional firm grows less than proportionally, indicating rapid convergence to competitive conduct.",
        "knowledge",
        "In small local markets, the population required to support each additional entrant rises sharply from monopoly to duopoly but flattens quickly, suggesting that competitive conduct is approached with only a handful of firms.",
        "knowledge",
    ),
    # 43. Roth kidney exchange (market design)
    (
        "Roth, Sonmez, and Unver, 'Kidney Exchange', Quarterly Journal of Economics 119 (2004) 457-488, designed matching mechanisms for paired kidney donation that are strategy-proof and produce Pareto-efficient outcomes.",
        "knowledge",
        "Paired kidney exchange programs can be organized through strategy-proof mechanisms that increase the number of feasible transplants relative to direct donation alone.",
        "knowledge",
    ),
    # 44. Grossman-Hart property rights (organizational econ)
    (
        "Grossman and Hart, 'The Costs and Benefits of Ownership: A Theory of Vertical and Lateral Integration', Journal of Political Economy 94 (1986) 691-719, introduced the property-rights theory of the firm based on residual control rights over assets.",
        "knowledge",
        "The boundaries of the firm are determined by who holds residual control rights over assets when contracts are incomplete, because ownership affects ex ante investment incentives.",
        "knowledge",
    ),
    # 45. Becker human capital (labour / health econ)
    (
        "Gary Becker, 'Human Capital: A Theoretical and Empirical Analysis, with Special Reference to Education' (NBER, Columbia University Press, 1964), formalized investment in schooling and training as analogous to investment in physical capital.",
        "knowledge",
        "Schooling, training, and health can be modeled as investments that raise an individual's productivity and lifetime earnings, with returns that can be compared to those on physical capital.",
        "knowledge",
    ),
    # 46. Grossman health capital (health econ)
    (
        "Michael Grossman, 'On the Concept of Health Capital and the Demand for Health', Journal of Political Economy 80 (1972) 223-255, modeled health as a durable capital stock that depreciates with age and can be augmented by investment.",
        "knowledge",
        "Individuals can be viewed as choosing a path of investment in health as a durable stock that yields utility directly and indirectly by expanding time available for work and leisure.",
        "knowledge",
    ),
    # 47. Finkelstein Oregon Medicaid experiment (health econ / public finance)
    (
        "Finkelstein et al., 'The Oregon Health Insurance Experiment: Evidence from the First Year', Quarterly Journal of Economics 127 (2012) 1057-1106, used the 2008 Oregon Medicaid lottery to identify causal effects of insurance coverage.",
        "knowledge",
        "Randomized access to Medicaid in Oregon increased healthcare utilization, reduced financial strain, and improved self-reported health, without detectable short-run effects on objective measures such as blood pressure or cholesterol.",
        "knowledge",
    ),
    # 48. NBER Working Paper on monetary policy (monetary)
    (
        "Romer and Romer, 'A New Measure of Monetary Shocks: Derivation and Implications', NBER Working Paper 9866 (2003, later published in American Economic Review 94, 2004, 1055-1084), constructed narrative-based monetary shocks from FOMC records.",
        "knowledge",
        "Monetary policy shocks constructed from narrative records of Federal Open Market Committee intentions produce larger and more persistent estimated effects on output and prices than shocks identified from simple reduced-form VARs.",
        "knowledge",
    ),
    # 49. IMF WEO current account (international macro)
    (
        "The IMF World Economic Outlook, October 2019, Chapter 4 'The Rise of Corporate Market Power and Its Macroeconomic Effects', documented a broad-based rise in firm-level markups across advanced economies since 2000.",
        "knowledge",
        "Firm-level markups over marginal cost have risen broadly across advanced economies since around 2000, with the increase concentrated among already-high-markup firms.",
        "knowledge",
    ),
    # 50. Laibson hyperbolic discounting (behavioural / public econ)
    (
        "David Laibson, 'Golden Eggs and Hyperbolic Discounting', Quarterly Journal of Economics 112 (1997) 443-478, introduced quasi-hyperbolic discounting into intertemporal consumption choice and analyzed commitment devices.",
        "knowledge",
        "People tend to discount the near future more steeply than the distant future, creating time-inconsistent preferences that can generate demand for illiquid savings vehicles as commitment devices.",
        "knowledge",
    ),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (ref_text, ref_domain, fact_text, fact_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            ref_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            fact_id = f"class-{ID_OFFSET + (2 * i):05d}"
            f.write(json.dumps({
                "id": ref_id,
                "domain": ref_domain,
                "text": ref_text,
                "memory_type": "reference",
                "pair_id": pair_id,
            }, ensure_ascii=False) + "\n")
            f.write(json.dumps({
                "id": fact_id,
                "domain": fact_domain,
                "text": fact_text,
                "memory_type": "fact",
                "pair_id": pair_id,
            }, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
