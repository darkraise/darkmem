import { describe, it, expect, beforeEach } from "vitest"
import {
  useProjectStore,
  ALL_PROJECTS,
  DEFAULT_PROJECT,
} from "../project-store"

describe("projectStore", () => {
  beforeEach(() => {
    localStorage.clear()
    useProjectStore.setState({
      activeProject: DEFAULT_PROJECT,
      missingProject: null,
    })
  })

  it("opens on every project", () => {
    expect(useProjectStore.getInitialState().activeProject).toBe(ALL_PROJECTS)
    expect(useProjectStore.getInitialState().missingProject).toBeNull()
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

  it("reconcile keeps a scope the corpus still holds", () => {
    useProjectStore.getState().setProject("acme")
    useProjectStore.getState().reconcile(["acme", "darkmem"])
    expect(useProjectStore.getState().activeProject).toBe("acme")
    expect(useProjectStore.getState().missingProject).toBeNull()
  })

  it("reconcile widens a scope the corpus no longer holds, naming it", () => {
    useProjectStore.getState().setProject("gone")
    useProjectStore.getState().reconcile(["acme"])
    expect(useProjectStore.getState().activeProject).toBe(ALL_PROJECTS)
    expect(useProjectStore.getState().missingProject).toBe("gone")
  })

  it("reconcile leaves the all-projects scope alone", () => {
    useProjectStore.getState().setProject(ALL_PROJECTS)
    useProjectStore.getState().reconcile([])
    expect(useProjectStore.getState().activeProject).toBe(ALL_PROJECTS)
    expect(useProjectStore.getState().missingProject).toBeNull()
  })

  it("picking a scope clears the missing-project notice", () => {
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: "gone" })
    useProjectStore.getState().setProject("acme")
    expect(useProjectStore.getState().missingProject).toBeNull()
  })

  it("persists the scope but not the notice", () => {
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: "gone" })
    useProjectStore.getState().setProject("acme")
    const stored = JSON.parse(localStorage.getItem("darkmem-project") ?? "{}")
    expect(stored.state).toEqual({ activeProject: "acme" })
  })
})
