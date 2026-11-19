import { describe, it, expect, vi } from "vitest"

// sigma reads WebGL enums off the global constructors at module load; the test
// DOM ships neither. Real GL constant values.
const GL = {
  FLOAT: 0x1406,
  UNSIGNED_BYTE: 0x1401,
  TRIANGLES: 0x0004,
  ONE: 1,
  ONE_MINUS_SRC_ALPHA: 0x0303,
  ONE_MINUS_SRC_COLOR: 0x0301,
  BLEND: 0x0be2,
}
Object.assign(globalThis, { WebGLRenderingContext: GL, WebGL2RenderingContext: GL })

type Attr = { name: string; size: number; type: number }
type Proto = {
  renderProgram: (params: unknown, info: unknown) => void
  getDefinition: () => { ATTRIBUTES: Attr[] }
  processVisibleItem: (nodeIndex: number, start: number, data: unknown) => void
  setUniforms: (params: unknown, info: unknown) => void
}

const load = async (additive: boolean, time = 0) => {
  const { createNodeGlowProgram } = await import("../node-glow-program")
  const Program = createNodeGlowProgram({ additive, clock: { time } })
  return Program.prototype as unknown as Proto
}
const fakeGl = () => ({
  ...GL,
  enable: vi.fn(),
  useProgram: vi.fn(),
  blendFunc: vi.fn(),
  uniform1f: vi.fn(),
  uniform2f: vi.fn(),
  uniformMatrix3fv: vi.fn(),
})
const fakeThis = () => ({ setUniforms: vi.fn(), drawWebGL: vi.fn(), METHOD: GL.TRIANGLES })

