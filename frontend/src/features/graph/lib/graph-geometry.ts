import type Sigma from "sigma";
import { hexToRgba } from "./graph-colors";

// vis-network is not a dependency of the new frontend; drawHullForGroup
// is only used by MiniGraph (which has been adapted to a list view).
type Network = {
  getPosition: (id: string) => { x: number; y: number } | null;
};

export type HullMode = "none" | "cluster" | "tag" | "source";

export function convexHull(
  pts: { x: number; y: number }[],
): { x: number; y: number }[] {
  if (pts.length < 3) return pts;
  const sorted = [...pts].sort((a, b) => a.x - b.x || a.y - b.y);
  const cross = (
    o: { x: number; y: number },
    a: { x: number; y: number },
    b: { x: number; y: number },
  ) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lower: { x: number; y: number }[] = [];
  for (const p of sorted) {
    while (
      lower.length >= 2 &&
      cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0
    )
      lower.pop();
    lower.push(p);
  }
  const upper: { x: number; y: number }[] = [];
  for (const p of [...sorted].reverse()) {
    while (
      upper.length >= 2 &&
      cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0
    )
      upper.pop();
    upper.push(p);
  }
  upper.pop();
  lower.pop();
  return lower.concat(upper);
}

export function expandHull(
  hull: { x: number; y: number }[],
  padding: number,
): { x: number; y: number }[] {
  if (hull.length === 0) return hull;
  const cx = hull.reduce((s, p) => s + p.x, 0) / hull.length;
  const cy = hull.reduce((s, p) => s + p.y, 0) / hull.length;
  return hull.map((p) => {
    const dx = p.x - cx;
    const dy = p.y - cy;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    return { x: p.x + (dx / dist) * padding, y: p.y + (dy / dist) * padding };
  });
}

export function drawSmoothClosed(
  ctx: CanvasRenderingContext2D,
  hull: { x: number; y: number }[],
) {
  const n = hull.length;
  if (n < 3) return;
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const p0 = hull[(i - 1 + n) % n];
    const p1 = hull[i];
    const p2 = hull[(i + 1) % n];
    const p3 = hull[(i + 2) % n];
    const tension = 6;
    const cp1x = p1.x + (p2.x - p0.x) / tension;
    const cp1y = p1.y + (p2.y - p0.y) / tension;
    const cp2x = p2.x - (p3.x - p1.x) / tension;
    const cp2y = p2.y - (p3.y - p1.y) / tension;
    if (i === 0) ctx.moveTo(p1.x, p1.y);
    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
  }
  ctx.closePath();
}

export function drawHullForGroup(
  ctx: CanvasRenderingContext2D,
  network: Network,
  memberIds: string[],
  color: string,
  fillAlpha: number,
  strokeAlpha: number,
  _label?: string,
) {
  const positions: { x: number; y: number }[] = [];
  for (const id of memberIds) {
    try {
      const pos = network.getPosition(id);
      if (pos) positions.push(pos);
    } catch {
      // node not yet rendered
    }
  }
  if (positions.length < 2) return;

  if (positions.length === 2) {
    const cx = (positions[0].x + positions[1].x) / 2;
    const cy = (positions[0].y + positions[1].y) / 2;
    const dx = positions[1].x - positions[0].x;
    const dy = positions[1].y - positions[0].y;
    const dist = Math.sqrt(dx * dx + dy * dy) / 2 + 50;
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy, dist, dist * 0.6, Math.atan2(dy, dx), 0, Math.PI * 2);
    ctx.fillStyle = hexToRgba(color, fillAlpha);
    ctx.fill();
    ctx.strokeStyle = hexToRgba(color, strokeAlpha);
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
    return;
  }

  const hull = expandHull(convexHull(positions), 45);
  ctx.save();
  drawSmoothClosed(ctx, hull);
  ctx.fillStyle = hexToRgba(color, fillAlpha);
  ctx.fill();
  ctx.strokeStyle = hexToRgba(color, strokeAlpha);
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.restore();
}

export function drawHullForSigma(
  ctx: CanvasRenderingContext2D,
  sigma: Sigma,
  memberIds: string[],
  color: string,
  fillAlpha: number,
  strokeAlpha: number,
) {
  const positions: { x: number; y: number }[] = [];
  for (const id of memberIds) {
    const data = sigma.getNodeDisplayData(id);
    if (data) {
      const vp = sigma.framedGraphToViewport(data);
      positions.push({ x: vp.x, y: vp.y });
    }
  }
  if (positions.length < 2) return;

  if (positions.length === 2) {
    const cx = (positions[0].x + positions[1].x) / 2;
    const cy = (positions[0].y + positions[1].y) / 2;
    const dx = positions[1].x - positions[0].x;
    const dy = positions[1].y - positions[0].y;
    const dist = Math.sqrt(dx * dx + dy * dy) / 2 + 30;
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy, dist, dist * 0.6, Math.atan2(dy, dx), 0, Math.PI * 2);
    ctx.fillStyle = hexToRgba(color, fillAlpha);
    ctx.fill();
    ctx.strokeStyle = hexToRgba(color, strokeAlpha);
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
    return;
  }

  const hull = expandHull(convexHull(positions), 25);
  ctx.save();
  drawSmoothClosed(ctx, hull);
  ctx.fillStyle = hexToRgba(color, fillAlpha);
  ctx.fill();
  ctx.strokeStyle = hexToRgba(color, strokeAlpha);
  ctx.lineWidth = 1.5;
  ctx.stroke();
  ctx.restore();
}

export function computeHullGroups(
  memories: { id: string; cluster: number; tags: string[]; source: string }[],
  hullMode: HullMode,
): Map<string, string[]> {
  const groups = new Map<string, string[]>();
  if (hullMode === "none") return groups;

  for (const m of memories) {
    switch (hullMode) {
      case "cluster": {
        if (m.cluster < 0) break;
        const key = String(m.cluster);
        const arr = groups.get(key) ?? [];
        arr.push(m.id);
        groups.set(key, arr);
        break;
      }
      case "tag": {
        for (const tag of m.tags) {
          const arr = groups.get(tag) ?? [];
          arr.push(m.id);
          groups.set(tag, arr);
        }
        break;
      }
      case "source": {
        const arr = groups.get(m.source) ?? [];
        arr.push(m.id);
        groups.set(m.source, arr);
        break;
      }
    }
  }

  if (hullMode === "tag" || hullMode === "source") {
    for (const [key, members] of groups) {
      if (members.length < 2) groups.delete(key);
    }
  }

  return groups;
}
