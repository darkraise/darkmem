import { describe, it, expect, beforeEach, afterEach } from "vitest"
import {
  accentFromTokens,
  applyAccentFavicon,
  watchAccentFavicon,
} from "../accent-favicon"
import { DEFAULT_ACCENT } from "../brand-mark"

/** MutationObserver delivers on a microtask, so assertions must yield first. */
const flush = () => new Promise((resolve) => setTimeout(resolve, 0))

function setToken(value: string | null) {
  if (value === null) document.documentElement.style.removeProperty("--primary")
  else document.documentElement.style.setProperty("--primary", value)
}

const iconHref = () =>
  document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.href ?? ""

describe("accentFromTokens", () => {
  afterEach(() => setToken(null))

  it("wraps the bare triplet the library stores into a colour function", () => {
    setToken("262 83% 58%")
    expect(accentFromTokens(document.documentElement)).toBe("hsl(262 83% 58%)")
  })

  it("falls back when the token is absent rather than emitting hsl()", () => {
    setToken(null)
    expect(accentFromTokens(document.documentElement)).toBe(DEFAULT_ACCENT)
  })
})

describe("applyAccentFavicon", () => {
  beforeEach(() => {
    document.head.replaceChildren()
    setToken(null)
  })
  afterEach(() => setToken(null))

  it("repaints an existing icon link in the resolved accent", () => {
    const link = document.createElement("link")
    link.rel = "icon"
    link.href = "/favicon.svg"
    document.head.appendChild(link)

    setToken("161 94% 30%")
    applyAccentFavicon()

    expect(decodeURIComponent(iconHref())).toContain("hsl(161 94% 30%)")
    expect(document.querySelectorAll('link[rel="icon"]')).toHaveLength(1)
  })

  it("creates the link when the document has none", () => {
    setToken("347 77% 50%")
    applyAccentFavicon()

    const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
    expect(link).not.toBeNull()
    expect(link!.type).toBe("image/svg+xml")
    expect(decodeURIComponent(link!.href)).toContain("hsl(347 77% 50%)")
  })

  it("tracks a later accent change instead of keeping the first one", () => {
    setToken("221 83% 53%")
    applyAccentFavicon()
    expect(decodeURIComponent(iconHref())).toContain("hsl(221 83% 53%)")

    setToken("32 95% 44%")
    applyAccentFavicon()

    const href = decodeURIComponent(iconHref())
    expect(href).toContain("hsl(32 95% 44%)")
    expect(href).not.toContain("hsl(221 83% 53%)")
  })
})

describe("watchAccentFavicon", () => {
  let stop: (() => void) | undefined

  beforeEach(() => {
    document.head.replaceChildren()
    setToken(null)
  })
  afterEach(() => {
    stop?.()
    stop = undefined
    setToken(null)
  })

  // The bug this exists for: ThemeProvider writes --primary from its own
  // effect, and React runs child effects first. A consumer that read the token
  // once on mount painted the tab with the *previous* accent and never
  // corrected itself, because its own dependencies were already final.
  it("corrects itself when the theme writes its tokens after mount", async () => {
    setToken("217 91% 60%")
    stop = watchAccentFavicon()
    expect(decodeURIComponent(iconHref())).toContain("hsl(217 91% 60%)")

    // Stands in for ThemeProvider's own late write.
    setToken("142 71% 45%")
    await flush()

    const href = decodeURIComponent(iconHref())
    expect(href).toContain("hsl(142 71% 45%)")
    expect(href).not.toContain("hsl(217 91% 60%)")
  })

  it("follows an accent change made while mounted", async () => {
    setToken("221 83% 53%")
    stop = watchAccentFavicon()

    setToken("262 83% 58%")
    await flush()
    expect(decodeURIComponent(iconHref())).toContain("hsl(262 83% 58%)")

    setToken("32 95% 44%")
    await flush()
    expect(decodeURIComponent(iconHref())).toContain("hsl(32 95% 44%)")
  })

  it("stops repainting once disconnected", async () => {
    setToken("221 83% 53%")
    stop = watchAccentFavicon()
    stop()
    stop = undefined

    setToken("347 77% 50%")
    await flush()
    expect(decodeURIComponent(iconHref())).toContain("hsl(221 83% 53%)")
  })

  it("leaves the icon alone when a rewrite does not move the accent", async () => {
    setToken("221 83% 53%")
    stop = watchAccentFavicon()
    const before = iconHref()

    // A theme drag rewrites the style attribute without moving --primary.
    document.documentElement.style.setProperty("--radius", "0.5rem")
    await flush()

    expect(iconHref()).toBe(before)
    document.documentElement.style.removeProperty("--radius")
  })
})
