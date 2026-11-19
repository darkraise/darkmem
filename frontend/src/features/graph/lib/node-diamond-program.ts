import { NodeSquareProgram } from "@sigma/node-square"
import { floatColor } from "sigma/utils"
import type { Settings } from "sigma/settings"
import type { NodeDisplayData, PartialButFor } from "sigma/types"
import type { GraphThemeTokens } from "./code-graph-theme"
import { drawFocusRing, drawLabelPlate, hoverChrome } from "./node-hover"
import type { ChromeKind } from "./node-hover"
import type { SelectionColor } from "./graph-prefs"

const DIAMOND_VERTEX_SHADER = /* glsl */ `
attribute vec4 a_id;
attribute vec4 a_color;
attribute vec4 a_borderColor;
attribute vec2 a_position;
attribute float a_size;
attribute float a_angle;

uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_cameraAngle;
uniform float u_correctionRatio;

varying vec4 v_color;
varying vec4 v_borderColor;
varying vec2 v_diffVector;
varying float v_size;

const float bias = 255.0 / 254.0;
const float sqrt_8 = sqrt(8.0);
const float ROTATION = 0.7854; // π/4 = 45°

void main() {
  float size = a_size * u_correctionRatio / u_sizeRatio * sqrt_8;
  float angle = a_angle + u_cameraAngle + ROTATION;
  vec2 diffVector = size * vec2(cos(angle), sin(angle));
  vec2 position = a_position + diffVector;
  gl_Position = vec4(
    (u_matrix * vec3(position, 1)).xy,
    0,
    1
  );

  // Handed to the fragment shader so it can tell body from border. The quad's
  // four corners ARE the diamond's, so the L1 norm of this vector is exactly
  // v_size along the outline and 0 at the centre.
  v_diffVector = diffVector;
  v_size = size;

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

const DIAMOND_FRAGMENT_SHADER = /* glsl */ `
// highp, not mediump: the vertex stage declares u_correctionRatio too, where
// uniforms default to highp, and GLSL refuses to link a program whose two
// stages disagree on a shared uniform's precision.
precision highp float;

varying vec4 v_color;
varying vec4 v_borderColor;
varying vec2 v_diffVector;
varying float v_size;

uniform float u_correctionRatio;

const float sqrt_2 = sqrt(2.0);
const float BORDER_PX = 2.0;
const float FEATHER_PX = 1.0;

void main(void) {
  float dist = abs(v_diffVector.x) + abs(v_diffVector.y);

  #ifdef PICKING_MODE
  // Body and border answer the pick alike, so hit-testing is untouched by the
  // hollow look — clicking the middle of an entity still selects it.
  gl_FragColor = v_color;
  #else
  // The sqrt(2) converts a perpendicular width into this L1 metric: a
  // diamond's edges run at 45 degrees, so an L1 step of d crosses only
  // d / sqrt(2) of actual width. Widths go through u_correctionRatio and NOT
  // u_sizeRatio, which is what holds the border at a constant pixel weight
  // while the camera zooms.
  float border = u_correctionRatio * BORDER_PX * sqrt_2;
  float feather = u_correctionRatio * FEATHER_PX * sqrt_2;
  float inner = v_size - border;
  gl_FragColor = mix(
    v_color,
    v_borderColor,
    smoothstep(inner - feather, inner + feather, dist)
  );
  #endif
}
`

export function drawDiamondNodeHover(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
  tokens: GraphThemeTokens,
  color: SelectionColor,
  kind: ChromeKind,
): void {
  const chrome = hoverChrome(tokens, color, kind, data.color)
  drawLabelPlate(context, data, settings, chrome)
  drawFocusRing(context, data.x, data.y, data.size, chrome, "diamond")
}

const { UNSIGNED_BYTE, FLOAT } = WebGLRenderingContext

export class NodeDiamondProgram extends NodeSquareProgram {
  constructor(...args: ConstructorParameters<typeof NodeSquareProgram>) {
    super(...args)
    // Clear inherited drawSquareNodeHover so sigma falls through to
    // defaultDrawNodeHover where we route to drawDiamondNodeHover.
    //
    // The cast is load-bearing: sigma's base class declares `drawHover` as
    // `... | undefined`, but NodeSquareProgram narrows it to a required
    // function, so clearing it is outside the declared type while being
    // exactly what the renderer supports.
    this.drawHover = undefined as unknown as typeof this.drawHover
    // Same reason, same cast: clearing the inherited drawSquareNodeLabel lets
    // sigma fall through to defaultDrawNodeLabel, where the renderers install
    // the ring-clearing offset. Without this a diamond's resting label sits at
    // sigma's hardcoded 3px while every disc's sits outside the ring.
    this.drawLabel = undefined as unknown as typeof this.drawLabel
  }

  getDefinition() {
    const def = super.getDefinition()
    return {
      ...def,
      VERTEX_SHADER_SOURCE: DIAMOND_VERTEX_SHADER,
      FRAGMENT_SHADER_SOURCE: DIAMOND_FRAGMENT_SHADER,
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
    // borderColor rides the node attributes and survives the reducer's object
    // spread; falling back to the fill means a node that never set one renders
    // exactly as it did before this program grew a border.
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
