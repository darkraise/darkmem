import { NodeCircleProgram } from "sigma/rendering"
import type { NodeProgramType, ProgramInfo } from "sigma/rendering"
import { floatColor } from "sigma/utils"
import type { NodeDisplayData, RenderParams } from "sigma/types"
import type Sigma from "sigma"
import { CLUMP_R0, CORE_K, type Classification } from "./constellation-layout"

export const GLOW_SPREAD = 3

export interface GlowClock {
  time: number
  /** Per-role light and disc-size multipliers for the additive pass. */
  coreGain?: number
  coreScale?: number
  satelliteGain?: number
  satelliteScale?: number
}

/** Discs covering each pixel, on average, that the additive pass can sum
 *  before colour clips toward white. */
export const COVERAGE_TARGET = 0.45
/** Below this a fragment's light rounds away in an 8-bit framebuffer while
 *  thousands of overlapping glows still sum to white. */
export const GAIN_FLOOR = 0.1
const MIN_RADIUS_PX = 1

/**
 * The additive pass sums every overlapping disc and glow, so a wide view of a
 * dense role clips to white and loses its community colours. Coverage is the
 * disc radius over the role's node spacing, never deeper than the role's
 * group. The role's light is scaled to keep the sum near its colours; where
 * that would take it below GAIN_FLOOR, its discs shrink (all alike, so
 * relative sizes hold) until the floor suffices. Zooming in restores both.
 */
export function densityStyle(
  nodeRadiusPx: number,
  spacingPx: number,
  maxOverlap: number,
): { gain: number; scale: number } {
  if (spacingPx <= 0 || nodeRadiusPx <= 0) return { gain: 1, scale: 1 }
  const coverage = (r: number) => Math.min(maxOverlap, (r * r) / (spacingPx * spacingPx))
  const gainFor = (c: number) => (c <= COVERAGE_TARGET ? 1 : COVERAGE_TARGET / c)
  if (gainFor(coverage(nodeRadiusPx)) >= GAIN_FLOOR) {
    return { gain: gainFor(coverage(nodeRadiusPx)), scale: 1 }
  }
  const shrunk = Math.min(
    nodeRadiusPx,
    Math.max(MIN_RADIUS_PX, spacingPx * Math.sqrt(COVERAGE_TARGET / GAIN_FLOOR)),
  )
  return { gain: gainFor(coverage(shrunk)), scale: shrunk / nodeRadiusPx }
}

interface SizedGraph {
  getNodeAttribute(id: string, name: string): unknown
}

function meanSize(graph: SizedGraph, ids: readonly string[]): number {
  let sum = 0
  for (const id of ids) sum += graph.getNodeAttribute(id, "size") as number
  return ids.length ? sum / ids.length : 0
}

/** Keeps the clock's per-role style current: sigma emits beforeRender ahead
 *  of every draw, after any camera move. */
export function trackDensityGain(
  sigma: Pick<Sigma, "on" | "graphToViewport" | "scaleSize">,
  graph: SizedGraph,
  classification: Pick<Classification, "core" | "satellites">,
  clock: GlowClock,
): void {
  const coreSize = meanSize(graph, classification.core)
  const satelliteMembers = classification.satellites.flat()
  const satelliteSize = meanSize(graph, satelliteMembers)
  const clump = satelliteMembers.length / Math.max(1, classification.satellites.length)
  sigma.on("beforeRender", () => {
    const o = sigma.graphToViewport({ x: 0, y: 0 })
    const e = sigma.graphToViewport({ x: 1000, y: 0 })
    const pxPerUnit = Math.hypot(e.x - o.x, e.y - o.y) / 1000
    const core = densityStyle(
      sigma.scaleSize(coreSize),
      CORE_K * pxPerUnit,
      classification.core.length,
    )
    const satellite = densityStyle(sigma.scaleSize(satelliteSize), CLUMP_R0 * pxPerUnit, clump)
    clock.coreGain = core.gain
    clock.coreScale = core.scale
    clock.satelliteGain = satellite.gain
    clock.satelliteScale = satellite.scale
  })
}

const VERTEX_SHADER = /* glsl */ `
attribute vec4 a_id;
attribute vec4 a_color;
attribute vec2 a_position;
attribute float a_size;
attribute float a_angle;
attribute float a_brightness;
attribute float a_phase;

uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_time;
uniform float u_coreGain;
uniform float u_coreScale;
uniform float u_satelliteGain;
uniform float u_satelliteScale;

varying vec4 v_color;
varying vec2 v_diffVector;
varying float v_radius;
varying float v_outer;
varying float v_alpha;

const float bias = 255.0 / 254.0;
const float SPREAD = ${GLOW_SPREAD.toFixed(1)};
const float TAU = 6.283185307179586;

void main() {
  float radius = a_size * u_correctionRatio / u_sizeRatio * 2.0;
  #ifndef LIGHT_MODE
  if (a_brightness > 0.9) radius *= u_coreScale;
  else if (a_brightness > 0.5) radius *= u_satelliteScale;
  #endif
  float outer = radius * SPREAD;
  // The triangle's incircle is half its circumradius, so the vertices sit at
  // twice the glow radius for the whole falloff to fit inside it.
  vec2 diffVector = 2.0 * outer * vec2(cos(a_angle), sin(a_angle));
  vec2 position = a_position + diffVector;
  gl_Position = vec4((u_matrix * vec3(position, 1)).xy, 0, 1);

  v_diffVector = diffVector;
  v_radius = radius;
  v_outer = outer;

  float brightness = a_brightness;
  #ifdef LIGHT_MODE
  if (a_brightness < 0.5) brightness = 0.55;
  #else
  if (a_brightness > 0.9) brightness *= u_coreGain;
  else if (a_brightness > 0.5) brightness *= u_satelliteGain;
  #endif
  if (a_brightness < 0.5) {
    float period = 3.0 + 4.0 * a_phase;
    brightness *= 1.0 + 0.3 * sin(TAU * (u_time / period + a_phase));
  }
  v_alpha = brightness;

  #ifdef PICKING_MODE
  v_color = a_id;
  #else
  v_color = a_color;
  #endif
  v_color.a *= bias;
}
`

