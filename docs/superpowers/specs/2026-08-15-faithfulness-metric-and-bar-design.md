# Faithfulness metric definition — span-support coverage, its bar, and its gold shape (TH1.01)

**Status:** committed before any of Lane A exists. **Owning docs:** 16 §4, 17 §6;
ordering rule doc 20 §4 and the EH1 epic header. **Task:** TH1.01, `Gate: G-F (label)`.

This document defines the faithfulness metric for F8 grounded answering — what is
counted, what the bar is and why, and what the claim/span gold set must look like —
**before** the system it measures is built. Doc 20 §4 makes the ordering the point:
a metric defined after the thing it measures gets defined to fit. The proof of the
ordering is the git history itself: at this commit, no `documents`/`blocks` writer,
no parser, no block tree, no block partition writer, no grounded Q&A flow and no
claim/span gold exist anywhere in the tree (the T0.13 tables are inert and labelled
so). The same discipline committed `promotion_bars.py` before G-C's first
measurement and `coverage_bars.py` before G-E's.

**What this task deliberately did not read**, so the next reader can check the
claim instead of trusting it: no gate-ledger result section, no
`entailment/verdicts/`, no `entailment/cache/`, no `resample_runs/`, and
`LABELLING.md` only up to its `## History` strip line. Two measured numbers were
unavoidably in context anyway (repo baseline docs quote them): gpt-5.5's
contradiction-recall 0.945 and the contradiction-precision series 0.79–0.90.
Both are **contradiction-verdict** numbers on the **claim/fact** variant. Neither
touches any bar stated here: the per-answer bar below is 1.0, a value no
measurement anywhere could launder toward, and the two judge bars are taken from
doc 17 §6's standing rule (0.95 truth-critical / 0.90 other), which predates every
judge run — the same rule, applied to the same discrimination, would state the
same numbers had those figures never been seen. No span-variant measurement exists
anywhere, so there was nothing to fit even by accident.

---

## 1. The metric — span-support coverage, precisely

