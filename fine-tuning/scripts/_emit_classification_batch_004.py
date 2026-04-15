"""Classification top-up batch-004 — contrastive_reference_fact mode, medical & public-health slice.

Each pair has one `reference` row citing a named trial/guideline/journal/body and one
`fact` row stating the same underlying health fact without the citation. 50 pairs -> 100 rows.

Writes to data/v2/classification/batch_004.tmp.jsonl with ids class-00301..class-00400 and
pair ids cls-pair-00151..cls-pair-00200.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_004.tmp.jsonl"
ID_OFFSET = 300
PAIR_OFFSET = 150

# Each entry: (ref_text, ref_domain, fact_text, fact_domain)
PAIRS: list[tuple[str, str, str, str]] = [
    # 1 — cardiovascular — SPRINT trial
    (
        "The SPRINT trial published in NEJM in 2015 found that targeting systolic blood pressure below 120 mmHg cut major cardiovascular events by about 25 percent versus the standard target of 140 mmHg in high-risk non-diabetic adults.",
        "knowledge",
        "Driving systolic blood pressure below 120 mmHg in high-risk non-diabetic adults reduces major cardiovascular events by roughly a quarter compared with the usual 140 mmHg target.",
        "knowledge",
    ),
    # 2 — cardiovascular — statins, CTT meta-analysis
    (
        "The Cholesterol Treatment Trialists' Collaboration meta-analysis in The Lancet showed that each 1 mmol/L reduction in LDL cholesterol on statin therapy produces roughly a 22 percent drop in major vascular events per year of treatment.",
        "knowledge",
        "Every 1 mmol/L that statins pull LDL cholesterol down translates into about a 22 percent lower annual rate of major vascular events.",
        "knowledge",
    ),
    # 3 — cardiovascular — aspirin primary prevention, ASPREE
    (
        "The ASPREE trial reported in NEJM in 2018 that daily low-dose aspirin in healthy older adults did not reduce cardiovascular events but did raise major bleeding, arguing against routine primary prevention aspirin over age 70.",
        "knowledge",
        "For healthy adults over 70, taking low-dose aspirin every day does not lower heart attack or stroke risk and noticeably increases major bleeding, so it is no longer recommended for primary prevention.",
        "knowledge",
    ),
    # 4 — oncology — mammography, USPSTF
    (
        "The USPSTF 2024 recommendation statement now advises biennial screening mammography for women aged 40 to 74 at average risk, a shift from the prior age 50 start.",
        "knowledge",
        "Average-risk women should start getting a screening mammogram every two years from age 40, not from 50 as previously advised.",
        "knowledge",
    ),
    # 5 — oncology — colorectal screening, USPSTF
    (
        "The USPSTF 2021 guideline lowered the recommended starting age for colorectal cancer screening from 50 to 45 for average-risk adults, citing rising early-onset incidence.",
        "knowledge",
        "Routine colorectal cancer screening should now begin at age 45 rather than 50 for adults at average risk.",
        "knowledge",
    ),
    # 6 — oncology — HPV vaccination, Cochrane
    (
        "A Cochrane systematic review of HPV vaccine randomized trials concluded that vaccinating adolescent girls before sexual debut substantially reduces the incidence of high-grade cervical intraepithelial neoplasia.",
        "knowledge",
        "Vaccinating adolescent girls against HPV before they become sexually active sharply cuts the rate of high-grade cervical precancerous lesions.",
        "knowledge",
    ),
    # 7 — oncology — lung cancer screening, NLST
    (
        "The National Lung Screening Trial, reported in NEJM in 2011, showed that low-dose CT screening reduced lung cancer mortality by 20 percent compared with chest X-ray in heavy-smoking adults aged 55 to 74.",
        "knowledge",
        "Heavy smokers aged 55 to 74 who get annual low-dose CT scans are about 20 percent less likely to die from lung cancer than those screened only with chest X-ray.",
        "knowledge",
    ),
    # 8 — infectious disease — measles vaccine, WHO
    (
        "The WHO position paper on measles vaccines states that two doses of measles-containing vaccine confer roughly 97 percent protection against measles and are required for herd immunity thresholds around 95 percent coverage.",
        "knowledge",
        "Two doses of a measles vaccine give about 97 percent individual protection, and reaching herd immunity against measles needs roughly 95 percent community coverage.",
        "knowledge",
    ),
    # 9 — infectious disease — HIV PrEP, iPrEx
    (
        "The iPrEx trial published in NEJM in 2010 demonstrated that daily oral tenofovir-emtricitabine reduced HIV acquisition by 44 percent overall and by more than 90 percent among participants with detectable drug levels.",
        "knowledge",
        "Taking daily oral tenofovir-emtricitabine as PrEP cuts HIV acquisition by about 44 percent on average and by over 90 percent in people who actually take it consistently.",
        "knowledge",
    ),
    # 10 — infectious disease — COVID mRNA vaccine, Polack et al.
    (
        "Polack and colleagues reported in NEJM in 2020 that two doses of the BNT162b2 mRNA COVID-19 vaccine conferred 95 percent efficacy against symptomatic SARS-CoV-2 infection in the pivotal phase 3 trial.",
        "knowledge",
        "Two doses of the BNT162b2 mRNA COVID-19 vaccine were 95 percent effective at preventing symptomatic SARS-CoV-2 infection in the pivotal phase 3 trial.",
        "knowledge",
    ),
    # 11 — infectious disease — hand hygiene, WHO
    (
        "The WHO Guidelines on Hand Hygiene in Health Care report that adherence to the five moments of hand hygiene reduces healthcare-associated infection rates by 30 to 40 percent in acute-care settings.",
        "knowledge",
        "Following the five moments of hand hygiene in acute-care wards drops healthcare-associated infection rates by roughly a third.",
        "knowledge",
    ),
    # 12 — endocrinology — metformin, UKPDS
    (
        "The UKPDS 34 trial in The Lancet showed that metformin reduced diabetes-related mortality by 42 percent in overweight patients with newly diagnosed type 2 diabetes compared with conventional diet-only therapy.",
        "knowledge",
        "Metformin cuts diabetes-related mortality by about 42 percent in overweight adults with new type 2 diabetes compared with diet alone.",
        "knowledge",
    ),
    # 13 — endocrinology — SGLT2, EMPA-REG
    (
        "The EMPA-REG OUTCOME trial reported in NEJM in 2015 that empagliflozin reduced cardiovascular death by 38 percent in patients with type 2 diabetes and established cardiovascular disease.",
        "knowledge",
        "Empagliflozin lowers cardiovascular death by around 38 percent in people with type 2 diabetes who already have cardiovascular disease.",
        "knowledge",
    ),
    # 14 — endocrinology — GLP-1, STEP-1
    (
        "The STEP 1 trial of semaglutide 2.4 mg weekly, published in NEJM in 2021, achieved a mean body weight reduction of 14.9 percent over 68 weeks in adults with obesity but without diabetes.",
        "knowledge",
        "Weekly 2.4 mg semaglutide produces an average 15 percent body weight loss over 68 weeks in adults with obesity and no diabetes.",
        "knowledge",
    ),
    # 15 — endocrinology — levothyroxine for subclinical hypothyroidism
    (
        "A BMJ meta-analysis of randomized trials found that levothyroxine replacement for subclinical hypothyroidism in adults over 65 did not improve quality-of-life or thyroid-related symptoms.",
        "knowledge",
        "Treating subclinical hypothyroidism in older adults with levothyroxine does not meaningfully improve symptoms or quality of life.",
        "knowledge",
    ),
    # 16 — nutrition — Mediterranean diet, PREDIMED
    (
        "The PREDIMED trial in NEJM reported that a Mediterranean diet supplemented with extra-virgin olive oil or mixed nuts reduced major cardiovascular events by about 30 percent in high-risk adults.",
        "knowledge",
        "A Mediterranean diet enriched with extra-virgin olive oil or mixed nuts cuts major cardiovascular events by roughly 30 percent in high-risk adults.",
        "knowledge",
    ),
    # 17 — nutrition — sodium, Cochrane
    (
        "A Cochrane review of sodium reduction trials concluded that modest salt restriction lowers systolic blood pressure by about 4 to 5 mmHg in hypertensive adults.",
        "knowledge",
        "Cutting dietary salt by a modest amount lowers systolic blood pressure by roughly 4 to 5 mmHg in people with hypertension.",
        "knowledge",
    ),
    # 18 — nutrition — vitamin D, VITAL trial
    (
        "The VITAL trial in NEJM found that vitamin D3 2000 IU daily did not reduce incident invasive cancer or major cardiovascular events over 5 years in generally healthy adults.",
        "knowledge",
        "Taking 2000 IU of vitamin D3 every day does not lower cancer incidence or major cardiovascular events in generally healthy adults over about five years.",
        "knowledge",
    ),
    # 19 — mental health — SSRI, STAR*D
    (
        "The STAR*D study reported in the American Journal of Psychiatry that only about one third of patients with major depression achieve remission on an initial SSRI, with cumulative remission reaching roughly 67 percent after four sequential treatment steps.",
        "knowledge",
        "Only about a third of people with major depression reach remission on their first SSRI; with up to four sequential treatment steps, cumulative remission approaches two-thirds.",
        "knowledge",
    ),
    # 20 — mental health — CBT, NICE depression
    (
        "The NICE guideline NG222 on depression in adults recommends cognitive behavioural therapy or an SSRI as a first-line option for moderate depression, citing equivalent short-term efficacy.",
        "knowledge",
        "For moderate adult depression, cognitive behavioural therapy and SSRIs work about equally well in the short term and either can be offered first line.",
        "knowledge",
    ),
    # 21 — mental health — suicide risk, means restriction
    (
        "A Lancet Psychiatry systematic review of means restriction interventions reported that restricting access to highly lethal methods, especially firearms and pesticides, produces measurable reductions in overall suicide rates.",
        "knowledge",
        "Restricting access to highly lethal suicide methods, particularly firearms and pesticides, reliably lowers overall suicide rates.",
        "knowledge",
    ),
    # 22 — paediatrics — back-to-sleep, AAP
    (
        "The AAP Task Force on Sudden Infant Death Syndrome recommends that infants be placed supine for every sleep period, a practice associated with more than a 50 percent drop in SIDS incidence since the Back to Sleep campaign began in 1994.",
        "knowledge",
        "Putting babies on their backs for every sleep has halved SIDS rates since the early 1990s and remains the standard recommendation.",
        "knowledge",
    ),
    # 23 — paediatrics — breastfeeding, WHO
    (
        "The WHO recommends exclusive breastfeeding for the first six months of life, with continued breastfeeding alongside appropriate complementary foods up to two years or beyond.",
        "knowledge",
        "Infants should be exclusively breastfed for their first six months, with breastfeeding continuing alongside complementary foods up to age two or later.",
        "knowledge",
    ),
    # 24 — paediatrics — bronchiolitis, AAP guideline
    (
        "The AAP clinical practice guideline on bronchiolitis recommends against routine use of bronchodilators, corticosteroids, or chest physiotherapy in infants with typical viral bronchiolitis.",
        "knowledge",
        "In infants with typical viral bronchiolitis, bronchodilators, corticosteroids, and chest physiotherapy are not recommended as routine treatments.",
        "knowledge",
    ),
    # 25 — paediatrics — ORS, WHO
    (
        "WHO and UNICEF guidance establishes low-osmolarity oral rehydration solution as first-line therapy for acute diarrhoea in children, reducing the need for intravenous fluids and shortening diarrhoea duration.",
        "knowledge",
        "Low-osmolarity oral rehydration solution is the first-line treatment for children with acute diarrhoea and cuts both IV fluid use and diarrhoea duration.",
        "knowledge",
    ),
    # 26 — surgery — appendicitis, APPAC
    (
        "The APPAC trial in JAMA showed that antibiotic therapy alone successfully treated roughly 73 percent of adults with uncomplicated acute appendicitis at five-year follow-up, avoiding surgery.",
        "knowledge",
        "About 73 percent of adults with uncomplicated acute appendicitis can be treated with antibiotics alone and avoid surgery through five years of follow-up.",
        "knowledge",
    ),
    # 27 — surgery — WHO Surgical Safety Checklist
    (
        "A New England Journal of Medicine study by Haynes et al. reported that implementing the WHO Surgical Safety Checklist was associated with a drop in inpatient surgical mortality from 1.5 to 0.8 percent across eight participating hospitals.",
        "knowledge",
        "Rolling out the WHO Surgical Safety Checklist has been shown to cut inpatient surgical mortality from about 1.5 percent to under 1 percent.",
        "knowledge",
    ),
    # 28 — surgery — VTE prophylaxis, ACCP
    (
        "The ACCP CHEST guidelines recommend pharmacologic venous thromboembolism prophylaxis in most hospitalized medical and surgical patients at moderate to high thrombotic risk.",
        "knowledge",
        "Most hospitalized medical and surgical patients at moderate to high clot risk should receive pharmacologic VTE prophylaxis.",
        "knowledge",
    ),
    # 29 — obstetrics — folic acid, MRC trial
    (
        "The MRC Vitamin Study, published in The Lancet in 1991, showed that preconception folic acid supplementation reduced the recurrence of neural tube defects by 72 percent.",
        "knowledge",
        "Taking folic acid before and during early pregnancy cuts the recurrence of neural tube defects by about 72 percent.",
        "knowledge",
    ),
    # 30 — obstetrics — magnesium sulfate, Magpie
    (
        "The Magpie trial in The Lancet established that magnesium sulfate more than halves the risk of eclampsia in women with pre-eclampsia and reduces maternal mortality.",
        "knowledge",
        "Magnesium sulfate cuts the risk of eclampsia by more than half in women with pre-eclampsia and also lowers maternal mortality.",
        "knowledge",
    ),
    # 31 — obstetrics — antenatal corticosteroids, Cochrane
    (
        "A Cochrane review confirms that a single course of antenatal corticosteroids given to women at risk of preterm birth reduces neonatal respiratory distress syndrome and neonatal death.",
        "knowledge",
        "A single course of antenatal corticosteroids for women likely to deliver preterm reduces newborn respiratory distress syndrome and neonatal death.",
        "knowledge",
    ),
    # 32 — obstetrics — GDM screening, USPSTF
    (
        "The USPSTF recommends screening for gestational diabetes in asymptomatic pregnant women at or after 24 weeks of gestation, citing moderate net benefit.",
        "knowledge",
        "Asymptomatic pregnant women should be screened for gestational diabetes starting at 24 weeks of gestation.",
        "knowledge",
    ),
    # 33 — pharmacology — warfarin vs DOAC, RE-LY
    (
        "The RE-LY trial in NEJM showed that dabigatran 150 mg twice daily reduced stroke or systemic embolism in atrial fibrillation compared with warfarin, without increasing major bleeding.",
        "knowledge",
        "In atrial fibrillation, dabigatran 150 mg twice daily prevents more strokes and systemic emboli than warfarin without raising major bleeding.",
        "knowledge",
    ),
    # 34 — pharmacology — PPIs long-term, BMJ observational
    (
        "A BMJ cohort study reported that long-term proton-pump inhibitor use was associated with a modestly increased risk of hip fracture, Clostridioides difficile infection, and community-acquired pneumonia.",
        "knowledge",
        "Long-term proton-pump inhibitor use is linked to modestly higher risks of hip fracture, C. difficile infection, and community-acquired pneumonia.",
        "knowledge",
    ),
    # 35 — pharmacology — antibiotic stewardship, IDSA
    (
        "The IDSA guideline on antimicrobial stewardship documents that formal stewardship programmes reduce inappropriate antibiotic use and lower C. difficile infection rates in hospitals.",
        "knowledge",
        "Hospital antimicrobial stewardship programmes cut inappropriate antibiotic use and drop C. difficile infection rates.",
        "knowledge",
    ),
    # 36 — pharmacology — beta-blockers post-MI, ISIS-1
    (
        "The ISIS-1 trial in The Lancet showed that early intravenous atenolol after acute myocardial infarction reduced 7-day vascular mortality by about 15 percent.",
        "knowledge",
        "Giving intravenous atenolol early after an acute myocardial infarction cuts 7-day vascular mortality by around 15 percent.",
        "knowledge",
    ),
    # 37 — epidemiology — smoking, Doll & Hill
    (
        "Doll and Hill's 50-year cohort study of British doctors in the BMJ concluded that lifelong smokers lose on average 10 years of life expectancy compared with never-smokers.",
        "knowledge",
        "Lifelong smokers lose about ten years of life expectancy on average compared with people who never smoked.",
        "knowledge",
    ),
    # 38 — epidemiology — seatbelts, Cochrane
    (
        "A Cochrane review of seatbelt laws and use concluded that wearing a seatbelt reduces the risk of death in a motor-vehicle crash by approximately 45 percent for front-seat occupants.",
        "knowledge",
        "Wearing a seatbelt cuts the risk of death in a car crash by roughly 45 percent for front-seat occupants.",
        "knowledge",
    ),
    # 39 — epidemiology — Global Burden of Disease, hypertension
    (
        "The Global Burden of Disease 2019 study in The Lancet ranked high systolic blood pressure as the single largest contributor to global disability-adjusted life years lost.",
        "knowledge",
        "High systolic blood pressure is the single biggest driver of global disability-adjusted life years lost.",
        "knowledge",
    ),
    # 40 — epidemiology — air pollution, WHO
    (
        "The WHO 2021 air quality guidelines state that long-term exposure to PM2.5 above 5 micrograms per cubic metre is associated with measurable increases in cardiovascular and respiratory mortality.",
        "knowledge",
        "Long-term exposure to fine particulate PM2.5 above 5 micrograms per cubic metre raises cardiovascular and respiratory mortality.",
        "knowledge",
    ),
    # 41 — preventive medicine — physical activity, WHO
    (
        "The WHO 2020 Guidelines on Physical Activity and Sedentary Behaviour recommend that adults do 150 to 300 minutes of moderate-intensity aerobic activity or 75 to 150 minutes of vigorous activity per week.",
        "knowledge",
        "Adults should aim for 150 to 300 minutes of moderate aerobic activity or 75 to 150 minutes of vigorous activity per week.",
        "knowledge",
    ),
    # 42 — preventive medicine — tobacco cessation, USPSTF
    (
        "The USPSTF recommends that clinicians ask all adults about tobacco use and provide behavioural interventions plus FDA-approved pharmacotherapy to those who smoke.",
        "knowledge",
        "Clinicians should ask every adult about tobacco use and offer behavioural counselling plus FDA-approved pharmacotherapy to smokers.",
        "knowledge",
    ),
    # 43 — preventive medicine — statins primary prevention, USPSTF
    (
        "The USPSTF 2022 recommendation supports low- to moderate-dose statin therapy for adults aged 40 to 75 with at least one cardiovascular risk factor and a 10-year ASCVD risk of 10 percent or higher.",
        "knowledge",
        "Adults aged 40 to 75 with at least one cardiovascular risk factor and a 10-year ASCVD risk of 10 percent or more should be offered low- to moderate-dose statin therapy.",
        "knowledge",
    ),
    # 44 — preventive medicine — alcohol, Lancet GBD
    (
        "A Lancet analysis from the Global Burden of Disease study concluded that the safest level of alcohol consumption for overall health is zero drinks per week.",
        "knowledge",
        "From a pure population-health standpoint, the safest amount of alcohol to drink per week is zero.",
        "knowledge",
    ),
    # 45 — cardiovascular — heart failure, PARADIGM-HF
    (
        "The PARADIGM-HF trial in NEJM demonstrated that sacubitril-valsartan reduced the combined endpoint of cardiovascular death or heart failure hospitalization by 20 percent compared with enalapril in HFrEF.",
        "knowledge",
        "In heart failure with reduced ejection fraction, sacubitril-valsartan cuts the combined risk of cardiovascular death or heart failure hospitalization by about 20 percent versus enalapril.",
        "knowledge",
    ),
    # 46 — infectious disease — BCG vaccine, WHO
    (
        "WHO position on BCG vaccination holds that a single neonatal dose provides substantial protection against disseminated tuberculosis and tuberculous meningitis in children.",
        "knowledge",
        "A single neonatal BCG dose offers strong protection against disseminated TB and TB meningitis in children.",
        "knowledge",
    ),
    # 47 — oncology — tamoxifen, EBCTCG
    (
        "The EBCTCG meta-analysis in The Lancet showed that five years of adjuvant tamoxifen reduced 15-year breast cancer mortality by about one third in women with ER-positive early breast cancer.",
        "knowledge",
        "Five years of adjuvant tamoxifen cuts 15-year breast cancer mortality by roughly a third in women with ER-positive early breast cancer.",
        "knowledge",
    ),
    # 48 — mental health — lithium, Cochrane
    (
        "A Cochrane review of lithium in bipolar disorder concluded that long-term lithium therapy reduces the rate of manic and depressive relapses and lowers suicide risk compared with placebo.",
        "knowledge",
        "Long-term lithium therapy in bipolar disorder reduces manic and depressive relapses and lowers suicide risk.",
        "knowledge",
    ),
    # 49 — nutrition — trans fats, WHO REPLACE
    (
        "The WHO REPLACE action package documents that eliminating industrial trans fats from the food supply can prevent more than 500,000 deaths from coronary heart disease globally each year.",
        "knowledge",
        "Removing industrial trans fats from the food supply could prevent over half a million coronary heart disease deaths worldwide every year.",
        "knowledge",
    ),
    # 50 — public health — WHO tobacco MPOWER
    (
        "The WHO MPOWER package reports that raising tobacco taxes so that excise represents at least 75 percent of the retail price is the single most cost-effective intervention to reduce tobacco consumption.",
        "knowledge",
        "Pushing tobacco excise taxes to at least 75 percent of the retail price is the most cost-effective way to cut smoking rates at the population level.",
        "knowledge",
    ),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
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
