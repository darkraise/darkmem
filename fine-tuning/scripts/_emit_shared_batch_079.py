"""One-off emitter for shared-base batch-079 — cross domain.

Slice: personal finance meets tech (budgeting apps, aggregators, brokerage
APIs, tax software, crypto wallets, plain-text accounting, retirement tools,
money writers, finance podcasts). Writes 50 rows to
data/v2/shared/batch_079.tmp.jsonl with ids shared-03901..03950. The main
session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_079.tmp.jsonl"
ID_OFFSET = 3900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched the household budget from Mint to Monarch on 2026-01-08 after Intuit killed Mint and the CSV export left a decade of categories homeless.", "decision", "cross", False,
     [("Mint", "service"), ("Monarch", "service"), ("2026-01-08", "date"), ("Intuit", "organization"), ("CSV", "concept")],
     [("Monarch", "Mint", "REPLACES")],
     "when did the household budget actually leave Mint and where did it land",
     "budget app migration mint shutdown csv export category history"),
    # --- 2 ---
    ("YNAB's four-rule method finally clicked once the rent category stopped borrowing from the groceries envelope, so the give-every-dollar-a-job habit stuck through Q1 2026.", "milestone", "cross", False,
     [("YNAB", "service"), ("Q1 2026", "date")],
     [],
     "when did the envelope budgeting habit actually become sustainable",
     "zero based budget envelope method rule adoption quarter habit"),
    # --- 3 ---
    ("Prefers Copilot over Monarch on iPhone because Copilot's review screen for uncategorized Plaid transactions takes two taps where Monarch needs four.", "preference", "cross", False,
     [("Copilot", "service"), ("Monarch", "service"), ("iPhone", "infrastructure"), ("Plaid", "service")],
     [("Copilot", "Monarch", "PREFERS")],
     "which budgeting app wins for quick mobile categorization and why",
     "mobile budget app review flow tap count uncategorized transaction"),
    # --- 4 ---
    ("Actual Budget self-hosted on a Raspberry Pi replaced the YNAB subscription on 2026-02-14 because the 109-dollar annual fee stopped being worth it once the local sync finally worked.", "decision", "cross", False,
     [("Actual Budget", "service"), ("Raspberry Pi", "infrastructure"), ("YNAB", "service"), ("2026-02-14", "date")],
     [("Actual Budget", "YNAB", "REPLACES"), ("Actual Budget", "Raspberry Pi", "DEPLOYED_ON")],
     "when did the budget tooling go self-hosted and what triggered the switch",
     "self hosted budget subscription cancellation raspberry pi local sync"),
    # --- 5 ---
    ("Plaid's link flow broke against the Schwab brokerage connection on 2026-03-02 and every downstream tool, Copilot and Monarch and Lunch Money, went dark on the investment balances for four days.", "problem", "cross", False,
     [("Plaid", "service"), ("Schwab", "organization"), ("2026-03-02", "date"), ("Copilot", "service"), ("Monarch", "service"), ("Lunch Money", "service")],
     [("Copilot", "Plaid", "USES"), ("Monarch", "Plaid", "USES"), ("Lunch Money", "Plaid", "USES")],
     "what caused the multi-app blackout on brokerage balances that first week of March",
     "aggregator outage brokerage link downstream budget tool blackout"),
    # --- 6. noise ---
    ("Let me think about how to phrase this.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Lunch Money's rules engine auto-categorized 94 percent of the Chase transactions last month, so the weekly reconciliation on Sunday nights dropped from an hour to twelve minutes.", "fact", "cross", False,
     [("Lunch Money", "service"), ("Chase", "organization")],
     [],
     "how much did the weekly reconciliation shrink after the auto-categorization worked",
     "rules engine auto categorize reconciliation time weekly review drop"),
    # --- 8 ---
    ("Beancount replaced the old Google Sheets ledger on 2026-01-30 because the double-entry constraint caught a two-year-old typo in the 401k cost basis that the spreadsheet never flagged.", "decision", "cross", False,
     [("Beancount", "tool"), ("Google Sheets", "service"), ("2026-01-30", "date"), ("401k", "concept")],
     [("Beancount", "Google Sheets", "REPLACES")],
     "when did the plain-text ledger take over from the spreadsheet and why",
     "plain text accounting double entry typo detection cost basis catch"),
    # --- 9 ---
    ("Prefers hledger over Beancount for the household books because hledger's register report runs in under a second against a 15-year journal where Beancount's bean-query stalls.", "preference", "cross", False,
     [("hledger", "tool"), ("Beancount", "tool")],
     [("hledger", "Beancount", "PREFERS")],
     "which plain-text accounting tool won for the long-running household journal",
     "plain text ledger performance long journal register report speed"),
    # --- 10 ---
    ("Fidelity's Active Trader Pro replaced Robinhood as the primary brokerage on 2026-02-21 after Robinhood's options chain showed stale bid-ask spreads during the Nvidia earnings run.", "decision", "cross", False,
     [("Fidelity", "organization"), ("Active Trader Pro", "tool"), ("Robinhood", "service"), ("2026-02-21", "date"), ("Nvidia", "organization")],
     [("Fidelity", "Robinhood", "REPLACES")],
     "when did the primary brokerage move off Robinhood and what triggered it",
     "brokerage migration active trader options chain latency earnings"),
    # --- 11 ---
    ("The IBKR API keeps a paper-trading portfolio synced to a DuckDB file every 15 minutes so the Beancount journal picks up mark-to-market without a manual CSV dump.", "architecture", "cross", False,
     [("IBKR", "organization"), ("DuckDB", "database"), ("Beancount", "tool"), ("CSV", "concept")],
     [("Beancount", "DuckDB", "USES"), ("IBKR", "DuckDB", "COMMUNICATES_WITH")],
     "how does the paper-trading account feed the plain-text ledger without manual exports",
     "brokerage api paper trade mark to market sync duckdb ledger pipe"),
    # --- 12 ---
    ("Ramit Sethi's Conscious Spending Plan template on 2026-01-12 finally got the guilt-free spending bucket separated from the savings bucket that used to silently drain it.", "milestone", "cross", False,
     [("Ramit Sethi", "person"), ("Conscious Spending Plan", "method"), ("2026-01-12", "date")],
     [("Conscious Spending Plan", "Ramit Sethi", "AUTHORED_BY")],
     "when did the conscious spending split actually take effect on the budget",
     "conscious spending plan guilt free spending savings bucket split"),
    # --- 13 ---
    ("The Mr Money Mustache 4 percent rule post anchors the FI number in the Projection Lab scenario, and the 2057 target year barely budges when the savings rate stays above 55 percent.", "reference", "cross", False,
     [("Mr Money Mustache", "person"), ("Projection Lab", "service"), ("2057", "date")],
     [("Projection Lab", "Mr Money Mustache", "BUILDS_ON")],
     "which blogger's math underpins the current FI projection and what year does it point at",
     "four percent rule financial independence projection savings rate"),
    # --- 14 ---
    ("TurboTax Deluxe replaced FreeTaxUSA for the 2025 return on 2026-03-19 because the K-1 import for the SPG partnership was a two-minute task in TurboTax and a manual slog in FreeTaxUSA.", "decision", "cross", False,
     [("TurboTax", "service"), ("FreeTaxUSA", "service"), ("2026-03-19", "date"), ("K-1", "concept")],
     [("TurboTax", "FreeTaxUSA", "REPLACES")],
     "when did tax software swap for the 2025 return and why",
     "tax software migration partnership k1 import manual entry friction"),
    # --- 15 ---
    ("Prefers FreeTaxUSA for the W-2-only return because the 15-dollar state filing beats TurboTax's 64 and the federal side stays free even with the HSA contribution form.", "preference", "cross", False,
     [("FreeTaxUSA", "service"), ("TurboTax", "service"), ("HSA", "concept")],
     [("FreeTaxUSA", "TurboTax", "PREFERS")],
     "which tax tool wins for the simple W-2 and HSA case",
     "tax software state filing cost comparison hsa form simple return"),
    # --- 16 ---
    ("The 2026-02-28 Wealthsimple Tax import pulled the Questrade T5008 capital gains slip in a single click, so the crypto staking rewards were the only line that needed manual entry.", "milestone", "cross", False,
     [("2026-02-28", "date"), ("Wealthsimple Tax", "service"), ("Questrade", "organization"), ("T5008", "concept")],
     [("Wealthsimple Tax", "Questrade", "COMMUNICATES_WITH")],
     "when did the Canadian tax import cut the manual work down to just the staking line",
     "canadian tax import capital gains slip staking rewards manual entry"),
    # --- 17 ---
    ("CoinTracker replaced Koinly on 2026-01-27 because Koinly misclassified the Lido staking rewards as income twice and the IRS 1099-DIV match failed both years.", "decision", "cross", False,
     [("CoinTracker", "service"), ("Koinly", "service"), ("2026-01-27", "date"), ("Lido", "service"), ("IRS", "organization")],
     [("CoinTracker", "Koinly", "REPLACES")],
     "why did the crypto tax tool swap after back-to-back staking misclassifications",
     "crypto tax software staking rewards classification irs mismatch swap"),
    # --- 18 ---
    ("The hardware Ledger Nano X finally replaced the MetaMask hot wallet for the long-term ETH stash on 2026-03-08 after the phishing attempt on 2026-03-05 scared the last holdouts off the hot side.", "milestone", "cross", False,
     [("Ledger Nano X", "infrastructure"), ("MetaMask", "service"), ("2026-03-08", "date"), ("ETH", "concept"), ("2026-03-05", "date")],
     [("Ledger Nano X", "MetaMask", "REPLACES")],
     "when did the long-term crypto move off the hot wallet and what pushed it",
     "hardware wallet migration phishing event hot wallet cold storage"),
    # --- 19 ---
    ("Relief washed over me when the Kraken 1099 reconciliation against the CoinTracker export finally balanced to the cent for the 2025 tax year.", "fact", "cross", False,
     [("Relief", "emotion"), ("Kraken", "organization"), ("CoinTracker", "service")],
     [("CoinTracker", "Kraken", "COMMUNICATES_WITH")],
     "what finally made the 2025 crypto tax reconciliation balance",
     "exchange 1099 reconciliation cent match crypto tax year balance"),
    # --- 20 ---
    ("Fidelity's Full View dashboard beats Personal Capital for the household net-worth roll-up because Personal Capital kept double-counting the Vanguard joint brokerage across two logins.", "preference", "cross", False,
     [("Fidelity", "organization"), ("Full View", "tool"), ("Personal Capital", "service"), ("Vanguard", "organization")],
     [("Full View", "Personal Capital", "PREFERS")],
     "which net-worth dashboard stopped double-counting the Vanguard balance",
     "net worth dashboard double count joint brokerage aggregator bug"),
    # --- 21 ---
    ("The retirement projection moved from a custom Monte Carlo in Excel to cFIREsim on 2026-02-17 because cFIREsim's sequence-of-returns visualization made the 30-year tail risk legible to Sarah.", "decision", "cross", False,
     [("Monte Carlo", "algorithm"), ("Excel", "tool"), ("cFIREsim", "service"), ("2026-02-17", "date"), ("Sarah", "person")],
     [("cFIREsim", "Excel", "REPLACES"), ("cFIREsim", "Sarah", "KNOWS")],
     "when did the retirement model swap and what made it worth explaining again",
     "retirement monte carlo sequence returns tail risk projection swap"),
    # --- 22 ---
    ("Projection Lab's tax-advantaged vs taxable split chart exposed that the backdoor Roth conversion timing was costing 2400 dollars a year in unnecessary ordinary income.", "fact", "cross", False,
     [("Projection Lab", "service"), ("Roth", "concept")],
     [],
     "what did the projection tool surface about the backdoor Roth timing",
     "tax advantaged taxable split chart backdoor roth conversion timing"),
    # --- 23 ---
    ("The 2026-02-04 Copilot update added the Apple Card transaction feed natively, which replaced the weekly PDF-to-CSV Hazel workflow on the Mac.", "milestone", "cross", False,
     [("2026-02-04", "date"), ("Copilot", "service"), ("Apple Card", "service"), ("PDF", "concept"), ("CSV", "concept"), ("Hazel", "tool"), ("Mac", "infrastructure")],
     [("Copilot", "Hazel", "REPLACES")],
     "when did the Apple Card feed stop needing the Hazel PDF scraper",
     "apple card feed native support pdf csv hazel workflow retirement"),
    # --- 24 ---
    ("Prefers Portfolio Performance over Sharesight for the Euro side of the book because Portfolio Performance handles the German Kapitalertragsteuer withholding cleanly where Sharesight's TER assumptions ignore it.", "preference", "cross", False,
     [("Portfolio Performance", "tool"), ("Sharesight", "service"), ("Kapitalertragsteuer", "concept")],
     [("Portfolio Performance", "Sharesight", "PREFERS")],
     "which portfolio tracker handles the German withholding tax correctly",
     "portfolio tracker german withholding tax capital gains ter assumption"),
    # --- 25 ---
    ("Afford Anything podcast episode 528 on 2026-02-11 reframed the emergency fund from three-months to a glide path tied to the household fixed expenses in Monarch.", "reference", "cross", False,
     [("Afford Anything", "publication"), ("2026-02-11", "date"), ("Monarch", "service")],
     [],
     "which podcast episode changed how the emergency fund target gets computed",
     "podcast episode emergency fund glide path fixed expense target reframe"),
    # --- 26 ---
    ("The Animal Spirits podcast stays in Overcast's starred playlist because the Tuesday episode talk-track shows up before the market open and the Smart Speed shaves 17 minutes off the 90-minute runtime.", "preference", "cross", False,
     [("Animal Spirits", "publication"), ("Overcast", "service"), ("Smart Speed", "method")],
     [("Overcast", "Animal Spirits", "USES")],
     "which podcast lives in the starred playlist and why does it fit the morning",
     "podcast playlist smart speed commute listening market open routine"),
    # --- 27 ---
    ("Anxiety spiked when the Schwab Intelligent Portfolios cash drag on 2026-03-11 ate two full percentage points of return versus the equivalent Vanguard three-fund lazy portfolio.", "problem", "cross", False,
     [("Anxiety", "emotion"), ("Schwab Intelligent Portfolios", "service"), ("2026-03-11", "date"), ("Vanguard", "organization")],
     [],
     "what surfaced the cash-drag problem on the Schwab robo compared to the lazy portfolio",
     "robo advisor cash drag performance gap three fund portfolio compare"),
    # --- 28 ---
    ("Etrade's Power E*TRADE platform replaced the Robinhood options workflow on 2026-01-18 because the P/L chart with the greeks overlay saved two hours of manual sheet building every expiry Friday.", "decision", "cross", False,
     [("Etrade", "organization"), ("Power E*TRADE", "tool"), ("Robinhood", "service"), ("2026-01-18", "date")],
     [("Power E*TRADE", "Robinhood", "REPLACES")],
     "when did the options platform swap and what did the new chart replace",
     "options platform pl chart greeks overlay expiry friday workflow swap"),
    # --- 29 ---
    ("The personal finance vault in Obsidian hit 412 notes on 2026-03-14 and the Dataview query for upcoming annual renewals (LastPass, Turbo, NYT) finally beat the Notion template it replaced.", "milestone", "cross", False,
     [("Obsidian", "tool"), ("2026-03-14", "date"), ("Dataview", "library"), ("LastPass", "service"), ("Notion", "tool")],
     [("Obsidian", "Notion", "REPLACES"), ("Dataview", "Obsidian", "DEPLOYED_ON")],
     "when did the personal finance vault pass the old Notion template in usefulness",
     "personal finance vault note count dataview annual renewal query"),
    # --- 30 ---
    ("Prefers Fidelity over Vanguard for the new Roth on 2026-02-25 because the Fidelity Zero index funds cover the same total-market slice at a zero expense ratio and the UI doesn't feel 15 years old.", "preference", "cross", False,
     [("Fidelity", "organization"), ("Vanguard", "organization"), ("2026-02-25", "date"), ("Roth", "concept")],
     [("Fidelity", "Vanguard", "PREFERS")],
     "why did the new Roth open at Fidelity instead of Vanguard",
     "brokerage choice zero expense ratio index fund ui modernization roth"),
    # --- 31 ---
    ("Yodlee's connection to the Capital One 360 savings account kept dropping every 14 days, so Tiller moved that feed over to the direct CSV import on 2026-02-19.", "problem", "cross", False,
     [("Yodlee", "service"), ("Capital One", "organization"), ("Tiller", "service"), ("2026-02-19", "date"), ("CSV", "concept")],
     [("Tiller", "Yodlee", "REPLACES")],
     "when did the Capital One feed stop going through the aggregator",
     "aggregator connection drop savings account manual csv fallback"),
    # --- 32 ---
    ("The Bogleheads wiki page on asset location drove the 2026-03-22 rebalance that pushed REITs into the HSA and kept the tax-inefficient bond fund out of the taxable brokerage.", "reference", "cross", False,
     [("Bogleheads", "organization"), ("2026-03-22", "date"), ("REITs", "concept"), ("HSA", "concept")],
     [],
     "which reference shaped the asset-location decisions in the spring rebalance",
     "asset location wiki rebalance reit hsa tax efficient placement"),
    # --- 33. noise ---
    ("Hmm, one moment.", "fact", "noise", True, [], [], None, None),
    # --- 34 ---
    ("The Choose FI Facebook group's Monarch-to-Lunch-Money thread from 2026-01-22 ran through fifty replies, and the consensus favored Lunch Money for folks already living in plain-text accounting.", "reference", "cross", False,
     [("Choose FI", "organization"), ("Facebook", "service"), ("Monarch", "service"), ("Lunch Money", "service"), ("2026-01-22", "date")],
     [],
     "where did the community tilt on the Monarch vs Lunch Money debate that month",
     "community thread discussion consensus plain text accounting crossover"),
    # --- 35 ---
    ("Wise's borderless multi-currency account replaced the Charles Schwab checking for foreign ATM withdrawals on 2026-03-01 because the real-time mid-market FX beat the Schwab end-of-day Visa rate.", "decision", "cross", False,
     [("Wise", "service"), ("Charles Schwab", "organization"), ("2026-03-01", "date"), ("Visa", "organization")],
     [("Wise", "Charles Schwab", "REPLACES")],
     "when did foreign ATM withdrawals move off Schwab and what beat it",
     "multi currency account atm withdrawal mid market fx rate advantage"),
    # --- 36 ---
    ("Empower Retirement's fee analyzer flagged a 0.92 percent expense ratio on the old 401k target-date fund, and the 2026-02-09 rollover to a Vanguard IRA saved an estimated 26 thousand over 25 years.", "milestone", "cross", False,
     [("Empower Retirement", "organization"), ("401k", "concept"), ("2026-02-09", "date"), ("Vanguard", "organization"), ("IRA", "concept")],
     [("Vanguard", "Empower Retirement", "REPLACES")],
     "when did the 401k rollover happen and what did the fee analyzer surface",
     "401k rollover expense ratio analyzer target date fund savings estimate"),
    # --- 37 ---
    ("Shake Shack shifted the frequent-coffee habit off the Starbucks app once the Copilot subscription audit called out 184 dollars a month in mobile-order lattes.", "fact", "cross", False,
     [("Shake Shack", "organization"), ("Starbucks", "organization"), ("Copilot", "service")],
     [("Copilot", "Starbucks", "RELATED_TO")],
     "what prompted the coffee-habit shift after the subscription audit",
     "subscription audit mobile order coffee habit spend surface shift"),
    # --- 38 ---
    ("The Charles Schwab Stock Slices feature replaced the fractional-share workflow on Robinhood for the kids' UTMA accounts on 2026-02-06 because Schwab covers dividend reinvestment where Robinhood paused it.", "decision", "cross", False,
     [("Charles Schwab", "organization"), ("Stock Slices", "service"), ("Robinhood", "service"), ("2026-02-06", "date"), ("UTMA", "concept")],
     [("Stock Slices", "Robinhood", "REPLACES")],
     "when did the kids' UTMA fractional-share workflow move off Robinhood",
     "fractional share dividend reinvestment custodial account utma swap"),
    # --- 39 ---
    ("Prefers the Discover it cash-back card over the Citi Double Cash for the grocery rotating category because the Discover 5-percent tiers align with the Lunch Money tag-based reimbursement report.", "preference", "cross", False,
     [("Discover", "organization"), ("Citi Double Cash", "service"), ("Lunch Money", "service")],
     [("Discover", "Citi Double Cash", "PREFERS")],
     "which cash-back card wins for groceries and how does the budget app see it",
     "cash back rotating category grocery tag reimbursement report card"),
    # --- 40 ---
    ("The Sankey diagram exported from SankeyMATIC finally made the 2025 cash-flow picture clear to my dad, and the retirement drawdown strategy conversation went better than the prior five attempts.", "milestone", "cross", False,
     [("SankeyMATIC", "tool"), ("dad", "person")],
     [("dad", "SankeyMATIC", "KNOWS")],
     "what visualization finally made the cash-flow story land with family",
     "sankey diagram cash flow visualization family finance conversation"),
    # --- 41 ---
    ("The Money Guy Show's Financial Order of Operations poster anchors the 2026 savings waterfall, and the HSA step pushed ahead of the taxable brokerage once the max match caught up.", "reference", "cross", False,
     [("Money Guy Show", "publication"), ("2026", "date"), ("HSA", "concept")],
     [],
     "which framework anchors the 2026 savings order and what moved up",
     "financial order operations savings waterfall hsa brokerage priority"),
    # --- 42 ---
    ("Qube Money's digital envelopes replaced the cash-in-envelope system on 2026-01-19 because the physical mall trips stopped when the debit card blocked the category swipe at the register.", "decision", "cross", False,
     [("Qube Money", "service"), ("2026-01-19", "date")],
     [],
     "when did the envelopes go digital and what made the switch stick",
     "digital envelope budget card block physical cash replacement"),
    # --- 43 ---
    ("The Rockstar Finance weekly roundup, now hosted under Cashflow Cookbook after the 2026-02 handoff, still lands in Feedly every Friday and drives the weekend personal finance reading queue.", "architecture", "cross", False,
     [("Rockstar Finance", "publication"), ("Cashflow Cookbook", "publication"), ("Feedly", "service")],
     [("Cashflow Cookbook", "Rockstar Finance", "REPLACES"), ("Feedly", "Cashflow Cookbook", "USES")],
     "how does the weekly personal finance reading queue get filled now",
     "finance blog roundup feed reader weekly queue successor handoff"),
    # --- 44 ---
    ("Portfolio Visualizer's backtest of a Golden Butterfly versus a three-fund on 2026-03-05 convinced me that the 20-percent long-term-Treasury slice was worth the rebalance tax drag in taxable accounts.", "milestone", "cross", False,
     [("Portfolio Visualizer", "service"), ("Golden Butterfly", "pattern"), ("2026-03-05", "date")],
     [],
     "which backtest sealed the Golden Butterfly allocation decision and when",
     "backtest tool lazy portfolio allocation treasury slice tax drag"),
    # --- 45 ---
    ("Satisfaction set in once the Boxcar-derived mileage log in Tripcatcher replaced the paper notebook, and the 2025 Schedule C deduction audit took 25 minutes instead of a weekend.", "milestone", "cross", False,
     [("Satisfaction", "emotion"), ("Boxcar", "tool"), ("Tripcatcher", "service"), ("Schedule C", "concept")],
     [("Tripcatcher", "Boxcar", "BUILDS_ON")],
     "when did the mileage log digitization actually pay off for Schedule C",
     "mileage log digital schedule c deduction audit time savings paper"),
    # --- 46 ---
    ("The Bogleheads forum thread on 2026-02-13 explained the Gemini Earn aftermath clearly enough that my sister Priya moved her emergency fund out of BlockFi-like yield products into a Treasury Direct bill ladder.", "reference", "cross", False,
     [("Bogleheads", "organization"), ("2026-02-13", "date"), ("Gemini Earn", "service"), ("Priya", "person"), ("BlockFi", "organization"), ("Treasury Direct", "service")],
     [("Priya", "Treasury Direct", "USES")],
     "which forum post drove the move out of crypto yield into a T-bill ladder",
     "crypto yield product aftermath t bill ladder emergency fund swap"),
    # --- 47 ---
    ("Prefers the ERN Safe Withdrawal Rate spreadsheet over the Trinity Study rule-of-thumb because the glide-path sensitivity to CAPE-10 starting valuations actually shows up in the worst-case bands.", "preference", "cross", False,
     [("ERN", "person"), ("Trinity Study", "method"), ("CAPE-10", "concept")],
     [("ERN", "Trinity Study", "PREFERS")],
     "which withdrawal-rate tool wins when the starting valuation matters",
     "safe withdrawal rate cape starting valuation sensitivity glide path"),
    # --- 48 ---
    ("The Phoenix Life Planning book's goal-based questions on 2026-03-29 rewrote the early-retirement target from a dollar number to a weekly-rhythm sketch, and the FIRE spreadsheet got three new lifestyle columns.", "milestone", "cross", False,
     [("Phoenix Life Planning", "publication"), ("2026-03-29", "date"), ("FIRE", "concept")],
     [],
     "when did the FIRE target shift from dollars to a lifestyle rhythm",
     "life planning goal based retirement target lifestyle columns reframe"),
    # --- 49 ---
    ("Excitement hit when the Treasury Direct auto-roll on 2026-03-20 pushed the 13-week T-bill ladder into place without a single manual trade, and the Beancount import caught the CUSIP correctly the first time.", "milestone", "cross", False,
     [("Excitement", "emotion"), ("Treasury Direct", "service"), ("2026-03-20", "date"), ("Beancount", "tool"), ("CUSIP", "concept")],
     [("Beancount", "Treasury Direct", "COMMUNICATES_WITH")],
     "when did the T-bill ladder go on autopilot and what caught the CUSIP cleanly",
     "t bill ladder auto roll treasury direct cusip import first try"),
    # --- 50 ---
    ("The Personal Finance subreddit's weekly wiki link to the prime directive flowchart still wins for onboarding new folks, and my cousin Dev hit the emergency-fund milestone on 2026-03-24 after three months on the flowchart.", "milestone", "cross", False,
     [("Personal Finance", "publication"), ("Dev", "person"), ("2026-03-24", "date")],
     [("Dev", "Personal Finance", "KNOWS")],
     "when did Dev hit the emergency-fund milestone from the flowchart",
     "prime directive flowchart emergency fund milestone reddit onboarding"),
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
