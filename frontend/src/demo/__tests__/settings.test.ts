import { afterEach, describe, expect, it } from "vitest"
import {
  activeArmCount,
  allArms,
  armStatus,
  cronInfo,
  embeddingKindWarning,
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
    expect(m.last_op_note).toMatch(/demoted to deprecated/)
  })

  it("prune_caches drops the retired fingerprints", () => {
    useDemoStore.getState().runMaintenanceOp("prune_caches")
    const m = useDemoStore.getState().maintenance
    expect(m.dbops.retired_fingerprints).toEqual([])
    expect(m.last_op_note).toMatch(/3 retired cache tables dropped/)
  })
})

describe("store — distribution curb", () => {
  it("curbing flips the client and appends an inject_curbed log row", () => {
    const before = useDemoStore.getState().distribution.log.length
    useDemoStore.getState().setDistributionCurb("cursor", true)
    const d = useDemoStore.getState().distribution
    expect(d.clients.find((c) => c.id === "cursor")?.status).toBe("curbed")
    expect(d.log.length).toBe(before + 1)
    expect(d.log[0]).toMatchObject({
      target: "cursor",
      event_type: "inject_curbed",
    })
  })

  it("un-curbing resumes without fabricating an inject log row", () => {
    useDemoStore.getState().setDistributionCurb("codex-cli", false)
    const d = useDemoStore.getState().distribution
    expect(d.clients.find((c) => c.id === "codex-cli")?.status).toBe(
      "connected",
    )
    expect(d.log.filter((r) => r.target === "codex-cli").length).toBe(2)
  })
})
