import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

const SRC = join(process.cwd(), "src")
const SELF = join(SRC, "__tests__", "min-text-size.test.ts")
const TOO_SMALL = /text-\[(?:[0-9]|1[01])(?:\.\d+)?px\]/

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(tsx?|css)$/.test(entry)) out.push(p)
  }
  return out
}

describe("text is never smaller than 12px", () => {
  it("no source sets an arbitrary text size below 12px", () => {
    const offenders = walk(SRC)
      .filter((f) => f !== SELF)
      .flatMap((f) =>
        readFileSync(f, "utf8")
          .split("\n")
          .map((line, i) => (TOO_SMALL.test(line) ? `${relative(SRC, f)}:${i + 1}` : null))
          .filter((hit): hit is string => hit !== null),
      )
    expect(offenders, "use text-xs (13px in this app) or larger").toEqual([])
  })
})
