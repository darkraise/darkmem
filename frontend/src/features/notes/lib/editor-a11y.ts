import { useEffect, type RefObject } from "react"
import type { PageEditorInstance } from "./editor-schema"

/**
 * BlockNote gap (0.54.2): a checklist item's checkbox and a toggle's
 * disclosure button render with no accessible name, and neither accepts one
 * through `domAttributes`. This names them from the DOM BlockNote produced,
 * and is re-run whenever that DOM changes.
 */
export function labelEditorControls(root: ParentNode): void {
  root
    .querySelectorAll<HTMLInputElement>(
      '[data-content-type="checkListItem"] input[type="checkbox"]',
    )
    .forEach((input) => {
      const label = input.checked ? "Mark as not done" : "Mark as done"
      if (input.getAttribute("aria-label") !== label) {
        input.setAttribute("aria-label", label)
      }
    })

  root.querySelectorAll<HTMLElement>(".bn-toggle-button").forEach((button) => {
    const open =
      button.closest("[data-show-children]")?.getAttribute("data-show-children") ===
      "true"
    const label = open ? "Collapse" : "Expand"
    if (button.getAttribute("aria-label") !== label) {
      button.setAttribute("aria-label", label)
    }
    if (button.getAttribute("aria-expanded") !== String(open)) {
      button.setAttribute("aria-expanded", String(open))
    }
  })
}

type DomObserver = { stop(): void; start(): void }

/**
 * ProseMirror's own observer reads an attribute write inside the editor as a
 * document edit and redraws the block, which replaces the labelled control and
 * re-triggers this pass. `domObserver` is ProseMirror internals, absent from
 * its typings; it is paused around the writes so they are never seen.
 */
export function useEditorControlLabels(
  ref: RefObject<HTMLElement | null>,
  editor: PageEditorInstance,
): void {
  useEffect(() => {
    const root = ref.current
    if (!root) return
    const relabel = () => {
      const domObserver = (
        editor.prosemirrorView as unknown as { domObserver?: DomObserver } | undefined
      )?.domObserver
      domObserver?.stop()
      try {
        labelEditorControls(root)
      } finally {
        domObserver?.start()
      }
    }
    relabel()
    // aria-* is not in this filter, so the pass's own writes never re-trigger
    // this observer; ProseMirror's is the one that has to be paused.
    const observer = new MutationObserver(relabel)
    observer.observe(root, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["data-show-children", "checked"],
    })
    // Ticking a box changes the `checked` property, which no mutation reports.
    root.addEventListener("change", relabel)
    return () => {
      observer.disconnect()
      root.removeEventListener("change", relabel)
    }
  }, [ref, editor])
}
