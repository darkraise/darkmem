/**
 * A structural mirror of the backend's one badge-claim producer —
 * `backend/app/services/fact_badge.py::build_claim` (doc 12 §4, doc 13
 * §5.3, invariant 14).
 *
 * T2.75: doc 13 §5.3 forbids any screen paraphrasing the badge claim, but
 * nothing under `frontend/` checked that before this module — the
 * backend's own guards (T2.36a's certainty-word check, T2.71/T2.77's
 * second-producer scan) walk `backend/app` only and cannot see a demo
 * fixture or a component comment. This module recognises every SHAPE
 * `build_claim` can produce and rejects everything else; it is a grammar
 * check, not a byte-for-byte oracle against a specific fixture's data.
 *
 * **What walks this grammar** (fix round 2026-08-04a, F4): every
 * `frontend/src/demo/data/*-curated.ts` module, discovered by
 * `import.meta.glob` in `__tests__/badge-grammar.test.ts` rather than by a
 * hand-listed import set — a new curated file needs no change here to be
 * covered. Within each module the walk collects every string found under
 * the exact keys `claim`, `badge_claim`, and `badge_line`, at any nesting
 * depth, in any array or object. This is a **named-field convention, not a
 * free-text scan**: a badge string authored under a different key in a new
 * file (the way `settings-curated.ts`'s `inject_items[].text` composes one
 * into a longer sentence, or `memories-curated.ts`'s `verification_detail`
 * does) is not discovered, and is a stated residual, not an oversight —
 * doc 15 treats both as compositions of the badge string rather than the
 * badge string itself, which is the same reasoning T2.75's original review
 * used to clear them.
 *
 * Two files needed a rename, not just discovery, because `claim` meant a
 * second thing in each and a generic walk over the bare key name would
 * have false-failed on every occurrence of that second thing:
 *
 * - `activity-curated.ts`'s `DemoDreamAction.claim` was overloaded between a
 *   real ladder transition's badge (promotion, ratification) and narrative
 *   prose about a *different* kind of dream action (refine's before/after,
 *   a demotion's reason, invalidation's closure sentence) — text that was
 *   never meant to look like `build_claim`'s output. The two are now
 *   different fields: a genuine post-transition badge is `badge_claim`;
 *   the narrative one is renamed to `note` (not `claim`, since bare `claim`
 *   also means a genuine badge in `knowledge-curated.ts` and a single walked
 *   key cannot mean two things) and is not walked. The dispute-cycle legend
 *   at
 *   `CURATED_DREAM_CYCLE.disputed.legend` — a verbatim quote of this
 *   module's own doc comment above, `"disputed: 2 origins assert X, 1
 *   origin asserts not-X, as of T"`, teaching the shape rather than
 *   instantiating it — is named `legend`, not `claim`, for the same reason.
 * - `chat-curated.ts`'s `ChatContextRow.claim` was never a badge at all: it
 *   is the row's subject text (a fact's plain-English statement, or a
 *   quoted L0 memory's content), always paired with a separate `badge_line`
 *   that carries the actual badge. Renamed to `subject_text` so the walk
 *   below can collect `claim` unconditionally everywhere it still appears
 *   (knowledge-curated.ts's facts and articles) without also collecting ten
 *   sentences that were never claims.
 *
 * After both renames, every remaining `claim`, `badge_claim` and
 * `badge_line` field, in every curated file, really is a badge string —
 * the walk needs no further per-file exception.
 *
 * **What this catches**, proven by the paired mutation test in
 * `__tests__/badge-grammar.test.ts`: an invented sentence with no
 * counterpart in the producer's grammar (e.g. "extracted signal, not yet
 * corroborated"); a wrong number/noun agreement (the producer always says
 * "distinct origin**s**" for a count other than 1, and always literally
 * "of kind**s**" regardless of count — "of kind" singular is not a shape
 * the producer emits); an added attribution the producer never emits
 * ("human-ratified by <name> on <date>" — the producer's confirmed suffix
 * is a bare ", human-ratified" with no name and no date beyond the
 * sentence's own `as of`); a reordered or renamed connective; and the two
 * forbidden certainty words ("true", "verified") appearing in the badge's
 * own voice — mirroring `assert_no_certainty_words`, including the part of
 * its rule that matters most: the words are forbidden in the *template*,
 * never in interpolated data (F6, below).
 *
 * **What this does NOT catch**, stated rather than hidden:
 *
 * - A claim shaped correctly but wrong on the *numbers* for its own
 *   fixture — e.g. "asserted by 3 distinct origins" on a fixture whose
 *   `sources` array has 2 distinct `origin_key`s. Nothing here re-derives
 *   the count from `sources`, so a grammatically legal but
 *   data-inconsistent claim passes. That is a different, narrower property
 *   `demo/__tests__/knowledge.test.ts` already partly covers for origin
 *   counting — this module does not claim to be that test.
 * - **Kind-list shapes the real producer can never emit (F7).** `origin_kinds`
 *   is accepted unsorted, with duplicates, or drawn from outside the closed
 *   vocabulary (`memory`, `code`, `human`, and the reserved `block`) —
 *   `OriginProfile.source_kinds` on the backend is `tuple(sorted({...}))`,
 *   always sorted and deduplicated, so `[memory, code]`, `[code, code]` and
 *   `[banana, banana]` all pass here despite none being real backend output.
 * - **The L0 carve-out is prefix-anchored (F7).** `NO_BADGE_LIFECYCLE` only
 *   checks that the text *starts with* "no verification badge on this row —
 *   badge: null"; anything appended after that prefix — including a second,
 *   fabricated sentence — still passes.
 * - **Mirror drift from the real producer (F5), the residual that matters
 *   most.** This grammar and `buildAssertedByClaim` below are one
 *   hand-maintained TypeScript file; nothing in CI ever executes the real
 *   `build_claim`. If doc 12's sentence changes on the backend, this file
 *   does not know: the regex and the generator stay mutually consistent
 *   with each other and with every demo fixture, and the whole suite stays
 *   green while every string here quietly drifts from what the backend
 *   actually emits. Closing this needs a backend-pinned oracle (a small
 *   JSON of real `build_claim` outputs for a fixed input matrix, generated
 *   from Python and committed, that a vitest test asserts this port
 *   reproduces byte-for-byte); this fix round chose to state the residual
 *   rather than build that harness — see the commit body for the argument.
 *   Acceptable today because `buildAssertedByClaim` is demo-quarantined:
 *   nothing outside `frontend/src/demo/` imports it, and the real wire
 *   surface it would otherwise race does not exist yet.
 *
 * **On articles specifically**: `backend/app/services/layer_composition.py`
 * (`derive_badges`) mints a badge for `id_kind == "fact"` only and
 * deliberately raises rather than minting a null one for `id_kind ==
 * "article"` — the article channel is T3.02's and unshipped, so there is
 * today no live call site producing an article's claim at all, unlike a
 * fact's. Every non-null `CURATED_ARTICLES` claim in this demo already
 * happens to follow `build_claim`'s exact grammar (`origin_count` mirrors
 * `coverage.entailed`), so this module validates article claims against
 * the same grammar as facts on that basis — an inference from the
 * existing fixtures' own convention, not a confirmed backend contract.
 */

