"""One-off emitter for classification top-up batch-003.

Produces 100 rows (50 pairs) in contrastive_reference_fact mode, legal
and policy slice. Each pair contains one `reference` row citing a real
statute, case, treaty, or regulation, paired with a `fact` row asserting
the same underlying legal fact without the citation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_003.tmp.jsonl"

ID_OFFSET = 200
PAIR_OFFSET = 100

# Each pair: (ref_text, ref_domain, fact_text, fact_domain)
PAIRS: list[tuple[str, str, str, str]] = [
    # --- 1. Constitutional: judicial review ---
    ("Marbury v. Madison (1803) established the principle that the Supreme Court has the power to strike down acts of Congress that conflict with the Constitution.",
     "knowledge",
     "The Supreme Court has the power to invalidate federal laws that it finds to be unconstitutional.",
     "knowledge"),
    # --- 2. Constitutional: segregation ---
    ("Brown v. Board of Education (1954) held that racial segregation of children in public schools is unconstitutional.",
     "knowledge",
     "Racial segregation of students in public schools violates the constitutional guarantee of equal protection.",
     "knowledge"),
    # --- 3. Constitutional: Miranda warnings ---
    ("Miranda v. Arizona (1966) requires police to inform suspects in custody of their right to remain silent and their right to an attorney before interrogation.",
     "knowledge",
     "Before questioning a person held in custody, the police must notify them of their right to stay silent and to have a lawyer present.",
     "knowledge"),
    # --- 4. Data protection: right to erasure ---
    ("Article 17 of the General Data Protection Regulation grants data subjects the right to obtain the erasure of their personal data without undue delay.",
     "knowledge",
     "Individuals in the European Union may require a controller to delete their personal data without undue delay.",
     "knowledge"),
    # --- 5. Data protection: lawful basis ---
    ("Article 6 of the General Data Protection Regulation enumerates the six lawful bases on which personal data may be processed.",
     "knowledge",
     "Processing personal data in the European Union is only lawful if it rests on one of six enumerated legal grounds.",
     "knowledge"),
    # --- 6. Internet platform immunity ---
    ("Section 230 of the Communications Decency Act shields interactive computer service providers from being treated as the publisher of content posted by their users.",
     "knowledge",
     "Online platforms in the United States are generally not liable as publishers for content that third-party users post on them.",
     "knowledge"),
    # --- 7. Intellectual property: copyright term ---
    ("17 U.S.C. section 302 fixes the term of copyright for works created on or after January 1, 1978 at the life of the author plus seventy years.",
     "knowledge",
     "Copyright in the United States for works created after 1977 lasts for the life of the author plus seventy years.",
     "knowledge"),
    # --- 8. Intellectual property: fair use ---
    ("17 U.S.C. section 107 codifies the fair use defense to copyright infringement and lists the four factors courts weigh.",
     "knowledge",
     "Using a copyrighted work without permission may be permitted in the United States if the use qualifies as fair use under a four-factor balancing test.",
     "knowledge"),
    # --- 9. Patents: novelty ---
    ("35 U.S.C. section 102 bars the patenting of inventions that were already publicly known, used, patented, or described in a printed publication before the effective filing date.",
     "knowledge",
     "An invention cannot receive a United States patent if it was publicly disclosed before the application's effective filing date.",
     "knowledge"),
    # --- 10. Trademarks ---
    ("The Lanham Act, codified at 15 U.S.C. sections 1051 and following, governs federal trademark registration and infringement in the United States.",
     "knowledge",
     "Federal trademark registration and infringement claims in the United States are governed by a single statutory scheme.",
     "knowledge"),
    # --- 11. Contract law: UCC goods ---
    ("Section 2-201 of the Uniform Commercial Code requires contracts for the sale of goods for $500 or more to be in writing to be enforceable.",
     "knowledge",
     "A contract to sell goods worth five hundred dollars or more must generally be evidenced by a writing to be enforceable in most United States jurisdictions.",
     "knowledge"),
    # --- 12. Contract law: perfect tender ---
    ("Section 2-601 of the Uniform Commercial Code allows a buyer to reject goods that fail in any respect to conform to the contract.",
     "knowledge",
     "A buyer of goods may reject the entire shipment if it deviates in any respect from what the contract required.",
     "knowledge"),
    # --- 13. Contract law: consideration ---
    ("The Restatement (Second) of Contracts section 71 defines consideration as a performance or return promise that is bargained for.",
     "knowledge",
     "A promise is enforceable as a contract only if each party bargains for and gives something of legal value in exchange.",
     "knowledge"),
    # --- 14. Tort: negligence standard ---
    ("Palsgraf v. Long Island Railroad Co. (1928) limited a defendant's negligence liability to plaintiffs within the foreseeable zone of danger.",
     "knowledge",
     "A defendant's duty of care in negligence extends only to plaintiffs whose injury was a foreseeable consequence of the defendant's conduct.",
     "knowledge"),
    # --- 15. Tort: products liability ---
    ("Section 402A of the Restatement (Second) of Torts imposes strict liability on sellers of products that are in a defective condition unreasonably dangerous to the user.",
     "knowledge",
     "A seller is strictly liable for harm caused by a product sold in a defective condition that is unreasonably dangerous to the consumer.",
     "knowledge"),
    # --- 16. Criminal: insanity ---
    ("M'Naghten's Case (1843) set out the common law test that a defendant is not criminally responsible if, due to mental disease, they did not know the nature of the act or that it was wrong.",
     "knowledge",
     "Under the traditional common law insanity test, a defendant is not criminally responsible when a mental disease prevents them from knowing the nature or wrongfulness of the act.",
     "knowledge"),
    # --- 17. Criminal: exclusionary rule ---
    ("Mapp v. Ohio (1961) applied the Fourth Amendment exclusionary rule to state criminal prosecutions through the Fourteenth Amendment.",
     "knowledge",
     "Evidence obtained in violation of constitutional search and seizure protections is inadmissible in state criminal trials.",
     "knowledge"),
    # --- 18. Criminal: right to counsel ---
    ("Gideon v. Wainwright (1963) held that the Sixth Amendment guarantees indigent criminal defendants the right to appointed counsel in state felony cases.",
     "knowledge",
     "An indigent person charged with a state felony has a constitutional right to have an attorney appointed at public expense.",
     "knowledge"),
    # --- 19. International: Refugee Convention ---
    ("Article 33 of the 1951 Refugee Convention prohibits the expulsion or return of a refugee to a territory where their life or freedom would be threatened.",
     "knowledge",
     "A state party to the main international refugee treaty may not send a refugee back to a country where their life or freedom would be at risk.",
     "knowledge"),
    # --- 20. International: Geneva Conventions ---
    ("Common Article 3 of the 1949 Geneva Conventions prohibits violence, torture, and outrages upon personal dignity against persons not taking active part in hostilities.",
     "knowledge",
     "International humanitarian law forbids torture and degrading treatment of civilians and other persons who are not actively participating in an armed conflict.",
     "knowledge"),
    # --- 21. International: Vienna Convention on Treaties ---
    ("Article 26 of the Vienna Convention on the Law of Treaties codifies the pacta sunt servanda rule that every treaty in force binds its parties and must be performed in good faith.",
     "knowledge",
     "Every treaty in force obliges its parties to perform their obligations in good faith.",
     "knowledge"),
    # --- 22. International: UN Charter force ---
    ("Article 2(4) of the United Nations Charter prohibits member states from using force against the territorial integrity or political independence of any state.",
     "knowledge",
     "Member states of the United Nations are forbidden from using armed force against another state's territorial integrity or political independence.",
     "knowledge"),
    # --- 23. Environmental: NEPA ---
    ("The National Environmental Policy Act of 1969 requires federal agencies to prepare an environmental impact statement for major federal actions significantly affecting the environment.",
     "knowledge",
     "United States federal agencies must produce a detailed environmental impact statement before taking major actions that significantly affect the environment.",
     "knowledge"),
    # --- 24. Environmental: Clean Air Act ---
    ("Section 109 of the Clean Air Act directs the Environmental Protection Agency to set National Ambient Air Quality Standards for criteria pollutants.",
     "knowledge",
     "The federal environmental regulator must establish nationwide ambient air quality standards for designated pollutants.",
     "knowledge"),
    # --- 25. Environmental: Paris Agreement ---
    ("Article 2 of the Paris Agreement commits parties to holding the increase in global average temperature to well below 2 degrees Celsius above pre-industrial levels.",
     "knowledge",
     "Parties to the landmark international climate accord have agreed to keep global average warming well below two degrees Celsius above pre-industrial levels.",
     "knowledge"),
    # --- 26. Administrative: Chevron ---
    ("Chevron U.S.A., Inc. v. Natural Resources Defense Council (1984) required courts to defer to a federal agency's reasonable interpretation of an ambiguous statute it administers.",
     "knowledge",
     "Courts historically deferred to reasonable agency interpretations when the statute an agency administers is ambiguous.",
     "knowledge"),
    # --- 27. Administrative: APA rulemaking ---
    ("Section 553 of the Administrative Procedure Act requires federal agencies to provide notice of proposed rulemaking and an opportunity for public comment.",
     "knowledge",
     "Federal agencies in the United States must generally publish a notice of proposed rulemaking and accept public comments before issuing binding regulations.",
     "knowledge"),
    # --- 28. Tax: income ---
    ("Section 61 of the Internal Revenue Code defines gross income as all income from whatever source derived.",
     "knowledge",
     "For United States federal income tax purposes, gross income broadly includes income from any source unless a specific exception applies.",
     "knowledge"),
    # --- 29. Tax: charitable deduction ---
    ("Section 170 of the Internal Revenue Code permits individual taxpayers to deduct qualifying contributions to charitable organizations, subject to percentage limits.",
     "knowledge",
     "United States individual taxpayers may deduct charitable contributions to qualifying organizations up to statutory percentage limits.",
     "knowledge"),
    # --- 30. Tax: capital gains ---
    ("Section 1221 of the Internal Revenue Code defines a capital asset for purposes of computing capital gains and losses.",
     "knowledge",
     "United States tax law provides a statutory definition of a capital asset used when computing capital gains and losses.",
     "knowledge"),
    # --- 31. Employment: Title VII ---
    ("Title VII of the Civil Rights Act of 1964 prohibits employers with fifteen or more employees from discriminating on the basis of race, color, religion, sex, or national origin.",
     "knowledge",
     "Employers in the United States above a size threshold may not discriminate in employment based on race, color, religion, sex, or national origin.",
     "knowledge"),
    # --- 32. Employment: ADA ---
    ("The Americans with Disabilities Act of 1990 requires covered employers to provide reasonable accommodations to qualified employees with disabilities unless doing so causes undue hardship.",
     "knowledge",
     "United States employers must provide reasonable workplace accommodations to qualified disabled employees unless the accommodation would impose undue hardship.",
     "knowledge"),
    # --- 33. Employment: FLSA ---
    ("Section 207 of the Fair Labor Standards Act requires employers to pay non-exempt employees overtime at one and one-half times the regular rate for hours worked beyond forty in a workweek.",
     "knowledge",
     "Non-exempt United States workers must be paid overtime at time and a half for hours worked beyond forty in a single workweek.",
     "knowledge"),
    # --- 34. Employment: NLRA ---
    ("Section 7 of the National Labor Relations Act protects the right of employees to engage in concerted activities for mutual aid or protection.",
     "knowledge",
     "Private-sector workers in the United States have a protected legal right to act together for mutual aid or protection.",
     "knowledge"),
    # --- 35. Securities: 10b-5 ---
    ("Rule 10b-5 under the Securities Exchange Act of 1934 prohibits fraud, misrepresentation, and deceit in connection with the purchase or sale of any security.",
     "knowledge",
     "United States securities law prohibits fraudulent or deceptive conduct in connection with any securities transaction.",
     "knowledge"),
    # --- 36. Securities: registration ---
    ("Section 5 of the Securities Act of 1933 generally prohibits the offer or sale of securities unless a registration statement is in effect, absent an exemption.",
     "knowledge",
     "Issuers may not offer or sell securities to the United States public unless the offering is registered or qualifies for an exemption.",
     "knowledge"),
    # --- 37. Antitrust ---
    ("Section 1 of the Sherman Antitrust Act of 1890 makes illegal every contract, combination, or conspiracy in restraint of trade or commerce.",
     "knowledge",
     "Any agreement that unreasonably restrains trade or commerce is illegal under United States antitrust law.",
     "knowledge"),
    # --- 38. Bankruptcy: automatic stay ---
    ("Section 362 of the Bankruptcy Code imposes an automatic stay on most collection actions against a debtor upon the filing of a bankruptcy petition.",
     "knowledge",
     "Filing a bankruptcy petition in the United States automatically halts most collection actions against the debtor.",
     "knowledge"),
    # --- 39. Bankruptcy: Chapter 7 discharge ---
    ("Section 727 of the Bankruptcy Code grants an individual debtor a discharge of most prepetition debts in a Chapter 7 liquidation case.",
     "knowledge",
     "An individual who completes a liquidation bankruptcy in the United States generally receives a discharge of most prepetition debts.",
     "knowledge"),
    # --- 40. Property: adverse possession ---
    ("The doctrine of adverse possession, as set out in the Restatement (First) of Property section 222, allows a possessor of land to acquire title through open, notorious, continuous, and hostile possession for the statutory period.",
     "knowledge",
     "A person who openly, notoriously, continuously, and hostilely possesses land for the statutory period can acquire legal title to it.",
     "knowledge"),
    # --- 41. Immigration: asylum ---
    ("Section 208 of the Immigration and Nationality Act authorizes the grant of asylum to an applicant who qualifies as a refugee.",
     "knowledge",
     "A person in the United States who meets the legal definition of a refugee may be granted asylum by the government.",
     "knowledge"),
    # --- 42. Civil procedure: federal jurisdiction ---
    ("28 U.S.C. section 1332 grants federal district courts diversity jurisdiction over civil actions between citizens of different states where the amount in controversy exceeds $75,000.",
     "knowledge",
     "United States federal district courts may hear civil suits between citizens of different states when more than seventy-five thousand dollars is at stake.",
     "knowledge"),
    # --- 43. Civil procedure: FRCP 12(b)(6) ---
    ("Rule 12(b)(6) of the Federal Rules of Civil Procedure permits a defendant to move to dismiss a complaint for failure to state a claim upon which relief can be granted.",
     "knowledge",
     "A defendant in a United States federal civil case can seek early dismissal of a complaint that does not state a legally sufficient claim.",
     "knowledge"),
    # --- 44. Evidence: hearsay ---
    ("Rule 802 of the Federal Rules of Evidence generally renders hearsay inadmissible unless an exception applies.",
     "knowledge",
     "Out-of-court statements offered for the truth of the matter asserted are generally inadmissible in federal court unless an exception applies.",
     "knowledge"),
    # --- 45. Family: same-sex marriage ---
    ("Obergefell v. Hodges (2015) held that the Fourteenth Amendment requires all states to license and recognize marriages between two people of the same sex.",
     "knowledge",
     "States in the United States must issue marriage licenses to same-sex couples and recognize such marriages validly performed elsewhere.",
     "knowledge"),
    # --- 46. Health privacy ---
    ("The Health Insurance Portability and Accountability Act of 1996 Privacy Rule, codified at 45 C.F.R. Part 164, restricts the uses and disclosures of protected health information by covered entities.",
     "knowledge",
     "Covered healthcare providers and insurers in the United States face regulatory limits on how they may use and disclose a patient's health information.",
     "knowledge"),
    # --- 47. Consumer privacy ---
    ("The California Consumer Privacy Act of 2018, codified at California Civil Code section 1798.100 and following, grants California residents the right to know what personal information businesses collect about them.",
     "knowledge",
     "Residents of California have a legal right to request from businesses the categories and specific pieces of personal information collected about them.",
     "knowledge"),
    # --- 48. Human rights: ECHR ---
    ("Article 8 of the European Convention on Human Rights protects the right to respect for private and family life, home, and correspondence.",
     "knowledge",
     "States parties to the main European human rights treaty must respect individuals' private and family life, home, and correspondence.",
     "knowledge"),
    # --- 49. International trade ---
    ("Article I of the General Agreement on Tariffs and Trade sets out the most-favored-nation obligation that any advantage granted to one contracting party must be extended to all others.",
     "knowledge",
     "Under the foundational multilateral trade treaty, any trade advantage one state grants must be extended unconditionally to all other state parties.",
     "knowledge"),
    # --- 50. Extradition: UN torture convention ---
    ("Article 3 of the United Nations Convention against Torture prohibits state parties from expelling, returning, or extraditing a person to a state where there are substantial grounds for believing they would be subjected to torture.",
     "knowledge",
     "A state may not deport or extradite a person to a country where they would face a substantial risk of being tortured.",
     "knowledge"),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (ref_text, ref_domain, fact_text, fact_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            ref_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            fact_id = f"class-{ID_OFFSET + (2 * i):05d}"
            ref_row = {
                "id": ref_id,
                "domain": ref_domain,
                "text": ref_text,
                "memory_type": "reference",
                "pair_id": pair_id,
            }
            fact_row = {
                "id": fact_id,
                "domain": fact_domain,
                "text": fact_text,
                "memory_type": "fact",
                "pair_id": pair_id,
            }
            f.write(json.dumps(ref_row, ensure_ascii=False) + "\n")
            f.write(json.dumps(fact_row, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
