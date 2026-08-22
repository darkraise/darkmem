import { describe, it, expect, beforeEach } from "vitest"
import { useProjectStore, DEFAULT_PROJECT } from "../project-store"

describe("projectStore", () => {
  beforeEach(() => {
    localStorage.clear()
    useProjectStore.setState({ activeProject: DEFAULT_PROJECT })
  })

  it("defaults to the backend's own default project", () => {
    expect(useProjectStore.getState().activeProject).toBe("default")
  })

  it("setProject updates the active project", () => {
    useProjectStore.getState().setProject("acme")
    expect(useProjectStore.getState().activeProject).toBe("acme")
  })

  it("setProject trims whitespace", () => {
    useProjectStore.getState().setProject("  acme  ")
    expect(useProjectStore.getState().activeProject).toBe("acme")
  })

  it("setProject ignores an empty or blank value", () => {
    useProjectStore.getState().setProject("acme")
    useProjectStore.getState().setProject("   ")
    expect(useProjectStore.getState().activeProject).toBe("acme")
  })

  it("persists the active project under the darkmem-project key", () => {
    useProjectStore.getState().setProject("acme")
    const stored = JSON.parse(localStorage.getItem("darkmem-project") ?? "{}")
    expect(stored.state.activeProject).toBe("acme")
  })
})
