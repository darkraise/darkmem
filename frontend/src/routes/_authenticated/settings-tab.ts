export type SettingsTabValue = "flags" | "classification" | "workers" | "assistant"
const KNOWN: SettingsTabValue[] = ["flags", "classification", "workers", "assistant"]

export function resolveStoredTab(stored: string | null): SettingsTabValue {
  if (stored && (KNOWN as string[]).includes(stored)) return stored as SettingsTabValue
  return "flags"
}
