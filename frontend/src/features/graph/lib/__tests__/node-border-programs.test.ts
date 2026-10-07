import { describe, it, expect } from "vitest"

// sigma reads WebGL enums off the global constructors at module load, and
// The test DOM ships neither. Stub them before the dynamic imports below; the values
// are the real GL constants so a program definition still round-trips.
const GL = { FLOAT: 0x1406, UNSIGNED_BYTE: 0x1401, TRIANGLES: 0x0004 }
Object.assign(globalThis, {
  WebGLRenderingContext: GL,
  WebGL2RenderingContext: GL,
})

type Attr = { name: string; size: number; type: number; normalized?: boolean }
type Def = { ATTRIBUTES: Attr[]; VERTEX_SHADER_SOURCE: string; FRAGMENT_SHADER_SOURCE: string }
type Program = {
  prototype: {
    getDefinition: () => Def
    processVisibleItem: (nodeIndex: number, startIndex: number, data: unknown) => void
  }
}

// Loaded lazily inside each test: a static import would hoist above the stub
// above and sigma would read the enums off a global that is not there yet.
const packColor = async (hex: string) => (await import("sigma/utils")).floatColor(hex)

// One float per attribute in ATTRIBUTES order: a 4x UNSIGNED_BYTE colour is
// packed into a single float, so `size` does not predict the slot count.
function slotsOf(def: Def): string[] {
  return def.ATTRIBUTES.flatMap((a) =>
    a.type === GL.UNSIGNED_BYTE ? [a.name] : Array(a.size).fill(a.name),
  )
}

const cases = [
  {
    label: "diamond",
    load: async () =>
      (await import("../node-diamond-program"))
        .NodeDiamondProgram as unknown as Program,
  },
  {
    label: "bordered circle",
    load: async () =>
      (await import("../node-circle-bordered-program"))
        .NodeCircleBorderedProgram as unknown as Program,
  },
]

describe.each(cases)("$label program", ({ load }) => {
  it("declares a_borderColor next to a_color", async () => {
    const program = await load()
    const names = program.prototype.getDefinition.call({}).ATTRIBUTES.map((a) => a.name)
    expect(names.indexOf("a_borderColor")).toBe(names.indexOf("a_color") + 1)
  })

  it("declares the border attribute in both shaders", async () => {
    const program = await load()
    const def = program.prototype.getDefinition.call({})
    expect(def.VERTEX_SHADER_SOURCE).toContain("attribute vec4 a_borderColor")
    expect(def.VERTEX_SHADER_SOURCE).toContain("varying vec4 v_borderColor")
    expect(def.FRAGMENT_SHADER_SOURCE).toContain("varying vec4 v_borderColor")
  })

  // The single highest-risk property in either program: processVisibleItem
  // writes an interleaved buffer positionally, so a slot that disagrees with
  // ATTRIBUTES makes every node read its neighbour's bytes.
  it("writes each slot the definition declares, in that order", async () => {
    const program = await load()
    const def = program.prototype.getDefinition.call({})
    const slots = slotsOf(def)
    const array = new Float32Array(slots.length + 4).fill(NaN)
    const data = { x: 3, y: 5, size: 7, color: "#112233", borderColor: "#445566" }

    program.prototype.processVisibleItem.call({ array }, 42, 0, data)

    const at = (name: string) => array[slots.indexOf(name)]
    expect(at("a_position")).toBe(3)
    expect(array[slots.indexOf("a_position") + 1]).toBe(5)
    expect(at("a_size")).toBe(7)
    expect(at("a_color")).toBe(await packColor("#112233"))
    expect(at("a_borderColor")).toBe(await packColor("#445566"))
    expect(at("a_id")).toBe(42)
    // Exactly the declared width, so the next node starts where sigma expects.
    expect([...array.slice(slots.length)].every(Number.isNaN)).toBe(true)
  })

  it("falls back to the fill when a node carries no border colour", async () => {
    const program = await load()
    const def = program.prototype.getDefinition.call({})
    const slots = slotsOf(def)
    const array = new Float32Array(slots.length)

    program.prototype.processVisibleItem.call({ array }, 1, 0, {
      x: 0,
      y: 0,
      size: 1,
      color: "#abcdef",
    })

    expect(array[slots.indexOf("a_borderColor")]).toBe(await packColor("#abcdef"))
  })

  it("writes at the offset it is given, not always at zero", async () => {
    const program = await load()
    const def = program.prototype.getDefinition.call({})
    const slots = slotsOf(def)
    const array = new Float32Array(slots.length * 2).fill(NaN)

    program.prototype.processVisibleItem.call({ array }, 9, slots.length, {
      x: 1,
      y: 2,
      size: 3,
      color: "#000000",
      borderColor: "#ffffff",
    })

    expect([...array.slice(0, slots.length)].every(Number.isNaN)).toBe(true)
    expect(array[slots.length + slots.indexOf("a_borderColor")]).toBe(
      await packColor("#ffffff"),
    )
  })
})
