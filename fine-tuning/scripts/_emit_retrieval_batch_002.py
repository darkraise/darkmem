"""One-off emitter for retrieval top-up batch-002.

Produces 100 paraphrase-kind retrieval rows targeting shared rows
shared-00101..shared-00200. Writes to data/v2/retrieval/batch_002.tmp.jsonl.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_002.tmp.jsonl"
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 100
SHARED_OFFSET = 100
QUERY_KIND = "paraphrase"

QUERIES: list[str] = [
    # 00101 married Jamie Kyoto 2026-06-15
    "what day did my partner and I tie the knot overseas",
    # 00102 Barcelona over Lisbon summer trip food
    "which Spanish city beat the Portuguese one for holiday plans",
    # 00103 morning runs riverfront over gym
    "which exercise style does the user favour at sunrise",
    # 00104 parking dispute with Martin upstairs
    "which neighbour still has an ongoing grievance with me",
    # 00105 Mom's pho recipe green notebook page 47
    "how do I find Mother's noodle broth instructions",
    # 00106 Sunday evening meal prep journaling
    "which habits fill the hours before sleep on the last day of the week",
    # 00107 Dad's birthday 1961-09-12 turning 65
    "which year was my father born and how old is he now",
    # 00108 Tokyo Marathon 2026-03-01 eight months training
    "how long did I prepare before finishing the big run in Japan",
    # 00109 Spanish lessons dropping French
    "why did the Romance language choice shift toward Spanish",
    # 00110 oat milk replaced dairy reflux
    "what milk alternative went into my cups after the acid issues",
    # 00111 saving 15000 euros stalled rent hike
    "why is the European currency savings plan behind schedule",
    # 00112 chicken piccata Bon Appetit Nov 2023
    "which food publication gave me the capers-and-lemon poultry dish",
    # 00113 Sam 50/30/20 budget monthly
    "how do my partner and I review our finances at month start",
    # 00114 dog eats only salmon and peanut butter
    "which two foods will my pet actually accept",
    # 00115 quit smoking 2025-01-01 fourteen months
    "how long have I been off tobacco as of now",
    # 00116 move Berlin April 2027 from Amsterdam
    "where am I heading next year and what motivates the move",
    # 00117 bookshop cafes over nightclubs
    "what quiet venue beats loud bars for meeting friends",
    # 00118 inheritance dispute Rachel cabin arbitration
    "which sibling estate fight moved into formal mediation",
    # 00119 NYT article 2025-11-14 changed caffeine view
    "which newspaper sleep piece adjusted how I see stimulants",
    # 00120 grocery run Saturday farmers market Maya
    "when and with whom do I do produce shopping each week",
    # 00121 Grandma Helena Lisbon since 2019
    "how long has my grandmother lived by herself abroad",
    # 00122 paid off student loan BMO 2026-02-28
    "when did the eleven-year tuition repayment finish",
    # 00123 dropped yoga for reformer pilates
    "why did I leave traditional yoga behind this year",
    # 00124 Thai curry over Indian curry
    "which curry tradition usually wins dinner around here",
    # 00125 Bali flight cancelled Singapore layover
    "how did the Indonesia trip get salvaged after the carrier cancelled",
    # 00126 Marie Kondo tidying method
    "whose minimalist book am I following to clean house",
    # 00127 Friday date night Jamie restaurant film
    "what weekly couple tradition alternates food and movies",
    # 00128 dog Kensington shelter 2021-04-03
    "which rescue organisation did we adopt the dog from and when",
    # 00129 first 5k Cherry Blossom Run 2026-04-05 28 min
    "what was my debut short race and finishing time",
    # 00130 couples therapy Dr. Chen Jake
    "which therapist is helping with the repeating argument with my partner",
    # 00131 Rhone wine beats Napa
    "which wine area gives me more for the same price",
    # 00132 stress migraines afternoon caffeine cut
    "how did trimming late coffee halve my headaches",
    # 00133 Anna recommended book on the power of now
    "which friend-recommended mindfulness title did I just complete",
    # 00134 6am Saturday swim community pool
    "what athletic routine kicks off my weekend before the kids rise",
    # 00135 cat allergic to fish tuna
    "which seafood makes my cat swell up",
    # 00136 promoted senior engineering manager Lumen 2026-03-20
    "when did my employer bump me to a senior management title",
    # 00137 hypertrophy blocks built on strength base
    "how is the gym programming evolving from last year's base",
    # 00138 paper books evening ebooks travel
    "when do I actually reach for a digital reader instead of print",
    # 00139 knee flare-up gym break Dr. Rosen rehab Monday
    "why am I skipping the gym and who is handling my recovery",
    # 00140 Dr. Huberman podcast morning light
    "whose show shapes my daylight-based sleep protocol",
    # 00141 weeknight fresh dinners weekend leftovers
    "how does my weekly cooking rhythm split across the days",
    # 00142 wedding anniversary 2019-07-04
    "what date marks my marriage each year",
    # 00143 one year sober 2026-04-07 Jess
    "when did my alcohol-free streak hit a full year",
    # 00144 NOISE
    "can I have a moment to think this through",
    # 00145 Reformer pilates improves on mat class hip
    "which pilates style is easier on my hip joint",
    # 00146 hiking Dolomites over camping Alps
    "which mountain holiday format do I actually enjoy more",
    # 00147 college friends drifting Priya Ben
    "why is the undergraduate friend group falling out of touch",
    # 00148 Whole30 program cravings day 14
    "which structured elimination diet is driving my kitchen choices",
    # 00149 Friday phone-off board games kids
    "what device-free family tradition closes out the workweek",
    # 00150 NOISE
    "can I pause before reacting to this",
    # 00151 speed of light 299792458 1983 SI
    "what is the fixed numerical value for how fast light travels",
    # 00152 Vaswani 2017 transformer Attention Is All You Need
    "which paper first laid out the transformer design",
    # 00153 Bayesian model averaging over single model climate
    "which ensemble weighting approach did the climate team adopt",
    # 00154 mitochondria own DNA maternal
    "which parent passes down the DNA inside those cellular power plants",
    # 00155 tidyverse over base R exploration
    "which R ecosystem does the team reach for first when exploring data",
    # 00156 2015 replication study 60 percent social psychology
    "what fraction of behavioural science findings failed to replicate recently",
    # 00157 CRISPR Cas9 first human cells 2013-01-03 Zhang
    "when was gene editing first shown to work in human cells",
    # 00158 general relativity curvature spacetime
    "how does Einstein's theory re-interpret what gravity actually is",
    # 00159 NOISE
    "that seems like a sensible place to begin",
    # 00160 water max density 4C ice floats
    "why do frozen chunks sit atop bodies of liquid water",
    # 00161 Boyd Vandenberghe 2004 convex optimization textbook
    "which 2004 book is the go-to reference for convex optimisation",
    # 00162 random forests to gradient boosted trees churn
    "which boosting method replaced the forest model for predicting churn",
    # 00163 Einstein summation over sigmas
    "which index convention do reviewers prefer in tensor proofs",
    # 00164 diminishing marginal utility second slice cake
    "what economic idea says extra helpings matter less",
    # 00165 acquiescence bias 2024 cohort survey
    "what bias warped the agreement ratings in last year's survey",
    # 00166 plate tectonics mainstream 1960s
    "in which decade did drifting continents become settled science",
    # 00167 Kahneman dual-process fast intuitive slow deliberative
    "how is thinking divided in the two-mode cognitive framework",
    # 00168 universal grammar innate language faculty
    "which linguistic hypothesis claims an inborn language capacity",
    # 00169 APA 7th edition stats reporting
    "which manual prescribes how statistics are formatted in our papers",
    # 00170 random-effects meta-analysis heterogeneity
    "why did the pooled analysis avoid a fixed-effects approach",
    # 00171 Mathematica over SymPy symbolic
    "which symbolic algebra tool do we prefer for tough expressions",
    # 00172 Hubble tension local vs CMB
    "why does modern cosmology disagree with itself on how fast the universe grows",
    # 00173 AlphaFold 2 CASP14 2020
    "when did computational protein folding match bench-grade accuracy",
    # 00174 conference double-blind three reviewers meta-reviewer
    "how does this venue organise its blind review workflow",
    # 00175 fundamental theorem calculus differentiation integration
    "which result ties together slopes and areas under curves",
    # 00176 CoNLL-2003 English NER benchmark
    "what is the go-to English corpus for benchmarking entity taggers",
    # 00177 Flesch-Kincaid to LIX multilingual
    "which readability measure replaced Flesch-Kincaid after multi-language work",
    # 00178 Cochrane reviews over single trials epidemiology
    "what evidence source does the group consult first for disease questions",
    # 00179 selection bias inflated effect 18 percent
    "by how much did flawed recruitment puff up the apparent finding",
    # 00180 Carolyn Bertozzi Nobel chemistry 2022 click bioorthogonal
    "which scientist claimed the 2022 chemistry prize for bio-friendly coupling",
    # 00181 FAIR findable accessible interoperable reusable
    "what do the four letters of the open-data principle stand for",
    # 00182 Library of Alexandria gradual decline not single fire
    "how did the ancient scroll collection actually disappear over time",
    # 00183 CONSORT 2010 randomised trials checklist
    "which reporting checklist do randomised trial authors cite",
    # 00184 Julia over Python ODE 40x speed
    "which language replaced Python in the differential equation service",
    # 00185 NOISE
    "hold on while I check that properly",
    # 00186 within-subjects over between-subjects
    "which experimental design do we reach for to tame individual variance",
    # 00187 Newtonian mechanics fails near light speed
    "where does the classical physics framework stop working",
    # 00188 LIGO first gravitational wave 2015-09-14 binary black hole
    "when was a spacetime ripple captured directly for the first time",
    # 00189 PRISMA identification screening eligibility inclusion
    "what four phases organise a systematic review under the common standard",
    # 00190 informed consent capacity voluntariness disclosure
    "what trio of conditions underlies a valid research consent",
    # 00191 SEP free will entry starting point
    "which online philosophy reference begins most free-will discussions",
    # 00192 hierarchical Dirichlet prior AIC BIC disagreement
    "which nonparametric prior settled the topic-count question for us",
    # 00193 two replications outweigh single original
    "how does our team balance repeat studies against a single large trial",
    # 00194 quantum mechanics general relativity Planck scale
    "where do the two leading physical theories fail to reconcile",
    # 00195 cryo-EM structural biology 2017 Nobel
    "which cryogenic imaging method won the 2017 chemistry prize",
    # 00196 standard model fermions bosons three generations
    "how does particle physics organise its fundamental constituents",
    # 00197 penicillin Fleming 1928
    "who stumbled onto penicillin and when",
    # 00198 ImageNet benchmark image classification
    "which dataset anchored image recognition progress since 2010",
    # 00199 Gaussian to Matern spatial smoothing
    "which covariance prior took over for capturing local roughness",
    # 00200 arXiv preprints before journal lab
    "where does the group share drafts before peer-reviewed journals",
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    with SHARED.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    slice_lines = lines[SHARED_OFFSET:SHARED_OFFSET + 100]
    assert len(slice_lines) == 100, f"expected 100 shared rows, got {len(slice_lines)}"
    written = 0
    with OUT.open("w", encoding="utf-8") as out_f:
        for i, (src_line, query) in enumerate(zip(slice_lines, QUERIES), start=1):
            src = json.loads(src_line)
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": src["id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
