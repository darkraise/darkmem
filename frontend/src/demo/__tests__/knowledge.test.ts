import { afterEach, describe, expect, it } from "vitest"
import {
  ARTICLE_IDS,
  CURATED_ARTICLES,
  CURATED_FACTS,
  FACT_IDS,
} from "../data/knowledge-curated"
import {
  distinctOriginCount,
  filterFacts,
  groupSourcesByOrigin,
  liveArticles,
  withheldArticles,
  RUNG_SORT,
} from "../knowledge"
import { useDemoStore } from "../store"

const heroFact = CURATED_FACTS.find((f) => f.id === FACT_IDS.semanticWeight)!

afterEach(() => {
  useDemoStore.getState().resetKnowledge()
})

describe("origin grouping", () => {
  it("counts DISTINCT origin_key, never raw rows — the echo pair counts once", () => {
    expect(heroFact.sources).toHaveLength(4)
    expect(distinctOriginCount(heroFact.sources)).toBe(3)
  })

  it("groups rows by origin_key preserving first-seen order", () => {
    const groups = groupSourcesByOrigin(heroFact.sources)
    expect(groups).toHaveLength(3)
    expect(groups[0]?.origin_key).toBe("session:9f21b7c4")
    expect(groups[0]?.rows).toHaveLength(2)
  })

  // T2.86: doc 10 §6's `stale` overlay, mirrored from the live door's
  // `FactSourceGroup.stale` — a group is stale only when every one of its
  // rows is, matching the backend's `OriginGroup.is_stale`.
  it("a group is stale only when every one of its rows is", () => {
    const allStale = groupSourcesByOrigin([
      { origin_key: "repo-a", kind: "code", ref: "r1", detail: "", at: "", stale: true },
      { origin_key: "repo-a", kind: "code", ref: "r2", detail: "", at: "", stale: true },
    ])
    expect(allStale[0]?.stale).toBe(true)

    const mixed = groupSourcesByOrigin([
      { origin_key: "repo-b", kind: "code", ref: "r3", detail: "", at: "", stale: true },
      { origin_key: "repo-b", kind: "code", ref: "r4", detail: "", at: "", stale: false },
    ])
    expect(mixed[0]?.stale).toBe(false)

    const none = groupSourcesByOrigin([
      { origin_key: "repo-c", kind: "code", ref: "r5", detail: "", at: "" },
    ])
    expect(none[0]?.stale).toBe(false)
  })
})

describe("filterFacts", () => {
  const all = { subject: "", relation: "any", status: "any", project: "all" }

  it("sorts confirmed → corroborated → disputed → candidate", () => {
    const sorted = filterFacts(CURATED_FACTS, all)
    const ranks = sorted.map((f) => RUNG_SORT[f.verification_status])
    expect(ranks).toEqual([...ranks].sort((a, b) => a - b))
    expect(sorted[0]?.verification_status).toBe("confirmed")
    const last = sorted[sorted.length - 1]
    expect(last?.verification_status).toBe("candidate")
  })

  it("scopes by project without deleting the other project's facts", () => {
    const darkmem = filterFacts(CURATED_FACTS, { ...all, project: "darkmem" })
    expect(darkmem.some((f) => f.project === "darkraise-ui")).toBe(false)
    expect(darkmem.length).toBe(CURATED_FACTS.length - 1)
  })

  it("filters by subject, relation, and status independently", () => {
    const bySubject = filterFacts(CURATED_FACTS, {
      ...all,
      subject: "semantic_weight",
    })
    expect(bySubject.map((f) => f.id)).toContain(FACT_IDS.semanticWeight)

    const byRelation = filterFacts(CURATED_FACTS, {
      ...all,
      relation: "DEPLOYED_ON",
    })
    expect(byRelation).toHaveLength(1)
    expect(byRelation[0]?.id).toBe(FACT_IDS.deployCompose)

    const disputed = filterFacts(CURATED_FACTS, { ...all, status: "disputed" })
    expect(disputed.length).toBeGreaterThan(0)
    expect(disputed.every((f) => f.verification_status === "disputed")).toBe(
      true,
    )
  })
})

describe("honesty invariants in the fixtures", () => {
  it("every disputed fact carries BOTH conflicting sides", () => {
    const disputed = CURATED_FACTS.filter(
      (f) => f.verification_status === "disputed",
    )
    expect(disputed.length).toBeGreaterThan(0)
    for (const fact of disputed) {
      expect(fact.dispute).toBeDefined()
      expect(fact.dispute?.sides).toHaveLength(2)
    }
  })

  it("stale label ⇔ fact_set_hash mismatch — never independently invented", () => {
    for (const article of CURATED_ARTICLES) {
      if (article.verification_status === "superseded") continue
      expect(article.stale != null).toBe(
        article.fact_set_hash !== article.current_fact_set_hash,
      )
    }
  })

  it("coverage ratio is entailed/total, a labelled measure, not a vague score", () => {
    for (const article of CURATED_ARTICLES) {
      const { ratio, entailed, total } = article.coverage
      expect(ratio).toBeCloseTo(entailed / total, 1)
    }
  })

  it("no citation dangles — every fact_id resolves to a curated fact", () => {
    const factIds = new Set(CURATED_FACTS.map((f) => f.id))
    for (const article of CURATED_ARTICLES) {
      for (const citation of article.citations) {
        expect(factIds.has(citation.fact_id)).toBe(true)
      }
    }
  })
})

