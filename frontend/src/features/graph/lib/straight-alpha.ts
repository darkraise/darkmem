import type { EdgeProgramType, ProgramInfo } from "sigma/rendering"
import type { RenderParams } from "sigma/types"

type EdgeProgramClass = new (...args: never[]) => {
  renderProgram(params: RenderParams, info: ProgramInfo): void
}

/**
 * sigma's edge shaders emit straight (not premultiplied) colour, yet sigma
 * blends with ONE, ONE_MINUS_SRC_ALPHA, which expects premultiplied colour.
 * Over the transparent canvas the backdrop needs, an edge at 8% alpha then
 * lands at nearly full strength. Premultiplying in the blend keeps a faint
 * edge faint; sigma's own blend is restored for every other program.
 */
export function withStraightAlpha<T extends EdgeProgramType>(Base: T): T {
  const Straight = class extends (Base as unknown as EdgeProgramClass) {
    renderProgram(params: RenderParams, info: ProgramInfo) {
      if (info.isPicking) {
        super.renderProgram(params, info)
        return
      }
      const gl = info.gl
      gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
      super.renderProgram(params, info)
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
    }
  }
  return Straight as unknown as T
}
