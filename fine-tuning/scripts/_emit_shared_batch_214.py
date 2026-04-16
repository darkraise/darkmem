"""One-off emitter for shared-base batch-214 — personal domain (travel planning and long-trip logistics: flight deals, airline alliances, award miles, rewards bookings, accommodation, remote-work visas, travel insurance, trusted traveler programs, airport lounges, eSIMs).

Writes 50 rows to data/v2/shared/batch_214.tmp.jsonl with ids shared-10651..10700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_214.tmp.jsonl"
ID_OFFSET = 10650

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched my main travel card from Chase Sapphire Preferred to Chase Sapphire Reserve after the transfer-partner math on long-haul redemptions made the higher annual fee pay for itself on two trips a year.", "decision", "personal", False,
     [("Chase Sapphire Preferred", "organization"), ("Chase Sapphire Reserve", "organization")],
     [("Chase Sapphire Reserve", "Chase Sapphire Preferred", "REPLACES")],
     "which rewards card did I upgrade to and what analysis justified the higher annual fee",
     "chase sapphire reserve preferred upgrade transfer partner annual"),
    # --- 2 ---
    ("Plan to hit Portugal D7 visa eligibility by December so I can base out of Lisbon through next summer without juggling Schengen stamps every 90 days.", "milestone", "personal", False,
     [("Portugal D7", "concept"), ("Lisbon", "place"), ("Schengen", "concept")],
     [("Portugal D7", "Schengen", "APPLIES_TO")],
     "which remote-work residency am I lining up for Lisbon and what rolling limit does it sidestep",
     "portugal d7 lisbon schengen 90 day remote work visa"),
    # --- 3 ---
    ("Book all star-alliance long-hauls through ANA Mileage Club rather than United MileagePlus because the round-the-world chart is still priced on the old zone system.", "decision", "personal", False,
     [("ANA Mileage Club", "organization"), ("United MileagePlus", "organization"), ("round-the-world", "concept")],
     [("ANA Mileage Club", "United MileagePlus", "PREFERS")],
     "which miles program do I route star alliance redemptions through and why not the US carrier",
     "ana united mileageplus star alliance round world zone chart"),
    # --- 4 ---
    ("Every deal search now starts in Google Flights with the explore map, then confirms routing in ITA Matrix; Kayak multi-city is only for the weird open-jaw itineraries neither handles cleanly.", "architecture", "personal", False,
     [("Google Flights", "service"), ("ITA Matrix", "service"), ("Kayak", "service"), ("open-jaw", "concept")],
     [("Google Flights", "ITA Matrix", "COMMUNICATES_WITH"), ("Kayak", "open-jaw", "APPLIES_TO")],
     "which three search tools layer together for my deal workflow and which one handles open jaws",
     "google flights ita matrix kayak multi city open jaw explore"),
    # --- 5 ---
    ("Award Wallet is the single source of truth for every loyalty balance across twelve programs; the monthly email digest is the only reason I ever remember that Alaska Mileage Plan miles expire.", "fact", "personal", False,
     [("Award Wallet", "service"), ("Alaska Mileage Plan", "organization")],
     [("Award Wallet", "Alaska Mileage Plan", "APPLIES_TO")],
     "which aggregator keeps me on top of loyalty balances and flags the Alaska expiry risk",
     "award wallet loyalty balance alaska mileage plan expire digest"),
    # --- 6 ---
    ("AwardHacker is the go-to for picking the cheapest partner chart on any given route; last week it surfaced that Aeroplan quotes Tokyo-to-London for fewer miles than British Airways Avios despite both being Oneworld-adjacent.", "reference", "personal", False,
     [("AwardHacker", "service"), ("Aeroplan", "organization"), ("Avios", "concept"), ("Oneworld", "organization")],
     [("AwardHacker", "Aeroplan", "APPLIES_TO")],
     "which tool do I use to pick the cheapest partner chart and what odd pricing did it surface recently",
     "awardhacker aeroplan avios oneworld tokyo london chart partner"),
    # --- 7 ---
    ("Locked in a standing rule to book window seats on the left side of widebodies after spending an hour on Seat Guru reading reviews about the recline-blocking bulkheads on the right rail.", "decision", "personal", False,
     [("Seat Guru", "service"), ("bulkhead", "concept")],
     [("Seat Guru", "bulkhead", "APPLIES_TO")],
     "which seat orientation do I lock in on widebodies and which site informed the rule",
     "seat guru window left widebody bulkhead recline review"),
    # --- 8 ---
    ("The newsletter stack is Going, Scott's Cheap Flights, and Secret Flying: the first two for mistake fares out of my home airport, Secret Flying for error fares everywhere else.", "architecture", "personal", False,
     [("Going", "service"), ("Scott's Cheap Flights", "service"), ("Secret Flying", "service"), ("mistake fares", "concept")],
     [("Going", "mistake fares", "APPLIES_TO"), ("Secret Flying", "mistake fares", "APPLIES_TO")],
     "which three deal newsletters split my alerting between home airport and everywhere else",
     "going scott cheap flights secret flying mistake fare newsletter"),
    # --- 9 ---
    ("Hit the lifetime 100k miles threshold on United MileagePlus last October; the Million Miler track is still three trips a year for eight years, so the target is slipping.", "milestone", "personal", False,
     [("United MileagePlus", "organization"), ("Million Miler", "concept"), ("October", "date")],
     [("Million Miler", "United MileagePlus", "APPLIES_TO")],
     "which loyalty milestone did I cross last October and how far off is the lifetime track",
     "united mileageplus million miler 100k lifetime october track"),
    # --- 10. noise ---
    ("The corner bakery started stocking a rosemary focaccia on Wednesdays and it vanishes by eleven every time.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Global Entry interview slot finally cleared at Newark after a four-month backlog; TSA PreCheck falls out of it for free, so the CLEAR membership renewal got cancelled.", "milestone", "personal", False,
     [("Global Entry", "concept"), ("Newark", "place"), ("TSA PreCheck", "concept"), ("CLEAR", "organization")],
     [("Global Entry", "TSA PreCheck", "PRODUCES"), ("Global Entry", "CLEAR", "REPLACES")],
     "which trusted traveler slot cleared in Newark and which paid membership did it let me drop",
     "global entry newark tsa precheck clear cancel interview trusted"),
    # --- 12 ---
    ("NEXUS application submitted alongside the Global Entry renewal because the land-border reciprocity means the Vancouver weekend trips stop burning an hour at the Peace Arch crossing.", "decision", "personal", False,
     [("NEXUS", "concept"), ("Global Entry", "concept"), ("Vancouver", "place"), ("Peace Arch", "place")],
     [("NEXUS", "Global Entry", "EXTENDS"), ("NEXUS", "Peace Arch", "APPLIES_TO")],
     "which trusted traveler program stacks with Global Entry for the Vancouver land border run",
     "nexus global entry vancouver peace arch land border weekend"),
    # --- 13 ---
    ("SafetyWing Nomad Insurance covers the rolling twelve-month base policy; Allianz only gets bought on top for ski weeks because the adventure sports exclusion in SafetyWing bit me in Hakuba.", "architecture", "personal", False,
     [("SafetyWing", "organization"), ("Allianz", "organization"), ("Hakuba", "place"), ("adventure sports", "activity")],
     [("SafetyWing", "adventure sports", "APPLIES_TO"), ("Allianz", "SafetyWing", "EXTENDS")],
     "which travel insurer runs my base policy and which one tops up for ski trips after the Hakuba gap",
     "safetywing nomad allianz hakuba adventure sport exclusion ski"),
    # --- 14 ---
    ("Priority Pass lounge access came through the Capital One Venture X and the Amex Platinum; since the Venture X guest allowance is unlimited, the Platinum lounge benefit is mostly redundant on solo trips.", "fact", "personal", False,
     [("Priority Pass", "service"), ("Capital One Venture X", "organization"), ("Amex Platinum", "organization")],
     [("Capital One Venture X", "Priority Pass", "PRODUCES"), ("Amex Platinum", "Priority Pass", "PRODUCES")],
     "which two cards grant Priority Pass and which one wins on guest allowance",
     "priority pass venture x amex platinum guest lounge solo"),
    # --- 15 ---
    ("Airalo is the default eSIM provider for one-off country trips; Saily took over for long European hops because the regional Europe plan is cheaper per gigabyte once the trip crosses three countries.", "decision", "personal", False,
     [("Airalo", "service"), ("Saily", "service"), ("eSIM", "concept")],
     [("Saily", "Airalo", "REPLACES"), ("Airalo", "eSIM", "IS_A")],
     "which eSIM provider do I default to and when does the Europe-wide alternative take over",
     "airalo saily esim europe regional gigabyte multi country"),
    # --- 16 ---
    ("Holafly stays on the shelf because the unlimited-data marketing hides a throttle after the first five gigabytes; the smaller Airalo plans are genuinely metered which is easier to reason about.", "problem", "personal", False,
     [("Holafly", "service"), ("Airalo", "service"), ("throttle", "concept")],
     [("Holafly", "throttle", "APPLIES_TO")],
     "why does Holafly stay off the eSIM short list and what is the hidden cap behind its unlimited label",
     "holafly airalo unlimited throttle five gigabyte hidden cap"),
    # --- 17 ---
    ("Accommodation search usually starts on Booking.com for chain hotels, Agoda for Southeast Asia, and Trip.com as the tiebreaker because its member rate sometimes undercuts both by fifteen percent.", "architecture", "personal", False,
     [("Booking.com", "service"), ("Agoda", "service"), ("Trip.com", "service"), ("Southeast Asia", "place")],
     [("Agoda", "Southeast Asia", "APPLIES_TO"), ("Trip.com", "Booking.com", "IMPROVES_ON")],
     "which three hotel aggregators do I layer and which one tends to undercut the others",
     "booking agoda trip com southeast asia chain member rate"),
    # --- 18 ---
    ("Long stays are split between Airbnb and Vrbo: Airbnb for city apartments where the reviews matter most, Vrbo for beach houses because family hosts tend to list there over Airbnb.", "preference", "personal", False,
     [("Airbnb", "service"), ("Vrbo", "service"), ("beach house", "concept")],
     [("Airbnb", "Vrbo", "RELATED_TO"), ("Vrbo", "beach house", "APPLIES_TO")],
     "how do I split long stays between Airbnb and Vrbo based on property type",
     "airbnb vrbo beach house city apartment long stay split"),
    # --- 19 ---
    ("Expedia and Hotels.com got dropped from the rotation after the loyalty free-night program changed to variable pricing; the old one-free-per-ten stays was the only thing keeping them competitive.", "problem", "personal", False,
     [("Expedia", "service"), ("Hotels.com", "service"), ("free-night program", "concept")],
     [("Expedia", "free-night program", "APPLIES_TO"), ("Hotels.com", "free-night program", "APPLIES_TO")],
     "which two hotel sites left the rotation after their loyalty structure changed and why",
     "expedia hotels com free night variable ten stay loyalty"),
    # --- 20 ---
    ("The Points Guy and One Mile at a Time are the daily read; The Points Guy for the US card churn content, One Mile at a Time for the international premium-cabin trip reports that actually describe catering differences.", "reference", "personal", False,
     [("The Points Guy", "publication"), ("One Mile at a Time", "publication")],
     [("The Points Guy", "One Mile at a Time", "RELATED_TO")],
     "which two travel blogs split my daily reading between US churn and international cabin reviews",
     "points guy one mile at time churn premium cabin catering"),
    # --- 21 ---
    ("Flying Blue Promo Rewards drop on the first of every month; set a calendar reminder so I can snipe the Paris-to-anywhere deals before they sell out by day three.", "reference", "personal", False,
     [("Flying Blue", "organization"), ("Promo Rewards", "concept"), ("Paris", "place")],
     [("Flying Blue", "Promo Rewards", "PRODUCES"), ("Promo Rewards", "Paris", "APPLIES_TO")],
     "which loyalty program drops promo awards monthly and what cadence do I set reminders for",
     "flying blue promo reward paris monthly first day calendar"),
    # --- 22 ---
    ("Barbados Welcome Stamp was the test run for year-long remote work in 2021; it proved the case for chasing the Spain digital nomad visa once the Portugal D7 queue cleared.", "milestone", "personal", False,
     [("Barbados Welcome Stamp", "concept"), ("Spain digital nomad", "concept"), ("Portugal D7", "concept"), ("2021", "date")],
     [("Spain digital nomad", "Barbados Welcome Stamp", "BUILDS_ON"), ("Portugal D7", "Spain digital nomad", "RELATED_TO")],
     "which 2021 remote-work program proved the pattern for the Spain and Portugal visa chase",
     "barbados welcome stamp spain digital nomad portugal d7 2021"),
    # --- 23 ---
    ("Estonia e-Residency is the administrative backbone for the invoicing LLC; it is not a visa and does not give physical stay rights, which I had to re-explain to the accountant twice.", "fact", "personal", False,
     [("Estonia e-Residency", "concept"), ("LLC", "organization"), ("accountant", "person")],
     [("Estonia e-Residency", "LLC", "APPLIES_TO")],
     "what does Estonia e-Residency actually cover and what does it explicitly not grant",
     "estonia e residency llc invoice accountant physical stay visa"),
    # --- 24 ---
    ("The Schengen 90/180 tracker is a pinned spreadsheet; any single day error compounds into an overstay a year later, so the calendar math stays cross-checked against the official calculator every quarter.", "architecture", "personal", False,
     [("Schengen", "concept"), ("spreadsheet", "tool"), ("overstay", "concept")],
     [("spreadsheet", "Schengen", "APPLIES_TO"), ("Schengen", "overstay", "CAUSES")],
     "how do I track the Schengen rolling limit and what is the compounding risk I guard against",
     "schengen 90 180 spreadsheet overstay tracker quarterly calculator"),
    # --- 25 ---
    ("Capital One Venture X earns flat two miles everywhere but the 10x on Capital One Travel is the real unlock; routing the car rentals through it this year beat the Chase Travel portal by about fourteen percent.", "fact", "personal", False,
     [("Capital One Venture X", "organization"), ("Capital One Travel", "service"), ("Chase Travel", "service"), ("car rental", "concept")],
     [("Capital One Travel", "Chase Travel", "IMPROVES_ON"), ("Capital One Travel", "car rental", "APPLIES_TO")],
     "which Capital One card earns category on the travel portal and how does it compare to Chase",
     "venture x capital one travel chase portal car rental 10x"),
    # --- 26 ---
    ("Amex Platinum is held for the Centurion Lounge network and the Fine Hotels and Resorts program; the fee pays for itself on two FHR stays a year thanks to the one-category room upgrade.", "decision", "personal", False,
     [("Amex Platinum", "organization"), ("Centurion Lounge", "place"), ("Fine Hotels and Resorts", "service")],
     [("Amex Platinum", "Centurion Lounge", "PRODUCES"), ("Amex Platinum", "Fine Hotels and Resorts", "PRODUCES")],
     "why do I keep paying the Amex Platinum fee and which two perks break even on it",
     "amex platinum centurion lounge fine hotels resorts fhr upgrade"),
    # --- 27 ---
    ("Citi Prestige got closed last cycle after Citi gutted the fourth-night-free benefit; the replacement role went to the Venture X which handled the hotel category coverage without drama.", "decision", "personal", False,
     [("Citi Prestige", "organization"), ("Venture X", "organization"), ("fourth-night-free", "concept")],
     [("Venture X", "Citi Prestige", "REPLACES"), ("Citi Prestige", "fourth-night-free", "APPLIES_TO")],
     "which card got closed after its signature hotel perk was cut and what replaced it",
     "citi prestige fourth night free closed venture x hotel"),
    # --- 28 ---
    ("Avios pooling across the British Airways household account lets partner miles stack; the family account gets fed from Chase transfers during the 25% Avios bonus windows that hit roughly twice a year.", "architecture", "personal", False,
     [("Avios", "concept"), ("British Airways", "organization"), ("Chase", "organization"), ("household account", "concept")],
     [("Chase", "Avios", "PRODUCES"), ("British Airways", "household account", "APPLIES_TO")],
     "how does Avios household pooling stack with Chase transfers during bonus windows",
     "avios british airways household chase transfer 25 percent bonus"),
    # --- 29 ---
    ("Aeroplan eUpgrade credits are the cheapest paid-to-business path on Air Canada long-hauls; the trick is that the eUpgrade window opens 48 hours before departure for elite tiers, not at booking.", "fact", "personal", False,
     [("Aeroplan", "organization"), ("eUpgrade", "concept"), ("Air Canada", "organization")],
     [("Aeroplan", "eUpgrade", "PRODUCES"), ("eUpgrade", "Air Canada", "APPLIES_TO")],
     "how does Aeroplan eUpgrade get used on Air Canada and what timing window actually matters",
     "aeroplan eupgrade air canada elite 48 hour window business"),
    # --- 30 ---
    ("Prefer booking Japanese domestic legs as separate ANA tickets rather than a through-ticket from the international carrier; stopover rules are looser and the cash price on those short segments is trivial.", "preference", "personal", False,
     [("ANA", "organization"), ("Japan", "place"), ("stopover", "concept")],
     [("ANA", "Japan", "APPLIES_TO"), ("ANA", "stopover", "APPLIES_TO")],
     "why do I split out Japanese domestic legs from the international booking",
     "ana japan domestic separate ticket stopover through fare cash"),
    # --- 31 ---
    ("The credit-card app rotation settled into a six-month churn cycle; Chase 5/24 is the gating constraint so the Amex and Capital One applications go into the first and fourth slots to avoid burning Chase budget.", "architecture", "personal", False,
     [("credit-card app rotation", "concept"), ("Chase 5/24", "concept"), ("Amex", "organization"), ("Capital One", "organization")],
     [("Amex", "Chase 5/24", "APPLIES_TO"), ("Capital One", "Chase 5/24", "APPLIES_TO")],
     "how did the six-month churn cadence end up ordered around the 5/24 rule",
     "credit card churn chase 5 24 amex capital one rotation"),
    # --- 32 ---
    ("Round-the-world bookings on Oneworld Explorer turned out wildly cheaper in miles than Star Alliance RTW for the same continents; the switch happened after pricing the same itinerary on both charts back-to-back.", "decision", "personal", False,
     [("Oneworld Explorer", "concept"), ("Star Alliance RTW", "concept")],
     [("Oneworld Explorer", "Star Alliance RTW", "REPLACES")],
     "which round the world product won the head to head and what pricing exercise forced the decision",
     "oneworld explorer rtw star alliance award mile compare chart"),
    # --- 33 ---
    ("Booked the first Maldives trip for next April through Aeroplan; the sweet spot is Air Canada LHR-MLE which prices at 70k Aeroplan one-way in business versus 120k on United.", "milestone", "personal", False,
     [("Maldives", "place"), ("Aeroplan", "organization"), ("April", "date"), ("LHR-MLE", "place")],
     [("Aeroplan", "LHR-MLE", "APPLIES_TO"), ("Aeroplan", "Maldives", "APPLIES_TO")],
     "which Maldives business-class award did I lock in and which sweet-spot route made it cheap",
     "maldives aeroplan april lhr mle business 70k sweet spot"),
    # --- 34 ---
    ("Portugal D7 requires 12 months of bank statements showing passive income above the minimum wage threshold; the application packet folder on Dropbox stays updated monthly so nothing goes stale in the 60-day submission window.", "reference", "personal", False,
     [("Portugal D7", "concept"), ("Dropbox", "service"), ("passive income", "concept")],
     [("Portugal D7", "passive income", "APPLIES_TO")],
     "what income record does the Portugal D7 packet require and how do I keep it submission ready",
     "portugal d7 passive income 12 month bank statement dropbox"),
    # --- 35 ---
    ("Decided that the only remaining viable path for AA miles is American Airlines web specials dropping off-peak; published award pricing has inflated to the point where the sub-30k tickets are effectively the whole program now.", "decision", "personal", False,
     [("American Airlines", "organization"), ("web specials", "concept"), ("AA miles", "concept")],
     [("American Airlines", "web specials", "PRODUCES"), ("American Airlines", "AA miles", "APPLIES_TO")],
     "why is American Airlines redemption now basically only worth it through web specials",
     "american airlines web special off peak aa mile inflation"),
    # --- 36 ---
    ("Long-layover protocol: if the connection is over seven hours, go landside and find food downtown rather than camping in a lounge; solved the airport-food fatigue that wrecked the first week of the Southeast Asia swing.", "decision", "personal", False,
     [("Long-layover", "concept"), ("Southeast Asia", "place"), ("airport-food fatigue", "emotion")],
     [("Long-layover", "airport-food fatigue", "CAUSES")],
     "what is the seven-hour layover rule and what problem did it fix on the Southeast Asia trip",
     "long layover seven hour landside southeast asia food fatigue"),
    # --- 37 ---
    ("Prefer United Polaris over American Flagship on the transatlantic because the cabin refresh pulled ahead on soft-product consistency; the lie-flat hardware is a wash but the bedding kit wins.", "preference", "personal", False,
     [("United Polaris", "concept"), ("American Flagship", "concept"), ("transatlantic", "concept")],
     [("United Polaris", "American Flagship", "PREFERS"), ("United Polaris", "transatlantic", "APPLIES_TO")],
     "which US carrier product do I prefer on the transatlantic and what tipped it over the competitor",
     "united polaris american flagship transatlantic bedding lie flat"),
    # --- 38 ---
    ("Mobile Passport Control app at JFK is now the fallback when the Global Entry kiosks are down; saved an hour on the last Lisbon return when the whole kiosk row rebooted at once.", "fact", "personal", False,
     [("Mobile Passport Control", "service"), ("JFK", "place"), ("Global Entry", "concept"), ("Lisbon", "place")],
     [("Mobile Passport Control", "Global Entry", "REPLACES"), ("Mobile Passport Control", "JFK", "APPLIES_TO")],
     "which app is my JFK fallback when Global Entry kiosks are offline and what incident proved its value",
     "mobile passport control jfk global entry kiosk lisbon return"),
    # --- 39 ---
    ("SkyTeam miles stay in Virgin Atlantic Flying Club rather than Delta SkyMiles; Virgin still publishes a partner chart, and the Delta dynamic pricing made the 95k ANA business redemption impossible to replicate.", "decision", "personal", False,
     [("SkyTeam", "organization"), ("Virgin Atlantic Flying Club", "organization"), ("Delta SkyMiles", "organization"), ("ANA", "organization")],
     [("Virgin Atlantic Flying Club", "Delta SkyMiles", "REPLACES"), ("Delta SkyMiles", "SkyTeam", "IS_A")],
     "why do my SkyTeam adjacent miles sit with Virgin Flying Club instead of Delta",
     "virgin atlantic flying club delta skymiles ana partner chart"),
    # --- 40 ---
    ("Finalised the long-flight emergency kit after two years of iteration: compression-sock set, melatonin, noise-cancelling headphones, and a decoy wallet; zero of these are optional after the laptop-bag theft in Barcelona.", "milestone", "personal", False,
     [("compression-sock", "concept"), ("melatonin", "food"), ("decoy wallet", "concept"), ("Barcelona", "place")],
     [("decoy wallet", "Barcelona", "APPLIES_TO")],
     "what four items live permanently in the long-flight kit and which incident pushed the decoy wallet in",
     "compression sock melatonin headphone decoy wallet barcelona theft"),
    # --- 41 ---
    ("Booking flow always locks lodging before flights on the high-season trips; cancellation policies on flexible hotel rates are softer than airline change fees, so this absorbs the risk when deal flights drop last minute.", "architecture", "personal", False,
     [("lodging", "concept"), ("cancellation policies", "concept"), ("deal flights", "concept")],
     [("lodging", "deal flights", "APPLIES_TO"), ("cancellation policies", "lodging", "APPLIES_TO")],
     "why do I lock lodging before flights for peak trips and which cancellation asymmetry drives it",
     "lodging first flight cancellation flexible rate deal high season"),
    # --- 42 ---
    ("Priority Pass restaurant credits at the home airport have quietly become better than the lounge food; eleven trips this year used the Timberline Grill credit instead of the crowded Delta Sky Club buffet.", "fact", "personal", False,
     [("Priority Pass", "service"), ("Timberline Grill", "organization"), ("Delta Sky Club", "place")],
     [("Priority Pass", "Timberline Grill", "APPLIES_TO")],
     "why do I take the Priority Pass restaurant credit over the lounge buffet at my home airport",
     "priority pass restaurant timberline grill delta sky club credit"),
    # --- 43. noise ---
    ("The neighbor's tabby figured out how to open the screen door and now hosts meetings on the porch every afternoon.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Always pre-check seat maps on ExpertFlyer the night the booking opens; the paid tier for seat alerts catches exit-row openings within the hour, which is the only way I still get 11A on the 787.", "preference", "personal", False,
     [("ExpertFlyer", "service"), ("exit-row", "concept"), ("787", "platform")],
     [("ExpertFlyer", "exit-row", "PRODUCES"), ("exit-row", "787", "APPLIES_TO")],
     "which seat tool grabs exit rows for me on the 787 and what tier actually matters",
     "expertflyer seat alert exit row 787 paid tier 11a"),
    # --- 45 ---
    ("Visa-free reciprocity chart lives as a bookmarked VisaHQ page; any trip planned beyond six months gets cross-checked there because the rules shift without much announcement, especially for the Gulf states.", "reference", "personal", False,
     [("VisaHQ", "service"), ("Visa-free", "concept"), ("Gulf states", "place")],
     [("VisaHQ", "Visa-free", "APPLIES_TO"), ("VisaHQ", "Gulf states", "APPLIES_TO")],
     "which resource do I use to double-check visa reciprocity and which region shifts rules quietly",
     "visahq visa free gulf state reciprocity bookmark six month"),
    # --- 46 ---
    ("The transfer-partner cheat sheet is stored as a single Notion table: columns are source program, partner, conversion ratio, and typical bonus cadence; it saves fifteen minutes every time I price an award.", "reference", "personal", False,
     [("transfer-partner", "concept"), ("Notion", "service"), ("conversion ratio", "concept")],
     [("Notion", "transfer-partner", "APPLIES_TO")],
     "how is the transfer partner cheat sheet structured and which tool hosts it",
     "transfer partner notion table conversion ratio bonus cadence"),
    # --- 47 ---
    ("The Thailand Elite visa got evaluated as the Portugal D7 backup last summer but got shelved; the fifteen-year commitment and the lack of path to permanent residency made the numbers not work for the medium term.", "decision", "personal", False,
     [("Thailand Elite", "concept"), ("Portugal D7", "concept"), ("permanent residency", "concept"), ("summer", "date")],
     [("Thailand Elite", "Portugal D7", "RELATED_TO"), ("Thailand Elite", "permanent residency", "CONTRADICTS")],
     "why did Thailand Elite get shelved as the Portugal D7 backup despite the long validity",
     "thailand elite portugal d7 permanent residency fifteen year"),
    # --- 48 ---
    ("The long-haul workflow got built around a three-window pre-trip checklist: 330 days out for award space, 21 days for seat maps and lounge plans, 48 hours for same-day upgrades and eSIM activation.", "architecture", "personal", False,
     [("pre-trip checklist", "concept"), ("award space", "concept"), ("same-day upgrades", "concept"), ("eSIM", "concept")],
     [("pre-trip checklist", "award space", "APPLIES_TO"), ("pre-trip checklist", "eSIM", "APPLIES_TO")],
     "what three pre-trip windows structure my long-haul workflow and what happens in each",
     "pre trip checklist 330 day 21 day 48 hour award space"),
    # --- 49 ---
    ("Hidden-city ticketing went off the rotation after United closed my MileagePlus account once; the Skiplagged savings were nice but losing a lifetime-miles balance twice in a row is not a trade worth repeating.", "problem", "personal", False,
     [("Skiplagged", "service"), ("United", "organization"), ("MileagePlus", "organization"), ("Hidden-city", "concept")],
     [("Skiplagged", "Hidden-city", "APPLIES_TO"), ("United", "Hidden-city", "CONTRADICTS")],
     "why did I stop using Skiplagged for hidden-city tickets after the United incident",
     "skiplagged united mileageplus hidden city account close risk"),
    # --- 50 ---
    ("Big six-month 2027 itinerary is locked: Lisbon base with weekend hops to Morocco and Madeira, a month in Japan across cherry-blossom season, then Oneworld Explorer RTW westbound through South Pacific and South America.", "milestone", "personal", False,
     [("Lisbon", "place"), ("Morocco", "place"), ("Madeira", "place"), ("Japan", "place"), ("Oneworld Explorer", "concept"), ("2027", "date")],
     [("Lisbon", "Morocco", "RELATED_TO"), ("Oneworld Explorer", "Japan", "APPLIES_TO")],
     "what does the six-month 2027 itinerary cover and which RTW product carries the back half",
     "lisbon morocco madeira japan oneworld explorer rtw 2027"),
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
