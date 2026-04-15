"""One-off emitter for classification top-up batch-024 — contrastive_decision_architecture mode, personal finance slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_024.tmp.jsonl with ids class-02301..02400.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_024.tmp.jsonl"
ID_OFFSET = 2300
PAIR_OFFSET = 900

# (decision_text, decision_domain, architecture_text, architecture_domain)
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. emergency fund — HYSA move
    (
        "Switched the emergency fund from a Chase checking account to Marcus HYSA after I realised a year of inflation had eaten most of the interest.",
        "personal",
        "Six months of expenses sit in a Marcus HYSA at 4.1% APY, auto-funded via a $500 monthly transfer from the Chase checking account on the 5th of each month.",
        "personal",
    ),
    # 2. brokerage choice
    (
        "Moved the taxable brokerage from Robinhood to Fidelity after a third outage during a market open made me worry about execution reliability.",
        "personal",
        "Taxable investing runs through a Fidelity cash management account linked to a Fidelity brokerage, with dividends auto-reinvested and a monthly $1,000 buy order for VTI on the 15th.",
        "personal",
    ),
    # 3. 401k allocation
    (
        "Rebalanced the 401k from a target-date 2055 fund to a three-fund split after the expense ratio on the target-date fund came in at 0.75% versus 0.04% on the index funds.",
        "personal",
        "The 401k is 70% FXAIX (S&P 500), 20% FSPSX (international), and 10% FXNAX (US bonds), rebalanced quarterly and contributing 15% of salary up to the federal limit.",
        "personal",
    ),
    # 4. tax-advantaged account ordering
    (
        "Decided to max the HSA before the Roth IRA this year after reading that the triple tax advantage beats the Roth's single advantage when medical costs are expected to rise.",
        "personal",
        "Annual contribution order is 401k to employer match, then HSA to the family limit, then Roth IRA to the full $7,000, then back to the 401k up to the federal cap.",
        "personal",
    ),
    # 5. debt-payoff strategy
    (
        "Switched from the debt snowball to the debt avalanche after running the math showing the 24% store card would cost an extra $1,400 in interest if paid off last.",
        "personal",
        "Consumer debt is paid in avalanche order: the 24.99% Kohl's card, then the 21.5% Amex Blue, then the 6.8% federal student loan, with $1,200 extra principal per month split by priority.",
        "personal",
    ),
    # 6. mortgage refinance
    (
        "Refinanced the mortgage from a 6.75% 30-year to a 5.5% 15-year after the break-even on closing costs came in at 22 months and we planned to stay at least seven years.",
        "personal",
        "The primary residence carries a 15-year fixed mortgage at 5.5% with Rocket, $2,480 monthly PITI, escrowed property tax and homeowners insurance, and a biweekly payment schedule.",
        "personal",
    ),
    # 7. credit card stack
    (
        "Dropped the Chase Freedom Unlimited for the Citi Double Cash after realising the 1.5% everywhere rate was worse than a flat 2% with no rotating categories to track.",
        "personal",
        "The credit card stack is Amex Gold for dining and groceries, Citi Double Cash as the 2% catch-all, and the Chase Sapphire Preferred held only for the travel portal and trip insurance.",
        "personal",
    ),
    # 8. travel-card strategy
    (
        "Cancelled the Chase Sapphire Reserve and opened the Capital One Venture X after the $550 annual fee could no longer be justified without the old Priority Pass restaurants.",
        "personal",
        "Travel rewards funnel into a Venture X at 2x on everything, with the $300 travel credit used against Capital One Travel bookings and the 10,000-mile anniversary bonus offsetting the fee.",
        "personal",
    ),
    # 9. budgeting method
    (
        "Moved from spreadsheet-only budgeting to YNAB after the third month of categorising transactions by hand on Sunday nights became unsustainable.",
        "personal",
        "Budget lives in YNAB with four category groups (Immediate Obligations, True Expenses, Quality of Life, Just for Fun), zero-based each month and reconciled to the Ally checking account nightly.",
        "personal",
    ),
    # 10. bill automation
    (
        "Switched every recurring bill to autopay on a single Amex Blue Cash after missing a $9 electric bill triggered a 30-day late credit report hit.",
        "personal",
        "All recurring bills autopay to an Amex Blue Cash on the 1st of the month, the Amex autopays in full from Ally checking on the 25th, and a calendar alert on the 20th triggers a statement review.",
        "personal",
    ),
    # 11. savings buckets
    (
        "Stopped keeping all savings in one generic account after mixing the vacation and home-repair funds made it impossible to tell how much was actually available for the bathroom remodel.",
        "personal",
        "Short-term savings live in Ally buckets: Vacation at $150/month, Home Repair at $300/month, Car Replacement at $250/month, and Christmas at $100/month, each with a visible target.",
        "personal",
    ),
    # 12. kids' college fund
    (
        "Opened a Utah my529 plan over the in-state New York 529 after discovering the Utah plan's Vanguard underlying funds had expense ratios half of the home-state alternative.",
        "personal",
        "The kids' college savings sit in a Utah my529 account with an age-based moderate option, $400 monthly auto-contribution per child, and grandparents contributing via the Ugift link on birthdays.",
        "personal",
    ),
    # 13. estate planning
    (
        "Hired a local estate attorney to draft a revocable living trust after a cousin's probate dragged for eighteen months and cost the family around $40,000 in fees.",
        "personal",
        "The estate is structured as a revocable living trust holding the house and brokerage accounts, with pour-over wills, healthcare directives, and durable powers of attorney stored in a fireproof safe.",
        "personal",
    ),
    # 14. insurance stack
    (
        "Bumped umbrella coverage from $1M to $3M after a neighbour's slip-and-fall lawsuit made me realise one rental tenant injury could wipe out everything outside retirement.",
        "personal",
        "The insurance stack is a $3M umbrella over auto and home, Geico on two vehicles with 100/300/100 liability, a 20-year $1M term life policy, and long-term disability at 60% of salary through work.",
        "personal",
    ),
    # 15. charitable giving
    (
        "Switched from writing year-end checks to a Fidelity Charitable donor-advised fund after two years of bunching deductions made itemising meaningfully better than the standard deduction.",
        "personal",
        "Charitable giving flows through a Fidelity Charitable DAF funded with appreciated VTI shares every other December, granting $300 monthly to the chosen nonprofits and rebalancing the portfolio tax-free.",
        "personal",
    ),
    # 16. international transfers
    (
        "Stopped wiring to the UK account through the big bank and moved to Wise after a $45 wire fee plus a 3% FX markup cost more than a month of London rent.",
        "personal",
        "Cross-border transfers to the UK account run through Wise on the interbank rate with a ~$5 fee per transfer, scheduled on the 28th of each month to cover the £900 GBP rent payment.",
        "personal",
    ),
    # 17. foreign-currency hedging
    (
        "Decided to pre-buy twelve months of EUR after the dollar spiked 8% against the euro and a planned Italy sabbatical would otherwise be priced in a volatile currency.",
        "personal",
        "Foreign-currency reserves are held as €18,000 in a Wise multi-currency account and $5,000 in a Schwab Global Investing account in JPY, topped up quarterly based on planned spend.",
        "personal",
    ),
    # 18. side-income bookkeeping
    (
        "Started running the freelance income through a separate LLC checking account after a commingled Venmo paper trail turned a simple Schedule C into a three-weekend reconstruction project.",
        "personal",
        "Freelance income lands in a Relay Financial LLC checking account, is categorised weekly in Wave, pays quarterly estimated taxes via EFTPS, and sweeps 30% of net revenue to a separate tax-reserve savings account.",
        "personal",
    ),
    # 19. rental property ledger
    (
        "Switched the rental property books from a spreadsheet to Stessa after the 2024 Schedule E took two full days and I still missed a $1,100 HVAC deduction.",
        "personal",
        "The duplex is tracked in Stessa with both units as separate properties, bank feeds from the dedicated rental checking account, and receipts attached to each transaction for audit-ready Schedule E export.",
        "personal",
    ),
    # 20. crypto allocation
    (
        "Capped crypto holdings at 3% of net worth after the 2022 drawdown turned what had been a 12% position into a painful tax-loss-harvesting exercise.",
        "personal",
        "Crypto holdings are a fixed 3% target split 70% BTC and 30% ETH on Kraken, rebalanced annually back into the brokerage when it drifts past 4%, with cold storage on a Ledger for anything over $10,000.",
        "personal",
    ),
    # 21. HSA investing
    (
        "Moved the HSA from the default Fidelity cash sweep into FZROX after leaving $2,300 on the table over three years in uninvested contributions.",
        "personal",
        "The HSA is held at Fidelity with a $2,000 cash buffer for current-year medical spending and the remaining balance invested 100% in FZROX, receipts scanned into a Google Drive folder for future reimbursement.",
        "personal",
    ),
    # 22. Roth conversion ladder
    (
        "Started a Roth conversion ladder from the rollover IRA after early-retirement math showed five years of low-income conversions would cut lifetime tax paid by roughly $90,000.",
        "personal",
        "Each January converts $40,000 from the Traditional rollover IRA at Fidelity into the Roth IRA, staying under the 12% bracket, with a five-year seasoning clock tracked in a spreadsheet per conversion.",
        "personal",
    ),
    # 23. I-bonds
    (
        "Bought $10,000 in Series I Bonds at TreasuryDirect after the composite rate hit 9.62% and the HYSA was paying under 1% at the same time.",
        "personal",
        "Inflation-protected savings are $30,000 in Series I Bonds at TreasuryDirect, purchased $10,000 each January from 2022 through 2024, with the first tranche becoming penalty-free in 2027.",
        "personal",
    ),
    # 24. CD ladder
    (
        "Built a one-year CD ladder at Ally after sitting on $40,000 of house-downpayment cash in checking earning essentially nothing for eight months.",
        "personal",
        "Down-payment savings are a 12-month CD ladder of four $10,000 rungs maturing every three months at Ally, each rung auto-rolling into a new 12-month CD unless the house search concludes first.",
        "personal",
    ),
    # 25. backdoor Roth
    (
        "Started doing the backdoor Roth after my salary crossed the direct contribution phase-out and leaving $7,000 in Roth space on the table each year was no longer acceptable.",
        "personal",
        "The backdoor Roth runs every January: $7,000 non-deductible contribution to the Traditional IRA at Fidelity, converted to the Roth IRA within 48 hours, with the Traditional IRA otherwise empty to avoid pro-rata.",
        "personal",
    ),
    # 26. mega backdoor Roth
    (
        "Turned on after-tax 401k contributions with in-plan Roth conversion after the plan added the feature and the ~$30,000 of extra Roth space was too valuable to ignore.",
        "personal",
        "The mega backdoor Roth is configured at a 10% after-tax contribution rate in the Fidelity 401k with an automatic daily in-plan Roth conversion, targeting the $46,500 after-tax limit by December.",
        "personal",
    ),
    # 27. Social Security claiming
    (
        "Decided to delay Social Security from 67 to 70 after running OpenSocialSecurity and seeing a $58,000 higher expected lifetime benefit given our longevity assumptions.",
        "personal",
        "Retirement income is planned as portfolio drawdown from 65 to 70, then Social Security at 70 taking the full 132% delayed credit, with a small part-time consulting income filling the gap through 67.",
        "personal",
    ),
    # 28. Medicare supplement
    (
        "Picked Medigap Plan G over Medicare Advantage after a friend's out-of-network cancer care under Advantage cost $18,000 that Plan G would have covered.",
        "personal",
        "Healthcare at 65 is Original Medicare Part A and B, a Medigap Plan G policy with Mutual of Omaha at $160/month, and a standalone Part D drug plan selected each fall during open enrollment.",
        "personal",
    ),
    # 29. long-term care insurance
    (
        "Bought a hybrid long-term care policy at age 55 after watching a parent burn through $400,000 in four years of memory care with no coverage in place.",
        "personal",
        "Long-term care coverage is a Nationwide CareMatter II hybrid policy funded with a $100,000 single premium, providing $7,500/month of LTC benefit for up to 72 months with a residual life insurance benefit.",
        "personal",
    ),
    # 30. 529-to-Roth rollover
    (
        "Stopped front-loading the 529 beyond expected college costs after SECURE 2.0 opened a $35,000 lifetime 529-to-Roth rollover path for any remaining balance.",
        "personal",
        "The 529 is funded to 90% of projected college cost and any leftover balance is queued to roll over $7,000 per year into the beneficiary's Roth IRA starting in their first year with earned income.",
        "personal",
    ),
    # 31. donor-advised fund vs QCD
    (
        "Switched giving strategy at age 72 from the DAF to Qualified Charitable Distributions after RMDs pushed us into IRMAA and only QCDs would reduce AGI.",
        "personal",
        "Charitable giving after age 72 uses QCDs directly from the Traditional IRA up to $105,000 per year, handled by Vanguard's QCD form, which satisfies the RMD and keeps AGI below the IRMAA thresholds.",
        "personal",
    ),
    # 32. tax-loss harvesting
    (
        "Turned on automatic tax-loss harvesting at Wealthfront after manually selling losers in December left $3,000 of losses unused because I forgot wash-sale dates.",
        "personal",
        "Tax-loss harvesting runs daily inside a Wealthfront taxable account with two-ticker pairs (VTI/ITOT, VXUS/IXUS) to avoid wash sales, harvesting roughly $8,000 of losses per year against ordinary income.",
        "personal",
    ),
    # 33. asset location
    (
        "Rearranged accounts so bonds live only in the 401k after realising holding BND in the taxable account was throwing off $1,100 of annual interest taxed at 32%.",
        "personal",
        "Asset location keeps US and international equities in the taxable brokerage for qualified dividend treatment, REITs and bonds in the 401k, and the highest-growth equities in the Roth IRA for tax-free compounding.",
        "personal",
    ),
    # 34. rewards checking account
    (
        "Opened a SoFi Checking and Savings after the brick-and-mortar bank's 0.01% yield became indefensible with SoFi offering 4.6% on the same dollars.",
        "personal",
        "Day-to-day banking runs on SoFi Checking and Savings with direct deposit on the 1st and 15th, paying 4.6% on savings and 0.5% on checking, plus a $300 welcome bonus credited after the direct-deposit threshold.",
        "personal",
    ),
    # 35. car purchase financing
    (
        "Paid cash for the replacement Subaru instead of taking the 6.9% loan after the car-fund bucket had been funded for exactly this purpose for four years.",
        "personal",
        "Vehicle ownership is a five-year-old paid-off Subaru Outback with $250/month being redirected back into the Ally Car Replacement bucket, targeting $30,000 available cash by the next purchase in 2031.",
        "personal",
    ),
    # 36. parental financial support
    (
        "Started covering my mother's Medicare supplement premiums directly after her fixed Social Security income fell behind her medication costs two years running.",
        "personal",
        "Parental support is a $425 monthly autopay from joint checking directly to the Mutual of Omaha Medigap policy, with a separate $200 monthly Venmo for groceries, reviewed with a sibling each December.",
        "personal",
    ),
    # 37. prenup / joint finances
    (
        "Agreed with my spouse to keep inheritances in individually titled accounts after our estate attorney flagged that commingling into the joint brokerage would make them marital property.",
        "personal",
        "Household finances are a Yours-Mine-Ours model: a joint Ally checking for bills funded proportionally by income, individual Schwab brokerage accounts for separate property, and one joint Vanguard account for shared goals.",
        "personal",
    ),
    # 38. identity theft protection
    (
        "Froze credit at all three bureaus and dropped the paid LifeLock subscription after realising the freeze was free and did 90% of what the $30/month service claimed.",
        "personal",
        "Identity protection is a permanent credit freeze at Equifax, Experian, and TransUnion, a Chexsystems freeze, and quarterly pulls from annualcreditreport.com tracked in a recurring calendar reminder.",
        "personal",
    ),
    # 39. solo 401k for side business
    (
        "Opened a Solo 401k at Fidelity for the consulting LLC after the SEP IRA's pro-rata rule started interfering with the backdoor Roth from my W-2 job.",
        "personal",
        "The consulting LLC uses a Fidelity Solo 401k with a $23,000 employee Roth deferral and a 25%-of-net-SE-income employer traditional contribution, funded by March 15 each year after the CPA finalises K-1 numbers.",
        "personal",
    ),
    # 40. custodial brokerage for kids
    (
        "Opened UTMAs for both kids at Fidelity after the tax-free gift of $3,000 per year at the kiddie-tax threshold beat parking the birthday money in savings.",
        "personal",
        "Each child has a Fidelity UTMA holding 100% FZROX, funded by birthday and holiday gifts up to the kiddie-tax threshold of ~$2,600 of unearned income per year, to be retitled to them at age 21.",
        "personal",
    ),
    # 41. pet insurance
    (
        "Bought Trupanion on the puppy at week eight after a friend's adult dog's surgery without insurance came to $11,000 and the monthly premium seemed trivial in comparison.",
        "personal",
        "Pet coverage is a Trupanion policy at $62/month with a $500 per-condition deductible, autopay on the Amex Blue Cash, and claims submitted through the Trupanion app with vet direct-pay enabled.",
        "personal",
    ),
    # 42. will update cadence
    (
        "Refreshed the will and beneficiary designations after the second child was born because the old documents still named only the first child and a since-divorced sibling as guardian.",
        "personal",
        "Estate documents are reviewed every three years and after any major life event, with the will, trust, and beneficiary designations kept in a Trustworthy digital vault and a sealed paper copy with the estate attorney.",
        "personal",
    ),
    # 43. cash back aggregation
    (
        "Dropped the cashback credit card for Apple Pay with the Apple Card after a six-month test showed 3% on Apple Pay transactions beat the flat 2% card at the merchants we actually use.",
        "personal",
        "Daily spend is routed through Apple Pay backed by the Apple Card earning 3% at select merchants and 2% on all Apple Pay, with cashback swept monthly as a Daily Cash transfer to the Goldman Sachs savings linked to the card.",
        "personal",
    ),
    # 44. homeowners deductible
    (
        "Raised the homeowners deductible from $1,000 to $5,000 after the annual premium dropped $680 and the emergency fund could clearly absorb the higher out-of-pocket risk.",
        "personal",
        "The homeowners policy is a State Farm HO-3 with a $5,000 all-perils deductible, $650,000 dwelling coverage with extended replacement cost, and a separate $10,000 deductible for wind/hail given the storm exposure.",
        "personal",
    ),
    # 45. student loan repayment plan
    (
        "Moved federal student loans from the 10-year standard plan to SAVE after the income-driven payment dropped to $180/month and any balance after 20 years would be forgiven.",
        "personal",
        "Federal student loans are on the SAVE plan with a $180/month payment recalculated each July based on AGI, autopay enabled for the 0.25% interest deduction, and PSLF certification submitted annually by the employer.",
        "personal",
    ),
    # 46. gold / precious metals allocation
    (
        "Opened a 5% allocation to IAU inside the Roth IRA after a stagflation-scenario analysis showed equities-only portfolios had a 28% max drawdown during the 1970s.",
        "personal",
        "The precious-metals sleeve is a 5% target in IAU held inside the Roth IRA at Fidelity, rebalanced annually with equities when it drifts beyond the 4-6% band, and excluded from taxable accounts to avoid collectibles tax treatment.",
        "personal",
    ),
    # 47. real estate syndication
    (
        "Committed $50,000 to a multifamily syndication in Dallas after five years of accredited-investor due diligence showed that sponsor had hit every preferred-return target across three prior deals.",
        "personal",
        "Illiquid real estate is a $50,000 LP commitment in a Dallas multifamily syndication with a five-year hold, 8% preferred return, 70/30 split above pref, and K-1s filed each April through the CPA.",
        "personal",
    ),
    # 48. whole life cancellation
    (
        "Surrendered the $400k whole-life policy opened at age 22 after running the numbers showed a 1.8% internal rate of return and a term-plus-invest-the-difference strategy was clearly superior.",
        "personal",
        "Life insurance is now pure term: a $1M 20-year Haven Life policy on each spouse at $28/month, with the former whole-life cash value rolled 1035 into a low-cost Fidelity variable annuity to preserve the cost basis.",
        "personal",
    ),
    # 49. travel rewards stockpile rules
    (
        "Stopped hoarding Chase Ultimate Rewards points after a devaluation of the Hyatt transfer ratio knocked 20% off the effective value of the balance overnight.",
        "personal",
        "Travel points are capped at 150,000 Ultimate Rewards, 100,000 Amex MR, and 75,000 Capital One miles per account, with anything over the cap transferred to a booking within 60 days or redeemed as travel-portal cash.",
        "personal",
    ),
    # 50. annual money review cadence
    (
        "Started a formal January money day after two years of drifting allocations and missed contribution deadlines showed that a single annual sit-down prevented every recurring mistake.",
        "personal",
        "The household runs a January money day: net-worth snapshot in Monarch, rebalance across all accounts, update beneficiary designations, refresh the IPS document, and schedule the CPA tax-prep appointment for late February.",
        "personal",
    ),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (dec_text, dec_domain, arch_text, arch_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            dec_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            arch_id = f"class-{ID_OFFSET + (2 * i):05d}"
            f.write(json.dumps({"id": dec_id, "domain": dec_domain, "text": dec_text, "memory_type": "decision", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"id": arch_id, "domain": arch_domain, "text": arch_text, "memory_type": "architecture", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
