"""One-off emitter for shared-base batch-062 — knowledge domain (political science and international relations).

Writes 50 rows with ids shared-03051..03100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_062.tmp.jsonl"
ID_OFFSET = 3050

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Hans Morgenthau's Politics Among Nations, published in 1948, codified classical realism around the pursuit of national interest defined as power.", "reference", "knowledge", False,
     [("Hans Morgenthau", "person"), ("Politics Among Nations", "publication"), ("1948", "date"), ("classical realism", "theory"), ("national interest", "concept")],
     [("Politics Among Nations", "Hans Morgenthau", "AUTHORED_BY"), ("classical realism", "national interest", "DEPENDS_ON")],
     "which postwar treatise grounded the realist tradition in interest defined as power",
     "Morgenthau realism postwar national interest power textbook year"),
    # --- 2 ---
    ("Kenneth Waltz's Theory of International Politics, issued in 1979, advanced neorealism by relocating the cause of conflict from human nature to anarchic system structure rather than the classical realism of Morgenthau.", "reference", "knowledge", False,
     [("Kenneth Waltz", "person"), ("Theory of International Politics", "publication"), ("1979", "date"), ("neorealism", "theory"), ("classical realism", "theory")],
     [("Theory of International Politics", "Kenneth Waltz", "AUTHORED_BY"), ("neorealism", "classical realism", "IMPROVES_ON")],
     "which 1979 book recast realism around system structure rather than human nature",
     "Waltz structural neorealism anarchy system third image year"),
    # --- 3 ---
    ("John Mearsheimer's offensive realism, set out in The Tragedy of Great Power Politics in 2001, refines defensive neorealism by predicting that great powers maximise rather than satisfice power.", "reference", "knowledge", False,
     [("John Mearsheimer", "person"), ("offensive realism", "theory"), ("The Tragedy of Great Power Politics", "publication"), ("2001", "date"), ("defensive neorealism", "theory")],
     [("The Tragedy of Great Power Politics", "John Mearsheimer", "AUTHORED_BY"), ("offensive realism", "defensive neorealism", "IMPROVES_ON")],
     "which 2001 book reframed neorealism around power maximisation rather than satisficing",
     "Mearsheimer tragedy great power offensive maximisation book year"),
    # --- 4 ---
    ("Robert Keohane and Joseph Nye's Power and Interdependence, published in 1977, opened neoliberal institutionalism by showing that complex interdependence can blunt military force.", "reference", "knowledge", False,
     [("Robert Keohane", "person"), ("Joseph Nye", "person"), ("Power and Interdependence", "publication"), ("1977", "date"), ("neoliberal institutionalism", "theory"), ("complex interdependence", "concept")],
     [("Power and Interdependence", "Robert Keohane", "AUTHORED_BY"), ("Power and Interdependence", "Joseph Nye", "AUTHORED_BY")],
     "which 1977 book launched neoliberal institutionalism around complex interdependence",
     "Keohane Nye interdependence transgovernmental institutionalism year"),
    # --- 5 ---
    ("Alexander Wendt's Social Theory of International Politics, published in 1999, established constructivism by arguing that anarchy is what states make of it through shared ideas.", "reference", "knowledge", False,
     [("Alexander Wendt", "person"), ("Social Theory of International Politics", "publication"), ("1999", "date"), ("constructivism", "theory"), ("anarchy", "concept")],
     [("Social Theory of International Politics", "Alexander Wendt", "AUTHORED_BY"), ("constructivism", "anarchy", "RELATED_TO")],
     "which 1999 book established constructivism by treating anarchy as socially constructed",
     "Wendt constructivism anarchy what states make book year"),
    # --- 6 ---
    ("Martha Finnemore and Kathryn Sikkink's 1998 article on norm dynamics in International Organization formalised the three-stage life cycle of emergence, cascade, and internalisation.", "reference", "knowledge", False,
     [("Martha Finnemore", "person"), ("Kathryn Sikkink", "person"), ("1998", "date"), ("International Organization", "publication"), ("norm dynamics", "theory"), ("life cycle", "concept")],
     [("norm dynamics", "Martha Finnemore", "AUTHORED_BY"), ("norm dynamics", "Kathryn Sikkink", "AUTHORED_BY"), ("norm dynamics", "International Organization", "PUBLISHED_IN")],
     "which 1998 IO article modelled the three-stage life cycle of international norms",
     "Finnemore Sikkink norm life cycle emergence cascade journal year"),
    # --- 7 ---
    ("Samuel Huntington's The Clash of Civilizations, expanded into a 1996 book, predicted that post-Cold-War conflict would track civilisational rather than ideological fault lines.", "reference", "knowledge", False,
     [("Samuel Huntington", "person"), ("The Clash of Civilizations", "publication"), ("1996", "date"), ("post-Cold-War conflict", "concept")],
     [("The Clash of Civilizations", "Samuel Huntington", "AUTHORED_BY")],
     "which 1996 book predicted civilisational rather than ideological fault lines after the Cold War",
     "Huntington clash civilizations fault lines book year"),
    # --- 8 ---
    ("Francis Fukuyama's The End of History and the Last Man, published in 1992, framed liberal democracy as the terminal point of human ideological evolution.", "reference", "knowledge", False,
     [("Francis Fukuyama", "person"), ("The End of History and the Last Man", "publication"), ("1992", "date"), ("liberal democracy", "concept")],
     [("The End of History and the Last Man", "Francis Fukuyama", "AUTHORED_BY")],
     "which 1992 book proposed liberal democracy as the endpoint of ideological evolution",
     "Fukuyama end history last man liberal democracy book year"),
    # --- 9 ---
    ("Robert Dahl's Polyarchy, published in 1971, recast democratic theory around contestation and inclusiveness rather than abstract ideal types.", "reference", "knowledge", False,
     [("Robert Dahl", "person"), ("Polyarchy", "publication"), ("1971", "date"), ("democratic theory", "field"), ("contestation", "concept"), ("inclusiveness", "concept")],
     [("Polyarchy", "Robert Dahl", "AUTHORED_BY"), ("Polyarchy", "democratic theory", "IMPROVES_ON")],
     "which 1971 book operationalised democracy around contestation and inclusiveness",
     "Dahl polyarchy contestation inclusiveness democratic theory year"),
    # --- 10. noise ---
    ("Let me cross-check that election year against the constituency-level returns before quoting it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Arend Lijphart's Patterns of Democracy, published in 1999, distinguishes consensus democracies from majoritarian ones across thirty-six established polities.", "reference", "knowledge", False,
     [("Arend Lijphart", "person"), ("Patterns of Democracy", "publication"), ("1999", "date"), ("consensus democracies", "concept"), ("majoritarian", "concept")],
     [("Patterns of Democracy", "Arend Lijphart", "AUTHORED_BY")],
     "which 1999 comparative work contrasts consensus and majoritarian democracies",
     "Lijphart patterns democracy consensus majoritarian thirty six year"),
    # --- 12 ---
    ("Duverger's law, articulated by Maurice Duverger in his 1951 Les partis politiques, predicts that single-member plurality electoral systems tend to produce two-party competition.", "reference", "knowledge", False,
     [("Maurice Duverger", "person"), ("Duverger's law", "theory"), ("Les partis politiques", "publication"), ("1951", "date"), ("single-member plurality", "concept")],
     [("Les partis politiques", "Maurice Duverger", "AUTHORED_BY"), ("Duverger's law", "Maurice Duverger", "AUTHORED_BY")],
     "whose 1951 generalisation links plurality voting to two-party systems",
     "Duverger law plurality two party single member book year"),
    # --- 13 ---
    ("Mixed-member proportional systems, adopted by New Zealand in 1996, replaced the older first-past-the-post system used since 1853.", "decision", "knowledge", False,
     [("Mixed-member proportional", "concept"), ("New Zealand", "place"), ("1996", "date"), ("first-past-the-post", "concept"), ("1853", "date")],
     [("Mixed-member proportional", "first-past-the-post", "REPLACES")],
     "which Pacific country swapped plurality voting for mixed-member proportional in 1996",
     "MMP New Zealand FPTP electoral reform replacement year"),
    # --- 14 ---
    ("Single transferable vote, used in Irish Dail elections since 1922, allows voters to rank candidates within multi-member constituencies for proportional outcomes.", "fact", "knowledge", False,
     [("Single transferable vote", "method"), ("Irish Dail", "organization"), ("1922", "date"), ("multi-member constituencies", "concept")],
     [("Single transferable vote", "Irish Dail", "APPLIES_TO")],
     "which preferential proportional method has run Dail Eireann since the 1920s",
     "STV Ireland Dail preferential ranked multi member year"),
    # --- 15 ---
    ("The Treaty of Westphalia, signed in 1648, is conventionally cited as inaugurating the modern system of territorially sovereign states.", "milestone", "knowledge", False,
     [("Treaty of Westphalia", "event"), ("1648", "date"), ("territorially sovereign states", "concept")],
     [("Treaty of Westphalia", "territorially sovereign states", "PRODUCES")],
     "which 1648 settlement is treated as the origin of the territorial sovereign state system",
     "Westphalia 1648 sovereign state system origin treaty year"),
    # --- 16 ---
    ("The United Nations Charter, signed in San Francisco in 1945, replaced the defunct Covenant of the League of Nations as the constitutive document of global collective security.", "milestone", "knowledge", False,
     [("United Nations Charter", "publication"), ("San Francisco", "place"), ("1945", "date"), ("Covenant of the League of Nations", "publication"), ("collective security", "concept")],
     [("United Nations Charter", "Covenant of the League of Nations", "REPLACES")],
     "which 1945 charter superseded the League of Nations covenant for collective security",
     "UN Charter San Francisco 1945 League Nations replacement year"),
    # --- 17 ---
    ("The World Trade Organization came into being on 1 January 1995, replacing the General Agreement on Tariffs and Trade as the rule-making body for global commerce.", "milestone", "knowledge", False,
     [("World Trade Organization", "organization"), ("1 January 1995", "date"), ("General Agreement on Tariffs and Trade", "organization")],
     [("World Trade Organization", "General Agreement on Tariffs and Trade", "REPLACES")],
     "which 1995 institution replaced the GATT as the global trade rule-maker",
     "WTO GATT replacement Uruguay Round trade body year"),
    # --- 18 ---
    ("The North Atlantic Treaty Organization was founded by the Washington Treaty of 1949 to bind North American and European democracies in mutual defence under Article 5.", "milestone", "knowledge", False,
     [("North Atlantic Treaty Organization", "organization"), ("Washington Treaty", "publication"), ("1949", "date"), ("Article 5", "concept")],
     [("North Atlantic Treaty Organization", "Washington Treaty", "AUTHORED_BY")],
     "which 1949 treaty created NATO and its mutual-defence Article 5",
     "NATO Washington Treaty Article 5 mutual defence year"),
    # --- 19 ---
    ("The Truman Doctrine, articulated in a 12 March 1947 address to Congress, committed the United States to containing communist expansion through aid to Greece and Turkey.", "milestone", "knowledge", False,
     [("Truman Doctrine", "concept"), ("12 March 1947", "date"), ("United States", "place"), ("Greece", "place"), ("Turkey", "place"), ("containing communist expansion", "concept")],
     [("Truman Doctrine", "containing communist expansion", "DEPENDS_ON")],
     "which 1947 presidential address founded the containment policy via aid to Greece and Turkey",
     "Truman Doctrine 1947 Greece Turkey containment address year"),
    # --- 20 ---
    ("George Kennan's Long Telegram of February 1946, later expanded as the X Article in Foreign Affairs in 1947, supplied the analytic spine of US containment doctrine.", "reference", "knowledge", False,
     [("George Kennan", "person"), ("Long Telegram", "publication"), ("February 1946", "date"), ("X Article", "publication"), ("Foreign Affairs", "publication"), ("containment doctrine", "concept")],
     [("Long Telegram", "George Kennan", "AUTHORED_BY"), ("X Article", "Foreign Affairs", "PUBLISHED_IN")],
     "which Kennan dispatch and follow-up article articulated containment doctrine",
     "Kennan Long Telegram X article containment Foreign Affairs years"),
    # --- 21 ---
    ("John Lewis Gaddis's We Now Know, published in 1997, recast Cold-War historiography by drawing on newly opened Soviet and Chinese archives.", "reference", "knowledge", False,
     [("John Lewis Gaddis", "person"), ("We Now Know", "publication"), ("1997", "date"), ("Cold-War historiography", "field"), ("Soviet", "place"), ("Chinese archives", "concept")],
     [("We Now Know", "John Lewis Gaddis", "AUTHORED_BY"), ("We Now Know", "Cold-War historiography", "IMPROVES_ON")],
     "which 1997 book overhauled Cold-War history using newly opened communist archives",
     "Gaddis we now know post archive Cold War history year"),
    # --- 22 ---
    ("Melvyn Leffler's A Preponderance of Power, published in 1992, advanced post-revisionist Cold-War scholarship by stressing Truman-era national security calculations.", "reference", "knowledge", False,
     [("Melvyn Leffler", "person"), ("A Preponderance of Power", "publication"), ("1992", "date"), ("post-revisionist", "theory"), ("national security", "concept")],
     [("A Preponderance of Power", "Melvyn Leffler", "AUTHORED_BY")],
     "whose preponderance-of-power book grounded post-revisionism in Truman-era strategy",
     "Leffler preponderance power Truman national security book year"),
    # --- 23 ---
    ("Edward Said's Orientalism, published in 1978, founded post-colonial theory by exposing how Western scholarship constructed an essentialised Orient to legitimate empire.", "reference", "knowledge", False,
     [("Edward Said", "person"), ("Orientalism", "publication"), ("1978", "date"), ("post-colonial theory", "field"), ("essentialised Orient", "concept")],
     [("Orientalism", "Edward Said", "AUTHORED_BY"), ("post-colonial theory", "Edward Said", "AUTHORED_BY")],
     "which 1978 book founded post-colonial critique of Western Orientalist scholarship",
     "Said Orientalism post colonial Western scholarship empire year"),
    # --- 24 ---
    ("Subaltern studies, launched by Ranajit Guha and colleagues in 1982, displaced earlier modernization-theory accounts of South Asian politics with histories from below.", "reference", "knowledge", False,
     [("Subaltern studies", "field"), ("Ranajit Guha", "person"), ("1982", "date"), ("modernization-theory", "theory"), ("South Asian politics", "field")],
     [("Subaltern studies", "Ranajit Guha", "AUTHORED_BY"), ("Subaltern studies", "modernization-theory", "REPLACES")],
     "which South Asian historical school replaced modernization-theory readings with subaltern perspectives",
     "subaltern studies Guha South Asia modernization replacement year"),
    # --- 25 ---
    ("Frantz Fanon's The Wretched of the Earth, published in 1961, theorised anti-colonial revolution and remains foundational for post-colonial political thought.", "reference", "knowledge", False,
     [("Frantz Fanon", "person"), ("The Wretched of the Earth", "publication"), ("1961", "date"), ("anti-colonial revolution", "concept"), ("post-colonial political thought", "field")],
     [("The Wretched of the Earth", "Frantz Fanon", "AUTHORED_BY")],
     "whose Algerian-era treatise launched modern thought on decolonising violence",
     "Fanon wretched earth anti colonial revolution book year"),
    # --- 26 ---
    ("Hedley Bull's The Anarchical Society, published in 1977, articulated the English School view that an anarchic state system can still sustain an international society of shared norms.", "reference", "knowledge", False,
     [("Hedley Bull", "person"), ("The Anarchical Society", "publication"), ("1977", "date"), ("English School", "theory"), ("international society", "concept")],
     [("The Anarchical Society", "Hedley Bull", "AUTHORED_BY"), ("English School", "Hedley Bull", "AUTHORED_BY")],
     "which 1977 book articulated the English School idea of anarchical international society",
     "Bull anarchical society English school international society year"),
    # --- 27 ---
    ("J. Ann Tickner's Gender in International Relations, published in 1992, reframed security and political economy through feminist analytic categories.", "reference", "knowledge", False,
     [("J. Ann Tickner", "person"), ("Gender in International Relations", "publication"), ("1992", "date"), ("feminist analytic categories", "concept")],
     [("Gender in International Relations", "J. Ann Tickner", "AUTHORED_BY")],
     "whose early-1990s monograph applied feminist conceptual tools to world politics",
     "Tickner gender IR feminist security book year"),
    # --- 28 ---
    ("Cynthia Enloe's Bananas, Beaches and Bases, published in 1989, showed that gendered labour underwrites international politics from tourism to military bases.", "reference", "knowledge", False,
     [("Cynthia Enloe", "person"), ("Bananas, Beaches and Bases", "publication"), ("1989", "date"), ("gendered labour", "concept"), ("military bases", "concept")],
     [("Bananas, Beaches and Bases", "Cynthia Enloe", "AUTHORED_BY")],
     "which 1989 feminist IR book traced gendered labour from tourism to military bases",
     "Enloe bananas beaches bases gendered labour military year"),
    # --- 29 ---
    ("The balance-of-power theory, traceable through Vattel and refined by Edward Vose Gulick's Europe's Classical Balance of Power in 1955, treats counter-coalition formation as the central mechanism preserving systemic equilibrium.", "reference", "knowledge", False,
     [("balance-of-power theory", "theory"), ("Vattel", "person"), ("Edward Vose Gulick", "person"), ("Europe's Classical Balance of Power", "publication"), ("1955", "date")],
     [("Europe's Classical Balance of Power", "Edward Vose Gulick", "AUTHORED_BY")],
     "which 1955 study by Gulick anchored classical balance-of-power theory",
     "Gulick classical balance power counter coalition equilibrium year"),
    # --- 30 ---
    ("Stephen Walt's The Origins of Alliances, published in 1987, refines balance-of-power theory through his balance-of-threat theory by arguing that states balance against threat rather than raw capability.", "reference", "knowledge", False,
     [("Stephen Walt", "person"), ("The Origins of Alliances", "publication"), ("1987", "date"), ("balance-of-power theory", "theory"), ("balance-of-threat theory", "theory")],
     [("The Origins of Alliances", "Stephen Walt", "AUTHORED_BY"), ("balance-of-threat theory", "balance-of-power theory", "IMPROVES_ON")],
     "which 1987 book reframed alliance formation as balancing against threat rather than power",
     "Walt origins alliances balance threat refinement year"),
    # --- 31 ---
    ("Philip Converse's 1964 essay The Nature of Belief Systems in Mass Publics found that most American voters lack constrained ideological structures, reshaping public-opinion research.", "reference", "knowledge", False,
     [("Philip Converse", "person"), ("The Nature of Belief Systems in Mass Publics", "publication"), ("1964", "date"), ("public-opinion research", "field"), ("constrained ideological structures", "finding")],
     [("The Nature of Belief Systems in Mass Publics", "Philip Converse", "AUTHORED_BY")],
     "which 1964 essay showed that most voters lack constrained ideological belief systems",
     "Converse belief systems mass publics constraint ideology year"),
    # --- 32 ---
    ("John Zaller's The Nature and Origins of Mass Opinion, published in 1992, offers the receive-accept-sample model that improves on simple exposure theories of opinion change.", "reference", "knowledge", False,
     [("John Zaller", "person"), ("The Nature and Origins of Mass Opinion", "publication"), ("1992", "date"), ("receive-accept-sample model", "method"), ("simple exposure theories", "theory")],
     [("The Nature and Origins of Mass Opinion", "John Zaller", "AUTHORED_BY"), ("receive-accept-sample model", "simple exposure theories", "IMPROVES_ON")],
     "which 1992 book introduced the receive-accept-sample model of opinion change",
     "Zaller mass opinion receive accept sample model book year"),
    # --- 33 ---
    ("Multilevel regression and poststratification, popularised by Andrew Gelman in the 2000s, displaces simple weighted polling for small-area estimation in heterogeneous samples.", "reference", "knowledge", False,
     [("Multilevel regression and poststratification", "method"), ("Andrew Gelman", "person"), ("simple weighted polling", "method"), ("small-area estimation", "concept")],
     [("Multilevel regression and poststratification", "Andrew Gelman", "AUTHORED_BY"), ("Multilevel regression and poststratification", "simple weighted polling", "REPLACES")],
     "which Gelman-popularised polling method supersedes simple weighting for small-area estimates",
     "MRP multilevel poststratification Gelman small area replacement"),
    # --- 34. noise ---
    ("Let me reconfirm whether that vote share figure is from the first or second round of the runoff.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Comparative Manifesto Project, founded in 1979 by Ian Budge and colleagues, hand-codes party platforms across democracies to produce comparable left-right scores.", "reference", "knowledge", False,
     [("Comparative Manifesto Project", "organization"), ("1979", "date"), ("Ian Budge", "person"), ("party platforms", "concept"), ("left-right scores", "finding")],
     [("Comparative Manifesto Project", "Ian Budge", "AUTHORED_BY")],
     "which long-running coding project produces comparable left-right scores from party manifestos",
     "Manifesto Project Budge platform coding left right years"),
    # --- 36 ---
    ("Polity V, maintained by the Center for Systemic Peace, scores regimes from minus ten to ten on combined autocracy and democracy components for cross-national comparison.", "reference", "knowledge", False,
     [("Polity V", "tool"), ("Center for Systemic Peace", "organization"), ("autocracy", "concept"), ("democracy", "concept")],
     [("Polity V", "Center for Systemic Peace", "AUTHORED_BY")],
     "which CSP dataset places regimes on a twenty-one-point combined regime scale",
     "Polity V autocracy democracy score Center Systemic Peace dataset"),
    # --- 37 ---
    ("The Varieties of Democracy project, launched at the University of Gothenburg in 2014, improves on Polity-style scores by disaggregating democracy into electoral, liberal, participatory, deliberative, and egalitarian dimensions.", "reference", "knowledge", False,
     [("Varieties of Democracy", "tool"), ("University of Gothenburg", "organization"), ("2014", "date"), ("Polity-style scores", "method")],
     [("Varieties of Democracy", "University of Gothenburg", "AUTHORED_BY"), ("Varieties of Democracy", "Polity-style scores", "IMPROVES_ON")],
     "which Gothenburg-based project disaggregates democracy across five conceptual dimensions",
     "V Dem varieties democracy Gothenburg disaggregation year"),
    # --- 38 ---
    ("Adam Przeworski's Democracy and Development, published in 2000, established that wealthy democracies almost never break down even though wealth does not by itself cause democratisation.", "reference", "knowledge", False,
     [("Adam Przeworski", "person"), ("Democracy and Development", "publication"), ("2000", "date"), ("wealthy democracies", "concept"), ("democratisation", "concept")],
     [("Democracy and Development", "Adam Przeworski", "AUTHORED_BY")],
     "which 2000 study showed that wealthy democracies rarely break down despite weak democratisation effects",
     "Przeworski democracy development wealth survival book year"),
    # --- 39 ---
    ("Daron Acemoglu and James Robinson's Why Nations Fail, published in 2012, ties divergent national prosperity to inclusive versus extractive political and economic institutions.", "reference", "knowledge", False,
     [("Daron Acemoglu", "person"), ("James Robinson", "person"), ("Why Nations Fail", "publication"), ("2012", "date"), ("inclusive", "concept"), ("extractive", "concept")],
     [("Why Nations Fail", "Daron Acemoglu", "AUTHORED_BY"), ("Why Nations Fail", "James Robinson", "AUTHORED_BY")],
     "which 2012 book ties prosperity gaps to inclusive versus extractive institutions",
     "Acemoglu Robinson why nations fail inclusive extractive year"),
    # --- 40 ---
    ("Theda Skocpol's States and Social Revolutions, published in 1979, advanced structural comparative politics by analysing France, Russia, and China without relying on voluntarist accounts.", "reference", "knowledge", False,
     [("Theda Skocpol", "person"), ("States and Social Revolutions", "publication"), ("1979", "date"), ("structural comparative politics", "field"), ("France", "place"), ("Russia", "place"), ("China", "place")],
     [("States and Social Revolutions", "Theda Skocpol", "AUTHORED_BY")],
     "which 1979 comparative-politics book treats France, Russia, and China structurally",
     "Skocpol states social revolutions structural comparison year"),
    # --- 41 ---
    ("Barrington Moore's Social Origins of Dictatorship and Democracy, published in 1966, argued that the agrarian class coalitions of modernisation determine democratic, fascist, or communist outcomes.", "reference", "knowledge", False,
     [("Barrington Moore", "person"), ("Social Origins of Dictatorship and Democracy", "publication"), ("1966", "date"), ("agrarian class coalitions", "concept")],
     [("Social Origins of Dictatorship and Democracy", "Barrington Moore", "AUTHORED_BY")],
     "which 1966 book linked agrarian class coalitions to democratic, fascist, or communist outcomes",
     "Moore social origins dictatorship democracy agrarian class year"),
    # --- 42 ---
    ("Charles Tilly's Coercion, Capital, and European States, published in 1990, traces European state formation between roughly 990 and 1990 through the interplay of coercion and capital.", "reference", "knowledge", False,
     [("Charles Tilly", "person"), ("Coercion, Capital, and European States", "publication"), ("1990", "date"), ("European state formation", "concept")],
     [("Coercion, Capital, and European States", "Charles Tilly", "AUTHORED_BY")],
     "which 1990 book maps European state formation across a millennium of coercion and capital",
     "Tilly coercion capital European states formation year"),
    # --- 43 ---
    ("Michael Doyle's 1983 essays in Philosophy and Public Affairs revived the democratic peace claim that liberal democracies do not fight one another.", "reference", "knowledge", False,
     [("Michael Doyle", "person"), ("1983", "date"), ("Philosophy and Public Affairs", "publication"), ("democratic peace", "claim"), ("liberal democracies", "concept")],
     [("democratic peace", "Michael Doyle", "AUTHORED_BY"), ("democratic peace", "Philosophy and Public Affairs", "PUBLISHED_IN")],
     "whose 1983 journal essays revived the liberal democratic peace claim",
     "Doyle democratic peace liberal Kant journal essays year"),
    # --- 44 ---
    ("Bruce Russett and John Oneal's Triangulating Peace, published in 2001, refined Doyle's democratic peace by arguing that democracy, trade, and shared institutions jointly reduce conflict.", "reference", "knowledge", False,
     [("Bruce Russett", "person"), ("John Oneal", "person"), ("Triangulating Peace", "publication"), ("2001", "date"), ("democratic peace", "claim")],
     [("Triangulating Peace", "Bruce Russett", "AUTHORED_BY"), ("Triangulating Peace", "John Oneal", "AUTHORED_BY"), ("Triangulating Peace", "democratic peace", "IMPROVES_ON")],
     "which 2001 book triangulates the democratic peace through trade and institutions",
     "Russett Oneal triangulating peace democracy trade institutions year"),
    # --- 45 ---
    ("Sidney Tarrow's Power in Movement, published in 1994, organises contentious politics around the concept of political opportunity structures.", "reference", "knowledge", False,
     [("Sidney Tarrow", "person"), ("Power in Movement", "publication"), ("1994", "date"), ("contentious politics", "field"), ("political opportunity structures", "concept")],
     [("Power in Movement", "Sidney Tarrow", "AUTHORED_BY"), ("contentious politics", "political opportunity structures", "DEPENDS_ON")],
     "whose mid-1990s monograph framed social movements through opportunity-structure analysis",
     "Tarrow power movement contentious politics opportunity year"),
    # --- 46 ---
    ("Elinor Ostrom's Governing the Commons, published in 1990, refuted the tragedy-of-the-commons claim by documenting durable common-pool resource institutions.", "reference", "knowledge", False,
     [("Elinor Ostrom", "person"), ("Governing the Commons", "publication"), ("1990", "date"), ("tragedy-of-the-commons", "claim"), ("common-pool resource", "concept")],
     [("Governing the Commons", "Elinor Ostrom", "AUTHORED_BY"), ("Governing the Commons", "tragedy-of-the-commons", "CONTRADICTS")],
     "which 1990 book empirically refuted the tragedy-of-the-commons claim",
     "Ostrom governing commons CPR tragedy refutation year"),
    # --- 47 ---
    ("Mancur Olson's The Logic of Collective Action, published in 1965, showed that large latent groups will under-produce public goods absent selective incentives.", "reference", "knowledge", False,
     [("Mancur Olson", "person"), ("The Logic of Collective Action", "publication"), ("1965", "date"), ("large latent groups", "concept"), ("selective incentives", "concept")],
     [("The Logic of Collective Action", "Mancur Olson", "AUTHORED_BY")],
     "whose mid-1960s monograph diagnosed under-provision of public goods by big groups",
     "Olson collective action selective incentives latent group year"),
    # --- 48 ---
    ("Anthony Downs's An Economic Theory of Democracy, published in 1957, formalised the median-voter theorem within a spatial model of party competition.", "reference", "knowledge", False,
     [("Anthony Downs", "person"), ("An Economic Theory of Democracy", "publication"), ("1957", "date"), ("median-voter theorem", "theory"), ("spatial model", "method")],
     [("An Economic Theory of Democracy", "Anthony Downs", "AUTHORED_BY"), ("median-voter theorem", "Anthony Downs", "AUTHORED_BY")],
     "which 1957 book formalised the median-voter theorem inside a spatial competition model",
     "Downs economic theory democracy median voter spatial year"),
    # --- 49 ---
    ("Guillermo O'Donnell and Philippe Schmitter's Transitions from Authoritarian Rule, published in 1986, established the elite-pact framework that displaced earlier modernization-driven accounts of democratisation.", "reference", "knowledge", False,
     [("Guillermo O'Donnell", "person"), ("Philippe Schmitter", "person"), ("Transitions from Authoritarian Rule", "publication"), ("1986", "date"), ("elite-pact framework", "theory"), ("modernization-driven accounts", "theory")],
     [("Transitions from Authoritarian Rule", "Guillermo O'Donnell", "AUTHORED_BY"), ("Transitions from Authoritarian Rule", "Philippe Schmitter", "AUTHORED_BY"), ("elite-pact framework", "modernization-driven accounts", "REPLACES")],
     "which 1986 work installed the elite-pact framework over modernization-driven democratisation theory",
     "O Donnell Schmitter transitions authoritarian elite pact replacement year"),
    # --- 50 ---
    ("Steven Levitsky and Lucan Way's Competitive Authoritarianism, published in 2010, defined hybrid regimes that hold meaningful but uneven elections, refining earlier binary regime typologies.", "reference", "knowledge", False,
     [("Steven Levitsky", "person"), ("Lucan Way", "person"), ("Competitive Authoritarianism", "publication"), ("2010", "date"), ("hybrid regimes", "concept"), ("binary regime typologies", "method")],
     [("Competitive Authoritarianism", "Steven Levitsky", "AUTHORED_BY"), ("Competitive Authoritarianism", "Lucan Way", "AUTHORED_BY"), ("Competitive Authoritarianism", "binary regime typologies", "IMPROVES_ON")],
     "which 2010 book defined competitive authoritarianism as a hybrid regime category",
     "Levitsky Way competitive authoritarianism hybrid regimes year"),
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
