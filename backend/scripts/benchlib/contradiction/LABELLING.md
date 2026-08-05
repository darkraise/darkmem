# Contradiction-pair gold — labelling rules (fact-pair variant, doc 17 §5.2)

This file is the authority for what the label and each slice *mean*. Label
pairs against these decision procedures, not from intuition about the word
"contradiction" — the production veto is **absolute** (doc 08 §4.2), so a
label here is a claim about when a fact may be demoted to `disputed` with
no vote and no appeal. Every pair's `rationale` cites the rule it was
decided under; a pair you cannot write such a rationale for is a pair that
does not enter the file.

Files: `gold.json` (50 pairs seeded by T2.57, all live). Loader and
validation: `benchlib/contradiction_gold.py`,
`benchlib/tests/test_contradiction_gold.py`. Consumer: T2.52's miss-rate
runner, which measures the combined same-endpoint + `pg_trgm` candidate
generator's recall against the `contradiction` pairs and reads the
negative slices as filter/adjudication checks (below).

## The error asymmetry, and where labelling effort went

**A false positive in this gold is far more expensive than a false
negative.** The veto is absolute: one non-echo contradiction over an
overlapping window demotes a fact to `disputed`, and consensus cannot
outvote it (doc 08 §4.2). A pair mislabelled `contradiction` therefore
teaches the pipeline downstream of this gold to manufacture disputes —
the one direction of error doc 08 §5.3 forbids — while a mislabelled
negative merely delays a catch, the stated preferred failure. Labelling
effort here is weighted accordingly, in three concrete ways:

1. **Positives rest only on watertight exclusion grounds.** Every
   `contradiction` pair is an inverse-replacement or exclusive-relation
   reversal (the rules below) — the grounds the entailment gold ratified
   and the shipped veto's own deterministic rule already encodes. No
   positive rests on a single-valued-slot judgment: the entailment
   corpus's three *unratified* exclusive-slot extensions (host-of-instance,
   IS_A-kind, REPLACES-object; see the entailment `LABELLING.md`'s
   Step-5 fork section) are deliberately **not used as contradiction
   grounds here**, so no owner ruling on them can invalidate a positive
   label in this file. The shipped veto's own finding that
   `SINGLE_VALUED_RELATIONS` is empty — no stored relation is
   single-valued across its senses — is treated as binding.
2. **The negative classes get more pairs than strictly required.** 28 of
   50 pairs are negatives, one hard class per naive-generator failure
   mode, because the false-positive side is where a gold error costs a
   true fact its badge.
3. **Every machine-checkable precondition is enforced by the loader**, so
   only the genuinely human judgment (does content oppose?) rests on a
   rationale.

## What a pair is

Two **sides**, `a` and `b`, each a materializable `knowledge_triples` row:
`subject_name` / `rel_type` / `object_name` (canonical lowercase, closed
relation vocabulary), `fact` (byte-equal to the shipping `fact_sentence`
rendering — the trigram arm runs over renderer-minted text, so free-text
sides would measure a distribution the table cannot contain), `project`,
a half-open belief window `[valid_at, invalid_at)` (null = unbounded, the
shipped `windows_overlap` convention, imported not re-implemented), and
`origin_keys` (the distinct attributable origins backing the row's
`fact_sources`). Sides are unordered; the label is symmetric.

**`label` is veto-grade**: `contradiction` means the pair satisfies all
three veto conjuncts — genuinely opposed content, overlapping validity
windows, independent origins. `not-contradiction` means at least one
conjunct fails; the slice names which one, and each negative slice is
built so exactly one conjunct is the reason (the loader enforces the other
two hold), keeping every label attributable.

**Known representational limit.** The shipped echo test is asymmetric
(the challenger must bring a fresh witness), so an origin structure like
{a} vs {a, b} disputes one side only. A symmetric pair label cannot
express that; such structures are excluded here — positives require
*disjoint* origin sets, echoes require *equal* ones — and the asymmetric
middle belongs to `tests/test_contradiction_veto.py`, not to this gold.

## Opposition grounds — the admissible rules, cited by name

- **Inverse-replacement rule.** A REPLACES-family edge (`REPLACES`,
  `IMPROVES_ON`; the family is one bucket, `relations.REPLACES_FAMILY`)
  asserted in both directions between the same two referents over one
  window: directed succession cannot run both ways. This is the shipped
  deterministic veto rule (T2.04) verbatim.
- **Exclusive-reversal rule.** Both directions of a relation the
  entailment gold's reversal-exclusivity table (ratified 2026-08-03)
  classes exclusive — `HAS_PART`, `IMPLEMENTS`, `EXTENDS`, `IS_A`,
  `DEPLOYED_ON`, `AUTHORED_BY`, `HAPPENED_ON` — asserted over the same
  ordered pair of referents. Antisymmetry makes the cycle incoherent.
  Note the exclusivity governs *role reversal for one pair*; it says
  nothing about object multiplicity (see multi-valued-slot below).
