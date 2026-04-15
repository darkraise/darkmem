"""One-off emitter for shared-base batch-118 — personal domain (adult education and career-change courses slice).

Writes 50 rows to data/v2/shared/batch_118.tmp.jsonl with ids shared-05851..05900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_118.tmp.jsonl"
ID_OFFSET = 5850

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Enrolled in the Warwick evening MBA cohort starting 2026-09-14; two years part-time, Monday and Thursday sessions on the Coventry campus.", "milestone", "personal", False,
     [("Warwick", "organization"), ("MBA", "concept"), ("2026-09-14", "date"), ("Coventry", "place"), ("Monday", "date"), ("Thursday", "date")],
     [("MBA", "Warwick", "LOCATED_IN")],
     "when does the part-time business degree cohort kick off and what is the weekly pattern",
     "warwick evening MBA start date campus weekday cadence two year"),
    # --- 2 ---
    ("Chose Le Wagon over General Assembly for the web-dev bootcamp; the Ruby-first curriculum fit the agency I was trying to land at.", "decision", "personal", False,
     [("Le Wagon", "organization"), ("General Assembly", "organization"), ("web-dev bootcamp", "event"), ("Ruby", "language")],
     [("Le Wagon", "General Assembly", "PREFERS"), ("Le Wagon", "Ruby", "USES")],
     "which coding bootcamp won out and why the language choice mattered",
     "le wagon over general assembly ruby first agency target bootcamp"),
    # --- 3 ---
    ("The PMP exam sat on 2026-03-22 in the Pearson Vue centre at Reading; passed above target on all five domains on the first attempt.", "milestone", "personal", False,
     [("PMP", "concept"), ("2026-03-22", "date"), ("Pearson Vue", "organization"), ("Reading", "place")],
     [("PMP", "Pearson Vue", "LOCATED_IN")],
     "when did I clear the project-management certification and on which try",
     "project mgmt cert sit location score domain breakdown try count"),
    # --- 4 ---
    ("Switched from the CFA Level 2 prep track to the CAIA programme after 2025-12; the alternatives firm I joined cared more about the CAIA letters.", "decision", "personal", False,
     [("CFA Level 2", "concept"), ("CAIA", "concept"), ("2025-12", "date"), ("alternatives firm", "organization")],
     [("CAIA", "CFA Level 2", "REPLACES")],
     "which finance qualification replaced the chartered-analyst track and why",
     "CFA level 2 swap CAIA alternatives firm letter value late 2025"),
    # --- 5 ---
    ("The Open University BSc in Computing and IT will finish on 2027-06-30; started in 2023 as a slow lane back into tech after the nursing career.", "reference", "personal", False,
     [("Open University", "organization"), ("BSc", "concept"), ("Computing and IT", "field"), ("2027-06-30", "date"), ("nursing", "field"), ("2023", "date")],
     [("BSc", "Open University", "LOCATED_IN")],
     "when does the distance-learning degree wrap up and what led me into it",
     "open university BSc computing finish date nursing pivot start 2023"),
    # --- 6 ---
    ("Prefers the Maven cohort-based courses to the self-paced Coursera specialisations; the live cohorts force me to actually finish the final project.", "preference", "personal", False,
     [("Maven", "platform"), ("Coursera", "platform"), ("cohort-based courses", "concept"), ("final project", "concept")],
     [("Maven", "Coursera", "PREFERS")],
     "which online-learning format wins out and what does it do better",
     "maven cohort over coursera self paced completion final project drive"),
    # --- 7 ---
    ("Paid the Turing School tuition through the deferred-payment agreement; 17% of salary for 24 months once base pay clears $50k after graduation.", "reference", "personal", False,
     [("Turing School", "organization"), ("deferred-payment agreement", "concept"), ("tuition", "concept"), ("graduation", "event")],
     [("deferred-payment agreement", "Turing School", "RELATED_TO")],
     "how did I fund the coding bootcamp and what triggers the repayment",
     "turing school ISA tuition salary percent threshold month term"),
    # --- 8 ---
    ("The AWS Solutions Architect Associate exam passed on 2026-02-11; sat the SAA-C03 version at 780, six months after starting the Stephane Maarek course.", "milestone", "personal", False,
     [("AWS Solutions Architect Associate", "concept"), ("2026-02-11", "date"), ("SAA-C03", "concept"), ("Stephane Maarek", "person")],
     [("AWS Solutions Architect Associate", "SAA-C03", "IS_A")],
     "when did I clear the cloud-architect certification and what prep course fed into it",
     "AWS SAA-C03 pass date score maarek course six month prep"),
    # --- 9 ---
    ("Dropped the Lambda School data-science track in week 14; the live-teaching quality had collapsed after the layoffs and I cut my losses.", "problem", "personal", False,
     [("Lambda School", "organization"), ("data-science track", "concept"), ("week 14", "date"), ("layoffs", "event")],
     [],
     "what unfinished bootcamp did I walk away from and what tipped it",
     "lambda school data science drop week 14 instructor layoff quality"),
    # --- 10. noise ---
    ("Let me pull up the enrolment confirmation email.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The PGCE at Canterbury Christ Church starts 2026-09-07; secondary mathematics route, 120 days in school and two university-based blocks.", "architecture", "personal", False,
     [("PGCE", "concept"), ("Canterbury Christ Church", "organization"), ("2026-09-07", "date"), ("secondary mathematics", "field")],
     [("PGCE", "Canterbury Christ Church", "LOCATED_IN")],
     "how is the teacher-training year structured at the named university",
     "PGCE canterbury christ church maths secondary school days blocks"),
    # --- 12 ---
    ("Chose the Flatiron software engineering immersive over Codesmith; Flatiron's career-services track for non-CS graduates was what sold it.", "decision", "personal", False,
     [("Flatiron", "organization"), ("Codesmith", "organization"), ("software engineering immersive", "concept"), ("career-services track", "concept")],
     [("Flatiron", "Codesmith", "PREFERS")],
     "which programming bootcamp beat the alternative and why",
     "flatiron over codesmith career service non CS graduate immersive"),
    # --- 13 ---
    ("The ACCA qualification route is my path out of bookkeeping into proper management accounting; Fundamentals done in 2025, Strategic Professional exams in 2026.", "architecture", "personal", False,
     [("ACCA", "concept"), ("bookkeeping", "field"), ("management accounting", "field"), ("Fundamentals", "concept"), ("Strategic Professional", "concept"), ("2025", "date"), ("2026", "date")],
     [("Strategic Professional", "Fundamentals", "BUILDS_ON")],
     "how is the chartered-accountancy pivot laid out across the two years",
     "ACCA route bookkeeping to management accounting fundamentals strategic"),
    # --- 14 ---
    ("Returned to the University of Leeds for a part-time MSc in Health Economics on 2026-01-15, 19 years after the original BA finished.", "milestone", "personal", False,
     [("University of Leeds", "organization"), ("MSc", "concept"), ("Health Economics", "field"), ("2026-01-15", "date"), ("BA", "concept")],
     [("MSc", "University of Leeds", "LOCATED_IN")],
     "when did I return to university and how long was the gap",
     "leeds MSc health economics return date gap years BA original"),
    # --- 15 ---
    ("The Reforge Growth Series cohort runs 2026-05-04 through 2026-07-10; six weeks, Tuesday live sessions, small-group sprint teams on Slack.", "reference", "personal", False,
     [("Reforge", "platform"), ("Growth Series", "concept"), ("2026-05-04", "date"), ("2026-07-10", "date"), ("Tuesday", "date"), ("Slack", "platform")],
     [("Growth Series", "Reforge", "LOCATED_IN")],
     "when does the product-growth cohort run and how is it structured each week",
     "reforge growth series cohort date range weekly live slack sprint team"),
    # --- 16 ---
    ("Chose the CIPD Level 5 over an MSc HR; the CIPD had the professional recognition employers wanted and was half the cost.", "decision", "personal", False,
     [("CIPD Level 5", "concept"), ("MSc HR", "concept"), ("professional recognition", "concept")],
     [("CIPD Level 5", "MSc HR", "PREFERS")],
     "which HR credential route won over the academic one and on what grounds",
     "CIPD level 5 over MSc HR professional recognition cost trade"),
    # --- 17 ---
    ("The Cisco CCNA 200-301 exam passed on 2026-04-01 at Reading Pearson Vue; third attempt, the routing subnetting was what finally clicked.", "milestone", "personal", False,
     [("Cisco", "organization"), ("CCNA 200-301", "concept"), ("2026-04-01", "date"), ("Reading", "place"), ("Pearson Vue", "organization"), ("subnetting", "concept")],
     [],
     "when did the network-engineering certification clear and what had been blocking it",
     "CCNA 200-301 pass date third attempt subnetting routing breakthrough"),
    # --- 18 ---
    ("Switched from the part-time MArch at Westminster to the RIBA Studio route after 2025-10; the studio hours on top of client work were crushing me.", "decision", "personal", False,
     [("MArch", "concept"), ("Westminster", "organization"), ("RIBA Studio", "concept"), ("2025-10", "date")],
     [("RIBA Studio", "MArch", "REPLACES")],
     "which architectural-qualification route replaced the other and why",
     "MArch westminster swap RIBA studio workload client late 2025"),
    # --- 19 ---
    ("The legal apprenticeship with Kennedys started 2026-02-03; six-year solicitor apprenticeship, zero tuition fees, salary from day one at £24k.", "milestone", "personal", False,
     [("legal apprenticeship", "concept"), ("Kennedys", "organization"), ("2026-02-03", "date"), ("solicitor apprenticeship", "concept")],
     [("solicitor apprenticeship", "Kennedys", "LOCATED_IN")],
     "when did the solicitor route begin and what are the financial terms",
     "legal apprenticeship kennedys start date six year salary no tuition"),
    # --- 20 ---
    ("Prefers the in-person CFA Level 1 Kaplan weekend classes to the online Schweser videos; the discipline of a physical room matters for a 10-month slog.", "preference", "personal", False,
     [("CFA Level 1", "concept"), ("Kaplan", "organization"), ("Schweser", "organization"), ("weekend classes", "event")],
     [("Kaplan", "Schweser", "PREFERS")],
     "which CFA prep format wins out and why the long study matters",
     "CFA level 1 kaplan weekend over schweser video discipline commitment"),
    # --- 21 ---
    ("The CPA Exam REG section cleared on 2026-03-18 with a 78; only FAR left before the Illinois board closes my candidacy window in November.", "milestone", "personal", False,
     [("CPA Exam", "concept"), ("REG", "concept"), ("2026-03-18", "date"), ("FAR", "concept"), ("Illinois board", "organization"), ("November", "date")],
     [("REG", "CPA Exam", "HAS_PART"), ("FAR", "CPA Exam", "HAS_PART")],
     "which CPA section cleared and which one still blocks completion before the window",
     "CPA REG pass date FAR remaining illinois candidacy window november"),
    # --- 22 ---
    ("The General Assembly UX Immersive cost £11,500 through the Career Development Loan; 12 weeks full-time, finished 2025-11-28 with the portfolio showcase.", "reference", "personal", False,
     [("General Assembly", "organization"), ("UX Immersive", "concept"), ("Career Development Loan", "concept"), ("2025-11-28", "date"), ("portfolio showcase", "event")],
     [("UX Immersive", "General Assembly", "LOCATED_IN")],
     "how did I fund the design bootcamp and when did it wrap up",
     "general assembly UX immersive fee career development loan finish date"),
    # --- 23 ---
    ("Chose the part-time MSc Computer Science at Birkbeck over UCL's evening course; Birkbeck's later starting hour actually worked with the day job.", "decision", "personal", False,
     [("MSc Computer Science", "concept"), ("Birkbeck", "organization"), ("UCL", "organization"), ("evening course", "concept")],
     [("Birkbeck", "UCL", "PREFERS")],
     "which part-time CS master won over the alternative and why",
     "birkbeck over UCL MSc computer science evening schedule day job fit"),
    # --- 24 ---
    ("The Google UX Design Certificate on Coursera finished on 2025-10-05 after six months; useful as an on-ramp but did not get interviews on its own.", "problem", "personal", False,
     [("Google UX Design Certificate", "concept"), ("Coursera", "platform"), ("2025-10-05", "date"), ("interviews", "event")],
     [("Google UX Design Certificate", "Coursera", "LOCATED_IN")],
     "when did the MOOC certificate complete and how did it play with recruiters",
     "google UX certificate coursera finish date interview traction limit"),
    # --- 25 ---
    ("The Microsoft Azure Administrator AZ-104 certification replaced my stale MCSE credential on 2026-01-08; the MCSE had been retired for years.", "decision", "personal", False,
     [("Microsoft Azure Administrator", "concept"), ("AZ-104", "concept"), ("MCSE", "concept"), ("2026-01-08", "date")],
     [("AZ-104", "MCSE", "REPLACES")],
     "which current cloud credential took over from the retired Microsoft one",
     "AZ-104 azure admin replace MCSE stale retire certification date"),
    # --- 26 ---
    ("The Ironhack data analytics bootcamp in Madrid starts 2026-10-05; relocating for 10 weeks on an unpaid sabbatical from the council job.", "milestone", "personal", False,
     [("Ironhack", "organization"), ("data analytics bootcamp", "concept"), ("Madrid", "place"), ("2026-10-05", "date"), ("sabbatical", "event"), ("council job", "concept")],
     [("Ironhack", "Madrid", "LOCATED_IN")],
     "when does the data bootcamp start and what work arrangement covers it",
     "ironhack madrid data analytics bootcamp start date sabbatical council"),
    # --- 27 ---
    ("The route from secondary-school teacher to product manager went through the Mind the Product Leadership course and two internal transfers at the publisher.", "fact", "personal", False,
     [("secondary-school teacher", "person"), ("product manager", "person"), ("Mind the Product", "organization"), ("publisher", "organization")],
     [("product manager", "secondary-school teacher", "REPLACES")],
     "which formal course mediated the teacher-to-PM pivot and where did it land",
     "teacher to product manager path mind the product leadership publisher"),
    # --- 28 ---
    ("Prefers the Springboard mentor-led data science track to the DataCamp self-guided path; the weekly mentor call is the only reason the projects ship.", "preference", "personal", False,
     [("Springboard", "organization"), ("DataCamp", "platform"), ("data science track", "concept"), ("mentor call", "event")],
     [("Springboard", "DataCamp", "PREFERS")],
     "which data-science learning platform wins out and what drives the choice",
     "springboard mentor led over datacamp self guided weekly call completion"),
    # --- 29 ---
    ("The Institute of Chartered Accountants of Scotland TPS exam failed on 2026-03-29; resit is scheduled for 2026-06-14 with a different study planner.", "problem", "personal", False,
     [("Institute of Chartered Accountants of Scotland", "organization"), ("TPS", "concept"), ("2026-03-29", "date"), ("2026-06-14", "date"), ("study planner", "tool")],
     [],
     "which accountancy exam did I fail and when is the retake booked",
     "ICAS TPS fail date resit schedule different study planner retry"),
    # --- 30 ---
    ("The MBA application to London Business School went in on 2026-01-20; two recommenders from previous roles, GMAT 720, essays on the career pivot from medicine.", "milestone", "personal", False,
     [("MBA", "concept"), ("London Business School", "organization"), ("2026-01-20", "date"), ("GMAT", "concept"), ("medicine", "field")],
     [("MBA", "London Business School", "LOCATED_IN")],
     "when did the top-school MBA application go in and what was the pitch",
     "LBS MBA application date GMAT score medicine pivot recommender"),
    # --- 31 ---
    ("Chose the Executive MBA at IE Business School over the full-time programme; leaving clinical work for two years was not survivable financially.", "decision", "personal", False,
     [("Executive MBA", "concept"), ("IE Business School", "organization"), ("full-time programme", "concept"), ("clinical work", "activity")],
     [("Executive MBA", "full-time programme", "PREFERS")],
     "which MBA format won out and what forced the call",
     "executive MBA IE over full time clinical income gap two year"),
    # --- 32 ---
    ("The Terraform Associate 003 exam passed on 2026-02-27 at 89%; completed HashiCorp's own learn path plus two practice exams from Bryan Krausen.", "milestone", "personal", False,
     [("Terraform Associate 003", "concept"), ("2026-02-27", "date"), ("HashiCorp", "organization"), ("Bryan Krausen", "person")],
     [("Terraform Associate 003", "HashiCorp", "RELATED_TO")],
     "when did the infrastructure-as-code certification clear and what prep fed it",
     "terraform associate 003 pass date score hashicorp learn krausen practice"),
    # --- 33 ---
    ("The Kellogg MMM dual-degree deadline on 2026-01-05 was missed by six hours; resubmitting for the Round 2 deadline on 2026-03-12 instead.", "problem", "personal", False,
     [("Kellogg MMM", "concept"), ("2026-01-05", "date"), ("Round 2", "event"), ("2026-03-12", "date")],
     [],
     "which MBA deadline slipped and what is the fallback submission date",
     "kellogg MMM deadline miss late round 2 resubmit date"),
    # --- 34. noise ---
    ("I'll grab the transcript and come back in five minutes.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Hyper Island Digital Data Strategist diploma in Stockholm runs 2026-08-24 through 2027-06-11; nine months, project-based, no written exams.", "architecture", "personal", False,
     [("Hyper Island", "organization"), ("Digital Data Strategist", "concept"), ("Stockholm", "place"), ("2026-08-24", "date"), ("2027-06-11", "date")],
     [("Hyper Island", "Stockholm", "LOCATED_IN")],
     "how is the Nordic digital diploma structured across the year",
     "hyper island stockholm data strategist diploma date range project based"),
    # --- 36 ---
    ("The Oxford Saïd Diploma in Financial Strategy is my pivot from treasury analyst into corporate finance; six modules, 18 months, evenings in Oxford.", "milestone", "personal", False,
     [("Oxford Saïd", "organization"), ("Diploma in Financial Strategy", "concept"), ("treasury analyst", "person"), ("corporate finance", "field"), ("Oxford", "place")],
     [("Diploma in Financial Strategy", "Oxford Saïd", "LOCATED_IN")],
     "which executive diploma is carrying my shift from treasury to corporate finance",
     "oxford said diploma financial strategy treasury pivot module length"),
    # --- 37 ---
    ("Prefers the Pluralsight skill-path certificates to the random Udemy courses for the AZ-500 security track; assessment gating actually measures retention.", "preference", "personal", False,
     [("Pluralsight", "platform"), ("Udemy", "platform"), ("AZ-500", "concept"), ("skill-path", "concept")],
     [("Pluralsight", "Udemy", "PREFERS")],
     "which learning platform wins out for the security-track prep and why",
     "pluralsight skill path over udemy AZ-500 assessment gate retention"),
    # --- 38 ---
    ("The engineering-to-law jump went through the GDL at the University of Law on 2025-09-15; distance learning for the day-job years, then the SQE1 in 2027.", "architecture", "personal", False,
     [("GDL", "concept"), ("University of Law", "organization"), ("2025-09-15", "date"), ("SQE1", "concept"), ("2027", "date")],
     [("GDL", "University of Law", "LOCATED_IN"), ("SQE1", "GDL", "BUILDS_ON")],
     "how is the engineering-to-law pivot sequenced across the qualifications",
     "GDL university of law start date SQE1 2027 engineering law pivot"),
    # --- 39 ---
    ("The BIMM music production diploma final project premieres on 2026-06-20 at the Hackney showcase; two-year part-time programme, fourth career now.", "milestone", "personal", False,
     [("BIMM", "organization"), ("music production", "field"), ("2026-06-20", "date"), ("Hackney", "place"), ("showcase", "event")],
     [("showcase", "Hackney", "LOCATED_IN")],
     "when does my music-production capstone premiere and where",
     "BIMM music production diploma final project showcase date hackney"),
    # --- 40 ---
    ("Replaced the Codecademy Pro subscription with the Frontend Masters learning path on 2025-12-01; the Masters content is deeper and tracks industry practice.", "decision", "personal", False,
     [("Codecademy Pro", "platform"), ("Frontend Masters", "platform"), ("2025-12-01", "date"), ("learning path", "concept")],
     [("Frontend Masters", "Codecademy Pro", "REPLACES")],
     "which front-end learning subscription took over and on what grounds",
     "frontend masters replace codecademy pro date depth industry practice"),
    # --- 41 ---
    ("The Stanford LEAD certificate finished on 2026-02-28; 12 months, 100% online, admitted as a mid-career operations director with nine years of line management.", "milestone", "personal", False,
     [("Stanford LEAD", "concept"), ("2026-02-28", "date"), ("operations director", "person"), ("line management", "field")],
     [],
     "when did the Stanford online business certificate close and on what profile",
     "stanford LEAD finish date operations director mid career line management"),
    # --- 42 ---
    ("Chose the NHS Graduate Management Training Scheme finance specialism over a private graduate programme; the pension and union protections closed it out.", "decision", "personal", False,
     [("NHS Graduate Management Training Scheme", "organization"), ("finance specialism", "field"), ("private graduate programme", "concept"), ("pension", "concept"), ("union", "organization")],
     [("NHS Graduate Management Training Scheme", "private graduate programme", "PREFERS")],
     "which graduate programme won out and what tipped the decision",
     "NHS graduate management scheme finance over private pension union call"),
    # --- 43 ---
    ("Prefers the Harvard HBX CORe programme to the Wharton Online alternative for the finance fundamentals gap; HBX's case discussions felt closer to the real room.", "preference", "personal", False,
     [("Harvard HBX CORe", "concept"), ("Wharton Online", "organization"), ("finance fundamentals", "field"), ("case discussions", "method")],
     [("Harvard HBX CORe", "Wharton Online", "PREFERS")],
     "which online business fundamentals programme wins over the other and why",
     "HBX core over wharton online finance fundamentals case discussion real"),
    # --- 44 ---
    ("The Open Classrooms mentor-led path to developer career finished on 2025-12-15; six projects, nine months, all funded by the France Travail Compte Personnel de Formation.", "reference", "personal", False,
     [("Open Classrooms", "organization"), ("developer", "person"), ("2025-12-15", "date"), ("France Travail", "organization"), ("Compte Personnel de Formation", "concept")],
     [("Compte Personnel de Formation", "France Travail", "RELATED_TO")],
     "when did the mentor-led developer path finish and how was it funded",
     "open classrooms mentor developer finish date france travail CPF funding"),
    # --- 45 ---
    ("The Praxis apprenticeship year placed me at a Columbus marketing firm from 2025-09-02; alternative to a four-year college, one year structured placement then a hiring decision.", "architecture", "personal", False,
     [("Praxis", "organization"), ("Columbus", "place"), ("2025-09-02", "date"), ("four-year college", "concept"), ("hiring decision", "event")],
     [("Praxis", "four-year college", "REPLACES")],
     "how is the apprenticeship alternative to college structured and where did I land",
     "praxis apprenticeship columbus marketing firm structured year hire decision"),
    # --- 46 ---
    ("Chose the CFA ESG Investing certificate over the GARP SCR; the CFA letters already carried weight and the ESG add-on was cheaper to bolt on.", "decision", "personal", False,
     [("CFA ESG Investing certificate", "concept"), ("GARP SCR", "concept"), ("CFA", "concept"), ("ESG", "field")],
     [("CFA ESG Investing certificate", "GARP SCR", "PREFERS")],
     "which sustainability-finance credential won out over the alternative and why",
     "CFA ESG certificate over GARP SCR letter carry cheap bolt on"),
    # --- 47 ---
    ("The ICAEW ACA training contract with BDO runs 2026-09-01 through 2029-08-31; three years, level-7 apprenticeship, 450 study days across the period.", "reference", "personal", False,
     [("ICAEW ACA", "concept"), ("BDO", "organization"), ("2026-09-01", "date"), ("2029-08-31", "date"), ("level-7 apprenticeship", "concept")],
     [("ICAEW ACA", "BDO", "LOCATED_IN")],
     "how is the chartered-accountant training contract structured over the term",
     "ICAEW ACA training contract BDO date range study days level 7"),
    # --- 48 ---
    ("Prefers the Metis data science bootcamp alumni network to the Galvanize network; four hires came through Metis slack channels, none from Galvanize.", "preference", "personal", False,
     [("Metis", "organization"), ("Galvanize", "organization"), ("alumni network", "concept"), ("slack channels", "platform")],
     [("Metis", "Galvanize", "PREFERS")],
     "which bootcamp's alumni network wins out in practice and by what measure",
     "metis over galvanize alumni network slack hire count outcome"),
    # --- 49 ---
    ("The MSc Data Science at City, University of London withdrew my application on 2026-02-14 for a missing Maths A-level equivalence; resubmitting through the ALC route.", "problem", "personal", False,
     [("MSc Data Science", "concept"), ("City, University of London", "organization"), ("2026-02-14", "date"), ("Maths A-level", "concept"), ("ALC", "concept")],
     [("MSc Data Science", "City, University of London", "LOCATED_IN")],
     "what blocked the data-science masters application and what is the workaround",
     "city university MSc data science reject math A level ALC resubmit"),
    # --- 50 ---
    ("The Hack Reactor software engineering programme on-site interview on 2026-04-22 at 14:00 decides the July 2026 cohort slot; JavaScript technical plus culture fit.", "reference", "personal", False,
     [("Hack Reactor", "organization"), ("software engineering programme", "concept"), ("2026-04-22", "date"), ("July 2026", "date"), ("JavaScript", "language"), ("culture fit", "concept")],
     [("software engineering programme", "Hack Reactor", "LOCATED_IN")],
     "when is the bootcamp interview and what does it gate into",
     "hack reactor interview date july 2026 cohort javascript technical culture"),
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
