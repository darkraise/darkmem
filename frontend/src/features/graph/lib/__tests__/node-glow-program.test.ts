import { describe, it, expect, vi } from "vitest"

// sigma reads WebGL enums off the global constructors at module load; the test
// DOM ships neither. Real GL constant values.
const GL = {
  FLOAT: 0x1406,
  UNSIGNED_BYTE: 0x1401,
  TRIANGLES: 0x0004,
  ONE: 1,
  ONE_MINUS_SRC_ALPHA: 0x0303,
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

  it("never shrinks a disc below one pixel", async () => {
    const { scale } = await style(10, 0.1, 19000)
    expect(scale * 10).toBeCloseTo(1)
  })
})
