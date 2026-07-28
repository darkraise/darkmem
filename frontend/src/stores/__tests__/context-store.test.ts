import { describe, it, expect, beforeEach } from "vitest"
import { useContextStore } from "../context-store"
import { useProjectStore, DEFAULT_PROJECT } from "../project-store"

describe("contextStore", () => {
  beforeEach(() => {
    useContextStore.setState({ declared: null })
    useProjectStore.setState({
      activeProject: DEFAULT_PROJECT,
      knownProjects: [DEFAULT_PROJECT],
    })
  })

  it("starts undeclared — null, not a placeholder object", () => {
    expect(useContextStore.getState().declared).toBeNull()
  })

  it("declareContext with one axis produces a declared context", () => {
    useContextStore.getState().declareContext({ env: "prod" })
    expect(useContextStore.getState().declared).toEqual({ axes: { env: "prod" } })
  })

  it("declareContext normalises case and whitespace", () => {
    useContextStore.getState().declareContext({ env: "  PROD  " })
    expect(useContextStore.getState().declared).toEqual({ axes: { env: "prod" } })
  })

  it("declareContext accepts multiple axes at once", () => {
    useContextStore.getState().declareContext({ env: "prod", version: "15" })
    expect(useContextStore.getState().declared).toEqual({
      axes: { env: "prod", version: "15" },
    })
  })

  // Ruling 4 / the backend's own _AxisSet.__post_init__ rule: a context
  // with every axis empty is not a "declared but vacuous" object, it IS
  // undeclared — null is the only representation, never a live-but-empty
  // one that could be mistaken for a real declaration downstream.
  it("declareContext with every axis blank collapses back to undeclared, not a vacuous object", () => {
    useContextStore.getState().declareContext({ env: "prod" })
    useContextStore.getState().declareContext({ env: "", situation: null, version: undefined })
    expect(useContextStore.getState().declared).toBeNull()
  })

  it("declareContext drops an axis whose value is only whitespace", () => {
    useContextStore.getState().declareContext({ env: "prod", situation: "   " })
    expect(useContextStore.getState().declared).toEqual({ axes: { env: "prod" } })
  })

  it("clearContext returns to undeclared", () => {
    useContextStore.getState().declareContext({ env: "prod" })
    useContextStore.getState().clearContext()
    expect(useContextStore.getState().declared).toBeNull()
  })

  it("is a distinct store from projectStore — declaring context never touches the active project", () => {
    useProjectStore.getState().setProject("acme")
    useContextStore.getState().declareContext({ env: "prod" })
    expect(useProjectStore.getState().activeProject).toBe("acme")
  })

  it("is a distinct store from projectStore — switching project never declares a context", () => {
    useProjectStore.getState().setProject("production")
    expect(useContextStore.getState().declared).toBeNull()
  })
})
