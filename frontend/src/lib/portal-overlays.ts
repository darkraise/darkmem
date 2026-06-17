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
