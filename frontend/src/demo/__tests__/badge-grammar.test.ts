import { afterEach, describe, expect, it } from "vitest"
import {
  ARTICLE_IDS,
  CURATED_REVIEW_ITEMS,
  FACT_IDS,
} from "../data/knowledge-curated"
import { validateBadgeClaim } from "../badge-grammar"
import { useDemoStore } from "../store"

// T2.75 (fix round 2026-08-04a, F4): the original guard imported exactly
// knowledge-curated.ts and chat-curated.ts by name -- "the two files
// T2.71's review found" -- and every other demo data file was invisible to
// it. The reviewer proved the hole by planting a fresh badge paraphrase in
// activity-curated.ts (the same divergence class this suite exists to
// catch) and watching the whole frontend suite pass 535/535. This glob
// discovers every `*-curated.ts` module under `../data` instead of a
// hand-listed import set, so a new curated file is covered the moment it
// exists, with no change needed here.
const CURATED_MODULES = import.meta.glob<Record<string, unknown>>(
  "../data/*-curated.ts",
  { eager: true },
)

// Exact field-name convention, not a free-text scan (see badge-grammar.ts's
// module docstring, "What walks this grammar"): a badge string authored
// under a different key (settings-curated.ts's `inject_items[].text`,
// memories-curated.ts's `verification_detail`) composes the claim into a
// longer sentence and is a stated residual, not covered here.
const CLAIM_KEYS = new Set(["claim", "badge_claim", "badge_line"])

function collectBadgeClaims(node: unknown, out: string[] = []): string[] {
  if (Array.isArray(node)) {
    for (const item of node) collectBadgeClaims(item, out)
  } else if (node !== null && typeof node === "object") {
    for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
      if (CLAIM_KEYS.has(key) && typeof value === "string") {
        out.push(value)
      } else {
        collectBadgeClaims(value, out)
      }
    }
  }
  return out
}

describe("every badge claim in frontend/src/demo/data matches a shape the producer can emit", () => {
  it("discovers every *-curated.ts module (not a hand-listed import set)", () => {
    // Pinned to a floor, not an exact count: the glob returning fewer than
    // the seven curated files on disk today means the pattern or the vitest
    // glob wiring broke, which is exactly the silent-omission failure mode
    // this test exists to rule out. A file added later only raises this.
    expect(Object.keys(CURATED_MODULES).length).toBeGreaterThanOrEqual(7)
  })

  it("validates every claim/badge_claim/badge_line string found, at any depth, in any module", () => {
    const claims = Object.values(CURATED_MODULES).flatMap((mod) =>
      collectBadgeClaims(mod),
    )

    expect(claims.length).toBeGreaterThan(0)

    const failures = claims
      .map((c) => ({ c, check: validateBadgeClaim(c) }))
      .filter(({ check }) => !check.ok)

    expect(failures.map((f) => f.check.reason)).toEqual([])
  })
})

