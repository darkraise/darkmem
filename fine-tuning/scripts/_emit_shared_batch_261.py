"""One-off emitter for shared-base batch-261 — personal domain (homebrewing beer: styles, BJCP, grain, hops, yeast, equipment, water chemistry, fermentation control, dry hopping, LODO, MLF).

Writes 50 rows to data/v2/shared/batch_261.tmp.jsonl with ids shared-13001..13050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_261.tmp.jsonl"
ID_OFFSET = 13000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Swapped the old Anvil Foundry out for a BrewZilla 3.1.1 after the recirculation pump on the Anvil seized mid-mash; the step mash profiles now actually hold setpoint during a Helles decoction.", "decision", "personal", False,
     [("Anvil Foundry", "tool"), ("BrewZilla", "tool"), ("Helles", "concept")],
     [("BrewZilla", "Anvil Foundry", "REPLACES")],
     "which all-in-one electric system replaced the Anvil after its pump failed on a decoction brew",
     "brewzilla anvil foundry recirculation pump helles step mash decoction"),
    # --- 2 architecture ---
    ("Water chemistry builds go through Bru'n Water for every brew day; the spreadsheet pulls the local Seattle municipal report, then the Gypsum and Calcium Chloride additions land on a sticker that rides with the mash tun.", "architecture", "personal", False,
     [("Bru'n Water", "tool"), ("Seattle", "place"), ("Gypsum", "concept"), ("Calcium Chloride", "concept")],
     [("Bru'n Water", "Seattle", "APPLIES_TO")],
     "which spreadsheet drives salt additions each brew day and how do the numbers reach the mash tun",
     "brun water seattle gypsum calcium chloride mash tun sticker municipal"),
    # --- 3 milestone ---
    ("Took home a bronze at the March 2026 Cascade Brewers Cup with a West Coast IPA built on Simcoe, Mosaic, and Citra; the judges flagged the Mosaic dry-hop window as the standout note in the scoresheet.", "milestone", "personal", False,
     [("March 2026", "date"), ("Cascade Brewers Cup", "event"), ("West Coast IPA", "concept"), ("Simcoe", "concept"), ("Mosaic", "concept"), ("Citra", "concept")],
     [("West Coast IPA", "Cascade Brewers Cup", "APPLIES_TO")],
     "which competition medal landed in early 2026 and which three hops carried the IPA to the podium",
     "cascade brewers cup west coast ipa simcoe mosaic citra dry hop bronze"),
    # --- 4 fact ---
    ("The BJCP 2021 guidelines list the Gose target pH at 3.4 and tie the minerality character to a Noble-hop backbone; my house recipe lands right at that mark with a Saaz bittering charge.", "fact", "personal", False,
     [("BJCP", "publication"), ("Gose", "concept"), ("Saaz", "concept")],
     [("Gose", "BJCP", "PUBLISHED_IN")],
     "which style guide pins the Gose pH target at 3.4 and which noble hop does the house recipe use",
     "bjcp 2021 gose ph 3.4 saaz noble hop minerality backbone"),
    # --- 5 reference ---
    ("Imperial Pub is the house English-ale yeast of record for brown porters and bitters; the bank tube lives in the kegerator on the middle shelf beside the Wyeast 1056 backup for American strains.", "reference", "personal", False,
     [("Imperial Pub", "tool"), ("Wyeast 1056", "tool"), ("kegerator", "tool")],
     [],
     "which two yeast cultures live in the kegerator bank and which one carries English-ale duty",
     "imperial pub wyeast 1056 kegerator bank english ale brown porter"),
    # --- 6 preference ---
    ("Prefer Maris Otter over Golden Promise for British bitters; the biscuit note pulls through the finish in a way Golden Promise never quite delivers on the electric system.", "preference", "personal", False,
     [("Maris Otter", "food"), ("Golden Promise", "food")],
     [("Maris Otter", "Golden Promise", "PREFERS")],
     "which British base malt wins the house pick for bitters and what sensory note decides it",
     "maris otter golden promise british bitter biscuit finish electric"),
    # --- 7 problem ---
    ("The Voss kveik fermentation on the last Helles stalled at 1.024 because the Inkbird was probing the ambient cabinet rather than the fermentor thermowell; relocating the probe cleared it overnight.", "problem", "personal", False,
     [("Voss kveik", "tool"), ("Helles", "concept"), ("Inkbird", "tool")],
     [("Inkbird", "Voss kveik", "CONFIGURES")],
     "which temperature controller misread caused the Helles Kveik stall and how did relocating the probe fix it",
     "voss kveik helles inkbird probe fermentor thermowell stall 1.024"),
    # --- 8 decision ---
    ("Moved the dry-hop regime for New England IPA from a single post-fermentation charge to a split biotransformation dose at 1.030 plus a cold-side charge at flameout of fermentation; the haze stability improved and the grassy note faded.", "decision", "personal", False,
     [("New England IPA", "concept"), ("biotransformation", "method"), ("dry-hop", "activity")],
     [("biotransformation", "dry-hop", "APPLIES_TO")],
     "which dry-hop split replaced the single post-fermentation charge on the NEIPA program and what two gains did it unlock",
     "neipa dry hop biotransformation split gravity post fermentation haze"),
    # --- 9 architecture ---
    ("Fermentation temperature control runs on a Tilt Pi feeding an Inkbird ITC-308 that clamps the chamber to the programmed profile; the Tilt hydrometer itself reports gravity so the diacetyl rest triggers automatically at 75 percent attenuation.", "architecture", "personal", False,
     [("Tilt Pi", "tool"), ("Inkbird", "tool"), ("Tilt hydrometer", "tool"), ("diacetyl rest", "method")],
     [("Tilt Pi", "Inkbird", "COMMUNICATES_WITH"), ("Tilt hydrometer", "diacetyl rest", "CAUSES")],
     "how does the chamber escalate to a diacetyl rest automatically on the current rig",
     "tilt pi inkbird itc-308 hydrometer diacetyl rest 75 attenuation chamber"),
    # --- 10 noise ---
    ("The neighbour's cat keeps sitting on the fermentation chamber lid like it owns the garage and the lid has a permanent fur halo now.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Switched primary fermentation vessel from a glass Brew Bucket to an SS Brewtech Unitank 7; pressure-capable fermentation finally closed the oxygen gap on pale lagers and cut the transfer losses in half.", "decision", "personal", False,
     [("Brew Bucket", "tool"), ("SS Brewtech", "tool"), ("Unitank", "tool")],
     [("Unitank", "Brew Bucket", "REPLACES")],
     "which fermentor upgrade replaced the glass Brew Bucket and what two issues did the pressure vessel resolve",
     "ss brewtech unitank brew bucket pressure fermentation lager transfer"),
    # --- 12 reference ---
    ("The Schwarzbier grist bill of record is 70 percent Pilsner malt, 20 percent Munich, 8 percent chocolate malt, and 2 percent acidulated malt; it sits in the recipe book tagged as the house dark lager.", "reference", "personal", False,
     [("Schwarzbier", "concept"), ("Pilsner", "food"), ("Munich", "food"), ("chocolate malt", "food"), ("acidulated malt", "food")],
     [("Schwarzbier", "Pilsner", "HAS_PART"), ("Schwarzbier", "Munich", "HAS_PART"), ("Schwarzbier", "chocolate malt", "HAS_PART")],
     "which four malts compose the house Schwarzbier grist and in which proportions",
     "schwarzbier pilsner munich chocolate acidulated malt dark lager grist"),
    # --- 13 fact ---
    ("Galaxy dry-hopped at 6 grams per litre drove the passionfruit character in the last West Coast Pilsner collaboration with Finn; the same charge on a Helles would wreck the style into citrus territory.", "fact", "personal", False,
     [("Galaxy", "concept"), ("West Coast Pilsner", "concept"), ("Finn", "person"), ("Helles", "concept")],
     [("Galaxy", "West Coast Pilsner", "APPLIES_TO")],
     "which hop and dose pushed the passionfruit note in the West Coast Pilsner collab and who co-brewed it",
     "galaxy west coast pilsner finn passionfruit 6 gram helles collab"),
    # --- 14 architecture ---
    ("LODO pale-lager pipeline runs a CO2 purge on the Fermzilla, a sealed transfer through the Blichmann QuickCarb, and a dissolved-oxygen reading below 30 ppb at package on the Anton Paar meter rental.", "architecture", "personal", False,
     [("LODO", "method"), ("Fermzilla", "tool"), ("Blichmann", "tool"), ("Anton Paar", "tool")],
     [("LODO", "Fermzilla", "APPLIES_TO"), ("LODO", "Blichmann", "USES")],
     "which three-step pipeline keeps packaged dissolved oxygen under 30 ppb for pale lagers",
     "lodo fermzilla blichmann quickcarb anton paar dissolved oxygen 30 ppb"),
    # --- 15 decision ---
    ("Locked the house Saison yeast to Omega Hothead as the DIPA crossover strain; tried WLP001 and it never produced the stonefruit ester that the Omega culture gives on a peppered 32 C fermentation.", "decision", "personal", False,
     [("Omega Hothead", "tool"), ("Saison", "concept"), ("WLP001", "tool")],
     [("Omega Hothead", "WLP001", "PREFERS")],
     "which Omega culture beat WLP001 for the Saison program and at what fermentation peak",
     "omega hothead wlp001 saison dipa stonefruit ester 32 celsius"),
    # --- 16 milestone ---
    ("Hit the 100th brew-day log entry on the Spike Solo in April 2026; the recipe book crossed every BJCP category from Berliner Weisse through Imperial Stout along the way.", "milestone", "personal", False,
     [("Spike Solo", "tool"), ("April 2026", "date"), ("BJCP", "publication"), ("Berliner Weisse", "concept"), ("Imperial Stout", "concept")],
     [("Spike Solo", "BJCP", "APPLIES_TO")],
     "which brew-day counter cleared 100 in spring 2026 and which style span the log now covers",
     "spike solo 100 brew day april bjcp berliner weisse imperial stout"),
    # --- 17 preference ---
    ("Prefer Lallemand Verdant IPA over Escarpment BRY-97 for hop-forward American ales; Verdant throws a softer mouthfeel on the New England IPA recipe while BRY-97 still owns the crisp West Coast program.", "preference", "personal", False,
     [("Lallemand Verdant", "tool"), ("Escarpment BRY-97", "tool"), ("New England IPA", "concept")],
     [("Lallemand Verdant", "Escarpment BRY-97", "PREFERS")],
     "which dry yeast wins the NEIPA role against BRY-97 and which program still keeps BRY-97",
     "lallemand verdant bry-97 escarpment neipa oat mouthfeel west coast"),
    # --- 18 architecture ---
    ("The dissolved oxygen meter is an in-line Orbisphere rental that pulls a sample from a sanitary tee between the Unitank and the keg post; package DO logs land in the Brewers Friend recipe note with a timestamp.", "architecture", "personal", False,
     [("Orbisphere", "tool"), ("Unitank", "tool"), ("Brewers Friend", "tool")],
     [("Orbisphere", "Brewers Friend", "PRODUCES")],
     "how do packaged dissolved oxygen readings land inside the recipe notebook automatically",
     "orbisphere unitank sanitary tee brewers friend log package do timestamp"),
    # --- 19 reference ---
    ("House Helles recipe: 100 percent floor-malted Pilsner, 18 IBU from Hallertau Mittelfrüh at 60 minutes, WLP833 at 10 C, and a three-day diacetyl rest at 16 C before a six-week lagering hold.", "reference", "personal", False,
     [("Helles", "concept"), ("Pilsner", "food"), ("Hallertau Mittelfrüh", "concept"), ("diacetyl rest", "method")],
     [("Helles", "Pilsner", "HAS_PART"), ("Helles", "Hallertau Mittelfrüh", "HAS_PART")],
     "which single base malt and which noble hop define the house Helles specification",
     "helles pilsner floor malted hallertau mittelfruh wlp833 diacetyl rest"),
    # --- 20 decision ---
    ("Picked the Grainfather G70 over a Speidel Braumeister for the 50-litre upgrade; the counterflow chiller that ships with the G70 finally beat the in-mash coil on knockout time for pale lagers.", "decision", "personal", False,
     [("Grainfather", "tool"), ("Speidel", "tool")],
     [("Grainfather", "Speidel", "PREFERS")],
     "which 50-litre all-in-one beat the Braumeister on the knockout time shootout for pale lagers",
     "grainfather g70 speidel braumeister counterflow chiller knockout lager"),
    # --- 21 problem ---
    ("The last Flanders Red went stuck at 1.014 because the garage dropped below 15 C in October and the Brettanomyces slowed to a crawl; moved the carboy into the heated office for the rest of the aging window.", "problem", "personal", False,
     [("Flanders Red", "concept"), ("Brettanomyces", "concept")],
     [],
     "what temperature drop stalled the Flanders Red aging window and how did the move fix it",
     "flanders red 1.014 brett october garage office heated aging stall"),
    # --- 22 decision ---
    ("Committed the Mixed-Fermentation program to a dedicated coolship room with an airlock tree on a solera of three Fermzilla 55s; fresh wort tops off the leading vessel each year and the trailing one gets pulled for blending.", "decision", "personal", False,
     [("Mixed-Fermentation", "method"), ("coolship", "tool"), ("Fermzilla", "tool")],
     [("Mixed-Fermentation", "Fermzilla", "DEPLOYED_ON")],
     "how is the solera structured across the three Fermzilla vessels and which one feeds blending",
     "mixed fermentation coolship fermzilla 55 solera blending top wort"),
    # --- 23 fact ---
    ("Strata delivered a dank-passionfruit punch on the pale ale at 4 grams per litre dry-hop; Sabro overlapped on the coconut side but lost the fruit focus when paired with Mosaic.", "fact", "personal", False,
     [("Strata", "concept"), ("Sabro", "concept"), ("Mosaic", "concept")],
     [],
     "which hop carried the dank-passionfruit lead on the pale ale and which one muddied the pairing",
     "strata sabro mosaic pale ale dry hop dank passionfruit coconut"),
    # --- 24 decision ---
    ("Retired the Tettnang bittering charge on the Dunkel in favour of East Kent Goldings; the base malt-forward profile survived better against an English hop than a German one in the side-by-side pour.", "decision", "personal", False,
     [("Tettnang", "concept"), ("East Kent Goldings", "concept"), ("Dunkel", "concept")],
     [("East Kent Goldings", "Tettnang", "REPLACES")],
     "which English hop replaced Tettnang on the Dunkel bittering role and why",
     "tettnang east kent goldings dunkel bittering malt forward side by side"),
    # --- 25 reference ---
    ("Doppelbock house recipe calls for a double decoction mash on Vienna and Munich, Hallertau Mittelfrüh at 22 IBU, and a six-month lagering window at 2 C before kegging.", "reference", "personal", False,
     [("Doppelbock", "concept"), ("Vienna", "food"), ("Munich", "food"), ("Hallertau Mittelfrüh", "concept")],
     [("Doppelbock", "Vienna", "HAS_PART"), ("Doppelbock", "Munich", "HAS_PART")],
     "which decoction schedule and which two malts anchor the house Doppelbock",
     "doppelbock double decoction vienna munich hallertau mittelfruh lager"),
    # --- 26 milestone ---
    ("Closed out the Baltic Porter brewday on 2026-02-14 with the first successful lager fermentation on the Unitank at spund pressure; packaged DO came in at 18 ppb on the Anton Paar readout.", "milestone", "personal", False,
     [("Baltic Porter", "concept"), ("2026-02-14", "date"), ("Unitank", "tool"), ("Anton Paar", "tool")],
     [("Baltic Porter", "Unitank", "APPLIES_TO")],
     "which brewday landed the first spunded lager on the Unitank and what dissolved oxygen number did it hit",
     "baltic porter 2026 02 14 unitank spund pressure anton paar 18 ppb"),
    # --- 27 architecture ---
    ("The Berliner Weisse pipeline kettle-sours with Goodbelly on a 36-hour hold at 40 C before boil; pH target is 3.3 before wort goes back to the Pilsner yeast on WLP001 for the clean-fermentation finish.", "architecture", "personal", False,
     [("Berliner Weisse", "concept"), ("Goodbelly", "tool"), ("WLP001", "tool")],
     [("Berliner Weisse", "Goodbelly", "USES"), ("Berliner Weisse", "WLP001", "USES")],
     "which kettle-sour bug and which clean yeast split the Berliner Weisse fermentation in two stages",
     "berliner weisse goodbelly kettle sour 36 hour 40 celsius wlp001 pilsner"),
    # --- 28 preference ---
    ("Prefer the iSpindel over the Tilt hydrometer for pressure fermentations on the Unitank; the iSpindel's plastic body handles the 15 psi spunding better than the Tilt's magnet seat.", "preference", "personal", False,
     [("iSpindel", "tool"), ("Tilt hydrometer", "tool"), ("Unitank", "tool")],
     [("iSpindel", "Tilt hydrometer", "PREFERS")],
     "which gravity-logger wins under spunding pressure and why does the Tilt lose the role",
     "ispindel tilt hydrometer unitank pressure spunding magnet plastic"),
    # --- 29 decision ---
    ("Committed to flaked oats at 12 percent on every New England IPA going forward after a wheat malt ramp up to 20 percent caused stuck sparges three brewdays running on the Grainfather.", "decision", "personal", False,
     [("flaked oats", "food"), ("wheat malt", "food"), ("New England IPA", "concept"), ("Grainfather", "tool")],
     [("flaked oats", "wheat malt", "REPLACES")],
     "which adjunct ratio change fixed the stuck sparges on the Grainfather NEIPA program",
     "flaked oats 12 percent wheat malt neipa stuck sparge grainfather"),
    # --- 30 fact ---
    ("Nelson Sauvin hit the white-wine grape note on the second pour of the Saison; the Omega Hothead culture amplified it at 30 C without breaking into solvent territory.", "fact", "personal", False,
     [("Nelson Sauvin", "concept"), ("Saison", "concept"), ("Omega Hothead", "tool")],
     [("Nelson Sauvin", "Saison", "APPLIES_TO")],
     "which hop produced the white-wine note on the Saison and which yeast held the ferment without solvent",
     "nelson sauvin saison omega hothead 30 celsius white wine grape"),
    # --- 31 architecture ---
    ("MLF on the Flanders Red runs on a co-pitch of Pediococcus and Lactobacillus in the secondary oak barrel; the barrel sits in the basement cellar at 14 C for twelve months before a Brettanomyces refermentation in bottle.", "architecture", "personal", False,
     [("MLF", "method"), ("Flanders Red", "concept"), ("Pediococcus", "concept"), ("Lactobacillus", "concept"), ("Brettanomyces", "concept")],
     [("MLF", "Flanders Red", "APPLIES_TO")],
     "which two bugs drive the secondary MLF on the Flanders Red and what completes the bottle stage",
     "mlf flanders red pediococcus lactobacillus brett oak barrel cellar"),
    # --- 32 reference ---
    ("The Lambic house recipe spec: 60 percent raw wheat malt, 40 percent Pilsner base, a Turbid mash to 62 C, aged hops at 3 IBU, and a coolship inoculation on a cold November night before barrel transfer.", "reference", "personal", False,
     [("Lambic", "concept"), ("wheat malt", "food"), ("Pilsner", "food"), ("coolship", "tool")],
     [("Lambic", "wheat malt", "HAS_PART"), ("Lambic", "Pilsner", "HAS_PART")],
     "which mash style and which grain ratio define the house Lambic and what inoculates the wort",
     "lambic raw wheat pilsner turbid mash aged hop coolship november"),
    # --- 33 problem ---
    ("The West Coast IPA carbonation stripped hop flavour within two weeks; the regulator on the Blichmann spunding valve was drifting high and pushing 3.2 volumes instead of the 2.4 target on the datasheet.", "problem", "personal", False,
     [("West Coast IPA", "concept"), ("Blichmann", "tool")],
     [("Blichmann", "West Coast IPA", "CAUSES")],
     "which regulator drift stripped the IPA hop flavour and how much over the target did it push",
     "west coast ipa blichmann spunding regulator 3.2 volume 2.4 carbonation"),
    # --- 34 milestone ---
    ("Bottled the first homegrown Voss kveik ale on 2026-01-20 after three generations of repitching; the attenuation held at 86 percent and the orange character stayed clean.", "milestone", "personal", False,
     [("Voss kveik", "tool"), ("2026-01-20", "date")],
     [],
     "which date marked the third-generation Voss repitch bottling and what attenuation did it hit",
     "voss kveik 2026 01 20 repitch third generation 86 percent orange"),
    # --- 35 decision ---
    ("Adopted EZ Water 3.0 as the backup calculator alongside Bru'n Water for quick brewdays; the simpler sliders keep the cognitive load low when the Brewers Friend recipe already has the grist dialed in.", "decision", "personal", False,
     [("EZ Water", "tool"), ("Bru'n Water", "tool"), ("Brewers Friend", "tool")],
     [("EZ Water", "Bru'n Water", "APPLIES_TO")],
     "which backup water calculator sits beside Bru'n Water for quick brewdays and why was it chosen",
     "ez water 3.0 brun water brewers friend quick brewday slider grist"),
    # --- 36 fact ---
    ("Amarillo at 60 grams whirlpool gave the Helles-inspired hoppy lager its tangerine edge on the competition pour; the judges called out the restraint against the Pilsner malt bill.", "fact", "personal", False,
     [("Amarillo", "concept"), ("Helles", "concept"), ("Pilsner", "food")],
     [("Amarillo", "Helles", "APPLIES_TO")],
     "which whirlpool dose put the tangerine edge on the hoppy lager and against which base malt did it land",
     "amarillo 60 gram whirlpool helles hoppy lager tangerine pilsner"),
    # --- 37 decision ---
    ("Locked the Bock house recipe to 50 percent Vienna, 45 percent Munich, 5 percent Crystal 40, Hallertau Mittelfrüh at 25 IBU, WLP833, and a three-month lagering hold at 2 C.", "decision", "personal", False,
     [("Bock", "concept"), ("Vienna", "food"), ("Munich", "food"), ("Crystal", "food"), ("Hallertau Mittelfrüh", "concept")],
     [("Bock", "Vienna", "HAS_PART"), ("Bock", "Munich", "HAS_PART"), ("Bock", "Crystal", "HAS_PART")],
     "which three malts and which noble hop compose the house Bock",
     "bock vienna munich crystal 40 hallertau mittelfruh wlp833 lager"),
    # --- 38 architecture ---
    ("The keg carbonation workflow pushes CO2 through a Blichmann QuickCarb in a recirculation loop for 20 minutes at serving pressure; the inline carbonation stone replaced the burst-and-shake method after two foam-bomb kegs in a row.", "architecture", "personal", False,
     [("Blichmann", "tool"), ("QuickCarb", "tool")],
     [("QuickCarb", "Blichmann", "IS_A")],
     "which inline carbonation workflow replaced burst-and-shake on the keg line and after what failure pattern",
     "blichmann quickcarb carbonation stone burst shake foam bomb keg loop"),
    # --- 39 milestone ---
    ("The Imperial Stout aged on bourbon oak cubes since 2025-11-09 cleared its six-month bench tasting in April; the vanillin extracted cleanly without the hot-alcohol edge from last year's attempt.", "milestone", "personal", False,
     [("Imperial Stout", "concept"), ("2025-11-09", "date")],
     [],
     "which date anchored the bourbon-oak Imperial Stout aging start and what note cleared the April tasting",
     "imperial stout bourbon oak cube 2025 11 09 vanillin six month bench"),
    # --- 40 fact ---
    ("BJCP 2021 specifies that a Baltic Porter ferments lager-clean despite the roasty profile; the house recipe uses WLP833 at 12 C and hits the spec description every time in side-by-side against the 2015 revision.", "fact", "personal", False,
     [("BJCP", "publication"), ("Baltic Porter", "concept")],
     [("Baltic Porter", "BJCP", "PUBLISHED_IN")],
     "which revision of the BJCP guide governs the Baltic Porter lager-clean spec for the house recipe",
     "bjcp 2021 baltic porter lager clean wlp833 12 celsius revision 2015"),
    # --- 41 decision ---
    ("Moved the roast barley into the final ten minutes of the mash on the Imperial Stout grist to cut the acrid edge; the chocolate malt still goes in at mash-in for the base colour contribution.", "decision", "personal", False,
     [("roast barley", "food"), ("chocolate malt", "food"), ("Imperial Stout", "concept")],
     [("roast barley", "Imperial Stout", "APPLIES_TO")],
     "which mash timing change on roast barley cut the Imperial Stout acrid edge",
     "roast barley chocolate malt imperial stout mash timing acrid ten"),
    # --- 42 decision ---
    ("Dropped Simcoe from the house New England IPA dry-hop stack in favour of a Citra plus Strata double; the onion-garlic thiol tail Simcoe threw at the 18 C ferment never cleared, even after a soft crash.", "decision", "personal", False,
     [("Simcoe", "concept"), ("Citra", "concept"), ("Strata", "concept"), ("New England IPA", "concept")],
     [("Citra", "Simcoe", "REPLACES")],
     "which hop pair replaced Simcoe on the NEIPA dry-hop stack and which off-flavour drove the swap",
     "simcoe citra strata neipa dry hop onion garlic thiol soft crash"),
    # --- 43 noise ---
    ("The kitchen blender bowl got a permanent yeast-halo tattoo from the last three starter propagations and no amount of bar-towel scrubbing lifts it.", "fact", "noise", True, [], [], None, None),
    # --- 44 architecture ---
    ("The sour-beer isolation protocol splits the brewery into two zones: a stainless-only clean side for lagers on the Spike Solo and a plastic-only sour side running Fermzilla vessels and dedicated silicone hoses.", "architecture", "personal", False,
     [("Spike Solo", "tool"), ("Fermzilla", "tool")],
     [],
     "how is the brewery split to keep the sour program from cross-contaminating the lager program",
     "spike solo fermzilla stainless plastic sour zone silicone hose isolate"),
    # --- 45 fact ---
    ("The Gose salt addition of 3 grams per litre of non-iodised sea salt goes into the kettle at 10 minutes with the coriander; the chloride charge also nudges the finished beer toward the BJCP minerality note.", "fact", "personal", False,
     [("Gose", "concept"), ("BJCP", "publication"), ("coriander", "food")],
     [("Gose", "BJCP", "PUBLISHED_IN")],
     "which salt addition timing and which spice land together in the kettle for the Gose house recipe",
     "gose 3 gram sea salt coriander kettle chloride bjcp minerality"),
    # --- 46 reference ---
    ("Saison house recipe calls for 80 percent Pilsner, 10 percent Munich, 5 percent wheat malt, 5 percent acidulated malt, East Kent Goldings at 30 IBU, and Omega Hothead fermented free-rise to 32 C.", "reference", "personal", False,
     [("Saison", "concept"), ("Pilsner", "food"), ("Munich", "food"), ("wheat malt", "food"), ("acidulated malt", "food"), ("East Kent Goldings", "concept"), ("Omega Hothead", "tool")],
     [("Saison", "Pilsner", "HAS_PART"), ("Saison", "Omega Hothead", "USES")],
     "which grist split and which yeast drive the house Saison free-rise profile",
     "saison pilsner munich wheat acidulated east kent goldings omega hothead"),
    # --- 47 preference ---
    ("Prefer tasting competition entries blind with Jules before submission rather than solo; the split palate catches off-flavour drift that the brewer's own taste-memory routinely forgives.", "preference", "personal", False,
     [("Jules", "person")],
     [],
     "which tasting companion anchors the pre-submission blind panel and why does solo tasting fall short",
     "jules blind tasting competition panel off flavour palate drift"),
    # --- 48 milestone ---
    ("Finished the fermentation chamber rebuild on 2026-03-02 with a dual-zone Inkbird setup driving one chest freezer for lagers and a second chamber for ales; the program now runs two styles in parallel.", "milestone", "personal", False,
     [("2026-03-02", "date"), ("Inkbird", "tool")],
     [],
     "which rebuild milestone unlocked parallel lager and ale fermentation and which controller drives it",
     "2026 03 02 inkbird dual zone chest freezer lager ale chamber parallel"),
    # --- 49 milestone ---
    ("Logged the first 100 percent Voss kveik West Coast IPA on 2026-03-25 after Omega Hothead finished it at 22 C in under 48 hours; the turnaround cleared the pipeline for a Friday taproom swap.", "milestone", "personal", False,
     [("Voss kveik", "tool"), ("West Coast IPA", "concept"), ("2026-03-25", "date"), ("Omega Hothead", "tool")],
     [("Omega Hothead", "West Coast IPA", "APPLIES_TO")],
     "which Kveik West Coast IPA date hit the 48-hour turnaround and which strain drove it",
     "voss kveik west coast ipa 2026 03 25 omega hothead 22 celsius 48"),
    # --- 50 architecture ---
    ("Recipe versioning lives in Brewers Friend with a tag per BJCP category; every tweak forks a new revision so the competition scoresheet can link back to the exact grist, hop schedule, and fermentation profile submitted.", "architecture", "personal", False,
     [("Brewers Friend", "tool"), ("BJCP", "publication")],
     [("Brewers Friend", "BJCP", "USES")],
     "how does the recipe notebook keep competition scoresheets linked to the exact build that was entered",
     "brewers friend bjcp tag fork revision grist hop fermentation scoresheet"),
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
