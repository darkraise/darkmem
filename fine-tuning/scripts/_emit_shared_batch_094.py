"""One-off emitter for shared-base batch-094 — cross domain.

Slice: shopping and e-commerce meets tech (resale marketplaces, deal trackers,
browser extensions, return-policy tooling, package aggregators, barcode apps,
subscription boxes, gift-card managers). Writes 50 rows to
data/v2/shared/batch_094.tmp.jsonl with ids shared-04651..04700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_094.tmp.jsonl"
ID_OFFSET = 4650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped raw Amazon listing checks for CamelCamelCamel after the 2026-02-11 KitchenAid deal turned out to have been cheaper three weeks earlier by forty dollars.", "decision", "cross", False,
     [("Amazon", "service"), ("CamelCamelCamel", "service"), ("2026-02-11", "date"), ("KitchenAid", "organization")],
     [("CamelCamelCamel", "Amazon", "IMPROVES_ON")],
     "which price-history tool took over for eyeballing Amazon deals",
     "price tracker history chart stand mixer deal drop lookup"),
    # --- 2 ---
    ("Prefers Vinted over eBay for offloading used clothing because Vinted's flat buyer-pays-shipping model avoids the eBay Standard Envelope weight fight on a linen shirt.", "preference", "cross", False,
     [("Vinted", "service"), ("eBay", "service"), ("eBay Standard Envelope", "service")],
     [("Vinted", "eBay", "PREFERS"), ("Vinted", "eBay", "REPLACES")],
     "which resale platform wins for unloading old clothes and why",
     "second hand clothing resale platform shipping cost buyer pays"),
    # --- 3 ---
    ("The Honey extension got uninstalled on 2026-01-28 after the PayPal-owned affiliate stripping rerouted a Wirecutter link and tanked the creator credit I actually wanted to give.", "decision", "cross", False,
     [("Honey", "service"), ("2026-01-28", "date"), ("PayPal", "organization"), ("Wirecutter", "publication")],
     [("Honey", "PayPal", "USES")],
     "when did the coupon extension get ripped off the browser and why",
     "coupon extension affiliate link hijack creator credit uninstall"),
    # --- 4 ---
    ("Slickdeals replaced the ad-hoc RSS feeds from dealnews and Ben's Bargains because the frontpage popularity filter already surfaces the Anker charger drop before the RSS polls.", "decision", "cross", False,
     [("Slickdeals", "service"), ("RSS", "protocol"), ("dealnews", "service"), ("Ben's Bargains", "service"), ("Anker", "organization")],
     [("Slickdeals", "dealnews", "REPLACES"), ("Slickdeals", "Ben's Bargains", "REPLACES")],
     "which deal aggregator took over for the older RSS-based sources",
     "deal aggregator frontpage vote community surface RSS polling"),
    # --- 5 ---
    ("17track pulls the Yanwen, SFC, and USPS hops for the AliExpress shipment into one thread so I stopped juggling three carrier sites for the same parcel.", "architecture", "cross", False,
     [("17track", "service"), ("Yanwen", "organization"), ("SFC", "organization"), ("USPS", "organization"), ("AliExpress", "service")],
     [("17track", "USPS", "COMMUNICATES_WITH"), ("17track", "Yanwen", "COMMUNICATES_WITH")],
     "how do the cross-border parcel hops get tracked in one place now",
     "multi carrier package tracking aggregator cross border last mile"),
    # --- 6. noise ---
    ("Give me a minute, I need to look that up.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("PriceRunner beat CamelCamelCamel for the UK Dyson search because CamelCamelCamel only watches Amazon and PriceRunner spans Currys and John Lewis on the same listing.", "preference", "cross", False,
     [("PriceRunner", "service"), ("CamelCamelCamel", "service"), ("UK", "place"), ("Dyson", "organization"), ("Amazon", "service"), ("Currys", "organization"), ("John Lewis", "organization")],
     [("PriceRunner", "CamelCamelCamel", "IMPROVES_ON")],
     "which price comparison tool works better for UK multi-retailer searches",
     "price comparison retailer spread UK Dyson listing cross store"),
    # --- 8 ---
    ("Depop replaced Poshmark for the Y2K denim flips because Depop's buyer base actually pays the 65-dollar ask while Poshmark's counter-offer reflex bottomed everything out at 30.", "decision", "cross", False,
     [("Depop", "service"), ("Poshmark", "service"), ("Y2K", "concept")],
     [("Depop", "Poshmark", "REPLACES")],
     "which resale app carried the vintage denim flips and why",
     "resale platform vintage denim buyer willingness counter offer"),
    # --- 9 ---
    ("The ReturnMate pickup service replaced trudging to a UPS dropoff on 2026-03-02 because the Zappos return for the three wrong-size Hoka runners finally got handed off at the door.", "milestone", "cross", False,
     [("ReturnMate", "service"), ("UPS", "organization"), ("2026-03-02", "date"), ("Zappos", "service"), ("Hoka", "organization")],
     [("ReturnMate", "UPS", "REPLACES")],
     "when did the shoe returns stop requiring a UPS run",
     "return pickup doorstep service dropoff replacement running shoe"),
    # --- 10 ---
    ("Barcode Lookup on the iPhone reads the EAN on the Trader Joe's frozen gyoza and pulls the Costco Kirkland equivalent price so the per-gram comparison actually lands in the cart.", "architecture", "cross", False,
     [("Barcode Lookup", "tool"), ("iPhone", "infrastructure"), ("EAN", "concept"), ("Trader Joe's", "organization"), ("Costco", "organization"), ("Kirkland", "organization")],
     [("Barcode Lookup", "iPhone", "DEPLOYED_ON")],
     "how does the frozen-aisle price comparison actually work in store",
     "barcode scan grocery comparison per unit price cross retailer"),
    # --- 11 ---
    ("Mercari replaced Craigslist for selling the used GPU on 2026-02-19 after the first two Craigslist lookie-loos no-showed and Mercari's label printed within three minutes of the sale.", "decision", "cross", False,
     [("Mercari", "service"), ("Craigslist", "service"), ("2026-02-19", "date"), ("GPU", "infrastructure")],
     [("Mercari", "Craigslist", "REPLACES")],
     "when did the hardware resale leave Craigslist for Mercari and why",
     "local resale platform flake no show prepaid label graphics card"),
    # --- 12 ---
    ("Frustration hit on 2026-03-14 when Amazon Prime's same-day promise slipped to three days for the printer ink because the 90210 fulfillment center hit a cluster outage.", "problem", "cross", False,
     [("Frustration", "emotion"), ("2026-03-14", "date"), ("Amazon Prime", "service")],
     [],
     "what went wrong with the same-day Amazon delivery that week",
     "same day delivery slip fulfillment outage prime promise miss"),
    # --- 13 ---
    ("The Rakuten extension replaced Honey on Chrome for cashback because Rakuten actually pays out quarterly to PayPal while Honey's Gold credits never converted to anything useful.", "decision", "cross", False,
     [("Rakuten", "service"), ("Honey", "service"), ("Chrome", "platform"), ("PayPal", "organization")],
     [("Rakuten", "Honey", "REPLACES")],
     "which cashback extension replaced Honey on the browser and why",
     "cashback extension payout mechanism gold credit quarterly check"),
    # --- 14 ---
    ("Etsy seller Mira Ceramics in Porto DMed directly through Instagram on 2026-02-25 to offer the seconds-sale mug at cost, and the off-platform payment via Wise saved both of us the Etsy fee.", "fact", "cross", False,
     [("Etsy", "service"), ("Mira Ceramics", "organization"), ("Porto", "place"), ("Instagram", "service"), ("2026-02-25", "date"), ("Wise", "service")],
     [("Mira Ceramics", "Etsy", "USES"), ("Mira Ceramics", "Instagram", "USES")],
     "how did the Porto ceramics seller arrange the seconds-mug purchase",
     "small shop direct message off platform payment seconds sale fee"),
    # --- 15 ---
    ("Aftership's iOS widget shows the Shopify merchant hop before Amazon's Logistics truck even scans, so the dashboard order status moves from label-created to out-for-delivery in one glance.", "architecture", "cross", False,
     [("Aftership", "service"), ("iOS", "infrastructure"), ("Shopify", "platform"), ("Amazon", "service")],
     [("Aftership", "Shopify", "COMMUNICATES_WITH"), ("Aftership", "iOS", "DEPLOYED_ON")],
     "how does the merchant-side tracking surface before the last-mile scan",
     "package tracker widget merchant webhook status aggregation"),
    # --- 16 ---
    ("PoshWholesale replaced the ad-hoc ClosetBundle buys on Poshmark because the wholesale tier hides the 20-percent Posh Affiliate cut on bulk liquidation lots.", "decision", "cross", False,
     [("PoshWholesale", "service"), ("Poshmark", "service"), ("ClosetBundle", "service"), ("Posh Affiliate", "service")],
     [("PoshWholesale", "ClosetBundle", "REPLACES")],
     "which wholesale sourcing channel took over for ClosetBundle buying",
     "bulk resale sourcing wholesale tier affiliate cut liquidation lot"),
    # --- 17 ---
    ("Prefers Facebook Marketplace over OfferUp for local furniture because the Messenger handoff actually surfaces the seller's mutual-friend signal before I drive to Queens for a couch.", "preference", "cross", False,
     [("Facebook Marketplace", "service"), ("OfferUp", "service"), ("Messenger", "service"), ("Queens", "place")],
     [("Facebook Marketplace", "OfferUp", "PREFERS")],
     "which local marketplace wins for big-furniture buys and why",
     "local marketplace trust signal mutual friend couch pickup"),
    # --- 18 ---
    ("The Dollar Shave Club subscription got downgraded to quarterly on 2026-03-07 because the razor cartridge usage dropped after the Philips OneBlade arrived and eight blades a month just piled up.", "decision", "cross", False,
     [("Dollar Shave Club", "service"), ("2026-03-07", "date"), ("Philips OneBlade", "infrastructure")],
     [("Philips OneBlade", "Dollar Shave Club", "REPLACES")],
     "when did the shaving subscription cadence change and why",
     "subscription cadence downgrade razor usage hybrid shaving tool"),
    # --- 19 ---
    ("Stockpile gift-card app replaced the shoebox of Starbucks and Target cards once the Stockpile balance check on 2026-01-12 caught a 45-dollar Sephora card I'd forgotten was active.", "milestone", "cross", False,
     [("Stockpile", "tool"), ("Starbucks", "organization"), ("Target", "organization"), ("2026-01-12", "date"), ("Sephora", "organization")],
     [("Stockpile", "Starbucks", "COMMUNICATES_WITH")],
     "what tool took over for the shoebox of physical gift cards",
     "gift card wallet balance check forgotten credit aggregation"),
    # --- 20 ---
    ("Excitement spiked when the ShopGoodwill auction for the 1970s Tenba bag closed at 18 dollars on 2026-02-22 after CamelCamelCamel flagged a fresh Amazon new-with-tags listing at 240.", "milestone", "cross", False,
     [("Excitement", "emotion"), ("ShopGoodwill", "service"), ("Tenba", "organization"), ("2026-02-22", "date"), ("CamelCamelCamel", "service"), ("Amazon", "service")],
     [("CamelCamelCamel", "Amazon", "COMMUNICATES_WITH")],
     "which auction win got vindicated by the Amazon new price",
     "thrift auction win arbitrage vintage bag price comparison"),
    # --- 21 ---
    ("PayPal Honey's comparison-shopping sidebar hijacked the eBay checkout page on 2026-02-05 by surfacing a fake dupe listing, so the extension got locked to Amazon domains only.", "problem", "cross", False,
     [("PayPal Honey", "service"), ("eBay", "service"), ("2026-02-05", "date"), ("Amazon", "service")],
     [("PayPal Honey", "eBay", "COMMUNICATES_WITH")],
     "what went wrong with the coupon sidebar on the eBay checkout flow",
     "comparison sidebar checkout hijack fake dupe extension scope"),
    # --- 22 ---
    ("Poshmark's bundle discount replaced the manual haggle over DMs for the Nike dunk resales because the 10-percent auto-trigger closes the sale before the buyer cools off.", "decision", "cross", False,
     [("Poshmark", "service"), ("Nike", "organization")],
     [],
     "how did the sneaker bundle negotiations stop eating DM time",
     "bundle discount auto trigger resale negotiation buyer urgency"),
    # --- 23 ---
    ("Curiosity drove me to install the Keepa extension alongside CamelCamelCamel because Keepa's sales-rank graph caught the Graco car seat restock a full day before the CCC price drop alert fired.", "decision", "cross", False,
     [("Curiosity", "emotion"), ("Keepa", "service"), ("CamelCamelCamel", "service"), ("Graco", "organization"), ("CCC", "service")],
     [("Keepa", "CamelCamelCamel", "IMPROVES_ON")],
     "which price tracker caught the restock before the usual alert",
     "sales rank graph restock signal price tracker overlap Amazon"),
    # --- 24 ---
    ("The 2026-03-18 Patagonia return got routed through Happy Returns because the QR-code drop at the Staples kiosk skipped the box-and-label ritual entirely.", "fact", "cross", False,
     [("2026-03-18", "date"), ("Patagonia", "organization"), ("Happy Returns", "service"), ("QR", "concept"), ("Staples", "organization")],
     [("Happy Returns", "Staples", "DEPLOYED_ON")],
     "how did the Patagonia jacket return get handled without repackaging",
     "box free return QR kiosk retail partner reverse logistics"),
    # --- 25 ---
    ("Klarna replaced Affirm for the 2026-02-14 Sonos Era 300 split because the 4-payment interest-free plan cleared faster than Affirm's soft-credit-pull step.", "decision", "cross", False,
     [("Klarna", "service"), ("Affirm", "service"), ("2026-02-14", "date"), ("Sonos Era 300", "infrastructure")],
     [("Klarna", "Affirm", "REPLACES")],
     "which buy-now-pay-later service handled the Sonos speaker split",
     "BNPL split installment plan soft credit pull speaker purchase"),
    # --- 26 ---
    ("The BirchBox subscription got canceled on 2026-02-01 because the 10-dollar-a-month sample curation turned into the same brand rotation three months in a row.", "decision", "cross", False,
     [("BirchBox", "service"), ("2026-02-01", "date")],
     [],
     "when did the beauty sample subscription get pulled and why",
     "subscription box cancel sample repetition curation fatigue"),
    # --- 27 ---
    ("Joy surged when the Bokksu matcha box landed the Morihan matcha I'd been hunting on the Tokyo Rakuten site since 2026-01-09.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Bokksu", "service"), ("Morihan", "organization"), ("Tokyo", "place"), ("Rakuten", "service"), ("2026-01-09", "date")],
     [("Bokksu", "Morihan", "PRODUCES")],
     "which subscription box finally landed the matcha I'd been chasing",
     "curated snack box rare brand sourcing cross border shopping"),
    # --- 28 ---
    ("The Amazon Prime membership auto-renewed at 139 dollars on 2026-01-22 before the Slickdeals thread about the 6.99 EBT tier surfaced, so the refund dispute ate two chat sessions.", "problem", "cross", False,
     [("Amazon Prime", "service"), ("2026-01-22", "date"), ("Slickdeals", "service"), ("EBT", "concept")],
     [],
     "what went wrong with the Prime membership renewal this year",
     "auto renewal membership tier discount missed refund dispute"),
    # --- 29 ---
    ("Paribus died in 2021 so the price-adjustment watcher moved to Earny on 2026-02-28, and Earny's Target receipt scan recovered eight dollars on a Switch game that dropped 48 hours after purchase.", "decision", "cross", False,
     [("Paribus", "service"), ("Earny", "service"), ("2026-02-28", "date"), ("Target", "organization"), ("Switch", "infrastructure")],
     [("Earny", "Paribus", "REPLACES")],
     "which price-adjustment tool replaced Paribus and proved the value",
     "price protection adjustment retroactive refund receipt scan"),
    # --- 30 ---
    ("Grocery Run's 2026-03-11 pricing comparison for Fairway versus Morton Williams surfaced the Hellmann's 30-ounce jar at a two-dollar delta, so the Chrome pin moved to Fairway for the week.", "fact", "cross", False,
     [("Grocery Run", "tool"), ("2026-03-11", "date"), ("Fairway", "organization"), ("Morton Williams", "organization"), ("Hellmann's", "organization"), ("Chrome", "platform")],
     [("Grocery Run", "Chrome", "DEPLOYED_ON")],
     "which grocery comparison tool drove the neighborhood store pick that week",
     "grocery price compare store swap chrome pin pantry staple"),
    # --- 31 ---
    ("Prefers Mercari Local over StockX for sneaker resale in Brooklyn because the in-person meet at the Atlantic Terminal cuts the StockX authentication fee that eats ten percent of gross.", "preference", "cross", False,
     [("Mercari Local", "service"), ("StockX", "service"), ("Brooklyn", "place"), ("Atlantic Terminal", "place")],
     [("Mercari Local", "StockX", "PREFERS")],
     "which resale channel wins for local sneaker handoffs and why",
     "local resale meetup sneaker authentication fee fee avoidance"),
    # --- 32 ---
    ("The Boxed.com shutdown on 2026-01-04 pushed the bulk pantry order back to Costco.com because Boxed's flat-rate shipping had been the only thing beating the Costco delivery markup.", "problem", "cross", False,
     [("Boxed.com", "service"), ("2026-01-04", "date"), ("Costco.com", "service"), ("Costco", "organization")],
     [("Costco.com", "Boxed.com", "REPLACES")],
     "what forced the bulk pantry order back onto the Costco site",
     "shutdown fallback bulk pantry flat rate shipping warehouse club"),
    # --- 33 ---
    ("PriceBlink's browser-bar comparison replaced a tab-shuffle routine for the Sony WH-1000XM6 hunt on 2026-02-17 because the popup surfaces B&H and Crutchfield prices without leaving the Best Buy listing.", "decision", "cross", False,
     [("PriceBlink", "service"), ("Sony WH-1000XM6", "infrastructure"), ("2026-02-17", "date"), ("B&H", "organization"), ("Crutchfield", "organization"), ("Best Buy", "organization")],
     [("PriceBlink", "Best Buy", "USES")],
     "which browser extension killed the headphone-shopping tab shuffle",
     "in page price comparison extension headphones retailer spread"),
    # --- 34. noise ---
    ("One moment, let me double check.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Gelato on Shopify printed the custom tote design for Rosa Alvarez's Etsy shop on-demand because the Etsy-native POD rate was eating thirty percent of her margin on the small batch.", "architecture", "cross", False,
     [("Gelato", "service"), ("Shopify", "platform"), ("Rosa Alvarez", "person"), ("Etsy", "service"), ("POD", "concept")],
     [("Rosa Alvarez", "Gelato", "USES"), ("Gelato", "Shopify", "DEPLOYED_ON")],
     "how did the custom tote fulfillment work off of Etsy's native POD",
     "print on demand margin fulfillment small batch Etsy Shopify bridge"),
    # --- 36 ---
    ("The Ikea click-and-collect locker at the Red Hook store replaced the white-glove delivery for the Kallax haul on 2026-03-09 because the 59-dollar delivery fee was not worth it for three flat packs.", "decision", "cross", False,
     [("Ikea", "organization"), ("Red Hook", "place"), ("Kallax", "concept"), ("2026-03-09", "date")],
     [],
     "how did the Kallax pickup get handled without paying for delivery",
     "click collect locker flat pack pickup delivery fee avoidance"),
    # --- 37 ---
    ("Instacart replaced FreshDirect on 2026-02-11 once the Whole Foods Market Prime 10-percent got applied at checkout and the FreshDirect delivery window was slipping four hours routinely.", "decision", "cross", False,
     [("Instacart", "service"), ("FreshDirect", "service"), ("2026-02-11", "date"), ("Whole Foods Market", "organization"), ("Prime", "service")],
     [("Instacart", "FreshDirect", "REPLACES")],
     "which grocery delivery service won for the household and why",
     "grocery delivery swap membership discount window reliability"),
    # --- 38 ---
    ("The gift-card fraud catcher Raise swapped out for GCX on 2026-01-30 because Raise's payout throttle held a 420-dollar Lowe's card for eleven days and GCX cleared in two.", "decision", "cross", False,
     [("Raise", "service"), ("GCX", "service"), ("2026-01-30", "date"), ("Lowe's", "organization")],
     [("GCX", "Raise", "REPLACES")],
     "which gift-card resale channel took over and why",
     "gift card resale payout delay clearing time throttle liquidity"),
    # --- 39 ---
    ("Prefers physical digital-receipt capture through Fetch Rewards over scanning into Expensify for grocery runs because Fetch's Kroger loyalty tie-in accrues points the Expensify OCR ignores.", "preference", "cross", False,
     [("Fetch Rewards", "service"), ("Expensify", "service"), ("Kroger", "organization"), ("OCR", "algorithm")],
     [("Fetch Rewards", "Expensify", "PREFERS")],
     "which receipt capture flow wins for grocery loyalty point accrual",
     "receipt scan rewards loyalty integration grocery cash back OCR"),
    # --- 40 ---
    ("Regret set in when the 2026-01-18 StockX sale of the Jordan 4 Military Black got flagged by the Verification Center for a minor midsole scuff and the 15-percent seller fee was still deducted.", "problem", "cross", False,
     [("Regret", "emotion"), ("2026-01-18", "date"), ("StockX", "service"), ("Jordan 4 Military Black", "concept"), ("Verification Center", "service")],
     [("Verification Center", "StockX", "IS_A")],
     "what soured the January Jordan 4 sale on the sneaker resale site",
     "authentication flag seller fee deduction rejected sneaker condition"),
    # --- 41 ---
    ("The Wyze Cam at the porch feeds PackageBot, a self-hosted Go daemon my neighbor Daichi wrote, that cross-references the Amazon OOB scan and texts me when a box actually lands on the mat.", "architecture", "cross", False,
     [("Wyze Cam", "infrastructure"), ("PackageBot", "tool"), ("Go", "language"), ("Daichi", "person"), ("Amazon", "service")],
     [("PackageBot", "Wyze Cam", "USES"), ("PackageBot", "Amazon", "COMMUNICATES_WITH"), ("Daichi", "Go", "USES")],
     "how does the porch camera actually confirm a package delivery now",
     "porch camera package detection self hosted daemon carrier scan"),
    # --- 42 ---
    ("Shipt replaced the Target Drive Up run on 2026-02-26 because the Shipt shopper flagged a missing tomato sauce before checkout instead of after the trunk got loaded.", "decision", "cross", False,
     [("Shipt", "service"), ("Target", "organization"), ("Drive Up", "service"), ("2026-02-26", "date")],
     [("Shipt", "Drive Up", "REPLACES")],
     "which Target fulfillment swap made the grocery run smoother",
     "target delivery replacement shopper contact substitute flag trunk"),
    # --- 43 ---
    ("The Ticketmaster to StubHub resale pipeline broke on 2026-03-25 for the Knicks playoff ticket because Ticketmaster's SafeTix barcode rotation killed the StubHub PDF download.", "problem", "cross", False,
     [("Ticketmaster", "service"), ("StubHub", "service"), ("2026-03-25", "date"), ("Knicks", "organization"), ("SafeTix", "service"), ("PDF", "concept")],
     [("SafeTix", "StubHub", "CONTRADICTS")],
     "what broke the ticket resale flow for the Knicks playoff seat",
     "rotating barcode ticket resale pdf download incompatibility"),
    # --- 44 ---
    ("Amazon Household replaced a separate Prime account for my brother Emmett on 2026-02-03 once the shared Kindle library and the Prime Video profile stopped clashing with the parental controls.", "milestone", "cross", False,
     [("Amazon Household", "service"), ("Prime", "service"), ("Emmett", "person"), ("2026-02-03", "date"), ("Kindle", "platform"), ("Prime Video", "service")],
     [("Amazon Household", "Prime", "REPLACES")],
     "when did the household share kick in and what did it fix",
     "household account consolidation shared library parental controls"),
    # --- 45 ---
    ("The Poshmark posh-credit on 2026-03-06 got converted to a Stockpile gift-card balance because Poshmark's withdrawal minimum is 50 dollars and the store credit was stuck at 43.", "decision", "cross", False,
     [("Poshmark", "service"), ("2026-03-06", "date"), ("Stockpile", "tool")],
     [],
     "how did the stuck Poshmark credit actually get converted to usable cash",
     "store credit withdrawal minimum gift card conversion liquidity"),
    # --- 46 ---
    ("Prefers PriceGrabber on desktop over the Shopping.com app for appliance research because PriceGrabber's merchant-rating rollup still catches the Abt Electronics offer that Shopping.com quietly dropped.", "preference", "cross", False,
     [("PriceGrabber", "service"), ("Shopping.com", "service"), ("Abt Electronics", "organization")],
     [("PriceGrabber", "Shopping.com", "PREFERS")],
     "which comparison site wins for appliance research and why",
     "appliance research merchant rating comparison engine desktop"),
    # --- 47 ---
    ("The Amazon return window got gamed once on 2026-02-20 when the 30-day limit on the Dyson V15 stretched because Camilla had bought it through her Prime student account that carries 60.", "fact", "cross", False,
     [("Amazon", "service"), ("2026-02-20", "date"), ("Dyson V15", "infrastructure"), ("Camilla", "person"), ("Prime", "service")],
     [("Camilla", "Prime", "USES")],
     "how did the Dyson V15 return stretch past the normal 30-day window",
     "return window extension student membership variant vacuum cleaner"),
    # --- 48 ---
    ("Trustpilot replaced the Google Reviews check for small Shopify shops because the Trustpilot flag on a dropshipper running through Oberlo caught the 2026-03-19 wallet purchase before checkout.", "decision", "cross", False,
     [("Trustpilot", "service"), ("Google Reviews", "service"), ("Shopify", "platform"), ("Oberlo", "service"), ("2026-03-19", "date")],
     [("Trustpilot", "Google Reviews", "REPLACES")],
     "which review source caught the dropshipper red flag before checkout",
     "trustpilot oberlo wallet purchase abandon shopify small store"),
    # --- 49 ---
    ("The Costco Citi Visa 4-percent on gas replaced the Amex BlueCash Preferred on 2026-01-15 once the Costco rotisserie-chicken routine pushed the warehouse spend past the Amex 250-dollar grocery cap.", "decision", "cross", False,
     [("Costco Citi Visa", "service"), ("Amex BlueCash Preferred", "service"), ("2026-01-15", "date"), ("Costco", "organization"), ("Amex", "organization")],
     [("Costco Citi Visa", "Amex BlueCash Preferred", "REPLACES")],
     "when did the warehouse-spending card swap happen and why",
     "warehouse club card swap category cap cash back rotation"),
    # --- 50 ---
    ("Relief washed in when Aftership surfaced the delayed Shein parcel at the Brooklyn DHL facility on 2026-03-28 and the chargeback threat to the Capital One card got pulled at the last minute.", "milestone", "cross", False,
     [("Relief", "emotion"), ("Aftership", "service"), ("Shein", "service"), ("Brooklyn", "place"), ("DHL", "organization"), ("2026-03-28", "date"), ("Capital One", "organization")],
     [("Aftership", "DHL", "COMMUNICATES_WITH")],
     "what kept the Shein chargeback from going through at the end of March",
     "tracker surfaced delayed parcel chargeback cancellation last mile"),
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
