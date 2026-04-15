"""One-off emitter for shared-base batch-093 — knowledge domain (law and jurisprudence as a research/academic field).

Writes 50 rows with ids shared-04601..04650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_093.tmp.jsonl"
ID_OFFSET = 4600

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("H. L. A. Hart's The Concept of Law, published in 1961, recast legal positivism around the union of primary and secondary rules anchored by a rule of recognition.", "reference", "knowledge", False,
     [("H. L. A. Hart", "person"), ("The Concept of Law", "publication"), ("1961", "date"), ("legal positivism", "theory"), ("rule of recognition", "concept")],
     [("The Concept of Law", "H. L. A. Hart", "AUTHORED_BY"), ("The Concept of Law", "legal positivism", "BUILDS_ON")],
     "which 1961 jurisprudential book reframed positivism around primary and secondary rules",
     "Hart Concept Law rule recognition positivism primary secondary year"),
    # --- 2 ---
    ("Ronald Dworkin's Law's Empire of 1986 argues for law as integrity and positions judicial interpretation as a constructive enterprise that improves on Hartian positivism.", "reference", "knowledge", False,
     [("Ronald Dworkin", "person"), ("Law's Empire", "publication"), ("1986", "date"), ("law as integrity", "theory"), ("Hartian positivism", "theory")],
     [("Law's Empire", "Ronald Dworkin", "AUTHORED_BY"), ("law as integrity", "Hartian positivism", "IMPROVES_ON")],
     "which 1986 Dworkin book frames law as integrity against Hartian positivism",
     "Dworkin Law Empire integrity interpretive positivism critique year"),
    # --- 3 ---
    ("Joseph Raz's The Authority of Law, published in 1979, defends an exclusive positivism in which legal authority depends on a service conception of practical reasons.", "reference", "knowledge", False,
     [("Joseph Raz", "person"), ("The Authority of Law", "publication"), ("1979", "date"), ("exclusive positivism", "theory"), ("service conception", "concept")],
     [("The Authority of Law", "Joseph Raz", "AUTHORED_BY")],
     "which 1979 book grounds exclusive positivism in a service conception of authority",
     "Raz authority law exclusive positivism service reasons year"),
    # --- 4 ---
    ("John Finnis's Natural Law and Natural Rights, published in 1980, revived classical natural-law theory by grounding legal obligation in seven basic goods of human flourishing.", "reference", "knowledge", False,
     [("John Finnis", "person"), ("Natural Law and Natural Rights", "publication"), ("1980", "date"), ("natural-law theory", "theory"), ("basic goods", "concept")],
     [("Natural Law and Natural Rights", "John Finnis", "AUTHORED_BY"), ("Natural Law and Natural Rights", "natural-law theory", "BUILDS_ON")],
     "which 1980 book rebuilt natural-law theory around seven basic human goods",
     "Finnis natural law rights basic goods flourishing year"),
    # --- 5 ---
    ("Lon Fuller's The Morality of Law, published in 1964, lists eight procedural desiderata of legality that form an inner morality of law and challenge strict positivism.", "reference", "knowledge", False,
     [("Lon Fuller", "person"), ("The Morality of Law", "publication"), ("1964", "date"), ("inner morality of law", "concept"), ("strict positivism", "theory")],
     [("The Morality of Law", "Lon Fuller", "AUTHORED_BY"), ("inner morality of law", "strict positivism", "CONTRADICTS")],
     "which 1964 book lists eight procedural desiderata as the inner morality of law",
     "Fuller morality law eight desiderata inner procedural year"),
    # --- 6 ---
    ("The Hart-Fuller debate of 1958 in the Harvard Law Review crystallised the mid-century clash between legal positivism and natural-law theory around Nazi grudge informer cases.", "milestone", "knowledge", False,
     [("Hart-Fuller debate", "event"), ("1958", "date"), ("Harvard Law Review", "publication"), ("grudge informer cases", "concept"), ("natural-law theory", "theory")],
     [("Hart-Fuller debate", "Harvard Law Review", "PUBLISHED_IN")],
     "which 1958 exchange in a flagship American journal staged positivism against natural law",
     "Hart Fuller Harvard debate grudge informer positivism natural law year"),
    # --- 7 ---
    ("Hans Kelsen's Pure Theory of Law, definitively issued in 1960, founds a hierarchy of norms on a hypothetical Grundnorm that validates the entire legal order.", "reference", "knowledge", False,
     [("Hans Kelsen", "person"), ("Pure Theory of Law", "publication"), ("1960", "date"), ("Grundnorm", "concept"), ("hierarchy of norms", "concept")],
     [("Pure Theory of Law", "Hans Kelsen", "AUTHORED_BY")],
     "whose 1960 pure theory anchors the legal order in a presupposed Grundnorm",
     "Kelsen pure theory law Grundnorm Stufenbau hierarchy year"),
    # --- 8 ---
    ("Oliver Wendell Holmes's essay The Path of the Law, published in 1897 in the Harvard Law Review, launched American legal realism by defining law as predictions of what courts will do.", "milestone", "knowledge", False,
     [("Oliver Wendell Holmes", "person"), ("The Path of the Law", "publication"), ("1897", "date"), ("Harvard Law Review", "publication"), ("American legal realism", "theory")],
     [("The Path of the Law", "Oliver Wendell Holmes", "AUTHORED_BY"), ("The Path of the Law", "Harvard Law Review", "PUBLISHED_IN")],
     "which 1897 Holmes essay seeded American legal realism around the prediction theory",
     "Holmes path law prediction theory bad man realism year"),
    # --- 9 ---
    ("American legal realism in the 1920s and 1930s improves on classical Langdellian formalism by treating judicial decisions as driven by policy and social fact rather than logical deduction.", "reference", "knowledge", False,
     [("American legal realism", "theory"), ("1920s", "date"), ("1930s", "date"), ("Langdellian formalism", "theory")],
     [("American legal realism", "Langdellian formalism", "IMPROVES_ON")],
     "which interwar movement displaced Langdellian formalism with policy-driven decision analysis",
     "legal realism Langdell formalism interwar policy decision critique"),
    # --- 10. noise ---
    ("Give me a moment, I want to cross-check that citation against the official reporter before quoting it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Karl Llewellyn's The Bramble Bush of 1930 packaged American legal realism as a working method for law students and reframed common-law reasoning as situation-sense.", "reference", "knowledge", False,
     [("Karl Llewellyn", "person"), ("The Bramble Bush", "publication"), ("1930", "date"), ("American legal realism", "theory"), ("situation-sense", "concept")],
     [("The Bramble Bush", "Karl Llewellyn", "AUTHORED_BY")],
     "which 1930 lecture series popularised American realism as a student method",
     "Llewellyn Bramble Bush realism situation sense lectures year"),
    # --- 12 ---
    ("Critical Legal Studies, consolidated at the 1977 Conference on Critical Legal Studies, pushed back against liberal legalism by arguing that legal doctrine encodes political hierarchy.", "milestone", "knowledge", False,
     [("Critical Legal Studies", "theory"), ("Conference on Critical Legal Studies", "event"), ("1977", "date"), ("liberal legalism", "theory")],
     [("Critical Legal Studies", "liberal legalism", "CONTRADICTS")],
     "which late-1970s American movement attacked liberal legalism as cover for political hierarchy",
     "Critical Legal Studies CLS 1977 conference liberal legalism hierarchy"),
    # --- 13 ---
    ("Duncan Kennedy's article Form and Substance in Private Law Adjudication, published in the 1976 Harvard Law Review, is a foundational text of Critical Legal Studies.", "reference", "knowledge", False,
     [("Duncan Kennedy", "person"), ("Form and Substance in Private Law Adjudication", "publication"), ("1976", "date"), ("Harvard Law Review", "publication"), ("Critical Legal Studies", "theory")],
     [("Form and Substance in Private Law Adjudication", "Duncan Kennedy", "AUTHORED_BY"), ("Form and Substance in Private Law Adjudication", "Harvard Law Review", "PUBLISHED_IN")],
     "which 1976 Duncan Kennedy article seeded Critical Legal Studies in a flagship American journal",
     "Kennedy form substance private law adjudication Harvard 1976 CLS"),
    # --- 14 ---
    ("Feminist jurisprudence, crystallised by Catharine MacKinnon's Feminism Unmodified of 1987, reframes sex equality doctrine around dominance theory rather than formal sameness.", "reference", "knowledge", False,
     [("Feminist jurisprudence", "theory"), ("Catharine MacKinnon", "person"), ("Feminism Unmodified", "publication"), ("1987", "date"), ("dominance theory", "theory"), ("formal sameness", "theory")],
     [("Feminism Unmodified", "Catharine MacKinnon", "AUTHORED_BY"), ("dominance theory", "formal sameness", "REPLACES")],
     "which 1987 MacKinnon collection reoriented feminist jurisprudence around dominance theory",
     "MacKinnon Feminism Unmodified dominance sameness feminist jurisprudence year"),
    # --- 15 ---
    ("Kimberle Crenshaw's 1989 University of Chicago Legal Forum article coined intersectionality as an analytic frame within critical race theory.", "milestone", "knowledge", False,
     [("Kimberle Crenshaw", "person"), ("1989", "date"), ("University of Chicago Legal Forum", "publication"), ("intersectionality", "concept"), ("critical race theory", "theory")],
     [("intersectionality", "Kimberle Crenshaw", "AUTHORED_BY"), ("intersectionality", "University of Chicago Legal Forum", "PUBLISHED_IN")],
     "whose 1989 law-review article introduced intersectionality into critical race theory",
     "Crenshaw intersectionality Chicago Legal Forum critical race year"),
    # --- 16 ---
    ("Richard Posner's Economic Analysis of Law, first published in 1973, became the canonical textbook of the law-and-economics movement associated with the University of Chicago.", "reference", "knowledge", False,
     [("Richard Posner", "person"), ("Economic Analysis of Law", "publication"), ("1973", "date"), ("law-and-economics", "field"), ("University of Chicago", "organization")],
     [("Economic Analysis of Law", "Richard Posner", "AUTHORED_BY")],
     "which 1973 textbook became the canonical entry point to law-and-economics",
     "Posner Economic Analysis Law Chicago school textbook year"),
    # --- 17 ---
    ("Ronald Coase's The Problem of Social Cost, published in 1960 in the Journal of Law and Economics, reframed externalities as reciprocal and launched modern law-and-economics.", "reference", "knowledge", False,
     [("Ronald Coase", "person"), ("The Problem of Social Cost", "publication"), ("1960", "date"), ("Journal of Law and Economics", "publication"), ("law-and-economics", "field")],
     [("The Problem of Social Cost", "Ronald Coase", "AUTHORED_BY"), ("The Problem of Social Cost", "Journal of Law and Economics", "PUBLISHED_IN")],
     "which 1960 Coase article reframed externalities and launched modern law-and-economics",
     "Coase social cost reciprocal externalities Journal Law Economics year"),
    # --- 18 ---
    ("Guido Calabresi and Douglas Melamed's article Property Rules, Liability Rules, and Inalienability, published in the 1972 Harvard Law Review, organises entitlements around protection regimes.", "reference", "knowledge", False,
     [("Guido Calabresi", "person"), ("Douglas Melamed", "person"), ("Property Rules, Liability Rules, and Inalienability", "publication"), ("1972", "date"), ("Harvard Law Review", "publication")],
     [("Property Rules, Liability Rules, and Inalienability", "Guido Calabresi", "AUTHORED_BY"), ("Property Rules, Liability Rules, and Inalienability", "Harvard Law Review", "PUBLISHED_IN")],
     "which 1972 Harvard article organised entitlements into property, liability, and inalienability regimes",
     "Calabresi Melamed entitlements cathedral Harvard 1972 property liability"),
    # --- 19 ---
    ("Marbury v Madison, decided by the United States Supreme Court in 1803 under Chief Justice John Marshall, established the doctrine of judicial review over federal legislation.", "reference", "knowledge", False,
     [("Marbury v Madison", "event"), ("United States Supreme Court", "organization"), ("1803", "date"), ("John Marshall", "person"), ("judicial review", "concept")],
     [("Marbury v Madison", "judicial review", "PRODUCES")],
     "which 1803 Marshall decision established federal judicial review in the United States",
     "Marbury Madison 1803 Marshall judicial review founding case"),
    # --- 20 ---
    ("Brown v Board of Education, decided in 1954 by the United States Supreme Court under Chief Justice Earl Warren, replaced the separate-but-equal doctrine of Plessy v Ferguson.", "milestone", "knowledge", False,
     [("Brown v Board of Education", "event"), ("1954", "date"), ("United States Supreme Court", "organization"), ("Earl Warren", "person"), ("Plessy v Ferguson", "event")],
     [("Brown v Board of Education", "Plessy v Ferguson", "REPLACES")],
     "which 1954 Warren Court decision overturned the separate-but-equal Plessy doctrine",
     "Brown Board Education 1954 Warren Plessy separate equal overruling"),
    # --- 21 ---
    ("Dobbs v Jackson Women's Health Organization, decided by the United States Supreme Court in 2022, replaced the abortion-rights framework of Roe v Wade and Planned Parenthood v Casey.", "milestone", "knowledge", False,
     [("Dobbs v Jackson Women's Health Organization", "event"), ("United States Supreme Court", "organization"), ("2022", "date"), ("Roe v Wade", "event"), ("Planned Parenthood v Casey", "event")],
     [("Dobbs v Jackson Women's Health Organization", "Roe v Wade", "REPLACES"), ("Dobbs v Jackson Women's Health Organization", "Planned Parenthood v Casey", "REPLACES")],
     "which 2022 United States Supreme Court decision overruled Roe and Casey on abortion rights",
     "Dobbs Jackson 2022 Roe Casey overruling abortion doctrine"),
    # --- 22 ---
    ("Donoghue v Stevenson, decided by the House of Lords in 1932, founded the modern tort of negligence by articulating Lord Atkin's neighbour principle.", "reference", "knowledge", False,
     [("Donoghue v Stevenson", "event"), ("House of Lords", "organization"), ("1932", "date"), ("tort of negligence", "concept"), ("neighbour principle", "concept")],
     [("Donoghue v Stevenson", "neighbour principle", "PRODUCES")],
     "which 1932 House of Lords decision installed the neighbour principle in the tort of negligence",
     "Donoghue Stevenson 1932 neighbour principle negligence snail ginger beer"),
    # --- 23 ---
    ("Originalism, defended in Antonin Scalia's A Matter of Interpretation of 1997, holds that constitutional meaning is fixed at ratification and improves on living-constitutionalist methods.", "reference", "knowledge", False,
     [("Originalism", "theory"), ("Antonin Scalia", "person"), ("A Matter of Interpretation", "publication"), ("1997", "date"), ("living-constitutionalist methods", "theory")],
     [("A Matter of Interpretation", "Antonin Scalia", "AUTHORED_BY"), ("Originalism", "living-constitutionalist methods", "IMPROVES_ON")],
     "which 1997 Scalia book defended originalism against living-constitutionalist methods",
     "Scalia Matter Interpretation originalism fixed meaning year"),
    # --- 24 ---
    ("Living constitutionalism, articulated in David Strauss's The Living Constitution of 2010, treats the document as a common-law tradition that adapts through precedent rather than fixed original meaning.", "reference", "knowledge", False,
     [("Living constitutionalism", "theory"), ("David Strauss", "person"), ("The Living Constitution", "publication"), ("2010", "date"), ("fixed original meaning", "concept")],
     [("The Living Constitution", "David Strauss", "AUTHORED_BY"), ("Living constitutionalism", "fixed original meaning", "CONTRADICTS")],
     "which 2010 Strauss book defends the living constitution as a common-law tradition",
     "Strauss living constitution common law adaptation year"),
    # --- 25 ---
    ("Bruce Ackerman's We the People series, beginning with Foundations in 1991, introduces dualist democracy and constitutional moments as a theory of American constitutional change.", "reference", "knowledge", False,
     [("Bruce Ackerman", "person"), ("We the People", "publication"), ("Foundations", "publication"), ("1991", "date"), ("dualist democracy", "theory"), ("constitutional moments", "concept")],
     [("We the People", "Bruce Ackerman", "AUTHORED_BY"), ("Foundations", "Bruce Ackerman", "AUTHORED_BY")],
     "which 1991 Ackerman volume introduced dualist democracy and constitutional moments",
     "Ackerman We People Foundations dualist democracy constitutional moments year"),
    # --- 26 ---
    ("The civil-law tradition, rooted in Justinian's Corpus Juris Civilis of 529 to 534 CE, still structures codified legal systems across continental Europe and Latin America.", "reference", "knowledge", False,
     [("civil-law tradition", "concept"), ("Justinian", "person"), ("Corpus Juris Civilis", "publication"), ("529 to 534 CE", "date"), ("continental Europe", "place"), ("Latin America", "place")],
     [("civil-law tradition", "Corpus Juris Civilis", "BUILDS_ON")],
     "which sixth-century compilation anchors the civil-law tradition across continental Europe",
     "Justinian Corpus Juris Civilis civil law codified Europe sixth century"),
    # --- 27 ---
    ("The common-law tradition, traced through Bracton's thirteenth-century treatise On the Laws and Customs of England, organises law around judicial precedent rather than comprehensive codification.", "reference", "knowledge", False,
     [("common-law tradition", "concept"), ("Bracton", "person"), ("On the Laws and Customs of England", "publication"), ("judicial precedent", "concept"), ("comprehensive codification", "concept")],
     [("On the Laws and Customs of England", "Bracton", "AUTHORED_BY"), ("judicial precedent", "comprehensive codification", "PREFERS")],
     "which thirteenth-century English treatise anchors the common-law tradition of precedent",
     "Bracton England customs common law precedent codification tradition"),
    # --- 28 ---
    ("Comparative law as an academic discipline was institutionalised by the 1900 Paris Congress of Comparative Law organised by Raymond Saleilles and Edouard Lambert.", "milestone", "knowledge", False,
     [("Comparative law", "field"), ("Paris Congress of Comparative Law", "event"), ("1900", "date"), ("Raymond Saleilles", "person"), ("Edouard Lambert", "person")],
     [("Comparative law", "Paris Congress of Comparative Law", "BUILDS_ON")],
     "which 1900 Paris congress institutionalised comparative law as an academic discipline",
     "Paris 1900 congress comparative law Saleilles Lambert founding"),
    # --- 29 ---
    ("Konrad Zweigert and Hein Koetz's Introduction to Comparative Law, revised in 1998, organises legal families through the methodology of functional equivalents.", "reference", "knowledge", False,
     [("Konrad Zweigert", "person"), ("Hein Koetz", "person"), ("Introduction to Comparative Law", "publication"), ("1998", "date"), ("functional equivalents", "method")],
     [("Introduction to Comparative Law", "Konrad Zweigert", "AUTHORED_BY")],
     "which 1998 German textbook organises comparative law around functional equivalents",
     "Zweigert Koetz Introduction Comparative Law functional equivalents year"),
    # --- 30 ---
    ("The Vienna Convention on the Law of Treaties, concluded in 1969 and in force from 1980, codified treaty interpretation and replaced the prior patchwork of customary ad-hoc rules.", "milestone", "knowledge", False,
     [("Vienna Convention on the Law of Treaties", "publication"), ("1969", "date"), ("1980", "date"), ("treaty interpretation", "concept"), ("customary ad-hoc rules", "concept")],
     [("Vienna Convention on the Law of Treaties", "customary ad-hoc rules", "REPLACES")],
     "which 1969 convention codified treaty interpretation and replaced earlier ad-hoc practice",
     "Vienna Convention Treaties 1969 1980 interpretation codification"),
    # --- 31 ---
    ("The Rome Statute of 1998 established the International Criminal Court at The Hague with jurisdiction over genocide, crimes against humanity, war crimes, and aggression.", "milestone", "knowledge", False,
     [("Rome Statute", "publication"), ("1998", "date"), ("International Criminal Court", "organization"), ("The Hague", "place"), ("genocide", "concept"), ("war crimes", "concept")],
     [("International Criminal Court", "Rome Statute", "BUILDS_ON")],
     "which 1998 statute founded the International Criminal Court at The Hague",
     "Rome Statute ICC Hague genocide war crimes aggression year"),
    # --- 32 ---
    ("The International Court of Justice, seated in the Peace Palace at The Hague since 1946, delivered the landmark Nicaragua v United States judgment on the prohibition of force in 1986.", "reference", "knowledge", False,
     [("International Court of Justice", "organization"), ("Peace Palace", "place"), ("The Hague", "place"), ("1946", "date"), ("Nicaragua v United States", "event"), ("1986", "date")],
     [("International Court of Justice", "The Hague", "LOCATED_IN")],
     "which 1986 International Court of Justice judgment anchored the law on the use of force",
     "ICJ Peace Palace Hague Nicaragua United States force 1986"),
    # --- 33 ---
    ("The European Convention on Human Rights, concluded in Rome in 1950, is adjudicated by the European Court of Human Rights in Strasbourg.", "reference", "knowledge", False,
     [("European Convention on Human Rights", "publication"), ("Rome", "place"), ("1950", "date"), ("European Court of Human Rights", "organization"), ("Strasbourg", "place")],
     [("European Court of Human Rights", "European Convention on Human Rights", "APPLIES_TO"), ("European Court of Human Rights", "Strasbourg", "LOCATED_IN")],
     "which 1950 Rome convention is enforced by the Strasbourg human-rights court",
     "ECHR Rome 1950 Strasbourg European Court Human Rights treaty"),
    # --- 34. noise ---
    ("Actually, hold on, let me flip back to the headnote for a second to get the page pin-cite right.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The International Covenant on Civil and Political Rights, adopted in 1966 and in force from 1976, binds state parties to core civil-liberty guarantees monitored by the Human Rights Committee.", "reference", "knowledge", False,
     [("International Covenant on Civil and Political Rights", "publication"), ("1966", "date"), ("1976", "date"), ("Human Rights Committee", "organization"), ("civil-liberty guarantees", "concept")],
     [("Human Rights Committee", "International Covenant on Civil and Political Rights", "APPLIES_TO")],
     "which 1966 UN covenant on civil and political rights is monitored by the Human Rights Committee",
     "ICCPR 1966 1976 Human Rights Committee civil political covenant"),
    # --- 36 ---
    ("The World Justice Project Rule of Law Index, first published in 2010, scores over 140 jurisdictions on eight factors and has become a standard benchmark in comparative legal research.", "reference", "knowledge", False,
     [("World Justice Project Rule of Law Index", "publication"), ("2010", "date"), ("comparative legal research", "field")],
     [],
     "which 2010 cross-country index has become a standard rule-of-law benchmark",
     "WJP Rule of Law Index 2010 jurisdictions factors benchmark"),
    # --- 37 ---
    ("Roman-law jurisprudence survives through Gaius's Institutes of around 161 CE, which organised private law into the triadic scheme of personae, res, and actiones that still shapes civil-law doctrine.", "reference", "knowledge", False,
     [("Roman-law jurisprudence", "field"), ("Gaius", "person"), ("Institutes", "publication"), ("161 CE", "date"), ("civil-law doctrine", "concept")],
     [("Institutes", "Gaius", "AUTHORED_BY"), ("civil-law doctrine", "Institutes", "BUILDS_ON")],
     "which second-century Gaian treatise gave Roman law its persons-things-actions scheme",
     "Gaius Institutes personae res actiones Roman law civil tradition"),
    # --- 38 ---
    ("The Yale Law Journal, founded in 1891, became a leading venue for legal realism and later law-and-economics scholarship alongside the Harvard Law Review.", "reference", "knowledge", False,
     [("Yale Law Journal", "publication"), ("1891", "date"), ("legal realism", "theory"), ("law-and-economics", "field"), ("Harvard Law Review", "publication")],
     [],
     "which 1891-founded American law journal became a hub for legal realism and law-and-economics",
     "Yale Law Journal 1891 realism economics venue scholarship"),
    # --- 39 ---
    ("Jeremy Bentham's Of Laws in General, composed around 1782 but first fully published in 1945, is a foundational text of analytical jurisprudence and early command-theory positivism.", "reference", "knowledge", False,
     [("Jeremy Bentham", "person"), ("Of Laws in General", "publication"), ("1782", "date"), ("1945", "date"), ("analytical jurisprudence", "field"), ("command-theory positivism", "theory")],
     [("Of Laws in General", "Jeremy Bentham", "AUTHORED_BY"), ("analytical jurisprudence", "Of Laws in General", "BUILDS_ON")],
     "which late-eighteenth-century Bentham manuscript seeded analytical jurisprudence",
     "Bentham Of Laws General command theory analytical jurisprudence year"),
    # --- 40 ---
    ("John Austin's The Province of Jurisprudence Determined, published in 1832, defined law as the command of a sovereign backed by sanction and was later improved on by Hart's rule-based model.", "reference", "knowledge", False,
     [("John Austin", "person"), ("The Province of Jurisprudence Determined", "publication"), ("1832", "date"), ("command of a sovereign", "theory"), ("Hart's rule-based model", "theory")],
     [("The Province of Jurisprudence Determined", "John Austin", "AUTHORED_BY"), ("Hart's rule-based model", "command of a sovereign", "IMPROVES_ON")],
     "which 1832 Austin book defined law as sovereign command before Hart revised it",
     "Austin Province Jurisprudence Determined command sovereign sanction year"),
    # --- 41 ---
    ("Constitutional theorist John Hart Ely's Democracy and Distrust of 1980 defends process-based judicial review that improves on purely substantive value-imposition accounts.", "reference", "knowledge", False,
     [("John Hart Ely", "person"), ("Democracy and Distrust", "publication"), ("1980", "date"), ("process-based judicial review", "theory"), ("value-imposition accounts", "theory")],
     [("Democracy and Distrust", "John Hart Ely", "AUTHORED_BY"), ("process-based judicial review", "value-imposition accounts", "IMPROVES_ON")],
     "which 1980 Ely book defends process-based judicial review against value-imposition",
     "Ely Democracy Distrust process review representation reinforcing year"),
    # --- 42 ---
    ("Cass Sunstein's minimalism, articulated in One Case at a Time of 1999, favours narrow and shallow judicial opinions over broad theoretical rulings as a constitutional method.", "preference", "knowledge", False,
     [("Cass Sunstein", "person"), ("One Case at a Time", "publication"), ("1999", "date"), ("narrow and shallow judicial opinions", "method"), ("broad theoretical rulings", "method")],
     [("One Case at a Time", "Cass Sunstein", "AUTHORED_BY"), ("narrow and shallow judicial opinions", "broad theoretical rulings", "PREFERS")],
     "which 1999 Sunstein book argues for narrow minimalist opinions over broad theoretical rulings",
     "Sunstein One Case Time minimalism narrow shallow opinions year"),
    # --- 43 ---
    ("Alan Watson's Legal Transplants, published in 1974, argues that borrowing across legal systems is the dominant engine of doctrinal change in comparative law.", "reference", "knowledge", False,
     [("Alan Watson", "person"), ("Legal Transplants", "publication"), ("1974", "date"), ("comparative law", "field")],
     [("Legal Transplants", "Alan Watson", "AUTHORED_BY")],
     "which 1974 Watson book argued that transplants drive doctrinal change in comparative law",
     "Watson Legal Transplants borrowing comparative law doctrinal year"),
    # --- 44 ---
    ("Mirjan Damaska's The Faces of Justice and State Authority, published in 1986, contrasts hierarchical and coordinate judicial ideals as the deep structure of comparative procedure.", "reference", "knowledge", False,
     [("Mirjan Damaska", "person"), ("The Faces of Justice and State Authority", "publication"), ("1986", "date"), ("hierarchical", "concept"), ("coordinate judicial ideals", "concept")],
     [("The Faces of Justice and State Authority", "Mirjan Damaska", "AUTHORED_BY")],
     "which 1986 Damaska book contrasts hierarchical and coordinate ideals in comparative procedure",
     "Damaska Faces Justice State Authority hierarchical coordinate year"),
    # --- 45 ---
    ("The Universal Declaration of Human Rights, adopted by the United Nations General Assembly on 10 December 1948, provides the normative anchor for later human-rights treaties.", "milestone", "knowledge", False,
     [("Universal Declaration of Human Rights", "publication"), ("United Nations General Assembly", "organization"), ("10 December 1948", "date"), ("human-rights treaties", "concept")],
     [("human-rights treaties", "Universal Declaration of Human Rights", "BUILDS_ON")],
     "which 1948 United Nations declaration anchors the modern human-rights treaty system",
     "Universal Declaration Human Rights UDHR UN 1948 Paris treaty system"),
    # --- 46 ---
    ("Hersch Lauterpacht's An International Bill of the Rights of Man, published in 1945, shaped the drafting of the Universal Declaration and founded modern international human-rights scholarship.", "reference", "knowledge", False,
     [("Hersch Lauterpacht", "person"), ("An International Bill of the Rights of Man", "publication"), ("1945", "date"), ("Universal Declaration", "publication"), ("international human-rights scholarship", "field")],
     [("An International Bill of the Rights of Man", "Hersch Lauterpacht", "AUTHORED_BY"), ("Universal Declaration", "An International Bill of the Rights of Man", "BUILDS_ON")],
     "which 1945 Lauterpacht book prefigured the Universal Declaration and international rights scholarship",
     "Lauterpacht International Bill Rights Man 1945 Universal Declaration precursor"),
    # --- 47 ---
    ("Carl Schmitt's Political Theology of 1922 defined sovereignty as the decision on the exception and provoked enduring debate in constitutional theory.", "reference", "knowledge", False,
     [("Carl Schmitt", "person"), ("Political Theology", "publication"), ("1922", "date"), ("sovereignty", "concept"), ("constitutional theory", "field")],
     [("Political Theology", "Carl Schmitt", "AUTHORED_BY")],
     "which 1922 Schmitt book defined sovereignty as the decision on the exception",
     "Weimar jurist decisionism exception emergency power constitutional debate"),
    # --- 48 ---
    ("The Legal Process school, organised by Henry Hart and Albert Sacks in their 1958 teaching materials at Harvard, repositioned postwar jurisprudence around institutional settlement and reasoned elaboration.", "reference", "knowledge", False,
     [("Legal Process school", "theory"), ("Henry Hart", "person"), ("Albert Sacks", "person"), ("1958", "date"), ("Harvard", "organization"), ("institutional settlement", "concept")],
     [("Legal Process school", "Henry Hart", "AUTHORED_BY"), ("Legal Process school", "Albert Sacks", "AUTHORED_BY")],
     "which 1958 Harvard teaching materials anchored the Legal Process school of postwar jurisprudence",
     "Hart Sacks Legal Process Harvard institutional settlement reasoned elaboration year"),
    # --- 49 ---
    ("Robert Cover's essay Nomos and Narrative, published in the 1983 Harvard Law Review, frames law as a normative universe inhabited and contested by communities of interpretation.", "reference", "knowledge", False,
     [("Robert Cover", "person"), ("Nomos and Narrative", "publication"), ("1983", "date"), ("Harvard Law Review", "publication"), ("normative universe", "concept")],
     [("Nomos and Narrative", "Robert Cover", "AUTHORED_BY"), ("Nomos and Narrative", "Harvard Law Review", "PUBLISHED_IN")],
     "which 1983 Cover essay frames law as a nomos inhabited by interpretive communities",
     "Cover Nomos Narrative Harvard 1983 normative universe interpretation"),
    # --- 50 ---
    ("Amartya Sen's The Idea of Justice, published in 2009, improves on John Rawls's transcendental institutionalism by grounding justice theory in comparative real-world assessments.", "reference", "knowledge", False,
     [("Amartya Sen", "person"), ("The Idea of Justice", "publication"), ("2009", "date"), ("John Rawls", "person"), ("transcendental institutionalism", "theory")],
     [("The Idea of Justice", "Amartya Sen", "AUTHORED_BY"), ("The Idea of Justice", "transcendental institutionalism", "IMPROVES_ON")],
     "which 2009 Sen book recasts justice theory against Rawlsian transcendental institutionalism",
     "Sen Idea Justice Rawls transcendental comparative realisation year"),
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
