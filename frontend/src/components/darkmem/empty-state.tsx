import type { ReactNode } from "react"
import {
  CircleAlert,
  CircleCheck,
  FileQuestion,
  Inbox,
  SearchX,
  type LucideIcon,
} from "lucide-react"
import { EmptyState as UiEmptyState } from "darkraise-ui/components/empty-state"
import { cn } from "darkraise-ui/lib"

/**
 * Which situation produced the absence. The kind is the only input that
 * decides the mark and the colour — a caller cannot pass an icon, which is
 * what stops two surfaces drawing the same event differently.
 *
 * - `empty`    nothing exists yet
 * - `filtered` a query, scope or selection excluded everything
 * - `missing`  a specific id does not resolve
 * - `failed`   the request errored — never render this as an absence
 * - `resolved` zero is the good outcome, not a gap
 *
 * There is deliberately no `loading` kind. A pending request is not an
 * absence, and rendering it as one told the reader the vault was bare while
 * it was still being read; use a Skeleton in the shape of the content.
 */
export type EmptyStateKind =
  | "empty"
  | "filtered"
  | "missing"
  | "failed"
  | "resolved"

/** Icon and semantic token per kind, from darkraise-ui's own token set — the
 *  same four the app already uses for status elsewhere. */
const MARK: Record<EmptyStateKind, { icon: LucideIcon; tone: string }> = {
  empty: { icon: Inbox, tone: "text-muted-foreground" },
  filtered: { icon: SearchX, tone: "text-info-text" },
  missing: { icon: FileQuestion, tone: "text-warning-text" },
  failed: { icon: CircleAlert, tone: "text-destructive" },
  resolved: { icon: CircleCheck, tone: "text-success-text" },
}

interface EmptyStateBase {
  title: string
  description?: ReactNode
  /** The one action that resolves this state — retry, clear the filter, go
   *  back, create the first one. Omit where nothing the reader can do would
   *  change it. */
  action?: ReactNode
  /**
   * `panel` (default) sits at natural height inside the card that already
   * owns the section's boundary. `page` centres in the content area for a
   * whole-page absence, where the library's `py-10` alone would strand the
   * state just under the header of a tall empty column.
   *
   * Neither adds a container: an empty state fills the one that owns the
   * content, it never introduces its own.
   */
  scope?: "panel" | "page"
  className?: string
}

/**
 * Only `empty` takes an icon, and the union is what enforces that.
 *
 * A page's own emblem says *where you are* — a vault with nothing in it yet
 * is still the Memories page, still the Topics page. That is worth carrying.
 * The other four say *what happened*, and an event that renders differently
 * on every screen is the drift this set exists to close: a reader cannot
 * learn twenty-three marks, but can learn that amber-question means "this id
 * does not resolve" anywhere it appears. So passing `icon` with
 * `kind="failed"` is a type error, not a style choice.
 */
export type EmptyStateProps =
  | (EmptyStateBase & { kind: "empty"; icon?: LucideIcon })
  | (EmptyStateBase & { kind: Exclude<EmptyStateKind, "empty"> })

export function EmptyState(props: EmptyStateProps) {
  const { kind, title, description, action, scope = "panel", className } = props
  const { icon: fallback, tone } = MARK[kind]
  const Icon = (kind === "empty" && props.icon) || fallback
  return (
    <UiEmptyState
      // The chip is 48px with a 24px glyph by default. Both step up here so
      // the mark carries a page-scale absence; `--icon-scale` is kept in the
      // expression so the theme's font-size axis still moves it.
      className={cn(
        "[&_.dr-empty-state-icon]:size-14",
        "[&_.dr-empty-state-icon_svg]:size-[calc(2rem*var(--icon-scale))]",
        scope === "page" && "min-h-[22rem] justify-center",
        className,
      )}
      // The library wraps this in its own `.dr-empty-state-icon` chip, so the
      // tone rides a span inside it rather than a second element carrying the
      // same class.
      icon={
        <span className={cn("contents", tone)}>
          <Icon aria-hidden />
        </span>
      }
      title={title}
      description={description}
      action={action}
    />
  )
}
