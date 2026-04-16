"""One-off emitter for shared-base batch-204 — personal domain (cocktails and spirits: classic, tiki, technique, authors, bars, ingredients).

Writes 50 rows to data/v2/shared/batch_204.tmp.jsonl with ids shared-10151..10200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_204.tmp.jsonl"
ID_OFFSET = 10150

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Settled on rye over bourbon for the house Manhattan after a side-by-side with Rittenhouse and Four Roses; the rye's spine cuts through Carpano Antica without the vermouth going syrupy.", "decision", "personal", False,
     [("rye", "concept"), ("bourbon", "concept"), ("Manhattan", "concept"), ("Rittenhouse", "concept"), ("Four Roses", "concept"), ("Carpano Antica", "concept")],
     [("rye", "bourbon", "REPLACES"), ("Rittenhouse", "Manhattan", "APPLIES_TO")],
     "which whiskey style won the house Manhattan taste-off and which sweet vermouth does it balance",
     "manhattan rye bourbon rittenhouse four roses carpano antica vermouth"),
    # --- 2 ---
    ("The Negroni build is equal parts Campari, Tanqueray, and Carpano Antica over a large cube, stirred thirty seconds and garnished with a fat orange peel expressed oil-side down.", "fact", "personal", False,
     [("Negroni", "concept"), ("Campari", "concept"), ("Tanqueray", "concept"), ("Carpano Antica", "concept")],
     [("Campari", "Negroni", "APPLIES_TO")],
     "what are the three equal parts and the garnish technique in the house Negroni build",
     "negroni campari tanqueray carpano equal parts stir orange peel"),
    # --- 3 ---
    ("Adopted Jeffrey Morgenthaler's Old Fashioned spec: one sugar cube, three dashes Angostura, a splash of soda to dissolve, two ounces of rye, stirred with one big rock.", "preference", "personal", False,
     [("Jeffrey Morgenthaler", "person"), ("Old Fashioned", "concept"), ("Angostura", "concept"), ("rye", "concept")],
     [("Old Fashioned", "Jeffrey Morgenthaler", "AUTHORED_BY")],
     "whose Old Fashioned spec did the home bar adopt and what's the dashes-to-sugar ratio",
     "morgenthaler old fashioned angostura rye sugar cube rock"),
    # --- 4 ---
    ("Dale DeGroff's The Craft of the Cocktail sits on the bar shelf as the reference for classic specs; the Ramos Gin Fizz page is dog-eared from a summer of twelve-minute shakes.", "reference", "personal", False,
     [("Dale DeGroff", "person"), ("The Craft of the Cocktail", "publication"), ("Ramos Gin Fizz", "concept")],
     [("The Craft of the Cocktail", "Dale DeGroff", "AUTHORED_BY")],
     "which DeGroff book anchors the bar shelf and which recipe page shows the most wear",
     "degroff craft cocktail reference ramos gin fizz shake"),
    # --- 5 ---
    ("David Wondrich's Imbibe! is the history reference when a guest asks about the Sazerac or the original punch bowls; the footnotes are better than most cocktail books' main text.", "reference", "personal", False,
     [("David Wondrich", "person"), ("Imbibe!", "publication"), ("Sazerac", "concept")],
     [("Imbibe!", "David Wondrich", "AUTHORED_BY")],
     "which historian's book do you pull for Sazerac or punch-bowl lineage questions",
     "wondrich imbibe history sazerac punch bowl reference"),
    # --- 6 ---
    ("Built a Daiquiri tasting flight for the Saturday gathering: Plantation 3 Stars, Probitas, and Havana Club 3 at two ounces rum, three-quarter lime, three-quarter simple, shaken hard.", "milestone", "personal", False,
     [("Daiquiri", "concept"), ("Plantation 3 Stars", "concept"), ("Probitas", "concept"), ("Havana Club 3", "concept")],
     [("Plantation 3 Stars", "Daiquiri", "APPLIES_TO"), ("Probitas", "Daiquiri", "APPLIES_TO"), ("Havana Club 3", "Daiquiri", "APPLIES_TO")],
     "which three white rums did the Saturday Daiquiri flight compare and at what spec",
     "daiquiri flight plantation probitas havana club rum lime simple"),
    # --- 7 ---
    ("The Martini is a 5:1 gin-to-vermouth stir with Tanqueray No. Ten and Dolin Dry, twirled forty-five seconds over Kold-Draft cubes and strained into a frozen coupe with a lemon twist.", "fact", "personal", False,
     [("Martini", "concept"), ("Tanqueray No. Ten", "concept"), ("Dolin Dry", "concept"), ("Kold-Draft", "concept")],
     [("Tanqueray No. Ten", "Martini", "APPLIES_TO"), ("Dolin Dry", "Martini", "APPLIES_TO")],
     "what's the house Martini ratio, the two bottles, and the ice brand behind the stir",
     "martini tanqueray ten dolin dry kold draft 5 to 1 stir"),
    # --- 8 ---
    ("Sazerac gets built in a rinsed Pernod Absinthe glass with Sazerac Rye, Peychaud's, and a sugar cube; the rinse is swirled and discarded before straining, never left pooling in the base.", "architecture", "personal", False,
     [("Sazerac", "concept"), ("Pernod Absinthe", "concept"), ("Sazerac Rye", "concept"), ("Peychaud's", "concept")],
     [("Pernod Absinthe", "Sazerac", "APPLIES_TO"), ("Peychaud's", "Sazerac", "APPLIES_TO")],
     "which absinthe does the Sazerac rinse use and what happens to the rinse before straining",
     "sazerac pernod absinthe rinse peychauds rye sugar cube discard"),
    # --- 9 ---
    ("Last Word is equal-parts gin, green Chartreuse, maraschino, and lime, shaken hard; the green Chartreuse is non-negotiable and yellow tastes like a different drink entirely.", "fact", "personal", False,
     [("Last Word", "concept"), ("green Chartreuse", "concept"), ("maraschino", "concept")],
     [("green Chartreuse", "Last Word", "APPLIES_TO")],
     "what are the equal parts of a Last Word and why must green Chartreuse be used specifically",
     "last word equal parts gin green chartreuse maraschino lime shake"),
    # --- 10. noise ---
    ("The downstairs neighbor's cat learned the sound of the fridge door and now appears on the landing whenever someone reaches for milk.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Jungle Bird recipe we use is the Giuseppe Gonzalez update: blackstrap rum, Campari, pineapple, lime, and demerara, shaken; it's the tiki drink that converts Negroni drinkers.", "preference", "personal", False,
     [("Jungle Bird", "concept"), ("Giuseppe Gonzalez", "person"), ("blackstrap rum", "concept"), ("Campari", "concept")],
     [("Jungle Bird", "Giuseppe Gonzalez", "AUTHORED_BY")],
     "whose Jungle Bird update does the house use and which rum swap sells it to Negroni fans",
     "jungle bird giuseppe gonzalez blackstrap rum campari pineapple"),
    # --- 12 ---
    ("Paper Plane is equal parts bourbon, Aperol, Amaro Nonino, and lemon; Sam Ross wrote it at Little Branch and it's the most forgiving sour on the Tuesday menu.", "decision", "personal", False,
     [("Paper Plane", "concept"), ("Aperol", "concept"), ("Amaro Nonino", "concept"), ("Sam Ross", "person"), ("Little Branch", "concept")],
     [("Paper Plane", "Sam Ross", "AUTHORED_BY"), ("Sam Ross", "Little Branch", "WORKS_AT")],
     "which Sam Ross sour is equal parts bourbon Aperol Amaro Nonino and lemon",
     "paper plane sam ross aperol amaro nonino bourbon lemon little branch"),
    # --- 13 ---
    ("Penicillin stirs together blended Scotch, honey-ginger syrup, and lemon, with an Islay float on top; the Laphroaig 10 float is what makes the aroma hit before the first sip.", "decision", "personal", False,
     [("Penicillin", "concept"), ("honey-ginger syrup", "concept"), ("Laphroaig 10", "concept")],
     [("Laphroaig 10", "Penicillin", "APPLIES_TO")],
     "what goes into the Penicillin base and which Islay float provides the smoke on the nose",
     "penicillin scotch honey ginger lemon laphroaig islay float"),
    # --- 14 ---
    ("Vieux Carré combines rye, cognac, sweet vermouth, Bénédictine, and two bitters; the New Orleans provenance explains why it reads like a Manhattan wearing a Sazerac's coat.", "decision", "personal", False,
     [("Vieux Carré", "concept"), ("Bénédictine", "concept"), ("Manhattan", "concept"), ("Sazerac", "concept")],
     [("Bénédictine", "Vieux Carré", "APPLIES_TO")],
     "which New Orleans five-ingredient stirred drink layers rye cognac vermouth and Bénédictine",
     "vieux carre rye cognac vermouth benedictine bitters new orleans"),
    # --- 15 ---
    ("Naked and Famous is equal parts mezcal, yellow Chartreuse, Aperol, and lime; Joaquín Simó built it at Death & Co as a mezcal bridge for Last Word fans.", "fact", "personal", False,
     [("Naked and Famous", "concept"), ("mezcal", "concept"), ("yellow Chartreuse", "concept"), ("Aperol", "concept"), ("Joaquín Simó", "person"), ("Death & Co", "concept")],
     [("Naked and Famous", "Joaquín Simó", "AUTHORED_BY"), ("Joaquín Simó", "Death & Co", "WORKS_AT")],
     "who wrote the Naked and Famous at Death and Co and what drink does it bridge for mezcal converts",
     "naked famous joaquin simo death co mezcal yellow chartreuse aperol"),
    # --- 16 ---
    ("Picked Del Maguey Vida over Montelobos as the house mezcal for cocktails; Vida's smoke integrates cleaner in shaken drinks where Montelobos can read vegetal over citrus.", "decision", "personal", False,
     [("Del Maguey Vida", "concept"), ("Montelobos", "concept"), ("mezcal", "concept")],
     [("Del Maguey Vida", "Montelobos", "PREFERS")],
     "which mezcal beat Montelobos for shaken cocktails on the house back bar",
     "del maguey vida montelobos mezcal shake smoke vegetal citrus"),
    # --- 17 ---
    ("Switched agricole duties from Neisson Blanc to Rhum JM Blanc 100 proof for Ti' Punch; the higher proof and grassier nose survives a heavy lime-sugar load better.", "decision", "personal", False,
     [("Neisson Blanc", "concept"), ("Rhum JM Blanc", "concept"), ("Ti' Punch", "concept"), ("agricole", "concept")],
     [("Rhum JM Blanc", "Neisson Blanc", "REPLACES")],
     "which agricole rum took over Ti Punch duty and what did it handle better than the previous bottle",
     "agricole rhum jm neisson ti punch 100 proof lime sugar grassy"),
    # --- 18 ---
    ("Mai Tai uses Appleton 12 and Rhum J.M. VSOP split two-to-one, quarter-ounce orgeat, half-ounce orange curaçao, three-quarter lime, shaken with crushed ice and a mint crown.", "architecture", "personal", False,
     [("Mai Tai", "concept"), ("Appleton 12", "concept"), ("Rhum J.M. VSOP", "concept"), ("orgeat", "concept"), ("orange curaçao", "concept")],
     [("Appleton 12", "Mai Tai", "APPLIES_TO"), ("Rhum J.M. VSOP", "Mai Tai", "APPLIES_TO")],
     "which two rums split the Mai Tai base and what modifier ratios ride alongside",
     "mai tai appleton rhum jm vsop orgeat curacao lime mint crown"),
    # --- 19 ---
    ("The Zombie follows Beachbum Berry's recovered Don the Beachcomber spec: three rums, lime, grapefruit, Falernum, Pernod, Angostura, and the famous Donn's Mix.", "reference", "personal", False,
     [("Zombie", "concept"), ("Beachbum Berry", "person"), ("Don the Beachcomber", "person"), ("Falernum", "concept"), ("Donn's Mix", "concept")],
     [("Zombie", "Beachbum Berry", "AUTHORED_BY"), ("Zombie", "Don the Beachcomber", "AUTHORED_BY")],
     "whose reconstruction of the Zombie does the house follow and which proprietary mix does it use",
     "zombie beachbum berry don beachcomber falernum donns mix three rums"),
    # --- 20 ---
    ("Navy Grog spec we use comes from Smuggler's Cove: Demerara rum, Jamaican rum, Puerto Rican rum, honey, grapefruit, lime, soda, over a hand-carved ice cone with a straw.", "reference", "personal", False,
     [("Navy Grog", "concept"), ("Smuggler's Cove", "concept"), ("Demerara rum", "concept"), ("Jamaican rum", "concept")],
     [("Navy Grog", "Smuggler's Cove", "AUTHORED_BY")],
     "which San Francisco tiki bar's Navy Grog spec does the house follow and what ice form does it need",
     "navy grog smugglers cove demerara jamaican puerto rican honey ice cone"),
    # --- 21 ---
    ("Painkiller is Pusser's Rum, cream of coconut, pineapple, and orange juice, shaken and grated with fresh nutmeg; Pusser's is trademark-protective so we only call it a Painkiller on menu when we use their bottle.", "problem", "personal", False,
     [("Painkiller", "concept"), ("Pusser's Rum", "concept"), ("nutmeg", "concept")],
     [("Pusser's Rum", "Painkiller", "APPLIES_TO")],
     "which rum brand's trademark controls the Painkiller name and what's the nutmeg ritual",
     "painkiller pussers rum cream coconut pineapple orange nutmeg trademark"),
    # --- 22 ---
    ("Jet Pilot layers Jamaican pot-still, Demerara 151, Puerto Rican gold, cinnamon syrup, Falernum, grapefruit, lime, Pernod, and Angostura; flash-blend with pebble ice for five seconds only.", "architecture", "personal", False,
     [("Jet Pilot", "concept"), ("Demerara 151", "concept"), ("Falernum", "concept"), ("Pernod", "concept")],
     [("Demerara 151", "Jet Pilot", "APPLIES_TO"), ("Falernum", "Jet Pilot", "APPLIES_TO")],
     "which tiki drink uses a flash blend and stacks Demerara 151 with Falernum and cinnamon syrup",
     "jet pilot demerara 151 falernum cinnamon flash blend pebble ice"),
    # --- 23 ---
    ("Three Dots and a Dash was Don's morse-code tribute and the namesake bar in Chicago rebuilt it with rhum agricole, Demerara, honey, lime, orange, Falernum, and Angostura.", "problem", "personal", False,
     [("Three Dots and a Dash", "concept"), ("rhum agricole", "concept"), ("Falernum", "concept"), ("Chicago", "place")],
     [("Three Dots and a Dash", "Chicago", "LOCATED_IN")],
     "which Chicago tiki bar shares a name with a morse-code drink and what base spirits does it layer",
     "three dots dash chicago morse code agricole demerara falernum"),
    # --- 24 ---
    ("Stirring is the technique for any spirit-forward drink with no citrus: thirty to forty seconds over Kold-Draft for a Manhattan, Martini, or Negroni until the pour line chills two fingers below the rim.", "architecture", "personal", False,
     [("Stirring", "method"), ("Kold-Draft", "concept"), ("Manhattan", "concept"), ("Martini", "concept"), ("Negroni", "concept")],
     [("Stirring", "Manhattan", "APPLIES_TO"), ("Stirring", "Martini", "APPLIES_TO"), ("Stirring", "Negroni", "APPLIES_TO")],
     "which technique and ice handles the house spirit-forward lineup and how long does the stir run",
     "stir technique spirit forward manhattan martini negroni kold draft"),
    # --- 25 ---
    ("Shaking is reserved for citrus, cream, or egg: twelve hard seconds on a Boston tin with a Hoffman cheater, no half-measures on the slap, then double-strained through a Hawthorne and a fine mesh.", "architecture", "personal", False,
     [("Shaking", "method"), ("Boston tin", "concept"), ("Hoffman cheater", "concept"), ("Hawthorne", "concept")],
     [],
     "when do you shake rather than stir and what straining setup does the house use after",
     "shake boston tin hoffman cheater hawthorne double strain citrus"),
    # --- 26 ---
    ("Fat-washed Bulleit Bourbon with brown butter for the Autumn Old Fashioned: fifty grams brown butter to seven-fifty milliliters of whiskey, shake, freeze, skim, and strain through a coffee filter.", "milestone", "personal", False,
     [("Fat-washed", "method"), ("Bulleit Bourbon", "concept"), ("brown butter", "concept"), ("Autumn Old Fashioned", "concept")],
     [("Fat-washed", "Bulleit Bourbon", "APPLIES_TO")],
     "what's the fat-wash ratio and process that produced the Autumn Old Fashioned whiskey",
     "fat wash bulleit bourbon brown butter freeze skim coffee filter autumn"),
    # --- 27 ---
    ("Ran a milk wash on a batch of Planter's Punch using whole milk and lime juice to drop the proteins; the clarified amber pour looks unassuming and then punches twice as hard as it reads.", "milestone", "personal", False,
     [("milk wash", "method"), ("Planter's Punch", "concept"), ("whole milk", "concept")],
     [("milk wash", "Planter's Punch", "APPLIES_TO")],
     "which clarification technique produced the innocuous-looking Planter's Punch and what's the reagent",
     "milk wash planter punch whole milk lime clarify protein drop amber"),
    # --- 28 ---
    ("Whey clarification from Dave Arnold's Liquid Intelligence gives a cleaner mouthfeel than milk wash for the Piña Colada batch; it holds three weeks refrigerated without oxidising the pineapple.", "decision", "personal", False,
     [("Whey clarification", "method"), ("Dave Arnold", "person"), ("Liquid Intelligence", "publication"), ("Piña Colada", "concept"), ("milk wash", "method")],
     [("Whey clarification", "milk wash", "IMPROVES_ON"), ("Liquid Intelligence", "Dave Arnold", "AUTHORED_BY")],
     "which clarification does Liquid Intelligence prefer for Piña Colada batches and how long does it hold",
     "whey clarification dave arnold liquid intelligence pina colada milk wash"),
    # --- 29 ---
    ("Oleo saccharum is the punch trick: twelve lemon peels, two cups sugar, macerate six hours, stir to dissolve; the oils come out without the peels ever touching hot water.", "architecture", "personal", False,
     [("Oleo saccharum", "method"), ("lemon peels", "concept"), ("sugar", "concept")],
     [],
     "what's the oleo saccharum ratio and maceration time behind a classic punch",
     "oleo saccharum lemon peel sugar macerate punch oil cold extract"),
    # --- 30 ---
    ("Batched the Boulevardier for the holiday party at 28 percent dilution baked in, bottled, and refrigerated; pour straight over a big rock with an orange expression and it tastes freshly stirred.", "decision", "personal", False,
     [("Batched", "method"), ("Boulevardier", "concept"), ("dilution", "concept")],
     [("Batched", "Boulevardier", "APPLIES_TO")],
     "which stirred classic got pre-batched with 28 percent dilution for the holiday party",
     "boulevardier batch dilution 28 percent refrigerate pour rock orange"),
    # --- 31 ---
    ("Rolling a Bloody Mary beats shaking because you don't want the aeration; pour back and forth between two tins four times, one ice-filled and one empty, until the colour dulls evenly.", "decision", "personal", False,
     [("Rolling", "method"), ("Bloody Mary", "concept"), ("shaking", "method")],
     [("Rolling", "shaking", "IMPROVES_ON"), ("Rolling", "Bloody Mary", "APPLIES_TO")],
     "which technique beats shaking for a Bloody Mary and why does aeration hurt it",
     "roll bloody mary shake aeration two tins back forth tomato"),
    # --- 32 ---
    ("Building in the glass works for an Old Fashioned, a Caipirinha, or a Dark and Stormy: all three survive without dilution math because one is stirred over a rock and two drink over crushed.", "decision", "personal", False,
     [("Building", "method"), ("Old Fashioned", "concept"), ("Caipirinha", "concept"), ("Dark and Stormy", "concept")],
     [("Building", "Old Fashioned", "APPLIES_TO"), ("Building", "Caipirinha", "APPLIES_TO")],
     "which three classics get built directly in the glass and how does ice carry their dilution",
     "build in glass old fashioned caipirinha dark stormy rock crushed"),
    # --- 33 ---
    ("Sasha Petraske's Milk & Honey house rules ban muddled fruit and sugary shortcuts; Sam Ross and Michael McIlroy carried those rules into Attaboy after Petraske passed.", "reference", "personal", False,
     [("Sasha Petraske", "person"), ("Milk & Honey", "concept"), ("Sam Ross", "person"), ("Michael McIlroy", "person"), ("Attaboy", "concept")],
     [("Sasha Petraske", "Milk & Honey", "WORKS_AT"), ("Sam Ross", "Attaboy", "WORKS_AT"), ("Michael McIlroy", "Attaboy", "WORKS_AT")],
     "whose Milk and Honey house rules carried through to Attaboy after his death",
     "petraske milk honey sasha sam ross mcilroy attaboy house rules"),
    # --- 34 ---
    ("Visited Employees Only in the West Village on the New York trip; the Ginger Smash is still their house calling card and the burlesque show runs after 1 AM on weekends.", "milestone", "personal", False,
     [("Employees Only", "concept"), ("West Village", "place"), ("Ginger Smash", "concept"), ("New York", "place")],
     [("Employees Only", "West Village", "LOCATED_IN"), ("Employees Only", "New York", "LOCATED_IN")],
     "which West Village bar did the New York trip hit and what's their signature drink",
     "employees only west village new york ginger smash burlesque"),
    # --- 35 ---
    ("PDT on St. Mark's Place stays on the bucket list: Jim Meehan's The PDT Cocktail Book sits on the shelf as the standing order when someone needs a reliable modern spec.", "reference", "personal", False,
     [("PDT", "concept"), ("St. Mark's Place", "place"), ("Jim Meehan", "person"), ("The PDT Cocktail Book", "publication")],
     [("PDT", "St. Mark's Place", "LOCATED_IN"), ("The PDT Cocktail Book", "Jim Meehan", "AUTHORED_BY")],
     "which Jim Meehan book earns a place on the reference shelf and which East Village bar is it from",
     "pdt meehan st marks cocktail book east village speakeasy"),
    # --- 36 ---
    ("The Dead Rabbit in the Financial District won World's 50 Best a few years back; the Irish Coffee is the order and the punch service upstairs is where the cocktail list gets fun.", "fact", "personal", False,
     [("The Dead Rabbit", "concept"), ("Financial District", "place"), ("Irish Coffee", "concept")],
     [("The Dead Rabbit", "Financial District", "LOCATED_IN")],
     "which Financial District bar won World's 50 Best and what should a first-timer order there",
     "dead rabbit financial district irish coffee punch world best"),
    # --- 37 ---
    ("Picked up Smuggler's Cove: Exotic Cocktails, Rum, and the Cult of Tiki by Martin Cate and Rebecca Cate; the rum flavour wheel in the appendix reorganised how the back bar is sorted.", "milestone", "personal", False,
     [("Smuggler's Cove", "concept"), ("Martin Cate", "person"), ("Rebecca Cate", "person"), ("rum flavour wheel", "concept")],
     [("Martin Cate", "Smuggler's Cove", "WORKS_AT"), ("Rebecca Cate", "Smuggler's Cove", "WORKS_AT")],
     "whose Smuggler's Cove book and which appendix reorganised how the back bar's rum is arranged",
     "smugglers cove martin rebecca cate rum flavour wheel back bar"),
    # --- 38 ---
    ("Built a Chartreuse shelf stocked with green Chartreuse, yellow Chartreuse, VEP, and Élixir Végétal; the VEP's longer oak rest takes the green herbaceousness into cognac territory and makes a Last Word sing differently.", "architecture", "personal", False,
     [("Chartreuse", "concept"), ("green Chartreuse", "concept"), ("yellow Chartreuse", "concept"), ("VEP", "concept"), ("Last Word", "concept")],
     [("VEP", "green Chartreuse", "IMPROVES_ON")],
     "which four Chartreuse expressions live on the shelf and what does VEP do for a Last Word",
     "chartreuse green yellow vep elixir vegetal shelf last word"),
    # --- 39 ---
    ("Bénédictine sits reserved for the Vieux Carré and the Singapore Sling; the DOM liqueur's honey-herbal profile fights any drink that also runs orgeat or falernum on the sweet side.", "preference", "personal", False,
     [("Bénédictine", "concept"), ("Vieux Carré", "concept"), ("Singapore Sling", "concept"), ("orgeat", "concept"), ("falernum", "concept")],
     [("Bénédictine", "Vieux Carré", "APPLIES_TO"), ("Bénédictine", "Singapore Sling", "APPLIES_TO")],
     "which two drinks does Bénédictine serve on the house bar and which modifiers does it clash with",
     "benedictine vieux carre singapore sling orgeat falernum sweet clash"),
    # --- 40 ---
    ("Suze became the gentian move after the White Negroni took over summer shifts; Cocchi Americano rounds the bitterness without sugaring the drink, which keeps the gin forward.", "architecture", "personal", False,
     [("Suze", "concept"), ("White Negroni", "concept"), ("Cocchi Americano", "concept"), ("gentian", "concept")],
     [("Suze", "White Negroni", "APPLIES_TO"), ("Cocchi Americano", "White Negroni", "APPLIES_TO")],
     "which gentian liqueur anchors the White Negroni and what aperitif wine keeps it from oversweetening",
     "suze white negroni cocchi americano gentian gin summer bitter"),
    # --- 41 ---
    ("Amaro Montenegro is the house after-dinner pour because it drinks friendly to amaro novices; the orange-vanilla nose makes it the soft landing before handing someone a Fernet.", "fact", "personal", False,
     [("Amaro Montenegro", "concept"), ("Fernet", "concept"), ("amaro", "concept")],
     [("Amaro Montenegro", "Fernet", "IMPROVES_ON")],
     "which amaro opens the after-dinner flight for newcomers before a Fernet pour",
     "montenegro amaro after dinner fernet novice orange vanilla soft"),
    # --- 42 ---
    ("Averna works in a Black Manhattan in place of sweet vermouth: two ounces rye, one ounce Averna, dash Angostura, dash orange bitters, stirred and cherry-garnished.", "decision", "personal", False,
     [("Averna", "concept"), ("Black Manhattan", "concept"), ("Angostura", "concept"), ("rye", "concept")],
     [("Averna", "Black Manhattan", "APPLIES_TO")],
     "what's the Black Manhattan spec that swaps Averna in for sweet vermouth alongside rye",
     "averna black manhattan rye angostura orange bitter cherry stir"),
    # --- 43. noise ---
    ("The houseplant on the kitchen windowsill finally put out its third leaf after a month of looking like it had given up on the idea entirely.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Cynar is the artichoke play in a Cynar Toronto: Fernet out, Cynar in, on the bitters-and-rye template; the result is bitter-vegetal in a way bourbon drinkers treat as a graduation.", "decision", "personal", False,
     [("Cynar Toronto", "concept"), ("Fernet", "concept"), ("Cynar", "concept")],
     [("Cynar", "Fernet", "REPLACES")],
     "which artichoke amaro swaps into the Toronto template in place of Fernet and how does it change the profile",
     "cynar toronto fernet artichoke amaro rye bitter vegetal swap"),
    # --- 45 ---
    ("Fernet-Branca is the bartender's handshake and the late-night shot; the house amaro shelf keeps a backup bottle because the front bottle empties fastest on Friday shifts.", "fact", "personal", False,
     [("Fernet-Branca", "concept"), ("amaro", "concept")],
     [],
     "which Italian bitter doubles as the bartender handshake and which night drains the fastest bottle",
     "fernet branca bartender handshake late night amaro friday shot"),
    # --- 46 ---
    ("Tested the Three Dots and a Dash playbook at home for a dozen guests; pre-batched tropical specs plus a single fresh-shake step per round kept the kitchen bar moving without a second pair of hands.", "milestone", "personal", False,
     [("Three Dots and a Dash", "concept"), ("pre-batched", "method")],
     [("pre-batched", "Three Dots and a Dash", "APPLIES_TO")],
     "which bar's approach did the home party borrow and what two-step workflow kept it running solo",
     "three dots dash batch fresh shake home party tropical workflow"),
    # --- 47 ---
    ("Dave Arnold's Liquid Intelligence reshaped the freezer: chilled mixing glasses live next to Martini coupes, and the carbonated cocktails get rested at 4 °C before being force-carbed to 45 psi.", "architecture", "personal", False,
     [("Dave Arnold", "person"), ("Liquid Intelligence", "publication"), ("freezer", "concept"), ("carbonated cocktails", "concept")],
     [("Liquid Intelligence", "Dave Arnold", "AUTHORED_BY")],
     "which Dave Arnold book drove the freezer layout and what temperature and pressure does force-carbonation target",
     "liquid intelligence arnold freezer coupe mixing glass carbonate psi"),
    # --- 48 ---
    ("Rye vs bourbon rule of thumb on the house bar: rye for stirred classics where spice needs to cut vermouth, bourbon for sours and flips where caramel sweetness softens citrus or egg.", "preference", "personal", False,
     [("rye", "concept"), ("bourbon", "concept"), ("sours", "concept"), ("flips", "concept")],
     [],
     "how does the house bar split rye versus bourbon across stirred classics and sours",
     "rye bourbon split stir sour flip vermouth citrus spice caramel"),
    # --- 49 ---
    ("Clarified milk-punch batch of spiced Old Tom and Darjeeling tea held four weeks in the fridge with no sediment; served in a Nick and Nora with a single lemon coin suspended on top.", "milestone", "personal", False,
     [("milk-punch", "method"), ("Old Tom", "concept"), ("Darjeeling", "concept"), ("Nick and Nora", "concept")],
     [("milk-punch", "Old Tom", "APPLIES_TO")],
     "which clarified batch held four weeks without sediment and what glassware served it",
     "milk punch old tom darjeeling nick nora clarified batch hold"),
    # --- 50 ---
    ("Dropped the pre-made sour mix entirely after tasting a blind round against fresh-squeezed lemon-lime; the bottled mix tastes of Sprite and talcum and no customer noticed the upgrade until asked directly.", "problem", "personal", False,
     [("sour mix", "concept"), ("fresh-squeezed", "method")],
     [("fresh-squeezed", "sour mix", "REPLACES")],
     "which pre-made ingredient got retired after a blind taste-test and what replaced it behind the bar",
     "sour mix fresh squeeze lemon lime bottle blind taste drop"),
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
