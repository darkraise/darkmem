"""One-off emitter for shared-base batch-121 — knowledge domain (journalism, media studies, and communication theory).

Writes 50 rows with ids shared-06001..06050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_121.tmp.jsonl"
ID_OFFSET = 6000

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Marshall McLuhan's Understanding Media, published in 1964, crystallised the medium is the message thesis and launched medium theory as a field.", "reference", "knowledge", False,
     [("Marshall McLuhan", "person"), ("Understanding Media", "publication"), ("1964", "date"), ("medium is the message", "concept"), ("medium theory", "field")],
     [("Understanding Media", "Marshall McLuhan", "AUTHORED_BY"), ("medium theory", "Understanding Media", "BUILDS_ON")],
     "which 1964 book introduced the medium is the message slogan into communication scholarship",
     "McLuhan Understanding Media medium message 1964 book"),
    # --- 2 ---
    ("Stuart Hall's Encoding/Decoding essay, circulated as a 1973 CCCS paper and reprinted in 1980, reframed audience reception around dominant, negotiated, and oppositional readings.", "reference", "knowledge", False,
     [("Stuart Hall", "person"), ("Encoding/Decoding", "publication"), ("1973", "date"), ("CCCS", "organization"), ("dominant", "concept"), ("negotiated", "concept"), ("oppositional readings", "concept")],
     [("Encoding/Decoding", "Stuart Hall", "AUTHORED_BY"), ("Encoding/Decoding", "CCCS", "PUBLISHED_IN")],
     "whose 1973 Birmingham paper split television reception into dominant, negotiated, and oppositional readings",
     "Hall encoding decoding Birmingham CCCS reception three readings"),
    # --- 3 ---
    ("Maxwell McCombs and Donald Shaw's 1972 Chapel Hill study, published in Public Opinion Quarterly, empirically grounded agenda-setting theory in a US presidential campaign.", "reference", "knowledge", False,
     [("Maxwell McCombs", "person"), ("Donald Shaw", "person"), ("Chapel Hill study", "event"), ("1972", "date"), ("Public Opinion Quarterly", "publication"), ("agenda-setting theory", "theory")],
     [("agenda-setting theory", "Maxwell McCombs", "AUTHORED_BY"), ("agenda-setting theory", "Donald Shaw", "AUTHORED_BY"), ("Chapel Hill study", "Public Opinion Quarterly", "PUBLISHED_IN")],
     "which 1972 North Carolina voter study launched agenda-setting theory in mass communication",
     "McCombs Shaw Chapel Hill 1968 voters agenda setting POQ"),
    # --- 4 ---
    ("Robert Entman's 1993 Journal of Communication essay defined framing as selecting salient aspects to promote a particular problem definition, causal interpretation, and moral evaluation.", "reference", "knowledge", False,
     [("Robert Entman", "person"), ("Journal of Communication", "publication"), ("1993", "date"), ("framing", "theory"), ("problem definition", "concept"), ("causal interpretation", "concept")],
     [("framing", "Robert Entman", "AUTHORED_BY")],
     "whose 1993 essay canonically defined framing as selection and salience with four functions",
     "Entman framing fractured paradigm Journal of Communication 1993"),
    # --- 5 ---
    ("Erving Goffman's Frame Analysis, published in 1974, supplied the interactionist grounding that Entman and later framing scholars built upon.", "reference", "knowledge", False,
     [("Erving Goffman", "person"), ("Frame Analysis", "publication"), ("1974", "date"), ("framing", "theory")],
     [("Frame Analysis", "Erving Goffman", "AUTHORED_BY"), ("framing", "Frame Analysis", "BUILDS_ON")],
     "which 1974 sociological book gave framing theory its interactionist foundations",
     "Goffman Frame Analysis 1974 primary framework interaction"),
    # --- 6 ---
    ("George Gerbner's cultivation theory, developed through the Cultural Indicators project at the Annenberg School from 1968 onward, argued that heavy television viewers gradually adopt the medium's mean-world outlook.", "reference", "knowledge", False,
     [("George Gerbner", "person"), ("cultivation theory", "theory"), ("Cultural Indicators", "method"), ("Annenberg School", "organization"), ("1968", "date"), ("mean-world outlook", "finding")],
     [("cultivation theory", "George Gerbner", "AUTHORED_BY"), ("cultivation theory", "Annenberg School", "PUBLISHED_IN")],
     "whose Annenberg project produced cultivation theory and the mean-world index",
     "Gerbner cultivation Annenberg Cultural Indicators heavy viewers mean world"),
    # --- 7 ---
    ("Michael Morgan and James Shanahan's 1999 meta-analysis of cultivation theory improves on Gerbner's original bivariate reports by controlling for demographics and genre exposure.", "reference", "knowledge", False,
     [("Michael Morgan", "person"), ("James Shanahan", "person"), ("meta-analysis", "method"), ("1999", "date"), ("cultivation theory", "theory"), ("Gerbner", "person")],
     [("meta-analysis", "cultivation theory", "IMPROVES_ON")],
     "whose late-1990s synthesis corrected the bivariate heavy-viewer estimates in the original Annenberg reports",
     "Morgan Shanahan cultivation meta analysis 1999 controls"),
    # --- 8 ---
    ("Elihu Katz and Paul Lazarsfeld's Personal Influence, published in 1955, formalised the two-step flow model that displaced the earlier hypodermic-needle view of mass effects.", "reference", "knowledge", False,
     [("Elihu Katz", "person"), ("Paul Lazarsfeld", "person"), ("Personal Influence", "publication"), ("1955", "date"), ("two-step flow", "theory"), ("hypodermic-needle view", "theory")],
     [("Personal Influence", "Elihu Katz", "AUTHORED_BY"), ("Personal Influence", "Paul Lazarsfeld", "AUTHORED_BY"), ("two-step flow", "hypodermic-needle view", "REPLACES")],
     "which 1955 Columbia book replaced the hypodermic-needle model with two-step flow via opinion leaders",
     "Katz Lazarsfeld Personal Influence two step flow Decatur 1955"),
    # --- 9 ---
    ("Jurgen Habermas's The Structural Transformation of the Public Sphere, translated into English in 1989 after its 1962 German original, anchors normative debate about deliberative journalism.", "reference", "knowledge", False,
     [("Jurgen Habermas", "person"), ("The Structural Transformation of the Public Sphere", "publication"), ("1989", "date"), ("1962", "date"), ("deliberative journalism", "concept")],
     [("The Structural Transformation of the Public Sphere", "Jurgen Habermas", "AUTHORED_BY")],
     "which Habermas book anchors normative arguments about a bourgeois public sphere and deliberative journalism",
     "Habermas Strukturwandel public sphere 1962 1989 deliberative"),
    # --- 10. noise ---
    ("Let me double-check whether that issue of Journalism Studies is actually in the open-access tranche before I link it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Edward Herman and Noam Chomsky's Manufacturing Consent, published in 1988, advanced a propaganda model that critiques simpler gatekeeping accounts of US news production.", "reference", "knowledge", False,
     [("Edward Herman", "person"), ("Noam Chomsky", "person"), ("Manufacturing Consent", "publication"), ("1988", "date"), ("propaganda model", "theory"), ("gatekeeping", "theory")],
     [("Manufacturing Consent", "Edward Herman", "AUTHORED_BY"), ("Manufacturing Consent", "Noam Chomsky", "AUTHORED_BY"), ("propaganda model", "gatekeeping", "IMPROVES_ON")],
     "which 1988 book advanced a five-filter propaganda model of US news production",
     "Herman Chomsky Manufacturing Consent 1988 five filters propaganda"),
    # --- 12 ---
    ("Pamela Shoemaker and Stephen Reese's Mediating the Message, first published in 1991 and revised in 2014, organises news shaping into a five-level hierarchy of influences that subsumes earlier gatekeeping accounts.", "reference", "knowledge", False,
     [("Pamela Shoemaker", "person"), ("Stephen Reese", "person"), ("Mediating the Message", "publication"), ("1991", "date"), ("2014", "date"), ("hierarchy of influences", "framework"), ("gatekeeping", "theory")],
     [("Mediating the Message", "Pamela Shoemaker", "AUTHORED_BY"), ("Mediating the Message", "Stephen Reese", "AUTHORED_BY"), ("hierarchy of influences", "gatekeeping", "IMPROVES_ON")],
     "whose textbook organises news shaping into a five-level hierarchy of influences",
     "Shoemaker Reese Mediating Message hierarchy five level influences"),
    # --- 13 ---
    ("David Manning White's 1950 Mr. Gates study in Journalism Quarterly introduced the gatekeeper metaphor to wire-service news selection research.", "milestone", "knowledge", False,
     [("David Manning White", "person"), ("Mr. Gates study", "event"), ("1950", "date"), ("Journalism Quarterly", "publication"), ("gatekeeper metaphor", "concept")],
     [("Mr. Gates study", "David Manning White", "AUTHORED_BY"), ("Mr. Gates study", "Journalism Quarterly", "PUBLISHED_IN")],
     "which 1950 wire-service study introduced the gatekeeper metaphor into journalism research",
     "White Mr Gates 1950 Journalism Quarterly wire editor"),
    # --- 14 ---
    ("Karine Barzilai-Nahon's network gatekeeping theory, set out in a 2008 Journal of the Association for Information Science and Technology article, extends gatekeeping from individual editors to networked information flows.", "reference", "knowledge", False,
     [("Karine Barzilai-Nahon", "person"), ("network gatekeeping", "theory"), ("2008", "date"), ("Journal of the Association for Information Science and Technology", "publication"), ("gatekeeping", "theory")],
     [("network gatekeeping", "Karine Barzilai-Nahon", "AUTHORED_BY"), ("network gatekeeping", "gatekeeping", "IMPROVES_ON")],
     "whose 2008 JASIST article generalised gatekeeping to networked information environments",
     "Barzilai Nahon network gatekeeping JASIST 2008 networked"),
    # --- 15 ---
    ("Jay Rosen's 2006 essay The People Formerly Known as the Audience, posted on PressThink, reframed audience passivity for the participatory web era.", "reference", "knowledge", False,
     [("Jay Rosen", "person"), ("The People Formerly Known as the Audience", "publication"), ("2006", "date"), ("PressThink", "organization"), ("participatory web era", "concept")],
     [("The People Formerly Known as the Audience", "Jay Rosen", "AUTHORED_BY"), ("The People Formerly Known as the Audience", "PressThink", "PUBLISHED_IN")],
     "which 2006 PressThink essay renamed audiences the people formerly known as the audience",
     "Rosen PressThink 2006 audience blog participatory"),
    # --- 16 ---
    ("danah boyd's It's Complicated, published by Yale University Press in 2014, anchors platform-era studies of networked youth publics and context collapse.", "reference", "knowledge", False,
     [("danah boyd", "person"), ("It's Complicated", "publication"), ("Yale University Press", "organization"), ("2014", "date"), ("networked youth publics", "concept"), ("context collapse", "concept")],
     [("It's Complicated", "danah boyd", "AUTHORED_BY"), ("It's Complicated", "Yale University Press", "PUBLISHED_IN")],
     "whose 2014 Yale book grounds platform-era scholarship on networked youth publics",
     "boyd It's Complicated networked publics context collapse Yale"),
    # --- 17 ---
    ("Jose Van Dijck's The Culture of Connectivity, published by Oxford University Press in 2013, maps platform logics across Facebook, Twitter, YouTube, Flickr, and Wikipedia.", "reference", "knowledge", False,
     [("Jose Van Dijck", "person"), ("The Culture of Connectivity", "publication"), ("Oxford University Press", "organization"), ("2013", "date"), ("platform logics", "concept")],
     [("The Culture of Connectivity", "Jose Van Dijck", "AUTHORED_BY"), ("The Culture of Connectivity", "Oxford University Press", "PUBLISHED_IN")],
     "whose 2013 comparative study surveyed five major social platforms under one connectivity framework",
     "Van Dijck Culture of Connectivity Oxford 2013 platform logics"),
    # --- 18 ---
    ("Eli Pariser's The Filter Bubble, published in 2011, popularised the filter-bubble critique of personalised news feeds and search results.", "reference", "knowledge", False,
     [("Eli Pariser", "person"), ("The Filter Bubble", "publication"), ("2011", "date"), ("filter-bubble critique", "concept"), ("personalised news feeds", "concept")],
     [("The Filter Bubble", "Eli Pariser", "AUTHORED_BY")],
     "whose 2011 volume coined the popular critique of algorithmically tailored online content",
     "Pariser Filter Bubble 2011 personalisation algorithmic"),
    # --- 19 ---
    ("Axel Bruns's Are Filter Bubbles Real, published by Polity in 2019, improves on the filter-bubble thesis by marshalling empirical audience data against the strong version of the claim.", "reference", "knowledge", False,
     [("Axel Bruns", "person"), ("Are Filter Bubbles Real", "publication"), ("Polity", "organization"), ("2019", "date"), ("filter-bubble thesis", "concept")],
     [("Are Filter Bubbles Real", "Axel Bruns", "AUTHORED_BY"), ("Are Filter Bubbles Real", "Polity", "PUBLISHED_IN"), ("Are Filter Bubbles Real", "filter-bubble thesis", "IMPROVES_ON")],
     "whose 2019 Polity book empirically pushed back on the strong filter-bubble thesis",
     "Bruns Filter Bubbles Real Polity 2019 empirical pushback"),
    # --- 20 ---
    ("Nick Diakopoulos's Automating the News, published by Harvard University Press in 2019, surveys computational journalism practices from algorithmic accountability to automated content production.", "reference", "knowledge", False,
     [("Nick Diakopoulos", "person"), ("Automating the News", "publication"), ("Harvard University Press", "organization"), ("2019", "date"), ("computational journalism", "field"), ("algorithmic accountability", "concept")],
     [("Automating the News", "Nick Diakopoulos", "AUTHORED_BY"), ("Automating the News", "Harvard University Press", "PUBLISHED_IN")],
     "whose 2019 monograph mapped the span of algorithmic newsroom practices from oversight to production",
     "Diakopoulos Automating the News Harvard 2019 computational"),
    # --- 21 ---
    ("C. W. Anderson, Emily Bell, and Clay Shirky's Post-Industrial Journalism, released by the Tow Center in 2012, argued for rebuilding US newsrooms around networked, data-driven workflows.", "decision", "knowledge", False,
     [("C. W. Anderson", "person"), ("Emily Bell", "person"), ("Clay Shirky", "person"), ("Post-Industrial Journalism", "publication"), ("Tow Center", "organization"), ("2012", "date")],
     [("Post-Industrial Journalism", "C. W. Anderson", "AUTHORED_BY"), ("Post-Industrial Journalism", "Emily Bell", "AUTHORED_BY"), ("Post-Industrial Journalism", "Clay Shirky", "AUTHORED_BY"), ("Post-Industrial Journalism", "Tow Center", "PUBLISHED_IN")],
     "which 2012 Tow Center report urged rebuilding newsrooms around networked data workflows",
     "Anderson Bell Shirky Post Industrial Journalism Tow 2012"),
    # --- 22 ---
    ("The Data Journalism Handbook, first published by O'Reilly in 2012 under the European Journalism Centre, codified shared methods for spreadsheet-driven and open-data reporting across the data journalism community.", "reference", "knowledge", False,
     [("The Data Journalism Handbook", "publication"), ("O'Reilly", "organization"), ("2012", "date"), ("European Journalism Centre", "organization"), ("data journalism", "field")],
     [("The Data Journalism Handbook", "O'Reilly", "PUBLISHED_IN"), ("The Data Journalism Handbook", "European Journalism Centre", "AUTHORED_BY")],
     "which 2012 O'Reilly handbook codified practices for data journalism",
     "Data Journalism Handbook O'Reilly 2012 EJC open data"),
    # --- 23 ---
    ("Lucas Graves's Deciding What's True, published by Columbia University Press in 2016, is the key ethnographic study of the US fact-checking movement and its verification methodology.", "reference", "knowledge", False,
     [("Lucas Graves", "person"), ("Deciding What's True", "publication"), ("Columbia University Press", "organization"), ("2016", "date"), ("fact-checking movement", "field"), ("verification methodology", "method")],
     [("Deciding What's True", "Lucas Graves", "AUTHORED_BY"), ("Deciding What's True", "Columbia University Press", "PUBLISHED_IN")],
     "which 2016 Columbia book ethnographically studied the US fact-checking movement",
     "Graves Deciding What's True Columbia 2016 fact checking"),
    # --- 24 ---
    ("The International Fact-Checking Network's 2016 Code of Principles, hosted by the Poynter Institute, standardised transparency criteria for signatory fact-checking organisations.", "milestone", "knowledge", False,
     [("International Fact-Checking Network", "organization"), ("Code of Principles", "publication"), ("2016", "date"), ("Poynter Institute", "organization"), ("transparency criteria", "concept")],
     [("Code of Principles", "International Fact-Checking Network", "AUTHORED_BY"), ("International Fact-Checking Network", "Poynter Institute", "PUBLISHED_IN")],
     "which 2016 Poynter-hosted code standardised transparency for fact-checking signatories",
     "IFCN Code of Principles Poynter 2016 fact checking transparency"),
    # --- 25 ---
    ("Columbia Journalism Review, founded at Columbia University in 1961, remains the dominant US trade journal for reflective coverage of American journalism practice.", "reference", "knowledge", False,
     [("Columbia Journalism Review", "publication"), ("Columbia University", "organization"), ("1961", "date"), ("American journalism practice", "field")],
     [("Columbia Journalism Review", "Columbia University", "PUBLISHED_IN")],
     "which 1961 Columbia-hosted magazine is the main US trade journal of record on journalism",
     "CJR Columbia Journalism Review 1961 trade magazine"),
    # --- 26 ---
    ("Journalism Studies, the Routledge journal launched in 2000 under founding editor Bob Franklin, became the flagship European venue for empirical journalism research.", "reference", "knowledge", False,
     [("Journalism Studies", "publication"), ("Routledge", "organization"), ("2000", "date"), ("Bob Franklin", "person"), ("empirical journalism research", "field")],
     [("Journalism Studies", "Routledge", "PUBLISHED_IN"), ("Journalism Studies", "Bob Franklin", "AUTHORED_BY")],
     "which 2000 Routledge journal became the European flagship for empirical journalism research",
     "Journalism Studies Routledge 2000 Franklin journal founding"),
    # --- 27 ---
    ("New Media & Society, a Sage journal founded in 1999, anchors much of the empirical literature on digital-media and platform journalism research.", "reference", "knowledge", False,
     [("New Media & Society", "publication"), ("Sage", "organization"), ("1999", "date"), ("platform journalism research", "field")],
     [("New Media & Society", "Sage", "PUBLISHED_IN")],
     "which late-1990s Sage periodical became a core venue for empirical platform-era scholarship",
     "New Media Society Sage 1999 journal digital"),
    # --- 28 ---
    ("The 2016 Pulitzer Prize for Public Service was awarded to the Associated Press for its Seafood from Slaves investigation, a touchstone reference case for accountability reporting.", "reference", "knowledge", False,
     [("2016 Pulitzer Prize for Public Service", "event"), ("Associated Press", "organization"), ("Seafood from Slaves", "publication"), ("accountability reporting", "field")],
     [("Seafood from Slaves", "Associated Press", "AUTHORED_BY"), ("2016 Pulitzer Prize for Public Service", "Seafood from Slaves", "BUILDS_ON")],
     "which 2016 Pulitzer Public Service winner is cited as a canonical accountability reporting case",
     "Pulitzer 2016 Public Service AP Seafood Slaves accountability"),
    # --- 29 ---
    ("The 2017 Pulitzer Prize for Explanatory Reporting, shared by the International Consortium of Investigative Journalists, Sueddeutsche Zeitung, and McClatchy for the Panama Papers, canonised cross-border collaborative investigation.", "milestone", "knowledge", False,
     [("2017 Pulitzer Prize for Explanatory Reporting", "event"), ("International Consortium of Investigative Journalists", "organization"), ("Sueddeutsche Zeitung", "organization"), ("McClatchy", "organization"), ("Panama Papers", "publication"), ("cross-border collaborative investigation", "method")],
     [("Panama Papers", "International Consortium of Investigative Journalists", "AUTHORED_BY"), ("Panama Papers", "Sueddeutsche Zeitung", "AUTHORED_BY"), ("Panama Papers", "McClatchy", "AUTHORED_BY"), ("2017 Pulitzer Prize for Explanatory Reporting", "Panama Papers", "BUILDS_ON")],
     "which 2017 Pulitzer Explanatory winner canonised cross-border collaborative investigation",
     "Pulitzer 2017 Explanatory ICIJ Panama Papers SZ McClatchy"),
    # --- 30 ---
    ("The 2003 Pulitzer Prize for Public Service went to The Boston Globe for its Spotlight team's investigation into Catholic clergy abuse, a foundational reference for systemic investigative reporting.", "reference", "knowledge", False,
     [("2003 Pulitzer Prize for Public Service", "event"), ("The Boston Globe", "organization"), ("Spotlight team", "organization"), ("Catholic clergy abuse", "concept"), ("systemic investigative reporting", "field")],
     [("2003 Pulitzer Prize for Public Service", "The Boston Globe", "AUTHORED_BY")],
     "which 2003 Pulitzer Public Service winner investigated Catholic clergy abuse",
     "Pulitzer 2003 Boston Globe Spotlight clergy investigative"),
    # --- 31 ---
    ("Herbert Gans's Deciding What's News, published by Vintage in 1979, remains the canonical newsroom ethnography of CBS, NBC, Newsweek, and Time.", "reference", "knowledge", False,
     [("Herbert Gans", "person"), ("Deciding What's News", "publication"), ("Vintage", "organization"), ("1979", "date"), ("CBS", "organization"), ("NBC", "organization"), ("Newsweek", "organization")],
     [("Deciding What's News", "Herbert Gans", "AUTHORED_BY"), ("Deciding What's News", "Vintage", "PUBLISHED_IN")],
     "which 1979 ethnography observed CBS, NBC, Newsweek, and Time newsrooms together",
     "Gans Deciding What's News 1979 CBS NBC newsroom ethnography"),
    # --- 32 ---
    ("Gaye Tuchman's Making News, published by Free Press in 1978, argued that journalistic routines and objectivity rituals systematically shape news as a constructed reality.", "reference", "knowledge", False,
     [("Gaye Tuchman", "person"), ("Making News", "publication"), ("Free Press", "organization"), ("1978", "date"), ("journalistic routines", "concept"), ("objectivity rituals", "concept")],
     [("Making News", "Gaye Tuchman", "AUTHORED_BY"), ("Making News", "Free Press", "PUBLISHED_IN")],
     "whose 1978 book framed news as constructed reality through routines and objectivity rituals",
     "Tuchman Making News 1978 objectivity ritual routines construction"),
    # --- 33 ---
    ("Michael Schudson's Discovering the News, published by Basic Books in 1978, historicised American objectivity as a twentieth-century professional norm rather than a timeless commitment.", "reference", "knowledge", False,
     [("Michael Schudson", "person"), ("Discovering the News", "publication"), ("Basic Books", "organization"), ("1978", "date"), ("American objectivity", "concept")],
     [("Discovering the News", "Michael Schudson", "AUTHORED_BY"), ("Discovering the News", "Basic Books", "PUBLISHED_IN")],
     "which 1978 book historicised American objectivity as a professional norm of the twentieth century",
     "Schudson Discovering the News 1978 objectivity history"),
    # --- 34. noise ---
    ("Hmm, I should verify whether that citation points to the 1983 Journal of Communication ferment issue or the later symposium.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Barbie Zelizer's Taking Journalism Seriously, published by Sage in 2004, improves on earlier single-discipline surveys by mapping journalism scholarship across sociology, history, and cultural studies simultaneously.", "reference", "knowledge", False,
     [("Barbie Zelizer", "person"), ("Taking Journalism Seriously", "publication"), ("Sage", "organization"), ("2004", "date"), ("journalism scholarship", "field"), ("single-discipline surveys", "concept")],
     [("Taking Journalism Seriously", "Barbie Zelizer", "AUTHORED_BY"), ("Taking Journalism Seriously", "Sage", "PUBLISHED_IN"), ("Taking Journalism Seriously", "single-discipline surveys", "IMPROVES_ON")],
     "whose 2004 Sage book surveyed journalism studies across sociology, history, and cultural studies together",
     "Zelizer Taking Journalism Seriously Sage 2004 interdisciplinary"),
    # --- 36 ---
    ("Daniel Hallin and Paolo Mancini's Comparing Media Systems, published by Cambridge University Press in 2004, proposed three models of media and politics across eighteen Western democracies.", "reference", "knowledge", False,
     [("Daniel Hallin", "person"), ("Paolo Mancini", "person"), ("Comparing Media Systems", "publication"), ("Cambridge University Press", "organization"), ("2004", "date"), ("three models of media and politics", "framework")],
     [("Comparing Media Systems", "Daniel Hallin", "AUTHORED_BY"), ("Comparing Media Systems", "Paolo Mancini", "AUTHORED_BY"), ("Comparing Media Systems", "Cambridge University Press", "PUBLISHED_IN")],
     "which 2004 Cambridge book proposed three models of media and politics across Western democracies",
     "Hallin Mancini Comparing Media Systems 2004 three models"),
    # --- 37 ---
    ("Manuel Castells's Communication Power, published by Oxford University Press in 2009, frames mass self-communication as the organising concept of networked politics.", "reference", "knowledge", False,
     [("Manuel Castells", "person"), ("Communication Power", "publication"), ("Oxford University Press", "organization"), ("2009", "date"), ("mass self-communication", "concept"), ("networked politics", "field")],
     [("Communication Power", "Manuel Castells", "AUTHORED_BY"), ("Communication Power", "Oxford University Press", "PUBLISHED_IN")],
     "which 2009 Oxford book formalised mass self-communication as a category for networked politics",
     "Castells Communication Power Oxford 2009 mass self communication"),
    # --- 38 ---
    ("W. Lance Bennett's indexing hypothesis, first articulated in a 1990 Journal of Communication article, claims US news frames largely index the range of elite debate.", "reference", "knowledge", False,
     [("W. Lance Bennett", "person"), ("indexing hypothesis", "theory"), ("1990", "date"), ("Journal of Communication", "publication"), ("elite debate", "concept")],
     [("indexing hypothesis", "W. Lance Bennett", "AUTHORED_BY"), ("indexing hypothesis", "Journal of Communication", "PUBLISHED_IN")],
     "whose 1990 Journal of Communication article proposed that US news indexes elite debate",
     "Bennett indexing hypothesis 1990 Journal of Communication elites"),
    # --- 39 ---
    ("Dietram Scheufele's 1999 framing-as-process model, also in Journal of Communication, improves on Entman's original framing synthesis by distinguishing frame-building from frame-setting at the audience level.", "reference", "knowledge", False,
     [("Dietram Scheufele", "person"), ("framing-as-process model", "theory"), ("1999", "date"), ("Journal of Communication", "publication"), ("frame-building", "concept"), ("frame-setting", "concept"), ("Entman's original framing synthesis", "theory")],
     [("framing-as-process model", "Dietram Scheufele", "AUTHORED_BY"), ("framing-as-process model", "Entman's original framing synthesis", "IMPROVES_ON")],
     "whose 1999 JoC article distinguished frame-building from frame-setting as stages in framing research",
     "Scheufele framing process 1999 JoC frame building setting"),
    # --- 40 ---
    ("Mark Deuze's Media Work, published by Polity in 2007, reframes journalists as one occupational species within a broader media-industries labour force.", "reference", "knowledge", False,
     [("Mark Deuze", "person"), ("Media Work", "publication"), ("Polity", "organization"), ("2007", "date"), ("media-industries labour force", "concept")],
     [("Media Work", "Mark Deuze", "AUTHORED_BY"), ("Media Work", "Polity", "PUBLISHED_IN")],
     "whose 2007 monograph redescribed reporters as one occupational slice of a wider creative workforce",
     "Deuze Media Work Polity 2007 occupational labour"),
    # --- 41 ---
    ("Thomas Patterson's Informing the News, published by Vintage in 2013, argues that knowledge-based journalism should replace the objectivity-plus-balance default of US political reporting.", "decision", "knowledge", False,
     [("Thomas Patterson", "person"), ("Informing the News", "publication"), ("Vintage", "organization"), ("2013", "date"), ("knowledge-based journalism", "concept"), ("objectivity-plus-balance", "concept")],
     [("Informing the News", "Thomas Patterson", "AUTHORED_BY"), ("Informing the News", "Vintage", "PUBLISHED_IN"), ("knowledge-based journalism", "objectivity-plus-balance", "REPLACES")],
     "which 2013 book argued that knowledge-based journalism should supplant objectivity-plus-balance",
     "Patterson Informing the News 2013 knowledge based objectivity"),
    # --- 42 ---
    ("The Reuters Institute Digital News Report, published annually by the Reuters Institute for the Study of Journalism at Oxford since 2012, is the principal cross-country reference on digital news consumption.", "reference", "knowledge", False,
     [("Reuters Institute Digital News Report", "publication"), ("Reuters Institute for the Study of Journalism", "organization"), ("Oxford", "place"), ("2012", "date"), ("digital news consumption", "finding")],
     [("Reuters Institute Digital News Report", "Reuters Institute for the Study of Journalism", "AUTHORED_BY"), ("Reuters Institute for the Study of Journalism", "Oxford", "PUBLISHED_IN")],
     "which annual Oxford-based report is the main cross-country reference on digital news consumption since 2012",
     "Reuters Institute Digital News Report Oxford 2012 survey"),
    # --- 43 ---
    ("Wolfgang Donsbach's presidential address in the 2008 Journalism journal prefers a role-centred definition of journalism over the market-centred alternative.", "preference", "knowledge", False,
     [("Wolfgang Donsbach", "person"), ("Journalism", "publication"), ("2008", "date"), ("role-centred definition of journalism", "concept"), ("market-centred alternative", "concept")],
     [("role-centred definition of journalism", "market-centred alternative", "PREFERS")],
     "whose 2008 Journalism presidential address preferred role-centred over market-centred definitions of journalism",
     "Donsbach Journalism 2008 presidential address role market"),
    # --- 44 ---
    ("Silvio Waisbord's Reinventing Professionalism, published by Polity in 2013, diagnoses a global crisis of journalistic professionalism as news systems diverge from the US-centric model.", "problem", "knowledge", False,
     [("Silvio Waisbord", "person"), ("Reinventing Professionalism", "publication"), ("Polity", "organization"), ("2013", "date"), ("journalistic professionalism", "concept"), ("US-centric model", "concept")],
     [("Reinventing Professionalism", "Silvio Waisbord", "AUTHORED_BY"), ("Reinventing Professionalism", "Polity", "PUBLISHED_IN")],
     "whose 2013 survey argued that reporter professionalism is fracturing worldwide as systems drift from the American template",
     "Waisbord Reinventing Professionalism Polity 2013 global crisis"),
    # --- 45 ---
    ("Rodney Benson and Erik Neveu's Bourdieu and the Journalistic Field, published by Polity in 2005, adapts field theory to news production and replaces simpler newsroom-sociology accounts.", "reference", "knowledge", False,
     [("Rodney Benson", "person"), ("Erik Neveu", "person"), ("Bourdieu and the Journalistic Field", "publication"), ("Polity", "organization"), ("2005", "date"), ("field theory", "theory"), ("newsroom-sociology accounts", "concept")],
     [("Bourdieu and the Journalistic Field", "Rodney Benson", "AUTHORED_BY"), ("Bourdieu and the Journalistic Field", "Erik Neveu", "AUTHORED_BY"), ("Bourdieu and the Journalistic Field", "Polity", "PUBLISHED_IN"), ("field theory", "newsroom-sociology accounts", "REPLACES")],
     "which 2005 Polity volume adapted field theory to journalism, moving beyond simpler newsroom sociology",
     "Benson Neveu Bourdieu Journalistic Field Polity 2005"),
    # --- 46 ---
    ("Philip Napoli's Social Media and the Public Interest, published by Columbia University Press in 2019, argues that platform companies should be regulated as media institutions rather than neutral intermediaries.", "decision", "knowledge", False,
     [("Philip Napoli", "person"), ("Social Media and the Public Interest", "publication"), ("Columbia University Press", "organization"), ("2019", "date"), ("platform companies", "concept"), ("neutral intermediaries", "concept")],
     [("Social Media and the Public Interest", "Philip Napoli", "AUTHORED_BY"), ("Social Media and the Public Interest", "Columbia University Press", "PUBLISHED_IN"), ("platform companies", "neutral intermediaries", "REPLACES")],
     "which 2019 Columbia book argued that platforms should be regulated as media institutions, not neutral intermediaries",
     "Napoli Social Media Public Interest Columbia 2019 regulation"),
    # --- 47 ---
    ("Matthew Powers's NGOs as Newsmakers, published by Columbia University Press in 2018, documents how humanitarian organisations have replaced some traditional foreign-correspondent roles.", "reference", "knowledge", False,
     [("Matthew Powers", "person"), ("NGOs as Newsmakers", "publication"), ("Columbia University Press", "organization"), ("2018", "date"), ("humanitarian organisations", "organization"), ("foreign-correspondent roles", "concept")],
     [("NGOs as Newsmakers", "Matthew Powers", "AUTHORED_BY"), ("NGOs as Newsmakers", "Columbia University Press", "PUBLISHED_IN"), ("humanitarian organisations", "foreign-correspondent roles", "REPLACES")],
     "which 2018 Columbia book documents NGOs partially replacing foreign correspondents as newsmakers",
     "Powers NGOs as Newsmakers Columbia 2018 humanitarian"),
    # --- 48 ---
    ("Rasmus Kleis Nielsen and Meera Selva's 2019 Reuters Institute report on media capture consolidates evidence that ownership concentration erodes editorial autonomy in several democracies.", "reference", "knowledge", False,
     [("Rasmus Kleis Nielsen", "person"), ("Meera Selva", "person"), ("Reuters Institute", "organization"), ("2019", "date"), ("media capture", "concept"), ("editorial autonomy", "finding")],
     [("Reuters Institute", "Rasmus Kleis Nielsen", "AUTHORED_BY"), ("Reuters Institute", "Meera Selva", "AUTHORED_BY")],
     "which 2019 Reuters Institute report consolidated evidence on media capture and editorial autonomy",
     "Nielsen Selva Reuters Institute 2019 media capture"),
    # --- 49 ---
    ("Caroline Fisher's 2016 Journalism Studies article prefers a principled-distance framing of source relations over the classic objectivity-as-detachment stance.", "preference", "knowledge", False,
     [("Caroline Fisher", "person"), ("Journalism Studies", "publication"), ("2016", "date"), ("principled-distance framing", "concept"), ("objectivity-as-detachment", "concept")],
     [("principled-distance framing", "objectivity-as-detachment", "PREFERS")],
     "whose 2016 paper argued against classical detachment in favour of a normatively calibrated stance on sources",
     "Fisher Journalism Studies 2016 principled distance sources"),
    # --- 50 ---
    ("Tamar Liebes and Elihu Katz's The Export of Meaning, published by Oxford University Press in 1990, improves on single-nation encoding/decoding studies by tracing cross-cultural Dallas reception across six audiences.", "reference", "knowledge", False,
     [("Tamar Liebes", "person"), ("Elihu Katz", "person"), ("The Export of Meaning", "publication"), ("Oxford University Press", "organization"), ("1990", "date"), ("Dallas", "publication"), ("single-nation encoding/decoding studies", "concept")],
     [("The Export of Meaning", "Tamar Liebes", "AUTHORED_BY"), ("The Export of Meaning", "Elihu Katz", "AUTHORED_BY"), ("The Export of Meaning", "Oxford University Press", "PUBLISHED_IN"), ("The Export of Meaning", "single-nation encoding/decoding studies", "IMPROVES_ON")],
     "which 1990 Oxford book extended encoding/decoding research through cross-cultural Dallas reception",
     "Liebes Katz Export of Meaning Oxford 1990 Dallas cross cultural"),
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
