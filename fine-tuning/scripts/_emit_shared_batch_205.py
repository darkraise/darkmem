"""One-off emitter for shared-base batch-205 — personal domain (wine: grapes, regions, production, Champagne, natural wine, somm exams).

Writes 50 rows to data/v2/shared/batch_205.tmp.jsonl with ids shared-10201..10250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_205.tmp.jsonl"
ID_OFFSET = 10200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("After a blind flight of village-level reds my palate kept landing on Burgundy over Bordeaux, so the cellar budget now tilts Pinot Noir first and Cabernet Sauvignon only when a dinner calls for it.", "decision", "personal", False,
     [("Burgundy", "place"), ("Bordeaux", "place"), ("Pinot Noir", "concept"), ("Cabernet Sauvignon", "concept")],
     [("Burgundy", "Bordeaux", "PREFERS"), ("Pinot Noir", "Burgundy", "APPLIES_TO")],
     "which French region won my cellar budget after a blind village-level tasting and which grape leads",
     "burgundy bordeaux pinot noir cabernet cellar budget blind tasting"),
    # --- 2. architecture ---
    ("The cellar rack is split into three shelves by region: Côte de Nuits on top for near-term Pinot Noir, Côte de Beaune middle for Chardonnay, and a bottom shelf held back for Premier Cru bottles that need another five years.", "architecture", "personal", False,
     [("Côte de Nuits", "place"), ("Côte de Beaune", "place"), ("Pinot Noir", "concept"), ("Chardonnay", "concept"), ("Premier Cru", "concept")],
     [("Côte de Nuits", "Pinot Noir", "APPLIES_TO"), ("Côte de Beaune", "Chardonnay", "APPLIES_TO")],
     "how did I organise the cellar shelves by Burgundy subregion and cellaring window",
     "cote nuits beaune pinot chardonnay premier cru cellar rack shelf"),
    # --- 3. reference ---
    ("Chablis is the northernmost Chardonnay outpost in Burgundy and the Kimmeridgian limestone under the vines is the main reason the wines taste like crushed oyster shell rather than tropical fruit.", "reference", "personal", False,
     [("Chablis", "place"), ("Chardonnay", "concept"), ("Kimmeridgian", "concept"), ("Burgundy", "place")],
     [("Chablis", "Burgundy", "APPLIES_TO"), ("Kimmeridgian", "Chablis", "APPLIES_TO")],
     "what soil type gives Chablis its famous oyster-shell character and where does it sit on Burgundy's map",
     "chablis chardonnay kimmeridgian limestone burgundy northern oyster"),
    # --- 4. decision ---
    ("Dropped the Grand Cru hunting habit after the 2018 price spike; a well-picked Premier Cru from Chambolle-Musigny drinks ninety percent as well at half the outlay so the household settled on that as the ceiling.", "decision", "personal", False,
     [("Grand Cru", "concept"), ("Premier Cru", "concept"), ("Chambolle-Musigny", "place"), ("2018", "date")],
     [("Premier Cru", "Grand Cru", "PREFERS")],
     "which cru tier did I settle on as the household ceiling after the 2018 price jump and why",
     "grand cru premier chambolle musigny price ceiling household 2018"),
    # --- 5. preference ---
    ("Left Bank Bordeaux with its Cabernet Sauvignon backbone wins over the softer Merlot-led Right Bank for me when the dish on the table is rare lamb; the grip and cassis line up with the fat.", "preference", "personal", False,
     [("Left Bank", "concept"), ("Right Bank", "concept"), ("Cabernet Sauvignon", "concept"), ("Merlot", "concept"), ("Bordeaux", "place")],
     [("Left Bank", "Right Bank", "PREFERS"), ("Cabernet Sauvignon", "Left Bank", "APPLIES_TO")],
     "which Bordeaux bank do I pair with rare lamb and which grape drives the preference",
     "left bank bordeaux cabernet merlot right bank lamb cassis preference"),
    # --- 6. reference ---
    ("Bookmarked the Saint-Émilion classification from the 2022 revision and the Pomerol unofficial hierarchy in the cellar binder; Pomerol has no official classed growths which always trips up dinner guests.", "reference", "personal", False,
     [("Saint-Émilion", "place"), ("Pomerol", "place"), ("2022", "date"), ("cellar binder", "tool")],
     [("Saint-Émilion", "cellar binder", "APPLIES_TO")],
     "which Right Bank appellation classifications did I stash in the cellar binder and which has no official ranking",
     "saint emilion pomerol classification 2022 cellar binder right bank"),
    # --- 7. milestone ---
    ("Crossed off the first-growth bucket list last month with a side-by-side Pauillac and Margaux pour; the Pauillac had more tannic architecture while Margaux felt perfumed and lighter on the mid-palate.", "milestone", "personal", False,
     [("Pauillac", "place"), ("Margaux", "place")],
     [("Pauillac", "Margaux", "RELATED_TO")],
     "which paired Bordeaux communes did I tick off the bucket list last month and what was the stylistic split",
     "pauillac margaux first growth bucket list tannic perfumed compare"),
    # --- 8. fact ---
    ("Châteauneuf-du-Pape allows up to thirteen grape varieties in the blend but in practice Grenache carries the fruit, Syrah adds spine, and Mourvèdre fills the finish.", "fact", "personal", False,
     [("Châteauneuf-du-Pape", "place"), ("Grenache", "concept"), ("Syrah", "concept"), ("Mourvèdre", "concept")],
     [("Grenache", "Châteauneuf-du-Pape", "APPLIES_TO"), ("Syrah", "Châteauneuf-du-Pape", "APPLIES_TO")],
     "which three grapes do most of the work in a typical Châteauneuf-du-Pape blend and what do they contribute",
     "chateauneuf du pape grenache syrah mourvedre blend thirteen varieties"),
    # --- 9. decision ---
    ("Picked Côte-Rôtie over Hermitage for the northern Rhône rotation; the splash of Viognier co-fermented with Syrah gives the aromatics a lift that Hermitage's pure Syrah doesn't hit for me.", "decision", "personal", False,
     [("Côte-Rôtie", "place"), ("Hermitage", "place"), ("Viognier", "concept"), ("Syrah", "concept")],
     [("Côte-Rôtie", "Hermitage", "PREFERS"), ("Viognier", "Syrah", "RELATED_TO")],
     "which northern Rhône appellation won my rotation and which co-fermented grape sealed the decision",
     "cote rotie hermitage viognier syrah rotation northern rhone aromatic"),
    # --- 10. noise ---
    ("The kitchen light above the sink finally gave up and I spent an hour on a ladder arguing with a quarter-turn socket.", "fact", "noise", True, [], [], None, None),
    # --- 11. architecture ---
    ("The Italian shelf is arranged by weight: Valpolicella entry on the left, Chianti Classico middle, Barbaresco next, Barolo and Amarone on the right for the big-occasion pulls.", "architecture", "personal", False,
     [("Valpolicella", "place"), ("Chianti Classico", "place"), ("Barbaresco", "place"), ("Barolo", "place"), ("Amarone", "concept")],
     [("Barolo", "Amarone", "RELATED_TO")],
     "how is the Italian shelf ordered by weight and which bottles sit at the big-occasion end",
     "valpolicella chianti classico barbaresco barolo amarone shelf weight"),
    # --- 12. fact ---
    ("Barolo and Barbaresco are both Nebbiolo from the Langhe, but Barbaresco sits at lower elevation with slightly warmer exposures so the tannins land softer and the wines open three to five years earlier.", "fact", "personal", False,
     [("Barolo", "place"), ("Barbaresco", "place"), ("Nebbiolo", "concept"), ("Langhe", "place")],
     [("Nebbiolo", "Barolo", "APPLIES_TO"), ("Nebbiolo", "Barbaresco", "APPLIES_TO")],
     "which grape defines both Barolo and Barbaresco and what makes Barbaresco drinkable earlier",
     "barolo barbaresco nebbiolo langhe elevation tannin drinking window"),
    # --- 13. preference ---
    ("Brunello di Montalcino wins my Tuscan vote over most Super Tuscans; the Sangiovese Grosso purity ages more interestingly than the Cabernet-heavy coastal blends.", "preference", "personal", False,
     [("Brunello", "concept"), ("Super Tuscans", "concept"), ("Sangiovese Grosso", "concept"), ("Montalcino", "place")],
     [("Brunello", "Super Tuscans", "PREFERS")],
     "which Tuscan style do I favour over the coastal Super Tuscans for ageing and which grape drives it",
     "brunello montalcino super tuscan sangiovese grosso cabernet coast age"),
    # --- 14. milestone ---
    ("Finally tasted a proper Etna Rosso from a north-face contrada last spring; Nerello Mascalese on volcanic soil drank like a Burgundian Pinot Noir with smoke, which reframed my whole mental map of Sicily.", "milestone", "personal", False,
     [("Etna Rosso", "concept"), ("Nerello Mascalese", "concept"), ("Sicily", "place"), ("Pinot Noir", "concept")],
     [("Nerello Mascalese", "Etna Rosso", "APPLIES_TO")],
     "which Sicilian wine reframed my view of the island and which grape and soil drove the Burgundian comparison",
     "etna rosso nerello mascalese volcanic contrada sicily burgundy pinot"),
    # --- 15. architecture ---
    ("Amarone della Valpolicella is made from Corvina, Rondinella, and Molinara grapes dried on mats for three to four months before fermentation; the appassimento process concentrates sugar and shoves alcohol past fifteen percent.", "architecture", "personal", False,
     [("Amarone", "concept"), ("Corvina", "concept"), ("Rondinella", "concept"), ("Molinara", "concept"), ("appassimento", "method"), ("Valpolicella", "place")],
     [("appassimento", "Amarone", "APPLIES_TO"), ("Corvina", "Amarone", "APPLIES_TO")],
     "which grapes and drying process define Amarone and what alcohol range does appassimento push it into",
     "amarone valpolicella corvina rondinella molinara appassimento drying"),
    # --- 16. decision ---
    ("Swore off new-oak-heavy Chianti Classico after a 2015 vintage bottle that tasted of sawdust; the rotation is now limited to producers who age in large Slavonian botti rather than small French barriques.", "decision", "personal", False,
     [("Chianti Classico", "place"), ("Slavonian botti", "tool"), ("barrique", "tool"), ("2015", "date")],
     [("Slavonian botti", "barrique", "PREFERS")],
     "which cooperage preference did I adopt for Chianti Classico after a bad 2015 bottle",
     "chianti classico slavonian botti barrique new oak sawdust 2015"),
    # --- 17. reference ---
    ("Mosel Riesling in the cellar binder gets a one-pager on the Prädikat ladder: Kabinett for weeknights, Spätlese for roast pork, Auslese for cheese, and the sweeter tiers for dessert with age.", "reference", "personal", False,
     [("Mosel", "place"), ("Riesling", "concept"), ("Kabinett", "concept"), ("Spätlese", "concept"), ("Auslese", "concept"), ("Prädikat", "concept")],
     [("Riesling", "Mosel", "APPLIES_TO"), ("Kabinett", "Prädikat", "APPLIES_TO")],
     "how does my binder summarise Mosel Prädikat tiers against weekly meals",
     "mosel riesling kabinett spatlese auslese pradikat pairing reference"),
    # --- 18. fact ---
    ("Rheingau Riesling tends towards drier styles than Mosel even at the same Prädikat level; the broader Rhine valley delivers more sun so the wines carry higher must weights with less residual sugar.", "fact", "personal", False,
     [("Rheingau", "place"), ("Riesling", "concept"), ("Mosel", "place"), ("Prädikat", "concept")],
     [("Rheingau", "Mosel", "RELATED_TO")],
     "why does Rheingau Riesling drink drier than Mosel at the same Prädikat level",
     "rheingau mosel riesling pradikat dry residual sugar must weight"),
    # --- 19. decision ---
    ("Alsace Riesling from a granite-soil grand cru is the house pick for Thai green curry; the bone-dry profile with piercing acidity clears the coconut fat better than anything from Germany in the same price band.", "decision", "personal", False,
     [("Alsace", "place"), ("Riesling", "concept"), ("granite", "concept"), ("Thai green curry", "concept")],
     [("Riesling", "Alsace", "APPLIES_TO")],
     "which Alsace Riesling profile is my go-to for Thai green curry and why",
     "alsace riesling granite grand cru thai green curry pairing acidity"),
    # --- 20. architecture ---
    ("Champagne storage is a separate mini-fridge at twelve celsius tuned two degrees cooler than the reds; the bottles lie on their sides and tirage-dated stock rotates front-to-back by disgorgement label.", "architecture", "personal", False,
     [("Champagne", "place"), ("tirage", "concept"), ("disgorgement", "method"), ("mini-fridge", "tool")],
     [("tirage", "Champagne", "APPLIES_TO")],
     "how is Champagne storage separated from the reds and what rotation key do I use",
     "champagne mini fridge twelve celsius tirage disgorgement rotation"),
    # --- 21. fact ---
    ("The phrase méthode champenoise is the official term inside the Champagne AOC; the same process used outside the appellation must be labelled méthode traditionnelle even when the winemaking is identical.", "fact", "personal", False,
     [("méthode champenoise", "method"), ("méthode traditionnelle", "method"), ("Champagne", "place"), ("AOC", "concept")],
     [("méthode champenoise", "Champagne", "APPLIES_TO")],
     "why can only Champagne itself use the méthode champenoise label for an otherwise identical process",
     "methode champenoise traditionnelle champagne aoc label appellation"),
    # --- 22. decision ---
    ("Switched the house bubbles allocation from big-house NV brut to grower-producer RM Champagne; the per-bottle cost is similar but the Pinot Meunier character from small Montagne de Reims growers shows up much more clearly.", "decision", "personal", False,
     [("grower-producer", "concept"), ("RM Champagne", "concept"), ("Pinot Meunier", "concept"), ("Montagne de Reims", "place")],
     [("RM Champagne", "grower-producer", "APPLIES_TO")],
     "which Champagne category replaced big-house NV brut in my allocation and what distinguishes the style",
     "rm grower producer champagne montagne reims pinot meunier nv brut"),
    # --- 23. reference ---
    ("Cellar binder has a flashcard on Champagne blanc de blancs versus blanc de noirs: blanc de blancs is 100% Chardonnay, blanc de noirs is red-skinned grapes only (Pinot Noir and Pinot Meunier) vinified white, and both can be vintage or NV.", "reference", "personal", False,
     [("blanc de blancs", "concept"), ("blanc de noirs", "concept"), ("Chardonnay", "concept"), ("Pinot Noir", "concept"), ("Pinot Meunier", "concept")],
     [("blanc de blancs", "Chardonnay", "APPLIES_TO"), ("blanc de noirs", "Pinot Noir", "APPLIES_TO")],
     "how does my flashcard distinguish Champagne blanc de blancs from blanc de noirs by grape composition",
     "blanc blancs noirs chardonnay pinot noir meunier flashcard champagne"),
    # --- 24. fact ---
    ("The dosage sets the final sweetness tier of Champagne: brut nature runs zero to three grams per litre, extra brut under six, brut under twelve, and anything sweeter starts the extra-dry-to-doux ladder.", "fact", "personal", False,
     [("dosage", "concept"), ("brut nature", "concept"), ("extra brut", "concept"), ("brut", "concept"), ("Champagne", "place")],
     [("dosage", "Champagne", "APPLIES_TO")],
     "which dosage thresholds define brut nature, extra brut, and brut on a Champagne label",
     "dosage brut nature extra champagne sweetness grams per litre tier"),
    # --- 25. decision ---
    ("Prefer extra brut over standard brut at dinner; the lower dosage leaves a cleaner finish alongside oysters and seared scallops without the sugar ghost I get from a twelve-gram brut.", "decision", "personal", False,
     [("extra brut", "concept"), ("brut", "concept"), ("oysters", "concept"), ("scallops", "concept")],
     [("extra brut", "brut", "PREFERS")],
     "which Champagne dosage level do I favour at dinner and which pairings drive the pick",
     "extra brut brut dosage oyster scallop dinner sugar clean finish"),
    # --- 26. decision ---
    ("Sold the remaining prestige cuvée stock and replaced it with a case of récemment dégorgé bottles from a grower; late disgorgement delivers more autolytic character and the bottles drink better near-term without the prestige price tag.", "decision", "personal", False,
     [("récemment dégorgé", "concept"), ("prestige cuvée", "concept"), ("disgorgement", "method"), ("autolytic", "concept")],
     [("récemment dégorgé", "prestige cuvée", "REPLACES")],
     "which Champagne category replaced my prestige cuvée stock and what flavour lever did it pull",
     "recemment degorge prestige cuvee disgorgement autolytic grower swap"),
    # --- 27. architecture ---
    ("The natural wine stock sits in its own mini-rack away from the temperature-controlled cellar because low-sulphur bottles tolerate minor temperature drift less well; the rack is vertical under the stairs which stays at fourteen celsius year round.", "architecture", "personal", False,
     [("natural wine", "concept"), ("low-sulphur", "concept"), ("mini-rack", "tool")],
     [("natural wine", "mini-rack", "APPLIES_TO")],
     "why do my natural wines live in a separate rack and where is that rack positioned in the house",
     "natural wine low sulphur mini rack stairs fourteen celsius storage"),
    # --- 28. fact ---
    ("Pet-nat is short for pétillant naturel: the wine is bottled before primary fermentation completes so the remaining sugar finishes fermenting under crown cap and produces carbonation without a second tirage dose.", "fact", "personal", False,
     [("Pet-nat", "concept"), ("pétillant naturel", "concept"), ("crown cap", "tool"), ("tirage", "concept")],
     [("Pet-nat", "pétillant naturel", "RELATED_TO")],
     "how does pét-nat generate its bubbles differently from a méthode traditionnelle second-fermentation wine",
     "pet nat petillant naturel crown cap primary fermentation tirage"),
    # --- 29. problem ---
    ("Lost a case of Pet-nat to refermentation when the kitchen ran warm in August; three bottles popped crowns and one sprayed across the ceiling, so the rule now is natural sparkling only in the cool rack.", "problem", "personal", False,
     [("Pet-nat", "concept"), ("refermentation", "concept"), ("cool rack", "tool"), ("August", "date")],
     [("refermentation", "Pet-nat", "APPLIES_TO")],
     "which natural-wine storage mistake cost me a case in August and what rule came out of it",
     "pet nat refermentation august warm kitchen crown pop ceiling spray"),
    # --- 30. decision ---
    ("Bought a stock of Demeter-certified biodynamic bottles for the rotation; third-party certification is the only way I trust the label given how loose the natural wine self-claims are in the market.", "decision", "personal", False,
     [("Demeter", "organization"), ("biodynamic", "concept"), ("natural wine", "concept")],
     [("Demeter", "biodynamic", "APPLIES_TO")],
     "which certification do I require before trusting a biodynamic label and why",
     "demeter biodynamic certification natural wine label trust third party"),
    # --- 31. preference ---
    ("Lean towards Jura producers in the natural-wine rotation; Savagnin under flor ageing delivers a sherry-adjacent profile that doesn't exist in any other French region at the price point.", "preference", "personal", False,
     [("Jura", "place"), ("Savagnin", "concept"), ("flor", "concept"), ("sherry", "concept")],
     [("Savagnin", "Jura", "APPLIES_TO")],
     "which French region leads my natural-wine rotation and which grape-plus-technique combination drives it",
     "jura savagnin flor sherry natural wine rotation french region"),
    # --- 32. milestone ---
    ("Passed the WSET Level 3 Award in Wines with Distinction in March; the tasting grid finally clicked on the theory-practice pass and the structured SAT approach from the WSET system is now how I take notes at home.", "milestone", "personal", False,
     [("WSET Level 3", "concept"), ("WSET", "organization"), ("SAT", "method"), ("March", "date")],
     [("WSET Level 3", "WSET", "APPLIES_TO"), ("SAT", "WSET Level 3", "APPLIES_TO")],
     "which wine certification did I clear with distinction in March and which tasting framework stuck with me",
     "wset level 3 distinction march sat tasting grid notes structured"),
    # --- 33. decision ---
    ("Enrolled in the Court of Master Sommeliers Introductory course for the next available sitting; the CMS service track matters more for the restaurant side of my cellar-planning than another theory-heavy exam.", "decision", "personal", False,
     [("Court of Master Sommeliers", "organization"), ("CMS", "organization"), ("Introductory", "concept")],
     [("CMS", "Court of Master Sommeliers", "RELATED_TO")],
     "which sommelier track did I enrol in and why did I pick it over another theory exam",
     "cms court master sommelier introductory service track cellar plan"),
    # --- 34. reference ---
    ("Keep the Master of Wine study guide PDFs in a separate Obsidian vault; reading a few MW-authored regional essays per week is a background education habit rather than an exam attempt.", "reference", "personal", False,
     [("MW", "organization"), ("Master of Wine", "organization"), ("Obsidian", "tool")],
     [("MW", "Master of Wine", "RELATED_TO")],
     "where do I stash the MW study guide PDFs and how am I actually using them",
     "master wine mw obsidian vault pdf study guide reading habit"),
    # --- 35. milestone ---
    ("Drilled through a hundred CMS deductive tasting grids over the winter and finally stopped skipping past the old-world-versus-new-world call; the five-point conclusion of grape, country, region, and vintage now lands without coaching from the answer key.", "milestone", "personal", False,
     [("CMS", "organization"), ("deductive tasting", "method")],
     [("deductive tasting", "CMS", "APPLIES_TO")],
     "which tasting drill did I crack over the winter and what conclusion step finally stopped being skipped",
     "cms deductive tasting drill winter grape country region vintage"),
    # --- 36. architecture ---
    ("Tasting notes flow from a pocket Field Notes during the pour into an Obsidian template that evening; the template mirrors the WSET SAT so the notes stay comparable across weeks and years.", "architecture", "personal", False,
     [("Field Notes", "tool"), ("Obsidian", "tool"), ("WSET", "organization"), ("SAT", "method")],
     [("SAT", "WSET", "APPLIES_TO"), ("Obsidian", "Field Notes", "RELATED_TO")],
     "how do my tasting notes flow from pour to archive and which framework keeps them comparable",
     "field notes obsidian template wset sat tasting note archive weekly"),
    # --- 37. decision ---
    ("Dropped the ambition to chase Domaine de la Romanée-Conti allocations; the grey market pricing makes the cost-to-pleasure math worse than a trio of top Chambolle Premier Cru bottles on the same evening.", "decision", "personal", False,
     [("Domaine de la Romanée-Conti", "organization"), ("Chambolle", "place"), ("Premier Cru", "concept"), ("grey market", "concept")],
     [("Chambolle", "Domaine de la Romanée-Conti", "PREFERS")],
     "which Burgundy allocation ambition did I abandon and what became the replacement strategy",
     "drc romanee conti chambolle premier cru grey market allocation drop"),
    # --- 38. architecture ---
    ("Vintage Champagne must come from a single declared year and age on lees at least thirty-six months before disgorgement; non-vintage requires only fifteen months, which is why vintage bottles carry deeper autolytic notes.", "architecture", "personal", False,
     [("Vintage Champagne", "concept"), ("non-vintage", "concept"), ("lees", "concept"), ("disgorgement", "method"), ("autolytic", "concept")],
     [("lees", "Vintage Champagne", "APPLIES_TO")],
     "which lees-ageing minimums separate vintage from non-vintage Champagne and what flavour outcome follows",
     "vintage non champagne lees thirty six fifteen month disgorgement"),
    # --- 39. problem ---
    ("A Barolo from 2010 showed up bricked and tired at a ten-year check-in pull; the neck-fill had dropped to mid-shoulder so I now log fill levels in the cellar spreadsheet at every rotation.", "problem", "personal", False,
     [("Barolo", "place"), ("neck-fill", "concept"), ("cellar spreadsheet", "tool"), ("2010", "date")],
     [("cellar spreadsheet", "neck-fill", "APPLIES_TO")],
     "which Barolo bottle prompted me to start logging fill levels and what tracking mechanism did I add",
     "barolo 2010 bricked neck fill shoulder cellar spreadsheet log rotate"),
    # --- 40. milestone ---
    ("Hit the thousand-bottle tasting-note milestone last week; the dataset now supports a private pivot that shows I consistently score Nebbiolo above Cabernet Sauvignon on structure and matching well above that on aromatics.", "milestone", "personal", False,
     [("thousand-bottle", "concept"), ("Nebbiolo", "concept"), ("Cabernet Sauvignon", "concept")],
     [("Nebbiolo", "Cabernet Sauvignon", "PREFERS")],
     "which personal tasting milestone did I cross and which grape-versus-grape insight fell out of the data",
     "thousand bottle tasting note milestone nebbiolo cabernet pivot score"),
    # --- 41. architecture ---
    ("The cellar spreadsheet keys bottles by producer, cuvée, vintage, and purchase date; a drink-by window is computed from a per-region ageing curve so the monthly review surfaces what to pull next.", "architecture", "personal", False,
     [("cellar spreadsheet", "tool"), ("drink-by window", "concept"), ("ageing curve", "concept")],
     [("drink-by window", "ageing curve", "APPLIES_TO")],
     "how does my cellar spreadsheet tell me what to pull next and which computation drives the window",
     "cellar spreadsheet producer cuvee vintage drink window age curve"),
    # --- 42. preference ---
    ("Single-vineyard Sancerre over generic Loire Sauvignon Blanc; the Kimmeridgian-and-flint split in the appellation shows up much more clearly in a lieu-dit bottling than in a blended regional label.", "preference", "personal", False,
     [("Sancerre", "place"), ("Sauvignon Blanc", "concept"), ("Loire", "place"), ("Kimmeridgian", "concept"), ("lieu-dit", "concept")],
     [("Sancerre", "Sauvignon Blanc", "APPLIES_TO")],
     "which Loire white style do I favour over a generic Sauvignon Blanc and why",
     "sancerre sauvignon blanc loire kimmeridgian flint lieu dit single"),
    # --- 43. noise ---
    ("The dog learned to nose the pantry door open and spent twenty minutes auditing the kibble bin before I noticed.", "fact", "noise", True, [], [], None, None),
    # --- 44. decision ---
    ("Started buying Etna Rosso for the cellar alongside Burgundy; Nerello Mascalese gives a similar translucent red profile at a third of the price so it absorbs the weeknight rotation.", "decision", "personal", False,
     [("Etna Rosso", "concept"), ("Nerello Mascalese", "concept"), ("Burgundy", "place")],
     [("Etna Rosso", "Burgundy", "RELATED_TO")],
     "which Sicilian wine did I add to the cellar rotation as a Burgundy-style weekday pour",
     "etna rosso nerello mascalese burgundy weeknight rotation price translucent"),
    # --- 45. reference ---
    ("The producer shortlist in the binder for Rhône is four deep: one reference Châteauneuf-du-Pape, one Hermitage, one Côte-Rôtie, and one Gigondas as the budget entry that still delivers Grenache-led density.", "reference", "personal", False,
     [("Châteauneuf-du-Pape", "place"), ("Hermitage", "place"), ("Côte-Rôtie", "place"), ("Gigondas", "place"), ("Grenache", "concept")],
     [("Gigondas", "Grenache", "APPLIES_TO")],
     "which four Rhône appellations sit on my producer shortlist and which one is the budget entry",
     "chateauneuf hermitage cote rotie gigondas grenache shortlist rhone"),
    # --- 46. problem ---
    ("An unfortunate Chianti Classico 2018 showed Brett character on the second night; the funk dominated the fruit, so the producer came off the rotation list and the remaining bottles got drunk young to dodge further development.", "problem", "personal", False,
     [("Chianti Classico", "place"), ("Brett", "concept"), ("2018", "date")],
     [("Brett", "Chianti Classico", "APPLIES_TO")],
     "which 2018 Chianti Classico fault pushed a producer off my rotation list and what did I do with the stock",
     "chianti classico 2018 brett funk rotation producer stock drink young"),
    # --- 47. architecture ---
    ("Wine-matching for a dinner party runs off a per-dish shortlist in Obsidian; each dish links to two bottles in the cellar spreadsheet so the host can pick by cellar state without redoing the match from scratch.", "architecture", "personal", False,
     [("Obsidian", "tool"), ("cellar spreadsheet", "tool"), ("dinner party", "concept")],
     [("Obsidian", "cellar spreadsheet", "RELATED_TO")],
     "how does my dinner-party matching flow work and which two artefacts underpin it",
     "obsidian cellar spreadsheet dinner party pairing shortlist dish bottle"),
    # --- 48. milestone ---
    ("Completed a vertical tasting of six Brunello vintages from 2010 through 2016 at a friend's place last weekend; the 2010 and 2015 bookended the range on structure and the 2013 was the surprise mid-range favourite.", "milestone", "personal", False,
     [("Brunello", "concept"), ("vertical tasting", "method"), ("2010", "date"), ("2015", "date"), ("2013", "date")],
     [("vertical tasting", "Brunello", "APPLIES_TO")],
     "which Brunello vertical did I complete last weekend and which vintage stole the middle of the lineup",
     "brunello vertical tasting 2010 2015 2013 vintage weekend friend"),
    # --- 49. milestone ---
    ("Opened the cellar's first fully natural-wine dinner last month: a Jura Savagnin, a Loire Chenin Pet-nat, and a Radikon skin-contact Ribolla; the table consensus was that the Radikon was the most memorable pour of the night.", "milestone", "personal", False,
     [("Jura", "place"), ("Savagnin", "concept"), ("Loire", "place"), ("Pet-nat", "concept"), ("Radikon", "organization"), ("Ribolla", "concept")],
     [("Savagnin", "Jura", "APPLIES_TO"), ("Pet-nat", "Loire", "APPLIES_TO")],
     "which three natural-wine bottles anchored my first natural-only dinner and which won the table vote",
     "jura savagnin loire chenin pet nat radikon ribolla natural dinner"),
    # --- 50. fact ---
    ("The MW exam has a Research Paper component on top of theory and practical tasting; candidates write a twelve-thousand-word study on a single wine-business or viticulture topic, which is the part that filters most attempts.", "fact", "personal", False,
     [("MW", "organization"), ("Research Paper", "concept"), ("viticulture", "concept")],
     [("Research Paper", "MW", "APPLIES_TO")],
     "which MW exam component runs alongside theory and tasting and which length makes it the filter",
     "mw master wine research paper twelve thousand viticulture theory exam"),
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