const FRAGMENT_SHADER = /* glsl */ `
// highp: the vertex stage declares u_correctionRatio too, and GLSL refuses to
// link stages that disagree on a shared uniform's precision.
precision highp float;

varying vec4 v_color;
varying vec2 v_diffVector;
varying float v_radius;
varying float v_outer;
varying float v_alpha;

uniform float u_correctionRatio;

const vec4 transparent = vec4(0.0, 0.0, 0.0, 0.0);
const float GLOW_STRENGTH = 0.45;

void main(void) {
  float dist = length(v_diffVector);

  #ifdef PICKING_MODE
  gl_FragColor = dist > v_radius ? transparent : v_color;
  #else
  float feather = u_correctionRatio;
  float disc = 1.0 - smoothstep(v_radius - feather, v_radius, dist);
  float shape = disc;
  #ifndef LIGHT_MODE
  float t = max(dist - v_radius, 0.0) / max(v_outer - v_radius, 1e-6);
  float glow = GLOW_STRENGTH * exp(-6.0 * t * t) * (1.0 - step(v_outer, dist));
  shape = max(disc, glow);
  #endif
  float a = shape * v_color.a * v_alpha;
  if (a <= 0.0) discard;
  // Premultiplied, so the additive pass adds light rather than full colour
  // wherever the glow is faint.
  gl_FragColor = vec4(v_color.rgb * a, a);
  #endif
}
`

const { UNSIGNED_BYTE, FLOAT } = WebGLRenderingContext

type GlowDisplayData = NodeDisplayData & { brightness?: number; phase?: number }

export function createNodeGlowProgram(opts: {
  additive: boolean
  clock: GlowClock
}): NodeProgramType {
  const { additive, clock } = opts
  const prefix = additive ? "" : "#define LIGHT_MODE\n"

  return class NodeGlowProgram extends NodeCircleProgram {
    getDefinition() {
      const def = super.getDefinition()
      return {
        ...def,
        VERTEX_SHADER_SOURCE: prefix + VERTEX_SHADER,
        FRAGMENT_SHADER_SOURCE: prefix + FRAGMENT_SHADER,
        // The base class pins its uniform list as a tuple type; sigma reads the
        // array at runtime, so the extra entry only needs to get past the type.
        UNIFORMS: [...def.UNIFORMS, "u_time", "u_coreGain", "u_coreScale", "u_satelliteGain", "u_satelliteScale"] as unknown as typeof def.UNIFORMS,
        // processVisibleItem writes the interleaved array in exactly this order.
        ATTRIBUTES: [
          { name: "a_position", size: 2, type: FLOAT },
          { name: "a_size", size: 1, type: FLOAT },
          { name: "a_color", size: 4, type: UNSIGNED_BYTE, normalized: true },
          { name: "a_id", size: 4, type: UNSIGNED_BYTE, normalized: true },
          { name: "a_brightness", size: 1, type: FLOAT },
          { name: "a_phase", size: 1, type: FLOAT },
        ],
      }
    }

    processVisibleItem(nodeIndex: number, startIndex: number, data: NodeDisplayData) {
      const array = this.array
      const d = data as GlowDisplayData
      let i = startIndex
      array[i++] = d.x
      array[i++] = d.y
      array[i++] = d.size
      array[i++] = floatColor(d.color)
      array[i++] = nodeIndex
      array[i++] = d.brightness ?? 1
      array[i++] = d.phase ?? 0
    }

    setUniforms(params: RenderParams, info: ProgramInfo) {
      super.setUniforms(params, info)
      const locations = info.uniformLocations as Record<string, WebGLUniformLocation>
      info.gl.uniform1f(locations.u_time!, clock.time)
      info.gl.uniform1f(locations.u_coreGain!, clock.coreGain ?? 1)
      info.gl.uniform1f(locations.u_satelliteGain!, clock.satelliteGain ?? 1)
      info.gl.uniform1f(locations.u_coreScale!, clock.coreScale ?? 1)
      info.gl.uniform1f(locations.u_satelliteScale!, clock.satelliteScale ?? 1)
    }

    renderProgram(params: RenderParams, info: ProgramInfo) {
      if (!additive || info.isPicking) {
        super.renderProgram(params, info)
        return
      }
      const gl = info.gl
      gl.blendFunc(gl.ONE, gl.ONE)
      super.renderProgram(params, info)
      // sigma sets this once per context and every other program relies on it.
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
    }
  }
}
