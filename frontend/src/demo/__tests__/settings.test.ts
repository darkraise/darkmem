import { afterEach, describe, expect, it } from "vitest"
import {
  activeArmCount,
  allArms,
  armStatus,
  cronInfo,
  embeddingKindWarning,
  resolveLadderParam,
  maskKey,
  validateParamsJson,
} from "../settings"
import { useDemoStore } from "../store"

afterEach(() => {
  useDemoStore.getState().resetSettings()
})

describe("armStatus — invariant 23", () => {
  it("renders 0 as inactive (built-but-unspent), non-zero as active", () => {
    expect(armStatus(0)).toBe("inactive")
    expect(armStatus(0.05)).toBe("active")
    expect(armStatus(1)).toBe("active")
  })
})

describe("allArms", () => {
  it("returns exactly the seven w_* arms", () => {
    const flags = useDemoStore.getState().flags
    expect(allArms(flags).map((a) => a.key)).toEqual([
      "w_conf",
      "w_importance",
      "w_heat",
      "w_recency",
      "w_ppr",
      "w_dual",
      "w_context_boost",
    ])
  })

  it("counts the measured activations on this instance", () => {
    expect(activeArmCount(useDemoStore.getState().flags)).toBe(3)
  })
})

describe("cronInfo", () => {
  it("accepts five-field (minute precision)", () => {
    const info = cronInfo("*/5 * * * *")
    expect(info).toMatchObject({ ok: true, fields: 5 })
  })

  it("accepts six-field (seconds-first, Quartz-style)", () => {
    const info = cronInfo("*/10 * * * * *")
    expect(info).toMatchObject({ ok: true, fields: 6 })
  })

  it("rejects any other arity", () => {
    expect(cronInfo("* * *")).toMatchObject({ ok: false })
    expect(cronInfo("")).toMatchObject({ ok: false })
  })
})

describe("validateParamsJson", () => {
  it("accepts an object and the empty string", () => {
    expect(validateParamsJson('{"temperature": 0}').ok).toBe(true)
    expect(validateParamsJson("").ok).toBe(true)
  })

  it("rejects arrays, scalars, and malformed JSON", () => {
    expect(validateParamsJson("[1]").ok).toBe(false)
    expect(validateParamsJson("42").ok).toBe(false)
    expect(validateParamsJson("{oops").ok).toBe(false)
  })
})

describe("embeddingKindWarning — derived from api_kind, not a stored flag", () => {
  it("warns for anthropic and deepseek only", () => {
    expect(embeddingKindWarning("anthropic")).toMatch(/no embeddings/)
    expect(embeddingKindWarning("deepseek")).toMatch(/no embeddings/)
    expect(embeddingKindWarning("openai")).toBeNull()
    expect(embeddingKindWarning("ollama")).toBeNull()
  })
})

describe("maskKey", () => {
  it("keeps only the last four characters visible", () => {
    expect(maskKey("sk-abcdef4f2a")).toBe("••••••••••••4f2a")
    expect(maskKey("")).toBe("")
  })
})

describe("store — flags", () => {
  it("saveArm writes the value and flips source to override", () => {
    useDemoStore.getState().saveArm("w_heat", 0.2)
    const arm = useDemoStore
      .getState()
      .flags.fusion_arms.find((a) => a.key === "w_heat")
    expect(arm).toMatchObject({ value: 0.2, source: "override" })
  })

  it("saveArm reaches a paired graph-flag arm and recounts overrides", () => {
    const before = useDemoStore.getState().flags.overrides_written
    useDemoStore.getState().saveArm("w_ppr", 0.1)
    const flags = useDemoStore.getState().flags
    const ppr = flags.graph_flags.find((f) => f.key === "ppr_enabled")
    expect(ppr?.paired_arm).toMatchObject({ value: 0.1, source: "override" })
    expect(flags.overrides_written).toBe(before + 1)
  })

  it("setGraphFlag marks the flag an override", () => {
    useDemoStore.getState().setGraphFlag("community_injection_enabled", true)
    const flag = useDemoStore
      .getState()
      .flags.graph_flags.find((f) => f.key === "community_injection_enabled")
    expect(flag).toMatchObject({ enabled: true, source: "override" })
  })
})