describe("node glow program", () => {
  it("draws its normal pass additively in the dark theme and restores sigma's blending", async () => {
    const proto = await load(true)
    const gl = fakeGl()
    const self = fakeThis()
    proto.renderProgram.call(self, {}, { gl, program: {}, isPicking: false })
    expect(gl.blendFunc.mock.calls).toEqual([
      [GL.ONE, GL.ONE],
      [GL.ONE, GL.ONE_MINUS_SRC_ALPHA],
    ])
    expect(self.drawWebGL).toHaveBeenCalledTimes(1)
    const [first, second] = gl.blendFunc.mock.invocationCallOrder
    const draw = self.drawWebGL.mock.invocationCallOrder[0]!
    expect(first!).toBeLessThan(draw)
    expect(draw).toBeLessThan(second!)
  })

  it("UI-2: screen-blends the memory canvas's light so an overlap never passes its brighter colour", async () => {
    const { createNodeGlowProgram } = await import("../node-glow-program")
    const proto = createNodeGlowProgram({ additive: true, clock: { time: 0 }, memoryCanvas: true })
      .prototype as unknown as Proto
    const gl = fakeGl()
    proto.renderProgram.call(fakeThis(), {}, { gl, program: {}, isPicking: false })
    expect(gl.blendFunc.mock.calls).toEqual([
      [GL.ONE, GL.ONE_MINUS_SRC_COLOR],
      [GL.ONE, GL.ONE_MINUS_SRC_ALPHA],
    ])
  })

  it("UI-4: only the memory canvas caps its core and clump discs in the light theme", async () => {
    const { createNodeGlowProgram } = await import("../node-glow-program")
    const src = (memoryCanvas: boolean) => {
      const proto = createNodeGlowProgram({ additive: false, clock: { time: 0 }, memoryCanvas })
        .prototype as unknown as Proto
      return (proto.getDefinition.call(proto) as unknown as { VERTEX_SHADER_SOURCE: string }).VERTEX_SHADER_SOURCE
    }
    expect(src(true)).toMatch(/^#define LIGHT_MODE\n#define CRISP_LIGHT\n/)
    expect(src(false)).not.toMatch(/#define CRISP_LIGHT/)
  })

  it("never touches the blend function on the picking pass", async () => {
    const proto = await load(true)
    const gl = fakeGl()
    const self = fakeThis()
    proto.renderProgram.call(self, {}, { gl, program: {}, isPicking: true })
    expect(gl.blendFunc).not.toHaveBeenCalled()
    expect(self.drawWebGL).toHaveBeenCalledTimes(1)
  })

  it("never draws additively in the light theme", async () => {
    const proto = await load(false)
    const gl = fakeGl()
    proto.renderProgram.call(fakeThis(), {}, { gl, program: {}, isPicking: false })
    expect(gl.blendFunc).not.toHaveBeenCalled()
  })

  it("packs brightness and phase per node, defaulting brightness to 1", async () => {
    const proto = await load(true)
    const attrs = proto.getDefinition.call({}).ATTRIBUTES
    const slots = attrs.flatMap((a) =>
      a.type === GL.UNSIGNED_BYTE ? [a.name] : (Array(a.size).fill(a.name) as string[]),
    )
    expect(slots).toEqual(expect.arrayContaining(["a_position", "a_size", "a_color", "a_id", "a_brightness", "a_phase"]))
    const self = { array: new Float32Array(slots.length * 2) }
    proto.processVisibleItem.call(self, 0, 0, { x: 1, y: 2, size: 3, color: "#ff0000", brightness: 0.45, phase: 0.25 })
    proto.processVisibleItem.call(self, 1, slots.length, { x: 0, y: 0, size: 1, color: "#00ff00" })
    expect(self.array[slots.indexOf("a_brightness")]).toBeCloseTo(0.45)
    expect(self.array[slots.indexOf("a_phase")]).toBeCloseTo(0.25)
    expect(self.array[slots.length + slots.indexOf("a_brightness")]).toBe(1)
  })

  it("feeds the shared clock to u_time", async () => {
    const proto = await load(true, 12.5)
    const gl = fakeGl()
    proto.setUniforms.call(
      {},
      { matrix: new Float32Array(9), sizeRatio: 1, correctionRatio: 1, pixelRatio: 1, zoomRatio: 1, width: 10, height: 10, downSizingRatio: 1 },
      { gl, uniformLocations: { u_time: "T", u_matrix: "M", u_sizeRatio: "S", u_correctionRatio: "C" } },
    )
    expect(gl.uniform1f).toHaveBeenCalledWith("T", 12.5)
  })
})


describe("densityStyle", () => {
  const style = async (r: number, s: number, max: number) =>
    (await import("../node-glow-program")).densityStyle(r, s, max)

  it("leaves a sparse role at full light and size", async () => {
    expect(await style(2, 10, 500)).toEqual({ gain: 1, scale: 1 })
  })

  it("dims a dense role so its summed coverage stays at the target", async () => {
    const { COVERAGE_TARGET } = await import("../node-glow-program")
    const { gain, scale } = await style(4, 2, 500)
    expect(scale).toBe(1)
    expect(gain * 4).toBeCloseTo(COVERAGE_TARGET)
  })

  it("never assumes more overlap than the role's group holds", async () => {
    const { COVERAGE_TARGET } = await import("../node-glow-program")
    expect((await style(40, 1, 3)).gain).toBeCloseTo(COVERAGE_TARGET / 3)
  })

  it("shrinks the discs rather than dimming below the floor", async () => {
    const { GAIN_FLOOR } = await import("../node-glow-program")
    const { gain, scale } = await style(12, 0.76, 19000)
    expect(gain).toBeCloseTo(GAIN_FLOOR)
    expect(scale).toBeLessThan(0.2)
  })

  it("keeps a floored role at its floor, shrinking instead", async () => {
    const { densityStyle, SATELLITE_GAIN_FLOOR } = await import("../node-glow-program")
    const { gain, scale } = densityStyle(6, 1, 7, SATELLITE_GAIN_FLOOR)
    expect(gain).toBeCloseTo(SATELLITE_GAIN_FLOOR)
    expect(scale).toBeLessThan(1)
  })

  it("never shrinks a disc below one pixel", async () => {
    const { scale } = await style(10, 0.1, 19000)
    expect(scale * 10).toBeCloseTo(1)
  })
})

describe("core density", () => {
  const points = (n: number, spread: number) => {
    const pos = new Map<string, { x: number; y: number }>()
    for (let i = 0; i < n; i++) {
      const a = i * 2.399963
      const r = spread * Math.sqrt((i + 0.5) / n)
      pos.set(`c${i}`, { x: r * Math.cos(a), y: r * Math.sin(a) })
    }
    return pos
  }
  const graphOf = (pos: Map<string, { x: number; y: number }>) => ({
    getNodeAttribute: (id: string, name: string) =>
      name === "size" ? 6 : pos.get(id)![name as "x" | "y"],
  })

  it("reads an even core at CORE_K and a packed lobe at its own spacing", async () => {
    const { localSpacing } = await import("../node-glow-program")
    const { CORE_K, coreRadius } = await import("../constellation-layout")
    const even = points(400, coreRadius(400))
    expect(localSpacing(graphOf(even), [...even.keys()], 12)).toBe(CORE_K)
    const lobe = points(400, coreRadius(400) / 4)
    const trueSpacing = Math.sqrt((Math.PI * (coreRadius(400) / 4) ** 2) / 400)
    const measured = localSpacing(graphOf(lobe), [...lobe.keys()], 12)
    expect(measured).toBeGreaterThan(0.6 * trueSpacing)
    expect(measured).toBeLessThanOrEqual(trueSpacing)
  })

  it("reads a stack of near-coincident nodes in an even core, even on a cell edge", async () => {
    const { localSpacing } = await import("../node-glow-program")
    const { coreRadius } = await import("../constellation-layout")
    const pos = points(400, coreRadius(400))
    for (let i = 0; i < 8; i++) pos.set(`stack${i}`, { x: 12 + (i % 2 ? 0.2 : -0.2), y: 12 + (i % 2 ? 0.2 : -0.2) })
    expect(localSpacing(graphOf(pos), [...pos.keys()], 12)).toBeLessThanOrEqual(12 / Math.sqrt(8))
  })

  it("draws a packed memory core crisp at its measured spacing, and leaves the code canvas at CORE_K", async () => {
    const { trackDensityGain, densityStyle, localSpacing, CRISP_RATIO, CRISP_MIN_PX } = await import("../node-glow-program")
    const { CORE_K, coreRadius } = await import("../constellation-layout")
    const lobe = points(400, coreRadius(400) / 4)
    const ids = [...lobe.keys()]
    const styleOf = (memoryCanvas: boolean) => {
      let onRender = () => {}
      const sigma = {
        on: (_e: string, f: () => void) => {
          onRender = f
        },
        graphToViewport: (p: { x: number; y: number }) => p,
        scaleSize: (s: number) => s,
      }
      const clock: { time: number; coreGain?: number; coreScale?: number } = { time: 0 }
      trackDensityGain(sigma as never, graphOf(lobe), { core: ids, satellites: [], halo: [] }, clock, undefined, memoryCanvas)
      onRender()
      return { gain: clock.coreGain!, radius: 6 * clock.coreScale! }
    }
    const spacing = localSpacing(graphOf(lobe), ids, 12)
    const crisp = styleOf(true)
    expect(crisp.radius).toBeCloseTo(Math.max(CRISP_MIN_PX, CRISP_RATIO * spacing))
    expect(crisp.radius).toBeLessThan(0.5 * spacing)
    expect(crisp.gain).toBe(1)
    const code = densityStyle(6, CORE_K, 400)
    expect(styleOf(false)).toEqual({ gain: code.gain, radius: 6 * code.scale })
  })

  it("crispStyle lifts its cap once zooming in widens the spacing", async () => {
    const { crispStyle, CRISP_RATIO, CRISP_MIN_PX } = await import("../node-glow-program")
    expect(crispStyle(6, 100, 400)).toEqual({ gain: 1, scale: 1 })
    expect(crispStyle(6, 10, 400).scale * 6).toBeCloseTo(CRISP_RATIO * 10)
    expect(crispStyle(6, 1, 400).scale * 6).toBeGreaterThanOrEqual(CRISP_MIN_PX - 1e-9)
  })
})

describe("halo density", () => {
  it("A8: halo gain times coverage stays at or below the target at the fit view, for small and large halo sizes", async () => {
    const { trackDensityGain, COVERAGE_TARGET } = await import("../node-glow-program")
    const { loadRealCorpus } = await import("../../fixtures/real-corpus")
    const { layoutIslands } = await import("../cluster-layout")
    // The real corpus clusters every memory, so a quarter is unclustered and
    // unlinked here to give the loose island the halo treatment's load.
    const c = loadRealCorpus("all")
    const unlinked = new Set(c.memories.filter((_m, i) => i % 4 === 0).map((m) => m.id))
    const layout = layoutIslands(
      c.memories.map((m) => (unlinked.has(m.id) ? { ...m, cluster: -1 } : m)),
      c.edges.filter((e) => !unlinked.has(e.source) && !unlinked.has(e.target)),
    )
    const loose = layout.groups.find((g) => g.loose)!
    const cls = {
      core: layout.groups.filter((g) => !g.loose).flatMap((g) => g.members),
      satellites: [] as string[][],
      halo: loose.members,
    }
    const outer = { haloInner: 0, haloOuter: loose.radius }
    const isHalo = new Set(loose.members)
    const scale = 800 / layout.extent
    for (const haloSize of [1.5, 20, 40]) {
      let onRender = () => {}
      const sigma = {
        on: (_e: string, f: () => void) => {
          onRender = f
        },
        graphToViewport: (p: { x: number; y: number }) => ({ x: p.x * scale, y: p.y * scale }),
        scaleSize: (s: number) => s,
      }
      const graph = {
        getNodeAttribute: (id: string) => (isHalo.has(id) ? haloSize : 6),
      }
      const clock: { time: number; haloGain?: number; haloScale?: number } = { time: 0 }
      trackDensityGain(sigma as never, graph, cls, clock, outer)
      onRender()
      const spacing =
        Math.sqrt((Math.PI * (outer.haloOuter ** 2 - outer.haloInner ** 2)) / cls.halo.length) * scale
      const radius = haloSize * (clock.haloScale ?? 1)
      const coverage = (radius * radius) / (spacing * spacing)
      expect((clock.haloGain ?? 1) * coverage).toBeLessThanOrEqual(COVERAGE_TARGET + 1e-9)
    }
  })

  it("A8: feeds u_haloGain and u_haloScale from the clock and applies them in the dark-theme shader", async () => {
    const { createNodeGlowProgram } = await import("../node-glow-program")
    const Program = createNodeGlowProgram({ additive: true, clock: { time: 0, haloGain: 0.3, haloScale: 0.6 } })
    const proto = Program.prototype as unknown as Proto
    const def = proto.getDefinition.call(proto) as unknown as { VERTEX_SHADER_SOURCE: string; UNIFORMS: string[] }
    expect(def.UNIFORMS).toEqual(expect.arrayContaining(["u_haloGain", "u_haloScale"]))
    expect(def.VERTEX_SHADER_SOURCE).toMatch(/a_brightness < 0\.5\)[^;]*radius \*= u_haloScale/)
    expect(def.VERTEX_SHADER_SOURCE).toMatch(/brightness \*= u_haloGain/)
    const gl = fakeGl()
    proto.setUniforms.call(
      {},
      { matrix: new Float32Array(9), sizeRatio: 1, correctionRatio: 1, pixelRatio: 1, zoomRatio: 1, width: 10, height: 10, downSizingRatio: 1 },
      { gl, uniformLocations: { u_time: "T", u_haloGain: "HG", u_haloScale: "HS", u_matrix: "M", u_sizeRatio: "S", u_correctionRatio: "C" } },
    )
    expect(gl.uniform1f).toHaveBeenCalledWith("HG", 0.3)
    expect(gl.uniform1f).toHaveBeenCalledWith("HS", 0.6)
  })
})