const DATE = String.raw`\d{4}-\d{2}-\d{2}`
const TAIL = String.raw`(?:, as of ${DATE}|, checked as of ${DATE}|, verification not yet recomputed)`
const KINDS = String.raw`\[(?:[a-z]+(?:, [a-z]+)*)?\]`

// "asserted by N distinct origin(s) of kinds [...], no known contradiction
// {tail}[, human-ratified]" — fact_badge.build_claim's non-disputed branch.
const PLAIN = new RegExp(
  `^asserted by (\\d+) distinct (origins?) of kinds (${KINDS}), no known contradiction(${TAIL})(, human-ratified)?$`,
)

// "disputed: {mine} {claim}, {theirs} {counterpart}{tail}" or, lacking a
// journalled counterpart, "disputed: {mine} {claim}, the contradicting
// claim was not recorded{tail}" — build_claim's DISPUTED branch.
const DISPUTED = new RegExp(
  `^disputed: (\\d+) (origin asserts|origins assert) (.+?), (?:(\\d+) (origin asserts|origins assert) (.+?)|the contradicting claim was not recorded)(${TAIL})$`,
)

// L0 memories carry lifecycle, not the ladder (doc 12): `badge` is null,
// and this is the UI's own description of that null state, not a claim
// shape build_claim could ever produce — it never runs through the
// grammar below.
const NO_BADGE_LIFECYCLE = /^no verification badge on this row — badge: null/

// Mirrors fact_badge.assert_no_certainty_words: the badge's own TEMPLATE
// voice may never claim "true" or "verified". This is guarded on the
// residue after the interpolated data is stripped out, exactly as the
// backend's `_render` does — the backend's own docstring is explicit that
// the rule is guarded on the badge's vocabulary, not the data, precisely
// because a disputed claim's interpolated `claim_text`/`counterpart_text`
// can legally contain either word (e.g. a fact about a boolean flag
// defaulting to `true`). Checking the whole string, interpolated data
// included, is a proven false positive (F6): it rejects a sentence
// `build_claim` legitimately emits.
const CERTAINTY_WORDS = /\b(?:true|verified)\b/i

export interface BadgeClaimCheck {
  ok: boolean
  reason?: string
}