- **Alias completion.** Either rule above may bind through declared
  co-reference: when a side names a referent differently ("k8s" /
  "kubernetes", "elephant database" / "postgres 16"), the rationale
  **must state the co-reference explicitly** — it is part of the label
  and re-adjudicated with it. This is deliberate: doc 17 §5.2's designed
  blind spot ("uses postgres 14" vs "migrated the datastore off
  relational") is exactly opposition mediated by reference, not by
  tokens.

Not admissible as positive grounds today: single-valued-slot value
conflicts (no stored relation qualifies — the veto module's finding),
negation (the renderer cannot mint a negated fact text), and anything
resting on the entailment corpus's unratified extensions. When real
disputes arrive (`real-dispute` provenance below) or a slot rule is
ratified, new positive classes enter by editing **this file first**,
then appending pairs — rule-then-pairs, inherited discipline.

## The six slices

One slice per pair (v1 discipline). The loader enforces each slice's
label **and** its structural preconditions; ↺ marks what stays human.

| Slice | Label | Structure (loader-enforced) | Human judgment ↺ |
|---|---|---|---|
| `same-endpoint` | contradiction | shares ≥ 1 full endpoint name; windows overlap; origins disjoint | opposition under a named rule |
| `lexically-disjoint` | contradiction | endpoint-name token sets disjoint; windows overlap; origins disjoint | opposition + declared co-reference |
| `non-overlap` | not-contradiction | `windows_overlap` is False; shares an endpoint name; origins disjoint | sides would oppose if windows met |
| `echo` | not-contradiction | origin sets equal; windows overlap; shares an endpoint name | sides would oppose but for the shared origin |
| `similar-unrelated` | not-contradiction | ≥ 1 shared name token, no shared full name; windows overlap; origins disjoint | no opposition despite similarity |
| `compatible-same-endpoint` | not-contradiction | shares ≥ 1 full endpoint name; windows overlap; origins disjoint | slot is multi-valued; both facts stand |

What each slice measures for T2.52:

- The two positive slices split the **recall** number: `same-endpoint`
  pairs must be surfaced by the index-lookup arm; `lexically-disjoint`
  pairs are the trigram shortlist's designed blind spot, and the miss
  rate **on that slice alone** is the `triple_embeddings` writer trigger
  (bar: the `contradiction_missrate_bar` config row, recommended default
  > 20%, doc 17 §5.2 — stated before any run).
- `non-overlap` pairs are shaped so the generator *would* surface them;
  the overlap filter must then discard them (doc 08 §5.3 scores only
  overlapping-window pairs). A non-overlap pair reported as a candidate
  scored by the LLM is a filter defect.
- `echo` pairs exercise the non-echo requirement: content that opposes,
  witnessed by no independent origin, must not veto.
- `similar-unrelated` and `compatible-same-endpoint` are shortlist bait
  the *adjudicator* must reject; for the generator they are lawful
  candidates (recall gold never punishes surfacing a negative), so they
  qualify the scan's precision, not the generator's recall.

Negative-slice purity: each negative slice fails exactly one veto
conjunct. In `similar-unrelated` and `compatible-same-endpoint` the
failing conjunct is opposition itself, and windows/origins are pinned
valid so nothing else can be the reason.

## Decision procedure

1. **Adjudicate the pair in isolation.** Each pair is its own
   micro-world; cross-pair coherence is not required and not implied
   (two pairs may assume different histories for one technology).
2. **Ask the three conjuncts in order**: opposed content (under a named
   admissible rule, with co-references declared)? Overlapping windows
   (the imported `windows_overlap`, half-open, null-unbounded)?
   Independent origins (disjoint sets)? All three → `contradiction`;
   otherwise `not-contradiction`, sliced by the failing conjunct.
3. **Doubt resolves to `not-contradiction`.** The asymmetry section
   above is normative: a pair whose opposition needs an unratified rule,
   a stretched co-reference, or world knowledge the sides do not carry
   does not enter as a positive.

## Provenance — per side, honesty over volume

Provenance is **per side**, because genuine contradictions are almost
never two real rows: a coherent corpus does not mint opposing facts, so
real material enters one side at a time.

- `l2-fact` — the side is byte-anchored to the entailment gold's
  committed harvest manifest (`entailment/l2_harvest.json`), same
  `fact_key` contract, manifest row as source of truth. Anchored sides
  keep the open-ended window the harvest minted (`fact_lift` renders
  every lifted row open — the one-reachable-branch finding), so every
  bounded-window side is necessarily hand-authored; that is this gold's
  analogue of the entailment `temporal` exemption, and it sunsets the
  same way (a producer that mints windows).
- `hand-authored-synthetic-fact` — authored for this set, through the
  shipping renderer, in the corpus domain.
- `real-dispute` — **reserved, zero sides today.** For sides taken from
  production disputes once the contradiction scan exists and the owner
  adjudicates one (doc 17 §5.2: "each adjudicated dispute is a free gold
  candidate"). The count is pinned to zero by test; a producer landing
  moves the pin visibly, never relabels existing sides.

**Origins and windows are gold-fixture dimensions**, not part of the
anchor: the manifest models neither, so `origin_keys` (and windows on
hand-authored sides) are authored world-state. One consequence is
disclosed rather than hidden: cg-0047's two real sides were minted from
a single memory in the recorded run, but the gold fixes independent
origins so the compatibility question — not the echo question — is that
pair's single point.

21 of 100 sides are anchored (l2-fact). Doc 17 §11's ≥ 50%-real floor
binds the judge-qualification gold, not this file; it is structurally
unreachable here because a real side's opposing counterpart cannot be
real (above). The honest statement is this paragraph plus the declared
counts, and the growth path to more real material is `real-dispute`.

## Composition — a design decision, stated with its justification

50 pairs: 22 `contradiction` (10 same-endpoint, 12 lexically-disjoint),
28 `not-contradiction` (7 non-overlap, 7 echo, 8 similar-unrelated, 6
compatible-same-endpoint).

- **Total and positive split.** Doc 17 §5.2 recommends ≥ 50 pairs with
  "at least half lexically disjoint"; read here as half of the
  *contradiction* pairs (12/22 = 55%), since the disjoint slice exists to
  power the recall measurement and only positives enter recall. Reading
  it as half of all pairs would crowd out the negative classes, which
  the T2.57 brief names as the point of the set.
- **Disjoint-slice power.** 12 disjoint positives give the miss rate a
  granularity of 1/12 ≈ 8.3%, so the recommended 20% bar is breached at
  3 misses — coarse but sufficient for a writer-trigger decision; grown
  from real disputes as they occur rather than padded now.
- **Negative sizing.** Each negative class carries 6–8 pairs — enough
  that a systematic filter or adjudication failure shows as a pattern,
  not a single flake — and every pair within a class varies relation,
  domain and mechanism, because near-duplicate padding is explicitly
  refused (doc 17 §11's stance applied here).
- **Mechanism monoculture, disclosed.** All 22 positives are
  reversal-family oppositions, because those are the only watertight
  grounds available in renderer-rendered triple space today (see the
  admissible-rules section). This is a known narrowing of the positive
  distribution, accepted in exchange for a zero-false-positive design
  target; it widens when real disputes or ratified slot rules arrive.

## File discipline (doc 17 §11, inherited)

- **Append-only.** New pairs take the next `cg-` id at the end. A wrong
  pair is retired in place (`"retired": true` + reason in `notes`) —
  never deleted, rewritten, or reordered.
- **Declared counts** (slice, label, side-provenance) cover live pairs
  only and move with every append or retirement, visibly. Side counts
  count sides: two per live pair.
- **Labelling is generator- and judge-blind.** No pair may be added,
  retired, or relabelled because of what the candidate generator or any
  judge model does with it. If a run disagrees with a pair, the pair is
  re-examined against these rules; if the rules were wrong, this file
  changes first, visibly, with the rationale.
- **Rule-then-pairs.** A new opposition ground or slice is ratified in
  this file before any pair uses it.

## Divergences from the entailment gold's conventions, and why

The schema, adjudication lifecycle (`author` → `adjudicated`),
append-only discipline, declared-counts pattern, anchor contract and
labelling-rules-file shape are inherited. The deliberate divergences:

1. **Pairs of sides, not premise/hypothesis.** The unit under test is a
   symmetric pair of fact rows, not a directed claim-against-fact check.
2. **Provenance is per side**, with `real-dispute` replacing
   `synthesis-draft` as the reserved-at-zero future producer. The
   `hand-authored-bench-corpus` provenance has no analogue: corpus
   entries are memory contents, and sides here must be renderer-minted
   fact texts.
3. **Sides carry structure (triple, window, origins), not just text**,
   because the system under measurement is SQL over `knowledge_triples`,
   not a text-only judge; and the loader binds that structure to the
   shipping code by import (`fact_sentence`, `compute_triple_key`,
   `windows_overlap`, `RELATIONSHIP_TYPES`) so gold semantics cannot
   drift from code semantics.
4. **Labels are two-way, not three-way.** The veto is binary; the
   finer "why not" split lives in the slice tag, which the loader
   cross-checks structurally where possible.

## History

- **2026-08-05 (T2.57).** 50 pairs seeded, author-labelled; composition,
  admissible rules and the error-asymmetry policy fixed in this file in
  the same change as the pairs. Independent re-adjudication (flipping
  `label_source` to `adjudicated`) is future work for the T2.52/T2.33
  gate owner, mirroring the entailment T2.25 → T2.54 split.
