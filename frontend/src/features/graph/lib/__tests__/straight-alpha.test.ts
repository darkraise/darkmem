import { describe, it, expect, vi } from "vitest"
import type { EdgeProgramType, ProgramInfo } from "sigma/rendering"
import type { RenderParams } from "sigma/types"
import { withStraightAlpha } from "../straight-alpha"

const GL = { ONE: 1, SRC_ALPHA: 0x0302, ONE_MINUS_SRC_ALPHA: 0x0303 }

function setup(isPicking: boolean) {
  const draw = vi.fn()
  class Base {
    renderProgram() {
      draw()
    }
  }
  const Straight = withStraightAlpha(Base as unknown as EdgeProgramType)
  const gl = { ...GL, blendFunc: vi.fn(), blendFuncSeparate: vi.fn() }
  const program = new (Straight as unknown as new () => {
    renderProgram(params: RenderParams, info: ProgramInfo): void
  })()
  program.renderProgram({} as RenderParams, { gl, isPicking } as unknown as ProgramInfo)
  return { draw, gl }
}

describe("withStraightAlpha", () => {
  it("premultiplies colour in the blend while drawing, then restores sigma's blend", () => {
    const { draw, gl } = setup(false)
    expect(gl.blendFuncSeparate).toHaveBeenCalledWith(GL.SRC_ALPHA, GL.ONE_MINUS_SRC_ALPHA, GL.ONE, GL.ONE_MINUS_SRC_ALPHA)
    expect(gl.blendFunc).toHaveBeenCalledWith(GL.ONE, GL.ONE_MINUS_SRC_ALPHA)
    const [set] = gl.blendFuncSeparate.mock.invocationCallOrder
    const [drawn] = draw.mock.invocationCallOrder
    const [restored] = gl.blendFunc.mock.invocationCallOrder
    expect(set!).toBeLessThan(drawn!)
    expect(drawn!).toBeLessThan(restored!)
  })

  it("leaves the picking pass's blending alone", () => {
    const { draw, gl } = setup(true)
    expect(draw).toHaveBeenCalledTimes(1)
    expect(gl.blendFuncSeparate).not.toHaveBeenCalled()
    expect(gl.blendFunc).not.toHaveBeenCalled()
  })
})
