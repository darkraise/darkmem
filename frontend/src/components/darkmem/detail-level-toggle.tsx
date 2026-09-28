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
 *    /memories   — every row, through WhyRetrievedTrace.
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
  "/memories",
  "/settings",
] as const

/** Segment-wise prefix match: `/memories` covers `/memories/<id>` but not
 *  `/memoriesarchive`, and `/code` never inherits a decision made for a
 *  differently-named sibling. A bare `startsWith` would conflate them. */
function consumesDetailLevel(pathname: string): boolean {
  return DETAIL_LEVEL_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  )
}

export function DetailLevelToggle() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const level = useDetailLevel((s) => s.level)
  const setLevel = useDetailLevel((s) => s.setLevel)

  // Hidden, not disabled: a disabled control still says "this page has a
  // detail level, you just can't reach it", which is not true here.
  if (!consumesDetailLevel(pathname)) return null

  return (
    <IconSegmented
      value={level}
      options={OPTIONS}
      onChange={setLevel}
      label="Detail level"
    />
  )
}
