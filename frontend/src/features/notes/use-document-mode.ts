import { useSyncExternalStore } from "react"

export type DocumentMode = "light" | "dark"

function read(): DocumentMode {
  return document.documentElement.dataset.mode === "dark" ? "dark" : "light"
}

function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-mode"] })
  return () => observer.disconnect()
}

/** The resolved colour mode darkraise-ui's ThemeProvider writes to
 *  `<html data-mode>`. Read from the document rather than through
 *  `useTheme()`, which throws outside a ThemeProvider, so the editor renders
 *  in any tree a test mounts it in. */
export function useDocumentMode(): DocumentMode {
  return useSyncExternalStore(subscribe, read, () => "light")
}