describe("the grammar actually rejects what it claims to reject — proven, not assumed", () => {
  const GOOD =
    "asserted by 2 distinct origins of kinds [human, memory], no known contradiction, as of 2026-07-21, human-ratified"

  it("accepts the producer's real confirmed form", () => {
    expect(validateBadgeClaim(GOOD).ok).toBe(true)
  })

  it("accepts the producer's checked form for a fact the recompute held", () => {
    expect(
      validateBadgeClaim(
        "asserted by 1 distinct origin of kinds [memory], no known contradiction, checked as of 2026-10-05",
      ).ok,
    ).toBe(true)
  })

  it("rejects an added human attribution the producer never emits (the T2.75 divergence, replanted)", () => {
    const paraphrase =
      "human-ratified by q.tran on 2026-07-21; previously asserted by 2 distinct origins of kinds [human, memory]"
    const result = validateBadgeClaim(paraphrase)
    expect(result.ok).toBe(false)
    expect(result.reason).toMatch(/matches no shape/)
  })

  it("rejects singular 'of kind' where the producer always says 'of kinds'", () => {
    const result = validateBadgeClaim(
      "asserted by 1 distinct origin of kind [memory], no known contradiction, as of 2026-07-23",
    )
    expect(result.ok).toBe(false)
  })

  it("rejects a wholly invented sentence with no counterpart in the grammar", () => {
    const result = validateBadgeClaim(
      "extracted signal, not yet corroborated — 1 origin, as of 2026-07-18",
    )
    expect(result.ok).toBe(false)
    expect(result.reason).toMatch(/matches no shape/)
  })

  it("rejects the forbidden certainty words in the template itself, not interpolated data", () => {
    expect(validateBadgeClaim("this fact is verified").ok).toBe(false)
    expect(validateBadgeClaim("this claim is true").ok).toBe(false)
  })

  it("still accepts the real form once the paraphrase is corrected", () => {
    expect(
      validateBadgeClaim(
        "asserted by 1 distinct origin of kinds [memory], no known contradiction, as of 2026-07-23",
      ).ok,
    ).toBe(true)
  })

  // F6: proven against the real backend producer (build_claim(
  //   verification_status="disputed", origin_count=2, origin_kinds=["code","memory"],
  //   as_of=2026-07-24, claim_text="reranker_enabled DEFAULTS_TO true",
  //   counterpart_text="reranker_enabled DEFAULTS_TO false", counterpart_origin_count=1,
  // )) -- fact_badge._render strips claim_text/counterpart_text before checking
  // certainty words, so this sentence is legal backend output. The old
  // whole-string CERTAINTY_WORDS check rejected it; this is the reason it
  // must not.
  it("accepts a disputed claim whose interpolated data legally contains 'true' (F6)", () => {
    const realProducerOutput =
      "disputed: 2 origins assert reranker_enabled DEFAULTS_TO true, 1 origin asserts reranker_enabled DEFAULTS_TO false, as of 2026-07-24"
    expect(validateBadgeClaim(realProducerOutput)).toEqual({ ok: true })
  })

  // Guards the fix itself: interpolated data does not get a free pass on
  // shape or agreement checks, only on the certainty-word check.
  it("still rejects a disputed claim with interpolated data if the count/noun disagree", () => {
    const result = validateBadgeClaim(
      "disputed: 2 origin asserts reranker_enabled DEFAULTS_TO true, 1 origin asserts reranker_enabled DEFAULTS_TO false, as of 2026-07-24",
    )
    expect(result.ok).toBe(false)
  })
})

// T2.75: the divergence wasn't only a static fixture — `demo/store.ts`'s
// ratify actions generated `human-ratified by {by} on {on}` at runtime,
// the same unemittable shape, on every interactive ratification. These
// two prove the LIVE code path, not just the data it starts from.
describe("the interactive ratify actions generate a real badge claim, not hand-built prose", () => {
  afterEach(() => {
    useDemoStore.getState().resetKnowledge()
  })

  it("ratifying a fact produces a claim the producer could emit", () => {
    const reviewItem = CURATED_REVIEW_ITEMS.find(
      (r) => r.kind === "fact" && r.target_id === FACT_IDS.rerankerDefault,
    )
    expect(reviewItem).toBeDefined()

    useDemoStore.getState().ratifyReviewItem(reviewItem!.id, "j.rivera")
    const ratified = useDemoStore
      .getState()
      .facts.find((f) => f.id === FACT_IDS.rerankerDefault)

    expect(ratified?.verification_status).toBe("confirmed")
    expect(ratified?.claim).not.toBeNull()
    expect(validateBadgeClaim(ratified!.claim!)).toEqual({ ok: true })
    expect(ratified?.claim).not.toMatch(/j\.rivera/)
  })

  it("ratifying an article produces a claim the producer could emit", () => {
    const reviewItem = CURATED_REVIEW_ITEMS.find(
      (r) => r.kind === "article" && r.target_id === ARTICLE_IDS.providerQuirks,
    )
    expect(reviewItem).toBeDefined()

    useDemoStore.getState().ratifyReviewItem(reviewItem!.id, "j.rivera")
    const ratified = useDemoStore
      .getState()
      .articles.find((a) => a.id === ARTICLE_IDS.providerQuirks)

    expect(ratified?.verification_status).toBe("confirmed")
    expect(ratified?.claim).not.toBeNull()
    expect(validateBadgeClaim(ratified!.claim!)).toEqual({ ok: true })
    expect(ratified?.claim).not.toMatch(/j\.rivera/)
  })
})
