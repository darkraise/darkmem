import { afterEach, describe, expect, it } from "vitest"
import {
  CURATED_DREAM_ACTIONS,
  CURATED_DREAM_CYCLE,
  CURATED_DREAM_PAST_ACTIONS,
  CURATED_FEED_EVENTS,
  CURATED_PIPELINE_FAILURES,
  CURATED_PIPELINE_RUNS,
  CURATED_SESSION_RUNS,
  DAY_DRILL_DEFAULT,
  CURATED_DAY_BUCKETS,
} from "../data/activity-curated"
import {
  dayBucket,
  deriveRunFailedStep,
  dreamActionsOfType,
  eligibleForUndo,
  failedStepSeverity,
  filterFeed,
  groupFailuresByStep,
  isPoison,
  isValidDay,
  shiftDay,
  validateJobConfig,
} from "../activity"
import { useDemoStore } from "../store"

afterEach(() => {
  useDemoStore.getState().resetActivity()
})

describe("pipeline honesty — a partial/failed run always NAMES its step", () => {
  it("derives the named failed step for every non-clean terminal", () => {
    for (const run of CURATED_PIPELINE_RUNS) {
      const step = deriveRunFailedStep(run)
      if (run.terminal === "partial" || run.terminal === "failed") {
        expect(step, `${run.id} must name its failed step`).not.toBeNull()
      } else {
        expect(step, `${run.id} is clean — no failed step`).toBeNull()
      }
    }
  })

  it("hard errors win in phase order — first one wins", () => {
    const failed = CURATED_PIPELINE_RUNS.find((r) => r.id === "mem_e41a88")!
    // Both phase 1 and phase 2 errored; phase order names content_embedding.
    expect(deriveRunFailedStep(failed)).toBe("content_embedding")
  })

  it("a graph-savepoint failure names graph_write while vector survives", () => {
    const partial = CURATED_PIPELINE_RUNS.find((r) => r.id === "mem_5b13d0")!
    expect(deriveRunFailedStep(partial)).toBe("graph_write")
    expect(partial.substeps?.vector).toBe("ok")
  })

  it("degraded extraction names extraction_partial with warn severity", () => {
    const degraded = CURATED_PIPELINE_RUNS.find((r) => r.id === "mem_9e02f7")!
    expect(deriveRunFailedStep(degraded)).toBe("extraction_partial")
    expect(failedStepSeverity("extraction_partial")).toBe("warn")
    expect(failedStepSeverity("graph_write")).toBe("error")
  })
})

describe("feed filters", () => {
  it("passes everything through on 'all'", () => {
    expect(filterFeed(CURATED_FEED_EVENTS, "all")).toHaveLength(
      CURATED_FEED_EVENTS.length,
    )
  })

  it("filters to a single category", () => {
    const verification = filterFeed(CURATED_FEED_EVENTS, "verification")
    expect(verification.length).toBeGreaterThan(0)
    expect(verification.every((e) => e.category === "verification")).toBe(true)
  })

  it("the dispute row is the only toast-flagged event", () => {
    const toasts = CURATED_FEED_EVENTS.filter((e) => e.toast)
    expect(toasts).toHaveLength(1)
    expect(toasts[0]?.badge).toBe("disputed")
  })
})

describe("triage", () => {
  it("groups by failed step preserving first-seen order", () => {
    const groups = groupFailuresByStep(CURATED_PIPELINE_FAILURES)
    expect(groups.map((g) => g.step)).toEqual([
      "extraction",
      "content_embedding",
      "community_detection",
    ])
    expect(groups[0]?.failures).toHaveLength(2)
  })

  it("poison is the ≥5-attempts heuristic", () => {
    const poison = CURATED_PIPELINE_FAILURES.filter(isPoison)
    expect(poison.map((f) => f.id)).toEqual(["fail-zai-models"])
  })

  it("retry queues without resolving; forget removes; retry-all queues all", () => {
    useDemoStore.getState().retryFailure("fail-reranker-swap")
    let state = useDemoStore.getState()
    const queued = state.pipelineFailures.find(
      (f) => f.id === "fail-reranker-swap",
    )!
    expect(queued.retry_queued).toBe(true)
    // Still open — a queued retry is not a resolution.
    expect(state.pipelineFailures).toHaveLength(4)

    state.forgetFailure("fail-reranker-swap")
    state = useDemoStore.getState()
    expect(
      state.pipelineFailures.some((f) => f.id === "fail-reranker-swap"),
    ).toBe(false)

    state.retryAllFailures()
    state = useDemoStore.getState()
    expect(state.pipelineFailures.every((f) => f.retry_queued)).toBe(true)
  })
})

