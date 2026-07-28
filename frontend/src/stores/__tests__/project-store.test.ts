import { describe, it, expect, beforeEach } from "vitest"
import { useProjectStore, DEFAULT_PROJECT } from "../project-store"

describe("projectStore", () => {
  beforeEach(() => {
    localStorage.clear()
    useProjectStore.setState({
      activeProject: DEFAULT_PROJECT,
      knownProjects: [DEFAULT_PROJECT],
    })
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

  it("tracks known projects, most-recent first, deduplicated", () => {
    useProjectStore.getState().setProject("acme")
    useProjectStore.getState().setProject("beta")
    useProjectStore.getState().setProject("acme")
    expect(useProjectStore.getState().knownProjects).toEqual([
      "acme",
      "beta",
      DEFAULT_PROJECT,
    ])
  })

  it("caps known projects at a bounded size", () => {
    for (let i = 0; i < 20; i++) {
      useProjectStore.getState().setProject(`project-${i}`)
    }
    expect(useProjectStore.getState().knownProjects.length).toBeLessThanOrEqual(8)
    expect(useProjectStore.getState().knownProjects[0]).toBe("project-19")
  })

  it("persists the active project under the darkmem-project key", () => {
    useProjectStore.getState().setProject("acme")
    const stored = JSON.parse(localStorage.getItem("darkmem-project") ?? "{}")
    expect(stored.state.activeProject).toBe("acme")
  })
})
