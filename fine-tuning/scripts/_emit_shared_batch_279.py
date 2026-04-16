"""One-off emitter for shared-base batch-279 — personal domain (beekeeping and apiculture: hive types, bee races, queen rearing, mite management, honey harvest, swarm control, community resources).

Writes 50 rows to data/v2/shared/batch_279.tmp.jsonl with ids shared-13901..13950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_279.tmp.jsonl"
ID_OFFSET = 13900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Standardised the home apiary on Langstroth 10-frame deeps after two seasons running British National alongside; the interchangeable frames across three yards cut my swap-out time in half.", "decision", "personal", False,
     [("Langstroth 10-frame", "tool"), ("British National", "tool"), ("apiary", "place")],
     [("Langstroth 10-frame", "British National", "REPLACES")],
     "which hive format did the apiary settle on and what practical win drove the switch from the other format",
     "langstroth 10 frame british national apiary standard interchange swap"),
    # --- 2 ---
    ("Kept the old Warre hive at the back fence as a foundationless observation colony; the top-bar-like combs let me trace wax-rendering losses without disturbing the production yard.", "architecture", "personal", False,
     [("Warre", "tool"), ("foundationless", "method"), ("wax-rendering", "method")],
     [("Warre", "foundationless", "USES")],
     "which hive sits at the back fence as an observation colony and what comb style does it run",
     "warre hive foundationless observation back fence wax render comb"),
    # --- 3 ---
    ("Switched the bee race from Italian to Carniolan after the third year of summer dearth wiped out the brood; the slower build-up and better frugality matched my forage window.", "decision", "personal", False,
     [("Italian", "concept"), ("Carniolan", "concept"), ("summer dearth", "event"), ("forage window", "concept")],
     [("Carniolan", "Italian", "REPLACES")],
     "which race of bee replaced the Italians in my yard and what forage constraint motivated it",
     "carniolan italian bee race summer dearth forage frugal build up"),
    # --- 4 ---
    ("Added two Buckfast nucs from a northern breeder to diversify the queen lines; the temper on these colonies is noticeably calmer than last year's feral cutout.", "milestone", "personal", False,
     [("Buckfast", "concept"), ("nucs", "tool"), ("feral cutout", "event")],
     [],
     "which queen line got added to diversify the apiary and how does its temper compare to last season's rescue",
     "buckfast nuc feral cutout diversify queen line temper calm"),
    # --- 5 ---
    ("Requeened the grumpiest production hive with a VSH-bred Saskatraz queen; the hygienic behaviour trait was the deciding factor after last autumn's mite test came back high.", "decision", "personal", False,
     [("VSH", "method"), ("Saskatraz", "concept"), ("hygienic behaviour", "method"), ("mite test", "method")],
     [("VSH", "hygienic behaviour", "USES")],
     "which queen genetics replaced the grumpy production hive and which trait tipped the decision",
     "vsh saskatraz requeen grumpy hygienic mite test autumn trait"),
    # --- 6 ---
    ("Russian queens handle our long wet springs without the early brood break that Italians reliably give me; the bonus is a measurably tighter Varroa population through June.", "fact", "personal", False,
     [("Russian", "concept"), ("Italians", "concept"), ("brood break", "method"), ("Varroa", "concept")],
     [],
     "which bee race handles the long wet spring better than Italians and what secondary mite benefit shows up",
     "russian italian brood break wet spring varroa tight population"),
    # --- 7 ---
    ("Adopted the Doolittle method for queen rearing this year; a dedicated cell builder colony gets grafted larvae from the best mother and pumps out ten cells on a reliable cadence.", "architecture", "personal", False,
     [("Doolittle method", "method"), ("cell builder", "tool"), ("grafted larvae", "method")],
     [("Doolittle method", "cell builder", "USES")],
     "which queen-rearing method did the apiary adopt this year and how is the cell builder set up",
     "doolittle method cell builder graft larva mother queen rear cadence"),
    # --- 8 ---
    ("Bought a Jenter cell-cup kit to stop damaging young larvae during grafting; the retention rate on cells went from roughly half to better than eighty percent within a cycle.", "milestone", "personal", False,
     [("Jenter", "tool"), ("grafting", "method"), ("cell-cup", "tool")],
     [("Jenter", "grafting", "IMPROVES_ON")],
     "which kit replaced hand-grafting for larva handling and how much did the cell retention improve",
     "jenter cell cup graft larva retention rate eighty percent kit"),
    # --- 9 ---
    ("Inspection cadence is every ten to fourteen days from April through July, then stretches out to monthly after the autumn feed is on; the long-winter gap starts when cluster forms below the handhold.", "reference", "personal", False,
     [("Inspection cadence", "method"), ("autumn feed", "method"), ("cluster", "concept")],
     [],
     "what inspection rhythm does the apiary run across the seasons and which signal opens the winter gap",
     "inspection cadence ten fourteen days april july monthly cluster handhold"),
    # --- 10. noise ---
    ("The neighbour's cat knocked a clay plant pot off the greenhouse bench and the crack pattern is weirdly decorative.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Lost two colonies to Nosema ceranae after a damp spring; fecal staining on the front of the hive and a crawling bee trail at the entrance were the first giveaways before the lab confirm.", "problem", "personal", False,
     [("Nosema ceranae", "concept"), ("fecal staining", "concept"), ("crawling bee", "concept")],
     [],
     "which disease took out two colonies in the damp spring and which two entrance signs flagged it first",
     "nosema ceranae fecal stain crawl bee damp spring colony loss entrance"),
    # --- 12 ---
    ("Picked oxalic acid vaporisation over dribble for the broodless winter treatment; a single three-gram dose through a Varrox vaporiser under the hive knocked mite counts to near zero before spring.", "decision", "personal", False,
     [("oxalic acid vaporisation", "method"), ("dribble", "method"), ("Varrox", "tool"), ("mite counts", "concept")],
     [("oxalic acid vaporisation", "dribble", "PREFERS")],
     "which winter oxalic acid delivery did I settle on and which applicator handles the broodless dose",
     "oxalic acid vaporisation dribble varrox broodless winter mite count"),
    # --- 13 ---
    ("Formic acid MAQS strips went on during the late-summer dearth because they penetrate capped brood and I needed a single treatment window before the ivy flow.", "decision", "personal", False,
     [("Formic acid", "concept"), ("MAQS", "tool"), ("capped brood", "concept"), ("ivy flow", "event")],
     [("MAQS", "capped brood", "APPLIES_TO")],
     "which mite treatment went on during the late-summer dearth and what brood reach forced the choice",
     "formic acid maqs capped brood late summer dearth ivy flow strip"),
    # --- 14 ---
    ("Thymol-based Apiguard trays are the fallback when daytime temps sit above fifteen and below thirty degrees; below that the gel doesn't evaporate and above it the bees beard hard and abscond risk climbs.", "reference", "personal", False,
     [("Thymol", "concept"), ("Apiguard", "tool"), ("beard", "concept"), ("abscond", "event")],
     [("Apiguard", "Thymol", "USES")],
     "which temperature window governs the Apiguard treatment and which behaviour flags out-of-range application",
     "thymol apiguard temperature fifteen thirty degree beard abscond tray"),
    # --- 15 ---
    ("Apivar amitraz strips are rotated out of the treatment plan every other year so I don't drive local resistance; MAQS or oxalic handles the off years in the rotation.", "preference", "personal", False,
     [("Apivar", "tool"), ("amitraz", "concept"), ("resistance", "concept"), ("rotation", "method")],
     [("Apivar", "amitraz", "USES")],
     "how does the treatment rotation avoid driving Apivar resistance and what carries the off years",
     "apivar amitraz resistance rotate year maqs oxalic off year local"),
    # --- 16 ---
    ("Drone brood culling is the biomechanical layer of the IPM stack; a green drone frame in the second box gets pulled and freezer-treated on a two-week cycle through May and June.", "architecture", "personal", False,
     [("Drone brood culling", "method"), ("IPM", "concept"), ("drone frame", "tool"), ("freezer", "tool")],
     [("Drone brood culling", "IPM", "USES")],
     "which biomechanical technique sits in the IPM stack and what two-week cadence drives the drone frame",
     "drone brood cull ipm frame freezer two week may june biomechanical"),
    # --- 17 ---
    ("Baseline mite load on every yard comes from an alcohol wash on three hundred bees every four weeks; the three-percent threshold triggers a treatment rather than waiting for symptoms.", "reference", "personal", False,
     [("alcohol wash", "method"), ("mite load", "concept"), ("threshold", "concept")],
     [],
     "which monitoring method sets the mite-load baseline and what numerical threshold triggers treatment",
     "alcohol wash three hundred bee four week threshold three percent mite"),
    # --- 18 ---
    ("The smoker I carry is a stainless Dadant 10-inch with a leather bellow; cedar chips and burlap give a cool clean smoke without the harsh sap of pine shavings.", "fact", "personal", False,
     [("smoker", "tool"), ("Dadant", "tool"), ("cedar chips", "concept"), ("burlap", "concept")],
     [("smoker", "cedar chips", "USES")],
     "which smoker model and fuel mix do I carry to the yard for cool clean smoke",
     "smoker dadant ten inch leather bellow cedar chip burlap cool clean"),
    # --- 19 ---
    ("Swapped the J-hook hive tool for the Italian-style lever after a hand-injury season; the longer handle pries frames without torquing my thumb on the propolis-glued ones.", "decision", "personal", False,
     [("hive tool", "tool"), ("J-hook", "tool"), ("Italian-style lever", "tool"), ("propolis", "concept")],
     [("Italian-style lever", "J-hook", "REPLACES")],
     "which hive tool replaced the J-hook after the hand-injury season and why does the new one help",
     "j hook italian lever hive tool hand injury propolis frame pry"),
    # --- 20 ---
    ("The queen excluder choice went to the plastic Nicot-style framed ones rather than the unframed metal; the frame stops the bee-space crush that was killing excess drones every inspection.", "decision", "personal", False,
     [("queen excluder", "tool"), ("Nicot", "tool"), ("bee-space", "concept")],
     [("Nicot", "queen excluder", "USES")],
     "which queen excluder style replaced the unframed metal one and what crush issue did it eliminate",
     "queen excluder nicot frame metal plastic bee space drone crush"),
    # --- 21 ---
    ("Porter escape boards remain my harvest clearing method over fume boards; the boards take overnight but my neighbours don't smell butyric anhydride through the fence line.", "preference", "personal", False,
     [("Porter", "tool"), ("escape boards", "tool"), ("fume boards", "tool"), ("butyric anhydride", "concept")],
     [("escape boards", "fume boards", "PREFERS")],
     "which harvest clearing tool do I favour over fume boards and what neighbour consideration drove the choice",
     "porter escape board fume butyric anhydride neighbour overnight clear"),
    # --- 22 ---
    ("Built a dedicated honey room with a four-frame radial extractor and a stainless uncapping tank; the move off the kitchen counter was overdue and the floor drain saves an hour per harvest.", "milestone", "personal", False,
     [("honey room", "place"), ("radial extractor", "tool"), ("uncapping tank", "tool"), ("floor drain", "infrastructure")],
     [],
     "which dedicated facility did I build for honey processing and which feature of it cut an hour from harvest",
     "honey room radial extractor uncap tank floor drain harvest kitchen"),
    # --- 23 ---
    ("Uncapping uses a heated knife for full frames and an uncapping fork for the patchy capping; the hybrid approach beat the cold knife on frames that had crystallised corners from last season's ivy.", "architecture", "personal", False,
     [("heated knife", "tool"), ("uncapping fork", "tool"), ("cold knife", "tool"), ("crystallised", "concept")],
     [("heated knife", "cold knife", "IMPROVES_ON")],
     "which uncapping combo handles full frames versus patchy capping and why did the cold knife get retired",
     "heat knife uncap fork cold scratch patchy ivy crystallise frame"),
    # --- 24 ---
    ("Honey moisture gets checked with a digital refractometer calibrated against the supplied oil drop; jars only go out the door below eighteen-point-five percent to stay within the national shelf-life rule.", "reference", "personal", False,
     [("refractometer", "tool"), ("Honey moisture", "concept"), ("oil drop", "concept"), ("shelf-life rule", "concept")],
     [],
     "which instrument governs the honey moisture gate and what percentage threshold do jars have to beat",
     "refractometer honey moisture oil drop eighteen five percent shelf life"),
    # --- 25 ---
    ("Wax rendering runs through a solar wax melter on sunny days and a stainless double-boiler with a wool filter for the winter cappings; the two-path system handled this year's mixed weather.", "architecture", "personal", False,
     [("solar wax melter", "tool"), ("double-boiler", "tool"), ("wool filter", "tool"), ("cappings", "concept")],
     [],
     "which two rendering paths does the wax shop run and how are summer versus winter cappings split",
     "solar wax melter double boiler wool filter capping summer winter"),
    # --- 26 ---
    ("Going foundationless on two hives this season gave me measurably whiter cut comb for table honey; the trade was a higher crossed-comb rate that I pruned out with bamboo skewers through April.", "fact", "personal", False,
     [("foundationless", "method"), ("cut comb", "tool"), ("crossed-comb", "concept"), ("bamboo skewers", "tool")],
     [],
     "what did the foundationless trial deliver for cut comb and which labour cost went up as a result",
     "foundationless cut comb cross bamboo skewer white table prune hive"),
    # --- 27 ---
    ("Kept drawn foundation on the production supers because the bees draw out wax roughly three times faster than starting from scratch; comb renewal happens on a rolling three-year rotation.", "decision", "personal", False,
     [("drawn foundation", "concept"), ("production supers", "tool"), ("comb renewal", "method")],
     [("drawn foundation", "production supers", "APPLIES_TO")],
     "why did production supers stay on drawn foundation and what rotation keeps the comb fresh",
     "drawn foundation production super three year rotation comb renewal"),
    # --- 28 ---
    ("Made six five-frame nucs in late May to carry as overwinter insurance; the nuc boxes are pine with a migratory cover and a screened bottom for summer travel between yards.", "milestone", "personal", False,
     [("nuc", "tool"), ("migratory cover", "tool"), ("screened bottom", "tool"), ("insurance", "concept")],
     [],
     "how many nucs did I make in late May for overwinter insurance and what hardware do the nuc boxes use",
     "nuc five frame overwinter insurance pine migratory cover screen bottom"),
    # --- 29 ---
    ("Early-season splits go walk-away with a capped swarm cell rather than a purchased queen; the timing lands emergence right in the window when drones are mature for open mating in the yard.", "architecture", "personal", False,
     [("splits", "method"), ("walk-away", "method"), ("swarm cell", "concept"), ("open mating", "method")],
     [],
     "which split method relies on a capped swarm cell and how does the timing align with drone maturity",
     "split walk away swarm cell queen purchase open mating drone window"),
    # --- 30 ---
    ("Swarm control runs on the Demaree method in the populous yard; separating the queen from the brood with a super of frames below the excluder breaks the swarm cue without losing the bees.", "architecture", "personal", False,
     [("Demaree", "method"), ("queen", "concept"), ("excluder", "tool"), ("swarm cue", "concept")],
     [("Demaree", "swarm cue", "APPLIES_TO")],
     "which swarm control method does the populous yard run and what hive rearrangement breaks the swarm cue",
     "demaree swarm control queen excluder brood super cue populous yard"),
    # --- 31 ---
    ("The Pagden method stays on the shelf for the back-fence hive since I can't easily move it off its stand; the brood-box relocation trick assumes a wheelbarrow-level path I don't have there.", "decision", "personal", False,
     [("Pagden", "method"), ("back-fence hive", "place"), ("brood-box", "tool")],
     [("Pagden", "back-fence hive", "APPLIES_TO")],
     "why does the Pagden method not get used on the back-fence hive and which access constraint rules it out",
     "pagden swarm back fence hive brood box move wheelbarrow access"),
    # --- 32 ---
    ("Spring feed is 1:1 sugar syrup in a top feeder to spark brood rearing; autumn rolls to 2:1 sugar syrup to stock the winter pantry with less water for the bees to drive off.", "reference", "personal", False,
     [("1:1 sugar syrup", "food"), ("2:1 sugar syrup", "food"), ("top feeder", "tool"), ("brood rearing", "method")],
     [],
     "which sugar-syrup ratios map to which seasons and what's the rationale for the thicker autumn mix",
     "one to one two to one sugar syrup spring autumn top feeder brood"),
    # --- 33 ---
    ("Fondant patties replace syrup once night temperatures drop below ten degrees; syrup invites robbing and the bees won't take cold feed, so a solid cake over the cluster handles both.", "decision", "personal", False,
     [("Fondant", "food"), ("syrup", "food"), ("robbing", "event"), ("cluster", "concept")],
     [("Fondant", "syrup", "REPLACES")],
     "which feed swaps in below ten degrees at night and what two problems does the swap solve at once",
     "fondant syrup cold ten degree robbing cluster patty winter feed"),
    # --- 34 ---
    ("Pollen patties go on only when a trap-sample shows low incoming pollen; stuffing cake in front of a healthy forage flow tends to breed small hive beetle in the upper box.", "problem", "personal", False,
     [("Pollen patties", "food"), ("trap-sample", "method"), ("small hive beetle", "concept")],
     [("Pollen patties", "small hive beetle", "APPLIES_TO")],
     "when does the pollen patty go on and which pest risk keeps it off during strong flows",
     "pollen patty trap sample small hive beetle forage flow upper box"),
    # --- 35 ---
    ("The Beekeepers Naturally forum is where I check local flow calls and pest waves before committing to a treatment window; the regional reports save me a week of guessing every season.", "preference", "personal", False,
     [("Beekeepers Naturally", "organization"), ("flow calls", "concept"), ("pest waves", "concept"), ("treatment window", "concept")],
     [],
     "which community do I check first for local flow and pest reports before setting a treatment window",
     "beekeepers naturally forum flow call pest wave treatment window region"),
    # --- 36 ---
    ("Michael Palmer's sustainable apiary talks are the reason the nuc-as-insurance policy exists in my yard; the winter nuc configuration is his layout, down to the divider board.", "fact", "personal", False,
     [("Michael Palmer", "person"), ("sustainable apiary", "concept"), ("divider board", "tool"), ("winter nuc", "tool")],
     [("Michael Palmer", "winter nuc", "BUILDS_ON")],
     "whose practice drives the nuc-as-insurance policy in the yard and which piece of hardware traces to him",
     "michael palmer sustainable apiary nuc insurance divider board winter"),
    # --- 37 ---
    ("Randy Oliver's ScientificBeekeeping articles anchor the mite-threshold numbers I use; the alcohol-wash triggers and the oxalic-glycerin towel recipe both come from there rather than the club newsletter.", "reference", "personal", False,
     [("Randy Oliver", "person"), ("ScientificBeekeeping", "organization"), ("oxalic-glycerin", "concept"), ("club newsletter", "publication")],
     [("Randy Oliver", "ScientificBeekeeping", "AUTHORED_BY")],
     "whose writing anchors the mite-threshold numbers and the glycerin towel recipe in my yard",
     "randy oliver scientific beekeeping mite threshold oxalic glycerin towel"),
    # --- 38 ---
    ("Honey Bee Health Coalition's Varroa guide sits laminated in the bee shed; the dose tables for each miticide and the label rotation chart replaced three bookmarks that never stayed current.", "preference", "personal", False,
     [("Honey Bee Health Coalition", "organization"), ("Varroa guide", "publication"), ("bee shed", "place"), ("dose tables", "publication")],
     [("Honey Bee Health Coalition", "Varroa guide", "PRODUCES")],
     "which laminated guide sits in the bee shed and what content replaced a pile of outdated bookmarks",
     "honey bee health coalition varroa guide laminate shed dose rotation"),
    # --- 39 ---
    ("Built a Flow Hive kit over one winter as a demo colony for the local school visits; the plastic frames stay on one deep and the production money hives never see them.", "architecture", "personal", False,
     [("Flow Hive", "tool"), ("demo colony", "concept"), ("school visits", "event"), ("production money hives", "tool")],
     [("Flow Hive", "demo colony", "APPLIES_TO")],
     "which hive style fills the demo role for school visits and where does it sit relative to production hives",
     "flow hive demo school visit plastic frame deep production money"),
    # --- 40 ---
    ("An AZ hive from a Slovenian builder went in the shed-integrated side of the apiary; the back-opening design lets inspections happen standing up and the kids can watch through the back glass.", "milestone", "personal", False,
     [("AZ hive", "tool"), ("Slovenian", "place"), ("shed-integrated", "place"), ("back glass", "tool")],
     [],
     "which Slovenian hive style went into the shed-integrated apiary and what does the back glass enable",
     "az hive slovenian shed integrate back glass open stand watch"),
    # --- 41 ---
    ("Horizontal hives in the community garden handle local educational workshops; the single-box-no-lift layout has been a win for the older volunteers who couldn't wrangle full Langstroth supers.", "fact", "personal", False,
     [("Horizontal hive", "tool"), ("community garden", "place"), ("educational workshops", "event"), ("volunteers", "concept")],
     [],
     "which hive format serves the community garden workshops and what accessibility win comes with it",
     "horizontal hive community garden workshop volunteer no lift super"),
    # --- 42 ---
    ("Top-bar hive experiment in year two produced a third of the production yard's honey per colony but cut the vertical-lifting load to zero on inspection days.", "fact", "personal", False,
     [("Top-bar hive", "tool"), ("production yard", "place"), ("vertical-lifting", "concept")],
     [],
     "how did the top-bar hive honey yield compare to the production yard and what ergonomic trade-off came with it",
     "top bar hive production yard third honey yield vertical lift ergonomic"),
    # --- 43. noise ---
    ("Left a library book about coastal lighthouses in the car overnight and the condensation warped the jacket into a soft wave.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Tried a Langstroth 8-frame box for a back-friendly super during the main flow; the narrower box cut lifted weight by about twenty percent compared to the Langstroth 10-frame mediums.", "decision", "personal", False,
     [("Langstroth 8-frame", "tool"), ("Langstroth 10-frame", "tool"), ("main flow", "event")],
     [("Langstroth 8-frame", "Langstroth 10-frame", "IMPROVES_ON")],
     "which narrower box replaced the medium super during the main flow and how much lift weight did it save",
     "langstroth 8 frame back friendly super flow twenty percent weight lift"),
    # --- 45 ---
    ("A feral cutout from the church belfry went into an Africanized-screened queen cage for transport; I requeened within forty-eight hours and kept the brood comb on the principle that temper follows the mother.", "problem", "personal", False,
     [("feral cutout", "event"), ("Africanized", "concept"), ("queen cage", "tool"), ("church belfry", "place")],
     [],
     "how was the church-belfry cutout handled for Africanized risk and how fast did the requeen happen",
     "feral cutout church belfry africanized queen cage requeen forty eight"),
    # --- 46 ---
    ("The uncapping fork stays in the freezer between sessions so the wax snaps rather than smears; the tip-life on the tines tripled since adopting the cold-fork habit two seasons ago.", "fact", "personal", False,
     [("uncapping fork", "tool"), ("freezer", "tool"), ("tines", "tool")],
     [("uncapping fork", "freezer", "LOCATED_IN")],
     "what storage habit triples the uncapping fork's tine life and why does the cold help",
     "uncap fork freezer cold tine life snap smear wax store habit"),
    # --- 47 ---
    ("The bee brush is a soft-bristle horsehair rather than the yellow plastic; the plastic bristles were snagging on the foundationless comb and rolling bees into the frame side.", "decision", "personal", False,
     [("bee brush", "tool"), ("horsehair", "concept"), ("yellow plastic", "concept"), ("foundationless comb", "tool")],
     [("horsehair", "yellow plastic", "REPLACES")],
     "which bee brush bristle replaced the yellow plastic and what foundationless issue forced the change",
     "bee brush horsehair yellow plastic foundationless comb bristle roll"),
    # --- 48 ---
    ("Logged the first hundred-pound harvest from a single colony in season eight; a Carniolan mother line on drawn foundation with the Demaree split timing was the combination that did it.", "milestone", "personal", False,
     [("hundred-pound harvest", "concept"), ("Carniolan", "concept"), ("Demaree", "method"), ("drawn foundation", "concept")],
     [("Carniolan", "hundred-pound harvest", "PRODUCES")],
     "which combination delivered the first hundred-pound single-colony harvest in season eight",
     "hundred pound harvest carniolan demaree drawn foundation season eight"),
    # --- 49 ---
    ("Winter loss ran at twelve percent across the yard this year against the regional average of thirty; the IPM stack with alcohol-wash triggers and the oxalic-glycerin towels is the honest reason for the gap.", "milestone", "personal", False,
     [("Winter loss", "concept"), ("IPM", "concept"), ("alcohol-wash", "method"), ("oxalic-glycerin towels", "tool")],
     [("IPM", "Winter loss", "IMPROVES_ON")],
     "what was the winter loss rate this year against the regional average and which practice stack closed the gap",
     "winter loss twelve percent thirty region ipm alcohol wash oxalic towel"),
    # --- 50 ---
    ("Keeping two colonies deliberately untreated in a screened observation yard to benchmark mite-tolerant genetics from the Saskatraz line; year one alcohol-wash numbers ran half the neighbouring treated hives.", "architecture", "personal", False,
     [("untreated", "method"), ("observation yard", "place"), ("Saskatraz", "concept"), ("alcohol-wash", "method")],
     [("Saskatraz", "untreated", "APPLIES_TO")],
     "why are two Saskatraz colonies kept deliberately untreated and how did their year-one mite wash compare",
     "untreated observation saskatraz mite tolerant alcohol wash half neighbour"),
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