describe("jobs", () => {
  it("ships every registered job — the list can never be empty", () => {
    const jobs = useDemoStore.getState().jobs
    expect(jobs.map((j) => j.key)).toEqual([
      "repo_sync",
      "code_enrichment",
      "token_blocklist_cleanup",
      "pipeline_failure_cleanup",
      "graph_orphan_cleanup",
      "tag_orphan_cleanup",
      "expired_memory_cleanup",
      "buffer_flush",
      "job_run_cleanup",
      "llm_usage_cleanup",
      "backup_ship",
      "code_deriver",
      "ppr_snapshot",
      "relation_embedding_refresh",
      "block_embedding_refresh",
      "repo_entity_anchoring",
      "repo_entity_merge",
      "citation_reverify",
      "fact_lift",
      "verification_recompute",
      "contradiction_scan",
      "memory_dream",
      "topic_detection",
      "article_synthesis",
    ])
  })

  it("a trigger on a held lock returns 409 busy — never queued", () => {
    const result = useDemoStore.getState().triggerJob("code_enrichment")
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.status).toBe(409)
      expect(result.lock_held_since).toBe("14:12:00 UTC")
    }
    // The running job's state is untouched — the request was discarded.
    const job = useDemoStore
      .getState()
      .jobs.find((j) => j.key === "code_enrichment")!
    expect(job.running).toBe(true)
    expect(job.last_run_label).toBe("14:07:00 UTC")
  })

  it("a trigger on an idle job completes and records the run", () => {
    const result = useDemoStore.getState().triggerJob("repo_sync")
    expect(result.ok).toBe(true)
    const job = useDemoStore.getState().jobs.find((j) => j.key === "repo_sync")!
    expect(job.last_run_label).toBe("just now (manual)")
    expect(job.last_status).toBe("ok")
  })

  it("validateJobConfig enforces type, bounds, and rejects unknown keys", () => {
    const schema = useDemoStore
      .getState()
      .jobs.find((j) => j.key === "code_enrichment")!.config_schema

    expect(validateJobConfig(schema, { batch_size: 10 })).toEqual({
      ok: true,
      config: { batch_size: 10 },
    })
    const tooBig = validateJobConfig(schema, { batch_size: 101 })
    expect(tooBig.ok).toBe(false)
    const notInt = validateJobConfig(schema, { batch_size: "5.5" })
    expect(notInt.ok).toBe(false)
    const unknown = validateJobConfig(schema, { batch_size: 5, nope: 1 })
    expect(unknown.ok).toBe(false)
    if (!unknown.ok) expect(unknown.errors.nope).toContain("unknown key")
  })

  it("saveJobConfig writes the validated value into the schema field", () => {
    useDemoStore.getState().saveJobConfig("code_enrichment", { batch_size: 20 })
    const job = useDemoStore
      .getState()
      .jobs.find((j) => j.key === "code_enrichment")!
    expect(job.config_schema[0]?.value).toBe(20)
  })
})

