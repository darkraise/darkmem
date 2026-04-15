"""One-off emitter for retrieval top-up batch-009 — typo-kind queries.

Consumes shared rows 800..899 and emits one typo query per source row.
Each query is 4-18 words with 1-3 typos per query, varying typo types
(adjacent-key slips, dropped/doubled letters, transpositions, common
misspellings, split/merge word errors, wrong-vowel slips).

Writes 100 rows to data/v2/retrieval/batch_009.tmp.jsonl.
Ids: ret-00801..ret-00900. Source ids: shared-00800..shared-00899.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_PATH = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_009.tmp.jsonl"
ID_OFFSET = 800
SHARED_OFFSET = 800
QUERY_KIND = "typo"

# One typo-kind query per source row 800..899 (100 queries total).
# Queries paraphrase the source with 1-3 deliberate typos, 4-18 words.
QUERIES: list[str] = [
    # 800 GW170817 multimessenger
    "wich 2017 nuetron star merger gave us gravitaitonal waves with EM counterpart",
    # 801 Simon bounded rationality
    "whcih theory frames descision making under cogntive limits",
    # 802 Tversky/Kahneman prospect theory
    "what framewrk says loses loom larger than equivelent gains in risky choice",
    # 803 prospect theory improves on EU theory
    "which behavioural model upgarde the classical utiltiy baseline for risk preferences",
    # 804 Banerjee Duflo RCTs
    "whose programe maisntreamed field expierments in development economics",
    # 805 Card Krueger minimum wage
    "which 1994 New Jerey fastfood study challenegd minimum wage theory",
    # 806 SDT three needs
    "wich motivtion framework names autonomy competance and relatedness",
    # 807 Bowlby attachment
    "whose theory connets infant bondng to adult relationshp patterns",
    # 808 Festinger dissonance
    "what theroy explains attitide change as concilation between clashing beliefs",
    # 809 Stanford marshmallow
    "which famos self-control study wekaned after controlling for familiy background",
    # 810 noise (effect size)
    "hold on pulling teh exact effct size before commiting to that claim",
    # 811 Dweck growth mindset
    "whoose mindset theroy shows shirnking effects in larger replications",
    # 812 BI units prefer field trials
    "why do nudge unts prefer feild trials over lab-only evdence for policy",
    # 813 UK BIT spinout date
    "when did teh UK nudege unit spinout from cabint office as social venture",
    # 814 Thinking Fast and Slow
    "wich trade book poularised two system reasoning to general readres",
    # 815 Game theory applications
    "which matheatical toolikt underpins auctoin design and matching markets",
    # 816 Roth Shapley 2012 Nobel
    "which ecnomists won 2012 Noble for matching theroy applied to kidney exchanges",
    # 817 Rational choice theory
    "whcih framework models agents as consitent utilty maximisers",
    # 818 Heuristics and biases
    "whcih descriptive traditon displaced ratinoal agent in decision research",
    # 819 Longitudinal cohort example
    "whcih desgin follows one panel for yars with canonical British exmaple",
    # 820 Framingham Heart Study
    "whcih long running cohort anchored modren cardiovasular epidemiolgy research",
    # 821 Randomised field experiments
    "whcih evidnce form beats surevys when causaton is the goal",
    # 822 Ecological validity
    "wihch critque flags lab to field generalistaion failures in psychology",
    # 823 Pre-registered replication
    "wihc publishing format anchros credibilty checks in psycholgy journals",
    # 824 Registered Reports extend preregistration
    "wihch review format adds stage one peer reveiw before data colection",
    # 825 Meta-science credibility revolution
    "wihch reform movemnt made open data and code firstclass requirments",
    # 826 Many Labs 2
    "whcih multilab replicatoin reported about half of clasic effects holding up",
    # 827 Why Nations Fail
    "wihch book blames extractve institutons for long run devlopment gaps",
    # 828 Dev econ prefers DiD
    "whcih quasi experimntal design is faviured when a contorl panel exists",
    # 829 RAND Health Insurance Experiment
    "whcih classic insurnace RCT ran from the early 1970s into the eigthties",
    # 830 School voucher/charter mixed
    "wihch school-choice evidnce is dominated by city level hetrogeneity",
    # 831 Tennessee STAR class size
    "whcih clas size RCT in the late 1980s showed durable smal class gains",
    # 832 Piketty Capital
    "wihch book poularised the r > g framng of long run inequailty",
    # 833 Milgram obedience contested
    "whcih clasic social psych resut was reopened by verison level reanalsis",
    # 834 noise (effect size)
    "give me a secnd I need to lok up the effct size first",
    # 835 Putnam Bowling Alone
    "wihch book frams postwar civic decline as social capial erosion",
    # 836 IVs replace OLS
    "whcih estimator takes ovr when unobsereved confounding threatens OLS",
    # 837 RDD
    "whcih desgin uses sharp cutofs to mimic randomisaton locally",
    # 838 Synthetic control extends DiD
    "whcih case study estimaor extends dif in dif with weigthed control",
    # 839 Abadie 2003 Basque
    "wihch early syntetic control paper used a Basque regional case in 2003",
    # 840 Nash equilibrium
    "what soluton concpet requires no profiable unilatral deviation by any player",
    # 841 MRP over raw weighting
    "wihch survey estimatr beats raw wieghting for small area politcs",
    # 842 GBD DALYs
    "wihc WHO initative harmoises disease burden measurment using daly",
    # 843 Public health surveillance
    "how do helath agencys feed natioal dashboards from notifable reporting",
    # 844 Vaccination coverage measles
    "whcih disease has a notabley hgh herd immunty threshold in coverage metrics",
    # 845 Grameen microfinance 1983
    "whcih microfinace institution scaled group lendng in Bangadesh from 1983",
    # 846 Banerjee 2015 microfinance
    "wihch mid 2010s synthesis showed microfiance only modstly helping buisnesses",
    # 847 Robust SEs replace homoskedastic
    "whcih correctoin should analyts use when hetroskedasticity is visbile",
    # 848 Duncan mobility tables
    "whose classicl sociologcal tool formaised intergenerationl status flow",
    # 849 PISA
    "whcih triennal assesment publshes cross country student competance scores",
    # 850 Cluster randomisation
    "whcih randomisation desgin wins when household level spilovers are real",
    # 851 Cook's theorem
    "wihc result first identifed a compleet problem for the NP class",
    # 852 Rudin
    "wihch textbok anchors undergraudate rigurous real analsis teaching",
    # 853 Kripke semantics
    "what interpertation scheme took over for modal oerators in logic",
    # 854 AKS primality 2002
    "when did a deterministc polynmial time primalty checker first appear",
    # 855 Grover's algorithm
    "wihch quantum rotine beats brute forc lookup by a square root fator",
    # 856 Functionalism
    "wihch position defines mentl states by their causl role profile",
    # 857 Category theory over set theory
    "which abtract framework anchors modren algerbraic geometry work today",
    # 858 Hartshorne
    "wihch graduate textbok carried the schmes torch after the French foudations",
    # 859 Halting problem
    "what classcal decison problem has no genral computable soltuion",
    # 860 noise (look up paper)
    "let me pul up the paper to get the exat statment real quick",
    # 861 PSPACE PH
    "wihch space class sits above the unbonded alternation tower with open collapse",
    # 862 Wittgenstein PI 1953
    "when did Wittgenteins later work overtuning picture theroy appear",
    # 863 Dependent type theory
    "wich type system generalies STLC by letting typs depend on values",
    # 864 Simplex method 1947
    "wihch pivotng routine for linar optimisaton traces to the late 1940s",
    # 865 Moral realism vs anti-realism
    "wihch metaethcial stance asserts oberver independent ethcial facts",
    # 866 Sipser
    "wihch textbok usualy opens the doar to automata and complexity theroy",
    # 867 Miller-Rabin
    "wihch randomised primlaity test accpets bounded monte carlo error for speed",
    # 868 CLRS
    "wihch hefty refernce anchors most algortihms courses in prctice",
    # 869 Parfit Reasons and Persons
    "wihch book seperated what matters in suvival from strict personal identty",
    # 870 Public-key crypto trapdoor
    "wihch crytographic primitve powers asymetric schemes with a secret",
    # 871 ECC replaces RSA
    "wihc key exchnge family takes ovr when bandwidth and compute are tigth",
    # 872 Curry-Howard
    "wihch bridge conects logical proofs to programs in a type sytem",
    # 873 HoTT builds on MLTT
    "wihch newer fondation reads types as spaes and identties as paths",
    # 874 Wiles 1994 FLT
    "when and by wohm was Fermats last theorm finaly proven",
    # 875 Rawls Theory of Justice
    "wihch treatise built distribuive principles from veil of ignorace thought experiment",
    # 876 Lattice crypto NIST
    "wihch scheme family is favoured by the NITS post quatum standardistion process",
    # 877 Church-Turing thesis
    "what informl claim tries effective computability to a sigle model of computation",
    # 878 Coq over Lean
    "which proff assistent wins when legacy teahing material is the deciding factor",
    # 879 Scala cats recursion schemes
    "wihch tyepd JVM libary packages recursion patterns over inductve data",
    # 880 Anscombe Intention 1957
    "when did the monograph reshapping philosohpy of action first appear",
    # 881 BFT two-thirds
    "what thershold of honst nodes does arbirary fault consensus deamnd",
    # 882 CAP theorem
    "wihch imposibility result constrains distribted data store guarntees",
    # 883 MacIntyre After Virtue
    "wihch book charged that moral vocabluary is fragmeted leftovers of virtue ethics",
    # 884 noise (reference)
    "hold on I wnat to doulbe check that refernce before commiting to it",
    # 885 Quine Two Dogmas 1951
    "wihch 1951 essay rejcted the twin empircist pillars of mid century philosohpy",
    # 886 Big-O notation
    "what notaion family captures worst case growht of resorce consumption",
    # 887 Shor's algorithm
    "wihch quantm routine threatens RSA by factorng in polnomial time",
    # 888 Externalism mental content
    "wihch view about meanning places part of content outside the thinkrs head",
    # 889 Homomorphic encryption
    "wihch crypto capabilty lets a party compte over encripted data directly",
    # 890 Red-black trees
    "wihch balaced tree takes ovr when logrithmic worst case is requird",
    # 891 Martingale convergence
    "wihch probablity results quiety power many limit and stoping proofs",
    # 892 Dummit and Foote
    "wht course structure often shapes first year graudate algebra courses",
    # 893 Haskell lazy evaluation
    "wihch evalution strategy does teh canonical pure fuctional language pick",
    # 894 Riemann Hypothesis
    "what unreslved conjcture pins non trivial zeta zeros to the critcal line",
    # 895 Kripke 1970 lectures
    "when did the semnar on rigd designation and refernce take place",
    # 896 Paxos
    "how does teh classic consesus protocl structure its agrement rounds",
    # 897 Raft over Paxos
    "wihch consesus desgin aimed at being easier to lern than its predcessor",
    # 898 Gettier cases
    "wihch counterexampls undrmined the classicl definition of knowlege",
    # 899 Lamport happens-before
    "whoose partial order definded distribted concurrency for practcal purposes",
]


def _load_shared_rows(path: Path, start: int, count: int) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < start:
                continue
            if i >= start + count:
                break
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    for i, q in enumerate(QUERIES):
        wc = len(q.split())
        assert 4 <= wc <= 18, f"query {i} has {wc} words (must be 4-18): {q!r}"

    sources = _load_shared_rows(SHARED_PATH, SHARED_OFFSET, 100)
    assert len(sources) == 100, f"expected 100 source rows, got {len(sources)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (src, query) in enumerate(zip(sources, QUERIES), start=1):
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": src["id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
