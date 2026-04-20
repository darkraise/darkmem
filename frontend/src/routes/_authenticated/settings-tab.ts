export type SettingsTabValue = "flags" | "classification" | "workers" | "assistant"
const LEGACY: Record<string, SettingsTabValue> = { ml: "flags", prompts: "assistant" }
const KNOWN: SettingsTabValue[] = ["flags", "classification", "workers", "assistant"]

export function resolveStoredTab(stored: string | null): SettingsTabValue {
  if (stored && LEGACY[stored]) return LEGACY[stored]
  if (stored && (KNOWN as string[]).includes(stored)) return stored as SettingsTabValue
  return "flags"
}
