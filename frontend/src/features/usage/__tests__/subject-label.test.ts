import { describe, expect, it } from "vitest"

import { subjectLabel } from "../subject-label"

describe("subjectLabel", () => {
  it("names the job rather than showing the run's composite id", () => {
    // `{key}@{started_at}`: the run has no job_runs id to be named by, because
    // that row is written only after the runner returns.
    const l = subjectLabel("job_run", "memory_dream@2026-08-23T04:00:00+00:00")
    expect(l.title).toBe("memory_dream")
    expect(l.detail).not.toContain("2026-08-23T04:00:00")
    expect(l.raw).toContain("@")
  })

  it("splits a maintenance subject into its kind and its target", () => {
    const l = subjectLabel("maintenance", "reembed_memories:9f3c1a2b-1111-2222-3333-444455556666")
    expect(l.title).toBe("reembed memories")
    // The random tail, not the UUIDv7 timestamp head (see lib/short-id).
    expect(l.detail).toBe("…55556666")
  })

  it("names the conversation a chat turn belongs to", () => {
    const l = subjectLabel("chat", "aaaaaaaa-1111-2222-3333-444455556666:bbbbbbbb-1111")
    expect(l.title).toBe("Chat turn")
    expect(l.detail).toMatch(/conversation …55556666/)
  })

  it("falls back to the raw id when the shape does not match its type", () => {
    // A label that says the wrong thing is worse than an id the reader has to
    // work at, so a malformed subject keeps its id rather than being parsed
    // into a confident guess.
    const l = subjectLabel("job_run", "no-at-sign-here")
    expect(l.detail).toContain("no-at-si")
    expect(l.raw).toBe("no-at-sign-here")
  })

  it("says an unattributed cost has no owner rather than leaving a blank", () => {
    const l = subjectLabel("unattributed", null)
    expect(l.title).toBe("Unattributed")
    expect(l.detail).toBe("no owner recorded")
    expect(l.raw).toBeNull()
  })
})
