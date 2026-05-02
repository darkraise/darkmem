export type SettingsTabValue =
  | "flags"
  | "classification"
  | "workers"
  | "assistant"
  | "llm-providers"
  | "llm-profiles"
  | "ml-profiles"
const KNOWN: SettingsTabValue[] = [
  "flags",
  "classification",
  "workers",
  "assistant",
  "llm-providers",
  "llm-profiles",
  "ml-profiles",
]

export function resolveStoredTab(stored: string | null): SettingsTabValue {
  if (stored && (KNOWN as string[]).includes(stored)) return stored as SettingsTabValue
  return "flags"
}
