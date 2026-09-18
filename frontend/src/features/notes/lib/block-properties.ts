export type Properties = Record<string, unknown> | null

/** The keys each page block type defines -- a copy of
 *  `backend/app/services/block_verbs.py`'s `_PAGE_TYPE_PROPERTIES`, which is
 *  the authority. A type change drops every other key. */
export const PAGE_TYPE_PROPERTIES: Readonly<Record<string, readonly string[]>> = {
  paragraph: [],
  heading: ["level"],
  list: ["ordered", "marker", "number"],
  code: ["language"],
  quote: [],
  table: ["header", "alignments"],
  table_row: ["cells"],
  divider: [],
  html: [],
  todo: ["checked"],
  toggle: [],
  callout: ["variant"],
}

/** `_PAGE_CONTAINERS`: the only types that hold children on a page, besides a
 *  table holding its rows. */
export const PAGE_CONTAINERS: ReadonlySet<string> = new Set(["list", "todo", "toggle"])

export const CALLOUT_VARIANTS = ["error", "info", "success", "warning"] as const
export type CalloutVariant = (typeof CALLOUT_VARIANTS)[number]

export function isCalloutVariant(value: unknown): value is CalloutVariant {
  return typeof value === "string" && (CALLOUT_VARIANTS as readonly string[]).includes(value)
}

function nonEmpty(props: Record<string, unknown>): Properties {
  return Object.keys(props).length === 0 ? null : props
}

/** The properties `update_block` stores: the sent keys merged over the stored
 *  ones, then, on a type change, only the keys the new type defines. */
export function mergeProperties(
  stored: Properties,
  sent: Properties,
  oldType: string,
  newType: string,
): Properties {
  const merged = nonEmpty({ ...(stored ?? {}), ...(sent ?? {}) })
  if (merged === null || oldType === newType) return merged
  const defined = PAGE_TYPE_PROPERTIES[newType] ?? []
  return nonEmpty(Object.fromEntries(Object.entries(merged).filter(([k]) => defined.includes(k))))
}

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical)
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value as object)
        .sort()
        .map((k) => [k, canonical((value as Record<string, unknown>)[k])]),
    )
  }
  return value
}

/** Deep equality with `null` and `{}` equal, since the server stores an empty
 *  merge as NULL. */
export function propertiesEqual(a: Properties, b: Properties): boolean {
  return JSON.stringify(canonical(nonEmpty(a ?? {}))) === JSON.stringify(canonical(nonEmpty(b ?? {})))
}

/** `_check_page_nesting`: may a block of `parentType` (null = the page root)
 *  hold a block of `childType`. */
export function canHold(parentType: string | null, childType: string): boolean {
  if (parentType === null || PAGE_CONTAINERS.has(parentType)) return true
  return parentType === "table" && childType === "table_row"
}

/** `_validate_page_block`'s required properties; the message is the server's. */
export function invalidProperties(type: string, props: Properties): string | null {
  const p = props ?? {}
  if (type === "todo" && typeof p.checked !== "boolean") {
    return "a todo block needs a boolean `checked` property"
  }
  if (type === "callout" && !isCalloutVariant(p.variant)) {
    return `a callout block needs \`variant\` set to one of ${CALLOUT_VARIANTS.join(", ")}`
  }
  return null
}
