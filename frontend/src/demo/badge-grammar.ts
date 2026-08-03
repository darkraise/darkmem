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
 * own voice, mirroring `assert_no_certainty_words`.
 *
 * **What this does NOT catch**, stated rather than hidden: a claim that
 * is shaped correctly but wrong on the *numbers* for its own fixture —
 * e.g. "asserted by 3 distinct origins" on a fixture whose `sources`
 * array has 2 distinct `origin_key`s. Nothing here re-derives the count
 * from `sources`, so a grammatically legal but data-inconsistent claim
 * passes. That is a different, narrower property
 * `demo/__tests__/knowledge.test.ts` already partly covers for origin
 * counting — this module does not claim to be that test.
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
const TAIL = String.raw`(?:, as of ${DATE}|, verification not yet recomputed)`
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

// Mirrors fact_badge.assert_no_certainty_words: the badge's own voice may
// never claim "true" or "verified", whatever the interpolated data says.
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

/** Does `text` match a shape `fact_badge.build_claim` can produce? */
export function validateBadgeClaim(text: string): BadgeClaimCheck {
  if (CERTAINTY_WORDS.test(text)) {
    return { ok: false, reason: `contains a forbidden certainty word: "${text}"` }
  }

  if (NO_BADGE_LIFECYCLE.test(text)) {
    return { ok: true }
  }

  const plain = PLAIN.exec(text)
  if (plain) {
    // Groups 1-2 are mandatory in PLAIN (not inside any `?` construct), so a
    // successful match guarantees both are present.
    const count = plain[1]!
    const noun = plain[2]!
    if (!agrees(count, noun)) {
      return { ok: false, reason: `origin count/noun disagree: "${text}"` }
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
    const theirsCount = disputed[4]
    const theirsPhrase = disputed[5]
    if (!agrees(mineCount, minePhrase)) {
      return { ok: false, reason: `disputed origin count/noun disagree (mine): "${text}"` }
    }
    if (theirsCount !== undefined && !agrees(theirsCount, theirsPhrase!)) {
      return { ok: false, reason: `disputed origin count/noun disagree (theirs): "${text}"` }
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