**Faithfulness = entailed answer-claims / total answer-claims**, per answer
(doc 16 §4's formula, unchanged). The definitions below are what make that
fraction computable and ungameable.

**The claim unit is the answer sentence.** TH1.08's generation contract is
per-sentence citation ("every sentence carries a block citation with its char
span"), so the sentence is the citation-bearing unit and therefore the counting
unit. No sub-sentence claim splitting in v1: splitting is a scorer policy with
its own failure modes (a splitter that fragments a conjunction manufactures
denominators), and the whole-hypothesis rule below makes the sentence-grained
count conservative rather than lenient.

**The denominator is every sentence of the served answer body. There is no
exclusion channel.** Not "assertive sentences", not "content sentences" — every
sentence. The reason is the composed-verdict lesson G-C's bars already paid for
(`promotion_rate_min_eligible`): any generator-reachable exclusion rule lets the
generator move its own denominator, and silencing a claim is the same move as
passing it, one step earlier. A refusal, a hedge, or meta-discourse ("I could
not find…") belongs in the flow's *label* channel, not in the answer body; a
generator that pads the body with uncitable prose fails the gate, which is the
gate working. The cost is stated: the generation prompt must keep meta-text out
of the body, and a sloppy generator will under-serve grounded labels rather than
over-serve them — the sanctioned error direction.

**The premise for a sentence is its cited span set, verbatim.** A sentence cites
one or more `(document_id, block_id, char_span)` references; the premise put to
the judge is the ordered concatenation of exactly those span bytes, and nothing
else. Doc 16 §4's sequence diagram shows the one-span case ("does span s entail
claim c"); this definition fixes the multi-citation case the same diagram leaves
open, additively — a set of spans is the premise, entailment is of the whole
sentence by the whole premise. Two hard edges follow on purpose:

- **The judge sees only the cited spans.** No surrounding block context, no
  whole-document fallback, no search-for-support (doc 16 §4 bars that fallback
  explicitly). A sentence whose truth rests on an antecedent outside its cited
  span — "it", "this approach", a table cell without its header row — is not
  entailed *by its citation*, and that is the correct verdict: the citation is
  the claim's evidence, and evidence the reader cannot see by following the
  citation is not evidence the label may lean on.
- **An uncited sentence fails outright** (doc 16 §4, verbatim). Uncited is
  ungrounded by definition.

**The numerator is the sentences whose full content the judge rules `entailed`
by their premise.** Whole-hypothesis scoring is inherited from the claim/fact
gold's general procedure 1: a conjunction with one unsupported conjunct is not
entailed; partial credit does not exist. `grounded ⇔ entailed` — the faithfulness
consumer branches on the `entailed` verdict alone, exactly as the article pass
does (`claim_entailment.ENTAILED`), and the same one-verdict scan discipline
binds any future faithfulness consumer module.

**An unmeasurable claim is not an entailed claim.** If the judge is unreachable,
unqualified for the faithfulness role, or returns garbage, the claim counts in
the denominator and not the numerator — `UNMEASURED` fails closed, the posture
`claim_entailment.ClaimVerdict` already takes. A judge outage must degrade to
"could not fully ground", never to a grounded label nobody measured.

**An answer with zero claims is not grounded.** Coverage 0/0 is refused, not
vacuously cleared: "every sentence is entailed" over an empty body grounds
nothing, and a generator that emits an empty or all-label body must not collect
the strongest label the surface can serve.

## 2. The per-answer bar — `faithfulness_coverage_bar` = 1.0

An answer is served **as grounded** only at coverage ≥ 1.0 — every sentence
entailed by its cited spans. Below that it is served labelled
("could not fully ground this answer") or withheld, per doc 16 §4 and
invariant 14; TH1.09 decides labelled-vs-withheld, this bar decides only the
grounded/not-grounded boundary.

**The derivation, in three steps — none of them a number read off a run:**

1. **Doc 16's own label vocabulary already states the semantics.** The
   below-bar label is "could not *fully* ground this answer". Its complement —
   the grounded label — therefore asserts *full* grounding. A bar below 1.0
   would serve an answer that could not fully ground under the label that says
   it did, which is precisely the mislabelling invariant 14 exists to forbid.
   The bar is read off the design doc's own words, not chosen.

2. **The grounded label is binary, so its guarantee must be length-invariant.**
   The article twin stores coverage as the article's `confidence` — the reader
   *sees the number* — and its below-bar path routes a subject into a human
   review queue, so a 1.0 article bar would convert near-perfect articles into
   queue load. The answer surface serves neither: the reader sees a binary
   badge, and the below-bar path costs a label, not a reviewer. A binary badge
   whose meaning varies with answer length ("all sentences" at n = 10, "all but
   two" at n = 40) is two claims under one word. 1.0 is the only bar under
   which "grounded" means the same thing at every answer length.

3. **The regime arithmetic, shown so it can be rechecked.** For an answer of
   n ≤ 19 sentences, one unentailed sentence gives coverage ≤ 18/19 ≈ 0.947,
   so every bar in (18/19, 1.0] — the article twin's 0.95 included — is the
   *same predicate*: one miss refuses the label. The twin's 0.95 and this 1.0
   diverge only at n ≥ 20, where 0.95 begins tolerating misses — at n = 40,
   coverage 39/40 = 0.975 clears 0.95 with an unsupported sentence served
   under the grounded badge, and 38/40 = 0.95 clears with two. Interactive
   answers live almost entirely in the short regime where the two bars agree;
   where they disagree is exactly where the looser one leaks. The pin test
   carries this arithmetic as an executable assertion.

**The priced cost.** The judge's own recall bar is 0.90, so a qualified judge
may falsely refuse up to one genuinely entailed claim in ten; under independence
an honestly grounded n-sentence answer earns the grounded label with probability
about 0.9^n at worst (≈ 0.66 at n = 4, ≈ 0.43 at n = 8). That is a
served-labelled rate, not a truth failure — the answer still reaches the user
with its citations, marked honestly — and it is the sanctioned error direction
(doc 08 §5.3's asymmetry, the maintainer's under-claiming preference). If the
label proves unearnable in practice, the repair is a better judge or a licensed
loosening with the argument written down — never a quietly friendlier default.

**The anti-fit check.** The standing test that a bar is a derivation is that the
measured thing does not automatically clear it. Nothing exists to measure yet,
which is the strongest form of that check; structurally, 1.0 is additionally the
one value no laundering argument can reach — every fit loosens, and there is
nothing above 1.0 to have loosened from. The obvious fitted value is the twin's
0.95 ("match the article bar"), and the pin test pins this bar against exactly
that.

**What would have to be true for this bar to be wrong.** (a) The grounded label
is re-specified as a per-sentence property served sentence-by-sentence, making
the answer-level boundary vestigial — that is a doc 16 amendment, not a bar
move. (b) Measured judge false-refusal makes the label unearnable at qualifying
recall *and* the owner judges the labelled path insufficient for the product —
that is the licence path, bounded at 0.95, because below 0.95 the corpus has no
argument at all: the twin's own rule-derived value is the floor of any coherent
loosening. **That licence buys nothing in the short regime, and saying otherwise
would over-promise it** (TH1.01 review, Important-2): by §2's own regime
arithmetic a 0.95 bar demands the same all-claims-entailed predicate for every
answer under twenty sentences, so at n = 8 loosening to 0.95 changes no verdict
whatsoever. The only repair available where answers actually live is judge
recall — the licence reaches the long regime alone. (c) Answers become long-form by design — which makes the sub-1.0
leak larger, so it argues for this bar, not against it.

## 3. The ship-gate bars — the faithfulness role's judge qualification

Doc 16 §4's second use of the metric: F8 does not ship until doc 17 shows the
judge reliable at the **claim/span** entailment discrimination on labelled gold.
Per doc 17 §6's 2026-08-12 amendment, admission is per consumer **role** over one
judge identity, and a role is admitted only for the discrimination it makes. The
faithfulness consumer branches on `entailed` alone, on a premise distribution
(raw document span text) the claim/fact gold does not represent — the
amendment's own caption: the gold splits by grounding target because the premise
distributions differ. So F8's admission is a **third role**, `faithfulness`,
with its own record, minted only by a cleared run on claim/span gold; the
entailment role's record on claim/fact gold qualifies it for articles, not for
this.

Its bars, by doc 17 §6's standing rule — the truth-critical metric at 0.95, the
other at 0.90, a rule that predates every judge run:

- **`faithfulness_gate_precision_bar` = 0.95** — precision on `entailed` is
  truth-critical: a judge that calls an unsupported answer sentence entailed
  serves a hallucination under the grounded badge, the top of the
  truth-over-everything ordering.
- **`faithfulness_gate_recall_bar` = 0.90** — a falsely refused sentence costs
  a label, the sanctioned direction.

Same numbers as the groundedness pair because the rule and the discrimination
are the same; what is *not* shared is the record, the gold, or the sitting.
A qualifying run's record must disclose the not-entailed→entailed confusion
cells (the claim/span analogue of the `contradicted_judged_entailed` disclosure
condition), and a record that names a retired pair set is inert for this role
exactly as for the other two.

**Wiring is deliberately not this task's.** Adding `faithfulness` to
`JUDGE_ROLES` / `BAR_METRICS` / `ROLE_VERDICTS` (verdict `entailed`) belongs to
TH1.09 (the serving check, which must call `judge(role="faithfulness")`) and
TH1.17 (the runner). Both must **import** the defaults from
`app/services/faithfulness_bars.py` — never restate the numbers — so the bars
stated today and the bars enforced then cannot be two values. When the role
lands, its two bar keys join `BAR_METRICS` and the roles-partition test carries
them; until then they live only in this module, on purpose: orphaning a bar
into no role's gate is exactly what that test forbids.

## 4. Conservative directions, the licence path, and the config surface

The bars live in **`backend/app/services/faithfulness_bars.py`** as committed
defaults under the ladder's floor-clamp shape, and each is a `config` row:

| config row key | default | compared | conservative | loosening it does |
|---|---|---|---|---|
| `faithfulness_coverage_bar` | 1.0 | `coverage >= bar` | **higher** (floor) | serves unentailed sentences under the grounded label |
| `faithfulness_gate_precision_bar` | 0.95 | `precision >= bar` | **higher** (floor) | admits a judge that grounds hallucinations |
| `faithfulness_gate_recall_bar` | 0.90 | `recall >= bar` | **higher** (floor) | admits a judge that refuses honest answers (label churn, not truth) |

The direction is carried **per parameter** (`FaithfulnessBarSpec.conservative`),
not assumed module-wide — G-C's clamp found a bar whose abuse a direction-blind
guard read as a tightening, so the pin test **re-derives** each direction from
the committed predicates rather than trusting this table. All three happen to be
floors; the structure is what prevents a fourth bar joining direction-unstated.
Note `faithfulness_coverage_bar` sits at the top of its domain, so a config row
can only restate or loosen it — every genuine move on that key takes a licence.

**The licence row is `faithfulness_bar_licences`**, shaped exactly like
`verification_bar_licences` / `promotion_bar_licences` and read by the same
rules: per parameter by name, never blanket; a `value` stating the furthest the
recorded argument reaches in that bar's loosening direction (the licence bounds
the loosening, which is what stops the bar row licensing itself); an `argument`
citation checked for presence and never for truth; a bound outside (0, 1]
licensing nothing, because a bound no candidate can trip unlocks the parameter
silently. Tightening is free. A readable row below its floor without a
matching licence clamps back to the committed default — to the default, never
to the licensed value, which would put a number on the gate the operator did
not write — with a warning naming what was missing. An unreadable row raises,
and the eventual enforcement paths fail closed on it. Nothing in the tree
writes the licence row. The honest limit is the same as its two precedents': an
operator with config-write access can write both rows and nothing in-process
stops that; what the clamp buys is that a loosening is never a single number
edit with no trace.

**Visibility obligation, stated now so TH1.17 inherits it rather than
rediscovers T2.128:** any gate runner that resolves these bars must print, per
bar, the committed value, the effective value, and which of *no config row* /
*honoured* / *CLAMPED* happened — a clamp that speaks only through `logging` is
byte-invisible in the artifact a reviewer reads. The app-side reader warns, as
its two precedents do.

**The pre-stated verdict predicates ship with the bars**, so the arithmetic is
committed before any consumer: `answer_grounded(entailed_claims, total_claims,
bars)` — counts, not a rate, because 39/40 and 975/1000 are the same 0.975 and
not the same evidence (the T2.132 lesson), refusing `total == 0` and incoherent
counts — and `faithfulness_role_clears(entailed_precision, entailed_recall,
bars)`. `tests/test_faithfulness_bars.py` pins every default by value, pins the
coverage bar against 0.95 (the fitted value), re-derives the directions, and
pins the clamp behaviour, so moving any goalpost is a visible two-file diff.

## 5. The claim/span gold — shape only; zero pairs are authored here

The claim/fact gold's discipline transfers wholesale and is not restated:
append-only file with declared counts; one slice per pair; a `rationale` citing
a named rule; judge-blind labelling with two independent blind passes and owner
escalation; provenance honesty with reserved-at-zero vocabularies pinned by
test; retire-in-place, never delete; quarantine of per-pair judge output
(`cache/`, `verdicts/` siblings) from every author and adjudicator;
proposition-level (not byte-level) independence; ≥ 200 pairs (doc 17 §6),
near-misses the majority. The claim/span gold is a **sibling file under its own
labelling rules** (the claim/fact LABELLING.md says exactly this), never mixed
into `gold.json`.

**What a faithfulness gold needs that the entailment gold's shape does not
give it:**

1. **A span anchor contract in place of `fact_key`.** The claim/fact gold
   byte-binds `l2-fact` premises to a committed harvest manifest. Here the
   premise is document bytes, so the anchor is
   `{document_uri or fixture path, content_hash, block_id, char_span}` per
   cited span, and the loader re-derives the premise bytes from the anchored
   document content and byte-compares — drift fails loudly and forces
   retire-and-replace, exactly like corpus drift. Until Lane A can mint real
   `documents` rows, anchors resolve against **committed fixture documents**
   (files in the gold's own directory, hashed); the same "real governs the
   distribution" clause applies when TH1.02+ exist — a premise is *real* when
   the shipping parser produced its block and span, and a provenance value
   records which.

2. **Multi-span premises.** A pair's premise is an *ordered list* of one or
   more anchored spans, because §1 defines the runtime premise that way. The
   claim/fact schema has a single premise string and cannot express the
   composition case at all.

3. **A binary verdict vocabulary: `entailed` / `not-entailed`.** The
   claim/fact gold keeps three verdicts because the contradiction role is
   qualified from the same file; no consumer makes a contradiction
   discrimination over spans, and a `contradicted` census here would mint
   numbers no role's gate reads — the orphaned-bar shape. The cost is stated:
   if a future consumer wants contradiction-over-spans, that is a new gold or
   a relabelling round, not a reinterpretation of this one. Hard negatives
   (value swaps, reversals) are still authored; they are labelled
   `not-entailed` and carried by slices.

4. **Span-specific slices the claim/fact gold has no analogue for**, alongside
   the transferable ones (verbatim, paraphrase, weakening, overreach,
   value-swap-style, unrelated — all reinterpreted over document prose):
   - `span-truncation` — the cited span cuts off before (or starts after) the
     clause that would support the claim; the surrounding block supports it,
     the citation does not. Verdict: not-entailed. This is the failure a
     span-anchored citation system uniquely invents.
   - `context-dependence` — the span supports the claim only via an antecedent
     outside it ("it", "this approach", a table cell without its header).
     Verdict: not-entailed, by §1's judge-sees-only-the-spans rule; the slice
     exists to catch a judge that resolves anaphora from world plausibility.
   - `multi-span-composition` — the claim is entailed only by the conjunction
     of two or more cited spans, no single one sufficing. Verdict: entailed.
     The recall-side hard case for a judge that reads only the first span.
   - `structure-fragment` — the span is a list item, table fragment, or
     heading-scoped line whose meaning depends on document structure the span
     text carries only partially. Mixed verdicts, decided by what the bytes
     alone assert.
   The claim/fact temporal slice does not transfer as-is (block spans carry no
   validity windows); temporal material appears only as ordinary prose content.

5. **A provenance vocabulary for documents**: `hand-authored-fixture-span`
   (fixture document authored for the gold, span cited from it),
   `document-span` (parser-produced block from a real ingested document —
   reserved, zero pairs until TH1.02+), `qa-draft` (hypothesis harvested from a
   real TH1.08 answer — reserved, zero pairs until TH1.08 exists, pinned at
   zero by test exactly as `synthesis-draft` is).

**Deliberately not done here:** no pair authored, no gold file created, no
loader written, no existing gold touched. The gold's authoring task (M1's, on
TH1.10/TH1.17's path) starts from this section, and its labelling rules file
must be written rule-then-pairs before any pair exists.

## 6. Findings against the design docs, recorded rather than absorbed

- **Doc 16 §4's one-span-per-claim diagram vs TH1.08's contract.** The diagram
  binds each claim to one span; nothing in doc 16 forbids a sentence citing
  two blocks and TH1.08 will produce such sentences. §1 resolves it additively
  (premise = the cited span set); if a later reading insists on strictly one
  span per sentence, that is a doc 16 clarification to ratify, and this
  definition degrades to it as the singleton case.
- **The article twin's bar is not clamp-enforced.**
  `claim_entailment.DEFAULT_COVERAGE_THRESHOLD` says of itself that it is
  "convention-recorded, not clamp-enforced". The faithfulness bars land under
  the clamp from day one; the asymmetry now points at the article side, and
  closing it there is its own task, not this one's.
- **Doc 16/17's "one judge, three consumers" predates the per-role record
  split.** The 2026-08-12 amendment names two roles because two consumers
  existed to charter; the third consumer's role is implied by the amendment's
  own logic, not stated. §3 states it. If the owner instead rules that the
  faithfulness consumer may ride the entailment role's claim/fact record, that
  is a Tier-3 call against the amendment's premise-distribution argument — the
  default reading here is the conservative one.
