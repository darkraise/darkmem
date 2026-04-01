export const CLUSTER_PALETTE = [
  "#a855f7",
  "#3fb950",
  "#f97316",
  "#06b6d4",
  "#ec4899",
  "#eab308",
  "#6366f1",
  "#14b8a6",
  "#f43f5e",
  "#84cc16",
  "#8b5cf6",
  "#0ea5e9",
];

export const TAG_PALETTE = [
  "#22d3ee",
  "#2dd4bf",
  "#4ade80",
  "#a3e635",
  "#facc15",
  "#fb923c",
];

export const UNCLUSTERED_COLOR = "#8b949e";

export const TYPE_COLOR_PREASSIGNED: Record<string, string> = {
  fact: "#58a6ff",
  decision: "#d2a8ff",
  debug: "#f85149",
  architecture: "#3fb950",
  preference: "#ffa657",
  session: "#79c0ff",
  workflow: "#56d364",
};

const TYPE_COLOR_DYNAMIC = [
  "#f778ba",
  "#bb86fc",
  "#4fc3f7",
  "#aed581",
  "#ffb74d",
  "#ff6b6b",
  "#22d3ee",
  "#e879f9",
];

const typeColorAssignments = new Map<string, string>();
let nextDynamicIdx = 0;

export function clusterColor(id: number): string {
  if (id < 0) return UNCLUSTERED_COLOR;
  return CLUSTER_PALETTE[id % CLUSTER_PALETTE.length];
}

export function tagColor(idx: number): string {
  return TAG_PALETTE[idx % TAG_PALETTE.length];
}

export function typeColor(memoryType: string | null): string {
  if (!memoryType) return UNCLUSTERED_COLOR;
  if (TYPE_COLOR_PREASSIGNED[memoryType]) return TYPE_COLOR_PREASSIGNED[memoryType];
  if (!typeColorAssignments.has(memoryType)) {
    typeColorAssignments.set(
      memoryType,
      TYPE_COLOR_DYNAMIC[nextDynamicIdx % TYPE_COLOR_DYNAMIC.length],
    );
    nextDynamicIdx++;
  }
  return typeColorAssignments.get(memoryType)!;
}

export function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

export function lightenHex(hex: string, amount = 0.35): string {
  const r = Math.min(255, Math.round(parseInt(hex.slice(1, 3), 16) + (255 - parseInt(hex.slice(1, 3), 16)) * amount));
  const g = Math.min(255, Math.round(parseInt(hex.slice(3, 5), 16) + (255 - parseInt(hex.slice(3, 5), 16)) * amount));
  const b = Math.min(255, Math.round(parseInt(hex.slice(5, 7), 16) + (255 - parseInt(hex.slice(5, 7), 16)) * amount));
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

export function darkenHex(hex: string, amount = 0.45): string {
  const r = Math.max(0, Math.round(parseInt(hex.slice(1, 3), 16) * (1 - amount)));
  const g = Math.max(0, Math.round(parseInt(hex.slice(3, 5), 16) * (1 - amount)));
  const b = Math.max(0, Math.round(parseInt(hex.slice(5, 7), 16) * (1 - amount)));
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}
