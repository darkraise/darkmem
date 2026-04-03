export type ColorMode = "type" | "cluster" | "tag";

export const PALETTE_400 = [
  "#f87171","#fb923c","#fbbf24","#facc15","#a3e635","#4ade80","#34d399",
  "#2dd4bf","#22d3ee","#38bdf8","#60a5fa","#818cf8","#a78bfa","#c084fc",
  "#e879f9","#f472b6","#fb7185",
];

export const PALETTE_200 = [
  "#fecaca","#fed7aa","#fde68a","#fef08a","#d9f99d","#bbf7d0","#a7f3d0",
  "#99f6e4","#a5f3fc","#bae6fd","#bfdbfe","#c7d2fe","#ddd6fe","#e9d5ff",
  "#f5d0fe","#fbcfe8","#fecdd3",
];

export const PALETTE_600 = [
  "#dc2626","#ea580c","#d97706","#ca8a04","#65a30d","#16a34a","#059669",
  "#0d9488","#0891b2","#0284c7","#2563eb","#4f46e5","#7c3aed","#9333ea",
  "#c026d3","#db2777","#e11d48",
];

export const UNIFIED_PALETTE = [...PALETTE_400, ...PALETTE_200, ...PALETTE_600];

export const UNCLUSTERED_COLOR = "#8b949e";

const KNOWN_TYPE_INDICES: Record<string, number> = {
  fact: 10,
  decision: 12,
  debug: 0,
  architecture: 5,
  preference: 1,
  session: 8,
  workflow: 6,
};

function stableHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (Math.imul(31, hash) + str.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export function resolveNodeColor(
  node: { cluster: number; memory_type: string | null; tags: string[] },
  colorMode: ColorMode,
): string {
  if (colorMode === "cluster") {
    if (node.cluster < 0) return UNCLUSTERED_COLOR;
    return UNIFIED_PALETTE[node.cluster % 51];
  }

  if (colorMode === "type") {
    if (!node.memory_type) return UNCLUSTERED_COLOR;
    const idx = KNOWN_TYPE_INDICES[node.memory_type];
    if (idx !== undefined) return UNIFIED_PALETTE[idx];
    return UNIFIED_PALETTE[stableHash(node.memory_type) % 51];
  }

  // tag mode
  if (!node.tags || node.tags.length === 0) return UNCLUSTERED_COLOR;
  const prefix = node.tags[0].split("/")[0];
  return UNIFIED_PALETTE[stableHash(prefix) % 51];
}

export function resolveGroupColor(
  groupKey: string,
  groupIndex: number,
  colorMode: ColorMode,
  hullMode: string,
): string {
  if (colorMode === hullMode && colorMode === "cluster") {
    const id = parseInt(groupKey, 10);
    if (!isNaN(id) && id >= 0) return UNIFIED_PALETTE[id % 51];
    return UNCLUSTERED_COLOR;
  }

  if (colorMode === hullMode && colorMode === "tag") {
    const prefix = groupKey.split("/")[0];
    return UNIFIED_PALETTE[stableHash(prefix) % 51];
  }

  return UNIFIED_PALETTE[groupIndex % 51];
}

export const ENTITY_TYPE_COLORS: Record<string, string> = {
  person: "#60a5fa",
  service: "#4ade80",
  project: "#c084fc",
  technology: "#fb923c",
  concept: "#8b949e",
  organization: "#f472b6",
};

export function entityTypeColor(entityType: string): string {
  return ENTITY_TYPE_COLORS[entityType] ?? "#8b949e";
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

export function blendHex(hex1: string, hex2: string, ratio = 0.5): string {
  const r = Math.round(parseInt(hex1.slice(1, 3), 16) * (1 - ratio) + parseInt(hex2.slice(1, 3), 16) * ratio);
  const g = Math.round(parseInt(hex1.slice(3, 5), 16) * (1 - ratio) + parseInt(hex2.slice(3, 5), 16) * ratio);
  const b = Math.round(parseInt(hex1.slice(5, 7), 16) * (1 - ratio) + parseInt(hex2.slice(5, 7), 16) * ratio);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

export function darkenHex(hex: string, amount = 0.45): string {
  const r = Math.max(0, Math.round(parseInt(hex.slice(1, 3), 16) * (1 - amount)));
  const g = Math.max(0, Math.round(parseInt(hex.slice(3, 5), 16) * (1 - amount)));
  const b = Math.max(0, Math.round(parseInt(hex.slice(5, 7), 16) * (1 - amount)));
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}
