import { NodeCircleProgram } from "sigma/rendering"
import { floatColor } from "sigma/utils"
import type { NodeDisplayData } from "sigma/types"

// A disc whose outline carries the node's identity colour while its body stays
// on one shared neutral. sigma 3 ships no border program and @sigma/node-border
// is not a dependency, so the ring is carved in the fragment shader — the same
// approach node-diamond-program.ts takes for entity nodes on the memory graph.
const BORDERED_VERTEX_SHADER = /* glsl */ `
attribute vec4 a_id;
attribute vec4 a_color;
attribute vec4 a_borderColor;
attribute vec2 a_position;
attribute float a_size;
attribute float a_angle;

uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_correctionRatio;

varying vec4 v_color;
varying vec4 v_borderColor;
varying vec2 v_diffVector;
varying float v_radius;

const float bias = 255.0 / 254.0;

void main() {
  float size = a_size * u_correctionRatio / u_sizeRatio * 4.0;
  vec2 diffVector = size * vec2(cos(a_angle), sin(a_angle));
  vec2 position = a_position + diffVector;
  gl_Position = vec4(
    (u_matrix * vec3(position, 1)).xy,
    0,
    1
  );

  v_diffVector = diffVector;
  v_radius = size / 2.0;

  #ifdef PICKING_MODE
  v_color = a_id;
  v_borderColor = a_id;
  #else
  v_color = a_color;
  v_borderColor = a_borderColor;
  #endif

  v_color.a *= bias;
  v_borderColor.a *= bias;
}
`

const BORDERED_FRAGMENT_SHADER = /* glsl */ `
// highp, not mediump: the vertex stage declares u_correctionRatio too, where
// uniforms default to highp, and GLSL refuses to link a program whose two
// stages disagree on a shared uniform's precision.
precision highp float;

varying vec4 v_color;
varying vec4 v_borderColor;
varying vec2 v_diffVector;
varying float v_radius;

uniform float u_correctionRatio;

const vec4 transparent = vec4(0.0, 0.0, 0.0, 0.0);
const float BORDER_PX = 2.0;

void main(void) {
  float dist = length(v_diffVector);
  // Widths go through u_correctionRatio and NOT u_sizeRatio, which is what
  // holds the ring at a constant pixel weight while the camera zooms.
  float feather = u_correctionRatio * 2.0;

  #ifdef PICKING_MODE
  // Body and ring answer the pick alike, so hit-testing is untouched by the
  // hollow look; only the triangle's corners outside the disc are excluded.
  if (dist > v_radius) gl_FragColor = transparent;
  else gl_FragColor = v_color;
  #else
  float inner = v_radius - u_correctionRatio * BORDER_PX;
  vec4 color = mix(
    v_color,
    v_borderColor,
    smoothstep(inner - feather, inner, dist)
  );
  gl_FragColor = mix(
    color,
    transparent,
    smoothstep(v_radius - feather, v_radius, dist)
  );
  #endif
}
`

const { UNSIGNED_BYTE, FLOAT } = WebGLRenderingContext

export class NodeCircleBorderedProgram extends NodeCircleProgram {
  getDefinition() {
    const def = super.getDefinition()
    return {
      ...def,
      VERTEX_SHADER_SOURCE: BORDERED_VERTEX_SHADER,
      FRAGMENT_SHADER_SOURCE: BORDERED_FRAGMENT_SHADER,
      // Inserted after a_color, and processVisibleItem below writes the
      // interleaved array in exactly this order — the two must move together
      // or every node reads its neighbour's bytes.
      ATTRIBUTES: [
        { name: "a_position", size: 2, type: FLOAT },
        { name: "a_size", size: 1, type: FLOAT },
        { name: "a_color", size: 4, type: UNSIGNED_BYTE, normalized: true },
        { name: "a_borderColor", size: 4, type: UNSIGNED_BYTE, normalized: true },
        { name: "a_id", size: 4, type: UNSIGNED_BYTE, normalized: true },
      ],
    }
  }

  processVisibleItem(nodeIndex: number, startIndex: number, data: NodeDisplayData) {
    const array = this.array
    // Falling back to the fill means a node that never set a borderColor
    // renders exactly as a plain disc, as it did before this program existed.
    const border =
      (data as NodeDisplayData & { borderColor?: string }).borderColor ||
      data.color
    let i = startIndex
    array[i++] = data.x
    array[i++] = data.y
    array[i++] = data.size
    array[i++] = floatColor(data.color)
    array[i++] = floatColor(border)
    array[i++] = nodeIndex
  }
}
