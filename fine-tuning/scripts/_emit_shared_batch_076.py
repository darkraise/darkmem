"""One-off emitter for shared-base batch-076 — knowledge domain (medicine, public health, epidemiology).

Writes 50 rows with ids shared-03751..03800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_076.tmp.jsonl"
ID_OFFSET = 3750

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Framingham Heart Study, launched in 1948 in Framingham, Massachusetts, established the modern concept of cardiovascular risk factors through decades of cohort follow-up.", "milestone", "knowledge", False,
     [("Framingham Heart Study", "publication"), ("1948", "date"), ("Framingham", "place"), ("Massachusetts", "place"), ("cardiovascular risk factors", "concept")],
     [("Framingham Heart Study", "cardiovascular risk factors", "PRODUCES")],
     "where and when did the canonical post-war American cohort that named cardiac risk factors begin",
     "Framingham heart cohort cardiovascular risk factor longitudinal year"),
    # --- 2 ---
    ("The UK Biobank, recruited between 2006 and 2010, enrolled roughly 500,000 adult participants to support large-scale genetic and epidemiological research.", "reference", "knowledge", False,
     [("UK Biobank", "publication"), ("2006", "date"), ("2010", "date"), ("genetic and epidemiological research", "field")],
     [("UK Biobank", "genetic and epidemiological research", "SUPPORTS")],
     "which British biomedical resource recruited half a million adults between 2006 and 2010",
     "UK Biobank half million adult cohort genetic epidemiology recruitment"),
    # --- 3 ---
    ("The Nurses' Health Study, begun by Frank Speizer in 1976, has tracked over 120,000 American female nurses to study chronic disease risk and lifestyle exposures.", "reference", "knowledge", False,
     [("Nurses' Health Study", "publication"), ("Frank Speizer", "person"), ("1976", "date"), ("chronic disease risk", "concept")],
     [("Nurses' Health Study", "Frank Speizer", "AUTHORED_BY")],
     "which 1976 American cohort followed over 120,000 female nurses for chronic disease risk",
     "Nurses Health Study Speizer female cohort chronic disease year"),
    # --- 4 ---
    ("The Medical Research Council Streptomycin trial of 1948, designed by Austin Bradford Hill, is widely treated as the first properly randomised controlled trial in clinical medicine.", "milestone", "knowledge", False,
     [("Medical Research Council", "organization"), ("Streptomycin trial", "event"), ("1948", "date"), ("Austin Bradford Hill", "person"), ("randomised controlled trial", "method")],
     [("Streptomycin trial", "Austin Bradford Hill", "AUTHORED_BY"), ("Streptomycin trial", "randomised controlled trial", "IMPLEMENTS")],
     "which 1948 British tuberculosis study is treated as the first true randomised controlled trial",
     "MRC Streptomycin Bradford Hill randomisation tuberculosis trial year"),
    # --- 5 ---
    ("Austin Bradford Hill's 1965 paper in the Proceedings of the Royal Society of Medicine articulated nine viewpoints for inferring causation from epidemiological association.", "reference", "knowledge", False,
     [("Austin Bradford Hill", "person"), ("1965", "date"), ("Proceedings of the Royal Society of Medicine", "publication"), ("causation", "concept"), ("epidemiological association", "concept")],
     [("Proceedings of the Royal Society of Medicine", "Austin Bradford Hill", "AUTHORED_BY")],
     "whose 1965 paper laid out the canonical viewpoints for inferring causation from association",
     "Bradford Hill criteria causation epidemiology nine viewpoints year"),
    # --- 6 ---
    ("The CONSORT statement, first published in JAMA in 1996 and revised in 2010, improves on earlier ad hoc trial reporting by mandating a 25-item checklist and flow diagram.", "reference", "knowledge", False,
     [("CONSORT statement", "publication"), ("JAMA", "publication"), ("1996", "date"), ("2010", "date"), ("ad hoc trial reporting", "concept")],
     [("CONSORT statement", "JAMA", "PUBLISHED_IN"), ("CONSORT statement", "ad hoc trial reporting", "IMPROVES_ON")],
     "which reporting standard replaced ad hoc trial write-ups with a 25-item checklist and flow diagram",
     "CONSORT JAMA trial reporting checklist flow diagram years"),
    # --- 7 ---
    ("The GRADE framework, introduced by Gordon Guyatt and colleagues from 2004, improves on earlier letter-grade evidence schemes by separately rating quality of evidence and strength of recommendation.", "reference", "knowledge", False,
     [("GRADE framework", "framework"), ("Gordon Guyatt", "person"), ("2004", "date"), ("letter-grade evidence schemes", "concept")],
     [("GRADE framework", "Gordon Guyatt", "AUTHORED_BY"), ("GRADE framework", "letter-grade evidence schemes", "IMPROVES_ON")],
     "which evidence-grading framework supplanted earlier letter-grade schemes from the mid-2000s",
     "GRADE Guyatt evidence quality recommendation strength year"),
    # --- 8 ---
    ("The Cochrane Collaboration, founded in Oxford in 1993 by Iain Chalmers and named for Archie Cochrane, organises systematic reviews of healthcare interventions.", "milestone", "knowledge", False,
     [("Cochrane Collaboration", "organization"), ("Oxford", "place"), ("1993", "date"), ("Iain Chalmers", "person"), ("Archie Cochrane", "person"), ("systematic reviews", "method")],
     [("Cochrane Collaboration", "Iain Chalmers", "AUTHORED_BY"), ("Cochrane Collaboration", "systematic reviews", "PRODUCES")],
     "which 1993 Oxford-founded body organises systematic reviews of healthcare interventions",
     "Cochrane Collaboration Chalmers Oxford systematic review founding year"),
    # --- 9 ---
    ("The evidence-based medicine pyramid, popularised by David Sackett and the McMaster group from the early 1990s, ranks systematic reviews and randomised trials above observational studies and expert opinion.", "architecture", "knowledge", False,
     [("evidence-based medicine pyramid", "framework"), ("David Sackett", "person"), ("McMaster", "organization"), ("systematic reviews", "method"), ("randomised trials", "method"), ("observational studies", "method"), ("expert opinion", "concept")],
     [("evidence-based medicine pyramid", "David Sackett", "AUTHORED_BY"), ("randomised trials", "expert opinion", "PREFERS")],
     "which hierarchy popularised by Sackett and McMaster ranks RCTs above observational studies and opinion",
     "EBM pyramid Sackett McMaster systematic review hierarchy nineties"),
    # --- 10. noise ---
    ("Let me check whether that protocol amendment was filed before or after the interim analysis.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("In epidemiology, incidence measures the number of new disease cases arising in a defined population over a specified interval, while prevalence captures the proportion already affected at a point in time.", "fact", "knowledge", False,
     [("incidence", "concept"), ("prevalence", "concept"), ("disease cases", "concept")],
     [("incidence", "prevalence", "RELATED_TO")],
     "how do incidence and prevalence differ as epidemiological measures of disease occurrence",
     "incidence prevalence new cases existing proportion measure distinction"),
    # --- 12 ---
    ("The case-control design, sharpened by Jerome Cornfield's 1951 analysis of lung cancer and smoking, samples on outcome and looks backward to compare exposure histories.", "reference", "knowledge", False,
     [("case-control design", "method"), ("Jerome Cornfield", "person"), ("1951", "date"), ("lung cancer", "concept"), ("smoking", "concept")],
     [("case-control design", "Jerome Cornfield", "AUTHORED_BY")],
     "which retrospective study design samples on outcome to compare past exposures",
     "case control retrospective Cornfield odds ratio lung cancer year"),
    # --- 13 ---
    ("Richard Doll and Austin Bradford Hill's 1954 British Doctors Study, published in the BMJ, provided the first prospective cohort evidence linking cigarette smoking to lung cancer mortality.", "reference", "knowledge", False,
     [("Richard Doll", "person"), ("Austin Bradford Hill", "person"), ("1954", "date"), ("British Doctors Study", "publication"), ("BMJ", "publication"), ("cigarette smoking", "concept"), ("lung cancer mortality", "finding")],
     [("British Doctors Study", "Richard Doll", "AUTHORED_BY"), ("British Doctors Study", "BMJ", "PUBLISHED_IN")],
     "which 1954 British prospective cohort first linked smoking to lung cancer mortality",
     "Doll Hill British Doctors smoking lung cancer cohort year"),
    # --- 14 ---
    ("Modern messenger RNA vaccines such as BNT162b2 replaced earlier inactivated and protein-subunit COVID-19 candidates as the dominant Western platform during 2020 and 2021.", "decision", "knowledge", False,
     [("messenger RNA vaccines", "technology"), ("BNT162b2", "technology"), ("inactivated", "method"), ("protein-subunit", "method"), ("COVID-19", "concept"), ("2020", "date"), ("2021", "date")],
     [("messenger RNA vaccines", "inactivated", "REPLACES"), ("messenger RNA vaccines", "protein-subunit", "REPLACES")],
     "which COVID-era platform displaced inactivated and protein-subunit candidates in Western markets",
     "mRNA vaccine BNT162b2 COVID inactivated subunit replacement years"),
    # --- 15 ---
    ("Edward Jenner's 1798 Inquiry into the Variolae Vaccinae documented cowpox inoculation as protection against smallpox, displacing the older variolation practice.", "milestone", "knowledge", False,
     [("Edward Jenner", "person"), ("1798", "date"), ("Inquiry into the Variolae Vaccinae", "publication"), ("cowpox inoculation", "method"), ("smallpox", "concept"), ("variolation", "method")],
     [("Inquiry into the Variolae Vaccinae", "Edward Jenner", "AUTHORED_BY"), ("cowpox inoculation", "variolation", "REPLACES")],
     "whose 1798 inquiry on cowpox inoculation displaced the older variolation practice for smallpox",
     "Jenner Variolae Vaccinae cowpox smallpox variolation replacement year"),
    # --- 16 ---
    ("The World Health Organization certified the global eradication of smallpox in 1980, the only human infectious disease eliminated to date through coordinated vaccination.", "milestone", "knowledge", False,
     [("World Health Organization", "organization"), ("smallpox", "concept"), ("1980", "date"), ("vaccination", "method")],
     [("World Health Organization", "smallpox", "PRODUCES")],
     "in which year did the WHO certify the global eradication of smallpox",
     "WHO smallpox eradication certification year only human disease"),
    # --- 17 ---
    ("John Snow's 1854 mapping of cholera deaths around the Broad Street pump in London is conventionally treated as the founding case of modern epidemiology.", "milestone", "knowledge", False,
     [("John Snow", "person"), ("1854", "date"), ("cholera deaths", "concept"), ("Broad Street", "place"), ("London", "place"), ("modern epidemiology", "field")],
     [("John Snow", "modern epidemiology", "PRODUCES")],
     "which 1854 London cholera investigation is treated as the founding case of epidemiology",
     "Snow Broad Street pump cholera London epidemiology founding year"),
    # --- 18 ---
    ("Ignaz Semmelweis demonstrated in 1847 that handwashing with chlorinated lime sharply reduced puerperal fever mortality at the Vienna General Hospital obstetric wards.", "milestone", "knowledge", False,
     [("Ignaz Semmelweis", "person"), ("1847", "date"), ("handwashing", "method"), ("chlorinated lime", "concept"), ("puerperal fever", "concept"), ("Vienna General Hospital", "organization")],
     [("Ignaz Semmelweis", "handwashing", "AUTHORED_BY")],
     "who showed in 1847 that chlorinated handwashing cut puerperal fever in Vienna obstetric wards",
     "Semmelweis Vienna chlorinated lime puerperal fever handwashing year"),
    # --- 19 ---
    ("Alexander Fleming's 1928 observation of Penicillium notatum lysing staphylococci on a stray plate launched the era of antibiotic chemotherapy.", "milestone", "knowledge", False,
     [("Alexander Fleming", "person"), ("1928", "date"), ("Penicillium notatum", "concept"), ("staphylococci", "concept"), ("antibiotic chemotherapy", "concept")],
     [("Alexander Fleming", "antibiotic chemotherapy", "PRODUCES")],
     "whose 1928 plate observation opened the antibiotic chemotherapy era",
     "Fleming Penicillium notatum staphylococci antibiotic discovery year"),
    # --- 20 ---
    ("The 2014 WHO global report on antimicrobial resistance warned that carbapenem-resistant Enterobacteriaceae are spreading worldwide, threatening the gains of mid-twentieth-century antibiotic therapy.", "problem", "knowledge", False,
     [("WHO global report on antimicrobial resistance", "publication"), ("2014", "date"), ("carbapenem-resistant Enterobacteriaceae", "concept"), ("antibiotic therapy", "concept")],
     [("WHO global report on antimicrobial resistance", "antibiotic therapy", "CONTRADICTS")],
     "which 2014 WHO report flagged carbapenem-resistant Enterobacteriaceae as a global threat",
     "WHO antimicrobial resistance carbapenem CRE global report year"),
    # --- 21 ---
    ("The Centers for Disease Control and Prevention published its first Antibiotic Resistance Threats report in 2013 and updated the threat list in 2019, ranking Clostridioides difficile among the urgent pathogens.", "reference", "knowledge", False,
     [("Centers for Disease Control and Prevention", "organization"), ("Antibiotic Resistance Threats", "publication"), ("2013", "date"), ("2019", "date"), ("Clostridioides difficile", "concept")],
     [("Antibiotic Resistance Threats", "Centers for Disease Control and Prevention", "AUTHORED_BY")],
     "which CDC report series ranked Clostridioides difficile among urgent antimicrobial threats",
     "CDC AR Threats Clostridioides difficile urgent pathogen list years"),
    # --- 22 ---
    ("The European Centre for Disease Prevention and Control, established in Stockholm in 2005, coordinates surveillance and outbreak response across European Union member states.", "fact", "knowledge", False,
     [("European Centre for Disease Prevention and Control", "organization"), ("Stockholm", "place"), ("2005", "date"), ("European Union", "organization")],
     [("European Centre for Disease Prevention and Control", "European Union", "SUPPORTS")],
     "which 2005 Stockholm-based agency coordinates EU disease surveillance and outbreak response",
     "ECDC Stockholm European Union surveillance outbreak founding year"),
    # --- 23 ---
    ("The 2005 International Health Regulations, agreed at the World Health Assembly in Geneva, replaced the 1969 framework and require member states to report public-health emergencies of international concern.", "milestone", "knowledge", False,
     [("International Health Regulations", "publication"), ("2005", "date"), ("World Health Assembly", "event"), ("Geneva", "place"), ("public-health emergencies of international concern", "concept")],
     [("International Health Regulations", "World Health Assembly", "AUTHORED_BY")],
     "which 2005 Geneva treaty replaced the 1969 framework for cross-border public-health emergencies",
     "IHR 2005 World Health Assembly Geneva PHEIC notification treaty year"),
    # --- 24 ---
    ("The Global Outbreak Alert and Response Network, organised by WHO from 2000, replaced ad hoc bilateral outbreak responses with a standing partnership of more than 250 technical institutions.", "architecture", "knowledge", False,
     [("Global Outbreak Alert and Response Network", "organization"), ("WHO", "organization"), ("2000", "date"), ("ad hoc bilateral outbreak responses", "concept")],
     [("Global Outbreak Alert and Response Network", "WHO", "AUTHORED_BY"), ("Global Outbreak Alert and Response Network", "ad hoc bilateral outbreak responses", "REPLACES")],
     "which 2000 WHO partnership replaced ad hoc bilateral outbreak responses with a standing technical network",
     "GOARN WHO outbreak network standing partnership year"),
    # --- 25 ---
    ("The Coalition for Epidemic Preparedness Innovations, launched at Davos in 2017, finances vaccine development against priority pathogens such as Nipah, Lassa, and MERS.", "milestone", "knowledge", False,
     [("Coalition for Epidemic Preparedness Innovations", "organization"), ("Davos", "place"), ("2017", "date"), ("Nipah", "concept"), ("Lassa", "concept"), ("MERS", "concept")],
     [("Coalition for Epidemic Preparedness Innovations", "MERS", "APPLIES_TO")],
     "which 2017 Davos-launched coalition finances vaccines against Nipah, Lassa, and MERS",
     "CEPI Davos vaccine Nipah Lassa MERS pandemic preparedness year"),
    # --- 26 ---
    ("The Salk inactivated poliovirus vaccine, licensed in the United States in 1955, was largely replaced for routine use by the Sabin live oral vaccine over the following decade.", "decision", "knowledge", False,
     [("Salk inactivated poliovirus vaccine", "technology"), ("United States", "place"), ("1955", "date"), ("Sabin live oral vaccine", "technology")],
     [("Sabin live oral vaccine", "Salk inactivated poliovirus vaccine", "REPLACES")],
     "which oral polio vaccine displaced the Salk inactivated formulation for routine use after 1955",
     "Salk Sabin polio vaccine licensure replacement year"),
    # --- 27 ---
    ("The Global Burden of Disease study, coordinated by the Institute for Health Metrics and Evaluation in Seattle, quantifies disability-adjusted life years for over 350 diseases and injuries.", "reference", "knowledge", False,
     [("Global Burden of Disease", "publication"), ("Institute for Health Metrics and Evaluation", "organization"), ("Seattle", "place"), ("disability-adjusted life years", "concept")],
     [("Global Burden of Disease", "Institute for Health Metrics and Evaluation", "AUTHORED_BY"), ("Global Burden of Disease", "disability-adjusted life years", "PRODUCES")],
     "which Seattle-coordinated study quantifies DALYs across more than 350 diseases and injuries",
     "Global Burden Disease IHME Seattle DALY disease injury"),
    # --- 28 ---
    ("Christopher Murray and Alan Lopez first published the disability-adjusted life year framework in their 1996 World Bank monograph on the global burden of disease.", "reference", "knowledge", False,
     [("Christopher Murray", "person"), ("Alan Lopez", "person"), ("disability-adjusted life year", "concept"), ("1996", "date"), ("World Bank", "organization")],
     [("disability-adjusted life year", "Christopher Murray", "AUTHORED_BY")],
     "who first published the DALY framework in a 1996 World Bank monograph",
     "Murray Lopez DALY World Bank monograph burden disease year"),
    # --- 29 ---
    ("The Lancet's 2009 commission on managing the health effects of climate change framed climate change as the dominant global health threat of the twenty-first century.", "reference", "knowledge", False,
     [("Lancet", "publication"), ("2009", "date"), ("commission on managing the health effects of climate change", "publication"), ("global health threat", "claim")],
     [("commission on managing the health effects of climate change", "Lancet", "PUBLISHED_IN")],
     "which 2009 Lancet commission framed climate change as the dominant twenty-first-century health threat",
     "Lancet climate health commission twenty first century year"),
    # --- 30 ---
    ("The Tuskegee Syphilis Study, conducted by the United States Public Health Service from 1932 to 1972 in Macon County, Alabama, is treated as a defining ethical violation in clinical research history.", "problem", "knowledge", False,
     [("Tuskegee Syphilis Study", "event"), ("United States Public Health Service", "organization"), ("1932", "date"), ("1972", "date"), ("Macon County", "place"), ("Alabama", "place")],
     [("Tuskegee Syphilis Study", "United States Public Health Service", "AUTHORED_BY")],
     "which forty-year US Public Health Service syphilis study is treated as a defining research ethics violation",
     "Tuskegee syphilis Public Health Service Macon Alabama years"),
    # --- 31 ---
    ("The Belmont Report, issued in 1979 by the National Commission for the Protection of Human Subjects, codified respect for persons, beneficence, and justice as the founding principles of US research ethics.", "milestone", "knowledge", False,
     [("Belmont Report", "publication"), ("1979", "date"), ("National Commission for the Protection of Human Subjects", "organization"), ("respect for persons", "concept"), ("beneficence", "concept"), ("justice", "concept")],
     [("Belmont Report", "National Commission for the Protection of Human Subjects", "AUTHORED_BY")],
     "which 1979 US report codified respect for persons, beneficence, and justice as research ethics principles",
     "Belmont Report 1979 National Commission research ethics principles year"),
    # --- 32 ---
    ("The World Medical Association's Declaration of Helsinki, first adopted in 1964 and revised most recently in 2013, is the dominant international ethical statement for biomedical research on human subjects.", "reference", "knowledge", False,
     [("World Medical Association", "organization"), ("Declaration of Helsinki", "publication"), ("1964", "date"), ("2013", "date"), ("biomedical research on human subjects", "concept")],
     [("Declaration of Helsinki", "World Medical Association", "AUTHORED_BY")],
     "which World Medical Association declaration is the dominant international biomedical research ethics statement",
     "Helsinki Declaration WMA human subjects biomedical research years"),
    # --- 33 ---
    ("ClinicalTrials.gov, established by the United States National Library of Medicine in 2000, is the dominant public registry for prospective clinical trial registration mandated by ICMJE journals.", "reference", "knowledge", False,
     [("ClinicalTrials.gov", "platform"), ("United States National Library of Medicine", "organization"), ("2000", "date"), ("ICMJE", "organization"), ("clinical trial registration", "method")],
     [("ClinicalTrials.gov", "United States National Library of Medicine", "AUTHORED_BY"), ("ClinicalTrials.gov", "clinical trial registration", "SUPPORTS")],
     "which 2000 NLM-built registry is the dominant US public site for ICMJE-mandated trial registration",
     "ClinicalTrials.gov NLM ICMJE registration registry founding year"),
    # --- 34. noise ---
    ("Hmm, I should re-pull the funnel plot before claiming there's no small-study effect here.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Double-blind randomisation, in which neither patient nor clinician knows the assigned arm, is the dominant method of bias control in pivotal pharmaceutical efficacy trials.", "preference", "knowledge", False,
     [("Double-blind randomisation", "method"), ("bias control", "concept"), ("pharmaceutical efficacy trials", "concept")],
     [("Double-blind randomisation", "bias control", "SUPPORTS")],
     "what is the dominant blinding strategy for guarding against measurement bias in pivotal drug studies",
     "blinding strategy pivotal pharmaceutical drug efficacy trial bias"),
    # --- 36 ---
    ("Jonas Salk's poliovirus vaccine field trial of 1954, coordinated by Thomas Francis Jr. across 1.8 million American schoolchildren, remains one of the largest placebo-controlled trials ever run.", "milestone", "knowledge", False,
     [("Jonas Salk", "person"), ("poliovirus vaccine field trial", "event"), ("1954", "date"), ("Thomas Francis Jr.", "person"), ("placebo-controlled trials", "method")],
     [("poliovirus vaccine field trial", "Thomas Francis Jr.", "AUTHORED_BY")],
     "which 1954 Salk polio vaccine field trial enrolled 1.8 million American schoolchildren under Francis",
     "Salk Francis polio field trial American schoolchildren year"),
    # --- 37 ---
    ("The 2014 to 2016 West African Ebola epidemic, centred on Guinea, Liberia, and Sierra Leone, exposed gaps in WHO outbreak response that the 2016 Ebola Interim Assessment Panel report sought to address.", "problem", "knowledge", False,
     [("West African Ebola epidemic", "event"), ("2014", "date"), ("2016", "date"), ("Guinea", "place"), ("Liberia", "place"), ("Sierra Leone", "place"), ("Ebola Interim Assessment Panel", "organization")],
     [("Ebola Interim Assessment Panel", "West African Ebola epidemic", "APPLIES_TO")],
     "which West African Ebola epidemic prompted the WHO Ebola Interim Assessment Panel review",
     "Ebola West Africa Guinea Liberia Sierra Leone WHO panel years"),
    # --- 38 ---
    ("The 1918 Spanish influenza pandemic killed an estimated 50 million people worldwide and remains the benchmark scenario in modern pandemic preparedness planning.", "milestone", "knowledge", False,
     [("Spanish influenza pandemic", "event"), ("1918", "date"), ("pandemic preparedness planning", "concept")],
     [("Spanish influenza pandemic", "pandemic preparedness planning", "APPLIES_TO")],
     "what global influenza event from the First World War era still anchors modern preparedness planning",
     "1918 Spanish flu influenza pandemic benchmark preparedness scenario"),
    # --- 39 ---
    ("Anthony Fauci led the United States National Institute of Allergy and Infectious Diseases from 1984 to 2022, shaping responses to HIV/AIDS, the 2009 H1N1 pandemic, and COVID-19.", "fact", "knowledge", False,
     [("Anthony Fauci", "person"), ("United States National Institute of Allergy and Infectious Diseases", "organization"), ("1984", "date"), ("2022", "date"), ("HIV/AIDS", "concept"), ("H1N1", "concept"), ("COVID-19", "concept")],
     [("Anthony Fauci", "United States National Institute of Allergy and Infectious Diseases", "WORKS_AT")],
     "who led the US NIAID across the HIV/AIDS, H1N1, and COVID-19 responses from 1984 to 2022",
     "Fauci NIAID HIV AIDS H1N1 COVID director tenure years"),
    # --- 40 ---
    ("The 1984 identification of human immunodeficiency virus by Luc Montagnier and Robert Gallo opened the path to combination antiretroviral therapy, which displaced AZT monotherapy in the mid-1990s.", "milestone", "knowledge", False,
     [("human immunodeficiency virus", "concept"), ("Luc Montagnier", "person"), ("Robert Gallo", "person"), ("1984", "date"), ("combination antiretroviral therapy", "method"), ("AZT monotherapy", "method")],
     [("combination antiretroviral therapy", "AZT monotherapy", "REPLACES")],
     "which combination regimen displaced AZT monotherapy after the 1984 identification of HIV",
     "Montagnier Gallo HIV identification ART AZT monotherapy year"),
    # --- 41 ---
    ("The PRISMA statement, first published in PLOS Medicine and the BMJ in 2009 and revised as PRISMA 2020, improves on earlier QUOROM reporting standards for systematic reviews and meta-analyses.", "reference", "knowledge", False,
     [("PRISMA statement", "publication"), ("PLOS Medicine", "publication"), ("BMJ", "publication"), ("2009", "date"), ("PRISMA 2020", "publication"), ("QUOROM", "publication")],
     [("PRISMA 2020", "QUOROM", "IMPROVES_ON"), ("PRISMA statement", "PLOS Medicine", "PUBLISHED_IN")],
     "which 2009 reporting standard replaced the QUOROM checklist for systematic reviews and meta-analyses",
     "PRISMA QUOROM systematic review meta analysis reporting standard year"),
    # --- 42 ---
    ("Archie Cochrane's 1972 monograph Effectiveness and Efficiency, published by the Nuffield Provincial Hospitals Trust, argued that medicine should be evaluated by randomised trials and population-level outcomes.", "reference", "knowledge", False,
     [("Archie Cochrane", "person"), ("1972", "date"), ("Effectiveness and Efficiency", "publication"), ("Nuffield Provincial Hospitals Trust", "organization"), ("randomised trials", "method")],
     [("Effectiveness and Efficiency", "Archie Cochrane", "AUTHORED_BY")],
     "which 1972 Cochrane monograph argued that medicine should be evaluated by randomised trials",
     "Cochrane Effectiveness Efficiency Nuffield monograph randomised year"),
    # --- 43 ---
    ("The 1974 Lalonde report by the Canadian government broke from a curative-care frame by treating lifestyle and environment as primary determinants of population health.", "decision", "knowledge", False,
     [("Lalonde report", "publication"), ("1974", "date"), ("Canadian government", "organization"), ("curative-care frame", "concept"), ("population health", "concept")],
     [("Lalonde report", "curative-care frame", "REPLACES")],
     "which mid-1970s federal Canadian paper reframed health policy around lifestyle and environmental drivers",
     "Lalonde report Canada curative care population health determinants year"),
    # --- 44 ---
    ("Sir Michael Marmot's Whitehall II study, launched in 1985 among British civil servants, showed a graded social gradient in cardiovascular and all-cause mortality across employment grades.", "reference", "knowledge", False,
     [("Sir Michael Marmot", "person"), ("Whitehall II", "publication"), ("1985", "date"), ("British civil servants", "organization"), ("social gradient", "finding")],
     [("Whitehall II", "Sir Michael Marmot", "AUTHORED_BY"), ("Whitehall II", "social gradient", "PRODUCES")],
     "which Marmot-led 1985 British civil-service cohort showed a graded mortality gradient across employment grades",
     "Marmot Whitehall II civil servant social gradient mortality year"),
    # --- 45 ---
    ("The Diabetes Control and Complications Trial, published in the New England Journal of Medicine in 1993, established intensive insulin therapy as the standard of care for type 1 diabetes.", "reference", "knowledge", False,
     [("Diabetes Control and Complications Trial", "publication"), ("New England Journal of Medicine", "publication"), ("1993", "date"), ("intensive insulin therapy", "method"), ("type 1 diabetes", "concept")],
     [("Diabetes Control and Complications Trial", "New England Journal of Medicine", "PUBLISHED_IN"), ("intensive insulin therapy", "type 1 diabetes", "APPLIES_TO")],
     "which 1993 NEJM trial established intensive insulin therapy as the standard for type 1 diabetes",
     "DCCT NEJM intensive insulin type 1 diabetes standard care year"),
    # --- 46 ---
    ("The Women's Health Initiative trial, halted early in 2002, overturned the prior consensus on combined hormone replacement therapy by showing increased breast cancer and cardiovascular event rates.", "reference", "knowledge", False,
     [("Women's Health Initiative", "publication"), ("2002", "date"), ("combined hormone replacement therapy", "method"), ("breast cancer", "concept"), ("cardiovascular event rates", "finding")],
     [("Women's Health Initiative", "combined hormone replacement therapy", "CONTRADICTS")],
     "which 2002 trial overturned the prior consensus on combined hormone replacement therapy",
     "WHI 2002 hormone replacement therapy breast cancer cardiovascular year"),
    # --- 47 ---
    ("The Million Women Study, organised by Valerie Beral from 1996 in the United Kingdom, recruited over a million women aged 50 and older to study breast cancer and hormone exposures.", "reference", "knowledge", False,
     [("Million Women Study", "publication"), ("Valerie Beral", "person"), ("1996", "date"), ("United Kingdom", "place"), ("breast cancer", "concept"), ("hormone exposures", "concept")],
     [("Million Women Study", "Valerie Beral", "AUTHORED_BY")],
     "which mid-1990s British cohort enrolled over a million older women to investigate hormone-related cancer",
     "Million Women Study Beral UK breast cancer hormone cohort year"),
    # --- 48 ---
    ("The MRC CRASH-2 trial, published in The Lancet in 2010, showed that early tranexamic acid reduces death from bleeding in trauma patients and reshaped global trauma protocols.", "reference", "knowledge", False,
     [("MRC", "organization"), ("CRASH-2", "publication"), ("Lancet", "publication"), ("2010", "date"), ("tranexamic acid", "concept"), ("trauma patients", "concept")],
     [("CRASH-2", "Lancet", "PUBLISHED_IN"), ("tranexamic acid", "trauma patients", "APPLIES_TO")],
     "which 2010 Lancet trial showed tranexamic acid reduces bleeding death in trauma patients",
     "CRASH-2 MRC tranexamic acid trauma bleeding Lancet year"),
    # --- 49 ---
    ("The 2003 SARS outbreak, first reported by Carlo Urbani in Hanoi, prompted the 2005 revision of the International Health Regulations and the creation of national pandemic plans across Asia.", "milestone", "knowledge", False,
     [("SARS outbreak", "event"), ("2003", "date"), ("Carlo Urbani", "person"), ("Hanoi", "place"), ("International Health Regulations", "publication"), ("pandemic plans", "concept")],
     [("SARS outbreak", "International Health Regulations", "CAUSES")],
     "which early-2000s Asian respiratory outbreak triggered the IHR overhaul and national pandemic planning",
     "SARS Urbani Hanoi 2003 IHR revision pandemic plan year"),
    # --- 50 ---
    ("The Number Needed to Treat metric, popularised by Andreas Laupacis and David Sackett in a 1988 New England Journal of Medicine paper, improves on bare relative risk reductions for clinical decision-making.", "reference", "knowledge", False,
     [("Number Needed to Treat", "concept"), ("Andreas Laupacis", "person"), ("David Sackett", "person"), ("1988", "date"), ("New England Journal of Medicine", "publication"), ("relative risk reductions", "concept")],
     [("Number Needed to Treat", "Andreas Laupacis", "AUTHORED_BY"), ("Number Needed to Treat", "relative risk reductions", "IMPROVES_ON")],
     "which 1988 NEJM paper popularised Number Needed to Treat over bare relative risk reductions",
     "NNT Laupacis Sackett NEJM relative risk reduction year"),
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
