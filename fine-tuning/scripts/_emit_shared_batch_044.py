"""One-off emitter for shared-base batch-044 — personal domain (personal finance / investing / money habits slice).

Writes 50 rows to data/v2/shared/batch_044.tmp.jsonl with ids shared-02151..02200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_044.tmp.jsonl"
ID_OFFSET = 2150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Moved the emergency fund from Marcus at 4.10% to Wealthfront Cash at 4.85% on 2026-02-03; the extra yield works out to about £31 a month on the balance.", "decision", "personal", False,
     [("Marcus", "organization"), ("Wealthfront Cash", "service"), ("2026-02-03", "date")],
     [("Wealthfront Cash", "Marcus", "REPLACES")],
     "where did the rainy-day cash migrate for a better yield and on what date",
     "high yield savings rate jump cash parking move date monthly gain"),
    # --- 2 ---
    ("The household three-fund portfolio sits at 60% VTSAX, 30% VTIAX, 10% VBTLX; rebalance happens once per calendar quarter if any sleeve drifts over five points.", "architecture", "personal", False,
     [("three-fund portfolio", "pattern"), ("VTSAX", "concept"), ("VTIAX", "concept"), ("VBTLX", "concept")],
     [],
     "how are the index funds split across the family allocation and when does rebalancing fire",
     "three-fund Bogle household allocation domestic international bond drift threshold"),
    # --- 3 ---
    ("Opened a Roth IRA at Fidelity on 2026-01-14 and funded the 2025 contribution of $7,000 before the April deadline; auto-invested into FZROX same day.", "milestone", "personal", False,
     [("Roth IRA", "concept"), ("Fidelity", "organization"), ("2026-01-14", "date"), ("FZROX", "tool")],
     [],
     "when did the after-tax retirement account open and where did the first contribution land",
     "Roth account brokerage prior year contribution deadline zero-fee fund same day"),
    # --- 4 ---
    ("Prefers Monarch Money over YNAB for the shared budget; the partner view and auto-categorisation cut the weekly review from ninety to twenty minutes.", "preference", "personal", False,
     [("Monarch Money", "service"), ("YNAB", "service")],
     [("Monarch Money", "YNAB", "PREFERS")],
     "which budgeting tool won the household review slot and what did it save in time",
     "budget app couple shared ledger auto-category time reduction weekly"),
    # --- 5 ---
    ("Paid off the 22.9% Barclaycard balance of £4,200 on 2026-03-18 before adding to the brokerage again; the interest math simply beat any equity return expectation.", "decision", "personal", False,
     [("Barclaycard", "organization"), ("2026-03-18", "date"), ("brokerage", "service")],
     [],
     "when did the high-APR credit card debt clear and why did that jump the investing queue",
     "credit card payoff interest rate beats stock expected return sequence priority"),
    # --- 6 ---
    ("The backdoor Roth conversion routine happens every January: contribute $7,000 to the Traditional IRA at Schwab, convert two business days later, zero pro-rata thanks to no pre-tax balance.", "architecture", "personal", False,
     [("backdoor Roth", "method"), ("January", "date"), ("Traditional IRA", "concept"), ("Schwab", "organization"), ("pro-rata", "concept")],
     [],
     "how is the high-income retirement contribution workaround sequenced each year",
     "backdoor Roth mechanic non-deductible contribution convert rule clean basis timing"),
    # --- 7 ---
    ("The HSA at Lively is run as a stealth IRA: contributions maxed at $4,150, receipts scanned into Dropbox for later reimbursement, investments in VTI inside the account.", "architecture", "personal", False,
     [("HSA", "concept"), ("Lively", "service"), ("Dropbox", "service"), ("VTI", "concept")],
     [("HSA", "Lively", "LOCATED_IN")],
     "how is the medical savings account being used for long-horizon investing instead of immediate spend",
     "HSA stealth IRA receipt archive provider equity fund long-term reimburse later"),
    # --- 8 ---
    ("Refinanced the 6.8% mortgage with Rocket to a 5.375% thirty-year on 2026-02-25; closing costs of $3,800 break even at month eighteen on the payment delta.", "milestone", "personal", False,
     [("mortgage", "concept"), ("Rocket", "organization"), ("2026-02-25", "date")],
     [],
     "when did the home loan rate drop close and when does the refinance break even",
     "mortgage refi lender rate cut thirty year closing cost payback month"),
    # --- 9 ---
    ("The tax-loss harvesting sweep on 2025-12-29 booked $6,100 in losses by swapping VTI for ITOT; kept the allocation while banking the carry-forward.", "milestone", "personal", False,
     [("tax-loss harvesting", "method"), ("2025-12-29", "date"), ("VTI", "concept"), ("ITOT", "concept")],
     [("ITOT", "VTI", "REPLACES")],
     "when was the year-end loss capture done and which two funds swapped to stay invested",
     "year end tax loss harvest fund pair substitute wash sale avoid allocation hold"),
    # --- 10. noise ---
    ("Hang on, I want to grab coffee before we open the spreadsheet.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The 529 plan for Noah at Utah's my529 holds the Vanguard Moderate age-based track; auto-contribution of $400 monthly since 2024.", "reference", "personal", False,
     [("529 plan", "concept"), ("Noah", "person"), ("my529", "platform"), ("Vanguard Moderate age-based", "tool")],
     [("529 plan", "Noah", "APPLIES_TO")],
     "what college savings account is running for the kid and what track does it sit in",
     "529 college savings state plan child age-based glide path monthly auto fund"),
    # --- 12 ---
    ("Prefers Fidelity Go for the taxable brokerage over Betterment; the advisory fee drops to zero below $25,000 and the tax overlay is cleaner.", "preference", "personal", False,
     [("Fidelity Go", "service"), ("Betterment", "service")],
     [("Fidelity Go", "Betterment", "PREFERS")],
     "which robo-advisor won the taxable account and on what cost basis",
     "robo advisor pick taxable account fee tier under threshold tax overlay"),
    # --- 13 ---
    ("The donor-advised fund at Fidelity Charitable opened on 2025-11-10 with $15,000 of appreciated VTSAX; deduction goes on the 2025 return and grant-outs spread over three years.", "milestone", "personal", False,
     [("donor-advised fund", "concept"), ("Fidelity Charitable", "organization"), ("2025-11-10", "date"), ("VTSAX", "concept")],
     [],
     "when did the giving vehicle open and what was put in versus what gets granted out when",
     "DAF opening appreciated shares bunch deduction year grant schedule"),
    # --- 14 ---
    ("The cash-flow routine on the first of every month: paycheck lands, 401k and HSA already swept, then auto-transfers to brokerage and mortgage on the second business day.", "architecture", "personal", False,
     [("401k", "concept"), ("HSA", "concept"), ("brokerage", "service"), ("mortgage", "concept")],
     [],
     "how does the monthly money waterfall run from paycheck through the accounts",
     "paycheck waterfall pay yourself first automation sequence month start sweep"),
    # --- 15 ---
    ("Switched from Quicken to Actual Budget on 2026-01-30; the self-hosted server on the home NAS ended the $104 annual fee and kept ten years of imported history intact.", "decision", "personal", False,
     [("Quicken", "service"), ("Actual Budget", "service"), ("2026-01-30", "date"), ("home NAS", "place")],
     [("Actual Budget", "Quicken", "REPLACES")],
     "when did the money tracker migrate off the paid tool and where does it live now",
     "personal finance app migration self host subscription drop historical import preserved"),
    # --- 16 ---
    ("Prefers swapping jobs every three years over chasing the internal raise; the market bump averaged 24% versus 4% inside, even after benefits math.", "preference", "personal", False,
     [("jobs", "concept"), ("internal raise", "concept")],
     [("jobs", "internal raise", "PREFERS")],
     "which compensation strategy pays more over time compared to staying put for raises",
     "job hop vs internal raise salary growth benefit adjusted multi-year"),
    # --- 17 ---
    ("The emergency fund target climbed from three months to six months on 2026-03-01 after the layoff at the last company; parked as a CD ladder at Ally.", "decision", "personal", False,
     [("emergency fund", "concept"), ("2026-03-01", "date"), ("CD ladder", "method"), ("Ally", "organization")],
     [("emergency fund", "Ally", "LOCATED_IN")],
     "when did the safety-net size bump up and where is the cash held now",
     "emergency fund resize months expense layoff trigger certificate ladder bank"),
    # --- 18 ---
    ("The credit card churning hobby retired on 2026-02-12 after hitting a Chase 5/24 block; keeping only the Sapphire Preferred and the AmEx Platinum for now.", "decision", "personal", False,
     [("credit card churning", "activity"), ("2026-02-12", "date"), ("Chase", "organization"), ("Sapphire Preferred", "service"), ("AmEx Platinum", "service")],
     [],
     "when did the points-chasing habit end and which two cards stayed in the wallet",
     "churning stop rule block remaining premium cards travel points simplify"),
    # --- 19 ---
    ("The expense-splitting setup with Maya uses Splitwise for day-to-day and a single monthly settle-up to the joint Chase account; receipts photographed into the app.", "architecture", "personal", False,
     [("Maya", "person"), ("Splitwise", "platform"), ("Chase", "organization")],
     [("Splitwise", "Chase", "COMMUNICATES_WITH")],
     "how is shared spending tracked and reconciled with the partner each month",
     "partner expense split tracker monthly settle joint account receipts photo"),
    # --- 20 ---
    ("Net worth crossed £500,000 on 2026-04-01 for the first time; the brokerage gains and the mortgage paydown both contributed roughly half each over the past year.", "milestone", "personal", False,
     [("Net worth", "concept"), ("£500,000", "concept"), ("2026-04-01", "date")],
     [],
     "when did the half-million pound number tick over and what drove the jump this year",
     "net worth milestone crossing half million drivers split equity gain principal paydown"),
    # --- 21 ---
    ("The I Bond ladder started on 2024-10-01 with $10,000 a year via TreasuryDirect; each tranche gets tagged with the purchase date in the tracking spreadsheet.", "reference", "personal", False,
     [("I Bond", "concept"), ("2024-10-01", "date"), ("TreasuryDirect", "service")],
     [],
     "when did the inflation bond ladder start and how is each rung logged",
     "I bonds ladder inflation purchase annual cap tracking spreadsheet tag"),
    # --- 22 ---
    ("Crypto exposure is capped at 2% of the liquid portfolio and bought only in BTC and ETH at Coinbase; any excess trims back on the first of the quarter.", "architecture", "personal", False,
     [("Crypto", "concept"), ("BTC", "concept"), ("ETH", "concept"), ("Coinbase", "platform")],
     [],
     "how is the digital asset allocation fenced and where is it actually held",
     "crypto allocation cap rule two assets exchange quarterly trim rebalance"),
    # --- 23 ---
    ("The 401k at work hit the $23,500 contribution cap on 2025-10-22; the final paycheck surprise of $1,800 freed up for the brokerage after matching continued via true-up.", "problem", "personal", False,
     [("401k", "concept"), ("$23,500", "concept"), ("2025-10-22", "date"), ("brokerage", "service"), ("true-up", "concept")],
     [],
     "what happened when the workplace retirement cap hit early and where did the extra cash go",
     "401k cap early front load paycheck windfall true up match brokerage redirect"),
    # --- 24 ---
    ("Quarterly estimated taxes are auto-paid through EFTPS on the 15th of January, April, June, and September; the amount comes from the TurboTax planner draft.", "architecture", "personal", False,
     [("estimated taxes", "concept"), ("EFTPS", "platform"), ("15th", "date"), ("TurboTax", "tool")],
     [("estimated taxes", "EFTPS", "USES")],
     "how do the self-employment quarterly tax payments get sent and where does the figure come from",
     "quarterly estimate payment schedule federal portal planner draft amount"),
    # --- 25 ---
    ("Prefers a single high-limit Chase Sapphire Reserve to carrying three mid-tier cards for travel; the Priority Pass access and insurance coverage end the debate.", "preference", "personal", False,
     [("Chase Sapphire Reserve", "service"), ("Priority Pass", "service")],
     [("Chase Sapphire Reserve", "Priority Pass", "USES")],
     "which single travel card replaced the multi-card wallet and what perk sealed it",
     "travel credit card single high annual fee lounge access insurance consolidation"),
    # --- 26 ---
    ("The inheritance planning call with Mum on 2026-03-08 sorted the LPA and the will draft; solicitor Priya Nair to finalise both by end of May.", "milestone", "personal", False,
     [("Mum", "person"), ("2026-03-08", "date"), ("LPA", "concept"), ("Priya Nair", "person")],
     [("Priya Nair", "LPA", "CONFIGURES")],
     "when did the estate-planning conversation with the parent happen and who is drafting the paperwork",
     "estate planning parent conversation power of attorney will solicitor deadline"),
    # --- 27 ---
    ("The 0% balance transfer on the Barclaycard Platinum gave eighteen months of float; the £4,200 moved from the old Capital One on 2025-09-14 with a 3.4% fee.", "fact", "personal", False,
     [("Barclaycard Platinum", "service"), ("Capital One", "organization"), ("2025-09-14", "date")],
     [],
     "what zero-interest card soaked up the old balance and what was the transfer fee",
     "balance transfer card promo period fee percent source card move date"),
    # --- 28 ---
    ("The rule-of-25 target for coast-FI is £1.1 million at age 45; current trajectory from the projection spreadsheet lands at age 46 in the base scenario.", "reference", "personal", False,
     [("rule-of-25", "method"), ("coast-FI", "goal"), ("£1.1 million", "concept"), ("45", "date")],
     [],
     "what is the coast financial independence number and how far off is the current plan",
     "coast FI number age target projection spreadsheet base scenario gap"),
    # --- 29 ---
    ("Opened an UTMA at Schwab for Noah on 2025-12-01 with $2,500 of Grandma's gift; invested into SWTSX to avoid the kiddie-tax drag from dividends.", "milestone", "personal", False,
     [("UTMA", "concept"), ("Schwab", "organization"), ("Noah", "person"), ("2025-12-01", "date"), ("SWTSX", "concept"), ("kiddie-tax", "concept")],
     [],
     "when did the custodial account open for the child and how was the gift invested",
     "UTMA custodial account gift from grandparent growth fund kiddie tax dividend avoid"),
    # --- 30 ---
    ("The car refinance with PenFed on 2026-01-20 dropped the auto loan from 7.2% to 4.9% APR; three years left, $74 saved a month.", "milestone", "personal", False,
     [("PenFed", "organization"), ("2026-01-20", "date"), ("auto loan", "concept")],
     [],
     "when did the vehicle loan refinance land and what rate and savings came out",
     "auto loan refinance credit union rate cut term remaining monthly saving"),
    # --- 31 ---
    ("Prefers ETFs to mutual funds in the taxable account; the spread is tight enough on ITOT that the tax-efficiency gain beats the convenience hit.", "preference", "personal", False,
     [("ETFs", "concept"), ("mutual funds", "concept"), ("ITOT", "concept")],
     [("ETFs", "mutual funds", "PREFERS")],
     "which fund wrapper wins in the taxable slot and what makes the case clear",
     "ETF vs mutual fund taxable wrapper tax drag spread convenience tradeoff"),
    # --- 32 ---
    ("The annual financial review with Alex Chen, CFP on 2026-02-07 flagged the bond glidepath as too conservative; bumped equities from 65% to 72% inside the IRA.", "decision", "personal", False,
     [("Alex Chen", "person"), ("CFP", "field"), ("2026-02-07", "date"), ("IRA", "concept")],
     [("Alex Chen", "CFP", "IS_A")],
     "when was the yearly planner meeting and what allocation change came out of it",
     "CFP annual review glidepath too cautious equity bump retirement account"),
    # --- 33 ---
    ("The grocery budget overran every month of Q4 2025 by 18% because of the toddler feeding ramp; raised the envelope from £520 to £640 for 2026.", "problem", "personal", False,
     [("Q4 2025", "date"), ("toddler", "person"), ("envelope", "method")],
     [],
     "why did the food category blow its line item and what did the new allowance become",
     "budget overrun food category reason kid growth envelope resize new year"),
    # --- 34. noise ---
    ("Oh wait, I need to pull up the statement PDF first.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Contributed $8,300 to the family HSA on 2026-01-05 before the employer match window closed; HDHP coverage starts in February for the full year.", "milestone", "personal", False,
     [("HSA", "concept"), ("2026-01-05", "date"), ("HDHP", "concept"), ("February", "date")],
     [],
     "when did the family health savings max out and when does the qualifying plan kick in",
     "HSA family max contribution year start employer match window HDHP coverage"),
    # --- 36 ---
    ("Switched the travel points strategy from AmEx Membership Rewards to Chase Ultimate Rewards on 2026-02-20; the Hyatt transfer partner alone justified the move for the household.", "decision", "personal", False,
     [("AmEx Membership Rewards", "service"), ("Chase Ultimate Rewards", "service"), ("2026-02-20", "date"), ("Hyatt", "organization")],
     [("Chase Ultimate Rewards", "AmEx Membership Rewards", "REPLACES")],
     "when did the rewards currency pivot happen and which transfer partner tipped it",
     "points program switch transfer partner hotel chain household primary currency"),
    # --- 37 ---
    ("The mega-backdoor Roth path inside the 401k opened on 2026-01-15 after the plan doc update; $34,500 of after-tax contributions rolling out to the Roth each December.", "milestone", "personal", False,
     [("mega-backdoor Roth", "method"), ("401k", "concept"), ("2026-01-15", "date"), ("Roth", "concept"), ("December", "date")],
     [],
     "when did the workplace after-tax conversion route unlock and when does the rollout happen",
     "mega backdoor Roth plan amendment after tax bucket in-service conversion year end"),
    # --- 38 ---
    ("The high-yield-savings rate tracker in Google Sheets pulls APYs from Bankrate via IMPORTHTML; refreshes every Monday and flags any bank lagging by more than 20 basis points.", "architecture", "personal", False,
     [("high-yield-savings", "concept"), ("Google Sheets", "tool"), ("Bankrate", "organization"), ("IMPORTHTML", "api")],
     [("Google Sheets", "Bankrate", "COMMUNICATES_WITH")],
     "how does the HYSA rate monitor stay current and when does it nudge a switch",
     "HYSA rate tracker sheet scrape Monday refresh threshold basis point alert"),
    # --- 39 ---
    ("Prefers dollar-cost averaging on the fifteenth of each month to lump-sum on bonus week; the cash-flow smoothness and the no-regret framing keep Maya on board.", "preference", "personal", False,
     [("dollar-cost averaging", "method"), ("fifteenth", "date"), ("lump-sum", "method"), ("Maya", "person")],
     [("dollar-cost averaging", "lump-sum", "PREFERS")],
     "which investing cadence wins in the house over the one-shot deposit and why",
     "DCA vs lump sum bonus cadence partner comfort regret framing monthly timing"),
    # --- 40 ---
    ("The FSA dependent-care enrolment for 2026 maxed at $5,000 on 2025-11-15 open enrolment; daycare invoices get uploaded to WEX the first week of every month.", "reference", "personal", False,
     [("FSA", "concept"), ("2026", "date"), ("2025-11-15", "date"), ("WEX", "service")],
     [],
     "what pre-tax benefit is funding daycare and how do reimbursements flow through the portal",
     "FSA dependent care enrolment cap childcare receipt monthly upload portal"),
    # --- 41 ---
    ("Closed the Wells Fargo checking on 2026-02-28 after the ATM-fee creep; the primary chequing moved to Schwab Bank for the global refund and the overdraft line.", "milestone", "personal", False,
     [("Wells Fargo", "organization"), ("2026-02-28", "date"), ("Schwab Bank", "organization")],
     [("Schwab Bank", "Wells Fargo", "REPLACES")],
     "when did the old checking account close and which bank took over the daily spending",
     "checking account close fee creep switch primary bank ATM global refund"),
    # --- 42 ---
    ("The charitable giving rule is 5% of gross income, bunched every other year into the DAF; off-years keep only the church tithe and the local school appeal.", "architecture", "personal", False,
     [("charitable giving", "concept"), ("DAF", "concept"), ("church tithe", "concept"), ("school appeal", "event")],
     [],
     "what is the household giving structure and how does the bunching cadence run",
     "charity percent income bunching alternating year DAF off year baseline obligations"),
    # --- 43 ---
    ("Sold the last individual stock position, $4,800 of Apple from the 2018 ESPP, on 2026-03-12; portfolio is now 100% index funds and bond ETFs.", "milestone", "personal", False,
     [("Apple", "organization"), ("2018", "date"), ("ESPP", "concept"), ("2026-03-12", "date")],
     [],
     "when did the last single-name stock leave the portfolio and what changed in the mix",
     "last single stock sale legacy ESPP cleanup index only portfolio transition date"),
    # --- 44 ---
    ("The household cash-buffer floor in the Amex Savings checking is £2,500; any balance above that on the 25th sweeps to the Wealthfront Cash high-yield tier automatically.", "architecture", "personal", False,
     [("Amex Savings", "service"), ("£2,500", "concept"), ("Wealthfront Cash", "service")],
     [("Amex Savings", "Wealthfront Cash", "COMMUNICATES_WITH")],
     "how does the operating-cash buffer run and when does the excess get swept to higher yield",
     "checking buffer floor monthly sweep threshold higher yield tier automation"),
    # --- 45 ---
    ("The first-ever financial advisor engagement was a flat-fee review with Arbor Planning on 2026-02-18 at £1,500; the written plan lands within four weeks.", "milestone", "personal", False,
     [("Arbor Planning", "organization"), ("2026-02-18", "date")],
     [],
     "when did the first paid planner engagement start and what was the fee structure",
     "financial advisor first hire flat fee engagement plan deliverable timeline"),
    # --- 46 ---
    ("Prefers paying the mortgage biweekly over monthly once the refi closed; the thirteenth payment a year trims the thirty-year down to about twenty-six.", "preference", "personal", False,
     [("biweekly", "method"), ("monthly", "method"), ("refi", "concept")],
     [("biweekly", "monthly", "PREFERS")],
     "which mortgage payment schedule wins after the refinance and what does it shorten the loan to",
     "mortgage biweekly vs monthly extra payment year shave term principle"),
    # --- 47 ---
    ("The umbrella liability policy with Chubb went live on 2026-03-05 for $2 million coverage; annual premium $410 after the home and auto were already bundled.", "fact", "personal", False,
     [("umbrella liability", "concept"), ("Chubb", "organization"), ("2026-03-05", "date")],
     [],
     "when did the extra-liability policy activate and what does it cover and cost",
     "umbrella insurance coverage amount annual premium bundled discount activation date"),
    # --- 48 ---
    ("The target-date fund in the old 401k rolled over to the IRA at Vanguard on 2026-01-08; consolidation finally makes the annual rebalance a single screen.", "milestone", "personal", False,
     [("target-date fund", "concept"), ("401k", "concept"), ("IRA", "concept"), ("Vanguard", "organization"), ("2026-01-08", "date")],
     [("IRA", "401k", "REPLACES")],
     "when did the old employer retirement account roll over and what does the consolidation enable",
     "401k rollover IRA consolidation former employer single dashboard rebalance ease"),
    # --- 49 ---
    ("The small-business Solo 401k at E-Trade was opened on 2025-09-30 for the side consulting income; $12,400 of profit-sharing contribution went in on the final day of the year.", "milestone", "personal", False,
     [("Solo 401k", "concept"), ("E-Trade", "organization"), ("2025-09-30", "date")],
     [],
     "when did the one-person retirement account for the side income open and what was the first contribution",
     "solo 401k side business freelance income profit sharing year end contribution"),
    # --- 50 ---
    ("Tracks FIRE progress as a percentage of the £1.4 million target; current reading 62% as of 2026-03-31, up from 54% at the start of the year.", "reference", "personal", False,
     [("FIRE", "goal"), ("£1.4 million", "concept"), ("2026-03-31", "date")],
     [],
     "how is the early-retirement progress tracked and what is the latest reading",
     "FIRE progress percent target quarter reading year start compare movement"),
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
