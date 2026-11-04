import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

const SRC = join(process.cwd(), "src")
const SELF = join(SRC, "__tests__", "text-color-tokens.test.ts")
// A whole `text-primary` / `text-success` class, with or without a variant
// prefix or an opacity suffix — never `text-primary-foreground` or the
// `-text` tokens themselves.
const RAW = /(?<![-\w])text-(?:primary|success|warning|info)(?![-\w])/
// darkraise-ui 7.0 removed the bare status colours, and Tailwind drops an
// unknown utility without a word: `bg-warning/10` would paint nothing.
const REMOVED_STATUS =
  /(?<![-\w])(?:bg|text|border|ring|outline|fill|stroke|divide|from|via|to)-(?:destructive|success|warning|info)(?![-\w])|var\(--(?:destructive|success|warning|info)(?:-foreground)?\)/

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(tsx?|css)$/.test(entry)) out.push(p)
  }
  return out
}

function offendersOf(pattern: RegExp): string[] {
  return walk(SRC)
    .filter((f) => f !== SELF)
    .flatMap((f) =>
      readFileSync(f, "utf8")
        .split("\n")
        .map((line, i) =>
          pattern.test(line) ? `${relative(SRC, f)}:${i + 1}` : null,
        )
        .filter((hit): hit is string => hit !== null),
    )
}

describe("semantic text colours use the contrast-safe tokens", () => {
  it("no source uses text-primary/-success/-warning/-info as a text colour", () => {
    expect(
      offendersOf(RAW),
      "use the matching text-*-text token (light-mode contrast)",
    ).toEqual([])
  })

  it("no source uses a status colour darkraise-ui 7.0 removed", () => {
    expect(
      offendersOf(REMOVED_STATUS),
      "use the -solid, -edge, -subtle or -text status token",
    ).toEqual([])
  })

  it("defines the primary text token and aliases it in dark mode", () => {
    const css = readFileSync(join(SRC, "styles", "globals.css"), "utf8")
    expect(css).toContain("--color-primary-text: var(--primary-text)")
    expect(css).toContain(
      "--primary-text: color-mix(in oklch, hsl(var(--primary)) 70%, black)",
    )
    expect(css).toMatch(
      /\[data-mode="dark"\]\s*\{[^}]*--primary-text: hsl\(var\(--primary\)\)/,
    )
  })
})