describe("resolveLadderParam — the floors, mirrored for display", () => {
  const floor3 = {
    name: "n_default",
    committed: null,
    effective: 3,
    floor: 3,
    measured: false,
    state: "default" as const,
  }

  it("honours a tightening — more evidence never needs permission", () => {
    expect(resolveLadderParam(floor3, 5, [])).toMatchObject({
      committed: 5,
      effective: 5,
      state: "honoured",
    })
  })

  it("clamps an unbacked loosening back to the floor and says why", () => {
    const out = resolveLadderParam(floor3, 1, [])
    expect(out).toMatchObject({ committed: 1, effective: 3, state: "clamped" })
    // The note must name the gate, so the row says what would license the
    // value rather than only that it was refused.
    expect(out.note).toMatch(/T2\.40/)
  })

  it("honours a loosening a recorded measurement names by name", () => {
    expect(resolveLadderParam(floor3, 1, ["n_default"])).toMatchObject({
      effective: 1,
      state: "honoured",
    })
  })

  it("never lets an origin count reach zero, measurement or not", () => {
    // N = 0 makes `k >= n` true for a fact with no sources at all, which is
    // not a loosening any measurement can authorise.
    const out = resolveLadderParam(floor3, 0, ["n_default"])
    expect(out).toMatchObject({ effective: 1, state: "clamped" })
  })

  it("clearing a commitment returns the parameter to its floor", () => {
    const committed = resolveLadderParam(floor3, 9, [])
    expect(resolveLadderParam(committed, null, [])).toMatchObject({
      committed: null,
      effective: 3,
      state: "default",
    })
  })
})

describe("store — the ladder gate and the tunables", () => {
  it("saveCorroboration commits one threshold and counts it as an override", () => {
    const before = useDemoStore.getState().flags.overrides_written
    useDemoStore.getState().saveCorroboration("n_default", 5)
    const flags = useDemoStore.getState().flags
    expect(
      flags.corroboration.params.find((p) => p.name === "n_default"),
    ).toMatchObject({ committed: 5, effective: 5, state: "honoured" })
    expect(flags.corroboration.rowPresent).toBe(true)
    expect(flags.overrides_written).toBe(before + 1)
  })

  it("clearing the last commitment drops the row", () => {
    useDemoStore.getState().saveCorroboration("n_default", 5)
    useDemoStore.getState().saveCorroboration("n_default", null)
    expect(useDemoStore.getState().flags.corroboration.rowPresent).toBe(false)
  })

  it("saveTunable flips source to override, and back on a return to default", () => {
    useDemoStore.getState().saveTunable("pipeline_concurrency", 8)
    const find = () =>
      useDemoStore
        .getState()
        .flags.tunables.find((t) => t.key === "pipeline_concurrency")
    expect(find()).toMatchObject({ value: 8, source: "override" })
    useDemoStore.getState().saveTunable("pipeline_concurrency", 5)
    expect(find()).toMatchObject({ value: 5, source: "default" })
  })

  it("setClassificationAreas keeps general on — the API forces it back anyway", () => {
    useDemoStore.getState().setClassificationAreas(["technical"])
    expect(useDemoStore.getState().flags.classification_areas).toEqual([
      "general",
      "technical",
    ])
  })
})

describe("store — LLM", () => {
  it("saveLLMPurpose merges the patch and records the save trace", () => {
    useDemoStore.getState().saveLLMPurpose("reasoning", {
      base_url: "api.openai.com/v2",
    })
    const state = useDemoStore.getState().llm
    const purpose = state.purposes.find((p) => p.purpose === "reasoning")
    expect(purpose?.base_url).toBe("api.openai.com/v2")
    expect(state.last_save).toEqual({
      purpose: "reasoning",
      fields: ["base_url"],
    })
  })

  it("setClassifierKind flips the two-value field", () => {
    useDemoStore.getState().setClassifierKind("local")
    expect(useDemoStore.getState().llm.classifier_kind).toBe("local")
  })
})

describe("store — jobs settings", () => {
  it("setJobEnabled + saveJobCron mutate the job row", () => {
    useDemoStore.getState().setJobEnabled("repo_sync", false)
    useDemoStore.getState().saveJobCron("repo_sync", "*/7 * * * *")
    const job = useDemoStore
      .getState()
      .jobs.find((j) => j.key === "repo_sync")
    expect(job).toMatchObject({ enabled: false, cron: "*/7 * * * *" })
    useDemoStore.getState().setJobEnabled("repo_sync", true)
  })
})

describe("store — maintenance", () => {
  it("expired sweep zeroes the counts and names the demotion", () => {
    useDemoStore.getState().runMaintenanceOp("expired_memory_cleanup")
    const m = useDemoStore.getState().maintenance
    expect(m.cleanup.expired).toBe(0)
    expect(m.last_op_note).toMatch(/marked deprecated/)
  })

  it("prune_caches drops the retired fingerprints", () => {
    useDemoStore.getState().runMaintenanceOp("prune_caches")
    const m = useDemoStore.getState().maintenance
    expect(m.dbops.retired_fingerprints).toEqual([])
    expect(m.last_op_note).toMatch(/3 unused caches dropped/)
  })
})
