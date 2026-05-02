export type SettingsTabValue =
  | "flags"
  | "classification"
  | "workers"
  | "assistant"
  | "llm-providers"
  | "llm-profiles"
const KNOWN: SettingsTabValue[] = [
  "flags",
  "classification",
  "workers",
  "assistant",
  "llm-providers",
  "llm-profiles",
]

export function resolveStoredTab(stored: string | null): SettingsTabValue {
  if (stored && (KNOWN as string[]).includes(stored)) return stored as SettingsTabValue
  return "flags"
}
