import { afterEach, describe, expect, it } from "vitest"
import {
  ARTICLE_IDS,
  CURATED_ARTICLES,
  CURATED_FACTS,
  CURATED_REVIEW_ITEMS,
  FACT_IDS,
} from "../data/knowledge-curated"
import { CURATED_CHAT_THREADS, DEMO_REPLY_CONTEXT } from "../data/chat-curated"
import { validateBadgeClaim } from "../badge-grammar"
import { useDemoStore } from "../store"

// T2.75: knowledge-curated.ts and chat-curated.ts are the two files T2.71's
// review found carrying badge-shaped claim strings the backend's own
// second-producer scan cannot see (it walks backend/app only). This suite
// is that missing coverage for frontend/ — every `claim` this demo treats
// as the fact/article badge, and every `badge_line` chat's turn-context
// rows carry, must be a shape fact_badge.build_claim can actually emit.

function collectStrings(node: unknown, key: string, out: string[] = []): string[] {
  if (Array.isArray(node)) {
    for (const item of node) collectStrings(item, key, out)
  } else if (node !== null && typeof node === "object") {
    for (const [k, v] of Object.entries(node as Record<string, unknown>)) {
      if (k === key && typeof v === "string") out.push(v)
      else collectStrings(v, key, out)
    }
  }
  return out
}

describe("every badge claim in frontend/ matches a shape the producer can emit", () => {
  it("knowledge-curated's fact and article claims", () => {
    const claims = [
      ...CURATED_FACTS.map((f) => f.claim),
      ...CURATED_ARTICLES.map((a) => a.claim),
    ].filter((c): c is string => typeof c === "string")

    expect(claims.length).toBeGreaterThan(0)

    const failures = claims
      .map((c) => ({ c, check: validateBadgeClaim(c) }))
      .filter(({ check }) => !check.ok)

    expect(failures.map((f) => f.check.reason)).toEqual([])
  })

  it("chat-curated's badge_line entries, at every nesting depth", () => {
    const lines = [
      ...collectStrings(CURATED_CHAT_THREADS, "badge_line"),
      ...collectStrings(DEMO_REPLY_CONTEXT, "badge_line"),
    ]

    expect(lines.length).toBeGreaterThan(0)

    const failures = lines
      .map((line) => ({ line, check: validateBadgeClaim(line) }))
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

  it("rejects the forbidden certainty words even inside an otherwise-legal sentence", () => {
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
