import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

const SRC = join(process.cwd(), "src")
const SELF = join(SRC, "__tests__", "text-color-tokens.test.ts")
// A whole `text-primary` / `text-success` class, with or without a variant
// prefix or an opacity suffix — never `text-primary-foreground` or the
// `-text` tokens themselves.
const RAW = /(?<![-\w])text-(?:primary|success|warning|info)(?![-\w])/

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(tsx?|css)$/.test(entry)) out.push(p)
  }
  return out
}

describe("semantic text colours use the contrast-safe tokens", () => {
  it("no source uses text-primary/-success/-warning/-info as a text colour", () => {
    const offenders = walk(SRC)
      .filter((f) => f !== SELF)
      .flatMap((f) =>
        readFileSync(f, "utf8")
          .split("\n")
          .map((line, i) =>
            RAW.test(line) ? `${relative(SRC, f)}:${i + 1}` : null,
          )
          .filter((hit): hit is string => hit !== null),
      )
    expect(
      offenders,
      "use the matching text-*-text token (light-mode contrast)",
    ).toEqual([])
  })

  it("defines the four tokens and aliases them in dark mode", () => {
    const css = readFileSync(join(SRC, "styles", "globals.css"), "utf8")
    for (const token of ["primary", "success", "warning", "info"]) {
      expect(css).toContain(`--color-${token}-text: var(--${token}-text)`)
    }
    expect(css).toContain(
      "--primary-text: color-mix(in oklch, hsl(var(--primary)) 70%, black)",
    )
    expect(css).toMatch(
      /\[data-mode="dark"\]\s*\{[^}]*--primary-text: hsl\(var\(--primary\)\)/,
    )
  })
})
