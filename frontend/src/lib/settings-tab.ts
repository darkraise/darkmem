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

export const SETTINGS_TAB_STORAGE_KEY = "darkmem.settings.tab"
export const SETTINGS_TAB_EVENT = "darkmem:settings-tab"

/**
 * Switch the Settings page to `tab` from anywhere in the tree. The page owns
 * the active-tab state, so we persist the choice and broadcast an event it
 * listens for — lets a deep child (e.g. a "Manage Profiles" link inside the
 * pipeline panel) jump tabs without threading a callback through the tree.
 */
export function navigateToSettingsTab(tab: SettingsTabValue): void {
  if (typeof window === "undefined") return
  window.localStorage.setItem(SETTINGS_TAB_STORAGE_KEY, tab)
  window.dispatchEvent(new CustomEvent(SETTINGS_TAB_EVENT, { detail: tab }))
}
