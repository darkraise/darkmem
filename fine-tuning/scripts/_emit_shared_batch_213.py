"""One-off emitter for shared-base batch-213 — personal domain (FIRE movement, index investing, tax-advantaged accounts, budgeting tools, retirement planning).

Writes 50 rows to data/v2/shared/batch_213.tmp.jsonl with ids shared-10601..10650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_213.tmp.jsonl"
ID_OFFSET = 10600

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Committed to Lean FIRE with a 625k target after modelling a 25k annual spend against a 4% rule withdrawal; Fat FIRE never survived the budget review honestly.", "decision", "personal", False,
     [("Lean FIRE", "concept"), ("Fat FIRE", "concept"), ("4% rule", "concept")],
     [("Lean FIRE", "Fat FIRE", "PREFERS")],
     "which flavour of FIRE did I land on after running the numbers and what withdrawal rule set the target",
     "lean fire fat fire 4 percent rule target withdrawal spend"),
    # --- 2. architecture ---
    ("The portfolio is a Boglehead three-fund layout: VTSAX for US equity, VXUS for ex-US, and a short-term bond fund sleeve rebalanced once a year on my birthday.", "architecture", "personal", False,
     [("Boglehead", "concept"), ("VTSAX", "tool"), ("VXUS", "tool"), ("three-fund", "pattern")],
     [("three-fund", "Boglehead", "APPLIES_TO"), ("VTSAX", "three-fund", "USES")],
     "how is my portfolio structured across US and international equity and how often do I rebalance",
     "boglehead three fund vtsax vxus bond rebalance birthday portfolio"),
    # --- 3. fact ---
    ("An HSA gives the triple tax advantage: contributions are pre-tax, growth is untaxed, and qualified medical withdrawals come out free; no other account stacks all three.", "fact", "personal", False,
     [("HSA", "concept"), ("triple tax advantage", "concept")],
     [("HSA", "triple tax advantage", "APPLIES_TO")],
     "which account gives the triple tax advantage and what are the three legs of that benefit",
     "hsa triple tax advantage pre tax growth withdrawal medical"),
    # --- 4. decision ---
    ("Chose Roth IRA over traditional for the 2026 contribution because my current bracket is still the 12% one and I expect higher income by the time I draw from it.", "decision", "personal", False,
     [("Roth IRA", "concept"), ("traditional", "concept"), ("2026", "date")],
     [("Roth IRA", "traditional", "PREFERS")],
     "which IRA flavour did I pick for this year's contribution and what bracket reasoning drove the choice",
     "roth ira traditional 2026 contribution bracket future income"),
    # --- 5. architecture ---
    ("Backdoor Roth is wired as an annual ritual: contribute 7k to a non-deductible traditional IRA in January and convert to Roth the same week before any gains accrue.", "architecture", "personal", False,
     [("Backdoor Roth", "concept"), ("traditional IRA", "concept"), ("Roth", "concept")],
     [("Backdoor Roth", "traditional IRA", "USES")],
     "how is the backdoor Roth sequence scheduled each year and why does the conversion happen so fast",
     "backdoor roth traditional ira convert january contribution gain"),
    # --- 6. milestone ---
    ("Hit the 401(k) match ceiling in March 2026 for the first time; the employer 5% match on full salary now compounds for the rest of the year without extra effort.", "milestone", "personal", False,
     [("401(k)", "concept"), ("March 2026", "date"), ("employer 5% match", "concept")],
     [],
     "when did I first max the employer 401(k) match in a calendar year and what does that unlock afterwards",
     "401k match ceiling march 2026 employer 5 percent salary compound"),
    # --- 7. reference ---
    ("Big Ern's ERN safe withdrawal series is my canonical source for sequence-of-returns risk analysis; Part 8 on the bond tent glide path settled the argument for me.", "reference", "personal", False,
     [("Big Ern", "person"), ("ERN safe withdrawal", "concept"), ("bond tent", "concept"), ("glide path", "concept")],
     [("bond tent", "glide path", "APPLIES_TO")],
     "which blog series do I treat as authoritative on safe withdrawal and which part convinced me on bond tents",
     "ern big safe withdrawal bond tent glide path sequence return"),
    # --- 8. decision ---
    ("Swapped SPY for VOO inside the taxable brokerage; the expense ratio gap is small but the tax-loss harvesting pairing with VTI is cleaner under the wash-sale rule.", "decision", "personal", False,
     [("SPY", "tool"), ("VOO", "tool"), ("VTI", "tool"), ("tax-loss harvesting", "concept"), ("wash-sale", "concept")],
     [("VOO", "SPY", "REPLACES"), ("VOO", "VTI", "APPLIES_TO")],
     "which S&P 500 ETF did I swap and what tax-loss harvesting pairing cleaned up the wash-sale risk",
     "spy voo vti etf expense ratio tax loss harvest wash sale"),
    # --- 9. architecture ---
    ("Tax-loss harvesting runs as an October sweep: any lot more than 3% underwater gets sold into a partner fund for 31 days then rotated back, logged in a spreadsheet per lot.", "architecture", "personal", False,
     [("Tax-loss harvesting", "concept"), ("October", "date"), ("partner fund", "concept")],
     [],
     "when does the tax-loss harvesting sweep run each year and what threshold triggers a lot swap",
     "tax loss harvest october sweep partner fund 31 day lot swap"),
    # --- 10. noise ---
    ("The squirrel on the back deck has figured out how to steal peanuts from the new baffle-guarded feeder and seems rather pleased with itself.", "fact", "noise", True, [], [], None, None),
    # --- 11. milestone ---
    ("Completed the first mega backdoor Roth cycle in 2026 after the plan admin finally turned on after-tax contributions with in-plan Roth conversion; moved 34k in under a year.", "milestone", "personal", False,
     [("mega backdoor Roth", "concept"), ("2026", "date"), ("after-tax contributions", "concept"), ("in-plan Roth conversion", "concept")],
     [("mega backdoor Roth", "after-tax contributions", "USES")],
     "what big tax-advantaged move did I pull off for the first time this year once the plan admin enabled it",
     "mega backdoor roth 2026 after tax conversion plan admin 34k"),
    # --- 12. decision ---
    ("Picked VT as the one-ticket global index for the kid's UTMA account; a single fund tracking both US and ex-US at cap weight beat explaining rebalancing to an eight-year-old.", "decision", "personal", False,
     [("VT", "tool"), ("UTMA", "concept")],
     [("VT", "UTMA", "APPLIES_TO")],
     "which single-ticker global fund did I pick for the kid's UTMA and what did it simplify",
     "vt global index utma kid single ticker rebalance cap weight"),
    # --- 13. reference ---
    ("Bought JL Collins The Simple Path to Wealth in paperback for three relatives this year; the stock series chapter is what finally got my sister into VTSAX.", "reference", "personal", False,
     [("JL Collins", "person"), ("The Simple Path to Wealth", "tool"), ("VTSAX", "tool")],
     [("The Simple Path to Wealth", "VTSAX", "APPLIES_TO")],
     "which book did I hand out to relatives and which chapter moved my sister to the total market fund",
     "jl collins simple path wealth book vtsax stock series sister"),
    # --- 14. architecture ---
    ("Budgeting runs on YNAB with the zero-based method: every incoming dollar is assigned to a category before the day ends, and rollovers cover seasonal spikes like property tax.", "architecture", "personal", False,
     [("YNAB", "tool"), ("zero-based", "concept"), ("property tax", "concept")],
     [("YNAB", "zero-based", "USES")],
     "which budgeting app and method handle my cash flow and how do seasonal spikes get covered",
     "ynab zero based budget category dollar rollover property tax"),
    # --- 15. preference ---
    ("I prefer YNAB over the envelope method on paper; the digital category containers give me the same mental model without the physical drawer of cash envelopes.", "preference", "personal", False,
     [("YNAB", "tool"), ("envelope method", "concept")],
     [("YNAB", "envelope method", "PREFERS")],
     "which budgeting tool do I prefer over physical envelopes and why does the digital version still feel right",
     "ynab envelope method digital category container prefer cash"),
    # --- 16. problem ---
    ("Mint shutdown in 2024 broke my category history import; had to scrape the final CSV export by hand and stitch two years of tagged transactions back into YNAB.", "problem", "personal", False,
     [("Mint", "tool"), ("CSV", "technology"), ("YNAB", "tool"), ("2024", "date")],
     [("YNAB", "Mint", "REPLACES")],
     "which budgeting tool shutdown forced a manual CSV stitch and which tool did I migrate the history into",
     "mint shutdown 2024 csv export ynab migrate category history"),
    # --- 17. reference ---
    ("Ramit Sethi's conscious spending plan was the frame I used to split guilt-free spending from savings goals; the 60-20-20 split is now encoded directly in YNAB targets.", "reference", "personal", False,
     [("Ramit Sethi", "person"), ("conscious spending", "concept"), ("YNAB", "tool")],
     [("conscious spending", "YNAB", "APPLIES_TO")],
     "which personal-finance author's spending framework sits behind my YNAB target splits",
     "ramit sethi conscious spend plan ynab 60 20 target split"),
    # --- 18. architecture ---
    ("The retirement plan uses a bond tent glide path: bond allocation climbs from 20% today to 60% by age 65 then slowly drops back to 40% as sequence risk fades.", "architecture", "personal", False,
     [("bond tent", "concept"), ("glide path", "concept"), ("sequence risk", "concept")],
     [("bond tent", "sequence risk", "APPLIES_TO")],
     "how does the bond allocation glide from now through retirement and which risk is it meant to tame",
     "bond tent glide path allocation age 65 sequence risk retire"),
    # --- 19. fact ---
    ("The Trinity Study's 4% rule was built on 30-year horizons with 50/50 stock/bond portfolios; using it for a 50-year early-retirement horizon is a well-known misapplication.", "fact", "personal", False,
     [("Trinity Study", "concept"), ("4% rule", "concept")],
     [("4% rule", "Trinity Study", "APPLIES_TO")],
     "what horizon and portfolio mix was the 4% rule actually studied on and where does FIRE usage overreach it",
     "trinity study 4 percent rule 30 year 50 50 portfolio early retire"),
    # --- 20. decision ---
    ("Cut Personal Capital after the Empower rebrand once the net-worth view started forcing upsell banners; switched to a self-hosted spreadsheet pulling prices via a Google Sheets finance formula.", "decision", "personal", False,
     [("Personal Capital", "tool"), ("Empower", "tool"), ("Google Sheets", "tool")],
     [("Google Sheets", "Personal Capital", "REPLACES")],
     "which net-worth tool did I drop after the rebrand and what replaced it for tracking",
     "personal capital empower rebrand upsell google sheets net worth"),
    # --- 21. architecture ---
    ("Monte Carlo retirement planning runs monthly in FIRECalc and cFIREsim; success rate above 95% across both tools is the gate before any lifestyle-inflation decision.", "architecture", "personal", False,
     [("Monte Carlo", "concept"), ("FIRECalc", "tool"), ("cFIREsim", "tool")],
     [],
     "which two planning tools do I run each month and what success threshold gates lifestyle creep",
     "monte carlo firecalc cfiresim monthly success rate 95 percent lifestyle"),
    # --- 22. reference ---
    ("Mr. Money Mustache's shockingly simple math post is still my go-to explainer for savings rate versus years-to-FI; the table collapses the whole argument onto one page.", "reference", "personal", False,
     [("Mr. Money Mustache", "person"), ("savings rate", "concept")],
     [],
     "whose savings-rate-to-years-to-FI post do I send to people who ask why savings rate matters so much",
     "mr money mustache savings rate years fi table simple math"),
    # --- 23. milestone ---
    ("Hit a 50% savings rate for the first time in Q1 2026; the combination of the 401(k) full match plus the backdoor Roth front-loading did most of the lift.", "milestone", "personal", False,
     [("savings rate", "concept"), ("Q1 2026", "date"), ("401(k)", "concept"), ("backdoor Roth", "concept")],
     [("backdoor Roth", "savings rate", "APPLIES_TO")],
     "which quarter did I first cross a 50% savings rate and which two tax-advantaged moves did the heavy lifting",
     "savings rate 50 percent q1 2026 401k backdoor roth front load"),
    # --- 24. decision ---
    ("Target-date funds are out of the taxable brokerage but stay in the 401(k); capital gains distributions on TDFs in taxable were a nasty surprise the year I first looked.", "decision", "personal", False,
     [("Target-date funds", "concept"), ("401(k)", "concept"), ("capital gains", "concept")],
     [("Target-date funds", "401(k)", "APPLIES_TO")],
     "where are target-date funds allowed in my accounts and which tax event drove them out of taxable",
     "target date fund 401k taxable capital gain distribution surprise"),
    # --- 25. architecture ---
    ("REITs live exclusively in the Roth IRA because their dividends are taxed as ordinary income; the tax-location rule for non-qualified payouts is baked into the rebalance script.", "architecture", "personal", False,
     [("REITs", "concept"), ("Roth IRA", "concept"), ("tax-location", "concept")],
     [("REITs", "Roth IRA", "APPLIES_TO")],
     "where do REITs live across my accounts and which tax characteristic forces that placement",
     "reit roth ira dividend ordinary income tax location rebalance"),
    # --- 26. problem ---
    ("Forgot the pro-rata rule on a backdoor Roth in 2023 after rolling an old 401(k) into a traditional IRA; got a 1099-R that taxed the conversion as partly deductible.", "problem", "personal", False,
     [("pro-rata rule", "concept"), ("backdoor Roth", "concept"), ("traditional IRA", "concept"), ("1099-R", "publication"), ("2023", "date")],
     [("pro-rata rule", "backdoor Roth", "APPLIES_TO")],
     "which IRS rule did I trip on a backdoor Roth after a 401k rollover and what form surfaced the tax hit",
     "pro rata rule backdoor roth 401k rollover traditional ira 1099"),
    # --- 27. decision ---
    ("Parked the emergency fund in VWRA-adjacent short duration treasuries instead of a savings account; the yield gap in 2026 was large enough to beat the inflation drag.", "decision", "personal", False,
     [("VWRA", "tool"), ("short duration treasuries", "concept"), ("2026", "date")],
     [("short duration treasuries", "VWRA", "PREFERS")],
     "where does the emergency fund sit instead of a plain savings account and what drove the choice",
     "vwra treasury emergency fund savings yield inflation 2026"),
    # --- 28. milestone ---
    ("Crossed Coast FIRE in October 2026: current invested assets compound to the retirement target by age 60 without a single further contribution.", "milestone", "personal", False,
     [("Coast FIRE", "concept"), ("October 2026", "date"), ("retirement target", "concept")],
     [],
     "which FIRE variant did I cross this year and what does crossing it mean for future contributions",
     "coast fire october 2026 invested asset compound target 60 retire"),
    # --- 29. fact ---
    ("Dollar-cost averaging into VTI happens on the 5th and 20th of each month; lump-sum on a RSU vest goes in the same day to avoid behavioural loss aversion.", "fact", "personal", False,
     [("Dollar-cost averaging", "concept"), ("VTI", "tool"), ("RSU", "concept"), ("lump-sum", "concept")],
     [("lump-sum", "RSU", "APPLIES_TO")],
     "what DCA schedule do I use for VTI and how do RSU vests get handled differently",
     "dollar cost average vti 5th 20th rsu lump sum loss aversion"),
    # --- 30. fact ---
    ("QQQ is explicitly not part of my core allocation; the tech concentration duplicates what VTSAX already holds at cap weight and adds tracking-error variance for nothing.", "fact", "personal", False,
     [("QQQ", "tool"), ("VTSAX", "tool"), ("tracking-error", "concept")],
     [("QQQ", "VTSAX", "APPLIES_TO")],
     "why is QQQ deliberately absent from my core allocation given what VTSAX already owns",
     "qqq vtsax tech concentration tracking error core allocation"),
    # --- 31. decision ---
    ("Moved the HSA provider from the employer default to Fidelity for the zero-fee investment menu; the employer account now only holds the year's deductible buffer.", "decision", "personal", False,
     [("HSA", "concept"), ("Fidelity", "organization"), ("deductible buffer", "concept")],
     [("Fidelity", "HSA", "APPLIES_TO")],
     "which HSA provider did I switch to and what role does the employer account keep afterwards",
     "hsa fidelity employer default zero fee investment deductible"),
    # --- 32. architecture ---
    ("Withdrawal sequencing in retirement will go taxable first, then traditional, then Roth last; the ordering stretches the Roth compounding horizon by over a decade.", "architecture", "personal", False,
     [("taxable", "concept"), ("traditional", "concept"), ("Roth", "concept")],
     [("Roth", "taxable", "APPLIES_TO")],
     "in what order will I draw down the three account buckets in retirement and what does that ordering protect",
     "withdrawal order taxable traditional roth compound horizon retire"),
    # --- 33. fact ---
    ("Hit a wash-sale surprise in 2025 when the automatic 401(k) contribution bought VTSAX 28 days after a TLH trade in the taxable account; disallowed about 400 of losses.", "fact", "personal", False,
     [("wash-sale", "concept"), ("401(k)", "concept"), ("VTSAX", "tool"), ("TLH", "concept"), ("2025", "date")],
     [("wash-sale", "401(k)", "APPLIES_TO")],
     "which 401k and taxable account interaction triggered a wash-sale and how much of the loss got disallowed",
     "wash sale 401k vtsax tlh 2025 28 day disallow 400 loss"),
    # --- 34. decision ---
    ("Dropped Betterment's robo-advisor after calculating that the 0.25% fee was larger than my tax-loss harvesting savings once the portfolio crossed 400k.", "decision", "personal", False,
     [("Betterment", "tool"), ("robo-advisor", "concept"), ("tax-loss harvesting", "concept")],
     [("tax-loss harvesting", "Betterment", "REPLACES")],
     "which robo-advisor did I drop and what crossover point made the fee bigger than the TLH benefit",
     "betterment robo advisor 0 25 fee tax loss harvest 400k"),
    # --- 35. milestone ---
    ("First year I fully funded all three tax-advantaged buckets in 2026: 401(k), HSA, and Roth IRA; remainder went into VTSAX in taxable.", "milestone", "personal", False,
     [("2026", "date"), ("401(k)", "concept"), ("HSA", "concept"), ("Roth IRA", "concept"), ("VTSAX", "tool")],
     [],
     "which was the first year I maxed every tax-advantaged bucket and where did the overflow land",
     "2026 max 401k hsa roth ira vtsax taxable bucket"),
    # --- 36. reference ---
    ("Used the cFIREsim success-rate output as evidence when negotiating my sabbatical; a 97% rate on a 30-year horizon turned the conversation from feasibility to scheduling.", "reference", "personal", False,
     [("cFIREsim", "tool"), ("sabbatical", "concept")],
     [],
     "which simulator output did I bring to the sabbatical negotiation and what success rate carried the argument",
     "cfiresim success rate 97 percent sabbatical negotiate 30 year"),
    # --- 37. milestone ---
    ("Barista FIRE became the documented fallback plan in 2026 after a contract-review scare; part-time barista-style work would cover health insurance premiums while the portfolio keeps compounding.", "milestone", "personal", False,
     [("Barista FIRE", "concept"), ("2026", "date"), ("health insurance", "concept")],
     [("Barista FIRE", "health insurance", "APPLIES_TO")],
     "when did Barista FIRE become a documented fallback plan and which expense is it meant to cover",
     "barista fire 2026 part time health insurance premium compound"),
    # --- 38. decision ---
    ("Refused to buy VXUS hedged-currency variants after reading the long-run currency-neutral data; unhedged ex-US equity stays in the portfolio as intended.", "decision", "personal", False,
     [("VXUS", "tool"), ("hedged-currency", "concept")],
     [("VXUS", "hedged-currency", "PREFERS")],
     "why did I reject the hedged-currency variant of VXUS and stay with unhedged ex-US",
     "vxus hedged currency ex us equity long run data unhedged"),
    # --- 39. preference ---
    ("Strongly prefer Vanguard mutual funds like VTSAX over the ETF equivalent inside tax-advantaged accounts; the automatic fractional dollar purchase is friction I don't want.", "preference", "personal", False,
     [("Vanguard", "organization"), ("VTSAX", "tool"), ("ETF", "concept")],
     [("VTSAX", "ETF", "PREFERS")],
     "inside tax-advantaged accounts, do I prefer Vanguard mutual funds or ETFs and why",
     "vanguard vtsax mutual fund etf fractional dollar tax advantaged"),
    # --- 40. fact ---
    ("The mega backdoor Roth annual ceiling in 2026 is around 46k of after-tax space on top of the 23k elective deferral; not every plan allows it and the plan document is the source of truth.", "fact", "personal", False,
     [("mega backdoor Roth", "concept"), ("2026", "date"), ("elective deferral", "concept"), ("plan document", "concept")],
     [("mega backdoor Roth", "plan document", "APPLIES_TO")],
     "what is the 2026 after-tax ceiling for the mega backdoor Roth and what gates availability",
     "mega backdoor roth 2026 46k after tax 23k elective plan document"),
    # --- 41. architecture ---
    ("Net-worth tracking is a flat Google Sheet with one row per month; the pivot against FIRECalc output makes the years-to-FI line visible at every monthly review.", "architecture", "personal", False,
     [("Google Sheet", "tool"), ("FIRECalc", "tool"), ("years-to-FI", "concept")],
     [("Google Sheet", "FIRECalc", "USES")],
     "which tool do I use for net-worth tracking and what view surfaces the years-to-FI trajectory",
     "google sheet net worth monthly firecalc pivot years to fi"),
    # --- 42. problem ---
    ("State tax on HSA contributions in California caught me off guard; the federal triple tax advantage does not carry to the state return and the W-2 Box 12 W amount is taxable there.", "problem", "personal", False,
     [("HSA", "concept"), ("California", "place"), ("W-2", "publication"), ("triple tax advantage", "concept")],
     [("California", "HSA", "APPLIES_TO")],
     "which state breaks the HSA triple tax advantage at the state level and which payroll box surfaces the add-back",
     "hsa california state tax triple advantage w2 box 12 w add back"),
    # --- 43. noise ---
    ("The sourdough starter survived a two-week fridge nap and came back bubbling after just one feed which feels like a small miracle every time.", "fact", "noise", True, [], [], None, None),
    # --- 44. decision ---
    ("Stopped chasing individual dividend stocks after one read of The Simple Path to Wealth; the total-return frame makes the dividend-yield trap obvious in hindsight.", "decision", "personal", False,
     [("The Simple Path to Wealth", "tool"), ("dividend stocks", "concept"), ("total-return", "concept")],
     [("total-return", "dividend stocks", "PREFERS")],
     "which book retired my dividend-stock chase and what investing frame took its place",
     "simple path wealth dividend stock total return yield trap"),
    # --- 45. milestone ---
    ("Paid off the last non-mortgage debt in September 2026; freed cash flow redirected into VTI on the same automatic schedule that used to cover the loan payment.", "milestone", "personal", False,
     [("September 2026", "date"), ("VTI", "tool"), ("non-mortgage debt", "concept")],
     [("VTI", "non-mortgage debt", "REPLACES")],
     "when did non-mortgage debt hit zero and where does the freed cash flow get redirected automatically",
     "non mortgage debt payoff september 2026 vti automatic loan"),
    # --- 46. reference ---
    ("Kept a printed copy of the ERN safe withdrawal series Part 25 on historical worst cases at my desk; every time the market drops I look at the cape-based equity glide path chart.", "reference", "personal", False,
     [("ERN safe withdrawal", "concept"), ("Part 25", "publication"), ("cape-based equity", "concept"), ("glide path", "concept")],
     [],
     "which printed piece of retirement research do I keep on the desk and which chart stays useful in drawdowns",
     "ern safe withdrawal part 25 cape equity glide path desk drawdown"),
    # --- 47. fact ---
    ("Rebalance triggers on 5% drift per asset class rather than calendar cadence; the threshold rule beats the birthday rule on tax drag in backtests across 2018 and 2022.", "fact", "personal", False,
     [("Rebalance", "concept"), ("5% drift", "config"), ("2018", "date"), ("2022", "date")],
     [],
     "which rebalance trigger replaced the calendar rule and which backtests validated it",
     "rebalance 5 percent drift calendar threshold backtest 2018 2022"),
    # --- 48. preference ---
    ("I lean hard on Boglehead orthodoxy over stock-picking; the forum's age and low-turnover sample size is worth more than any 50 YouTube finance channels combined.", "preference", "personal", False,
     [("Boglehead", "concept"), ("stock-picking", "concept"), ("YouTube", "tool")],
     [("Boglehead", "stock-picking", "PREFERS")],
     "where do I anchor my investing preferences and what kind of source do I discount relative to that",
     "boglehead stock pick youtube finance channel forum orthodoxy"),
    # --- 49. preference ---
    ("Prefer JL Collins' stock series posts in the original blog form over the book for onboarding friends; the hyperlink trail through the series does a better job than chapter breaks.", "preference", "personal", False,
     [("JL Collins", "person"), ("stock series", "concept"), ("blog", "concept")],
     [("blog", "stock series", "APPLIES_TO")],
     "which format of JL Collins' work do I use when onboarding friends and what does the hyperlink trail add",
     "jl collins stock series blog book onboard friend hyperlink"),
    # --- 50. decision ---
    ("Adopted a three-bucket retirement withdrawal architecture: one year cash, five years bonds, rest equity; the cash bucket absorbs sequence risk without forcing a stock sale in a crash.", "decision", "personal", False,
     [("three-bucket", "pattern"), ("cash", "concept"), ("bonds", "concept"), ("equity", "concept"), ("sequence risk", "concept")],
     [("three-bucket", "sequence risk", "APPLIES_TO")],
     "which withdrawal architecture will I use in retirement and how does it insulate from a crash-year stock sale",
     "three bucket retirement cash bond equity sequence risk crash"),
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
