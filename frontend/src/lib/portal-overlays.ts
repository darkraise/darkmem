// darkraise-ui's DismissableLayer treats any pointerdown outside the dialog's
// own DOM node as an outside click, but Select/Combobox/Popover/menu content
// is portaled to document.body — so picking an option in a dropdown inside a
// dialog would close the dialog. preventDefault() vetoes the close
// (DialogContent checks event.defaultPrevented). Selection itself is safe:
// SelectItem commits on click, which still fires after a canceled pointerdown.
const PORTALED_OVERLAY_SELECTOR = [
  ".dr-select-content",
  ".dr-combobox-content",
  ".dr-popover-content",
  ".dr-menu-content",
].join(", ")

export function ignorePortaledOverlayPointerDown(event: PointerEvent) {
  const target = event.target
  if (
    target instanceof Element &&
    target.closest(PORTALED_OVERLAY_SELECTOR)
  ) {
    event.preventDefault()
  }
}

// darkraise-ui 6.6 gap: Escape pressed while a Select (or Combobox) inside a
// dialog is open closes the whole dialog and loses what was typed. Both are
// DismissableLayers listening on document capture, and the dialog registered
// first. Its "am I the top layer" test only looks for layers nested in its
// own DOM node, and Select content is portaled to document.body, so the
// dialog closes; a Combobox handles Escape in its input's React handler,
// which runs after the dialog's capture listener has already closed it.
//
// Pass this as DialogContent's `onEscapeKeyDown`. When the Escape belongs to
// an open list it vetoes the dialog's close and closes the list itself,
// because the veto (preventDefault) also makes the list's own handler skip
// the event: a Select through its trigger, which toggles; a Combobox through
// the mousedown-outside its click-outside hook listens for, dispatched on the
// dialog itself, which the dialog's own pointerdown guard never sees.
// darkraise-ui 7.0 closes only the open list on its own (asserted unguarded
// in portal-overlays.test.tsx), so this is now redundant and can be retired.
export function keepDialogOpenOnListEscape(event: KeyboardEvent) {
  const target = event.target
  if (!(target instanceof Element)) return

  const listbox = target.closest('[role="listbox"]')
  const labelledBy = listbox?.getAttribute("aria-labelledby")
  // A trigger given its own id (for a <label htmlFor>) no longer carries the
  // id the list's aria-labelledby names, so fall back to the trigger that
  // controls the list, then to the open trigger inside the dialog.
  const selectTrigger = listbox
    ? ((labelledBy ? document.getElementById(labelledBy) : null) ??
      (listbox.id
        ? document.querySelector(`[aria-controls="${CSS.escape(listbox.id)}"]`)
        : null) ??
      document.querySelector(
        '[role="dialog"] button[aria-expanded="true"]',
      ))
    : null
  if (
    selectTrigger instanceof HTMLElement &&
    selectTrigger.getAttribute("aria-expanded") === "true"
  ) {
    event.preventDefault()
    selectTrigger.click()
    return
  }

  if (
    target.getAttribute("role") === "combobox" &&
    target.getAttribute("aria-expanded") === "true"
  ) {
    event.preventDefault()
    const outside =
      target.closest('[role="dialog"], [role="alertdialog"]') ?? document.body
    outside.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))
  }
}
