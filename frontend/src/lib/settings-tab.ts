export type SettingsTabValue =
  | "flags"
  | "classification"
  | "assistant"
  | "llm-pipeline"
  | "llm-providers"
  | "llm-profiles"
  | "ml-profiles"
  | "jobs"
  | "security"
  | "maintenance"
const KNOWN: SettingsTabValue[] = [
  "flags",
  "classification",
  "assistant",
  "llm-pipeline",
  "llm-providers",
  "llm-profiles",
  "ml-profiles",
  "jobs",
  "security",
  "maintenance",
]

export function resolveStoredTab(stored: string | null): SettingsTabValue {
  if (stored && (KNOWN as string[]).includes(stored))
    return stored as SettingsTabValue
  return "flags"
}