describe("dream digest undo", () => {
  it("every cycle group has a fixture entry set and the seven types are covered", () => {
    for (const group of CURATED_DREAM_CYCLE.groups) {
      expect(
        dreamActionsOfType(CURATED_DREAM_ACTIONS, group.type).length,
        `group ${group.type} must have entries`,
      ).toBeGreaterThan(0)
    }
    expect(CURATED_DREAM_CYCLE.groups).toHaveLength(7)
  })

  it("a blocked action always carries its printed reason", () => {
    const blocked = [
      ...CURATED_DREAM_ACTIONS,
      ...CURATED_DREAM_PAST_ACTIONS,
    ].filter((a) => a.undo_blocked)
    expect(blocked.length).toBeGreaterThan(0)
    for (const action of blocked) {
      expect(action.undo_blocked?.reason).toBeTruthy()
    }
    // Every past-cycle action is past its window — all blocked.
    expect(CURATED_DREAM_PAST_ACTIONS.every((a) => a.undo_blocked)).toBe(true)
  })

  it("undoDreamAction flips only an eligible action", () => {
    useDemoStore.getState().undoDreamAction("dream-sup-setup-secret")
    let state = useDemoStore.getState()
    expect(
      state.dreamActions.find((a) => a.id === "dream-sup-setup-secret")?.undone,
    ).toBe(true)

    // A blocked action refuses the undo.
    state.undoDreamAction("dream-sup-mcp-bearer")
    state = useDemoStore.getState()
    expect(
      state.dreamActions.find((a) => a.id === "dream-sup-mcp-bearer")?.undone,
    ).toBe(false)
  })

  it("undoDreamBatch undoes only the eligible entries of the group", () => {
    useDemoStore.getState().undoDreamBatch("supersede")
    const state = useDemoStore.getState()
    const group = dreamActionsOfType(state.dreamActions, "supersede")
    expect(
      group.find((a) => a.id === "dream-sup-setup-secret")?.undone,
    ).toBe(true)
    // The blocked entry survives the batch untouched.
    expect(group.find((a) => a.id === "dream-sup-mcp-bearer")?.undone).toBe(
      false,
    )
    expect(eligibleForUndo(group)).toHaveLength(0)
  })

  it("ratification is never batchable", () => {
    const ratify = CURATED_DREAM_CYCLE.groups.find((g) => g.type === "ratify")!
    expect(ratify.batchable).toBe(false)
  })
})

describe("day drill", () => {
  it("resolves the curated UTC bucket and misses an empty day", () => {
    expect(dayBucket(CURATED_DAY_BUCKETS, DAY_DRILL_DEFAULT)?.events.length).toBe(
      7,
    )
    expect(dayBucket(CURATED_DAY_BUCKETS, "2026-05-03")).toBeUndefined()
  })

  it("shiftDay does UTC calendar arithmetic across month boundaries", () => {
    expect(shiftDay("2026-07-20", -1)).toBe("2026-07-19")
    expect(shiftDay("2026-07-31", 1)).toBe("2026-08-01")
  })

  it("isValidDay accepts YYYY-MM-DD only", () => {
    expect(isValidDay("2026-07-20")).toBe(true)
    expect(isValidDay("20-07-2026")).toBe(false)
    expect(isValidDay(42)).toBe(false)
  })

  it("the rung pair appears only on the verification transition", () => {
    const bucket = dayBucket(CURATED_DAY_BUCKETS, DAY_DRILL_DEFAULT)!
    const withPair = bucket.events.filter((e) => e.transition)
    expect(withPair).toHaveLength(1)
    expect(withPair[0]?.type).toBe("verified")
    expect(withPair[0]?.transition?.to_label).toBe("human-ratified")
  })
})

describe("session checkpoints are operational, not knowledge", () => {
  it("fixtures carry no verification vocabulary", () => {
    const serialized = JSON.stringify(CURATED_SESSION_RUNS)
    expect(serialized).not.toContain("verification_status")
    expect(serialized).not.toContain("corroborated")
  })

  it("the resume block is marker-bounded for strip-before-rewrite", () => {
    // The markers the *writer* recognises (`inject_block.MARKER_BEGIN` /
    // `MARKER_END`), not a vocabulary of the mockup's own. This assertion
    // pinned `darkmem:resume:begin` until 2026-08-11 — a pair no shipped code
    // has ever written, and one that would have made the real writer append a
    // second live pair beneath a human's pasted copy.
    const run = CURATED_SESSION_RUNS[0]!
    expect(run.latest?.resume_block).toContain("<!-- darkmem:begin -->")
    expect(run.latest?.resume_block).toContain("<!-- darkmem:end -->")
  })

  it("one run honestly has no checkpoint yet", () => {
    const empty = CURATED_SESSION_RUNS.find((r) => r.latest === null)
    expect(empty).toBeDefined()
    expect(empty?.history).toHaveLength(0)
  })
})

describe("resetActivity", () => {
  it("restores the curated fixtures after mutations", () => {
    const store = useDemoStore.getState()
    store.forgetFailure("fail-reranker-swap")
    store.undoDreamBatch("refine")
    store.triggerJob("repo_sync")
    store.resetActivity()

    const state = useDemoStore.getState()
    expect(state.pipelineFailures).toHaveLength(4)
    expect(state.dreamActions.every((a) => !a.undone)).toBe(true)
    expect(state.jobs.find((j) => j.key === "repo_sync")?.last_run_label).toBe(
      "14:10 UTC",
    )
  })
})
