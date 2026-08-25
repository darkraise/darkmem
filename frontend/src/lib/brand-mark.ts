/** The darkmem mark, in one place.
 *
 *  Three surfaces need identical geometry — `public/logo.svg` (masked into the
 *  sidebar), `public/favicon.svg` (the pre-script fallback) and the data URI the
 *  runtime favicon builds from the live accent. Three hand-maintained copies
 *  would drift, so they are all derived from here and
 *  `brand-assets.test.ts` fails the build when a committed file stops matching.
 *
 *  Tone is carried by opacity alone, never by a second colour: the sidebar
 *  paints this file as a CSS mask, and a mask reads only the alpha channel.
 */

export const MARK_VIEWBOX = "0 0 32 32"

/** Fallback when `--primary` cannot be read — the library's own default blue. */
export const DEFAULT_ACCENT = "hsl(221 83% 53%)"

/** Same hue one step lighter, for the dark-ground favicon. */
export const DEFAULT_ACCENT_DARK = "hsl(213 94% 68%)"

/** Shapes only, so callers can wrap them in whatever colouring scheme fits. */
function shapes(ink: string): string {
  return (
    `<path d="M12.635 28.557A13 13 0 1 1 28.557 19.365" fill="none" stroke="${ink}"` +
    ` stroke-width="2.4" stroke-linecap="round" opacity=".3"/>` +
    `<rect x="10" y="10.1" width="12" height="2.6" rx="1.3" fill="${ink}" opacity=".45"/>` +
    `<rect x="10" y="14.7" width="8.4" height="2.6" rx="1.3" fill="${ink}" opacity=".72"/>` +
    `<rect x="10" y="19.3" width="5" height="2.6" rx="1.3" fill="${ink}"/>`
  )
}

/**
 * @param ink   any CSS colour the shapes paint with.
 * @param style optional stylesheet injected ahead of the shapes, which is how
 *              the static favicon carries its own light/dark handling.
 */
export function buildMarkSvg(ink: string, style?: string): string {
  const sheet = style ? `<style>${style}</style>` : ""
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${MARK_VIEWBOX}" width="32" height="32">` +
    sheet +
    shapes(ink) +
    `</svg>`
  )
}

/** The mask source: one ink, so only the alpha channel matters. */
export function buildLogoSvg(): string {
  return buildMarkSvg("#000")
}

/**
 * The static favicon. It cannot see the app's tokens — a `<link rel="icon">`
 * document is isolated — so it carries the default accent and swaps on the OS
 * preference. `AccentFavicon` replaces it with the live accent once React runs.
 */
export function buildFaviconSvg(): string {
  const style =
    `:root{--mark:${DEFAULT_ACCENT}}` +
    `@media (prefers-color-scheme:dark){:root{--mark:${DEFAULT_ACCENT_DARK}}}`
  return buildMarkSvg("var(--mark)", style)
}

/** An `<img>`/`<link>`-safe data URI. */
export function markDataUri(ink: string): string {
  return `data:image/svg+xml,${encodeURIComponent(buildMarkSvg(ink))}`
}
