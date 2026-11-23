import { describe, expect, it } from "vitest"

// Wire keys, flags and hooks the backend no longer serves. A frontend that
// still names one either reads a key that never arrives or renders a control
// that steers nothing.
const REMOVED = [
  ["w", "context", "boost"],
  ["community", "injection", "enabled"],
  ["by", "context", "conflict"],
  ["flag", "measurements"],
  ["token", "budget"],
  ["watch", "enabled"],
].map((parts) => parts.join("_"))
REMOVED.push(["use", "Vector", "Projection"].join(""))
REMOVED.push(["declare", "Context"].join(""), ["X", "Darkmem", "Context"].join("-"))

const SOURCES = import.meta.glob<string>("/src/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
})

describe("removed names", () => {
  it("no removed name remains in the frontend", () => {
    const files = Object.keys(SOURCES)
    expect(files.length).toBeGreaterThan(100)
    const hits = files.flatMap((file) =>
      REMOVED.filter((name) => SOURCES[file]!.includes(name)).map(
        (name) => `${file}: ${name}`,
      ),
    )
    expect(hits).toEqual([])
  })
})
