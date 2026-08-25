import { DEFAULT_ACCENT, markDataUri } from "./brand-mark"

/** The token the library resolves the brand colour into. */
const ACCENT_TOKEN = "--primary"

/**
 * `--primary` holds a bare HSL triplet (`221 83% 53%`), not a colour function,
 * because the library composes alpha onto it as `hsl(var(--primary) / .5)`.
 */
export function accentFromTokens(root: HTMLElement): string {
  const triplet = getComputedStyle(root).getPropertyValue(ACCENT_TOKEN).trim()
  return triplet ? `hsl(${triplet})` : DEFAULT_ACCENT
}

function iconLink(doc: Document): HTMLLinkElement {
  const existing = doc.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (existing) return existing
  const link = doc.createElement("link")
  link.rel = "icon"
  doc.head.appendChild(link)
  return link
}

/**
 * Repaints the favicon in the currently resolved accent.
 *
 * A `<link rel="icon">` loads its SVG as an isolated document, so the file
 * cannot read `--primary` the way the masked sidebar mark can. Rebuilding the
 * icon as a data URI is the only way it tracks the accent picker.
 */
export function applyAccentFavicon(doc: Document = document): string {
  const ink = accentFromTokens(doc.documentElement)
  const href = markDataUri(ink)
  const link = iconLink(doc)
  link.type = "image/svg+xml"
  link.href = href
  return href
}

/**
 * Repaints the icon now, and again whenever the theme rewrites its tokens.
 *
 * Observing the element rather than subscribing to the theme's own state is
 * deliberate. `ThemeProvider` applies tokens as inline styles on `<html>` from
 * its own effect, and React runs child effects before parent ones — so a
 * consumer that merely reads the token on mount reads the *previous* accent and
 * never learns it was wrong, because its dependencies were already at their
 * final values. Watching the attribute removes the ordering question entirely,
 * and picks up every axis that feeds `--primary` without enumerating them.
 */
export function watchAccentFavicon(doc: Document = document): () => void {
  let applied = ""

  const sync = () => {
    const ink = accentFromTokens(doc.documentElement)
    // A theme drag rewrites the style attribute continuously; only the ink
    // actually reaching the tab is worth rebuilding a data URI for.
    if (ink === applied) return
    applied = ink
    applyAccentFavicon(doc)
  }

  sync()
  const observer = new MutationObserver(sync)
  observer.observe(doc.documentElement, {
    attributes: true,
    // `style` carries the tokens; `data-mode` is watched too so a resolved
    // light/dark flip is caught even if a future version stops rewriting
    // the custom properties for it.
    attributeFilter: ["style", "data-mode"],
  })
  return () => observer.disconnect()
}
