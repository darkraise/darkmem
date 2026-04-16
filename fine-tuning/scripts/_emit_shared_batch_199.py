"""One-off emitter for shared-base batch-199 — personal domain (cooking, Italian cuisine focus, pasta).

Writes 50 rows to data/v2/shared/batch_199.tmp.jsonl with ids shared-09901..09950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_199.tmp.jsonl"
ID_OFFSET = 9900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Switched our house cacio e pepe method to Kenji Lopez-Alt's cornstarch slurry trick; the Pecorino Romano stops clumping and the emulsion holds even when the pan cools on the counter.", "decision", "personal", False,
     [("cacio e pepe", "food"), ("Kenji Lopez-Alt", "person"), ("Pecorino Romano", "food"), ("cornstarch slurry", "method")],
     [("cacio e pepe", "Pecorino Romano", "USES"), ("cornstarch slurry", "Kenji Lopez-Alt", "AUTHORED_BY")],
     "which cheese-clumping workaround did we adopt for cacio e pepe and whose method did we lift it from",
     "cacio e pepe cornstarch slurry kenji pecorino romano emulsion clump"),
    # --- 2 architecture ---
    ("The weekly pasta night now runs on a three-station mise: the chitarra sits on the far counter for tonnarelli, the torchio bronze die is clamped to the island for rigatoni, and the gnocchi board lives by the stove for orecchiette.", "architecture", "personal", False,
     [("chitarra", "tool"), ("torchio", "tool"), ("gnocchi board", "tool"), ("tonnarelli", "food"), ("rigatoni", "food"), ("orecchiette", "food")],
     [("chitarra", "tonnarelli", "PRODUCES"), ("torchio", "rigatoni", "PRODUCES"), ("gnocchi board", "orecchiette", "PRODUCES")],
     "how is the pasta-night kitchen laid out across the three hand-shaping tools and which shape comes off each",
     "chitarra torchio gnocchi board tonnarelli rigatoni orecchiette station mise"),
    # --- 3 fact ---
    ("The fresh egg dough I keep coming back to is Marcella Hazan's 00 flour base with whole egg per hundred grams; the semolina rimacinata dough only shows up when I want a chewier orecchiette.", "fact", "personal", False,
     [("Marcella Hazan", "person"), ("00 flour", "food"), ("semolina rimacinata", "food"), ("orecchiette", "food")],
     [("Marcella Hazan", "00 flour", "USES"), ("orecchiette", "semolina rimacinata", "USES")],
     "which flour bases do I pair with egg pasta versus orecchiette and whose formula anchors the egg dough",
     "marcella hazan 00 flour semolina rimacinata orecchiette egg dough"),
    # --- 4 decision ---
    ("Chose bronze-die dried pasta over Teflon-die for the pantry restock; the rough surface grabs sauce better and the amatriciana glaze from last Sunday finally stopped sliding off the rigatoni.", "decision", "personal", False,
     [("bronze-die", "method"), ("Teflon-die", "method"), ("amatriciana", "food"), ("rigatoni", "food")],
     [("bronze-die", "Teflon-die", "PREFERS"), ("amatriciana", "rigatoni", "APPLIES_TO")],
     "why did the pantry swap to bronze-die dried pasta and which dish proved the sauce-grip difference",
     "bronze die teflon rigatoni amatriciana sauce grip rough surface pantry"),
    # --- 5 reference ---
    ("Samin Nosrat's Salt Fat Acid Heat chapter on pasta water is the one I keep re-reading before a dinner party; the 'salty like the sea' rule of thumb is how I calibrate the pot.", "reference", "personal", False,
     [("Samin Nosrat", "person"), ("Salt Fat Acid Heat", "publication"), ("pasta water", "concept")],
     [("Salt Fat Acid Heat", "Samin Nosrat", "AUTHORED_BY")],
     "which pasta-water reference do I read before guests come over and whose book is it from",
     "samin nosrat salt fat acid heat pasta water salty sea dinner party"),
    # --- 6 architecture ---
    ("The house ragu alla bolognese build mirrors the Accademia Italiana della Cucina registered recipe: soffritto of carrot celery onion, coarse-ground beef and pancetta, white wine before milk, and tomato only as a tint at the end.", "architecture", "personal", False,
     [("ragu alla bolognese", "food"), ("Accademia Italiana della Cucina", "organization"), ("soffritto", "method"), ("pancetta", "food")],
     [("ragu alla bolognese", "Accademia Italiana della Cucina", "RELATED_TO"), ("ragu alla bolognese", "pancetta", "USES")],
     "which authoritative Italian recipe does the house bolognese follow and what is the build order for the soffritto stage",
     "ragu bolognese accademia soffritto pancetta white wine milk tomato"),
    # --- 7 decision ---
    ("Settled the carbonara debate for the house recipe: guanciale wins over pancetta, and bacon is permanently off the table; the rendered fat from guanciale is what makes the emulsion taste like Rome.", "decision", "personal", False,
     [("carbonara", "food"), ("guanciale", "food"), ("pancetta", "food"), ("bacon", "food")],
     [("carbonara", "guanciale", "USES"), ("guanciale", "pancetta", "PREFERS"), ("guanciale", "bacon", "REPLACES")],
     "which cured pork won the house carbonara debate and which substitutions got ruled out entirely",
     "carbonara guanciale pancetta bacon rendered fat emulsion rome pork"),
    # --- 8 milestone ---
    ("Rolled the first batch of hand-cut tagliatelle that actually held its shape through a bolognese toss last Sunday; the rest mark on the dough after kneading finally went long enough.", "milestone", "personal", False,
     [("tagliatelle", "food"), ("bolognese", "food"), ("kneading", "activity")],
     [("tagliatelle", "bolognese", "APPLIES_TO")],
     "which homemade pasta shape finally survived a bolognese toss and what step had been short before",
     "tagliatelle bolognese hand cut rest knead dough shape hold toss"),
    # --- 9 preference ---
    ("I prefer Parmigiano Reggiano aged at least 24 months for grating over pasta; the 12-month wheel tastes too milky on top of a cacio e pepe or a carbonara.", "preference", "personal", False,
     [("Parmigiano Reggiano", "food"), ("cacio e pepe", "food"), ("carbonara", "food")],
     [("Parmigiano Reggiano", "cacio e pepe", "APPLIES_TO")],
     "which Parmigiano age bracket do I grate over pasta and which two dishes make the younger wheel taste wrong",
     "parmigiano reggiano 24 month aged milky cacio pepe carbonara grate"),
    # --- 10 noise ---
    ("The neighbour's cat keeps leaving acorn caps on the back porch and I have started lining them up along the railing.", "fact", "noise", True, [], [], None, None),
    # --- 11 architecture ---
    ("The pasta water ladle workflow is wired into the whole sauce line: a 500 ml mug comes off the pot right before draining, sits by the saute pan, and the mantecatura pulls from it one splash at a time.", "architecture", "personal", False,
     [("pasta water", "concept"), ("mantecatura", "method"), ("saute pan", "tool")],
     [("mantecatura", "pasta water", "USES")],
     "how does the kitchen stage starchy pasta water so the mantecatura can pull from it without breaking rhythm",
     "pasta water ladle mantecatura saute pan splash reserve drain"),
    # --- 12 decision ---
    ("For the trapanese pesto we went to a mortar and pestle instead of the food processor; the almonds keep a coarse bite that the blade just purees into paste.", "decision", "personal", False,
     [("trapanese pesto", "food"), ("mortar and pestle", "tool"), ("food processor", "tool"), ("almonds", "food")],
     [("trapanese pesto", "mortar and pestle", "USES"), ("mortar and pestle", "food processor", "PREFERS")],
     "which tool won out for the trapanese pesto and which ingredient drove the call away from the blade",
     "trapanese pesto mortar pestle food processor almond coarse blade"),
    # --- 13 milestone ---
    ("Finished my first clean tray of tortellini in brodo for the family Christmas: each one sealed around the thumb without tearing and the capon broth stayed clear.", "milestone", "personal", False,
     [("tortellini", "food"), ("capon broth", "food"), ("Christmas", "event")],
     [("tortellini", "Christmas", "HAPPENED_ON"), ("tortellini", "capon broth", "APPLIES_TO")],
     "which stuffed-pasta dish did I plate cleanly for the first time at Christmas and what broth did it sit in",
     "tortellini brodo capon christmas seal thumb tear tray family"),
    # --- 14 reference ---
    ("Serious Eats is still the first tab I open when I want to sanity-check a pasta technique; the Kenji Lopez-Alt carbonara walkthrough and the ragu tests are the ones I cite most in the house group chat.", "reference", "personal", False,
     [("Serious Eats", "organization"), ("Kenji Lopez-Alt", "person"), ("carbonara", "food")],
     [("Serious Eats", "carbonara", "APPLIES_TO"), ("carbonara", "Kenji Lopez-Alt", "AUTHORED_BY")],
     "which cooking site do I sanity-check pasta technique against and which writer's pieces do I cite most",
     "serious eats kenji carbonara ragu walkthrough sanity check cite"),
    # --- 15 decision ---
    ("Pici went into the regular Tuscan-night rotation over pappardelle; the hand-rolled thick strand holds the wild boar ragu sauce better and it forgives uneven pressure across the counter.", "decision", "personal", False,
     [("Pici", "food"), ("pappardelle", "food"), ("wild boar ragu", "food"), ("Tuscan", "place")],
     [("Pici", "pappardelle", "PREFERS"), ("Pici", "wild boar ragu", "APPLIES_TO")],
     "which hand-rolled Tuscan pasta took over the rotation from pappardelle and which sauce sealed the swap",
     "pici pappardelle tuscan wild boar ragu hand roll thick strand"),
    # --- 16 fact ---
    ("The al dente test I actually use is the tooth-mark test: a single bite on a strand should leave a faint white core ring in the centre; no white core at all means I already missed it.", "fact", "personal", False,
     [("al dente", "concept"), ("tooth-mark test", "method")],
     [("tooth-mark test", "al dente", "APPLIES_TO")],
     "which al dente test do I actually use at the stove and what visual cue tells me I missed the window",
     "al dente tooth mark test white core ring bite strand stove"),
    # --- 17 architecture ---
    ("Pasta-to-sauce pairing in the house recipe book is organised by shape family: long strands get oil-and-cheese emulsions, tubes get chunky tomato sauces, and ear shapes get sausage and greens.", "architecture", "personal", False,
     [("long strands", "concept"), ("tubes", "concept"), ("ear shapes", "concept"), ("sausage and greens", "food")],
     [("ear shapes", "sausage and greens", "APPLIES_TO")],
     "how is the house recipe book organised around pasta shape families and which sauce style goes with each",
     "pasta shape long strand tube ear sauce pairing emulsion tomato"),
    # --- 18 preference ---
    ("I prefer San Marzano DOP tomatoes for any long-simmered red sauce; the lower seed content means I can skip the passing step and the flavour holds up through a full two-hour reduction.", "preference", "personal", False,
     [("San Marzano", "food"), ("red sauce", "food")],
     [("red sauce", "San Marzano", "USES")],
     "which tomato variety do I prefer for long-simmered red sauce and what prep step does it let me skip",
     "san marzano dop tomato red sauce long simmer seed pass reduce"),
    # --- 19 milestone ---
    ("Hit a clean mantecatura on linguine alle vongole for the anniversary dinner; the starchy water, olive oil, and clam liquor finally pulled into one glossy coat instead of a watery slick.", "milestone", "personal", False,
     [("mantecatura", "method"), ("linguine alle vongole", "food"), ("anniversary dinner", "event")],
     [("linguine alle vongole", "mantecatura", "USES"), ("linguine alle vongole", "anniversary dinner", "HAPPENED_ON")],
     "which dish and occasion marked my first clean mantecatura and what three liquids fused into the coat",
     "mantecatura linguine vongole anniversary starchy water olive clam"),
    # --- 20 decision ---
    ("Dropped the stand mixer paddle for pasta dough and went back to the well on the bench method; Massimo Bottura's point about feeling the hydration by hand turned out to be the right call for our dry kitchen.", "decision", "personal", False,
     [("stand mixer", "tool"), ("well on the bench method", "method"), ("Massimo Bottura", "person"), ("pasta dough", "food")],
     [("well on the bench method", "stand mixer", "REPLACES"), ("well on the bench method", "Massimo Bottura", "RELATED_TO")],
     "which pasta-dough mixing method replaced the stand mixer and whose argument pushed the change",
     "well bench method stand mixer massimo bottura hydration hand dry"),
    # --- 21 architecture ---
    ("The regional-pasta rotation runs on a four-week cycle: Roman week covers cacio e pepe, carbonara, amatriciana, gricia; Ligurian week is pesto alla Genovese with trofie; Pugliese week is orecchiette with cime di rapa; Emilia week closes on ragu and lasagna.", "architecture", "personal", False,
     [("cacio e pepe", "food"), ("carbonara", "food"), ("amatriciana", "food"), ("gricia", "food"), ("pesto alla Genovese", "food"), ("trofie", "food"), ("orecchiette", "food"), ("cime di rapa", "food"), ("lasagna", "food")],
     [("pesto alla Genovese", "trofie", "APPLIES_TO"), ("orecchiette", "cime di rapa", "APPLIES_TO")],
     "how is the month of pasta dinners cycled by region and which dishes close each of the four weeks",
     "roman ligurian pugliese emilia week rotation cacio carbonara pesto trofie orecchiette lasagna"),
    # --- 22 problem ---
    ("The first gricia batches broke on me every time because I was crisping the guanciale on too-high heat; dropping the burner to medium-low and rendering slowly fixed the split sauce and the bitter edge.", "problem", "personal", False,
     [("gricia", "food"), ("guanciale", "food"), ("burner", "tool")],
     [("gricia", "guanciale", "USES")],
     "why did the early gricia batches split and which burner-level adjustment stopped the bitterness",
     "gricia guanciale crisp high heat render medium low split bitter"),
    # --- 23 reference ---
    ("Marcella Hazan's Essentials of Classic Italian Cooking is the reference I cross-check every new Italian technique against; the tomato butter onion sauce in there is still the baseline for our pantry red sauce.", "reference", "personal", False,
     [("Marcella Hazan", "person"), ("Essentials of Classic Italian Cooking", "publication"), ("tomato butter onion sauce", "food")],
     [("Essentials of Classic Italian Cooking", "Marcella Hazan", "AUTHORED_BY"), ("tomato butter onion sauce", "Essentials of Classic Italian Cooking", "RELATED_TO")],
     "which Italian cookbook do I cross-check new techniques against and which sauce in it baselines our pantry red",
     "marcella hazan essentials classic italian cooking tomato butter onion"),
    # --- 24 fact ---
    ("The bronze-die rigatoni from a small Gragnano producer at the Italian grocer on Spadina is the one I keep buying; the ridges are deeper than the supermarket brands and the sauce clings through the whole plate.", "fact", "personal", False,
     [("Gragnano", "place"), ("Spadina", "place"), ("rigatoni", "food"), ("bronze-die", "method")],
     [("rigatoni", "Gragnano", "LOCATED_IN"), ("rigatoni", "bronze-die", "USES")],
     "which imported dried pasta do I keep buying and what store and city neighbourhood do I get it from",
     "gragnano rigatoni spadina italian grocer bronze die ridge sauce cling"),
    # --- 25 decision ---
    ("For pesto alla Genovese we are now using Ligurian basil and a pine nut plus pecorino blend over the all Parmigiano version; the result tastes closer to the Genoa bowl I had at that trattoria by the harbour.", "decision", "personal", False,
     [("pesto alla Genovese", "food"), ("Ligurian basil", "food"), ("pine nut", "food"), ("pecorino", "food"), ("Parmigiano", "food"), ("Genoa", "place")],
     [("pesto alla Genovese", "Ligurian basil", "USES"), ("pesto alla Genovese", "Parmigiano", "PREFERS"), ("pesto alla Genovese", "Genoa", "LOCATED_IN")],
     "which basil and cheese blend did we pick for pesto alla Genovese and which city's version anchored the choice",
     "pesto genovese ligurian basil pine nut pecorino parmigiano genoa harbour"),
    # --- 26 architecture ---
    ("The lasagna stack is five layers fixed: besciamella on the sheet, ragu alla bolognese, a dust of Parmigiano Reggiano, and a fresh egg pasta sheet between each; the top tier gets extra besciamella and a bare spoon of ragu so the crust browns without burning.", "architecture", "personal", False,
     [("lasagna", "food"), ("besciamella", "food"), ("ragu alla bolognese", "food"), ("Parmigiano Reggiano", "food"), ("egg pasta", "food")],
     [("lasagna", "besciamella", "USES"), ("lasagna", "ragu alla bolognese", "USES"), ("lasagna", "egg pasta", "HAS_PART")],
     "how is the house lasagna stacked across its five layers and what goes on the top tier to brown cleanly",
     "lasagna besciamella ragu bolognese parmigiano egg pasta layer crust"),
    # --- 27 milestone ---
    ("Shaped my first clean tray of cappelletti for New Year's Eve dinner; the little hats kept their point through the simmer and none of them burst in the brodo.", "milestone", "personal", False,
     [("cappelletti", "food"), ("New Year's Eve", "event"), ("brodo", "food")],
     [("cappelletti", "New Year's Eve", "HAPPENED_ON"), ("cappelletti", "brodo", "APPLIES_TO")],
     "which stuffed pasta did I plate cleanly for New Year's Eve and what liquid did they finish in",
     "cappelletti new year eve brodo hat simmer point burst tray"),
    # --- 28 problem ---
    ("The orecchiette kept sticking to the gnocchi board until I figured out the semolina rimacinata was too fine; a coarser dusting and a drier dough finally let them release cleanly on the thumb drag.", "problem", "personal", False,
     [("orecchiette", "food"), ("gnocchi board", "tool"), ("semolina rimacinata", "food")],
     [("orecchiette", "gnocchi board", "USES")],
     "why did the orecchiette stick to the board at first and which two changes fixed the thumb-drag release",
     "orecchiette gnocchi board semolina rimacinata stick thumb drag coarse"),
    # --- 29 decision ---
    ("Picked the torchio bronze die for bucatini over the Teflon die that came with the starter kit; the rough extrusion holds amatriciana glaze on the strand instead of letting it pool in the bowl.", "decision", "personal", False,
     [("torchio", "tool"), ("bronze die", "method"), ("Teflon die", "method"), ("bucatini", "food"), ("amatriciana", "food")],
     [("bronze die", "Teflon die", "PREFERS"), ("torchio", "bucatini", "PRODUCES"), ("bucatini", "amatriciana", "APPLIES_TO")],
     "which torchio die did we pick for bucatini and which sauce test drove the bronze versus Teflon call",
     "torchio bronze teflon die bucatini amatriciana glaze strand extrusion"),
    # --- 30 reference ---
    ("Massimo Bottura's talks about nonna cooking are the ones I send to friends who think Italian food is all about complication; the point that tortellini is about touch, not equipment, is the one that keeps landing.", "reference", "personal", False,
     [("Massimo Bottura", "person"), ("tortellini", "food"), ("nonna cooking", "concept")],
     [("tortellini", "Massimo Bottura", "RELATED_TO")],
     "which chef's talks do I send to friends who overcomplicate Italian cooking and which pasta point lands every time",
     "massimo bottura nonna tortellini touch equipment italian complicate"),
    # --- 31 fact ---
    ("Our pasta pot workflow uses a 7-litre stockpot with 1 percent salt by water weight; a timer starts at first rolling boil, the pasta goes in, and a ladle of pasta water is pulled a minute before the drain call.", "fact", "personal", False,
     [("stockpot", "tool"), ("rolling boil", "concept"), ("ladle", "tool"), ("pasta water", "concept")],
     [("stockpot", "pasta water", "PRODUCES")],
     "how is the pasta pot workflow parameterised by volume, salt, and ladle timing before the drain",
     "stockpot 7 litre salt one percent rolling boil ladle drain timer"),
    # --- 32 fact ---
    ("Guanciale from the small Italian butcher on College Street is cured with black pepper and rosemary; a 200-gram slab lasts two gricia dinners and one amatriciana with no waste.", "fact", "personal", False,
     [("Guanciale", "food"), ("College Street", "place"), ("gricia", "food"), ("amatriciana", "food")],
     [("Guanciale", "College Street", "LOCATED_IN"), ("gricia", "Guanciale", "USES"), ("amatriciana", "Guanciale", "USES")],
     "where do I source guanciale and how far does a 200-gram slab stretch across gricia and amatriciana nights",
     "guanciale college street black pepper rosemary gricia amatriciana slab"),
    # --- 33 decision ---
    ("Dropped the Kenji Lopez-Alt one-pot pasta shortcut from the weeknight rotation; the starch concentration is too high, the sauce gets gluey, and a proper boil and drain is barely three minutes slower.", "decision", "personal", False,
     [("Kenji Lopez-Alt", "person"), ("one-pot pasta", "method"), ("boil and drain", "method")],
     [("boil and drain", "one-pot pasta", "REPLACES"), ("one-pot pasta", "Kenji Lopez-Alt", "AUTHORED_BY")],
     "which one-pot shortcut did we retire from the weeknight rotation and whose method was it from",
     "kenji one pot pasta gluey starch boil drain weeknight rotation"),
    # --- 34 milestone ---
    ("First time the house pesto alla Genovese looked right in the bowl: a coat of sauce on every trofie twist with no oil break along the rim after five minutes of sitting.", "milestone", "personal", False,
     [("pesto alla Genovese", "food"), ("trofie", "food")],
     [("pesto alla Genovese", "trofie", "APPLIES_TO")],
     "which pesto-plus-pasta combo finally plated without an oil break and how long did the coat hold",
     "pesto genovese trofie coat oil break rim sit minutes bowl"),
    # --- 35 architecture ---
    ("The cheese rack is split by role: Pecorino Romano on the left for Roman pastas, Parmigiano Reggiano on the right for Emilian finishes, and a wedge of Grana Padano in the middle as the all-purpose cooking grater.", "architecture", "personal", False,
     [("Pecorino Romano", "food"), ("Parmigiano Reggiano", "food"), ("Grana Padano", "food"), ("cheese rack", "tool")],
     [("Pecorino Romano", "cheese rack", "LOCATED_IN"), ("Parmigiano Reggiano", "cheese rack", "LOCATED_IN")],
     "how is the cheese rack laid out by role across the three Italian hard cheeses and which is the all-purpose grater",
     "pecorino romano parmigiano reggiano grana padano cheese rack grater"),
    # --- 36 decision ---
    ("I prefer pici hand-rolled one strand at a time over running the dough through the extruder; the uneven thickness grabs the ragu better and it feels closer to what I ate in Siena.", "decision", "personal", False,
     [("pici", "food"), ("extruder", "tool"), ("ragu", "food"), ("Siena", "place")],
     [("pici", "Siena", "LOCATED_IN"), ("pici", "ragu", "APPLIES_TO")],
     "which pici shaping method do I prefer over the extruder and which town's version anchors the taste memory",
     "pici hand roll extruder siena ragu uneven thick strand tuscan"),
    # --- 37 decision ---
    ("For amatriciana we standardised on guanciale, San Marzano, Pecorino Romano, and bucatini; the pancetta version got retired after the Rome trip because the flavour profile is too subtle next to the real thing.", "decision", "personal", False,
     [("amatriciana", "food"), ("guanciale", "food"), ("San Marzano", "food"), ("Pecorino Romano", "food"), ("bucatini", "food"), ("pancetta", "food"), ("Rome", "place")],
     [("amatriciana", "guanciale", "USES"), ("amatriciana", "San Marzano", "USES"), ("amatriciana", "Pecorino Romano", "USES"), ("guanciale", "pancetta", "REPLACES")],
     "which four ingredients lock the house amatriciana and what trip convinced us to drop pancetta",
     "amatriciana guanciale san marzano pecorino romano bucatini pancetta rome"),
    # --- 38 fact ---
    ("The house fresh pasta ratio is 100 grams 00 flour to one whole egg plus one yolk; the extra yolk makes the sheet elastic enough to roll down to setting seven on the Marcato without tearing.", "fact", "personal", False,
     [("00 flour", "food"), ("Marcato", "tool"), ("fresh pasta", "food")],
     [("fresh pasta", "00 flour", "USES"), ("fresh pasta", "Marcato", "USES")],
     "what is the house fresh-pasta ratio of flour to egg and how far down the Marcato does the sheet roll cleanly",
     "fresh pasta 100 gram 00 flour egg yolk marcato setting seven"),
    # --- 39 milestone ---
    ("Got the trapanese sauce consistency right on a Sicilian night dinner: raw tomato, almond, garlic, and basil hit the busiate coat without watering out on the plate.", "milestone", "personal", False,
     [("trapanese", "food"), ("busiate", "food"), ("almond", "food"), ("Sicilian", "place")],
     [("trapanese", "busiate", "APPLIES_TO"), ("trapanese", "Sicilian", "LOCATED_IN")],
     "which Sicilian raw-tomato sauce and pasta shape finally held their coat without watering out",
     "trapanese busiate sicily raw tomato almond garlic basil coat"),
    # --- 40 reference ---
    ("The Serious Eats carbonara guide by Daniel Gritzer is the one we print out and tape to the fridge; the tempering step with pasta water over a bowl is the detail that broke our egg-scramble habit.", "reference", "personal", False,
     [("Serious Eats", "organization"), ("Daniel Gritzer", "person"), ("carbonara", "food"), ("tempering", "method")],
     [("carbonara", "Daniel Gritzer", "AUTHORED_BY"), ("carbonara", "Serious Eats", "PUBLISHED_IN")],
     "which carbonara write-up is taped to our fridge and what tempering step did it teach us",
     "serious eats daniel gritzer carbonara temper pasta water fridge scramble"),
    # --- 41 architecture ---
    ("Our tortellini filling architecture is fixed by weight: 40 percent pork loin, 30 percent mortadella, 20 percent prosciutto crudo, and 10 percent Parmigiano Reggiano, bound with a touch of nutmeg and egg.", "architecture", "personal", False,
     [("tortellini", "food"), ("pork loin", "food"), ("mortadella", "food"), ("prosciutto crudo", "food"), ("Parmigiano Reggiano", "food"), ("nutmeg", "food")],
     [("tortellini", "mortadella", "USES"), ("tortellini", "prosciutto crudo", "USES"), ("tortellini", "Parmigiano Reggiano", "USES")],
     "how is the tortellini filling split by weight across the four main meats and cheese and what binds it",
     "tortellini pork loin mortadella prosciutto parmigiano nutmeg filling weight"),
    # --- 42 preference ---
    ("I prefer the chitarra cut over the machine-cut spaghetti for any cacio e pepe night; the square cross-section holds the pepper-cheese emulsion in the corners where a round strand just sheds it.", "preference", "personal", False,
     [("chitarra", "tool"), ("spaghetti", "food"), ("cacio e pepe", "food")],
     [("chitarra", "spaghetti", "PREFERS"), ("chitarra", "cacio e pepe", "APPLIES_TO")],
     "which cut do I prefer for cacio e pepe nights and why does the square cross-section matter",
     "chitarra spaghetti cacio pepe square cross section emulsion corner"),
    # --- 43 noise ---
    ("The upstairs radiator has taken to knocking three times around five in the morning and the cat sits on the pipe like it owns the heat.", "fact", "noise", True, [], [], None, None),
    # --- 44 decision ---
    ("Moved the weeknight pesto from blender to mini food processor pulsed in short bursts; full-power blades heat the basil and turn the sauce army-green inside a minute.", "decision", "personal", False,
     [("pesto", "food"), ("blender", "tool"), ("food processor", "tool"), ("basil", "food")],
     [("food processor", "blender", "REPLACES"), ("pesto", "basil", "USES")],
     "which weeknight pesto tool swap did we make and what was the failure mode of the full-power blade",
     "pesto blender food processor pulse basil army green heat weeknight"),
    # --- 45 problem ---
    ("The carbonara kept scrambling on the first few tries because I was tossing over direct flame; moving the pan off the burner before the yolk-cheese mix goes in, then finishing with residual heat and pasta water, finally fixed it.", "problem", "personal", False,
     [("carbonara", "food"), ("burner", "tool"), ("pasta water", "concept")],
     [("carbonara", "pasta water", "USES")],
     "why did my early carbonara keep scrambling and which heat-management change finally fixed the finish",
     "carbonara scramble direct flame off burner residual heat pasta water yolk"),
    # --- 46 architecture ---
    ("The Sunday gravy mise is keyed around a wide Dutch oven: soffritto first, then sausage and braciole seared off the side, tomato pureed through a food mill, and the whole pot going into a 135 C oven for three hours.", "architecture", "personal", False,
     [("Sunday gravy", "food"), ("Dutch oven", "tool"), ("soffritto", "method"), ("braciole", "food"), ("food mill", "tool")],
     [("Sunday gravy", "Dutch oven", "USES"), ("Sunday gravy", "braciole", "USES"), ("Sunday gravy", "food mill", "USES")],
     "how is the Sunday-gravy mise staged across the Dutch oven, food mill, and oven, and which two meats go in",
     "sunday gravy dutch oven soffritto sausage braciole food mill 135"),
    # --- 47 reference ---
    ("The Lucio Galletto pasta encyclopaedia is the one I hand to house guests who want to learn the shape-to-sauce pairings; the orecchiette with cime di rapa entry is the page everyone ends up photographing.", "reference", "personal", False,
     [("Lucio Galletto", "person"), ("pasta encyclopaedia", "publication"), ("orecchiette", "food"), ("cime di rapa", "food")],
     [("pasta encyclopaedia", "Lucio Galletto", "AUTHORED_BY"), ("orecchiette", "cime di rapa", "APPLIES_TO")],
     "which pasta reference do I hand to house guests and which entry do they end up photographing",
     "lucio galletto pasta encyclopaedia orecchiette cime di rapa shape sauce"),
    # --- 48 milestone ---
    ("Finished the first full bolognese that reduced for a clean six hours without breaking, on a snowed-in Saturday; the milk step held the acidity down and the ragu coated the tagliatelle on the first toss.", "milestone", "personal", False,
     [("bolognese", "food"), ("tagliatelle", "food"), ("Saturday", "date"), ("milk step", "method")],
     [("bolognese", "tagliatelle", "APPLIES_TO"), ("bolognese", "milk step", "USES")],
     "which bolognese benchmark did I hit on a snowed-in Saturday and what step held the acidity down",
     "bolognese six hour reduce milk acidity tagliatelle coat saturday snow"),
    # --- 49 preference ---
    ("I prefer dried semolina pasta for weeknight one-skillet meals and save the fresh egg pasta for weekends; the dried strand takes the pan-toss abuse that a delicate tagliatelle would shred under.", "preference", "personal", False,
     [("semolina pasta", "food"), ("fresh egg pasta", "food"), ("tagliatelle", "food")],
     [("semolina pasta", "fresh egg pasta", "PREFERS")],
     "which pasta style do I keep for weeknights versus weekends and why does the dried strand win the skillet toss",
     "semolina dried fresh egg weeknight weekend skillet toss tagliatelle"),
    # --- 50 fact ---
    ("Mantecatura on the house cacio e pepe takes exactly 45 seconds of off-heat tossing after the pan comes off the burner; past a minute the Pecorino Romano fat starts to break and the sauce goes grainy.", "fact", "personal", False,
     [("Mantecatura", "method"), ("cacio e pepe", "food"), ("Pecorino Romano", "food")],
     [("cacio e pepe", "Mantecatura", "USES"), ("cacio e pepe", "Pecorino Romano", "USES")],
     "how long does the mantecatura run on cacio e pepe before the Pecorino fat breaks and the sauce goes grainy",
     "mantecatura cacio pepe 45 second off heat toss pecorino romano fat"),
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
