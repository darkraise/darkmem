/**
 * TanStack Router adapter for darkraise-ui 1.0.8+.
 *
 * darkraise-ui decoupled its layout + navigation components from any specific
 * router in 1.0.8. Every component that used to call TanStack hooks directly
 * now reads them through `useRouterAdapter()`, which the consumer supplies
 * via `RouterAdapterProvider`.
 *
 * This adapter implements the five entry points the UI library expects —
 * `Link`, `useNavigate`, `usePathname`, `useBack`, `useInvalidate` — in terms
 * of `@tanstack/react-router` so the existing nav/sidebar/PageHeader keep
 * working without churn.
 */
import type {
  AnchorHTMLAttributes,
  CSSProperties,
  MouseEvent,
  ReactNode,
  Ref,
} from "react"
import {
  Link as TanstackLink,
  useLocation as useTanstackLocation,
  useNavigate as useTanstackNavigate,
  useRouter as useTanstackRouter,
} from "@tanstack/react-router"
import type { RouterAdapter, RouterLinkProps } from "darkraise-ui/router"

type LinkProps = {
  to: string
  className?: string
  activeClassName?: string
  activeExact?: boolean
  style?: CSSProperties
  children: ReactNode
  onClick?: (e: MouseEvent<HTMLAnchorElement>) => void
}

export interface NavHrefTarget {
  to: string
  search?: Record<string, string>
}

/**
 * Nav hrefs may carry a query string (`/code?tab=graph`); TanStack's `to`
 * is a bare path, so split the href into `{ to, search }` before handing it
 * to Link/navigate.
 */
export function splitNavHref(href: string): NavHrefTarget {
  const qIndex = href.indexOf("?")
  if (qIndex === -1) return { to: href }
  const search: Record<string, string> = {}
  for (const [key, value] of new URLSearchParams(href.slice(qIndex + 1))) {
    search[key] = value
  }
  return { to: href.slice(0, qIndex), search }
}

/**
 * Active matching for nav links. darkraise-ui's SidebarItem passes
 * `activeExact: true` for every leaf, which — mapped to TanStack's
 * `{ exact: true }` — deselected the parent nav item on detail views
 * (`/memories/$id` no longer matched `/memories`). Instead: "/" matches
 * exactly (anything else would make it always active), every other path
 * matches itself or a strict path-segment prefix (so `/memories-old`
 * never matches `/memories`, but `/knowledge/facts/$id` keeps the Facts
 * item active), and an href query string additionally requires those
 * params to equal the current (validated) search.
 */
export function isNavHrefActive(
  href: string,
  pathname: string,
  search: Record<string, unknown>,
): boolean {
  const target = splitNavHref(href)
  const pathActive =
    target.to === "/"
      ? pathname === "/"
      : pathname === target.to || pathname.startsWith(target.to + "/")
  if (!pathActive) return false
  if (!target.search) return true
  return Object.entries(target.search).every(
    ([key, value]) => String(search[key] ?? "") === value,
  )
}

/** href → label for the app's nav, so a collapsed rail link can be named.
 *
 *  darkraise-ui gap (SidebarItem, 6.x): a collapsed nav link renders only its
 *  icon and sets no `aria-label`, so every rail link was an empty link to
 *  assistive tech. `RouterLinkProps` carries no label, so the layout registers
 *  its nav here and the adapter names any link the library marks
 *  `data-collapsed="true"`. Retire once the library labels collapsed items. */
const navLabels = new Map<string, string>()

export function registerNavLabels(
  groups: ReadonlyArray<{
    items: ReadonlyArray<{ href: string; label: string }>
  }>,
) {
  for (const group of groups) {
    for (const item of group.items) navLabels.set(item.href, item.label)
  }
}

/** Every prop beyond `RouterLinkProps` is forwarded to the anchor, and so is
 *  the ref. Radix `Slot` (TooltipTrigger/PopoverTrigger `asChild`) merges its
 *  ref, pointer/focus handlers, `data-state` and `aria-describedby` into the
 *  child's props; dropping them is why the collapsed rail's per-item tooltip
 *  never opened. The library's `data-collapsed` / `data-depth` hooks ride the
 *  same path. */
function AdapterLink({
  to,
  className,
  activeClassName,
  // Consumed: TanStack would otherwise receive it as an unknown anchor prop.
  activeExact: _activeExact,
  style,
  children,
  onClick,
  ref,
  ...rest
}: LinkProps & {
  ref?: Ref<HTMLAnchorElement>
} & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, keyof LinkProps | "href">) {
  const pathname = useTanstackLocation({ select: (l) => l.pathname })
  const search = useTanstackLocation({ select: (l) => l.search }) as Record<
    string,
    unknown
  >
  const target = splitNavHref(to)
  const active =
    activeClassName !== undefined && isNavHrefActive(to, pathname, search)
  const collapsedLabel =
    (rest as Record<string, unknown>)["data-collapsed"] === "true"
      ? navLabels.get(to)
      : undefined
  return (
    <TanstackLink
      {...rest}
      aria-label={rest["aria-label"] ?? collapsedLabel}
      ref={ref}
      to={target.to}
      search={target.search}
      className={
        active && activeClassName
          ? [className, activeClassName].filter(Boolean).join(" ")
          : className
      }
      style={style}
      onClick={onClick}
    >
      {children}
    </TanstackLink>
  )
}

function useAdapterNavigate(): (to: string) => void {
  const navigate = useTanstackNavigate()
  return (to: string) => {
    // Adapter surface accepts a plain path string; delegate to TanStack's
    // object-form navigate so type-safe params still flow through in the app.
    const target = splitNavHref(to)
    navigate({ to: target.to, search: target.search })
  }
}

function useAdapterPathname(): string {
  return useTanstackLocation({ select: (l) => l.pathname })
}

function useAdapterBack(): () => void {
  const router = useTanstackRouter()
  return () => {
    router.history.back()
  }
}

function useAdapterInvalidate(): () => void {
  const router = useTanstackRouter()
  return () => {
    // Fire-and-forget — darkraise-ui's use case is "refresh after nav edit",
    // so awaiting the invalidation promise is not required.
    void router.invalidate()
  }
}

export const tanstackRouterAdapter: RouterAdapter = {
  Link: AdapterLink as RouterAdapter["Link"],
  useNavigate: useAdapterNavigate,
  usePathname: useAdapterPathname,
  useBack: useAdapterBack,
  useInvalidate: useAdapterInvalidate,
}

export type { RouterLinkProps }
