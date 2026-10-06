import { AlignLeft, Circle } from "lucide-react"
import { useRouterState } from "@tanstack/react-router"
import { IconSegmented, type IconSegmentedOption } from "./icon-segmented"
import { useDetailLevel, type DetailLevel } from "./use-detail-level"

const OPTIONS: ReadonlyArray<IconSegmentedOption<DetailLevel>> = [
  { value: "simple", label: "Simple", icon: Circle },
  { value: "advanced", label: "Advanced", icon: AlignLeft },
]

/** Route prefixes where something actually reads the detail level.
 *
 *  The toggle is one mount in the app header, but only five of the eight page
 *  areas consume the preference. On the other three it was a live control
 *  that changed nothing — worse than absent, because it invites the reader to
 *  try it and teaches them the setting is broken.
 *
 *  What each entry is earning its place on:
 *    /knowledge  — nine consumers: fact detail, ladder, sources, facts tab,
 *                  review queue, hygiene queue, topics, live dispute, article
 *                  detail (plus the article route itself).
 *    /activity   — day tab (raw id lists), dream digest.
 *    /chat       — the retrieval context panel, through WhyRetrievedTrace.
 *    /memories   — every row, through WhyRetrievedTrace. The list only: a
 *                  memory's own page (/memories/<id>) reads nothing, so it
 *                  is in DETAIL_LEVEL_EXACT_ROUTES, not here by prefix.
 *    /settings   — the Distribution tab's per-target detail. Route-level, so
 *                  the toggle is idle on the other Settings tabs; gating per
 *                  tab would make it appear and vanish *within* one page,
 *                  which reads worse than a control that is occasionally idle.
 *
 *  This is an ALLOWLIST on purpose. A blocklist would default a newly added
 *  page to showing a dead control; defaulting to hidden makes the failure mode
 *  "a real setting is missing" — visible, and someone reports it — rather than
 *  "a dead control shipped", which nobody reports because it looks fine.
 *
 *  Exported so `detail-level-placement.test.tsx` drives its cases off this
 *  list rather than a hand-copied one, and the two cannot drift apart.
 */
export const DETAIL_LEVEL_ROUTES = [
  "/knowledge",
  "/activity",
  "/chat",
  "/settings",
] as const

/** Pages that consume the level while the pages under them do not. */
export const DETAIL_LEVEL_EXACT_ROUTES = ["/memories"] as const

/** Segment-wise prefix match: `/knowledge` covers `/knowledge/<id>` but not
 *  `/knowledgebase`, and `/code` never inherits a decision made for a
 *  differently-named sibling. A bare `startsWith` would conflate them. */
function consumesDetailLevel(pathname: string): boolean {
  return (
    (DETAIL_LEVEL_EXACT_ROUTES as readonly string[]).includes(pathname) ||
    DETAIL_LEVEL_ROUTES.some(
      (route) => pathname === route || pathname.startsWith(`${route}/`),
    )
  )
}

/** Both variants print a visible "Detail" caption: the segments are icon-only
 *  (a circle and lines), so without it the control's meaning lived only in a
 *  hover tooltip. `row` emits the caption and the control as two siblings for
 *  the narrow header popover's two-column grid, so the caption vanishes with
 *  the control on routes that do not consume the level. */
export function DetailLevelToggle({
  variant = "inline",
}: {
  variant?: "inline" | "row"
}) {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const level = useDetailLevel((s) => s.level)
  const setLevel = useDetailLevel((s) => s.setLevel)

  // Hidden, not disabled: a disabled control still says "this page has a
  // detail level, you just can't reach it", which is not true here.
  if (!consumesDetailLevel(pathname)) return null

  const control = (
    <IconSegmented
      value={level}
      options={OPTIONS}
      onChange={setLevel}
      label="Detail level"
    />
  )
  if (variant === "row") {
    return (
      <>
        <span aria-hidden className="text-muted-foreground text-xs font-medium">
          Detail
        </span>
        <div className="flex min-w-0 items-center">{control}</div>
      </>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <span aria-hidden className="text-muted-foreground text-xs">
        Detail
      </span>
      {control}
    </span>
  )
}
