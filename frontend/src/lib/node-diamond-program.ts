import { NodeSquareProgram } from "@sigma/node-square";
import { drawDiscNodeLabel } from "sigma/rendering";
import type { Settings } from "sigma/settings";
import type { NodeDisplayData, PartialButFor } from "sigma/types";

const DIAMOND_VERTEX_SHADER = /* glsl */ `
attribute vec4 a_id;
attribute vec4 a_color;
attribute vec2 a_position;
attribute float a_size;
attribute float a_angle;

uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_cameraAngle;
uniform float u_correctionRatio;

varying vec4 v_color;

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

  #ifdef PICKING_MODE
  v_color = a_id;
  #else
  v_color = a_color;
  #endif

  v_color.a *= bias;
}
`;

function drawDiamondNodeHover(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
): void {
  const size = settings.labelSize;
  const font = settings.labelFont;
  const weight = settings.labelWeight;
  context.font = `${weight} ${size}px ${font}`;

  context.fillStyle = "#FFF";
  context.shadowOffsetX = 0;
  context.shadowOffsetY = 0;
  context.shadowBlur = 8;
  context.shadowColor = "#000";

  const PADDING = 2;
  const r = data.size + PADDING;

  if (typeof data.label === "string") {
    const textWidth = context.measureText(data.label).width;
    const boxWidth = Math.round(textWidth + 5);
    const boxHeight = Math.round(size + 2 * PADDING);

    context.beginPath();
    // Diamond shape on the left (rotated square)
    context.moveTo(data.x, data.y - r);     // top
    context.lineTo(data.x + r, data.y);     // right
    // Label box extending right from the diamond
    context.lineTo(data.x + r, data.y + boxHeight / 2);
    context.lineTo(data.x + r + boxWidth, data.y + boxHeight / 2);
    context.lineTo(data.x + r + boxWidth, data.y - boxHeight / 2);
    context.lineTo(data.x + r, data.y - boxHeight / 2);
    context.lineTo(data.x + r, data.y);     // back to right point
    context.lineTo(data.x, data.y + r);     // bottom
    context.lineTo(data.x - r, data.y);     // left
    context.closePath();
    context.fill();
  } else {
    // Diamond shape only (no label)
    context.beginPath();
    context.moveTo(data.x, data.y - r);
    context.lineTo(data.x + r, data.y);
    context.lineTo(data.x, data.y + r);
    context.lineTo(data.x - r, data.y);
    context.closePath();
    context.fill();
  }

  context.shadowOffsetX = 0;
  context.shadowOffsetY = 0;
  context.shadowBlur = 0;

  // Draw diamond border on top of the node
  const br = data.size * 0.75 + 2;
  context.beginPath();
  context.moveTo(data.x, data.y - br);
  context.lineTo(data.x + br, data.y);
  context.lineTo(data.x, data.y + br);
  context.lineTo(data.x - br, data.y);
  context.closePath();
  context.strokeStyle = "#ffffff";
  context.lineWidth = 3;
  context.stroke();

  drawDiscNodeLabel(context, data, settings);
}

export class NodeDiamondProgram extends NodeSquareProgram {
  constructor(...args: ConstructorParameters<typeof NodeSquareProgram>) {
    super(...args);
    this.drawHover = drawDiamondNodeHover;
  }

  getDefinition() {
    const def = super.getDefinition();
    return {
      ...def,
      VERTEX_SHADER_SOURCE: DIAMOND_VERTEX_SHADER,
    };
  }
}
