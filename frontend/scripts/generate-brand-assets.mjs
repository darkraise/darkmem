// Writes public/logo.svg and public/favicon.svg from src/lib/brand-mark.ts, so
// the mark's geometry has exactly one source. `brand-assets.test.ts` fails the
// build when a committed file drifts from what this emits.
//
// Run from frontend/:  node scripts/generate-brand-assets.mjs

import { writeFileSync } from "node:fs"
import { resolve, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { createRequire } from "node:module"

const here = dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)
const ts = require("typescript")
const { readFileSync } = await import("node:fs")

// brand-mark.ts is TypeScript with no runtime dependencies, so transpiling it
// here is cheaper and less brittle than adding a bundler step for two files.
const source = readFileSync(resolve(here, "../src/lib/brand-mark.ts"), "utf8")
const js = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText

const mod = await import(
  `data:text/javascript;base64,${Buffer.from(js).toString("base64")}`
)

const targets = [
  ["logo.svg", mod.buildLogoSvg()],
  ["favicon.svg", mod.buildFaviconSvg()],
]

for (const [name, svg] of targets) {
  const path = resolve(here, "../public", name)
  writeFileSync(path, svg + "\n", "utf8")
  console.log(`wrote public/${name} (${svg.length} bytes)`)
}
