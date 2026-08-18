import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

const SRC = join(process.cwd(), "src")
const WRAPPER = join(SRC, "components", "darkmem", "empty-state.tsx")

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.tsx?$/.test(entry)) out.push(p)
  }
  return out
}

describe("EmptyState has one door", () => {
  /**
   * The redesign only holds while the kind decides the mark. A file importing
   * the library component directly can pass any icon it likes, which is
   * exactly how 74 states drifted onto 23 icons and three spellings of one
   * failure. `@/components/darkmem`'s wrapper takes no icon prop, so routing
   * every consumer through it is what makes the set enforceable.
   */
  it("is imported from the library only by its own wrapper", () => {
    const offenders = walk(SRC)
      .filter((f) => f !== WRAPPER)
      // Tests name the path to assert about it; they are not consumers.
      .filter((f) => !f.includes("__tests__"))
      .filter((f) =>
        readFileSync(f, "utf8").includes("darkraise-ui/components/empty-state"),
      )
      .map((f) => relative(SRC, f))

    expect(
      offenders,
      "import { EmptyState } from '@/components/darkmem' instead",
    ).toEqual([])
  })
})
