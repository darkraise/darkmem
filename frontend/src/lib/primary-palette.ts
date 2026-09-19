import type { ParticleBackgroundProps } from "@/components/particle-background"

/** The theme stores colours as bare HSL triples ("221 83% 53%"). */
export function hslTripleToRgb(triple: string): [number, number, number] | null {
  const m = triple.trim().match(/^(-?[\d.]+)(?:deg)?\s+([\d.]+)%\s+([\d.]+)%$/)
  if (!m) return null
  const h = ((Number(m[1]) % 360) + 360) % 360
  const s = Number(m[2]) / 100
  const l = Number(m[3]) / 100
  const a = s * Math.min(l, 1 - l)
  const channel = (n: number) => {
    const k = (n + h / 30) % 12
    return Math.round((l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))) * 255)
  }
  return [channel(0), channel(8), channel(4)]
}

/** Particle colours from the live accent, so the guest backdrop follows the
 *  Appearance picker instead of a fixed palette. */
export function readPrimaryParticleColors(
  root: HTMLElement = document.documentElement,
): ParticleBackgroundProps["colors"] {
  // The theme provider writes the live accent as an inline style on <html>;
  // the stylesheet default is the fallback before it has run.
  const triple =
    root.style.getPropertyValue("--primary") ||
    getComputedStyle(root).getPropertyValue("--primary")
  const rgb = hslTripleToRgb(triple)
  if (!rgb) return undefined
  const [r, g, b] = rgb
  const solid = `rgb(${r}, ${g}, ${b})`
  return {
    nodes: [solid, `rgba(${r}, ${g}, ${b}, 0.7)`],
    accents: [solid],
    link: `${r},${g},${b}`,
    mouseLink: `${r},${g},${b}`,
  }
}