function nounFrom(phrase: string): "origin" | "origins" {
  return phrase.startsWith("origins") ? "origins" : "origin"
}

function agrees(count: string, phrase: string): boolean {
  const singular = Number(count) === 1
  return nounFrom(phrase) === (singular ? "origin" : "origins")
}

/**
 * Remove every interpolated value from `text`, mirroring `fact_badge._render`
 * exactly: the certainty-word check runs on what remains (the template's own
 * words), never on data a caller supplied. Values are removed wholesale
 * (every occurrence), not word-by-word, so a forbidden word embedded inside
 * an interpolated phrase is removed along with the phrase that contains it.
 */
function stripInterpolated(text: string, values: ReadonlyArray<string | undefined>): string {
  let residue = text
  for (const value of values) {
    if (value) residue = residue.split(value).join(" ")
  }
  return residue
}

/** Does `text` match a shape `fact_badge.build_claim` can produce? */
export function validateBadgeClaim(text: string): BadgeClaimCheck {
  if (NO_BADGE_LIFECYCLE.test(text)) {
    if (CERTAINTY_WORDS.test(text)) {
      return { ok: false, reason: `contains a forbidden certainty word: "${text}"` }
    }
    return { ok: true }
  }

  const plain = PLAIN.exec(text)
  if (plain) {
    // Groups 1-2 are mandatory in PLAIN (not inside any `?` construct), so a
    // successful match guarantees both are present.
    const count = plain[1]!
    const noun = plain[2]!
    const kindsBracket = plain[3]!
    if (!agrees(count, noun)) {
      return { ok: false, reason: `origin count/noun disagree: "${text}"` }
    }
    // origin_kinds is the only interpolated data in the plain form (F6): the
    // bracket's contents, not the surrounding "of kinds [...]" template.
    const kinds = kindsBracket
      .slice(1, -1)
      .split(", ")
      .filter((kind) => kind.length > 0)
    const residue = stripInterpolated(text, kinds)
    if (CERTAINTY_WORDS.test(residue)) {
      return { ok: false, reason: `contains a forbidden certainty word: "${text}"` }
    }
    return { ok: true }
  }

  const disputed = DISPUTED.exec(text)
  if (disputed) {
    // Groups 1-3 are mandatory; 4-6 exist together only on the
    // with-counterpart alternative, so testing one for undefined covers all
    // three.
    const mineCount = disputed[1]!
    const minePhrase = disputed[2]!
    const mineText = disputed[3]!
    const theirsCount = disputed[4]
    const theirsPhrase = disputed[5]
    const theirsText = disputed[6]
    if (!agrees(mineCount, minePhrase)) {
      return { ok: false, reason: `disputed origin count/noun disagree (mine): "${text}"` }
    }
    if (theirsCount !== undefined && !agrees(theirsCount, theirsPhrase!)) {
      return { ok: false, reason: `disputed origin count/noun disagree (theirs): "${text}"` }
    }
    // mineText/theirsText are the disputed form's interpolated data (F6):
    // the fact's own triple and its counterpart's, which may legally
    // contain "true" or "verified" as part of what is being disputed (e.g.
    // a claim about a boolean flag's default).
    const residue = stripInterpolated(text, [mineText, theirsText])
    if (CERTAINTY_WORDS.test(residue)) {
      return { ok: false, reason: `contains a forbidden certainty word: "${text}"` }
    }
    return { ok: true }
  }

  return { ok: false, reason: `matches no shape build_claim can produce: "${text}"` }
}

export function isValidBadgeClaim(text: string): boolean {
  return validateBadgeClaim(text).ok
}

/**
 * A TS port of `build_claim`'s non-disputed branch — the one shape the
 * demo's interactive code (`demo/store.ts`'s ratify actions) needs to
 * generate at runtime rather than merely validate. R2 (T2.75): generating
 * is the stronger option and is worth it here because the string is
 * actually *computed*, not hand-authored prose — the two ratify actions
 * used to interpolate `by`/`on` straight into a made-up "human-ratified
 * by X on Y" sentence, a shape `build_claim` never emits. Kept deliberately
 * narrow: no disputed-form generator exists because nothing in this demo
 * ratifies a fact or article out of the `disputed` state directly.
 */
export function buildAssertedByClaim({
  originCount,
  kinds,
  asOf,
  humanRatified,
}: {
  originCount: number
  kinds: readonly string[]
  asOf: string
  humanRatified: boolean
}): string {
  const noun = originCount === 1 ? "origin" : "origins"
  const sortedKinds = Array.from(new Set(kinds)).sort()
  const base =
    `asserted by ${originCount} distinct ${noun} of kinds [${sortedKinds.join(", ")}], ` +
    `no known contradiction, as of ${asOf}`
  return humanRatified ? `${base}, human-ratified` : base
}
