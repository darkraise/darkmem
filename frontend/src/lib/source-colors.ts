// Null prototype: source names are client-supplied slugs, and inherited
// keys like "constructor" would dodge the ?? fallbacks at the lookup sites.
export const SOURCE_COLORS: Record<string, string> = Object.assign(Object.create(null), {
  "claude-code": "#58a6ff",
  codex: "#e3b341",
  kiro: "#ff7b72",
  cursor: "#39c5cf",
  windsurf: "#1f6feb",
  "gemini-cli": "#7ee787",
  cline: "#db61a2",
  opencode: "#26a641",
  mcp: "#8957e5",
  dashboard: "#f778ba",
  api: "#d2a8ff",
  "mcp-test": "#3fb950",
  "rest-test": "#ffa657",
})

// Distinct from every mapped color so an unmapped source can't render as a
// known client on the dashboard pie. Unmapped sources stay routine: the
// header/User-Agent passthrough produces arbitrary new names.
const FALLBACK_COLORS = [
  "#6e7681",
  "#bc8cff",
  "#9e6a03",
  "#0f6e6b",
  "#bf3989",
  "#57606a",
]

export function sourceColor(name: string, index: number): string {
  return (
    SOURCE_COLORS[name] ??
    FALLBACK_COLORS[index % FALLBACK_COLORS.length] ??
    "#8b949e"
  )
}