describe("article visibility", () => {
  it("excludes superseded and review_state=open rows from the live list", () => {
    const live = liveArticles(CURATED_ARTICLES, "darkmem")
    const ids = live.map((a) => a.id)
    expect(ids).not.toContain(ARTICLE_IDS.retrievalFusionV1)
    expect(ids).not.toContain(ARTICLE_IDS.providerQuirks)
    expect(ids).toContain(ARTICLE_IDS.retrievalFusion)
  })

  it("routes the withheld ungrounded article to Review, not into the void", () => {
    const withheld = withheldArticles(CURATED_ARTICLES, "darkmem")
    expect(withheld.map((a) => a.id)).toEqual([ARTICLE_IDS.providerQuirks])
  })

  it("keeps the superseded predecessor reachable via lineage", () => {
    const predecessor = CURATED_ARTICLES.find(
      (a) => a.id === ARTICLE_IDS.retrievalFusionV1,
    )!
    expect(predecessor.superseded_by).toBe(ARTICLE_IDS.retrievalFusion)
    const successor = CURATED_ARTICLES.find(
      (a) => a.id === ARTICLE_IDS.retrievalFusion,
    )!
    expect(successor.supersedes).toBe(ARTICLE_IDS.retrievalFusionV1)
  })
})

describe("store actions", () => {
  it("ratify flips the fact to confirmed, writes a human origin, and closes the item", () => {
    const store = useDemoStore.getState()
    store.ratifyReviewItem("review-reranker-default", "q.tran")
    const state = useDemoStore.getState()

    expect(
      state.reviewItems.some((r) => r.id === "review-reranker-default"),
    ).toBe(false)

    const fact = state.facts.find((f) => f.id === FACT_IDS.rerankerDefault)!
    expect(fact.verification_status).toBe("confirmed")
    expect(fact.review_state).toBeNull()
    expect(fact.sources.some((s) => s.kind === "human")).toBe(true)
    const lastRung = fact.ladder[fact.ladder.length - 1]
    expect(lastRung?.transition?.to).toBe("confirmed")
    // Both sides' origins remain on record after ratification.
    expect(fact.dispute?.sides).toHaveLength(2)
  })

  it("ratify on an article item confirms the article and clears review_state", () => {
    useDemoStore.getState().ratifyReviewItem("review-provider-quirks", "q.tran")
    const article = useDemoStore
      .getState()
      .articles.find((a) => a.id === ARTICLE_IDS.providerQuirks)!
    expect(article.verification_status).toBe("confirmed")
    expect(article.review_state).toBeNull()
    // Coverage stays labelled exactly as measured — ratify never inflates it.
    expect(article.coverage.ratio).toBeCloseTo(0.33, 2)
  })

  it("re-ground queues without resolving; clear removes the item", () => {
    useDemoStore.getState().regroundReviewItem("review-test-db")
    let state = useDemoStore.getState()
    const queued = state.reviewItems.find((r) => r.id === "review-test-db")!
    expect(queued.reground_queued).toBe(true)
    // Still open — re-ground is not a resolution.
    expect(
      state.facts.find((f) => f.id === FACT_IDS.testDb)?.verification_status,
    ).toBe("corroborated")

    state.clearReviewItem("review-test-db")
    state = useDemoStore.getState()
    expect(state.reviewItems.some((r) => r.id === "review-test-db")).toBe(false)
  })

  it("pin decisions are recorded, not client-side hidden", () => {
    useDemoStore.getState().decidePinSuggestion("pin-retry-backoff", "dismissed")
    const suggestion = useDemoStore
      .getState()
      .pinSuggestions.find((p) => p.id === "pin-retry-backoff")!
    expect(suggestion.decision).toBe("dismissed")
  })

  it("hygiene bulk actions remove only the selected ids", () => {
    const before = useDemoStore.getState().hygiene
    expect(before.duplicates).toHaveLength(2)
    useDemoStore.getState().resolveHygiene("duplicates", ["dup-cookie-secure"])
    const after = useDemoStore.getState().hygiene
    expect(after.duplicates.map((p) => p.id)).toEqual(["dup-reranker-top40"])
    expect(after.lowConfidence).toHaveLength(before.lowConfidence.length)
  })

  it("resetKnowledge restores the curated fixtures", () => {
    useDemoStore.getState().clearReviewItem("review-reranker-default")
    useDemoStore.getState().resetKnowledge()
    const state = useDemoStore.getState()
    expect(
      state.reviewItems.some((r) => r.id === "review-reranker-default"),
    ).toBe(true)
  })
})
