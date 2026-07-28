import { describe, it, expect, beforeEach } from "vitest"
import { readdirSync, readFileSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import {
  QUERY_KEY_SCOPE,
  projectScopedKey,
  useProjectScopedKey,
} from "../query-keys"
import { useProjectStore, DEFAULT_PROJECT } from "@/stores/project-store"
import { renderHook } from "@testing-library/react"

const __dirname = dirname(fileURLToPath(import.meta.url))
const HOOKS_API_DIR = join(__dirname, "..", "..", "hooks", "api")

/**
 * Every leading string literal that appears in a `queryKey:` array
 * anywhere under src/hooks/api — discovered by scanning the directory,
 * never hand-listed (Ruling 1). A new hook that adds a `queryKey:
 * ["somethingNew", ...]` without registering "somethingNew" in
 * QUERY_KEY_SCOPE makes this list contain a member QUERY_KEY_SCOPE does
 * not have, and the completeness test below fails on it by name.
 */
function discoverQueryKeyDomains(): string[] {
  const domains = new Set<string>()
  for (const entry of readdirSync(HOOKS_API_DIR)) {
    if (!entry.endsWith(".ts") || entry.endsWith(".test.ts")) continue
    const source = readFileSync(join(HOOKS_API_DIR, entry), "utf-8")
    const pattern = /queryKey:\s*\[\s*\n?\s*"([a-zA-Z]+)"/g
    for (const match of source.matchAll(pattern)) {
      const domain = match[1]
      if (domain) domains.add(domain)
    }
  }
  return [...domains]
}

describe("query-key layer: completeness (Ruling 1)", () => {
  it("finds at least one domain to check (the scan itself is not vacuous)", () => {
    expect(discoverQueryKeyDomains().length).toBeGreaterThan(10)
  })

  it("every queryKey found under src/hooks/api is classified in QUERY_KEY_SCOPE", () => {
    const discovered = discoverQueryKeyDomains()
    const unclassified = discovered.filter((d) => !(d in QUERY_KEY_SCOPE))
    expect(
      unclassified,
      `New query key(s) found in src/hooks/api with no entry in QUERY_KEY_SCOPE ` +
        `(src/lib/query-keys.ts): ${unclassified.join(", ")}. ` +
        `Classify each as "auto" | "manual" | "global" | "deferred" before adding it.`,
    ).toEqual([])
  })

  it("every entry in QUERY_KEY_SCOPE corresponds to a real queryKey (no stale entries)", () => {
    const discovered = new Set(discoverQueryKeyDomains())
    const stale = Object.keys(QUERY_KEY_SCOPE).filter((d) => !discovered.has(d))
    expect(stale, `QUERY_KEY_SCOPE entries with no matching queryKey: ${stale.join(", ")}`).toEqual(
      [],
    )
  })

  it("manual and deferred entries carry a non-empty reason", () => {
    for (const [domain, scope] of Object.entries(QUERY_KEY_SCOPE)) {
      if (scope.kind === "manual" || scope.kind === "deferred") {
        expect(scope.reason.trim().length, `${domain}: empty reason`).toBeGreaterThan(0)
      }
    }
  })
})

describe("query-key layer: every 'auto' domain mechanically carries the active project", () => {
  beforeEach(() => {
    useProjectStore.setState({
      activeProject: DEFAULT_PROJECT,
      knownProjects: [DEFAULT_PROJECT],
    })
  })

  const autoDomains = Object.entries(QUERY_KEY_SCOPE)
    .filter(([, scope]) => scope.kind === "auto")
    .map(([domain]) => domain)

  it("found at least one 'auto' domain to check", () => {
    expect(autoDomains.length).toBeGreaterThan(0)
  })

  it.each(autoDomains)("projectScopedKey(%s) embeds the active project at index 1", (domain) => {
    useProjectStore.getState().setProject("alpha")
    expect(projectScopedKey(domain)).toEqual([domain, "alpha"])
  })

  it.each(autoDomains)(
    "useProjectScopedKey(%s) re-keys when the active project changes",
    (domain) => {
      const { result, rerender } = renderHook(() => useProjectScopedKey(domain))
      expect(result.current).toEqual([domain, DEFAULT_PROJECT])

      useProjectStore.getState().setProject("beta")
      rerender()
      expect(result.current).toEqual([domain, "beta"])
    },
  )

  it("refuses to build a scoped key for a domain not registered as auto", () => {
    expect(() => projectScopedKey("notARealDomain")).toThrow(/not registered as "auto"/)
  })
})
