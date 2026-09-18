import { describe, expect, it } from "vitest"
import {
  canHold,
  invalidProperties,
  isCalloutVariant,
  mergeProperties,
  propertiesEqual,
} from "../lib/block-properties"

describe("block properties", () => {
  it("merges sent keys over stored ones when the type stays", () => {
    expect(mergeProperties({ ordered: true, marker: "3.", number: 3 }, { ordered: true, marker: "1." }, "list", "list")).toEqual({
      ordered: true,
      marker: "1.",
      number: 3,
    })
  })

  it("keeps only the new type's keys on a type change", () => {
    expect(mergeProperties({ ordered: false, marker: "-" }, { checked: false }, "list", "todo")).toEqual({ checked: false })
    expect(mergeProperties({ checked: true }, null, "todo", "paragraph")).toBeNull()
  })

  it("stores an empty merge as null", () => {
    expect(mergeProperties(null, {}, "paragraph", "paragraph")).toBeNull()
  })

  it("compares with null and {} equal and key order ignored", () => {
    expect(propertiesEqual(null, {})).toBe(true)
    expect(propertiesEqual({ a: 1, b: [1, { c: 2, d: 3 }] }, { b: [1, { d: 3, c: 2 }], a: 1 })).toBe(true)
    expect(propertiesEqual({ a: 1 }, { a: 2 })).toBe(false)
  })

  it("lets only list, todo and toggle hold children, and a table its rows", () => {
    expect(canHold(null, "paragraph")).toBe(true)
    for (const parent of ["list", "todo", "toggle"]) expect(canHold(parent, "code")).toBe(true)
    for (const parent of ["paragraph", "heading", "quote", "callout", "code"]) expect(canHold(parent, "paragraph")).toBe(false)
    expect(canHold("table", "table_row")).toBe(true)
    expect(canHold("table", "paragraph")).toBe(false)
  })

  it("requires checked on a todo and a known variant on a callout", () => {
    expect(invalidProperties("todo", { checked: false })).toBeNull()
    expect(invalidProperties("todo", null)).toMatch(/checked/)
    expect(invalidProperties("callout", { variant: "warning" })).toBeNull()
    expect(invalidProperties("callout", { variant: "tip" })).toMatch(/variant/)
    expect(isCalloutVariant("success")).toBe(true)
    expect(isCalloutVariant("note")).toBe(false)
  })
})
